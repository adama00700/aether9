from __future__ import annotations

import json
from pathlib import Path

from aether9.api import run_file

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "hello.a9"

result = run_file(TARGET)
print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
