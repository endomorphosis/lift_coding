"""Pydantic models aligned with spec/openapi.yaml."""

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class Profile(str, Enum):
    """Profile enum."""

    WORKOUT = "workout"
    KITCHEN = "kitchen"
    COMMUTE = "commute"
    DEFAULT = "default"


class PrivacyMode(str, Enum):
    """Privacy mode enum for controlling data exposure in responses."""

    STRICT = "strict"  # No images, no code snippets, summaries only
    BALANCED = "balanced"  # Small excerpts permitted with redaction
    DEBUG = "debug"  # Verbose (never default)


class TextInput(BaseModel):
    """Text input schema."""

    type: Literal["text"] = "text"
    text: str = Field(..., max_length=2000)


class AudioFormat(str, Enum):
    """Audio format enum."""

    WAV = "wav"
    M4A = "m4a"
    MP3 = "mp3"
    OPUS = "opus"


class AudioInput(BaseModel):
    """Audio input schema."""

    type: Literal["audio"] = "audio"
    format: AudioFormat
    uri: str
    duration_ms: int | None = Field(default=None, ge=0)


class ImageInput(BaseModel):
    """Image input schema for camera snapshots."""

    type: Literal["image"] = "image"
    uri: str = Field(
        ...,
        description="URI to the image/camera snapshot (not fetched or processed yet)",
    )
    content_type: str | None = Field(
        default=None,
        description="MIME type of the image (e.g., image/jpeg, image/png)",
        examples=["image/jpeg"],
    )


class ClientContext(BaseModel):
    """Client context."""

    device: str
    locale: str = Field(..., examples=["en-US"])
    timezone: str = Field(..., examples=["America/Los_Angeles"])
    app_version: str = Field(..., examples=["0.1.0"])
    noise_mode: bool = False
    debug: bool = False
    privacy_mode: PrivacyMode = PrivacyMode.STRICT


class CommandRequest(BaseModel):
    """Command request."""

    input: TextInput | AudioInput | ImageInput
    profile: Profile
    client_context: ClientContext
    idempotency_key: str | None = None


class ActionCommandRequest(BaseModel):
    """Structured action command request."""

    action_id: str = Field(
        ...,
        description=(
            "Stable card action identifier such as read_cid or rerun_dataset_search. "
            "Some client-local actions may also use mobile_* identifiers such as "
            "mobile_open_wearables_diagnostics."
        ),
    )
    params: dict[str, Any] = Field(default_factory=dict)
    profile: Profile
    client_context: ClientContext
    idempotency_key: str | None = None


class ParsedIntent(BaseModel):
    """Parsed intent."""

    name: str = Field(..., examples=["inbox.list"])
    confidence: float = Field(..., ge=0.0, le=1.0)
    entities: dict[str, Any] = Field(default_factory=dict)


class PendingAction(BaseModel):
    """Pending action."""

    token: str
    expires_at: datetime
    summary: str


class ActionItem(BaseModel):
    """Structured card action metadata."""

    id: str = Field(
        ...,
        description=(
            "Stable action identifier. Server-routed actions are suitable for POST "
            "/v1/commands/action, while some app-local actions may use mobile_* IDs "
            "such as mobile_open_wearables_diagnostics."
        ),
    )
    label: str
    phrase: str
    execution_mode: str | None = None
    execution_mode_label: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)


class UICard(BaseModel):
    """UI card."""

    title: str
    subtitle: str | None = None
    lines: list[str] = Field(default_factory=list)
    deep_link: str | None = None
    actions: list[str] = Field(default_factory=list)
    action_items: list[ActionItem] = Field(default_factory=list)


class DebugInfo(BaseModel):
    """Debug info."""

    transcript: str | None = None
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    profile_metadata: dict[str, Any] | None = None  # Optional profile info (speech_rate, etc.)


class CommandStatus(str, Enum):
    """Command status."""

    OK = "ok"
    NEEDS_CONFIRMATION = "needs_confirmation"
    ERROR = "error"


class FollowOnTask(BaseModel):
    """Explicit spawned-task metadata attached to command responses."""

    model_config = {
        "json_schema_extra": {
            "example": {
                "task_id": "task-9b2b1d9d",
                "state": "running",
                "provider": "ipfs_accelerate_mcp",
                "provider_label": "IPFS Accelerate",
                "capability": "agentic_fetch",
                "summary": "IPFS Accelerate agentic fetch running.",
                "mcp_execution_mode": "mcp_remote",
                "mcp_preferred_execution_mode": "direct_import",
                "result_preview": "Connectivity receipt captured",
            }
        }
    }

    task_id: str
    state: str | None = None
    provider: str | None = None
    provider_label: str | None = None
    capability: str | None = None
    summary: str | None = None
    mcp_execution_mode: str | None = None
    mcp_preferred_execution_mode: str | None = None
    result_preview: str | None = None


class CommandResponse(BaseModel):
    """Command response."""

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "ok",
                "intent": {
                    "name": "agent.result_rerun",
                    "confidence": 1.0,
                    "entities": {
                        "task_id": "task-9b2b1d9d",
                    },
                },
                "spoken_text": "Workflow rerun requested.",
                "cards": [],
                "pending_action": None,
                "follow_on_task": {
                    "task_id": "task-9b2b1d9d",
                    "state": "running",
                    "provider": "ipfs_accelerate_mcp",
                    "provider_label": "IPFS Accelerate",
                    "capability": "agentic_fetch",
                    "summary": "IPFS Accelerate agentic fetch running.",
                },
                "debug": {
                    "transcript": "rerun that fetch with https://example.com",
                    "tool_calls": [
                        {
                            "task_id": "task-9b2b1d9d",
                            "provider": "ipfs_accelerate_mcp",
                            "state": "running",
                        }
                    ],
                },
            }
            ,
            "examples": [
                {
                    "status": "ok",
                    "intent": {
                        "name": "agent.result_rerun",
                        "confidence": 1.0,
                        "entities": {
                            "task_id": "task-9b2b1d9d",
                        },
                    },
                    "spoken_text": "Workflow rerun requested.",
                    "cards": [],
                    "pending_action": None,
                    "follow_on_task": {
                        "task_id": "task-9b2b1d9d",
                        "state": "running",
                        "provider": "ipfs_accelerate_mcp",
                        "provider_label": "IPFS Accelerate",
                        "capability": "agentic_fetch",
                        "summary": "IPFS Accelerate agentic fetch running.",
                    },
                },
                {
                    "status": "needs_confirmation",
                    "intent": {
                        "name": "pr.merge",
                        "confidence": 1.0,
                        "entities": {
                            "pr_number": 456,
                        },
                    },
                    "spoken_text": "Ready to merge PR 456. Say confirm to proceed.",
                    "cards": [],
                    "pending_action": {
                        "token": "conf-abc123xyz",
                        "expires_at": "2026-01-17T01:00:00Z",
                        "summary": "Merge PR #456 in owner/repo",
                    },
                    "follow_on_task": None,
                },
            ],
        }
    }

    status: CommandStatus
    intent: ParsedIntent
    spoken_text: str
    cards: list[UICard] = Field(default_factory=list)
    pending_action: PendingAction | None = None
    follow_on_task: FollowOnTask | None = None
    debug: DebugInfo | None = None


