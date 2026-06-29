# Tach Domain Contracts

## Status

Accepted.

## Context

The repository had strict Tach root ownership, but the root `tach.toml` had
grown into large path buckets. That kept unassigned files visible, but it made
the architecture contract too easy to satisfy by adding another path to an
oversized group.

## Decision

Split package-level Tach contracts into `tach.domain.toml` files beside the code
they govern. Keep root `tach.toml` for top-level modules and shared source-root
settings. Require every root and domain module to declare `depends_on`, and keep
`tach check --exact` passing so unused dependency declarations fail.

Archguard now validates both root and domain Tach configuration. It rejects
missing `depends_on` declarations and oversized `paths = [...]` groups so future
agents cannot use broad buckets as a shortcut.

## Alternatives Considered

- Keep one large root `tach.toml`: rejected because it is difficult to review
  and encourages compliance-only path lumping.
- Generate `tach.toml` from custom fragments: rejected because Tach already
  supports `tach.domain.toml` natively.
- Keep semantic Tach `layer` ordering in this pass: rejected because current
  code still has cross-package cycles. Explicit dependency contracts are a
  stronger honest baseline than fake layer ordering.

## Boundaries

Domain files may define package-local modules and explicit dependencies. They
must not hide unrelated modules in broad path groups. Future semantic layer
cleanup should reduce cross-domain dependencies rather than relax these checks.
