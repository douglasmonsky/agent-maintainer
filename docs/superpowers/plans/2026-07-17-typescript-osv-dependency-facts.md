# TypeScript OSV Dependency Facts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add safe, deduplicated OSV Scanner v2 repair facts and shared compact summaries over the existing optional ecosystem-neutral scanner.

**Architecture:** A new dependency-free `agent_repair_facts.parsers.osv_scanner` module owns OSV v2 validation, alias grouping, fixed-version extraction, source-path safety, deterministic ordering, and exact fact rendering. The artifact registry and `agent_maintainer.core.structured_security` consume that boundary, while the existing scanner command, configuration, profiles, and exit semantics remain unchanged.

**Tech Stack:** Python 3.11–3.14, dataclasses, pathlib, pytest, Ruff, Wemake, Tach, DocSync, Markdownlint, OSV Scanner v2 JSON.

## Global Constraints

- Reuse `enable_osv_scanner`, `osv_scanner_args`, and `osv_scanner_profiles`; add no TypeScript-specific OSV command.
- Keep OSV disabled by default and on the existing `manual` default profile.
- Emit one normalized finding per valid OSV alias group and one fallback finding for every ungrouped valid advisory.
- Read current package versions from `packages[].package.version`, with outer `packages[].version` only as a legacy fallback.
- Collect fixes only from valid `affected[].ranges[].events[].fixed` values.
- Reject absolute, drive-qualified, empty, `.` identity, and parent-traversal fact paths; unsafe paths may expose only a safe filename label.
- Sort before retaining at most 500 normalized findings.
- Emit at most 50 compact lines; exact context retains the existing five-fact-per-check limit.
- Perform no subprocess, network, repository discovery, or filesystem traversal in the parser.
- Store only bounded projections of public captures; never commit absolute temporary paths or full oversized advisory bodies.
- Keep TypeScript/JavaScript experimental; defer package-manager audit facts, automatic fixes, thresholds, and promotion.
- Add an ADR for every new Tach dependency edge.

---

### Task 1: Normalize OSV Scanner V2 Findings And Exact Facts

**Files:**

- Create: `src/agent_repair_facts/parsers/osv_scanner.py`
- Create: `tests/fixtures/osv_scanner/v2-grouped.json`
- Create: `tests/repair_facts/test_osv_scanner_facts.py`
- Modify: `src/agent_repair_facts/registry.py`
- Modify: `src/agent_repair_facts/tach.domain.toml`

**Interfaces:**

- Consumes: `agent_repair_facts.payloads.FactSource`, `json_object`, `json_array`, `json_objects`, `optional_text`, `read_json`, and `fact_payload`.
- Produces: `OSV_FACT_LIMIT: int`, `OsvFinding`, `OsvParseResult`, `parse_osv_payload(payload: object) -> OsvParseResult`, `format_osv_finding(finding: OsvFinding) -> str`, and `osv_facts(source: FactSource, check: str) -> list[dict[str, object]]`.
- Registry contract: `ARTIFACT_FACT_PARSERS` maps exact check name `osv-scanner` to `osv_facts`.

- [ ] **Step 1: Add the current-v2 grouped fixture**

Create `tests/fixtures/osv-scanner/v2-grouped.json` with one safe npm source, one unsafe absolute pnpm source, alias groups, nested versions, fixed range events, and a malformed neighbor:

```json
{
  "results": [
    {
      "source": {"path": "apps/web/package-lock.json", "type": "lockfile"},
      "packages": [
        {
          "package": {"ecosystem": "npm", "name": "lodash", "version": "4.17.20"},
          "vulnerabilities": [
            {
              "id": "CVE-2021-23337",
              "aliases": ["GHSA-35jh-r3h4-6jhm"],
              "summary": "Command injection in lodash",
              "affected": [
                {"ranges": [{"events": [{"introduced": "0"}, {"fixed": "4.17.21"}]}]}
              ]
            },
            {
              "id": "GHSA-35jh-r3h4-6jhm",
              "aliases": ["CVE-2021-23337"],
              "summary": "Alias record for the same vulnerability",
              "affected": [
                {"ranges": [{"events": [{"fixed": "4.17.21"}, {"last_affected": "4.17.20"}]}]}
              ]
            }
          ],
          "groups": [
            {
              "ids": ["GHSA-35jh-r3h4-6jhm", "CVE-2021-23337"],
              "aliases": ["CVE-2021-23337", "GHSA-35jh-r3h4-6jhm"],
              "max_severity": "HIGH"
            }
          ]
        },
        {"package": {"name": 7}, "vulnerabilities": "bad"}
      ]
    },
    {
      "source": {"path": "/Users/example/project/pnpm-lock.yaml", "type": "lockfile"},
      "packages": [
        {
          "package": {"ecosystem": "npm", "name": "demo", "version": "1.0.0"},
          "vulnerabilities": [
            {"id": "GHSA-demo", "aliases": [], "summary": "A standalone advisory"}
          ],
          "groups": []
        }
      ]
    }
  ]
}
```

- [ ] **Step 2: Write failing parser and registry tests**

