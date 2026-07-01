# Phase 75: Below-10 Debt And Strict Typing Ratchets

## PR Title

```text
feat: ratchet strict typing and lower dogfood debt
```

## Scope

Drive Agent Maintainer's own dogfooding posture below a `10/100` advisory
Technical Debt Score without gaming thresholds. Add a sustainable strict-Pyright
ratchet, calibrate the score model with stronger evidence, reduce real
mutation/test debt, and split only evidence-backed near-limit modules.

## Requirements

- Keep this phase roadmap-first before behavior changes.
- Mark Phase 74 complete in the top-level roadmap.
- Add Technical Debt Score calibration so excellent repositories can score
  excellent.
- Replace the blunt source-file-count reviewability penalty with stronger
  signals: folder file-count findings, files near or over configured length
  caps, failed verifier manifest checks, and hotspot/bug-magnet overlap when
  available.
- Add positive evidence reductions for active, green controls: Tach strict
  module coverage, coverage and diff-cover at or above 90, current diagnostics
  and guidance, active mutation ratchets within budget, and active docs/config
  gates for matching files.
- Add a disabled-by-default strict Pyright ratchet using a baseline rather than
  turning strict mode into a zero-error gate.
- New config fields: `pyright_strict_ratchet_enabled`,
  `pyright_strict_baseline`, `pyright_strict_max_errors`, and
  `pyright_strict_profiles`.
- Add a repo baseline at `config/pyright-strict-baseline.json` from current
  strict-mode diagnostics.
- Summarize strict Pyright diagnostics by rule and file, not raw JSON.
- Refactor only evidence-backed near-limit files: `doctor/setup.py`,
  `checks/change_budget.py`, `verify/artifacts.py`, and
  `assess/debt_categories.py`.
- Update Tach domains and add ADRs for architecture-boundary changes.
- Reduce Mutmut survivors from the current blocking count of `16` where
  feasible without brittle tests.
- Keep new scanner categories, global strict Pyright mode, and arbitrary folder
  churn out of scope.

## Acceptance Criteria

- `python3 -m agent_maintainer assess debt` reports this repo below `10/100`
  with transparent evidence.
- Normal configured Pyright remains zero-error.
- Strict Pyright ratchet exists, is disabled by default for downstream repos,
  and is enabled for this repo only after a baseline is committed.
- Strict Pyright ratchet blocks regressions over baseline plus configured
  budget.
- Mutmut survivors are lower than `16`, or docs record why further reduction
  would require brittle or disproportionate tests.
- Final checks pass: `guidance --check`, `change-plan check`,
  `tach check --exact`, `doctor --strict`, `verify --profile precommit`,
  `full`, `ci`, `security`, and `manual`.

## Progress

- [ ] Roadmap-first phase entry and Phase 74 status cleanup.
- [ ] Technical Debt Score calibration and docs.
- [ ] Strict Pyright ratchet config, runner, baseline, docs, and tests.
- [ ] Evidence-backed cleanup refactor for near-limit modules.
- [ ] Mutation survivor reduction and documentation.

## Out Of Scope

- New scanner categories.
- Global Pyright strict mode.
- Changing public profile names.
- External case studies.
- Headroom integration.
