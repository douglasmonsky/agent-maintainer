# Context Safety

Context safety keeps verification feedback useful when a repository has large
files, long logs, broad diffs, or many existing violations. The goal is to give
agents enough evidence to repair the next issue without flooding the working
context.

Default behavior stays conservative:

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

Large log selections are refused by default with safer expansion options. Use
`--confirm-large` only when the larger output is intentionally needed.

## Context Estimates

Use `context estimate` before expanding large files, logs, or diffs:

```bash
python -m agent_maintainer context estimate
python -m agent_maintainer context estimate --file src/legacy/big.py
python -m agent_maintainer context estimate --log pyright --tail 500
python -m agent_maintainer context estimate --diff --summary
```

Estimates report approximate character and token cost using `tokens ~= chars / 4`.
Large log refusals include a matching estimate command so agents can inspect
cost before raising `--budget` or using `--confirm-large`.

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

Use `context pack` to generate a bounded repair packet agents can reopen
without dumping full logs, files, or diffs:

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

The Markdown pack separates exact repair facts from supporting context, labels
repository and tool excerpts as untrusted, includes ratchet state and top
targets when a baseline exists, records omitted counts, and ends with safe
expansion commands. Use the JSON pack for automation and the Markdown pack for
human or agent handoff.
