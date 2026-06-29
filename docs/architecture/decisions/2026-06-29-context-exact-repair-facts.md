# Architecture Decision: Context Exact Repair Facts

Status: accepted

## Context

Context packs had the correct high-level structure, but exact repair facts only
reported that a check failed with an exit code. Agents still had to expand logs
before seeing file and line locations even when structured verifier artifacts
already existed.

## Decision

Add `agent_maintainer.context.exact_facts` as the structured artifact extraction
module for context packs. It reads artifact paths from verifier manifest failure
records and extracts bounded facts from known JSON artifacts, starting with
Ruff, Pyright, and Bandit.

`packs.py` remains responsible for pack orchestration. `pack_rendering.py`
renders normalized fact fields including location and symbol when present.

## Alternatives Considered

Parsing selected log excerpts was rejected because context packs already treat
logs as untrusted supporting evidence and keep them bounded.

Adding extraction directly to `packs.py` was rejected because that file already
orchestrates log selection, file outlines, compression, ratchet state, and
rendering.

## Still Forbidden

Exact fact extraction must remain bounded and structured. It must not dump whole
logs, source files, or unbounded artifact payloads into hook output or context
packs.
