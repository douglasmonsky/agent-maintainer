"""Compatibility shim for verifier timing helpers."""

from agent_run_artifacts import timing

SECONDS_PER_MINUTE = timing.SECONDS_PER_MINUTE
PROFILE_DURATION_HINTS = timing.PROFILE_DURATION_HINTS
utc_timestamp = timing.utc_timestamp
run_timing = timing.run_timing
profile_duration_hint = timing.profile_duration_hint
format_duration = timing.format_duration
duration_seconds = timing.duration_seconds
parsed_duration_seconds = timing.parsed_duration_seconds
