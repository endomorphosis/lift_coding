"""FastAPI backend for HandsFree Dev Companion.

This implementation combines webhook handling with comprehensive API endpoints.
"""

__all__ = ["app", "get_db", "FIXTURE_USER_ID"]

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from fastapi import FastAPI, Header, HTTPException, Request, status
from fastapi.responses import FileResponse, JSONResponse, Response

from handsfree.auth import FIXTURE_USER_ID, CurrentUser
from handsfree.commands.intent_parser import IntentParser
from handsfree.commands.pending_actions import PendingActionManager, RedisPendingActionManager
from handsfree.commands.profiles import ProfileConfig
from handsfree.commands.router import CommandRouter
from handsfree.db import init_db
from handsfree.db.action_logs import write_action_log
from handsfree.db.github_connections import (
    create_github_connection,
    get_github_connection,
    get_github_connections_by_user,
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
from handsfree.models import (
    ActionResult,
    AudioInput,
    CommandRequest,
    CommandResponse,
    CommandStatus,
    ConfirmRequest,
    CreateGitHubConnectionRequest,
    CreateNotificationSubscriptionRequest,
    CreateRepoSubscriptionRequest,
    DebugInfo,
    DependencyStatus,
    GitHubConnectionResponse,
    GitHubConnectionsListResponse,
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
from handsfree.models import (
    PendingAction as PydanticPendingAction,
)
from handsfree.policy import PolicyDecision, evaluate_action_policy
from handsfree.redis_client import get_redis_client
from handsfree.secrets import get_default_secret_manager
from handsfree.stt import get_stt_provider
from handsfree.webhooks import (
    normalize_github_event,
    verify_github_signature,
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

# Webhook store (DB-backed, initialized lazily)
_webhook_store = None


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


def _fetch_audio_data(uri: str) -> bytes:
    """Fetch audio data from URI.

    Supports file:// URIs for local testing and development.
    In production, this could support pre-signed URLs from S3, etc.

    Args:
        uri: Audio URI (file:// or local path)

    Returns:
        Audio data as bytes

    Raises:
        ValueError: If URI scheme is unsupported
        FileNotFoundError: If local file doesn't exist
    """
    parsed = urlparse(uri)

    # Support file:// URIs and plain paths
    if parsed.scheme in ("", "file"):
        # Extract path from file:// URI or use as-is
        path = parsed.path if parsed.scheme == "file" else uri

        # Convert to Path object and read
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"Audio file not found: {path}")

        return file_path.read_bytes()
    else:
        # Future: Support http/https pre-signed URLs
        raise ValueError(
            f"Unsupported audio URI scheme: {parsed.scheme}. "
            f"Currently only file:// URIs are supported in dev/test mode."
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


@app.post("/v1/command", response_model=CommandResponse)
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

    # Extract text from input
    if isinstance(request.input, TextInput):
        text = request.input.text.strip()
    elif isinstance(request.input, AudioInput):
        # Audio input - transcribe to text using STT
        try:
            # Fetch audio data from URI
            audio_data = _fetch_audio_data(request.input.uri)

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
        except (ValueError, FileNotFoundError) as e:
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

        # In balanced/debug mode, accept but don't process
        # Log acceptance without URI (unless debug mode with redaction)
        if request.client_context.debug:
            from handsfree.logging_utils import redact_secrets

            redacted_uri = redact_secrets(request.input.uri)
            log_info(
                logger,
                "Accepted image input (not processed)",
                user_id=user_id,
                privacy_mode=privacy_mode.value,
                uri=redacted_uri,
                content_type=request.input.content_type,
            )
        else:
            log_info(
                logger,
                "Accepted image input (not processed)",
                user_id=user_id,
                privacy_mode=privacy_mode.value,
            )

        # Return stub response indicating image is not processed
        clear_request_id()
        debug_info = DebugInfo(
            transcript="<image input - not processed yet>",
        )
        if request.client_context.debug:
            # Include stub message in debug info
            debug_info.tool_calls = [
                {
                    "note": (
                        "Image input accepted but not processed. "
                        "OCR/vision processing not yet implemented."
                    ),
                    "content_type": request.input.content_type or "unknown",
                }
            ]

        return CommandResponse(
            status=CommandStatus.OK,
            intent=ParsedIntent(name="image.placeholder", confidence=1.0),
            spoken_text=(
                "Image received but cannot be processed yet. "
                "Please describe what you need help with."
            ),
            debug=debug_info,
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
        # Agent delegate commands - use old handler for backward compatibility
        # This ensures task_id is included in entities as tests expect
        return _handle_agent_delegate(parsed_intent, transcript, "api", user_id)

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

    return CommandResponse(
        status=status,
        intent=intent,
        spoken_text=spoken_text,
        cards=cards,
        pending_action=pending_action,
        debug=debug,
    )


@app.post("/v1/commands/confirm", response_model=CommandResponse)
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
            # For now, just return a success response
            # In a full implementation, this would execute the actual side effect
            intent_name = confirmed_action.intent_name
            entities = confirmed_action.entities

            if intent_name == "pr.request_review":
                reviewers = entities.get("reviewers", [])
                pr_num = entities.get("pr_number", "unknown")
                reviewers_str = " and ".join(reviewers)
                response = CommandResponse(
                    status=CommandStatus.OK,
                    intent=ParsedIntent(
                        name=intent_name,
                        confidence=1.0,
                        entities=entities,
                    ),
                    spoken_text=(
                        f"Review request sent to {reviewers_str} "
                        f"for PR {pr_num}. (Fixture response)"
                    ),
                )
            elif intent_name == "pr.merge":
                pr_num = entities.get("pr_number", "unknown")
                response = CommandResponse(
                    status=CommandStatus.OK,
                    intent=ParsedIntent(
                        name=intent_name,
                        confidence=1.0,
                        entities=entities,
                    ),
                    spoken_text=f"PR {pr_num} merged successfully. (Fixture response)",
                )
            elif intent_name == "agent.delegate":
                instruction = entities.get("instruction", "handle this")
                response = CommandResponse(
                    status=CommandStatus.OK,
                    intent=ParsedIntent(
                        name=intent_name,
                        confidence=1.0,
                        entities=entities,
                    ),
                    spoken_text=f"Agent task created: {instruction}. (Fixture response)",
                )
            else:
                response = CommandResponse(
                    status=CommandStatus.OK,
                    intent=ParsedIntent(
                        name=intent_name,
                        confidence=1.0,
                        entities=entities,
                    ),
                    spoken_text="Action confirmed. (Fixture response)",
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
            metrics.record_confirmation("ok")

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
            spoken_text=f"PR {pr_number} summary: This is a fixture response. "
            f"Real GitHub integration coming in PR-005.",
            cards=[
                UICard(
                    title=f"PR #{pr_number}",
                    subtitle="Fixture data",
                    lines=[
                        "This is a stubbed response.",
                        "Real PR data will be fetched from GitHub in PR-005.",
                    ],
                )
            ],
        )
    elif action_type == "request_review":
        # Handle DB-backed request_review action with exactly-once semantics
        # Atomically delete the pending action to prevent duplicate execution.
        # Note: get_pending_action already verified the action exists and is not expired,
        # but between that check and this delete, another concurrent request could have
        # consumed it, or it could have been cleaned up. The atomic delete with RETURNING
        # ensures exactly-once execution - if the delete fails, the action is gone and
        # we correctly return 404 to prevent re-execution.
        deleted = delete_pending_action(db, request.token)

        if not deleted:
            # Action was already consumed or cleaned up between the get and delete
            # This ensures idempotency even without an idempotency_key
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "not_found",
                    "message": "Pending action not found or already consumed",
                },
            )

        # Execute the side-effect
        repo = action_payload.get("repo")
        pr_number = action_payload.get("pr_number")
        reviewers = action_payload.get("reviewers", [])

        target = f"{repo}#{pr_number}"
        reviewers_str = ", ".join(reviewers)

        # Check if live mode is enabled and token is available
        from handsfree.github.auth import get_default_auth_provider

        auth_provider = get_default_auth_provider()
        token = None
        if auth_provider.supports_live_mode():
            token = auth_provider.get_token(user_id)

        # Execute via GitHub API if live mode enabled and token available
        if token:
            from handsfree.github.client import request_reviewers as github_request_reviewers

            logger.info(
                "Executing confirmed request_review via GitHub API (live mode) for %s",
                target,
            )

            github_result = github_request_reviewers(
                repo=repo,
                pr_number=pr_number,
                reviewers=reviewers,
                token=token,
            )

            if github_result["ok"]:
                # Write audit log for successful execution
                audit_log = write_action_log(
                    db,
                    user_id=user_id,
                    action_type="request_review",
                    ok=True,
                    target=target,
                    request={"reviewers": reviewers, "confirmed": True},
                    result={
                        "status": "success",
                        "message": "Review requested (live mode)",
                        "via_confirmation": True,
                        "github_response": github_result.get("response_data"),
                    },
                    idempotency_key=request.idempotency_key,
                )

                response = CommandResponse(
                    status=CommandStatus.OK,
                    intent=ParsedIntent(
                        name="request_review.confirmed",
                        confidence=1.0,
                        entities={"repo": repo, "pr_number": pr_number, "reviewers": reviewers},
                    ),
                    spoken_text=f"Review requested from {reviewers_str} on {target}.",
                )

                # Store for idempotency with link to audit log
                if request.idempotency_key:
                    from handsfree.db.idempotency_keys import store_idempotency_key

                    store_idempotency_key(
                        db,
                        key=request.idempotency_key,
                        user_id=user_id,
                        endpoint="/v1/commands/confirm",
                        response_data=response.model_dump(mode="json"),
                        audit_log_id=audit_log.id,
                        expires_in_seconds=86400,  # 24 hours
                    )
                    processed_commands[request.idempotency_key] = response
            else:
                # GitHub API call failed
                audit_log = write_action_log(
                    db,
                    user_id=user_id,
                    action_type="request_review",
                    ok=False,
                    target=target,
                    request={"reviewers": reviewers, "confirmed": True},
                    result={
                        "status": "error",
                        "message": github_result["message"],
                        "via_confirmation": True,
                        "status_code": github_result.get("status_code"),
                    },
                    idempotency_key=request.idempotency_key,
                )

                response = CommandResponse(
                    status=CommandStatus.ERROR,
                    intent=ParsedIntent(
                        name="request_review.confirmed",
                        confidence=1.0,
                        entities={"repo": repo, "pr_number": pr_number, "reviewers": reviewers},
                    ),
                    spoken_text=f"Failed to request reviewers: {github_result['message']}",
                )

                # Store for idempotency with link to audit log
                if request.idempotency_key:
                    from handsfree.db.idempotency_keys import store_idempotency_key

                    store_idempotency_key(
                        db,
                        key=request.idempotency_key,
                        user_id=user_id,
                        endpoint="/v1/commands/confirm",
                        response_data=response.model_dump(mode="json"),
                        audit_log_id=audit_log.id,
                        expires_in_seconds=86400,  # 24 hours
                    )
                    processed_commands[request.idempotency_key] = response
        else:
            # Fixture mode - simulate success
            logger.info(
                "Executing confirmed request_review in fixture mode (no live token) for %s",
                target,
            )

            audit_log = write_action_log(
                db,
                user_id=user_id,
                action_type="request_review",
                ok=True,
                target=target,
                request={"reviewers": reviewers, "confirmed": True},
                result={
                    "status": "success",
                    "message": "Review requested (fixture)",
                    "via_confirmation": True,
                },
                idempotency_key=request.idempotency_key,
            )

            response = CommandResponse(
                status=CommandStatus.OK,
                intent=ParsedIntent(
                    name="request_review.confirmed",
                    confidence=1.0,
                    entities={"repo": repo, "pr_number": pr_number, "reviewers": reviewers},
                ),
                spoken_text=f"Review requested from {reviewers_str} on {target}.",
            )
    elif action_type == "rerun_checks":
        # Handle DB-backed rerun_checks action with exactly-once semantics
        deleted = delete_pending_action(db, request.token)

        if not deleted:
            # Action was already consumed or cleaned up
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "not_found",
                    "message": "Pending action not found or already consumed",
                },
            )

        # Execute the side-effect
        repo = action_payload.get("repo")
        pr_number = action_payload.get("pr_number")

        target = f"{repo}#{pr_number}"

        # Check if live mode is enabled and token is available
        from handsfree.github.auth import get_default_auth_provider

        auth_provider = get_default_auth_provider()
        token = None
        if auth_provider.supports_live_mode():
            token = auth_provider.get_token(user_id)

        # Execute via GitHub API if live mode enabled and token available
        if token:
            from handsfree.github.client import rerun_workflow

            logger.info(
                "Executing confirmed rerun_checks via GitHub API (live mode) for %s",
                target,
            )

            github_result = rerun_workflow(
                repo=repo,
                pr_number=pr_number,
                token=token,
            )

            if github_result["ok"]:
                # Write audit log for successful execution
                write_action_log(
                    db,
                    user_id=user_id,
                    action_type="rerun",
                    ok=True,
                    target=target,
                    request={"confirmed": True},
                    result={
                        "status": "success",
                        "message": "Checks re-run (live mode)",
                        "via_confirmation": True,
                        "run_id": github_result.get("run_id"),
                    },
                    idempotency_key=request.idempotency_key,
                )

                response = CommandResponse(
                    status=CommandStatus.OK,
                    intent=ParsedIntent(
                        name="rerun_checks.confirmed",
                        confidence=1.0,
                        entities={"repo": repo, "pr_number": pr_number},
                    ),
                    spoken_text=f"Workflow checks re-run on {target}.",
                )
            else:
                # GitHub API call failed
                write_action_log(
                    db,
                    user_id=user_id,
                    action_type="rerun",
                    ok=False,
                    target=target,
                    request={"confirmed": True},
                    result={
                        "status": "error",
                        "message": github_result["message"],
                        "via_confirmation": True,
                        "status_code": github_result.get("status_code"),
                    },
                    idempotency_key=request.idempotency_key,
                )

                response = CommandResponse(
                    status=CommandStatus.ERROR,
                    intent=ParsedIntent(
                        name="rerun_checks.confirmed",
                        confidence=1.0,
                        entities={"repo": repo, "pr_number": pr_number},
                    ),
                    spoken_text=f"Failed to re-run checks: {github_result['message']}",
                )
        else:
            # Fixture mode - simulate success
            logger.info(
                "Executing confirmed rerun_checks in fixture mode (no live token) for %s",
                target,
            )

            write_action_log(
                db,
                user_id=user_id,
                action_type="rerun",
                ok=True,
                target=target,
                request={"confirmed": True},
                result={
                    "status": "success",
                    "message": "Checks re-run (fixture)",
                    "via_confirmation": True,
                },
                idempotency_key=request.idempotency_key,
            )

            response = CommandResponse(
                status=CommandStatus.OK,
                intent=ParsedIntent(
                    name="rerun_checks.confirmed",
                    confidence=1.0,
                    entities={"repo": repo, "pr_number": pr_number},
                ),
                spoken_text=f"Workflow checks re-run on {target}.",
            )
    elif action_type == "merge":
        # Handle DB-backed merge action with exactly-once semantics
        deleted = delete_pending_action(db, request.token)

        if not deleted:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "not_found",
                    "message": "Pending action not found or already consumed",
                },
            )

        repo = action_payload.get("repo")
        pr_number = action_payload.get("pr_number")
        merge_method = action_payload.get("merge_method") or "squash"

        target = f"{repo}#{pr_number}"

        from handsfree.github.auth import get_default_auth_provider

        auth_provider = get_default_auth_provider()
        token = None
        if auth_provider.supports_live_mode():
            token = auth_provider.get_token(user_id)

        if token:
            from handsfree.github.client import merge_pull_request

            logger.info(
                "Executing confirmed merge via GitHub API (live mode) for %s",
                target,
            )

            github_result = merge_pull_request(
                repo=repo,
                pr_number=pr_number,
                merge_method=merge_method,
                token=token,
            )

            if github_result["ok"]:
                write_action_log(
                    db,
                    user_id=user_id,
                    action_type="merge",
                    ok=True,
                    target=target,
                    request={"confirmed": True, "merge_method": merge_method},
                    result={
                        "status": "success",
                        "message": "Merged (live mode)",
                        "via_confirmation": True,
                        "github_response": github_result.get("response_data"),
                    },
                    idempotency_key=request.idempotency_key,
                )

                response = CommandResponse(
                    status=CommandStatus.OK,
                    intent=ParsedIntent(
                        name="merge.confirmed",
                        confidence=1.0,
                        entities={
                            "repo": repo,
                            "pr_number": pr_number,
                            "merge_method": merge_method,
                        },
                    ),
                    spoken_text=f"Merged successfully {target}.",
                )
            else:
                write_action_log(
                    db,
                    user_id=user_id,
                    action_type="merge",
                    ok=False,
                    target=target,
                    request={"confirmed": True, "merge_method": merge_method},
                    result={
                        "status": "error",
                        "message": github_result["message"],
                        "via_confirmation": True,
                        "status_code": github_result.get("status_code"),
                        "error_type": github_result.get("error_type"),
                    },
                    idempotency_key=request.idempotency_key,
                )

                response = CommandResponse(
                    status=CommandStatus.ERROR,
                    intent=ParsedIntent(
                        name="merge.confirmed",
                        confidence=1.0,
                        entities={
                            "repo": repo,
                            "pr_number": pr_number,
                            "merge_method": merge_method,
                        },
                    ),
                    spoken_text=f"Failed to merge: {github_result['message']}",
                )
        else:
            logger.info(
                "Executing confirmed merge in fixture mode (no live token) for %s",
                target,
            )

            write_action_log(
                db,
                user_id=user_id,
                action_type="merge",
                ok=True,
                target=target,
                request={"confirmed": True, "merge_method": merge_method},
                result={
                    "status": "success",
                    "message": "PR merged (fixture)",
                    "via_confirmation": True,
                },
                idempotency_key=request.idempotency_key,
            )

            response = CommandResponse(
                status=CommandStatus.OK,
                intent=ParsedIntent(
                    name="merge.confirmed",
                    confidence=1.0,
                    entities={
                        "repo": repo,
                        "pr_number": pr_number,
                        "merge_method": merge_method,
                    },
                ),
                spoken_text=f"Merged successfully {target}.",
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
async def get_inbox(profile: Profile | None = None) -> InboxResponse:
    """Get attention items (PRs, mentions, failing checks)."""
    items = _get_fixture_inbox_items()

    # Filter by profile if needed (stub for now)
    if profile == Profile.WORKOUT:
        # During workout, only show high priority items
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

    # Check idempotency first - database first, then in-memory cache as optimization
    if request.idempotency_key:
        from handsfree.db.idempotency_keys import get_idempotency_response

        cached_response = get_idempotency_response(db, request.idempotency_key)
        if cached_response:
            # Reconstruct ActionResult from cached data
            return ActionResult(**cached_response)

        # Also check in-memory cache (backward compatibility)
        if request.idempotency_key in idempotency_store:
            return idempotency_store[request.idempotency_key]

    # Check rate limit with burst limiting
    from handsfree.rate_limit import check_side_effect_rate_limit
    from handsfree.security import check_and_log_anomaly

    rate_limit_result = check_side_effect_rate_limit(
        db,
        user_id,
        "request_review",
    )

    if not rate_limit_result.allowed:
        # Write audit log for rate limit denial (only if not already logged)
        try:
            write_action_log(
                db,
                user_id=user_id,
                action_type="request_review",
                ok=False,
                target=f"{request.repo}#{request.pr_number}",
                request={"reviewers": request.reviewers},
                result={"error": "rate_limited", "message": rate_limit_result.reason},
                idempotency_key=request.idempotency_key,
            )
        except ValueError:
            # Idempotency key already used in audit log - this is a retry
            pass

        # Check for suspicious activity patterns
        check_and_log_anomaly(
            db,
            user_id,
            "request_review",
            "rate_limited",
            target=f"{request.repo}#{request.pr_number}",
            request_data={"reviewers": request.reviewers},
        )

        # Return 429 with Retry-After header
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=429,
            content={
                "detail": {
                    "error": "rate_limited",
                    "message": rate_limit_result.reason,
                    "retry_after": rate_limit_result.retry_after_seconds,
                }
            },
            headers={"Retry-After": str(rate_limit_result.retry_after_seconds)}
            if rate_limit_result.retry_after_seconds
            else {},
        )

    # Evaluate policy
    policy_result = evaluate_action_policy(
        db,
        user_id,
        request.repo,
        "request_review",
    )

    # Handle policy decisions
    if policy_result.decision == PolicyDecision.DENY:
        # Write audit log for policy denial (only if not already logged)
        try:
            write_action_log(
                db,
                user_id=user_id,
                action_type="request_review",
                ok=False,
                target=f"{request.repo}#{request.pr_number}",
                request={"reviewers": request.reviewers},
                result={"error": "policy_denied", "message": policy_result.reason},
                idempotency_key=request.idempotency_key,
            )
        except ValueError:
            # Idempotency key already used in audit log - this is a retry
            pass

        # Check for suspicious activity patterns
        check_and_log_anomaly(
            db,
            user_id,
            "request_review",
            "policy_denied",
            target=f"{request.repo}#{request.pr_number}",
            request_data={"reviewers": request.reviewers},
        )

        raise HTTPException(
            status_code=403,
            detail={
                "error": "policy_denied",
                "message": policy_result.reason,
            },
        )

    elif policy_result.decision == PolicyDecision.REQUIRE_CONFIRMATION:
        # Create pending action in database
        reviewers_str = ", ".join(request.reviewers)
        summary = f"Request review from {reviewers_str} on {request.repo}#{request.pr_number}"
        pending_action = create_pending_action(
            db,
            user_id=user_id,
            summary=summary,
            action_type="request_review",
            action_payload={
                "repo": request.repo,
                "pr_number": request.pr_number,
                "reviewers": request.reviewers,
            },
            expires_in_seconds=300,  # 5 minutes
        )

        # Write audit log for confirmation required
        audit_log = write_action_log(
            db,
            user_id=user_id,
            action_type="request_review",
            ok=True,
            target=f"{request.repo}#{request.pr_number}",
            request={"reviewers": request.reviewers},
            result={
                "status": "needs_confirmation",
                "token": pending_action.token,
                "reason": policy_result.reason,
            },
            idempotency_key=request.idempotency_key,
        )

        result = ActionResult(
            ok=False,
            message=f"Confirmation required: {policy_result.reason}. "
            f"Use token '{pending_action.token}' to confirm.",
            url=None,
        )

        # Store for idempotency (both persistent and in-memory)
        if request.idempotency_key:
            from handsfree.db.idempotency_keys import store_idempotency_key

            store_idempotency_key(
                db,
                key=request.idempotency_key,
                user_id=user_id,
                endpoint="/v1/actions/request-review",
                response_data=result.model_dump(mode="json"),
                audit_log_id=audit_log.id,
                expires_in_seconds=86400,  # 24 hours
            )
            idempotency_store[request.idempotency_key] = result

        return result

    # Policy allows the action - execute it
    target = f"{request.repo}#{request.pr_number}"

    # Check if live mode is enabled and token is available
    from handsfree.github.auth import get_default_auth_provider

    auth_provider = get_default_auth_provider()
    token = None
    if auth_provider.supports_live_mode():
        token = auth_provider.get_token(user_id)

    # Execute via GitHub API if live mode enabled and token available
    if token:
        from handsfree.github.client import request_reviewers

        logger.info(
            "Executing request_review via GitHub API (live mode) for %s",
            target,
        )

        github_result = request_reviewers(
            repo=request.repo,
            pr_number=request.pr_number,
            reviewers=request.reviewers,
            token=token,
        )

        if github_result["ok"]:
            # Write audit log for successful execution
            audit_log = write_action_log(
                db,
                user_id=user_id,
                action_type="request_review",
                ok=True,
                target=target,
                request={"reviewers": request.reviewers},
                result={
                    "status": "success",
                    "message": "Review requested (live mode)",
                    "github_response": github_result.get("response_data"),
                },
                idempotency_key=request.idempotency_key,
            )

            result = ActionResult(
                ok=True,
                message=github_result["message"],
                url=f"https://github.com/{request.repo}/pull/{request.pr_number}",
            )

            # Store for idempotency with link to audit log
            if request.idempotency_key:
                from handsfree.db.idempotency_keys import store_idempotency_key

                store_idempotency_key(
                    db,
                    key=request.idempotency_key,
                    user_id=user_id,
                    endpoint="/v1/actions/request-review",
                    response_data=result.model_dump(mode="json"),
                    audit_log_id=audit_log.id,
                    expires_in_seconds=86400,  # 24 hours
                )
                idempotency_store[request.idempotency_key] = result
        else:
            # GitHub API call failed
            audit_log = write_action_log(
                db,
                user_id=user_id,
                action_type="request_review",
                ok=False,
                target=target,
                request={"reviewers": request.reviewers},
                result={
                    "status": "error",
                    "message": github_result["message"],
                    "status_code": github_result.get("status_code"),
                },
                idempotency_key=request.idempotency_key,
            )

            result = ActionResult(
                ok=False,
                message=f"GitHub API error: {github_result['message']}",
                url=None,
            )

            # Store for idempotency with link to audit log
            if request.idempotency_key:
                from handsfree.db.idempotency_keys import store_idempotency_key

                store_idempotency_key(
                    db,
                    key=request.idempotency_key,
                    user_id=user_id,
                    endpoint="/v1/actions/request-review",
                    response_data=result.model_dump(mode="json"),
                    audit_log_id=audit_log.id,
                    expires_in_seconds=86400,  # 24 hours
                )
                idempotency_store[request.idempotency_key] = result
    else:
        # Fixture mode - simulate success
        logger.info(
            "Executing request_review in fixture mode (no live token) for %s",
            target,
        )

        audit_log = write_action_log(
            db,
            user_id=user_id,
            action_type="request_review",
            ok=True,
            target=target,
            request={"reviewers": request.reviewers},
            result={"status": "success", "message": "Review requested (fixture)"},
            idempotency_key=request.idempotency_key,
        )

        result = ActionResult(
            ok=True,
            message=f"Review requested from {', '.join(request.reviewers)} on {target}",
            url=f"https://github.com/{request.repo}/pull/{request.pr_number}",
        )

        # Store for idempotency with link to audit log
        if request.idempotency_key:
            from handsfree.db.idempotency_keys import store_idempotency_key

            store_idempotency_key(
                db,
                key=request.idempotency_key,
                user_id=user_id,
                endpoint="/v1/actions/request-review",
                response_data=result.model_dump(mode="json"),
                audit_log_id=audit_log.id,
                expires_in_seconds=86400,  # 24 hours
            )
            idempotency_store[request.idempotency_key] = result

    return result


