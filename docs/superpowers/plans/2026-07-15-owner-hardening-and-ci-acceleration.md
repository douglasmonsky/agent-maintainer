# Owner Hardening and CI Acceleration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve owner-facing correctness and speed while preserving one fail-closed verification and release evidence contract.

**Architecture:** Correct policy and diagnostics first, then add real-environment safety tests. Land low-risk workflow caching and release parallelism before introducing verifier-native partial manifests and PR sharding. Finish with a measured local commit path and bounded deletion of unused compatibility facades.

**Tech Stack:** Python 3.11–3.14, pytest, GitHub Actions, TOML/YAML, Agent Maintainer verifier, Agent Run Artifacts, Agent Waits, Agent Perf/Scalene.

## Global Constraints

- Keep total and changed-code coverage floors at 90%.
- Preserve `root_module = "forbid"` and all Tach boundaries.
- Do not publish, change credentials, or change GitHub environment protection.
- Cached external binaries must pass pinned SHA-256 verification after every restore.
- Terminal release jobs must require exact-SHA aggregate evidence and the verified distribution bundle.
- Add no compatibility shims.
- Use test-first red/green cycles for behavior changes and focused Conventional Commits.

---

### Task 1: Policy consistency and pip-audit repair facts

**Files:**

- Modify: `pyproject.toml`
- Create: `src/agent_repair_facts/parsers/security.py`
- Modify: `src/agent_repair_facts/registry.py`
- Create: `tests/repair_facts/test_security_repair_facts.py`
- Modify: `tests/config/test_config_loading.py`

**Interfaces:**

- Produces: `pip_audit_facts(path: FactSource, check: str) -> list[dict[str, object]]`
- Registers: artifact parser entry `("pip-audit", security.pip_audit_facts)`

- [ ] Write a failing configuration test requiring `src/agent_waits` in the repository Vulture paths and one 90% direct coverage floor.
- [ ] Run `.venv/bin/pytest tests/config/test_config_loading.py -q`; expect the new assertions to fail.
- [ ] Write failing parser tests for one vulnerability, multiple aliases/fix versions, malformed JSON, and an empty dependency list.
- [ ] Run `.venv/bin/pytest tests/repair_facts/test_security_repair_facts.py -q`; expect import/registration failure.
- [ ] Implement the minimal JSON parser using `payloads.read_json`, `payloads.json_object`, and `payloads.fact_payload`; do not parse human log text.
- [ ] Set `[tool.coverage.report].fail_under = 90` and add `src/agent_waits` to `vulture_paths`.
- [ ] Run both focused test files and `python3 -m agent_maintainer assess repair-fact-coverage --json`; expect pip-audit to use a structured parser.
- [ ] Commit with `fix: align verification policy configuration`.

### Task 2: Worktree doctor and safe artifact hygiene

**Files:**

- Modify: `src/agent_maintainer/doctor/support/environment.py`
- Modify: `src/agent_maintainer/doctor/support/integrations.py`
- Create: `src/agent_maintainer/doctor/artifact_cleanup.py`
- Modify: `src/agent_maintainer/doctor/cli.py`
- Modify: `tests/doctor/test_doctor_environment.py`
- Modify: `tests/doctor/test_doctor_support_integrations.py`
- Create: `tests/doctor/test_artifact_cleanup.py`

**Interfaces:**

- Produces: `artifact_cleanup_plan(repo_root: Path) -> tuple[Path, ...]`
- Produces: `prune_generated_artifacts(repo_root: Path, *, apply: bool) -> tuple[Path, ...]`

- [ ] Add a failing Git-state test where porcelain output contains `[gone]`; require WARNING with an upstream-remediation hint.
- [ ] Add a failing hook test requiring the exact repository bootstrap/hook command in the hint.
- [ ] Add failing cleanup tests proving default dry-run, root confinement, known-path allowlisting, and refusal of symlinks/unknown paths.
- [ ] Run the focused doctor tests; confirm the expected failures.
- [ ] Implement the smallest diagnostic changes and a dedicated cleanup module.
- [ ] Expose cleanup through an explicit doctor CLI option with dry-run default and `--apply` mutation.
- [ ] Run all doctor tests and `just doctor`.
- [ ] Commit with `fix: improve worktree health diagnostics`.

