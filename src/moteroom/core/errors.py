"""The error hierarchy every other package raises through."""

from __future__ import annotations


class MoteroomError(Exception):
    """Base class for everything this package raises on purpose."""


class ValidationError(MoteroomError):
    """A value was rejected before it ever reached storage."""

    def __init__(self, field: str, message: str) -> None:
        super().__init__(f"{field}: {message}")
        self.field = field
        self.message = message


class NotFoundError(MoteroomError):
    """A record was asked for by key and the book does not hold it."""

    def __init__(self, kind: str, key: str) -> None:
        super().__init__(f"no {kind} with key {key!r}")
        self.kind = kind
        self.key = key


class ConflictError(MoteroomError):
    """A write would contradict something the book already holds."""

    def __init__(self, kind: str, key: str, detail: str) -> None:
        super().__init__(f"{kind} {key!r}: {detail}")
        self.kind = kind
        self.key = key
        self.detail = detail
