# DocSync Repository I/O Boundary

## Context

DocSync consumes configuration and trace files controlled by the repository it
is checking. Those files can name document, evidence, attestation, and generated
output paths. Treating those names as trusted allowed a checkout to read or
write outside its own repository when a developer ran an ordinary check.

The trust boundary is the canonical repository root supplied to DocSync. The
checkout may choose which repository files participate in a trace, but it must
not expand DocSync's filesystem authority beyond that root or turn a routine
validation command into an implicit write.

## Decision

The package-owned I/O policy is split into small `docsync.config` modules:
`errors` defines policy failures, `io` owns bounded reads and atomic writes,
`paths` owns repository containment, and `resolution` maps configuration into
approved roots. Callers use the narrow module they need through the exact
imports recorded in `src/docsync/tach.domain.toml`.

Repository inputs must be relative, contain no parent traversal, and resolve
under the canonical repository root. DocSync rejects every existing symlink
component, sensitive credential or private-key names, non-regular files,
non-UTF-8 text, and files larger than 8 MiB. Bounded reads open nonblocking with
no-follow semantics where the platform supports them, validate the opened file
descriptor, and stop after the byte ceiling.

YAML syntax and parser-recursion failures are normalized into DocSync domain
errors. Deeply nested repository YAML therefore cannot escape through the CLI,
stable Python API, or MCP integration as an uncaught parser exception.

Generated outputs have a separate write root: `.docsync/out/`. A legacy config
that omits `outputs.directory` keeps that default. A configured output directory
may select a descendant of that root, but cannot select the repository root,
source files, or a sibling tree. Every output file must be a strict descendant
of the configured output directory, and configured output files must be
distinct. Policy-owned names such as the generated root's `.gitignore` are
reserved and cannot be selected as configurable artifact destinations.
Attestations remain under their independently confined
`.docsync/attestations/` root. Explicit trace-authoring and repair commands may
update their validated in-repository source and trace files.

Writes reject symlink and special-file targets, render to a collision-resistant
temporary file in the destination directory, preserve an existing file's mode,
and replace the destination atomically. Every path involved in a multi-file
operation is validated before the first mutation.

`docsync check` is read-only by default. Callers that need machine-readable
artifacts request them with `--write-reports`; Agent Maintainer does so for its
verifier integration. `index`, `prompt`, `freshness`, `attest`, initializer,
repair, and trace-authoring commands retain their documented explicit writes,
now constrained to their approved roots.

The Git-diff boundary rejects empty, option-like, whitespace-bearing, and
non-printable base revisions before invoking Git. This prevents direct CLI or
stable Python API callers from turning a base revision into an option such as
an outside `--output` destination. Git diff and revision output is captured
concurrently with a 16 MiB stdout ceiling, a 64 KiB stderr ceiling, and a
10-second deadline; the child is killed when any ceiling is crossed. External
diff and text-conversion drivers are disabled.

Trace YAML is read once and reused for payload and line-span parsing. A trace
may name at most 512 distinct repository inputs and at most 32 MiB of source
content in aggregate. Repeated document and claim paths are cached within one
index build. Attestation loading likewise has file-count and aggregate-byte
ceilings. Candidate discovery uses a bounded-memory heap to retain a
deterministic filename prefix plus one overflow witness rather than sorting an
unbounded directory listing. Sensitive input rules cover common VCS metadata,
cloud, container, Kubernetes, SSH, GPG, Terraform variables and state backups,
environment, credential-store, OAuth client-secret, service-account,
private-key, kubeconfig, and secret-file locations.

## Compatibility Impact

- Existing configs that use the default `.docsync/out/` paths continue to work,
  including configs without the new `outputs.directory` key.
- Scripts that relied on plain `docsync check` creating JSON and SARIF must add
  `--write-reports`.
- Absolute paths, parent traversal, sensitive paths, and symlinked paths that
  were previously accepted are now rejected, including symlinks whose targets
  remain inside the repository.
- Direct `freshness --output` values are repository-relative and must remain
  under the configured generated-output directory.

## Alternatives Considered

- Allow arbitrary absolute paths for trusted local use. Rejected because a
  repository config is not a trustworthy authority grant and the same parser
  runs in hooks and verification.
- Permit symlinks when their current target resolves inside the repository.
  Rejected because component swaps complicate the trust proof and are not
  needed for the supported DocSync layout.
- Keep report writes implicit for compatibility. Rejected because validation
  of an untrusted checkout must be observational unless output is requested.
- Reuse Agent Maintainer or agent-context path helpers. Rejected to preserve
  DocSync's extractable sibling-package boundary.

## Residual Limits

No portable path API eliminates every time-of-check/time-of-use race if another
process can rename validated parent directories during the operation. No-follow,
descriptor validation, same-directory temporary files, and atomic replacement
close the static malicious-checkout cases; callers still must not run DocSync in
a repository concurrently controlled by a hostile process. Some no-follow and
nonblocking flags are platform-dependent. Atomic replacement preserves basic
file mode but may not preserve extended attributes or platform-specific ACLs.
