"""Settlement reports.

Two different documents. The statement is one producer's page and it has to
add up in front of them, so it prints every line including the ones that are
nothing. The summary is the office's page and it drops to one line per
producer with the totals underneath.
"""

from __future__ import annotations

from collections.abc import Sequence

from moteroom.core.money import Money, total_money
from moteroom.core.weight import Weight, total
from moteroom.reporting.report import Report
from moteroom.settlement.statement import Statement


def statement_report(statement: Statement) -> Report:
    """One producer's page."""
    rows = tuple((name, str(amount)) for name, amount in statement.lines())
    verdict = "due to the producer" if statement.is_payable else "owing to the gin"
    return Report(
        title=f"settlement {statement.producer} {statement.season}",
        headers=("line", "amount"),
        rows=rows,
        right=(1,),
        notes=(
            f"{statement.bales} bales, {statement.lint}",
            f"{statement.net} {verdict}",
        ),
    )


def settlement_summary(statements: Sequence[Statement]) -> Report:
    """Every settlement written, one line each."""
    rows = tuple(
        (
            statement.producer,
            str(statement.bales),
            str(statement.lint.pounds),
            str(statement.lint_proceeds),
            str(statement.gin_charges),
            str(statement.seed_credit),
            str(statement.advanced),
            str(statement.net),
        )
        for statement in sorted(statements, key=lambda one: one.producer)
    )
    return Report(
        title="settlements",
        headers=(
            "producer",
            "bales",
            "lint",
            "proceeds",
            "charges",
            "seed",
            "advanced",
            "net",
        ),
        rows=rows,
        right=(1, 2, 3, 4, 5, 6, 7),
        notes=_summary_notes(statements),
    )


def _summary_notes(statements: Sequence[Statement]) -> tuple[str, ...]:
    if not statements:
        return ("nothing settled yet",)
    payable = [one for one in statements if one.is_payable]
    owing = [one for one in statements if not one.is_payable]
    return (
        f"{len(statements)} producers, "
        f"{sum(one.bales for one in statements)} bales, "
        f"{total([one.lint for one in statements])}",
        f"{len(payable)} to pay, {total_money([one.net for one in payable])}",
        f"{len(owing)} owing, {total_money([one.net for one in owing])}",
    )


def unsettled(producers: Sequence[str], statements: Sequence[Statement]) -> Report:
    """Producers with cotton in and no settlement written."""
    settled = {statement.producer for statement in statements}
    waiting = sorted(set(producers) - settled)
    return Report(
        title="not settled yet",
        headers=("producer",),
        rows=tuple((producer,) for producer in waiting),
        notes=(f"{len(waiting)} of {len(producers)} still to settle",),
    )


def total_paid(statements: Sequence[Statement]) -> Money:
    """What the season cost in cheques, ignoring the ones that came back."""
    return total_money([one.net for one in statements if one.is_payable])


def total_lint(statements: Sequence[Statement]) -> Weight:
    return total([one.lint for one in statements])
