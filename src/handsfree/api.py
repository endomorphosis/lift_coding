"""FastAPI backend for HandsFree Dev Companion.

This implementation combines webhook handling with comprehensive API endpoints.
"""

__all__ = ["app", "get_db", "FIXTURE_USER_ID"]

import base64
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Query, Request, status
from fastapi.responses import FileResponse, JSONResponse, Response

from handsfree.audio_fetch import fetch_audio_data
from handsfree.ai import (
    build_ai_backend_policy_history_report,
    AIRequestContext,
    AICapabilityRequest,
    build_ai_backend_policy_report,
    build_policy_resolution,
    build_api_execute_response,
    discover_failure_history_cids,
    execute_ai_request,
    resolve_policy_workflow,
)
from handsfree.actions import (
    DirectActionRequest,
    execute_confirmed_action,
    process_direct_action_request,
    process_direct_action_request_detailed,
)
from handsfree.auth import FIXTURE_USER_ID, CurrentUser
from handsfree.agents.results_views import resolve_result_query
from handsfree.image_fetch import fetch_image_data
from handsfree.commands.intent_parser import IntentParser
from handsfree.commands.pending_actions import PendingActionManager, RedisPendingActionManager
from handsfree.commands.profiles import Profile as CommandProfile, ProfileConfig
from handsfree.commands.router import CommandRouter
from handsfree.db import init_db
from handsfree.db.action_logs import write_action_log
from handsfree.db.ai_backend_policy_snapshots import (
    get_ai_backend_policy_snapshots,
    store_ai_backend_policy_snapshot,
)
from handsfree.db.ai_history_index import store_ai_history_record
from handsfree.db.github_connections import (
    create_github_connection,
    get_github_connection,
    get_github_connections_by_user,
)
from handsfree.db.oauth_states import (
    generate_oauth_state,
    validate_and_consume_oauth_state,
)
from handsfree.db.notifications import create_notification
from handsfree.db.pending_actions import (
    create_pending_action,
    delete_pending_action,
    get_pending_action,
)
from handsfree.db.webhook_events import DBWebhookStore
from handsfree.github import GitHubProvider
from handsfree.handlers.inbox import handle_inbox_list
from handsfree.handlers.pr_summary import handle_pr_summarize
from handsfree.logging_utils import (
    clear_request_id,
    log_error,
    log_info,
    log_warning,
    set_request_id,
)
from handsfree.commands.intent_parser import ParsedIntent as RouterParsedIntent
from handsfree.models import (
    ActionResult,
    ActionCommandRequest,
    AIAccelerateGenerateAndStoreExecuteRequest,
    AIAcceleratedPRSummaryExecuteRequest,
    AIAcceleratedFailureExplainExecuteRequest,
    AIBackendPolicyHistoryReport,
    AIBackendPolicyReport,
    AIBackendPolicySnapshotsResponse,
    AIBackendPolicySnapshotResponse,
    AICapabilityContext,
    AICapabilityExecuteRequest,
    AICapabilityExecuteResponse,
    AICopilotExplainFailureExecuteRequest,
    AICopilotExplainPRExecuteRequest,
    AICopilotSummarizeDiffExecuteRequest,
    AIFailureRAGExplainExecuteRequest,
    AIFindSimilarFailuresExecuteRequest,
    AIPRRAGSummaryExecuteRequest,
    AIStoredOutputReadExecuteRequest,
    AgentTaskControlResponse,
    ApiKeyResponse,
    ApiKeysListResponse,
    AudioInput,
    CommentRequest,
    CommandRequest,
    CommandResponse,
    CommandStatus,
    ConfirmRequest,
    CreateApiKeyRequest,
    CreateApiKeyResponse,
    DevPeerChatConversationsResponse,
    DevPeerChatHistoryResponse,
    DevPeerChatHandsetHeartbeatRequest,
    DevPeerChatHandsetSessionResponse,
    DevPeerChatOutboxAckRequest,
    DevPeerChatOutboxAckResponse,
    DevPeerChatOutboxReleaseRequest,
    DevPeerChatOutboxReleaseResponse,
    DevPeerChatOutboxPromoteRequest,
    DevPeerChatOutboxPromoteResponse,
    DevPeerChatOutboxResponse,
    DevPeerChatSendRequest,
    DevPeerChatSendResponse,
    DevPeerEnvelopeRequest,
    DevPeerEnvelopeResponse,
    DevTransportSessionClearResponse,
    DevTransportSessionCursor,
    DevTransportSessionsResponse,
    CreateGitHubConnectionRequest,
    CreateNotificationSubscriptionRequest,
    CreateRepoSubscriptionRequest,
    DebugInfo,
    DependencyStatus,
    FollowOnTask,
    GitHubConnectionResponse,
    GitHubConnectionsListResponse,
    GitHubOAuthCallbackResponse,
    GitHubOAuthStartResponse,
    ImageInput,
    InboxItem,
    InboxItemType,
    InboxResponse,
    MergeRequest,
    NotificationSubscriptionResponse,
    NotificationSubscriptionsListResponse,
    ParsedIntent,
    PrivacyMode,
    Profile,
    RepoSubscriptionResponse,
    RepoSubscriptionsListResponse,
    RequestReviewRequest,
    RerunChecksRequest,
    StatusResponse,
    TextInput,
    TTSRequest,
    UICard,
)
from handsfree.mcp.catalog import get_capability_descriptor, get_provider_descriptor
from handsfree.models import (
    PendingAction as PydanticPendingAction,
)
from handsfree.policy import PolicyDecision, evaluate_action_policy
from handsfree.redis_client import get_redis_client
from handsfree.secrets import get_default_secret_manager
from handsfree.stt import get_stt_provider
from handsfree.ocr import get_ocr_provider
from handsfree.peer_chat import PeerChatSessionService
from handsfree.webhooks import (
    normalize_github_event,
    verify_github_signature,
)
from handsfree.transport.libp2p_bluetooth import (
    CHAT_PROTOCOL_ID,
    PeerEnvelope,
    PersistedTransportSessionCursor,
    encode_chat_message_payload,
    decode_chat_message_payload,
    decode_transport_message,
    decode_transport_envelope,
    decode_transport_payload,
    encode_transport_envelope,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = FastAPI(
    title="HandsFree Dev Companion API",
    version="1.0.0",
    description="API for hands-free developer assistant",
)

# Database connection (initialized lazily)
_db_conn = None

# In-memory storage (for backwards compatibility with existing tests)
pending_actions_memory: dict[str, dict[str, Any]] = {}
webhook_payloads: list[dict[str, Any]] = []
# In-memory storage
pending_actions: dict[str, dict[str, Any]] = {}
processed_commands: dict[str, CommandResponse] = {}
idempotency_store: dict[str, ActionResult] = {}
processed_ai_requests: dict[str, AICapabilityExecuteResponse] = {}
dev_peer_sessions: dict[str, str] = {}
dev_peer_chat_service = PeerChatSessionService(db_conn_factory=lambda: get_db())
_peer_transport_provider = None

FOLLOW_ON_TASK_INTENTS = {
    "agent.delegate",
    "agent.delegate.confirmed",
    "agent.result_pin",
    "agent.result_unpin",
    "agent.result_rerun",
    "agent.result_rerun_fetch",
    "agent.result_rerun_dataset",
    "agent.result_save_ipfs",
}

COMMAND_RESPONSE_EXAMPLES = {
    "task_spawn": {
        "summary": "Spawned MCP task",
        "value": {
            "status": "ok",
            "intent": {
                "name": "agent.result_rerun",
                "confidence": 1.0,
                "entities": {
                    "task_id": "task-9b2b1d9d",
                },
            },
            "spoken_text": "Workflow rerun requested.",
            "cards": [],
            "pending_action": None,
            "follow_on_task": {
                "task_id": "task-9b2b1d9d",
                "state": "running",
                "provider": "ipfs_accelerate_mcp",
                "provider_label": "IPFS Accelerate",
                "capability": "agentic_fetch",
                "summary": "IPFS Accelerate agentic fetch running.",
            },
        },
    },
    "needs_confirmation": {
        "summary": "Confirmation required",
        "value": {
            "status": "needs_confirmation",
            "intent": {
                "name": "pr.merge",
                "confidence": 1.0,
                "entities": {
                    "pr_number": 456,
                },
            },
            "spoken_text": "Ready to merge PR 456. Say confirm to proceed.",
            "cards": [],
            "pending_action": {
                "token": "conf-abc123xyz",
                "expires_at": "2026-01-17T01:00:00Z",
                "summary": "Merge PR #456 in owner/repo",
            },
        },
    },
}

CONFIRM_COMMAND_RESPONSE_EXAMPLES = {
    "needs_confirmation": COMMAND_RESPONSE_EXAMPLES["needs_confirmation"],
    "task_spawn": {
        "summary": "Confirmed action spawned MCP task",
        "value": {
            "status": "ok",
            "intent": {
                "name": "agent.delegate.confirmed",
                "confidence": 1.0,
                "entities": {
                    "task_id": "task-9b2b1d9d",
                },
            },
            "spoken_text": "IPFS Accelerate workflow created.",
            "cards": [],
            "pending_action": None,
            "follow_on_task": {
                "task_id": "task-9b2b1d9d",
                "state": "running",
                "provider": "ipfs_accelerate_mcp",
                "provider_label": "IPFS Accelerate",
                "capability": "agentic_fetch",
                "summary": "IPFS Accelerate agentic fetch running.",
            },
        },
    },
}

COMMAND_ERROR_EXAMPLES = {
    "invalid_request": {
        "summary": "Invalid request payload",
        "value": {
            "error": "validation_error",
            "message": "Request body failed schema validation",
        },
    },
    "invalid_action_id": {
        "summary": "Unsupported action ID",
        "value": {
            "error": "invalid_action_id",
            "message": "Unsupported action_id: unknown_action",
        },
    },
    "expired_pending_action": {
        "summary": "Expired confirmation token",
        "value": {
            "error": "expired",
            "message": "Pending action has expired",
        },
    },
}

# Webhook store (DB-backed, initialized lazily)
_webhook_store = None


def _extract_follow_on_task(
    *,
    intent_name: str,
    status: CommandStatus,
    entities: dict[str, Any],
    tool_calls: list[dict[str, Any]] | None = None,
) -> FollowOnTask | None:
    """Build explicit spawned-task metadata for task-creating command responses."""
    if status != CommandStatus.OK or intent_name not in FOLLOW_ON_TASK_INTENTS:
        return None

    task_id = entities.get("task_id")
    if not isinstance(task_id, str) or not task_id:
        return None

    state = entities.get("state") if isinstance(entities.get("state"), str) else None
    provider = entities.get("provider") if isinstance(entities.get("provider"), str) else None
    provider_label = (
        entities.get("provider_label") if isinstance(entities.get("provider_label"), str) else None
    )
    capability = None
    for capability_key in ("capability", "mcp_capability"):
        if isinstance(entities.get(capability_key), str):
            capability = entities[capability_key]
            break

    if isinstance(tool_calls, list):
        matching_call = next(
            (
                call
                for call in tool_calls
                if isinstance(call, dict) and call.get("task_id") == task_id
            ),
            None,
        )
        if matching_call is not None:
            if state is None and isinstance(matching_call.get("state"), str):
                state = matching_call["state"]
            if provider is None and isinstance(matching_call.get("provider"), str):
                provider = matching_call["provider"]
            if provider_label is None and isinstance(matching_call.get("provider_label"), str):
                provider_label = matching_call["provider_label"]
            if capability is None:
                for capability_key in ("capability", "mcp_capability"):
                    if isinstance(matching_call.get(capability_key), str):
                        capability = matching_call[capability_key]
                        break

    return _build_follow_on_task(
        task_id=task_id,
        state=state,
        provider=provider,
        provider_label=provider_label,
        capability=capability,
    )


def _humanize_identifier(identifier: str | None) -> str | None:
    if not isinstance(identifier, str) or not identifier.strip():
        return None
    return identifier.replace("_", " ").replace("-", " ").strip().title()


def _derive_provider_label(provider: str | None, provider_label: str | None = None) -> str | None:
    if isinstance(provider_label, str) and provider_label.strip():
        return provider_label.strip()
    if not isinstance(provider, str) or not provider.strip():
        return None
    descriptor = get_provider_descriptor(provider)
    if descriptor is not None:
        return descriptor.display_name
    return _humanize_identifier(provider)


def _derive_capability_label(capability: str | None) -> str | None:
    if not isinstance(capability, str) or not capability.strip():
        return None
    descriptor = get_capability_descriptor(capability)
    if descriptor is not None:
        return descriptor.title
    return _humanize_identifier(capability)


def _build_follow_on_task(
    *,
    task_id: str,
    state: str | None = None,
    provider: str | None = None,
    provider_label: str | None = None,
    capability: str | None = None,
) -> FollowOnTask:
    resolved_provider_label = _derive_provider_label(provider, provider_label)
    resolved_capability = capability if isinstance(capability, str) and capability.strip() else None
    capability_label = _derive_capability_label(resolved_capability)

    summary_parts: list[str] = []
    if resolved_provider_label:
        summary_parts.append(resolved_provider_label)
    if capability_label:
        summary_parts.append(capability_label.lower())
    summary_base = " ".join(summary_parts).strip() or "Task"
    summary = f"{summary_base} {state}.".strip() if state else f"{summary_base} created."

    return FollowOnTask(
        task_id=task_id,
        state=state,
        provider=provider,
        provider_label=resolved_provider_label,
        capability=resolved_capability,
        summary=summary,
    )


def _parsed_intent_from_action_id(
    action_id: str, params: dict[str, Any] | None = None
) -> RouterParsedIntent:
    """Translate a structured card action ID into a router intent."""
    params = params or {}
    action_map: dict[str, tuple[str, tuple[str, ...]]] = {
        "open_result": ("agent.result_open", ()),
        "show_result_details": ("agent.result_details", ()),
        "show_related_results": ("agent.result_related", ()),
        "save_result_to_ipfs": ("agent.result_save_ipfs", ()),
        "read_cid": ("agent.result_read", ("cid",)),
        "share_cid": ("agent.result_share", ("cid",)),
        "pin_result": ("agent.result_pin", ("cid", "mcp_preferred_execution_mode")),
        "pin_result_local": ("agent.result_pin", ("cid", "mcp_preferred_execution_mode")),
        "pin_result_remote": ("agent.result_pin", ("cid", "mcp_preferred_execution_mode")),
        "unpin_result": ("agent.result_unpin", ("cid", "mcp_preferred_execution_mode")),
        "unpin_result_local": ("agent.result_unpin", ("cid", "mcp_preferred_execution_mode")),
        "unpin_result_remote": ("agent.result_unpin", ("cid", "mcp_preferred_execution_mode")),
        "rerun_workflow": ("agent.result_rerun", ("mcp_preferred_execution_mode",)),
        "rerun_fetch_with_url": (
            "agent.result_rerun_fetch",
            ("mcp_seed_url", "mcp_preferred_execution_mode"),
        ),
        "rerun_dataset_search": (
            "agent.result_rerun_dataset",
            ("mcp_input", "mcp_preferred_execution_mode"),
        ),
    }
    resolved = action_map.get(action_id)
    if resolved is None:
        raise ValueError(f"Unsupported action_id: {action_id}")
    intent_name, allowed_keys = resolved
    entities = {key: params[key] for key in allowed_keys if key in params}
    return RouterParsedIntent(name=intent_name, confidence=1.0, entities=entities)


# Initialize command infrastructure
_intent_parser = IntentParser()

# Initialize pending action manager with Redis if available
_redis_client = get_redis_client()
if _redis_client is not None:
    logger.info("Using Redis-backed pending action manager")
    _pending_action_manager = RedisPendingActionManager(
        redis_client=_redis_client, default_expiry_seconds=60
    )
else:
    logger.info("Redis unavailable, using in-memory pending action manager")
    _pending_action_manager = PendingActionManager()

_command_router: CommandRouter | None = None
_github_provider = GitHubProvider()

# Mapping from handler item types to API model types
_INBOX_ITEM_TYPE_MAP = {
    "pr": InboxItemType.PR,
    "mention": InboxItemType.MENTION,
    "check": InboxItemType.CHECK,
    "agent": InboxItemType.AGENT,
}

_PROFILE_TO_COMMAND_PROFILE = {
    Profile.WORKOUT: CommandProfile.WORKOUT,
    Profile.KITCHEN: CommandProfile.KITCHEN,
    Profile.COMMUTE: CommandProfile.COMMUTE,
    Profile.DEFAULT: CommandProfile.DEFAULT,
}


def get_db():
    """Get or initialize database connection.

    Uses DUCKDB_PATH environment variable or defaults to data/handsfree.db.
    Tests set DUCKDB_PATH=:memory: in conftest.py for isolation.
    """
    global _db_conn
    if _db_conn is None:
        _db_conn = init_db()  # Uses get_db_path() from connection.py
    return _db_conn


def get_command_router() -> CommandRouter:
    """Get or initialize command router with database connection."""
    global _command_router
    if _command_router is None:
        db = get_db()
        _command_router = CommandRouter(
            _pending_action_manager, db_conn=db, github_provider=_github_provider
        )
    return _command_router


def get_db_webhook_store() -> DBWebhookStore:
    """Get the DB-backed webhook store instance."""
    global _webhook_store
    if _webhook_store is None:
        db = get_db()
        _webhook_store = DBWebhookStore(db)
    return _webhook_store


async def _execute_ai_capability_request(
    request: AICapabilityExecuteRequest,
    user_id: CurrentUser,
) -> AICapabilityExecuteResponse:
    """Execute a shared AI capability request through the unified AI contract."""
    try:
        policy_workflow, policy_capability_id = resolve_policy_workflow(
            workflow=request.workflow,
            capability_id=request.capability_id,
        )
        resolved_capability_id = policy_capability_id or request.resolve_capability_id()
        request.validate_execution_requirements()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_request",
                "message": str(exc),
            },
        ) from exc
    resolved_workflow = policy_workflow or request.resolve_workflow()
    if request.idempotency_key:
        from handsfree.db.idempotency_keys import get_idempotency_response

        db = get_db()
        cached_response = get_idempotency_response(db, request.idempotency_key)
        if cached_response:
            return AICapabilityExecuteResponse(**cached_response)

        if request.idempotency_key in processed_ai_requests:
            return processed_ai_requests[request.idempotency_key]

    command_profile = _PROFILE_TO_COMMAND_PROFILE.get(request.profile, CommandProfile.DEFAULT)
    profile_config = ProfileConfig.for_profile(command_profile)
    normalized_context = request.normalized_context()

    options = request.build_options_dict()
    if resolved_capability_id in {
        "github.check.failure_rag_explain",
        "github.check.accelerated_failure_explain",
    } and "github_provider" not in options:
        options["github_provider"] = _github_provider
    request_inputs = dict(request.inputs)
    if (
        "history_cids" not in request_inputs
        and resolved_capability_id in {
            "github.check.failure_rag_explain",
            "github.check.accelerated_failure_explain",
            "github.check.find_similar_failures",
        }
    ):
        auto_history_cids = discover_failure_history_cids(
            get_db(),
            user_id=user_id,
            repo=normalized_context.repo,
            pr_number=normalized_context.pr_number,
            workflow_name=normalized_context.workflow_name,
            check_name=normalized_context.check_name,
            failure_target=normalized_context.failure_target,
            failure_target_type=normalized_context.failure_target_type,
        )
        if auto_history_cids:
            request_inputs["history_cids"] = auto_history_cids

    ai_request = AICapabilityRequest(
        capability_id=resolved_capability_id,
        context=AIRequestContext(
            repo=normalized_context.repo,
            pr_number=normalized_context.pr_number,
            workflow_name=normalized_context.workflow_name,
            check_name=normalized_context.check_name,
            failure_target=normalized_context.failure_target,
            failure_target_type=normalized_context.failure_target_type,
            session_id=normalized_context.session_id,
            user_id=user_id,
        ),
        inputs=request_inputs,
        options=options,
    )
    result = execute_ai_request(ai_request, profile_config=profile_config)
    output = result.output if isinstance(result.output, dict) else {"value": result.output}

    response = build_api_execute_response(result)
    response.workflow = resolved_workflow
    response.policy_resolution = build_policy_resolution(
        requested_workflow=request.workflow,
        resolved_workflow=resolved_workflow,
        requested_capability_id=request.capability_id,
        resolved_capability_id=resolved_capability_id,
    )
    response.trace = dict(response.trace)
    response.trace["policy_resolution"] = response.policy_resolution.model_dump(mode="json")
    db = get_db()
    target_parts = []
    if normalized_context.repo:
        target_parts.append(normalized_context.repo)
    if normalized_context.pr_number is not None:
        target_parts.append(f"#{normalized_context.pr_number}")
    if normalized_context.failure_target:
        target_parts.append(str(normalized_context.failure_target))
    if not target_parts and "cid" in request.options:
        target_parts.append(str(request.options["cid"]))

    write_action_log(
        conn=db,
        user_id=user_id,
        action_type=f"ai.execute.{resolved_capability_id}",
        ok=result.ok,
        target=" ".join(target_parts) or None,
        request={
            "capability_id": resolved_capability_id,
            "workflow": resolved_workflow.value if resolved_workflow else None,
            "profile": request.profile.value,
            "context": normalized_context.model_dump(),
            "inputs": request_inputs,
            "options": options,
        },
        result=response.model_dump(),
        idempotency_key=request.idempotency_key,
    )

    if (
        resolved_capability_id in {
            "github.check.failure_rag_explain",
            "github.check.accelerated_failure_explain",
        }
        and isinstance(output, dict)
        and isinstance(output.get("ipfs_cid"), str)
        and output["ipfs_cid"].strip()
    ):
        store_ai_history_record(
            db,
            user_id=user_id,
            capability_id=resolved_capability_id,
            repo=output.get("repo") or normalized_context.repo,
            pr_number=output.get("pr_number") or normalized_context.pr_number,
            failure_target=output.get("failure_target") or normalized_context.failure_target,
            failure_target_type=output.get("failure_target_type")
            or normalized_context.failure_target_type,
            ipfs_cid=output["ipfs_cid"].strip(),
        )

    if request.idempotency_key:
        from handsfree.db.idempotency_keys import store_idempotency_key

        store_idempotency_key(
            conn=db,
            key=request.idempotency_key,
            user_id=user_id,
            endpoint="/v1/ai/execute",
            response_data=response.model_dump(),
        )
        processed_ai_requests[request.idempotency_key] = response

    return response


