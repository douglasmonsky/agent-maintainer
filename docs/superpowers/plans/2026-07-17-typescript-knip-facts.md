# TypeScript Knip Facts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an explicit, opt-in TypeScript Knip check that turns supported Knip JSON issue categories into bounded exact repair facts and compact summaries without changing TypeScript's experimental status.

**Architecture:** The existing experimental TypeScript provider owns root and workspace command registration. A dedicated repair-facts parser owns Knip's grouped JSON shape, category normalization, deterministic ordering, and the 500-fact retention bound. The exact-facts registry and compact TypeScript summarizer share a narrow check-family normalizer so root and `:<workspace>` check names behave consistently. Recorded public-repository fixtures validate the parser contract without introducing live-network tests.

**Tech Stack:** Python 3.11+, dataclasses, JSON, pytest, Ruff, Pyright, Tach, DocSync, GitHub-hosted public TypeScript fixtures.

## Global Constraints

- Preserve opt-in behavior: `enable_typescript` and an explicit command remain required.
- Add no Knip dependency, version enforcement, thresholds, autofix, or default command inference.
- Honor the configured command's process exit status through the existing check runner.
- Enable the Knip check in `full` and `ci`, never `precommit`, by default.
- Support only unused files, exports, types, dependencies, binaries, unlisted dependencies, and unresolved imports.
- Keep cycles, duplicates, catalogs, enum members, namespace/class members, and other categories out of scope.
- Sort normalized findings before retaining at most 500 facts.
- Emit at most 50 Knip lines in the compact report; the context pack's existing 5-fact bound remains unchanged.
- Preserve Knip line and column values exactly as reported.
- Treat malformed, non-object, or unsupported JSON as zero exact facts and an unavailable structured summary, never as a parser exception.
- Keep TypeScript experimental in every public document.
- Use synthetic fixtures as the authoritative category contract and pinned TanStack Query and Astro captures as compatibility evidence.

---

## Task 1: Register explicit root and workspace Knip checks

**Files:**

- Modify: `src/agent_maintainer/config/schema.py`
- Modify: `src/agent_maintainer/config/schema_fields.py`
- Modify: `src/agent_maintainer/config/registry.py`
- Modify: `src/agent_maintainer/config/workspaces.py`
- Modify: `src/agent_maintainer/ecosystems/typescript/provider.py`
- Test: `tests/config/test_typescript_config.py`
- Test: `tests/config/test_workspace_config.py`
- Test: `tests/catalogs/test_typescript_catalog.py`
- Test: `tests/catalogs/test_global_catalog_characterization.py`
- Test: `tests/catalogs/test_provider_registry.py`

### Step 1: Write failing configuration tests

- [ ] Extend `test_pyproject_loads_typescript_provider_config` with:

```python
"typescript_knip_command": ["pnpm", "exec", "knip", "--reporter", "json"],
"typescript_knip_profiles": ["full", "ci"],
```

- [ ] Assert the loaded values are tuples:

```python
assert loaded.typescript_knip_command == (
    "pnpm",
    "exec",
    "knip",
    "--reporter",
    "json",
)
assert loaded.typescript_knip_profiles == ("full", "ci")
```

- [ ] Extend the environment test with `AGENT_MAINTAINER_TYPESCRIPT_KNIP_COMMAND` and `AGENT_MAINTAINER_TYPESCRIPT_KNIP_PROFILES` and assert the same coercion contract.
- [ ] Add a default assertion that `MaintainerConfig().typescript_knip_profiles == ("full", "ci")`.
- [ ] Run the focused configuration test and verify it fails because the fields do not exist:

```bash
PATH=.venv/bin:$PATH pytest tests/config/test_typescript_config.py -q
```

Expected: FAIL with an unknown configuration field or missing attribute involving `typescript_knip_command`.

### Step 2: Add schema and coercion fields

- [ ] In `src/agent_maintainer/config/schema.py`, define and expose:

```python
DEFAULT_TYPESCRIPT_KNIP_PROFILES = ("full", "ci")

typescript_knip_command: tuple[str, ...] = ()
typescript_knip_profiles: tuple[str, ...] = DEFAULT_TYPESCRIPT_KNIP_PROFILES
```

