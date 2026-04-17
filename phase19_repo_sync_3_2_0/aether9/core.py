import time
from typing import Any, List, Tuple


class Aether9Core:
    @staticmethod
    def digital_root(value: Any) -> int:
        if isinstance(value, (int, float)):
            s = str(abs(int(value)))
            dr = sum(int(d) for d in s)
        elif isinstance(value, (list, tuple)):
            dr = sum(Aether9Core.digital_root(i) for i in value)
        else:
            dr = sum(ord(c) for c in str(value))
        while dr > 9:
            dr = sum(int(d) for d in str(dr))
        return 9 if dr in (9, 0) else dr

    @staticmethod
    def resonance_gate(value: Any, expected: int) -> Any:
        dr = Aether9Core.digital_root(value)
        if dr != expected:
            raise ValueError(
                f"⚠️  Asymmetry: {value} has root {dr}, expected {expected}"
            )
        return value

    @staticmethod
    def wait_pulse(required_root: int = 9, timeout_ms: int = 100) -> bool:
        start = time.time_ns()
        while True:
            if Aether9Core.digital_root(time.time_ns()) == required_root:
                return True
            if (time.time_ns() - start) > timeout_ms * 1_000_000:
                return False
            time.sleep(0.000005)


class VortexSequencer:
    SEQUENCE = [1, 2, 4, 8, 7, 5]

    def __init__(self, data: List[Any]):
        self.data = list(data)

    def compute_seal(self) -> Tuple[int, int]:
        n, sig = len(self.data), 0
        for step in range(n):
            idx = (step * self.SEQUENCE[step % 6]) % n
            val = self.data[idx]
            sig = (sig * 31 + (val * (step + 1)) + step) % (2 ** 32)
        return sig, Aether9Core.digital_root(sig)

    def flow(self) -> Tuple[List[Any], int, int]:
        results = []
        n = len(self.data)
        for step in range(n):
            idx = (step * self.SEQUENCE[step % 6]) % n
            results.append(self.data[idx])
        raw_sig, seal = self.compute_seal()
        return results, raw_sig, seal


def lattice_equilibrium(
    required_root: int = 9,
    strict: bool = True,
    vortex_data: List[Any] = None,
    expected_raw_sig: int = None,
):
    def decorator(func):
        def wrapper(*args, **kwargs):
            if vortex_data is not None:
                raw_sig, _ = VortexSequencer(vortex_data).compute_seal()
                if expected_raw_sig is not None and raw_sig != expected_raw_sig:
                    raise RuntimeError(
                        f"❌ Vortex Tampered! got={raw_sig}, expected={expected_raw_sig}"
                    )
            Aether9Core.wait_pulse(9)
            result = func(*args, **kwargs)
            root = Aether9Core.digital_root(result)
            if strict and root != required_root:
                raise RuntimeError(
                    f"❌ Lattice Asymmetry! root={root}, expected={required_root}"
                )
            return result
        return wrapper
    return decorator
