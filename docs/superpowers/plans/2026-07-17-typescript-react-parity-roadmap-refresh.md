# TypeScript/React Parity Roadmap Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land a current Phase 177 TypeScript/React parity roadmap on `main`, preserve Phase 176 for Codex rewake hardening, and make advisory package-manager/workspace detection the explicit Phase 178 follow-up.

**Architecture:** Reconstruct the useful ideas from stale commit `386c8c1` as current documentation rather than merging its branch. The durable roadmap owns capability mapping and sequencing; the bounded phase file owns Phase 177 acceptance; the compact roadmap and provider-status page expose only current status and the next safe boundary.

**Tech Stack:** Markdown, pytest documentation contracts, DocSync, Agent Maintainer verifier, Git, GitHub CLI

## Global Constraints

- Start from branch `codex/typescript-parity-roadmap-refresh`, whose parent is current `origin/main` and whose approved design is commit `b2fe6bf`.
- Treat `origin/codex/react-typescript-parity-roadmap` and commit `386c8c1` as read-only reference material; do not merge, rebase, rewrite, or cherry-pick them unchanged.
- Phase 176 remains `Codex Terminal Rewake Hardening`; the parity roadmap is Phase 177.
- Phase 177 is documentation-only: no provider runtime, configuration schema, detector, adapter, workflow, dependency, or command behavior changes.
- Phase 178 observes advisory package-manager/workspace evidence only; repository evidence must never become subprocess arguments.
- TypeScript/JavaScript remains experimental and advisory unless a separate evidence-backed promotion assessment changes it.
- Use focused pull requests to `main`; do not create a long-lived TypeScript integration branch.
- Keep `docs/ROADMAP.md` at or below its enforced 180-line limit.
- Add no dependencies and do not weaken Python-provider behavior, architecture contracts, tests, or verification thresholds.

---

## File Responsibility Map

- `docs/roadmap/typescript-react-parity-roadmap.md`: durable capability map, implementation sequence, Phase 178 safety boundary, evidence bar, and promotion criteria.
- `docs/roadmap/phases/phase-177-typescript-react-parity-roadmap.md`: bounded Phase 177 contract and verification commands.
- `docs/roadmap/full-roadmap-blueprint.md`: one-line phase index entry required for every tracked phase file.
- `docs/ROADMAP.md`: compact current-state pointer showing Phase 177 complete and Phase 178 next.
- `docs/provider-status.md`: truthful provider maturity and next-step wording for users.
- `tests/docs/test_roadmap_docs.py`: structural and semantic roadmap contracts.
- `tests/docs/test_first_touch_docs.py`: public provider-status wording contract and DocSync evidence.

### Task 1: Restore The Durable Phase 177 Roadmap

**Files:**

- Create: `docs/roadmap/typescript-react-parity-roadmap.md`
- Create: `docs/roadmap/phases/phase-177-typescript-react-parity-roadmap.md`
- Modify: `docs/roadmap/full-roadmap-blueprint.md`
- Test: `tests/docs/test_roadmap_docs.py`

**Interfaces:**

- Consumes: approved decisions in `docs/superpowers/specs/2026-07-17-typescript-react-parity-roadmap-refresh-design.md`.
- Produces: the durable roadmap path `docs/roadmap/typescript-react-parity-roadmap.md`, the completed Phase 177 contract, and a Phase 178 boundary that Task 2 can link from current-state docs.

- [ ] **Step 1: Write the failing roadmap contract**

Add these constants beside the existing roadmap path constants in `tests/docs/test_roadmap_docs.py`:

```python
TYPESCRIPT_PARITY_ROADMAP = ROADMAP_ROOT / "typescript-react-parity-roadmap.md"
TYPESCRIPT_PARITY_PHASE = (
    PHASES_DIR / "phase-177-typescript-react-parity-roadmap.md"
)
```

Add this test after `test_roadmap_overview_describes_current_state`:

```python
def test_typescript_parity_roadmap_keeps_execution_explicit_and_phased() -> None:
    """Parity planning stays advisory, evidence-backed, and independently merged."""

    roadmap = TYPESCRIPT_PARITY_ROADMAP.read_text(encoding="utf-8")
    phase = TYPESCRIPT_PARITY_PHASE.read_text(encoding="utf-8")
    normalized_roadmap = " ".join(roadmap.split())

    for phrase in (
        "focused pull requests to `main`",
        "Phase 178: advisory package-manager and workspace detection.",
        "Repository evidence must never become subprocess arguments.",
        "at least two external real-repository comparisons",
        "TypeScript/React blocking-gate promotion assessment",
    ):
        assert phrase in normalized_roadmap
    assert phase.startswith("# Phase 177: TypeScript/React Parity Roadmap")
    assert "Status: complete" in phase
    assert "No provider runtime behavior changes." in phase
```

