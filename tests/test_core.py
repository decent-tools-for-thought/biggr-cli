from __future__ import annotations

import pytest

from biggr_cli.core import (
    _resolve_xref_families,
    apply_limit_to_table,
    model_summary,
    parse_key_value_pairs,
    parse_object_id,
    render_output,
    validate_positive_limit,
)
from biggr_cli.errors import ApiResponseError


def test_parse_object_id_int_and_string() -> None:
    assert parse_object_id("511145") == 511145
    assert parse_object_id("iML1515") == "iML1515"


def test_parse_key_value_pairs() -> None:
    parsed = parse_key_value_pairs(["length=5", "search[value]=eco"])
    assert parsed == {"length": "5", "search[value]": "eco"}


def test_parse_key_value_pairs_rejects_invalid() -> None:
    with pytest.raises(ValueError):
        parse_key_value_pairs(["bad"])


def test_apply_limit_to_table() -> None:
    payload = {
        "recordsTotal": 3,
        "recordsFiltered": 3,
        "data": [{"id": 1}, {"id": 2}, {"id": 3}],
    }
    limited = apply_limit_to_table(payload, 2)
    assert limited["data"] == [{"id": 1}, {"id": 2}]
    assert limited["recordsFiltered"] == 2


def test_render_output_jsonl_from_table() -> None:
    payload = {"recordsTotal": 2, "recordsFiltered": 2, "data": [{"id": 1}, {"id": 2}]}
    output = render_output(payload, "jsonl")
    lines = output.splitlines()
    assert lines == ['{"id": 1}', '{"id": 2}']


def test_render_output_jsonl_rejects_non_object_list() -> None:
    with pytest.raises(ApiResponseError):
        render_output([1, 2, 3], "jsonl")


def test_validate_positive_limit() -> None:
    assert validate_positive_limit(1) == 1
    with pytest.raises(ValueError):
        validate_positive_limit(0)


def test_resolve_xref_families() -> None:
    assert _resolve_xref_families("CHEBI", "CHEBI:1") == ["metabolites_ref"]
    assert _resolve_xref_families("RHEA", "RHEA:1") == ["reactions_ref"]
    assert _resolve_xref_families("EC", "EC:1.1.1.1") == ["reactions_ec"]


def test_resolve_xref_families_rejects_unknown() -> None:
    with pytest.raises(ValueError):
        _resolve_xref_families("foo", "bar")


class _SummaryClient:
    def get_object(self, object_type: str, object_id: str | int) -> dict[str, object]:
        _ = object_id
        assert object_type == "model"
        return {
            "id": 4,
            "object": {
                "id": 4,
                "bigg_id": "iML1515",
                "organism": "E. coli",
                "taxon_id": 511145,
                "model_count": {
                    "reaction_count": 2712,
                    "metabolite_count": 1877,
                    "gene_count": 1516,
                },
            },
        }


def test_model_summary_normalization() -> None:
    summary = model_summary(client=_SummaryClient(), model_id="iML1515")  # type: ignore[arg-type]
    assert summary["model_bigg_id"] == "iML1515"
    assert isinstance(summary["counts"], dict)
