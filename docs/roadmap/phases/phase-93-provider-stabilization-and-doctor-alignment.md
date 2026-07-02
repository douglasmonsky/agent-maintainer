# Phase 93: Provider Stabilization And Doctor Alignment

## Status

Complete.

## Goal

Harden the early post-provider-refactor seam before adding more languages.
Agent Maintainer should remain honest about current maturity: Python is the
core/reference provider, TypeScript/JavaScript is experimental, and the public
plugin API remains deferred.

## Scope

- Add small internal registry metadata for built-in providers.
- Keep provider metadata private/internal; do not expose external plugin
  loading.
- Make provider maturity, docs, enabled config fields, and capability lists
  explicit.
- Align doctor output with provider state, especially experimental
  TypeScript/JavaScript command configuration.
- Add tool capability hints so common Node executables do not default to
  Python-package advice.
- Clarify scheduled reviewability checks as Python-backed policy checks until
  multi-ecosystem policy adapters mature.
- Add tests for provider registry metadata, doctor warnings, provider status,
  and non-Python capability hints.

## Non-Goals

- No new language providers.
- No public provider plugin API.
- No verifier behavior change for existing Python checks.
- No config migration or command semantic change.
- No workspace scheduling, per-workspace ratchets, or coverage routing.
- No attempt to make TypeScript/JavaScript a parity provider.

## Acceptance Criteria

- Built-in provider metadata exists for Python and TypeScript/JavaScript.
- Catalog construction uses the internal built-in provider registry while
  preserving existing check order behavior.
- `doctor` reports a compact provider status row.
- `doctor` warns when TypeScript/JavaScript is enabled with no configured
  commands.
- Missing Node tool hints point to ecosystem-appropriate installation advice,
  not Agent Maintainer's Python dev lock.
- Docs and comments do not overclaim that Python-backed reviewability checks are
  already language-neutral.
- Focused tests and standard lightweight checks pass.

## Verification

Run focused checks first:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest \
  tests/catalogs/test_provider_registry.py \
  tests/doctor/test_typescript_doctor.py \
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

The next design phase should address multi-ecosystem reviewability policy
deliberately. Do not add another language until provider status, doctor
behavior, and capability hints are stable.