- [ ] **Step 2: Run the new contract and verify the red state**

Run:

```bash
.venv/bin/pytest -q tests/docs/test_roadmap_docs.py::test_typescript_parity_roadmap_keeps_execution_explicit_and_phased
```

Expected: FAIL with `FileNotFoundError` for `docs/roadmap/typescript-react-parity-roadmap.md`.

- [ ] **Step 3: Create the durable parity roadmap**

Create `docs/roadmap/typescript-react-parity-roadmap.md` with this complete content:

````markdown
# TypeScript/React Parity Roadmap

This roadmap defines the evidence needed for the experimental
TypeScript/JavaScript provider to approach Python-provider parity in TypeScript
and React repositories. TypeScript stays advisory until each blocking candidate
has low-noise fixture and external-repository evidence.

## Integration Strategy

Land each bounded capability through focused pull requests to `main`. Do not
use a long-lived integration branch: experimental provider status and explicit
configuration already isolate incomplete TypeScript behavior while preserving
normal review, rollback, and CI on every slice.

The stale `origin/codex/react-typescript-parity-roadmap` branch is historical
reference only. Phase 176 remains Codex terminal-rewake hardening; this roadmap
is Phase 177.

## Current State

Already landed:

- React-shaped TSX and workspace reviewability evidence.
- Explicit root and workspace-owned lint, typecheck, and test commands.
- TypeScript compiler, ESLint JSON, Jest/Vitest JSON, Istanbul summary, and LCOV
  repair facts.
- TypeScript/React doctor and setup-advisor guidance.

Still missing before a promotion assessment:

- Blocking TypeScript/React reviewability gates.
- Advisory package-manager and workspace detection.
- First-class dead-code, dependency, security, architecture, changed-line
  coverage, mutation, and generated-file adapters.
- Broader external evidence across React, Vite, Next.js, and workspace layouts.

## Parity Tool Map

| Python capability | TypeScript/React candidate | Status | Decision |
|---|---|---|---|
| Black/Ruff formatting | Biome format or Prettier | Strong replacement | Recommend a detected project formatter; never add one automatically. |
| Ruff/Pylint/Wemake lint | ESLint, typescript-eslint, React plugins, SonarJS | Partial replacement | Measure typed ESLint and React rulepacks instead of imitating one Python tool. |
| MyPy/Pyright | `tsc --noEmit` or project typecheck scripts | Strong replacement | Preserve explicit command ownership and stable compiler facts. |
| Pytest/unittest | Vitest, Jest, Playwright component tests, Testing Library | Strong replacement | Execute configured scripts only and parse stable artifacts. |
| Coverage.py/diff-cover | Istanbul/V8 LCOV plus a changed-line adapter | Partial replacement | Build advisory LCOV changed-line facts before any threshold gate. |
| Tach/import-linter | dependency-cruiser, Nx boundaries, ESLint boundaries | Partial replacement | Start with dependency-cruiser; support Nx only when a repository declares it. |
| Vulture/Deptry | Knip | Strong replacement | Parse stable Knip JSON for unused files, exports, dependencies, and unresolved binaries. |
| pip-audit | OSV Scanner plus package-manager audit | Strong replacement | Add lockfile-aware OSV facts before package-manager audit summaries. |
| Bandit | Semgrep JS/TS rules and ESLint security plugins | Partial replacement | Keep advisory until external evidence measures false positives. |
| Gitleaks | Gitleaks | Ecosystem-neutral | Reuse the existing secret scan without a TypeScript adapter. |
| Radon/Xenon | ESLint complexity and SonarJS cognitive complexity | Partial replacement | Measure advisory facts before defining thresholds. |
| Mutmut | StrykerJS | Strong replacement | Add report parsing and a runtime-cost guard before ratcheting. |
| Python SBOM | CycloneDX npm or package-manager SBOM output | Strong replacement | Detect optional artifacts before requiring execution. |
| License reporting | SBOM license fields | Partial replacement | Prefer existing SBOM data over another command surface. |
| Interrogate | TypeDoc or API Extractor for libraries | No app-repo equivalent | Do not force Python docstring coverage onto React applications. |
| DocSync | DocSync | Ecosystem-neutral | Keep the existing language-agnostic documentation contract. |
| React hooks | `eslint-plugin-react-hooks` | Strong React signal | Recommend when present or explicitly selected. |
| JSX accessibility | `eslint-plugin-jsx-a11y` | Strong React signal | Start advisory and measure external-repository noise. |
| Testing Library quality | `eslint-plugin-testing-library` | Strong React signal | Recommend only for repositories that use Testing Library or opt in. |
| Generated-file policy | Explicit classifier and framework evidence | No single replacement | Cover framework and codegen outputs with fixture-backed rules. |

