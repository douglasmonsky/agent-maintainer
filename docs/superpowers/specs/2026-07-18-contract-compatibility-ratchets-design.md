# Contract And Compatibility Ratchets Design

**Date:** 2026-07-18

**Status:** Draft for written-spec review

**Scope:** Phase 184 contract discovery, semantic compatibility classification,
contract and package version obligations, deterministic baselines, CLI and
verifier integration, and Agent Maintainer dogfood coverage

## Problem

Agent Maintainer can map a diff to required evidence, but it cannot yet explain
whether that diff changes a public configuration, CLI, Python API,
IPC/JSON-RPC, or persistence contract. Repositories therefore rely on reviewers
to notice removals, renamed fields, requiredness changes, incompatible types,
and stale schema versions. The same review must also infer whether the package
version and migration guidance are sufficient.

Phase 184 adds a repository-owned semantic ratchet. It prevents accidental
contract drift while preserving Agent Maintainer's current pre-1.0 policy: an
intentional beta break remains allowed when the exact compatibility finding,
contract revision, package version, migration evidence, and review decision
agree.

## Goals

- Detect semantic changes to configured contract surfaces without treating raw
  source hashes as contracts.
- Normalize configuration, CLI, nominated Python API, JSON Schema,
  IPC/JSON-RPC, and persistence facts behind one comparison model.
- Classify exact changes as breaking, compatible additive, or review-required.
- Require contract-local revisions and recommend or validate a minimum package
  bump under repository-owned version policy.
- Make intentional migration evidence explicit and machine-verifiable.
- Produce bounded deterministic human, JSON, and repair-fact output.
- Integrate one optional blocking verifier gate without suppressing existing
  checks or creating a reduced test executor.
- Dogfood the feature on Agent Maintainer's current documented surfaces.

## Non-Goals

- No cross-version compatibility promise for Agent Maintainer before 1.0.
- No automatic source rewrite, schema migration, changelog generation, version
  bump, or baseline acceptance.
- No reflection over every module shipped in a wheel.
- No arbitrary target-module imports, repository command execution, network
  access, or shell evaluation during extraction.
- No OpenAPI, protobuf, database-engine migration, or arbitrary-language ABI
  support in Phase 184.
- No compatibility inference for unsupported JSON Schema constructs.
- No failure-history clustering; Phase 185 consumes this phase's stable repair
  facts and owns recurring failure intelligence.

## Chosen Approach

Build one semantic compatibility kernel with isolated extractor adapters. Each
extractor emits a normalized descriptor. The kernel owns comparison, version
obligations, decisions, reporting, and baseline freshness without knowing how
the descriptor was produced.

This is preferred over source-diff heuristics, which cannot reliably understand
aliases, defaults, requiredness, or schema semantics, and over separate
surface-specific ratchets, which would duplicate policy, output, version, and
failure behavior.

## Support Policy

The ratchet distinguishes accidental drift from intentional beta evolution; it
does not replace `docs/api-support-policy.md`.

- Without contract policy, the verifier gate is absent and discovery is
  advisory.
- With checked-in policy and baseline, undeclared drift blocks.
- An intentional breaking beta change is valid only when the exact change is
  classified, the contract revision advances, the configured package-version
  obligation passes, and changed migration evidence exists.
- Stable `1.x+` packages default to SemVer major/minor/patch rules.
- Pre-1.0 repositories own their mapping. Agent Maintainer maps intentional
  material changes within its current `0.1.0bN` line to a prerelease increment
  plus migration evidence; it does not silently force `0.2.0`.

## Repository Files

### Authored policy

`.agent-maintainer/contracts.toml` is strict source truth. It declares:

- policy schema version;
- package-version source and pre-1.0 mapping;
- contract IDs, owners, stability, revisions, kinds, and source paths;
- extractor-specific inputs;
- migration-evidence paths;
- exact fingerprint decisions for review-required changes.

Unknown keys, duplicate IDs, unsafe paths, unsupported kinds, invalid versions,
ambiguous aliases, and overlapping decision fingerprints fail closed.

Illustrative shape:

```toml
version = 1
package_version_file = "pyproject.toml"
pre_one_breaking = "prerelease"
stable_breaking = "major"

[[contracts]]
id = "agent-maintainer-config"
kind = "config-capabilities"
owner = "agent_maintainer.config"
stability = "beta"
revision = 1
source = "config/agent-maintainer-capabilities.json"
migration_paths = ["CHANGELOG.md", "docs/upgrading-to-*.md"]

[[contracts]]
id = "docsync-api"
kind = "python-api"
owner = "docsync.api"
stability = "beta"
revision = 1
source = "src/docsync/api.py"
exports = ["*"]
```