- [ ] Add both tuple fields to `TUPLE_FIELDS` in `src/agent_maintainer/config/schema_fields.py`.
- [ ] Add both top-level keys to the configuration registry alongside the existing TypeScript command/profile keys so environment and pyproject loading use the normal coercion path.
- [ ] Run:

```bash
PATH=.venv/bin:$PATH pytest tests/config/test_typescript_config.py -q
```

Expected: PASS.

### Step 3: Write failing workspace configuration tests

- [ ] Add `typescript_knip_command` to the `api` workspace table and expected `WorkspaceConfig` value in `tests/config/test_workspace_config.py`:

```python
typescript_knip_command = ["pnpm", "--filter", "api", "exec", "knip", "--reporter", "json"]
```

- [ ] Extend the coercion test with the same field and tuple assertion.
- [ ] Run:

```bash
PATH=.venv/bin:$PATH pytest tests/config/test_workspace_config.py -q
```

Expected: FAIL because `WorkspaceConfig` rejects the unknown field.

### Step 4: Add the workspace command field

- [ ] In `src/agent_maintainer/config/workspaces.py`, add:

```python
typescript_knip_command: tuple[str, ...] = ()
```

- [ ] Add `typescript_knip_command` to the workspace key registry used by nested-table coercion.
- [ ] Run the workspace configuration test again.

Expected: PASS.

### Step 5: Write failing provider catalog tests

- [ ] Extend the root enabled-provider test with a Knip command and assert:

```python
assert by_name["typescript-knip"].command == [
    "pnpm",
    "exec",
    "knip",
    "--reporter",
    "json",
]
assert by_name["typescript-knip"].profiles == ("full", "ci")
```

- [ ] Extend the workspace test and assert `typescript-knip:api` owns the workspace-specific command.
- [ ] Assert no Knip check is created when the root/workspace command is empty.
- [ ] Assert `typescript-knip` is included in `full` and `ci` but excluded from `precommit` through the existing catalog characterization surface.
- [ ] Run:

```bash
PATH=.venv/bin:$PATH pytest tests/catalogs/test_typescript_catalog.py tests/catalogs/test_global_catalog_characterization.py tests/catalogs/test_provider_registry.py -q
```

Expected: FAIL because the provider does not register `typescript-knip`.

### Step 6: Register the provider checks

- [ ] In `src/agent_maintainer/ecosystems/typescript/provider.py`, add the root check via the same `_configured_check` helper used for lint/typecheck/test:

```python
_configured_check(
    name="typescript-knip",
    command=config.typescript_knip_command,
    profiles=config.typescript_knip_profiles,
)
```

- [ ] Add the workspace check with the established suffix contract:

```python
_configured_check(
    name=f"typescript-knip:{workspace.name}",
    command=workspace.typescript_knip_command,
    profiles=config.typescript_knip_profiles,
)
```

- [ ] Preserve existing command validation and skip-empty behavior; do not special-case exit codes or executables.
- [ ] Run all Task 1 tests:

```bash
PATH=.venv/bin:$PATH pytest tests/config/test_typescript_config.py tests/config/test_workspace_config.py tests/catalogs/test_typescript_catalog.py tests/catalogs/test_global_catalog_characterization.py tests/catalogs/test_provider_registry.py -q
```

Expected: PASS.

### Step 7: Commit the provider slice

- [ ] Review `git diff --check` and the focused diff.
- [ ] Stage only Task 1 files.
- [ ] Commit:

```bash
git commit -m "feat: add explicit TypeScript Knip checks"
```

---

## Task 2: Parse bounded Knip facts and compact summaries

**Files:**

- Create: `src/agent_repair_facts/parsers/typescript_knip.py`
- Modify: `src/agent_repair_facts/parsers/typescript.py`
- Modify: `src/agent_repair_facts/registry.py`
- Modify: `src/agent_repair_facts/tach.domain.toml`
- Modify: `src/agent_maintainer/core/structured_typescript.py`
- Modify: `src/agent_maintainer/core/tach.domain.toml`
- Create: `tests/fixtures/typescript_knip/supported-issues.json`
- Create: `tests/fixtures/typescript_knip/malformed.json`
- Create: `tests/repair_facts/test_typescript_knip_facts.py`
- Modify: `tests/context/test_typescript_exact_facts.py`
- Modify: `tests/core/test_typescript_structured_output.py`

