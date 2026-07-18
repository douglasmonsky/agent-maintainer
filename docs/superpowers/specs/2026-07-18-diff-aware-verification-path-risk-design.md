# Diff-Aware Verification Planning And Path-Risk Policy Design

## Status

Approved through the repository's recommended-choice self-approval workflow on
2026-07-18.

## Problem

Agent Maintainer can classify changed files, expose ecosystem facts, suggest
tests, and run fixed verification profiles. It cannot yet connect a concrete
diff to the exact repository units, checks, documentation, architecture proof,
security gates, and review categories that the change requires. Repositories
also lack a declarative way to make sensitive paths demand named evidence.

That gap forces agents to reconstruct policy from prose and broad CI workflows.
It also encourages two unsafe extremes: running everything for every change, or
silently skipping important gates based on incomplete heuristics.

## Goal

Build a provider-neutral verification planner and declarative path-risk policy
as one additive control layer. Given a Git diff, the planner must produce a
deterministic, machine-readable explanation of:

- changed paths and their ecosystem roles;
- affected Python packages, TypeScript workspaces, and Gradle modules;
- matched risk rules;
- required verifier profiles and checks;
- named evidence that is satisfied or missing;
- required review categories; and
- exact recommended commands.

Explicitly required rules may block when enforcement is requested. The planner
must never suppress an existing verifier gate in this phase.

## Non-Goals

- Dynamically removing checks from existing verification profiles.
- Executing selected checks inside the planner.
- Inferring semantic-version bumps or compatibility impact.
- Classifying new versus pre-existing failures.
- Normalizing Playwright, Electron, accessibility, or screenshot artifacts.
- Flake, duration, bundle-size, or startup-performance ratchets.
- Adding another ecosystem provider.
- Reading GitHub labels or other remote review state.

Those remain separate roadmap phases after the planner contract is stable.

## Chosen Approach

Create a dedicated `agent_maintainer.verification_plan` domain and expose it as
`agent-maintainer verify-plan`. The domain consumes existing neutral Git-change
facts, ecosystem classifiers, repository package/workspace evidence, and the
verifier catalog. It owns only planning, policy validation, evidence matching,
and rendering.

This is preferred to extending `assess reviewability`, which is intentionally
advisory, and to teaching `verify` to skip checks dynamically, which could hide
coverage when a policy is incomplete.

## Architecture

The new domain has focused modules:

- `models.py`: immutable policy and report types plus schema constants.
- `policy.py`: strict TOML loading and validation.
- `matching.py`: repository-relative path normalization and glob matching.
- `units.py`: affected Python, TypeScript, Gradle, and repository-root units.
- `planner.py`: rule matching, requirement evaluation, unions, and commands.
- `reporting.py`: deterministic human-readable and JSON output.
- `cli.py`: argument parsing and exit-status behavior.

The root CLI lazily dispatches `verify-plan` to the new domain. A verifier
catalog entry invokes `verify-plan --enforce` only when the default policy file
exists. This makes enforcement available to normal verification without making
the planner a second command runner.

The Tach domain contract declares every cross-domain dependency exactly. The
planner may depend on configuration, catalogs, neutral ecosystem facts, and
bounded setup evidence; those domains do not depend back on the planner.

## Policy File

The default policy path is `.agent-maintainer/path-risk.toml`. Callers may use
`--policy PATH` for inspection and tests. The document is versioned separately
from `pyproject.toml` configuration:

```toml
version = 1

[[rules]]
id = "architecture-policy"
description = "Architecture contract changes require architecture proof."
paths = ["tach.toml", "src/**/tach.domain.toml"]
mode = "required"
profiles = ["precommit"]
checks = ["tach-config", "tach"]
review_categories = ["architecture"]

[[rules.evidence]]
id = "architecture-decision"
kind = "changed-path"
paths = ["docs/architecture/decisions/*.md"]
minimum = 1
message = "Add or update an architecture decision record."
```

### Document Contract

Top-level keys:

- `version`: required integer; only `1` is accepted.
- `rules`: optional array of rule tables; absent is equivalent to empty.

Rule keys:

- `id`: required unique kebab-case identifier.
- `description`: optional non-empty text.
- `paths`: required non-empty repository-relative glob array.
- `mode`: optional `advisory` or `required`; default `advisory`.
- `profiles`: optional verifier profile names.
- `checks`: optional exact verifier check names.
- `review_categories`: optional unique kebab-case labels.
- `evidence`: optional array of evidence tables.

Evidence keys:

- `id`: required identifier unique within its rule.
- `kind`: required; Phase 183 accepts only `changed-path`.
- `paths`: required non-empty repository-relative glob array.
- `minimum`: optional positive integer; default `1`.
- `message`: optional non-empty repair guidance.

Unknown keys are errors. Duplicate identifiers, empty arrays where values are
required, unsupported versions or modes, absolute paths, parent traversal, NUL
characters, and unknown profile or check names are errors. This strictness
prevents misspelled policy from becoming silently ineffective.

### Glob Semantics

All paths use normalized POSIX separators and are relative to the repository
root. `*` matches within one path segment, `**` matches zero or more complete
segments, and `?` matches one non-separator character. Matching is
case-sensitive and does not consult `.gitignore`.

