"""Declaration-only cache unit fixtures; no actual or false Lean job is run.

Synthetic receipts model already qualified inputs for pure structural controls.
Their fixture data is not original native execution evidence or an RPI proof.
"""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("real_curvature_proof_cache_units",
                                            HERE / "real_curvature_proof_cache.py")
cache = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cache)


def _hash(label):
    return hashlib.sha256(label.encode()).hexdigest()


def _file(path, label, size=32, *, complete=False):
    result = {"path": path, "bytes": size, "sha256": _hash(label)}
    if complete:
        result["complete"] = True
    return result


def _rebind_result(arguments):
    result = arguments["qualified_result"]
    result["native_check_sha256"] = cache.canonical_sha256(result["native_check"])
    arguments["expected_qualified_result_sha256"] = cache.canonical_sha256(result)


@pytest.fixture(scope="module")
def declaration_only_arguments():
    checker_text = "# Declaration-only synthetic checker fixture; never executed.\n"
    checker_sha = _hash(checker_text)
    dimensions = {"schema": cache.DIMENSIONS_SCHEMA, "corpus_sha256": "sha256:" + _hash("unit-corpus"),
        "native_mu_exact": {"numerator": "1", "denominator": "4"},
        "native_eta_exact": {"numerator": "1", "denominator": "8"},
        "theorem": "UnitFixture.quadraticBound", "evidence_kind": "real_candidate_quadratic_curvature",
        "translation_status": "explicit_real_model_without_native_source_equivalence",
        "retention_format": "bounded_lean_files@1",
        "authority_profile": deepcopy(cache._AUTHORITY_PROFILE),
        **{key: _hash("unit-" + key) for key in cache._DIGEST_DIMENSIONS}}
    dimensions["checker_source_sha256"] = checker_sha
    dimensions["assumptions_sha256"] = cache.canonical_sha256(["propext"])
    dimensions["retention_profile_sha256"] = cache.canonical_sha256(cache._ORDINARY_RETENTION_PROFILE)
    check = {"schema": "ranker-real-curvature-bounded-analytic-lean-check@1", "status": "passed",
        "expected_success": True, "matches_expectation": True, "native_invocations": 1, "returncode": 0,
        **{k: False for k in ("timed_out", "cancelled", "unavailable", "resource_exhausted", "output_truncated",
            "workspace_limit_exceeded", "proof_authority", "execution_authority", "completion_authority",
            "planner_activation", "python_ranker_source_equivalence_proved", "binary64_error_bound_proved",
            "historical_execution_origin_proved", "optimizer_convergence_proved")},
        "workspace_cleaned": True, "artifact_anomalies": [], "axiom_report_error": None,
        "post_call_binding_error": None, "full_task_satisfaction": "unknown",
        "all32_governing_RPI_exits": "OPEN", "official_benchmark_score": None,
        "proof_source_in_frozen_per_job_environment": True,
        "direct_imports_and_implicit_Init_in_frozen_registry": True,
        "root_lease_owned_by_caller": True,
        "outer120s_and_frozen_project_import_guard_owned_by_caller": True,
        "environment_actual_runtime_open_trace_claimed": False,
        "actual_root_lease": {"cpu_slots": 1, "memory_mb": 2048, "child_process_slots": 4,
            "gpu_memory_mb": 0, "unified_memory_mb": 0, "requires_gpu": False,
            "cancelled": False, "released": False, "owner_pid": 1, "lease_id": "1" * 32},
        "native_bounds": dict(cache._NATIVE_BOUNDS),
        "source": _file("/declaration-only/Fixture.lean", "proof-source"),
        "augmented_source": _file("/declaration-only/output/Fixture.lean", "augmented-source"),
        "environment_manifest": _file("/declaration-only/environment.json", "environment"),
        "compiled_artifacts": [_file("/declaration-only/output/Fixture.olean", "synthetic-object", complete=True)],
        "theorem_axiom_output": [{"theorem": "UnitFixture.quadraticBound", "axioms": ["propext"], "report_occurrences": 1}],
        "allowed_standard_axioms": ["Classical.choice", "Quot.sound", "propext"]}
    dimensions["proof_source_sha256"] = check["source"]["sha256"]
    dimensions["environment_manifest_sha256"] = check["environment_manifest"]["sha256"]
    result = {"schema": cache.RESULT_SCHEMA, "cache_dimensions_sha256": cache.canonical_sha256(dimensions),
        "native_check": check, "native_check_sha256": cache.canonical_sha256(check),
        "checker_source": {"path": "/declaration-only/checker.py", "bytes": len(checker_text.encode()), "sha256": checker_sha},
        "checker_source_text": checker_text,
        **{k: dimensions[k] for k in ("checker_source_sha256", "theorem_statement_sha256", "numeric_binding_sha256",
            "translation_profile_sha256", "verification_policy_sha256", "network_policy_sha256")}}
    return {"cache_dimensions": dimensions, "expected_cache_dimensions_sha256": cache.canonical_sha256(dimensions),
        "qualified_result": result, "expected_qualified_result_sha256": cache.canonical_sha256(result)}


