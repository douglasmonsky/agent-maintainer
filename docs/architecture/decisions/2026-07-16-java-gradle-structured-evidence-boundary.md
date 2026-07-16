# Java/Gradle Structured Evidence Boundary

## Status

Accepted on 2026-07-16.

## Context

Checkstyle, PMD, and later Java report adapters need one low-noise finding
identity and an explicit existing-debt lifecycle. Line numbers move during
unrelated edits, duplicate findings are meaningful, and numeric complexity
values must ratchet without becoming part of identity. This policy cannot live
in the generic verifier or in native SpotBugs filter handling.

## Decision

- `agent_maintainer.ecosystems.java.findings` owns normalized repository-relative
  paths, normalized text, semantic finding identity, and SHA-256 fingerprints.
- A fingerprint includes tool, rule, path, semantic subject, message, and
  severity. It excludes source line and numeric measurement.
- `agent_maintainer.ecosystems.java.baseline` owns a strict versioned JSON
  schema, source-commit provenance, duplicate occurrence counts, numeric
  ceilings, deterministic rendering, and bounded parsing.
- Duplicate findings compare as a multiset. Numeric duplicates match highest
  current values to highest stored ceilings so removal of a lower duplicate
  cannot create a false regression.
- Baseline creation and pruning are explicit lifecycle operations. Verification
  is comparison-only and may never create, overwrite, or prune a baseline.
- Java report adapters may depend on finding identity; the runner may later
  compose fresh report evidence with the comparator. Provider-neutral file
  ceilings and JaCoCo thresholds remain separate policies.
- Checkstyle, PMD, SpotBugs, and JUnit share one bounded, entity-free XML input
  primitive. Checkstyle, PMD, and SpotBugs expose normalized `JavaFinding`
  records; SpotBugs exposes native-filter identities separately, while JUnit
  exposes bounded totals plus failure/error details instead of debt findings.
- Source paths emitted by quality tools are normalized beneath the configured
  Gradle root. Published messages and test details are whitespace-normalized and
  truncated independently of the XML parser's harder resource ceiling.

The modules remain Java-owned. Core verification receives only bounded result
artifacts and does not learn third-party report formats or Java baseline schema.

## Alternatives considered

- Including line number in identity was rejected because harmless source edits
  would recreate existing debt.
- Collapsing duplicates into a set was rejected because an additional identical
  finding is new debt.
- Storing only one maximum numeric value was rejected because duplicate methods
  need independent ceilings and deterministic matching.
- Reusing the native SpotBugs filter was rejected because Checkstyle and PMD do
  not share that format or lifecycle.

## Forbidden boundaries

- Do not accept unknown baseline fields or versions through compatibility
  shims.
- Do not treat malformed, oversized, mixed numeric/nonnumeric, or unconfined
  finding input as an empty baseline.
- Do not persist source-line movement as debt identity.
- Do not let baseline comparison override a failed Gradle execution.
- Do not persist raw Gradle XML or treat truncated repair facts as the source of
  truth for native tool output.
