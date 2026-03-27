"""Configuration loading with CLI > env > defaults precedence."""

from __future__ import annotations

import os
from dataclasses import dataclass

from .errors import ConfigError

DEFAULT_BASE_URL = "https://biggr.org/api/v3"
DEFAULT_TIMEOUT_SECONDS = 20.0
DEFAULT_FORMAT = "text"


@dataclass(frozen=True)
class AppConfig:
    """Runtime configuration values used by the CLI and client."""

    base_url: str
    timeout_seconds: float
    output_format: str


def resolve_config(
    base_url_flag: str | None,
    timeout_flag: float | None,
    output_flag: str | None,
) -> AppConfig:
    """Resolve configuration values by precedence.

    Priority order:
    1. Explicit CLI flags
    2. Environment variables
    3. Built-in defaults
    """
    base_url = base_url_flag or os.getenv("BIGGR_BASE_URL") or DEFAULT_BASE_URL

    timeout_value = timeout_flag
    if timeout_value is None:
        raw_timeout = os.getenv("BIGGR_TIMEOUT")
        if raw_timeout is not None:
            try:
                timeout_value = float(raw_timeout)
            except ValueError as exc:
                raise ConfigError("Invalid BIGGR_TIMEOUT value; expected a number.") from exc

    if timeout_value is None:
        timeout_value = DEFAULT_TIMEOUT_SECONDS

    if timeout_value <= 0:
        raise ConfigError("Timeout must be greater than zero.")

    output_format = output_flag or os.getenv("BIGGR_OUTPUT") or DEFAULT_FORMAT
    if output_format not in {"text", "json", "jsonl"}:
        raise ConfigError("Output format must be one of: text, json, jsonl.")

    return AppConfig(
        base_url=base_url.rstrip("/"), timeout_seconds=timeout_value, output_format=output_format
    )