@app.post("/v1/actions/rerun-checks", response_model=ActionResult)
async def rerun_checks(
    request: RerunChecksRequest,
    user_id: CurrentUser,
) -> ActionResult:
    """Re-run CI checks with policy evaluation and rate limiting."""
    # Get DB connection
    db = get_db()

    # Check idempotency - database first, then in-memory cache as optimization
    if request.idempotency_key:
        from handsfree.db.idempotency_keys import get_idempotency_response

        cached_response = get_idempotency_response(db, request.idempotency_key)
        if cached_response:
            return ActionResult(**cached_response)

        if request.idempotency_key in idempotency_store:
            logger.info(
                "Returning cached result for idempotency key: %s",
                request.idempotency_key,
            )
            return idempotency_store[request.idempotency_key]

    # Rate limiting with burst limiting
    from handsfree.rate_limit import check_side_effect_rate_limit
    from handsfree.security import check_and_log_anomaly

    rate_limit_result = check_side_effect_rate_limit(
        db,
        user_id,
        "rerun",
    )

    if not rate_limit_result.allowed:
        # Write audit log for rate limit
        write_action_log(
            db,
            user_id=user_id,
            action_type="rerun",
            ok=False,
            target=f"{request.repo}#{request.pr_number}",
            request={},
            result={"error": "rate_limited", "message": rate_limit_result.reason},
            idempotency_key=request.idempotency_key,
        )

        # Check for suspicious activity patterns
        check_and_log_anomaly(
            db,
            user_id,
            "rerun",
            "rate_limited",
            target=f"{request.repo}#{request.pr_number}",
            request_data={},
        )

        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=429,
            content={
                "detail": {
                    "error": "rate_limited",
                    "message": rate_limit_result.reason,
                    "retry_after": rate_limit_result.retry_after_seconds,
                }
            },
            headers={"Retry-After": str(rate_limit_result.retry_after_seconds)}
            if rate_limit_result.retry_after_seconds
            else {},
        )

    # Evaluate policy
    policy_result = evaluate_action_policy(
        db,
        user_id,
        request.repo,
        "rerun",
    )

    # Handle policy decisions
    if policy_result.decision == PolicyDecision.DENY:
        # Write audit log for policy denial
        try:
            write_action_log(
                db,
                user_id=user_id,
                action_type="rerun",
                ok=False,
                target=f"{request.repo}#{request.pr_number}",
                request={},
                result={"error": "policy_denied", "message": policy_result.reason},
                idempotency_key=request.idempotency_key,
            )
        except ValueError:
            # Idempotency key already used - this is a retry
            pass

        # Check for suspicious activity patterns
        check_and_log_anomaly(
            db,
            user_id,
            "rerun",
            "policy_denied",
            target=f"{request.repo}#{request.pr_number}",
            request_data={},
        )

        raise HTTPException(
            status_code=403,
            detail={
                "error": "policy_denied",
                "message": policy_result.reason,
            },
        )

    elif policy_result.decision == PolicyDecision.REQUIRE_CONFIRMATION:
        # Create pending action in database
        summary = f"Re-run checks on {request.repo}#{request.pr_number}"
        pending_action = create_pending_action(
            db,
            user_id=user_id,
            summary=summary,
            action_type="rerun_checks",
            action_payload={
                "repo": request.repo,
                "pr_number": request.pr_number,
            },
            expires_in_seconds=300,  # 5 minutes
        )

        # Write audit log for confirmation required
        write_action_log(
            db,
            user_id=user_id,
            action_type="rerun",
            ok=True,
            target=f"{request.repo}#{request.pr_number}",
            request={},
            result={
                "status": "needs_confirmation",
                "token": pending_action.token,
                "reason": policy_result.reason,
            },
            idempotency_key=request.idempotency_key,
        )

        result = ActionResult(
            ok=False,
            message=f"Confirmation required: {policy_result.reason}. "
            f"Use token '{pending_action.token}' to confirm.",
            url=None,
        )

        # Store for idempotency
        if request.idempotency_key:
            idempotency_store[request.idempotency_key] = result

        return result

    # Policy allows the action - execute it
    target = f"{request.repo}#{request.pr_number}"

    # Check if live mode is enabled and token is available
    from handsfree.github.auth import get_default_auth_provider

    auth_provider = get_default_auth_provider()
    token = None
    if auth_provider.supports_live_mode():
        token = auth_provider.get_token(user_id)

    # Execute via GitHub API if live mode enabled and token available
    if token:
        from handsfree.github.client import rerun_workflow

        logger.info(
            "Executing rerun_checks via GitHub API (live mode) for %s",
            target,
        )

        github_result = rerun_workflow(
            repo=request.repo,
            pr_number=request.pr_number,
            token=token,
        )

        if github_result["ok"]:
            # Write audit log for successful execution
            write_action_log(
                db,
                user_id=user_id,
                action_type="rerun",
                ok=True,
                target=target,
                request={},
                result={
                    "status": "success",
                    "message": "Checks re-run (live mode)",
                    "run_id": github_result.get("run_id"),
                },
                idempotency_key=request.idempotency_key,
            )

            result = ActionResult(
                ok=True,
                message=github_result["message"],
                url=f"https://github.com/{request.repo}/pull/{request.pr_number}",
            )
        else:
            # GitHub API call failed
            write_action_log(
                db,
                user_id=user_id,
                action_type="rerun",
                ok=False,
                target=target,
                request={},
                result={
                    "status": "error",
                    "message": github_result["message"],
                    "status_code": github_result.get("status_code"),
                },
                idempotency_key=request.idempotency_key,
            )

            result = ActionResult(
                ok=False,
                message=f"GitHub API error: {github_result['message']}",
                url=None,
            )
    else:
        # Fixture mode - simulate success
        logger.info(
            "Executing rerun_checks in fixture mode (no live token) for %s",
            target,
        )

        write_action_log(
            db,
            user_id=user_id,
            action_type="rerun",
            ok=True,
            target=target,
            request={},
            result={"status": "success", "message": "Checks re-run (fixture)"},
            idempotency_key=request.idempotency_key,
        )

        result = ActionResult(
            ok=True,
            message=f"Workflow checks re-run on {target}",
            url=f"https://github.com/{request.repo}/pull/{request.pr_number}",
        )

    # Store for idempotency
    if request.idempotency_key:
        from handsfree.db.idempotency_keys import store_idempotency_key

        store_idempotency_key(
            db,
            key=request.idempotency_key,
            user_id=user_id,
            endpoint="/v1/actions/rerun-checks",
            response_data=result.model_dump(mode="json"),
            expires_in_seconds=86400,  # 24 hours
        )
        idempotency_store[request.idempotency_key] = result

    return result