@pytest.fixture(scope="module")
def declaration_only_entry(declaration_only_arguments):
    return cache.build_real_curvature_proof_cache_entry(**declaration_only_arguments)


def _lookup(arguments, entry):
    return cache.lookup_real_curvature_proof_cache(**arguments, entry=entry,
                                                 expected_entry_sha256=cache.canonical_sha256(entry))


def test_exact_dimensions_return_only_advisory_copy(declaration_only_arguments, declaration_only_entry):
    row = _lookup(declaration_only_arguments, declaration_only_entry)
    assert row["status"] == "kernel_real_statement_bound"
    assert row["theorem"] == "UnitFixture.quadraticBound" and row["assumptions"] == ["propext"]
    assert row["evidence_kind"] == "real_candidate_quadratic_curvature" and row["advisory_only"] is True
    assert all(row[k] is False for k in cache._AUTHORITY_FIELDS)
    assert row["full_task_satisfaction"] == "unknown" and row["official_benchmark_score"] is None
    row["theorem"] = "Caller.changedItsCopy"
    assert declaration_only_entry["theorem_row"]["theorem"] == "UnitFixture.quadraticBound"
    assert declaration_only_entry["native_prover_calls_here"] == 0
    assert declaration_only_entry["filesystem_or_metadata_or_network_operations_here"] == 0
    assert declaration_only_entry["ProgramContract_or_RPI_or_core_policy_mutated"] is False


@pytest.mark.parametrize("dimension", ["schema", "corpus_sha256", "feature_profile_sha256", "difference_vectors_sha256",
    "train_pairs_sha256", "native_update_profile_sha256", "native_mu_exact", "native_eta_exact", "theorem",
    "evidence_kind", "theorem_statement_sha256", "proof_source_sha256", "assumptions_sha256", "checker_source_sha256",
    "environment_manifest_sha256", "numeric_binding_sha256", "translation_profile_sha256", "translation_status",
    "verification_policy_sha256", "network_policy_sha256", "authority_profile", "retention_format",
    "retention_profile_sha256"])
def test_every_required_cache_dimension_change_is_a_miss(declaration_only_arguments, declaration_only_entry, dimension):
    arguments = deepcopy(declaration_only_arguments)
    dimensions = arguments["cache_dimensions"]
    if dimension in ("native_mu_exact", "native_eta_exact"):
        dimensions[dimension] = {"numerator": "1", "denominator": "3"}
    elif dimension == "authority_profile":
        dimensions[dimension]["proof_authority"] = True
    elif dimension == "corpus_sha256":
        dimensions[dimension] = "sha256:" + "0" * 64
    elif dimension == "evidence_kind":
        dimensions[dimension] = "real_directional_second_derivative"
    elif dimension == "theorem":
        dimensions[dimension] = "UnitFixture.differentStatement"
    elif dimension == "retention_format":
        dimensions[dimension] = "bounded_lean_chunks@1"
    else:
        dimensions[dimension] = "0" * 64 if dimension.endswith("sha256") else "changed-declaration"
    arguments["expected_cache_dimensions_sha256"] = cache.canonical_sha256(dimensions)
    assert _lookup(arguments, declaration_only_entry) is None


