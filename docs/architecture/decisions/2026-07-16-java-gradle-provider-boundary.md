# Java/Gradle Provider Boundary

## Status

Accepted.

## Context

Agent Maintainer needs Java support for future repositories without adding Java
assumptions to the Python catalog or publishing an external provider API. Gradle
already owns Java build topology, source sets, plugins, toolchains, and task
execution. Reimplementing those responsibilities would create a second,
unreliable build model.

## Decision

Add Java/Gradle as a built-in experimental provider behind
`[tool.agent_maintainer.java].enabled`.

The Java package owns file classification, explicit profile-aware task planning,
checked-in wrapper confinement, and the command-only grouped runner. The shared
catalog owns ordering; the verifier owns profiles, execution, artifacts, and the
two parallel verification groups. Normal doctor performs static wrapper,
runtime, and configuration checks and never invokes Gradle.

The runner may execute only explicitly configured tasks through the exact
repository wrapper. It must not search `PATH` for Gradle, invoke a shell, add
`clean`, force daemon/cache/parallel flags, or discover tasks during normal
verification.

Tach records these dependencies explicitly. The provider remains internal and
experimental while setup templates, report parsing, findings baselines, and
coverage ratchets are implemented and calibrated.

## Consequences

Java repositories can opt into bounded `format`, `static`, and `tests` groups
without changing Python or TypeScript behavior. Gradle remains authoritative,
and failures are surfaced through one execution-only structured artifact per
group during the foundation phase.

The explicit task contract requires setup guidance and later observation before
Agent Maintainer can claim structured findings or coverage enforcement.

## Alternatives Considered

- A generic arbitrary-command provider was rejected because it would not encode
  wrapper confinement, task ownership, report evidence, or Java repair facts.
- Calling a system `gradle` executable was rejected because it is not
  repository-versioned or reproducible.
- A public plugin API was deferred until multiple built-in providers have proven
  stable boundaries through real use.

## Still Forbidden

The Java provider must not reproduce Gradle's project model, add Maven/Android/
Kotlin support implicitly, execute `tasks --all` during normal doctor or
verification, copy raw third-party reports into run history, or claim report,
baseline, setup, or coverage support before those phases land.
