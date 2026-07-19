# C/C++ CMake Experimental Provider Boundary

## Status

Accepted.

## Context

Agent Maintainer has mature Python behavior and experimental
TypeScript/JavaScript and Java/Gradle providers. C and C++ support must account
for multiple compilers, generators, target graphs, report tools, and platform
path rules without creating a second build-system model inside Agent
Maintainer.

CMake is a sufficiently common authoritative boundary for a useful first
experiment. The repository, not Agent Maintainer, already knows its compiler,
generator, presets, targets, build directory, environment, and report-producing
commands.

## Decision

Add `agent_maintainer.ecosystems.cpp` as a built-in experimental provider behind
`[tool.agent_maintainer.cpp].enabled`.

The provider owns conservative C/C++ and CMake file classification, explicit
command configuration, C/C++ suppression evidence, supported report parsing,
and static doctor guidance. Core continues to own profile selection, process
execution, bounded logs, run artifacts, context packs, repair plans, and hooks.

The initial provider runs only repository-owned explicit command arrays. It
does not select or infer a compiler, generator, preset, target, build directory,
package manager, or report converter. System executables must resolve normally;
repository wrappers must resolve to regular files confined to the repository.

The first supported report contracts are Clang-Tidy exported-fixes YAML,
Cppcheck XML version 2, CTest JUnit XML, LCOV tracefiles, and version-declared
gcovr JSON. Report declarations use exact repository-relative paths rather than
globs.

## Consequences

CMake repositories can opt into one consistent provider safety and evidence
contract across Linux/GCC, macOS/Clang, and Windows/MSVC while retaining their
own toolchain choices. The same check may use different repository-owned tools
on different platforms.

The provider starts disabled and smaller than Python. It remains experimental
through cross-platform fixtures and three pinned external comparisons. Runtime
sanitizers, other build systems, automatic setup edits, and blocking policy are
separate later decisions.

Adding a distinct internal header role is permitted because C/C++ header
ownership is ambiguous. Public reviewability may count headers with source only
after an explicit provider contract defines that behavior.

## Alternatives Considered

- A generic arbitrary-command provider was rejected because it would omit
  C/C++ classification, report semantics, path safety, and repair facts.
- Compiler or generator detection was rejected because CMake repositories may
  deliberately support multiple configurations and cross-compilation.
- Supporting CMake, Meson, Bazel, and Make together was rejected because it
  would combine unrelated build ownership contracts before the first provider
  is measured.
- Importing Java report orchestration was rejected because shared XML syntax
  does not make Gradle task provenance a C/C++ concept.

## Boundary Rules

- C/C++ modules may depend on provider-neutral config, path, executor, artifact,
  and repair-fact primitives through explicit Tach ownership.
- C/C++ modules must not import Java-specific orchestration.
- Normal doctor must not configure, build, or execute a CMake project.
- Normal verification must never create or mutate a debt baseline.
- Unknown report formats, unsafe paths, malformed required reports, and unknown
  gcovr major versions fail closed.
- Existing Python, TypeScript/JavaScript, and Java/Gradle behavior must not be
  weakened to create superficial provider symmetry.
