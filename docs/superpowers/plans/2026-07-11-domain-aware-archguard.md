# Domain-aware Archguard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Archguard map, impact, and boundary explanations reflect nested `tach.domain.toml` ownership and explicit dependencies without weakening legacy layered-root behavior.

**Architecture:** Extend the shared domain loader with a typed, fail-closed result, then merge root and domain rules into `ArchitectureMap`. Explicit `depends_on` wins when present; ordered layers remain the fallback only for rules without explicit dependencies.

**Tech Stack:** Python 3.11+, `tomllib`, dataclasses, pytest, Tach domain TOML, Markdown ADRs.

## Global Constraints

- Tach remains the enforcement engine; Archguard remains read-only explanation.
- Any root or domain policy load error makes dependency conclusions `unknown`.
- Never fall back to a broad root/layer rule and report `allowed` when domain policy is incomplete.
- Preserve existing output semantics for valid root-layer repositories.
- Keep affected-test output deterministic and bounded.
- Any `tach.domain.toml` dependency change requires an ADR in the same commit.

---

### Task 1: Return domain payloads and parse failures from one loader

**Files:**

- Modify: `tests/archguard/test_impact.py`
- Modify: `src/archguard/tach_config_domains.py`
- Modify: `src/archguard/impact.py`
- Modify: `src/archguard/tach.domain.toml`
- Create: `docs/architecture/decisions/2026-07-11-domain-aware-archguard-impact.md`

**Interfaces:**

- Consumes: source roots and discovered `tach.domain.toml` files.
- Produces: `load_domain_payloads(...) -> DomainLoadResult`; existing `domain_payloads` remains a compatibility wrapper.

- [ ] **Step 1: Add a failing malformed-domain fixture test**

Add to `tests/archguard/test_impact.py`:

```python
def test_malformed_domain_policy_fails_boundary_explanation_closed(tmp_path: Path) -> None:
    """Incomplete nested policy never falls back to a broad allowed result."""

    write_tach_fixture(tmp_path)
    domain = tmp_path / "src" / "sample" / "broken" / "tach.domain.toml"
    domain.parent.mkdir(parents=True)
    domain.write_text("[[modules]\npath =", encoding="utf-8")

    architecture = load_architecture(tmp_path)
    output = render_boundary(
        tmp_path,
        architecture,
        Path("src/sample/cli.py"),
        Path("src/sample/models.py"),
    )

    assert architecture.load_errors == (
        "src/sample/broken/tach.domain.toml: invalid_toml",
    )
    assert "Policy load errors:" in render_map(architecture)
    assert "Dependency direction: unknown: architecture policy is incomplete" in output
    assert "allowed:" not in output


def test_malformed_root_policy_returns_bounded_error_map(tmp_path: Path) -> None:
    """Root parse failures are reported without a traceback or false policy."""

    (tmp_path / "tach.toml").write_text("[[modules]\npath =", encoding="utf-8")

    architecture = load_architecture(tmp_path)

    assert architecture.load_errors == ("tach.toml: invalid_toml",)
    assert "- tach.toml: invalid_toml" in render_map(architecture)
    assert dependency_direction(architecture, None) == (
        "unknown: architecture policy is incomplete"
    )
```

- [ ] **Step 2: Run the test to verify RED**

Run: `PYTHONPATH=src .venv/bin/pytest tests/archguard/test_impact.py -k 'malformed_domain or malformed_root' -q`

Expected: FAIL because `ArchitectureMap` has no `load_errors` and malformed
domains are silently discarded.

- [ ] **Step 3: Add typed domain load results**

In `tach_config_domains.py`, import `dataclass` and add:

```python
@dataclass(frozen=True)
class DomainLoadResult:
    """Parsed domain payloads plus bounded fail-closed errors."""

    payloads: DomainPayloads
    errors: tuple[str, ...]
```

