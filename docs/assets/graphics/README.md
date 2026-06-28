# Agent Maintainer README graphics

This directory contains the editable source for Agent Maintainer's README
graphics. Do not edit the PNG files directly. Edit the HTML, CSS, or SVG
symbols, then rerender.

## Files

```text
docs/assets/graphics/
  overview.html                       # overview graphic source
  standard-runs.html                  # run comparison graphic source
  style.css                           # shared design tokens and layout
  symbols.svg                         # local SVG symbol library
  render_graphics.py                  # renderer/checker
  requirements.txt                    # optional renderer dependency
  agent-maintainer-overview.png       # rendered README image
  standard-runs-at-a-glance.png       # rendered README image
```

## Render

```bash
python -m pip install -r docs/assets/graphics/requirements.txt
python -m playwright install chromium  # optional if system Chromium exists
python docs/assets/graphics/render_graphics.py
```

Render one graphic:

```bash
python docs/assets/graphics/render_graphics.py --target overview
python docs/assets/graphics/render_graphics.py --target standard-runs
```

Use a system Chromium explicitly:

```bash
AGENT_MAINTAINER_GRAPHICS_CHROMIUM=/usr/bin/chromium \
  python docs/assets/graphics/render_graphics.py
```

## Check for stale PNGs

```bash
python docs/assets/graphics/render_graphics.py --check
```

## Suggested justfile entries

```make
render-graphics:
    python docs/assets/graphics/render_graphics.py

check-graphics:
    python docs/assets/graphics/render_graphics.py --check
```

## Editing rules

- Keep copy short enough to stay readable at 900 px README width.
- Use `symbols.svg` for icons; avoid external logo dependencies.
- Use text-only support labels such as `Supports: Codex · Claude Code`.
- Keep robot icons for agents and hook icons for hook mechanisms.
- Do not reintroduce old project names or old config namespaces.
- Update both PNGs whenever source HTML, CSS, or SVG changes.
