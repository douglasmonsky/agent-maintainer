# Critical Stabilization Roadmap

- Status: active
- Target: release-ready `0.1.0b6`
- Audit baseline: `b4c0505bdcc6bdfd7b4cd2cb65c52095c83ea862`
- Started: 2026-07-09

## Decision

Pause feature expansion and make the existing beta safe, predictable, and
releaseable. The work in this document takes precedence over the TypeScript,
rewake, analytics, orchestration, and other feature tracks until every required
outcome below is verified.

The stabilization target is a release-ready repository, not an automatic
release. Creating a tag, publishing packages, changing deployment settings, or
changing GitHub account security settings requires a separate explicit action.

## Task Card

### Goal

Remove the confidentiality, integrity, mutation-safety, configuration, process,
and release-control failures found in the 2026-07-09 deep audit. Leave behind
enforceable contracts and regression tests instead of one-time repairs.

### Desired outcome

A new or existing Python repository can install Agent Maintainer, preview and
apply its managed changes, run hooks and verification repeatedly, and receive
the same safe result without losing user configuration or exposing files
outside the repository. A release can proceed only from immutable evidence that
all required profiles passed for the exact source and artifacts being published.

### In scope

- MCP and DocSync filesystem trust boundaries.
- Generated hook inventory, rendering, installation, status, and removal.
- Bootstrap, install, init, dry-run, merge, backup, and idempotency semantics.
- Fail-closed configuration parsing and validation.
- Detached verifier process lifecycle.
- Strict Pyright ratchet recovery and required deep verification.
- Release workflow pinning, artifact identity, and evidence binding.
- Changelog, versioned documentation, local links, built-package smoke tests,
  and release-readiness records.

### Out of scope

- New ecosystems, top-level commands, analytics, scoring, orchestration, or
  other product features.
- Publishing `0.1.0b6`, pushing a branch, or creating a pull request or tag.
- Production credentials, deployment configuration, billing, or account
  permissions.
- Enabling GitHub-hosted security settings that cannot be represented and
  verified in this repository. Those remain a release-owner checklist item.
- Broad architectural rewrites that are not necessary to close an acceptance
  criterion in this roadmap.

### Constraints

- Preserve existing user files and third-party hooks.
- Keep local-first and no-upload defaults.
- Do not weaken coverage, lint, type, security, architecture, or change-budget
  gates to make verification pass.
- Use synthetic malicious-repository fixtures; never place real credentials or
  private records in tests or logs.
- Make each implementation unit independently reviewable and commit it only
  after its focused checks pass.
- Run the repository's broad verification before declaring the program done.

## Audit Baseline

The baseline established these facts:

- Full verification passed with 1,476 tests, 11 skips, and 94.27% coverage.
- Security verification passed.
- Manual verification failed because strict Pyright reported 1,231 errors
  against an allowed baseline of 889.
- Release-only tests passed even while the manual gate was red.
- A clean-clone bootstrap changed three tracked hook files and created three
  untracked backups; two regenerated files failed Ruff formatting.
- MCP accepted an outside file path, and DocSync accepted repository-controlled
  paths capable of escaping the checkout.
- Generated agent-track hook configuration referenced two files the scaffold
  did not create.
- Mutating top-level commands ignored arguments, and Claude hook merging could
  replace unrelated event arrays.
- Unknown and invalid configuration could be silently ignored or accepted.
- Detached verification could pass a closed stdin descriptor to every Python
  check.
- The publish workflow did not require full, security, and manual evidence for
  the exact artifact, and several actions were referenced by mutable tags.
- Public `main` documentation described substantial behavior not present in the
  latest published beta.

These are regression-test inputs, not merely historical notes.

## Required Outcomes

All outcomes in this table block stabilization completion.

