"""Helpers for building Meta glasses mobile ORB request artifacts.

These helpers keep stable CID generation and stored ORB record construction out
of the API transport layer.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from handsfree.models import (
    MetaGlassesMobileOrbBindServiceRequest,
    MetaGlassesMobileOrbDispatchResponseRequest,
    MetaGlassesMobileOrbEventRequest,
    MetaGlassesMobileOrbInvokeServiceRequest,
    MetaGlassesMobileOrbRegisterRequest,
    MetaGlassesMobileOrbRevokeBindingRequest,
    MetaGlassesMobileOrbSubscribeServiceUpdatesRequest,
)

CONTROL_SURFACE_CONTRACT_REF = "control_surface_contract:hallucinate-app:remote-client"
CONTROL_SURFACE_POLICY_BUNDLE_REF = {
    "policy_id": "policy:hallucinate-app:remote-client-transport",
    "policy_cid": "local:hallucinate-app:remote-client-transport",
    "version": "0.1.0",
    "scope": "remote-client-transport",
    "source": "system_default",
}
CONTROL_SURFACE_COMPILED_POLICY_CID = "local:hallucinate-app:remote-client-transport"
CONTROL_SURFACE_SCHEMA_REFS = [
    "control_surface_contract",
    "interaction_envelope",
    "policy_decision",
    "mediation_receipt",
]


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _local_sha256_cid(prefix: str, value: Any) -> str:
    digest = hashlib.sha256(_stable_json(value).encode("utf-8")).hexdigest()
    return f"sha256:{prefix}:{digest}"


def _first_nonempty_string(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _payload_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        dumped = value.model_dump()
        return dumped if isinstance(dumped, dict) else {}
    return value if isinstance(value, dict) else {}


def _payload_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _without_none(value: dict[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if item is not None}


def _control_surface_contract_ref(payload: dict[str, Any]) -> str:
    return (
        _first_nonempty_string(payload.get("control_surface_contract_ref"))
        or CONTROL_SURFACE_CONTRACT_REF
    )


def _remote_surface(operation: str, payload: dict[str, Any]) -> str:
    platform = _first_nonempty_string(payload.get("platform"))
    if platform == "simulator":
        return "simulator"
    if operation == "publish_glasses_event" or payload.get("event_type") in {
        "captouch",
        "neural_input",
        "display_action",
    }:
        return "meta_glasses"
    return "mobile"


def _remote_actor_id(payload: dict[str, Any]) -> str:
    return (
        _first_nonempty_string(
            payload.get("edge_session_id"),
            payload.get("edge_id"),
            payload.get("device_id"),
            payload.get("binding_handle"),
            payload.get("correlation_id"),
        )
        or "remote-client"
    )


def _runtime_context(
    *,
    payload: dict[str, Any],
    surface: str,
    emitted_at: str,
) -> dict[str, Any]:
    return {
        "local_time": emitted_at,
        "state_frames": _payload_list(payload.get("state_frames")),
        "device_mode": _first_nonempty_string(payload.get("device_mode"), surface) or surface,
        "platform": _first_nonempty_string(payload.get("platform"), surface) or surface,
        "location_context": payload.get("location_context")
        if isinstance(payload.get("location_context"), dict)
        else {},
        "device_context": _without_none(
            {
                "edge_id": payload.get("edge_id"),
                "edge_session_id": payload.get("edge_session_id"),
                "device_id": payload.get("device_id"),
                "device_model": payload.get("device_model"),
                "dat_capabilities": payload.get("dat_capabilities"),
                "glasses_context": payload.get("glasses_context"),
                "display_context": payload.get("display_context"),
            }
        ),
    }


def _intent_from_payload(operation: str, payload: dict[str, Any], surface: str) -> str:
    nested_payload = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}
    arguments = payload.get("arguments") if isinstance(payload.get("arguments"), dict) else {}
    return (
        _first_nonempty_string(
            payload.get("user_intent"),
            payload.get("intent"),
            nested_payload.get("intent"),
            nested_payload.get("command"),
            arguments.get("intent"),
        )
        or f"{surface}.{operation}"
    )


def _normalized_intent(operation: str, payload: dict[str, Any], surface: str) -> dict[str, Any]:
    existing = payload.get("normalized_intent")
    if isinstance(existing, dict) and existing.get("method") and existing.get("target_ref"):
        return {
            "intent": str(existing.get("intent") or f"{surface}.{operation}"),
            "method": str(existing.get("method") or operation),
            "target_ref": str(
                existing.get("target_ref")
                or f"handsfree.meta_glasses.mobile.mobile_orb_bridge.{operation}"
            ),
            "arguments": existing.get("arguments")
            if isinstance(existing.get("arguments"), dict)
            else payload,
            "confidence": float(existing.get("confidence") or 1.0),
        }

    return {
        "intent": _intent_from_payload(operation, payload, surface),
        "method": operation,
        "target_ref": f"handsfree.meta_glasses.mobile.mobile_orb_bridge.{operation}",
        "arguments": payload,
        "confidence": 1.0,
    }


def _logic_binding(operation: str, surface: str) -> dict[str, Any]:
    binding_id = f"hallucinate_app.remote_client.{surface}.{operation}"
    return {
        "binding_id": binding_id,
        "policy_bundle_ref": dict(CONTROL_SURFACE_POLICY_BUNDLE_REF),
        "compiled_policy_cid": CONTROL_SURFACE_COMPILED_POLICY_CID,
        "surface_ref": surface,
        "method_ref": operation,
        "norm_refs": [f"{binding_id}.transport_only"],
    }


def _interaction_envelope(
    *,
    operation: str,
    payload: dict[str, Any],
    emitted_at: str,
) -> dict[str, Any]:
    existing = payload.get("interaction_envelope")
    if isinstance(existing, dict) and existing.get("interaction_id"):
        normalized = _normalized_intent(operation, payload, _remote_surface(operation, payload))
        return {
            **existing,
            "normalized_intent": existing.get("normalized_intent") or normalized,
            "control_surface_contract_ref": existing.get("control_surface_contract_ref")
            or _control_surface_contract_ref(payload),
            "policy_bundle_ref": existing.get("policy_bundle_ref")
            or dict(CONTROL_SURFACE_POLICY_BUNDLE_REF),
            "compiled_policy_cid": existing.get("compiled_policy_cid")
            or CONTROL_SURFACE_COMPILED_POLICY_CID,
            "logic_bindings": existing.get("logic_bindings") or [],
        }

    surface = _remote_surface(operation, payload)
    actor_id = _remote_actor_id(payload)
    intent = _normalized_intent(operation, payload, surface)
    contract_ref = _control_surface_contract_ref(payload)
    logic_binding = _logic_binding(operation, surface)
    return {
        "interaction_id": _first_nonempty_string(
            payload.get("interaction_id"),
            payload.get("correlation_id"),
            payload.get("edge_session_id"),
        )
        or _local_sha256_cid("interaction", {"operation": operation, "payload": payload}),
        "surface": surface,
        "surface_event": _first_nonempty_string(payload.get("event_type"), operation) or operation,
        "raw_payload": payload,
        "normalized_intent": intent,
        "actor": {
            "type": "remote_client",
            "id": actor_id,
            "delegation_chain": [actor_id],
        },
        "context": _runtime_context(payload=payload, surface=surface, emitted_at=emitted_at),
        "control_surface_contract_ref": contract_ref,
        "policy_bundle_ref": dict(CONTROL_SURFACE_POLICY_BUNDLE_REF),
        "compiled_policy_cid": CONTROL_SURFACE_COMPILED_POLICY_CID,
        "logic_bindings": [logic_binding],
    }


def _canonical_outcome(value: Any) -> str:
    if value == "permit":
        return "allow"
    if value in {
        "allow",
        "deny",
        "require_confirmation",
        "defer",
        "rewrite",
        "fallback_surface",
        "rate_limit",
    }:
        return str(value)
    return "allow"


def _policy_decision(
    *,
    envelope: dict[str, Any],
    operation: str,
    emitted_at: str,
    outcome: str,
    reason: str,
) -> dict[str, Any]:
    existing = envelope.get("policy_decision")
    if isinstance(existing, dict) and existing.get("decision_id"):
        return existing

    normalized_intent = envelope["normalized_intent"]
    policy_ref = dict(CONTROL_SURFACE_POLICY_BUNDLE_REF)
    canonical_outcome = _canonical_outcome(outcome)
    explanation = (
        f"{reason} Remote clients transport the Hallucinate App mediation receipt "
        "and do not define or authorize a separate policy contract."
    )
    decision_seed = {
        "interaction_id": envelope["interaction_id"],
        "outcome": canonical_outcome,
        "operation": operation,
        "compiled_policy_cid": CONTROL_SURFACE_COMPILED_POLICY_CID,
    }
    return {
        "decision_id": _local_sha256_cid("control-surface-decision", decision_seed),
        "interaction_id": envelope["interaction_id"],
        "interaction_envelope": envelope,
        "outcome": canonical_outcome,
        "policy_bundle_ref": policy_ref,
        "compiled_policy_cid": CONTROL_SURFACE_COMPILED_POLICY_CID,
        "decided_at": emitted_at,
        "matched_norms": [
            {
                "norm_id": "remote_client_transport_receipt",
                "outcome": canonical_outcome,
                "priority": 100,
                "policy_bundle_ref": policy_ref,
                "logic_clause_refs": [
                    binding.get("binding_id")
                    for binding in envelope.get("logic_bindings", [])
                    if isinstance(binding, dict) and binding.get("binding_id")
                ],
                "guard_refs": [],
                "explanation": explanation,
            }
        ],
        "effects": [
            {
                "outcome": canonical_outcome,
                "method": normalized_intent["method"],
                "target_ref": normalized_intent["target_ref"],
                "arguments": normalized_intent["arguments"],
                "confirmation_required": canonical_outcome == "require_confirmation",
                "reason": explanation,
            }
        ],
        "frame_facts": [
            {
                "fact_id": _local_sha256_cid("fact", [envelope["interaction_id"], "surface"]),
                "kind": "surface",
                "subject": envelope["surface"],
                "predicate": "surface.id",
                "value": envelope["surface"],
                "attrs": {},
            },
            {
                "fact_id": _local_sha256_cid("fact", [envelope["interaction_id"], "event"]),
                "kind": "event",
                "subject": envelope["surface"],
                "predicate": "surface_event",
                "value": envelope["surface_event"],
                "attrs": {},
            },
            {
                "fact_id": _local_sha256_cid("fact", [envelope["interaction_id"], "method"]),
                "kind": "method",
                "subject": normalized_intent["target_ref"],
                "predicate": "intent.method",
                "value": normalized_intent["method"],
                "attrs": {},
            },
        ],
        "reasons": [explanation],
        "explanation": explanation,
        "confidence": normalized_intent["confidence"],
        "metadata": {
            "source": "hallucinate_app.control_surface_mediator.remote_client_envelope",
            "authorization_scope": "hallucinate_app_control_surface_contract",
            "remote_client_policy_contract": False,
            "transport_receipt": True,
            "schema_refs": CONTROL_SURFACE_SCHEMA_REFS,
        },
    }


def _mediation_receipt(
    *,
    envelope: dict[str, Any],
    decision: dict[str, Any],
    emitted_at: str,
    receipt_cid: str | None,
) -> dict[str, Any]:
    existing = envelope.get("mediation_receipt")
    if isinstance(existing, dict) and existing.get("receipt_id"):
        return existing

    effect = decision["effects"][0] if decision.get("effects") else {}
    invoked = decision.get("outcome") not in {
        "deny",
        "require_confirmation",
        "defer",
        "rate_limit",
    }
    receipt_id = receipt_cid or _local_sha256_cid(
        "mediation_receipt",
        {
            "interaction_id": envelope["interaction_id"],
            "decision_id": decision["decision_id"],
            "outcome": decision["outcome"],
        },
    )
    return {
        "receipt_id": receipt_id,
        "emitted_at": emitted_at,
        "control_surface_contract_ref": envelope["control_surface_contract_ref"],
        "interaction_envelope": envelope,
        "policy_decision": decision,
        "policy_refs": [
            {
                "policy_bundle_ref": decision["policy_bundle_ref"],
                "compiled_policy_cid": decision["compiled_policy_cid"],
                "matched_norm_refs": [
                    norm.get("norm_id")
                    for norm in decision.get("matched_norms", [])
                    if isinstance(norm, dict) and norm.get("norm_id")
                ],
            }
        ],
        "mediation_result": {
            "outcome": decision["outcome"],
            "invoked": invoked,
            "final_method": effect.get("method") or envelope["normalized_intent"]["method"],
            "final_target_ref": effect.get("target_ref")
            or envelope["normalized_intent"]["target_ref"],
            "confirmation_required": bool(effect.get("confirmation_required")),
            "rate_limit_key": effect.get("rate_limit_key"),
        },
        "explanation": decision["explanation"],
        "metadata": {
            "source": "hallucinate_app.control_surface_mediator.remote_client_envelope",
            "remote_client_policy_contract": False,
            "schema_refs": CONTROL_SURFACE_SCHEMA_REFS,
        },
    }


def _transported_control_surface_artifacts(payload: dict[str, Any]) -> dict[str, Any] | None:
    receipt = payload.get("mediation_receipt")
    if not isinstance(receipt, dict):
        return None
    envelope = receipt.get("interaction_envelope")
    decision = receipt.get("policy_decision")
    if not isinstance(envelope, dict) or not isinstance(decision, dict):
        return None
    normalized_intent = envelope.get("normalized_intent")
    if not isinstance(normalized_intent, dict):
        return None
    control_surface_contract_ref = (
        _first_nonempty_string(
            receipt.get("control_surface_contract_ref"),
            envelope.get("control_surface_contract_ref"),
            payload.get("control_surface_contract_ref"),
        )
        or CONTROL_SURFACE_CONTRACT_REF
    )
    return {
        "control_surface_contract_ref": control_surface_contract_ref,
        "interaction_envelope": envelope,
        "normalized_intent": normalized_intent,
        "policy_decision": decision,
        "mediation_receipt": receipt,
    }


def build_mobile_orb_control_surface_artifacts(
    *,
    operation: str,
    payload: Any,
    emitted_at: str,
    receipt_cid: str | None = None,
    outcome: str = "allow",
    reason: str = "Remote client artifact normalized to canonical control-surface envelope.",
) -> dict[str, Any]:
    """Build canonical Hallucinate App control-surface artifacts for remote clients."""
    payload_dict = _payload_dict(payload)
    transported = _transported_control_surface_artifacts(payload_dict)
    if transported is not None:
        return transported

    emitted_at = emitted_at or datetime.now(UTC).isoformat()
    envelope = _interaction_envelope(
        operation=operation,
        payload=payload_dict,
        emitted_at=emitted_at,
    )
    decision = _policy_decision(
        envelope=envelope,
        operation=operation,
        emitted_at=emitted_at,
        outcome=outcome,
        reason=reason,
    )
    receipt = _mediation_receipt(
        envelope=envelope,
        decision=decision,
        emitted_at=emitted_at,
        receipt_cid=receipt_cid,
    )
    return {
        "control_surface_contract_ref": envelope["control_surface_contract_ref"],
        "interaction_envelope": envelope,
        "normalized_intent": envelope["normalized_intent"],
        "policy_decision": decision,
        "mediation_receipt": receipt,
    }


def _normalize_method_signatures(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    normalized: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        method_name = _first_nonempty_string(item.get("name"))
        if not method_name:
            continue
        normalized.append({key: item[key] for key in sorted(item.keys()) if item[key] is not None})
    return normalized


def _normalize_error_definitions(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    normalized: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        error_name = _first_nonempty_string(item.get("name"))
        if not error_name:
            continue
        normalized.append({key: item[key] for key in sorted(item.keys()) if item[key] is not None})
    return normalized


def _normalize_descriptor_metadata(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}

    normalized = {
        "provider_name": _first_nonempty_string(value.get("provider_name")),
        "server_family": _first_nonempty_string(
            value.get("server_family"),
            value.get("mcp_server_family"),
        ),
        "tool_name": _first_nonempty_string(
            value.get("tool_name"),
            value.get("default_tool_name"),
            value.get("operation_tool_name"),
        ),
    }
    return {key: item for key, item in normalized.items() if isinstance(item, str) and item.strip()}


def _normalize_interface_descriptor(
    service_interface_cid: str,
    service_descriptor: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(service_descriptor, dict) or not service_descriptor:
        return None

    methods = _normalize_method_signatures(service_descriptor.get("methods"))
    compatibility = service_descriptor.get("compatibility")
    if not isinstance(compatibility, dict):
        compatibility = {}
    metadata = _normalize_descriptor_metadata(service_descriptor.get("metadata"))

    normalized = {
        "name": _first_nonempty_string(
            service_descriptor.get("name"),
            service_descriptor.get("service_id"),
            service_descriptor.get("serviceId"),
            service_interface_cid,
        )
        or service_interface_cid,
        "namespace": _first_nonempty_string(
            service_descriptor.get("namespace"),
            service_descriptor.get("service_namespace"),
            service_descriptor.get("serviceNamespace"),
            "handsfree.meta_glasses.mobile",
        )
        or "handsfree.meta_glasses.mobile",
        "version": _first_nonempty_string(service_descriptor.get("version"), "0.1.0") or "0.1.0",
        "methods": methods,
        "errors": _normalize_error_definitions(service_descriptor.get("errors")),
        "requires": list(service_descriptor.get("requires", []))
        if isinstance(service_descriptor.get("requires"), list)
        else [],
        "compatibility": {
            key: compatibility[key]
            for key in sorted(compatibility.keys())
            if compatibility[key] is not None
        },
    }
    if metadata:
        normalized["metadata"] = metadata
    return normalized


def _descriptor_cid(service_interface_cid: str, service_descriptor: dict[str, Any] | None) -> str:
    normalized_descriptor = _normalize_interface_descriptor(
        service_interface_cid,
        service_descriptor,
    )
    if normalized_descriptor is not None:
        return _local_sha256_cid("mcp-interface", normalized_descriptor)
    return service_interface_cid


def _descriptor_service_id(
    service_interface_cid: str,
    service_descriptor: dict[str, Any] | None,
) -> str:
    if not isinstance(service_descriptor, dict):
        return service_interface_cid
    return (
        _first_nonempty_string(
            service_descriptor.get("service_id"),
            service_descriptor.get("serviceId"),
            service_descriptor.get("name"),
            service_descriptor.get("namespace"),
        )
        or service_interface_cid
    )


def _descriptor_operation(
    requested_operation: str | None,
    service_descriptor: dict[str, Any] | None,
) -> str:
    if _first_nonempty_string(requested_operation):
        return requested_operation or "invoke"
    if isinstance(service_descriptor, dict):
        methods = service_descriptor.get("methods")
        if isinstance(methods, list):
            for method in methods:
                if isinstance(method, dict):
                    method_name = _first_nonempty_string(method.get("name"))
                    if method_name:
                        return method_name
    return "invoke"


def _build_orb_binding_metadata(
    request: MetaGlassesMobileOrbBindServiceRequest,
    binding_handle: str,
) -> dict[str, Any]:
    descriptor = (
        request.service_descriptor if isinstance(request.service_descriptor, dict) else None
    )
    normalized_descriptor = _normalize_interface_descriptor(
        request.service_interface_cid,
        descriptor,
    )
    descriptor_cid = _descriptor_cid(request.service_interface_cid, descriptor)
    service_id = _descriptor_service_id(request.service_interface_cid, descriptor)
    operation = _descriptor_operation(request.operation, descriptor)
    descriptor_metadata = _normalize_descriptor_metadata(
        descriptor.get("metadata") if descriptor else None
    )
    return {
        "handle": binding_handle,
        "interface_cid": request.service_interface_cid,
        "descriptor_cid": descriptor_cid,
        "service_id": service_id,
        "operation": operation,
        "transport": request.transport_preference,
        "transport_binding": {
            "transport": request.transport_preference,
            "service_id": service_id,
            "operation": operation,
            "metadata": {
                **descriptor_metadata,
                "descriptor_cid": descriptor_cid,
                "descriptor_available": descriptor is not None,
                "descriptor_kind": "mcp-idl" if normalized_descriptor is not None else None,
                "interface_descriptor": normalized_descriptor,
            },
        },
    }


def build_mobile_orb_policy_decision(reason: str) -> dict[str, Any]:
    """Build a canonical Hallucinate App policy decision for ORB bridge actions."""
    artifacts = build_mobile_orb_control_surface_artifacts(
        operation="bind_service",
        payload={"reason": reason},
        emitted_at="1970-01-01T00:00:00Z",
        reason=reason,
    )
    return artifacts["policy_decision"]


def build_mobile_orb_register_artifacts(
    *,
    request: MetaGlassesMobileOrbRegisterRequest,
    registered_at: str,
) -> tuple[str, str, dict[str, Any]]:
    """Build the stable IDs and stored record for an edge registration."""
    session_seed = {
        "edge_id": request.edge_id,
        "platform": request.platform,
        "device_id": request.device_id,
        "local_interface_cids": request.local_interface_cids,
    }
    edge_session_id = _local_sha256_cid("mobile-orb-edge", session_seed)
    payload = {
        **request.model_dump(),
        "edge_session_id": edge_session_id,
    }
    control_surface_artifacts = build_mobile_orb_control_surface_artifacts(
        operation="register_edge_capabilities",
        payload=payload,
        emitted_at=registered_at,
        reason="Mobile ORB edge registration normalized by Hallucinate App control-surface contract.",
    )
    return (
        edge_session_id,
        control_surface_artifacts["control_surface_contract_ref"],
        {
            **request.model_dump(),
            "edge_session_id": edge_session_id,
            "registered_at": registered_at,
            **control_surface_artifacts,
        },
    )


def build_mobile_orb_event_artifacts(
    *,
    request: MetaGlassesMobileOrbEventRequest,
) -> tuple[str, str, dict[str, Any]]:
    """Build the stable IDs and stored record for a glasses event."""
    payload = request.model_dump()
    event_cid = _local_sha256_cid("mobile-orb-event", payload)
    receipt_cid = _local_sha256_cid(
        "mobile-orb-receipt",
        {
            "operation": "publish_glasses_event",
            "event_cid": event_cid,
            "correlation_id": request.correlation_id,
        },
    )
    control_surface_artifacts = build_mobile_orb_control_surface_artifacts(
        operation="publish_glasses_event",
        payload={**payload, "event_cid": event_cid},
        emitted_at=request.observed_at or "",
        receipt_cid=receipt_cid,
        reason="Meta-glasses event normalized by Hallucinate App control-surface contract.",
    )
    return (
        event_cid,
        receipt_cid,
        {
            **payload,
            "event_cid": event_cid,
            "receipt_cid": receipt_cid,
            "transport_status": "received",
            **control_surface_artifacts,
        },
    )


def build_mobile_orb_bind_service_artifacts(
    *,
    request: MetaGlassesMobileOrbBindServiceRequest,
    bound_at: str,
) -> tuple[str, dict[str, Any], dict[str, Any]]:
    """Build the stable IDs, policy, and stored record for a service binding."""
    binding_handle = _local_sha256_cid(
        "mobile-orb-binding",
        {
            "edge_session_id": request.edge_session_id,
            "service_interface_cid": request.service_interface_cid,
            "operation": request.operation,
            "transport": request.transport_preference,
        },
    )
    control_surface_artifacts = build_mobile_orb_control_surface_artifacts(
        operation="bind_service",
        payload={**request.model_dump(), "binding_handle": binding_handle},
        emitted_at=bound_at,
        reason="Service descriptor binding normalized by Hallucinate App control-surface contract.",
    )
    policy_decision = control_surface_artifacts["policy_decision"]
    orb_binding = _build_orb_binding_metadata(request, binding_handle)
    return (
        binding_handle,
        policy_decision,
        {
            **request.model_dump(),
            "binding_handle": binding_handle,
            "policy_decision": policy_decision,
            **control_surface_artifacts,
            "orb_binding": orb_binding,
            "bound_at": bound_at,
        },
    )


def build_mobile_orb_invoke_receipt_cid(
    *,
    request: MetaGlassesMobileOrbInvokeServiceRequest,
) -> str:
    """Build the stable receipt CID for a service invocation."""
    return _local_sha256_cid(
        "mobile-orb-receipt",
        {
            "binding_handle": request.binding_handle,
            "operation": request.operation,
            "correlation_id": request.correlation_id,
            "arguments": request.arguments,
        },
    )


def build_mobile_orb_subscription_artifacts(
    *,
    request: MetaGlassesMobileOrbSubscribeServiceUpdatesRequest,
) -> tuple[str, str]:
    """Build the stable IDs for a service update subscription."""
    subscription_id = _local_sha256_cid(
        "mobile-orb-subscription",
        {
            "binding_handle": request.binding_handle,
            "operation": request.operation,
            "stream": request.stream,
            "correlation_id": request.correlation_id,
        },
    )
    receipt_cid = _local_sha256_cid("mobile-orb-receipt", request.model_dump())
    return subscription_id, receipt_cid


def build_mobile_orb_subscription_record(
    *,
    request: MetaGlassesMobileOrbSubscribeServiceUpdatesRequest,
    binding: dict[str, Any],
    subscription_id: str,
    receipt_cid: str,
    subscribed_at: str,
) -> dict[str, Any]:
    """Build the stored subscription record for service update routing."""
    generation_key = f"{request.binding_handle}:{request.operation}:{request.stream}"
    control_surface_artifacts = build_mobile_orb_control_surface_artifacts(
        operation="subscribe_service_updates",
        payload={
            **request.model_dump(),
            "subscription_id": subscription_id,
            "edge_session_id": binding.get("edge_session_id"),
        },
        emitted_at=subscribed_at,
        receipt_cid=receipt_cid,
        reason="Service update subscription normalized by Hallucinate App control-surface contract.",
    )
    return {
        **request.model_dump(),
        "subscription_id": subscription_id,
        "receipt_cid": receipt_cid,
        "generation_key": generation_key,
        "edge_session_id": binding.get("edge_session_id"),
        "service_interface_cid": binding.get("service_interface_cid"),
        "service_id": binding.get("orb_binding", {}).get("service_id")
        if isinstance(binding.get("orb_binding"), dict)
        else None,
        "orb_binding": binding.get("orb_binding"),
        "status": "active",
        "subscribed_at": subscribed_at,
        **control_surface_artifacts,
    }


def build_mobile_orb_dispatch_receipt_cid(
    *,
    request: MetaGlassesMobileOrbDispatchResponseRequest,
) -> str:
    """Build the stable receipt CID for a glasses response dispatch."""
    return _local_sha256_cid(
        "mobile-orb-receipt",
        {
            "operation": "dispatch_glasses_response",
            "correlation_id": request.correlation_id,
            "parent_receipt_cids": request.parent_receipt_cids,
            "render_targets": request.render_targets,
        },
    )


def build_mobile_orb_revoke_receipt_cid(
    *,
    request: MetaGlassesMobileOrbRevokeBindingRequest,
) -> str:
    """Build the stable receipt CID for a service binding revocation."""
    return _local_sha256_cid("mobile-orb-receipt", request.model_dump())
