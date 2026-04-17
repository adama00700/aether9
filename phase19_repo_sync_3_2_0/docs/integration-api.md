# Integration API

Aether-9 v3.1.1 plus the Phase 11 integration pack adds a small Python-facing API for common workflows.

## Goals

The integration API is designed for callers that want structured results without having to shell out to the CLI.

Supported workflows:
- export source file to artifact
- inspect artifact or signature path
- verify source against signature
- run source or artifact through the VM
- chain export plus inspect in one call

## Example

```python
from aether9.api import export_file, inspect_path, verify_file, run_file

exported = export_file('examples/hello.a9', format='binary', force=True)
print(exported.to_dict())

inspected = inspect_path('examples/hello.a9b')
print(inspected.to_dict())

verified = verify_file('examples/hello.a9')
print(verified.to_dict())

ran = run_file('examples/hello.a9b')
print(ran.to_dict())
```

## Result model

Every API call returns a dataclass result with:
- `success`
- `error_type`
- `error_message`

and workflow-specific fields such as artifact path, metadata, stdout, return value, or verification status.

## Current design note

This pack intentionally focuses on file-based integration first. It does not yet introduce a full in-memory artifact API or machine-readable CLI flags. Those remain part of later v3.2.0 phases.
