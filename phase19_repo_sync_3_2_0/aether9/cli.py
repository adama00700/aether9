#!/usr/bin/env python3
"""aether — Aether-9 Language CLI."""

from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path
from typing import Any, Optional

from . import __version__
from .api import export_file, inspect_path, run_file, verify_file
from .compiler import Aether9Compiler, CompileError, LexError, ParseError
from .core import VortexSequencer
from .repl import run_shell
from .signature import SignatureFile
from .vm import Bytecode, BytecodeFormatError, AetherVM, VMError, compile_to_bytecode


G = "\033[32m"
R = "\033[31m"
X = "\033[0m"


CLI_EXIT_OK = 0
CLI_EXIT_GENERAL = 1
CLI_EXIT_VALIDATION = 2
CLI_EXIT_RUNTIME = 3
CLI_EXIT_USAGE = 4


def _paths(f: str):
    p = Path(f)
    return p, p.with_suffix('.py'), p.with_suffix('.a9s')


def _read(p: Path) -> str:
    if not p.exists():
        _die(f"file not found: {p}")
    return p.read_text()


def _die(message: str, code: int = CLI_EXIT_GENERAL) -> None:
    print(f"aether: error: {message}", file=sys.stderr)
    raise SystemExit(code)


def _ok(message: str) -> None:
    print(f"  {G}✓{X}  {message}")


def _fail(message: str) -> None:
    print(f"  {R}✗{X}  {message}", file=sys.stderr)


def _info(message: str) -> None:
    print(f"      {message}")


def _emit_json(payload: dict[str, Any], *, code: int = CLI_EXIT_OK) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))
    raise SystemExit(code)


def _compile_source(p: Path, source: str, py: Path, a9s: Path):
    code, registry = Aether9Compiler().compile(source)
    sig = SignatureFile.generate(source, registry, p.name)
    py.write_text(code)
    SignatureFile.save(sig, str(a9s))
    return code, sig


def _load_or_compile_bytecode(path: Path) -> Bytecode:
    if not path.exists():
        _die(f"file not found: {path}")
    if path.suffix == '.a9b':
        return Bytecode.load(str(path))
    source = path.read_text()
    bc, _ = compile_to_bytecode(source)
    return bc


def _instruction_payload(code):
    return [
        {"index": i, "op": ins.op.name, "arg": ins.arg}
        for i, ins in enumerate(code)
    ]


def _disasm_payload(path: Path, bc: Bytecode, *, verbose: bool) -> dict[str, Any]:
    binary = False
    if path.exists() and path.suffix == '.a9b':
        try:
            binary = path.read_bytes().startswith(b'A9B9')
        except OSError:
            binary = False
    functions = {}
    summaries = bc.function_summaries()
    for name, code in sorted(bc.functions.items()):
        functions[name] = {
            "summary": summaries.get(name, {}),
            "instructions": _instruction_payload(code),
        }
    return {
        "success": True,
        "command": "disasm",
        "target": str(path),
        "verbose": verbose,
        "artifact_metadata": bc.artifact_contract(binary=binary),
        "main_instructions": _instruction_payload(bc.instructions),
        "functions": functions,
        "disassembly_text": bc.disassemble(verbose=verbose),
    }


def cmd_compile(args: argparse.Namespace) -> None:
    p, py, a9s = _paths(args.file)
    source = _read(p)
    if args.json:
        try:
            _, sig = _compile_source(p, source, py, a9s)
            payload = {
                "success": True,
                "command": "compile",
                "source_path": str(p),
                "python_output": str(py),
                "signature_output": str(a9s),
                "arrays": sorted(sig.get("arrays", {}).keys()),
                "global_mac_prefix": (sig.get("global_mac") or sig.get("global_seal") or "")[:16],
            }
            _emit_json(payload)
        except (LexError, ParseError, CompileError, OSError) as e:
            _emit_json({
                "success": False,
                "command": "compile",
                "source_path": str(p),
                "error_type": type(e).__name__,
                "error_message": str(e),
            }, code=CLI_EXIT_GENERAL)
    print(f"⚙️   compiling  {p.name}")
    try:
        _, sig = _compile_source(p, source, py, a9s)
    except (LexError, ParseError, CompileError) as e:
        _fail(str(e))
        raise SystemExit(CLI_EXIT_GENERAL)
    _ok(f"{py.name}   — compiled python")
    _ok(f"{a9s.name}  — signature file")
    _info(f"arrays      : {list(sig['arrays'].keys())}")
    _info(f"global seal : {sig.get('global_mac', sig.get('global_seal', '—'))[:16] + '...'}")
    if args.verbose:
        for name, info in sig['arrays'].items():
            _info(f"{name:16s}  hmac={info.get('hmac', '—')[:16]}...")


