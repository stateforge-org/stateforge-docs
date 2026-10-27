"""Render validated entity-flow declarations for the shared browser component."""

from __future__ import annotations

import html
import json
from typing import Any


def render_entity_flow(declaration: dict[str, Any]) -> str:
    """Render one interactive entity flow plus an accessible static fallback."""
    encoded = json.dumps(declaration, ensure_ascii=False, separators=(",", ":"))
    encoded = (
        encoded.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
    )
    return (
        '\n<div class="sf-entity-flow-host">\n'
        "<stateforge-entity-flow "
        f'data-documentation-version="{html.escape(declaration["documentation_version"])}">'
        '<script type="application/json" class="sf-entity-flow-data">'
        f"{encoded}</script>"
        f"{_render_fallback(declaration)}"
        "</stateforge-entity-flow>\n"
        "</div>\n"
    )


def _render_fallback(declaration: dict[str, Any]) -> str:
    entities = ", ".join(entity["label"] for entity in declaration["entities"])
    steps = "".join(
        "<li>"
        f"<strong>{html.escape(step['title'])}</strong> "
        f"{html.escape(step['detail'])}"
        "</li>"
        for step in declaration["steps"]
    )
    return (
        '<details class="sf-entity-flow-fallback">'
        f"<summary>{html.escape(declaration['title'])}</summary>"
        f"<p>{html.escape(entities)}</p>"
        f"<ol>{steps}</ol>"
        "</details>"
    )
