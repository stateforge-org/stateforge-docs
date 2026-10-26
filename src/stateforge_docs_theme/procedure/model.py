"""Load and validate versioned procedure declarations."""

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
    text_list,
)

SCHEMA_ID = "stateforge.docs/procedure/v1"
MAX_DECLARATION_BYTES = 512 * 1024

_FORBIDDEN_VERSION_KEYS = frozenset(
    {"version", "protocol_version", "documentation_version"}
)
_ENTITY_KINDS = frozenset(
    {"process", "service", "resource", "storage", "external", "user"}
)
_TONES = frozenset({"normal", "success", "warning", "failure"})


ProcedureDeclarationError = DeclarationError


def load_procedure(path: Path, *, docs_dir: Path) -> dict[str, Any]:
    """Load one declaration and derive its documentation version from its path."""
    declaration, documentation_version = load_versioned_yaml(
        path,
        docs_dir=docs_dir,
        maximum_bytes=MAX_DECLARATION_BYTES,
        source_name="procedure",
    )
    forbidden = _FORBIDDEN_VERSION_KEYS.intersection(declaration)
    if forbidden:
        names = ", ".join(sorted(forbidden))
        raise ProcedureDeclarationError(
            f"procedure versions come from directories, not fields: {names}"
        )

    _validate_declaration(declaration)
    expanded = _expand_scenario_prefixes(declaration)
    return {**expanded, "documentation_version": documentation_version}


def _validate_declaration(declaration: dict[str, Any]) -> None:
    exact_keys(
        declaration,
        required={"schema", "procedure", "title", "summary", "entities", "scenarios"},
        optional={"default_scenario"},
        context="procedure declaration",
    )
    if text(declaration["schema"], "schema") != SCHEMA_ID:
        raise ProcedureDeclarationError(f"schema must be {SCHEMA_ID!r}")
    identifier(declaration["procedure"], "procedure")
    text(declaration["title"], "title")
    text(declaration["summary"], "summary")

    entities = list_value(declaration["entities"], "entities")
    if not entities:
        raise ProcedureDeclarationError("entities must not be empty")
    entity_ids: set[str] = set()
    for index, value in enumerate(entities):
        entity_id = _validate_entity(value, f"entities[{index}]")
        if entity_id in entity_ids:
            raise ProcedureDeclarationError(f"duplicate entity ID: {entity_id}")
        entity_ids.add(entity_id)

    scenarios = mapping(declaration["scenarios"], "scenarios")
    if not scenarios:
        raise ProcedureDeclarationError("scenarios must not be empty")
    scenario_ids = set(scenarios)
    for scenario_id, scenario_value in scenarios.items():
        identifier(scenario_id, "scenario identifier")
        _validate_scenario(
            scenario_id,
            scenario_value,
            entity_ids,
            scenario_ids,
        )

    default_scenario = declaration.get("default_scenario", next(iter(scenarios)))
    if default_scenario not in scenarios:
        raise ProcedureDeclarationError(
            "default_scenario must identify one declared scenario"
        )


def _validate_entity(value: Any, context: str) -> str:
    entity = mapping(value, context)
    exact_keys(
        entity,
        required={"id", "label", "kind"},
        optional={"role"},
        context=context,
    )
    entity_id = identifier(entity["id"], f"{context}.id")
    text(entity["label"], f"{context}.label")
    kind = text(entity["kind"], f"{context}.kind")
    if kind not in _ENTITY_KINDS:
        raise ProcedureDeclarationError(
            f"{context}.kind must be one of {sorted(_ENTITY_KINDS)}"
        )
    if "role" in entity:
        text(entity["role"], f"{context}.role")
    return entity_id


def _validate_scenario(
    scenario_id: str,
    value: Any,
    entity_ids: set[str],
    scenario_ids: set[str],
) -> None:
    context = f"scenarios.{scenario_id}"
    scenario = mapping(value, context)
    exact_keys(
        scenario,
        required={"label", "steps"},
        optional={"prefix"},
        context=context,
    )
    text(scenario["label"], f"{context}.label")
    if "prefix" in scenario:
        prefix = mapping(scenario["prefix"], f"{context}.prefix")
        exact_keys(
            prefix,
            required={"scenario", "through"},
            optional=set(),
            context=f"{context}.prefix",
        )
        parent = identifier(
            prefix["scenario"],
            f"{context}.prefix.scenario",
        )
        if parent not in scenario_ids:
            raise ProcedureDeclarationError(
                f"{context}.prefix references unknown scenario: {parent}"
            )
        identifier(prefix["through"], f"{context}.prefix.through")
    steps = list_value(scenario["steps"], f"{context}.steps")
    if not steps:
        raise ProcedureDeclarationError(f"{context}.steps must not be empty")
    step_ids: set[str] = set()
    for index, value in enumerate(steps):
        step_id = _validate_step(
            value,
            f"{context}.steps[{index}]",
            entity_ids,
        )
        if step_id is None:
            continue
        if step_id in step_ids:
            raise ProcedureDeclarationError(
                f"{context}.steps contains duplicate step ID: {step_id}"
            )
        step_ids.add(step_id)


