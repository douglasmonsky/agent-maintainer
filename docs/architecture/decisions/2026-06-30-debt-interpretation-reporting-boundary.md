# Debt Interpretation Reporting Boundary

## Context

Phase 73 makes Technical Debt Score output clearer for humans and agents. The
score builder already owns debt risk semantics, while the text renderer owns
CLI presentation. Without an explicit dependency, the CLI text renderer could
drift from JSON, Markdown, HTML, and PR-summary interpretation.

## Decision

Allow `agent_maintainer.assess.reporting` to depend on
`agent_maintainer.assess.debt_score` for the shared debt interpretation helpers.
The renderer still does not compute scores; it only reuses advisory wording
derived from the score.

## Consequences

Debt interpretation wording stays consistent across text, JSON, Markdown, HTML,
and PR-summary surfaces. The scoring and category construction boundary remains
inside `debt_score` and `debt_categories`.

What remains forbidden: reporting modules should not inspect repository files,
collect evidence, or make scoring decisions. They should only render typed
reports.
