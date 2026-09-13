#!/usr/bin/python3.12
"""Materialize the NS-018 withdrawn-ablation scope record. No experiments."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve()
while not (ROOT / "scripts" / "paper_supervisors.py").is_file():
    if ROOT.parent == ROOT:
        raise SystemExit("repository root not found")
    ROOT = ROOT.parent

ABLATIONS = ROOT / "papers/completion/neurosymbolic_supervision/runs/ablations"
ORIGINAL192 = ROOT / (
    "papers/completion/neurosymbolic_supervision/pilot/recovery/final_input_source/"
    "original192.private.json"
)
FREEZE = ROOT / "papers/completion/neurosymbolic_supervision/artifacts/final_experiment_freeze.json"
POLICY = ROOT / (
    "papers/completion/neurosymbolic_supervision/pilot/recovery/final_input_source/"
    "analysis_policy.json"
)
SCOPE = ROOT / "papers/completion/neurosymbolic_supervision/protocol/final32_adoption_scope.json"
FINAL_MANIFEST = ROOT / "papers/completion/neurosymbolic_supervision/protocol/final_run_manifest.json"
MAIN = ROOT / "papers/completion/neurosymbolic_supervision/runs/main"
NS017 = ROOT / "papers/completion/neurosymbolic_supervision/receipts/NS-017.json"
NS016_BUNDLE = ROOT / (
    "papers/completion/neurosymbolic_supervision/receipts/snapshots/NS-016/"
    "post32_completion_v1/actual_bundle_manifest.json"
)
PILOT_COSTS = ROOT / "papers/completion/neurosymbolic_supervision/pilot/costs.jsonl"
BOUNDARY = ROOT / (
    "papers/completion/neurosymbolic_supervision/pilot/recovery/final_input_source/"
    "pilot_boundary_disclosure.private.json"
)
BUILDER = ROOT / (
    "papers/completion/neurosymbolic_supervision/pilot/recovery/final_input_source/"
    "build_final_inputs.py"
)
BATCH = ROOT / (
    "papers/completion/neurosymbolic_supervision/pilot/recovery/final_input_source/"
    "host_service/batch_control.py"
)
TASKS = ROOT / "papers/completion/neurosymbolic_supervision/tasks.json"

FREEZE_FILE_SHA = "7175ca68247d958dabf83a97441fe6042d3b88feafa74f95c76e1720cc74fa1a"
FREEZE_CANONICAL_SHA = "ac605b5de8b58cc41c5c3609e7752e5e4441ab627dbbe6d31f4d8d086b33732d"
ORIGINAL192_SHA = "6ed6e590479d7d71bdcc9cc67fc7cccf51b05230c0f6761fcd7c520bece2ac80"
POLICY_SHA = "a0edbc1cdf13f1d5aab4170dd60fcb3a3b2ef26d192f6dbbdce9b6a26ff700d3"
EMPTY_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
MAIN_HASHES = {
    "manifest.json": "0891bee6e3a556f5448250bbf11815ac255958a2f02add848d4e0934f23aeeac",
    "attempts.jsonl": "7d3471f965cc9bd6c024e1fd9c528b9797c40601e5083eb8f1f506d78094716f",
    "deviations.md": "af86395218d147f7a9707bce476cf7aa002fe3af87df8a0a1b3f658608ff0c24",
    "provider_receipts.jsonl": "8448634cb9dd6569a46dc9a90dbd48f99f047a798014df7f461c19d93b7bd55a",
    "resource_measurements.jsonl": "97e9a1bb9503886c3a609322cab8dbe1e927854df10bee5805be16240eec17ee",
}
BUNDLE_SHA = "f8488d8e69f097a8332ec6ae41aded6b260e5ad8df90531bd539d6f9e85b4f46"
ANALYSIS_SHA = "824366e7fb10725be884b04448d5b4a8dd2ff5c478af5df7a8c98721f4641766"
ARMS_AB = ("A", "B")
REPS = (104729, 130363)
CRITERIA = (
    "Each retained efficiency mechanism has a matched isolated comparison or an explicit non-attributable limitation.",
    "Controls differ only in declared factors; enabled checks and acceptance standards are recorded.",
    "Deny-all contributes only diagnostic safety/cost evidence and cannot satisfy useful-progress promotion.",
    "Ablation failures, extra fallback, proof/index/setup/training costs, and slower workloads remain in outputs.",
)

DEVIATIONS = """# Withdrawn ablations and limits of attribution

