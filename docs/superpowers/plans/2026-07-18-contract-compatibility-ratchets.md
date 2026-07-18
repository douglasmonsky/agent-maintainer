# Contract And Compatibility Ratchets Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add repository-owned semantic contract ratchets that detect accidental config, CLI, Python API, JSON-RPC, and persistence drift and enforce exact revision, package-version, decision, and migration obligations.

**Architecture:** A new inward-facing `agent_maintainer.contracts` domain loads one strict TOML policy, extracts normalized descriptors through isolated adapters, compares base/current/live state, and returns deterministic compatibility reports. Thin root-CLI and verifier-catalog adapters expose advisory `diff`, enforcing `check`, and guarded `snapshot --write` workflows without importing verifier infrastructure into the domain.

**Tech Stack:** Python 3.11–3.14, frozen dataclasses, standard-library `ast`, `json`, `tomllib`, `hashlib`, and `subprocess`, existing `packaging.version.Version`, pytest, Tach exact dependency contracts, Archguard, and DocSync.

## Global Constraints

- Policy and report schema versions are exactly `1`.
- The authored policy is `.agent-maintainer/contracts.toml`; the generated baseline is `.agent-maintainer/contracts-baseline.json`.
- No target module import, target command execution, network access, shell evaluation, automatic package-version edit, migration rewrite, or broad baseline acceptance is allowed.
- Every configured path is repository-relative, canonical, confined, nonsymlinked, and bounded before reading or writing.
- Baseline output contains no timestamp, absolute path, environment value, or worktree-dirty state and is byte-identical for identical semantic facts.
- `diff` is advisory; `check` enforces; `snapshot --write` writes only after extraction and version obligations pass.
- Exit `0` means valid with no unresolved obligation, `1` means a compatibility/version/migration/decision/freshness finding, and `2` means invalid policy, baseline, Git, extractor, or path input.
- Breaking changes require an exact one-step contract revision increase and changed migration evidence.
- Stable breaking/additive changes require SemVer major/minor impact; Agent Maintainer beta changes use an explicit prerelease increment policy rather than an implied `0.2.0` bump.
- Review-required changes block until an exact SHA-256 fingerprint decision classifies them; wildcard, prefix, and suppress-all decisions are invalid.
- The optional verifier check activates only when `.agent-maintainer/contracts.toml` exists and never removes or suppresses another check.
- Human, JSON, and repair-fact output is deterministic, sorted, bounded, escaped, and free of raw untrusted payloads.
- No new runtime dependency is added.
- All fixtures use synthetic repository data.
- Use `PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH` for repository commands until a fresh project environment is established.

---

### Task 1: Establish The Cohesive Change And Contract Domain Models

**Files:**

- Create: `.agent-maintainer/change-plans/contract-compatibility-ratchets.md`
- Create: `src/agent_maintainer/contracts/__init__.py`
- Create: `src/agent_maintainer/contracts/models.py`
- Create: `src/agent_maintainer/contracts/limits.py`
- Create: `tests/contracts/__init__.py`
- Create: `tests/contracts/test_models.py`
- Modify: `docs/superpowers/specs/2026-07-18-contract-compatibility-ratchets-design.md`

**Interfaces:**

- Produces: `ContractPolicy`, `ContractSpec`, `ContractDecision`, `Descriptor`, `ContractBaseline`, `ContractChange`, `ContractObligation`, `RepairFact`, and `ContractReport` frozen dataclasses.
- Produces: `ContractError`, `PolicyError`, `BaselineError`, `ExtractionError`, and `GitContractError` bounded exception classes.
- Produces: exact literals `ContractKind`, `Classification`, and `VersionImpact`.
- Produces: shared limits `MAX_INPUT_BYTES = 1_000_000`, `MAX_CONTRACTS = 256`, `MAX_MEMBERS = 10_000`, `MAX_DEPTH = 64`, and `MAX_REPORT_ITEMS = 200`.

- [ ] **Step 1: Create the active cohesive change plan**

Create front matter with `id = "contract-compatibility-ratchets"`, `kind = "feature"`, `status = "active"`, `base_ref = "453a00f"`, `expires = 2026-08-15`, `requires_tests = true`, `requires_full_verify = true`, `max_changed_files = 90`, and `max_changed_lines = 7500`. Allow only the new contracts domain/tests, `.agent-maintainer/contracts*`, the four dogfood manifests/schemas, direct CLI/catalog/Tach/config/docs/roadmap/DocSync integration files, this approved spec/plan, and the Phase 184 roadmap record. Forbid `config/prod/**`, `.env`, and `.env.*`. Explain why the extractors, comparison kernel, policy, CLI, dogfood evidence, and enforcement gate are one cohesive public control layer and list rollback as reverting Phase 184 commits in reverse order.

Run:

```bash
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH python -m agent_maintainer change-plan check
```

Expected: `PASS change plans`.

- [ ] **Step 2: Write failing model-invariant tests**

```python
from dataclasses import FrozenInstanceError

import pytest

from agent_maintainer.contracts.models import ContractChange, Descriptor


def test_descriptor_is_immutable_and_semantic_only() -> None:
    descriptor = Descriptor(
        contract_id="docsync-api",
        kind="python-api",
        owner="docsync.api",
        stability="beta",
        revision=1,
        sources=("src/docsync/api.py",),
        body={"exports": []},
        fingerprint="sha256:abc",
    )

    with pytest.raises(FrozenInstanceError):
        descriptor.revision = 2  # type: ignore[misc]


def test_change_identity_contains_no_free_form_source_payload() -> None:
    change = ContractChange(
        contract_id="docsync-api",
        operation="member-remove",
        path="exports.check_repo",
        before="function",
        after=None,
        classification="breaking",
        fingerprint="sha256:def",
        reason="export removed",
    )

    assert change.identity() == (
        "docsync-api",
        "member-remove",
        "exports.check_repo",
        "sha256:def",
    )
```

- [ ] **Step 3: Run the model tests and verify RED**

```bash
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH pytest tests/contracts/test_models.py -q
```

Expected: collection fails because `agent_maintainer.contracts` does not exist.

- [ ] **Step 4: Implement the immutable domain vocabulary**

Use tuple collection fields and frozen dataclasses. Keep normalized bodies JSON-compatible while returning defensive copies from serialization boundaries.

