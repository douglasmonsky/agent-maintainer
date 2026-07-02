# Experimental TypeScript/JavaScript Provider

Agent Maintainer includes an experimental TypeScript/JavaScript ecosystem
provider. It is disabled by default and runs only commands configured by the
repository.

The provider exists to validate ecosystem-provider architecture without
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

| Check | Default profiles |
|---|---|
| `typescript-lint` | `precommit`, `full`, `ci` |
| `typescript-typecheck` | `full`, `ci` |
| `typescript-test` | `full`, `ci` |

If `enable_typescript = true` but a command is empty, the corresponding check is
reported as an optional skip. Agent Maintainer will not guess a package manager
or invent a command.

`doctor` stays silent when the provider is disabled. When the provider is
enabled, `doctor` reports whether any TypeScript commands are configured and
whether configured command executables are available on `PATH`, including
repo-local `node_modules/.bin`.

## Structured Output

Agent Maintainer can extract compact summaries and exact repair facts from
configured-command outputs:

- `typescript-typecheck`: `tsc --pretty false` style diagnostics such as
  `src/app.ts(4,9): error TS2322: ...`;
- `typescript-lint`: ESLint JSON formatter output;
- `typescript-test`: Jest-compatible JSON output with `testResults` and
  `assertionResults`, including Vitest/Jest JSON reporter shapes.

These parsers are advisory repair-loop helpers. They do not require new config
fields, and malformed output falls back to the normal bounded raw-log summary.

For current maturation evidence and promotion criteria, see
[TypeScript Provider Maturation Notes](case-studies/typescript-provider-maturation.md).

## Classification

The provider classifies common TypeScript and JavaScript paths:

- source files: `.ts`, `.tsx`, `.js`, `.jsx`, `.mjs`, `.cjs`;
- tests: `.test.*`, `.spec.*`, `__tests__`, `tests`, `specs`;
- ignored/generated paths: `node_modules`, build outputs, coverage outputs,
  `__generated__`, generated folders;
- dependency and config files: `package.json`, lockfiles, `tsconfig.json`,
  ESLint, Biome, Vite, Vitest, Jest, and Next config files.

Classification is internal in this phase. It prepares later policy adapters
without changing existing Python policy behavior.

## Limitations

- No package-manager autodetection.
- No generated starter files yet.
- No structured parser for coverage output or non-JSON test transcripts.
- No TypeScript coverage, mutation, dependency, or security adapter.
- No public plugin API.

Python remains the core/reference provider. TypeScript support starts smaller on
purpose so the provider seam can prove itself before deeper ecosystem features
are added. See [Provider Contribution Guide](provider-contribution-guide.md)
before adding or promoting provider capabilities.
