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

- [ ] When adding a relevant guardrail capability, enable it for this repository
  in the same pass so the kit remains its own first consumer.
- [ ] Leave a new capability disabled for this repository only when it is
  objectively not applicable, too slow for normal profiles, requires
  unavailable external binaries, requires credentials or external services, or
  has privacy/network implications that have not been explicitly accepted.
- [ ] If a capability is intentionally not enabled here, document the reason in
  the roadmap, tool map, or relevant feature docs.
- [ ] Prefer advisory/warn-only rollout for subjective design smells, then
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
- [ ] Prefer structured artifacts over raw text when producing compact failure
  summaries.
- [x] Add tests for manifest content, failure-note content, stale artifacts, and
  successful runs.
- [x] Teach `doctor` to detect stale logs and stale structured artifacts.
- [ ] Keep runtime application logging enforcement advisory and disabled by
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
- [ ] If using SHA pinning, pin third-party actions to full-length commit SHAs.
- [x] If using tag pinning, document the tradeoff and add Dependabot coverage for
  GitHub Actions.
- [x] Add tests for workflow-tool applicability and optional-skip behavior.

## Phase 6: Add Backend-Neutral Secret Scanning

- [ ] Add a `secret_scanner` config concept.
- [ ] Treat secret scanning as opt-in or mode/profile-driven, not mandatory in
  every profile.
- [ ] Use `gitleaks` as the initial default backend when secret scanning is
  enabled.
- [ ] Treat `gitleaks` as an `external_binary`, not a Python dependency.
- [ ] Keep scanner wiring backend-neutral enough to support `betterleaks`.
- [ ] Keep normal profiles to current-tree, staged, or comparison-range scans.
- [ ] Add a manual/security profile for full-history scans.
- [ ] Teach `doctor` to report disabled, missing-backend, active, unsupported
  backend, and invalid-history-scan states.
- [ ] Document why Gitleaks is the first backend but not a permanent architectural
  commitment.

## Phase 7: Improve Doctor Product UX

- [ ] Report the active architecture backend.
- [ ] Report active coverage, diff-cover, Interrogate, complexity, and
  file-length thresholds.
- [ ] Report unsafe config states separately from missing dependencies.
- [ ] Detect and report stale verification logs from disabled or removed checks.
- [ ] Use consistent state vocabulary: `active`, `disabled`, `not applicable`,
  `missing`, and `unsafe config`.
- [ ] Include relevant remediation hints without making text output noisy.
- [ ] Keep JSON output stable and covered by tests.

## Phase 8: Add Structural Cohesion Signals

- [ ] Add a folder-level Python file-count smell check.
- [ ] Treat folder file count as advisory by default, not proof of bad design.
- [ ] Default to warning around 20 Python files in one folder.
- [ ] Block only at a high threshold, around 40 Python files, and only in
  `fresh-strict`.
- [ ] Never block tests, migrations, generated folders, virtualenvs, caches, or
  explicitly configured plugin/command registries.
- [ ] Add config such as `[tool.ai_guardrails.structure] folder_file_warn`,
  `folder_file_block`, and `ignore_folder_file_count_paths`, or an equivalent
  shape that fits the final config model.
- [ ] Add configurable regex hint patterns for naming clusters, separate from
  the warn/block thresholds.
- [ ] Ship conservative built-in regex hints for common hierarchy smells:
  repeated prefixes like `^guardrail_`, `^check_`, and domain prefixes such as
  `^user_` or `^course_`; repeated role suffixes like `_model$`, `_service$`,
  `_repository$`, `_client$`, `_adapter$`, `_parser$`, `_loader$`, `_schema$`,
  `_executor$`, and `_reporting$`; and layer words such as `cli`, `args`,
  `config`, `models`, `checks`, `doctor`, `executor`, and `reporting`.
- [ ] Use regex matches to enrich advisory messages with concrete clusters and
  likely split candidates, not as standalone failure conditions.
- [ ] Detect prefix clusters that suggest fake flat hierarchy, such as many
  `guardrail_*` or `check_*` modules in one folder.
