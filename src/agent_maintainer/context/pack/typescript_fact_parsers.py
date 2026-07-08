"""Compatibility shim for TypeScript repair-fact parsers."""

from agent_repair_facts.parsers import typescript

diagnostic_facts = typescript.diagnostic_facts
read_diagnostics = typescript.read_diagnostics
typescript_lint_facts = typescript.typescript_lint_facts
typescript_test_artifact_facts = typescript.typescript_test_artifact_facts
typescript_test_facts = typescript.typescript_test_facts
typescript_typecheck_facts = typescript.typescript_typecheck_facts
