"""Shared validation mechanics for versioned documentation declarations."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

_VERSION_DIRECTORY = re.compile(r"^v\d+(?:\.\d+)*$")
_VERSIONED_FILENAME = re.compile(r"(?:^|[-_.])v\d+(?:\.\d+)*(?:$|[-_.])")


class DeclarationError(ValueError):
    """Raised when a declarative documentation source is invalid."""


def load_versioned_yaml(
    path: Path,
    *,
    docs_dir: Path,
    maximum_bytes: int,
    source_name: str,
) -> tuple[dict[str, Any], str]:
    """Load bounded YAML and derive its documentation version from its path."""
    resolved_docs = docs_dir.resolve()
    resolved_path = path.resolve()
    if not resolved_path.is_relative_to(resolved_docs):
        raise DeclarationError(f"{source_name} source must remain inside docs_dir")
    if resolved_path.suffix not in {".yaml", ".yml"}:
        raise DeclarationError(f"{source_name} source must be YAML")
    if _VERSIONED_FILENAME.search(resolved_path.stem):
        raise DeclarationError(
            f"{source_name} filenames must not contain versions; "
            "use a version directory"
        )
    try:
        size = resolved_path.stat().st_size
    except OSError as error:
        raise DeclarationError(
            f"cannot read {source_name} source: {resolved_path}"
        ) from error
    if size > maximum_bytes:
        raise DeclarationError(f"{source_name} source exceeds {maximum_bytes} bytes")
    try:
        loaded = yaml.safe_load(resolved_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as error:
        raise DeclarationError(
            f"invalid {source_name} source: {resolved_path}"
        ) from error

    relative = resolved_path.relative_to(resolved_docs)
    return mapping(loaded, f"{source_name} declaration"), version_from_path(relative)


def version_from_path(relative_path: Path) -> str:
    """Return the nearest version directory containing a declaration."""
    for part in reversed(relative_path.parts[:-1]):
        if _VERSION_DIRECTORY.fullmatch(part):
            return part
    raise DeclarationError(
        "declaration source must be located below a version directory such as "
        "v0.1.0/procedures/bootstrap.yaml"
    )


def mapping(value: Any, context: str) -> dict[str, Any]:
    """Require a string-keyed mapping."""
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise DeclarationError(f"{context} must be a string-keyed mapping")
    return value


def list_value(value: Any, context: str) -> list[Any]:
    """Require a list."""
    if not isinstance(value, list):
        raise DeclarationError(f"{context} must be a list")
    return value


def text(value: Any, context: str) -> str:
    """Require non-empty text."""
    if not isinstance(value, str) or not value.strip():
        raise DeclarationError(f"{context} must be non-empty text")
    return value


def identifier(value: Any, context: str) -> str:
    """Require a lowercase kebab-case declaration identifier."""
    result = text(value, context)
    if not re.fullmatch(r"[a-z][a-z0-9-]*", result):
        raise DeclarationError(
            f"{context} must use lowercase letters, digits, and hyphens"
        )
    return result


def text_list(value: Any, context: str) -> list[str]:
    """Require a list of non-empty strings."""
    values = list_value(value, context)
    for index, item in enumerate(values):
        text(item, f"{context}[{index}]")
    return values


def identifier_list(value: Any, context: str) -> set[str]:
    """Require a duplicate-free list of declaration identifiers."""
    values = list_value(value, context)
    identifiers = {
        identifier(item, f"{context}[{index}]") for index, item in enumerate(values)
    }
    if len(identifiers) != len(values):
        raise DeclarationError(f"{context} must not contain duplicates")
    return identifiers


def exact_keys(
    value: dict[str, Any],
    *,
    required: set[str],
    optional: set[str],
    context: str,
) -> None:
    """Require an exact set of mandatory and optional mapping keys."""
    missing = required.difference(value)
    unknown = set(value).difference(required | optional)
    if missing:
        raise DeclarationError(f"{context} is missing: {', '.join(sorted(missing))}")
    if unknown:
        raise DeclarationError(
            f"{context} contains unknown fields: {', '.join(sorted(unknown))}"
        )


def require_known_entities(
    referenced: set[str], entity_ids: set[str], context: str
) -> None:
    """Require all referenced entity identifiers to be declared."""
    unknown = referenced.difference(entity_ids)
    if unknown:
        raise DeclarationError(
            f"{context} references unknown entities: {', '.join(sorted(unknown))}"
        )