def cmd_export(args: argparse.Namespace) -> None:
    p = Path(args.file)
    out = Path(args.output) if args.output else p.with_suffix('.a9b')
    sig_path = Path(args.signature_output) if args.signature_output else p.with_suffix('.a9s')

    if args.json:
        result = export_file(
            p,
            output_path=out,
            format=args.format,
            write_signature=(not args.no_signature),
            signature_path=sig_path,
            force=args.force,
        )
        payload = result.to_dict()
        payload.update({"command": "export"})
        code = CLI_EXIT_OK if result.success else CLI_EXIT_GENERAL
        _emit_json(payload, code=code)

    source = _read(p)
    if out.exists() and not args.force:
        _die(f"output already exists: {out}  (use --force to overwrite)")
    if sig_path.exists() and not args.no_signature and not args.force:
        _die(f"signature already exists: {sig_path}  (use --force to overwrite)")

    print(f"📦  exporting   {p.name}")
    try:
        bc, registry = compile_to_bytecode(source)
        bc.save(str(out), format=args.format)
    except (LexError, ParseError, CompileError, BytecodeFormatError) as e:
        _fail(str(e))
        raise SystemExit(CLI_EXIT_GENERAL)
    except OSError as e:
        _die(str(e))

    _ok(f"{out.name}  — bytecode {args.format}")
    _info(f"instructions: {len(bc.instructions)}")
    _info(f"functions   : {list(bc.functions.keys())}")
    _info(f"arrays      : {list(registry.keys())}")

    if not args.no_signature:
        try:
            sig = SignatureFile.generate(source, registry, p.name)
            SignatureFile.save(sig, str(sig_path))
        except OSError as e:
            _die(str(e))
        _ok(f"{sig_path.name}  — signature file")
        _info(f"global seal : {sig.get('global_mac', sig.get('global_seal', '—'))[:16] + '...'}")

    if args.verbose:
        print("\n" + bc.disassemble())


def cmd_verify(args: argparse.Namespace) -> None:
    p, _, a9s = _paths(args.file)
    if args.json:
        result = verify_file(p, signature_path=a9s)
        payload = result.to_dict()
        payload.update({"command": "verify"})
        code = CLI_EXIT_OK if result.success else CLI_EXIT_VALIDATION
        _emit_json(payload, code=code)

    source = _read(p)
    if not a9s.exists():
        _die(f"no signature file: {a9s}\n       run 'aether compile {p}' or 'aether export {p}' first.")
    print(f"🔍  verifying  {p.name}")
    sig = SignatureFile.load(str(a9s))
    ok, msg = SignatureFile.verify(sig, source)
    if ok:
        _ok("signature valid")
        _info(f"arrays      : {list(sig['arrays'].keys())}")
        _info(f"global seal : {sig.get('global_mac', sig.get('global_seal', '—'))[:16] + '...'}")
        if args.verbose:
            for name, info in sig['arrays'].items():
                cur, _ = VortexSequencer(info['data']).compute_seal()
                mark = f"{G}✓{X}" if cur == info['raw_sig'] else f"{R}✗{X}"
                _info(f"{name:16s}  {mark}  hmac={info.get('hmac', '—')[:16]}...")
    else:
        _fail(msg)
        raise SystemExit(CLI_EXIT_VALIDATION)


