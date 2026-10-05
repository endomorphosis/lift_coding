"""Pure numeric controls: no fit, optimizer replay, corpus prepare or checker.

The original matrix fixture is materialized once by the separately admitted
root preparation. Tests read its immutable bytes and prior frozen receipts.
These controls have no official benchmark score or general convergence claim.
"""
from copy import deepcopy
from fractions import Fraction
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[3]
spec = importlib.util.spec_from_file_location("original_curvature_numeric_binding",
                                            HERE / "build_curvature_numeric_binding.py")
numeric = importlib.util.module_from_spec(spec)
spec.loader.exec_module(numeric)


def _read(path, raw_sha256=None):
    raw = path.read_bytes()
    if raw_sha256 is not None:
        assert hashlib.sha256(raw).hexdigest() == raw_sha256
    return json.loads(raw)


def _rational(value):
    return Fraction(int(value["numerator"]), int(value["denominator"]))


def _reseal(obj, field, *, ascii=True, prefix=""):
    obj.pop(field, None)
    obj[field] = prefix + numeric.canonical_sha256(obj, ascii=ascii)


@pytest.fixture(scope="module")
def original_arguments():
    previous = WORKSPACE / "qualification/codebase_ir/ranker-trace-authentication-20261005-01"
    request = _read(previous / "preparation/request.json")
    artifact = _read(HERE / "original-differences-01.json")
    corpus = _read(Path(request["original_corpus_envelope"]["path"]),
                   "2a452811f54d85509e2d0b0c962ecab5d8cd221a6cd0321556a387c95da0a8e7")
    result = _read(Path(request["original_ranker_result"]["path"]),
                   "6a6b7eaa20bf1a82a958ff6c9a6ab6f64c613fb880569a76b625de156284d60a")
    auth = _read(previous / "evidence/actual-01/authentication-result.json",
                 "43b69bbb493c0aff290b040eb734d24866b2c83817e96950a0a86aada057f794")
    assert artifact["artifact_sha256"] == "b118242266592aa2fd553fc9a23ad649271513202c7708c991506553cf1530d8"
    assert numeric.canonical_sha256(result) == "6d904cc4662e271372c68bd27d5a6c041018cd786259c2f48adec919c7a80ef4"
    return {"differences": deepcopy(artifact["differences"]), "difference_artifact": artifact,
        "corpus_envelope": corpus, "ranker_result": result, "trace_authentication": auth,
        "expected_difference_sha256": numeric.ORIGINAL_DIFFERENCES_SHA256,
        "expected_difference_artifact_sha256": numeric.canonical_sha256(artifact),
        "expected_corpus_envelope_sha256": numeric.canonical_sha256(corpus),
        "expected_ranker_result_sha256": numeric.canonical_sha256(result),
        "expected_authentication_sha256": numeric.canonical_sha256(auth)}


@pytest.fixture(scope="module")
def original_certificate(original_arguments):
    return numeric.build_numeric_curvature_binding(**original_arguments)


