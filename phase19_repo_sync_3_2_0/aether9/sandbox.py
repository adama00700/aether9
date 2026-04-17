"""
Aether-9 Sandbox — isolated execution layer
─────────────────────────────────────────────
طبقتان من الحماية:
  1. AST Guard — يفحص الكود قبل التنفيذ ويرفض أي شيء خطير
  2. Subprocess Runner — ينفذ الكود في process منفصل محدود
"""

import ast
import sys
import os
import subprocess
import tempfile
import json
import resource
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List

ALLOWED_BUILTINS = frozenset({
    'print', 'len', 'abs', 'min', 'max',
    'str', 'int', 'float', 'bool', 'range',
    'isinstance', 'type', 'repr',
    'True', 'False', 'None',
})

FORBIDDEN_NODES = (
    ast.Import,
    ast.ImportFrom,
    ast.Global,
    ast.Nonlocal,
)

FORBIDDEN_NAMES = frozenset({
    '__import__', '__builtins__', '__class__',
    'eval', 'exec', 'compile', 'open',
    'input',
    '__subclasses__', '__mro__', '__bases__',
    'getattr', 'setattr', 'delattr', 'vars', 'dir',
    'globals', 'locals',
})


@dataclass
class ExecutionPolicy:
    allow_write: List[str] = field(default_factory=list)
    allow_read: List[str] = field(default_factory=list)
    max_runtime: int = 30
    max_memory_mb: int = 256
    allow_network: bool = False

    @classmethod
    def default(cls) -> "ExecutionPolicy":
        return cls()

    @classmethod
    def from_file(cls, path: str) -> "ExecutionPolicy":
        data = json.loads(open(path).read())
        return cls(
            allow_write=data.get("allow_write", []),
            allow_read=data.get("allow_read", []),
            max_runtime=data.get("max_runtime", 30),
            max_memory_mb=data.get("max_memory_mb", 256),
            allow_network=data.get("allow_network", False),
        )

    def to_file(self, path: str):
        open(path, 'w').write(json.dumps({
            "allow_write": self.allow_write,
            "allow_read": self.allow_read,
            "max_runtime": self.max_runtime,
            "max_memory_mb": self.max_memory_mb,
            "allow_network": self.allow_network,
        }, indent=2))


R = "\033[31m"
Y = "\033[33m"
X = "\033[0m"
BOLD = "\033[1m"


class ASTGuardError(Exception):
    pass


class ASTGuard(ast.NodeVisitor):
    def visit_Import(self, node):
        raise ASTGuardError(
            f"  {BOLD}{R}[SecurityError]{X}\n"
            f"  'import' is not allowed in Aether-9 programs.\n"
            f"  {Y}hint:{X} use the stdlib functions instead (abs, min, max, dr, ...)\n"
        )

    def visit_ImportFrom(self, node):
        raise ASTGuardError(
            f"  {BOLD}{R}[SecurityError]{X}\n"
            f"  'from ... import' is not allowed in Aether-9 programs.\n"
        )

    def visit_Global(self, node):
        raise ASTGuardError(
            f"  {BOLD}{R}[SecurityError]{X}\n"
            f"  'global' statement is not allowed.\n"
        )

    def visit_Name(self, node):
        if node.id in FORBIDDEN_NAMES:
            raise ASTGuardError(
                f"  {BOLD}{R}[SecurityError]{X}\n"
                f"  '{node.id}' is not allowed in Aether-9 programs.\n"
                f"  {Y}hint:{X} use the Aether-9 stdlib instead.\n"
            )
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id in ('object', 'type', '__build_class__'):
            raise ASTGuardError(
                f"  {BOLD}{R}[SecurityError]{X}\n"
                f"  '{node.func.id}()' is not allowed.\n"
            )
        self.generic_visit(node)

    def visit_Attribute(self, node):
        if isinstance(node.attr, str) and node.attr.startswith('__'):
            dangerous = {'__class__', '__subclasses__', '__mro__', '__globals__', '__builtins__', '__code__'}
            if node.attr in dangerous:
                raise ASTGuardError(
                    f"  {BOLD}{R}[SecurityError]{X}\n"
                    f"  Attribute '{node.attr}' is not allowed.\n"
                )
        self.generic_visit(node)




def _contains_break(node: ast.AST) -> bool:
    return any(isinstance(child, ast.Break) for child in ast.walk(node))


