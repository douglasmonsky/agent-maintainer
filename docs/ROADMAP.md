# Product Roadmap

This roadmap tracks the next hardening and productization pass for the guardrail
kit. Keep the checkboxes current as work lands so future agents can resume from
repo state instead of reconstructing the plan from chat history.

## Current Baseline

- [x] Private GitHub repository exists.
- [x] Private origin and remote CI verification have been proven for this repo.
- [x] Canonical CLI uses `python3 -m scripts.guardrail`.
- [x] `fresh-strict` mode is active for this repository.
- [x] Tach is the active architecture backend for this repository.
- [x] `root_module = "forbid"` is configured in `tach.toml`.
- [x] Tests, coverage, diff-cover, Ruff, Pyright, Radon, Xenon, Pylint, deptry,
  vulture, Bandit, pip-audit, wemake, Interrogate, pre-commit, CI, and Codex
  hooks are already part of the guardrail surface.
- [x] Docker is intentionally not part of this repository's own workflow.

## Standing Implementation Rules

- [x] When adding a relevant guardrail capability, enable it for this repository
  in the same pass so the kit remains its own first consumer.
- [x] Leave a new capability disabled for this repository only when it is
  objectively not applicable, too slow for normal profiles, requires
  unavailable external binaries, requires credentials or external services, or
  has privacy/network implications that have not been explicitly accepted.
- [x] If a capability is intentionally not enabled here, document the reason in
  the roadmap, tool map, or relevant feature docs.
- [x] Prefer advisory/warn-only rollout for subjective design smells, then
  graduate to blocking only when the signal is precise enough for
  `fresh-strict`.

## Phase 0: Generated Agent Guidance

- [x] Add a generator that renders agent-facing guidance from
  `[tool.ai_guardrails]`.
- [x] Include active mode, source roots, test roots, architecture backend,
  thresholds, required commands, enabled optional gates, and escape hatches.
- [x] Frame generated guidance as positive operating instructions, not just a
  list of ways checks can fail.
- [x] Keep human-owned `AGENTS.md` content authoritative and avoid overwriting it
  wholesale.
- [x] Use a protected generated block or a committed sidecar file such as
  `AGENTS.guardrails.md`.
- [x] If using a sidecar file, add a stable human-owned pointer from `AGENTS.md`
  so agents know to read it.
- [x] Make generated output deterministic and free of secrets, machine-local
  paths, volatile git state, or timestamps.
- [x] Add a `doctor` freshness check so generated guidance cannot silently drift
  from configuration.
- [x] Add tests proving guidance updates when config changes and remains stable
  when config does not change.
- [x] Use this repository as the first consumer so subsequent roadmap work gets
  immediate benefit from the generated guidance.
- [x] Consider optional subdirectory `AGENTS.md` generation only after the root
  guidance flow is proven.

## Phase 1: Test-Driven Enforcement Fidelity

- [x] Add a failing regression test proving aggregate verification does not hide
  change-budget warnings behind a plain `PASS`.
- [x] Add a failing regression test proving `pyright_type_checking_mode` changes
  the actual Pyright invocation.
- [x] Add a failing regression test proving unsafe `pip-audit` config is
  diagnosed.
- [x] Add a failing regression test proving `justfile verify-full-output` no
  longer hard-codes stale `src` assumptions.
- [x] Make change-budget warnings visible in all profiles.
- [x] Make source-without-test-change warnings fail in Codex/local precommit for
  `fresh-strict` unless an explicit escape hatch is set.
- [x] Keep CI primarily governed by `diff-cover`; make the source/test-change
  heuristic fatal only when explicitly configured for `fresh-strict`.
- [x] Add an explicit escape hatch for source-only changes that are already
  covered by existing tests.
- [x] Generate a temporary Pyright config from `GuardrailConfig` and run Pyright
  with `--project`.
- [x] Teach `doctor` to compare configured Pyright mode with any active root
  Pyright config.
- [x] Warn when `enable_pip_audit = true` has empty `pip_audit_args` in
  `custom` or `legacy-ratchet`.
- [x] Fail when `enable_pip_audit = true` has empty `pip_audit_args` in
  `fresh-strict`.
- [x] Replace or repair `justfile verify-full-output` so it follows configured
  roots instead of `src`.

## Phase 2: Make Legacy-Ratchet Real

- [x] Add file-length baselining for `legacy-ratchet`.
- [x] Make legacy file-length checks fail only for new or worsened violations.
- [x] Document the baseline file format and refresh workflow.
- [x] Add tests for clean legacy baselines, worsened legacy violations, and new
  oversized files.
- [x] Consider complexity baselining after file-length baselining is stable;
  defer it until file-length ratcheting has real adoption feedback.