@app.post("/v1/actions/merge", response_model=ActionResult)
async def merge_pr(
    request: MergeRequest,
    user_id: CurrentUser,
) -> ActionResult:
    """Merge a PR with strict policy gating and confirmation."""
    db = get_db()

    # Check idempotency first - database first, then in-memory cache as optimization
    if request.idempotency_key:
        from handsfree.db.idempotency_keys import get_idempotency_response

        cached_response = get_idempotency_response(db, request.idempotency_key)
        if cached_response:
            return ActionResult(**cached_response)

        if request.idempotency_key in idempotency_store:
            return idempotency_store[request.idempotency_key]

    # Rate limiting (strict) with burst limiting
    from handsfree.rate_limit import check_side_effect_rate_limit
    from handsfree.security import check_and_log_anomaly

    rate_limit_result = check_side_effect_rate_limit(
        db,
        user_id,
        "merge",
    )

    if not rate_limit_result.allowed:
        write_action_log(
            db,
            user_id=user_id,
            action_type="merge",
            ok=False,
            target=f"{request.repo}#{request.pr_number}",
            request={"merge_method": request.merge_method},
            result={"error": "rate_limited", "message": rate_limit_result.reason},
            idempotency_key=request.idempotency_key,
        )

        # Check for suspicious activity patterns
        check_and_log_anomaly(
            db,
            user_id,
            "merge",
            "rate_limited",
            target=f"{request.repo}#{request.pr_number}",
            request_data={"merge_method": request.merge_method},
        )

        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=429,
            content={
                "detail": {
                    "error": "rate_limited",
                    "message": rate_limit_result.reason,
                    "retry_after": rate_limit_result.retry_after_seconds,
                }
            },
            headers={"Retry-After": str(rate_limit_result.retry_after_seconds)}
            if rate_limit_result.retry_after_seconds
            else {},
        )

    # Evaluate policy (merge is denied by default)
    policy_result = evaluate_action_policy(
        db,
        user_id,
        request.repo,
        "merge",
        pr_checks_status=None,
        pr_approvals_count=0,
    )

    if policy_result.decision == PolicyDecision.DENY:
        write_action_log(
            db,
            user_id=user_id,
            action_type="merge",
            ok=False,
            target=f"{request.repo}#{request.pr_number}",
            request={"merge_method": request.merge_method},
            result={"error": "policy_denied", "message": policy_result.reason},
            idempotency_key=request.idempotency_key,
        )

        # Check for suspicious activity patterns
        check_and_log_anomaly(
            db,
            user_id,
            "merge",
            "policy_denied",
            target=f"{request.repo}#{request.pr_number}",
            request_data={"merge_method": request.merge_method},
        )

        raise HTTPException(
            status_code=403,
            detail={"error": "policy_denied", "message": policy_result.reason},
        )

    # Always require confirmation for merge
    summary = f"Merge {request.repo}#{request.pr_number} using {request.merge_method}"
    pending_action = create_pending_action(
        db,
        user_id=user_id,
        summary=summary,
        action_type="merge",
        action_payload={
            "repo": request.repo,
            "pr_number": request.pr_number,
            "merge_method": request.merge_method,
        },
        expires_in_seconds=300,
    )

    audit_log = write_action_log(
        db,
        user_id=user_id,
        action_type="merge",
        ok=True,
        target=f"{request.repo}#{request.pr_number}",
        request={"merge_method": request.merge_method},
        result={
            "status": "needs_confirmation",
            "token": pending_action.token,
            "reason": policy_result.reason,
        },
        idempotency_key=request.idempotency_key,
    )

    result = ActionResult(
        ok=False,
        message=(
            f"Confirmation required: {policy_result.reason}. "
            f"Use token '{pending_action.token}' to confirm."
        ),
        url=None,
    )

    if request.idempotency_key:
        from handsfree.db.idempotency_keys import store_idempotency_key

        store_idempotency_key(
            db,
            key=request.idempotency_key,
            user_id=user_id,
            endpoint="/v1/actions/merge",
            response_data=result.model_dump(mode="json"),
            audit_log_id=audit_log.id,
            expires_in_seconds=86400,  # 24 hours
        )
        idempotency_store[request.idempotency_key] = result

    return result


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

    # Check rate limit with burst limiting
    from handsfree.rate_limit import check_side_effect_rate_limit
    from handsfree.security import check_and_log_anomaly

    rate_limit_result = check_side_effect_rate_limit(
        db,
        user_id,
        "request_review",
    )

    if not rate_limit_result.allowed:
        # Write audit log for rate limit denial
        try:
            write_action_log(
                db,
                user_id=user_id,
                action_type="request_review",
                ok=False,
                target=f"{repo}#{pr_number}",
                request={"reviewers": reviewers},
                result={"error": "rate_limited", "message": rate_limit_result.reason},
                idempotency_key=idempotency_key,
            )
        except ValueError:
            # Idempotency key already used - this is a retry
            logger.debug(
                "Idempotency key %s already used for rate limit audit log", idempotency_key
            )

        # Check for suspicious activity patterns
        check_and_log_anomaly(
            db,
            user_id,
            "request_review",
            "rate_limited",
            target=f"{repo}#{pr_number}",
            request_data={"reviewers": reviewers},
        )

        # Create user-friendly spoken message with retry guidance
        retry_msg = ""
        if rate_limit_result.retry_after_seconds:
            retry_msg = f" Please try again in {rate_limit_result.retry_after_seconds} seconds."

        return CommandResponse(
            status=CommandStatus.ERROR,
            intent=parsed_intent,
            spoken_text=f"Rate limit exceeded.{retry_msg}",
            debug=DebugInfo(transcript=text),
        )

    # Evaluate policy
    policy_result = evaluate_action_policy(
        db,
        user_id,
        repo,
        "request_review",
    )

    # Handle policy decisions
    if policy_result.decision == PolicyDecision.DENY:
        # Write audit log for policy denial
        try:
            write_action_log(
                db,
                user_id=user_id,
                action_type="request_review",
                ok=False,
                target=f"{repo}#{pr_number}",
                request={"reviewers": reviewers},
                result={"error": "policy_denied", "message": policy_result.reason},
                idempotency_key=idempotency_key,
            )
        except ValueError:
            # Idempotency key already used
            logger.debug(
                "Idempotency key %s already used for policy denial audit log",
                idempotency_key,
            )

        # Check for suspicious activity patterns
        check_and_log_anomaly(
            db,
            user_id,
            "request_review",
            "policy_denied",
            target=f"{repo}#{pr_number}",
            request_data={"reviewers": reviewers},
        )

        return CommandResponse(
            status=CommandStatus.ERROR,
            intent=parsed_intent,
            spoken_text=f"Action not allowed: {policy_result.reason}",
            debug=DebugInfo(transcript=text),
        )

    elif policy_result.decision == PolicyDecision.REQUIRE_CONFIRMATION:
        # Create pending action in database
        reviewers_str = ", ".join(reviewers)
        summary = f"Request review from {reviewers_str} on {repo}#{pr_number}"
        pending_action = create_pending_action(
            db,
            user_id=user_id,
            summary=summary,
            action_type="request_review",
            action_payload={
                "repo": repo,
                "pr_number": pr_number,
                "reviewers": reviewers,
            },
            expires_in_seconds=300,  # 5 minutes
        )

        # Write audit log for confirmation required
        write_action_log(
            db,
            user_id=user_id,
            action_type="request_review",
            ok=True,
            target=f"{repo}#{pr_number}",
            request={"reviewers": reviewers},
            result={
                "status": "needs_confirmation",
                "token": pending_action.token,
                "reason": policy_result.reason,
            },
            idempotency_key=idempotency_key,
        )

        return CommandResponse(
            status=CommandStatus.NEEDS_CONFIRMATION,
            intent=parsed_intent,
            spoken_text=f"{summary}. Say 'confirm' to proceed.",
            pending_action=PydanticPendingAction(
                token=pending_action.token,
                expires_at=pending_action.expires_at,
                summary=summary,
            ),
            debug=DebugInfo(transcript=text),
        )

    # Policy allows the action - execute it directly
    target = f"{repo}#{pr_number}"

    # Check if live mode is enabled and token is available
    from handsfree.github.auth import get_default_auth_provider

    auth_provider = get_default_auth_provider()
    token = None
    if auth_provider.supports_live_mode():
        token = auth_provider.get_token(user_id)

    # Execute via GitHub API if live mode enabled and token available
    if token:
        from handsfree.github.client import request_reviewers as github_request_reviewers

        logger.info(
            "Executing request_review via GitHub API (live mode) for %s",
            target,
        )

        github_result = github_request_reviewers(
            repo=repo,
            pr_number=pr_number,
            reviewers=reviewers,
            token=token,
        )

        if github_result["ok"]:
            # Write audit log for successful execution
            write_action_log(
                db,
                user_id=user_id,
                action_type="request_review",
                ok=True,
                target=target,
                request={"reviewers": reviewers},
                result={
                    "status": "success",
                    "message": "Review requested (live mode)",
                    "github_response": github_result.get("response_data"),
                },
                idempotency_key=idempotency_key,
            )

            reviewers_str = ", ".join(reviewers)
            return CommandResponse(
                status=CommandStatus.OK,
                intent=parsed_intent,
                spoken_text=f"Review requested from {reviewers_str} on {target}.",
                debug=DebugInfo(transcript=text),
            )
        else:
            # GitHub API call failed
            write_action_log(
                db,
                user_id=user_id,
                action_type="request_review",
                ok=False,
                target=target,
                request={"reviewers": reviewers},
                result={
                    "status": "error",
                    "message": github_result["message"],
                    "status_code": github_result.get("status_code"),
                },
                idempotency_key=idempotency_key,
            )

            return CommandResponse(
                status=CommandStatus.ERROR,
                intent=parsed_intent,
                spoken_text=f"Failed to request reviewers: {github_result['message']}",
                debug=DebugInfo(transcript=text),
            )
    else:
        # Fixture mode - simulate success
        logger.info(
            "Executing request_review in fixture mode (no live token) for %s",
            target,
        )

        write_action_log(
            db,
            user_id=user_id,
            action_type="request_review",
            ok=True,
            target=target,
            request={"reviewers": reviewers},
            result={"status": "success", "message": "Review requested (fixture)"},
            idempotency_key=idempotency_key,
        )

        reviewers_str = ", ".join(reviewers)
        return CommandResponse(
            status=CommandStatus.OK,
            intent=parsed_intent,
            spoken_text=f"Review requested from {reviewers_str} on {target}.",
            debug=DebugInfo(transcript=text),
        )


