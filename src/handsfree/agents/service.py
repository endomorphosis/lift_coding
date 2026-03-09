"""Agent orchestration service.

Handles agent task delegation and status queries.
"""

import logging
import os
from datetime import UTC, datetime
from typing import Any
from uuid import NAMESPACE_DNS, UUID, uuid5

import duckdb

from handsfree.agent_providers import get_provider, is_copilot_cli_available
from handsfree.mcp import (
    get_provider_descriptor,
    infer_provider_capability,
    resolve_capability_execution_mode,
    resolve_provider_capability,
)
from handsfree.db.agent_tasks import (
    create_agent_task,
    get_agent_task_by_id,
    get_agent_tasks,
    update_agent_task_trace,
    update_agent_task_state,
)
from handsfree.db.notifications import create_notification

logger = logging.getLogger(__name__)


def _trace_result_envelope(trace: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(trace, dict):
        return None
    envelope = trace.get("mcp_result_envelope")
    return envelope if isinstance(envelope, dict) else None


def _trace_result_preview(trace: dict[str, Any] | None) -> str | None:
    envelope = _trace_result_envelope(trace)
    summary = envelope.get("summary") if envelope else None
    if isinstance(summary, str) and summary.strip():
        return summary.strip()
    preview = (trace or {}).get("mcp_result_preview")
    if isinstance(preview, str) and preview.strip():
        return preview.strip()
    return None


def _trace_result_output(trace: dict[str, Any] | None) -> Any:
    envelope = _trace_result_envelope(trace)
    if envelope and "structured_output" in envelope:
        return envelope.get("structured_output")
    return (trace or {}).get("mcp_result_output")


def _trace_follow_up_actions(trace: dict[str, Any] | None) -> list[dict[str, Any]]:
    envelope = _trace_result_envelope(trace)
    actions = envelope.get("follow_up_actions") if envelope else None
    return actions if isinstance(actions, list) else []


def _requested_local_fallback(preferred_mode: str | None, resolved_mode: str | None) -> bool:
    return (
        str(preferred_mode or "").strip().lower() == "direct_import"
        and str(resolved_mode or "").strip().lower() == "mcp_remote"
    )


def _execution_fallback_message(preferred_mode: str | None, resolved_mode: str | None) -> str | None:
    if _requested_local_fallback(preferred_mode, resolved_mode):
        return "Execution: remote (local unavailable)"
    return None


class AgentService:
    """Service for managing agent task delegation and status."""

    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        """Initialize the agent service.

        Args:
            conn: Database connection.
        """
        self.conn = conn

    def _is_github_dispatch_configured(self) -> bool:
        """Check if github_issue_dispatch provider is configured.

        Returns:
            True if HANDSFREE_AGENT_DISPATCH_REPO and GitHub token are available.
        """
        dispatch_repo = os.getenv("HANDSFREE_AGENT_DISPATCH_REPO")
        github_token = os.getenv("GITHUB_TOKEN")
        return bool(dispatch_repo and github_token)

    def _is_copilot_cli_runnable(self) -> bool:
        """Return whether Copilot CLI can run either live or in fixture mode."""
        if os.getenv("HANDSFREE_CLI_FIXTURE_MODE", "false").lower() == "true":
            return True
        return is_copilot_cli_available()

    def delegate(
        self,
        user_id: str,
        instruction: str | None,
        provider: str | None = None,
        target_type: str | None = None,
        target_ref: str | None = None,
        trace: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a new agent task and start it via the provider.

        Args:
            user_id: User ID creating the task.
            instruction: Instruction for the agent.
            provider: Provider name. If None, uses provider selection precedence:
                     1. HANDSFREE_AGENT_DEFAULT_PROVIDER environment variable
                     2. github_issue_dispatch if configured (HANDSFREE_AGENT_DISPATCH_REPO + token)
                     3. copilot_cli when `gh copilot` is available
                     4. "copilot" as final fallback
            target_type: Type of target ("issue", "pr", or None).
            target_ref: Reference to target (e.g., "owner/repo#123").
            trace: Optional trace information (JSON-serializable).

        Returns:
            Dictionary with task information and spoken confirmation.
        """
        # Determine provider with precedence:
        # 1. Explicit argument
        # 2. HANDSFREE_AGENT_DEFAULT_PROVIDER env var
        # 3. github_issue_dispatch if configured
        # 4. copilot_cli if available
        # 5. copilot as fallback
        if provider is None:
            provider = os.getenv("HANDSFREE_AGENT_DEFAULT_PROVIDER")
            if provider is None:
                # Check if github_issue_dispatch is configured
                if self._is_github_dispatch_configured():
                    provider = "github_issue_dispatch"
                elif self._is_copilot_cli_runnable():
                    provider = "copilot_cli"
                else:
                    provider = "copilot"
        # Merge provided trace with default metadata
        task_trace = trace or {}
        if "created_via" not in task_trace:
            task_trace["created_via"] = "delegate_command"
        provider_descriptor = get_provider_descriptor(provider)
        if provider_descriptor is not None:
            resolved_capability = resolve_provider_capability(
                provider,
                task_trace.get("mcp_capability"),
                instruction,
            )
            task_trace.setdefault("provider_label", provider_descriptor.display_name)
            task_trace.setdefault(
                "mcp_capability",
                resolved_capability or infer_provider_capability(provider, instruction),
            )
            resolved_execution_mode = resolve_capability_execution_mode(
                provider,
                task_trace.get("mcp_capability"),
                task_trace.get("mcp_preferred_execution_mode"),
            )
            if resolved_execution_mode is not None:
                task_trace.setdefault("mcp_execution_mode", resolved_execution_mode)

        # Create task in database (starts in "created" state)
        task = create_agent_task(
            conn=self.conn,
            user_id=user_id,
            provider=provider,
            instruction=instruction,
            target_type=target_type,
            target_ref=target_ref,
            trace=task_trace,
        )

        # Emit "created" notification
        self._emit_notification(
            user_id=user_id,
            event="task_created",
            task_id=task.id,
            message=f"Agent task {task.id} created",
        )

        # Start the task via the provider
        try:
            agent_provider = get_provider(provider)
            start_result = agent_provider.start_task(task)

            if start_result.get("ok"):
                provider_trace = start_result.get("trace", {})
                next_state = "completed" if provider_trace.get("mcp_sync_completed") else "running"
                if next_state == "completed":
                    updated_task = update_agent_task_state(
                        conn=self.conn,
                        task_id=task.id,
                        new_state="running",
                        trace_update=provider_trace,
                    )
                    if updated_task is not None:
                        updated_task = update_agent_task_state(
                            conn=self.conn,
                            task_id=task.id,
                            new_state="completed",
                        )
                else:
                    updated_task = update_agent_task_state(
                        conn=self.conn,
                        task_id=task.id,
                        new_state=next_state,
                        trace_update=provider_trace,
                    )

                if updated_task:
                    if next_state == "completed":
                        self._emit_completion_notification(updated_task, next_state)
                    else:
                        self._emit_notification(
                            user_id=user_id,
                            event="task_running",
                            task_id=task.id,
                            message=f"Agent task {task.id} is now running",
                        )

                    # Update task reference with new state
                    task = updated_task

                    logger.info(
                        "Started task %s with provider %s, transitioned to %s",
                        task.id,
                        provider,
                        next_state,
                    )
            else:
                # Provider failed to start - log but don't fail the delegation
                # Task remains in "created" state for manual intervention or retry
                error_msg = start_result.get("message", "Unknown error")
                logger.warning(
                    "Failed to start task %s with provider %s: %s",
                    task.id,
                    provider,
                    error_msg,
                )

                # Update trace with error information
                error_trace = {
                    "start_error": error_msg,
                    "start_failed_at": datetime.now(UTC).isoformat(),
                }
                updated_task = update_agent_task_trace(
                    conn=self.conn,
                    task_id=task.id,
                    trace_update=error_trace,
                )
                if updated_task:
                    task = updated_task

        except Exception as e:
            # Log exception but don't fail the delegation
            logger.exception("Exception while starting task %s with provider %s", task.id, provider)

            # Update trace with exception information
            error_trace = {
                "start_exception": str(e),
                "start_failed_at": datetime.now(UTC).isoformat(),
            }
            updated_task = update_agent_task_trace(
                conn=self.conn,
                task_id=task.id,
                trace_update=error_trace,
            )
            if updated_task:
                task = updated_task

        # Generate spoken confirmation
        provider_label = provider_descriptor.display_name if provider_descriptor else None
        capability = (
            infer_provider_capability(provider, instruction)
            if provider_descriptor is not None
            else None
        )
        if provider_label and target_type and target_ref:
            spoken = f"{provider_label} task created for {target_type} {target_ref}."
        elif provider_label and capability:
            spoken = f"{provider_label} {capability.replace('_', ' ')} task created."
        elif target_type and target_ref:
            spoken = f"Task created for {target_type} {target_ref}."
        else:
            spoken = "Agent task created."

        if task.trace and task.trace.get("mcp_sync_completed"):
            preview = _trace_result_preview(task.trace)
            if preview:
                spoken = preview
            elif provider_label and capability:
                spoken = f"{provider_label} {capability.replace('_', ' ')} completed."
            elif provider_label:
                spoken = f"{provider_label} completed."
            else:
                spoken = "Agent task completed."

        return {
            "task_id": task.id,
            "state": task.state,
            "provider": task.provider,
            "spoken_text": spoken,
            "result_preview": _trace_result_preview(task.trace),
            "result_output": _trace_result_output(task.trace),
            "follow_up_actions": _trace_follow_up_actions(task.trace),
        }

    def get_status(self, user_id: str) -> dict[str, Any]:
        """Get status summary of agent tasks for a user.

        For mock provider tasks in created or running state, checks provider status
        and auto-advances task state if needed.

        Args:
            user_id: User ID to query tasks for.

        Returns:
            Dictionary with task summary and spoken text.
        """
        # Query all tasks for user
        tasks = get_agent_tasks(conn=self.conn, user_id=user_id, limit=100)

        # Check status of providers that expose pull-based lifecycle updates.
        for task in tasks:
            if task.provider in (
                "mock",
                "ipfs_datasets_mcp",
                "ipfs_kit_mcp",
                "ipfs_accelerate_mcp",
            ) and task.state in ("created", "running"):
                try:
                    # For created tasks, start them first
                    if task.state == "created":
                        agent_provider = get_provider(task.provider)
                        start_result = agent_provider.start_task(task)

                        if start_result.get("ok"):
                            # Transition to "running" state
                            updated_task = update_agent_task_state(
                                conn=self.conn,
                                task_id=task.id,
                                new_state="running",
                                trace_update=start_result.get("trace", {}),
                            )

                            if updated_task:
                                # Emit "running" notification
                                self._emit_notification(
                                    user_id=task.user_id,
                                    event="task_running",
                                    task_id=task.id,
                                    message=f"Agent task {task.id} is now running",
                                )
                                task.state = "running"
                                task.trace = updated_task.trace

                    # For running tasks, check status
                    if task.state == "running":
                        agent_provider = get_provider(task.provider)
                        status_result = agent_provider.check_status(task)

                        if status_result.get("ok"):
                            new_status = status_result.get("status")
                            if new_status and new_status != task.state:
                                # Update task state based on provider response
                                trace_update = status_result.get("trace", {})
                                updated_task = update_agent_task_state(
                                    conn=self.conn,
                                    task_id=task.id,
                                    new_state=new_status,
                                    trace_update=trace_update,
                                )

                                if updated_task:
                                    # Emit notification for state change
                                    if new_status in ("completed", "failed"):
                                        self._emit_completion_notification(updated_task, new_status)
                                    else:
                                        self._emit_notification(
                                            user_id=task.user_id,
                                            event="state_changed",
                                            task_id=task.id,
                                            message=f"Task {task.id} transitioned to {new_status}",
                                        )
                                    # Update the task in the list
                                    task.state = new_status
                                    task.trace = updated_task.trace
                except Exception as e:
                    logger.warning(
                        "Failed to check/advance status for task %s with provider %s: %s",
                        task.id,
                        task.provider,
                        e,
                    )

        # Count by state (using updated states)
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
                    "provider": t.provider,
                    "target_type": t.target_type,
                    "target_ref": t.target_ref,
                    "instruction": t.instruction,
                    "result_preview": _trace_result_preview(t.trace),
                    "result_output": _trace_result_output(t.trace),
                    "result_envelope": _trace_result_envelope(t.trace),
                    "provider_label": (t.trace or {}).get("provider_label") if t.trace else None,
                    "mcp_execution_mode": (t.trace or {}).get("mcp_execution_mode") if t.trace else None,
                    "mcp_preferred_execution_mode": (
                        (t.trace or {}).get("mcp_preferred_execution_mode") if t.trace else None
                    ),
                    "follow_up_actions": _trace_follow_up_actions(t.trace),
                }
                for t in tasks[:10]  # Return up to 10 recent tasks
            ],
            "spoken_text": spoken,
        }

    def _get_task_for_user(self, user_id: str, task_id: str) -> Any:
        """Load a task and enforce user ownership."""
        task = get_agent_task_by_id(conn=self.conn, task_id=task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        try:
            effective_user_id = (
                str(UUID(user_id)) if "-" in user_id else str(uuid5(NAMESPACE_DNS, user_id))
            )
        except (ValueError, AttributeError):
            effective_user_id = str(uuid5(NAMESPACE_DNS, user_id))
        if task.user_id != effective_user_id:
            raise ValueError(f"Task {task_id} not found")
        return task

    def pause_task(
        self,
        user_id: str,
        task_id: str | None = None,
    ) -> dict[str, Any]:
        """Pause a running agent task.

        Args:
            user_id: User ID making the request.
            task_id: Optional task ID to pause. If not provided, pauses most recent running task.

        Returns:
            Dictionary with task information and spoken confirmation.

        Raises:
            ValueError: If task not found or no running tasks available.
        """
        # If no task_id provided, get most recent running task for user
        if not task_id:
            tasks = get_agent_tasks(conn=self.conn, user_id=user_id, state="running", limit=1)
            if not tasks:
                raise ValueError("No running tasks found to pause")
            task_id = tasks[0].id
        else:
            self._get_task_for_user(user_id=user_id, task_id=task_id)

        # Transition from running to needs_input (pause state)
        task = update_agent_task_state(
            conn=self.conn,
            task_id=task_id,
            new_state="needs_input",
            trace_update={"paused_via": "pause_command"},
        )

        if not task:
            raise ValueError(f"Task {task_id} not found")

        # Emit notification
        self._emit_notification(
            user_id=task.user_id,
            event="task_paused",
            task_id=task.id,
            message=f"Agent task {task.id} paused",
        )

        return {
            "task_id": task.id,
            "state": task.state,
            "spoken_text": f"Task {task.id[:8]} paused.",
        }

    def resume_task(
        self,
        user_id: str,
        task_id: str | None = None,
    ) -> dict[str, Any]:
        """Resume a paused agent task.

        Args:
            user_id: User ID making the request.
            task_id: Optional task ID to resume. If not provided, resumes most recent paused task.

        Returns:
            Dictionary with task information and spoken confirmation.

        Raises:
            ValueError: If task not found or no paused tasks available.
        """
        # If no task_id provided, get most recent paused task (needs_input) for user
        if not task_id:
            tasks = get_agent_tasks(conn=self.conn, user_id=user_id, state="needs_input", limit=1)
            if not tasks:
                raise ValueError("No paused tasks found to resume")
            task_id = tasks[0].id
        else:
            self._get_task_for_user(user_id=user_id, task_id=task_id)

        # Transition from needs_input back to running (resume)
        task = update_agent_task_state(
            conn=self.conn,
            task_id=task_id,
            new_state="running",
            trace_update={"resumed_via": "resume_command"},
        )

        if not task:
            raise ValueError(f"Task {task_id} not found")

        # Emit notification
        self._emit_notification(
            user_id=task.user_id,
            event="task_resumed",
            task_id=task.id,
            message=f"Agent task {task.id} resumed",
        )

        return {
            "task_id": task.id,
            "state": task.state,
            "spoken_text": f"Task {task.id[:8]} resumed.",
        }

    def cancel_task(
        self,
        user_id: str,
        task_id: str,
    ) -> dict[str, Any]:
        """Cancel an agent task and mark it failed with cancellation metadata."""
        task = self._get_task_for_user(user_id=user_id, task_id=task_id)
        if task.state not in ("created", "running", "needs_input"):
            raise ValueError(f"Task {task_id} cannot be cancelled from state '{task.state}'")

        trace_update = {
            "cancelled_at": datetime.now(UTC).isoformat(),
            "cancelled_via": "task_control_api",
            "cancelled": True,
        }

        if task.state != "created":
            provider_result = get_provider(task.provider).cancel_task(task)
            if not provider_result.get("ok"):
                raise ValueError(provider_result.get("message", "Failed to cancel task"))
            provider_trace = provider_result.get("trace")
            if isinstance(provider_trace, dict):
                trace_update.update(provider_trace)
            provider_message = provider_result.get("message")
            if isinstance(provider_message, str) and provider_message.strip():
                trace_update["cancel_message"] = provider_message.strip()

        updated_task = update_agent_task_state(
            conn=self.conn,
            task_id=task.id,
            new_state="failed",
            trace_update=trace_update,
        )
        if not updated_task:
            raise ValueError(f"Task {task_id} not found")

        self._emit_notification(
            user_id=updated_task.user_id,
            event="task_cancelled",
            task_id=updated_task.id,
            message=f"Agent task {updated_task.id} cancelled",
        )

        return {
            "task_id": updated_task.id,
            "state": updated_task.state,
            "spoken_text": f"Task {updated_task.id[:8]} cancelled.",
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
            "provider": task.provider,
        }
        if task.instruction:
            metadata["instruction"] = task.instruction

        # Extract PR information from trace if available
        if task.trace:
            if "provider_label" in task.trace:
                metadata["provider_label"] = task.trace["provider_label"]
            if "mcp_capability" in task.trace:
                metadata["mcp_capability"] = task.trace["mcp_capability"]
            if "mcp_cid" in task.trace:
                metadata["mcp_cid"] = task.trace["mcp_cid"]
            if "mcp_execution_mode" in task.trace:
                metadata["mcp_execution_mode"] = task.trace["mcp_execution_mode"]
            if "mcp_preferred_execution_mode" in task.trace:
                metadata["mcp_preferred_execution_mode"] = task.trace[
                    "mcp_preferred_execution_mode"
                ]
            if "mcp_seed_url" in task.trace:
                metadata["mcp_seed_url"] = task.trace["mcp_seed_url"]
            if "mcp_result_preview" in task.trace:
                metadata["result_preview"] = _trace_result_preview(task.trace)
            if "mcp_result_output" in task.trace or "mcp_result_envelope" in task.trace:
                metadata["result_output"] = _trace_result_output(task.trace)
            if "mcp_result_envelope" in task.trace:
                metadata["result_envelope"] = task.trace["mcp_result_envelope"]
            follow_up_actions = _trace_follow_up_actions(task.trace)
            if follow_up_actions:
                metadata["follow_up_actions"] = follow_up_actions
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
        if isinstance(metadata.get("result_preview"), str) and metadata["result_preview"].strip():
            message_parts.append(f"Result: {metadata['result_preview'].strip()}")

        fallback_message = _execution_fallback_message(
            metadata.get("mcp_preferred_execution_mode"),
            metadata.get("mcp_execution_mode"),
        )
        if fallback_message:
            message_parts.append(fallback_message)

        message = ". ".join(message_parts)

        # Create notification
        create_notification(
            conn=self.conn,
            user_id=task.user_id,
            event_type=f"task_{new_state}",
            message=message,
            metadata=metadata,
        )
