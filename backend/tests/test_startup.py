"""Check the real module entry point in a clean, dataset-free subprocess."""

import os
import subprocess
import sys
from pathlib import Path


def test_fresh_process_import_and_startup_are_offline(tmp_path: Path) -> None:
    tests_directory = Path(__file__).resolve().parent
    project_root = tests_directory.parents[1]
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.upper().startswith(("OCEAN_", "COPERNICUSMARINE_"))
    }
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            str(tests_directory / "startup_probe.py"),
            str(project_root),
        ],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "without scientific imports" in result.stdout
    assert list(tmp_path.iterdir()) == []
