# TypeScript Package And Workspace Evidence Design

Status: approved for implementation planning

## Goal

Implement Phase 178 as advisory, provenance-rich package-manager and workspace
evidence for TypeScript and JavaScript repositories. The setup assessment and
setup advisor may explain observed repository declarations, but no detected
value may select a package manager, enable a provider, infer package ownership,
or become a subprocess argument.

## Context

The experimental TypeScript provider already executes only explicit root and
workspace command arrays from `MaintainerConfig`. Existing setup assessment
collects root `package.json` script names, while setup-advisor guidance tells a
user to map those scripts into reviewed commands without guessing a package
manager.

Phase 178 fills the remaining evidence gap. It observes recognized root
metadata, lockfiles, workspace declarations, and explicit Agent Maintainer
workspace configuration. TypeScript remains experimental and advisory after
this phase.

## Decisions

- Package and workspace detection belongs to the assessment boundary, not the
  TypeScript provider or executor.
- Detection is declaration-only. Workspace globs remain literal and nested
  packages are not scanned to infer ownership.
- Setup assessment JSON exposes complete typed facts. Setup-advisor text adds
  concise explanations and review prompts.
- Doctor remains configuration-focused and does not scan repository metadata in
  this phase.
- Setup track, preset, provider enablement, and explicit configured commands do
  not change based on detected evidence.
- The implementation adds no dependency. PyYAML is already a runtime
  dependency and may parse `pnpm-workspace.yaml` safely.

## Scope

### Package-manager signals

Recognize only these root-level signals:

| Source | Field or filename | Manager |
|---|---|---|
| `package.json` | `packageManager` | Parsed declaration |
| `package.json` | `devEngines.packageManager.name` and `.version` | Parsed Corepack declaration |
| repository root | `package-lock.json` | npm |
| repository root | `npm-shrinkwrap.json` | npm |
| repository root | `pnpm-lock.yaml` | pnpm |
| repository root | `yarn.lock` | Yarn |
| repository root | `bun.lock` | Bun |
| repository root | `bun.lockb` | Bun, legacy lockfile |

Normalize recognized manager names to `npm`, `pnpm`, `yarn`, or `bun` while
retaining the original observed declaration value. Multiple signals for one
manager are corroborating facts. Signals for different managers remain present
and produce an ambiguity issue; the detector never chooses a winner.

The top-level `packageManager` value must be a string containing a recognized
name and a non-empty descriptor separated by `@`. The
`devEngines.packageManager` value must be an object with string `name` and
non-empty string `version` fields. A present declaration with any other shape
is invalid evidence. Other `devEngines.packageManager` fields are preserved by
the repository but remain outside this detector's scope.

### Workspace declarations

Recognize only:

- `package.json#workspaces` as an array of strings;
- `package.json#workspaces.packages` as an array of strings;
- `pnpm-workspace.yaml#packages` as an array of strings; and
- `[tool.agent_maintainer.workspaces.<name>]` tables in `pyproject.toml`.

Record package and pnpm workspace patterns literally in deterministic order.
Record each explicit Agent Maintainer workspace name and its exact table path.
Do not expand globs, inspect matched directories, read nested `package.json`
files, or infer which package owns a script or command.

When a workspace list mixes strings with invalid entries, retain the valid
literal strings and add one `invalid-workspace-declaration` issue for that
field. A present workspace container with no supported list shape produces the
same issue and no declaration.

### Advisory issues

Missing optional files and fields are normal and produce no issue. Present but
invalid evidence produces stable advisory issue kinds:

- `malformed-package-json`
- `malformed-pnpm-workspace`
- `malformed-agent-maintainer-config`
- `invalid-package-manager-declaration`
- `unsupported-package-manager`
- `conflicting-package-managers`
- `invalid-workspace-declaration`

Every issue includes its source path, source field when available, and a concise
message. Malformed metadata does not abort the bounded repository scan or hide
other valid root-level signals.

## Architecture

### Assessment-owned detector

Create `src/agent_maintainer/assess/package_workspace_evidence.py`. Its public
function accepts the resolved repository root and returns one immutable
`PackageWorkspaceEvidence` aggregate. The detector performs fixed root-file
reads only and has no command-execution, configuration-mutation, network, or
nested-directory responsibility.

`collect_evidence()` calls the detector once and attaches its return value to
`RepoEvidence`. Existing Git-backed or filesystem-backed bounded file scanning
continues to supply the rest of the repository facts.

### Typed public evidence

Add frozen dataclasses in `src/agent_maintainer/assess/models.py`:

- `PackageManagerSignal`
  - `manager: str`
  - `kind: str`
  - `source_path: str`
  - `source_field: str`
  - `value: str`
