# Legacy Ratchet Example

This example shows a safer starting point for an existing repository that wants
Agent Maintainer feedback without enabling every strict gate immediately.

Key choices:

- `mode = "legacy-ratchet"`
- `architecture_tool = "import-linter"` so architecture checks skip until a
  contract exists
- lower-friction coverage defaults with changed-code coverage still active
- optional hardening gates disabled until a baseline exists

Run from this directory after installing Agent Maintainer:

```bash
python -m agent_maintainer doctor
python -m agent_maintainer verify --profile precommit --base-ref HEAD
```