```python
ContractKind = Literal[
    "config-capabilities",
    "cli-manifest",
    "python-api",
    "json-schema",
]
Classification = Literal["breaking", "compatible", "review-required"]
VersionImpact = Literal["none", "prerelease", "patch", "minor", "major"]


@dataclass(frozen=True)
class ContractSpec:
    id: str
    kind: ContractKind
    owner: str
    stability: str
    revision: int
    source: str
    exports: tuple[str, ...] = ()
    migration_paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class ContractChange:
    contract_id: str
    operation: str
    path: str
    before: object | None
    after: object | None
    classification: Classification
    fingerprint: str
    reason: str

    def identity(self) -> tuple[str, str, str, str]:
        return (self.contract_id, self.operation, self.path, self.fingerprint)
```

`ContractReport` must carry `schema_version`, mode, base availability, current/base package versions, descriptors, changes, obligations, decisions, repair facts, advisories, errors, and `can_snapshot`.

- [ ] **Step 5: Run focused tests and commit the model boundary**

```bash
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH pytest tests/contracts/test_models.py -q
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH python -m agent_maintainer change-plan check
git add -- .agent-maintainer/change-plans/contract-compatibility-ratchets.md docs/superpowers/specs/2026-07-18-contract-compatibility-ratchets-design.md src/agent_maintainer/contracts/__init__.py src/agent_maintainer/contracts/limits.py src/agent_maintainer/contracts/models.py tests/contracts/__init__.py tests/contracts/test_models.py
git commit -m "feat: add contract ratchet domain models"
```

Expected: model tests and the change-plan check pass; the commit succeeds through hooks.

### Task 2: Load Strict Authored Policy And Canonical Baselines

**Files:**

- Create: `src/agent_maintainer/contracts/policy.py`
- Create: `src/agent_maintainer/contracts/baseline.py`
- Create: `src/agent_maintainer/contracts/paths.py`
- Create: `tests/contracts/test_policy.py`
- Create: `tests/contracts/test_baseline.py`
- Create: `tests/contracts/test_paths.py`

**Interfaces:**

- Consumes: Task 1 models and `agent_maintainer.core.repo_paths.validate_repo_path`.
- Produces: `load_policy(repo_root: Path, path: Path = Path(".agent-maintainer/contracts.toml")) -> ContractPolicy | None`.
- Produces: `parse_policy(text: str, *, source: str) -> ContractPolicy` for Git blob loading.
- Produces: `load_baseline(repo_root: Path, path: Path = Path(".agent-maintainer/contracts-baseline.json")) -> ContractBaseline | None`.
- Produces: `parse_baseline(text: str, *, source: str) -> ContractBaseline`.
- Produces: `render_baseline(baseline: ContractBaseline) -> str` and `write_baseline_atomic(repo_root: Path, path: Path, baseline: ContractBaseline) -> None`.
- Produces: `canonical_json(value: object) -> str` and `fingerprint(value: object) -> str`.

- [ ] **Step 1: Write strict policy rejection tests**

Parameterize unsupported/missing version, unknown keys at every level, duplicate contract IDs, duplicate fingerprints, unsupported kinds, invalid owners/stability/revisions, wildcard fingerprints, absolute/parent/backslash/NUL paths, overlapping decisions, invalid PEP 440 sources, empty migration paths, and kind-specific keys used on the wrong extractor.

```python
def test_policy_loads_exact_contract_and_decision(tmp_path: Path) -> None:
    write_policy(
        tmp_path,
        """version = 1
package_version_file = "pyproject.toml"
pre_one_breaking = "prerelease"
stable_breaking = "major"

[[contracts]]
id = "docsync-api"
kind = "python-api"
owner = "docsync.api"
stability = "beta"
revision = 1
source = "src/docsync/api.py"
exports = ["*"]
migration_paths = ["CHANGELOG.md"]

[[decisions]]
contract = "docsync-api"
fingerprint = "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
classification = "breaking"
reason = "Documented beta migration."
""",
    )

    policy = load_policy(tmp_path)

    assert policy is not None
    assert policy.contracts[0].id == "docsync-api"
    assert policy.decisions[0].classification == "breaking"
```

- [ ] **Step 2: Write canonical baseline and atomic-write tests**

Cover stable ordering under reversed descriptor/member input, descriptor and document fingerprint verification, missing/duplicate contracts, unsupported schema/generator, symlink/special-file rejection, one-megabyte limit, noncanonical source paths, and failed replace preserving the old file.

```python
def test_render_baseline_is_byte_stable(sample_baseline: ContractBaseline) -> None:
    first = render_baseline(sample_baseline)
    second = render_baseline(reversed_baseline(sample_baseline))

    assert first == second
    assert first.endswith("\n")
    assert "created_at" not in first
    assert str(Path.cwd()) not in first


def test_tampered_descriptor_fingerprint_fails_closed(tmp_path: Path) -> None:
    path = write_baseline(tmp_path, descriptor_fingerprint="sha256:" + "0" * 64)

    with pytest.raises(BaselineError, match="fingerprint"):
        load_baseline(tmp_path, path.relative_to(tmp_path))
```

- [ ] **Step 3: Run policy/baseline tests and verify RED**

```bash
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH pytest tests/contracts/test_policy.py tests/contracts/test_baseline.py tests/contracts/test_paths.py -q
```

Expected: imports fail for the absent policy, baseline, and path modules.

- [ ] **Step 4: Implement confined reads, strict TOML, and canonical JSON**

Open files only after `lstat`, reject symlinks/nonregular files, enforce byte and UTF-8 limits, and validate resolved parents remain under the repository root. Validate allowed key sets before converting values. Canonical JSON uses sorted mapping keys, normalized sorted descriptor/member arrays, compact fingerprint bytes, and pretty output only at the final baseline boundary.

```python
def fingerprint(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=True,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def render_baseline(baseline: ContractBaseline) -> str:
    payload = baseline_to_dict(baseline, include_document_fingerprint=False)
    payload["document_fingerprint"] = fingerprint(payload)
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
```

Atomic writes create a mode-`0o600` temporary regular file in the destination directory, `fsync` it, revalidate the destination parent, and replace only the exact configured baseline path. Cleanup removes only the named temporary file created by that call.

- [ ] **Step 5: Run focused tests and commit storage boundaries**

```bash
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH pytest tests/contracts/test_policy.py tests/contracts/test_baseline.py tests/contracts/test_paths.py -q
git add -- src/agent_maintainer/contracts/baseline.py src/agent_maintainer/contracts/paths.py src/agent_maintainer/contracts/policy.py tests/contracts/test_baseline.py tests/contracts/test_paths.py tests/contracts/test_policy.py
git commit -m "feat: load contract policy and baselines"
```

Expected: all strict decoding and storage tests pass.

### Task 3: Add The Extractor Protocol, Config Capabilities, And CLI Manifest

**Files:**

