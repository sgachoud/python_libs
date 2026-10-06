"""Ensure incorrect consumer code is rejected by the inline annotations."""

import json
from pathlib import Path
import subprocess
import sys

import metacore
from observable import observable as implementation


def test_typing_rejects_incorrect_defaults_writes_reads_and_callbacks(tmp_path):
    text = (Path(__file__).parent / "typing/invalid.py.txt").read_text(encoding="utf-8")
    sample = tmp_path / "invalid.py"
    sample.write_text(text, encoding="utf-8")
    config = tmp_path / "pyrightconfig.json"
    config.write_text(
        json.dumps(
            {
                "typeCheckingMode": "standard",
                "pythonVersion": "3.13",
                "extraPaths": [
                    str(Path(implementation.__file__).resolve().parents[1]),
                    str(Path(metacore.__file__).resolve().parents[1]),
                ],
            }
        ),
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pyright",
            "--project",
            str(config),
            "--pythonpath",
            sys.executable,
            "--outputjson",
            str(sample),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    diagnostics = json.loads(result.stdout)
    errors = [
        item
        for item in diagnostics["generalDiagnostics"]
        if item["severity"] == "error"
    ]
    expected_lines = {
        index
        for index, line in enumerate(text.splitlines())
        if "# expected-error" in line
    }
    assert result.returncode == 1, result.stdout + result.stderr
    assert {item["range"]["start"]["line"] for item in errors} == expected_lines, errors
    assert len(errors) == len(expected_lines), errors
    assert diagnostics["summary"]["warningCount"] == 0, diagnostics
