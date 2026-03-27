<div align="center">

# biggr-cli

[![Release](https://img.shields.io/github/v/release/decent-tools-for-thought/biggr-cli?sort=semver&color=0f766e)](https://github.com/decent-tools-for-thought/biggr-cli/releases)
![Python](https://img.shields.io/badge/python-3.11%2B-0ea5e9)
![License](https://img.shields.io/badge/license-MIT-14b8a6)

Comprehensive command-line client for BiGGr v3 data access: tables, objects, downloads, search/xref, Escher maps, and higher-level model workflows.

</div>

> [!IMPORTANT]
> This codebase is entirely AI-generated. It is useful to me, I hope it might be useful to others, and issues and contributions are welcome.

## Map
- [Install](#install)
- [Functionality](#functionality)
- [Configuration](#configuration)
- [Quick Start](#quick-start)
- [Credits](#credits)

## Install
$$\color{#0EA5E9}Install \space \color{#14B8A6}Tool$$

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install .
biggr --help
```

## Functionality
$$\color{#0EA5E9}Work \space \color{#14B8A6}Tables$$

- `biggr tables`: direct DataTables-style endpoint access with GET query params (`--param`) or POST form fields (`--form`).
- `biggr endpoint`: explicit named coverage for every documented table endpoint.
- `biggr validate-endpoint`: preflight endpoint validation and URL/method preview without calling upstream.

Named endpoint coverage (`biggr endpoint <name>`):
- `compartments`, `genomes`, `models`, `collections`
- `collection` (`collection_bigg_id`)
- `universal-reactions`, `universal-metabolites`
- `universal-metabolite-in-models` (`model_bigg_id`)
- `compartment-models` (`compartment_bigg_id`)
- `model-reactions`, `model-genes`, `model-metabolites` (`model_bigg_id`)
- `model-metabolite-in-reactions` (`model_bigg_id`, `metabolite_bigg_id`)
- `search-metabolites`, `search-metabolites-ref`, `search-metabolites-ann`, `search-metabolites-inchikey` (`query`)
- `search-reactions`, `search-reactions-ref`, `search-reactions-ann`, `search-reactions-ec` (`query`)
- `search-models`, `search-genomes` (`query`)

$$\color{#0EA5E9}Inspect \space \color{#14B8A6}Objects$$
- `biggr objects`: direct `POST /objects` access by `type` + `id`.
- `biggr object-get`: object fetch plus optional relationship expansion (`--expand`).
- `biggr api object-types`: list documented object types.

$$\color{#0EA5E9}Resolve \space \color{#14B8A6}Search$$
- `biggr search`: family-specific search endpoints.
- `biggr xref`: namespace-aware external-id search (`CHEBI:...`, `RHEA:...`, `EC:...`, `seed:...`, `kegg:...`, `metacyc:...`, `metanetx:...`).
- `biggr xref-resolve`: normalized xref resolution output (selected families, entity hint, matches).
- `biggr search-smart`: heuristic routing for xref-style, EC-like, and broad free-text queries.

$$\color{#0EA5E9}Export \space \color{#14B8A6}Data$$
- `biggr download`: bulk download for one resource (`metabolites` or `reactions`).
- `biggr download-all`: fetch both resources; optionally write `metabolites.json` and `reactions.json`.

$$\color{#0EA5E9}Browse \space \color{#14B8A6}Escher$$
- `biggr escher`: fetch raw map JSON for one model/map pair.
- `biggr escher-list`: list documented map IDs, optionally probe availability for a specific model.
- `biggr escher-url`: print editable map URL for browser workflows.
- `biggr api escher-maps`: list documented map IDs from API metadata command group.

$$\color{#0EA5E9}Analyze \space \color{#14B8A6}Models$$
- `biggr model summary`: compact model summary with counts.
- `biggr model reactions|genes|metabolites`: common model table shortcuts.
- `biggr model metabolite-usage`: reactions involving one metabolite in a model.
- `biggr model reaction`: one-shot model reaction profile lookup.
- `biggr model metabolite`: one-shot metabolite profile + usage summary.
- `biggr model export`: model bundle (summary + key tables + Escher map availability).
- `biggr models-top`: rank models by reaction/metabolite/gene counts.
- `biggr compare models`: side-by-side summary with count deltas.

$$\color{#0EA5E9}Check \space \color{#14B8A6}Runtime$$
- `biggr doctor`: connectivity/runtime/API sanity checks.
- `biggr docs`: generated full command reference (global options, commands, subcommands, and options).

$$\color{#0EA5E9}Use \space \color{#14B8A6}Escape\space Hatch$$
- `biggr raw`: arbitrary GET/POST for endpoints outside dedicated command groups.

## Configuration
$$\color{#0EA5E9}Set \space \color{#14B8A6}Defaults$$

Configuration precedence:
1. CLI flags
2. Environment variables
3. Built-in defaults

Supported settings:
- `--base-url` / `BIGGR_BASE_URL` (default `https://biggr.org/api/v3`)
- `--timeout` / `BIGGR_TIMEOUT` (default `20` seconds)
- `--output` / `BIGGR_OUTPUT` (`text|json|jsonl`, default `text`)

Example:

```bash
export BIGGR_TIMEOUT=40
export BIGGR_OUTPUT=json
biggr tables /models --limit 10
```

## Quick Start
$$\color{#0EA5E9}Try \space \color{#14B8A6}Queries$$

```bash
# Discover command surface
biggr --help
biggr docs

# API metadata and catalogs
biggr api table-endpoints --output json
biggr api object-types --output json
biggr api escher-maps --output json

# Core table/object workflows
biggr endpoint models --limit 3 --output json
biggr objects model iML1515 --output json
biggr object-get model iML1515 --expand model_reactions --output json

# Search/xref workflows
biggr search models ecoli --limit 3 --output json
biggr xref CHEBI:17790 --limit 3 --output json
biggr xref-resolve RHEA:16505 --limit 3 --output json
biggr search-smart "ecoli" --limit 3 --output json

# Model workflows
biggr model summary iML1515 --output json
biggr model reactions iML1515 --limit 3 --output json
biggr model metabolite-usage iML1515 atp_c:-4 --output json
biggr model export iML1515 --limit 3 --output json
biggr compare models iML1515 iJO1366 --output json

# Downloads and Escher
biggr download reactions --limit 2 --output json
biggr download-all --out-dir ./biggr-downloads
biggr escher iML1515 ubiquinone --output json
biggr escher-list --model iML1515 --output json
biggr escher-url iML1515 ubiquinone --output json

# Validation and diagnostics
biggr validate-endpoint model-reactions --arg model_bigg_id=iML1515 --output json
biggr doctor --output json
```

## Credits

This client wraps the BiGGr v3 Data Access API and is not affiliated with BiGGr.

Credit goes to the BiGGr team for the data platform, endpoint design, and documentation this tool relies on.
