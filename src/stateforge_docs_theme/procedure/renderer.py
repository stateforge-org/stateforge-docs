"""Render validated procedure declarations for the shared browser player."""

from __future__ import annotations

import html
import json
from typing import Any


def render_player(
    declaration: dict[str, Any], *, selected_scenario: str | None = None
) -> str:
    """Render one interactive player plus a complete static fallback."""
    scenarios = declaration["scenarios"]
    scenario_id = selected_scenario or declaration.get("default_scenario")
    if scenario_id is None:
        scenario_id = next(iter(scenarios))
    if scenario_id not in scenarios:
        raise ValueError(f"unknown procedure scenario: {scenario_id}")

    payload = {**declaration, "default_scenario": scenario_id}
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    encoded = (
        encoded.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
    )
    fallback = _render_fallback(declaration, scenario_id)
    return (
        '\n<div class="sf-procedure-host">\n'
        "<stateforge-procedure-player "
        f'data-documentation-version="{html.escape(declaration["documentation_version"])}">'
        f'<script type="application/json" class="sf-procedure-data">{encoded}</script>'
        f"{fallback}"
        "</stateforge-procedure-player>\n"
        "</div>\n"
    )


def _render_fallback(declaration: dict[str, Any], scenario_id: str) -> str:
    scenario = declaration["scenarios"][scenario_id]
    steps = "".join(
        "<li>"
        f"<strong>{html.escape(step['title'])}</strong> "
        f"{html.escape(step['detail'])}"
        "</li>"
        for step in scenario["steps"]
    )
    return (
        '<details class="sf-procedure-fallback">'
        f"<summary>{html.escape(declaration['title'])}: "
        f"{html.escape(scenario['label'])}</summary>"
        f"<ol>{steps}</ol>"
        "</details>"
    )
