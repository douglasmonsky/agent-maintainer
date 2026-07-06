<!-- docsync:object docs.case_studies_future_call_roi_loop.overview -->
# Future-Call ROI Loop Dogfood Case Study

This case study records the July 6, 2026 dogfood loop used after the
runtime-event, waiter, local observability, and scoring-dataset phases landed
on `main`.

## Goal

Show whether Agent Maintainer's Future-Call ROI loop gives future agents better
next actions for cost, quality, and speed without adopting an external
orchestration framework.

## Baseline Workflow

Before phases 149 through 159, the normal roadmap loop relied on a maintainer or
agent to read the roadmap, inspect raw verifier artifacts, hand-poll pull
request checks, and infer follow-up tests from broad failure logs.

No pre-phase run captured an apples-to-apples token, dollar, or elapsed-time
baseline for the same task. This study therefore treats quantitative baseline
cost and speed impact as unavailable.

## New Workflow

After phases 149 through 159, the dogfood loop used repo-native primitives:

- PR waits used the repository waiter instead of manual check polling.
- Runtime events summarized local command and verifier activity.
- Technical-debt assessment gave a single advisory debt score with category
  evidence.
- Setup assessment confirmed the repository's expected `agent` track and
  `ai-agent-heavy` preset from tracked files.
- Repair-fact coverage identified whether failed checks had structured facts or
  only fallback summaries.
- Test-intelligence scans identified narrow Hypothesis and mutation candidates.
- Verifier profiles produced run-scoped artifacts rather than raw logs in chat.

Generated analysis artifacts stayed under `.verify-logs/`; this page records
only compact measured facts.

## Evidence

| Surface | Command or artifact | Measured result |
| --- | --- | --- |
| Technical debt | `python3 -m agent_maintainer assess debt` | Technical debt score `6/100` (`low`) with `high` confidence and zero findings. The summary was: "The repo has strong maintenance controls; keep ratchets fresh." |
| Setup fit | `python3 -m agent_maintainer assess setup --json` | Recommended track `agent`, preset `ai-agent-heavy`, `high` confidence. The scan inspected 1,027 tracked files, including 377 source files and 226 Python test files. |
| Runtime events | `python3 -m agent_maintainer events summary` | 143 events across 18 files, zero malformed lines, and four failure records, all tied to the manual `pyright-strict-ratchet` verifier run. |
| Runtime waste | `python3 -m agent_maintainer events waste` | Warned about security/manual overlap, three heavy profiles in the sampled window, fresh verifier runs without reuse events, and 42 generated/cache artifacts. Wait-poll counts and same-state duplicate verification were not yet measurable. |
| Repair facts | `python3 -m agent_maintainer assess repair-fact-coverage --json` | Latest failed manual check had one fallback fact and zero structured facts, so structured repair-fact coverage was `0.0%` for that failure. |
| Focused next tests | `python3 -m agent_maintainer test-intel hypothesis-candidates --limit 5` and `python3 -m agent_maintainer test-intel mutation-targets --limit 5` | Both scans ranked `src/agent_maintainer/assess/debt_security.py::security_score`, `src/agent_maintainer/config/coercion.py::coerce_updates`, and `src/archguard/impact.py::boundary_status` as top follow-up targets. |
| Verification | `.verify-logs/runs/20260706T182902406275Z-full-0f7e40a99a16/manifest.json` | Full profile recorded 30 checks, all passed. |
| Security verification | `.verify-logs/runs/20260706T183043122056Z-security-a5dc769ae0f2/manifest.json` | Security profile recorded one `secret-scan-history` check, passed. |
| Manual verification | `.verify-logs/runs/20260706T183051406806Z-manual-445b0a41ddb5/LAST_FAILURE.md` | Manual profile found `pyright-strict-ratchet` drift: 1,047 errors versus 889 allowed, delta `+158`. Other manual checks passed or were disabled. |

## Cost Impact

The loop reduced agent search cost qualitatively by replacing raw artifact
inspection with compact summaries and explicit next commands. The clearest
measured cost signal is negative: runtime waste still found avoidable heavy
profile overlap and generated artifact debris.

Token spend, API dollars, and chat narration volume were not captured, so this
study does not claim a quantified cost reduction.

## Quality Impact

Quality improved in two concrete ways:

- The debt scan confirmed the repository remained low debt after the merged
  roadmap slices.
- The manual verifier failure was precise enough to identify strict Pyright
  ratchet drift as a remaining technical-debt target rather than a broad
  quality failure.

Quality is not yet good enough for automated cheap-worker routing because the
latest failed check had only fallback repair facts. A worker can see the failure,
but the repo still needs structured parser coverage for that check family.

## Speed Impact

The loop gave faster next-action selection by pointing to specific files,
functions, and verifier checks. Runtime events recorded `test-intel
hypothesis-candidates` at about 64.5 seconds and the manual verifier command at
about 25.2 seconds.

End-to-end speed delta is unavailable because the baseline workflow did not
capture comparable timings and verifier manifests did not record per-check wall
clock durations.

## Model-Tier Routing Decision

The evidence does not yet support automatically routing easy tasks to cheaper
workers. It does support collecting more labeled examples for that decision:
the loop can identify low-risk documentation/test tasks, high-risk manual gate
failures, and specific escalation reasons.

Before cheaper-worker routing is safe, the repo needs more examples with:

- task difficulty labels;
- risk surface labels;
- context size;
- verification outcome;
- whether cheaper-worker output was accepted;
- whether escalation was required and why.

## Primitive Evaluation

- Task-broker primitives reduce conflict risk conceptually through locks and
  worktree planning, but this case study did not run parallel broker workers.
- MCP surface primitives make future command discovery easier, but this run did
  not measure MCP usage separately from local CLI usage.
- Context primitives reduced verification thrash by keeping failure expansion
  run-scoped and bounded.
- Runtime-event primitives exposed waste that raw logs would not summarize:
  heavy profile overlap, fresh-only verifier runs, and generated artifact
  debris.
- Adapter doctrine reduced adoption risk by keeping this loop inside repo-local
  contracts instead of introducing an external orchestration framework before
  local evidence justified one.

## Remaining Gaps

- Capture token, dollar, and chat narration metrics.
- Emit wait command runtime events so PR wait-poll counts become measurable.
- Emit verifier fingerprint reuse events so same-state duplicate verification
  becomes measurable.
- Add structured repair facts for `pyright-strict-ratchet`.
- Record per-check verifier durations in manifests.
- Grow the scoring example dataset before claiming model-tier routing safety.

## Agent Lesson

Use the ROI loop as a triage aid, not an autonomy proof. Let debt, runtime
events, repair-fact coverage, and test-intelligence output select the next
focused change, then require normal verification before merging.
<!-- docsync:object.end docs.case_studies_future_call_roi_loop.overview -->
