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
        if endpoint == "/models":
            assert params in ({"length": "2"}, None)
            return {
                "recordsTotal": 2,
                "recordsFiltered": 2,
                "data": [
                    {
                        "model__bigg_id": "iML1515",
                        "modelcount__reaction_count": 3000,
                        "modelcount__metabolite_count": 1800,
                        "modelcount__gene_count": 1500,
                    },
                    {
                        "model__bigg_id": "iJO1366",
                        "modelcount__reaction_count": 2500,
                        "modelcount__metabolite_count": 1700,
                        "modelcount__gene_count": 1300,
                    },
                ],
            }
        if endpoint in {
            "/search/reactions_ref/RHEA:1",
            "/search/metabolites_ref/CHEBI:1",
            "/search/reactions_ec/1.1.1.1",
            "/search/models/ecoli",
            "/search/genomes/ecoli",
            "/search/metabolites/ecoli",
            "/search/reactions/ecoli",
            "/collections/iML1515",
            "/models/iML1515/reactions",
            "/models/iML1515/genes",
            "/models/iML1515/metabolites",
            "/models/iML1515/metabolite_in_reactions/atp_c:-4",
        }:
            return {
                "recordsTotal": 1,
                "recordsFiltered": 1,
                "data": [{"id": endpoint, "model__bigg_id": "iML1515"}],
            }
        raise AssertionError(f"Unexpected list_table endpoint {endpoint}")

    def post_table(self, endpoint: str, form_data: dict[str, str]) -> dict[str, Any]:
        return {"endpoint": endpoint, "form": form_data}

    def get_object(self, object_type: str, object_id: str | int) -> dict[str, Any]:
        if object_type == "model":
            return {
                "id": 4,
                "object": {
                    "_type": "Model",
                    "id": 4,
                    "bigg_id": "iML1515",
                    "organism": "Escherichia coli",
                    "taxon_id": 511145,
                    "model_count": {
                        "reaction_count": 2712,
                        "metabolite_count": 1877,
                        "gene_count": 1516,
                    },
                },
            }
        return {"id": object_id, "object": {"_type": object_type, "id": 4}}

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


def test_model_summary_command(
    monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli_module, "BiggrClient", FakeClient)
    code = main(["--output", "json", "model", "summary", "iML1515"])
    out = capsys.readouterr().out
    assert code == 0
    assert '"model_bigg_id": "iML1515"' in out


def test_model_reactions_command(
    monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli_module, "BiggrClient", FakeClient)
    code = main(["--output", "json", "model", "reactions", "iML1515"])
    out = capsys.readouterr().out
    assert code == 0
    assert "/models/iML1515/reactions" in out


def test_model_genes_command(monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture[str]) -> None:
    monkeypatch.setattr(cli_module, "BiggrClient", FakeClient)
    code = main(["--output", "json", "model", "genes", "iML1515"])
    out = capsys.readouterr().out
    assert code == 0
    assert "/models/iML1515/genes" in out


def test_model_metabolites_command(
    monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli_module, "BiggrClient", FakeClient)
    code = main(["--output", "json", "model", "metabolites", "iML1515"])
    out = capsys.readouterr().out
    assert code == 0
    assert "/models/iML1515/metabolites" in out