@app.post("/v1/ai/execute", response_model=AICapabilityExecuteResponse)
async def execute_ai_capability_endpoint(
    request: AICapabilityExecuteRequest,
    user_id: CurrentUser,
) -> AICapabilityExecuteResponse:
    """Execute a shared AI capability through the unified AI contract."""
    return await _execute_ai_capability_request(request, user_id)


@app.post("/v1/ai/copilot/explain-pr", response_model=AICapabilityExecuteResponse)
async def execute_ai_copilot_explain_pr_endpoint(
    request: AICopilotExplainPRExecuteRequest,
    user_id: CurrentUser,
) -> AICapabilityExecuteResponse:
    """Execute the typed Copilot PR explanation workflow."""
    return await _execute_ai_capability_request(request.to_execute_request(), user_id)


@app.post("/v1/ai/copilot/summarize-diff", response_model=AICapabilityExecuteResponse)
async def execute_ai_copilot_summarize_diff_endpoint(
    request: AICopilotSummarizeDiffExecuteRequest,
    user_id: CurrentUser,
) -> AICapabilityExecuteResponse:
    """Execute the typed Copilot diff summary workflow."""
    return await _execute_ai_capability_request(request.to_execute_request(), user_id)


@app.post("/v1/ai/copilot/explain-failure", response_model=AICapabilityExecuteResponse)
async def execute_ai_copilot_explain_failure_endpoint(
    request: AICopilotExplainFailureExecuteRequest,
    user_id: CurrentUser,
) -> AICapabilityExecuteResponse:
    """Execute the typed Copilot failure explanation workflow."""
    return await _execute_ai_capability_request(request.to_execute_request(), user_id)


@app.post("/v1/ai/rag-summary", response_model=AICapabilityExecuteResponse)
async def execute_ai_pr_rag_summary_endpoint(
    request: AIPRRAGSummaryExecuteRequest,
    user_id: CurrentUser,
) -> AICapabilityExecuteResponse:
    """Execute the typed PR RAG summary workflow."""
    return await _execute_ai_capability_request(request.to_execute_request(), user_id)


@app.post("/v1/ai/accelerated-rag-summary", response_model=AICapabilityExecuteResponse)
async def execute_ai_accelerated_pr_summary_endpoint(
    request: AIAcceleratedPRSummaryExecuteRequest,
    user_id: CurrentUser,
) -> AICapabilityExecuteResponse:
    """Execute the typed accelerated PR summary workflow."""
    return await _execute_ai_capability_request(request.to_execute_request(), user_id)


@app.post("/v1/ai/failure-rag-explain", response_model=AICapabilityExecuteResponse)
async def execute_ai_failure_rag_explain_endpoint(
    request: AIFailureRAGExplainExecuteRequest,
    user_id: CurrentUser,
) -> AICapabilityExecuteResponse:
    """Execute the typed failure RAG explanation workflow."""
    return await _execute_ai_capability_request(request.to_execute_request(), user_id)


@app.post("/v1/ai/accelerated-failure-explain", response_model=AICapabilityExecuteResponse)
async def execute_ai_accelerated_failure_explain_endpoint(
    request: AIAcceleratedFailureExplainExecuteRequest,
    user_id: CurrentUser,
) -> AICapabilityExecuteResponse:
    """Execute the typed accelerated failure explanation workflow."""
    return await _execute_ai_capability_request(request.to_execute_request(), user_id)


@app.post("/v1/ai/find-similar-failures", response_model=AICapabilityExecuteResponse)
async def execute_ai_find_similar_failures_endpoint(
    request: AIFindSimilarFailuresExecuteRequest,
    user_id: CurrentUser,
) -> AICapabilityExecuteResponse:
    """Execute the typed similar-failures retrieval workflow."""
    return await _execute_ai_capability_request(request.to_execute_request(), user_id)


@app.post("/v1/ai/read-stored-output", response_model=AICapabilityExecuteResponse)
async def execute_ai_read_stored_output_endpoint(
    request: AIStoredOutputReadExecuteRequest,
    user_id: CurrentUser,
) -> AICapabilityExecuteResponse:
    """Execute the typed stored-output read workflow."""
    return await _execute_ai_capability_request(request.to_execute_request(), user_id)


@app.post("/v1/ai/accelerate-generate-and-store", response_model=AICapabilityExecuteResponse)
async def execute_ai_accelerate_generate_and_store_endpoint(
    request: AIAccelerateGenerateAndStoreExecuteRequest,
    user_id: CurrentUser,
) -> AICapabilityExecuteResponse:
    """Execute the typed accelerated generation plus storage workflow."""
    return await _execute_ai_capability_request(request.to_execute_request(), user_id)


def _normalize_mcp_task_result(task: Any) -> dict[str, Any] | None:
    """Return a client-friendly MCP result summary for an agent task."""
    trace = task.trace or {}
    if not isinstance(trace, dict):
        return None

    envelope = trace.get("mcp_result_envelope")
    envelope = envelope if isinstance(envelope, dict) else None

    capability = trace.get("mcp_capability")
    provider_label = trace.get("provider_label")
    result_output = envelope.get("structured_output") if envelope else trace.get("mcp_result_output")
    result_preview = envelope.get("summary") if envelope else trace.get("mcp_result_preview")

    normalized: dict[str, Any] = {
        "provider_label": provider_label,
        "capability": capability,
        "preview": result_preview,
    }

    if isinstance(result_output, dict):
        if "status" in result_output:
            normalized["status"] = result_output["status"]
        if "message" in result_output:
            normalized["message"] = result_output["message"]
        if "task" in result_output and isinstance(result_output["task"], dict):
            normalized["remote_task"] = result_output["task"]

    cid = trace.get("mcp_cid")
    if not cid and isinstance(result_output, dict):
        cid = result_output.get("cid")
    if cid:
        normalized["cid"] = cid

    if capability == "dataset_discovery" and isinstance(result_output, dict):
        queries = result_output.get("expanded_queries")
        if isinstance(queries, list):
            normalized["dataset_queries"] = queries

    if capability == "agentic_fetch":
        seed_url = trace.get("mcp_seed_url")
        if seed_url:
            normalized["seed_urls"] = [seed_url]
        if isinstance(result_output, dict):
            target_terms = result_output.get("target_terms")
            if isinstance(target_terms, list):
                normalized["target_terms"] = target_terms
            seed_urls = result_output.get("seed_urls")
            if isinstance(seed_urls, list):
                normalized["seed_urls"] = seed_urls

    if capability == "ipfs_pin":
        pin_action = trace.get("mcp_pin_action")
        if pin_action:
            normalized["pin_action"] = pin_action

    if envelope:
        normalized["execution_mode"] = envelope.get("execution_mode")
        normalized["status"] = envelope.get("status", normalized.get("status"))
        artifact_refs = envelope.get("artifact_refs")
        if isinstance(artifact_refs, dict):
            normalized["artifact_refs"] = artifact_refs
            cid = artifact_refs.get("result_cid")
            if cid and "cid" not in normalized:
                normalized["cid"] = cid
        follow_up_actions = envelope.get("follow_up_actions")
        if isinstance(follow_up_actions, list) and follow_up_actions:
            normalized["follow_up_actions"] = follow_up_actions

    if len(normalized) == 3 and not any(normalized.values()):
        return None
    return normalized


def _serialize_agent_task(task: Any) -> dict[str, Any]:
    """Serialize an AgentTask into API shape."""
    task_data = {
        "id": task.id,
        "state": task.state,
        "provider": task.provider,
        "description": task.instruction or "",
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
    }
    if task.target_type:
        task_data["target_type"] = task.target_type
    if task.target_ref:
        task_data["target_ref"] = task.target_ref
    if task.trace and isinstance(task.trace, dict):
        task_data["trace"] = task.trace
        if "pr_url" in task.trace:
            task_data["pr_url"] = task.trace["pr_url"]
        envelope = task.trace.get("mcp_result_envelope")
        envelope = envelope if isinstance(envelope, dict) else None
        if envelope and isinstance(envelope.get("summary"), str):
            task_data["result_preview"] = envelope["summary"]
        elif "mcp_result_preview" in task.trace:
            task_data["result_preview"] = task.trace["mcp_result_preview"]
        if envelope and "structured_output" in envelope:
            task_data["result_output"] = envelope.get("structured_output")
            task_data["result_envelope"] = envelope
            follow_up_actions = envelope.get("follow_up_actions")
            if isinstance(follow_up_actions, list):
                task_data["follow_up_actions"] = follow_up_actions
        elif "mcp_result_output" in task.trace:
            task_data["result_output"] = task.trace["mcp_result_output"]
    normalized_result = _normalize_mcp_task_result(task)
    if normalized_result is not None:
        task_data["result"] = normalized_result
    return task_data


def _resolve_effective_user_id(user_id: str, x_user_id_raw: str | None = None) -> str:
    """Resolve the effective user id, honoring dev-mode header override."""
    from handsfree.auth import get_auth_mode

    effective_user_id = user_id
    if get_auth_mode() == "dev" and x_user_id_raw:
        effective_user_id = x_user_id_raw
    return effective_user_id


def _normalize_user_id_for_lookup(user_id: str) -> str:
    """Normalize raw user ids to the UUID form stored in the DB."""
    from uuid import NAMESPACE_DNS, UUID, uuid5

    try:
        normalized_user_id = (
            str(UUID(user_id)) if "-" in user_id else str(uuid5(NAMESPACE_DNS, user_id))
        )
    except (ValueError, AttributeError):
        normalized_user_id = str(uuid5(NAMESPACE_DNS, user_id))
    return normalized_user_id


def _get_scoped_agent_task(conn: Any, task_id: str, user_id: str) -> Any:
    """Load a task and enforce user ownership."""
    from handsfree.db.agent_tasks import get_agent_task_by_id

    task = get_agent_task_by_id(conn=conn, task_id=task_id)
    if not task or task.user_id != _normalize_user_id_for_lookup(user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    return task


def _apply_task_result_view(
    task_data: dict[str, Any],
    result_view: str,
) -> dict[str, Any]:
    """Project task result fields for the requested response view."""
    if result_view == "normalized":
        task_data.pop("trace", None)
        task_data.pop("result_output", None)
        return task_data
    if result_view == "raw":
        task_data.pop("result", None)
        return task_data
    return task_data


def _filter_agent_tasks_for_results(
    tasks: list[Any],
    *,
    capability: str | None = None,
    results_only: bool = False,
) -> list[Any]:
    """Apply capability/result availability filtering to a task list."""
    if capability:
        tasks = [
            task for task in tasks
            if isinstance(task.trace, dict) and task.trace.get("mcp_capability") == capability
        ]
    if results_only:
        tasks = [
            task for task in tasks
            if task.state == "completed"
            and isinstance(task.trace, dict)
            and (
                task.trace.get("mcp_result_envelope") is not None
                or task.trace.get("mcp_result_preview") is not None
                or task.trace.get("mcp_result_output") is not None
            )
        ]
    return tasks


def _paginate_task_list(tasks: list[Any], *, limit: int, offset: int) -> tuple[list[Any], bool]:
    """Paginate an in-memory task list and return page plus has_more flag."""
    has_more = len(tasks) > offset + limit
    return tasks[offset: offset + limit], has_more


def _latest_tasks_by_result_key(tasks: list[Any]) -> list[Any]:
    """Keep only the first task for each provider/capability combination."""
    latest: list[Any] = []
    seen: set[tuple[str, str | None]] = set()
    for task in tasks:
        trace = task.trace if isinstance(task.trace, dict) else {}
        key = (task.provider, trace.get("mcp_capability"))
        if key in seen:
            continue
        seen.add(key)
        latest.append(task)
    return latest


def _summarize_result_tasks(tasks: list[Any]) -> dict[str, Any]:
    """Build aggregate counts for a filtered result task set."""
    by_provider: dict[str, int] = {}
    by_capability: dict[str, int] = {}
    for task in tasks:
        by_provider[task.provider] = by_provider.get(task.provider, 0) + 1
        trace = task.trace if isinstance(task.trace, dict) else {}
        capability = trace.get("mcp_capability")
        if isinstance(capability, str) and capability:
            by_capability[capability] = by_capability.get(capability, 0) + 1
    return {
        "total_results": len(tasks),
        "by_provider": by_provider,
        "by_capability": by_capability,
    }


def get_peer_transport():
    """Get or initialize the configured peer transport provider."""
    global _peer_transport_provider
    if _peer_transport_provider is None:
        from handsfree.transport import get_transport_provider

        _peer_transport_provider = get_transport_provider()
    return _peer_transport_provider


def _serialize_transport_session_cursor(
    cursor: PersistedTransportSessionCursor,
) -> DevTransportSessionCursor:
    return DevTransportSessionCursor(
        peer_id=cursor.peer_id,
        peer_ref=cursor.peer_ref,
        session_id=cursor.session_id,
        resume_token=cursor.resume_token,
        capabilities=list(cursor.capabilities),
        updated_at_ms=cursor.updated_at_ms,
    )


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/v1/status", response_model=StatusResponse)
def get_status():
    """Get service status endpoint.

    Returns lightweight status information for the mobile app and simulator,
    including service health, version, timestamp, and dependency readiness.
    Does not expose sensitive configuration values.
    """
    # Check DuckDB connection status
    dependencies = []

    try:
        db = get_db()
        # Simple check to see if DB is accessible
        db.execute("SELECT 1").fetchone()
        dependencies.append(
            DependencyStatus(
                name="duckdb",
                status="ok",
                message="Database connection healthy",
            )
        )
    except Exception as e:
        logger.warning("DuckDB health check failed: %s", e)
        dependencies.append(
            DependencyStatus(
                name="duckdb",
                status="unavailable",
                message="Database connection failed",
            )
        )

    # Overall status: ok if all critical dependencies are ok, degraded otherwise
    overall_status = "ok"
    if any(dep.status == "unavailable" for dep in dependencies):
        overall_status = "degraded"
    elif any(dep.status == "degraded" for dep in dependencies):
        overall_status = "degraded"

    return StatusResponse(
        status=overall_status,
        version=app.version,
        timestamp=datetime.now(UTC),
        dependencies=dependencies,
    )


@app.get("/v1/metrics")
def get_metrics():
    """Get observability metrics for the command flow.

    This endpoint is gated behind the HANDSFREE_ENABLE_METRICS environment variable.
    It returns in-memory metrics including command latency percentiles, intent counts,
    status counts, and confirmation outcomes.

    Returns:
        JSON with current metrics snapshot.

    Raises:
        404: If metrics are not enabled via HANDSFREE_ENABLE_METRICS=true
    """
    from handsfree.metrics import get_metrics_collector, is_metrics_enabled

    if not is_metrics_enabled():
        raise HTTPException(
            status_code=404,
            detail={
                "error": "not_found",
                "message": (
                    "Metrics endpoint not available. Set HANDSFREE_ENABLE_METRICS=true to enable."
                ),
            },
        )

    metrics = get_metrics_collector()
    snapshot = metrics.get_snapshot()

    return JSONResponse(content=snapshot)


@app.get("/simulator")
async def dev_simulator():
    """Serve the web-based dev simulator interface.

    This provides a user-friendly way to test the handsfree loop:
    - Record or upload audio
    - Call /v1/command endpoint
    - Display parsed intent and response
    - Call /v1/tts and play audio
    """
    simulator_path = Path(__file__).parent.parent.parent / "dev" / "simulator.html"
    if not simulator_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Simulator not found. Ensure dev/simulator.html exists.",
        )
    return FileResponse(simulator_path)


@app.post("/v1/webhooks/github", status_code=status.HTTP_202_ACCEPTED)
async def github_webhook(
    request: Request,
    x_github_event: str = Header(..., alias="X-GitHub-Event"),
    x_github_delivery: str = Header(..., alias="X-GitHub-Delivery"),
    x_hub_signature_256: str = Header(..., alias="X-Hub-Signature-256"),
) -> JSONResponse:
    """Handle GitHub webhook events.

    Verifies signature, checks for replay, stores event, and normalizes payload.

    Args:
        request: FastAPI request object
        x_github_event: GitHub event type header
        x_github_delivery: GitHub delivery ID header
        x_hub_signature_256: GitHub signature header

    Returns:
        202 Accepted response with event ID

    Raises:
        400 Bad Request if signature invalid or duplicate delivery
    """
    store = get_db_webhook_store()

    # Check for duplicate delivery (replay protection)
    if store.is_duplicate_delivery(x_github_delivery):
        log_warning(
            logger,
            "Duplicate delivery detected",
            delivery_id=x_github_delivery,
            event_type=x_github_event,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate delivery ID",
        )

    # Read raw body for signature verification
    body = await request.body()

    # Get webhook secret from environment (None in dev/test mode)
    from handsfree.webhooks import get_webhook_secret

    webhook_secret = get_webhook_secret()
    signature_ok = verify_github_signature(body, x_hub_signature_256, webhook_secret)

    if not signature_ok:
        log_error(
            logger,
            "Signature verification failed",
            delivery_id=x_github_delivery,
            event_type=x_github_event,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature",
        )

    # Parse payload
    try:
        payload = await request.json()
    except Exception as e:
        log_error(
            logger,
            "Failed to parse webhook payload",
            error=str(e),
            delivery_id=x_github_delivery,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        ) from e

    # Store raw event
    event_id = store.store_event(
        delivery_id=x_github_delivery,
        event_type=x_github_event,
        payload=payload,
        signature_ok=signature_ok,
    )

    # Get database connection once for all operations
    db = get_db()

    # Normalize event (if supported) and track processing status
    try:
        normalized = normalize_github_event(x_github_event, payload)
        if normalized:
            log_info(
                logger,
                "Normalized webhook event",
                event_type=x_github_event,
                action=normalized.get("action"),
                event_id=event_id,
            )

            # Process installation lifecycle events
            from handsfree.installation_lifecycle import process_installation_event

            event_type_normalized = normalized.get("event_type")
            if event_type_normalized in ("installation", "installation_repositories"):
                process_installation_event(db, normalized, payload)

            # Correlate PR events with agent tasks
            _correlate_pr_with_agent_tasks(normalized, payload)

            # Emit notification for normalized webhook events
            _emit_webhook_notification(normalized, payload)

            # Mark as successfully processed
            from handsfree.db.webhook_events import update_webhook_processing_status

            update_webhook_processing_status(db, event_id, processed_ok=True)
        else:
            # Event type not supported for normalization - not an error
            log_info(
                logger,
                "Webhook event not normalized (unsupported type/action)",
                event_type=x_github_event,
                event_id=event_id,
            )
    except Exception as e:
        # Normalization or notification emission failed
        log_error(
            logger,
            "Webhook processing failed",
            error=type(e).__name__,
            event_type=x_github_event,
            event_id=event_id,
        )
        # Store redacted error (no payload in error message)
        from handsfree.db.webhook_events import update_webhook_processing_status

        db = get_db()
        error_msg = f"{type(e).__name__}: normalization or notification failed"
        update_webhook_processing_status(
            db, event_id, processed_ok=False, processing_error=error_msg
        )

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={"event_id": event_id, "message": "Webhook accepted"},
    )


@app.post("/v1/webhooks/retry/{event_id}")
async def retry_webhook_processing(
    event_id: str,
) -> JSONResponse:
    """Retry processing a failed webhook event (dev-only endpoint).

    This endpoint retrieves a previously stored webhook event and retries
    normalization and notification emission. Useful for recovering from
    transient failures.

    Args:
        event_id: The webhook event ID to retry.

    Returns:
        200 OK with processing status.

    Raises:
        404: Event not found.
        403: Endpoint disabled (not in dev mode).
    """
    # Dev-only check
    from handsfree.auth import get_auth_mode

    if get_auth_mode() != "dev":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "forbidden",
                "message": "Retry endpoint is only available in dev mode",
            },
        )

    db = get_db()
    from handsfree.db.webhook_events import (
        get_webhook_event_by_id,
        update_webhook_processing_status,
    )

    # Retrieve the event
    event = get_webhook_event_by_id(db, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "not_found",
                "message": f"Webhook event {event_id} not found",
            },
        )

    # Retry normalization and notification
    try:
        normalized = normalize_github_event(event.event_type, event.payload)
        if normalized:
            log_info(
                logger,
                "Retried webhook normalization",
                event_type=event.event_type,
                action=normalized.get("action"),
                event_id=event_id,
            )
            # Emit notification
            _emit_webhook_notification(normalized, event.payload)

            # Mark as successfully processed
            update_webhook_processing_status(db, event_id, processed_ok=True)

            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "event_id": event_id,
                    "status": "success",
                    "message": "Webhook processed successfully",
                },
            )
        else:
            # Event type not supported
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "event_id": event_id,
                    "status": "skipped",
                    "message": "Event type not supported for normalization",
                },
            )
    except Exception as e:
        # Processing failed again
        log_error(
            logger,
            "Webhook retry failed",
            error=type(e).__name__,
            event_type=event.event_type,
            event_id=event_id,
        )
        error_msg = f"{type(e).__name__}: retry normalization or notification failed"
        update_webhook_processing_status(
            db, event_id, processed_ok=False, processing_error=error_msg
        )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "event_id": event_id,
                "status": "failed",
                "message": error_msg,
            },
        )


