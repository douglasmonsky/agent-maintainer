<!-- docsync:object docs.docsync_roadmap.overview -->
# DocSync Usefulness Roadmap

DocSync stays in this repository while the product contract hardens. The goal is
to make documentation freshness useful during normal pull-request review before
extracting a standalone package.

## Milestones

1. Authoring UX: add grouped `docsync trace ...` commands so users can create
   documents, objects, evidence, and claims without hand-editing YAML.
2. Hybrid claim precision: combine claim text fingerprints with optional claim
   spans so unrelated documentation edits do not satisfy changed evidence.
3. Agent review packets: include claim text, evidence context, document context,
   and exact repair actions in generated review prompts.
4. Attestations: record all evidence fingerprints plus reviewer, base/head, and
   expiry metadata so reviewed-but-unchanged claims are auditable.
5. Diagnostics: point trace errors at precise YAML lines and offer safe
   `docsync doctor --fix` repairs.
6. Standalone defaults: make initialization and base-ref behavior friendly for
   repositories that do not use Agent Maintainer.

## Completion Bar

Each milestone should land as an in-repo PR with focused DocSync tests,
`docsync doctor`, `docsync check`, and updated docs. Extraction should wait until
the CLI, trace schema, report packet, and attestation format are stable enough
to version independently.
<!-- docsync:object.end docs.docsync_roadmap.overview -->
