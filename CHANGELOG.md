# Changelog

## Unreleased

## 0.1.0b2 - 2026-06-27

Second beta release of Agent Maintainer.

### Added In 0.1.0b2

- Archguard CLI: `archguard` and `python -m archguard` for architecture policy
  governance.
- Architecture decision-note enforcement when Tach policy files change.
- Python compatibility CI matrix for Python 3.11, 3.12, 3.13, and 3.14.
- GitHub release artifact attachment for built wheel and sdist distributions.
- Fresh-strict and legacy-ratchet example projects.
- First-run onboarding walkthrough focused on diagnostics and repair loops.

### Changed In 0.1.0b2

- Agent Maintainer now consumes Archguard for Tach configuration validation.
- The real PyPI publishing environment requires manual reviewer approval.

### Beta Notes For 0.1.0b2

- Known limitation: Semgrep is excluded from `manual` and `all` extras on Python
  3.13+ while upstream dependency resolution is unstable there.

## 0.1.0b1 - 2026-06-27

Initial beta release of Agent Maintainer.

### Added In 0.1.0b1

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

### Beta Notes For 0.1.0b1

- Starter files and defaults may change before 1.0.
- Public config is intended to stabilize through beta feedback.
