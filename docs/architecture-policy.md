<!-- docsync:object docs.architecture_policy.overview -->

# Architecture Policy

Agent Maintainer treats architecture checks as policy, not just import linting.
For this repository, Tach is the active architecture tool.

## Strict Module Coverage

Tach should use explicit source roots and forbid unassigned root modules:

```toml
source_roots = ["src", ".codex/hooks", ".claude/hooks"]
root_module = "forbid"
```

With `root_module = "forbid"`, source files under configured roots must belong
to an explicit module. This prevents new files from drifting into unowned
architecture space.

## Domain Files

This repo keeps Tach policy split by domain files so the contract remains
reviewable as the package grows. Avoid dumping unrelated paths into one module
just to satisfy the checker.

When a file naturally belongs to a new domain, add that domain explicitly and
explain why in an architecture decision note.

## Policy Changes Require ADRs

If a change modifies Tach policy, domain files, dependency boundaries, or strict
root-module behavior, add or update an ADR under:

```text
docs/architecture/decisions/
```

The ADR should state:

- what boundary changed;
- why the change was needed;
- why it is not architecture drift;
- alternatives considered;
- what remains forbidden.

## Commands

Run:

```bash
python3 -m archguard tach-config --strict-root-module
python3 -m archguard decision-check --base-ref HEAD
tach check --exact
```

Do not use `tach sync` as a silent fix. If the graph changed, make the boundary
decision explicit.

See also:

- [Structure cohesion](structure-cohesion.md)
- [Tool map](tool-map.md)
- [Architecture decisions](architecture/decisions/)