- [x] Update `docs/legacy-ratchet.md` to distinguish fresh blocking from legacy
  ratcheting.

## Phase 3: Agent Diagnostic Artifacts

- [x] Add a diagnostics config section for verifier artifacts.
- [x] Add `.verify-logs/manifest.json`.
- [x] Record command, exit code, status, profile, timestamps, git SHA/state,
  relevant thresholds, and artifact paths per check.
- [x] Add `.verify-logs/LAST_FAILURE.md` with failed checks, concise diagnostics,
  full-log paths, and the exact rerun command.
- [x] Keep terminal output compact while making the artifact trail complete.
- [x] Store structured output where supported, starting with Pyright JSON.
- [x] Add `.verify-logs/hooks.jsonl` so Codex hook execution has a local audit
  trail that `doctor` can inspect.
- [x] Add Ruff JSON or SARIF output when useful for summaries.
- [x] Add pytest JUnit XML output.
- [x] Preserve coverage XML and consider coverage JSON.
- [x] Add Bandit JSON output.
- [x] Disable Python bytecode writes by default in guardrail and hook subprocesses
  to reduce generated-cache token leaks.
- [x] Prefer structured artifacts over raw text when producing compact failure
  summaries.
- [x] Add tests for manifest content, failure-note content, stale artifacts, and
  successful runs.
- [x] Teach `doctor` to detect stale logs and stale structured artifacts.
- [x] Keep runtime application logging enforcement advisory and disabled by
  default.

## Phase 4: Add Tool Capability Modeling

- [x] Add a tool capability model with at least `python_package`,
  `external_binary`, `github_action_only`, and `manual_optional`.
- [x] Use the capability model in `doctor` so missing external binaries are
  reported accurately.
- [x] Use the capability model in bootstrap docs and output so pip-installed and
  non-pip tools are not conflated.
- [x] Add tests for supported, missing, disabled, and not-applicable tool states.

## Phase 5: Harden GitHub Actions

- [x] Add explicit workflow permissions, starting with
  `permissions: contents: read`.
- [x] Add `actionlint` support when `.github/workflows` exists.
- [x] Add `zizmor` support when `.github/workflows` exists.
- [x] Enable `actionlint` for this repository.
- [x] Enable `zizmor` for this repository.
- [x] Decide the action pinning policy for this kit.
- [x] If using SHA pinning, pin third-party actions to full-length commit SHAs.
  Not applicable while the documented policy remains trusted tag pinning with
  Dependabot review.
- [x] If using tag pinning, document the tradeoff and add Dependabot coverage for
  GitHub Actions.
- [x] Add tests for workflow-tool applicability and optional-skip behavior.

## Phase 6: Add Backend-Neutral Secret Scanning

- [x] Add a `secret_scanner` config concept.
- [x] Treat secret scanning as opt-in or mode/profile-driven, not mandatory in
  every profile.
- [x] Use `gitleaks` as the initial default backend when secret scanning is
  enabled.
- [x] Treat `gitleaks` as an `external_binary`, not a Python dependency.
- [x] Keep scanner wiring backend-neutral enough to support `betterleaks`.
- [x] Keep normal profiles to current-tree, staged, or comparison-range scans.
- [x] Add a manual/security profile for full-history scans.
- [x] Teach `doctor` to report disabled, missing-backend, active, unsupported
  backend, and invalid-history-scan states.
- [x] Document why Gitleaks is the first backend but not a permanent architectural
  commitment.

## Phase 7: Improve Doctor Product UX

- [x] Report the active architecture backend.
- [x] Report active coverage, diff-cover, Interrogate, complexity, and
  file-length thresholds.
- [x] Report unsafe config states separately from missing dependencies.
- [x] Detect and report stale verification logs from disabled or removed checks.
- [x] Use consistent state vocabulary: `active`, `disabled`, `not applicable`,
  `missing`, and `unsafe config`.
- [x] Include relevant remediation hints without making text output noisy.
- [x] Keep JSON output stable and covered by tests.

## Phase 8: Add Structural Cohesion Signals

- [x] Add a folder-level Python file-count smell check.
- [x] Treat folder file count as advisory by default, not proof of bad design.
- [x] Default to warning around 20 Python files in one folder.
- [x] Block only at a high threshold, around 40 Python files, and only in
  `fresh-strict`.
- [x] Never block tests, migrations, generated folders, virtualenvs, caches, or
  explicitly configured plugin/command registries.
- [x] Add config such as `[tool.ai_guardrails.structure] folder_file_warn`,
  `folder_file_block`, and `ignore_folder_file_count_paths`, or an equivalent
  shape that fits the final config model.
