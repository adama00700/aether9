"""
Aether-9 Bytecode System
─────────────────────────────────────────────
Pipeline: source.a9 → AST → Bytecode → VM
بدون exec() — بدون Python runtime — interpreter مستقل
"""

from __future__ import annotations
from collections import Counter, deque
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Deque, Dict, List, Optional, Tuple
import hashlib
import json
import os
import struct


class Op(Enum):
    LOAD_CONST    = auto()
    LOAD_NAME     = auto()
    STORE_NAME    = auto()
    POP           = auto()

    BINARY_OP     = auto()
    COMPARE       = auto()
    UNARY_NEG     = auto()

    JUMP          = auto()
    JUMP_IF_FALSE = auto()
    JUMP_BACK     = auto()

    FOR_START     = auto()
    FOR_NEXT      = auto()
    FOR_END       = auto()

    MAKE_FUNC     = auto()
    CALL_FUNC     = auto()
    RETURN        = auto()

    PRINT         = auto()
    WRITE         = auto()
    READ          = auto()
    CALL_BUILTIN  = auto()

    HALT          = auto()


@dataclass
class Instruction:
    op: Op
    arg: Any = None

    def __repr__(self):
        return f"{self.op.name:<18} {self.arg!r}" if self.arg is not None else self.op.name


from .compiler import (
    ProgramNode, ArrayNode, LatticeNode, AssignNode,
    ReturnNode, CallNode, IfNode, ForNode, WhileNode,
    BinOpNode, NumberNode, StringNode, IdentNode,
    Aether9Compiler,
)


BUILTIN_FNS = frozenset({
    'abs', 'min', 'max', 'len', 'str', 'concat',
    'dr',  'mod', 'print', 'write', 'read', 'input',
})


class BytecodeCompiler:
    def __init__(self, registry: Dict):
        self.registry = registry
        self.code: List[Instruction] = []
        self.functions: Dict[str, List[Instruction]] = {}
        self.func_seals: Dict[str, Tuple[List, int]] = {}

    def _emit(self, op: Op, arg=None):
        self.code.append(Instruction(op, arg))
        return len(self.code) - 1

    def _patch(self, idx: int, new_arg):
        self.code[idx].arg = new_arg

    def compile(self, ast: ProgramNode) -> 'Bytecode':
        for node in ast.body:
            self._node(node)
        self._emit(Op.HALT)
        return Bytecode(
            instructions=self.code,
            functions=self.functions,
            func_seals=self.func_seals,
            registry=self.registry,
        )

    def _node(self, node):
        if isinstance(node, ArrayNode):
            self._array(node)
        elif isinstance(node, LatticeNode):
            self._lattice(node)
        elif isinstance(node, AssignNode):
            self._assign(node)
        elif isinstance(node, ReturnNode):
            self._return(node)
        elif isinstance(node, IfNode):
            self._if(node)
        elif isinstance(node, ForNode):
            self._for(node)
        elif isinstance(node, WhileNode):
            self._while(node)
        elif isinstance(node, CallNode):
            self._call_stmt(node)
        elif isinstance(node, BinOpNode):
            self._binop(node)
        elif isinstance(node, NumberNode):
            self._emit(Op.LOAD_CONST, node.value)
        elif isinstance(node, StringNode):
            self._emit(Op.LOAD_CONST, node.value)
        elif isinstance(node, IdentNode):
            self._emit(Op.LOAD_NAME, node.name)

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

    def _expr(self, node):
        if isinstance(node, NumberNode):
            self._emit(Op.LOAD_CONST, node.value)
        elif isinstance(node, StringNode):
            self._emit(Op.LOAD_CONST, node.value)
        elif isinstance(node, IdentNode):
            self._emit(Op.LOAD_NAME, node.name)
        elif isinstance(node, BinOpNode):
            self._binop(node)
        elif isinstance(node, CallNode):
            self._call_expr(node)

    def _binop(self, node: BinOpNode):
        self._expr(node.left)
        self._expr(node.right)
        if node.op in ('==', '!=', '<', '>', '<=', '>='):
            self._emit(Op.COMPARE, node.op)
        else:
            self._emit(Op.BINARY_OP, node.op)

    def _call_expr(self, node: CallNode):
        if node.func == 'print':
            for a in node.args:
                self._expr(a)
            self._emit(Op.PRINT, len(node.args))
            return
        if node.func == 'write':
            for a in node.args:
                self._expr(a)
            self._emit(Op.WRITE, len(node.args))
            return
        if node.func == 'read':
            for a in node.args:
                self._expr(a)
            self._emit(Op.READ, len(node.args))
            return
        if node.func in BUILTIN_FNS:
            for a in node.args:
                self._expr(a)
            self._emit(Op.CALL_BUILTIN, (node.func, len(node.args)))
            return
        for a in node.args:
            self._expr(a)
        self._emit(Op.CALL_FUNC, (node.func, len(node.args)))

    def _if(self, node: IfNode):
        self._expr(node.cond)
        patch = self._emit(Op.JUMP_IF_FALSE, None)
        for s in node.then_body:
            self._node(s)
        if node.else_body:
            skip = self._emit(Op.JUMP, None)
            self._patch(patch, len(self.code))
            for s in node.else_body:
                self._node(s)
            self._patch(skip, len(self.code))
        else:
            self._patch(patch, len(self.code))

    def _for(self, node: ForNode):
        self._emit(Op.LOAD_NAME, node.iterable)
        self._emit(Op.FOR_START, node.var)
        loop_top = len(self.code)
        patch = self._emit(Op.FOR_NEXT, None)
        for s in node.body:
            self._node(s)
        self._emit(Op.JUMP_BACK, loop_top)
        self._patch(patch, len(self.code))
        self._emit(Op.FOR_END)

    def _while(self, node: WhileNode):
        cond_addr = len(self.code)
        self._expr(node.cond)
        patch = self._emit(Op.JUMP_IF_FALSE, None)
        for s in node.body:
            self._node(s)
        self._emit(Op.JUMP_BACK, cond_addr)
        self._patch(patch, len(self.code))

    def _lattice(self, node: LatticeNode):
        saved_code = self.code
        self.code = []
        for p in node.params:
            self._emit(Op.STORE_NAME, p)
        for s in node.body:
            self._node(s)
        if not self.code or self.code[-1].op != Op.RETURN:
            self._emit(Op.RETURN)
        self.functions[node.name] = self.code
        self.code = saved_code
        if node.binding and node.binding in self.registry:
            info = self.registry[node.binding]
            self.func_seals[node.name] = (info['data'], info['raw_sig'])
        self._emit(Op.MAKE_FUNC, node.name)


