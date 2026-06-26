# Structure Cohesion

Folder file count is a smell, not proof of bad design. The guardrail warns when
one folder contains enough Python files that responsibility boundaries may be
getting hard for humans and agents to track.

Default policy:

- warn at 20 Python files in one folder
- block at 40 Python files only in `fresh-strict`
- ignore tests, migrations, generated folders, virtualenvs, and caches
- use regex hints to point at likely clusters, not to force arbitrary folders

Hints look for repeated prefixes such as `guardrail_` and `check_`, repeated
role suffixes such as `_model`, `_service`, `_repository`, `_client`,
`_adapter`, `_parser`, `_loader`, `_schema`, `_executor`, `_reporting`, and layer
words such as `cli`, `args`, `config`, `models`, `checks`, `doctor`, `executor`,
and `reporting`.

When this warning fires, split only if the files form multiple concepts. A good
split gives a clear answer to "what kind of thing belongs here?" This repository
already uses that shape in `src/ai_guardrails/config/`: schema, loading, coercion,
and mode logic live together under one package instead of remaining as unrelated
flat modules.

The first implementation intentionally stays simple and explainable. Sibling
import density may become a stronger cohesion signal later, but file count plus
regex/layer hints is easier to audit and less likely to force fake refactors.

Configuration:

```toml
[tool.ai_guardrails]
structure_paths = ["src"]
structure_ignore_paths = ["tests/**", "migrations/**", "generated/**"]
folder_file_warn = 20
folder_file_block = 40
structure_cluster_min = 4
structure_hint_patterns = ["^guardrail_", "^check_", "_service$"]
```
