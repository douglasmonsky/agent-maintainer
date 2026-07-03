<!-- docsync:object docs.fresh_strict.overview -->
# Fresh Strict Mode

Use `fresh-strict` when a repository is new or already clean enough that strict checks can block immediately.

```toml
[tool.agent_maintainer]
mode = "fresh-strict"
source_roots = ["src"]
test_roots = ["tests"]
package_paths = ["src"]
coverage_source = ["src"]
# Optional: set to tach for strict module ownership.
# architecture_tool = "tach"
```

This mode is meant to stop entropy before it becomes architecture. It keeps tests required, enables `wemake-python-styleguide`, enables Interrogate docstring coverage, lowers file and diff budgets, reduces the new-suppression budget, and sets Ruff McCabe complexity to `8`.

When `architecture_tool = "tach"` is used with `fresh-strict`, `tach.toml` must exist, define at least one module, set `root_module = "forbid"`, explicitly assign each non-init Python source module under Tach's checked source roots, and avoid module entries that no longer resolve to source files. The full verifier then runs `tach check --exact` so stale declared dependencies fail too.

Fresh-strict Tach mode also runs the Archguard architecture-decision gate in `precommit`, `full`, and `ci` profiles. Any change to Tach architecture policy files must include an architecture decision note.

Preset defaults:

| Setting | Value |
|---|---:|
| `file_length_max_physical` | 500 |
| `file_length_max_source` | 375 |
| `change_warn_lines` | 200 |
| `change_block_lines` | 600 |
| `change_warn_files` | 6 |
| `change_block_files` | 12 |
| `suppression_max_new` | 1 |
| `ruff_max_complexity` | 8 |
| `enable_wemake` | true |
| `enable_interrogate` | true |
| `interrogate_fail_under` | 80 |

Explicit pyproject fields, environment variables, and CLI flags still override the preset. For example, this keeps the mode but temporarily relaxes complexity for one run:

```bash
python3 -m agent_maintainer verify --profile full --mode fresh-strict
```

`fresh-strict` does not enable `pip-audit` by itself. Enable it with a pinned input when the repository has a stable dependency lock:

```toml
[tool.agent_maintainer]
mode = "fresh-strict"
enable_pip_audit = true
pip_audit_args = [
  "-r",
  "config/dev-lock.txt",
  "--no-deps",
  "--disable-pip",
  "--progress-spinner",
  "off",
  "--timeout",
  "5",
]
```

Use `--no-deps --disable-pip` only when the file is complete, pinned,
transitive lock. For partial requirements files, let `pip-audit` resolve
dependencies instead.

Docs/config hygiene gates are also explicit opt-ins. This repository enables
Markdownlint-cli2, yamllint, Taplo, and GitHub Actions schema validation because
Markdown, YAML, and TOML files are part of the Agent Maintainer verification surface.

For this repository, `fresh-strict` is active and the optional hardening gates are also enabled. Use:

```bash
python3 -m agent_maintainer doctor
python3 -m agent_maintainer verify --profile full
```