A9B_LEGACY_CONTRACT_VERSION = "aether9.artifact.v1"
A9B_CONTRACT_VERSION = "aether9.artifact.v2"
A9B_JSON_VERSION = "2.0-json"
A9B_BINARY_VERSION = "2.0-binary"
A9B_LEGACY_JSON_VERSIONS = {"1.0", "1.1-json"}
A9B_LEGACY_BINARY_VERSIONS = {"1.0-binary"}
A9B_BINARY_MAGIC = b"A9B9"
A9B_HEADER = struct.Struct(">4sHHII32s")
A9B_SECTION = struct.Struct(">HHQQ32s")
SECTION_MANIFEST, SECTION_MAIN, SECTION_FUNCTIONS, SECTION_FUNC_SEALS, SECTION_REGISTRY = 1, 2, 3, 4, 5
CODEC_JSON, CODEC_A9BIN = 1, 2
T_NONE, T_BOOL, T_INT, T_STR, T_LIST, T_TUPLE, T_DICT = range(7)


class BytecodeFormatError(Exception):
    """Raised when an .a9b artifact is malformed or fails integrity checks."""


def _u32(n: int) -> bytes:
    return struct.pack(">I", n)


def _read_u32(buf: bytes, pos: int):
    if pos + 4 > len(buf):
        raise BytecodeFormatError("unexpected end of binary value")
    return struct.unpack_from(">I", buf, pos)[0], pos + 4


def _blob(data: bytes) -> bytes:
    return _u32(len(data)) + data


def _read_blob(buf: bytes, pos: int):
    n, pos = _read_u32(buf, pos)
    end = pos + n
    if end > len(buf):
        raise BytecodeFormatError("truncated length-prefixed blob")
    return buf[pos:end], end


def _encode_value(value: Any) -> bytes:
    if value is None:
        return bytes([T_NONE])
    if isinstance(value, bool):
        return bytes([T_BOOL, int(value)])
    if isinstance(value, int):
        return bytes([T_INT]) + _blob(str(value).encode("ascii"))
    if isinstance(value, str):
        return bytes([T_STR]) + _blob(value.encode("utf-8"))
    if isinstance(value, list):
        return bytes([T_LIST]) + _u32(len(value)) + b"".join(_encode_value(v) for v in value)
    if isinstance(value, tuple):
        return bytes([T_TUPLE]) + _u32(len(value)) + b"".join(_encode_value(v) for v in value)
    if isinstance(value, dict):
        items = sorted(value.items(), key=lambda kv: str(kv[0]))
        out = bytearray([T_DICT]) + _u32(len(items))
        for k, v in items:
            out += _encode_value(str(k)) + _encode_value(v)
        return bytes(out)
    raise BytecodeFormatError(f"unsupported binary value type: {type(value).__name__}")


def _decode_value(buf: bytes, pos: int = 0):
    if pos >= len(buf):
        raise BytecodeFormatError("missing binary value type tag")
    tag, pos = buf[pos], pos + 1
    if tag == T_NONE:
        return None, pos
    if tag == T_BOOL:
        if pos >= len(buf):
            raise BytecodeFormatError("truncated boolean value")
        return bool(buf[pos]), pos + 1
    if tag == T_INT:
        raw, pos = _read_blob(buf, pos)
        return int(raw.decode("ascii")), pos
    if tag == T_STR:
        raw, pos = _read_blob(buf, pos)
        return raw.decode("utf-8"), pos
    if tag in (T_LIST, T_TUPLE):
        n, pos = _read_u32(buf, pos)
        vals = []
        for _ in range(n):
            v, pos = _decode_value(buf, pos)
            vals.append(v)
        return (tuple(vals) if tag == T_TUPLE else vals), pos
    if tag == T_DICT:
        n, pos = _read_u32(buf, pos)
        d = {}
        for _ in range(n):
            k, pos = _decode_value(buf, pos)
            v, pos = _decode_value(buf, pos)
            d[k] = v
        return d, pos
    raise BytecodeFormatError(f"unknown binary value type tag: {tag}")


