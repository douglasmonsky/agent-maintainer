"""Starter pyproject configuration template."""

from __future__ import annotations

STARTER_PYPROJECT = """\
# Starter Agent Maintainer config for package-first adoption.
# Merge this into your repository's pyproject.toml, then tune paths.

[tool.agent_maintainer]
# Kit default for existing repositories. Use "fresh-strict" only after the
# repository is clean enough for strict checks to block immediately.
mode = "custom"
architecture_tool = "import-linter"

# Core paths. Package users should not vendor src/agent_maintainer into their app.
source_roots = ["src"]
test_roots = ["tests"]
package_paths = ["src"]
coverage_source = ["src"]
file_length_paths = ["src", "tests", ".codex/hooks", ".claude/hooks"]
structure_paths = ["src", ".codex/hooks", ".claude/hooks"]
structure_ignore_paths = [
  "tests/**",
  "migrations/**",
  "generated/**",
  ".venv/**",
  "venv/**",
  "**/__pycache__/**",
]
vulture_paths = ["src", "tests", ".codex/hooks", ".claude/hooks"]

# Core policy. This kit default is intentionally lower than this repo's
# self-enforced 90 percent total coverage setting.
require_tests = true
coverage_fail_under = 80
diff_cover_fail_under = 90
file_length_max_physical = 600
file_length_max_source = 450
change_warn_lines = 300
change_block_lines = 800
change_warn_files = 8
change_block_files = 20
source_without_test_change_error_profiles = []
allow_source_without_test_change = false
cohesive_change_override_enabled = false
cohesive_change_override_paths = ["src/**"]
cohesive_change_override_max_lines = 2000
cohesive_change_override_max_files = 40
suppression_max_new = 3
xenon_max_absolute = "B"
xenon_max_modules = "A"
xenon_max_average = "A"
ruff_max_complexity = 10
pyright_type_checking_mode = "standard"

# Planned context-safe legacy repair layers. These fields are inert until the
# matching features are adopted.
context_default_budget_chars = 12000
context_hook_budget_chars = 8000
context_last_failure_budget_chars = 16000
context_pack_budget_chars = 24000
context_large_file_threshold_lines = 800
context_large_file_threshold_bytes = 250000
context_max_direct_file_read_lines = 250
context_max_direct_log_read_lines = 200
context_max_failure_items = 10
context_max_paths_default = 50
context_require_outline_for_large_files = true
context_compression_enabled = false
context_compression_backend = "extractive"
context_compression_target_ratio = 0.5
context_compression_require_backend = false
ratchet_enabled = false
ratchet_baseline_path = ".agent-maintainer/ratchet-baseline.json"
ratchet_guidance_path = "AGENTS.ratchet.md"
ratchet_target_limit = 5
large_changes_enabled = false
large_change_plan_dirs = [".agent-maintainer/change-plans"]
large_change_max_active_plans = 1
large_change_allow_expired_plans = false
large_change_require_required_sections = true
large_change_fail_out_of_plan_paths = true

# Optional hardening gates stay off until explicitly adopted.
enable_pip_audit = false
pip_audit_args = ["-r", "config/dev-lock.txt"]
enable_wemake = false
enable_interrogate = false
interrogate_fail_under = 80
enable_markdownlint = false
markdownlint_paths = ["**/*.md"]
enable_yamllint = false
yamllint_paths = [
  ".github/workflows",
  ".github/dependabot.yml",
  ".pre-commit-config.yaml",
  "*.yml",
  "*.yaml",
]
enable_taplo = false
taplo_paths = ["pyproject.toml", "tach.toml", "config/*.toml"]
enable_check_jsonschema = false
check_jsonschema_args = []
enable_secret_scanning = false
secret_scanner = "gitleaks"
secret_scan_profiles = ["full", "ci"]
secret_scan_history_profiles = ["security"]
enable_semgrep = false
semgrep_args = [
  "scan",
  "--config",
  "semgrep.yml",
  "--error",
  "--metrics=off",
  "src",
]
semgrep_profiles = ["manual"]
enable_osv_scanner = false
osv_scanner_args = ["scan", "source", "-r", "."]
osv_scanner_profiles = ["manual"]
enable_trivy = false
trivy_args = [
  "fs",
  "--scanners",
  "vuln,misconfig",
  "--format",
  "json",
  "--exit-code",
  "1",
  ".",
]
trivy_profiles = ["manual"]
enable_sbom = false
sbom_args = [
  "requirements",
  "config/dev-lock.txt",
  "--output-reproducible",
  "--of",
  "JSON",
]
sbom_profiles = ["ci"]
enable_license_check = false
license_check_args = ["--from=mixed", "--format=json"]
license_check_profiles = ["manual"]

[tool.agent_maintainer.diagnostics]
enabled = true
log_dir = ".verify-logs"
"""
