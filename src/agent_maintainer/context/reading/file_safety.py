"""Compatibility shim for file safety checks."""

from agent_context.reading import file_safety

GENERATED_MARKERS = file_safety.GENERATED_MARKERS
LOCK_FILE_NAMES = file_safety.LOCK_FILE_NAMES
MAX_JSON_LINE_LENGTH = file_safety.MAX_JSON_LINE_LENGTH
MAX_MINIFIED_JSON_LINES = file_safety.MAX_MINIFIED_JSON_LINES
REFUSED_PARTS = file_safety.REFUSED_PARTS
REFUSED_SUFFIXES = file_safety.REFUSED_SUFFIXES
TEXT_SAMPLE_BYTES = file_safety.TEXT_SAMPLE_BYTES
FileSafety = file_safety.FileSafety
denied = file_safety.denied
inspect_file = file_safety.inspect_file
inspect_path = file_safety.inspect_path
inspect_text = file_safety.inspect_text
is_binary = file_safety.is_binary
looks_generated = file_safety.looks_generated
looks_minified_json = file_safety.looks_minified_json
read_file_bytes = file_safety.read_file_bytes
refused_path = file_safety.refused_path
