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

The publish workflow owns a dedicated release-evidence job. It runs the full,
CI, security, manual, and release profiles from one checkout, then aggregates
their verifier-compatible manifests into one self-contained JSON document.

The aggregate is eligible only when:

- every required profile occurs exactly once;
- every manifest uses the supported schema, contains a passed check, and has no
  failed or unknown check status;
- every manifest records the same full Git SHA and a clean worktree;
- every profile is recent, with a maximum evidence age of 24 hours;
- the embedded canonical manifest matches its recorded SHA-256; and
- the aggregate commit matches the clean checkout consuming it.

The oldest profile controls aggregate expiry. Build, GitHub-release attachment,
TestPyPI, and PyPI jobs download the upstream aggregate and validate it again
before acting. They do not reconstruct profile evidence locally.

Release-only packaging checks are recorded through
`python -m agent_maintainer.release_evidence record -- just release-check`, so
their actual terminal exit code participates in the same profile contract.

## Consequences

- Publish runs are intentionally heavier because all release-blocking profiles
  execute hermetically for the exact workflow commit.
- Partial, duplicate, dirty, stale, malformed, failed, reordered, wrong-commit,
  and digest-mismatched evidence fails closed.
- Local profile runs remain useful preflight evidence but cannot authorize a
  publish job.
- Full action SHA pinning and verification of transferred distribution digests
  remain CS-08 work; this decision does not treat the aggregate's embedded
  profile digests as a substitute for artifact-transfer integrity.
