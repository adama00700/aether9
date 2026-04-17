import re
from typing import Dict, List, Tuple

from .core import VortexSequencer, lattice_equilibrium, Aether9Core
from .signature import SignatureFile


class BindingError(Exception):
    pass


class AetherTranspiler:
    ARRAY_P  = re.compile(r'^(\s*)(\w+)\s*=\s*\[([^\]]+)\]')
    LAT_USES = re.compile(r'^(\s*)lattice\s+(\w+)\s*\((.*?)\)\s+uses\s+(\w+)\s*:')
    LAT_PURE = re.compile(r'^(\s*)lattice\s+(\w+)\s*\((.*?)\)\s+pure\s*:')
    LAT_BARE = re.compile(r'^(\s*)lattice\s+(\w+)\s*\((.*?)\)\s*:')

    def __init__(self):
        self.registry: Dict = {}

    def _scan(self, code: str):
        for line in code.split('\n'):
            m = self.ARRAY_P.match(line)
            if m:
                name, data_str = m.group(2), m.group(3)
                try:
                    data = [
                        int(x.strip())
                        for x in data_str.split(',')
                        if x.strip().lstrip('-').isdigit()
                    ]
                    if data:
                        raw, seal = VortexSequencer(data).compute_seal()
                        self.registry[name] = {
                            'data': data, 'raw_sig': raw, 'seal': seal
                        }
                except Exception:
                    pass

    def _transform(self, code: str) -> str:
        out = []
        for i, line in enumerate(code.split('\n'), 1):

            m = self.LAT_USES.match(line)
            if m:
                ind, fn, params, arr = m.groups()
                if arr not in self.registry:
                    raise BindingError(
                        f"line {i}: '{fn}' references undefined array '{arr}'\n"
                        f"  Available: {list(self.registry.keys()) or 'none'}"
                    )
                info = self.registry[arr]
                out.append(
                    f"{ind}@lattice_equilibrium("
                    f"vortex_data={info['data']}, "
                    f"expected_raw_sig={info['raw_sig']})"
                )
                out.append(f"{ind}def {fn}({params}):")
                continue

            m = self.LAT_PURE.match(line)
            if m:
                ind, fn, params = m.groups()
                out.append(f"{ind}@lattice_equilibrium()")
                out.append(f"{ind}def {fn}({params}):")
                continue

            m = self.LAT_BARE.match(line)
            if m:
                ind, fn, params = m.groups()
                raise BindingError(
                    f"line {i}: '{fn}' has no binding.\n"
                    f"  Use 'uses <array>' or 'pure'.\n"
                    f"  Available arrays: {list(self.registry.keys()) or 'none'}"
                )

            out.append(line)
        return '\n'.join(out)

    def compile(self, source: str, source_name: str) -> Tuple[str, dict]:
        self._scan(source)
        secure = self._transform(source)
        sig    = SignatureFile.generate(source, self.registry, source_name)
        return secure, sig

    def execute(self, secure_code: str):
        exec(secure_code, {
            'lattice_equilibrium': lattice_equilibrium,
            'VortexSequencer':     VortexSequencer,
            'Aether9Core':         Aether9Core,
            'print':               print,
        })
