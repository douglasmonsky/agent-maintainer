# Dual-Client Agent Maintainer Setup Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship one Agent Maintainer setup skill that is safely installed for Codex and Claude Code and offers verified Agent Maintainer configuration during every new-repository setup.

**Architecture:** Package one client-neutral `SKILL.md` plus Codex UI metadata inside `agent_maintainer.skill`. A small ownership-aware lifecycle copies that bundle into each client's personal skill directory, hashes managed files, and refuses modified content; a top-level `agent-maintainer skill` command exposes install, status, and uninstall. The skill orchestrates the existing setup advisor, initializer, doctor, and verifier rather than duplicating their logic.

**Tech Stack:** Python 3.11+, `argparse`, dataclasses, `StrEnum`, `hashlib`, `importlib.metadata`, `importlib.resources`, JSON, `pathlib`, staged directory replacement, pytest, Setuptools package data, Markdown/YAML skill resources, Tach, and DocSync.

## Global Constraints

- Ask once after the scaffold exists and before the initial commit; declining performs no writes and suppresses another offer during that task.
- Present exactly three explained modes: Recommended, Guided, and Full control.
- Recommended defaults to track `agent` and preset `strict-new-repo` when evidence is incomplete.
- Install an exact Agent Maintainer version using the repository's development/tool convention.
- Use one shared `SKILL.md`; do not add an MCP server or compatibility shim.
- Install to `~/.codex/skills/agent-maintainer-setup/` and `~/.claude/skills/agent-maintainer-setup/`.
- Update or uninstall only hash-verified managed content; preserve unrelated and modified files.
- Leave global instruction files untouched unless fresh-session testing proves metadata routing insufficient.
- Do not lower verification thresholds or suppress failures.

## File Map

- `src/agent_maintainer/skill/models.py`: immutable bundle, manifest, status, and result types.
- `src/agent_maintainer/skill/resources.py`: packaged skill loader and distribution version.
- `src/agent_maintainer/skill/lifecycle.py`: client paths and ownership-safe lifecycle.
- `src/agent_maintainer/skill/cli.py`: install, status, and uninstall command surface.
- `src/agent_maintainer/skill/resources/agent-maintainer-setup/`: shared skill and Codex metadata.
- `tests/skill/`: resource, lifecycle, and CLI regressions.
- `docs/agent-maintainer-setup-skill.md`: public behavior and installation contract.

---

### Task 1: Package the portable skill resource

**Files:**

- Create: `src/agent_maintainer/skill/__init__.py`
- Create: `src/agent_maintainer/skill/models.py`
- Create: `src/agent_maintainer/skill/resources.py`
- Create: `src/agent_maintainer/skill/resources/agent-maintainer-setup/SKILL.md`
- Create: `src/agent_maintainer/skill/resources/agent-maintainer-setup/agents/openai.yaml`
- Create: `tests/skill/test_resources.py`
- Create: `tests/skill/test_interaction_contract.py`
- Modify: `pyproject.toml`
- Modify: `tests/packaging/test_package_metadata.py`

**Interfaces:**

- Consumes: installed distribution metadata for `agent-maintainer`.
- Produces: `SkillFile(relative_path: str, content: str, digest: str)`, `SkillBundle(name: str, package_version: str, files: tuple[SkillFile, ...])`, and `load_bundle() -> SkillBundle`.

- [ ] **Step 1: Write the failing portable-resource tests**

```python
def test_shared_skill_has_portable_frontmatter_and_setup_modes() -> None:
    bundle = resources.load_bundle()
    skill = next(item for item in bundle.files if item.relative_path == "SKILL.md")
    assert bundle.name == "agent-maintainer-setup"
    assert skill.content.startswith("---\nname: agent-maintainer-setup\ndescription: ")
    assert "disable-model-invocation" not in skill.content
    assert "creating, scaffolding, bootstrapping, or initializing" in skill.content
    assert "Set up Agent Maintainer for this repository?" in skill.content
    assert skill.content.count("**Recommended**") == 1
    assert skill.content.count("**Guided**") == 1
    assert skill.content.count("**Full control**") == 1
    assert "before the initial commit" in skill.content
    assert "Do not add an MCP server" in skill.content
```

