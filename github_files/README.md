<div align="center">

# Aether-9

**A deterministic, resonance-constrained programming language with built-in data integrity verification.**

[![PyPI version](https://badge.fury.io/py/aether9.svg)](https://pypi.org/project/aether9/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

---

## What is Aether-9?

Aether-9 is a scripting language that guarantees **data integrity at the compiler level**.

Every array you define gets a cryptographic spatial signature (VortexSeal). Every function bound to that array verifies the seal before executing. If the data was tampered with — even one byte — the program refuses to run.

```
# program.a9
data = [54, 36, 72, 90, 18, 45]

lattice process(x) uses data:
    return (x * 9) % 9 or 9

result = process(54)
print(result)
write("output.txt", result)
```

```bash
aether compile program.a9   # generates program.py + program.a9s
aether run     program.a9   # verify integrity → execute
aether verify  program.a9   # check signature without running
aether inspect program.a9s  # human-readable integrity report
```

---

## Install

```bash
pip install aether9
```

---

## Language Reference

### Arrays — the foundation

```
data = [54, 36, 72, 90, 18, 45]
```

Every array is automatically signed with a **VortexSeal** — a non-commutative spatial hash. The seal is stored in the `.a9s` signature file alongside a SHA-256 of your source code.

### Lattice functions

```
lattice compute(a, b) uses data:
    return (a + b) % 9 or 9
```

`uses data` binds the function to `data`'s VortexSeal. The seal is verified on every call. If `data` was modified after compilation, the function raises a `RuntimeError`.

```
lattice pure_fn(a, b) pure:
    return (a + b) % 9 or 9
```

`pure` functions have no array binding — no integrity check.

### Control flow

```
# if / else
if result == 9:
    print(result)
else:
    print(0)

# for loop
for item in data:
    result = process(item)

# while loop
counter = 0
while counter < 9 and total < 81:
    total = total + 9
    counter = counter + 1
```

### Nested calls

```
lattice normalize(x) uses data:
    return (x * 9) % 9 or 9

lattice pipeline(a, b) uses data:
    step1 = normalize(a + b)
    return step1 % 9 or 9
```

### I/O

```
print(result)                     # print to stdout
write("output.txt", result)       # write to file
loaded = read("output.txt")       # read from file
name = input("Enter value: ")     # read from stdin
```

### Standard library

| Function | Description |
|----------|-------------|
| `dr(x)` | Digital root — Aether-9's core operation |
| `abs(x)` | Absolute value |
| `min(a, b)` | Minimum of two values |
| `max(a, b)` | Maximum of two values |
| `mod(a, b)` | Modulo — same as `a % b` |
| `len(x)` | Length of string |
| `str(x)` | Convert number to string |
| `concat(a, b)` | Concatenate two strings |

---

## The .a9s Signature File

When you compile a `.a9` program, Aether-9 generates a `.a9s` file:

```json
{
  "version": "1.0",
  "source_hash": "36de8c45...",
  "arrays": {
    "data": {
      "raw_sig": 1686592731,
      "seal": 3
    }
  },
  "global_seal": 6
}
```

This file contains:
- SHA-256 hash of your source code
- VortexSeal for every array
- Global seal (integrity of the whole program)

If **anyone** modifies your source or data, `aether run` catches it immediately.

---

## CLI Commands

```bash
aether compile <file.a9>    # compile → .py + .a9s
aether run     <file.a9>    # verify signature → execute
aether verify  <file.a9>    # check .a9s without running
aether inspect <file.a9s>   # show integrity report
```

---

## Use Cases

**AI output verification** — wrap AI-generated results in Aether-9 lattices to guarantee they haven't been post-processed or tampered with.

**Financial audit trails** — compute sensitive values in `.a9` programs; the `.a9s` file serves as a tamper-evident log.

**Sovereign data pipelines** — ensure data flowing through a pipeline matches its original signature at every stage.

---

## How It Works

```
source.a9
    │
    ▼
 Lexer  →  tokens
    │
    ▼
 Parser →  AST
    │
    ▼
 SemanticAnalyzer  (forward ref check, binding validation)
    │
    ▼
 CodeGenerator  →  standalone Python + embedded runtime
    │
    ├──→  program.py   (executable, no dependencies)
    └──→  program.a9s  (SHA-256 + VortexSeal per array)
```

The generated `.py` file is completely standalone — it contains the entire Aether-9 runtime inline. No import of `aether9` at execution time.

---

## Examples

See the [`examples/`](examples/) directory:

- `hello.a9` — minimal program
- `energy_fusion.a9` — multi-lattice pipeline
- `ai_verify.a9` — verifying AI output integrity

---

## License

MIT — see [LICENSE](LICENSE)

---

## Author

Ahmed Harb Akeely — Independent Language Designer
