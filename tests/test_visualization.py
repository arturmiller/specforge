from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import tempfile

from typer.testing import CliRunner

from specforge.cli import app
from specforge.visualization import (
    RELATIONSHIP_GLOSSARY,
    build_graph,
    create_visualization,
    load_glossary,
    load_product_glossary,
)


ROOT = Path(__file__).resolve().parents[1]
PRODUCT = "products/calendar"


def test_graph_connects_derivation_to_implementation_and_verification() -> None:
    graph = build_graph(ROOT, PRODUCT)
    nodes = {node["id"] for node in graph["nodes"]}
    edges = {(edge["source"], edge["target"], edge["label"]) for edge in graph["edges"]}

    assert "fact:fact-dab5b18462a2d56b" in nodes
    assert "rule:security/authenticated-personal-data" in nodes
    assert "requirement:SEC-001@operation.read_event" in nodes
    assert "pattern:fastapi/bearer-ownership" in nodes
    assert "verification:TEST-SEC-001" in nodes
    assert (
        "rule:security/authenticated-personal-data",
        "requirement:SEC-001@operation.read_event",
        "derives",
    ) in edges
    assert (
        "requirement:SEC-001@operation.read_event",
        "pattern:fastapi/bearer-ownership",
        "implemented by",
    ) in edges


def test_rule_explains_condition_result_and_concrete_applications() -> None:
    graph = build_graph(ROOT, PRODUCT)
    rule = next(
        node
        for node in graph["nodes"]
        if node["id"] == "rule:security/authenticated-personal-data"
    )

    assert rule["label"] == "Authentifizierung für personenbezogene Daten"
    assert rule["details"]["technical_id"] == "security/authenticated-personal-data"
    assert rule["details"]["wenn"] == [
        "Operation bearbeitet Ressource",
        "UND Ressource enthält die Klassifikation PersonalData",
    ]
    assert rule["details"]["dann"] == [
        "SEC-001 gilt für die gebundene Operation",
        "authentication = required",
    ]
    read_application = next(
        application
        for application in rule["details"]["applications"]
        if application["label"] == "read_event → Event"
    )
    assert read_application["bindings"] == [
        "$operation → operation.read_event",
        "$resource → Event",
    ]
    assert read_application["why"] == [
        "operation.read_event bearbeitet Event",
        "Event enthält die Klassifikation PersonalData",
    ]
    assert read_application["result"] == [
        "SEC-001@operation.read_event",
        "authentication = required",
    ]


def test_rule_conditions_make_and_or_not_semantics_explicit() -> None:
    graph = build_graph(ROOT, PRODUCT)
    rules = {node["id"]: node for node in graph["nodes"] if node["kind"] == "rule"}

    assert rules["rule:calendar/event-time-interval"]["details"]["wenn"] == [
        "Operation bearbeitet Event",
        "UND (Operation hat die Aktion create ODER Operation hat die Aktion update)",
    ]
    assert rules["rule:privacy/minimize-personal-data-response"]["details"]["wenn"][-1] == (
        "UND (Operation hat die Aktion create ODER Operation hat die Aktion read ODER Operation hat die Aktion update)"
    )


def test_academy_glossaries_are_embedded_in_the_explorer() -> None:
    glossary = load_glossary(ROOT)
    product_glossary = load_product_glossary(ROOT, PRODUCT)
    graph = build_graph(ROOT, PRODUCT)

    assert glossary["Requirement Definition"].startswith("Die allgemeine")
    assert glossary["Control"].startswith("Die benannte Eigenschaft")
    assert glossary["Rule"].startswith("Eine maschinenlesbare Wenn-dann-Regel")
    assert glossary["Operation"].startswith("Eine ausführbare Aktion")
    assert product_glossary["Event"].startswith("Eine fachliche Entität")
    assert graph["glossary"] == {**glossary, **product_glossary}
    assert graph["glossaryKinds"]["Rule"] == "academy"
    assert graph["glossaryKinds"]["Event"] == "product"


