<!-- docsync:object docs.docsync_standalone_readme.overview -->
# DocSync

DocSync keeps documentation claims tied to source evidence as a repository
changes. It is for teams and coding agents that need README, architecture,
runbook, and release-note claims to stay reviewable instead of silently drifting
away from the code they describe.

DocSync is intentionally file-based. The source truth is a human-authored
`.docsync/trace.yml`; generated reports live under `.docsync/out/` and can be
rebuilt at any time.

The in-repository product roadmap is tracked in
[`docs/docsync-roadmap.md`](docsync-roadmap.md) until DocSync is ready to extract
as an independently versioned package.

## Core Workflow

1. Mark stable documentation objects with `<!-- docsync:object ... -->`.
2. Mark evidence regions in source, tests, config, or docs with
   `docsync:evidence.start` and `docsync:evidence.end`.
3. Link claims to evidence in `.docsync/trace.yml`.
4. Run `docsync doctor` to validate structure.
5. Run `docsync check --base origin/main` in review to catch changed evidence
   whose documentation claim was not reviewed.

## Command Surface

- `docsync init` creates `.docsync` starter files.
- `docsync index` writes a resolved trace index.
- `docsync freshness` writes passive content-hash metadata.
- `docsync check` validates structural and changed-claim rules.
- `docsync doctor` validates setup without Git diff checks.
- `docsync prompt` writes a compact review packet for agents.
- `docsync repair-object-end-markers` inserts missing Markdown end markers.
- `docsync attest` records reviewed-but-unchanged claim evidence.

## Minimal Trace

```yaml
version: 1
documents:
  docs.readme:
    path: README.md
    title: Example Project
    audience: public
objects:
  docs.readme.overview:
    document: docs.readme
    kind: heading_section
    path: README.md
    marker: docs.readme.overview
claims:
  claim.readme.supported_runtime:
    object: docs.readme.overview
    text: README states the supported Python runtime.
    severity: high
    evidence:
      - evidence.package.python_requires
evidence:
  evidence.package.python_requires:
    type: config
    anchors:
      - path: pyproject.toml
        mode: explicit_region
```

## Standalone Package Target

The standalone package should expose the `docsync` CLI, the public
`docsync.api` module, templates for `.docsync` starter files, and a small fixture
repository that demonstrates the review loop end to end. Agent Maintainer should
remain one integration consumer, not the package owner.
<!-- docsync:object.end docs.docsync_standalone_readme.overview -->
