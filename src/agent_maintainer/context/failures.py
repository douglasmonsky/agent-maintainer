"""Compatibility shim for context failure readers."""

from agent_context import failures

DEFAULT_CONTEXT_BUDGET = failures.DEFAULT_CONTEXT_BUDGET
DEFAULT_FAILURE_CATEGORY = failures.DEFAULT_FAILURE_CATEGORY
DEFAULT_FAILURE_LIMIT = failures.DEFAULT_FAILURE_LIMIT
FAILURE_CATEGORY_RULES = failures.FAILURE_CATEGORY_RULES
FAILURE_STATUSES = failures.FAILURE_STATUSES
MANIFEST_NAME = failures.MANIFEST_NAME
FailureCategoryRule = failures.FailureCategoryRule
FailureRecord = failures.FailureRecord
bound_report = failures.bound_report
failure_category = failures.failure_category
failure_records = failures.failure_records
load_manifest = failures.load_manifest
manifest_path = failures.manifest_path
optional_int = failures.optional_int
record_from_payload = failures.record_from_payload
record_sort_key = failures.record_sort_key
render_failures_json = failures.render_failures_json
render_failures_text = failures.render_failures_text
render_record = failures.render_record
string_tuple = failures.string_tuple