## Implementation Sequence

1. Phase 178: advisory package-manager and workspace detection.
2. Knip unused-code and dependency facts.
3. OSV and package-manager audit facts.
4. Dependency-cruiser architecture-boundary facts, followed by declared Nx
   boundary support.
5. LCOV changed-line coverage facts.
6. React hooks, JSX accessibility, and Testing Library recommendations.
7. Explicit generated-file and framework policy evidence.
8. StrykerJS mutation facts with a runtime-cost guard.
9. TypeScript/React blocking-gate promotion assessment.

Only Phase 178 is numbered in advance. Assign later phase numbers when each
slice has an approved design and implementation plan.

## Phase 178 Safety Boundary

Phase 178 may observe root `package.json` metadata, the `packageManager` field,
Corepack-related declarations, npm/pnpm/Yarn/Bun lockfiles, workspace manifests,
script names, and explicit Agent Maintainer workspace configuration.

Facts retain file-and-field provenance. Malformed metadata, multiple lockfiles,
conflicting declarations, and unsupported workspace shapes remain visible as
bounded advisory ambiguity. Agent Maintainer does not select a preferred package
manager, fall back to npm, or infer nested package ownership.

Doctor and setup-advisor may explain the evidence and show reviewed
configuration choices. The provider executor continues to use only explicit
root or workspace command arrays. Repository evidence must never become
subprocess arguments.

## Evidence And Promotion Criteria

Every future blocking candidate requires temporary-Git fixture coverage and at
least two external real-repository comparisons. Evidence must measure noise,
repair usefulness, runtime cost where relevant, and behavior across React,
Vite, Next.js, and workspace layouts.

TypeScript/React can move beyond experimental only when:

- blocking candidates have explicit low-noise evidence;
- doctor and setup-advisor remain explicit-command first;
- changed-line coverage and repair facts are stable;
- unsupported package managers, runners, frameworks, generated files, and
  monorepo layouts are documented;
- Python-provider behavior and architecture ownership do not regress;
- the complete focused, broad local, and hosted CI gates pass.

## Out Of Scope

- Executing inferred package scripts or package-manager commands.
- Enabling TypeScript/React blocking gates by default before promotion.
- Adding another ecosystem before the TypeScript/React promotion assessment.
- Weakening Python behavior to create a superficially provider-neutral API.
- Forcing Python-only documentation rules onto React application code.
````

- [ ] **Step 4: Create the bounded Phase 177 contract**

Create `docs/roadmap/phases/phase-177-typescript-react-parity-roadmap.md` with this complete content:

````markdown
# Phase 177: TypeScript/React Parity Roadmap

Status: complete

## Goal

Restore a current TypeScript/React parity roadmap on `main` and establish
advisory package-manager/workspace detection as the next bounded slice.

## Scope

- Map Python-provider capabilities to honest TypeScript/React candidates.
- Distinguish strong, partial, ecosystem-neutral, and unavailable equivalents.
- Define focused implementation slices and evidence requirements.
- Keep Phase 176 assigned to Codex terminal-rewake hardening.
- Use focused pull requests to `main` instead of a long-lived integration branch.

## Non-Goals

- No provider runtime behavior changes.
- No package-manager or workspace detector implementation.
- No inferred command execution.
- No dependency or workflow changes.
- No blocking TypeScript/React gate or provider promotion.

## Acceptance Criteria

- The durable roadmap records current evidence and remaining parity gaps.
- Phase 178 is advisory package-manager and workspace detection.
- Repository evidence is explicitly forbidden from becoming subprocess arguments.
- Every blocking candidate requires fixture and external-repository evidence.
- The compact roadmap and provider status point to the current parity track.

## Verification

Run:

```bash
.venv/bin/pytest -q tests/docs/test_roadmap_docs.py tests/docs/test_first_touch_docs.py
.venv/bin/python -m docsync check
git diff --check
```
````

- [ ] **Step 5: Add Phase 177 to the complete phase index**

Append this row after Phase 176 in `docs/roadmap/full-roadmap-blueprint.md`:

```markdown
| 177 | [TypeScript/React Parity Roadmap](phases/phase-177-typescript-react-parity-roadmap.md) |
```

