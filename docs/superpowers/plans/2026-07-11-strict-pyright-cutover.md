# Strict Pyright Dogfood Cutover Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make ordinary Pyright the repository's zero-error strict gate and remove the migration-only dogfood baseline.

**Architecture:** Change only repository policy, not the reusable ratchet product. A repository-policy test locks in strict ordinary checking, a disabled dogfood ratchet, and absence of the baseline artifact; the full verifier then exercises strict Pyright through its standard path.

**Tech Stack:** Python 3.11-3.14, Pyright, pytest, TOML, Agent Maintainer change plans and verifier.

## Global Constraints

- Preserve the reusable strict-ratchet runner and all downstream configuration fields.
- Do not add suppressions, casts, permissive `Any`, dependencies, or workflow changes.
- Keep historical stabilization evidence intact; add a dated completion note instead of rewriting history.
- Require exact zero diagnostics from ordinary Pyright before merge.

---

### Task 1: Lock the dogfood policy with a failing test

**Files:**
- Create: `.agent-maintainer/change-plans/pyright-strict-cutover.md`
- Modify: `tests/config/test_pyright_strict_config.py`

**Interfaces:**
- Consumes: `maintainer_config_loader.read_pyproject(path)` and `maintainer_config_loader.apply_pyproject(config, payload)`.
- Produces: repository policy evidence that ordinary mode is `strict`, the ratchet is disabled, and `config/pyright-strict-baseline.json` is absent.

- [ ] **Step 1: Create the active cohesive change plan**

Allow only the change plan, this design/implementation documentation, `pyproject.toml`, the strict baseline deletion, the Phase 75 roadmap entry, and the focused configuration test. Require tests and full verification; forbid source, workflows, production config, and environment files.

- [ ] **Step 2: Write the failing repository-policy test**

```python
from tests.support.paths import REPO_ROOT


def test_repository_uses_strict_pyright_without_migration_baseline() -> None:
    """Dogfood policy uses ordinary strict checking after migration reaches zero."""

    loaded = maintainer_config_loader.apply_pyproject(
        MaintainerConfig(),
        maintainer_config_loader.read_pyproject(REPO_ROOT / "pyproject.toml"),
    )

    assert loaded.pyright_type_checking_mode == "strict"
    assert loaded.pyright_strict_ratchet_enabled is False
    assert not (REPO_ROOT / "config" / "pyright-strict-baseline.json").exists()
```

- [ ] **Step 3: Run the test to verify the pre-cutover policy fails**

Run: `.venv/bin/pytest -q tests/config/test_pyright_strict_config.py::test_repository_uses_strict_pyright_without_migration_baseline`

Expected: FAIL because the current repository uses `standard`, enables the ratchet, and still contains the baseline.

### Task 2: Promote ordinary Pyright and retire the baseline

**Files:**
- Modify: `pyproject.toml`
- Delete: `config/pyright-strict-baseline.json`
- Modify: `docs/roadmap/phases/phase-75-below-10-debt-and-strict-typing-ratchets.md`

**Interfaces:**
- Consumes: the existing ordinary `pyright` verifier check.
- Produces: strict zero-error enforcement in normal/full/hosted verification without a dogfood comparison artifact.

- [ ] **Step 1: Change repository policy**

Set:

```toml
pyright_type_checking_mode = "strict"
pyright_strict_ratchet_enabled = false
```

Remove the repository-specific `pyright_strict_baseline` and `pyright_strict_max_errors` assignments. Do not change their schema defaults or consumer documentation.

- [ ] **Step 2: Delete the obsolete zero baseline**

Delete `config/pyright-strict-baseline.json`. Do not delete `src/agent_maintainer/runners/pyright_strict_baseline.py` or its tests because they remain a supported migration feature.

- [ ] **Step 3: Record roadmap completion**

Append a dated completion follow-up to Phase 75 stating that the dogfood repository reached zero strict diagnostics across 740 files, ordinary Pyright is now strict, and the reusable disabled-by-default ratchet remains available to downstream repositories.

- [ ] **Step 4: Run focused red-green validation**

Run: `.venv/bin/pytest -q tests/config/test_pyright_strict_config.py`

Expected: PASS.

Run: `PYTHONPATH=src .venv/bin/python -m agent_maintainer.runners.pyright`

Expected: PASS with zero errors under the generated strict configuration.

Run: `PYTHONPATH=src .venv/bin/python -m agent_maintainer.runners.pyright_strict`

Expected: PASS with `pyright strict ratchet skipped: disabled`.

### Task 3: Verify, complete, and publish the cutover

**Files:**
- Modify: `.agent-maintainer/change-plans/pyright-strict-cutover.md`

**Interfaces:**
- Consumes: completed Tasks 1-2.
- Produces: a merged, hosted-verified strict cutover and a complete change plan.

- [ ] **Step 1: Run local quality gates**

Run:

```bash
.venv/bin/ruff check tests/config/test_pyright_strict_config.py
.venv/bin/ruff format --check tests/config/test_pyright_strict_config.py
git diff --check
just v
```

Expected: all commands pass; the full verifier reports PASS.

- [ ] **Step 2: Complete the change plan and re-run policy validation**

Set the change plan status to `complete`, then rerun its focused validation and strict ordinary Pyright. Expected: PASS.

- [ ] **Step 3: Commit the implementation**

Stage only the planned files and commit:

```bash
git commit -m "chore: promote repository pyright to strict"
```

- [ ] **Step 4: Publish and merge**

Push `refactor/pyright-strict-cutover`, open a draft PR to `main`, and wait for CodeQL, Python 3.11-3.14 compatibility, and hosted verification. Confirm there are no unresolved comments or reviews, mark ready, merge with a merge commit, and delete the remote branch.

- [ ] **Step 5: Verify merged state**

Fetch `origin/main`, fast-forward this worktree, confirm the worktree is clean, confirm the baseline path is absent, and run ordinary Pyright once from the merged commit. Expected: zero errors.
