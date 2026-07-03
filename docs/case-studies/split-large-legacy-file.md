<!-- docsync:object docs.case_studies_split_large_legacy_file.overview -->
# Split Large Legacy File

This case study uses the
[`examples/context-safe-ratchet`](../../examples/context-safe-ratchet)
fixture to prove the large-file repair workflow. The fixture is intentionally
small so the test remains fast, but it exercises the same safe-reading
commands intended for larger legacy files.

## Goal

Show that an agent can inspect file shape before reading full source content,
then expand only the context it needs for the repair.

## Fixture

- Repository: `examples/context-safe-ratchet`
- Legacy file: `src/legacy/big.py`
- File length in fixture: 31 lines
- Known issue: negative quantities are not rejected

## Commands

Run from a temporary copy of the example:

```bash
git init
git add .
git commit -m "example baseline"
agent-maintainer context file src/legacy/big.py --outline
agent-maintainer verify --profile precommit --base-ref HEAD
```

## Measured Result

The file-outline command reported two functions without dumping the complete
file into the agent context:

| Symbol | Lines | Span |
|---|---:|---|
| `price_for_order` | 11 | `9:19` |
| `label_for_order` | 10 | `22:31` |

The verifier found the failing behavior through `pytest-coverage` in about
2 seconds. The failing test was:

```text
tests.test_big::test_price_for_order_rejects_negative_quantity
```

The bounded failure fact was:

```text
Failed: DID NOT RAISE ValueError
```

## Agent Lesson

For a real large file, the agent should use outline-first inspection before
reading full source. That keeps context bounded and points the repair toward
the relevant function span.

## Limitations

This fixture proves the workflow, not a production-scale split. A larger
case study should measure the same commands on a file that actually exceeds
the configured file-length warning threshold.
