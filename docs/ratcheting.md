# Ratcheting

Ratcheting is the adoption model for repositories that already have existing
violations. Instead of forcing a legacy repository to become clean all at once,
Agent Maintainer distinguishes new, worsened, unchanged, improved, and resolved
findings against a saved baseline.

Public behavior must remain deterministic and bounded by default.

## Baseline Status

Phase 13 adds a multi-check baseline file at:

```text
.agent-maintainer/ratchet-baseline.json
```

The baseline records current findings as JSON, including:

- version
- creation time
- creating tool
- base ref
- repository commit
- dirty worktree state
- mode
- enabled checks
- operator notes

Initial supported checks:

- `file-length`
- `structure-cohesion`

Create the initial baseline:

```bash
python3 -m agent_maintainer ratchet baseline create
```

Refresh after intentionally accepting current findings:

```bash
python3 -m agent_maintainer ratchet baseline refresh
```

Check status:

```bash
python3 -m agent_maintainer ratchet status
```

Emit machine-readable status:

```bash
python3 -m agent_maintainer ratchet status --format json
```

## Stale Baselines

`ratchet status` reports stale-baseline signals so agents and reviewers can tell
when the baseline no longer describes the repository being edited.

Current stale signals:

- baseline was created from a dirty worktree
- baseline base ref differs from the requested base ref
- baseline paths no longer exist
- baseline findings are no longer present in current findings

## Planned Follow-Up

Planned capabilities include ranked repair targets, changed-code discipline,
generated agent guidance in `AGENTS.ratchet.md`, context packs, and repair plans.
The intended outcome is stricter maintenance over time without turning every old
violation into immediate noise for the current change.