class AgentTaskControlResponse(BaseModel):
    """Typed response for task lifecycle control endpoints."""

    task_id: str
    state: str
    message: str
    updated_at: str | None = None


class ConfirmRequest(BaseModel):
    """Confirm request."""

    token: str
    idempotency_key: str | None = None


class InboxItemType(str, Enum):
    """Inbox item type."""

    PR = "pr"
    MENTION = "mention"
    CHECK = "check"
    AGENT = "agent"


class InboxItem(BaseModel):
    """Inbox item."""

    type: InboxItemType
    title: str
    priority: int = Field(..., ge=1, le=5)
    repo: str | None = None
    url: str | None = None
    summary: str | None = None
    checks_passed: int | None = Field(default=None, ge=0)
    checks_failed: int | None = Field(default=None, ge=0)
    checks_pending: int | None = Field(default=None, ge=0)


class InboxResponse(BaseModel):
    """Inbox response."""

    items: list[InboxItem]


class RequestReviewRequest(BaseModel):
    """Request review request."""

    repo: str = Field(..., examples=["owner/name"])
    pr_number: int = Field(..., ge=1)
    reviewers: list[str]
    idempotency_key: str | None = None


class RerunChecksRequest(BaseModel):
    """Rerun checks request."""

    repo: str
    pr_number: int = Field(..., ge=1)
    idempotency_key: str | None = None


class MergeMethod(str, Enum):
    """Merge method."""

    MERGE = "merge"
    SQUASH = "squash"
    REBASE = "rebase"


class MergeRequest(BaseModel):
    """Merge request."""

    repo: str
    pr_number: int = Field(..., ge=1)
    merge_method: MergeMethod = MergeMethod.SQUASH
    idempotency_key: str | None = None


class CommentRequest(BaseModel):
    """PR comment request."""

    repo: str
    pr_number: int = Field(..., ge=1)
    comment_body: str
    idempotency_key: str | None = None


class ActionResult(BaseModel):
    """Action result."""

    ok: bool
    message: str
    url: str | None = None


class AICapabilityContext(BaseModel):
    """API-facing AI capability context."""

    repo: str | None = None
    pr_number: int | None = Field(default=None, ge=1)
    workflow_name: str | None = None
    check_name: str | None = None
    failure_target: str | None = None
    failure_target_type: str | None = None
    session_id: str | None = None


class AIWorkflow(str, Enum):
    """Higher-level AI workflow aliases for API callers."""

    COPILOT_EXPLAIN_PR = "copilot_explain_pr"
    COPILOT_SUMMARIZE_DIFF = "copilot_summarize_diff"
    COPILOT_EXPLAIN_FAILURE = "copilot_explain_failure"
    PR_RAG_SUMMARY = "pr_rag_summary"
    ACCELERATED_PR_SUMMARY = "accelerated_pr_summary"
    FAILURE_RAG_EXPLAIN = "failure_rag_explain"
    ACCELERATED_FAILURE_EXPLAIN = "accelerated_failure_explain"
    FIND_SIMILAR_FAILURES = "find_similar_failures"
    READ_STORED_OUTPUT = "read_stored_output"
    ACCELERATE_GENERATE_AND_STORE = "accelerate_generate_and_store"


class AISummaryBackend(str, Enum):
    """Backend selection for PR summary workflows."""

    DEFAULT = "default"
    ACCELERATED = "accelerated"


class AIFailureAnalysisBackend(str, Enum):
    """Backend selection for failure analysis workflows."""

    DEFAULT = "default"
    ACCELERATED = "accelerated"


class AIGenerationOptions(BaseModel):
    """Typed generation options for AI capability execution."""

    model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = Field(default=None, ge=1)
    extra: dict[str, Any] = Field(default_factory=dict)

    def to_kwargs(self) -> dict[str, Any]:
        """Convert typed generation options to backend kwargs."""
        kwargs: dict[str, Any] = dict(self.extra)
        if self.model is not None:
            kwargs["model"] = self.model
        if self.temperature is not None:
            kwargs["temperature"] = self.temperature
        if self.max_tokens is not None:
            kwargs["max_tokens"] = self.max_tokens
        return kwargs


class AIEmbeddingOptions(BaseModel):
    """Typed embedding options for AI capability execution."""

    model: str | None = None
    dimensions: int | None = Field(default=None, ge=1)
    extra: dict[str, Any] = Field(default_factory=dict)

    def to_kwargs(self) -> dict[str, Any]:
        """Convert typed embedding options to backend kwargs."""
        kwargs: dict[str, Any] = dict(self.extra)
        if self.model is not None:
            kwargs["model"] = self.model
        if self.dimensions is not None:
            kwargs["dimensions"] = self.dimensions
        return kwargs


class AIIPFSOptions(BaseModel):
    """Typed IPFS storage options for AI capability execution."""

    pin: bool | None = None
    extra: dict[str, Any] = Field(default_factory=dict)

    def to_kwargs(self) -> dict[str, Any]:
        """Convert typed IPFS options to backend kwargs."""
        kwargs: dict[str, Any] = dict(self.extra)
        if self.pin is not None:
            kwargs["pin"] = self.pin
        return kwargs