Also parse `agents/openai.yaml` with `yaml.safe_load` and assert the exact
`interface` mapping contains the display name, 25-64 character short
description, and a default prompt naming `$agent-maintainer-setup`, with no
other top-level keys.

Create `test_interaction_contract.py` with one phrase matrix covering each
approved scenario:

```python
SCENARIOS = {
    "decline": ("make no Agent Maintainer changes", "do not ask again"),
    "recommended_python": ("track `agent`", "preset `strict-new-repo`"),
    "typescript": ("Do not guess", "explicit TypeScript command"),
    "escalation": ("continue in Guided or Full control",),
    "guided": ("Ask only questions", "materially affect this repository"),
    "full_control": ("every supported", "before writing repository files"),
    "completion": ("Merge", "agent-maintainer doctor", "--profile precommit"),
}
```

Load the shared skill and assert every phrase for every scenario. This is the
deterministic interaction contract; live clients remain responsible for model
behavior.

- [ ] **Step 2: Run the resource tests and observe RED**

Run: `PYTHONPATH=src .venv/bin/pytest tests/skill/test_resources.py -q`

Expected: collection fails because `agent_maintainer.skill` does not exist.

- [ ] **Step 3: Add immutable models and the resource loader**

```python
@dataclass(frozen=True)
class SkillFile:
    relative_path: str
    content: str
    digest: str


@dataclass(frozen=True)
class SkillBundle:
    name: str
    package_version: str
    files: tuple[SkillFile, ...]
```

```python
SKILL_NAME: Final = "agent-maintainer-setup"
RESOURCE_PATHS: Final = ("SKILL.md", "agents/openai.yaml")


def load_bundle() -> SkillBundle:
    root = resources.files("agent_maintainer.skill") / "resources" / SKILL_NAME
    files = tuple(_load_file(root, path) for path in RESOURCE_PATHS)
    return SkillBundle(SKILL_NAME, metadata.version("agent-maintainer"), files)
```

`_load_file` reads UTF-8 content and computes its SHA-256 hex digest.

- [ ] **Step 4: Write the complete shared skill and Codex metadata**

Use only `name` and `description` frontmatter. Include the exact consent prompt and the three approved descriptions, then specify Recommended defaults, Guided material questions, Full control's complete questionnaire, exact dependency pinning, advisor/dry-run/init/config-merge/guidance/doctor/precommit flow, conflict escalation, no-write decline, and final reporting. For repositories without a Python dependency convention, name `.agent-maintainer/tool-requirements.txt` and the ignored `.agent-maintainer/venv/`, and require Guided consent before creating them. End with `Do not add an MCP server or compatibility shim.` Keep the resource below 220 lines.

Generate `agents/openai.yaml` with this exact command rather than writing
assignment syntax into the YAML file:

```bash
python /Users/Monsky/.codex/skills/.system/skill-creator/scripts/generate_openai_yaml.py \
  src/agent_maintainer/skill/resources/agent-maintainer-setup \
  --interface 'display_name=Agent Maintainer Setup' \
  --interface 'short_description=Configure new repositories with Agent Maintainer' \
  --interface 'default_prompt=Use $agent-maintainer-setup when creating this repository and offer the approved setup modes before its initial commit.'
```

- [ ] **Step 5: Configure exact package data**

```toml
[tool.setuptools.package-data]
"agent_maintainer.skill" = [
  "resources/agent-maintainer-setup/SKILL.md",
  "resources/agent-maintainer-setup/agents/openai.yaml",
]
```

Extend the package metadata test to assert those exact entries.

- [ ] **Step 6: Run GREEN checks**

