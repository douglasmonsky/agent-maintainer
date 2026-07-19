# Phase 187: C/C++ Classification, Configuration, Registry, And Doctor

Status: planned

## Goal

Add an honest disabled-by-default C/C++ provider foundation that can classify
CMake repositories, load explicit configuration, expose metadata, report
suppression evidence, and diagnose setup without executing a command.

## Scope

- Add frozen nested `[tool.agent_maintainer.cpp]` configuration.
- Add exact command-array and profile fields without wiring execution.
- Add conservative C, C++, header, CMake, test, generated, vendor, dependency,
  documentation, and ignored classifications.
- Add the provider-neutral internal `header` file role.
- Register `cpp` metadata, classification, and suppression dispatch.
- Recognize NOLINT and Cppcheck suppression forms as advisory evidence.
- Add static CMake-root, command, executable, and wrapper doctor diagnostics.
- Add public provider and configuration documentation.

## Principal Files

- `src/agent_maintainer/config/cpp.py`
- `src/agent_maintainer/config/cpp_coercion.py`
- `src/agent_maintainer/config/cpp_validation.py`
- `src/agent_maintainer/ecosystems/cpp/classification.py`
- `src/agent_maintainer/ecosystems/cpp/suppressions.py`
- `src/agent_maintainer/ecosystems/registry.py`
- `src/agent_maintainer/doctor/support/cpp_provider.py`
- `docs/cpp-cmake-provider.md`
- `tests/config/test_cpp_config.py`
- `tests/ecosystems/test_cpp_classification.py`
- `tests/ecosystems/test_cpp_suppressions.py`
- `tests/doctor/test_cpp_doctor.py`

## Non-Goals

- No `cpp-format`, `cpp-static-analysis`, `cpp-build`, `cpp-test`, or
  `cpp-coverage` execution.
- No report declarations or report parsing.
- No command inference, CMake discovery, compiler selection, or setup edits.
- No reviewability thresholds, blocking gates, or provider promotion.

## Acceptance Criteria

- Defaults are frozen, disabled, and safe on every existing repository.
- Unknown keys, shell strings, unsafe roots, empty command elements, duplicate
  profiles, and invalid profiles fail deterministically.
- Header files remain distinguishable from source files.
- Disabled classification, suppressions, and doctor rows are silent.
- Enabled doctor remains static and provides actionable path/tool diagnostics.
- Provider status says foundation only and does not claim command support.
- Focused config, classification, registry, doctor, architecture, docs, and full
  verification pass.

## Phase 188 Handoff

Consume the frozen config and metadata without renaming fields. Add execution
and report declarations behind the same disabled provider boundary.
