# Verified Distribution Bundles

- Status: accepted
- Date: 2026-07-10
- Scope: release artifact creation, transfer, and publication

## Context

Exact-commit release evidence proves which source revision passed the required
checks, but an artifact service is a separate trust boundary. A wheel or sdist
could be omitted, added, or replaced after the build without invalidating the
source-evidence aggregate. Checking only the artifact name or job dependency
does not establish byte identity.

## Decision

The build job creates one deterministic distribution bundle containing a
manifest and a `packages/` directory. The domain contract lives in
`agent_run_artifacts.distribution_bundle`; symlink-safe filesystem operations
live at the application boundary in `agent_maintainer.release_artifacts_io`.
The CLI additionally requires its current checkout to be clean and equal to the
expected full commit SHA.

The manifest records its schema version, kind, exact commit, and a sorted exact
inventory of package paths, byte sizes, and SHA-256 digests. It permits only
regular wheel and sdist files and requires both formats. Validation rejects
unknown fields, unsafe paths, malformed identities, missing or extra files,
symlinks, special files, size drift, and digest drift.

The build job carries the manifest's own SHA-256 through an authenticated job
output, separately from the artifact payload. Consumers match that independent
identity before trusting the manifest, so replacing both package bytes and their
listed digests still fails. The publish workflow verifies the bundle before
upload, after every artifact download, and immediately before each release
attachment or index publication. Consumers use only the verified `packages/`
directory.

## Consequences

- Release eligibility now binds passed source checks to the exact bytes crossing
  each job boundary.
- Package transfer failures and substitutions fail before credentials or release
  mutation are used.
- The domain package remains independent of CLI, Git, workflow, and filesystem
  orchestration.
- New package formats require an explicit contract and test change; they cannot
  enter a release bundle by appearing in the build directory.

## Alternatives Considered

- Trusting the GitHub artifact name was rejected because names are not content
  identities.
- A manifest carried only inside the bundle was rejected because an attacker
  able to replace both it and a package could recompute the package digest.
- Rebuilding independently in each publish job was rejected because reproducible
  builds are not yet a declared release invariant and would increase complexity.

## Boundaries That Remain Forbidden

The domain module must not import Git, CLI, workflow, filesystem, or network
code. Publish jobs must not consume packages outside the verified bundle or
skip verification after a transfer.
