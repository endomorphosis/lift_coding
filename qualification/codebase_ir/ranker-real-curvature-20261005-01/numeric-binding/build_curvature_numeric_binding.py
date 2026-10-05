"""Pure exact numeric binding for the frozen original four-pair real model.

This binds a candidate quadratic curvature model, not an objective derivative.
Previously qualified native receipts are consumed through required external
pins; their corpus/features/optimizer are not replayed by this module.
"""
from __future__ import annotations

from fractions import Fraction
import hashlib
import json
import math
import re

SCHEMA = "terminal-ranker-original-real-curvature-numeric-binding@1"
DIFFERENCE_ARTIFACT_SCHEMA = "terminal-ranker-original-difference-artifact@1"
ORIGINAL_CORPUS_SHA256 = "sha256:d4aa22b9a7bfe796c31adbcf78f9b72987549a85117b8f08534f5a06c032a3df"
ORIGINAL_DIFFERENCES_SHA256 = "e8504c6e8004a2f2878bc79aae0af54c9541bff82df8cde670b48bdf7da03ac6"
ORIGINAL_FEATURE_PROFILE_SHA256 = "5c9ed26e5c02a2fd12c34dc27fcd6105db6798d28a984031c71e3f56aa5a1751"
ORIGINAL_TRAIN_PAIRS_SHA256 = "ae4c11971dd8f1a763e88e2c113d8c6e8bf1d4919df8f4b2760a36c496729845"
ORIGINAL_NATIVE_UPDATE_PROFILE_SHA256 = "5c8809e8cb25e058d803df64166082eedcf90fc9889ba7de5ee0a534799ba654"
ORIGINAL_MU = 0.01
ORIGINAL_ETA = 0.4053827573154274
ORIGINAL_NATIVE_SMOOTHNESS = 1.233402237705318
PAIR_COUNT, DIMENSION, COORDINATE_OPERATIONS = 4, 80, 320
MAX_INPUT_BYTES, MAX_OUTPUT_BYTES = 8 * 1024 * 1024, 64 * 1024
_OMITTED = object()
_AUTHORITY = tuple("semantic_alignment_verified source_semantics_verified proof_authority "
    "formalization_authority execution_authority completion_authority mutation_authority "
    "omission_authority behavioral_satisfaction whole_program_proved "
    "asymptotic_optimizer_convergence_proved".split())


class NumericCurvatureBindingError(ValueError):
    """A bounded input identity or exact arithmetic prerequisite differs."""


def _need(value, message):
    if value is not True:
        raise NumericCurvatureBindingError(message)


def _wire(value, *, ascii=True, byte_limit=MAX_INPUT_BYTES):
    pending, count = [(value, 0)], 0
    while pending:
        item, depth = pending.pop()
        count += 1
        _need(depth <= 48 and count <= 1_000_000, "bounded plain JSON required")
        if type(item) is dict:
            _need(len(item) <= 65_536 and all(type(k) is str for k in item),
                  "bounded exact string JSON keys required")
            pending.extend((v, depth + 1) for v in item.values())
        elif type(item) is list:
            _need(len(item) <= 65_536, "bounded exact JSON list required")
            pending.extend((v, depth + 1) for v in item)
        elif type(item) is float:
            _need(math.isfinite(item), "finite JSON floats required")
        elif type(item) is int:
            _need(item.bit_length() <= 4096, "bounded exact JSON integers required")
        elif type(item) is str:
            _need(len(item.encode()) <= MAX_INPUT_BYTES, "bounded JSON strings required")
        else:
            _need(type(item) in (bool, type(None)), "exact plain JSON values required")
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=ascii, allow_nan=False).encode()
    _need(len(raw) <= byte_limit, "bounded JSON bytes required")
    return raw


def canonical_sha256(value, *, ascii=True):
    """Complete object hash, including any self field; never a raw-file hash."""
    return hashlib.sha256(_wire(value, ascii=ascii)).hexdigest()


def _digest(value, *, ascii=True):
    return canonical_sha256(value, ascii=ascii)


def _external_pin(value):
    _need(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None,
          "exact lowercase canonical SHA256 pin required")


def _self_digest(value, field, *, ascii=True, prefix=""):
    _need(type(value) is dict and field in value, "native self digest field required")
    _need(value[field] == prefix + _digest({k: v for k, v in value.items() if k != field},
                                         ascii=ascii), "native self digest differs")


def _rational(value):
    return {"numerator": str(value.numerator), "denominator": str(value.denominator)}


def _matrix_shape(differences):
    _need(type(differences) is list and len(differences) == PAIR_COUNT,
          "complete original four-row difference matrix required")
    for row in differences:
        _need(type(row) is list and len(row) == DIMENSION and all(
            type(x) is float and math.isfinite(x) and abs(x) <= 2 for x in row),
            "eighty exact bounded binary64 coordinates per row required")


