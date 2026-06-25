# Legacy Ratchet Mode

Use `legacy-ratchet` when installing the kit into an existing repository that should improve without first paying down every historical issue.

```toml
[tool.ai_guardrails]
mode = "legacy-ratchet"
source_roots = ["src"]
test_roots = ["tests"]
package_paths = ["src"]
coverage_source = ["src"]
```

This mode keeps conservative defaults and leaves the heavy optional gates off unless explicitly configured. In particular, it disables `wemake-python-styleguide`, Interrogate, and `pip-audit` at the mode layer. Existing explicit pyproject fields still win.

Unlike `fresh-strict`, legacy mode does not require every historical file to satisfy the file-length thresholds immediately. It defaults:

```toml
file_length_baseline = ".guardrails/file-length-baseline.json"
```

With that baseline, existing oversized files pass when they are unchanged or improved. The check fails when a new file exceeds the limits or an existing baseline entry grows beyond its recorded physical or source-line count.

Baseline format:

```json
{
  "version": 1,
  "limits": {
    "max_physical": 600,
    "max_source": 450
  },
  "files": {
    "src/legacy_module.py": {
      "physical": 724,
      "source": 510
    }
  }
}
```

Generate or refresh the baseline after choosing the intended limits:

```bash
python3 -m scripts.check_file_lengths \
  --write-baseline .guardrails/file-length-baseline.json
```

Refresh deliberately. A refresh accepts the current state as the new floor, so review the diff and do not use it to hide newly worsened files.

Recommended adoption path:

1. Configure correct source, test, package, coverage, file-length, and vulture paths.
2. Run `python3 -m scripts.guardrail doctor` and fix hard failures first.
3. Run `python3 -m scripts.guardrail verify --profile fast`.
4. Add tests or set `require_tests = false` only when tests are intentionally absent.
5. Generate `.guardrails/file-length-baseline.json` if oversized legacy files exist.
6. Promote to `precommit`, then `full`, then `ci`.
7. Enable `tach.toml` or `.importlinter`, Interrogate, `pip-audit`, and `wemake` only after each has a clean baseline or explicit ratchet plan.

Useful overrides during adoption:

```bash
python3 -m scripts.guardrail verify --profile full \
  --mode legacy-ratchet \
  --source-root my_package \
  --package-path my_package \
  --coverage-source my_package
```

Keep suppressions narrow. The suppression budget is meant to prevent new broad ignores even when old code still needs cleanup.