def cmd_run(args: argparse.Namespace) -> None:
    p, py, a9s = _paths(args.file)
    source = _read(p)
    if a9s.exists():
        print(f"🔍  verifying  {p.name}")
        sig = SignatureFile.load(str(a9s))
        ok, msg = SignatureFile.verify(sig, source)
        if not ok:
            _fail(msg)
            print(f"\n       re-compile with 'aether compile {p}' if intentional.", file=sys.stderr)
            raise SystemExit(CLI_EXIT_VALIDATION)
        _ok(f"signature valid  (global_seal={sig.get('global_mac', sig.get('global_seal', '—'))[:16] + '...'})")
        if py.exists() and py.stat().st_mtime >= a9s.stat().st_mtime:
            code = py.read_text()
        else:
            try:
                code, _ = _compile_source(p, source, py, a9s)
            except (LexError, ParseError, CompileError) as e:
                _fail(str(e))
                raise SystemExit(CLI_EXIT_GENERAL)
    else:
        print(f"⚙️   no .a9s — compiling {p.name}")
        try:
            code, sig = _compile_source(p, source, py, a9s)
        except (LexError, ParseError, CompileError) as e:
            _fail(str(e))
            raise SystemExit(CLI_EXIT_GENERAL)
        _ok(f"compiled & signed  (global_seal={sig.get('global_mac', sig.get('global_seal', '—'))[:16] + '...'})")
    print(f"\n🚀  running    {p.name}\n")
    try:
        exec(compile(code, str(py), 'exec'), {'__name__': '__main__'})
    except RuntimeError as e:
        _fail(str(e))
        raise SystemExit(CLI_EXIT_RUNTIME)


def cmd_vm(args: argparse.Namespace) -> None:
    p = Path(args.file)
    if args.json:
        result = run_file(p)
        payload = result.to_dict()
        payload.update({"command": "vm", "verbose": bool(args.verbose)})
        code = CLI_EXIT_OK if result.success else CLI_EXIT_RUNTIME
        _emit_json(payload, code=code)

    print(f"⚡  vm running  {p.name}\n")
    try:
        bc = _load_or_compile_bytecode(p)
        if args.verbose:
            meta = bc.artifact_contract(binary=p.suffix == '.a9b' and p.read_bytes().startswith(b'A9B9')) if p.exists() and p.suffix == '.a9b' else bc.artifact_contract(binary=False)
            _info(f"instructions: {meta.get('instruction_count', 0)}")
            _info(f"functions   : {meta.get('functions', [])}")
            _info(f"arrays      : {meta.get('arrays', [])}")
        AetherVM(workdir=str(p.parent)).run(bc)
    except VMError as e:
        _fail(str(e))
        raise SystemExit(CLI_EXIT_RUNTIME)
    except (LexError, ParseError, CompileError, Exception) as e:
        _fail(str(e))
        raise SystemExit(CLI_EXIT_GENERAL)


def cmd_disasm(args: argparse.Namespace) -> None:
    try:
        bc = _load_or_compile_bytecode(Path(args.file))
        if args.json:
            payload = _disasm_payload(Path(args.file), bc, verbose=bool(args.verbose))
            _emit_json(payload)
        print(bc.disassemble(verbose=args.verbose))
    except (LexError, ParseError, CompileError, Exception) as e:
        if args.json:
            _emit_json({
                "success": False,
                "command": "disasm",
                "target": args.file,
                "error_type": type(e).__name__,
                "error_message": str(e),
            }, code=CLI_EXIT_GENERAL)
        _fail(str(e))
        raise SystemExit(CLI_EXIT_GENERAL)


def _print_opcode_histogram(hist: dict) -> None:
    if not hist:
        return
    print("  opcode histogram")
    for name, count in hist.items():
        print(f"    {name:16s} {count}")


def _print_function_summaries(meta: dict) -> None:
    summaries = meta.get('function_summaries', {}) or {}
    if not summaries:
        return
    print(f"\n  Functions  ({len(summaries)})")
    for name, info in summaries.items():
        print(
            f"    {name}\n"
            f"      params          {info.get('params', [])}\n"
            f"      instruction_count  {info.get('instruction_count', 0)}\n"
            f"      sealed          {info.get('sealed', False)}"
        )


