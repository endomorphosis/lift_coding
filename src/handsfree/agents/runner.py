"""Agent task runner module.

Provides a minimal runner loop that can transition tasks through states.
Guarded by HANDSFREE_AGENT_RUNNER_ENABLED environment variable.
"""

import json
import logging
import os
import time
import uuid
from datetime import UTC, datetime
from typing import Any

import duckdb

from handsfree.db.notifications import create_notification
from handsfree.db.agent_tasks import (
    get_agent_task_by_id,
    get_agent_tasks,
    update_agent_task_state,
)

logger = logging.getLogger(__name__)


def is_runner_enabled() -> bool:
    """Check if agent runner is enabled via environment variable.

    Returns:
        True if HANDSFREE_AGENT_RUNNER_ENABLED=true, False otherwise.
    """
    return os.environ.get("HANDSFREE_AGENT_RUNNER_ENABLED", "").lower() == "true"


def get_task_completion_delay() -> int:
    """Get the delay in seconds before auto-completing tasks.

    Returns:
        Delay in seconds (default: 10).
    """
    return int(os.environ.get("HANDSFREE_AGENT_TASK_COMPLETION_DELAY", "10"))


def should_simulate_failure() -> bool:
    """Check if tasks should simulate failure for testing.

    Returns:
        True if HANDSFREE_AGENT_SIMULATE_FAILURE=true, False otherwise.
    """
    return os.environ.get("HANDSFREE_AGENT_SIMULATE_FAILURE", "").lower() == "true"


def auto_start_created_tasks(conn: duckdb.DuckDBPyConnection) -> int:
    """Auto-transition created tasks to running state.

    This simulates the beginning of agent execution without real code changes.
    Creates an optional notification on transition to running.

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

            # Optional: Create notification on transition to running
            # Priority 3 (medium) - may be throttled based on user profile
            try:
                create_notification(
                    conn=conn,
                    user_id=task.user_id,
                    event_type="agent.task_started",
                    message=f"Agent task started: {task.instruction or 'No instruction'}",
                    metadata={
                        "task_id": task.id,
                        "provider": task.provider,
                        "target_type": task.target_type,
                        "target_ref": task.target_ref,
                    },
                    priority=3,
                )
            except Exception as e:
                # Don't fail the task transition if notification creation fails
                logger.warning("Failed to create notification for task %s: %s", task.id, e)

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
            task_uuid = uuid.UUID(task_id)
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


def process_running_task(
    conn: duckdb.DuckDBPyConnection,
    task_id: str,
    simulate_work: bool = True,
) -> tuple[bool, str | None]:
    """Process a running task by simulating work and transitioning to completed or failed.

    This is a minimal "do work" routine that simulates task execution.
    In a real implementation, this would call external agents or execute code.

    Args:
        conn: Database connection.
        task_id: Task ID to process.
        simulate_work: If True, simulate work with a short delay (default: True).

    Returns:
        Tuple of (success, error_message). error_message is None on success.
    """
    try:
        task = get_agent_task_by_id(conn, task_id)
        if not task:
            return False, f"Task {task_id} not found"

        if task.state != "running":
            return False, f"Task {task_id} is not in running state (current: {task.state})"

        logger.info("Processing task %s: %s", task_id, task.instruction or "No instruction")

        # Simulate work (in production, this would call the actual agent provider)
        if simulate_work:
            time.sleep(0.5)  # Minimal delay to simulate work

        # Simulate progress update
        simulate_progress_update(conn, task_id, "Work completed successfully")

        # Transition to completed
        update_agent_task_state(
            conn=conn,
            task_id=task_id,
            new_state="completed",
            trace_update={
                "completed_at": datetime.now(UTC).isoformat(),
                "completed_by": "runner_loop",
                "result": "Task completed successfully (simulated)",
            },
        )
        logger.info("Task %s completed successfully", task_id)
        return True, None

    except ValueError as e:
        # Invalid transition
        error_msg = f"Invalid state transition: {e}"
        logger.warning("Failed to process task %s: %s", task_id, error_msg)
        return False, error_msg
    except Exception as e:
        # Unexpected error - mark task as failed
        error_msg = f"Unexpected error: {e}"
        logger.error("Error processing task %s: %s", task_id, error_msg)
        try:
            update_agent_task_state(
                conn=conn,
                task_id=task_id,
                new_state="failed",
                trace_update={
                    "failed_at": datetime.now(UTC).isoformat(),
                    "failed_by": "runner_loop",
                    "error": error_msg,
                },
            )
        except Exception as fe:
            logger.error("Failed to mark task %s as failed: %s", task_id, fe)
        return False, error_msg


def process_running_tasks(conn: duckdb.DuckDBPyConnection) -> dict[str, int]:
    """Process all running tasks.

    Args:
        conn: Database connection.

    Returns:
        Dictionary with counts of completed, failed, and skipped tasks.
    """
    tasks = get_agent_tasks(conn=conn, state="running", limit=100)

    completed = 0
    failed = 0
    skipped = 0

    for task in tasks:
        success, error = process_running_task(conn, task.id)
        if success:
            completed += 1
        elif error:
            failed += 1
        else:
            skipped += 1

    return {"completed": completed, "failed": failed, "skipped": skipped}


def run_once(conn: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    """Run one iteration of the agent runner loop.

    Performs:
    - Auto-start created tasks
    - Process running tasks to completion or failure

    Args:
        conn: Database connection.

    Returns:
        Dictionary with statistics about the run.
    """
    if not is_runner_enabled():
        return {
            "enabled": False,
            "tasks_started": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "message": "Agent runner is disabled",
        }

    started_count = auto_start_created_tasks(conn)
    process_results = process_running_tasks(conn)

    return {
        "enabled": True,
        "tasks_started": started_count,
        "tasks_completed": process_results["completed"],
        "tasks_failed": process_results["failed"],
        "tasks_skipped": process_results["skipped"],
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
            if result.get("tasks_started", 0) > 0 or result.get("tasks_completed", 0) > 0:
                logger.info(
                    "Runner iteration: started=%d, completed=%d, failed=%d",
                    result.get("tasks_started", 0),
                    result.get("tasks_completed", 0),
                    result.get("tasks_failed", 0),
                )
        except Exception as e:
            logger.error("Error in runner loop iteration: %s", e)

        time.sleep(interval_seconds)
