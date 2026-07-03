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
```

Default profiles are:

| Check | Default Profiles |
|---|---|
| `typescript-lint` | `precommit`, `full`, `ci` |
| `typescript-typecheck` | `full`, `ci` |
| `typescript-test` | `full`, `ci` |

If `enable_typescript = true` but a command is empty, the corresponding check is
reported as an optional skip. Agent Maintainer will not guess the package
manager or invent a command.

`doctor` stays silent when the provider is disabled. When the provider is
enabled, `doctor` reports whether TypeScript commands are configured and whether
configured command executables are available on `PATH`, including repo-local
`node_modules/.bin`.

## Structured Output

Agent Maintainer can extract compact summaries and exact repair facts from
configured-command output:

- `typescript-typecheck`: `tsc --pretty false` style diagnostics such as
  `src/app.ts(4,9): error TS2322: ...`;
- `typescript-lint`: ESLint JSON formatter output;
- `typescript-test`: Jest-compatible JSON output with `testResults` and
  `assertionResults`, including Vitest/Jest JSON reporter shapes.

These parsers are repair-loop helpers. They do not require new config fields,
and malformed output falls back to the normal bounded raw-log summary.

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
Structured repair facts currently expect stable JSON or TypeScript
compiler-style output; arbitrary human-oriented transcripts stay bounded raw
logs.

Frameworks are classified conservatively. `Next.js`, `Vite`, `Astro`,
`SvelteKit`, and monorepo workspace layouts are not inferred into framework
specific default checks, generated-file rules, coverage adapters, or dependency
policies. Configure the repository's own scripts first, then use
`assess reviewability` to inspect advisory changed-file evidence.

Coverage, dependency/security, mutation, and blocking reviewability adapters are
not implemented for TypeScript/JavaScript yet. The provider should remain
experimental until these surfaces have fixture and real-repo evidence.

## Limitations

- No package-manager autodetection.
- No generated starter files yet.
- No structured parser for coverage output or arbitrary non-JSON test
  transcripts.
- No TypeScript coverage, mutation, dependency, or security adapter.
- No public plugin API.
- No TypeScript reviewability gate is blocking by default.

Python remains the core/reference provider. TypeScript support starts smaller on
purpose so the provider seam can prove itself before deeper ecosystem features
are added.

Read the [Provider Contribution Guide](provider-contribution-guide.md) before
adding or promoting provider capabilities.
