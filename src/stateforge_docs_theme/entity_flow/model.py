"""Load and validate versioned entity-flow declarations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from stateforge_docs_theme.declaration import (
    DeclarationError,
    exact_keys,
    identifier,
    identifier_list,
    list_value,
    load_versioned_yaml,
    mapping,
    require_known_entities,
    text,
)

SCHEMA_ID = "stateforge.docs/entity-flow/v1"
MAX_DECLARATION_BYTES = 128 * 1024

EntityFlowDeclarationError = DeclarationError

_BRANDS = frozenset({"none", "service", "stateforge"})
_ACCENTS = frozenset({"neutral", "service", "systemd", "provider", "agent"})
_TONES = frozenset({"normal", "success", "warning", "failure"})


def load_entity_flow(path: Path, *, docs_dir: Path) -> dict[str, Any]:
    """Load one entity flow and derive its documentation version from its path."""
    declaration, documentation_version = load_versioned_yaml(
        path,
        docs_dir=docs_dir,
        maximum_bytes=MAX_DECLARATION_BYTES,
        source_name="entity-flow",
    )
    _validate_declaration(declaration)
    return {**declaration, "documentation_version": documentation_version}


def _validate_declaration(declaration: dict[str, Any]) -> None:
    exact_keys(
        declaration,
        required={"schema", "flow", "title", "entities", "steps"},
        optional={"summary", "autoplay"},
        context="entity-flow declaration",
    )
    if text(declaration["schema"], "schema") != SCHEMA_ID:
        raise EntityFlowDeclarationError(f"schema must be {SCHEMA_ID!r}")
    identifier(declaration["flow"], "flow")
    text(declaration["title"], "title")
    if "summary" in declaration:
        text(declaration["summary"], "summary")
    if "autoplay" in declaration and not isinstance(declaration["autoplay"], bool):
        raise EntityFlowDeclarationError("autoplay must be a boolean")

    entities = list_value(declaration["entities"], "entities")
    if len(entities) < 2:
        raise EntityFlowDeclarationError("entities must contain at least two entries")
    entity_ids: set[str] = set()
    for index, value in enumerate(entities):
        entity_id = _validate_entity(value, f"entities[{index}]")
        if entity_id in entity_ids:
            raise EntityFlowDeclarationError(f"duplicate entity ID: {entity_id}")
        entity_ids.add(entity_id)

    steps = list_value(declaration["steps"], "steps")
    if not steps:
        raise EntityFlowDeclarationError("steps must not be empty")
    step_ids: set[str] = set()
    for index, value in enumerate(steps):
        step_id = _validate_step(value, f"steps[{index}]", entity_ids)
        if step_id in step_ids:
            raise EntityFlowDeclarationError(f"duplicate step ID: {step_id}")
        step_ids.add(step_id)


def _validate_entity(value: Any, context: str) -> str:
    entity = mapping(value, context)
    exact_keys(
        entity,
        required={"id", "label", "kind", "accent", "state"},
        optional={"brand", "description"},
        context=context,
    )
    entity_id = identifier(entity["id"], f"{context}.id")
    text(entity["label"], f"{context}.label")
    text(entity["kind"], f"{context}.kind")
    if "description" in entity:
        text(entity["description"], f"{context}.description")
    brand = identifier(entity.get("brand", "none"), f"{context}.brand")
    if brand not in _BRANDS:
        raise EntityFlowDeclarationError(
            f"{context}.brand must be one of {sorted(_BRANDS)}"
        )
    accent = identifier(entity["accent"], f"{context}.accent")
    if accent not in _ACCENTS:
        raise EntityFlowDeclarationError(
            f"{context}.accent must be one of {sorted(_ACCENTS)}"
        )
    _validate_state(entity["state"], f"{context}.state")
    return entity_id


def _validate_step(value: Any, context: str, entity_ids: set[str]) -> str:
    step = mapping(value, context)
    exact_keys(
        step,
        required={
            "id",
            "phase",
            "title",
            "detail",
            "active",
            "states",
            "transitions",
            "responsibility",
        },
        optional=set(),
        context=context,
    )
    step_id = identifier(step["id"], f"{context}.id")
    text(step["phase"], f"{context}.phase")
    text(step["title"], f"{context}.title")
    text(step["detail"], f"{context}.detail")
    active = identifier_list(step["active"], f"{context}.active")
    require_known_entities(active, entity_ids, f"{context}.active")

    states = mapping(step["states"], f"{context}.states")
    require_known_entities(set(states), entity_ids, f"{context}.states")
    for entity_id, state_value in states.items():
        _validate_state(state_value, f"{context}.states.{entity_id}")

    transitions = list_value(step["transitions"], f"{context}.transitions")
    for index, transition_value in enumerate(transitions):
        _validate_transition(
            transition_value,
            f"{context}.transitions[{index}]",
            entity_ids,
        )

    responsibility = mapping(
        step["responsibility"],
        f"{context}.responsibility",
    )
    exact_keys(
        responsibility,
        required={"entities", "label"},
        optional=set(),
        context=f"{context}.responsibility",
    )
    owners = identifier_list(
        responsibility["entities"],
        f"{context}.responsibility.entities",
    )
    if not owners:
        raise EntityFlowDeclarationError(
            f"{context}.responsibility.entities must not be empty"
        )
    require_known_entities(owners, entity_ids, f"{context}.responsibility.entities")
    text(responsibility["label"], f"{context}.responsibility.label")

    if not states and not transitions:
        raise EntityFlowDeclarationError(
            f"{context} must change entity state or carry a transition"
        )
    return step_id


def _validate_state(value: Any, context: str) -> None:
    state = mapping(value, context)
    exact_keys(
        state,
        required={"label", "value"},
        optional={"tone"},
        context=context,
    )
    text(state["label"], f"{context}.label")
    text(state["value"], f"{context}.value")
    tone = identifier(state.get("tone", "normal"), f"{context}.tone")
    if tone not in _TONES:
        raise EntityFlowDeclarationError(
            f"{context}.tone must be one of {sorted(_TONES)}"
        )


def _validate_transition(
    value: Any,
    context: str,
    entity_ids: set[str],
) -> None:
    transition = mapping(value, context)
    exact_keys(
        transition,
        required={"source", "target", "label"},
        optional={"tone"},
        context=context,
    )
    source = identifier(transition["source"], f"{context}.source")
    target = identifier(transition["target"], f"{context}.target")
    require_known_entities({source, target}, entity_ids, context)
    text(transition["label"], f"{context}.label")
    tone = identifier(transition.get("tone", "normal"), f"{context}.tone")
    if tone not in _TONES:
        raise EntityFlowDeclarationError(
            f"{context}.tone must be one of {sorted(_TONES)}"
        )
