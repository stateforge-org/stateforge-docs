"""Load and validate versioned procedure declarations."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

SCHEMA_ID = "stateforge.docs/procedure/v1"
MAX_DECLARATION_BYTES = 512 * 1024

_VERSION_DIRECTORY = re.compile(r"^v\d+(?:\.\d+)*$")
_VERSIONED_FILENAME = re.compile(r"(?:^|[-_.])v\d+(?:\.\d+)*(?:$|[-_.])")
_FORBIDDEN_VERSION_KEYS = frozenset(
    {"version", "protocol_version", "documentation_version"}
)
_ENTITY_KINDS = frozenset(
    {"process", "service", "resource", "storage", "external", "user"}
)
_TONES = frozenset({"normal", "success", "warning", "failure"})


class ProcedureDeclarationError(ValueError):
    """Raised when a procedure declaration violates the shared contract."""


def load_procedure(path: Path, *, docs_dir: Path) -> dict[str, Any]:
    """Load one declaration and derive its documentation version from its path."""
    resolved_docs = docs_dir.resolve()
    resolved_path = path.resolve()
    if not resolved_path.is_relative_to(resolved_docs):
        raise ProcedureDeclarationError("procedure source must remain inside docs_dir")
    if resolved_path.suffix not in {".yaml", ".yml"}:
        raise ProcedureDeclarationError("procedure source must be YAML")
    if _VERSIONED_FILENAME.search(resolved_path.stem):
        raise ProcedureDeclarationError(
            "procedure filenames must not contain versions; use a version directory"
        )
    try:
        size = resolved_path.stat().st_size
    except OSError as error:
        raise ProcedureDeclarationError(
            f"cannot read procedure source: {resolved_path}"
        ) from error
    if size > MAX_DECLARATION_BYTES:
        raise ProcedureDeclarationError(
            f"procedure source exceeds {MAX_DECLARATION_BYTES} bytes"
        )
    try:
        loaded = yaml.safe_load(resolved_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as error:
        raise ProcedureDeclarationError(
            f"invalid procedure source: {resolved_path}"
        ) from error

    declaration = _mapping(loaded, "procedure declaration")
    forbidden = _FORBIDDEN_VERSION_KEYS.intersection(declaration)
    if forbidden:
        names = ", ".join(sorted(forbidden))
        raise ProcedureDeclarationError(
            f"procedure versions come from directories, not fields: {names}"
        )

    relative = resolved_path.relative_to(resolved_docs)
    documentation_version = _version_from_path(relative)
    _validate_declaration(declaration)
    expanded = _expand_scenario_prefixes(declaration)
    return {**expanded, "documentation_version": documentation_version}


def _version_from_path(relative_path: Path) -> str:
    for part in reversed(relative_path.parts[:-1]):
        if _VERSION_DIRECTORY.fullmatch(part):
            return part
    raise ProcedureDeclarationError(
        "procedure source must be located below a version directory such as "
        "v0.1.0/procedures/bootstrap.yaml"
    )


def _validate_declaration(declaration: dict[str, Any]) -> None:
    _exact_keys(
        declaration,
        required={"schema", "procedure", "title", "summary", "entities", "scenarios"},
        optional={"default_scenario"},
        context="procedure declaration",
    )
    if _text(declaration["schema"], "schema") != SCHEMA_ID:
        raise ProcedureDeclarationError(f"schema must be {SCHEMA_ID!r}")
    _identifier(declaration["procedure"], "procedure")
    _text(declaration["title"], "title")
    _text(declaration["summary"], "summary")

    entities = _list(declaration["entities"], "entities")
    if not entities:
        raise ProcedureDeclarationError("entities must not be empty")
    entity_ids: set[str] = set()
    for index, value in enumerate(entities):
        entity_id = _validate_entity(value, f"entities[{index}]")
        if entity_id in entity_ids:
            raise ProcedureDeclarationError(f"duplicate entity ID: {entity_id}")
        entity_ids.add(entity_id)

    scenarios = _mapping(declaration["scenarios"], "scenarios")
    if not scenarios:
        raise ProcedureDeclarationError("scenarios must not be empty")
    scenario_ids = set(scenarios)
    for scenario_id, scenario_value in scenarios.items():
        _identifier(scenario_id, "scenario identifier")
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
    entity = _mapping(value, context)
    _exact_keys(
        entity,
        required={"id", "label", "kind"},
        optional={"role"},
        context=context,
    )
    entity_id = _identifier(entity["id"], f"{context}.id")
    _text(entity["label"], f"{context}.label")
    kind = _text(entity["kind"], f"{context}.kind")
    if kind not in _ENTITY_KINDS:
        raise ProcedureDeclarationError(
            f"{context}.kind must be one of {sorted(_ENTITY_KINDS)}"
        )
    if "role" in entity:
        _text(entity["role"], f"{context}.role")
    return entity_id


def _validate_scenario(
    scenario_id: str,
    value: Any,
    entity_ids: set[str],
    scenario_ids: set[str],
) -> None:
    context = f"scenarios.{scenario_id}"
    scenario = _mapping(value, context)
    _exact_keys(
        scenario,
        required={"label", "steps"},
        optional={"prefix"},
        context=context,
    )
    _text(scenario["label"], f"{context}.label")
    if "prefix" in scenario:
        prefix = _mapping(scenario["prefix"], f"{context}.prefix")
        _exact_keys(
            prefix,
            required={"scenario", "through"},
            optional=set(),
            context=f"{context}.prefix",
        )
        parent = _identifier(
            prefix["scenario"],
            f"{context}.prefix.scenario",
        )
        if parent not in scenario_ids:
            raise ProcedureDeclarationError(
                f"{context}.prefix references unknown scenario: {parent}"
            )
        _identifier(prefix["through"], f"{context}.prefix.through")
    steps = _list(scenario["steps"], f"{context}.steps")
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
    step = _mapping(value, context)
    _exact_keys(
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
    step_id = _identifier(step["id"], f"{context}.id") if "id" in step else None
    _text(step["title"], f"{context}.title")
    _text(step["detail"], f"{context}.detail")
    _text(step["phase"], f"{context}.phase")
    _text_list(step.get("fields", []), f"{context}.fields")

    active = _identifier_list(step["active"], f"{context}.active")
    _require_known_entities(active, entity_ids, f"{context}.active")

    transitions = _list(step["transitions"], f"{context}.transitions")
    for index, transition_value in enumerate(transitions):
        _validate_transition(
            transition_value,
            f"{context}.transitions[{index}]",
            entity_ids,
        )

    activities = _mapping(step["activities"], f"{context}.activities")
    _require_known_entities(set(activities), entity_ids, f"{context}.activities")
    for entity_id, activity_value in activities.items():
        activity = _mapping(activity_value, f"{context}.activities.{entity_id}")
        _exact_keys(
            activity,
            required={"title", "items"},
            optional=set(),
            context=f"{context}.activities.{entity_id}",
        )
        _text(activity["title"], f"{context}.activities.{entity_id}.title")
        _text_list(activity["items"], f"{context}.activities.{entity_id}.items")

    if "context" in step:
        shared_context = _mapping(step["context"], f"{context}.context")
        _exact_keys(
            shared_context,
            required={"kind", "value"},
            optional=set(),
            context=f"{context}.context",
        )
        _text(shared_context["kind"], f"{context}.context.kind")
        _text(shared_context["value"], f"{context}.context.value")
    return step_id


def _expand_scenario_prefixes(
    declaration: dict[str, Any],
) -> dict[str, Any]:
    scenarios = _mapping(declaration["scenarios"], "scenarios")
    expanded_steps: dict[str, list[Any]] = {}

    def expand(scenario_id: str, stack: tuple[str, ...]) -> list[Any]:
        if scenario_id in expanded_steps:
            return expanded_steps[scenario_id]
        if scenario_id in stack:
            cycle = " -> ".join((*stack, scenario_id))
            raise ProcedureDeclarationError(f"scenario prefix cycle detected: {cycle}")

        scenario = _mapping(
            scenarios[scenario_id],
            f"scenarios.{scenario_id}",
        )
        inherited: list[Any] = []
        if "prefix" in scenario:
            prefix = _mapping(
                scenario["prefix"],
                f"scenarios.{scenario_id}.prefix",
            )
            parent_id = prefix["scenario"]
            through = prefix["through"]
            parent_steps = expand(parent_id, (*stack, scenario_id))
            for index, step_value in enumerate(parent_steps):
                step = _mapping(
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

        combined = [*inherited, *_list(scenario["steps"], "steps")]
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
            for key, item in _mapping(
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
    transition = _mapping(value, context)
    _exact_keys(
        transition,
        required={"source", "target", "label"},
        optional={"tone"},
        context=context,
    )
    source = _identifier(transition["source"], f"{context}.source")
    target = _identifier(transition["target"], f"{context}.target")
    _require_known_entities({source, target}, entity_ids, context)
    _text(transition["label"], f"{context}.label")
    tone = _text(transition.get("tone", "normal"), f"{context}.tone")
    if tone not in _TONES:
        raise ProcedureDeclarationError(
            f"{context}.tone must be one of {sorted(_TONES)}"
        )


def _require_known_entities(
    referenced: set[str], entity_ids: set[str], context: str
) -> None:
    unknown = referenced.difference(entity_ids)
    if unknown:
        raise ProcedureDeclarationError(
            f"{context} references unknown entities: {', '.join(sorted(unknown))}"
        )


def _mapping(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ProcedureDeclarationError(f"{context} must be a string-keyed mapping")
    return value


def _list(value: Any, context: str) -> list[Any]:
    if not isinstance(value, list):
        raise ProcedureDeclarationError(f"{context} must be a list")
    return value


def _text(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProcedureDeclarationError(f"{context} must be non-empty text")
    return value


def _identifier(value: Any, context: str) -> str:
    identifier = _text(value, context)
    if not re.fullmatch(r"[a-z][a-z0-9-]*", identifier):
        raise ProcedureDeclarationError(
            f"{context} must use lowercase letters, digits, and hyphens"
        )
    return identifier


def _text_list(value: Any, context: str) -> list[str]:
    values = _list(value, context)
    for index, item in enumerate(values):
        _text(item, f"{context}[{index}]")
    return values


def _identifier_list(value: Any, context: str) -> set[str]:
    values = _list(value, context)
    identifiers = {
        _identifier(item, f"{context}[{index}]") for index, item in enumerate(values)
    }
    if len(identifiers) != len(values):
        raise ProcedureDeclarationError(f"{context} must not contain duplicates")
    return identifiers


def _exact_keys(
    value: dict[str, Any],
    *,
    required: set[str],
    optional: set[str],
    context: str,
) -> None:
    missing = required.difference(value)
    unknown = set(value).difference(required | optional)
    if missing:
        raise ProcedureDeclarationError(
            f"{context} is missing: {', '.join(sorted(missing))}"
        )
    if unknown:
        raise ProcedureDeclarationError(
            f"{context} contains unknown fields: {', '.join(sorted(unknown))}"
        )
