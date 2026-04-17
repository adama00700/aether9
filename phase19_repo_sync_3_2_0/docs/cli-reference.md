# CLI Reference

The `aether` CLI is the main public interface for compile, export, verify, inspect, disassemble, VM execution, and shell usage.

## Command Summary

```bash
aether compile <file.a9>
aether export  <file.a9> --format <json|binary>
aether verify  <file.a9>
aether run     <file.a9>
aether vm      <file.a9|file.a9b>
aether inspect <file.a9b> [-v]
aether disasm  <file.a9|file.a9b> [-v]
aether shell
```

## `aether compile`

Compiles Aether source to Python and creates a signature sidecar.

```bash
aether compile program.a9
```

Outputs typically include:

- `program.py`
- `program.a9s`

## `aether export`

Exports source into a `.a9b` artifact.

### JSON artifact

```bash
aether export program.a9 --format json
```

### Binary artifact

```bash
aether export program.a9 --format binary
```

### Useful flags

```bash
aether export program.a9 --format binary --force
aether export program.a9 --format binary --output build/program.a9b
aether export program.a9 --format binary --no-signature
```

## `aether verify`

Checks the current source file against its `.a9s` sidecar.

```bash
aether verify program.a9
```

## `aether run`

Runs the source path through the Python compile path.

```bash
aether run program.a9
```

This is different from `aether vm`, which uses the bytecode runtime.

## `aether vm`

Runs a source file or an artifact through the Aether VM.

```bash
aether vm program.a9
aether vm program.a9b
```

Verbose mode prints artifact metadata before execution:

```bash
aether vm program.a9b -v
```

## `aether inspect`

Displays artifact-level metadata.

```bash
aether inspect program.a9b
aether inspect program.a9b -v
```

Verbose mode includes richer metadata such as opcode histogram and per-function summaries.

## `aether disasm`

Shows the bytecode instruction stream.

```bash
aether disasm program.a9
aether disasm program.a9b
aether disasm program.a9b -v
```

## `aether shell`

Starts the interactive REPL:

```bash
aether shell
```

## Diagnostics Notes

The VM and CLI now expose richer runtime diagnostics, including:

- execution category
- frame and instruction pointer
- opcode and argument
- stack tail
- call stack
- recent trace buffer

See [VM Architecture](vm-architecture.md) for more.
