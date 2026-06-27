# First Run Walkthrough

This walkthrough shows the intended repair loop after initializing Agent
Maintainer in a downstream repository.

## 1. Install And Initialize

```bash
python -m pip install "agent-maintainer[core]"
agent-maintainer init --track core
```

Merge `config/pyproject.agent-maintainer.toml` into `pyproject.toml`, then
commit the starter files.

## 2. Run Doctor

```bash
agent-maintainer doctor
```

Expected result: compact `PASS`, `WARN`, or `FAIL` rows. Fix `FAIL` rows first.
Warnings usually mean an optional tool, hook, or stricter policy has not been
adopted yet.

## 3. Run The Completion Gate

```bash
agent-maintainer verify --profile precommit --base-ref HEAD
```

Healthy output is quiet:

```text
PASS
```

## 4. Read Diagnostics Before Changing Thresholds

When verification fails, inspect the generated failure note before changing
configuration:

```bash
cat .verify-logs/LAST_FAILURE.md
```

The note points to failed checks, log files, artifacts, and the exact rerun
command. Fix the behavior, test, config, or architecture boundary the note
identifies, then rerun the same command.

## 5. Common First Repairs

| Failure | First Repair |
|---|---|
| Source changed without tests | Add or update a focused test. |
| File-length failure | Split the file by responsibility before suppressing. |
| Change-budget warning | Split the work into smaller commits or PRs. |
| Tach policy changed | Add an architecture decision note under `docs/architecture/decisions/`. |
| Missing optional tool | Install it only if the repo intentionally adopts that gate. |

The goal is not to silence Agent Maintainer. The goal is to make the next code
change small, tested, diagnosable, and easier to review.
