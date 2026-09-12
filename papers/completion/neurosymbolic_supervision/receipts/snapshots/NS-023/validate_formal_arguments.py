#!/usr/bin/env python3
"""Structural audit for NS-023 formal-argument restatement and gate map.

Stdlib only. This program does not invoke a prover, import accelerate
packages, run pytest, or treat snapshot presence as a scientific theorem.
It checks that the restated arguments have precise scope/premises/conclusions,
that implementation evidence is not used to infer untested closures, and that
Algorithm 1 is labeled executed composition only on the integrated witness.
"""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys


ROOT = Path(__file__).resolve().parents[6]
PAPER = ROOT / "papers/completion/neurosymbolic_supervision"
AUDIT = PAPER / "audit"
MANUSCRIPT = PAPER / "manuscript"
QUAL = PAPER / "qualification"
SNAPSHOT = PAPER / "receipts/snapshots/NS-023"
EXTRACT = PAPER / "paper_extracted.txt"
WITNESS = QUAL / "end_to_end_witness.json"

CURRENT = {
    "formal_argument_review.md": AUDIT / "formal_argument_review.md",
    "assumption_gate_map.json": AUDIT / "assumption_gate_map.json",
    "formal_arguments.tex": MANUSCRIPT / "formal_arguments.tex",
}

REQUIRED_STATEMENTS = ("FA-EQ2", "FA-I31", "FA-I32", "FA-I33", "FA-ALG1")
REQUIRED_ASSUMPTIONS = (
    "A-INITIAL-ROOT",
    "A-COMPLETE-MANIFEST",
    "A-CHECKER",
    "A-TRANSLATION",
    "A-CURRENT-PARENT",
    "A-EXCLUSIVE-PUBLICATION",
    "A-PROTECTED-AUTHORITY",
    "A-DETERMINISTIC-PROJECTION",
    "A-EXACT-INPUT",
    "A-TRUSTED-EFFECT",
    "A-UNKNOWN-SPEC",
    "A-INCONSISTENT-SPEC",
    "A-INCOMPLETE-PROJECTION",
    "A-UNIVERSAL-DEPENDENCY-CLOSURE",
    "A-COLD-ORACLE",
    "A-SOLE-PUBLICATION-PATH",
    "A-NATIVE-PROOF",
    "A-COMPOSITION-EDGE",
    "A-WORLD-PROCEDURE",
)
ALLOWED_DISPOSITIONS = {
    "tested_premise",
    "trusted_limitation",
    "undischarged",
    "unavailable",
    "fail_closed_not_completeness",
}
MUST_NOT_BE_TESTED = {
    "A-TRUSTED-EFFECT",
    "A-UNIVERSAL-DEPENDENCY-CLOSURE",
    "A-COLD-ORACLE",
    "A-UNKNOWN-SPEC",
    "A-INCONSISTENT-SPEC",
    "A-INCOMPLETE-PROJECTION",
    "A-NATIVE-PROOF",
    "A-COMPOSITION-EDGE",
    "A-WORLD-PROCEDURE",
}
MUST_BE_UNDISCHARGED = {
    "A-UNKNOWN-SPEC",
    "A-INCONSISTENT-SPEC",
    "A-INCOMPLETE-PROJECTION",
    "A-UNIVERSAL-DEPENDENCY-CLOSURE",
    "A-COLD-ORACLE",
}
MUST_BE_UNAVAILABLE = {"A-NATIVE-PROOF", "A-COMPOSITION-EDGE", "A-WORLD-PROCEDURE"}
MUST_BE_TRUSTED = {"A-TRUSTED-EFFECT", "A-INITIAL-ROOT", "A-SOLE-PUBLICATION-PATH"}
FILE_DIGESTS = {
    "papers/completion/neurosymbolic_supervision/paper_extracted.txt":
        "809af88bfd4e8f78fc7fbc7c067dc5d41392c6c2d4aaf75ec02ec813036a23a4",
    "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/incremental_sealing/admission.py":
        "16fcc43f52f41641abf297e36e0850e87394fdcfac2c9c0807ada19e4cd9cb4b",
    "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/incremental_sealing/sealer.py":
        "9618561ddda1d53b9368ea220ceeff13c7149986d8d49641b78e6623a3a22fed",
    "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/semantic_state/durable_state.py":
        "e718a115671f7d84fc7f5c693c8ef03d4216465d71e79fad04adf2442a277a9f",
    "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/test_proof_cache.py":
        "4c5977b0910f381f3fc85e5e370825043c7166ced5fffcd4868290e67d332883",
    "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/pre_implementation_kernel.py":
        "681183a1096f76a6d7e06cd703792aa1faacc1f90644e387fbdeea890890413c",
    "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/control/authorization_logic.py":
        "455104fb4c968414c8542d186d8d2594742c2e7c2b8f5c70c8293d5116f44ff1",
    "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/logic_translation_validation.py":
        "6eebde25647840e696d2bcd204be015b7b5d1302d29bc8444f2b583199279f62",
}
SEALED_BINARIES = ("z3", "lean", "coqc", "cvc5", "souffle")
FORBIDDEN_TEX = (
    "machine-checked theorem",
    "proves arbitrary python",
    "universal python",
    "exactly-once side effects",
    "universal dependency closure is established",
    "algorithm 1 ran as a complete",
    "full loop executed",
    "cold-oracle agreement is established",
)
FORBIDDEN_IDENTIFYING = (
    "github.com",
    "overleaf.com",
    "/home/barberb",
    "hallucinate_app",
)
REVIEW_PHRASES = (
    "unmachine-checked",
    "scope",
    "premises",
    "conclusion",
    "independent argument",
    "external side-effect atomicity",
    "universal dependency closure",
    "executed composition",
    "intended composition",
    "deny-all",
    "incomplete",
    "unknown",
    "ns-011",
    "ns-013",
    "three acceptance questions",
)
TEX_PHRASES = (
    "unmachine-checked",
    "conditional",
    "intended composition",
    "executed composition",
    "behavioral claim",
    "action permission",
    "publication",
    "incomplete",
    "unknown",
    "external side-effect",
    "universal dependency closure",
)
EXECUTED_ALLOWED_LINES = {4, 7, 9, 11, 13, 14, 16}


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def fail(message: str) -> None:
    raise AssertionError(message)