- [ ] Detect layer mixing signals, such as CLI entrypoints, config parsing,
  execution, reporting, models, and individual checks living in one flat folder.
- [ ] Consider sibling-import density as a future stronger cohesion signal, but
  keep the first implementation simple and explainable.
- [ ] Emit messages that recommend considering a split by responsibility instead
  of requiring arbitrary subfolders.
- [ ] Surface structural cohesion signals in generated agent guidance so agents
  proactively notice refactor pressure.
- [ ] Teach `doctor` to report active structure thresholds and ignored paths.
- [ ] Add tests for normal folders, warning folders, fresh-strict block folders,
  ignored folders, regex hint clusters, prefix clusters, and explicit registry
  exemptions.
- [ ] Document when to split into subpackages and use this repository's
  `guardrail_lib/config` extraction as the motivating example.

## Phase 9: Add Docs And Config Hygiene

- [ ] Add `markdownlint-cli2` support for Markdown structure.
- [ ] Enable Markdown linting for this repository once the docs pass cleanly.
- [ ] Add `yamllint` support when YAML files exist.
- [ ] Enable YAML linting for this repository if the workflow and pre-commit
  config pass cleanly.
- [ ] Add `taplo` support when TOML files exist.
- [ ] Enable TOML linting for this repository after formatting existing TOML.
- [ ] Add `check-jsonschema` support only where schemas or stable config
  contracts exist.
- [ ] Continue skipping `typos` and `codespell` as low-leverage AI-maintainability
  gates.
- [ ] Update `docs/tool-map.md` as each docs/config hygiene gate becomes
  supported.

## Phase 10: Raise Test Depth Toward 90 Percent

- [ ] Raise the coverage target only after meaningful tests exist.
- [ ] Add branch/error-path tests for `scripts/check_change_budget.py`.
- [ ] Add branch/error-path tests for `scripts/check_suppression_budget.py`.
- [ ] Add branch/error-path tests for `scripts/check_file_lengths.py`.
- [ ] Add branch/error-path tests for `scripts/check_tach_config.py`.
- [ ] Add branch/error-path tests for `scripts/guardrail_executor.py`.
- [ ] Add branch/error-path tests for `.codex/hooks/post_edit_fast_gate.py`.
- [ ] Add branch/error-path tests for `.codex/hooks/stop_full_verify.py`.
- [ ] Raise `coverage_fail_under` toward 90 only after the suite proves those
  paths.
- [ ] Avoid chasing 100 percent coverage unless it reflects real risk reduction.

## Phase 11: Add Slow And Advanced Profiles

- [ ] Add a slow/manual profile concept separate from normal `full`.
- [ ] Add `mutmut` as a slow/manual mutation-testing option.
- [ ] Document mutmut's POSIX fork requirement and Windows-through-WSL support.
- [ ] Add optional Semgrep support with local or pinned rules first.
- [ ] Add OSV Scanner only for mixed-ecosystem repositories.
- [ ] Add Trivy only for repositories with Docker, container, Kubernetes,
  Terraform, or other IaC assets.
- [ ] Add license checks as an optional policy gate.
- [ ] Add SBOM generation as a CI artifact, not a blocking default.
- [ ] Prefer `cyclonedx-python` for Python-only SBOMs.
- [ ] Prefer Syft/Grype for broader deployable or container projects.

## Explicit Non-Goals For Now

- [ ] Do not add Docker to this repository's own workflow.
- [ ] Do not make every supported scanner a default blocking gate.
- [ ] Do not make source-only changes a blanket CI failure without an escape
  hatch.
- [ ] Do not switch back from Tach to Import Linter for this repository.
- [ ] Do not adopt Betterleaks as the first default backend until its install and
  config story is clear for this kit.
- [ ] Do not raise docstring coverage to 100 percent as a default policy.
- [ ] Do not force arbitrary subfolders from folder file count alone; use count
  as a refactor signal, not as a standalone design proof.
