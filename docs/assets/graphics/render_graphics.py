#!/usr/bin/env python3
"""Render Agent Maintainer README graphics from editable HTML/CSS/SVG sources.

The HTML, CSS, and SVG files in this directory are the source of truth. This
script renders deterministic PNG files for the README and can fail when
committed PNGs are stale.

Usage:
    python docs/assets/graphics/render_graphics.py
    python docs/assets/graphics/render_graphics.py --check
    python docs/assets/graphics/render_graphics.py --target overview
"""

from __future__ import annotations

import argparse
import filecmp
import os
import shutil
import tempfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
STYLE_PATH = ROOT / "style.css"
SYMBOLS_PATH = ROOT / "symbols.svg"
CSS_LINK = '<link rel="stylesheet" href="style.css">'


@dataclass(frozen=True)
class GraphicTarget:
    """One README graphic target."""

    name: str
    html: str
    output: str
    width: int = 1200
    height: int = 900


TARGETS = (
    GraphicTarget("overview", "overview.html", "agent-maintainer-overview.png"),
    GraphicTarget("standard-runs", "standard-runs.html", "standard-runs-at-a-glance.png"),
)
TARGETS_BY_NAME = {target.name: target for target in TARGETS}


def parse_args() -> argparse.Namespace:
    """Parse command-line options."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="render to a temporary directory and fail if committed PNGs are stale",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT,
        help="directory for rendered PNGs; defaults to this graphics directory",
    )
    parser.add_argument(
        "--target",
        choices=("all", *TARGETS_BY_NAME),
        default="all",
        help="render only one graphic target",
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=1.0,
        help="Playwright device scale factor; use 2 for higher-resolution PNGs",
    )
    return parser.parse_args()


def selected_targets(name: str) -> tuple[GraphicTarget, ...]:
    """Return the target set selected by CLI."""
    if name == "all":
        return TARGETS
    return (TARGETS_BY_NAME[name],)


def rendered_html(source: Path) -> str:
    """Inline shared CSS and SVG symbols for stable screenshot rendering."""
    css = STYLE_PATH.read_text(encoding="utf-8")
    symbols = SYMBOLS_PATH.read_text(encoding="utf-8")
    html = source.read_text(encoding="utf-8")
    html = html.replace(CSS_LINK, f"<style>\n{css}\n</style>")
    html = html.replace("symbols.svg#", "#")
    return html.replace("<body>", f"<body>\n{symbols}\n", 1)


def import_playwright() -> tuple[type[Exception], Any]:
    """Import Playwright only for render/check commands, not for --help."""
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover - user-facing environment error
        raise SystemExit(
            "Playwright is required to render graphics. Run: "
            "python -m pip install -r docs/assets/graphics/requirements.txt"
        ) from exc
    return PlaywrightError, sync_playwright


def system_chromium() -> str | None:
    """Return a system Chromium/Chrome executable path when available."""
    env_override = os.environ.get("AGENT_MAINTAINER_GRAPHICS_CHROMIUM")
    if env_override:
        return env_override
    for name in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable"):
        if path := shutil.which(name):
            return path
    return None


def launch_browser(playwright: Any, playwright_error: type[Exception]) -> Any:
    """Launch Chromium, falling back to a system executable if needed."""
    launch_args = {"headless": True, "args": ["--no-sandbox", "--disable-gpu"]}
    try:
        return playwright.chromium.launch(**launch_args)
    except playwright_error:
        executable = system_chromium()
        if executable is None:
            raise SystemExit(
                "Could not launch Chromium. Run `python -m playwright install chromium` "
                "or install a system Chromium package."
            ) from None
        return playwright.chromium.launch(executable_path=executable, **launch_args)


def render_target(browser: Any, target: GraphicTarget, out_dir: Path, *, scale: float) -> None:
    """Render one target PNG by screenshotting the artboard element."""
    page = browser.new_page(
        viewport={"width": target.width, "height": target.height},
        device_scale_factor=scale,
    )
    try:
        page.set_content(rendered_html(ROOT / target.html), wait_until="load")
        page.locator("main.artboard").screenshot(
            path=str(out_dir / target.output),
            animations="disabled",
            caret="hide",
        )
    finally:
        page.close()


def render_all(out_dir: Path, targets: Iterable[GraphicTarget], *, scale: float) -> None:
    """Render all selected graphics."""
    out_dir.mkdir(parents=True, exist_ok=True)
    playwright_error, sync_playwright = import_playwright()
    with sync_playwright() as playwright:
        browser = launch_browser(playwright, playwright_error)
        try:
            for target in targets:
                render_target(browser, target, out_dir, scale=scale)
        finally:
            browser.close()


def stale_outputs(tmp_dir: Path, targets: tuple[GraphicTarget, ...]) -> list[str]:
    """Return target outputs whose rendered PNG differs from the committed PNG."""
    stale: list[str] = []
    for target in targets:
        current = ROOT / target.output
        rendered = tmp_dir / target.output
        if not current.exists() or not filecmp.cmp(rendered, current, shallow=False):
            stale.append(target.output)
    return stale


def check_stale(targets: tuple[GraphicTarget, ...], *, scale: float) -> int:
    """Return nonzero if rendered PNGs differ from committed outputs."""
    with tempfile.TemporaryDirectory(prefix="agent-maintainer-graphics-") as tmp:
        tmp_dir = Path(tmp)
        render_all(tmp_dir, targets, scale=scale)
        stale = stale_outputs(tmp_dir, targets)
    if stale:
        print("Stale generated graphics detected:")
        for output in stale:
            print(f"  {output}")
        print("Run: python docs/assets/graphics/render_graphics.py")
        return 1
    print("Graphics are current.")
    return 0


def main() -> int:
    """Render or check README graphics."""
    args = parse_args()
    targets = selected_targets(args.target)
    if args.check:
        return check_stale(targets, scale=args.scale)
    render_all(args.out_dir, targets, scale=args.scale)
    for target in targets:
        print(f"wrote {args.out_dir / target.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
