"""Prepare and publish source-only stage diagnostics from frozen saved lanes.

This wrapper reads weak TRAIN proposal metadata. It never opens a query
reference panel or human review package. Producer subset receipts transcribe
historical artifact associations; they are not new runtime attestations.
"""
from __future__ import annotations

import hashlib
import importlib.abc
import json
import math
import os
import stat
import sys
import time
import types
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPO = ROOT / "external/ipfs_datasets"
CAMPAIGN = Path(__file__).resolve().parent
OUTPUT = CAMPAIGN / "stage-workflow-01"
MAX_FILE_BYTES = 16 * 1024**2
MAX_AGGREGATE_BYTES = 64 * 1024**2
VIEWS = ("legacy8_raw", "native384_raw", "native768_raw")
PINS = {
    "prior_validation": ("representation-boundary-01/validation.json", "f9cbd4a7daf87304ee187b0dac242777ba1f9f93769b7c401a893948d7e9055e"),
    "legacy8_raw": ("representation-boundary-01/legacy8_raw_bundle.json", "b390d5b8b829ae08b1566e498170a083e79501f192d0080f9e1bca476b5bc83c"),
    "native384_raw": ("representation-boundary-01/native384_raw_bundle.json", "dc5bfd8c077bca2b28d0a924be71fc0d54840a07be610e071186664af2394570"),
    "native768_raw": ("representation-boundary-01/native768_raw_bundle.json", "6f93cfa4cccb67935bb12b61847df26d96cb6e6ae7acdf94596d2e5867a0c8b3"),
    "historical_expected": ("representation-boundary-01/expected_bindings.json", "1305b06acf37d094122c0db7f96095b0be9ab1d94f650c4f3600c5834b1ed82f"),
    "source_context_joins": ("representation-boundary-01/source_context_joins.json", "d435e13c8477c7d767040a5736e2845991a577b09b8654e19d8bbb491be1d1d6"),
    "train_weak_supervision": ("canonical-codec-01/train_weak_supervision.json", "97a333821790db1ad11a542f918a32e583b9b4ab150b82cdd71bbd883bbc42ba"),
}
CODE_PATHS = {
    "assay_runner": Path(__file__),
    "lane_owner": REPO / "ipfs_datasets_py/logic/formalization/autoencoder/alignment_lane_bundle.py",
    "stage_owner": REPO / "ipfs_datasets_py/logic/formalization/autoencoder/alignment_stage_declarations.py",
    "raw_ranking_owner": REPO / "ipfs_datasets_py/logic/formalization/autoencoder/alignment_raw_ranking.py",
    "workflow_owner": REPO / "ipfs_datasets_py/logic/formalization/autoencoder/alignment_stage_workflow.py",
    "workflow_cli": REPO / "scripts/ops/autoencoder/run_alignment_stage.py",
}
FORBIDDEN = {"torch", "numpy", "scipy", "transformers", "sentence_transformers", "spacy", "safetensors",
             "tensorflow", "jax", "lean", "z3", "cvc5"}
READ_TOTAL = 0


def require(condition, message):
    if not condition:
        raise ValueError(message)