- Create: `src/agent_maintainer/contracts/extraction.py`
- Create: `src/agent_maintainer/contracts/extractors/__init__.py`
- Create: `src/agent_maintainer/contracts/extractors/config_capabilities.py`
- Create: `src/agent_maintainer/contracts/extractors/cli_manifest.py`
- Create: `tests/contracts/test_extraction.py`
- Create: `tests/contracts/extractors/test_config_capabilities.py`
- Create: `tests/contracts/extractors/test_cli_manifest.py`

**Interfaces:**

- Produces: `Extractor(Protocol)` with `extract(repo_root: Path, spec: ContractSpec) -> Descriptor`.
- Produces: `extract_contract(repo_root: Path, spec: ContractSpec) -> Descriptor` and `extract_all(repo_root: Path, policy: ContractPolicy) -> tuple[Descriptor, ...]`.
- Produces: `extract_config_capabilities(repo_root: Path, spec: ContractSpec) -> Descriptor` and `extract_cli_manifest(repo_root: Path, spec: ContractSpec) -> Descriptor`.
- Normalizes members as sorted mappings with exact `name`, `kind`, `required`, `default`, `choices`, `constraints`, `aliases`, `environment`, and `stability` keys.

- [ ] **Step 1: Write routing and bounded-failure tests**

```python
def test_extract_all_is_sorted_by_contract_id(monkeypatch, tmp_path: Path) -> None:
    observed: list[str] = []

    def fake_extract(root: Path, spec: ContractSpec) -> Descriptor:
        observed.append(spec.id)
        return descriptor_for(spec)

    monkeypatch.setattr(extraction, "extract_contract", fake_extract)
    descriptors = extraction.extract_all(tmp_path, policy_with_contracts("z", "a"))

    assert tuple(item.contract_id for item in descriptors) == ("a", "z")
    assert observed == ["a", "z"]
```

Also assert unknown kinds cannot reach routing, one extractor error identifies only the normalized contract ID/path, and aggregate extraction stops without returning partial baseline data.

- [ ] **Step 2: Write config and CLI normalization matrices**

Config tests cover nested tables, value kinds, JSON scalar/list/object defaults, sorted choices, numeric bounds, aliases, environment names, stability, duplicate fields, hostile control text, non-finite numbers, and member limits. CLI tests cover console scripts, nested command paths, option aliases, requiredness, multiplicity, choices, defaults, positional arguments, exit statuses, duplicate command/option identities, and unknown keys.

```python
def test_cli_option_normalizes_aliases_and_multiplicity(tmp_path: Path) -> None:
    write_json(
        tmp_path / "config/cli.json",
        {
            "schema_version": 1,
            "console_scripts": ["agent-maintainer"],
            "commands": [
                {
                    "path": ["contract", "check"],
                    "exit_statuses": [0, 1, 2],
                    "options": [
                        {
                            "name": "base-ref",
                            "aliases": ["-b"],
                            "kind": "string",
                            "required": False,
                            "multiple": False,
                            "default": "origin/main",
                        }
                    ],
                }
            ],
        },
    )

    descriptor = extract_cli_manifest(tmp_path, cli_spec("config/cli.json"))

    assert descriptor.body["commands"][0]["options"][0]["aliases"] == ["-b"]
```

- [ ] **Step 3: Run extractor tests and verify RED**

```bash
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH pytest tests/contracts/test_extraction.py tests/contracts/extractors/test_config_capabilities.py tests/contracts/extractors/test_cli_manifest.py -q
```

Expected: imports fail for the absent extraction package.

- [ ] **Step 4: Implement pure-data extraction and fingerprinting**

Each adapter reads one confined JSON document, validates exact schema keys/types and limits, sorts identity-bearing arrays, constructs a semantic body, and calls one shared descriptor builder.

```python
def build_descriptor(spec: ContractSpec, body: dict[str, object]) -> Descriptor:
    semantic = {
        "contract_id": spec.id,
        "kind": spec.kind,
        "owner": spec.owner,
        "stability": spec.stability,
        "revision": spec.revision,
        "sources": [spec.source],
        "body": body,
    }
    return Descriptor(
        contract_id=spec.id,
        kind=spec.kind,
        owner=spec.owner,
        stability=spec.stability,
        revision=spec.revision,
        sources=(spec.source,),
        body=body,
        fingerprint=fingerprint(semantic),
    )
```

- [ ] **Step 5: Run focused tests and commit the first adapters**

```bash
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH pytest tests/contracts/test_extraction.py tests/contracts/extractors/test_config_capabilities.py tests/contracts/extractors/test_cli_manifest.py -q
git add -- src/agent_maintainer/contracts/extraction.py src/agent_maintainer/contracts/extractors/__init__.py src/agent_maintainer/contracts/extractors/cli_manifest.py src/agent_maintainer/contracts/extractors/config_capabilities.py tests/contracts/test_extraction.py tests/contracts/extractors/test_cli_manifest.py tests/contracts/extractors/test_config_capabilities.py
git commit -m "feat: extract config and CLI contracts"
```

Expected: routing and both adapter suites pass.

### Task 4: Extract Nominated Python APIs Without Importing Code

**Files:**

- Create: `src/agent_maintainer/contracts/extractors/python_api.py`
- Create: `tests/contracts/extractors/test_python_api.py`
- Modify: `src/agent_maintainer/contracts/extraction.py`

**Interfaces:**

- Consumes: Task 3 descriptor builder and validated `ContractSpec.exports`.
- Produces: `extract_python_api(repo_root: Path, spec: ContractSpec) -> Descriptor`.
- Normalizes functions, async functions, classes, methods, parameters, annotations, and explicitly significant literal constants without evaluating or importing the module.

- [ ] **Step 1: Write AST extraction and compatibility-shape tests**

Cover explicit `__all__`, policy-nominated names, `exports = ["*"]`, functions/classes/constants, positional-only/positional-or-keyword/vararg/keyword-only/kwargs ordering, default presence without default evaluation, async state, return annotations, decorators excluded from contract identity, nested/private names excluded, and deterministic source-order independence.

```python
def test_python_function_signature_is_normalized_without_import(tmp_path: Path) -> None:
    source = tmp_path / "src/public.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        "__all__ = ['fetch']\n"
        "def fetch(item: str, /, limit: int = 10, *, strict: bool = False) -> list[str]:\n"
        "    raise RuntimeError('must not execute')\n",
        encoding="utf-8",
    )

    descriptor = extract_python_api(tmp_path, python_spec("src/public.py", ("*",)))

    function = descriptor.body["exports"][0]
    assert function["name"] == "fetch"
    assert [item["kind"] for item in function["parameters"]] == [
        "positional-only",
        "positional-or-keyword",
        "keyword-only",
    ]
    assert function["return_annotation"] == "list[str]"
```

