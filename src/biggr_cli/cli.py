"""CLI argument parsing and command dispatch for BiGGr."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from typing import Any

from .catalog import TABLE_ENDPOINT_SPECS
from .client import BiggrClient
from .config import resolve_config
from .core import (
    apply_limit_to_table,
    compare_models,
    doctor_checks,
    download_all,
    download_query,
    escher_editor_url,
    escher_query,
    export_model_bundle,
    list_escher_maps,
    list_object_types,
    list_table_endpoints,
    model_metabolite_profile,
    model_metabolite_usage,
    model_reaction_profile,
    model_summary,
    model_table_resource,
    models_top,
    normalize_table_endpoint,
    object_get_with_expansion,
    object_query,
    parse_key_value_pairs,
    render_output,
    search_query,
    search_smart,
    search_xref_query,
    table_named_endpoint,
    table_query,
    validate_endpoint_request,
    validate_positive_limit,
    xref_resolve,
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

    subparsers.add_parser("docs", help="Print complete CLI command reference.")

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

    p_endpoint = subparsers.add_parser(
        "endpoint",
        help="Call any documented table endpoint by name (explicit endpoint catalog).",
    )
    p_endpoint.add_argument(
        "name", choices=sorted(TABLE_ENDPOINT_SPECS.keys()), help="Endpoint name."
    )
    p_endpoint.add_argument(
        "--arg",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Path template variable, repeatable (for endpoints with placeholders).",
    )
    p_endpoint.add_argument(
        "--param",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Repeatable query parameter for GET requests.",
    )
    p_endpoint.add_argument(
        "--form",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Repeatable form field for POST requests.",
    )
    p_endpoint.add_argument("--limit", type=int, help="Client-side cap on returned rows.")

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

    p_search_xref = subparsers.add_parser(
        "xref", help="Search by external namespace prefix, e.g. CHEBI:17790."
    )
    p_search_xref.add_argument("query", help="External identifier query in NAMESPACE:ID format.")
    p_search_xref.add_argument("--limit", type=int, help="Client-side cap on returned rows.")

    p_search_smart = subparsers.add_parser(
        "search-smart",
        help="Heuristic search mode for xref/EC/plain-text queries.",
    )
    p_search_smart.add_argument("query", help="Query token.")
    p_search_smart.add_argument("--limit", type=int, help="Client-side cap on returned rows.")

    p_objects = subparsers.add_parser("objects", help="Query object API via POST /objects.")
    p_objects.add_argument("type", help="Object type, e.g. model, taxon, model.model_reactions.")
    p_objects.add_argument("id", help="Object id (int or string BiGG id).")

    p_object_get = subparsers.add_parser(
        "object-get",
        help="Get object and optionally expand relationships using object internal id.",
    )
    p_object_get.add_argument("type", help="Object type, e.g. model.")
    p_object_get.add_argument("id", help="Object id (BiGG id or integer id).")
    p_object_get.add_argument(
        "--expand",
        action="append",
        default=[],
        metavar="REL",
        help="Relationship to expand (repeatable), e.g. model_reactions or model.model_reactions.",
    )

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

    p_escher_url = subparsers.add_parser("escher-url", help="Print editable Escher map URL.")
    p_escher_url.add_argument("model_bigg_id", help="Model BiGG ID, e.g. iML1515.")
    p_escher_url.add_argument("map_bigg_id", help="Map id, e.g. ubiquinone.")

    p_escher_list = subparsers.add_parser(
        "escher-list",
        help="List known Escher maps, optionally probe availability for a model.",
    )
    p_escher_list.add_argument(
        "--model",
        dest="model_bigg_id",
        help="Model BiGG ID to probe map availability (optional).",
    )

    p_model = subparsers.add_parser("model", help="High-level model workflows.")
    model_sub = p_model.add_subparsers(dest="model_command", required=True)

    p_model_summary = model_sub.add_parser("summary", help="Show compact model summary.")
    p_model_summary.add_argument("model_bigg_id", help="Model BiGG ID.")

    p_model_reactions = model_sub.add_parser("reactions", help="List model reactions table.")
    p_model_reactions.add_argument("model_bigg_id", help="Model BiGG ID.")
    p_model_reactions.add_argument("--limit", type=int, help="Client-side cap on returned rows.")

    p_model_genes = model_sub.add_parser("genes", help="List model genes table.")
    p_model_genes.add_argument("model_bigg_id", help="Model BiGG ID.")
    p_model_genes.add_argument("--limit", type=int, help="Client-side cap on returned rows.")

    p_model_metabolites = model_sub.add_parser("metabolites", help="List model metabolites table.")
    p_model_metabolites.add_argument("model_bigg_id", help="Model BiGG ID.")
    p_model_metabolites.add_argument("--limit", type=int, help="Client-side cap on returned rows.")

    p_model_usage = model_sub.add_parser(
        "metabolite-usage",
        help="List reactions in model that involve given metabolite.",
    )
    p_model_usage.add_argument("model_bigg_id", help="Model BiGG ID.")
    p_model_usage.add_argument("metabolite_bigg_id", help="Metabolite BiGG ID in the model.")
    p_model_usage.add_argument("--limit", type=int, help="Client-side cap on returned rows.")

    p_model_reaction = model_sub.add_parser(
        "reaction",
        help="Fetch one reaction profile in model context.",
    )
    p_model_reaction.add_argument("model_bigg_id", help="Model BiGG ID.")
    p_model_reaction.add_argument("reaction_bigg_id", help="Reaction BiGG ID in model context.")

    p_model_metabolite = model_sub.add_parser(
        "metabolite",
        help="Fetch one metabolite profile in model context and usage summary.",
    )
    p_model_metabolite.add_argument("model_bigg_id", help="Model BiGG ID.")
    p_model_metabolite.add_argument(
        "metabolite_bigg_id", help="Metabolite BiGG ID in model context."
    )
    p_model_metabolite.add_argument(
        "--usage-limit", type=int, help="Client-side cap on usage rows."
    )

    p_model_export = model_sub.add_parser(
        "export",
        help="Export model bundle containing summary, tables, and map availability.",
    )
    p_model_export.add_argument("model_bigg_id", help="Model BiGG ID.")
    p_model_export.add_argument("--limit", type=int, help="Client-side cap per table payload.")

    p_compare = subparsers.add_parser("compare", help="Compare two models by summary counts.")
    compare_sub = p_compare.add_subparsers(dest="compare_command", required=True)
    p_compare_models = compare_sub.add_parser("models", help="Compare two model ids.")
    p_compare_models.add_argument("model_a", help="Left model BiGG ID.")
    p_compare_models.add_argument("model_b", help="Right model BiGG ID.")

    p_xref_resolve = subparsers.add_parser(
        "xref-resolve",
        help="Resolve a namespace:id query to inferred entity and matches.",
    )
    p_xref_resolve.add_argument("query", help="External identifier query in NAMESPACE:ID format.")
    p_xref_resolve.add_argument("--limit", type=int, help="Client-side cap on returned rows.")

    p_validate = subparsers.add_parser(
        "validate-endpoint",
        help="Preflight endpoint resolution and request metadata without API call.",
    )
    p_validate.add_argument(
        "name", choices=sorted(TABLE_ENDPOINT_SPECS.keys()), help="Endpoint name."
    )
    p_validate.add_argument(
        "--arg",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Path variable assignment, repeatable.",
    )
    p_validate.add_argument(
        "--param",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Query parameter assignment, repeatable.",
    )
    p_validate.add_argument(
        "--form",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="POST form assignment, repeatable.",
    )

    subparsers.add_parser("doctor", help="Run connectivity and API sanity diagnostics.")

    p_api = subparsers.add_parser("api", help="API metadata and documented capability listings.")
    api_sub = p_api.add_subparsers(dest="api_command", required=True)
    api_sub.add_parser("table-endpoints", help="List all documented table endpoints.")
    api_sub.add_parser("object-types", help="List documented object types for /objects API.")
    api_sub.add_parser("escher-maps", help="List documented Escher map ids.")

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

    p_download_all = subparsers.add_parser(
        "download-all",
        help="Download metabolites and reactions together; optionally write JSON files.",
    )
    p_download_all.add_argument(
        "--out-dir", help="Directory where metabolites.json and reactions.json are written."
    )
    p_download_all.add_argument("--limit", type=int, help="Client-side cap per resource.")

    p_models_top = subparsers.add_parser("models-top", help="Rank top models by count metrics.")
    p_models_top.add_argument(
        "--by",
        choices=["reactions", "metabolites", "genes"],
        default="reactions",
        help="Ranking metric.",
    )
    p_models_top.add_argument("--limit", type=int, default=10, help="Number of models to return.")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "docs":
        print(generate_command_docs(parser))
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

        if args.command == "endpoint":
            endpoint_args = parse_key_value_pairs(args.arg)
            get_params = parse_key_value_pairs(args.param)
            post_form = parse_key_value_pairs(args.form)
            limit = validate_positive_limit(args.limit)
            payload = table_named_endpoint(
                client=client,
                endpoint_name=args.name,
                endpoint_args=endpoint_args,
                get_params=get_params,
                post_form=post_form,
            )
            return apply_limit_to_table(payload, limit)

        if args.command == "search":
            limit = validate_positive_limit(args.limit)
            payload = search_query(client=client, family=args.family, query=args.query)
            return apply_limit_to_table(payload, limit)

        if args.command == "xref":
            limit = validate_positive_limit(args.limit)
            payload = search_xref_query(client=client, query=args.query)
            return apply_limit_to_table(payload, limit)

        if args.command == "xref-resolve":
            limit = validate_positive_limit(args.limit)
            return xref_resolve(client=client, query=args.query, limit=limit)

        if args.command == "search-smart":
            limit = validate_positive_limit(args.limit)
            return search_smart(client=client, query=args.query, limit=limit)

        if args.command == "objects":
            return object_query(client=client, object_type=args.type, object_id_raw=args.id)

        if args.command == "object-get":
            return object_get_with_expansion(
                client=client,
                object_type=args.type,
                object_id_raw=args.id,
                expand_relationships=args.expand,
            )

        if args.command == "download":
            limit = validate_positive_limit(args.limit)
            return download_query(client=client, resource=args.resource, limit=limit)

        if args.command == "escher":
            return escher_query(
                client=client, model_bigg_id=args.model_bigg_id, map_bigg_id=args.map_bigg_id
            )

        if args.command == "escher-url":
            return escher_editor_url(model_bigg_id=args.model_bigg_id, map_bigg_id=args.map_bigg_id)

        if args.command == "escher-list":
            return list_escher_maps(client=client, model_bigg_id=args.model_bigg_id)

        if args.command == "model":
            if args.model_command == "summary":
                return model_summary(client=client, model_id=args.model_bigg_id)
            if args.model_command in {"reactions", "genes", "metabolites"}:
                limit = validate_positive_limit(args.limit)
                payload = model_table_resource(
                    client=client,
                    model_bigg_id=args.model_bigg_id,
                    resource=args.model_command,
                )
                return apply_limit_to_table(payload, limit)
            if args.model_command == "metabolite-usage":
                limit = validate_positive_limit(args.limit)
                payload = model_metabolite_usage(
                    client=client,
                    model_bigg_id=args.model_bigg_id,
                    metabolite_bigg_id=args.metabolite_bigg_id,
                )
                return apply_limit_to_table(payload, limit)
            if args.model_command == "reaction":
                return model_reaction_profile(
                    client=client,
                    model_bigg_id=args.model_bigg_id,
                    reaction_bigg_id=args.reaction_bigg_id,
                )
            if args.model_command == "metabolite":
                usage_limit = validate_positive_limit(args.usage_limit)
                return model_metabolite_profile(
                    client=client,
                    model_bigg_id=args.model_bigg_id,
                    metabolite_bigg_id=args.metabolite_bigg_id,
                    usage_limit=usage_limit,
                )
            if args.model_command == "export":
                limit = validate_positive_limit(args.limit)
                return export_model_bundle(
                    client=client, model_bigg_id=args.model_bigg_id, limit=limit
                )
            raise ValueError(f"Unsupported model command: {args.model_command}")

        if args.command == "compare":
            if args.compare_command == "models":
                return compare_models(client=client, model_a=args.model_a, model_b=args.model_b)
            raise ValueError(f"Unsupported compare command: {args.compare_command}")

        if args.command == "api":
            if args.api_command == "table-endpoints":
                return list_table_endpoints()
            if args.api_command == "object-types":
                return list_object_types()
            if args.api_command == "escher-maps":
                return list_escher_maps(client=client, model_bigg_id=None)
            raise ValueError(f"Unsupported api command: {args.api_command}")

        if args.command == "raw":
            endpoint = normalize_table_endpoint(args.endpoint)
            params = parse_key_value_pairs(args.param)
            form_data = parse_key_value_pairs(args.form)
            if args.method == "GET":
                if form_data:
                    raise ValueError("--form is only valid with POST.")
                return client.list_table(endpoint=endpoint, params=params or None)
            return client.post_table(endpoint=endpoint, form_data=form_data)

        if args.command == "download-all":
            limit = validate_positive_limit(args.limit)
            return download_all(client=client, out_dir=args.out_dir, limit=limit)

        if args.command == "models-top":
            limit = validate_positive_limit(args.limit)
            if limit is None:
                raise ValueError("--limit must be provided.")
            return models_top(client=client, by=args.by, limit=limit)

        if args.command == "validate-endpoint":
            endpoint_args = parse_key_value_pairs(args.arg)
            get_params = parse_key_value_pairs(args.param)
            post_form = parse_key_value_pairs(args.form)
            return validate_endpoint_request(
                endpoint_name=args.name,
                endpoint_args=endpoint_args,
                get_params=get_params,
                post_form=post_form,
                base_url=base_url,
            )

        if args.command == "doctor":
            return doctor_checks(client=client, base_url=base_url, timeout_seconds=timeout_seconds)

    raise ValueError(f"Unsupported command: {args.command}")


def generate_command_docs(parser: argparse.ArgumentParser) -> str:
    """Generate a full command/subcommand/options reference from argparse tree."""
    lines: list[str] = []
    lines.append("# biggr Command Reference")
    lines.append("")
    lines.append("## Global Options")
    lines.extend(_format_options(parser, prefix="- "))
    lines.append("")
    lines.append("## Commands")

    top_subparsers = _get_subparsers_action(parser)
    if top_subparsers is None:
        lines.append("- (none)")
        return "\n".join(lines)

    for name in sorted(top_subparsers.choices):
        command_parser = top_subparsers.choices[name]
        lines.append(f"### {name}")
        desc = command_parser.description or command_parser.format_usage().strip()
        lines.append(f"{desc}")

        command_options = _format_options(command_parser, prefix="- ")
        if command_options:
            lines.append("Options:")
            lines.extend(command_options)

        nested = _get_subparsers_action(command_parser)
        if nested is not None:
            lines.append("Subcommands:")
            for sub_name in sorted(nested.choices):
                sub_parser = nested.choices[sub_name]
                lines.append(f"- {name} {sub_name}")
                sub_options = _format_options(sub_parser, prefix="  - ")
                lines.extend(sub_options)
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _format_options(parser: argparse.ArgumentParser, prefix: str) -> list[str]:
    output: list[str] = []
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            continue
        if not action.option_strings and action.dest == "help":
            continue
        if action.dest == argparse.SUPPRESS:
            continue

        if action.option_strings:
            flags = ", ".join(action.option_strings)
            metavar = action.metavar if isinstance(action.metavar, str) else None
            if metavar is None and action.dest and action.nargs != 0 and action.choices is None:
                metavar = action.dest.upper()
            if action.choices:
                choice_text = "|".join(str(choice) for choice in action.choices)
                flags = f"{flags} {{{choice_text}}}"
            elif metavar:
                flags = f"{flags} {metavar}"
            help_text = action.help or ""
            output.append(f"{prefix}`{flags}`: {help_text}")
        else:
            name = action.metavar or action.dest
            help_text = action.help or ""
            output.append(f"{prefix}`{name}`: {help_text}")
    return output


def _get_subparsers_action(parser: argparse.ArgumentParser) -> Any:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action
    return None


def entrypoint() -> int:
    return main()