| ID | Outcome | Audit source | Completion signal |
|---|---|---|---|
| CS-01 | Repository-confined MCP context reads | F-01 | Outside, traversal, symlink, sensitive, special, and oversized paths are refused before content is opened. |
| CS-02 | Repository-confined DocSync I/O | F-02 | Every configured input/output resolves inside an approved root; ordinary check is read-only unless output is requested. |
| CS-03 | One executable managed-hook contract | F-03, F-14 | Every emitted command target comes from one manifest, exists, is current, formats cleanly, and survives a safe invocation. |
| CS-04 | Predictable, lossless mutation | F-04, F-05, F-11 | Help/errors/dry-run do not mutate; user hooks survive; backups are collision-proof; a second apply is a byte-for-byte no-op. |
| CS-05 | Fail-closed configuration | F-06 | Unknown, mistyped, out-of-range, contradictory, and type-confused values stop command construction with actionable errors. |
| CS-06 | Reliable detached verification | F-10 | A background verifier survives terminal closure, owns valid standard streams, and reports the real terminal result. |
| CS-07 | Enforced deep release evidence | F-07 | Strict typing has a reviewed monotonic baseline, and publish eligibility requires full, CI, security, manual, and release evidence for one commit. |
| CS-08 | Immutable workflow supply chain | F-08 | Actions are full-SHA pinned, workflow validation is strict, and artifacts are digest-verified across jobs. |
| CS-09 | Version-matched release contract | F-09, F-12 | Unreleased is reconstructed, public beta docs are clearly versioned, links resolve, and advertised entry points pass built-artifact smoke tests. |

## Non-Negotiable Design Rules

### Filesystem boundaries

Every model-controlled or repository-controlled path follows one policy:

1. Start from an explicit trusted root.
2. Reject absolute user input and lexical parent traversal.
3. Resolve the candidate and prove containment in the trusted root.
4. Reject symlink escapes and non-regular files before opening.
5. Reject sensitive names and enforce a byte ceiling before reading.
6. Stream or read the bounded requested content once.
7. Keep write roots separate from read roots and make writes explicit.

An unsafe local-only escape hatch, if retained for compatibility, must never be
reachable through MCP.

### Mutations

Every mutating command must have strict parsing, side-effect-free help, a
side-effect-free preview, explicit conflict classifications, atomic writes,
documented rollback, and a second-run no-op guarantee. `--force` may resolve a
known conflict, but it may not suppress a promised backup or delete unrelated
configuration.

### Configuration

Configuration is invalid unless the complete merged document validates. One
authoritative field registry should drive coercion, environment mappings,
unknown-key detection, CLI metadata, and generated reference documentation.
Python's `bool` values must not satisfy integer fields.

### Release evidence

Release evidence must bind together:

- source commit SHA;
- verification profile and command;
- immutable action implementations;
- built wheel and source archive digests;
- the artifact transferred between build and publish jobs.

A human checklist may add assurance, but it may not substitute for a failed or
missing automated gate.

## Implementation Units

### Unit 0 — Record and freeze the stabilization contract

Deliverables:

- this roadmap;
- an active integration-branch cohesive change plan;
- a root-roadmap pointer that makes stabilization the current priority.

Checks:

- change-plan validation;
- roadmap documentation tests;
- Markdown lint and link checks for changed documents;
- clean diff review.

Exit criterion: the planning artifacts are committed before source changes.

### Unit 1 — Constrain MCP and DocSync paths

Deliverables:

- a shared or deliberately parallel small containment primitive with explicit
  read and write policies;
- an MCP workspace-root contract and bounded, single-pass file reading;
- DocSync input and output confinement;
- read-only default behavior for `docsync check`, with reports requested
  explicitly;
- malicious-checkout fixtures for absolute paths, traversal, symlink parents,
  sensitive files, sparse oversized files, FIFOs, and devices.

Checks:

- focused path-policy, context-reading, MCP, and DocSync tests;
- a timeout-protected test proving special files are rejected without blocking;
- full and security verification before merging the unit.

Exit criterion: no untrusted path is opened until its root, kind, sensitivity,
and size have been approved.

Implementation status (2026-07-10): complete on
`codex/critical-stabilization`. CS-01 and CS-02 now have repository-confined,
bounded read/write policies; MCP child import and process-output isolation;
read-only default DocSync checks; atomic explicit outputs; and malicious
checkout coverage for traversal, symlinks, sensitive/special/oversized inputs,
output collisions, Git option injection, module shadowing, output floods, and
timeouts. Verification evidence:

- focused Unit 1 suite: 499 passed;
- MCP and path-boundary regression suite: 155 passed;
- precommit: `20260710T045535732412Z-precommit-efb217b867e9`;
- full: `20260710T050217032265Z-full-12c03f81b8b5`; and
- security: `20260710T050342782829Z-security-31caaa63de5c`.