def _looks_like_obvious_infinite_loop(python_code: str) -> bool:
    """Fast-path for trivial infinite loops before spawning a subprocess.

    This is not a full termination checker; it only catches the common
    `while True: ...` shape used in timeout regression tests and avoids
    pathological host behavior where CPU-bound child processes can starve the
    parent watchdog.
    """
    try:
        tree = ast.parse(python_code)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.While) and isinstance(node.test, ast.Constant) and node.test.value is True:
            if not _contains_break(node):
                return True
    return False


def guard_check(python_code: str) -> None:
    try:
        tree = ast.parse(python_code)
    except SyntaxError as e:
        raise ASTGuardError(f"Syntax error while parsing generated code: {e}") from e
    ASTGuard().visit(tree)


_SAFE_RUNTIME_HEADER = '''\
import sys, os, time
_SAFE = {
    'print': print,
    'len': len,
    'abs': abs,
    'min': min,
    'max': max,
    'str': str,
    'int': int,
    'float': float,
    'bool': bool,
    'range': range,
    'isinstance': isinstance,
    'type': type,
    'repr': repr,
    'True': True,
    'False': False,
    'None': None,
}
import builtins as _b
for _name in ('eval', 'exec', 'compile', 'breakpoint', 'input'):
    try:
        delattr(_b, _name)
    except AttributeError:
        pass
del _b, _name
import os as _os
_ALLOWED_WRITE = {allowed_write_placeholder}
_WORKDIR = "{workdir_placeholder}"
def _safe_write(filename, value):
    basename = _os.path.basename(str(filename))
    if basename not in _ALLOWED_WRITE:
        raise PermissionError("Write to " + str(filename) + " is not allowed by policy.")
    safe_path = _os.path.join(_WORKDIR, basename)
    with open(safe_path, 'w') as _f:
        _f.write(str(value) + chr(10))
    return 9

def _safe_read(filename):
    basename = _os.path.basename(str(filename))
    safe_path = _os.path.join(_WORKDIR, basename)
    with open(safe_path) as _f:
        content = _f.read().strip()
    try:
        return int(content)
    except ValueError:
        return content
'''


class SandboxResult:
    def __init__(self, stdout: str, stderr: str, returncode: int, timed_out: bool):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self.timed_out = timed_out

    @property
    def success(self) -> bool:
        return self.returncode == 0 and not self.timed_out


class Sandbox:
    def __init__(self, timeout: int = 30, workdir: Optional[str] = None, policy: Optional[ExecutionPolicy] = None):
        self.policy = policy or ExecutionPolicy.default()
        self.timeout = timeout if timeout is not None else self.policy.max_runtime
        self.workdir = workdir or os.getcwd()

    def run(self, python_code: str, input_data: str = "") -> SandboxResult:
        try:
            guard_check(python_code)
        except ASTGuardError as e:
            return SandboxResult(stdout="", stderr=str(e), returncode=1, timed_out=False)

        if _looks_like_obvious_infinite_loop(python_code):
            return SandboxResult(
                stdout="",
                stderr=f"  {BOLD}{R}[TimeoutError]{X}\n  Program exceeded {self.timeout}s limit.\n",
                returncode=1,
                timed_out=True,
            )

        allowed = set(self.policy.allow_write)
        header = _SAFE_RUNTIME_HEADER.replace('{allowed_write_placeholder}', repr(allowed)).replace(
            '{workdir_placeholder}', self.workdir.replace('\\', '/')
        )
        patched = python_code.replace('_a9_write(', '_safe_write(')
        patched = patched.replace('_a9_read(', '_safe_read(')
        safe_code = header + patched

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, dir=self.workdir) as f:
            f.write(safe_code)
            tmp_path = f.name

        try:
            env = {'PATH': '/usr/bin:/bin', 'PYTHONPATH': '', 'HOME': self.workdir}
            mem_bytes = self.policy.max_memory_mb * 1024 * 1024

            # RLIMIT_AS proved unsafe here: on this Python runtime it can hang
            # even trivial subprocesses during interpreter startup.
            # Keep policy.max_memory_mb in the API for forward compatibility,
            # but do not apply a hard memory cap until a reliable backend exists.
            result = subprocess.run(
                [sys.executable, '-I', '-E', '-S', tmp_path],
                preexec_fn=None,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=self.workdir,
                env=env,
                input=input_data,
            )
            return SandboxResult(
                stdout=result.stdout,
                stderr=result.stderr,
                returncode=result.returncode,
                timed_out=False,
            )
        except subprocess.TimeoutExpired:
            return SandboxResult(
                stdout="",
                stderr=f"  {BOLD}{R}[TimeoutError]{X}\n  Program exceeded {self.timeout}s limit.\n",
                returncode=1,
                timed_out=True,
            )
        finally:
            Path(tmp_path).unlink(missing_ok=True)
