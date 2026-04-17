# Automation Patterns

This document describes how Aether-9 fits into automated workflows.

## Pattern A — CI validation gate

Use Aether as a build-step validation component:

1. export artifact
2. inspect artifact
3. verify source/signature pair
4. run VM smoke test
5. publish artifact only if all steps succeed

## Pattern B — Service-side execution wrapper

A service can expose a narrow API around:

- `export_file`
- `inspect_path`
- `verify_file`
- `run_file`

This is useful when the service wants to provide controlled Aether execution without exposing raw CLI parsing logic.

## Pattern C — Review-first execution

For security-sensitive workflows, the host system can enforce:

```text
export -> inspect -> verify -> approve -> run
```

This is one of the strongest public patterns in the Aether model because it makes execution a deliberate lifecycle rather than an opaque one-step action.

## Pattern D — Machine-readable CLI fallback

When embedding the Python API is not practical, use the CLI with `--json` and consume structured payloads instead of human-readable output.

## Pattern E — Validation package refresh

The validation runner can be used as a recurring evidence generator in:

- CI pipelines
- release qualification
- internal technical review
- integration proof packages

## Preferred practice

Prefer the Python integration API when possible.

Use the CLI with `--json` when the integration boundary is shell-based or process-based.