def raw(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(raw(value)).hexdigest()


def seal(value):
    require("content_sha256" not in value, "cannot reseal an already sealed value")
    return {**value, "content_sha256": digest(value)}


def strict_json(data):
    def pairs(values):
        result = {}
        for key, value in values:
            require(key not in result, "duplicate JSON key")
            result[key] = value
        return result

    def invalid(value):
        raise ValueError("nonfinite JSON scalar: " + value)

    def finite(value):
        result = float(value)
        require(math.isfinite(result), "finite JSON number required")
        return result

    result = json.loads(data.decode("utf-8", errors="strict"), object_pairs_hook=pairs,
                        parse_constant=invalid, parse_float=finite)
    raw(result)
    return result


def identity(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def read_file(path, expected_sha256=None, *, parse=True):
    global READ_TOTAL
    path = Path(path).absolute()
    require(all(not parent.is_symlink() for parent in (path, *path.parents)), "symlink input forbidden")
    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0))
    try:
        before = os.fstat(descriptor)
        require(stat.S_ISREG(before.st_mode) and 0 < before.st_size <= MAX_FILE_BYTES,
                "bounded ordinary input required")
        READ_TOTAL += before.st_size
        require(READ_TOTAL <= MAX_AGGREGATE_BYTES, "assay aggregate read bound exceeded")
        chunks, count, hasher = [], 0, hashlib.sha256()
        while chunk := os.read(descriptor, 1024 * 1024):
            count += len(chunk)
            require(count <= MAX_FILE_BYTES, "input grew beyond byte bound")
            hasher.update(chunk)
            if parse:
                chunks.append(chunk)
        after = os.fstat(descriptor)
        require(count == before.st_size and identity(before) == identity(after) == identity(path.lstat()),
                "input changed during bounded read")
    finally:
        os.close(descriptor)
    observed = {"path": str(path), "bytes": count, "sha256": hasher.hexdigest()}
    require(expected_sha256 is None or observed["sha256"] == expected_sha256, "selected file SHA differs")
    return strict_json(b"".join(chunks)) if parse else None, observed


def check_seal(value):
    require(type(value) is dict, "sealed JSON object required")
    for name in ("content_sha256", "payload_sha256"):
        if name in value:
            require(value[name] == digest({key: item for key, item in value.items() if key != name}),
                    "historical JSON seal differs")


class RejectOptional(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".", 1)[0] in FORBIDDEN:
            raise ImportError("optional numerical/prover stack forbidden in saved-lane assay")
        return None


def owners():
    require(not FORBIDDEN.intersection(sys.modules), "optional numerical/prover stack already imported")
    if not any(type(finder) is RejectOptional for finder in sys.meta_path):
        sys.meta_path.insert(0, RejectOptional())
    sys.path.insert(0, str(REPO))
    for name, relative in (("ipfs_datasets_py", "ipfs_datasets_py"), ("ipfs_datasets_py.logic", "ipfs_datasets_py/logic"),
                           ("ipfs_datasets_py.logic.formalization", "ipfs_datasets_py/logic/formalization"),
                           ("ipfs_datasets_py.logic.formalization.autoencoder", "ipfs_datasets_py/logic/formalization/autoencoder")):
        if name not in sys.modules:
            module = types.ModuleType(name)
            module.__path__ = [str(REPO / relative)]
            module.__package__ = name
            sys.modules[name] = module
    from ipfs_datasets_py.logic.formalization.autoencoder import alignment_lane_bundle as lane
    from ipfs_datasets_py.logic.formalization.autoencoder import (
        alignment_stage_declarations as core,
    )
    require(Path(lane.__file__).resolve() == CODE_PATHS["lane_owner"].resolve()
            and Path(core.__file__).resolve() == CODE_PATHS["stage_owner"].resolve(), "exact canonical owner checkout required")
    return lane, core


def subset(bundle, ids):
    result = deepcopy(bundle)
    result["rows"] = [row for row in result["rows"] if row["id"] in ids]
    producer = result["producer_receipt"]
    producer["rows"] = [row for row in producer["rows"] if row["id"] in ids]
    producer.pop("content_sha256")
    result["producer_receipt"] = seal(producer)
    result.pop("content_sha256")
    result = seal(result)
    expected = {"profile_sha256": digest(result["profile"]),
                "producer_receipt_sha256": digest(result["producer_receipt"]),
                "inputs": [{"id": row["id"], "input_sha256": row["input_sha256"]} for row in result["rows"]]}
    return result, expected


def source_row(row):
    return {"id": row["id"], "input_sha256": row["input_sha256"], "representation_sha256": row["vector_sha256"],
            "status": row["status"], "reason": row["reason"]}


