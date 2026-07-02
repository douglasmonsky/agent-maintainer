# Polyglot Ecosystem Provider Roadmap

Agent Maintainer should remain a coherent agent-maintenance framework rather than becoming a bag of language-specific scripts. The core should own orchestration, diagnostics, profiles, reports, context safety, repair-loop ergonomics, and policy primitives. Ecosystem providers should own language/toolchain-specific knowledge.

## Definition

In this project, polyglot means supporting repositories that contain one or more programming-language ecosystems, such as Python, TypeScript/JavaScript, Go, Rust, Java, C#, Ruby, PHP, or mixed monorepos.

Polyglot does not mean merely running arbitrary commands. It means applying Agent Maintainer's reviewability and repair-loop policies across ecosystems while preserving compact diagnostics, stable profiles, bounded artifacts, and agent-safe repair context.

## Product Boundary

Core framework responsibilities:

- CLI orchestration.
- Profile model.
- Check execution.
- Subprocess timeout and output bounding.
- Run-scoped diagnostics.
- `.verify-logs` artifact layout.
- Manifest schema.
- `LAST_FAILURE.md`.
- PR summary generation.
- Static HTML report generation.
- Context safety and context pack rendering.
- Repair-plan rendering.
- Hook manager and agent-client adapters.
- Architecture decision-note machinery where language-neutral.
- Global docs/config/security checks where ecosystem-independent.
- Stable result statuses and output contract.

Ecosystem provider responsibilities:

- File-role classification.
- Source/test/generated/config/docs/dependency file patterns.
- Ecosystem-specific ignore rules.
- Toolchain detection.
- Check generation for language-specific tools.
- Formatter, linter, type, test, coverage, dependency, and security command definitions.
- Coverage artifact expectations and parsing.
- Suppression classification.
- Structured artifact parsing into exact repair facts.
- Ecosystem-specific scaffold snippets.
- Ecosystem-specific doctor capability rows.
- Ecosystem-specific guidance snippets.
- Optional test-intelligence integration.
- Optional ratchet dimensions.

Immediate design principle: core owns the loop; providers own ecosystem excellence. Phase 1 must make Python safer to refactor by characterizing current behavior. Phase 2 may make Python the first built-in ecosystem provider, but it must not change current observable behavior.

Do not constrain Python excellence to fit a lowest-common-denominator provider model. Python is the core/reference provider and must preserve its current full design space. The provider architecture should make Python-specific behavior explicit, testable, and easier to evolve. It should not remove Python-specific capabilities, rename stable Python checks, weaken Python policy gates, or force Python tools into abstractions designed around other ecosystems.

The provider seam should be capability-oriented. Providers may implement different capabilities at different maturity levels. Python can remain richer than experimental providers. A future TypeScript provider does not need mutation testing on day one because Python has Mutmut, and a Go provider does not need to mimic Pyright. The core framework should orchestrate checks and diagnostics, while ecosystem providers remain free to implement rich ecosystem-specific behavior.

If a proposed abstraction makes an existing Python feature harder to express, stop and redesign the abstraction. Do not simplify Python behavior to satisfy the abstraction.

## Provider Maturity

- Internal: built into the package, not documented as externally stable.
- Experimental: available but not guaranteed complete; suitable for early community contribution.
- Supported: tested with scaffold fixtures, doctor support, structured parsers, docs, and CI fixtures.
- Core: maintained as part of the primary package compatibility contract. Python begins here.

## API Stability Policy

- Do not publish an external plugin API until at least two non-Python built-in providers have been implemented and the abstraction has survived real use.
- Internal provider interfaces may change between beta releases.
- Community language support should first land as built-in experimental providers through normal PR review.
- External package discovery and loading are deferred until the internal architecture has stabilized.

## Capability Model

Provider capabilities should be descriptive, not mandatory. Python starts as the reference provider with a rich capability set:

```python
PythonProvider.capabilities = {
    "format": "ruff",
    "lint": "ruff/pylint/wemake",
    "typecheck": "pyright",
    "test": "pytest",
    "coverage": "coverage.py",
    "diff_coverage": "diff-cover",
    "mutation": "mutmut",
    "security": "bandit/pip-audit",
    "dead_code": "vulture",
    "dependency_hygiene": "deptry",
}
```

A future TypeScript provider could start smaller:

```python
TypeScriptProvider.capabilities = {
    "format": "prettier_or_biome",
    "lint": "eslint_or_biome",
    "typecheck": "tsc",
    "test": "vitest_or_jest",
    "coverage": "lcov",
    "security": "osv_or_package_manager_audit",
}
```

