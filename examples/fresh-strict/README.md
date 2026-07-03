<!-- docsync:evidence.start evidence.mode_examples.fresh_strict_fixture -->
# Fresh Strict Example

This example shows the shape of a small new Python repository that opts into
strict Agent Maintainer checks from the start.

Key choices:

- `mode = "fresh-strict"`
- `architecture_tool = "tach"`
- `root_module = "forbid"` in `tach.toml`
- source, tests, coverage, and package paths all point at `src` and `tests`

Run from this directory after installing Agent Maintainer:

```bash
python -m agent_maintainer doctor
python -m agent_maintainer verify --profile precommit --base-ref HEAD
```
<!-- docsync:evidence.end evidence.mode_examples.fresh_strict_fixture -->
