"""Choose a bounded complete message representation using exact local costs.

This pure adapter makes no provider call or native worker observation. A caller
authorizes substitution of one identified context message only. A session owner
must separately prevent rewriting message IDs/content already delivered earlier.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import stat

SCHEMA = "terminal-complete-message-adaptive-delivery@1"
MAX_MESSAGES = 32
MAX_SERIALIZED_BYTES = 500_000
MAX_GUIDANCE_BYTES = 65_536
LEDGER_SOURCE = Path("/home/barberb/lift_coding/maintenance/terminal-source-capsules-20261014-01/token_cost_review.py")
LEDGER_SHA256 = "ea806dbaa99d1c1ee241c6acb0fa0097f2de172f4921bf10fc16e0b8fb020041"
CLAIMS = {name: False for name in (
    "provider_usage_measured", "provider_token_savings_measured",
    "provider_tokenizer_equivalence_established", "native_worker_delivery_observed",
    "native_full_supervisor_invoked", "live_session_history_immutability_verified",
    "source_runtime_equivalence_proved", "source_model_equivalence_proved",
    "full_task_satisfaction", "requirement_discharge", "source_omission_authority",
    "proof_authority", "execution_authority", "completion_authority")}


class AdaptiveDeliveryError(ValueError):
    """The candidate, exact messages, local codec or declared bounds differ."""


class DeliveryBudgetError(AdaptiveDeliveryError):
    """The final selected complete serialized input exceeds its token budget."""


def _need(condition, message):
    if not condition:
        raise AdaptiveDeliveryError(message)


def _text(value, name, maximum=MAX_SERIALIZED_BYTES):
    _need(type(value) is str, name + " must be exact text")
    try:
        raw = value.encode("utf-8")
    except UnicodeError as error:
        raise AdaptiveDeliveryError(name + " must be strict UTF-8") from error
    _need(len(raw) <= maximum, name + " exceeds byte bound")
    return raw


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _ledger():
    import token_cost_review as ledger
    _need(Path(ledger.__file__).resolve(strict=True) == LEDGER_SOURCE,
          "exact sealed complete-message ledger required")
    descriptor = os.open(LEDGER_SOURCE, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        before = os.fstat(stream.fileno())
        _need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and 0 < before.st_size <= 65_536,
              "bounded single-link sealed ledger source required")
        raw = stream.read(65_537)
        after = os.fstat(stream.fileno())
    witness = lambda row: (row.st_dev, row.st_ino, row.st_size, row.st_mtime_ns, row.st_ctime_ns)
    _need(len(raw) == before.st_size and witness(before) == witness(after) == witness(LEDGER_SOURCE.lstat())
          and _sha(raw) == LEDGER_SHA256, "sealed complete-message ledger source changed")
    return ledger


def _messages(messages):
    _need(type(messages) is list and 1 <= len(messages) <= MAX_MESSAGES,
          "one to 32 exact complete messages required")
    ids, total = [], 0
    for message in messages:
        _need(type(message) is dict and set(message) == {"message_id", "role", "content"},
              "closed message_id/role/content fields required")
        identity = message["message_id"]
        raw_id = _text(identity, "message ID", 512)
        _need(0 < len(identity) <= 128 and raw_id, "bounded nonempty exact message ID required")
        _need(type(message["role"]) is str and message["role"] in {"system", "developer", "user", "assistant", "tool"},
              "known exact message role required")
        total += len(_text(message["content"], "complete message content"))
        _need(total <= MAX_SERIALIZED_BYTES, "cumulative message content exceeds serialized profile")
        _need(identity not in ids, "duplicate message ID")
        ids.append(identity)
    return ids


def _manifest(messages):
    return [{"message_id": row["message_id"], "role": row["role"], "index": index,
             "content_bytes": len(row["content"].encode("utf-8")),
             "content_sha256": _sha(row["content"].encode("utf-8"))}
            for index, row in enumerate(messages)]


def _measure(ledger, tokenizer, messages):
    _messages(messages)
    try:
        serialized = ledger.serialize_messages(messages)
        payload = serialized["payload"]
        raw = _text(payload, "complete serialized message payload")
        tokens = tokenizer.encode(payload)
    except ledger.TokenCostError as error:
        raise AdaptiveDeliveryError("complete-message local measurement refused: " + str(error)) from error
    _need(type(tokens) is list and all(type(token) is int for token in tokens),
          "actual exact offline BPE token list required")
    _need(tokenizer.decode(tokens) == payload, "whole serialized input tokenizer roundtrip differs")
    _need(serialized["messages"] == [{"role": row["role"], "content": row["content"]} for row in messages],
          "serialized complete message content/role population differs")
    return {"serialized_payload": payload, "payload_sha256": _sha(raw), "payload_bytes": len(raw),
            "input_tokens": len(tokens), "message_manifest": _manifest(messages)}


def select_delivery(*, original_rendered: str, packed_wire: str, messages: list,
        context_message_id: str, restore, max_input_tokens: int, tokenizer_descriptor=None,
        history_required_ids: tuple = (), delivery_mode: str = "adaptive",
        routing_guidance: str = "") -> dict:
    """Select a final complete input after exact packed restoration and counting.

    Adaptive mode chooses packed only for a strict complete-message local token
    decrease. Expanded and packed modes are explicit forced controls; each still
    checks the final selected budget. Message IDs are local custody metadata,
    excluded by the unchanged C ledger's role/content wire format.
    """
    original_bytes = _text(original_rendered, "complete original context")
    _text(packed_wire, "complete packed wire")
    guidance_bytes = _text(routing_guidance, "explicit packed routing guidance", MAX_GUIDANCE_BYTES)
    _need(type(delivery_mode) is str and delivery_mode in {"adaptive", "expanded", "packed"},
          "closed adaptive/expanded/packed delivery mode required")
    _need(type(max_input_tokens) is int and 0 < max_input_tokens < 2**63,
          "positive exact signed-64-bit input token budget required")
    ids = _messages(messages)
    _text(context_message_id, "context message ID", 512)
    _need(context_message_id in ids, "identified context message is missing")
    index = ids.index(context_message_id)
    _need(messages[index]["content"].encode("utf-8") == original_bytes,
          "identified context message must contain the exact original context")
    _need(type(history_required_ids) is tuple and len(history_required_ids) <= MAX_MESSAGES
          and all(type(identity) is str for identity in history_required_ids),
          "bounded exact tuple of required history IDs required")
    _need(len(set(history_required_ids)) == len(history_required_ids)
          and all(identity in ids for identity in history_required_ids), "required history ID missing or duplicated")
    _need(callable(restore), "actual pure packed restoration callback required")
    baseline = deepcopy(messages)
    try:
        restored = restore(packed_wire)
    except Exception as error:
        raise AdaptiveDeliveryError("actual packed restoration callback refused") from error
    _need(type(restored) is str and _text(restored, "restored complete native context") == original_bytes,
          "packed restoration does not match the complete original context")
    _messages(messages)
    _need(messages == baseline, "restoration callback changed caller messages")

    packed = deepcopy(baseline)
    separator = "\n" if routing_guidance else ""
    packed[index]["content"] = routing_guidance + separator + packed_wire
    _messages(packed)
    ledger = _ledger()
    tokenizer, descriptor = ledger.load_tokenizer(tokenizer_descriptor)
    expanded_cost = _measure(ledger, tokenizer, baseline)
    packed_cost = _measure(ledger, tokenizer, packed)
    expanded_cost["within_input_token_budget"] = expanded_cost["input_tokens"] <= max_input_tokens
    packed_cost["within_input_token_budget"] = packed_cost["input_tokens"] <= max_input_tokens
    cheaper = packed_cost["input_tokens"] < expanded_cost["input_tokens"]
    if delivery_mode == "adaptive":
        form = "packed" if cheaper else "expanded"
        reason = "packed_strictly_cheaper_complete_input" if cheaper else "expanded_no_strict_packed_decrease"
    else:
        form, reason = delivery_mode, "caller_forced_" + delivery_mode
    selected_messages = packed if form == "packed" else baseline
    selected_cost = packed_cost if form == "packed" else expanded_cost
    if not selected_cost["within_input_token_budget"]:
        raise DeliveryBudgetError("final complete serialized input exceeds token budget: selected=" + form
            + ", selected_tokens=" + str(selected_cost["input_tokens"]) + ", expanded_tokens="
            + str(expanded_cost["input_tokens"]) + ", packed_tokens=" + str(packed_cost["input_tokens"])
            + ", max_input_tokens=" + str(max_input_tokens))
    for position, message in enumerate(selected_messages):
        _need(message["message_id"] == baseline[position]["message_id"] and message["role"] == baseline[position]["role"]
              and (position == index or message["content"] == baseline[position]["content"]),
              "only the designated context content may change")
    _need(messages == baseline, "caller message population changed during local selection")
    _, after = ledger.load_tokenizer(descriptor)
    _need(after == descriptor and _ledger() is ledger, "offline tokenizer or sealed ledger changed during selection")
    return {"schema": SCHEMA, "delivery_mode": delivery_mode, "selected_form": form, "reason": reason,
        "selected_messages": deepcopy(selected_messages), **deepcopy(selected_cost),
        "max_input_tokens": max_input_tokens, "final_complete_input_within_budget": True,
        "expanded_full_message_cost": expanded_cost, "packed_full_message_cost": packed_cost,
        "packed_strictly_cheaper_complete_input": cheaper,
        "signed_local_input_token_difference": expanded_cost["input_tokens"] - selected_cost["input_tokens"],
        "adaptive_local_nonregression_checked": delivery_mode == "adaptive",
        "selected_local_tokens_not_greater_than_expanded": selected_cost["input_tokens"] <= expanded_cost["input_tokens"],
        "context_message_id": context_message_id, "context_message_index": index,
        "original_context_sha256": _sha(original_bytes), "packed_wire_sha256": _sha(packed_wire.encode("utf-8")),
        "packed_restores_complete_original": True, "context_substitution_authorized_by_caller_only": True,
        "every_other_message_bytes_roles_ids_unchanged": True, "input_message_manifest": _manifest(baseline),
        "history_required_ids": list(history_required_ids), "required_history_ids_present": True,
        "required_noncontext_history_bytes_unchanged": True,
        "designated_context_is_required_history": context_message_id in history_required_ids,
        "prior_delivery_state_checked": False,
        "routing_guidance": {"text": routing_guidance, "separator": separator, "bytes": len(guidance_bytes),
            "included_in_packed_message": bool(routing_guidance), "charged_in_complete_packed_input": True},
        "tokenizer": descriptor, "ledger": {"path": str(LEDGER_SOURCE), "sha256": LEDGER_SHA256},
        "cost_scope": "unchanged sealed C serializer: every role/content message and full JSON framing; local IDs tracked separately",
        "message_ids_are_local_manifest_only": True, "provider_usage": None,
        "provider_invocations": 0, **CLAIMS}


__all__ = ["select_delivery", "AdaptiveDeliveryError", "DeliveryBudgetError", "SCHEMA", "CLAIMS"]
