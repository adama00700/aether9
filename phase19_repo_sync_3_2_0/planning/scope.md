# Scope

## Primary objective

Turn Aether-9 from a usable CLI/runtime toolchain into a more integration-ready platform.

## Core goals

### 1. Integration API
Provide a cleaner Python-facing API for common workflows:
- export source to artifact
- inspect artifact
- verify artifact
- run artifact in VM
- obtain structured machine-readable results

### 2. Machine-readable CLI output
Add structured output options for CLI commands where useful, especially:
- `aether inspect --json`
- `aether verify --json`
- `aether vm --json`
- optional structured output for `disasm`

### 3. Artifact contract cleanup
Strengthen and normalize artifact metadata so downstream consumers can parse and trust outputs more consistently.

### 4. Integrator-facing documentation
Document Aether-9 not only as a language and CLI tool, but as a component that can be embedded into larger systems.

### 5. Validation refinement
Extend validation to focus more on reproducible integration-oriented evidence.

## Non-goals

The following are explicitly out of scope for v3.2.0:
- floats
- maps / dicts
- major syntax expansion
- optimizer / JIT work
- alternative runtimes beyond the current VM path
- large stdlib growth
- deep SCP coupling inside the public release
- language feature expansion for its own sake

## Release identity

This is a **platform-integration release**, not a language-breadth release.
