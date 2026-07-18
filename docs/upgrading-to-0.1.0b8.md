<!-- docsync:object docs.upgrade_0_1_0b8.overview -->
# Upgrading from 0.1.0b7 to 0.1.0b8

`0.1.0b8` is published on PyPI. Use this guide to review the experimental Java
and TypeScript additions before adopting them in an existing repository.

## Before You Start

1. Commit or otherwise preserve the application repository's current state.
2. Record existing Codex and Claude hook configuration owned by other tools.
3. Keep the published beta available for rollback:

   ```bash
   python -m pip install "agent-maintainer[core]==0.1.0b7"
   ```

4. Install the published release:

   ```bash
   python -m pip install --upgrade "agent-maintainer[core]==0.1.0b8"
   agent-maintainer doctor
   ```

## Preview Repository Mutations

Preview initialization, hook installation, and Java setup before applying an
operation:

```bash
agent-maintainer init --dry-run --track core --preset existing-app
agent-maintainer install --dry-run
agent-maintainer setup java --preview
```

Review every add, merge, conflict, skip, and replacement. Java setup must use a
checked-in Gradle wrapper and must not create a system-Gradle fallback.

## Check Behavior Changes

- Java/Gradle remains experimental; enable it deliberately and retain existing
  native build policy until the preview is reviewed.
- Spotless, SpotBugs, Checkstyle, PMD, and JaCoCo setup supports Groovy and
  Kotlin DSL projects without hiding existing plugin configuration.
- JaCoCo coverage thresholds can only ratchet upward, and multi-project reports
  retain per-module truth rather than inventing a repository-wide percentage.
- Copied and renamed destinations now count toward cohesive-change budgets.
- TypeScript/JavaScript package-manager and workspace detection is advisory;
  Agent Maintainer does not choose a package manager or run repository scripts.
- Configured Knip and dependency-cruiser checks provide bounded repair facts,
  while the existing OSV Scanner gate provides grouped vulnerability facts.
- Existing LCOV can be inspected against changed lines without running a test
  tool or enforcing a threshold:

  ```bash
  agent-maintainer test-intel typescript-coverage --base-ref origin/main
  ```

- TypeScript/JavaScript remains experimental. Keep existing native lint, test,
  architecture, dependency-audit, and coverage policy until the advisory
  output has been calibrated for the repository.

## Complete The Upgrade

Run the profiles appropriate to the repository and inspect the final diff:

```bash
agent-maintainer doctor
agent-maintainer verify --profile precommit
agent-maintainer verify --profile full
agent-maintainer verify --profile ci --base-ref origin/main --compare-branch origin/main
agent-maintainer verify --profile security
```

For Java repositories, also run the checked-in wrapper tasks that the setup
preview selected on every supported operating system before making them
required.

## Rollback

If the new behavior is unsuitable, restore the preserved repository state
and reinstall the published beta:

```bash
python -m pip install --force-reinstall "agent-maintainer[core]==0.1.0b7"
```

Do not copy candidate-generated files over the restored state. If a mutation
was interrupted, inspect its ignored backup record before retrying or removing
anything manually.
<!-- docsync:object.end docs.upgrade_0_1_0b8.overview -->