Implement `load_domain_payloads(repo_root, source_roots)` by discovering every
domain config under valid source roots. Parse each file with UTF-8 and
`tomllib.loads`. Append `<repo-relative-path>: invalid_toml` for
`TOMLDecodeError`, `<path>: invalid_utf8` for `UnicodeError`, and
`<path>: read_error` for `OSError`. Never include exception text or file
content. Return sorted payloads and errors.

Keep existing callers stable:

```python
def domain_payloads(repo_root: Path, source_roots: object) -> DomainPayloads:
    """Return successfully parsed Tach domain payloads."""

    return load_domain_payloads(repo_root, source_roots).payloads
```

- [ ] **Step 4: Carry load errors into the architecture map**

Add a defaulted field so existing constructors remain valid:

```python
@dataclass(frozen=True)
class ArchitectureMap:
    source_roots: tuple[str, ...]
    layers: tuple[str, ...]
    modules: tuple[ModuleRule, ...]
    load_errors: tuple[str, ...] = ()
```

In `load_architecture`, catch root `OSError`, `UnicodeError`, and
`TOMLDecodeError` and return an empty map with the matching bounded
`tach.toml: <error_code>` error. For a valid root, call
`load_domain_payloads` and store its errors. At the start of both
`dependency_direction` and `boundary_status`, return
`unknown: architecture policy is incomplete` when `load_errors` is non-empty.
Render each load error under a `Policy load errors:` map section.

- [ ] **Step 5: Declare and explain the new internal dependency**

Change the Archguard module contract now, in the same commit that imports the
domain loader:

```toml
[[modules]]
path = "impact"
depends_on = ["structured_values", "tach_config_domains"]
```

Create `docs/architecture/decisions/2026-07-11-domain-aware-archguard-impact.md`
with sections `Status`, `Context`, `Decision`, `Dependency direction`,
`Alternatives`, and `Remaining constraints`. Record the full approved design:
the shared domain loader flows inward to read-only impact analysis, explicit
dependencies take precedence over legacy layers, malformed policy fails closed,
Tach remains authoritative, and no product package imports Archguard internals.

- [ ] **Step 6: Verify GREEN and compatibility wrapper behavior**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest tests/archguard/test_impact.py::test_malformed_domain_policy_fails_boundary_explanation_closed tests/archguard/test_tach_config.py -q
PYTHONPATH=src .venv/bin/python -m archguard tach-config --strict-root-module
.venv/bin/tach check --exact
```

Expected: PASS; strict Tach config tests continue consuming successful domain
payloads through the wrapper and the new dependency is exact.

- [ ] **Step 7: Commit the fail-closed loader slice**

```bash
git add -- \
  tests/archguard/test_impact.py \
  src/archguard/tach_config_domains.py \
  src/archguard/impact.py \
  src/archguard/tach.domain.toml \
  docs/architecture/decisions/2026-07-11-domain-aware-archguard-impact.md
git commit -m "fix: fail closed on incomplete tach domains"
```

### Task 2: Merge nested ownership and explicit dependency rules

**Files:**

- Modify: `tests/archguard/test_impact.py`
- Modify: `src/archguard/impact.py`

**Interfaces:**

- Consumes: `DomainLoadResult.payloads` from Task 1.
- Produces: full-name `ModuleRule` records with optional explicit dependencies and domain roots.

- [ ] **Step 1: Add a domain fixture and failing ownership/boundary tests**

Add this fixture helper:

```python
def write_domain_fixture(repo_root: Path) -> None:
    """Write nested verify/wait ownership with local and absolute dependencies."""

    verify = repo_root / "src" / "sample" / "verify"
    wait = repo_root / "src" / "sample" / "wait"
    tests = repo_root / "tests"
    verify.mkdir(parents=True)
    wait.mkdir(parents=True)
    tests.mkdir()
    (verify / "worker.py").write_text("VALUE = 1\n", encoding="utf-8")
    (verify / "orchestrator.py").write_text("VALUE = 1\n", encoding="utf-8")
    (wait / "broker.py").write_text("VALUE = 1\n", encoding="utf-8")
    (tests / "verify").mkdir()
    (tests / "verify" / "test_worker.py").write_text(
        "def test_worker(): pass\n", encoding="utf-8"
    )
    (repo_root / "tach.toml").write_text(
        'source_roots = ["src"]\nroot_module = "forbid"\n\n'
        '[[modules]]\npath = "sample"\n',
        encoding="utf-8",
    )
    (verify / "tach.domain.toml").write_text(
        '[root]\ndepends_on = []\n\n'
        '[[modules]]\npath = "worker"\ndepends_on = ["//sample.wait.broker"]\n\n'
        '[[modules]]\npath = "orchestrator"\ndepends_on = ["worker"]\n',
        encoding="utf-8",
    )
    (wait / "tach.domain.toml").write_text(
        '[root]\ndepends_on = []\n\n'
        '[[modules]]\npath = "broker"\ndepends_on = []\n',
        encoding="utf-8",
    )
