"""Import policy tests for the package layout."""

from __future__ import annotations

from pathlib import Path

FORBIDDEN_IMPORT_FRAGMENTS = (
    "from scripts",
    "import scripts",
    "scripts." + "guard" + "rail_core",
    "scripts." + "guard" + "rail_catalogs",
    "scripts." + "guard" + "rail_doctor",
    "scripts.verify_quiet",
    "guard" + "rail_" + "lib",
    "ai_" + "guard" + "rails",
    "ai-" + "guard" + "rails",
    "[tool." + "ai_" + "guard" + "rails]",
    "AGENTS." + "guard" + "rails.md",
)


def test_package_code_does_not_import_legacy_script_modules() -> None:
    """Keep implementation imports package-first after the src migration."""

    roots = (Path("src/agent_maintainer"), Path(".codex/hooks"))
    offenders: list[str] = []
    for root in roots:
        for path in root.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            if any(fragment in text for fragment in FORBIDDEN_IMPORT_FRAGMENTS):
                offenders.append(path.as_posix())

    assert offenders == []
