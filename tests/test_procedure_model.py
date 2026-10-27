from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from stateforge_docs_theme.procedure.model import (
    ProcedureDeclarationError,
    load_procedure,
)

FIXTURE_DOCS = Path(__file__).parent / "fixtures/site/docs"
DECLARATION = FIXTURE_DOCS / "v0.1.0/procedures/bootstrap.yaml"


def test_version_is_derived_from_directory() -> None:
    loaded = load_procedure(DECLARATION, docs_dir=FIXTURE_DOCS)

    assert loaded["documentation_version"] == "v0.1.0"
    assert loaded["procedure"] == "bootstrap"
    assert [entity["id"] for entity in loaded["entities"]] == [
        "provider",
        "discovery-directory",
        "unix-socket",
        "agent",
    ]


def test_scenario_prefix_expands_shared_steps() -> None:
    loaded = load_procedure(DECLARATION, docs_dir=FIXTURE_DOCS)

    incompatible = loaded["scenarios"]["incompatible"]
    assert "prefix" not in incompatible
    assert [step["id"] for step in incompatible["steps"][:-1]] == [
        "publish-endpoint",
        "discover-endpoint",
        "open-channel",
        "validate-request",
    ]
    assert incompatible["steps"][-1]["title"] == ("Reject incompatible versions")


@pytest.mark.parametrize(
    "field",
    ["version", "protocol_version", "documentation_version"],
)
def test_declaration_rejects_embedded_versions(tmp_path: Path, field: str) -> None:
    docs = tmp_path / "docs"
    destination = docs / "v0.1.0/procedures/bootstrap.yaml"
    destination.parent.mkdir(parents=True)
    declaration = yaml.safe_load(DECLARATION.read_text())
    declaration[field] = "1.0"
    destination.write_text(yaml.safe_dump(declaration))

    with pytest.raises(
        ProcedureDeclarationError,
        match="versions come from directories",
    ):
        load_procedure(destination, docs_dir=docs)


def test_declaration_rejects_versioned_filename(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    destination = docs / "v0.1.0/procedures/bootstrap-v1.yaml"
    destination.parent.mkdir(parents=True)
    destination.write_text(DECLARATION.read_text())

    with pytest.raises(
        ProcedureDeclarationError,
        match="filenames must not contain versions",
    ):
        load_procedure(destination, docs_dir=docs)


def test_declaration_requires_version_directory(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    destination = docs / "procedures/bootstrap.yaml"
    destination.parent.mkdir(parents=True)
    destination.write_text(DECLARATION.read_text())

    with pytest.raises(
        ProcedureDeclarationError,
        match="below a version directory",
    ):
        load_procedure(destination, docs_dir=docs)


def test_declaration_cannot_escape_docs_dir(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    outside = tmp_path / "v0.1.0/procedures/bootstrap.yaml"
    outside.parent.mkdir(parents=True)
    outside.write_text(DECLARATION.read_text())

    with pytest.raises(
        ProcedureDeclarationError,
        match="inside docs_dir",
    ):
        load_procedure(outside, docs_dir=docs)


def test_declaration_does_not_limit_entity_count(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    destination = docs / "v0.1.0/procedures/bootstrap.yaml"
    destination.parent.mkdir(parents=True)
    declaration = yaml.safe_load(DECLARATION.read_text())
    declaration["entities"].extend(
        {
            "id": f"external-{index}",
            "label": f"External system {index}",
            "kind": "external",
            "role": "Participates in the documented procedure",
        }
        for index in range(12)
    )
    destination.write_text(yaml.safe_dump(declaration))

    loaded = load_procedure(destination, docs_dir=docs)

    assert len(loaded["entities"]) == 16


def test_transition_rejects_unknown_entity(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    destination = docs / "v0.1.0/procedures/bootstrap.yaml"
    destination.parent.mkdir(parents=True)
    declaration = yaml.safe_load(DECLARATION.read_text())
    declaration["scenarios"]["success"]["steps"][0]["transitions"][0]["target"] = (
        "missing-entity"
    )
    destination.write_text(yaml.safe_dump(declaration))

    with pytest.raises(
        ProcedureDeclarationError,
        match="references unknown entities",
    ):
        load_procedure(destination, docs_dir=docs)


def test_scenario_prefix_rejects_unknown_step(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    destination = docs / "v0.1.0/procedures/bootstrap.yaml"
    destination.parent.mkdir(parents=True)
    declaration = yaml.safe_load(DECLARATION.read_text())
    declaration["scenarios"]["incompatible"]["prefix"]["through"] = "missing-step"
    destination.write_text(yaml.safe_dump(declaration))

    with pytest.raises(
        ProcedureDeclarationError,
        match="references unknown step",
    ):
        load_procedure(destination, docs_dir=docs)


def test_scenario_prefix_rejects_cycles(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    destination = docs / "v0.1.0/procedures/bootstrap.yaml"
    destination.parent.mkdir(parents=True)
    declaration = yaml.safe_load(DECLARATION.read_text())
    declaration["scenarios"]["success"]["prefix"] = {
        "scenario": "incompatible",
        "through": "validate-request",
    }
    destination.write_text(yaml.safe_dump(declaration))

    with pytest.raises(
        ProcedureDeclarationError,
        match="scenario prefix cycle detected",
    ):
        load_procedure(destination, docs_dir=docs)
