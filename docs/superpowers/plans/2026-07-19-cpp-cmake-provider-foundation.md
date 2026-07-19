# C/C++ CMake Provider Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the disabled-by-default Phase 187 C/C++ CMake provider foundation: typed configuration, conservative classification, advisory suppression evidence, provider metadata, and static doctor diagnostics without executing C/C++ commands.

**Architecture:** Add a frozen nested `CppCmakeConfig` beside the Java nested configuration and register C/C++ classification and suppression dispatch through the existing internal provider registry. Keep runtime checks out of the provider list until Phase 188; Phase 187 doctor reads configuration and the filesystem only, resolves system executables or explicit repository wrappers, and never configures or builds CMake.

**Tech Stack:** Python 3.11+, frozen dataclasses, `pathlib`, existing Agent Maintainer config/registry/doctor models, pytest, Hypothesis where already used, Tach, DocSync, Ruff, Pyright, and Markdownlint.

## Global Constraints

- Internal provider name is `cpp`; display name is `C/C++ (CMake)`.
- The provider is built in, experimental, disabled by default, and enabled only by `[tool.agent_maintainer.cpp].enabled = true`.
- Initial platforms are Linux/GCC, macOS/Clang, and Windows/MSVC.
- CMake and repository-owned explicit command arrays are the only initial build and execution boundary.
- Agent Maintainer does not install tools or select a compiler, generator, preset, target, build directory, or package manager.
- Commands are arrays, never shell strings; shell executables and standalone shell-control tokens are invalid.
- Phase 187 does not execute a C/C++ command and does not add report declarations or report parsing.
- C/C++ remains advisory and adds no blocking reviewability or coverage gate.
- Existing Python, TypeScript/JavaScript, and Java/Gradle behavior must remain unchanged.
- All new internal modules receive explicit Tach ownership in the same commit that creates them.

---

### Task 1: Add the frozen nested C/C++ configuration contract

**Files:**

- Create: `src/agent_maintainer/config/cpp.py`
- Create: `src/agent_maintainer/config/cpp_coercion.py`
- Create: `src/agent_maintainer/config/cpp_validation.py`
- Modify: `src/agent_maintainer/config/schema.py`
- Modify: `src/agent_maintainer/config/coercion.py`
- Modify: `src/agent_maintainer/config/registry.py`
- Modify: `src/agent_maintainer/config/source_validation.py`
- Modify: `src/agent_maintainer/config/validation.py`
- Modify: `src/agent_maintainer/config/tach.domain.toml`
- Create: `tests/config/test_cpp_config.py`

**Interfaces:**

- Consumes: `MaintainerConfig`, `ConfigIssue`, `ConfigValidationError`, `json_array`, `json_object`, and `models.VALID_PROFILES`.
- Produces: `CppCmakeConfig`, `coerce_cpp(raw_value, *, source) -> CppCmakeConfig`, and `cpp_issues(cpp, *, source) -> tuple[ConfigIssue, ...]`.
- Produces config fields consumed by later tasks: `MaintainerConfig.cpp.enabled`, `cmake_root`, five command tuples, and five profile tuples.

- [ ] **Step 1: Write failing configuration tests**

Create `tests/config/test_cpp_config.py` with the frozen defaults, complete-table,
unknown-key, unsafe-path, invalid-command, and invalid-profile cases:

```python
"""Tests for the nested C/C++ CMake configuration contract."""

from __future__ import annotations

import re
from dataclasses import FrozenInstanceError

import pytest

from agent_maintainer.config import loader
from agent_maintainer.config.cpp import CppCmakeConfig
from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.config.validation import ConfigValidationError


def apply_cpp(raw: object) -> MaintainerConfig:
    return loader.apply_pyproject(MaintainerConfig(), {"cpp": raw})


def test_cpp_defaults_are_frozen_and_disabled() -> None:
    cpp = MaintainerConfig().cpp

    assert cpp == CppCmakeConfig()
    assert cpp.enabled is False
    assert cpp.cmake_root == "."
    assert cpp.format_command == ()
    assert cpp.static_analysis_command == ()
    assert cpp.build_command == ()
    assert cpp.test_command == ()
    assert cpp.coverage_command == ()
    assert cpp.format_profiles == ("precommit", "full", "ci")
    assert cpp.static_analysis_profiles == ("precommit", "full", "ci")
    assert cpp.build_profiles == ("full", "ci")
    assert cpp.test_profiles == ("full", "ci")
    assert cpp.coverage_profiles == ("full", "ci")
    with pytest.raises(FrozenInstanceError):
        cpp.enabled = True  # type: ignore[misc]


def test_complete_cpp_table_is_coerced_without_shell_parsing() -> None:
    cpp = apply_cpp(
        {
            "enabled": True,
            "cmake_root": "native",
            "format_command": ["cmake", "--build", "--preset", "ci", "--target", "format-check"],
            "static_analysis_command": ["./ci/static-analysis"],
            "build_command": ["cmake", "--build", "--preset", "ci"],
            "test_command": ["ctest", "--preset", "ci"],
            "coverage_command": ["./ci/coverage"],
            "format_profiles": ["precommit", "ci"],
            "static_analysis_profiles": ["full"],
            "build_profiles": ["ci"],
            "test_profiles": ["full"],
            "coverage_profiles": ["ci"],
        }
    ).cpp

    assert cpp.enabled is True
    assert cpp.cmake_root == "native"
    assert cpp.static_analysis_command == ("./ci/static-analysis",)
    assert cpp.test_command == ("ctest", "--preset", "ci")
    assert cpp.coverage_profiles == ("ci",)


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        ([], "cpp: must be a table"),
        ({"enabled": "yes"}, "cpp.enabled: must be a boolean"),
        ({"build_command": "cmake --build ."}, "cpp.build_command: must be a list of strings"),
        ({"build_command": ["cmake", ""]}, "cpp.build_command"),
        ({"build_command": ["bash", "-c", "cmake --build ."]}, "cpp.build_command"),
        ({"build_command": ["cmake", "|", "tee", "log"]}, "cpp.build_command"),
        ({"build_profiles": ["full", "full"]}, "cpp.build_profiles"),
        ({"test_profiles": ["unknown"]}, "cpp.test_profiles"),
        ({"cmake_root": "/tmp/native"}, "cpp.cmake_root"),
        ({"cmake_root": "../native"}, "cpp.cmake_root"),
    ],
)
def test_cpp_config_rejects_invalid_values(raw: object, message: str) -> None:
    with pytest.raises(ConfigValidationError, match=re.escape(message)):
        apply_cpp(raw)


def test_cpp_config_rejects_unknown_nested_keys() -> None:
    with pytest.raises(
        ConfigValidationError,
        match=r"tool\.agent_maintainer\.cpp\.unknown",
    ):
        apply_cpp({"unknown": True})
```