### Step 1: Add authoritative synthetic Knip fixtures

- [ ] Create `supported-issues.json` using Knip's current top-level `issues` array of file groups. Include one supported item from each family:

```json
{
  "files": ["src/unused.ts"],
  "issues": [
    {
      "file": "src/api.ts",
      "exports": [{"name": "unusedExport", "line": 8, "col": 3}],
      "types": [{"name": "UnusedType", "line": 12, "col": 1}],
      "dependencies": [{"name": "left-pad", "line": 2, "col": 5}],
      "devDependencies": [{"name": "vitest"}],
      "optionalPeerDependencies": [{"name": "react-dom"}],
      "unlisted": [{"name": "missing-package", "line": 3, "col": 7}],
      "binaries": [{"name": "tsx"}],
      "unresolved": [{"name": "./missing", "line": 21, "col": 9}],
      "cycles": [{"name": "src/a.ts -> src/b.ts"}],
      "duplicates": [{"name": "duplicate"}],
      "enumMembers": [{"name": "UnusedMember"}]
    }
  ]
}
```

- [ ] Include `nsExports` and `nsTypes` cases so namespace export/type aliases normalize into the export/type families.
- [ ] Create `malformed.json` containing syntactically invalid JSON.

### Step 2: Write failing parser tests

- [ ] In `tests/repair_facts/test_typescript_knip_facts.py`, specify the public parser contract:

```python
facts = typescript_knip.knip_facts(fixture, "typescript-knip")

assert [fact["symbol"] for fact in facts] == [
    "knip-unused-dependency",
    "knip-unused-dependency",
    "knip-unused-dependency",
    "knip-unused-export",
    "knip-unused-export",
    "knip-unused-file",
    "knip-unused-type",
    "knip-unused-type",
    "knip-unlisted-dependency",
    "knip-unresolved",
    "knip-unused-binary",
]
```

- [ ] Assert deterministic ordering by `(path, category, name, line-or--1, column-or--1)` rather than fixture insertion order.
- [ ] Assert every payload has the original check name, normalized path, preserved line/column, stable symbol, concise message, and severity `error`.
- [ ] Assert ignored categories emit no facts.
- [ ] Assert absolute and parent-traversal paths are rejected while valid neighboring paths remain available.
- [ ] Assert malformed JSON, non-object JSON, missing `issues`, non-array `issues`, malformed file groups, and malformed issue entries return `[]`.
- [ ] Generate 501 supported findings in memory and assert the sorted result is truncated to exactly 500.
- [ ] Run:

```bash
PATH=.venv/bin:$PATH pytest tests/repair_facts/test_typescript_knip_facts.py -q
```

Expected: FAIL because the parser module does not exist.

### Step 3: Implement the dedicated Knip parser

- [ ] In `typescript_knip.py`, define:

```python
KNIP_FACT_LIMIT = 500

@dataclass(frozen=True)
class KnipFinding:
    path: str
    category: str
    name: str
    line: int | None
    column: int | None
```

- [ ] Define one explicit category map:

```python
KNIP_CATEGORIES = {
    "files": ("unused-file", "knip-unused-file"),
    "exports": ("unused-export", "knip-unused-export"),
    "nsExports": ("unused-export", "knip-unused-export"),
    "types": ("unused-type", "knip-unused-type"),
    "nsTypes": ("unused-type", "knip-unused-type"),
    "dependencies": ("unused-dependency", "knip-unused-dependency"),
    "devDependencies": ("unused-dependency", "knip-unused-dependency"),
    "optionalPeerDependencies": ("unused-dependency", "knip-unused-dependency"),
    "unlisted": ("unlisted-dependency", "knip-unlisted-dependency"),
    "binaries": ("unused-binary", "knip-unused-binary"),
    "unresolved": ("unresolved", "knip-unresolved"),
}
```

