# Phase 186: C/C++ Provider Contract And Roadmap

Status: complete

## Goal

Define the durable architecture, sequencing, safety boundary, and qualification
bar for a built-in experimental C/C++ CMake provider before runtime code lands.

## Scope

- Record the approved CMake-first provider design.
- Add the Phase 186-191 roadmap and split phase cards.
- Accept the internal built-in provider boundary decision.
- Record the approved experiment without claiming current runtime support.
- Produce a decision-complete Phase 187 implementation plan.
- Preserve the existing active roadmap's bounded recovery structure.

## Principal Files

- `docs/superpowers/specs/2026-07-19-cpp-cmake-experimental-provider-design.md`
- `docs/roadmap/cpp-cmake-experimental-provider-roadmap.md`
- `docs/roadmap/phases/phase-186-cpp-provider-contract-and-roadmap.md`
- `docs/roadmap/phases/phase-187-cpp-classification-config-registry-doctor.md`
- `docs/roadmap/phases/phase-188-cpp-explicit-commands-and-bounded-artifacts.md`
- `docs/roadmap/phases/phase-189-cpp-static-analysis-facts.md`
- `docs/roadmap/phases/phase-190-cpp-test-and-coverage-facts.md`
- `docs/roadmap/phases/phase-191-cpp-cross-platform-and-external-proof.md`
- `docs/architecture/decisions/2026-07-19-cpp-cmake-experimental-provider-boundary.md`
- `docs/superpowers/plans/2026-07-19-cpp-cmake-provider-foundation.md`

## Non-Goals

- No runtime provider, configuration, classifier, command, parser, or doctor
  behavior.
- No dependency or workflow changes.
- No claim that C/C++ is a current provider.
- No provider promotion or blocking gate.

## Acceptance Criteria

- The roadmap states Linux/GCC, macOS/Clang, and Windows/MSVC requirements.
- Repository-owned explicit commands remain authoritative.
- The supported artifact contracts and deferred work are exact.
- Six independently reviewable phases have bounded acceptance bars.
- Phase 187 can execute from its implementation plan without reopening design.
- Roadmap structure, links, line limits, and Markdown validation pass.

## Verification

Run:

```bash
.venv/bin/pytest -q tests/docs/test_roadmap_docs.py
markdownlint-cli2 "**/*.md"
git diff --check
```

## Phase 187 Handoff

Add only the configuration, classification, registry, suppression, doctor, and
public-documentation foundation. Do not execute C/C++ commands or parse reports.
