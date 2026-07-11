# Support Policy

Agent Maintainer is beta software maintained on a best-effort basis. There is
no guaranteed response time, paid support channel, or compatibility promise
outside the documented beta contract.

## Where To Ask

- Reproducible defects: choose **Bug report** from the
  [issue chooser](https://github.com/douglasmonsky/agent-maintainer/issues/new/choose).
- Setup and usage questions: choose **Support request** from the issue chooser.
- Product proposals: choose **Feature request** and explain the problem and
  measurable outcome before proposing an implementation.
- Security vulnerabilities: use the private route in
  [SECURITY.md](SECURITY.md), never a public support issue.

Search existing issues before filing a new one. One focused report is easier to
triage than a combined list of unrelated problems.

## Supported Surface

The latest published beta is the normal support target. The current unreleased
candidate is accepted for testing and feedback but may change before release.

- Python 3.11 through 3.14 is the core compatibility contract.
- Compatibility CI runs on Ubuntu. macOS is used for regular local development;
  Windows behavior is currently best effort.
- Python is the core provider. TypeScript/JavaScript and task-broker surfaces
  remain experimental or advisory where their documentation says so.
- Agent Maintainer coordinates third-party tools. Tool-specific behavior that
  is unrelated to Agent Maintainer's orchestration may need to be reported to
  that upstream project.

## What To Include

Provide the Agent Maintainer version or commit, operating system, Python
version, installation method, exact command, expected result, actual result,
and a minimal synthetic reproduction. Include the bounded failure summary and
run ID when available.

Redact credentials, usernames, home-directory paths, private repository names,
student or customer data, and production details. Do not upload an entire
`.verify-logs` directory or private source tree. Replace sensitive data with a
small synthetic fixture that preserves the behavior.

## Triage

Reports may be closed when they cannot be reproduced, concern an unsupported
version, omit requested diagnostics, or belong to an upstream tool. Useful
reports may still wait for maintainer capacity. Release and security-boundary
work takes priority over feature expansion during stabilization.
