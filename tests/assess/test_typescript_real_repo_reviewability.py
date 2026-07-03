"""End-to-end TypeScript reviewability evidence from temporary Git repos."""

from __future__ import annotations

import json
import shutil
import subprocess  # nosec B404
from pathlib import Path
from typing import Any

import pytest

from agent_maintainer.assess import cli

LOW_NOISE_CHANGED_FILES = 2
HEAVY_SOURCE_FILES = 4
HEAVY_SOURCE_LINES = 200
ONE_BROAD_SUPPRESSION = 1


# docsync:evidence.start evidence.typescript.real_repo_reviewability_tests
def test_typescript_real_repo_source_plus_test_stays_low_noise(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A real TypeScript source-plus-test diff reports evidence without findings."""
    repo = _typescript_repo(tmp_path)
    _write(
        repo / "src/ui/Button.tsx",
        "\n".join(
            (
                "export function Button() {",
                "  return <button>Save</button>;",
                "}",
            ),
        ),
    )
    _write(
        repo / "src/ui/Button.test.tsx",
        "\n".join(
            (
                "import { Button } from './Button';",
                "test('renders label', () => {",
                "  expect(Button).toBeDefined();",
                "});",
            ),
        ),
    )

    payload = _run_reviewability_json(repo, capsys)

    assert payload["total_changed_files"] == LOW_NOISE_CHANGED_FILES
    assert payload["classified_files"] == LOW_NOISE_CHANGED_FILES
    assert payload["unclassified_files"] == 0
    assert payload["advisory_findings"] == []
    assert payload["broad_suppressions"] == 0

    summary = _summary(payload, "typescript")
    assert summary["source_files"] == 1
    assert summary["test_files"] == 1
    assert summary["source_lines"] > 0
    assert summary["test_lines"] > 0


def test_typescript_real_repo_source_heavy_without_tests_reports_advisories(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A real TypeScript source-only heavy diff reports advisory risk facts."""
    repo = _typescript_repo(tmp_path)
    for name in ("client", "session", "settings", "routing"):
        _write(
            repo / f"src/app/{name}.ts",
            _typescript_lines(name, include_broad_suppression=(name == "client")),
        )

    payload = _run_reviewability_json(repo, capsys)

    summary = _summary(payload, "typescript")
    assert summary["source_files"] == HEAVY_SOURCE_FILES
    assert summary["test_files"] == 0
    assert summary["source_lines"] >= HEAVY_SOURCE_LINES
    assert summary["broad_suppressions"] == ONE_BROAD_SUPPRESSION

    finding_kinds = {
        finding["kind"]
        for finding in payload["advisory_findings"]
        if finding["ecosystem"] == "typescript"
    }
    assert finding_kinds == {
        "broad-suppression",
        "source-heavy",
        "source-without-test",
    }
    assert payload["broad_suppressions"] == ONE_BROAD_SUPPRESSION
    assert payload["suppressions"][0]["broad"] is True


def test_typescript_real_repo_npm_vite_vitest_shape_stays_low_noise(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An npm Vite/Vitest-shaped source-plus-test diff stays advisory-only."""

    repo = _typescript_repo(tmp_path)
    _write(
        repo / "package.json",
        "\n".join(
            (
                '{"scripts":{"lint":"eslint .","typecheck":"tsc --noEmit",',
                '"test":"vitest run"},"devDependencies":{"@vitejs/plugin-react":"latest"}}',
            ),
        )
        + "\n",
    )
    _write(
        repo / "vite.config.ts",
        "import { defineConfig } from 'vite';\nexport default defineConfig({});\n",
    )
    _write(
        repo / "vitest.config.ts",
        "import { defineConfig } from 'vitest/config';\nexport default defineConfig({});\n",
    )
    _write(
        repo / "src/ui/Card.tsx",
        "export function Card() {\n return <section>Ready</section>;\n}\n",
    )
    _write(
        repo / "src/ui/Card.test.tsx",
        "import { Card } from './Card';\ntest('renders card', () => Card());\n",
    )
    _git(
        repo,
        "add",
        "package.json",
        "vite.config.ts",
        "vitest.config.ts",
        "src/ui/Card.tsx",
        "src/ui/Card.test.tsx",
    )

    payload = _run_reviewability_json(repo, capsys)

    assert payload["advisory_findings"] == []
    assert _role_counts(payload) == {"config": 3, "source": 1, "test": 1}
    summary = _summary(payload, "typescript")
    assert summary["source_files"] == 1
    assert summary["test_files"] == 1
    assert summary["changed_files"] == LOW_NOISE_CHANGED_FILES


def test_typescript_real_repo_pnpm_config_lockfile_shape_stays_low_noise(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A pnpm config lockfile diff reports roles without source advisories."""

    repo = _typescript_repo(tmp_path)
    _write(
        repo / "package.json",
        '{"packageManager":"pnpm@9.0.0","scripts":{"test":"vitest run"}}\n',
    )
    _write(repo / "pnpm-lock.yaml", "lockfileVersion: '9.0'\n")
    _write(repo / "tsconfig.json", '{"compilerOptions":{"strict":true}}\n')
    _git(repo, "add", "package.json", "pnpm-lock.yaml", "tsconfig.json")

    payload = _run_reviewability_json(repo, capsys)

    assert payload["advisory_findings"] == []
    assert _role_counts(payload) == {"config": 2, "dependency": 1}
    summary = _summary(payload, "typescript")
    assert summary["changed_files"] == 1
    assert summary["source_files"] == 0
    assert summary["test_files"] == 0


# docsync:evidence.end evidence.typescript.real_repo_reviewability_tests


def _typescript_repo(tmp_path: Path) -> Path:
    """Create a committed TypeScript repo baseline with Agent Maintainer enabled."""
    if shutil.which("git") is None:
        pytest.skip("git executable is required for real-repo reviewability evidence")

    repo = tmp_path / "typescript-repo"
    repo.mkdir()
    _write(
        repo / "pyproject.toml",
        "\n".join(
            (
                "[tool.agent_maintainer]",
                "enable_typescript = true",
                'typescript_lint_command = ["npm", "run", "lint"]',
                'typescript_typecheck_command = ["npm", "run", "typecheck"]',
                'typescript_test_command = ["npm", "test"]',
                "",
            ),
        ),
    )
    _write(repo / "package.json", '{"scripts":{"lint":"eslint .","test":"jest"}}\n')
    _write(repo / "src/ui/Button.tsx", "export function Button() { return null; }\n")
    _write(repo / "src/ui/Button.test.tsx", "test('baseline', () => undefined);\n")
    for name in ("client", "session", "settings", "routing"):
        _write(repo / f"src/app/{name}.ts", f"export const {name} = true;\n")

    _git(repo, "init")
    _git(repo, "config", "user.name", "Agent Maintainer Test")
    _git(repo, "config", "user.email", "agent-maintainer@example.test")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "baseline")
    return repo


def _run_reviewability_json(
    repo: Path,
    capsys: pytest.CaptureFixture[str],
) -> dict[str, Any]:
    """Run public reviewability CLI and return parsed JSON payload."""
    status = cli.main(
        [
            "reviewability",
            "--target",
            str(repo),
            "--base-ref",
            "HEAD",
            "--json",
        ],
    )
    assert status == 0
    return json.loads(capsys.readouterr().out)


def _summary(payload: dict[str, Any], ecosystem: str) -> dict[str, Any]:
    """Return one provider summary from reviewability JSON."""
    summaries = {summary["ecosystem"]: summary for summary in payload["provider_summaries"]}
    return summaries[ecosystem]


def _role_counts(payload: dict[str, Any]) -> dict[str, int]:
    """Return changed-file role counts from reviewability JSON."""
    return {item["key"]: item["count"] for item in payload["by_role"]}


def _typescript_lines(name: str, *, include_broad_suppression: bool) -> str:
    """Return enough changed TypeScript source lines to trigger heavy advisory."""
    lines = ["// eslint-disable" if include_broad_suppression else f"// {name}"]
    lines.extend(f"export const {name}_{index} = {index};" for index in range(60))
    return "\n".join(lines) + "\n"


def _write(path: Path, content: str) -> None:
    """Write fixture content, creating parent directories."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _git(repo: Path, *args: str) -> None:
    """Run a Git command in the fixture repository."""
    subprocess.run(  # nosec B603
        ["git", *args],
        cwd=repo,
        check=True,
        text=True,
        capture_output=True,
    )
