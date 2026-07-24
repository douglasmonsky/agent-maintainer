# Symphony Pilot Environment Assessment

Assessment date: 2026-07-24

Pilot repository: `douglasmonsky/agent-maintainer`

## Recommendation

Run the official Symphony reference implementation as a pinned user-level
binary outside the repository. Use GitHub Issues with the opt-in `agent-ready`
label, one isolated clone per issue, one concurrent worker, a dedicated Codex
home, the stock loopback-only dashboard, and `scripts/status-symphony` for
Git/PR facts the dashboard does not expose.

The repository's experimental task broker remains a planning and manual
handoff incubator. Its documented worker backends do not launch agents, so it
does not duplicate Symphony.

## Codex Installation

| Item | Observed state |
|---|---|
| Codex CLI | `codex-cli 0.146.0-alpha.3.1` |
| CLI path | `/Applications/ChatGPT.app/Contents/Resources/codex` |
| Desktop bundle | ChatGPT/Codex build `26.715.52143` (`5591`) |
| Authentication | Logged in through ChatGPT; no secret value inspected |
| App Server | Available and experimental; stdio is supported |
| User config | `~/.codex/config.toml` |
| Existing profiles | `deep`, `routine`, and `urgent` separate config files |
| Pilot Codex home | `~/.codex-symphony/config.toml` |
| Interactive defaults | `workspace-write`, approval `never`, network enabled |
| Global instructions | `~/.codex/AGENTS.md` plus repository `AGENTS.md` |

The installed CLI accepts `--profile` for runtime commands but rejects it for
`app-server`. The pilot therefore starts App Server with
`CODEX_HOME=~/.codex-symphony`, whose `config.toml` contains only restricted
autonomous defaults and whose `auth.json` is a symlink to the existing
permission-restricted ChatGPT login. Project `.codex/config.toml` may still be
discovered, so the Symphony command also disables hooks and multi-agent
execution through highest-precedence CLI overrides.

## Symphony Installation

