#!/usr/bin/env python3
"""Curatorial metadata/text processing. Print only aggregate counts, never bodies/IDs."""
import collections
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import unicodedata

import numpy as np
from sklearn.feature_extraction.text import CountVectorizer

os.umask(0o077)
STAGE = Path(__file__).resolve().parent
BRIDGE = STAGE.parent / "af004_source_bridge"
PRIVATE = Path.home() / ".local/state/ipfs_accelerate_py/vericodegen-2026/research-inputs/autoformalization/af004-v1"
PLAN = json.loads((STAGE / "grouping_plan.json").read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, data):
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    path.chmod(0o600)


def tokens(text):
    return re.findall(r"[^\W_]+", unicodedata.normalize("NFKC", text).casefold())


def shingles(text):
    ts = tokens(text)
    return (" ".join(ts[i:i + 5]) for i in range(len(ts) - 4))


class Union:
    def __init__(self, n):
        self.parent = list(range(n))

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def merge(self, x, y):
        x, y = self.find(x), self.find(y)
        if x != y:
            self.parent[max(x, y)] = min(x, y)


def base_key(row):
    m = row.get("metadata", {})
    structure = m.get("part") if row["family"] == "cfr" else m.get("chapter_id") if row["family"] == "mpep" else "whole-edition"
    if structure is None:
        structure = "whole-edition"
    return (row["source_root_id"], row["current_through"], str(structure))


