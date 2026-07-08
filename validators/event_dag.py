"""Event DAG validator for MCP++ provenance events."""

from __future__ import annotations

from typing import Any, Dict, List

from .base_mcp import ValidationResult


class EventDAGValidator:
    """Validate single Event DAG records and ordered DAG lists."""

    REQUIRED_EVENT_FIELDS = ("event_cid", "timestamp", "parents")

    def validate_event(self, event: Dict[str, Any]) -> ValidationResult:
        result = ValidationResult(is_valid=True, message_type="event")
        if not isinstance(event, dict):
            result.add_error("Event must be an object")
            return result

        for field in self.REQUIRED_EVENT_FIELDS:
            if field not in event:
                result.add_error(f"Event missing required field: {field}")

        if "parents" in event and not isinstance(event["parents"], list):
            result.add_error("'parents' must be a list")

        return result

    def validate_dag(self, dag: List[Dict[str, Any]]) -> ValidationResult:
        result = ValidationResult(is_valid=True, message_type="event_dag")
        if not isinstance(dag, list):
            result.add_error("DAG must be a list of events")
            return result

        seen = set()
        for index, event in enumerate(dag):
            event_result = self.validate_event(event)
            if not event_result.is_valid:
                result.errors.extend(event_result.errors)
                result.is_valid = False
            event_cid = event.get("event_cid") if isinstance(event, dict) else None
            if event_cid in seen:
                result.add_error(f"Duplicate event_cid: {event_cid}")
            if event_cid:
                seen.add(event_cid)
            for parent in event.get("parents", []) if isinstance(event, dict) else []:
                if parent not in seen and index > 0:
                    result.add_warning(f"Event {event_cid or index} references unseen parent: {parent}")

        return result