def _exact_constants(differences, regularization, step_size):
    """Rational work only; the sole matrix-fold entry point, after preflight."""
    _matrix_shape(differences)
    _need(type(regularization) is float and math.isfinite(regularization)
          and type(step_size) is float and math.isfinite(step_size),
          "finite binary64 real-model scalars required")
    rows = [[Fraction.from_float(x) for x in row] for row in differences]
    norms = [sum((x * x for x in row), Fraction(0)) for row in rows]
    mu, eta = Fraction.from_float(regularization), Fraction.from_float(step_size)
    maximum, mean = max(norms), sum(norms, Fraction(0)) / PAIR_COUNT
    average_L, conservative_L = mu + mean / 4, mu + maximum / 4
    _need(mu > 0 and eta > 0 and eta * conservative_L <= 1,
          "exact positive native step exceeds candidate curvature bound")
    return {"pair_difference_coordinates_exact": [[_rational(x) for x in row] for row in rows],
        "pair_squared_norms_exact": [_rational(x) for x in norms],
        "maximum_pair_squared_norm_exact": _rational(maximum),
        "mean_pair_squared_norm_exact": _rational(mean),
        "native_mu_exact": _rational(mu), "native_eta_exact": _rational(eta),
        "logistic_coefficient_cap_exact": _rational(Fraction(1, 4)),
        "mean_curvature_L_exact": _rational(average_L),
        "conservative_curvature_L_exact": _rational(conservative_L),
        "eta_times_mean_curvature_L_exact": _rational(eta * average_L),
        "eta_times_conservative_curvature_L_exact": _rational(eta * conservative_L),
        "exact_positive_mu": True, "exact_positive_eta": True,
        "exact_eta_times_mean_L_le_one": eta * average_L <= 1,
        "exact_eta_times_conservative_L_le_one": True}


