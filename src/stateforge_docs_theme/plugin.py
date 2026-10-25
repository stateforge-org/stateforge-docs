"""MkDocs integration for the shared StateForge documentation system."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, TypedDict

import yaml
from mkdocs.config import config_options
from mkdocs.config.base import Config
from mkdocs.exceptions import PluginError
from mkdocs.plugins import BasePlugin
from mkdocs.structure.files import Files
from mkdocs.structure.pages import Page

from stateforge_docs_theme.branding import (
    COMPONENT_ACCENTS,
    LIGHT_FOREGROUND,
    component_accent,
    contrast_foreground,
)
from stateforge_docs_theme.procedure.model import (
    ProcedureDeclarationError,
    load_procedure,
)
from stateforge_docs_theme.procedure.renderer import render_player

_PROCEDURE_FENCE = re.compile(
    r"^```stateforge-procedure[ \t]*\n(?P<body>.*?)^```[ \t]*$",
    re.MULTILINE | re.DOTALL,
)


class DocumentationVersionConfig(Config):  # type: ignore[no-untyped-call]
    """One link rendered by the shared documentation version selector."""

    label = config_options.Type(str)
    url = config_options.Type(str)


class DocumentationVersion(TypedDict):
    """One normalized documentation-version link exposed to the theme."""

    label: str
    url: str
    current: bool


class StateForgeDocsConfig(Config):  # type: ignore[no-untyped-call]
    """Configuration shared by all StateForge documentation consumers."""

    component = config_options.Type(str, default="stateforge")
    accent = config_options.Optional(config_options.Type(str))
    documentation_version = config_options.Optional(config_options.Type(str))
    latest_version = config_options.Optional(config_options.Type(str))
    versions = config_options.ListOfItems(
        config_options.SubConfig(DocumentationVersionConfig),
        default=[],
    )
    historical_warning = config_options.Type(bool, default=True)
    procedure_players = config_options.Type(bool, default=True)


class StateForgeDocsPlugin(  # type: ignore[no-untyped-call]
    BasePlugin[StateForgeDocsConfig]
):
    """Render declarative procedure players and expose component identity."""

    def on_config(self, config: Any) -> Any:
        try:
            accent = component_accent(self.config.component, self.config.accent)
        except ValueError as error:
            raise PluginError(
                f"invalid StateForge theme configuration: {error}"
            ) from error

        versions: list[DocumentationVersion] = [
            {"label": entry.label, "url": entry.url, "current": False}
            for entry in self.config.versions
        ]
        labels = [entry["label"] for entry in versions]
        if len(labels) != len(set(labels)):
            raise PluginError("documentation version labels must be unique")
        current_version = self.config.documentation_version
        latest_version = self.config.latest_version
        if current_version and versions and current_version not in labels:
            raise PluginError(
                "documentation_version must identify one configured version"
            )
        if latest_version and versions and latest_version not in labels:
            raise PluginError("latest_version must identify one configured version")

        for entry in versions:
            entry["current"] = entry["label"] == current_version
        latest_url = next(
            (entry["url"] for entry in versions if entry["label"] == latest_version),
            None,
        )
        historical = bool(
            self.config.historical_warning
            and current_version
            and latest_version
            and current_version not in {latest_version, "dev"}
        )

        foreground = contrast_foreground(accent)
        logo_filter = (
            "brightness(0) invert(1)"
            if foreground == LIGHT_FOREGROUND
            else "brightness(0)"
        )
        extra = dict(config.extra or {})
        stateforge = dict(extra.get("stateforge") or {})
        stateforge.update(
            {
                "accent": accent,
                "accent_foreground": foreground,
                "component": self.config.component,
                "documentation_version": current_version,
                "historical": historical,
                "known_components": sorted(COMPONENT_ACCENTS),
                "latest_url": latest_url,
                "latest_version": latest_version,
                "logo_filter": logo_filter,
                "versions": versions,
            }
        )
        extra["stateforge"] = stateforge
        config.extra = extra
        return config

    def on_page_markdown(
        self,
        markdown: str,
        *,
        page: Page,
        config: Any,
        files: Files,
    ) -> str:
        del files
        if not self.config.procedure_players:
            return markdown

        if page.file.abs_src_path is None:
            raise PluginError(f"page has no source path: {page.file.src_path}")
        page_source = Path(page.file.abs_src_path)
        docs_dir = Path(config.docs_dir)

        def replace(match: re.Match[str]) -> str:
            try:
                directive = _load_directive(match.group("body"))
                source = (page_source.parent / directive["source"]).resolve()
                declaration = load_procedure(source, docs_dir=docs_dir)
                return render_player(
                    declaration,
                    selected_scenario=directive.get("scenario"),
                )
            except (ProcedureDeclarationError, ValueError) as error:
                raise PluginError(
                    f"{page.file.src_path}: invalid stateforge-procedure block: {error}"
                ) from error

        return _PROCEDURE_FENCE.sub(replace, markdown)


def _load_directive(source: str) -> dict[str, str]:
    try:
        loaded = yaml.safe_load(source)
    except yaml.YAMLError as error:
        raise ProcedureDeclarationError("directive must be valid YAML") from error
    if not isinstance(loaded, dict) or not all(
        isinstance(key, str) and isinstance(value, str) for key, value in loaded.items()
    ):
        raise ProcedureDeclarationError(
            "directive must be a string-keyed mapping of text values"
        )
    missing = {"source"}.difference(loaded)
    unknown = set(loaded).difference({"source", "scenario"})
    if missing:
        raise ProcedureDeclarationError("directive requires source")
    if unknown:
        raise ProcedureDeclarationError(
            f"directive contains unknown fields: {', '.join(sorted(unknown))}"
        )
    return loaded