@app.post("/v1/dev/audio")
async def dev_upload_audio(
    request: dict,
    user_id: CurrentUser,
) -> JSONResponse:
    """Upload audio bytes to the backend for local/mobile development (dev-only).

    This endpoint accepts base64-encoded audio bytes and saves them under a dev-only
    directory on the server, returning a `file://` URI.

    The returned URI can be used as `input.uri` when calling `POST /v1/command` with
    `input.type="audio"`, leveraging existing `fetch_audio_data()` support for `file://`.

    Security:
    - Only enabled when `HANDSFREE_AUTH_MODE=dev`.
    - Enforces a max decoded payload size.
    """

    from handsfree.auth import get_auth_mode

    if get_auth_mode() != "dev":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "forbidden",
                "message": "Dev audio upload is only available in dev mode",
            },
        )

    data_base64 = request.get("data_base64") or request.get("audio_base64")
    audio_format = str(request.get("format") or "m4a").lower()

    if not isinstance(data_base64, str) or not data_base64.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_request",
                "message": "Missing required field: data_base64 (or audio_base64)",
            },
        )

    allowed_exts = {"wav", "m4a", "mp3", "opus"}
    if audio_format not in allowed_exts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_request",
                "message": f"Unsupported audio format: {audio_format}",
            },
        )

    import base64
    import os
    import uuid
    from pathlib import Path

    max_size = int(os.getenv("HANDSFREE_DEV_AUDIO_MAX_BYTES", str(10 * 1024 * 1024)))
    dev_dir = Path(os.getenv("HANDSFREE_DEV_AUDIO_DIR", "data/dev_audio")).resolve()
    dev_dir.mkdir(parents=True, exist_ok=True)

    try:
        audio_bytes = base64.b64decode(data_base64, validate=True)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_request",
                "message": "data_base64 must be valid base64",
            },
        ) from e

    if len(audio_bytes) > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_request",
                "message": f"Audio too large (max {max_size} bytes)",
            },
        )

    file_id = uuid.uuid4().hex
    file_path = dev_dir / f"{file_id}.{audio_format}"
    file_path.write_bytes(audio_bytes)

    uri = f"file://{file_path}"
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "uri": uri,
            "bytes": len(audio_bytes),
            "format": audio_format,
            "user_id": user_id,
        },
    )


@app.post("/v1/dev/peer-envelope", response_model=DevPeerEnvelopeResponse)
async def dev_ingest_peer_envelope(
    request: DevPeerEnvelopeRequest,
    user_id: CurrentUser,
) -> DevPeerEnvelopeResponse:
    """Validate and ingest a dev peer envelope (dev-only).

    This endpoint is intended for mobile bring-up. It accepts a base64-encoded
    Bluetooth transport frame, validates it with the same transport codec used
    by the backend, and returns an ack frame for valid message envelopes.
    """

    from handsfree.auth import get_auth_mode

    if get_auth_mode() != "dev":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "forbidden",
                "message": "Dev peer envelope ingress is only available in dev mode",
            },
        )

    try:
        frame = base64.b64decode(request.frame_base64, validate=True)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_request",
                "message": "frame_base64 must be valid base64",
            },
        ) from exc

    try:
        envelope = decode_transport_envelope(frame)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_request",
                "message": str(exc),
            },
        ) from exc

    dev_peer_sessions[envelope.peer_id] = envelope.session_id

    protocol: str | None = None
    conversation_id: str | None = None
    payload_text: str | None = None
    payload_json: dict[str, Any] | None = None
    ack_frame_base64: str | None = None
    if envelope.kind == "message":
        protocol, payload_bytes = decode_transport_message(envelope.payload_b64)
        payload_text = payload_bytes.decode("utf-8", errors="replace")
        if protocol == CHAT_PROTOCOL_ID:
            try:
                payload_json = decode_chat_message_payload(payload_bytes)
                stored_message = dev_peer_chat_service.ingest_chat_payload(
                    envelope.peer_id, payload_json
                )
                conversation_id = stored_message.conversation_id
                payload_json = {
                    "conversation_id": stored_message.conversation_id,
                    "peer_id": stored_message.peer_id,
                    "sender_peer_id": stored_message.sender_peer_id,
                    "text": stored_message.text,
                    "timestamp_ms": stored_message.timestamp_ms,
                }
            except Exception:
                payload_json = None
        ack = PeerEnvelope(
            kind="ack",
            peer_id=envelope.peer_id,
            session_id=envelope.session_id,
            acked_message_id=envelope.message_id,
        )
        ack_frame_base64 = base64.b64encode(encode_transport_envelope(ack)).decode("ascii")

    return DevPeerEnvelopeResponse(
        accepted=True,
        peer_ref=request.peer_ref,
        peer_id=envelope.peer_id,
        kind=envelope.kind,
        session_id=envelope.session_id,
        message_id=envelope.message_id,
        protocol=protocol,
        conversation_id=conversation_id,
        payload_text=payload_text,
        payload_json=payload_json,
        ack_frame_base64=ack_frame_base64,
    )


@app.get("/v1/dev/peer-chat/{conversation_id}", response_model=DevPeerChatHistoryResponse)
async def dev_get_peer_chat_history(
    conversation_id: str,
    user_id: CurrentUser,
) -> DevPeerChatHistoryResponse:
    """Return normalized dev peer chat history for a conversation id (dev-only)."""

    from handsfree.auth import get_auth_mode

    if get_auth_mode() != "dev":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "forbidden",
                "message": "Dev peer chat history is only available in dev mode",
            },
        )

    if not conversation_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_request",
                "message": "conversation_id must be provided",
            },
        )

    return DevPeerChatHistoryResponse(
        conversation_id=conversation_id,
        messages=dev_peer_chat_service.list_messages(conversation_id),
    )


@app.get("/v1/dev/peer-chat", response_model=DevPeerChatConversationsResponse)
async def dev_list_peer_chat_conversations(
    user_id: CurrentUser,
    limit: int = Query(default=20, ge=1, le=100),
) -> DevPeerChatConversationsResponse:
    """Return recent normalized dev peer chat conversations (dev-only)."""

    from handsfree.auth import get_auth_mode

    if get_auth_mode() != "dev":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "forbidden",
                "message": "Dev peer chat conversations are only available in dev mode",
            },
        )

    return DevPeerChatConversationsResponse(
        conversations=dev_peer_chat_service.list_recent_conversations(limit=limit),
    )


@app.get("/v1/dev/transport-sessions", response_model=DevTransportSessionsResponse)
async def dev_list_transport_sessions(user_id: CurrentUser) -> DevTransportSessionsResponse:
    """Return persisted transport session cursors for transport diagnostics (dev-only)."""

    from handsfree.auth import get_auth_mode

    if get_auth_mode() != "dev":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "forbidden",
                "message": "Dev transport sessions are only available in dev mode",
            },
        )

    transport = get_peer_transport()
    list_cursors = getattr(transport, "list_persisted_session_cursors", None)
    cursors = list_cursors() if list_cursors is not None else []
    return DevTransportSessionsResponse(
        sessions=[_serialize_transport_session_cursor(cursor) for cursor in cursors],
    )


@app.delete(
    "/v1/dev/transport-sessions/{peer_id}",
    response_model=DevTransportSessionClearResponse,
)
async def dev_clear_transport_session(
    peer_id: str,
    user_id: CurrentUser,
) -> DevTransportSessionClearResponse:
    """Clear a persisted transport session cursor for transport diagnostics (dev-only)."""

    from handsfree.auth import get_auth_mode

    if get_auth_mode() != "dev":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "forbidden",
                "message": "Dev transport session clearing is only available in dev mode",
            },
        )

    if not peer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_request",
                "message": "peer_id must be provided",
            },
        )

    transport = get_peer_transport()
    clear_cursor = getattr(transport, "clear_persisted_session_cursor", None)
    cleared = bool(clear_cursor(peer_id)) if clear_cursor is not None else False
    return DevTransportSessionClearResponse(peer_id=peer_id, cleared=cleared)


@app.post("/v1/dev/peer-chat/send", response_model=DevPeerChatSendResponse)
async def dev_send_peer_chat(
    request: DevPeerChatSendRequest,
    user_id: CurrentUser,
) -> DevPeerChatSendResponse:
    """Send an outbound dev peer chat message via the configured transport."""

    from handsfree.auth import get_auth_mode
    from handsfree.peer_chat import build_conversation_id

    if get_auth_mode() != "dev":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "forbidden",
                "message": "Dev peer chat send is only available in dev mode",
            },
        )

    transport = get_peer_transport()
    local_identity = getattr(transport, "get_local_identity", lambda: None)()
    sender_peer_id = getattr(local_identity, "peer_id", None) or "local-dev-peer"
    conversation_id = request.conversation_id or build_conversation_id(request.peer_id, sender_peer_id)
    timestamp_ms = int(datetime.now(UTC).timestamp() * 1000)
    payload = encode_chat_message_payload(
        request.text,
        sender_peer_id=sender_peer_id,
        conversation_id=conversation_id,
        priority=request.priority,
        timestamp_ms=timestamp_ms,
    )

    try:
        if hasattr(transport, "send_protocol_message"):
            transport.send_protocol_message(request.peer_id, CHAT_PROTOCOL_ID, payload)
        else:
            transport.send(request.peer_id, payload)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "transport_unavailable",
                "message": str(exc),
            },
        ) from exc

    dev_peer_chat_service.ingest_chat_payload(
        request.peer_id,
        {
            "conversation_id": conversation_id,
            "sender_peer_id": sender_peer_id,
            "text": request.text,
            "priority": request.priority,
            "timestamp_ms": timestamp_ms,
        },
    )
    dev_peer_chat_service.queue_outbound_message(
        recipient_peer_id=request.peer_id,
        sender_peer_id=sender_peer_id,
        conversation_id=conversation_id,
        text=request.text,
        priority=request.priority,
        timestamp_ms=timestamp_ms,
    )

    return DevPeerChatSendResponse(
        accepted=True,
        peer_id=request.peer_id,
        sender_peer_id=sender_peer_id,
        protocol=CHAT_PROTOCOL_ID,
        conversation_id=conversation_id,
        text=request.text,
        priority=request.priority,
        transport_provider=type(transport).__name__,
        timestamp_ms=timestamp_ms,
    )


@app.get("/v1/dev/peer-chat/outbox/{peer_id}", response_model=DevPeerChatOutboxResponse)
async def dev_get_peer_chat_outbox(
    peer_id: str,
    user_id: CurrentUser,
    lease_ms: int | None = Query(default=None, ge=0, le=120000),
) -> DevPeerChatOutboxResponse:
    """Fetch queued outbound dev peer chat messages for a handset peer id."""

    from handsfree.auth import get_auth_mode

    if get_auth_mode() != "dev":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "forbidden",
                "message": "Dev peer chat outbox is only available in dev mode",
            },
        )

    if not peer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_request",
                "message": "peer_id must be provided",
            },
    )

    policy = dev_peer_chat_service.get_handset_delivery_policy(peer_id)
    summary = dev_peer_chat_service.summarize_outbound_messages(peer_id)
    preview_messages = dev_peer_chat_service.preview_outbound_messages(peer_id)
    messages = dev_peer_chat_service.fetch_outbound_messages(peer_id, lease_ms=lease_ms)
    dev_peer_chat_service.record_handset_heartbeat(peer_id, fetched_outbox=True)
    return DevPeerChatOutboxResponse(
        peer_id=peer_id,
        delivery_mode=policy["delivery_mode"],
        recommended_lease_ms=policy["recommended_lease_ms"],
        recommended_poll_ms=policy["recommended_poll_ms"],
        queued_total=summary["queued_total"],
        queued_urgent=summary["queued_urgent"],
        queued_normal=summary["queued_normal"],
        deliverable_now=summary["deliverable_now"],
        held_now=summary["held_now"],
        messages=messages,
        preview_messages=preview_messages,
    )


@app.get(
    "/v1/dev/peer-chat/outbox/{peer_id}/status",
    response_model=DevPeerChatOutboxResponse,
)
async def dev_get_peer_chat_outbox_status(
    peer_id: str,
    user_id: CurrentUser,
) -> DevPeerChatOutboxResponse:
    """Return queued outbox status without leasing or replay side effects."""

    from handsfree.auth import get_auth_mode

    if get_auth_mode() != "dev":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "forbidden",
                "message": "Dev peer chat outbox status is only available in dev mode",
            },
        )

    if not peer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_request",
                "message": "peer_id must be provided",
            },
        )

    policy = dev_peer_chat_service.get_handset_delivery_policy(peer_id)
    summary = dev_peer_chat_service.summarize_outbound_messages(peer_id)
    preview_messages = dev_peer_chat_service.preview_outbound_messages(peer_id)
    return DevPeerChatOutboxResponse(
        peer_id=peer_id,
        delivery_mode=policy["delivery_mode"],
        recommended_lease_ms=policy["recommended_lease_ms"],
        recommended_poll_ms=policy["recommended_poll_ms"],
        queued_total=summary["queued_total"],
        queued_urgent=summary["queued_urgent"],
        queued_normal=summary["queued_normal"],
        deliverable_now=summary["deliverable_now"],
        held_now=summary["held_now"],
        messages=[],
        preview_messages=preview_messages,
    )


@app.post(
    "/v1/dev/peer-chat/outbox/{peer_id}/ack",
    response_model=DevPeerChatOutboxAckResponse,
)
async def dev_ack_peer_chat_outbox(
    peer_id: str,
    request: DevPeerChatOutboxAckRequest,
    user_id: CurrentUser,
) -> DevPeerChatOutboxAckResponse:
    """Acknowledge handset-delivered dev peer chat outbox messages."""

    from handsfree.auth import get_auth_mode

    if get_auth_mode() != "dev":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "forbidden",
                "message": "Dev peer chat outbox ack is only available in dev mode",
            },
        )

    if not peer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_request",
                "message": "peer_id must be provided",
            },
        )

    dev_peer_chat_service.record_handset_heartbeat(peer_id, acknowledged_outbox=True)
    return DevPeerChatOutboxAckResponse(
        peer_id=peer_id,
        acknowledged_message_ids=dev_peer_chat_service.acknowledge_outbound_messages(
            peer_id,
            request.outbox_message_ids,
        ),
    )


@app.post(
    "/v1/dev/peer-chat/outbox/{peer_id}/release",
    response_model=DevPeerChatOutboxReleaseResponse,
)
async def dev_release_peer_chat_outbox(
    peer_id: str,
    request: DevPeerChatOutboxReleaseRequest,
    user_id: CurrentUser,
) -> DevPeerChatOutboxReleaseResponse:
    """Release leased outbox messages so they are deliverable again."""

    from handsfree.auth import get_auth_mode

    if get_auth_mode() != "dev":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "forbidden",
                "message": "Dev peer chat outbox release is only available in dev mode",
            },
        )

    if not peer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_request",
                "message": "peer_id must be provided",
            },
        )

    return DevPeerChatOutboxReleaseResponse(
        peer_id=peer_id,
        released_message_ids=dev_peer_chat_service.release_outbound_leases(
            peer_id,
            request.outbox_message_ids,
        ),
    )


@app.post(
    "/v1/dev/peer-chat/outbox/{peer_id}/promote",
    response_model=DevPeerChatOutboxPromoteResponse,
)
async def dev_promote_peer_chat_outbox(
    peer_id: str,
    request: DevPeerChatOutboxPromoteRequest,
    user_id: CurrentUser,
) -> DevPeerChatOutboxPromoteResponse:
    """Promote queued outbox messages to urgent priority."""

    from handsfree.auth import get_auth_mode

    if get_auth_mode() != "dev":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "forbidden",
                "message": "Dev peer chat outbox promote is only available in dev mode",
            },
        )

    if not peer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_request",
                "message": "peer_id must be provided",
            },
        )

    return DevPeerChatOutboxPromoteResponse(
        peer_id=peer_id,
        promoted_message_ids=dev_peer_chat_service.promote_outbound_messages(
            peer_id,
            request.outbox_message_ids,
        ),
    )


@app.post(
    "/v1/dev/peer-chat/handsets/{peer_id}/heartbeat",
    response_model=DevPeerChatHandsetSessionResponse,
)
async def dev_record_peer_chat_handset_heartbeat(
    peer_id: str,
    request: DevPeerChatHandsetHeartbeatRequest,
    user_id: CurrentUser,
) -> DevPeerChatHandsetSessionResponse:
    """Record a lightweight handset heartbeat for the dev peer chat relay."""

    from handsfree.auth import get_auth_mode

    if get_auth_mode() != "dev":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "forbidden",
                "message": "Dev peer chat handset heartbeat is only available in dev mode",
            },
        )

    if not peer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_request",
                "message": "peer_id must be provided",
            },
        )

    return DevPeerChatHandsetSessionResponse(
        **dev_peer_chat_service.record_handset_heartbeat(
            peer_id,
            display_name=request.display_name,
        )
    )


@app.get(
    "/v1/dev/peer-chat/handsets/{peer_id}",
    response_model=DevPeerChatHandsetSessionResponse,
)
async def dev_get_peer_chat_handset_session(
    peer_id: str,
    user_id: CurrentUser,
) -> DevPeerChatHandsetSessionResponse:
    """Get the currently observed handset relay session state."""

    from handsfree.auth import get_auth_mode

    if get_auth_mode() != "dev":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "forbidden",
                "message": "Dev peer chat handset status is only available in dev mode",
            },
        )

    session = dev_peer_chat_service.get_handset_session(peer_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "not_found",
                "message": f"No handset relay session found for {peer_id}",
            },
        )

    return DevPeerChatHandsetSessionResponse(**session)


