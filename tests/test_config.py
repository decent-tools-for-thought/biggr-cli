from __future__ import annotations

import pytest

from biggr_cli.config import DEFAULT_BASE_URL, DEFAULT_TIMEOUT_SECONDS, resolve_config
from biggr_cli.errors import ConfigError


def test_resolve_config_uses_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BIGGR_BASE_URL", raising=False)
    monkeypatch.delenv("BIGGR_TIMEOUT", raising=False)
    monkeypatch.delenv("BIGGR_OUTPUT", raising=False)

    cfg = resolve_config(None, None, None)
    assert cfg.base_url == DEFAULT_BASE_URL
    assert cfg.timeout_seconds == DEFAULT_TIMEOUT_SECONDS
    assert cfg.output_format == "text"


def test_resolve_config_env_precedence(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BIGGR_BASE_URL", "https://example.test/api/v3/")
    monkeypatch.setenv("BIGGR_TIMEOUT", "12")
    monkeypatch.setenv("BIGGR_OUTPUT", "json")

    cfg = resolve_config(None, None, None)
    assert cfg.base_url == "https://example.test/api/v3"
    assert cfg.timeout_seconds == 12.0
    assert cfg.output_format == "json"


def test_resolve_config_cli_overrides_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BIGGR_BASE_URL", "https://env.test/api/v3")
    monkeypatch.setenv("BIGGR_TIMEOUT", "8")
    monkeypatch.setenv("BIGGR_OUTPUT", "text")

    cfg = resolve_config("https://cli.test/v3", 2.5, "jsonl")
    assert cfg.base_url == "https://cli.test/v3"
    assert cfg.timeout_seconds == 2.5
    assert cfg.output_format == "jsonl"


def test_resolve_config_rejects_invalid_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BIGGR_TIMEOUT", "x")

    with pytest.raises(ConfigError):
        resolve_config(None, None, None)