| Item | Observed state |
|---|---|
| Source | Official [`openai/symphony`](https://github.com/openai/symphony) |
| Source revision inspected | `f8e8b8a670c799f6e0ade7a8c25c4bf4a4a56ec7` |
| Installed release | `v0.0.2`, published 2026-07-24 |
| Binary | `~/.codex/bin/symphony-v0.0.2` |
| Stable link | `~/.codex/bin/symphony` |
| Integrity | Official SHA-256 asset verified successfully |
| Service model | User-level process; no daemon, `sudo`, firewall, or public bind |
| Dashboard | Phoenix LiveView and JSON API on `127.0.0.1:4000` |

Symphony is explicitly labeled an early engineering preview. Pinning and
controlled upgrades are required.

## MCP Inventory

Symphony injects its own repository tracker tool; no Desktop MCP is required
for the pilot.

| MCP | Desktop | Symphony | Reason | Required changes |
|---|---|---|---|---|
| `unity-mcp` | Disabled | Disabled | Unity relay; unrelated and potentially interactive | None |
| `node_repl` | Enabled | Disabled | Carries Browser, Chrome, and Computer Use environment and broad UI capability | Keep Desktop-only |
| `open-design` | Enabled | Disabled | Fixed local daemon and checkout path | Make workspace-relative before reconsidering |
| `headroom` | Enabled | Disabled | Host service not required for issue delivery | Audit data and filesystem reach first |
| `computer-use` | Disabled | Disabled | Desktop UI control is inappropriate unattended | Keep Desktop-only |
| `openaiDeveloperDocs` | Disabled | Disabled | Remote read-only docs are unnecessary for scoped workers | Enable only for documentation issues if needed |
| `serena` | Enabled | Disabled | JetBrains broker requires project activation; current pilot semantics are unavailable | Prove per-workspace broker activation before allowlisting |
| `serena_lsp` | Disabled | Disabled | LSP context is not currently configured for this Python repository | Evaluate only after a workspace-local setup |
| `playwright` | Enabled | Disabled | `npx ...@latest`, browser/network access, and no pilot need | Pin a version and scope to localhost before use |
| `gitnexus` | Enabled | Disabled | Useful for impact analysis, but host indexes may span repositories | Prove per-workspace indexing and bounded graph access |
| Symphony `github_api` | N/A | Enabled | Built-in host-side GitHub adapter, scoped by workflow and token permissions | Prefer a repository-only fine-grained token |

The configured MCPs do not contain secret values. The GitHub tracker token is
resolved in the host process, and Symphony removes declared tracker-token
variables from the App Server child. Git pushes may still use the user's Git
credential helper, which is a residual host-credential boundary.

## Skills Inventory

Current Codex discovers repository skills under `.agents/skills`, user skills
under `~/.agents/skills`, and system/plugin skills from their installed
locations.

| Skills | Classification | Symphony posture |
|---|---|---|
| `symphony-github-work` | Repository-local | Required and safe for the pilot |
| Agent Maintainer guidance and setup | Global reusable | Guidance is safe; setup is not invoked in this existing repository |
| `test-selector`, `pr-review`, `spec-to-plan`, `task-intake` | Global reusable | Safe when issue scope calls for them |
| GitNexus skill family | Global reusable; tool-dependent | Instructions may load, but the MCP is disabled pending workspace proof |
| `agent-perf` | Global reusable; conditional | Use only for measured performance issues |
| GitHub plugin skills | Global reusable; connected-tool dependent | Not required because Symphony injects `github_api` |
| Browser, Chrome, Computer Use, UI, document, and connected-app skills | Desktop-only for this pilot | Tools are disabled or absent in the worker |
| Data Analytics and artifact skills | Global reusable; task-specific | Not needed for repository implementation issues |
| Legacy `.codex/skills` layout from the handoff | Obsolete for current discovery | Do not create |

No pre-existing repository-local skill implemented autonomous issue delivery.
The new skill contains only GitHub delivery procedure; orchestration settings
remain in `WORKFLOW.md`.

## Repository Readiness

The repository is unusually strong for autonomous work:

- root and generated Agent Maintainer instructions define architecture,
  thresholds, change budgets, test requirements, and bounded failure evidence;
- `Justfile` provides canonical fast, precommit, full, CI, security, manual,
  and long-wait commands;
- Tach architecture contracts and ADR rules constrain dependency drift;
- issue and pull-request templates already enforce privacy and evidence;
- CI spans Python compatibility, coverage, lint, architecture, security, docs,
  packaging, and live Java/Gradle checks;
- the existing task-broker experiment explicitly separates orchestration from
  core business logic.

The pilot adds only the missing issue-readiness template, lifecycle procedure,
Symphony contract, service wrappers, and operations/security documentation.

Discovery also found the TypeScript `0.1.0b14` publication plan still marked
active after both implementation PRs merged, the trusted publish workflow
succeeded, and PyPI published `0.1.0b14`. That stale status rejected every
unrelated branch diff and prevented a valid Symphony change plan. The pilot
marks that plan complete without changing its historical scope.

## GitHub Readiness

| Item | Observed state |
|---|---|
| Repository | Public; Issues enabled |
| Current identity | `douglasmonsky`, repository permission `ADMIN` |
| Git auth | GitHub CLI keyring authentication; token value not printed |
| Default branch | `main` |
| Required check | `verify`, strict/up-to-date |
| Pull requests | Required; stale reviews dismissed; conversations resolved |
| Admin enforcement | Enabled |
| Force pushes/deletions | Disabled |
| Project board/ruleset | No repository ruleset or open project-state workflow found |
| Existing autonomous labels | None before this pilot |

GitHub's Symphony adapter models only `open` and `closed`. The richer lifecycle
therefore uses the minimal labels `agent-ready`, `agent-running`,
`agent-blocked`, and `human-review`. Dependency relations are not normalized by
the GitHub adapter, so issue text and the worker readiness gate must enforce
dependencies during this pilot.

## Official-Implementation Differences

- GitHub Issues is now a built-in Symphony adapter; a custom tracker adapter is
  not required.
- The GitHub adapter injects `github_api` host-side and removes tracker-token
  environment variables from the Codex child.
- `WORKFLOW.md` supports `required_labels`, explicit App Server approval and
  sandbox policies, retry backoff, turn/stall timeouts, and a loopback web
  server.
- The stock dashboard exposes run/retry/block counts, turns, tokens, last
  activity, retry/block reasons, and issue detail JSON containing workspace
  paths.
- The stock dashboard does not expose branch, dirty files, recent commit,
  persisted verification status, or PR URL. `scripts/status-symphony` adds
  those facts from Symphony JSON, Git, verification artifacts, and GitHub.
- Codex App Server isolation uses a dedicated `CODEX_HOME`, and repository
  skills live under
  `.agents/skills`.
- Codex Desktop does not need a private App Server deep link for intervention;
  the supported `codex app <workspace>` command opens the workspace as a new
  Desktop context.

## Residual Risks

- Symphony `v0.0.2` is an early preview with an unstable schema.
- Public issue content is untrusted input. Only maintainers should apply
  `agent-ready`, and the worker must still reject ambiguous or unsafe issues.
- The current GitHub identity has broader permissions than a future bot should.
- Network access is necessary for clone, dependencies, push, and GitHub, so the
  workspace sandbox is not a network isolation boundary.
- All optional MCPs are disabled for the pilot. Serena and GitNexus should be
  enabled only after isolated-workspace path and data-scope tests pass.
- Verification can be long and resource-intensive; concurrency remains one.
