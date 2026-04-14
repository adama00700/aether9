"""Tests for Aether-9 .a9s signature system"""
import json
import time
import hashlib
import pytest
import tempfile
import os

from aether9.core      import Aether9Core, VortexSequencer
from aether9.signature import SignatureFile
from aether9.compiler  import Aether9Compiler


class TestDigitalRoot:
    def test_single_digit(self):
        assert Aether9Core.digital_root(9) == 9

    def test_zero_is_nine(self):
        assert Aether9Core.digital_root(0) == 9

    def test_multi_digit(self):
        assert Aether9Core.digital_root(18)  == 9
        assert Aether9Core.digital_root(27)  == 9
        assert Aether9Core.digital_root(54)  == 9
        assert Aether9Core.digital_root(12345) == 6

    def test_list(self):
        assert Aether9Core.digital_root([9, 18, 27]) == 9


class TestVortexSeal:
    def test_deterministic(self):
        data = [54, 36, 72, 90, 18, 45]
        s1 = VortexSequencer(data).compute_seal()
        s2 = VortexSequencer(data).compute_seal()
        assert s1 == s2

    def test_order_sensitive(self):
        """Swapping elements changes the seal."""
        a = VortexSequencer([54, 36]).compute_seal()[0]
        b = VortexSequencer([36, 54]).compute_seal()[0]
        assert a != b

    def test_value_sensitive(self):
        """Changing one value changes the seal."""
        a = VortexSequencer([54, 36, 72]).compute_seal()[0]
        b = VortexSequencer([55, 36, 72]).compute_seal()[0]
        assert a != b

    def test_swap_54_45(self):
        """The classic tamper: swapping 54 and 45."""
        original = VortexSequencer([54, 36, 72, 90, 18, 45]).compute_seal()[0]
        tampered = VortexSequencer([45, 36, 72, 90, 18, 54]).compute_seal()[0]
        assert original != tampered

    def test_single_element(self):
        raw, seal = VortexSequencer([9]).compute_seal()
        assert isinstance(raw, int)
        assert 1 <= seal <= 9


class TestSignatureFile:
    SOURCE = (
        "data = [54, 36, 72]\n"
        "lattice fn(x) uses data:\n"
        "    return (x + 9) % 9 or 9\n"
    )

    def _registry(self):
        raw, seal = VortexSequencer([54, 36, 72]).compute_seal()
        return {"data": {"data": [54, 36, 72], "raw_sig": raw, "seal": seal}}

    def test_generate_keys(self):
        sig = SignatureFile.generate(self.SOURCE, self._registry(), "test.a9")
        assert "version"     in sig
        assert "source_hash" in sig
        assert "arrays"      in sig
        assert "global_mac"  in sig
        assert sig["version"] == "2.0"

    def test_source_hash(self):
        sig = SignatureFile.generate(self.SOURCE, self._registry(), "test.a9")
        expected = hashlib.sha256(self.SOURCE.encode()).hexdigest()
        assert sig["source_hash"] == expected

    def test_verify_ok(self):
        sig = SignatureFile.generate(self.SOURCE, self._registry(), "test.a9")
        ok, msg = SignatureFile.verify(sig, self.SOURCE)
        assert ok
        assert msg == "OK"

    def test_verify_source_modified(self):
        sig = SignatureFile.generate(self.SOURCE, self._registry(), "test.a9")
        modified = self.SOURCE.replace("54", "55")
        ok, msg = SignatureFile.verify(sig, modified)
        assert not ok
        assert "hash mismatch" in msg

    def test_verify_array_hmac_tampered(self):
        reg = self._registry()
        sig = SignatureFile.generate(self.SOURCE, reg, "test.a9")
        sig["arrays"]["data"]["hmac"] = "a" * 64
        ok, msg = SignatureFile.verify(sig, self.SOURCE)
        assert not ok
        assert "HMAC mismatch" in msg

    def test_verify_global_mac_tampered(self):
        sig = SignatureFile.generate(self.SOURCE, self._registry(), "test.a9")
        sig["global_mac"] = "a" * 64  # tampered
        ok, msg = SignatureFile.verify(sig, self.SOURCE)
        assert not ok
        assert "Global MAC" in msg

    def test_save_and_load(self):
        sig = SignatureFile.generate(self.SOURCE, self._registry(), "test.a9")
        with tempfile.NamedTemporaryFile(suffix=".a9s", delete=False, mode='w') as f:
            path = f.name
        try:
            SignatureFile.save(sig, path)
            loaded = SignatureFile.load(path)
            assert loaded["source_hash"] == sig["source_hash"]
            assert loaded["global_mac"] == sig["global_mac"]
        finally:
            os.unlink(path)


class TestFullPipeline:
    """End-to-end: compile → sign → tamper → detect."""

    def test_clean_run(self):
        src = (
            "data = [54, 36, 72]\n"
            "lattice fn(x) uses data:\n"
            "    return (x * 9) % 9 or 9\n"
            "result = fn(54)\n"
        )
        code, registry = Aether9Compiler().compile(src)
        sig = SignatureFile.generate(src, registry, "test.a9")
        ok, msg = SignatureFile.verify(sig, src)
        assert ok

    def test_tamper_detected(self):
        src = (
            "data = [54, 36, 72]\n"
            "lattice fn(x) uses data:\n"
            "    return (x * 9) % 9 or 9\n"
        )
        _, registry = Aether9Compiler().compile(src)
        sig = SignatureFile.generate(src, registry, "test.a9")

        tampered = src.replace("[54, 36, 72]", "[55, 36, 72]")
        ok, msg = SignatureFile.verify(sig, tampered)
        assert not ok
        assert "hash mismatch" in msg
