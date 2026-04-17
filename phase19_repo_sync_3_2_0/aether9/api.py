from __future__ import annotations

from contextlib import redirect_stdout
from dataclasses import asdict, dataclass, field
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Optional

from .compiler import Aether9Compiler, CompileError, LexError, ParseError
from .signature import SignatureFile
from .vm import AetherVM, Bytecode, BytecodeFormatError, VMError, compile_to_bytecode


@dataclass
class APIResult:
    success: bool
    error_type: Optional[str] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExportArtifactResult(APIResult):
    source_name: Optional[str] = None
    artifact_path: Optional[str] = None
    artifact_format: Optional[str] = None
    signature_path: Optional[str] = None
    instruction_count: int = 0
    functions: List[str] = field(default_factory=list)
    arrays: List[str] = field(default_factory=list)
    contract: Optional[str] = None
    artifact_version: Optional[str] = None


@dataclass
class InspectPathResult(APIResult):
    path: Optional[str] = None
    kind: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VerifyFileResult(APIResult):
    source_path: Optional[str] = None
    signature_path: Optional[str] = None
    ok: bool = False
    message: Optional[str] = None
    arrays: List[str] = field(default_factory=list)
    source_hash: Optional[str] = None
    global_mac_prefix: Optional[str] = None


@dataclass
class VMRunResult(APIResult):
    target_path: Optional[str] = None
    target_kind: Optional[str] = None
    stdout: str = ''
    return_value: Any = None
    artifact_metadata: Dict[str, Any] = field(default_factory=dict)


def _ok(result_cls, **kwargs):
    return result_cls(success=True, **kwargs)


def _err(result_cls, exc: Exception, **kwargs):
    return result_cls(
        success=False,
        error_type=type(exc).__name__,
        error_message=str(exc),
        **kwargs,
    )


def _read_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f'file not found: {path}')
    return path.read_text(encoding='utf-8')


def export_file(
    file_path: str | Path,
    *,
    output_path: str | Path | None = None,
    format: str = 'json',
    write_signature: bool = True,
    signature_path: str | Path | None = None,
    force: bool = False,
) -> ExportArtifactResult:
    try:
        src_path = Path(file_path)
        source = _read_text(src_path)
        bc, registry = compile_to_bytecode(source)

        out = Path(output_path) if output_path else src_path.with_suffix('.a9b')
        sig_out = Path(signature_path) if signature_path else src_path.with_suffix('.a9s')

        if out.exists() and not force:
            raise FileExistsError(f'output already exists: {out}')
        if write_signature and sig_out.exists() and not force:
            raise FileExistsError(f'signature already exists: {sig_out}')

        bc.save(str(out), format=format)
        sig_path_str = None
        if write_signature:
            sig = SignatureFile.generate(source, registry, src_path.name)
            SignatureFile.save(sig, str(sig_out))
            sig_path_str = str(sig_out)

        contract = bc.artifact_contract(binary=(format == 'binary'))
        return _ok(
            ExportArtifactResult,
            source_name=src_path.name,
            artifact_path=str(out),
            artifact_format=format,
            signature_path=sig_path_str,
            instruction_count=len(bc.instructions),
            functions=sorted(bc.functions.keys()),
            arrays=sorted(registry.keys()),
            contract=contract.get('contract'),
            artifact_version=contract.get('version'),
        )
    except (FileNotFoundError, FileExistsError, LexError, ParseError, CompileError, BytecodeFormatError, OSError) as exc:
        return _err(ExportArtifactResult, exc)