class AICapabilityExecuteRequest(BaseModel):
    """API request for executing a shared AI capability."""

    capability_id: str | None = None
    workflow: AIWorkflow | None = None
    profile: Profile = Profile.DEFAULT
    context: AICapabilityContext = Field(default_factory=AICapabilityContext)
    inputs: dict[str, Any] = Field(default_factory=dict)
    persist_output: bool | None = None
    generation: AIGenerationOptions | None = None
    embeddings: AIEmbeddingOptions | None = None
    ipfs: AIIPFSOptions | None = None
    options: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = None

    _WORKFLOW_MAP = {
        AIWorkflow.COPILOT_EXPLAIN_PR: "copilot.pr.explain",
        AIWorkflow.COPILOT_SUMMARIZE_DIFF: "copilot.pr.diff_summary",
        AIWorkflow.COPILOT_EXPLAIN_FAILURE: "copilot.pr.failure_explain",
        AIWorkflow.PR_RAG_SUMMARY: "github.pr.rag_summary",
        AIWorkflow.ACCELERATED_PR_SUMMARY: "github.pr.accelerated_summary",
        AIWorkflow.FAILURE_RAG_EXPLAIN: "github.check.failure_rag_explain",
        AIWorkflow.ACCELERATED_FAILURE_EXPLAIN: "github.check.accelerated_failure_explain",
        AIWorkflow.FIND_SIMILAR_FAILURES: "github.check.find_similar_failures",
        AIWorkflow.READ_STORED_OUTPUT: "ipfs.content.read_ai_output",
        AIWorkflow.ACCELERATE_GENERATE_AND_STORE: "ipfs.accelerate.generate_and_store",
    }

    def resolve_capability_id(self) -> str:
        """Resolve the concrete capability ID from capability_id or workflow."""
        if self.capability_id:
            return self.capability_id

        if self.workflow is None:
            raise ValueError("Either capability_id or workflow must be provided")
        return self._WORKFLOW_MAP[self.workflow]

    def resolve_workflow(self) -> AIWorkflow | None:
        """Resolve the workflow alias from workflow or capability_id."""
        if self.workflow is not None:
            return self.workflow

        if self.capability_id is None:
            return None

        for workflow, capability_id in self._WORKFLOW_MAP.items():
            if capability_id == self.capability_id:
                return workflow
        return None

    def normalized_context(self) -> AICapabilityContext:
        """Return context with workflow/check aliases normalized for execution."""
        context = self.context.model_copy(deep=True)

        if context.workflow_name:
            if context.failure_target and context.failure_target != context.workflow_name:
                raise ValueError("workflow_name conflicts with context.failure_target")
            if context.failure_target_type and context.failure_target_type != "workflow":
                raise ValueError("workflow_name conflicts with context.failure_target_type")
            context.failure_target = context.workflow_name
            context.failure_target_type = "workflow"

        if context.check_name:
            if context.failure_target and context.failure_target != context.check_name:
                raise ValueError("check_name conflicts with context.failure_target")
            if context.failure_target_type and context.failure_target_type != "check":
                raise ValueError("check_name conflicts with context.failure_target_type")
            context.failure_target = context.check_name
            context.failure_target_type = "check"

        return context

    def validate_execution_requirements(self) -> None:
        """Validate workflow/capability-specific execution requirements."""
        resolved_capability_id = self.resolve_capability_id()
        context = self.normalized_context()

        if resolved_capability_id in {
            "copilot.pr.explain",
            "copilot.pr.diff_summary",
            "copilot.pr.failure_explain",
            "github.pr.rag_summary",
            "github.pr.accelerated_summary",
            "github.check.failure_rag_explain",
            "github.check.accelerated_failure_explain",
            "github.check.find_similar_failures",
        } and context.pr_number is None:
            raise ValueError(f"{resolved_capability_id} requires context.pr_number")

        if resolved_capability_id == "ipfs.accelerate.generate_and_store":
            prompt = self.inputs.get("prompt") or self.options.get("prompt")
            if not prompt:
                raise ValueError("ipfs.accelerate.generate_and_store requires inputs.prompt or options.prompt")

        if resolved_capability_id == "ipfs.content.read_ai_output":
            cid = self.inputs.get("cid") or self.options.get("cid")
            if not cid:
                raise ValueError("ipfs.content.read_ai_output requires inputs.cid or options.cid")

        if bool(context.failure_target_type) != bool(context.failure_target):
            raise ValueError("failure_target and failure_target_type must be provided together")

    def build_options_dict(self) -> dict[str, Any]:
        """Merge typed options with legacy generic options."""
        merged = dict(self.options)
        if self.persist_output is not None:
            merged["persist_output"] = self.persist_output
        if self.generation is not None:
            merged["generation_options"] = self.generation.to_kwargs()
        if self.embeddings is not None:
            merged["embedding_options"] = self.embeddings.to_kwargs()
        if self.ipfs is not None:
            merged["ipfs_options"] = self.ipfs.to_kwargs()
        return merged


class AIWorkflowExecuteRequestBase(BaseModel):
    """Base typed API request for workflow-specific AI execution."""

    profile: Profile = Profile.DEFAULT
    persist_output: bool | None = None
    generation: AIGenerationOptions | None = None
    embeddings: AIEmbeddingOptions | None = None
    ipfs: AIIPFSOptions | None = None
    options: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = None

    def _base_execute_kwargs(self) -> dict[str, Any]:
        return {
            "profile": self.profile,
            "persist_output": self.persist_output,
            "generation": self.generation,
            "embeddings": self.embeddings,
            "ipfs": self.ipfs,
            "options": self.options,
            "idempotency_key": self.idempotency_key,
        }


class AIPRRAGSummaryExecuteRequest(AIWorkflowExecuteRequestBase):
    """Typed request for the PR RAG summary workflow."""

    pr_number: int = Field(..., ge=1)
    repo: str | None = None
    session_id: str | None = None
    summary_backend: AISummaryBackend | None = None

    def to_execute_request(self) -> AICapabilityExecuteRequest:
        """Convert to the generic execute request shape."""
        return AICapabilityExecuteRequest(
            workflow=(
                AIWorkflow.ACCELERATED_PR_SUMMARY
                if self.summary_backend == AISummaryBackend.ACCELERATED
                else AIWorkflow.PR_RAG_SUMMARY
            ),
            context=AICapabilityContext(
                repo=self.repo,
                pr_number=self.pr_number,
                session_id=self.session_id,
            ),
            **self._base_execute_kwargs(),
        )


class AIAcceleratedPRSummaryExecuteRequest(AIWorkflowExecuteRequestBase):
    """Typed request for the accelerated PR summary workflow."""

    pr_number: int = Field(..., ge=1)
    repo: str | None = None
    session_id: str | None = None

    def to_execute_request(self) -> AICapabilityExecuteRequest:
        """Convert to the generic execute request shape."""
        return AICapabilityExecuteRequest(
            workflow=AIWorkflow.ACCELERATED_PR_SUMMARY,
            context=AICapabilityContext(
                repo=self.repo,
                pr_number=self.pr_number,
                session_id=self.session_id,
            ),
            **self._base_execute_kwargs(),
        )


class AICopilotExplainPRExecuteRequest(AIWorkflowExecuteRequestBase):
    """Typed request for the Copilot PR explanation workflow."""

    pr_number: int = Field(..., ge=1)
    repo: str | None = None
    session_id: str | None = None

    def to_execute_request(self) -> AICapabilityExecuteRequest:
        """Convert to the generic execute request shape."""
        return AICapabilityExecuteRequest(
            workflow=AIWorkflow.COPILOT_EXPLAIN_PR,
            context=AICapabilityContext(
                repo=self.repo,
                pr_number=self.pr_number,
                session_id=self.session_id,
            ),
            **self._base_execute_kwargs(),
        )