Exact review decisions are narrow and auditable:

```toml
[[decisions]]
contract = "agent-maintainer-config"
fingerprint = "sha256:..."
classification = "breaking"
reason = "Replace the beta-only legacy alias with the documented key."
```

Wildcards, prefix ignores, and suppress-all decisions are invalid.

### Generated baseline

`.agent-maintainer/contracts-baseline.json` is deterministic generated evidence,
not authored policy. It contains:

- baseline schema version and generator identity;
- package version at the snapshot;
- one sorted normalized descriptor per contract;
- contract revision, kind, owner, stability, source paths, semantic body, and
  descriptor SHA-256;
- no timestamps, absolute paths, environment data, or Git worktree dirtiness.

Identical semantic facts produce byte-identical JSON. The baseline reader
rejects special files, symlinks, oversized input, duplicate contracts,
unsupported versions, mismatched fingerprints, and non-canonical paths.

## Architecture

Add `agent_maintainer.contracts` as an inward-facing domain with focused units:

- `models`: immutable policy, descriptor, change, decision, obligation, and
  report types;
- `policy`: strict TOML decoding and repository-confined path validation;
- `baseline`: canonical JSON loading, fingerprinting, and atomic writing;
- `extraction`: orchestration and adapter protocol;
- `extractors.config_capabilities`: normalized field/default/constraint facts;
- `extractors.cli_manifest`: console entry point, command, and option facts;
- `extractors.python_api`: AST-only nominated export and signature facts;
- `extractors.json_schema`: supported structural JSON Schema facts;
- `comparison`: kind-neutral change operations and adapter-specific semantic
  classification;
- `versioning`: contract revision and package bump obligations;
- `git_base`: bounded base-ref policy/baseline reads;
- `reporting`: deterministic text, JSON, and repair facts;
- `cli`: `diff`, `check`, and `snapshot` command behavior.

The domain does not import verifier, catalog, CLI-root, or infrastructure
execution modules. A thin catalog adapter invokes the public contract CLI in
enforcement mode. The root CLI only dispatches. A package-local Tach contract
and an ADR document this dependency direction.

## Extractor Contract

Every extractor receives a confined repository root plus one validated policy
entry and returns one normalized descriptor or a bounded typed error. Extractor
output is pure data and must not include timestamps or machine-specific paths.

### Configuration capabilities

Read a checked-in machine capability document such as
`config/agent-maintainer-capabilities.json`. Normalize field names, nested
tables, value kinds, defaults, bounds, choices, aliases, environment variables,
and stability. Existing generated-reference checks remain responsible for
proving that the capability document matches the Python registry.

### CLI manifest

Normalize checked-in console entry points, command paths, option names,
requiredness, multiplicity, value kinds, defaults, choices, aliases, and exit
status contracts. Agent Maintainer's own manifest is generated from its
canonical command routing and public command definitions, with a focused
freshness test. External repositories may author or generate the same static
manifest; Phase 184 never executes their CLI to discover it.

### Python API

Parse nominated Python files with the standard-library AST. Only explicit
exports or policy-nominated names are contracts. Normalize public functions,
classes, methods, parameter kinds/order/default presence, annotations, return
annotations, async state, and exported constants whose literal values are
declared significant. Bodies, docstrings, private symbols, and arbitrary
distribution contents are excluded.

### JSON Schema

Support a documented structural subset sufficient for IPC/JSON-RPC and durable
record contracts: `$id`, `type`, `properties`, `required`,
`additionalProperties`, `items`, `enum`, `const`, numeric/string bounds, and
local `$defs`/`$ref`. Repository-confined local references are resolved with
cycle and depth limits. Unsupported keywords or ambiguous composition become
review-required facts rather than guessed compatibility.

## Three-Way Comparison

`contract check --base-ref <ref>` uses three states:

1. base policy and baseline read through bounded Git operations;
2. current checked-in policy and baseline;
3. live descriptors extracted from the current repository.

The checker first proves that the current checked-in baseline exactly matches
live extraction. It then compares the base descriptors with current live
descriptors and evaluates current policy, contract revisions, package version,
decisions, and migration evidence.

This prevents a baseline rewrite from hiding a breaking change. Initial adoption
requires an explicit initialization mode and makes no retroactive compatibility
claim. When no usable base ref exists, freshness can be checked but historical
compatibility is reported as unavailable rather than inferred.

## Compatibility Classification

The shared operation vocabulary includes contract add/remove, member
add/remove/rename, type change, requiredness change, default change, constraint
change, alias change, and unsupported-semantic change.

