#!/usr/bin/env python3
"""Validate AF-017 retrieval artifacts against the task acceptance criteria."""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parents[2]
REPO_ROOT = PAPER_ROOT.parents[2]


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path):
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line:
            rows.append(json.loads(line))
    return rows


def main() -> int:
    judgments_path = PAPER_ROOT / "data" / "retrieval_judgments.jsonl"
    retrieval_path = PAPER_ROOT / "runs" / "retrieval" / "results.jsonl"
    premise_path = PAPER_ROOT / "runs" / "premise_selection" / "results.jsonl"
    manifest_path = PAPER_ROOT / "config" / "retrieval_manifest.json"
    judgments = load_jsonl(judgments_path)
    retrieval = load_jsonl(retrieval_path)
    premises = load_jsonl(premise_path)
    manifest = load_json(manifest_path)

    errors = []
    n_docs = manifest["corpus"]["n_documents"]
    n_queries = manifest["queries"]["n_queries"]
    n_goals = manifest["queries"]["n_premise_goals"]
    doc_ids = set(manifest["corpus"]["document_ids"])
    query_ids = set(manifest["queries"]["query_ids"])
    premise_goal_ids = {qid for qid in query_ids if qid.startswith("g.")}
    if n_docs != 34 or n_queries != 12 or n_goals != 5:
        errors.append(f"unexpected pool counts docs={n_docs} queries={n_queries} goals={n_goals}")
    if len(doc_ids) != n_docs or len(query_ids) != n_queries:
        errors.append("manifest document/query id lists disagree with counts")

    coverage = {}
    by_task = defaultdict(list)
    for row in judgments:
        if row.get("schema") != "autoformalization-retrieval-judgment/v1":
            errors.append(f"bad judgment schema {row.get('label_task')}")
            continue
        task = row.get("label_task")
        if row.get("kind") == "coverage":
            coverage[task] = row
            continue
        by_task[task].append(row)

    expected_pairs = {
        "relevance": n_docs * n_queries,
        "admitted_premise_usefulness": n_docs * n_queries,
        "proxy_import_overlap": n_docs * n_goals,
    }
    families = {
        "relevance": "citation_and_controlling_source/v1",
        "admitted_premise_usefulness": "explicit_dependency_or_admission/v1",
        "proxy_import_overlap": "shared_import_proximity_proxy/v1",
    }
    for task, n_pairs in expected_pairs.items():
        cov = coverage.get(task)
        if not cov:
            errors.append(f"missing coverage row for {task}")
            continue
        if cov.get("n_pairs") != n_pairs:
            errors.append(f"{task} coverage n_pairs {cov.get('n_pairs')} != {n_pairs}")
        if cov.get("n_documents") != n_docs:
            errors.append(f"{task} coverage n_documents mismatch")
        if not cov.get("implicit_negatives") or not cov.get("full_corpus_query_product"):
            errors.append(f"{task} coverage does not assert a full corpus/query product")
        if cov["provenance"]["family"] != families[task]:
            errors.append(f"{task} coverage provenance family mismatch")
        if task != "proxy_import_overlap" and not cov["provenance"]["independent_of_retrieval_scores"]:
            errors.append(f"{task} coverage not independent of retrieval scores")
        if task != "proxy_import_overlap" and not cov["provenance"]["independent_of_other_label_task"]:
            errors.append(f"{task} coverage not independent of the other primary label task")
        if task == "proxy_import_overlap" and not cov["provenance"]["derived_from_import_overlap"]:
            errors.append("proxy coverage must be labeled as import-overlap derived")
        positives = []
        allowed_queries = premise_goal_ids if task == "proxy_import_overlap" else query_ids
        for row in by_task[task]:
            if row.get("label") != 1:
                errors.append(f"{task} compact qrels may list only positives")
                break
            pair = (row["query_id"], row["document_id"])
            positives.append(pair)
            if row["query_id"] not in allowed_queries or row["document_id"] not in doc_ids:
                errors.append(f"{task} positive outside the frozen pool: {pair}")
            if row["provenance"]["family"] != families[task]:
                errors.append(f"{task} provenance family mismatch")
                break
            if task != "proxy_import_overlap" and not row["provenance"]["independent_of_retrieval_scores"]:
                errors.append(f"{task} not independent of retrieval scores")
            if task != "proxy_import_overlap" and not row["provenance"]["independent_of_other_label_task"]:
                errors.append(f"{task} not independent of the other primary label task")
            if task == "proxy_import_overlap" and not row["provenance"]["derived_from_import_overlap"]:
                errors.append("proxy rows must be labeled as import-overlap derived")
        if len(set(positives)) != len(positives):
            errors.append(f"{task} has duplicate positives")
        if cov.get("n_positives") != len(set(positives)):
            errors.append(f"{task} n_positives {cov.get('n_positives')} != {len(set(positives))}")

    rel_pos = {(r["query_id"], r["document_id"]) for r in by_task["relevance"] if r.get("label") == 1}
    use_pos = {(r["query_id"], r["document_id"]) for r in by_task["admitted_premise_usefulness"] if r.get("label") == 1}
    if not rel_pos or not use_pos:
        errors.append("missing positive labels")
    if rel_pos == use_pos:
        errors.append("relevance and usefulness positive sets are identical")
    if manifest.get("judgments", {}).get("n_relevance_pairs") != n_docs * n_queries:
        errors.append("manifest relevance pair count is not the full corpus/query product")
    if manifest.get("judgments", {}).get("n_usefulness_pairs") != n_docs * n_queries:
        errors.append("manifest usefulness pair count is not the full corpus/query product")

    vector_rows = [row for row in retrieval if row.get("route_id") == "vector_exact_ip"]
    if not vector_rows:
        errors.append("no measured vector route rows")
    for row in vector_rows:
        if row.get("mock_vectors") or row.get("declared_only_cli"):
            errors.append("vector row marked mock or declared-only CLI")
        if row.get("vector_backend") != "stdlib-exact-inner-product/v1":
            errors.append("vector backend identity missing")
        if row.get("execution_status") != "measured":
            errors.append("vector route not measured")
        scores = [hit["score"] for hit in row.get("ranked") or []]
        if len(set(round(score, 6) for score in scores)) <= 1:
            errors.append("vector scores are constant; mock ranks are forbidden")
        if any(hit["score"] == 1.0 and hit["rank"] != 1 for hit in row.get("ranked") or []):
            pass

    routes = {row.get("route_id") for row in retrieval if row.get("route_id")}
    if routes != {"lexical_bm25", "vector_exact_ip", "graph_walk", "combined_rrf"}:
        errors.append(f"unexpected routes {routes}")
    for row in retrieval:
        if row.get("kind") == "summary":
            continue
        if row.get("corpus_n_documents") != n_docs or row.get("query_n") != n_queries:
            errors.append(f"retrieval row missing full corpus/query counts: {row.get('record_id')}")
            break

    if manifest["routes"]["vector_exact_ip"]["mock_vectors"]:
        errors.append("manifest claims mock vectors")
    if manifest["routes"]["vector_exact_ip"]["declared_only_cli"]:
        errors.append("manifest claims declared-only CLI vector search")
    if manifest["routes"]["vector_exact_ip"]["faiss_library"]["available"]:
        errors.append("manifest claims FAISS available under sealed PATH")
    if "No FAISS-library" not in " ".join(manifest["unavailable_conditions"]["claim_narrowing"]):
        errors.append("FAISS unavailability does not narrow associated claims")

    selectors = {row.get("selector_id") for row in premises if row.get("selector_id")}
    if selectors != {"deterministic_baseline", "hand_authored_graph_selector"}:
        errors.append(f"unexpected selectors {selectors}")
    for row in premises:
        if row.get("kind") == "summary":
            if not row.get("hand_authored_weights_disclosed") or not row.get("proxy_labels_disclosed"):
                errors.append("summary does not disclose hand-authored weights or proxy labels")
            if row.get("trained_selector_claimed"):
                errors.append("trained selector claimed without a train/split artifact")
            continue
        if row.get("selector_id") == "hand_authored_graph_selector":
            weights = row["weights"]
            if weights.get("trained") or weights.get("independent_train_split") is not None:
                errors.append("graph selector claimed as trained")
            if "hand_authored" not in weights.get("provenance", ""):
                errors.append("graph selector provenance missing hand-authored disclosure")
            if not weights.get("model_digest", "").startswith("sha256:"):
                errors.append("graph selector digest missing")
        if "proxy_import_overlap" not in row.get("label_tasks", {}):
            errors.append("premise row missing proxy label task")
        if "admitted_premise_usefulness" not in row.get("label_tasks", {}):
            errors.append("premise row missing usefulness label task")
        if row.get("corpus_n_documents") != 20 or row.get("query_n") != n_goals:
            errors.append(f"premise row missing full theorem-pool/query counts: {row.get('record_id')}")

    if manifest["selectors"]["hand_authored_graph_selector"]["trained"]:
        errors.append("manifest trained flag true")
    if manifest["judgments"]["human_adjudication"]:
        errors.append("human adjudication claimed")
    if manifest["eligible_natural_held_out"]:
        errors.append("natural held-out eligibility claimed")
    if manifest["unavailable_conditions"]["natural_legal_corpus_retrieval"]["natural_source_units"]["final_test"] != 1913:
        errors.append("upstream final-test unit count missing from unavailable record")

    print(json.dumps({
        "ok": not errors,
        "n_judgments": len(judgments),
        "n_relevance_pairs": expected_pairs["relevance"],
        "n_usefulness_pairs": expected_pairs["admitted_premise_usefulness"],
        "n_proxy_pairs": expected_pairs["proxy_import_overlap"],
        "n_retrieval": len(retrieval),
        "n_premise": len(premises),
        "n_documents": n_docs,
        "n_queries": n_queries,
        "relevance_positives": len(rel_pos),
        "usefulness_positives": len(use_pos),
        "vector_rows": len(vector_rows),
        "errors": errors,
        "paths": {
            "judgments": str(judgments_path.relative_to(REPO_ROOT)),
            "retrieval": str(retrieval_path.relative_to(REPO_ROOT)),
            "premise": str(premise_path.relative_to(REPO_ROOT)),
            "manifest": str(manifest_path.relative_to(REPO_ROOT)),
        },
    }, indent=2, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