class AICopilotSummarizeDiffExecuteRequest(AIWorkflowExecuteRequestBase):
    """Typed request for the Copilot diff summary workflow."""

    pr_number: int = Field(..., ge=1)
    repo: str | None = None
    session_id: str | None = None

    def to_execute_request(self) -> AICapabilityExecuteRequest:
        """Convert to the generic execute request shape."""
        return AICapabilityExecuteRequest(
            workflow=AIWorkflow.COPILOT_SUMMARIZE_DIFF,
            context=AICapabilityContext(
                repo=self.repo,
                pr_number=self.pr_number,
                session_id=self.session_id,
            ),
            **self._base_execute_kwargs(),
        )


class AICopilotExplainFailureExecuteRequest(AIWorkflowExecuteRequestBase):
    """Typed request for the Copilot failure explanation workflow."""

    pr_number: int = Field(..., ge=1)
    repo: str | None = None
    session_id: str | None = None
    workflow_name: str | None = None
    check_name: str | None = None
    failure_target: str | None = None
    failure_target_type: str | None = None

    @model_validator(mode="after")
    def _validate_failure_target_shape(self) -> "AICopilotExplainFailureExecuteRequest":
        if self.workflow_name and self.check_name:
            raise ValueError("workflow_name and check_name are mutually exclusive")
        if bool(self.failure_target) != bool(self.failure_target_type):
            raise ValueError("failure_target and failure_target_type must be provided together")
        return self

    def to_execute_request(self) -> AICapabilityExecuteRequest:
        """Convert to the generic execute request shape."""
        return AICapabilityExecuteRequest(
            workflow=AIWorkflow.COPILOT_EXPLAIN_FAILURE,
            context=AICapabilityContext(
                repo=self.repo,
                pr_number=self.pr_number,
                workflow_name=self.workflow_name,
                check_name=self.check_name,
                failure_target=self.failure_target,
                failure_target_type=self.failure_target_type,
                session_id=self.session_id,
            ),
            **self._base_execute_kwargs(),
        )


class AIFailureRAGExplainExecuteRequest(AIWorkflowExecuteRequestBase):
    """Typed request for the failure RAG explain workflow."""

    pr_number: int = Field(..., ge=1)
    repo: str | None = None
    session_id: str | None = None
    workflow_name: str | None = None
    check_name: str | None = None
    failure_target: str | None = None
    failure_target_type: str | None = None
    history_cids: list[str] = Field(default_factory=list)
    failure_backend: AIFailureAnalysisBackend | None = None

    @model_validator(mode="after")
    def _validate_failure_target_shape(self) -> "AIFailureRAGExplainExecuteRequest":
        if self.workflow_name and self.check_name:
            raise ValueError("workflow_name and check_name are mutually exclusive")
        if bool(self.failure_target) != bool(self.failure_target_type):
            raise ValueError("failure_target and failure_target_type must be provided together")
        return self

    def to_execute_request(self) -> AICapabilityExecuteRequest:
        """Convert to the generic execute request shape."""
        return AICapabilityExecuteRequest(
            workflow=(
                AIWorkflow.ACCELERATED_FAILURE_EXPLAIN
                if self.failure_backend == AIFailureAnalysisBackend.ACCELERATED
                else AIWorkflow.FAILURE_RAG_EXPLAIN
            ),
            context=AICapabilityContext(
                repo=self.repo,
                pr_number=self.pr_number,
                workflow_name=self.workflow_name,
                check_name=self.check_name,
                failure_target=self.failure_target,
                failure_target_type=self.failure_target_type,
                session_id=self.session_id,
            ),
            inputs={"history_cids": self.history_cids} if self.history_cids else {},
            **self._base_execute_kwargs(),
        )


class AIAcceleratedFailureExplainExecuteRequest(AIWorkflowExecuteRequestBase):
    """Typed request for the accelerated failure explanation workflow."""

    pr_number: int = Field(..., ge=1)
    repo: str | None = None
    session_id: str | None = None
    workflow_name: str | None = None
    check_name: str | None = None
    failure_target: str | None = None
    failure_target_type: str | None = None
    history_cids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_failure_target_shape(self) -> "AIAcceleratedFailureExplainExecuteRequest":
        if self.workflow_name and self.check_name:
            raise ValueError("workflow_name and check_name are mutually exclusive")
        if bool(self.failure_target) != bool(self.failure_target_type):
            raise ValueError("failure_target and failure_target_type must be provided together")
        return self

    def to_execute_request(self) -> AICapabilityExecuteRequest:
        """Convert to the generic execute request shape."""
        return AICapabilityExecuteRequest(
            workflow=AIWorkflow.ACCELERATED_FAILURE_EXPLAIN,
            context=AICapabilityContext(
                repo=self.repo,
                pr_number=self.pr_number,
                workflow_name=self.workflow_name,
                check_name=self.check_name,
                failure_target=self.failure_target,
                failure_target_type=self.failure_target_type,
                session_id=self.session_id,
            ),
            inputs={"history_cids": self.history_cids} if self.history_cids else {},
            **self._base_execute_kwargs(),
        )


class AIFindSimilarFailuresExecuteRequest(AIWorkflowExecuteRequestBase):
    """Typed request for the similar-failure retrieval workflow."""

    pr_number: int = Field(..., ge=1)
    history_candidates: list[Any] = Field(default_factory=list)
    repo: str | None = None
    session_id: str | None = None
    workflow_name: str | None = None
    check_name: str | None = None
    failure_target: str | None = None
    failure_target_type: str | None = None
    history_cids: list[str] = Field(default_factory=list)
    top_k: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def _validate_failure_target_shape(self) -> "AIFindSimilarFailuresExecuteRequest":
        if self.workflow_name and self.check_name:
            raise ValueError("workflow_name and check_name are mutually exclusive")
        if bool(self.failure_target) != bool(self.failure_target_type):
            raise ValueError("failure_target and failure_target_type must be provided together")
        return self

    def to_execute_request(self) -> AICapabilityExecuteRequest:
        """Convert to the generic execute request shape."""
        execute_request = AICapabilityExecuteRequest(
            workflow=AIWorkflow.FIND_SIMILAR_FAILURES,
            context=AICapabilityContext(
                repo=self.repo,
                pr_number=self.pr_number,
                workflow_name=self.workflow_name,
                check_name=self.check_name,
                failure_target=self.failure_target,
                failure_target_type=self.failure_target_type,
                session_id=self.session_id,
            ),
            inputs={
                "history_candidates": self.history_candidates,
                **({"history_cids": self.history_cids} if self.history_cids else {}),
            },
            **self._base_execute_kwargs(),
        )
        if self.top_k is not None:
            execute_request.options["top_k"] = self.top_k
        return execute_request


class AIStoredOutputReadExecuteRequest(AIWorkflowExecuteRequestBase):
    """Typed request for reading a stored AI output from IPFS."""

    cid: str = Field(..., min_length=1)

    def to_execute_request(self) -> AICapabilityExecuteRequest:
        """Convert to the generic execute request shape."""
        return AICapabilityExecuteRequest(
            workflow=AIWorkflow.READ_STORED_OUTPUT,
            inputs={"cid": self.cid},
            **self._base_execute_kwargs(),
        )


