from __future__ import annotations

from biggr_cli.catalog import TABLE_ENDPOINT_SPECS


def test_all_documented_table_endpoints_present() -> None:
    expected = {
        "compartments",
        "genomes",
        "models",
        "collections",
        "collection",
        "universal-reactions",
        "universal-metabolites",
        "universal-metabolite-in-models",
        "compartment-models",
        "model-reactions",
        "model-genes",
        "model-metabolites",
        "model-metabolite-in-reactions",
        "search-metabolites",
        "search-metabolites-ref",
        "search-metabolites-ann",
        "search-metabolites-inchikey",
        "search-reactions",
        "search-reactions-ref",
        "search-reactions-ann",
        "search-reactions-ec",
        "search-models",
        "search-genomes",
    }
    assert set(TABLE_ENDPOINT_SPECS) == expected