def test_glossary_terms_are_highlighted_with_accessible_tooltips() -> None:
    html = create_visualization(ROOT, PRODUCT).read_text(encoding="utf-8")

    assert 'class="glossary-term glossary-${kind}" tabindex="0"' in html
    assert "${level} · ${data.glossary[key]}" in html
    assert ".glossary-term:hover:after,.glossary-term:focus:after" in html
    assert "positionGlossary(details)" in html
    assert "glossaryText(n.definition?'Requirement Definition':nodeKindLabel(n))" in html
    assert "<label>${glossaryText(label)}</label>" in html
    assert "SpecForge-Begriff</span>" in html
    assert "Produktbegriff</span>" in html


def test_rule_renders_when_and_then_as_one_consecutive_block() -> None:
    html = create_visualization(ROOT, PRODUCT).read_text(encoding="utf-8")
    script = html.rsplit("<script>", 1)[1].split("</script>", 1)[0]
    rule_logic = script.split("function renderRuleLogic", 1)[1].split(
        "function renderApplications", 1
    )[0]

    assert "detailRow('WENN',details.wenn)}${detailRow('DANN',details.dann)" in rule_logic
    assert "renderRuleLogic(n.details)+renderApplications" in script


def test_knowledge_requirement_definition_contains_explanation() -> None:
    graph = build_graph(ROOT, PRODUCT)
    definition = next(
        node for node in graph["nodes"] if node["id"] == "requirement-definition:DATA-001"
    )

    assert definition["definition"] is True
    assert definition["details"]["statement"] == "Event end must be later than event start."
    assert definition["details"]["expectation"] == "event_time_interval = end_after_start"
    assert definition["details"]["verifications"][0]["id"] == "TEST-DATA-001"


def test_package_requirements_are_expressed_as_relationships() -> None:
    graph = build_graph(ROOT, PRODUCT)
    package = next(node for node in graph["nodes"] if node["id"] == "package:calendar")
    edges = {
        (edge["source"], edge["target"], edge["label"])
        for edge in graph["edges"]
    }

    assert "requirements" not in package["details"]
    assert (
        "package:calendar",
        "requirement-definition:PRODUCT-001",
        "contains",
    ) in edges


def test_package_roles_and_integration_are_explicit() -> None:
    graph = build_graph(ROOT, PRODUCT)
    packages = {
        node["id"]: node for node in graph["nodes"] if node["kind"] == "package"
    }
    edges = {
        (edge["source"], edge["target"], edge["label"])
        for edge in graph["edges"]
    }

    assert packages["package:calendar"]["details"]["package_kind"] == "domain"
    assert packages["package:calendar-fastapi-react"]["details"]["package_kind"] == "integration"
    assert packages["package:fastapi-react"]["details"]["package_kind"] == "implementation"
    assert packages["package:privacy"]["details"]["package_kind"] == "policy"
    assert ("package:calendar-fastapi-react", "package:calendar", "binds domain") in edges
    assert ("package:calendar-fastapi-react", "package:fastapi-react", "binds implementation") in edges


def test_explorer_has_a_package_role_view() -> None:
    html = create_visualization(ROOT, PRODUCT).read_text(encoding="utf-8")

    assert "'Pakete':['product','package']" in html
    assert "['Produkt','Policy','Domäne','Integration','Implementierung']" in html
    assert "n.details.package_kind===role" in html
    assert "domain:'Domänenpaket'" in html
    assert "integration:'Integrationspaket'" in html
    assert "implementation:'Implementierungspaket'" in html
    assert "`${n.label} · Produkt`" in html
    assert "`${n.label} · ${packageRoleLabels[n.details.package_kind]||'Paket'}`" in html


def test_every_relationship_has_a_hover_explanation() -> None:
    graph = build_graph(ROOT, PRODUCT)
    labels = {edge["label"] for edge in graph["edges"]}

    assert labels <= RELATIONSHIP_GLOSSARY.keys()
    assert RELATIONSHIP_GLOSSARY["defines"].startswith("Das Produkt definiert")
    assert RELATIONSHIP_GLOSSARY["offers"].startswith("Das Produkt stellt")
    assert RELATIONSHIP_GLOSSARY["depends on"].startswith("Das Produkt lädt")

    html = create_visualization(ROOT, PRODUCT).read_text(encoding="utf-8")
    assert 'class="edge-label" tabindex="0"' in html
    assert "<title>${esc(definition)}</title>" in html
    assert "relationshipText(e.label)" in html


