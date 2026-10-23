"""One authored held-out structural query; ranking is candidate evidence only.

The fixed query is declared independently of feature fitting. Only the
training-fitted vocabulary can represent its atoms. Reconstructed vectors and
optional latents nominate source functions; separate exact source/projection
checks retain the distinction between retrieval and conditional model proof.
No repository function, prover, provider, or optimizer is executed here.
"""
from __future__ import annotations

import ast
import hashlib
import json
import math
from pathlib import PurePosixPath
import re


SCHEMA = "terminal-typed-structural-nomination-review@1"
QUERY_ID = "authored-query:integer-ceiling-alignment-expression@1"
MAX_CANDIDATES = 1024
MAX_WIDTH = 4096
MAX_SOURCE_BYTES = 8192
_AUTHORITY = dict(proof_authority=False, execution_authority=False,
    completion_authority=False, omission_authority=False,
    source_semantics_verified=False, benchmark_intent_understanding_verified=False,
    semantic_contract_recall_verified=False, full_task_satisfaction_proved=False,
    source_model_equivalence_proved=False, training_convergence_proved=False)


class NominationReviewError(ValueError):
    """The supplied evidence or bounded diagnostic population is inconsistent."""


def _wire(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False).encode("utf-8")


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _need(condition, message):
    if not condition:
        raise NominationReviewError(message)


def _key(modality, *parts):
    return modality + "|" + json.dumps(list(parts), separators=(",", ":"), ensure_ascii=False)


def authored_query_vector(feature_names):
    """Project a fixed authored arithmetic query through train-only keys.

    Counts describe the requested expression shape, not an observed held-out
    feature row. Missing keys remain explicit OOV atoms; they are never added
    to the vocabulary. Normalize independently within each named modality.
    """
    _need(type(feature_names) is list and 0 < len(feature_names) <= MAX_WIDTH
        and all(type(name) is str and len(name) <= 4096 and "|" in name for name in feature_names)
        and len(set(feature_names)) == len(feature_names),
        "bounded unique training feature names required")
    counts = {_key("ast", "kind", name): value for name, value in {
        "FunctionDef": 1, "Return": 1, "BinOp": 4, "Add": 1, "Sub": 1,
        "Mult": 1, "FloorDiv": 1, "Name": 8, "Load": 8, "Constant": 1,
        "arguments": 1, "arg": 2}.items()}
    counts.update({_key("ast", "edge", "BinOp", "op", name): 1
        for name in ("Add", "Sub", "Mult", "FloorDiv")})
    counts[_key("ast", "edge", "Return", "value", "BinOp")] = 1
    counts[_key("literals", "int", "1")] = 1
    counts[_key("interfaces", "parameter_count", 2)] = 1
    counts[_key("types", "annotation", "int")] = 3
    values = [math.log1p(counts.get(name, 0)) for name in feature_names]
    groups = {}
    for index, name in enumerate(feature_names):
        groups.setdefault(name.split("|", 1)[0], []).append(index)
    for indices in groups.values():
        norm = math.sqrt(sum(values[index] ** 2 for index in indices))
        if norm:
            for index in indices:
                values[index] /= norm
    present = set(feature_names)
    result = {"schema": "terminal-authored-structural-query@1", "query_id": QUERY_ID,
        "declaration_timing": "fixed_in_source_before_feature_fitting",
        "criteria": {"returns": 1, "operators": ["Add", "Sub", "Mult", "FloorDiv"],
            "parameters": 2, "annotation": "int", "integer_literal": 1,
            "expression": "((parameter_0 + parameter_1 - 1) // parameter_1) * parameter_1"},
        "counts": counts, "represented_atoms": sorted(set(counts) & present),
        "oov_atoms": [{"atom": name, "count": counts[name]} for name in sorted(set(counts) - present)],
        "vector": values, "normalization": "per-modality log1p counts then L2",
        "query_derived_from_heldout_row": False, "query_atoms_added_to_vocabulary": False}
    result["query_sha256"] = _sha(_wire(result))
    return result


def _vectors(value, count, width, label):
    _need(type(value) is list and len(value) == count, label + " population differs")
    copied = []
    for row in value:
        _need(type(row) is list and len(row) == width, label + " dimension differs")
        _need(all(type(item) in (int, float) and math.isfinite(item) and abs(item) <= 1e6 for item in row),
            label + " requires finite bounded exact numbers")
        copied.append([float(item) for item in row])
    return copied


