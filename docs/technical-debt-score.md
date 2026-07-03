<!-- docsync:object docs.technical_debt_score.overview -->
# Technical Debt Score

The Technical Debt Score is an advisory scorecard for repository maintenance
risk. It is not a hidden pass/fail gate. Lower is better, and the score is
useful only because the underlying evidence is visible.

```bash
python3 -m agent_maintainer assess debt
python3 -m agent_maintainer assess debt --json
python3 -m agent_maintainer assess debt --target ../some-repo
```

By default, the command writes:

```text
.verify-logs/technical-debt-score.json
.verify-logs/technical-debt-score.md
```

Use `--no-write` to print the score without writing artifacts.

## Score Bands

| Score | Meaning |
|---:|---|
| `0-9` | Excellent dogfooding: strong active controls with only watch items. |
| `10-25` | Low maintenance risk. |
| `26-50` | Moderate risk with a few adoption gaps. |
| `51-75` | High risk; prioritize tests, boundaries, and diagnostics. |
| `76-100` | Critical risk; start with conservative ratchets. |

Every score includes category evidence. Missing evidence lowers confidence
instead of pretending the repo is healthy. A below-10 score does not mean there
is no possible cleanup work. It means active controls are strong, diagnostic
evidence is current, and no category has meaningful debt pressure under the
configured policy.

## Categories

| Category | Signals |
|---|---|
| Reviewability | Change budget, file length caps, folder-count policy, and verifier evidence. |
| Tests and Coverage | Required tests, detected tests, total and changed-code coverage floors. |
| Type and Style | Pyright mode, strict-Pyright ratchet, Ruff complexity, and wemake strictness. |
| Architecture Boundaries | Tach or Import Linter config evidence and strict module coverage. |
| Dependencies and Security | pip-audit, secret scanning, OSV, Trivy, SBOM, and licenses. |
| Docs and Config Hygiene | Interrogate, markdownlint, yamllint, Taplo, and check-jsonschema. |
| Diagnostics | Run-scoped artifacts and manifest presence. |
| Ratchets and Mutation Maturity | Legacy ratchets and Mutmut target/result ratchets. |

## Report Integration

`python3 -m agent_maintainer report html` includes a Technical Debt Score panel
when `.verify-logs/technical-debt-score.json` exists. Generate the score first:

```bash
python3 -m agent_maintainer assess debt
python3 -m agent_maintainer report html
```

The verification summary also includes the score and top debt drivers when the
artifact exists. If the score has not been run, it says `not run` and shows the
exact command.

## How Agents Should Use It

The score is a prioritization aid:

- Pick the highest-risk category with clear evidence.
- Make one focused repair.
- Rerun the smallest relevant check.
- Run `assess debt` again to see whether the score or evidence changed.

Do not tune the score by disabling relevant gates. Improve the underlying
signals, or document why a gate is intentionally not relevant.
<!-- docsync:object.end docs.technical_debt_score.overview -->