def folded(text: str) -> str:
    return text.replace("’", "'").replace("Θ", "theta").lower()


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def check_source_digests() -> None:
    for relative, expected in FILE_DIGESTS.items():
        path = ROOT / relative
        if not path.is_file():
            fail(f"missing inspected source: {relative}")
        if digest(path) != expected:
            fail(f"source digest drifted: {relative}")


def sealed_prover_status() -> dict[str, str | None]:
    status: dict[str, str | None] = {}
    for name in SEALED_BINARIES:
        found = shutil.which(name)
        status[name] = found
        if found:
            fail(f"sealed PATH unexpectedly contains prover {name} at {found}")
    return status


def check_ns011_absent(data: dict) -> None:
    cold = QUAL / "cold_oracle_results.jsonl"
    receipt = PAPER / "receipts/NS-011.json"
    if cold.is_file() or receipt.is_file():
        fail("NS-011 artifacts appeared; this audit assumed they were absent")
    if data.get("ns011_cold_oracle_present") is not False:
        fail("gate map must record NS-011 cold oracle absent")
    cold_assump = next(a for a in data["assumptions"] if a["id"] == "A-COLD-ORACLE")
    if cold_assump["disposition"] != "undischarged":
        fail("A-COLD-ORACLE must remain undischarged")
    if cold_assump.get("qualification", {}).get("evidence"):
        fail("A-COLD-ORACLE must not cite fabricated cold-oracle evidence")


