# Runtime Diagnostics

Aether-9 now includes richer runtime diagnostics for VM failures and artifact review.

## Error Categories

The public VM diagnostics model includes categories such as:

- `validation_error`
- `execution_error`
- `stack_error`
- `name_error`
- `arity_error`
- `security_error`

## Runtime Context

When a VM failure occurs, diagnostics may include:

- frame
- instruction pointer
- opcode
- opcode argument
- visible locals
- stack tail
- call stack
- recent trace entries

## Why this matters

This improves:

- debugging usability
- execution review
- failure clarity
- developer ergonomics
- runtime observability

## CLI Touchpoints

Diagnostics are visible through:

```bash
aether vm program.a9b -v
aether inspect program.a9b -v
aether disasm program.a9b -v
```

## Scope

This is a developer-facing diagnostics layer. It does not change the public language syntax, but it makes the runtime much easier to inspect and troubleshoot.
