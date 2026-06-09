"""Helpers for building Meta glasses mobile ORB responses.

These helpers keep the phone-edge ORB response shaping in one place so API
endpoints do not manually normalize display-widget actions, follow-up actions,
and spoken text.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from handsfree.meta_glasses_display_widget_contract import (
    DISPLAY_WIDGET_ACTION_CONTRACT,
    DISPLAY_WIDGET_ACTION_DEFINITIONS,
)
from handsfree.meta_glasses_mobile_orb_artifacts import (
    build_mobile_orb_control_surface_artifacts,
)
from handsfree.models import (
    MetaGlassesMobileOrbBindServiceRequest,
    MetaGlassesMobileOrbBindServiceResponse,
    MetaGlassesMobileOrbDispatchResponseRequest,
    MetaGlassesMobileOrbDispatchResponseResponse,
    MetaGlassesMobileOrbEventRequest,
    MetaGlassesMobileOrbEventResponse,
    MetaGlassesMobileOrbInvokeServiceRequest,
    MetaGlassesMobileOrbInvokeServiceResponse,
    MetaGlassesMobileOrbRegisterRequest,
    MetaGlassesMobileOrbRegisterResponse,
    MetaGlassesMobileOrbRevokeBindingRequest,
    MetaGlassesMobileOrbRevokeBindingResponse,
    MetaGlassesMobileOrbSubscribeServiceUpdatesRequest,
    MetaGlassesMobileOrbSubscribeServiceUpdatesResponse,
)

DISPLAY_WIDGET_DEFINITION_BY_ID = {
    definition["id"]: definition for definition in DISPLAY_WIDGET_ACTION_DEFINITIONS
}
DISPLAY_WIDGET_DEFINITION_BY_ACTION = {
    definition["action"]: definition for definition in DISPLAY_WIDGET_ACTION_DEFINITIONS
}
DISPLAY_WIDGET_DEFINITION_BY_OPERATION = {
    definition["operation"]: definition for definition in DISPLAY_WIDGET_ACTION_DEFINITIONS
}
DEFAULT_DISPLAY_WIDGET_DEFINITION = DISPLAY_WIDGET_DEFINITION_BY_OPERATION["render_widget"]


def _normalize_follow_up_actions(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _normalize_display_widget_action(value: Any) -> dict[str, Any] | None:
    return value if isinstance(value, dict) else None


def _normalize_spoken_text(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _local_sha256_cid(prefix: str, value: Any) -> str:
    digest = hashlib.sha256(_stable_json(value).encode("utf-8")).hexdigest()
    return f"sha256:{prefix}:{digest}"


def _without_none(value: dict[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if item is not None}


def _first_nonempty_string(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _control_surface_fields(artifacts: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(artifacts, dict):
        return {}
    return _without_none(
        {
            "control_surface_contract_ref": artifacts.get("control_surface_contract_ref"),
            "interaction_envelope": artifacts.get("interaction_envelope"),
            "normalized_intent": artifacts.get("normalized_intent"),
            "policy_decision": artifacts.get("policy_decision"),
            "mediation_receipt": artifacts.get("mediation_receipt"),
        }
    )


def _build_control_surface_artifacts(
    *,
    operation: str,
    payload: Any,
    receipt_cid: str | None = None,
    reason: str,
) -> dict[str, Any]:
    return build_mobile_orb_control_surface_artifacts(
        operation=operation,
        payload=payload,
        emitted_at=datetime.now(UTC).isoformat(),
        receipt_cid=receipt_cid,
        reason=reason,
    )


def _mediation_invoked(artifacts: dict[str, Any]) -> bool:
    receipt = artifacts.get("mediation_receipt") if isinstance(artifacts, dict) else None
    result = receipt.get("mediation_result") if isinstance(receipt, dict) else None
    return bool(result.get("invoked")) if isinstance(result, dict) else False


def _display_widget_definition_for(action: dict[str, Any]) -> dict[str, str]:
    raw_type = _first_nonempty_string(action.get("type"), action.get("id"))
    if raw_type and raw_type in DISPLAY_WIDGET_DEFINITION_BY_ID:
        return DISPLAY_WIDGET_DEFINITION_BY_ID[raw_type]

    raw_operation = _first_nonempty_string(action.get("operation"))
    if raw_operation and raw_operation in DISPLAY_WIDGET_DEFINITION_BY_OPERATION:
        return DISPLAY_WIDGET_DEFINITION_BY_OPERATION[raw_operation]

    raw_action = _first_nonempty_string(action.get("action"))
    if raw_action and raw_action in DISPLAY_WIDGET_DEFINITION_BY_ACTION:
        return DISPLAY_WIDGET_DEFINITION_BY_ACTION[raw_action]

    return DEFAULT_DISPLAY_WIDGET_DEFINITION


def _normalize_policy_decision(
    value: Any,
    reason: str,
    *,
    operation: str = "dispatch_glasses_response",
    payload: Any | None = None,
    receipt_cid: str | None = None,
) -> dict[str, Any]:
    if isinstance(value, dict):
        if value.get("decision_id") and isinstance(value.get("interaction_envelope"), dict):
            return value
        outcome = value.get("outcome")
        if outcome == "permit":
            outcome = "allow"
        if outcome not in {
            "allow",
            "deny",
            "require_confirmation",
            "defer",
            "rewrite",
            "fallback_surface",
            "rate_limit",
        }:
            outcome = "allow"
        reasons = value.get("reasons")
        if isinstance(reasons, str):
            reasons = [reasons]
        elif not isinstance(reasons, list):
            reasons = []
        return {
            **value,
            "outcome": outcome,
            "reasons": reasons or [reason],
            "source": value.get("source")
            or "hallucinate_app.control_surface_mediator.remote_client_envelope",
        }

    artifacts = _build_control_surface_artifacts(
        operation=operation,
        payload=payload or {"reason": reason},
        receipt_cid=receipt_cid,
        reason=reason,
    )
    return artifacts["policy_decision"]


def _normalize_display_widget_mobile_action(
    value: Any,
    *,
    correlation_id: str,
    receipt_cid: str,
    fallback: dict[str, Any] | None = None,
    policy_reason: str = "Display widget action generated by the mobile ORB bridge.",
) -> dict[str, Any] | None:
    action = _normalize_display_widget_action(value)
    if action is None:
        return None

    definition = _display_widget_definition_for(action)
    manifest = action.get("manifest") if isinstance(action.get("manifest"), dict) else None
    descriptor_cid = _first_nonempty_string(
        action.get("descriptor_cid"),
        action.get("interface_cid"),
        _local_sha256_cid("display-widget-interface", DISPLAY_WIDGET_ACTION_CONTRACT),
    )
    widget_id = _first_nonempty_string(
        action.get("widget_id"),
        action.get("widgetId"),
        manifest.get("widget_id") if manifest else None,
        "handsfree.mobile-orb.display-widget",
    )
    widget_cid = _first_nonempty_string(
        action.get("widget_cid"),
        action.get("widgetCid"),
        manifest.get("widget_cid") if manifest else None,
        _local_sha256_cid(
            "display-widget",
            {
                "widget_id": widget_id,
                "operation": definition["operation"],
                "manifest": manifest,
            },
        ),
    )
    action_fallback = (
        action.get("fallback") if isinstance(action.get("fallback"), dict) else fallback
    )
    control_surface_artifacts = _build_control_surface_artifacts(
        operation=definition["operation"],
        payload={**action, "correlation_id": correlation_id},
        receipt_cid=receipt_cid,
        reason=policy_reason,
    )

    return _without_none(
        {
            "contract": DISPLAY_WIDGET_ACTION_CONTRACT,
            "type": definition["id"],
            "action": definition["action"],
            "operation": definition["operation"],
            "descriptor_cid": descriptor_cid,
            "interface_cid": _first_nonempty_string(action.get("interface_cid"), descriptor_cid),
            "widget_id": widget_id,
            "widget_cid": widget_cid,
            "orb_receipt_cid": _first_nonempty_string(
                action.get("orb_receipt_cid"),
                action.get("receipt_cid"),
                receipt_cid,
            ),
            "policy_decision": _normalize_policy_decision(
                control_surface_artifacts.get("policy_decision"),
                policy_reason,
                operation=definition["operation"],
                payload=action,
                receipt_cid=receipt_cid,
            ),
            "control_surface_contract_ref": control_surface_artifacts.get(
                "control_surface_contract_ref"
            ),
            "interaction_envelope": control_surface_artifacts.get("interaction_envelope"),
            "normalized_intent": control_surface_artifacts.get("normalized_intent"),
            "mediation_receipt": control_surface_artifacts.get("mediation_receipt"),
            "correlation_id": _first_nonempty_string(
                action.get("correlation_id"),
                action.get("correlationId"),
                correlation_id,
            ),
            "request_id": _first_nonempty_string(action.get("request_id"), action.get("requestId")),
            "issued_at": _first_nonempty_string(action.get("issued_at"), action.get("issuedAt"))
            or datetime.now(UTC).isoformat(),
            "state": action.get("state"),
            "patch": action.get("patch"),
            "manifest": manifest,
            "focus": action.get("focus"),
            "activated_action_id": _first_nonempty_string(
                action.get("activated_action_id"),
                action.get("activatedActionId"),
                action.get("action_id"),
            ),
            "video": action.get("video"),
            "subscription": action.get("subscription"),
            "fallback": action_fallback,
        }
    )


def _display_widget_action_item(payload: dict[str, Any]) -> dict[str, Any]:
    definition = DISPLAY_WIDGET_DEFINITION_BY_ID.get(
        payload.get("type"),
        DEFAULT_DISPLAY_WIDGET_DEFINITION,
    )
    return {
        "id": definition["id"],
        "label": definition["label"],
        "phrase": definition["phrase"],
        "params": {
            "descriptor_cid": payload["descriptor_cid"],
            "widget_cid": payload["widget_cid"],
            "orb_receipt_cid": payload["orb_receipt_cid"],
            "policy_decision": payload["policy_decision"],
            "display_widget_action": payload,
        },
        "mobile_payload": payload,
    }


def _orb_binding_metadata(
    *,
    binding: dict[str, Any],
    request: MetaGlassesMobileOrbInvokeServiceRequest,
) -> dict[str, Any]:
    if isinstance(binding.get("orb_binding"), dict):
        return binding["orb_binding"]

    transport = binding.get("transport_preference") or binding.get("transport") or "mcp-server"
    service_interface_cid = binding["service_interface_cid"]
    service_id = binding.get("service_id") or service_interface_cid
    return {
        "handle": request.binding_handle,
        "interface_cid": service_interface_cid,
        "descriptor_cid": binding.get("descriptor_cid") or service_interface_cid,
        "service_id": service_id,
        "operation": request.operation,
        "transport": transport,
        "transport_binding": {
            "transport": transport,
            "service_id": service_id,
            "operation": request.operation,
            "metadata": {
                "descriptor_available": isinstance(binding.get("service_descriptor"), dict),
            },
        },
    }


def build_mobile_orb_register_response(
    *,
    request: MetaGlassesMobileOrbRegisterRequest,
    edge_session_id: str,
    control_surface_artifacts: dict[str, Any] | None = None,
) -> MetaGlassesMobileOrbRegisterResponse:
    """Build the phone edge registration response."""
    artifacts = control_surface_artifacts or _build_control_surface_artifacts(
        operation="register_edge_capabilities",
        payload={**request.model_dump(), "edge_session_id": edge_session_id},
        reason="Mobile ORB edge registration normalized by Hallucinate App control-surface contract.",
    )
    return MetaGlassesMobileOrbRegisterResponse(
        edge_session_id=edge_session_id,
        accepted_interface_cids=request.local_interface_cids,
        policy_cid=None,
        **_control_surface_fields(artifacts),
        expires_at=None,
    )


def build_mobile_orb_event_response(
    *,
    request: MetaGlassesMobileOrbEventRequest,
    event_cid: str,
    receipt_cid: str,
) -> MetaGlassesMobileOrbEventResponse:
    """Build the normalized glasses event publish response."""
    artifacts = _build_control_surface_artifacts(
        operation="publish_glasses_event",
        payload={**request.model_dump(), "event_cid": event_cid},
        receipt_cid=receipt_cid,
        reason="Meta-glasses event normalized by Hallucinate App control-surface contract.",
    )
    routed_operations = (
        ["bind_service", "invoke_service"]
        if request.event_type in {"captouch", "neural_input", "display_action"}
        else []
    )
    return MetaGlassesMobileOrbEventResponse(
        event_cid=event_cid,
        accepted=_mediation_invoked(artifacts),
        routed_operations=routed_operations,
        receipt_cid=receipt_cid,
        **_control_surface_fields(artifacts),
    )


def build_mobile_orb_bind_service_response(
    *,
    request: MetaGlassesMobileOrbBindServiceRequest,
    binding_handle: str,
    policy_decision: dict[str, Any],
    orb_binding: dict[str, Any] | None = None,
    control_surface_artifacts: dict[str, Any] | None = None,
) -> MetaGlassesMobileOrbBindServiceResponse:
    """Build a service binding response for the mobile ORB edge."""
    artifacts = control_surface_artifacts or _build_control_surface_artifacts(
        operation="bind_service",
        payload=request.model_dump(),
        reason="Service descriptor binding normalized by Hallucinate App control-surface contract.",
    )
    artifact_fields = _control_surface_fields(artifacts)
    canonical_policy_decision = artifact_fields.pop(
        "policy_decision",
        policy_decision,
    )
    return MetaGlassesMobileOrbBindServiceResponse(
        binding_handle=binding_handle,
        transport=request.transport_preference,
        granted_capabilities=[],
        policy_decision=canonical_policy_decision,
        orb_binding=orb_binding,
        **artifact_fields,
        expires_at=None,
    )


def build_mobile_orb_invoke_service_response(
    *,
    binding: dict[str, Any],
    request: MetaGlassesMobileOrbInvokeServiceRequest,
    receipt_cid: str,
) -> MetaGlassesMobileOrbInvokeServiceResponse:
    """Build a normalized receipt-backed response for a service invocation."""
    artifacts = _build_control_surface_artifacts(
        operation="invoke_service",
        payload=request.model_dump(),
        receipt_cid=receipt_cid,
        reason="Service invocation normalized by Hallucinate App control-surface contract.",
    )
    follow_up_actions = _normalize_follow_up_actions(request.arguments.get("follow_up_actions"))
    display_widget_action = _normalize_display_widget_mobile_action(
        request.arguments.get("display_widget_action"),
        correlation_id=request.correlation_id,
        receipt_cid=receipt_cid,
        fallback=request.arguments.get("fallback")
        if isinstance(request.arguments.get("fallback"), dict)
        else None,
        policy_reason="Service invocation display widget action permitted.",
    )
    if display_widget_action:
        action_item = _display_widget_action_item(display_widget_action)
        if not any(action.get("id") == action_item["id"] for action in follow_up_actions):
            follow_up_actions.append(action_item)
    spoken_text = _normalize_spoken_text(request.arguments.get("spoken_text"))
    return MetaGlassesMobileOrbInvokeServiceResponse(
        ok=True,
        service_result={
            "operation": request.operation,
            "arguments": request.arguments,
            "service_interface_cid": binding["service_interface_cid"],
            "orb_binding": _orb_binding_metadata(binding=binding, request=request),
        },
        output_refs=[receipt_cid],
        provenance_refs=[
            binding["service_interface_cid"],
            *request.parent_receipt_cids,
        ],
        receipt_cid=receipt_cid,
        **_control_surface_fields(artifacts),
        follow_up_actions=follow_up_actions,
        display_widget_action=display_widget_action,
        spoken_text=spoken_text,
    )


def build_mobile_orb_subscribe_response(
    *,
    request: MetaGlassesMobileOrbSubscribeServiceUpdatesRequest,
    subscription_id: str,
    receipt_cid: str,
    subscription: dict[str, Any] | None = None,
) -> MetaGlassesMobileOrbSubscribeServiceUpdatesResponse:
    """Build a service update subscription response."""
    artifacts = (
        _control_surface_fields(subscription)
        if isinstance(subscription, dict)
        else _control_surface_fields(
            _build_control_surface_artifacts(
                operation="subscribe_service_updates",
                payload=request.model_dump(),
                receipt_cid=receipt_cid,
                reason="Service update subscription normalized by Hallucinate App control-surface contract.",
            )
        )
    )
    return MetaGlassesMobileOrbSubscribeServiceUpdatesResponse(
        subscription_id=subscription_id,
        receipt_cid=receipt_cid,
        generation_key=f"{request.binding_handle}:{request.operation}:{request.stream}",
        **artifacts,
        subscription=subscription,
    )


def build_mobile_orb_dispatch_response(
    *,
    request: MetaGlassesMobileOrbDispatchResponseRequest,
    receipt_cid: str,
) -> MetaGlassesMobileOrbDispatchResponseResponse:
    """Build phone-local actions generated from a service invocation result."""
    artifacts = _build_control_surface_artifacts(
        operation="dispatch_glasses_response",
        payload=request.model_dump(),
        receipt_cid=receipt_cid,
        reason="Glasses response dispatch normalized by Hallucinate App control-surface contract.",
    )
    result = request.result
    display_widget_action = _normalize_display_widget_mobile_action(
        result.get("display_widget_action"),
        correlation_id=request.correlation_id,
        receipt_cid=receipt_cid,
        fallback=request.fallback,
        policy_reason="Display widget dispatch permitted by the mobile ORB bridge.",
    )
    dispatched_actions = _normalize_follow_up_actions(result.get("follow_up_actions"))
    if display_widget_action:
        action_item = _display_widget_action_item(display_widget_action)
        if not any(action.get("id") == action_item["id"] for action in dispatched_actions):
            dispatched_actions.append(action_item)
    return MetaGlassesMobileOrbDispatchResponseResponse(
        dispatched_actions=dispatched_actions,
        display_widget_action=display_widget_action,
        spoken_text=_normalize_spoken_text(result.get("spoken_text")),
        receipt_cid=receipt_cid,
        **_control_surface_fields(artifacts),
    )


def build_mobile_orb_revoke_binding_response(
    *,
    revoked: bool,
    receipt_cid: str,
    request: MetaGlassesMobileOrbRevokeBindingRequest | None = None,
) -> MetaGlassesMobileOrbRevokeBindingResponse:
    """Build a service binding revocation response."""
    artifacts = _build_control_surface_artifacts(
        operation="revoke_binding",
        payload=request.model_dump() if hasattr(request, "model_dump") else {"revoked": revoked},
        receipt_cid=receipt_cid,
        reason="Service binding revocation normalized by Hallucinate App control-surface contract.",
    )
    return MetaGlassesMobileOrbRevokeBindingResponse(
        revoked=revoked,
        receipt_cid=receipt_cid,
        **_control_surface_fields(artifacts),
    )