def _cosine(left, right):
    denominator = math.sqrt(sum(item * item for item in left)) * math.sqrt(sum(item * item for item in right))
    return 0.0 if not denominator else max(-1.0, min(1.0,
        sum(a * b for a, b in zip(left, right)) / denominator))


def _sources(source_records):
    _need(type(source_records) is list and 1 <= len(source_records) <= 5,
        "one to five exact source records required")
    result = {}
    for row in source_records:
        _need(type(row) is dict and type(row.get("path")) is str, "source record path required")
        path = row["path"]
        pure = PurePosixPath(path)
        _need(bool(path) and len(path.encode("utf-8")) <= 4096
            and pure.as_posix() == path and not pure.is_absolute()
            and ".." not in pure.parts and ".git" not in pure.parts and path.endswith(".py")
            and path not in result and "\\" not in path and not any(char in path for char in "\r\n\0"),
            "unique canonical Python source path required")
        body = row.get("source_bytes")
        if body is None and type(row.get("source_text")) is str:
            body = row["source_text"].encode("utf-8")
        _need(type(body) is bytes and 0 < len(body) <= MAX_SOURCE_BYTES, "bounded exact source bytes required")
        _need(type(row.get("sha256")) is str and _sha(body) == row["sha256"],
            "source record SHA256 differs")
        try:
            body.decode("utf-8")
        except UnicodeError as error:
            raise NominationReviewError("UTF-8 source required") from error
        result[path] = body
    return result


def _function_nodes(sources):
    result = {}
    for path, body in sources.items():
        try:
            tree = ast.parse(body.decode("utf-8"))
        except (SyntaxError, ValueError, RecursionError) as error:
            raise NominationReviewError("source function parsing failed") from error
        def visit(node, prefix=""):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                result[(path, prefix + node.name, node.lineno)] = node
                prefix += node.name + "."
            elif isinstance(node, ast.ClassDef):
                prefix += node.name + "."
            for child in ast.iter_child_nodes(node):
                visit(child, prefix)
        visit(tree)
    _need(0 < len(result) <= MAX_CANDIDATES, "bounded complete function population required")
    return result


def _fragment(body, node):
    offsets = [0, *[index + 1 for index, value in enumerate(body) if value == 10]]
    start = offsets[node.lineno - 1] + node.col_offset
    end = offsets[node.end_lineno - 1] + node.end_col_offset
    return body[start:end], start, end


def _shape(node):
    """Independent authored AST-pattern match; annotations imply no runtime type."""
    if type(node) is not ast.FunctionDef or len(node.body) != 1 or type(node.body[0]) is not ast.Return:
        return False
    args = node.args
    if (len(args.posonlyargs) + len(args.args) != 2 or args.kwonlyargs or args.vararg or args.kwarg
            or args.defaults or args.kw_defaults or node.decorator_list):
        return False
    annotations = [arg.annotation for arg in (*args.posonlyargs, *args.args)] + [node.returns]
    if not all(type(annotation) is ast.Name and annotation.id == "int" for annotation in annotations):
        return False
    names = [arg.arg for arg in (*args.posonlyargs, *args.args)]
    def expression(value):
        if type(value) is ast.Name and value.id in names:
            return ["parameter", names.index(value.id)]
        if type(value) is ast.Constant and type(value.value) is int:
            return ["literal", value.value]
        if type(value) is ast.BinOp and type(value.op) in (ast.Add, ast.Sub, ast.Mult, ast.FloorDiv):
            return [type(value.op).__name__, expression(value.left), expression(value.right)]
        return ["unsupported"]
    return expression(node.body[0].value) == ["Mult", ["FloorDiv", ["Sub",
        ["Add", ["parameter", 0], ["parameter", 1]], ["literal", 1]],
        ["parameter", 1]], ["parameter", 1]]


def _lexical(source):
    terms = set(re.findall(r"[a-z]+", source.lower()))
    wanted = {"return", "align", "int", "granularity", "arithmetic", "floor"}
    return len(terms & wanted) / len(wanted)


