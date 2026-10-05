"""Root-owned, file-only preparation of exact observed publication facts."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
Q = ROOT.parents[1] / "qualification/codebase_ir/ranker-real-curvature-20261005-01"


def pin(path):
    path = Path(path).resolve(strict=True); raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def main():
    review = Q / "qualified-review-01.json"; seal_path = Q / "file-only-seal-01.json"
    assert pin(review)["sha256"] == "2c98df30a37fecffff99340d447dcf548c6c244a53223cbed39c914bb0e9238c"
    assert pin(seal_path)["sha256"] == "6c281bd21da026b27797f78f98d0932bad4e7a115779a4fc348ee6987f30af15"
    seal = json.loads(seal_path.read_bytes())
    documents = {"qualified_review": pin(review), "file_seal": pin(seal_path),
        "numeric_binding": pin(Q / "evidence/numeric-01/numeric-binding.json"),
        "metadata_readback": pin(Q / "evidence/metadata-01/metadata-readback.json"),
        "mathematical_mapping": pin(Q / "math/qualified-proof-mapping-01.json"),
        "numeric_source_audit": pin(Q / "proof-cache/final-numeric-coordinate-source-audit-01.json"),
        "cache_join_result": pin(Q / "evidence/cache-joins-02/cache-join-result.json"),
        "publication_source_review": pin(ROOT.parent / "ranker-curvature-publication-source-review-20261005-01/source-review-01.json")}
    roles = {"positive_native_checks": [], "negative_native_checks": [], "qualified_cache_acceptances": [],
        "original_numeric_binding": "numeric_binding", "native_metadata_readback": "metadata_readback",
        "failure_and_call_accounting": "qualified_review"}
    facts = []
    def fact(document, pointer, value):
        facts.append({"document": document, "pointer": pointer, "equals": value})
    boundaries = {"full_task_satisfaction": "unknown", "all32_governing_RPI_exits": "OPEN",
        "python_ranker_source_equivalence_proved": False, "binary64_error_bound_proved": False,
        "historical_execution_origin_proved": False, "global_optimizer_convergence_proved": False,
        "proof_authority": False, "execution_authority": False, "completion_authority": False,
        "planner_activation": False, "official_benchmark_score": None, "all_failed_attempts_retained": True,
        "new_public_fits": 0, "new_ranker_training_trace_replays": 0}
    for key, value in boundaries.items(): fact("qualified_review", "/" + key, value)
    for key, value in {"schema": "ranker-real-curvature-closed-qualification-review@1", "status": "passed",
        "native_lean_calls": 19, "qualified_positive_native_lean_checks": 10, "genuine_negative_native_lean_checks": 1,
        "inconclusive_native_lean_checks_retained": 8, "selected_pure_test_executions": 249,
        "all_failed_owned_phase_count": 10, "metadata_family_count": 32, "metadata_payloads": 4378,
        "cache_same_query_hits": 10, "cache_changed_dimension_misses": 230,
        "prior4348_payloads_preserved_exactly": True, "contracts_payloads_unchanged": True,
        "original_real_profile_curvature_qualified": True, "original_real_one_step_descent_qualified": True,
        "native_solver_and_metadata_limits_unchanged": True, "all_owned_leases_drained": True}.items():
        fact("qualified_review", "/" + key, value)
    for path in sorted((Q / "evidence").glob("lean-*/check-result.json")):
        body = json.loads(path.read_bytes())
        if body["status"] not in ("passed", "rejected"): continue
        name = path.parent.name.replace("-", "_")
        documents[name] = pin(path)
        roles["positive_native_checks" if body["status"] == "passed" else "negative_native_checks"].append(name)
        for key in ("schema", "status", "expected_success", "matches_expectation", "native_invocations", "native_bounds",
            "compiled_artifacts", "theorem_axiom_output", "source", "augmented_source", "environment_manifest"):
            fact(name, "/" + key, body[key])
    for path in sorted((Q / "evidence/cache-joins-02/joins").glob("*.cache-entry.json")):
        name = "cache_" + path.name.split(".")[0].replace("-", "_")
        body = json.loads(path.read_bytes()); documents[name] = pin(path); roles["qualified_cache_acceptances"].append(name)
        for key in ("schema", "status", "cache_key_sha256", "cache_dimensions", "native_check_sha256", "theorem_row"):
            fact(name, "/" + key, body[key])
    for key in ("schema", "status", "corpus_sha256", "pair_count", "dimension", "native_mu_exact", "native_eta_exact",
        "feature_profile_sha256", "difference_vectors_sha256", "train_pairs_sha256", "native_update_profile_sha256",
        "exact_eta_times_conservative_L_le_one", "exact_eta_times_mean_L_le_one", "prior_trace_replayed_or_revalidated_here"):
        fact("numeric_binding", "/" + key, json.loads(Path(documents["numeric_binding"]["path"]).read_bytes())[key])
    for key, value in {"schema": "ranker-real-curvature-native-metadata-readback@1", "status": "passed",
        "fresh_process_readback_verified": True, "all_payload_rows_read_back_exactly": True,
        "prior4348_payload_rows_preserved_exactly": True, "contracts_payloads_unchanged": True,
        "metadata_family_count": 32, "metadata_row_count": 4378}.items(): fact("metadata_readback", "/" + key, value)
    fact("metadata_readback", "/fresh_process_readback/verified", True)
    fact("cache_join_result", "/pure_lookup_metrics", {"same_query_hits": 10, "changed_dimension_queries": 230, "changed_dimension_misses": 230})
    fact("cache_join_result", "/prior_payloads_exact_and_order_preserved", True)
    fact("mathematical_mapping", "/status", "passed_file_only_actual_qualified_mathematical_mapping")
    fact("publication_source_review", "/status", "passed_source_only_no_remaining_blocker")
    profile = {"raw_population_max": 320 * 1024**2, "per_file_max": 16 * 1024**2,
        "per_decoded_container_max": 16 * 1024**2, "compressed_shard_max": 256 * 1024**2,
        "aggregate_decoded_work_max": 1024**3, "wall_seconds": 180, "members_max": 10000, "depth_max": 6,
        "zstd_arguments": ["-T1", "-3"], "member_readback_profile": "same_first_decoded_tar_and_member_streams@1",
        "duplicate_verification_decoder_invocations": 0,
        "authorization_scope": "explicit root publication-only320MiB raw/1GiB decoded; native limits unchanged",
        "authorization_reason": "final root seal273066128 bytes/1080 regular leaves exceeds256MiB; retain all failures and22 complete dependency profiles"}
    policy = ROOT / "required-facts.json"; assert not policy.exists()
    policy.write_text(json.dumps(facts, sort_keys=True, indent=2) + "\n")
    plan = ROOT / "plan.json"; assert not plan.exists()
    additions = [str(path) for path in sorted(ROOT.iterdir()) if path.is_file()]
    additions += [str(plan), str(seal_path), documents["publication_source_review"]["path"],
        str(ROOT.parent / "ranker-curvature-publication-source-review-20261005-01/review_source_01.py")]
    body = {"schema": "ranker-curvature-publication-plan@1", "source_and_artifacts_quiet": True,
        "scope_root": str(Q), "excluded_dependency_subtrees": list(map(str, (Q / "environment/mathlib4", Q / "environment/cache"))),
        "publication_profile": profile, "documents": documents, "semantic_roles": roles, "semantic_policy": pin(policy),
        "expected_sealed_file_count": len(seal["files"]), "expected_sealed_file_bytes": sum(row["bytes"] for row in seal["files"]),
        "excluded_zero_byte_locks": [row["path"] for row in seal["files"] if row["bytes"] == 0 and row["path"].endswith(".lock")],
        "excluded_fixture_symlinks": seal["fixture_symlinks"],
        "external_dependencies": {"official_repository": "https://github.com/leanprover-community/mathlib4",
            "mathlib_revision": "5ed2965256430c3649e86755f9576b54eca72435", "raw_dependency_bodies_published": False,
            "environment_manifests": [row for row in seal["files"] if Path(row["path"]).name == "environment-manifest.json"],
            "reproduction_notes": "Restore this owned bundle and prior frozen source/corpus evidence at their declared paths; use Lean4.34.0 and the exact official Mathlib revision/lake manifest. Hydrate the declared imports and verify each complete environment profile and local compiled-module binding before reproducing a check. Raw dependency/cache bodies are local, not part of this public bundle; dependency runtime opens and full Python stdlib closure are not claimed."},
        "explicit_addition_paths": additions}
    plan.write_text(json.dumps(body, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"plan": pin(plan), "policy": pin(policy), "documents": len(documents), "facts": len(facts),
        "sealed_files": len(seal["files"]), "sealed_bytes": sum(row["bytes"] for row in seal["files"])}))


if __name__ == "__main__": main()
