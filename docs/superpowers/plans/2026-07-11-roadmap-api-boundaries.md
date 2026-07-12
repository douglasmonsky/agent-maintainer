# Roadmap, API Support, and Package Boundaries Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Correct roadmap drift, classify the product surface, publish the pre-1.0 API and compatibility policy, and enforce `agent_waits` ownership.

**Architecture:** Keep the product CLI-first: only explicitly documented Python imports become supported beta API. Treat compatibility shims as migration groups with removal gates, and keep `agent_waits` product-neutral through a readable AST boundary test in addition to Tach.

**Tech Stack:** Python 3.11+, pytest, Markdown, existing CLI usage string, Tach/AST architecture tests.

## Global Constraints

- Do not remove a compatibility shim before `0.1.0b6`.
- Do not promote every wheel-distributed package to supported public API.
- Keep `docsync.api` as the only initially named supported Python import surface.
- Keep basic quiet waits distinct from experimental terminal rewake.
- Do not mark `0.1.0b6` published or run the real-turn smoke.
- Do not refactor `MaintainerConfig` in this plan.

---

### Task 1: Enforce and document the `agent_waits` package boundary

**Files:**

- Modify: `tests/architecture/test_internal_package_boundaries.py`
- Modify: `docs/roadmap/internal-package-boundaries.md`

**Interfaces:**

- Consumes: existing `PackageBoundary` and `BOUNDARIES` AST regression harness.
- Produces: an explicit `agent_waits` rule forbidding imports from product packages.

- [ ] **Step 1: Write the failing boundary-declaration test**

Append this test before the existing import-direction test:

```python
def test_agent_waits_boundary_is_declared() -> None:
    """Reusable wait primitives keep an explicit product-neutral boundary."""

    boundary = next(
        (item for item in BOUNDARIES if item.package == "agent_waits"),
        None,
    )

    assert boundary == PackageBoundary(
        "agent_waits",
        frozenset(
            {
                "agent_client_hooks",
                "agent_context",
                "agent_maintainer",
                "agent_repair_facts",
                "agent_run_artifacts",
                "archguard",
                "docsync",
            }
        ),
    )
```

- [ ] **Step 2: Run the test to verify RED**

Run: `PYTHONPATH=src .venv/bin/pytest tests/architecture/test_internal_package_boundaries.py::test_agent_waits_boundary_is_declared -q`

Expected: FAIL because `BOUNDARIES` does not contain `agent_waits`.

- [ ] **Step 3: Add the production boundary declaration**

Add the matching `PackageBoundary` entry to `BOUNDARIES`:

```python
PackageBoundary(
    "agent_waits",
    frozenset(
        {
            "agent_client_hooks",
            "agent_context",
            "agent_maintainer",
            "agent_repair_facts",
            "agent_run_artifacts",
            "archguard",
            "docsync",
        }
    ),
),
```

Add `agent_waits/` to the `Current Package Shape` tree with the description
“product-neutral wait records, watcher state, and notification claims.” Add a
completed-state bullet saying its dependency direction is covered by the AST
regression and its package-local Tach contract.

- [ ] **Step 4: Verify GREEN**

Run: `PYTHONPATH=src .venv/bin/pytest tests/architecture/test_internal_package_boundaries.py -q`

Expected: PASS with both the declaration assertion and the recursive import scan.

- [ ] **Step 5: Commit the boundary slice**

```bash
git add -- tests/architecture/test_internal_package_boundaries.py docs/roadmap/internal-package-boundaries.md
git commit -m "test: enforce agent waits package boundary"
```

### Task 2: Publish a discoverable pre-1.0 API and shim policy

**Files:**

- Create: `docs/api-support-policy.md`
- Create: `docs/compatibility-shims.md`
- Modify: `README.md`
- Modify: `tests/packaging/test_public_docs.py`

**Interfaces:**

- Consumes: the public README, wheel package layout, and current forwarding modules.
- Produces: one discoverable support policy and one complete shim-group inventory.

- [ ] **Step 1: Write the failing public-doc contract test**

Add constants and a test to `tests/packaging/test_public_docs.py`:

