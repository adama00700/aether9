"""Tests for Aether-9 Parser"""
import pytest
from aether9.compiler import (
    Lexer, Parser, ParseError,
    ProgramNode, ArrayNode, LatticeNode, AssignNode,
    ReturnNode, IfNode, ForNode, WhileNode, CallNode,
    BinOpNode, NumberNode, IdentNode, StringNode,
)


def parse(src):
    return Parser(Lexer(src).tokenize()).parse()


def body(src):
    return parse(src).body


class TestArrays:
    def test_simple(self):
        nodes = body("data = [54, 36, 72]")
        assert len(nodes) == 1
        assert isinstance(nodes[0], ArrayNode)
        assert nodes[0].name == "data"
        assert nodes[0].elements == [54, 36, 72]

    def test_empty(self):
        nodes = body("data = []")
        assert isinstance(nodes[0], ArrayNode)
        assert nodes[0].elements == []

    def test_single_element(self):
        nodes = body("data = [9]")
        assert nodes[0].elements == [9]


class TestAssignment:
    def test_number(self):
        nodes = body("x = 42")
        assert isinstance(nodes[0], AssignNode)
        assert nodes[0].name == "x"
        assert isinstance(nodes[0].value, NumberNode)

    def test_expression(self):
        nodes = body("x = a + b")
        assert isinstance(nodes[0], AssignNode)
        assert isinstance(nodes[0].value, BinOpNode)

    def test_string(self):
        nodes = body('label = "hello"')
        assert isinstance(nodes[0], AssignNode)
        assert isinstance(nodes[0].value, StringNode)
        assert nodes[0].value.value == "hello"


class TestLattice:
    def test_uses_binding(self):
        src = "data = [54]\nlattice fn(x) uses data:\n    return x\n"
        nodes = body(src)
        lattice = next(n for n in nodes if isinstance(n, LatticeNode))
        assert lattice.name == "fn"
        assert lattice.params == ["x"]
        assert lattice.binding == "data"

    def test_pure_binding(self):
        src = "lattice fn(x) pure:\n    return x\n"
        nodes = body(src)
        assert nodes[0].binding is None

    def test_no_binding_raises(self):
        with pytest.raises(ParseError):
            parse("lattice fn(x):\n    return x\n")

    def test_multi_param(self):
        src = "data = [9]\nlattice fn(a, b, c) uses data:\n    return a\n"
        nodes = body(src)
        lattice = next(n for n in nodes if isinstance(n, LatticeNode))
        assert lattice.params == ["a", "b", "c"]

    def test_body_return(self):
        src = "data = [9]\nlattice fn(x) uses data:\n    return x\n"
        nodes = body(src)
        lattice = next(n for n in nodes if isinstance(n, LatticeNode))
        assert isinstance(lattice.body[0], ReturnNode)


class TestControlFlow:
    def test_if_only(self):
        src = "data = [9]\nlattice fn(x) uses data:\n    if x == 9:\n        return 9\n    return x\n"
        nodes = body(src)
        lattice = next(n for n in nodes if isinstance(n, LatticeNode))
        assert isinstance(lattice.body[0], IfNode)
        assert lattice.body[0].else_body == []

    def test_if_else(self):
        src = (
            "data = [9]\n"
            "lattice fn(x) uses data:\n"
            "    if x == 9:\n"
            "        return 9\n"
            "    else:\n"
            "        return x\n"
        )
        nodes = body(src)
        lattice = next(n for n in nodes if isinstance(n, LatticeNode))
        assert isinstance(lattice.body[0], IfNode)
        assert len(lattice.body[0].else_body) > 0

    def test_for_loop(self):
        src = "data = [9]\nlattice fn(a, b) uses data:\n    for item in data:\n        return item\n"
        nodes = body(src)
        lattice = next(n for n in nodes if isinstance(n, LatticeNode))
        assert isinstance(lattice.body[0], ForNode)
        assert lattice.body[0].var == "item"
        assert lattice.body[0].iterable == "data"

    def test_while_loop(self):
        src = (
            "data = [9]\n"
            "lattice fn(x) uses data:\n"
            "    while x < 9:\n"
            "        x = x + 1\n"
            "    return x\n"
        )
        nodes = body(src)
        lattice = next(n for n in nodes if isinstance(n, LatticeNode))
        assert isinstance(lattice.body[0], WhileNode)


class TestExpressions:
    def test_binop_add(self):
        nodes = body("x = a + b")
        assert nodes[0].value.op == "+"

    def test_binop_percent(self):
        nodes = body("x = a % 9")
        assert nodes[0].value.op == "%"

    def test_comparison_eq(self):
        nodes = body("x = a == b")
        assert nodes[0].value.op == "=="

    def test_and_or(self):
        nodes = body("x = a and b or c")
        assert isinstance(nodes[0].value, BinOpNode)

    def test_call(self):
        nodes = body("x = fn(54, 36)")
        call = nodes[0].value
        assert isinstance(call, CallNode)
        assert call.func == "fn"
        assert len(call.args) == 2

    def test_nested_call(self):
        nodes = body("x = f(g(9))")
        outer = nodes[0].value
        assert isinstance(outer, CallNode)
        assert isinstance(outer.args[0], CallNode)
