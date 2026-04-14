<div align="center">

# Aether-9

**A VM-based programming language with built-in execution integrity workflows.**

*Compile. Export. Inspect. Verify. Execute.*

[![PyPI version](https://badge.fury.io/py/aether9.svg)](https://pypi.org/project/aether9/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-117%20passing-brightgreen.svg)](tests/)
[![License](https://img.shields.io/badge/license-see%20LICENSE-green.svg)](LICENSE)

</div>

---

## Overview

Aether-9 is a compact programming language and runtime designed around a simple idea:

> Source code, data, and executable artifacts should remain verifiable from creation to execution.

Aether-9 programs can be parsed, compiled, exported into `.a9b` artifacts, inspected, disassembled, and executed through the Aether VM.

Version **3.1.0** introduces the first public binary artifact workflow for Aether-9.

---

## What's New in v3.1.0

Aether-9 v3.1.0 moves the project from an experimental compiler/runtime prototype toward a usable VM-based execution workflow.

### Highlights

- Binary `.a9b` artifact support
- Stable JSON artifact support for debugging and development
- `aether export` command
- `aether inspect` command
- `aether disasm` command
- `aether vm` execution path
- Self-contained bytecode artifacts
- Runtime artifact loading improvements
- Improved sandbox stability
- Safer bytecode loader behavior
- Better support for sealed lattice execution
- Artifact contract foundation for future releases

Sensitive internal signing details and private implementation decisions are intentionally not documented publicly.

---

## Installation

Install the latest released version from PyPI:

```bash
pip install aether9==3.1.0
```

Verify the installation:

```bash
aether --version
```

---

## Quick Start

Create a file named `program.a9`:

```aether
data = [54, 36, 72]

lattice verify(x) uses data:
    return dr(x) or 9

result = verify(54)
print(result)
```

Export it to a binary artifact:

```bash
aether export program.a9 --format binary
```

Run the artifact with the Aether VM:

```bash
aether vm program.a9b
```

Inspect the artifact:

```bash
aether inspect program.a9b
```

Disassemble it:

```bash
aether disasm program.a9b
```

---

## CLI

### Export

Export an Aether source file into an executable artifact:

```bash
aether export program.a9 --format binary
```

Export as JSON for debugging:

```bash
aether export program.a9 --format json
```

Write to a custom output path:

```bash
aether export program.a9 --format binary --output build/program.a9b
```

Overwrite an existing artifact:

```bash
aether export program.a9 --format binary --force
```

Export without writing a signature sidecar:

```bash
aether export program.a9 --format binary --no-signature
```

### Run

Run a bytecode artifact:

```bash
aether vm program.a9b
```

### Inspect

Show artifact metadata:

```bash
aether inspect program.a9b
```

### Disassemble

Show VM instructions:

```bash
aether disasm program.a9b
```

---

## Artifact Formats

Aether-9 v3.1.0 supports two artifact formats.

### Binary `.a9b`

The binary artifact format is intended for compact runtime execution.

```bash
aether export program.a9 --format binary
```

Binary artifacts include:

- format identifier
- version metadata
- instruction section
- function section
- registry section
- integrity checksum metadata

### JSON `.a9b`

The JSON artifact format is intended for debugging, tests, and developer inspection.

```bash
aether export program.a9 --format json
```

JSON artifacts are human-readable and useful while developing new language/runtime features.

---

## Execution Model

Traditional execution usually follows this shape:

```text
Source Code → Runtime → Output
```

Aether-9 uses an artifact-oriented workflow:

```text
Source Code
    ↓
Lexer / Parser / AST
    ↓
Bytecode Compiler
    ↓
.a9b Artifact
    ↓
Aether VM
    ↓
Output
```

The runtime executes bytecode instructions through the Aether VM instead of executing generated Python source with `exec()`.

---

## Language Reference

### Arrays

Arrays are first-class data declarations used by lattice functions.

```aether
data = [54, 36, 72, 90, 18, 45]
```

### Lattice Functions

A lattice may be bound to an array:

```aether
data = [54, 36, 72]

lattice compute(x) uses data:
    return (x + 9) % 9 or 9
```

A lattice may also be pure:

```aether
lattice normalize(x) pure:
    return dr(x) or 9
```

### Assignments

```aether
x = 9
label = "aether"
result = x + 9
```

### Control Flow

```aether
if result == 9:
    print(result)
else:
    print(0)
```

```aether
for item in data:
    print(item)
```

```aether
counter = 0
while counter < 9:
    counter = counter + 1
```

### Nested Calls

```aether
data = [54, 36, 72]

lattice step1(x) uses data:
    return (x + 9) % 9 or 9

lattice step2(x) uses data:
    return step1(x) % 9 or 9

result = step2(54)
```

### I/O

```aether
print(result)
write("output.txt", result)
loaded = read("output.txt")
```

---

## Standard Library

| Function | Description |
|---|---|
| `dr(x)` | Digital-root operation |
| `abs(x)` | Absolute value |
| `min(a, b)` | Minimum |
| `max(a, b)` | Maximum |
| `mod(a, b)` | Modulo with Aether-9 normalization |
| `len(x)` | Length of string representation |
| `str(x)` | Convert value to string |
| `concat(a, b)` | Concatenate two values as strings |
| `print(x)` | Print value |
| `write(path, value)` | Write value to a file |
| `read(path)` | Read value from a file |

---

## Aether VM

Aether-9 v3.1.0 includes a stack-based VM.

The VM supports:

- constants
- variable load/store
- arithmetic operations
- comparison operations
- conditional jumps
- loops
- lattice calls
- builtin calls
- basic I/O instructions
- return handling
- halt handling

Example disassembly:

```text
=== main ===
     0  LOAD_CONST         [54, 36, 72]
     1  STORE_NAME         'data'
     2  MAKE_FUNC          'verify'
     3  LOAD_CONST         54
     4  CALL_FUNC          ('verify', 1)
     5  STORE_NAME         'result'
     6  LOAD_NAME          'result'
     7  PRINT              1
     8  POP
     9  HALT

=== verify [sealed] ===
     0  STORE_NAME         'x'
     1  LOAD_NAME          'x'
     2  CALL_BUILTIN       ('dr', 1)
     3  RETURN
```

---

## Sandbox and Runtime Policy

Aether-9 includes sandbox and policy mechanisms intended to reduce unsafe execution behavior.

Current public-facing policy features include:

- timeout control
- write allow-listing
- blocked dynamic execution patterns
- restricted execution surface
- isolated subprocess execution path for sandboxed workflows

Example policy file:

```json
{
  "allow_write": ["report.txt", "output.txt"],
  "max_runtime": 30,
  "max_memory_mb": 128,
  "allow_network": false
}
```

By default, write access is restricted.

---

## Integrity and Verification

Aether-9 artifacts are designed around verifiable execution.

Public verification concepts include:

- source-to-artifact consistency
- array binding metadata
- artifact-level validation
- checksum-backed loading
- sealed lattice execution checks

Private keys, sensitive signing internals, and implementation-specific security details are not documented in this README.

---

## Architecture

```text
source.a9
    │
    ├─ Lexer
    │
    ├─ Parser
    │
    ├─ AST
    │
    ├─ Semantic checks
    │
    ├─ Bytecode compiler
    │
    ├─ Artifact writer
    │      ├─ JSON .a9b
    │      └─ Binary .a9b
    │
    └─ Aether VM
           ├─ loader
           ├─ verifier
           ├─ stack frames
           ├─ lattice calls
           ├─ builtin calls
           └─ runtime policy
```

---

## Use Cases

### AI Pipeline Verification

Bind important AI pipeline values to verifiable artifacts before execution.

### Secure Automation

Export deterministic automation steps into bytecode artifacts that can be inspected before execution.

### Audit-Friendly Workflows

Keep source, artifact, and signature metadata together for reviewable execution workflows.

### Research Runtime

Experiment with VM-based language design, bytecode inspection, and execution integrity models.

---

## Examples

Suggested example files:

```text
examples/
├─ hello.a9
├─ lattice_demo.a9
├─ artifact_export.a9
├─ inspect_demo.a9
└─ pipeline_verify.a9
```

Minimal example:

```aether
data = [9, 18, 27]

lattice total(x) uses data:
    acc = 0
    for item in data:
        acc = acc + item
    return acc % 9 or 9

result = total(9)
print(result)
```

Export and run:

```bash
aether export examples/hello.a9 --format binary
aether vm examples/hello.a9b
```

---

## Testing

Install development dependencies:

```bash
pip install aether9[dev]
```

Run tests:

```bash
pytest tests/
```

Current release validation:

```text
117 tests passing
```

Test coverage includes:

- lexer
- parser
- compiler
- signature system
- sandbox behavior
- bytecode VM
- CLI export
- JSON artifact loading
- binary artifact loading
- runtime error behavior

---

## Version Notes

### v3.1.0

- Added binary `.a9b` artifact support
- Added stable JSON artifact export path
- Added official CLI export workflow
- Added artifact inspection workflow
- Added artifact disassembly workflow
- Improved VM artifact loading
- Improved sandbox stability
- Fixed bytecode loader behavior for array values
- Added artifact contract foundation

---

## Roadmap

Planned future work may include:

- stronger runtime diagnostics
- expanded artifact metadata
- additional verifier tooling
- improved developer ergonomics
- richer integration tests
- future language features after runtime stabilization

Language expansion is intentionally secondary to runtime stability.

---

## Security Notes

Aether-9 is experimental software.

It includes integrity-oriented runtime features, but it should not be treated as a complete security boundary for hostile code without independent review.

Do not publish private signing keys, internal secrets, or deployment-specific policy details in public repositories.

---

## License

See [`LICENSE`](LICENSE).

Commercial usage, redistribution, or production deployment may require prior written permission depending on the license terms used by the repository owner.

---

<div align="center">

**Built by Ahmed Harb Akeely**

</div>
