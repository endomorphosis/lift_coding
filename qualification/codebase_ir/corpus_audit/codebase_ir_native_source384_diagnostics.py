#!/usr/bin/env python3
"""Read selected public native source384 exports without numerical execution."""
from __future__ import annotations

import argparse
import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import codebase_ir_corpus_audit as audit
import codebase_ir_final_evaluation as final
import codebase_ir_final_lock as lock_tool

INPUT_SCHEMA = "codebase-ir-native-source384-diagnostics-input@1"
REPORT_SCHEMA = "codebase-ir-native-source384-diagnostics@1"
ROLES = ("learned", "zero_head", "source_label_baseline", "qualification")
SELECTORS = {"learned": "public/actual-learned.json", "zero_head": "public/actual-zero_head.json",
             "source_label_baseline": "public/model-off-baseline.json", "qualification": "qualification.json"}
FALSE_FLAGS = {"native_execution_performed", "training_executed", "current_authority_claimed",
               "model_selection_performed", "promotion_performed", "candidate_model_qualified",
               "producer_authentication_verified", "numerical_provenance_verified", "source_semantics_verified",
               "source_derived_accuracy_available", "heldout_independence_verified", "learned_weight_dependence_verified",
               "git_object_custody_verified", "preconstraint_raw_output_available", "checker_execution_replayed"}
INFERENCE_FLAGS = {"admitted", "claim_proved", "completion_authority", "execution_authority", "proof_authority",
                   "publication_performed", "qualified", "security_specification_inferred", "source_semantics_verified",
                   "whole_program_semantics_verified"}
ROW_FIELDS = {"admitted", "candidate_ir", "claim_proved", "completion_authority", "continue_planning", "execution_authority",
              "head_sha256", "id", "predicted_classes", "projected_embedding", "projection_sha256", "proof_authority",
              "publication_performed", "qualified", "reason", "security_specification_inferred", "source_contract",
              "source_semantics_verified", "source_sha256", "status", "whole_program_semantics_verified"}
OPTIONAL_METADATA = {"target_access", "teacher_forcing", "weight_ablation"}
CONTRACT_FIELDS = {"assumptions", "base_qualification_sha256", "candidate_sha256", "checks", "completion_authority",
                   "executes_source", "execution_authority", "projections", "proof_authority", "provider_calls",
                   "qualification_gaps", "qualified", "schema", "security_specification_inferred", "solver_calls",
                   "source_binding", "source_semantics_verified", "source_sha256", "status", "whole_program_semantics_verified"}
BASELINE_ROW_FIELDS = {"admitted", "candidate_sha256", "claim_proved", "completion_authority", "execution_authority",
                       "formalized", "id", "lake_status", "lean_declarations_sha256", "lowering", "parser_status",
                       "program_sha256", "promotion_performed", "proof_authority", "reason", "security_specification_inferred",
                       "semantic_lowering_supported", "source_qualification", "source_semantics_verified", "source_sha256",
                       "whole_program_semantics_verified"}
QUALIFICATION_FIELDS = {"archive_integrity", "attempts", "blocking_dependencies", "checkpoint", "criterion",
                        "frozen_production_modules_changed", "mapping", "prior_evidence", "prior_evidence_sha256",
                        "privacy", "production_acceptance", "profile", "promotion_performed", "proposed_criterion_acceptance",
                        "resource_admission", "schema", "scope_limits", "seconds", "skips", "test_file", "test_sha256",
                        "tests", "training_executed"}


@dataclass(frozen=True)
class Limits:
    max_files: int = 6
    max_file_bytes: int = 1024 * 1024
    max_total_bytes: int = 8 * 1024 * 1024
    max_rows: int = 32
    max_manifest_children: int = 64

    def __post_init__(self):
        audit._require(all(type(value) is int and value > 0 for value in asdict(self).values()), "positive exact diagnostics limits required")


DEFAULT_LIMITS = Limits()


