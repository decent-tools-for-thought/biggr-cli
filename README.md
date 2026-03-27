# biggr-cli

`biggr-cli` is a production-ready command-line wrapper for the BiGGr v3 Data Access API, built for scriptable table/object lookup and Escher map retrieval.

## API profile

- API name: BiGGr v3 Data Access API
- API purpose: Programmatic access to metabolic models, reactions, metabolites, related objects, search tables, and Escher maps
- Primary users: Bioinformatics/data engineers, metabolic modeling researchers, pipeline developers
- Auth model: None (public API)
- Base URL: `https://biggr.org/api/v3`
- Docs: `https://biggr.org/data_access`

## Install

Python 3.11+ is required.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install .
```

After install, the `biggr` command is available.

## Quick start

```bash
# Show help
biggr
biggr --help

# List models table
biggr tables /models --output json

# Datatables-style POST with server-side length
biggr tables /models --form length=5 --output json

# Search models
biggr search models ecoli --limit 3 --output json

# Fetch one object by BiGG id
biggr objects model iML1515 --output json

# Fetch one object relationship by internal id
biggr objects model.model_reactions 4 --output json

# Download bulk reactions (truncated client-side)
biggr download reactions --limit 2 --output json

# Fetch Escher raw JSON map
biggr escher iML1515 ubiquinone --output json
```

## Command surface

- `biggr tables <endpoint>`
- `biggr search <family> <query>`
- `biggr objects <type> <id>`
- `biggr download <metabolites|reactions>`
- `biggr escher <model_bigg_id> <map_bigg_id>`
- `biggr raw <GET|POST> <endpoint>`

`raw` is the generic escape hatch for endpoints not covered by convenience commands.

## Output modes

- `--output text` (default): concise summaries that preserve key context
- `--output json`: pretty JSON, highest fidelity
- `--output jsonl`: one JSON object per line for row-oriented responses

`jsonl` works for object payloads and list/table row payloads containing objects.

## Configuration

Configuration precedence is explicit:

1. CLI flags
2. Environment variables
3. Built-in defaults

Supported flags/env vars:

- `--base-url` / `BIGGR_BASE_URL` (default `https://biggr.org/api/v3`)
- `--timeout` / `BIGGR_TIMEOUT` (default `20` seconds)
- `--output` / `BIGGR_OUTPUT` (`text|json|jsonl`, default `text`)

Example:

```bash
export BIGGR_TIMEOUT=40
export BIGGR_OUTPUT=json
biggr tables /models --limit 10
```

## Error handling and exit codes

- `0`: success
- `2`: usage/config/validation errors
- `1`: runtime/API/network/upstream response errors

The CLI reports concise, actionable messages for:

- HTTP failures (including status code)
- network failures/timeouts
- rate limiting (`429`, includes `Retry-After` if present)
- malformed JSON responses
- invalid argument shapes such as malformed `KEY=VALUE`

## Verification

```bash
# Install development dependencies
pip install -e .[dev]

# Lint
ruff check .

# Type check
mypy src tests

# Test
pytest
```

## Notes and caveats

- The BiGGr table API follows DataTables server-side conventions. Use `--form` for POST fields (for example `length=5`).
- Relationship object queries often require internal integer IDs (as described in BiGGr docs), while top-level objects usually accept BiGG IDs.
- This CLI intentionally avoids hidden retries for non-idempotent calls; failures are surfaced directly.

## Attribution

This tool wraps the public BiGGr API and is not an official BiGGr release. Credit to the BiGGr team for the upstream data platform and API.
