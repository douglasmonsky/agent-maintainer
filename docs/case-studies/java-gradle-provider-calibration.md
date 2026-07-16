# Java/Gradle Provider Calibration

This calibration records reproducible, sanitized fixture evidence for the
experimental Java/Gradle provider. It is an engineering checkpoint, not a
marketing benchmark or an external-repository claim. The evidence does not
promote Java support beyond experimental status.

## Cases and results

| Case | Setup preview | Wrapper calls | Runtime | False positives | Baseline churn | Coverage evidence |
| --- | --- | ---: | ---: | ---: | --- | --- |
| `java-only` | 4 files, 123 diff lines, 0 manual edits | 1 | 5 s | 0 | 0 entries changed on no-op | project `:` at 80% line / 70% branch |
| `mixed-python-java` | 4 files, 123 diff lines, 0 manual edits | 1 | 5 s | 0 | 0 entries changed on no-op | project `:` at 90% line / 80% branch |
| `multi-project` | 4 files, 123 diff lines, 0 manual edits | 1 | 7 s | 0 | 0 of 2 entries changed on no-op | separate `:` and `:app` facts |

All three setup previews were side-effect-free and reversible. None
restructured the existing build. The mixed fixture retained its Python files,
and the multi-project command selected both `check` and fully qualified
`:app:check` in one checked-wrapper invocation.

## Measurement method

The checked Gradle 9.6.1 wrapper from the live Groovy fixture executed each
sanitized project with `--no-daemon --console=plain`. Measurements were taken
on macOS with JBR 25 and a warm Gradle distribution cache. The JSON evidence in
`tests/fixtures/java_gradle/calibration/` records the exact relative commands,
runtime, setup result, seeded repair-fact assessment, baseline churn, threshold
mode, and coverage-report paths.

The coverage percentages are parsed from bounded JaCoCo XML rather than copied
from prose. Multi-project evidence remains two labeled project facts; it does
not synthesize a repository-wide percentage. Seeded failures produced one
actionable static finding in the single-project cases and separate static plus
coverage facts in the multi-project case.

## Threshold calibration

New repositories retain the strict defaults of 80% line and 70% branch
coverage. The established multi-project case records those values as both base
and current floors. No setup or verification path silently lowers an existing
threshold. Measured coverage at the floor is accepted; any downward property
change remains a regression even when current XML has headroom.

## Interpretation and limitations

The controlled cases show zero observed false positives, useful structured
repair facts for seeded failures, stable no-op baselines, bounded wrapper-call
counts, and truthful coverage labels. They also prove that Java setup does not
rewrite the Python side of a mixed repository.

These are small sanitized repositories, not production workloads. Runtime is
cache- and machine-dependent, Windows proof comes from the live CI matrix, and
the multi-project fixture uses per-project reports rather than a real aggregate
report. Broader external repositories remain useful future evidence, but they
are not required to keep this provider useful for the maintainer's own new
repositories.
