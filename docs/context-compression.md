# Context Compression

This document tracks planned beta work. implementation will land in small
phases. Public behavior must remain deterministic and bounded by default.

Context compression is the planned optional layer for summarizing supporting
evidence after sensitive details and exact repair facts are separated. It must
never replace exact diagnostics required to fix a failing check.

Planned capabilities include a backend interface, sanitized inputs, optional
Headroom support, and a clear distinction between exact failure facts and
compressed supporting context.

Compression should remain opt-in. Bounded deterministic summaries are the
default behavior.