@app.post(
    "/v1/command",
    response_model=CommandResponse,
    responses={
        200: {
            "description": "Command handled",
            "content": {
                "application/json": {
                    "examples": COMMAND_RESPONSE_EXAMPLES,
                }
            },
        },
        400: {
            "description": "Invalid request",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_request": COMMAND_ERROR_EXAMPLES["invalid_request"],
                    }
                }
            },
        },
    },
)
async def submit_command(
    request: CommandRequest,
    user_id: CurrentUser,
    x_session_id: str | None = Header(default=None, alias="X-Session-Id"),
    x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
) -> CommandResponse:
    """Submit a hands-free command.

    Args:
        request: Command request body
        user_id: User ID extracted from authentication (via CurrentUser dependency)
        x_session_id: Optional session identifier from X-Session-Id header
        x_request_id: Optional request ID for tracing (generates one if not provided)

    Returns:
        CommandResponse with status, intent, spoken text, etc.
    """
    # Record start time for latency measurement
    start_time = datetime.now(UTC)

    # Set up request ID for tracing
    set_request_id(x_request_id)

    # Determine session ID: prefer header, fallback to idempotency_key
    session_id = x_session_id or request.idempotency_key

    # user_id is provided via authentication dependency (CurrentUser)

    # Log the request with structured context
    log_info(
        logger,
        "Received command request",
        user_id=user_id,
        session_id=session_id or "none",
        idempotency_key=request.idempotency_key or "none",
        endpoint="/v1/command",
    )

    # Check idempotency - database first, then in-memory cache as optimization
    if request.idempotency_key:
        from handsfree.db.idempotency_keys import get_idempotency_response

        db = get_db()
        cached_response = get_idempotency_response(db, request.idempotency_key)
        if cached_response:
            # Reconstruct CommandResponse from cached data
            return CommandResponse(**cached_response)

        # Also check in-memory cache (backward compatibility)
        if request.idempotency_key in processed_commands:
            return processed_commands[request.idempotency_key]

    # Extract text from input (all branches either set text or return early)
    text: str
    if isinstance(request.input, TextInput):
        text = request.input.text.strip()
    elif isinstance(request.input, AudioInput):
        # Audio input - transcribe to text using STT
        try:
            # Fetch audio data from URI
            audio_data = fetch_audio_data(request.input.uri)

            # Get STT provider and transcribe
            stt_provider = get_stt_provider()
            text = stt_provider.transcribe(audio_data, request.input.format.value)

            log_info(
                logger,
                "Transcribed audio input",
                format=request.input.format.value,
                duration_ms=request.input.duration_ms,
                transcript_length=len(text),
                user_id=user_id,
            )
        except NotImplementedError as e:
            # STT is disabled
            clear_request_id()
            return CommandResponse(
                status=CommandStatus.ERROR,
                intent=ParsedIntent(name="error.stt_disabled", confidence=1.0),
                spoken_text=str(e),
                debug=DebugInfo(transcript="<audio input - STT disabled>"),
            )
        except (ValueError, FileNotFoundError, RuntimeError) as e:
            # Invalid audio format or URI
            log_error(logger, "Audio input error", error=str(e), user_id=user_id)
            clear_request_id()
            return CommandResponse(
                status=CommandStatus.ERROR,
                intent=ParsedIntent(name="error.audio_input", confidence=1.0),
                spoken_text=f"Could not process audio input: {str(e)}",
                debug=DebugInfo(transcript="<audio input - error>"),
            )
        except Exception as e:
            # Unexpected error during transcription
            log_error(
                logger,
                "Unexpected STT error",
                error=str(e),
                error_type=type(e).__name__,
                user_id=user_id,
            )
            clear_request_id()
            return CommandResponse(
                status=CommandStatus.ERROR,
                intent=ParsedIntent(name="error.stt_failed", confidence=1.0),
                spoken_text="Audio transcription failed. Please try again or use text input.",
                debug=DebugInfo(transcript="<audio input - transcription failed>"),
            )
    elif isinstance(request.input, ImageInput):
        # Image input - privacy enforcement
        privacy_mode = request.client_context.privacy_mode

        # In strict mode, reject image inputs
        if privacy_mode == PrivacyMode.STRICT:
            # Log the rejection (without URI unless debug mode)
            if request.client_context.debug:
                from handsfree.logging_utils import redact_secrets

                redacted_uri = redact_secrets(request.input.uri)
                log_info(
                    logger,
                    "Rejected image input in strict privacy mode",
                    user_id=user_id,
                    uri=redacted_uri,
                )
            else:
                log_info(
                    logger,
                    "Rejected image input in strict privacy mode",
                    user_id=user_id,
                )

            clear_request_id()
            return CommandResponse(
                status=CommandStatus.ERROR,
                intent=ParsedIntent(name="error.image_not_supported", confidence=1.0),
                spoken_text="Image input is not supported in strict privacy mode.",
                debug=DebugInfo(transcript="<image input - rejected by privacy mode>"),
            )

        # In balanced/debug mode, accept and process with OCR
        # Log acceptance without URI (unless debug mode with redaction)
        if request.client_context.debug:
            from handsfree.logging_utils import redact_secrets

            redacted_uri = redact_secrets(request.input.uri)
            log_info(
                logger,
                "Accepted image input for OCR processing",
                user_id=user_id,
                privacy_mode=privacy_mode.value,
                uri=redacted_uri,
                content_type=request.input.content_type,
            )
        else:
            log_info(
                logger,
                "Accepted image input for OCR processing",
                user_id=user_id,
                privacy_mode=privacy_mode.value,
            )

        # Fetch and process image with OCR
        try:
            # Fetch image data
            image_data = fetch_image_data(request.input.uri)

            # Get OCR provider and extract text
            ocr_provider = get_ocr_provider()
            text = ocr_provider.extract_text(
                image_data, request.input.content_type or "image/jpeg"
            )

            log_info(
                logger,
                "Extracted text from image input",
                content_type=request.input.content_type,
                transcript_length=len(text),
                user_id=user_id,
            )
        except NotImplementedError as e:
            # OCR is disabled
            clear_request_id()
            return CommandResponse(
                status=CommandStatus.ERROR,
                intent=ParsedIntent(name="error.ocr_disabled", confidence=1.0),
                spoken_text=str(e),
                debug=DebugInfo(transcript="<image input - OCR disabled>"),
            )
        except (ValueError, FileNotFoundError, RuntimeError) as e:
            # Invalid image format or URI
            log_error(logger, "Image input error", error=str(e), user_id=user_id)
            clear_request_id()
            return CommandResponse(
                status=CommandStatus.ERROR,
                intent=ParsedIntent(name="error.image_input", confidence=1.0),
                spoken_text="Could not process image input.",
                debug=DebugInfo(transcript="<image input - error>"),
            )
        except Exception as e:
            # Unexpected error during OCR
            log_error(
                logger,
                "Unexpected OCR error",
                error=str(e),
                error_type=type(e).__name__,
                user_id=user_id,
            )
            clear_request_id()
            return CommandResponse(
                status=CommandStatus.ERROR,
                intent=ParsedIntent(name="error.ocr_failed", confidence=1.0),
                spoken_text="Image OCR failed. Please try again or use text input.",
                debug=DebugInfo(transcript="<image input - OCR failed>"),
            )
    else:
        # Unknown input type
        clear_request_id()
        return CommandResponse(
            status=CommandStatus.ERROR,
            intent=ParsedIntent(name="error.unknown_input", confidence=1.0),
            spoken_text="Unknown input type.",
            debug=DebugInfo(transcript="<unknown input>"),
        )

    # Parse intent using the intent parser
    parsed_intent = _intent_parser.parse(text)

    # Store command in database if debug mode is enabled or auth mode is dev
    # Don't store debug.transcript commands themselves to avoid recursive transcript lookup
    from handsfree.auth import get_auth_mode
    from handsfree.db.commands import store_command

    db = get_db()
    should_store_transcript = request.client_context.debug or get_auth_mode() == "dev"

    # Store command with or without transcript based on debug/auth mode
    # Skip storing debug.transcript commands to avoid self-referential lookups
    # Determine input type
    if isinstance(request.input, TextInput):
        input_type = "text"
    elif isinstance(request.input, AudioInput):
        input_type = "audio"
    elif isinstance(request.input, ImageInput):
        input_type = "image"
    else:
        input_type = "unknown"

    if parsed_intent.name != "debug.transcript":
        store_command(
            conn=db,
            user_id=user_id,
            input_type=input_type,
            status="ok",  # Will be updated later if needed
            profile=request.profile.value,
            transcript=text if should_store_transcript else None,
            intent_name=parsed_intent.name,
            intent_confidence=parsed_intent.confidence,
            entities=parsed_intent.entities,
            store_transcript=should_store_transcript,
        )

    # Global voice follow-ups: allow saying "confirm" or "cancel" without a token.
    # This bridges the plan's system.confirm/system.cancel intents to the token-based
    # /v1/commands/confirm endpoint by selecting the latest pending action for the user.
    if parsed_intent.name in ("system.confirm", "system.cancel"):
        from handsfree.db.pending_actions import (
            delete_pending_action,
            get_latest_pending_action_for_user,
        )

        latest = get_latest_pending_action_for_user(db, user_id)
        if latest is None:
            return CommandResponse(
                status=CommandStatus.OK,
                intent=ParsedIntent(name=parsed_intent.name, confidence=1.0),
                spoken_text=(
                    "No pending action to confirm."
                    if parsed_intent.name == "system.confirm"
                    else "No pending action to cancel."
                ),
                debug=DebugInfo(transcript=text),
            )

        if parsed_intent.name == "system.confirm":
            # Delegate actual execution + exactly-once semantics to the confirm endpoint.
            return await confirm_command(
                ConfirmRequest(token=latest.token, idempotency_key=None),
                user_id=user_id,
            )

        # system.cancel
        delete_pending_action(db, latest.token)
        return CommandResponse(
            status=CommandStatus.OK,
            intent=ParsedIntent(name="system.cancel", confidence=1.0),
            spoken_text="Cancelled.",
            debug=DebugInfo(transcript=text),
        )

    # Special handling for pr.request_review - needs policy evaluation, rate limiting, audit logging
    # This bypasses the router because these intents require database operations and policy checks
    if parsed_intent.name == "pr.request_review":
        # Convert dataclass intent to Pydantic model for the handler
        pydantic_intent = ParsedIntent(
            name=parsed_intent.name,
            confidence=parsed_intent.confidence,
            entities=parsed_intent.entities,
        )
        response = await _handle_request_review_command(
            pydantic_intent, text, request.idempotency_key, user_id
        )
        # Store for idempotency (both persistent and in-memory)
        if request.idempotency_key:
            from handsfree.db.idempotency_keys import store_idempotency_key

            db = get_db()
            store_idempotency_key(
                db,
                key=request.idempotency_key,
                user_id=user_id,
                endpoint="/v1/command",
                response_data=response.model_dump(mode="json"),
                expires_in_seconds=86400,  # 24 hours
            )
            processed_commands[request.idempotency_key] = response
        return response

    # Route through CommandRouter for other intents
    router = get_command_router()
    router_response = router.route(
        intent=parsed_intent,
        profile=request.profile,
        session_id=session_id,  # Use session ID from header or idempotency key
        user_id=user_id,  # Pass user ID for policy evaluation
        idempotency_key=request.idempotency_key,  # Pass for audit logging
    )

    # For system commands (repeat, next), router returns complete response
    # Don't re-apply fixture handlers - just convert directly
    # Debug commands are also treated as system commands
    if parsed_intent.name.startswith("system.") or parsed_intent.name.startswith("debug."):
        response = _convert_router_response_direct(router_response, text, request.profile)
    else:
        # Convert router response to CommandResponse
        response = _convert_router_response_to_command_response(
            router_response,
            parsed_intent,
            text,
            request.profile,
            user_id,
            request.client_context.privacy_mode,
        )

        # For non-system commands, update the router's stored response with the enhanced version
        # This ensures system.repeat returns the full enriched response
        if session_id:
            router = get_command_router()
            # Store the enhanced response as a dict for the router's session state
            enhanced_dict = {
                "status": response.status.value,
                "intent": {
                    "name": response.intent.name,
                    "confidence": response.intent.confidence,
                    "entities": response.intent.entities,
                },
                "spoken_text": response.spoken_text,
                "cards": [card.model_dump() for card in response.cards] if response.cards else [],
            }
            if response.follow_on_task:
                enhanced_dict["follow_on_task"] = response.follow_on_task.model_dump()
            if response.pending_action:
                enhanced_dict["pending_action"] = {
                    "token": response.pending_action.token,
                    "expires_at": response.pending_action.expires_at.isoformat(),
                    "summary": response.pending_action.summary,
                }
            router._last_responses[session_id] = enhanced_dict

            # Also update navigation state with enhanced cards
            if response.cards:
                items = []
                for card in response.cards:
                    items.append(
                        {
                            "type": "card",
                            "intent_name": parsed_intent.name,
                            "data": card.model_dump(),
                        }
                    )
                router._navigation_state[session_id] = (items, 0)

    # Store for idempotency (both persistent and in-memory)
    if request.idempotency_key:
        from handsfree.db.idempotency_keys import store_idempotency_key

        db = get_db()
        store_idempotency_key(
            db,
            key=request.idempotency_key,
            user_id=user_id,
            endpoint="/v1/command",
            response_data=response.model_dump(mode="json"),
            expires_in_seconds=86400,  # 24 hours
        )
        processed_commands[request.idempotency_key] = response

    # Record metrics for observability
    from handsfree.metrics import get_metrics_collector

    end_time = datetime.now(UTC)
    latency_ms = (end_time - start_time).total_seconds() * 1000
    metrics = get_metrics_collector()
    metrics.record_command(
        intent_name=response.intent.name,
        status=response.status.value,
        latency_ms=latency_ms,
    )

    # Clear request ID from context
    clear_request_id()

    return response


@app.post(
    "/v1/commands/action",
    response_model=CommandResponse,
    responses={
        200: {
            "description": "Action handled",
            "content": {
                "application/json": {
                    "examples": COMMAND_RESPONSE_EXAMPLES,
                }
            },
        },
        400: {
            "description": "Invalid action request",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_action_id": COMMAND_ERROR_EXAMPLES["invalid_action_id"],
                        "invalid_request": COMMAND_ERROR_EXAMPLES["invalid_request"],
                    }
                }
            },
        }
    },
)
async def submit_action_command(
    request: ActionCommandRequest,
    user_id: CurrentUser,
    x_session_id: str | None = Header(default=None, alias="X-Session-Id"),
    x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
) -> CommandResponse:
    """Submit a structured action command using a card action ID."""
    start_time = datetime.now(UTC)
    set_request_id(x_request_id)
    session_id = x_session_id or request.idempotency_key

    log_info(
        logger,
        "Received action command request",
        user_id=user_id,
        session_id=session_id or "none",
        idempotency_key=request.idempotency_key or "none",
        action_id=request.action_id,
        endpoint="/v1/commands/action",
    )

    if request.idempotency_key:
        from handsfree.db.idempotency_keys import get_idempotency_response

        db = get_db()
        cached_response = get_idempotency_response(db, request.idempotency_key)
        if cached_response:
            return CommandResponse(**cached_response)
        if request.idempotency_key in processed_commands:
            return processed_commands[request.idempotency_key]

    try:
        parsed_intent = _parsed_intent_from_action_id(request.action_id, request.params)
    except ValueError as exc:
        clear_request_id()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_action_id",
                "message": str(exc),
            },
        ) from exc

    router = get_command_router()
    action_session_id = session_id
    embedded_card = request.params.get("card")
    task_id = request.params.get("task_id")
    notification_id = request.params.get("notification_id")
    if isinstance(embedded_card, dict):
        title = embedded_card.get("title")
        if not isinstance(title, str) or not title.strip():
            clear_request_id()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "invalid_card_context",
                    "message": "Embedded card context requires a title",
                },
            )
        action_session_id = action_session_id or "action-card-context"
        router.seed_navigation_card(action_session_id, embedded_card)
    elif isinstance(task_id, str) and task_id.strip():
        from handsfree.db.agent_tasks import get_agent_task_by_id
        from handsfree.commands.router import _build_result_card

        db = get_db()
        task = get_agent_task_by_id(db, task_id.strip())
        if task is None or task.user_id != user_id:
            clear_request_id()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "task_not_found",
                    "message": f"No accessible task found for {task_id}",
                },
            )
        action_session_id = action_session_id or f"action-task-{task.id}"
        router.seed_navigation_card(action_session_id, _build_result_card(task))
    elif isinstance(notification_id, str) and notification_id.strip():
        from handsfree.commands.router import _build_result_card
        from handsfree.db.agent_tasks import get_agent_task_by_id
        from handsfree.db.notifications import build_notification_card, get_notification

        db = get_db()
        notification = get_notification(db, user_id=user_id, notification_id=notification_id.strip())
        if notification is None:
            clear_request_id()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "notification_not_found",
                    "message": f"No accessible notification found for {notification_id}",
                },
            )

        seeded_card: dict[str, Any] | None = None
        metadata = notification.metadata or {}
        notification_task_id = metadata.get("task_id")
        if isinstance(notification_task_id, str) and notification_task_id.strip():
            task = get_agent_task_by_id(db, notification_task_id.strip())
            if task is not None and task.user_id == user_id:
                seeded_card = _build_result_card(task)

        if seeded_card is None:
            notification_card = build_notification_card(
                notification.id,
                notification.event_type,
                notification.message,
                notification.metadata,
            )
            if notification_card is not None:
                seeded_card = notification_card

        if seeded_card is None:
            clear_request_id()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "notification_context_unavailable",
                    "message": f"Notification {notification_id} does not include actionable result context",
                },
            )

        action_session_id = action_session_id or f"action-notification-{notification.id}"
        router.seed_navigation_card(action_session_id, seeded_card)

    router_response = router.route(
        intent=parsed_intent,
        profile=request.profile,
        session_id=action_session_id,
        user_id=user_id,
        idempotency_key=request.idempotency_key,
    )

    transcript = f"<action:{request.action_id}>"
    response = _convert_router_response_to_command_response(
        router_response,
        parsed_intent,
        transcript,
        request.profile,
        user_id,
        request.client_context.privacy_mode,
    )

    if action_session_id:
        enhanced_dict = {
            "status": response.status.value,
            "intent": {
                "name": response.intent.name,
                "confidence": response.intent.confidence,
                "entities": response.intent.entities,
            },
            "spoken_text": response.spoken_text,
            "cards": [card.model_dump() for card in response.cards] if response.cards else [],
        }
        if response.follow_on_task:
            enhanced_dict["follow_on_task"] = response.follow_on_task.model_dump()
        if response.pending_action:
            enhanced_dict["pending_action"] = {
                "token": response.pending_action.token,
                "expires_at": response.pending_action.expires_at.isoformat(),
                "summary": response.pending_action.summary,
            }
        router._last_responses[action_session_id] = enhanced_dict
        if response.cards:
            items = [
                {
                    "type": "card",
                    "intent_name": response.intent.name,
                    "data": card.model_dump(),
                }
                for card in response.cards
            ]
            router._navigation_state[action_session_id] = (items, 0)

    if request.idempotency_key:
        from handsfree.db.idempotency_keys import store_idempotency_key

        db = get_db()
        store_idempotency_key(
            db,
            key=request.idempotency_key,
            user_id=user_id,
            endpoint="/v1/commands/action",
            response_data=response.model_dump(mode="json"),
            expires_in_seconds=86400,
        )
        processed_commands[request.idempotency_key] = response

    from handsfree.metrics import get_metrics_collector

    end_time = datetime.now(UTC)
    latency_ms = (end_time - start_time).total_seconds() * 1000
    metrics = get_metrics_collector()
    metrics.record_command(
        intent_name=response.intent.name,
        status=response.status.value,
        latency_ms=latency_ms,
    )

    clear_request_id()
    return response


def _convert_router_response_direct(
    router_response: dict[str, Any],
    transcript: str,
    profile: Profile,
) -> CommandResponse:
    """Convert router response dict directly to CommandResponse without re-applying handlers.

    Used for system commands where router returns complete response that shouldn't be modified.

    Args:
        router_response: Response dict from CommandRouter
        transcript: Original text transcript
        profile: User profile

    Returns:
        CommandResponse object
    """
    # Extract basic fields
    status_str = router_response.get("status", "ok")
    status = CommandStatus(status_str)

    # Get intent from response
    intent_dict = router_response.get("intent", {})
    intent = ParsedIntent(
        name=intent_dict.get("name", "unknown"),
        confidence=intent_dict.get("confidence", 1.0),
        entities=intent_dict.get("entities", {}),
    )

    spoken_text = router_response.get("spoken_text", "")

    # Get cards if present
    cards: list[UICard] = []
    if "cards" in router_response and router_response["cards"]:
        cards = [UICard(**card) for card in router_response["cards"]]

    # Handle pending action
    pending_action = None
    if "pending_action" in router_response and router_response["pending_action"]:
        pa = router_response["pending_action"]
        # Parse expires_at if it's a string, otherwise use as-is
        expires_at = pa["expires_at"]
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        pending_action = PydanticPendingAction(
            token=pa["token"],
            expires_at=expires_at,
            summary=pa["summary"],
        )

    # Build debug info with profile metadata
    profile_config = ProfileConfig.for_profile(profile)
    debug = DebugInfo(
        transcript=transcript,
        profile_metadata={
            "profile": profile_config.profile.value,
            "max_spoken_words": profile_config.max_spoken_words,
            "speech_rate": profile_config.speech_rate,
        },
    )

    return CommandResponse(
        status=status,
        intent=intent,
        spoken_text=spoken_text,
        cards=cards,
        pending_action=pending_action,
        follow_on_task=_extract_follow_on_task(
            intent_name=intent.name,
            status=status,
            entities=intent.entities,
        ),
        debug=debug,
    )


def _convert_router_response_to_command_response(
    router_response: dict[str, Any],
    parsed_intent: Any,
    transcript: str,
    profile: Profile,
    user_id: str,
    privacy_mode: PrivacyMode = PrivacyMode.STRICT,
) -> CommandResponse:
    """Convert router response dict to CommandResponse model.

    Args:
        router_response: Response dict from CommandRouter
        parsed_intent: The parsed intent object
        transcript: Original text transcript
        profile: User profile
        user_id: User ID from header or fixture
        privacy_mode: Privacy mode for controlling data exposure

    Returns:
        CommandResponse object
    """
    # Extract basic fields
    status_str = router_response.get("status", "ok")
    status = CommandStatus(status_str)

    # Get intent from response or use parsed one
    intent_dict = router_response.get("intent", {})
    intent = ParsedIntent(
        name=intent_dict.get("name", parsed_intent.name),
        confidence=intent_dict.get("confidence", parsed_intent.confidence),
        entities=intent_dict.get("entities", parsed_intent.entities),
    )

    spoken_text = router_response.get("spoken_text", "")

    # Handle special intents with fixture-backed handlers
    cards: list[UICard] = []

    # Get profile config for applying truncation
    profile_config = ProfileConfig.for_profile(profile)

    if parsed_intent.name == "inbox.list":
        # Use fixture-backed inbox handler
        try:
            inbox_result = handle_inbox_list(
                provider=_github_provider,
                user="fixture-user",
                privacy_mode=privacy_mode,
                profile_config=profile_config,
            )
            items = inbox_result.get("items", [])
            spoken_text = inbox_result.get("spoken_text", spoken_text)

            # Convert items to cards
            cards = [
                UICard(
                    title=item["title"],
                    subtitle=f"{item['type']} - Priority {item['priority']}",
                    lines=[item["summary"]] if item.get("summary") else [],
                    deep_link=item.get("url"),
                )
                for item in items[:3]  # Limit to top 3
            ]
        except Exception:
            # Fallback to router's response
            pass

    elif parsed_intent.name == "pr.summarize" and status == CommandStatus.OK:
        # Use fixture-backed PR summary handler (only if not requiring confirmation)
        pr_number = parsed_intent.entities.get("pr_number")
        if pr_number and isinstance(pr_number, int):
            try:
                pr_result = handle_pr_summarize(
                    provider=_github_provider,
                    repo="fixture/repo",
                    pr_number=pr_number,
                    privacy_mode=privacy_mode,
                    profile_config=profile_config,
                )
                spoken_text = pr_result.get("spoken_text", spoken_text)

                # Create a card for the PR
                cards = [
                    UICard(
                        title=f"PR #{pr_number}: {pr_result.get('title', 'Unknown')}",
                        subtitle=f"By {pr_result.get('author', 'unknown')}",
                        lines=[
                            f"{pr_result.get('changed_files', 0)} files changed",
                            f"+{pr_result.get('additions', 0)} -{pr_result.get('deletions', 0)}",
                            f"State: {pr_result.get('state', 'unknown')}",
                        ],
                    )
                ]
            except Exception:
                # Fallback to router's response
                pass

    elif parsed_intent.name == "agent.delegate" and status == CommandStatus.OK:
        intent_entities = router_response.get("intent", {}).get("entities", {})
        if "task_id" not in intent_entities:
            # Fall back only when the router did not include task/task-result metadata.
            return _handle_agent_delegate(
                parsed_intent,
                transcript,
                "api",
                user_id,
                client_context=request.client_context.model_dump(mode="json"),
            )
        if intent_entities.get("state") != "completed":
            task_id = intent_entities.get("task_id", "")
            issue_number = intent_entities.get("issue_number")
            pr_number = intent_entities.get("pr_number")
            target_description = ""
            if issue_number:
                target_description = f" for issue #{issue_number}"
            elif pr_number:
                target_description = f" for PR #{pr_number}"
            spoken_text = (
                f"I've delegated the task{target_description} to an agent. "
                f"Task ID is {str(task_id)[:8]}. Say 'agent status' to check progress."
            )

    elif parsed_intent.name == "agent.status" and status == CommandStatus.OK:
        # Agent status commands - use old handler for backward compatibility
        return _handle_agent_status(transcript, "api", user_id)

    elif parsed_intent.name == "agent.pause" and status == CommandStatus.OK:
        # Agent pause commands
        return _handle_agent_pause(parsed_intent, transcript, "api", user_id)

    elif parsed_intent.name == "agent.resume" and status == CommandStatus.OK:
        # Agent resume commands
        return _handle_agent_resume(parsed_intent, transcript, "api", user_id)

    # Get cards from router response if not already set
    if not cards and "cards" in router_response:
        cards = [UICard(**card) for card in router_response["cards"]]

    # Handle pending action
    pending_action = None
    if "pending_action" in router_response and router_response["pending_action"]:
        pa = router_response["pending_action"]
        pending_action = PydanticPendingAction(
            token=pa["token"],
            expires_at=datetime.fromisoformat(pa["expires_at"]),
            summary=pa["summary"],
        )

    # Build debug info with profile metadata
    debug = DebugInfo(
        transcript=transcript,
        profile_metadata={
            "profile": profile_config.profile.value,
            "max_spoken_words": profile_config.max_spoken_words,
            "speech_rate": profile_config.speech_rate,
        },
    )
    tool_calls = router_response.get("debug", {}).get("tool_calls")
    if isinstance(tool_calls, list):
        debug.tool_calls = tool_calls

    return CommandResponse(
        status=status,
        intent=intent,
        spoken_text=spoken_text,
        cards=cards,
        pending_action=pending_action,
        follow_on_task=_extract_follow_on_task(
            intent_name=intent.name,
            status=status,
            entities=intent.entities,
            tool_calls=debug.tool_calls,
        ),
        debug=debug,
    )


