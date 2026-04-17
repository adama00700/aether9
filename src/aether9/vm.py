"""
Aether-9 Bytecode System
─────────────────────────────────────────────
Pipeline: source.a9 → AST → Bytecode → VM
بدون exec() — بدون Python runtime — interpreter مستقل
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple
import struct
import hashlib
import hmac
import time
import os

# ══════════════════════════════════════════════
# OPCODES
# ══════════════════════════════════════════════

class Op(Enum):
    # stack
    LOAD_CONST    = auto()   # push literal
    LOAD_NAME     = auto()   # push variable
    STORE_NAME    = auto()   # pop → variable
    POP           = auto()   # discard top

    # arithmetic / comparison
    BINARY_OP     = auto()   # op: + - * / % and or
    COMPARE       = auto()   # op: == != < > <= >=
    UNARY_NEG     = auto()

    # control flow
    JUMP          = auto()   # unconditional
    JUMP_IF_FALSE = auto()   # pop + jump if falsy
    JUMP_BACK     = auto()   # for while loops

    # iteration
    FOR_START     = auto()   # push iterator state
    FOR_NEXT      = auto()   # advance or jump past loop
    FOR_END       = auto()   # cleanup

    # functions
    MAKE_FUNC     = auto()   # define lattice
    CALL_FUNC     = auto()   # call with n args
    RETURN        = auto()   # return top of stack

    # IO + stdlib
    PRINT         = auto()
    WRITE         = auto()
    READ          = auto()
    CALL_BUILTIN  = auto()   # abs, min, max, dr, …

    # program
    HALT          = auto()


@dataclass
class Instruction:
    op:      Op
    arg:     Any = None   # name, value, address, op-string

    def __repr__(self):
        return f"{self.op.name:<18} {self.arg!r}" if self.arg is not None \
               else self.op.name


# ══════════════════════════════════════════════
# BYTECODE COMPILER  (AST → Instructions)
# ══════════════════════════════════════════════

from .compiler import (
    ProgramNode, ArrayNode, LatticeNode, AssignNode,
    ReturnNode, CallNode, IfNode, ForNode, WhileNode,
    BinOpNode, NumberNode, StringNode, IdentNode,
    Aether9Compiler,
)
from .core import VortexSequencer
from .signature import SignatureFile, _DEFAULT_KEY

BUILTIN_FNS = frozenset({
    'abs', 'min', 'max', 'len', 'str', 'concat',
    'dr',  'mod', 'print', 'write', 'read', 'input',
})


class BytecodeCompiler:
    """Compiles an Aether-9 AST to a flat list of Instructions."""

    def __init__(self, registry: Dict):
        self.registry   = registry
        self.code: List[Instruction] = []
        self.functions: Dict[str, List[Instruction]] = {}
        # vortex seals embedded per function
        self.func_seals: Dict[str, Tuple[List, int]] = {}

    # ── helpers ──

    def _emit(self, op: Op, arg=None):
        self.code.append(Instruction(op, arg))
        return len(self.code) - 1

    def _patch(self, idx: int, new_arg):
        self.code[idx].arg = new_arg

    # ── program ──

    def compile(self, ast: ProgramNode) -> 'Bytecode':
        for node in ast.body:
            self._node(node)
        self._emit(Op.HALT)
        return Bytecode(
            instructions = self.code,
            functions    = self.functions,
            func_seals   = self.func_seals,
            registry     = self.registry,
        )

    # ── dispatch ──

    def _node(self, node):
        if   isinstance(node, ArrayNode):   self._array(node)
        elif isinstance(node, LatticeNode): self._lattice(node)
        elif isinstance(node, AssignNode):  self._assign(node)
        elif isinstance(node, ReturnNode):  self._return(node)
        elif isinstance(node, IfNode):      self._if(node)
        elif isinstance(node, ForNode):     self._for(node)
        elif isinstance(node, WhileNode):   self._while(node)
        elif isinstance(node, CallNode):    self._call_stmt(node)
        elif isinstance(node, BinOpNode):   self._binop(node)
        elif isinstance(node, NumberNode):  self._emit(Op.LOAD_CONST, node.value)
        elif isinstance(node, StringNode):  self._emit(Op.LOAD_CONST, node.value)
        elif isinstance(node, IdentNode):   self._emit(Op.LOAD_NAME, node.name)

    def _array(self, node: ArrayNode):
        self._emit(Op.LOAD_CONST, node.elements)
        self._emit(Op.STORE_NAME, node.name)

    def _assign(self, node: AssignNode):
        self._expr(node.value)
        self._emit(Op.STORE_NAME, node.name)

    def _return(self, node: ReturnNode):
        self._expr(node.value)
        self._emit(Op.RETURN)

    def _call_stmt(self, node: CallNode):
        self._call_expr(node)
        self._emit(Op.POP)

    # ── expressions ──

    def _expr(self, node):
        if   isinstance(node, NumberNode): self._emit(Op.LOAD_CONST, node.value)
        elif isinstance(node, StringNode): self._emit(Op.LOAD_CONST, node.value)
        elif isinstance(node, IdentNode):  self._emit(Op.LOAD_NAME,  node.name)
        elif isinstance(node, BinOpNode):  self._binop(node)
        elif isinstance(node, CallNode):   self._call_expr(node)

    def _binop(self, node: BinOpNode):
        self._expr(node.left)
        self._expr(node.right)
        if node.op in ('==', '!=', '<', '>', '<=', '>='):
            self._emit(Op.COMPARE, node.op)
        else:
            self._emit(Op.BINARY_OP, node.op)

    def _call_expr(self, node: CallNode):
        if node.func == 'print':
            for a in node.args: self._expr(a)
            self._emit(Op.PRINT, len(node.args))
            return
        if node.func == 'write':
            for a in node.args: self._expr(a)
            self._emit(Op.WRITE, len(node.args))
            return
        if node.func == 'read':
            for a in node.args: self._expr(a)
            self._emit(Op.READ, len(node.args))
            return
        if node.func in BUILTIN_FNS:
            for a in node.args: self._expr(a)
            self._emit(Op.CALL_BUILTIN, (node.func, len(node.args)))
            return
        # lattice call
        for a in node.args: self._expr(a)
        self._emit(Op.CALL_FUNC, (node.func, len(node.args)))

    # ── control flow ──

    def _if(self, node: IfNode):
        self._expr(node.cond)
        patch = self._emit(Op.JUMP_IF_FALSE, None)

        for s in node.then_body: self._node(s)

        if node.else_body:
            skip = self._emit(Op.JUMP, None)
            self._patch(patch, len(self.code))
            for s in node.else_body: self._node(s)
            self._patch(skip, len(self.code))
        else:
            self._patch(patch, len(self.code))

    def _for(self, node: ForNode):
        self._emit(Op.LOAD_NAME, node.iterable)
        self._emit(Op.FOR_START, node.var)
        loop_top = len(self.code)
        patch = self._emit(Op.FOR_NEXT, None)     # jump past loop when done

        for s in node.body: self._node(s)

        self._emit(Op.JUMP_BACK, loop_top)
        self._patch(patch, len(self.code))
        self._emit(Op.FOR_END)

    def _while(self, node: WhileNode):
        cond_addr = len(self.code)
        self._expr(node.cond)
        patch = self._emit(Op.JUMP_IF_FALSE, None)

        for s in node.body: self._node(s)

        self._emit(Op.JUMP_BACK, cond_addr)
        self._patch(patch, len(self.code))

    # ── lattice (compiled to separate instruction list) ──

    def _lattice(self, node: LatticeNode):
        saved_code = self.code
        self.code  = []

        # أول شيء في الدالة: STORE_NAME لكل parameter
        for p in node.params:
            self._emit(Op.STORE_NAME, p)

        for s in node.body: self._node(s)
        if not self.code or self.code[-1].op != Op.RETURN:
            self._emit(Op.RETURN)

        self.functions[node.name] = self.code
        self.code = saved_code

        # embed vortex seal if binding exists
        if node.binding and node.binding in self.registry:
            info = self.registry[node.binding]
            self.func_seals[node.name] = (info['data'], info['raw_sig'])

        # emit MAKE_FUNC to register at runtime
        self._emit(Op.MAKE_FUNC, node.name)


# ══════════════════════════════════════════════
# BYTECODE  (container)
# ══════════════════════════════════════════════

@dataclass
class Bytecode:
    instructions: List[Instruction]
    functions:    Dict[str, List[Instruction]]
    func_seals:   Dict[str, Tuple[List, int]]
    registry:     Dict

    MAGIC = b"A9B9"
    BINARY_VERSION = 1

    _T_NONE  = 0
    _T_INT   = 1
    _T_STR   = 2
    _T_LIST  = 3
    _T_TUPLE = 4

    def disassemble(self) -> str:
        lines = ["=== main ==="]
        for i, ins in enumerate(self.instructions):
            lines.append(f"  {i:4d}  {ins}")
        for name, code in self.functions.items():
            seal = self.func_seals.get(name)
            lines.append(f"\n=== {name} {'[sealed]' if seal else '[pure]'} ===")
            for i, ins in enumerate(code):
                lines.append(f"  {i:4d}  {ins}")
        return '\n'.join(lines)

    # ── JSON compatibility format ──

    def _to_json_dict(self) -> Dict[str, Any]:
        def ser_ins(ins_list):
            return [{'op': i.op.name, 'arg': i.arg} for i in ins_list]
        return {
            'version':      '1.0-json',
            'instructions': ser_ins(self.instructions),
            'functions':    {k: ser_ins(v) for k, v in self.functions.items()},
            'func_seals':   {k: list(v) for k, v in self.func_seals.items()},
        }

    def save_json(self, path: str):
        """Serialize to the legacy human-readable JSON .a9b container."""
        import json
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self._to_json_dict(), f, indent=2)

    # ── Binary format v1 ──
    # Layout:
    #   magic               4 bytes   b"A9B9"
    #   version             u16       currently 1
    #   main_code           codeblock
    #   functions_count     u32
    #   repeated: name      value-string + codeblock
    #   seals_count         u32
    #   repeated: name      value-string + data-list + raw_sig-int
    #
    # Value tags used for instruction args and seal data:
    #   0 None, 1 signed int64, 2 UTF-8 string, 3 list, 4 tuple

    @classmethod
    def _pack_u8(cls, value: int) -> bytes:
        return struct.pack('>B', value)

    @classmethod
    def _pack_u16(cls, value: int) -> bytes:
        return struct.pack('>H', value)

    @classmethod
    def _pack_u32(cls, value: int) -> bytes:
        return struct.pack('>I', value)

    @classmethod
    def _pack_i64(cls, value: int) -> bytes:
        return struct.pack('>q', int(value))

    @classmethod
    def _read_exact(cls, f, n: int) -> bytes:
        data = f.read(n)
        if len(data) != n:
            raise VMError('truncated binary .a9b container')
        return data

    @classmethod
    def _read_u8(cls, f) -> int:
        return struct.unpack('>B', cls._read_exact(f, 1))[0]

    @classmethod
    def _read_u16(cls, f) -> int:
        return struct.unpack('>H', cls._read_exact(f, 2))[0]

    @classmethod
    def _read_u32(cls, f) -> int:
        return struct.unpack('>I', cls._read_exact(f, 4))[0]

    @classmethod
    def _read_i64(cls, f) -> int:
        return struct.unpack('>q', cls._read_exact(f, 8))[0]

    @classmethod
    def _encode_value(cls, value: Any) -> bytes:
        if value is None:
            return cls._pack_u8(cls._T_NONE)
        if isinstance(value, bool):
            # bool is an int subclass; encode it deterministically as int 0/1.
            return cls._pack_u8(cls._T_INT) + cls._pack_i64(1 if value else 0)
        if isinstance(value, int):
            return cls._pack_u8(cls._T_INT) + cls._pack_i64(value)
        if isinstance(value, str):
            raw = value.encode('utf-8')
            return cls._pack_u8(cls._T_STR) + cls._pack_u32(len(raw)) + raw
        if isinstance(value, list):
            out = bytearray([cls._T_LIST])
            out.extend(cls._pack_u32(len(value)))
            for item in value:
                out.extend(cls._encode_value(item))
            return bytes(out)
        if isinstance(value, tuple):
            out = bytearray([cls._T_TUPLE])
            out.extend(cls._pack_u32(len(value)))
            for item in value:
                out.extend(cls._encode_value(item))
            return bytes(out)
        raise TypeError(f'cannot encode bytecode value: {value!r}')

    @classmethod
    def _decode_value(cls, f) -> Any:
        tag = cls._read_u8(f)
        if tag == cls._T_NONE:
            return None
        if tag == cls._T_INT:
            return cls._read_i64(f)
        if tag == cls._T_STR:
            size = cls._read_u32(f)
            return cls._read_exact(f, size).decode('utf-8')
        if tag in (cls._T_LIST, cls._T_TUPLE):
            count = cls._read_u32(f)
            values = [cls._decode_value(f) for _ in range(count)]
            return tuple(values) if tag == cls._T_TUPLE else values
        raise VMError(f'unknown binary value tag: {tag}')

    @classmethod
    def _encode_instruction(cls, ins: Instruction) -> bytes:
        if not isinstance(ins.op, Op):
            raise TypeError(f'invalid opcode: {ins.op!r}')
        return cls._pack_u16(ins.op.value) + cls._encode_value(ins.arg)

    @classmethod
    def _decode_instruction(cls, f) -> Instruction:
        op_value = cls._read_u16(f)
        try:
            op = Op(op_value)
        except ValueError as exc:
            raise VMError(f'unknown binary opcode id: {op_value}') from exc
        arg = cls._decode_value(f)
        return Instruction(op, arg)

    @classmethod
    def _encode_code(cls, code: List[Instruction]) -> bytes:
        out = bytearray(cls._pack_u32(len(code)))
        for ins in code:
            out.extend(cls._encode_instruction(ins))
        return bytes(out)

    @classmethod
    def _decode_code(cls, f) -> List[Instruction]:
        count = cls._read_u32(f)
        return [cls._decode_instruction(f) for _ in range(count)]

    def save_binary(self, path: str):
        """Serialize to the binary A9B9 .a9b container."""
        out = bytearray()
        out.extend(self.MAGIC)
        out.extend(self._pack_u16(self.BINARY_VERSION))
        out.extend(self._encode_code(self.instructions))

        out.extend(self._pack_u32(len(self.functions)))
        for name, code in self.functions.items():
            out.extend(self._encode_value(name))
            out.extend(self._encode_code(code))

        out.extend(self._pack_u32(len(self.func_seals)))
        for name, seal in self.func_seals.items():
            data, raw_sig = seal
            out.extend(self._encode_value(name))
            out.extend(self._encode_value(list(data)))
            out.extend(self._encode_value(int(raw_sig)))

        with open(path, 'wb') as f:
            f.write(bytes(out))

    def save(self, path: str, format: str = 'json'):
        """Serialize to .a9b. Defaults to JSON for backward compatibility."""
        fmt = format.lower()
        if fmt == 'json':
            return self.save_json(path)
        if fmt in ('binary', 'bin'):
            return self.save_binary(path)
        raise ValueError("format must be 'json' or 'binary'")

    @classmethod
    def detect_format(cls, path: str) -> str:
        with open(path, 'rb') as f:
            head = f.read(4)
        return 'binary' if head == cls.MAGIC else 'json'

    @classmethod
    def load_json(cls, path: str) -> 'Bytecode':
        import json
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        def des(lst):
            result = []
            for item in lst:
                op = Op[item['op']]
                arg = item.get('arg')
                # JSON turns tuple args into lists. Only opcode metadata tuples
                # should be restored; literal arrays must remain lists.
                if op in (Op.CALL_FUNC, Op.CALL_BUILTIN) and isinstance(arg, list) and len(arg) == 2:
                    arg = tuple(arg)
                result.append(Instruction(op, arg))
            return result

        def des_seal(value):
            data_value, raw_sig = value
            if isinstance(data_value, tuple):
                data_value = list(data_value)
            return (data_value, raw_sig)

        return cls(
            instructions = des(data['instructions']),
            functions    = {k: des(v) for k, v in data['functions'].items()},
            func_seals   = {k: des_seal(v) for k, v in data['func_seals'].items()},
            registry     = {},
        )

    @classmethod
    def load_binary(cls, path: str) -> 'Bytecode':
        with open(path, 'rb') as f:
            magic = cls._read_exact(f, 4)
            if magic != cls.MAGIC:
                raise VMError('invalid binary .a9b magic bytes')
            version = cls._read_u16(f)
            if version != cls.BINARY_VERSION:
                raise VMError(f'unsupported binary .a9b version: {version}')

            instructions = cls._decode_code(f)

            functions = {}
            for _ in range(cls._read_u32(f)):
                name = cls._decode_value(f)
                if not isinstance(name, str):
                    raise VMError('binary function name must be a string')
                functions[name] = cls._decode_code(f)

            func_seals = {}
            for _ in range(cls._read_u32(f)):
                name = cls._decode_value(f)
                data = cls._decode_value(f)
                raw_sig = cls._decode_value(f)
                if not isinstance(name, str):
                    raise VMError('binary seal name must be a string')
                if not isinstance(data, list):
                    raise VMError(f"binary seal data for '{name}' must be a list")
                if not isinstance(raw_sig, int):
                    raise VMError(f"binary seal raw_sig for '{name}' must be an int")
                func_seals[name] = (data, raw_sig)

            trailing = f.read(1)
            if trailing:
                raise VMError('unexpected trailing data in binary .a9b container')

        return cls(
            instructions=instructions,
            functions=functions,
            func_seals=func_seals,
            registry={},
        )

    @classmethod
    def load(cls, path: str) -> 'Bytecode':
        """Load either JSON .a9b or binary A9B9 .a9b automatically."""
        if cls.detect_format(path) == 'binary':
            return cls.load_binary(path)
        return cls.load_json(path)


# ══════════════════════════════════════════════
# VM  (stack-based interpreter)
# ══════════════════════════════════════════════

class VMError(Exception): pass
class VMSecurityError(VMError): pass
class VMHalt(Exception): pass


def _digital_root(v: int) -> int:
    s = str(abs(int(v))); d = sum(int(c) for c in s)
    while d > 9: d = sum(int(c) for c in str(d))
    return 9 if d in (9, 0) else d


STDLIB = {
    'abs':    lambda a: abs(a),
    'min':    lambda a, b: min(a, b),
    'max':    lambda a, b: max(a, b),
    'len':    lambda a: len(str(a)),
    'str':    lambda a: str(a),
    'concat': lambda a, b: str(a) + str(b),
    'dr':     lambda a: _digital_root(a),
    'mod':    lambda a, b: (a % b) or 9,
}


class Frame:
    """Stack frame for a lattice call."""
    def __init__(self, name: str, code: List[Instruction],
                 args: Dict, caller_ns: Dict):
        self.name      = name
        self.code      = code
        self.ip        = 0
        self.stack:    List = []
        self.locals:   Dict = dict(args)
        self.caller_ns = caller_ns

    def push(self, v):
        self.stack.append(v)

    def pop(self):
        if not self.stack:
            raise VMError(f"stack underflow in frame '{self.name}'")
        return self.stack.pop()

    def peek(self):
        if not self.stack:
            raise VMError(f"empty stack in frame '{self.name}'")
        return self.stack[-1]


class AetherVM:
    """
    Stack-based interpreter for Aether-9 bytecode.
    بدون exec() — كل instruction تُنفَّذ مباشرة.
    """

    def __init__(self, workdir: str = '.'):
        self.workdir  = workdir
        self.ns:  Dict = {}          # global namespace
        self.fns: Dict[str, List[Instruction]] = {}
        self.seals: Dict[str, Tuple] = {}

    def run(self, bc: Bytecode) -> Any:
        self.fns   = bc.functions
        self.seals = bc.func_seals
        # inject arrays
        for name, info in bc.registry.items():
            self.ns[name] = info['data']

        frame = Frame('__main__', bc.instructions, {}, self.ns)
        return self._exec(frame)

    def _exec(self, frame: Frame) -> Any:
        code = frame.code
        ns   = frame.locals if frame.name != '__main__' else self.ns

        while frame.ip < len(code):
            ins = code[frame.ip]
            frame.ip += 1

            op, arg = ins.op, ins.arg

            # ── stack ops ──
            if op == Op.LOAD_CONST:
                frame.push(arg)

            elif op == Op.LOAD_NAME:
                _sentinel = object()
                val = ns.get(arg, _sentinel)
                if val is _sentinel:
                    val = self.ns.get(arg, _sentinel)
                if val is _sentinel:
                    raise VMError(f"name '{arg}' is not defined")
                frame.push(val)

            elif op == Op.STORE_NAME:
                ns[arg] = frame.pop()

            elif op == Op.POP:
                frame.pop()

            # ── arithmetic ──
            elif op == Op.BINARY_OP:
                b, a = frame.pop(), frame.pop()
                ops = {
                    '+': lambda x,y: x+y, '-': lambda x,y: x-y,
                    '*': lambda x,y: x*y, '/': lambda x,y: x//y,
                    '%': lambda x,y: x%y,
                    'or':  lambda x,y: x or y,
                    'and': lambda x,y: x and y,
                }
                if arg not in ops:
                    raise VMError(f"unknown op: {arg}")
                frame.push(ops[arg](a, b))

            elif op == Op.COMPARE:
                b, a = frame.pop(), frame.pop()
                ops = {'==': a==b, '!=': a!=b, '<': a<b,
                       '>': a>b, '<=': a<=b, '>=': a>=b}
                if arg not in ops:
                    raise VMError(f"unknown comparison op: {arg}")
                frame.push(ops[arg])

            elif op == Op.UNARY_NEG:
                frame.push(-frame.pop())

            # ── control flow ──
            elif op == Op.JUMP:
                frame.ip = arg

            elif op == Op.JUMP_IF_FALSE:
                if not frame.pop():
                    frame.ip = arg

            elif op == Op.JUMP_BACK:
                frame.ip = arg

            # ── for loop ──
            elif op == Op.FOR_START:
                iterable = frame.pop()
                frame.push((iter(iterable), arg))  # (iterator, var_name)

            elif op == Op.FOR_NEXT:
                if not frame.stack:
                    frame.ip = arg
                    continue
                it_state = frame.stack[-1]  # peek
                if not isinstance(it_state, tuple):
                    frame.ip = arg
                    continue
                iterator, var_name = it_state
                try:
                    val = next(iterator)
                    ns[var_name] = val
                except StopIteration:
                    frame.pop()    # remove iterator
                    frame.ip = arg  # jump past loop

            elif op == Op.FOR_END:
                pass  # iterator already consumed

            # ── functions ──
            elif op == Op.MAKE_FUNC:
                pass  # already registered in self.fns

            elif op == Op.CALL_FUNC:
                fname, nargs = arg
                fn_code = self.fns.get(fname)
                if fn_code is None:
                    raise VMError(f"undefined lattice: '{fname}'")

                # vortex seal check
                if fname in self.seals:
                    data, expected_sig = self.seals[fname]
                    from aether9.core import VortexSequencer as VS
                    actual, _ = VS(data).compute_seal()
                    if actual != expected_sig:
                        raise VMSecurityError(
                            f"Vortex tampered in '{fname}': "
                            f"got={actual}, expected={expected_sig}"
                        )

                args_vals = [frame.pop() for _ in range(nargs)][::-1]
                # params are the first N STORE_NAMEs in the function
                params = [ins.arg for ins in fn_code[:nargs]
                          if ins.op == Op.STORE_NAME]
                fn_args = dict(zip(params, args_vals))
                child = Frame(fname, fn_code, fn_args, ns)
                # params already in locals — skip their STORE_NAME instructions
                child.ip = len(params)
                result = self._exec(child)

                # lattice output check
                if result is not None and result != 0:
                    if _digital_root(result) != 9:
                        raise VMError(
                            f"Lattice asymmetry in '{fname}': "
                            f"root={_digital_root(result)}, expected=9"
                        )
                frame.push(result)

            elif op == Op.RETURN:
                val = frame.pop()
                return (val or 9)

            # ── IO ──
            elif op == Op.PRINT:
                vals = [frame.pop() for _ in range(arg)][::-1]
                print(*vals)
                frame.push(None)

            elif op == Op.WRITE:
                val, fname = frame.pop(), frame.pop()
                path = os.path.join(self.workdir, os.path.basename(str(fname)))
                open(path, 'w').write(str(val) + '\n')
                frame.push(9)

            elif op == Op.READ:
                fname = frame.pop()
                path  = os.path.join(self.workdir, os.path.basename(str(fname)))
                content = open(path).read().strip()
                try:    frame.push(int(content))
                except: frame.push(content)

            elif op == Op.CALL_BUILTIN:
                fname, nargs = arg
                vals = [frame.pop() for _ in range(nargs)][::-1]
                fn   = STDLIB.get(fname)
                if fn is None:
                    raise VMError(f"unknown builtin: '{fname}'")
                frame.push(fn(*vals))

            elif op == Op.HALT:
                return

            else:
                raise VMError(
                    f"unhandled opcode {op!r} in frame '{frame.name}' "
                    f"at instruction {frame.ip - 1}"
                )

        return None

    def _get_params(self, fname: str) -> List[str]:
        """Extract parameter names from function bytecode."""
        # params are the first STORE_NAMEs before any LOAD
        params = []
        for ins in self.fns.get(fname, []):
            if ins.op == Op.STORE_NAME and ins.arg not in params:
                params.append(ins.arg)
                # stop when we hit non-param code
                break
        return params


# ══════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════

def compile_to_bytecode(source: str) -> Tuple[Bytecode, Dict]:
    """source.a9 → Bytecode + registry"""
    compiler = Aether9Compiler()
    _, registry = compiler.compile(source)

    from .compiler import Lexer, Parser
    tokens = Lexer(source).tokenize()
    ast    = Parser(tokens).parse()

    bc = BytecodeCompiler(registry).compile(ast)
    return bc, registry


def run_bytecode(bc: Bytecode, registry: Dict,
                 workdir: str = '.') -> None:
    """Execute bytecode in the VM."""
    vm = AetherVM(workdir=workdir)
    vm.run(bc)