def check_map(data: dict, tex: str, review: str) -> None:
    if data.get("schema") != "neurosymbolic-supervision/assumption-gate-map@1":
        fail("assumption_gate_map schema mismatch")
    if data.get("task_id") != "NS-023":
        fail("assumption_gate_map task_id mismatch")
    machine = data.get("machine_check") or {}
    if machine.get("status") != "unmachine_checked":
        fail("machine_check.status must be unmachine_checked")
    if machine.get("universal_python_proof_work_initiated") is not False:
        fail("universal Python proof work must not be initiated")
    if machine.get("independently_checked_proof_artifact") is not False:
        fail("no independently checked proof artifact may be claimed")
    if machine.get("sealed_path") != "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin":
        fail("machine_check must record the sealed PATH")
    provers = machine.get("provers_in_sealed_path") or {}
    for name in SEALED_BINARIES:
        if provers.get(name) is not None:
            fail(f"gate map claims prover {name} is available")

    statements = data.get("statements")
    if not isinstance(statements, list):
        fail("statements must be a list")
    by_stmt = {}
    for item in statements:
        if not isinstance(item, dict) or item.get("id") in by_stmt:
            fail("invalid or duplicate statement")
        sid = item["id"]
        by_stmt[sid] = item
        for field in ("name", "location", "kind", "scope", "premises", "conclusion", "argument", "validity"):
            if not item.get(field):
                fail(f"{sid} missing {field}")
        if item.get("machine_checked") is not False:
            fail(f"{sid} must be unmachine-checked")
        if not isinstance(item.get("premises"), list) or not item["premises"]:
            fail(f"{sid} premises must be a nonempty list")
        if not isinstance(item.get("not_established"), list) or not item["not_established"]:
            fail(f"{sid} must list what it does not establish")
        validity = item["validity"]
        if not str(validity).startswith("valid_"):
            fail(f"{sid} argument is not recorded as valid")
    missing_stmt = [sid for sid in REQUIRED_STATEMENTS if sid not in by_stmt]
    if missing_stmt:
        fail(f"missing statements: {missing_stmt}")
    if by_stmt["FA-ALG1"].get("full_loop_executed") is not False:
        fail("FA-ALG1 must not claim the full loop executed")
    if by_stmt["FA-I32"]["kind"] != "proof_obligation":
        fail("FA-I32 must remain a proof obligation")
    if "universal" in by_stmt["FA-I31"]["conclusion"].lower() and "python" in by_stmt["FA-I31"]["conclusion"].lower():
        fail("FA-I31 conclusion overreaches")

    assumptions = data.get("assumptions")
    if not isinstance(assumptions, list):
        fail("assumptions must be a list")
    by_a = {}
    for item in assumptions:
        if not isinstance(item, dict) or item.get("id") in by_a:
            fail("invalid or duplicate assumption")
        aid = item["id"]
        by_a[aid] = item
        if item.get("disposition") not in ALLOWED_DISPOSITIONS:
            fail(f"{aid} has invalid disposition {item.get('disposition')}")
        if item.get("cannot_silently_discharge") is not True:
            fail(f"{aid} must not be silently dischargeable")
        if not item.get("statement") or not item.get("required_by"):
            fail(f"{aid} missing statement or required_by")
        if not item.get("limitation"):
            fail(f"{aid} missing limitation")
        if aid in MUST_NOT_BE_TESTED and item["disposition"] == "tested_premise":
            fail(f"{aid} cannot be treated as a tested premise")
    missing_a = [aid for aid in REQUIRED_ASSUMPTIONS if aid not in by_a]
    if missing_a:
        fail(f"missing assumptions: {missing_a}")
    for aid in MUST_BE_UNDISCHARGED:
        if by_a[aid]["disposition"] != "undischarged":
            fail(f"{aid} must be undischarged, found {by_a[aid]['disposition']}")
    for aid in MUST_BE_UNAVAILABLE:
        if by_a[aid]["disposition"] != "unavailable":
            fail(f"{aid} must be unavailable")
    for aid in MUST_BE_TRUSTED:
        if by_a[aid]["disposition"] != "trusted_limitation":
            fail(f"{aid} must be a trusted limitation")
    if by_a["A-DETERMINISTIC-PROJECTION"]["disposition"] != "fail_closed_not_completeness":
        fail("A-DETERMINISTIC-PROJECTION must be fail_closed_not_completeness")
    if by_a["A-COMPLETE-MANIFEST"]["disposition"] != "tested_premise":
        fail("A-COMPLETE-MANIFEST should be a tested premise on the sealer")
    if by_a["A-TRANSLATION"]["disposition"] != "tested_premise":
        fail("A-TRANSLATION should be a tested premise on NS-009")

    cited = {aid for stmt in statements for aid in stmt["premises"]}
    unknown_cite = sorted(cited - set(by_a))
    if unknown_cite:
        fail(f"statements cite unknown assumptions: {unknown_cite}")

    non = data.get("non_inferences") or {}
    if non.get("external_side_effect_atomicity") != "not_inferred":
        fail("external side-effect atomicity must not be inferred")
    if non.get("universal_dependency_closure") != "not_inferred":
        fail("universal dependency closure must not be inferred")
    if non.get("universal_python_correctness") != "not_inferred":
        fail("universal Python correctness must not be inferred")
    for flag in (
        "unknown_specifications_discharged",
        "inconsistent_specifications_discharged",
        "incomplete_projections_discharged",
        "cold_oracle_agreement_discharged",
        "native_proof_usable",
        "algorithm1_full_loop_executed",
        "matched_ad_experiment",
    ):
        if non.get(flag) is not False:
            fail(f"non_inference flag {flag} must be false")

    questions = data.get("three_questions") or {}
    for name in ("behavioral_claim", "action_permission", "publication"):
        if name not in questions:
            fail(f"missing three-question entry {name}")
        if "does_not_answer" not in questions[name]:
            fail(f"{name} must record what it does not answer")

    alg = data.get("algorithm1") or {}
    if alg.get("label") != "intended_composition_with_partial_executed_witness":
        fail("Algorithm 1 label mismatch")
    if alg.get("full_loop_executed") is not False:
        fail("Algorithm 1 full_loop_executed must be false")
    if alg.get("live_ad_experiment") is not False:
        fail("Algorithm 1 must not be a live A-D experiment")
    if alg.get("witness_task") != "NS-013":
        fail("executed composition must cite NS-013")
    executed = alg.get("executed_composition")
    if not isinstance(executed, list) or not executed:
        fail("executed_composition mapping missing")
    for step in executed:
        if step.get("label") != "executed_composition":
            fail("executed mapping has unlabeled step")
        line = step.get("algorithm_line")
        lines = line if isinstance(line, list) else [line]
        for number in lines:
            if number not in EXECUTED_ALLOWED_LINES:
                fail(f"line {number} is not supported as executed composition")
    intended = alg.get("intended_only")
    if not isinstance(intended, list) or len(intended) < 6:
        fail("intended_only mapping is too thin")

    if data.get("manuscript_application") != "NS-022":
        fail("manuscript application must remain NS-022")

    review_l = folded(review)
    tex_l = folded(tex)
    if "unmachine-checked" not in review_l:
        fail("review does not keep sketches unmachine-checked")
    if by_stmt["FA-EQ2"]["id"] not in review and "fa-eq2" not in review_l:
        fail("review does not independently cover FA-EQ2")