def test_missing_required_dimension_is_a_miss(declaration_only_arguments, declaration_only_entry):
    arguments = deepcopy(declaration_only_arguments)
    arguments["cache_dimensions"].pop("environment_manifest_sha256")
    arguments["expected_cache_dimensions_sha256"] = cache.canonical_sha256(arguments["cache_dimensions"])
    assert _lookup(arguments, declaration_only_entry) is None


@pytest.mark.parametrize("fault", ["rejected", "inconclusive", "negative_expectation", "unregistered_theorem",
    "nonstandard_axiom", "source_swap", "environment_swap", "proof_caps_swap", "checker_bytes_swap",
    "truncated_object", "native_authority_promotion", "unfrozen_import_registry", "lease_profile_swap",
    "oversized_ordinary_object"])
def test_newly_resealed_qualified_claims_do_not_bypass_native_evidence_checks(declaration_only_arguments, fault):
    arguments = deepcopy(declaration_only_arguments)
    result, check = arguments["qualified_result"], arguments["qualified_result"]["native_check"]
    if fault in ("rejected", "inconclusive"):
        check["status"] = fault
    elif fault == "negative_expectation":
        check["expected_success"] = False
    elif fault == "unregistered_theorem":
        check["theorem_axiom_output"][0]["theorem"] = "UnitFixture.anotherStatement"
    elif fault == "nonstandard_axiom":
        check["theorem_axiom_output"][0]["axioms"].append("sorryAx")
    elif fault == "source_swap":
        check["source"]["sha256"] = "0" * 64
    elif fault == "environment_swap":
        check["environment_manifest"]["sha256"] = "0" * 64
    elif fault == "proof_caps_swap":
        check["native_bounds"]["max_output_bytes"] *= 2
    elif fault == "checker_bytes_swap":
        result["checker_source_text"] += "# replaced bytes\n"
    elif fault == "truncated_object":
        check["compiled_artifacts"][0]["complete"] = False
    elif fault == "unfrozen_import_registry":
        check["direct_imports_and_implicit_Init_in_frozen_registry"] = False
    elif fault == "lease_profile_swap":
        check["actual_root_lease"]["cpu_slots"] = 2
    elif fault == "oversized_ordinary_object":
        check["compiled_artifacts"][0]["bytes"] = 65537
    else:
        check["optimizer_convergence_proved"] = True
    _rebind_result(arguments)
    with pytest.raises(cache.RealCurvatureCacheError):
        cache.build_real_curvature_proof_cache_entry(**arguments)


@pytest.mark.parametrize("mutation", ["authority", "theorem", "evidence_kind", "translation", "compiled_object"])
def test_entry_self_reseal_and_new_external_entry_pin_cannot_forge_advisory_claims(declaration_only_arguments, declaration_only_entry, mutation):
    forged = deepcopy(declaration_only_entry)
    if mutation == "authority":
        forged["theorem_row"]["proof_authority"] = True
    elif mutation == "theorem":
        forged["theorem_row"]["theorem"] = "Forged.actualNativeHessian"
    elif mutation == "evidence_kind":
        forged["theorem_row"]["evidence_kind"] = "real_directional_second_derivative"
    elif mutation == "translation":
        forged["theorem_row"]["translation_status"] = "native_source_equivalence_proved"
    else:
        forged["complete_compiled_artifact_sha256s"] = ["0" * 64]
    forged.pop("cache_entry_sha256")
    forged["cache_entry_sha256"] = cache.canonical_sha256(forged)
    assert _lookup(declaration_only_arguments, forged) is None


