# Suggested Commands

Run from repository root.

- Bootstrap development tools: `just bootstrap`
- Diagnose setup/config/toolchain: `just doctor`
- Focused test: `.venv/bin/pytest tests/<area>/test_<name>.py -q`
- Fast verifier: `just vf`
- Precommit completion gate when trusted hooks are unavailable: `just vp`
- Broad local gate: `just v`
- CI-equivalent gate for diff/base-ref/workflow behavior: `just vc`
- Security profile: `just vs`
- Manual/slow profile: `just vm`
- Release-only packaging tests: `just release-check`
- Validate generated guidance: `just guidance-check`; regenerate only with `just guidance`
- Validate generated config reference: `just config-reference-check`; regenerate with `just config-reference`
- Validate an active cohesive change plan: `just change-plan-check`
- Long-running ownership: `just wg <run-id>`, `just wp <pr-number>`, `just wv <run-id>`
- Exact literal/file discovery stays with `rg` and `rg --files`; use Serena JetBrains tools for semantic symbols, references, implementations, hierarchy, inspections, and refactors.