def _decode_full_value(buf: bytes) -> Any:
    value, pos = _decode_value(buf, 0)
    if pos != len(buf):
        raise BytecodeFormatError("trailing bytes after binary value")
    return value


def _supported_contract(contract: str | None) -> bool:
    return contract in {A9B_LEGACY_CONTRACT_VERSION, A9B_CONTRACT_VERSION}


def _section_name(section_id: int) -> str:
    return {
        SECTION_MANIFEST: 'manifest',
        SECTION_MAIN: 'instructions',
        SECTION_FUNCTIONS: 'functions',
        SECTION_FUNC_SEALS: 'func_seals',
        SECTION_REGISTRY: 'registry',
    }.get(section_id, f'section_{section_id}')


def _codec_name(codec: int) -> str:
    return {
        CODEC_JSON: 'json',
        CODEC_A9BIN: 'a9bin',
    }.get(codec, f'codec_{codec}')


@dataclass
class Bytecode:
    instructions: List[Instruction]
    functions: Dict[str, List[Instruction]]
    func_seals: Dict[str, Tuple[List, int]]
    registry: Dict

    def disassemble(self, *, verbose: bool = False) -> str:
        lines = []
        if verbose:
            lines.extend([
                '=== artifact summary ===',
                f"contract           {A9B_CONTRACT_VERSION}",
                f"instruction_count  {len(self.instructions)}",
                f"functions          {sorted(self.functions.keys())}",
                f"arrays             {sorted(self.registry.keys())}",
                f"sealed_functions   {sorted(self.func_seals.keys())}",
                'opcode_histogram  ' + ', '.join(f"{k}={v}" for k, v in self.opcode_histogram().items()),
                '',
            ])
        lines.append("=== main ===")
        for i, ins in enumerate(self.instructions):
            lines.append(f"  {i:4d}  {ins}")
        for name, code in self.functions.items():
            seal = self.func_seals.get(name)
            summary = self.function_summaries()[name]
            prefix = f"\n=== {name} {'[sealed]' if seal else '[pure]'}"
            if verbose:
                prefix += f" params={summary['params']} instructions={summary['instruction_count']}"
            prefix += ' ==='
            lines.append(prefix)
            for i, ins in enumerate(code):
                lines.append(f"  {i:4d}  {ins}")
        return '\n'.join(lines)

    @staticmethod
    def _ser_ins(items):
        return [{'op': i.op.name, 'arg': i.arg} for i in items]

    @staticmethod
    def _des_ins(items):
        out = []
        for item in items:
            try:
                op = Op[item['op']]
            except KeyError as e:
                raise BytecodeFormatError(f"unknown opcode in artifact: {item.get('op')!r}") from e
            arg = item.get('arg')
            if op in (Op.CALL_FUNC, Op.CALL_BUILTIN) and isinstance(arg, list):
                arg = tuple(arg)
            out.append(Instruction(op, arg))
        return out

    def opcode_histogram(self) -> Dict[str, int]:
        counts = Counter(ins.op.name for ins in self.instructions)
        for code in self.functions.values():
            counts.update(ins.op.name for ins in code)
        return dict(sorted(counts.items()))

    def function_summaries(self) -> Dict[str, Dict[str, Any]]:
        summaries = {}
        for name, code in sorted(self.functions.items()):
            params = []
            for ins in code:
                if ins.op == Op.STORE_NAME and ins.arg not in params:
                    params.append(ins.arg)
                    continue
                break
            summaries[name] = {
                'instruction_count': len(code),
                'sealed': name in self.func_seals,
                'params': params,
            }
        return summaries

    def artifact_contract(self, *, binary: bool = False) -> Dict[str, Any]:
        functions = sorted(self.functions.keys())
        arrays = sorted(self.registry.keys())
        histogram = self.opcode_histogram()
        summaries = self.function_summaries()
        sections = [
            {
                'name': _section_name(SECTION_MANIFEST),
                'section_id': SECTION_MANIFEST,
                'codec': _codec_name(CODEC_JSON),
                'required': True,
            },
            {
                'name': _section_name(SECTION_MAIN),
                'section_id': SECTION_MAIN,
                'codec': _codec_name(CODEC_A9BIN),
                'required': True,
            },
            {
                'name': _section_name(SECTION_FUNCTIONS),
                'section_id': SECTION_FUNCTIONS,
                'codec': _codec_name(CODEC_A9BIN),
                'required': True,
            },
            {
                'name': _section_name(SECTION_FUNC_SEALS),
                'section_id': SECTION_FUNC_SEALS,
                'codec': _codec_name(CODEC_A9BIN),
                'required': True,
            },
            {
                'name': _section_name(SECTION_REGISTRY),
                'section_id': SECTION_REGISTRY,
                'codec': _codec_name(CODEC_A9BIN),
                'required': True,
            },
        ] if binary else [
            {
                'name': 'json',
                'section_id': 0,
                'codec': 'json',
                'required': True,
            }
        ]
        counts = {
            'instructions': len(self.instructions),
            'functions': len(functions),
            'arrays': len(arrays),
            'sealed_functions': len(self.func_seals),
        }
        names = {
            'functions': functions,
            'arrays': arrays,
        }
        integrity = {
            'sealed_function_count': len(self.func_seals),
            'opcode_histogram': histogram,
            'function_summaries': summaries,
        }
        metadata = {
            'contract': A9B_CONTRACT_VERSION,
            'schema_version': 2,
            'artifact_kind': 'bytecode',
            'version': A9B_BINARY_VERSION if binary else A9B_JSON_VERSION,
            'format': 'aether9-bytecode-binary' if binary else 'aether9-bytecode-json',
            'container': {
                'type': 'binary' if binary else 'json',
                'magic': A9B_BINARY_MAGIC.decode('ascii') if binary else None,
                'legacy_versions_supported': sorted(A9B_LEGACY_BINARY_VERSIONS if binary else A9B_LEGACY_JSON_VERSIONS),
            },
            'compatibility': {
                'legacy_contracts_supported': [A9B_LEGACY_CONTRACT_VERSION],
                'current_contract': A9B_CONTRACT_VERSION,
            },
            'sections': sections,
            'counts': counts,
            'names': names,
            'integrity': integrity,
            # legacy compatibility fields kept for existing callers/tests
            'instruction_count': counts['instructions'],
            'functions': functions,
            'arrays': arrays,
            'opcodes': [op.name for op in Op],
            'opcode_histogram': histogram,
            'function_summaries': summaries,
            'sealed_function_count': len(self.func_seals),
        }
        return metadata

    def to_artifact_dict(self) -> Dict[str, Any]:
        manifest = self.artifact_contract(binary=False)
        data = {
            'manifest': manifest,
            'instructions': self._ser_ins(self.instructions),
            'functions': {k: self._ser_ins(v) for k, v in sorted(self.functions.items())},
            'func_seals': {k: list(v) for k, v in sorted(self.func_seals.items())},
            'registry': self.registry,
        }
        data.update({
            'contract': manifest['contract'],
            'version': manifest['version'],
            'format': manifest['format'],
            'instruction_count': manifest['instruction_count'],
            'functions_list': manifest['functions'],
            'arrays_list': manifest['arrays'],
        })
        return data

    @classmethod
    def from_artifact_dict(cls, data: Dict[str, Any]) -> 'Bytecode':
        manifest = data.get('manifest', {}) if isinstance(data.get('manifest'), dict) else {}
        contract = manifest.get('contract') or data.get('contract')
        version = manifest.get('version') or data.get('version', '1.0')
        if contract and not _supported_contract(contract):
            raise BytecodeFormatError(f"unsupported .a9b contract: {contract!r}")
        supported_versions = {'1.0', *A9B_LEGACY_JSON_VERSIONS, *A9B_LEGACY_BINARY_VERSIONS, A9B_JSON_VERSION, A9B_BINARY_VERSION}
        if version not in supported_versions:
            raise BytecodeFormatError(f"unsupported .a9b version: {version!r}")
        if 'instructions' not in data:
            raise BytecodeFormatError("artifact missing instructions section")
        return cls(
            instructions=cls._des_ins(data['instructions']),
            functions={k: cls._des_ins(v) for k, v in data.get('functions', {}).items()},
            func_seals={k: tuple(v) for k, v in data.get('func_seals', {}).items()},
            registry=data.get('registry', {}),
        )

    def save(self, path: str, *, format: str = 'json'):
        if format == 'json':
            return self.save_json(path)
        if format in ('binary', 'bin'):
            return self.save_binary(path)
        raise BytecodeFormatError(f"unsupported save format: {format!r}")

    def save_json(self, path: str):
        with open(path, 'w', encoding='utf-8') as f:
            f.write(json.dumps(self.to_artifact_dict(), indent=2, sort_keys=True) + '\n')

    @staticmethod
    def _encode_instruction_list(instructions):
        out = bytearray(_u32(len(instructions)))
        for ins in instructions:
            out += struct.pack(">H", ins.op.value) + _blob(_encode_value(ins.arg))
        return bytes(out)

    @staticmethod
    def _decode_instruction_list(buf):
        pos = 0
        count, pos = _read_u32(buf, pos)
        by_value = {op.value: op for op in Op}
        out = []
        for _ in range(count):
            if pos + 2 > len(buf):
                raise BytecodeFormatError("truncated opcode id")
            op_id = struct.unpack_from(">H", buf, pos)[0]
            pos += 2
            arg_blob, pos = _read_blob(buf, pos)
            if op_id not in by_value:
                raise BytecodeFormatError(f"unknown opcode id: {op_id}")
            out.append(Instruction(by_value[op_id], _decode_full_value(arg_blob)))
        if pos != len(buf):
            raise BytecodeFormatError("trailing bytes after instruction stream")
        return out

    @classmethod
    def _encode_functions(cls, functions):
        items = sorted(functions.items())
        out = bytearray(_u32(len(items)))
        for name, code in items:
            out += _blob(name.encode('utf-8')) + _blob(cls._encode_instruction_list(code))
        return bytes(out)

    @classmethod
    def _decode_functions(cls, buf):
        pos = 0
        count, pos = _read_u32(buf, pos)
        out = {}
        for _ in range(count):
            name, pos = _read_blob(buf, pos)
            code, pos = _read_blob(buf, pos)
            out[name.decode('utf-8')] = cls._decode_instruction_list(code)
        if pos != len(buf):
            raise BytecodeFormatError("trailing bytes after function table")
        return out

    def save_binary(self, path: str):
        manifest = json.dumps(self.artifact_contract(binary=True), sort_keys=True, separators=(',', ':')).encode('utf-8')
        sections = [
            (SECTION_MANIFEST, CODEC_JSON, manifest),
            (SECTION_MAIN, CODEC_A9BIN, self._encode_instruction_list(self.instructions)),
            (SECTION_FUNCTIONS, CODEC_A9BIN, self._encode_functions(self.functions)),
            (SECTION_FUNC_SEALS, CODEC_A9BIN, _encode_value(self.func_seals)),
            (SECTION_REGISTRY, CODEC_A9BIN, _encode_value(self.registry)),
        ]
        offset = A9B_HEADER.size + A9B_SECTION.size * len(sections)
        table, payload = bytearray(), bytearray()
        for section_id, codec, body in sections:
            table += A9B_SECTION.pack(section_id, codec, offset, len(body), hashlib.sha256(body).digest())
            payload += body
            offset += len(body)
        digest = hashlib.sha256(bytes(table) + bytes(payload)).digest()
        header = A9B_HEADER.pack(A9B_BINARY_MAGIC, 1, 0, 0, len(sections), digest)
        with open(path, 'wb') as f:
            f.write(header + table + payload)

    @classmethod
    def _load_binary_bytes(cls, raw: bytes) -> 'Bytecode':
        if len(raw) < A9B_HEADER.size:
            raise BytecodeFormatError("binary .a9b is shorter than header")
        magic, major, minor, flags, count, digest = A9B_HEADER.unpack_from(raw, 0)
        if magic != A9B_BINARY_MAGIC:
            raise BytecodeFormatError("invalid binary .a9b magic")
        if (major, minor) != (1, 0):
            raise BytecodeFormatError(f"unsupported binary .a9b version: {major}.{minor}")
        table_start = A9B_HEADER.size
        table_end = table_start + A9B_SECTION.size * count
        if table_end > len(raw):
            raise BytecodeFormatError("truncated binary .a9b section table")
        table = raw[table_start:table_end]
        payload = raw[table_end:]
        if hashlib.sha256(table + payload).digest() != digest:
            raise BytecodeFormatError("binary .a9b container checksum mismatch")
        sections = {}
        for idx in range(count):
            entry_pos = table_start + idx * A9B_SECTION.size
            section_id, codec, offset, length, sha = A9B_SECTION.unpack_from(raw, entry_pos)
            end = offset + length
            if end > len(raw):
                raise BytecodeFormatError(f"section {section_id} points past end of file")
            body = raw[offset:end]
            if hashlib.sha256(body).digest() != sha:
                raise BytecodeFormatError(f"section {section_id} checksum mismatch")
            sections[section_id] = (codec, body)
        required = {SECTION_MANIFEST, SECTION_MAIN, SECTION_FUNCTIONS, SECTION_FUNC_SEALS, SECTION_REGISTRY}
        missing = required - set(sections)
        if missing:
            raise BytecodeFormatError(f"binary .a9b missing sections: {sorted(missing)}")
        manifest = json.loads(sections[SECTION_MANIFEST][1].decode('utf-8'))
        contract = manifest.get('contract')
        if not _supported_contract(contract):
            raise BytecodeFormatError(f"binary .a9b contract mismatch: {contract!r}")
        return cls(
            instructions=cls._decode_instruction_list(sections[SECTION_MAIN][1]),
            functions=cls._decode_functions(sections[SECTION_FUNCTIONS][1]),
            func_seals={k: tuple(v) for k, v in _decode_full_value(sections[SECTION_FUNC_SEALS][1]).items()},
            registry=_decode_full_value(sections[SECTION_REGISTRY][1]),
        )

    @classmethod
    def load(cls, path: str) -> 'Bytecode':
        raw = open(path, 'rb').read()
        if raw.startswith(A9B_BINARY_MAGIC):
            return cls._load_binary_bytes(raw)
        try:
            return cls.from_artifact_dict(json.loads(raw.decode('utf-8')))
        except Exception as e:
            if isinstance(e, BytecodeFormatError):
                raise
            raise BytecodeFormatError(f"unable to load .a9b artifact: {e}") from e

    @classmethod
    def inspect_file(cls, path: str) -> Dict[str, Any]:
        raw = open(path, 'rb').read()
        if raw.startswith(A9B_BINARY_MAGIC):
            if len(raw) < A9B_HEADER.size:
                raise BytecodeFormatError('binary .a9b is shorter than header')
            magic, major, minor, flags, count, digest = A9B_HEADER.unpack_from(raw, 0)
            table_start = A9B_HEADER.size
            table_end = table_start + A9B_SECTION.size * count
            if table_end > len(raw):
                raise BytecodeFormatError('truncated binary .a9b section table')
            table = raw[table_start:table_end]
            payload = raw[table_end:]
            bc = cls._load_binary_bytes(raw)
            meta = bc.artifact_contract(binary=True)
            section_details = []
            for idx in range(count):
                entry_pos = table_start + idx * A9B_SECTION.size
                section_id, codec, offset, length, sha = A9B_SECTION.unpack_from(raw, entry_pos)
                section_details.append({
                    'name': _section_name(section_id),
                    'section_id': section_id,
                    'codec': _codec_name(codec),
                    'offset': offset,
                    'length': length,
                    'sha256_prefix': sha.hex()[:16],
                })
            meta['byte_size'] = len(raw)
            meta['binary_header'] = {
                'magic': magic.decode('ascii'),
                'major': major,
                'minor': minor,
                'flags': flags,
                'section_count': count,
                'container_checksum_prefix': digest.hex()[:16],
            }
            meta['sections'] = section_details
            meta['integrity'].update({
                'container_checksum_prefix': digest.hex()[:16],
                'table_checksum_prefix': hashlib.sha256(table + payload).hexdigest()[:16],
            })
            return meta
        data = json.loads(raw.decode('utf-8'))
        bc = cls.from_artifact_dict(data)
        manifest = data.get('manifest') if isinstance(data.get('manifest'), dict) else None
        meta = bc.artifact_contract(binary=False)
        if manifest:
            # preserve actual manifest version/contract when inspecting saved artifacts
            meta['contract'] = manifest.get('contract', meta['contract'])
            meta['version'] = manifest.get('version', meta['version'])
            meta['format'] = manifest.get('format', meta['format'])
            meta['schema_version'] = manifest.get('schema_version', meta.get('schema_version'))
        meta['byte_size'] = len(raw)
        meta['json_keys'] = sorted(data.keys())
        meta['sections'] = [{'name': 'json', 'section_id': 0, 'codec': 'json', 'length': len(raw), 'required': True}]
        return meta