- [ ] **Step 6: Run the complete roadmap test file**

Run:

```bash
.venv/bin/pytest -q tests/docs/test_roadmap_docs.py
```

Expected: PASS, including the new semantic contract, the phase-index link
contract, the 500-line phase limit, and existing roadmap size limits.

- [ ] **Step 7: Commit the durable roadmap slice**

Run:

```bash
git add -- tests/docs/test_roadmap_docs.py docs/roadmap/typescript-react-parity-roadmap.md docs/roadmap/phases/phase-177-typescript-react-parity-roadmap.md docs/roadmap/full-roadmap-blueprint.md
git commit -m "docs: restore TypeScript React parity roadmap"
```

Expected: commit hooks pass and the commit contains exactly the four listed
files.

### Task 2: Activate The Current Track And Provider Boundary

**Files:**

- Modify: `docs/ROADMAP.md`
- Modify: `docs/provider-status.md`
- Test: `tests/docs/test_roadmap_docs.py`
- Test: `tests/docs/test_first_touch_docs.py`

**Interfaces:**

- Consumes: the durable roadmap and Phase 177 paths created by Task 1.
- Produces: a compact active-track pointer, truthful public provider status, and the exact Phase 178 advisory boundary users and future implementers rely on.

- [ ] **Step 1: Write failing current-state and provider wording assertions**

Add these assertions to
`test_active_roadmap_reports_current_strict_and_api_state` in
`tests/docs/test_roadmap_docs.py`:

```python
    assert "Phase 176: Codex Terminal Rewake Hardening" in text
    assert "Phase 177: TypeScript/React Parity Roadmap" in text
    assert "Phase 178: Advisory Package-Manager And Workspace Detection" in text
    assert "(roadmap/typescript-react-parity-roadmap.md)" in text
```

Add these phrases to the `docs/provider-status.md` tuple in
`test_provider_docs_contain_clear_maturity_phrases` in
`tests/docs/test_first_touch_docs.py`:

```python
            "TypeScript/React parity work now advances through focused pull "
            "requests to `main`.",
            "Phase 178 observes package-manager and workspace evidence for "
            "advisory setup facts only.",
            "Detected evidence never creates or executes a command.",
```

- [ ] **Step 2: Run both contracts and verify the red state**

Run:

```bash
.venv/bin/pytest -q tests/docs/test_roadmap_docs.py::test_active_roadmap_reports_current_strict_and_api_state tests/docs/test_first_touch_docs.py::test_provider_docs_contain_clear_maturity_phrases
```

Expected: FAIL because the Phase 177/178 current-state lines and new
provider-status wording are absent.

- [ ] **Step 3: Add the compact active parity track**

Insert this exact section between the completed Phase 176 section and
`## Active: External Proof And Architecture Hardening` in `docs/ROADMAP.md`:

```markdown
## Active: TypeScript/React Parity

Follow the [parity roadmap](roadmap/typescript-react-parity-roadmap.md). Phase 177
refreshes the plan; Phase 178 adds advisory package-manager/workspace detection.

- [x] Phase 177: TypeScript/React Parity Roadmap
- [ ] Phase 178: Advisory Package-Manager And Workspace Detection
```

This addition brings the file to the enforced 180-line maximum; do not add
extra blank lines or duplicate roadmap prose.

- [ ] **Step 4: Update the public provider-status boundary**

Replace the opening paragraph of `## Current Focus` in
`docs/provider-status.md` with this exact content, retaining the existing links
to the TypeScript maturation notes and Java provider evidence immediately after
it:

```markdown
TypeScript/JavaScript is again the active parity track. TypeScript/React parity
work now advances through focused pull requests to `main`. The
[TypeScript/React Parity Roadmap](roadmap/typescript-react-parity-roadmap.md)
keeps the provider experimental while evidence accumulates. Phase 178 observes
package-manager and workspace evidence for advisory setup facts only. Detected
evidence never creates or executes a command.

Java/Gradle remains the second built-in experimental priority. Neither provider
is promoted by this sequencing decision. TypeScript still must satisfy the bar
in
```

The retained text must continue with the existing
`[TypeScript Provider Maturation Notes]` link, followed by the Java provider and
calibration links.

- [ ] **Step 5: Run focused documentation and DocSync contracts**

Run:

```bash
.venv/bin/pytest -q tests/docs/test_roadmap_docs.py tests/docs/test_first_touch_docs.py tests/docsync/test_public_doc_trace.py
.venv/bin/python -m docsync check
```