```bash
PYTHONPATH=src .venv/bin/pytest tests/skill/test_resources.py tests/skill/test_interaction_contract.py tests/packaging/test_package_metadata.py -q
python /Users/Monsky/.codex/skills/.system/skill-creator/scripts/quick_validate.py src/agent_maintainer/skill/resources/agent-maintainer-setup
PYTHONPATH=src .venv/bin/ruff check src/agent_maintainer/skill tests/skill/test_resources.py
PYTHONPATH=src .venv/bin/ruff format --check src/agent_maintainer/skill tests/skill/test_resources.py
```

Expected: all pass.

- [ ] **Step 7: Commit**

Stage only Task 1 files, including `test_interaction_contract.py`, and commit
`feat: package agent maintainer setup skill`.

### Task 2: Implement ownership-safe dual-client lifecycle

**Files:**

- Modify: `src/agent_maintainer/skill/models.py`
- Create: `src/agent_maintainer/skill/lifecycle.py`
- Create: `tests/skill/test_lifecycle.py`

**Interfaces:**

- Consumes: `load_bundle() -> SkillBundle`.
- Produces: `SkillState`, `SkillStatus`, `SkillOwnershipError`, `status(home, client)`, `install(home, clients)`, and `uninstall(home, clients)`.

- [ ] **Step 1: Write failing lifecycle tests**

```python
def test_install_status_and_uninstall_both_clients(tmp_path: Path) -> None:
    assert tuple(lifecycle.status(tmp_path, c).state for c in CLIENTS) == (
        SkillState.MISSING,
        SkillState.MISSING,
    )
    installed = lifecycle.install(tmp_path, CLIENTS)
    assert all(item.state is SkillState.CURRENT for item in installed)
    assert lifecycle.install(tmp_path, CLIENTS) == installed
    removed = lifecycle.uninstall(tmp_path, CLIENTS)
    assert all(item.state is SkillState.MISSING for item in removed)


def test_modified_managed_file_blocks_update_and_uninstall(tmp_path: Path) -> None:
    lifecycle.install(tmp_path, ("codex",))
    skill = lifecycle.client_destination(tmp_path, "codex") / "SKILL.md"
    skill.write_text("user content\n", encoding="utf-8")
    assert lifecycle.status(tmp_path, "codex").state is SkillState.LOCALLY_MODIFIED
    with pytest.raises(SkillOwnershipError, match="locally modified"):
        lifecycle.install(tmp_path, ("codex",))
    with pytest.raises(SkillOwnershipError, match="locally modified"):
        lifecycle.uninstall(tmp_path, ("codex",))
    assert skill.read_text(encoding="utf-8") == "user content\n"
```

Add cases for stale update, unrelated-file preservation, unowned destination, malformed manifest, missing managed file, wrong client, replacement rollback, deterministic JSON, and directory pruning.

- [ ] **Step 2: Run lifecycle tests and observe RED**

Run: `PYTHONPATH=src .venv/bin/pytest tests/skill/test_lifecycle.py -q`

Expected: lifecycle interfaces are absent.

- [ ] **Step 3: Add state and manifest models**

```python
class SkillState(StrEnum):
    MISSING = "missing"
    CURRENT = "current"
    STALE = "stale"
    LOCALLY_MODIFIED = "locally-modified"


@dataclass(frozen=True)
class SkillManifest:
    schema_version: int
    skill: str
    client: str
    package_version: str
    files: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class SkillStatus:
    client: str
    destination: Path
    state: SkillState
    package_version: str
    installed_version: str | None = None
    detail: str = ""
```

- [ ] **Step 4: Implement classification and staged replacement**

Use:

```python
CLIENTS: Final = ("codex", "claude-code")
MANIFEST_NAME: Final = ".agent-maintainer-skill.json"
SCHEMA_VERSION: Final = 1
CLIENT_PATHS: Final = {
    "codex": Path(".codex/skills/agent-maintainer-setup"),
    "claude-code": Path(".claude/skills/agent-maintainer-setup"),
}
```

Classify absent as missing; invalid or absent manifests, missing files, and digest mismatches as locally modified; hash-verified content with a different packaged version or digest as stale; exact matches as current.

For mutation, copy the destination to a temporary sibling, apply all changes there, write sorted/indented manifest JSON, rename the old tree to a unique backup, and replace it with the staged tree. Restore the backup if replacement fails; delete it only after success.

