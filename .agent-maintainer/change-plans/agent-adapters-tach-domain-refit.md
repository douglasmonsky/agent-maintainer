+++
id = "agent-adapters-tach-domain-refit"
kind = "refactor"
status = "active"
base_ref = "origin/main"
expires = 2026-07-13
allowed_paths = [".agent-maintainer/change-plans/**", "src/**", "tests/**", "docs/**", "examples/**", "tach.toml", "pyproject.toml"]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 120
max_changed_lines = 12000
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++
# Cohesive Change Plan: agent-adapters-tach-domain-refit

## Why this change intentionally large

This branch intentionally combines two architecture-maintenance refactors. The
hook installer is gaining an explicit agent-client adapter boundary so Codex and
Claude Code support do not keep accumulating conditional path logic in the hook
manager. The Tach contract is also being split into package-level
`tach.domain.toml` files so architecture ownership stays close to the code it
describes instead of growing a broad root compliance bucket.

## Why this should not be split smaller

The adapter work changes the same ownership model that Tach now documents. A
Tach-only split before the adapter boundary would freeze a short-lived module
shape, and an adapter-only change would leave the root `tach.toml` with stale
catchall buckets. The work is still limited to hook architecture, Tach contract
layout, architecture-check validation, and the tests/docs proving those changes.

## What allowed to change

Allowed changes are:

- `src/agent_maintainer/hooks/**` adapter and manager refactor.
- `src/archguard/tach_config.py` domain-file validation support.
- `src/archguard/tach_config_domains.py` domain-file loading and expansion.
- `src/archguard/tach_config_sources.py` source-module discovery helpers.
- `tach.toml` and `src/**/tach.domain.toml` architecture contracts.
- Focused tests for hook adapters, Tach config validation, doctor fixtures, and
  examples that must satisfy the stricter contract.
- Documentation and ADR updates explaining the new adapter boundary and Tach
  domain-contract policy.

## What must not change

The verifier semantics, configured thresholds, package identity, publishing
workflow, scanner policy, generated hook runtime behavior, and public command
surface must not change in this plan except where tests require path or wording
updates for the adapter/Tach refactor. No new scanner categories or unrelated
feature work belong in this branch.

## Verification plan

Run focused tests first:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest \
  tests/hooks/test_hook_manager.py \
  tests/archguard/test_tach_config.py \
  tests/doctor/test_doctor_optional_gates.py \
  tests/packaging/test_example_projects.py -q
```

Then run the architecture and repository gates:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/tach check --exact
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m archguard tach-config --strict-root-module
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile precommit
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile full
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile ci --base-ref origin/main --compare-branch origin/main
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile security
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile manual
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer guidance --check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer doctor --strict
```

## Rollback plan

Revert the adapter commit and the Tach domain-contract commit together if the
PR exposes a release-blocking regression. The previous root `tach.toml` shape
and hook manager implementation can be restored from `origin/main`; no data
migration or external service state is involved.

## Follow-up ratchet work

No ratchet debt is intentionally introduced. If verification exposes unrelated
ratchet targets, handle them in separate follow-up PRs rather than expanding
this plan.
