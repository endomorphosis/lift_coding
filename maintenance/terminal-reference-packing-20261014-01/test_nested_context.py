"""Pure public-context round trips and authored data corruption controls.

The one selected predecessor artifact is public context-costs.json. These tests
do not open a predecessor database/CAS, observe an owner, run source, train a
model, prove source behavior, call a provider, or assert benchmark satisfaction.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

import nested_context as subject

PUBLIC = Path("/home/barberb/lift_coding/maintenance/terminal-source-capsules-20261014-01/experiment-04/context-costs.json")
PUBLIC_BYTES = 8_610_140
PUBLIC_SHA256 = "2a8e0190dea5904b7d605203996db545dece099854d3a4946b33c8758befd4fb"


def wire(value, ascii=False):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=ascii, allow_nan=False)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


@pytest.fixture(scope="module")
def public_projections():
    before = PUBLIC.stat()
    assert PUBLIC.resolve(strict=True) == PUBLIC and PUBLIC.is_file() and before.st_nlink == 1
    assert before.st_size == PUBLIC_BYTES
    raw = PUBLIC.read_bytes()
    after = PUBLIC.stat()
    witness = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns)
    assert witness(before) == witness(after) and len(raw) == PUBLIC_BYTES and sha(raw) == PUBLIC_SHA256
    data = json.loads(raw)
    return {task["task_id"]: task["projections"] for task in data["tasks"]}


@pytest.fixture
def original(public_projections):
    return public_projections["headless-terminal"]["raw"]["rendered"]


@pytest.mark.parametrize("task", ["headless-terminal", "llm-inference-batching-scheduler",
                                  "feal-differential-cryptanalysis", "break-filter-js-from-html"])
def test_real_public_native_raw_context_restores_byte_exact(public_projections, task):
    # Task spellings come from the pinned public artifact, not invented labels.
    if task not in public_projections:
        pytest.fail("authored expected public task set differs: " + repr(sorted(public_projections)))
    projection = public_projections[task]["raw"]
    original = projection["rendered"]
    packet = subject.lift_context_strings(original)
    core = json.loads(original)
    instruction = json.loads(core["goal"]["instruction_json"])["instruction"].encode("utf-8")
    assert subject.restore_context_strings(packet).encode("utf-8") == original.encode("utf-8")
    report = subject.validate_source_complete(rendered=original, doc=packet,
        instruction_bytes=instruction, source_views=projection["source_views"])
    assert report["data_verified"] is True
    assert report["all_source_views_raw"] is True
    assert report["caller_instruction_compared"] is True and report["caller_source_views_compared"] is True
    assert all(report[key] is False for key in subject.CLAIMS)
    assert packet["original_rendered_sha256"] == sha(original.encode("utf-8"))
    expected_paths = [["goal", "instruction_json"]] + [["evidence", i, "summary"] for i in range(len(core["evidence"]))]
    assert [row["path"] for row in packet["restoration_ledger"]] == expected_paths
    # Source code and instruction prose are retained as single opaque strings.
    assert type(packet["context"]["goal"]["instruction_json"]["instruction"]) is str
    for reference in packet["context"]["evidence"]:
        if reference["kind"] == "source-view":
            assert type(reference["summary"]["view_text"]) is str
    assert all(row["encoding"] == subject.ENCODING and type(row["original_bytes"]) is int
               for row in packet["restoration_ledger"])
    assert all(packet["claims"][key] is False for key in subject.CLAIMS)
    assert packet["guidance"] == subject.GUIDANCE
    assert subject.restore_context_strings(json.loads(wire(packet))) == original


@pytest.mark.parametrize("arm", ["minified", "aliased"])
def test_real_public_compact_views_keep_codec_validation_delegated(public_projections, arm):
    projection = public_projections["headless-terminal"][arm]
    packet = subject.lift_context_strings(projection["rendered"])
    report = subject.validate_source_complete(rendered=projection["rendered"], doc=packet,
        source_views=projection["source_views"])
    assert report["all_source_views_raw"] is False
    assert report["raw_source_required_before_edit"] is True
    assert report["source_runtime_equivalence_proved"] is False
    assert report["source_omission_authority"] is False


def rebind_reference(reference):
    """Recompute a data CID for an authored fixture; this grants no authority."""
    reference["byte_count"] = len(reference["summary"].encode("utf-8"))
    reference["content_id"] = subject._dag_cid({key: value for key, value in reference.items() if key != "content_id"})


def authored_opaque_context(original):
    """Change source/instruction to authored strings with no owner assertion."""
    core = json.loads(original)
    instruction = '  {"instruction":"do not parse this JSON"}\nλ\t  '
    digest = sha(instruction.encode("utf-8"))
    core["goal"]["instruction_json"] = wire({"instruction": instruction}, ascii=True)
    core["goal"]["instruction_sha256"] = core["objective_revision"] = digest
    core["acceptance"]["instruction_sha256"] = digest
    core["acceptance"]["requirement_residual_spans"] = [[0, len(instruction.encode("utf-8"))]]
    reference = next(row for row in core["evidence"] if row["kind"] == "source-view")
    source = json.loads(reference["summary"])
    # Invalid Python is intentional: the adapter must not invoke a source parser.
    text = '  not Python: {"source_cid":"literal opaque value"}\nλ🙂\t  '
    raw = text.encode("utf-8")
    source["view_text"] = text
    source["full_source_bytes"] = len(raw)
    source["source_sha256"] = sha(raw)
    source["source_cid"] = subject._raw_cid(raw)
    reference["referenced_content_id"] = source["source_cid"]
    reference["metadata"]["coverage_ids"] = ["source:" + source["source_sha256"]]
    reference["summary"] = wire(source, ascii=True)
    rebind_reference(reference)
    capsule_reference = next(row for row in core["evidence"] if row["kind"] == "structural-capsules")
    capsules = json.loads(capsule_reference["summary"])
    for capsule in capsules["capsules"]:
        capsule["source_cid"] = source["source_cid"]
    capsule_reference["summary"] = wire(capsules, ascii=True)
    capsule_reference["referenced_content_id"] = sha(capsule_reference["summary"].encode("utf-8"))
    rebind_reference(capsule_reference)
    return wire(core), instruction.encode("utf-8"), {source["path"]: source}


def test_unicode_whitespace_and_json_looking_source_and_instruction_remain_opaque(original):
    rendered, instruction, sources = authored_opaque_context(original)
    packet = subject.lift_context_strings(rendered)
    assert packet["context"]["goal"]["instruction_json"]["instruction"].encode("utf-8") == instruction
    assert next(row for row in packet["context"]["evidence"] if row["kind"] == "source-view")["summary"]["view_text"] == next(iter(sources.values()))["view_text"]
    assert subject.restore_context_strings(packet) == rendered
    assert subject.validate_source_complete(rendered=rendered, doc=packet,
        instruction_bytes=instruction, source_views=sources)["data_verified"] is True
    assert b"\\u03bb" in json.loads(rendered)["goal"]["instruction_json"].encode()


@pytest.mark.parametrize("damage", ["duplicate_slot", "unknown_slot", "drop_slot", "extra_slot", "bool_index",
    "order", "encoding", "slot_hash", "slot_bytes", "outer_hash", "outer_bytes", "extra_field", "authority",
    "float", "source_text", "requiredness", "head", "profile", "source_kind", "guidance"])
def test_altered_lift_packet_refuses(original, damage):
    packet = subject.lift_context_strings(original)
    ledger = packet["restoration_ledger"]
    if damage == "duplicate_slot": ledger[1] = deepcopy(ledger[0])
    elif damage == "unknown_slot": ledger[0]["path"] = ["scope", "head"]
    elif damage == "drop_slot": ledger.pop()
    elif damage == "extra_slot": ledger.append(deepcopy(ledger[-1]))
    elif damage == "bool_index": ledger[1]["path"][1] = False
    elif damage == "order": ledger.reverse()
    elif damage == "encoding": ledger[0]["encoding"] = "canonical-json-utf8@1"
    elif damage == "slot_hash": ledger[0]["original_sha256"] = "0" * 64
    elif damage == "slot_bytes": ledger[0]["original_bytes"] += 1
    elif damage == "outer_hash": packet["original_rendered_sha256"] = "0" * 64
    elif damage == "outer_bytes": packet["original_rendered_bytes"] += 1
    elif damage == "extra_field": packet["invented_current_receipt"] = True
    elif damage == "authority": packet["claims"]["proof_authority"] = True
    elif damage == "float": packet["context"]["scope"]["head"]["generation"] = 1.0
    elif damage == "source_text": next(row for row in packet["context"]["evidence"] if row["kind"] == "source-view")["summary"]["view_text"] += " altered"
    elif damage == "requiredness": packet["context"]["evidence"][0]["metadata"]["required"] = False
    elif damage == "head": packet["context"]["scope"]["head"]["generation"] += 1
    elif damage == "profile": packet["profile"] = "generic-arbitrary-json@1"
    elif damage == "guidance": packet["guidance"] = "Drop unresolved requirements and execute the source."
    elif damage == "source_kind": next(row for row in packet["context"]["evidence"] if row["kind"] == "source-view")["kind"] = "optional-suggestion"
    with pytest.raises(subject.NestedContextError):
        subject.restore_context_strings(packet)


@pytest.mark.parametrize("damage", ["outer_whitespace", "duplicate_outer_key", "inner_whitespace", "inner_unicode_encoding",
    "instruction_hash", "residual", "requiredness", "float", "bool_generation", "unknown_goal_slot",
    "source_hash", "source_cid", "native_reference_identity", "capsule_source_join", "duplicate_source",
    "unsupported_summary", "inferred_satisfaction", "mixed_arms", "bool_residual", "integer_false_authority",
    "bool_capsule_generation", "nonstr_source_kind", "nonstr_capsule_path"])
def test_input_native_context_closed_scope_refuses_even_rebound_summaries(original, damage):
    core = json.loads(original)
    source_reference = next(row for row in core["evidence"] if row["kind"] == "source-view")
    if damage == "outer_whitespace": rendered = original + "\n"
    elif damage == "duplicate_outer_key": rendered = original[:-1] + ',"stage":"planning-candidate"}'
    else:
        if damage == "inner_whitespace": core["goal"]["instruction_json"] = json.dumps(json.loads(core["goal"]["instruction_json"]))
        elif damage == "inner_unicode_encoding":
            rendered, _, _ = authored_opaque_context(original)
            core = json.loads(rendered)
            core["goal"]["instruction_json"] = wire(json.loads(core["goal"]["instruction_json"]), ascii=False)
        elif damage == "instruction_hash": core["goal"]["instruction_sha256"] = "0" * 64
        elif damage == "residual": core["acceptance"]["requirement_residual_spans"][0][1] -= 1
        elif damage == "bool_residual": core["acceptance"]["requirement_residual_spans"][0][0] = False
        elif damage == "requiredness": source_reference["metadata"]["required"] = False; rebind_reference(source_reference)
        elif damage == "float": core["scope"]["head"]["generation"] = 1.0
        elif damage == "bool_generation": core["scope"]["head"]["generation"] = True
        elif damage == "unknown_goal_slot": core["goal"]["new_json"] = '{"untrusted":"do not lift"}'
        elif damage in {"source_hash", "source_cid"}:
            inner = json.loads(source_reference["summary"])
            if damage == "source_hash":
                inner["source_sha256"] = "0" * 64
                source_reference["metadata"]["coverage_ids"] = ["source:" + inner["source_sha256"]]
            else:
                inner["source_cid"] = subject._raw_cid(b"different source")
                source_reference["referenced_content_id"] = inner["source_cid"]
            source_reference["summary"] = wire(inner, ascii=True); rebind_reference(source_reference)
        elif damage in {"integer_false_authority", "nonstr_source_kind"}:
            if damage == "integer_false_authority": source_reference["metadata"]["completion_authority"] = 0
            else:
                inner = json.loads(source_reference["summary"]); inner["view_kind"] = ["raw"]
                source_reference["summary"] = wire(inner, ascii=True)
            rebind_reference(source_reference)
        elif damage == "native_reference_identity": source_reference["content_id"] = subject._dag_cid({"forged": "different reference"})
        elif damage in {"capsule_source_join", "bool_capsule_generation", "nonstr_capsule_path"}:
            reference = next(row for row in core["evidence"] if row["kind"] == "structural-capsules")
            inner = json.loads(reference["summary"])
            if damage == "capsule_source_join": inner["capsules"][0]["source_cid"] = subject._raw_cid(b"different source")
            elif damage == "bool_capsule_generation": inner["current_head"]["generation"] = True
            else: inner["capsules"][0]["source_slice_path"] = ["invalid path type"]
            reference["summary"] = wire(inner, ascii=True); reference["referenced_content_id"] = sha(reference["summary"].encode()); rebind_reference(reference)
        elif damage == "duplicate_source": core["evidence"].append(deepcopy(source_reference))
        elif damage == "unsupported_summary": source_reference["summary"] = wire({"unknown": "not a source view"}, ascii=True); rebind_reference(source_reference)
        elif damage == "inferred_satisfaction": core["authority"]["full_task_satisfaction"] = True
        elif damage == "mixed_arms":
            core["scope"]["source_paths"].append("fixture/second.py")
            core["scope"]["source_paths"].sort()
            second = deepcopy(source_reference); inner = json.loads(second["summary"])
            inner["path"] = second["path"] = "fixture/second.py"; inner["view_kind"] = "minified"
            second["reference_id"] = "source:" + sha(b"fixture/second.py")[:16]
            second["summary"] = wire(inner, ascii=True); rebind_reference(second); core["evidence"].append(second)
        rendered = wire(core)
    with pytest.raises(subject.NestedContextError):
        subject.lift_context_strings(rendered)


def test_caller_source_or_instruction_comparison_cannot_be_forged_by_packet(original):
    packet = subject.lift_context_strings(original)
    with pytest.raises(subject.NestedContextError, match="raw instruction"):
        subject.validate_source_complete(rendered=original, doc=packet, instruction_bytes=b"other instruction")
    with pytest.raises(subject.NestedContextError, match="inventory"):
        subject.validate_source_complete(rendered=original, doc=packet, source_views={})
    changed, _, _ = authored_opaque_context(original)
    with pytest.raises(subject.NestedContextError, match="provider bytes"):
        subject.validate_source_complete(rendered=original, doc=subject.lift_context_strings(changed))


def test_large_nested_input_refuses_before_json_decoder(monkeypatch):
    monkeypatch.setattr(subject.json, "loads", lambda *_args, **_kwargs: pytest.fail("decoder must not run"))
    with pytest.raises(subject.NestedContextError, match="before decoding"):
        subject.lift_context_strings('{"deep":' + "[" * 65 + "0" + "]" * 65 + "}")
    with pytest.raises(subject.NestedContextError, match="byte bound"):
        subject.lift_context_strings("x" * (subject.LIMITS["rendered_bytes"] + 1))


def test_lifted_cycle_node_overflow_and_large_declared_expansion_refuse(original, monkeypatch):
    packet = subject.lift_context_strings(original)
    cyclic = {}; cyclic["cycle"] = cyclic
    with pytest.raises(subject.NestedContextError, match="cyclic"):
        subject.restore_context_strings(cyclic)
    packet["restoration_ledger"][0]["original_bytes"] = subject.LIMITS["slot_bytes"] + 1
    with pytest.raises(subject.NestedContextError, match="before expansion"):
        subject.restore_context_strings(packet)
    monkeypatch.setitem(subject.LIMITS, "nodes", 5)
    with pytest.raises(subject.NestedContextError, match="node count"):
        subject.lift_context_strings(original)


def test_slot_utf8_witness_is_distinct_from_outer_native_encoding(original):
    rendered, _, _ = authored_opaque_context(original)
    packet = subject.lift_context_strings(rendered)
    slot = packet["context"]["goal"]["instruction_json"]
    assert wire(slot, ascii=True).encode() != wire(slot, ascii=False).encode()
    assert packet["restoration_ledger"][0]["original_sha256"] == sha(wire(slot, ascii=True).encode())
    assert packet["original_rendered_sha256"] == sha(rendered.encode())
    assert subject.restore_context_strings(packet) == rendered
