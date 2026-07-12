# Beta Compatibility Policy Override Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove cross-version compatibility and deprecation commitments from the pre-1.0 policy while retaining a tested map for safely deleting active forwarding modules.

**Architecture:** Documentation describes only exact-installed-version expectations. The shim inventory becomes a cleanup map: compatibility never blocks deletion, but current internal callers, docs, and tests migrate in the same change so the repository remains working.

**Tech Stack:** Markdown and pytest public-document contract tests.

## Global Constraints

- No command, configuration, format, or Python import has a cross-version compatibility guarantee before 1.0.
- `docsync.api` is the current intended DocSync entry point, not a frozen signature.
- No deprecation window, grace beta, support window, or earliest-removal release is required.
- Compatibility is not a reason to retain a forwarding module.
- Do not blindly delete a forwarding module while current repository callers still depend on it; migrate those callers and delete it in one tested change.
- This task changes policy and inventory semantics only; source-shim deletion is separate evidence-led work.

---

### Task 1: Replace compatibility promises with immediate beta cleanup rules

**Files:**

- Modify: `tests/packaging/test_public_docs.py`
- Modify: `docs/api-support-policy.md`
- Modify: `docs/compatibility-shims.md`

**Interfaces:**

- Consumes: the exhaustive shim-group inventory and its executable source scan.
- Produces: exact-version beta expectations and a no-grace tested deletion rule.

- [ ] **Step 1: Rewrite the public-doc test first**

Replace the old support-window assertions with:

```python
assert "## Current-version documented surfaces" in policy
assert "## Current Python entry points" in policy
assert "no cross-version compatibility guarantee" in policy
assert "may change or be removed without a deprecation window" in policy
assert "`docsync.api`" in policy
assert "not a frozen signature" in policy
assert "## Deletion rule" in inventory
assert "Compatibility is not a reason to retain a shim" in inventory
assert "same tested change" in inventory
assert "0.1.0b7" not in inventory
assert "Support window" not in inventory
assert "Earliest removal" not in inventory
```

Keep the existing group assertions and executable scan that requires every
`Compatibility` module to appear as a full dotted path.

- [ ] **Step 2: Run the test to verify RED**

Run: `PYTHONPATH=src .venv/bin/pytest tests/packaging/test_public_docs.py::test_public_docs_define_pre_one_api_support -q`

Expected: FAIL because the current documents promise a beta support line and
an earliest removal release.

- [ ] **Step 3: Rewrite the policy semantics**

Use these normative sections in `docs/api-support-policy.md`:

```markdown
## Current-version documented surfaces

Documented commands, configuration, and schema-versioned artifacts are expected
to work for the exact installed beta version. There is no cross-version
compatibility guarantee before 1.0.

## Current Python entry points

`docsync.api` is the intended DocSync integration boundary for current code,
not a frozen signature. It may change or be removed without a deprecation
window before 1.0.

## Internal and unstable surfaces

Distribution is not an API promise. Internal packages and modules may change or
be removed without compatibility shims.

## Change communication

Release notes and upgrade guidance should explain material user-facing changes
when useful, but communication is not a compatibility gate.

## Forwarding-module cleanup

The compatibility-shim cleanup inventory identifies canonical replacements.
Compatibility is not a reason to retain a shim.
```

Link `compatibility-shim cleanup inventory` to the sibling path
`compatibility-shims.md` in the actual document.

- [ ] **Step 4: Convert the inventory into a cleanup map**

Keep the exhaustive groups and full dotted paths. Replace the table columns
with `Group`, `Forwarding paths`, `Owner/replacement`, and `Current deletion
rule`. Every row uses:

```text
Migrate current repository callers, docs, and tests to the canonical owner,
then delete the forwarding module in the same tested change.
```

End with:

```markdown
## Deletion rule

Compatibility is not a reason to retain a shim during beta. A forwarding
module can be deleted immediately when its current repository callers, docs,
and tests migrate to the canonical owner in the same tested change. No support
window, deprecation release, or earliest-removal version applies.
```

- [ ] **Step 5: Verify GREEN and commit**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest \
  tests/packaging/test_public_docs.py::test_public_docs_define_pre_one_api_support \
  tests/docs/test_markdown_links.py -q
```

Expected: 2 tests PASS with complete shim enumeration and valid local links.

```bash
git add -- tests/packaging/test_public_docs.py docs/api-support-policy.md docs/compatibility-shims.md
git commit -m "docs: drop beta compatibility promises"
```
