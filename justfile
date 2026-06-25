# Canonical developer commands. All agent instructions should point here.

bootstrap:
    python3 -m scripts.guardrail bootstrap

doctor:
    python3 -m scripts.guardrail doctor

verify:
    python3 -m scripts.guardrail verify --profile full

verify-fast:
    python3 -m scripts.guardrail verify --profile fast

verify-precommit:
    python3 -m scripts.guardrail verify --profile precommit

verify-ci:
    python3 -m scripts.guardrail verify --profile ci --base-ref origin/main --compare-branch origin/main

# Example for a flat package layout:
verify-flat PACKAGE:
    python3 -m scripts.guardrail verify --profile full --source-root {{PACKAGE}} --coverage-source {{PACKAGE}} --package-path {{PACKAGE}} --test-root tests

verify-full-output:
    ruff format --check .
    ruff check .
    pyright
    pytest -q --tb=short --disable-warnings --cov=src --cov-report=term-missing:skip-covered --cov-report=xml --cov-fail-under=80 tests
    radon cc src -a -s
    radon mi src -s
    xenon --max-absolute B --max-modules A --max-average A src
    pylint src --score=n
    python3 -m scripts.check_tach_config --strict-root-module
    tach check --exact
    interrogate --fail-under=80 --ignore-init-method --ignore-init-module --ignore-private --ignore-semiprivate --ignore-magic scripts .codex/hooks
    deptry .
    vulture src tests scripts
    bandit -q -r src
    # pip-audit is intentionally not run here by default. Prefer a pinned input:
    # pip-audit -r requirements.txt

clean-verify-logs:
    rm -rf .verify-logs coverage.xml .coverage htmlcov
