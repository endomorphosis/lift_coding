#!/usr/bin/env python3
"""Copy AF-025 outputs into the snapshot tree, hash artifacts, and write the receipt."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[5]
PAPER = REPO_ROOT / "papers/completion/autoformalization"
SNAP = PAPER / "receipts" / "snapshots" / "AF-025"
RECEIPT = PAPER / "receipts" / "AF-025.json"
SEALED_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"
PYTHON = "/usr/bin/python3.12"

OUTPUTS = {
    "papers/completion/autoformalization/evidence/final_reproduction.json":
        "papers/completion/autoformalization/receipts/snapshots/AF-025/outputs/evidence/final_reproduction.json",
    "papers/completion/autoformalization/submission/author_review_packet.md":
        "papers/completion/autoformalization/receipts/snapshots/AF-025/outputs/submission/author_review_packet.md",
    "papers/completion/autoformalization/submission/checksums.json":
        "papers/completion/autoformalization/receipts/snapshots/AF-025/outputs/submission/checksums.json",
}

CRITERIA = [
    {
        "criterion": "Reproduction result includes exact commands/environment, expected versus actual tables, and explicit unavailable checks; mere LaTeX compilation is not empirical validation.",
        "status": "met",
        "explanation": "final_reproduction.json records sealed-PATH /usr/bin/python3.12 commands for regenerate_tables.py --check and verify_retained_inputs.py on the unpacked anonymous supplement, plus paper-tree SHA-256 comparison. Expected versus actual hashes match a2ebba34895da30b383954e93ec582d2738a212d15de7b329fecf5a4d0c7aa49, dcb2582f2c091a48b3c26bb1b1698e1287d70d77cc2c3824b4f1f822bd2d6e74, 655dfb58c0c1a960b636dbe35292ee243fbcb197fad1108f8a047742e2f62d3f, and 62e63725fe02f4ac9f9c5a3b397d0b2d9f9d7a1e25fc87e9eb7fdc21cb01cc72. Sealed-PATH lean/lake/elan/z3/cvc5/vampire/eprover/coqc/isabelle probes are unavailable. LaTeX compilation is explicitly not empirical validation and was not used as such.",
        "evidence": [
            "papers/completion/autoformalization/receipts/snapshots/AF-025/outputs/evidence/final_reproduction.json",
            "papers/completion/autoformalization/receipts/snapshots/AF-025/logs/zip_regenerate_tables.stdout.log",
            "papers/completion/autoformalization/receipts/snapshots/AF-025/logs/check_outputs.stdout.log",
        ],
    },
    {
        "criterion": "Final packet links manuscript, supplement, claim audit and raw evidence with version/checksum identities.",
        "status": "met",
        "explanation": "checksums.json pins SHA-256 identities for the anonymous PDF, supplement ZIP, claim audit, summary/tables, native-checker and example receipts, official templates, and final_reproduction.json under analysis_id 392407da2432633405e512e2e0b17e960ed89c2a3552f4a09959e73125fc4c43 and AF-028 scope policy. author_review_packet.md quotes those identities and the live table hashes.",
        "evidence": [
            "papers/completion/autoformalization/receipts/snapshots/AF-025/outputs/submission/checksums.json",
            "papers/completion/autoformalization/receipts/snapshots/AF-025/outputs/submission/author_review_packet.md",
            "papers/completion/autoformalization/receipts/snapshots/AF-025/logs/check_outputs.stdout.log",
        ],
    },
    {
        "criterion": "The manuscript objective is complete when every retained automated empirical claim has real reproducible evidence and omitted/unmeasured human-dependent claims are explicit. Outside reviewers and optional author feedback are not prerequisites; unfinished required training or fabricated scientific evidence cannot be hidden by the scope change.",
        "status": "met",
        "explanation": "Retained automated claims in the AF-022 ledger have live source files. C1-C6 remain unrun; independent human fidelity remains unmeasured_not_collected; C7 is inconclusive. AF-029 packed-CPU updates stay claim_admissible=false, T2 update_counts=[0], T4 unactivated, and Arm E locked. The AF-028 scope change does not convert those into measured success. Outside reviewers and optional author feedback are recorded as not required.",
        "evidence": [
            "papers/completion/autoformalization/receipts/snapshots/AF-025/outputs/evidence/final_reproduction.json",
            "papers/completion/autoformalization/receipts/snapshots/AF-025/outputs/submission/author_review_packet.md",
            "papers/completion/autoformalization/receipts/snapshots/AF-025/logs/check_outputs.stdout.log",
        ],
    },
    {
        "criterion": "No claim that authors approved or the paper was submitted/published is made without real evidence.",
        "status": "met",
        "explanation": "final_reproduction.json, checksums.json, and author_review_packet.md set author_sign_off, workshop_submission, openreview_upload, and public_upload to false. The packet states it does not record author sign-off and does not claim an abstract or paper was submitted. Tentative CFP dates remain author-confirmed live facts.",
        "evidence": [
            "papers/completion/autoformalization/receipts/snapshots/AF-025/outputs/submission/author_review_packet.md",
            "papers/completion/autoformalization/receipts/snapshots/AF-025/outputs/evidence/final_reproduction.json",
            "papers/completion/autoformalization/receipts/snapshots/AF-025/outputs/submission/checksums.json",
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


def hash_tree() -> dict[str, str]:
    artifacts = {}
    for path in sorted(SNAP.rglob("*")):
        if not path.is_file():
            continue
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        rel = str(path.relative_to(REPO_ROOT))
        artifacts[rel] = sha256(path)
    return artifacts


def sealed_env(home: Path) -> list[str]:
    return [
        "/usr/bin/env", "-i",
        f"PATH={SEALED_PATH}",
        f"HOME={home}",
        f"XDG_CACHE_HOME={home / '.cache'}",
        f"XDG_CONFIG_HOME={home / '.config'}",
        f"XDG_DATA_HOME={home / '.local/share'}",
        f"XDG_STATE_HOME={home / '.local/state'}",
        "PYTHONDONTWRITEBYTECODE=1",
        "PYTHONNOUSERSITE=1",
        "LANG=C.UTF-8",
        PYTHON,
        "-S",
        str((HERE / "assemble_packet.py").relative_to(REPO_ROOT)),
    ]


def main() -> int:
    home = Path(tempfile.mkdtemp(prefix="ipfs-accelerate-validation-home-af025-"))
    os.makedirs(home / ".cache", exist_ok=True)
    os.makedirs(home / ".config", exist_ok=True)
    os.makedirs(home / ".local" / "share", exist_ok=True)
    os.makedirs(home / ".local" / "state", exist_ok=True)
    (SNAP / "logs").mkdir(parents=True, exist_ok=True)
    packet = subprocess.run(
        sealed_env(home),
        cwd=str(REPO_ROOT),
        check=False,
        capture_output=True,
        text=True,
        env=None,
    )
    (SNAP / "logs" / "assemble_packet.stdout.log").write_text(packet.stdout, encoding="utf-8")
    (SNAP / "logs" / "assemble_packet.stderr.log").write_text(packet.stderr, encoding="utf-8")
    if packet.returncode != 0:
        print("packet assembly failed", file=sys.stderr)
        print(packet.stdout, file=sys.stderr)
        print(packet.stderr, file=sys.stderr)
        return packet.returncode
    copy_outputs()
    sealed = subprocess.run(
        [sys.executable, str(HERE / "run_sealed.py")],
        cwd=str(REPO_ROOT),
        check=False,
    )
    if sealed.returncode != 0:
        print("sealed checks failed", file=sys.stderr)
        stdout = (SNAP / "logs" / "check_outputs.stdout.log").read_text(encoding="utf-8") if (SNAP / "logs" / "check_outputs.stdout.log").is_file() else ""
        stderr = (SNAP / "logs" / "check_outputs.stderr.log").read_text(encoding="utf-8") if (SNAP / "logs" / "check_outputs.stderr.log").is_file() else ""
        print(stdout, file=sys.stderr)
        print(stderr, file=sys.stderr)
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
            "log": f"papers/completion/autoformalization/receipts/snapshots/AF-025/logs/{name}.stdout.log",
            "stderr_log": f"papers/completion/autoformalization/receipts/snapshots/AF-025/logs/{name}.stderr.log",
            "execution_kind": {
                "python_version": "sealed-PATH interpreter identity",
                "json_parse": "JSON parse pin of final_reproduction.json and checksums.json",
                "check_outputs": "stdlib table-hash, native-checker unavailability, PDF/supplement/claim-ledger, and packet checks; no model, training, or provider call",
            }[name],
        }
        if name == "check_outputs":
            command["script_artifact"] = "papers/completion/autoformalization/receipts/snapshots/AF-025/check_outputs.py"
        commands.append(command)
        if command["exit_code"] != 0:
            print(f"{name} failed", file=sys.stderr)
            return 1
    artifacts = hash_tree()
    receipt = {
        "schema": "paper-task-evidence/v1",
        "task_id": "AF-025",
        "status": "complete",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "source_versions": {
            "python": {
                "interpreter": "/usr/bin/python3.12",
                "version": (SNAP / "logs" / "python_version.stdout.log").read_text(encoding="utf-8").strip(),
                "path": SEALED_PATH,
            },
            "checker": {
                "source": "papers/completion/autoformalization/receipts/snapshots/AF-025/check_outputs.py",
                "sha256": artifacts["papers/completion/autoformalization/receipts/snapshots/AF-025/check_outputs.py"],
                "schema": "autoformalization-final-reproduction/v1",
                "standard_library_only": True,
            },
            "analysis_id": "392407da2432633405e512e2e0b17e960ed89c2a3552f4a09959e73125fc4c43",
            "empirical_execution": "Stdlib sealed-PATH ZIP table regeneration, retained-input locator, native-checker unavailability probes, and PDF/supplement/claim-ledger inspection. No model call, training, native-checker execution, public upload, or fabricated author sign-off. LaTeX compilation is not empirical validation.",
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
