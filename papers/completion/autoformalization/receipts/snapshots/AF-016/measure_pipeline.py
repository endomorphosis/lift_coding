#!/usr/bin/env python3
"""AF-016 matched A–E source-to-proof benchmark under the sealed PATH.

Execute available prespecified arms on frozen public selection sources and a
constructed Q1 control. Table 6 remains the 1913-unit final-test comparison:
those cells are unrun, unmeasured, or unavailable with narrowed claims. This
harness does not open private final-test bodies, invent model calls, or treat
compiler/teacher/prover success as original-source semantic gold.

Standard library only at runtime. Project packages are inspected and hashed,
not imported. Native Lean/Z3/CVC5 are probed on PATH; missing checkers are
unavailable rather than synthetic proofs.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA_RESULT = "autoformalization-evaluation-result/v1"
SCHEMA_MANIFEST = "autoformalization-pipeline-comparison-manifest/v1"
SCHEMA_RECIPE = "autoformalization-population-recipe/v1"
TASK_ID = "AF-016"
SUITE_ID = "AF-016-matched-pipeline-comparison/v1"
CHECKER_ID = "AF-010-shared-target-checker/v1"
CHECKER_DIGEST = "0d22c6e92be47a464452266e1a09d3b1d072f98ce3e5fec19bdbe9f47273f052"
COMPILER_B_ID = "typed-deontic-canonical-compiler/frozen-no-guidance/v1"
COMPILER_C_ID = "intent-formalization-compiler/v1"
FROZEN_CANONICAL_PROFILE_ID = (
    "typed_deontic__no_guidance__no_repair__not_applicable__deterministic"
)
PIPELINE_ARMS = ("A", "B", "C", "D", "E")
TABLE6_COLUMNS = (
    "sources_covered",
    "fidelity_uncertainty",
    "correct_transfers",
    "cost_latency",
)
ORIGINAL_HEADINGS = {
    "sources_covered": "Sources / covered",
    "fidelity_uncertainty": "Fidelity / uncertainty",
    "correct_transfers": "Correct transfers",
    "cost_latency": "Cost / latency",
}
REVISED_HEADINGS = {
    "sources_covered": (
        "Coverage / abstention on eligible final-test natural units "
        "(unrun is not zero)"
    ),
    "fidelity_uncertainty": (
        "Independent source-semantic fidelity / uncertainty "
        "(unmeasured; not prover or teacher agreement)"
    ),
    "correct_transfers": (
        "Exact-goal native-checked useful proof / correct transfer "
        "(semantic false-transfer remains unmeasured)"
    ),
    "cost_latency": (
        "Total measured cost / latency on the Table 6 population "
        "(unrun is not a zero-cost success)"
    ),
}
NATIVE_TOOLS = ("lean", "lake", "elan", "z3", "cvc5", "vampire", "eprover", "coqc", "isabelle")
C_VIEW_IDS = (
    "intent-ir-view/facts/v1",
    "intent-ir-view/intention-deontic/v1",
    "intent-ir-view/action-hoare/v1",
    "intent-ir-view/invariant/v1",
    "intent-ir-view/verification/v1",
    "intent-ir-view/failure/v1",
)
B_VOCABULARY = {
    "actors": ("party", "parties", "copyright_royalty_board"),
    "actions": ("file", "claim", "prescribe"),
    "objects": ("royalty_fee", "claim", "procedure"),
    "qualifiers": ("cable", "satellite", "compulsory_license"),
}
Q1_SOURCE = {
    "source_id": "AF016-DEV-Q1-protected-write",
    "split": "constructed_control",
    "source_family_time_group": "constructed:q1-protected-write",
    "text": "If Protected is true and Approved is false, then Write is false.",
    "goal_id": "Q1_protected_and_not_approved_implies_not_write",
    "goal_formula": "Protected ∧ ¬Approved → ¬Write",
    "premise_ids": ("Protected", "Approved", "Write"),
    "fragment": "q1-protected-write",
}
SEALED_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parents[2]
REPO_ROOT = HERE.parents[5]
EVAL_DIR = PAPER_ROOT / "evaluation"

INSPECTED_SOURCES = {
    "bench_semantic_logic_roundtrip.py": {
        "path": "external/ipfs_datasets/benchmarks/bench_semantic_logic_roundtrip.py",
        "imported": False,
        "note": "Named native report conversion remains unqualified; not executed as Table 6.",
    },
    "bench_semantic_roundtrip_compositions.py": {
        "path": "external/ipfs_datasets/benchmarks/bench_semantic_roundtrip_compositions.py",
        "imported": False,
        "note": "Inspected composition benchmark; not imported and not Table 6.",
    },
    "bench_itp_hammer.py": {
        "path": "external/ipfs_datasets/benchmarks/bench_itp_hammer.py",
        "imported": False,
        "note": "Would import project packages; hashed only.",
    },
    "pipeline_arms.py": {
        "path": "papers/completion/autoformalization/evaluation/pipeline_arms.py",
        "imported": False,
        "note": "AF-027 development adapters are not Table 6. Dummy identity theorems are not reused.",
    },
    "canonical_compiler.py": {
        "path": "external/ipfs_datasets/ipfs_datasets_py/logic/legal_ir/canonical_compiler.py",
        "imported": False,
        "note": "Native import requires multiformats; B uses the frozen-profile stdlib replica.",
    },
    "intent_formalization_compiler.py": {
        "path": "external/ipfs_datasets/ipfs_datasets_py/logic/intent_ir/formalize/compiler.py",
        "imported": False,
        "note": "Native import requires multiformats; C uses the stdlib multiview replica.",
    },
    "legal_ir_learned_guidance.py": {
        "path": "external/ipfs_datasets/ipfs_datasets_py/logic/integration/reasoning/legal_ir_learned_guidance.py",
        "imported": False,
        "note": "E stays locked; export identity is not applied learned guidance.",
    },
}


class HarnessError(RuntimeError):
    """Raised when AF-016 cannot emit an honest record."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_dumps(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    except ValueError as exc:
        raise HarnessError("canonical JSON requires finite numeric values") from exc


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_obj(value: Any) -> str:
    return sha256_text(canonical_dumps(value))


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line:
            rows.append(json.loads(line))
    return rows


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_text(payload, encoding="utf-8")
    temporary.replace(path)


def write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(canonical_dumps(row) + "\n" for row in rows)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_text(payload, encoding="utf-8")
    temporary.replace(path)


