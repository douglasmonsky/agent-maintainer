# Troubleshooting

Start with:

```bash
python3 -m scripts.guardrail doctor
```

Use `--strict` after setup or after pushing when warnings should fail:

```bash
python3 -m scripts.guardrail doctor --strict
```

## Common Issues

| Symptom | Fix |
|---|---|
| Missing Python package command | Run `python3 -m scripts.guardrail bootstrap`. |
| Missing external binary | Install the named binary with the platform package manager, then rerun `doctor`. |
| GitHub Actions-only tool is not applicable | Add workflows only if that gate is relevant for the repository. |
| Manual optional tool is disabled | Enable the slow/manual gate only when that workflow is intentionally adopted. |
| Missing source, test, package, or coverage roots | Set `[tool.ai_guardrails]` paths in `pyproject.toml`. |
| Legacy file-length ratchet fails | Split the new or worsened oversized file, or refresh `file_length_baseline` only after reviewing the diff. |
| Pre-commit hook is not installed | Run `python3 -m scripts.guardrail install`. |
| Architecture config is absent | Add `tach.toml` or `.importlinter`, or accept the optional skip. |
| Tach fails in `fresh-strict` | Set `root_module = "forbid"` and define explicit modules. |
| `pip-audit` is disabled | Enable it with a pinned input such as `config/dev-lock.txt`. |
| `pip-audit` is enabled without pinned input | Add `pip_audit_args = ["-r", "config/dev-lock.txt"]` or disable pip-audit. |
| Source changed without test-file changes | Add or update tests, or set `allow_source_without_test_change = true` only when existing tests already cover the change. |
| Pyright mode differs from root config | Align `pyrightconfig.json` with `[tool.ai_guardrails].pyright_type_checking_mode`; the verifier uses its generated config. |
| `wemake` is disabled | Enable `fresh-strict` or set `enable_wemake = true`. |
| `interrogate` is disabled | Enable it after choosing a docstring coverage baseline. |
| Interrogate fails | Add useful docstrings or lower the ratchet only with an explicit baseline note. |
| Branch is ahead or dirty | Commit/push intentionally, or run non-strict doctor while work is in progress. |
| CI diff-cover cannot compare branches | Use a fetched base ref such as `origin/main`. |
| `zizmor` reports unpinned first-party actions | Either pin actions to commit SHAs or document the tag-pinning policy in `zizmor.yml`. |
| `zizmor` reports Dependabot cooldown | Add a `cooldown` section to `.github/dependabot.yml`. |

## Dependency Lock

`config/dev-dependencies.txt` is the human-edited dependency input. `config/dev-lock.txt` is generated and preferred by bootstrap and CI when present.

Refresh the lock after changing dependency inputs:

```bash
python3 -m scripts.guardrail bootstrap
.venv/bin/python -m pip freeze --exclude-editable | sort > config/dev-lock.txt
```

Then run:

```bash
python3 -m scripts.guardrail verify --profile full
```

## Verification Logs

The quiet verifier writes raw command output to `.verify-logs/`. When the terminal output is abbreviated, inspect the matching log file before changing thresholds or adding suppressions.

Clean generated logs with:

```bash
just clean-verify-logs
```
