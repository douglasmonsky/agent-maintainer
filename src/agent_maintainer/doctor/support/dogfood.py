"""Doctor checks for source-checkout dogfooding."""

from __future__ import annotations

import shutil
import subprocess  # nosec B404
from pathlib import Path

from agent_maintainer.doctor.support import models as maintainer_doctor_models

DoctorResult = maintainer_doctor_models.DoctorResult
OK = maintainer_doctor_models.OK
WARNING = maintainer_doctor_models.WARNING

CONSOLE_SCRIPT = "agent-maintainer"


def check_console_script_dogfood(repo_root: Path) -> DoctorResult:
    """Report whether console script imports local checkout code."""

    expected = repo_root / "src" / "agent_maintainer" / "__init__.py"
    if not expected.exists():
        return DoctorResult(
            "dogfood-console-script",
            OK,
            "No local src/agent_maintainer package.",
            state=maintainer_doctor_models.NOT_APPLICABLE,
        )
    script = shutil.which(CONSOLE_SCRIPT)
    if script is None:
        return DoctorResult(
            "dogfood-console-script",
            OK,
            "agent-maintainer console script not on PATH; module command is canonical.",
            state=maintainer_doctor_models.NOT_APPLICABLE,
        )
    resolved = console_script_import_path(Path(script))
    if resolved is None:
        return DoctorResult(
            "dogfood-console-script",
            WARNING,
            f"Cannot inspect {script} import target.",
            state=maintainer_doctor_models.MISSING,
            hint="Use PYTHONPATH=src python3 -m agent_maintainer in this checkout.",
        )
    if resolved == expected.resolve():
        return DoctorResult(
            "dogfood-console-script",
            OK,
            "agent-maintainer console script imports local src/agent_maintainer.",
        )
    return DoctorResult(
        "dogfood-console-script",
        WARNING,
        f"agent-maintainer console script imports {resolved}; expected {expected.resolve()}.",
        state=maintainer_doctor_models.UNSAFE_CONFIG,
        hint="Run python -m pip install -e .",
    )


def console_script_import_path(script_path: Path) -> Path | None:
    """Return package import path used by console script interpreter."""

    python_path = console_script_python(script_path)
    if python_path is None:
        return None
    result = subprocess.run(  # nosec B603
        (
            python_path,
            "-c",
            (
                "import agent_maintainer, pathlib; "
                "print(pathlib.Path(agent_maintainer.__file__).resolve())"
            ),
        ),
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return Path(result.stdout.strip()).resolve()


def console_script_python(script_path: Path) -> str | None:
    """Return Python executable from console script shebang."""

    try:
        first_line = script_path.read_text(encoding="utf-8").splitlines()[0]
    except (IndexError, OSError, UnicodeDecodeError):
        return None
    if not first_line.startswith("#!"):
        return None
    python_path = first_line.removeprefix("#!").strip()
    return python_path if "python" in Path(python_path).name else None