- [ ] **Step 5: Implement install and uninstall**

`install` must no-op on current, update stale, create missing, and raise before mutation on locally modified. `uninstall` must no-op on missing, require hash-verified current/stale state, remove only manifest-listed files and the manifest, prune empty managed parents, and preserve unrelated files.

- [ ] **Step 6: Run lifecycle GREEN checks**

```bash
PYTHONPATH=src .venv/bin/pytest tests/skill/test_lifecycle.py -q
PYTHONPATH=src .venv/bin/ruff check src/agent_maintainer/skill tests/skill
PYTHONPATH=src .venv/bin/ruff format --check src/agent_maintainer/skill tests/skill
PYTHONPATH=src .venv/bin/python -m agent_maintainer.runners.pyright
```

Expected: tests pass and Pyright reports zero diagnostics.

- [ ] **Step 7: Commit**

Stage only Task 2 files and commit `feat: manage dual-client setup skill`.

### Task 3: Expose the public CLI and architecture contract

**Files:**

- Create: `src/agent_maintainer/skill/cli.py`
- Create: `src/agent_maintainer/skill/tach.domain.toml`
- Create: `tests/skill/test_cli.py`
- Modify: `src/agent_maintainer/cli.py`
- Modify: `tach.toml`
- Create: `docs/architecture/decisions/2026-07-13-dual-client-setup-skill.md`
- Modify: `tests/packaging/test_public_governance.py`

**Interfaces:**

- Consumes: lifecycle functions, `CLIENTS`, and `SkillOwnershipError`.
- Produces: `agent-maintainer skill install|status|uninstall` with repeatable `--client`.

- [ ] **Step 1: Write failing CLI tests**

```python
def test_skill_cli_forwards_repeatable_clients(tmp_path: Path, monkeypatch, capsys) -> None:
    calls = []
    monkeypatch.setattr(cli, "user_home", lambda: tmp_path)
    monkeypatch.setattr(
        cli.lifecycle,
        "install",
        lambda home, clients: calls.append((home, clients)) or current_statuses(home, clients),
    )
    assert cli.main(["install", "--client", "codex", "--client", "claude-code"]) == 0
    assert calls == [(tmp_path, ("codex", "claude-code"))]
    assert "codex: current" in capsys.readouterr().out
```

Add real top-level subprocess tests outside a Git repo, mutation-client requirement, status defaulting to both, parser rejection before mutation, bounded ownership error, and stable output for all states.

- [ ] **Step 2: Run CLI tests and observe RED**

Run: `PYTHONPATH=src .venv/bin/pytest tests/skill/test_cli.py -q`

Expected: skill CLI and routing are absent.

- [ ] **Step 3: Implement parser and rendering**

```python
def _add_clients(parser: argparse.ArgumentParser, *, required: bool) -> None:
    parser.add_argument(
        "--client",
        action="append",
        choices=lifecycle.CLIENTS,
        required=required,
        dest="clients",
    )
```

Install/uninstall require at least one client. Status defaults to both. Catch only `SkillOwnershipError`, print its message to stderr, and return one.

- [ ] **Step 4: Register the global command**

Add `skill` under stable workflows, add it to `command_handlers`, add a dual-client example, and implement an undecorated lazy `skill_command`. Do not apply repository config preflight because this command manages personal client state and must work outside Git repositories.

- [ ] **Step 5: Add Tach policy and ADR**

The skill domain permits `cli -> lifecycle`, `lifecycle -> models, resources`, and `resources -> models`. Add `agent_maintainer.skill.cli` to `agent_maintainer.cli`'s exact root dependencies. The ADR records the personal-skill boundary, rejects coupling to hook mutations and MCP, and keeps other domains from depending on lifecycle internals.

- [ ] **Step 6: Run CLI and architecture GREEN checks**

