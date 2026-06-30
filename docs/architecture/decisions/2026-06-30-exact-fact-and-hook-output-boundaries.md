# ADR: Exact Fact Parsers and Hook Output Runner Boundaries

## Status

Accepted.

## Context

Review hardening found two boundary gaps after the context package split:

- hook runtime still owned bounded subprocess-output collection directly;
- exact repair facts were starting to grow beyond Ruff, Pyright, and Bandit into
  pytest, coverage, file-length, and change-budget parsing.

Keeping both changes inside the existing runtime and `pack.exact_facts` modules
would have hidden new responsibilities behind already important orchestration
files.

## Decision

Add focused modules for the new responsibilities:

- `agent_maintainer.hooks.subprocess_runner` owns temp-file-backed, bounded
  verifier subprocess output collection for agent hooks.
- `agent_maintainer.context.pack.fact_parsers` dispatches exact repair fact
  parsing.
- `agent_maintainer.context.pack.lint_fact_parsers`,
  `pytest_fact_parsers`, `log_fact_parsers`, and `fact_payloads` own their
  specific parsing and normalization concerns.

The Tach contracts assign each new file explicitly and keep `root_module =
"forbid"` coverage intact.

## Why This Is Not Architecture Drift

The new modules narrow responsibilities that were otherwise accumulating in
orchestration modules. `hooks.runtime` still decides when hooks run and what they
emit. `pack.exact_facts` still decides artifact ordering and generic fallback.
The new modules only perform bounded subprocess capture or parse specific
artifact/log formats.

## Alternatives Considered

Leaving everything in `hooks.runtime` and `pack.exact_facts` was rejected because
it would push those files toward file-length and module-member limits.

Adding suppressions for `wemake` or Tach was rejected because the split is
straightforward and creates clearer ownership.

Making each parser a public plugin interface was rejected as premature. The
parsers are internal implementation details for current verifier artifacts.

## Still Forbidden

Do not relax Tach strict-root coverage or add parser files without assigning
them to a domain contract. Do not let hook runtime capture unbounded verifier
stdout/stderr in memory. Do not add broad parser registries until there is a
real external extension use case.
