"""Authored contexts; genuine retained codec and offline whole-message BPE."""
import base64
import hashlib
import json
import zlib

import pytest

import packing_costs as costs
import token_cost_review as ledger
from benchmarks.agent_supervisor.container_coding import terminal_semantic_context_transport as native


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


@pytest.fixture
def small():
    packet = {"instruction": "Inspect π and preserve trailing newlines.\n\n",
              "sources": [{"path": "a.py", "source": "def add(a, b):\n    return a + b\n"}],
              "residual": {"unproved": True, "bytes": [0, 57]}}
    rendered = canonical(packet)
    return rendered, native.encode_context_packet(packet)


@pytest.fixture
def repeated():
    source = "def inspect(value):\n    # Complete original raw source α.\n    return value\n" * 100
    rendered = canonical({"instruction": "Preserve the entire original context.\n",
                          "sources": [{"path": "a.py", "source": source},
                                      {"path": "b.py", "source": source}],
                          "residual": {"unproved": True, "unchanged_source": source}})
    return rendered, native.encode_context_packet(json.loads(rendered))


def reference_wire(original):
    """Authored, self-contained reversible fixture; never an actual model call."""
    return canonical({"guide": "base64 decode body, then zlib decompress to exact UTF-8 original JSON",
                      "body": base64.b64encode(zlib.compress(original.encode())).decode()})


def restore_reference(wire):
    return zlib.decompress(base64.b64decode(json.loads(wire)["body"], validate=True)).decode("utf-8")


def evaluate(pair, **options):
    original, wire = pair
    return costs.evaluate_packing_costs(task_id="authored-task", original_rendered=original,
                                      encoded_wire=wire, **options)


def inputs(report, comparison, arm):
    return [row for row in report["comparisons"][comparison][arm]["events"] if row["kind"] == "input"]


def actual_messages(context, *, followups=(), outputs=(), common_expansion=None):
    messages = [{"role": "system", "content": costs.SYSTEM}, {"role": "user", "content": context}]
    result = []
    for turn in range(len(followups) + 1):
        if turn:
            if turn == 1 and common_expansion is not None:
                messages.append({"role": "tool", "content": common_expansion})
            messages.append({"role": "user", "content": followups[turn - 1]})
        result.append(ledger.serialize_messages(messages)["payload"])
        if outputs:
            messages.append({"role": "assistant", "content": outputs[turn]})
    return result


def test_native_actual_codec_and_exact_unicode_original(small):
    report = evaluate(small)
    original, wire = small
    assert report["bindings"]["original_sha256"] == hashlib.sha256(original.encode()).hexdigest()
    assert report["bindings"]["decoded_sha256"] == report["bindings"]["original_sha256"]
    assert report["bindings"]["encoded_wire_sha256"] == hashlib.sha256(wire.encode()).hexdigest()
    assert report["native_generic_codec"]["decode_api"] == "decode_context_packet"
    assert report["native_generic_codec"]["pure_codec_executed"] is True
    assert report["native_generic_codec"]["worker_process_invoked"] is False
    assert report["post_materialization_model_input_token_difference"] == 0
    assert inputs(report, "decode_before_model", "baseline") == inputs(report, "decode_before_model", "compact")


def test_small_native_wire_can_cost_more_but_control_still_zero(small):
    report = evaluate(small)
    direct = report["comparisons"]["direct_encoded_delivery"]
    assert direct["signed_local_token_difference"] < 0
    assert direct["break_even"]["compact_full_cost_is_lower"] is False
    assert report["comparisons"]["decode_before_model"]["signed_local_token_difference"] == 0


def test_full_self_contained_dictionary_wire_is_counted_not_just_nodes(repeated):
    report = evaluate(repeated)
    tokenizer, _ = ledger.load_tokenizer()
    whole = actual_messages(repeated[1])[0]
    row = inputs(report, "direct_encoded_delivery", "compact")[0]
    assert row["tokens"] == len(tokenizer.encode(whole))
    assert row["bytes"] == len(whole.encode())
    assert json.loads(repeated[1])["decoder_instructions"] in ledger.serialize_messages(
        [{"role": "user", "content": repeated[1]}])["messages"][0]["content"]
    assert report["comparisons"]["direct_encoded_delivery"]["signed_local_token_difference"] > 0


