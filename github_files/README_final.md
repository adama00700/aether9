<div align="center">

# Aether-9

**The first programming language that refuses to run tampered code.**

*A secure execution layer that blocks unsafe or untrusted operations before they run.*

[![PyPI version](https://badge.fury.io/py/aether9.svg)](https://pypi.org/project/aether9/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

---

## The Problem

Modern systems execute code and trust data blindly. A pipeline processes numbers. An AI agent acts on instructions. A financial system computes values. **Nobody knows if the input was modified between creation and execution.**

By the time you detect the tampering, the damage is done.

---

## The Solution

Aether-9 binds every function to its data at compile time. This means execution is no longer implicit — it is explicitly validated before it is allowed to happen.

If the data changes — even one byte — the program **refuses to execute**. Not after. **Before.**

```
data = [54, 36, 72, 90, 18, 45]

lattice process(x) uses data:
    return (x * 9) % 9 or 9

result = process(54)
write("output.txt", result)
```

```bash
$ aether compile program.a9
  ✓  program.py   — compiled
  ✓  program.a9s  — integrity seal

$ aether run program.a9
  ✓  signature valid
  ✓  data integrity confirmed
  →  executing...
```

Modify one number in your data and try again:

```bash
$ aether run program.a9
  ✗  Source code was modified (hash mismatch)
     re-compile if the change is intentional.
```

---

## Execution Model

Traditional systems:
```
Code → Executes → Detect issues later
```

Aether-9:
```
Code → Verified → Allowed or Blocked → Executes
```

This is not a security wrapper. It is a different execution paradigm — one where untrusted operations cannot run by design.

---

## Install

```bash
pip install aether9
```

---

## Use Cases

### AI Agents Control
Prevents AI agents from executing unsafe or manipulated actions in real-world environments. Every action is bound to its validated data context — if the context was altered, execution stops.

### Secure Automation Pipelines
Ensure that data flowing through an automated pipeline matches its original signature at every stage. Any injection or modification is caught before execution, not after.

### Financial Audit Trails
Compute sensitive values in `.a9` programs. The `.a9s` file serves as a tamper-evident log — provably linked to both the source code and the input data.

---

## AI Verification — Complete Example

```bash
pip install aether9
aether compile ai_verify.a9
aether run     ai_verify.a9
aether inspect ai_verify.a9s
```

**`ai_verify.a9`:**
```
ai_scores  = [54, 36, 72, 90, 18, 45]   # AI model outputs
thresholds = [9, 18, 27, 36, 45, 54]    # approved decision thresholds

lattice verify_score(x) uses ai_scores:
    root = dr(x)
    if root == 9:
        return 9
    else:
        return 0

lattice global_integrity(a, b) uses ai_scores:
    total = 0
    for score in ai_scores:
        check = verify_score(score)
        total = total + check
    return total % 9 or 9

integrity = global_integrity(54, 36)
write("integrity_report.txt", integrity)
```

**What happens if the AI output is tampered with:**
```bash
# Someone changes 54 → 55 in ai_scores
$ aether run ai_verify.a9
  ✗  Source code was modified (hash mismatch)
     re-compile if the change is intentional.
```

The `.a9s` file records the exact state that was trusted:
```json
{
  "source_hash": "eb0a3565...",
  "arrays": {
    "ai_scores":  { "raw_sig": 1686592731 },
    "thresholds": { "raw_sig": 310973358  }
  },
  "global_seal": 6
}
```

Any modification — to the source, the data, or the `.a9s` itself — is detected before execution.

---

## How It Works

When you compile a `.a9` program, three things happen:

**1. Data is signed** — every array gets a non-commutative spatial hash (VortexSeal) that encodes both values and their order.

**2. Source is sealed** — a SHA-256 hash of your source code is stored in the `.a9s` signature file.

**3. Functions are locked to data** — each `lattice` function is bound to its array's seal at compile time. On every call, the seal is re-verified.

```json
{
  "version": "1.0",
  "source_hash": "36de8c45...",
  "arrays": {
    "data": { "raw_sig": 1686592731, "seal": 3 }
  },
  "global_seal": 6
}
```

---

## Language Reference

### Arrays

```
data = [54, 36, 72, 90, 18, 45]
```

### Lattice functions

```
# bound to data — verifies seal on every call
lattice compute(a, b) uses data:
    return (a + b) % 9 or 9

# no binding — pure computation
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

while counter < 9:
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
name = input("Enter value: ")
```

### Standard library

| Function | Description |
|----------|-------------|
| `abs(x)` | Absolute value |
| `min(a, b)` | Minimum |
| `max(a, b)` | Maximum |
| `mod(a, b)` | Modulo |
| `len(x)` | String length |
| `str(x)` | Number to string |
| `concat(a, b)` | String concatenation |
| `dr(x)` | Digital root |

### CLI

```bash
aether compile <file.a9>    # compile → .py + .a9s
aether run     <file.a9>    # verify → execute
aether verify  <file.a9>    # check integrity only
aether inspect <file.a9s>   # show seal report
```

---

## Examples

See [`examples/`](examples/):

- `hello.a9` — minimal program
- `energy_fusion.a9` — multi-lattice pipeline
- `ai_verify.a9` — AI agent output verification
- `stdlib_demo.a9` — standard library showcase

---

## License
License Notice

Aether-9 is provided for evaluation and research review only.
Commercial use, integration into products or systems, redistribution, or production deployment is prohibited without prior written permission from Ahmed Harb Akeely.
MIT — see [LICENSE](LICENSE)

---

*Built by Ahmed Harb Akeely*
