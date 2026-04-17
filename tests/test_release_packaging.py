from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_release_version():
    import aether9
    assert aether9.__version__ == "3.3.0"


def test_binary_cli_smoke(tmp_path: Path):
    src = tmp_path / "program.a9"
    src.write_text(
        'data = [54, 36]\n'
        'lattice fn(x) uses data:\n'
        '    print("release-smoke")\n'
        '    return (x + 9) % 9 or 9\n'
        'result = fn(54)\n'
        'print(result)\n',
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([
        str(Path(__file__).resolve().parents[1] / "src"),
        env.get("PYTHONPATH", ""),
    ])
    export = subprocess.run(
        [sys.executable, "-S", "-m", "aether9.cli", "export", src.name, "--format", "binary"],
        cwd=tmp_path,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=10,
    )
    assert export.returncode == 0, export.stderr
    assert (tmp_path / "program.a9b").read_bytes()[:4] == b"A9B9"
    run = subprocess.run(
        [sys.executable, "-S", "-m", "aether9.cli", "run", "program.a9b"],
        cwd=tmp_path,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=10,
    )
    assert run.returncode == 0, run.stderr
    assert "release-smoke" in run.stdout
    assert "\n9\n" in run.stdout