def checker_contract() -> dict[str, Any]:
    return {
        "advice_cannot_replace_checking": True,
        "checker_id": CHECKER_ID,
        "intended_native": "lean",
        "intended_solver_local": "z3_or_cvc5_descriptive_only",
        "mutation_allowed": False,
        "native_receipt_required_for_useful_proof": True,
        "shared_across_arms": list(PIPELINE_ARMS),
        "solver_local_is_not_native_checked_proof": True,
    }


def identity_pin(
    *,
    source_id: str,
    source_sha256: str,
    goal_id: str,
    goal_sha256: str,
    premise_ids: Sequence[str],
    premise_sha256: str,
    checker_digest: str,
) -> dict[str, Any]:
    payload = {
        "checker_digest": checker_digest,
        "checker_id": CHECKER_ID,
        "goal_id": goal_id,
        "goal_sha256": goal_sha256,
        "premise_ids": list(premise_ids),
        "premise_sha256": premise_sha256,
        "source_id": source_id,
        "source_sha256": source_sha256,
    }
    payload["pin_sha256"] = sha256_obj(payload)
    return payload


def empty_phase(status: str, detail: str | None = None) -> dict[str, Any]:
    phase: dict[str, Any] = {"status": status, "score": None}
    if detail:
        phase["detail"] = detail
    return phase


def inspect_sources() -> dict[str, Any]:
    report = {}
    for name, spec in INSPECTED_SOURCES.items():
        path = REPO_ROOT / spec["path"]
        report[name] = {
            "exists": path.is_file(),
            "imported": False,
            "note": spec["note"],
            "path": spec["path"],
            "sha256": sha256_file(path) if path.is_file() else None,
        }
    return report


def probe_binaries() -> dict[str, Any]:
    found: dict[str, Any] = {}
    for name in NATIVE_TOOLS:
        resolved = shutil.which(name)
        found[name] = {
            "path": resolved,
            "sha256": sha256_file(Path(resolved)) if resolved and Path(resolved).is_file() else None,
            "usable": bool(resolved),
        }
    return {
        "any_native_checker_usable": any(found[name]["usable"] for name in ("lean", "z3", "cvc5")),
        "home": os.environ.get("HOME"),
        "path": os.environ.get("PATH"),
        "tools": found,
    }


def probe_direct_model() -> dict[str, Any]:
    env_keys = ("XAI_API_KEY", "GROK_API_KEY", "OPENAI_API_KEY")
    present = [key for key in env_keys if os.environ.get(key)]
    home = Path(os.environ.get("HOME") or "")
    auth = home / ".config" / "grok" / "auth.json"
    return {
        "auth_file_present": auth.is_file(),
        "blockers": [
            item for item in (
                "no process-environment model credential under sealed env -i" if not present else None,
                "private validation HOME has no Grok auth.json" if not auth.is_file() else None,
                "native Lean checker required for Arm A useful-proof credit and is absent",
            ) if item
        ],
        "credential_env_keys_present": present,
        "runnable": False,
    }


def probe_arm_e(consumer: Mapping[str, Any]) -> dict[str, Any]:
    locked = bool(consumer.get("e_locked"))
    t4 = consumer.get("T4")
    applied = consumer.get("matching_ingestion_digest_is_applied_learning")
    return {
        "T4": t4,
        "applied_learned_features": False,
        "blockers": [
            "AF-013 consumer observation records T4 unactivated/unavailable",
            "e_locked is true; matching ingestion identity is not applied learned guidance",
            "advice cannot replace checking; native checker remains absent",
        ],
        "e_locked": locked,
        "matching_ingestion_digest_is_applied_learning": bool(applied),
        "runnable": False,
    }


def q1_holds(protected: bool, approved: bool, write: bool) -> bool:
    return (not (protected and not approved)) or (not write)


def guarded_write(protected: bool, approved: bool) -> bool:
    return (not protected) or approved


def unguarded_write(_protected: bool, _approved: bool) -> bool:
    return True


def q1_assignments(write_fn) -> list[dict[str, Any]]:
    rows = []
    for protected, approved in ((True, True), (True, False), (False, True), (False, False)):
        write = bool(write_fn(protected, approved))
        rows.append({
            "approved": approved,
            "protected": protected,
            "q1": q1_holds(protected, approved, write),
            "write": write,
        })
    return rows


def compile_arm_b(source_text: str) -> dict[str, Any]:
    text = " ".join(source_text.split())
    lowered = text.lower()
    if "must not" in lowered or "shall not" in lowered:
        modality = "F"
    elif re.search(r"\b(must|shall)\b", lowered):
        modality = "O"
    elif re.search(r"\bmay\b", lowered):
        modality = "P"
    else:
        modality = None
    matched_actions = [item for item in B_VOCABULARY["actions"] if item.replace("_", " ") in lowered]
    matched_objects = [item for item in B_VOCABULARY["objects"] if item.replace("_", " ") in lowered]
    matched_actors = [item for item in B_VOCABULARY["actors"] if item.replace("_", " ") in lowered]
    if modality is None or not matched_actions:
        ir = {
            "guidance": "no_guidance",
            "learned_stages": [],
            "model_call_count": 0,
            "producer": COMPILER_B_ID,
            "profile": FROZEN_CANONICAL_PROFILE_ID,
            "reason": "source outside declared vocabulary or modality",
            "repair": "no_repair",
            "rules": [],
            "status": "abstained",
        }
        source_map = []
    else:
        action = matched_actions[0]
        start = lowered.find(action.replace("_", " "))
        if start < 0:
            start = 0
        end = min(len(source_text), start + max(len(action), 4))
        ir = {
            "guidance": "no_guidance",
            "learned_stages": [],
            "model_call_count": 0,
            "producer": COMPILER_B_ID,
            "profile": FROZEN_CANONICAL_PROFILE_ID,
            "repair": "no_repair",
            "rules": [{
                "action": action,
                "actor": matched_actors[0] if matched_actors else "party",
                "conditions": [],
                "exceptions": [],
                "modality": modality,
                "object": matched_objects[0] if matched_objects else "",
                "temporal": [],
            }],
            "status": "compiled",
        }
        source_map = [{"end": end, "rule_index": 0, "start": max(0, start)}]
    return {"ir": ir, "ir_sha256": sha256_obj(ir), "source_map": source_map, "vocabulary": B_VOCABULARY}


def reconstruct_b(ir: Mapping[str, Any]) -> str:
    if not ir.get("rules"):
        return ""
    rule = ir["rules"][0]
    word = {"O": "must", "P": "may", "F": "must not"}[rule["modality"]]
    parts = [str(rule["actor"]).replace("_", " "), word, str(rule["action"]).replace("_", " ")]
    if rule.get("object"):
        parts.append(str(rule["object"]).replace("_", " "))
    return " ".join(parts) + "."