- [ ] **Step 2: Run the tests and confirm the missing contract**

Run:

```bash
PATH=".venv/bin:$PATH" .venv/bin/pytest -q tests/config/test_cpp_config.py
```

Expected: collection fails because `agent_maintainer.config.cpp` does not exist.

- [ ] **Step 3: Add the frozen configuration model**

Create `src/agent_maintainer/config/cpp.py`:

```python
"""Frozen public configuration model for the C/C++ CMake provider."""

from __future__ import annotations

from dataclasses import dataclass

PRECOMMIT_PROFILES = ("precommit", "full", "ci")
FULL_PROFILES = ("full", "ci")


@dataclass(frozen=True)
class CppCmakeConfig:
    """Resolved disabled-by-default C/C++ CMake provider configuration."""

    enabled: bool = False
    cmake_root: str = "."
    format_command: tuple[str, ...] = ()
    static_analysis_command: tuple[str, ...] = ()
    build_command: tuple[str, ...] = ()
    test_command: tuple[str, ...] = ()
    coverage_command: tuple[str, ...] = ()
    format_profiles: tuple[str, ...] = PRECOMMIT_PROFILES
    static_analysis_profiles: tuple[str, ...] = PRECOMMIT_PROFILES
    build_profiles: tuple[str, ...] = FULL_PROFILES
    test_profiles: tuple[str, ...] = FULL_PROFILES
    coverage_profiles: tuple[str, ...] = FULL_PROFILES
```

Import `CppCmakeConfig` in `config/schema.py` and add this field immediately
before `java` so nested provider configuration remains grouped:

```python
cpp: CppCmakeConfig = field(default_factory=CppCmakeConfig)
java: JavaGradleConfig = field(default_factory=JavaGradleConfig)
```

- [ ] **Step 4: Add coercion and fail-closed validation**

Create `src/agent_maintainer/config/cpp_coercion.py` with one list-of-strings
coercer and no shell parsing:

```python
"""Coercion for nested C/C++ CMake provider configuration."""

from __future__ import annotations

from dataclasses import replace

from agent_maintainer.config.cpp import CppCmakeConfig
from agent_maintainer.config import validation
from agent_maintainer.core.structured_values import json_array, json_object

CPP_TUPLE_FIELDS = (
    "format_command",
    "static_analysis_command",
    "build_command",
    "test_command",
    "coverage_command",
    "format_profiles",
    "static_analysis_profiles",
    "build_profiles",
    "test_profiles",
    "coverage_profiles",
)


def _string_tuple(value: object, field_name: str) -> tuple[str, ...]:
    values = json_array(value)
    if values is None:
        raise TypeError(f"{field_name} must be a list of strings")
    strings = tuple(item for item in values if isinstance(item, str))
    if len(strings) != len(values):
        raise TypeError(f"{field_name} must be a list of strings")
    return strings


def coerce_cpp(raw_value: object, *, source: str = "configuration") -> CppCmakeConfig:
    """Coerce the provider-owned C/C++ table without shell shortcuts."""

    raw = json_object(raw_value)
    if raw is None:
        raise TypeError("cpp must be a table")
    validation.validate_raw_config({"cpp": raw}, source=source)
    updates: dict[str, object] = {
        name: _string_tuple(raw[name], f"cpp.{name}")
        for name in CPP_TUPLE_FIELDS
        if name in raw
    }
    if "enabled" in raw:
        enabled = raw["enabled"]
        if not isinstance(enabled, bool):
            raise TypeError("cpp.enabled must be a boolean")
        updates["enabled"] = enabled
    if "cmake_root" in raw:
        cmake_root = raw["cmake_root"]
        if not isinstance(cmake_root, str) or not cmake_root:
            raise TypeError("cpp.cmake_root must be a non-empty string")
        updates["cmake_root"] = cmake_root
    return replace(CppCmakeConfig(), **updates)
```

