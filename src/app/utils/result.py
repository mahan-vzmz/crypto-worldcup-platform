"""A functional Result type for error handling without exceptions.

Provides ``Ok`` and ``Err`` wrappers to explicitly type the success and
failure paths of domain operations.
"""

from dataclasses import dataclass
from typing import TypeVar

T = TypeVar("T")
U = TypeVar("U")
E = TypeVar("E", bound=Exception)


@dataclass(frozen=True)
class Ok[T]:
    """Represents a successful outcome containing a value."""

    value: T


@dataclass(frozen=True)
class Err[E]:
    """Represents a failed outcome containing an error."""

    error: E


Result = Ok[T] | Err[E]
