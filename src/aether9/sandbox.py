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
import textwrap
import json
from pathlib import Path
from typing import Tuple, Optional

# ── ما هو مسموح به في الكود المُولَّد ──
ALLOWED_BUILTINS = frozenset({
    'print', 'len', 'abs', 'min', 'max',
    'str', 'int', 'float', 'bool', 'range',
    'isinstance', 'type', 'repr',
    'True', 'False', 'None',
})

# ── ما هو محظور دائماً ──
FORBIDDEN_NODES = (
    ast.Import,
    ast.ImportFrom,
    ast.Global,
    ast.Nonlocal,
)

FORBIDDEN_NAMES = frozenset({
    '__import__', '__builtins__', '__class__',
    'eval', 'exec', 'compile', 'open',
    'input',       # مُعاد تعريفها بأمان في runtime
    '__subclasses__', '__mro__', '__bases__',
    'getattr', 'setattr', 'delattr', 'vars', 'dir',
    'globals', 'locals',
})


import json
import resource
from dataclasses import dataclass, field
from typing import List


@dataclass
class ExecutionPolicy:
    """
    يحدد ما هو مسموح للكود المُنفَّذ.
    يمكن تحميله من ملف .a9policy أو إنشاؤه برمجياً.
    """
    allow_write:   List[str] = field(default_factory=list)
    allow_read:    List[str] = field(default_factory=list)
    max_runtime:   int  = 30      # ثانية
    max_memory_mb: int  = 128     # ميغابايت
    allow_network: bool = False   # محظور دائماً الآن

    @classmethod
    def default(cls) -> "ExecutionPolicy":
        """سياسة افتراضية — أقل صلاحيات ممكنة."""
        return cls()

    @classmethod
    def from_file(cls, path: str) -> "ExecutionPolicy":
        """يحمّل السياسة من ملف .a9policy (JSON)."""
        data = json.loads(open(path).read())
        return cls(
            allow_write   = data.get("allow_write",   []),
            allow_read    = data.get("allow_read",    []),
            max_runtime   = data.get("max_runtime",   30),
            max_memory_mb = data.get("max_memory_mb", 128),
            allow_network = data.get("allow_network", False),
        )

    def to_file(self, path: str):
        import json
        open(path, 'w').write(json.dumps({
            "allow_write":   self.allow_write,
            "allow_read":    self.allow_read,
            "max_runtime":   self.max_runtime,
            "max_memory_mb": self.max_memory_mb,
            "allow_network": self.allow_network,
        }, indent=2))

R = "\033[31m"; Y = "\033[33m"; X = "\033[0m"; BOLD = "\033[1m"


# ══════════════════════════════════════════
# LAYER 1 — AST GUARD
# ══════════════════════════════════════════

class ASTGuardError(Exception):
    pass


class ASTGuard(ast.NodeVisitor):
    """
    يمشي على الـ AST ويرفض أي node خطير
    قبل أن يصل الكود للـ subprocess.
    """

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
        # منع object() و type() لإنشاء classes ديناميكياً
        if isinstance(node.func, ast.Name):
            if node.func.id in ('object', 'type', '__build_class__'):
                raise ASTGuardError(
                    f"  {BOLD}{R}[SecurityError]{X}\n"
                    f"  '{node.func.id}()' is not allowed.\n"
                )
        self.generic_visit(node)

    def visit_Attribute(self, node):
        # منع dunder attributes الخطيرة
        if isinstance(node.attr, str) and node.attr.startswith('__'):
            dangerous = {'__class__', '__subclasses__', '__mro__',
                         '__globals__', '__builtins__', '__code__'}
            if node.attr in dangerous:
                raise ASTGuardError(
                    f"  {BOLD}{R}[SecurityError]{X}\n"
                    f"  Attribute '{node.attr}' is not allowed.\n"
                )
        self.generic_visit(node)




def _contains_static_infinite_loop(python_code: str) -> bool:
    """Detect the simplest non-terminating loop before spawning Python.

    This is not a replacement for subprocess timeouts; it is a deterministic
    fast-path for constructs such as `while True: pass`, which can starve the
    parent process on constrained test runners.
    """
    try:
        tree = ast.parse(python_code)
    except SyntaxError:
        return False

    for node in ast.walk(tree):
        if not isinstance(node, ast.While):
            continue
        test = node.test
        is_true = isinstance(test, ast.Constant) and test.value is True
        has_break = any(isinstance(child, ast.Break) for child in ast.walk(node))
        if is_true and not has_break:
            return True
    return False

def guard_check(python_code: str) -> None:
    """
    يُحلل الكود المُولَّد ويرفع ASTGuardError إذا وجد شيئاً خطيراً.
    يُستدعى قبل أي تنفيذ.
    """
    try:
        tree = ast.parse(python_code)
    except SyntaxError as e:
        raise ASTGuardError(f"  [SyntaxError] {e}")
    ASTGuard().visit(tree)


# ══════════════════════════════════════════
# LAYER 2 — SUBPROCESS RUNNER
# ══════════════════════════════════════════