def _ranking(scores, candidates, positive_ids):
    rows = sorted(({"candidate_id": candidate["candidate_id"], "score": float(score)}
        for candidate, score in zip(candidates, scores)), key=lambda row: (-row["score"], row["candidate_id"]))
    positive_ranks = [index + 1 for index, row in enumerate(rows) if row["candidate_id"] in positive_ids]
    _need(len(positive_ranks) == len(positive_ids), "positive ranking population lost")
    return {"ranked_candidates": rows, "positive_ranks": positive_ranks,
        "mrr": 1.0 / min(positive_ranks),
        "recall_at_k": {str(k): sum(rank <= k for rank in positive_ranks) / len(positive_ids)
            for k in (1, 3, 5, 10)}, "ranking_authority": "candidate_nomination_only"}


def _negative_controls(query44):
    from align_projection import AlignmentProjectionError, project_alignment
    from ipfs_datasets_py.logic.formalization.autoencoder.security import codebase_autoencoder as baseline

    positive = b"def align(x: int, g: int) -> int:\n    return ((x + g - 1) // g) * g\n"
    definitions = [
        ("same_counts_different_literal", positive.replace(b"g - 1", b"g - 2")),
        ("wrong_multiplication", positive.replace(b") * g", b") + g")),
        ("wrong_division", positive.replace(b") // g", b") / g")),
    ]
    reference, unsupported = baseline._features({"control.py": positive}, ["control.py"], 16)
    _need(not unsupported and len(reference) == 1, "authored positive control unavailable")
    result = []
    for name, body in definitions:
        found, unsupported = baseline._features({"control.py": body}, ["control.py"], 16)
        _need(not unsupported and len(found) == 1, "authored negative control unavailable")
        try:
            project_alignment(source_bytes=body, source_path="control.py", source_sha256=_sha(body))
        except AlignmentProjectionError as error:
            rejected, reason = True, str(error)
        else:
            rejected, reason = False, "unexpected_projection_acceptance"
        _need(rejected, "false arithmetic formula must be rejected by exact source projector")
        node = ast.parse(body.decode()).body[0]
        result.append({"control_id": "authored-control:" + name, "source_text": body.decode(),
            "source_sha256": _sha(body), "source_origin": "authored_negative_not_benchmark_source",
            "same_original_44_features_as_positive": found[0]["features"] == reference[0]["features"],
            "original_44_query_cosine": _cosine(found[0]["features"], query44),
            "structured_ast_match": _shape(node), "exact_projection_rejected": rejected,
            "rejection_reason": reason, "training_gradient_used": False, "prover_invoked": False})
    _need(result[0]["same_original_44_features_as_positive"], "literal distractor lost same-count control")
    return result


