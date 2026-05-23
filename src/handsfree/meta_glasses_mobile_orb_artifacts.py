"""Helpers for building Meta glasses mobile ORB request artifacts.

These helpers keep stable CID generation and stored ORB record construction out
of the API transport layer.
"""

from __future__ import annotations

import hashlib
import json
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
        normalized.append(
            {
                key: item[key]
                for key in sorted(item.keys())
                if item[key] is not None
            }
        )
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
        normalized.append(
            {
                key: item[key]
                for key in sorted(item.keys())
                if item[key] is not None
            }
        )
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
    return {
        key: item
        for key, item in normalized.items()
        if isinstance(item, str) and item.strip()
    }


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
    """Build the default policy decision for local ORB bridge actions."""
    payload = {
        "outcome": "permit",
        "reasons": [reason],
        "source": "handsfree-mobile-orb",
        "required_capabilities": [],
        "granted_capabilities": [],
    }
    return {
        **payload,
        "decision_cid": _local_sha256_cid("mobile-orb-policy-decision", payload),
    }


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
    policy_cid = _local_sha256_cid(
        "mobile-orb-policy",
        {
            "edge_session_id": edge_session_id,
            "accepted_interface_cids": request.local_interface_cids,
            "transport_preferences": request.transport_preferences,
        },
    )
    return (
        edge_session_id,
        policy_cid,
        {
            **request.model_dump(),
            "edge_session_id": edge_session_id,
            "policy_cid": policy_cid,
            "registered_at": registered_at,
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
    return (
        event_cid,
        receipt_cid,
        {
            **payload,
            "event_cid": event_cid,
            "receipt_cid": receipt_cid,
            "accepted": True,
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
    policy_decision = build_mobile_orb_policy_decision(
        "Service descriptor binding accepted."
    )
    orb_binding = _build_orb_binding_metadata(request, binding_handle)
    return (
        binding_handle,
        policy_decision,
        {
            **request.model_dump(),
            "binding_handle": binding_handle,
            "policy_decision": policy_decision,
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
