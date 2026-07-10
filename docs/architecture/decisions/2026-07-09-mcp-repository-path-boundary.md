# 2026-07-09: MCP Repository Path Boundary

## Status

Accepted.

## Context

The MCP adapter accepts model-controlled arguments and runs local Agent
Maintainer and DocSync commands. Its original `context_file` handler forwarded
an arbitrary path to the context CLI. The shared reader then loaded the whole
target twice before bounding the response. Other MCP handlers also accepted
unconfined log, event, target, configuration, and trace paths.

That behavior made the process working directory an ambient and incomplete
trust boundary. It could disclose process-readable files outside the
repository, open special files, or consume excessive memory before response
limits applied.

## Decision

Bind every MCP server instance to one canonical workspace root when the server
is constructed. `mcp serve --workspace-root` selects the root; the startup
working directory is the default. Changing the process working directory after
construction does not change the service's authority.

Every model-controlled filesystem argument must pass one MCP path policy before
a subprocess starts:

- paths are relative to the captured workspace root;
- absolute paths and parent traversal are rejected;
- existing symlink components and unexpected filesystem object kinds are
  rejected;
- context file reads reject credential and private-key names and files larger
  than 1 MiB; and
- context-pack output directories/files are checked for symlink or special-file
  redirects before command execution; and
- subprocesses run with the captured workspace root as their working directory.

Trusted Python entry points start with safe-path mode (`-P`) and receive a
controlled absolute `PYTHONPATH` that contains only Agent Maintainer's source
root. Inherited relative import paths and Python startup hooks are removed, so
a hostile checkout cannot shadow `agent_maintainer` or `docsync` with a local
module or package.

Child stdout and stderr are drained concurrently. Each stream retains only a
bounded tail, has an independent hard byte ceiling, and kills the child's
process group when that ceiling is exceeded. A timeout follows the same
kill-and-reap path. This bounds memory and prevents a child that fills one pipe,
floods output, or becomes silent from wedging the MCP server.

Model-controlled Git revisions are also rejected before process creation when
they are empty, option-like, contain whitespace, or contain non-printable
characters. DocSync and context-pack Git adapters repeat the option-injection
check at their public domain boundaries so direct CLI or Python API use cannot
turn a revision into an output-writing Git option.

MCP context packs may write only below `.verify-logs/`, preflight both pack
destinations before the first mutation, and use same-directory atomic
replacement. They always select the local `none` compression backend, so a
repository cannot opt an MCP caller into provider-backed compression. MCP
verification overrides repository-configured artifact and event directories
with a fresh descendant of `.verify-logs/mcp/`; the result reports that root so
follow-up diagnostics can address it explicitly.

MCP context-pack requests also force `--no-live-ratchet`. Live ratchet
recomputation invokes repository-wide file-length and structure scanners whose
configured roots and file reads are not part of this confined MCP boundary. A
repository therefore cannot activate those scanners merely by supplying a
ratchet baseline. The local context-pack CLI retains live recomputation by
default for compatibility in trusted repositories; callers handling an
untrusted checkout must use `--no-live-ratchet` until the general ratchet
scanners adopt equivalent root, file-kind, and aggregate-read controls.

The reusable context reader applies the same sensitive-name, regular-file, and
byte-ceiling rules. File context, context packs, and file estimates are confined
to their workspace root by default. The reader checks metadata before opening,
opens a leaf without following a final symlink where the platform supports it,
rechecks the opened descriptor, and performs one bounded read pass. There is no
MCP-exposed flag that disables these checks.

Verifier manifests are bounded regular UTF-8 inputs. Manifest-controlled log
and exact-fact artifact paths must be workspace-relative and pass the same
symlink, sensitive-name, special-file, and byte-ceiling checks before a parser
reads them. Log selection performs one bounded read rather than trusting the
manifest's path or loading an unbounded file.

Sensitive-name policy covers common cloud, container, Kubernetes, SSH, GPG,
Terraform, environment, credential-store, service-account, private-key, and
secret-file locations. Exact-fact parsing deduplicates paths and applies both a
file-count ceiling and an aggregate byte budget before repository artifacts
reach format-specific parsers.

## Boundary Rules

- `agent_maintainer.mcp.path_safety` owns MCP argument validation and path-kind
  policies.
- `agent_maintainer.mcp.server.McpService` owns the immutable workspace root.
- `agent_context.reading.file_safety` owns reusable sensitive-name and bounded
  file-read policy.
- Domain CLIs remain authoritative for command semantics and must reapply their
  own input/output safety rules where they open files.
- New MCP tools with filesystem arguments must use a declared workspace path
  policy before constructing a command.

## Alternatives Considered

- Bound output only. Rejected because response truncation does not bound the
  initial file read or prevent special-file blocking.
- Canonicalize only `context_file`. Rejected because the other MCP path
  arguments would remain equivalent escape channels.
- Accept absolute paths that happen to resolve under the workspace. Rejected
  because repository-relative arguments are easier to audit and prevent the
  caller from selecting a different local root convention.

## Verification

Tests cover absolute and traversal paths, outside canaries, sensitive names,
symlink-parent escapes, sparse oversized files, FIFOs, device paths, all current
MCP filesystem arguments, captured-root stability after a working-directory
change, context-pack manifest log/artifact canaries, output-directory symlink
redirects, Git-option outside-write canaries, and the absence of a file-injection
argument on context-pack MCP calls. Tests also cover source-tree output canaries,
multi-output preflight, repository-enabled provider compression, verifier-root
symlinks, duplicate exact-fact artifacts, and compact pointer-only child output.
An integration test supplies a valid baseline while replacing the live-ratchet
entry point with a failure sentinel, proving the MCP-generated command cannot
reach repository-wide recomputation.
Hostile-checkout tests place both file and package shadows for
`agent_maintainer` and `docsync` in the child working directory while inheriting
a relative `PYTHONPATH`; neither shadow executes. Process tests cover rapid
stdout beyond the hard ceiling, a silent timeout, and simultaneous stdout and
stderr production without deadlock.
Architecture checks keep the MCP path-policy dependencies explicit.

## Residual Risk

Path validation and the command's eventual domain-level open occur at different
times. The child reader rechecks parent symlinks and the final descriptor, which
blocks repository-controlled static escapes. A hostile local process with
concurrent write access could still race a parent-directory replacement on
platforms without a root-relative, no-follow open primitive. If the threat
model expands to mutually hostile local processes, use an `openat`-style
directory-descriptor walk (or an equivalent platform sandbox) for the entire
path.
