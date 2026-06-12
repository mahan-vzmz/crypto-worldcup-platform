"""Custom exception hierarchy for the application.

All deliberately-raised application errors derive from ``AppError``. This gives
calling code a single base type to catch ("something our code raised on purpose")
while still allowing precise handling of individual failure domains.

Each layer translates foreign exceptions (e.g. ``requests`` or ``json`` errors)
into one of these types at its boundary, so lower-level libraries never leak
upward into the service or presentation layers.
"""


class AppError(Exception):
    """Base class for every exception raised deliberately by this application.

    Catch this at the top level (e.g. in ``main``) to handle any known,
    anticipated failure gracefully. Unexpected exceptions (such as a bare
    ``KeyError`` from a genuine bug) are intentionally *not* covered by this
    base, so they surface loudly instead of being silently swallowed.
    """


class ConfigError(AppError):
    """Raised when configuration is missing or invalid.

    Example: a required environment variable is absent, or a setting holds a
    value that cannot be parsed. Raised by the configuration layer.
    """


class StorageError(AppError):
    """Raised when a persistence operation fails.

    Example: a JSON file cannot be read or written, or stored data cannot be
    serialized or deserialized. Raised by the storage layer, which translates
    lower-level ``OSError`` and ``json`` exceptions into this type.
    """


class APIError(AppError):
    """Raised when an external API request fails.

    Example: a request times out, returns an error status, or returns a body
    that cannot be parsed into our models. Raised by the client layer, which
    translates lower-level ``requests`` exceptions into this type.
    """