class AIAccelerateGenerateAndStoreExecuteRequest(AIWorkflowExecuteRequestBase):
    """Typed request for accelerated generation plus IPFS storage."""

    prompt: str = Field(..., min_length=1)
    kit_pin: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_execute_request(self) -> AICapabilityExecuteRequest:
        """Convert to the generic execute request shape."""
        return AICapabilityExecuteRequest(
            workflow=AIWorkflow.ACCELERATE_GENERATE_AND_STORE,
            inputs={
                "prompt": self.prompt,
                "kit_pin": self.kit_pin,
                **({"metadata": self.metadata} if self.metadata else {}),
            },
            **self._base_execute_kwargs(),
        )


class AIRAGSummaryOutput(BaseModel):
    """Typed output for composite PR summary capabilities."""

    schema_name: str = "rag_summary"
    schema_version: int = 1
    headline: str
    summary: str
    spoken_text: str
    repo: str | None = None
    pr_number: int | None = None
    source_summary: str | None = None
    embedding_dimensions: int | None = None
    ipfs_cid: str | None = None


class AICopilotOutput(BaseModel):
    """Typed output for Copilot CLI read-only capabilities."""

    schema_name: str = "copilot_output"
    schema_version: int = 1
    headline: str
    summary: str
    spoken_text: str


class AIFailureAnalysisOutput(BaseModel):
    """Typed output for composite failure analysis capabilities."""

    schema_name: str = "failure_analysis"
    schema_version: int = 1
    headline: str
    summary: str
    spoken_text: str
    repo: str | None = None
    pr_number: int | None = None
    failure_target: str | None = None
    failure_target_type: str | None = None
    checks_context: str | None = None
    embedding_dimensions: int | None = None
    ipfs_cid: str | None = None


class AISimilarFailuresOutput(BaseModel):
    """Typed output for similar-failure retrieval capabilities."""

    schema_name: str = "similar_failures"
    schema_version: int = 1
    repo: str | None = None
    pr_number: int | None = None
    failure_target: str | None = None
    failure_target_type: str | None = None
    checks_context: str
    embedding_dimensions: int
    ranked_matches: list[dict[str, Any]] = Field(default_factory=list)


class AIStoredOutputRead(BaseModel):
    """Typed output for CID-based stored AI output retrieval."""

    schema_name: str = "stored_output"
    schema_version: int = 1
    headline: str
    summary: str
    spoken_text: str
    cid: str
    stored_capability_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    payload: dict[str, Any] = Field(default_factory=dict)


class AIAcceleratedStoredOutput(BaseModel):
    """Typed output for accelerated generation plus storage."""

    schema_name: str = "accelerated_stored_output"
    schema_version: int = 1
    prompt: str
    generated: dict[str, Any] = Field(default_factory=dict)
    cid: str
    stored_bytes: int
    kit_pin: dict[str, Any] | None = None


class AIPolicyResolution(BaseModel):
    """Policy resolution metadata for API-facing AI execution."""

    requested_workflow: AIWorkflow | None = None
    resolved_workflow: AIWorkflow | None = None
    requested_capability_id: str | None = None
    resolved_capability_id: str
    policy_applied: bool = False


class AIBackendPolicyConfig(BaseModel):
    """Resolved AI backend policy configuration."""

    summary_backend: str
    failure_backend: str
    github_auth_source: str | None = None
    github_live_mode_requested: bool = False
    snapshot_retention_days: int | None = None
    snapshot_max_records_per_user: int | None = None
    snapshot_min_interval_seconds: int | None = None


class AIBackendPolicyWindow(BaseModel):
    """Recent action-log window summary for AI policy observability."""

    log_limit: int
    ai_execute_logs: int
    policy_applied_count: int


class AIBackendPolicyBucketReport(BaseModel):
    """Time-bucketed AI policy observability summary."""

    ai_execute_logs: int
    policy_applied_count: int
    remapped_capability_counts: dict[str, int] = Field(default_factory=dict)
    direct_capability_counts: dict[str, int] = Field(default_factory=dict)
    requested_workflow_counts: dict[str, int] = Field(default_factory=dict)
    resolved_workflow_counts: dict[str, int] = Field(default_factory=dict)
    remap_counts: dict[str, int] = Field(default_factory=dict)
    action_counts: dict[str, int] = Field(default_factory=dict)


class AICapabilityUsageCount(BaseModel):
    """Compact capability usage counter entry."""

    capability_id: str
    count: int


class AITopCapabilities(BaseModel):
    """Top capability usage summary for admin/debug reporting."""

    overall: list[AICapabilityUsageCount] = Field(default_factory=list)
    remapped: list[AICapabilityUsageCount] = Field(default_factory=list)
    direct: list[AICapabilityUsageCount] = Field(default_factory=list)


class AIRemapCount(BaseModel):
    """Compact workflow-remap counter entry."""

    remap_key: str
    count: int


class AILatestSnapshotInfo(BaseModel):
    """Latest persisted backend-policy snapshot metadata."""

    id: str
    created_at: datetime
    age_seconds: int = Field(ge=0)
    freshness_threshold_seconds: int = Field(ge=0)
    freshness: Literal["fresh", "stale"]


class AISnapshotHealth(BaseModel):
    """Compact snapshot health summary for admin observability responses."""

    status: Literal["healthy", "stale", "missing"]


class AISnapshotPolicyConfig(BaseModel):
    """Snapshot-specific policy settings surfaced in admin observability responses."""

    retention_days: int | None = None
    max_records_per_user: int | None = None
    min_interval_seconds: int | None = None


class AISnapshotSummary(BaseModel):
    """Reusable snapshot status block shared by admin observability responses."""

    latest_snapshot: AILatestSnapshotInfo | None = None
    snapshot_health: AISnapshotHealth
    policy: AISnapshotPolicyConfig
    snapshot_capture: "AISnapshotCaptureInfo | None" = None
    next_capture: "AISnapshotCaptureInfo | None" = None


class AIBackendPolicyReport(BaseModel):
    """Admin/debug report for AI backend policy and recent remaps."""

    report_generated_at: datetime
    policy: AIBackendPolicyConfig
    recent_window: AIBackendPolicyWindow
    time_buckets: dict[str, AIBackendPolicyBucketReport] = Field(default_factory=dict)
    top_capabilities: AITopCapabilities = Field(default_factory=AITopCapabilities)
    top_remaps: list[AIRemapCount] = Field(default_factory=list)
    remapped_capability_counts: dict[str, int] = Field(default_factory=dict)
    direct_capability_counts: dict[str, int] = Field(default_factory=dict)
    requested_workflow_counts: dict[str, int] = Field(default_factory=dict)
    resolved_workflow_counts: dict[str, int] = Field(default_factory=dict)
    remap_counts: dict[str, int] = Field(default_factory=dict)
    action_counts: dict[str, int] = Field(default_factory=dict)
    snapshot_summary: AISnapshotSummary
    latest_snapshot: AILatestSnapshotInfo | None = None
    snapshot_health: AISnapshotHealth
    snapshot_capture: "AISnapshotCaptureInfo | None" = None


