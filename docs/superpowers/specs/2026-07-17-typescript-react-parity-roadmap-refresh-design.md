# TypeScript/React Parity Roadmap Refresh Design

Date: 2026-07-17

Status: approved for roadmap implementation

## Context

Agent Maintainer already has an experimental, explicit-command
TypeScript/JavaScript provider. Phases 165 through 175 added React-shaped
reviewability evidence, package-manager and workspace evidence, structured test
and coverage facts, doctor and setup-advisor guidance, and explicit
workspace-owned commands.

Commit `386c8c1` on `origin/codex/react-typescript-parity-roadmap` contains a
useful parity map and sequenced implementation ideas, but that branch predates
the current `main`. It also assigns the TypeScript roadmap to Phase 176, which
now belongs to the completed Codex terminal-rewake hardening phase. Merging or
rebasing that branch would preserve stale roadmap state and create avoidable
integration work.

## Decision

Reconstruct the useful parity-roadmap content on a fresh branch from current
`main`. Record the roadmap as Phase 177 and treat the old branch as reference
material only: do not merge it, rebase it, rewrite it, or cherry-pick its commit
unchanged.

Phase 177 is documentation-only. Subsequent TypeScript parity slices will use
small, independently verified pull requests to `main`. There will be no
long-lived TypeScript integration branch. The provider remains experimental and
advisory unless a later, evidence-backed promotion assessment explicitly
changes that status.

## Goals

- Restore a current TypeScript/React parity roadmap without reviving stale
  branch state.
- Map Python-provider capabilities to realistic TypeScript/React candidates,
  including places where no direct equivalent exists.
- Sequence bounded implementation slices with explicit safety and promotion
  gates.
- Make advisory package-manager and workspace detection the first
  implementation slice, Phase 178.
- Keep command ownership explicit and prevent repository evidence from becoming
  implicit command execution.

## Non-Goals

- No provider runtime, configuration schema, detector, adapter, or CI behavior
  changes in Phase 177.
- No inferred or generated package-manager commands.
- No dependency additions.
- No default blocking TypeScript/React gate.
- No provider promotion.
- No new ecosystem work before the TypeScript/React promotion assessment.
- No attempt to force Python-only documentation or quality rules onto React
  application code when the ecosystem lacks an honest equivalent.

## Phase 177 Documentation Shape

Phase 177 will add or update the following roadmap surfaces:

- `docs/roadmap/typescript-react-parity-roadmap.md`: durable parity map,
  implementation sequence, evidence requirements, and promotion criteria.
- `docs/roadmap/phases/phase-177-typescript-react-parity-roadmap.md`: bounded
  phase goal, scope, non-goals, acceptance criteria, and verification commands.
- `docs/ROADMAP.md`: compact active-track entry after the completed phases 165
  through 175 and the unrelated Phase 176 rewake work.
- `docs/roadmap/full-roadmap-blueprint.md`: phase index entry.
- `docs/provider-status.md`: current experimental status and the next evidence
  milestone without overstating shipped support.

The roadmap will preserve the useful capability map from `386c8c1`, covering
formatting, linting, type checking, tests, changed-line coverage, architecture,
dead code, dependency integrity and security, secrets, complexity, mutation,
SBOM and licenses, React hooks, accessibility, Testing Library, and generated
files. Each row will distinguish a strong replacement, a partial replacement,
an ecosystem-neutral capability, or no honest equivalent.

## Implementation Sequence

After Phase 177 lands, parity work proceeds through focused pull requests:

1. Phase 178: advisory package-manager and workspace detection.
2. Knip unused-code and dependency facts.
3. OSV and package-manager audit facts.
4. Dependency-cruiser architecture-boundary facts, with Nx support only for
   repositories that already declare Nx boundaries.
5. LCOV changed-line coverage facts.
6. React hooks, JSX accessibility, and Testing Library lint recommendations.
7. Explicit generated-file and framework policy evidence.
8. StrykerJS mutation-report facts with a runtime-cost guard.
9. TypeScript/React blocking-gate promotion assessment.

The durable roadmap may assign phase numbers beyond 178 when each slice is
planned. Phase 177 will not reserve numbers for underspecified work or create
empty phase files.

## Phase 178 Boundary

Phase 178 observes repository evidence and reports advisory facts. It does not
execute or synthesize commands.

### Inputs

- Root `package.json` metadata, including the `packageManager` field and script
  names.
- Corepack-related declarations that are present in repository-owned metadata.
- Recognized lockfiles for npm, pnpm, Yarn, and Bun.
- Root workspace declarations and recognized workspace manifest files.
- Existing explicit Agent Maintainer workspace configuration.

### Processing

The detector will normalize evidence into typed facts that preserve provenance:
which file and field supplied each observation. Multiple lockfiles, conflicting
package-manager declarations, malformed metadata, and unsupported workspace
shapes remain visible as ambiguity rather than being resolved by preference or
guessing.

### Consumers

Doctor and setup-advisor may use the facts to explain likely setup choices and
the exact configuration the user must review. The TypeScript provider executor
continues to use only explicit root or workspace command arrays from Agent
Maintainer configuration.

### Forbidden Flow

Repository evidence must never flow directly into subprocess arguments. A
detected package manager, workspace, or script name cannot create, modify, or
run a TypeScript check without explicit reviewed configuration.

## Failure And Ambiguity Behavior

- Malformed `package.json` or workspace metadata produces bounded advisory
  evidence with the source path and a concise repair hint.
- Conflicting lockfiles or `packageManager` declarations are reported as
  ambiguous; Agent Maintainer does not select a winner.
- Unsupported package managers or workspace layouts are named without falling
  back to npm or root-only execution.
- Missing optional evidence remains an advisory absence, not a provider error.
- Existing explicit commands retain their current behavior even when detection
  evidence is incomplete or contradictory.

## Evidence And Promotion Policy

Every future blocking candidate requires temporary-Git fixture coverage and at
least two external real-repository comparisons. Evidence must measure noise,
repair usefulness, runtime cost where relevant, and behavior across React,
Vite, Next.js, and workspace layouts. No advisory becomes blocking merely
because an adapter or parser exists.

Python-provider behavior and architecture ownership must remain unchanged or
improve. Shared abstractions are justified only when they preserve the stronger
existing Python path and express a real cross-ecosystem contract.

## Testing And Verification

Phase 177 verification will include:

- roadmap and first-touch documentation tests;
- provider-status wording coverage where existing tests require it;
- DocSync checks and trace updates when linked evidence changes;
- Markdown linting and `git diff --check`;
- one broad repository verifier profile before the pull request is opened;
- the complete required GitHub pull-request checks before merge.

Phase 178 will be designed and implemented separately with test-driven coverage
for each accepted evidence shape, ambiguity case, and forbidden execution path.

## Rollback

Phase 177 is documentation-only and can be reverted as one focused commit
without affecting runtime behavior. Later implementation slices remain
independently revertible because each lands through its own pull request and
does not depend on a long-lived integration branch.

## Alternatives Considered

### Merge the stale roadmap branch unchanged

Rejected because it is based on old `main`, collides with the completed Phase
176, and carries obsolete roadmap state.

### Skip roadmap recovery and implement detection immediately

Rejected because the parity sequence, promotion bar, and non-equivalent Python
capabilities would remain implicit, making scope drift more likely.

### Continue on a long-lived integration branch

Rejected because experimental/advisory feature flags already isolate incomplete
capabilities. Focused pull requests to `main` provide earlier verification,
smaller reviews, simpler rollback, and less merge debt.
