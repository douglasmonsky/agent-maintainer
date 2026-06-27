# Changelog

## 0.1.0b1 - 2026-06-27

Initial beta release of Agent Maintainer.

### Added

- Package-first CLI: `agent-maintainer` and `python -m agent_maintainer`.
- `init` tracks: `core`, `agent`, and `hardening`.
- Low-noise verification profiles: `fast`, `precommit`, `full`, `ci`,
  `security`, and `manual`.
- Change budget, file length, suppression budget, structure cohesion, type
  checking, coverage, architecture, dependency hygiene, security, docs/config
  hygiene, and diagnostic artifact support.
- Generated agent guidance via `AGENTS.agent-maintainer.md`.
- Release-only packaging checks for dependency resolution, wheel/sdist builds,
  artifact metadata, and console-script smoke tests.

### Beta Notes

- Starter files and defaults may change before 1.0.
- Public config is intended to stabilize through beta feedback.
