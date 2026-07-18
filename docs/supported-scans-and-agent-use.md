<!-- docsync:object docs.supported_scans.overview -->
# Supported Scans And Agent Use

Agent Maintainer coordinates existing tools. It does not replace them. Its value
is profile discipline, bounded artifacts, repair commands, and agent guidance
that keeps raw logs out of chat.

## Scan Matrix

| Area | Tools / Checks | Typical Profile | Agent Use |
|---|---|---|---|
| Change control | Change budget, cohesive change plans, source-without-test policy | `fast`, `precommit`, `ci` | Keep edits small and explain intentionally large changes. |
| Size and structure | File length, folder cohesion, suppression budget, provider-neutral per-path file ceilings | `fast`, `precommit`, `full`, advisory or blocking | Refactor high-branch functions before expanding features; prune improved ceilings explicitly. |
| Java/Gradle evidence | Checked-wrapper task groups; Spotless/SpotBugs native ratchets; upward-only JaCoCo thresholds; bounded Checkstyle, PMD, SpotBugs, JUnit, and JaCoCo reports; separate project coverage labels | `precommit`, `full`, `ci` by configured group | Use complete, non-truncated runner artifacts for Java baseline lifecycle and exact repair facts; keep raw XML in Gradle build output. |
| Python quality | Ruff, Pyright, Pylint, wemake, Xenon/Radon | `precommit`, `full`, `ci` | Fix design pressure before adding suppressions. |
| Tests and coverage | pytest, coverage, diff-cover, release packaging checks | `precommit`, `full`, `ci`, release | Add focused tests before broader gates. |
| Architecture | Tach, Import Linter, Archguard decision notes, dependency-cruiser | `full`, `ci` | Respect module boundaries; add ADRs for policy changes; use explicit TypeScript/JavaScript architecture commands and bounded cruise-result facts. |
| Dependency hygiene | deptry, vulture | `full`, `ci` | Remove dead code/deps or document intentional exports. |
| Python security | Bandit, pip-audit | `full`, `ci` | Fix insecure patterns and vulnerable dependencies. |
| Secrets | Gitleaks current-tree, range, and history modes | `full`, `ci`, `security` | Stop immediately and rotate secrets if real credentials appear. |
| Documentation traceability | DocSync freshness checks when `.docsync/trace.yml` exists | `precommit`, `full`, `ci` | Update linked docs, add evidence, or create an attestation instead of ignoring stale claims. |
| SAST | Semgrep | `manual` | Run on focused, stable configs; treat findings as review inputs. |
| Multi-ecosystem CVEs | OSV Scanner | `manual` | Enable for repos with JS, lock files, or mixed ecosystems; use alias-grouped exact facts and safe relative lockfile provenance for repairs. |
| Containers and IaC | Trivy | `manual` | Enable only when Docker, Kubernetes, Terraform, or images matter. |
| SBOM and licenses | CycloneDX Python, pip-licenses | `ci`, `manual` | Produce audit artifacts; add policy only after license rules exist. |
| GitHub Actions | actionlint, zizmor | `full`, `ci` | Keep workflow syntax and permissions safe. |
| Docs/config hygiene | Interrogate, markdownlint, yamllint, Taplo, check-jsonschema | `full`, `ci` | Keep public docs, YAML, TOML, and schema contracts readable. |
| Mutation testing | Mutmut target/result ratchets, mutation sweep | `manual` | Keep blocking targets narrow; use sweeps for advisory test discovery. |
| Repair loop | `.verify-logs`, context commands, repair plans, HTML report | all profiles | Use run IDs and bounded context instead of pasting raw logs. |

Agent Maintainer requests DocSync JSON/SARIF with `docsync check
--write-reports` for repair facts. Direct `docsync check` stays read-only.

## Recommended Agent Workflow

1. Read `AGENTS.md` and `AGENTS.agent-maintainer.md`.
2. Run focused tests and touched-file lint during the edit loop.
3. Use `context failures` or `context log` only after a verifier failure.
4. Let trusted Stop/SubagentStop hooks cover `precommit` for the final state;
   run `verify --profile precommit` manually only when hooks are unavailable,
   bypassed, or a failure needs reproduction.
5. Run one broad local profile before PR or merge, usually `full`; use `ci`
   instead when diff/base-ref, workflow, or profile behavior changed. Run both
   only when that overlap is under test. Run `security` or `manual` when touching
   those gates, before release, or when explicitly requested.
6. Use `assess setup` before first adoption or major config tightening.
7. Use `assess debt` to choose the next hardening category.

## Setup And Score Commands

```bash
python3 -m agent_maintainer assess setup
python3 -m agent_maintainer assess setup --json
python3 -m agent_maintainer assess debt
python3 -m agent_maintainer assess debt --json
python3 -m agent_maintainer assess file-baselines
python3 -m agent_maintainer assess file-baselines --json
python3 -m agent_maintainer assess file-baselines create --dry-run
python3 -m agent_maintainer assess file-baselines inspect --json
python3 -m agent_maintainer assess file-baselines prune --dry-run
python3 -m agent_maintainer assess java-baseline create --dry-run
python3 -m agent_maintainer assess java-baseline inspect --json
python3 -m agent_maintainer assess java-baseline prune --dry-run
```

Setup and debt assessments remain advisory. File-baseline reports return
nonzero for ceiling regressions when configured in blocking mode. Lifecycle
commands are explicit local writes unless `--dry-run` or `inspect` is used; they
do not replace tests or reviewer judgment.
<!-- docsync:object.end docs.supported_scans.overview -->
