<!-- docsync:object docs.context_safety.overview -->
# Context Safety

Context safety keeps verification feedback useful when a repository has large
files, long logs, broad diffs, or many existing violations. The goal is to give
agents enough evidence to repair the next issue without flooding the working
context.

Default behavior is conservative:

- summarize first;
- keep full generated artifacts on disk;
- show omitted counts when output is bounded;
- require explicit commands before printing large supporting context.

## Failure Expansion

Use `context failures` to inspect failed checks from `.verify-logs/manifest.json`
without dumping raw logs:

```bash
python -m agent_maintainer context failures
python -m agent_maintainer context failures --check pyright
python -m agent_maintainer context failures --limit 20
python -m agent_maintainer context failures --budget 16000
python -m agent_maintainer context failures --format json
```

Failure output is grouped by repair priority, including type errors, test
failures, coverage failures, architecture failures, structure ratchets,
suppression issues, security/tooling findings, and style/noise.

## Log Expansion

Use `context log` to inspect only the relevant slice of a verifier log:

```bash
python -m agent_maintainer context log pyright --tail 120
python -m agent_maintainer context log pytest-coverage --head 80 --tail 120
python -m agent_maintainer context log ruff --lines 200:260
python -m agent_maintainer context log pyright --budget 20000
python -m agent_maintainer context log pyright --confirm-large
```

Large log selections are refused by default when safer expansion options exist.
Use `--confirm-large` only when larger output is intentionally needed.

## Context Estimates

Use `context estimate` before expanding large files, logs, or diffs:

```bash
python -m agent_maintainer context estimate
python -m agent_maintainer context estimate --file src/legacy/big.py
python -m agent_maintainer context estimate --log pyright --tail 500
python -m agent_maintainer context estimate --diff --summary
```

Estimates report approximate character and token cost using
`tokens ~= chars / 4`. Large log refusals include a matching estimate command so
agents can inspect cost before raising `--budget` or using `--confirm-large`.

## Safe File Context

Use `context file` for bounded file navigation instead of dumping large files:

```bash
python -m agent_maintainer context file src/example.py --outline
python -m agent_maintainer context file src/example.py --symbols
python -m agent_maintainer context file src/example.py --symbol Example.method
python -m agent_maintainer context file src/example.py --lines 40:80
python -m agent_maintainer context file src/example.py --around 120 --context 20
python -m agent_maintainer context file src/example.py --format json
```

The command refuses symlinks, binary or non-UTF-8 files, notebooks, lock files,
cache/build paths, generated files, and minified JSON. Python outlines use AST
metadata when possible and fall back to regex/chunk navigation when syntax is
broken.

## Bounded Diff Context

Use `context diff` to inspect changed code without dumping full diffs:

```bash
python -m agent_maintainer context diff --summary
python -m agent_maintainer context diff --name-only --limit 80
python -m agent_maintainer context diff --path src/example.py
python -m agent_maintainer context diff --path src/example.py --hunks 5
python -m agent_maintainer context diff --base-ref origin/main
python -m agent_maintainer context diff --staged
```

Summaries include changed file counts, Python/test/docs/generated categories,
largest changed files, rename/move candidates, import-only candidates,
shown/omitted path counts, and expansion commands.

## Context Packs

Use `context pack` to generate a bounded repair packet without dumping full logs,
files, or diffs into agent context. By default, the command writes pack files and
prints a compact repair-capsule pointer:

```bash
python -m agent_maintainer context pack
python -m agent_maintainer context pack --budget 16000
python -m agent_maintainer context pack --check pytest-coverage
python -m agent_maintainer context pack --file src/legacy/big.py
python -m agent_maintainer context pack --format json
```

The command always writes:

```text
.verify-logs/context/PACK.md
.verify-logs/context/PACK.json
```

Use `--print-full` only when you intentionally need the full Markdown pack:

```bash
python -m agent_maintainer context pack --print-full
```

The Markdown pack separates exact repair facts from supporting context, labels
repository tool excerpts as untrusted, includes ratchet state when a baseline
exists, records omitted counts, and ends with safe expansion commands. Use the
JSON pack for automation and the Markdown pack for deliberate human or agent
handoff.

Exact repair facts are structured and bounded. When verifier artifacts provide
machine-readable locations, such as Ruff, Pyright, or Bandit JSON, context packs
surface check, file, line, symbol, severity, and message before any log
expansion. Logs remain supporting evidence, not the primary repair source.

## Retention Upload Policy

Context packs are local-only by default because they may include source excerpts
or selected verification output:

```text
.verify-logs/context/PACK.md
.verify-logs/context/PACK.json
```

Keep normal verification artifacts upload-safe by uploading explicit top-level
paths:

```text
.verify-logs/manifest.json
.verify-logs/LAST_FAILURE.md
.verify-logs/*.log
.verify-logs/*.json
!.verify-logs/context/**
```

Do not upload the whole `.verify-logs/` directory unless context packs are
explicitly disabled or marked upload-safe:

```toml
[tool.agent_maintainer]
context_write_context_packs = false
# or:
context_packs_local_only = false
context_pack_contains_source = false
```

`agent-maintainer doctor` warns when GitHub Actions artifact upload settings
include local-only source-bearing context packs.

## Hook Failure Pointers

Agent Maintainer hooks generate a context pack when verification fails, then
emit a compact repair capsule instead of dumping raw verifier output into the
agent conversation. Hook output includes result, profile, run id when available,
top repair facts, one likely next action, one expansion command, and the pack
artifact path while remaining bounded by `context_hook_budget_chars`.

If pack generation fails, hooks fall back to bounded verifier output and include
the pack-generation error so the failure remains diagnosable.
<!-- docsync:object.end docs.context_safety.overview -->
