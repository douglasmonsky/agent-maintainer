# Java/Gradle Setup and Native-Ratchet Boundary

## Status

Accepted on 2026-07-16.

## Context

Java setup must support deterministic new-repository scaffolds while preserving
arbitrary existing Gradle builds. The setup path also needs a reviewed diff and
stale-content check before local writes, plus later task/report observations and
native SpotBugs baseline creation. Those concerns do not belong in the generic
provider registry or verifier catalog.

## Decision

- `agent_maintainer.core.setup_plans` owns provider-neutral reviewed file edits,
  diff digests, repository confinement, stale-source checks, and delegation to
  the existing transactional initializer.
- `agent_maintainer.ecosystems.java.setup` owns recognized Gradle scaffold
  planning and deterministic Java ruleset writes.
- `agent_maintainer.ecosystems.java.semantic_edits` owns typed agent handoffs,
  returned validation evidence, and the second reviewed digest for arbitrary
  build edits.
- Java defaults and bundled templates remain Java-owned and are package data.
- Later observation and bounded report modules may depend on the checked wrapper
  and Java configuration, but normal verification remains command-only.

This is not architecture drift: the shared layer knows only exact file edits
and transaction safety, while every Gradle concept remains inside the Java
provider package.

## Alternatives considered

- Regex-rewriting arbitrary Groovy or Kotlin DSL was rejected because it cannot
  preserve build semantics reliably.
- Reimplementing transactional writes in the Java provider was rejected because
  the initializer already owns backup and rollback behavior.
- A Gradle Tooling API, custom plugin, or hidden init script was rejected because
  it would introduce a second runtime product and weaken wrapper confinement.

## Forbidden boundaries

- No arbitrary build is applied without a displayed, approved semantic diff and
  successful validation evidence.
- No setup path may escape the repository or apply after its reviewed source
  changes.
- Verification never creates or rewrites setup files or baselines.
- Java setup never imports CLI orchestration, executes system Gradle, or rewrites
  unrelated workflows and project files.
