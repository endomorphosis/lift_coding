"""Pure advisory cache for independently pinned qualified real-model proofs.

No proof, numeric replay, filesystem, database, network or policy operation
occurs here. The caller retains actual checker evidence and supplies trusted
external complete-object pins. These pins do not authenticate their own origin.
"""
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
import re

DIMENSIONS_SCHEMA = "terminal-ranker-real-curvature-cache-dimensions@2"
RESULT_SCHEMA = "terminal-ranker-real-curvature-qualified-cache-result@2"
ENTRY_SCHEMA = "terminal-ranker-real-curvature-proof-cache-entry@2"
MAX_BYTES = 262144
_AXIOMS = frozenset(("propext", "Classical.choice", "Quot.sound"))
_EVIDENCE = frozenset(("real_candidate_quadratic_curvature", "real_scalar_derivative",
    "real_directional_second_derivative", "real_logistic_coefficient_bound",
    "real_coordinate_geometry", "exact_original_rational_arithmetic",
    "real_objective_gradient_identity", "real_objective_step_descent",
    "original_real_profile_curvature", "original_real_profile_descent"))
_DIGEST_DIMENSIONS = tuple("feature_profile_sha256 difference_vectors_sha256 train_pairs_sha256 "
    "native_update_profile_sha256 theorem_statement_sha256 proof_source_sha256 "
    "assumptions_sha256 checker_source_sha256 environment_manifest_sha256 "
    "numeric_binding_sha256 translation_profile_sha256 verification_policy_sha256 "
    "network_policy_sha256 retention_profile_sha256".split())
_DIMENSION_FIELDS = frozenset(("schema", "corpus_sha256", "native_mu_exact", "native_eta_exact",
    "theorem", "evidence_kind", "translation_status", "authority_profile", "retention_format", *_DIGEST_DIMENSIONS))
_AUTHORITY_FIELDS = tuple("semantic_alignment_verified source_semantics_verified proof_authority formalization_authority "
    "execution_authority completion_authority mutation_authority omission_authority behavioral_satisfaction "
    "whole_program_proved asymptotic_optimizer_convergence_proved planner_activation whole_source_runtime_equivalence_proved "
    "binary64_error_bound_proved global_optimizer_convergence_proved multivariate_Frechet_Hessian_identity_proved "
    "historical_execution_origin_authenticated_here".split())
_AUTHORITY_PROFILE = {**{k: False for k in _AUTHORITY_FIELDS}, "full_task_satisfaction": "unknown",
    "all32_governing_RPI_exits": "OPEN", "official_benchmark_score": None}
_ROOT_JOIN_FIELDS = frozenset(("schema", "cache_dimensions_sha256", "native_check", "native_check_sha256",
    "checker_source_sha256", "checker_source", "checker_source_text", "theorem_statement_sha256", "numeric_binding_sha256",
    "translation_profile_sha256", "verification_policy_sha256", "network_policy_sha256"))
_NATIVE_BOUNDS = {"timeout_seconds": 20, "cpu_seconds": 20, "max_input_bytes": 262144,
    "max_output_bytes": 65536, "max_workspace_bytes": 16777216}
_ORDINARY_RETENTION_PROFILE = {"schema": "bounded_lean_files@1", "max_artifact_bytes": 65536,
    "max_compiled_object_count": 4, "native_bounds": dict(_NATIVE_BOUNDS)}
_CHUNK_RETENTION_PROFILE = {"format": "bounded_lean_chunks@1", "native_per_file_capture_bytes": 65536,
    "native_max_declared_outputs": 64, "chunk_bytes": 65536, "max_chunk_files": 61,
    "max_raw_object_bytes": 3997696, "max_manifest_bytes": 65536, "max_object_files": 4,
    "object_suffixes": [".olean", ".olean.private", ".olean.server", ".ir"],
    "native_cpu_seconds": 20, "native_wall_seconds": 20, "native_workspace_bytes": 16777216,
    "native_max_source_bytes": 262144, "compression": "none",
    "chunk_order": "consecutive-global-index-and-object-concatenation"}