def _validate_step(
    value: Any,
    context: str,
    entity_ids: set[str],
) -> str | None:
    step = mapping(value, context)
    exact_keys(
        step,
        required={
            "title",
            "detail",
            "phase",
            "active",
            "transitions",
            "activities",
        },
        optional={"id", "fields", "context"},
        context=context,
    )
    step_id = identifier(step["id"], f"{context}.id") if "id" in step else None
    text(step["title"], f"{context}.title")
    text(step["detail"], f"{context}.detail")
    text(step["phase"], f"{context}.phase")
    text_list(step.get("fields", []), f"{context}.fields")

    active = identifier_list(step["active"], f"{context}.active")
    require_known_entities(active, entity_ids, f"{context}.active")

    transitions = list_value(step["transitions"], f"{context}.transitions")
    for index, transition_value in enumerate(transitions):
        _validate_transition(
            transition_value,
            f"{context}.transitions[{index}]",
            entity_ids,
        )

    activities = mapping(step["activities"], f"{context}.activities")
    require_known_entities(set(activities), entity_ids, f"{context}.activities")
    for entity_id, activity_value in activities.items():
        activity = mapping(activity_value, f"{context}.activities.{entity_id}")
        exact_keys(
            activity,
            required={"title", "items"},
            optional=set(),
            context=f"{context}.activities.{entity_id}",
        )
        text(activity["title"], f"{context}.activities.{entity_id}.title")
        text_list(activity["items"], f"{context}.activities.{entity_id}.items")

    if "context" in step:
        shared_context = mapping(step["context"], f"{context}.context")
        exact_keys(
            shared_context,
            required={"kind", "value"},
            optional=set(),
            context=f"{context}.context",
        )
        text(shared_context["kind"], f"{context}.context.kind")
        text(shared_context["value"], f"{context}.context.value")
    return step_id


def _expand_scenario_prefixes(
    declaration: dict[str, Any],
) -> dict[str, Any]:
    scenarios = mapping(declaration["scenarios"], "scenarios")
    expanded_steps: dict[str, list[Any]] = {}

    def expand(scenario_id: str, stack: tuple[str, ...]) -> list[Any]:
        if scenario_id in expanded_steps:
            return expanded_steps[scenario_id]
        if scenario_id in stack:
            cycle = " -> ".join((*stack, scenario_id))
            raise ProcedureDeclarationError(f"scenario prefix cycle detected: {cycle}")

        scenario = mapping(
            scenarios[scenario_id],
            f"scenarios.{scenario_id}",
        )
        inherited: list[Any] = []
        if "prefix" in scenario:
            prefix = mapping(
                scenario["prefix"],
                f"scenarios.{scenario_id}.prefix",
            )
            parent_id = prefix["scenario"]
            through = prefix["through"]
            parent_steps = expand(parent_id, (*stack, scenario_id))
            for index, step_value in enumerate(parent_steps):
                step = mapping(
                    step_value,
                    f"scenarios.{parent_id}.steps[{index}]",
                )
                inherited.append(step_value)
                if step.get("id") == through:
                    break
            else:
                raise ProcedureDeclarationError(
                    f"scenarios.{scenario_id}.prefix references unknown step "
                    f"in {parent_id}: {through}"
                )

        combined = [*inherited, *list_value(scenario["steps"], "steps")]
        identifiers = [
            step["id"] for step in combined if isinstance(step, dict) and "id" in step
        ]
        if len(identifiers) != len(set(identifiers)):
            raise ProcedureDeclarationError(
                f"scenarios.{scenario_id} expands to duplicate step IDs"
            )
        expanded_steps[scenario_id] = combined
        return combined

    expanded_scenarios = {
        scenario_id: {
            key: item
            for key, item in mapping(
                scenario_value,
                f"scenarios.{scenario_id}",
            ).items()
            if key != "prefix"
        }
        for scenario_id, scenario_value in scenarios.items()
    }
    for scenario_id in scenarios:
        expanded_scenarios[scenario_id]["steps"] = expand(scenario_id, ())

    return {**declaration, "scenarios": expanded_scenarios}


def _validate_transition(value: Any, context: str, entity_ids: set[str]) -> None:
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
    tone = text(transition.get("tone", "normal"), f"{context}.tone")
    if tone not in _TONES:
        raise ProcedureDeclarationError(
            f"{context}.tone must be one of {sorted(_TONES)}"
        )