### Breaking by default

- contract or member removal;
- rename without a declared alias or migration mapping;
- optional to required;
- type narrowing or incompatible type replacement;
- config default change;
- command/option removal or requiredness increase;
- positional parameter reorder or newly required Python parameter;
- persisted key removal or incompatible JSON Schema constraint;
- closing `additionalProperties` for previously accepted records.

### Compatible additive by default

- new optional configuration or schema property with a default;
- new command or optional option;
- new nominated Python export or optional trailing parameter;
- widened accepted input type where output obligations do not narrow;
- new alias preserving the canonical member.

### Review-required

- enum expansion for potentially exhaustive consumers;
- annotation or schema constructs whose compatibility is not provable;
- unsupported JSON Schema composition or reference semantics;
- changes with conflicting aliases or inferred renames;
- opaque literal/default representations.

Review-required changes block until an exact fingerprint decision classifies
them. Decisions record reason and classification but cannot waive freshness,
contract revision, package version, or migration evidence.

## Version Obligations

Each report computes two independent obligations.

### Contract revision

Breaking changes require the affected contract revision to advance by exactly
one from the base policy. Compatible changes may keep the revision. Skipped
revisions, revision decreases, and revision changes without semantic drift are
errors unless initialization policy explicitly explains them.

### Package version

The aggregate change set maps to one minimum impact:

- `none`: no semantic contract change;
- `prerelease`: configured beta-line evolution;
- `patch`: compatible correction under repository policy;
- `minor`: compatible additive stable change;
- `major`: breaking stable change.

`packaging.version.Version` parses PEP 440 versions. The checker compares the
base snapshot package version with the current configured source and validates
that the actual change satisfies the recommendation. Reports show the current
version, minimum impact, and a concrete recommended next version when it can be
derived without ambiguity.

## Migration Evidence

Breaking contracts require at least one configured migration path to be a
current or destination path in the Git diff. Deleted evidence cannot satisfy
the requirement. The contract report names the exact missing paths and change
fingerprints. Phase 183 path-risk policy may independently require the same
upgrade guide or review category; the two gates share facts conceptually but do
not import each other's domains.

## Public Commands

```text
agent-maintainer contract diff [--base-ref REF] [--json]
agent-maintainer contract check [--base-ref REF] [--json]
agent-maintainer contract snapshot --write [--base-ref REF] [--initialize]
```

- `diff` is advisory and renders every semantic change and obligation.
- `check` enforces freshness, decisions, versions, and migration evidence.
- `snapshot --write` writes only after extraction and version obligations are
  valid; it never edits policy, package versions, or migration docs.
- `--initialize` is valid only when no baseline exists and records that no
  historical compatibility assertion was made.

Exit statuses are consistent across commands:

- `0`: valid and no unresolved obligation;
- `1`: unresolved compatibility, version, migration, decision, or freshness
  finding;
- `2`: invalid policy, baseline, Git input, extractor input, or unsafe path.

Human output is bounded and stable. JSON uses `schema_version = 1` and contains
sorted contracts, changes, obligations, decisions, repair facts, and advisories
without timestamps.

## Verifier Integration

Add one `contract-compatibility` catalog check to `fast`, `precommit`, `full`,
and `ci` only when `.agent-maintainer/contracts.toml` exists. It invokes the
public checker in enforcement mode against the profile's authoritative diff
context. It does not select or suppress other checks.

Success stays quiet. Failure emits a bounded summary with exact contract IDs,
fingerprints, minimum bump, missing migration evidence, and the command needed
to inspect the full report. Run-scoped artifacts retain the complete JSON.

## Agent Maintainer Dogfood Scope

Phase 184 checks in policy, baseline, and source-backed manifests for:

1. `[tool.agent_maintainer]` configuration capabilities;
2. console scripts and the stable top-level command tree;
3. the nominated `docsync.api` Python boundary;
4. Codex app-server JSON-RPC messages used by the wait client;
5. durable `agent_waits.WaitRecord` persistence.

The JSON-RPC and wait-record schemas become explicit checked-in JSON Schema
documents with regression tests tying them to their current model/serializer
behavior. The phase does not claim that upstream Codex protocols are controlled
by Agent Maintainer; it ratchets the subset this repository consumes.

## Failure And Security Behavior

Configured extraction fails closed. Error messages are bounded and never echo
raw untrusted payloads beyond normalized contract IDs, paths, keywords, and
fingerprints.

Reject:

- absolute, parent-traversing, NUL-containing, or backslash-confused paths;
- symlinks, special files, oversized inputs, excessive nesting, reference
  cycles, and excessive member counts;
