"""MkDocs integration for the shared StateForge documentation system."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml
from mkdocs.config import config_options
from mkdocs.config.base import Config
from mkdocs.exceptions import PluginError
from mkdocs.plugins import BasePlugin
from mkdocs.structure.files import Files
from mkdocs.structure.pages import Page

from stateforge_docs_theme.procedure.model import (
    ProcedureDeclarationError,
    load_procedure,
)
from stateforge_docs_theme.procedure.renderer import render_player

_PROCEDURE_FENCE = re.compile(
    r"^```stateforge-procedure[ \t]*\n(?P<body>.*?)^```[ \t]*$",
    re.MULTILINE | re.DOTALL,
)


class StateForgeDocsConfig(Config):  # type: ignore[no-untyped-call]
    """Configuration shared by all StateForge documentation consumers."""

    component = config_options.Choice(
        (
            "stateforge",
            "agent",
            "provider",
            "protocol",
            "control-plane",
            "sf-aop",
        ),
        default="stateforge",
    )
    procedure_players = config_options.Type(bool, default=True)


class StateForgeDocsPlugin(  # type: ignore[no-untyped-call]
    BasePlugin[StateForgeDocsConfig]
):
    """Render declarative procedure players and expose component identity."""

    def on_config(self, config: Any) -> Any:
        extra = dict(config.extra or {})
        stateforge = dict(extra.get("stateforge") or {})
        stateforge["component"] = self.config.component
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