Create `tests/repair_facts/test_osv_scanner_facts.py` with explicit DocSync markers and these tests:

```python
"""Tests exact repair facts from OSV Scanner v2 JSON artifacts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_repair_facts import registry
from agent_repair_facts.parsers import osv_scanner

FIXTURE = Path(__file__).parents[1] / "fixtures" / "osv-scanner" / "v2-grouped.json"


def artifact_facts(payload: object) -> list[dict[str, object]]:
    return registry.artifact_facts_from_text(
        "osv-scanner",
        Path(".verify-logs/osv-scanner.json"),
        json.dumps(payload),
    )


# docsync:evidence.start evidence.typescript.osv_fact_tests
def test_osv_v2_groups_emit_safe_deduplicated_facts() -> None:
    facts = registry.artifact_facts(
        "osv-scanner",
        FIXTURE,
    )

    assert facts == [
        {
            "check": "osv-scanner",
            "path": "apps/web/package-lock.json",
            "line": None,
            "column": None,
            "symbol": "CVE-2021-23337",
            "message": (
                "npm/lodash 4.17.20: CVE-2021-23337 "
                "(GHSA-35jh-r3h4-6jhm); source: apps/web/package-lock.json; "
                "fix: 4.17.21; severity: HIGH; Command injection in lodash"
            ),
            "severity": "error",
        },
        {
            "check": "osv-scanner",
            "path": None,
            "line": None,
            "column": None,
            "symbol": "GHSA-demo",
            "message": (
                "npm/demo 1.0.0: GHSA-demo; source: pnpm-lock.yaml; "
                "A standalone advisory"
            ),
            "severity": "error",
        },
    ]


def test_osv_nested_version_wins_with_legacy_outer_fallback() -> None:
    payload = {
        "results": [
            {
                "source": {"path": "package-lock.json", "type": "lockfile"},
                "packages": [
                    {
                        "package": {"ecosystem": "npm", "name": "nested", "version": "2"},
                        "version": "1",
                        "vulnerabilities": [{"id": "OSV-NESTED"}],
                    },
                    {
                        "package": {"ecosystem": "npm", "name": "legacy"},
                        "version": "3",
                        "vulnerabilities": [{"id": "OSV-LEGACY"}],
                    },
                ],
            }
        ]
    }

    messages = [fact["message"] for fact in artifact_facts(payload)]
    assert messages[0].startswith("npm/legacy 3: OSV-LEGACY")
    assert messages[1].startswith("npm/nested 2: OSV-NESTED")


@pytest.mark.parametrize("payload", [None, [], {}, {"results": {}}, {"results": [None, {}]}])
def test_osv_invalid_payloads_emit_no_facts(payload: object) -> None:
    assert artifact_facts(payload) == []


def test_osv_malformed_group_does_not_hide_valid_vulnerability() -> None:
    payload = {
        "results": [
            {
                "source": {"path": "package-lock.json", "type": "lockfile"},
                "packages": [
                    {
                        "package": {"ecosystem": "npm", "name": "demo", "version": "1"},
                        "vulnerabilities": [{"id": "OSV-1"}, {"id": "OSV-2"}],
                        "groups": [{"ids": ["OSV-1"]}, {"ids": "bad"}],
                    }
                ],
            }
        ]
    }

    assert [fact["symbol"] for fact in artifact_facts(payload)] == ["OSV-1", "OSV-2"]


def test_osv_sorts_before_the_retention_limit() -> None:
    vulnerabilities = [
        {"id": f"OSV-{index:03d}"}
        for index in range(osv_scanner.OSV_FACT_LIMIT, -1, -1)
    ]
    payload = {
        "results": [
            {
                "source": {"path": "package-lock.json", "type": "lockfile"},
                "packages": [
                    {
                        "package": {"ecosystem": "npm", "name": "demo", "version": "1"},
                        "vulnerabilities": vulnerabilities,
                    }
                ],
            }
        ]
    }

    facts = artifact_facts(payload)
    assert len(facts) == osv_scanner.OSV_FACT_LIMIT
    assert facts[0]["symbol"] == "OSV-000"
    assert facts[-1]["symbol"] == "OSV-499"
# docsync:evidence.end evidence.typescript.osv_fact_tests
```

