"""Tests for Aether-9 Sandbox — isolated execution"""
import pytest
from aether9.sandbox import Sandbox, guard_check, ASTGuardError, ExecutionPolicy


class TestASTGuard:
    def test_clean_code_passes(self):
        guard_check("x = 9\nprint(x)\n")  # no error

    def test_import_blocked(self):
        with pytest.raises(ASTGuardError, match="import"):
            guard_check("import os\n")

    def test_from_import_blocked(self):
        with pytest.raises(ASTGuardError):
            guard_check("from os import path\n")

    def test_eval_blocked(self):
        with pytest.raises(ASTGuardError, match="eval"):
            guard_check("eval('9+9')\n")

    def test_exec_blocked(self):
        with pytest.raises(ASTGuardError, match="exec"):
            guard_check("exec('x=9')\n")

    def test_open_blocked(self):
        with pytest.raises(ASTGuardError, match="open"):
            guard_check("open('file.txt')\n")

    def test_dunder_blocked(self):
        with pytest.raises(ASTGuardError):
            guard_check("x = ().__class__.__subclasses__()\n")


class TestSandbox:
    def setup_method(self):
        self.s = Sandbox(timeout=5)

    def test_basic_execution(self):
        r = self.s.run("print('hello')\n")
        assert r.success
        assert "hello" in r.stdout

    def test_arithmetic(self):
        r = self.s.run("x = 9 * 9\nprint(x)\n")
        assert r.success
        assert "81" in r.stdout

    def test_import_blocked_at_runtime(self):
        r = self.s.run("import os\nprint(os.getcwd())\n")
        assert not r.success

    def test_timeout(self):
        s = Sandbox(timeout=1)
        r = s.run("while True: pass\n")
        assert r.timed_out
        assert not r.success

    def test_stdout_captured(self):
        r = self.s.run("print('aether9')\nprint('secure')\n")
        assert "aether9" in r.stdout
        assert "secure" in r.stdout

    def test_runtime_error_captured(self):
        r = self.s.run("raise RuntimeError('test error')\n")
        assert not r.success

    def test_subprocess_flag_I(self):
        """Python -I flag بيعزل الـ sys.path."""
        r = self.s.run("import sys\nprint(sys.flags.isolated)\n")
        assert not r.success  # import blocked before even reaching this


class TestPolicyLayer:
    def test_default_policy_blocks_write(self):
        s = Sandbox()
        r = s.run("_safe_write('evil.txt', 9)\n")
        assert not r.success

    def test_policy_allows_specific_file(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = ExecutionPolicy(allow_write=["out.txt"])
            s = Sandbox(workdir=d, policy=p)
            r = s.run("_safe_write('out.txt', 9)\nprint('ok')\n")
            assert r.success

    def test_policy_blocks_unlisted_file(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = ExecutionPolicy(allow_write=["out.txt"])
            s = Sandbox(workdir=d, policy=p)
            r = s.run("_safe_write('other.txt', 9)\n")
            assert not r.success

    def test_policy_file_roundtrip(self):
        import tempfile, os
        p = ExecutionPolicy(allow_write=["report.txt"], max_runtime=20)
        with tempfile.NamedTemporaryFile(suffix=".a9policy",
                                         delete=False) as f:
            path = f.name
        try:
            p.to_file(path)
            p2 = ExecutionPolicy.from_file(path)
            assert p2.allow_write == ["report.txt"]
            assert p2.max_runtime == 20
        finally:
            os.unlink(path)

    def test_type_constructor_blocked(self):
        s = Sandbox()
        r = s.run("x = type('Evil', (), {})()\n")
        assert not r.success