The provider API should not require symmetry between providers. Missing capabilities should produce clear not-applicable or disabled states, not fake checks.

## Proposed Provider Shape

The following sketch is proposed and non-binding. Phase 1 should start with characterization tests, not abstractions. Phase 2 should introduce the smallest internal seam that preserves current Python behavior.

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class EcosystemContext:
    repo_root: Path
    config: MaintainerConfig
    profile: str
    base_ref: str
    compare_branch: str
    staged: bool
    diagnostic_artifacts_dir: Path


@dataclass(frozen=True)
class FileClassification:
    path: str
    ecosystem: str
    role: FileRole
    generated: bool = False
    reason: str = ""


class EcosystemProvider(Protocol):
    name: str
    maturity: ProviderMaturity

    def checks(self, context: EcosystemContext) -> list[Check]:
        ...

    def classify_path(self, path: str) -> FileClassification | None:
        ...

    def suppression_findings(
        self,
        path: str,
        added_line: str,
    ) -> list[SuppressionFinding]:
        ...

    def doctor_findings(self, context: DoctorContext) -> list[DoctorFinding]:
        ...

    def scaffold_files(self, context: ScaffoldContext) -> list[StarterFile]:
        ...

    def guidance_sections(self, context: GuidanceContext) -> list[GuidanceSection]:
        ...

    def structured_artifact_parsers(self) -> list[ArtifactParser]:
        ...