def inspect_path(path: str | Path) -> InspectPathResult:
    try:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f'file not found: {p}')
        if p.suffix == '.a9b':
            meta = Bytecode.inspect_file(str(p))
            return _ok(InspectPathResult, path=str(p), kind='artifact', metadata=meta)
        if p.suffix == '.a9s':
            sig = SignatureFile.load(str(p))
            meta = {
                'version': sig.get('version'),
                'source': sig.get('source'),
                'created_at': sig.get('created_at'),
                'arrays': sorted(sig.get('arrays', {}).keys()),
                'source_hash': sig.get('source_hash'),
                'global_mac_prefix': (sig.get('global_mac') or '')[:16],
            }
            return _ok(InspectPathResult, path=str(p), kind='signature', metadata=meta)
        raise ValueError(f'unsupported inspect path type: {p.suffix or "<none>"}')
    except (FileNotFoundError, ValueError, BytecodeFormatError, OSError) as exc:
        return _err(InspectPathResult, exc, path=str(path))


def verify_file(file_path: str | Path, *, signature_path: str | Path | None = None) -> VerifyFileResult:
    try:
        src = Path(file_path)
        sig_path = Path(signature_path) if signature_path else src.with_suffix('.a9s')
        source = _read_text(src)
        sig = SignatureFile.load(str(sig_path))
        ok, msg = SignatureFile.verify(sig, source)
        return VerifyFileResult(
            success=ok,
            ok=ok,
            message=msg,
            source_path=str(src),
            signature_path=str(sig_path),
            arrays=sorted(sig.get('arrays', {}).keys()),
            source_hash=sig.get('source_hash'),
            global_mac_prefix=(sig.get('global_mac') or '')[:16],
            error_type=None if ok else 'SignatureVerificationError',
            error_message=None if ok else msg,
        )
    except (FileNotFoundError, OSError) as exc:
        return _err(VerifyFileResult, exc, source_path=str(file_path), signature_path=str(signature_path) if signature_path else None, ok=False, message=str(exc))


def run_file(
    path: str | Path,
    *,
    workdir: str | Path | None = None,
    capture_stdout: bool = True,
) -> VMRunResult:
    target = Path(path)
    out = StringIO()
    try:
        if not target.exists():
            raise FileNotFoundError(f'file not found: {target}')
        if target.suffix == '.a9b':
            bc = Bytecode.load(str(target))
            target_kind = 'artifact'
        elif target.suffix == '.a9':
            source = _read_text(target)
            bc, _ = compile_to_bytecode(source)
            target_kind = 'source'
        else:
            raise ValueError(f'unsupported run target type: {target.suffix or "<none>"}')

        vm = AetherVM(workdir=str(workdir or target.parent))
        if target.suffix == '.a9b':
            try:
                contract = Bytecode.inspect_file(str(target))
            except (OSError, BytecodeFormatError):
                contract = bc.artifact_contract(binary=False)
        else:
            contract = bc.artifact_contract(binary=False)
        if capture_stdout:
            with redirect_stdout(out):
                result = vm.run(bc)
        else:
            result = vm.run(bc)
        return _ok(
            VMRunResult,
            target_path=str(target),
            target_kind=target_kind,
            stdout=out.getvalue(),
            return_value=result,
            artifact_metadata=contract,
        )
    except (FileNotFoundError, ValueError, LexError, ParseError, CompileError, BytecodeFormatError, VMError, OSError) as exc:
        return _err(VMRunResult, exc, target_path=str(target), target_kind='artifact' if str(target).endswith('.a9b') else 'source', stdout=out.getvalue())


def export_and_inspect(
    file_path: str | Path,
    *,
    output_path: str | Path | None = None,
    format: str = 'json',
    write_signature: bool = True,
    signature_path: str | Path | None = None,
    force: bool = False,
) -> Dict[str, Any]:
    exported = export_file(
        file_path,
        output_path=output_path,
        format=format,
        write_signature=write_signature,
        signature_path=signature_path,
        force=force,
    )
    payload = {'export': exported.to_dict()}
    if exported.success and exported.artifact_path:
        payload['inspect'] = inspect_path(exported.artifact_path).to_dict()
    return payload


__all__ = [
    'APIResult',
    'ExportArtifactResult',
    'InspectPathResult',
    'VerifyFileResult',
    'VMRunResult',
    'export_file',
    'inspect_path',
    'verify_file',
    'run_file',
    'export_and_inspect',
]
