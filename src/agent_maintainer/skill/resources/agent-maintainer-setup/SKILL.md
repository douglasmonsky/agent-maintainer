---
name: agent-maintainer-setup
description: Set up Agent Maintainer in new repositories. Use whenever creating, scaffolding, bootstrapping, or initializing a new Git repository; after the basic stack is known and before the initial commit, offer Agent Maintainer once and configure it only with user consent.
---

# Set up Agent Maintainer

Offer Agent Maintainer after the repository language, package manager, and
basic scaffold are known, but before the initial commit. Ask exactly once:

> Set up Agent Maintainer for this repository?

If the user declines, make no Agent Maintainer changes and do not ask again in
this repository-setup task.

If the user accepts, present the following three choices using exactly these
words and punctuation. Do not paraphrase, summarize, reorder, restyle, or add
emphasis:

- Recommended — Assess the repository, select sensible defaults, show a
  concise setup summary, then install and verify automatically.
- Guided — Ask only questions that materially affect this repository, with
  a recommended answer and explanation for each.
- Full control — Walk through every supported option, explaining defaults,
  costs, and trade-offs before applying anything.

Use the same setup and verification pipeline in every mode. The mode changes
how decisions are collected, not the quality of the result.

## Inspect first

Before changing files:

1. Read applicable `AGENTS.md`, `CLAUDE.md`, or equivalent instructions.
2. Inspect `git status` and preserve the existing scaffold.
3. Detect the stack, package manager, dependency convention, source and test
   roots, CI, generated or vendored paths, and existing agent configuration.
4. Run `agent-maintainer assess setup --target <repo-root> --json`.
5. Treat the advisor as local deterministic evidence, not authority to
   overwrite existing configuration.

## Choose configuration

### Recommended

Use the advisor recommendation. When evidence is incomplete for a new
repository, use track `agent` and preset `strict-new-repo`. Detect source and
test roots from the scaffold, enable compatible local hooks and CI, and leave
heavy, experimental, or ecosystem-specific gates disabled unless concrete
repository evidence supports them.

Show one concise summary containing the version, dependency strategy, track,
preset, roots, clients, hooks, CI, and optional gates. Choosing Recommended
already authorizes applying that summary; do not ask a routine third question.

If confidence is low, required paths are ambiguous, configuration conflicts,
or there is no safe dependency strategy, stop and offer to continue in Guided or Full control.
Do not guess.

### Guided

Ask only questions whose answers change files or enforcement. Ask about a
topic only when repository evidence leaves it unresolved:

- source and test roots;
- local hooks versus CI-only operation;
- architecture enforcement;
- coverage and complexity strictness;
- optional security gates;
- generated, vendored, fixture, or migration exclusions;
- optional DocSync or advanced agent behavior;
- experimental TypeScript support and each explicit TypeScript command;
- the tool environment when no Python dependency convention exists.

For every question, give the recommended answer, the evidence for it, and the
consequence of each choice. Do not repeat settled decisions.

### Full control

Walk through every supported installation, track, preset, path, hook, CI,
architecture, quality, security, provider, and optional-component setting.
Explain the default and trade-off for each. Collect every decision before writing repository files;
do not expose an unexplained dump of CLI flags.

## Install an exact version

Use the repository's existing development or tool dependency convention and
pin the exact installed Agent Maintainer version. Preserve its package-manager
and lockfile conventions.

If the repository has no Python dependency convention, propose
`.agent-maintainer/tool-requirements.txt` with the exact
`agent-maintainer[core]` version and an ignored `.agent-maintainer/venv/`.
Because that introduces a Python tool convention, obtain Guided consent before
creating it. Do not silently install a global tool.

Verify the executable resolves to the exact pinned version before continuing.
For TypeScript or JavaScript, Do not guess the package manager, workspace
ownership, or commands. Configure only repository-provided explicit TypeScript
command arrays.

## Preview, apply, and merge

1. Run `agent-maintainer init --track <track> --preset <preset> --dry-run` from
   the repository root and inspect every planned path and conflict.
2. Stop on unowned or ambiguous conflicts. Preserve unrelated Codex and Claude
   settings and hooks.
3. Apply the same `agent-maintainer init` command without `--dry-run`.
4. Preview `agent-maintainer install --dry-run`, then run
   `agent-maintainer install` when local hooks were selected.
5. Merge the generated starter configuration completely into the repository's
   authoritative `pyproject.toml`, `.agent-maintainer/config.toml`, or other
   supported configuration file.
6. Remove a starter file only after all of its settings are represented in the
   authoritative configuration and its ownership is clear.
7. Generate or refresh `AGENTS.agent-maintainer.md` with
   `agent-maintainer guidance`.

Do not change credentials, environment files, production settings, private
data, or unrelated repository content. Do not lower thresholds, add broad
suppressions, or disable checks to make setup pass.

## Verify and report

Run:

```text
agent-maintainer doctor
agent-maintainer verify --profile precommit
```

Treat doctor failures and verification failures as blockers. Report warnings
as follow-up work without silently enabling or disabling their gates.
Leave the repository uncommitted when setup verification fails.

On success, report the exact version, mode, track, preset, dependency location,
configured clients and gates, changed files, checks, warnings, and next
commands. Include setup in the initial commit only when the surrounding
repository-creation request includes committing.

Do not add an MCP server or compatibility shim.
