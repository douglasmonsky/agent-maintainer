# C/C++ CMake Experimental Provider Design

## Status

- Design date: 2026-07-19
- Maturity target: built-in experimental provider
- Internal provider name: `cpp`
- Public display name: C/C++ (CMake)
- Initial platforms: Linux/GCC, macOS/Clang, and Windows/MSVC
- Initial build-system boundary: CMake with repository-owned commands

## Problem

Agent Maintainer has a core Python provider and experimental TypeScript and
Java providers, but it cannot yet classify C/C++ changes, validate CMake-owned
verification commands, or turn common native-tool reports into bounded repair
facts. Repositories can run arbitrary commands outside Agent Maintainer, but
that does not provide provider-aware reviewability, setup diagnostics, safe
artifact handling, or compact agent repair context.

C/C++ support is more fragmented than the existing providers. Headers may
belong to multiple targets, compiler diagnostics vary across GCC, Clang, and
MSVC, build trees contain large generated outputs, and coverage formats differ
by toolchain. The first provider must therefore be useful without guessing.

## Goals

1. Add a disabled-by-default built-in `cpp` provider for CMake repositories.
2. Support Linux/GCC, macOS/Clang, and Windows/MSVC as design inputs from the
   first implementation phase.
3. Classify C, C++, header, test, generated, vendor, CMake, dependency, and
   documentation paths conservatively.
4. Run repository-owned explicit format, static-analysis, build, test, and
   coverage commands through the existing Agent Maintainer executor.
5. Normalize configured Clang-Tidy, Cppcheck, CTest JUnit, LCOV, and gcovr
   artifacts into bounded sanitized evidence.
6. Provide static doctor diagnostics without configuring or building the
   repository.
7. Validate behavior with cross-platform fixtures and three pinned public
   repositories before declaring the experiment qualified.
8. Preserve all existing Python, TypeScript, and Java behavior.

## Non-Goals

The initial experiment does not:

- install CMake, Ninja, compilers, analysis tools, or coverage converters;
- choose a compiler, generator, preset, build directory, or target;
- rewrite `CMakeLists.txt`, `CMakePresets.json`, or tool configuration;
- discover commands from project contents;
- support Meson, Bazel, raw Makefiles, Autotools, or non-CMake build ownership;
- normalize AddressSanitizer, UndefinedBehaviorSanitizer, ThreadSanitizer, or
  MSVC runtime diagnostics;
- add C/C++ architecture analysis, mutation testing, or dependency scanning;
- add blocking C/C++ reviewability gates or default coverage thresholds;
- expose a stable external provider API; or
- promote C/C++ beyond experimental maturity.

## Design Principles

- Core owns the loop; the provider owns C/C++ ecosystem knowledge.
- Explicit configuration is authoritative. Missing information produces a
  skip or configuration error, never a guessed command.
- Cross-platform capability does not require fake tool symmetry.
- Reports are evidence only when tied to an exact configured command outcome.
- Normal verification never creates or mutates a debt baseline.
- Agent-facing facts remain bounded, sanitized, deterministic, and useful.
- Provider additions must not weaken or rename Python behavior.

## Provider Boundary

The provider lives under `src/agent_maintainer/ecosystems/cpp/` and uses the
existing provider registry, `Check` model, executor, run artifacts, doctor
reporting, changed-file classification, and repair-fact registry.

Focused modules own one responsibility each:

- `classification.py`: file roles and ignored path families;
- `provider.py`: profile-aware checks built from explicit command arrays;
- `reports/clang_tidy.py`: Clang-Tidy exported-fixes parsing;
- `reports/cppcheck.py`: Cppcheck XML parsing;
- `reports/ctest.py`: CTest JUnit parsing;
- `reports/lcov.py`: LCOV line and branch coverage parsing;
- `reports/gcovr.py`: version-declared gcovr JSON parsing;
- `report_evidence.py`: report validation and normalized evidence assembly;
- `artifacts.py`: bounded sanitized runner payloads;
- `doctor.py`: static configuration and artifact-readiness checks;
- `suppressions.py`: advisory C/C++ suppression classification; and
- `errors.py`: typed provider configuration and evidence errors.

