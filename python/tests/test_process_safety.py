"""Keep potentially fatal native-input regressions isolated from the test runner."""

import json
import subprocess
import sys
from pathlib import Path


def test_pathological_inputs_leave_the_installed_extension_usable():
    script = Path(__file__).resolve().parents[2] / "scripts" / "check_inputs.py"
    result = subprocess.run(
        [sys.executable, "-I", str(script), "--cases", "10000", "--seed", "76381"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    # PanicException derives from BaseException; it and process aborts must fail this check.
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["cases"] == report["accepted"] + report["documented_value_errors"] == 10_000
    assert report["large_cases"] == 7
    assert report["seed"] == 76381
