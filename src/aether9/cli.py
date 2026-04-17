#!/usr/bin/env python3
"""Aether-9 command line interface.

Stage 4 hardening goals:
- Stable subcommands instead of a single positional command switch.
- Official JSON and binary bytecode export paths for .a9 -> .a9b.
- Auto-detect inspect/disassemble/verify/run support for JSON and A9B9 binary .a9b containers.
- Backward-compatible source compile/signature commands.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

from .compiler import Aether9Compiler, CompileError, LexError, ParseError
from .core import VortexSequencer
from .repl import run_shell
from .signature import SignatureFile
from .vm import AetherVM, Bytecode, Instruction, Op, VMError, compile_to_bytecode, run_bytecode


class CLIError(Exception):
    """User-facing CLI error."""


G = "\033[32m"
R = "\033[31m"
X = "\033[0m"


def _ok(message: str) -> None:
    print(f"  {G}✓{X}  {message}")


def _fail(message: str) -> None:
    print(f"  {R}✗{X}  {message}", file=sys.stderr)


def _info(message: str) -> None:
    print(f"      {message}")


def _die(message: str) -> None:
    raise CLIError(message)


def _paths(source_file: str | Path) -> Tuple[Path, Path, Path, Path]:
    p = Path(source_file)
    return p, p.with_suffix(".py"), p.with_suffix(".a9s"), p.with_suffix(".a9b")


def _read(path: str | Path) -> str:
    p = Path(path)
    if not p.exists():
        _die(f"file not found: {p}")
    return p.read_text(encoding="utf-8")


def _load_source(path: str | Path) -> Tuple[Path, str]:
    p = Path(path)
    return p, _read(p)


def _compile_source_to_python(source_path: Path, source: str, py_path: Path, sig_path: Path):
    code, registry = Aether9Compiler().compile(source)
    sig = SignatureFile.generate(source, registry, source_path.name)
    py_path.write_text(code, encoding="utf-8")
    SignatureFile.save(sig, str(sig_path))
    return code, sig


def _compile_source_to_bytecode(source_path: Path, source: str) -> Bytecode:
    bc, _registry = compile_to_bytecode(source)
    return bc


def _format_mac(sig: dict) -> str:
    value = sig.get("global_mac", sig.get("global_seal", "—"))
    if isinstance(value, str) and len(value) > 16:
        return value[:16] + "..."
    return str(value)


def _iter_codes(bc: Bytecode) -> Iterable[Tuple[str, List[Instruction]]]:
    yield "__main__", bc.instructions
    for name, code in bc.functions.items():
        yield name, code


def verify_bytecode_structure(bc: Bytecode) -> Tuple[bool, List[str]]:
    """Validate structural invariants for a loaded bytecode container.

    This is intentionally a structural verifier. Cryptographic integrity for source
    signatures remains the responsibility of .a9s verification.
    """
    errors: List[str] = []

    if not isinstance(bc.instructions, list):
        errors.append("main instructions must be a list")
    if not isinstance(bc.functions, dict):
        errors.append("functions must be a dictionary")
    if not isinstance(bc.func_seals, dict):
        errors.append("func_seals must be a dictionary")

    for frame_name, code in _iter_codes(bc):
        if not isinstance(code, list):
            errors.append(f"{frame_name}: code must be a list")
            continue

        for idx, ins in enumerate(code):
            if not isinstance(ins, Instruction):
                errors.append(f"{frame_name}[{idx}]: invalid instruction object")
                continue
            if not isinstance(ins.op, Op):
                errors.append(f"{frame_name}[{idx}]: invalid opcode {ins.op!r}")
                continue

            if ins.op in (Op.JUMP, Op.JUMP_IF_FALSE, Op.JUMP_BACK, Op.FOR_NEXT):
                if not isinstance(ins.arg, int):
                    errors.append(f"{frame_name}[{idx}]: jump target must be int")
                elif ins.arg < 0 or ins.arg > len(code):
                    errors.append(
                        f"{frame_name}[{idx}]: jump target {ins.arg} outside 0..{len(code)}"
                    )

            elif ins.op == Op.CALL_FUNC:
                if not (isinstance(ins.arg, tuple) and len(ins.arg) == 2):
                    errors.append(f"{frame_name}[{idx}]: CALL_FUNC arg must be (name, nargs)")
                else:
                    fname, nargs = ins.arg
                    if not isinstance(fname, str):
                        errors.append(f"{frame_name}[{idx}]: CALL_FUNC name must be str")
                    elif fname not in bc.functions:
                        errors.append(f"{frame_name}[{idx}]: undefined lattice '{fname}'")
                    if not isinstance(nargs, int) or nargs < 0:
                        errors.append(f"{frame_name}[{idx}]: CALL_FUNC nargs must be non-negative int")

            elif ins.op == Op.CALL_BUILTIN:
                if not (isinstance(ins.arg, tuple) and len(ins.arg) == 2):
                    errors.append(f"{frame_name}[{idx}]: CALL_BUILTIN arg must be (name, nargs)")
                else:
                    fname, nargs = ins.arg
                    if not isinstance(fname, str):
                        errors.append(f"{frame_name}[{idx}]: CALL_BUILTIN name must be str")
                    if not isinstance(nargs, int) or nargs < 0:
                        errors.append(f"{frame_name}[{idx}]: CALL_BUILTIN nargs must be non-negative int")

            elif ins.op == Op.COMPARE:
                if ins.arg not in {"==", "!=", "<", ">", "<=", ">="}:
                    errors.append(f"{frame_name}[{idx}]: unknown comparison op {ins.arg!r}")

            elif ins.op == Op.BINARY_OP:
                if ins.arg not in {"+", "-", "*", "/", "%", "or", "and"}:
                    errors.append(f"{frame_name}[{idx}]: unknown binary op {ins.arg!r}")

    for fname, seal in bc.func_seals.items():
        if fname not in bc.functions:
            errors.append(f"func_seals references unknown lattice '{fname}'")
        if not (isinstance(seal, tuple) and len(seal) == 2):
            errors.append(f"func_seals['{fname}'] must be (data, raw_sig)")
            continue
        data, raw_sig = seal
        if not isinstance(data, list):
            errors.append(f"func_seals['{fname}'].data must be list")
        if not isinstance(raw_sig, int):
            errors.append(f"func_seals['{fname}'].raw_sig must be int")

    return (len(errors) == 0), errors


def cmd_compile(args: argparse.Namespace) -> None:
    source_path, py_path, sig_path, _bc_path = _paths(args.file)
    source = _read(source_path)
    print(f"⚙️   compiling  {source_path.name}")
    code, sig = _compile_source_to_python(source_path, source, py_path, sig_path)
    _ok(f"{py_path.name}   — compiled python")
    _ok(f"{sig_path.name}  — signature file")
    _info(f"arrays      : {list(sig['arrays'].keys())}")
    _info(f"global seal : {_format_mac(sig)}")
    if args.verbose:
        for name, info in sig["arrays"].items():
            _info(f"{name:16s}  hmac={info.get('hmac', '—')[:16]}...")


def cmd_export(args: argparse.Namespace) -> None:
    source_path, _py_path, _sig_path, default_bc_path = _paths(args.file)
    source = _read(source_path)
    fmt = args.format.lower()
    if fmt not in {"json", "binary"}:
        _die("format must be 'json' or 'binary'")

    out_path = Path(args.output) if args.output else default_bc_path
    bc = _compile_source_to_bytecode(source_path, source)
    bc.save(str(out_path), format=fmt)
    print(f"📦  exporting   {source_path.name}")
    label = "A9B9 binary" if fmt == "binary" else "json"
    _ok(f"{out_path.name}  — bytecode container ({label})")
    _info(f"instructions: {len(bc.instructions)}")
    _info(f"functions   : {len(bc.functions)}")


def _run_source_vm(path: Path) -> None:
    source = _read(path)
    bc = _compile_source_to_bytecode(path, source)
    run_bytecode(bc, {}, workdir=str(path.parent))


def _run_source_python(path: Path) -> None:
    source_path, py_path, sig_path, _bc_path = _paths(path)
    source = _read(source_path)
    code, sig = _compile_source_to_python(source_path, source, py_path, sig_path)
    exec(compile(code, str(py_path), "exec"), {"__name__": "__main__"})


def cmd_run(args: argparse.Namespace) -> None:
    path = Path(args.file)
    if not path.exists():
        _die(f"file not found: {path}")

    if path.suffix == ".a9b":
        bc = Bytecode.load(str(path))
        ok, errors = verify_bytecode_structure(bc)
        if not ok:
            _die("bytecode verification failed:\n" + "\n".join(f"- {e}" for e in errors))
        print(f"🚀  running bytecode  {path.name}\n")
        AetherVM(workdir=str(path.parent)).run(bc)
        return

    if path.suffix != ".a9":
        _die("run expects a .a9 source file or a .a9b bytecode file")

    print(f"🚀  running source  {path.name}  [{args.backend} backend]\n")
    if args.backend == "python":
        _run_source_python(path)
    else:
        _run_source_vm(path)


def cmd_verify(args: argparse.Namespace) -> None:
    path = Path(args.file)
    if not path.exists():
        _die(f"file not found: {path}")

    if path.suffix == ".a9b":
        fmt = Bytecode.detect_format(str(path))
        bc = Bytecode.load(str(path))
        ok, errors = verify_bytecode_structure(bc)
        print(f"🔍  verifying bytecode  {path.name}")
        if not ok:
            for error in errors:
                _fail(error)
            raise SystemExit(1)
        _ok("bytecode structure valid")
        _info(f"format      : {fmt}")
        _info(f"instructions: {len(bc.instructions)}")
        _info(f"functions   : {len(bc.functions)}")
        return

    if path.suffix == ".a9s":
        sig = SignatureFile.load(str(path))
        print(f"🔍  inspecting signature  {path.name}")
        _ok("signature file loaded")
        _info(f"source: {sig.get('source', '—')}")
        _info(f"arrays: {list(sig.get('arrays', {}).keys())}")
        return

    if path.suffix != ".a9":
        _die("verify expects a .a9 source file, .a9s signature, or .a9b bytecode file")

    source_path, _py_path, sig_path, _bc_path = _paths(path)
    source = _read(source_path)
    if not sig_path.exists():
        _die(f"no signature file: {sig_path}\n       run 'aether compile {source_path}' first")

    print(f"🔍  verifying source  {source_path.name}")
    sig = SignatureFile.load(str(sig_path))
    ok, msg = SignatureFile.verify(sig, source)
    if not ok:
        _fail(msg)
        raise SystemExit(1)
    _ok("signature valid")
    _info(f"arrays      : {list(sig['arrays'].keys())}")
    _info(f"global seal : {_format_mac(sig)}")
    if args.verbose:
        for name, info in sig["arrays"].items():
            cur, _ = VortexSequencer(info["data"]).compute_seal()
            mark = f"{G}✓{X}" if cur == info["raw_sig"] else f"{R}✗{X}"
            _info(f"{name:16s}  {mark}  hmac={info.get('hmac', '—')[:16]}...")


def _inspect_signature(path: Path) -> None:
    sig = SignatureFile.load(str(path))
    created = sig.get("created_at")
    if isinstance(created, (int, float)):
        ts = _dt.datetime.fromtimestamp(created).strftime("%Y-%m-%d %H:%M:%S")
    else:
        ts = "—"
    width = 56
    print(f"\n{'─' * width}\n  Aether-9 Signature  ·  {path.name}\n{'─' * width}")
    print(f"  version      {sig.get('version', '—')}")
    print(f"  source       {sig.get('source', '—')}")
    print(f"  created      {ts}")
    print(f"  source hash  {str(sig.get('source_hash', '—'))[:20]}…")
    print(f"  global seal  {_format_mac(sig)}")
    print(f"\n  Arrays  ({len(sig.get('arrays', {}))})")
    for name, info in sig.get("arrays", {}).items():
        print(f"    {name}\n      data     {info.get('data')}\n      hmac     {info.get('hmac', '—')[:20]}...")
    print(f"{'─' * width}\n")


def _inspect_bytecode(path: Path) -> None:
    fmt = Bytecode.detect_format(str(path))
    bc = Bytecode.load(str(path))
    ok, errors = verify_bytecode_structure(bc)
    op_counts = {}
    for _name, code in _iter_codes(bc):
        for ins in code:
            op_counts[ins.op.name] = op_counts.get(ins.op.name, 0) + 1

    width = 56
    print(f"\n{'─' * width}\n  Aether-9 Bytecode  ·  {path.name}\n{'─' * width}")
    print(f"  status       {'valid' if ok else 'invalid'}")
    print(f"  format       {fmt}")
    print(f"  main ins     {len(bc.instructions)}")
    print(f"  functions    {len(bc.functions)}")
    print(f"  sealed fns   {len(bc.func_seals)}")
    print("\n  Functions")
    for name, code in bc.functions.items():
        sealed = "sealed" if name in bc.func_seals else "pure"
        print(f"    {name:16s} {len(code):3d} instructions  {sealed}")
    print("\n  Opcodes")
    for op_name in sorted(op_counts):
        print(f"    {op_name:16s} {op_counts[op_name]}")
    if errors:
        print("\n  Errors")
        for error in errors:
            print(f"    - {error}")
    print(f"{'─' * width}\n")


def cmd_inspect(args: argparse.Namespace) -> None:
    path = Path(args.file)
    if not path.exists():
        _die(f"file not found: {path}")

    if path.suffix == ".a9b":
        _inspect_bytecode(path)
    elif path.suffix == ".a9s":
        _inspect_signature(path)
    elif path.suffix == ".a9":
        _sig_path = path.with_suffix(".a9s")
        _bc_path = path.with_suffix(".a9b")
        if _bc_path.exists():
            _inspect_bytecode(_bc_path)
        elif _sig_path.exists():
            _inspect_signature(_sig_path)
        else:
            _die(f"no .a9b or .a9s companion found for {path}")
    else:
        _die("inspect expects .a9, .a9s, or .a9b")


def cmd_disasm(args: argparse.Namespace) -> None:
    path = Path(args.file)
    if not path.exists():
        _die(f"file not found: {path}")

    if path.suffix == ".a9b":
        bc = Bytecode.load(str(path))
    elif path.suffix == ".a9":
        source = _read(path)
        bc = _compile_source_to_bytecode(path, source)
    else:
        _die("disasm expects a .a9 source file or .a9b bytecode file")
    print(bc.disassemble())


def cmd_shell(args: argparse.Namespace) -> None:
    run_shell()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aether",
        description="Aether-9 CLI — compiler, bytecode exporter, VM runner",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_compile = sub.add_parser("compile", help="compile .a9 to Python and create .a9s signature")
    p_compile.add_argument("file")
    p_compile.add_argument("-v", "--verbose", action="store_true")
    p_compile.set_defaults(func=cmd_compile)

    p_run = sub.add_parser("run", help="run .a9 source or .a9b bytecode")
    p_run.add_argument("file")
    p_run.add_argument("--backend", choices=["vm", "python"], default="vm")
    p_run.set_defaults(func=cmd_run)

    p_export = sub.add_parser("export", help="export .a9 source to .a9b bytecode")
    p_export.add_argument("file")
    p_export.add_argument("--format", default="json", choices=["json", "binary"])
    p_export.add_argument("-o", "--output")
    p_export.set_defaults(func=cmd_export)

    p_inspect = sub.add_parser("inspect", help="inspect .a9b bytecode or .a9s signature")
    p_inspect.add_argument("file")
    p_inspect.set_defaults(func=cmd_inspect)

    p_disasm = sub.add_parser("disasm", help="disassemble .a9 or .a9b")
    p_disasm.add_argument("file")
    p_disasm.set_defaults(func=cmd_disasm)

    p_verify = sub.add_parser("verify", help="verify .a9 source signature or .a9b structure")
    p_verify.add_argument("file")
    p_verify.add_argument("-v", "--verbose", action="store_true")
    p_verify.set_defaults(func=cmd_verify)

    p_shell = sub.add_parser("shell", help="start interactive Aether shell")
    p_shell.set_defaults(func=cmd_shell)

    # Backward-compatible alias for older docs/releases.
    p_vm = sub.add_parser("vm", help=argparse.SUPPRESS)
    p_vm.add_argument("file")
    p_vm.set_defaults(func=lambda args: cmd_run(argparse.Namespace(file=args.file, backend="vm")))

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
        return 0
    except (LexError, ParseError, CompileError, VMError) as exc:
        _fail(str(exc))
        return 1
    except CLIError as exc:
        print(f"aether: error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
