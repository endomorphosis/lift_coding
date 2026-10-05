"""File-bound preparation of advisory cache joins and additive metadata inputs.

The caller supplies a frozen specification and owns admission, the import guard,
the qualification seal, and the subsequent metadata/restart job. This module
does not run a solver, model, database, network client, or metadata indexer.

Specification @1 fields are exactly: schema, qualification_root, closure_files,
cache_source_path, prior_metadata_path, numeric_binding_path, numeric_owned_path,
numeric_outer_path, attempts, proofs. closure_files are exact raw-file
{path,bytes,sha256} bindings, including this driver and every referenced input.
Attempts have {id,check_result_path,owned_receipt_path,outer_receipt_path,
checker_source_path}; check_result_path may be null for a recorded preflight
failure. Proofs have {id,attempt_id,theorem,evidence_kind,statement_span,
translation_policy_path,verification_policy_path,network_policy_path}; the
statement span has {start_utf8_byte,end_utf8_byte,sha256} and selects the actual
theorem declaration from the compiled source. A policy may be shared by proofs.

The translation policy schema is terminal-ranker-real-translation-policy@1;
status is explicit_real_model_without_native_source_equivalence, the three
native_source_equivalence_proved/native_binary64_semantics_proved/
global_optimizer_convergence_proved flags are false, and original_real_profile_join
is null or {attempt_id,theorem} pointing at an actual passed registered Real
profile theorem. The verification policy schema is
terminal-ranker-real-verification-policy@1 and requires native_bounds plus an
exact all-false authority_profile. The network policy schema is
terminal-ranker-real-network-policy@1; network_requested_in_proof_job and
network_enforcement_proved are false. The latter explicitly avoids claiming an
unobserved runtime network sandbox. Raw policy bytes become cache dimensions.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import types

SPEC_SCHEMA = "terminal-ranker-real-curvature-qualified-cache-join-spec@1"
CACHE_SOURCE_SHA256 = "2b076527c8bc5984090df47d73122a4c29987d9a0c75f7c88ee5d7b7bcdef48b"
MAX_FILE_BYTES = 64 * 1024**2
MAX_TOTAL_INPUT_BYTES = 512 * 1024**2
MAX_METADATA_BYTES = 16 * 1024**2
NEW_FAMILIES = ("ranker_real_curvature_numeric", "ranker_real_curvature_checks", "ranker_real_curvature_proofs")
ORIGINAL_CORPUS = "sha256:d4aa22b9a7bfe796c31adbcf78f9b72987549a85117b8f08534f5a06c032a3df"
_KIND_DECLARATIONS = {
    "real_logistic_coefficient_bound": ("LogisticCoefficient.lean", "RankerRealCurvature", {
        "realLogisticP_mem_Ioo", "realLogisticCoeff_bounds", "realLogisticCoeff_zero"}),
    "real_coordinate_geometry": ("CoordinateGeometry.lean", "RankerRealCurvature", {
        "squaredEuclideanNorm_nonneg", "dot_sq_le"}),
    "real_candidate_quadratic_curvature": ("LogisticCurvature.lean", "RankerRealCurvature", {
        "candidateHessianQuad_bounds", "originalFourPairCandidate_bounds"}),
    "real_scalar_derivative": ("ScalarSoftplus.lean", "RankerRealCurvature", {
        "realStablePairLoss_eq", "hasDerivAt_realLogisticP", "hasDerivAt_realPairLoss",
        "hasDerivAt_negative_realLogisticP", "deriv_realPairLoss", "secondDeriv_realPairLoss"}),
    "real_directional_second_derivative": ("DirectionalObjective.lean", "RankerRealCurvature", {
        "hasDerivAt_lineFirstDerivative", "secondDeriv_realObjectiveLine", "secondDeriv_realObjectiveLine_zero",
        "actual_secondDirectional_bounds"}),
    "exact_original_rational_arithmetic": ("OriginalNumericCurvature.lean", "OriginalRankerCurvatureArithmetic", {
        "original_norms_exact", "original_shape", "original_positive_scalars", "original_mean_bound",
        "original_conservative_bound", "original_safe_steps"}),
    "real_objective_gradient_identity": ("RealGradient.lean", "RankerRealCurvature", {
        "dot_realCoordinateGradient", "lineFirstDerivative_zero_eq_dot_gradient"}),
    "real_objective_step_descent": ("RealDescent.lean", "RankerRealCurvature", {
        "realObjective_taylor_upper", "realGradientStep_descent", "realGradientStep_safe_descent"}),
    "original_real_profile_curvature": ("OriginalRealProfile.lean", "RankerRealCurvature", {
        "originalReal_norms_exact", "originalReal_meanL_exact", "originalReal_eta_le_inverse_meanL",
        "originalReal_candidate_bounds", "originalReal_actual_secondDirectional_bounds"}),
    "original_real_profile_descent": ("OriginalRealDescent.lean", "RankerRealCurvature", {
        "originalReal_meanCurvatureBound_exact", "originalReal_safe_descent"}),
}


class QualifiedCacheJoinError(ValueError):
    pass


def _need(condition, message):
    if condition is not True:
        raise QualifiedCacheJoinError(message)


def _hex(value):
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _signature(value):
    return tuple(getattr(value, "st_" + key) for key in
                 ("dev", "ino", "mode", "nlink", "size", "mtime_ns", "ctime_ns"))


def _binding(value):
    _need(type(value) is dict and set(value) == {"path", "bytes", "sha256"}
          and type(value["path"]) is str and Path(value["path"]).is_absolute()
          and type(value["bytes"]) is int and 0 < value["bytes"] <= MAX_FILE_BYTES
          and _hex(value["sha256"]), "exact bounded raw-file binding required")
    return value


def _read(value):
    _binding(value)
    path = Path(value["path"])
    _need(path.resolve(strict=True) == path, "canonical immutable input path required")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        _need(stat.S_ISREG(before.st_mode) and before.st_size == value["bytes"], "raw file type/size differs")
        data = bytearray()
        while len(data) <= value["bytes"]:
            part = os.read(fd, min(1024**2, value["bytes"] + 1 - len(data)))
            if not part:
                break
            data.extend(part)
        _need(len(data) == value["bytes"] and hashlib.sha256(data).hexdigest() == value["sha256"]
              and _signature(before) == _signature(os.fstat(fd)) == _signature(path.lstat()),
              "complete raw input pin or before/after stat differs")
        return bytes(data)
    finally:
        os.close(fd)


def _json(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            _need(key not in result, "duplicate input JSON key")
            result[key] = value
        return result
    def nonfinite(value):
        raise QualifiedCacheJoinError("nonfinite JSON value: " + value)
    return json.loads(raw.decode("utf-8"), object_pairs_hook=unique, parse_constant=nonfinite)


def _raw_json(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                       allow_nan=False) + "\n").encode()


def _base_pin(value):
    _need(type(value) is dict and all(k in value for k in ("path", "bytes", "sha256")),
          "retained actual file descriptor required")
    return _binding({k: value[k] for k in ("path", "bytes", "sha256")})


def _closed(owned, outer, *, positive=False):
    _need(type(owned) is dict and owned.get("schema") == "terminal-ranker-curvature-owned-control@1"
          and type(outer) is dict and outer.get("schema") == "terminal-ranker-curvature-outer-control@1"
          and owned.get("invocation") == outer.get("invocation")
          and owned.get("cleanup_errors") == [] and outer.get("cleanup_errors") == []
          and owned.get("root_release_returned") is True,
          "actual owned/outer closure and cleanup bindings required")
    if positive:
        _need(owned.get("status") == "passed" and owned.get("primary_error") is None
              and outer.get("primary_error") is None and type(outer.get("returncode")) is int
              and outer["returncode"] == 0 and owned.get("old348_protected4_prior203_unchanged") is True,
              "passed protected-input actual owned/outer phase required")


def _policies(proof, inputs, api):
    translation = _json(inputs[proof["translation_policy_path"]])
    verification = _json(inputs[proof["verification_policy_path"]])
    network = _json(inputs[proof["network_policy_path"]])
    _need(type(translation) is dict and translation.get("schema") == "terminal-ranker-real-translation-policy@1"
          and translation.get("status") == "explicit_real_model_without_native_source_equivalence"
          and all(translation.get(k) is False for k in ("native_source_equivalence_proved",
              "native_binary64_semantics_proved", "global_optimizer_convergence_proved"))
          and "original_real_profile_join" in translation,
          "explicit real translation and unproved native semantics policy required")
    _need(type(verification) is dict and verification.get("schema") == "terminal-ranker-real-verification-policy@1"
          and api.canonical_sha256(verification.get("native_bounds")) == api.canonical_sha256(api._NATIVE_BOUNDS)
          and api.canonical_sha256(verification.get("authority_profile")) == api.canonical_sha256(api._AUTHORITY_PROFILE),
          "unchanged exact verification and all-false authority policy required")
    _need(type(network) is dict and network.get("schema") == "terminal-ranker-real-network-policy@1"
          and network.get("network_requested_in_proof_job") is False
          and network.get("network_enforcement_proved") is False,
          "honest network-request and enforcement scope policy required")
    return translation


def _changed_dimension(dimensions, key):
    changed = deepcopy(dimensions)
    if key == "authority_profile":
        changed[key]["proof_authority"] = True
    elif key in ("native_mu_exact", "native_eta_exact"):
        value = changed[key]
        value["numerator"] = str(int(value["numerator"]) + int(value["denominator"]))
    elif key == "corpus_sha256":
        value = changed[key][7:]
        changed[key] = "sha256:" + ("0" if value[0] != "0" else "1") + value[1:]
    elif key.endswith("sha256"):
        value = changed[key]
        changed[key] = ("0" if value[0] != "0" else "1") + value[1:]
    elif key == "evidence_kind":
        changed[key] = ("real_scalar_derivative" if changed[key] != "real_scalar_derivative"
                        else "real_candidate_quadratic_curvature")
    elif key == "retention_format":
        changed[key] = ("bounded_lean_chunks@1" if changed[key] != "bounded_lean_chunks@1"
                        else "bounded_lean_files@1")
    else:
        changed[key] += "_changed_query"
    return changed


def build_qualified_cache_joins(*, specification_path, expected_specification_sha256, output_root):
    """Prepare new files; the caller subsequently admits the metadata job."""
    _need(_hex(expected_specification_sha256), "independent raw specification SHA256 required")
    specification_path = Path(specification_path)
    _need(specification_path.is_absolute() and specification_path.resolve(strict=True) == specification_path,
          "canonical frozen specification path required")
    specification_pin = {"path": str(specification_path), "bytes": specification_path.stat().st_size,
                         "sha256": expected_specification_sha256}
    specification_raw = _read(specification_pin)
    spec = _json(specification_raw)
    _need(type(spec) is dict and set(spec) == {"schema", "qualification_root", "closure_files",
              "cache_source_path", "prior_metadata_path", "numeric_binding_path", "numeric_owned_path",
              "numeric_outer_path", "attempts", "proofs"} and spec["schema"] == SPEC_SCHEMA,
          "exact frozen join specification required")
    root = Path(spec["qualification_root"])
    _need(root.is_absolute() and root.resolve(strict=True) == root and root.is_dir(),
          "canonical qualification root required")
    rows = spec["closure_files"]
    _need(type(rows) is list and 0 < len(rows) <= 4096, "bounded frozen input population required")
    closure = {_binding(row)["path"]: row for row in rows}
    _need(len(closure) == len(rows) and sum(row["bytes"] for row in rows) <= MAX_TOTAL_INPUT_BYTES,
          "unique bounded frozen closure required")
    _need(str(Path(__file__).resolve()) in closure, "actual driver source must be in frozen closure")
    inputs = {path: _read(binding) for path, binding in closure.items()}
    for key in ("cache_source_path", "prior_metadata_path", "numeric_binding_path", "numeric_owned_path", "numeric_outer_path"):
        _need(type(spec[key]) is str and spec[key] in inputs, "required input outside frozen closure")
    cache_pin = closure[spec["cache_source_path"]]
    _need(cache_pin["sha256"] == CACHE_SOURCE_SHA256, "qualified v2 cache source pin differs")
    api = types.ModuleType("held_qualified_real_curvature_cache_v2")
    api.__file__ = cache_pin["path"]
    exec(compile(inputs[cache_pin["path"]], cache_pin["path"], "exec"), api.__dict__)
    prior = _json(inputs[spec["prior_metadata_path"]])
    _need(type(prior) is dict and len(prior) == 29 and all(type(k) is str and type(v) is list for k, v in prior.items())
          and sum(len(v) for v in prior.values()) == 4348 and not set(NEW_FAMILIES) & set(prior),
          "exact prior 29-family/4348-payload population required")
    numeric = _json(inputs[spec["numeric_binding_path"]])
    _need(type(numeric) is dict and numeric.get("schema") == "terminal-ranker-original-real-curvature-numeric-binding@1"
          and numeric.get("status") == "exact_original_profile_candidate_curvature_constants"
          and numeric.get("corpus_sha256") == ORIGINAL_CORPUS and type(numeric.get("pair_count")) is int
          and numeric["pair_count"] == 4 and type(numeric.get("dimension")) is int
          and numeric["dimension"] == 80 and numeric.get("exact_positive_mu") is True
          and numeric.get("exact_positive_eta") is True and numeric.get("candidate_curvature_numeric_inequalities_checked") is True,
          "original exact four-pair/eighty-coordinate numeric receipt required")
    numeric_without_self = dict(numeric)
    numeric_self = numeric_without_self.pop("numeric_binding_sha256")
    _need(api.canonical_sha256(numeric_without_self) == numeric_self, "numeric native self digest differs")
    numeric_owned = _json(inputs[spec["numeric_owned_path"]])
    numeric_outer = _json(inputs[spec["numeric_outer_path"]])
    _closed(numeric_owned, numeric_outer, positive=True)
    _need(numeric_owned.get("numeric_binding") == closure[spec["numeric_binding_path"]]
          and numeric_owned.get("coordinate_visits") == 320
          and all(numeric_owned.get(k) == 0 and type(numeric_owned[k]) is int for k in
              ("native_preparation_calls", "gradient_evaluations", "fit_calls", "optimizer_updates")),
          "actual pure numeric phase join differs")
    attempts = spec["attempts"]
    _need(type(attempts) is list and 0 < len(attempts) <= 256, "all bounded native attempts required")
    checks, attempt_map, attempt_summaries, owned_paths = [], {}, [], []
    for attempt in attempts:
        _need(type(attempt) is dict and set(attempt) == {"id", "check_result_path", "owned_receipt_path",
                  "outer_receipt_path", "checker_source_path"} and type(attempt["id"]) is str
              and re.fullmatch(r"[A-Za-z0-9_-]{1,80}", attempt["id"]) is not None and attempt["id"] not in attempt_map,
              "distinct exact attempt specification required")
        for key in ("owned_receipt_path", "outer_receipt_path", "checker_source_path"):
            _need(attempt[key] in inputs, "actual attempt input outside frozen closure")
        owned = _json(inputs[attempt["owned_receipt_path"]])
        outer = _json(inputs[attempt["outer_receipt_path"]])
        _closed(owned, outer)
        _need(type(owned.get("mode")) is str and owned["mode"].startswith("lean-"), "actual native attempt phase required")
        invocation_pin = _base_pin(owned["invocation"])
        _need(closure.get(invocation_pin["path"]) == invocation_pin, "actual invocation outside frozen closure")
        invocation = _json(inputs[invocation_pin["path"]])
        checker_pin = closure[attempt["checker_source_path"]]
        _need(checker_pin in invocation.get("extra_inputs", []), "actual admitted checker source differs")
        check_path = attempt["check_result_path"]
        if check_path is None:
            _need(owned.get("status") == "failed" and owned.get("native_proof_checks") == [],
                  "missing actual check receipt is not a recorded preflight failure")
            check = {"schema": "terminal-ranker-real-curvature-preflight-refusal@1", "status": "inconclusive",
                "attempt_id": attempt["id"], "native_check_receipt_available": False,
                "owned_receipt": closure[attempt["owned_receipt_path"]],
                "outer_receipt": closure[attempt["outer_receipt_path"]], **deepcopy(api._AUTHORITY_PROFILE)}
        else:
            _need(type(check_path) is str and check_path in inputs and closure[check_path] in owned.get("native_proof_checks", []),
                  "actual native check receipt differs from owned phase")
            check = _json(inputs[check_path])
            _need(type(check) is dict and check.get("status") in ("passed", "rejected", "inconclusive")
                  and check.get("schema") in ("ranker-real-curvature-bounded-analytic-lean-check@1",
                                             "ranker-real-curvature-bounded-analytic-lean-check@2"),
                  "actual check status/schema required")
            retained = [check[k] for k in ("source", "augmented_source", "environment_manifest")]
            retained += check.get("compiled_artifacts", []) + check.get("retained_chunk_artifacts", [])
            retained += [check[k] for k in ("retention_manifest", "retention_helper", "python_executable") if check.get(k) is not None]
            for descriptor in retained:
                binding = _base_pin(descriptor)
                _need(closure.get(binding["path"]) == binding, "actual check file outside frozen closure")
        checks.append(deepcopy(check))
        owned_paths.append(attempt["owned_receipt_path"])
        attempt_map[attempt["id"]] = (attempt, owned, outer, check)
        attempt_summaries.append({"attempt_id": attempt["id"], "status": check["status"],
            "check_result_raw_pin": closure[check_path] if check_path is not None else None,
            "owned_receipt": closure[attempt["owned_receipt_path"]], "outer_receipt": closure[attempt["outer_receipt_path"]]})
    recorded_native_owned = []
    for path in sorted((root / "evidence").glob("*/closed.json")):
        raw = path.read_bytes()
        _need(len(raw) <= MAX_FILE_BYTES, "bounded recorded phase receipt required")
        row = _json(raw)
        if type(row) is dict and type(row.get("mode")) is str and row["mode"].startswith("lean-"):
            recorded_native_owned.append(str(path))
    _need(set(recorded_native_owned) == set(owned_paths) and len(owned_paths) == len(set(owned_paths)),
          "native attempt population omits or duplicates recorded history")
    proofs = spec["proofs"]
    _need(type(proofs) is list and 0 < len(proofs) <= 128, "bounded positive advisory theorem population required")
    entries, prepared, proof_summaries, proof_ids = [], [], [], set()
    lookup_totals = {"same_query_hits": 0, "changed_dimension_queries": 0, "changed_dimension_misses": 0}
    for proof in proofs:
        _need(type(proof) is dict and set(proof) == {"id", "attempt_id", "theorem", "evidence_kind", "statement_span",
                  "translation_policy_path", "verification_policy_path", "network_policy_path"}
              and type(proof["id"]) is str and re.fullmatch(r"[A-Za-z0-9_-]{1,80}", proof["id"]) is not None
              and proof["id"] not in proof_ids and proof["attempt_id"] in attempt_map,
              "distinct exact qualified theorem specification required")
        proof_ids.add(proof["id"])
        for key in ("translation_policy_path", "verification_policy_path", "network_policy_path"):
            _need(proof[key] in inputs, "proof policy outside frozen closure")
        attempt, owned, outer, check = attempt_map[proof["attempt_id"]]
        _closed(owned, outer, positive=True)
        _need(check.get("status") == "passed", "only passed actual theorem checks may populate proof cache")
        translation = _policies(proof, inputs, api)
        join = translation["original_real_profile_join"]
        if join is not None:
            _need(type(join) is dict and set(join) == {"attempt_id", "theorem"} and join["attempt_id"] in attempt_map,
                  "explicit original Rat-to-Real profile join required")
            _, joined_owned, joined_outer, joined_check = attempt_map[join["attempt_id"]]
            _closed(joined_owned, joined_outer, positive=True)
            _need(join["theorem"] == "RankerRealCurvature.originalReal_actual_secondDirectional_bounds"
                  and joined_check.get("source", {}).get("path", "").rsplit("/", 1)[-1] == "OriginalRealProfile.lean"
                  and joined_check.get("status") == "passed" and any(row.get("theorem") == join["theorem"] for row in
                  joined_check.get("theorem_axiom_output", [])), "original Real vector/cast theorem is not actually qualified")
        _need(proof["evidence_kind"] not in ("original_real_profile_curvature", "original_real_profile_descent")
              or join is not None, "original real profile instantiation cannot be assumed")
        source_pin = _base_pin(check["source"])
        source_raw = inputs[source_pin["path"]]
        _need(type(proof["evidence_kind"]) is str and proof["evidence_kind"] in _KIND_DECLARATIONS,
              "reviewed source-specific theorem taxonomy required")
        filename, namespace, declarations = _KIND_DECLARATIONS[proof["evidence_kind"]]
        _need(source_pin["path"].rsplit("/", 1)[-1] == filename
              and proof["theorem"] in {namespace + "." + name for name in declarations},
              "actual theorem/source does not match the accurate evidence kind")
        span = proof["statement_span"]
        _need(type(span) is dict and set(span) == {"start_utf8_byte", "end_utf8_byte", "sha256"}
              and type(span["start_utf8_byte"]) is int and type(span["end_utf8_byte"]) is int
              and 0 <= span["start_utf8_byte"] < span["end_utf8_byte"] <= len(source_raw) and _hex(span["sha256"]),
              "exact actual theorem declaration byte span required")
        statement = source_raw[span["start_utf8_byte"]:span["end_utf8_byte"]]
        _need(hashlib.sha256(statement).hexdigest() == span["sha256"]
              and type(proof["theorem"]) is str and re.search(r"\btheorem\s+" + re.escape(proof["theorem"].split(".")[-1]) +
                  r"(?=\s|\{|\(|:)", statement.decode("utf-8")) is not None,
              "actual source theorem declaration differs")
        registry = check.get("theorem_axiom_output", [])
        matches = [row for row in registry if row.get("theorem") == proof["theorem"]]
        _need(len(matches) == 1, "actual registered qualified theorem required")
        checker_pin = closure[attempt["checker_source_path"]]
        retention_format = check.get("retention_format", "bounded_lean_files@1")
        retention_profile_pin = (check["retention_profile_sha256"] if retention_format == "bounded_lean_chunks@1"
                                 else api.canonical_sha256(api._ORDINARY_RETENTION_PROFILE))
        dimensions = {"schema": api.DIMENSIONS_SCHEMA, "corpus_sha256": numeric["corpus_sha256"],
            "native_mu_exact": deepcopy(numeric["native_mu_exact"]), "native_eta_exact": deepcopy(numeric["native_eta_exact"]),
            "theorem": proof["theorem"], "evidence_kind": proof["evidence_kind"],
            "translation_status": translation["status"], "authority_profile": deepcopy(api._AUTHORITY_PROFILE),
            "retention_format": retention_format, "retention_profile_sha256": retention_profile_pin,
            **{key: numeric[key] for key in ("feature_profile_sha256", "difference_vectors_sha256", "train_pairs_sha256",
                                            "native_update_profile_sha256")},
            "theorem_statement_sha256": span["sha256"], "proof_source_sha256": source_pin["sha256"],
            "assumptions_sha256": api.canonical_sha256(sorted(matches[0]["axioms"])),
            "checker_source_sha256": checker_pin["sha256"], "environment_manifest_sha256": check["environment_manifest"]["sha256"],
            "numeric_binding_sha256": api.canonical_sha256(numeric),
            "translation_profile_sha256": closure[proof["translation_policy_path"]]["sha256"],
            "verification_policy_sha256": closure[proof["verification_policy_path"]]["sha256"],
            "network_policy_sha256": closure[proof["network_policy_path"]]["sha256"]}
        dimensions_pin = api.canonical_sha256(dimensions)
        result = {"schema": api.RESULT_SCHEMA, "cache_dimensions_sha256": dimensions_pin,
            "native_check": deepcopy(check), "native_check_sha256": api.canonical_sha256(check),
            "checker_source": deepcopy(checker_pin), "checker_source_text": inputs[checker_pin["path"]].decode("utf-8"),
            **{key: dimensions[key] for key in ("checker_source_sha256", "theorem_statement_sha256", "numeric_binding_sha256",
                "translation_profile_sha256", "verification_policy_sha256", "network_policy_sha256")}}
        arguments = {"cache_dimensions": dimensions, "expected_cache_dimensions_sha256": dimensions_pin,
                     "qualified_result": result, "expected_qualified_result_sha256": api.canonical_sha256(result)}
        entry = api.build_real_curvature_proof_cache_entry(**arguments)
        entry_pin = api.canonical_sha256(entry)
        row = api.lookup_real_curvature_proof_cache(**arguments, entry=entry, expected_entry_sha256=entry_pin)
        _need(row == entry["theorem_row"], "actual same-query advisory cache hit differs")
        lookup_totals["same_query_hits"] += 1
        misses = []
        _need(len(dimensions) == 23, "cache dimension profile changed without driver review")
        for key in sorted(dimensions):
            query = _changed_dimension(dimensions, key)
            changed_arguments = {**arguments, "cache_dimensions": query,
                                 "expected_cache_dimensions_sha256": api.canonical_sha256(query)}
            observed = api.lookup_real_curvature_proof_cache(**changed_arguments, entry=entry, expected_entry_sha256=entry_pin)
            _need(observed is None, "changed actual cache dimension did not miss: " + key)
            misses.append(key)
        lookup_totals["changed_dimension_queries"] += len(misses)
        lookup_totals["changed_dimension_misses"] += len(misses)
        entries.append(entry)
        prepared.extend([(proof["id"] + ".dimensions.json", dimensions), (proof["id"] + ".qualified-result.json", result),
                         (proof["id"] + ".cache-entry.json", entry)])
        proof_summaries.append({"proof_id": proof["id"], "attempt_id": proof["attempt_id"], "theorem": proof["theorem"],
            "evidence_kind": proof["evidence_kind"], "cache_key_sha256": dimensions_pin,
            "qualified_result_sha256": arguments["expected_qualified_result_sha256"], "complete_cache_entry_sha256": entry_pin,
            "same_query_hit": True, "changed_dimension_misses": misses,
            "original_real_profile_join": deepcopy(join)})
    metadata = deepcopy(prior)
    metadata[NEW_FAMILIES[0]], metadata[NEW_FAMILIES[1]], metadata[NEW_FAMILIES[2]] = [deepcopy(numeric)], checks, entries
    _need(len(metadata) == 32 and all(metadata[key] == prior[key] for key in prior), "prior payloads or family cap changed")
    metadata_raw = _raw_json(metadata)
    _need(len(metadata_raw) <= MAX_METADATA_BYTES, "bounded new metadata input required")
    for path, binding in closure.items():
        _need(_read(binding) == inputs[path], "frozen input changed after pure joins")
    _need(_read(specification_pin) == specification_raw, "frozen join specification changed")
    output = Path(output_root)
    _need(output.is_absolute() and output.parent.resolve(strict=True) == output.parent
          and output.is_relative_to(root) and not output.exists(), "fresh owned qualification output directory required")
    output.mkdir(mode=0o700)
    emitted = []
    def write(name, raw, maximum):
        _need(len(raw) <= maximum, "bounded joined artifact required")
        path = output / name
        with path.open("xb") as stream:
            stream.write(raw)
        emitted.append({"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
    for name, payload in prepared:
        write(name, _raw_json(payload), 65536)
    write("metadata-inputs.json", metadata_raw, MAX_METADATA_BYTES)
    report = {"schema": "terminal-ranker-real-curvature-qualified-cache-joins@1", "status": "prepared_inputs_only",
        "specification": specification_pin, "cache_source": cache_pin,
        "prior_metadata_input": closure[spec["prior_metadata_path"]], "numeric_binding_raw_pin": closure[spec["numeric_binding_path"]],
        "numeric_binding_native_self_sha256": numeric_self, "numeric_binding_complete_object_sha256": api.canonical_sha256(numeric),
        "prior_families": 29, "prior_payloads": 4348, "new_families": list(NEW_FAMILIES), "result_families": 32,
        "result_payloads": sum(len(v) for v in metadata.values()), "prior_payloads_exact_and_order_preserved": True,
        "attempts": attempt_summaries, "proofs": proof_summaries, "pure_lookup_metrics": lookup_totals,
        "raw_inputs_checked_before_and_after": len(closure), "raw_input_bytes": sum(row["bytes"] for row in rows),
        "atomic_snapshot_or_external_pin_origin_authenticated_here": False,
        "native_preparations_here": 0, "gradient_or_optimizer_or_fit_calls_here": 0, "Lean_or_solver_calls_here": 0,
        "metadata_or_database_or_restart_jobs_here": 0, "network_operations_here": 0,
        "ProgramContract_or_RPI_or_core_policy_mutated": False, "output_files": deepcopy(emitted),
        **deepcopy(api._AUTHORITY_PROFILE)}
    write("cache-joins-closed.json", _raw_json(report), 65536)
    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Prepare pinned cache joins and new metadata inputs without indexing")
    parser.add_argument("--specification", required=True)
    parser.add_argument("--specification-sha256", required=True)
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()
    result = build_qualified_cache_joins(specification_path=arguments.specification,
        expected_specification_sha256=arguments.specification_sha256, output_root=arguments.output)
    print(json.dumps({"status": result["status"], "proof_entries": len(result["proofs"]),
                      "pure_lookup_metrics": result["pure_lookup_metrics"]}, sort_keys=True))