The governing pre-outcome scope retains a 32-cell A/B comparison with local-cold caches: eight independent families and two nested repetition identifiers (104729 and 130363). These identifiers are not asserted to be served-model random seeds. Canonical freeze ac605b5de8b58cc41c5c3609e7752e5e4441ab627dbbe6d31f4d8d086b33732d, freeze file SHA256 7175ca68247d958dabf83a97441fe6042d3b88feafa74f95c76e1720cc74fa1a. This record implements that existing freeze; it does not change the experiment after outcomes.

The original ordered plan contains 192 cells: eight families × six arms (A, B, C, D, C-no-route, C-no-reuse) × two cache modes × two repetitions. Filtering that order to A/B and local-cold retains exactly the frozen 32 cell identities. The 160 removed cells comprise 128 non-A/B cells plus 32 A/B local-warm cells, a disjoint partition. Eight additional families were not recruited; they have no invented identities or observations here. The original sixteen-family target would have contained 384 factor cells; the preserved original plan contains 192.

Root-admitted main evidence now exists under NS-017 and is bound here by hash. This ablation record does not copy those 32 terminal rows, useful-completion labels, or resource clocks into `attempts.jsonl` or `resource_measurements.jsonl`. Bound main evidence is not an isolated component-ablation result.

| Comparison or mechanism | Disposition and interpretation |
| --- | --- |
| A/B source-linked native semantic context | Retained main factor comparison using matched public raw selection. It does not isolate arbitrary internal subcomponents or establish isolated efficiency gains. Actual main outcomes remain in the separately admitted NS-017 evidence. |
| C/D routing and governance; C-no-route and C-no-reuse | Withdrawn from this experiment. No measured component-ablation result or routing/reuse efficacy claim. |
| Local-warm caches, reuse and publication comparisons | Withdrawn. Shared preparation does not establish a measured warm-cache or proof-reuse benefit. |
| Translation checks | No isolated experiment performed or authorized. Contribution remains non-attributable. |
| Sealer (sequential/parallel) | No isolated experiment performed or authorized. Contribution remains non-attributable. |
| Parallel preparation | No isolated experiment performed or authorized. Contribution remains non-attributable. |
| Procedure components | No isolated experiment performed or authorized. Contribution remains non-attributable. |
| Deny-all | At most diagnostic safety/cost evidence; it cannot establish useful completion or satisfy useful-progress promotion. No deny-all ablation observation is claimed here. |

`attempts.jsonl` and `resource_measurements.jsonl` are both real zero-byte files, representing zero measured ablation rows. They are not the main 32-cell dataset, a file-generation failure, or a successful control result. They are not evidence that experimental or setup costs are zero. The manifest enumerates withdrawn planned cells as scope metadata, not empirical attempts.

For the retained main comparison, declared checks and acceptance standards remain those of the bound frozen analysis policy: an actual sealed candidate under its one-use grant, independently cold-scored with all nonempty public and hidden checks passing, plus the separate measured resource rules. This document does not assert that any cell passed those checks, and it does not re-score NS-017. Failure, abstention, missing or unscored validation must not receive useful-success credit. Historical signed labels and measured timing deviations remain intact in their own ledgers. An unchanged acceptance standard is not evidence that a withdrawn control was run.

Proof, index, setup, training, fallback, cleanup, review and workload-specific cost attribution is unmeasured for isolated ablations and remains null, not zero. Actual pilot/protocol failures, preparation and baseline measurements, diagnostic and lease records remain in their separately bound evidence scopes, including NS-016/NS-028 pilot costs and the NS-017 main resource/provider ledgers. The historical pilot boundary disclosure remains applicable, including its unscored overrun and unknown settled remote charges. Child, wrapper, gateway, scorer and operator intervals can overlap and must not be summed as disjoint elapsed time. No slower workload, failed setup, extra fallback, or unknown charge is removed by the absence of ablation rows. This record does not replace the full cost ledgers.