@app.post(
    "/v1/commands/confirm",
    response_model=CommandResponse,
    responses={
        200: {
            "description": "Confirmation processed",
            "content": {
                "application/json": {
                    "examples": CONFIRM_COMMAND_RESPONSE_EXAMPLES,
                }
            },
        },
        404: {
            "description": "Pending action not found/expired",
            "content": {
                "application/json": {
                    "examples": {
                        "expired_pending_action": COMMAND_ERROR_EXAMPLES["expired_pending_action"],
                    }
                }
            },
        }
    },
)
async def confirm_command(
    request: ConfirmRequest,
    user_id: CurrentUser,
) -> CommandResponse:
    """Confirm a previously proposed side-effect action.

    Args:
        request: Confirmation request.
        user_id: User ID extracted from authentication (via CurrentUser dependency).
    """
    db = get_db()

    # Check idempotency - database first, then in-memory cache as optimization
    if request.idempotency_key:
        from handsfree.db.idempotency_keys import get_idempotency_response

        cached_response = get_idempotency_response(db, request.idempotency_key)
        if cached_response:
            # Reconstruct CommandResponse from cached data
            return CommandResponse(**cached_response)

        # Also check in-memory cache (backward compatibility)
        if request.idempotency_key in processed_commands:
            return processed_commands[request.idempotency_key]

    # Check PendingActionManager first (for intents from router)
    pending_action = _pending_action_manager.get(request.token)
    if pending_action:
        # Confirm and consume the action
        confirmed_action = _pending_action_manager.confirm(request.token)
        if confirmed_action:
            # Execute the intent that was pending
            intent_name = confirmed_action.intent_name
            entities = confirmed_action.entities

            # Map router intents to DB-backed action handlers for real execution
            if intent_name in ("pr.request_review", "pr.comment", "pr.merge"):
                action_type_map = {
                    "pr.request_review": "request_review",
                    "pr.comment": "comment",
                    "pr.merge": "merge",
                }
                response = execute_confirmed_action(
                    conn=db,
                    user_id=user_id,
                    action_type=action_type_map[intent_name],
                    action_payload=entities,
                    idempotency_key=request.idempotency_key,
                    via_router_token=True,
                )

            elif intent_name == "agent.delegate":
                # Execute agent delegation via agent service
                instruction = entities.get("instruction", "handle this")
                issue_num = entities.get("issue_number")
                pr_num = entities.get("pr_number")
                provider = entities.get("provider")
                
                # Check if agent service is available (requires DB connection)
                if not db:
                    response = CommandResponse(
                        status=CommandStatus.ERROR,
                        intent=ParsedIntent(
                            name=intent_name,
                            confidence=1.0,
                            entities=entities,
                        ),
                        spoken_text="Agent service not available. Database connection required.",
                    )
                else:
                    from handsfree.agents.service import AgentService
                    
                    agent_service = AgentService(db)
                    
                    target_type = None
                    target_ref = None
                    if issue_num:
                        target_type = "issue"
                        target_ref = f"#{issue_num}"
                    elif pr_num:
                        target_type = "pr"
                        target_ref = f"#{pr_num}"
                    
                    # Build trace with confirmation metadata
                    trace = {
                        "intent_name": intent_name,
                        "entities": entities,
                        "confirmed_at": datetime.now(UTC).isoformat(),
                        "via_router_token": True,
                    }
                    
                    try:
                        # Create and start the agent task
                        result = agent_service.delegate(
                            user_id=user_id,
                            instruction=instruction,
                            provider=provider,
                            target_type=target_type,
                            target_ref=target_ref,
                            trace=trace,
                        )
                        
                        spoken_text = result.get("spoken_text", "Agent task created.")
                        
                        # Write audit log
                        task_id = result.get("task_id")
                        write_action_log(
                            db,
                            user_id=user_id,
                            action_type="agent_delegate",
                            ok=True,
                            target=target_ref or "general",
                            request={"instruction": instruction, "confirmed": True},
                            result={
                                "status": "success",
                                "message": "Agent task created",
                                "via_confirmation": True,
                                "via_router_token": True,
                                "task_id": task_id,
                            },
                            idempotency_key=request.idempotency_key,
                        )
                        
                        response = CommandResponse(
                            status=CommandStatus.OK,
                            intent=ParsedIntent(
                                name="agent.delegate.confirmed",
                                confidence=1.0,
                                entities=entities,
                            ),
                            spoken_text=spoken_text,
                            follow_on_task=_build_follow_on_task(
                                task_id=result["task_id"],
                                state=result.get("state"),
                                provider=result.get("provider"),
                            ),
                        )
                    except (KeyboardInterrupt, SystemExit):
                        # Re-raise critical exceptions to avoid masking shutdown signals
                        raise
                    except Exception as e:
                        logger.error("Failed to delegate to agent: %s", e)
                        
                        write_action_log(
                            db,
                            user_id=user_id,
                            action_type="agent_delegate",
                            ok=False,
                            target=target_ref or "general",
                            request={"instruction": instruction, "confirmed": True},
                            result={
                                "status": "error",
                                "message": str(e),
                                "via_confirmation": True,
                                "via_router_token": True,
                            },
                            idempotency_key=request.idempotency_key,
                        )
                        
                        response = CommandResponse(
                            status=CommandStatus.ERROR,
                            intent=ParsedIntent(
                                name="agent.delegate.confirmed",
                                confidence=1.0,
                                entities=entities,
                            ),
                            spoken_text=f"Failed to create agent task: {str(e)}",
                        )
            
            else:
                # Unknown intent from router - log for debugging
                write_action_log(
                    db,
                    user_id=user_id,
                    action_type="unknown",
                    ok=False,
                    target="unknown",
                    request={"intent_name": intent_name, "entities": entities, "confirmed": True},
                    result={
                        "status": "error",
                        "message": f"Unknown action type: {intent_name}",
                        "via_confirmation": True,
                        "via_router_token": True,
                    },
                    idempotency_key=request.idempotency_key,
                )
                
                response = CommandResponse(
                    status=CommandStatus.ERROR,
                    intent=ParsedIntent(
                        name=intent_name,
                        confidence=1.0,
                        entities=entities,
                    ),
                    spoken_text=f"Unknown action type: {intent_name}",
                )

            # Store for idempotency (both persistent and in-memory)
            if request.idempotency_key:
                from handsfree.db.idempotency_keys import store_idempotency_key

                store_idempotency_key(
                    db,
                    key=request.idempotency_key,
                    user_id=user_id,
                    endpoint="/v1/commands/confirm",
                    response_data=response.model_dump(mode="json"),
                    expires_in_seconds=86400,  # 24 hours
                )
                processed_commands[request.idempotency_key] = response

            # Record confirmation metrics for observability
            from handsfree.metrics import get_metrics_collector

            metrics = get_metrics_collector()
            if response.status == CommandStatus.OK:
                metrics.record_confirmation("ok")
            else:
                metrics.record_confirmation("error")

            return response

    # Check if pending action exists in memory (legacy path)
    action_data = None
    is_memory_action = False

    if request.token in pending_actions_memory:
        action_data = pending_actions_memory[request.token]
        is_memory_action = True

        # Check expiration for memory actions
        if datetime.now(UTC) > action_data["expires_at"]:
            del pending_actions_memory[request.token]
            # Record not_found metric for expired action
            from handsfree.metrics import get_metrics_collector

            metrics = get_metrics_collector()
            metrics.record_confirmation("not_found")
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "expired",
                    "message": "Pending action has expired",
                },
            )

        action_type = action_data["action"]
        action_payload = action_data
    else:
        # Check database for pending action
        db_action = get_pending_action(db, request.token)

        if db_action is None:
            # Record not_found metric
            from handsfree.metrics import get_metrics_collector

            metrics = get_metrics_collector()
            metrics.record_confirmation("not_found")
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "not_found",
                    "message": "Pending action not found or expired",
                },
            )

        action_type = db_action.action_type
        action_payload = db_action.action_payload
        action_data = db_action

    # Execute the action based on type
    if action_type == "summarize_pr":
        # Handle memory-based summarize_pr action
        pr_number = action_payload.get("pr_number")
        response = CommandResponse(
            status=CommandStatus.OK,
            intent=ParsedIntent(
                name="pr.summarize",
                confidence=1.0,
                entities={"pr_number": pr_number},
            ),
            spoken_text=f"PR {pr_number} summary: This is a fixture response.",
            cards=[
                UICard(
                    title=f"PR #{pr_number}",
                    subtitle="Fixture data",
                    lines=[
                        "This is a stubbed response.",
                        "Enable live mode with GitHub authentication for real data.",
                    ],
                )
            ],
        )
    elif action_type in ("request_review", "rerun_checks", "comment", "merge"):
        deleted = delete_pending_action(db, request.token)

        if not deleted:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "not_found",
                    "message": "Pending action not found or already consumed",
                },
            )

        response = execute_confirmed_action(
            conn=db,
            user_id=user_id,
            action_type=action_type,
            action_payload=action_payload,
            idempotency_key=request.idempotency_key,
        )
    else:
        response = CommandResponse(
            status=CommandStatus.ERROR,
            intent=ParsedIntent(name="confirm.unknown", confidence=0.5),
            spoken_text=f"Unknown action type: {action_type}",
        )

    # Clean up pending action from memory if it was a memory action
    if is_memory_action:
        del pending_actions_memory[request.token]

    # Store for idempotency (both persistent and in-memory)
    if request.idempotency_key:
        from handsfree.db.idempotency_keys import store_idempotency_key

        store_idempotency_key(
            db,
            key=request.idempotency_key,
            user_id=user_id,
            endpoint="/v1/commands/confirm",
            response_data=response.model_dump(mode="json"),
            expires_in_seconds=86400,  # 24 hours
        )
        processed_commands[request.idempotency_key] = response

    # Record confirmation metrics for observability
    from handsfree.metrics import get_metrics_collector

    metrics = get_metrics_collector()
    if response.status == CommandStatus.OK:
        metrics.record_confirmation("ok")
    elif response.status == CommandStatus.ERROR:
        metrics.record_confirmation("error")
    elif response.status == CommandStatus.NEEDS_CONFIRMATION:
        # This shouldn't normally happen for confirmations, but track it
        metrics.record_confirmation("needs_confirmation")
    else:
        # Log unexpected status for debugging
        logger.warning("Unexpected confirmation status: %s", response.status)
        metrics.record_confirmation("unexpected")

    return response


@app.get("/v1/inbox", response_model=InboxResponse)
async def get_inbox(
    user_id: CurrentUser,
    profile: Profile | None = None,
) -> InboxResponse:
    """Get attention items (PRs, mentions, failing checks)."""
    # Use ProfileConfig for profile-aware filtering and truncation
    profile_config = ProfileConfig.for_profile(profile or Profile.DEFAULT)
    
    # Use a placeholder; live mode resolves the authenticated login.
    # In fixture mode, username doesn't matter because fixtures are static.
    user = "me"
    
    # Call the inbox handler to get rich items with checks summary
    try:
        result = handle_inbox_list(
            provider=_github_provider,
            user=user,
            privacy_mode=PrivacyMode.STRICT,
            profile_config=profile_config,
            user_id=user_id,
        )
        
        # Convert handler items to InboxItem format
        items = []
        for item_data in result.get("items", []):
            item = InboxItem(
                type=_INBOX_ITEM_TYPE_MAP.get(item_data.get("type", "pr"), InboxItemType.PR),
                title=item_data.get("title", ""),
                priority=item_data.get("priority", 3),
                repo=item_data.get("repo", ""),
                url=item_data.get("url", ""),
                summary=item_data.get("summary", ""),
                checks_passed=item_data.get("checks_passed"),
                checks_failed=item_data.get("checks_failed"),
                checks_pending=item_data.get("checks_pending"),
            )
            items.append(item)
        
    except Exception as e:
        logger.error("Failed to fetch inbox via handler: %s", str(e))
        # Fall back to fixture items on error
        items = _get_fixture_inbox_items()
    
    # Apply profile-based filtering
    # During workout, only show high priority items for focused attention
    if profile == Profile.WORKOUT:
        items = [item for item in items if item.priority >= 4]
    
    return InboxResponse(items=items)


@app.post("/v1/actions/request-review", response_model=ActionResult)
async def request_review(
    request: RequestReviewRequest,
    user_id: CurrentUser,
) -> ActionResult:
    """Request reviewers on a PR with policy evaluation and audit logging.

    Args:
        request: Request review request.
        user_id: User ID extracted from authentication (via CurrentUser dependency).
    """
    db = get_db()
    reviewers_str = ", ".join(request.reviewers)
    return process_direct_action_request(
        conn=db,
        user_id=user_id,
        request=DirectActionRequest(
            endpoint="/v1/actions/request-review",
            action_type="request_review",
            execution_action_type="request_review",
            pending_action_type="request_review",
            repo=request.repo,
            pr_number=request.pr_number,
            action_payload={
                "repo": request.repo,
                "pr_number": request.pr_number,
                "reviewers": request.reviewers,
            },
            log_request={"reviewers": request.reviewers},
            pending_summary=f"Request review from {reviewers_str} on {request.repo}#{request.pr_number}",
            idempotency_key=request.idempotency_key,
            anomaly_request_data={"reviewers": request.reviewers},
        ),
        idempotency_store=idempotency_store,
    )


@app.post("/v1/actions/rerun-checks", response_model=ActionResult)
async def rerun_checks(
    request: RerunChecksRequest,
    user_id: CurrentUser,
) -> ActionResult:
    """Re-run CI checks with policy evaluation and rate limiting."""
    db = get_db()
    return process_direct_action_request(
        conn=db,
        user_id=user_id,
        request=DirectActionRequest(
            endpoint="/v1/actions/rerun-checks",
            action_type="rerun",
            execution_action_type="rerun",
            pending_action_type="rerun_checks",
            repo=request.repo,
            pr_number=request.pr_number,
            action_payload={"repo": request.repo, "pr_number": request.pr_number},
            log_request={},
            pending_summary=f"Re-run checks on {request.repo}#{request.pr_number}",
            idempotency_key=request.idempotency_key,
        ),
        idempotency_store=idempotency_store,
    )


@app.post("/v1/actions/comment", response_model=ActionResult)
async def comment_on_pr(
    request: CommentRequest,
    user_id: CurrentUser,
) -> ActionResult:
    """Post a PR comment with policy evaluation and audit logging."""
    db = get_db()
    preview = (
        request.comment_body[:50] + "..."
        if len(request.comment_body) > 50
        else request.comment_body
    )
    return process_direct_action_request(
        conn=db,
        user_id=user_id,
        request=DirectActionRequest(
            endpoint="/v1/actions/comment",
            action_type="comment",
            execution_action_type="comment",
            pending_action_type="comment",
            repo=request.repo,
            pr_number=request.pr_number,
            action_payload={
                "repo": request.repo,
                "pr_number": request.pr_number,
                "comment_body": request.comment_body,
            },
            log_request={"comment_body": request.comment_body},
            pending_summary=f"Post comment on {request.repo}#{request.pr_number}: {preview}",
            idempotency_key=request.idempotency_key,
            anomaly_request_data={"comment_body": request.comment_body},
        ),
        idempotency_store=idempotency_store,
    )


@app.post("/v1/actions/merge", response_model=ActionResult)
async def merge_pr(
    request: MergeRequest,
    user_id: CurrentUser,
) -> ActionResult:
    """Merge a PR with strict policy gating and confirmation."""
    db = get_db()
    return process_direct_action_request(
        conn=db,
        user_id=user_id,
        request=DirectActionRequest(
            endpoint="/v1/actions/merge",
            action_type="merge",
            execution_action_type=None,
            pending_action_type="merge",
            repo=request.repo,
            pr_number=request.pr_number,
            action_payload={
                "repo": request.repo,
                "pr_number": request.pr_number,
                "merge_method": request.merge_method,
            },
            log_request={"merge_method": request.merge_method},
            pending_summary=f"Merge {request.repo}#{request.pr_number} using {request.merge_method}",
            idempotency_key=request.idempotency_key,
            anomaly_request_data={"merge_method": request.merge_method},
            policy_kwargs={"pr_checks_status": None, "pr_approvals_count": 0},
            always_require_confirmation=True,
        ),
        idempotency_store=idempotency_store,
    )


async def _handle_request_review_command(
    parsed_intent: ParsedIntent, text: str, idempotency_key: str | None, user_id: str
) -> CommandResponse:
    """Handle pr.request_review intent with policy evaluation.

    This creates a pending action that requires confirmation unless policy allows direct execution.

    Args:
        parsed_intent: Pydantic ParsedIntent model
        text: Original text command
        idempotency_key: Optional idempotency key
        user_id: User ID from header or fixture
    """
    db = get_db()

    # Extract entities
    reviewers = parsed_intent.entities.get("reviewers", [])
    pr_number = parsed_intent.entities.get("pr_number")

    # For voice commands, we need a default repo. In a real implementation, this would come
    # from context (e.g., current repo, last mentioned repo, etc.)
    # For now, we'll require the PR number and use a placeholder repo.
    # If no PR number is provided, return an error.
    if not pr_number:
        return CommandResponse(
            status=CommandStatus.ERROR,
            intent=parsed_intent,
            spoken_text=(
                "Please specify a PR number, for example: 'request review from alice on PR 123'."
            ),
            debug=DebugInfo(transcript=text),
        )

    if not reviewers:
        return CommandResponse(
            status=CommandStatus.ERROR,
            intent=parsed_intent,
            spoken_text="Please specify at least one reviewer.",
            debug=DebugInfo(transcript=text),
        )

    # Use a default repo for now (in production, this would come from context)
    repo = parsed_intent.entities.get("repo", "default/repo")

    reviewers_str = ", ".join(reviewers)
    try:
        detailed = process_direct_action_request_detailed(
            conn=db,
            user_id=user_id,
            request=DirectActionRequest(
                endpoint="/v1/command",
                action_type="request_review",
                execution_action_type="request_review",
                pending_action_type="request_review",
                repo=repo,
                pr_number=pr_number,
                action_payload={
                    "repo": repo,
                    "pr_number": pr_number,
                    "reviewers": reviewers,
                },
                log_request={"reviewers": reviewers},
                pending_summary=f"Request review from {reviewers_str} on {repo}#{pr_number}",
                idempotency_key=idempotency_key,
                anomaly_request_data={"reviewers": reviewers},
            ),
            idempotency_store=idempotency_store,
        )
    except HTTPException as exc:
        if exc.status_code == 403 and isinstance(exc.detail, dict):
            return CommandResponse(
                status=CommandStatus.ERROR,
                intent=parsed_intent,
                spoken_text=f"Action not allowed: {exc.detail.get('message', 'policy denied')}",
                debug=DebugInfo(transcript=text),
            )
        raise

    if detailed.http_response is not None:
        retry_after = detailed.http_response.headers.get("Retry-After")
        retry_msg = f" Please try again in {retry_after} seconds." if retry_after else ""
        return CommandResponse(
            status=CommandStatus.ERROR,
            intent=parsed_intent,
            spoken_text=f"Rate limit exceeded.{retry_msg}",
            debug=DebugInfo(transcript=text),
        )

    if detailed.pending_token:
        return CommandResponse(
            status=CommandStatus.NEEDS_CONFIRMATION,
            intent=parsed_intent,
            spoken_text=f"{detailed.pending_summary}. Say 'confirm' to proceed.",
            pending_action=PydanticPendingAction(
                token=detailed.pending_token,
                expires_at=detailed.pending_expires_at,
                summary=detailed.pending_summary or "",
            ),
            debug=DebugInfo(transcript=text),
        )

    result = detailed.action_result
    if result and result.ok:
        return CommandResponse(
            status=CommandStatus.OK,
            intent=parsed_intent,
            spoken_text=f"Review requested from {reviewers_str} on {repo}#{pr_number}.",
            debug=DebugInfo(transcript=text),
        )

    message = result.message if result else "Failed to request reviewers."
    return CommandResponse(
        status=CommandStatus.ERROR,
        intent=parsed_intent,
        spoken_text=message,
        debug=DebugInfo(transcript=text),
    )


