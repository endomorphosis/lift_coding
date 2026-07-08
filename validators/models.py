"""Pydantic models for MCP++ cross-server conformance tests."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


CID_PATTERN = r"^(Qm[1-9A-HJ-NP-Za-km-z]{44}|b[a-z2-7]{58})$"


class MethodDescriptor(BaseModel):
    """MCP-IDL method descriptor."""

    model_config = ConfigDict(extra="allow", strict=True)

    name: str = Field(..., min_length=1)
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Dict[str, Any] = Field(default_factory=dict)
    description: Optional[str] = None
    errors: List[str] = Field(default_factory=list)
    streaming: bool = False


class InterfaceDescriptor(BaseModel):
    """MCP++ Profile A interface descriptor."""

    model_config = ConfigDict(extra="allow", strict=True)

    name: str = Field(..., min_length=1)
    namespace: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)
    methods: List[MethodDescriptor] = Field(..., min_length=1)
    errors: List[str] = Field(default_factory=list)
    requires: List[str] = Field(default_factory=list)
    compatibility: Dict[str, Any] = Field(default_factory=dict)
    semantic_tags: Optional[List[str]] = None
    observability: Optional[Dict[str, Any]] = None
    interaction_patterns: Optional[Union[List[str], Dict[str, Any]]] = None
    resource_cost_hints: Optional[Dict[str, Any]] = None
    interface_cid: Optional[str] = Field(None, pattern=CID_PATTERN)
    cid: Optional[str] = Field(None, pattern=CID_PATTERN)


class EventType(str, Enum):
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
    event_type: Union[EventType, str] = Field(...)
    parents: List[str] = Field(default_factory=list)
    timestamp: Union[str, float, int] = Field(...)
    payload: Dict[str, Any] = Field(default_factory=dict)
