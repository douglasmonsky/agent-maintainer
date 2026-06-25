# Canonical developer commands. All agent instructions should point here.

verify:
    python scripts/guardrail.py verify --profile full

verify-fast:
    python scripts/guardrail.py verify --profile fast

verify-precommit:
    python scripts/guardrail.py verify --profile precommit

verify-ci:
    python scripts/guardrail.py verify --profile ci --base-ref origin/main --compare-branch origin/main

# Example for a flat package layout:
verify-flat PACKAGE:
    python scripts/guardrail.py verify --profile full --source-root {{PACKAGE}} --coverage-source {{PACKAGE}} --package-path {{PACKAGE}} --test-root tests

verify-full-output:
    ruff format --check .
    ruff check .
    pyright
    pytest -q --tb=short --disable-warnings --cov=src --cov-report=term-missing:skip-covered --cov-report=xml --cov-fail-under=80 tests
    radon cc src -a -s
    radon mi src -s
    xenon --max-absolute B --max-modules A --max-average A src
    pylint src --score=n
    lint-imports
    deptry .
    vulture src tests scripts
    bandit -q -r src
    # pip-audit is intentionally not run here by default. Prefer a pinned input:
    # pip-audit -r requirements.txt

clean-verify-logs:
    rm -rf .verify-logs coverage.xml .coverage htmlcov
