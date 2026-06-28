# Test Intelligence

This document tracks planned beta work. implementation will land in small
phases. Public behavior must remain deterministic and bounded by default.

Test intelligence is the planned layer that helps agents choose meaningful
tests for the source they changed. Existing pytest, coverage, and diff-cover
gates prove whether tests ran and changed lines are covered, but they do not
fully explain which tests are relevant or what kind of test is missing.

Planned capabilities include changed-source to test hints, source-without-test
guidance, branch coverage signals, mutation-test target suggestions,
Hypothesis candidate guidance, and CrossHair candidate guidance for pure typed
functions.

These signals should guide better tests without encouraging coverage theater or
turning slow research tools into normal precommit gates.
