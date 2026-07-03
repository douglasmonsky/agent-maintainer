# Phase 141: Provider-Neutral File Baseline Controls

Status: complete

## Goal

Design and implement provider-neutral file baseline controls so Agent
Maintainer can apply simple file facts such as length, nonblank lines, changed
file counts, and changed line counts across explicit file groups without
forcing every ecosystem through Python-specific checks.

## Scope

- Add the detailed roadmap/spec in
  `docs/roadmap/provider-neutral-file-baselines.md`.
- Define the first config shape for filetype/path watched groups.
- Add advisory `assess file-baselines` text and JSON output.
- Dogfood conservative docs/config/tests groups in this repository.
- Preserve current Python blocking file-length and change-budget behavior.
- Keep non-Python groups advisory until fixture and repo evidence proves low
  noise.
- Document that Tach remains Python module/import boundary enforcement, not the
  generic cross-language baseline mechanism.
- Later implementation should add tests for `.tsx`, `.md`, `.toml`, `.yaml`,
  generated, and ignored files.

## Non-goals

- No TypeScript or React blocking gate by default.
- No Tach replacement.
- No cross-language import graph in this phase.
- No package-manager or framework autodetection.
- No provider promotion.
- No change to current Python check names or exit behavior.

## Acceptance Criteria

- Roadmap/spec names which controls can be generic and which must stay
  provider-owned.
- Proposed config supports explicit include/exclude glob groups.
- `assess file-baselines` reads configured groups and emits compact text/JSON.
- This repository dogfoods advisory docs/config/tests groups without findings.
- Tach's language boundary is documented clearly.
- Roadmap index links to this phase.

## Verification

Run:

```bash
git diff --check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile fast
```
