# Agent Maintainer Graphics

This directory contains static public-facing graphics used by the README and
GitHub repository metadata. The old HTML/CSS/SVG render pipeline was removed to
avoid making documentation assets part of the developer toolchain.

## Files

```text
docs/assets/graphics/
  agent-maintainer-overview.png        # overview image
  agent-maintainer-social-preview.png  # README hero and GitHub social preview
  standard-runs-at-a-glance.png        # run profile comparison image
```

`agent-maintainer-social-preview.png` is a 1280 x 640 PNG suitable for GitHub's
repository social preview. It is intentionally optimized below 1 MB.

## Editing Rules

- Keep graphics readable at 900 px README width.
- Keep source/editing notes in the PR that changes an image.
- Do not add a repo-local rendering pipeline unless it materially improves
  maintainability and has a clear owner.
- Do not reintroduce old project names or old config namespaces.
