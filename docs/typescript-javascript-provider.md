<!-- docsync:object docs.typescript_provider.overview -->
# Experimental TypeScript/JavaScript Provider

Agent Maintainer includes an experimental TypeScript/JavaScript ecosystem
provider. It is disabled by default and only runs commands that the repository
configures explicitly.

The provider exists to validate the ecosystem-provider architecture without
weakening Python behavior or pretending every JavaScript repository uses the
same package manager, linter, test runner, or build layout.

## Configuration

Enable the provider by supplying explicit commands:

```toml
[tool.agent_maintainer]
enable_typescript = true
typescript_lint_command = ["npm", "run", "lint"]
typescript_typecheck_command = ["npm", "run", "typecheck"]
typescript_test_command = ["npm", "test", "--", "--runInBand"]
```

For pnpm projects, keep the same explicit-command shape:

```toml
[tool.agent_maintainer]
enable_typescript = true
typescript_lint_command = ["pnpm", "run", "lint"]
typescript_typecheck_command = ["pnpm", "run", "typecheck"]
typescript_test_command = ["pnpm", "run", "test"]
typescript_knip_command = ["pnpm", "exec", "knip", "--reporter", "json"]
```

For Vite/Vitest projects, prefer repository scripts over inferred commands:

```toml
[tool.agent_maintainer]
enable_typescript = true
typescript_lint_command = ["npm", "run", "lint"]
typescript_typecheck_command = ["npm", "run", "typecheck"]
typescript_test_command = ["npm", "run", "test", "--", "--run"]
```

Command arrays are passed directly to subprocess execution. They are not shell
strings.

Profile membership is configurable:

```toml
[tool.agent_maintainer]
typescript_lint_profiles = ["precommit", "full", "ci"]
typescript_typecheck_profiles = ["full", "ci"]
typescript_test_profiles = ["full", "ci"]
typescript_knip_profiles = ["full", "ci"]
```

Default profiles are:

| Check | Default Profiles |
|---|---|
| `typescript-lint` | `precommit`, `full`, `ci` |
| `typescript-typecheck` | `full`, `ci` |
| `typescript-test` | `full`, `ci` |
| `typescript-knip` | `full`, `ci` |

`typescript_knip_profiles` defaults to `full` and `ci`. Knip stays out of
`precommit` by default because it normally analyzes the whole repository.

If `enable_typescript = true` but a command is empty, the corresponding check is
reported as an optional skip. Agent Maintainer will not guess the package
manager or invent a command.

`doctor` stays silent when the provider is disabled. When the provider is
enabled, `doctor` reports whether TypeScript commands are configured and whether
configured command executables are available on `PATH`, including repo-local
`node_modules/.bin`. Empty-command doctor hints point to stable output formats
that improve repair facts: ESLint JSON, `tsc --pretty false`, Jest/Vitest JSON,
and existing `coverage-summary.json` or `lcov.info` artifacts. After commands
are configured, `doctor` may emit a non-blocking `PASS` advisory row when command
text does not visibly mention those parser-friendly outputs; the row is guidance
only and still does not infer package managers or invent commands.

## Structured Output

Agent Maintainer can extract compact summaries and exact repair facts from
configured-command output:

- `typescript-typecheck`: `tsc --pretty false` style diagnostics such as
  `src/app.ts(4,9): error TS2322: ...`;
- `typescript-lint`: ESLint JSON formatter output;
- `typescript-test`: Jest-compatible JSON output with `testResults` and
  `assertionResults`, Vitest task-style JSON fixtures, Istanbul
  `coverage-summary.json`, and LCOV `lcov.info` artifacts;
- `typescript-knip`: Knip `--reporter json` output for unused files, exports,
  types, dependencies, binaries, unlisted dependencies, and unresolved imports
  or binaries;
- `osv-scanner`: OSV Scanner v2 output from the existing ecosystem-neutral
  manual gate.

Knip findings are sorted before Agent Maintainer retains at most 500 normalized
findings. Compact failed-check summaries contain at most 50 total lines,
including an omission marker when needed; exact context packs keep their
existing 5-fact-per-check bound. Line and column values are preserved exactly
as Knip reports them. Cycles, duplicates, catalogs, enum members, and
namespace/class member categories are ignored in this phase.

Only repository-relative paths are emitted. Absolute and parent-traversal paths
are rejected so local machine paths cannot enter summaries or repair context.

Agent Maintainer honors the configured Knip command's exit status. Exit `0`
passes, while exits `1` and `2` fail through the normal check runner. It does
not add `--no-exit-code`, thresholds, reporter flags, or version enforcement.
Pin Knip through the repository's exact dependency or lockfile and include
`--reporter json` in the explicit command when structured facts are wanted.

