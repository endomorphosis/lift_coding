"""Genuine native compiler controls over exclusively authored source contexts."""
from copy import deepcopy
import json

import pytest

import capsule_codec
from capsule_io import FALSE, sha
import context_projection as subject
from token_cost_review import evaluate_token_costs, load_tokenizer, serialize_messages
from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead
from ipfs_datasets_py.logic.software_contracts.content import cid_for_bytes, cid_for_structured
from ipfs_accelerate_py.agent_supervisor.context.context_compiler import RequiredContextOverflowError


def _head():
    snapshot = cid_for_structured({"schema": "authored-context-snapshot@1"})
    return CodebaseHead(repository_id="authored:source-complete-context", generation=1,
        manifest_cid=cid_for_structured({"schema": "authored-context-manifest@1"}), snapshot_cid=snapshot,
        ast_revision_id="rev:authored:source-complete-context:snapshot:" + snapshot,
        receipt_cid=cid_for_structured({"schema": "authored-context-receipt@1"})).to_dict()


@pytest.fixture(scope="module")
def fixture_data():
    tokenizer, _ = load_tokenizer()
    instruction = '  Preserve the complete original behavior: α 東京 🦆.\nKeep this trailing blank line.\n\n'.encode()
    bodies = {
        "authored-task/environment/first.py": (b"def repeated_identifier(long_parameter: int) -> int:\n    # " +
            b"ordinary explanatory padding " * 40 + b"\n    return long_parameter + long_parameter\n"),
        "authored-task/environment/second.py": 'def unicode_function(long_parameter):\n    text = "é 雪"\n    return long_parameter + long_parameter\n'.encode(),
    }
    head = _head()
    sources, codecs, pins = {}, {}, []
    for path, body in sorted(bodies.items()):
        source_cid = cid_for_bytes(body)
        pins.append({"path": path, "bytes": len(body), "sha256": sha(body)})
        sources[path] = {"path": path, "source_text": body.decode(), "source_cid": source_cid, "head": deepcopy(head)}
        codecs[path] = {"minified": capsule_codec.build_capsule_codec(body, path, source_cid, head),
                        "aliased": capsule_codec.build_capsule_codec(body, path, source_cid, head, aliases=True)}
    return {"task": {"task_id": "authored-task", "sources": pins,
              "instruction": {"path": "authored-task/instruction.md", "bytes": len(instruction), "sha256": sha(instruction)}},
            "instruction": instruction, "head": head, "source_rows": sources, "codec_rows": codecs,
            "capsule_summaries": [], "tokenizer": tokenizer}


def compile_arm(fixture_data, arm="raw", **changes):
    return subject.compile_task_context(**dict(fixture_data, arm=arm, **changes))


@pytest.mark.parametrize("arm", subject.ARMS)
def test_native_compiler_preserves_full_unicode_instruction_and_all_required_source_views(fixture_data, arm):
    projected = compile_arm(fixture_data, arm)
    core = json.loads(projected["rendered"])
    original = fixture_data["instruction"]
    assert json.loads(core["goal"]["instruction_json"])["instruction"].encode() == original
    assert core["acceptance"]["requirement_residual_spans"] == [[0, len(original)]]
    assert core["goal"]["instruction_sha256"] == sha(original)
    assert core["scope"]["source_paths"] == sorted(fixture_data["source_rows"])
    assert core["scope"]["raw_source_required_before_edit"] is True
    assert core["scope"]["all_instruction_requirements_unresolved"] is True
    evidence = core["evidence"]
    assert len(evidence) == len(fixture_data["source_rows"]) + 1
    assert projected["native_capsule"]["expansion_references"] == []
    assert "expansion_references" not in core
    source_refs = [row for row in evidence if row["kind"] == "source-view"]
    assert {row["path"] for row in source_refs} == set(fixture_data["source_rows"])
    for row in source_refs:
        assert row["tier"] == "invariant" and row["metadata"]["required"] is True
        assert row["referenced_content_id"] == fixture_data["source_rows"][row["path"]]["source_cid"]
        assert json.loads(row["summary"]) == projected["source_views"][row["path"]]
        assert row["byte_count"] == len(row["summary"].encode())
    assert projected["rendered_local_bpe_tokens"] == len(fixture_data["tokenizer"].encode(projected["rendered"]))
    assert projected["native_reserved_input_tokens"] == projected["native_capsule"]["input_tokens"]
    assert projected["rendered_local_bpe_tokens"] <= projected["native_reserved_input_tokens"] <= 20000
    assert projected["all_instruction_bytes_preserved"]
    assert projected["all_source_syntax_present_as_display"]
    assert projected["requirement_coverage_qualified"] is False
    assert all(projected[key] is False for key in FALSE)


def test_raw_minified_and_aliased_display_restore_exact_original_without_runtime_claim(fixture_data):
    projected = {arm: compile_arm(fixture_data, arm) for arm in subject.ARMS}
    assert any(codec["minified"]["view_text"] != fixture_data["source_rows"][path]["source_text"]
               for path, codec in fixture_data["codec_rows"].items())
    for path, source in fixture_data["source_rows"].items():
        raw = source["source_text"].encode()
        assert projected["raw"]["source_views"][path]["view_text"].encode() == raw
        for arm in ("minified", "aliased"):
            view = projected[arm]["source_views"][path]
            codec = fixture_data["codec_rows"][path][arm]
            assert view["view_text"] == codec["view_text"]
            assert view["runtime_equivalence_claimed"] is False
            assert view["raw_source_required_before_edit"] is True
            assert capsule_codec.expand_capsule_codec(codec, fixture_data["head"], sha(raw),
                source["source_cid"], expected_path=path) == raw
            if arm == "aliased":
                assert view["alias_dictionary"] == codec["expansion_sidecar"]["aliases"]["dictionary"]
                assert "never execute" in view["alias_guidance"]
                assert view["alias_dictionary"]


