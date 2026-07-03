# Architecture Decision: DocSync Object Region Markers

Status: accepted

## What Changed?

DocSync now has an explicit `markdown.object_regions` helper that validates
Markdown object start/end markers, and the `commands.object_markers` repair
command may depend on it.

## Why Necessary?

DocSync object scope now mirrors evidence scope with explicit end markers. The
parser and repair command both need the same fence-aware marker discovery so
examples inside code fences do not become live trace objects.

## Why This Is Not Architecture Drift

The dependency stays inside the DocSync package. It does not introduce any
dependency on Agent Maintainer, Archguard, hook clients, or verifier internals.
The new module keeps object-region rules centralized instead of duplicating
Markdown marker parsing in the command layer.

## Alternatives Considered

1. Duplicate marker scanning in the repair command. Rejected because parser and
   repair behavior would drift.
2. Put object-region validation in the CLI command. Rejected because validation
   is Markdown-domain logic, not command orchestration.
3. Let the repair command parse raw strings directly. Rejected because it would
   likely mis-handle fenced examples and reopen the token-bloat/problematic
   marker behavior this change is designed to fix.

## Boundary Impact

`markdown.object_regions` owns fence-aware object start/end marker collection
and strict-region diagnostics. `commands.object_markers` owns migration and
repair orchestration. `markdown.parser` continues to own DocObject resolution.

## What Remains Forbidden?

DocSync must remain extractable and must not import `agent_maintainer` or
`archguard`. Do not relax DocSync Tach contracts or run `tach sync` to hide
unexpected dependencies.

## Review Or Expiration Condition

Revisit this decision if DocSync moves marker-region validation into a public
API or if non-Markdown document formats need a separate object-region model.