@dataclass
class VMTraceEntry:
    frame: str
    ip: int
    op: str
    arg: Any
    stack_depth: int


class VMError(Exception):
    category = 'vm_error'

    def __init__(
        self,
        message: str,
        *,
        frame: Optional[str] = None,
        ip: Optional[int] = None,
        op: Optional[str] = None,
        arg: Any = None,
        stack_tail: Optional[List[str]] = None,
        locals_visible: Optional[List[str]] = None,
        call_stack: Optional[List[str]] = None,
        trace: Optional[List[VMTraceEntry]] = None,
        cause: Optional[str] = None,
    ):
        super().__init__(message)
        self.message = message
        self.frame = frame
        self.ip = ip
        self.op = op
        self.arg = arg
        self.stack_tail = stack_tail or []
        self.locals_visible = locals_visible or []
        self.call_stack = call_stack or []
        self.trace = trace or []
        self.cause = cause

    def format(self) -> str:
        lines = [f'{self.category}: {self.message}']
        if self.frame is not None:
            lines.append(
                f'  frame={self.frame} ip={self.ip} op={self.op} arg={self.arg!r}'
            )
        if self.call_stack:
            lines.append(f"  call_stack={' -> '.join(self.call_stack)}")
        if self.stack_tail:
            lines.append(f"  stack_tail=[{', '.join(self.stack_tail)}]")
        if self.locals_visible:
            lines.append(f"  locals={self.locals_visible}")
        if self.cause:
            lines.append(f'  cause={self.cause}')
        if self.trace:
            lines.append('  recent_trace:')
            for entry in self.trace[-8:]:
                lines.append(
                    f"    - {entry.frame}@{entry.ip}: {entry.op} {entry.arg!r} (stack_depth={entry.stack_depth})"
                )
        return '\n'.join(lines)

    def __str__(self) -> str:
        return self.format()


