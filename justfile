# Canonical developer commands. All agent instructions should point here.
export PYTHONDONTWRITEBYTECODE := "1"
export PYTHONPATH := "src"

bootstrap:
    python3 -m ai_guardrails bootstrap

doctor:
    python3 -m ai_guardrails doctor

guidance:
    python3 -m ai_guardrails guidance

guidance-check:
    python3 -m ai_guardrails guidance --check

verify:
    python3 -m ai_guardrails verify --profile full

verify-fast:
    python3 -m ai_guardrails verify --profile fast

verify-precommit:
    python3 -m ai_guardrails verify --profile precommit

verify-ci:
    python3 -m ai_guardrails verify --profile ci --base-ref origin/main --compare-branch origin/main

verify-manual:
    python3 -m ai_guardrails verify --profile manual

# Example for a flat package layout:
verify-flat PACKAGE:
    python3 -m ai_guardrails verify --profile full --source-root {{PACKAGE}} --coverage-source {{PACKAGE}} --package-path {{PACKAGE}} --test-root tests

verify-full-output:
    ruff format --check .
    ruff check .
    python3 -m ai_guardrails.runners.pyright
    pytest -q --tb=short --disable-warnings --cov=.codex/hooks --cov=src/ai_guardrails --cov-report=term-missing:skip-covered --cov-report=xml --cov-fail-under=90 tests
    radon cc .codex/hooks src/ai_guardrails -a -s
    radon mi .codex/hooks src/ai_guardrails -s
    xenon --max-absolute B --max-modules A --max-average A .codex/hooks src/ai_guardrails
    pylint .codex/hooks src/ai_guardrails --score=n
    python3 -m ai_guardrails.checks.tach_config --strict-root-module
    tach check --exact
    interrogate --fail-under=80 --ignore-init-method --ignore-init-module --ignore-private --ignore-semiprivate --ignore-magic .codex/hooks src/ai_guardrails
    deptry .
    vulture .codex/hooks src/ai_guardrails tests
    bandit -q -r .codex/hooks src/ai_guardrails
    markdownlint-cli2 "**/*.md"
    yamllint .github/workflows .pre-commit-config.yaml .markdownlint-cli2.yaml .yamllint zizmor.yml
    taplo fmt --check pyproject.toml tach.toml config/*.toml
    check-jsonschema --builtin-schema vendor.github-workflows .github/workflows/verify.yml
    pip-audit -r config/dev-lock.txt

clean-verify-logs:
    rm -rf .verify-logs coverage.xml .coverage htmlcov