### Task 3: Real-environment contract smokes

**Files:**

- Create: `tests/packaging/test_owner_contract_smoke.py`
- Create: `tests/wait/test_durable_wait_contract_smoke.py`
- Modify: `pyproject.toml`

**Interfaces:**

- Tests public CLI/process contracts only; no new production API.

- [ ] Add a smoke that builds/installs the local wheel in an isolated environment and initializes a temporary Git repository.
- [ ] Add a smoke that creates one deterministic failing check, consumes its repair fact, repairs the fixture, and verifies pass.
- [ ] Add a synthetic durable wait smoke that registers, sweeps, and resumes a terminal local process without launchd or network access.
- [ ] Add an exact-SHA release evidence aggregate/validate smoke using local manifests.
- [ ] Run each smoke individually and confirm missing behavior or fixture wiring fails before implementation changes.
- [ ] Add only the fixture/support behavior required for the smokes to pass.
- [ ] Run the complete smoke set twice to detect retained state.
- [ ] Commit with `test: add end-to-end maintainer contract smokes`.

### Task 4: Safe workflow caching

**Files:**

- Modify: `.github/workflows/verify.yml`
- Modify: `.github/workflows/deep-verify.yml`
- Modify: `.github/workflows/publish.yml`
- Modify: `tests/packaging/test_github_actions_policy.py`

**Interfaces:**

- GitHub Actions cache keys include OS, Python version where applicable, and dependency/tool identity.

- [ ] Change workflow-policy tests first to require pip lockfile caching, npm caching with `npm ci`, and checksum verification after external-tool cache restoration.
- [ ] Run `.venv/bin/pytest tests/packaging/test_github_actions_policy.py -q`; expect failures.
- [ ] Add fully pinned cache actions only if setup-python/setup-node native caching cannot cover the asset.
- [ ] Update all three workflows without changing profile commands.
- [ ] Run the focused policy tests plus YAML, Actionlint, and Zizmor checks through the CI profile.
- [ ] Commit with `ci: cache verified workflow dependencies`.

### Task 5: Parallel release evidence and concurrent build

**Files:**

- Modify: `.github/workflows/publish.yml`
- Modify: `tests/packaging/test_publish_workflow.py`
- Modify: `docs/release-checklist.md`
- Modify: `docs/architecture/decisions/2026-07-10-exact-commit-release-evidence.md`

**Interfaces:**

- Matrix profiles: `full`, `ci`, `security`, `manual`, `release`
- Aggregate job id remains `release-evidence`
- Profile artifacts are named with both `github.sha` and profile.

- [ ] Rewrite workflow tests first to require the five-leg matrix, unchanged aggregate artifact name, build independence, and dual downstream gates.
- [ ] Run publish/release tests and confirm they fail against the serial workflow.
- [ ] Implement the matrix while preserving the special CI and release commands.
- [ ] Download manifests into runner temporary storage and aggregate them in contract order.
- [ ] Remove evidence consumption from the non-publishing build job; retain evidence and bundle validation before every terminal mutation.
- [ ] Update release documentation and ADR language from one checkout to isolated exact-SHA checkouts.
- [ ] Run publish, release-evidence, workflow policy, DocSync, CI, security, and manual gates.
- [ ] Commit with `ci: parallelize release evidence profiles`.

### Task 6: Verifier-native partial manifests

**Files:**

- Create: `src/agent_maintainer/verify/groups.py`
- Create: `src/agent_run_artifacts/verification_aggregate.py`
- Modify: `src/agent_maintainer/verify/quiet.py`
- Modify: `src/agent_maintainer/verify/artifacts.py`
- Modify: `tests/verify/test_verify_quiet_config.py`
- Create: `tests/verify/test_verification_groups.py`
- Create: `tests/verify/test_verification_aggregate.py`

**Interfaces:**

- Produces: `checks_for_group(checks: Sequence[Check], group: str) -> list[Check]`
- Produces: `aggregate_partial_manifests(paths: Sequence[Path]) -> dict[str, object]`
- Partial identity includes profile, group, HEAD, base ref, compare branch, config hash, and selected check names.

