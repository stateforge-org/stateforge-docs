"""Stable StateForge brand tokens shared by the theme and its tests."""

from __future__ import annotations

import re
from collections.abc import Mapping
from types import MappingProxyType

DEFAULT_ACCENT = "#245fc7"
LIGHT_FOREGROUND = "#ffffff"
DARK_FOREGROUND = "#111827"

COMPONENT_ACCENTS: Mapping[str, str] = MappingProxyType(
    {
        "stateforge": DEFAULT_ACCENT,
        "agent": "#1d5fbf",
        "provider": "#087a61",
        "protocol": "#a95000",
        "control-plane": "#6542b8",
        "sf-aop": "#98365d",
    }
)

_COMPONENT = re.compile(r"^[a-z][a-z0-9-]*$")
_HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


def component_accent(component: str, custom_accent: str | None = None) -> str:
    """Resolve one validated component accent, allowing future repositories."""
    if not _COMPONENT.fullmatch(component):
        raise ValueError("component must use lowercase letters, digits, and hyphens")
    accent = custom_accent or COMPONENT_ACCENTS.get(component, DEFAULT_ACCENT)
    if not _HEX_COLOR.fullmatch(accent):
        raise ValueError("accent must be a six-digit hexadecimal color")
    return accent.lower()


def contrast_foreground(background: str) -> str:
    """Choose the higher-contrast brand-safe foreground for a background."""
    candidates = (LIGHT_FOREGROUND, DARK_FOREGROUND)
    return max(candidates, key=lambda color: contrast_ratio(background, color))


def contrast_ratio(first: str, second: str) -> float:
    """Return the WCAG contrast ratio for two hexadecimal colors."""
    lighter, darker = sorted(
        (_relative_luminance(first), _relative_luminance(second)),
        reverse=True,
    )
    return (lighter + 0.05) / (darker + 0.05)


def _relative_luminance(color: str) -> float:
    if not _HEX_COLOR.fullmatch(color):
        raise ValueError("color must be a six-digit hexadecimal color")
    channels = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]
