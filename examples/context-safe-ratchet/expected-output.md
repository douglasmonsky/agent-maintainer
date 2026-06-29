# Expected Output

The exact line numbers may differ after edits, but a healthy run should show:

```text
context failures: bounded failing-check summaries, not full logs
context file --outline: symbols and line ranges for src/legacy/big.py
ratchet next: one or more ranked repair targets
verify --profile precommit: fails until the negative-quantity edge case is fixed
```

After the repair, `pytest` and the precommit profile should pass.
