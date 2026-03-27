"""Core operations and output rendering for BiGGr CLI."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from typing import Any

from .client import BiggrClient
from .errors import ApiResponseError


def parse_object_id(value: str) -> str | int:
    """Parse object id; convert decimal integers to int, keep others as strings."""
    return int(value) if value.isdigit() else value


def parse_key_value_pairs(items: list[str]) -> dict[str, str]:
    """Parse repeated key=value CLI arguments into a dictionary."""
    parsed: dict[str, str] = {}
    for raw in items:
        if "=" not in raw:
            raise ValueError(f"Invalid key-value '{raw}'. Expected KEY=VALUE.")
        key, value = raw.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"Invalid key-value '{raw}'. Key cannot be empty.")
        parsed[key] = value
    return parsed


def table_query(
    client: BiggrClient,
    endpoint: str,
    get_params: Mapping[str, str] | None,
    post_form: Mapping[str, str] | None,
) -> dict[str, Any]:
    """Execute a table request with optional POST body.

    If form data is provided, POST is used. Otherwise GET.
    """
    if post_form:
        return client.post_table(endpoint=endpoint, form_data=post_form)
    return client.list_table(endpoint=endpoint, params=get_params)


def object_query(client: BiggrClient, object_type: str, object_id_raw: str) -> dict[str, Any]:
    """Execute an object query by type and id."""
    object_id = parse_object_id(object_id_raw)
    return client.get_object(object_type=object_type, object_id=object_id)


def search_query(client: BiggrClient, family: str, query: str) -> dict[str, Any]:
    """Execute a search query for a supported search family."""
    endpoint = f"/search/{family}/{query}"
    return client.list_table(endpoint=endpoint)


def download_query(client: BiggrClient, resource: str, limit: int | None) -> list[dict[str, Any]]:
    """Fetch and optionally truncate bulk download data."""
    rows = client.get_download(resource)
    if limit is not None:
        return rows[:limit]
    return rows


def escher_query(client: BiggrClient, model_bigg_id: str, map_bigg_id: str) -> list[Any]:
    """Fetch an Escher map payload."""
    return client.get_escher_map(model_bigg_id=model_bigg_id, map_bigg_id=map_bigg_id)


def render_output(payload: Any, output_format: str) -> str:
    """Render a payload into text/json/jsonl outputs."""
    if output_format == "json":
        return json.dumps(payload, indent=2, sort_keys=True)

    if output_format == "jsonl":
        rows = _rows_for_jsonl(payload)
        return "\n".join(json.dumps(row, sort_keys=True) for row in rows)

    return render_text(payload)


def render_text(payload: Any) -> str:
    """Human-readable text mode preserving core fidelity."""
    if isinstance(payload, dict):
        if {"recordsTotal", "recordsFiltered", "data"}.issubset(payload):
            total = payload.get("recordsTotal")
            filtered = payload.get("recordsFiltered")
            rows = payload.get("data")
            count = len(rows) if isinstance(rows, list) else "unknown"
            header = f"records_total={total} records_filtered={filtered} rows={count}"
            if isinstance(rows, list):
                preview = "\n".join(_summarize_row(row) for row in rows[:10])
                return f"{header}\n{preview}" if preview else header
            return header

        if "object" in payload and isinstance(payload["object"], dict):
            obj = payload["object"]
            name = obj.get("bigg_id") or obj.get("name") or obj.get("id")
            return f"object_type={obj.get('_type', 'unknown')} id={payload.get('id')} name={name}"

        return json.dumps(payload, indent=2, sort_keys=True)

    if isinstance(payload, list):
        if payload and isinstance(payload[0], dict):
            lines = [f"rows={len(payload)}"]
            lines.extend(_summarize_row(row) for row in payload[:10])
            return "\n".join(lines)
        return json.dumps(payload, indent=2, sort_keys=True)

    return str(payload)


def _rows_for_jsonl(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        if "data" in payload and isinstance(payload["data"], list):
            rows = payload["data"]
            if all(isinstance(row, dict) for row in rows):
                return [row for row in rows if isinstance(row, dict)]
            raise ApiResponseError("Cannot output non-object rows as jsonl.")
        return [payload]

    if isinstance(payload, list):
        if all(isinstance(row, dict) for row in payload):
            return [row for row in payload if isinstance(row, dict)]
        raise ApiResponseError("Cannot output list containing non-objects as jsonl.")

    raise ApiResponseError("jsonl output is only available for object or row-list payloads.")


def _summarize_row(row: Any) -> str:
    if not isinstance(row, dict):
        return str(row)
    preferred_keys = ["bigg_id", "model__bigg_id", "name", "model__organism", "id"]
    parts: list[str] = []
    for key in preferred_keys:
        if key in row:
            parts.append(f"{key}={row[key]}")
    if not parts:
        first_pairs = list(row.items())[:3]
        parts = [f"{k}={v}" for k, v in first_pairs]
    return " | ".join(parts)


def apply_limit_to_table(payload: dict[str, Any], limit: int | None) -> dict[str, Any]:
    """Apply client-side row limit to table response payloads."""
    if limit is None:
        return payload

    data = payload.get("data")
    if not isinstance(data, list):
        raise ApiResponseError("Table response missing list 'data' field.")

    limited = data[:limit]
    updated = dict(payload)
    updated["data"] = limited
    updated["recordsFiltered"] = min(int(payload.get("recordsFiltered", len(data))), len(limited))
    return updated


def normalize_table_endpoint(endpoint: str) -> str:
    """Ensure endpoint starts with a slash for consistency."""
    if endpoint.startswith("/"):
        return endpoint
    return f"/{endpoint}"


def validate_positive_limit(limit: int | None) -> int | None:
    if limit is None:
        return None
    if limit <= 0:
        raise ValueError("--limit must be greater than zero.")
    return limit


def flatten_lines(items: Iterable[str]) -> str:
    """Join lines for stable command output in tests and CLI."""
    return "\n".join(items)