```python
API_SUPPORT_POLICY = Path("docs/api-support-policy.md")
COMPATIBILITY_SHIMS = Path("docs/compatibility-shims.md")


def test_public_docs_define_pre_one_api_support() -> None:
    """The beta API promise and shim lifecycle are public and discoverable."""

    readme = README.read_text(encoding="utf-8")
    policy = API_SUPPORT_POLICY.read_text(encoding="utf-8")
    inventory = COMPATIBILITY_SHIMS.read_text(encoding="utf-8")

    assert "](docs/api-support-policy.md)" in readme
    assert "## Supported beta surfaces" in policy
    assert "## Intended beta Python API" in policy
    assert "`docsync.api`" in policy
    assert "Distribution is not an API promise" in policy
    assert "](compatibility-shims.md)" in policy
    assert "## Removal gate" in inventory
    assert "0.1.0b7" in inventory
    for group in (
        "Archguard forwarding",
        "Configuration facade",
        "Context extraction",
        "Hook extraction",
        "Repair-fact extraction",
        "Run-artifact extraction",
        "Wait extraction",
    ):
        assert group in inventory

    for source_path in sorted(Path("src").rglob("*.py")):
        source = source_path.read_text(encoding="utf-8")
        if not source.startswith('"""Compatibility'):
            continue
        module = ".".join(source_path.relative_to("src").with_suffix("").parts)
        assert f"`{module}`" in inventory, module
```

- [ ] **Step 2: Run the test to verify RED**

Run: `PYTHONPATH=src .venv/bin/pytest tests/packaging/test_public_docs.py::test_public_docs_define_pre_one_api_support -q`

Expected: FAIL because the policy files do not exist.

- [ ] **Step 3: Write the support policy**

Create `docs/api-support-policy.md` with these exact normative sections:

```markdown
# Pre-1.0 API Support Policy

## Supported beta surfaces

The documented `agent-maintainer`, `archguard`, and `docsync` commands,
documented `[tool.agent_maintainer]` keys, and schema-versioned documented
artifacts are supported for the current beta line.

## Intended beta Python API

`docsync.api` is the only initially named supported Python import surface.
Adding another import requires public documentation and a compatibility test.

## Internal and unstable surfaces

Distribution is not an API promise. Other modules under `agent_maintainer`,
`archguard`, `agent_context`, `agent_client_hooks`, `agent_repair_facts`,
`agent_run_artifacts`, `agent_waits`, and `docsync` remain internal unless this
policy explicitly promotes them.

## Change and deprecation window

Supported beta surfaces receive release notes, upgrade guidance, and at least
one beta release of notice before removal unless they are unsafe or unusable.
Internal surfaces may change without deprecation.

## Compatibility shims

The [compatibility-shim inventory](compatibility-shims.md) records forwarding
owners, support windows, removal conditions, and earliest removal releases.
```

- [ ] **Step 4: Write the compatibility inventory**

Create `docs/compatibility-shims.md`. Use a table with columns `Group`,
`Forwarding paths`, `Owner/replacement`, `Support window`, `Removal condition`,
and `Earliest removal`. Include every module whose top-level docstring begins
with `Compatibility`; write every forwarding path as its full dotted module in
backticks so the completeness test can match it. Group them as follows:

```text
Archguard forwarding: agent_maintainer.checks.tach_config, agent_maintainer.tach
Configuration facade: agent_maintainer.config.metadata, agent_maintainer.core.config
Context extraction: every agent_maintainer.context forwarding module
Hook extraction: agent_maintainer.hooks.adapters, merge, templates
Repair-fact extraction: agent_maintainer.ecosystems.typescript.diagnostics
Run-artifact extraction: agent_maintainer.verify artifact_manifest, git_state,
  history, pr_summary, pr_summary_support, timing
Wait extraction: agent_maintainer.wait.models
```

For every row use support window `through 0.1.0b6`, earliest removal
`0.1.0b7`, and this removal condition:

```text
No supported docs import the forwarding path; no non-compatibility production
caller imports it; compatibility tests have been replaced by replacement-path
tests; release notes announce removal.
```

End with `## Removal gate` stating that all four conditions must be proven in
one focused PR and that no shim is removed by this inventory change.

- [ ] **Step 5: Link the policy from the README and verify GREEN**

Add `- [Pre-1.0 API support](docs/api-support-policy.md)` under `Further
Reading`, adjacent to Support and Contributing.

Run: `PYTHONPATH=src .venv/bin/pytest tests/packaging/test_public_docs.py::test_public_docs_define_pre_one_api_support tests/docs/test_markdown_links.py -q`

Expected: PASS and all repository-local Markdown links resolve.

- [ ] **Step 6: Commit the policy slice**

```bash
git add -- README.md docs/api-support-policy.md docs/compatibility-shims.md tests/packaging/test_public_docs.py
git commit -m "docs: define pre-1.0 api support"
```

### Task 3: Reclassify the top-level product surface

**Files:**

- Modify: `src/agent_maintainer/cli.py`
- Modify: `tests/packaging/test_script_helpers.py`
- Modify: `docs/tool-map.md`

