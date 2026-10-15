"""Genuine offline BPE controls for full scripts and conservative local scope."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

import token_cost_review as subject


@pytest.fixture(scope="module")
def tokenizer():
    return subject.load_tokenizer()


def event(name, content, *, category="task", kind="input", retry_of=None):
    return {"event_id": name, "kind": kind, "payload": content,
            "segments": [{"partition": category, "text": content}], "retry_of": retry_of}


def test_exact_offline_definition_roundtrip_unicode_and_special_spellings(tokenizer):
    encoding, descriptor = tokenizer
    text = "α β 東京 🦆\n<|endoftext|> <|endofprompt|>"
    assert encoding.decode(encoding.encode(text)) == text
    assert b"".join(encoding.decode_single_token_bytes(token) for token in encoding.encode(text)) == text.encode()
    assert descriptor["definition_sha256"] == subject.DEFINITION_SHA256
    assert descriptor["offline"] and not descriptor["network_fallback"]
    assert not descriptor["provider_tokenizer_equivalence_established"]
    assert subject.tokenizer_count("") == 0


def test_serialization_preserves_complete_json_framing_unicode_and_escaped_content(tokenizer):
    encoding, _ = tokenizer
    messages = [{"role": "system", "content": "Use exact source.", "partition": "setup"},
        {"role": "user", "content": 'α "quoted"\ncode', "segments": [
            {"partition": "task", "text": 'α "quoted"\n'}, {"partition": "retrieval", "text": "code"}]}]
    serialized = subject.serialize_messages(messages)
    assert json.loads(serialized["payload"])["messages"] == [{"role": m["role"], "content": m["content"]} for m in messages]
    assert "".join(piece["text"] for piece in serialized["segments"]) == serialized["payload"]
    report = subject.evaluate_token_costs([dict(serialized, event_id="turn1", kind="input")],
                                         [dict(serialized, event_id="turn1", kind="input")])
    row = report["baseline"]["events"][0]
    assert row["tokens"] == len(encoding.encode(serialized["payload"]))
    assert sum(row["partition_tokens"].values()) == row["tokens"]
    assert sum(row["partition_bytes"].values()) == len(serialized["payload"].encode())
    assert row["partition_bytes"]["framing"] > 0


def test_full_repeated_history_and_retry_are_charged_at_every_call(tokenizer):
    encoding, _ = tokenizer
    system = {"role": "system", "content": "Persistent system setup.", "partition": "setup", "message_id": "setup"}
    user = {"role": "user", "content": "Original task." * 20, "partition": "task", "message_id": "task"}
    initial = dict(subject.serialize_messages([system, user]), event_id="initial", kind="input")
    follow = dict(subject.serialize_messages([dict(system, partition="history"), dict(user, partition="history"),
        {"role": "tool", "content": "Expanded source." * 20, "partition": "expansion"}]),
        event_id="expanded", kind="input", required_history_ids=["setup", "task"])
    retry = dict(follow, event_id="retry", retry_of="expanded")
    report = subject.evaluate_token_costs([initial, follow, retry], [initial, follow, retry])
    arm = report["baseline"]
    assert arm["totals"]["input_tokens"] == len(encoding.encode(initial["payload"])) + 2 * len(encoding.encode(follow["payload"]))
    assert arm["totals"]["retry_input_tokens"] == len(encoding.encode(follow["payload"]))
    assert arm["partition_totals"]["history"]["tokens"] > 0
    assert arm["partition_totals"]["expansion"]["tokens"] > 0
    assert not arm["history_deduplicated"]


def test_bpe_boundary_partition_counts_conserve_whole_without_summing_independent_chunks(tokenizer):
    encoding, _ = tokenizer
    payload = "hello"
    assert len(encoding.encode("hel")) + len(encoding.encode("lo")) != len(encoding.encode(payload))
    request = {"event_id": "input", "kind": "input", "payload": payload,
        "segments": [{"partition": "history", "text": "hel"}, {"partition": "capsule", "text": "lo"}]}
    report = subject.evaluate_token_costs([request], [request])
    row = report["compact"]["events"][0]
    assert row["tokens"] == len(encoding.encode(payload))
    assert sum(row["partition_tokens"].values()) == row["tokens"]


def test_setup_sidecar_and_scripted_output_are_included_without_provider_claim(tokenizer):
    script = [event("setup", "Alias dictionary: a = function metadata", kind="setup", category="setup"),
              event("input", "a"), event("output", "Scripted response.", kind="output", category="output")]
    report = subject.evaluate_token_costs(script, script)
    totals = report["baseline"]["totals"]
    assert totals["total_tokens"] == totals["input_tokens"] + totals["output_tokens"] + totals["setup_tokens"]
    assert totals["output_tokens"] > 0 and totals["setup_tokens"] > 0
    assert report["provider_usage"] is None and report["provider_token_savings"] is None
    assert report["provider_money_savings"] is None
    assert all(report[key] is False for key in subject.CLAIMS)


def test_expansion_cost_can_eliminate_apparent_initial_capsule_gain(tokenizer):
    baseline = [event("input1", "Full source facts. " * 100), event("input2", "Full source facts. " * 100)]
    compact = [event("input1", "Capsule.", category="capsule"),
               event("input2", "History plus expanded source. " * 400, category="expansion")]
    report = subject.evaluate_token_costs(baseline, compact)
    assert report["paired_cumulative_anchors"][0]["signed_local_token_difference"] > 0
    assert report["signed_local_token_difference"] < 0
    assert not report["break_even"]["compact_full_cost_is_lower"]
    assert report["break_even"]["additional_expansion_requires_rerendering_all_affected_full_inputs"]


def test_full_setup_amortization_uses_cumulative_common_anchors(tokenizer):
    baseline = [event("input1", "original body " * 30), event("input2", "original body " * 100)]
    compact = [event("dictionary", "dictionary setup " * 60, kind="setup", category="setup"),
               event("input1", "capsule", category="capsule"), event("input2", "capsule", category="capsule")]
    report = subject.evaluate_token_costs(baseline, compact)
    assert report["paired_cumulative_anchors"][0]["signed_local_token_difference"] < 0
    assert report["paired_cumulative_anchors"][1]["signed_local_token_difference"] > 0
    assert report["break_even"]["first_nonnegative_common_anchor"] == "input2"


@pytest.mark.parametrize("damage", ["missing_cover", "changed_cover", "duplicate_event", "fake_usage", "retry_future"])
def test_undercount_or_unsupported_usage_claim_refuses(damage, tokenizer):
    initial = event("input", "Complete task and history")
    script = [initial]
    if damage == "missing_cover":
        initial["segments"][0]["text"] = "Complete task"
    elif damage == "changed_cover":
        initial["segments"][0]["text"] = "Substituted task and history"
    elif damage == "duplicate_event":
        script += [deepcopy(initial)]
    elif damage == "fake_usage":
        initial["provider_usage"] = {"input_tokens": 0}
    else:
        initial["retry_of"] = "future"
    with pytest.raises(subject.TokenCostError):
        subject.evaluate_token_costs(script, script)


def test_declared_history_id_omission_or_rewrite_refuses(tokenizer):
    original = dict(subject.serialize_messages([{ "role": "user", "content": "Original long body", "message_id": "original"}]),
                    event_id="input1", kind="input")
    omitted = dict(subject.serialize_messages([{ "role": "user", "content": "New body"}]),
                   event_id="input2", kind="input", required_history_ids=["original"])
    with pytest.raises(subject.TokenCostError, match="history"):
        subject.evaluate_token_costs([original, omitted], [original, omitted])
    rewritten = dict(subject.serialize_messages([{ "role": "user", "content": "short", "message_id": "original"}]),
                     event_id="input2", kind="input", required_history_ids=["original"])
    with pytest.raises(subject.TokenCostError, match="historical"):
        subject.evaluate_token_costs([original, rewritten], [original, rewritten])


def test_false_tokenizer_descriptor_or_provider_equivalence_refuses(tokenizer):
    _, descriptor = tokenizer
    changed = deepcopy(descriptor)
    changed["provider_tokenizer_equivalence_established"] = True
    with pytest.raises(subject.TokenCostError, match="descriptor"):
        subject.load_tokenizer(changed)


def test_missing_or_modified_offline_asset_has_no_network_fallback(tmp_path, monkeypatch):
    absent = tmp_path / "missing-ranks"
    monkeypatch.setattr(subject, "BPE_ASSET", absent)
    with pytest.raises(FileNotFoundError):
        subject.load_tokenizer()
    absent.write_bytes(b"authored wrong rank data\n")
    with pytest.raises(subject.TokenCostError, match="pin"):
        subject.load_tokenizer()


def test_bad_utf8_and_full_event_profile_limits_refuse(tokenizer):
    for body in ("\ud800", "x" * (subject.MAX_PAYLOAD_BYTES + 1)):
        with pytest.raises(subject.TokenCostError):
            subject.evaluate_token_costs([event("input", body)], [event("input", body)])
    script = [event(f"input{i}", "x") for i in range(subject.MAX_EVENTS + 1)]
    with pytest.raises(subject.TokenCostError, match="script"):
        subject.evaluate_token_costs(script, script)
