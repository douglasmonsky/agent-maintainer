<!-- docsync:object docs.troubleshooting.overview -->
# Troubleshooting

Start with:

```bash
python3 -m agent_maintainer doctor
```

Use `--strict` after setup or after pushing when warnings should fail:

```bash
python3 -m agent_maintainer doctor --strict
```

If `doctor` reports unknown `[tool.agent_maintainer]` keys, fix the typo or
remove the unsupported key before trusting the policy. Strict doctor mode turns
that warning into a failing setup result.

Verifier subprocess output is bounded and written to run-scoped artifacts under
`.verify-logs/`. A timed-out check exits as code `124`; inspect the referenced
log before widening timeouts or rerunning every profile.

For passthrough tool options such as `--semgrep-arg` and
`--check-jsonschema-arg`, repeat the option for each tool argument. Commas are
preserved inside those values.

## Common Issues

| Symptom | Fix |
|---|---|
| Missing Python package command | Run `PYTHONPATH=src python3 -m agent_maintainer bootstrap` before editable install works; bootstrap repairs hidden macOS `.pth` files and adds a local source-package symlink when possible. |
| Missing external binary | Install the named binary with the platform package manager, then rerun `doctor`. |
| Missing external binary: gitleaks | Install Gitleaks locally, for example `brew install gitleaks` on macOS, or disable secret scanning for repos that do not use it. |
| Missing external binary: osv-scanner or trivy | Install the scanner locally only for repositories where that manual gate is relevant, or keep it disabled. |
| Missing external binary: markdownlint-cli2 or taplo | Run `npm ci` when `package-lock.json` is present, or disable the gate when the file type is not relevant. |
| Missing Python package command: yamllint or check-jsonschema | Run `python3 -m agent_maintainer bootstrap` after refreshing `config/dev-lock.txt`. |
| Missing Python package command: cyclonedx-py or pip-licenses | Run `python3 -m agent_maintainer bootstrap` after refreshing `config/dev-lock.txt`. |
| GitHub Actions-only tool is not applicable | Add workflows only if that gate is relevant for the repository. |
| Manual optional tool is disabled | Enable the slow/manual gate only when that workflow is intentionally adopted. |
| Missing source, test, package, or coverage roots | Set `[tool.agent_maintainer]` paths in `pyproject.toml`, or use `.agent-maintainer/config.toml` / `agent-maintainer.toml` when the repo does not use pyproject config. |
| Legacy file-length ratchet fails | Split the new or worsened oversized file, or refresh `file_length_baseline` only after reviewing the diff. |
| Pre-commit hook is not installed | Run `python3 -m agent_maintainer install`. |
| Architecture config is absent | Add `tach.toml` or `.importlinter`, or accept the optional skip. |
| Tach fails in `fresh-strict` | Set `root_module = "forbid"`, explicitly assign each non-init Python source module under Tach's checked roots, and remove module entries that no longer resolve to source. |
| `pip-audit` is disabled | Enable it with a pinned input such as `config/dev-lock.txt`. |
| `pip-audit` is enabled without pinned input | Add `pip_audit_args = ["-r", "config/dev-lock.txt"]` or disable pip-audit. |
| License check should enforce policy | Add `--allow-only=...` or `--fail-on=...` to `license_check_args`; otherwise it is only a report. |
| Source changed without test-file changes | Add or update tests, or set `allow_source_without_test_change = true` only when existing tests already cover the change. |
| Pyright mode differs from root config | Align `pyrightconfig.json` with `[tool.agent_maintainer].pyright_type_checking_mode`; the verifier uses its generated config. |
| `wemake` is disabled | Enable `fresh-strict` or set `enable_wemake = true`. |
| `interrogate` is disabled | Enable it after choosing a docstring coverage baseline. |
| Interrogate fails | Add useful docstrings or lower the ratchet only with an explicit baseline note. |
| Branch is ahead or dirty | Commit/push intentionally, or run non-strict doctor while work is in progress. |
| Verifier reuses a failed same-state result after a transient tool or network failure | Rerun the same profile with `--force`, for example `python3 -m agent_maintainer verify --profile full --force`. |
| Hook says same-state verifier is already running | Wait with the command in the hook capsule instead of starting another verifier. If repo state changed after the hook started, rerun the relevant profile once. |
| Hook reused a previous same-state failure | Inspect the run-scoped failure capsule, fix the root cause, then rerun the relevant profile with `--force` only for confirmed transient failures. |
| CI diff-cover cannot compare branches | Use a fetched base ref such as `origin/main`. |
| `zizmor` reports unpinned first-party actions | Either pin actions to commit SHAs or document the tag-pinning policy in `zizmor.yml`. |
| `zizmor` reports Dependabot cooldown | Add a `cooldown` section to `.github/dependabot.yml`. |

Claude async-rewake stop hooks surface the same compact hook capsule on stderr
and exit `2`; treat that as Claude Code being reawakened to wait or repair,
not as an unstructured shell failure.

## Dependency Lock

`config/dev-dependencies.txt` is the human-edited dependency input. `config/dev-lock.txt` is generated and preferred by bootstrap and CI when present.

Refresh the lock after changing dependency inputs:

```bash
python3 -m agent_maintainer bootstrap
.venv/bin/python -m pip freeze --exclude-editable | sort > config/dev-lock.txt
```

Then run:

```bash
python3 -m agent_maintainer verify --profile full
```

## Verification Logs

The quiet verifier writes raw command output to `.verify-logs/`. When the terminal output is abbreviated, inspect the matching log file before changing thresholds or adding suppressions.

Clean generated logs with:

```bash
just clean-verify-logs
```

Agent Maintainer and hook subprocesses set `PYTHONDONTWRITEBYTECODE=1` by default so
`__pycache__` and `*.pyc` files are not produced during normal verification.
Set `AGENT_MAINTAINER_WRITE_BYTECODE=true` only when explicitly debugging Python
bytecode-cache behavior.
<!-- docsync:object.end docs.troubleshooting.overview -->
