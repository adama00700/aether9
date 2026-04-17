"""Stage 4 binary .a9b format tests for Aether-9."""

from __future__ import annotations

import io
import os
import subprocess
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest

from aether9.vm import AetherVM, Bytecode, VMError, compile_to_bytecode


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
SITE = Path("/opt/pyvenv/lib/python3.13/site-packages")


def sample_source() -> str:
    return (
        "data = [54, 36]\n"
        "lattice fn(x) uses data:\n"
        "    print(\"stage4-binary\")\n"
        "    return (x + 9) % 9 or 9\n"
        "result = fn(54)\n"
        "print(result)\n"
    )


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
    program.write_text(sample_source(), encoding="utf-8")
    return program


def test_binary_save_load_preserves_semantics_and_magic(tmp_path: Path):
    bc, _ = compile_to_bytecode(sample_source())
    out = tmp_path / "program.a9b"

    bc.save(str(out), format="binary")

    assert out.read_bytes()[:4] == b"A9B9"
    assert Bytecode.detect_format(str(out)) == "binary"
    loaded = Bytecode.load(str(out))
    vm = AetherVM(workdir=str(tmp_path))
    with redirect_stdout(io.StringIO()) as stdout:
        vm.run(loaded)
    assert vm.ns["data"] == [54, 36]
    assert isinstance(vm.ns["data"], list)
    assert vm.ns["result"] == 9
    assert "stage4-binary" in stdout.getvalue()


def test_json_save_load_remains_backward_compatible(tmp_path: Path):
    bc, _ = compile_to_bytecode(sample_source())
    out = tmp_path / "program-json.a9b"

    bc.save(str(out), format="json")

    assert out.read_bytes()[:4] != b"A9B9"
    assert Bytecode.detect_format(str(out)) == "json"
    loaded = Bytecode.load(str(out))
    vm = AetherVM(workdir=str(tmp_path))
    vm.run(loaded)
    assert vm.ns["data"] == [54, 36]
    assert vm.ns["result"] == 9


def test_truncated_binary_container_is_rejected(tmp_path: Path):
    bad = tmp_path / "bad.a9b"
    bad.write_bytes(b"A9B9\x00")

    with pytest.raises(VMError, match="truncated"):
        Bytecode.load(str(bad))


def test_cli_binary_export_verify_inspect_disasm_and_run(tmp_path: Path):
    program = write_program(tmp_path)

    exported = run_cli(tmp_path, "export", program.name, "--format", "binary")
    assert exported.returncode == 0, exported.stderr
    assert "A9B9 binary" in exported.stdout
    assert (tmp_path / "program.a9b").read_bytes()[:4] == b"A9B9"

    verified = run_cli(tmp_path, "verify", "program.a9b")
    assert verified.returncode == 0, verified.stderr
    assert "bytecode structure valid" in verified.stdout
    assert "format      : binary" in verified.stdout

    inspected = run_cli(tmp_path, "inspect", "program.a9b")
    assert inspected.returncode == 0, inspected.stderr
    assert "Aether-9 Bytecode" in inspected.stdout
    assert "format       binary" in inspected.stdout

    disassembled = run_cli(tmp_path, "disasm", "program.a9b")
    assert disassembled.returncode == 0, disassembled.stderr
    assert "=== main ===" in disassembled.stdout
    assert "CALL_FUNC" in disassembled.stdout

    ran = run_cli(tmp_path, "run", "program.a9b")
    assert ran.returncode == 0, ran.stderr
    assert "running bytecode" in ran.stdout
    assert "stage4-binary" in ran.stdout
    assert "\n9\n" in ran.stdout
