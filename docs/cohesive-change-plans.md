# Cohesive Change Plans

This document tracks planned beta work. implementation will land in small
phases. Public behavior must remain deterministic and bounded by default.

Cohesive change plans are the planned path for intentional large changes that
cannot fit normal change budgets. A plan should explain why a larger change is
cohesive, which files are in scope, how the work will be reviewed, and what
evidence proves the change stayed disciplined.

Planned capabilities include structured plan files, required override
explanations, plan-to-diff validation, and integration with change-budget
checks.

The goal is not to make large changes easy to hide. The goal is to make
legitimate migrations explicit, reviewable, and mechanically constrained.
