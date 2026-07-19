# Experimental C/C++ (CMake) Provider

## Status

The built-in C/C++ provider is an experimental Phase 187 foundation. It is
disabled by default and remains advisory-only. Enable it explicitly with
`[tool.agent_maintainer.cpp]` after the repository owns its CMake workflow.

## Supported Now

Phase 187 supports configuration loading, conservative file classification,
advisory suppression evidence, and static doctor diagnostics. Linux/GCC,
macOS/Clang, and Windows/MSVC define the platform and toolchain boundary, but
this phase does not run a compiler or build on any platform.

## Configuration

Configure all work as repository-owned explicit command arrays:

```toml
[tool.agent_maintainer.cpp]
enabled = true
cmake_root = "."
format_command = ["cmake", "--build", "--preset", "ci", "--target", "format-check"]
static_analysis_command = ["cmake", "--build", "--preset", "ci", "--target", "static-analysis"]
build_command = ["cmake", "--build", "--preset", "ci"]
test_command = ["ctest", "--preset", "ci"]
coverage_command = ["cmake", "--build", "--preset", "ci", "--target", "coverage"]
format_profiles = ["precommit", "full", "ci"]
static_analysis_profiles = ["precommit", "full", "ci"]
build_profiles = ["full", "ci"]
test_profiles = ["full", "ci"]
coverage_profiles = ["full", "ci"]
```

Command arrays are configuration evidence in this phase. Phase 187 does not execute
them. Phase 188 adds execution through the existing checked-command boundary and
typed report declarations.

## Command Ownership And Build Boundary

Only repository-owned explicit command arrays are accepted; shell strings are
not. Agent Maintainer does not infer a compiler, generator, preset, target, or
build directory. It does not install tools, prepare an environment, discover
commands, or edit CMake setup. Put redirection, pipes, environment setup, and
toolchain choices in a reviewed repository wrapper when they are needed.

The initial build-system boundary is CMake. Meson, Bazel, Make, and Autotools
remain unsupported.

## Doctor Rows And Repair Actions

Normal doctor is static and never configures, builds, tests, or otherwise runs
a configured C/C++ command.

| Row | What It Checks | Concrete Repair |
|---|---|---|
| `cpp-cmake-root` | `cmake_root` resolves to an existing repository-confined directory. | Create the directory or correct `cmake_root` to a safe repository-relative path. |
| `cpp-command-config` | At least one explicit command array is configured. | Configure the required command fields, or set `enabled = false`. |
| `cpp-command-executables` | Each configured executable resolves as a system tool or safe repository wrapper. | Install the missing tool or configure a regular executable wrapper confined to the repository. |
| `cpp-cmake-presets` | A preset command has `CMakePresets.json` or `CMakeUserPresets.json` under `cmake_root`. | Add the matching preset file under `cmake_root` or remove the preset argument. |

## Unsupported Surface

Phase 187 does not provide report parsing, typed report declarations,
sanitizers, blocking policy, provider promotion, or a stable external provider
API. It also does not support Meson, Bazel, Make, or Autotools. Suppression
evidence and doctor findings are advisory-only.

## Design References

- [C/C++ CMake experimental provider roadmap](roadmap/cpp-cmake-experimental-provider-roadmap.md)
- [Accepted C/C++ CMake provider boundary](architecture/decisions/2026-07-19-cpp-cmake-experimental-provider-boundary.md)
- [C/C++ CMake experimental provider design](superpowers/specs/2026-07-19-cpp-cmake-experimental-provider-design.md)