class Pins:
    def __init__(self, limits):
        self.limits, self.files, self.total, self.identities = limits, {}, 0, set()

    def read(self, path, maximum):
        audit._require(path not in self.files, "aliased diagnostics input selector")
        audit._require(len(self.files) < self.limits.max_files, "diagnostics file budget exceeded")
        remaining = self.limits.max_total_bytes - self.total
        audit._require(remaining >= 0, "diagnostics aggregate byte budget exceeded")
        raw = final.Capture.regular(path, min(maximum, self.limits.max_file_bytes, remaining))
        identity = path.stat(follow_symlinks=False)
        key = identity.st_dev, identity.st_ino
        audit._require(key not in self.identities, "hard-linked diagnostics input alias")
        self.identities.add(key)
        self.files[path] = raw
        self.total += len(raw)
        return raw

    def descriptor(self, value):
        audit._closed(value, {"path", "sha256", "size_bytes"}, "native external descriptor")
        path = Path(audit._text(value["path"], "native input path", 4096))
        audit._require(path.is_absolute() and str(path) == value["path"], "canonical absolute native input required")
        audit._digest(value["sha256"], "native input SHA")
        size = value["size_bytes"]
        audit._require(type(size) is int and 0 <= size <= self.limits.max_file_bytes, "exact bounded native descriptor required")
        raw = self.read(path, size)
        audit._require(len(raw) == size and audit._sha(raw) == value["sha256"], "native external pin mismatch")
        return path, raw

    def recheck(self):
        for path, raw in self.files.items():
            audit._require(final.Capture.regular(path, len(raw)) == raw, "native selected input drifted")


def _json(raw, limits):
    return audit._load_json(raw, audit.Limits(max_json_bytes=limits.max_file_bytes, max_json_nodes=100_000))


def _boolean(value, label):
    audit._require(type(value) is bool, "exact recorded Boolean required: " + label)


def _nonnegative(value, label):
    audit._require(type(value) is int and value >= 0, "exact recorded nonnegative integer required: " + label)


def _finite_number(value):
    # JSON integers are unbounded. Avoid float coercion of a huge integer and
    # preserve a bounded portable numerical layout for recorded projections.
    return abs(value) <= 2**53 if type(value) is int else type(value) is float and math.isfinite(value)


def _closed_optional(value, required, optional, label):
    audit._require(type(value) is dict and required <= set(value) <= required | optional, "closed " + label + " fields required")


def _contract(value, source_sha, candidate_sha):
    _closed_optional(value, CONTRACT_FIELDS, {"reason"}, "native source contract")
    if value.get("reason") is not None:
        audit._text(value["reason"], "recorded native contract reason", 2048)
    audit._require(value["schema"] == "security-source-program-binding-384/v2", "native source contract v2 required")
    audit._require(value["source_sha256"] == source_sha and value["candidate_sha256"] == candidate_sha,
                   "native row/contract source or candidate binding mismatch")
    for key in ("source_sha256", "candidate_sha256", "base_qualification_sha256"):
        audit._digest(value[key], "native contract " + key)
    for key in ("executes_source", "completion_authority", "execution_authority", "proof_authority", "qualified",
                "security_specification_inferred", "source_semantics_verified", "whole_program_semantics_verified"):
        _boolean(value[key], key)
        if key != "qualified":
            audit._require(value[key] is False, "public native contract authority/source claim outside diagnostics profile")
    for key in ("provider_calls", "solver_calls"):
        _nonnegative(value[key], key)
    audit._text(value["status"], "recorded source contract status")
    audit._require(type(value["checks"]) is list and len(value["checks"]) <= 32, "bounded recorded contract checks required")
    for check in value["checks"]:
        audit._closed(check, {"check", "status"}, "recorded source check")
        audit._text(check["check"], "recorded check")
        audit._text(check["status"], "recorded check status")
    for key in ("assumptions", "qualification_gaps", "projections"):
        audit._require(type(value[key]) is list and len(value[key]) <= 64, "bounded native contract inventory required")
        if key != "projections":
            for item in value[key]:
                audit._text(item, "recorded contract " + key, 2048)
    binding = value["source_binding"]
    audit._require(binding is None or type(binding) is dict, "recorded source binding object/null required")
    spans = []
    if binding is not None:
        audit._require(binding.get("source_sha256") == source_sha, "native source binding does not match row")
        spans = binding.get("spans", [])
        audit._require(type(spans) is list and len(spans) <= 32, "bounded recorded source spans required")
        for span in spans:
            audit._closed(span, {"span_id", "start_byte", "end_byte", "sha256"}, "recorded source span")
            audit._text(span["span_id"], "recorded span ID")
            audit._digest(span["sha256"], "recorded span SHA")
            audit._require(type(span["start_byte"]) is int and type(span["end_byte"]) is int
                           and 0 <= span["start_byte"] < span["end_byte"] <= 64 * 1024,
                           "bounded exact recorded source byte span required")
    return {"schema": value["schema"], "status": value["status"], "checks": value["checks"], "qualified_claim": value["qualified"],
            "source_binding_recorded": binding is not None, "recorded_spans": spans, "claim_truth_verified": False}


