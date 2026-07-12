# Agent Maintainer 0.1.0b6 Qualification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce and validate complete local exact-commit evidence for one merged `0.1.0b6` candidate without publishing it.

**Architecture:** Qualify one clean `origin/main` SHA with the same five-manifest contract used by the publish workflow. Preserve the aggregate outside Git, then add a clearly labeled evidence-only documentation commit that names—but does not redefine—the qualified candidate SHA.

**Tech Stack:** Git, Agent Maintainer verifier profiles, pytest release tests, exact-commit release-evidence CLI, GitHub Actions/`gh` read-only inspection, Markdown release notes.

## Global Constraints

- Do not tag, publish to TestPyPI/PyPI, create a GitHub release, or dispatch the publish workflow.
- Do not run the Phase 176 real-turn smoke.
- Qualify only after every architecture-hardening PR is merged and `origin/main` is current.
- Every profile manifest must name the same clean full SHA and be less than 24 hours old.
- Keep generated manifests, distributions, coverage, and aggregate evidence outside Git.
- The follow-up evidence-doc commit is not itself the qualified release candidate.

---

### Task 1: Select a clean merged candidate SHA

**Files:**

- No repository files.
- Create outside Git: `/Users/Monsky/Documents/Codex/2026-07-11/release-evidence-b6/<sha>/`

**Interfaces:**

- Consumes: merged `origin/main` after roadmap/API, wait, attention, and Archguard chunks.
- Produces: immutable shell variables `CANDIDATE_SHA`, `EVIDENCE_ROOT`, and `PROFILE_DIR` for one run.

- [ ] **Step 1: Verify all implementation work is merged**

Run:

```bash
git fetch --prune origin
git status --short --branch
git log -1 --oneline origin/main
gh pr list --state open --json number,title,headRefName
```

Expected: no uncommitted files, no architecture-hardening PR remains open, and
`origin/main` contains every prior chunk.

- [ ] **Step 2: Start a clean qualification branch at exact main**

Run:

```bash
git switch -c chore/b6-qualification origin/main
git status --porcelain
```

Expected: the second command prints nothing.

- [ ] **Step 3: Create the external evidence directory**

Run:

```bash
CANDIDATE_SHA="$(git rev-parse HEAD)"
EVIDENCE_ROOT="/Users/Monsky/Documents/Codex/2026-07-11/release-evidence-b6/$CANDIDATE_SHA"
PROFILE_DIR="$EVIDENCE_ROOT/profiles"
test ! -e "$EVIDENCE_ROOT"
mkdir -p "$PROFILE_DIR"
printf '%s\n' "$CANDIDATE_SHA" > "$EVIDENCE_ROOT/candidate-sha.txt"
```

Expected: the `test` prevents overwriting a prior evidence run and the new
directory is outside the repository.

### Task 2: Run and aggregate the exact local release matrix

**Files:**

- Read: `.verify-logs/manifest.json` after each profile.
- Write outside Git: `$PROFILE_DIR/{full,ci,security,manual,release}.json`
- Write outside Git: `$EVIDENCE_ROOT/release-evidence.json`

**Interfaces:**

- Consumes: clean candidate SHA from Task 1.
- Produces: one validated aggregate matching `agent_run_artifacts.release_evidence.REQUIRED_PROFILES`.

- [ ] **Step 1: Run environment and precommit checks**

Run in separate terminal executions so output remains reviewable:

```bash
just doctor
AGENT_MAINTAINER_ALLOW_FOREGROUND_WAIT=1 just vp
```

Expected: doctor PASS and precommit manifest has no failed/unknown checks.
Precommit is a qualification prerequisite but is not one of the five aggregate
profiles.

- [ ] **Step 2: Record full and CI manifests**

Run:

```bash
CANDIDATE_SHA="$(git rev-parse HEAD)"
EVIDENCE_ROOT="/Users/Monsky/Documents/Codex/2026-07-11/release-evidence-b6/$CANDIDATE_SHA"
PROFILE_DIR="$EVIDENCE_ROOT/profiles"

AGENT_MAINTAINER_ALLOW_FOREGROUND_WAIT=1 \
  PYTHONPATH=src python3 -m agent_maintainer verify --profile full
cp .verify-logs/manifest.json "$PROFILE_DIR/full.json"

AGENT_MAINTAINER_ALLOW_FOREGROUND_WAIT=1 \
  PYTHONPATH=src python3 -m agent_maintainer verify \
    --profile ci --base-ref HEAD --compare-branch HEAD
cp .verify-logs/manifest.json "$PROFILE_DIR/ci.json"
```

Expected: both commands exit 0 and both copied manifests record
`git.sha == CANDIDATE_SHA`, `git.dirty == false`, and no failed/unknown check.

- [ ] **Step 3: Record security and manual manifests**