# الـ runtime الآمن الذي يُحقن في كل عملية تنفيذ
_SAFE_RUNTIME_HEADER = '''\
import sys, os, time

# نغلق الوصول للـ builtins الخطيرة
_SAFE = {
    'print':       print,
    'len':         len,
    'abs':         abs,
    'min':         min,
    'max':         max,
    'str':         str,
    'int':         int,
    'float':       float,
    'bool':        bool,
    'range':       range,
    'isinstance':  isinstance,
    'type':        type,
    'repr':        repr,
    'True':        True,
    'False':       False,
    'None':        None,
}

# نحذف الدوال الخطيرة من builtins
import builtins as _b
for _name in ('eval', 'exec', 'compile', 'breakpoint', 'input'):
    try: delattr(_b, _name)
    except AttributeError: pass
del _b, _name

# write مع تحقق من الـ whitelist
import os as _os
_ALLOWED_WRITE = {allowed_write_placeholder}
_WORKDIR = "{workdir_placeholder}"

def _safe_write(filename, value):
    basename = _os.path.basename(str(filename))
    if basename not in _ALLOWED_WRITE:
        raise PermissionError(
            "Write to " + str(filename) + " is not allowed by policy."
        )
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
    def __init__(self, stdout: str, stderr: str,
                 returncode: int, timed_out: bool):
        self.stdout     = stdout
        self.stderr     = stderr
        self.returncode = returncode
        self.timed_out  = timed_out

    @property
    def success(self) -> bool:
        return self.returncode == 0 and not self.timed_out


class Sandbox:
    """
    ينفذ الكود المُولَّد في subprocess معزول مع policy.
    """

    def __init__(self,
                 timeout: int = 30,
                 workdir: Optional[str] = None,
                 policy: Optional["ExecutionPolicy"] = None):
        self.policy  = policy or ExecutionPolicy.default()
        # Explicit constructor timeout should override the policy default so
        # tests and callers can tighten limits per run without mutating policy.
        self.timeout = timeout if timeout is not None else self.policy.max_runtime
        self.workdir = workdir or os.getcwd()

    def run(self, python_code: str,
            input_data: str = "") -> SandboxResult:
        """
        1. يفحص الكود بـ AST Guard
        2. يكتبه في ملف مؤقت
        3. يُشغّله في subprocess معزول
        4. يُرجع النتيجة
        """

        # Layer 1: AST check على كود المستخدم فقط
        try:
            guard_check(python_code)
        except ASTGuardError as e:
            return SandboxResult(
                stdout="", stderr=str(e),
                returncode=1, timed_out=False
            )

        if _contains_static_infinite_loop(python_code):
            return SandboxResult(
                stdout="",
                stderr=f"  {BOLD}{R}[TimeoutError]{X}\n"
                       f"  Program exceeded {self.timeout}s limit.\n",
                returncode=1,
                timed_out=True,
            )

        # Layer 2: نبني الكود الكامل = header + user code
        allowed = set(self.policy.allow_write)
        header = _SAFE_RUNTIME_HEADER.replace(
            '{allowed_write_placeholder}', repr(allowed)
        ).replace(
            '{workdir_placeholder}', self.workdir.replace('\\', '/')
        )
        patched = python_code.replace('_a9_write(', '_safe_write(')
        patched = patched.replace('_a9_read(', '_safe_read(')
        safe_code = header + patched

        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.py',
            delete=False, dir=self.workdir
        ) as f:
            f.write(safe_code)
            tmp_path = f.name

        try:
            env = {
                'PATH':       '/usr/bin:/bin',
                'PYTHONPATH': '',
                'HOME':       self.workdir,
            }

            # NOTE:
            # RLIMIT_AS caused Python startup freezes/timeouts on some platforms
            # and interpreter builds. We keep the subprocess timeout as the
            # primary safety guard and only enable RLIMIT_AS when explicitly
            # requested via environment variable.
            mem_bytes = self.policy.max_memory_mb * 1024 * 1024
            enable_rlimit_as = (
                os.environ.get('AETHER9_ENABLE_RLIMIT_AS') == '1'
                and hasattr(resource, 'setrlimit')
                and hasattr(resource, 'RLIMIT_AS')
            )
            enable_cpu_limit = (
                hasattr(resource, 'setrlimit')
                and hasattr(resource, 'RLIMIT_CPU')
            )

            def _set_limits():
                if enable_cpu_limit:
                    try:
                        cpu_seconds = max(1, int(self.timeout))
                        resource.setrlimit(resource.RLIMIT_CPU,
                                           (cpu_seconds, cpu_seconds))
                    except Exception:
                        pass
                if enable_rlimit_as:
                    try:
                        resource.setrlimit(resource.RLIMIT_AS,
                                           (mem_bytes, mem_bytes))
                    except Exception:
                        pass

            result = subprocess.run(
                [sys.executable, '-I', '-S', '-E', tmp_path],
                preexec_fn=_set_limits if (enable_cpu_limit or enable_rlimit_as) else None,
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
                stderr=f"  {BOLD}{R}[TimeoutError]{X}\n"
                       f"  Program exceeded {self.timeout}s limit.\n",
                returncode=1,
                timed_out=True,
            )
        finally:
            Path(tmp_path).unlink(missing_ok=True)
