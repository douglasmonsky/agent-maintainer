"""Tests for reusable TypeScript LCOV line records."""

from __future__ import annotations

from agent_repair_facts.parsers.typescript_coverage import (
    LcovFileRecord,
    parse_lcov_records,
)


def test_parse_lcov_records_merges_and_sorts_line_hits() -> None:
    """Duplicate records merge deterministically and positive hits win."""

    records = parse_lcov_records(
        """
SF:src/z.ts
DA:9,0
DA:not-a-line
end_of_record
SF:src/a.ts
DA:12,-1
DA:10,0
DA:11,2,checksum
end_of_record
SF:src/a.ts
DA:10,4
DA:11,0
DA:0,3
end_of_record
""".lstrip()
    )

    assert records == (
        LcovFileRecord(
            source="src/a.ts",
            executable_lines=frozenset((10, 11, 12)),
            covered_lines=frozenset((10, 11)),
        ),
        LcovFileRecord(
            source="src/z.ts",
            executable_lines=frozenset((9,)),
            covered_lines=frozenset(),
        ),
    )


def test_parse_lcov_records_retains_empty_and_unterminated_records() -> None:
    """Record presence remains distinct from executable-line presence."""

    records = parse_lcov_records(
        """
SF:src/empty.ts
end_of_record
SF:src/final.ts
DA:7,1
""".lstrip()
    )

    assert records == (
        LcovFileRecord(
            source="src/empty.ts",
            executable_lines=frozenset(),
            covered_lines=frozenset(),
        ),
        LcovFileRecord(
            source="src/final.ts",
            executable_lines=frozenset((7,)),
            covered_lines=frozenset((7,)),
        ),
    )


def test_parse_lcov_records_skips_unsafe_source_scalars() -> None:
    """Empty, dot, control-bearing, and overlong sources are ignored."""

    records = parse_lcov_records(
        "\n".join(
            (
                "SF:",
                "DA:1,0",
                "end_of_record",
                "SF:.",
                "DA:2,0",
                "end_of_record",
                "SF:src/unsafe\x00.ts",
                "DA:3,0",
                "end_of_record",
                f"SF:{'x' * 1001}",
                "DA:4,0",
                "end_of_record",
                "SF:src/safe.ts",
                "DA:5,0",
                "end_of_record",
            )
        )
    )

    assert records == (
        LcovFileRecord(
            source="src/safe.ts",
            executable_lines=frozenset((5,)),
            covered_lines=frozenset(),
        ),
    )


def test_parse_lcov_records_skips_overlong_numeric_neighbors() -> None:
    """Hostile integer fields do not raise or hide later valid DA lines."""

    records = parse_lcov_records(
        f"SF:src/app.ts\nDA:{'9' * 5_000},1\nDA:6,{'9' * 5_000}\nDA:7,1\nend_of_record\n"
    )

    assert records == (
        LcovFileRecord(
            source="src/app.ts",
            executable_lines=frozenset((7,)),
            covered_lines=frozenset((7,)),
        ),
    )