- malformed Git refs, duplicate identities, unknown kinds/keys, invalid version
  mappings, mismatched fingerprints, and non-finite numeric constraints;
- Python syntax errors, dynamic export declarations, and unsafe annotation
  expressions that cannot be represented without execution.

Baseline writes use an atomic repository-confined replace. No generated file is
written during `diff` or `check`.

## Verification Strategy

### Focused tests

- strict policy and baseline decoding, canonical serialization, and atomic
  writing;
- property tests for ordering invariance, stable fingerprints, and bounded
  normalization;
- table-driven compatibility matrices for every extractor and operation;
- Python parameter-kind, default, annotation, export, and class-member changes;
- JSON Schema requiredness, type, enum, constraints, references, cycles, and
  unsupported-keyword behavior;
- base/current/live anti-bypass integration tests;
- package-version matrices for prerelease, pre-1.0, and stable SemVer policy;
- exact decision fingerprints and migration destination-only evidence;
- CLI exit semantics, deterministic JSON, bounded human output, and repair
  facts;
- catalog conditional activation and authoritative diff propagation;
- Agent Maintainer dogfood manifest/schema freshness tests.

### Adversarial tests

- symlinks, special files, oversized and deeply nested JSON/TOML, hostile
  Unicode/control text, path escapes, ambiguous aliases, and malformed Git
  output;
- dynamic Python constructs that would require execution;
- JSON reference bombs, cycles, duplicate members, and unsupported composition;
- baseline tampering, fingerprint mismatch, downgrade, skip, and rewrite
  attempts.

### Completion gates

- focused contract suite and mutation coverage for compatibility classifiers;
- exact Ruff, strict Pyright, Tach, Archguard ADR, DocSync, and public docs;
- fresh full, CI, and security profiles;
- independent review and protected hosted checks.

## Rollout

1. Land the domain models, strict policy, canonical baseline, and tests.
2. Add extractors one at a time behind the shared adapter contract.
3. Add semantic comparison, decisions, and version obligations.
4. Expose CLI/reporting and repair facts.
5. Dogfood all five Agent Maintainer contracts in advisory mode and record the
   initial baseline.
6. Enable the conditional blocking catalog gate once the dogfood baseline and
   anti-bypass tests pass.
7. Document the beta support-policy relationship and migration workflow.

The external-proof cohort runs alongside implementation and records activation
cost, false positives, review findings, repair iterations, and retained use.
Phase 185 follows with recurring failure fingerprints and machine-readable
repair packets built on this phase's output.

## Alternatives Rejected

- **Source-diff heuristics:** too many false positives and insufficient semantic
  knowledge for aliases, defaults, requiredness, and schema constraints.
- **Independent surface-specific ratchets:** duplicates policy, version rules,
  output, repair facts, and enforcement behavior.
- **Runtime reflection/import:** executes repository code and makes extraction
  environment-dependent.
- **Raw golden text or source hashes:** detects formatting and implementation
  changes that are not contract changes while missing semantic intent.
- **Automatic baseline acceptance or version edits:** turns the ratchet into a
  bypass and hides review decisions.
- **Freeze all beta surfaces:** conflicts with the explicit pre-1.0 support
  policy and would prevent necessary product evolution.

## Acceptance Criteria

- One strict authored policy and deterministic generated baseline cover every
  configured contract.
- Current baseline freshness and base-to-current compatibility are both checked;
  rewriting the baseline cannot hide drift.
- All four extractor families emit the common descriptor model without network,
  arbitrary imports, or target command execution.
- Breaking, compatible, and review-required changes have exact stable facts and
  tested classifications.
- Contract revision, package bump, exact decision, and migration evidence
  obligations are independently validated.
- Human and JSON reports are deterministic, bounded, safe, and actionable.
- The optional catalog gate activates only with policy and never suppresses an
  existing verifier check.
- Agent Maintainer dogfoods config, CLI, `docsync.api`, Codex JSON-RPC, and wait
  persistence contracts.
- Focused, property, adversarial, mutation, architecture, full, CI, security,
  independent review, and hosted gates pass before Phase 184 completes.

## Recorded Decisions

The user requested that remaining design questions be recorded while recommended
answers proceed under standing self-approval. The recorded choices are:

1. Explicit beta evolution rather than a new cross-version freeze.
2. Authored TOML policy plus deterministic generated JSON baseline.
3. Config, CLI, nominated Python API, and JSON Schema extractors in Phase 184.
4. Independent contract-revision and package-version obligations.
5. Advisory diff, blocking check, and guarded snapshot writing with no broad
   accept escape hatch.
6. One compatibility kernel with isolated extractor adapters.