def _candidate(value):
    audit._closed(value, {"kind", "document"}, "native candidate")
    audit._require(type(value["kind"]) is str and type(value["document"]) is dict, "native candidate kind/document required")
    if value["kind"] != "program_expression" or value["document"].get("kind") != "binary":
        return {"status": "unsupported_codec", "kind": value["kind"], "operator": None, "type_ref": None,
                "operand_ids": None, "evaluation_order": None}
    doc = audit._closed(value["document"], {"attributes", "evaluation_order", "expression_id", "kind", "operand_ids",
                                          "operator", "source_ref_ids", "span_ids", "symbol_ids", "type_ref"}, "native binary candidate")
    audit._require(type(doc["attributes"]) is dict, "native candidate attributes object required")
    for key in ("expression_id", "operator", "type_ref"):
        audit._text(doc[key], "native candidate " + key)
    for key in ("operand_ids", "evaluation_order", "source_ref_ids", "span_ids", "symbol_ids"):
        audit._require(type(doc[key]) is list and len(doc[key]) <= 32, "bounded native candidate selector list required")
        for item in doc[key]:
            audit._text(item, "native candidate selector")
    supported = (len(doc["operand_ids"]) == 2 and doc["evaluation_order"] == doc["operand_ids"]
                 and doc["operator"] in {"+", "-", "*", "==", "!=", "<", "<=", ">", ">="}
                 and doc["type_ref"] in {"integer", "boolean"})
    return {"status": "recognized_binary_codec" if supported else "unsupported_codec",
            **{key: doc[key] for key in ("kind", "operator", "type_ref", "operand_ids", "evaluation_order")}}


