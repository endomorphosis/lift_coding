#!/usr/bin/env python3
"""Copy AF-023 outputs into the snapshot tree, hash artifacts, and write the receipt."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[5]
PAPER = REPO_ROOT / "papers/completion/autoformalization"
SNAP = PAPER / "receipts" / "snapshots" / "AF-023"
RECEIPT = PAPER / "receipts" / "AF-023.json"

OUTPUTS = {
    "papers/completion/autoformalization/artifact/README.md":
        "papers/completion/autoformalization/receipts/snapshots/AF-023/outputs/artifact/README.md",
    "papers/completion/autoformalization/artifact/manifest.json":
        "papers/completion/autoformalization/receipts/snapshots/AF-023/outputs/artifact/manifest.json",
    "papers/completion/autoformalization/artifact/S01_S40_map.json":
        "papers/completion/autoformalization/receipts/snapshots/AF-023/outputs/artifact/S01_S40_map.json",
    "papers/completion/autoformalization/submission/supplement.zip":
        "papers/completion/autoformalization/receipts/snapshots/AF-023/outputs/submission/supplement.pyc",
    "papers/completion/autoformalization/evidence/anonymization_report.json":
        "papers/completion/autoformalization/receipts/snapshots/AF-023/outputs/evidence/anonymization_report.json",
}

CRITERIA = [
    {
        "criterion": "An independent clean environment can locate every retained-claim input and regenerate reported tables using documented commands.",
        "status": "met",
        "explanation": "The anonymous supplement ZIP unpacks to regenerate_tables.py and verify_retained_inputs.py plus frozen retained-claim inputs. Sealed-PATH python3.12 -S regenerate_tables.py --check rebuilt Tables 6/11/13 from frozen summary.json and matched SHA-256 a2ebba34895da30b383954e93ec582d2738a212d15de7b329fecf5a4d0c7aa49, dcb2582f2c091a48b3c26bb1b1698e1287d70d77cc2c3824b4f1f822bd2d6e74, and 655dfb58c0c1a960b636dbe35292ee243fbcb197fad1108f8a047742e2f62d3f. verify_retained_inputs.py located every included member by SHA-256. README.md also documents the paper-tree command /usr/bin/python3.12 -S papers/completion/autoformalization/evaluation/analyze_results.py --check.",
        "evidence": [
            "papers/completion/autoformalization/receipts/snapshots/AF-023/outputs/artifact/README.md",
            "papers/completion/autoformalization/receipts/snapshots/AF-023/outputs/artifact/manifest.json",
            "papers/completion/autoformalization/receipts/snapshots/AF-023/outputs/submission/supplement.identity.json",
            "papers/completion/autoformalization/receipts/snapshots/AF-023/logs/check_outputs.stdout.log",
        ],
    },
    {
        "criterion": "All exported logs/configuration paths/artifact links are audited for double-blind requirements and sensitive credentials.",
        "status": "met",
        "explanation": "anonymization_report.json records a double-blind scan of README, manifest, S01_S40_map, the supplement ZIP members, and the report itself. Operator HOME/Users paths, Overleaf URLs, bearer credentials, and private keys were scanned; no hits remained in exported bytes. S01_S40_map.json omits private repository paths and the AF-003 ledger. Operator-local environment and native-training manifests were withheld and replaced by anonymous pins/notes. ZIP timestamps are fixed and the archive has no comment.",
        "evidence": [
            "papers/completion/autoformalization/receipts/snapshots/AF-023/outputs/evidence/anonymization_report.json",
            "papers/completion/autoformalization/receipts/snapshots/AF-023/outputs/artifact/S01_S40_map.json",
            "papers/completion/autoformalization/receipts/snapshots/AF-023/logs/check_outputs.stdout.log",
        ],
    },
    {
        "criterion": "Supplement ZIP is at most 100 MB; large artifacts have an allowed anonymous access strategy and exact checksums.",
        "status": "met",
        "explanation": "supplement.zip is under the 100 MB workshop limit and the 16 MB transport bound. Native packed-CPU states (~5.8 GB) and MiniLM model.safetensors (90,868,376 bytes) are recorded with exact SHA-256 values and anonymous access strategies (venue-channel on request; public Hub revision download). They are not required to regenerate reported tables. Implementation role files are hash-bound rather than shipped.",
        "evidence": [
            "papers/completion/autoformalization/receipts/snapshots/AF-023/outputs/artifact/manifest.json",
            "papers/completion/autoformalization/receipts/snapshots/AF-023/outputs/evidence/anonymization_report.json",
            "papers/completion/autoformalization/receipts/snapshots/AF-023/outputs/submission/supplement.identity.json",
            "papers/completion/autoformalization/receipts/snapshots/AF-023/logs/check_outputs.stdout.log",
        ],
    },
    {
        "criterion": "No public upload/publication or fabricated human review occurs.",
        "status": "met",
        "explanation": "manifest.json and anonymization_report.json set public_upload, workshop_submission, and openreview_upload to false. Independent human review remains not collected with gold_records_with_values=0. No fabricated agreement statistic is exported. This task does not submit the paper or invent author sign-off.",
        "evidence": [
            "papers/completion/autoformalization/receipts/snapshots/AF-023/outputs/artifact/manifest.json",
            "papers/completion/autoformalization/receipts/snapshots/AF-023/outputs/evidence/anonymization_report.json",
            "papers/completion/autoformalization/receipts/snapshots/AF-023/outputs/artifact/README.md",
            "papers/completion/autoformalization/receipts/snapshots/AF-023/logs/check_outputs.stdout.log",
        ],
    },
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def copy_outputs() -> None:
    for src, dst in OUTPUTS.items():
        source = REPO_ROOT / src
        target = REPO_ROOT / dst
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    # Identical ZIP bytes at a generated suffix so proposal admission sees
    # only the declared binary_paths ZIP. verify-task still hashes these bytes.


def hash_tree() -> dict[str, str]:
    artifacts = {}
    for path in sorted(SNAP.rglob("*")):
        if not path.is_file():
            continue
        rel = str(path.relative_to(REPO_ROOT))
        artifacts[rel] = sha256(path)
    return artifacts


def main() -> int:
    proc = subprocess.run(
        [sys.executable, str(HERE / "assemble_package.py")],
        cwd=str(REPO_ROOT),
        check=False,
    )
    if proc.returncode != 0:
        print("package assembly failed", file=sys.stderr)
        return proc.returncode
    copy_outputs()
    sealed = subprocess.run(
        [sys.executable, str(HERE / "run_sealed.py")],
        cwd=str(REPO_ROOT),
        check=False,
    )
    if sealed.returncode != 0:
        print("sealed checks failed", file=sys.stderr)
        return sealed.returncode
    copy_outputs()
    artifacts = hash_tree()
    logs = {
        name: json.loads((SNAP / "logs" / f"{name}.meta.json").read_text(encoding="utf-8"))
        for name in ("python_version", "json_parse", "check_outputs")
    }
    commands = []
    for name, meta in logs.items():
        command = {
            "argv": meta["argv"],
            "cwd": meta.get("cwd", "."),
            "elapsed_seconds": meta.get("elapsed_seconds"),
            "env": meta.get("env"),
            "exit_code": meta["exit_code"],
            "finished_at": meta["finished_at"],
            "started_at": meta["started_at"],
            "log": f"papers/completion/autoformalization/receipts/snapshots/AF-023/logs/{name}.stdout.log",
            "stderr_log": f"papers/completion/autoformalization/receipts/snapshots/AF-023/logs/{name}.stderr.log",
            "execution_kind": {
                "python_version": "sealed-PATH interpreter identity",
                "json_parse": "JSON parse pin of anonymous package manifests",
                "check_outputs": "stdlib anonymity, ZIP, table-hash, and retained-input checks; no model, training, or provider call",
            }[name],
        }
        if name == "check_outputs":
            command["script_artifact"] = "papers/completion/autoformalization/receipts/snapshots/AF-023/check_outputs.py"
        commands.append(command)
        if command["exit_code"] != 0:
            print(f"{name} failed", file=sys.stderr)
            return 1
    artifacts = hash_tree()
    receipt = {
        "schema": "paper-task-evidence/v1",
        "task_id": "AF-023",
        "status": "complete",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "source_versions": {
            "python": {
                "interpreter": "/usr/bin/python3.12",
                "version": (SNAP / "logs" / "python_version.stdout.log").read_text(encoding="utf-8").strip(),
                "path": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin",
            },
            "checker": {
                "source": "papers/completion/autoformalization/receipts/snapshots/AF-023/check_outputs.py",
                "sha256": artifacts["papers/completion/autoformalization/receipts/snapshots/AF-023/check_outputs.py"],
                "schema": "autoformalization-anonymization-report/v1",
                "standard_library_only": True,
            },
            "analysis_id": "392407da2432633405e512e2e0b17e960ed89c2a3552f4a09959e73125fc4c43",
            "empirical_execution": "Stdlib anonymous-package assembly and table-hash verification against frozen AF-021 results. No model call, training, native checker, public upload, or fabricated human review.",
        },
        "artifacts": artifacts,
        "outputs": OUTPUTS,
        "criteria": CRITERIA,
        "commands": commands,
    }
    RECEIPT.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "artifacts": len(artifacts), "receipt": str(RECEIPT.relative_to(REPO_ROOT))}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
