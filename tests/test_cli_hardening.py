"""Stage 3 CLI hardening tests for Aether-9."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
SITE = Path("/opt/pyvenv/lib/python3.13/site-packages")


def run_cli(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(SRC), str(SITE)])
    return subprocess.run(
        [sys.executable, "-S", "-m", "aether9.cli", *args],
        cwd=tmp_path,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=10,
    )


def write_program(tmp_path: Path) -> Path:
    program = tmp_path / "program.a9"
    program.write_text(
        "data = [54, 36]\n"
        "lattice fn(x) uses data:\n"
        "    print(\"cli-stage3\")\n"
        "    return (x + 9) % 9 or 9\n"
        "result = fn(54)\n"
        "print(result)\n",
        encoding="utf-8",
    )
    return program


def test_compile_creates_python_and_signature(tmp_path: Path):
    program = write_program(tmp_path)

    result = run_cli(tmp_path, "compile", str(program.name))

    assert result.returncode == 0, result.stderr
    assert "compiled python" in result.stdout
    assert (tmp_path / "program.py").exists()
    assert (tmp_path / "program.a9s").exists()


def test_verify_source_signature_after_compile(tmp_path: Path):
    program = write_program(tmp_path)
    assert run_cli(tmp_path, "compile", program.name).returncode == 0

    result = run_cli(tmp_path, "verify", program.name)

    assert result.returncode == 0, result.stderr
    assert "signature valid" in result.stdout


def test_export_json_creates_a9b_and_preserves_two_element_array(tmp_path: Path):
    program = write_program(tmp_path)

    result = run_cli(tmp_path, "export", program.name, "--format", "json")

    assert result.returncode == 0, result.stderr
    assert "bytecode container" in result.stdout
    a9b = tmp_path / "program.a9b"
    assert a9b.exists()
    data = json.loads(a9b.read_text(encoding="utf-8"))
    assert data["instructions"][0] == {"op": "LOAD_CONST", "arg": [54, 36]}


def test_verify_a9b_structure(tmp_path: Path):
    program = write_program(tmp_path)
    assert run_cli(tmp_path, "export", program.name).returncode == 0

    result = run_cli(tmp_path, "verify", "program.a9b")

    assert result.returncode == 0, result.stderr
    assert "bytecode structure valid" in result.stdout


def test_inspect_a9b_reports_bytecode_metadata(tmp_path: Path):
    program = write_program(tmp_path)
    assert run_cli(tmp_path, "export", program.name).returncode == 0

    result = run_cli(tmp_path, "inspect", "program.a9b")

    assert result.returncode == 0, result.stderr
    assert "Aether-9 Bytecode" in result.stdout
    assert "functions" in result.stdout
    assert "sealed" in result.stdout


def test_disasm_a9b_outputs_instruction_stream(tmp_path: Path):
    program = write_program(tmp_path)
    assert run_cli(tmp_path, "export", program.name).returncode == 0

    result = run_cli(tmp_path, "disasm", "program.a9b")

    assert result.returncode == 0, result.stderr
    assert "=== main ===" in result.stdout
    assert "CALL_FUNC" in result.stdout
    assert "=== fn [sealed] ===" in result.stdout


def test_run_source_defaults_to_vm_backend(tmp_path: Path):
    program = write_program(tmp_path)

    result = run_cli(tmp_path, "run", program.name)

    assert result.returncode == 0, result.stderr
    assert "[vm backend]" in result.stdout
    assert "cli-stage3" in result.stdout
    assert "\n9\n" in result.stdout


def test_run_a9b_bytecode(tmp_path: Path):
    program = write_program(tmp_path)
    assert run_cli(tmp_path, "export", program.name).returncode == 0

    result = run_cli(tmp_path, "run", "program.a9b")

    assert result.returncode == 0, result.stderr
    assert "running bytecode" in result.stdout
    assert "cli-stage3" in result.stdout
    assert "\n9\n" in result.stdout


def test_export_binary_creates_a9b_magic_bytes(tmp_path: Path):
    program = write_program(tmp_path)

    result = run_cli(tmp_path, "export", program.name, "--format", "binary")

    assert result.returncode == 0, result.stderr
    assert "A9B9 binary" in result.stdout
    a9b = tmp_path / "program.a9b"
    assert a9b.exists()
    assert a9b.read_bytes()[:4] == b"A9B9"


def test_verify_rejects_tampered_a9b_call_target(tmp_path: Path):
    program = write_program(tmp_path)
    assert run_cli(tmp_path, "export", program.name).returncode == 0
    a9b = tmp_path / "program.a9b"
    data = json.loads(a9b.read_text(encoding="utf-8"))
    data["instructions"][4]["arg"] = ["ghost", 1]
    a9b.write_text(json.dumps(data), encoding="utf-8")

    result = run_cli(tmp_path, "verify", "program.a9b")

    assert result.returncode == 1
    assert "undefined lattice" in result.stderr