def test_changed_result_without_new_trusted_pin_is_a_miss(declaration_only_arguments, declaration_only_entry):
    arguments = deepcopy(declaration_only_arguments)
    arguments["qualified_result"]["native_check"]["proof_authority"] = True
    assert _lookup(arguments, declaration_only_entry) is None


def test_authority_promotion_rejected_even_after_dimension_and_result_reseals(declaration_only_arguments):
    arguments = deepcopy(declaration_only_arguments)
    arguments["cache_dimensions"]["authority_profile"]["whole_source_runtime_equivalence_proved"] = True
    dimensions_pin = cache.canonical_sha256(arguments["cache_dimensions"])
    arguments["expected_cache_dimensions_sha256"] = dimensions_pin
    arguments["qualified_result"]["cache_dimensions_sha256"] = dimensions_pin
    _rebind_result(arguments)
    with pytest.raises(cache.RealCurvatureCacheError, match="operational authority"):
        cache.build_real_curvature_proof_cache_entry(**arguments)


@pytest.mark.parametrize("pin", [None, True, "A" * 64])
def test_malformed_external_entry_pin_misses(declaration_only_arguments, declaration_only_entry, pin):
    assert cache.lookup_real_curvature_proof_cache(**declaration_only_arguments, entry=declaration_only_entry,
                                                 expected_entry_sha256=pin) is None


def _reseal_manifest(check):
    raw = (json.dumps(check["retention_manifest_body"], sort_keys=True, separators=(",", ":")) + "\n").encode()
    check["retention_manifest"]["bytes"] = len(raw)
    check["retention_manifest"]["sha256"] = hashlib.sha256(raw).hexdigest()


