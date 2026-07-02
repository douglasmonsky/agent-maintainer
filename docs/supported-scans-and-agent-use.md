# Supported Scans And Agent Use

Agent Maintainer coordinates existing tools. It does not replace them. Its value
is profile discipline, bounded artifacts, repair commands, and agent guidance
that keeps raw logs out of chat.

## Scan Matrix

| Area | Tools / Checks | Typical Profile | Agent Use |
|---|---|---|---|
| Change control | Change budget, cohesive change plans, source-without-test policy | `fast`, `precommit`, `ci` | Keep edits small and explain intentionally large changes. |
| Size and structure | File length, folder cohesion, suppression budget | `fast`, `precommit`, `full` | Refactor high-branch functions before expanding features. |
| Python quality | Ruff, Pyright, Pylint, wemake, Xenon/Radon | `precommit`, `full`, `ci` | Fix design pressure before adding suppressions. |
| Tests and coverage | pytest, coverage, diff-cover, release packaging checks | `precommit`, `full`, `ci`, release | Add focused tests before broader gates. |
| Architecture | Tach, Import Linter, Archguard decision notes | `full`, `ci` | Respect module boundaries; add ADRs for boundary changes. |
| Dependency hygiene | deptry, vulture | `full`, `ci` | Remove dead code/deps or document intentional exports. |
| Python security | Bandit, pip-audit | `full`, `ci` | Fix insecure patterns and vulnerable dependencies. |
| Secrets | Gitleaks current-tree, range, and history modes | `full`, `ci`, `security` | Stop immediately and rotate secrets if real credentials appear. |
| SAST | Semgrep | `manual` | Run on focused, stable configs; treat findings as review inputs. |
| Multi-ecosystem CVEs | OSV Scanner | `manual` | Enable for repos with JS, lock files, or mixed ecosystems. |
| Containers and IaC | Trivy | `manual` | Enable only when Docker, Kubernetes, Terraform, or images matter. |
| SBOM and licenses | CycloneDX Python, pip-licenses | `ci`, `manual` | Produce audit artifacts; add policy only after license rules exist. |
| GitHub Actions | actionlint, zizmor | `full`, `ci` | Keep workflow syntax and permissions safe. |
| Docs/config hygiene | Interrogate, markdownlint, yamllint, Taplo, check-jsonschema | `full`, `ci` | Keep public docs, YAML, TOML, and schema contracts readable. |
| Mutation testing | Mutmut target/result ratchets, mutation sweep | `manual` | Keep blocking targets narrow; use sweeps for advisory test discovery. |
| Repair loop | `.verify-logs`, context commands, repair plans, HTML report | all profiles | Use run IDs and bounded context instead of pasting raw logs. |

## Recommended Agent Workflow

1. Read `AGENTS.md` and `AGENTS.agent-maintainer.md`.
2. Run focused tests and touched-file lint during the edit loop.
3. Use `context failures` or `context log` only after a verifier failure.
4. Run `verify --profile precommit` before finishing local work.
5. Run `full`, `ci`, `security`, and `manual` once before PR or merge.
6. Use `assess setup` before first adoption or major config tightening.
7. Use `assess debt` to choose the next hardening category.

## Setup And Score Commands

```bash
python3 -m agent_maintainer assess setup
python3 -m agent_maintainer assess setup --json
python3 -m agent_maintainer assess debt
python3 -m agent_maintainer assess debt --json
```

These commands are advisory. They should guide configuration and repair plans,
not replace tests or reviewer judgment.
