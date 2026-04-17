# Aether-9 v3.3.0

Aether-9 is a secure, policy-aware bytecode execution layer for AI-native and automation workflows.

This release consolidates the hardened Python VM, official CLI subcommands, JSON `.a9b` compatibility, and the new binary `.a9b` container with `A9B9` magic bytes.

## Install

```bash
pip install aether9==3.3.0
```

For local testing from this release package:

```bash
python -m pip install -e .[dev]
pytest -q
```

## Quick start

Create `program.a9`:

```aether
prices = [54, 36]

lattice verify(x) uses prices:
    print("aether9")
    return (x + 9) % 9 or 9

result = verify(54)
print(result)
```

Run the source through the VM backend:

```bash
aether run program.a9
```

Export bytecode:

```bash
aether export program.a9 --format json
aether export program.a9 --format binary
```

Inspect, verify, disassemble, and run bytecode:

```bash
aether inspect program.a9b
aether verify program.a9b
aether disasm program.a9b
aether run program.a9b
```

## Supported CLI commands

```bash
aether compile program.a9
aether run program.a9
aether run program.a9b
aether export program.a9 --format json
aether export program.a9 --format binary
aether inspect program.a9b
aether disasm program.a9b
aether verify program.a9b
```

## What is included in v3.3.0

- VM hardening and opcode coverage improvements.
- Stack underflow protection and stricter VM error handling.
- JSON `.a9b` backward compatibility.
- Binary `.a9b` container with `A9B9` magic bytes.
- CLI hardening for compile, run, export, inspect, disasm, and verify.
- Full integration tests for source-to-bytecode-to-VM workflows.
- Release packaging for PyPI-style wheel and source distribution.

## Security model summary

Aether-9 combines parser/compiler checks, `.a9s` source signatures, HMAC-backed integrity metadata, sandboxed Python execution for legacy paths, and an independent stack-based VM for `.a9b` bytecode execution.

Do not publish private keys, unreleased constants, or proprietary governance logic in the public repository.
