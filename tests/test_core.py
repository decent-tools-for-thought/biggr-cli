from __future__ import annotations

import pytest

from biggr_cli.core import (
    apply_limit_to_table,
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