- [ ] Implement `parse_knip_json(raw_output: str) -> list[KnipFinding]` with the shared JSON boundary helpers. Read `col` first and accept `column` as a compatibility fallback. For file findings, use the item's `name` when present and otherwise the group path.
- [ ] Implement a private sort key that maps missing positions to `-1`, sort before applying `[:KNIP_FACT_LIMIT]`, and never depend on object insertion order.
- [ ] Implement `knip_facts(path: FactSource, check: str) -> list[dict[str, object]]` using `fact_payload`:

```python
fact_payload(
    {
        "check": check,
        "path": finding.path,
        "line": finding.line,
        "column": finding.column,
        "symbol": symbol,
        "message": f"{label}: {finding.name}",
        "severity": "error",
    }
)
```

- [ ] Run the parser tests and Ruff on the new module:

```bash
PATH=.venv/bin:$PATH pytest tests/repair_facts/test_typescript_knip_facts.py -q
PATH=.venv/bin:$PATH ruff check src/agent_repair_facts/parsers/typescript_knip.py tests/repair_facts/test_typescript_knip_facts.py
```

Expected: PASS.

### Step 4: Write failing registry and workspace-name tests

- [ ] In `src/agent_repair_facts/parsers/typescript.py`, specify a narrow normalization helper through tests:

```python
assert typescript.check_family("typescript-knip:api") == "typescript-knip"
assert typescript.check_family("typescript-lint:web") == "typescript-lint"
assert typescript.check_family("pytest:api") == "pytest:api"
```

- [ ] Extend exact-facts tests so `typescript-lint:api`, `typescript-typecheck:api`, `typescript-test:api`, and `typescript-knip:api` dispatch to their existing/dedicated parsers while payloads preserve the original suffixed check name.
- [ ] Run:

```bash
PATH=.venv/bin:$PATH pytest tests/context/test_typescript_exact_facts.py tests/repair_facts/test_typescript_knip_facts.py -q
```

Expected: FAIL because suffixed TypeScript checks do not dispatch.

### Step 5: Normalize only known TypeScript check families

- [ ] In `src/agent_repair_facts/parsers/typescript.py`, add:

```python
TYPESCRIPT_CHECK_FAMILIES = frozenset(
    ("typescript-lint", "typescript-typecheck", "typescript-test", "typescript-knip")
)

def check_family(check: str) -> str:
    family = check.partition(":")[0]
    return family if family in TYPESCRIPT_CHECK_FAMILIES else check
```

- [ ] Add `("typescript-knip", typescript_knip.knip_facts)` to the exact parser registry.
- [ ] Normalize with `typescript.check_family(check)` only for parser lookup; pass the untouched `check` string to the selected parser.
- [ ] Add only the parser-layer dependency needed by Tach; do not broaden the domain allowlist.
- [ ] Run the registry/context tests.

Expected: PASS.

### Step 6: Write failing compact-summary tests

- [ ] Extend `tests/core/test_typescript_structured_output.py` to cover:
  - root and workspace Knip check names;
  - deterministic supported-category lines;
  - ignored categories;
  - malformed JSON fallback;
  - a 51-finding payload truncated to 50 lines;
  - existing workspace lint/typecheck/test summaries now recognized.
- [ ] Assert the summary contains at most 50 total lines and reserves the final line for an omission marker when more than 50 findings are retained.
- [ ] Run:

```bash
PATH=.venv/bin:$PATH pytest tests/core/test_typescript_structured_output.py -q
```

Expected: FAIL because `summarize_typescript_check` does not recognize Knip or suffixed names.

### Step 7: Implement compact Knip summaries

- [ ] In `structured_typescript.py`, normalize the check with `typescript.check_family(check_name)`.
- [ ] Reuse `parse_knip_json` and its normalized findings rather than reparsing Knip independently.
- [ ] For Knip, return `None` for invalid/unavailable payloads; otherwise return at most 50 total lines, using the final line as an omission marker when necessary. Keep the summary under the existing reporting contract and preserve original locations.
- [ ] Add the precise core-to-parser Tach dependency and an architecture decision note in Task 3 if the domain policy requires one.
- [ ] Run:

