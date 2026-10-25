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
    page.emulate_media(color_scheme=scheme)
    page.goto(f"{site_url}/v0.1.0/", wait_until="networkidle")

    assert page.locator("body").get_attribute("data-md-color-scheme") == (
        expected_palette
    )
    assert page.locator(".sf-version-selector").is_visible()
    assert page.locator(".sf-historical-warning").is_visible()
    assert page.locator(".md-header__source").is_visible() is (width >= 1220)
    assert page.evaluate(
        "document.documentElement.scrollWidth <= document.documentElement.clientWidth"
    )
    assert page.locator("stateforge-procedure-player").is_visible()

    evidence = Path(os.environ.get("STATEFORGE_VISUAL_EVIDENCE", str(tmp_path)))
    evidence.mkdir(parents=True, exist_ok=True)
    page.screenshot(
        path=evidence / f"fixture-{width}-{scheme}.png",
        full_page=True,
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

    accent = page.evaluate(
        "getComputedStyle(document.documentElement)"
        ".getPropertyValue('--sf-accent').trim()"
    )
    assert accent == "#a95000"
    logo_filter = page.locator(".md-header__button.md-logo img").evaluate(
        "element => getComputedStyle(element).filter"
    )
    assert logo_filter != "none"
    assert page.locator('[aria-label="Documentation versions"]').count() == 1
    assert page.locator('[aria-current="page"]').get_attribute("href") == "./"

    for asset in (
        "/assets/images/stateforge-mark.svg",
        "/assets/images/stateforge-favicon.svg",
    ):
        response = page.request.get(f"{site_url}{asset}")
        assert response.ok
        assert response.headers["content-type"].startswith("image/svg+xml")
    page.close()
