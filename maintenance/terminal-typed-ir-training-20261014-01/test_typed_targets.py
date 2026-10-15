"""Authored structural controls require no scheduler, database or training."""
from copy import deepcopy
import hashlib
import json

import pytest

import typed_targets as subject
from ipfs_datasets_py.logic.software_contracts.content import cid_for_structured
from ipfs_datasets_py.logic.software_contracts.python_frontend import PythonASTExtractor


def fixture(codes=None):
    codes = codes or {
        "train/unit.py": b"def train(x: int):\n    return x + 1\n",
        "validation/unit.py": b"def val(x):\n    return x - 2\n",
        "evaluation/unit.py": b"def evaluate(x):\n    return x * 999\n",
    }
    tree = cid_for_structured({"schema": "authored-test-snapshot@1"})
    tasks, records = [], []
    for path, body in sorted(codes.items()):
        split = path.split("/", 1)[0]
        pin = {"path": path, "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}
        tasks.append({"task_id": split, "split": split, "sources": [pin]})
        ast_record = PythonASTExtractor().extract(body, path=path, repository_id="authored:targets",
            repository_tree_cid=tree, revision="snapshot:" + tree).to_dict()
        records.append({**pin, "source_cid": ast_record["provenance"]["source_cid"],
            "ast_cid": cid_for_structured(ast_record), "parse_status": "ok",
            "ast": ast_record, "source_bytes": body})
    return {"schema": "terminal-codebase-ir-corpus@1", "tasks": tasks}, records


def test_train_only_vocabulary_and_complete_heldout_oov_inventory():
    manifest, records = fixture()
    result = subject.build_targets(manifest, records)
    assert result["split_counts"] == {"train": 1, "validation": 1, "evaluation": 1}
    training = next(row for row in result["rows"] if row["split"] == "train")
    assert set(result["feature_names"]) == set(training["atom_counts"])
    assert 'literals|["int","999"]' not in result["feature_names"]
    evaluation = next(row for row in result["rows"] if row["split"] == "evaluation")
    assert {"atom": 'literals|["int","999"]', "count": 1} in evaluation["unknown_atoms"]
    assert evaluation["unknown_atom_mass"] > 0
    assert len(evaluation["features"]) == result["input_width"]
    assert len(evaluation["baseline44_features"]) == 44
    assert subject.validate_targets(manifest, records, result)["verified"]
    assert all(value is False for value in result["claims"].values())


def test_heldout_mutation_never_changes_vocabulary_or_training_features():
    manifest, records = fixture()
    first = subject.build_targets(manifest, records)
    other_manifest, other_records = fixture({
        "train/unit.py": next(row["source_bytes"] for row in records if row["path"] == "train/unit.py"),
        "validation/unit.py": b"def val(x):\n    return [x for x in range(11)]\n",
        "evaluation/unit.py": b"def evaluate(x):\n    return {'unseen_literal': x / 783}\n",
    })
    changed = subject.build_targets(other_manifest, other_records)
    assert first["feature_names"] == changed["feature_names"]
    assert first["vocabulary_fit_unit_ids"] == changed["vocabulary_fit_unit_ids"]
    assert next(row["features"] for row in first["rows"] if row["split"] == "train") == next(
        row["features"] for row in changed["rows"] if row["split"] == "train")


def test_native_ids_provenance_line_and_path_are_outside_count_vectors():
    manifest, records = fixture({"train/unit.py": b"def renamed(x: int):\n    return x + 1\n"})
    before = subject.build_targets(manifest, records)
    changed = deepcopy(records)
    native = changed[0]["ast"]
    mapping = {}
    for family, idkey in (("symbols", "symbol_id"), ("scopes", "scope_id"),
                          ("calls", "call_id"), ("references", "reference_id"),
                          ("imports", "import_id"), ("effects", "effect_id")):
        for index, row in enumerate(native[family]):
            mapping[row[idkey]] = f"authored:{family}:{index}"
    def replace(value):
        if type(value) is str:
            return mapping.get(value, value)
        if type(value) is list:
            return [replace(item) for item in value]
        if type(value) is dict:
            return {key: replace(item) for key, item in value.items()}
        return value
    changed[0]["ast"] = replace(native)
    changed[0]["ast_cid"] = cid_for_structured(changed[0]["ast"])
    after = subject.build_targets(manifest, changed)
    assert before["feature_names"] == after["feature_names"]
    assert before["rows"][0]["features"] == after["rows"][0]["features"]
    assert before["rows"][0]["native_binding"] != after["rows"][0]["native_binding"]
    moved_manifest, moved_records = fixture({"train/other_name.py": b"\n\ndef renamed(x: int):\n    return x + 1\n"})
    moved = subject.build_targets(moved_manifest, moved_records)
    assert before["feature_names"] == moved["feature_names"]
    assert before["rows"][0]["features"] == moved["rows"][0]["features"]
    assert before["rows"][0]["row_id"] != moved["rows"][0]["row_id"]


def test_ast_field_edges_distinguish_same_kind_histogram_structure():
    first_manifest, first_records = fixture({"train/unit.py": b"def arithmetic():\n    return 1 + (2 * 3)\n"})
    second_manifest, second_records = fixture({"train/unit.py": b"def arithmetic():\n    return (1 + 2) * 3\n"})
    first = subject.build_targets(first_manifest, first_records)["rows"][0]
    second = subject.build_targets(second_manifest, second_records)["rows"][0]
    assert first["baseline44_features"] == second["baseline44_features"]
    assert first["atom_counts"] != second["atom_counts"]
    assert first["typed_target"]["syntax"]["field_edges"] != second["typed_target"]["syntax"]["field_edges"]


def test_literal_types_and_exact_bounded_values_do_not_collapse():
    rows = []
    for value in ("True", "1", "2", "'1'", "1.0"):
        manifest, records = fixture({"train/unit.py": (f"def literal():\n    return {value}\n").encode()})
        rows.append(subject.build_targets(manifest, records)["rows"][0])
    assert len({json.dumps(row["atom_counts"], sort_keys=True) for row in rows}) == 5


def test_unbounded_literal_retained_as_explicit_residual():
    body = b"def literal():\n    return '" + b"x" * 300 + b"'\n"
    manifest, records = fixture({"train/unit.py": body})
    result = subject.build_targets(manifest, records)
    assert result["rows"][0]["typed_target"]["unsupported"][0]["kind"] == "literal_outside_bounded_atom_profile"
    assert not any(name.startswith("literals|") for name in result["feature_names"])


def test_file_scope_native_imports_and_diagnostics_remain_outside_function_counts():
    manifest, records = fixture({"train/unit.py": b"import math\ndef function(x):\n    return math.sqrt(x)\n"})
    result = subject.build_targets(manifest, records)
    assert result["files"][0]["file_scope_residuals"]["imports"]
    assert result["rows"][0]["typed_target"]["native_normalized"]["calls"]
    assert not any("math" in key for key in result["feature_names"])


@pytest.mark.parametrize("damage", ["raw", "native_cid", "source_cid", "native_path", "native_span", "partial"])
def test_source_native_record_or_span_binding_mismatch_refuses(damage):
    manifest, records = fixture()
    if damage == "raw":
        records[0]["source_bytes"] += b"# changed\n"
    elif damage == "native_cid":
        records[0]["ast_cid"] = cid_for_structured({"wrong": True})
    elif damage == "source_cid":
        records[0]["source_cid"] = records[1]["source_cid"]
    elif damage == "native_path":
        records[0]["ast"]["provenance"]["path"] = "wrong.py"
        records[0]["ast_cid"] = cid_for_structured(records[0]["ast"])
    elif damage == "native_span":
        symbol = next(row for row in records[0]["ast"]["symbols"] if row["kind"] == "function")
        symbol["span"]["end_byte"] -= 1
        records[0]["ast_cid"] = cid_for_structured(records[0]["ast"])
    else:
        records[0]["parse_status"] = "partial"
    with pytest.raises(ValueError):
        subject.build_targets(manifest, records)


def test_duplicate_missing_and_crosssplit_ast_leakage_refuse():
    manifest, records = fixture()
    for wrong in (records[:-1], records + [records[0]]):
        with pytest.raises(subject.TypedTargetError):
            subject.build_targets(manifest, wrong)
    duplicate_manifest, duplicate_records = fixture({
        "train/unit.py": b"def copy(x):\n    return x + 1\n",
        "evaluation/unit.py": b"def copy(x):\n    return x + 1\n",
    })
    with pytest.raises(subject.TypedTargetError, match="crosssplit"):
        subject.build_targets(duplicate_manifest, duplicate_records)


def test_exact_replay_refuses_vector_or_oov_corruption():
    manifest, records = fixture()
    result = subject.build_targets(manifest, records)
    changed = deepcopy(result)
    changed["rows"][0]["features"][0] += 0.25
    with pytest.raises(subject.TypedTargetError, match="replay"):
        subject.validate_targets(manifest, records, changed)


def test_explicit_byte_mapping_and_augmented_rows_agree():
    manifest, records = fixture()
    expected = subject.build_targets(manifest, records)
    stripped = [{key: value for key, value in row.items() if key != "source_bytes"} for row in records]
    mapped = {row["path"]: row["source_bytes"] for row in records}
    assert subject.build_targets(manifest, stripped, mapped) == expected
    for block in expected["modality_spans"]:
        for row in expected["rows"]:
            mass = sum(value * value for value in row["features"][block["start"]:block["stop"]])
            assert mass == pytest.approx(0.0) or mass == pytest.approx(1.0)


def test_constructor_and_decorated_method_keep_exact_native_spans():
    manifest, records = fixture({"train/unit.py": b"class Example:\n    def __init__(self, x: int):\n        self.x = x\n    @staticmethod\n    def method(x):\n        return x + 1\n"})
    result = subject.build_targets(manifest, records)
    assert [row["symbol"] for row in result["rows"]] == ["Example.__init__", "Example.method"]
    for row in result["rows"]:
        assert row["native_binding"]["symbol_span"]["start_byte"] == row["start_byte"]