def main():
    start = dt.datetime.now(dt.timezone.utc).isoformat()
    PRIVATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    for p in [PRIVATE, PRIVATE.parent]:
        p.chmod(0o700)
    frozen = PRIVATE / "raw"
    frozen.mkdir(mode=0o700, exist_ok=True)
    src = BRIDGE / "patent-legal-corpus-86c77cb6.documents.jsonl"
    assert sha(src) == PLAN["source_sha256"]
    for name in [src.name, "patent-legal-corpus-86c77cb6.README.md", "patent-legal-corpus-86c77cb6.coverage.json", "bridge_manifest.json"]:
        dest = frozen / name
        if dest.exists():
            assert sha(dest) == sha(BRIDGE / name), "Refuse to replace changed frozen source"
        else:
            shutil.copyfile(BRIDGE / name, dest)
        dest.chmod(0o600)
    rows = [json.loads(line) for line in (frozen / src.name).open()]
    eligible, exclusions = [], []
    for row in rows:
        reasons = []
        rights = row.get("rights_review", {})
        if not row.get("text", "").strip():
            reasons.append("empty_text")
        if row.get("metadata", {}).get("reserved") is True:
            reasons.append("reserved_section")
        if rights.get("review_status") != "reviewed" or rights.get("redistribution_allowed") is not True:
            reasons.append("rights_not_qualified")
        if row.get("ai_derived"):
            reasons.append("nonempty_ai_derived_payload")
        if row.get("classification") != "public_official":
            reasons.append("not_official_natural_source")
        if reasons:
            exclusions.append({"record_id": row["record_id"], "family": row["family"], "reasons": reasons})
        else:
            eligible.append(row)
    keys = sorted({base_key(r) for r in eligible})
    key_index = {k: i for i, k in enumerate(keys)}
    group = [key_index[base_key(r)] for r in eligible]
    union = Union(len(keys))
    edges = []
    identity_maps = collections.defaultdict(dict)
    for i, row in enumerate(eligible):
        lineage = row.get("source_lineage", {})
        identities = {
            "source_uri": lineage.get("source_uri"),
            "source_sha256": lineage.get("source_sha256"),
            "normalized_fulltext": hashlib.sha256(" ".join(tokens(row["text"])).encode()).hexdigest(),
        }
        for kind, value in identities.items():
            if not value:
                continue
            previous = identity_maps[kind].setdefault(value, i)
            if previous != i and group[i] != group[previous]:
                union.merge(group[i], group[previous])
                edges.append({"a": i, "b": previous, "kind": kind})
    print(json.dumps({"phase": "identity", "input_records": len(rows), "eligible_records": len(eligible), "excluded_records": len(exclusions), "base_groups": len(keys), "components": len({union.find(g) for g in group})}), flush=True)
    vectorizer = CountVectorizer(analyzer=shingles, binary=True, dtype=np.int32)
    x = vectorizer.fit_transform(r["text"] for r in eligible)
    sizes = np.asarray(x.sum(axis=1)).ravel()
    intersections = (x @ x.T).tocoo()
    comparisons = 0
    for i, j, intersection in zip(intersections.row, intersections.col, intersections.data):
        i, j, intersection = int(i), int(j), int(intersection)
        if j <= i or group[i] == group[j]:
            continue
        comparisons += 1
        smaller = min(int(sizes[i]), int(sizes[j]))
        if smaller < 40 or intersection < 40:
            continue
        containment = intersection / smaller
        jaccard = intersection / (int(sizes[i]) + int(sizes[j]) - intersection)
        if containment >= 0.8 or jaccard >= 0.8:
            union.merge(group[i], group[j])
            edges.append({"a": i, "b": j, "kind": "five_token_shingle_overlap", "shared": intersection, "containment": containment, "jaccard": jaccard})
    components = collections.defaultdict(list)
    for i, g in enumerate(group):
        components[union.find(g)].append(i)
    private_graph = {
        "source_sha256": PLAN["source_sha256"],
        "grouping_plan_sha256": sha(STAGE / "grouping_plan.json"),
        "base_group_keys": keys,
        "records": [{"record_id": r["record_id"], "base_group": group[i], "component": union.find(group[i]), "family": r["family"], "current_through": r["current_through"]} for i, r in enumerate(eligible)],
        "excluded": exclusions,
        "edges": edges,
        "components": dict(components),
    }
    save(PRIVATE / "lexical_graph.private.json", private_graph)
    summary = {
        "schema": "af004-lexical-graph-audit/v1",
        "started_at": start,
        "completed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source_sha256": PLAN["source_sha256"],
        "grouping_plan_sha256": sha(STAGE / "grouping_plan.json"),
        "builder_sha256": sha(Path(__file__)),
        "input_records": len(rows),
        "eligible_natural_source_records": len(eligible),
        "excluded_records": len(exclusions),
        "exclusion_reason_counts": dict(collections.Counter(reason for row in exclusions for reason in row["reasons"])),
        "eligible_domain_counts": dict(collections.Counter(r["family"] for r in eligible)),
        "base_structural_groups": len(keys),
        "macro_source_editions": len({r["source_root_id"] for r in eligible}),
        "unique_shingles": x.shape[1],
        "all_document_pairs": len(eligible) * (len(eligible) - 1) // 2,
        "cross_group_pairs_with_nonzero_overlap": comparisons,
        "cross_group_edge_counts": dict(collections.Counter(e["kind"] for e in edges)),
        "connected_components_after_identity_and_lexical_union": len(components),
        "component_size_histogram": dict(collections.Counter(len(v) for v in components.values())),
        "component_base_group_count_histogram": dict(collections.Counter(len({group[i] for i in v}) for v in components.values())),
        "maximum_possible_final_test_groups_before_development_reservation": len(components),
        "required_final_test_groups": 20,
        "required_final_test_natural_units": 100,
        "floor_possible_after_lexical_graph": len(components) >= 23 and len(eligible) >= 103,
        "partition_assignment_status": "not_assigned_pending_full_grouping_and_access_enforcement",
        "private_graph_sha256": sha(PRIVATE / "lexical_graph.private.json"),
        "private_graph_location": "Owner-only research-inputs/autoformalization/af004-v1; no membership or source IDs published in this report",
        "paraphrase_screen_status": "pending_if_floor_possible; additional unions cannot increase component count",
        "semantic_labels_read": False,
        "body_text_printed": False,
        "independence_claim": "Structural connected components remain candidates; four macro-editions share legal domain and temporal provenance. This audit does not prove statistical independence.",
    }
    save(STAGE / "lexical_graph_audit.json", summary)
    print(json.dumps(summary, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
