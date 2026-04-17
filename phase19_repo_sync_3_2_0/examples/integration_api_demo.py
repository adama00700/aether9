from pathlib import Path

from aether9.api import export_file, inspect_path, verify_file, run_file

EXAMPLE = Path(__file__).with_name('hello.a9')
ARTIFACT = EXAMPLE.with_suffix('.demo.a9b')
SIGNATURE = EXAMPLE.with_suffix('.demo.a9s')

exp = export_file(EXAMPLE, output_path=ARTIFACT, format='binary', write_signature=True, signature_path=SIGNATURE, force=True)
print('EXPORT:', exp.to_dict())

ins = inspect_path(ARTIFACT)
print('INSPECT:', ins.to_dict())

ver = verify_file(EXAMPLE, signature_path=SIGNATURE)
print('VERIFY:', ver.to_dict())

run = run_file(ARTIFACT)
print('RUN:', run.to_dict())
