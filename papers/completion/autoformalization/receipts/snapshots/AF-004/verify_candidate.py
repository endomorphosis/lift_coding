#!/usr/bin/env python3
"""Independent staged-file checks, including malicious final-ID disclosure rejection."""
import collections
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

from build_lexical_graph import PRIVATE, STAGE, save, sha, tokens
from data_admission import admit, scan_sources

PREFIX = Path("papers/completion/autoformalization")


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for k, v in value.items():
            yield k
            yield from strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from strings(v)


def verify(root):
    private = json.loads((PRIVATE / "partitions.private.json").read_text())
    graph = json.loads((PRIVATE / "full_graph.private.json").read_text())
    membership = private["membership"]
    final_ids = {r["record_id"] for r in membership["final_test"]}
    for path in (root / PREFIX).rglob("*"):
        if not path.is_file():
            continue
        if path.suffix == ".json":
            values = set(strings(json.loads(path.read_text())))
            assert not values & final_ids, "private final IDs disclosed in public artifact"
        elif path.suffix == ".jsonl":
            for line in path.open():
                assert not set(strings(json.loads(line))) & final_ids, "private final IDs disclosed in public artifact"
        else:
            payload = path.read_bytes()
            assert not any(x.encode() in payload for x in final_ids), "private final IDs disclosed in public artifact"
    split = json.loads((root / PREFIX / "data/splits.json").read_text())
    corpus = json.loads((root / PREFIX / "data/corpus_manifest.json").read_text())
    audit = json.loads((root / PREFIX / "evidence/split_audit.json").read_text())
    assert split["partition_membership_commitment_sha256"] == sha(PRIVATE / "partitions.private.json")
    for name, members in membership.items():
        counts = split["counts"][name]
        assert counts["natural_source_units"] == len({r["normalized_source_unit_sha256"] for r in members})
        assert counts["natural_source_records"] == len(members)
        assert counts["operational_connected_components"] == len({r["component"] for r in members})
        assert counts["by_domain_record_counts"] == dict(collections.Counter(r["family"] for r in members))
        assert corpus["counts_by_split"][name] == counts
        if not private["floor_possible"]:
            assert not members and not split["exports"]
            continue
        export = split["exports"][name]
        path = PRIVATE / "final_test.private.jsonl" if name == "final_test" else root / export["path"]
        assert path.is_file() and not path.is_symlink()
        assert sha(path) == export["sha256"] and path.stat().st_size == export["bytes"]
        rows = [json.loads(line) for line in path.open()]
        assert {r["record_id"] for r in rows} == {r["record_id"] for r in members}
        assert len(rows) == len(members)
        actual_units = {hashlib.sha256(" ".join(tokens(r["text"])).encode()).hexdigest() for r in rows}
        assert actual_units == {r["normalized_source_unit_sha256"] for r in members}
        assert all(not r.get("ai_derived") for r in rows)
        assert all(r["rights_review"]["redistribution_allowed"] is True for r in rows)
        assert all(r["metadata"].get("reserved") is not True for r in rows)
    assignments = {r["record_id"]: name for name, rows in membership.items() for r in rows}
    assert len(assignments) == sum(len(rows) for rows in membership.values())
    groups = collections.defaultdict(set)
    for r in graph["records"]:
        if r["record_id"] in assignments:
            groups[r["base_group"]].add(assignments[r["record_id"]])
    assert all(len(v) == 1 for v in groups.values())
    for e in graph["edges"] + graph.get("paraphrase_edges", []):
        a, b = (graph["records"][e[x]]["record_id"] for x in ["a", "b"])
        assert assignments.get(a) == assignments.get(b)
    if private["floor_possible"]:
        assert len({r["normalized_source_unit_sha256"] for r in membership["final_test"]}) >= 100
        assert len({r["component"] for r in membership["final_test"]}) >= 20
        assert all(membership.values())
    else:
        assert corpus["status"] == "incomplete_frozen_population_floor_unsatisfied", "unmet frozen floor mislabeled complete"
    assert audit["checks"]["scoped_provider_mount_deny_test"] == "pending_root_harness_enforcement"
    assert not (root / PREFIX / "receipts/AF-004.json").exists(), "Do not manufacture a completed receipt while isolation review remains pending"
    return {"passed": True, "private_final_identifiers_disclosed": False, "observed_cross_partition_graph_edges": 0, "actual_population_floor_passes": private["floor_possible"], "split_export_membership_and_hashes_exact": True, "scope": "Staged files only; does not exercise provider mounts, network denial, human annotation, or validate statistical independence"}


def main():
    root = STAGE / "candidate"
    result = verify(root)
    private = json.loads((PRIVATE / "partitions.private.json").read_text())
    members = private["membership"]["final_test"]
    if members:
        split_path = root / PREFIX / "data/splits.json"
        splits = json.loads(split_path.read_text())
        deny_path = PRIVATE / "holdout_deny_index.private.json"
        result["trusted_input_admission_checks"] = [admit(root, role, root / splits["exports"][split]["path"], deny_path, sha(split_path)) for role, split in [("training", "train"), ("model_selection", "selection"), ("fixed_canary", "fixed_canary")]]
        deny = json.loads(deny_path.read_text())
        try:
            scan_sources(PRIVATE / "final_test.private.jsonl", deny)
        except ValueError as error:
            assert "private final-test source" in str(error)
            result["negative_actual_final_source_admission_rejected"] = True
        else:
            raise AssertionError("Admission filter accepted actual final-test input")
        try:
            admit(root, "training", root / splits["exports"]["selection"]["path"], deny_path, sha(split_path))
        except ValueError as error:
            assert "not admitted for declared role" in str(error)
            result["negative_selection_as_training_rejected"] = True
        else:
            raise AssertionError("Admission filter accepted selection input for training")
    with tempfile.TemporaryDirectory(prefix="af004-disclosure-negative-") as temp:
        bad = Path(temp)
        shutil.copytree(root / PREFIX, bad / PREFIX)
        target = bad / PREFIX / "data/corpus_manifest.json"
        payload = json.loads(target.read_text())
        if members:
            payload["hidden_final_id"] = members[0]["record_id"]
            expected = "private final IDs disclosed"
        else:
            payload["status"] = "completed"
            expected = "unmet frozen floor mislabeled complete"
        target.write_text(json.dumps(payload))
        try:
            verify(bad)
        except AssertionError as error:
            assert expected in str(error)
            result["negative_final_id_disclosure_rejected" if members else "negative_false_floor_completion_rejected"] = True
        else:
            raise AssertionError("Verifier accepted deliberate invalid scientific/privacy state")
    result["verifier_sha256"] = sha(Path(__file__))
    save(STAGE / "candidate_verification.json", result)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
