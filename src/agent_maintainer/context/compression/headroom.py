"""Compatibility shim for optional Headroom compression helpers."""

from __future__ import annotations

from agent_context.compression import headroom as _headroom

BACKEND_HEADROOM = _headroom.BACKEND_HEADROOM
HEADROOM_INSTALL_MESSAGE = _headroom.HEADROOM_INSTALL_MESSAGE
MESSAGE_ROLE = _headroom.MESSAGE_ROLE
CompressionBackendError = _headroom.CompressionBackendError
CompressionBackendUnavailable = _headroom.CompressionBackendUnavailable
dict_result_content = _headroom.dict_result_content
headroom_content = _headroom.headroom_content
headroom_messages = _headroom.headroom_messages
load_headroom_compressor = _headroom.load_headroom_compressor
message_content = _headroom.message_content
messages_content = _headroom.messages_content
normalized_headroom_content = _headroom.normalized_headroom_content
run_headroom_compressor = _headroom.run_headroom_compressor