def cmd_inspect(args: argparse.Namespace) -> None:
    p = Path(args.file)
    if args.json:
        result = inspect_path(p)
        payload = result.to_dict()
        payload.update({"command": "inspect"})
        code = CLI_EXIT_OK if result.success else CLI_EXIT_GENERAL
        _emit_json(payload, code=code)

    if not p.exists():
        _die(f"file not found: {p}")
    if p.suffix == '.a9b':
        try:
            meta = Bytecode.inspect_file(str(p))
        except (OSError, BytecodeFormatError, json.JSONDecodeError) as e:
            _die(str(e))
        print(f"\n{'─' * 50}\n  Aether-9 Bytecode  ·  {p.name}\n{'─' * 50}")
        print(f"  contract      {meta.get('contract', 'unknown')}")
        print(f"  version       {meta.get('version', 'unknown')}")
        print(f"  format        {meta.get('format', 'unknown')}")
        print(f"  instructions  {meta.get('instruction_count', 0)}")
        print(f"  functions     {meta.get('functions', [])}")
        print(f"  arrays        {meta.get('arrays', [])}")
        print(f"  byte size     {meta.get('byte_size', 0)}")
        if args.verbose:
            print(f"  sealed funcs  {meta.get('sealed_function_count', 0)}")
            sections = meta.get('sections', [])
            if sections:
                print(f"  sections      {sections}")
            print()
            _print_opcode_histogram(meta.get('opcode_histogram', {}))
            _print_function_summaries(meta)
        print(f"{'─' * 50}\n")
        return

    sig = SignatureFile.load(str(p))
    ts = datetime.datetime.fromtimestamp(sig['created_at']).strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n{'─' * 50}\n  Aether-9 Signature  ·  {p.name}\n{'─' * 50}")
    print(f"  version      {sig['version']}")
    print(f"  source       {sig['source']}")
    print(f"  created      {ts}")
    print(f"  source hash  {sig['source_hash'][:20]}…")
    print(f"  global seal  {sig.get('global_mac', sig.get('global_seal', '—'))[:16] + '...'}")
    print(f"\n  Arrays  ({len(sig['arrays'])})")
    for name, info in sig['arrays'].items():
        print(f"    {name}\n      data     {info['data']}\n      hmac     {info.get('hmac', '—')[:20]}...")
        if args.verbose:
            print(f"      raw_sig  {info.get('raw_sig', '—')}\n      seal     {info.get('seal', '—')}")
    print(f"{'─' * 50}\n")


def cmd_shell(args: argparse.Namespace) -> None:
    run_shell()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aether",
        description="Aether-9 Language CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest='command', required=True)

    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')

    def add_file_command(name: str, handler, help_text: str):
        p = sub.add_parser(name, help=help_text)
        p.add_argument('file')
        p.add_argument('-v', '--verbose', action='store_true')
        p.add_argument('--json', action='store_true', help='emit machine-readable JSON output')
        p.set_defaults(func=handler)
        return p

    add_file_command('compile', cmd_compile, 'compile .a9 to Python and .a9s')
    add_file_command('run', cmd_run, 'compile/verify and run through Python backend')
    add_file_command('verify', cmd_verify, 'verify .a9 against .a9s')
    add_file_command('inspect', cmd_inspect, 'inspect .a9s or .a9b')
    add_file_command('vm', cmd_vm, 'run .a9 source or .a9b bytecode through AetherVM')
    add_file_command('disasm', cmd_disasm, 'disassemble .a9 source or .a9b bytecode')

    exp = sub.add_parser('export', help='export .a9 to .a9b bytecode')
    exp.add_argument('file')
    exp.add_argument('--format', choices=['json', 'binary'], default='json')
    exp.add_argument('-o', '--output')
    exp.add_argument('--signature-output')
    exp.add_argument('--no-signature', action='store_true')
    exp.add_argument('-f', '--force', action='store_true')
    exp.add_argument('-v', '--verbose', action='store_true')
    exp.add_argument('--json', action='store_true', help='emit machine-readable JSON output')
    exp.set_defaults(func=cmd_export)

    sh = sub.add_parser('shell', help='start the Aether shell')
    sh.set_defaults(func=cmd_shell)
    return parser


def main(argv: Optional[list[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
