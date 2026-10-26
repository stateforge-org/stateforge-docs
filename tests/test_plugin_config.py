from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
from mkdocs.commands.build import build
from mkdocs.config import load_config
from mkdocs.exceptions import Abort


def _write_site(tmp_path: Path, plugin_config: str) -> Path:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "index.md").write_text("# Fixture\n")
    config = tmp_path / "mkdocs.yml"
    config.write_text(
        dedent(
            f"""
            site_name: StateForge configuration fixture
            theme:
              name: stateforge
            plugins:
              - stateforge:
            {plugin_config}
            """
        )
    )
    return config


@pytest.mark.parametrize(
    "plugin_config",
    [
        """
                  documentation_version: v0.1.0
                  latest_version: v0.1.0
                  versions:
                    - label: v0.1.0
                      url: ./
                    - label: v0.1.0
                      url: ../duplicate/
        """,
        """
                  documentation_version: v0.1.0
                  latest_version: v0.2.0
                  versions:
                    - label: v0.2.0
                      url: ../v0.2.0/
        """,
        """
                  documentation_version: v0.1.0
                  latest_version: v0.2.0
                  versions:
                    - label: v0.1.0
                      url: ./
        """,
    ],
)
def test_invalid_version_configuration_is_rejected(
    tmp_path: Path,
    plugin_config: str,
) -> None:
    config_file = _write_site(tmp_path, plugin_config)
    config = load_config(
        config_file=str(config_file),
        site_dir=str(tmp_path / "site"),
        strict=True,
    )

    with pytest.raises(Abort):
        build(config)


def test_future_component_configuration_is_rendered(tmp_path: Path) -> None:
    config_file = _write_site(
        tmp_path,
        """
                  component: stateforge-storage
                  accent: "#e8c547"
        """,
    )
    config = load_config(
        config_file=str(config_file),
        site_dir=str(tmp_path / "site"),
        strict=True,
    )

    build(config)

    rendered = (tmp_path / "site/index.html").read_text()
    assert "--sf-component-accent: #e8c547" in rendered
    assert "stateforge-mark.svg" in rendered
