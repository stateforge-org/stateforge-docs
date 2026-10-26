from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from stateforge_docs_theme.entity_flow import (
    EntityFlowDeclarationError,
    load_entity_flow,
)

FIXTURE_DOCS = Path(__file__).parent / "fixtures/site/docs"
DECLARATION = FIXTURE_DOCS / "v0.1.0/trigger-flow.yaml"


def test_entity_flow_derives_version_and_preserves_declared_entities() -> None:
    loaded = load_entity_flow(DECLARATION, docs_dir=FIXTURE_DOCS)

    assert loaded["documentation_version"] == "v0.1.0"
    assert loaded["flow"] == "trigger-publication"
    assert [entity["id"] for entity in loaded["entities"]] == [
        "service",
        "manager",
        "provider",
        "agent",
    ]
    assert loaded["steps"][-1]["responsibility"]["entities"] == ["agent"]


def _write_declaration(
    tmp_path: Path, declaration: dict[str, object]
) -> tuple[Path, Path]:
    docs = tmp_path / "docs"
    destination = docs / "v0.1.0/flow.yaml"
    destination.parent.mkdir(parents=True)
    destination.write_text(yaml.safe_dump(declaration))
    return destination, docs


def test_entity_flow_rejects_unknown_entity_references(tmp_path: Path) -> None:
    declaration = yaml.safe_load(DECLARATION.read_text())
    declaration["steps"][0]["active"].append("missing")
    destination, docs = _write_declaration(tmp_path, declaration)

    with pytest.raises(
        EntityFlowDeclarationError,
        match="references unknown entities: missing",
    ):
        load_entity_flow(destination, docs_dir=docs)


def test_entity_flow_rejects_unbundled_brand(tmp_path: Path) -> None:
    declaration = yaml.safe_load(DECLARATION.read_text())
    declaration["entities"][0]["brand"] = "vendor-logo"
    destination, docs = _write_declaration(tmp_path, declaration)

    with pytest.raises(EntityFlowDeclarationError, match="brand must be one of"):
        load_entity_flow(destination, docs_dir=docs)


def test_entity_flow_requires_version_directory(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    destination = docs / "flow.yaml"
    docs.mkdir()
    destination.write_text(DECLARATION.read_text())

    with pytest.raises(
        EntityFlowDeclarationError,
        match="below a version directory",
    ):
        load_entity_flow(destination, docs_dir=docs)
