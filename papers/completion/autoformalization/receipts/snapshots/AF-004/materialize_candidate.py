#!/usr/bin/env python3
"""Build reviewable AF004 manifests; never assert unfinished isolation/annotation work is complete."""
import collections
import datetime as dt
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import shutil

from build_lexical_graph import PRIVATE, STAGE, save, sha, tokens

os.umask(0o077)
PREFIX = Path("papers/completion/autoformalization")
OUT = STAGE / "candidate" / PREFIX
SNAPSHOT = OUT / "receipts/snapshots/AF-004"


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def artifact(path):
    return {"path": str(path.relative_to(STAGE / "candidate")), "sha256": sha(path), "bytes": path.stat().st_size}


def main():
    graph = json.loads((PRIVATE / "full_graph.private.json").read_text())
    lexical = json.loads((STAGE / "lexical_graph_audit.json").read_text())
    semantic = json.loads((STAGE / "paraphrase_graph_audit.json").read_text())
    plan = json.loads((STAGE / "grouping_plan.json").read_text())
    assert graph["grouping_plan_sha256"] == sha(STAGE / "grouping_plan.json")
    assert semantic["private_graph_sha256"] == sha(PRIVATE / "full_graph.private.json")
    records = graph["records"]
    data_by_id = {r["record_id"]: r for r in (json.loads(line) for line in (PRIVATE / "raw/patent-legal-corpus-86c77cb6.documents.jsonl").open())}
    for r in records:
        r["normalized_source_unit_sha256"] = hashlib.sha256(" ".join(tokens(data_by_id[r["record_id"]]["text"])).encode()).hexdigest()
    def unique_units(indices):
        return {records[i]["normalized_source_unit_sha256"] for i in indices}
    components = list(graph["components"].values())
    # Freeze secret once. It controls deterministic assignment and prevents public hashes disclosing IDs.
    salt_path = PRIVATE / "partition_salt.private.bin"
    if not salt_path.exists():
        salt_path.write_bytes(secrets.token_bytes(32))
        salt_path.chmod(0o600)
    salt = salt_path.read_bytes()
    def order_key(indices):
        ids = sorted(records[i]["record_id"] for i in indices)
        return hmac.new(salt, canonical({"seed": 104729, "members": ids}), hashlib.sha256).hexdigest()
    components.sort(key=order_key)
    partitions = {s: [] for s in ["train", "selection", "fixed_canary", "final_test"]}
    partition_groups = collections.Counter()
    floor_possible = len(components) >= 23 and len(unique_units(range(len(records)))) >= 103
    if floor_possible:
        stop = 0
        while stop < len(components) and (stop < 20 or len(unique_units(partitions["final_test"])) < 100):
            partitions["final_test"].extend(components[stop])
            stop += 1
        if len(components) - stop < 3:
            floor_possible = False
            partitions = {s: [] for s in partitions}
        else:
            partition_groups["final_test"] = stop
            for i, group in enumerate(components[stop:]):
                split = ["train", "selection", "fixed_canary"][i % 3]
                partitions[split].extend(group)
                partition_groups[split] += 1
    partition_of = {i: split for split, indices in partitions.items() for i in indices}
    assert not floor_possible or len(partition_of) == len(records)
    all_edges = graph["edges"] + graph.get("paraphrase_edges", [])
    cross_edges = sum(partition_of.get(e["a"]) != partition_of.get(e["b"]) for e in all_edges)
    assert cross_edges == 0
    membership = {s: [records[i] for i in sorted(indices)] for s, indices in partitions.items()}
    save(PRIVATE / "partitions.private.json", {"seed": 104729, "grouping_plan_sha256": graph["grouping_plan_sha256"], "membership": membership, "source_sha256": graph["source_sha256"], "floor_possible": floor_possible})
    save(PRIVATE / "holdout_deny_index.private.json", {"normalized_source_sha256": sorted({r["normalized_source_unit_sha256"] for r in membership["final_test"]}), "source_id_sha256": sorted({hashlib.sha256(r["record_id"].encode()).hexdigest() for r in membership["final_test"]}), "purpose": "Trusted-runner admission filter only; never expose this index to provider context, never use as a training target"})
    SNAPSHOT.mkdir(parents=True, exist_ok=True)
    for directory in [OUT / "data", OUT / "evidence"]:
        directory.mkdir(parents=True, exist_ok=True)
    snapshot_sources = ["grouping_plan.json", "source_unit_accounting_addendum.json", "build_lexical_graph.py", "screen_paraphrases.py", "materialize_candidate.py", "verify_candidate.py", "data_admission.py", "lexical_graph_audit.json", "paraphrase_graph_audit.json", "lexical_graph.log", "paraphrase_graph.attempt1.log", "paraphrase_graph.log"]
    for name in snapshot_sources:
        shutil.copyfile(STAGE / name, SNAPSHOT / name)
    bridge = STAGE.parent / "af004_source_bridge"
    for name in ["patent-legal-corpus-86c77cb6.README.md", "patent-legal-corpus-86c77cb6.coverage.json"]:
        shutil.copyfile(bridge / name, SNAPSHOT / name)
    split_exports = {}
    if floor_possible:
        for split, indices in partitions.items():
            target = PRIVATE / "final_test.private.jsonl" if split == "final_test" else SNAPSHOT / (split + ".sources.jsonl")
            with target.open("w") as handle:
                for i in sorted(indices):
                    handle.write(json.dumps(data_by_id[records[i]["record_id"]], sort_keys=True) + "\n")
            target.chmod(0o600)
            split_exports[split] = ({"private_owner_only": True, "sha256": sha(target), "bytes": target.stat().st_size, "membership_disclosed": False} if split == "final_test" else artifact(target))
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    counts = {}
    for split, indices in partitions.items():
        representatives = {}
        for i in sorted(indices, key=lambda i: records[i]["record_id"]):
            representatives.setdefault(records[i]["normalized_source_unit_sha256"], records[i])
        counts[split] = {"natural_source_units": len(representatives), "natural_source_records": len(indices), "exact_normalized_alias_records": len(indices) - len(representatives), "operational_connected_components": partition_groups[split], "by_domain": dict(collections.Counter(r["family"] for r in representatives.values())), "by_domain_record_counts": dict(collections.Counter(records[i]["family"] for i in indices)), "by_source_time": dict(collections.Counter(r["current_through"] for r in representatives.values())), "component_record_size_histogram": dict(collections.Counter(len(g) for g in components if g and partition_of.get(g[0]) == split))}
    fixture = {"path": "external/ipfs_datasets/tests/fixtures/semantic_roundtrip/pilot_cases.json", "sha256": "6d34cdd1392d3a9964f04e4260f722e076ba7b96c3cdd2fc59749460756cf167", "source_revision": "ac82107e246b30e35a2bbdcf75e01370d22350c6", "observed_entries": 5, "admission": "excluded_synthetic_fixture", "natural_denominator": 0, "rights": "Repository license does not independently establish embedded fixture text provenance; fixture classification is sufficient for natural-data exclusion"}
    inventory = {
        "legal_policy": {"dataset": "justicedao/patent-legal-corpus", "revision": plan["source_revision"], "raw_content_sha256": graph["source_sha256"], "observed": lexical["input_records"], "eligible_records": lexical["eligible_natural_source_records"], "unique_normalized_source_units": len(unique_units(range(len(records)))), "exact_normalized_alias_records": len(records) - len(unique_units(range(len(records)))), "alias_policy": "Retain alias provenance in source exports but select one canonical representative per normalized source unit for annotation/evaluation. Aliases never inflate the100-unit floor.", "excluded": lexical["excluded_records"], "exclusion_reasons": lexical["exclusion_reason_counts"], "rights": "All upstream record metadata declares reviewed, redistribution_allowed=true, public-domain-US-government; dataset card declares CC0-1.0. These are preserved upstream declarations, not a new independent legal determination.", "time_semantics": "Per-record current_through/source_revision from upstream official edition metadata; no publication date inferred from download time", "source_body_location": "Owner-only private research-inputs; only qualified development split exports may be mounted for providers", "source_families": lexical["eligible_domain_counts"], "macro_source_editions": 4},
        "coding_requirements_and_implementation": {"candidate_dataset": "Publicus/skillcenter-ir", "revision": "2cc11a73403d03c0679ffa909c893ef6a850048a", "local_shard_rows": 4096, "local_shard_sha256": "bde002275f12f8a2e2fb4632ec5921eb3cf65babffb988872ead5679dc271fd5", "upstream_license_risk_allow_rows": 72, "upstream_license_risk_needs_review_rows": 4024, "admission": "pending_original_source_authorship_temporal_identity_and_record_rights_qualification", "natural_admitted": 0, "label_columns_read": False, "limitation": "Skill descriptions and auto-IR scores are not assumed to be human requirements, executable snippets, or semantic gold; no full remote corpus count is claimed local"},
        "trace_material": {"admission": "unavailable_no_qualified_natural_trace_artifact_discovered", "natural_admitted": 0, "remediation": "Acquire retained execution traces tied to exact natural source and executable versions, rights and time provenance; generated traces remain their own derived-data population"},
        "synthetic_fixture": fixture,
    }
    status = "candidate_partitioned_pending_access_enforcement_and_independence_review" if floor_possible else "incomplete_frozen_population_floor_unsatisfied"
    corpus = {"schema": "autoformalization-corpus-manifest/v2", "created_at": now, "status": status, "grouping_plan_sha256": graph["grouping_plan_sha256"], "inventories": inventory, "counts_by_split": counts, "full_route_scope": "Legal/policy natural cohort candidate populated; coding and trace provenance remain explicitly pending. This does not narrow the paper's full empirical route or claim experiments/annotation have run.", "private_inventory_commitment_sha256": sha(PRIVATE / "partitions.private.json"), "private_final_ids_disclosed": False, "source_artifacts": [artifact(SNAPSHOT / "patent-legal-corpus-86c77cb6.README.md"), artifact(SNAPSHOT / "patent-legal-corpus-86c77cb6.coverage.json")]}
    splits = {"schema": "autoformalization-source-partitions/v2", "created_at": now, "status": status, "assignment": plan["split_assignment"], "graph": {"base_structural_groups": lexical["base_structural_groups"], "after_lexical_union": lexical["connected_components_after_identity_and_lexical_union"], "after_fixed_encoder_union": semantic["components_after_full_graph_union"], "macro_editions": 4, "independence": "Operational whole-source components, not proven independent samples; source-edition/domain dependence must be retained in reported limitations and reviewed before confirmatory inference"}, "counts": counts, "exports": split_exports, "partition_membership_commitment_sha256": sha(PRIVATE / "partitions.private.json"), "holdout": {"state": "private_staged_not_released", "salt_published": False, "ids_in_public_manifests": False, "body_in_provider_exports": False, "semantic_gold": "pending_AF005", "release_rule": "Only root-authorized sealed harness with scoped final-test read after checkpoint/configuration/patch lock; append-only evaluation output cannot feed development"}}
    teachers = {"schema": "autoformalization-teacher-manifest/v2", "created_at": now, "semantic_gold": {"status": "pending_AF005_independent_candidate_blind_annotation", "existing_semantic_labels_used": 0, "rights_review_is_not_semantic_review": True}, "source_grouping_encoder": {"status": "actually_executed_preseal_only", "producer": semantic["embedding_producer"], "fulltext_windows": semantic["fulltext_windows"], "private_vector_sha256": semantic["private_encoder_artifact_sha256"], "purpose": "Fixed lexical/paraphrase leakage grouping only; never use holdout vectors as training targets or source-quality scores", "vectors_exported_to_provider": False}, "upstream_vector_exclusion": {"producer": "local-hashed-term-projection@1.0.0", "status": "excluded_from_semantic_embedding_and_teacher_claims", "targets_imported": 0}, "compiler_and_view_targets": {"status": "producer_interfaces_selected_in_AF003_but_dataset_targets_not_generated", "environment_manifest_sha256": sha(STAGE.parents[1] / "autoformalization/config/environment_manifest.json"), "targets_produced": 0}, "proof_feedback": {"status": "pending_actual_checker_feedback_task", "records": 0}, "learned_advice": {"status": "pending_training_and_promotion_tasks", "checkpoints": 0}, "mock_targets": {"semantic_claim_admission": False, "natural_gold_admission": False}}
    blockers = ["Actual provider/harness mount and network isolation has not been exercised by this isolated candidate builder; owner-only files and a locked flag alone do not prove criterion3.", "Operational part/chapter connected components require scientific review of macro-edition dependence before calling the frozen source-family/time heterogeneity floor satisfied.", "Independent semantic annotation/adjudication remains AF005;100 independently adjudicated final units have not yet been claimed.", "Coding requirements, implementation and trace populations are inventoried but not qualified; their empirical rows remain pending."]
    downstream_unmet_prerequisites = blockers[2:]
    blockers = blockers[:2]
    if not floor_possible:
        blockers.insert(0, "The conservative full graph cannot support20 final-test components plus100 natural units and nonempty train/selection/canary partitions. Additional independent qualified natural source families are required; no split was manufactured.")
    audit = {"schema": "autoformalization-split-audit/v2", "created_at": now, "status": status, "lexical": lexical, "paraphrase": {k: v for k, v in semantic.items() if k != "embedding_producer"}, "cross_partition_detected_graph_edges": cross_edges, "detected_graph_edges_total": len(all_edges), "checks": {"whole_part_chapter_adjacent_sections_unsplit": True, "identity_exact_near_duplicate_and_cross_view_detected_edges_unsplit": cross_edges == 0, "fixed_full_text_paraphrase_screen_executed": True, "prespecified_thresholds_unchanged": True, "all_records_accounted_for": len(records) + lexical["excluded_records"] == lexical["input_records"], "final_test_ge_20_operational_components": partition_groups["final_test"] >= 20, "final_test_ge_100_natural_units": len(unique_units(partitions["final_test"])) >= 100, "four_nonempty_partitions": all(partitions.values()), "holdout_paths_owner_only": all((p.stat().st_mode & 0o777) == 0o600 for p in PRIVATE.rglob("*") if p.is_file()), "scoped_provider_mount_deny_test": "pending_root_harness_enforcement", "same_user_host_access_security_boundary": False}, "blockers_before_AF004_acceptance": blockers, "public_data_contamination_limit": "This corpus is public and may exist in pretrained model data, host caches or public downloads. Secret assignment and scoped no-network mounts prevent declared workflow reads, not unknowable pretraining exposure. Development exports can permit complement inference if an actor independently obtains the full public corpus; no claim of cryptographic or adversarial secrecy is made.", "no_label_or_body_output": True, "semantic_or_benchmark_results_claimed": False}
    corpus["population_limitations"] = {"fixed_one_shot_allocation": f"The giant derivative-connected component remains whole, yielding {counts['train']['natural_source_units']} training / {counts['selection']['natural_source_units']} selection / {counts['fixed_canary']['natural_source_units']} canary versus {counts['final_test']['natural_source_units']} unique final units. Do not rebalance or retry the salt after this result.", "development_domain": "CFR legal material only; no cross-domain training capability inferred", "statistics": "Four broad official editions remain correlated; operational source components are not20independent sampled corpora."}
    audit["downstream_unmet_prerequisites"] = downstream_unmet_prerequisites
    audit["dependency_boundary"] = "AF005independent annotation follows AF004. Pending annotation is not a circular prerequisite for completing the corpus task;100adjudicated semantic results remain unmeasured until that later work."
    for path, payload in [(OUT / "data/corpus_manifest.json", corpus), (OUT / "data/splits.json", splits), (OUT / "data/teacher_manifest.json", teachers), (OUT / "evidence/split_audit.json", audit)]:
        save(path, payload)
    review = {"candidate_root": str(STAGE / "candidate"), "generated_at": now, "status": status, "files": [artifact(p) for p in sorted(OUT.rglob("*")) if p.is_file()], "receipt_created": False, "reason": "An AF004completed receipt would overstate pending isolation and independence qualification. Root owns integration and native acceptance.", "split_counts": counts, "blockers": blockers, "private_root": str(PRIVATE)}
    save(STAGE / "review.json", review)
    print(json.dumps({"status": status, "split_counts": counts, "candidate_files": len(review["files"]), "receipt_created": False}, sort_keys=True))


if __name__ == "__main__":
    main()
