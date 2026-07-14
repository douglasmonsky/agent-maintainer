# Dual-Client Agent Maintainer Setup Skill Design

Date: 2026-07-13
Status: approved conversational design

## Context

Agent Maintainer has a deterministic setup advisor, transactional initializer,
doctor, verification profiles, and managed Codex and Claude Code hooks. The
missing first-use layer is agent guidance that notices a new repository at the
right time, asks whether Agent Maintainer should be adopted, and completes the
configuration instead of leaving the user to translate documentation into a
working setup.

The primary use case is repositories created by the same user, not general
third-party adoption. The feature should still behave consistently in Codex
and Claude Code because setup is the only major Agent Maintainer workflow that
would otherwise remain client-specific.

Codex and Claude Code both consume directory-based skills with a `SKILL.md`
entry point. A shared skill can therefore orchestrate the existing CLI without
introducing an MCP server.

## Goals

- Offer Agent Maintainer once during every new-repository setup, after the
  stack and basic scaffold exist and before the initial commit.
- Make declining safe, silent, and final for that repository-setup task.
- Give users Recommended, Guided, and Full control configuration modes with a
  concise description of each mode before selection.
- Install an exact Agent Maintainer version as a repository-owned development
  or tool dependency.
- Produce a complete, verified configuration instead of an unmerged starter
  file.
- Ship one canonical skill that works in personal Codex and Claude Code skill
  directories.
- Keep installation, update, status, and uninstall ownership-safe.

## Non-Goals

- An Agent Maintainer MCP server.
- Organization-wide or marketplace distribution in the first release.
- Silent setup without the user's initial consent.
- Automatic modification of production settings, credentials, or private
  data.
- Replacing the setup advisor, initializer, doctor, or verifier with logic in
  the skill.
- Compatibility wrappers for older beta interfaces.

## User Interaction

### Trigger and timing

The skill metadata must say that it applies whenever an agent creates or
initializes a new Git repository. The agent waits until the language, package
manager, and basic scaffold are knowable, then asks before the initial commit:

> Set up Agent Maintainer for this repository?

The offer is made once per repository-setup task. A decline causes no writes
and suppresses another offer during the same task.

If the user accepts, the agent presents three choices with these descriptions:

- **Recommended** — Assess the repository, select sensible defaults, show a
  concise setup summary, then install and verify automatically.
- **Guided** — Ask only questions that materially affect this repository, with
  a recommended answer and explanation for each.
- **Full control** — Walk through every supported option, explaining defaults,
  costs, and trade-offs before applying anything.

The mode changes how decisions are collected, not the quality or verification
of the resulting setup.

### Recommended mode

Recommended mode runs the setup advisor and uses its recommendation. When a
new repository does not provide enough distinguishing evidence, the defaults
are:

- track `agent`;
- preset `strict-new-repo`;
- configure Codex and Claude Code when their clients are present;
- detect source and test roots from the scaffold;
- enable compatible local hooks and CI;
- leave heavy, experimental, or ecosystem-specific gates disabled unless
  repository evidence supports them.

Before writing, the agent shows the selected track, preset, dependency
strategy, clients, roots, hooks, CI, and optional gates. Choosing Recommended
mode already authorizes applying that summary; it does not add a routine third
confirmation.

If the advisor is low-confidence, required paths are ambiguous, an existing
configuration conflicts, or the repository lacks a safe dependency strategy,
Recommended mode stops and offers to continue in Guided or Full control mode.
It does not guess.

### Guided mode

Guided mode asks only questions whose answers change generated files or
enforcement. Depending on repository evidence, these may cover:

- ambiguous source and test roots;
- local hooks versus CI-only operation;
- architecture enforcement;
- coverage and complexity strictness;
- optional security gates;
- experimental TypeScript support;
- generated, vendored, fixture, or migration exclusions;
- optional DocSync or advanced agent behavior;
- a repository-owned tool environment when no Python dependency manager
  exists.

