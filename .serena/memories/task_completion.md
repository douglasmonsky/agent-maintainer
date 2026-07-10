# Task Completion Gates

- Inspect `git status --short --branch`, diff stat, and the actual diff; preserve unrelated/user changes and check for secrets or private data.
- Run the smallest focused tests while editing. Do not duplicate a trusted hook result for the same tree state.
- If trusted hooks are unavailable, run `just vp` before handoff.
- For a larger coherent change, run one broad profile: normally `just v`; use `just vc` when workflow, diff/base-ref, or CI-profile behavior changed. Run both only when their overlap is under test.
- Run `just vs` or `just vm` when those gates were changed, explicitly requested, or before release. Run `just release-check` for package/release work.
- After setup, toolchain, hook, initializer, or configuration changes, run `just doctor`.
- When Agent Maintainer config changes, regenerate and validate `AGENTS.agent-maintainer.md` with `just guidance`; when config-reference inputs change, regenerate and validate the reference.
- Architecture-policy changes require a current ADR and exact Tach validation. DocSync-facing changes require trace/currentness validation.
- Do not claim completion while a required check fails; read `.verify-logs/LAST_FAILURE.md` before expanding logs or changing code.
- Before staging, recheck status and stage explicit paths only. Use a focused Conventional Commit if committing is in scope.
