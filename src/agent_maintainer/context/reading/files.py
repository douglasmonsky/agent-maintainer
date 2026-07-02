"""Compatibility shim for file context readers."""

from agent_context.reading import files

DEFAULT_FILE_CONTEXT_LINES = files.DEFAULT_FILE_CONTEXT_LINES
ContextSelection = files.ContextSelection
FileContext = files.FileContext
FileRequest = files.FileRequest
around_range = files.around_range
bounded_context = files.bounded_context
count_lines = files.count_lines
find_symbol = files.find_symbol
lines_context = files.lines_context
outline_context = files.outline_context
outline_for_path = files.outline_for_path
parse_line_range = files.parse_line_range
refused_context = files.refused_context
render_file_json = files.render_file_json
render_file_text = files.render_file_text
render_outline = files.render_outline
render_symbol = files.render_symbol
select_file_context = files.select_file_context
selected_file_context = files.selected_file_context
symbol_context = files.symbol_context
symbols_context = files.symbols_context
