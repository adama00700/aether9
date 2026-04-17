# Examples Guide

The repository examples are organized into three groups.

## Learning Examples

### `hello.a9`
The smallest readable example.

### `control_flow.a9`
Demonstrates:
- arrays
- lattice functions
- if/else
- for loops
- while loops

### `stdlib_demo.a9`
Shows public builtin functions:
- `abs`
- `min`
- `max`
- `mod`
- `str`
- `concat`
- `len`

## Artifact / Runtime Examples

### `export_binary_demo.a9`
Use this when demonstrating export:

```bash
aether export examples/export_binary_demo.a9 --format binary --force
```

### `inspect_demo.a9`
Use this when demonstrating inspection and disassembly:

```bash
aether inspect examples/export_binary_demo.a9b -v
aether disasm examples/inspect_demo.a9 -v
```

### `vm_execution_demo.a9`
Use this when demonstrating VM execution:

```bash
aether vm examples/vm_execution_demo.a9
```

## Positioning Examples

### `ai_verification.a9`
A small integrity-flavored scoring flow.

### `tamper_detection_demo.a9`
Useful when demonstrating sidecars and verification:

```bash
aether export examples/tamper_detection_demo.a9 --format json --force
aether verify examples/tamper_detection_demo.a9
```

### `write_read_demo.a9`
Demonstrates simple file I/O and policy usage.

## Notes

- These examples are intentionally short and reviewable.
- They are useful for onboarding, demos, docs, and evaluation.
- They do not expose non-public signing material.
