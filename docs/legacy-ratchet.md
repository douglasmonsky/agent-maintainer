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

This mode keeps conservative defaults and leaves the heavy optional gates off unless explicitly configured. In particular, it disables `wemake-python-styleguide` and `pip-audit` at the mode layer. Existing explicit pyproject fields still win.

Recommended adoption path:

1. Configure correct source, test, package, coverage, file-length, and vulture paths.
2. Run `python3 -m scripts.guardrail doctor` and fix hard failures first.
3. Run `python3 -m scripts.guardrail verify --profile fast`.
4. Add tests or set `require_tests = false` only when tests are intentionally absent.
5. Promote to `precommit`, then `full`, then `ci`.
6. Enable `.importlinter`, `pip-audit`, and `wemake` only after each has a clean baseline or explicit ratchet plan.

Useful overrides during adoption:

```bash
python3 -m scripts.guardrail verify --profile full \
  --mode legacy-ratchet \
  --source-root my_package \
  --package-path my_package \
  --coverage-source my_package
```

Keep suppressions narrow. The suppression budget is meant to prevent new broad ignores even when old code still needs cleanup.