```bash
PATH=.venv/bin:$PATH pytest tests/core/test_typescript_structured_output.py tests/context/test_typescript_exact_facts.py tests/repair_facts/test_typescript_knip_facts.py -q
PATH=.venv/bin:$PATH tach check
```

Expected: PASS.

### Step 8: Commit the facts slice

- [ ] Run `git diff --check`, inspect the Task 2 diff, and stage only Task 2 files.
- [ ] Commit:

```bash
git commit -m "feat: parse TypeScript Knip facts"
```

---

## Task 3: Record public compatibility evidence and close Phase 179 docs

**Files:**

- Create: `tests/fixtures/typescript_knip_external/tanstack-query.json`
- Create: `tests/fixtures/typescript_knip_external/astro.json`
- Create: `tests/assess/test_typescript_knip_external_fixtures.py`
- Modify: `.docsync/trace.yml`
- Modify: `tests/docsync/test_public_doc_trace.py`
- Modify: `docs/typescript-javascript-provider.md`
- Modify: `docs/provider-status.md`
- Modify: `docs/setup-advisor.md`
- Modify: `docs/ROADMAP.md`
- Modify: `docs/roadmap/typescript-react-parity-roadmap.md`
- Modify: `docs/roadmap/full-roadmap-blueprint.md`
- Create: `docs/roadmap/phases/phase-179-typescript-knip-unused-code-dependency-facts.md`
- Create if required by Tach policy: `docs/architecture/decisions/2026-07-17-typescript-knip-parser-boundary.md`
- Modify: `tests/docs/test_first_touch_docs.py`
- Modify: `tests/docs/test_roadmap_docs.py`

### Step 1: Write failing external-fixture contract tests

- [ ] Define a small JSON metadata contract and test both fixture files:

```python
assert fixture["source_repository"].startswith("https://github.com/")
assert len(fixture["commit"]) == 40
assert fixture["command"][-2:] == ["--reporter", "json"]
assert fixture["exit_code"] in (0, 1)
assert fixture["supported_finding_count"] >= 0
assert fixture["retained_finding_count"] <= 500
assert fixture["config_sha256"]
assert fixture["lockfile_sha256"]
```

- [ ] Feed each recorded `stdout` payload through `parse_knip_json` and assert counts and bounded retained facts match the metadata.
- [ ] Pin:
  - TanStack Query `97db5d244715642fb63d9ce78566aa632cdfdc07`
  - Astro `91992ef2ccd9a90fa4270633eb4f5d3b811bf315`
- [ ] Run:

```bash
PATH=.venv/bin:$PATH pytest tests/assess/test_typescript_knip_external_fixtures.py -q
```

Expected: FAIL because the fixture files do not exist.

### Step 2: Capture the two public repositories once

- [ ] Use fresh temporary checkouts outside the repository, check out the exact commits, and use each repository's declared package manager and lockfile.
- [ ] Run the repository-native Knip binary with JSON output:

```bash
pnpm exec knip --reporter json
```

- [ ] Record only public, bounded compatibility evidence:
  - repository URL and exact commit;
  - package manager and runtime versions;
  - exact Knip command and process exit code;
  - stdout JSON or `{ "issues": [] }` when the successful tool emits no JSON;
  - supported and retained normalized counts;
  - SHA-256 of the Knip config and lockfile used.
- [ ] Do not commit clones, dependency trees, caches, absolute temporary paths, or environment values.
- [ ] Run the fixture contract tests.

Expected: PASS.

### Step 3: Write failing public-doc and roadmap tests

- [ ] Add DocSync evidence IDs for provider registration, synthetic parser facts, and external fixtures.
- [ ] Update tests to require these phrases/contracts:
  - explicit `typescript_knip_command` example;
  - `pnpm exec knip --reporter json` recommendation;
  - root and workspace support;
  - `full` and `ci` defaults;
  - exit status is honored;
  - 500 normalized fact and 50 compact-line bounds;
  - experimental status;
  - Phase 179 complete with Phase 180 OSV scanning next.
- [ ] Run:

```bash
PATH=.venv/bin:$PATH pytest tests/docs/test_first_touch_docs.py tests/docs/test_roadmap_docs.py tests/docsync/test_public_doc_trace.py -q
```

Expected: FAIL until the documentation and trace map are updated.

