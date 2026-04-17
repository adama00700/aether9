# VM Architecture

Aether-9 includes a dedicated stack-based virtual machine.

## Why the VM matters

The VM is important because it makes execution explicit.

Instead of treating generated host code as the only execution object, Aether-9 lowers source into bytecode and then runs that bytecode through a dedicated interpreter.

That enables:

- disassembly
- inspectable runtime behavior
- explicit control flow
- artifact-oriented execution
- richer runtime diagnostics

## Execution Pipeline

```text
source.a9
  -> Lexer
  -> Parser
  -> AST
  -> Bytecode Compiler
  -> .a9b artifact
  -> Aether VM
```

## Public Instruction Categories

The public opcode model includes categories such as:

### Stack
- `LOAD_CONST`
- `LOAD_NAME`
- `STORE_NAME`
- `POP`

### Arithmetic and comparison
- `BINARY_OP`
- `COMPARE`
- `UNARY_NEG`

### Control flow
- `JUMP`
- `JUMP_IF_FALSE`
- `JUMP_BACK`

### Iteration
- `FOR_START`
- `FOR_NEXT`
- `FOR_END`

### Functions
- `MAKE_FUNC`
- `CALL_FUNC`
- `RETURN`

### I/O and builtins
- `PRINT`
- `WRITE`
- `READ`
- `CALL_BUILTIN`

### Program control
- `HALT`

## Runtime Frames

Each function/lattice call runs in a frame with:

- instruction pointer
- stack
- local namespace
- caller context

This is how Aether-9 keeps runtime behavior explicit rather than hidden inside a host interpreter.

## Diagnostics

Recent runtime hardening adds richer failure context:

- error category
- frame name
- instruction pointer
- opcode
- opcode argument
- visible locals
- stack tail
- call stack
- recent trace entries

This makes `aether vm` and runtime debugging more practical for real review.

## Disassembly

Disassembly is available with:

```bash
aether disasm program.a9b
aether disasm program.a9b -v
```

Verbose mode includes:

- artifact summary
- opcode histogram
- function summaries
- sealed function visibility
