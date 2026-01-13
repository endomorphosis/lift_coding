"""Agent tasks persistence module.

Manages lifecycle and state transitions for agent delegation tasks.
"""

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import duckdb


# Valid state transitions
VALID_TRANSITIONS = {
    "created": ["running", "failed"],
    "running": ["needs_input", "completed", "failed"],
    "needs_input": ["running", "failed"],
    "completed": [],
    "failed": [],
}


@dataclass
class AgentTask:
    """Represents an agent task."""

    id: str
    user_id: str
    provider: str
    target_type: str | None  # "issue" or "pr" or None
    target_ref: str | None  # e.g., "owner/repo#123"
    instruction: str | None
    state: str
    trace: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "provider": self.provider,
            "target_type": self.target_type,
            "target_ref": self.target_ref,
            "instruction": self.instruction,
            "state": self.state,
            "trace": self.trace,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


def create_agent_task(
    conn: duckdb.DuckDBPyConnection,
    user_id: str,
    provider: str,
    instruction: str | None = None,
    target_type: str | None = None,
    target_ref: str | None = None,
    trace: dict[str, Any] | None = None,
) -> AgentTask:
    """Create a new agent task.

    Args:
        conn: Database connection.
        user_id: UUID of the user creating the task (string, will be converted to UUID).
        provider: Provider name (e.g., "copilot", "custom").
        instruction: Instruction text for the agent.
        target_type: Type of target ("issue", "pr", or None).
        target_ref: Reference to target (e.g., "owner/repo#123").
        trace: Optional trace information (JSON-serializable).

    Returns:
        Created AgentTask object.
    """
    task_id = str(uuid.uuid4())
    now = datetime.now(UTC)
    state = "created"
    
    # Convert user_id to UUID if it's not already one
    try:
        user_uuid = uuid.UUID(user_id) if '-' in user_id else uuid.uuid5(uuid.NAMESPACE_DNS, user_id)
    except (ValueError, AttributeError):
        # If conversion fails, generate a UUID from the string
        user_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, user_id)

    # Parse target_ref to extract repo, issue, pr if provided
    repo_full_name = None
    issue_number = None
    pr_number = None

    if target_ref:
        # Parse format like "owner/repo#123"
        if "#" in target_ref:
            repo_part, num_part = target_ref.rsplit("#", 1)
            repo_full_name = repo_part
            try:
                num = int(num_part)
                if target_type == "issue":
                    issue_number = num
                elif target_type == "pr":
                    pr_number = num
            except ValueError:
                pass

    conn.execute(
        """
        INSERT INTO agent_tasks
        (id, user_id, provider, repo_full_name, issue_number, pr_number, 
         instruction, status, last_update, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            uuid.UUID(task_id),
            user_uuid,
            provider,
            repo_full_name,
            issue_number,
            pr_number,
            instruction,
            state,
            json.dumps(trace) if trace else None,
            now,
            now,
        ],
    )

    return AgentTask(
        id=task_id,
        user_id=user_id,
        provider=provider,
        target_type=target_type,
        target_ref=target_ref,
        instruction=instruction,
        state=state,
        trace=trace,
        created_at=now,
        updated_at=now,
    )


def update_agent_task_state(
    conn: duckdb.DuckDBPyConnection,
    task_id: str,
    new_state: str,
    trace_update: dict[str, Any] | None = None,
) -> AgentTask | None:
    """Update agent task state with transition validation.

    Args:
        conn: Database connection.
        task_id: Task ID to update (string UUID).
        new_state: New state to transition to.
        trace_update: Optional trace information to add/merge.

    Returns:
        Updated AgentTask object if successful, None if task not found.

    Raises:
        ValueError: If state transition is invalid.
    """
    # Get current task
    task = get_agent_task_by_id(conn, task_id)
    if not task:
        return None

    # Validate transition
    valid_next_states = VALID_TRANSITIONS.get(task.state, [])
    if new_state not in valid_next_states:
        raise ValueError(
            f"Invalid state transition from '{task.state}' to '{new_state}'. "
            f"Valid transitions: {valid_next_states}"
        )

    now = datetime.now(UTC)

    # Merge trace updates if provided
    updated_trace = task.trace or {}
    if trace_update:
        updated_trace.update(trace_update)
    
    try:
        task_uuid = uuid.UUID(task_id)
    except ValueError:
        return None

    conn.execute(
        """
        UPDATE agent_tasks
        SET status = ?, last_update = ?, updated_at = ?
        WHERE id = ?
        """,
        [new_state, json.dumps(updated_trace) if updated_trace else None, now, task_uuid],
    )

    return AgentTask(
        id=task.id,
        user_id=task.user_id,
        provider=task.provider,
        target_type=task.target_type,
        target_ref=task.target_ref,
        instruction=task.instruction,
        state=new_state,
        trace=updated_trace,
        created_at=task.created_at,
        updated_at=now,
    )


def get_agent_task_by_id(
    conn: duckdb.DuckDBPyConnection,
    task_id: str,
) -> AgentTask | None:
    """Get a specific agent task by ID.

    Args:
        conn: Database connection.
        task_id: The task ID (string UUID).

    Returns:
        AgentTask if found, None otherwise.
    """
    try:
        task_uuid = uuid.UUID(task_id)
    except ValueError:
        return None
        
    result = conn.execute(
        """
        SELECT id, user_id, provider, repo_full_name, issue_number, pr_number,
               instruction, status, last_update, created_at, updated_at
        FROM agent_tasks
        WHERE id = ?
        """,
        [task_uuid],
    ).fetchone()

    if not result:
        return None

    # Reconstruct target_type and target_ref
    target_type = None
    target_ref = None
    if result[4] is not None:  # issue_number
        target_type = "issue"
        target_ref = f"{result[3]}#{result[4]}" if result[3] else f"#{result[4]}"
    elif result[5] is not None:  # pr_number
        target_type = "pr"
        target_ref = f"{result[3]}#{result[5]}" if result[3] else f"#{result[5]}"

    trace = None
    if result[8]:  # last_update
        try:
            trace = json.loads(result[8]) if isinstance(result[8], str) else result[8]
        except (json.JSONDecodeError, TypeError):
            trace = None

    return AgentTask(
        id=str(result[0]),
        user_id=str(result[1]),
        provider=result[2],
        target_type=target_type,
        target_ref=target_ref,
        instruction=result[6],
        state=result[7],
        trace=trace,
        created_at=result[9],
        updated_at=result[10],
    )


def get_agent_tasks(
    conn: duckdb.DuckDBPyConnection,
    user_id: str | None = None,
    provider: str | None = None,
    state: str | None = None,
    limit: int = 100,
) -> list[AgentTask]:
    """Query agent tasks with optional filters.

    Args:
        conn: Database connection.
        user_id: Filter by user ID (string, will be converted to UUID).
        provider: Filter by provider.
        state: Filter by state.
        limit: Maximum number of tasks to return.

    Returns:
        List of AgentTask objects, ordered by created_at DESC.
    """
    query = (
        "SELECT id, user_id, provider, repo_full_name, issue_number, pr_number, "
        "instruction, status, last_update, created_at, updated_at "
        "FROM agent_tasks WHERE 1=1"
    )
    params = []

    if user_id:
        # Convert user_id to UUID
        try:
            user_uuid = uuid.UUID(user_id) if '-' in user_id else uuid.uuid5(uuid.NAMESPACE_DNS, user_id)
        except (ValueError, AttributeError):
            user_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, user_id)
        query += " AND user_id = ?"
        params.append(user_uuid)

    if provider:
        query += " AND provider = ?"
        params.append(provider)

    if state:
        query += " AND status = ?"
        params.append(state)

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    results = conn.execute(query, params).fetchall()

    tasks = []
    for row in results:
        # Reconstruct target_type and target_ref
        target_type = None
        target_ref = None
        if row[4] is not None:  # issue_number
            target_type = "issue"
            target_ref = f"{row[3]}#{row[4]}" if row[3] else f"#{row[4]}"
        elif row[5] is not None:  # pr_number
            target_type = "pr"
            target_ref = f"{row[3]}#{row[5]}" if row[3] else f"#{row[5]}"

        trace = None
        if row[8]:  # last_update
            try:
                trace = json.loads(row[8]) if isinstance(row[8], str) else row[8]
            except (json.JSONDecodeError, TypeError):
                trace = None

        tasks.append(
            AgentTask(
                id=str(row[0]),
                user_id=str(row[1]),
                provider=row[2],
                target_type=target_type,
                target_ref=target_ref,
                instruction=row[6],
                state=row[7],
                trace=trace,
                created_at=row[9],
                updated_at=row[10],
            )
        )

    return tasks