class RealCurvatureCacheError(ValueError):
    """An exact cache dimension or qualified result prerequisite differs."""


def _need(condition, message):
    if condition is not True:
        raise RealCurvatureCacheError(message)


def _wire(value):
    pending, nodes = [(value, 0)], 0
    while pending:
        item, depth = pending.pop()
        nodes += 1
        _need(nodes <= 65536 and depth <= 32, "bounded exact cache JSON required")
        if type(item) is dict:
            _need(len(item) <= 4096 and all(type(k) is str for k in item), "exact cache JSON keys required")
            pending.extend((v, depth + 1) for v in item.values())
        elif type(item) is list:
            _need(len(item) <= 4096, "bounded exact cache JSON list required")
            pending.extend((v, depth + 1) for v in item)
        elif type(item) is str:
            _need(len(item.encode()) <= MAX_BYTES, "bounded cache JSON string required")
        elif type(item) is int:
            _need(item.bit_length() <= 4096, "bounded cache JSON integer required")
        elif type(item) is float:
            # Actual native receipts contain finite elapsed times and limits.
            _need(item == item and abs(item) != float("inf"), "finite cache JSON float required")
        else:
            _need(type(item) in (bool, type(None)), "exact plain cache JSON values required")
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()
    _need(len(raw) <= MAX_BYTES, "bounded complete cache object required")
    return raw


def canonical_sha256(value):
    """ASCII canonical complete-object pin, including any self field."""
    return hashlib.sha256(_wire(value)).hexdigest()


def _hex(value):
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _pinned(value, expected):
    _need(_hex(expected), "independent lowercase complete-object SHA256 pin required")
    _need(type(value) is dict and canonical_sha256(value) == expected, "external cache input pin differs")


def _positive_rational(value):
    _need(type(value) is dict and set(value) == {"numerator", "denominator"}
          and all(type(v) is str and re.fullmatch(r"[1-9][0-9]{0,4095}", v) for v in value.values()),
          "canonical positive rational dimension required")
    q = Fraction(int(value["numerator"]), int(value["denominator"]))
    _need(str(q.numerator) == value["numerator"] and str(q.denominator) == value["denominator"],
          "reduced rational cache dimension required")


def _dimensions(value):
    _need(type(value) is dict and set(value) == _DIMENSION_FIELDS and value["schema"] == DIMENSIONS_SCHEMA,
          "all exact cache dimensions required")
    _need(type(value["corpus_sha256"]) is str and re.fullmatch(r"sha256:[0-9a-f]{64}", value["corpus_sha256"]) is not None,
          "native corpus identity dimension required")
    _need(all(_hex(value[k]) for k in _DIGEST_DIMENSIONS), "exact digest dimensions required")
    _positive_rational(value["native_mu_exact"])
    _positive_rational(value["native_eta_exact"])
    _need(type(value["theorem"]) is str and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_']*(?:\.[A-Za-z_][A-Za-z0-9_']*)+",
          value["theorem"]) is not None, "fully qualified real-model theorem dimension required")
    _need(type(value["evidence_kind"]) is str and value["evidence_kind"] in _EVIDENCE
          and type(value["translation_status"]) is str
          and value["translation_status"] == "explicit_real_model_without_native_source_equivalence",
          "real evidence and source-translation distinction required")
    _need(value["retention_format"] in ("bounded_lean_files@1", "bounded_lean_chunks@1"),
          "explicit artifact retention cache dimension required")
    authority = value["authority_profile"]
    _need(type(authority) is dict and set(authority) == set(_AUTHORITY_PROFILE)
          and all(authority[k] is False for k in _AUTHORITY_FIELDS)
          and authority["full_task_satisfaction"] == "unknown"
          and authority["all32_governing_RPI_exits"] == "OPEN"
          and authority["official_benchmark_score"] is None,
          "cache dimensions grant no operational authority or native equivalence")


