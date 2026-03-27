"""Static API catalog metadata from BiGGr data access docs."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TableEndpointSpec:
    name: str
    path_template: str
    required_args: tuple[str, ...] = ()


TABLE_ENDPOINT_SPECS: dict[str, TableEndpointSpec] = {
    "compartments": TableEndpointSpec("compartments", "/compartments"),
    "genomes": TableEndpointSpec("genomes", "/genomes"),
    "models": TableEndpointSpec("models", "/models"),
    "collections": TableEndpointSpec("collections", "/collections"),
    "collection": TableEndpointSpec(
        "collection",
        "/collections/{collection_bigg_id}",
        required_args=("collection_bigg_id",),
    ),
    "universal-reactions": TableEndpointSpec("universal-reactions", "/universal/reactions"),
    "universal-metabolites": TableEndpointSpec("universal-metabolites", "/universal/metabolites"),
    "universal-metabolite-in-models": TableEndpointSpec(
        "universal-metabolite-in-models",
        "/universal/metabolite_in_models/{model_bigg_id}",
        required_args=("model_bigg_id",),
    ),
    "compartment-models": TableEndpointSpec(
        "compartment-models",
        "/compartments/{compartment_bigg_id}/models",
        required_args=("compartment_bigg_id",),
    ),
    "model-reactions": TableEndpointSpec(
        "model-reactions",
        "/models/{model_bigg_id}/reactions",
        required_args=("model_bigg_id",),
    ),
    "model-genes": TableEndpointSpec(
        "model-genes",
        "/models/{model_bigg_id}/genes",
        required_args=("model_bigg_id",),
    ),
    "model-metabolites": TableEndpointSpec(
        "model-metabolites",
        "/models/{model_bigg_id}/metabolites",
        required_args=("model_bigg_id",),
    ),
    "model-metabolite-in-reactions": TableEndpointSpec(
        "model-metabolite-in-reactions",
        "/models/{model_bigg_id}/metabolite_in_reactions/{metabolite_bigg_id}",
        required_args=("model_bigg_id", "metabolite_bigg_id"),
    ),
    "search-metabolites": TableEndpointSpec(
        "search-metabolites",
        "/search/metabolites/{query}",
        required_args=("query",),
    ),
    "search-metabolites-ref": TableEndpointSpec(
        "search-metabolites-ref",
        "/search/metabolites_ref/{query}",
        required_args=("query",),
    ),
    "search-metabolites-ann": TableEndpointSpec(
        "search-metabolites-ann",
        "/search/metabolites_ann/{query}",
        required_args=("query",),
    ),
    "search-metabolites-inchikey": TableEndpointSpec(
        "search-metabolites-inchikey",
        "/search/metabolites_inchikey/{query}",
        required_args=("query",),
    ),
    "search-reactions": TableEndpointSpec(
        "search-reactions",
        "/search/reactions/{query}",
        required_args=("query",),
    ),
    "search-reactions-ref": TableEndpointSpec(
        "search-reactions-ref",
        "/search/reactions_ref/{query}",
        required_args=("query",),
    ),
    "search-reactions-ann": TableEndpointSpec(
        "search-reactions-ann",
        "/search/reactions_ann/{query}",
        required_args=("query",),
    ),
    "search-reactions-ec": TableEndpointSpec(
        "search-reactions-ec",
        "/search/reactions_ec/{query}",
        required_args=("query",),
    ),
    "search-models": TableEndpointSpec(
        "search-models",
        "/search/models/{query}",
        required_args=("query",),
    ),
    "search-genomes": TableEndpointSpec(
        "search-genomes",
        "/search/genomes/{query}",
        required_args=("query",),
    ),
}


DOCUMENTED_OBJECT_TYPES: list[str] = [
    "MODEL",
    "COMPONENT",
    "COMPARTMENTALIZEDCOMPONENT",
    "MODELCOMPARTMENTALIZEDCOMPONENT",
    "UNIVERSALCOMPONENT",
    "REACTION",
    "UNIVERSALREACTION",
    "REFERENCEREACTION",
    "REFERENCECOMPOUND",
    "REFERENCEREACTIVEPART",
    "GENOME",
    "CHROMOSOME",
    "COMPARTMENT",
    "PUBLICATION",
    "INCHI",
    "MEMOTETEST",
    "MEMOTERESULT",
    "ANNOTATION",
    "TAXON",
]


DOCUMENTED_ESCHER_MAPS: list[str] = [
    "ubiquinone",
    "menaquinone",
    "2demethylmenaquinone",
    "ecoli_central_metabolism",
    "nucleotide_histidine_biosynthesis",
    "arginine_biosynthesis",
    "aspartate_asparagine_biosynthesis",
    "cysteine_biosynthesis",
]
