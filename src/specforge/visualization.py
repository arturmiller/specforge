from __future__ import annotations

from html import escape
import json
from pathlib import Path
import re
from typing import Any

from .compiler import Compiler
from .io import write_if_changed
from .glossary import load_academy_glossary, load_product_glossary as _load_product_glossary
from .semantic import RELATION_DEFINITIONS
from .views import query_view


COLORS = {
    "product": "#e7b35a",
    "package": "#8fb8a8",
    "entity": "#5f91c9",
    "field": "#83add8",
    "operation": "#477bb2",
    "classification": "#c487b5",
    "fact": "#a9a9b3",
    "rule": "#d98261",
    "requirement": "#e6a24d",
    "pattern": "#71a77c",
    "verification": "#887ab8",
    "artifact": "#77808b",
}

_EDGE_LABELS = {key: label for key, (_, label, _) in RELATION_DEFINITIONS.items()}
RELATIONSHIP_GLOSSARY = {
    _EDGE_LABELS[key]: definition
    for key, (_, _, definition) in RELATION_DEFINITIONS.items()
}


def load_glossary(root: Path) -> dict[str, str]:
    return load_academy_glossary(root)


def load_product_glossary(root: Path, product: str | Path) -> dict[str, str]:
    return _load_product_glossary(Compiler(root).product_file(product))


