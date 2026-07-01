# Assessment Debt Constants Boundary

## Decision

`agent_maintainer.assess.debt_category_constants` owns Technical Debt Score
category thresholds, weights, and check-keyword tuples.

`agent_maintainer.assess.debt_categories` may depend on those constants, but the
constants module must not depend back on scoring, config, evidence, or reporting
code.

## Rationale

`debt_categories.py` was approaching the configured file-length pressure point.
Moving immutable scoring constants into a dedicated module reduces the scorer's
size while keeping behavior unchanged and avoiding arbitrary package churn.

## Alternatives Considered

Splitting each category into separate modules was deferred because the current
category functions are still cohesive and share manifest-scoring helpers. A
constants-only extraction gives immediate size relief without increasing call
graph complexity.

## Still Forbidden

The constants module should remain pure data. Do not add scoring logic,
filesystem access, config loading, or report formatting there.
