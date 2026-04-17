"""Tests for Aether-9 Compiler — end-to-end compilation"""
import pytest
from aether9.compiler import Aether9Compiler, CompileError, ParseError, LexError


def compile_and_run(src):
    """Compile source and execute, returning namespace."""
    code, _ = Aether9Compiler().compile(src)
    ns = {}
    exec(compile(code, "<test>", "exec"), ns)
    return ns


def run(src):
    """Shortcut: compile, run, return namespace."""
    return compile_and_run(src)


class TestBasicExecution:
    def test_array_and_assign(self):
        ns = run("data = [54, 36, 72]\nx = 9\n")
        assert ns["data"] == [54, 36, 72]
        assert ns["x"] == 9

    def test_lattice_pure(self):
        ns = run(
            "data = [54, 36]\n"
            "lattice double(x) pure:\n"
            "    return (x * 2) % 9 or 9\n"
            "result = double(9)\n"
        )
        assert ns["result"] == 9

    def test_lattice_uses(self):
        ns = run(
            "data = [54, 36, 72]\n"
            "lattice fn(x) uses data:\n"
            "    return (x + 9) % 9 or 9\n"
            "result = fn(54)\n"
        )
        assert ns["result"] == 9


class TestControlFlow:
    def test_if_true_branch(self):
        ns = run(
            "data = [54]\n"
            "lattice fn(x) uses data:\n"
            "    if x == 54:\n"
            "        return 9\n"
            "    else:\n"
            "        return x\n"
            "result = fn(54)\n"
        )
        assert ns["result"] == 9

    def test_if_false_branch(self):
        ns = run(
            "data = [54]\n"
            "lattice fn(x) uses data:\n"
            "    if x == 0:\n"
            "        return 0\n"
            "    else:\n"
            "        return 9\n"
            "result = fn(54)\n"
        )
        assert ns["result"] == 9

    def test_for_accumulates(self):
        ns = run(
            "data = [9, 18, 27]\n"
            "lattice total(a, b) uses data:\n"
            "    acc = 0\n"
            "    for item in data:\n"
            "        acc = acc + item\n"
            "    return acc % 9 or 9\n"
            "result = total(9, 9)\n"
        )
        assert ns["result"] == 9

    def test_while_loop(self):
        ns = run(
            "data = [9]\n"
            "lattice count(x) uses data:\n"
            "    i = 0\n"
            "    while i < 9:\n"
            "        i = i + 1\n"
            "    return i % 9 or 9\n"
            "result = count(9)\n"
        )
        assert ns["result"] == 9

    def test_while_and_condition(self):
        ns = run(
            "data = [9]\n"
            "lattice fn(x) uses data:\n"
            "    i = 0\n"
            "    total = 0\n"
            "    while i < 9 and total < 81:\n"
            "        total = total + 9\n"
            "        i = i + 1\n"
            "    return total % 9 or 9\n"
            "result = fn(9)\n"
        )
        assert ns["result"] == 9


class TestNestedCalls:
    def test_two_level(self):
        ns = run(
            "data = [54, 36]\n"
            "lattice step1(x) uses data:\n"
            "    return (x + 9) % 9 or 9\n"
            "lattice step2(x) uses data:\n"
            "    return step1(x) % 9 or 9\n"
            "result = step2(54)\n"
        )
        assert ns["result"] == 9

    def test_three_level(self):
        ns = run(
            "data = [9, 18, 27]\n"
            "lattice a(x) uses data:\n"
            "    return (x + 9) % 9 or 9\n"
            "lattice b(x) uses data:\n"
            "    return a(x) % 9 or 9\n"
            "lattice c(x) uses data:\n"
            "    return b(x) % 9 or 9\n"
            "result = c(9)\n"
        )
        assert ns["result"] == 9

    def test_forward_ref_raises(self):
        with pytest.raises(CompileError, match="before it is defined"):
            Aether9Compiler().compile(
                "data = [9]\n"
                "lattice compute(x) uses data:\n"
                "    return helper(x)\n"
                "lattice helper(x) uses data:\n"
                "    return x % 9 or 9\n"
            )


class TestStdlib:
    def test_dr(self):
        ns = run("data = [9]\nlattice fn(x) uses data:\n    return dr(x) or 9\nresult = fn(9)\n")
        assert ns["result"] == 9

    def test_abs(self):
        ns = run("x = abs(9)\n")
        assert ns["x"] == 9

    def test_min_max(self):
        ns = run("a = min(54, 36)\nb = max(54, 36)\n")
        assert ns["a"] == 36
        assert ns["b"] == 54

    def test_mod(self):
        ns = run("x = mod(54, 9)\n")
        assert ns["x"] == 9

    def test_len(self):
        ns = run('x = len("aether")\n')
        assert ns["x"] == 6

    def test_str(self):
        ns = run("x = str(9)\n")
        assert ns["x"] == "9"

    def test_concat(self):
        ns = run('x = concat("a", "9")\n')
        assert ns["x"] == "a9"


class TestErrors:
    def test_lex_error(self):
        with pytest.raises(LexError):
            Aether9Compiler().compile("data = [9]\nx @ y\n")

    def test_undefined_array(self):
        with pytest.raises(CompileError, match="not defined"):
            Aether9Compiler().compile(
                "lattice fn(x) uses ghost:\n    return x\n"
            )

    def test_missing_binding(self):
        with pytest.raises(ParseError):
            Aether9Compiler().compile(
                "lattice fn(x):\n    return x\n"
            )

    def test_lattice_asymmetry_at_runtime(self):
        """Lattice that returns non-resonant value raises RuntimeError."""
        code, _ = Aether9Compiler().compile(
            "data = [54]\n"
            "lattice bad(x) uses data:\n"
            "    return x + 1\n"
        )
        ns = {}
        exec(compile(code, "<test>", "exec"), ns)
        with pytest.raises(RuntimeError, match="Lattice asymmetry"):
            ns["bad"](54)