def _handle_agent_delegate(
    parsed_intent: ParsedIntent,
    text: str,
    device: str,
    user_id: str,
    client_context: dict[str, Any] | None = None,
) -> CommandResponse:
    """Handle agent.delegate intent.

    Parse the command and create an agent task using AgentService.
    Provider is selected from intent entities or defaults to copilot.

    Args:
        parsed_intent: Parsed intent with entities
        text: Command text
        device: Device identifier
        user_id: User ID from header or fixture
    """
    from handsfree.agents.service import AgentService
    from handsfree.agents.delegation import enrich_delegate_trace_for_client_context

    # Extract entities from parsed intent
    instruction = parsed_intent.entities.get("instruction", text)
    issue_number = parsed_intent.entities.get("issue_number")
    pr_number = parsed_intent.entities.get("pr_number")
    # Use provider from intent entities, or None to let AgentService use env default
    # Note: Tests may override this by explicitly specifying provider in intent
    provider = parsed_intent.entities.get("provider")

    normalized_client_context = client_context or {}

    # Build target reference
    target_type = None
    target_ref = None

    if issue_number:
        target_type = "issue"
        target_ref = f"#{issue_number}"
    elif pr_number:
        target_type = "pr"
        target_ref = f"#{pr_number}"

    try:
        # Build trace with original transcript and parsed entities
        from datetime import UTC, datetime

        trace = {
            "transcript": text,
            "intent_name": parsed_intent.name,
            "entities": {
                "instruction": instruction,
                "issue_number": issue_number,
                "pr_number": pr_number,
                "provider": provider,
            },
            "created_at": datetime.now(UTC).isoformat(),
        }
        provider, trace = enrich_delegate_trace_for_client_context(
            provider,
            trace,
            normalized_client_context,
        )

        # Create task via AgentService
        db = get_db()
        agent_service = AgentService(db)
        result = agent_service.delegate(
            user_id=user_id,
            instruction=instruction,
            provider=provider,
            target_type=target_type,
            target_ref=target_ref,
            trace=trace,
        )

        task_id = result["task_id"]
        actual_provider = result["provider"]  # Get actual provider used (may differ from input)

        # Build entity response
        target_description = ""
        if issue_number:
            target_description = f" for issue #{issue_number}"
        elif pr_number:
            target_description = f" for PR #{pr_number}"

        return CommandResponse(
            status=CommandStatus.OK,
            intent=ParsedIntent(
                name="agent.delegate",
                confidence=0.90,
                entities={
                    "instruction": instruction,
                    "task_id": task_id,
                    "issue_number": issue_number,
                    "pr_number": pr_number,
                },
            ),
            spoken_text=f"I've delegated the task{target_description} to an agent. "
            f"Task ID is {task_id[:8]}. Say 'agent status' to check progress.",
            cards=[
                UICard(
                    title="Agent Task Created",
                    subtitle=f"Task {task_id[:8]}",
                    lines=[
                        f"Provider: {actual_provider}",
                        f"Instruction: {instruction}",
                        f"State: {result['state']}",
                    ],
                )
            ],
            follow_on_task=_build_follow_on_task(
                task_id=task_id,
                state=result.get("state"),
                provider=actual_provider,
            ),
            debug=DebugInfo(transcript=text, tool_calls=[{"task_id": task_id}]),
        )
    except Exception as e:
        return CommandResponse(
            status=CommandStatus.ERROR,
            intent=ParsedIntent(name="agent.delegate", confidence=0.90),
            spoken_text=f"Failed to create agent task: {str(e)}",
            debug=DebugInfo(transcript=text),
        )


def _handle_agent_status(text: str, device: str, user_id: str) -> CommandResponse:
    """Handle agent.status intent.

    Query and return the status of agent tasks using AgentService.

    Args:
        text: Command text
        device: Device identifier
        user_id: User ID from header or fixture
    """
    from handsfree.agents.service import AgentService

    try:
        db = get_db()
        agent_service = AgentService(db)
        result = agent_service.get_status(user_id=user_id)

        total = result["total"]
        tasks = result["tasks"]
        spoken_text = result["spoken_text"]

        if total == 0:
            return CommandResponse(
                status=CommandStatus.OK,
                intent=ParsedIntent(name="agent.status", confidence=0.95),
                spoken_text="You have no agent tasks.",
                debug=DebugInfo(transcript=text),
            )

        # Count by state
        state_counts = {}
        for task in tasks:
            state_counts[task["state"]] = state_counts.get(task["state"], 0) + 1

        # Build spoken response
        parts = []
        if state_counts.get("running"):
            parts.append(f"{state_counts['running']} running")
        if state_counts.get("needs_input"):
            parts.append(f"{state_counts['needs_input']} waiting for input")
        if state_counts.get("completed"):
            parts.append(f"{state_counts['completed']} completed")
        if state_counts.get("failed"):
            parts.append(f"{state_counts['failed']} failed")
        if state_counts.get("created"):
            parts.append(f"{state_counts['created']} created")

        spoken_text = (
            f"You have {len(tasks)} agent task{'s' if len(tasks) != 1 else ''}: {', '.join(parts)}."
        )

        def render_agent_result_lines(
            preview: str | None,
            output: dict[str, Any] | None,
        ) -> list[str]:
            lines: list[str] = []
            if isinstance(output, dict):
                for key in ("message", "status", "expanded_queries", "target_terms", "seed_urls"):
                    value = output.get(key)
                    if value is None:
                        continue
                    if isinstance(value, list):
                        rendered = ", ".join(str(item) for item in value[:3])
                    else:
                        rendered = str(value)
                    if rendered:
                        lines.append(f"{key}: {rendered}")

                task_info = output.get("task")
                if isinstance(task_info, dict):
                    task_status = task_info.get("status")
                    task_id = task_info.get("task_id")
                    if task_status:
                        lines.append(f"task.status: {task_status}")
                    if task_id:
                        lines.append(f"task.id: {task_id}")

            if not lines and preview:
                lines.append(f"Result: {preview}")
            return lines[:3]

        # Build cards for recent tasks
        cards = []
        tool_calls = []
        for task in tasks[:5]:  # Show top 5 most recent
            state_emoji = {
                "created": "⏱️",
                "running": "⚙️",
                "needs_input": "⏸️",
                "completed": "✅",
                "failed": "❌",
            }.get(task["state"], "❓")

            instruction = task.get("instruction")
            if instruction and len(instruction) > 60:
                instruction_display = instruction[:60] + "..."
            else:
                instruction_display = instruction or "No instruction"

            card_lines = [f"Instruction: {instruction_display}"]
            card_lines.extend(
                render_agent_result_lines(
                    task.get("result_preview"),
                    task.get("result_output"),
                )
            )
            cards.append(
                UICard(
                    title=f"{state_emoji} Task {task['id'][:8]}",
                    subtitle=f"{task['state']} • {task.get('provider', 'unknown')}",
                    lines=card_lines,
                )
            )
            tool_call = {
                "task_id": task["id"],
                "provider": task.get("provider"),
                "state": task["state"],
            }
            if task.get("result_output") is not None:
                tool_call["result_output"] = task["result_output"]
            tool_calls.append(tool_call)

        return CommandResponse(
            status=CommandStatus.OK,
            intent=ParsedIntent(
                name="agent.status",
                confidence=0.95,
                entities={"task_count": total},
            ),
            spoken_text=spoken_text,
            cards=cards,
            debug=DebugInfo(transcript=text, tool_calls=tool_calls),
        )
    except Exception as e:
        return CommandResponse(
            status=CommandStatus.ERROR,
            intent=ParsedIntent(name="agent.status", confidence=0.95),
            spoken_text=f"Failed to get agent status: {str(e)}",
            debug=DebugInfo(transcript=text),
        )


def _handle_agent_pause(
    parsed_intent: ParsedIntent, text: str, device: str, user_id: str
) -> CommandResponse:
    """Handle agent.pause intent.

    Pause a running agent task. If task_id is provided in entities, pauses that specific task.
    Otherwise, pauses the most recent running task for the user.

    Args:
        parsed_intent: Parsed intent with entities.
        text: Command text.
        device: Device identifier.
        user_id: User ID from header or fixture.
    """
    from handsfree.agents.service import AgentService

    task_id = parsed_intent.entities.get("task_id")

    try:
        db = get_db()
        agent_service = AgentService(db)
        result = agent_service.pause_task(user_id=user_id, task_id=task_id)

        return CommandResponse(
            status=CommandStatus.OK,
            intent=ParsedIntent(
                name="agent.pause",
                confidence=0.95,
                entities={"task_id": result["task_id"]},
            ),
            spoken_text=result["spoken_text"],
            cards=[
                UICard(
                    title="Agent Task Paused",
                    subtitle=f"Task {result['task_id'][:8]}",
                    lines=[
                        f"State: {result['state']}",
                        "Use 'resume agent' to continue",
                    ],
                )
            ],
            debug=DebugInfo(transcript=text),
        )
    except ValueError as e:
        return CommandResponse(
            status=CommandStatus.ERROR,
            intent=ParsedIntent(name="agent.pause", confidence=0.95),
            spoken_text=str(e),
            debug=DebugInfo(transcript=text),
        )
    except Exception as e:
        return CommandResponse(
            status=CommandStatus.ERROR,
            intent=ParsedIntent(name="agent.pause", confidence=0.95),
            spoken_text=f"Failed to pause agent task: {str(e)}",
            debug=DebugInfo(transcript=text),
        )


def _handle_agent_resume(
    parsed_intent: ParsedIntent, text: str, device: str, user_id: str
) -> CommandResponse:
    """Handle agent.resume intent.

    Resume a paused agent task. If task_id is provided in entities, resumes that specific task.
    Otherwise, resumes the most recent paused task for the user.

    Args:
        parsed_intent: Parsed intent with entities.
        text: Command text.
        device: Device identifier.
        user_id: User ID from header or fixture.
    """
    from handsfree.agents.service import AgentService

    task_id = parsed_intent.entities.get("task_id")

    try:
        db = get_db()
        agent_service = AgentService(db)
        result = agent_service.resume_task(user_id=user_id, task_id=task_id)

        return CommandResponse(
            status=CommandStatus.OK,
            intent=ParsedIntent(
                name="agent.resume",
                confidence=0.95,
                entities={"task_id": result["task_id"]},
            ),
            spoken_text=result["spoken_text"],
            cards=[
                UICard(
                    title="Agent Task Resumed",
                    subtitle=f"Task {result['task_id'][:8]}",
                    lines=[
                        f"State: {result['state']}",
                        "Task is now running",
                    ],
                )
            ],
            debug=DebugInfo(transcript=text),
        )
    except ValueError as e:
        return CommandResponse(
            status=CommandStatus.ERROR,
            intent=ParsedIntent(name="agent.resume", confidence=0.95),
            spoken_text=str(e),
            debug=DebugInfo(transcript=text),
        )
    except Exception as e:
        return CommandResponse(
            status=CommandStatus.ERROR,
            intent=ParsedIntent(name="agent.resume", confidence=0.95),
            spoken_text=f"Failed to resume agent task: {str(e)}",
            debug=DebugInfo(transcript=text),
        )


def _get_fixture_inbox_items() -> list[InboxItem]:
    """Get fixture inbox items for testing."""
    return [
        InboxItem(
            type=InboxItemType.PR,
            title="Review: Add authentication middleware",
            priority=5,
            repo="acme/backend",
            url="https://github.com/acme/backend/pull/123",
            summary="Security: New JWT auth middleware needs review",
        ),
        InboxItem(
            type=InboxItemType.CHECK,
            title="CI failing on main branch",
            priority=5,
            repo="acme/frontend",
            url="https://github.com/acme/frontend/actions/runs/456",
            summary="Test suite failing after recent merge",
        ),
        InboxItem(
            type=InboxItemType.MENTION,
            title="@you mentioned in issue #789",
            priority=3,
            repo="acme/docs",
            url="https://github.com/acme/docs/issues/789",
            summary="Question about API documentation",
        ),
        InboxItem(
            type=InboxItemType.AGENT,
            title="Copilot completed task",
            priority=2,
            repo="acme/ml-service",
            url="https://github.com/acme/ml-service/pull/45",
            summary="Automated refactoring PR ready for review",
        ),
    ]


def _correlate_pr_with_agent_tasks(normalized: dict[str, Any], raw_payload: dict[str, Any]) -> None:
    """Correlate PR webhooks with dispatched agent tasks.

    When a PR is opened, checks if it references a dispatch issue or contains
    task metadata, then updates the corresponding agent task to completed.

    Args:
        normalized: Normalized webhook event data.
        raw_payload: Raw webhook payload.
    """
    import re

    from handsfree.db.agent_tasks import get_agent_tasks, update_agent_task_state

    event_type = normalized.get("event_type")
    action = normalized.get("action")

    # Only process PR opened events
    if event_type != "pull_request" or action != "opened":
        return

    db = get_db()
    pr_number = normalized.get("pr_number")
    pr_url = normalized.get("pr_url")
    repo = normalized.get("repo")

    # Extract PR body from raw payload
    pr = raw_payload.get("pull_request", {})
    pr_body = pr.get("body") or ""

    # Try to extract task_id from PR body metadata
    task_id = None

    # Look for agent_task_metadata comment in PR body
    metadata_match = re.search(
        r"<!--\s*agent_task_metadata\s+(.*?)\s*-->",
        pr_body,
        re.DOTALL,
    )
    if metadata_match:
        try:
            metadata = json.loads(metadata_match.group(1))
            task_id = metadata.get("task_id")
        except Exception:
            pass

    # Also check for "Fixes #N" or "Closes #N" references to issues
    issue_refs = re.findall(r"(?:fixes|closes|resolves)\s+#(\d+)", pr_body, re.IGNORECASE)

    # If we found task_id in metadata, update that task
    if task_id:
        try:
            # Query all tasks to find the matching one
            tasks = get_agent_tasks(conn=db, limit=1000)
            for task in tasks:
                if task.id == task_id and task.state in ("created", "running"):
                    # Update task to completed
                    trace_update = {
                        "pr_url": pr_url,
                        "pr_number": pr_number,
                        "repo_full_name": repo,
                        "correlated_via": "pr_metadata",
                    }

                    updated_task = update_agent_task_state(
                        conn=db,
                        task_id=task_id,
                        new_state="completed",
                        trace_update=trace_update,
                    )

                    if updated_task:
                        logger.info(
                            "Correlated PR %s#%d with task %s via metadata, marked completed",
                            repo,
                            pr_number,
                            task_id,
                        )

                        # Emit completion notification via agent service
                        from handsfree.agents.service import AgentService

                        service = AgentService(db)
                        service._emit_completion_notification(updated_task, "completed")

                    break
        except Exception as e:
            logger.warning("Failed to correlate PR with task via metadata: %s", e)

    # If we found issue references, check if any match dispatch issues
    if issue_refs:
        try:
            # Query all running/created tasks from github_issue_dispatch provider
            tasks = get_agent_tasks(conn=db, limit=1000)
            for task in tasks:
                if (
                    task.provider == "github_issue_dispatch"
                    and task.state in ("created", "running")
                    and task.trace
                ):
                    issue_number = task.trace.get("issue_number")
                    dispatch_repo = task.trace.get("dispatch_repo")

                    # Check if this PR references the dispatch issue
                    if issue_number and str(issue_number) in issue_refs and dispatch_repo == repo:
                        # Update task to completed
                        trace_update = {
                            "pr_url": pr_url,
                            "pr_number": pr_number,
                            "repo_full_name": repo,
                            "correlated_via": "issue_reference",
                        }

                        updated_task = update_agent_task_state(
                            conn=db,
                            task_id=task.id,
                            new_state="completed",
                            trace_update=trace_update,
                        )

                        if updated_task:
                            msg = (
                                "Correlated PR %s#%d with task %s via issue ref #%d, "
                                "marked completed"
                            )
                            logger.info(
                                msg,
                                repo,
                                pr_number,
                                task.id,
                                issue_number,
                            )

                            # Emit completion notification via agent service
                            from handsfree.agents.service import AgentService

                            service = AgentService(db)
                            service._emit_completion_notification(updated_task, "completed")

                        break
        except Exception as e:
            logger.warning("Failed to correlate PR with task via issue reference: %s", e)


def _emit_webhook_notification(normalized: dict[str, Any], raw_payload: dict[str, Any]) -> None:
    """Emit notifications for normalized webhook events.

    Determines affected user(s) based on repository subscriptions and GitHub connections,
    then creates notifications for each affected user.

    Args:
        normalized: Normalized webhook event data.
        raw_payload: Raw webhook payload (for extracting installation_id).
    """
    from handsfree.db.repo_subscriptions import (
        get_users_for_installation,
        get_users_for_repo,
    )
    from handsfree.webhooks import extract_installation_id

    db = get_db()
    event_type = normalized.get("event_type")
    action = normalized.get("action")
    repo = normalized.get("repo")

    # Special handling for installation events which don't have a 'repo' field
    if event_type in ("installation", "installation_repositories"):
        # Installation events determine affected users differently
        affected_users = set()
        installation_id = extract_installation_id(raw_payload)
        if installation_id:
            installation_users = get_users_for_installation(db, installation_id)
            affected_users.update(installation_users)

        # Skip notification if no users found
        if not affected_users:
            logger.info(
                "No users for installation_id=%s, skipping notification",
                installation_id,
            )
            return

        # Continue to notification generation logic below
        # (repo is None for installation events, which is OK)
    elif not repo:
        logger.warning("No repository in normalized event, skipping notification")
        return
    else:
        # Determine affected users based on repo subscriptions and installation
        affected_users = set()

        # First, try to get users by repository name
        repo_users = get_users_for_repo(db, repo)
        affected_users.update(repo_users)

        # Also try to get users by installation_id if present
        installation_id = extract_installation_id(raw_payload)
        if installation_id:
            installation_users = get_users_for_installation(db, installation_id)
            affected_users.update(installation_users)

        # If no users found, log and return (no-op instead of routing to fixture user)
        if not affected_users:
            logger.info(
                "No users subscribed to repo '%s' (installation_id=%s), skipping notification",
                repo,
                installation_id,
            )
            return

    # Generate notification message and type based on event type
    notification_type = None
    message = None
    metadata = {}

    if event_type == "pull_request":
        pr_number = normalized.get("pr_number")
        pr_title = normalized.get("pr_title", "")

        if action == "opened":
            message = f"PR #{pr_number} opened in {repo}: {pr_title}"
            notification_type = "webhook.pr_opened"
        elif action == "closed":
            merged = normalized.get("pr_merged", False)
            if merged:
                message = f"PR #{pr_number} merged in {repo}: {pr_title}"
                notification_type = "webhook.pr_merged"
            else:
                message = f"PR #{pr_number} closed in {repo}: {pr_title}"
                notification_type = "webhook.pr_closed"
        else:
            # synchronize, reopened
            message = f"PR #{pr_number} {action} in {repo}: {pr_title}"
            notification_type = f"webhook.pr_{action}"

        metadata = {
            "pr_number": pr_number,
            "repo": repo,
            "pr_url": normalized.get("pr_url"),
        }

    elif event_type == "check_suite" and action == "completed":
        conclusion = normalized.get("conclusion")
        head_branch = normalized.get("head_branch")

        message = f"Check suite {conclusion} on {repo} ({head_branch})"
        notification_type = f"webhook.check_suite_{conclusion}"

        metadata = {
            "repo": repo,
            "conclusion": conclusion,
            "head_branch": head_branch,
            "pr_numbers": normalized.get("pr_numbers", []),
        }

    elif event_type == "check_run" and action == "completed":
        conclusion = normalized.get("conclusion")
        check_run_name = normalized.get("check_run_name")

        message = f"Check run '{check_run_name}' {conclusion} on {repo}"
        notification_type = f"webhook.check_run_{conclusion}"

        metadata = {
            "repo": repo,
            "conclusion": conclusion,
            "check_run_name": check_run_name,
            "pr_numbers": normalized.get("pr_numbers", []),
        }

    elif event_type == "pull_request_review" and action == "submitted":
        pr_number = normalized.get("pr_number")
        review_state = normalized.get("review_state")
        review_author = normalized.get("review_author")

        message = f"Review {review_state} by {review_author} on PR #{pr_number} in {repo}"
        notification_type = f"webhook.review_{review_state}"

        metadata = {
            "pr_number": pr_number,
            "repo": repo,
            "review_state": review_state,
            "review_author": review_author,
            "review_url": normalized.get("review_url"),
        }

    elif event_type == "issue_comment" and action == "created":
        issue_number = normalized.get("issue_number")
        is_pr = normalized.get("is_pull_request", False)
        comment_author = normalized.get("comment_author")
        comment_url = normalized.get("comment_url")
        mentions = normalized.get("mentions", [])

        # Only create notifications if there are mentions
        if mentions:
            # Generate mention notification for all subscribed users
            item_type = "PR" if is_pr else "issue"
            message = f"Mention by {comment_author} on {item_type} #{issue_number} in {repo}"
            notification_type = "webhook.mention"

            metadata = {
                "issue_number": issue_number,
                "is_pull_request": is_pr,
                "repo": repo,
                "comment_author": comment_author,
                "comment_url": comment_url,
                "mentions": mentions,
            }
        else:
            # No mentions, skip notification
            notification_type = None
            message = None

    elif event_type == "installation" and action == "created":
        # Installation created - low priority notification
        installation_id = normalized.get("installation_id")
        account_login = normalized.get("account_login")
        repositories = normalized.get("repositories", [])

        message = f"GitHub App installed for {account_login} ({len(repositories)} repositories)"
        notification_type = "webhook.installation_created"

        metadata = {
            "installation_id": installation_id,
            "account_login": account_login,
            "repositories": repositories,
        }

    elif event_type == "installation" and action == "deleted":
        # Installation deleted - low priority notification
        installation_id = normalized.get("installation_id")
        account_login = normalized.get("account_login")
        repositories = normalized.get("repositories", [])

        message = f"GitHub App uninstalled for {account_login}"
        notification_type = "webhook.installation_deleted"

        metadata = {
            "installation_id": installation_id,
            "account_login": account_login,
            "repositories": repositories,
        }

    # Create notification for each affected user
    if notification_type and message:
        for user_id in affected_users:
            create_notification(
                conn=db,
                user_id=user_id,
                event_type=notification_type,
                message=message,
                metadata=metadata,
            )
            logger.debug(
                "Created notification for user %s: type=%s",
                user_id,
                notification_type,
            )
    else:
        logger.warning(
            "Could not generate notification for event_type=%s, action=%s",
            event_type,
            action,
        )


@app.get("/v1/notifications")
async def get_notifications(
    user_id: CurrentUser,
    x_user_id_raw: str | None = Header(default=None, alias="X-User-ID"),
    since: str | None = None,
    limit: int = 50,
) -> JSONResponse:
    """Get notifications for the current user.

    Poll-based notification retrieval endpoint. Clients can poll this endpoint
    to get new notifications since a given timestamp.

    Args:
        since: Optional ISO 8601 timestamp to get notifications after this time.
        limit: Maximum number of notifications to return (default: 50, max: 100).
        user_id: User ID extracted from authentication (via CurrentUser dependency).

    Returns:
        JSON response with list of notifications.
    """
    from handsfree.db.notifications import list_notifications

    db = get_db()

    # In dev/test, some endpoints accept arbitrary user IDs (not UUIDs) via header
    # for isolation in tests. In non-dev modes, always trust the authenticated user.
    from handsfree.auth import get_auth_mode

    effective_user_id = user_id
    if get_auth_mode() == "dev" and x_user_id_raw:
        effective_user_id = x_user_id_raw

    # Parse since timestamp if provided
    since_dt = None
    if since:
        try:
            # Handle both +00:00 and Z formats, and URL-encoded spaces
            since_clean = since.replace(" ", "+").replace("Z", "+00:00")
            since_dt = datetime.fromisoformat(since_clean)
        except (ValueError, TypeError) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid 'since' timestamp format. Use ISO 8601 format. Error: {e}",
            ) from e

    # Fetch notifications
    notifications = list_notifications(
        conn=db,
        user_id=effective_user_id,
        since=since_dt,
        limit=limit,
    )

    return JSONResponse(
        content={
            "notifications": [n.to_dict() for n in notifications],
            "count": len(notifications),
        }
    )


