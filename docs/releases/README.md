<!-- docsync:object docs.release_index.overview -->
# Release Index

This index separates immutable publication evidence from release-candidate
intent. A version is published only when its record contains the exact commit,
tag, package-index workflows, artifact digests, and clean-install proof.

- Latest published release: [`0.1.0b5`](0.1.0b5.md)
- Current release candidate: [`0.1.0b6`](0.1.0b6.md) — unpublished

The candidate document is not release evidence. Until publication completes,
install the published version for normal use and follow the
[0.1.0b6 upgrade guide](../upgrading-to-0.1.0b6.md) only in a trusted test
checkout.

When a candidate is published, replace its intent-only record with immutable
evidence before moving the latest-published pointer.
<!-- docsync:object.end docs.release_index.overview -->
