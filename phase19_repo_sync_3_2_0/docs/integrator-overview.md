# Integrator Overview

Aether-9 can now be consumed in three ways:

1. As a **language and CLI tool**
2. As a **VM-based artifact workflow**
3. As a **Python-embedded component** through `aether9.api`

For integrators, the third path is usually the most important.

## Integration entry points

The public integration API focuses on four high-value operations:

- export source to an artifact
- inspect an artifact or signature sidecar
- verify source against its sidecar
- run source or artifact through the Aether VM

These operations are intentionally exposed as stable, structured helpers rather than requiring callers to parse human-readable CLI output.

## Why this matters

Integrators usually need:

- stable entry points
- structured return values
- predictable failure categories
- machine-readable metadata
- examples showing Aether as a component in a larger workflow

Aether-9's integration API is designed around those requirements.

## Recommended integration model

The preferred flow for most systems is:

```text
source.a9
   -> export_file(...)
   -> inspect_path(...)
   -> verify_file(...)
   -> run_file(...)
```

This keeps export, review, verification, and execution separated into explicit phases.

## Result object model

The API returns structured result objects that expose:

- `success`
- `error_type`
- `error_message`
- operation-specific metadata

Each result object can be converted to a dictionary with `to_dict()`.

## Best-fit integration scenarios

Aether-9 is especially suitable when the host system needs:

- controlled execution
- explicit artifact generation
- inspectable runtime inputs
- policy-aware workflow design
- repeatable validation and review paths

## What the API does not try to do

The current API does not aim to replace large orchestration frameworks or general plugin systems. It is intentionally scoped around the artifact and runtime lifecycle of Aether itself.