@app.post("/v1/tts")
async def text_to_speech(request: TTSRequest) -> Response:
    """Convert text to speech audio.

    This endpoint provides fixture-first TTS capability for the dev loop.
    By default, it uses a stub provider that returns deterministic audio placeholders.
    Real TTS providers can be enabled via environment variables in production.

    Args:
        request: TTS request with text, optional voice, and format

    Returns:
        Audio bytes with appropriate content-type header

    Raises:
        400 Bad Request for invalid input (empty text, text too long)
    """
    from handsfree.tts import get_tts_provider

    # Input validation
    if not request.text or not request.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_input",
                "message": "Text cannot be empty",
            },
        )

    if len(request.text) > 5000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_input",
                "message": "Text too long (maximum 5000 characters)",
            },
        )

    # Use factory to get configured TTS provider
    # Defaults to stub, but can be configured via HANDSFREE_TTS_PROVIDER env var
    provider = get_tts_provider()

    try:
        audio_bytes, content_type = provider.synthesize(
            text=request.text,
            voice=request.voice,
            format=request.format,
        )

        return Response(
            content=audio_bytes,
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="speech.{request.format}"',
            },
        )
    except Exception as e:
        logger.error("TTS synthesis failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "synthesis_failed",
                "message": "Failed to synthesize speech",
            },
        ) from e





