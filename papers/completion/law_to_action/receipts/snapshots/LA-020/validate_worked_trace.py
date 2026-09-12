#!/usr/bin/python3.12
"""Validate LA-020 source-to-effect trace against retained snapshot evidence."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
LIVE = ROOT / "papers" / "completion" / "law_to_action"
SNAP = Path(__file__).resolve().parent
STUB_CID = "bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi"
ACCEPTANCE = [
    "Each illustrated transition links to actual raw evidence under one run/case identity.",
    "Trace contains at least permitted useful work and prevented forbidden effects.",
    "Figure/table does not use a fabricated signature/proof receipt or pretend a conceptual step ran.",
]


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit("LA-020 validation failed: " + message)


def pdf_text(path: Path) -> str:
    data = path.read_bytes()
    require(data.startswith(b"%PDF"), f"{path} is not a PDF")
    chunks = []
    for part in data.split(b"stream"):
        try:
            chunks.append(part.decode("latin-1", "ignore"))
        except Exception:
            continue
    text = "\n".join(chunks)
    # Unescape simple PDF string literals.
    return text.replace("\\(", "(").replace("\\)", ")").replace("\\\\", "\\")


def main() -> int:
    live_json = LIVE / "results" / "worked_trace" / "trace.json"
    live_md = LIVE / "results" / "worked_trace" / "trace.md"
    live_pdf = LIVE / "results" / "figures" / "source_to_effect_trace.pdf"
    snap_json = SNAP / "outputs" / "results" / "worked_trace" / "trace.json"
    snap_md = SNAP / "outputs" / "results" / "worked_trace" / "trace.md"
    snap_pdf = SNAP / "outputs" / "results" / "figures" / "source_to_effect_trace.pdf"
    for path in (live_json, live_md, live_pdf, snap_json, snap_md, snap_pdf):
        require(path.is_file(), f"missing {path}")
        if path.suffix == ".pdf":
            require(live_pdf.read_bytes() == snap_pdf.read_bytes(), "live/snapshot PDF mismatch")
            try:
                live_pdf.read_bytes().decode("ascii")
            except UnicodeDecodeError as exc:
                raise SystemExit("LA-020 validation failed: PDF is not ASCII text and cannot be snapshot-admitted") from exc
        elif path in {live_json, live_md}:
            counterpart = snap_json if path == live_json else snap_md
            require(path.read_bytes() == counterpart.read_bytes(), f"live/snapshot mismatch: {path.name}")

    payload = load_json(live_json)
    require(payload.get("schema") == "law-to-action-worked-source-to-effect-trace/v1", "trace schema mismatch")
    require(payload.get("task") == "LA-020", "trace task mismatch")
    require(payload.get("replay_matches_la015") is True, "replay was not confirmed against LA-015")
    require(payload.get("theorem_proof") is False, "trace must not claim theorem_proof")
    require(payload.get("fabricated_signature") is False, "trace must not claim a fabricated signature")
    require(payload.get("independent_human_gold") is False, "trace must not claim independent human gold")
    require(payload.get("generated_program_count") == 0, "generated programs must remain zero")

    run = payload["run_identity"]
    require(run["source_run"] == "LA-015", "run identity is not LA-015")
    require(run["seed"] == 104729, "seed is not the frozen LA-015 seed")
    require(run["arm_id"] == "A4", "illustrated arm is not A4")
    require(run["implementation_revision"], "missing implementation revision")

    permitted = payload["illustrated"]["permitted_useful_work"]
    require(permitted["useful_work"] is True, "permitted useful work is missing")
    require(permitted["decision"] == "allow", "permitted case was not allowed")
    require(permitted["observed_effect_count"] == 1, "permitted case did not record one useful effect")
    require(permitted["observed_forbidden_effect"] is False, "permitted case recorded a forbidden effect")
    require(permitted["population"] == "skill", "permitted walkthrough is not a skill export case")
    require(permitted["mutation"] == "none", "permitted walkthrough is not the unmutated control")

    steps = payload["twelve_steps"]
    require(len(steps) == 12, f"expected 12 steps, found {len(steps)}")
    require([step["step"] for step in steps] == list(range(1, 13)), "steps are not 1..12")
    ran = [step for step in steps if step["status"] == "ran"]
    require(len(ran) >= 8, "too few executed steps")
    for step in steps:
        require(step["attempt_id"] == permitted["attempt_id"], f"step {step['step']} is not under the permitted attempt")
        require(step["case_id"] == permitted["case_id"], f"step {step['step']} is not under the permitted case")
        require(step["run_identity"]["attempt_id"] == permitted["attempt_id"], "step run identity drifted")
        require(step["evidence"], f"step {step['step']} has no evidence")
        for item in step["evidence"]:
            path = ROOT / item["path"]
            require(path.is_file(), f"missing evidence {item['path']}")
            require(str(path.relative_to(ROOT)).startswith("papers/completion/law_to_action/receipts/snapshots/LA-020/"), "evidence is outside the LA-020 snapshot")

    absent = payload["absent_or_narrowed"]
    absent_text = json.dumps(absent).lower()
    require("generated" in absent_text, "generated-code absence is not labeled")
    require("theorem_proof" in absent_text, "theorem_proof absence is not labeled")
    require("human gold" in absent_text or "independent human" in absent_text, "human-gold absence is not labeled")

    variants = payload["illustrated"]["variants"]
    kinds = [row["kind"] for row in variants]
    require(kinds == ["rejected_recipient", "undeclared_effect", "replay"], f"unexpected variants {kinds}")
    prevented = 0
    for variant in variants:
        forbidden = variant["forbidden"]
        allowed = variant["allowed"]
        require(allowed["useful_work"] is True, f"{variant['kind']} control lost useful work")
        require(allowed["observed_effect_count"] == 1, f"{variant['kind']} control had no effect")
        require(forbidden["decision"] == "deny", f"{variant['kind']} was not denied")
        require(forbidden["observed_effect_count"] == 0, f"{variant['kind']} leaked an effect")
        require(forbidden["observed_forbidden_effect"] is False, f"{variant['kind']} recorded a forbidden effect")
        require(forbidden["useful_work"] is False, f"{variant['kind']} was scored as useful work")
        stem = forbidden["attempt_id"].replace(":", "_")
        detail_path = SNAP / "traces" / "attempts" / f"{stem}.json"
        require(detail_path.is_file(), f"missing detailed replay {detail_path}")
        detail = load_json(detail_path)
        require(detail["attempt_id"] == forbidden["attempt_id"], "detailed replay identity mismatch")
        require(detail["decision"] == "deny", "detailed replay did not deny the forbidden variant")
        require(detail.get("sat", {}).get("theorem_proof") is False, "SAT marked theorem_proof")
        require(detail.get("ucan", {}).get("fabricated_signature") is False, "UCAN marked fabricated")
        require(detail.get("receipt", {}).get("selected_evidence_cids_not_published_proof") in {True, None} or detail.get("receipt", {}).get("kind") != "published_proof", "receipt pretends to be a published proof")
        prevented += 1
        la015_row = load_json(SNAP / "evidence" / "la015_selected.json")[forbidden["attempt_id"]]
        require(la015_row["decision"] == "deny", "LA-015 compact row is not a denial")
        require(la015_row["observed_effect_count"] == 0, "LA-015 compact row leaked an effect")
    require(prevented == 3, "expected three prevented forbidden variants")

    selected = load_json(SNAP / "evidence" / "la015_selected.json")
    for attempt_id, detailed_name in [(permitted["attempt_id"], permitted["attempt_id"].replace(":", "_"))]:
        detail = load_json(SNAP / "traces" / "attempts" / f"{detailed_name}.json")
        original = selected[attempt_id]
        for field in ("decision", "handler_calls", "observed_effect_count", "useful_work", "observed_forbidden_effect", "terminal_outcome"):
            require(original.get(field) == detail.get(field), f"{attempt_id} {field} replay mismatch")
        require(detail.get("sat", {}).get("authority_kind") == "satisfiability", "SAT authority is not satisfiability")
        require(detail.get("ucan", {}).get("crypto") == "real-ed25519", "UCAN crypto is not real Ed25519")
        require(detail.get("ucan", {}).get("signature_present") is True, "real UCAN signature was not retained")
        require(detail.get("receipt", {}).get("selected_evidence_cids_not_published_proof") is True, "stub CID was not labeled")
        require(detail.get("enforce", {}).get("mode") == "enforce", "ENFORCE mode missing")
        require(detail.get("handler", {}).get("arbitrary_generated_source_execution") is False, "handler claimed generated-source execution")

    md = live_md.read_text(encoding="utf-8")
    require(permitted["attempt_id"] in md, "markdown is missing the permitted attempt")
    require("theorem_proof" in md.lower() or "satisfiability" in md.lower(), "markdown does not scope SAT authority")
    require("rejected_recipient" in md and "undeclared_effect" in md and "replay" in md, "markdown is missing variants")
    for step in steps:
        require(step["name"].split(";")[0][:20] in md or str(step["step"]) in md, f"markdown missing step {step['step']}")

    rendered = pdf_text(live_pdf)
    require("Source-to-effect trace" in rendered, "PDF title missing")
    require(permitted["attempt_id"] in rendered, "PDF missing permitted attempt identity")
    require("useful_work=True" in rendered or "Useful" in rendered, "PDF missing useful-work column")
    require("satisfiability" in rendered, "PDF missing SAT authority label")
    require("theorem_proof" in rendered, "PDF missing theorem_proof non-claim")
    require("fabricated" in rendered.lower(), "PDF missing fabricated-signature non-claim")
    require("Generated-code" in rendered or "generated" in rendered.lower(), "PDF missing generated-code absence")
    require(STUB_CID not in rendered.replace("not-proof", ""), "PDF must not present the harness stub CID as a proof")
    # The stub CID may appear only if explicitly labeled not-proof; it should not appear unlabeled.
    if STUB_CID in rendered:
        require("not a published proof" in rendered.lower() or "not-proof" in rendered.lower() or "constants" in rendered.lower(), "stub CID appears without a not-proof label")
    for variant in variants:
        require(variant["forbidden"]["attempt_id"] in rendered, f"PDF missing {variant['kind']} identity")

    json_text = json.dumps(payload)
    require(json_text.count("theorem_proof") >= 1, "trace does not mention theorem_proof")
    require('"theorem_proof": true' not in json_text.lower(), "trace contains theorem_proof true")
    require(STUB_CID not in json.dumps(payload["illustrated"]), "stub CID used as illustrated proof")

    print(
        json.dumps(
            {
                "task": "LA-020",
                "status": "ok",
                "acceptance": ACCEPTANCE,
                "permitted_attempt_id": permitted["attempt_id"],
                "steps": len(steps),
                "ran_steps": len(ran),
                "variants_prevented": prevented,
                "useful_work": True,
                "forbidden_effects_prevented": True,
                "theorem_proof": False,
                "fabricated_signature": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