- `WorkspaceDeclaration`
  - `kind: str`
  - `name: str`
  - `source_path: str`
  - `source_field: str`
  - `patterns: tuple[str, ...]`
- `PackageWorkspaceIssue`
  - `kind: str`
  - `source_path: str`
  - `source_field: str`
  - `message: str`
- `PackageWorkspaceEvidence`
  - `manager_signals: tuple[PackageManagerSignal, ...]`
  - `workspace_declarations: tuple[WorkspaceDeclaration, ...]`
  - `issues: tuple[PackageWorkspaceIssue, ...]`
  - `unambiguous_manager: str`
  - `ambiguous: bool`

Add `package_workspace: PackageWorkspaceEvidence` to `RepoEvidence` with an
empty aggregate default so existing direct constructors remain compatible.
The existing dataclass serializer exposes nested evidence without a second
serialization path.

`unambiguous_manager` is populated only when all recognized manager signals
agree and no unsupported or invalid manager declaration makes the evidence
ambiguous. `ambiguous` is true for conflicting recognized managers or an
invalid/unsupported explicit manager declaration. It is not a package-manager
selection and has no execution semantics.

### Setup-advisor integration

Extend `src/agent_maintainer/assess/setup_advisor.py` with small pure rendering
helpers. Reasons summarize corroborated signals, workspace declarations, and
ambiguity while retaining the existing scan summary. Agent prompts ask the user
to review conflicts and map existing scripts into explicit root or workspace
commands.

These helpers run even when a TypeScript-only repository remains on the
`inspect` track. They do not change `_recommended_track()`,
`_recommended_preset()`, TypeScript gate enablement, or the current script-name
signal rules.

## Safety Invariants

- `TypeScriptProvider`, provider metadata, configuration coercion, catalogs, and
  executor code do not import package/workspace evidence.
- Detected manager names, versions, script names, workspace patterns, and issue
  text never become `Check.command`, `required_executable`, or configuration
  defaults.
- Explicit root and workspace commands behave identically when metadata is
  missing, malformed, or contradictory.
- No package-manager binary or package script is executed during detection,
  setup assessment, or setup-advisor rendering.
- Unsupported or ambiguous evidence remains visible and advisory.
- Root metadata is the only repository metadata read for this phase; nested
  package ownership remains out of scope.

## Testing Strategy

Follow red-green-refactor for every behavior.

### Detector tests

- one test for each recognized declaration and lockfile signal;
- agreement between multiple signals for the same manager;
- conflicts between declarations and lockfiles;
- unsupported and invalid manager declarations;
- missing and malformed JSON, YAML, and TOML;
- both supported `package.json` workspace shapes;
- pnpm workspace patterns;
- explicit Agent Maintainer workspace names;
- invalid workspace field shapes;
- deterministic ordering and provenance fields; and
- proof that nested package metadata is ignored and globs remain literal.

### Integration tests

- `collect_evidence()` includes the typed aggregate and preserves existing
  `package_scripts` behavior;
- setup-advisor reasons and prompts describe corroborated and ambiguous facts;
- TypeScript-only repositories remain on the current inspect/manual-review
  path; and
- existing provider and catalog tests prove command construction remains
  explicit-config-only.

Use temporary repository fixtures with synthetic metadata only. Do not include
private package names, credentials, registry tokens, or real user data.

## Documentation

- Document the new evidence in `docs/setup-advisor.md` and
  `docs/provider-status.md`.
- Add a completed Phase 178 page and advance the compact and durable TypeScript
  roadmaps to the next unnumbered Knip slice.
- Update the full roadmap blueprint and DocSync trace/tests where public claims
  change.
- Preserve Phase 177 as complete and TypeScript/React as experimental.

No architecture policy, dependency, workflow, or configuration schema change is
required.

## Delivery Slices

1. Add the typed detector, evidence collection integration, and focused tests.
2. Add setup-advisor rendering, ambiguity guidance, and execution-boundary
   regressions.
3. Complete Phase 178 documentation, roadmap updates, and DocSync coverage.

Each slice is independently reviewed and committed. After focused tests and
hooks pass, run one fresh full verifier profile before publishing.

## Acceptance Criteria

- Setup assessment JSON reports recognized package-manager and workspace facts
  with file-and-field provenance.
- Conflicts, malformed metadata, unsupported managers, and invalid workspace
  shapes are visible as bounded advisory issues.
- Workspace patterns remain declarations rather than inferred package owners.
- Setup advisor explains the facts without changing track, preset, enablement,
  configuration, or commands.
- TypeScript provider execution remains exclusively explicit-command driven.
- Focused tests, DocSync, repository hooks, the full verifier, and hosted CI all
  pass.
