"""
Aether-9 Signature System v2.0
─────────────────────────────────────────────────
التغييرات عن v1.0:
  - استبدال digital_root seals بـ HMAC-SHA256
  - global_seal أصبح HMAC على كل البيانات مجتمعة
  - VortexSeal يبقى كـ structural integrity check
  - إضافة signing key اختياري (بيئة الإنتاج)
"""

import json
import hashlib
import hmac
import time
import secrets
from pathlib import Path
from typing import Dict, Tuple, Optional

from .core import VortexSequencer

A9S_VERSION = "2.0"

# ── مفتاح افتراضي للبيئات التي لا تحدد مفتاحاً ──
# في الإنتاج: يجب تمريره من متغير البيئة AETHER9_KEY
_DEFAULT_KEY = b"aether9-integrity-v2"


def _hmac(key: bytes, data: bytes) -> str:
    """HMAC-SHA256 — يُرجع hex string."""
    return hmac.new(key, data, hashlib.sha256).hexdigest()


def _array_mac(key: bytes, name: str, data: list) -> str:
    """
    MAC يجمع اسم المصفوفة + قيمها + ترتيبها.
    أي تغيير في اسم أو قيمة أو ترتيب → MAC مختلف.
    """
    payload = json.dumps({"name": name, "data": data},
                         separators=(",", ":")).encode()
    return _hmac(key, payload)


def _global_mac(key: bytes, array_macs: Dict[str, str],
                source_hash: str) -> str:
    """
    MAC على كل البيانات مجتمعة بترتيب ثابت (sorted).
    يضمن أن إضافة أو حذف مصفوفة يغيّر الـ MAC.
    """
    payload = json.dumps({
        "source_hash":  source_hash,
        "array_macs":   dict(sorted(array_macs.items())),
    }, separators=(",", ":")).encode()
    return _hmac(key, payload)


class SignatureFile:
    """
    بنية .a9s v2.0:
    {
      "version":      "2.0",
      "created_at":   1234567890,
      "source":       "program.a9",
      "source_hash":  "<sha256>",     ← SHA-256 للسورس
      "arrays": {
        "prices": {
          "data":        [...],
          "vortex_sig":  12345,        ← spatial integrity (structural)
          "hmac":        "<hmac>"      ← cryptographic integrity ✅
        }
      },
      "global_mac":   "<hmac>",        ← MAC على الكل ✅
    }
    """

    @staticmethod
    def generate(source: str, arrays: Dict, source_name: str,
                 key: bytes = _DEFAULT_KEY) -> dict:

        source_hash = hashlib.sha256(source.encode()).hexdigest()
        array_macs  = {}
        arrays_out  = {}

        for name, info in arrays.items():
            mac = _array_mac(key, name, info["data"])
            array_macs[name] = mac
            arrays_out[name] = {
                "data":       info["data"],
                "vortex_sig": info["raw_sig"],   # structural check
                "hmac":       mac,               # cryptographic check
            }

        global_mac = _global_mac(key, array_macs, source_hash)

        return {
            "version":     A9S_VERSION,
            "created_at":  int(time.time()),
            "source":      source_name,
            "source_hash": source_hash,
            "arrays":      arrays_out,
            "global_mac":  global_mac,
        }

    @staticmethod
    def save(sig: dict, path: str):
        Path(path).write_text(json.dumps(sig, indent=2))

    @staticmethod
    def load(path: str) -> dict:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Signature file not found: {path}")
        return json.loads(p.read_text())

    @staticmethod
    def verify(sig: dict, source: str,
               key: bytes = _DEFAULT_KEY) -> Tuple[bool, str]:
        """
        يتحقق من ثلاثة أشياء بالترتيب:
        1. SHA-256 السورس كود
        2. HMAC كل مصفوفة على حدة
        3. global_mac (MAC على الكل)
        """
        # 1. source hash
        current_hash = hashlib.sha256(source.encode()).hexdigest()
        if current_hash != sig["source_hash"]:
            return False, "Source code was modified (hash mismatch)"

        # 2. per-array HMAC
        array_macs = {}
        for name, info in sig["arrays"].items():
            expected_mac = info.get("hmac")
            if not expected_mac:
                return False, f"Array '{name}' missing HMAC (v1.0 signature?)"
            actual_mac = _array_mac(key, name, info["data"])
            if not hmac.compare_digest(actual_mac, expected_mac):
                return False, f"Array '{name}' integrity check failed (HMAC mismatch)"
            array_macs[name] = actual_mac

        # 3. global MAC
        expected_global = sig.get("global_mac")
        if not expected_global:
            return False, "Missing global_mac (v1.0 signature?)"
        actual_global = _global_mac(key, array_macs, current_hash)
        if not hmac.compare_digest(actual_global, expected_global):
            return False, "Global MAC mismatch (.a9s file may have been tampered)"

        return True, "OK"