@pytest.mark.parametrize("kind", ["reference", "reference-lifted"])
def test_independent_reference_candidate_exact_restore_and_false_worker(kind, repeated):
    original = repeated[0]
    report = costs.evaluate_packing_costs(task_id="authored", original_rendered=original,
        encoded_wire=reference_wire(original), candidate_name="authored-" + kind,
        codec_kind=kind, restore=restore_reference)
    assert report["candidate_name"] == "authored-" + kind
    assert report["codec_kind"] == kind
    assert report["native_generic_codec"] is None
    assert report["caller_owned_restore_callback_executed"] is True
    assert report["caller_owned_decoder_provenance_verified_here"] is False
    assert report["post_materialization_full_input_hashes_and_tokens_equal"] is True
    assert report["comparisons"]["decode_before_model"]["signed_local_token_difference"] == 0


def test_three_turn_complete_history_and_outputs_counted_each_call(small):
    responses = ("First scripted analysis α.", "Second scripted analysis β.", "Final scripted analysis γ.")
    report = evaluate(small, script_name="three_turn_history", scripted_outputs=responses)
    tokenizer, _ = ledger.load_tokenizer()
    base_inputs = inputs(report, "direct_encoded_delivery", "baseline")
    payloads = actual_messages(small[0], followups=costs.FOLLOWUPS, outputs=responses)
    assert [row["tokens"] for row in base_inputs] == [len(tokenizer.encode(text)) for text in payloads]
    assert [row["bytes"] for row in base_inputs] == [len(text.encode()) for text in payloads]
    assert [row["messages"] for row in base_inputs] == [2, 4, 6]
    assert report["scripted_turns"] == 3
    totals = report["comparisons"]["direct_encoded_delivery"]["baseline"]["totals"]
    assert totals["input_tokens"] == sum(len(tokenizer.encode(text)) for text in payloads)
    assert totals["input_tokens"] > base_inputs[-1]["tokens"]
    assert totals["output_tokens"] == sum(len(tokenizer.encode(text)) for text in responses)
    assert totals["output_events"] == 3
    assert report["comparisons"]["direct_encoded_delivery"]["baseline"]["history_deduplicated"] is False
    assert report["comparisons"]["direct_encoded_delivery"]["baseline"]["partition_totals"]["history"]["bytes"] > len(small[0].encode()) * 2


def test_retry_charges_last_full_history_input_again(small):
    report = evaluate(small, script_name="three_turn_history", retry_last=True)
    for comparison in report["comparisons"].values():
        for arm in ("baseline", "compact"):
            rows = [row for row in comparison[arm]["events"] if row["kind"] == "input"]
            assert len(rows) == 4
            assert rows[-1]["retry_of"] == "input:2"
            assert rows[-1]["sha256"] == rows[-2]["sha256"]
            assert rows[-1]["tokens"] == rows[-2]["tokens"]
            assert comparison[arm]["totals"]["retry_input_tokens"] == rows[-2]["tokens"]
            assert comparison[arm]["totals"]["input_tokens"] == sum(row["tokens"] for row in rows)


def test_setup_cannot_create_decode_model_input_savings_and_is_in_full_cost(small):
    setup = "Install pinned pure decoder instructions.\n" * 20
    report = evaluate(small, decoder_setup=setup)
    tokenizer, _ = ledger.load_tokenizer()
    control = report["comparisons"]["decode_before_model"]
    assert control["compact"]["totals"]["input_tokens"] == control["baseline"]["totals"]["input_tokens"]
    assert control["compact"]["totals"]["setup_tokens"] == len(tokenizer.encode(setup))
    assert control["signed_local_token_difference"] == -len(tokenizer.encode(setup))
    assert control["break_even"]["first_nonnegative_common_anchor"] is None
    assert report["decoder_setup_is_local_materialization_not_provider_input"] is True


def test_break_even_uses_complete_setup_and_history_cost(repeated):
    setup = "Prepare exact decoder body and alias ledger.\n" * 500
    report = evaluate(repeated, script_name="three_turn_history", decoder_setup=setup)
    direct = report["comparisons"]["direct_encoded_delivery"]
    assert direct["signed_local_token_difference"] == (
        direct["baseline"]["totals"]["total_tokens"] - direct["compact"]["totals"]["total_tokens"])
    anchors = direct["paired_cumulative_anchors"]
    expected = next((row["event_id"] for row in anchors if row["signed_local_token_difference"] >= 0), None)
    assert direct["break_even"]["first_nonnegative_common_anchor"] == expected
    assert direct["compact"]["totals"]["setup_events"] == 1


