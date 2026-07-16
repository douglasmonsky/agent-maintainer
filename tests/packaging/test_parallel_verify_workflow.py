"""Contract tests for fail-closed parallel pull-request verification."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "verify.yml"
JAVA_LIVE_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "java-gradle-live.yml"
JAVA_LIVE_FIXTURES = REPO_ROOT / "tests" / "live" / "java_gradle"
PARTIAL_GROUP_COUNT = 2
RUNNER_COMMAND_TEXT_OCCURRENCES = 4

# docsync:evidence.start evidence.java.live_workflow_tests


def workflow_text() -> str:
    """Return the verified workflow source."""

    return WORKFLOW.read_text(encoding="utf-8")


def job_body(text: str, job: str, next_job: str | None) -> str:
    """Return one top-level workflow job body."""

    start = text.index(f"  {job}:")
    if next_job is None:
        return text[start:]
    return text[start : text.index(f"  {next_job}:", start)]


def test_verify_workflow_runs_verifier_owned_groups_in_parallel() -> None:
    """Independent jobs select groups through the product CLI contract."""

    text = workflow_text()
    tests_job = job_body(text, "tests-and-coverage", "static-and-policy")
    static_job = job_body(text, "static-and-policy", "verify")

    assert "--group tests-and-coverage" in tests_job
    assert "--group static-and-policy" in static_job
    assert "Set up Node" not in tests_job
    assert "Install external Agent Maintainer tools" not in tests_job
    assert "Set up Node" in static_job
    assert "Install external Agent Maintainer tools" in static_job
    assert "name: verify-tests-and-coverage-${{ github.sha }}" in tests_job
    assert "name: verify-static-and-policy-${{ github.sha }}" in static_job
    assert tests_job.count("include-hidden-files: true") == 1
    assert static_job.count("include-hidden-files: true") == 1


def test_verify_aggregate_job_preserves_protected_job_name_and_fails_closed() -> None:
    """The stable verify job aggregates both exact-run manifests."""

    text = workflow_text()
    aggregate_job = job_body(text, "verify", None)

    assert "needs: [tests-and-coverage, static-and-policy]" in aggregate_job
    assert "if: always()" in aggregate_job
    assert aggregate_job.count("actions/download-artifact@") == PARTIAL_GROUP_COUNT
    assert "name: verify-tests-and-coverage-${{ github.sha }}" in aggregate_job
    assert "name: verify-static-and-policy-${{ github.sha }}" in aggregate_job
    assert "--aggregate-partial partials/tests-and-coverage/manifest.json" in aggregate_job
    assert "--aggregate-partial partials/static-and-policy/manifest.json" in aggregate_job
    assert "--aggregate-output .verify-logs/manifest.json" in aggregate_job
    assert "name: verify-logs" in aggregate_job
    assert aggregate_job.count("include-hidden-files: true") == 1


def test_python_compatibility_matrix_remains_independent() -> None:
    """Parallel quality checks do not weaken supported-version coverage."""

    text = workflow_text()
    compatibility = job_body(text, "python-compatibility", "tests-and-coverage")

    assert 'python-version: ["3.11", "3.12", "3.13", "3.14"]' in compatibility
    assert "needs:" not in compatibility


def test_live_java_workflow_is_separate_bounded_and_experimental() -> None:
    """Live Gradle proof does not lengthen the protected aggregate verifier."""

    text = JAVA_LIVE_WORKFLOW.read_text(encoding="utf-8")

    assert "name: java-gradle-live" in text
    assert "workflow_dispatch:" in text
    assert "schedule:" in text
    assert "pull_request:" in text
    assert "push:" in text
    assert "timeout-minutes: 20" in text
    assert "fail-fast: false" in text
    assert "os: [ubuntu-latest, windows-latest]" in text
    assert "dsl: [groovy, kotlin]" in text
    assert "runs-on: ${{ matrix.os }}" in text
    assert "tests/live/java_gradle/${{ matrix.dsl }}" in text


def test_live_java_workflow_validates_wrappers_and_uses_bounded_cache() -> None:
    """Every matrix cell validates its checked wrapper and caches dependencies safely."""

    text = JAVA_LIVE_WORKFLOW.read_text(encoding="utf-8")

    assert "uses: actions/setup-java@" in text
    assert "distribution: temurin" in text
    assert 'java-version: "21"' in text
    assert "uses: gradle/actions/setup-gradle@" in text
    assert "cache-provider: basic" in text
    assert "cache-read-only: ${{ github.ref != 'refs/heads/main' }}" in text
    assert "validate-wrappers: true" in text
    assert "uses: actions/setup-python@" in text
    assert "python -m pip install --disable-pip-version-check ." in text
    assert "python -m agent_maintainer.ecosystems.java.runner --group static" in text
    assert "python -m agent_maintainer.ecosystems.java.runner --group tests" in text
    assert (
        text.count("agent_maintainer.ecosystems.java.runner --group")
        == RUNNER_COMMAND_TEXT_OCCURRENCES
    )
    assert "_AGENT_MAINTAINER_VERIFY_PROFILE: full" in text
    assert "agent-maintainer-live-base" in text
    assert "git commit-tree" in text
    assert "minimumLineCoverage=0.81" in text
    assert "minimumBranchCoverage=0.71" in text
    assert '["wrapper_invocations"]' in text
    assert 'if [ "$static_calls" -ne 1 ] || [ "$tests_calls" -ne 1 ]; then' in text
    assert "wrapper-calls.txt" in text
    assert "runtime-seconds.txt" in text


def test_live_java_workflow_uploads_reports_for_every_matrix_cell() -> None:
    text = JAVA_LIVE_WORKFLOW.read_text(encoding="utf-8")

    assert "if: always()" in text
    assert "uses: actions/upload-artifact@" in text
    assert "java-gradle-live-${{ matrix.os }}-${{ matrix.dsl }}-${{ github.sha }}" in text
    assert "build/reports/**" in text
    assert "build/agent-maintainer-live/**" in text
    assert "retention-days: 7" in text


def test_live_java_fixtures_are_real_checked_wrapper_projects() -> None:
    """Groovy and Kotlin DSL fixtures are self-contained apart from locked dependencies."""

    required = (
        "gradlew",
        "gradlew.bat",
        "gradle/wrapper/gradle-wrapper.jar",
        "gradle/wrapper/gradle-wrapper.properties",
        "gradle.properties",
        "pyproject.toml",
        "config/checkstyle/checkstyle.xml",
        "config/pmd/pmd.xml",
        "config/spotbugs/baseline.xml",
        "src/main/java/example/Calculator.java",
        "src/test/java/example/CalculatorTest.java",
    )
    for dsl, build_file, settings_file in (
        ("groovy", "build.gradle", "settings.gradle"),
        ("kotlin", "build.gradle.kts", "settings.gradle.kts"),
    ):
        fixture = JAVA_LIVE_FIXTURES / dsl
        for relative in (*required, build_file, settings_file):
            assert (fixture / relative).is_file(), f"missing {dsl}/{relative}"
        properties = (fixture / "gradle/wrapper/gradle-wrapper.properties").read_text(
            encoding="utf-8"
        )
        assert "gradle-9.6.1-bin.zip" in properties
        assert "distributionSha256Sum=" in properties


def test_live_java_fixtures_exercise_native_ratchets_and_xml_reports() -> None:
    """Live projects wire every native tool used by grouped verification."""

    for dsl, build_file in (("groovy", "build.gradle"), ("kotlin", "build.gradle.kts")):
        fixture = JAVA_LIVE_FIXTURES / dsl
        build = (fixture / build_file).read_text(encoding="utf-8")
        config = (fixture / "pyproject.toml").read_text(encoding="utf-8")

        assert "com.diffplug.spotless" in build
        assert "com.github.spotbugs" in build
        assert "ratchetFrom" in build
        assert "agent-maintainer-live-base" in build
        assert "baselineFile" in build
        assert "xml.required" in build
        assert 'spotless_ratchet_ref = "agent-maintainer-live-base"' in config
        assert 'jacoco_ratchet_ref = "agent-maintainer-live-base"' in config
        for task in (
            "spotlessCheck",
            "spotbugsMain",
            "checkstyleMain",
            "pmdMain",
            "test",
            "jacocoTestReport",
            "jacocoTestCoverageVerification",
        ):
            assert task in config


# docsync:evidence.end evidence.java.live_workflow_tests
