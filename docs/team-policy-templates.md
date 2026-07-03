<!-- docsync:object docs.team_policy_templates.overview -->
# Team Policy Templates

Team policy templates are named initializer presets for common adoption
contexts. They do not change which files an `init` track writes. They only
tune the starter `pyproject.toml` policy values.

Use them with any track:

```bash
agent-maintainer init --track agent --preset team-agent-heavy
```

## Templates

| Template | Use When | Policy Shape |
|---|---|---|
| `team-small-python-lib` | A compact package can start with tighter review budgets. | Same policy shape as `small-library`. |
| `team-legacy-service` | An existing service needs improvement ratchets before strict blocking. | Same policy shape as `legacy-ratchet`. |
| `team-agent-heavy` | Coding agents frequently edit source and should provide tests. | Same policy shape as `ai-agent-heavy`. |
| `team-security-sensitive` | A new or clean repo wants the strictest starter posture. | Same policy shape as `strict-new-repo`. |

## Selection Guidance

Choose `team-small-python-lib` for small packages with clear source and test
roots.

Choose `team-legacy-service` when existing debt should be tracked and reduced
without freezing all development immediately.

Choose `team-agent-heavy` when agents actively write code and source-only
changes should fail in normal completion profiles.

Choose `team-security-sensitive` only when the repo can tolerate strict starter
defaults, including zero new suppressions, strict Pyright mode, and wemake.

These templates are deterministic. Agent Maintainer does not infer a team
template automatically during `init`; use `agent-maintainer assess setup` when
you want recommendations before choosing a track and preset.
<!-- docsync:object.end docs.team_policy_templates.overview -->
