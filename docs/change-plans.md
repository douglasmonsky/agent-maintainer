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

This phase makes plans parseable and checkable. Change-budget integration is a
separate follow-up so large planned diffs do not become silent bypasses.
