# 2026-06-30: P0 Reliability Boundary Modules

## Decision

Add explicit Tach module assignments for the new reliability helpers:

- `agent_maintainer.config.validation`
- `agent_maintainer.verify.git_refs`

Allow `doctor.support.policy` to depend on config loading and validation so `doctor` can report ignored `[tool.agent_maintainer]` keys before users trust a typoed policy.

## Why

The P0 review identified four reliability risks: unbounded verifier subprocess output, silent config-key drift, comma-splitting arbitrary tool arguments, and unvalidated Git refs. Two of those need small pure helper modules that should be visible in the architecture contract instead of hidden inside orchestration code.

## Alternatives Considered

- Put unknown-key checks directly in `config.loader`: rejected because loading must remain tolerant enough for starter config and partial diagnostics. Doctor policy checks are the right place to turn tolerance into user-facing warnings.
- Put Git-ref validation directly in `verify.run_steps`: rejected because it would mix Git subprocess details into profile orchestration and make the validation harder to unit test.
- Relax Tach root coverage for the new files: rejected because this repo intentionally dogfoods explicit module ownership.

## Still Forbidden

Config validation must not import doctor, verifier, hooks, or catalogs. Git-ref validation must stay a pure verifier support helper and must not import check catalogs, config loading, or CLI modules. Doctor policy may read config for diagnostics but should not mutate config or run verifier checks.