A rule is matched when at least one changed destination path matches one of its
`paths`. Generated and ignored classifications remain eligible for matching so
security rules cannot be bypassed by locating a file under a generated-looking
directory.

## Affected Units

The planner reports the smallest known repository units affected by the diff:

- Python: configured `package_paths`, matched by longest path prefix.
- TypeScript: literal workspace declarations expanded to directories that
  contain `package.json`, then matched by longest path prefix.
- Java/Gradle: module paths derived by existing bounded repository evidence,
  matched by longest path prefix.
- Repository: a stable root unit for unmatched or ambiguous paths.

Each unit contains `kind`, `name`, `root`, and sorted `changed_paths`. A path may
belong to only one unit of a given ecosystem. Ambiguity falls back to the
repository unit and emits an advisory rather than guessing ownership.

## Planning Semantics

Planning follows this order:

1. Read numstat changes through the existing neutral Git adapter.
2. Classify every changed path through registered ecosystem providers.
3. Resolve affected units.
4. Load and validate policy, including verifier profile and check names.
5. Match all rules against all changed paths.
6. Evaluate every named evidence requirement against the same diff.
7. Union profiles, checks, and review categories from matched rules.
8. Sort and deduplicate all output by stable identifiers and paths.
9. Render text or schema-versioned JSON.

Overlapping rules are cumulative. Evidence is scoped to the rule that declares
it. Missing evidence from an advisory rule creates an advisory. Missing evidence
from a required rule creates a blocking finding, but affects the process exit
status only under `--enforce`.

The planner derives recommended commands from selected profiles. It reports
exact selected checks for orchestration and audit, but does not execute them.
Existing verifier profiles remain authoritative for command execution and run
artifacts.

## Report Contract

JSON output has `schema_version = 1` and these stable top-level fields:

- `target`, `base_ref`, `staged`, `policy_path`, and `policy_configured`;
- `changes`;
- `affected_units`;
- `matched_rules`;
- `selected_profiles` and `selected_checks`;
- `review_categories`;
- `requirements`;
- `recommended_commands`;
- `advisories`; and
- `blocking_findings`.

Every requirement reports `rule_id`, `id`, `mode`, `kind`, `paths`, `minimum`,
`matched_paths`, `status`, and `message`. Status is `satisfied` or `missing`.
The report includes no timestamps so identical repository state produces
byte-stable JSON.

Human output presents the same information in bounded sections and ends with
blocking findings or a clear ready result.

## CLI And Exit Status

```text
agent-maintainer verify-plan
  [--target PATH]
  [--base-ref REF]
  [--staged]
  [--policy PATH]
  [--json]
  [--enforce]
```

- `0`: valid plan; without `--enforce`, this includes plans with missing
  required evidence.
- `1`: `--enforce` was requested and required evidence is missing.
- `2`: invalid arguments, policy, repository state, base ref, profile, or check.

When the policy file is absent, the planner returns a valid unconfigured report
with no matched rules. The optional verifier catalog check is not applicable in
that state, preserving existing repositories' behavior.

## Repository Policy Rollout

The initial Agent Maintainer policy protects these surfaces:

- `tach.toml` and colocated Tach domains: architecture checks, an architecture
  review category, focused architecture tests, and an ADR when policy changes.
- dependency manifests and lock files: dependency/security profiles and
  packaging evidence.
- `.github/workflows/**`: workflow policy checks and a CI review category.
- release configuration and public version surfaces: release tests and release
  review.
- secret scanning, security tooling, and risk-policy files: the security profile
  and security review.

Rules should require evidence already expected by repository guidance. Phase 183
does not introduce a blanket ADR requirement for ordinary implementation files.

## Error Handling

Errors name the policy path, rule or evidence identifier, field, and rejected
value without printing file contents. Git failures preserve the target ref in
their message. An unresolved workspace pattern or ambiguous ownership is an
advisory; invalid policy is an error. Output remains bounded and never includes
environment values, credentials, or verifier log contents.

## Testing

Implementation uses test-driven development. Required proof includes:

- strict policy parsing and every rejection class;
- segment-aware glob matching, including `**` and path normalization;
- Python, TypeScript, Gradle, and root affected-unit resolution;
- overlapping rules and deterministic unions;
- advisory versus required evidence behavior;
- absent policy and invalid Git ref behavior;
- stable JSON schema and bounded text output;
- CLI exit statuses with and without `--enforce`;
- catalog applicability and command construction;
- Tach exact-boundary checks;
- package metadata and public documentation assertions; and
- the repository's full pre-push verification suite.

No network access or real private repository data is required for unit or CLI
tests. Fixtures use synthetic paths and minimal manifests.

## Success Criteria

Phase 183 is complete when:

1. A mixed Python, TypeScript, and Gradle diff yields deterministic affected
   units and exact selected evidence.
2. A required path rule fails under `--enforce` when named evidence is absent
   and passes when the evidence is present in the diff.
3. Advisory rules never block.
4. Invalid or misspelled policy cannot pass silently.
5. Existing verification profiles retain all current gates.
6. The JSON contract is documented and covered by exact assertions.
7. Agent Maintainer's own initial path-risk policy passes locally and in hosted
   protected checks.
