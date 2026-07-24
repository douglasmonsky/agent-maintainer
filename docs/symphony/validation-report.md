# Symphony Pilot Validation Report

Status: implementation and preflight in progress

## Test Issue

The end-to-end issue will be a narrow documentation contract change with
deterministic Markdown and repository verification. It will use the full
agent-ready template and must not require product, architecture, credential,
production, or destructive decisions.

The issue number, URL, workspace, branch, pull request, and final evidence will
be recorded here after the live run.

## Preflight Evidence

- Official Symphony `v0.0.2` macOS ARM64 asset downloaded.
- Official SHA-256 verification passed.
- Stable versioned install and symlink created under `~/.codex/bin`.
- Codex CLI, App Server availability, Codex login, GitHub login, repository
  permission, branch protection, required checks, and open PR state inspected.
- Repository work isolated from an unrelated dirty checkout in
  `/Users/Monsky/Developer/Codex/agent-maintainer-symphony-pilot`.
- Current `WORKFLOW.md` schema checked against the official `v0.0.2` source.
- A dedicated `~/.codex-symphony` App Server home was created with no optional
  MCPs and with hooks and multi-agent execution disabled. An initial
  `--profile symphony` live claim failed before its first turn because the
  installed CLI does not support profiles for `app-server`; the dedicated-home
  mechanism replaced it and retained strict CLI overrides.
- Initial service start failed closed because `v0.0.2` requires an explicit
  engineering-preview acknowledgement flag not shown in short help; the wrapper
  was corrected using the official CLI source before retrying.
- Change-plan preflight found the TypeScript `0.1.0b14` publication plan stale.
  PRs 415 and 416 were merged, publish run `29770203488` succeeded, and PyPI
  reports `0.1.0b14`; its status was changed from active to complete so the
  Symphony plan can be the repository's single active plan.

## Required Live Timeline

1. Create the bounded issue without `agent-ready`.
2. Start Symphony and confirm the dashboard/API are healthy.
3. Add `agent-ready`.
4. Observe the issue claim and isolated workspace creation.
5. Confirm the App Server starts with the dedicated Symphony `CODEX_HOME`.
6. Confirm `github_api` operates without exposing its credential.
7. Observe `agent-running`, workpad creation, branch creation, and edits.
8. Observe focused and final verification.
9. Observe commit, push, pull request, and verification evidence.
10. Observe `human-review` and removal of dispatch labels.
11. Open the workspace with `codex app <path>`.
12. Run one safe blocked-state issue and confirm precise escalation.

## Results

Pending the live run.

## Expansion Recommendation

Remain at one worker until the live issue-to-PR run, blocked escalation, manual
intervention, and cleanup procedure all pass. Do not enable optional MCPs or
increase concurrency based on preflight alone.