- [x] Add configurable regex hint patterns for naming clusters, separate from
  the warn/block thresholds.
- [x] Ship conservative built-in regex hints for common hierarchy smells:
  repeated prefixes like `^guardrail_`, `^check_`, and domain prefixes such as
  `^user_` or `^course_`; repeated role suffixes like `_model$`, `_service$`,
  `_repository$`, `_client$`, `_adapter$`, `_parser$`, `_loader$`, `_schema$`,
  `_executor$`, and `_reporting$`; and layer words such as `cli`, `args`,
  `config`, `models`, `checks`, `doctor`, `executor`, and `reporting`.
- [x] Use regex matches to enrich advisory messages with concrete clusters and
  likely split candidates, not as standalone failure conditions.
- [x] Detect prefix clusters that suggest fake flat hierarchy, such as many
  `guardrail_*` or `check_*` modules in one folder.
- [x] Detect layer mixing signals, such as CLI entrypoints, config parsing,
  execution, reporting, models, and individual checks living in one flat folder.
- [x] Consider sibling-import density as a future stronger cohesion signal, but
  keep the first implementation simple and explainable.
- [x] Emit messages that recommend considering a split by responsibility instead
  of requiring arbitrary subfolders.
- [x] Surface structural cohesion signals in generated agent guidance so agents
  proactively notice refactor pressure.
- [x] Teach `doctor` to report active structure thresholds and ignored paths.
- [x] Add tests for normal folders, warning folders, fresh-strict block folders,
  ignored folders, regex hint clusters, prefix clusters, and explicit registry
  exemptions.
- [x] Document when to split into subpackages and use this repository's
  `guardrail_lib/config` extraction as the motivating example.

## Phase 9: Add Docs And Config Hygiene

- [x] Add `markdownlint-cli2` support for Markdown structure.
- [x] Enable Markdown linting for this repository once the docs pass cleanly.
- [x] Add `yamllint` support when YAML files exist.
- [x] Enable YAML linting for this repository if the workflow and pre-commit
  config pass cleanly.
- [x] Add `taplo` support when TOML files exist.
- [x] Enable TOML linting for this repository after formatting existing TOML.
- [x] Add `check-jsonschema` support only where schemas or stable config
  contracts exist.
- [x] Continue skipping `typos` and `codespell` as low-leverage AI-maintainability
  gates.
- [x] Update `docs/tool-map.md` as each docs/config hygiene gate becomes
  supported.

## Phase 10: Raise Test Depth Toward 90 Percent

- [x] Raise the coverage target only after meaningful tests exist.
- [x] Add branch/error-path tests for `scripts/check_change_budget.py`.
- [x] Add branch/error-path tests for `scripts/check_suppression_budget.py`.
- [x] Add branch/error-path tests for `scripts/check_file_lengths.py`.
- [x] Add branch/error-path tests for `scripts/check_tach_config.py`.
- [x] Add branch/error-path tests for `scripts/guardrail_core/executor.py`.
- [x] Add branch/error-path tests for `.codex/hooks/post_edit_fast_gate.py`.
- [x] Add branch/error-path tests for `.codex/hooks/stop_full_verify.py`.
- [x] Raise `coverage_fail_under` toward 90 only after the suite proves those
  paths.
- [x] Avoid chasing 100 percent coverage unless it reflects real risk reduction.

## Phase 11: Add Slow And Advanced Profiles

- [x] Add a slow/manual profile concept separate from normal `full`.
- [x] Add `mutmut` as a slow/manual mutation-testing option.
- [x] Document mutmut's POSIX fork requirement and Windows-through-WSL support.
- [x] Add optional Semgrep support with local or pinned rules first.
- [x] Add OSV Scanner only for mixed-ecosystem repositories.
- [x] Add Trivy only for repositories with Docker, container, Kubernetes,
  Terraform, or other IaC assets.
- [x] Add license checks as an optional policy gate.
- [x] Add SBOM generation as a CI artifact, not a blocking default.
- [x] Prefer `cyclonedx-python` for Python-only SBOMs.
- [x] Prefer Syft/Grype for broader deployable or container projects.

## Explicit Non-Goals For Now

- [x] Do not add Docker to this repository's own workflow.
- [x] Do not make every supported scanner a default blocking gate.
- [x] Do not make source-only changes a blanket CI failure without an escape
  hatch.
- [x] Do not switch back from Tach to Import Linter for this repository.
- [x] Do not adopt Betterleaks as the first default backend until its install and
  config story is clear for this kit.
- [x] Do not raise docstring coverage to 100 percent as a default policy.
- [x] Do not force arbitrary subfolders from folder file count alone; use count
  as a refactor signal, not as a standalone design proof.