```

Add tests:

```python
def test_nested_domains_override_broad_root_ownership(tmp_path: Path) -> None:
    write_domain_fixture(tmp_path)
    architecture = load_architecture(tmp_path)

    impact = render_impact(
        tmp_path,
        architecture,
        Path("src/sample/verify/worker.py"),
    )
    allowed = render_boundary(
        tmp_path,
        architecture,
        Path("src/sample/verify/worker.py"),
        Path("src/sample/wait/broker.py"),
    )
    forbidden = render_boundary(
        tmp_path,
        architecture,
        Path("src/sample/wait/broker.py"),
        Path("src/sample/verify/worker.py"),
    )

    assert "Module ownership: sample.verify.worker" in impact
    assert "sample.verify.worker" in render_map(architecture)
    assert "depends on: sample.wait.broker" in render_map(architecture)
    assert "allowed: sample.verify.worker declares sample.wait.broker" in allowed
    assert "violation: sample.wait.broker does not declare sample.verify.worker" in forbidden


def test_domain_dependencies_normalize_local_and_absolute_paths(tmp_path: Path) -> None:
    write_domain_fixture(tmp_path)
    architecture = load_architecture(tmp_path)
    rules = {rule.name: rule for rule in architecture.modules}

    assert rules["sample.verify.worker"].depends_on == ("sample.wait.broker",)
    assert rules["sample.verify.orchestrator"].depends_on == (
        "sample.verify.worker",
    )
    assert rules["sample.wait.broker"].depends_on == ()
```

- [ ] **Step 2: Run the tests to verify RED**

Run: `PYTHONPATH=src .venv/bin/pytest tests/archguard/test_impact.py -k 'nested_domains or normalize_local' -q`

Expected: FAIL because only the broad `sample` root module is loaded.

- [ ] **Step 3: Extend the rule model without breaking layered callers**

Change `ModuleRule` to:

```python
@dataclass(frozen=True)
class ModuleRule:
    """Configured Tach module ownership and dependency rule."""

    name: str
    layer: str = NO_OWNER
    depends_on: tuple[str, ...] | None = None
    domain_root: str = ""
```

Update `module_rules(modules, *, domain_root="")` so root paths remain full and
domain-local paths are expanded with `domain_module_path`. Distinguish a missing
`depends_on` key (`None`) from an explicit empty list (`()`). Normalize
`//package.module` by removing `//`; normalize a domain-local dependency with
`domain_module_path(domain_root, value)`. Ignore malformed dependency values but
retain an explicit empty tuple so the result fails closed to violation.

Create one rule for each domain `[root]` table and merge it with every domain
module rule plus the existing root rules. Sort by full module name. The existing
longest-name `owner_for_module` then chooses the nested rule.

Keep legacy map lines unchanged when `depends_on is None`. For explicit rules,
append the suffix `depends on: <comma-separated modules>` or
`depends on: <none>` so the
read-only map exposes the policy source used by boundary explanations.

- [ ] **Step 4: Prefer explicit dependencies and preserve layer fallback**

