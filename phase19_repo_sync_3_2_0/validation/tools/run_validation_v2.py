from __future__ import annotations

import csv
import json
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aether9.api import export_file, inspect_path, verify_file, run_file

EXAMPLES = ROOT / "examples"
OUT = ROOT / "validation" / "results_v2"
OUT.mkdir(parents=True, exist_ok=True)

SUMMARY_FILE = OUT / "validation_v2_summary.json"
SCENARIOS_FILE = OUT / "validation_v2_scenarios.json"
CSV_FILE = OUT / "validation_v2_benchmark_runs.csv"
MANIFEST_FILE = OUT / "validation_v2_manifest.json"



def bench(label, fn, repeats=3):
    durs = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        fn()
        durs.append((time.perf_counter() - t0) * 1000.0)
    return {
        "label": label,
        "repeats": repeats,
        "mean_ms": round(statistics.mean(durs), 4),
        "min_ms": round(min(durs), 4),
        "max_ms": round(max(durs), 4),
    }


def run_cli_json(py: str, command: str, target: Path):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    proc = subprocess.run([py, "-m", "aether9.cli", command, str(target), "--json"], cwd=ROOT, capture_output=True, text=True, env=env)
    payload = {}
    try:
        payload = json.loads(proc.stdout.strip() or "{}")
    except Exception:
        payload = {"raw_stdout": proc.stdout, "raw_stderr": proc.stderr}
    return proc.returncode, payload


def run():
    scenarios = []
    hello = EXAMPLES / "hello.a9"
    inspect_demo = EXAMPLES / "inspect_demo.a9"
    hello_bin = OUT / "hello.v2.bin.a9b"
    hello_json = OUT / "hello.v2.json.a9b"
    hello_sig = OUT / "hello.v2.a9s"

    for path in [hello_bin, hello_json, hello_sig, OUT / "bench.bin.a9b", OUT / "bench.a9s", OUT / "tampered_source.a9"]:
        if path.exists():
            path.unlink()

    exp_bin = export_file(hello, output_path=hello_bin, format="binary", signature_path=hello_sig, force=True)
    exp_json = export_file(hello, output_path=hello_json, format="json", write_signature=False, force=True)
    ins_bin = inspect_path(hello_bin)
    ver = verify_file(hello, signature_path=hello_sig)
    run_res = run_file(hello_bin)

    scenarios.extend([
        {"name": "api_export_binary", "success": exp_bin.success, "kind": "api", "details": exp_bin.to_dict()},
        {"name": "api_export_json", "success": exp_json.success, "kind": "api", "details": exp_json.to_dict()},
        {"name": "api_inspect_binary", "success": ins_bin.success, "kind": "api", "details": ins_bin.to_dict()},
        {"name": "api_verify_signature", "success": ver.success and ver.ok, "kind": "api", "details": ver.to_dict()},
        {"name": "api_vm_run_binary", "success": run_res.success, "kind": "api", "details": run_res.to_dict()},
    ])

    tamper_src = EXAMPLES / "tamper_detection_demo.a9"
    tamper_sig = EXAMPLES / "tamper_detection_demo.a9s"
    original = tamper_src.read_text(encoding="utf-8")
    tampered = original.replace("[54, 36, 72]", "[55, 36, 72]")
    tmp_src = OUT / "tampered_source.a9"
    tmp_src.write_text(tampered, encoding="utf-8")
    tamper_ver = verify_file(tmp_src, signature_path=tamper_sig)
    scenarios.append({"name": "api_tamper_detected", "success": (not tamper_ver.ok), "kind": "api", "details": tamper_ver.to_dict()})

    py = sys.executable
    for label, cmd, target in [
        ("inspect", "inspect", hello_bin),
        ("verify", "verify", hello),
        ("vm", "vm", hello_bin),
        ("disasm", "disasm", inspect_demo),
    ]:
        rc, payload = run_cli_json(py, cmd, target)
        scenarios.append({"name": f"cli_{label}", "success": rc == 0 and isinstance(payload, dict) and payload.get("success", True), "kind": "cli", "returncode": rc, "details": payload})

    benches = [
        bench("api_export_binary", lambda: export_file(hello, output_path=OUT / "bench.bin.a9b", format="binary", signature_path=OUT / "bench.a9s", force=True)),
        bench("api_inspect_binary", lambda: inspect_path(hello_bin)),
        bench("api_verify_file", lambda: verify_file(hello, signature_path=hello_sig)),
        bench("api_run_binary", lambda: run_file(hello_bin)),
        bench("cli_inspect_json", lambda: run_cli_json(py, "inspect", hello_bin)),
        bench("cli_verify_json", lambda: run_cli_json(py, "verify", hello)),
        bench("cli_vm_json", lambda: run_cli_json(py, "vm", hello_bin)),
    ]

    summary = {
        "validation_version": "2",
        "contract_focus": "aether9.artifact.v2",
        "api_success_count": sum(1 for s in scenarios if s["kind"] == "api" and s["success"]),
        "cli_success_count": sum(1 for s in scenarios if s["kind"] == "cli" and s["success"]),
        "scenario_count": len(scenarios),
        "benchmarks": benches,
        "artifact_size_bytes": {
            "hello_binary": hello_bin.stat().st_size if hello_bin.exists() else None,
            "hello_json": hello_json.stat().st_size if hello_json.exists() else None,
        },
    }

    (OUT / "validation_v2_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (OUT / "validation_v2_scenarios.json").write_text(json.dumps(scenarios, indent=2), encoding="utf-8")
    with (OUT / "validation_v2_benchmark_runs.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["label", "repeats", "mean_ms", "min_ms", "max_ms"])
        w.writeheader()
        for row in benches:
            w.writerow(row)
    manifest = {
        "validation_version": "2",
        "generated_files": [
            "validation_v2_summary.json",
            "validation_v2_scenarios.json",
            "validation_v2_benchmark_runs.csv",
            "validation_v2_manifest.json",
            "hello.v2.bin.a9b",
            "hello.v2.json.a9b",
            "hello.v2.a9s",
            "tampered_source.a9",
        ]
    }
    (OUT / "validation_v2_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return summary


if __name__ == "__main__":
    if SUMMARY_FILE.exists() and SCENARIOS_FILE.exists() and CSV_FILE.exists() and MANIFEST_FILE.exists():
        print(SUMMARY_FILE.read_text(encoding="utf-8"))
    else:
        print(json.dumps(run(), indent=2))
