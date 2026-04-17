# Embedding Cookbook

This document shows practical ways to embed Aether-9 into a Python application.

## Pattern 1 — Export then inspect

Use this when the host system needs to create an artifact and immediately review it.

```python
from aether9.api import export_file, inspect_path

exp = export_file("examples/hello.a9", format="binary", force=True)
if not exp.success:
    raise RuntimeError(exp.error_message)

meta = inspect_path(exp.artifact_path)
print(meta.to_dict())
```

## Pattern 2 — Verify before execution

Use this when the source and sidecar should be checked before the VM is allowed to run.

```python
from aether9.api import verify_file, run_file

ver = verify_file("examples/hello.a9")
if not ver.success:
    raise RuntimeError(ver.message)

run = run_file("examples/hello.a9b")
print(run.stdout)
```

## Pattern 3 — Export, inspect, verify, run

This is the most reviewable integration sequence.

```python
from aether9.api import export_file, inspect_path, verify_file, run_file

exp = export_file("examples/inspect_demo.a9", format="binary", force=True)
ins = inspect_path(exp.artifact_path)
ver = verify_file("examples/inspect_demo.a9")
run = run_file(exp.artifact_path)

payload = {
    "export": exp.to_dict(),
    "inspect": ins.to_dict(),
    "verify": ver.to_dict(),
    "run": run.to_dict(),
}
print(payload)
```

## Pattern 4 — Use results as records

Every result object is designed to be logged or serialized.

```python
record = run.to_dict()
```

This is useful for:

- CI systems
- evaluation pipelines
- review dashboards
- API wrappers around Aether

## Pattern 5 — Separate policy from orchestration

Keep orchestration logic in the host application, and use Aether only for:

- artifact generation
- inspection
- validation
- VM execution

This separation keeps the Aether integration small and easier to maintain.
