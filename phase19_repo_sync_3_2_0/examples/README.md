# Aether-9 Examples Pack

This examples pack is organized into three groups.

## 1. Learning examples
- `hello.a9` — smallest possible program
- `control_flow.a9` — arrays, lattices, if/else, for, while
- `stdlib_demo.a9` — builtins such as `abs`, `min`, `max`, `mod`, `str`, `concat`, `len`

## 2. Artifact / runtime examples
- `export_binary_demo.a9` — ideal for `aether export --format binary`
- `inspect_demo.a9` — ideal for `aether inspect` and `aether disasm`
- `vm_execution_demo.a9` — ideal for `aether vm`

## 3. Positioning examples
- `ai_verification.a9` — integrity-flavored scoring flow
- `tamper_detection_demo.a9` — simple sealed-lattice example for signature / tamper demos
- `write_read_demo.a9` — simple file I/O workflow

## Suggested commands

### Export binary artifact
```bash
aether export examples/export_binary_demo.a9 --format binary --force
```

### Inspect artifact
```bash
aether inspect examples/export_binary_demo.a9b -v
```

### Disassemble source or artifact
```bash
aether disasm examples/inspect_demo.a9 -v
aether disasm examples/export_binary_demo.a9b -v
```

### Run through VM
```bash
aether vm examples/vm_execution_demo.a9
aether vm examples/export_binary_demo.a9b
```

### Verify source against sidecar
```bash
aether export examples/tamper_detection_demo.a9 --format json --force
aether verify examples/tamper_detection_demo.a9
```

## Notes
- The examples are intentionally small and reviewable.
- They are designed for demos, documentation, onboarding, and evaluation.
- Public examples do not expose private signing material or internal secrets.
