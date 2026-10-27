from __future__ import annotations

import os
import threading
from collections.abc import Iterator
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from mkdocs.commands.build import build
from mkdocs.config import load_config

if os.environ.get("STATEFORGE_VISUAL_TESTS") != "1":
    pytest.skip(
        "set STATEFORGE_VISUAL_TESTS=1 to run browser verification",
        allow_module_level=True,
    )

from playwright.sync_api import Browser, Page, sync_playwright  # noqa: E402


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        del format, args


@pytest.fixture(scope="module")
def site_directory(tmp_path_factory: pytest.TempPathFactory) -> Path:
    fixture = Path(__file__).parent / "fixtures/site"
    site = tmp_path_factory.mktemp("rendered-site")
    config = load_config(
        config_file=str(fixture / "mkdocs.yml"),
        site_dir=str(site),
        strict=True,
    )
    build(config)
    return site


@pytest.fixture(scope="module")
def site_url(site_directory: Path) -> Iterator[str]:
    handler = partial(_QuietHandler, directory=str(site_directory))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    try:
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


@pytest.fixture(scope="module")
def browser() -> Iterator[Browser]:
    with sync_playwright() as playwright:
        instance = playwright.chromium.launch()
        yield instance
        instance.close()


@pytest.mark.visual
@pytest.mark.parametrize(
    ("width", "height", "scheme", "expected_palette"),
    [
        (1440, 1000, "light", "default"),
        (390, 844, "dark", "slate"),
    ],
)
def test_responsive_light_and_dark_rendering(
    browser: Browser,
    site_url: str,
    tmp_path: Path,
    width: int,
    height: int,
    scheme: str,
    expected_palette: str,
) -> None:
    page = browser.new_page(viewport={"width": width, "height": height})
    console_errors: list[str] = []
    page_errors: list[str] = []
    page.on(
        "console",
        lambda message: (
            console_errors.append(message.text) if message.type == "error" else None
        ),
    )
    page.on("pageerror", lambda error: page_errors.append(str(error)))
    page.emulate_media(color_scheme=scheme)
    page.goto(f"{site_url}/v0.1.0/", wait_until="networkidle")

    assert page.locator("body").get_attribute("data-md-color-scheme") == (
        expected_palette
    )
    assert page.locator(".sf-version-selector").is_visible()
    assert page.locator("select[data-sf-version-selector]").is_visible()
    assert page.locator(".md-search").count() == 1
    assert page.locator(".md-search__input").count() == 1
    assert page.locator(".sf-historical-warning").is_visible()
    assert page.locator(".md-header__source").is_visible() is (width >= 1220)
    assert page.evaluate(
        "document.documentElement.scrollWidth <= document.documentElement.clientWidth"
    )
    assert page.locator("stateforge-procedure-player").is_visible()
    assert page.locator("pre.sf-mermaid svg").is_visible()
    assert page.locator("pre.sf-mermaid .error-icon").count() == 0
    assert page.locator("pre.mermaid[data-processed]").count() == 0
    assert not [
        error
        for error in console_errors
        if "Mermaid" in error or "UnknownDiagramError" in error
    ]
    assert not [
        error
        for error in page_errors
        if "Mermaid" in error or "UnknownDiagramError" in error
    ]
    flow = page.locator("stateforge-entity-flow")
    assert flow.is_visible()
    assert flow.locator(".sf-entity-flow__entity").count() == 4
    if width >= 1000:
        viewport = flow.locator(".sf-entity-flow__viewport")
        assert viewport.evaluate(
            "element => element.scrollWidth <= element.clientWidth"
        )

    evidence = Path(os.environ.get("STATEFORGE_VISUAL_EVIDENCE", str(tmp_path)))
    evidence.mkdir(parents=True, exist_ok=True)
    page.screenshot(
        path=evidence / f"fixture-{width}-{scheme}.png",
        full_page=True,
    )
    page.close()