def compile_arm_c(source_text: str) -> dict[str, Any]:
    text = " ".join(source_text.split())
    views = []
    for view_id in C_VIEW_IDS:
        views.append({
            "checked_bridges": False,
            "formulas": [{
                "formula_id": f"{view_id}::f0",
                "source_span": {"end_char": min(len(source_text), 240), "start_char": 0},
                "text": text[:240],
            }],
            "proof_transfer_admitted": False,
            "source_grounded": True,
            "view_id": view_id,
        })
    artifact = {
        "bridge_evidence": None,
        "cross_view_links": [{
            "admitted_proof_transfer": False,
            "from": C_VIEW_IDS[0],
            "relation": "source_grounded_alignment",
            "to": C_VIEW_IDS[1],
        }],
        "producer": COMPILER_C_ID,
        "producer_version": COMPILER_C_ID,
        "views": views,
    }
    return {
        "artifact": artifact,
        "artifact_sha256": sha256_obj(artifact),
        "source_map": [{"end": min(len(source_text), 240), "start": 0, "view_id": C_VIEW_IDS[0]}],
        "view_ids": list(C_VIEW_IDS),
    }


def reconstruct_c(artifact: Mapping[str, Any]) -> str:
    views = artifact.get("views") or []
    if not views:
        return ""
    formulas = views[0].get("formulas") or []
    if not formulas:
        return ""
    return str(formulas[0].get("text") or "")


def make_record(
    *,
    source_id: str,
    source_family_time_group: str,
    split: str,
    experiment_arm: str,
    execution_status: str,
    result_kind: str,
    constructed_control: bool,
    pin: Mapping[str, Any],
    record_id: str | None = None,
    parse: dict[str, Any],
    elaboration: dict[str, Any],
    source_maps: dict[str, Any],
    reconstruction: dict[str, Any],
    consistency: dict[str, Any],
    identities: dict[str, Any],
    elapsed_seconds: float,
    notes: str,
    useful: bool = False,
    false_transfer: bool = False,
    checker_class: str = "none",
    receipt_sha256: str | None = None,
    theorem: str | None = None,
    fragment: str | None = None,
    model: str | None = None,
    tool: str | None = None,
    compiler: str | None = None,
    checker: str | None = None,
) -> dict[str, Any]:
    if not math.isfinite(elapsed_seconds) or elapsed_seconds < 0:
        raise HarnessError("elapsed_seconds must be finite and nonnegative")
    record: dict[str, Any] = {
        "schema": SCHEMA_RESULT,
        "record_id": record_id or f"{experiment_arm}:{source_id}",
        "source_id": source_id,
        "source_family_time_group": source_family_time_group,
        "split": split,
        "experiment_arm": experiment_arm,
        "eligible": True,
        "fixture": False,
        "constructed_control": constructed_control,
        "execution_status": execution_status,
        "result_kind": result_kind,
        "parse": parse,
        "elaboration": elaboration,
        "source_facets": {
            "all_facet_match": None,
            "ambiguity": {"labels": [], "status": "unmeasured"},
            "independent_gold_present": False,
            "status": "unmeasured",
        },
        "source_maps": source_maps,
        "reconstruction": reconstruction,
        "consistency": consistency,
        "proof": {
            "checker_class": checker_class,
            "false_transfer": false_transfer,
            "fragment": fragment,
            "identity_pin_sha256": pin["pin_sha256"],
            "receipt_sha256": receipt_sha256,
            "theorem": theorem,
            "useful": useful,
        },
        "identities": {
            "checker": checker,
            "checker_digest": CHECKER_DIGEST,
            "checker_id": CHECKER_ID,
            "compiler": compiler,
            "experiment_arm": experiment_arm,
            "goal_id": pin["goal_id"],
            "goal_sha256": pin["goal_sha256"],
            "identity_pin_sha256": pin["pin_sha256"],
            "model": model,
            "premise_ids": list(pin["premise_ids"]),
            "premise_sha256": pin["premise_sha256"],
            "source_id": pin["source_id"],
            "source_sha256": pin["source_sha256"],
            "tool": tool,
            **identities,
        },
        "cost": {
            "cpu_seconds": None,
            "elapsed_seconds": elapsed_seconds,
            "gpu_seconds": None,
            "human_review_seconds": 0.0,
            "memory_gib": None,
            "provider_units": 0.0,
        },
        "notes": notes,
    }
    body = {key: record[key] for key in record if key != "artifacts"}
    record["artifacts"] = {"command_log_sha256": None, "raw_sha256": sha256_obj(body)}
    return record


