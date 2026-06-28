# Context Safety

This document tracks planned beta work. implementation will land in small
phases. Public behavior must remain deterministic and bounded by default.

Context safety is the planned layer that keeps verification feedback useful
when a repository has large files, long logs, broad diffs, or many existing
violations. The goal is to give agents enough evidence to repair the next
issue without flooding their working context.

Planned capabilities include bounded failure summaries, explicit commands for
expanding details, safe file and diff readers, and context packs that organize
repair evidence around the current task.

The default behavior should stay conservative: summarize first, keep generated
artifacts on disk, and require an explicit command before printing large
supporting context.