Adversarial cases must reject syntax errors, dynamic `__all__`, star imports used as export discovery, computed constant values, unsafe annotation nodes, excessive AST depth/member count, duplicate definitions, and files that change a sentinel proving imports were never executed.

- [ ] **Step 2: Run Python extractor tests and verify RED**

```bash
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH pytest tests/contracts/extractors/test_python_api.py -q
```

Expected: import failure because `python_api.py` is absent.

- [ ] **Step 3: Implement a strict AST-only normalizer**

Parse with `ast.parse`; accept annotation nodes composed only of `Name`, `Attribute`, `Subscript`, `Tuple`, `List`, `BinOp(BitOr)`, `Constant(None/string)`, and `Load`; render them with `ast.unparse` after validation. Record defaults only as `has_default`; record significant constants only when the policy names them and `ast.literal_eval` returns bounded JSON data.

```python
def _parameter(name: str, kind: str, annotation: ast.expr | None, has_default: bool) -> dict[str, object]:
    return {
        "annotation": _annotation_text(annotation),
        "has_default": has_default,
        "kind": kind,
        "name": name,
    }
```

Class extraction includes public methods and class attributes only when the class itself is nominated. Function bodies, docstrings, local definitions, and private members never enter the descriptor.

- [ ] **Step 4: Run focused tests and commit the Python adapter**

```bash
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH pytest tests/contracts/extractors/test_python_api.py tests/contracts/test_extraction.py -q
git add -- src/agent_maintainer/contracts/extraction.py src/agent_maintainer/contracts/extractors/python_api.py tests/contracts/extractors/test_python_api.py
git commit -m "feat: extract nominated Python API contracts"
```

Expected: AST and routing suites pass without importing fixtures.

### Task 5: Extract The Supported Structural JSON Schema Subset

**Files:**

- Create: `src/agent_maintainer/contracts/extractors/json_schema.py`
- Create: `tests/contracts/extractors/test_json_schema.py`
- Modify: `src/agent_maintainer/contracts/extraction.py`

**Interfaces:**

- Produces: `extract_json_schema(repo_root: Path, spec: ContractSpec) -> Descriptor`.
- Supports: `$id`, `type`, `properties`, `required`, `additionalProperties`, `items`, `enum`, `const`, numeric/string bounds, and local `$defs`/`$ref`.
- Emits: `unsupported_semantics` entries for known-but-unproved composition such as `oneOf`, `anyOf`, `allOf`, `not`, `if`, `then`, and `else`.

- [ ] **Step 1: Write supported-subset tests**

```python
def test_json_schema_normalizes_required_properties_and_local_ref(tmp_path: Path) -> None:
    write_json(
        tmp_path / "schemas/record.json",
        {
            "$id": "urn:record",
            "$defs": {"id": {"type": "string", "minLength": 1}},
            "type": "object",
            "properties": {
                "id": {"$ref": "#/$defs/id"},
                "note": {"type": ["string", "null"]},
            },
            "required": ["id"],
            "additionalProperties": False,
        },
    )

    descriptor = extract_json_schema(tmp_path, schema_spec("schemas/record.json"))

    assert descriptor.body["properties"]["id"]["required"] is True
    assert descriptor.body["properties"]["note"]["types"] == ["null", "string"]
    assert descriptor.body["additional_properties"] is False
```

Cover enum/const, integer/number/string/array/object/null/boolean types, inclusive/exclusive numeric bounds, string lengths/pattern, array items, deterministic property ordering, and nullable unions.

- [ ] **Step 2: Write adversarial reference and ambiguity tests**

Reject remote/file refs, path traversal, missing fragments, reference cycles, depth over 64, excessive properties, duplicate JSON keys, non-finite numbers, invalid regex/control text, and malformed required/property relationships. Assert supported composition keywords emit exact review-required semantic entries instead of guessed merged schemas.

- [ ] **Step 3: Run JSON Schema tests and verify RED**

```bash
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH pytest tests/contracts/extractors/test_json_schema.py -q
```

Expected: import failure because `json_schema.py` is absent.

- [ ] **Step 4: Implement bounded local resolution**

Load JSON with an `object_pairs_hook` that rejects duplicate keys. Resolve only `#/$defs/<escaped-name>` fragments and repository-confined explicitly configured local schema sources; track `(source, fragment)` on a stack and enforce depth/member limits.

```python
def _resolve_ref(context: SchemaContext, reference: str) -> dict[str, object]:
    if not reference.startswith("#/$defs/"):
        raise ExtractionError(context.contract_id, "unsupported or unsafe JSON reference")
    name = reference.removeprefix("#/$defs/").replace("~1", "/").replace("~0", "~")
    identity = (context.source, name)
    if identity in context.stack:
        raise ExtractionError(context.contract_id, "JSON reference cycle")
    return context.resolve_local_definition(name)
```

- [ ] **Step 5: Run focused tests and commit the schema adapter**

```bash
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH pytest tests/contracts/extractors/test_json_schema.py tests/contracts/test_extraction.py -q
git add -- src/agent_maintainer/contracts/extraction.py src/agent_maintainer/contracts/extractors/json_schema.py tests/contracts/extractors/test_json_schema.py
git commit -m "feat: extract structural JSON Schema contracts"
```

Expected: schema and routing suites pass.

### Task 6: Compare Descriptors And Classify Exact Semantic Changes

**Files:**

- Create: `src/agent_maintainer/contracts/comparison.py`
- Create: `src/agent_maintainer/contracts/classifiers.py`
- Create: `tests/contracts/test_comparison.py`
- Create: `tests/contracts/test_classifiers.py`

**Interfaces:**

- Produces: `compare_descriptors(base: Sequence[Descriptor], current: Sequence[Descriptor], decisions: Sequence[ContractDecision]) -> tuple[ContractChange, ...]`.
- Produces: exact operations `contract-add`, `contract-remove`, `member-add`, `member-remove`, `member-rename`, `type-change`, `requiredness-change`, `default-change`, `constraint-change`, `alias-change`, and `unsupported-semantic-change`.
- Produces: `change_fingerprint(contract_id, operation, path, before, after) -> str` independent of classification and decision reason.

- [ ] **Step 1: Write the shared operation matrix**

