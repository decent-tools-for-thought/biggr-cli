from __future__ import annotations

from typing import Any

import pytest
from _pytest.capture import CaptureFixture

import biggr_cli.cli as cli_module
from biggr_cli.cli import main


class FakeClient:
    def __init__(
        self,
        base_url: str,
        timeout_seconds: float,
        http_client: object | None = None,
    ) -> None:
        _ = (base_url, timeout_seconds, http_client)
        pass

    def __enter__(self) -> FakeClient:
        return self

    def __exit__(self, _exc_type: object, _exc: object, _tb: object) -> None:
        return None

    def list_table(self, endpoint: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        assert endpoint == "/models"
        assert params == {"length": "2"}
        return {
            "recordsTotal": 2,
            "recordsFiltered": 2,
            "data": [{"model__bigg_id": "iML1515"}, {"model__bigg_id": "iJO1366"}],
        }

    def post_table(self, endpoint: str, form_data: dict[str, str]) -> dict[str, Any]:
        return {"endpoint": endpoint, "form": form_data}

    def get_object(self, object_type: str, object_id: str | int) -> dict[str, Any]:
        return {"id": object_id, "object": {"_type": object_type}}

    def get_download(self, resource: str) -> list[dict[str, Any]]:
        return [{"bigg_id": resource}]

    def get_escher_map(self, model_bigg_id: str, map_bigg_id: str) -> list[Any]:
        return [{"model": model_bigg_id, "map": map_bigg_id}]


def test_tables_command_success(
    monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli_module, "BiggrClient", FakeClient)
    code = main(["tables", "/models", "--param", "length=2"])
    out = capsys.readouterr().out

    assert code == 0
    assert "records_total=2" in out
    assert "iML1515" in out


def test_invalid_key_value_returns_code_2(capsys: CaptureFixture[str]) -> None:
    code = main(["tables", "/models", "--param", "bad"])
    err = capsys.readouterr().err

    assert code == 2
    assert "Invalid key-value" in err