def _no_norm_work(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("preflight refusal reached exact norm work")
    monkeypatch.setattr(numeric, "_exact_constants", forbidden)


def _refuse_before_norm(monkeypatch, arguments):
    _no_norm_work(monkeypatch)
    with pytest.raises(numeric.NumericCurvatureBindingError):
        numeric.build_numeric_curvature_binding(**arguments)


def _update_artifact_pin(arguments):
    artifact = arguments["difference_artifact"]
    _reseal(artifact, "artifact_sha256")
    arguments["expected_difference_artifact_sha256"] = numeric.canonical_sha256(artifact)


def _update_result_and_auth_pins(arguments):
    result, auth = arguments["ranker_result"], arguments["trace_authentication"]
    training = result["training_receipt"]
    _reseal(training, "receipt_sha256")
    _reseal(result, "result_sha256")
    result_pin = numeric.canonical_sha256(result)
    auth["ranker_result_sha256"] = result_pin
    auth["native_ranker_result_self_sha256"] = result["result_sha256"]
    auth["training_receipt_sha256"] = training["receipt_sha256"]
    _reseal(auth, "authentication_sha256")
    arguments["expected_ranker_result_sha256"] = result_pin
    arguments["expected_authentication_sha256"] = numeric.canonical_sha256(auth)


def test_original_complete_exact_numeric_binding(original_arguments, original_certificate):
    c = original_certificate
    assert c["pair_count"] == 4 and c["dimension"] == 80
    assert [len(row) for row in c["pair_difference_coordinates_exact"]] == [80] * 4
    for original, embedded in zip(original_arguments["differences"], c["pair_difference_coordinates_exact"]):
        assert [_rational(x) for x in embedded] == [Fraction.from_float(x) for x in original]
    assert [_rational(x) for x in c["pair_squared_norms_exact"]] == [
        Fraction(46646319711462335500654408216079793, 20769187434139310514121985316880384),
        Fraction(1507989278949607563828642550842453, 1298074214633706907132624082305024),
        Fraction(5819461529695142022881884510840989, 5192296858534827628530496329220096),
        Fraction(6352267595556608209575680854216019, 2596148429267413814265248164610048)]
    assert _rational(c["native_mu_exact"]) == Fraction(5764607523034235, 576460752303423488)
    assert _rational(c["native_eta_exact"]) == Fraction(1825681634788183, 4503599627370496)
    assert _rational(c["mean_curvature_L_exact"]) == Fraction(
        148193205047351780041480481833762829, 332306998946228968225951765070086144)
    assert _rational(c["conservative_curvature_L_exact"]) == Fraction(
        6456113532727304764308018601938259, 10384593717069655257060992658440192)
    assert _rational(c["eta_times_mean_curvature_L_exact"]) < _rational(c["eta_times_conservative_curvature_L_exact"]) < 1
    assert c["coordinate_arithmetic_budget"]["charged_coordinate_visits"] == 320
    assert all(c[k] == 0 for k in ("native_preparation_calls", "native_objective_evaluations",
        "optimizer_updates", "training_calls", "checker_calls", "persistence_or_metadata_jobs"))
    assert c["actual_real_objective_Hessian_derivative_identity_proved"] is False
    assert c["binary64_feature_or_update_correctness_proved"] is False
    assert c["global_optimizer_convergence_proved"] is False
    assert c["proof_authority"] is False and c["full_task_satisfaction"] == "unknown"
    assert c["official_benchmark_score"] is None
    assert len(numeric._wire(c)) <= 65536


def test_companion_accepts_complete_genuine_binding(original_arguments, original_certificate):
    assert numeric.validate_numeric_curvature_binding(original_certificate, **original_arguments) == original_certificate


def test_hand_authored_exact_norm_and_constants():
    # Authored arithmetic unit fixture only; no original/native authenticity claim.
    matrix = [[0.0] * 80 for _ in range(4)]
    for row, length in zip(matrix, (1.0, 2.0, 1.0, 0.0)):
        row[0] = length
    c = numeric._exact_constants(matrix, 0.25, 0.25)
    assert [_rational(x) for x in c["pair_squared_norms_exact"]] == [1, 4, 1, 0]
    assert _rational(c["mean_curvature_L_exact"]) == Fraction(5, 8)
    assert _rational(c["conservative_curvature_L_exact"]) == Fraction(5, 4)
    assert _rational(c["eta_times_conservative_curvature_L_exact"]) == Fraction(5, 16)


def test_below_exact_rounded_norm_cannot_certify_boundary_step():
    # Native squared-product summation rounds 1 + 2^-54 to 1, below the real sum.
    row = [1.0, 2.0 ** -27] + [0.0] * 78
    exact_norm = Fraction(1) + Fraction(1, 2 ** 54)
    assert Fraction.from_float(float(exact_norm)) == 1 < exact_norm
    assert Fraction(2) * (Fraction(1, 4) + Fraction(1, 4)) == 1
    assert Fraction(2) * (Fraction(1, 4) + exact_norm / 4) > 1
    with pytest.raises(numeric.NumericCurvatureBindingError, match="exact positive native step"):
        numeric._exact_constants([row[:] for _ in range(4)], 0.25, 2.0)


@pytest.mark.parametrize("key,value", [
    ("expected_difference_sha256", None),
    ("expected_difference_artifact_sha256", True),
    ("expected_authentication_sha256", "A" * 64),
    ("expected_difference_sha256", "0" * 64),
    ("expected_difference_artifact_sha256", "0" * 64),
    ("expected_ranker_result_sha256", "0" * 64),
    ("expected_authentication_sha256", "0" * 64),
    ("expected_corpus_envelope_sha256", "0" * 64)])
def test_external_pins_refuse_before_norm(original_arguments, monkeypatch, key, value):
    arguments = dict(original_arguments, **{key: value})
    _refuse_before_norm(monkeypatch, arguments)


@pytest.mark.parametrize("budget", [True, 319, 321])
def test_exact_coordinate_budget_refuses_before_norm(original_arguments, monkeypatch, budget):
    _refuse_before_norm(monkeypatch, dict(original_arguments, max_coordinate_operations=budget))


@pytest.mark.parametrize("mutation", ["lost_pair", "lost_coordinate", "boolean_coordinate", "nonfinite_coordinate"])
def test_matrix_population_and_scalar_types_refuse_before_norm(original_arguments, monkeypatch, mutation):
    arguments = deepcopy(original_arguments)
    matrix = arguments["differences"]
    if mutation == "lost_pair":
        matrix.pop()
    elif mutation == "lost_coordinate":
        matrix[0].pop()
    elif mutation == "boolean_coordinate":
        matrix[0][0] = True
    else:
        matrix[0][0] = float("nan")
    _refuse_before_norm(monkeypatch, arguments)


@pytest.mark.parametrize("cap", [None, {"numerator": "1", "denominator": "2"},
                                      {"numerator": "2", "denominator": "8"}])
def test_quarter_cap_is_fixed_and_canonical(original_arguments, monkeypatch, cap):
    _refuse_before_norm(monkeypatch, dict(original_arguments, coefficient_cap=cap))


@pytest.mark.parametrize("field", ["feature_profile_sha256", "train_pairs_sha256", "corpus_sha256",
                                  "native_step_size", "L2", "differences"])
def test_resealed_frozen_artifact_with_new_external_pin_still_refuses(original_arguments, monkeypatch, field):
    arguments = deepcopy(original_arguments)
    artifact = arguments["difference_artifact"]
    if field == "differences":
        artifact[field][0][0] += 0.125
        artifact["difference_vectors_sha256"] = numeric.canonical_sha256(artifact[field])
    elif field in ("L2", "native_step_size"):
        artifact[field] *= 2
    else:
        artifact[field] = "sha256:" + "0" * 64 if field == "corpus_sha256" else "0" * 64
    _update_artifact_pin(arguments)
    _refuse_before_norm(monkeypatch, arguments)


@pytest.mark.parametrize("mutation", ["feature_profile", "step", "regularization"])
def test_coherently_resealed_native_receipts_and_new_pins_cannot_swap_original_profile(original_arguments, monkeypatch, mutation):
    arguments = deepcopy(original_arguments)
    result, auth, artifact = arguments["ranker_result"], arguments["trace_authentication"], arguments["difference_artifact"]
    if mutation == "feature_profile":
        result["feature_profile"]["tokenization"] = "forged alternate tokenizer"
        pin = numeric.canonical_sha256(result["feature_profile"])
        for obj in (result["checkpoint"], result["training_receipt"], auth, artifact):
            obj["feature_profile_sha256"] = pin
        checkpoint_pin = numeric.canonical_sha256(result["checkpoint"])
        result["training_receipt"]["checkpoint_sha256"] = auth["checkpoint_sha256"] = checkpoint_pin
    else:
        key, native_key = ("step_size", "native_step_size") if mutation == "step" else ("L2", "L2")
        result["training_receipt"][key] *= 2
        auth[native_key] = artifact[native_key] = result["training_receipt"][key]
    _update_artifact_pin(arguments)
    _update_result_and_auth_pins(arguments)
    _refuse_before_norm(monkeypatch, arguments)


@pytest.mark.parametrize("mutation", ["native_profile", "trace_population", "real_descent_claim"])
def test_resealed_trace_profile_and_qualification_swaps_refuse_before_norm(original_arguments, monkeypatch, mutation):
    arguments = deepcopy(original_arguments)
    auth = arguments["trace_authentication"]
    if mutation == "native_profile":
        auth["native_update_profile"]["libm_error_bound_proved"] = True
        auth["native_update_profile_sha256"] = numeric.canonical_sha256(auth["native_update_profile"])
    elif mutation == "trace_population":
        auth["replay_gradient_evaluations"] = 128
    else:
        auth["real_logistic_descent_proved"] = True
    _reseal(auth, "authentication_sha256")
    arguments["expected_authentication_sha256"] = numeric.canonical_sha256(auth)
    _refuse_before_norm(monkeypatch, arguments)


def test_changed_corpus_resealed_with_new_pin_is_outside_original_model(original_arguments, monkeypatch):
    arguments = deepcopy(original_arguments)
    envelope = arguments["corpus_envelope"]
    envelope["original_inputs"]["query_records"][0]["navigation_text"] += " forged"
    corpus = envelope["corpus"]
    corpus["original_inputs_sha256"] = numeric.canonical_sha256(envelope["original_inputs"], ascii=False)
    _reseal(corpus, "corpus_sha256", ascii=False, prefix="sha256:")
    arguments["expected_corpus_envelope_sha256"] = numeric.canonical_sha256(envelope)
    _refuse_before_norm(monkeypatch, arguments)


def test_ordered_membership_cannot_be_resealed_and_swapped(original_arguments, monkeypatch):
    arguments = deepcopy(original_arguments)
    result, auth, artifact = arguments["ranker_result"], arguments["trace_authentication"], arguments["difference_artifact"]
    result["training_receipt"]["train_pairs"].reverse()
    swapped_pin = numeric.canonical_sha256(result["training_receipt"]["train_pairs"])
    auth["train_pairs_sha256"] = artifact["train_pairs_sha256"] = swapped_pin
    _update_artifact_pin(arguments)
    _update_result_and_auth_pins(arguments)
    _refuse_before_norm(monkeypatch, arguments)


def test_forged_whole_native_result_self_digest_refuses_before_norm(original_arguments, monkeypatch):
    arguments = deepcopy(original_arguments)
    arguments["ranker_result"]["result_sha256"] = "0" * 64
    arguments["expected_ranker_result_sha256"] = numeric.canonical_sha256(arguments["ranker_result"])
    _refuse_before_norm(monkeypatch, arguments)


@pytest.mark.parametrize("mutation", ["coordinate", "curvature", "coefficient", "derivative_claim", "authority"])
def test_self_resealed_certificate_cannot_change_numeric_model_or_claims(original_arguments, original_certificate, mutation):
    forged = deepcopy(original_certificate)
    if mutation == "coordinate":
        forged["pair_difference_coordinates_exact"][0][0] = {"numerator": "7", "denominator": "8"}
    elif mutation == "curvature":
        forged["mean_curvature_L_exact"]["numerator"] = "1"
    elif mutation == "coefficient":
        forged["logistic_coefficient_cap_exact"]["denominator"] = "2"
    elif mutation == "derivative_claim":
        forged["actual_real_objective_Hessian_derivative_identity_proved"] = True
    else:
        forged["proof_authority"] = True
    _reseal(forged, "numeric_binding_sha256")
    with pytest.raises(numeric.NumericCurvatureBindingError, match="differs from pinned exact model"):
        numeric.validate_numeric_curvature_binding(forged, **original_arguments)


def test_certificate_self_digest_failure_refuses_before_norm(original_arguments, original_certificate, monkeypatch):
    forged = deepcopy(original_certificate)
    forged["numeric_binding_sha256"] = "0" * 64
    _no_norm_work(monkeypatch)
    with pytest.raises(numeric.NumericCurvatureBindingError, match="self digest"):
        numeric.validate_numeric_curvature_binding(forged, **original_arguments)