Table-drive every operation across contract kinds. Assert contract/member removal, optional-to-required, type narrowing, config default change, CLI command/option removal, newly required Python parameter, positional reorder, persisted key removal, tightened constraints, and closing `additionalProperties` are breaking. Assert optional additions with defaults, new command/optional option, nominated export, optional trailing parameter, type widening, and aliases preserving canonical identity are compatible.

```python
@pytest.mark.parametrize(
    ("before", "after", "classification"),
    (
        ({"required": False}, {"required": True}, "breaking"),
        ({"types": ["string"]}, {"types": ["null", "string"]}, "compatible"),
        ({"enum": ["a"]}, {"enum": ["a", "b"]}, "review-required"),
    ),
)
def test_property_change_matrix(before: object, after: object, classification: str) -> None:
    changes = compare_descriptors(
        (schema_descriptor(property_value=before),),
        (schema_descriptor(property_value=after),),
        (),
    )
    assert changes[0].classification == classification
```

- [ ] **Step 2: Write fingerprint-decision tests**

Assert fingerprints are stable under mapping order, differ when semantic before/after changes, cannot contain wildcards, cannot classify another contract, and resolve only one exact review-required finding. A decision may change `review-required` to `breaking` or `compatible`; it cannot waive freshness, revision, package, or migration obligations.

- [ ] **Step 3: Run comparison tests and verify RED**

```bash
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH pytest tests/contracts/test_comparison.py tests/contracts/test_classifiers.py -q
```

Expected: imports fail for missing comparison modules.

- [ ] **Step 4: Implement recursive semantic diff and kind classifiers**

Index contracts/members by validated identity, produce one operation per changed semantic leaf, and sort by `(contract_id, path, operation, fingerprint)`. Inferred renames and alias conflicts remain review-required. Apply exact decisions only after computing the original fingerprint.

```python
def change_fingerprint(
    contract_id: str,
    operation: str,
    path: str,
    before: object | None,
    after: object | None,
) -> str:
    return fingerprint(
        {
            "after": after,
            "before": before,
            "contract_id": contract_id,
            "operation": operation,
            "path": path,
        }
    )
```

- [ ] **Step 5: Run focused tests and commit semantic comparison**

```bash
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH pytest tests/contracts/test_comparison.py tests/contracts/test_classifiers.py -q
git add -- src/agent_maintainer/contracts/classifiers.py src/agent_maintainer/contracts/comparison.py tests/contracts/test_classifiers.py tests/contracts/test_comparison.py
git commit -m "feat: classify semantic contract changes"
```

Expected: the full compatibility matrix and decision tests pass.

### Task 7: Enforce Contract Revisions, Package Versions, And Migration Evidence

**Files:**

- Create: `src/agent_maintainer/contracts/versioning.py`
- Create: `src/agent_maintainer/contracts/migrations.py`
- Create: `tests/contracts/test_versioning.py`
- Create: `tests/contracts/test_migrations.py`

**Interfaces:**

- Produces: `contract_revision_obligations(base_policy: ContractPolicy, current_policy: ContractPolicy, changes: Sequence[ContractChange]) -> tuple[ContractObligation, ...]`.
- Produces: `package_version_obligation(base_version: str, current_version: str, policy: ContractPolicy, changes: Sequence[ContractChange]) -> ContractObligation`.
- Produces: `recommended_version(base: Version, impact: VersionImpact) -> Version | None`.
- Produces: `read_package_version(repo_root: Path, configured_path: str) -> str` for the exact `[project].version` value in the configured `pyproject.toml`.
- Produces: `migration_obligations(policy: ContractPolicy, changes: Sequence[ContractChange], git_changes: Sequence[GitPathChange]) -> tuple[ContractObligation, ...]`.

- [ ] **Step 1: Write revision and version matrices**

Cover exact `+1` revision on breaking changes, compatible/no-change revision stability, decrease, skip, driftless increase, new/removed contract handling, strict `[project].version` loading, stable `major/minor/patch`, beta `0.1.0b9 -> 0.1.0b10`, final-to-prerelease ambiguity, local/dev version normalization, and an actual version below/equal/above the recommendation.

```python
@pytest.mark.parametrize(
    ("base", "impact", "expected"),
    (
        ("0.1.0b9", "prerelease", "0.1.0b10"),
        ("1.4.2", "patch", "1.4.3"),
        ("1.4.2", "minor", "1.5.0"),
        ("1.4.2", "major", "2.0.0"),
    ),
)
def test_recommended_versions(base: str, impact: str, expected: str) -> None:
    assert str(recommended_version(Version(base), impact)) == expected
```

- [ ] **Step 2: Write migration evidence tests**

Use `GitPathChange` facts to prove a breaking contract is satisfied only by an added/modified/renamed destination matching one configured migration path. Deleted source evidence, unchanged existing docs, paths belonging to another contract, and glob prefix confusion must fail. Report exact missing paths and breaking fingerprints.

```python
def test_deleted_migration_document_does_not_satisfy_break(tmp_path: Path) -> None:
    obligations = migration_obligations(
        policy_with_migration("docs/upgrading.md"),
        (breaking_change("sha256:" + "a" * 64),),
        (GitPathChange("docs/upgrading.md", "deleted"),),
    )
    assert obligations[0].status == "unresolved"
```

- [ ] **Step 3: Run obligation tests and verify RED**

```bash
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH pytest tests/contracts/test_versioning.py tests/contracts/test_migrations.py -q
```

Expected: imports fail for missing obligation modules.

- [ ] **Step 4: Implement independent obligations**

Aggregate the strongest impact with `none < prerelease < patch < minor < major`. Breaking beta contracts use the configured `pre_one_breaking`; stable contracts use configured stable rules. Use `packaging.version.Version` for parsing/comparison and return an unresolved bounded obligation when a concrete recommendation is ambiguous.

Migration matching reuses Phase 183 segment-aware patterns but accepts only current/destination evidence paths from structured Git changes.

- [ ] **Step 5: Run focused tests and commit obligations**

```bash
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH pytest tests/contracts/test_versioning.py tests/contracts/test_migrations.py -q
git add -- src/agent_maintainer/contracts/migrations.py src/agent_maintainer/contracts/versioning.py tests/contracts/test_migrations.py tests/contracts/test_versioning.py
git commit -m "feat: enforce contract change obligations"
```

Expected: revision, package, and migration matrices pass.

### Task 8: Build The Base/Current/Live Anti-Bypass Service

**Files:**

- Create: `src/agent_maintainer/contracts/git_base.py`
- Create: `src/agent_maintainer/contracts/service.py`
- Create: `tests/contracts/test_git_base.py`
- Create: `tests/contracts/test_service.py`

**Interfaces:**

