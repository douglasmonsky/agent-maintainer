# Phase 191: C/C++ Cross-Platform And External Proof

Status: planned

## Goal

Qualify the experimental provider with live cross-platform fixtures and pinned
public-repository evidence before any maturity or blocking-policy decision.

## Scope

- Run live Linux/GCC, macOS/Clang, and Windows/MSVC fixtures.
- Audit and pin three public CMake repositories, one centered on each
  platform/toolchain.
- Commit immutable SHAs and sanitized report projections only.
- Measure activation time, command duration, classification misses, false
  positives, report completeness, repair iterations, artifact size, path leaks,
  and repeated-run stability.
- Publish the qualification report and remaining unsupported surface.

## Selection Criteria

The cohort collectively covers predominantly C, modern C++, mixed sources and
headers, multiple CMake targets, all three toolchains, and at least one
supported structured report per platform.

## Non-Goals

- No vendored third-party source tree.
- No provider promotion, blocking gate, automatic setup, or new build system.
- No repository selection based only on a passing happy path.

## Acceptance Criteria

- Every live fixture exercises config, commands, doctor, and structured facts.
- Every external projection is reproducible from an immutable public commit.
- No raw third-party report body or absolute checkout path is persisted.
- Missing and unsafe evidence produces actionable failures.
- Repeated unchanged runs are stable.
- Existing Python, TypeScript/JavaScript, and Java/Gradle checks remain green.
- Public docs state every observed unsupported tool and layout.

## Completion Decision

Qualification closes the experiment track but does not promote the provider.
Promotion requires a separate review of noise, maintenance cost, user demand,
and hosted CI stability.