Each question states the recommendation, its evidence, and the consequence of
each answer. Settled decisions are not asked again.

### Full control mode

Full control walks through every supported installation, track, preset, path,
hook, CI, architecture, quality, security, provider, and optional-component
setting. Questions are grouped by topic, but every supported option receives a
decision. Each question explains the default and trade-off instead of exposing
an unexplained list of CLI flags. All answers are collected before any
repository files are written.

## Architecture

### Canonical skill

The Agent Maintainer package ships one canonical skill directory named
`agent-maintainer-setup`. Its common `SKILL.md` uses only the shared `name` and
`description` frontmatter. The body stays client-neutral and delegates factual
assessment and mutation to Agent Maintainer commands.

Codex UI metadata lives in `agents/openai.yaml` beside the common skill.
Claude Code treats it as an unused supporting file. No separate Claude skill
body is maintained.

The skill is installed into personal client directories so it is available
before a new repository contains project-local instructions:

```text
~/.codex/skills/agent-maintainer-setup/
~/.claude/skills/agent-maintainer-setup/
```

### Installer commands

Add a focused command group:

```text
agent-maintainer skill install --client codex --client claude-code
agent-maintainer skill status
agent-maintainer skill uninstall --client codex
agent-maintainer skill uninstall --client claude-code
```

`install` copies packaged resources instead of symlinking into an environment
that may later be removed. The default remains explicit client selection. The
public installation example selects both clients as the recommended personal
installation.

Each installed directory contains a hidden Agent Maintainer ownership manifest
with the package version, client, managed relative paths, and content hashes.
The clients ignore this file. Status classifies each installation as missing,
current, stale, or locally modified.

An update replaces only managed files whose current hashes still match the
previous manifest. Uninstall removes only still-owned files and removes the
skill directory only when it is empty. Locally modified or unrelated files are
reported and preserved.

### Trigger reliability

The shared description is the first routing mechanism. It must explicitly
mention creating, scaffolding, bootstrapping, or initializing a new repository
and the pre-initial-commit offer.

Fresh-session acceptance tests determine whether this metadata triggers both
clients reliably. Global Codex or Claude instruction files are not changed by
default. If either client misses the trigger, add the smallest marked routing
instruction for that client, manage it with the same ownership rules, and
repeat the fresh-session test. Do not add an MCP server to solve routing.

## Repository Setup Pipeline

After consent and mode selection, every mode executes the same pipeline:

1. Read applicable repository instructions and inspect `git status`.
2. Detect the stack, package manager, dependency convention, source and test
   roots, CI, existing Agent Maintainer state, and installed agent clients.
3. Run `agent-maintainer assess setup --target <root> --json`.
4. Resolve mode-specific decisions without writing repository files.
5. Add the exact published Agent Maintainer version using the repository's
   existing development dependency convention.
6. If no Python dependency convention exists, propose
   `.agent-maintainer/tool-requirements.txt` containing the exact
   `agent-maintainer[core]` version and an ignored
   `.agent-maintainer/venv/` created with the available Python interpreter.
   Install from that manifest and invoke the platform-appropriate executable
   inside the environment. Because this introduces a Python tool convention,
   Recommended mode escalates to Guided mode before creating it.
7. Verify that the invoked executable reports the exact selected version.
8. Run `agent-maintainer init` with the selected track and preset in dry-run
   mode and inspect its conflict report.
9. Apply initialization transactionally.
10. Merge the generated starter configuration into the repository's
    authoritative `pyproject.toml`, `.agent-maintainer/config.toml`, or other
    supported configuration location.
11. Remove the starter only when its complete content is represented in the
    authoritative configuration and the initializer owns its removal.
12. Generate or refresh `AGENTS.agent-maintainer.md`.
13. Run `agent-maintainer doctor` and the `precommit` verification profile.
14. Review the final Git diff and report changed files, selected configuration,
    checks, warnings, and exact next commands.
15. Include setup in the initial commit only when the surrounding repository-
    creation request includes committing.

