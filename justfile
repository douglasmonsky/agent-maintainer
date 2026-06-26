# Canonical developer commands. All agent instructions should point here.
export PYTHONDONTWRITEBYTECODE := "1"

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

verify-manual:
    python3 -m scripts.guardrail verify --profile manual

# Example for a flat package layout:
verify-flat PACKAGE:
    python3 -m scripts.guardrail verify --profile full --source-root {{PACKAGE}} --coverage-source {{PACKAGE}} --package-path {{PACKAGE}} --test-root tests

verify-full-output:
    ruff format --check .
    ruff check .
    python3 -m scripts.run_pyright
    pytest -q --tb=short --disable-warnings --cov=scripts --cov=.codex/hooks --cov=guardrail_lib --cov-report=term-missing:skip-covered --cov-report=xml --cov-fail-under=90 tests
    radon cc scripts .codex/hooks guardrail_lib -a -s
    radon mi scripts .codex/hooks guardrail_lib -s
    xenon --max-absolute B --max-modules A --max-average A scripts .codex/hooks guardrail_lib
    pylint scripts .codex/hooks guardrail_lib --score=n
    python3 -m scripts.check_tach_config --strict-root-module
    tach check --exact
    interrogate --fail-under=80 --ignore-init-method --ignore-init-module --ignore-private --ignore-semiprivate --ignore-magic scripts .codex/hooks guardrail_lib
    deptry .
    vulture scripts .codex/hooks guardrail_lib tests
    bandit -q -r scripts .codex/hooks guardrail_lib
    markdownlint-cli2 "**/*.md"
    yamllint .github/workflows .pre-commit-config.yaml .markdownlint-cli2.yaml .yamllint zizmor.yml
    taplo fmt --check pyproject.toml tach.toml config/*.toml
    check-jsonschema --builtin-schema vendor.github-workflows .github/workflows/verify.yml
    pip-audit -r config/dev-lock.txt

clean-verify-logs:
    rm -rf .verify-logs coverage.xml .coverage htmlcov