def check_review(text: str) -> None:
    lowered = folded(text)
    for phrase in REVIEW_PHRASES:
        if phrase not in lowered:
            fail(f"formal_argument_review.md missing {phrase}")
    if "independently of generated" not in lowered and "independent argument" not in lowered:
        fail("review is not labeled independent of generated prose")
    if "not inferred" not in lowered and "are not inferred" not in lowered:
        fail("review does not forbid untested inferences")
    if "universal-python proof work" not in lowered and "universal python proof work" not in lowered:
        fail("review must record that universal-Python proof work was not started")
    for bad in ("machine-checked proof of equation 2", "z3 proved", "lean proved"):
        if bad in lowered:
            fail(f"review claims a machine-checked result: {bad}")


def check_tex(text: str) -> None:
    lowered = folded(text)
    for phrase in TEX_PHRASES:
        if phrase not in lowered:
            fail(f"formal_arguments.tex missing {phrase}")
    for bad in FORBIDDEN_TEX:
        if bad in lowered:
            fail(f"formal_arguments.tex contains forbidden claim: {bad}")
    for bad in FORBIDDEN_IDENTIFYING:
        if bad in lowered:
            fail(f"formal_arguments.tex contains identifying token {bad}")
    if "ipfs_accelerate_py" in text or "ipfs_datasets_py" in text:
        fail("manuscript fragment must not embed repository package paths")
    if "\\tag{2$'$}" not in text and r"\tag{2'$}" not in text:
        if r"\tag{2" not in text:
            fail("formal_arguments.tex does not restate Equation 2")
    if "FA-I31" not in text or "FA-I32" not in text or "FA-ALG1" not in text:
        fail("formal_arguments.tex missing statement labels")
    if "NS-022" not in text:
        fail("fragment must assign manuscript integration to NS-022")


