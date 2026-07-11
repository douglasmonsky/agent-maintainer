"""Generic wait status and result constants."""

from __future__ import annotations

from typing import Final

WAITS_DIR: Final = ".verify-logs/waits"
WAIT_STATUS_PENDING: Final = "pending"
WAIT_STATUS_READY: Final = "ready_for_manual_resume"
WAIT_STATUS_NOTIFYING: Final = "notifying"
WAIT_STATUS_NOTIFY_FAILED: Final = "notify_failed"
WAIT_STATUS_RESUMED: Final = "resumed"
WAIT_STATUS_EXPIRED_READY: Final = "expired_ready"
RESULT_PENDING: Final = "PENDING"
RESULT_PASS: Final = "PASS"
RESULT_FAIL: Final = "FAIL"
RESULT_TIMEOUT: Final = "TIMEOUT"
RESULT_ERROR: Final = "ERROR"
