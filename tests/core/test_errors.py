import pytest

from moteroom.core.errors import (
    ConflictError,
    MoteroomError,
    NotFoundError,
    ValidationError,
)


def test_every_error_is_one_of_ours():
    raised = (ValidationError("a", "b"), NotFoundError("a", "b"), ConflictError("a", "b", "c"))
    for error in raised:
        assert isinstance(error, MoteroomError)


def test_a_validation_error_names_the_field_and_the_reason():
    error = ValidationError("tare", "must weigh less than the gross")
    assert error.field == "tare"
    assert error.message == "must weigh less than the gross"
    assert str(error) == "tare: must weigh less than the gross"


def test_a_not_found_error_names_what_was_looked_for():
    error = NotFoundError("ticket", "9")
    assert error.kind == "ticket"
    assert error.key == "9"
    assert str(error) == "no ticket with key '9'"


def test_a_conflict_error_names_the_record_and_what_it_contradicts():
    error = ConflictError("module", "HW-004181", "was already weighed in")
    assert error.kind == "module"
    assert error.key == "HW-004181"
    assert error.detail == "was already weighed in"
    assert str(error) == "module 'HW-004181': was already weighed in"


def test_our_errors_can_be_caught_as_one():
    with pytest.raises(MoteroomError):
        raise ConflictError("a", "b", "c")


def test_our_errors_are_still_exceptions():
    assert isinstance(MoteroomError("something"), Exception)