def _inference(value, role, limits):
    audit._closed(value, {"result", "worker_receipt"}, "native inference envelope")
    result = audit._closed(value["result"], {"embedding_assets", "inference", "producer", "training_executed"}, "native result")
    _boolean(result["training_executed"], "native result training")
    audit._require(type(result["producer"]) is dict and type(result["embedding_assets"]) is list, "native producer/assets inventory required")
    audit._require(len(result["embedding_assets"]) <= 32, "bounded recorded embedding assets required")
    assets = set()
    for asset in result["embedding_assets"]:
        audit._closed(asset, {"bytes", "name", "sha256"}, "recorded embedding asset")
        name = audit._relative_path(asset["name"], "recorded embedding asset")
        audit._require(name not in assets, "duplicate recorded embedding asset")
        assets.add(name)
        _nonnegative(asset["bytes"], "recorded embedding asset bytes")
        audit._digest(asset["sha256"], "recorded embedding asset SHA")
    receipt = audit._closed(value["worker_receipt"], {"device", "elapsed_ms", "input_sha256", "memory_enforcement", "memory_mb",
                                                    "output_sha256", "provider_calls", "returncode", "workspace_cleaned"}, "native worker receipt")
    for key in ("input_sha256", "output_sha256"):
        audit._digest(receipt[key], "recorded receipt " + key)
    for key in ("elapsed_ms", "memory_mb", "provider_calls"):
        _nonnegative(receipt[key], key)
    audit._require(type(receipt["returncode"]) is int, "exact recorded return code required")
    _boolean(receipt["workspace_cleaned"], "recorded cleanup")
    for key in ("device", "memory_enforcement"):
        audit._text(receipt[key], "recorded receipt " + key)
    inf = audit._closed(result["inference"], INFERENCE_FLAGS | {"checkpoint_sha256", "dimension", "domain_id", "rows", "schema",
                                                             "source_contracts_checked"}, "native inference")
    audit._require(inf["schema"] == "structured-source-384-autoencoder/v1" and type(inf["dimension"]) is int
                   and inf["dimension"] == 384 and inf["domain_id"] == "security_ir", "registered native public source384 codec required")
    audit._digest(inf["checkpoint_sha256"], "claimed native checkpoint")
    for key in INFERENCE_FLAGS:
        audit._require(inf[key] is False, "native authority/source claim outside public diagnostics profile")
    _boolean(inf["source_contracts_checked"], "recorded source checks")
    rows = inf["rows"]
    audit._require(type(rows) is list and 0 < len(rows) <= limits.max_rows, "bounded nonempty native rows required")
    indexed = {}
    for row in rows:
        _closed_optional(row, ROW_FIELDS, OPTIONAL_METADATA, "native inference row")
        name = audit._digest(row["id"], "native row ID")
        audit._require(name not in indexed, "duplicate native row ID")
        for key in ("source_sha256", "head_sha256", "projection_sha256"):
            audit._digest(row[key], "native row " + key)
        for key in INFERENCE_FLAGS:
            audit._require(row[key] is False, "native row authority/source claim outside diagnostics profile")
        _boolean(row["continue_planning"], "native continue_planning")
        audit._text(row["status"], "recorded native row status")
        classes, embedding = row["predicted_classes"], row["projected_embedding"]
        audit._require(type(classes) is list and len(classes) == 4 and all(type(item) is int and 0 <= item < 4096 for item in classes),
                       "native scalar predicted class layout required")
        audit._require(type(embedding) is list and len(embedding) == 384 and all(_finite_number(item) for item in embedding),
                       "native finite 384D projection layout required")
        candidate_sha = audit._sha(audit._canonical(row["candidate_ir"]))
        contract = _contract(row["source_contract"], row["source_sha256"], candidate_sha)
        metadata = {}
        findings = []
        for key in ("target_access", "teacher_forcing"):
            if key in row:
                _boolean(row[key], key)
                metadata[key] = {"disposition": "recorded", "value": row[key], "independently_verified": False}
                if row[key]:
                    findings.append("recorded_" + key)
            else:
                metadata[key] = {"disposition": "unknown", "value": None, "independently_verified": False}
                findings.append("missing_" + key + "_metadata")
        if "weight_ablation" in row:
            audit._require(row["weight_ablation"] in {None, "zero_head"}, "known recorded ablation metadata required")
            ablation = {"disposition": "recorded", "value": row["weight_ablation"], "independently_verified": False}
            if (role == "zero_head") != (row["weight_ablation"] == "zero_head"):
                findings.append("recorded_ablation_role_mismatch")
        else:
            ablation = {"disposition": "unknown", "value": None, "independently_verified": False}
            findings.append("missing_ablation_metadata")
        indexed[name] = {"id": name, "source_sha256": row["source_sha256"], "head_sha256": row["head_sha256"],
                         "projection_sha256": row["projection_sha256"], "candidate_sha256": candidate_sha,
                         "candidate_codec": _candidate(row["candidate_ir"]), "predicted_classes": classes,
                         "returned_candidate": row["candidate_ir"], "candidate_stage": "returned_native_candidate_not_preconstraint_raw",
                         "recorded_status": row["status"], "recorded_source_contract": contract, "metadata": metadata,
                         "ablation": ablation, "findings": findings}
    return indexed, {"native_schema": inf["schema"], "claimed_checkpoint_sha256": inf["checkpoint_sha256"],
                     "producer_sha256": audit._sha(audit._canonical(result["producer"])),
                     "claimed_training_executed": result["training_executed"], "recorded_worker_receipt": receipt,
                     "worker_receipt_authenticated": False, "recorded_source_contracts_checked": inf["source_contracts_checked"]}


