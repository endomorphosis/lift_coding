"""Pinned, target-free reconstruction rankings and separate authored scoring.

The rank command never opens the reference panel. The score command first
recomputes its already-persisted rankings and then reads the selected panel.
Neither command imports a numerical model stack, trains, or grants semantics.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import math
import os
import sys
import types
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).absolute().parents[3]
REPO = ROOT / "external/ipfs_datasets"
OWNER_ROOT = REPO / "ipfs_datasets_py/logic/formalization/autoencoder"
MAX_BYTES = 32 * 1024 * 1024
ENDPOINT_SCHEMA = "source-reconstruction-evaluation-endpoints/v1"
RANK_SCHEMA = "source-reconstruction-matched-rankings/v1"
SCORE_SCHEMA = "source-reconstruction-authored-diagnostic-scores/v1"
LANES = {"legacy8": [8, 16, 4], "native384": [384, 128, 32], "native768": [768, 128, 64]}
VIEWS = ("raw_source", "latent", "reconstructed", "mean_reconstructed", "pca_reconstructed", "pca_latent")
MASKS = ("weak_decoder_fit", "strong_semantic_fit", "contrastive_supervision", "proof_supervision", "fidelity_evaluation")
SOURCE_FIELDS = ("id", "group_id", "split", "source_sha256", "panel_input_sha256", "lane_input_sha256", "context_role")
BINDINGS = ("checkpoint_binding", "model_file_binding", "training_report_binding", "native_train_bundle_binding",
            "native_query_bundle_binding")
PINS = {
    "alignment_representation_retrieval.py": "fea1daa81d36bf0f3b9264b3c15dfa7f46ec1af3428791b84adef8aa60236abd",
    "alignment_richer_retrieval.py": "bbbac13f8464e6c0b15b8add91ebd0cedeb0db6531c43f7e4962445153a5ef40",
    "alignment_richer_panel.py": "38133619c52349ab11ad44a11f2dc7ff378d8a4d53454939e4d952d99e87c06a",
    "alignment_lane_bundle.py": "d7d2e1303e15d46b70997e5880df6fb9a690bfebde63666cad04db516f3ef3a8",
    "../legal_ir/canonical_contracts.py": "d66ecfaa2c967cda40a1cf4b82936a34039e38ccdb3044468697a4f90af2844b",
}
FALSE = dict.fromkeys(("qualified", "proof_authority", "source_fidelity_established", "semantic_label_admission",
                      "independent_fidelity_available", "production_ranking_authorized", "semantic_equivalence_checked",
                      "training_executed", "model_inference_executed", "runtime_cryptographically_attested",
                      "derivative_provenance_exclusion_verified", "split_provenance_authenticated", "producer_identity_authenticated"), False)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def raw(value):
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    require(len(data) <= MAX_BYTES, "bounded finite ordinary JSON required")
    return data


def digest(value):
    return hashlib.sha256(raw(value)).hexdigest()


def seal(value):
    value["content_sha256"] = digest({k: v for k, v in value.items() if k != "content_sha256"})
    return value


def check_seal(value):
    require(type(value) is dict and value.get("content_sha256") == digest(
        {k: v for k, v in value.items() if k != "content_sha256"}), "content seal differs")


def closed(value, fields, label):
    require(type(value) is dict and set(value) == set(fields), "closed " + label + " required")


def sha(value):
    require(type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value), "lowercase SHA256 required")


def check_binding(value):
    closed(value, {"path", "bytes", "sha256"}, "file binding")
    require(type(value["path"]) is str and Path(value["path"]).is_absolute(), "absolute file path required")
    require(type(value["bytes"]) is int and 0 < value["bytes"] <= MAX_BYTES, "bounded file bytes required")
    sha(value["sha256"])


def file_bytes(path):
    path = Path(path).absolute()
    require(not any(p.is_symlink() for p in (path, *path.parents)), "nonsymlink path required")
    before = path.stat()
    require(path.is_file() and 0 < before.st_size <= MAX_BYTES, "bounded regular file required")
    data = path.read_bytes()
    after = path.stat()
    require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns), "file changed during read")
    require(len(data) == before.st_size, "file read bytes differ")
    return data


def binding(path):
    data = file_bytes(path)
    return {"path": str(Path(path).absolute()), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def parse_json(data):
    def pairs(items):
        value = {}
        for key, item in items:
            require(key not in value, "duplicate JSON key")
            value[key] = item
        return value
    return json.loads(data.decode("utf-8"), object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite JSON")))


def read_bound(value, *, json_value=True):
    check_binding(value)
    data = file_bytes(value["path"])
    require(len(data) == value["bytes"] and hashlib.sha256(data).hexdigest() == value["sha256"], "file binding differs")
    return parse_json(data) if json_value else data


def selected_file(path, expected_sha256):
    sha(expected_sha256)
    reference = binding(path)
    require(reference["sha256"] == expected_sha256, "externally selected file SHA differs")
    return read_bound(reference), reference


def write_json(path, value):
    data = raw(value) + b"\n"
    path = Path(path).absolute()
    require(path.parent.is_dir() and not any(p.is_symlink() for p in (path, *path.parents)), "fresh nonsymlink output required")
    with path.open("xb") as stream:
        os.chmod(path, 0o600)
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return binding(path)


def _extract(path, expected, names, context):
    """Execute only selected AST nodes from the unchanged hash-selected owner."""
    data = file_bytes(path)
    require(hashlib.sha256(data).hexdigest() == expected, "frozen metric owner SHA differs")
    parsed = ast.parse(data.decode("utf-8"), filename=str(path))
    nodes = [node for node in parsed.body if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name in names]
    require({node.name for node in nodes} == set(names) and len(nodes) == len(names), "metric owner entrypoints differ")
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), context)


def metric_owner():
    """Exact original arithmetic, with a canonical-wire-only target validator.

    The old _target additionally constructed unused structural features. The
    bound panel accepts one canonical seven-facet rule; validating that same
    wire payload directly avoids importing the unrelated feature/IR runtimes.
    """
    context = {"math": math, "Counter": Counter, "hashlib": hashlib, "json": json, "MAX_BYTES": 8 * 1024 * 1024,
               "SOURCE_WIDTHS": (8, 384, 768), "CORE_FACETS": ("modality", "actor", "action", "object"),
               "QUALIFIER_FACETS": ("conditions", "exceptions", "temporal")}
    context["FACET_WEIGHTS"] = dict.fromkeys(context["CORE_FACETS"] + context["QUALIFIER_FACETS"], 1.0)
    _extract(OWNER_ROOT / "alignment_richer_retrieval.py", PINS["alignment_richer_retrieval.py"],
             {"_require", "_raw", "_digest", "_finite", "_unit", "_counter_jaccard", "_facet_matches", "_metrics", "_coverage"}, context)
    context["_target"] = canonical_target
    _extract(OWNER_ROOT / "alignment_representation_retrieval.py", PINS["alignment_representation_retrieval.py"],
             {"_rank", "_score"}, context)
    return context


def canonical_target(value):
    """Bounded canonical seven-facet payload, without feature hashing."""
    closed(value, {"rules"}, "authored canonical target")
    require(type(value["rules"]) is list and len(value["rules"]) == 1, "one authored canonical rule required")
    rule = value["rules"][0]
    core = ("modality", "actor", "action", "object")
    qualifiers = ("conditions", "exceptions", "temporal")
    closed(rule, core + qualifiers, "canonical rule")
    require(rule["modality"] in {"O", "P", "F"}, "canonical modality differs")
    for facet in core:
        require(type(rule[facet]) is str and len(rule[facet]) <= 512 and "\x00" not in rule[facet]
                and (bool(rule[facet].strip()) or facet == "object" and rule[facet] == ""), "bounded canonical atom required")
    for facet in qualifiers:
        values = rule[facet]
        require(type(values) is list and len(values) <= 3
                and all(type(v) is str and 0 < len(v) <= 512 and v.strip() and "\x00" not in v for v in values)
                and values == sorted(set(values)), "sorted unique canonical qualifiers required")
    return {"canonical_ir": value}


def validate_endpoints(value):
    closed(value, {"schema", "lane_id", "seed", "architecture", "source_profile_sha256", *BINDINGS, "rows", "pca_control",
                   "model_inference_executed", "optimizer_updates", "content_sha256"}, "endpoint artifact")
    check_seal(value)
    require(value["schema"] == ENDPOINT_SCHEMA and value["lane_id"] in LANES, "endpoint schema/lane differs")
    require(type(value["seed"]) is int and value["seed"] in (1729, 1730, 1731)
            and value["architecture"] == LANES[value["lane_id"]], "selected architecture/seed differs")
    require(value["model_inference_executed"] is True and type(value["optimizer_updates"]) is int
            and value["optimizer_updates"] == 0, "frozen inference without optimizer updates required")
    sha(value["source_profile_sha256"])
    for key in BINDINGS:
        check_binding(value[key])
    d, _, z = value["architecture"]
    pca = value["pca_control"]
    closed(pca, {"effective_train_rank", "retained_axes", "threshold", "basis_sha256", "fit_rows",
                 "query_rows_read_before_fit", "recipe"}, "PCA control")
    require(type(pca["effective_train_rank"]) is int and 1 <= pca["effective_train_rank"] <= min(d, 15)
            and type(pca["retained_axes"]) is int and pca["retained_axes"] == min(z, pca["effective_train_rank"]), "declared PCA axes/rank differ")
    require(type(pca["threshold"]) in (int, float) and math.isfinite(pca["threshold"]) and pca["threshold"] > 0,
            "positive finite PCA threshold required")
    require(type(pca["fit_rows"]) is int and pca["fit_rows"] == 16 and type(pca["query_rows_read_before_fit"]) is int
            and pca["query_rows_read_before_fit"] == 0 and pca["recipe"] == "TRAIN_centered_SVD/v1", "TRAIN-only PCA recipe differs")
    sha(pca["basis_sha256"])
    widths = {view: d for view in VIEWS} | {"latent": z, "pca_latent": pca["retained_axes"]}
    require(type(value["rows"]) is list and len(value["rows"]) == 34, "all34 exposed sources required")
    for row in value["rows"]:
        closed(row, {*SOURCE_FIELDS, "endpoints"}, "target-free endpoint row")
        for field in ("source_sha256", "panel_input_sha256", "lane_input_sha256"):
            sha(row[field])
        require(row["id"] == "sha256:" + row["panel_input_sha256"], "source input ID differs")
        require(type(row["group_id"]) is str and bool(row["group_id"].strip()) and len(row["group_id"]) <= 512,
                "bounded source group required")
        require(row["split"] in {"train", "validation"} and row["context_role"] in {"none_required", "explicit_assumptions"},
                "exposed split/context required")
        require(row["split"] != "train" or row["context_role"] == "none_required", "context sources cannot enter TRAIN")
        closed(row["endpoints"], VIEWS, "declared endpoint views")
        for view, vector in row["endpoints"].items():
            require(vector is None or type(vector) is list and len(vector) == widths[view]
                    and all(type(v) in (int, float) and math.isfinite(v) for v in vector), "endpoint width/finite values differ")
        require(row["endpoints"]["raw_source"] is not None, "original raw source vector required")
    candidates = [row for row in value["rows"] if row["split"] == "train"]
    queries = [row for row in value["rows"] if row["split"] == "validation"]
    require(len(candidates) == 16 and len(queries) == 18, "fixed TRAIN16/query18 accounting differs")
    require(len({row["id"] for row in value["rows"]}) == 34, "duplicate source input ID")
    require(len({row["group_id"] for row in candidates}) == 4 and len({row["group_id"] for row in queries}) == 11,
            "original4TRAIN/11query groups required")
    for field in ("id", "group_id", "source_sha256", "panel_input_sha256", "lane_input_sha256"):
        require({row[field] for row in candidates}.isdisjoint({row[field] for row in queries}), "TRAIN/query " + field + " leakage")
    require(sum(row["context_role"] != "none_required" for row in queries) == 2, "two context diagnostic sources required")
    means = [row["endpoints"]["mean_reconstructed"] for row in value["rows"]]
    require(all(mean == means[0] for mean in means), "TRAIN mean control must be constant for all sources")
    return widths


def rank_endpoints(value):
    """Pure ranking: receives source-only metadata and vectors, never a panel."""
    widths = validate_endpoints(value)
    owner = metric_owner()
    rows = {row["id"]: row for row in value["rows"]}
    selection = [{key: row[key] for key in SOURCE_FIELDS} for row in sorted(rows.values(), key=lambda item: item["id"])]
    candidate_ids = sorted(key for key, row in rows.items() if row["split"] == "train")
    query_ids = sorted(set(rows) - set(candidate_ids))
    arms = {}
    for view in VIEWS:
        pool = {key: rows[key]["endpoints"][view] for key in candidate_ids}
        records = [{"id": key, "panel_input_sha256": rows[key]["panel_input_sha256"],
                    "query_vector_sha256": digest(rows[key]["endpoints"][view]),
                    **owner["_rank"](rows[key]["endpoints"][view], pool, widths[view])} for key in query_ids]
        arms[view] = {"dimension": widths[view], "native_input_dimension": value["architecture"][0],
                      "candidate_vector_sha256s": {key: digest(vector) for key, vector in pool.items()}, "rows": records}
    return seal({"schema": RANK_SCHEMA, "endpoints_content_sha256": value["content_sha256"],
                 "lane_id": value["lane_id"], "seed": value["seed"], "source_profile_sha256": value["source_profile_sha256"],
                 **{key: value[key] for key in BINDINGS}, "pca_control": value["pca_control"],
                 "source_selection": selection, "source_selection_sha256": digest(selection), "candidate_ids": candidate_ids,
                 "query_count": 18, "top_k": 5, "candidate_pool_fixed": True,
                 "declared_source_group_disjointness_checked": True, "declared_source_and_input_disjointness_checked": True,
                 "recipe": "cosine_of_each_declared_endpoint; descending_cosine_then_lexicographic_input_id",
                 "metric_owner_sha256s": {k: PINS[k] for k in ("alignment_representation_retrieval.py", "alignment_richer_retrieval.py")},
                 "arms": arms, "query_reference_consumed": False, "reference_targets_in_candidate_features": False,
                 "upstream_model_inference_executed": True, "ranking_operation_executed": True,
                 "optimizer_updates": 0, "model_calls": 0, "prover_calls": 0, "masks": dict.fromkeys(MASKS, 0), **FALSE})


def validate_rankings(rankings, endpoints):
    check_seal(rankings)
    expected = rank_endpoints(endpoints)
    extras = set(rankings) - set(expected)
    require(extras in (set(), {"endpoints_file_binding", "evaluation_owner_binding"}), "unexpected ranking binding fields")
    if extras:
        require(read_bound(rankings["endpoints_file_binding"]) == endpoints, "ranking endpoint file join differs")
        require(rankings["evaluation_owner_binding"] == binding(__file__), "ranking evaluation owner differs")
        expected = seal({**expected, **{key: rankings[key] for key in extras}})
    require(raw(rankings) == raw(expected), "rankings differ from source-only recomputation")


def _namespace_module(name, relative):
    if name not in sys.modules:
        module = types.ModuleType(name)
        module.__path__ = [str(REPO / relative)]
        module.__package__ = name
        sys.modules[name] = module


def _load_module(name, path, expected):
    require(hashlib.sha256(file_bytes(path)).hexdigest() == expected, "bound validation owner SHA differs")
    if name in sys.modules:
        module = sys.modules[name]
        require(Path(module.__file__).absolute() == Path(path).absolute(), "validation owner already imported from another path")
        return module
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def owners(*, include_panel=False):
    # Bypass broad package __init__ files; only these explicit stdlib owners run.
    for name, relative in (("ipfs_datasets_py", "ipfs_datasets_py"), ("ipfs_datasets_py.logic", "ipfs_datasets_py/logic"),
                           ("ipfs_datasets_py.logic.formalization", "ipfs_datasets_py/logic/formalization"),
                           ("ipfs_datasets_py.logic.formalization.autoencoder", "ipfs_datasets_py/logic/formalization/autoencoder"),
                           ("ipfs_datasets_py.logic.legal_ir", "ipfs_datasets_py/logic/legal_ir"), ("ipfs_datasets_py.utils", "ipfs_datasets_py/utils")):
        _namespace_module(name, relative)
    lane = _load_module("ipfs_datasets_py.logic.formalization.autoencoder.alignment_lane_bundle",
                        OWNER_ROOT / "alignment_lane_bundle.py", PINS["alignment_lane_bundle.py"])
    panel = None
    if include_panel:
        _load_module("ipfs_datasets_py.utils.cid_utils", REPO / "ipfs_datasets_py/utils/cid_utils.py",
                     "190fa0c6958b212d3c7b55dec9c92056c9b73259da6d8e576c4f5b70928cc1bf")
        _load_module("ipfs_datasets_py.logic.legal_ir.canonical_contracts", REPO / "ipfs_datasets_py/logic/legal_ir/canonical_contracts.py",
                     PINS["../legal_ir/canonical_contracts.py"])
        panel = _load_module("ipfs_datasets_py.logic.formalization.autoencoder.alignment_richer_panel",
                             OWNER_ROOT / "alignment_richer_panel.py", PINS["alignment_richer_panel.py"])
    return lane, panel


def verify_bound_inputs(value):
    """Join externally selected endpoint bytes to historical producers/models.

    SHA and source contracts establish saved-file integrity, not authenticated
    encoder/model execution or independent split/derivative provenance.
    """
    validate_endpoints(value)
    lane, _ = owners()
    train = read_bound(value["native_train_bundle_binding"])
    query = read_bound(value["native_query_bundle_binding"])
    for bundle in (train, query):
        expected = {"profile_sha256": digest(bundle["profile"]), "producer_receipt_sha256": digest(bundle["producer_receipt"]),
                    "inputs": [{"id": row["id"], "input_sha256": row["input_sha256"]} for row in bundle["rows"]]}
        lane.validate_lane_bundle(bundle, expected_bindings=expected)
        require(digest(bundle["profile"]) == value["source_profile_sha256"], "native source profile differs")
        require(bundle["profile"]["stage"] in {"historical_linguistic_features", "raw_embedding"}
                and bundle["profile"]["fit_input_recipe"] == bundle["profile"]["inference_input_recipe"] == "exact_source_only/v1",
                "only original exact-source raw views allowed")
    require(train["profile"] == query["profile"] and train["profile"]["lane_id"] == value["lane_id"], "TRAIN/query producer identity differs")
    rows = {row["id"]: row for row in value["rows"]}
    require(len(train["rows"]) == 16 and len(query["rows"]) == 18, "bound native cohort counts differ")
    require({row["id"] for row in train["rows"]} == {key for key, row in rows.items() if row["split"] == "train"}, "wrong TRAIN bank/source IDs")
    require({row["id"] for row in query["rows"]} == {key for key, row in rows.items() if row["split"] == "validation"}, "wrong query/source IDs")
    for source in train["rows"] + query["rows"]:
        row = rows[source["id"]]
        require(source["status"] == "available" and source["vector"] == row["endpoints"]["raw_source"], "raw vectors differ from bound native producer")
        require(source["input_sha256"] == row["lane_input_sha256"] and source["input"]["context"]["role"] == row["context_role"]
                and hashlib.sha256(source["input"]["source_text"].encode("utf-8")).hexdigest() == row["source_sha256"], "bound native source identity differs")
    report = read_bound(value["training_report_binding"])
    checkpoint = read_bound(value["checkpoint_binding"])
    check_seal(report)
    check_seal(checkpoint)
    selected_checkpoint = report["selected_checkpoint"]
    check_binding(selected_checkpoint)
    require(report["schema"] == "source-vector-reconstruction-training-report/v1"
            and report["status"] == "completed_fixed_budget_reconstruction_only" and report["selected_optimizer_updates"] == 200
            and all(selected_checkpoint[key] == value["checkpoint_binding"][key] for key in ("bytes", "sha256")),
            "selected200 model/report byte identity differs")
    require(report["config"] == checkpoint["config"] and checkpoint["schema"] == "source-vector-reconstruction-checkpoint/v1"
            and checkpoint["optimizer_steps"] == 200, "selected checkpoint profile differs")
    cfg = checkpoint["config"]
    require(report["normalization"] == checkpoint["normalization"]
            and digest(checkpoint["normalization"]) == cfg["normalization_sha256"], "selected TRAIN normalization identity differs")
    require(cfg["lane_id"] == value["lane_id"] and cfg["seed"] == value["seed"] and cfg["architecture"] == value["architecture"]
            and cfg["bundle_binding"] == value["native_train_bundle_binding"] and cfg["native_profile"] == train["profile"], "model/native producer join differs")
    require(cfg["training_ids"] == [row["id"] for row in train["rows"]]
            and cfg["input_sha256s"] == [row["input_sha256"] for row in train["rows"]], "model trained source selection differs")
    for selected in (report, checkpoint):
        require(selected["masks"] == dict.fromkeys(MASKS, 0) and all(type(v) is int for v in selected["masks"].values())
                and all(selected[k] is False for k in ("qualified", "semantic_fit_authorized", "contrastive_fit_authorized", "source_fidelity_established", "proof_authority")), "model cannot acquire semantic masks/authority")
    model = checkpoint["model_file"]
    require(value["model_file_binding"] == {**model, "path": str(Path(value["checkpoint_binding"]["path"]).parent / "model.safetensors")}, "selected model file binding differs")
    read_bound(value["model_file_binding"], json_value=False)
    observations = report["final_observations"]
    for index, source in enumerate(train["rows"]):
        require(rows[source["id"]]["endpoints"]["latent"] == observations["latent_vectors"][index]
                and rows[source["id"]]["endpoints"]["reconstructed"] == observations["reconstructed_vectors"][index], "TRAIN forward differs from saved selected model observations")


def score_rankings(rankings, endpoints, panel):
    """Posthoc exposed authored labels; never semantic or proof admission."""
    validate_rankings(rankings, endpoints)
    _, panel_owner = owners(include_panel=True)
    panel_owner.validate_alignment_richer_panel(panel)
    metadata = {"sha256:" + row["input_sha256"]: row for row in panel["rows"]}
    require(len(metadata) == 34 and set(metadata) == {row["id"] for row in rankings["source_selection"]}, "reference panel source IDs differ")
    for row in rankings["source_selection"]:
        item = metadata[row["id"]]
        require(all(row[field] == item[field] for field in ("group_id", "split", "source_sha256"))
                and row["panel_input_sha256"] == item["input_sha256"] and row["context_role"] == item["context"]["role"], "reference panel source identity differs")
    targets = {key: metadata[key]["target"] for key in rankings["candidate_ids"]}
    for target in targets.values():
        canonical_target(target)
    owner = metric_owner()
    arms = {}
    for view, records in rankings["arms"].items():
        positives, negatives, contextual = [], [], []
        for row in records["rows"]:
            item = metadata[row["id"]]
            if item["context"]["role"] != "none_required":
                contextual.append({"id": row["id"], "status": "interpretation_unavailable_context_withheld",
                                   "semantic_score": None, "ranking_status": row["status"]})
            elif item["row_kind"] == "positive":
                positives.append({"id": row["id"], "score": owner["_score"](row, item["target"], targets)})
            else:
                negatives.append({"id": row["id"], "row_kind": item["row_kind"], "status": "diagnostic_ranking_only",
                                  "semantic_score": None, "ranking_status": row["status"]})
        require(len(positives) == 8 and len(negatives) == 8 and len(contextual) == 2, "fixed8positive/8negative/2context accounting differs")
        available = [r["score"]["authored_metrics"] for r in positives if r["score"]["status"] == "available"]
        ndcgs = [r["graded_facet_ndcg"] for r in available if r["graded_facet_ndcg"] is not None]
        arms[view] = {"dimension": records["dimension"], "positive_rows": positives, "negative_diagnostic_rows": negatives,
                      "context_diagnostic_rows": contextual, "summary": {"eligible_positive_queries": 8,
                      "available_score_count": len(available), "mean_graded_facet_ndcg": math.fsum(ndcgs) / len(ndcgs) if ndcgs else None,
                      "mean_ndcg_over8_with_unavailable_zero": math.fsum(ndcgs) / 8,
                      "unavailable_positive_score_count": 8 - len(available)}}
    return seal({"schema": SCORE_SCHEMA, "ranking_content_sha256": rankings["content_sha256"],
                 "endpoints_content_sha256": endpoints["content_sha256"], "panel_payload_sha256": panel["integrity"]["panel_payload_sha256"],
                 "lane_id": endpoints["lane_id"], "seed": endpoints["seed"], "evaluation_role": "exposed_development",
                 "source_profile_sha256": endpoints["source_profile_sha256"],
                 **{key: endpoints[key] for key in BINDINGS}, "pca_control": endpoints["pca_control"],
                 "reference_origin": "synthetic_authored_unreviewed", "facet_weights": dict(owner["FACET_WEIGHTS"]),
                 "facet_match_recipe": "typed_facet_multiset_jaccard; empty_empty_equals_one",
                 "dcg_recipe": "linear_weighted_facet_fraction_over_log2_rank_plus_one; ideal_same_full_training_pool",
                 "target_access": True, "query_reference_consumed_in_ranking": False,
                 "query_reference_bodies_used_in_metrics": 8, "panel_contract_validation_inspects_all_rows": True,
                 "scored_positive_queries": 8, "negative_diagnostic_queries": 8, "context_diagnostic_queries": 2,
                 "upstream_model_inference_executed": True, "negative_abstention_or_context_resolution_established": False,
                 "optimizer_updates": 0, "model_calls": 0, "prover_calls": 0, "masks": dict.fromkeys(MASKS, 0), "arms": arms, **FALSE})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    rank = commands.add_parser("rank")
    score = commands.add_parser("score")
    for selected in (rank, score):
        selected.add_argument("--endpoints", required=True)
        selected.add_argument("--endpoints-sha256", required=True)
        selected.add_argument("--output", required=True)
    score.add_argument("--rankings", required=True)
    score.add_argument("--rankings-sha256", required=True)
    score.add_argument("--panel", required=True)
    score.add_argument("--panel-sha256", required=True)
    args = parser.parse_args()
    endpoints, endpoint_binding = selected_file(args.endpoints, args.endpoints_sha256)
    verify_bound_inputs(endpoints)
    if args.command == "rank":
        result = rank_endpoints(endpoints)
    else:
        rankings, rank_binding = selected_file(args.rankings, args.rankings_sha256)
        validate_rankings(rankings, endpoints)
        # This is the first reference-panel file read in either command.
        panel, panel_binding = selected_file(args.panel, args.panel_sha256)
        result = score_rankings(rankings, endpoints, panel)
        result = seal({**result, "rankings_file_binding": rank_binding, "panel_file_binding": panel_binding})
    result = seal({**result, "endpoints_file_binding": endpoint_binding, "evaluation_owner_binding": binding(__file__)})
    reference = write_json(args.output, result)
    print(json.dumps({"status": "saved", "command": args.command, "output_binding": reference}, sort_keys=True))


if __name__ == "__main__":
    main()
