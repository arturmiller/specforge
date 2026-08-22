from __future__ import annotations

from .semantic import SemanticDataset


VIEW_VERSION = "1.0.0"

QUERIES = {
    "packages": """
        SELECT ?source ?target ?relation WHERE {
          GRAPH ?graph {
            VALUES ?relation { dcterms:requires sf:bindsDomain sf:bindsImplementation }
            ?source ?relation ?target .
          }
        }
        ORDER BY ?source ?relation ?target
    """,
    "relationship-glossary": """
        SELECT ?relation ?label ?definition WHERE {
          GRAPH <https://specforge.dev/graph/vocabulary> {
            ?relation a rdf:Property ; rdfs:label ?label ; rdfs:comment ?definition .
            FILTER(LANG(?label) = "de" && LANG(?definition) = "de")
          }
        }
        ORDER BY ?relation
    """,
    "glossary": """
        SELECT ?label ?definition ?schemeName WHERE {
          GRAPH ?graph {
            ?term a skos:Concept ; skos:inScheme ?scheme ;
                  skos:prefLabel ?label ; skos:definition ?definition .
            ?scheme dcterms:identifier ?schemeName .
          }
        }
        ORDER BY ?label
    """,
    "product-model": """
        SELECT ?product ?entity ?operation ?field WHERE {
          GRAPH <https://specforge.dev/graph/product> {
            ?product a sf:Product .
            OPTIONAL { ?product sf:defines ?entity . OPTIONAL { ?entity sf:hasField ?field } }
            OPTIONAL { ?product sf:offers ?operation }
          }
        }
        ORDER BY ?entity ?field ?operation
    """,
    "rule-applications": """
        SELECT ?instance ?rule ?premise WHERE {
          GRAPH <https://specforge.dev/graph/resolved> {
            ?instance prov:qualifiedDerivation ?derivation .
            ?derivation sf:usedRule ?rule .
            OPTIONAL { ?derivation prov:entity ?premise }
          }
        }
        ORDER BY ?instance ?rule ?premise
    """,
    "requirements": """
        SELECT ?instance ?target ?pattern ?verification WHERE {
          GRAPH <https://specforge.dev/graph/resolved> {
            ?instance a sf:RequirementInstance ; sf:appliesTo ?target ;
                      sf:implementedBy ?pattern ; sf:verifiedBy ?verification .
          }
        }
        ORDER BY ?instance ?verification
    """,
    "provenance": """
        SELECT ?entity ?activity ?source WHERE {
          GRAPH ?graph {
            OPTIONAL { ?entity prov:wasGeneratedBy ?activity }
            OPTIONAL { ?entity prov:wasDerivedFrom ?source }
          }
        }
        ORDER BY ?entity ?activity ?source
    """,
    "violations": """
        SELECT ?result ?focus ?message WHERE {
          GRAPH <https://specforge.dev/graph/evidence> {
            ?report sh:result ?result .
            ?result sh:focusNode ?focus .
            OPTIONAL { ?result sh:resultMessage ?message }
          }
        }
        ORDER BY ?result
    """,
}


def query_view(dataset: SemanticDataset, name: str):
    if name not in QUERIES:
        raise KeyError(f"unknown SPARQL view {name!r}@{VIEW_VERSION}")
    return dataset.query(QUERIES[name])