Run:

```bash
CANDIDATE_SHA="$(git rev-parse HEAD)"
EVIDENCE_ROOT="/Users/Monsky/Documents/Codex/2026-07-11/release-evidence-b6/$CANDIDATE_SHA"
PROFILE_DIR="$EVIDENCE_ROOT/profiles"

AGENT_MAINTAINER_ALLOW_FOREGROUND_WAIT=1 \
  PYTHONPATH=src python3 -m agent_maintainer verify --profile security
cp .verify-logs/manifest.json "$PROFILE_DIR/security.json"

AGENT_MAINTAINER_ALLOW_FOREGROUND_WAIT=1 \
  PYTHONPATH=src python3 -m agent_maintainer verify --profile manual
cp .verify-logs/manifest.json "$PROFILE_DIR/manual.json"
```

Expected: both commands exit 0 and both manifests satisfy the same clean-SHA
contract.

- [ ] **Step 4: Record the release-only package profile**

Run:

```bash
CANDIDATE_SHA="$(git rev-parse HEAD)"
EVIDENCE_ROOT="/Users/Monsky/Documents/Codex/2026-07-11/release-evidence-b6/$CANDIDATE_SHA"
PROFILE_DIR="$EVIDENCE_ROOT/profiles"

PYTHONPATH=src .venv/bin/python -m agent_maintainer.release_evidence record \
  --output "$PROFILE_DIR/release.json" \
  -- just release-check
```

Expected: `release profile recorded` with exit 0. The command builds wheel and
sdist in temporary directories, runs metadata checks, installs declared extras,
and smokes advertised console scripts without committing artifacts.

- [ ] **Step 5: Aggregate and validate all five profiles**

Run:

```bash
CANDIDATE_SHA="$(git rev-parse HEAD)"
EVIDENCE_ROOT="/Users/Monsky/Documents/Codex/2026-07-11/release-evidence-b6/$CANDIDATE_SHA"
PROFILE_DIR="$EVIDENCE_ROOT/profiles"

PYTHONPATH=src .venv/bin/python -m agent_maintainer.release_evidence aggregate \
  --expected-sha "$CANDIDATE_SHA" \
  --manifest "$PROFILE_DIR/full.json" \
  --manifest "$PROFILE_DIR/ci.json" \
  --manifest "$PROFILE_DIR/security.json" \
  --manifest "$PROFILE_DIR/manual.json" \
  --manifest "$PROFILE_DIR/release.json" \
  --output "$EVIDENCE_ROOT/release-evidence.json"

PYTHONPATH=src .venv/bin/python -m agent_maintainer.release_evidence validate \
  --expected-sha "$CANDIDATE_SHA" \
  --manifest "$EVIDENCE_ROOT/release-evidence.json"
```

Expected: `release evidence aggregated` for five profiles followed by `release
evidence valid` for the exact candidate SHA.

- [ ] **Step 6: Save a compact, non-sensitive local summary**

Run:

```bash
CANDIDATE_SHA="$(git rev-parse HEAD)"
EVIDENCE_ROOT="/Users/Monsky/Documents/Codex/2026-07-11/release-evidence-b6/$CANDIDATE_SHA"

jq '{commit, required_profiles, generated_at, expires_at}' \
  "$EVIDENCE_ROOT/release-evidence.json" \
  > "$EVIDENCE_ROOT/summary.json"
git status --porcelain
```

Expected: the summary contains the candidate SHA and five required profiles;
Git status remains empty.

### Task 3: Confirm hosted supported-Python evidence for the same SHA

**Files:**

- No repository files.
- Write outside Git: `$EVIDENCE_ROOT/hosted-main-run.json`

**Interfaces:**

- Consumes: GitHub Actions runs triggered by the final merge to `main`.
- Produces: read-only evidence that the supported Python matrix passed on `CANDIDATE_SHA`.

- [ ] **Step 1: Find the exact main workflow run**

Run:

```bash
CANDIDATE_SHA="$(git rev-parse HEAD)"
EVIDENCE_ROOT="/Users/Monsky/Documents/Codex/2026-07-11/release-evidence-b6/$CANDIDATE_SHA"

gh run list \
  --branch main \
  --workflow verify.yml \
  --commit "$CANDIDATE_SHA" \
  --limit 5 \
  --json databaseId,headSha,status,conclusion,url \
  > "$EVIDENCE_ROOT/hosted-main-run.json"
jq 'map(select(.headSha == $sha))' \
  --arg sha "$CANDIDATE_SHA" \
  "$EVIDENCE_ROOT/hosted-main-run.json"
```

Expected: exactly one relevant run with `status: completed` and
`conclusion: success`.

- [ ] **Step 2: Inspect the supported-Python jobs**

Resolve `RUN_ID` from that JSON and run:

```bash
CANDIDATE_SHA="$(git rev-parse HEAD)"
EVIDENCE_ROOT="/Users/Monsky/Documents/Codex/2026-07-11/release-evidence-b6/$CANDIDATE_SHA"
RUN_ID="$(jq -r --arg sha "$CANDIDATE_SHA" \
  'map(select(.headSha == $sha and .status == "completed" and .conclusion == "success")) | first | .databaseId // empty' \
  "$EVIDENCE_ROOT/hosted-main-run.json")"
test -n "$RUN_ID"
gh run view "$RUN_ID" --json jobs,url,headSha > "$EVIDENCE_ROOT/hosted-main-jobs.json"
jq '.jobs[] | {name, status, conclusion}' "$EVIDENCE_ROOT/hosted-main-jobs.json"
```

Expected: Python 3.11, 3.12, 3.13, and 3.14 artifact/install smoke jobs are
present and successful. If the exact main run is missing or failed, qualification
is blocked; do not substitute another SHA.

### Task 4: Record the qualified SHA in an evidence-only follow-up commit

**Files:**

- Modify: `tests/release/test_release_state.py`
- Modify: `docs/releases/0.1.0b6.md`

**Interfaces:**

- Consumes: validated local aggregate and exact hosted run from Tasks 2-3.
- Produces: a truthful in-repo pointer to the already qualified candidate SHA.

- [ ] **Step 1: Write the failing candidate-evidence test**

Add:

```python
def test_release_candidate_notes_record_local_qualification() -> None:
    """Candidate notes identify qualified source without claiming publication."""

    candidate = (REPO_ROOT / "docs" / "releases" / "0.1.0b6.md").read_text(
        encoding="utf-8"
    )

    assert "## Local Qualification Evidence" in candidate
    assert re.search(r"Qualified candidate commit: `[0-9a-f]{40}`", candidate)
    assert "Five-profile aggregate: `validated`" in candidate
    assert "Publication: `not authorized`" in candidate
    assert "Real-turn smoke: `not authorized`" in candidate
    assert "evidence-only follow-up commit" in candidate
```

Add `import re` if it is not already present.

- [ ] **Step 2: Run the test to verify RED**

Run: `AGENT_MAINTAINER_RUN_RELEASE_TESTS=1 PYTHONPATH=src .venv/bin/pytest tests/release/test_release_state.py::test_release_candidate_notes_record_local_qualification -q`

Expected: FAIL because the qualification section is absent.

- [ ] **Step 3: Add the truthful evidence section**

Append `## Local Qualification Evidence` to the candidate notes with:

```markdown
- Qualified candidate commit: `<CANDIDATE_SHA>`
- Local profiles: `precommit`, `full`, `ci`, `security`, `manual`, and `release` passed
- Five-profile aggregate: `validated`
- Hosted supported-Python matrix: `<HOSTED_RUN_URL>` passed for Python 3.11-3.14
- Publication: `not authorized`
- Real-turn smoke: `not authorized`

This section is an evidence-only follow-up commit. The immutable candidate is
the qualified SHA above; this documentation commit does not redefine it.
```

Replace the angle-bracket values with the actual SHA and exact hosted run URL.
Keep `Status: unpublished` and do not add tag, package-index workflow, artifact
filename, or publication digest claims.

- [ ] **Step 4: Verify docs and commit separately from the candidate**

Run:

```bash
AGENT_MAINTAINER_RUN_RELEASE_TESTS=1 PYTHONPATH=src .venv/bin/pytest \
  tests/release/test_release_state.py \
  tests/packaging/test_public_docs.py \
  tests/docs/test_markdown_links.py -q
git diff --check
```

Expected: PASS.

```bash
git add -- tests/release/test_release_state.py docs/releases/0.1.0b6.md
git commit -m "docs: record b6 qualification evidence"
```

Do not rerun or reinterpret qualification against this evidence-only commit.

### Task 5: Prepare the final handoff

**Files:**

- No additional repository files.

**Interfaces:**

- Consumes: candidate SHA, evidence path, hosted run URL, and evidence-only commit.
- Produces: a clean future-run handoff with no implied publication authorization.

- [ ] **Step 1: Perform final repository review**

Run:

```bash
git status --short --branch
git log -5 --oneline --decorate
git diff origin/main...HEAD --stat
git diff origin/main...HEAD --check
```

Expected: only the intentional evidence-only docs/test commit differs from the
qualified main SHA and the worktree is clean.

- [ ] **Step 2: Report exact evidence and remaining gates**

The handoff must name:

```text
qualified candidate SHA
evidence-only commit SHA
external aggregate path
hosted main run URL
local profiles and release check result
publication/tag/TestPyPI/PyPI: not performed
Phase 176 real-turn smoke: not performed
```

Do not publish or request release credentials as part of this plan.
