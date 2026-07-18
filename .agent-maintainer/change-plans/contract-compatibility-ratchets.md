+++
id = "contract-compatibility-ratchets"
kind = "feature"
status = "active"
base_ref = "453a00f"
expires = 2026-08-15
allowed_paths = [
  ".agent-maintainer/change-plans/contract-compatibility-ratchets.md",
  ".agent-maintainer/contracts-baseline.json",
  ".agent-maintainer/contracts.toml",
  ".docsync/**",
  "CHANGELOG.md",
  "README.md",
  "config/agent-maintainer-capabilities.json",
  "config/agent-maintainer-cli.json",
  "config/dev-lock.txt",
  "docs/ROADMAP.md",
  "docs/api-support-policy.md",
  "docs/architecture/decisions/2026-07-18-contract-compatibility-ratchets.md",
  "docs/architecture/subsystem-stability.md",
  "docs/roadmap/full-roadmap-blueprint.md",
  "docs/roadmap/phases/phase-184-contract-compatibility-ratchets.md",
  "docs/superpowers/plans/2026-07-18-contract-compatibility-ratchets.md",
  "docs/superpowers/specs/2026-07-18-contract-compatibility-ratchets-design.md",
  "docs/tool-map.md",
  "pyproject.toml",
  "schemas/agent-waits-wait-record.schema.json",
  "schemas/codex-app-server-wait.schema.json",
  "src/agent_maintainer/catalogs/catalog.py",
  "src/agent_maintainer/catalogs/global_checks.py",
  "src/agent_maintainer/catalogs/tach.domain.toml",
  "src/agent_maintainer/cli.py",
  "src/agent_maintainer/contracts/**",
  "src/agent_maintainer/core/executor.py",
  "src/agent_maintainer/verify/groups.py",
  "tach.toml",
  "tests/catalogs/test_contract_catalog.py",
  "tests/config/test_config_reference.py",
  "tests/contracts/**",
  "tests/packaging/test_package_metadata.py",
  "tests/packaging/test_public_docs.py",
  "tests/packaging/test_script_helpers.py",
  "tests/release/test_release_packaging.py",
  "tests/verify/test_verification_groups.py",
  "tests/wait/test_agent_waits_core.py",
  "tests/wait/test_codex_app_server.py",
]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 90
max_changed_lines = 15000
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++
# Cohesive Change Plan: contract-compatibility-ratchets

## Why this change intentionally large

Phase 184 joins strict authored policy, canonical baseline evidence, four
semantic extractors, a shared compatibility classifier, version and migration
obligations, deterministic reports, CLI behavior, and one conditional verifier
gate. These surfaces form one control-layer contract: a repository change must
produce the same exact compatibility facts in local inspection, automated
enforcement, and hosted review.

The file count also includes five source-backed dogfood contracts, architecture
records, roadmap updates, and DocSync evidence invalidated by the new public
command and catalog entry. Those records are scoped proof of the implementation,
not unrelated feature breadth.

## Why this should not be split smaller

The implementation uses focused test-first commits, but shipping extractors
without anti-bypass base/current/live evaluation would permit baseline rewrites
to hide drift. Shipping enforcement without deterministic reports, exact
decisions, version obligations, and migration evidence would make failures
opaque. The policy, kernel, adapters, and gate must therefore be reviewed
against one branch base.

## What allowed to change

Only the new contract-ratchet domain and tests, authored/generated contract
files, five dogfood manifests or schemas, the required PEP 440 runtime parser,
direct root CLI/catalog/verifier/Tach integration, synthetic regression fixtures,
architecture and roadmap records, public documentation, DocSync evidence, and
the approved design and execution plan may change.

## What must not change

Do not import or execute target repository code, execute target commands, use
the network or a shell, rewrite package versions or migrations, broadly accept
baselines, suppress existing checks, add runtime dependencies beyond the
approved PEP 440 parser, classify failure history, or perform unrelated refactors.
Production data, credentials, billing,
deployments, and external account state remain outside scope.

## Verification plan

Implement every behavior test-first. Run focused model, policy, baseline,
extractor, classifier, version, migration, service, CLI, catalog, dogfood, and
documentation suites; exact Tach and Archguard checks; DocSync; the self-hosted
contract command; classifier mutation checks; fresh full, CI-equivalent, and
security profiles; one comprehensive review; and all protected hosted checks.

## Risks

The primary risks are false compatibility claims from ambiguous source syntax,
unsafe repository-path or Git-blob handling, nondeterministic fingerprints,
baseline rewrite bypass, incorrect prerelease recommendations, and accidental
coupling from the inward domain to verifier infrastructure. Strict decoding,
bounded pure-data extraction, exact fingerprints, three-way comparison, and
Tach contracts address those risks.

## Rollback plan

Revert the Phase 184 commits in reverse order. The feature changes no production
data or external state. Removing the optional catalog entry and authored policy
restores the prior verifier behavior; removing the generated baseline and
dogfood manifests requires no data repair.

## Follow-up ratchet work

Phase 185 owns recurring failure fingerprinting and machine-readable repair
packets. The external-proof cohort continues in parallel as a measurement track.