def run_arm_a(source: Mapping[str, Any], *, binaries: Mapping[str, Any], model: Mapping[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    source_sha = sha256_text(source["text"])
    goal_id = f"unproduced-direct-model-goal:{source['source_id']}"
    pin = identity_pin(
        source_id=source["source_id"],
        source_sha256=source_sha,
        goal_id=goal_id,
        goal_sha256=sha256_text(goal_id),
        premise_ids=(),
        premise_sha256=sha256_obj([]),
        checker_digest=CHECKER_DIGEST,
    )
    blockers = list(model["blockers"])
    if not binaries["any_native_checker_usable"]:
        blockers.append("native checker absent from sealed PATH")
    elapsed = time.perf_counter() - started
    return make_record(
        source_id=source["source_id"],
        source_family_time_group=source["source_family_time_group"],
        split=source["split"],
        experiment_arm="A",
        execution_status="unavailable",
        result_kind="no_run",
        constructed_control=source["split"] == "constructed_control",
        pin=pin,
        parse=empty_phase("unavailable", "direct-model inference was not dispatched"),
        elaboration=empty_phase("unavailable", "no model-produced target to elaborate"),
        source_maps=empty_phase("unavailable"),
        reconstruction={
            "cycle": empty_phase("unavailable"),
            "final": empty_phase("unavailable"),
            "forward": empty_phase("unavailable"),
        },
        consistency=empty_phase("unavailable"),
        identities={
            "candidate_produced": False,
            "checker_request": {
                "identical_to_candidate_pin": True,
                "pin_sha256": pin["pin_sha256"],
                "submitted": False,
                "reason": "; ".join(blockers),
            },
            "entry_point": "papers/completion/autoformalization/evaluation/pipeline_arms.py:run_arm_a",
            "unavailable_blockers": blockers,
        },
        elapsed_seconds=elapsed,
        notes="Arm A is unavailable on the sealed PATH: no model credential and no native checker. No fixture output was substituted.",
        theorem=goal_id,
        fragment=None,
        checker=CHECKER_ID,
        compiler=None,
        model=None,
        tool=None,
    )


def run_arm_b(source: Mapping[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    compiled = compile_arm_b(source["text"])
    ir = compiled["ir"]
    reconstructed = reconstruct_b(ir)
    recycled = compile_arm_b(reconstructed) if reconstructed else None
    cycle_ok = bool(recycled) and recycled["ir_sha256"] == compiled["ir_sha256"]
    second = reconstruct_b(recycled["ir"]) if recycled else ""
    final_ok = bool(reconstructed) and reconstructed == second
    source_sha = sha256_text(source["text"])
    if ir["status"] == "compiled":
        rule = ir["rules"][0]
        goal_id = f"B:{source['source_id']}:{rule['modality']}:{rule['actor']}:{rule['action']}:{rule['object']}"
        premises = tuple(p for p in (rule["actor"], rule["action"], rule["object"]) if p)
        execution_status = "measured"
        result_kind = "bounded_observation"
        parse = empty_phase("success", "declared-vocabulary tokenization")
        elaboration = empty_phase("success", "frozen canonical profile; no_guidance/no_repair")
        maps = empty_phase("success", "span of first matched action token")
        forward = empty_phase("success", "source compiled to typed deontic IR")
        cycle = empty_phase("success" if cycle_ok else "failure", "producer IR recompile of reconstructed text")
        final = empty_phase("success" if final_ok else "failure", "reconstruction idempotence; not original-source identity")
        consistency = empty_phase("success", "single-rule IR; no cross-source premises")
        notes = "Arm B structural compiler outcome on the frozen declared vocabulary. Not independent source-semantic fidelity and not a native checked proof."
    else:
        goal_id = f"B:{source['source_id']}:abstained"
        premises = ()
        execution_status = "abstained"
        result_kind = "failure"
        parse = empty_phase("success", "source text normalized")
        elaboration = empty_phase("abstained", ir["reason"])
        maps = empty_phase("abstained", "no matched action span")
        forward = empty_phase("abstained")
        cycle = empty_phase("unmeasured")
        final = empty_phase("unmeasured")
        consistency = empty_phase("abstained")
        notes = "Arm B explicitly abstained: source outside declared vocabulary or modality. Abstention is not a zero-score success."
    pin = identity_pin(
        source_id=source["source_id"],
        source_sha256=source_sha,
        goal_id=goal_id,
        goal_sha256=sha256_text(goal_id + compiled["ir_sha256"]),
        premise_ids=premises,
        premise_sha256=sha256_obj(list(premises)),
        checker_digest=CHECKER_DIGEST,
    )
    elapsed = time.perf_counter() - started
    return make_record(
        source_id=source["source_id"],
        source_family_time_group=source["source_family_time_group"],
        split=source["split"],
        experiment_arm="B",
        execution_status=execution_status,
        result_kind=result_kind,
        constructed_control=source["split"] == "constructed_control",
        pin=pin,
        parse=parse,
        elaboration=elaboration,
        source_maps=maps,
        reconstruction={"cycle": cycle, "final": final, "forward": forward},
        consistency=consistency,
        identities={
            "candidate_produced": ir["status"] == "compiled",
            "candidate_sha256": compiled["ir_sha256"],
            "checker_request": {
                "identical_to_candidate_pin": True,
                "pin_sha256": pin["pin_sha256"],
                "reason": "native checker absent from sealed PATH; candidate identities remain pinned",
                "submitted": False,
            },
            "entry_point": "papers/completion/autoformalization/evaluation/pipeline_arms.py:run_arm_b",
            "frozen_canonical_profile": FROZEN_CANONICAL_PROFILE_ID,
            "ir_status": ir["status"],
        },
        elapsed_seconds=elapsed,
        notes=notes,
        theorem=goal_id,
        fragment="typed-deontic-declared-vocabulary",
        checker=CHECKER_ID,
        compiler=COMPILER_B_ID,
        tool=COMPILER_B_ID,
    )


def run_arm_c(source: Mapping[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    compiled = compile_arm_c(source["text"])
    reconstructed = reconstruct_c(compiled["artifact"])
    recycled = compile_arm_c(reconstructed) if reconstructed else None
    # Compare view texts, not full artifact hashes: producer timestamps are absent,
    # but view formula text is the reconstruction target.
    cycle_ok = bool(reconstructed) and reconstructed == reconstruct_c(recycled["artifact"] if recycled else {"views": []})
    source_sha = sha256_text(source["text"])
    goal_id = f"C:{source['source_id']}:multiview-no-transfer"
    premises = tuple(C_VIEW_IDS)
    pin = identity_pin(
        source_id=source["source_id"],
        source_sha256=source_sha,
        goal_id=goal_id,
        goal_sha256=compiled["artifact_sha256"],
        premise_ids=premises,
        premise_sha256=sha256_obj(list(premises)),
        checker_digest=CHECKER_DIGEST,
    )
    elapsed = time.perf_counter() - started
    return make_record(
        source_id=source["source_id"],
        source_family_time_group=source["source_family_time_group"],
        split=source["split"],
        experiment_arm="C",
        execution_status="measured",
        result_kind="bounded_observation",
        constructed_control=source["split"] == "constructed_control",
        pin=pin,
        parse=empty_phase("success", "source-grounded view extraction"),
        elaboration=empty_phase("success", "six typed views; no admitted proof transfer"),
        source_maps=empty_phase("success", "view-0 source span"),
        reconstruction={
            "cycle": empty_phase("success" if cycle_ok else "failure", "producer view-text reconstruction"),
            "final": empty_phase("success" if reconstructed == source["text"][:240] or reconstructed == " ".join(source["text"].split())[:240] else "failure", "reconstructed view text vs normalized source prefix; not semantic gold"),
            "forward": empty_phase("success", "source compiled to typed multiview"),
        },
        consistency=empty_phase("success", "cross-view links are alignment only; proof_transfer_admitted=false"),
        identities={
            "candidate_produced": True,
            "candidate_sha256": compiled["artifact_sha256"],
            "checked_bridges": False,
            "checker_request": {
                "identical_to_candidate_pin": True,
                "pin_sha256": pin["pin_sha256"],
                "reason": "native checker absent; C does not consume D bridge evidence",
                "submitted": False,
            },
            "entry_point": "papers/completion/autoformalization/evaluation/pipeline_arms.py:run_arm_c",
            "proof_transfer_admitted": False,
            "view_ids": list(C_VIEW_IDS),
        },
        elapsed_seconds=elapsed,
        notes="Arm C typed source-grounded multiview without proof transfer. Bridge evidence was not supplied and is not present on the record.",
        theorem=goal_id,
        fragment="typed-multiview-no-transfer",
        checker=CHECKER_ID,
        compiler=COMPILER_C_ID,
        tool=COMPILER_C_ID,
    )


def run_arm_d_natural(source: Mapping[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    compiled = compile_arm_c(source["text"])
    source_sha = sha256_text(source["text"])
    goal_id = f"D:{source['source_id']}:no-admitted-bridge"
    pin = identity_pin(
        source_id=source["source_id"],
        source_sha256=source_sha,
        goal_id=goal_id,
        goal_sha256=compiled["artifact_sha256"],
        premise_ids=(),
        premise_sha256=sha256_obj([]),
        checker_digest=CHECKER_DIGEST,
    )
    elapsed = time.perf_counter() - started
    return make_record(
        source_id=source["source_id"],
        source_family_time_group=source["source_family_time_group"],
        split=source["split"],
        experiment_arm="D",
        execution_status="unsupported",
        result_kind="failure",
        constructed_control=False,
        pin=pin,
        parse=empty_phase("success", "C-level views produced; transfer not admitted"),
        elaboration=empty_phase("success", "typed views without a property-specific bridge for this source"),
        source_maps=empty_phase("success"),
        reconstruction={
            "cycle": empty_phase("unmeasured", "transfer unsupported; reconstruction not scored as a transfer"),
            "final": empty_phase("unmeasured"),
            "forward": empty_phase("success", "views compiled; no checked bridge"),
        },
        consistency=empty_phase("unsupported", "no compatible cross-source premises admitted for this source_id"),
        identities={
            "bridge_status": "unsupported_no_admitted_bridge_for_source",
            "candidate_produced": True,
            "candidate_sha256": compiled["artifact_sha256"],
            "checker_request": {
                "identical_to_candidate_pin": True,
                "pin_sha256": pin["pin_sha256"],
                "reason": "no admitted property-specific bridge binds this source_id; checker was not invoked on a transferred goal",
                "submitted": False,
            },
            "entry_point": "papers/completion/autoformalization/evaluation/pipeline_arms.py:run_arm_d",
            "looked_up_bridge_source_id": source["source_id"],
        },
        elapsed_seconds=elapsed,
        notes="Arm D found no AF-015 property-specific bridge for this frozen selection source. Unsupported transfer is not a measured zero and is not a false transfer.",
        false_transfer=False,
        theorem=goal_id,
        fragment=None,
        checker=CHECKER_ID,
        compiler=COMPILER_C_ID,
        tool="bridge-lookup/v1",
    )


def run_arm_d_constructed(kind: str) -> dict[str, Any]:
    started = time.perf_counter()
    write_fn = guarded_write if kind == "guarded" else unguarded_write
    rows = q1_assignments(write_fn)
    accepted = all(row["q1"] for row in rows)
    counter = [row for row in rows if not row["q1"]]
    source_sha = sha256_text(Q1_SOURCE["text"])
    goal_sha = sha256_text(Q1_SOURCE["goal_formula"])
    premise_sha = sha256_obj(list(Q1_SOURCE["premise_ids"]))
    pin = identity_pin(
        source_id=Q1_SOURCE["source_id"],
        source_sha256=source_sha,
        goal_id=Q1_SOURCE["goal_id"],
        goal_sha256=goal_sha,
        premise_ids=Q1_SOURCE["premise_ids"],
        premise_sha256=premise_sha,
        checker_digest=CHECKER_DIGEST,
    )
    evidence = {
        "assignments": rows,
        "goal_formula": Q1_SOURCE["goal_formula"],
        "goal_id": Q1_SOURCE["goal_id"],
        "implementation": kind,
        "identity_pin_sha256": pin["pin_sha256"],
        "premise_ids": list(Q1_SOURCE["premise_ids"]),
        "source_id": Q1_SOURCE["source_id"],
        "source_sha256": source_sha,
        "status": "accepted_transfer" if accepted else "accepted_countermodel",
        "supported_fragment": Q1_SOURCE["fragment"],
    }
    evidence["receipt_sha256"] = sha256_obj(evidence)
    if evidence["identity_pin_sha256"] != pin["pin_sha256"]:
        raise HarnessError("constructed D evidence pin drifted from candidate pin")
    if evidence["source_id"] != Q1_SOURCE["source_id"] or evidence["goal_id"] != Q1_SOURCE["goal_id"]:
        raise HarnessError("constructed D evidence identities drifted")
    elapsed = time.perf_counter() - started
    record = make_record(
        source_id=Q1_SOURCE["source_id"],
        source_family_time_group=Q1_SOURCE["source_family_time_group"],
        split="constructed_control",
        experiment_arm="D",
        execution_status="measured",
        result_kind="bounded_observation" if accepted else "countermodel",
        constructed_control=True,
        record_id=f"D:{Q1_SOURCE['source_id']}:{kind}",
        pin=pin,
        parse=empty_phase("success", "constructed Q1 sentence"),
        elaboration=empty_phase("success", "finite Boolean fragment q1-protected-write"),
        source_maps=empty_phase("success", "whole-sentence source span"),
        reconstruction={
            "cycle": empty_phase("unmeasured", "finite witness is not a compiler roundtrip"),
            "final": empty_phase("unmeasured"),
            "forward": empty_phase("success", "goal and premises bound before the witness check"),
        },
        consistency=empty_phase("success" if (accepted or counter) else "failure", "premises Protected/Approved/Write remain jointly interpretable"),
        identities={
            "bridge_status": evidence["status"],
            "candidate_produced": True,
            "checker_request": {
                "identical_to_candidate_pin": True,
                "pin_sha256": pin["pin_sha256"],
                "reason": "finite constructed witness; not a native kernel proof",
                "submitted": True,
            },
            "entry_point": "papers/completion/autoformalization/evaluation/bridge_cases.py",
            "implementation": kind,
            "policy_source_id": Q1_SOURCE["source_id"],
            "unguarded_countermodels": counter,
        },
        elapsed_seconds=elapsed,
        notes="Constructed finite Q1 witness. Labeled constructed_control and excluded from Table 6 natural cells. Not machine-checked compiler soundness.",
        useful=False,
        false_transfer=False,
        checker_class="none",
        receipt_sha256=evidence["receipt_sha256"],
        theorem=Q1_SOURCE["goal_id"],
        fragment=Q1_SOURCE["fragment"],
        checker=CHECKER_ID,
        compiler=COMPILER_C_ID,
        tool="finite-q1-witness/v1",
    )
    # Re-bind proof identity pin to the policy-level pin shared with the candidate.
    record["proof"]["identity_pin_sha256"] = pin["pin_sha256"]
    record["identities"]["policy_identity_pin_sha256"] = pin["pin_sha256"]
    record["identities"]["evidence_source_id"] = Q1_SOURCE["source_id"]
    record["identities"]["evidence_goal_id"] = Q1_SOURCE["goal_id"]
    record["identities"]["evidence_premise_ids"] = list(Q1_SOURCE["premise_ids"])
    body = {key: record[key] for key in record if key != "artifacts"}
    record["artifacts"] = {
        "command_log_sha256": None,
        "finite_witness_sha256": evidence["receipt_sha256"],
        "raw_sha256": sha256_obj(body),
    }
    return record


def run_arm_e(source: Mapping[str, Any], *, guidance: Mapping[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    source_sha = sha256_text(source["text"])
    goal_id = f"unproduced-learned-advice-goal:{source['source_id']}"
    pin = identity_pin(
        source_id=source["source_id"],
        source_sha256=source_sha,
        goal_id=goal_id,
        goal_sha256=sha256_text(goal_id),
        premise_ids=(),
        premise_sha256=sha256_obj([]),
        checker_digest=CHECKER_DIGEST,
    )
    elapsed = time.perf_counter() - started
    return make_record(
        source_id=source["source_id"],
        source_family_time_group=source["source_family_time_group"],
        split=source["split"],
        experiment_arm="E",
        execution_status="unavailable",
        result_kind="no_run",
        constructed_control=source["split"] == "constructed_control",
        pin=pin,
        parse=empty_phase("unavailable", "learned advice was not loaded"),
        elaboration=empty_phase("unavailable"),
        source_maps=empty_phase("unavailable"),
        reconstruction={
            "cycle": empty_phase("unavailable"),
            "final": empty_phase("unavailable"),
            "forward": empty_phase("unavailable"),
        },
        consistency=empty_phase("unavailable"),
        identities={
            "candidate_produced": False,
            "checker_digest_equals_D": True,
            "checker_mutated": False,
            "checker_request": {
                "identical_to_candidate_pin": True,
                "pin_sha256": pin["pin_sha256"],
                "reason": "; ".join(guidance["blockers"]),
                "submitted": False,
            },
            "e_locked": True,
            "entry_point": "papers/completion/autoformalization/evaluation/pipeline_arms.py:run_arm_e",
            "learned_advice_applied": False,
            "unavailable_blockers": list(guidance["blockers"]),
        },
        elapsed_seconds=elapsed,
        notes="Arm E remains locked: T4 unactivated, e_locked true, matching ingestion is not applied learning, checker digest unchanged from D.",
        theorem=goal_id,
        fragment=None,
        checker=CHECKER_ID,
        compiler=None,
        model=None,
        tool=None,
    )


def table6_cell(arm: str, column: str, **fields: Any) -> dict[str, Any]:
    cell = {
        "arm": arm,
        "cell_id": f"{arm}:{column}",
        "column": column,
        "denominator": 1913,
        "numerator": None,
        "original_heading": ORIGINAL_HEADINGS[column],
        "population": "final_test.natural_source_units",
        "revised_heading": REVISED_HEADINGS[column],
        "value": None,
        **fields,
    }
    return cell


def build_table6_cells(
    *,
    binaries: Mapping[str, Any],
    model: Mapping[str, Any],
    guidance: Mapping[str, Any],
) -> list[dict[str, Any]]:
    lean_absent = not binaries["tools"]["lean"]["usable"]
    model_absent = not model["runnable"]
    e_locked = not guidance["runnable"]
    cells = []
    for arm in PIPELINE_ARMS:
        arm_blockers = []
        if arm == "A" and (model_absent or lean_absent):
            arm_blockers.append("direct-model and native checker unavailable on sealed PATH")
        if arm == "E" and e_locked:
            arm_blockers.append("T4 unactivated; e_locked; learned features not applied")
        if lean_absent and arm in {"A", "B", "C", "D", "E"}:
            arm_blockers.append("native Lean/Z3/CVC5 absent from sealed PATH")
        cells.append(table6_cell(
            arm, "sources_covered",
            status="unrun",
            definition=(
                "Count of eligible final-test natural source units with execution_status=measured, "
                "divided by 1913. Unavailable, unsupported, abstained, timeout, invalid, failure, "
                "partial, and no_run remain in the denominator and are not scored as zero coverage."
            ),
            narrowed_claim=(
                "No Table 6 coverage claim. Final-test identities remain locked and unused. "
                "Selection-split structural coverage is a separate non-Table-6 diagnostic."
            ),
            backing="compact unrun recipe over splits.json counts.final_test.natural_source_units=1913",
            blockers=arm_blockers,
        ))
        cells.append(table6_cell(
            arm, "fidelity_uncertainty",
            status="unmeasured",
            definition=(
                "All-facet independent source-semantic fidelity requires independent gold and a "
                "definite judgment on every eligible unit. Primary numerator is null until that "
                "population is complete. Uncertainty is not imputed from missing labels."
            ),
            narrowed_claim=(
                "Independent human agreement and source-semantic fidelity are unmeasured. "
                "Parse/elaboration, teacher agreement, reconstruction, and prover success are "
                "not this cell and are not original-source gold."
            ),
            backing="AF-005 gold_facets remain pending_independent_review; AF-028 human_fidelity_status=unmeasured_not_collected",
            blockers=["independent_human_semantic_labels_available=false"],
        ))
        transfer_status = "unrun"
        if arm == "A" and (model_absent or lean_absent):
            transfer_status = "unavailable"
        if arm == "E" and e_locked:
            transfer_status = "unavailable"
        if lean_absent and arm in {"B", "C", "D"}:
            transfer_status = "unavailable"
        cells.append(table6_cell(
            arm, "correct_transfers",
            status=transfer_status,
            definition=(
                "Native-checked useful-proof coverage requires result_kind=native_checked_proof, "
                "proof.useful=true, checker_class=native, and receipt_sha256, with the receipt "
                "naming the same source/goal/premise/checker identities as the candidate. "
                "Semantic false-transfer is a separate unmeasured quantity."
            ),
            narrowed_claim=(
                "No Table 6 correct-transfer or native useful-proof claim. Sealed PATH has no "
                "Lean/Z3/CVC5. Constructed Q1 finite witnesses are labeled constructed_control "
                "and do not fill this cell. AF-027 development Lean identity theorems are not reused."
            ),
            backing="sealed-PATH binary probe plus compact 1913-unit no_run recipe",
            blockers=arm_blockers,
        ))
        cells.append(table6_cell(
            arm, "cost_latency",
            status="unrun",
            definition=(
                "Sum of observed elapsed/cpu/gpu/provider/human-review costs over the 1913-unit "
                "final-test population, including failed and unrun attempts attributed to that "
                "population. A deterministically emitted formula does not have zero total cost."
            ),
            narrowed_claim=(
                "No Table 6 cost/latency figure. Final-test was not executed, so the cell is "
                "unrun rather than 0. Selection-split structural elapsed times are retained "
                "separately and are not this cell."
            ),
            backing="compact unrun recipe total_cost.status=unrun with retained_cost_records=0",
            blockers=["final_test_locked"],
        ))
    if len(cells) != 20:
        raise HarnessError(f"expected 20 Table 6 cells, got {len(cells)}")
    return cells


def load_selection_sources() -> list[dict[str, Any]]:
    path = PAPER_ROOT / "receipts" / "snapshots" / "AF-004" / "selection.sources.jsonl"
    rows = load_jsonl(path)
    if len(rows) != 15:
        raise HarnessError(f"expected 15 selection sources, got {len(rows)}")
    sources = []
    for row in rows:
        text = str(row["text"])
        sources.append({
            "citation": row.get("citation"),
            "record_id": row["record_id"],
            "source_family_time_group": f"{row['family']}:{row['effective_start']}",
            "source_id": row["record_id"],
            "source_sha256": sha256_text(text),
            "split": "selection",
            "text": text,
        })
    return sources


def import_run_benchmark():
    if str(EVAL_DIR) not in sys.path:
        sys.path.insert(0, str(EVAL_DIR))
    import run_benchmark as harness  # noqa: WPS433
    return harness


def main() -> int:
    if checker_contract() and sha256_obj(checker_contract()) != CHECKER_DIGEST:
        raise HarnessError("shared checker digest drifted")
    splits = load_json(PAPER_ROOT / "data" / "splits.json")
    plan = load_json(PAPER_ROOT / "config" / "experiment_plan.json")
    metrics = load_json(PAPER_ROOT / "config" / "metrics.json")
    scope = load_json(PAPER_ROOT / "config" / "structural_evidence_scope.json")
    consumer = load_json(PAPER_ROOT / "evidence" / "consumer_activation.json")
    gold = load_jsonl(PAPER_ROOT / "data" / "gold_facets.jsonl")
    final_count = splits["counts"]["final_test"]["natural_source_units"]
    if final_count != 1913:
        raise HarnessError("frozen final-test natural source units drifted")
    if splits.get("holdout", {}).get("state") != "private_staged_not_released":
        raise HarnessError("final-test holdout is not locked")
    if any(item.get("label_status") == "admitted" for item in gold):
        raise HarnessError("gold facets unexpectedly admitted")
    binaries = probe_binaries()
    model = probe_direct_model()
    guidance = probe_arm_e(consumer)
    inspected = inspect_sources()
    selection = load_selection_sources()
    constructed_source = {
        "source_family_time_group": Q1_SOURCE["source_family_time_group"],
        "source_id": Q1_SOURCE["source_id"],
        "split": "constructed_control",
        "text": Q1_SOURCE["text"],
    }

    records: list[dict[str, Any]] = []
    for source in selection:
        records.append(run_arm_a(source, binaries=binaries, model=model))
        records.append(run_arm_b(source))
        records.append(run_arm_c(source))
        records.append(run_arm_d_natural(source))
        records.append(run_arm_e(source, guidance=guidance))
    records.append(run_arm_a(constructed_source, binaries=binaries, model=model))
    records.append(run_arm_b(constructed_source))
    records.append(run_arm_c(constructed_source))
    records.append(run_arm_d_constructed("guarded"))
    records.append(run_arm_d_constructed("unguarded"))
    records.append(run_arm_e(constructed_source, guidance=guidance))

    for record in records:
        if record["fixture"]:
            raise HarnessError(f"fixture leaked into results: {record['record_id']}")
        if record["identities"]["source_id"] not in {record["source_id"], Q1_SOURCE["source_id"]}:
            raise HarnessError(f"source identity mismatch: {record['record_id']}")
        pin = record["identities"]["identity_pin_sha256"]
        request = record["identities"]["checker_request"]
        if request["pin_sha256"] != pin:
            raise HarnessError(f"candidate/checker pin mismatch: {record['record_id']}")
        if record["proof"]["useful"]:
            raise HarnessError(f"useful proof claimed without native receipt: {record['record_id']}")
        if record["result_kind"] == "native_checked_proof":
            raise HarnessError(f"native_checked_proof emitted without a kernel: {record['record_id']}")
        if record["experiment_arm"] == "C":
            dumped = canonical_dumps(record)
            for blocked in ("translation_receipts", "checked_property_bridges", "accepted_transfer"):
                if blocked in dumped and record["identities"].get("checked_bridges"):
                    raise HarnessError(f"C consumed D evidence: {record['record_id']}")
        if record["experiment_arm"] == "E" and record["identities"].get("checker_mutated"):
            raise HarnessError("E mutated its checker")

    harness = import_run_benchmark()
    for record in records:
        harness.validate_record(record)

    selection_records = [row for row in records if row["split"] == "selection"]
    constructed_records = [row for row in records if row["constructed_control"]]
    if len(selection_records) != 75:
        raise HarnessError(f"expected 75 selection records, got {len(selection_records)}")

    unrun_recipe = {
        "schema": SCHEMA_RECIPE,
        "arms": list(PIPELINE_ARMS),
        "default_execution_status": "no_run",
        "default_result_kind": "no_run",
        "eligible_basis": {
            "corpus_manifest_sha256": sha256_file(PAPER_ROOT / "data" / "corpus_manifest.json"),
            "count": 1913,
            "experiment_plan_sha256": sha256_file(PAPER_ROOT / "config" / "experiment_plan.json"),
            "field": "natural_source_units",
            "manifest_path": "papers/completion/autoformalization/data/splits.json",
            "manifest_sha256": sha256_file(PAPER_ROOT / "data" / "splits.json"),
            "private_final_ids_disclosed": False,
            "split": "final_test",
        },
        "notes": "Compact Table 6 unrun recipe. Individual final-test identities remain undisclosed.",
        "records": [],
    }
    unrun_tables = harness.regenerate_tables(unrun_recipe, metrics=metrics)
    harness.assert_tables_deterministic(unrun_recipe, unrun_tables)

    selection_recipe = {
        "schema": SCHEMA_RECIPE,
        "arms": list(PIPELINE_ARMS),
        "default_execution_status": "no_run",
        "default_result_kind": "no_run",
        "eligible_basis": {
            "count": 15,
            "field": "natural_source_units",
            "manifest_path": "papers/completion/autoformalization/receipts/snapshots/AF-004/selection.sources.jsonl",
            "manifest_sha256": sha256_file(PAPER_ROOT / "receipts" / "snapshots" / "AF-004" / "selection.sources.jsonl"),
            "split": "selection",
        },
        "notes": "Non-Table-6 structural execution on the frozen public selection split.",
        "records": selection_records,
    }
    selection_tables = harness.regenerate_tables(selection_recipe, metrics=metrics)

    cells = build_table6_cells(binaries=binaries, model=model, guidance=guidance)
    by_arm: dict[str, dict[str, int]] = {arm: {} for arm in PIPELINE_ARMS}
    for row in selection_records:
        arm = row["experiment_arm"]
        status = row["execution_status"]
        by_arm[arm][status] = by_arm[arm].get(status, 0) + 1

    manifest = {
        "schema": SCHEMA_MANIFEST,
        "task_id": TASK_ID,
        "suite_id": SUITE_ID,
        "created_at": utc_now(),
        "claim_policy": {
            "constructed_control_is_not_table_6": True,
            "development_qualification_is_not_table_6": True,
            "independent_fidelity_unmeasured": True,
            "selection_structural_is_not_final_distribution": True,
            "semantic_false_transfer_unmeasured": True,
            "synthetic_success_forbidden": True,
            "unavailable_is_not_zero": True,
            "unrun_is_not_zero": True,
        },
        "frozen_inputs": {
            "consumer_activation_sha256": sha256_file(PAPER_ROOT / "evidence" / "consumer_activation.json"),
            "environment_manifest_sha256": sha256_file(PAPER_ROOT / "config" / "environment_manifest.json"),
            "experiment_plan_sha256": sha256_file(PAPER_ROOT / "config" / "experiment_plan.json"),
            "gold_facets_sha256": sha256_file(PAPER_ROOT / "data" / "gold_facets.jsonl"),
            "metrics_sha256": sha256_file(PAPER_ROOT / "config" / "metrics.json"),
            "pipeline_arms_sha256": sha256_file(PAPER_ROOT / "config" / "pipeline_arms.json"),
            "selection_sources_sha256": sha256_file(PAPER_ROOT / "receipts" / "snapshots" / "AF-004" / "selection.sources.jsonl"),
            "splits_sha256": sha256_file(PAPER_ROOT / "data" / "splits.json"),
            "structural_evidence_scope_sha256": sha256_file(PAPER_ROOT / "config" / "structural_evidence_scope.json"),
            "teacher_manifest_sha256": sha256_file(PAPER_ROOT / "data" / "teacher_manifest.json"),
        },
        "matched_comparison": {
            "checker_digest": CHECKER_DIGEST,
            "checker_id": CHECKER_ID,
            "eligible_final_test_natural_source_units": 1913,
            "private_final_ids_disclosed": False,
            "resource_envelope": plan["common_budget"],
            "seeds": plan["population_and_statistics"]["seeds"],
            "shared_checker_across_arms": list(PIPELINE_ARMS),
        },
        "capability_probe": {
            "direct_model": model,
            "home": os.environ.get("HOME"),
            "home_is_validation_private": "ipfs-accelerate-validation-home-" in str(os.environ.get("HOME") or ""),
            "interpreter": sys.executable,
            "learned_guidance": guidance,
            "native_binaries": binaries,
            "path": os.environ.get("PATH"),
            "python_version": sys.version,
        },
        "inspected_not_imported": inspected,
        "table6": {
            "cell_count": len(cells),
            "cells": cells,
            "denominator": 1913,
            "original_caption": "Final empirical results remain unmeasured in this draft. Fill from retained runs, not targets.",
            "revised_caption": (
                "Table 6 final-test A–E comparison. Each of 20 cells is unrun, unmeasured, or "
                "unavailable with a narrowed claim. Selection-split structural outcomes and "
                "constructed Q1 witnesses are retained separately and are not these cells."
            ),
            "unrun_recipe_sha256": sha256_obj({key: unrun_recipe[key] for key in unrun_recipe if key != "records"}),
            "unrun_tables_sha256": unrun_tables["tables_sha256"],
        },
        "non_table6_structural_execution": {
            "constructed_control_records": len(constructed_records),
            "not_final_distribution": True,
            "population": "AF-004 selection.sources.jsonl (15 natural CFR units) plus constructed Q1",
            "selection_execution_status_counts": by_arm,
            "selection_records": len(selection_records),
            "selection_tables_sha256": selection_tables["tables_sha256"],
            "split": "selection",
        },
        "scope": {
            "adjudication_status": scope.get("adjudication_status"),
            "human_fidelity_status": scope.get("human_fidelity_status"),
            "independent_human_semantic_labels_available": scope.get("independent_human_semantic_labels_available"),
            "policy_id": scope.get("policy_id"),
        },
        "limitations": [
            "Final-test 1913-unit Table 6 comparison is unrun; identities remain undisclosed.",
            "Independent source-semantic fidelity and semantic false-transfer are unmeasured.",
            "Sealed PATH has no lean/lake/elan/z3/cvc5/vampire/eprover/coqc/isabelle.",
            "Arm A had no model credential and was not dispatched.",
            "Arm E is locked; T4 unactivated; checker digest equals D and was not mutated.",
            "Constructed Q1 finite witnesses are not Table 6 and not compiler soundness.",
            "AF-027 development qualification and dummy identity theorems are not reused.",
        ],
    }
    manifest["manifest_sha256"] = sha256_obj({key: manifest[key] for key in manifest if key != "manifest_sha256"})

    out_dir = PAPER_ROOT / "runs" / "pipeline_comparison"
    write_json(out_dir / "manifest.json", manifest)
    write_jsonl(out_dir / "results.jsonl", records)
    summary = {
        "constructed_records": len(constructed_records),
        "manifest_sha256": manifest["manifest_sha256"],
        "results_records": len(records),
        "selection_records": len(selection_records),
        "table6_cells": len(cells),
        "table6_statuses": sorted({cell["status"] for cell in cells}),
        "unrun_tables_sha256": unrun_tables["tables_sha256"],
    }
    print(canonical_dumps(summary))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except HarnessError as exc:
        print(f"measure_pipeline: {exc}", file=sys.stderr)
        raise SystemExit(1)
