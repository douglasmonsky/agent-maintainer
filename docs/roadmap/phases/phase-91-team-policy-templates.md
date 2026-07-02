# Phase 91: Team Policy Templates

Status: complete in PR.

## Goal

Add team-oriented initializer presets that make existing policy shapes easier
to choose during onboarding without adding SaaS, dashboards, or new scanners.

## Scope

- Add team presets:
  - `team-small-python-lib`
  - `team-legacy-service`
  - `team-agent-heavy`
  - `team-security-sensitive`
- Keep templates deterministic and track-independent.
- Document template intent and mapped policy behavior.
- Update initializer tests.

## Non-Goals

- No SaaS or dashboard behavior.
- No organization account integration.
- No new policy gates or scanners.
- No automatic repository inference.
- No generated starter file set changes.

## Acceptance Criteria

- `agent-maintainer init --preset <team-template>` accepts every team preset.
- Generated starter config records the requested team preset name.
- Team templates are documented.
- Existing presets keep their current behavior.
- Precommit passes.

## Verification

Run:

```bash
python -m pytest tests/packaging/test_initializer.py -q
python -m agent_maintainer verify --profile precommit
```
