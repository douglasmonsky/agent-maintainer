"""Import policy tests for the package layout."""

from __future__ import annotations

from pathlib import Path

FORBIDDEN_IMPORT_FRAGMENTS = (
    "from scripts",
    "import scripts",
    "scripts.guardrail_core",
    "scripts.guardrail_catalogs",
    "scripts.guardrail_doctor",
    "scripts.verify_quiet",
    "guardrail_lib",
)


def test_package_code_does_not_import_legacy_script_modules() -> None:
    """Keep implementation imports package-first after the src migration."""

    roots = (Path("src/ai_guardrails"), Path(".codex/hooks"))
    offenders: list[str] = []
    for root in roots:
        for path in root.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            if any(fragment in text for fragment in FORBIDDEN_IMPORT_FRAGMENTS):
                offenders.append(path.as_posix())

    assert offenders == []
