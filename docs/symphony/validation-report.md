# Symphony Pilot Validation Report

Status: pilot mechanics validated; autonomous PR creation externally blocked

## Preflight Evidence

- Official Symphony `v0.0.2` macOS ARM64 asset and published SHA-256 verified.
- Stable versioned binary and reversible symlink installed under
  `~/.codex/bin`.
- Codex CLI/App Server, ChatGPT login, GitHub login, repository permission,
  branch protection, required checks, and open PR state inspected.
- Current `WORKFLOW.md` schema checked against official `v0.0.2` source.
- Full repository verifier passed before publication: run
  `20260724T185948249024Z-full-cae9d82e65f5`.
- Setup commit was pushed to `codex/symphony-pilot` and draft PR
  [#423](https://github.com/douglasmonsky/agent-maintainer/pull/423) opened.
- The per-user `launchctl` service stayed alive after the initiating command,
  with dashboard and JSON API on loopback.
- The worker obtained unmerged pilot configuration through the explicit
  `SYMPHONY_SOURCE_REF=codex/symphony-pilot` launch environment. The source
  commit was visible in every clean issue clone.

## Compatibility Corrections

- `v0.0.2` requires an engineering-preview acknowledgement flag not shown in
  short help; the wrapper supplies it only alongside documented pilot controls.
- The installed Codex CLI rejects `--profile` for `app-server`. A dedicated
  `~/.codex-symphony` App Server home replaced the profile approach while
  retaining strict CLI overrides.
- Current Codex protects `.git` recursively under `workspace-write`. A
  mode-`0555`, absolute-path execution-rule bridge now limits out-of-sandbox
  Git writes to a direct `GH-<number>` issue clone, its matching branch,
  explicit publish paths, a Conventional Commit, and push.
- The stale TypeScript `0.1.0b14` plan was marked complete only after PRs
  #415/#416, publish run `29770203488`, and PyPI `0.1.0b14` were verified.
- The full gate found newly published GitPython advisories. A Python 3.13
  lock refresh changed only GitPython `3.1.52` to `3.1.55`; the configured
  audit then passed with only the repository's existing time-bounded ignores.

## Bounded Implementation Exercise

Issue [#424](https://github.com/douglasmonsky/agent-maintainer/issues/424)
authorized one documentation file.

Validated:

- Symphony claimed the issue and created an isolated workspace from pushed
  setup commit `8fbfdb6`.
- Dedicated App Server authentication succeeded without exposing the GitHub
  token to the child.
- The Git bridge created `codex/symphony-gh-424`.
- The worker added `agent-running`, maintained one workpad, and changed only
  `docs/symphony/operations.md`.
- Focused Markdown lint passed.
- Full verifier passed in the issue workspace: run
  `20260724T192808210147Z-full-d7f0b4678694` in 3m05s.
- The bridge published commit `5d1af53` to origin.
- `codex app /Users/Monsky/Developer/Codex/symphony-workspaces/agent-maintainer/GH-424`
  successfully opened the preserved workspace in Desktop.

Blocked:

- Pull-request creation returned an opaque GitHub server error through
  Symphony's injected REST tool, direct REST, and `gh pr create`, against both
  `main` and the stacked setup branch.
- GitHub's status API reported API Requests and Pull Requests operational.
- The branch, commit, verification artifacts, and workpad are preserved.
  Issue #424 is `agent-blocked`; no credential, permission, or repository
  setting change is indicated.

## Token Evidence

| Exercise | Model calls | Aggregate input | Cached input | Non-cached input | Output |
|---|---:|---:|---:|---:|---:|
| Initial Git-permission block | 12 | 306,082 | 266,496 (87.1%) | 39,586 | 3,222 |
| One-file implementation rerun | 47 | 2,262,556 | 2,149,120 (95.0%) | 113,436 | 13,040 |
| Intentional decision block | 8 | 183,339 | 151,808 (82.8%) | 31,531 | 2,187 |

The one-file run is not a healthy steady-state cost even though caching worked.
The dominant mechanism was repeated large-context model calls during verifier
waiting and equivalent PR mutation retries. Equivalent failed external
mutations are now capped at one retry. Concurrency remains one.

## Controlled Blocked-State Exercise

Issue [#425](https://github.com/douglasmonsky/agent-maintainer/issues/425)
intentionally withheld a harmless public terminology choice.

- Worker made no repository changes.
- Workpad identifies the exact “Paused” versus “Needs attention” decision.
- It records why the choice is required, its lack of security impact, how to
  verify resolution, and how to requeue.
- Final labels are exactly `agent-blocked`; `agent-ready` and `agent-running`
  are absent.
- Full verification was correctly skipped because implementation was
  explicitly prohibited.

## Expansion Recommendation

Do not expand this pilot yet. Keep one worker, no optional MCPs, and no
auto-merge until:

1. GitHub accepts PR creation for the preserved #424 branch.
2. At least two more bounded tasks complete below an agreed token/call budget.
3. A repository-only GitHub identity replaces the current broad user token.
4. Serena or GitNexus is individually proven in a disposable isolated
   workspace before being allowlisted.
