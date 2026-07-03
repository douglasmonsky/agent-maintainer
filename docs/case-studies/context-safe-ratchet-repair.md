<!-- docsync:object docs.case_studies_context_safe_ratchet_repair.overview -->
# Context-Safe Ratchet Repair

This case study uses the
[`examples/context-safe-ratchet`](../../examples/context-safe-ratchet)
fixture to show the repair loop for legacy code under bounded diagnostics.

## Goal

Show that Agent Maintainer gives an agent exact next commands and compact
failure facts instead of requiring raw log dumps in chat.

## Fixture

- Repository: `examples/context-safe-ratchet`
- Known failure: `price_for_order` accepts negative quantities
- Verification profile: `precommit`
- Expected failing check: `pytest-coverage`

## Commands

Run from a temporary copy of the example:

```bash
git init
git add .
git commit -m "example baseline"
agent-maintainer ratchet baseline create --base-ref HEAD --force
agent-maintainer ratchet status --base-ref HEAD
agent-maintainer ratchet next --base-ref HEAD --limit 3
agent-maintainer verify --profile precommit --base-ref HEAD
```

Then expand only the failing check:

```bash
agent-maintainer context --log-dir .verify-logs/runs/<run-id> failures \
  --check pytest-coverage --limit 20
agent-maintainer context --log-dir .verify-logs/runs/<run-id> log \
  pytest-coverage --tail 120
```

## Measured Result

The baseline command created:

```text
.agent-maintainer/ratchet-baseline.json
```

The ratchet status reported no new, worsened, unchanged, improved, or
resolved findings for this clean baseline. The verifier then failed exactly
one check:

| Metric | Result |
|---|---|
| Profile | `precommit` |
| Failed checks | `pytest-coverage` |
| Test result | 2 tests, 1 failure |
| Failing test | `tests.test_big::test_price_for_order_rejects_negative_quantity` |
| Failure fact | `Failed: DID NOT RAISE ValueError` |
| Coverage total | 71% |
| Duration | about 2 seconds |

The verifier summary included expansion commands pointing at the run-scoped
diagnostic directory instead of printing the entire pytest log.

## Agent Lesson

Use the run id from the verifier summary, inspect the bounded failure facts,
fix the behavior, rerun the focused failing test, then rerun the relevant
verification profile.

## Limitations

The example is intentionally tiny. It validates the context-safe repair
loop and command shape, not an end-to-end production legacy migration.
