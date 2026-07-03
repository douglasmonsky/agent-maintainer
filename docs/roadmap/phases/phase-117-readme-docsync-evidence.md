# Phase 117: README DocSync Evidence Ratchet

Status: complete

## Goal

Start full DocSync dogfooding on public documentation by tracing the README's
durable onboarding and supported-check claims to live source evidence.

## Scope

- Add DocSync object IDs for high-value README sections.
- Add trace claims for package identity, quick start command flow, run profiles,
  supported checks, agent repair loop, and Technical Debt Score command surface.
- Add explicit evidence markers in stable source/config files.
- Add tests that keep README trace coverage intentional.

## Non-goals

- No generated `.docsync/out` artifacts committed.
- No README copy rewrite beyond hidden object markers.
- No broad trace of every documentation page in this phase.
- No runtime behavior changes.

## Deliverables

- README DocSync object markers.
- Expanded `.docsync/trace.yml`.
- Source evidence regions for README claims.
- `tests/docsync/test_readme_trace.py`.

## Acceptance Criteria

- `docsync check --base origin/main` passes.
- README durable claims are linked to explicit live evidence anchors.
- New test fails if README trace coverage is removed accidentally.
- No `.docsync/out` generated files are committed.

## Verification

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m docsync check --base origin/main`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/docsync/test_readme_trace.py tests/docsync -q`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile precommit`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile full`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile ci --base-ref origin/main --compare-branch origin/main`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile security`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile manual`

## Notes For Future Tasks

Continue this ratchet section by section through public docs. Keep each slice
small enough that claim text, source evidence, and tests remain reviewable.
