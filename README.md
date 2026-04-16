# Aether-9

**A VM-based programming language and execution framework for verifiable, tamper-aware, policy-controlled execution.**

Aether-9 combines a compact source language, a bytecode compiler, portable `.a9b` artifacts, verification sidecars, a stack-based virtual machine, sandbox-aware execution, and developer tooling for export, inspection, disassembly, and runtime execution.

This repository is synchronized to the **3.1.1 stabilization release**.

---

## Why Aether-9

Most language toolchains stop at parsing, compilation, and runtime execution.
Aether-9 adds a different priority stack:

- explicit execution artifacts
- verification-aware workflow
- stack-based dedicated VM execution
- policy-aware runtime controls
- public-safe diagnostics and reviewability

This makes Aether-9 especially relevant for:

- security-sensitive automation
- verifiable execution pipelines
- AI and agent-adjacent runtime control
- audit-friendly internal tooling
- research into execution integrity and controlled runtimes

---

## What is included in 3.1.1

### Runtime stabilization
- richer VM diagnostics
- structured runtime error categories
- frame, opcode, stack-tail, and trace context
- more usable verbose inspection and disassembly output

### Examples pack
- learning examples
- artifact/runtime examples
- positioning examples
- policy example for controlled file write/read flow

### Developer docs pack
- getting started guide
- language reference
- CLI reference
- artifact format guide
- VM architecture notes
- security model notes
- examples guide
- runtime diagnostics notes

### Validation package
- benchmark methodology
- benchmark summary
- scenario matrix
- integration review notes
- reproducible validation runner and result files

---

## Installation

From a local release wheel:

```bash
pip install ./aether9-3.1.1-py3-none-any.whl
```

From PyPI after publication of the 3.1.1 release:

```bash
pip install aether9==3.1.1
```

Check the installed version:

```bash
aether --version
```

---

## Quick start

Create a file named `program.a9`:

```aether
data = [54, 36, 72]

lattice verify(x) uses data:
    return dr(x) or 9

result = verify(54)
print(result)
```

Export a binary artifact:

```bash
aether export program.a9 --format binary
```

Inspect it:

```bash
aether inspect program.a9b -v
```

Disassemble it:

```bash
aether disasm program.a9b -v
```

Run it through the Aether VM:

```bash
aether vm program.a9b -v
```

---

## Core workflow

```text
source.a9
    -> Lexer / Parser / AST
    -> Bytecode compiler
    -> .a9b artifact
    -> inspect / disasm / verify
    -> Aether VM
```

Aether-9 is therefore more than a syntax layer. It is a language-plus-runtime system built around explicit execution artifacts and controlled runtime behavior.

---

## Repository map

### Main code
- `aether9/` — source package
- `aether9/compiler.py` — lexer, parser, AST, compiler path
- `aether9/vm.py` — bytecode container and VM runtime
- `aether9/sandbox.py` — sandbox and execution policy behavior
- `aether9/cli.py` — command-line entry points

### Documentation
- `docs/README.md`
- `docs/getting-started.md`
- `docs/language-reference.md`
- `docs/cli-reference.md`
- `docs/artifact-format.md`
- `docs/vm-architecture.md`
- `docs/security-model.md`
- `docs/examples.md`
- `docs/runtime-diagnostics.md`

### Examples
- `examples/README.md`
- `examples/hello.a9`
- `examples/control_flow.a9`
- `examples/stdlib_demo.a9`
- `examples/export_binary_demo.a9`
- `examples/inspect_demo.a9`
- `examples/vm_execution_demo.a9`
- `examples/ai_verification.a9`
- `examples/tamper_detection_demo.a9`
- `examples/write_read_demo.a9`

### Validation
- `validation/README.md`
- `validation/benchmark-methodology.md`
- `validation/benchmark-summary.md`
- `validation/scenario-matrix.md`
- `validation/integration-review.md`
- `validation/validation-checklist.md`
- `validation/tools/run_validation.py`
- `validation/results/`

### Release tracking
- `CHANGELOG.md`
- `RELEASE_NOTES_3_1_1.md`

---

## Selected validation snapshot

Current 3.1.1 validation artifacts include the following public snapshot:

- `compile_to_bytecode` average: **0.788 ms**
- `inspect_binary_artifact` average: **0.6522 ms**
- `load_binary_artifact` average: **0.7067 ms**
- `vm_run_from_binary` average: **1.0217 ms**
- `inspect_demo.a9` JSON artifact size: **3086 bytes**
- `inspect_demo.a9` binary artifact size: **1639 bytes**

The repository also contains validation scenarios covering export, inspect, VM execution, tamper detection, verbose diagnostics, and sandbox blocking.

---

## CLI surface

Primary public commands:

```bash
aether --version
aether export <file.a9> --format binary
aether export <file.a9> --format json
aether inspect <file.a9b> -v
aether disasm <file.a9b> -v
aether vm <file.a9b> -v
```

---

## Security note

This repository documents the **public** Aether-9 model only.
It intentionally does **not** publish:

- private signing keys
- undisclosed internal secrets
- sensitive implementation material that should not be exposed publicly

The goal is to make the system understandable and reviewable without disclosing material that would weaken its security posture.

---

## 3.1.1 repo sync priorities

This repository state is intended to reflect a project that is now built around three parallel themes:

- **Core technology** — stable runtime, artifacts, VM, CLI, sandbox
- **Validation package** — measurable scenarios, benchmark notes, result files
- **Integration-ready platform** — examples, docs, inspection workflow, release notes

The next logical step after this sync is planning the **3.2.0** cycle on top of a clean public repository state.

---

## License

See `LICENSE` in the repository root.

---

**Built by Ahmed Harb Akeely**