class AIBackendPolicyHistoryBucket(BaseModel):
    """Time-series bucket for backend policy observability."""

    started_at: datetime
    ended_at: datetime
    ai_execute_logs: int
    policy_applied_count: int
    remap_counts: dict[str, int] = Field(default_factory=dict)


class AIBackendPolicyHistoryReport(BaseModel):
    """Historical backend-policy trend report."""

    report_generated_at: datetime
    policy: AIBackendPolicyConfig
    window_hours: int
    bucket_hours: int
    buckets: list[AIBackendPolicyHistoryBucket] = Field(default_factory=list)
    snapshot_summary: AISnapshotSummary
    latest_snapshot: AILatestSnapshotInfo | None = None
    snapshot_health: AISnapshotHealth


class AISnapshotCaptureInfo(BaseModel):
    """Snapshot capture metadata for admin backend-policy reads."""

    capture_requested: bool
    capture_mode: Literal["created", "reused", "skipped"]
    snapshot_id: str | None = None
    snapshot_created_at: datetime | None = None


class AIBackendPolicySnapshotResponse(BaseModel):
    """Persisted backend-policy snapshot response."""

    id: str
    created_at: datetime
    summary_backend: str
    failure_backend: str
    github_auth_source: str | None = None
    github_live_mode_requested: bool = False
    ai_execute_logs: int
    policy_applied_count: int
    remap_counts: dict[str, int] = Field(default_factory=dict)
    top_capabilities: dict[str, Any] = Field(default_factory=dict)
    top_remaps: list[dict[str, Any]] = Field(default_factory=list)


class AIBackendPolicySnapshotsResponse(BaseModel):
    """List response for persisted backend-policy snapshots."""

    report_generated_at: datetime
    snapshots: list[AIBackendPolicySnapshotResponse] = Field(default_factory=list)
    policy: AIBackendPolicyConfig | None = None
    snapshot_summary: AISnapshotSummary
    snapshot_health: AISnapshotHealth
    next_capture: AISnapshotCaptureInfo | None = None


class AICapabilityExecuteResponse(BaseModel):
    """API response for a shared AI capability execution."""

    ok: bool
    capability_id: str
    workflow: AIWorkflow | None = None
    execution_mode: str
    output_type: str | None = None
    policy_resolution: AIPolicyResolution | None = None
    typed_output: (
        AIRAGSummaryOutput
        | AICopilotOutput
        | AIFailureAnalysisOutput
        | AISimilarFailuresOutput
        | AIStoredOutputRead
        | AIAcceleratedStoredOutput
        | None
    ) = None
    output: dict[str, Any] = Field(default_factory=dict)
    trace: dict[str, Any] = Field(default_factory=dict)


class Error(BaseModel):
    """Error response."""

    error: str
    message: str
    details: dict[str, Any] | None = None


class CreateGitHubConnectionRequest(BaseModel):
    """Request to create a GitHub connection."""

    installation_id: int | None = None
    token: str | None = Field(
        default=None,
        description="GitHub access token (will be stored securely in secret manager)",
    )
    token_ref: str | None = Field(
        default=None,
        description=(
            "Reference to token in secret manager (NOT the actual token). "
            "Use this OR 'token', not both."
        ),
    )
    scopes: str | None = Field(
        default=None,
        description="Comma-separated OAuth scopes",
    )


class GitHubConnectionResponse(BaseModel):
    """GitHub connection response."""

    id: str
    user_id: str
    installation_id: int | None
    token_ref: str | None
    scopes: str | None
    created_at: datetime
    updated_at: datetime


class GitHubConnectionsListResponse(BaseModel):
    """List of GitHub connections."""

    connections: list[GitHubConnectionResponse]


class CreateRepoSubscriptionRequest(BaseModel):
    """Request to create a repository subscription."""

    repo_full_name: str = Field(
        ..., min_length=1, description="Full repository name (e.g., 'owner/repo')"
    )
    installation_id: int | None = Field(
        default=None,
        description="GitHub App installation ID (optional)",
    )


class RepoSubscriptionResponse(BaseModel):
    """Response for a repository subscription."""

    id: str
    user_id: str
    repo_full_name: str
    installation_id: int | None
    created_at: str


class RepoSubscriptionsListResponse(BaseModel):
    """Response for listing repository subscriptions."""

    subscriptions: list[RepoSubscriptionResponse]


class GitHubOAuthStartResponse(BaseModel):
    """Response for GitHub OAuth start endpoint."""

    authorize_url: str = Field(
        ...,
        description="GitHub OAuth authorization URL to redirect user to",
    )
    state: str | None = Field(
        default=None,
        description="Optional state parameter for CSRF protection",
    )


class GitHubOAuthCallbackResponse(BaseModel):
    """Response for successful GitHub OAuth callback."""

    connection_id: str = Field(
        ...,
        description="ID of the created/updated GitHub connection",
    )
    scopes: str | None = Field(
        default=None,
        description="OAuth scopes granted by the user",
    )


class TTSRequest(BaseModel):
    """Text-to-speech request."""

    text: str = Field(..., min_length=1, max_length=5000)
    voice: str | None = Field(
        default=None,
        description="Voice identifier (provider-specific)",
    )
    format: str = Field(
        default="wav",
        description="Audio format (wav, mp3)",
        pattern="^(wav|mp3)$",
    )


class DevAudioUploadRequest(BaseModel):
    """Dev-only audio upload payload."""

    data_base64: str | None = Field(
        default=None,
        description="Base64-encoded audio payload.",
    )
    audio_base64: str | None = Field(
        default=None,
        description="Backward-compatible alias for data_base64.",
    )
    format: str = Field(
        default="m4a",
        description="Audio file extension/format (e.g. wav, m4a, mp3, opus).",
    )

    def resolved_data_base64(self) -> str | None:
        """Return canonical base64 audio payload from either accepted field."""
        payload = self.data_base64 if isinstance(self.data_base64, str) else self.audio_base64
        if not isinstance(payload, str):
            return None
        payload = payload.strip()
        return payload or None

    def resolved_format(self) -> str:
        """Return normalized audio format with default fallback."""
        return str(self.format or "m4a").lower()


