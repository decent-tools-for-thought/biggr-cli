"""Core operations and output rendering for BiGGr CLI."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from .catalog import DOCUMENTED_ESCHER_MAPS, DOCUMENTED_OBJECT_TYPES, TABLE_ENDPOINT_SPECS
from .client import BiggrClient
from .errors import ApiError, ApiResponseError


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


def search_xref_query(client: BiggrClient, query: str) -> dict[str, Any]:
    """Resolve namespace-prefixed xref query to one or more search families."""
    if ":" not in query:
        raise ValueError("xref query must be in NAMESPACE:IDENTIFIER format.")

    namespace, identifier = query.split(":", 1)
    ns = namespace.strip().lower()
    ident = identifier.strip()
    if not ns or not ident:
        raise ValueError("xref query must be in NAMESPACE:IDENTIFIER format.")

    families = _resolve_xref_families(ns, ident)
    responses: list[tuple[str, dict[str, Any]]] = []
    for family in families:
        response = search_query(client=client, family=family, query=query)
        responses.append((family, response))

    return _merge_table_payloads(query=query, families=responses)


def download_query(client: BiggrClient, resource: str, limit: int | None) -> list[dict[str, Any]]:
    """Fetch and optionally truncate bulk download data."""
    rows = client.get_download(resource)
    if limit is not None:
        return rows[:limit]
    return rows


def escher_query(client: BiggrClient, model_bigg_id: str, map_bigg_id: str) -> list[Any]:
    """Fetch an Escher map payload."""
    return client.get_escher_map(model_bigg_id=model_bigg_id, map_bigg_id=map_bigg_id)


def list_escher_maps(client: BiggrClient, model_bigg_id: str | None) -> dict[str, Any]:
    """List known maps, optionally probing availability for one model."""
    if model_bigg_id is None:
        return {
            "model_bigg_id": None,
            "recordsTotal": len(DOCUMENTED_ESCHER_MAPS),
            "recordsFiltered": len(DOCUMENTED_ESCHER_MAPS),
            "data": [
                {"map_bigg_id": map_id, "available": None} for map_id in DOCUMENTED_ESCHER_MAPS
            ],
        }

    rows: list[dict[str, Any]] = []
    for map_id in DOCUMENTED_ESCHER_MAPS:
        try:
            payload = client.get_escher_map(model_bigg_id=model_bigg_id, map_bigg_id=map_id)
            rows.append(
                {"map_bigg_id": map_id, "available": True, "preview": payload[0] if payload else {}}
            )
        except ApiError:
            rows.append({"map_bigg_id": map_id, "available": False})

    return {
        "model_bigg_id": model_bigg_id,
        "recordsTotal": len(DOCUMENTED_ESCHER_MAPS),
        "recordsFiltered": len(DOCUMENTED_ESCHER_MAPS),
        "data": rows,
    }


def escher_editor_url(model_bigg_id: str, map_bigg_id: str) -> dict[str, str]:
    return {
        "model_bigg_id": model_bigg_id,
        "map_bigg_id": map_bigg_id,
        "url": f"https://biggr.org/models/{model_bigg_id}/escher/{map_bigg_id}",
    }


def list_object_types() -> dict[str, Any]:
    return {
        "recordsTotal": len(DOCUMENTED_OBJECT_TYPES),
        "recordsFiltered": len(DOCUMENTED_OBJECT_TYPES),
        "data": [{"object_type": obj_type} for obj_type in DOCUMENTED_OBJECT_TYPES],
    }


def list_table_endpoints() -> dict[str, Any]:
    rows = [
        {
            "name": spec.name,
            "path_template": spec.path_template,
            "required_args": list(spec.required_args),
        }
        for spec in TABLE_ENDPOINT_SPECS.values()
    ]
    return {
        "recordsTotal": len(rows),
        "recordsFiltered": len(rows),
        "data": rows,
    }


def table_named_endpoint(
    client: BiggrClient,
    endpoint_name: str,
    endpoint_args: Mapping[str, str],
    get_params: Mapping[str, str] | None,
    post_form: Mapping[str, str] | None,
) -> dict[str, Any]:
    spec = TABLE_ENDPOINT_SPECS.get(endpoint_name)
    if spec is None:
        raise ValueError(f"Unknown endpoint '{endpoint_name}'.")

    missing = [arg for arg in spec.required_args if arg not in endpoint_args]
    if missing:
        names = ", ".join(missing)
        raise ValueError(f"Missing endpoint args: {names}")

    endpoint = spec.path_template.format(**endpoint_args)
    return table_query(client=client, endpoint=endpoint, get_params=get_params, post_form=post_form)


def model_table_resource(client: BiggrClient, model_bigg_id: str, resource: str) -> dict[str, Any]:
    """Fetch model-linked table resources."""
    endpoint = f"/models/{model_bigg_id}/{resource}"
    return client.list_table(endpoint=endpoint)


def model_metabolite_usage(
    client: BiggrClient, model_bigg_id: str, metabolite_bigg_id: str
) -> dict[str, Any]:
    """Fetch reactions in a model that involve a given metabolite."""
    endpoint = f"/models/{model_bigg_id}/metabolite_in_reactions/{metabolite_bigg_id}"
    return client.list_table(endpoint=endpoint)


def model_summary(client: BiggrClient, model_id: str) -> dict[str, Any]:
    """Build a compact summary for one model."""
    payload = object_query(client=client, object_type="model", object_id_raw=model_id)
    obj = payload.get("object")
    if not isinstance(obj, dict):
        raise ApiResponseError("Model object response missing 'object' dictionary.")

    model_count = obj.get("model_count")
    counts: dict[str, Any] = {}
    if isinstance(model_count, dict):
        counts = {
            "reaction_count": model_count.get("reaction_count"),
            "metabolite_count": model_count.get("metabolite_count"),
            "gene_count": model_count.get("gene_count"),
        }

    return {
        "model_bigg_id": obj.get("bigg_id"),
        "model_id": obj.get("id"),
        "organism": obj.get("organism"),
        "taxon_id": obj.get("taxon_id"),
        "counts": counts,
        "raw": payload,
    }


def object_get_with_expansion(
    client: BiggrClient,
    object_type: str,
    object_id_raw: str,
    expand_relationships: list[str],
) -> dict[str, Any]:
    """Fetch object and optionally expand relationship payloads."""
    base_payload = object_query(client=client, object_type=object_type, object_id_raw=object_id_raw)
    if not expand_relationships:
        return base_payload

    base_obj = base_payload.get("object")
    if not isinstance(base_obj, dict):
        raise ApiResponseError("Object response missing 'object' dictionary for expansion.")

    internal_id = base_obj.get("id")
    if internal_id is None:
        internal_id = base_payload.get("id")
    if not isinstance(internal_id, int):
        raise ApiResponseError(
            "Expansion requires an internal integer id in object.id or top-level id."
        )

    expanded: dict[str, Any] = {}
    for rel in expand_relationships:
        rel_name = rel.strip()
        if not rel_name:
            continue
        rel_type = rel_name if "." in rel_name else f"{object_type}.{rel_name}"
        expanded[rel_name] = client.get_object(object_type=rel_type, object_id=internal_id)

    return {"base": base_payload, "expanded": expanded}


def models_top(client: BiggrClient, by: str, limit: int) -> dict[str, Any]:
    """Return top models ranked by one count metric."""
    payload = client.list_table(endpoint="/models")
    rows = payload.get("data")
    if not isinstance(rows, list):
        raise ApiResponseError("/models response missing list 'data' field.")

    key_map = {
        "reactions": "modelcount__reaction_count",
        "metabolites": "modelcount__metabolite_count",
        "genes": "modelcount__gene_count",
    }
    sort_key = key_map[by]

    sorted_rows = sorted(
        (row for row in rows if isinstance(row, dict)),
        key=lambda row: int(row.get(sort_key, 0)),
        reverse=True,
    )

    top = sorted_rows[:limit]
    return {
        "rank_by": by,
        "recordsTotal": len(rows),
        "recordsFiltered": len(top),
        "data": top,
    }


def download_all(client: BiggrClient, out_dir: str | None, limit: int | None) -> dict[str, Any]:
    """Download both metabolites and reactions, optionally writing to disk."""
    metabolites = download_query(client=client, resource="metabolites", limit=limit)
    reactions = download_query(client=client, resource="reactions", limit=limit)

    if out_dir is None:
        return {
            "metabolites": metabolites,
            "reactions": reactions,
            "counts": {"metabolites": len(metabolites), "reactions": len(reactions)},
        }

    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    metabolite_file = out_path / "metabolites.json"
    reaction_file = out_path / "reactions.json"
    metabolite_file.write_text(json.dumps(metabolites, indent=2, sort_keys=True), encoding="utf-8")
    reaction_file.write_text(json.dumps(reactions, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "counts": {"metabolites": len(metabolites), "reactions": len(reactions)},
        "files": {
            "metabolites": str(metabolite_file),
            "reactions": str(reaction_file),
        },
    }


def compare_models(client: BiggrClient, model_a: str, model_b: str) -> dict[str, Any]:
    """Compare two models by summary counts and metadata."""
    left = model_summary(client=client, model_id=model_a)
    right = model_summary(client=client, model_id=model_b)

    left_counts_raw = left.get("counts")
    right_counts_raw = right.get("counts")
    left_counts: dict[str, Any] = left_counts_raw if isinstance(left_counts_raw, dict) else {}
    right_counts: dict[str, Any] = right_counts_raw if isinstance(right_counts_raw, dict) else {}

    deltas = {
        "reaction_count_delta": _safe_int(right_counts.get("reaction_count"))
        - _safe_int(left_counts.get("reaction_count")),
        "metabolite_count_delta": _safe_int(right_counts.get("metabolite_count"))
        - _safe_int(left_counts.get("metabolite_count")),
        "gene_count_delta": _safe_int(right_counts.get("gene_count"))
        - _safe_int(left_counts.get("gene_count")),
    }

    return {
        "model_a": left,
        "model_b": right,
        "deltas": deltas,
    }


def model_reaction_profile(
    client: BiggrClient, model_bigg_id: str, reaction_bigg_id: str
) -> dict[str, Any]:
    """Fetch one reaction row in model context."""
    table = model_table_resource(client=client, model_bigg_id=model_bigg_id, resource="reactions")
    row = _find_first_row(
        table,
        ["modelreaction__bigg_id", "reaction__bigg_id", "universalreaction__bigg_id"],
        reaction_bigg_id,
    )
    return {
        "model_bigg_id": model_bigg_id,
        "reaction_bigg_id": reaction_bigg_id,
        "match": row,
    }


def model_metabolite_profile(
    client: BiggrClient,
    model_bigg_id: str,
    metabolite_bigg_id: str,
    usage_limit: int | None,
) -> dict[str, Any]:
    """Fetch one metabolite row in model context plus usage summary."""
    table = model_table_resource(client=client, model_bigg_id=model_bigg_id, resource="metabolites")
    row = _find_first_row(
        table,
        [
            "modelcompartmentalizedcomponent__bigg_id",
            "component__bigg_id",
            "universalcomponent__bigg_id",
        ],
        metabolite_bigg_id,
    )
    usage = model_metabolite_usage(
        client=client,
        model_bigg_id=model_bigg_id,
        metabolite_bigg_id=metabolite_bigg_id,
    )
    usage = apply_limit_to_table(usage, usage_limit)
    return {
        "model_bigg_id": model_bigg_id,
        "metabolite_bigg_id": metabolite_bigg_id,
        "match": row,
        "usage": usage,
    }


def xref_resolve(client: BiggrClient, query: str, limit: int | None) -> dict[str, Any]:
    """Resolve xref into selected families and candidate matches."""
    if ":" not in query:
        raise ValueError("xref query must be in NAMESPACE:IDENTIFIER format.")
    namespace, identifier = query.split(":", 1)
    families = _resolve_xref_families(namespace.strip().lower(), identifier.strip())
    merged = search_xref_query(client=client, query=query)
    merged = apply_limit_to_table(merged, limit)
    entity_hint = _entity_hint_from_families(families)
    return {
        "query": query,
        "namespace": namespace,
        "identifier": identifier,
        "families": families,
        "entity_hint": entity_hint,
        "results": merged,
    }


def search_smart(client: BiggrClient, query: str, limit: int | None) -> dict[str, Any]:
    """Heuristic search routing for plain text, xref, and EC-like tokens."""
    stripped = query.strip()
    if not stripped:
        raise ValueError("search query cannot be empty.")

    if _looks_like_xref(stripped):
        resolved = xref_resolve(client=client, query=stripped, limit=limit)
        return {
            "mode": "xref",
            "query": stripped,
            "result": resolved,
        }

    if _looks_like_ec_query(stripped):
        payload = search_query(client=client, family="reactions_ec", query=stripped)
        payload = apply_limit_to_table(payload, limit)
        return {
            "mode": "ec",
            "query": stripped,
            "result": payload,
        }

    families = ["models", "genomes", "metabolites", "reactions"]
    responses: list[tuple[str, dict[str, Any]]] = []
    for family in families:
        responses.append((family, search_query(client=client, family=family, query=stripped)))
    merged = _merge_table_payloads(query=stripped, families=responses)
    merged = apply_limit_to_table(merged, limit)
    return {
        "mode": "broad",
        "query": stripped,
        "families": families,
        "result": merged,
    }


def export_model_bundle(
    client: BiggrClient, model_bigg_id: str, limit: int | None
) -> dict[str, Any]:
    """Bundle summary and key model resources for ETL/export workflows."""
    summary = model_summary(client=client, model_id=model_bigg_id)
    reactions = apply_limit_to_table(
        model_table_resource(client=client, model_bigg_id=model_bigg_id, resource="reactions"),
        limit,
    )
    genes = apply_limit_to_table(
        model_table_resource(client=client, model_bigg_id=model_bigg_id, resource="genes"),
        limit,
    )
    metabolites = apply_limit_to_table(
        model_table_resource(client=client, model_bigg_id=model_bigg_id, resource="metabolites"),
        limit,
    )
    maps = list_escher_maps(client=client, model_bigg_id=model_bigg_id)
    return {
        "model_bigg_id": model_bigg_id,
        "summary": summary,
        "reactions": reactions,
        "genes": genes,
        "metabolites": metabolites,
        "escher_maps": maps,
    }


def validate_endpoint_request(
    endpoint_name: str,
    endpoint_args: Mapping[str, str],
    get_params: Mapping[str, str],
    post_form: Mapping[str, str],
    base_url: str,
) -> dict[str, Any]:
    """Validate endpoint invocation and return preflight metadata."""
    spec = TABLE_ENDPOINT_SPECS.get(endpoint_name)
    if spec is None:
        raise ValueError(f"Unknown endpoint '{endpoint_name}'.")

    missing = [arg for arg in spec.required_args if arg not in endpoint_args]
    if missing:
        names = ", ".join(missing)
        raise ValueError(f"Missing endpoint args: {names}")

    endpoint_path = spec.path_template.format(**endpoint_args)
    method = "POST" if post_form else "GET"
    return {
        "name": endpoint_name,
        "method": method,
        "endpoint_path": endpoint_path,
        "url": f"{base_url.rstrip('/')}{endpoint_path}",
        "required_args": list(spec.required_args),
        "provided_args": dict(endpoint_args),
        "query_params": dict(get_params),
        "form_fields": dict(post_form),
    }


def doctor_checks(client: BiggrClient, base_url: str, timeout_seconds: float) -> dict[str, Any]:
    """Run lightweight diagnostics for connectivity and core workflows."""
    checks: list[dict[str, Any]] = []

    def run_check(name: str, fn: Any) -> None:
        try:
            fn()
            checks.append({"name": name, "ok": True})
        except Exception as exc:
            checks.append({"name": name, "ok": False, "error": str(exc)})

    run_check("tables.models", lambda: client.list_table("/models", params={"length": "1"}))
    run_check("download.metabolites", lambda: client.get_download("metabolites"))
    run_check("search.models", lambda: search_query(client=client, family="models", query="ecoli"))

    ok_count = sum(1 for c in checks if c.get("ok") is True)
    return {
        "base_url": base_url,
        "timeout_seconds": timeout_seconds,
        "checks_total": len(checks),
        "checks_ok": ok_count,
        "checks_failed": len(checks) - ok_count,
        "checks": checks,
    }


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


def _resolve_xref_families(namespace: str, identifier: str) -> list[str]:
    ns = namespace.lower()
    if ns in {"chebi", "seed.compound", "kegg.compound", "metacyc.compound", "metanetx.chemical"}:
        return ["metabolites_ref"]
    if ns in {"rhea", "seed.reaction", "kegg.reaction", "metacyc.reaction", "metanetx.reaction"}:
        return ["reactions_ref"]
    if ns in {"inchikey"}:
        return ["metabolites_inchikey"]
    if ns in {"ec", "ec-code"}:
        return ["reactions_ec"]
    if ns in {"seed", "kegg", "metacyc", "metanetx"}:
        inferred = _infer_auto_xref_family(identifier)
        if inferred is not None:
            return [inferred]
        return ["metabolites_ref", "reactions_ref"]
    raise ValueError(f"Unsupported xref namespace '{namespace}'.")


def _infer_auto_xref_family(identifier: str) -> str | None:
    token = identifier.upper()
    if token.startswith("CPD") or token.startswith("C") or token.startswith("MNXM"):
        return "metabolites_ref"
    if token.startswith("RXN") or token.startswith("R") or token.startswith("MNXR"):
        return "reactions_ref"
    return None


def _merge_table_payloads(
    query: str,
    families: list[tuple[str, dict[str, Any]]],
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    records_total = 0
    for family, payload in families:
        data = payload.get("data")
        if not isinstance(data, list):
            raise ApiResponseError(f"Search payload for family '{family}' missing list data.")
        for row in data:
            if isinstance(row, dict):
                row_copy = dict(row)
                row_copy["_source_family"] = family
                rows.append(row_copy)
        total = payload.get("recordsFiltered", payload.get("recordsTotal", len(data)))
        records_total += int(total)

    return {
        "query": query,
        "recordsTotal": records_total,
        "recordsFiltered": len(rows),
        "data": rows,
    }


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _find_first_row(payload: dict[str, Any], keys: list[str], value: str) -> dict[str, Any] | None:
    rows = payload.get("data")
    if not isinstance(rows, list):
        raise ApiResponseError("Expected 'data' list in table payload.")
    needle = value.lower()
    for row in rows:
        if not isinstance(row, dict):
            continue
        for key in keys:
            cell = row.get(key)
            if isinstance(cell, str) and cell.lower() == needle:
                return row
    return None


def _looks_like_xref(query: str) -> bool:
    if ":" not in query:
        return False
    namespace = query.split(":", 1)[0].strip().lower()
    known = {
        "chebi",
        "rhea",
        "inchikey",
        "ec",
        "ec-code",
        "seed",
        "seed.compound",
        "seed.reaction",
        "kegg",
        "kegg.compound",
        "kegg.reaction",
        "metacyc",
        "metacyc.compound",
        "metacyc.reaction",
        "metanetx",
        "metanetx.chemical",
        "metanetx.reaction",
    }
    return namespace in known


def _looks_like_ec_query(query: str) -> bool:
    if query.lower().startswith("ec:") or query.lower().startswith("ec-code:"):
        return True
    return re.fullmatch(r"\d+(\.\d+){1,3}(\.\*)?", query) is not None


def _entity_hint_from_families(families: list[str]) -> str:
    if all(f.startswith("metabolites") for f in families):
        return "metabolite"
    if all(f.startswith("reactions") for f in families):
        return "reaction"
    return "mixed"


def flatten_lines(items: Iterable[str]) -> str:
    """Join lines for stable command output in tests and CLI."""
    return "\n".join(items)
