# Tach Domain Roots Own Package Descendants

## Boundary

Archguard treats a valid `[root]` declaration in `tach.domain.toml` as explicit
ownership of every Python source module below that domain directory. Root
`tach.toml` entries remain exact ownership declarations for top-level modules
that are not covered by a domain file.

## Why

Tach itself applies a domain root contract to the package subtree. Requiring the
same leaf modules to be repeated in root `tach.toml` creates duplicate module
definitions and prevents Tach from loading otherwise valid domain-oriented
configuration. Archguard already parsed and validated domain files, so exact
name comparison was stricter than Tach's ownership model.

## Alternatives

Repeating every leaf in root `tach.toml` was rejected because it conflicts with
domain roots and produces large generated inventories. Disabling explicit
ownership checks was rejected because modules outside every root or domain
would then become invisible.

## Still Forbidden

Source modules outside all configured root modules and domain roots still fail.
Malformed domain roots, stale explicit module paths, missing dependency
contracts, and oversized path groups remain errors.