@pytest.mark.visual
def test_entity_flow_steps_state_and_responsibility(
    browser: Browser,
    site_url: str,
) -> None:
    page: Page = browser.new_page(viewport={"width": 1440, "height": 1000})
    page.goto(f"{site_url}/v0.1.0/", wait_until="networkidle")

    flow = page.locator("stateforge-entity-flow")
    assert flow.locator(".sf-entity-flow__phase strong").inner_text() == (
        "Unit state changed"
    )
    flow.locator('.sf-entity-flow__step-buttons button[data-step="2"]').click()
    assert flow.locator(".sf-entity-flow__phase strong").inner_text() == (
        "Trigger publication"
    )
    provider = flow.locator('.sf-entity-flow__entity[data-entity="provider"]')
    assert "is-responsible" in (provider.get_attribute("class") or "")
    assert flow.locator(".sf-entity-flow__message").inner_text() == (
        "TriggerPublication"
    )

    flow.locator('button[data-action="next"]').click()
    assert flow.locator(".sf-entity-flow__phase strong").inner_text() == (
        "Durable acknowledgement"
    )
    agent = flow.locator('.sf-entity-flow__entity[data-entity="agent"]')
    assert "is-responsible" in (agent.get_attribute("class") or "")
    assert page.evaluate(
        "document.documentElement.scrollWidth <= document.documentElement.clientWidth"
    )
    page.close()


@pytest.mark.visual
def test_focus_brand_assets_and_component_accent(
    browser: Browser,
    site_url: str,
) -> None:
    page: Page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.goto(f"{site_url}/v0.1.0/", wait_until="networkidle")

    page.keyboard.press("Tab")
    focused = page.locator(":focus")
    assert focused.count() == 1
    outline = focused.evaluate("element => getComputedStyle(element).outlineStyle")
    assert outline != "none"
    box_shadow = focused.evaluate("element => getComputedStyle(element).boxShadow")
    assert box_shadow != "none"

    component_accent = page.evaluate(
        "getComputedStyle(document.documentElement)"
        ".getPropertyValue('--sf-component-accent').trim()"
    )
    assert component_accent == "#a95000"
    brand = page.evaluate(
        "getComputedStyle(document.documentElement)"
        ".getPropertyValue('--sf-brand').trim()"
    )
    assert brand == "#7fbcfb"
    header_background = page.locator(".md-header").evaluate(
        "element => getComputedStyle(element).backgroundColor"
    )
    assert header_background == "rgb(16, 19, 23)"
    logo_filter = page.locator(".md-header__button.md-logo img").evaluate(
        "element => getComputedStyle(element).filter"
    )
    assert logo_filter == "none"
    assert page.locator('[aria-label="Documentation versions"]').count() == 1
    selector = page.locator("select[data-sf-version-selector]")
    assert selector.evaluate("element => element.tagName") == "SELECT"
    assert selector.input_value() == "./"
    assert selector.locator("option").count() == 2

    selector.select_option(label="v0.2.0")
    page.wait_for_url("**/v0.2.0/")
    assert page.url.endswith("/v0.2.0/")

    for asset in (
        "/assets/images/stateforge-mark.svg",
        "/assets/images/stateforge-favicon.svg",
    ):
        response = page.request.get(f"{site_url}{asset}")
        assert response.ok
        assert response.headers["content-type"].startswith("image/svg+xml")
    page.close()


@pytest.mark.visual
def test_lifecycle_flow_plays_selected_stage(
    browser: Browser,
    site_url: str,
) -> None:
    page: Page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.goto(f"{site_url}/v0.1.0/", wait_until="networkidle")

    lifecycle = page.locator("[data-sf-lifecycle]")
    steps = lifecycle.locator("[data-sf-flow-step]")
    assert steps.count() == 2
    assert steps.nth(0).get_attribute("aria-pressed") == "true"
    assert steps.nth(0).locator("[data-sf-flow-action]").inner_text() == "REPLAY"
    assert steps.nth(1).locator("[data-sf-flow-action]").inner_text() == "PLAY"

    steps.nth(1).click()
    assert steps.nth(1).get_attribute("aria-pressed") == "true"
    assert steps.nth(1).locator("[data-sf-flow-action]").inner_text() == "REPLAY"
    assert lifecycle.locator("[data-sf-flow-source-state]").inner_text() == (
        "Awaits disposition"
    )
    assert lifecycle.locator("[data-sf-flow-target-state]").inner_text() == (
        "Acknowledges state"
    )
    page.wait_for_function(
        "document.querySelector('[data-sf-flow-status]').textContent === "
        "'State acknowledged'"
    )
    assert lifecycle.get_attribute("aria-busy") == "false"
    page.close()
