# Experimental Go Provider

Agent Maintainer includes an experimental Go ecosystem provider. It is disabled
by default and only runs commands configured by the repository.

This provider validates the ecosystem-provider architecture outside Python and
Node-style package-manager workflows. It does not assume every Go repository
uses the same lint, vet, test, or workspace setup.

Related reading:

- [Provider Contribution Guide](provider-contribution-guide.md)
- [Polyglot Ecosystem Provider Roadmap](roadmap/polyglot-ecosystem-providers.md)
- [Diagnostics and Repair Loop](diagnostics-repair-loop.md)

## Configuration

Enable the provider and supply explicit commands:

```toml
[tool.agent_maintainer]
enable_go = true
go_format_command = ["gofmt", "-l", "."]
go_vet_command = ["go", "vet", "./..."]
go_test_command = ["go", "test", "./..."]
```

Command arrays are passed directly to subprocess execution. They are not shell
strings.

Profile membership is configurable:

```toml
[tool.agent_maintainer]
go_format_profiles = ["precommit", "full", "ci"]
go_vet_profiles = ["full", "ci"]
go_test_profiles = ["full", "ci"]
```

Default profiles are:

| Check | Default profiles |
|---|---|
| `go-format` | `precommit`, `full`, `ci` |
| `go-vet` | `full`, `ci` |
| `go-test` | `full`, `ci` |

If `enable_go = true` but a command is empty, the corresponding check reports
an optional skip. Agent Maintainer will not guess a Go command.

## Classification

The provider classifies common Go paths:

- source files: `.go`;
- tests: `_test.go`;
- generated files: `.pb.go`, `_gen.go`, `_generated.go`, and generated
  folders;
- dependency files: `go.mod`, `go.sum`, `go.work.sum`;
- config files: `go.work`, `go.env`, `.golangci.yml`, `.golangci.yaml`;
- ignored paths: `vendor`, build outputs, coverage outputs, and VCS folders.

Classification is internal in this phase. It prepares later policy adapters
without changing existing Python policy behavior.

## Limitations

- No Go starter files yet.
- No package or workspace autodetection.
- No structured parser for `go test`, `go vet`, or `golangci-lint` output.
- No Go coverage, mutation, dependency, or security adapter.
- No public plugin API.

Python remains the core/reference provider. Go support starts smaller on
purpose so the provider seam can prove itself across a second non-Python
ecosystem before deeper capabilities are added.
