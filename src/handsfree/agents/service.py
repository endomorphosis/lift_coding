"""Agent orchestration service.

Handles agent task delegation and status queries.
"""

from typing import Any

import duckdb

from handsfree.db.agent_tasks import (
    create_agent_task,
    get_agent_tasks,
    update_agent_task_state,
)
from handsfree.db.notifications import create_notification


class AgentService:
    """Service for managing agent task delegation and status."""

    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        """Initialize the agent service.

        Args:
            conn: Database connection.
        """
        self.conn = conn

    def delegate(
        self,
        user_id: str,
        instruction: str | None,
        provider: str = "copilot",
        target_type: str | None = None,
        target_ref: str | None = None,
    ) -> dict[str, Any]:
        """Create a new agent task.

        Args:
            user_id: User ID creating the task.
            instruction: Instruction for the agent.
            provider: Provider name (default: "copilot").
            target_type: Type of target ("issue", "pr", or None).
            target_ref: Reference to target (e.g., "owner/repo#123").

        Returns:
            Dictionary with task information and spoken confirmation.
        """
        # Create task in database
        task = create_agent_task(
            conn=self.conn,
            user_id=user_id,
            provider=provider,
            instruction=instruction,
            target_type=target_type,
            target_ref=target_ref,
            trace={"created_via": "delegate_command"},
        )

        # Log notification (placeholder for now)
        self._emit_notification(
            user_id=user_id,
            event="task_created",
            task_id=task.id,
            message=f"Agent task {task.id} created",
        )

        # Generate spoken confirmation
        if target_type and target_ref:
            spoken = f"Task created for {target_type} {target_ref}."
        else:
            spoken = "Agent task created."

        return {
            "task_id": task.id,
            "state": task.state,
            "spoken_text": spoken,
        }

    def get_status(self, user_id: str) -> dict[str, Any]:
        """Get status summary of agent tasks for a user.

        Args:
            user_id: User ID to query tasks for.

        Returns:
            Dictionary with task summary and spoken text.
        """
        # Query all tasks for user
        tasks = get_agent_tasks(conn=self.conn, user_id=user_id, limit=100)

        # Count by state
        state_counts = {}
        for task in tasks:
            state_counts[task.state] = state_counts.get(task.state, 0) + 1

        total = len(tasks)

        # Generate spoken summary
        if total == 0:
            spoken = "No agent tasks."
        elif total == 1:
            task = tasks[0]
            spoken = f"1 task {task.state}."
        else:
            # Summarize by state
            parts = []
            for state in ["running", "created", "needs_input", "completed", "failed"]:
                count = state_counts.get(state, 0)
                if count > 0:
                    parts.append(f"{count} {state}")

            if parts:
                spoken = f"{total} tasks: " + ", ".join(parts) + "."
            else:
                spoken = f"{total} tasks."

        return {
            "total": total,
            "by_state": state_counts,
            "tasks": [
                {
                    "id": t.id,
                    "state": t.state,
                    "target_type": t.target_type,
                    "target_ref": t.target_ref,
                    "instruction": t.instruction,
                }
                for t in tasks[:10]  # Return up to 10 recent tasks
            ],
            "spoken_text": spoken,
        }

    def advance_task_state(
        self,
        task_id: str,
        new_state: str,
        trace_update: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Advance a task to a new state (for testing/API).

        Args:
            task_id: Task ID to update.
            new_state: New state to transition to.
            trace_update: Optional trace information to add.

        Returns:
            Dictionary with updated task information.

        Raises:
            ValueError: If state transition is invalid or task not found.
        """
        task = update_agent_task_state(
            conn=self.conn,
            task_id=task_id,
            new_state=new_state,
            trace_update=trace_update,
        )

        if not task:
            raise ValueError(f"Task {task_id} not found")

        # For completed/failed tasks, emit a completion notification with PR info
        if new_state in ("completed", "failed"):
            self._emit_completion_notification(task, new_state)
        else:
            # Emit regular state change notification
            self._emit_notification(
                user_id=task.user_id,
                event="state_changed",
                task_id=task.id,
                message=f"Task {task.id} transitioned to {new_state}",
            )

        return {
            "task_id": task.id,
            "state": task.state,
            "updated_at": task.updated_at.isoformat(),
        }

    def _emit_notification(
        self,
        user_id: str,
        event: str,
        task_id: str,
        message: str,
    ) -> None:
        """Emit a user-facing notification.

        Persists notification to the database for poll-based retrieval.

        Args:
            user_id: User to notify.
            event: Event type.
            task_id: Related task ID.
            message: Notification message.
        """
        # Write notification to database
        create_notification(
            conn=self.conn,
            user_id=user_id,
            event_type=event,
            message=message,
            metadata={"task_id": task_id},
        )

    def _emit_completion_notification(
        self,
        task: Any,
        new_state: str,
    ) -> None:
        """Emit a completion notification for completed/failed tasks.

        Includes PR link/reference from trace if available.

        Args:
            task: The AgentTask object.
            new_state: The new state (completed or failed).
        """
        # Build metadata with task_id and state
        metadata = {
            "task_id": task.id,
            "state": new_state,
        }

        # Extract PR information from trace if available
        if task.trace:
            # Check for PR URL
            if "pr_url" in task.trace:
                metadata["pr_url"] = task.trace["pr_url"]
            
            # Check for PR number
            if "pr_number" in task.trace:
                metadata["pr_number"] = task.trace["pr_number"]
            
            # Check for repo full name
            if "repo_full_name" in task.trace:
                metadata["repo_full_name"] = task.trace["repo_full_name"]

        # Build message with PR reference if available
        message_parts = [f"Agent task {task.id} {new_state}"]
        if "pr_url" in metadata:
            message_parts.append(f"PR: {metadata['pr_url']}")
        elif "pr_number" in metadata and "repo_full_name" in metadata:
            message_parts.append(f"PR: {metadata['repo_full_name']}#{metadata['pr_number']}")
        elif "pr_number" in metadata:
            message_parts.append(f"PR #{metadata['pr_number']}")

        message = ". ".join(message_parts)

        # Create notification
        create_notification(
            conn=self.conn,
            user_id=task.user_id,
            event_type=f"task_{new_state}",
            message=message,
            metadata=metadata,
        )
