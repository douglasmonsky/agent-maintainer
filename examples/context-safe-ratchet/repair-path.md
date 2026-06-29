# Repair Path

1. Run `pytest tests/test_big.py -q` to reproduce the failing edge case.
2. Inspect `src/legacy/big.py` with `agent-maintainer context file --outline`.
3. Update `price_for_order` so negative quantities raise `ValueError`.
4. Add or keep a focused regression test for negative quantities.
5. Run `pytest tests/test_big.py -q`.
6. Run `agent-maintainer verify --profile precommit --base-ref HEAD`.
