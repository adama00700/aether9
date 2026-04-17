# Getting Started

This guide walks through the shortest path from a source file to an inspected and executed Aether-9 artifact.

## 1. Install

```bash
pip install aether9==3.1.0
```

Check the installed version:

```bash
aether --version
```

## 2. Write a minimal program

Create a file named `hello.a9`:

```aether
data = [54, 36, 72]

lattice verify(x) uses data:
    return dr(x) or 9

result = verify(54)
print(result)
```

## 3. Export an artifact

Export the source file into a bytecode artifact:

```bash
aether export hello.a9 --format binary
```

This produces:

- `hello.a9b`
- `hello.a9s`

## 4. Inspect the artifact

```bash
aether inspect hello.a9b
```

Verbose inspection:

```bash
aether inspect hello.a9b -v
```

## 5. Disassemble it

```bash
aether disasm hello.a9b
```

Verbose disassembly:

```bash
aether disasm hello.a9b -v
```

## 6. Run it through the VM

```bash
aether vm hello.a9b
```

You can also run directly from source:

```bash
aether vm hello.a9
```

## 7. Verify the source against its sidecar

```bash
aether verify hello.a9
```

## Suggested next steps

- Read the [Language Reference](language-reference.md)
- Review the [CLI Reference](cli-reference.md)
- Browse the [Examples Guide](examples.md)