**Interfaces:**

- Consumes: `agent_maintainer.cli.USAGE` and the existing command registry.
- Produces: five user-facing categories without changing dispatch behavior.

- [ ] **Step 1: Write the failing help-classification assertions**

Replace the old `Core commands` and `Agent repair commands` assertions with:

```python
    for heading in (
        "Stable workflows:\n",
        "Repair and inspection:\n",
        "Optional local intelligence:\n",
        "Experimental integrations:\n",
        "Operations:\n",
    ):
        assert heading in result.stdout
    assert "wait            Quiet polling is stable; terminal rewake is experimental." in result.stdout
    assert "Core commands:\n" not in result.stdout
```

- [ ] **Step 2: Run the test to verify RED**

Run: `PYTHONPATH=src .venv/bin/pytest tests/packaging/test_script_helpers.py::test_maintainer_package_entrypoint_help -q`

Expected: FAIL because the old headings remain.

- [ ] **Step 3: Replace only the `USAGE` grouping**

Keep every command and example, but group commands exactly as follows:

```text
Stable workflows: doctor, guidance, init, install, verify, wait
Repair and inspection: assess, context, ratchet, repair-plan, test-intel
Optional local intelligence: attention, events, report, scoring
Experimental integrations: mcp
Operations: bootstrap, change-plan, hooks
```

Use the wait description `Quiet polling is stable; terminal rewake is
experimental.` Update the top-level command table in `docs/tool-map.md` with
the same categories and stability note. Do not move command handlers or change
exit behavior.

- [ ] **Step 4: Verify GREEN**

Run: `PYTHONPATH=src .venv/bin/pytest tests/packaging/test_script_helpers.py::test_maintainer_package_entrypoint_help tests/packaging/test_public_docs.py -q`

Expected: PASS with the new categories and unchanged console entry point.

- [ ] **Step 5: Commit the classification slice**

```bash
git add -- src/agent_maintainer/cli.py tests/packaging/test_script_helpers.py docs/tool-map.md
git commit -m "docs: classify the command surface"
```

### Task 4: Correct the active roadmap and verify the governance chunk

**Files:**

- Modify: `docs/ROADMAP.md`
- Modify: `tests/docs/test_roadmap_docs.py`

**Interfaces:**

- Consumes: merged strict-Pyright state and Tasks 1-3.
- Produces: an active roadmap with completed governance items and still-open implementation work.

- [ ] **Step 1: Write the failing roadmap-truth test**

Add:

```python
def test_active_roadmap_reports_current_strict_and_api_state() -> None:
    """The active tracker does not revive completed strict-typing debt."""

    text = Path("docs/ROADMAP.md").read_text(encoding="utf-8")

    assert "`1,265` diagnostics" not in text
    assert "Strict Pyright cutover complete" in text
    assert "[x] Reclassify top-level help" in text
    assert "[x] Add `agent_waits`" in text
    assert "[x] Publish a pre-1.0 API-support policy" in text
    assert "[ ] Guarantee changed, failed, exact-fact" in text
```

- [ ] **Step 2: Run the test to verify RED**

Run: `PYTHONPATH=src .venv/bin/pytest tests/docs/test_roadmap_docs.py::test_active_roadmap_reports_current_strict_and_api_state -q`

Expected: FAIL on the stale diagnostic baseline.

- [ ] **Step 3: Update only completed roadmap state**

Rename `Active: External Proof And Strict-Typing Debt` to `Active: External
Proof And Architecture Hardening`. Replace the diagnostic targets with a
checked `Strict Pyright cutover complete` item naming zero diagnostics and the
retired baseline. Check the help classification, `agent_waits`, and API policy
items. Leave both attention items, external proof, Phase 176 real-turn smoke,
and b6 publication unchecked.

- [ ] **Step 4: Run focused and broad checks**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest \
  tests/architecture/test_internal_package_boundaries.py \
  tests/docs/test_roadmap_docs.py \
  tests/docs/test_markdown_links.py \
  tests/packaging/test_public_docs.py \
  tests/packaging/test_script_helpers.py -q
.venv/bin/tach check --exact
```

Expected: all tests PASS and Tach reports no dependency violations.

- [ ] **Step 5: Commit the roadmap and run the chunk gate**

```bash
git add -- docs/ROADMAP.md tests/docs/test_roadmap_docs.py
git commit -m "docs: reconcile the active architecture roadmap"
just v
```

Expected: the full profile reaches a terminal PASS. Review its manifest if the
command returns a background wait capsule.
