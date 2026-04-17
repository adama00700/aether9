from __future__ import annotations

import json
from pathlib import Path

from aether9.api import export_file, inspect_path, verify_file

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "inspect_demo.a9"

exp = export_file(TARGET, format="binary", force=True)
ins = inspect_path(exp.artifact_path) if exp.success and exp.artifact_path else None
ver = verify_file(TARGET)

payload = {
    "export": exp.to_dict(),
    "inspect": ins.to_dict() if ins else None,
    "verify": ver.to_dict(),
}

print(json.dumps(payload, indent=2, sort_keys=True))
