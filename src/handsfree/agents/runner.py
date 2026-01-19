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

from handsfree.db.agent_tasks import get_agent_task_by_id, get_agent_tasks, update_agent_task_state
from handsfree.db.notifications import create_notification

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


def process_running_tasks(conn: duckdb.DuckDBPyConnection) -> dict[str, int]:
    """Process running tasks and transition them to completed or failed.

    For each running task:
    1. Add progress updates if the task has been running for a while
    2. Check if the task has been running long enough to complete
    3. Transition to completed (or failed if configured) and create notification

    Args:
        conn: Database connection.

    Returns:
        Dictionary with counts of progressed, completed, and failed tasks.
    """
    tasks = get_agent_tasks(conn=conn, state="running", limit=100)

    progressed_count = 0
    completed_count = 0
    failed_count = 0

    completion_delay = get_task_completion_delay()
    simulate_failure = should_simulate_failure()

    now = datetime.now(UTC)

    for task in tasks:
        try:
            # Extract auto_started_at from trace
            auto_started_at_str = (task.trace or {}).get("auto_started_at")
            if not auto_started_at_str:
                # If no start time recorded, skip this task
                logger.warning("Task %s has no auto_started_at in trace, skipping", task.id)
                continue

            # Parse the start time - handle both Z and +00:00 formats
            try:
                auto_started_at = datetime.fromisoformat(auto_started_at_str)
            except ValueError:
                try:
                    # Try with Z replaced if fromisoformat fails
                    auto_started_at = datetime.fromisoformat(auto_started_at_str.replace("Z", "+00:00"))
                except ValueError as e:
                    logger.warning(
                        "Task %s has invalid auto_started_at datetime '%s': %s; skipping",
                        task.id,
                        auto_started_at_str,
                        e,
                    )
                    continue

            # Calculate elapsed time
            elapsed = (now - auto_started_at).total_seconds()

            # Add progress update if task has been running for at least half the completion delay
            # and hasn't had a recent progress update
            last_progress_at_str = (task.trace or {}).get("last_progress_at")
            if elapsed >= completion_delay / 2:
                # Check if we already added a progress update
                if not last_progress_at_str:
                    progress_msg = f"Task in progress... (elapsed: {int(elapsed)}s)"
                    if simulate_progress_update(conn, task.id, progress_msg):
                        progressed_count += 1
                        logger.info("Added progress update to task %s", task.id)

            # Check if task should complete or fail
            if elapsed >= completion_delay:
                if simulate_failure:
                    # Transition to failed
                    update_agent_task_state(
                        conn=conn,
                        task_id=task.id,
                        new_state="failed",
                        trace_update={
                            "completed_at": now.isoformat(),
                            "completed_by": "runner_loop",
                            "result": "simulated_failure",
                            "error": "Task failed for testing purposes",
                        },
                    )
                    failed_count += 1
                    logger.info("Auto-failed task %s (simulated failure)", task.id)

                    # Create notification for failure (priority 4 - important)
                    try:
                        create_notification(
                            conn=conn,
                            user_id=task.user_id,
                            event_type="agent.task_failed",
                            message=f"Agent task failed: {task.instruction or 'No instruction'}",
                            metadata={
                                "task_id": task.id,
                                "provider": task.provider,
                                "target_type": task.target_type,
                                "target_ref": task.target_ref,
                                "error": "Task failed for testing purposes",
                            },
                            priority=4,
                        )
                    except Exception as e:
                        logger.warning("Failed to create failure notification for task %s: %s", task.id, e)

                else:
                    # Transition to completed
                    update_agent_task_state(
                        conn=conn,
                        task_id=task.id,
                        new_state="completed",
                        trace_update={
                            "completed_at": now.isoformat(),
                            "completed_by": "runner_loop",
                            "result": "success",
                            "summary": "Task completed successfully (simulated)",
                        },
                    )
                    completed_count += 1
                    logger.info("Auto-completed task %s", task.id)

                    # Create notification for completion (priority 4 - important)
                    try:
                        create_notification(
                            conn=conn,
                            user_id=task.user_id,
                            event_type="agent.task_completed",
                            message=f"Agent task completed: {task.instruction or 'No instruction'}",
                            metadata={
                                "task_id": task.id,
                                "provider": task.provider,
                                "target_type": task.target_type,
                                "target_ref": task.target_ref,
                                "summary": "Task completed successfully (simulated)",
                            },
                            priority=4,
                        )
                    except Exception as e:
                        logger.warning("Failed to create completion notification for task %s: %s", task.id, e)

        except ValueError as e:
            # Invalid transition or task not found
            logger.warning("Failed to process running task %s: %s", task.id, e)
        except Exception as e:
            # Unexpected error
            logger.error("Unexpected error processing running task %s: %s", task.id, e)

    return {
        "progressed": progressed_count,
        "completed": completed_count,
        "failed": failed_count,
    }


def run_once(conn: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    """Run one iteration of the agent runner loop.

    Performs:
    - Auto-start created tasks
    - Process running tasks (progress updates and completion)

    Args:
        conn: Database connection.

    Returns:
        Dictionary with statistics about the run.
    """
    if not is_runner_enabled():
        return {
            "enabled": False,
            "tasks_started": 0,
            "tasks_progressed": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "message": "Agent runner is disabled",
        }

    started_count = auto_start_created_tasks(conn)
    running_stats = process_running_tasks(conn)

    return {
        "enabled": True,
        "tasks_started": started_count,
        "tasks_progressed": running_stats["progressed"],
        "tasks_completed": running_stats["completed"],
        "tasks_failed": running_stats["failed"],
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
            if result["tasks_started"] > 0 or result["tasks_completed"] > 0 or result["tasks_failed"] > 0:
                logger.info(
                    "Runner iteration: started=%d, progressed=%d, completed=%d, failed=%d",
                    result["tasks_started"],
                    result["tasks_progressed"],
                    result["tasks_completed"],
                    result["tasks_failed"],
                )
        except Exception as e:
            logger.error("Error in runner loop iteration: %s", e)

        time.sleep(interval_seconds)