def evaluate_nominations(*, corpus_manifest: dict, targets: dict, source_records: list[dict],
        learned_reconstructions: list[list[float]], untrained_reconstructions: list[list[float]],
        alignment_projection: dict, learned_latents: list[list[float]] | None = None,
        query_latent: list[float] | None = None) -> dict:
    """Replay source targets and evaluate one fixed held-out query, without fit.

    Caller-supplied learned/untrained arrays must be joined to independently
    recorded checkpoints by the training driver. This consumer validates their
    finite dimensions and exact function population, not optimizer provenance.
    """
    from typed_targets import validate_targets
    from align_projection import validate_alignment_projection
    from ipfs_datasets_py.logic.formalization.autoencoder.security import codebase_autoencoder as baseline

    sources = _sources(source_records)
    validate_targets(corpus_manifest, source_records, expected=targets)
    _need(targets.get("schema") == "terminal-typed-function-count-targets@1", "exact typed target schema required")
    rows, names = targets["rows"], targets["feature_names"]
    _need(type(rows) is list and 0 < len(rows) <= MAX_CANDIDATES, "bounded target rows required")
    query = authored_query_vector(names)
    raw = _vectors([row["features"] for row in rows], len(rows), len(names), "raw typed vectors")
    learned = _vectors(learned_reconstructions, len(rows), len(names), "learned reconstructions")
    untrained = _vectors(untrained_reconstructions, len(rows), len(names), "untrained reconstructions")
    native44, unsupported = baseline._features(sources, sorted(sources), MAX_CANDIDATES)
    _need(not unsupported and len(native44) == len(rows), "complete original 44-feature population required")
    by_id = {row["row_id"]: row for row in native44}
    nodes = _function_nodes(sources)
    _need(len(nodes) == len(rows), "typed rows must account for every source function")
    source = alignment_projection["source"]
    parent = sources.get(source["path"])
    _need(parent is not None and _sha(parent) == source["sha256"], "retained alignment parent source changed")
    validate_alignment_projection(source_bytes=parent, source_path=source["path"],
        source_sha256=source["sha256"], expected=alignment_projection)
    candidates, positives = [], []
    for row in rows:
        identity = row["row_id"]
        base = by_id.get(identity)
        _need(base is not None and base["path"] == row["path"] and base["symbol"] == row["symbol"]
            and base["line"] == row["line"] and base["ast_sha256"] == row["ast_sha256"]
            and base["features"] == row["baseline44_features"], "original source/function/baseline identity differs")
        node = nodes[(row["path"], row["symbol"], row["line"])]
        fragment, start, end = _fragment(sources[row["path"]], node)
        exact = (row["path"] == source["path"] and row["symbol"] == "align"
            and start == source["start_byte"] and end == source["end_byte"]
            and _sha(fragment) == source["function_bytes_sha256"])
        if exact:
            _need(row["split"] == "evaluation" and _shape(node), "exact alignment positive must be held-out evaluation")
            positives.append(identity)
        candidates.append({"candidate_id": identity, "path": row["path"], "symbol": row["symbol"],
            "split": row["split"], "ast_sha256": row["ast_sha256"],
            "source_sha256": _sha(sources[row["path"]]),
            "function_source_sha256": _sha(fragment), "start_byte": start, "end_byte": end,
            "lexical_query_score": _lexical(fragment.decode()), "structured_ast_match": _shape(node),
            "exact_retained_projection_source_match": exact, "behavioral_satisfaction": False})
    _need(len(positives) == 1 and len({row["candidate_id"] for row in candidates}) == len(candidates),
        "one unique exact retained held-out positive required")
    fixed44 = {"FunctionDef": 1, "Name": 8, "Constant": 1, "Return": 1, "BinOp": 4, "argument_count": 2}
    query44 = [math.log1p(fixed44.get(name, 0)) for name in baseline.FEATURES]
    norm = math.sqrt(sum(value * value for value in query44))
    query44 = [value / norm for value in query44]
    controls = _negative_controls(query44)
    positive_ids = set(positives)
    methods = {
        "raw_richer_feature_cosine": _ranking([_cosine(row, query["vector"]) for row in raw], candidates, positive_ids),
        "learned_reconstruction_cosine": _ranking([_cosine(row, query["vector"]) for row in learned], candidates, positive_ids),
        "untrained_reconstruction_cosine": _ranking([_cosine(row, query["vector"]) for row in untrained], candidates, positive_ids),
        "original_44_ast_count_cosine": _ranking([_cosine(row["baseline44_features"], query44) for row in rows], candidates, positive_ids),
        "lexical_token_overlap": _ranking([row["lexical_query_score"] for row in candidates], candidates, positive_ids),
        "structured_ast_graph_matching": _ranking([float(row["structured_ast_match"]) for row in candidates], candidates, positive_ids),
    }
    _need((learned_latents is None) == (query_latent is None), "latent candidates require the same-model authored query latent")
    if learned_latents is not None:
        _need(type(query_latent) is list and 1 <= len(query_latent) <= 64, "bounded authored query latent required")
        latent = _vectors(learned_latents, len(rows), len(query_latent), "learned latents")
        query_latent = _vectors([query_latent], 1, len(query_latent), "query latent")[0]
        methods["learned_latent_cosine"] = _ranking([_cosine(row, query_latent) for row in latent], candidates, positive_ids)
    result = {"schema": SCHEMA, "query": query, "positive_candidate_ids": sorted(positives),
        "positive_label_basis": "exact retained conditional projection parent hash and function byte slice",
        "candidate_count": len(candidates), "candidates": candidates, "methods": methods,
        "negative_controls": controls, "query_count": 1,
        "evaluation_scope": "one authored held-out structural alignment query over the admitted function inventory",
        "rankings_require_independent_exact_source_validation": True,
        "exact_parent_projection_replayed": True, "target_vocabulary_fitted_on_training_only": True,
        "heldout_data_used_for_optimizer_gradients_here": False,
        "model_arrays_supplied_by_caller": True, "optimizer_provenance_verified_here": False,
        "training_executed_here": False, "prover_invoked_here": False, "source_executed_here": False,
        "provider_calls": 0, **_AUTHORITY}
    result["report_sha256"] = _sha(_wire(result))
    _need(len(_wire(result)) <= 16 * 1024 * 1024, "nomination report exceeds finite byte bound")
    return json.loads(_wire(result))


__all__ = ["SCHEMA", "NominationReviewError", "authored_query_vector", "evaluate_nominations"]