### Step 4: Update public docs and close the roadmap phase

- [ ] Document root configuration:

```toml
[tool.agent_maintainer]
enable_typescript = true
typescript_knip_command = ["pnpm", "exec", "knip", "--reporter", "json"]
```

- [ ] Document workspace configuration under `[tool.agent_maintainer.workspaces.<name>]` and state that profiles come from top-level `typescript_knip_profiles`.
- [ ] Recommend exact/lockfile-pinned Knip versions but explicitly state Agent Maintainer does not enforce a Knip version.
- [ ] State the supported categories, ignored categories, bounds, malformed-output behavior, and honored exit semantics.
- [ ] Keep provider status experimental and call out explicit configuration/no inference.
- [ ] Create the Phase 179 page with scope, implementation, tests, public comparison evidence, known limits, and acceptance results.
- [ ] Mark Phase 179 complete in the TypeScript roadmap and full blueprint; make Phase 180 OSV dependency scanning the next item.
- [ ] Keep `docs/ROADMAP.md` within its file-length policy by replacing the active TypeScript phase text instead of appending redundant history.
- [ ] If Tach requires a new cross-domain allowlist, document why normalized parser reuse is preferred to a duplicate core parser.

### Step 5: Run documentation and focused feature checks

- [ ] Run:

```bash
PATH=.venv/bin:$PATH pytest tests/config/test_typescript_config.py tests/config/test_workspace_config.py tests/catalogs/test_typescript_catalog.py tests/repair_facts/test_typescript_knip_facts.py tests/context/test_typescript_exact_facts.py tests/core/test_typescript_structured_output.py tests/assess/test_typescript_knip_external_fixtures.py tests/docs/test_first_touch_docs.py tests/docs/test_roadmap_docs.py tests/docsync/test_public_doc_trace.py -q
PATH=.venv/bin:$PATH python -m agent_maintainer.docsync_cli check
PATH=.venv/bin:$PATH ruff check src tests
PATH=.venv/bin:$PATH tach check
```

Expected: PASS.

### Step 6: Commit the evidence and documentation slice

- [ ] Run `git diff --check`, inspect the Task 3 diff, and stage only Task 3 files.
- [ ] Commit:

```bash
git commit -m "docs: complete TypeScript Knip facts phase"
```

---

## Task 4: Full verification and branch review

**Files:**

- Verify only; fix failures in their owning Task 1–3 files and use a focused conventional commit when needed.

### Step 1: Run the repository's named verification gates

- [ ] Inspect `.codex/tasks.toml`; use `codex-task` for defined repeated gates.
- [ ] Run the fast gate first:

```bash
/Users/Monsky/.codex/bin/codex-task fast --json
```

- [ ] Run the full gate required by the repository before completion:

```bash
/Users/Monsky/.codex/bin/codex-task full --json
```

Expected: PASS. Any documented advisory warnings must be unrelated and non-blocking.

### Step 2: Perform an independent review

- [ ] Give one read-only reviewer the design spec, implementation commits, exact task scope, and acceptance checks.
- [ ] Ask for one batched review covering correctness, malformed JSON safety, deterministic bounds, TypeScript workspace behavior, architecture policy, documentation accuracy, and secret/private-data exposure.
- [ ] Address every confirmed finding with focused tests and a conventional commit; do not rewrite existing commits.

### Step 3: Final repository inspection

- [ ] Run:

```bash
git status --short --branch
git diff --stat origin/main...HEAD
git diff --check origin/main...HEAD
git log --oneline origin/main..HEAD
```

- [ ] Inspect the actual diff and staged state for secrets, credentials, private data, temporary paths, generated dependency trees, and unintended files.
- [ ] Confirm the branch contains only the design, plan, feature, facts, documentation/evidence, and any focused review-fix commits.
- [ ] Confirm the worktree is clean.

### Step 4: Finish the development branch

- [ ] Use the `superpowers:finishing-a-development-branch` skill to choose the user-approved integration path.
- [ ] Push and create/update a non-draft PR only when the existing task workflow calls for publication; never force-push.
- [ ] Report commit hashes, compact verification results, any skipped external recapture with reason, and residual risks.
