from __future__ import annotations

from pathlib import Path

from stateforge_docs_theme.entity_flow import load_entity_flow, render_entity_flow

FIXTURE_DOCS = Path(__file__).parent / "fixtures/site/docs"
DECLARATION = FIXTURE_DOCS / "v0.1.0/trigger-flow.yaml"


def test_entity_flow_renderer_embeds_data_and_static_fallback() -> None:
    declaration = load_entity_flow(DECLARATION, docs_dir=FIXTURE_DOCS)

    rendered = render_entity_flow(declaration)

    assert '<stateforge-entity-flow data-documentation-version="v0.1.0">' in rendered
    assert '"documentation_version":"v0.1.0"' in rendered
    assert '<details class="sf-entity-flow-fallback">' in rendered
    assert "Acknowledge the accepted trigger" in rendered