After load-error, unowned, and same-module checks, implement:

```python
if source.depends_on is not None:
    if any(
        target.name == dependency or target.name.startswith(f"{dependency}.")
        for dependency in source.depends_on
    ):
        return f"allowed: {source.name} declares {target.name}"
    return f"violation: {source.name} does not declare {target.name}"
```

Only use the existing ordered-layer comparison when `source.depends_on is
None`. In `dependency_direction`, render `may not depend on other configured
modules` for an empty tuple and a comma-separated explicit allowlist otherwise;
leave the old layer string byte-for-byte unchanged for legacy rules.

- [ ] **Step 5: Verify domain and legacy GREEN**

Run: `PYTHONPATH=src .venv/bin/pytest tests/archguard/test_impact.py -q`

Expected: all new domain tests and all existing layered-root tests PASS.

- [ ] **Step 6: Commit the domain semantics slice**

```bash
git add -- tests/archguard/test_impact.py src/archguard/impact.py
git commit -m "feat: explain tach domain dependencies"
```

### Task 3: Improve test hints, document semantics, and dogfood the commands

**Files:**

- Modify: `tests/archguard/test_impact.py`
- Modify: `src/archguard/impact.py`
- Modify: `docs/tool-map.md`

**Interfaces:**

- Consumes: `ModuleRule.domain_root` and explicit dependencies from Task 2.
- Produces: bounded domain-aware test candidates and truthful public Archguard documentation.

- [ ] **Step 1: Add a failing bounded test-candidate assertion**

Extend the nested-domain impact test:

```python
assert "Affected tests: tests/verify/test_worker.py" in impact
```

Before rendering `impact`, add 13 more matching files so the fixture has 14
domain candidates, then assert bounded output:

```python
for index in range(13):
    (tmp_path / "tests" / "verify" / f"test_worker_{index}.py").write_text(
        "def test_worker(): pass\n",
        encoding="utf-8",
    )

assert impact.count("tests/verify/") == 12
assert "(+2 more)" in impact
```

- [ ] **Step 2: Run the test to verify RED**

Run: `PYTHONPATH=src .venv/bin/pytest tests/archguard/test_impact.py::test_nested_domains_override_broad_root_ownership -q`

Expected: FAIL because the broad current heuristic does not use `verify` as a
test-directory hint and does not bound output.

- [ ] **Step 3: Implement deterministic bounded hints**

Add `MAX_AFFECTED_TESTS = 12`. Match a test when its stem contains the owner
leaf or its relative directory parts contain the final `domain_root` segment.
Sort all candidates, render the first 12, and append `(+N more)` when omitted.
Keep `none found` behavior unchanged.

- [ ] **Step 4: Update public Archguard documentation**

Update `docs/tool-map.md` to state that map/impact/explain-boundary merge nested
domain ownership, prefer explicit dependencies, preserve legacy layers, bound
test hints, and report incomplete policy as unknown.

- [ ] **Step 5: Verify focused policy and dogfood output**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest tests/archguard -q
PYTHONPATH=src .venv/bin/python -m archguard tach-config --strict-root-module
.venv/bin/tach check --exact
PYTHONPATH=src .venv/bin/python -m archguard map
PYTHONPATH=src .venv/bin/python -m archguard impact src/agent_maintainer/verify/background_wait.py
PYTHONPATH=src .venv/bin/python -m archguard explain-boundary \
  src/agent_maintainer/verify/background_wait.py \
  src/agent_maintainer/wait/broker.py
```

Expected: tests/Tach PASS; map and impact name nested owners; the boundary is
allowed only because `verify.background_wait` explicitly declares
`wait.broker` after the wait-lifecycle chunk.

- [ ] **Step 6: Commit and run the broad gate**

```bash
git add -- \
  tests/archguard/test_impact.py \
  src/archguard/impact.py \
  docs/tool-map.md
git commit -m "feat: make archguard domain aware"
just v
```

Expected: terminal full-profile PASS after reviewing the original run manifest.
