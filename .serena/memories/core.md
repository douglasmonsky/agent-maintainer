# Agent Maintainer Core

- Python `src/`-layout developer tool for maintainability checks, bounded diagnostics, repair guidance, onboarding/scaffolding, hooks, waits, and release evidence.
- Main package map:
  - `src/agent_maintainer`: CLI and orchestration; entrypoint is `agent_maintainer.cli:console_main`.
  - `src/archguard`: architecture impact and decision-note tooling; entrypoint is `archguard.cli:console_main`.
  - `src/docsync`: extractable sibling package with public `docsync.api` boundary; must not import `agent_maintainer` or `archguard`; entrypoint is `docsync.cli:console_main`.
  - `src/agent_context`, `agent_client_hooks`, `agent_waits`, `agent_repair_facts`, and `agent_run_artifacts`: narrow shared packages with explicit Tach ownership.
  - `tests/` mirrors product domains; release and packaging checks live under `tests/release` and `tests/packaging`.
- Architecture source of truth: root `tach.toml` plus colocated `tach.domain.toml` files. Root modules are forbidden and dependency declarations are exact. Architecture-policy edits require an ADR under `docs/architecture/decisions/`.
- Agent Maintainer policy source of truth: `[tool.agent_maintainer]` in `pyproject.toml`; `AGENTS.agent-maintainer.md` is generated and must not be hand-edited.
- DocSync source truth is `.docsync/trace.yml`; `.docsync/out/` and `.verify-logs/` are generated artifacts.
- Runtime: Python 3.11–3.14, setuptools `src/` layout, PyYAML, and the `agent-maintainer`, `archguard`, and `docsync` console scripts; Node 22+ is development-only.
- Local orchestration uses `just`; package/tool declarations live in `pyproject.toml`, `config/dev-dependencies.txt`, and `config/dev-lock.txt`.
- Read working commands in `mem:suggested_commands`, code rules in `mem:conventions`, and finish gates in `mem:task_completion`.
