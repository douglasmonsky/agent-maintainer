# Phase 74: Review-Driven Stabilization Metadata, Schedules, and Output Contracts

## PR Title

```text
feat: stabilize config metadata and verification contracts
```

## Scope

Address the static review's release-stabilization concerns before adding new
scanner categories or case-study work. The priority is reducing drift across
configuration, CLI, docs, starter files, and verifier output while preserving
the existing public command surface.

## Requirements

- Add a config-field metadata layer that records each `MaintainerConfig` field's
  TOML key, environment variable coverage, CLI override status, docs label, and
  stability level.
- Add tests that fail when `MaintainerConfig` fields drift from metadata or
  environment override mappings.
- Normalize optional-skip status terminology so success output and artifacts can
  distinguish disabled, missing optional, not applicable, unsafe config, and
  required-skip states.
- Decide and document architecture-backend asymmetry: Tach gets decision-note
  enforcement; Import Linter support remains simpler unless equivalent policy
  is implemented.
- Add scheduled security/manual workflow coverage, or document why the existing
  workflow matrix is the only supported automated cadence.
- Add end-to-end scaffold adoption tests for `core`, `agent`, and `hardening`
  tracks, including generated workflow/install expectations.
- Align hardening-track starter workflow behavior with generated Node-backed
  tooling, either by installing Node dependencies or by documenting local-only
  hardening metadata clearly.
- Replace truthiness-based CLI threshold overrides with `is not None` semantics
  so intentional zero values are not silently ignored.
- Expand structured repair summaries for high-value artifacts beyond Ruff,
  Pyright, and Bandit, starting with pytest/JUnit, coverage JSON, Semgrep, OSV,
  Gitleaks, and pip-audit where artifacts exist.
- Add tests for Gitleaks secret-scan range command construction and document the
  intended commit range.
- Preserve context-pack expansion commands under tight budgets where practical.
- Keep changes split into focused PRs; do not add new scanner categories in this
  phase.

## Acceptance Criteria

- Metadata tests cover every `MaintainerConfig` field and every declared
  `AGENT_MAINTAINER_*` environment override.
- At least one public doc explains config metadata/drift expectations and links
  to setup/adoption docs.
- Optional skip statuses are more precise in typed data and output remains
  compact.
- Scheduled or explicitly documented manual/security cadence exists.
- Starter adoption tests cover `core`, `agent`, and `hardening` tracks.
- CLI zero-value override behavior is tested for at least change-budget and
  file-length checks.
- Structured summary tests cover at least one additional non-Ruff/Pyright/Bandit
  artifact class.
- Context budget tests prove expansion commands survive small-but-valid budgets.
- Final checks pass: `guidance --check`, `change-plan check`, `tach check
  --exact`, `verify --profile precommit`, `full`, `ci`, `security`, and
  `manual`.

## Progress

- [x] Added config metadata inventory and drift tests for schema fields, env
  maps, CLI override fields, diagnostics TOML aliases, and docs labels.
- [x] Normalize optional-skip status terminology.
- [x] Add scheduled or documented manual/security cadence.
- [x] Expand starter adoption tests across tracks.
- [x] Fix truthiness-based CLI threshold overrides.
- [ ] Expand structured repair summaries.
- [x] Add Gitleaks range command tests.
- [x] Preserve context-pack expansion commands under tight budgets.

## Out Of Scope

- New scanner integrations.
- New public profile names.
- Headroom integration.
- Case-study repositories.
- Monorepo support.