class VMValidationError(VMError):
    category = 'validation_error'


class VMExecutionError(VMError):
    category = 'execution_error'


class VMStackError(VMExecutionError):
    category = 'stack_error'


class VMNameError(VMExecutionError):
    category = 'name_error'


class VMArityError(VMExecutionError):
    category = 'arity_error'


class VMSecurityError(VMExecutionError):
    category = 'security_error'


class VMHalt(Exception):
    pass


def _digital_root(v: int) -> int:
    s = str(abs(int(v)))
    d = sum(int(c) for c in s)
    while d > 9:
        d = sum(int(c) for c in str(d))
    return 9 if d in (9, 0) else d


STDLIB = {
    'abs': lambda a: abs(a),
    'min': lambda a, b: min(a, b),
    'max': lambda a, b: max(a, b),
    'len': lambda a: len(str(a)),
    'str': lambda a: str(a),
    'concat': lambda a, b: str(a) + str(b),
    'dr': lambda a: _digital_root(a),
    'mod': lambda a, b: (a % b) or 9,
}


class Frame:
    def __init__(self, name: str, code: List[Instruction], args: Dict, caller_ns: Dict):
        self.name = name
        self.code = code
        self.ip = 0
        self.stack: List[Any] = []
        self.locals: Dict[str, Any] = dict(args)
        self.caller_ns = caller_ns

    def push(self, v):
        self.stack.append(v)

    def pop(self):
        return self.stack.pop()

    def peek(self):
        return self.stack[-1]


