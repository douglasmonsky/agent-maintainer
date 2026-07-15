# Owner Hardening and CI Acceleration Design

## Goal

Make Agent Maintainer faster and easier to operate as the owner's default
development foundation without weakening its verification, release, or
architecture contracts.

## Scope

This design covers repository changes only. Public proof and ongoing dogfood
campaigns are excluded. The implementation includes policy consistency,
worktree diagnostics, real-environment contract tests, workflow caching,
parallel release evidence, verifier-native partial results and aggregation,
a measured fast local commit path, and bounded compatibility cleanup.

## Design principles

1. Preserve one authoritative verification conclusion.
2. Fail closed on incomplete, stale, duplicate, or mismatched evidence.
3. Cache downloads, never trust cache contents without existing checksum or
   lockfile validation.
4. Keep publishing jobs dependent on exact-SHA release evidence and the
   verified distribution bundle.
5. Make local speed a profile-policy decision, not an ad hoc hook bypass.
6. Delete compatibility facades only after repository consumers migrate; do
   not add replacement shims.
7. Use focused commits and tests before implementation.

## Policy and diagnostic corrections

The repository's own Vulture scope must include every owned Python package,
including `src/agent_waits`. Coverage configuration must have one effective
repository floor so direct Coverage.py runs and Agent Maintainer runs cannot
communicate different policy. Pip-audit JSON findings must become structured
repair facts rather than generic target/fallback text.

Doctor must distinguish a healthy tracking branch from a deleted upstream,
report missing hooks with an exact safe remediation, and describe missing or
large verification state precisely. Artifact cleanup must be explicit,
repository-root-bound, limited to known generated paths, and dry-run by
default.

## Contract smoke boundary

The real-environment suite uses temporary directories and locally built
artifacts. It proves local wheel installation, fresh-repository initialization,
one failure-to-repair cycle, one synthetic durable wait, and exact-SHA release
evidence aggregation. It does not require network access, user credentials, or
production services.

## Workflow caching

Python caches are keyed by operating system, Python version, and dependency
inputs. npm uses the setup-node download cache while retaining `npm ci`.
Pinned gitleaks and OSV downloads may be cached, but their existing SHA-256
checks run on every restore before extraction or execution.

## Release parallelism

A matrix job records the `full`, `ci`, `security`, `manual`, and
`release` evidence independently at the same `github.sha`. Artifact names
include the SHA and profile. The existing `release-evidence` job becomes a
small aggregator so downstream trust relationships and artifact naming remain
stable. Distribution building runs concurrently because it cannot publish.
Every terminal publication or attachment job continues to require both the
aggregate evidence and build jobs.

## Verifier-native partial results

Parallel PR execution is implemented at the verifier boundary, not by copying
individual shell commands into workflows. A partial manifest records the
profile, group, exact source identity, configuration fingerprint, selected
checks, results, and coverage-data identity where applicable. Aggregation
rejects missing groups, duplicates, mismatched source/configuration identity,
overlapping checks, or unsuccessful partial results.

The first groups are `tests-and-coverage` and `static-and-policy`. Coverage
is combined and enforced exactly once. The aggregate job emits the same
authoritative summary and status expected from sequential verification.

## Local commit path

Profiling capture must produce trustworthy output before CPU-level changes.
The synchronous commit path runs inexpensive policy checks and affected tests.
Full coverage remains mandatory before push or through an exact-fingerprint
successful result. A background full verifier may start after commit, using the
existing wait lifecycle, but it never converts a failed or unknown result into
permission to push.

## Simplification

Subsystems are documented as core, optional, or experimental without creating a
new plugin framework. Compatibility facades are removed in bounded groups after
reference analysis and consumer migration. Public CLI/import boundaries are
handled last. Large files are split only where the touched code exposes a real
responsibility boundary.

## Failure handling

All aggregation and cleanup operations fail closed. Missing evidence is an
error, not a skip. Unknown paths are never pruned. Cached binary checksum
failure discards the cache result and fails the job. Local result reuse requires
an exact verification fingerprint.

## Validation

Focused tests cover each new contract. Workflow changes pass pinned-action,
schema, Actionlint, Zizmor, YAML, DocSync, and release-evidence tests. Verifier
changes compare sequential and aggregate results on passing and failing cases.
The final branch passes CI-equivalent, full, security, and manual profiles as
required by the touched surface.