Create `src/agent_maintainer/config/cpp_validation.py`:

```python
"""Fail-closed validation for C/C++ CMake provider configuration."""

from __future__ import annotations

from pathlib import PurePosixPath

from agent_maintainer import models
from agent_maintainer.config.cpp import CppCmakeConfig
from agent_maintainer.config.issues import ConfigIssue

COMMAND_FIELDS = (
    "format_command",
    "static_analysis_command",
    "build_command",
    "test_command",
    "coverage_command",
)
PROFILE_FIELDS = (
    "format_profiles",
    "static_analysis_profiles",
    "build_profiles",
    "test_profiles",
    "coverage_profiles",
)
SHELL_EXECUTABLES = frozenset(("bash", "cmd", "powershell", "pwsh", "sh", "zsh"))
SHELL_CONTROL_TOKENS = frozenset(("&&", ";", "<", ">", ">>", "|", "||"))


def cpp_issues(cpp: CppCmakeConfig, *, source: str) -> tuple[ConfigIssue, ...]:
    """Return deterministic C/C++ provider configuration issues."""

    issues: list[ConfigIssue] = []
    normalized_root = cpp.cmake_root.replace("\\", "/")
    root_path = PurePosixPath(normalized_root)
    if root_path.is_absolute() or ".." in root_path.parts:
        issues.append(ConfigIssue(source, "cpp.cmake_root", "must stay repository-relative"))
    for field_name in COMMAND_FIELDS:
        command = getattr(cpp, field_name)
        if any(not item for item in command):
            issues.append(ConfigIssue(source, f"cpp.{field_name}", "must not contain empty elements"))
        executable_name = (
            PurePosixPath(command[0].replace("\\", "/")).name.lower().removesuffix(".exe")
            if command
            else ""
        )
        if executable_name in SHELL_EXECUTABLES:
            issues.append(ConfigIssue(source, f"cpp.{field_name}", "must not invoke a shell executable"))
        if any(item in SHELL_CONTROL_TOKENS for item in command):
            issues.append(ConfigIssue(source, f"cpp.{field_name}", "must not contain shell control tokens"))
    for field_name in PROFILE_FIELDS:
        profiles = getattr(cpp, field_name)
        if len(profiles) != len(set(profiles)):
            issues.append(ConfigIssue(source, f"cpp.{field_name}", "profiles must be unique"))
        invalid = sorted(set(profiles) - models.VALID_PROFILES)
        if invalid:
            issues.append(ConfigIssue(source, f"cpp.{field_name}", f"invalid profiles: {', '.join(invalid)}"))
    return tuple(issues)
```

- [ ] **Step 5: Wire nested loading and ownership**

Make these exact integration changes:

```python
# config/coercion.py
from agent_maintainer.config.cpp_coercion import coerce_cpp

cpp = raw.get("cpp")
if cpp is not None:
    updates["cpp"] = coerce_cpp(cpp, source=source)
```

```python
# config/registry.py
CPP_KEYS = frozenset(
    (
        "enabled", "cmake_root",
        "format_command", "static_analysis_command", "build_command",
        "test_command", "coverage_command",
        "format_profiles", "static_analysis_profiles", "build_profiles",
        "test_profiles", "coverage_profiles",
    )
)
```

Add `cpp` to the nested top-level key inventory, add `_unknown_cpp` beside
`_unknown_java` in `source_validation.py`, and call it from `unknown_keys`.
Import `cpp_issues` in `validation.py` and insert:

```python
issues.extend(cpp_issues(config.cpp, source=source))
```

Add `cpp`, `cpp_coercion`, and `cpp_validation` modules and their exact
dependencies to `config/tach.domain.toml`; extend `coercion`, `schema`, and
`validation` dependencies accordingly.

- [ ] **Step 6: Run focused config tests and make them green**

Run:

```bash
PATH=".venv/bin:$PATH" .venv/bin/pytest -q tests/config/test_cpp_config.py tests/config/test_config_loading.py tests/config/test_config_validation.py tests/config/test_config_reference.py
```

Expected: all selected tests pass with zero failures.

- [ ] **Step 7: Commit the configuration contract**

```bash
git add -- src/agent_maintainer/config/cpp.py src/agent_maintainer/config/cpp_coercion.py src/agent_maintainer/config/cpp_validation.py src/agent_maintainer/config/schema.py src/agent_maintainer/config/coercion.py src/agent_maintainer/config/registry.py src/agent_maintainer/config/source_validation.py src/agent_maintainer/config/validation.py src/agent_maintainer/config/tach.domain.toml tests/config/test_cpp_config.py
git commit -m "feat: add C/C++ provider configuration"
```

### Task 2: Add conservative C/C++ and CMake classification

**Files:**