The implementation may reuse provider-neutral path confinement, XML safety,
LCOV record, JUnit, file-baseline, and artifact-bound helpers. It must not
import Java-specific orchestration merely because Java already parses XML.
Shared extraction is allowed only when both providers can depend on a neutral
module without weakening either contract.

## Configuration Contract

Configuration uses a nested table and remains disabled by default:

```toml
[tool.agent_maintainer.cpp]
enabled = true
cmake_root = "."
format_command = ["cmake", "--build", "--preset", "ci", "--target", "format-check"]
static_analysis_command = ["cmake", "--build", "--preset", "ci", "--target", "static-analysis"]
build_command = ["cmake", "--build", "--preset", "ci"]
test_command = ["ctest", "--preset", "ci", "--output-junit", "build/reports/ctest.xml"]
coverage_command = ["cmake", "--build", "--preset", "ci", "--target", "coverage"]
format_profiles = ["precommit", "full", "ci"]
static_analysis_profiles = ["precommit", "full", "ci"]
build_profiles = ["full", "ci"]
test_profiles = ["full", "ci"]
coverage_profiles = ["full", "ci"]

[[tool.agent_maintainer.cpp.reports]]
check = "cpp-static-analysis"
format = "clang-tidy-exported-fixes"
path = "build/reports/clang-tidy.yaml"
required = true
max_bytes = 5000000

[[tool.agent_maintainer.cpp.reports]]
check = "cpp-test"
format = "ctest-junit"
path = "build/reports/ctest.xml"
required = true
max_bytes = 5000000

[[tool.agent_maintainer.cpp.reports]]
check = "cpp-coverage"
format = "lcov"
path = "build/reports/coverage.info"
required = false
max_bytes = 5000000
scope = "repository"
```

Commands are arrays, never shell strings. The first element is the required
executable. Repository-owned wrapper programs are allowed when they are
regular files confined to the repository and invoked explicitly. Redirection,
pipes, compiler selection, and environment setup belong in those repository
commands, not in provider inference.

Each repeated `reports` table identifies:

- producing check;
- one supported report format;
- one repository-relative exact file path;
- required or optional status;
- a positive byte limit no larger than the provider ceiling; and
- coverage scope label when more than one real scope is present.

The initial schema deliberately excludes globs. Repositories with multiple
reports declare multiple tables, which keeps provenance, bounds, and error
messages unambiguous. Supported initial `format` values are
`clang-tidy-exported-fixes`, `cppcheck-xml-v2`, `ctest-junit`, `lcov`, and
`gcovr-json`. Unknown values are configuration errors. Coverage `scope` must be
a non-empty repository-defined label when multiple coverage reports are
declared; it never changes the underlying measurements.

## File Classification

The classifier recognizes, at minimum:

- C source: `.c`;
- C++ source: `.cc`, `.cpp`, `.cxx`, `.c++`;
- headers: `.h`, `.hh`, `.hpp`, `.hxx`, `.inl`;
- CMake configuration: `CMakeLists.txt`, `CMakePresets.json`,
  `CMakeUserPresets.json`, and `.cmake` files;
- common C/C++ tool configuration such as `.clang-format`, `.clang-tidy`, and
  Cppcheck suppressions files;
- tests under explicit/common test path segments and recognized test suffixes;
- documentation by existing provider-neutral rules;
- dependency metadata such as Conan, vcpkg, and CPM lock/manifest files only
  when a recognized exact filename is present;
- generated/configured headers under build or generated roots; and
- ignored build, cache, IDE, package-manager, and vendored dependency trees.

Headers remain a separate provider role in internal evidence when ownership is
ambiguous, while public reviewability can count them with source only where the
provider contract explicitly says so. The classifier never assigns a header to
a CMake target without authoritative compile database evidence.

## Checks And Profiles

The provider exposes stable check names:

