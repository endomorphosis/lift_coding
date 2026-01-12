"""FastAPI backend for HandsFree Dev Companion.

This is a minimal implementation with in-memory storage.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

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
    PendingAction,
    Profile,
    RequestReviewRequest,
    RerunChecksRequest,
    TextInput,
    UICard,
)

app = FastAPI(
    title="HandsFree Dev Companion API",
    version="1.0.0",
    description="API for hands-free developer assistant",
)

# In-memory storage
pending_actions: dict[str, dict[str, Any]] = {}
webhook_payloads: list[dict[str, Any]] = []
processed_commands: dict[str, CommandResponse] = {}

# Test user ID for MVP (in production this would come from auth)
TEST_USER_ID = "00000000-0000-0000-0000-000000000001"


@app.post("/v1/command", response_model=CommandResponse)
async def submit_command(request: CommandRequest) -> CommandResponse:
    """Submit a hands-free command."""
    # Check idempotency
    if request.idempotency_key and request.idempotency_key in processed_commands:
        return processed_commands[request.idempotency_key]

    # Extract text from input
    if isinstance(request.input, TextInput):
        text = request.input.text.lower().strip()
    else:
        # Audio input - return error for now
        return CommandResponse(
            status=CommandStatus.ERROR,
            intent=ParsedIntent(name="error.unsupported", confidence=1.0),
            spoken_text="Audio input is not yet supported in this version.",
            debug=DebugInfo(transcript="<audio input>"),
        )

    # Simple intent parsing
    if "inbox" in text:
        # Return inbox items
        items = _get_fixture_inbox_items()
        cards = [
            UICard(
                title=item.title,
                subtitle=f"{item.type.value} - Priority {item.priority}",
                lines=[item.summary] if item.summary else [],
                deep_link=item.url,
            )
            for item in items[:3]  # Limit to top 3
        ]

        response = CommandResponse(
            status=CommandStatus.OK,
            intent=ParsedIntent(name="inbox.list", confidence=0.95, entities={}),
            spoken_text=f"You have {len(items)} items in your inbox. "
            f"Top priority: {items[0].title if items else 'none'}.",
            cards=cards,
            debug=DebugInfo(transcript=text),
        )
    elif "summarize" in text and "pr" in text:
        # Extract PR number
        words = text.split()
        pr_number = None
        for i, word in enumerate(words):
            if word == "pr" and i + 1 < len(words):
                try:
                    pr_number = int(words[i + 1])
                    break
                except ValueError:
                    pass

        if pr_number:
            # Create a pending action requiring confirmation
            token = str(uuid.uuid4())
            expires_at = datetime.now(UTC) + timedelta(minutes=5)

            pending_action = PendingAction(
                token=token,
                expires_at=expires_at,
                summary=f"Fetch and summarize PR #{pr_number}",
            )

            # Store pending action
            pending_actions[token] = {
                "action": "summarize_pr",
                "pr_number": pr_number,
                "expires_at": expires_at,
            }

            response = CommandResponse(
                status=CommandStatus.NEEDS_CONFIRMATION,
                intent=ParsedIntent(
                    name="pr.summarize",
                    confidence=0.90,
                    entities={"pr_number": pr_number},
                ),
                spoken_text=f"I found PR {pr_number}. Say 'confirm' to fetch the summary.",
                pending_action=pending_action,
                debug=DebugInfo(transcript=text),
            )
        else:
            response = CommandResponse(
                status=CommandStatus.ERROR,
                intent=ParsedIntent(name="pr.summarize", confidence=0.50),
                spoken_text="I couldn't find a PR number in your request.",
                debug=DebugInfo(transcript=text),
            )
    elif "agent" in text and ("delegate" in text or "ask" in text or "fix" in text):
        # Handle agent.delegate intent
        response = _handle_agent_delegate(text, request.client_context.device)
    elif "agent" in text and ("status" in text or "progress" in text):
        # Handle agent.status intent
        response = _handle_agent_status(text, request.client_context.device)
    elif "merge" in text:
        response = CommandResponse(
            status=CommandStatus.ERROR,
            intent=ParsedIntent(name="pr.merge", confidence=0.80, entities={}),
            spoken_text=(
                "Merge actions require strict policy gates. This feature is coming in PR-007."
            ),
            debug=DebugInfo(transcript=text),
        )
    else:
        # Unknown command
        response = CommandResponse(
            status=CommandStatus.OK,
            intent=ParsedIntent(name="unknown", confidence=0.30, entities={}),
            spoken_text="I didn't understand that command. Try 'inbox' or 'summarize PR <number>'.",
            debug=DebugInfo(transcript=text),
        )

    # Store for idempotency
    if request.idempotency_key:
        processed_commands[request.idempotency_key] = response

    return response


@app.post("/v1/commands/confirm", response_model=CommandResponse)
async def confirm_command(request: ConfirmRequest) -> CommandResponse:
    """Confirm a previously proposed side-effect action."""
    # Check idempotency
    if request.idempotency_key and request.idempotency_key in processed_commands:
        return processed_commands[request.idempotency_key]

    # Check if pending action exists
    if request.token not in pending_actions:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "not_found",
                "message": "Pending action not found or expired",
            },
        )

    action_data = pending_actions[request.token]

    # Check expiration
    if datetime.now(UTC) > action_data["expires_at"]:
        del pending_actions[request.token]
        raise HTTPException(
            status_code=404,
            detail={
                "error": "expired",
                "message": "Pending action has expired",
            },
        )

    # Execute the action (stubbed for now)
    action_type = action_data["action"]

    if action_type == "summarize_pr":
        pr_number = action_data["pr_number"]
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
    else:
        response = CommandResponse(
            status=CommandStatus.ERROR,
            intent=ParsedIntent(name="confirm.unknown", confidence=0.5),
            spoken_text=f"Unknown action type: {action_type}",
        )

    # Clean up pending action
    del pending_actions[request.token]

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


@app.post("/v1/webhooks/github", status_code=202)
async def github_webhook(request: Request) -> dict[str, str]:
    """Receive GitHub webhooks (signature verification stubbed for dev)."""
    # Get raw payload
    payload = await request.json()

    # In production, verify signature using X-Hub-Signature-256 header
    # For now, just store it
    webhook_payloads.append(
        {
            "timestamp": datetime.now(UTC).isoformat(),
            "payload": payload,
        }
    )

    return {"status": "accepted"}


@app.post("/v1/actions/request-review", response_model=ActionResult)
async def request_review(request: RequestReviewRequest) -> ActionResult:
    """Request reviewers on a PR (stubbed - real implementation in PR-007)."""
    return ActionResult(
        ok=True,
        message=f"[STUB] Would request review from {', '.join(request.reviewers)} "
        f"on {request.repo}#{request.pr_number}. Real implementation in PR-007.",
        url=None,
    )


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
    from handsfree.db.agent_tasks import create_agent_task, update_task_status

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
    repo_full_name = None

    words = text.split()
    for i, word in enumerate(words):
        if word.lower() == "issue" and i + 1 < len(words):
            try:
                issue_number = int(words[i + 1].replace("#", ""))
            except ValueError:
                pass
        elif word.lower() == "pr" and i + 1 < len(words):
            try:
                pr_number = int(words[i + 1].replace("#", ""))
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
            repo_full_name=repo_full_name,
            issue_number=issue_number,
            pr_number=pr_number,
        )

        # Start the task with the provider
        agent_provider = get_provider(provider)
        result = agent_provider.start_task(task)

        # Update task status
        if result.get("ok"):
            update_task_status(
                conn,
                task.id,
                status="running",
                last_update=result.get("message", "Agent started"),
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
                intent=ParsedIntent(name="agent.status", confidence=0.95),
                spoken_text="You have no agent tasks.",
                debug=DebugInfo(transcript=text),
            )

        # Count by status
        status_counts = {}
        for task in tasks:
            status_counts[task.status] = status_counts.get(task.status, 0) + 1

        # Build spoken response
        parts = []
        if status_counts.get("running"):
            parts.append(f"{status_counts['running']} running")
        if status_counts.get("needs_input"):
            parts.append(f"{status_counts['needs_input']} waiting for input")
        if status_counts.get("completed"):
            parts.append(f"{status_counts['completed']} completed")
        if status_counts.get("failed"):
            parts.append(f"{status_counts['failed']} failed")

        spoken_text = f"You have {len(tasks)} agent tasks: {', '.join(parts)}."

        # Build cards for recent tasks
        cards = []
        for task in tasks[:5]:  # Show top 5 most recent
            status_emoji = {
                "created": "⏱️",
                "running": "⚙️",
                "needs_input": "⏸️",
                "completed": "✅",
                "failed": "❌",
            }.get(task.status, "❓")

            instruction_display = (
                task.instruction[:60] + "..." if len(task.instruction) > 60 else task.instruction
            )

            cards.append(
                UICard(
                    title=f"{status_emoji} Task {task.id[:8]}",
                    subtitle=f"{task.status} • {task.provider}",
                    lines=[
                        f"Instruction: {instruction_display}",
                        f"Last update: {task.last_update or 'No updates'}",
                    ],
                )
            )

        return CommandResponse(
            status=CommandStatus.OK,
            intent=ParsedIntent(
                name="agent.status",
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
            intent=ParsedIntent(name="agent.status", confidence=0.95),
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