### Unit 2 — Unify managed hooks and make mutation safe

Deliverables:

- one per-client managed-file/managed-entry manifest used by scaffold, install,
  status, update, uninstall, and documentation;
- the missing Codex and Claude PR-wait wrappers in agent and hardening output;
- renderer-currentness and Ruff-currentness checks for every checked-in managed
  Python file;
- real parsers for bootstrap and install, including help and rejected-argument
  behavior;
- explicit separation of dependency setup from hook installation;
- identity-aware merge/update/removal that preserves third-party hooks and
  ordering;
- an ignored, collision-proof backup directory and rollback instructions;
- transactional preview/apply behavior for existing repositories.

Checks:

- parse every emitted hook command and safely execute its target;
- coexistence fixtures containing third-party hooks in every managed event;
- clean-clone first-run and second-run tests with `git status --porcelain`;
- force, conflict, dry-run, help, typo, interrupted-write, and rollback tests;
- full verification before merging the unit.

Exit criterion: onboarding and installation are lossless, previewable, and
idempotent in both empty and existing repositories.

Implementation status (2026-07-10): complete on
`codex/critical-stabilization`. CS-03 and CS-04 now use one executable manifest
for scaffold/install/update/status/uninstall; preserve third-party config down
to mixed Claude matcher commands; refuse unowned removals; store repository
recovery data under the real Git directory; roll back writes and removals; and
classify existing-repository initialization before apply. Verification evidence:

- focused hook/initializer lifecycle suite: 79 passed;
- clean-clone first-run and second-run Git-status tests: passed; and
- full: `20260710T120658085479Z-full-66a069fe87cb`.

### Unit 3 — Validate configuration before behavior

Deliverables:

- an authoritative field-spec registry covering neutral config, `pyproject`
  config, environment values, workspaces, file baselines, and nested tables;
- typed coercion that distinguishes booleans from integers;
- bounds and cross-field rules for percentages, counts, intervals, timeouts,
  warning/block ordering, paths, and profile compatibility;
- one `validate_config()` boundary used before all public command behavior;
- generated configuration reference and capability metadata from the registry;
- migration-quality diagnostics that name the source and dotted key.

Checks:

- table-driven valid/invalid field tests;
- typo tests at every nesting level and configuration source;
- precedence tests for file, environment, and CLI values;
- fresh-strict tests proving no command continues after invalid policy;
- full verification before merging the unit.

Exit criterion: malformed configuration cannot silently weaken or bypass a
guardrail.

### Unit 4 — Make background verification own its lifecycle

Deliverables:

- detached jobs receive `DEVNULL` or owned descriptors for standard input and
  stable destinations for standard output/error;
- descriptor closure, spawn failure, cancellation, registry updates, and final
  status are explicit;
- terminal-close integration coverage uses a real subprocess boundary rather
  than mocks alone.

Checks:

- focused wait/async tests;
- an integration test that launches, closes the parent terminal/session, waits,
  and asserts the verifier's true check result;
- full verification before merging the unit.

Exit criterion: terminal lifecycle cannot turn every Python check into a bad
file-descriptor failure or a false result.

### Unit 5 — Restore deep and release trust

Deliverables:

- triage of the strict-Pyright delta by rule and file;
- fixes for genuine regressions and a reviewed legacy-debt baseline only where
  repair is not practical in this stabilization cycle;
- a per-file/per-rule monotonic ratchet that prevents error substitution;
- required CI execution of full, CI, security, manual, and release profiles;
- an evidence manifest keyed to the exact commit;
- full-SHA workflow action references with update comments;
- build-produced digests verified after every artifact transfer and immediately
  before publish;
- workflow concurrency and non-canceling release behavior;
- strict workflow schema/security validation including deep verification.

Checks:

- manual profile passes without increasing unreviewed debt;
- every required profile passes locally or in its hermetic equivalent;
- strict Zizmor reports no high-severity findings;
- tampered-artifact and wrong-commit evidence tests fail closed;
- release tests install and exercise the exact verified artifacts.

Exit criterion: publish cannot become eligible from partial, stale, mutable, or
artifact-mismatched evidence.

### Unit 6 — Reconcile the public release contract

Deliverables:

