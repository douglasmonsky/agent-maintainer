# Subsystem Stability

These labels describe how Agent Maintainer's current subsystems are intended to
be used. They are documentation metadata, not a runtime registry or a promise
of pre-1.0 cross-version compatibility.

- `core`: maintained as part of the default owner workflow. Changes must keep
  the documented workflow coherent and migration-free within the current tree.
- `optional`: maintained, tested functionality that is not required for the
  default workflow and may require an extra tool, profile, or explicit command.
- `experimental`: exploratory integration surface. It may change or be removed
  without a compatibility shim.

## Subsystem Map

| Subsystem | Stability | Scope |
| --- | --- | --- |
| Setup and configuration | `core` | Initialization, bootstrap, doctor, guidance, setup skill, and managed hooks. |
| Verification and repair facts | `core` | Profiles, runners, fingerprints, manifests, summaries, and repair guidance. |
| Context, ratchets, and assessment | `core` | Bounded context, legacy baselines, debt signals, and repair planning. |
| Test intelligence | `core` | Affected-test selection and deeper opt-in testing recommendations. |
| Archguard | `core` | Architecture maps, impact analysis, Tach policy, and decision checks. |
| Wait orchestration | `core` | Quiet GitHub, PR, and verifier waits plus durable local wait state. |
| Attention, events, reports, and scoring | `optional` | Owner-invoked local diagnostics and datasets. |
| DocSync | `optional` | Trace-based documentation checks for repositories that adopt its contract. |
| Deep security and mutation profiles | `optional` | Explicit slower gates outside the normal commit loop. |
| MCP surface | `experimental` | Optional typed local tool server for agent integrations. |
| TypeScript provider | `experimental` | Early multi-language provider and structured-diagnostic support. |
| Terminal rewake backends | `experimental` | Client-specific wake delivery layered over stable quiet waits. |

The `agent-maintainer wait` command is core because quiet waits and durable
state are supported owner workflows. Its terminal rewake backends remain
experimental independently of the command label.

## Public Command Labels

Every installed console script and every registered `agent-maintainer`
top-level command has exactly one label here.

| Command | Stability | Owner-facing purpose |
| --- | --- | --- |
| `agent-maintainer assess` | `core` | Recommend setup and report maintenance signals. |
| `agent-maintainer bootstrap` | `core` | Prepare the development checkout. |
| `agent-maintainer change-plan` | `core` | Manage cohesive large-change authority. |
| `agent-maintainer context` | `core` | Read bounded repair context. |
| `agent-maintainer doctor` | `core` | Diagnose setup and integration drift. |
| `agent-maintainer guidance` | `core` | Generate or validate repository agent guidance. |
| `agent-maintainer hooks` | `core` | Manage agent-client hooks. |
| `agent-maintainer init` | `core` | Initialize Agent Maintainer in a repository. |
| `agent-maintainer install` | `core` | Install project-local verification hooks. |
| `agent-maintainer ratchet` | `core` | Inspect legacy improvement baselines. |
| `agent-maintainer repair-plan` | `core` | Turn diagnostics into bounded repair guidance. |
| `agent-maintainer skill` | `core` | Install and inspect the new-repository setup skill. |
| `agent-maintainer test-intel` | `core` | Select and run relevant tests. |
| `agent-maintainer verify` | `core` | Run configured verification profiles. |
| `agent-maintainer wait` | `core` | Run quiet waits and manage durable wait state. |
| `archguard` | `core` | Inspect and enforce architecture policy. |
| `agent-maintainer attention` | `optional` | Build local file-attention ledgers. |
| `agent-maintainer events` | `optional` | Summarize local runtime events. |
| `agent-maintainer report` | `optional` | Render diagnostic reports. |
| `agent-maintainer scoring` | `optional` | Manage local scoring examples. |
| `docsync` | `optional` | Check adopted documentation trace contracts. |
| `agent-maintainer mcp` | `experimental` | Run the optional typed MCP surface. |

## Change Rules

- Core changes preserve the current documented owner workflow and require
  direct tests for affected commands.
- Optional changes remain fail-closed when explicitly enabled but must not
  become a hidden dependency of the default workflow.
- Experimental changes remain isolated behind explicit commands or settings.
- Moving a subsystem between labels requires updating this document and its
  command-coverage test in the same change.
