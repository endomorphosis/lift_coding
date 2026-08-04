"""Pydantic models for MCP++ cross-server conformance tests."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

CID_PATTERN = r"^(Qm[1-9A-HJ-NP-Za-km-z]{44}|b[a-z2-7]{58})$"


class MethodDescriptor(BaseModel):
    """MCP-IDL method descriptor."""

    model_config = ConfigDict(extra="allow", strict=True)

    name: str = Field(..., min_length=1)
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    description: str | None = None
    errors: list[str] = Field(default_factory=list)
    streaming: bool = False


class InterfaceDescriptor(BaseModel):
    """MCP++ Profile A interface descriptor."""

    model_config = ConfigDict(extra="allow", strict=True)

    name: str = Field(..., min_length=1)
    namespace: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)
    methods: list[MethodDescriptor] = Field(..., min_length=1)
    errors: list[str] = Field(default_factory=list)
    requires: list[str] = Field(default_factory=list)
    compatibility: dict[str, Any] = Field(default_factory=dict)
    semantic_tags: list[str] | None = None
    observability: dict[str, Any] | None = None
    interaction_patterns: list[str] | dict[str, Any] | None = None
    resource_cost_hints: dict[str, Any] | None = None
    interface_cid: str | None = Field(None, pattern=CID_PATTERN)
    cid: str | None = Field(None, pattern=CID_PATTERN)


class EventType(StrEnum):
    INVOCATION = "invocation"
    RESULT = "result"
    ERROR = "error"
    DELEGATION = "delegation"
    POLICY_DECISION = "policy_decision"
    INTENT = "intent"
    DECISION = "decision"
    RECEIPT = "receipt"
    ENVELOPE = "envelope"


class DAGEvent(BaseModel):
    """MCP++ Event DAG wire event."""

    model_config = ConfigDict(extra="allow", strict=True)

    event_cid: str = Field(..., pattern=CID_PATTERN)
    event_type: EventType | str = Field(...)
    parents: list[str] = Field(default_factory=list)
    timestamp: str | float | int = Field(...)
    payload: dict[str, Any] = Field(default_factory=dict)