- [ ] **Step 3: Run the new tests and verify the expected failure**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/pytest tests/repair_facts/test_osv_scanner_facts.py -q
```

Expected: collection fails because `agent_repair_facts.parsers.osv_scanner` does not exist or registry returns no OSV facts.

- [ ] **Step 4: Implement the typed parser boundary**

Create `src/agent_repair_facts/parsers/osv_scanner.py` with these public types and functions:

```python
"""Parse bounded OSV Scanner v2 findings and exact repair facts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath, PureWindowsPath

from agent_repair_facts import payloads

OSV_FACT_LIMIT = 500
OSV_SUMMARY_CHAR_LIMIT = 200


@dataclass(frozen=True)
class OsvFinding:
    path: str | None
    source_label: str
    source_type: str
    ecosystem: str
    package: str
    version: str
    advisory: str
    aliases: tuple[str, ...]
    fixed_versions: tuple[str, ...]
    max_severity: str | None
    summary: str | None


@dataclass(frozen=True)
class OsvParseResult:
    findings: tuple[OsvFinding, ...]
    supported_count: int
    valid: bool


def parse_osv_payload(payload: object) -> OsvParseResult:
    root = payloads.json_object(payload)
    if root is None:
        return OsvParseResult((), 0, False)
    results = payloads.json_array(root.get("results"))
    if results is None:
        return OsvParseResult((), 0, False)
    findings: list[OsvFinding] = []
    for result in payloads.json_objects(results):
        findings.extend(_result_findings(result))
    findings.sort(key=_finding_sort_key)
    return OsvParseResult(
        tuple(findings[:OSV_FACT_LIMIT]),
        len(findings),
        True,
    )


def osv_facts(source: payloads.FactSource, check: str) -> list[dict[str, object]]:
    parsed = parse_osv_payload(payloads.read_json(source))
    return [_fact(check, finding) for finding in parsed.findings]


def format_osv_finding(finding: OsvFinding) -> str:
    base = f"{finding.ecosystem}/{finding.package} {finding.version}: {finding.advisory}"
    if finding.aliases:
        base = f"{base} ({', '.join(finding.aliases)})"
    details = [f"source: {finding.source_label}"]
    if finding.fixed_versions:
        details.append(f"fix: {', '.join(finding.fixed_versions)}")
    if finding.max_severity:
        details.append(f"severity: {finding.max_severity}")
    if finding.summary:
        details.append(finding.summary)
    return "; ".join((base, *details))
```

Implement the private normalization helpers with this complete behavior:

```python
@dataclass(frozen=True)
class _SourceInfo:
    path: str | None
    label: str
    source_type: str


def _result_findings(result: dict[str, object]) -> list[OsvFinding]:
    source = _source_info(result.get("source"))
    findings: list[OsvFinding] = []
    for item in payloads.json_objects(result.get("packages")):
        findings.extend(_package_findings(source, item))
    return findings


def _package_findings(source: _SourceInfo, item: dict[str, object]) -> list[OsvFinding]:
    package_info = payloads.json_object(item.get("package"))
    if package_info is None:
        return []
    name = payloads.optional_text(package_info.get("name"))
    version = payloads.optional_text(package_info.get("version")) or payloads.optional_text(
        item.get("version")
    )
    if name is None or version is None:
        return []
    ecosystem = payloads.optional_text(package_info.get("ecosystem")) or "<unknown>"
    vulnerabilities = tuple(payloads.json_objects(item.get("vulnerabilities")))
    by_id = {
        advisory: vulnerability
        for vulnerability in vulnerabilities
        if (advisory := payloads.optional_text(vulnerability.get("id"))) is not None
    }
    referenced: set[str] = set()
    findings: list[OsvFinding] = []
    for group in payloads.json_objects(item.get("groups")):
        ids = tuple(sorted(set(_text_values(group.get("ids"))) & by_id.keys()))
        if not ids:
            continue
        referenced.update(ids)
        findings.append(
            _group_finding(source, ecosystem, name, version, ids, group, by_id)
        )
    for advisory in sorted(by_id.keys() - referenced):
        findings.append(
            _fallback_finding(
                source,
                ecosystem,
                name,
                version,
                advisory,
                by_id[advisory],
            )
        )
    return findings


def _group_finding(
    source: _SourceInfo,
    ecosystem: str,
    package: str,
    version: str,
    ids: tuple[str, ...],
    group: dict[str, object],
    vulnerabilities: dict[str, dict[str, object]],
) -> OsvFinding:
    canonical = ids[0]
    records = tuple(vulnerabilities[advisory] for advisory in ids)
    aliases = set(ids[1:])
    aliases.update(_text_values(group.get("aliases")))
    for record in records:
        aliases.update(_text_values(record.get("aliases")))
    aliases.discard(canonical)
    return OsvFinding(
        path=source.path,
        source_label=source.label,
        source_type=source.source_type,
        ecosystem=ecosystem,
        package=package,
        version=version,
        advisory=canonical,
        aliases=tuple(sorted(aliases)),
        fixed_versions=_fixed_versions(records),
        max_severity=payloads.optional_text(group.get("max_severity")),
        summary=_summary(vulnerabilities.get(canonical) or records[0]),
    )


def _fallback_finding(
    source: _SourceInfo,
    ecosystem: str,
    package: str,
    version: str,
    advisory: str,
    vulnerability: dict[str, object],
) -> OsvFinding:
    aliases = set(_text_values(vulnerability.get("aliases")))
    aliases.discard(advisory)
    return OsvFinding(
        path=source.path,
        source_label=source.label,
        source_type=source.source_type,
        ecosystem=ecosystem,
        package=package,
        version=version,
        advisory=advisory,
        aliases=tuple(sorted(aliases)),
        fixed_versions=_fixed_versions((vulnerability,)),
        max_severity=None,
        summary=_summary(vulnerability),
    )


def _fixed_versions(vulnerabilities: tuple[dict[str, object], ...]) -> tuple[str, ...]:
    fixes: set[str] = set()
    for vulnerability in vulnerabilities:
        for affected in payloads.json_objects(vulnerability.get("affected")):
            for value_range in payloads.json_objects(affected.get("ranges")):
                for event in payloads.json_objects(value_range.get("events")):
                    fixed = payloads.optional_text(event.get("fixed"))
                    if fixed is not None:
                        fixes.add(fixed)
    return tuple(sorted(fixes))


def _summary(vulnerability: dict[str, object] | None) -> str | None:
    if vulnerability is None:
        return None
    raw = payloads.optional_text(vulnerability.get("summary"))
    if raw is None:
        return None
    text = " ".join(raw.split())
    if len(text) <= OSV_SUMMARY_CHAR_LIMIT:
        return text
    return f"{text[: OSV_SUMMARY_CHAR_LIMIT - 3].rstrip()}..."


def _source_info(value: object) -> _SourceInfo:
    source = payloads.json_object(value) or {}
    path, label = _safe_source_path(source.get("path"))
    source_type = payloads.optional_text(source.get("type")) or "unknown"
    return _SourceInfo(path, label, source_type)


def _safe_source_path(value: object) -> tuple[str | None, str]:
    text = payloads.optional_text(value)
    if text is None:
        return (None, "<unknown source>")
    windows_path = PureWindowsPath(text)
    posix_path = PurePosixPath(text.replace("\\", "/"))
    filename = windows_path.name or posix_path.name or "<unknown source>"
    unsafe = (
        posix_path.is_absolute()
        or windows_path.is_absolute()
        or bool(windows_path.drive)
        or ".." in posix_path.parts
        or posix_path.as_posix() == "."
    )
    if unsafe:
        return (None, filename)
    normalized = posix_path.as_posix()
    return (normalized, normalized)


def _text_values(value: object) -> tuple[str, ...]:
    values = payloads.json_array(value) or []
    return tuple(
        text
        for item in values
        if (text := payloads.optional_text(item)) is not None
    )


def _finding_sort_key(finding: OsvFinding) -> tuple[str, str, str, str, str]:
    return (
        finding.source_label,
        finding.ecosystem,
        finding.package,
        finding.version,
        finding.advisory,
    )


def _fact(check: str, finding: OsvFinding) -> dict[str, object]:
    return payloads.fact_payload(
        {
            "check": check,
            "path": finding.path,
            "symbol": finding.advisory,
            "message": format_osv_finding(finding),
            "severity": "error",
        }
    )
```

- [ ] **Step 5: Register the artifact parser and Tach module**

Modify `src/agent_repair_facts/registry.py` by adding this import to the existing
parser import group:

```python
from agent_repair_facts.parsers import osv_scanner
```

Add this entry immediately after `pip-audit` in `ARTIFACT_FACT_PARSERS`:

```python
("osv-scanner", osv_scanner.osv_facts),
```

Modify `src/agent_repair_facts/tach.domain.toml` so `registry` depends on `parsers.osv_scanner`, and declare:

```toml
[[modules]]
path = "parsers.osv_scanner"
depends_on = [
  "payloads",
]
```

- [ ] **Step 6: Run focused parser checks**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/pytest tests/repair_facts/test_osv_scanner_facts.py tests/repair_facts/test_security_repair_facts.py -q
.venv/bin/ruff check src/agent_repair_facts/parsers/osv_scanner.py src/agent_repair_facts/registry.py tests/repair_facts/test_osv_scanner_facts.py
.venv/bin/ruff format --check src/agent_repair_facts/parsers/osv_scanner.py src/agent_repair_facts/registry.py tests/repair_facts/test_osv_scanner_facts.py
```

Expected: all tests and static checks pass.

- [ ] **Step 7: Commit exact facts**

```bash
git add -- src/agent_repair_facts/parsers/osv_scanner.py src/agent_repair_facts/registry.py src/agent_repair_facts/tach.domain.toml tests/fixtures/osv-scanner/v2-grouped.json tests/repair_facts/test_osv_scanner_facts.py
git commit -m "feat: parse OSV dependency facts"
```

### Task 2: Share OSV Findings With Compact Summaries And Context

**Files:**

- Create: `tests/core/test_osv_structured_output.py`
- Create: `tests/context/test_osv_exact_facts.py`
- Create: `docs/architecture/decisions/2026-07-17-osv-parser-boundary.md`
- Modify: `src/agent_maintainer/core/structured_security.py`
- Modify: `src/agent_maintainer/core/tach.domain.toml`
- Modify: `tests/core/test_structured_artifact_summaries.py`

**Interfaces:**

- Consumes: Task 1 `parse_osv_payload`, `OsvParseResult`, and `format_osv_finding`.
- Produces: `summarize_osv_payload(payload: object) -> str | None` backed exclusively by the shared parser.
- Preserves: `structured_artifact_summary("osv-scanner", paths)` and the existing context builder APIs.

- [ ] **Step 1: Add failing compact-summary tests**

Create `tests/core/test_osv_structured_output.py`:

```python
"""Tests bounded OSV Scanner v2 artifact summaries."""

from __future__ import annotations

from agent_maintainer.core import structured_security

OSV_SUMMARY_LINE_LIMIT = 50


# docsync:evidence.start evidence.typescript.osv_summary_tests
def test_osv_summary_uses_nested_version_and_alias_group() -> None:
    payload = {
        "results": [
            {
                "source": {"path": "package-lock.json", "type": "lockfile"},
                "packages": [
                    {
                        "package": {"ecosystem": "npm", "name": "demo", "version": "2"},
                        "version": "1",
                        "vulnerabilities": [
                            {"id": "CVE-1", "aliases": ["GHSA-1"], "summary": "demo issue"},
                            {"id": "GHSA-1", "aliases": ["CVE-1"]},
                        ],
                        "groups": [{"ids": ["GHSA-1", "CVE-1"]}],
                    }
                ],
            }
        ]
    }

    assert structured_security.summarize_osv_payload(payload) == (
        "npm/demo 2: CVE-1 (GHSA-1); source: package-lock.json; demo issue"
    )


def test_osv_summary_reserves_final_line_for_omission_marker() -> None:
    payload = _payload_with_findings(51)
    summary = structured_security.summarize_osv_payload(payload)
    assert summary is not None
    lines = summary.splitlines()
    assert len(lines) == OSV_SUMMARY_LINE_LIMIT
    assert lines[-1] == "... 2 more OSV vulnerabilities omitted. See .verify-logs/osv-scanner.json"


def test_osv_invalid_payload_has_no_summary() -> None:
    assert structured_security.summarize_osv_payload({}) is None


def _payload_with_findings(count: int) -> dict[str, object]:
    return {
        "results": [
            {
                "source": {"path": "package-lock.json", "type": "lockfile"},
                "packages": [
                    {
                        "package": {"ecosystem": "npm", "name": "demo", "version": "1"},
                        "vulnerabilities": [{"id": f"OSV-{index:03d}"} for index in range(count)],
                    }
                ],
            }
        ]
    }
# docsync:evidence.end evidence.typescript.osv_summary_tests
```

- [ ] **Step 2: Add a failing exact-context bound test**

Create `tests/context/test_osv_exact_facts.py` with a failed `FailureRecord` whose `artifact_paths` contains a temporary `osv-scanner.json` holding seven advisories. Call `exact_facts.repair_facts(tmp_path, (record,))` and assert:

```python
assert len(facts) == 5
assert [fact["symbol"] for fact in facts] == [f"OSV-{index:03d}" for index in range(5)]
```

Use the exact record shape:

```python
FailureRecord(
    name="osv-scanner",
    status="failed",
    category="security/tooling",
    priority=9,
    exit_code=1,
    log_path=str(tmp_path / "osv-scanner.log"),
    log_bytes=0,
    expansion_commands=(),
    artifact_paths=(str(artifact_path),),
)
```

- [ ] **Step 3: Run the focused tests and verify schema drift fails**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/pytest tests/core/test_osv_structured_output.py tests/context/test_osv_exact_facts.py tests/core/test_structured_artifact_summaries.py -q
```

Expected: the current summary emits the legacy version or duplicate advisory lines; new shared-parser expectations fail.

- [ ] **Step 4: Replace the duplicate OSV summary walk**

Modify `src/agent_maintainer/core/structured_security.py`:

```python
from agent_repair_facts.parsers import osv_scanner


def summarize_osv_payload(payload: object) -> str | None:
    """Summarize bounded normalized OSV Scanner vulnerabilities."""

    parsed = osv_scanner.parse_osv_payload(payload)
    if not parsed.valid or not parsed.findings:
        return None
    visible_limit = STRUCTURED_DIAGNOSTIC_LIMIT - 1
    if parsed.supported_count <= STRUCTURED_DIAGNOSTIC_LIMIT:
        return "\n".join(map(osv_scanner.format_osv_finding, parsed.findings))
    lines = [
        osv_scanner.format_osv_finding(finding)
        for finding in parsed.findings[:visible_limit]
    ]
    omitted = parsed.supported_count - visible_limit
    lines.append(
        f"... {omitted} more OSV vulnerabilities omitted. "
        "See .verify-logs/osv-scanner.json"
    )
    return "\n".join(lines)
```

Remove only the now-unused OSV-specific helpers: `osv_result_lines`,
`osv_package_lines`, `osv_package_name`, `vulnerabilities`, and
`osv_vulnerability_count`. Keep Semgrep, Gitleaks, pip-audit, shared value
helpers, and `append_omitted` behavior unchanged.

Update the OSV payload in `tests/core/test_structured_artifact_summaries.py` to
put `version` inside `package`, add `source`, and retain the expected concise
summary with source provenance.

- [ ] **Step 5: Declare and document the architecture boundary**

Modify the `structured_security` entry in `src/agent_maintainer/core/tach.domain.toml`:

```toml
[[modules]]
path = "structured_security"
depends_on = [
  "structured_values",
  "//agent_repair_facts.parsers.osv_scanner",
]
```

Create `docs/architecture/decisions/2026-07-17-osv-parser-boundary.md` with
Status, Context, Decision, Why This Is Not Architecture Drift, Alternatives
Considered, and Consequences sections. State that the reusable parser performs
no execution or network work, core reporting depends inward on normalized
findings, `agent_repair_facts` never imports `agent_maintainer`, and duplicate
parsers or a TypeScript-specific OSV adapter remain forbidden.

- [ ] **Step 6: Run focused summaries, context, and architecture checks**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/pytest tests/core/test_osv_structured_output.py tests/context/test_osv_exact_facts.py tests/core/test_structured_artifact_summaries.py tests/repair_facts/test_osv_scanner_facts.py -q
PATH=.venv/bin:$PATH tach check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m archguard decision-check --base-ref 651ce85
```

Expected: tests, Tach, and architecture decision checks pass.

- [ ] **Step 7: Commit shared summary behavior**

```bash
git add -- src/agent_maintainer/core/structured_security.py src/agent_maintainer/core/tach.domain.toml tests/core/test_osv_structured_output.py tests/core/test_structured_artifact_summaries.py tests/context/test_osv_exact_facts.py docs/architecture/decisions/2026-07-17-osv-parser-boundary.md
git commit -m "feat: share OSV facts with repair summaries"
```

### Task 3: Add Public Npm And Pnpm Compatibility Evidence

**Files:**

- Create: `tests/fixtures/typescript_osv_external/eslint-plugin-vitest.json`
- Create: `tests/fixtures/typescript_osv_external/node-typescript-boilerplate.json`
- Create: `tests/assess/test_typescript_osv_external_fixtures.py`
- Modify: `src/agent_maintainer/assess/setup_advisor.py`
- Modify: `tests/assess/test_setup_advisor.py`

**Interfaces:**

- Consumes: Task 1 `parse_osv_payload` and `OSV_FACT_LIMIT`.
- Produces: offline, bounded public capture fixtures with replay metadata and one improved existing `osv-scanner` setup recommendation.
- Does not modify scanner commands or provider command metadata.

- [ ] **Step 1: Capture exact public repository scans in temporary space**

Verify the installed scanner and create a task-specific temporary directory:

```bash
osv-scanner --version
mktemp -d /private/tmp/agent-maintainer-osv180.XXXXXX
```

Clone or reuse detached checkouts only inside that returned directory, then scan:

```bash
git clone --filter=blob:none https://github.com/vitest-dev/eslint-plugin-vitest.git <temp>/eslint-plugin-vitest
git -C <temp>/eslint-plugin-vitest checkout --detach 7c697f8a53d7d7551b00ef11217d58cd45a0cf7d
osv-scanner scan source -r <temp>/eslint-plugin-vitest --format json --output-file <temp>/eslint-plugin-vitest.raw.json

git clone --filter=blob:none https://github.com/jsynowiec/node-typescript-boilerplate.git <temp>/node-typescript-boilerplate
git -C <temp>/node-typescript-boilerplate checkout --detach 550dfd2a976d69254ed71eb6f5a6c5ee20060807
osv-scanner scan source -r <temp>/node-typescript-boilerplate --format json --output-file <temp>/node-typescript-boilerplate.raw.json
```

Record each scanner exit code immediately. Do not install dependencies or run
package scripts. Calculate SHA-256 for the lockfile and raw output. Preserve the
temporary raw files through review; do not commit or print full advisory
details.

- [ ] **Step 2: Write failing replay tests before committing projections**

Create `tests/assess/test_typescript_osv_external_fixtures.py` with DocSync
markers. Use this fixture metadata contract:

```python
EXPECTED_FIXTURES = {
    "eslint-plugin-vitest.json": (
        "https://github.com/vitest-dev/eslint-plugin-vitest",
        "7c697f8a53d7d7551b00ef11217d58cd45a0cf7d",
        "pnpm-lock.yaml",
        "pnpm@10.18.3",
    ),
    "node-typescript-boilerplate.json": (
        "https://github.com/jsynowiec/node-typescript-boilerplate",
        "550dfd2a976d69254ed71eb6f5a6c5ee20060807",
        "package-lock.json",
        "npm",
    ),
}
```

For each fixture, assert:

```python
assert fixture["schema_version"] == 1
assert fixture["source_repository"] == repository
assert fixture["commit"] == commit
assert fixture["lockfile_path"] == lockfile
assert fixture["package_manager"] == package_manager
assert fixture["scanner_version"]
assert fixture["capture_command"] == ["osv-scanner", "scan", "source", "-r", ".", "--format", "json"]
assert fixture["exit_code"] in (0, 1)
assert fixture["lockfile_sha256"]
assert fixture["raw_report_sha256"]
assert fixture["projection_method"] == "parser-consumed-fields-v1"

parsed = osv_scanner.parse_osv_payload(fixture["projection"])
assert parsed.valid is True
assert parsed.supported_count == fixture["supported_finding_count"]
assert len(parsed.findings) == fixture["retained_finding_count"]
assert len(parsed.findings) <= osv_scanner.OSV_FACT_LIMIT
```

Add a privacy test that serializes each fixture and rejects `/private/tmp/`,
`/Users/`, Windows drive prefixes, and `..` source paths.

- [ ] **Step 3: Produce bounded deterministic projections**

Create the two JSON fixture files with top-level metadata from Step 1 and a
`projection` object. Project only:

- `results[].source.path` normalized to the repository-relative lockfile;
- `results[].source.type`;
- package `name`, `version`, and `ecosystem`;
- vulnerability `id`, `aliases`, normalized/truncated `summary`, and only
  `affected[].ranges[].events[].fixed` events;
- group `ids`, `aliases`, and `max_severity`.

Sort results, packages, vulnerabilities, groups, IDs, aliases, and fixed events
before JSON serialization. Retain at most the first 25 normalized groups per
repository and record `projection_omitted_count`. If a scan is clean, preserve
the valid empty `results` projection and zero counts rather than fabricating a
finding.

- [ ] **Step 4: Improve setup recommendation evidence without changing profiles**

Change the existing OSV branch in `_optional_gates`:

```python
if evidence.has_package_json:
    lockfile_detail = " and a dependency lockfile" if evidence.has_lock_file else ""
    gates.append(
        GateRecommendation(
            name="osv-scanner",
            recommendation="consider",
            reason=f"Package metadata{lockfile_detail} can be scanned for known vulnerabilities.",
            config_key="enable_osv_scanner",
            profiles=("manual",),
        ),
    )
```

Add tests in `tests/assess/test_setup_advisor.py` proving package metadata plus a
lockfile gets the lockfile-aware reason, package metadata without a lockfile
keeps a truthful package-only reason, recommendation remains `consider`, and
profiles remain exactly `("manual",)`.

- [ ] **Step 5: Run replay and setup-advisor checks**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/pytest tests/assess/test_typescript_osv_external_fixtures.py tests/assess/test_setup_advisor.py tests/repair_facts/test_osv_scanner_facts.py -q
```

Expected: all tests pass offline with no scanner binary or network use.

- [ ] **Step 6: Commit public evidence and guidance**

```bash
git add -- src/agent_maintainer/assess/setup_advisor.py tests/assess/test_setup_advisor.py tests/assess/test_typescript_osv_external_fixtures.py tests/fixtures/typescript_osv_external/eslint-plugin-vitest.json tests/fixtures/typescript_osv_external/node-typescript-boilerplate.json
git commit -m "test: add public OSV compatibility evidence"
```

### Task 4: Complete Phase 180 Documentation, DocSync, And Verification

**Files:**

- Create: `docs/roadmap/phases/phase-180-typescript-osv-dependency-facts.md`
- Modify: `docs/roadmap/full-roadmap-blueprint.md`
- Modify: `docs/roadmap/typescript-react-parity-roadmap.md`
- Modify: `docs/typescript-javascript-provider.md`
- Modify: `docs/provider-status.md`
- Modify: `docs/supported-scans-and-agent-use.md`
- Modify: `docs/tool-map.md`
- Modify: `tests/docs/test_first_touch_docs.py`
- Modify: `.docsync/trace.yml`
- Create: `.docsync/attestations/attest.<timestamp>.claim.docs.typescript_provider_repair_facts.<head>.yml`

**Interfaces:**

- Consumes: completed parser, summaries, context, public evidence, and setup guidance from Tasks 1–3.
- Produces: completed Phase 180 roadmap state and DocSync evidence tying public OSV claims to tests.
- Next roadmap slice: package-manager audit facts; no implementation in this plan.

- [ ] **Step 1: Add failing public-document assertions and DocSync anchors**

Extend `tests/docs/test_first_touch_docs.py` to require these exact public
phrases across provider and status docs:

```python
"Phase 180 OSV dependency facts are complete."
"uses the existing ecosystem-neutral `osv-scanner` gate"
"one fact per OSV alias group"
"package-manager audit facts are the next parity slice"
"TypeScript/JavaScript remains experimental"
```

Add DocSync explicit regions around the new OSV fact, summary, and external
fixture tests. Extend `claim.docs.typescript_provider_repair_facts` to mention
bounded OSV v2 outputs and include:

```yaml
- evidence.typescript.osv_fact_tests
- evidence.typescript.osv_summary_tests
- evidence.typescript.osv_external_fixtures
```

Define each evidence object with its exact test path and `mode: explicit_region`.

- [ ] **Step 2: Run docs tests and verify they fail before prose updates**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/pytest tests/docs/test_first_touch_docs.py tests/docsync/test_public_doc_trace.py -q
```

Expected: failures identify missing Phase 180 prose or evidence anchors.

- [ ] **Step 3: Write the focused phase and update roadmap sequence**

Create `docs/roadmap/phases/phase-180-typescript-osv-dependency-facts.md` with
Status, Objective, Scope, Safety Boundary, Evidence, Acceptance Criteria,
Verification, and Completion Notes. State the exact limits, existing global
configuration boundary, two pinned repositories, and package-manager audits as
the next slice.

Add Phase 180 to `docs/roadmap/full-roadmap-blueprint.md`. Update item 3 in
`docs/roadmap/typescript-react-parity-roadmap.md` to mark OSV facts complete and
package-manager audit facts next. Add a `Phase 180 OSV Boundary` section that
records alias grouping, path safety, bounds, and public capture strategy.

- [ ] **Step 4: Update provider and scan documentation**

Update `docs/typescript-javascript-provider.md` and `docs/provider-status.md` to
say:

- OSV facts come from the existing ecosystem-neutral `osv-scanner` gate, not a
  TypeScript command;
- OSV remains explicitly enabled and manual by default;
- valid relative lockfile provenance is retained, unsafe machine paths are
  redacted;
- facts group aliases and include fixes where OSV range events provide them;
- 500 parser, 50 summary, and five context limits apply;
- npm and pnpm public projections are evidence, not provider promotion;
- package-manager audit, mutation, coverage gates, and blocking reviewability
  remain unsupported.

Update `docs/supported-scans-and-agent-use.md` and `docs/tool-map.md` only to
describe the new exact repair facts and safe source behavior. Do not change the
documented command, defaults, profiles, or installation policy.

- [ ] **Step 5: Refresh DocSync attestations and verify docs**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m docsync review --base HEAD
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m docsync attest claim.docs.typescript_provider_repair_facts --evidence evidence.typescript.osv_fact_tests --evidence evidence.typescript.osv_summary_tests --evidence evidence.typescript.osv_external_fixtures --reason "Reviewed Phase 180 grouped OSV v2 facts, safe lockfile provenance, bounded summaries, and pinned npm/pnpm compatibility evidence; the provider repair-fact documentation is accurate."
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m docsync check
npx --no-install markdownlint-cli2 docs/roadmap/phases/phase-180-typescript-osv-dependency-facts.md docs/roadmap/full-roadmap-blueprint.md docs/roadmap/typescript-react-parity-roadmap.md docs/typescript-javascript-provider.md docs/provider-status.md docs/supported-scans-and-agent-use.md docs/tool-map.md docs/superpowers/specs/2026-07-17-typescript-osv-dependency-facts-design.md docs/superpowers/plans/2026-07-17-typescript-osv-dependency-facts.md docs/architecture/decisions/2026-07-17-osv-parser-boundary.md
```

Expected: DocSync and Markdownlint pass.

- [ ] **Step 6: Run the complete focused Phase 180 suite**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/pytest \
  tests/repair_facts/test_osv_scanner_facts.py \
  tests/repair_facts/test_security_repair_facts.py \
  tests/core/test_osv_structured_output.py \
  tests/core/test_structured_artifact_summaries.py \
  tests/context/test_osv_exact_facts.py \
  tests/assess/test_typescript_osv_external_fixtures.py \
  tests/assess/test_setup_advisor.py \
  tests/docs/test_first_touch_docs.py \
  tests/docsync/test_public_doc_trace.py -q
PATH=.venv/bin:$PATH tach check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m archguard decision-check --base-ref 651ce85
```

Expected: all focused tests and architecture checks pass.

- [ ] **Step 7: Run required manual/security and broad verification**

Because Phase 180 changes a manual security gate, run:

```bash
PATH=.venv/bin:$PATH AGENT_MAINTAINER_ALLOW_FOREGROUND_WAIT=1 python -m agent_maintainer verify --profile manual
PATH=.venv/bin:$PATH AGENT_MAINTAINER_ALLOW_FOREGROUND_WAIT=1 python -m agent_maintainer verify --profile security
PATH=.venv/bin:$PATH AGENT_MAINTAINER_ALLOW_FOREGROUND_WAIT=1 just v
```

The manual and security profiles may perform network-backed scanners configured
by this repository. Record their compact run IDs and results. The full profile
must pass; existing non-blocking cohesion warnings may remain, but no new
warning or failure may be suppressed.

- [ ] **Step 8: Perform final diff, privacy, and secret review**

Run:

```bash
git status --short --branch
git diff --check
git diff --stat origin/main...HEAD
git diff origin/main...HEAD
rg -n "/Users/|/private/tmp|[A-Za-z]:\\\\|BEGIN (RSA|OPENSSH|EC) PRIVATE KEY|AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9_]{20,}" tests/fixtures/typescript_osv_external tests/fixtures/osv-scanner docs/roadmap/phases/phase-180-typescript-osv-dependency-facts.md
```

Expected: only synthetic rejection inputs contain machine-path markers; no
fixture metadata, rendered fact, secret, credential, or private record is
present.

- [ ] **Step 9: Commit Phase 180 completion**

Stage only the intentional remaining paths, including the generated DocSync
attestation, then commit:

```bash
git commit -m "docs: complete TypeScript OSV facts phase"
```

- [ ] **Step 10: Request one comprehensive review and publish**

Use `superpowers:requesting-code-review` for one batched correctness, security,
privacy, architecture, and missing-verification review. Fix findings, rerun the
smallest affected checks, then rerun one fresh full verification of final HEAD.

Use `superpowers:finishing-a-development-branch`. The recommended publication
choice is push and create a draft PR targeting `main`; preserve the linked
worktree for CI and review follow-up.