- Create: `src/agent_maintainer/ecosystems/cpp/__init__.py`
- Create: `src/agent_maintainer/ecosystems/cpp/classification.py`
- Modify: `src/agent_maintainer/ecosystems/models.py`
- Modify: `src/agent_maintainer/ecosystems/file_changes.py`
- Modify: `src/agent_maintainer/ecosystems/registry.py`
- Modify: `src/agent_maintainer/ecosystems/tach.domain.toml`
- Create: `tests/ecosystems/test_cpp_classification.py`
- Modify: `tests/ecosystems/test_file_changes.py`
- Modify: `tests/catalogs/test_provider_registry.py`

**Interfaces:**

- Consumes: `CppCmakeConfig`, `FileClassification`, `FileRole`, and registry classification dispatch.
- Produces: `classification.classify_path(path, config) -> FileClassification | None`, `FileRole.HEADER`, and a disabled-aware `cpp_classification_candidate`.
- Header classification remains distinct; no reviewability source count changes in this task.

- [ ] **Step 1: Write failing classifier and registry tests**

Create parameterized tests that assert these exact mappings:

```python
@pytest.mark.parametrize(
    ("path", "role", "generated", "ignored"),
    [
        ("src/main.c", FileRole.SOURCE, False, False),
        ("src/main.cpp", FileRole.SOURCE, False, False),
        ("include/api.hpp", FileRole.HEADER, False, False),
        ("tests/api_test.cc", FileRole.TEST, False, False),
        ("CMakeLists.txt", FileRole.CONFIG, False, False),
        ("cmake/toolchain.cmake", FileRole.CONFIG, False, False),
        ("CMakePresets.json", FileRole.CONFIG, False, False),
        (".clang-tidy", FileRole.CONFIG, False, False),
        ("vcpkg.json", FileRole.DEPENDENCY, False, False),
        ("conan.lock", FileRole.DEPENDENCY, False, False),
        ("build/generated/config.hpp", FileRole.GENERATED, True, True),
        ("third_party/lib/vendor.cc", FileRole.IGNORED, False, True),
        ("README.md", FileRole.DOCS, False, False),
        ("notes/data.json", None, False, False),
    ],
)
def test_cpp_path_roles(path, role, generated, ignored) -> None:
    result = classify_path(path, CppCmakeConfig(enabled=True))
    if role is None:
        assert result is None
        return
    assert result is not None
    assert result.role is role
    assert result.generated is generated
    assert result.ignored is ignored
```

Add a registry test proving disabled C/C++ classification is silent and enabled
classification returns ecosystem `cpp`. Add a file-change selection test proving
`FileRole.HEADER` is high confidence when a shared config/docs candidate is also
present.

- [ ] **Step 2: Run the focused tests and confirm RED**

Run:

```bash
PATH=".venv/bin:$PATH" .venv/bin/pytest -q tests/ecosystems/test_cpp_classification.py tests/ecosystems/test_file_changes.py tests/catalogs/test_provider_registry.py
```

Expected: collection or assertions fail because `cpp.classification`,
`FileRole.HEADER`, and registry dispatch do not exist.

- [ ] **Step 3: Implement the classifier with exact path families**

Create `src/agent_maintainer/ecosystems/cpp/classification.py` using these
constants and precedence order:

```python
ECOSYSTEM_NAME = "cpp"
C_SOURCE_EXTENSIONS = frozenset((".c",))
CPP_SOURCE_EXTENSIONS = frozenset((".c++", ".cc", ".cpp", ".cxx"))
HEADER_EXTENSIONS = frozenset((".h", ".hh", ".hpp", ".hxx", ".inl"))
TEST_PARTS = frozenset(("spec", "specs", "test", "tests"))
TEST_MARKERS = ("_test.", "_tests.", ".test.", ".spec.")
BUILD_IGNORED_PARTS = frozenset(
    (".cache", "CMakeFiles", "_deps", "build", "cmake-build-debug", "cmake-build-release", "out")
)
VENDOR_PARTS = frozenset(("third_party", "vendor"))
ALWAYS_IGNORED_PARTS = frozenset((".git", ".idea", ".vscode"))
GENERATED_PARTS = frozenset(("generated", "gen"))
CMAKE_NAMES = frozenset(("CMakeLists.txt", "CMakePresets.json", "CMakeUserPresets.json"))
TOOL_CONFIG_NAMES = frozenset((".clang-format", ".clang-tidy", ".cppcheck", ".cppcheck-suppressions", "cppcheck-suppressions.txt"))
DEPENDENCY_NAMES = frozenset(("conan.lock", "conanfile.py", "conanfile.txt", "vcpkg-configuration.json", "vcpkg.json"))
DOC_EXTENSIONS = frozenset((".md", ".rst", ".txt"))
```

Implement `classify_path` in this exact precedence:

1. Normalize `\\` to `/` and remove leading `./`.
2. Return generated-and-ignored for recognized source/header paths under a
   build-ignored part, or under an explicit generated part.
3. Return ignored for vendor, IDE, VCS, cache, and remaining build paths.
4. Return dependency for exact dependency names.
5. Return config for exact CMake/tool names or `.cmake` suffix.
6. Return docs for recognized documentation suffixes.
7. Return `None` for unrecognized suffixes.
8. Return test before header/source when a test part or marker is present.
9. Return header for header suffixes and source for C/C++ suffixes.