def test_model_metabolite_usage_command(
    monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli_module, "BiggrClient", FakeClient)
    code = main(
        [
            "--output",
            "json",
            "model",
            "metabolite-usage",
            "iML1515",
            "atp_c:-4",
        ]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "/models/iML1515/metabolite_in_reactions/atp_c:-4" in out


def test_xref_command(monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture[str]) -> None:
    monkeypatch.setattr(cli_module, "BiggrClient", FakeClient)
    code = main(["--output", "json", "xref", "RHEA:1"])
    out = capsys.readouterr().out
    assert code == 0
    assert '"_source_family": "reactions_ref"' in out


def test_object_get_expand_command(
    monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli_module, "BiggrClient", FakeClient)
    code = main(
        [
            "--output",
            "json",
            "object-get",
            "model",
            "iML1515",
            "--expand",
            "model_reactions",
        ]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert '"expanded"' in out
    assert '"model_reactions"' in out


def test_escher_list_command(monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture[str]) -> None:
    monkeypatch.setattr(cli_module, "BiggrClient", FakeClient)
    code = main(["--output", "json", "escher-list", "--model", "iML1515"])
    out = capsys.readouterr().out
    assert code == 0
    assert '"model_bigg_id": "iML1515"' in out
    assert '"map_bigg_id": "ubiquinone"' in out


def test_download_all_command(monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture[str]) -> None:
    monkeypatch.setattr(cli_module, "BiggrClient", FakeClient)
    code = main(["--output", "json", "download-all"])
    out = capsys.readouterr().out
    assert code == 0
    assert '"counts"' in out
    assert '"metabolites": 1' in out


def test_models_top_command(monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture[str]) -> None:
    monkeypatch.setattr(cli_module, "BiggrClient", FakeClient)
    code = main(["--output", "json", "models-top", "--by", "reactions", "--limit", "1"])
    out = capsys.readouterr().out
    assert code == 0
    assert '"rank_by": "reactions"' in out
    assert '"model__bigg_id": "iML1515"' in out


def test_endpoint_named_command(
    monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli_module, "BiggrClient", FakeClient)
    code = main(
        [
            "--output",
            "json",
            "endpoint",
            "collection",
            "--arg",
            "collection_bigg_id=iML1515",
        ]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "/collections/iML1515" in out


def test_escher_url_command(capsys: CaptureFixture[str]) -> None:
    code = main(["--output", "json", "escher-url", "iML1515", "ubiquinone"])
    out = capsys.readouterr().out
    assert code == 0
    assert '"url": "https://biggr.org/models/iML1515/escher/ubiquinone"' in out


def test_api_table_endpoints_command(capsys: CaptureFixture[str]) -> None:
    code = main(["--output", "json", "api", "table-endpoints"])
    out = capsys.readouterr().out
    assert code == 0
    assert '"name": "models"' in out


def test_api_object_types_command(capsys: CaptureFixture[str]) -> None:
    code = main(["--output", "json", "api", "object-types"])
    out = capsys.readouterr().out
    assert code == 0
    assert '"object_type": "MODEL"' in out


def test_api_escher_maps_command(
    monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli_module, "BiggrClient", FakeClient)
    code = main(["--output", "json", "api", "escher-maps"])
    out = capsys.readouterr().out
    assert code == 0
    assert '"map_bigg_id": "ubiquinone"' in out


def test_compare_models_command(
    monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli_module, "BiggrClient", FakeClient)
    code = main(["--output", "json", "compare", "models", "iML1515", "iJO1366"])
    out = capsys.readouterr().out
    assert code == 0
    assert '"deltas"' in out


def test_model_reaction_profile_command(
    monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli_module, "BiggrClient", FakeClient)
    code = main(
        [
            "--output",
            "json",
            "model",
            "reaction",
            "iML1515",
            "/models/iML1515/reactions",
        ]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert '"reaction_bigg_id"' in out


def test_model_metabolite_profile_command(
    monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli_module, "BiggrClient", FakeClient)
    code = main(
        [
            "--output",
            "json",
            "model",
            "metabolite",
            "iML1515",
            "atp_c:-4",
            "--usage-limit",
            "1",
        ]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert '"usage"' in out


def test_xref_resolve_command(monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture[str]) -> None:
    monkeypatch.setattr(cli_module, "BiggrClient", FakeClient)
    code = main(["--output", "json", "xref-resolve", "RHEA:1", "--limit", "1"])
    out = capsys.readouterr().out
    assert code == 0
    assert '"entity_hint": "reaction"' in out


def test_search_smart_command(monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture[str]) -> None:
    monkeypatch.setattr(cli_module, "BiggrClient", FakeClient)
    code = main(["--output", "json", "search-smart", "ecoli", "--limit", "1"])
    out = capsys.readouterr().out
    assert code == 0
    assert '"mode": "broad"' in out


def test_model_export_command(monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture[str]) -> None:
    monkeypatch.setattr(cli_module, "BiggrClient", FakeClient)
    code = main(["--output", "json", "model", "export", "iML1515", "--limit", "1"])
    out = capsys.readouterr().out
    assert code == 0
    assert '"summary"' in out
    assert '"escher_maps"' in out


def test_validate_endpoint_command(capsys: CaptureFixture[str]) -> None:
    code = main(
        [
            "--output",
            "json",
            "validate-endpoint",
            "collection",
            "--arg",
            "collection_bigg_id=iML1515",
        ]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert '"endpoint_path": "/collections/iML1515"' in out


def test_doctor_command(monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture[str]) -> None:
    monkeypatch.setattr(cli_module, "BiggrClient", FakeClient)
    code = main(["--output", "json", "doctor"])
    out = capsys.readouterr().out
    assert code == 0
    assert '"checks_total"' in out
