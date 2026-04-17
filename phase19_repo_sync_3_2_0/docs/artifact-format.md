# Artifact Format

Aether-9 uses `.a9b` as the executable artifact container and `.a9s` as the verification sidecar.

## `.a9b` Overview

The `.a9b` artifact is the executable representation of an Aether program after bytecode compilation.

It exists in two public forms:

- JSON artifact form
- Binary artifact form

## JSON Artifact

JSON artifacts are primarily useful for:

- developer inspection
- tests
- debugging
- readable fixtures

Create one with:

```bash
aether export program.a9 --format json
```

## Binary Artifact

Binary artifacts are primarily useful for:

- compact distribution
- VM execution
- cleaner packaging
- execution-oriented workflows

Create one with:

```bash
aether export program.a9 --format binary
```

## Public Contract Fields

At a high level, public artifact metadata includes:

- contract
- version
- format
- sections
- instruction count
- functions
- arrays
- opcode histogram
- function summaries
- sealed function count

You can view these with:

```bash
aether inspect program.a9b
aether inspect program.a9b -v
```

## Typical Artifact Contents

An artifact contains public execution data such as:

- main instruction list
- function bodies
- function seal metadata
- bound array registry

## `.a9s` Sidecar

The `.a9s` sidecar is used for verification workflows.

It commonly includes public fields such as:

- source hash
- per-array integrity metadata
- global verification metadata

Verify a source file with:

```bash
aether verify program.a9
```

## Important Notes

- Public docs intentionally describe the artifact model at a workflow level.
- Private keys, signing secrets, and non-public implementation details should not be documented in public repositories.
- The runtime-facing artifact model is closely related to the [VM Architecture](vm-architecture.md).
