# Cohesive Change Plans

Cohesive change plans document intentionally large changes before they bypass
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
should not be split smaller, what may change, what must not change, how it will
be verified, how it can be rolled back, and what ratchet work remains.

When a valid active plan exists, the change-budget gate can bend normal changed
line/file limits and source-without-test heuristics for the scoped migration.
Out-of-plan paths, expired plans, and missing required sections still fail.
Coverage, type checks, Ruff, architecture checks, suppression budgets, security
checks, generated guidance freshness, and doctor checks still run normally.
