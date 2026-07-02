"""Compatibility shim for pytest repair-fact parsers."""

from agent_repair_facts.parsers import pytest

coverage_fact = pytest.coverage_fact
coverage_facts = pytest.coverage_facts
coverage_file_has_missing_lines = pytest.coverage_file_has_missing_lines
first_failure_or_error = pytest.first_failure_or_error
junit_fact = pytest.junit_fact
junit_facts = pytest.junit_facts
junit_message = pytest.junit_message
local_name = pytest.local_name
parse_junit_root = pytest.parse_junit_root
pytest_artifact_facts = pytest.pytest_artifact_facts
