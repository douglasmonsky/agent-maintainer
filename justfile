# Canonical developer commands. All agent instructions should point here.
export PYTHONDONTWRITEBYTECODE := "1"
export PYTHONPATH := "src"

bootstrap:
    python3 -m agent_maintainer bootstrap

doctor:
    python3 -m agent_maintainer doctor

guidance:
    python3 -m agent_maintainer guidance

guidance-check:
    python3 -m agent_maintainer guidance --check

verify:
    python3 -m agent_maintainer verify --profile full

verify-fast:
    python3 -m agent_maintainer verify --profile fast

verify-precommit:
    python3 -m agent_maintainer verify --profile precommit

verify-ci:
    python3 -m agent_maintainer verify --profile ci --base-ref origin/main --compare-branch origin/main

verify-manual:
	python3 -m agent_maintainer verify --profile manual

release-check:
	PYTHON="$([ -x .venv/bin/python ] && printf '%s' .venv/bin/python || printf '%s' python3)"; AGENT_MAINTAINER_RUN_RELEASE_TESTS=1 "$PYTHON" -m pytest -m release tests/release -q

# Example for a flat package layout:
verify-flat PACKAGE:
    python3 -m agent_maintainer verify --profile full --source-root {{PACKAGE}} --coverage-source {{PACKAGE}} --package-path {{PACKAGE}} --test-root tests

verify-full-output:
    ruff format --check .
    ruff check .
    python3 -m agent_maintainer.runners.pyright
    pytest -q --tb=short --disable-warnings --cov=.codex/hooks --cov=.claude/hooks --cov=src/agent_maintainer --cov=src/archguard --cov-report=term-missing:skip-covered --cov-report=xml --cov-fail-under=90 tests
    radon cc .codex/hooks .claude/hooks src/agent_maintainer src/archguard -a -s
    radon mi .codex/hooks .claude/hooks src/agent_maintainer src/archguard -s
    xenon --max-absolute B --max-modules A --max-average A .codex/hooks .claude/hooks src/agent_maintainer src/archguard
    pylint .codex/hooks .claude/hooks src/agent_maintainer src/archguard --score=n
    python3 -m archguard tach-config --strict-root-module
    tach check --exact
    interrogate --fail-under=80 --ignore-init-method --ignore-init-module --ignore-private --ignore-semiprivate --ignore-magic .codex/hooks .claude/hooks src/agent_maintainer src/archguard
    deptry .
    vulture .codex/hooks .claude/hooks src/agent_maintainer src/archguard tests
    bandit -q -r .codex/hooks .claude/hooks src/agent_maintainer src/archguard
    markdownlint-cli2 "**/*.md"
    yamllint .github/workflows .pre-commit-config.yaml .markdownlint-cli2.yaml .yamllint zizmor.yml
    taplo fmt --check pyproject.toml tach.toml config/*.toml
    check-jsonschema --builtin-schema vendor.github-workflows .github/workflows/verify.yml
    pip-audit -r config/dev-lock.txt

clean-verify-logs:
    rm -rf .verify-logs coverage.xml .coverage htmlcov
