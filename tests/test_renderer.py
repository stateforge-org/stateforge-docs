from __future__ import annotations

from pathlib import Path

from stateforge_docs_theme.procedure.model import load_procedure
from stateforge_docs_theme.procedure.renderer import render_player

FIXTURE_DOCS = Path(__file__).parent / "fixtures/site/docs"
DECLARATION = FIXTURE_DOCS / "v0.1.0/procedures/bootstrap.yaml"


def test_renderer_embeds_derived_version_and_static_fallback() -> None:
    declaration = load_procedure(DECLARATION, docs_dir=FIXTURE_DOCS)

    rendered = render_player(declaration)

    assert 'data-documentation-version="v0.1.0"' in rendered
    assert '"documentation_version":"v0.1.0"' in rendered
    assert '<details class="sf-procedure-fallback">' in rendered
    assert "Publish the endpoint descriptor" in rendered


def test_renderer_selects_requested_scenario() -> None:
    declaration = load_procedure(DECLARATION, docs_dir=FIXTURE_DOCS)

    rendered = render_player(declaration, selected_scenario="incompatible")

    assert '"default_scenario":"incompatible"' in rendered
    assert "Reject incompatible versions" in rendered