Add `HEADER = "header"` to `FileRole` and `FileRole.HEADER` to
`HIGH_CONFIDENCE_ROLES`. Do not add `cpp` to
`SOURCE_TEST_ADVISORY_ECOSYSTEMS`.

- [ ] **Step 4: Register classification without runtime checks**

Add `cpp_classification_candidate` to `ecosystems/registry.py`:

```python
def cpp_classification_candidate(
    path: str | Path,
    config: MaintainerConfig,
    _repo_root: Path | None,
) -> FileClassification | None:
    """Return C/C++ classification only after explicit provider enablement."""

    if not config.cpp.enabled:
        return None
    return cpp_classification.classify_path(path, config.cpp)
```

Append it to `CLASSIFICATION_PROVIDERS`. Add `cpp` and `cpp.classification`
modules to `ecosystems/tach.domain.toml`, and add the new dependency to the
registry module.

- [ ] **Step 5: Run focused and existing classifier tests**

Run:

```bash
PATH=".venv/bin:$PATH" .venv/bin/pytest -q tests/ecosystems/test_cpp_classification.py tests/ecosystems/test_file_changes.py tests/ecosystems/test_python_classification.py tests/ecosystems/test_typescript_classification.py tests/ecosystems/test_java_classification.py tests/catalogs/test_provider_registry.py
```

Expected: all selected tests pass; existing ecosystem mappings are unchanged.

- [ ] **Step 6: Commit the classifier foundation**

```bash
git add -- src/agent_maintainer/ecosystems/cpp/__init__.py src/agent_maintainer/ecosystems/cpp/classification.py src/agent_maintainer/ecosystems/models.py src/agent_maintainer/ecosystems/file_changes.py src/agent_maintainer/ecosystems/registry.py src/agent_maintainer/ecosystems/tach.domain.toml tests/ecosystems/test_cpp_classification.py tests/ecosystems/test_file_changes.py tests/catalogs/test_provider_registry.py
git commit -m "feat: classify C/C++ CMake repositories"
```

### Task 3: Add path-aware advisory C/C++ suppression evidence

**Files:**

- Create: `src/agent_maintainer/ecosystems/cpp/suppressions.py`
- Modify: `src/agent_maintainer/ecosystems/typescript/suppressions.py`
- Modify: `src/agent_maintainer/ecosystems/registry.py`
- Modify: `src/agent_maintainer/assess/reviewability.py`
- Modify: `src/agent_maintainer/ecosystems/tach.domain.toml`
- Create: `tests/ecosystems/test_cpp_suppressions.py`
- Modify: `tests/ecosystems/test_typescript_suppressions.py`
- Modify: `tests/catalogs/test_provider_registry.py`
- Modify: `tests/assess/test_reviewability_advisories.py`

**Interfaces:**

- Consumes: changed-file path plus each added line from reviewability assessment.
- Produces: `classify_line(line, path="") -> tuple[SuppressionFinding, ...]` for TypeScript and C/C++, and `advisory_suppression_findings(ecosystem, line, path="")` in the registry.
- Existing two-argument registry callers remain source-compatible because `path` defaults to an empty string.

- [ ] **Step 1: Write failing suppression tests**

Create tests for these exact classifications:

```python
def test_cpp_nolint_broadness() -> None:
    broad = suppressions.classify_line("value(); // NOLINT")
    narrow = suppressions.classify_line("value(); // NOLINT(readability-identifier-naming)")
    next_line = suppressions.classify_line("// NOLINTNEXTLINE(bugprone-use-after-move)")

    assert [(item.kind, item.broad) for item in broad] == [("nolint", True)]
    assert [(item.kind, item.broad) for item in narrow] == [("nolint", False)]
    assert [(item.kind, item.broad) for item in next_line] == [("nolint-next-line", False)]


def test_cpp_nolint_region_and_cppcheck_forms() -> None:
    assert suppressions.classify_line("// NOLINTBEGIN")[0].broad is True
    assert suppressions.classify_line("// NOLINTEND")[0].kind == "nolint-end"
    assert suppressions.classify_line("// cppcheck-suppress nullPointer")[0].broad is False
    assert suppressions.classify_line("// cppcheck-suppress-file")[0].broad is True


def test_cppcheck_suppression_file_requires_recognized_path() -> None:
    finding = suppressions.classify_line("uninitvar", path="cppcheck-suppressions.txt")

    assert [(item.kind, item.broad) for item in finding] == [("cppcheck-suppression-file", False)]
    assert suppressions.classify_line("uninitvar", path="notes.txt") == ()
```

Add a TypeScript regression test calling `classify_line` with a path and proving
all existing findings are unchanged. Add a reviewability test proving the
changed file path reaches the C/C++ suppression classifier.

- [ ] **Step 2: Run tests and confirm RED**

Run:

```bash
PATH=".venv/bin:$PATH" .venv/bin/pytest -q tests/ecosystems/test_cpp_suppressions.py tests/ecosystems/test_typescript_suppressions.py tests/catalogs/test_provider_registry.py tests/assess/test_reviewability_advisories.py
```

Expected: collection fails because C/C++ suppression support does not exist and
the registry does not accept path context.

- [ ] **Step 3: Implement bounded line classifiers**

