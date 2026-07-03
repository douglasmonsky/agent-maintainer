"""Compatibility shim for GitHub PR verification summaries."""

from agent_run_artifacts import pr_summary

PR_SUMMARY_NAME = pr_summary.PR_SUMMARY_NAME
DEBT_SCORE_NAME = pr_summary.DEBT_SCORE_NAME
DEBT_SCORE_COMMAND = pr_summary.DEBT_SCORE_COMMAND
DEBT_DRIVER_LIMIT = pr_summary.DEBT_DRIVER_LIMIT
render_pr_summary = pr_summary.render_pr_summary
header_lines = pr_summary.header_lines
verification_result_lines = pr_summary.verification_result_lines
technical_debt_score_lines = pr_summary.technical_debt_score_lines
top_failure_lines = pr_summary.top_failure_lines
failure_lines = pr_summary.failure_lines
test_intelligence_lines = pr_summary.test_intelligence_lines
ratchet_target_lines = pr_summary.ratchet_target_lines
change_budget_lines = pr_summary.change_budget_lines
change_plan_lines = pr_summary.change_plan_lines
context_pack_lines = pr_summary.context_pack_lines
expansion_command_lines = pr_summary.expansion_command_lines
