"""Compatibility shim for diff path classification."""

from agent_context.reading import diff_classify

DOC_SUFFIXES = diff_classify.DOC_SUFFIXES
GENERATED_PARTS = diff_classify.GENERATED_PARTS
LOCK_FILE_NAMES = diff_classify.LOCK_FILE_NAMES
PYTHON_SUFFIX = diff_classify.PYTHON_SUFFIX
count_matching = diff_classify.count_matching
is_docs_path = diff_classify.is_docs_path
is_generated_or_lock_path = diff_classify.is_generated_or_lock_path
is_python_path = diff_classify.is_python_path
is_test_path = diff_classify.is_test_path