```

This sketch should prevent over-engineering, not require it. If a future phase can preserve behavior with a smaller protocol, it should.

## Python Compatibility Contract

Future implementation phases must preserve:

- Existing CLI commands and subcommands.
- Existing profile names.
- Existing default profile behavior.
- Existing check names unless explicitly documented and migrated.
- Existing command lines for current Python checks unless a deliberate bug fix is approved.
- Existing artifact filenames and locations where users or docs may rely on them.
- Existing optional skip behavior.
- Existing `[tool.agent_maintainer]` config semantics.
- Existing environment variable semantics.
- Existing CLI override semantics.
- Existing `pyproject.toml` support.
- Existing init tracks and presets unless changed by a separate migration phase.
- Existing `AGENTS.agent-maintainer.md` behavior.
- Existing run-scoped diagnostics layout.
- Existing `.verify-logs/manifest.json` basic schema.
- Existing `LAST_FAILURE.md` and PR summary intent.
- Existing CI workflow behavior.
- Existing `agent-maintainer` and `archguard` console scripts.
- Existing `python -m agent_maintainer` module entrypoint.

Make this contract testable. Phase 1 must begin by adding characterization tests around current check generation before moving code.

## Testing Strategy

Before implementation:

- Add characterization tests for current `make_checks()` output.
- Assert expected check names by profile.
- Assert profile membership for key checks.
- Assert key command lines.
- Assert artifact paths for Pyright, Ruff, Bandit, pytest coverage, SBOM, licenses, secret scans, and other structured checks.
- Assert optional skip behavior for disabled optional integrations.
- Assert Python source/test classification current behavior before generic file classification is introduced.
- Assert file-length behavior against Python files.
- Assert suppression-budget behavior against current Python suppression patterns.
- Assert change-budget behavior for Python source/test roots.
- Add scaffold smoke tests where feasible.
- Avoid snapshot tests that are too brittle unless the snapshot is intentionally part of the compatibility contract.

During implementation:

- After each phase, run the narrowest relevant tests.
- For code changes touching verifier behavior, run `python3 -m agent_maintainer verify --profile precommit` if dependencies are available.
- If full verification is too expensive, run targeted pytest modules plus `python3 -m agent_maintainer verify --profile fast`.
- For documentation-only Phase 0, run the repo's markdown/docs hygiene checks if available and practical; otherwise run the smallest available docs check and explain why broader checks were skipped.

## Implementation Phases

### Phase 0: Roadmap And Architecture Plan

Scope:

- Create this roadmap.
- Create the numbered repository phase entry for this planning work.
- Link from roadmap indexes.
- Make no runtime behavior changes.

Acceptance criteria:

- Roadmap exists.
- Numbered repository phase entry exists.
- Existing roadmap index links to the roadmap.
- Invariants, phases, non-goals, testing plan, contribution model, and risk register are documented.
- Documentation checks are attempted.
- No source code refactor is included.

### Phase 1: Characterization Safety Net

Scope:

- Add tests that lock down current Python check catalog behavior.
- Add tests for key current policy behavior.
- Add no provider abstraction unless absolutely needed for test helpers.

Acceptance criteria:

- Tests fail if check names, profile memberships, key commands, or artifact paths change unexpectedly.
- Tests are explicit enough to protect Python behavior but not so brittle that harmless formatting changes fail.
- Existing verifier behavior is unchanged.
- No language support is added.

### Phase 2: Minimal Internal Provider Seam, Python Only

Scope:

- Introduce the smallest internal provider abstraction required to let Python generate its current checks.
- Move Python-specific check generation behind a Python provider.
- Keep the central catalog responsible for orchestration and ordering.
- Do not publish a provider API.

Acceptance criteria:

- `make_checks()` returns behavior-equivalent results.
- Characterization tests pass.
- CLI behavior is unchanged.
- Python-specific capabilities remain at least as expressive as before the refactor.
- Docs mention this only if architecture status needs an update.

### Phase 3: Separate Global Checks From Ecosystem Checks

Scope:

- Distinguish global checks from Python provider checks.
- Treat language-neutral docs/config, workflow, broad security, architecture-decision, and diagnostics-adjacent checks as global where appropriate.
- Avoid changing check order unless tests and docs justify it.

Acceptance criteria:

- Same selected checks for current repo/profile combinations.
- Global-vs-ecosystem ownership is documented.
- Optional skip behavior is preserved.

### Phase 4: Generic File Classification, Python Only

Scope:

- Introduce generic file-role classification.
- Implement a Python classifier that preserves current `.py` source/test behavior.
- Prepare change-budget, file-length, structure-cohesion, suppression-budget, and test relevance to consume classification later.

Acceptance criteria:

- Existing Python behavior is unchanged.
- Tests cover source, test, generated, and ignored classification.
- No new language support is added.

### Phase 5: Generalize Policy Checks Through Provider/Classifier Adapters

Scope:

- Refactor change-budget, file-length, structure-cohesion, suppression-budget, and source-without-test-change logic so they no longer hard-code Python extensions or patterns.
- Keep the Python provider supplying current rules.

Acceptance criteria:

- Existing Python policy tests pass.
- Existing CLI options still work.
- New generic internal types are documented.
- No TypeScript provider is added.

### Phase 6: Neutral Config Path Exploration

Scope:

- Add support for a language-neutral config file such as `.agent-maintainer/config.toml` or `agent-maintainer.toml`.
- Keep `pyproject.toml` support.
- Define precedence explicitly.
- Do not force existing Python users to migrate.

Acceptance criteria:

- Current `[tool.agent_maintainer]` behavior remains unchanged.
- New neutral config behavior is tested.
- Precedence is documented.
- Error messages are clear when multiple config sources conflict.

### Phase 7: Experimental TypeScript/JavaScript Provider

Scope:

- Add the first non-Python provider as experimental.
- Start with configured commands rather than aggressive autodetection.
- Implement file classification and a small check set.
- Avoid package-manager assumptions where possible.

Acceptance criteria:

- Python behavior is unchanged.
- TypeScript provider can be enabled explicitly.
- Provider has focused docs and tests.
- Doctor hints and scaffold fixtures can land in a follow-up phase after the
  internal seam proves stable.
- No external plugin API is added.

### Phase 8: Structured Artifact Parser Expansion

Scope:

- Add exact-fact parsing for new provider outputs.
- Improve parser architecture for existing Python outputs only where needed.

Acceptance criteria:

- Repair facts are compact, structured, and safe for context packs.
- Existing Pyright, Ruff, and Bandit summaries continue to work.
- New parsers have tests with sample outputs.

### Phase 9: Provider Contribution Guide

Scope:

- Document how community contributors can add built-in experimental providers.
- Include required files, tests, docs, scaffold expectations, and maturity checklist.
- Publish contributor-facing guide at
  [`docs/provider-contribution-guide.md`](../provider-contribution-guide.md).

Acceptance criteria:

- Contributor guide exists.
- Provider checklist exists.
- Experimental provider policy is explicit.
- No promise of external plugin stability is made.

### Phase 10: Second Non-Python Provider

Scope:

- Add Go or Rust as a second experimental provider to validate the abstraction outside Node.
- First implementation path is the experimental Go provider documented at
  [`docs/go-provider.md`](../go-provider.md).

Acceptance criteria:

- Provider interface survives a second ecosystem without major conceptual contortions.
- Any interface changes are documented as internal.
- Community contribution model is refined.

### Phase 11: Public Provider API Decision

Scope:

- Decide whether external provider packages are ready.
- If yes, design plugin discovery/loading separately.
- If no, document why built-in experimental providers remain the contribution path.

Acceptance criteria:

- Explicit decision record exists.
- API stability policy is updated.
- Migration path is documented if external plugins are introduced.

## Community Provider Contribution Checklist

See [`docs/provider-contribution-guide.md`](../provider-contribution-guide.md)
for the contributor-facing version of this checklist.

A new provider should include:

- Provider module under the agreed ecosystem path.
- File classifier.
- Source/test/generated/config/docs rules.
- Suppression classifier.
- Minimal check set by profile.
- Doctor capability detection.
- Optional scaffold snippets.
- Structured parser fixtures where relevant.
- Documentation page.
- Example fixture repo or fixture tree.
- Characterization tests.
- Clear maturity label.
- Security/artifact-sensitivity review.
- Coverage story, even if advisory-only.
- Statement of unsupported package managers/test runners.
- Guidance for agents using that ecosystem.

## Proposed Future Module Layout

This layout is proposed, not binding:

```text
src/agent_maintainer/ecosystems/__init__.py
src/agent_maintainer/ecosystems/models.py
src/agent_maintainer/ecosystems/registry.py
src/agent_maintainer/ecosystems/python/__init__.py
src/agent_maintainer/ecosystems/python/checks.py
src/agent_maintainer/ecosystems/python/classification.py
src/agent_maintainer/ecosystems/python/suppressions.py
src/agent_maintainer/ecosystems/python/artifacts.py
src/agent_maintainer/ecosystems/python/scaffold.py
src/agent_maintainer/ecosystems/python/doctor.py
src/agent_maintainer/ecosystems/typescript/... later, not now
```

Implementation should choose the smallest layout that keeps modules understandable.

## Required Non-Goals

- Do not add non-Python language support in Phase 0.
- Do not create external plugin loading in early phases.
- Do not break existing Python config.
- Do not rename current checks as part of the provider extraction.
- Do not replace the verifier engine.
- Do not turn Agent Maintainer into a generic task runner.
- Do not make every provider responsible for diagnostics or reporting.
- Do not move hook/client logic into providers unless a concrete ecosystem-specific hook need emerges.
- Do not require non-Python users to use `pyproject.toml` long-term.
- Do not require Python users to stop using `pyproject.toml`.
- Do not make all providers equal or force them to expose identical capabilities.
- Do not move rich Python semantics into weak generic abstractions.

Stop and reassess if a future phase:

- Requires changing public CLI behavior to make the provider seam work.
- Requires weakening Python checks before characterization tests exist.
- Introduces dynamic plugin loading before two built-in non-Python providers exist.
- Cannot preserve check names, profile memberships, and artifact paths without a documented migration.
- Makes provider code responsible for run-scoped diagnostics, context packs, hooks, or reports.
- Makes an existing Python feature harder to express or extend.

## Risk Register

1. Over-abstraction before a second provider exists.
   Mitigation: start with Python-only internal provider seam and minimal protocol.
2. Behavior drift in Python checks.
   Mitigation: characterization tests before refactor; behavior-preserving phases.
3. Config surface explosion.
   Mitigation: schema metadata plan; avoid adding ecosystem config until provider seam exists.
4. Public plugin API too early.
   Mitigation: built-in experimental providers first; external loading deferred.
5. Check catalog becoming fragmented.
   Mitigation: clear ownership split between core/global checks and ecosystem checks.
6. Optional-skip semantics becoming confusing across languages.
   Mitigation: preserve current behavior first; later improve status taxonomy deliberately.
7. Coverage normalization across languages becoming hard.
   Mitigation: coverage adapters; start advisory; support one runner at a time.
8. Community providers lowering quality.
   Mitigation: maturity levels, provider checklist, fixture tests, docs requirements, CI expectations.
9. Scaffolded repos breaking.
   Mitigation: scaffold smoke tests for each track/provider combination.
10. Docs/guidance drift.
    Mitigation: schema/provider metadata should eventually generate or validate docs fragments.
11. Agent-generated broad refactors.
    Mitigation: phase gates, small PRs, strict non-goals, and verifier runs after each phase.
12. Architecture boundary confusion.
    Mitigation: decision notes for provider architecture and module ownership.
13. Lowest-common-denominator provider design.
    Mitigation: capability-oriented providers; Python remains the reference provider for ecosystem excellence.

## Codex Task Decomposition Guidance

- Complete one phase per PR unless the user explicitly changes scope.
- Perform a deep assessment after each phase before starting the next phase.
- Do not refactor before Phase 1 characterization tests exist.
- For Phase 1, add tests only.
- For Phase 2, keep `make_checks()` as the integration point.
- For Phase 3, preserve check order unless characterization tests prove a safe migration path.
- For Phase 4 and Phase 5, prefer adapters over large rewrites.
- For Phase 7 and later, require fixture repos and doctor hints before calling a provider supported.
- If a phase feels awkward, stop and revise this roadmap before adding another language.