- [ ] Write failing tests for group selection, unknown groups, duplicate checks, missing groups, identity mismatch, failed partials, and deterministic aggregation.
- [ ] Run focused tests and confirm missing-module/API failures.
- [ ] Implement immutable group definitions and fail-closed aggregation without changing sequential execution.
- [ ] Add CLI/config parsing for explicit partial group selection and aggregate-only operation.
- [ ] Prove a normal sequential invocation produces unchanged results and artifacts.
- [ ] Run verifier, artifact, runtime-eventing, and release-evidence tests.
- [ ] Commit with `feat: aggregate partial verification results`.

### Task 7: Parallel PR and push verification

**Files:**

- Modify: `.github/workflows/verify.yml`
- Modify: `tests/packaging/test_github_actions_policy.py`
- Create: `tests/packaging/test_parallel_verify_workflow.py`

**Interfaces:**

- Component jobs: `tests-and-coverage`, `static-and-policy`
- Protected conclusion remains job id `verify`.

- [ ] Add failing workflow tests requiring both component jobs, coverage combination/enforcement, partial artifact transfer, and one aggregate result.
- [ ] Implement component jobs using verifier-native groups only.
- [ ] Ensure base-ref/config identity is computed once and supplied identically.
- [ ] Keep the existing Python compatibility matrix unchanged.
- [ ] Run workflow tests and `just vc`.
- [ ] Commit with `ci: parallelize pull request verification`.

### Task 8: Measured fast local commit path

**Files:**

- Modify: `pyproject.toml`
- Modify: `.pre-commit-config.yaml`
- Modify: `src/agent_maintainer/verify/locking.py`
- Modify: `tests/verify/test_locking.py`
- Modify: `tests/packaging/test_precommit_config.py`

**Interfaces:**

- Reuse remains governed by `VerificationFingerprint`; no partial fingerprint matches.

- [ ] Repair and rerun Agent Perf until a representative profile contains application hotspots; retain unprofiled timings.
- [ ] Add failing tests defining which inexpensive checks and affected tests run at commit time.
- [ ] Add failing fingerprint tests proving source, tests, config, dependency, base-ref, and environment changes invalidate reuse.
- [ ] Implement the minimal profile/hook change and exact reuse behavior.
- [ ] Require full verification at pre-push or an exact successful fingerprint.
- [ ] Measure documentation-only, small-source, test-only, and cross-package changes.
- [ ] Run precommit, full, and CI profiles.
- [ ] Commit with `feat: speed up the local commit verification path`.

### Task 9: Stability classification and bounded facade deletion

**Files:**

- Create: `docs/architecture/subsystem-stability.md`
- Modify: `README.md`
- Modify: repository-owned compatibility facade modules selected by reference analysis
- Modify: importing source/tests for each selected facade

**Interfaces:**

- Stability labels are documentation metadata only: core, optional, experimental.
- No new runtime registry or compatibility layer.

- [ ] Classify current subsystems and verify every documented public command has one label.
- [ ] Inventory compatibility facades and exact repository consumers with semantic/native reference checks.
- [ ] Select the least externally exposed facade group and write import/architecture tests that fail after direct-boundary migration is required.
- [ ] Migrate repository consumers, delete the facade, and run package/import/Tach tests.
- [ ] Repeat in bounded commits; stop before CLI/public import deletion unless usage evidence proves it safe.
- [ ] Review touched hotspot files and extract only concrete persistence/policy or launch/state boundaries.
- [ ] Commit documentation with `docs: classify subsystem stability`; use one `refactor:` commit per deleted facade group.

### Task 10: Final verification and branch completion

**Files:**

- Modify: `CHANGELOG.md`
- Modify: `.agent-maintainer/change-plans/owner-hardening-and-ci-acceleration.md`

**Interfaces:**

- No new interface.

- [ ] Regenerate guidance/DocSync artifacts only where source contracts require it.
- [ ] Run focused changed-surface tests, then `just vc`, `security`, `manual`, and one final `just v`.
- [ ] Inspect status, diff stat, complete diff, staged paths, and secret/privacy exposure.
- [ ] Obtain one independent comprehensive review and resolve actionable findings.
- [ ] Mark the change plan complete only after all required gates pass.
- [ ] Update the changelog with owner-facing behavior and measured CI/local timing.
- [ ] Use superpowers:finishing-a-development-branch to present integration options.