- Produces: `resolve_base_commit(repo_root: Path, base_ref: str) -> str`.
- Produces: `read_base_contract_files(repo_root: Path, base_ref: str) -> BaseContractState | None` using bounded `git show` blobs.
- Produces: `build_contract_report(repo_root: Path, *, base_ref: str, mode: str, initialize: bool = False) -> ContractReport`.
- Proves: checked-in current baseline exactly equals live extraction before historical comparison.

- [ ] **Step 1: Write bounded Git-base tests**

Cover valid refs resolved to hex commits, option-shaped/malformed refs, missing base files, partial base state, oversized blobs, invalid UTF-8, subprocess failure, symlink-like tree entries, and commands terminated with `--`. Assert no shell is used and error text contains only bounded ref/path identity.

```python
def test_base_ref_is_resolved_before_blob_reads(monkeypatch, tmp_path: Path) -> None:
    runner = RecordingGitRunner(
        outputs=(b"a" * 40 + b"\n", valid_policy_bytes(), valid_baseline_bytes())
    )
    monkeypatch.setattr(git_base, "run_git", runner)

    state = read_base_contract_files(tmp_path, "origin/main")

    assert state is not None
    assert runner.commands[0][-2:] == ("origin/main^{commit}", "--")
    assert all("origin/main" not in part for part in runner.commands[1:])
```

- [ ] **Step 2: Write three-way anti-bypass tests**

Test current baseline/live mismatch, rewritten current baseline hiding a break, base descriptor/current live break, absent usable base, initialization with no baseline, initialization rejected when baseline exists, decision resolution, revision/version/migration combinations, and deterministic report ordering.

```python
def test_rewriting_current_baseline_cannot_hide_live_break(repo: ContractRepo) -> None:
    repo.commit_base_contract(function="old")
    repo.write_current_contract(function="new")
    repo.write_current_baseline_for(function="new")

    report = build_contract_report(repo.path, base_ref=repo.base_sha, mode="check")

    assert any(change.operation == "member-remove" for change in report.changes)
    assert any(item.kind == "contract-revision" for item in report.obligations)
```

- [ ] **Step 3: Run service tests and verify RED**

```bash
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH pytest tests/contracts/test_git_base.py tests/contracts/test_service.py -q
```

Expected: imports fail for missing service modules.

- [ ] **Step 4: Implement ordered three-way evaluation**

Evaluation order is: load current policy; extract live descriptors; load current baseline; reject freshness mismatch; load optional base policy/baseline; compare base descriptors to current live; read structured Git changes once; compute decisions, revisions, package version, and migration obligations; derive one sorted repair fact per unresolved change or obligation with exact contract ID, fingerprint, summary, and inspect command; set `can_snapshot` only when no invalid or unresolved obligation exists.

```python
def _baseline_is_fresh(
    baseline: ContractBaseline,
    descriptors: tuple[Descriptor, ...],
) -> bool:
    return tuple(item.fingerprint for item in baseline.descriptors) == tuple(
        item.fingerprint for item in descriptors
    )
```

When no usable base exists, report freshness normally and add exactly one historical-compatibility-unavailable advisory. Initialization creates no retroactive change set.

- [ ] **Step 5: Run focused tests and commit orchestration**

```bash
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH pytest tests/contracts/test_git_base.py tests/contracts/test_service.py tests/contracts/test_comparison.py tests/contracts/test_versioning.py tests/contracts/test_migrations.py -q
git add -- src/agent_maintainer/contracts/git_base.py src/agent_maintainer/contracts/service.py tests/contracts/test_git_base.py tests/contracts/test_service.py
git commit -m "feat: enforce three-way contract ratchets"
```

Expected: base/current/live and obligation integration suites pass.

### Task 9: Render Deterministic Reports And Expose Contract Commands

**Files:**

- Create: `src/agent_maintainer/contracts/reporting.py`
- Create: `src/agent_maintainer/contracts/cli.py`
- Create: `tests/contracts/test_reporting.py`
- Create: `tests/contracts/test_cli.py`

**Interfaces:**

- Produces: `report_to_dict(report: ContractReport) -> dict[str, object]`, `render_json(report: ContractReport) -> str`, and `render_text(report: ContractReport) -> str`.
- Produces: `main(argv: list[str] | None = None) -> int` for `diff`, `check`, and `snapshot --write`.
- Produces: complete JSON on stdout for the verifier's existing run-scoped captured log; `diff` and `check` never write a generated repository file.

- [ ] **Step 1: Write exact report-schema tests**

Assert schema version, sorted contracts/changes/obligations/decisions/repair facts, one trailing newline, no timestamp or absolute path, bounded human sections, ASCII-escaped control text, stable identical output, and fingerprints in both changes and repair facts.

```python
def test_json_report_is_byte_stable(sample_report: ContractReport) -> None:
    first = render_json(sample_report)
    second = render_json(sample_report)

    assert first == second
    assert first.endswith("\n")
    assert json.loads(first)["schema_version"] == 1
    assert "timestamp" not in first
```

- [ ] **Step 2: Write CLI exit and write-safety tests**

Cover advisory `diff` returning `0` with findings, clean/blocked/invalid `check` returning `0/1/2`, JSON equivalence, default/custom base ref, snapshot requiring literal `--write`, initialization, refusal when obligations fail, no writes from diff/check, atomic write success, and root-relative target handling.

```python
def test_snapshot_requires_explicit_write(capsys: pytest.CaptureFixture[str]) -> None:
    status = cli.main(["snapshot"])

    assert status == 2
    assert "snapshot requires --write" in capsys.readouterr().err


def test_diff_is_advisory_with_breaking_findings(monkeypatch) -> None:
    monkeypatch.setattr(cli, "build_contract_report", lambda *args, **kwargs: blocked_report())
    assert cli.main(["diff", "--json"]) == 0
```

- [ ] **Step 3: Run reporting/CLI tests and verify RED**

```bash
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH pytest tests/contracts/test_reporting.py tests/contracts/test_cli.py -q
```

Expected: imports fail for missing reporting and CLI modules.

- [ ] **Step 4: Implement intentional rendering and command parsing**

Build explicit dictionaries rather than generic dataclass serialization. Limit every human section to `MAX_REPORT_ITEMS`, escape through JSON string encoding, and point overflow to `--json`. Parse with subparsers and a shared `--target`, `--base-ref`, and `--json` parent.

```python
def _status(command: str, report: ContractReport) -> int:
    if report.errors:
        return 2
    if command == "diff":
        return 0
    return 1 if report.unresolved else 0
```

For snapshot, build the prospective baseline from live descriptors and current package version, then call the Task 2 atomic writer only when `report.can_snapshot` is true.