Expected: all selected tests PASS and DocSync prints `DocSync check passed.`

- [ ] **Step 6: Confirm compact-roadmap and diff hygiene limits**

Run:

```bash
wc -l docs/ROADMAP.md
git diff --check
```

Expected: `docs/ROADMAP.md` reports no more than 180 lines and
`git diff --check` prints nothing.

- [ ] **Step 7: Commit the current-state integration slice**

Run:

```bash
git add -- docs/ROADMAP.md docs/provider-status.md tests/docs/test_roadmap_docs.py tests/docs/test_first_touch_docs.py
git commit -m "docs: activate TypeScript parity roadmap"
```

Expected: commit hooks pass and the commit contains exactly the four listed
files.

### Task 3: Verify, Publish, And Merge Phase 177

**Files:**

- Verify only: all committed Phase 177 files from Tasks 1 and 2.

**Interfaces:**

- Consumes: the approved design commit plus the two focused implementation commits.
- Produces: a green pull request merged into `main`, leaving the existing stale reference branch untouched.

- [ ] **Step 1: Review the complete branch diff and state**

Run:

```bash
git status --short --branch
git diff --check origin/main...HEAD
git diff --stat origin/main...HEAD
git diff origin/main...HEAD -- docs/superpowers/specs/2026-07-17-typescript-react-parity-roadmap-refresh-design.md docs/superpowers/plans/2026-07-17-typescript-react-parity-roadmap-refresh.md docs/roadmap/typescript-react-parity-roadmap.md docs/roadmap/phases/phase-177-typescript-react-parity-roadmap.md docs/roadmap/full-roadmap-blueprint.md docs/ROADMAP.md docs/provider-status.md tests/docs/test_roadmap_docs.py tests/docs/test_first_touch_docs.py
```

Expected: the worktree is clean, only the approved documentation/test surface
differs from `origin/main`, and no whitespace errors appear.

- [ ] **Step 2: Run the broad local verifier on the exact branch state**

Run:

```bash
PATH=.venv/bin:$PATH AGENT_MAINTAINER_ALLOW_FOREGROUND_WAIT=1 just v
```

Expected: `PASS` for the `full` profile. Existing structure-cohesion warnings
may remain warnings; no failed check is acceptable.

- [ ] **Step 3: Push the focused branch**

Run:

```bash
git push -u origin codex/typescript-parity-roadmap-refresh
```

Expected: pre-push hooks pass and the remote branch is created without
force-pushing or modifying the stale roadmap branch.

- [ ] **Step 4: Open the Phase 177 pull request**

Run:

```bash
gh pr create --base main --head codex/typescript-parity-roadmap-refresh --title "docs: refresh TypeScript React parity roadmap" --body "Restores the approved TypeScript/React parity roadmap as Phase 177 on current main, preserves Phase 176 for Codex rewake hardening, replaces the stale integration-branch strategy with focused PRs, and defines advisory package-manager/workspace detection as Phase 178."
```

Expected: GitHub returns the URL of one open, ready-for-review pull request.

- [ ] **Step 5: Wait for every required hosted check**

Run:

```bash
TS_PR_NUMBER=$(gh pr view --json number --jq .number)
PATH=.venv/bin:$PATH AGENT_MAINTAINER_ALLOW_FOREGROUND_WAIT=1 just wp "$TS_PR_NUMBER"
```

Expected: `Result: PASS` for the pull request. Diagnose and fix any failure
before continuing.

- [ ] **Step 6: Confirm mergeability and merge without deleting branches**

Run:

```bash
TS_PR_NUMBER=$(gh pr view --json number --jq .number)
gh pr view "$TS_PR_NUMBER" --json state,isDraft,mergeable,mergeStateStatus,statusCheckRollup
gh pr merge "$TS_PR_NUMBER" --merge
```

Expected: the PR is open, not draft, mergeable, clean, and fully green before
the merge command succeeds. Do not pass `--delete-branch`.

- [ ] **Step 7: Verify the merged `main` state**

Run:

```bash
git fetch origin main:refs/remotes/origin/main
TS_PR_NUMBER=$(gh pr view --json number --jq .number)
gh pr view "$TS_PR_NUMBER" --json state,mergedAt,mergeCommit,url
git show origin/main:docs/ROADMAP.md | rg "Phase 177|Phase 178"
git show origin/main:docs/provider-status.md | rg "focused pull requests|advisory setup facts"
```

Expected: the PR state is `MERGED`; `origin/main` names Phase 177 and Phase 178;
provider status preserves the explicit advisory-only detection boundary.
