# Dependency Risk Register

The machine-readable source of truth is
[`config/dependency-risks.toml`](../config/dependency-risks.toml). An accepted
risk must name an owner, rationale, expiry, review trigger, resolution
condition, and concrete mitigations. Expired accepted risks fail the policy
test; they cannot silently become permanent suppressions.

OSV exceptions are stricter still: every ignored advisory must exactly match an
active accepted record, use the same expiry date, and cite the owning risk ID
in its reason. Resolved records remain in the register so reviewers can see why
an exception existed and what closed it.

## Current Accepted Risks

| ID | Owner | Expiry | Decision |
|---|---|---|---|
| `DR-003-python-lock-without-hashes` | `release-maintainer` | 2026-08-31 | The complete development environment is exactly pinned but not hash-locked. Keep the existing audit, SBOM, license, and exact-artifact digest mitigations while cross-platform pip hash enforcement is designed. |
| `DR-004-build-system-lower-bounds` | `release-maintainer` | 2026-08-31 | Isolated builds still resolve lower-bounded build requirements. Continue exact-commit dual-artifact builds and digest verification while a pinned build-toolchain provenance contract is designed. |

The risk must be resolved or explicitly re-reviewed before expiry. Resolution
means generating compatible distribution hashes for `DR-003` and a pinned,
provenance-recorded build toolchain for `DR-004`, not merely extending their
dates.

## Resolved Decisions

| ID | Owner | Expiry | Resolution |
|---|---|---|---|
| `DR-001-js-yaml-merge-key-dos` | `release-maintainer` | 2026-09-30 | `markdownlint-cli2` 0.23.0 moved to `js-yaml` 5.2.0. The OSV exception was removed and `npm audit` is clean. |
| `DR-002-semgrep-python-313-compatibility` | `release-maintainer` | 2026-08-31 | Semgrep 1.169.0 declares Python 3.10 through 3.14 support. The `manual` and `all` extra markers were removed. |

## Review Commands

Run the ecosystem-native checks after any dependency or risk-record change:

```bash
npm ci
npm audit
.venv/bin/pip-audit -r config/dev-lock.txt --no-deps --disable-pip \
  --progress-spinner off --timeout 20
osv-scanner scan source -r . --config osv-scanner.toml
```

Then run the manual and release profiles before treating a resolved exception
as release evidence. Never add an ignore first and promise to document it
later; the owned, unexpired record and mitigation must land with the exception.
