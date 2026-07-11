<!-- docsync:object docs.docsync_extraction.overview -->
# DocSync Extraction Notes

DocSync should be incubated in this repository until the standalone package
boundary is boring. DocSync is implemented as an extractable sibling package
under `src/docsync/`. It must not import `agent_maintainer` or `archguard`; the
boundary is enforced by Tach and import tests.

Keep in-repo work aligned with these standalone-readiness rules:

1. DocSync source stays under `src/docsync/`.
2. DocSync tests stay under `tests/docsync/`.
3. Agent Maintainer integration uses the public `docsync.api` boundary.
4. DocSync must not import `agent_maintainer` or `archguard`.
5. Runtime dependencies stay minimal and explicit in package metadata.
6. CLI behavior is documented before it becomes part of the extraction contract.

The product and implementation sequence lives in
[`docs/docsync-roadmap.md`](docsync-roadmap.md).

<!-- docsync:claim claim.docsync.trace_source_truth -->
DocSync source truth lives under `.docsync/`. The trace file is human-authored,
and generated files under `.docsync/out/` are rebuildable artifacts that should
not be committed. Repository-controlled inputs are bounded and confined to the
repository; generated report writes require an explicit command mode.

Markdown object regions use explicit start and end markers when
`require_object_end_markers` is enabled:

```markdown
<!-- docsync:object docs.example.overview -->
# Example
<!-- docsync:object.end docs.example.overview -->
```

Run `python -m docsync repair-object-end-markers --write` to insert missing
object end markers when introducing DocSync to legacy docs.
<!-- docsync:claim.end claim.docsync.trace_source_truth -->

<!-- docsync:claim claim.docsync.command_surface -->
DocSync currently exposes these user-facing commands:

- `docsync init`
- `docsync index`
- `docsync freshness`
- `docsync check`
- `docsync doctor`
- `docsync prompt`
- `docsync repair-object-end-markers`
- `docsync attest`
- `docsync trace ...`

`docsync init --agents` opts into AGENTS.md policy changes, `docsync doctor
--fix` applies safe starter repairs, and `docsync trace ...` provides grouped
authoring commands for documents, objects, evidence, claims, and trace listing.
Plain `docsync check` is read-only; `--write-reports` explicitly creates its JSON
and SARIF artifacts under `.docsync/out/`.
<!-- docsync:claim.end claim.docsync.command_surface -->

Do not extract DocSync only because the directory is separable. Extract it when
the product contract needs independent versioning, external issue tracking,
package releases, or adoption by projects that should not vendor Agent
Maintainer. Before extraction, the trace schema, CLI command names, generated
output paths, and attestation format should be stable enough to document as
compatibility commitments.

To extract DocSync into a standalone package:

1. Copy `src/docsync/`.
2. Copy `tests/docsync/`.
3. Copy `.docsync/config.yml`, `.docsync/schema.json`, and an empty
   `.docsync/trace.yml` template.
4. Move or copy DocSync-focused docs and fixture repositories.
5. Copy `docsync = "docsync.cli:console_main"` entry point and the PyYAML
   runtime dependency into the target `pyproject.toml`.
6. Add standalone package metadata, README, license, CI, and release workflow.
7. Run `python -m pytest tests/docsync -q`.
8. Run `python -m docsync --help` and `python -m docsync doctor` from a
   fixture repository.
9. Replace in-repo source imports in Agent Maintainer with the package
   dependency and keep integration tests here.

Generated files under `.docsync/out/` are not source truth. They are rebuilt by
`docsync index`, `docsync check --write-reports`, `docsync prompt`, and
`python -m docsync freshness`. Plain `docsync check` is read-only; use the
explicit report flag only when JSON and SARIF artifacts are required.

`python -m docsync freshness` writes passive freshness metadata to
`.docsync/out/freshness.json`. The report records last observed content hashes
and cheap Git state for traced documentation objects and evidence anchors
without adding manual timestamps to human docs.

The experimental knowledge graph, vector retrieval, GraphQL, and wiki prototype
remain preserved on `experiment/docsync-knowledge-graph`; that work is not part
of the foundation extraction surface.
<!-- docsync:object.end docs.docsync_extraction.overview -->
