from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .compiler import Compiler
from .io import write_if_changed
from .views import load_view, query_view


def _rows(result: Any) -> list[dict[str, str | None]]:
    return [
        {str(name): str(value) if value is not None else None for name, value in row.asdict().items()}
        for row in result
    ]


def _condition(value: Any) -> dict[str, Any]:
    return value.model_dump(mode="json", by_alias=True, exclude_none=True)


def build_training_scenario(root: Path, product: str = "products/calendar") -> Path:
    """Build the offline Academy snapshot from the canonical compiler result."""
    compiler = Compiler(root)
    resolved = compiler.resolve(product, write=False)
    dataset = compiler.semantic_dataset(product)
    spec, _, definitions, rules, patterns, _ = compiler.load_inputs(product)
    manifests = compiler.load_package_manifests(product)

    privacy = next(item for item in rules if item.id == "privacy/minimize-personal-data-response")
    privacy_instance = next(
        item for item in resolved.requirements
        if item.requirement == "PRIVACY-001" and item.target == "operation.read_event"
    )
    ownership = next(item for item in rules if item.id == "security/owned-resources")
    ownership_instance = next(
        item for item in resolved.requirements
        if item.requirement == "SEC-002" and item.target == "operation.update_event"
    )
    event = next(item for item in resolved.entities if item.id == "Event")

    package_rows = _rows(query_view(dataset, "packages"))
    glossary_rows = _rows(query_view(dataset, "glossary"))
    relationship_rows = _rows(query_view(dataset, "relationship-glossary"))
    rule_rows = _rows(query_view(dataset, "rule-applications"))
    requirement_rows = _rows(query_view(dataset, "requirements"))
    provenance_rows = _rows(query_view(dataset, "provenance"))
    privacy_rule_rows = [
        row for row in rule_rows
        if "PRIVACY-001" in (row.get("instance") or "") and "read_event" in (row.get("instance") or "")
    ]
    privacy_requirement_rows = [
        row for row in requirement_rows
        if "PRIVACY-001" in (row.get("instance") or "") and "read_event" in (row.get("instance") or "")
    ]

    scenario = {
        "schemaVersion": 1,
        "scenarioHash": resolved.content_hash,
        "hashAlgorithm": resolved.hash_algorithm,
        "product": resolved.product.model_dump(mode="json"),
        "packages": [
            {
                "name": name,
                "version": resolved.knowledge.packages[name]["version"],
                "role": manifest.kind,
                "purpose": manifest.purpose,
                "integrates": manifest.integrates.model_dump(mode="json") if manifest.integrates else None,
            }
            for name, manifest in sorted(manifests.items())
        ],
        "packageRelations": package_rows,
        "glossary": glossary_rows,
        "relationshipGlossary": relationship_rows,
        "facts": [item.model_dump(mode="json") for item in resolved.facts],
        "entities": [item.model_dump(mode="json") for item in resolved.entities],
        "operations": [item.model_dump(mode="json") for item in resolved.operations],
        "responseFields": [item.response_name or item.name for item in event.fields],
        "privacy": {
            "rule": {"id": privacy.id, "version": privacy.version, "when": _condition(privacy.when), "then": privacy.then.model_dump(mode="json")},
            "definition": definitions["PRIVACY-001"].model_dump(mode="json"),
            "instance": privacy_instance.model_dump(mode="json"),
            "pattern": next(item.model_dump(mode="json") for item in patterns if item.id == privacy_instance.pattern),
        },
        "ownership": {
            "rule": {"id": ownership.id, "version": ownership.version, "when": _condition(ownership.when), "then": ownership.then.model_dump(mode="json")},
            "definition": definitions["SEC-002"].model_dump(mode="json"),
            "instance": ownership_instance.model_dump(mode="json"),
            "pattern": next(item.model_dump(mode="json") for item in patterns if item.id == ownership_instance.pattern),
        },
        "views": {"ruleApplications": rule_rows, "requirements": requirement_rows, "provenance": provenance_rows},
        "privacyProofChain": {
            "requirement": privacy_requirement_rows,
            "derivation": privacy_rule_rows,
            "provenance": [row for row in provenance_rows if row.get("entity") in {
                premise for item in privacy_rule_rows for premise in [item.get("premise")] if premise
            }],
        },
        "validationResults": [
            {"kind": "SHACL", "focus": "Event", "expected": "hasField owner", "observed": "owner vorhanden", "result": "PASS"},
            {"kind": "Verification", "focus": privacy_instance.target, "expected": "nur deklarierte Response-Felder", "observed": ", ".join(item.response_name or item.name for item in event.fields), "result": "PASS"},
            {"kind": "Verification", "focus": ownership_instance.target, "expected": "fremde Ressource ist verborgen", "observed": "HTTP 404", "result": "PASS"},
        ],
        "preparedQuery": load_view("rule-applications"),
    }

    # Editorial references are deliberately explicit and must resolve before UI output exists.
    required = {
        "rule:privacy/minimize-personal-data-response": privacy.id,
        "requirement-instance:PRIVACY-001@operation.read_event": privacy_instance.id,
        "rule:security/owned-resources": ownership.id,
        "requirement-instance:SEC-002@operation.update_event": ownership_instance.id,
    }
    for reference, value in required.items():
        if not value:
            raise ValueError(f"unresolved training scenario_ref: {reference}")

    destination = root / "training-prototype" / "scenario.generated.js"
    rendered = "window.SPECFORGE_TRAINING_SCENARIO = " + json.dumps(
        scenario, ensure_ascii=False, sort_keys=True, indent=2
    ) + ";\n"
    write_if_changed(destination, rendered)
    return destination
