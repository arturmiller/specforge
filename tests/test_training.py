from pathlib import Path

from specforge.training import build_training_scenario


ROOT = Path(__file__).parents[1]


def test_training_scenario_is_built_from_current_semantic_model() -> None:
    destination = build_training_scenario(ROOT)
    rendered = destination.read_text(encoding="utf-8")

    assert "PRIVACY-001@operation.read_event" in rendered
    assert "SEC-002@operation.update_event" in rendered
    assert "privacy/minimize-personal-data-response" in rendered
    assert "security/owned-resources" in rendered
    assert '"responseFields": [' in rendered
    assert '"hashAlgorithm": "rdfc-1.0+sha256"' in rendered
    assert "relationshipGlossary" in rendered
    assert "Zeigt für jede abgeleitete Requirement Instance" in rendered


def test_training_ui_has_one_hash_bound_journey_and_independent_final_case() -> None:
    source = (ROOT / "training-prototype" / "app.js").read_text(encoding="utf-8")
    html = (ROOT / "training-prototype" / "index.html").read_text(encoding="utf-8")

    assert source.count('title:"') == 8
    assert "specforge-training:${data.scenarioHash}" in source
    assert "localStorage.setItem" in source
    assert "data-check-final" in source
    assert "state.finalPassed=true" in source
    assert 'status.id="interaction-status"' in source
    assert 'status.hidden=false' in source
    assert 'classes:["product","product","product","product"]' in source
    assert "prefers-reduced-motion" in (ROOT / "training-prototype" / "styles.css").read_text(encoding="utf-8")
    assert "prototype-switcher" not in html
    assert "fonts.googleapis.com" not in html
    assert "RIF Core ist das normative gespeicherte Rule-Format" in source


def test_every_gated_interaction_has_visible_feedback() -> None:
    source = (ROOT / "training-prototype" / "app.js").read_text(encoding="utf-8")

    for control in ("data-check-classify", "data-check-rule", "data-check-order", "data-check-final"):
        assert source.count(control) >= 2, f"{control} must be rendered and wired"
    assert "Noch nicht ganz." in source
    assert "Binde alle Variablen" in source
    assert "Die Reihenfolge stimmt noch nicht" in source
    assert "Abschlussfall noch nicht bestanden" in source
    assert "interaction-status" in source
