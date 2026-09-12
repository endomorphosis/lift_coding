#!/usr/bin/env python3
"""AF-014 bounded compiler/decompiler repair ablation.

Development-set defect: exception tokens leaked into governing predicates
(``audit_exempt``) and ``unless``/``except`` cues were compiled as generic
conditions.  The executable repair scopes exception prefixes onto the
governing formula, excludes exception tokens from that predicate, and
labels exception-prefix cues with role ``exception``.

This harness does not open final-test packets, does not treat T4 guidance
overlay as the repair, does not drop independently specified source meaning
to make a round-trip look equal, and does not claim a measured T5
improvement.  Native Lean/Z3/CVC5 binaries are probed on the sealed PATH
and recorded unavailable when absent.  Standard-library plus the two
patched codec modules only.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
PAPER = HERE.parents[2]
REPO = PAPER.parents[2]
sys.path.insert(0, str(REPO / "external" / "ipfs_datasets"))

from ipfs_datasets_py.logic.modal.codec import (  # noqa: E402
    EXCEPTION_SCOPE_RULE_ID as CODEC_RULE_ID,
    _apply_executable_exception_scoping,
    _enrich_modal_ir_formula_clauses,
)
from ipfs_datasets_py.optimizers.logic_theorem_optimizer.spacy_modal_codec import (  # noqa: E402
    EXCEPTION_SCOPE_RULE_ID,
    SpaCyLegalEncoder,
    SpaCyModalIRCompiler,
)

SCHEMA_RESULT = "autoformalization-compiler-repair-result/v1"
SCHEMA_TRACE = "autoformalization-repair-task-trace/v1"
SCHEMA_VALIDATION = "autoformalization-repair-validation/v1"
TASK_ID = "AF-014"
SUITE_ID = "AF-014-bounded-compiler-decompiler-repair"
ARM = "T5"
STARTING_ARM = "T4"
RULE_ID = "af014-executable-exception-scoping/v1"
CANARY_SHA256 = "98549048682ea1eb727812a6bb8e9d7a9834c22d43a62fd5373b7b7fad97c207"
CANARY_ID = f"af004-fixed-canary-{CANARY_SHA256}"
CANARY_PATH = (
    PAPER / "receipts" / "snapshots" / "AF-004" / "fixed_canary.sources.jsonl"
)
PRE_PATCH = {
    "spacy_modal_codec.py": "fd40489c229a8976e50e31d5b9b46184796d7b0cd73e35531dfd0e817833b26f",
    "codec.py": "0f81dad45244ab88d3df5ac8c5d585d80d4ee14c59a5441c1bdd19f5a2cccd86",
}
BASELINE_MP09 = {
    "source": "The operator must audit unless exempt.",
    "split": "constructed_control",
    "family_id": "MP09-exception-scope",
    "deontic_predicate": "audit_exempt",
    "deontic_exceptions": ["unless exempt"],
    "unless_role": "condition",
    "defect": (
        "Exception token 'exempt' leaked into the governing deontic predicate "
        "and the unless cue was compiled as a generic condition."
    ),
}
NATIVE_CHECKERS = (
    "lean", "lake", "z3", "cvc5", "vampire", "eprover", "coqc", "isabelle",
)
SEALED_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"

DEVELOPMENT_CASES = (
    {
        "record_id": "T5-DEV-MP09-EXCEPTION-SCOPE",
        "family_id": "MP09-exception-scope",
        "source": "The operator must audit unless exempt.",
        "required": {
            "deontic_predicate_equals": "audit",
            "deontic_predicate_excludes": ("exempt",),
            "deontic_exceptions_contains": "unless exempt",
            "unless_role": "exception",
        },
        "notes": "Supported MP09 reading: not exempt -> O(audit). Predicate must not absorb the exception.",
    },
    {
        "record_id": "T5-DEV-CONDITION-AND-EXCEPTION",
        "family_id": "compiler-contract-if-unless",
        "source": (
            "If the application is complete, the agency must issue written "
            "notice unless waived."
        ),
        "required": {
            "deontic_exceptions_contains": "unless waived",
            "deontic_conditions_contains": "if the application is complete",
            "deontic_predicate_excludes": ("waived",),
        },
        "notes": "Existing compiler contract retained; exception remains a distinct slot.",
    },
    {
        "record_id": "T5-DEV-EXCEPT-AS-OTHERWISE-PROVIDED",
        "family_id": "compiler-contract-except-as-otherwise-provided",
        "source": (
            "The Secretary shall publish the notice except as otherwise "
            "provided in this section."
        ),
        "required": {
            "deontic_exceptions_contains": "except as otherwise provided",
            "deontic_predicate_excludes": ("provided",),
        },
        "notes": "Longer exception prefix is scoped, not folded into publish_notice.",
    },
    {
        "record_id": "T5-DEV-NO-EXCEPTION-REGRESSION",
        "family_id": "compiler-contract-no-exception",
        "source": "The agency must make records promptly available to any person.",
        "required": {
            "deontic_predicate_includes": "records",
            "deontic_exceptions_empty": True,
        },
        "notes": "Sentences without exception prefixes keep their previous predicate terms.",
    },
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda handle=handle: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_bytes(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, indent=2, sort_keys=True) + "\n"
    tmp = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    with tmp.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    tmp.replace(path)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line:
            rows.append(json.loads(line))
    return rows


def probe_native_checkers() -> list[dict[str, Any]]:
    probes = []
    for name in NATIVE_CHECKERS:
        resolved = shutil.which(name)
        probes.append(
            {
                "name": name,
                "resolved_path": resolved,
                "status": "unavailable" if resolved is None else "present",
                "usable_in_sealed_validation": resolved is not None,
            }
        )
    return probes


def formula_view(formula) -> dict[str, Any]:
    return {
        "family": formula.operator.family,
        "symbol": formula.operator.symbol,
        "predicate": formula.predicate.name,
        "role": formula.predicate.role,
        "arguments": list(formula.predicate.arguments or []),
        "conditions": list(formula.conditions or []),
        "exceptions": list(formula.exceptions or []),
        "cue": formula.metadata.get("cue"),
        "exception_scope_rule": formula.metadata.get("exception_scope_rule"),
        "exception_scope_role": formula.metadata.get("exception_scope_role"),
        "exception_tokens_excluded_from_predicate": formula.metadata.get(
            "exception_tokens_excluded_from_predicate"
        ),
        "exception_scope_source": formula.metadata.get("exception_scope_source"),
    }


def compile_text(encoder, compiler, text: str, document_id: str):
    encoding = encoder.encode(text, document_id=document_id)
    compiled = compiler.compile(encoding)
    enriched = _enrich_modal_ir_formula_clauses(compiled)
    return _apply_executable_exception_scoping(enriched)


def deontic_formula(ir):
    for formula in ir.formulas:
        if formula.operator.family == "deontic":
            return formula
    return None


def check_required(ir, required: dict[str, Any]) -> tuple[bool, list[str]]:
    failures: list[str] = []
    deontic = deontic_formula(ir)
    if deontic is None:
        failures.append("missing deontic formula")
        return False, failures
    predicate = deontic.predicate.name.lower()
    exceptions = [str(item).lower() for item in deontic.exceptions]
    conditions = [str(item).lower() for item in deontic.conditions]
    if "deontic_predicate_equals" in required:
        if deontic.predicate.name != required["deontic_predicate_equals"]:
            failures.append(
                f"predicate {deontic.predicate.name!r} != {required['deontic_predicate_equals']!r}"
            )
    for token in required.get("deontic_predicate_excludes", ()):
        if token.lower() in predicate.split("_"):
            failures.append(f"predicate still contains excluded token {token!r}")
    if "deontic_predicate_includes" in required:
        token = required["deontic_predicate_includes"]
        if token.lower() not in predicate:
            failures.append(f"predicate missing {token!r}")
    if "deontic_exceptions_contains" in required:
        needle = required["deontic_exceptions_contains"].lower()
        if not any(needle in item for item in exceptions):
            failures.append(f"exceptions {exceptions!r} missing {needle!r}")
    if required.get("deontic_exceptions_empty") and exceptions:
        failures.append(f"expected no exceptions, got {exceptions!r}")
    if "deontic_conditions_contains" in required:
        needle = required["deontic_conditions_contains"].lower()
        if not any(needle in item for item in conditions):
            failures.append(f"conditions {conditions!r} missing {needle!r}")
    if "unless_role" in required:
        unless_formulas = [
            formula for formula in ir.formulas
            if str(formula.metadata.get("cue", "")).lower() == "unless"
        ]
        if not unless_formulas:
            failures.append("missing unless cue formula")
        elif unless_formulas[0].predicate.role != required["unless_role"]:
            failures.append(
                f"unless role {unless_formulas[0].predicate.role!r} != {required['unless_role']!r}"
            )
    return not failures, failures


def result_row(
    *,
    record_id: str,
    execution_status: str,
    result_kind: str,
    outcome: str,
    notes: str,
    constructed: bool,
    split: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    body = {
        "schema": SCHEMA_RESULT,
        "task_id": TASK_ID,
        "suite_id": SUITE_ID,
        "record_id": record_id,
        "experiment_arm": ARM,
        "starting_arm": STARTING_ARM,
        "split": split,
        "constructed_control": constructed,
        "fixture": constructed,
        "eligible_for_natural_table": False,
        "execution_status": execution_status,
        "result_kind": result_kind,
        "outcome": outcome,
        "notes": notes,
        "accepted_improvement_is_measured_outcome": False,
        "source_semantic_fidelity": "unmeasured",
        "human_agreement": "unmeasured",
        "identities": {
            "checker": "stdlib_structural_compiler_contract",
            "compiler": "spacy_modal_codec_v1+executable_exception_scoping",
            "experiment_arm": ARM,
            "exception_scope_rule": RULE_ID,
            "tool": str(HERE / "run_compiler_repair.py"),
        },
        "proof": {
            "checker_class": "none",
            "receipt_sha256": None,
            "useful": False,
        },
    }
    if extra:
        body.update(extra)
    body["artifacts"] = {"raw_sha256": sha256_json(body)}
    return body


def mp12_shared_loss() -> dict[str, Any]:
    def implication(left: bool, right: bool) -> bool:
        return (not left) or right

    def norm_satisfied(norm: dict[str, str], exempt: bool, obligation_holds: bool) -> bool:
        if "exception" in norm:
            return implication(not exempt, obligation_holds)
        return obligation_holds

    original = {"obligation": "audit", "exception": "exempt"}
    first_ir = {"obligation": original["obligation"]}
    realized = "must audit"
    realized_source = {"obligation": "audit"}
    second_ir = {"obligation": realized_source["obligation"]}
    disagreements = []
    for exempt, obligation_holds in ((False, False), (False, True), (True, False), (True, True)):
        source_truth = norm_satisfied(original, exempt, obligation_holds)
        round_trip_truth = norm_satisfied(realized_source, exempt, obligation_holds)
        if source_truth != round_trip_truth:
            disagreements.append(
                {
                    "exempt": exempt,
                    "obligation_holds": obligation_holds,
                    "source_truth": source_truth,
                    "round_trip_truth": round_trip_truth,
                }
            )
    return {
        "family_id": "MP12-round-trip-shared-loss",
        "original_source": original,
        "first_ir": first_ir,
        "realized": realized,
        "recompiled_ir": second_ir,
        "recompiled_ir_equal": first_ir == second_ir,
        "source_meaning_equal": not disagreements,
        "meaning_disagreement_count": len(disagreements),
        "meaning_counterexamples": disagreements,
        "claim": (
            "Equal recompiled IR after dropping the same exception is not source "
            "fidelity. The compiler patch does not delete this independently "
            "specified meaning disagreement."
        ),
    }


def canary_structural(encoder, compiler) -> dict[str, Any]:
    rows = load_jsonl(CANARY_PATH)
    observations = []
    for row in rows:
        record_id = row["record_id"]
        text = row.get("text") or ""
        source_sha = (
            row.get("source_lineage", {}).get("source_sha256")
            or sha256_bytes(text.encode("utf-8"))
        )
        ir = compile_text(encoder, compiler, text, record_id)
        exception_formulas = [
            formula_view(formula)
            for formula in ir.formulas
            if formula.exceptions
        ]
        observations.append(
            {
                "record_id": record_id,
                "source_text_sha256": source_sha,
                "formula_count": len(ir.formulas),
                "exception_formula_count": len(exception_formulas),
                "exception_scope_rule": ir.metadata.get("exception_scope_rule"),
                "compiled": True,
            }
        )
    return {
        "canary_id": CANARY_ID,
        "path": str(CANARY_PATH.relative_to(REPO)),
        "sha256": sha256_file(CANARY_PATH),
        "expected_sha256": CANARY_SHA256,
        "n_records": len(rows),
        "used_for_patch_selection": False,
        "role": "paired_fixed_canary_structural_regression",
        "distinct_from_final_test": True,
        "observations": observations,
    }


def main() -> int:
    started = utc_now()
    if EXCEPTION_SCOPE_RULE_ID != RULE_ID or CODEC_RULE_ID != RULE_ID:
        raise SystemExit("exception-scope rule id drifted between codec modules")
    encoder = SpaCyLegalEncoder(model_name="definitely_missing_legal_model")
    compiler = SpaCyModalIRCompiler()
    native = probe_native_checkers()
    missing_native = [item["name"] for item in native if item["status"] == "unavailable"]

    development_rows = []
    development_views = []
    all_passed = True
    for case in DEVELOPMENT_CASES:
        ir = compile_text(encoder, compiler, case["source"], case["record_id"])
        passed, failures = check_required(ir, case["required"])
        all_passed = all_passed and passed
        view = {
            "record_id": case["record_id"],
            "family_id": case["family_id"],
            "source": case["source"],
            "passed": passed,
            "failures": failures,
            "document_exception_scope_rule": ir.metadata.get("exception_scope_rule"),
            "document_exception_scope_source": ir.metadata.get("exception_scope_source"),
            "formulas": [formula_view(formula) for formula in ir.formulas],
        }
        development_views.append(view)
        development_rows.append(
            result_row(
                record_id=case["record_id"],
                execution_status="measured" if passed else "failure",
                result_kind="bounded_observation",
                outcome="structural_exception_scope_contract"
                if passed
                else "structural_exception_scope_mismatch",
                notes=case["notes"] + ("" if passed else f" failures={failures}"),
                constructed=True,
                split="constructed_control",
                extra={
                    "family_id": case["family_id"],
                    "patch_selected_from_final_test": False,
                    "compiler_observation": view,
                },
            )
        )

    mp09 = next(item for item in development_views if item["record_id"] == "T5-DEV-MP09-EXCEPTION-SCOPE")
    deontic = next(item for item in mp09["formulas"] if item["family"] == "deontic")
    if deontic["predicate"] == BASELINE_MP09["deontic_predicate"]:
        all_passed = False
        development_rows[0]["execution_status"] = "failure"
        development_rows[0]["notes"] += " post-patch predicate still equals the frozen defect"

    shared_loss = mp12_shared_loss()
    if shared_loss["source_meaning_equal"] or shared_loss["meaning_disagreement_count"] == 0:
        all_passed = False
    development_rows.append(
        result_row(
            record_id="T5-DEV-MP12-SHARED-LOSS-RETAINED",
            execution_status="measured" if not shared_loss["source_meaning_equal"] else "failure",
            result_kind="bounded_observation",
            outcome="shared_source_error_retained",
            notes=shared_loss["claim"],
            constructed=True,
            split="constructed_control",
            extra={"family_id": "MP12-round-trip-shared-loss", "shared_loss": shared_loss},
        )
    )

    canary = canary_structural(encoder, compiler)
    canary_ok = (
        canary["n_records"] == 38
        and canary["sha256"] == CANARY_SHA256
        and all(item["compiled"] for item in canary["observations"])
        and not canary["used_for_patch_selection"]
    )
    all_passed = all_passed and canary_ok
    development_rows.append(
        result_row(
            record_id="T5-CANARY-STRUCTURAL",
            execution_status="measured" if canary_ok else "failure",
            result_kind="bounded_observation",
            outcome="paired_fixed_canary_structural",
            notes=(
                "38-record AF-004 canary compiled after freeze; not used to choose "
                "the patch; distinct from the 1913-unit final test."
            ),
            constructed=False,
            split="fixed_canary",
            extra={
                "canary_id": CANARY_ID,
                "canary_sha256": canary["sha256"],
                "n_records": canary["n_records"],
                "used_for_patch_selection": False,
                "formula_count_sum": sum(item["formula_count"] for item in canary["observations"]),
                "exception_formula_count_sum": sum(
                    item["exception_formula_count"] for item in canary["observations"]
                ),
            },
        )
    )

    development_rows.append(
        result_row(
            record_id="T5-T4-STARTING-ARM",
            execution_status="unavailable",
            result_kind="no_run",
            outcome="t4_unactivated_unavailable",
            notes=(
                "Protocol-defined T5 starting arm is sealed T4. AF-013 records T4 as "
                "unactivated/unavailable with E locked. Matching ingestion identity is "
                "not applied learned guidance. This repair is an executable compiler "
                "change, not a parameter update."
            ),
            constructed=False,
            split="selection",
            extra={
                "T4": "unactivated/unavailable",
                "e_locked": True,
                "applied_learned_features": False,
                "parameter_action": False,
                "executable_change": True,
            },
        )
    )
    development_rows.append(
        result_row(
            record_id="T5-FINAL-TEST",
            execution_status="no_run",
            result_kind="no_run",
            outcome="unrun_final_test",
            notes=(
                "Final-test packets remain sealed (1913 natural units). They were not "
                "read, scored, or used to choose the patch. Untouched-test T5 "
                "evaluation remains unrun with narrowed claims."
            ),
            constructed=False,
            split="final_test",
            extra={
                "used_for_patch_selection": False,
                "natural_source_units": 1913,
                "opened": False,
            },
        )
    )
    development_rows.append(
        result_row(
            record_id="T5-NATIVE-CHECKERS",
            execution_status="unavailable",
            result_kind="no_run",
            outcome="native_checkers_unavailable",
            notes="Sealed PATH has no Lean/Z3/CVC5/Isabelle binaries; no kernel proof is claimed.",
            constructed=False,
            split="constructed_control",
            extra={"native_checkers": native, "missing_native_checkers": missing_native},
        )
    )
    development_rows.append(
        result_row(
            record_id="T5-UNEXECUTED-SYNTHESIS",
            execution_status="no_run",
            result_kind="no_run",
            outcome="unrun_program_synthesis",
            notes=(
                "Unbounded compiler/decompiler synthesis was not executed. The "
                "accepted change is one bounded executable exception-scoping rule."
            ),
            constructed=False,
            split="constructed_control",
            extra={"synthesis_executed": False},
        )
    )
    development_rows.append(
        result_row(
            record_id="T5-NO-MEASURED-IMPROVEMENT",
            execution_status="no_run",
            result_kind="no_run",
            outcome="no_accepted_improvement_as_measured_outcome",
            notes=(
                "Structural contracts on constructed development witnesses are not "
                "held-out fidelity, native checked coverage, or a measured T5 gain. "
                "No accepted improvement is reported as a valid measured outcome."
            ),
            constructed=True,
            split="constructed_control",
            extra={"unseen_fidelity": None, "native_checked_coverage": None},
        )
    )

    rejected = [
        {
            "proposal_id": "reject-drop-exception-to-equalize-mp12",
            "status": "rejected",
            "reason": (
                "Deleting the independently specified exception from source meaning "
                "would make C12/MP12 source_meaning_equal and make a proof easy. "
                "Shared source errors are retained."
            ),
            "kind": "semantic_erasure",
        },
        {
            "proposal_id": "reject-t4-guidance-overlay-as-repair",
            "status": "rejected",
            "reason": (
                "_apply_compiler_guidance_typed_semantics is a learned-guidance/"
                "parameter overlay. T4 is unactivated/unavailable; a parameter "
                "action is not an executable compiler/decompiler patch."
            ),
            "kind": "parameter_action",
        },
        {
            "proposal_id": "reject-final-test-patch-selection",
            "status": "rejected",
            "reason": "Final-test examples never choose the patch.",
            "kind": "leakage",
        },
        {
            "proposal_id": "reject-unbounded-registry-rewrite",
            "status": "rejected",
            "reason": "Unbounded synthesis remains unrun; only the bounded exception-scoping rule was applied.",
            "kind": "unexecuted_synthesis",
        },
    ]
    for item in rejected:
        development_rows.append(
            result_row(
                record_id=f"T5-REJECTED-{item['proposal_id']}",
                execution_status="measured",
                result_kind="bounded_observation",
                outcome="rejected_patch",
                notes=item["reason"],
                constructed=True,
                split="constructed_control",
                extra={"rejected_patch": item},
            )
        )

    spacy_path = REPO / "external/ipfs_datasets/ipfs_datasets_py/optimizers/logic_theorem_optimizer/spacy_modal_codec.py"
    codec_path = REPO / "external/ipfs_datasets/ipfs_datasets_py/logic/modal/codec.py"
    post_patch = {
        "spacy_modal_codec.py": sha256_file(spacy_path),
        "codec.py": sha256_file(codec_path),
    }
    if post_patch["spacy_modal_codec.py"] == PRE_PATCH["spacy_modal_codec.py"]:
        raise SystemExit("spacy_modal_codec.py was not changed")
    if post_patch["codec.py"] == PRE_PATCH["codec.py"]:
        raise SystemExit("codec.py was not changed")

    live_results = PAPER / "runs" / "compiler_repair" / "results.jsonl"
    live_trace = PAPER / "evidence" / "repair_task_trace.json"
    live_validation = PAPER / "evidence" / "repair_validation.json"
    live_diff = PAPER / "evidence" / "compiler_patch.diff"

    trace = {
        "schema": SCHEMA_TRACE,
        "task_id": TASK_ID,
        "suite_id": SUITE_ID,
        "rule_id": RULE_ID,
        "starting_arm": STARTING_ARM,
        "starting_arm_status": "unactivated/unavailable",
        "chain": [
            {
                "stage": "observed_defect",
                "evidence": "compiler introspection on MP09 constructed development witness",
                "split": "constructed_control",
                "final_test_used": False,
                "observation": BASELINE_MP09,
            },
            {
                "stage": "task_proposal",
                "proposal_id": "af014-executable-exception-scoping/v1",
                "kind": "executable_compiler_change",
                "parameter_action": False,
                "description": (
                    "Scope unless/except prefixes as exception guards, exclude "
                    "exception-clause tokens from governing predicates, and keep "
                    "this rule independent of T4 guidance overlay."
                ),
            },
            {
                "stage": "actual_patch",
                "paths": [
                    "external/ipfs_datasets/ipfs_datasets_py/optimizers/logic_theorem_optimizer/spacy_modal_codec.py",
                    "external/ipfs_datasets/ipfs_datasets_py/logic/modal/codec.py",
                ],
                "pre_patch_sha256": PRE_PATCH,
                "post_patch_sha256": post_patch,
                "diff": str(live_diff.relative_to(REPO)),
            },
            {
                "stage": "validation_evidence",
                "development_structural": [item["record_id"] for item in DEVELOPMENT_CASES],
                "shared_loss_retained": True,
                "fixed_canary": CANARY_ID,
                "final_test": "unrun",
                "native_checkers": missing_native,
            },
            {
                "stage": "activation_configuration",
                "exception_scope_rule": RULE_ID,
                "always_on_in_compiler": True,
                "t4_learned_guidance": "unactivated/unavailable",
                "arm_e": "locked",
                "parameter_action": False,
            },
            {
                "stage": "rollback_identity",
                "restore_pre_patch_blobs": PRE_PATCH,
                "post_patch_blobs": post_patch,
                "applied_learning_rollback_performed": False,
                "note": (
                    "Rollback is restoration of the two pre-patch codec blobs. "
                    "This is not rollback of a T4 learned effect; AF-013 default "
                    "reset remains an actual compiler reset."
                ),
            },
        ],
        "rejected_patches": rejected,
        "review_cost": {
            "unit": "sealed_path_python_process",
            "native_checker_calls": 0,
            "provider_calls": 0,
            "final_test_opens": 0,
            "synthesis_calls": 0,
        },
    }

    validation = {
        "schema": SCHEMA_VALIDATION,
        "task_id": TASK_ID,
        "suite_id": SUITE_ID,
        "started_at": started,
        "finished_at": utc_now(),
        "all_structural_contracts_passed": all_passed,
        "rule_id": RULE_ID,
        "environment": {
            "python_executable": sys.executable,
            "python_version": sys.version.split()[0],
            "path": os.environ.get("PATH", ""),
            "home": os.environ.get("HOME", ""),
            "home_is_validation_private": Path(os.environ.get("HOME", "")).name.startswith(
                "ipfs-accelerate-validation-home-"
            ),
        },
        "baseline": {
            "starting_arm": STARTING_ARM,
            "status": "unactivated/unavailable",
            "source": "AF-013 consumer_activation.json",
            "e_locked": True,
            "pre_patch_sha256": PRE_PATCH,
            "mp09_defect": BASELINE_MP09,
        },
        "development": development_views,
        "shared_loss": shared_loss,
        "canary": {
            "canary_id": canary["canary_id"],
            "sha256": canary["sha256"],
            "n_records": canary["n_records"],
            "used_for_patch_selection": False,
            "distinct_from_final_test": True,
            "formula_count_sum": sum(item["formula_count"] for item in canary["observations"]),
            "exception_formula_count_sum": sum(
                item["exception_formula_count"] for item in canary["observations"]
            ),
            "all_compiled": all(item["compiled"] for item in canary["observations"]),
        },
        "final_test": {
            "status": "unrun",
            "opened": False,
            "used_for_patch_selection": False,
            "natural_source_units": 1913,
        },
        "native_checkers": native,
        "missing_native_checkers": missing_native,
        "activation": {
            "exception_scope_rule": RULE_ID,
            "t4_learned_guidance": "unactivated/unavailable",
            "parameter_action": False,
            "executable_change": True,
        },
        "rollback_identity": {
            "pre_patch_sha256": PRE_PATCH,
            "post_patch_sha256": post_patch,
            "applied_learning_rollback_performed": False,
        },
        "rejected_patches": rejected,
        "claim_limits": [
            "Structural compiler contracts on constructed development witnesses are not original-source semantic gold.",
            "No native checker proof was executed.",
            "T5 unseen fidelity and native checked coverage remain unrun.",
            "No accepted improvement is a valid measured outcome.",
            "Unexecuted synthesis remains unrun.",
            "Human agreement and independent source-semantic fidelity remain unmeasured.",
        ],
        "structural_evidence_scope": (
            "papers/completion/autoformalization/config/structural_evidence_scope.json"
        ),
    }

    write_jsonl(live_results, development_rows)
    write_json(live_trace, trace)
    write_json(live_validation, validation)

    snapshot_root = HERE
    mapping = {
        live_results: snapshot_root / "runs" / "compiler_repair" / "results.jsonl",
        live_trace: snapshot_root / "evidence" / "repair_task_trace.json",
        live_validation: snapshot_root / "evidence" / "repair_validation.json",
        live_diff: snapshot_root / "evidence" / "compiler_patch.diff",
        spacy_path: snapshot_root
        / "external/ipfs_datasets/ipfs_datasets_py/optimizers/logic_theorem_optimizer/spacy_modal_codec.py",
        codec_path: snapshot_root
        / "external/ipfs_datasets/ipfs_datasets_py/logic/modal/codec.py",
    }
    for source, dest in mapping.items():
        if not source.is_file():
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(source.read_bytes())

    summary = {
        "suite_id": SUITE_ID,
        "task_id": TASK_ID,
        "all_structural_contracts_passed": all_passed,
        "rule_id": RULE_ID,
        "results": str(live_results),
        "trace": str(live_trace),
        "validation": str(live_validation),
        "canary_id": CANARY_ID,
        "missing_native_checkers": missing_native,
        "accepted_improvement_is_measured_outcome": False,
        "final_test": "unrun",
        "t4": "unactivated/unavailable",
    }
    print(json.dumps(summary, sort_keys=True))
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
