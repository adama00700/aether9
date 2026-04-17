# Aether-9 v3.2.0 — Final Release

Aether-9 v3.2.0 is the final integration-ready platform release following RC2 validation.

## Highlights

- Python integration API via `aether9.api`
- Machine-readable CLI output via `--json`
- Artifact contract v2 metadata cleanup
- JSON and binary artifact support under `aether9.artifact.v2`
- Correct VM JSON metadata reporting for both JSON and binary artifacts
- Integrator documentation and embedding examples
- Validation v2 package with API, CLI, artifact, and tamper-detection scenarios
- Runtime diagnostics with structured error reporting

## Install

```bash
pip install aether9==3.2.0
```

## Basic Usage

```bash
aether --version
aether export hello.a9 --format binary --json
aether inspect hello.a9b --json
aether disasm hello.a9b --json
aether verify hello.a9 --json
aether vm hello.a9b --json
```

## Python API

```python
from aether9.api import export_file, inspect_path, verify_file, run_file

exp = export_file("hello.a9", format="binary", force=True)
ins = inspect_path("hello.a9b")
ver = verify_file("hello.a9")
run = run_file("hello.a9b")
```

## RC2 Fix Included

This final release includes the RC2 fix for `vm --json` metadata reporting on JSON artifacts.
