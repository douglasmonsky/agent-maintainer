# Symphony Pilot Security Model

## Trust Boundaries

Symphony runs as the current macOS user. It is not a container, VM, privileged
daemon, or production isolation boundary. Codex receives a workspace-write
sandbox rooted at the issue clone, but the worker also has network access for
dependencies, Git, and GitHub.

The reference binary describes itself as running without the usual guardrails
and requires an explicit acknowledgement flag. For this pilot, the compensating
controls are an opt-in label, one repository, one worker, a dedicated Codex
home, workspace-only Codex writes, disabled optional MCPs/hooks/subagents, a
loopback-only dashboard, required verification, manual review, and no auto-merge.

Only trusted maintainers may apply `agent-ready`. Issue content, repository
content, dependencies, and external responses remain untrusted inputs.

## Credentials

| Credential | Storage | Exposure |
|---|---|---|
| Codex login | Existing Codex/ChatGPT credential store | Used by App Server; not copied into the repository |
| GitHub CLI login | Existing OS keyring | Start script retrieves it for the Symphony host without printing it |
| `GITHUB_TOKEN` | Symphony process environment | Removed from the Codex child by the GitHub adapter |
| Git push credential | Existing Git credential helper/keyring | May be reachable by `git push` from the worker |

No credential is stored in `WORKFLOW.md`, repository files, logs, issues, or
pull requests. Do not copy `.env`, `auth.json`, or unrelated host environment
files into an issue workspace.

The current user token has repository administration and broad scopes. The
recommended post-pilot improvement is a dedicated fine-grained token or bot
limited to this repository with Issues, Pull requests, and Contents permissions
required for comments, labels, branches, and PRs. Creating or granting that
credential remains a human action.

## Codex Policy

- Codex home: `~/.codex-symphony`;
- authentication: `auth.json` is a permission-restricted symlink to the
  existing ChatGPT login; no credential is copied into a workspace;
- approval: `never`;
- thread sandbox: `workspace-write`;
- turn policy: workspace write with network access;
- hooks: disabled by CLI override;
- multi-agent spawning: disabled by CLI override;
- optional MCPs: disabled;
- worker concurrency: one;
- App Server transport: local stdio child process.

The worker must stop and label the issue blocked instead of seeking an
interactive approval that no human is monitoring.

## GitHub Tool

Symphony's injected `github_api` executes in the host process using the
configured tracker credential. The child receives a tool interface, not the
token value. Scheduler polling is repository-specific, but the raw tool's
ultimate authority is still bounded by the credential, so least privilege is
important.

The worker may:

- read and update the scoped issue;
- manage the four lifecycle labels;
- maintain one workpad comment;
- open or update its pull request.

The worker may not change branch protection, repository visibility, Actions
secrets, environments, billing, collaborators, or security settings.

## Repository and Data Rules

- Never include secrets, private records, real student data, access tokens, or
  identifying datasets in prompts, fixtures, logs, screenshots, commits, issue
  comments, or PRs.
- Prefer synthetic fixtures and aggregate output.
- Review staged files and diffs for secrets before push.
- Do not relax tests, coverage, architecture contracts, security scans, or
  branch protection to obtain a pass.
- Do not execute issue-authored destructive commands without explicit human
  authorization.
- Dependencies are installed only from repository-declared lock/config files.

## Service and Network

The dashboard binds only to `127.0.0.1:4000`. The scripts use an ephemeral
per-user `launchctl` job; they do not expose it publicly, open firewall ports,
install a privileged or persistent system daemon, or use `sudo`.

Network access includes OpenAI, GitHub, package indexes, and repository-declared
tool downloads. This is necessary for the pilot and is a residual exfiltration
risk. Optional browser, Computer Use, and remote MCP tools remain disabled.

## Destructive-Action Protections

- Symphony is stopped with a validated PID and `SIGTERM`; the script refuses an
  unrelated process.
- Workspace cleanup is manual and not implemented as recursive deletion.
- The worker does not merge, close issues, force-push, rewrite history, or
  change protected settings.
- Existing checkouts and uncommitted work are not used as worker workspaces.
- Retry requires an explicit maintainer-applied `agent-ready` label.

## Known Residual Risks

- `v0.0.2` is an early preview.
- A compromised dependency or repository instruction can influence a worker.
- The current user's Git credential helper may grant more access than the
  injected tracker tool.
- The host process and current macOS account are outside the Codex workspace
  sandbox.
- Network access cannot be restricted to an allowlist by this workflow.
- Dashboard history is limited; the status script and GitHub workpad provide
  operational evidence, not a tamper-proof audit log.
- Disabled MCPs reduce capability. Enabling Serena or GitNexus requires the
  isolated-workspace audit in the operations guide.