def prepare_assay():
    """Return exact input payloads and selected historical pins without writing."""
    global READ_TOTAL
    READ_TOTAL = 0
    lane, core = owners()
    values, selected = {}, {}
    for name, (relative, sha) in PINS.items():
        values[name], selected[name] = read_file(CAMPAIGN / relative, sha)
        check_seal(values[name])
    code = {name: read_file(path, parse=False)[1] for name, path in CODE_PATHS.items()}
    train = values["train_weak_supervision"]
    require(train["split"] == "train" and train["row_count"] == len(train["rows"]) == 16,
            "frozen weak TRAIN manifest differs")
    train_rows = {row["id"]: row for row in train["rows"]}
    require(len(train_rows) == 16, "unique TRAIN identities required")
    original_masks = {row["id"]: deepcopy(row["masks"]) for row in train["rows"]}
    require(all(masks == {name: int(name == "weak_decoder_fit") for name in lane.MASKS}
                for masks in original_masks.values()), "historical weak masks differ")
    formal = {key: digest(row["proposal"]["canonical_ir"]) for key, row in train_rows.items()}
    require(len(set(formal.values())) == 16, "sixteen distinct weak formal identities required")
    all_ids = {row["id"] for row in values[VIEWS[0]]["rows"]}
    require(len(all_ids) == 34 and set(train_rows) <= all_ids, "TRAIN/source lane membership differs")
    query_ids = all_ids - set(train_rows)
    require(len(query_ids) == 18, "complete eighteen-query membership required")
    joins = {row["id"]: row for row in values["source_context_joins"]["rows"]}
    require(set(joins) == all_ids, "saved context join membership differs")
    inputs, prepared_views, norms = {}, {}, {}
    policy = seal({"schema": "alignment-ranking-policy/v1", "mode": "raw_source_to_source", "top_k": 3,
                   "tie_break": core.TIE_BREAK})
    for view in VIEWS:
        bundle = values[view]
        require({row["id"] for row in bundle["rows"]} == all_ids, "raw lane identity coverage differs")
        lane.validate_lane_bundle(bundle, expected_bindings=values["historical_expected"]["views"][view])
        artifact = bundle["producer_receipt"]["artifact_binding"]
        _, selected[view + "_historical_producer_artifact"] = read_file(artifact["path"], artifact["sha256"], parse=False)
        require(selected[view + "_historical_producer_artifact"] == artifact, "historical producer file binding differs")
        by_id = {row["id"]: row for row in bundle["rows"]}
        for key in train_rows:
            require(hashlib.sha256(by_id[key]["input"]["source_text"].encode("utf-8")).hexdigest()
                    == train_rows[key]["source_sha256"] == joins[key]["source_sha256"], "TRAIN source join differs")
        for key, row in by_id.items():
            require(row["input_sha256"] == joins[key]["explicit_envelope_input_sha256"], "full input recipe join differs")
            require(hashlib.sha256(row["input"]["source_text"].encode("utf-8")).hexdigest() == joins[key]["source_sha256"]
                    and row["input"]["context"]["sha256"] == joins[key]["context_sha256"]
                    and row["input"]["context"]["role"] == joins[key]["context_role"]
                    and key == "sha256:" + joins[key]["historical_authored_input_sha256"],
                    "complete saved source/context/historical identity join differs")
        train_bundle, train_expected = subset(bundle, set(train_rows))
        query_bundle, query_expected = subset(bundle, query_ids)
        train_validation = lane.validate_lane_bundle(train_bundle, expected_bindings=train_expected)
        query_validation = lane.validate_lane_bundle(query_bundle, expected_bindings=query_expected)
        bank = seal({"schema": "alignment-frozen-train-bank/v1", "lane_validation": train_validation,
                     "file_binding": None, "rows": [{**source_row(row), "split": "train", "formal_view_sha256": formal[row["id"]]}
                                                       for row in train_bundle["rows"]]})
        queries = seal({"schema": "alignment-target-free-queries/v1", "file_binding": None,
                        "rows": [source_row(row) for row in query_bundle["rows"]]})
        roles = {"lane_validation": query_validation, "queries": queries, "frozen_bank": bank,
                 "ranking_policy": policy, "checkpoint_binding": None}
        declaration = seal({"schema": core.RANK_SCHEMA, **roles})
        expected = core._bindings(roles)
        core.validate_rank_declaration(declaration, expected_bindings=expected)
        payloads = {"train_bundle": train_bundle, "query_bundle": query_bundle,
                    "train_expected_bindings": train_expected, "query_expected_bindings": query_expected,
                    "rank_declaration": declaration, "rank_expected_bindings": expected}
        for name, payload in payloads.items():
            inputs[f"{view}_{name}.json"] = payload
        prepared_views[view] = {"declaration": declaration, "expected_bindings": expected,
                                "bank": bank, "train_bundle": train_bundle, "query_bundle": query_bundle}
        observed_norms = {key: math.hypot(*row["vector"]) for key, row in by_id.items() if row["vector"] is not None}
        norms[view] = {"available_count": sum(row["status"] == "available" for row in bundle["rows"]),
                       "unavailable_count": sum(row["status"] == "unavailable" for row in bundle["rows"]),
                       "zero_train_count": sum(observed_norms.get(key) == 0 for key in train_rows),
                       "zero_query_count": sum(observed_norms.get(key) == 0 for key in query_ids),
                       "minimum_norm": min(observed_norms.values()), "maximum_norm": max(observed_norms.values())}
    chosen = prepared_views["native384_raw"]
    manifest = seal({"schema": "alignment-train-manifest/v1", "file_binding": None,
                     "rows": [{**row, "masks": dict.fromkeys(lane.MASKS, 0)} for row in chosen["bank"]["rows"]]})
    fit_policy = seal({"schema": "alignment-fit-policy/v1", "relation_policy": core.RELATION_POLICY,
                       "checkpoint_selection": "fixed_final_step",
                       "budget": {"trial_count": 12, "steps_per_trial": 80, "max_seconds": 300}})
    fit_roles = {"lane_validation": chosen["bank"]["lane_validation"], "train_manifest": manifest, "fit_policy": fit_policy}
    inputs["fit_declaration.json"] = seal({"schema": core.FIT_SCHEMA, **fit_roles})
    inputs["fit_expected_bindings.json"] = core._bindings(fit_roles)
    core.validate_fit_declaration(inputs["fit_declaration.json"], expected_bindings=inputs["fit_expected_bindings.json"])
    diagnostics = {"train_count": 16, "query_count": 18, "train_id_query_id_overlap_count": 0,
                   "train_formal_identity_count": 16, "views": norms}
    for field, name in (("source_sha256", "exact_source"), ("explicit_envelope_input_sha256", "exact_full_input"),
                        ("historical_authored_input_sha256", "historical_authored_input")):
        a, b = {joins[key][field] for key in train_rows}, {joins[key][field] for key in query_ids}
        diagnostics[name] = {"train_unique_count": len(a), "query_unique_count": len(b), "overlap_count": len(a & b)}
        require(not a & b, "exact source/input TRAIN-query overlap")
    return {"inputs": inputs, "selected_input_bindings": selected, "code_bindings": code,
            "views": prepared_views, "split_diagnostics": diagnostics,
            "original_train_masks": original_masks,
            "subset_provenance": {"scope": "producer_subset_transcription_of_pinned_historical_artifact_associations",
                                  "producer_runtime_attestation_established": False,
                                  "profile_and_vector_values_preserved": True,
                                  "historical_input_sha_recipe": values["source_context_joins"]["historical_input_sha_recipe"],
                                  "explicit_input_sha_recipe": values["source_context_joins"]["explicit_input_sha_recipe"]},
            "parent_train_proposal_metadata_read": True, "query_reference_panel_accessed": False,
            "human_review_packages_accessed": False, "reference_paths_forwarded_to_rank_child": False}