def check_witness_alignment(data: dict) -> None:
    if not WITNESS.is_file():
        fail("NS-013 end_to_end_witness.json is required for composition labels")
    witness = load_json(WITNESS)
    if witness.get("schema") != "neurosymbolic-supervision/end-to-end-witness@1":
        fail("unexpected NS-013 witness schema")
    if witness.get("live_ad_experiment") is not False:
        fail("NS-013 witness is unexpectedly a live A-D experiment")
    if witness.get("simulation_counted_as_success") is not False:
        fail("NS-013 witness counted simulation as success")
    steps = set(witness.get("steps_completed") or [])
    required = {
        "plan_bounded_repair",
        "choose_reasoning_route",
        "validate_candidate",
        "reuse_narrowly",
        "seal_and_publish",
        "incomplete_cannot_complete",
        "simulation_labeled_qualification",
    }
    missing = sorted(required - steps)
    if missing:
        fail(f"NS-013 witness missing steps required for executed composition: {missing}")
    executed_steps = {item["witness_step"] for item in data["algorithm1"]["executed_composition"]}
    extra = executed_steps - steps
    if extra:
        fail(f"gate map labels executed steps absent from NS-013 witness: {sorted(extra)}")
    if data["algorithm1"].get("witness_id") != witness.get("ids", {}).get("task_cid") and data[
        "algorithm1"
    ].get("witness_id") != witness.get("task", {}).get("identity"):
        # Accept either ids.task_cid or task.identity.
        task_cid = (witness.get("ids") or {}).get("task_cid")
        identity = (witness.get("task") or {}).get("identity")
        if data["algorithm1"].get("witness_id") not in {task_cid, identity}:
            fail("Algorithm 1 witness_id does not match NS-013 task identity")


def check_qualification_presence() -> None:
    required = (
        QUAL / "logic_report.md",
        QUAL / "sealer_recovery_report.md",
        QUAL / "reuse_adapter_report.md",
        QUAL / "provider_gate_report.md",
        QUAL / "end_to_end_case_study.md",
        QUAL / "native_scope_decision.md",
        QUAL / "extensions_report.md",
        EXTRACT,
    )
    for path in required:
        if not path.is_file():
            fail(f"missing qualification/source record: {path.relative_to(ROOT)}")


def check_snapshots() -> None:
    for name, current in CURRENT.items():
        snap = SNAPSHOT / name
        if not snap.is_file():
            fail(f"missing snapshot {snap}")
        if digest(current) != digest(snap):
            fail(f"current {name} differs from snapshot")


def main() -> None:
    check_source_digests()
    prover_status = sealed_prover_status()
    check_qualification_presence()
    outputs = {name: path.read_text(encoding="utf-8") for name, path in CURRENT.items()}
    data = json.loads(outputs["assumption_gate_map.json"])
    check_map(data, outputs["formal_arguments.tex"], outputs["formal_argument_review.md"])
    check_review(outputs["formal_argument_review.md"])
    check_tex(outputs["formal_arguments.tex"])
    check_ns011_absent(data)
    check_witness_alignment(data)
    check_snapshots()
    print("NS-023 formal-argument audit: OK")
    print("statements=5; assumptions=19; machine_checked=false; full_loop_executed=false")
    print("external_side_effect_atomicity=not_inferred; universal_dependency_closure=not_inferred")
    print("unknown_incomplete_undischarged=true; ns011_cold_oracle=absent")
    print("provers=" + json.dumps(prover_status, sort_keys=True))
    print("manuscript_not_edited=NS-022")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as exc:
        print(f"NS-023 validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