def _baseline(value, limits):
    audit._closed(value, {"embeddings_executed", "lake", "learned_prediction_claimed", "model_executed", "route", "source_head",
                         "target_origin", "training_executed"}, "native source-label baseline")
    for key in ("embeddings_executed", "learned_prediction_claimed", "model_executed", "training_executed"):
        audit._require(value[key] is False, "deterministic source-label baseline must retain its separate native meaning")
    audit._require(value["route"] == "deterministic_source_label_baseline_not_model_inference", "explicit native source-label baseline required")
    audit._text(value["target_origin"], "recorded source-label provenance")
    audit._require(type(value["source_head"]) is dict, "recorded baseline head required")
    lake = audit._closed(value["lake"], {"admitted", "all_candidates_compiled", "assumptions", "backend_executed", "claim_proved",
        "completion_authority", "count", "execution", "execution_authority", "formalized", "input_sha256", "lean_source",
        "lean_source_sha256", "library", "producer", "promotion_performed", "proof_authority", "rows", "schema", "scope",
        "security_specification_inferred", "source_replay_passed", "source_semantics_verified", "status", "supported_count",
        "tool_binary_sha256", "tool_pin_scope", "whole_program_semantics_verified"}, "native baseline Lake receipt")
    audit._require(lake["schema"] == "source-program-384-lake/v1", "native Lake receipt v1 required")
    for key in ("admitted", "claim_proved", "completion_authority", "execution_authority", "promotion_performed", "proof_authority",
                "security_specification_inferred", "source_semantics_verified", "whole_program_semantics_verified"):
        audit._require(lake[key] is False, "native baseline authority/source claim outside diagnostics profile")
    rows = lake["rows"]
    audit._require(type(rows) is list and 0 < len(rows) <= limits.max_rows, "bounded nonempty baseline rows required")
    audit._require(type(lake["count"]) is int and lake["count"] == len(rows), "baseline declared row count differs from population")
    _nonnegative(lake["supported_count"], "baseline supported count")
    audit._require(lake["supported_count"] <= len(rows), "baseline supported count exceeds population")
    indexed = {}
    for row in rows:
        audit._closed(row, BASELINE_ROW_FIELDS, "native baseline row")
        name = audit._digest(row["id"], "native baseline ID")
        audit._require(name not in indexed, "duplicate native baseline ID")
        for key in ("source_sha256", "candidate_sha256", "lean_declarations_sha256", "program_sha256"):
            audit._digest(row[key], "baseline " + key)
        contract = _contract(row["source_qualification"], row["source_sha256"], row["candidate_sha256"])
        for key in ("admitted", "claim_proved", "completion_authority", "execution_authority", "promotion_performed", "proof_authority",
                    "security_specification_inferred", "source_semantics_verified", "whole_program_semantics_verified"):
            audit._require(row[key] is False, "baseline row authority/source claim outside diagnostics profile")
        for key in ("parser_status", "lake_status"):
            audit._text(row[key], "recorded baseline " + key)
        indexed[name] = {"id": name, "source_sha256": row["source_sha256"], "candidate_sha256": row["candidate_sha256"],
                         "recorded_source_contract": contract, "recorded_parser_status": row["parser_status"],
                         "recorded_lake_status": row["lake_status"], "baseline_meaning": "deterministic_source_label_not_model_inference"}
    return indexed, {"route": value["route"], "target_origin_claim": value["target_origin"], "recorded_lake_status": lake["status"],
                     "source_truth_independently_verified": False, "mapped_to_final_scorer_model_off": False}


def _pair(rows):
    records = []
    for name in sorted(set().union(*(set(group) for group in rows.values()))):
        present = {role: group[name] for role, group in rows.items() if name in group}
        selected = next(iter(present.values()))
        audit._require(all(row["source_sha256"] == selected["source_sha256"] for row in present.values()),
                       "same native ID refers to different source bytes across modes")
        learned, zero, baseline = (present.get(role) for role in ROLES[:3])
        if learned and zero:
            audit._require((learned["head_sha256"], learned["projection_sha256"]) == (zero["head_sha256"], zero["projection_sha256"]),
                           "native learned/zero-head source generation or projection differs")
        records.append({"id": name, "source_sha256": selected["source_sha256"], "present_roles": sorted(present),
                        "missing_roles": sorted(set(ROLES[:3]) - set(present)), "rows": present,
                        "returned_learned_zero_candidates_equal": learned["candidate_sha256"] == zero["candidate_sha256"] if learned and zero else None,
                        "learned_matches_source_label_candidate_digest": learned["candidate_sha256"] == baseline["candidate_sha256"] if learned and baseline else None,
                        "zero_matches_source_label_candidate_digest": zero["candidate_sha256"] == baseline["candidate_sha256"] if zero and baseline else None,
                        "source_derived_accuracy": None, "independent_sample_verified": False})
    return records