def test_visualization_is_self_contained_and_deterministic() -> None:
    first = create_visualization(ROOT, PRODUCT)
    first_bytes = first.read_bytes()
    second = create_visualization(ROOT, PRODUCT)

    assert second.read_bytes() == first_bytes
    html = first.read_text(encoding="utf-8")
    assert "https://" not in html
    assert "Spec Explorer" in html
    payload = html.split('<script id="graph-data" type="application/json">', 1)[1].split("</script>", 1)[0]
    assert json.loads(payload)["product"]["id"] == "calendar"


def test_visualization_javascript_is_valid() -> None:
    node = shutil.which("node")
    if node is None:
        return
    html = create_visualization(ROOT, PRODUCT).read_text(encoding="utf-8")
    script = html.rsplit("<script>", 1)[1].split("</script>", 1)[0]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".js", encoding="utf-8", delete=False) as handle:
        handle.write(script)
        script_path = Path(handle.name)
    try:
        result = subprocess.run(
            [node, "--check", script_path], text=True, capture_output=True, check=False
        )
    finally:
        script_path.unlink()

    assert result.returncode == 0, result.stderr


def test_nodes_are_not_captured_by_canvas_panning() -> None:
    html = create_visualization(ROOT, PRODUCT).read_text(encoding="utf-8")
    script = html.rsplit("<script>", 1)[1].split("</script>", 1)[0]

    pointer_handler = script.split("svg.onpointerdown=e=>", 1)[1].split(";svg.onpointermove", 1)[0]

    assert "if(e.target.closest('.node'))return" in pointer_handler
    assert pointer_handler.index("closest('.node')") < pointer_handler.index("setPointerCapture")


def test_selection_can_be_cleared_without_treating_a_drag_as_a_click() -> None:
    html = create_visualization(ROOT, PRODUCT).read_text(encoding="utf-8")
    script = html.rsplit("<script>", 1)[1].split("</script>", 1)[0]

    assert "if(selected===id){clearSelection();return}" in script
    assert "if(!e.target.closest('.node'))clearSelection()" in script
    assert "suppressCanvasClick=Boolean(drag?.moved)" in script


def test_related_knowledge_nodes_are_navigable() -> None:
    html = create_visualization(ROOT, PRODUCT).read_text(encoding="utf-8")
    script = html.rsplit("<script>", 1)[1].split("</script>", 1)[0]

    assert 'data-related="${esc(other)}"' in script
    assert "el.onclick=()=>navigate(el.dataset.related)" in script
    assert "n?.definition&&activeView!=='Knowledge'" in script
    assert "`${otherNode.label} — ${otherNode.details.statement}`" in script


def test_content_hash_is_rendered_last() -> None:
    html = create_visualization(ROOT, PRODUCT).read_text(encoding="utf-8")
    script = html.rsplit("<script>", 1)[1].split("</script>", 1)[0]

    select_function = script.split("function select(id)", 1)[1].split("function navigate", 1)[0]

    assert "filter(([key])=>!['content_hash','applications','wenn','dann'].includes(key))" in select_function
    assert select_function.index("<label>Beziehungen</label>") < select_function.index(
        "<label>Content Hash</label>"
    )


def test_sidebars_have_mouse_draggable_splitters() -> None:
    html = create_visualization(ROOT, PRODUCT).read_text(encoding="utf-8")

    assert 'data-resize="left"' in html
    assert 'data-resize="right"' in html
    assert "handle.setPointerCapture(e.pointerId)" in html
    assert "main.style.setProperty(`--${side}-width`" in html


def test_visualize_cli_writes_generated_html(monkeypatch, tmp_path: Path) -> None:
    # The command resolves paths from the repository root, just like all other CLI commands.
    monkeypatch.chdir(ROOT)
    result = CliRunner().invoke(app, ["visualize", PRODUCT])

    assert result.exit_code == 0, result.output
    assert (ROOT / "generated/calendar/visualization/index.html").exists()
