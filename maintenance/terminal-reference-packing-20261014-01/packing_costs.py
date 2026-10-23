"""Scripted full-message packing costs and an exact decode-before-model control.

The worker's generic pure dictionary codec is reused. Direct encoded delivery
is a hypothetical model interface; no worker receipt or provider use is created.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

SCHEMA = "terminal-reference-packing-local-costs@1"
LEDGER_SOURCE = Path("/home/barberb/lift_coding/maintenance/terminal-source-capsules-20261014-01/token_cost_review.py")
LEDGER_SHA256 = "ea806dbaa99d1c1ee241c6acb0fa0097f2de172f4921bf10fc16e0b8fb020041"
SYSTEM = ("Review the complete original task and source context. Preserve all instruction, source and "
          "residual bytes. Representations grant no execution, completion or proof authority.")
FOLLOWUPS = ("Continue planning using every required source and unresolved instruction.",
             "Check the remaining obligations against the same complete source context.")
FALSE = {"provider_usage_measured": False, "provider_token_savings_measured": False,
         "native_worker_delivery_observed": False, "native_full_supervisor_invoked": False,
         "official_terminal_bench_harness_executed": False,
         "model_interpretation_equivalence_proved": False,
         "source_runtime_equivalence_proved": False, "full_task_satisfaction_proved": False,
         "proof_authority": False, "execution_authority": False, "completion_authority": False}


class PackingCostError(ValueError):
    """A retained codec/ledger, exact materialization or scripted arm differs."""


def _need(condition, message):
    if not condition:
        raise PackingCostError(message)


def _ledger():
    import token_cost_review as ledger
    _need(Path(ledger.__file__).resolve() == LEDGER_SOURCE
          and hashlib.sha256(LEDGER_SOURCE.read_bytes()).hexdigest() == LEDGER_SHA256,
          "exact sealed full-message token ledger required")
    return ledger


def _text(value, name, maximum=1_048_576):
    _need(type(value) is str, name + " must be literal text")
    try:
        raw = value.encode("utf-8")
    except UnicodeError as error:
        raise PackingCostError(name + " must be strict UTF-8") from error
    _need(len(raw) <= maximum, name + " exceeds declared byte bound")
    return raw


def _canonical_original(original_rendered):
    from benchmarks.agent_supervisor.container_coding import terminal_semantic_context_transport as transport
    _text(original_rendered, "original full rendered context", transport.MAX_DECODED_BYTES)
    try:
        packet = json.loads(original_rendered)
        canonical = transport.canonical_context_packet(packet)
    except (TypeError, ValueError, RecursionError) as error:
        raise PackingCostError("original full context must be canonical JSON") from error
    _need(canonical == original_rendered, "original full context differs from native canonical bytes")
    return transport, packet


def _native_roundtrip(original_rendered, encoded_wire):
    transport, packet = _canonical_original(original_rendered)
    _text(encoded_wire, "generic encoded wire", transport.MAX_ENCODED_BYTES)
    try:
        decoded = transport.canonical_context_packet(transport.decode_context_packet(encoded_wire))
        expected_wire = transport.encode_context_packet(packet)
    except (TypeError, ValueError, RecursionError) as error:
        raise PackingCostError("native dictionary wire refused by genuine decoder") from error
    _need(decoded == original_rendered and expected_wire == encoded_wire,
          "native dictionary wire does not restore exact full original context")
    return decoded, {"module": transport.__name__, "path": transport.__file__,
        "sha256": hashlib.sha256(Path(transport.__file__).read_bytes()).hexdigest(),
        "encode_api": "encode_context_packet", "decode_api": "decode_context_packet",
        "canonical_api": "canonical_context_packet",
        "pure_codec_executed": True, "worker_process_invoked": False}


def _script(ledger, context, *, followups, outputs, retry_last, common_expansion, decoder_setup):
    _text(context, "model-visible context")
    _need(type(followups) in {list, tuple} and len(followups) <= 4,
          "bounded explicit follow-up instructions required")
    _need(type(outputs) in {list, tuple} and len(outputs) in {0, len(followups) + 1},
          "scripted outputs must cover each supplied input or be explicitly absent")
    _need(type(retry_last) is bool, "retry flag must be exact bool")
    for text in [*followups, *outputs]:
        _text(text, "scripted message", ledger.MAX_PAYLOAD_BYTES)
    _text(decoder_setup, "decoder setup artifact", ledger.MAX_PAYLOAD_BYTES)
    _need(common_expansion is None or type(common_expansion) is str,
          "common source expansion must be explicit literal text or absent")
    if common_expansion is not None:
        _need(len(followups) >= 1, "common source read requires a supplied later input")
        _text(common_expansion, "shared source-read message", ledger.MAX_PAYLOAD_BYTES)
    events = []
    if decoder_setup:
        events.append({"event_id": "decoder-setup", "kind": "setup", "payload": decoder_setup,
            "segments": [{"partition": "setup", "text": decoder_setup}]})
    messages = [{"role": "system", "content": SYSTEM, "partition": "setup", "message_id": "system"},
                {"role": "user", "content": context, "partition": "retrieval", "message_id": "context"}]
    for turn in range(len(followups) + 1):
        if turn:
            for message in messages:
                message["partition"] = "history"
            if turn == 1 and common_expansion is not None:
                messages.append({"role": "tool", "content": common_expansion, "partition": "expansion",
                                 "message_id": "common-source-read"})
            messages.append({"role": "user", "content": followups[turn - 1], "partition": "task",
                             "message_id": "followup:" + str(turn)})
        rendered = ledger.serialize_messages(messages)
        event_id = "input:" + str(turn)
        events.append(dict(rendered, event_id=event_id, kind="input",
                           required_history_ids=["system", "context"] if turn else []))
        if outputs:
            response = outputs[turn]
            events.append({"event_id": "output:" + str(turn), "kind": "output", "payload": response,
                "segments": [{"partition": "output", "text": response}]})
            messages.append({"role": "assistant", "content": response, "partition": "output",
                             "message_id": "response:" + str(turn)})
    if retry_last:
        last = next(event for event in reversed(events) if event["kind"] == "input")
        events.append(dict(last, event_id="retry:last", retry_of=last["event_id"]))
    return events


def evaluate_packing_costs(*, task_id, original_rendered, encoded_wire,
        candidate_name="native_dictionary", codec_kind="native", restore=None,
        script_name="one_turn", followup_instructions=None, scripted_outputs=(),
        retry_last=False, inline_guidance="", decoder_setup="", common_expansion=None,
        tokenizer_descriptor=None):
    """Compare hypothetical encoded inputs with full decoded model materialization.

    Reference decoders are caller-owned and independently source-pinned by the
    runner. Their exact output is checked here but is not a native worker. The
    entire supplied wire, including its dictionary/ledger, and any additional
    inline guidance are part of every complete direct model-input message.
    Optional source reads apply identically to every arm; packing adds no source
    omission which would justify a special raw-source expansion charge.
    """
    for value, name in [(task_id, "task identity"), (candidate_name, "candidate name")]:
        _need(0 < len(_text(value, name, 128)), "bounded " + name + " required")
    _need(type(codec_kind) is str and codec_kind in {"native", "reference", "reference-lifted"},
          "closed codec kind required")
    _need(type(script_name) is str and script_name in {"one_turn", "three_turn_history", "custom"},
          "closed script name required")
    if followup_instructions is None:
        followup_instructions = FOLLOWUPS if script_name == "three_turn_history" else ()
    _need(type(followup_instructions) in {list, tuple}, "explicit bounded follow-up list required")
    if script_name != "custom":
        _need(len(followup_instructions) == (2 if script_name == "three_turn_history" else 0),
              "follow-up count differs from declared script")
    _text(encoded_wire, "complete encoded wire", 256_000)
    _text(inline_guidance, "complete inline decoder guidance", 256_000)
    _need(restore is None or callable(restore), "restore must be a callback or absent")
    native = None
    if codec_kind == "native":
        decoded, native = _native_roundtrip(original_rendered, encoded_wire)
    else:
        _canonical_original(original_rendered)
        _need(callable(restore), "reference representation requires its exact restore callback")
        decoded = original_rendered
    if restore is not None:
        try:
            restored = restore(encoded_wire)
        except Exception as error:
            raise PackingCostError("nominated restore callback refused complete encoded wire") from error
        _need(type(restored) is str and restored == original_rendered,
              "nominated codec does not restore exact original full context")
        decoded = restored
    visible = inline_guidance + encoded_wire
    _text(visible, "complete inline guidance plus wire")
    ledger = _ledger()
    _, descriptor = ledger.load_tokenizer(tokenizer_descriptor)
    shared = dict(followups=followup_instructions, outputs=scripted_outputs, retry_last=retry_last,
                  common_expansion=common_expansion)
    baseline = _script(ledger, original_rendered, decoder_setup="", **shared)
    direct = _script(ledger, visible, decoder_setup=decoder_setup, **shared)
    materialized = _script(ledger, decoded, decoder_setup=decoder_setup, **shared)
    comparisons = {"direct_encoded_delivery": ledger.evaluate_token_costs(baseline, direct, descriptor),
                   "decode_before_model": ledger.evaluate_token_costs(baseline, materialized, descriptor)}
    controls = comparisons["decode_before_model"]
    original_inputs = [row for row in controls["baseline"]["events"] if row["kind"] == "input"]
    decoded_inputs = [row for row in controls["compact"]["events"] if row["kind"] == "input"]
    _need([(row["event_id"], row["sha256"], row["bytes"], row["tokens"]) for row in original_inputs]
          == [(row["event_id"], row["sha256"], row["bytes"], row["tokens"]) for row in decoded_inputs],
          "decode-before-model changes an actual scripted full input")
    _need(controls["baseline"]["totals"]["input_tokens"] == controls["compact"]["totals"]["input_tokens"],
          "post-materialization model input savings must be exactly zero")
    bindings = {"original_sha256": hashlib.sha256(original_rendered.encode()).hexdigest(),
        "encoded_wire_sha256": hashlib.sha256(encoded_wire.encode()).hexdigest(),
        "decoded_sha256": hashlib.sha256(decoded.encode()).hexdigest(),
        "original_bytes": len(original_rendered.encode()), "encoded_wire_bytes": len(encoded_wire.encode()),
        "direct_model_context_sha256": hashlib.sha256(visible.encode()).hexdigest(),
        "direct_model_context_bytes": len(visible.encode()),
        "inline_guidance_sha256": hashlib.sha256(inline_guidance.encode()).hexdigest(),
        "inline_guidance_bytes": len(inline_guidance.encode())}
    return {"schema": SCHEMA, "task_id": task_id, "candidate_name": candidate_name,
        "codec_kind": codec_kind, "script_name": script_name,
        "scripted_turns": len(followup_instructions) + 1, "comparisons": comparisons, "bindings": bindings,
        "native_generic_codec": native, "tokenizer": descriptor,
        "decoded_full_context_bytes_exact": True,
        "post_materialization_full_input_hashes_and_tokens_equal": True,
        "post_materialization_model_input_token_difference": 0,
        "caller_owned_restore_callback_executed": restore is not None,
        "caller_owned_decoder_provenance_verified_here": False,
        "direct_delivery_scope": "SCRIPTED hypothetical encoded wire sent directly to model with inline guidance",
        "decoded_delivery_scope": "SCRIPTED exact nominated codec materialization before model; no worker receipt",
        "decoder_setup_is_local_materialization_not_provider_input": True,
        "extra_llm_decoder_call_assumed": False,
        "packing_specific_raw_source_expansion_tax_assumed": False,
        "full_original_raw_code_retained_after_decode": True,
        "scripted_output_events_supplied": len(scripted_outputs),
        "common_source_read_supplied": common_expansion is not None,
        "provider_usage": None, "provider_token_savings": None,
        "actual_provider_invocations_created": 0, **FALSE}