- [ ] **Step 5: Run focused tests and commit public contract commands**

```bash
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH pytest tests/contracts/test_reporting.py tests/contracts/test_cli.py -q
git add -- src/agent_maintainer/contracts/cli.py src/agent_maintainer/contracts/reporting.py tests/contracts/test_cli.py tests/contracts/test_reporting.py
git commit -m "feat: expose contract ratchet commands"
```

Expected: reporting and all command exit/write semantics pass.

### Task 10: Add Root CLI, Catalog, Captured-Log, And Architecture Integration

**Files:**

- Modify: `src/agent_maintainer/cli.py`
- Modify: `src/agent_maintainer/catalogs/global_checks.py`
- Modify: `src/agent_maintainer/catalogs/catalog.py`
- Modify: `src/agent_maintainer/verify/groups.py`
- Modify: `src/agent_maintainer/core/executor.py`
- Modify: `src/agent_maintainer/contracts/tach.domain.toml`
- Modify: `src/agent_maintainer/catalogs/tach.domain.toml`
- Modify: `tach.toml`
- Create: `tests/catalogs/test_contract_catalog.py`
- Modify: `tests/packaging/test_script_helpers.py`
- Modify: `tests/verify/test_verification_groups.py`

**Interfaces:**

- Produces: root route `agent-maintainer contract ...` through `preflight.lazy_target_command`.
- Produces: optional check named `contract-compatibility` in fast, precommit, full, and CI profiles.
- Command: `python -m agent_maintainer contract check --base-ref REF --json` or staged equivalent.
- Artifact: `.verify-logs/contract-compatibility.json` retained by normal verifier artifacts.

- [ ] **Step 1: Write root dispatch and catalog tests**

```python
def test_contract_check_is_optional_and_exact() -> None:
    check = next(
        item
        for item in make_checks(MaintainerConfig(), "HEAD", "origin/main")
        if item.name == "contract-compatibility"
    )

    assert check.profiles == models.ALL_PROFILES
    assert check.required_paths == (".agent-maintainer/contracts.toml",)
    assert check.command[-5:] == [
        "contract",
        "check",
        "--base-ref",
        "HEAD",
        "--json",
    ]
```

Also assert staged mode uses `--staged` only if added to the public contract CLI, missing policy has the exact optional skip reason, check order is stable, every verifier group assigns the check, help lists `contract`, and lazy dispatch does not import contract extractors for unrelated commands.

- [ ] **Step 2: Run integration tests and verify RED**

```bash
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH pytest tests/catalogs/test_contract_catalog.py tests/packaging/test_script_helpers.py tests/verify/test_verification_groups.py -q
```

Expected: failures show the route and catalog check are absent.

- [ ] **Step 3: Implement thin adapters and exact dependency contracts**

```python
def contract_compatibility_check(base_ref: str) -> models.Check:
    return models.Check(
        "contract-compatibility",
        [
            sys.executable,
            "-m",
            "agent_maintainer",
            "contract",
            "check",
            "--base-ref",
            base_ref,
            "--json",
        ],
        models.ALL_PROFILES,
        required_paths=(".agent-maintainer/contracts.toml",),
        optional_skip_reason=(
            ".agent-maintainer/contracts.toml is absent; contract compatibility is not configured"
        ),
        optional_skip_status=models.SKIP_STATUS_MISSING_OPTIONAL,
    )
```

The contracts Tach root depends on no CLI/catalog/verifier modules. Only `cli` may depend on `service`, `reporting`, and `baseline`; catalog integration invokes the public root command as a subprocess description.

- [ ] **Step 4: Run integration and exact architecture checks**

```bash
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH pytest tests/catalogs/test_contract_catalog.py tests/packaging/test_script_helpers.py tests/verify/test_verification_groups.py -q
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH tach check
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH python -m archguard decision-check --base-ref 453a00f
```

Expected: integration, Tach, and the pre-existing decision check pass at this intermediate state without relaxing root strictness.

- [ ] **Step 5: Commit enforcement integration**

```bash
git add -- src/agent_maintainer/catalogs/catalog.py src/agent_maintainer/catalogs/global_checks.py src/agent_maintainer/catalogs/tach.domain.toml src/agent_maintainer/cli.py src/agent_maintainer/contracts/tach.domain.toml src/agent_maintainer/core/executor.py src/agent_maintainer/verify/groups.py tach.toml tests/catalogs/test_contract_catalog.py tests/packaging/test_script_helpers.py tests/verify/test_verification_groups.py
git commit -m "feat: enforce configured contract compatibility"
```

Expected: commit hooks pass.

### Task 11: Dogfood Five Agent Maintainer Contract Surfaces

**Files:**

- Create: `.agent-maintainer/contracts.toml`
- Create: `.agent-maintainer/contracts-baseline.json`
- Create: `config/agent-maintainer-cli.json`
- Create: `schemas/codex-app-server-wait.schema.json`
- Create: `schemas/agent-waits-wait-record.schema.json`
- Create: `tests/contracts/test_dogfood.py`
- Modify: `tests/config/test_config_reference.py`
- Modify: `tests/wait/test_codex_app_server.py`
- Modify: `tests/wait/test_agent_waits_core.py`
- Modify: `config/agent-maintainer-capabilities.json`

**Interfaces:**

- Config contract source: `config/agent-maintainer-capabilities.json`.
- CLI contract source: `config/agent-maintainer-cli.json`.
- Python API source: `src/docsync/api.py` with nominated public exports.
- JSON-RPC source: `schemas/codex-app-server-wait.schema.json`.
- Persistence source: `schemas/agent-waits-wait-record.schema.json`.

- [ ] **Step 1: Write dogfood freshness tests before manifests**

```python
def test_cli_manifest_matches_public_root_commands() -> None:
    payload = load_json(Path("config/agent-maintainer-cli.json"))
    manifested = {item["path"][0] for item in payload["commands"] if len(item["path"]) == 1}

    assert manifested == set(agent_cli.command_handlers())


def test_wait_record_schema_matches_serialized_keys(sample_wait_record: WaitRecord) -> None:
    schema = load_json(Path("schemas/agent-waits-wait-record.schema.json"))
    assert set(schema["properties"]) == set(sample_wait_record.as_dict())
    assert set(schema["required"]) <= set(sample_wait_record.as_dict())
```

JSON-RPC freshness tests validate every request produced by `app_server_messages` and `app_server_probe_messages` against the checked-in structural schema without executing an app server. Config freshness remains tied to `config.reference.render_capabilities_json()`.