def evaluate(manifest: Path, output: Path, limits: Limits = DEFAULT_LIMITS):
    manifest, output = manifest.absolute(), output.absolute()
    pins = Pins(limits)
    raw = pins.read(manifest, limits.max_file_bytes)
    spec = audit._closed(_json(raw, limits), {"schema", "release", "public_manifest", "exports"}, "native diagnostics input")
    audit._require(spec["schema"] == INPUT_SCHEMA, "versioned native diagnostics input required")
    release = audit._closed(spec["release"], {"repository", "commit"}, "claimed release provenance")
    audit._require(release["repository"] == "datasets" and type(release["commit"]) is str and len(release["commit"]) == 40
                   and all(char in "0123456789abcdef" for char in release["commit"]), "exact claimed datasets release commit required")
    public_path, public_raw = pins.descriptor(spec["public_manifest"])
    public = audit._closed(_json(public_raw, limits), {"schema", "files"}, "public acceptance manifest")
    audit._require(public["schema"] == "codebase-source384-acceptance-evidence@1" and type(public["files"]) is list
                   and 0 < len(public["files"]) <= limits.max_manifest_children, "bounded native acceptance manifest required")
    inventory = {}
    for child in public["files"]:
        audit._closed(child, {"path", "sha256", "bytes"}, "public native child")
        relative = audit._relative_path(child["path"], "public native child")
        audit._require(not any(part.startswith(".") for part in Path(relative).parts) and relative not in inventory,
                       "duplicate or hidden public native selector")
        audit._digest(child["sha256"], "public child SHA")
        _nonnegative(child["bytes"], "public child bytes")
        inventory[relative] = child
    audit._closed(spec["exports"], set(ROLES), "native selected export roles")
    documents, paths = {}, {"public_manifest": public_path}
    for role in ROLES:
        path, body = pins.descriptor(spec["exports"][role])
        declared = inventory.get(SELECTORS[role])
        audit._require(declared is not None and declared["sha256"] == audit._sha(body) and declared["bytes"] == len(body),
                       "selected native export differs from public manifest commitment")
        documents[role], paths[role] = _json(body, limits), path
    lock_tool._preflight_output(output, [manifest.parent, *(path.parent for path in paths.values())])
    rows, summaries = {}, {}
    for role in ROLES[:2]:
        rows[role], summaries[role] = _inference(documents[role], role, limits)
    rows["source_label_baseline"], summaries["source_label_baseline"] = _baseline(documents["source_label_baseline"], limits)
    qualification = audit._closed(documents["qualification"], QUALIFICATION_FIELDS, "native qualification record")
    audit._require(qualification["schema"] == "codebase-source384-acceptance@1" and qualification["criterion"] == "RPI-011"
                   and qualification["profile"] == "codebase_ir/source_conditioned_384_v1", "public source384 acceptance profile required")
    checkpoint = audit._closed(qualification["checkpoint"], {"artifact", "checkpoint_sha256", "child_id", "parent_id"}, "claimed checkpoint")
    audit._digest(checkpoint["checkpoint_sha256"], "qualification claimed checkpoint")
    artifact = audit._closed(checkpoint["artifact"], {"bytes", "sha256"}, "recorded checkpoint artifact")
    _nonnegative(artifact["bytes"], "recorded checkpoint bytes")
    audit._digest(artifact["sha256"], "recorded checkpoint artifact SHA")
    for key in ("child_id", "parent_id"):
        audit._text(checkpoint[key], "recorded checkpoint " + key)
    audit._require(all(summary["claimed_checkpoint_sha256"] == checkpoint["checkpoint_sha256"] for role, summary in summaries.items()
                       if role in ROLES[:2]), "native inference/qualification checkpoint mismatch")
    _boolean(qualification["training_executed"], "qualification recorded training")
    for key in ("tests", "skips"):
        _nonnegative(qualification[key], "qualification recorded " + key)
    audit._require(_finite_number(qualification["seconds"])
                   and qualification["seconds"] >= 0, "finite nonnegative recorded qualification cost required")
    audit._require(type(qualification["scope_limits"]) is list and len(qualification["scope_limits"]) <= 32, "bounded native scope limits required")
    for item in qualification["scope_limits"]:
        audit._text(item, "recorded qualification scope limit", 2048)
    records = _pair(rows)
    report = {"schema": REPORT_SCHEMA, "status": "passed", **dict.fromkeys(FALSE_FLAGS, False),
              "manifest_sha256": audit._sha(raw), "public_manifest_sha256": audit._sha(public_raw),
              "input_files_unchanged": True, "native_outputs_retained_unmodified": True, "source_label_baseline_separate": True,
              "selection_complete_for_declared_four_roles": True, "release_provenance_claim": release,
              "unknown_pretraining_exposure": True, "source_bytes_available": False,
              "source_bytes_disposition": "not supplied as an exact source-only input; selected digests/spans cannot enable independent accuracy scoring",
              "scope": "selected public native returned candidates and recorded metadata, not model or source truth qualification",
              "row_pairing_policy": "exact native ID and unchanged source digest; missing modes remain explicit",
              "row_counts": {role: len(group) for role, group in rows.items()}, "record_count": len(records),
              "complete_three_role_record_count": sum(not row["missing_roles"] for row in records),
              "mode_summaries": summaries, "paired_records": records,
              "source_only_handoff": {"schema": "codebase-ir-native-source384-source-handoff@1", "status": "awaiting_exact_source_bytes",
                  "requests": [{"native_id": row["id"], "source_sha256": row["source_sha256"],
                     "recorded_head_sha256": row["rows"].get("learned", row["rows"].get("zero_head", {})).get("head_sha256"),
                     "recorded_spans": next((item["recorded_source_contract"]["recorded_spans"] for item in row["rows"].values()
                                              if item["recorded_source_contract"]["recorded_spans"]), []),
                     "source_path": None, "source_path_disposition": "no retained filesystem source selector supplied by this codec",
                     "source_truth_verified": False} for row in records],
                  "requested_evidence": ["exact source-only raw bytes and repository/path/revision selectors",
                     "complete parent training/tuning/canary/replay exposure inventory or explicit unknown frontiers",
                     "explicit native output stage and preconstraint raw output if available",
                     "owner-reviewed codec and separate learned/zero-head/source-label baseline policy"],
                  "native_owner_contacted": False},
              "codec_counts": {role: {state: sum(row["candidate_codec"]["status"] == state for row in rows[role].values())
                                       for state in ("recognized_binary_codec", "unsupported_codec")} for role in ROLES[:2]},
              "recorded_qualification": {"claimed_training_executed": qualification["training_executed"],
                 "profile": qualification["profile"], "production_acceptance": qualification["production_acceptance"],
                 "blocking_dependencies": qualification["blocking_dependencies"], "scope_limits": qualification["scope_limits"],
                 "recorded_seconds": qualification["seconds"], "recorded_tests": qualification["tests"], "recorded_skips": qualification["skips"],
                 "claimed_checkpoint_sha256": checkpoint["checkpoint_sha256"], "independently_requalified": False},
              "unselected_public_children": sorted(set(inventory) - set(SELECTORS.values())),
              "limits": asdict(limits), "input_bytes": pins.total,
              "input_files": [{"role": "manifest" if path == manifest else next(role for role, selected in paths.items() if selected == path),
                               "path": str(path), "sha256": audit._sha(body), "size_bytes": len(body)} for path, body in sorted(pins.files.items())]}
    pins.recheck()
    output.mkdir(mode=0o700)
    (output / "inputs").mkdir(mode=0o700)
    copies = {}
    try:
        for path, body in pins.files.items():
            role = "manifest" if path == manifest else next(role for role, selected in paths.items() if selected == path)
            copy = output / "inputs" / (role + ".json")
            with copy.open("xb") as stream:
                stream.write(body)
            copy.chmod(0o600)
            copies[copy] = body
        pins.recheck()
        for path, body in copies.items():
            audit._require(final.Capture.regular(path, len(body)) == body, "retained native copy drifted")
        pins.recheck()
        report["retained_files"] = [{"path": path.relative_to(output).as_posix(), "sha256": audit._sha(body), "size_bytes": len(body)}
                                    for path, body in sorted(copies.items())]
    except (audit.AuditInputError, OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        report.update(status="refused", input_files_unchanged=False, native_outputs_retained_unmodified=False,
                      error=f"{type(exc).__name__}: {exc}")
    final._write(output / "native_source384_diagnostics.json", report)
    (output / "native_source384_diagnostics.json").chmod(0o600)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = evaluate(args.manifest, args.output)
    except (audit.AuditInputError, OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        parser.exit(3, f"native source384 diagnostics refused: {type(exc).__name__}: {exc}\n")
    print(audit._canonical({key: report[key] for key in ("status", "manifest_sha256", "public_manifest_sha256", "record_count", "row_counts")}).decode())
    return 0 if report["status"] == "passed" else 3


if __name__ == "__main__":
    sys.exit(main())