def test_common_raw_read_applies_identically_and_repeats_in_history(small):
    expansion = "Shared optional read: def extra():\n    return 'π'\n"
    report = evaluate(small, script_name="three_turn_history", common_expansion=expansion)
    tokenizer, _ = ledger.load_tokenizer()
    for arm, context in [("baseline", small[0]), ("compact", small[1])]:
        rows = inputs(report, "direct_encoded_delivery", arm)
        full = actual_messages(context, followups=costs.FOLLOWUPS, common_expansion=expansion)
        assert [row["tokens"] for row in rows] == [len(tokenizer.encode(text)) for text in full]
        assert rows[1]["partition_bytes"]["expansion"] == len(canonical(expansion)[1:-1].encode())
        assert any(item["message_id"] == "common-source-read" for item in rows[2]["message_manifest"])
    assert report["packing_specific_raw_source_expansion_tax_assumed"] is False
    assert report["common_source_read_supplied"] is True


def test_inline_guidance_is_model_visible_on_every_turn(small):
    guide = "ADDITIONAL INLINE GUIDANCE with Unicode δ.\n"
    report = evaluate(small, script_name="three_turn_history", inline_guidance=guide)
    tokenizer, _ = ledger.load_tokenizer()
    expected = actual_messages(guide + small[1], followups=costs.FOLLOWUPS)
    rows = inputs(report, "direct_encoded_delivery", "compact")
    assert [row["tokens"] for row in rows] == [len(tokenizer.encode(text)) for text in expected]
    assert report["bindings"]["direct_model_context_sha256"] == hashlib.sha256((guide + small[1]).encode()).hexdigest()
    assert report["comparisons"]["decode_before_model"]["signed_local_token_difference"] == 0


def test_estimates_are_not_actual_usage_or_receipts(small):
    report = evaluate(small)
    assert report["provider_usage"] is None
    assert report["provider_token_savings"] is None
    assert report["actual_provider_invocations_created"] == 0
    assert report["extra_llm_decoder_call_assumed"] is False
    assert report["tokenizer"]["provider_tokenizer_equivalence_established"] is False
    for key in costs.FALSE:
        assert report[key] is False
    for comparison in report["comparisons"].values():
        assert comparison["provider_usage"] is None
        assert comparison["provider_money_savings"] is None
        assert comparison["actual_live_history_completeness_verified"] is False


@pytest.mark.parametrize("mutation", ["wire", "original", "float"])
def test_native_wrong_wire_noncanonical_original_and_float_refused(small, mutation):
    original, wire = small
    if mutation == "wire":
        envelope = json.loads(wire)
        envelope["decoder_instructions"] += "changed"
        wire = canonical(envelope)
    elif mutation == "original":
        original += "\n"
    else:
        original = canonical({"forbidden_float": 0.5})
    with pytest.raises(costs.PackingCostError):
        evaluate((original, wire))


@pytest.mark.parametrize("restore", [None, lambda wire: "wrong", lambda wire: {}, lambda wire: (_ for _ in ()).throw(ValueError("refused"))])
def test_reference_requires_exact_real_restoration(small, restore):
    with pytest.raises(costs.PackingCostError):
        evaluate(small, codec_kind="reference", restore=restore)


def test_native_callback_cannot_override_native_decode(small):
    with pytest.raises(costs.PackingCostError, match="exact original"):
        evaluate(small, restore=lambda wire: small[0] + "\n")
    assert evaluate(small, restore=lambda wire: native.canonical_context_packet(
        native.decode_context_packet(wire)))["caller_owned_restore_callback_executed"] is True


@pytest.mark.parametrize("options", [
    {"script_name": "one_turn", "followup_instructions": ["extra"]},
    {"script_name": "three_turn_history", "followup_instructions": []},
    {"script_name": "unknown"}, {"codec_kind": "opaque"}, {"codec_kind": []},
    {"retry_last": 1}, {"scripted_outputs": ["one", "extra"]},
    {"common_expansion": "would otherwise be silently omitted"},
    {"candidate_name": ""}, {"inline_guidance": "x" * 256_001},
    {"script_name": "custom", "followup_instructions": ["x"] * 5},
])
def test_declared_scenario_bounds_and_no_silent_omissions(small, options):
    with pytest.raises((costs.PackingCostError, ledger.TokenCostError)):
        evaluate(small, **options)


def test_ledger_source_pin_is_enforced(small, monkeypatch):
    monkeypatch.setattr(costs, "LEDGER_SHA256", "0" * 64)
    with pytest.raises(costs.PackingCostError, match="exact sealed"):
        evaluate(small)


def test_replay_is_stable_no_elapsed_timestamps(small):
    report = evaluate(small, script_name="three_turn_history", retry_last=True)
    assert report == evaluate(small, script_name="three_turn_history", retry_last=True,
                              tokenizer_descriptor=report["tokenizer"])
