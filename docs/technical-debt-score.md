# Technical Debt Score

The Technical Debt Score is planned product work. It should give humans and
coding agents one transparent view of repository maintenance risk while keeping
the underlying evidence visible.

The score must not become an opaque badge. It should be a scorecard with
sub-scores, confidence, evidence links, and deltas.

## Scoring Principle

Use a 0-100 debt-risk score where lower is better:

- `0-20`: low debt signal.
- `21-50`: manageable debt.
- `51-75`: high maintenance risk.
- `76-100`: severe maintenance risk.

Every score must show which evidence moved it. If evidence is missing, lower the
confidence instead of pretending the repo is healthy.

## Proposed Categories

| Category | Signals |
|---|---|
| Reviewability | Change budget, touched-file count, diff size, cohesive change-plan status. |
| Tests and coverage | Total coverage, changed-code coverage, source-without-test-change policy, test root health. |
| Type and style quality | Pyright, Ruff, Pylint, wemake, Interrogate. |
| Complexity and size | Radon, Xenon, file length, structure cohesion. |
| Architecture | Tach or Import Linter status, Archguard decision-note coverage, boundary drift. |
| Dependency and security | deptry, vulture, Bandit, pip-audit, Gitleaks, Semgrep, OSV, Trivy where relevant. |
| Docs and config hygiene | markdownlint-cli2, yamllint, Taplo, check-jsonschema, stale generated guidance. |
| Diagnostics health | Fresh manifest, run-scoped artifacts, duplicate generated artifacts, hook audit trail. |
| Ratchet and mutation maturity | Ratchet targets, Mutmut target count, result ratchet, advisory sweep readiness. |

## Evidence Sources

The first implementation should derive evidence from existing Agent Maintainer
artifacts:

- `.verify-logs/manifest.json`
- `.verify-logs/pr-summary.md`
- coverage artifacts
- mutation result artifacts
- ratchet baseline/status output
- doctor JSON output
- current `[tool.agent_maintainer]` config

It should not require a new scanner category.

## Suggested Interface

```bash
python3 -m agent_maintainer assess debt
python3 -m agent_maintainer assess debt --json
python3 -m agent_maintainer assess debt --compare origin/main
```

Report integration should follow after the CLI:

```bash
python3 -m agent_maintainer report html
```

## Output Requirements

Human output should be compact:

```text
Technical Debt Score: 34/100 risk (medium confidence)

Top drivers:
1. Structure cohesion warnings in src/agent_maintainer/core and test_intel.
2. Mutmut advisory candidates not promotion-ready.
3. Manual Trivy gate disabled because no container/IaC assets detected.

Improvement path:
1. Split core helper responsibilities.
2. Continue mutation survivor triage for reporting.py.
3. Add setup advisor recommendations before expanding optional gates.
```

JSON output should include:

- total score;
- confidence;
- category scores;
- evidence references;
- missing evidence;
- top drivers;
- suggested next actions;
- delta from a comparison baseline when available.

## Guardrails

- Advisory by default.
- No hidden pass/fail behavior.
- No single score without category details.
- No network dependency.
- No punishment for irrelevant tools that are intentionally disabled.
- Missing evidence reduces confidence, not necessarily score.

## Why This Matters

Agent Maintainer already produces many useful signals. A transparent Technical
Debt Score can turn those signals into a prioritized repair conversation:

- humans see where maintenance risk is concentrated;
- agents get ranked repair targets;
- CI can show directionality without blocking on immature policy;
- teams can later choose their own score thresholds.
