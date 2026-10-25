from __future__ import annotations

import pytest

from stateforge_docs_theme.branding import (
    COMPONENT_ACCENTS,
    component_accent,
    contrast_foreground,
    contrast_ratio,
)


def test_named_component_accents_are_distinct_and_accessible() -> None:
    assert len(set(COMPONENT_ACCENTS.values())) == len(COMPONENT_ACCENTS)
    assert set(COMPONENT_ACCENTS) == {
        "stateforge",
        "agent",
        "provider",
        "protocol",
        "control-plane",
        "sf-aop",
    }
    for accent in COMPONENT_ACCENTS.values():
        foreground = contrast_foreground(accent)
        assert contrast_ratio(accent, foreground) >= 4.5


def test_future_component_can_supply_an_accessible_custom_accent() -> None:
    accent = component_accent("new-component", "#e8c547")

    assert accent == "#e8c547"
    assert contrast_foreground(accent) == "#111827"
    assert contrast_ratio(accent, contrast_foreground(accent)) >= 4.5


@pytest.mark.parametrize(
    ("component", "accent"),
    [
        ("Not Valid", None),
        ("valid", "blue"),
        ("valid", "#123"),
    ],
)
def test_invalid_brand_inputs_are_rejected(
    component: str,
    accent: str | None,
) -> None:
    with pytest.raises(ValueError):
        component_accent(component, accent)
