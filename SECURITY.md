# Security Policy

Agent Maintainer operates inside developer repositories and may run quality,
security, hook, packaging, and filesystem workflows. Reports that could expose
private files, credentials, repository integrity, or release artifacts are
treated as security issues.

## Supported Versions

| Version | Security support |
|---|---|
| Latest published beta | Supported |
| Current unreleased release candidate | Accepted for investigation; fixes ship only through a reviewed release |
| Older betas | Not supported; reproduce on the latest beta before reporting when safe |

## Report A Vulnerability Privately

Use [GitHub private vulnerability reporting](https://github.com/douglasmonsky/agent-maintainer/security/advisories/new).
Include the smallest safe reproduction, affected version or commit, expected
boundary, observed behavior, and likely impact.

Do not open a public issue with exploit details, credentials, private paths,
private repository content, or unredacted `.verify-logs` artifacts. If private
reporting is unavailable, open a public issue containing only a request for a
private contact route.

Particularly useful reports include:

- reads or writes outside an approved repository root;
- unsafe symlink, traversal, special-file, archive, or backup behavior;
- hooks or diagnostics that expose secrets or private command arguments;
- bypasses of configuration, release-evidence, or artifact-integrity checks;
- dependency or workflow vulnerabilities with a concrete Agent Maintainer
  impact.

## Response And Disclosure

The maintainer targets an initial acknowledgment within seven days and a first
triage decision within fourteen days. These are goals, not a service-level
agreement. Complex reports may take longer.

Please allow time for validation, a regression test, a coordinated fix, and a
supported release before public disclosure. Confirmed vulnerabilities are
documented through a GitHub security advisory and release notes when the fix is
available.

Good-faith research should minimize access to other people's data, avoid
service disruption or destructive testing, and stop once enough evidence has
been collected to explain the issue.

For non-security questions, use the channels in [SUPPORT.md](SUPPORT.md).