These parsers are repair-loop helpers. They do not require new config fields,
and malformed output falls back to the normal bounded raw-log summary.

## Phase 180 OSV Boundary

Phase 180 OSV dependency facts are complete. TypeScript support uses the
existing ecosystem-neutral `osv-scanner` gate; it does not add a provider
command or infer npm, pnpm, Yarn, or Bun behavior. The global gate remains
explicitly enabled and runs in the `manual` profile by default.

The shared OSV Scanner v2 parser emits one fact per OSV alias group. Facts
include the package ecosystem, name, version, advisory aliases, safe lockfile
provenance, and fixed versions when OSV range events provide them. Valid
repository-relative paths can become context targets. Absolute paths, parent
traversal, and Windows drive paths are redacted to a safe filename label.

The parser retains at most 500 normalized findings, failed-check summaries
contain at most 50 total lines, and context packs keep the existing five facts
per check. Synthetic tests cover malformed neighbors and unsafe paths. Bounded
projections from pinned pnpm `eslint-plugin-vitest` and npm
`node-typescript-boilerplate` revisions provide public compatibility evidence;
they do not promote the provider or add a default check.

The roadmap records that package-manager audit facts are the next parity slice.
Mutation, changed-line coverage gates, and blocking reviewability remain unsupported.
TypeScript/JavaScript remains experimental.

For current maturation evidence and promotion criteria, see
[TypeScript Provider Maturation Notes](case-studies/typescript-provider-maturation.md).

## Classification

The provider classifies common TypeScript and JavaScript paths:

- source files: `.ts`, `.tsx`, `.js`, `.jsx`, `.mjs`, `.cjs`;
- test files: `.test.*`, `.spec.*`, `__tests__`, `tests`, and `specs`;
- ignored or generated paths: `node_modules`, build outputs, coverage outputs,
  `__generated__`, and generated folders;
- dependency and config files: `package.json`, lockfiles, `tsconfig.json`,
  ESLint, Biome, Vite, Vitest, Jest, and Next config files.

Classification prepares later policy adapters without changing existing
Python-backed reviewability behavior.

## Unsupported Surface

The provider is intentionally explicit-command first. `npm`, `pnpm`, `yarn`, and
`bun` are supported only when the repository supplies exact command arrays.
Agent Maintainer does not infer package manager behavior from lockfiles,
`packageManager`, Corepack settings, workspace manifests, or local scripts.

Test runners are not auto-detected. `Jest`, `Vitest`, `Playwright`, `Cypress`,
`Mocha`, and other runners must be wired through `typescript_test_command`.
Structured repair facts currently expect stable JSON, TypeScript
compiler-style output, stable Jest/Vitest test JSON, or explicit
Istanbul/LCOV coverage artifacts; arbitrary human-oriented transcripts stay
bounded raw logs.

Frameworks are classified conservatively. `Next.js`, `Vite`, `Astro`,
`SvelteKit`, and monorepo workspace layouts are not inferred into framework
specific default checks, generated-file rules, coverage commands, or dependency
policies. Configure the repository's own scripts first, then use
`assess reviewability` to inspect advisory changed-file evidence.

Workspace command ownership is explicit. Configure root TypeScript commands only
when they intentionally cover packages you want Agent Maintainer to verify. For
package-specific checks, add commands under
`[tool.agent_maintainer.workspaces.<name>]`; Agent Maintainer will run only the
workspace TypeScript commands you configure and will not infer nested package
commands. Workspace Knip commands use the root `typescript_knip_profiles`
selection and stable names such as `typescript-knip:web`.

Coverage summaries and LCOV files can improve `typescript-test` repair facts
when a repository already produces those artifacts, Knip can improve
unused-code and dependency repair facts, and the ecosystem-neutral OSV gate can
provide dependency vulnerability facts. TypeScript coverage enforcement,
package-manager audit, mutation, and blocking reviewability adapters are not
implemented yet. The provider should remain experimental until these surfaces
have fixture and real-repo evidence.

## Limitations

- No package-manager autodetection.
- No generated starter files yet.
- No structured parser for arbitrary human-oriented test or coverage
  transcripts.
- No TypeScript coverage command adapter, mutation adapter, or package-manager
  audit adapter.
- No public plugin API.
- No TypeScript reviewability gate is blocking by default.

Python remains the core/reference provider. TypeScript support starts smaller on
purpose so the provider seam can prove itself before deeper ecosystem features
are added.

Read the [Provider Contribution Guide](provider-contribution-guide.md) before
adding or promoting provider capabilities.
<!-- docsync:object.end docs.typescript_provider.overview -->
