"""Agent tasks persistence module.

Manages agent task lifecycle with state machine and notification tracking.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import duckdb


@dataclass
class AgentTask:
    """Represents an agent task with lifecycle state."""

    id: str
    user_id: str
    provider: str
    repo_full_name: str | None
    issue_number: int | None
    pr_number: int | None
    instruction: str
    status: str
    last_update: str | None
    trace: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime


def create_agent_task(
    conn: duckdb.DuckDBPyConnection,
    user_id: str,
    provider: str,
    instruction: str,
    repo_full_name: str | None = None,
    issue_number: int | None = None,
    pr_number: int | None = None,
) -> AgentTask:
    """Create a new agent task.

    Args:
        conn: Database connection.
        user_id: UUID of the user.
        provider: Provider name (e.g., "copilot", "custom").
        instruction: Task instruction text.
        repo_full_name: Repository full name (owner/name).
        issue_number: Associated issue number.
        pr_number: Associated PR number.

    Returns:
        Created AgentTask object with status "created".
    """
    task_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    conn.execute(
        """
        INSERT INTO agent_tasks
        (id, user_id, provider, repo_full_name, issue_number, pr_number, 
         instruction, status, last_update, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            task_id,
            user_id,
            provider,
            repo_full_name,
            issue_number,
            pr_number,
            instruction,
            "created",
            "Task created",
            now,
            now,
        ],
    )

    return AgentTask(
        id=task_id,
        user_id=user_id,
        provider=provider,
        repo_full_name=repo_full_name,
        issue_number=issue_number,
        pr_number=pr_number,
        instruction=instruction,
        status="created",
        last_update="Task created",
        trace=None,
        created_at=now,
        updated_at=now,
    )


def update_task_status(
    conn: duckdb.DuckDBPyConnection,
    task_id: str,
    status: str,
    last_update: str | None = None,
) -> bool:
    """Update agent task status.

    Valid status transitions:
    - created -> running
    - running -> needs_input | completed | failed
    - needs_input -> running | completed | failed

    Args:
        conn: Database connection.
        task_id: Task ID.
        status: New status (created/running/needs_input/completed/failed).
        last_update: Optional status message.

    Returns:
        True if updated successfully, False if task not found.
    """
    now = datetime.now(UTC)

    # First check if task exists
    existing = conn.execute(
        "SELECT id FROM agent_tasks WHERE id = ?",
        [task_id],
    ).fetchone()

    if not existing:
        return False

    conn.execute(
        """
        UPDATE agent_tasks
        SET status = ?, last_update = ?, updated_at = ?
        WHERE id = ?
        """,
        [status, last_update, now, task_id],
    )

    return True


def get_agent_task(
    conn: duckdb.DuckDBPyConnection,
    task_id: str,
) -> AgentTask | None:
    """Get an agent task by ID.

    Args:
        conn: Database connection.
        task_id: Task ID.

    Returns:
        AgentTask if found, None otherwise.
    """
    result = conn.execute(
        """
        SELECT id, user_id, provider, repo_full_name, issue_number, pr_number,
               instruction, status, last_update, created_at, updated_at
        FROM agent_tasks
        WHERE id = ?
        """,
        [task_id],
    ).fetchone()

    if not result:
        return None

    return AgentTask(
        id=str(result[0]),
        user_id=str(result[1]),
        provider=result[2],
        repo_full_name=result[3],
        issue_number=result[4],
        pr_number=result[5],
        instruction=result[6],
        status=result[7],
        last_update=result[8],
        trace=None,  # TODO: Load from separate table if needed
        created_at=result[9],
        updated_at=result[10],
    )


def get_agent_tasks(
    conn: duckdb.DuckDBPyConnection,
    user_id: str | None = None,
    status: str | None = None,
    provider: str | None = None,
    limit: int = 50,
) -> list[AgentTask]:
    """Query agent tasks with optional filters.

    Args:
        conn: Database connection.
        user_id: Filter by user ID.
        status: Filter by status.
        provider: Filter by provider.
        limit: Maximum number of tasks to return.

    Returns:
        List of AgentTask objects, ordered by updated_at DESC.
    """
    query = """
        SELECT id, user_id, provider, repo_full_name, issue_number, pr_number,
               instruction, status, last_update, created_at, updated_at
        FROM agent_tasks
        WHERE 1=1
    """
    params = []

    if user_id:
        query += " AND user_id = ?"
        params.append(user_id)

    if status:
        query += " AND status = ?"
        params.append(status)

    if provider:
        query += " AND provider = ?"
        params.append(provider)

    query += " ORDER BY updated_at DESC LIMIT ?"
    params.append(limit)

    results = conn.execute(query, params).fetchall()

    return [
        AgentTask(
            id=str(row[0]),
            user_id=str(row[1]),
            provider=row[2],
            repo_full_name=row[3],
            issue_number=row[4],
            pr_number=row[5],
            instruction=row[6],
            status=row[7],
            last_update=row[8],
            trace=None,
            created_at=row[9],
            updated_at=row[10],
        )
        for row in results
    ]


def store_agent_trace(
    conn: duckdb.DuckDBPyConnection,
    task_id: str,
    trace_data: dict[str, Any],
) -> bool:
    """Store agent trace data (links, prompt, tools used).

    For now, this is a stub that could be extended to store
    trace in a separate table or JSON field.

    Args:
        conn: Database connection.
        task_id: Task ID.
        trace_data: Trace information (prompt, tools, links, etc).

    Returns:
        True if stored successfully.
    """
    # For MVP, we can log this or store in memory
    # Future: could add a separate agent_traces table
    return True