class DevMediaUploadRequest(BaseModel):
    """Dev-only generic media upload payload."""

    data_base64: str | None = Field(
        default=None,
        description="Base64-encoded media payload.",
    )
    media_kind: str | None = Field(
        default="image",
        description="Media kind hint (image or video).",
    )
    format: str | None = Field(
        default=None,
        description="Media file extension/format.",
    )
    mime_type: str | None = Field(
        default=None,
        description="Optional MIME type for downstream consumers.",
    )

    def resolved_data_base64(self) -> str | None:
        """Return stripped media base64 payload when present."""
        if not isinstance(self.data_base64, str):
            return None
        payload = self.data_base64.strip()
        return payload or None

    def resolved_media_kind(self) -> str:
        """Return normalized media kind defaulting to image."""
        return str(self.media_kind or "image").lower()

    def resolved_format(self, media_kind: str) -> str:
        """Return normalized format with media-kind-aware fallback."""
        default_format = "jpg" if media_kind == "image" else "mp4"
        return str(self.format or default_format).lower()


class AgentTaskMediaAttachRequest(BaseModel):
    """Request payload to attach media metadata to an agent task trace."""

    uri: str | None = Field(
        default=None,
        description="Stored media URI to attach to task trace.",
    )
    media_kind: str | None = Field(
        default="image",
        description="Media kind (image, video, or audio).",
    )
    format: str | None = Field(
        default=None,
        description="Media file extension/format.",
    )
    mime_type: str | None = Field(
        default=None,
        description="Optional MIME type associated with the media.",
    )
    source_asset_uri: str | None = Field(
        default=None,
        description="Original client-side asset URI (if available).",
    )
    action: str | None = Field(
        default=None,
        description="Capture action identifier (photo, video_start, etc).",
    )
    device_id: str | None = Field(
        default=None,
        description="Source wearable device identifier.",
    )
    device_name: str | None = Field(
        default=None,
        description="Human-readable source wearable name.",
    )
    captured_at: str | None = Field(
        default=None,
        description="ISO-8601 timestamp for when media was captured.",
    )

    def resolved_uri(self) -> str | None:
        """Return stripped media URI when present."""
        if not isinstance(self.uri, str):
            return None
        uri = self.uri.strip()
        return uri or None

    def resolved_media_kind(self) -> str:
        """Return normalized media kind defaulting to image."""
        return str(self.media_kind or "image").lower()


class DevPeerEnvelopeRequest(BaseModel):
    """Dev-only peer envelope ingress request."""

    peer_ref: str = Field(..., min_length=1)
    frame_base64: str = Field(..., min_length=1)


class DevPeerEnvelopeResponse(BaseModel):
    """Dev-only peer envelope ingress response."""

    accepted: bool
    peer_ref: str
    peer_id: str
    kind: str
    session_id: str
    message_id: str
    protocol: str | None = None
    conversation_id: str | None = None
    payload_text: str | None = None
    payload_json: dict[str, Any] | None = None
    ack_frame_base64: str | None = None


class DevPeerChatMessage(BaseModel):
    """Normalized dev peer chat message."""

    conversation_id: str
    peer_id: str
    sender_peer_id: str
    text: str
    priority: str = "normal"
    timestamp_ms: int
    task_snapshot: FollowOnTask | None = None


class DevPeerChatConversation(BaseModel):
    """Dev-only peer chat conversation summary."""

    conversation_id: str
    peer_id: str
    sender_peer_id: str
    last_text: str
    priority: str = "normal"
    last_timestamp_ms: int
    message_count: int
    task_snapshot: FollowOnTask | None = None


class DevPeerChatHistoryResponse(BaseModel):
    """Dev-only peer chat history response."""

    conversation_id: str
    messages: list[DevPeerChatMessage] = Field(default_factory=list)


class DevPeerChatConversationsResponse(BaseModel):
    """Dev-only recent peer chat conversations response."""

    conversations: list[DevPeerChatConversation] = Field(default_factory=list)


class DevPeerChatSendRequest(BaseModel):
    """Dev-only outbound peer chat send request."""

    peer_id: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)
    conversation_id: str | None = None
    priority: str = Field(default="normal", pattern="^(normal|urgent)$")
    task_id: str | None = None


class DevPeerChatSendResponse(BaseModel):
    """Dev-only outbound peer chat send response."""

    accepted: bool
    peer_id: str
    sender_peer_id: str
    protocol: str
    conversation_id: str
    text: str
    priority: str
    transport_provider: str
    timestamp_ms: int
    task_snapshot: FollowOnTask | None = None


class DevPeerChatOutboxMessage(BaseModel):
    """Dev-only outbound peer chat message queued for handset fetch."""

    outbox_message_id: str
    conversation_id: str
    peer_id: str
    sender_peer_id: str
    text: str
    priority: str = "normal"
    timestamp_ms: int
    leased_until_ms: int | None = None
    task_snapshot: FollowOnTask | None = None


class DevPeerChatOutboxPreviewMessage(BaseModel):
    """Dev-only queued outbox message preview with current delivery state."""

    outbox_message_id: str
    conversation_id: str
    peer_id: str
    sender_peer_id: str
    text: str
    priority: str = "normal"
    timestamp_ms: int
    leased_until_ms: int | None = None
    state: str
    hold_reason: str | None = None
    task_snapshot: FollowOnTask | None = None


class DevPeerChatOutboxResponse(BaseModel):
    """Dev-only outbound peer chat outbox response."""

    peer_id: str
    delivery_mode: str
    recommended_lease_ms: int
    recommended_poll_ms: int
    queued_total: int = 0
    queued_urgent: int = 0
    queued_normal: int = 0
    deliverable_now: int = 0
    held_now: int = 0
    messages: list[DevPeerChatOutboxMessage] = Field(default_factory=list)
    preview_messages: list[DevPeerChatOutboxPreviewMessage] = Field(default_factory=list)


class DevPeerChatOutboxAckRequest(BaseModel):
    """Acknowledge delivered outbox messages for a handset peer id."""

    outbox_message_ids: list[str] = Field(default_factory=list)


class DevPeerChatOutboxAckResponse(BaseModel):
    """Result of acknowledging queued outbox messages."""

    peer_id: str
    acknowledged_message_ids: list[str] = Field(default_factory=list)


class DevPeerChatOutboxReleaseRequest(BaseModel):
    """Release leased outbox messages back into a deliverable state."""

    outbox_message_ids: list[str] = Field(default_factory=list)


class DevPeerChatOutboxReleaseResponse(BaseModel):
    """Result of releasing leased outbox messages."""

    peer_id: str
    released_message_ids: list[str] = Field(default_factory=list)


class DevPeerChatOutboxPromoteRequest(BaseModel):
    """Promote queued outbox messages to urgent priority."""

    outbox_message_ids: list[str] = Field(default_factory=list)


class DevPeerChatOutboxPromoteResponse(BaseModel):
    """Result of promoting queued outbox messages to urgent priority."""

    peer_id: str
    promoted_message_ids: list[str] = Field(default_factory=list)


class DevPeerChatHandsetHeartbeatRequest(BaseModel):
    """Heartbeat request from a handset participating in dev peer chat relay."""

    display_name: str | None = None


