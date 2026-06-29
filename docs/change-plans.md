# Cohesive Change Plans

Cohesive change plans document intentionally large changes before they bend
normal review-size expectations.

Plans live in:

```text
.agent-maintainer/change-plans/<slug>.md
```

Create a starter plan:

```bash
python -m agent_maintainer change-plan new package-migration
```

Validate plans and current diff scope:

```bash
python -m agent_maintainer change-plan check
```

Plans use TOML front matter between `+++` delimiters, followed by required
markdown sections that explain why the work is intentionally large, why it
should not split smaller, what may change, what must not change, how it will be
verified, how it can be rolled back, and what ratchet work remains.

## Integration Branch Series

Use `kind = "integration-branch-series"` for a planned sequence of PRs that land
on a temporary integration branch before the final merge back to the target
branch.

```bash
python -m agent_maintainer change-plan new package-migration \
  --kind integration-branch-series \
  --integration-branch ratchet/package-migration \
  --expected-unit "move config modules" \
  --expected-unit "update tests"
```

Integration branch plans require these extra front-matter fields:

```toml
integration_branch = "ratchet/package-migration"
target_branch = "main"
merge_strategy = "squash-after-series"
expected_units = [
  "move config modules",
  "move check modules",
  "update tests",
  "update docs and generated guidance",
]
```

The change-budget gate gives planned-large-change treatment only when the active
Git branch matches `integration_branch` and the plan is otherwise valid.

When a valid active plan exists, the change-budget gate can bend normal changed
line/file limits and source-without-test heuristics for the scoped migration.
Out-of-plan paths, expired plans, and missing required sections still fail.
Coverage, type checks, Ruff, architecture checks, suppression budgets, security
checks, generated guidance freshness, and doctor checks still run normally.
