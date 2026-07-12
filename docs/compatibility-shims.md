# Compatibility Shim Inventory

This inventory maps forwarding modules to their canonical owners for immediate
cleanup during beta.

| Group | Forwarding paths | Owner/replacement | Current deletion rule |
| --- | --- | --- | --- |
| Archguard forwarding | `agent_maintainer.checks.tach_config`, `agent_maintainer.tach` | `archguard` | Migrate current repository callers, docs, and tests to the canonical owner, then delete the forwarding module in the same tested change. |
| Configuration facade | `agent_maintainer.config.metadata`, `agent_maintainer.core.config` | configuration packages | Migrate current repository callers, docs, and tests to the canonical owner, then delete the forwarding module in the same tested change. |
| Context extraction | `agent_maintainer.context.budget`, `agent_maintainer.context.compression.backends`, `agent_maintainer.context.compression.headroom`, `agent_maintainer.context.compression.models`, `agent_maintainer.context.estimate`, `agent_maintainer.context.failures`, `agent_maintainer.context.formatting`, `agent_maintainer.context.models`, `agent_maintainer.context.pack.fact_parsers`, `agent_maintainer.context.pack.fact_payloads`, `agent_maintainer.context.pack.lint_fact_parsers`, `agent_maintainer.context.pack.log_fact_parsers`, `agent_maintainer.context.pack.pytest_fact_parsers`, `agent_maintainer.context.pack.rendering`, `agent_maintainer.context.pack.sanitize`, `agent_maintainer.context.pack.typescript_fact_parsers`, `agent_maintainer.context.reading.diff`, `agent_maintainer.context.reading.diff_classify`, `agent_maintainer.context.reading.diff_git`, `agent_maintainer.context.reading.file_safety`, `agent_maintainer.context.reading.files`, `agent_maintainer.context.reading.logs`, `agent_maintainer.context.reading.python_outline` | `agent_context` | Migrate current repository callers, docs, and tests to the canonical owner, then delete the forwarding module in the same tested change. |
| Hook extraction | `agent_maintainer.hooks.adapters`, `agent_maintainer.hooks.merge`, `agent_maintainer.hooks.templates` | `agent_client_hooks` | Migrate current repository callers, docs, and tests to the canonical owner, then delete the forwarding module in the same tested change. |
| Repair-fact extraction | `agent_maintainer.ecosystems.typescript.diagnostics` | `agent_repair_facts` | Migrate current repository callers, docs, and tests to the canonical owner, then delete the forwarding module in the same tested change. |
| Run-artifact extraction | `agent_maintainer.verify.artifact_manifest`, `agent_maintainer.verify.git_state`, `agent_maintainer.verify.history`, `agent_maintainer.verify.pr_summary`, `agent_maintainer.verify.pr_summary_support`, `agent_maintainer.verify.timing` | `agent_run_artifacts` | Migrate current repository callers, docs, and tests to the canonical owner, then delete the forwarding module in the same tested change. |
| Wait extraction | `agent_maintainer.wait.models` | `agent_waits` | Migrate current repository callers, docs, and tests to the canonical owner, then delete the forwarding module in the same tested change. |

## Deletion rule

Compatibility is not a reason to retain a shim during beta. A forwarding
module can be deleted immediately when its current repository callers, docs,
and tests migrate to the canonical owner in the same tested change. No support
window, deprecation release, or earliest-removal version applies.