def _display(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    if value is True:
        return "true"
    if value is False:
        return "false"
    return str(value)


def _term(value: Any) -> str:
    variables = {
        "$operation": "Operation",
        "$resource": "Ressource",
        "$owner_field": "Eigentümerfeld",
    }
    return variables.get(str(value), _display(value))


def _fact_sentence(subject: Any, predicate: str, obj: Any) -> str:
    left, right = _term(subject), _term(obj)
    phrases = {
        "returns": f"{left} gibt {right} zurück",
        "acts_on": f"{left} bearbeitet {right}",
        "contains_classification": f"{left} enthält die Klassifikation {right}",
        "action": f"{left} hat die Aktion {right}",
        "scope": f"{left} hat den Geltungsbereich {right}",
        "has_field": f"{left} besitzt das Feld {right}",
        "relation": f"{left} hat die Beziehung {right}",
        "classified_as": f"{left} ist als {right} klassifiziert",
    }
    return phrases.get(predicate, f"{left} {predicate} {right}")


def _condition_expression(condition: Any) -> str:
    if condition.fact:
        fact = condition.fact
        return _fact_sentence(fact.subject, fact.predicate, fact.object)
    if condition.not_:
        return f"NICHT ({_condition_expression(condition.not_)})"
    if condition.any is not None:
        return "(" + " ODER ".join(_condition_expression(child) for child in condition.any) + ")"
    if condition.all is not None:
        return "(" + " UND ".join(_condition_expression(child) for child in condition.all) + ")"
    if condition.equals:
        return f"{_term(condition.equals[0])} entspricht {_term(condition.equals[1])}"
    return ""


def _condition_lines(condition: Any) -> list[str]:
    if condition.all is None:
        return [_condition_expression(condition)]
    lines: list[str] = []
    for index, child in enumerate(condition.all):
        expression = _condition_expression(child)
        lines.append(expression if index == 0 else f"UND {expression}")
    return lines


def _rule_title(control: str, value: Any) -> str:
    titles = {
        ("authentication", "required"): "Authentifizierung für personenbezogene Daten",
        ("authorization", "ownership"): "Eigentümerzugriff auf Ressourcen",
        ("event_time_interval", "end_after_start"): "Gültiges Zeitintervall für Events",
        ("response_data_minimization", "declared_fields_only"): "Datenminimierung in API-Antworten",
    }
    return titles.get((control, str(value)), control.replace("_", " ").title())


def build_graph(root: Path, product: str | Path) -> dict[str, Any]:
    """Build a presentation graph without changing compiler semantics."""
    root = root.resolve()
    compiler = Compiler(root)
    spec, concepts, definitions, rules, patterns, packages = compiler.load_inputs(product)
    manifests = compiler.load_package_manifests(product)
    resolved = compiler.resolve(product, write=False)
    semantic = compiler.semantic_dataset(product)
    product_path = compiler.product_file(product).relative_to(root).as_posix()
    nodes: dict[str, dict[str, Any]] = {}
    edges: set[tuple[str, str, str]] = set()

    def node(identifier: str, kind: str, label: str, *, source: str = "", **details: Any) -> str:
        nodes[identifier] = {
            "id": identifier,
            "kind": kind,
            "label": label,
            "source": source,
            "details": {key: value for key, value in details.items() if value not in (None, [], {}, "")},
        }
        return identifier

    def edge(source: str, target: str, label: str) -> None:
        edges.add((source, target, label))

    product_id = node(
        f"product:{spec.product.id}", "product", spec.product.id,
        source=product_path, version=spec.product.version, schema_version=spec.schema_version,
    )
    for name, metadata in sorted(packages.items()):
        manifest = manifests[name]
        package_id = node(
            f"package:{name}", "package", name,
            source=f"knowledge/{name}/{metadata['version']}/package.trig",
            package_kind=manifest.kind or "legacy", version=metadata["version"],
            owner=manifest.owner, purpose=manifest.purpose, content_hash=metadata["hash"],
        )
    package_names = {
        str(semantic.iris.package(name, metadata["version"])): name
        for name, metadata in packages.items()
    }
    product_iri = str(semantic.iris.product(spec.product.id, spec.product.version))
    relation_labels = {
        str(value[0]): _EDGE_LABELS[key] for key, value in RELATION_DEFINITIONS.items()
    }
    relationship_glossary = {
        relation_labels[str(row.relation)]: str(row.definition)
        for row in query_view(semantic, "relationship-glossary")
        if str(row.relation) in relation_labels
    }
    for row in query_view(semantic, "packages"):
        source_name = package_names.get(str(row.source))
        target_name = package_names.get(str(row.target))
        source = product_id if str(row.source) == product_iri else f"package:{source_name}"
        target = f"package:{target_name}"
        if source in nodes and target in nodes:
            edge(source, target, relation_labels[str(row.relation)])

    for entity in spec.entities:
        entity_id = node(f"entity:{entity.id}", "entity", entity.id, source=product_path)
        edge(product_id, entity_id, "defines")
        for field in entity.fields:
            field_id = node(
                f"field:{entity.id}.{field.name}", "field", f"{entity.id}.{field.name}",
                source=product_path, type=field.type, optional=field.optional,
                relation=field.relation, classification=field.classification,
            )
            edge(entity_id, field_id, "has field")
            if field.classification:
                classification_id = f"classification:{field.classification}"
                if classification_id not in nodes:
                    node(classification_id, "classification", field.classification)
                edge(field_id, classification_id, "classified as")

    for concept in concepts:
        concept_id = f"entity:{concept.id}"
        if concept_id not in nodes:
            node(concept_id, "entity", concept.id, source=f"{concept.source.document}@{concept.version}")
        for parent in concept.is_a:
            parent_id = f"entity:{parent}"
            if parent_id not in nodes:
                node(parent_id, "entity", parent)
            edge(concept_id, parent_id, "is a")
        for classification in concept.classifications:
            classification_id = f"classification:{classification}"
            if classification_id not in nodes:
                node(classification_id, "classification", classification)
            edge(concept_id, classification_id, "classified as")

    for operation in spec.operations:
        operation_id = node(
            f"operation:{operation.id}", "operation", operation.id, source=product_path,
            action=operation.action, acts_on=operation.acts_on, returns=operation.returns,
            actor=operation.actor, scope=operation.scope,
        )
        edge(product_id, operation_id, "offers")
        edge(operation_id, f"entity:{operation.acts_on}", "acts on")
        if operation.returns:
            edge(operation_id, f"entity:{operation.returns}", "returns")
        edge(operation_id, f"entity:{operation.actor}", "actor")

    source_by_id: dict[str, str] = {}
    for name, metadata in sorted(packages.items()):
        package = root / "knowledge" / name / metadata["version"]
        for filename, items in (
            ("requirements.ttl", [item for item in definitions.values() if item.source.document]),
            ("patterns.ttl", patterns),
            ("rules.ttl", rules),
        ):
            path = package / filename
            if not path.exists():
                continue
            source = path.read_text(encoding="utf-8")
            for item in items:
                if f'"{item.id}"' in source:
                    source_by_id.setdefault(item.id, path.relative_to(root).as_posix())

    for rule in rules:
        definition = definitions[rule.then.requirement]
        title = _rule_title(definition.expectation.control, definition.expectation.value)
        rule_id = node(
            f"rule:{rule.id}", "rule", title, source=source_by_id.get(rule.id, ""),
            technical_id=rule.id, version=rule.version,
            wenn=_condition_lines(rule.when),
            dann=[
                f"{rule.then.requirement} gilt für die gebundene Operation",
                f"{definition.expectation.control} = {_display(definition.expectation.value)}",
            ],
            applications=[],
        )
        nodes[rule_id]["details"]["applications"] = []
        requirement_id = f"requirement-definition:{rule.then.requirement}"
        edge(rule_id, requirement_id, "derives")

    for definition in definitions.values():
        definition_source = source_by_id.get(definition.id, "")
        node(
            f"requirement-definition:{definition.id}", "requirement", definition.id,
            source=definition_source, version=definition.version,
            statement=definition.statement,
            expectation=f"{definition.expectation.control} = {_display(definition.expectation.value)}",
            verifications=[
                {
                    "id": verification.id,
                    "adapter": verification.adapter,
                    "setup": verification.setup,
                    "assertion": verification.assertion.model_dump(mode="json", exclude_none=True),
                }
                for verification in definition.verifications
            ],
        )

    facts = {fact.id: fact for fact in resolved.facts}
    used_fact_ids = {
        fact_id
        for instance in resolved.requirements
        for derivation in instance.derivations
        for fact_id in derivation.facts
    }
    premise_ids = {premise for fact in facts.values() if fact.id in used_fact_ids for premise in fact.premises}
    visible_facts = used_fact_ids | premise_ids
    for fact_id in sorted(visible_facts):
        fact = facts[fact_id]
        node(
            f"fact:{fact.id}", "fact", f"{fact.subject} {fact.predicate} {_display(fact.object)}",
            source=fact.provenance, origin=fact.origin.value, derivation=fact.derivation,
        )
    for fact_id in sorted(visible_facts):
        for premise in facts[fact_id].premises:
            edge(f"fact:{premise}", f"fact:{fact_id}", "supports")

    verification_nodes: set[str] = set()
    for instance in resolved.requirements:
        instance_id = node(
            f"requirement:{instance.id}", "requirement", instance.id,
            source=source_by_id.get(instance.requirement, ""), statement=instance.statement,
            requirement_kind=instance.kind, status=instance.status.value,
            expectation=f"{instance.expectation.control} = {_display(instance.expectation.value)}",
            target=instance.target,
        )
        edge(f"requirement-definition:{instance.requirement}", instance_id, "instantiated as")
        edge(instance_id, f"operation:{instance.target.removeprefix('operation.')}", "applies to")
        for derivation in instance.derivations:
            edge(f"rule:{derivation.rule}", instance_id, "derives")
            for fact_id in derivation.facts:
                edge(f"fact:{fact_id}", f"rule:{derivation.rule}", "matches")
            rule_node = nodes[f"rule:{derivation.rule}"]
            bindings = [f"${key} → {_display(value)}" for key, value in sorted(derivation.bindings.items())]
            why = [
                _fact_sentence(facts[fact_id].subject, facts[fact_id].predicate, facts[fact_id].object)
                for fact_id in derivation.facts
            ]
            operation = instance.target.removeprefix("operation.")
            resource = derivation.bindings.get("resource")
            rule_node["details"]["applications"].append(
                {
                    "label": f"{operation} → {resource}" if resource else operation,
                    "bindings": bindings,
                    "why": why,
                    "result": [
                        instance.id,
                        f"{instance.expectation.control} = {_display(instance.expectation.value)}",
                    ],
                    "requirement": instance_id,
                }
            )
        if instance.pattern:
            edge(instance_id, f"pattern:{instance.pattern}", "implemented by")
        for verification in instance.verifications:
            verification_id = f"verification:{verification.id}"
            if verification_id not in verification_nodes:
                node(
                    verification_id, "verification", verification.id,
                    adapter=verification.adapter, setup=verification.setup,
                    assertion=verification.assertion.model_dump(mode="json", exclude_none=True),
                    mandatory=verification.mandatory,
                )
                verification_nodes.add(verification_id)
            edge(instance_id, verification_id, "verified by")

    for pattern in patterns:
        pattern_id = node(
            f"pattern:{pattern.id}", "pattern", pattern.id, source=source_by_id.get(pattern.id, ""),
            version=pattern.version, stack=pattern.stack, controls=pattern.controls or pattern.addresses,
        )
        for verification in pattern.verifications:
            edge(pattern_id, f"verification:{verification}", "provides")
        for artifact in pattern.artifacts:
            artifact_id = f"artifact:{artifact}"
            if artifact_id not in nodes:
                node(artifact_id, "artifact", artifact, source=artifact)
            edge(pattern_id, artifact_id, "touches")

    # Definition nodes are useful internally, but duplicate labels add noise. Connect their
    # package directly and retain them only when no concrete instance exists.
    instantiated = {instance.requirement for instance in resolved.requirements}
    for requirement_id, definition in definitions.items():
        source = source_by_id.get(requirement_id, "")
        parts = source.split("/")
        if len(parts) > 1:
            edge(f"package:{parts[1]}", f"requirement-definition:{requirement_id}", "contains")
        if requirement_id in instantiated:
            nodes[f"requirement-definition:{requirement_id}"]["definition"] = True

    glossary_rows = list(query_view(semantic, "glossary"))
    academy_glossary = {
        str(row.label): str(row.definition) for row in glossary_rows if str(row.schemeName) != "product"
    }
    product_glossary = {
        str(row.label): str(row.definition) for row in glossary_rows if str(row.schemeName) == "product"
    }
    return {
        "product": spec.product.model_dump(mode="json"),
        "nodes": sorted(nodes.values(), key=lambda item: (item["kind"], item["label"], item["id"])),
        "edges": [
            {"source": source, "target": target, "label": label}
            for source, target, label in sorted(edges)
            if source in nodes and target in nodes
        ],
        "colors": COLORS,
        "relationshipGlossary": relationship_glossary,
        "glossary": {**academy_glossary, **product_glossary},
        "glossaryKinds": {
            **{term: "academy" for term in academy_glossary},
            **{term: "product" for term in product_glossary},
        },
    }


def create_visualization(root: Path, product: str | Path) -> Path:
    root = root.resolve()
    graph = build_graph(root, product)
    product_id = graph["product"]["id"]
    destination = root / "generated" / product_id / "visualization" / "index.html"
    payload = json.dumps(graph, ensure_ascii=False, sort_keys=True).replace("</", "<\\/")
    html = HTML_TEMPLATE.replace("__TITLE__", escape(f"{product_id} – Spec Explorer")).replace("__GRAPH_DATA__", payload)
    write_if_changed(destination, html)
    return destination


HTML_TEMPLATE = r'''<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>__TITLE__</title>
  <style>
    :root{color-scheme:dark;--bg:#111315;--panel:#191c1f;--line:#30353a;--text:#ece9e2;--muted:#9ca3a8;--accent:#e7b35a}
    *{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:14px/1.45 Inter,ui-sans-serif,system-ui,sans-serif;overflow:hidden}
    header{height:68px;display:flex;align-items:center;gap:18px;padding:0 24px;border-bottom:1px solid var(--line);background:#151719}
    h1{font:600 18px/1.2 Georgia,serif;margin:0;white-space:nowrap}h1 span{color:var(--accent)}
    .views{display:flex;gap:5px}.views button,.filter{border:1px solid transparent;background:transparent;color:var(--muted);padding:8px 11px;border-radius:7px;cursor:pointer}
    .views button.active,.views button:hover{color:var(--text);background:#262a2e;border-color:#363b40}
    .search{margin-left:auto;position:relative}.search input{width:260px;background:#202428;border:1px solid #353a3f;color:var(--text);border-radius:8px;padding:9px 12px 9px 34px;outline:none}.search:before{content:'⌕';position:absolute;left:12px;top:5px;font-size:21px;color:var(--muted)}
    main{--left-width:210px;--right-width:330px;display:grid;grid-template-columns:var(--left-width) 6px minmax(240px,1fr) 6px var(--right-width);height:calc(100vh - 68px)}aside{background:var(--panel);padding:20px;overflow:auto}.details{border-right:0}.splitter{position:relative;background:#151719;cursor:col-resize;z-index:3}.splitter:after{content:'';position:absolute;inset:0 2px;background:#30353a;transition:background .15s}.splitter:hover:after,.splitter.active:after{background:var(--accent)}body.resizing{cursor:col-resize;user-select:none}
    h2{font:600 12px/1.2 ui-monospace,monospace;text-transform:uppercase;letter-spacing:.11em;color:var(--muted);margin:0 0 14px}.filter{display:flex;width:100%;align-items:center;gap:9px;text-align:left;margin:2px 0}.filter.active{background:#272b2f;color:var(--text)}.dot{width:9px;height:9px;border-radius:50%}.count{margin-left:auto;color:#737b82;font:12px ui-monospace,monospace}
    #stage{position:relative;overflow:hidden;background-image:radial-gradient(#292d30 1px,transparent 1px);background-size:24px 24px}.hint{position:absolute;left:16px;bottom:14px;color:#737b82;font-size:12px;background:#151719d9;padding:6px 9px;border-radius:6px}
    svg{width:100%;height:100%;cursor:grab}svg.dragging{cursor:grabbing}.edge{fill:none;stroke:#51575c;stroke-width:1.2;opacity:.65}.edge-label{fill:#aeb1b4;font-size:10px;cursor:help;text-decoration:underline dotted #777}.node rect{stroke-width:1.5;rx:8;filter:drop-shadow(0 3px 5px #0005)}.node text{fill:#f4f1e9;font-size:12px;pointer-events:none}.node .kind{fill:#aeb4b8;font-size:9px;text-transform:uppercase}.column-header{fill:#9ca3a8;font:600 11px ui-monospace,monospace;text-transform:uppercase;letter-spacing:.08em}.node.dim,.edge.dim,.edge-label.dim{opacity:.07}.node.selected rect{stroke:#fff;stroke-width:2.5}.node{cursor:pointer}
    .empty{color:var(--muted);margin-top:40px}.badge{display:inline-block;padding:3px 7px;border-radius:5px;background:#292d31;color:#bcc2c6;font:10px ui-monospace,monospace;text-transform:uppercase}.details h3{font:600 20px Georgia,serif;margin:12px 0 20px;overflow-wrap:anywhere}.row{padding:10px 0;border-top:1px solid #2b3034}.row label{display:block;color:#777f84;font-size:11px;text-transform:uppercase;letter-spacing:.06em;margin-bottom:4px}.row div{overflow-wrap:anywhere;white-space:pre-wrap}.source{color:#e0b66e;font-family:ui-monospace,monospace;font-size:12px}.relation{display:block;width:100%;border:0;background:transparent;color:#d8dde0;text-align:left;padding:5px 0;cursor:pointer}.relation:hover{color:var(--accent)}.glossary-term{position:relative;font-weight:800;color:#f0c56f;text-decoration:underline dotted currentColor 2px;text-underline-offset:3px;cursor:help;outline:none}.glossary-product{color:#92c9ec}.glossary-term:after{content:attr(data-definition);display:none;position:fixed;z-index:20;width:min(340px,calc(100vw - 32px));padding:10px 12px;border:1px solid #806b42;border-radius:7px;background:#24211b;color:#f1ece1;font-weight:400;font-size:12px;line-height:1.45;text-transform:none;letter-spacing:normal;white-space:normal;box-shadow:0 8px 24px #000b;pointer-events:none}.glossary-product:after{border-color:#52768d}.glossary-term:hover:after,.glossary-term:focus:after{display:block;left:var(--tip-x,16px);top:var(--tip-y,16px)}.glossary-hint{display:block;margin-top:12px;color:#8f969a;font-size:12px}.application{width:100%;border:1px solid #363c41;border-radius:7px;background:#22262a;color:#edf0f1;text-align:left;padding:9px 10px;margin:4px 0;cursor:pointer}.application:hover,.application.open{border-color:var(--accent)}.application-detail{display:none;margin:0 3px 10px;padding:8px 10px;border-left:2px solid #4c5358;color:#cbd0d3;font-size:12px}.application-detail.open{display:block}.application-detail b{display:block;color:#848c91;font-size:10px;letter-spacing:.08em;margin:8px 0 3px}.application-result{border:0;background:transparent;color:var(--accent);padding:0;cursor:pointer;text-align:left}.stats{margin:16px 0 25px;color:var(--muted)}
    @media(max-width:900px){main{--left-width:170px;grid-template-columns:var(--left-width) 6px 1fr}.details{position:absolute;right:0;top:68px;width:var(--right-width);height:calc(100vh - 68px);box-shadow:-10px 0 30px #0008}.splitter-right{display:none}.search input{width:180px}}
  </style>
</head>
<body>
<header><h1><span>Spec</span> Explorer · <b id="product"></b></h1><nav class="views"></nav><div class="search"><input id="search" placeholder="Knoten suchen …"></div></header>
<main id="main"><aside><h2>Elemente</h2><div id="filters"></div><div class="stats" id="stats"></div><h2>Legende</h2><small style="color:var(--muted)">Klicken: Details und Nachbarn<br>Doppelklicken: Teilgraph fokussieren<br>Mausrad: Zoomen · Ziehen: Verschieben</small><span class="glossary-hint"><span class="glossary-term" tabindex="0" data-definition="SpecForge-Begriff · Fachbegriff aus der SpecForge Academy.">SpecForge-Begriff</span><br><span class="glossary-term glossary-product" tabindex="0" data-definition="Produktbegriff · Fachbegriff aus der Domäne des konkreten Produkts.">Produktbegriff</span><br>Hovern für Erklärung</span></aside><div class="splitter splitter-left" data-resize="left" title="Linken Bereich vergrößern oder verkleinern"></div><section id="stage"><svg id="graph"><g id="viewport"><g id="edges"></g><g id="nodes"></g></g></svg><div class="hint">Nur fachlich relevante Fakten werden dargestellt.</div></section><div class="splitter splitter-right" data-resize="right" title="Rechten Bereich vergrößern oder verkleinern"></div><aside class="details" id="details"><div class="empty">Wähle einen Knoten, um Bedeutung, Herkunft und Beziehungen zu sehen.</div></aside></main>
<script id="graph-data" type="application/json">__GRAPH_DATA__</script>
<script>
const data=JSON.parse(document.getElementById('graph-data').textContent), byId=new Map(data.nodes.map(n=>[n.id,n]));
document.getElementById('product').textContent=data.product.id+'@'+data.product.version;
const views={
  'Trace':['fact','rule','requirement','operation','pattern','verification'],
  'Produkt':['product','entity','field','operation','classification','requirement'],
  'Pakete':['product','package'],
  'Knowledge':['product','package','classification','rule','requirement','pattern','verification'],
  'Implementierung':['operation','requirement','pattern','verification','artifact']
};
let activeView='Trace', enabled=new Set(views.Trace), selected=null, query='', focusIds=null, transform={x:20,y:20,k:1};
const svg=document.getElementById('graph'), viewport=document.getElementById('viewport'), edgeLayer=document.getElementById('edges'), nodeLayer=document.getElementById('nodes');
const kinds=[...new Set(data.nodes.map(n=>n.kind))];
function esc(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
const glossaryTerms=Object.keys(data.glossary||{}),glossaryPattern=glossaryTerms.length?new RegExp(`(^|[^\\p{L}\\p{N}_])(${glossaryTerms.map(term=>term.replace(/[.*+?^${}()|[\\]\\]/g,'\\$&')).join('|')})(?=$|[^\\p{L}\\p{N}_])`,'giu'):null;
function glossaryText(value){const safe=esc(value);if(!glossaryPattern)return safe;return safe.replace(glossaryPattern,(match,prefix,term)=>{const key=glossaryTerms.find(key=>key.toLocaleLowerCase()===term.toLocaleLowerCase()),kind=data.glossaryKinds[key],level=kind==='product'?'Produktbegriff':'SpecForge-Begriff';return `${prefix}<span class="glossary-term glossary-${kind}" tabindex="0" data-definition="${esc(`${level} · ${data.glossary[key]}`)}">${term}</span>`})}
function relationshipText(label){const definition=data.relationshipGlossary[label];return definition?`<span class="glossary-term" tabindex="0" data-definition="${esc(`Beziehung · ${definition}`)}">${esc(label)}</span>`:esc(label)}
function positionGlossary(root=document){root.querySelectorAll('.glossary-term').forEach(el=>{const place=()=>{const box=el.getBoundingClientRect();el.style.setProperty('--tip-x',`${Math.min(innerWidth-356,Math.max(16,box.left))}px`);el.style.setProperty('--tip-y',`${Math.min(innerHeight-120,box.bottom+8)}px`)};el.onmouseenter=place;el.onfocus=place})}
function visible(n){return enabled.has(n.kind)&&(!n.definition||activeView==='Knowledge')&&(!focusIds||focusIds.has(n.id))&&(!query||(`${n.label} ${n.kind} ${n.source} ${JSON.stringify(n.details)}`).toLowerCase().includes(query))}
function viewButtons(){const nav=document.querySelector('.views');nav.innerHTML=Object.keys(views).map(v=>`<button class="${v===activeView?'active':''}" data-view="${v}">${v}</button>`).join('');nav.querySelectorAll('button').forEach(b=>b.onclick=()=>{activeView=b.dataset.view;enabled=new Set(views[activeView]);selected=null;focusIds=null;viewButtons();filters();render()})}
function filters(){const counts=Object.fromEntries(kinds.map(k=>[k,data.nodes.filter(n=>n.kind===k&&(!n.definition||activeView==='Knowledge')).length]));document.getElementById('filters').innerHTML=kinds.map(k=>`<button class="filter ${enabled.has(k)?'active':''}" data-kind="${k}"><i class="dot" style="background:${data.colors[k]}"></i>${k}<span class="count">${counts[k]}</span></button>`).join('');document.querySelectorAll('.filter').forEach(b=>b.onclick=()=>{enabled.has(b.dataset.kind)?enabled.delete(b.dataset.kind):enabled.add(b.dataset.kind);filters();render()})}
function layout(nodes){if(activeView==='Pakete'){const roles=['product','policy','domain','integration','implementation'],positions=new Map();roles.forEach((role,column)=>nodes.filter(n=>role==='product'?n.kind==='product':n.kind==='package'&&n.details.package_kind===role).sort((a,b)=>a.label.localeCompare(b.label)).forEach((n,i)=>positions.set(n.id,{x:30+column*205,y:65+i*86})));return positions}const columns=['product','package','entity','field','classification','fact','rule','operation','requirement','pattern','verification','artifact'];const grouped=new Map(columns.map(k=>[k,[]]));nodes.forEach(n=>(grouped.get(n.kind)||grouped.get('artifact')).push(n));const positions=new Map();let x=30;columns.forEach(kind=>{const list=grouped.get(kind)||[];if(!list.length)return;list.sort((a,b)=>a.label.localeCompare(b.label));list.forEach((n,i)=>positions.set(n.id,{x,y:55+i*86}));x+=205});return positions}
function packageHeaders(){if(activeView!=='Pakete')return '';return ['Produkt','Policy','Domäne','Integration','Implementierung'].map((label,i)=>`<text class="column-header" x="${30+i*205}" y="28">${label}</text>`).join('')}
const packageRoleLabels={policy:'Policy-Paket',domain:'Domänenpaket',integration:'Integrationspaket',implementation:'Implementierungspaket',legacy:'Knowledge-Paket'};
function nodeKindLabel(n){if(activeView!=='Pakete')return n.kind;if(n.kind==='product')return 'Produkt';return packageRoleLabels[n.details.package_kind]||'Knowledge-Paket'}
function nodeDisplayLabel(n){if(activeView!=='Pakete')return n.label;if(n.kind==='product')return `${n.label} · Produkt`;return `${n.label} · ${packageRoleLabels[n.details.package_kind]||'Paket'}`}
function render(){const nodes=data.nodes.filter(visible), ids=new Set(nodes.map(n=>n.id)), edges=data.edges.filter(e=>ids.has(e.source)&&ids.has(e.target)), pos=layout(nodes);edgeLayer.innerHTML=edges.map(e=>{const a=pos.get(e.source),b=pos.get(e.target),x1=a.x+156,y1=a.y+25,x2=b.x,y2=b.y+25,m=(x1+x2)/2,definition=data.relationshipGlossary[e.label]||e.label;return `<g class="edge-group" data-source="${esc(e.source)}" data-target="${esc(e.target)}"><path class="edge" d="M${x1},${y1} C${m},${y1} ${m},${y2} ${x2},${y2}"/><text class="edge-label" tabindex="0" x="${m}" y="${(y1+y2)/2-4}" text-anchor="middle">${esc(e.label)}<title>${esc(definition)}</title></text></g>`}).join('');nodeLayer.innerHTML=packageHeaders()+nodes.map(n=>{const p=pos.get(n.id),fullLabel=nodeDisplayLabel(n),label=fullLabel.length>22?fullLabel.slice(0,21)+'…':fullLabel,kind=nodeKindLabel(n);return `<g class="node" data-id="${esc(n.id)}" transform="translate(${p.x},${p.y})"><rect width="156" height="50" fill="${data.colors[n.kind]}26" stroke="${data.colors[n.kind]}"/><text class="kind" x="10" y="16">${esc(kind)}</text><text x="10" y="35">${esc(label)}</text><title>${esc(fullLabel)}</title></g>`}).join('');document.getElementById('stats').textContent=`${nodes.length} Knoten · ${edges.length} Beziehungen`;nodeLayer.querySelectorAll('.node').forEach(el=>{el.onclick=()=>select(el.dataset.id);el.ondblclick=()=>focus(el.dataset.id)});applyTransform();if(selected&&ids.has(selected))highlight()}
function clearSelection(){selected=null;document.querySelectorAll('.node,.edge-group').forEach(el=>el.classList.remove('selected','dim'));document.getElementById('details').innerHTML='<div class="empty">Wähle einen Knoten, um Bedeutung, Herkunft und Beziehungen zu sehen.</div>'}
function formatDetail(value){if(Array.isArray(value)&&value.every(item=>typeof item==='string'))return value.map(item=>`• ${glossaryText(item)}`).join('<br>');return glossaryText(typeof value==='object'?JSON.stringify(value,null,2):value)}
function detailRow(label,value,extraClass=''){return `<div class="row ${extraClass}"><label>${glossaryText(label)}</label><div>${formatDetail(value)}</div></div>`}
function renderRuleLogic(details){return `<div class="rule-logic">${detailRow('WENN',details.wenn)}${detailRow('DANN',details.dann)}</div>`}
function renderApplications(applications){if(!applications?.length)return '';return `<div class="row"><label>Ausgelöst für</label><div>${applications.map((app,index)=>`<button class="application" data-application="${index}">${esc(app.label)}</button><div class="application-detail" data-application-detail="${index}"><b>WARUM?</b>${formatDetail(app.why)}<b>BINDUNGEN</b>${formatDetail(app.bindings)}<b>ERGEBNIS</b><button class="application-result" data-related="${esc(app.requirement)}">${formatDetail(app.result)}</button></div>`).join('')}</div></div>`}
function select(id){if(selected===id){clearSelection();return}selected=id;highlight();const n=byId.get(id),related=data.edges.filter(e=>e.source===id||e.target===id),isRule=n.kind==='rule',entries=Object.entries(n.details).filter(([key])=>!['content_hash','applications','wenn','dann'].includes(key)),contentHash=n.details.content_hash,metadata=entries.map(([k,v])=>detailRow(k.replaceAll('_',' '),v)).join(''),source=n.source?`<div class="row"><label>Quelle</label><div class="source">${esc(n.source)}</div></div>`:'';let rows=isRule?renderRuleLogic(n.details)+renderApplications(n.details.applications)+metadata+source:source+metadata+renderApplications(n.details.applications);rows+=`<div class="row"><label>Beziehungen</label><div>${related.map(e=>{const other=e.source===id?e.target:e.source,otherNode=byId.get(other),label=otherNode?.definition?`${otherNode.label} — ${otherNode.details.statement}`:otherNode?nodeDisplayLabel(otherNode):other;return `<button class="relation" data-related="${esc(other)}">${e.source===id?'→':'←'} ${relationshipText(e.label)} · ${glossaryText(label)}</button>`}).join('')||'—'}</div></div>`;if(contentHash!==undefined)rows+=`<div class="row"><label>Content Hash</label><div>${formatDetail(contentHash)}</div></div>`;const details=document.getElementById('details');details.innerHTML=`<span class="badge">${glossaryText(n.definition?'Requirement Definition':nodeKindLabel(n))}</span><h3>${glossaryText(nodeDisplayLabel(n))}</h3>${rows}`;details.querySelectorAll('[data-related]').forEach(el=>el.onclick=()=>navigate(el.dataset.related));details.querySelectorAll('[data-application]').forEach(el=>el.onclick=()=>{el.classList.toggle('open');details.querySelector(`[data-application-detail="${el.dataset.application}"]`).classList.toggle('open')});positionGlossary(details)}
function navigate(id){const n=byId.get(id);if(n?.definition&&activeView!=='Knowledge'){activeView='Knowledge';enabled=new Set(views.Knowledge);focusIds=null;viewButtons();filters();render()}select(id)}
function highlight(){const neighbours=new Set([selected]);data.edges.forEach(e=>{if(e.source===selected)neighbours.add(e.target);if(e.target===selected)neighbours.add(e.source)});document.querySelectorAll('.node').forEach(el=>{el.classList.toggle('selected',el.dataset.id===selected);el.classList.toggle('dim',!neighbours.has(el.dataset.id))});document.querySelectorAll('.edge-group').forEach(el=>el.classList.toggle('dim',el.dataset.source!==selected&&el.dataset.target!==selected))}
function focus(id){focusIds=new Set([id]);data.edges.forEach(e=>{if(e.source===id)focusIds.add(e.target);if(e.target===id)focusIds.add(e.source)});query='';document.getElementById('search').value='';render()}
document.getElementById('search').oninput=e=>{query=e.target.value.trim().toLowerCase();selected=null;render()};
let drag=null,suppressCanvasClick=false;svg.onpointerdown=e=>{if(e.target.closest('.node'))return;drag={x:e.clientX,y:e.clientY,ox:transform.x,oy:transform.y,moved:false};svg.setPointerCapture(e.pointerId);svg.classList.add('dragging')};svg.onpointermove=e=>{if(drag){drag.moved=drag.moved||Math.hypot(e.clientX-drag.x,e.clientY-drag.y)>3;transform.x=drag.ox+e.clientX-drag.x;transform.y=drag.oy+e.clientY-drag.y;applyTransform()}};svg.onpointerup=()=>{suppressCanvasClick=Boolean(drag?.moved);drag=null;svg.classList.remove('dragging')};svg.onclick=e=>{if(suppressCanvasClick){suppressCanvasClick=false;return}if(!e.target.closest('.node'))clearSelection()};svg.onwheel=e=>{e.preventDefault();transform.k=Math.max(.25,Math.min(2.2,transform.k*(e.deltaY<0?1.12:.89)));applyTransform()};function applyTransform(){viewport.setAttribute('transform',`translate(${transform.x},${transform.y}) scale(${transform.k})`)}
const main=document.getElementById('main');document.querySelectorAll('[data-resize]').forEach(handle=>handle.onpointerdown=e=>{const side=handle.dataset.resize,startX=e.clientX,startWidth=parseFloat(getComputedStyle(main).getPropertyValue(`--${side}-width`));handle.setPointerCapture(e.pointerId);handle.classList.add('active');document.body.classList.add('resizing');handle.onpointermove=move=>{const delta=move.clientX-startX,width=side==='left'?startWidth+delta:startWidth-delta,min=side==='left'?150:240,max=side==='left'?420:600;main.style.setProperty(`--${side}-width`,`${Math.max(min,Math.min(max,width))}px`)};handle.onpointerup=()=>{handle.onpointermove=null;handle.classList.remove('active');document.body.classList.remove('resizing')}});
viewButtons();filters();render();positionGlossary();
</script></body></html>
'''
