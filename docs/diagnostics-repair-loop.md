<!-- docsync:object docs.diagnostics_repair_loop.overview -->
# Diagnostics And Repair Loop

Agent Maintainer is designed to keep ordinary pass output quiet and put detailed
failure evidence in artifacts.

## Summary-First Output

Verifier output should prioritize:

- profile;
- pass or fail;
- run id;
- duration;
- failed checks;
- the smallest useful next command.

Raw stdout, stderr, stack traces, and long check details belong in run-scoped
files under `.verify-logs/runs/<run-id>/`.

## Failure Pointers

`LAST_FAILURE.md` is a convenience pointer to the latest failed run. It is not
the authoritative history. When multiple agents work in one repository, another
run can update the pointer.

Use run-scoped paths when repairing a specific failure:

```bash
python3 -m agent_maintainer context failures \
  --log-dir .verify-logs/runs/<run-id> \
  --limit 20
```

## Retention

Run history retention is configured in `pyproject.toml`:

```toml
[tool.agent_maintainer.diagnostics]
run_history_limit = 10
```

The default keeps enough recent runs for overlapping agent work without letting
diagnostics grow indefinitely. Use a larger value for heavily parallel repos.
Use `0` only when run history must be disabled.

## Repair Discipline

Read the failure note before changing code or configuration. Fix the root cause
instead of lowering thresholds, adding broad suppressions, or bypassing hooks. If
a check is wrong, make the smallest correction to the check, config, or docs and
include that reasoning in the PR.

See also:

- [Context safety](context-safety.md)
- [Agent Maintainer guidance](agent-maintainer-guidance.md)
- [Troubleshooting](troubleshooting.md)
