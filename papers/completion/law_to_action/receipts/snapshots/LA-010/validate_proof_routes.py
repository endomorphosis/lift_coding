#!/usr/bin/python3.12
"""Validate LA-010 prover qualification outputs against sealed-environment facts."""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
LIVE = ROOT / "papers" / "completion" / "law_to_action"
SNAP = Path(__file__).resolve().parent


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def main() -> int:
    provers_live = LIVE / "benchmark" / "manifests" / "provers.json"
    raw_live = LIVE / "results" / "proof_jobs" / "raw.jsonl"
    qual_live = LIVE / "results" / "proof_jobs" / "qualification.md"
    provers_snap = SNAP / "outputs" / "benchmark" / "manifests" / "provers.json"
    raw_snap = SNAP / "outputs" / "results" / "proof_jobs" / "raw.jsonl"
    qual_snap = SNAP / "outputs" / "results" / "proof_jobs" / "qualification.md"
    for path in (provers_live, raw_live, qual_live, provers_snap, raw_snap, qual_snap):
        if not path.is_file():
            raise SystemExit(f"missing {path}")
    if provers_live.read_bytes() != provers_snap.read_bytes():
        raise SystemExit("provers.json live/snapshot mismatch")
    if raw_live.read_bytes() != raw_snap.read_bytes():
        raise SystemExit("raw.jsonl live/snapshot mismatch")
    if qual_live.read_bytes() != qual_snap.read_bytes():
        raise SystemExit("qualification.md live/snapshot mismatch")

    manifest = load_json(provers_live)
    jobs = load_jsonl(raw_live)
    text = qual_live.read_text(encoding="utf-8")
    jobs_by_id = {row["job_id"]: row for row in jobs}

    assert manifest["schema"] == "law-to-action-prover-manifest/v1"
    assert manifest["task"] == "LA-010"
    assert manifest["empirical_benchmark_result"] is False
    assert manifest["authoritative_environment"]["python"] == "/usr/bin/python3.12"
    assert manifest["authoritative_environment"]["path"] == os.environ.get("PATH")
    assert manifest["selected_route"]["fragment"] == "QF_BOOL"
    assert manifest["selected_route"]["authority_kind"] == "satisfiability"
    assert manifest["selected_route"]["cannot_authorize_closed_profile_allow"] is True
    assert manifest["selected_route"]["kernel_reconstruction"] is False

    success = jobs_by_id["sat-success-unsat"]
    assert success["outcome"] == "unsat"
    assert success["provider"]["timed_out"] is False
    assert success["provider"]["result"]["status"] == "unsat"
    assert success["provider"]["result"]["algorithm"] == "dpll"
    assert success["checker"]["result"]["status"] == "unsat"
    assert success["checker"]["result"]["agrees_with_provider"] is True
    assert success["authority_kind_emitted"] == "satisfiability"
    assert (SNAP / "traces" / "sat-success-unsat" / "provider.stdout.raw").is_file()
    assert (SNAP / "traces" / "sat-success-unsat" / "checker.stdout.raw").is_file()
    assert (SNAP / "formulas" / "sat-success-unsat.json").is_file()

    counter = jobs_by_id["sat-counterexample"]
    assert counter["outcome"] == "sat"
    assert counter["provider"]["result"]["model"]
    assert counter["checker"]["result"]["status"] == "sat"
    assert counter["checker"]["result"]["agrees_with_provider"] is True

    timeout = jobs_by_id["sat-timeout"]
    assert timeout["provider"]["timed_out"] is True
    assert timeout["outcome"] == "timeout"
    assert timeout["checker"] is None

    unsupported_q = jobs_by_id["sat-unsupported-quantifiers"]
    assert unsupported_q["outcome"] == "unsupported"
    assert unsupported_q["provider"]["result"]["status"] == "unsupported"

    unsupported_i = jobs_by_id["sat-unsupported-qflia-interpolation"]
    assert unsupported_i["outcome"] == "unsupported"
    assert "interpolation" in unsupported_i["provider"]["result"]["reason"].lower() or "QF_LIA" in unsupported_i["provider"]["result"]["reason"]

    forged = jobs_by_id["sat-forged-model"]
    assert forged["forged_evidence_rejected"] is True
    assert forged["forged_checker"]["forged_evidence"] is True
    assert forged["forged_checker"]["claimed_model_accepted"] is False

    sat_only = jobs_by_id["authority-sat-only-cannot-allow"]
    assert sat_only["result"]["allowed"] is False
    assert sat_only["result"]["wire_status"] == "abstain"
    policy = jobs_by_id["authority-policy-cannot-allow"]
    assert policy["result"]["allowed"] is False
    simulated = jobs_by_id["authority-simulated-cannot-allow"]
    assert simulated["result"]["allowed"] is False
    kernel = jobs_by_id["authority-kernel-unavailable"]
    assert kernel["result"]["allowed"] is False
    for name in ("z3", "cvc5", "vampire", "eprover", "lean"):
        probe = kernel["native_probes"][name]
        assert probe["availability"] == "unavailable"
        assert probe["executable_path"] == ""
        assert shutil.which(name) is None

    families = {row["id"]: row for row in manifest["families"]}
    assert families["qf_bool_sympy_sat"]["status"] == "qualified"
    assert families["qf_bool_sympy_sat"]["required_for_benchmark"] is True
    assert families["qf_bool_sympy_sat"]["cannot_authorize_theorem_allow"] is True
    for optional in (
        "z3_smt",
        "cvc5_smt",
        "cvc5_qflia_interpolation",
        "vampire_fol",
        "eprover_fol",
        "lean_kernel",
        "coq_rocq_kernel",
        "isabelle_kernel",
    ):
        assert families[optional]["status"] in {"unavailable", "not_selected_unavailable"}
        assert families[optional].get("invented_results") is False
        assert families[optional]["required_for_benchmark"] is False
    assert families["policy_approval"]["status"] == "not_selected"
    assert families["runtime_monitor"]["status"] == "not_selected"
    assert manifest["authority_summary"]["sat_rejects_theorem"] is True
    assert manifest["authority_summary"]["no_weak_authority_allow"] is True
    assert manifest["authority_summary"]["select_job_result_sat_only_cannot_prove"] is True

    assert "QF_BOOL" in text
    assert "satisfiability" in text
    assert "theorem" in text.lower()
    assert "unavailable" in text.lower()
    assert "not a scored A4" in text or "not a scored A4 benchmark run" in text
    assert "Z3" in text and "cvc5" in text

    for name in ("z3", "cvc5", "vampire", "eprover", "lean", "coqc", "isabelle"):
        assert shutil.which(name) is None, f"unexpected {name} on PATH"

    print("LA-010 qualification validation: PASS")
    print(f"jobs={len(jobs)} families={len(families)} selected={success['outcome']}/{counter['outcome']}")
    print("authority rejects SAT-only/policy/simulated; native SMT/ATP/kernels unavailable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
