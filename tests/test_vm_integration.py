"""Integration tests for Aether-9 bytecode VM."""
import io
import os
import tempfile
from contextlib import redirect_stdout

import pytest

from aether9.vm import (
    AetherVM,
    Bytecode,
    Instruction,
    Op,
    VMError,
    VMSecurityError,
    compile_to_bytecode,
)


def run_source(src):
    bc, registry = compile_to_bytecode(src)
    vm = AetherVM()
    with redirect_stdout(io.StringIO()) as out:
        result = vm.run(bc)
    return bc, registry, vm, out.getvalue(), result


class TestBytecodeEndToEnd:
    def test_basic_lattice_result(self):
        _, _, vm, _, _ = run_source(
            "data = [54, 36, 72]\n"
            "lattice fn(x) uses data:\n"
            "    return (x + 9) % 9 or 9\n"
            "result = fn(54)\n"
        )
        assert vm.ns["result"] == 9

    def test_if_else_bytecode(self):
        _, _, vm, _, _ = run_source(
            "data = [54]\n"
            "lattice fn(x) uses data:\n"
            "    if x == 54:\n"
            "        return 9\n"
            "    else:\n"
            "        return x\n"
            "result = fn(54)\n"
        )
        assert vm.ns["result"] == 9

    def test_while_bytecode(self):
        _, _, vm, _, _ = run_source(
            "data = [9]\n"
            "lattice count(x) uses data:\n"
            "    i = 0\n"
            "    while i < 9:\n"
            "        i = i + 1\n"
            "    return i % 9 or 9\n"
            "result = count(9)\n"
        )
        assert vm.ns["result"] == 9

    def test_for_bytecode(self):
        _, _, vm, _, _ = run_source(
            "data = [9, 18, 27]\n"
            "lattice total(a, b) uses data:\n"
            "    acc = 0\n"
            "    for item in data:\n"
            "        acc = acc + item\n"
            "    return acc % 9 or 9\n"
            "result = total(9, 9)\n"
        )
        assert vm.ns["result"] == 9

    def test_nested_lattice_bytecode(self):
        _, _, vm, _, _ = run_source(
            "data = [54, 36]\n"
            "lattice step1(x) uses data:\n"
            "    return (x + 9) % 9 or 9\n"
            "lattice step2(x) uses data:\n"
            "    return step1(x) % 9 or 9\n"
            "result = step2(54)\n"
        )
        assert vm.ns["data"] == [54, 36]
        assert vm.ns["result"] == 9

    def test_save_load_preserves_two_element_arrays(self):
        bc, _, _, _, _ = run_source(
            "data = [54, 36]\n"
            "lattice fn(x) uses data:\n"
            "    return (x + 9) % 9 or 9\n"
            "result = fn(54)\n"
        )
        with tempfile.NamedTemporaryFile(suffix=".a9b", delete=False) as f:
            path = f.name
        try:
            bc.save(path)
            loaded = Bytecode.load(path)
            vm = AetherVM()
            vm.run(loaded)
            assert vm.ns["data"] == [54, 36]
            assert isinstance(vm.ns["data"], list)
            assert vm.ns["result"] == 9
        finally:
            os.unlink(path)

    def test_print_output_is_captured(self):
        _, _, _, stdout, _ = run_source('print("aether9", 9)\n')
        assert "aether9 9" in stdout


class TestVMHardening:
    def test_unary_neg_opcode(self):
        bc = Bytecode(
            instructions=[
                Instruction(Op.LOAD_CONST, 9),
                Instruction(Op.UNARY_NEG),
                Instruction(Op.STORE_NAME, "x"),
                Instruction(Op.HALT),
            ],
            functions={},
            func_seals={},
            registry={},
        )
        vm = AetherVM()
        vm.run(bc)
        assert vm.ns["x"] == -9

    def test_stack_underflow_is_clear_vmerror(self):
        bc = Bytecode(
            instructions=[Instruction(Op.POP), Instruction(Op.HALT)],
            functions={},
            func_seals={},
            registry={},
        )
        with pytest.raises(VMError, match="stack underflow"):
            AetherVM().run(bc)

    def test_unknown_comparison_operator_rejected(self):
        bc = Bytecode(
            instructions=[
                Instruction(Op.LOAD_CONST, 1),
                Instruction(Op.LOAD_CONST, 2),
                Instruction(Op.COMPARE, "<=>"),
                Instruction(Op.HALT),
            ],
            functions={},
            func_seals={},
            registry={},
        )
        with pytest.raises(VMError, match="unknown comparison op"):
            AetherVM().run(bc)

    def test_tampered_lattice_seal_fails(self):
        bc, _, _, _, _ = run_source(
            "data = [54, 36, 72]\n"
            "lattice fn(x) uses data:\n"
            "    return (x + 9) % 9 or 9\n"
            "result = fn(54)\n"
        )
        data, raw = bc.func_seals["fn"]
        bc.func_seals["fn"] = ([55, 36, 72], raw)
        with pytest.raises(VMSecurityError, match="Vortex tampered"):
            AetherVM().run(bc)
