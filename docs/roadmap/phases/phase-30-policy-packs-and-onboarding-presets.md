# Phase 30: Policy Packs and Onboarding Presets

## PR Title

```text
feat: add onboarding policy presets
```

## Presets

```bash
agent-maintainer init --preset small-library
agent-maintainer init --preset existing-app
agent-maintainer init --preset ai-agent-heavy
agent-maintainer init --preset legacy-ratchet
agent-maintainer init --preset strict-new-repo
```

## Behavior

Presets write tuned starter config.

## Acceptance Criteria

- Presets deterministic.
- Existing tracks still work.
- Tests cover each preset.
- Precommit passes.

---