@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTPExceptions and return Error schema."""
    if isinstance(exc.detail, dict):
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail,
        )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "http_error",
            "message": str(exc.detail),
        },
    )


@app.post("/v1/github/connections", response_model=GitHubConnectionResponse, status_code=201)
async def create_connection(
    request: CreateGitHubConnectionRequest,
    user_id: CurrentUser,
) -> GitHubConnectionResponse:
    """Create a new GitHub connection for the user.

    This endpoint securely stores GitHub tokens using the configured secret manager.
    You can provide either:
    - A 'token' field with the actual GitHub token (will be stored securely)
    - A 'token_ref' field with a reference to an already-stored token

    Args:
        request: Connection creation request.
        user_id: User ID extracted from authentication (via CurrentUser dependency).

    Returns:
        Created connection.

    Raises:
        HTTPException: If both token and token_ref are provided, or neither is provided.
    """
    db = get_db()

    # Determine the token_ref to store
    final_token_ref = None

    if request.token and request.token_ref:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either 'token' or 'token_ref', not both",
        )

    if request.token:
        # Store the token securely using the secret manager
        secret_manager = get_default_secret_manager()
        try:
            # Create a unique key for this token
            secret_key = f"github_token_{user_id}"
            final_token_ref = secret_manager.store_secret(
                key=secret_key,
                value=request.token,
                metadata={
                    "user_id": user_id,
                    "scopes": request.scopes or "",
                    "created_at": datetime.now(UTC).isoformat(),
                },
            )
            log_info(f"Stored GitHub token securely for user {user_id}")
        except Exception as e:
            log_error(f"Failed to store GitHub token: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to store token securely",
            ) from e
    elif request.token_ref:
        # Use the provided reference
        final_token_ref = request.token_ref
    # else: both are None, which is acceptable (e.g., for GitHub App installations)

    connection = create_github_connection(
        conn=db,
        user_id=user_id,
        installation_id=request.installation_id,
        token_ref=final_token_ref,
        scopes=request.scopes,
    )

    return GitHubConnectionResponse(
        id=connection.id,
        user_id=connection.user_id,
        installation_id=connection.installation_id,
        token_ref=connection.token_ref,
        scopes=connection.scopes,
        created_at=connection.created_at,
        updated_at=connection.updated_at,
    )


@app.get("/v1/github/connections", response_model=GitHubConnectionsListResponse)
async def list_connections(
    user_id: CurrentUser,
) -> GitHubConnectionsListResponse:
    """List all GitHub connections for the user.

    Args:
        user_id: User ID extracted from authentication (via CurrentUser dependency).

    Returns:
        List of connections.
    """
    db = get_db()

    connections = get_github_connections_by_user(conn=db, user_id=user_id)

    return GitHubConnectionsListResponse(
        connections=[
            GitHubConnectionResponse(
                id=conn.id,
                user_id=conn.user_id,
                installation_id=conn.installation_id,
                token_ref=conn.token_ref,
                scopes=conn.scopes,
                created_at=conn.created_at,
                updated_at=conn.updated_at,
            )
            for conn in connections
        ]
    )


@app.get("/v1/github/connections/{connection_id}", response_model=GitHubConnectionResponse)
async def get_connection(
    connection_id: str,
    user_id: CurrentUser,
) -> GitHubConnectionResponse:
    """Get a specific GitHub connection by ID.

    Args:
        connection_id: Connection UUID.
        user_id: User ID extracted from authentication (via CurrentUser dependency).

    Returns:
        Connection details.

    Raises:
        404: Connection not found or user doesn't have access.
    """
    db = get_db()

    connection = get_github_connection(conn=db, connection_id=connection_id)

    if connection is None or connection.user_id != user_id:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "not_found",
                "message": "Connection not found",
            },
        )

    return GitHubConnectionResponse(
        id=connection.id,
        user_id=connection.user_id,
        installation_id=connection.installation_id,
        token_ref=connection.token_ref,
        scopes=connection.scopes,
        created_at=connection.created_at,
        updated_at=connection.updated_at,
    )


@app.delete("/v1/github/connections/{connection_id}", status_code=204)
async def delete_connection(
    connection_id: str,
    user_id: CurrentUser,
) -> Response:
    """Delete a GitHub connection.

    This also removes the associated token from the secret manager if present.

    Returns 204 on success. Returns 404 if the connection does not exist or
    does not belong to the current user.
    """
    from handsfree.db.github_connections import delete_github_connection

    db = get_db()

    connection = get_github_connection(conn=db, connection_id=connection_id)
    if connection is None or connection.user_id != user_id:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": "Connection not found"},
        )

    # Delete the token from secret manager if it exists
    if connection.token_ref:
        secret_manager = get_default_secret_manager()
        try:
            secret_manager.delete_secret(connection.token_ref)
            log_info(f"Deleted secret for connection {connection_id}")
        except Exception as e:
            # Log but don't fail - the database record should still be deleted
            log_warning(f"Failed to delete secret for connection {connection_id}: {e}")

    delete_github_connection(conn=db, connection_id=connection_id)
    return Response(status_code=204)


@app.get("/v1/github/oauth/start", response_model=GitHubOAuthStartResponse)
async def github_oauth_start(
    user_id: CurrentUser,
    scopes: str | None = None,
) -> GitHubOAuthStartResponse:
    """Start GitHub OAuth flow by redirecting user to GitHub's authorize URL.

    This endpoint constructs the OAuth authorization URL and returns it to the client.
    The client should redirect the user to this URL to initiate the OAuth flow.

    Args:
        user_id: User ID extracted from authentication (via CurrentUser dependency).
        scopes: Optional comma-separated OAuth scopes (e.g., "repo,user:email").
                If not provided, uses GITHUB_OAUTH_SCOPES env var or defaults to "repo,user:email".

    Returns:
        Response containing the GitHub OAuth authorization URL.

    Raises:
        500: OAuth not configured (missing CLIENT_ID or REDIRECT_URI).
    """
    import os

    # Get OAuth configuration from environment
    client_id = os.getenv("GITHUB_OAUTH_CLIENT_ID")
    redirect_uri = os.getenv("GITHUB_OAUTH_REDIRECT_URI")
    default_scopes = os.getenv("GITHUB_OAUTH_SCOPES", "repo,user:email")

    if not client_id or not redirect_uri:
        log_error(
            logger,
            "GitHub OAuth not configured",
            missing_client_id=not client_id,
            missing_redirect_uri=not redirect_uri,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "oauth_not_configured",
                "message": (
                    "GitHub OAuth is not configured. "
                    "Set GITHUB_OAUTH_CLIENT_ID and GITHUB_OAUTH_REDIRECT_URI."
                ),
            },
        )

    # Use provided scopes or default
    oauth_scopes = scopes or default_scopes

    # Generate CSRF protection state token
    # TTL can be configured via GITHUB_OAUTH_STATE_TTL_MINUTES (default: 10)
    state_ttl_minutes = int(os.getenv("GITHUB_OAUTH_STATE_TTL_MINUTES", "10"))
    db = get_db()
    state_token = generate_oauth_state(
        conn=db,
        user_id=user_id,
        scopes=oauth_scopes,
        ttl_minutes=state_ttl_minutes,
    )

    # Construct GitHub OAuth authorization URL with state parameter
    from urllib.parse import urlencode

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": oauth_scopes,
        "state": state_token,
    }
    authorize_url = f"https://github.com/login/oauth/authorize?{urlencode(params)}"

    log_info(
        logger,
        "GitHub OAuth start",
        user_id=user_id,
        scopes=oauth_scopes,
        state_generated=True,
    )

    return GitHubOAuthStartResponse(
        authorize_url=authorize_url,
        state=state_token,
    )


@app.get("/v1/github/oauth/callback", response_model=GitHubOAuthCallbackResponse)
async def github_oauth_callback(
    user_id: CurrentUser,
    code: str | None = None,
    state: str | None = None,
) -> GitHubOAuthCallbackResponse:
    """Handle GitHub OAuth callback and exchange code for access token.

    This endpoint receives the authorization code from GitHub, exchanges it for
    an access token, stores the token securely, and creates/updates a GitHub connection.

    Args:
        user_id: User ID extracted from authentication (via CurrentUser dependency).
        code: Authorization code from GitHub OAuth callback.
        state: State parameter for CSRF validation (required).

    Returns:
        Response containing the created connection ID and granted scopes.

    Raises:
        400: Missing authorization code, missing state, or invalid/expired state.
        500: OAuth not configured or token exchange failed.
    """
    import os

    import httpx

    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "missing_code",
                "message": "Authorization code is required",
            },
        )

    # Validate state parameter for CSRF protection
    if not state:
        log_warning(
            logger,
            "OAuth callback missing state parameter",
            user_id=user_id,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "missing_state",
                "message": "State parameter is required for CSRF protection",
            },
        )

    # Validate and consume the state token
    db = get_db()
    oauth_state = validate_and_consume_oauth_state(
        conn=db,
        state=state,
        user_id=user_id,
    )

    if not oauth_state:
        log_warning(
            logger,
            "OAuth callback with invalid or expired state",
            user_id=user_id,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_state",
                "message": "Invalid or expired state parameter",
            },
        )

    log_info(
        logger,
        "OAuth state validated successfully",
        user_id=user_id,
        state_consumed=True,
    )

    # Get OAuth configuration from environment
    client_id = os.getenv("GITHUB_OAUTH_CLIENT_ID")
    client_secret = os.getenv("GITHUB_OAUTH_CLIENT_SECRET")
    redirect_uri = os.getenv("GITHUB_OAUTH_REDIRECT_URI")

    if not client_id or not client_secret or not redirect_uri:
        log_error(
            logger,
            "GitHub OAuth not configured for callback",
            missing_client_id=not client_id,
            missing_client_secret=not client_secret,
            missing_redirect_uri=not redirect_uri,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "oauth_not_configured",
                "message": "GitHub OAuth is not configured properly.",
            },
        )

    # Exchange code for access token
    try:
        log_info(logger, "Exchanging OAuth code for access token", user_id=user_id)

        response = httpx.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
            },
            headers={
                "Accept": "application/json",
            },
            timeout=10.0,
        )

        if response.status_code != 200:
            log_error(
                logger,
                "GitHub OAuth token exchange failed",
                status_code=response.status_code,
                user_id=user_id,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "token_exchange_failed",
                    "message": "Failed to exchange authorization code for access token",
                },
            )

        token_data = response.json()

        # Check for error in response
        if "error" in token_data:
            error_description = token_data.get("error_description", token_data["error"])
            log_error(
                logger,
                "GitHub OAuth returned error",
                error=token_data["error"],
                error_description=error_description,
                user_id=user_id,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "oauth_error",
                    "message": f"GitHub OAuth error: {error_description}",
                },
            )

        access_token = token_data.get("access_token")
        granted_scopes = token_data.get("scope", "")

        if not access_token:
            log_error(logger, "No access token in GitHub OAuth response", user_id=user_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "no_access_token",
                    "message": "No access token received from GitHub",
                },
            )

        log_info(
            logger,
            "Successfully exchanged OAuth code for token",
            user_id=user_id,
            scopes=granted_scopes,
        )

    except httpx.HTTPError as e:
        log_error(
            logger,
            "HTTP error during OAuth token exchange",
            error=str(e),
            user_id=user_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "network_error",
                "message": "Failed to communicate with GitHub OAuth service",
            },
        ) from e

    # Store the token securely using the secret manager
    db = get_db()
    secret_manager = get_default_secret_manager()

    try:
        # Create a unique key for this token
        secret_key = f"github_token_{user_id}"
        token_ref = secret_manager.store_secret(
            key=secret_key,
            value=access_token,
            metadata={
                "user_id": user_id,
                "scopes": granted_scopes,
                "source": "oauth",
                "created_at": datetime.now(UTC).isoformat(),
            },
        )
        log_info(
            logger,
            "Stored GitHub OAuth token securely",
            user_id=user_id,
            token_ref=token_ref,
        )
    except Exception as e:
        log_error(
            logger,
            "Failed to store GitHub OAuth token",
            error=str(e),
            user_id=user_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "storage_error",
                "message": "Failed to store token securely",
            },
        ) from e

    # Create GitHub connection record
    try:
        connection = create_github_connection(
            conn=db,
            user_id=user_id,
            installation_id=None,  # OAuth tokens don't have installation_id
            token_ref=token_ref,
            scopes=granted_scopes,
        )

        log_info(
            logger,
            "Created GitHub connection from OAuth",
            user_id=user_id,
            connection_id=connection.id,
        )

        return GitHubOAuthCallbackResponse(
            connection_id=connection.id,
            scopes=granted_scopes,
        )

    except Exception as e:
        # If connection creation fails, try to clean up the stored token
        try:
            secret_manager.delete_secret(token_ref)
        except Exception:
            pass  # Best effort cleanup

        log_error(
            logger,
            "Failed to create GitHub connection",
            error=str(e),
            user_id=user_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "connection_error",
                "message": "Failed to create GitHub connection",
            },
        ) from e


@app.post(
    "/v1/repos/subscriptions",
    response_model=RepoSubscriptionResponse,
    status_code=201,
)
async def create_repo_subscription(
    request: CreateRepoSubscriptionRequest,
    user_id: CurrentUser,
    x_user_id_raw: str | None = Header(default=None, alias="X-User-ID"),
) -> RepoSubscriptionResponse:
    """Create a new repository subscription for webhook notifications.

    Args:
        request: Subscription creation request.
        user_id: User ID extracted from authentication (via CurrentUser dependency).
        x_user_id_raw: Optional user ID header (dev mode only).

    Returns:
        Created subscription.
    """
    from handsfree.db.repo_subscriptions import (
        create_repo_subscription as db_create_repo_subscription,
    )

    db = get_db()

    # In dev/test, some endpoints accept arbitrary user IDs (not UUIDs) via header
    # for isolation in tests. In non-dev modes, always trust the authenticated user.
    from handsfree.auth import get_auth_mode

    effective_user_id = user_id
    if get_auth_mode() == "dev" and x_user_id_raw:
        effective_user_id = x_user_id_raw

    subscription = db_create_repo_subscription(
        conn=db,
        user_id=effective_user_id,
        repo_full_name=request.repo_full_name,
        installation_id=request.installation_id,
    )

    return RepoSubscriptionResponse(
        id=subscription.id,
        user_id=subscription.user_id,
        repo_full_name=subscription.repo_full_name,
        installation_id=subscription.installation_id,
        created_at=subscription.created_at.isoformat(),
    )


@app.get("/v1/repos/subscriptions", response_model=RepoSubscriptionsListResponse)
async def list_repo_subscriptions(
    user_id: CurrentUser,
    x_user_id_raw: str | None = Header(default=None, alias="X-User-ID"),
) -> RepoSubscriptionsListResponse:
    """List all repository subscriptions for the current user.

    Args:
        user_id: User ID extracted from authentication (via CurrentUser dependency).
        x_user_id_raw: Optional user ID header (dev mode only).

    Returns:
        List of subscriptions.
    """
    from handsfree.db.repo_subscriptions import (
        list_repo_subscriptions as db_list_repo_subscriptions,
    )

    db = get_db()

    # In dev/test, some endpoints accept arbitrary user IDs (not UUIDs) via header
    # for isolation in tests. In non-dev modes, always trust the authenticated user.
    from handsfree.auth import get_auth_mode

    effective_user_id = user_id
    if get_auth_mode() == "dev" and x_user_id_raw:
        effective_user_id = x_user_id_raw

    subscriptions = db_list_repo_subscriptions(conn=db, user_id=effective_user_id)

    return RepoSubscriptionsListResponse(
        subscriptions=[
            RepoSubscriptionResponse(
                id=sub.id,
                user_id=sub.user_id,
                repo_full_name=sub.repo_full_name,
                installation_id=sub.installation_id,
                created_at=sub.created_at.isoformat(),
            )
            for sub in subscriptions
        ]
    )


@app.delete("/v1/repos/subscriptions/{repo_full_name:path}", status_code=204)
async def delete_repo_subscription(
    repo_full_name: str,
    user_id: CurrentUser,
    x_user_id_raw: str | None = Header(default=None, alias="X-User-ID"),
) -> Response:
    """Delete a repository subscription.

    Args:
        repo_full_name: Full repository name (e.g., "owner/repo").
        user_id: User ID extracted from authentication (via CurrentUser dependency).
        x_user_id_raw: Optional user ID header (dev mode only).

    Returns:
        204 No Content on success.

    Raises:
        404: Subscription not found.
    """
    from handsfree.db.repo_subscriptions import (
        delete_repo_subscription as db_delete_repo_subscription,
    )

    db = get_db()

    # In dev/test, some endpoints accept arbitrary user IDs (not UUIDs) via header
    # for isolation in tests. In non-dev modes, always trust the authenticated user.
    from handsfree.auth import get_auth_mode

    effective_user_id = user_id
    if get_auth_mode() == "dev" and x_user_id_raw:
        effective_user_id = x_user_id_raw

    deleted = db_delete_repo_subscription(
        conn=db,
        user_id=effective_user_id,
        repo_full_name=repo_full_name,
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "not_found",
                "message": "Subscription not found",
            },
        )

    return Response(status_code=204)


@app.post(
    "/v1/notifications/subscriptions",
    response_model=NotificationSubscriptionResponse,
    status_code=201,
)
async def create_notification_subscription(
    request: CreateNotificationSubscriptionRequest,
    user_id: CurrentUser,
) -> NotificationSubscriptionResponse:
    """Create a new notification subscription for push delivery.

    Args:
        request: Subscription creation request.
        x_user_id: Optional user ID header (falls back to fixture user ID).

    Returns:
        Created subscription.
    """
    from handsfree.db.notification_subscriptions import create_subscription

    db = get_db()

    subscription = create_subscription(
        conn=db,
        user_id=user_id,
        endpoint=request.endpoint,
        subscription_keys=request.subscription_keys,
        platform=request.platform,
    )

    return NotificationSubscriptionResponse(
        id=subscription.id,
        user_id=subscription.user_id,
        endpoint=subscription.endpoint,
        platform=subscription.platform,
        subscription_keys=subscription.subscription_keys or {},
        created_at=subscription.created_at.isoformat(),
        updated_at=subscription.updated_at.isoformat(),
    )


@app.get("/v1/notifications/subscriptions", response_model=NotificationSubscriptionsListResponse)
async def list_notification_subscriptions(
    user_id: CurrentUser,
) -> NotificationSubscriptionsListResponse:
    """List all notification subscriptions for the user.

    Args:
        x_user_id: Optional user ID header (falls back to fixture user ID).

    Returns:
        List of subscriptions.
    """
    from handsfree.db.notification_subscriptions import list_subscriptions

    db = get_db()

    subscriptions = list_subscriptions(conn=db, user_id=user_id)

    return NotificationSubscriptionsListResponse(
        subscriptions=[
            NotificationSubscriptionResponse(
                id=sub.id,
                user_id=sub.user_id,
                endpoint=sub.endpoint,
                platform=sub.platform,
                subscription_keys=sub.subscription_keys or {},
                created_at=sub.created_at.isoformat(),
                updated_at=sub.updated_at.isoformat(),
            )
            for sub in subscriptions
        ]
    )


@app.delete("/v1/notifications/subscriptions/{subscription_id}", status_code=204)
async def delete_notification_subscription(
    subscription_id: str,
    user_id: CurrentUser,
) -> Response:
    """Delete a notification subscription.

    Args:
        subscription_id: Subscription UUID.
        x_user_id: Optional user ID header (falls back to fixture user ID).

    Returns:
        204 No Content on success.

    Raises:
        404: Subscription not found or user does not have access.
    """
    from handsfree.db.notification_subscriptions import delete_subscription, get_subscription

    db = get_db()

    # Verify subscription exists and belongs to user
    subscription = get_subscription(conn=db, subscription_id=subscription_id)
    if subscription is None or subscription.user_id != user_id:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "not_found",
                "message": "Subscription not found",
            },
        )

    # Delete subscription
    deleted = delete_subscription(conn=db, subscription_id=subscription_id)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "not_found",
                "message": "Subscription not found",
            },
        )

    return Response(status_code=204)


@app.get("/v1/notifications/{notification_id}")
async def get_notification_detail(
    notification_id: str,
    user_id: CurrentUser,
    x_user_id_raw: str | None = Header(default=None, alias="X-User-ID"),
) -> JSONResponse:
    """Get a specific notification by ID for the current user.

    Used by mobile app when a push notification includes notification_id.

    Args:
        notification_id: ID of the notification to retrieve.
        user_id: User ID extracted from authentication (via CurrentUser dependency).

    Returns:
        JSON response with notification details.

    Raises:
        HTTPException: 404 if notification not found or doesn't belong to user.
    """
    from handsfree.db.notifications import get_notification

    db = get_db()

    # In dev/test, some endpoints accept arbitrary user IDs (not UUIDs) via header
    # for isolation in tests. In non-dev modes, always trust the authenticated user.
    from handsfree.auth import get_auth_mode

    effective_user_id = user_id
    if get_auth_mode() == "dev" and x_user_id_raw:
        effective_user_id = x_user_id_raw

    # Fetch notification
    notification = get_notification(
        conn=db,
        user_id=effective_user_id,
        notification_id=notification_id,
    )

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    return JSONResponse(content=notification.to_dict())


@app.get("/v1/agents/tasks")
async def list_agent_tasks(
    user_id: CurrentUser,
    x_user_id_raw: str | None = Header(default=None, alias="X-User-ID"),
    task_status: str | None = Query(None, alias="status"),
    provider: str | None = Query(None),
    capability: str | None = Query(None),
    result_view: str = Query("full"),
    results_only: bool = Query(False),
    sort: str = Query("created_at"),
    direction: str = Query("desc"),
    limit: int = 100,
    offset: int = 0,
) -> JSONResponse:
    """List agent tasks for the authenticated user.

    Returns a list of agent tasks scoped to the current user, with optional filtering
    and pagination support.

    Args:
        user_id: User ID extracted from authentication.
        task_status: Optional filter by task status/state (e.g., "created", "running", "completed", "failed").
        provider: Optional provider filter.
        capability: Optional normalized MCP capability filter.
        result_view: One of `full`, `normalized`, or `raw`.
        results_only: When true, return only completed tasks with MCP result data.
        sort: Sort field (`created_at` or `updated_at`).
        direction: Sort direction (`asc` or `desc`).
        limit: Maximum number of tasks to return (default: 100, max: 100).
        offset: Number of tasks to skip for pagination (default: 0).

    Returns:
        200 OK with list of tasks.

    Response format:
        {
            "tasks": [
                {
                    "id": "task-uuid",
                    "state": "running",
                    "description": "instruction text",
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-01T00:00:00Z",
                    "pr_url": "https://github.com/owner/repo/pull/123" (optional)
                }
            ],
            "pagination": {
                "limit": 100,
                "offset": 0,
                "has_more": false
            }
        }
    """
    # Validate limit
    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_parameter",
                "message": "limit must be between 1 and 100",
            },
        )

    # Validate offset
    if offset < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_parameter",
                "message": "offset must be non-negative",
            },
        )

    if result_view not in {"full", "normalized", "raw"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_parameter",
                "message": "result_view must be one of: full, normalized, raw",
            },
        )
    if sort not in {"created_at", "updated_at"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_parameter",
                "message": "sort must be one of: created_at, updated_at",
            },
        )
    if direction not in {"asc", "desc"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_parameter",
                "message": "direction must be one of: asc, desc",
            },
        )

    db = get_db()
    from handsfree.db.agent_tasks import get_agent_tasks
    from handsfree.auth import get_auth_mode

    effective_user_id = user_id
    if get_auth_mode() == "dev" and x_user_id_raw:
        effective_user_id = x_user_id_raw

    # Query tasks with filters, fetch one extra to check if there are more
    tasks = get_agent_tasks(
        conn=db,
        user_id=effective_user_id,
        provider=provider,
        state="completed" if results_only and task_status is None else task_status,
        sort_by=sort,
        direction=direction,
        limit=1000 if (capability or results_only) else limit + 1,
        offset=0 if (capability or results_only) else offset,
    )

    tasks = _filter_agent_tasks_for_results(
        tasks,
        capability=capability,
        results_only=results_only,
    )
    if capability or results_only:
        tasks, has_more = _paginate_task_list(tasks, limit=limit, offset=offset)
    else:
        # Check if there are more results
        has_more = len(tasks) > limit
        if has_more:
            tasks = tasks[:limit]

    # Format response
    task_list = [
        _apply_task_result_view(_serialize_agent_task(task), result_view)
        for task in tasks
    ]

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "tasks": task_list,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "has_more": has_more,
            },
            "filters": {
                "status": task_status,
                "provider": provider,
                "capability": capability,
                "result_view": result_view,
                "results_only": results_only,
                "sort": sort,
                "direction": direction,
            },
        },
    )


@app.get("/v1/agents/tasks/{task_id}")
async def get_agent_task_detail(
    task_id: str,
    user_id: CurrentUser,
    x_user_id_raw: str | None = Header(default=None, alias="X-User-ID"),
) -> JSONResponse:
    """Get a specific agent task for the current user."""
    effective_user_id = _resolve_effective_user_id(user_id, x_user_id_raw)
    db = get_db()
    task = _get_scoped_agent_task(conn=db, task_id=task_id, user_id=effective_user_id)

    task_data = {
        "id": task.id,
        "state": task.state,
        "provider": task.provider,
        "description": task.instruction or "",
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        "target_type": task.target_type,
        "target_ref": task.target_ref,
        "trace": task.trace or {},
    }
    serialized_task = _serialize_agent_task(task)
    for key in (
        "result_preview",
        "result_output",
        "result_envelope",
        "follow_up_actions",
        "pr_url",
    ):
        if key in serialized_task:
            task_data[key] = serialized_task[key]
    normalized_result = _normalize_mcp_task_result(task)
    if normalized_result is not None:
        task_data["result"] = normalized_result

    return JSONResponse(status_code=status.HTTP_200_OK, content=task_data)


def _task_control_response(
    task_id: str,
    state: str,
    message: str,
    updated_at: str | None = None,
) -> AgentTaskControlResponse:
    return AgentTaskControlResponse(
        task_id=task_id,
        state=state,
        message=message,
        updated_at=updated_at,
    )


@app.get("/v1/agents/results")
async def list_agent_results(
    user_id: CurrentUser,
    x_user_id_raw: str | None = Header(default=None, alias="X-User-ID"),
    view: str | None = Query(None),
    provider: str | None = Query(None),
    capability: str | None = Query(None),
    preset: str | None = Query(None),
    latest_only: bool = Query(False),
    sort: str = Query("updated_at"),
    direction: str = Query("desc"),
    limit: int = 50,
    offset: int = 0,
) -> JSONResponse:
    """List completed MCP-backed task results with normalized payloads."""
    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_parameter",
                "message": "limit must be between 1 and 100",
            },
        )
    if offset < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_parameter",
                "message": "offset must be non-negative",
            },
        )
    if sort not in {"created_at", "updated_at"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_parameter",
                "message": "sort must be one of: created_at, updated_at",
            },
        )
    if direction not in {"asc", "desc"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_parameter",
                "message": "direction must be one of: asc, desc",
            },
        )

    try:
        resolved_query = resolve_result_query(
            view=view,
            provider=provider,
            capability=capability,
            preset=preset,
            latest_only=latest_only,
            sort=sort,
            direction=direction,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_parameter",
                "message": str(exc),
            },
        ) from exc
    view = resolved_query["view"]
    provider = resolved_query["provider"]
    capability = resolved_query["capability"]
    preset = resolved_query["preset"]
    latest_only = resolved_query["latest_only"]
    sort = resolved_query["sort"]
    direction = resolved_query["direction"]

    db = get_db()
    from handsfree.auth import get_auth_mode
    from handsfree.db.agent_tasks import get_agent_tasks

    effective_user_id = user_id
    if get_auth_mode() == "dev" and x_user_id_raw:
        effective_user_id = x_user_id_raw

    tasks = get_agent_tasks(
        conn=db,
        user_id=effective_user_id,
        provider=provider,
        state="completed",
        sort_by=sort,
        direction=direction,
        limit=1000,
        offset=0,
    )
    tasks = _filter_agent_tasks_for_results(
        tasks,
        capability=capability,
        results_only=True,
    )
    summary = _summarize_result_tasks(tasks)
    if latest_only:
        tasks = _latest_tasks_by_result_key(tasks)
    tasks, has_more = _paginate_task_list(tasks, limit=limit, offset=offset)

    results: list[dict[str, Any]] = []
    for task in tasks:
        task_data = _serialize_agent_task(task)
        results.append(
            {
                "task_id": task.id,
                "provider": task.provider,
                "state": task.state,
                "description": task.instruction or "",
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "updated_at": task.updated_at.isoformat() if task.updated_at else None,
                "result": task_data.get("result"),
                "result_preview": task_data.get("result_preview"),
                "result_output": task_data.get("result_output"),
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "results": results,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "has_more": has_more,
            },
            "summary": summary,
            "filters": {
                "view": view,
                "provider": provider,
                "capability": capability,
                "preset": preset,
                "latest_only": latest_only,
                "sort": sort,
                "direction": direction,
            },
        },
    )


@app.post("/v1/agents/tasks/{task_id}/pause", response_model=AgentTaskControlResponse)
async def pause_agent_task(
    task_id: str,
    user_id: CurrentUser,
    x_user_id_raw: str | None = Header(default=None, alias="X-User-ID"),
) -> AgentTaskControlResponse:
    """Pause a running task for the current user."""
    from handsfree.agents.service import AgentService

    effective_user_id = _resolve_effective_user_id(user_id, x_user_id_raw)
    db = get_db()
    _get_scoped_agent_task(conn=db, task_id=task_id, user_id=effective_user_id)
    agent_service = AgentService(db)

    try:
        result = agent_service.pause_task(user_id=effective_user_id, task_id=task_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_transition",
                "message": str(exc),
            },
        ) from exc

    return _task_control_response(
        task_id=result["task_id"],
        state=result["state"],
        message="Task paused successfully",
        updated_at=result.get("updated_at"),
    )


@app.post("/v1/agents/tasks/{task_id}/resume", response_model=AgentTaskControlResponse)
async def resume_agent_task(
    task_id: str,
    user_id: CurrentUser,
    x_user_id_raw: str | None = Header(default=None, alias="X-User-ID"),
) -> AgentTaskControlResponse:
    """Resume a paused task for the current user."""
    from handsfree.agents.service import AgentService

    effective_user_id = _resolve_effective_user_id(user_id, x_user_id_raw)
    db = get_db()
    _get_scoped_agent_task(conn=db, task_id=task_id, user_id=effective_user_id)
    agent_service = AgentService(db)

    try:
        result = agent_service.resume_task(user_id=effective_user_id, task_id=task_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_transition",
                "message": str(exc),
            },
        ) from exc

    return _task_control_response(
        task_id=result["task_id"],
        state=result["state"],
        message="Task resumed successfully",
        updated_at=result.get("updated_at"),
    )


@app.post("/v1/agents/tasks/{task_id}/cancel", response_model=AgentTaskControlResponse)
async def cancel_agent_task(
    task_id: str,
    user_id: CurrentUser,
    x_user_id_raw: str | None = Header(default=None, alias="X-User-ID"),
) -> AgentTaskControlResponse:
    """Cancel an active task for the current user."""
    from handsfree.agents.service import AgentService

    effective_user_id = _resolve_effective_user_id(user_id, x_user_id_raw)
    db = get_db()
    _get_scoped_agent_task(conn=db, task_id=task_id, user_id=effective_user_id)
    agent_service = AgentService(db)

    try:
        result = agent_service.cancel_task(user_id=effective_user_id, task_id=task_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_transition",
                "message": str(exc),
            },
        ) from exc

    return _task_control_response(
        task_id=result["task_id"],
        state=result["state"],
        message="Task cancelled successfully",
        updated_at=result.get("updated_at"),
    )


@app.post("/v1/agents/tasks/{task_id}/start", response_model=AgentTaskControlResponse)
async def start_agent_task(
    task_id: str,
    user_id: CurrentUser,
) -> AgentTaskControlResponse:
    """Start an agent task (dev-only endpoint).

    Transitions a task from 'created' to 'running' state.
    This endpoint is only available in dev mode.

    Args:
        task_id: The task ID to start.
        user_id: User ID extracted from authentication.

    Returns:
        200 OK with updated task information.

    Raises:
        403: Endpoint disabled (not in dev mode).
        404: Task not found.
        400: Invalid state transition.
    """
    # Dev-only check
    from handsfree.auth import get_auth_mode

    if get_auth_mode() != "dev":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "forbidden",
                "message": "Task control endpoints are only available in dev mode",
            },
        )

    db = get_db()
    from handsfree.agents.service import AgentService

    agent_service = AgentService(db)

    try:
        result = agent_service.advance_task_state(
            task_id=task_id,
            new_state="running",
            trace_update={
                "started_at": datetime.now(UTC).isoformat(),
                "started_via": "api_endpoint",
            },
        )

        return _task_control_response(
            task_id=result["task_id"],
            state=result["state"],
            message="Task started successfully",
            updated_at=result.get("updated_at"),
        )
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "not_found",
                    "message": str(e),
                },
            ) from e
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "invalid_transition",
                    "message": str(e),
                },
            ) from e


@app.post("/v1/agents/tasks/{task_id}/complete", response_model=AgentTaskControlResponse)
async def complete_agent_task(
    task_id: str,
    user_id: CurrentUser,
) -> AgentTaskControlResponse:
    """Complete an agent task (dev-only endpoint).

    Transitions a task from 'running' to 'completed' state.
    This endpoint is only available in dev mode.

    Args:
        task_id: The task ID to complete.
        user_id: User ID extracted from authentication.

    Returns:
        200 OK with updated task information.

    Raises:
        403: Endpoint disabled (not in dev mode).
        404: Task not found.
        400: Invalid state transition.
    """
    # Dev-only check
    from handsfree.auth import get_auth_mode

    if get_auth_mode() != "dev":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "forbidden",
                "message": "Task control endpoints are only available in dev mode",
            },
        )

    db = get_db()
    from handsfree.agents.service import AgentService

    agent_service = AgentService(db)

    try:
        result = agent_service.advance_task_state(
            task_id=task_id,
            new_state="completed",
            trace_update={
                "completed_at": datetime.now(UTC).isoformat(),
                "completed_via": "api_endpoint",
                "pr_url": None,  # Placeholder for PR link
            },
        )

        return _task_control_response(
            task_id=result["task_id"],
            state=result["state"],
            message="Task completed successfully",
            updated_at=result.get("updated_at"),
        )
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "not_found",
                    "message": str(e),
                },
            ) from e
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "invalid_transition",
                    "message": str(e),
                },
            ) from e


@app.post("/v1/agents/tasks/{task_id}/fail", response_model=AgentTaskControlResponse)
async def fail_agent_task(
    task_id: str,
    user_id: CurrentUser,
) -> AgentTaskControlResponse:
    """Fail an agent task (dev-only endpoint).

    Transitions a task to 'failed' state from 'created', 'running', or 'needs_input'.
    This endpoint is only available in dev mode.

    Args:
        task_id: The task ID to fail.
        user_id: User ID extracted from authentication.

    Returns:
        200 OK with updated task information.

    Raises:
        403: Endpoint disabled (not in dev mode).
        404: Task not found.
        400: Invalid state transition.
    """
    # Dev-only check
    from handsfree.auth import get_auth_mode

    if get_auth_mode() != "dev":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "forbidden",
                "message": "Task control endpoints are only available in dev mode",
            },
        )

    db = get_db()
    from handsfree.agents.service import AgentService

    agent_service = AgentService(db)

    try:
        result = agent_service.advance_task_state(
            task_id=task_id,
            new_state="failed",
            trace_update={
                "failed_at": datetime.now(UTC).isoformat(),
                "failed_via": "api_endpoint",
                "error": "Task failed via dev endpoint",
            },
        )

        return _task_control_response(
            task_id=result["task_id"],
            state=result["state"],
            message="Task failed successfully",
            updated_at=result.get("updated_at"),
        )
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "not_found",
                    "message": str(e),
                },
            ) from e
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "invalid_transition",
                    "message": str(e),
                },
            ) from e


# ============================================================================
# API Key Management Endpoints (Admin/Dev Only)
# ============================================================================


@app.post("/v1/admin/api-keys", response_model=CreateApiKeyResponse, status_code=201)
async def create_api_key(
    request: CreateApiKeyRequest,
    user_id: CurrentUser,
) -> CreateApiKeyResponse:
    """Create a new API key for the current user.

    This endpoint is only available in dev mode or for authenticated users.
    The plaintext key is returned ONLY in this response - it cannot be retrieved later.

    Args:
        request: API key creation request.
        user_id: Current authenticated user ID.

    Returns:
        Created API key with plaintext key (shown only once).

    Raises:
        403: Endpoint disabled (not in dev mode and not authenticated).
    """
    from handsfree.db.api_keys import create_api_key as db_create_api_key

    logger.info("Creating API key for user %s with label: %s", user_id, request.label)

    db = get_db()
    plaintext_key, api_key_record = db_create_api_key(
        db,
        user_id=user_id,
        label=request.label,
    )

    logger.info("API key created with ID: %s", api_key_record.id)

    return CreateApiKeyResponse(
        key=plaintext_key,
        api_key=ApiKeyResponse(
            id=api_key_record.id,
            user_id=api_key_record.user_id,
            label=api_key_record.label,
            created_at=api_key_record.created_at.isoformat(),
            revoked_at=api_key_record.revoked_at.isoformat() if api_key_record.revoked_at else None,
            last_used_at=api_key_record.last_used_at.isoformat()
            if api_key_record.last_used_at
            else None,
        ),
    )


@app.get("/v1/admin/api-keys", response_model=ApiKeysListResponse)
async def list_api_keys(
    user_id: CurrentUser,
    include_revoked: bool = False,
) -> ApiKeysListResponse:
    """List all API keys for the current user.

    Args:
        user_id: Current authenticated user ID.
        include_revoked: Whether to include revoked keys (default: False).

    Returns:
        List of API keys (without plaintext keys).
    """
    from handsfree.db.api_keys import get_api_keys_by_user

    logger.info("Listing API keys for user %s, include_revoked=%s", user_id, include_revoked)

    db = get_db()
    api_keys = get_api_keys_by_user(db, user_id, include_revoked=include_revoked)

    return ApiKeysListResponse(
        api_keys=[
            ApiKeyResponse(
                id=key.id,
                user_id=key.user_id,
                label=key.label,
                created_at=key.created_at.isoformat(),
                revoked_at=key.revoked_at.isoformat() if key.revoked_at else None,
                last_used_at=key.last_used_at.isoformat() if key.last_used_at else None,
            )
            for key in api_keys
        ]
    )


@app.delete("/v1/admin/api-keys/{key_id}", status_code=204)
async def revoke_api_key(
    key_id: str,
    user_id: CurrentUser,
) -> Response:
    """Revoke an API key.

    Args:
        key_id: UUID of the API key to revoke.
        user_id: Current authenticated user ID.

    Returns:
        204 No Content on success.

    Raises:
        404: API key not found.
        403: User does not own this API key.
    """
    from handsfree.db.api_keys import get_api_key
    from handsfree.db.api_keys import revoke_api_key as db_revoke_api_key

    logger.info("Revoking API key %s for user %s", key_id, user_id)

    db = get_db()

    # Check if key exists
    api_key = get_api_key(db, key_id)
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    # Verify ownership
    if api_key.user_id != user_id:
        logger.warning(
            "User %s attempted to revoke API key %s owned by %s",
            user_id,
            key_id,
            api_key.user_id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to revoke this API key",
        )

    # Revoke the key
    db_revoke_api_key(db, key_id)
    logger.info("API key %s revoked successfully", key_id)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/v1/admin/ai/backend-policy", response_model=AIBackendPolicyReport)
async def get_ai_backend_policy_report(
    user_id: CurrentUser,
    limit: int = Query(default=200, ge=1, le=1000),
    capture: bool = Query(default=True),
) -> AIBackendPolicyReport:
    """Return current AI backend policy and recent workflow remap counts."""
    db = get_db()
    report = build_ai_backend_policy_report(db, user_id=user_id, limit=limit)
    if capture:
        store_ai_backend_policy_snapshot(db, user_id=user_id, report=report)
    return report


@app.get("/v1/admin/ai/backend-policy/history", response_model=AIBackendPolicyHistoryReport)
async def get_ai_backend_policy_history_report(
    user_id: CurrentUser,
    window_hours: int = Query(default=24, ge=1, le=168),
    bucket_hours: int = Query(default=1, ge=1, le=24),
    limit: int = Query(default=1000, ge=1, le=5000),
) -> AIBackendPolicyHistoryReport:
    """Return bucketed historical AI backend policy activity."""
    db = get_db()
    return build_ai_backend_policy_history_report(
        db,
        user_id=user_id,
        window_hours=window_hours,
        bucket_hours=bucket_hours,
        limit=limit,
    )


@app.get("/v1/admin/ai/backend-policy/snapshots", response_model=AIBackendPolicySnapshotsResponse)
async def list_ai_backend_policy_snapshots(
    user_id: CurrentUser,
    limit: int = Query(default=50, ge=1, le=500),
) -> AIBackendPolicySnapshotsResponse:
    """Return persisted backend-policy snapshots for the current user."""
    db = get_db()
    snapshots = get_ai_backend_policy_snapshots(db, user_id=user_id, limit=limit)
    return AIBackendPolicySnapshotsResponse(
        snapshots=[
            AIBackendPolicySnapshotResponse(
                id=snapshot.id,
                created_at=snapshot.created_at,
                summary_backend=snapshot.summary_backend,
                failure_backend=snapshot.failure_backend,
                github_auth_source=snapshot.github_auth_source,
                github_live_mode_requested=snapshot.github_live_mode_requested,
                ai_execute_logs=snapshot.ai_execute_logs,
                policy_applied_count=snapshot.policy_applied_count,
                remap_counts=dict(snapshot.remap_counts),
                top_capabilities=dict(snapshot.top_capabilities),
                top_remaps=list(snapshot.top_remaps),
            )
            for snapshot in snapshots
        ]
    )
