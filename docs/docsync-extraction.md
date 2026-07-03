<!-- docsync:object docs.docsync_extraction.overview -->
# DocSync Extraction Notes

DocSync is implemented as an extractable sibling package under `src/docsync/`.
It must not import `agent_maintainer` or `archguard`; the boundary is enforced
by Tach and extraction tests.

DocSync source truth lives under `.docsync/`. The trace file is
human-authored, and generated files under `.docsync/out/` are rebuildable
artifacts that should not be committed.

To extract DocSync into a standalone package:

1. Copy `src/docsync/`.
2. Copy `tests/docsync/`.
3. Copy `.docsync/config.yml`, `.docsync/schema.json`, and an empty
   `.docsync/trace.yml` template.
4. Copy the `docsync = "docsync.cli:console_main"` entry point and the PyYAML
   runtime dependency into the target `pyproject.toml`.
5. Run `python -m pytest tests/docsync -q`.
6. Run `python -m docsync --help` and `python -m docsync doctor` from a fixture
   repository.

Generated files under `.docsync/out/` are not source truth. They can be rebuilt
with `docsync index`, `docsync check`, `docsync prompt`, `docsync attest`, and
`docsync doctor`.

The experimental knowledge graph, vector retrieval, GraphQL, and wiki prototype
is preserved on `experiment/docsync-knowledge-graph`; it is not part of the
foundation extraction surface.