- `cpp-format`;
- `cpp-static-analysis`;
- `cpp-build`;
- `cpp-test`; and
- `cpp-coverage`.

An empty configured command yields an explicit optional skip. A non-empty
command with a missing executable, unsafe repository wrapper, or invalid CMake
root is a configuration failure. The provider does not silently substitute
another tool.

Default profile recommendations are configuration defaults, not mandatory
tool choices. Precommit should remain responsive; build, test, and coverage
belong in `full` and `ci` unless a repository deliberately chooses otherwise.

## Evidence Flow

For each selected check:

1. Validate the repository-confined CMake root and command.
2. Run the command through the existing bounded executor.
3. Record its exact outcome and run identity.
4. Resolve only reports declared for that check.
5. Refuse unsafe, missing-required, stale, malformed, oversized, truncated,
   symlinked, or path-escaping reports.
6. Parse supported reports into normalized facts.
7. Store sanitized facts in the normal bounded runner artifact.
8. Let repair-fact consumers read that runner artifact once without reopening
   third-party paths.

A failed command remains authoritative even if a report exists. A successful
command does not make an invalid required report acceptable. Optional reports
are explicitly labeled absent rather than silently treated as complete.

## Structured Facts

Static-analysis facts contain:

- tool;
- repository-relative path;
- line and column when present;
- rule or diagnostic code;
- normalized severity;
- bounded message;
- stable semantic identity;
- occurrence count where duplicate diagnostics are meaningful; and
- completeness/truncation state.

CTest facts contain suite, case, outcome, bounded message, and duration when
available. Coverage facts contain real scope label, file path, executable and
covered line counts, branch counts when present, and completeness state.
Repository-wide coverage is emitted only when the producing report represents
one truthful aggregate scope.

The exact initial parser contracts are Clang-Tidy exported-fixes YAML,
Cppcheck XML version 2, CTest JUnit XML, LCOV tracefiles, and version-declared
gcovr JSON. The implementation pins accepted gcovr JSON format versions in
fixtures and rejects unknown major versions rather than guessing. These are
artifact contracts, not tool-installation promises. A Windows/MSVC repository
must explicitly produce one supported artifact through its own command or
wrapper; Agent Maintainer does not claim that MSVC natively emits GCC coverage
formats.

## Doctor Behavior

Doctor remains static and must not configure or build CMake projects. When the
provider is enabled it checks:

- `cmake_root` exists and remains inside the repository;
- configured command arrays are non-empty where required by local policy;
- command executables or repository wrappers are available;
- configured preset files and named report parents are plausible;
- `compile_commands.json` is present only when a configured analysis contract
  declares it required; and
- report paths and globs are lexically safe.

Doctor gives the smallest actionable repair hint. Disabled providers remain
quiet except for the provider-status summary.

## Suppression Evidence

The first classifier reports these additions as advisory facts:

- `NOLINT`;
- `NOLINTNEXTLINE`;
- `NOLINTBEGIN` and `NOLINTEND`;
- inline Cppcheck suppressions; and
- recognized Cppcheck suppressions-file entries.

Facts distinguish broad from rule-scoped suppression. They do not affect exit
status in the initial experiment.

## Cross-Platform Contract

Every implementation phase must consider:

- path separators and drive-letter paths;
- executable suffixes and repository wrapper resolution;
- CMake single-config and multi-config generators;
- GCC, Clang, and MSVC diagnostic path forms;
- UTF-8 decoding failures and bounded replacement behavior;
- line ending differences;
- case sensitivity differences; and
- deterministic output ordering across operating systems.

The provider does not require identical tools on every platform. It requires
the same configuration, safety, status, artifact, and repair-fact contracts.

## Roadmap Phases

### Phase 186: Provider Contract And Roadmap

Publish this design, the detailed implementation plan, provider status entry,
roadmap phase cards, and the architecture decision for a built-in experimental
CMake provider. Record explicit non-goals and cross-platform acceptance bars.
Phase 186 produces the umbrella roadmap and a separate decision-complete plan
for Phase 187. Later implementation phases receive their own detailed plans
after the preceding phase supplies measured evidence; this design does not
collapse six independently reviewable subsystems into one implementation
change.

