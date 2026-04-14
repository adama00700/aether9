<div align="center">

# Aether-9

**The first programming language with a built-in execution integrity layer.**

*Compile. Seal. Verify. Execute — in a sandboxed VM.*

[![PyPI version](https://badge.fury.io/py/aether9.svg)](https://pypi.org/project/aether9/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-103%20passing-brightgreen.svg)](tests/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

---

## The Problem

Every system that processes data — AI pipelines, financial engines, automation workflows — faces the same silent risk: **nobody knows if the data was modified between creation and execution.**

By the time you detect tampering, the damage is done.

---

## The Solution

Aether-9 makes tamper detection a compiler-level guarantee.

```
data = [54, 36, 72, 90, 18, 45]

lattice verify(x) uses data:
    root = dr(x)
    if root == 9:
        return 9
    else:
        return 0

total = 0
for score in data:
    r = verify(score)
    total = total + r

write("report.txt", total)
```

```bash
$ aether compile program.a9
  ✓  program.py   — compiled
  ✓  program.a9s  — integrity sealed (HMAC-SHA256)

$ aether run program.a9
  ✓  source hash verified
  ✓  data HMAC verified
  ✓  executing...
```

Change one value in `data` — execution stops before it starts:

```bash
$ aether run program.a9
  ✗  Source code was modified (hash mismatch)
```

---

## Install

```bash
pip install aether9
```

---

## Execution Model

**Traditional:**
```
Code → Executes → Detect issues later
```

**Aether-9:**
```
Code → HMAC verified → AST scanned → Sandboxed VM → Executes
```

Execution is explicitly validated before it is allowed to happen.

---

## How It Works

**1. Compile** — Lexer → Parser → AST → Bytecode + `.a9s` signature

**2. Sign** — every array gets an HMAC-SHA256 bound to its name, values, and order. A SHA-256 of your source code is also stored.

**3. Verify** — on every `aether run`, all HMACs and the source hash are re-checked before any instruction executes.

**4. Execute** — in a sandboxed subprocess with AST Guard (no `import`, `eval`, `exec`) and a stack-based VM (`aether vm`) that runs without `exec()`.

```json
{
  "version":     "2.0",
  "source_hash": "eb0a3565...",
  "arrays": {
    "data": { "hmac": "86666352...", "vortex_sig": 1686592731 }
  },
  "global_mac": "a3e1113b..."
}
```

---

## CLI

```bash
aether compile <file.a9>    # compile → .py + .a9s
aether run     <file.a9>    # verify → sandboxed execute
aether vm      <file.a9>    # verify → VM execute (no exec())
aether verify  <file.a9>    # check integrity only
aether inspect <file.a9s>   # show seal report
aether disasm  <file.a9>    # show bytecode instructions
aether shell                # interactive REPL
```

---

## Language Reference

### Arrays — auto-signed at compile time

```
data = [54, 36, 72, 90, 18, 45]
```

### Lattice functions

```
# bound to data — HMAC verified on every call
lattice compute(a, b) uses data:
    return (a + b) % 9 or 9

# no binding
lattice add(a, b) pure:
    return a + b
```

### Control flow

```
if result == 9:
    print(result)
else:
    print(0)

for item in data:
    result = process(item)

while counter < 9 and total < 81:
    total = total + 9
    counter = counter + 1
```

### Nested calls

```
lattice normalize(x) uses data:
    return (x * 9) % 9 or 9

lattice pipeline(a, b) uses data:
    step = normalize(a + b)
    return step % 9 or 9
```

### I/O

```
print(result)
write("output.txt", result)
loaded = read("output.txt")
```

### Standard library

| Function | Description |
|----------|-------------|
| `dr(x)` | Digital root — Aether-9's core operation |
| `abs(x)` | Absolute value |
| `min(a, b)` | Minimum |
| `max(a, b)` | Maximum |
| `mod(a, b)` | Modulo |
| `len(x)` | String length |
| `str(x)` | Number to string |
| `concat(a, b)` | String concatenation |

---

## Execution Policy

Control what a program is allowed to do with `.a9policy`:

```json
{
  "allow_write":   ["report.txt", "output.txt"],
  "max_runtime":   30,
  "max_memory_mb": 128,
  "allow_network": false
}
```

By default — no writes, 30s timeout, 128MB memory.

---

## VM — Bytecode Interpreter

```bash
aether vm     program.a9    # execute in stack-based VM
aether disasm program.a9    # show bytecode
```

```
=== main ===
   0  LOAD_CONST         [54, 36, 72]
   1  STORE_NAME         'data'
   2  MAKE_FUNC          'verify'
   3  FOR_START          'score'
   4  FOR_NEXT           12
   5  CALL_FUNC          ('verify', 1)
   ...
  12  HALT

=== verify [sealed] ===
   0  STORE_NAME         'x'
   1  LOAD_NAME          'x'
   2  CALL_BUILTIN       ('dr', 1)
   3  COMPARE            '=='
   4  JUMP_IF_FALSE      8
   5  LOAD_CONST         9
   6  RETURN
```

---

## Use Cases

**AI Output Verification** — bind AI-generated scores to their HMAC at creation time. Any post-processing or hallucination into different values is detected before the scores enter your decision system.

**Secure Automation Pipelines** — ensure data flowing through a pipeline matches its original signature at every stage.

**Financial Audit Trails** — the `.a9s` file is a tamper-evident log provably linked to both source code and input data.

---

## Architecture

```
source.a9
    │
    ├─ Lexer → Tokens
    ├─ Parser → AST
    ├─ SemanticAnalyzer (forward refs, bindings)
    ├─ BytecodeCompiler → Instructions
    │
    ├─ program.py    (Python codegen path)
    ├─ program.a9b   (bytecode path)
    └─ program.a9s   (HMAC-SHA256 signatures)
             │
    ┌────────┴────────┐
    │   Execution     │
    │                 │
    │  AST Guard      │  ← blocks import/eval/exec
    │  Subprocess     │  ← isolated process
    │  AetherVM       │  ← stack-based, no exec()
    │  Policy Layer   │  ← write whitelist, timeout
    └─────────────────┘
```

---

## Examples

See [`examples/`](examples/):
- `hello.a9` — minimal program
- `energy_fusion.a9` — multi-lattice pipeline
- `ai_verify.a9` — AI output integrity verification
- `stdlib_demo.a9` — standard library showcase

---

## Testing

```bash
pip install aether9[dev]
pytest tests/
```

103 tests — Lexer, Parser, Compiler, Signature, Sandbox, VM.

---

## License

MIT — see [LICENSE](LICENSE)

---

*Built by Ahmed Harb Akeely*
