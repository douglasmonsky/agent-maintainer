"""Compatibility shim for context size estimates."""

from agent_context import estimate

DEFAULT_DIFF_CONTEXT_LINES = estimate.DEFAULT_DIFF_CONTEXT_LINES
TOKEN_CHAR_RATIO = estimate.TOKEN_CHAR_RATIO
ContextEstimate = estimate.ContextEstimate
EstimateRequest = estimate.EstimateRequest
build_estimate = estimate.build_estimate
estimate_context = estimate.estimate_context
estimate_diff = estimate.estimate_diff
estimate_failures = estimate.estimate_failures
estimate_file = estimate.estimate_file
estimate_log = estimate.estimate_log
estimate_tokens = estimate.estimate_tokens
log_recommendation = estimate.log_recommendation
read_text = estimate.read_text
recommend_budget = estimate.recommend_budget
render_estimate_json = estimate.render_estimate_json
render_estimate_text = estimate.render_estimate_text
run_git_diff = estimate.run_git_diff
