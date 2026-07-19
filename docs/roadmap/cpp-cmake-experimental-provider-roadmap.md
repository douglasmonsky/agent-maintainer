# C/C++ CMake Experimental Provider Roadmap

This roadmap turns the approved C/C++ experiment into six independently
reviewable phases. The provider is disabled by default, remains experimental,
and executes only repository-owned explicit commands.

## Why CMake First

C and C++ repositories vary by compiler, generator, target graph, dependency
manager, test runner, static-analysis tool, and coverage pipeline. CMake gives
the experiment one authoritative build-system boundary without pretending the
ecosystem is uniform. Agent Maintainer consumes repository-owned commands and
artifacts; it does not reproduce CMake's project model.

The provider does not select a compiler, generator, preset, target, build
directory, package manager, or coverage converter. It does not install tools or
rewrite CMake configuration.

## Product Boundary

- Internal provider name: `cpp`.
- Public display name: C/C++ (CMake).
- Maturity: built-in experimental provider.
- Enablement: `[tool.agent_maintainer.cpp].enabled = true`.
- Initial platforms: Linux/GCC, macOS/Clang, and Windows/MSVC.
- Initial build system: CMake with repository-owned explicit commands.
- Initial checks: format, static analysis, build, test, and coverage.
- Initial facts: Clang-Tidy, Cppcheck, CTest, LCOV, and gcovr artifacts.

Core continues to own profiles, command execution, bounded logs, run artifacts,
context packs, repair plans, and hooks. The provider owns C/C++ classification,
configuration semantics, report formats, suppression evidence, and doctor
guidance.

## Supported Artifact Contracts

The initial parser contracts are exact:

- Clang-Tidy exported-fixes YAML;
- Cppcheck XML version 2;
- CTest JUnit XML;
- LCOV tracefiles; and
- version-declared gcovr JSON.

Each report declaration identifies one producing check, one supported format,
one exact repository-relative path, required or optional status, a positive
byte limit, and a truthful coverage scope when applicable. Unknown formats and
unknown gcovr major versions fail closed.

These are artifact contracts, not installation promises. A Windows/MSVC
repository may use a repository wrapper to produce LCOV or gcovr evidence, but
Agent Maintainer will not claim that MSVC natively emits GCC coverage formats.

## Cross-Platform Contract

Every implementation phase accounts for:

- POSIX separators, Windows separators, and drive-letter paths;
- executable suffixes and repository wrapper resolution;
- CMake single-config and multi-config generators;
- GCC, Clang, and MSVC diagnostic path forms;
- UTF-8 decoding failure and bounded replacement behavior;
- LF and CRLF input;
- case-sensitive and case-insensitive filesystems; and
- deterministic ordering across operating systems.

Cross-platform support means the same configuration, safety, status, artifact,
and repair-fact contracts. It does not require identical tools on each
platform.

## Implementation Sequence

### Phase 186: Provider Contract And Roadmap

Status: complete.

Publish the approved design, this roadmap, the Phase 186-191 cards, the
built-in-provider boundary decision, and a decision-complete implementation
plan for Phase 187. Record the experiment in provider status without claiming
that runtime support has landed.

### Phase 187: Classification, Configuration, Registry, And Doctor

Status: planned.

Add the disabled nested configuration, conservative file roles, header role,
ignored roots, provider metadata, advisory suppression facts, and static doctor
diagnostics. Add public configuration documentation and fixture-backed tests.
No C/C++ command executes in this phase.

### Phase 188: Explicit Commands And Bounded Artifacts

Status: planned.

Add `cpp-format`, `cpp-static-analysis`, `cpp-build`, `cpp-test`, and
`cpp-coverage`. Resolve system executables and explicit repository wrappers
safely, preserve profile selection, link declared reports to exact command
outcomes, and emit bounded sanitized runner artifacts. Exercise the command
contract on Linux, macOS, and Windows.

### Phase 189: Static-Analysis Facts

Status: planned.

Parse Clang-Tidy exported-fixes YAML and Cppcheck XML version 2 into normalized,
bounded, deterministic findings. Validate freshness, containment, schema,
finding limits, message limits, duplicate identity, and unsafe paths. Add a
baseline lifecycle only if measured external evidence proves comparison-only
debt handling is necessary.

### Phase 190: Test And Coverage Facts

Status: planned.

Parse CTest JUnit XML, LCOV tracefiles, and version-declared gcovr JSON. Emit
truthful per-file and real-scope coverage facts, bounded test failures, and
advisory changed-line coverage. Do not synthesize aggregate percentages or
introduce default thresholds.

### Phase 191: Cross-Platform And External Proof

Status: planned.

Run live fixtures on Linux/GCC, macOS/Clang, and Windows/MSVC. Audit and pin
three public repositories, one centered on each platform/toolchain. Commit only
sanitized projections and immutable SHAs, never third-party source trees.

Measure activation time, command duration, classification misses, false
positives, report completeness, repair iterations, artifact size, path leaks,
and repeated-run stability.

## Phase Gates

Each phase lands through a focused pull request to `main`. A phase may start
only after the preceding phase's contract and verification evidence are merged.
The detailed implementation plan for each later phase is written after the
preceding phase supplies measured evidence.

Every phase must:

- preserve Python, TypeScript/JavaScript, and Java/Gradle behavior;
- keep C/C++ disabled by default;
- reject unsafe repository paths and shell-string shortcuts;
- keep agent-facing output bounded, sanitized, and deterministic;
- update Tach ownership for every new internal module;
- add focused tests before implementation;
- pass focused, architecture, documentation, and broad verification; and
- document unsupported tools and layouts honestly.

## Qualification Bar

The experiment is qualified only when:

- all focused and broad repository checks pass;
- each operating-system fixture exercises configuration, commands, doctor, and
  at least one structured artifact;
- three pinned public repositories produce reproducible sanitized evidence;
- missing or unsafe tools and reports produce actionable failures;
- repeated no-change runs produce stable normalized output;
- no raw third-party report body or absolute checkout path enters persisted
  agent-facing facts;
- existing Python characterization remains unchanged and passing; and
- public documentation states every unsupported tool and layout.

Qualification does not promote the provider. Promotion requires a separate
decision based on external noise, maintenance cost, user demand, and hosted CI
stability.

## Deferred Work

The following require separate designs after Phase 191:

- AddressSanitizer, UndefinedBehaviorSanitizer, ThreadSanitizer, and MSVC
  runtime diagnostic facts;
- Meson, Bazel, Autotools, and raw Make support;
- reviewed CMake setup edits;
- Conan or vcpkg vulnerability and dependency facts;
- C/C++ architecture analysis;
- blocking reviewability or coverage ratchets; and
- promotion beyond experimental maturity.

## Durable Design Sources

- [Approved experiment design](../superpowers/specs/2026-07-19-cpp-cmake-experimental-provider-design.md)
- [Built-in provider boundary decision](../architecture/decisions/2026-07-19-cpp-cmake-experimental-provider-boundary.md)
- [Phase 187 implementation plan](../superpowers/plans/2026-07-19-cpp-cmake-provider-foundation.md)
