# Agent Maintainer Core

- Python `src/`-layout developer tool for maintainability checks, bounded diagnostics, repair guidance, onboarding/scaffolding, hooks, waits, and release evidence.
- `src/agent_maintainer` owns CLI/orchestration; `src/archguard` owns architecture tools; `src/docsync` is an extractable sibling behind `docsync.api` and must not import the other two.
- `src/agent_context`, `agent_client_hooks`, `agent_waits`, `agent_repair_facts`, and `agent_run_artifacts` are narrow Tach-owned shared packages; `tests/` mirrors product domains.
- Architecture source of truth: root `tach.toml` plus colocated `tach.domain.toml` files. Root modules are forbidden and dependency declarations are exact. Architecture-policy edits require an ADR under `docs/architecture/decisions/`.
- Policy lives in `[tool.agent_maintainer]` and `.docsync/trace.yml`; never hand-edit generated guidance, `.docsync/out/`, or `.verify-logs/`.
- Runtime is Python 3.11–3.14 with setuptools/PyYAML; Node 22+ is development-only, and declarations live in `pyproject.toml` plus `config/dev-{dependencies,lock}.txt`.
- Commands: `just bootstrap/doctor`, focused `.venv/bin/pytest`, then `just vf/vp/v/vc/vs/vm` or `just release-check` as scope requires.
- Finish by reviewing status/diff/secrets, validating generated/DocSync/Tach contracts when touched, and staging explicit paths for a Conventional Commit; use `rg`, Serena JetBrains, and headless `serena_lsp` at their documented boundaries.