### Phase 187: Classification, Configuration, Registry, And Doctor

Add conservative file roles, ignored roots, typed nested configuration,
provider metadata, advisory suppression facts, static doctor rows, public docs,
and fixture-backed tests. No C/C++ command executes in this phase.

### Phase 188: Explicit Commands And Bounded Artifacts

Add the five profile-aware checks, optional skips, executable/wrapper safety,
typed report declarations, exact command-outcome linkage, and sanitized runner
artifacts. Exercise the same provider contract on Linux, macOS, and Windows.

### Phase 189: Static-Analysis Facts

Add Clang-Tidy exported-fixes and Cppcheck XML parsers, adversarial evidence
validation, deterministic repair facts, and an explicit baseline lifecycle only
if measured external evidence demonstrates that comparison-only debt handling
is necessary.

### Phase 190: Test And Coverage Facts

Add CTest JUnit, LCOV, and gcovr parsing; truthful multi-scope coverage; bounded
repair facts; and advisory changed-line coverage. Do not introduce default
thresholds or synthesize aggregate percentages.

### Phase 191: Cross-Platform And External Proof

Run live CMake fixtures on Linux/GCC, macOS/Clang, and Windows/MSVC. Add three
pinned public-repository comparisons, one centered on each platform/toolchain.
Record activation time, command duration, classification misses, false
positives, report completeness, repair iterations, artifact sizes, path leaks,
and repeated-run stability.

## Qualification Bar

The experiment is qualified when:

- every focused and broad repository check passes;
- all three operating-system fixtures exercise provider configuration,
  commands, doctor, and at least one structured artifact;
- three pinned external repositories produce reproducible sanitized evidence;
- configured missing/unsafe tools and reports fail with actionable facts;
- repeated no-change runs produce stable normalized output;
- no raw third-party report body or absolute checkout path enters persisted
  agent-facing facts;
- existing Python characterization tests remain unchanged and pass; and
- public documentation accurately states all unsupported tools and layouts.

Qualification does not promote the provider. A separate maturity decision must
review external noise, maintenance cost, user demand, and cross-platform CI
stability before any supported label or blocking default is proposed.

## External Evidence Selection

Each external repository must be public, pinned to an immutable commit, use
CMake as an authoritative build path, and have a license compatible with
committed sanitized projections. The cohort must collectively cover:

- predominantly C code;
- modern C++ code;
- mixed source and headers;
- more than one CMake target;
- GCC, Clang, and MSVC execution; and
- at least one supported structured report per platform.

The repository names are selected during Phase 191 after a read-only candidate
audit. The roadmap commits immutable SHAs and sanitized projections, not cloned
third-party source trees.

## Risks And Mitigations

- **Header ownership ambiguity:** classify conservatively; use compile database
  evidence only when explicitly configured.
- **Build-system fragmentation:** keep the first contract CMake-only.
- **Tool-output drift:** pin fixture tool versions and validate schema/version
  markers when formats provide them.
- **Windows asymmetry:** require equivalent provider contracts, not invented
  GCC-native artifacts.
- **Large reports:** enforce file count, byte, finding, and message limits.
- **Generated/vendor noise:** ignore known build roots and require conservative
  opt-in for ambiguous vendor layouts.
- **CI cost:** group commands and cache only through repository-owned workflows;
  Agent Maintainer does not invent cache policy.
- **Provider sprawl:** keep every phase independently reviewable and preserve
  the experimental label.

## Follow-Up Work

Only after Phase 191 evidence may separate designs consider:

- ASan, UBSan, TSan, and MSVC runtime diagnostic facts;
- Meson, Bazel, Autotools, or raw Make support;
- reviewed CMake setup edits;
- dependency and vulnerability facts for Conan or vcpkg;
- C/C++ architecture analysis;
- opt-in blocking reviewability or coverage ratchets; and
- promotion beyond experimental maturity.
