# Phase 180: TypeScript OSV Dependency Facts

## Status

Complete on 2026-07-17.

## Objective

Turn existing OSV Scanner v2 artifacts into deterministic, path-safe repair
facts and compact summaries that are useful for TypeScript dependency failures
without creating a TypeScript-specific security command.

## Scope

- Register `osv-scanner.json` with the shared repair-fact registry.
- Normalize current nested package versions with a legacy outer-version
  fallback.
- Emit one fact per OSV alias group, with valid ungrouped advisories preserved.
- Extract fixed versions only from `affected[].ranges[].events[].fixed`.
- Reuse the same normalization for compact core summaries and context facts.
- Record offline public npm and pnpm compatibility projections.
- Improve setup-advisor wording when package metadata and a lockfile coexist.

The implementation reuses the existing global `enable_osv_scanner` setting,
catalog command, JSON artifact, installation policy, and `manual` profile. It
does not add a provider command, infer package-manager commands, install
dependencies, or change scanner exit status.

## Safety Boundary

Only non-empty OSV string fields are accepted. Valid repository-relative source
paths remain targetable provenance. Absolute paths, parent traversal, and
Windows drive paths are reduced to a non-targetable filename label. Facts never
include local checkout roots or raw vulnerability details beyond the bounded
summary, aliases, severity, and fixed versions consumed by the repair loop.

The parser sorts before retaining 500 findings. Compact failed-check summaries
contain at most 50 total lines, reserving the last line for an omission count
when needed. Context packs keep the existing five-fact-per-check limit.

## Evidence

Synthetic fixtures cover alias grouping, nested and legacy versions, fixed
events, malformed neighbors, unsafe paths, deterministic ordering, summaries,
and all three retention bounds. The core summary and repair-fact paths consume
the same normalized parser result.

OSV Scanner 2.4.0 captured two pinned public repositories without installing
dependencies or running package scripts:

- `vitest-dev/eslint-plugin-vitest` at
  `7c697f8a53d7d7551b00ef11217d58cd45a0cf7d`, using
  `pnpm-lock.yaml` and `pnpm@10.18.3`;
- `jsynowiec/node-typescript-boilerplate` at
  `550dfd2a976d69254ed71eb6f5a6c5ee20060807`, using
  `package-lock.json` and npm.

Each committed projection records the repository, revision, lockfile and raw
report hashes, scanner version, exit status, normalization method, and counts.
It retains at most 25 sorted alias groups and removes all temporary machine
paths. Normal tests replay the projections offline without OSV Scanner or
network access.

## Acceptance Criteria

- Current OSV v2 package shapes and legacy version fallback parse safely.
- Alias-equivalent advisories produce one repair fact and one summary line.
- Fixed versions come only from OSV fixed events.
- Unsafe paths never become context targets or fixture metadata.
- Parser, summary, and context bounds have explicit tests.
- Public npm and pnpm projections replay deterministically offline.
- OSV remains explicit, optional, ecosystem-neutral, and manual by default.
- TypeScript/JavaScript remains experimental.

## Verification

Focused parser, summary, context, setup-advisor, public-fixture, documentation,
DocSync, architecture, formatting, and lint checks cover this phase. Manual,
security, and full verification profiles run before publication because this
phase changes evidence and guidance for a manual security gate.

## Completion Notes

Phase 180 OSV dependency facts are complete. The new evidence does not promote
the provider or make OSV blocking. Package-manager audit facts are the next
parity slice; changed-line coverage, mutation, broader security adapters, and
blocking TypeScript/React reviewability remain later roadmap work.
