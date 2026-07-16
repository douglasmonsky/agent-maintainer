<!-- docsync:object docs.provider_contribution_guide.overview -->
# Provider Contribution Guide

Agent Maintainer can grow beyond Python only if new ecosystem support stays
coherent with the existing repair loop. A provider is not just a set of
commands. It should teach Agent Maintainer how a language ecosystem classifies
files, reports problems, exposes setup health, and gives coding agents compact
repair facts.

Python is the core reference provider. It may remain richer than experimental
providers. Do not weaken Python behavior to make another ecosystem fit a
lowest-common-denominator abstraction.

Related reading:

- [Polyglot Ecosystem Provider Roadmap](roadmap/polyglot-ecosystem-providers.md)
- [Experimental TypeScript/JavaScript Provider](typescript-javascript-provider.md)
- [Diagnostics and Repair Loop](diagnostics-repair-loop.md)
- [Supported Scans and Agent Use](supported-scans-and-agent-use.md)

## Contribution Model

New language support should land as a built-in experimental provider through
normal pull request review.

Do not add external provider package discovery during beta. The current
decision is recorded in
[`2026-07-02-provider-api-stability.md`](architecture/decisions/2026-07-02-provider-api-stability.md).
Built-in experimental providers remain the contribution path until the internal
seam has survived real use outside this repository.

The current registry contains the Python core/reference provider plus built-in
experimental TypeScript/JavaScript and Java/Gradle providers. Java/Gradle is
disabled by default and currently exposes explicit checked-wrapper groups,
reviewed setup/native ratchets, and static doctor support; it is not a public
provider API or a feature-parity claim.

Provider additions should be small and phased:

1. Classify files and document unsupported layouts.
2. Add explicit-command checks.
3. Add doctor hints.
4. Add fixture or scaffold smoke tests.
5. Add structured parsers for exact repair facts.
6. Add coverage, dependency, security, or test-intelligence adapters only when
   the earlier pieces are stable.

## Maturity Levels

| Level | Meaning |
|---|---|
| Internal | Built into package internals; not documented as stable. |
| Experimental | Available for early use; gaps and breaking changes expected. |
| Supported | Has fixtures, doctor support, docs, parsers, and CI coverage. |
| Core | Part of the primary compatibility contract. Python starts here. |

Experimental providers must be explicit about gaps. A provider can be useful
without matching every Python capability.

## Required Shape

A new provider should include:

- Provider module under `src/agent_maintainer/ecosystems/<name>/`.
- File classifier for source, tests, generated files, config, docs, and
  dependency files.
- Ecosystem-specific ignore rules.
- Suppression classifier when the ecosystem has meaningful inline or config
  suppressions.
- Minimal profile-aware check generation.
- Doctor capability detection and repair hints.
- Documentation page.
- Fixture tree or fixture-style tests.
- Structured parser fixtures for linter, type checker, or test output when
  available.
- Clear maturity label.
- Security and artifact-sensitivity review for generated logs and reports.
- Coverage story, even if coverage begins advisory-only.
- Statement of unsupported package managers, build tools, test runners, or
  repo layouts.
- Agent guidance snippets only when they are compact and actionable.

Optional pieces can follow later:

- Starter files for `agent-maintainer init`.
- Coverage/diff-coverage adapters.
- Dependency hygiene or vulnerability checks.
- Mutation or property-test guidance.
- Test-intelligence integration.
- Ratchet dimensions.
- Static HTML report cards.

## Check Design Rules

Provider checks should use the existing `Check` model and executor behavior.
They should not implement their own subprocess runner, log layout, timeout
policy, status taxonomy, or output truncation.

Good provider checks:

- Use command arrays, not shell strings.
- Are profile-aware.
- Declare required executables and required paths.
- Produce optional skips when explicitly disabled or not configured.
- Write logs and structured artifacts under the normal run-scoped diagnostics
  layout.
- Keep terminal and hook output compact.
- Prefer exact repair facts over long raw transcripts.

Avoid:

- Package-manager autodetection before fixtures prove it works.
- Silent guessing of commands.
- Renaming stable Python checks to satisfy a generic model.
- Adding global config fields before provider ownership is clear.
- Making every provider implement every Python capability.

## Classification Rules

Provider classifiers should answer what a file is, not whether a command should
run. At minimum, classify:

- Source files.
- Test files.
- Generated files.
- Dependency manifests and locks.
- Tool config files.
- Documentation.
- Ignored build, cache, vendored, or dependency directories.

Classification should be conservative. If a provider cannot classify a path
with confidence, it should return no classification rather than inventing a
role. Later policy checks can combine provider classification with explicit
user configuration.

## Doctor Expectations

Doctor support should explain setup health without becoming noisy.

Disabled providers should normally stay silent. Enabled providers should report:

- Whether required commands are configured.
- Whether configured executable names are available on `PATH` or in
  repo-local tool directories such as `node_modules/.bin`.
- Whether required config files or source roots are missing.
- The smallest useful repair command or configuration change.

Warnings should be actionable. Avoid inventorying disabled tools.

## Structured Parser Expectations

Structured parsers should convert tool output into compact repair facts:

- file path;
- line and column when present;
- rule or diagnostic code when present;
- severity;
- short message.

Parsers should tolerate malformed output and fall back to the normal bounded
raw-log summary. They must not print full raw logs into agent-facing summaries.

## Tests

Provider pull requests should include focused tests before broad verifier runs.

Required tests:

- File classification for source, tests, generated files, ignored paths, config
  files, docs, and dependency manifests.
- Check generation for enabled and disabled provider states.
- Profile membership for provider checks.
- Optional skip behavior when commands are missing or disabled.
- Doctor pass/warn cases.
- Structured parser sample outputs when parsers exist.
- Fixture or scaffold smoke coverage for the smallest meaningful repo layout.

Regression tests should protect Python behavior when provider internals change.
Do not add broad snapshots unless the output is intentionally part of the
compatibility contract.

## Documentation Checklist

A provider documentation page should include:

- Maturity level.
- How to enable it.
- Example config.
- Default profile membership.
- What it checks.
- What it deliberately does not check yet.
- Tool output formats supported for compact summaries or exact facts.
- Doctor behavior.
- Unsupported package managers, test runners, or layouts.
- Links to diagnostics, repair-loop, and optional-gate docs where relevant.

## Promotion Checklist

Before moving a provider from experimental to supported, verify:

- File classification covers common real-world layouts.
- Doctor catches common setup mistakes.
- Fixture or scaffold smoke tests exercise initialization and verification.
- Structured parsers exist for the primary failure outputs.
- Documentation states limitations clearly.
- CI runs provider tests.
- Agent-facing output remains compact.
- Python behavior and Python characterization tests remain unchanged.

## Review Questions

Review provider PRs with these questions:

- Does this keep the core framework responsible for orchestration and
  diagnostics?
- Does provider code own only ecosystem-specific knowledge?
- Does it avoid hidden command guessing?
- Does it preserve current Python behavior?
- Does it fail closed when configuration is ambiguous?
- Are raw logs kept in artifacts instead of agent context?
- Can a future provider copy this pattern without inheriting accidental
  assumptions from one ecosystem?
<!-- docsync:object.end docs.provider_contribution_guide.overview -->