class AetherVM:
    def __init__(self, workdir: str = '.', *, trace_limit: int = 25):
        self.workdir = workdir
        self.ns: Dict[str, Any] = {}
        self.fns: Dict[str, List[Instruction]] = {}
        self.seals: Dict[str, Tuple] = {}
        self.call_stack: List[str] = []
        self.trace_limit = max(1, trace_limit)
        self.trace_buffer: Deque[VMTraceEntry] = deque(maxlen=self.trace_limit)

    def run(self, bc: Bytecode) -> Any:
        self.fns = bc.functions
        self.seals = bc.func_seals
        self.call_stack = []
        self.trace_buffer.clear()
        self.ns = {}
        for name, info in bc.registry.items():
            self.ns[name] = info['data']
        frame = Frame('__main__', bc.instructions, {}, self.ns)
        return self._exec(frame)

    @staticmethod
    def _safe_repr(value: Any, *, limit: int = 48) -> str:
        text = repr(value)
        return text if len(text) <= limit else text[: limit - 3] + '...'

    def _call_path(self, frame: Frame) -> List[str]:
        if self.call_stack and self.call_stack[-1] == frame.name:
            return list(self.call_stack)
        return list(self.call_stack) + [frame.name]

    def _remember_trace(self, frame: Frame, ins: Instruction) -> None:
        self.trace_buffer.append(
            VMTraceEntry(
                frame=frame.name,
                ip=max(frame.ip - 1, 0),
                op=ins.op.name,
                arg=ins.arg,
                stack_depth=len(frame.stack),
            )
        )

    def _raise(self, frame: Frame, ins: Instruction, message: str, *, exc_type=VMExecutionError, cause: Optional[Exception] = None):
        raise exc_type(
            message,
            frame=frame.name,
            ip=max(frame.ip - 1, 0),
            op=ins.op.name,
            arg=ins.arg,
            stack_tail=[self._safe_repr(v) for v in frame.stack[-5:]],
            locals_visible=sorted(frame.locals.keys()),
            call_stack=self._call_path(frame),
            trace=list(self.trace_buffer),
            cause=None if cause is None else f'{type(cause).__name__}: {cause}',
        )

    def _require_stack(self, frame: Frame, ins: Instruction, count: int):
        if len(frame.stack) < count:
            self._raise(frame, ins, f"stack underflow: need {count}, have {len(frame.stack)}", exc_type=VMStackError)

    def _validate_target(self, frame: Frame, ins: Instruction, target: int):
        if not isinstance(target, int) or not (0 <= target <= len(frame.code)):
            self._raise(frame, ins, f"invalid jump target: {target!r}", exc_type=VMValidationError)

    def _get_params(self, fname: str) -> List[str]:
        params = []
        for ins in self.fns.get(fname, []):
            if ins.op == Op.STORE_NAME and ins.arg not in params:
                params.append(ins.arg)
                continue
            break
        return params

    def _exec(self, frame: Frame) -> Any:
        code = frame.code
        ns = frame.locals if frame.name != '__main__' else self.ns

        while frame.ip < len(code):
            ins = code[frame.ip]
            frame.ip += 1
            op, arg = ins.op, ins.arg
            self._remember_trace(frame, ins)

            try:
                if op == Op.LOAD_CONST:
                    frame.push(arg)

                elif op == Op.LOAD_NAME:
                    sentinel = object()
                    val = ns.get(arg, sentinel)
                    if val is sentinel:
                        val = self.ns.get(arg, sentinel)
                    if val is sentinel:
                        self._raise(frame, ins, f"name '{arg}' is not defined", exc_type=VMNameError)
                    frame.push(val)

                elif op == Op.STORE_NAME:
                    self._require_stack(frame, ins, 1)
                    ns[arg] = frame.pop()

                elif op == Op.POP:
                    self._require_stack(frame, ins, 1)
                    frame.pop()

                elif op == Op.BINARY_OP:
                    self._require_stack(frame, ins, 2)
                    b, a = frame.pop(), frame.pop()
                    ops = {
                        '+': lambda x, y: x + y,
                        '-': lambda x, y: x - y,
                        '*': lambda x, y: x * y,
                        '/': lambda x, y: x // y,
                        '%': lambda x, y: x % y,
                        'or': lambda x, y: x or y,
                        'and': lambda x, y: x and y,
                    }
                    fn = ops.get(arg)
                    if fn is None:
                        self._raise(frame, ins, f"unknown binary op: {arg!r}", exc_type=VMValidationError)
                    frame.push(fn(a, b))

                elif op == Op.COMPARE:
                    self._require_stack(frame, ins, 2)
                    b, a = frame.pop(), frame.pop()
                    if arg == '==':
                        frame.push(a == b)
                    elif arg == '!=':
                        frame.push(a != b)
                    elif arg == '<':
                        frame.push(a < b)
                    elif arg == '>':
                        frame.push(a > b)
                    elif arg == '<=':
                        frame.push(a <= b)
                    elif arg == '>=':
                        frame.push(a >= b)
                    else:
                        self._raise(frame, ins, f"unknown compare op: {arg!r}", exc_type=VMValidationError)

                elif op == Op.UNARY_NEG:
                    self._require_stack(frame, ins, 1)
                    frame.push(-frame.pop())

                elif op == Op.JUMP:
                    self._validate_target(frame, ins, arg)
                    frame.ip = arg

                elif op == Op.JUMP_IF_FALSE:
                    self._validate_target(frame, ins, arg)
                    self._require_stack(frame, ins, 1)
                    if not frame.pop():
                        frame.ip = arg

                elif op == Op.JUMP_BACK:
                    self._validate_target(frame, ins, arg)
                    frame.ip = arg

                elif op == Op.FOR_START:
                    self._require_stack(frame, ins, 1)
                    iterable = frame.pop()
                    try:
                        iterator = iter(iterable)
                    except TypeError as e:
                        self._raise(frame, ins, f"value is not iterable: {iterable!r}")
                    frame.push((iterator, arg))

                elif op == Op.FOR_NEXT:
                    self._validate_target(frame, ins, arg)
                    if not frame.stack:
                        frame.ip = arg
                        continue
                    it_state = frame.stack[-1]
                    if not (isinstance(it_state, tuple) and len(it_state) == 2):
                        self._raise(frame, ins, "invalid iterator state on stack")
                    iterator, var_name = it_state
                    try:
                        ns[var_name] = next(iterator)
                    except StopIteration:
                        frame.pop()
                        frame.ip = arg

                elif op == Op.FOR_END:
                    pass

                elif op == Op.MAKE_FUNC:
                    pass

                elif op == Op.CALL_FUNC:
                    fname, nargs = arg
                    fn_code = self.fns.get(fname)
                    if fn_code is None:
                        self._raise(frame, ins, f"undefined lattice: '{fname}'", exc_type=VMNameError)
                    if fname in self.seals:
                        data, expected_sig = self.seals[fname]
                        from aether9.core import VortexSequencer as VS
                        actual, _ = VS(data).compute_seal()
                        if actual != expected_sig:
                            self._raise(
                                frame,
                                ins,
                                f"Vortex tampered in '{fname}': got={actual}, expected={expected_sig}",
                                exc_type=VMSecurityError,
                            )
                    self._require_stack(frame, ins, nargs)
                    args_vals = [frame.pop() for _ in range(nargs)][::-1]
                    params = self._get_params(fname)
                    if len(params) != nargs:
                        self._raise(
                            frame,
                            ins,
                            f"arity mismatch for '{fname}': expected {len(params)}, got {nargs}",
                            exc_type=VMArityError,
                        )
                    child = Frame(fname, fn_code, dict(zip(params, args_vals)), ns)
                    child.ip = len(params)
                    self.call_stack.append(fname)
                    try:
                        result = self._exec(child)
                    finally:
                        self.call_stack.pop()
                    if result is not None and result != 0 and _digital_root(result) != 9:
                        self._raise(frame, ins, f"Lattice asymmetry in '{fname}': root={_digital_root(result)}, expected=9")
                    frame.push(result)

                elif op == Op.RETURN:
                    self._require_stack(frame, ins, 1)
                    val = frame.pop()
                    return val or 9

                elif op == Op.PRINT:
                    self._require_stack(frame, ins, arg)
                    vals = [frame.pop() for _ in range(arg)][::-1]
                    print(*vals)
                    frame.push(None)

                elif op == Op.WRITE:
                    self._require_stack(frame, ins, 2)
                    val, fname = frame.pop(), frame.pop()
                    path = os.path.join(self.workdir, os.path.basename(str(fname)))
                    open(path, 'w').write(str(val) + '\n')
                    frame.push(9)

                elif op == Op.READ:
                    self._require_stack(frame, ins, 1)
                    fname = frame.pop()
                    path = os.path.join(self.workdir, os.path.basename(str(fname)))
                    content = open(path).read().strip()
                    try:
                        frame.push(int(content))
                    except ValueError:
                        frame.push(content)

                elif op == Op.CALL_BUILTIN:
                    fname, nargs = arg
                    self._require_stack(frame, ins, nargs)
                    vals = [frame.pop() for _ in range(nargs)][::-1]
                    fn = STDLIB.get(fname)
                    if fn is None:
                        self._raise(frame, ins, f"unknown builtin: '{fname}'", exc_type=VMValidationError)
                    frame.push(fn(*vals))

                elif op == Op.HALT:
                    return None

                else:
                    self._raise(frame, ins, f"unsupported opcode: {op!r}", exc_type=VMValidationError)

            except (VMError, VMSecurityError):
                raise
            except Exception as e:
                self._raise(frame, ins, 'unexpected runtime failure', cause=e)

        return None


def compile_to_bytecode(source: str) -> Tuple[Bytecode, Dict]:
    compiler = Aether9Compiler()
    _, registry = compiler.compile(source)

    from .compiler import Lexer, Parser
    tokens = Lexer(source).tokenize()
    ast = Parser(tokens).parse()

    bc = BytecodeCompiler(registry).compile(ast)
    return bc, registry


def run_bytecode(bc: Bytecode, registry: Dict, workdir: str = '.') -> None:
    vm = AetherVM(workdir=workdir)
    vm.run(bc)
