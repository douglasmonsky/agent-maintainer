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