```bash
PYTHONPATH=src .venv/bin/pytest tests/skill/test_cli.py tests/packaging/test_public_governance.py -q
PYTHONPATH=src .venv/bin/python -m archguard tach-config --strict-root-module
PYTHONPATH=src .venv/bin/tach check --exact
PYTHONPATH=src .venv/bin/ruff check src/agent_maintainer/cli.py src/agent_maintainer/skill tests/skill
PYTHONPATH=src .venv/bin/ruff format --check src/agent_maintainer/cli.py src/agent_maintainer/skill tests/skill
PYTHONPATH=src .venv/bin/python -m agent_maintainer.runners.pyright
```

Expected: all pass with zero Pyright diagnostics.

- [ ] **Step 7: Commit**

Stage only Task 3 files and commit `feat: expose setup skill lifecycle`.

### Task 4: Document, package-smoke, and forward-test both clients

**Files:**

- Create: `docs/agent-maintainer-setup-skill.md`
- Modify: `README.md`
- Modify: `docs/quick-start.md`
- Modify: `.docsync/trace.yml`
- Modify: `tests/docs/test_first_touch_docs.py`
- Modify: `tests/docsync/test_public_doc_trace.py`
- Modify: `tests/packaging/test_onboarding_smoke.py`

**Interfaces:**

- Consumes: public CLI and packaged skill.
- Produces: public onboarding, DocSync evidence, artifact proof, and Codex/Claude trigger evidence.

- [ ] **Step 1: Write failing docs and package-smoke tests**

Require `docs/agent-maintainer-setup-skill.md` to contain the dual-client install command, all three mode names, `before the initial commit`, and `does not add an MCP server`. Add its document/object/claim IDs to DocSync tests. Extend clean wheel smoke to assert both resource files exist and `agent-maintainer skill --help` succeeds.

- [ ] **Step 2: Run tests and observe RED**

```bash
PYTHONPATH=src .venv/bin/pytest tests/docs/test_first_touch_docs.py tests/docsync/test_public_doc_trace.py tests/packaging/test_onboarding_smoke.py -q
```

Expected: absent docs, trace, and artifact assertions fail.

- [ ] **Step 3: Write docs and trace**

Document exact installation, status, trigger timing, approved mode descriptions, exact-version repository adoption, reinstall updates, modified-file refusal, safe uninstall, and the no-MCP boundary. Add `docs.agent_maintainer_setup_skill`, its `.overview` object, `claim.docs.agent_maintainer_setup_dual_client`, and evidence pointing to resource/lifecycle tests. Add matching DocSync markers.

- [ ] **Step 4: Run focused GREEN checks and artifact build**

```bash
PYTHONPATH=src .venv/bin/pytest tests/skill tests/docs/test_first_touch_docs.py tests/docsync/test_public_doc_trace.py tests/packaging/test_package_metadata.py tests/packaging/test_onboarding_smoke.py -q
markdownlint-cli2 README.md docs/quick-start.md docs/agent-maintainer-setup-skill.md docs/architecture/decisions/2026-07-13-dual-client-setup-skill.md docs/superpowers/specs/2026-07-13-dual-client-setup-skill-design.md docs/superpowers/plans/2026-07-13-dual-client-setup-skill.md
PYTHONPATH=src .venv/bin/python -m docsync check
.venv/bin/python -m build
```

Inspect wheel and sdist for both skill resources.

- [ ] **Step 5: Install the development skill for both clients**

```bash
PYTHONPATH=src .venv/bin/python -m agent_maintainer skill status
PYTHONPATH=src .venv/bin/python -m agent_maintainer skill install --client codex --client claude-code
PYTHONPATH=src .venv/bin/python -m agent_maintainer skill status
```

Expected: both current. Stop on locally modified state; do not overwrite.

- [ ] **Step 6: Run fresh-session trigger tests**

Create and preserve isolated scratch repositories under:

```text
/Users/Monsky/Developer/Codex/agent-maintainer-skill-forward-tests/2026-07-13/codex
/Users/Monsky/Developer/Codex/agent-maintainer-skill-forward-tests/2026-07-13/claude
```

Use this prompt only for the first turn:

