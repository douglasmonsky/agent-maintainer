# Canonical developer commands. All agent instructions should point here.

bootstrap:
    python3 -m scripts.guardrail bootstrap

doctor:
    python3 -m scripts.guardrail doctor

guidance:
    python3 -m scripts.guardrail guidance

guidance-check:
    python3 -m scripts.guardrail guidance --check

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
    python3 -m scripts.run_pyright
    pytest -q --tb=short --disable-warnings --cov=scripts --cov=.codex/hooks --cov-report=term-missing:skip-covered --cov-report=xml --cov-fail-under=80 tests
    radon cc scripts .codex/hooks -a -s
    radon mi scripts .codex/hooks -s
    xenon --max-absolute B --max-modules A --max-average A scripts .codex/hooks
    pylint scripts .codex/hooks --score=n
    python3 -m scripts.check_tach_config --strict-root-module
    tach check --exact
    interrogate --fail-under=80 --ignore-init-method --ignore-init-module --ignore-private --ignore-semiprivate --ignore-magic scripts .codex/hooks
    deptry .
    vulture scripts .codex/hooks tests
    bandit -q -r scripts .codex/hooks
    pip-audit -r config/dev-lock.txt

clean-verify-logs:
    rm -rf .verify-logs coverage.xml .coverage htmlcov
