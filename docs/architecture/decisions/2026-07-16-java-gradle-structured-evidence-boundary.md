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
- Java report adapters depend on finding identity, and the runner composes fresh
  report evidence with the comparator only after a successful Gradle process.
  Provider-neutral file ceilings and JaCoCo thresholds remain separate policies.
- Checkstyle, PMD, SpotBugs, and JUnit share one bounded, entity-free XML input
  primitive. Checkstyle, PMD, and SpotBugs expose normalized `JavaFinding`
  records; SpotBugs exposes native-filter identities separately, while JUnit
  exposes bounded totals plus failure/error details instead of debt findings.
- Source paths emitted by quality tools are normalized beneath the configured
  Gradle root. Published messages and test details are whitespace-normalized and
  truncated independently of the XML parser's harder resource ceiling.
- Provider report declarations are resolved to one task per evidence plan.
  Executed tasks require a newly written snapshot; cached and up-to-date tasks
  may reuse complete reports; no-source tasks require report absence and cannot
  satisfy required tests. All other or ambiguous outcomes fail closed.
- A failed Gradle process remains authoritative. Successful runs then apply, in
  order, task outcome checks, report confinement and freshness, parser
  completeness, findings debt comparison, and bounded artifact publication.
- Static runner artifacts record the producing Git commit. Explicit baseline
  create/prune accepts only complete, non-truncated evidence from that exact
  current commit and a clean worktree; inspect remains read-only.

The modules remain Java-owned. Core verification receives only bounded result
artifacts and does not learn third-party report formats or Java baseline schema.
Repair-fact parsing consumes that already-bounded artifact through the shared
single-read context budget; it never reopens raw Gradle XML or follows an
artifact-provided path.

The provider-neutral file-ceiling subsystem has its own versioned group/path
schema and create/inspect/prune lifecycle. It applies the same defaults,
established floors, rename behavior, and prune rules to Java, Python, and other
configured groups without importing Java finding identity or report formats.

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