```text
Create a minimal Python package repository here, initialize Git, add a README and one tested function, and prepare the initial commit. Stop whenever you need a user decision.
```

For Codex, run a fresh persisted `codex exec --json --skip-git-repo-check
-C <codex-scratch> -s workspace-write` process, retain only the
`thread.started` identifier in shell memory, and reduce the event stream to a
boolean indicating whether the exact consent prompt appeared. Resume that
thread with `codex exec resume <thread-id> --json "Yes"` and reduce its events
to booleans for all three exact descriptions. Do not write raw JSONL or model
messages to disk.

For Claude Code, first require `command -v claude` and record `claude
--version`. Run from the Claude scratch root with `claude -p --output-format
stream-json --verbose --permission-mode acceptEdits`, reduce the stream to the
exact consent boolean and session identifier in memory, then use `claude
--resume <session-id> -p "Yes" --output-format stream-json --verbose` for the
three-description booleans. If the executable or authenticated session is
unavailable, record `BLOCKED_CLIENT_UNAVAILABLE`; do not install a client,
print credentials, or claim a Claude live PASS.

Each available client must offer `Set up Agent Maintainer for this repository?`
before committing and, after consent, show the exact three descriptions before
changing Agent Maintainer files. Record only pass/fail, client version, skill
digest, thread/session identifier, and scratch path.

- [ ] **Step 7: Execute the conditional routing fallback if metadata misses**

Skip this step when every available client passes metadata-only routing. If a
client runs successfully but misses the trigger, stop before editing global
instructions and add:

- `src/agent_maintainer/skill/routing.py` with managed begin/end markers;
- `tests/skill/test_routing.py` covering absent/current/malformed/modified
  blocks and preservation of all unrelated instruction text;
- `skill routing install|status|uninstall --client ...` CLI routes;
- ownership metadata for the exact external instruction path;
- public documentation for the fallback.

The exact destinations are `~/.codex/AGENTS.md` and
`~/.claude/CLAUDE.md`. The managed block content is:

```text
When creating, scaffolding, bootstrapping, or initializing a new Git
repository, use the agent-maintainer-setup skill after the basic scaffold
exists and before the initial commit. Ask whether to set it up; do not apply
Agent Maintainer without consent.
```

Use markers `<!-- BEGIN agent-maintainer-setup routing -->` and
`<!-- END agent-maintainer-setup routing -->`. Refuse unmatched, duplicated,
or locally modified managed blocks. Install or remove only the marked block,
preserve the rest of the instruction file byte-for-byte, and add a focused ADR
update because the lifecycle now owns an external instruction path. Observe
RED before implementation, then repeat both live tests.

- [ ] **Step 8: Run broad verification**

```bash
PYTHONPATH=src .venv/bin/python -m agent_maintainer.runners.pyright
just v
git diff --check
```

Follow any durable wait command to a terminal result. Expected: zero Pyright diagnostics and full PASS.

- [ ] **Step 9: Commit**

Stage only Task 4 files and commit `docs: publish setup skill workflow`.

### Task 5: Final integrated review

**Files:**

- Review the complete branch; modify only for blocking findings.

**Interfaces:**

- Consumes: complete branch diff from `origin/main`.
- Produces: explicit spec, quality, safety, and dual-client verdicts.

- [ ] **Step 1: Review the complete branch**

Check every design requirement, managed-file transition, artifact, client-neutral instruction, CLI outside Git, architecture boundary, docs/trace claim, and fresh-session result.

- [ ] **Step 2: Correct findings with focused RED/GREEN tests**

Add one narrow regression per finding, observe RED, implement the smallest correction, and rerun affected checks. Do not broaden scope or add MCP.

- [ ] **Step 3: Run final hygiene**

```bash
git status --short --branch
git diff --stat origin/main...HEAD
git diff --check origin/main...HEAD
just v
```

Inspect for secrets, private data, accidental global-client content, generated artifacts, and unrelated changes.

- [ ] **Step 4: Commit only if review changed files**

Use one focused Conventional Commit for review corrections; otherwise leave the reviewed commits unchanged.