def build_numeric_curvature_binding(*, differences, difference_artifact, ranker_result,
        trace_authentication, corpus_envelope, expected_difference_sha256,
        expected_difference_artifact_sha256, expected_ranker_result_sha256,
        expected_authentication_sha256, expected_corpus_envelope_sha256,
        coefficient_cap=_OMITTED, max_coordinate_operations=COORDINATE_OPERATIONS):
    """Bind the original profile to exact constants, with zero native work.

    All five external pins hash complete ASCII canonical JSON objects. The
    difference pin hashes the bare matrix; artifact pin includes its self field.
    Original native corpus identity uses its separate non-ASCII self convention.
    Trusted pin origin and prior native qualifications remain caller prerequisites.
    """
    for value in (expected_difference_sha256, expected_difference_artifact_sha256,
                  expected_ranker_result_sha256, expected_authentication_sha256,
                  expected_corpus_envelope_sha256):
        _external_pin(value)
    _need(type(max_coordinate_operations) is int
          and COORDINATE_OPERATIONS <= max_coordinate_operations <= COORDINATE_OPERATIONS,
          "exact original 320-coordinate budget required before rational work")
    if coefficient_cap is _OMITTED:
        coefficient_cap = {"numerator": "1", "denominator": "4"}
    _need(type(coefficient_cap) is dict and coefficient_cap ==
          {"numerator": "1", "denominator": "4"}, "fixed canonical quarter coefficient required")
    _matrix_shape(differences)
    _need(expected_difference_sha256 == ORIGINAL_DIFFERENCES_SHA256
          and _digest(differences) == expected_difference_sha256,
          "original externally pinned difference matrix differs")
    for obj, expected in ((difference_artifact, expected_difference_artifact_sha256),
            (ranker_result, expected_ranker_result_sha256),
            (trace_authentication, expected_authentication_sha256),
            (corpus_envelope, expected_corpus_envelope_sha256)):
        _need(type(obj) is dict and _digest(obj) == expected, "external complete-object pin differs")
    artifact, result, auth = difference_artifact, ranker_result, trace_authentication
    _need(set(artifact) == {"schema", "corpus_sha256", "feature_profile_sha256",
        "train_pairs_sha256", "differences", "difference_vectors_sha256", "L2",
        "native_step_size", "native_numeric_smoothness", "artifact_sha256"}
        and artifact["schema"] == DIFFERENCE_ARTIFACT_SCHEMA, "exact frozen difference artifact required")
    _self_digest(artifact, "artifact_sha256")
    _matrix_shape(artifact["differences"])
    _need(_digest(artifact["differences"]) == expected_difference_sha256
          and artifact["difference_vectors_sha256"] == expected_difference_sha256,
          "frozen artifact does not contain the supplied original matrix")
    _need(set(corpus_envelope) == {"schema", "corpus", "original_inputs"}
          and corpus_envelope["schema"] == "terminal-intent-relevance-frozen-envelope@1",
          "original frozen corpus envelope required")
    corpus, original_inputs = corpus_envelope["corpus"], corpus_envelope["original_inputs"]
    _need(type(corpus) is dict and type(original_inputs) is dict
          and corpus.get("schema") == "terminal-codebase-native-intent-relevance-corpus@1"
          and corpus.get("corpus_sha256") == ORIGINAL_CORPUS_SHA256,
          "expanded or changed corpus identity is outside original model")
    _self_digest(corpus, "corpus_sha256", ascii=False, prefix="sha256:")
    _need(corpus.get("original_inputs_sha256") == _digest(original_inputs, ascii=False),
          "corpus original-input envelope differs")
    _need(result.get("schema") == "terminal-codebase-intent-ranker-training@1"
          and auth.get("schema") == "terminal-codebase-ranker-training-trace-authentication@1"
          and auth.get("status") == "authenticated_finite_native_training_trace",
          "qualified original native result and trace receipt required")
    _self_digest(result, "result_sha256")
    _self_digest(auth, "authentication_sha256")
    training, checkpoint, profile = result.get("training_receipt"), result.get("checkpoint"), result.get("feature_profile")
    _need(type(training) is dict and type(checkpoint) is dict and type(profile) is dict,
          "complete native training, checkpoint and feature profile required")
    _self_digest(training, "receipt_sha256")
    for obj in (corpus, result, auth):
        _need(all(obj.get(k) is False for k in _AUTHORITY), "operational authority must remain false")
    _need(all(auth.get(k) is False for k in ("historical_execution_origin_authenticated",
          "historical_training_provenance_authenticated_here", "binary64_error_bound_proved",
          "real_logistic_descent_proved", "asymptotic_convergence_proved", "global_optimizer_convergence_proved")),
          "prior trace receipt cannot promote real or historical claims")
    _need(all(obj.get("corpus_sha256") == ORIGINAL_CORPUS_SHA256
              for obj in (artifact, result, auth, training, checkpoint)), "original corpus binding differs")
    _need(profile.get("schema") == "fixed-query-code-lexical-native-AST-interactions@1"
          and type(profile.get("dimension")) is int and profile["dimension"] == DIMENSION
          and _digest(profile) == ORIGINAL_FEATURE_PROFILE_SHA256
          and all(obj.get("feature_profile_sha256") == ORIGINAL_FEATURE_PROFILE_SHA256
                  for obj in (artifact, auth, training, checkpoint)), "original feature profile differs")
    _need(_digest(auth.get("native_update_profile")) == ORIGINAL_NATIVE_UPDATE_PROFILE_SHA256
          and auth.get("native_update_profile_sha256") == ORIGINAL_NATIVE_UPDATE_PROFILE_SHA256,
          "original native update profile differs")
    _need(type(corpus.get("pairs")) is list and type(corpus.get("queries")) is list
          and len(corpus["pairs"]) <= 4096 and len(corpus["queries"]) <= 64,
          "bounded complete corpus membership required")
    _need(all(type(p) is dict for p in corpus["pairs"])
          and all(type(q) is dict for q in corpus["queries"]), "plain native membership rows required")
    pairs = [p for p in corpus["pairs"] if p.get("task_role") == "train"]
    queries = {q.get("query_id"): q.get("task_role") for q in corpus["queries"]}
    _need(len(pairs) == PAIR_COUNT and len(queries) == len(corpus["queries"])
          and all(queries.get(p.get("query_id")) == "train" for p in pairs)
          and _digest(pairs) == ORIGINAL_TRAIN_PAIRS_SHA256
          and _digest(training.get("train_pairs")) == ORIGINAL_TRAIN_PAIRS_SHA256
          and all(obj.get("train_pairs_sha256") == ORIGINAL_TRAIN_PAIRS_SHA256
                  for obj in (artifact, auth)), "original ordered train membership differs")
    _need(auth.get("ranker_result_sha256") == expected_ranker_result_sha256
          and auth.get("native_ranker_result_self_sha256") == result["result_sha256"]
          and auth.get("checkpoint_sha256") == training.get("checkpoint_sha256") == _digest(checkpoint)
          and auth.get("training_receipt_sha256") == training["receipt_sha256"],
          "original native artifact identities differ")
    _need(all(obj.get("train_pair_feature_differences_sha256") == expected_difference_sha256
                  for obj in (training, auth)), "train matrix binding differs")
    for key, native_key, expected in (("L2", "L2", ORIGINAL_MU),
            ("step_size", "native_step_size", ORIGINAL_ETA),
            ("smoothness_upper_bound_numeric", "native_numeric_smoothness", ORIGINAL_NATIVE_SMOOTHNESS)):
        _need(type(training.get(key)) is float and training[key] == expected
              and all(type(obj.get(native_key)) is float and obj[native_key] == expected
                      for obj in (artifact, auth)), "original native scalar/profile differs")
    _need(type(training.get("epochs")) is int and training["epochs"] == 128
          and all(type(auth.get(k)) is int and auth[k] == v for k, v in {
              "epochs": 128, "train_pair_count": PAIR_COUNT, "dimension": DIMENSION,
              "gradient_evaluations": 131, "replay_gradient_evaluations": 129,
              "endpoint_validation_gradient_evaluations": 2, "native_preparation_calls": 2,
              "optimizer_replay_updates": 128, "checked_trace_rows": 129,
              "checked_weight_state_digests": 129, "new_training_fit_calls": 0,
              "checkpoint_activation_calls": 0}.items()), "original trace population/counters differ")
    exact = _exact_constants(differences, training["L2"], training["step_size"])
    conservative = exact["conservative_curvature_L_exact"]
    conservative_L = Fraction(int(conservative["numerator"]), int(conservative["denominator"]))
    native_smoothness = Fraction.from_float(training["smoothness_upper_bound_numeric"])
    _need(native_smoothness >= conservative_L, "native selected smoothness does not cover exact model bound")
    certificate = {"schema": SCHEMA, "status": "exact_original_profile_candidate_curvature_constants",
        "corpus_sha256": ORIGINAL_CORPUS_SHA256, "feature_profile_sha256": ORIGINAL_FEATURE_PROFILE_SHA256,
        "train_pairs_sha256": ORIGINAL_TRAIN_PAIRS_SHA256,
        "native_update_profile_sha256": ORIGINAL_NATIVE_UPDATE_PROFILE_SHA256,
        "external_complete_object_pins": {"difference_artifact_sha256": expected_difference_artifact_sha256,
            "ranker_result_sha256": expected_ranker_result_sha256,
            "authentication_sha256": expected_authentication_sha256,
            "corpus_envelope_sha256": expected_corpus_envelope_sha256},
        "difference_vectors_sha256": expected_difference_sha256,
        "pair_count": PAIR_COUNT, "dimension": DIMENSION, **exact,
        "native_selected_smoothness_exact": _rational(native_smoothness),
        "native_selected_smoothness_ge_exact_conservative_L": True,
        "norm": "squared Euclidean coordinate sum; no function-space default norm",
        "candidate_quadratic_model": "Q(w,v)=mu*sum_j(v_j^2)+mean_i(c(dot(w,d_i))*dot(d_i,v)^2), c(t)=p(t)*(1-p(t)), p(t)=1/(1+exp(t))",
        "coefficient_scope": "each real logistic coefficient lies between zero and the fixed quarter cap; separate theorem input",
        "coordinate_arithmetic_budget": {"charged_coordinate_visits": COORDINATE_OPERATIONS,
            "max_coordinate_operations": max_coordinate_operations,
            "scope": "one complete exact rational embedding and norm square accumulation per coordinate",
            "integer_bit_complexity_or_total_arithmetic_operations_is_not_claimed": True},
        "candidate_curvature_numeric_inequalities_checked": True,
        "candidate_curvature_theorem_checker_status": "not_run_here",
        "actual_real_objective_Hessian_derivative_identity_proved": False,
        "binary64_feature_or_update_correctness_proved": False,
        "binary64_or_libm_error_bound_proved": False,
        "global_optimizer_convergence_proved": False,
        "historical_execution_origin_authenticated_here": False,
        "prior_trace_receipt_consumed_passively": True,
        "prior_trace_replayed_or_revalidated_here": False,
        "external_pin_origin_authenticated_here": False,
        "native_preparation_calls": 0, "native_objective_evaluations": 0,
        "optimizer_updates": 0, "training_calls": 0, "checker_calls": 0,
        "persistence_or_metadata_jobs": 0, "planner_activation": False,
        "full_task_satisfaction": "unknown", "all32_governing_RPI_exits": "OPEN",
        "official_benchmark_score": None, **{k: False for k in _AUTHORITY}}
    certificate["numeric_binding_sha256"] = _digest(certificate)
    _wire(certificate, byte_limit=MAX_OUTPUT_BYTES)
    return certificate


def validate_numeric_curvature_binding(receipt, **arguments):
    """Rebuild every exact constant against required independent input pins."""
    _need(type(receipt) is dict, "plain numeric binding receipt required")
    _self_digest(receipt, "numeric_binding_sha256")
    rebuilt = build_numeric_curvature_binding(**arguments)
    _need(_wire(receipt, byte_limit=MAX_OUTPUT_BYTES) == _wire(rebuilt, byte_limit=MAX_OUTPUT_BYTES),
          "numeric curvature binding differs from pinned exact model")
    return rebuilt