Create `cpp/suppressions.py` with compiled expressions for
`NOLINT`, `NOLINTNEXTLINE`, `NOLINTBEGIN`, `NOLINTEND`,
`cppcheck-suppress`, and `cppcheck-suppress-file`. Define these recognized
suppressions-file names:

```python
CPPCHECK_SUPPRESSION_FILE_NAMES = frozenset(
    (".cppcheck-suppressions", "cppcheck-suppressions.txt")
)
```

Use these rules:

- `NOLINT` and `NOLINTNEXTLINE` are narrow only when their parentheses contain
  at least one non-whitespace rule token.
- `NOLINTBEGIN` is broad without a rule list; `NOLINTEND` mirrors its rule-list
  broadness so unbalanced regions remain visible without parser state.
- `cppcheck-suppress <id>` is narrow; `cppcheck-suppress` without an id and
  `cppcheck-suppress-file` are broad.
- A non-empty, non-comment line in an exact suppressions-file name is a narrow
  `cppcheck-suppression-file` finding.
- Return at most one finding per marker family per input line in deterministic
  source order.

Change TypeScript's public signature to:

```python
def classify_line(line: str, path: str = "") -> tuple[SuppressionFinding, ...]:
    del path
    ...
```

Change the registry `SuppressionProvider` alias to accept `(line, path)`, pass
`path` through `advisory_suppression_findings`, and register both `typescript`
and `cpp`. In reviewability, call:

```python
registry.advisory_suppression_findings(ecosystem, line, path)
```

using `classification.path` from `_suppression_findings`.

- [ ] **Step 4: Run suppression and reviewability tests**

Run:

```bash
PATH=".venv/bin:$PATH" .venv/bin/pytest -q tests/ecosystems/test_cpp_suppressions.py tests/ecosystems/test_typescript_suppressions.py tests/catalogs/test_provider_registry.py tests/assess/test_reviewability_advisories.py tests/assess/test_reviewability_assessment.py
```

Expected: all selected tests pass and TypeScript output remains byte-for-byte
compatible for existing inputs.

- [ ] **Step 5: Commit suppression evidence**

```bash
git add -- src/agent_maintainer/ecosystems/cpp/suppressions.py src/agent_maintainer/ecosystems/typescript/suppressions.py src/agent_maintainer/ecosystems/registry.py src/agent_maintainer/assess/reviewability.py src/agent_maintainer/ecosystems/tach.domain.toml tests/ecosystems/test_cpp_suppressions.py tests/ecosystems/test_typescript_suppressions.py tests/catalogs/test_provider_registry.py tests/assess/test_reviewability_advisories.py
git commit -m "feat: report C/C++ suppression evidence"
```

### Task 4: Register provider metadata and static doctor diagnostics

**Files:**

- Modify: `src/agent_maintainer/ecosystems/registry.py`
- Create: `src/agent_maintainer/doctor/support/cpp_provider.py`
- Modify: `src/agent_maintainer/doctor/support/policy.py`
- Modify: `src/agent_maintainer/doctor/cli.py`
- Modify: `src/agent_maintainer/doctor/tach.domain.toml`
- Modify: `tests/catalogs/test_provider_registry.py`
- Create: `tests/doctor/test_cpp_doctor.py`

**Interfaces:**

- Consumes: `ProviderMetadata`, `ProviderCommandSpec`, `CppCmakeConfig`, `DoctorResult`, and repository root.
- Produces: `CPP_PROVIDER`, provider status ordering `(python, typescript, java, cpp)`, and `check_cpp_provider(repo_root, config) -> tuple[DoctorResult, ...]`.
- Phase 187 deliberately leaves `experimental_check_providers()` unchanged; `CppProvider` runtime checks begin in Phase 188.

- [ ] **Step 1: Write failing metadata and doctor tests**

Extend registry tests to assert:

```python
assert tuple(providers) == ("python", "typescript", "java", "cpp")
assert providers["cpp"].display_name == "C/C++ (CMake)"
assert providers["cpp"].maturity is ProviderMaturity.EXPERIMENTAL
assert providers["cpp"].enabled_field == "cpp.enabled"
assert providers["cpp"].capabilities == ("classification", "suppression-evidence", "doctor")
assert [provider.name for provider in experimental_check_providers()] == ["typescript", "java"]
```

Create `tests/doctor/test_cpp_doctor.py` with:

- disabled provider returns no rows;
- missing `cmake_root` produces `cpp-cmake-root` warning;
- no configured commands produces `cpp-command-config` warning;
- missing system executable produces `cpp-command-executables` warning;
- repository wrapper outside the repository or through a symlink is unsafe;
- repository-confined regular executable wrapper is accepted;
- a command using `--preset` warns when neither CMake preset file exists;
- an existing preset file removes that warning;
- monkeypatched `subprocess.run` raises if doctor attempts execution;
- full doctor includes C/C++ rows only when enabled.

- [ ] **Step 2: Run focused tests and confirm RED**

Run:

```bash
PATH=".venv/bin:$PATH" .venv/bin/pytest -q tests/catalogs/test_provider_registry.py tests/doctor/test_cpp_doctor.py
```

Expected: tests fail because `CPP_PROVIDER` and `check_cpp_provider` do not
exist.

