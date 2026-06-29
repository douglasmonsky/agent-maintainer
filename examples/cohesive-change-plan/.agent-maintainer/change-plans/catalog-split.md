+++
id = "catalog-split"
kind = "cohesive-change"
status = "active"
base_ref = "HEAD"
expires = 2099-01-01
allowed_paths = ["src/catalog/**", "tests/**"]
forbidden_paths = ["src/payments/**"]
max_changed_files = 8
max_changed_lines = 500
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = ["src/catalog/pricing.py"]
+++

## Why this change intentionally large

The catalog pricing functions are moving behind a clearer module boundary.

## Why this should not be split smaller

The tests and implementation need to move together to preserve behavior.

## What allowed to change

Only catalog source files and tests for the catalog behavior are in scope.

## What must not change

Payment, user, and deployment behavior must remain untouched.

## Verification plan

Run focused catalog tests, then run Agent Maintainer precommit verification.

## Rollback plan

Revert the catalog module split and keep the old single-file implementation.

## Follow-up ratchet work

After merge, reduce complexity in `src/catalog/pricing.py`.
