"""Compatibility shim for repair-fact parser registry."""

from agent_repair_facts import registry

ARTIFACT_FACT_PARSERS = registry.ARTIFACT_FACT_PARSERS
LOG_FACT_PARSERS = registry.LOG_FACT_PARSERS
FactParser = registry.FactParser
FactParserEntry = registry.FactParserEntry
artifact_facts = registry.artifact_facts
find_parser = registry.find_parser
log_facts = registry.log_facts
