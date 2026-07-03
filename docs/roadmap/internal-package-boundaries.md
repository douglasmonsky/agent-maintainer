# Internal Package Boundary Refactor Roadmap

Agent Maintainer should remain one PyPI distribution for now while extracting
reusable primitives into clear internal packages. The refactor must preserve
current user behavior, CLI commands, generated artifacts, hook semantics, and
diagnostic output while improving package ownership and dependency direction.

The exact implementation handoff is preserved in
[`internal-package-boundaries-implementation-guide.txt`](internal-package-boundaries-implementation-guide.txt).
Use that file as the detailed task source before moving code.

## Target Shape

```text
src/
  agent_maintainer/     # product orchestrator, policies, CLI, profiles
  agent_repair_facts/   # normalized repair facts from tool output
  agent_context/        # bounded context, context packs, safe expansion
  agent_run_artifacts/  # verifier artifact schemas and renderers
  agent_client_hooks/   # hook config/templates/adapters
  docsync/              # existing docs evidence and claim freshness package
  archguard/            # architecture/config validation package
```

Current-state note: DocSync now owns the docs/evidence responsibility that the
original handoff called `docs_evidence`. Do not create a second `docs_evidence`
package during this refactor unless a future ADR explicitly reopens that
boundary.

Current-state note: `agent_context` extraction is split. Phase 112 moved context
models, budget/formatting helpers, failure-manifest readers, estimates, and safe
file/log/diff readers. Context-pack builder/rendering/compression, ratchet
context, and Agent Maintainer context CLI remain product-owned until their Agent
Maintainer dependencies are isolated.

Current-state note: `agent_run_artifacts` extraction is split. Phase 113 moved
manifest payload helpers, run history helpers, Git-state helpers, PR summary
rendering helpers, and timing metadata helpers. Product-owned artifact write
orchestration remains under `agent_maintainer.verify.artifacts` until config and
check-result adapters are fully isolated.

## Hard Invariants

- Keep `agent-maintainer` as the only public distribution in this pass.
- Do not change user-facing CLI behavior while moving ownership.
- Do not change context pack JSON shape except through an explicit migration.
- Do not make new packages import `agent_maintainer`.
- Keep compatibility shims for moved internal import paths during the first
  full refactor pass.
- Update Tach ownership and add ADRs before relying on new boundaries.
- Update `[tool.agent_maintainer]` source, package, coverage, structure,
  vulture, Semgrep, and cohesive-change paths as packages are introduced.
- Regenerate `AGENTS.agent-maintainer.md` after config path changes.
- Run characterization and artifact checks before moving each major package.

## Phase Sequence

| Phase | Goal | Exit Criteria |
| --- | --- | --- |
| 0 | Establish baseline refactor guardrails | Current guidance, doctor, fast/precommit verification, pytest, and Tach baseline captured; representative artifacts saved for comparison. |
| 1 | Define package ownership and dependency direction | ADR documents package responsibilities and allowed dependencies; DocSync is the docs/evidence package. |
| 2 | Update global config expectations | New package roots are represented in config paths, Semgrep paths, mutation settings, and generated guidance when introduced. |
| 3 | Update Tach root ownership and domain contracts | Root/domain Tach files explicitly own every new package; `tach check --exact` passes. |
| 4 | Extract `agent_repair_facts` | Repair-fact payloads/parsers/registry move behind new package with compatibility shims and direct tests. |
| 5 | Extract `agent_context` | Context budget, reading, compression, and pack modules move behind new package while `python -m agent_maintainer context ...` stays stable. |
| 6 | Extract `agent_run_artifacts` | Manifest, run history, `LAST_FAILURE.md`, PR summary, timing, and git-state helpers move behind artifact package. |
| 7 | Extract `agent_client_hooks` | Hook config/template generation moves behind client-hook package; runtime verification stays in `agent_maintainer`. |
| 8 | Stabilize DocSync boundary | Existing DocSync package remains extractable; future evidence work extends DocSync instead of creating `docs_evidence`. |
| 9 | Refactor Agent Maintainer orchestrator | Product modules import the new primitives while preserving existing orchestration behavior. |
| 10 | Update tests import paths | New packages have direct tests; old import paths remain covered by compatibility tests. |
| 11 | Add architecture regression tests | Tests enforce that extracted packages do not import `agent_maintainer` and only use allowed package dependencies. |
| 12 | Update docs | README and product docs explain internal packages without changing public install story. |
| 13 | Improve token-bleed behavior during refactor | Context pack output modes, hook pointer wording, run-scoped hook packs, and surgical expansion commands remain compact. |
| 14 | Update packaging and scripts | Wheel/sdist include all internal packages; clean wheel import smoke passes. |
| 15 | Decide shim cleanup strategy | Compatibility shims are either retained intentionally or removed with tests/docs updated. |
| 16 | Run full regression matrix | Fast, full, CI, security, manual, Tach, Pyright, pytest, artifact, hook, and wheel checks pass. |
| 17 | Audit specific regression risks | Source-root scanning, coverage, Tach ownership, context shape, hook output, old imports, and wheel contents are explicitly checked. |
| 18 | Final acceptance | New packages exist, boundaries hold, behavior remains stable, and full verification passes. |

## Caution Points

- Start each moving phase from a clean branch. Do not combine this refactor with
  unrelated DocSync or roadmap cleanup work.
- Move one package boundary at a time. Do not extract context, artifacts, and
  hooks in the same PR.
- Preserve old import paths through shims until all tests and docs are updated.
- Compare context pack JSON, `LAST_FAILURE.md`, `manifest.json`, PR summary, and
  hook output before and after each extraction.
- Treat Tach failures as design feedback. Do not broaden module buckets just to
  pass exact checks.

## First Action

When this refactor starts, complete Phase 0 only:

1. Start from clean `main`.
2. Run the baseline checks listed in the exact implementation guide.
3. Save representative pre-refactor artifacts outside the repo.
4. Add or update the ownership ADR.
5. Stop before moving code.