The skill orchestrates these commands and decisions. Setup classification,
file generation, managed hook merging, doctor policy, and verification remain
owned by the existing Agent Maintainer implementation.

## Safety and Error Handling

- Never overwrite existing configuration silently.
- Preserve unrelated Codex and Claude settings and hooks.
- Treat the expected uncommitted scaffold as user work and avoid reverting or
  hiding it.
- Keep credentials, environment files, production settings, and private data
  out of assessment output and generated files.
- Stop on dependency installation failure, version mismatch, initializer
  conflict, or any doctor failure.
- Report doctor warnings as follow-up items; do not silently convert them into
  failures or disable their gates.
- Do not lower thresholds, add broad suppressions, or remove checks merely to
  make the first verification pass.
- Leave the repository uncommitted when setup verification fails.
- Make skill installation and repository setup idempotent.
- Preserve locally modified installed skill files during update and uninstall.

## Verification

### Portable skill contract

- Validate the canonical `SKILL.md` against Codex skill rules.
- Validate the same file against Claude Code's common Agent Skills contract.
- Assert that the description covers all new-repository trigger phrases and
  the required pre-commit offer.
- Assert that the skill describes Recommended, Guided, and Full control modes
  exactly once and includes the approved explanations.

### Installer tests

Use temporary home directories to cover:

- Codex-only, Claude-only, and dual installation;
- correct packaged content and ownership manifests;
- repeated installation without changes;
- stale packaged content update;
- locally modified file refusal;
- missing, current, stale, and locally modified status;
- ownership-safe partial and complete uninstall;
- preservation of unrelated files in either skill directory.

### Interaction and repository fixtures

Cover these scenarios:

- declining the initial offer makes no changes and does not prompt again;
- a fresh Python repository completes Recommended mode;
- a fresh TypeScript repository retains explicit provider commands and does
  not guess unsupported package-manager behavior;
- a low-confidence or conflicting repository escalates from Recommended to
  Guided mode;
- existing Codex and Claude configuration is preserved;
- Guided mode asks only material unresolved questions;
- Full control records a decision for every supported option;
- the exact dependency is pinned, starter configuration is fully merged, both
  clients coexist, doctor passes, and the selected verifier passes.

### Fresh-session forward tests

Start independent Codex and Claude Code sessions with a normal request to
create a new repository. Do not mention the skill or expected answer. Each
client must:

1. create enough scaffold to identify the repository;
2. offer Agent Maintainer before the initial commit;
3. make no Agent Maintainer changes before consent;
4. present accurate Recommended, Guided, and Full control descriptions after
   consent.

If metadata-only routing fails, implement the bounded managed routing
instruction described above and repeat both tests.

### Repository gates

Run focused skill-resource, installer, CLI, initializer, and documentation
tests, then the canonical strict Pyright and full verifier. Update public setup
and installation documentation and its DocSync evidence when the new commands
and workflow become public.

## Alternatives Considered

### Separate Codex and Claude skills

Rejected because their setup decisions and safety requirements would drift.
Client differences are limited to installation paths and optional metadata, so
they do not justify two skill bodies.

### MCP-backed setup service

Rejected for the first version. The existing CLI already exposes deterministic
assessment, initialization, doctor, and verification behavior, while Codex and
Claude Code can both execute local commands and edit files. An MCP server would
add process lifecycle, registration, security, and compatibility work without
solving a demonstrated capability gap.

### Silent automatic adoption

Rejected because adding a dependency, hooks, CI, and enforcement policy is an
intentional repository decision. The initial consent prompt is required even
when Recommended mode will perform the remaining routine setup automatically.

## Success Criteria

The feature succeeds when a user creating a new repository in either Codex or
Claude Code is offered Agent Maintainer once, can choose an appropriately
explained setup mode, and receives an exact-pinned, conflict-safe, fully merged,
doctor-clean, verified configuration without needing to know Agent Maintainer's
CLI or configuration model.
