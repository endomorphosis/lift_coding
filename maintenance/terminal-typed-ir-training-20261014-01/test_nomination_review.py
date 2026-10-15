"""Held-out structural query controls without model fitting or source execution."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from nomination_review import (
    NominationReviewError, authored_query_vector, evaluate_nominations)


ROOT = Path(__file__).resolve().parent
PRIOR = ROOT.parent / "terminal-codebase-ir-training-20261014-01"
TYPED = ROOT.parent / "terminal-typed-ir-proof-index-20261014-01"
ALLOWED = {
    "headless-terminal/environment/base_terminal.py",
    "feal-differential-cryptanalysis/environment/feal.py",
    "break-filter-js-from-html/environment/filter.py",
    "llm-inference-batching-scheduler/environment/task_file/scripts/baseline_packer.py",
    "llm-inference-batching-scheduler/environment/task_file/scripts/cost_model.py",
}


@pytest.fixture(scope="module")
def actual_public_targets():
    """Only named sealed public source/IR inputs; no DB, test or solution bodies."""
    from typed_targets import build_targets

    manifest = json.loads((PRIOR / "corpus-manifest-01.json").read_bytes())
    structural = json.loads((TYPED / "experiment-03" / "result.json").read_bytes())["structural"]
    assert {row["path"] for row in structural["sources"]} == ALLOWED
    records = []
    for original in structural["sources"]:
        row = deepcopy(original)
        body = (PRIOR / "experiment-05" / "captured-sources" / row["path"]).read_bytes()
        assert len(body) <= 8192 and hashlib.sha256(body).hexdigest() == row["sha256"]
        row["source_bytes"] = body
        records.append(row)
    targets = build_targets(manifest, records)
    projection = json.loads((TYPED / "experiment-03" / "alignment-projection.json").read_bytes())
    return manifest, records, targets, projection


def _request(actual_public_targets):
    manifest, records, targets, projection = actual_public_targets
    width = len(targets["feature_names"])
    return {"corpus_manifest": manifest, "targets": targets, "source_records": records,
        "learned_reconstructions": deepcopy([row["features"] for row in targets["rows"]]),
        "untrained_reconstructions": [[0.0] * width for row in targets["rows"]],
        "alignment_projection": projection}


def test_one_actual_heldout_alignment_positive_with_six_distinct_controls(actual_public_targets):
    result = evaluate_nominations(**_request(actual_public_targets))
    assert result["candidate_count"] == 28
    assert result["query_count"] == 1
    assert len(result["positive_candidate_ids"]) == 1
    positive = next(row for row in result["candidates"]
        if row["candidate_id"] in result["positive_candidate_ids"])
    assert positive["symbol"] == "align" and positive["split"] == "evaluation"
    assert positive["path"].endswith("/cost_model.py")
    assert positive["exact_retained_projection_source_match"]
    assert result["exact_parent_projection_replayed"]
    assert set(result["methods"]) == {"raw_richer_feature_cosine", "learned_reconstruction_cosine",
        "untrained_reconstruction_cosine", "original_44_ast_count_cosine",
        "lexical_token_overlap", "structured_ast_graph_matching"}
    for method in result["methods"].values():
        assert len(method["ranked_candidates"]) == 28
        assert 1 <= method["positive_ranks"][0] <= 28
        assert method["mrr"] == 1.0 / method["positive_ranks"][0]
        assert all(0 <= value <= 1 for value in method["recall_at_k"].values())
        assert method["ranking_authority"] == "candidate_nomination_only"


def test_fixed_query_has_explicit_oov_without_fitting_or_observing_heldout_row():
    names = ['ast|["kind","Return"]', 'ast|["kind","Add"]', 'types|["annotation","int"]']
    query = authored_query_vector(names)
    assert query["vector"] == [2 ** -0.5, 2 ** -0.5, 1.0]
    assert query["oov_atoms"]
    assert any(row["atom"] == 'ast|["kind","FloorDiv"]' for row in query["oov_atoms"])
    assert query["query_derived_from_heldout_row"] is False
    assert query["query_atoms_added_to_vocabulary"] is False
    assert names == ['ast|["kind","Return"]', 'ast|["kind","Add"]', 'types|["annotation","int"]']


def test_identity_reconstruction_replays_raw_ranking_but_does_not_claim_a_trained_model(actual_public_targets):
    result = evaluate_nominations(**_request(actual_public_targets))
    assert result["methods"]["raw_richer_feature_cosine"] == result["methods"]["learned_reconstruction_cosine"]
    assert result["optimizer_provenance_verified_here"] is False
    assert result["model_arrays_supplied_by_caller"] is True
    assert result["training_executed_here"] is False
    assert result["heldout_data_used_for_optimizer_gradients_here"] is False


def test_identical_ast_counts_cannot_validate_a_changed_literal(actual_public_targets):
    result = evaluate_nominations(**_request(actual_public_targets))
    control = result["negative_controls"][0]
    assert control["control_id"] == "authored-control:same_counts_different_literal"
    assert control["same_original_44_features_as_positive"] is True
    assert control["structured_ast_match"] is False
    assert control["exact_projection_rejected"] is True
    assert control["training_gradient_used"] is False
    assert control["prover_invoked"] is False
    assert all(row["exact_projection_rejected"] for row in result["negative_controls"])


@pytest.mark.parametrize("change", ["source_hash", "source_body", "source_body_and_hash", "missing_source",
    "escaping_path", "oversized_path"])
def test_changed_sources_cannot_reuse_retained_projection_or_function_features(actual_public_targets, change):
    request = deepcopy(_request(actual_public_targets))
    if change == "missing_source":
        request["source_records"].pop()
    else:
        row = next(row for row in request["source_records"] if row["path"].endswith("/cost_model.py"))
        if change == "escaping_path":
            row["path"] = "../cost_model.py"
        elif change == "oversized_path":
            row["path"] = "a" * 4097 + ".py"
        elif change == "source_hash":
            row["sha256"] = "0" * 64
        else:
            row["source_bytes"] = row["source_bytes"].replace(b"g - 1", b"g - 2")
            if change == "source_body_and_hash":
                row["sha256"] = hashlib.sha256(row["source_bytes"]).hexdigest()
    with pytest.raises(ValueError):
        evaluate_nominations(**request)


@pytest.mark.parametrize("change", ["row_id", "ast_hash", "baseline", "vocabulary", "raw_feature"])
def test_target_or_vocabulary_tampering_cannot_relabel_the_positive(actual_public_targets, change):
    request = deepcopy(_request(actual_public_targets))
    row = request["targets"]["rows"][0]
    if change == "row_id":
        row["row_id"] = "0" * 64
    elif change == "ast_hash":
        row["ast_sha256"] = "0" * 64
    elif change == "baseline":
        row["baseline44_features"][0] += 0.1
    elif change == "vocabulary":
        request["targets"]["feature_names"].append('ast|["kind","EvaluationOnlyNode"]')
    else:
        row["features"][0] += 0.1
    with pytest.raises(ValueError):
        evaluate_nominations(**request)


@pytest.mark.parametrize("change", ["missing_row", "wrong_width", "nan", "bool", "large", "tuple"])
def test_caller_reconstructions_have_exact_bounded_finite_dimensions(actual_public_targets, change):
    request = deepcopy(_request(actual_public_targets))
    if change == "missing_row":
        request["learned_reconstructions"].pop()
    elif change == "wrong_width":
        request["learned_reconstructions"][0].pop()
    elif change == "tuple":
        request["learned_reconstructions"][0] = tuple(request["learned_reconstructions"][0])
    else:
        request["learned_reconstructions"][0][0] = {"nan": float("nan"), "bool": True, "large": 1e7}[change]
    with pytest.raises(NominationReviewError):
        evaluate_nominations(**request)


def test_optional_latent_ranking_requires_a_finite_same_dimension_authored_query(actual_public_targets):
    request = _request(actual_public_targets)
    latents = [[float(index + 1), 1.0] for index in range(len(request["targets"]["rows"]))]
    found = evaluate_nominations(**request, learned_latents=latents, query_latent=[1.0, 1.0])
    assert "learned_latent_cosine" in found["methods"]
    with pytest.raises(NominationReviewError, match="same-model"):
        evaluate_nominations(**request, learned_latents=latents)
    with pytest.raises(NominationReviewError, match="dimension"):
        evaluate_nominations(**request, learned_latents=latents, query_latent=[1.0])


def test_ranking_reports_never_become_benchmark_intent_or_semantic_recall_authority(actual_public_targets):
    result = evaluate_nominations(**_request(actual_public_targets))
    for key in ("proof_authority", "execution_authority", "completion_authority", "omission_authority",
        "source_semantics_verified", "benchmark_intent_understanding_verified",
        "semantic_contract_recall_verified", "full_task_satisfaction_proved",
        "source_model_equivalence_proved", "training_convergence_proved"):
        assert result[key] is False
    assert result["rankings_require_independent_exact_source_validation"] is True
    assert result["prover_invoked_here"] is False
    assert result["source_executed_here"] is False
    assert result["provider_calls"] == 0


def test_deterministic_report_replays_without_mutating_caller_data(actual_public_targets):
    request = _request(actual_public_targets)
    before = deepcopy(request)
    first = evaluate_nominations(**request)
    second = evaluate_nominations(**request)
    assert first == second
    assert request == before
