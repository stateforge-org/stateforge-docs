from __future__ import annotations

from importlib.metadata import entry_points
from pathlib import Path

from mkdocs.commands.build import build
from mkdocs.config import load_config

import stateforge_docs_theme


def test_theme_contains_bundled_brand_and_player_assets() -> None:
    package = Path(stateforge_docs_theme.__file__).parent
    theme = package / "theme"

    assert (theme / "mkdocs_theme.yml").is_file()
    assert (theme / "assets/images/stateforge-mark.svg").is_file()
    assert (theme / "assets/images/stateforge-favicon.svg").is_file()
    assert (theme / "assets/stylesheets/stateforge.css").is_file()
    player = theme / "assets/javascripts/procedure-player.js"
    assert player.is_file()
    source = player.read_text()
    assert "Bootstrap" not in source
    assert "StateForge Agent" not in source
    assert "Provider Process" not in source

    for asset in theme.rglob("*"):
        if asset.suffix in {".css", ".html", ".js"}:
            contents = asset.read_text()
            assert "http://" not in contents
            assert "https://" not in contents


def test_theme_is_discoverable_and_fixture_has_no_branding_copies() -> None:
    themes = {entry.name: entry.value for entry in entry_points(group="mkdocs.themes")}
    assert themes["stateforge"] == "stateforge_docs_theme.theme"

    fixture_docs = Path(__file__).parent / "fixtures/site/docs"
    local_branding = [
        path
        for path in fixture_docs.rglob("*")
        if path.suffix.lower() in {".css", ".svg", ".png", ".ico"}
    ]
    assert local_branding == []


def test_fixture_site_builds_with_interactive_player(tmp_path: Path) -> None:
    fixture = Path(__file__).parent / "fixtures/site"
    config = load_config(
        config_file=str(fixture / "mkdocs.yml"),
        site_dir=str(tmp_path / "site"),
        strict=True,
    )

    build(config)

    rendered = (tmp_path / "site/v0.1.0/index.html").read_text()
    assert "stateforge-procedure-player" in rendered
    assert 'data-documentation-version="v0.1.0"' in rendered
    assert "assets/javascripts/procedure-player.js" in rendered
    assert "assets/stylesheets/stateforge.css" in rendered
    assert "stateforge-brand-tokens" in rendered
    assert "#a95000" in rendered
    assert "--sf-logo-filter: brightness(0) invert(1)" in rendered
    assert "Documentation version" in rendered
    assert "v0.1.0" in rendered
    assert "v0.2.0" in rendered
    assert "You are reading StateForge documentation" in rendered
    assert "stateforge-org/stateforge-docs" in rendered
    assert "fonts.googleapis.com" not in rendered
    assert 'href="../assets/images/stateforge-favicon.svg"' in rendered

    site = tmp_path / "site"
    assert (site / "assets/images/stateforge-mark.svg").is_file()
    assert (site / "assets/images/stateforge-favicon.svg").is_file()