This completion does not launch translation, routing, reuse, warm-cache, sealer, parallel, or procedure experiments. C/D routing, warm caches, reuse, publication-comparison efficacy and original 16-family inferential objectives remain withdrawn; they are not completed benchmark outcomes. Outside human review is not required; human semantic fidelity remains unmeasured.

NS-019 should render its out-of-scope ablation table from this manifest and these empty datasets while regenerating its main table from the separately admitted complete main evidence. It should not manufacture ablation attempts or zeros to fill a table.

No external human review is required to document this scope. Independent human semantic fidelity and component-level causal effects remain unmeasured. This is off-live preparation; it grants no execution or native completion authority and changes none of the original freeze, source pins, receipts or native history.
"""


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canon(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def cell_id(unit: str, arm: str, cache: str, repetition: int) -> str:
    return hashlib.sha256(
        canon(
            {
                "unit": unit,
                "arm": arm,
                "cache": cache,
                "repetition": repetition,
                "record_kind": "final",
            }
        )
    ).hexdigest()


def require(ok: bool, message: str) -> None:
    if not ok:
        raise SystemExit(message)


def binding(path: Path, expected: str | None = None) -> dict:
    digest = sha(path)
    if expected is not None:
        require(digest == expected, "hash mismatch: " + str(path.relative_to(ROOT)))
    rel = str(path.relative_to(ROOT))
    return {
        "bytes": path.stat().st_size,
        "repository_path": rel,
        "sha256": digest,
    }


def dump(path: Path, obj) -> bytes:
    data = json.dumps(obj, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    path.write_bytes(data)
    return data


def main() -> int:
    original = json.loads(ORIGINAL192.read_bytes())
    freeze = json.loads(FREEZE.read_bytes())
    policy = json.loads(POLICY.read_bytes())
    scope = json.loads(SCOPE.read_bytes())
    ns017 = json.loads(NS017.read_bytes())

    require(sha(ORIGINAL192) == ORIGINAL192_SHA, "original192 hash changed")
    require(sha(FREEZE) == FREEZE_FILE_SHA, "freeze file hash changed")
    require(freeze.get("freeze_sha256") == FREEZE_CANONICAL_SHA, "canonical freeze hash changed")
    require(sha(POLICY) == POLICY_SHA, "analysis policy hash changed")
    require(original.get("amended_final_units_n8_families") == 192, "original192 unit count changed")
    units = original["units"]
    require(isinstance(units, list) and len(units) == 192, "original192 lineage is not 192 units")
    require(freeze.get("retained_executable_arms") == ["A", "B"], "retained arms changed")
    require(sorted(freeze.get("removed_arms", {})) == ["C", "C-no-reuse", "C-no-route", "D"], "removed arms changed")
    require(len(freeze.get("planned_cells", [])) == 32, "freeze planned cells are not 32")
    require(scope.get("removed_factor_cells") == 160, "adoption scope removed-cell count changed")
    require(ns017.get("task_id") == "NS-017" and ns017.get("status") == "complete", "NS-017 main evidence is not complete")

    retained_src = []
    withdrawn_src = []
    for index, unit in enumerate(units):
        keep = unit["arm"] in ARMS_AB and unit["cache"] == "local_cold"
        row = dict(unit)
        row["original_schedule_index"] = index
        (retained_src if keep else withdrawn_src).append(row)
    require(len(retained_src) == 32, "A/B local-cold filter is not 32")
    require(len(withdrawn_src) == 160, "withdrawn filter is not 160")

    computed = [
        cell_id(u["task_id"], u["arm"], u["cache"], u["repetition"]) for u in retained_src
    ]
    require(computed == freeze["planned_cells"], "original192 A/B local-cold order does not match freeze")
    require(computed == json.loads((MAIN / "manifest.json").read_bytes())["ordered_cells"], "NS-017 ordered cells differ")

    for name, expected in MAIN_HASHES.items():
        require(sha(MAIN / name) == expected, "NS-017 current output hash changed: " + name)

    warm = [u for u in withdrawn_src if u["arm"] in ARMS_AB and u["cache"] == "local_warm"]
    non_ab = [u for u in withdrawn_src if u["arm"] not in ARMS_AB]
    require(len(warm) == 32 and len(non_ab) == 128, "160-cell partition is not 32 warm + 128 non-A/B")

    retained_cells = []
    for unit, cid in zip(retained_src, computed):
        retained_cells.append(
            {
                "arm": unit["arm"],
                "cache": unit["cache"],
                "disposition": "retained_main_comparison_not_ablation",
                "family_id": unit["family_id"],
                "final_cell_id": cid,
                "observed_outcome_included": False,
                "order_key": unit["order_key"],
                "original_schedule_index": unit["original_schedule_index"],
                "record_kind": unit["record_kind"],
                "repetition": unit["repetition"],
                "task_id": unit["task_id"],
            }
        )

    withdrawn_cells = []
    for unit in withdrawn_src:
        partition = "AB_local_warm" if unit["arm"] in ARMS_AB else "non_AB_arm"
        withdrawn_cells.append(
            {
                "arm": unit["arm"],
                "cache": unit["cache"],
                "disposition": "withdrawn_from_final_ablation_scope",
                "family_id": unit["family_id"],
                "identity_cell_id": cell_id(unit["task_id"], unit["arm"], unit["cache"], unit["repetition"]),
                "measured_ablation_attempt": False,
                "order_key": unit["order_key"],
                "original_schedule_index": unit["original_schedule_index"],
                "record_kind": unit["record_kind"],
                "removal_partition": partition,
                "repetition": unit["repetition"],
                "task_id": unit["task_id"],
            }
        )

    ABLATIONS.mkdir(parents=True, exist_ok=True)
    attempts_path = ABLATIONS / "attempts.jsonl"
    resources_path = ABLATIONS / "resource_measurements.jsonl"
    deviations_path = ABLATIONS / "deviations.md"
    attempts_path.write_bytes(b"")
    resources_path.write_bytes(b"")
    deviations_bytes = DEVIATIONS.encode("utf-8")
    deviations_path.write_bytes(deviations_bytes)
    require(sha(attempts_path) == EMPTY_SHA and attempts_path.stat().st_size == 0, "attempts.jsonl is not empty")
    require(sha(resources_path) == EMPTY_SHA and resources_path.stat().st_size == 0, "resource_measurements.jsonl is not empty")

    files = {
        "attempts.jsonl": {"bytes": 0, "sha256": EMPTY_SHA},
        "deviations.md": {"bytes": len(deviations_bytes), "sha256": sha_bytes(deviations_bytes)},
        "resource_measurements.jsonl": {"bytes": 0, "sha256": EMPTY_SHA},
    }

    manifest = {
        "cost_rules": list(policy["cost_rules"]),
        "criterion_evidence": [
            {
                "criterion": 1,
                "evidence": "The only retained efficiency mechanism is the A/B source-linked native semantic context factor. It is a matched package-level main comparison, not an isolated component ablation, so causal efficiency remains an explicit non-attributable limitation.",
                "status": "explicit_non_attributable_limitation",
            },
            {
                "criterion": 2,
                "evidence": "The retained A/B design changes only the declared native semantic-context factor using matched public raw selection. Enabled checks and acceptance standards are the frozen analysis-policy rules recorded below; withdrawn C/D/warm/reuse/sealer/translation/parallel/procedure controls were not executed.",
                "status": "frozen_main_standard_retained_no_ablation_controls_executed",
            },
            {
                "criterion": 3,
                "evidence": "Deny-all is recorded as diagnostic safety/cost evidence only. It cannot satisfy useful-progress promotion and no deny-all observation is claimed.",
                "status": "diagnostic_only_no_deny_all_observation_claimed",
            },
            {
                "criterion": 4,
                "evidence": "Zero measured ablation rows are empty files, not zeros. Ablation failures were never suppressed because no isolated ablation ran. Extra fallback, proof/index/setup/training costs, slower workloads, and prior pilot/protocol failures remain in separately bound ledgers with null isolated attributions.",
                "status": "no_ablation_records_suppressed_costs_not_zero",
            },
        ],
        "declared_main_acceptance_standard": policy["useful_outcome"],
        "declared_main_common_scorer_profile": dict(policy["final_scorer_pid_amendment"]),
        "declared_main_resource_standard": dict(policy["measured_resource_success_rule"]),
        "deny_all": {
            "can_satisfy_useful_progress_promotion": False,
            "measured_ablation_attempt": False,
            "role": "diagnostic_safety_cost_evidence_only",
            "useful_completion_claimed": False,
        },
        "destination_preimages": [
            {
                "bytes": None,
                "repository_path": "papers/completion/neurosymbolic_supervision/runs/ablations/manifest.json",
                "sha256": None,
                "state": "present_written_by_this_record",
            },
            {
                "bytes": 0,
                "repository_path": "papers/completion/neurosymbolic_supervision/runs/ablations/attempts.jsonl",
                "sha256": EMPTY_SHA,
                "state": "present_empty_measured_ablation_rows",
            },
            {
                "bytes": 0,
                "repository_path": "papers/completion/neurosymbolic_supervision/runs/ablations/resource_measurements.jsonl",
                "sha256": EMPTY_SHA,
                "state": "present_empty_measured_ablation_rows",
            },
            {
                "bytes": files["deviations.md"]["bytes"],
                "repository_path": "papers/completion/neurosymbolic_supervision/runs/ablations/deviations.md",
                "sha256": files["deviations.md"]["sha256"],
                "state": "present_written_by_this_record",
            },
        ],
        "disposition": "withdrawn_ablations_with_non_attributable_retained_main_contrast",
        "downstream_ns019": {
            "ablation_table_rule": "Render withdrawals/non-attribution from this manifest and zero measured ablation rows; obtain main results from separately admitted complete main evidence. Never interpret absence as zero cost or fabricate rows.",
            "acceptance_criteria_exact": [
                "One documented analysis command regenerates main and ablation tables from immutable raw records.",
                "All counts reconcile to the run manifest, including failed/unsolved/timeout/abstained/unavailable cases.",
                "Confidence intervals and quality gates follow the preregistered plan; deviations and inconclusive outcomes are explicit.",
                "No estimated preliminary number is labeled measured, no missing cost is zero, and overlapping stage times are not summed as elapsed.",
            ],
            "title": "Regenerate descriptive eight-family A/B outcomes and measured cost summaries",
        },
        "execution_authorization": {
            "native_completion_authorized": False,
            "new_model_or_scorer_calls": False,
            "parallel_experiment": False,
            "procedure_experiment": False,
            "reuse_experiment": False,
            "routing_experiment": False,
            "sealer_experiment": False,
            "translation_experiment": False,
            "warm_cache_experiment": False,
        },
        "files": files,
        "freeze_file_sha256": FREEZE_FILE_SHA,
        "freeze_sha256": FREEZE_CANONICAL_SHA,
        "main_outcome_rows_included": 0,
        "measured_ablation_attempt_rows": 0,
        "measured_ablation_resource_rows": 0,
        "native_completion_authorized": False,
        "native_task_acceptance_criteria_exact": list(CRITERIA),
        "new_scientific_execution_authorized": False,
        "off_live_preparation": True,
        "overall_experimental_cost_total": None,
        "overall_experimental_cost_total_status": "not_computed_or_pooled_by_this_scope_record",
        "population": {
            "identifiers_are_claimed_served_api_random_seeds": False,
            "nested_repetition_identifiers": [104729, 130363],
            "ordered_filter_verified_against_frozen_batch": True,
            "original_arms": ["A", "B", "C", "D", "C-no-route", "C-no-reuse"],
            "original_cache_modes": ["local_cold", "local_warm"],
            "original_factor_cells_if_all_16_families_recruited": 384,
            "original_family_count": 8,
            "original_family_target": 16,
            "original_planned_factor_cells": 192,
            "retained_independent_families": 8,
            "retained_main_cells": 32,
            "unrecruited_families": 8,
            "unrecruited_family_identities": None,
            "withdrawn_disjoint_partition": {"AB_local_warm": 32, "non_AB_arm": 128},
            "withdrawn_planned_factor_cells": 160,
        },
        "prepared_at_utc": datetime.now(timezone.utc).isoformat(),
        "retained_factor_comparison": {
            "arms": ["A", "B"],
            "attribution": "explicit_non_attributable_limitation",
            "cache": "local_cold",
            "isolates_arbitrary_subcomponents": False,
            "matched_isolated_component_comparison": False,
            "matched_public_raw_selection": True,
            "name": "source_linked_native_semantic_context",
            "repetitions": [104729, 130363],
        },
        "retained_main_planned_cells": retained_cells,
        "root_admitted_main_evidence": {
            "bound_after_existence": True,
            "copied_into_ablation_rows": False,
            "files": {
                "papers/completion/neurosymbolic_supervision/runs/main/attempts.jsonl": binding(MAIN / "attempts.jsonl", MAIN_HASHES["attempts.jsonl"]),
                "papers/completion/neurosymbolic_supervision/runs/main/deviations.md": binding(MAIN / "deviations.md", MAIN_HASHES["deviations.md"]),
                "papers/completion/neurosymbolic_supervision/runs/main/manifest.json": binding(MAIN / "manifest.json", MAIN_HASHES["manifest.json"]),
                "papers/completion/neurosymbolic_supervision/runs/main/provider_receipts.jsonl": binding(MAIN / "provider_receipts.jsonl", MAIN_HASHES["provider_receipts.jsonl"]),
                "papers/completion/neurosymbolic_supervision/runs/main/resource_measurements.jsonl": binding(MAIN / "resource_measurements.jsonl", MAIN_HASHES["resource_measurements.jsonl"]),
            },
            "ns017_receipt": binding(NS017),
            "ns017_status": ns017.get("status"),
            "role": "separately_admitted_main_comparison_not_isolated_ablation",
            "strict_complete32_analysis_sha256": ANALYSIS_SHA,
        },
        "row_semantics": {
            "empty_attempts": "No isolated ablation observations under the governing withdrawn scope; not the retained main dataset.",
            "empty_resources": "No isolated ablation resource observations; not zero experimental/setup cost.",
            "planned_cell_entries_are_empirical_attempts": False,
        },
        "schema": "ns018-withdrawn-ablations-manifest/v1",
        "scope_limitations": [
            "No component-level causal efficiency result.",
            "No C/D, warm-cache, routing/reuse or publication-comparison efficacy evidence.",
            "No isolated translation, sealer, parallel, or procedure experiment.",
            "No independent human semantic fidelity measurement.",
            "Main 32-cell evidence exists and is bound by hash from NS-017; this record does not copy those outcomes or interpret them as isolated component results.",
            "Original pre-outcome boolean fields are historical freeze metadata, not a current execution-status assertion.",
            "Original pilot/protocol costs and resource deviations remain separate; this is not the complete numerical supplement.",
        ],
        "separate_existing_cost_evidence": {
            "actual32_bundle_manifest": binding(NS016_BUNDLE, BUNDLE_SHA),
            "ns017_main_provider_receipts": binding(MAIN / "provider_receipts.jsonl", MAIN_HASHES["provider_receipts.jsonl"]),
            "ns017_main_resource_measurements": binding(MAIN / "resource_measurements.jsonl", MAIN_HASHES["resource_measurements.jsonl"]),
            "pilot_boundary_disclosure": binding(BOUNDARY),
            "retained_paper_pilot_costs": binding(PILOT_COSTS),
        },
        "source_bindings": {
            "cell_identity_source": binding(BATCH),
            "current_scope": binding(SCOPE),
            "current_task_contract": binding(TASKS),
            "frozen_analysis_policy": binding(POLICY, POLICY_SHA),
            "historical_pilot_boundary_disclosure": binding(BOUNDARY),
            "ordered_filter_source": binding(BUILDER),
            "original_192_ordered_plan": binding(ORIGINAL192, ORIGINAL192_SHA),
            "original_preoutcome_freeze": binding(FREEZE, FREEZE_FILE_SHA),
            "paper_final_run_manifest": binding(FINAL_MANIFEST),
        },
        "task_id": "NS-018",
        "unmeasured_isolated_cost_attribution": {
            "cleanup": None,
            "fallback": None,
            "index": None,
            "proof": None,
            "reason": "No isolated ablation measurements; empty datasets do not estimate or zero main/prior/setup costs.",
            "review": None,
            "setup": None,
            "training": None,
            "workload_specific": None,
        },
        "unperformed_component_ablations": [
            {
                "disposition": "retained_main_factor_comparison_not_isolated_component_ablation",
                "matched_isolated_comparison": False,
                "mechanism": "source_linked_native_semantic_context",
                "measured_ablation_attempt": False,
                "non_attributable_limitation": True,
            },
            {
                "disposition": "withdrawn_from_final_ablation_scope",
                "matched_isolated_comparison": False,
                "mechanism": "C_D_routing_and_governance",
                "measured_ablation_attempt": False,
                "non_attributable_limitation": True,
            },
            {
                "disposition": "withdrawn_from_final_ablation_scope",
                "matched_isolated_comparison": False,
                "mechanism": "C_no_route",
                "measured_ablation_attempt": False,
                "non_attributable_limitation": True,
            },
            {
                "disposition": "withdrawn_from_final_ablation_scope",
                "matched_isolated_comparison": False,
                "mechanism": "C_no_reuse",
                "measured_ablation_attempt": False,
                "non_attributable_limitation": True,
            },
            {
                "disposition": "withdrawn_from_final_ablation_scope",
                "matched_isolated_comparison": False,
                "mechanism": "local_warm_cache",
                "measured_ablation_attempt": False,
                "non_attributable_limitation": True,
            },
            {
                "disposition": "withdrawn_from_final_ablation_scope",
                "matched_isolated_comparison": False,
                "mechanism": "test_proof_reuse",
                "measured_ablation_attempt": False,
                "non_attributable_limitation": True,
            },
            {
                "disposition": "withdrawn_from_final_ablation_scope",
                "matched_isolated_comparison": False,
                "mechanism": "publication_comparison_efficacy",
                "measured_ablation_attempt": False,
                "non_attributable_limitation": True,
            },
            {
                "disposition": "withdrawn_from_final_ablation_scope",
                "matched_isolated_comparison": False,
                "mechanism": "translation_checks",
                "measured_ablation_attempt": False,
                "non_attributable_limitation": True,
            },
            {
                "disposition": "withdrawn_from_final_ablation_scope",
                "matched_isolated_comparison": False,
                "mechanism": "sealer_sequential_or_parallel",
                "measured_ablation_attempt": False,
                "non_attributable_limitation": True,
            },
            {
                "disposition": "withdrawn_from_final_ablation_scope",
                "matched_isolated_comparison": False,
                "mechanism": "parallel_preparation",
                "measured_ablation_attempt": False,
                "non_attributable_limitation": True,
            },
            {
                "disposition": "withdrawn_from_final_ablation_scope",
                "matched_isolated_comparison": False,
                "mechanism": "procedure_components",
                "measured_ablation_attempt": False,
                "non_attributable_limitation": True,
            },
            {
                "disposition": "diagnostic_only_cannot_promote_useful_progress",
                "matched_isolated_comparison": False,
                "mechanism": "deny_all",
                "measured_ablation_attempt": False,
                "non_attributable_limitation": True,
            },
        ],
        "uses_final_outcomes_or_partial_results": False,
        "withdrawn_planned_cells": withdrawn_cells,
    }

    dump(ABLATIONS / "manifest.json", manifest)
    print("retained_main_cells", 32)
    print("withdrawn_planned_cells", 160)
    print("measured_ablation_attempt_rows", 0)
    print("measured_ablation_resource_rows", 0)
    print("main_outcome_rows_included", 0)
    print("freeze_file_sha256", FREEZE_FILE_SHA)
    print("freeze_sha256", FREEZE_CANONICAL_SHA)
    print("original192_sha256", ORIGINAL192_SHA)
    print("attempts_sha256", EMPTY_SHA)
    print("resource_measurements_sha256", EMPTY_SHA)
    print("deviations_sha256", files["deviations.md"]["sha256"])
    print("ns017_main_bound", True)
    print("status", "scope_record_materialized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