def _file(value, *, complete=False, maximum=None, extra=()):
    keys = {"path", "bytes", "sha256"} | ({"complete"} if complete else set())
    _need(type(value) is dict and set(value) == keys | set(extra)
          and type(value["path"]) is str and value["path"].startswith("/")
          and type(value["bytes"]) is int and 0 < value["bytes"] <=
              (maximum if maximum is not None else 65536 if complete else 64 * 1024**2)
          and _hex(value["sha256"]), "bounded retained proof file binding required")
    if complete:
        _need(value["complete"] is True, "complete compiled proof objects required")


def _retention(check, dimensions, artifacts, stem):
    """Join actual retained descriptors; never read or reconstruct chunk bytes."""
    format_name = dimensions["retention_format"]
    if format_name == "bounded_lean_files@1":
        _need(check["schema"] == "ranker-real-curvature-bounded-analytic-lean-check@1"
              and check.get("retention_format", format_name) == format_name
              and dimensions["retention_profile_sha256"] == canonical_sha256(_ORDINARY_RETENTION_PROFILE),
              "ordinary native artifact retention profile differs")
        for artifact in artifacts:
            _file(artifact, complete=True)
        return
    _need(check["schema"] == "ranker-real-curvature-bounded-analytic-lean-check@2"
          and check.get("retention_format") == format_name
          and type(check.get("retention_profile")) is dict
          and _wire(check["retention_profile"]) == _wire(_CHUNK_RETENTION_PROFILE)
          and check.get("retention_profile_sha256") == dimensions["retention_profile_sha256"] ==
              canonical_sha256(_CHUNK_RETENTION_PROFILE)
          and check.get("reconstruction_validation_error") is None,
          "fixed native chunk reconstruction profile required")
    _need(type(check.get("native_lean_invocations")) is int and check["native_lean_invocations"] == 1
          and type(check.get("native_lean_returncode")) is int and check["native_lean_returncode"] == 0,
          "one actual positive Lean invocation required")
    _file(check.get("retention_helper"))
    _file(check.get("python_executable"))
    _need(check["retention_helper"]["bytes"] + check["augmented_source"]["bytes"] <=
          _NATIVE_BOUNDS["max_input_bytes"], "combined native source/helper input bound required")
    for artifact in artifacts:
        _file(artifact, complete=True, maximum=3997696, extra=("retention_format",))
        _need(artifact["retention_format"] == format_name, "reconstructed object retention format differs")
    manifest = check.get("retention_manifest")
    _file(manifest, complete=True)
    _need(manifest["path"].rsplit("/", 1)[-1] == "LeanProofChunks.json", "actual chunk manifest binding required")
    body = check.get("retention_manifest_body")
    _need(type(body) is dict and set(body) == {"schema", "status", "retention_profile_sha256",
              "native_lean_invocations", "native_lean_returncode", "objects", "chunks", "aggregate_raw_object_bytes"}
          and body["schema"] == format_name and body["status"] == "complete"
          and body["retention_profile_sha256"] == dimensions["retention_profile_sha256"]
          and type(body["native_lean_invocations"]) is int and body["native_lean_invocations"] == 1
          and type(body["native_lean_returncode"]) is int and body["native_lean_returncode"] == 0,
          "complete actual positive chunk manifest required")
    manifest_bytes = _wire(body) + b"\n"
    _need(len(manifest_bytes) == manifest["bytes"] <= 65536
          and hashlib.sha256(manifest_bytes).hexdigest() == manifest["sha256"],
          "actual canonical manifest bytes differ")
    chunks, retained = body["chunks"], check.get("retained_chunk_artifacts")
    _need(type(chunks) is list and 1 <= len(chunks) <= 61 and type(retained) is list
          and len(retained) == len(chunks), "complete bounded captured chunk population required")
    chunk_names, chunk_sizes = [], {}
    for index, (row, captured) in enumerate(zip(chunks, retained)):
        name = "LeanProofChunk%03d.bin" % index
        _file(captured, complete=True)
        _need(type(row) is dict and set(row) == {"name", "bytes", "sha256"}
              and row["name"] == name and captured["path"].rsplit("/", 1)[-1] == name
              and type(row["bytes"]) is int and row["bytes"] == captured["bytes"]
              and row["sha256"] == captured["sha256"], "exact ordered chunk size/hash bindings required")
        chunk_names.append(name)
        chunk_sizes[name] = row["bytes"]
    objects = body["objects"]
    _need(type(objects) is list and len(objects) == len(artifacts), "complete reconstructed object population differs")
    allowed = [stem + suffix for suffix in _CHUNK_RETENTION_PROFILE["object_suffixes"]]
    object_names, used, total = [], [], 0
    for row, artifact in zip(objects, artifacts):
        _need(type(row) is dict and set(row) == {"name", "bytes", "sha256", "chunks"}
              and type(row["name"]) is str and row["name"] in allowed
              and artifact["path"].rsplit("/", 1)[-1] == row["name"]
              and type(row["bytes"]) is int and row["bytes"] == artifact["bytes"]
              and row["sha256"] == artifact["sha256"] and type(row["chunks"]) is list
              and len(row["chunks"]) > 0 and all(type(name) is str and name in chunk_sizes for name in row["chunks"]),
              "complete object descriptor/chunk membership differs")
        _need(all(chunk_sizes[name] == 65536 for name in row["chunks"][:-1])
              and sum(chunk_sizes[name] for name in row["chunks"]) == row["bytes"],
              "exact object chunk partition bytes differ")
        object_names.append(row["name"])
        used.extend(row["chunks"])
        total += row["bytes"]
    _need(object_names[0] == allowed[0] and object_names == [name for name in allowed if name in object_names]
          and used == chunk_names and type(body["aggregate_raw_object_bytes"]) is int
          and total == body["aggregate_raw_object_bytes"] == sum(chunk_sizes.values()) <= 3997696,
          "fixed complete object/chunk order and aggregate bound required")
    validation = check.get("reconstruction_validation")
    _need(type(validation) is dict and set(validation) == {"status", "manifest_complete", "exact_chunk_population",
              "aggregate_raw_object_bytes", "reconstructed_object_count", "chunk_count",
              "reconstructed_full_module_bodies_may_exceed_native_per_file_capture"}
          and validation["status"] == "passed" and validation["manifest_complete"] is True
          and validation["exact_chunk_population"] is True
          and validation["reconstructed_full_module_bodies_may_exceed_native_per_file_capture"] is True
          and all(type(validation[k]) is int and validation[k] == v for k, v in
              {"aggregate_raw_object_bytes": total, "reconstructed_object_count": len(objects),
               "chunk_count": len(chunks)}.items()), "actual complete reconstruction validation differs")


