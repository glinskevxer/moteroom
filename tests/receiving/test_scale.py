from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from moteroom.core.errors import ConflictError, NotFoundError, ValidationError
from moteroom.core.weight import Weight
from moteroom.receiving.scale import Certificate, ScaleBook

DAY = date(2025, 10, 14)


def certificate(**overrides: Any) -> Certificate:
    fields: dict[str, Any] = {
        "scale": "TB01",
        "tested_on": date(2025, 8, 1),
        "expires_on": date(2026, 7, 31),
        "tester": "STATE WEIGHTS",
        "error": Decimal("0.2"),
    }
    fields.update(overrides)
    return Certificate(**fields)


@pytest.mark.parametrize("scale", ["", "T01", "TB1", "tb01", "TB012"])
def test_a_scale_name_has_a_shape(scale):
    with pytest.raises(ValidationError):
        certificate(scale=scale)


def test_a_certificate_names_who_tested_it():
    with pytest.raises(ValidationError):
        certificate(tester="  ")


def test_a_certificate_has_to_run_forwards():
    with pytest.raises(ValidationError):
        certificate(expires_on=date(2025, 8, 1))


@pytest.mark.parametrize("error", ["5.1", "-5.1", "0.25"])
def test_an_error_off_the_scale_is_refused(error):
    with pytest.raises(ValidationError):
        certificate(error=Decimal(error))


def test_a_certificate_covers_its_own_dates():
    held = certificate()
    assert held.covers(date(2025, 8, 1))
    assert held.covers(date(2026, 7, 31))
    assert not held.covers(date(2025, 7, 31))
    assert not held.covers(date(2026, 8, 1))


def test_a_revoked_certificate_stops_covering():
    held = certificate(revoked_on=date(2025, 11, 1))
    assert held.covers(date(2025, 10, 31))
    assert not held.covers(date(2025, 11, 1))


def test_a_revocation_before_the_test_is_refused():
    with pytest.raises(ValidationError):
        certificate(revoked_on=date(2025, 7, 1))


def test_a_certificate_warns_before_it_runs_out():
    held = certificate()
    assert not held.expiring(date(2026, 6, 1))
    assert held.expiring(date(2026, 7, 20))
    assert held.days_left(date(2026, 7, 20)) == 11
    assert held.days_left(date(2027, 1, 1)) == 0


def test_a_certificate_prints_its_line():
    assert str(certificate()) == "TB01 certified to 2026-07-31 by STATE WEIGHTS"


def test_the_book_finds_what_stands_on_a_day():
    book = ScaleBook()
    book.certify(certificate())
    assert book.current("TB01", DAY).tester == "STATE WEIGHTS"
    assert book.is_certified("TB01", DAY)
    assert not book.is_certified("TB01", date(2027, 1, 1))
    assert book.scales() == ["TB01"]
    assert len(book) == 1


def test_a_scale_nobody_certified():
    with pytest.raises(NotFoundError):
        ScaleBook().current("TB01", DAY)
    assert not ScaleBook().is_certified("TB01", DAY)


def test_two_certificates_cannot_overlap():
    book = ScaleBook()
    book.certify(certificate())
    with pytest.raises(ConflictError):
        book.certify(certificate(tested_on=date(2026, 1, 1), expires_on=date(2026, 12, 31)))


def test_a_later_certificate_takes_over():
    book = ScaleBook()
    book.extend(
        [
            certificate(),
            certificate(tested_on=date(2026, 8, 1), expires_on=date(2027, 7, 31)),
        ]
    )
    assert book.current("TB01", date(2026, 9, 1)).expires_on == date(2027, 7, 31)
    assert len(book.for_scale("TB01")) == 2


def test_the_book_lists_what_runs_out_soon():
    book = ScaleBook()
    book.extend([certificate(), certificate(scale="TB02", expires_on=date(2026, 9, 30))])
    expiring = book.expiring(date(2026, 7, 20))
    assert [one.scale for one in expiring] == ["TB01"]
    assert book.expiring(date(2025, 10, 1)) == []


def test_a_weight_can_be_corrected_for_the_known_error():
    book = ScaleBook()
    book.certify(certificate(error=Decimal("1.0")))
    assert book.correction("TB01", DAY, Weight(21_200)) == Weight(20_988)
    book.certify(certificate(scale="TB02", error=Decimal("0.0")))
    assert book.correction("TB02", DAY, Weight(21_200)) == Weight(21_200)


def test_correcting_on_a_scale_with_no_certificate():
    with pytest.raises(NotFoundError):
        ScaleBook().correction("TB01", DAY, Weight(1_000))