@pytest.fixture(scope="module")
def declaration_only_chunk_arguments(declaration_only_arguments):
    arguments = deepcopy(declaration_only_arguments)
    dimensions, check = arguments["cache_dimensions"], arguments["qualified_result"]["native_check"]
    dimensions["retention_format"] = "bounded_lean_chunks@1"
    dimensions["retention_profile_sha256"] = cache.canonical_sha256(cache._CHUNK_RETENTION_PROFILE)
    check.update(schema="ranker-real-curvature-bounded-analytic-lean-check@2",
        native_lean_invocations=1, native_lean_returncode=0, retention_format="bounded_lean_chunks@1",
        retention_profile=deepcopy(cache._CHUNK_RETENTION_PROFILE),
        retention_profile_sha256=dimensions["retention_profile_sha256"],
        retention_helper=_file("/declaration-only/RetainLeanProof.py", "unit-helper"),
        python_executable=_file("/declaration-only/python", "unit-python"),
        reconstruction_validation_error=None)
    parts = [b"A" * 65536, b"B" * 65536]
    raw = b"".join(parts)
    chunks = [{"name": "LeanProofChunk%03d.bin" % index, "bytes": len(part),
               "sha256": hashlib.sha256(part).hexdigest()} for index, part in enumerate(parts)]
    object_descriptor = {"name": "Fixture.olean", "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                         "chunks": [row["name"] for row in chunks]}
    check["compiled_artifacts"] = [{"path": "/declaration-only/output/Fixture.olean", "bytes": len(raw),
        "sha256": object_descriptor["sha256"], "complete": True, "retention_format": "bounded_lean_chunks@1"}]
    check["retained_chunk_artifacts"] = [{"path": "/declaration-only/output/" + row["name"],
        "bytes": row["bytes"], "sha256": row["sha256"], "complete": True} for row in chunks]
    check["retention_manifest_body"] = {"schema": "bounded_lean_chunks@1", "status": "complete",
        "retention_profile_sha256": dimensions["retention_profile_sha256"], "native_lean_invocations": 1,
        "native_lean_returncode": 0, "objects": [object_descriptor], "chunks": chunks,
        "aggregate_raw_object_bytes": len(raw)}
    check["retention_manifest"] = _file("/declaration-only/output/LeanProofChunks.json", "temporary", complete=True)
    _reseal_manifest(check)
    check["reconstruction_validation"] = {"status": "passed", "manifest_complete": True,
        "exact_chunk_population": True, "aggregate_raw_object_bytes": len(raw),
        "reconstructed_object_count": 1, "chunk_count": len(chunks),
        "reconstructed_full_module_bodies_may_exceed_native_per_file_capture": True}
    arguments["expected_cache_dimensions_sha256"] = cache.canonical_sha256(dimensions)
    arguments["qualified_result"]["cache_dimensions_sha256"] = arguments["expected_cache_dimensions_sha256"]
    _rebind_result(arguments)
    return arguments


def test_complete_chunk_chain_accepts_large_object_under_unchanged_per_file_caps(declaration_only_chunk_arguments):
    entry = cache.build_real_curvature_proof_cache_entry(**declaration_only_chunk_arguments)
    assert _lookup(declaration_only_chunk_arguments, entry)["status"] == "kernel_real_statement_bound"
    check = declaration_only_chunk_arguments["qualified_result"]["native_check"]
    assert check["compiled_artifacts"][0]["bytes"] == 131072 > check["native_bounds"]["max_output_bytes"]
    assert all(row["bytes"] <= 65536 for row in check["retained_chunk_artifacts"])
    assert entry["fresh_chunk_reconstruction_performed_here"] is False
    assert entry["retention_format"] == "bounded_lean_chunks@1"


@pytest.mark.parametrize("fault", ["missing_chunk", "changed_chunk_digest", "manifest_digest",
    "chunk_order", "object_digest", "reconstruction_count", "aggregate_size", "profile_swap", "combined_input_size"])
def test_resealed_chunk_claims_require_complete_manifest_population_and_reconstruction_join(declaration_only_chunk_arguments, fault):
    arguments = deepcopy(declaration_only_chunk_arguments)
    check = arguments["qualified_result"]["native_check"]
    if fault == "missing_chunk":
        check["retained_chunk_artifacts"].pop()
    elif fault == "changed_chunk_digest":
        check["retained_chunk_artifacts"][0]["sha256"] = "0" * 64
    elif fault == "manifest_digest":
        check["retention_manifest"]["sha256"] = "0" * 64
    elif fault == "chunk_order":
        check["retention_manifest_body"]["objects"][0]["chunks"].reverse()
        _reseal_manifest(check)
    elif fault == "object_digest":
        check["compiled_artifacts"][0]["sha256"] = "0" * 64
    elif fault == "reconstruction_count":
        check["reconstruction_validation"]["chunk_count"] = 1
    elif fault == "aggregate_size":
        check["retention_manifest_body"]["aggregate_raw_object_bytes"] = 3997697
        check["reconstruction_validation"]["aggregate_raw_object_bytes"] = 3997697
        _reseal_manifest(check)
    elif fault == "combined_input_size":
        check["retention_helper"]["bytes"] = 262144
    else:
        check["retention_profile"]["native_per_file_capture_bytes"] = 131072
        check["retention_profile_sha256"] = cache.canonical_sha256(check["retention_profile"])
        arguments["cache_dimensions"]["retention_profile_sha256"] = check["retention_profile_sha256"]
        arguments["expected_cache_dimensions_sha256"] = cache.canonical_sha256(arguments["cache_dimensions"])
        arguments["qualified_result"]["cache_dimensions_sha256"] = arguments["expected_cache_dimensions_sha256"]
    _rebind_result(arguments)
    with pytest.raises(cache.RealCurvatureCacheError):
        cache.build_real_curvature_proof_cache_entry(**arguments)
