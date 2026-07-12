# Durable Verifier Wait Lifecycle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Route direct background verifier waits through the same durable watcher lifecycle as every other registered wait.

**Architecture:** `agent_maintainer.verify.background_wait` remains the verifier-facing adapter but delegates registration to the existing typed `agent_maintainer.wait.broker.register_background_verifier` service. The wait broker alone selects launchd or permitted process fallback and persists watcher state.

**Tech Stack:** Python 3.11+, pytest, `agent_waits` durable records, Tach domain contracts, Markdown ADRs.

## Global Constraints

- Strict Codex waits must fail closed when launchd is required and unavailable.
- Verifier code must not own subprocess, launchd, polling, sweeping, resume, or rewake behavior.
- `agent_waits` remains product-neutral.
- Preserve foreground verifier behavior and the existing registration capsule schema.
- Update the Tach dependency and ADR in the same change as the source dependency.

---

### Task 1: Replace the verifier-owned watcher with canonical registration

**Files:**

- Modify: `tests/verify/test_background_wait.py`
- Modify: `src/agent_maintainer/verify/background_wait.py`
- Modify: `src/agent_maintainer/verify/tach.domain.toml`
- Modify: `docs/architecture/decisions/2026-07-07-codex-verifier-background-wait.md`

**Interfaces:**

- Consumes: `agent_maintainer.wait.broker.BackgroundVerifierWait` and `register_background_verifier`.
- Produces: `register_background_verifier_wait(run_id: str, log_dir: Path) -> agent_waits.broker.BackgroundWaitRegistration` with canonical persisted watcher state.

- [ ] **Step 1: Replace the legacy process test with a failing lifecycle integration test**

Remove `PopenSpy`, `typing.cast`, `tests.support.callbacks`, and the two tests
that patch `background_wait.start_wait_watcher`. Add these imports and helper:

```python
import subprocess

from agent_maintainer.wait import broker as wait_broker
from agent_maintainer.wait import daemon_launchd
from agent_waits.watcher_state import watcher_state


def _unsupported_launchd(root: Path, _wait_id: str) -> daemon_launchd.DaemonLaunch:
    return daemon_launchd.DaemonLaunch(
        started=False,
        label="com.agent-maintainer.wait.test",
        log_path=root / "daemon.log",
        error="unsupported",
    )
```

Add the integration test:

```python
def test_register_background_verifier_wait_uses_durable_watcher_policy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Direct verifier registration persists canonical strict-Codex failure."""

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(wait_broker, "ensure_wait_daemon", _unsupported_launchd)

    def reject_legacy_popen(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("verifier adapter must not launch its own watcher")

    monkeypatch.setattr(subprocess, "Popen", reject_legacy_popen)

    registration = background_wait.register_background_verifier_wait(
        "run-123",
        Path(".verify-logs"),
    )

    persisted = wait_broker.WaitRegistry(tmp_path).read(registration.record.wait_id)
    state = watcher_state(persisted)
    assert registration.watcher_started is False
    assert registration.watcher_strategy == ""
    assert "launchd required for Codex rewake" in registration.watcher_error
    assert persisted.kind == wait_broker.WAIT_KIND_VERIFIER
    assert persisted.target_id == "run-123"
    assert persisted.metadata is not None
    assert persisted.metadata["log_dir"] == ".verify-logs"
    assert state.strategy == "failed"
    assert state.error_code == "launchd_required"
```

- [ ] **Step 2: Run the test to verify RED**

Run: `PYTHONPATH=src .venv/bin/pytest tests/verify/test_background_wait.py::test_register_background_verifier_wait_uses_durable_watcher_policy -q`

Expected: FAIL with `verifier adapter must not launch its own watcher` because
the old module calls `subprocess.Popen` directly.

- [ ] **Step 3: Implement the narrow delegation**

In `src/agent_maintainer/verify/background_wait.py`:

- remove imports of `subprocess`, `sys`, `RegisterWait`, and `WaitRegistry`;
- import `from agent_maintainer.wait import broker as lifecycle_broker`;
- delete `start_wait_watcher` entirely;
- replace registration with this implementation:

```python
def register_background_verifier_wait(
    run_id: str,
    log_dir: Path,
) -> wait_broker.BackgroundWaitRegistration:
    """Register one verifier wait through the canonical durable lifecycle."""

    return lifecycle_broker.register_background_verifier(
        lifecycle_broker.BackgroundVerifierWait(
            root=Path.cwd(),
            run_id=run_id,
            platform=wait_broker.CODEX_PLATFORM,
            log_dir=log_dir,
            interval_seconds=VERIFIER_WAIT_INTERVAL_SECONDS,
            timeout_seconds=VERIFIER_WAIT_TIMEOUT_SECONDS,
        ),
    )
```

Keep `background_launch_enabled` and `render_background_registration_text`
delegating to the product-neutral `agent_waits.broker` helpers.

- [ ] **Step 4: Update the explicit architecture contract**

Change the `background_wait` module entry in
`src/agent_maintainer/verify/tach.domain.toml` to:

```toml
[[modules]]
path = "background_wait"
depends_on = [
  "//agent_maintainer.wait.broker",
  "//agent_waits.broker",
]
```

Amend the 2026-07-07 ADR to say verifier launch code may call the typed wait
broker registration service, while handlers, registry internals, daemon,
launchd, sweeper, polling, resume, and rewake remain forbidden. Record the
rejected alternatives: a second launcher, moving launchd into `agent_waits`, and
an extra forwarding wrapper.

- [ ] **Step 5: Verify GREEN and persisted behavior**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest \
  tests/verify/test_background_wait.py \
  tests/wait/test_wait_broker_daemon.py -q
PYTHONPATH=src .venv/bin/python -m archguard tach-config --strict-root-module
.venv/bin/tach check --exact
```

Expected: all tests PASS, Archguard reports configured architecture, and Tach
reports no exact dependency violations.

- [ ] **Step 6: Commit the lifecycle change**

```bash
git add -- \
  tests/verify/test_background_wait.py \
  src/agent_maintainer/verify/background_wait.py \
  src/agent_maintainer/verify/tach.domain.toml \
  docs/architecture/decisions/2026-07-07-codex-verifier-background-wait.md
git commit -m "fix: unify verifier wait lifecycle"
```

### Task 2: Dogfood the direct verifier path and run the broad gate

**Files:**

- No source files unless a failing regression test identifies a defect.
- Inspect: `.verify-logs/runs/<run-id>/manifest.json`
- Inspect: `.verify-logs/waits/<wait-id>.json`

**Interfaces:**

- Consumes: `just vp` background-verifier launch path.
- Produces: runtime evidence that direct verification no longer reports a legacy `Popen` watcher for strict Codex.

- [ ] **Step 1: Launch the precommit profile through the real entry point**

Run: `just vp`

Expected initial output: `Result: PENDING` is allowed, but the registration text
must not say `watcher: started via popen`. On a host without supported launchd,
it must say `watcher: not started (launchd required for Codex rewake: ...)` and
include the fallback heartbeat request.

- [ ] **Step 2: Wait for the same verifier run to finish**

Use the exact `sweep_command` printed in the capsule, or inspect the run
manifest after the watcher completes. Do not create a second verifier wait by
passing a wait ID to `just wv`.

Expected: the original verifier manifest contains no failed checks.

- [ ] **Step 3: Inspect durable watcher state**

Read the JSON record named by the registration capsule and verify:

```text
metadata.watcher_strategy = "launchd" or "failed"
metadata.watcher_error_code = absent or "launchd_required"
metadata.watcher_pid = absent for strict Codex
```

- [ ] **Step 4: Run the broad profile**

Run: `just v`

Expected: terminal PASS. If the command backgrounds, follow only the original
run's sweep command and review its manifest before claiming success.