def prepare_score_inputs(saved):
    """Construct unavailable-reference score roles from a durable ranking only."""
    _, core = owners()
    references = seal({"schema": "alignment-scoring-reference-bindings/v1", "file_binding": None,
                       "rows": [{"id": row["id"], "input_sha256": row["input_sha256"], "reference_sha256": None,
                                 "admission_receipt_sha256": None, "fidelity_evaluation": 0, "status": "unavailable",
                                 "reason": "independently admitted fidelity reference unavailable; no reference panel opened"}
                                for row in saved["rows"]]})
    policy = seal({"schema": "alignment-score-policy/v1", "reference_policy": "admitted_references_only/v1",
                   "metric_policy": "not_implemented/v1"})
    roles = {"saved_rankings": saved, "frozen_bank": saved["rank_declaration"]["frozen_bank"],
             "references": references, "score_policy": policy}
    declaration, expected = seal({"schema": core.SCORE_SCHEMA, **roles}), core._bindings(roles)
    core.validate_score_declaration(declaration, expected_bindings=expected)
    return {"score_declaration.json": declaration, "score_expected_bindings.json": expected,
            "unavailable_reference_bindings.json": references}


def save(path, value):
    data = raw(value) + b"\n"
    require(len(data) <= MAX_FILE_BYTES, "bounded output required")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        os.fchmod(stream.fileno(), 0o600)
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return {"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def recheck(bindings):
    for binding in bindings.values():
        require(read_file(binding["path"], binding["sha256"], parse=False)[1] == binding,
                "selected bytes changed before publication")


def main():
    started = time.monotonic()
    prepared = prepare_assay()
    from ipfs_datasets_py.logic.formalization.autoencoder.alignment_stage_workflow import (
        run_alignment_stage,
    )
    require(Path(sys.modules[run_alignment_stage.__module__].__file__).resolve()
            == CODE_PATHS["workflow_owner"].resolve(), "exact workflow owner checkout required")
    require(not OUTPUT.exists(), "fresh immutable stage-workflow-01 directory required")
    recheck(prepared["selected_input_bindings"])
    recheck(prepared["code_bindings"])
    OUTPUT.mkdir(mode=0o700)
    directory = OUTPUT / "inputs"
    directory.mkdir(mode=0o700)
    input_files = {name: save(directory / name, value) for name, value in prepared["inputs"].items()}
    plan = save(OUTPUT / "plan.json", seal({"schema": "alignment-stage-workflow-assay-plan/v1",
        "created_utc": datetime.now(UTC).isoformat(), "selected_input_bindings": prepared["selected_input_bindings"],
        "code_bindings": prepared["code_bindings"], "input_file_bindings": input_files,
        "split_diagnostics": prepared["split_diagnostics"], "subset_provenance": prepared["subset_provenance"],
        "top_k": 3, "views": list(VIEWS), "proposed_fit_updates": 960, "worker_timeout_seconds": 30,
        "ranking_execution_policy": "raw_saved_source_cosine_only", "fit_and_score_execution_policy": "blocked",
        "parent_train_proposal_metadata_read": True, "query_reference_panel_accessed": False,
        "human_review_packages_accessed": False, "os_sandbox": False, "physical_reference_inaccessibility_established": False}))
    artifacts = {}
    reports = {}
    for view in VIEWS:
        report = run_alignment_stage("rank", input_files[f"{view}_rank_declaration.json"],
            input_files[f"{view}_rank_expected_bindings.json"], OUTPUT / (view + "_rank"),
            lane_bundle_selections={"query_bundle": input_files[f"{view}_query_bundle.json"],
                                    "expected_query_lane": input_files[f"{view}_query_expected_bindings.json"],
                                    "bank_bundle": input_files[f"{view}_train_bundle.json"],
                                    "expected_bank_lane": input_files[f"{view}_train_expected_bindings.json"]},
            worker_timeout_seconds=30)
        report_binding = read_file(OUTPUT / (view + "_rank") / "report.json")[1]
        artifacts[view] = {"rank_report_binding": report_binding,
                           "saved_rankings_binding": report["artifacts"]["saved_rankings"],
                           "rank_receipt_binding": report["artifacts"]["validation"],
                           "raw_ranking_diagnostic_binding": report["artifacts"]["raw_ranking_diagnostic"]}
        reports[view] = report
    fit = run_alignment_stage("fit", input_files["fit_declaration.json"], input_files["fit_expected_bindings.json"],
                              OUTPUT / "fit_blocked", worker_timeout_seconds=30)
    fit_report_binding = read_file(OUTPUT / "fit_blocked/report.json")[1]
    saved_binding = artifacts["native384_raw"]["saved_rankings_binding"]
    saved, observed = read_file(saved_binding["path"], saved_binding["sha256"])
    require(observed == saved_binding, "durable selected ranking bytes differ")
    score_inputs = prepare_score_inputs(saved)
    score_files = {name: save(directory / name, value) for name, value in score_inputs.items()}
    input_files.update(score_files)
    score = run_alignment_stage("score", input_files["score_declaration.json"], input_files["score_expected_bindings.json"],
        OUTPUT / "score_blocked", saved_rankings_binding=saved_binding,
        reference_bundle_binding=input_files["unavailable_reference_bindings.json"], worker_timeout_seconds=30)
    score_report_binding = read_file(OUTPUT / "score_blocked/report.json")[1]
    stats = {"ranked_query_count": 0, "unavailable_rank_query_count": 0, "top_k_hit_count": 0,
             "rank_views": {}, "model_calls": 0, "encoder_calls": 0, "prover_calls": 0, "optimizer_updates": 0,
             "fidelity_scores_created": 0, "proposed_fit_updates": 960}
    for view in VIEWS:
        ranking, binding = read_file(artifacts[view]["saved_rankings_binding"]["path"],
                                     artifacts[view]["saved_rankings_binding"]["sha256"])
        require(binding == artifacts[view]["saved_rankings_binding"], "saved rank binding differs")
        rows = ranking["rows"]
        count = {"query_count": len(rows), "available_count": sum(row["status"] == "available" for row in rows),
                 "unavailable_count": sum(row["status"] == "unavailable" for row in rows),
                 "top_k_hit_count": sum(len(row["hits"]) for row in rows), "frozen_candidate_count": 16}
        require(count["query_count"] == 18 and count["available_count"] == 18 and count["top_k_hit_count"] == 54,
                "actual saved ranking completeness differs")
        stats["rank_views"][view] = count
        stats["ranked_query_count"] += count["available_count"]
        stats["unavailable_rank_query_count"] += count["unavailable_count"]
        stats["top_k_hit_count"] += count["top_k_hit_count"]
    fit_receipt, _ = read_file(fit["artifacts"]["validation"]["path"], fit["artifacts"]["validation"]["sha256"])
    score_receipt, _ = read_file(score["artifacts"]["validation"]["path"], score["artifacts"]["validation"]["sha256"])
    require(fit_receipt["status"] == "blocked_no_contrastive_admission"
            and fit_receipt["proposed_optimizer_updates"] == 960, "blocked fit accounting differs")
    require(score_receipt["status"] == "blocked_no_admitted_fidelity_references"
            and score_receipt["unavailable_reference_count"] == 18 and score_receipt["scored_query_count"] == 0,
            "blocked scoring accounting differs")
    all_reports = {**reports, "fit": fit, "score": score}
    for name, result in all_reports.items():
        require(all(type(result[key]) is int and result[key] == 0 for key in (
                    "model_calls", "encoder_calls", "prover_calls", "optimizer_updates", "fidelity_scores_created")),
                "workflow cannot claim model/prover/optimizer/fidelity execution")
        require(result["ranking_operation_executed"] is (name in VIEWS)
                and result["training_executed"] is False and result["scoring_executed"] is False,
                "workflow operation scope differs")
        require(result["os_sandbox"] is False and result["child_isolation"] == "trusted_resource_bounded_subprocess",
                "workflow cannot claim physical confinement")
        require(all(type(value) is int and value == 0 for value in result["masks"].values()),
                "workflow masks must stay zero")
    stats["fit_status"] = fit_receipt["status"]
    stats["score_status"] = score_receipt["status"]
    stats["unavailable_fidelity_reference_count"] = score_receipt["unavailable_reference_count"]
    stats["worker_cpu_seconds"] = math.fsum(result["worker_usage"]["cpu_seconds"] for result in all_reports.values())
    stats["maximum_worker_peak_rss_kib"] = max(result["worker_usage"]["peak_rss_kib"] for result in all_reports.values())
    all_bindings = {"plan": plan, **{"input:" + name: binding for name, binding in input_files.items()},
                    "fit_report": fit_report_binding, "fit_receipt": fit["artifacts"]["validation"],
                    "score_report": score_report_binding, "score_receipt": score["artifacts"]["validation"]}
    for view, entries in artifacts.items():
        all_bindings.update({view + ":" + name: binding for name, binding in entries.items()})
    recheck(prepared["selected_input_bindings"])
    recheck(prepared["code_bindings"])
    recheck(all_bindings)
    require(not FORBIDDEN.intersection(sys.modules), "optional numerical/prover import occurred")
    report = seal({"schema": "alignment-stage-workflow-assay/v1", "created_utc": datetime.now(UTC).isoformat(),
        "status": "completed_static_input_preparation_and_raw_ranking_diagnostics_only", "plan_binding": plan,
        "selected_input_bindings": prepared["selected_input_bindings"], "code_bindings": prepared["code_bindings"],
        "input_file_bindings": input_files, "artifacts": artifacts,
        "fit_report_binding": fit_report_binding, "fit_receipt_binding": fit["artifacts"]["validation"],
        "score_report_binding": score_report_binding, "score_receipt_binding": score["artifacts"]["validation"],
        "all_input_artifact_bindings": all_bindings, "stats": stats, "split_diagnostics": prepared["split_diagnostics"],
        "subset_provenance": prepared["subset_provenance"], "original_train_masks": prepared["original_train_masks"],
        "new_stage_masks": {"weak_decoder_fit": 0, "strong_semantic_fit": 0, "contrastive_supervision": 0,
                            "proof_supervision": 0, "fidelity_evaluation": 0},
        "worker_reports": all_reports,
        "raw_ranking_operation_executed": True, "parent_train_proposal_metadata_read": True,
        "query_reference_panel_accessed": False, "human_review_packages_accessed": False,
        "query_reference_hashes_derived_from_old_panel": False, "rank_child_formal_payload_forwarded": False,
        "reference_paths_forwarded_to_rank_child": False, "optional_numerical_prover_imports_absent": True,
        "selected_historical_and_code_files_rechecked": True, "full_preservation_chain_rechecked": False,
        "os_sandbox": False, "physical_reference_inaccessibility_established": False,
        "self_or_derivative_exclusion_verified": False, "split_provenance_authenticated": False,
        "producer_runtime_attestation_established": False, "source_fidelity_established": False,
        "semantic_label_admission": False, "proof_authority": False, "qualified": False, "accepted": False,
        "training_executed": False, "scoring_executed": False, "wall_seconds": time.monotonic() - started,
        "observed_input_bytes_including_rechecks": READ_TOTAL})
    binding = save(OUTPUT / "assay.json", report)
    for published_directory in (directory, OUTPUT):
        descriptor = os.open(published_directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    print(json.dumps({"status": report["status"], "assay_binding": binding, "stats": stats}, sort_keys=True))


if __name__ == "__main__":
    main()
