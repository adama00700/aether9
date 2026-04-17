# Security Model

This document describes the **public** security model of Aether-9.

## Public Design Goal

Aether-9 is designed for execution workflows where control, verification, and inspectability matter.

Publicly visible protections include:

- artifact verification workflows
- lattice-bound integrity checks
- AST guard behavior
- sandboxed execution paths
- write allow-list policies
- runtime diagnostics for suspicious or invalid behavior

## AST Guard and Sandbox

The sandbox path is designed to reject unsafe patterns such as unrestricted host-language escape behavior.

Public tests and behavior show blocked patterns such as:

- `import`
- `from ... import`
- `eval`
- `exec`
- direct `open`
- unsafe dunder-style object traversal

Execution policies can also control writable outputs.

## Policy Example

```json
{
  "allow_write": ["report.txt", "output.txt"],
  "max_runtime": 30,
  "max_memory_mb": 128,
  "allow_network": false
}
```

## Verification Model

Aether-9's public verification workflow ties source and execution-critical metadata to sidecar information.

This improves trust around:

- whether source changed
- whether bound arrays changed
- whether execution-relevant metadata still matches

## Public Boundary

These docs are intentionally public-safe.

They do **not** disclose:

- private signing keys
- secret constants
- hidden trust material
- non-public operational parameters
- sensitive implementation details that should remain private

## Operational Framing

Aether-9 should be presented publicly as:

> a VM-based language and execution framework for verifiable, tamper-aware, policy-controlled execution

That is more accurate than describing it as only another general-purpose language.