- [ ] **Step 3: Add metadata without runtime provider registration**

Add this constant after `JAVA_PROVIDER`:

```python
CPP_PROVIDER = ProviderMetadata(
    name="cpp",
    display_name="C/C++ (CMake)",
    maturity=ProviderMaturity.EXPERIMENTAL,
    docs_path="docs/cpp-cmake-provider.md",
    capabilities=("classification", "suppression-evidence", "doctor"),
    enabled_field="cpp.enabled",
    command_specs=(
        ProviderCommandSpec("cpp-format", "cpp.format_command"),
        ProviderCommandSpec("cpp-static-analysis", "cpp.static_analysis_command"),
        ProviderCommandSpec("cpp-build", "cpp.build_command"),
        ProviderCommandSpec("cpp-test", "cpp.test_command"),
        ProviderCommandSpec("cpp-coverage", "cpp.coverage_command"),
    ),
)
```

Append `CPP_PROVIDER` to `BUILTIN_PROVIDER_METADATA`. Do not add a provider
instance to `experimental_check_providers()` in this phase.

- [ ] **Step 4: Implement static doctor checks**

Create `doctor/support/cpp_provider.py`. The public function returns rows in
this order when enabled:

1. `cpp-cmake-root`;
2. `cpp-command-config`;
3. `cpp-command-executables`; and
4. `cpp-cmake-presets` only when any configured command uses `--preset` or
   `--preset=<name>`.

Use these interfaces:

```python
def check_cpp_provider(repo_root: Path, config: MaintainerConfig) -> tuple[DoctorResult, ...]:
    """Return static C/C++ CMake health without executing a command."""

def configured_cpp_commands(cpp: CppCmakeConfig) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Return stable check-name and non-empty command pairs."""

def resolve_repository_wrapper(repo_root: Path, executable: str) -> Path:
    """Resolve one explicit path-like executable to a confined regular file."""
```

`resolve_repository_wrapper` must resolve relative path-like executables from
`repo_root`, require containment beneath `repo_root.resolve(strict=True)`, reject
symlinks, require a regular file, and require executable permission on POSIX.
Treat `/`, `\\`, a leading `.`, or a Windows drive prefix as path-like. Bare
executables resolve with `shutil.which(executable, path=path_with_local_bins(repo_root))`.

The root check resolves `repo_root / cpp.cmake_root`, requires repository
containment and a real directory, and never creates it. The config row warns
when all five commands are empty. The preset row accepts either
`CMakePresets.json` or `CMakeUserPresets.json` under the resolved CMake root.

Re-export `check_cpp_provider` from `doctor/support/policy.py`, insert it in
`doctor/cli.py` immediately after the Java provider rows, and add exact Tach
dependencies for `support.cpp_provider`, `support.policy`, and `cli`.

- [ ] **Step 5: Run doctor and registry tests**

Run:

```bash
PATH=".venv/bin:$PATH" .venv/bin/pytest -q tests/catalogs/test_provider_registry.py tests/doctor/test_cpp_doctor.py tests/doctor/test_typescript_doctor.py tests/doctor/test_java_doctor.py tests/doctor/test_doctor.py tests/doctor/test_doctor_cli_output.py
```

Expected: all selected tests pass; doctor execution spies observe zero CMake or
configured-command subprocesses.

- [ ] **Step 6: Commit metadata and static doctor support**

```bash
git add -- src/agent_maintainer/ecosystems/registry.py src/agent_maintainer/doctor/support/cpp_provider.py src/agent_maintainer/doctor/support/policy.py src/agent_maintainer/doctor/cli.py src/agent_maintainer/doctor/tach.domain.toml tests/catalogs/test_provider_registry.py tests/doctor/test_cpp_doctor.py
git commit -m "feat: diagnose C/C++ provider setup"
```

### Task 5: Publish the Phase 187 provider contract

**Files:**

- Create: `docs/cpp-cmake-provider.md`
- Modify: `docs/provider-status.md`
- Modify: `docs/configuration-reference.md`
- Modify: `README.md`
- Modify: `tests/docs/test_public_docs_prose.py`
- Modify: `tests/config/test_config_reference.py`

**Interfaces:**

- Consumes: the implemented Phase 187 defaults and doctor row names.
- Produces: honest public setup documentation and configuration-reference coverage.
- The docs must say commands are configured but not executed until Phase 188.

- [ ] **Step 1: Write failing documentation assertions**

Add assertions that require:

```python
provider_doc = Path("docs/cpp-cmake-provider.md").read_text(encoding="utf-8")
for phrase in (
    "C/C++ (CMake)",
    "experimental",
    "disabled by default",
    "repository-owned explicit command arrays",
    "Phase 187 does not execute",
    "Linux/GCC",
    "macOS/Clang",
    "Windows/MSVC",
):
    assert phrase in provider_doc
```

Extend config-reference tests to require every `CppCmakeConfig` field name and
`[tool.agent_maintainer.cpp]` in `docs/configuration-reference.md`.

- [ ] **Step 2: Run docs tests and confirm RED**

Run:

```bash
PATH=".venv/bin:$PATH" .venv/bin/pytest -q tests/docs/test_public_docs_prose.py tests/config/test_config_reference.py
```

