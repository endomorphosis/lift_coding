#!/usr/bin/env python3
"""Copy AF-022 outputs into the snapshot tree, hash artifacts, and write the receipt."""
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
SNAP = PAPER / "receipts" / "snapshots" / "AF-022"
RECEIPT = PAPER / "receipts" / "AF-022.json"

OUTPUTS = {
    "papers/completion/autoformalization/manuscript/main.tex":
        "papers/completion/autoformalization/receipts/snapshots/AF-022/manuscript/main.tex",
    "papers/completion/autoformalization/manuscript/references.bib":
        "papers/completion/autoformalization/receipts/snapshots/AF-022/manuscript/references.bib",
    "papers/completion/autoformalization/evidence/final_claim_audit.json":
        "papers/completion/autoformalization/receipts/snapshots/AF-022/evidence/final_claim_audit.json",
    "papers/completion/autoformalization/evidence/bibliography_audit.md":
        "papers/completion/autoformalization/receipts/snapshots/AF-022/evidence/bibliography_audit.md",
}

CRITERIA = [
    {
        "criterion": "Abstract/conclusion match the measured scope and use no invented checkpoint, deployment, transfer or training results.",
        "status": "met",
        "explanation": "The abstract reports automated structural correctness, exact-goal native checker receipts, teacher-agreement diagnostics, learned-update records, and finite constructed conformance; states that independent human source-facet fidelity and agreement were not collected; and keeps the 1913-unit final-test A--E coverage/cost unrun, fidelity unmeasured, and native useful-proof transfer unavailable. T2 accepted no sealed-PATH epochs; T1 is a sample-memory diagnostic; T3/T4/E/T5 remain unavailable or unrun. The conclusion states that the manuscript does not establish improved independent source fidelity or useful proof coverage on unseen material. Recovery-copy promises are not presented as results. check_outputs.py found no invented checkpoint, deployment, transfer, or training-success claims.",
        "evidence": [
            "papers/completion/autoformalization/receipts/snapshots/AF-022/manuscript/main.tex",
            "papers/completion/autoformalization/receipts/snapshots/AF-022/evidence/final_claim_audit.json",
            "papers/completion/autoformalization/receipts/snapshots/AF-022/logs/check_outputs.stdout.log",
        ],
    },
    {
        "criterion": "Every material claim maps to a source or raw result; finite illustrations and conditional propositions are labeled accurately.",
        "status": "met",
        "explanation": "final_claim_audit.json maps 27 material claims to manuscript locations, kinds, statuses, and source artifacts (summary.json, hypothesis_report.md, reference_results.json, bridge results, empirical_scope.tex). Finite illustrations (twelve reconstructed checks, policy--code--trace Q1/Q2) and the conditional transfer proposition (Equations 7--8 / Proposition 1) are labeled as such. C1--C6 remain unrun; C7 inconclusive; T1 diagnostic is not primary-admissible; T2 shared-learner is unsupported. Equations 1--14 are audited for reconstruction versus text, nonvacuity, and tense.",
        "evidence": [
            "papers/completion/autoformalization/receipts/snapshots/AF-022/evidence/final_claim_audit.json",
            "papers/completion/autoformalization/receipts/snapshots/AF-022/manuscript/main.tex",
            "papers/completion/autoformalization/receipts/snapshots/AF-022/logs/check_outputs.stdout.log",
            "papers/completion/autoformalization/receipts/snapshots/AF-022/logs/json_parse.stdout.log",
        ],
    },
    {
        "criterion": "The final narrative distinguishes A–E pipeline comparisons from T0–T5 learning comparisons.",
        "status": "met",
        "explanation": "The manuscript states that pipeline comparisons A--E vary the source-to-proof mechanism and learning comparisons T0--T5 vary memory, shared parameters, isolated proof heads, promoted guidance, and compiler repair, and that the two matrices are not merged. Separate definition tables tab:arms-ae and tab:arms-t and result tables tab:pipeline-results and tab:training-results are included. Section headings state that the A--E comparison is not a T0--T5 result and conversely. The claim audit records narrative_separation for both matrices.",
        "evidence": [
            "papers/completion/autoformalization/receipts/snapshots/AF-022/manuscript/main.tex",
            "papers/completion/autoformalization/receipts/snapshots/AF-022/evidence/final_claim_audit.json",
            "papers/completion/autoformalization/receipts/snapshots/AF-022/logs/check_outputs.stdout.log",
        ],
    },
    {
        "criterion": "References are verified and missing material comparisons addressed without claiming unrelated benchmarks were run.",
        "status": "met",
        "explanation": "references.bib retains original PDF references [1]--[10] with verified arXiv/DOI/venue metadata. bibliography_audit.md records each primary-source check and the recovered Jiang 2024 venue note. LeanDojo, DSP, Sledgehammer, Baldur, CompCert, seL4, and Dafny are added as related-work placement only, each labeled not executed as a paper benchmark / not re-benchmarked. The manuscript states that ProofNet, miniF2F, LeanDojo, CompCert, seL4, and Dafny were not run.",
        "evidence": [
            "papers/completion/autoformalization/receipts/snapshots/AF-022/manuscript/references.bib",
            "papers/completion/autoformalization/receipts/snapshots/AF-022/evidence/bibliography_audit.md",
            "papers/completion/autoformalization/receipts/snapshots/AF-022/manuscript/main.tex",
            "papers/completion/autoformalization/receipts/snapshots/AF-022/logs/check_outputs.stdout.log",
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
        rel = str(path.relative_to(REPO_ROOT))
        artifacts[rel] = sha256(path)
    return artifacts


def main() -> int:
    copy_outputs()
    proc = subprocess.run(
        [sys.executable, str(HERE / "run_sealed.py")],
        cwd=str(REPO_ROOT),
        check=False,
    )
    if proc.returncode != 0:
        print("sealed checks failed", file=sys.stderr)
        return proc.returncode
    # Re-copy outputs in case checks only read them.
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
            "log": f"papers/completion/autoformalization/receipts/snapshots/AF-022/logs/{name}.stdout.log",
            "stderr_log": f"papers/completion/autoformalization/receipts/snapshots/AF-022/logs/{name}.stderr.log",
            "execution_kind": {
                "python_version": "sealed-PATH interpreter identity",
                "json_parse": "JSON parse pin of final_claim_audit.json",
                "check_outputs": "stdlib manuscript/claim/bibliography acceptance checks; no model, training, or provider call",
            }[name],
        }
        if name == "check_outputs":
            command["script_artifact"] = "papers/completion/autoformalization/receipts/snapshots/AF-022/check_outputs.py"
        commands.append(command)
        if command["exit_code"] != 0:
            print(f"{name} failed", file=sys.stderr)
            return 1
    # Hash again after no further writes except receipt (receipt is not a snapshot artifact).
    artifacts = hash_tree()
    receipt = {
        "schema": "paper-task-evidence/v1",
        "task_id": "AF-022",
        "status": "complete",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "source_versions": {
            "python": {
                "interpreter": "/usr/bin/python3.12",
                "version": (SNAP / "logs" / "python_version.stdout.log").read_text(encoding="utf-8").strip(),
                "path": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin",
            },
            "checker": {
                "source": "papers/completion/autoformalization/receipts/snapshots/AF-022/check_outputs.py",
                "sha256": artifacts["papers/completion/autoformalization/receipts/snapshots/AF-022/check_outputs.py"],
                "schema": "autoformalization-final-claim-audit/v1",
                "standard_library_only": True,
            },
            "analysis_id": "392407da2432633405e512e2e0b17e960ed89c2a3552f4a09959e73125fc4c43",
            "empirical_execution": "Stdlib manuscript, claim-audit, and bibliography checks against frozen AF-021 results. No model call, training, native checker, or final-test body access.",
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