def _qualified_result(result, dimensions, dimensions_pin):
    _need(set(result) == _ROOT_JOIN_FIELDS and result["schema"] == RESULT_SCHEMA
          and result["cache_dimensions_sha256"] == dimensions_pin, "exact qualified root join required")
    for k in ("checker_source_sha256", "theorem_statement_sha256", "numeric_binding_sha256",
              "translation_profile_sha256", "verification_policy_sha256", "network_policy_sha256"):
        _need(result[k] == dimensions[k], "qualified result differs from cache dimension")
    _file(result["checker_source"])
    _need(type(result["checker_source_text"]) is str
          and len(result["checker_source_text"].encode()) == result["checker_source"]["bytes"]
          and hashlib.sha256(result["checker_source_text"].encode()).hexdigest() ==
              result["checker_source"]["sha256"] == dimensions["checker_source_sha256"],
          "retained checker bytes differ from actual checker source dimension")
    check = result["native_check"]
    _need(type(check) is dict and _hex(result["native_check_sha256"])
          and canonical_sha256(check) == result["native_check_sha256"], "native check complete-object pin differs")
    _need(check.get("schema") in ("ranker-real-curvature-bounded-analytic-lean-check@1",
                                "ranker-real-curvature-bounded-analytic-lean-check@2")
          and check.get("status") == "passed" and check.get("expected_success") is True
          and check.get("matches_expectation") is True
          and type(check.get("native_invocations")) is int and check["native_invocations"] == 1
          and type(check.get("returncode")) is int and check["returncode"] == 0,
          "one actual positive passed native check required")
    _need(all(check.get(k) is False for k in ("timed_out", "cancelled", "unavailable", "resource_exhausted",
              "output_truncated", "workspace_limit_exceeded")) and check.get("workspace_cleaned") is True
          and check.get("artifact_anomalies") == [] and check.get("axiom_report_error") is None
          and check.get("post_call_binding_error") is None
          and check.get("receipt_retention_overflow", False) is False, "complete clean native evidence required")
    _need(all(check.get(k) is False for k in ("proof_authority", "execution_authority", "completion_authority",
              "planner_activation", "python_ranker_source_equivalence_proved", "binary64_error_bound_proved",
              "historical_execution_origin_proved", "optimizer_convergence_proved"))
          and check.get("full_task_satisfaction") == "unknown"
          and check.get("all32_governing_RPI_exits") == "OPEN" and check.get("official_benchmark_score") is None,
          "native evidence grants no source, Float, convergence or operational authority")
    _need(all(check.get(k) is True for k in ("proof_source_in_frozen_per_job_environment",
              "direct_imports_and_implicit_Init_in_frozen_registry", "root_lease_owned_by_caller",
              "outer120s_and_frozen_project_import_guard_owned_by_caller"))
          and check.get("environment_actual_runtime_open_trace_claimed") is False,
          "actual frozen source/import and caller admission bindings required")
    lease = check.get("actual_root_lease")
    _need(type(lease) is dict and all(type(lease.get(k)) is int and lease[k] == v for k, v in
              {"cpu_slots": 1, "memory_mb": 2048, "child_process_slots": 4,
               "gpu_memory_mb": 0, "unified_memory_mb": 0}.items())
          and lease.get("requires_gpu") is False and lease.get("cancelled") is False
          and lease.get("released") is False and type(lease.get("owner_pid")) is int
          and lease["owner_pid"] > 0 and type(lease.get("lease_id")) is str
          and re.fullmatch(r"[0-9a-f]{32}", lease["lease_id"]) is not None,
          "actual unchanged root lease admission profile required")
    bounds = check.get("native_bounds")
    _need(type(bounds) is dict and set(bounds) == set(_NATIVE_BOUNDS)
          and all(type(bounds[k]) is int and bounds[k] == v for k, v in _NATIVE_BOUNDS.items()),
          "unchanged native proof limits required")
    _file(check.get("source"))
    _file(check.get("augmented_source"))
    _file(check.get("environment_manifest"))
    _need(check["source"]["bytes"] <= _NATIVE_BOUNDS["max_input_bytes"]
          and check["augmented_source"]["bytes"] <= _NATIVE_BOUNDS["max_input_bytes"],
          "actual native source input limits required")
    _need(check["source"]["sha256"] == dimensions["proof_source_sha256"]
          and check["environment_manifest"]["sha256"] == dimensions["environment_manifest_sha256"],
          "actual source/environment check bindings differ")
    artifacts = check.get("compiled_artifacts")
    _need(type(artifacts) is list and 1 <= len(artifacts) <= 4, "retained compiled object population required")
    filename = check["augmented_source"]["path"].rsplit("/", 1)[-1]
    _need(re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*\.lean", filename) is not None, "portable checked Lean source required")
    stem = filename[:-5]
    allowed = {stem + suffix for suffix in (".olean", ".olean.private", ".olean.server", ".ir")}
    names = []
    _retention(check, dimensions, artifacts, stem)
    for artifact in artifacts:
        name = artifact["path"].rsplit("/", 1)[-1]
        _need(name in allowed, "compiled artifact belongs to another source")
        names.append(name)
    _need(len(names) == len(set(names)) and stem + ".olean" in names, "complete main compiled object required")
    registry = check.get("theorem_axiom_output")
    _need(type(registry) is list and 0 < len(registry) <= 256, "actual theorem axiom registry required")
    observed, names = [], set()
    for row in registry:
        _need(type(row) is dict and set(row) == {"theorem", "axioms", "report_occurrences"}
              and type(row["theorem"]) is str and row["theorem"] not in names
              and type(row["report_occurrences"]) is int and row["report_occurrences"] > 0
              and type(row["axioms"]) is list and all(type(a) is str for a in row["axioms"])
              and len(row["axioms"]) == len(set(row["axioms"])) and set(row["axioms"]) <= _AXIOMS,
              "qualified distinct theorem and standard actual axioms required")
        names.add(row["theorem"])
        if row["theorem"] == dimensions["theorem"]:
            observed = sorted(row["axioms"])
    _need(dimensions["theorem"] in names and canonical_sha256(observed) == dimensions["assumptions_sha256"]
          and check.get("allowed_standard_axioms") == sorted(_AXIOMS), "qualified theorem/assumption dimension differs")
    return check, observed


def build_real_curvature_proof_cache_entry(*, cache_dimensions, expected_cache_dimensions_sha256,
        qualified_result, expected_qualified_result_sha256):
    """Create an inert advisory record from required externally pinned results."""
    _pinned(cache_dimensions, expected_cache_dimensions_sha256)
    _pinned(qualified_result, expected_qualified_result_sha256)
    _dimensions(cache_dimensions)
    check, assumptions = _qualified_result(qualified_result, cache_dimensions, expected_cache_dimensions_sha256)
    row = {"status": "kernel_real_statement_bound", "theorem": cache_dimensions["theorem"], "evidence_kind": cache_dimensions["evidence_kind"],
        "theorem_statement_sha256": cache_dimensions["theorem_statement_sha256"],
        "assumptions": assumptions, "translation_status": cache_dimensions["translation_status"],
        "proof_source_sha256": cache_dimensions["proof_source_sha256"],
        "environment_manifest_sha256": cache_dimensions["environment_manifest_sha256"],
        "numeric_binding_sha256": cache_dimensions["numeric_binding_sha256"],
        "qualified_result_sha256": expected_qualified_result_sha256, "advisory_only": True,
        **deepcopy(_AUTHORITY_PROFILE)}
    entry = {"schema": ENTRY_SCHEMA, "status": "qualified_advisory_real_model_theorem",
        "cache_key_sha256": expected_cache_dimensions_sha256,
        "cache_dimensions": deepcopy(cache_dimensions), "qualified_result_sha256": expected_qualified_result_sha256,
        "native_check_sha256": qualified_result["native_check_sha256"],
        "complete_compiled_artifact_sha256s": [a["sha256"] for a in check["compiled_artifacts"]],
        "retention_format": cache_dimensions["retention_format"],
        "retention_profile_sha256": cache_dimensions["retention_profile_sha256"],
        "fresh_chunk_reconstruction_performed_here": False,
        "theorem_row": row, "external_pin_origin_authenticated_here": False,
        "native_prover_calls_here": 0, "filesystem_or_metadata_or_network_operations_here": 0,
        "ProgramContract_or_RPI_or_core_policy_mutated": False, **deepcopy(_AUTHORITY_PROFILE)}
    entry["cache_entry_sha256"] = canonical_sha256(entry)
    _need(len(_wire(entry)) <= 65536, "bounded retained advisory entry required")
    return entry


def lookup_real_curvature_proof_cache(*, entry, expected_entry_sha256, cache_dimensions,
        expected_cache_dimensions_sha256, qualified_result, expected_qualified_result_sha256):
    """Exact identity hit returns a copy of an advisory row; all refusals miss."""
    try:
        _pinned(entry, expected_entry_sha256)
        _pinned(cache_dimensions, expected_cache_dimensions_sha256)
        if entry.get("cache_key_sha256") != expected_cache_dimensions_sha256:
            return None
        rebuilt = build_real_curvature_proof_cache_entry(cache_dimensions=cache_dimensions,
            expected_cache_dimensions_sha256=expected_cache_dimensions_sha256,
            qualified_result=qualified_result, expected_qualified_result_sha256=expected_qualified_result_sha256)
        if _wire(entry) != _wire(rebuilt):
            return None
        return deepcopy(rebuilt["theorem_row"])
    except (RealCurvatureCacheError, KeyError, TypeError, ValueError, OverflowError, RecursionError):
        return None
