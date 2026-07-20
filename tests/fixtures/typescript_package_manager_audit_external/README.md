# TypeScript package-manager audit projections

These files are sanitized, bounded offline projections tied to public repository
heads. They exercise the same JSON boundary as a configured command without
cloning a repository, installing a package manager, accessing the network, or
committing a dependency tree or full captured report.

The npm projection is tied to
`jsynowiec/node-typescript-boilerplate` at
`550dfd2a976d69254ed71eb6f5a6c5ee20060807`. The pnpm projection is tied to
`vitest-dev/eslint-plugin-vitest` at
`7c697f8a53d7d7551b00ef11217d58cd45a0cf7d`. The report hash and byte count
cover the canonical JSON serialization used by the offline replay test.

Yarn and Bun currently have synthetic contract fixtures only. A stable public
capture may be added later without changing the normalized contract. These
projections are advisory evidence and do not promote the TypeScript provider to
a blocking security gate.
