# Repair Path

1. Read `.agent-maintainer/change-plans/catalog-split.md`.
2. Keep implementation changes inside `src/catalog/**`.
3. Keep focused tests under `tests/**`.
4. Do not use the plan to hide unrelated edits.
5. Run `agent-maintainer change-plan check`.
6. Run `agent-maintainer verify --profile precommit --base-ref HEAD`.
