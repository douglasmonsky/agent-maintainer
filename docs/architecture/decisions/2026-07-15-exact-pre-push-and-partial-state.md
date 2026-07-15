# Bind Pre-Push And Partial Evidence To Exact Repository State

## Boundary

The installed pre-push hook consumes pre-commit's exact outgoing
`PRE_COMMIT_FROM_REF` and `PRE_COMMIT_TO_REF` values. It runs the complete
precommit profile against the remote-side ref and refuses to verify when the
local pushed ref is not the checked-out `HEAD` or the checkout is dirty.

Grouped verifier partials now carry the staged mode plus index, worktree,
untracked-file, configuration, and environment hashes from the verifier
fingerprint. Aggregation requires every shared field to match.
The tool environment is intentionally group-specific because independently
provisioned CI groups require different executables on `PATH`; the aggregate
preserves an environment hash keyed by group instead of requiring those hashes
to match.

## Why

Comparing a completed commit to `HEAD` produces an empty diff and can miss local
policy failures until CI. Likewise, commit/config identity alone cannot
distinguish two partial runs made from different dirty states at the same
commit. Both boundaries must bind evidence to the state actually checked.
Environment identity must also remain attached to each partial without making
valid tool-specialized jobs falsely incompatible.

## Why This Is Not Architecture Drift

The new hook module is a narrow command adapter from pre-commit's environment
contract to the existing verifier CLI. It adds explicit Tach dependencies on
the verifier input reader and orchestrator; it does not move verification
policy into hook code. Partial state remains owned by verifier fingerprints and
the extracted run-artifact aggregator.

## Alternatives Considered

- Keep `HEAD` as the pre-push base. This is incorrect after changes are
  committed because the resulting diff is empty.
- Infer a remote branch name. Branch tracking can be absent, stale, or differ
  from the ref Git is actually pushing; pre-commit already supplies exact SHAs.
- Accept partials based only on commit SHA. Local grouped runs can share a SHA
  while differing in staged, unstaged, untracked, or tool environment state.

## Still Forbidden

Pre-push verification must not guess a base ref or silently verify a different
local commit. Partial aggregation must not accept missing or mismatched exact
state fields, and CI remains authoritative after revalidating the aggregate at
the protected final job.
