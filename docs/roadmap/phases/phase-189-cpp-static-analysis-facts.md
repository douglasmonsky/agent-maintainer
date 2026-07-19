# Phase 189: C/C++ Static-Analysis Facts

Status: planned

## Goal

Turn supported Clang-Tidy and Cppcheck reports into safe, deterministic,
agent-useful repair facts.

## Scope

- Parse Clang-Tidy exported-fixes YAML.
- Parse Cppcheck XML version 2.
- Normalize paths, locations, diagnostic codes, severities, messages, and
  stable semantic identities.
- Bound documents, findings, messages, duplicates, and retained facts.
- Reject unsafe paths, unsupported schemas, malformed required evidence, and
  unknown formats.
- Register compact summaries and exact repair facts from one runner artifact.
- Compare external evidence before considering a findings baseline.

## Non-Goals

- No SARIF, compiler-text, clang-analyzer plist, or sanitizer parsing.
- No automatic tool flags, config generation, or baseline creation.
- No default static-analysis threshold or provider promotion.

## Acceptance Criteria

- Fixtures cover GCC-, Clang-, and MSVC-shaped paths, LF/CRLF, malformed
  neighbors, duplicates, truncation, and deterministic ordering.
- Absolute or escaping paths never become context targets.
- Repair-fact consumers read the bounded runner artifact once.
- Successful repeated parses produce byte-stable normalized output.
- A baseline is absent unless measured evidence and a separate lifecycle design
  justify it.

## Phase 190 Handoff

Reuse provider-neutral bounded XML and path primitives where their contracts are
truly neutral; do not couple test or coverage facts to static-analysis identity.