Expected: tests fail because the public C/C++ provider document and reference
entries do not exist.

- [ ] **Step 3: Write exact public guidance**

Create `docs/cpp-cmake-provider.md` with these sections:

- Status: experimental, built in, disabled by default, Phase 187 foundation.
- Supported now: config loading, classification, suppression evidence, static
  doctor across Linux/GCC, macOS/Clang, and Windows/MSVC.
- Config example containing all five command arrays and all five profile fields.
- Command ownership: repository-owned explicit command arrays only; no shell,
  compiler/generator/preset/target/build-directory inference, install, or setup
  edit.
- Phase boundary: Phase 187 does not execute commands; Phase 188 adds execution
  and typed report declarations.
- Unsupported surface: report parsing, sanitizers, Meson/Bazel/Make/Autotools,
  blocking policy, promotion, and stable external provider API.
- Doctor rows and concrete repair actions.
- Links to the C/C++ roadmap, accepted boundary decision, and design spec.

Move C/C++ from `Approved Provider Experiment` into the current-provider table
in `docs/provider-status.md` with maturity `Experimental foundation`; its
current-support cell lists classification, config, suppression evidence, and
static doctor only. Update README's provider list with the same language.

Add all nested keys and defaults to `docs/configuration-reference.md`, including
the statement that report declarations are unavailable until Phase 188.

- [ ] **Step 4: Run public-doc and Markdown checks**

Run:

```bash
PATH=".venv/bin:$PATH" .venv/bin/pytest -q tests/docs/test_public_docs_prose.py tests/config/test_config_reference.py tests/packaging/test_public_docs.py
markdownlint-cli2 "**/*.md"
PATH=".venv/bin:$PATH" .venv/bin/python -m docsync check
```

Expected: all selected tests pass, Markdownlint reports zero errors, and DocSync
reports no drift.

- [ ] **Step 5: Commit public documentation**

```bash
git add -- docs/cpp-cmake-provider.md docs/provider-status.md docs/configuration-reference.md README.md tests/docs/test_public_docs_prose.py tests/config/test_config_reference.py
git commit -m "docs: publish C/C++ provider foundation"
```

### Task 6: Qualify Phase 187 without widening scope

**Files:**

- Modify only if verification exposes a Phase 187 defect in files already named
  by Tasks 1-5.

**Interfaces:**

- Consumes: all Phase 187 commits.
- Produces: fresh focused, architecture, documentation, broad, and CI-equivalent evidence.

- [ ] **Step 1: Run focused Phase 187 tests**

```bash
PATH=".venv/bin:$PATH" .venv/bin/pytest -q tests/config/test_cpp_config.py tests/ecosystems/test_cpp_classification.py tests/ecosystems/test_cpp_suppressions.py tests/catalogs/test_provider_registry.py tests/doctor/test_cpp_doctor.py tests/docs/test_public_docs_prose.py tests/config/test_config_reference.py
```

Expected: all focused tests pass with zero failures.

- [ ] **Step 2: Run ecosystem and config regression tests**

```bash
PATH=".venv/bin:$PATH" .venv/bin/pytest -q tests/config tests/ecosystems tests/catalogs/test_provider_registry.py tests/doctor/test_typescript_doctor.py tests/doctor/test_java_doctor.py tests/assess/test_reviewability_advisories.py tests/assess/test_reviewability_assessment.py
```

Expected: all selected regression tests pass with zero failures.

- [ ] **Step 3: Run repository architecture and documentation gates**

```bash
PATH=".venv/bin:$PATH" .venv/bin/python -m tach check
PATH=".venv/bin:$PATH" .venv/bin/python -m docsync check
markdownlint-cli2 "**/*.md"
PATH=".venv/bin:$PATH" .venv/bin/ruff check src tests
PATH=".venv/bin:$PATH" .venv/bin/pyright
```

Expected: each command exits zero with no architecture, DocSync, lint, or type
diagnostics.

- [ ] **Step 4: Run the repository's broad verification contract**

```bash
PATH=".venv/bin:$PATH" just doctor
PATH=".venv/bin:$PATH" just v
```

Expected: doctor and the full verifier exit zero. No C/C++ command runs because
the provider is disabled in the Agent Maintainer repository.

- [ ] **Step 5: Review the final diff and phase boundary**

```bash
git status --short --branch
git diff --stat origin/main...HEAD
git diff --check origin/main...HEAD
git log --oneline origin/main..HEAD
```

Expected: only Phase 187 config, classifier, suppressions, registry, doctor,
ownership, tests, and docs are present; no provider runtime, report parser,
workflow, dependency, or release file changed.

- [ ] **Step 6: Record Phase 187 completion after merge evidence**

After the pull request merges and protected post-merge checks pass, update
`docs/roadmap/phases/phase-187-cpp-classification-config-registry-doctor.md`
to `Status: complete`, mark Phase 187 complete in `docs/ROADMAP.md`, and record
the merge PR and check evidence in the phase card. Commit that evidence as:

```bash
git add -- docs/ROADMAP.md docs/roadmap/phases/phase-187-cpp-classification-config-registry-doctor.md
git commit -m "docs: record C/C++ foundation qualification"
```