- [ ] **Step 2: Run dogfood tests and verify RED**

```bash
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH pytest tests/contracts/test_dogfood.py tests/config/test_config_reference.py tests/wait/test_codex_app_server.py tests/wait/test_agent_waits_core.py -q
```

Expected: missing manifest/schema/policy failures identify the five unrecorded contracts.

- [ ] **Step 3: Add strict policy and source-backed manifests**

Use contract IDs `agent-maintainer-config`, `agent-maintainer-cli`, `docsync-api`, `codex-app-server-wait`, and `agent-waits-wait-record`, each at revision `1`, beta stability, and explicit owner. Set `package_version_file = "pyproject.toml"`, `pre_one_breaking = "prerelease"`, and `stable_breaking = "major"`. Configure migration paths as `CHANGELOG.md` plus `docs/upgrading-to-*.md`.

The wait-record schema names all serialized keys, permits the conditional compatibility `pr_number`, and keeps `additionalProperties = false`. The app-server schema covers initialize, initialized, thread/resume, thread/read, turn/start, response, and terminal notification shapes actually consumed or emitted by the client.

- [ ] **Step 4: Generate and prove the initial baseline**

```bash
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH python -m agent_maintainer contract snapshot --write --initialize
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH python -m agent_maintainer contract check --base-ref 453a00f --json
```

Expected: snapshot reports five initialized contracts and check exits `0` with baseline freshness true and historical compatibility unavailable for initial adoption.

- [ ] **Step 5: Run dogfood regression suites and commit initial contracts**

```bash
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH pytest tests/contracts tests/config/test_config_reference.py tests/wait/test_codex_app_server.py tests/wait/test_agent_waits_core.py -q
git add -- .agent-maintainer/contracts-baseline.json .agent-maintainer/contracts.toml config/agent-maintainer-capabilities.json config/agent-maintainer-cli.json schemas/agent-waits-wait-record.schema.json schemas/codex-app-server-wait.schema.json tests/config/test_config_reference.py tests/contracts/test_dogfood.py tests/wait/test_agent_waits_core.py tests/wait/test_codex_app_server.py
git commit -m "feat: dogfood contract compatibility ratchets"
```

Expected: the complete contracts suite and source-manifest freshness tests pass.

### Task 12: Document The Boundary And Qualify Phase 184

**Files:**

- Create: `docs/architecture/decisions/2026-07-18-contract-compatibility-ratchets.md`
- Create: `docs/roadmap/phases/phase-184-contract-compatibility-ratchets.md`
- Modify: `README.md`
- Modify: `docs/api-support-policy.md`
- Modify: `docs/ROADMAP.md`
- Modify: `docs/roadmap/full-roadmap-blueprint.md`
- Modify: `docs/architecture/subsystem-stability.md`
- Modify: `docs/tool-map.md`
- Modify: `.docsync/trace.yml`
- Modify: `.agent-maintainer/change-plans/contract-compatibility-ratchets.md`
- Modify: `tests/packaging/test_public_docs.py`

**Interfaces:**

- Documents: beta evolution versus compatibility freeze, policy/baseline ownership, exact-decision workflow, revision/package/migration obligations, command exit statuses, dogfood scope, and Phase 185 handoff.
- Records: the contracts domain as inward-facing beta architecture and the catalog/root CLI as adapters.

- [ ] **Step 1: Write failing public-document contract tests**

```python
def test_public_docs_explain_contract_ratchet_workflow() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    support = Path("docs/api-support-policy.md").read_text(encoding="utf-8")

    assert "agent-maintainer contract diff" in readme
    assert "agent-maintainer contract check" in readme
    assert "contract snapshot --write" in readme
    assert ".agent-maintainer/contracts.toml" in readme
    assert "does not create a pre-1.0 compatibility guarantee" in support
```

- [ ] **Step 2: Run docs tests and verify RED**

```bash
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH pytest tests/packaging/test_public_docs.py -q
```

Expected: new Phase 184 documentation assertions fail.

- [ ] **Step 3: Write the ADR, roadmap record, public workflow, and DocSync trace**

The ADR must state the boundary change, why the inward domain is necessary, why it is not architecture drift, why source hashing/runtime reflection/separate ratchets were rejected, and what remains forbidden. Mark Phase 184 implemented only after all completion gates pass. Keep Phase 185 failure intelligence next and the external cohort as a parallel measurement track.

Run generated documentation maintenance only through repository commands:

```bash
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH python -m docsync index
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH python -m docsync check --base-ref 453a00f
```

Expected: DocSync index/check pass with the new exact evidence links.

- [ ] **Step 4: Run focused, mutation, architecture, and public gates**

```bash
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH pytest tests/contracts tests/catalogs/test_contract_catalog.py tests/packaging/test_script_helpers.py tests/packaging/test_public_docs.py tests/verify/test_verification_groups.py tests/config/test_config_reference.py tests/wait/test_codex_app_server.py tests/wait/test_agent_waits_core.py -q
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH tach check
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH python -m archguard decision-check --base-ref 453a00f
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH python -m agent_maintainer contract check --base-ref 453a00f --json
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH python -m agent_maintainer change-plan check
```

Expected: all focused, architecture, self-hosted contract, and cohesive-plan checks pass. Run the repository's existing mutation target command for `contracts.classifiers`; every surviving classifier mutant must be killed or explained by an exact equivalent-mutant record in the active change plan.

- [ ] **Step 5: Mark the cohesive change complete and commit documentation**

Change only the active plan front matter from `status = "active"` to `status = "complete"` after Step 4 passes.

```bash
git add -- .agent-maintainer/change-plans/contract-compatibility-ratchets.md .docsync/trace.yml README.md docs/ROADMAP.md docs/api-support-policy.md docs/architecture/decisions/2026-07-18-contract-compatibility-ratchets.md docs/architecture/subsystem-stability.md docs/roadmap/full-roadmap-blueprint.md docs/roadmap/phases/phase-184-contract-compatibility-ratchets.md docs/tool-map.md tests/packaging/test_public_docs.py
git commit -m "docs: document contract compatibility ratchets"
```

Expected: docs and affected-test hooks pass.

- [ ] **Step 6: Run completion verification and publish the implementation PR**

```bash
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH just v
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH just vc
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH just vs
git status --short --branch
git diff --check origin/main...HEAD
```

Expected: fresh full, CI-equivalent, and security profiles pass; status is clean; the branch diff has no whitespace errors. Then use `superpowers:requesting-code-review`, fix any correctness/security findings, push the branch, open a ready PR, wait through protected checks with `just wp <pr-number>`, and merge only after every required check succeeds.
