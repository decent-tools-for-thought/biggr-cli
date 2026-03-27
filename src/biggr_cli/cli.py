"""CLI argument parsing and command dispatch for BiGGr."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from typing import Any

from .client import BiggrClient
from .config import resolve_config
from .core import (
    apply_limit_to_table,
    download_query,
    escher_query,
    normalize_table_endpoint,
    object_query,
    parse_key_value_pairs,
    render_output,
    search_query,
    table_query,
    validate_positive_limit,
)
from .errors import ApiError, BiggrError, ConfigError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="biggr",
        description=(
            "CLI wrapper for BiGGr v3 data APIs (tables, objects, downloads, and Escher maps)."
        ),
    )
    parser.add_argument(
        "--base-url", help="Override BiGGr API base URL (default: https://biggr.org/api/v3)."
    )
    parser.add_argument("--timeout", type=float, help="HTTP timeout in seconds (default: 20).")
    parser.add_argument(
        "--output",
        choices=["text", "json", "jsonl"],
        help="Output format (default: text, env BIGGR_OUTPUT).",
    )

    subparsers = parser.add_subparsers(dest="command")

    p_tables = subparsers.add_parser("tables", help="Query DataTables-style API endpoints.")
    p_tables.add_argument(
        "endpoint", help="Table endpoint path, e.g. /models or /models/iML1515/reactions."
    )
    p_tables.add_argument(
        "--param",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Repeatable query parameter for GET requests.",
    )
    p_tables.add_argument(
        "--form",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Repeatable form field for POST requests (Datatables server-side style).",
    )
    p_tables.add_argument("--limit", type=int, help="Client-side cap on returned rows.")

    p_search = subparsers.add_parser("search", help="Search API shortcuts for common families.")
    p_search.add_argument(
        "family",
        choices=[
            "metabolites",
            "metabolites_ref",
            "metabolites_ann",
            "metabolites_inchikey",
            "reactions",
            "reactions_ref",
            "reactions_ann",
            "reactions_ec",
            "models",
            "genomes",
        ],
        help="Search family endpoint.",
    )
    p_search.add_argument(
        "query", help="Search term. For external refs use namespace:id style where relevant."
    )
    p_search.add_argument("--limit", type=int, help="Client-side cap on returned rows.")

    p_objects = subparsers.add_parser("objects", help="Query object API via POST /objects.")
    p_objects.add_argument("type", help="Object type, e.g. model, taxon, model.model_reactions.")
    p_objects.add_argument("id", help="Object id (int or string BiGG id).")

    p_download = subparsers.add_parser("download", help="Bulk downloads for reactions/metabolites.")
    p_download.add_argument(
        "resource", choices=["metabolites", "reactions"], help="Resource to download."
    )
    p_download.add_argument("--limit", type=int, help="Client-side cap on list entries.")

    p_escher = subparsers.add_parser(
        "escher", help="Fetch raw Escher map JSON for a model/map id pair."
    )
    p_escher.add_argument("model_bigg_id", help="Model BiGG ID, e.g. iML1515.")
    p_escher.add_argument("map_bigg_id", help="Map id, e.g. ubiquinone.")

    p_raw = subparsers.add_parser(
        "raw", help="Generic escape hatch for arbitrary endpoint GET/POST."
    )
    p_raw.add_argument("method", choices=["GET", "POST"], help="HTTP method.")
    p_raw.add_argument("endpoint", help="Endpoint relative to base URL, e.g. /models.")
    p_raw.add_argument(
        "--param",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Repeatable query parameter.",
    )
    p_raw.add_argument(
        "--form",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Repeatable form field for POST.",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    try:
        config = resolve_config(args.base_url, args.timeout, args.output)
        output_payload = dispatch_command(args, config.base_url, config.timeout_seconds)
        rendered = render_output(output_payload, config.output_format)
        if rendered:
            print(rendered)
        return 0
    except (ValueError, ConfigError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except (BiggrError, ApiError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def dispatch_command(args: argparse.Namespace, base_url: str, timeout_seconds: float) -> Any:
    with BiggrClient(base_url=base_url, timeout_seconds=timeout_seconds) as client:
        if args.command == "tables":
            endpoint = normalize_table_endpoint(args.endpoint)
            get_params = parse_key_value_pairs(args.param)
            post_form = parse_key_value_pairs(args.form)
            limit = validate_positive_limit(args.limit)
            payload = table_query(
                client=client,
                endpoint=endpoint,
                get_params=get_params,
                post_form=post_form,
            )
            return apply_limit_to_table(payload, limit)

        if args.command == "search":
            limit = validate_positive_limit(args.limit)
            payload = search_query(client=client, family=args.family, query=args.query)
            return apply_limit_to_table(payload, limit)

        if args.command == "objects":
            return object_query(client=client, object_type=args.type, object_id_raw=args.id)

        if args.command == "download":
            limit = validate_positive_limit(args.limit)
            return download_query(client=client, resource=args.resource, limit=limit)

        if args.command == "escher":
            return escher_query(
                client=client, model_bigg_id=args.model_bigg_id, map_bigg_id=args.map_bigg_id
            )

        if args.command == "raw":
            endpoint = normalize_table_endpoint(args.endpoint)
            params = parse_key_value_pairs(args.param)
            form_data = parse_key_value_pairs(args.form)
            if args.method == "GET":
                if form_data:
                    raise ValueError("--form is only valid with POST.")
                return client.list_table(endpoint=endpoint, params=params or None)
            return client.post_table(endpoint=endpoint, form_data=form_data)

    raise ValueError(f"Unsupported command: {args.command}")


def entrypoint() -> int:
    return main()
