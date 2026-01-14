"""Pydantic models aligned with spec/openapi.yaml."""

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class Profile(str, Enum):
    """Profile enum."""

    WORKOUT = "workout"
    KITCHEN = "kitchen"
    COMMUTE = "commute"
    DEFAULT = "default"


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


class ClientContext(BaseModel):
    """Client context."""

    device: str
    locale: str = Field(..., examples=["en-US"])
    timezone: str = Field(..., examples=["America/Los_Angeles"])
    app_version: str = Field(..., examples=["0.1.0"])
    noise_mode: bool = False


class CommandRequest(BaseModel):
    """Command request."""

    input: TextInput | AudioInput
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


class UICard(BaseModel):
    """UI card."""

    title: str
    subtitle: str | None = None
    lines: list[str] = Field(default_factory=list)
    deep_link: str | None = None


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


class CommandResponse(BaseModel):
    """Command response."""

    status: CommandStatus
    intent: ParsedIntent
    spoken_text: str
    cards: list[UICard] = Field(default_factory=list)
    pending_action: PendingAction | None = None
    debug: DebugInfo | None = None


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


class ActionResult(BaseModel):
    """Action result."""

    ok: bool
    message: str
    url: str | None = None


class Error(BaseModel):
    """Error response."""

    error: str
    message: str
    details: dict[str, Any] | None = None


class CreateGitHubConnectionRequest(BaseModel):
    """Request to create a GitHub connection."""

    installation_id: int | None = None
    token_ref: str | None = Field(
        default=None,
        description="Reference to token in secret manager (NOT the actual token)",
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


class CreateNotificationSubscriptionRequest(BaseModel):
    """Request to create a notification subscription."""

    endpoint: str = Field(..., min_length=1, description="Subscription endpoint URL")
    subscription_keys: dict[str, str] | None = Field(
        default=None,
        description="Provider-specific subscription keys (e.g., auth, p256dh for WebPush)",
    )


class NotificationSubscriptionResponse(BaseModel):
    """Response for a notification subscription."""

    id: str
    user_id: str
    endpoint: str
    subscription_keys: dict[str, str]
    created_at: str
    updated_at: str


class NotificationSubscriptionsListResponse(BaseModel):
    """Response for listing notification subscriptions."""

    subscriptions: list[NotificationSubscriptionResponse]


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
