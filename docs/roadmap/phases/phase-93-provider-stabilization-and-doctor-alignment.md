# Phase 93: Provider Stabilization And Doctor Alignment

Status: planned.

## Goal

Harden the early post-provider-refactor seam before adding more languages.
Agent Maintainer should remain honest about current maturity: Python is the
core/reference provider, TypeScript and Go are experimental configured-command
providers, and the public plugin API remains deferred.

## Scope

- Add a small internal registry for built-in provider metadata.
- Keep provider metadata private/internal; do not expose external plugin loading.
- Make provider maturity, docs, enabled config fields, and capability lists
  explicit.
- Align doctor output with provider state, especially experimental TypeScript
  and Go command configuration.
- Add tool capability hints for common Node and Go executables so missing-tool
  messages do not default to Python-package advice.
- Clarify that currently scheduled reviewability checks are Python-backed
  policy checks until multi-ecosystem policy adapters mature.
- Add tests for provider registry metadata, Go doctor warnings, provider status,
  and non-Python capability hints.

## Non-Goals

- No new language providers.
- No public provider plugin API.
- No verifier behavior change for existing Python checks.
- No config migration or command semantic change.
- No workspace scheduling, per-workspace ratchets, or coverage routing.
- No attempt to make TypeScript or Go parity providers.

## Acceptance Criteria

- Built-in provider metadata exists for Python, TypeScript, and Go.
- Catalog construction uses the internal built-in provider registry while
  preserving existing check order and behavior.
- `doctor` reports a compact provider status row.
- `doctor` warns when Go is enabled with no configured commands, matching the
  existing TypeScript behavior.
- Missing Node and Go tool hints point to ecosystem-appropriate installation
  advice, not Agent Maintainer's Python dev lock.
- Docs and comments do not overclaim that Python-backed reviewability checks are
  already language-neutral.
- Focused tests and standard lightweight checks pass.

## Verification

Run focused checks first:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest \
  tests/catalogs/test_provider_registry.py \
  tests/doctor/test_typescript_doctor.py \
  tests/doctor/test_go_doctor.py \
  tests/core/test_tool_capabilities.py \
  tests/catalogs/test_global_catalog_characterization.py -q
```

Then run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer change-plan check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/tach check --exact
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile precommit --base-ref HEAD --staged
```

## Follow-Up

After this phase, the next design phase should address multi-ecosystem
reviewability policy deliberately. Do not add another language until provider
status, doctor behavior, and capability hints are stable.