def _handle_agent_delegate(
    parsed_intent: ParsedIntent, text: str, device: str, user_id: str
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

    # Extract entities from parsed intent
    instruction = parsed_intent.entities.get("instruction", text)
    issue_number = parsed_intent.entities.get("issue_number")
    pr_number = parsed_intent.entities.get("pr_number")
    # Use provider from intent entities, or default to "copilot" if not specified
    # Note: Tests may override this by explicitly specifying provider in intent
    provider = parsed_intent.entities.get("provider", "copilot")

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
                        f"Provider: {provider}",
                        f"Instruction: {instruction}",
                        f"State: {result['state']}",
                    ],
                )
            ],
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

        # Build cards for recent tasks
        cards = []
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

            cards.append(
                UICard(
                    title=f"{state_emoji} Task {task['id'][:8]}",
                    subtitle=f"{task['state']} • {task.get('provider', 'unknown')}",
                    lines=[
                        f"Instruction: {instruction_display}",
                    ],
                )
            )

        return CommandResponse(
            status=CommandStatus.OK,
            intent=ParsedIntent(
                name="agent.status",
                confidence=0.95,
                entities={"task_count": total},
            ),
            spoken_text=spoken_text,
            cards=cards,
            debug=DebugInfo(transcript=text),
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
    from handsfree.tts import StubTTSProvider

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

    # For MVP, always use stub provider
    # In production, check env var for real TTS provider selection
    # provider = get_tts_provider()  # Would check HANDSFREE_TTS_PROVIDER env var
    provider = StubTTSProvider()

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
    )

    return NotificationSubscriptionResponse(
        id=subscription.id,
        user_id=subscription.user_id,
        endpoint=subscription.endpoint,
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


@app.post("/v1/agents/tasks/{task_id}/start")
async def start_agent_task(
    task_id: str,
    user_id: CurrentUser,
) -> JSONResponse:
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

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "task_id": result["task_id"],
                "state": result["state"],
                "updated_at": result["updated_at"],
                "message": "Task started successfully",
            },
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


@app.post("/v1/agents/tasks/{task_id}/complete")
async def complete_agent_task(
    task_id: str,
    user_id: CurrentUser,
) -> JSONResponse:
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

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "task_id": result["task_id"],
                "state": result["state"],
                "updated_at": result["updated_at"],
                "message": "Task completed successfully",
            },
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


@app.post("/v1/agents/tasks/{task_id}/fail")
async def fail_agent_task(
    task_id: str,
    user_id: CurrentUser,
) -> JSONResponse:
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

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "task_id": result["task_id"],
                "state": result["state"],
                "updated_at": result["updated_at"],
                "message": "Task failed successfully",
            },
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
