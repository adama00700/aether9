from __future__ import annotations

import json
from pathlib import Path

from aether9.api import export_file, verify_file, run_file

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "tamper_detection_demo.a9"
ARTIFACT = TARGET.with_suffix('.a9b')

exported = export_file(TARGET, output_path=ARTIFACT, format="binary", force=True)
verified = verify_file(TARGET)
ran = run_file(ARTIFACT) if exported.success else None

payload = {
    "export": exported.to_dict(),
    "verify": verified.to_dict(),
    "run": ran.to_dict() if ran else None,
}

print(json.dumps(payload, indent=2, sort_keys=True))
