# Context-Safe Ratchet Example

This example shows an existing Python repo using bounded context and ratchet
commands to repair legacy code without dumping whole files into an agent prompt.

## Run

From this directory, with Agent Maintainer installed:

```bash
git init
git add .
git commit -m "example baseline"
agent-maintainer ratchet baseline --base-ref HEAD --force
agent-maintainer ratchet status
agent-maintainer ratchet next
agent-maintainer context file src/legacy/big.py --outline
agent-maintainer context failures
agent-maintainer verify --profile precommit --base-ref HEAD
```

## Intentional Failure

`src/legacy/big.py` has branchy legacy logic and a known edge-case bug for
negative quantities. The tests show the expected behavior. The repair flow is:

1. Use `context failures` for bounded failure facts.
2. Use `context file ... --outline` before reading large files directly.
3. Use `ratchet next` to pick the smallest repair target.
4. Fix the edge case and rerun focused tests before the verifier profile.

See [expected-output.md](expected-output.md) and [repair-path.md](repair-path.md).
