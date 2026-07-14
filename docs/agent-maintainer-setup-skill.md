<!-- docsync:object docs.agent_maintainer_setup_skill.overview -->
# Agent Maintainer Setup Skill

Install one shared personal skill so Codex and Claude Code offer Agent
Maintainer while creating a repository:

```bash
python -m agent_maintainer skill install --client codex --client claude-code
python -m agent_maintainer skill status
```

The command copies the same packaged instructions to
`~/.codex/skills/agent-maintainer-setup/` and
`~/.claude/skills/agent-maintainer-setup/`. It records the package version and
SHA-256 digest of each managed file. It does not add an MCP server or modify a
repository.

## New Repository Offer

When an agent creates, scaffolds, bootstraps, or initializes a Git repository,
the skill waits until the language, package manager, and basic scaffold are
known. The agent then asks once, before the initial commit:

> Set up Agent Maintainer for this repository?

Declining makes no Agent Maintainer changes. Accepting opens three modes:

- **Recommended** assesses the repository, selects sensible defaults, shows a
  concise summary, and installs and verifies automatically.
- **Guided** asks only questions that materially affect this repository, with
  a recommended answer and explanation for each.
- **Full control** walks through every supported option and explains defaults,
  costs, and trade-offs before applying anything.

All modes use the same preview, setup, and verification pipeline. They differ
only in how decisions are collected.

## Repository Adoption

The agent preserves the repository's dependency and lockfile conventions and
pins the exact installed `agent-maintainer[core]` version. It previews
`agent-maintainer init` and local-hook installation before applying them,
merges generated configuration into the authoritative project configuration,
then runs:

```bash
agent-maintainer doctor
agent-maintainer verify --profile precommit
```

Setup remains uncommitted if a required check fails. Successful setup is part
of the initial commit only when the surrounding repository-creation request
already includes committing.

## Update Or Remove The Personal Skill

Re-run install after upgrading Agent Maintainer:

```bash
python -m agent_maintainer skill install --client codex --client claude-code
```

Current installs are unchanged. Stale files owned by an older package version
are replaced. If a managed file was edited, ownership is malformed, or the
destination existed without an Agent Maintainer manifest, the command refuses
to overwrite it.

To remove only verified managed files:

```bash
python -m agent_maintainer skill uninstall --client codex --client claude-code
```

Uninstall preserves unrelated files in the skill directory and also refuses
locally modified managed files. Resolve those files manually rather than
forcing ownership.
<!-- docsync:object.end docs.agent_maintainer_setup_skill.overview -->