@pytest.mark.parametrize("damage", ["instruction_hash", "instruction_length", "source_hash", "source_length",
    "source_path", "source_cid", "source_head", "missing_source", "extra_source", "missing_codec", "codec_path", "codec_source_hash",
    "codec_source_cid", "codec_view", "codec_head", "codec_wrong_mode", "codec_fragment"])
def test_missing_or_changed_task_source_or_codec_identity_refused(fixture_data, damage):
    changed = {key: deepcopy(value) for key, value in fixture_data.items() if key != "tokenizer"}
    changed["tokenizer"] = fixture_data["tokenizer"]
    path = next(iter(changed["source_rows"]))
    if damage == "instruction_hash":
        changed["task"]["instruction"]["sha256"] = "0" * 64
    elif damage == "instruction_length":
        changed["task"]["instruction"]["bytes"] -= 1
    elif damage == "source_hash":
        changed["task"]["sources"][0]["sha256"] = "0" * 64
    elif damage == "source_length":
        changed["task"]["sources"][0]["bytes"] -= 1
    elif damage == "source_path":
        changed["source_rows"][path]["path"] = "wrong/path.py"
    elif damage == "source_cid":
        changed["source_rows"][path]["source_cid"] = cid_for_bytes(b"authored different source")
    elif damage == "source_head":
        changed["source_rows"][path]["head"]["generation"] += 1
    elif damage == "missing_source":
        changed["source_rows"].pop(path)
    elif damage == "extra_source":
        changed["source_rows"]["unexpected.py"] = changed["source_rows"][path]
    elif damage == "missing_codec":
        changed["codec_rows"].pop(path)
    elif damage == "codec_wrong_mode":
        changed["codec_rows"][path]["aliased"] = deepcopy(changed["codec_rows"][path]["minified"])
    elif damage == "codec_fragment":
        source = changed["source_rows"][path]
        raw = source["source_text"].encode()
        changed["codec_rows"][path]["aliased"] = capsule_codec.build_capsule_codec(raw, path,
            source["source_cid"], changed["head"], aliases=True, span={"start_byte": 0, "end_byte": len(raw) - 1})
    else:
        for arm in ("minified", "aliased"):
            codec = changed["codec_rows"][path][arm]
            if damage == "codec_path":
                codec["bindings"]["path"] = "wrong/path.py"
            elif damage == "codec_source_hash":
                codec["bindings"]["source_sha256"] = "0" * 64
            elif damage == "codec_source_cid":
                codec["bindings"]["source_cid"] = cid_for_bytes(b"wrong")
            elif damage == "codec_view":
                codec["view_text"] = "MISSING ALL SOURCE SYNTAX"
            else:
                codec["bindings"]["head"]["generation"] += 1
    with pytest.raises(ValueError):
        compile_arm(changed, "aliased")


@pytest.mark.parametrize("arm", subject.ARMS)
def test_required_context_budget_overflow_refuses_without_silent_source_omission(fixture_data, arm):
    with pytest.raises(RequiredContextOverflowError):
        compile_arm(fixture_data, arm, budget_tokens=64)


def test_three_genuine_native_context_outputs_join_full_message_and_history_costs(fixture_data):
    _, descriptor = load_tokenizer()
    scenarios = {}
    for arm in subject.ARMS:
        core = compile_arm(fixture_data, arm)
        first = dict(serialize_messages([
            {"role": "system", "content": "Authored planning policy.", "partition": "setup", "message_id": "policy"},
            {"role": "user", "content": core["rendered"], "partition": "retrieval", "message_id": "context"}]),
            event_id="turn1", kind="input")
        second = dict(serialize_messages([
            {"role": "system", "content": "Authored planning policy.", "partition": "history", "message_id": "policy"},
            {"role": "user", "content": core["rendered"], "partition": "history", "message_id": "context"},
            {"role": "tool", "content": fixture_data["source_rows"][next(iter(fixture_data["source_rows"]))]["source_text"],
             "partition": "expansion"}]), event_id="turn2", kind="input", required_history_ids=["policy", "context"])
        scenarios[arm] = [first, second]
    for arm in ("minified", "aliased"):
        comparison = evaluate_token_costs(scenarios["raw"], scenarios[arm], descriptor)
        for name, events in (("baseline", scenarios["raw"]), ("compact", scenarios[arm])):
            assert comparison[name]["totals"]["input_tokens"] == sum(len(fixture_data["tokenizer"].encode(row["payload"])) for row in events)
            assert sum(row["tokens"] for row in comparison[name]["partition_totals"].values()) == comparison[name]["totals"]["total_tokens"]
            assert comparison[name]["partition_totals"]["history"]["tokens"] > 0
            assert comparison[name]["partition_totals"]["expansion"]["tokens"] > 0
        assert comparison["provider_usage"] is None
        assert comparison["provider_token_savings"] is None
