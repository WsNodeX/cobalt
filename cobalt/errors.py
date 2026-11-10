"""Exception hierarchy for cobalt."""

from __future__ import annotations


class CobaltError(Exception):
    """Base class for every error raised by cobalt."""


class InvalidConfiguration(CobaltError, ValueError):
    """Raised when a cache is built with parameters that cannot work."""


class KeyNotHashable(CobaltError, TypeError):
    """Raised when a non-hashable object is used as a cache key."""


class UnsupportedPolicy(CobaltError, KeyError):
    """Raised when the builder is asked for a policy that does not exist."""
