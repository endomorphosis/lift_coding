"""FastAPI backend for HandsFree Dev Companion.

This implementation combines webhook handling with comprehensive API endpoints.
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse

from handsfree.commands.intent_parser import IntentParser
from handsfree.commands.pending_actions import PendingActionManager
from handsfree.commands.router import CommandRouter
from handsfree.db import init_db
from handsfree.db.action_logs import write_action_log
from handsfree.db.pending_actions import (
    create_pending_action,
    delete_pending_action,
    get_pending_action,
)
from handsfree.github import GitHubProvider
from handsfree.handlers.inbox import handle_inbox_list
from handsfree.handlers.pr_summary import handle_pr_summarize
from handsfree.models import (
    ActionResult,
    CommandRequest,
    CommandResponse,
    CommandStatus,
    ConfirmRequest,
    DebugInfo,
    InboxItem,
    InboxItemType,
    InboxResponse,
    MergeRequest,
    ParsedIntent,
    Profile,
    RequestReviewRequest,
    RerunChecksRequest,
    TextInput,
    UICard,
)
from handsfree.models import (
    PendingAction as PydanticPendingAction,
)
from handsfree.policy import PolicyDecision, evaluate_action_policy
from handsfree.rate_limit import check_rate_limit
from handsfree.webhooks import (
    normalize_github_event,
    verify_github_signature,
    WebhookStore,
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

# Webhook store
_webhook_store = WebhookStore()

# Fixture user ID for development/testing
FIXTURE_USER_ID = "00000000-0000-0000-0000-000000000001"

# Initialize command infrastructure
_intent_parser = IntentParser()
_pending_action_manager = PendingActionManager()
_command_router: CommandRouter | None = None
_github_provider = GitHubProvider()


def get_db():
    """Get or initialize database connection."""
    global _db_conn
    if _db_conn is None:
        _db_conn = init_db(":memory:")
    return _db_conn


def get_command_router() -> CommandRouter:
    """Get or initialize command router with database connection."""
    global _command_router
    if _command_router is None:
        db = get_db()
        _command_router = CommandRouter(_pending_action_manager, db_conn=db)
    return _command_router


def get_db_webhook_store() -> WebhookStore:
    """Get the webhook store instance."""
    return _webhook_store


# Test user ID for MVP (in production this would come from auth)
TEST_USER_ID = "00000000-0000-0000-0000-000000000001"


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


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
        logger.warning("Duplicate delivery detected: %s", x_github_delivery)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate delivery ID",
        )

    # Read raw body for signature verification
    body = await request.body()

    # Verify signature (dev mode: secret=None allows 'dev' signature)
    # In production, get secret from environment/config
    webhook_secret = None  # Dev mode
    signature_ok = verify_github_signature(body, x_hub_signature_256, webhook_secret)

    if not signature_ok:
        logger.error(
            "Signature verification failed for delivery %s",
            x_github_delivery,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature",
        )

    # Parse payload
    try:
        payload = await request.json()
    except Exception as e:
        logger.error("Failed to parse webhook payload: %s", e)
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

    # Normalize event (if supported)
    normalized = normalize_github_event(x_github_event, payload)
    if normalized:
        logger.info(
            "Normalized event: type=%s, action=%s",
            x_github_event,
            normalized.get("action"),
        )
        # In a full implementation, normalized events would update inbox/notifications
        # For now, just log them

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={"event_id": event_id, "message": "Webhook accepted"},
    )


@app.post("/v1/command", response_model=CommandResponse)
async def submit_command(request: CommandRequest) -> CommandResponse:
    """Submit a hands-free command."""
    # Check idempotency
    if request.idempotency_key and request.idempotency_key in processed_commands:
        return processed_commands[request.idempotency_key]

    # Extract text from input
    if isinstance(request.input, TextInput):
        text = request.input.text.strip()
    else:
        # Audio input - return error for now
        return CommandResponse(
            status=CommandStatus.ERROR,
            intent=ParsedIntent(name="error.unsupported", confidence=1.0),
            spoken_text="Audio input is not yet supported in this version.",
            debug=DebugInfo(transcript="<audio input>"),
        )

    # Parse intent using the intent parser
    parsed_intent = _intent_parser.parse(text)

    # Route through CommandRouter
    router = get_command_router()
    router_response = router.route(
        intent=parsed_intent,
        profile=request.profile,
        session_id=request.idempotency_key,  # Use idempotency key as session ID
    )

    # Convert router response to CommandResponse
    response = _convert_router_response_to_command_response(
        router_response, parsed_intent, text, request.profile
    )

    # Store for idempotency
    if request.idempotency_key:
        processed_commands[request.idempotency_key] = response

    return response


def _convert_router_response_to_command_response(
    router_response: dict[str, Any],
    parsed_intent: Any,
    transcript: str,
    profile: Profile,
) -> CommandResponse:
    """Convert router response dict to CommandResponse model.

    Args:
        router_response: Response dict from CommandRouter
        parsed_intent: The parsed intent object
        transcript: Original text transcript
        profile: User profile

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
    
    if parsed_intent.name == "inbox.list":
        # Use fixture-backed inbox handler
        try:
            inbox_result = handle_inbox_list(
                provider=_github_provider,
                user="fixture-user",
                privacy_mode=True,
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
                    privacy_mode=True,
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
        return _handle_agent_delegate(transcript, "api")

    elif parsed_intent.name == "agent.progress" and status == CommandStatus.OK:
        # Agent status commands - use old handler for backward compatibility
        return _handle_agent_status(transcript, "api")

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

    # Build debug info
    debug = DebugInfo(transcript=transcript)

    return CommandResponse(
        status=status,
        intent=intent,
        spoken_text=spoken_text,
        cards=cards,
        pending_action=pending_action,
        debug=debug,
    )


@app.post("/v1/commands/confirm", response_model=CommandResponse)
async def confirm_command(request: ConfirmRequest) -> CommandResponse:
    """Confirm a previously proposed side-effect action."""
    db = get_db()

    # Check idempotency - return cached response if exists
    if request.idempotency_key and request.idempotency_key in processed_commands:
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
                    spoken_text=f"Review request sent to {reviewers_str} for PR {pr_num}. (Fixture response)",
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
                    spoken_text=f"PR {pr_num} merged. (Fixture response)",
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

            # Store for idempotency
            if request.idempotency_key:
                processed_commands[request.idempotency_key] = response

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

        # Execute the side-effect (fixture behavior - no real GitHub writes)
        repo = action_payload.get("repo")
        pr_number = action_payload.get("pr_number")
        reviewers = action_payload.get("reviewers", [])

        target = f"{repo}#{pr_number}"
        reviewers_str = ", ".join(reviewers)

        # Write audit log for the confirmation execution
        write_action_log(
            db,
            user_id=FIXTURE_USER_ID,
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
    else:
        response = CommandResponse(
            status=CommandStatus.ERROR,
            intent=ParsedIntent(name="confirm.unknown", confidence=0.5),
            spoken_text=f"Unknown action type: {action_type}",
        )

    # Clean up pending action from memory if it was a memory action
    if is_memory_action:
        del pending_actions_memory[request.token]

    # Store for idempotency
    if request.idempotency_key:
        processed_commands[request.idempotency_key] = response

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
async def request_review(request: RequestReviewRequest) -> ActionResult:
    """Request reviewers on a PR with policy evaluation and audit logging."""
    db = get_db()

    # Check idempotency first - return cached result if exists
    if request.idempotency_key and request.idempotency_key in idempotency_store:
        return idempotency_store[request.idempotency_key]

    # Check rate limit
    rate_limit_result = check_rate_limit(
        db,
        FIXTURE_USER_ID,
        "request_review",
        window_seconds=60,
        max_requests=10,
    )

    if not rate_limit_result.allowed:
        # Write audit log for rate limit denial (only if not already logged)
        try:
            write_action_log(
                db,
                user_id=FIXTURE_USER_ID,
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

        raise HTTPException(
            status_code=429,
            detail={
                "error": "rate_limited",
                "message": rate_limit_result.reason,
                "retry_after": rate_limit_result.retry_after_seconds,
            },
        )

    # Evaluate policy
    policy_result = evaluate_action_policy(
        db,
        FIXTURE_USER_ID,
        request.repo,
        "request_review",
    )

    # Handle policy decisions
    if policy_result.decision == PolicyDecision.DENY:
        # Write audit log for policy denial (only if not already logged)
        try:
            write_action_log(
                db,
                user_id=FIXTURE_USER_ID,
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
            user_id=FIXTURE_USER_ID,
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
        write_action_log(
            db,
            user_id=FIXTURE_USER_ID,
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

        # Store for idempotency
        if request.idempotency_key:
            idempotency_store[request.idempotency_key] = result

        return result

    # Policy allows the action - execute it
    # In a real implementation, this would call GitHub API
    # For now, we simulate success
    target = f"{request.repo}#{request.pr_number}"

    # Write audit log for successful execution
    write_action_log(
        db,
        user_id=FIXTURE_USER_ID,
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

    # Store for idempotency
    if request.idempotency_key:
        idempotency_store[request.idempotency_key] = result

    return result


@app.post("/v1/actions/rerun-checks", response_model=ActionResult)
async def rerun_checks(request: RerunChecksRequest) -> ActionResult:
    """Re-run CI checks (stubbed - real implementation in PR-007)."""
    return ActionResult(
        ok=True,
        message=f"[STUB] Would rerun checks on {request.repo}#{request.pr_number}. "
        f"Real implementation in PR-007.",
        url=None,
    )


@app.post("/v1/actions/merge", response_model=ActionResult)
async def merge_pr(request: MergeRequest) -> ActionResult:
    """Merge a PR (stubbed - real implementation in PR-007)."""
    return ActionResult(
        ok=False,
        message=f"[STUB] Merge action for {request.repo}#{request.pr_number} "
        f"requires policy gates. Real implementation in PR-007.",
        url=None,
    )


def _handle_agent_delegate(text: str, device: str) -> CommandResponse:
    """Handle agent.delegate intent.

    Parse the command and create an agent task.
    For MVP, uses mock provider.
    """
    from handsfree.agent_providers import get_provider
    from handsfree.db import init_db
    from handsfree.db.agent_tasks import create_agent_task, update_agent_task_state

    # Extract instruction from text
    # Simple parsing: everything after "agent" or "fix" or "ask agent to"
    instruction = text
    if "ask agent to" in text:
        instruction = text.split("ask agent to", 1)[1].strip()
    elif "fix" in text:
        instruction = text.split("fix", 1)[1].strip()

    # Extract issue/PR number if present
    issue_number = None
    pr_number = None
    target_type = None
    target_ref = None

    words = text.split()
    for i, word in enumerate(words):
        if word.lower() == "issue" and i + 1 < len(words):
            try:
                issue_number = int(words[i + 1].replace("#", ""))
                target_type = "issue"
                target_ref = f"#{issue_number}"
            except ValueError:
                pass
        elif word.lower() == "pr" and i + 1 < len(words):
            try:
                pr_number = int(words[i + 1].replace("#", ""))
                target_type = "pr"
                target_ref = f"#{pr_number}"
            except ValueError:
                pass

    # For MVP, use a test user ID and mock provider
    user_id = TEST_USER_ID
    provider = "mock"

    try:
        # Create task in database
        conn = init_db()
        task = create_agent_task(
            conn,
            user_id=user_id,
            provider=provider,
            instruction=instruction,
            target_type=target_type,
            target_ref=target_ref,
        )

        # Start the task with the provider
        agent_provider = get_provider(provider)
        result = agent_provider.start_task(task)

        # Update task state
        if result.get("ok"):
            update_agent_task_state(
                conn,
                task.id,
                new_state="running",
                trace_update={"started": result.get("message", "Agent started")},
            )

        conn.close()

        # Return response
        target = ""
        if issue_number:
            target = f" for issue #{issue_number}"
        elif pr_number:
            target = f" for PR #{pr_number}"

        return CommandResponse(
            status=CommandStatus.OK,
            intent=ParsedIntent(
                name="agent.delegate",
                confidence=0.90,
                entities={
                    "instruction": instruction,
                    "task_id": task.id,
                    "issue_number": issue_number,
                    "pr_number": pr_number,
                },
            ),
            spoken_text=f"I've delegated the task{target} to an agent. "
            f"Task ID is {task.id[:8]}. Say 'agent status' to check progress.",
            cards=[
                UICard(
                    title="Agent Task Created",
                    subtitle=f"Task {task.id[:8]}",
                    lines=[
                        f"Provider: {provider}",
                        f"Instruction: {instruction}",
                        "Status: running",
                    ],
                )
            ],
            debug=DebugInfo(transcript=text, tool_calls=[{"task_id": task.id}]),
        )
    except Exception as e:
        return CommandResponse(
            status=CommandStatus.ERROR,
            intent=ParsedIntent(name="agent.delegate", confidence=0.90),
            spoken_text=f"Failed to create agent task: {str(e)}",
            debug=DebugInfo(transcript=text),
        )


def _handle_agent_status(text: str, device: str) -> CommandResponse:
    """Handle agent.status intent.

    Query and return the status of agent tasks.
    """
    from handsfree.db import init_db
    from handsfree.db.agent_tasks import get_agent_tasks

    # For MVP, use a test user ID
    user_id = TEST_USER_ID

    try:
        conn = init_db()
        tasks = get_agent_tasks(conn, user_id=user_id, limit=10)
        conn.close()

        if not tasks:
            return CommandResponse(
                status=CommandStatus.OK,
                intent=ParsedIntent(name="agent.progress", confidence=0.95),
                spoken_text="You have no agent tasks.",
                debug=DebugInfo(transcript=text),
            )

        # Count by state
        state_counts = {}
        for task in tasks:
            state_counts[task.state] = state_counts.get(task.state, 0) + 1

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

        spoken_text = f"You have {len(tasks)} agent task{'s' if len(tasks) != 1 else ''}: {', '.join(parts)}."

        # Build cards for recent tasks
        cards = []
        for task in tasks[:5]:  # Show top 5 most recent
            status_emoji = {
                "created": "⏱️",
                "running": "⚙️",
                "needs_input": "⏸️",
                "completed": "✅",
                "failed": "❌",
            }.get(task.state, "❓")

            instruction_display = (
                task.instruction[:60] + "..." if task.instruction and len(task.instruction) > 60 else (task.instruction or "No instruction")
            )

            cards.append(
                UICard(
                    title=f"{status_emoji} Task {task.id[:8]}",
                    subtitle=f"{task.state} • {task.provider}",
                    lines=[
                        f"Instruction: {instruction_display}",
                    ],
                )
            )

        return CommandResponse(
            status=CommandStatus.OK,
            intent=ParsedIntent(
                name="agent.progress",  # Match router's convention
                confidence=0.95,
                entities={"task_count": len(tasks)},
            ),
            spoken_text=spoken_text,
            cards=cards,
            debug=DebugInfo(transcript=text),
        )
    except Exception as e:
        return CommandResponse(
            status=CommandStatus.ERROR,
            intent=ParsedIntent(name="agent.progress", confidence=0.95),
            spoken_text=f"Failed to get agent status: {str(e)}",
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
