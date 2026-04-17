# Aether-9

**A VM-based programming language and execution framework for verifiable, tamper-aware, integration-ready workflows.**

Aether-9 turns source programs into inspectable bytecode artifacts that can be exported, verified, disassembled, and executed through the Aether VM.

Current release: **v3.2.0**

```bash
pip install aether9==3.2.0
```

---

## What is Aether-9?

Aether-9 is a compact language + artifact pipeline + VM runtime designed around execution integrity.

Public workflow:

```text
source.a9
  -> lexer / parser / AST
  -> bytecode compiler
  -> .a9b artifact
  -> inspect / verify / disasm
  -> Aether VM execution
```

Aether-9 is useful where execution needs to be inspectable, packaged into artifacts, validated through structured metadata, callable from automation, and executed through a dedicated VM path.

---

## What's new in v3.2.0

Aether-9 v3.2.0 is an **integration-ready platform release**.

Highlights:

- Python Integration API via `aether9.api`
- machine-readable CLI output through `--json`
- artifact contract v2: `aether9.artifact.v2`
- binary and JSON artifact support
- improved artifact metadata reporting
- runtime diagnostics with structured error context
- integrator docs and examples
- validation v2 package and evidence outputs
- RC2 fix included for JSON artifact metadata reporting in VM JSON output

---

## Install

```bash
pip install aether9==3.2.0
```

Check the installed version:

```bash
python -m aether9.cli --version
python -c "import aether9; print(aether9.__version__)"
```

Expected:

```text
aether 3.2.0
3.2.0
```

---

## Quick start

Create `hello.a9`:

```aether
data = [54, 36, 72]

lattice verify(x) uses data:
    return dr(x) or 9

result = verify(54)
print(result)
```

Export a binary artifact:

```bash
python -m aether9.cli export hello.a9 --format binary --json
```

Inspect it:

```bash
python -m aether9.cli inspect hello.a9b --json
```

Disassemble it:

```bash
python -m aether9.cli disasm hello.a9b --json
```

Run it through the VM:

```bash
python -m aether9.cli vm hello.a9b --json
```

Expected VM output includes:

```json
{
  "success": true,
  "stdout": "9\n"
}
```

---

## Python Integration API

```python
from aether9.api import export_file, inspect_path, verify_file, run_file

exp = export_file("hello.a9", format="binary", force=True)
ins = inspect_path("hello.a9b")
ver = verify_file("hello.a9")
run = run_file("hello.a9b")

print(exp.to_dict())
print(ins.to_dict())
print(ver.to_dict())
print(run.to_dict())
```

The API returns structured result objects with `.to_dict()` for automation, CI, and service workflows.

---

## CLI commands

```bash
python -m aether9.cli export hello.a9 --format binary --json
python -m aether9.cli inspect hello.a9b --json
python -m aether9.cli disasm hello.a9b --json
python -m aether9.cli verify hello.a9 --json
python -m aether9.cli vm hello.a9b --json
```

`--json` makes outputs machine-readable and suitable for integration pipelines.

---

## Artifact contract v2

Aether-9 v3.2.0 uses:

```text
aether9.artifact.v2
```

Artifact metadata includes contract, schema version, artifact kind, container type, version, format, counts, names, sections, integrity metadata, opcode histogram, and function summaries.

Supported containers:

- binary `.a9b`
- JSON `.a9b`

Binary artifacts use the public magic marker:

```text
A9B9
```

---

## Runtime diagnostics

The VM reports structured runtime failures with context such as error type, frame, instruction pointer, opcode, argument, call stack, and recent trace.

---

## Documentation

See:

- [`docs/getting-started.md`](docs/getting-started.md)
- [`docs/cli-reference.md`](docs/cli-reference.md)
- [`docs/integration-api.md`](docs/integration-api.md)
- [`docs/artifact-format.md`](docs/artifact-format.md)
- [`docs/vm-architecture.md`](docs/vm-architecture.md)
- [`docs/runtime-diagnostics.md`](docs/runtime-diagnostics.md)
- [`docs/integrator-overview.md`](docs/integrator-overview.md)
- [`docs/embedding-cookbook.md`](docs/embedding-cookbook.md)
- [`docs/automation-patterns.md`](docs/automation-patterns.md)
- [`docs/security-model.md`](docs/security-model.md)

---

## Examples

See [`examples/`](examples/).

Examples cover basic language usage, control flow, standard library usage, binary export, artifact inspection, VM execution, Python API integration, embedded runner usage, and CI-style validation usage.

---

## Validation

See [`validation/`](validation/).

v3.2.0 includes validation v2 materials covering Python API flows, machine-readable CLI flows, artifact contract v2, binary and JSON artifact paths, and failure diagnostics scenarios.

---

## Public security note

Aether-9 includes public integrity, artifact, verification, and sandbox-oriented workflows.

Sensitive signing secrets, private keys, and undisclosed implementation details are intentionally not included in the public repository.

Aether-9 is experimental software and should be independently reviewed before use in high-risk production environments.

---

## Release notes

- [`RELEASE_NOTES_3_2_0.md`](RELEASE_NOTES_3_2_0.md)
- [`FINAL_READINESS_REPORT_3_2_0.md`](FINAL_READINESS_REPORT_3_2_0.md)
- [`CHANGELOG.md`](CHANGELOG.md)