class DevPeerChatHandsetSessionResponse(BaseModel):
    """Observed handset relay session state."""

    peer_id: str
    display_name: str | None = None
    status: str
    delivery_mode: str
    recommended_lease_ms: int
    recommended_poll_ms: int
    last_seen_ms: int
    last_seen_age_ms: int
    last_fetch_ms: int | None = None
    last_ack_ms: int | None = None


class DevTransportSessionCursor(BaseModel):
    """Dev-only persisted transport session cursor."""

    peer_id: str
    peer_ref: str
    session_id: str
    resume_token: str
    capabilities: list[str] = Field(default_factory=list)
    updated_at_ms: int | None = None


class DevTransportSessionsResponse(BaseModel):
    """Dev-only transport session cursor list response."""

    sessions: list[DevTransportSessionCursor] = Field(default_factory=list)


class DevTransportSessionClearResponse(BaseModel):
    """Dev-only response for clearing a transport session cursor."""

    peer_id: str
    cleared: bool


class CreateNotificationSubscriptionRequest(BaseModel):
    """Request to create a notification subscription."""

    endpoint: str = Field(
        ..., min_length=1, description="Subscription endpoint URL or device token"
    )
    platform: str = Field(
        default="webpush",
        description="Platform type: 'webpush', 'apns', 'fcm', or 'expo'",
        pattern="^(webpush|apns|fcm|expo)$",
    )
    subscription_keys: dict[str, str] | None = Field(
        default=None,
        description="Provider-specific subscription keys (e.g., auth, p256dh for WebPush)",
    )


class NotificationSubscriptionResponse(BaseModel):
    """Response for a notification subscription."""

    id: str
    user_id: str
    endpoint: str
    platform: str
    subscription_keys: dict[str, str]
    created_at: str
    updated_at: str


class NotificationSubscriptionsListResponse(BaseModel):
    """Response for listing notification subscriptions."""

    subscriptions: list[NotificationSubscriptionResponse]


class Notification(BaseModel):
    """User notification payload exposed via the API."""

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "notif-9b2b1d9d",
                "user_id": "00000000-0000-0000-0000-000000000001",
                "event_type": "task_completed",
                "message": "IPFS Datasets completed. Result: Expanded legal query",
                "metadata": {
                    "task_id": "task-9b2b1d9d",
                    "provider": "ipfs_datasets_mcp",
                    "provider_label": "IPFS Datasets",
                    "mcp_capability": "dataset_discovery",
                },
                "created_at": "2026-03-09T12:01:15Z",
                "priority": 3,
                "profile": "default",
                "delivery_status": "success",
                "card": {
                    "title": "Wearables Connectivity Receipt",
                    "subtitle": "Ray-Ban Meta",
                    "lines": [
                        "device: Ray-Ban Meta",
                        "state: connected",
                    ],
                    "deep_link": "ipfs://bafyreceipt",
                    "action_items": [
                        {
                            "id": "mobile_open_wearables_diagnostics",
                            "label": "Open Diagnostics",
                            "phrase": "open wearables bridge diagnostics",
                        },
                        {
                            "id": "mobile_reconnect_wearables_target",
                            "label": "Reconnect Target",
                            "phrase": "reconnect the selected wearables target",
                        },
                        {
                            "id": "read_cid",
                            "label": "Read Receipt",
                            "phrase": "read the wearables receipt",
                        }
                    ],
                },
            }
        }
    }

    id: str
    user_id: str
    event_type: str
    message: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    priority: int = Field(..., ge=1, le=5)
    profile: str
    last_delivery_attempt: str | None = None
    delivery_status: str | None = None
    card: UICard | None = None


class NotificationsListResponse(BaseModel):
    """Response for listing notifications."""

    model_config = {
        "json_schema_extra": {
            "example": {
                "notifications": [
                    {
                        "id": "notif-9b2b1d9d",
                        "user_id": "00000000-0000-0000-0000-000000000001",
                        "event_type": "task_completed",
                        "message": "IPFS Datasets completed. Result: Expanded legal query",
                        "metadata": {
                            "task_id": "task-9b2b1d9d",
                            "provider": "ipfs_accelerate_mcp",
                            "provider_label": "IPFS Accelerate",
                            "mcp_capability": "workflow",
                        },
                        "created_at": "2026-03-09T12:01:15Z",
                        "priority": 3,
                        "profile": "default",
                        "delivery_status": "success",
                        "card": {
                            "title": "Wearables Connectivity Receipt",
                            "subtitle": "Ray-Ban Meta",
                            "lines": [
                                "device: Ray-Ban Meta",
                                "state: connected",
                            ],
                            "deep_link": "ipfs://bafyreceipt",
                            "action_items": [
                                {
                                    "id": "mobile_open_wearables_diagnostics",
                                    "label": "Open Diagnostics",
                                    "phrase": "open wearables bridge diagnostics",
                                },
                                {
                                    "id": "mobile_reconnect_wearables_target",
                                    "label": "Reconnect Target",
                                    "phrase": "reconnect the selected wearables target",
                                },
                                {
                                    "id": "read_cid",
                                    "label": "Read Receipt",
                                    "phrase": "read the wearables receipt",
                                }
                            ],
                        },
                    }
                ],
                "count": 1,
            }
        }
    }

    notifications: list[Notification] = Field(default_factory=list)
    count: int = Field(..., ge=0)


class DependencyStatus(BaseModel):
    """Status of a service dependency."""

    name: str
    status: str = Field(..., description="Status: ok, degraded, or unavailable")
    message: str | None = None


class StatusResponse(BaseModel):
    """Service status response."""

    status: str = Field(..., description="Overall service status: ok, degraded, or unavailable")
    version: str | None = Field(default=None, description="Service version if available")
    timestamp: datetime = Field(..., description="Current server time")
    dependencies: list[DependencyStatus] = Field(
        default_factory=list,
        description="Status of dependencies like DuckDB, Redis (optional)",
    )


class CreateApiKeyRequest(BaseModel):
    """Request to create a new API key."""

    label: str | None = Field(
        default=None,
        max_length=100,
        description="Optional user-friendly label for the key (e.g., 'Mobile app', 'CI/CD')",
    )


class ApiKeyResponse(BaseModel):
    """Response for an API key (without the plaintext key)."""

    id: str
    user_id: str
    label: str | None
    created_at: str
    revoked_at: str | None
    last_used_at: str | None


class CreateApiKeyResponse(BaseModel):
    """Response when creating a new API key.

    This is the ONLY time the plaintext key is returned.
    """

    key: str = Field(
        ..., description="The plaintext API key. Save this - it will not be shown again."
    )
    api_key: ApiKeyResponse


class ApiKeysListResponse(BaseModel):
    """Response for listing API keys."""

    api_keys: list[ApiKeyResponse]
