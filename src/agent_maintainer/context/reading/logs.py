"""Compatibility shim for log context readers."""

from agent_context.reading import logs

DEFAULT_TAIL_LINES = logs.DEFAULT_TAIL_LINES
TOKEN_CHAR_RATIO = logs.TOKEN_CHAR_RATIO
LogRequest = logs.LogRequest
LogSelection = logs.LogSelection
estimate_log_command = logs.estimate_log_command
join_selection = logs.join_selection
log_path_from_check = logs.log_path_from_check
refusal_message = logs.refusal_message
render_log_json = logs.render_log_json
render_log_text = logs.render_log_text
resolve_log_path = logs.resolve_log_path
select_log = logs.select_log
slice_head_tail = logs.slice_head_tail
slice_line_range = logs.slice_line_range
slice_text = logs.slice_text
