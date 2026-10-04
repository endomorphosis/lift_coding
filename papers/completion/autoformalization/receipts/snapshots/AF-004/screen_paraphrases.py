#!/usr/bin/env python3
"""Preseal source grouping only; no model fitting, candidate generation, or label access."""
import os
os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", TOKENIZERS_PARALLELISM="false", OMP_NUM_THREADS="2", MKL_NUM_THREADS="2", OPENBLAS_NUM_THREADS="2")
os.umask(0o077)
import collections
import datetime as dt
import hashlib
import json
from pathlib import Path
import resource
import time

import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer
from build_lexical_graph import PRIVATE, STAGE, Union, save, sha


def main():
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    resource.setrlimit(resource.RLIMIT_AS, (16 * 1024**3, 16 * 1024**3))
    graph = json.loads((PRIVATE / "lexical_graph.private.json").read_text())
    assert len(graph["components"]) >= 23, "No need to inspect more source content when lexical graph already cannot support the frozen floor"
    records = graph["records"]
    wanted = {r["record_id"]: i for i, r in enumerate(records)}
    raw = PRIVATE / "raw/patent-legal-corpus-86c77cb6.documents.jsonl"
    assert sha(raw) == graph["source_sha256"]
    texts = [None] * len(records)
    for line in raw.open():
        r = json.loads(line)
        if r["record_id"] in wanted:
            texts[wanted[r["record_id"]]] = r["text"]
    manifest = json.loads((STAGE.parents[1] / "autoformalization/config/environment_manifest.json").read_text())
    def locate(value):
        if isinstance(value, dict):
            if "embedding_producer" in value:
                return value["embedding_producer"]
            for v in value.values():
                found = locate(v)
                if found:
                    return found
        elif isinstance(value, list):
            for v in value:
                found = locate(v)
                if found:
                    return found
    producer = locate(manifest)
    model_dir = Path(producer["model_directory"])
    assert producer["revision"] == "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
    for f in producer["files"]:
        assert sha(model_dir / f["path"]) == f["sha256"]
    tokenizer = AutoTokenizer.from_pretrained(model_dir, local_files_only=True, trust_remote_code=False)
    tokenizer.model_max_length = 10**9  # Full text is explicitly windowed below; no silent prefix truncation.
    model = AutoModel.from_pretrained(model_dir, local_files_only=True, trust_remote_code=False).eval().to("cpu")
    chunks, owners, lengths, starts = [], [], [], []
    for i, text in enumerate(texts):
        ids = tokenizer.encode(text, add_special_tokens=False, truncation=False)
        for start in range(0, len(ids), 240):
            body = ids[start:start + 240]
            chunks.append(tokenizer.build_inputs_with_special_tokens(body))
            owners.append(i)
            lengths.append(len(body))
            starts.append(start)
    del texts
    print(json.dumps({"phase": "tokenized", "documents": len(records), "windows": len(chunks), "all_tokens_covered": sum(lengths), "cpu_threads": torch.get_num_threads(), "memory_limit_bytes": resource.getrlimit(resource.RLIMIT_AS)[0]}), flush=True)
    vectors = []
    started_clock = time.monotonic()
    with torch.inference_mode():
        for start in range(0, len(chunks), 32):
            batch = tokenizer.pad({"input_ids": chunks[start:start + 32]}, padding=True, return_tensors="pt")
            outputs = model(**batch).last_hidden_state
            mask = batch["attention_mask"].unsqueeze(-1)
            embeddings = (outputs * mask).sum(1) / mask.sum(1)
            embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
            vectors.append(embeddings.numpy().copy())
            if start % (32 * 25) == 0:
                print(json.dumps({"phase": "embedding", "windows_completed": min(start + 32, len(chunks)), "elapsed_seconds": round(time.monotonic() - started_clock, 2)}), flush=True)
    vectors = np.concatenate(vectors)
    assert np.isfinite(vectors).all()
    np.savez_compressed(PRIVATE / "grouping_encoder_vectors.private.npz", vectors=vectors, owner=np.array(owners), token_start=np.array(starts), length=np.array(lengths))
    (PRIVATE / "grouping_encoder_vectors.private.npz").chmod(0o600)
    owner = np.array(owners)
    sizes = np.array(lengths)
    lexical = np.array([r["component"] for r in records])[owner]
    union = Union(len(graph["base_group_keys"]))
    for r in records:
        union.merge(r["base_group"], r["component"])
    edges = []
    for start in range(0, len(vectors), 256):
        similarities = vectors[start:start + 256] @ vectors.T
        ii, jj = np.where(similarities >= 0.95)
        for local, j in zip(ii, jj):
            i = start + int(local)
            j = int(j)
            if j <= i or lexical[i] == lexical[j]:
                continue
            if min(sizes[i], sizes[j]) / max(sizes[i], sizes[j]) < 0.5:
                continue
            a, b = int(owner[i]), int(owner[j])
            union.merge(records[a]["base_group"], records[b]["base_group"])
            edges.append({"a": a, "b": b, "a_window_start": starts[i], "b_window_start": starts[j], "cosine": float(similarities[local, j]), "kind": "fixed_encoder_fulltext_window_similarity"})
    for r in records:
        r["component"] = union.find(r["base_group"])
    components = collections.defaultdict(list)
    for i, r in enumerate(records):
        components[r["component"]].append(i)
    graph["components"] = dict(components)
    graph["paraphrase_edges"] = edges
    graph["encoder_vector_sha256"] = sha(PRIVATE / "grouping_encoder_vectors.private.npz")
    save(PRIVATE / "full_graph.private.json", graph)
    report = {
        "schema": "af004-fixed-encoder-grouping-audit/v1",
        "started_at": started,
        "completed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "script_sha256": sha(Path(__file__)),
        "source_sha256": graph["source_sha256"],
        "grouping_plan_sha256": graph["grouping_plan_sha256"],
        "embedding_producer": producer,
        "purpose": "Preseal fixed source-grouping screen only; no semantic labels, source fidelity scoring, compiler targets, model fitting or outcome inspection",
        "eligible_source_records": len(records),
        "fulltext_windows": len(vectors),
        "tokens_covered": sum(lengths),
        "cross_lexical_component_window_edges": len(edges),
        "components_after_full_graph_union": len(components),
        "component_size_histogram": dict(collections.Counter(len(v) for v in components.values())),
        "component_base_group_count_histogram": dict(collections.Counter(len({records[i]["base_group"] for i in v}) for v in components.values())),
        "floor_possible_before_split_assignment": len(components) >= 23 and len(records) >= 103,
        "required_final_test_groups": 20,
        "required_final_test_natural_units": 100,
        "private_graph_sha256": sha(PRIVATE / "full_graph.private.json"),
        "private_encoder_artifact_sha256": graph["encoder_vector_sha256"],
        "source_text_printed": False,
        "labels_read": False,
        "independence_and_screen_limit": "Fixed lexical and pretrained-encoder screens are operational detection tests, not proof that every semantic paraphrase or statistical dependence has been removed. Four macro-editions remain correlated; graph components cannot be relabeled as independently sampled corpora.",
    }
    save(STAGE / "paraphrase_graph_audit.json", report)
    print(json.dumps({k: v for k, v in report.items() if k != "embedding_producer"}, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
