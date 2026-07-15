# Exact-Commit Release Evidence

- Status: accepted
- Date: 2026-07-10
- Scope: publish eligibility and release verification

## Context

The publish workflow previously built and published distributions after only
the release-only packaging tests. Full, CI, security, and manual verification
could have run elsewhere, on another commit, from a dirty worktree, or not at
all. A green but unrelated workflow run was therefore not reliable evidence
for the source being published.

## Decision

The publish workflow owns five independent release-profile matrix jobs for the
full, CI, security, manual, and release profiles. Each clean checkout uploads
one verifier-compatible manifest for the workflow commit. A dedicated
release-evidence job downloads all five artifacts and aggregates them into one
self-contained JSON document.

The aggregate is eligible only when:

- every required profile occurs exactly once;
- every manifest uses the supported schema, contains a passed check, and has no
  failed or unknown check status;
- every manifest records the same full Git SHA and a clean worktree;
- every profile is recent, with a maximum evidence age of 24 hours;
- the embedded canonical manifest matches its recorded SHA-256; and
- the aggregate commit matches the clean checkout consuming it.

The oldest profile controls aggregate expiry. Distribution construction runs
in parallel with profile verification because it cannot publish or attach
artifacts. GitHub-release attachment, TestPyPI, and PyPI jobs require both the
aggregate and the verified distribution bundle, then validate both immediately
before acting. They do not reconstruct profile evidence locally.

Release-only packaging checks are recorded through
`python -m agent_maintainer.release_evidence record -- just release-check`, so
their actual terminal exit code participates in the same profile contract.

## Consequences

- Publish runs use more concurrent runners, but the release-blocking profiles
  no longer serialize their wall-clock time.
- Release workflows intentionally avoid dependency and tool-download caches so
  less-trusted workflow runs cannot poison publication inputs.
- Partial, duplicate, dirty, stale, malformed, failed, reordered, wrong-commit,
  and digest-mismatched evidence fails closed.
- Local profile runs remain useful preflight evidence but cannot authorize a
  publish job.
- Full action SHA pinning and verification of transferred distribution digests
  remain CS-08 work; this decision does not treat the aggregate's embedded
  profile digests as a substitute for artifact-transfer integrity.
