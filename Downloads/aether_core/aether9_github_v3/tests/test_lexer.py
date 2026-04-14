"""Tests for Aether-9 Lexer"""
import pytest
from aether9.compiler import Lexer, TT, LexError


def tokens(src):
    return [(t.type, t.value) for t in Lexer(src).tokenize()
            if t.type != TT.EOF]


class TestNumbers:
    def test_positive(self):
        result = tokens("42")
        assert (TT.NUMBER, 42) in result

    def test_negative(self):
        result = tokens("-9")
        assert (TT.NUMBER, -9) in result

    def test_zero(self):
        result = tokens("0")
        assert (TT.NUMBER, 0) in result


class TestStrings:
    def test_double_quoted(self):
        result = tokens('"hello"')
        assert (TT.STRING, "hello") in result

    def test_single_quoted(self):
        result = tokens("'world'")
        assert (TT.STRING, "world") in result

    def test_empty_string(self):
        result = tokens('""')
        assert (TT.STRING, "") in result


class TestKeywords:
    def test_lattice(self):   assert (TT.LATTICE, "lattice") in tokens("lattice")
    def test_uses(self):      assert (TT.USES,    "uses")    in tokens("uses")
    def test_pure(self):      assert (TT.PURE,    "pure")    in tokens("pure")
    def test_return(self):    assert (TT.RETURN,  "return")  in tokens("return")
    def test_if(self):        assert (TT.IF,      "if")      in tokens("if")
    def test_else(self):      assert (TT.ELSE,    "else")    in tokens("else")
    def test_for(self):       assert (TT.FOR,     "for")     in tokens("for")
    def test_in(self):        assert (TT.IN,      "in")      in tokens("in")
    def test_while(self):     assert (TT.WHILE,   "while")   in tokens("while")
    def test_and(self):       assert (TT.AND,     "and")     in tokens("and")
    def test_or(self):        assert (TT.OR,      "or")      in tokens("or")


class TestOperators:
    def test_comparison(self):
        ts = tokens("a == b != c <= d >= e < f > g")
        types = [t for t, _ in ts]
        assert TT.EQ  in types
        assert TT.NEQ in types
        assert TT.LTE in types
        assert TT.GTE in types
        assert TT.LT  in types
        assert TT.GT  in types

    def test_arithmetic(self):
        ts = tokens("a + b - c * d / e % f")
        types = [t for t, _ in ts]
        assert TT.PLUS    in types
        assert TT.MINUS   in types
        assert TT.STAR    in types
        assert TT.SLASH   in types
        assert TT.PERCENT in types


class TestIndentation:
    def test_indent_dedent(self):
        src = "if x:\n    return 9\n"
        types = [t for t, _ in tokens(src)]
        assert TT.INDENT in types
        assert TT.DEDENT in types

    def test_comment_ignored(self):
        result = tokens("# this is a comment\nx = 9")
        types = [t for t, _ in result]
        assert TT.IDENT in types
        assert TT.NUMBER in types


class TestErrors:
    def test_bad_character(self):
        with pytest.raises(LexError):
            tokens("x @ y")

    def test_bad_character_message(self):
        with pytest.raises(LexError, match="unexpected character"):
            tokens("x @ y")
