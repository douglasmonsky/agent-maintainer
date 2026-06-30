# Phase 60: Dogfood Source-Checkout Drift Detection

## PR Title

```text
feat: detect stale dogfood console scripts
```

## Scope

Keep this repository dogfooding the current source checkout, not an older
installed `agent-maintainer` package. `doctor` already checks the active module
import path. Extend it to warn when the interactive `agent-maintainer` console
script resolves stale `site-packages` code while this checkout is present.

## File Targets

```text
src/agent_maintainer/doctor/setup.py
src/agent_maintainer/doctor/support/dogfood.py
src/agent_maintainer/doctor/tach.domain.toml
tests/doctor/test_doctor_environment.py
docs/architecture/decisions/
docs/tool-map.md
docs/ROADMAP.md
```

## Requirements

- Keep committed hooks and CI on `PYTHONPATH=src python3 -m agent_maintainer`.
- Treat missing console script as not applicable; the module command is
  canonical in this checkout.
- Warn when the console script imports anything other than local
  `src/agent_maintainer`.
- Repair hint: `python -m pip install -e .`.
- Keep the console-script probe isolated under `doctor.support`.

## Acceptance Criteria

- Focused tests cover missing console script, local console import, stale
  console import, and uninspectable scripts.
- `doctor --strict` includes source and console dogfood rows.
- Tach assigns the new support module explicitly.
- Precommit, full, ci, security, manual profiles pass before PR merge.
