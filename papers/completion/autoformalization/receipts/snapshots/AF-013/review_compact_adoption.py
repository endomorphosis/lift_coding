#!/usr/bin/env python3
"""Sealed-PATH source/artifact review of the AF-013 compact operator bundle.

Does not reload multi-gigabyte T3 checkpoints, regenerate exports, rerun the
38-record canaries, invoke promotion, train, call checkers, or call providers.
The three operator runs already produced the compact native evidence; this
script checks those committed references, live/snapshot identity, and the
three original criteria.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[6]
PAPER = ROOT / "papers" / "completion" / "autoformalization"
SNAPSHOT = Path(__file__).resolve().parent / "operator-adoption-v1"
TEMPLATE = PAPER / "qualification" / "operator_inputs" / "AF-013" / "pending_receipt.template.json"
TEMPLATE_SHA256 = "bd2ca6ada18847423a86f1b3cbfc38b5fc2d8f187ba36794cd62504c4c56bd50"
CANARY_SHA256 = "98549048682ea1eb727812a6bb8e9d7a9834c22d43a62fd5373b7b7fad97c207"
CANARY_ID = f"af004-fixed-canary-{CANARY_SHA256}"
CANARY_EVIDENCE_ID = "lir-canary-evidence-944ac372cbce3d7326a08d58"
SEEDS = (104729, 130363, 155921)
T3_IDS = {
    104729: "def483e87bb57d27a8f24a3939a063d1039af95c111ec6d5733b452f612b5cbc",
    130363: "c90b4b9e7fd0120a7507b5e98bf7130e6c1e63091c14200afd3c2ee137ca5faf",
    155921: "a4e7a375e63e8a62c13691673342560596418095a0b1f0835ad6929d66d18be8",
}
BLOCK_REASONS = [
    "proof_receipts_missing",
    "missing_view_family_weights",
    "no_canonical_contracts_resolved",
    "no_guidance_records_met_promotion_threshold",
]
EXCLUDED_CATEGORIES = {
    "decoded_embeddings",
    "raw_source_text",
    "sample_identifiers",
    "sample_memory",
    "source_spans",
    "token_features",
}
E_REFUSE = 'if arm_id == "E" or not capability.get("runnable"):'
CRITERIA = [
    "Canary population and thresholds are fixed before comparison and are distinct from final test.",
    "Either actual consumer activation is evidenced by a matching loaded digest or the route is reported unactivated; export alone earns no downstream credit.",
    "Promotion rejection and rollback retain their genuine result and are analyzed rather than bypassed.",
]
REQUIRED_INTERPRETATION = (
    "Native compiler runs ingest the export identity but do not apply learned features. "
    "T4 is unactivated/unavailable; E remains locked. Default reset is an actual compiler reset, "
    "not rollback of a previously applied learned effect. Missing proof/source-copy metrics remain missing. "
    "Target-assisted T2 reconstruction is not source-free generalization or semantic fidelity. "
    "Human fidelity/agreement remain unmeasured; outside reviewers are not a manuscript-completion prerequisite. "
    "A native guardrails_passed flag over an empty family-metrics map supplies no measured proof/source-copy guardrail result. "
    "Export support counts describe native shared heads with samples=(), not empirical canary support."
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def phase_index(events, phase: str):
    for index, event in enumerate(events or []):
        if event.get("phase") == phase:
            return index
    return -1


def main() -> int:
    errors: list[str] = []
    if sha256_file(TEMPLATE) != TEMPLATE_SHA256:
        errors.append("pending receipt template digest drifted")
    template = load_json(TEMPLATE)
    artifacts = template.get("artifacts") or {}
    outputs = template.get("outputs") or {}
    if len(artifacts) != 4 or len(outputs) != 4:
        errors.append(f"template mapping counts artifacts={len(artifacts)} outputs={len(outputs)}")
    if [item.get("criterion") for item in template.get("criteria") or []] != CRITERIA:
        errors.append("template criteria drifted from the three original AF-013 criteria")

    for name, expected in artifacts.items():
        path = ROOT / name
        if not path.is_file():
            errors.append(f"missing snapshot {name}")
            continue
        digest = sha256_file(path)
        if digest != expected:
            errors.append(f"snapshot digest mismatch {name}")
        rel = path.relative_to(SNAPSHOT)
        live = PAPER / rel
        if not live.is_file():
            errors.append(f"missing live output {live.relative_to(ROOT)}")
        elif sha256_file(live) != expected:
            errors.append(f"live output differs from snapshot {live.relative_to(ROOT)}")

    for live_name, snapshot_name in outputs.items():
        if snapshot_name not in artifacts:
            errors.append(f"output maps to unhashed snapshot {live_name}")
        if live_name == snapshot_name:
            errors.append(f"output is its own snapshot {live_name}")

    canary_path = PAPER / "receipts" / "snapshots" / "AF-004" / "fixed_canary.sources.jsonl"
    if sha256_file(canary_path) != CANARY_SHA256:
        errors.append("AF-004 fixed canary digest drifted")
    canary_rows = load_jsonl(canary_path)
    canary_ids = [row.get("record_id") for row in canary_rows]
    canary_sources = {row.get("record_id"): (row.get("source_lineage") or {}).get("source_sha256") for row in canary_rows}
    if len(canary_ids) != 38 or len(set(canary_ids)) != 38:
        errors.append(f"AF-004 canary population is {len(canary_ids)}, not 38 distinct records")
    splits = load_json(PAPER / "data" / "splits.json")
    if (splits.get("exports") or {}).get("fixed_canary", {}).get("sha256") != CANARY_SHA256:
        errors.append("splits.json canary export digest drifted")
    if (splits.get("counts") or {}).get("fixed_canary", {}).get("natural_source_units") != 38:
        errors.append("splits.json canary unit count drifted")
    final_units = (splits.get("counts") or {}).get("final_test", {}).get("natural_source_units")
    if final_units != 1913:
        errors.append(f"final-test unit count drifted: {final_units}")
    if (splits.get("exports") or {}).get("final_test", {}).get("sha256") == CANARY_SHA256:
        errors.append("canary export digest equals the private final-test export")

    results = load_jsonl(PAPER / "runs" / "guidance_promotion" / "results.jsonl")
    export = load_json(PAPER / "evidence" / "guidance_export.json")
    consumer = load_json(PAPER / "evidence" / "consumer_activation.json")
    rollback = load_json(PAPER / "evidence" / "rollback_receipt.json")

    if len(results) != 3:
        errors.append(f"expected 3 result rows, got {len(results)}")
    if {row.get("seed") for row in results} != set(SEEDS):
        errors.append(f"result seeds { {row.get('seed') for row in results} }")
    if any(row.get("schema") != "af013-native-fixed-canary-result/v1" for row in results):
        errors.append("result schema drifted")

    export_by_seed = {item.get("seed"): item for item in export.get("seeds") or []}
    consumer_by_seed = {item.get("seed"): item for item in consumer.get("seeds") or []}
    rollback_by_seed = {item.get("seed"): item for item in rollback.get("seeds") or []}
    if set(export_by_seed) != set(SEEDS) or set(consumer_by_seed) != set(SEEDS) or set(rollback_by_seed) != set(SEEDS):
        errors.append("compact three-seed observations missing a frozen seed")

    if export.get("e_locked") is not True or export.get("export_samples") != 0:
        errors.append("guidance export did not keep E locked with sample_count 0")
    if export.get("native_raw_export_schema_not_implied") is not True:
        errors.append("export compact reference implied a native raw schema")
    if export.get("interpretation") != REQUIRED_INTERPRETATION:
        errors.append("guidance export interpretation drifted")
    if consumer.get("T4") != "unactivated/unavailable" or consumer.get("e_locked") is not True:
        errors.append("consumer observation did not report T4 unactivated/unavailable with E locked")
    if consumer.get("matching_ingestion_digest_is_applied_learning") is not False:
        errors.append("matching ingestion digest was treated as applied learning")
    if consumer.get("human_agreement") is not None or consumer.get("human_fidelity") is not None:
        errors.append("consumer observation claimed measured human metrics")
    if consumer.get("interpretation") != REQUIRED_INTERPRETATION:
        errors.append("consumer interpretation drifted")
    if rollback.get("applied_learning_rollback_performed") is not False:
        errors.append("rollback receipt claimed rollback of an applied learned effect")
    if rollback.get("reset_operations_attempted") != 114:
        errors.append(f"default-reset count {rollback.get('reset_operations_attempted')} != 114")
    if rollback.get("interpretation") != REQUIRED_INTERPRETATION:
        errors.append("rollback interpretation drifted")

    for row in results:
        seed = row.get("seed")
        if row.get("T4") != "unactivated/unavailable" or row.get("e_locked") is not True:
            errors.append(f"seed {seed} did not keep T4 unactivated and E locked")
        if row.get("denominator") != 38:
            errors.append(f"seed {seed} denominator is not the frozen 38-record canary")
        if row.get("interpretation") != REQUIRED_INTERPRETATION:
            errors.append(f"seed {seed} result interpretation drifted")
        checkpoint = row.get("checkpoint") or {}
        if checkpoint.get("arm") != "T3" or checkpoint.get("identity_sha256") != T3_IDS.get(seed):
            errors.append(f"seed {seed} did not bind the AF-029 T3 identity")
        if checkpoint.get("no_payload_parsed_or_rehashed") is not True:
            errors.append(f"seed {seed} reparsed or rehashed the checkpoint payload")
        diagnostics = row.get("canary_diagnostics") or []
        identities = row.get("canary_source_identities") or []
        if [item.get("record_id") for item in diagnostics] != canary_ids:
            errors.append(f"seed {seed} canary population drifted from AF-004")
        if [item.get("record_id") for item in identities] != canary_ids:
            errors.append(f"seed {seed} canary identity order drifted")
        for item in identities:
            expected_source = canary_sources.get(item.get("record_id"))
            if item.get("source_text_sha256") != expected_source:
                errors.append(f"seed {seed} source digest drifted for {item.get('record_id')}")
        if any(
            item.get("artifact_ingestion_digest_matches") is not True
            or (item.get("diagnostic_validity") or {}).get("on_metadata_only") is not True
            or (item.get("comparisons") or {}).get("off_on_core_equal") is not True
            or (item.get("comparisons") or {}).get("default_restored_core_equal") is not True
            for item in diagnostics
        ):
            errors.append(f"seed {seed} lost metadata-only ingestion or default-reset equality")
        events = row.get("native_stage_events") or []
        bound = phase_index(events, "native_imports_and_canary_bound")
        reloaded = phase_index(events, "native_checkpoint_reloaded")
        exported = phase_index(events, "shared_export_retained_dense_state_released")
        paired = phase_index(events, "paired_38_diagnostics_complete")
        terminal = phase_index(events, "terminal")
        if not (0 <= bound < reloaded < exported < paired < terminal):
            errors.append(f"seed {seed} did not bind the canary before checkpoint reload and comparison")
        if events[reloaded].get("identity_sha256") != T3_IDS.get(seed):
            errors.append(f"seed {seed} reload identity drifted")
        terminal_event = events[terminal]
        if (
            terminal_event.get("downstream_activation") is not False
            or terminal_event.get("training_calls") != 0
            or terminal_event.get("provider_calls") != 0
            or terminal_event.get("full_training_checker_calls") != 0
            or terminal_event.get("success") is not True
        ):
            errors.append(f"seed {seed} reran training/providers/checkers or claimed downstream activation")

        export_row = export_by_seed.get(seed) or {}
        export_payload = export_row.get("export") or {}
        if set(export_payload.get("excluded_categories") or []) != EXCLUDED_CATEGORIES:
            errors.append(f"seed {seed} export did not exclude raw-source/sample-memory channels")
        if export_payload.get("sample_count") != 0 or export_payload.get("sample_memory_included") is not False:
            errors.append(f"seed {seed} export included sample memory or samples")
        if export_payload.get("feature_count") != 64 or len(export_payload.get("stable_features") or []) != 64:
            errors.append(f"seed {seed} export feature_count drifted")
        if export_payload.get("view_family_weights") != {}:
            errors.append(f"seed {seed} export claimed nonempty view-family weights")
        if any(
            feature.get("sample_support") != 1 or feature.get("source_head_count") != 1
            for feature in export_payload.get("stable_features") or []
        ):
            errors.append(f"seed {seed} export support counts are not native shared heads with samples=()")
        if (export_row.get("checkpoint") or {}).get("identity_sha256") != T3_IDS.get(seed):
            errors.append(f"seed {seed} export checkpoint identity drifted")

        activation = (consumer_by_seed.get(seed) or {}).get("activation") or {}
        promotion = (consumer_by_seed.get(seed) or {}).get("promotion") or {}
        if activation.get("state") != "unactivated" or activation.get("T4") != "unavailable":
            errors.append(f"seed {seed} consumer route was not reported unactivated/unavailable")
        if activation.get("applied_learned_features") is not False:
            errors.append(f"seed {seed} claimed applied learned features")
        if activation.get("human_agreement") is not None or activation.get("human_fidelity") is not None:
            errors.append(f"seed {seed} claimed measured human metrics")
        if promotion.get("status") != "no_candidate" or promotion.get("promotion_report_outcome") != "no_candidate":
            errors.append(f"seed {seed} native no_candidate outcome was rewritten")
        if promotion.get("promoted") is not False or promotion.get("promotion_allowed") is not False:
            errors.append(f"seed {seed} promotion was marked allowed or promoted")
        if promotion.get("candidate_record_count") != 0 or promotion.get("guidance_records") not in ([], None):
            errors.append(f"seed {seed} invented guidance candidates")
        if promotion.get("block_reasons") != BLOCK_REASONS:
            errors.append(f"seed {seed} block reasons were not retained")
        activation_state = promotion.get("activation_state") or {}
        if activation_state.get("active") is not False or activation_state.get("state") != "blocked":
            errors.append(f"seed {seed} activation_state did not remain blocked")
        canary_evidence = promotion.get("canary_evidence") or {}
        binding = promotion.get("fixed_canary_binding") or {}
        if canary_evidence.get("canary_id") != CANARY_ID or binding.get("canary_id") != CANARY_ID:
            errors.append(f"seed {seed} canary_id drifted from AF-004")
        if canary_evidence.get("evidence_id") != CANARY_EVIDENCE_ID:
            errors.append(f"seed {seed} canary evidence_id drifted")
        if canary_evidence.get("fixed_sample_set") is not True or canary_evidence.get("metric_tolerance") != 0.0:
            errors.append(f"seed {seed} canary thresholds were not the frozen zero-tolerance set")
        if canary_evidence.get("family_metrics") != {}:
            errors.append(f"seed {seed} invented family-metric measurements")
        if canary_evidence.get("guardrails_passed") is not True:
            errors.append(f"seed {seed} lost the native empty-map guardrails_passed flag")
        causal = promotion.get("causal_evidence") or {}
        if causal.get("learned_path_responsive") is not False or causal.get("proof_receipt_count") != 0:
            errors.append(f"seed {seed} claimed a learned-path or proof-receipt effect")
        if causal.get("view_family_weights") != {} or causal.get("family_metric_deltas") != {}:
            errors.append(f"seed {seed} claimed nonempty family-weight or delta evidence")

        native_reset = (rollback_by_seed.get(seed) or {}).get("native_reset") or {}
        if native_reset.get("applied_learning_rollback_performed") is not False:
            errors.append(f"seed {seed} claimed rollback of an applied learned effect")
        if native_reset.get("reset_operations_attempted") != 38:
            errors.append(f"seed {seed} default-reset count drifted")

    arms_source = (PAPER / "evaluation" / "pipeline_arms.py").read_text(encoding="utf-8")
    if E_REFUSE not in arms_source:
        errors.append("pipeline_arms.py no longer unconditionally refuses E")
    if "unavailable_pending_AF-011_AF-013" not in arms_source:
        errors.append("pipeline_arms.py lost the AF-013 promotion gate")
    config = load_json(PAPER / "config" / "pipeline_arms.json")
    arm_e = (config.get("arms") or {}).get("E") or {}
    if arm_e.get("development_route") != "unavailable_pending_AF-011_AF-013":
        errors.append("pipeline_arms.json activated E")

    binding = load_json(PAPER / "evidence" / "native_training" / "eligible_checkpoint_binding.json")
    if binding.get("e_locked") is not True:
        errors.append("eligible-checkpoint binding unlocked E")
    if set(binding.get("t3_identities") or []) != set(T3_IDS.values()):
        errors.append("eligible-checkpoint T3 identities drifted")

    scope = load_json(PAPER / "evidence" / "native_training" / "reconstruction_metric_scope.json")
    if "target-assisted" not in str(scope.get("finding") or ""):
        errors.append("reconstruction metric scope lost the target-assisted finding")

    for task_id in ("AF-004", "AF-011", "AF-012", "AF-028", "AF-029"):
        path = PAPER / "receipts" / f"{task_id}.json"
        if not path.is_file():
            errors.append(f"{task_id} receipt missing")
            continue
        prior = load_json(path)
        if prior.get("status") != "complete" or prior.get("task_id") != task_id:
            errors.append(f"{task_id} receipt is not a preserved complete receipt")

    if errors:
        print("FAIL")
        for item in errors:
            print(item)
        return 1
    print("PASS")
    print(json.dumps({
        "T4": "unactivated/unavailable",
        "applied_learning_rollback_performed": False,
        "canary_id": CANARY_ID,
        "canary_records": 38,
        "e_locked": True,
        "export_samples": 0,
        "final_test_units": 1913,
        "live_outputs_match_snapshots": True,
        "matching_ingestion_digest_is_applied_learning": False,
        "promotion_report_outcome": "no_candidate",
        "reset_operations_attempted": 114,
        "seeds": list(SEEDS),
        "snapshot_artifacts": 4,
        "t3_identities": [T3_IDS[seed] for seed in SEEDS],
        "template_sha256": TEMPLATE_SHA256,
        "training_checker_provider_calls": 0,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
