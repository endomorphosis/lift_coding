"""Agent task runner module.

Provides a minimal runner loop that can transition tasks through states.
Guarded by HANDSFREE_AGENT_RUNNER_ENABLED environment variable.
"""

import logging
import os
import time
from datetime import UTC, datetime
from typing import Any

import duckdb

from handsfree.db.agent_tasks import get_agent_tasks, update_agent_task_state

logger = logging.getLogger(__name__)


def is_runner_enabled() -> bool:
    """Check if agent runner is enabled via environment variable.

    Returns:
        True if HANDSFREE_AGENT_RUNNER_ENABLED=true, False otherwise.
    """
    return os.environ.get("HANDSFREE_AGENT_RUNNER_ENABLED", "").lower() == "true"


def auto_start_created_tasks(conn: duckdb.DuckDBPyConnection) -> int:
    """Auto-transition created tasks to running state.

    This simulates the beginning of agent execution without real code changes.

    Args:
        conn: Database connection.

    Returns:
        Number of tasks transitioned to running.
    """
    # Get all tasks in 'created' state
    tasks = get_agent_tasks(conn=conn, state="created", limit=100)

    count = 0
    for task in tasks:
        try:
            # Transition to running with trace update
            update_agent_task_state(
                conn=conn,
                task_id=task.id,
                new_state="running",
                trace_update={
                    "auto_started_at": datetime.now(UTC).isoformat(),
                    "auto_started_by": "runner_loop",
                    "progress": "Task started automatically",
                },
            )
            count += 1
            logger.info("Auto-started task %s", task.id)
        except ValueError as e:
            # Invalid transition or task not found
            logger.warning("Failed to auto-start task %s: %s", task.id, e)
        except Exception as e:
            # Unexpected error
            logger.error("Unexpected error auto-starting task %s: %s", task.id, e)

    return count


def simulate_progress_update(
    conn: duckdb.DuckDBPyConnection,
    task_id: str,
    progress_message: str,
) -> bool:
    """Simulate a progress update for a running task.

    Updates the task trace with progress information without changing state.
    Since we can't transition running->running, we directly update the trace field.

    Args:
        conn: Database connection.
        task_id: Task ID to update.
        progress_message: Progress message to add to trace.

    Returns:
        True if update succeeded, False otherwise.
    """
    try:
        import json

        from handsfree.db.agent_tasks import get_agent_task_by_id

        task = get_agent_task_by_id(conn, task_id)
        if not task or task.state != "running":
            return False

        # Update trace directly without changing state
        # Merge new progress info with existing trace
        updated_trace = task.trace or {}
        updated_trace.update(
            {
                "last_progress_at": datetime.now(UTC).isoformat(),
                "progress": progress_message,
            }
        )

        # Update the database directly since we're not changing state
        try:
            task_uuid = __import__("uuid").UUID(task_id)
        except ValueError:
            return False

        conn.execute(
            """
            UPDATE agent_tasks
            SET last_update = ?, updated_at = ?
            WHERE id = ?
            """,
            [json.dumps(updated_trace), datetime.now(UTC), task_uuid],
        )
        return True
    except Exception as e:
        logger.error("Failed to simulate progress for task %s: %s", task_id, e)
        return False


def run_once(conn: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    """Run one iteration of the agent runner loop.

    Performs:
    - Auto-start created tasks
    - (Future: check for completed/failed tasks)

    Args:
        conn: Database connection.

    Returns:
        Dictionary with statistics about the run.
    """
    if not is_runner_enabled():
        return {
            "enabled": False,
            "tasks_started": 0,
            "message": "Agent runner is disabled",
        }

    started_count = auto_start_created_tasks(conn)

    return {
        "enabled": True,
        "tasks_started": started_count,
        "timestamp": datetime.now(UTC).isoformat(),
    }


def run_loop(conn: duckdb.DuckDBPyConnection, interval_seconds: int = 5) -> None:
    """Run the agent runner loop continuously.

    This is a background loop that periodically checks for tasks needing transitions.
    In production, this would be a separate process or background thread.

    Args:
        conn: Database connection.
        interval_seconds: Seconds between loop iterations (default: 5).
    """
    if not is_runner_enabled():
        logger.info("Agent runner loop is disabled (HANDSFREE_AGENT_RUNNER_ENABLED not set)")
        return

    logger.info("Starting agent runner loop (interval: %d seconds)", interval_seconds)

    while True:
        try:
            result = run_once(conn)
            if result["tasks_started"] > 0:
                logger.info("Runner iteration: started %d tasks", result["tasks_started"])
        except Exception as e:
            logger.error("Error in runner loop iteration: %s", e)

        time.sleep(interval_seconds)
