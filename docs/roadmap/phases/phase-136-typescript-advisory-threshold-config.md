# Phase 136: TypeScript Advisory Threshold Config

Status: complete

## Goal

Move TypeScript/JavaScript reviewability advisory thresholds from hard-coded
constants into beta config fields while keeping the behavior advisory-only and
non-blocking.

## Scope

- Add `[tool.agent_maintainer]` fields for TypeScript source-heavy and broad
  suppression advisory thresholds.
- Preserve current default advisory behavior.
- Keep thresholds scoped to `assess reviewability`; do not add blocking
  verifier gates.
- Update TypeScript maturation docs so documented names are active advisory
  config, not only candidates.
- Add focused tests for defaults and overrides.

## Non-goals

- Do not make TypeScript reviewability blocking.
- Do not add package-manager autodetection.
- Do not add another ecosystem.
- Do not change Python reviewability gates.

## Acceptance Criteria

- Defaults preserve existing source-heavy and broad-suppression advisory output.
- Config overrides affect TypeScript advisory findings deterministically.
- Config metadata and environment drift tests cover the new fields.
- Public docs accurately describe the advisory-only status.

## Verification

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/assess/test_reviewability_assessment.py tests/assess/test_typescript_reviewability_fixtures.py tests/config/test_config_loading.py tests/config/test_config_metadata.py -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile precommit
```
