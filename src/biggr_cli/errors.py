"""Custom exception hierarchy for user-facing errors."""


class BiggrError(Exception):
    """Base exception for all CLI/runtime errors."""


class ConfigError(BiggrError):
    """Configuration-related problem."""


class ApiError(BiggrError):
    """Base class for upstream API failures."""


class ApiAuthError(ApiError):
    """Authorization or authentication failed."""


class ApiRateLimitError(ApiError):
    """Rate limit reached."""


class ApiResponseError(ApiError):
    """Upstream response could not be parsed or was invalid."""