- a user-impact reconstruction of all post-`0.1.0b5` changes in Unreleased;
- explicit documentation labels for published versus unreleased behavior;
- version-matched release notes and upgrade guidance for `0.1.0b6`;
- repaired repository-local Markdown links;
- built-wheel and source-distribution smoke tests for every advertised console
  script on supported Python versions;
- realistic existing-application onboarding fixtures;
- dependency-risk records with owner, rationale, and expiry;
- contributor, security-reporting, and support documents needed for a public
  beta.

Checks:

- repository-wide Markdown link validation;
- package build, metadata, wheel, source archive, extras, and console-script
  smoke tests;
- the complete release-readiness matrix against one source commit;
- final broad verification and an independent review pass.

Exit criterion: repository docs, package behavior, changelog, and release
evidence describe the same beta.

## Verification Ladder

Each unit uses the smallest meaningful focused checks first, then broader
checks before commit:

1. Direct tests for the changed behavior and its failure modes.
2. Formatting, lint, typing, architecture, and generated-currentness checks for
   the affected surface.
3. Full verification for source-bearing units.
4. Security verification for trust-boundary or workflow units.
5. Manual/deep and release profiles for Units 5 and 6.
6. Final full, CI, security, manual, and release matrix on the same commit.

Tests may be skipped only when the relevant tool cannot run locally. Any skip
must record the exact command, reason, and remaining evidence needed.

## Commit and Review Strategy

Use one focused Conventional Commit per independently verifiable result. Keep
tests in the same commit as the behavior they protect. Do not mix roadmap-only,
filesystem-boundary, mutation, configuration, process, workflow, and release
documentation changes merely to reduce commit count.

The active cohesive change plan permits the branch-level series to exceed the
normal single-change budget; it does not relax coverage, typing, security,
architecture, suppression, or generated-file gates.

## Product Direction After Stabilization

The stable core should remain narrow:

- safe onboarding and diagnostics;
- verification profiles and repair facts;
- bounded context;
- predictable client hooks;
- legacy ratchets.

MCP, DocSync, wait/rewake behavior, event/scoring analytics, task brokering, and
experimental TypeScript blocking remain labs until external use proves they
improve outcomes without weakening the core.

The next product milestone is not more commands. It is repeatable activation in
three to five external repositories, followed by at least 30 real coding-agent
tasks with measured repair efficacy, false-positive rates, review cost, and
four-week retained use.

## Operating Improvements

After this program:

- schedule explicit stabilization windows instead of continuous phase growth;
- require every user-facing change to update Unreleased;
- keep one small outcome roadmap and archive completed implementation detail;
- make clean-clone dogfood tests part of required CI;
- review every new path, mutation, configuration, and subprocess boundary with
  its hostile-input and lifecycle tests;
- recruit a second release/security reviewer before treating human approval as
  an independent control;
- keep accepted risks owned and expiring rather than permanent suppressions.

## Success Metrics

| Metric | Target |
|---|---|
| Unintended tracked changes after setup | 0 |
| Second-run diff | 0 bytes |
| Untrusted path escapes | 0 |
| Invalid configuration accepted | 0 |
| Configured hook targets missing or stale | 0 |
| Required release profiles missing for an eligible artifact | 0 |
| Mutable workflow action references | 0 |
| Broken repository-local Markdown links | 0 |
| Advertised console scripts failing built-package smoke | 0 |
| First doctor plus precommit pass in design-partner repos | within 15 minutes |

## Stabilization Definition of Done

- [ ] CS-01 through CS-09 are implemented with focused regression tests.
- [ ] Bootstrap/install and generated-file dogfood tests leave a clean tree on
      first and second run.
- [ ] Full, CI, security, manual, and release profiles pass for one commit.
- [ ] Strict typing debt is reviewed and monotonic by rule and file.
- [ ] Workflow actions are immutable and artifact identity is verified.
- [ ] Unreleased, public docs, upgrade guidance, and package behavior agree.
- [ ] All repository-local Markdown links resolve.
- [ ] Every advertised console script passes built-artifact smoke tests.
- [ ] No threshold, baseline, exclusion, or suppression was weakened merely to
      obtain a pass.
- [ ] Final diff review finds no secret, private-data, production, or unrelated
      changes.
- [ ] Remaining external release-owner actions are documented explicitly.
