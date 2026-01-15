"""Intent parser for converting text to structured intents."""

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class ParsedIntent:
    """Structured representation of a parsed command intent."""

    name: str
    confidence: float
    entities: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "name": self.name,
            "confidence": self.confidence,
            "entities": self.entities,
        }


def _parse_reviewers(text: str) -> list[str]:
    """Parse reviewer names from text, handling comma and space separation.

    Args:
        text: Text containing reviewer names, e.g., "alice, bob" or "alice bob"

    Returns:
        List of reviewer names
    """
    # If text contains commas or "and", use those as separators
    if "," in text or " and " in text.lower():
        return [r.strip() for r in text.replace(" and ", ",").split(",") if r.strip()]
    # Otherwise, split by spaces
    return [r.strip() for r in text.split() if r.strip()]


class IntentParser:
    """Parse text transcripts into structured intents using pattern matching."""

    def __init__(self) -> None:
        """Initialize the intent parser with pattern rules."""
        # Pattern rules: (regex, intent_name, entity_extractors)
        self.patterns: list[tuple[re.Pattern[str], str, dict[str, Any]]] = [
            # System commands (more flexible patterns)
            (
                re.compile(r"\b(repeat|say that again)\b", re.IGNORECASE),
                "system.repeat",
                {},
            ),
            (
                re.compile(r"\b(next|next one)\b", re.IGNORECASE),
                "system.next",
                {},
            ),
            (re.compile(r"\bcancel\b", re.IGNORECASE), "system.cancel", {}),
            (
                re.compile(r"\b(confirm|confirmed)\b", re.IGNORECASE),
                "system.confirm",
                {},
            ),
            (
                re.compile(r"\b(workout|kitchen|commute)\s+mode\b", re.IGNORECASE),
                "system.set_profile",
                {"profile": lambda m: m.group(1).lower()},
            ),
            # Inbox commands
            (
                re.compile(
                    r"\b(what needs my attention|inbox|pr inbox|anything failing)\b",
                    re.IGNORECASE,
                ),
                "inbox.list",
                {},
            ),
            # PR summarize
            (
                re.compile(r"\bsummarize\s+(pr|pull\s+request)\s+(\d+)\b", re.IGNORECASE),
                "pr.summarize",
                {"pr_number": lambda m: int(m.group(2))},
            ),
            (
                re.compile(r"\bsummarize\s+the\s+last\s+pr\b", re.IGNORECASE),
                "pr.summarize",
                {"pr_number": "last"},
            ),
            (
                re.compile(r"\bwhat\s+changed\s+in\s+pr\s+(\d+)\b", re.IGNORECASE),
                "pr.summarize",
                {"pr_number": lambda m: int(m.group(1))},
            ),
            (
                re.compile(r"\btell me about\s+pr\s+(\d+)\b", re.IGNORECASE),
                "pr.summarize",
                {"pr_number": lambda m: int(m.group(1))},
            ),
            # PR request review (side effect)
            (
                re.compile(
                    r"\brequest\s+review\s+from\s+([\w\s,]+?)\s+on\s+pr\s+(\d+)$",
                    re.IGNORECASE,
                ),
                "pr.request_review",
                {
                    "reviewers": lambda m: [
                        r.strip() for r in m.group(1).replace(" and ", ",").split(",") if r.strip()
                    ],
                    "pr_number": lambda m: int(m.group(2)),
                },
            ),
            (
                re.compile(
                    r"\brequest\s+review\s+from\s+([\w\s,]+)$",
                    re.IGNORECASE,
                ),
                "pr.request_review",
                {
                    "reviewers": lambda m: [
                        r.strip() for r in m.group(1).replace(" and ", ",").split(",") if r.strip()
                    ],
                },
            ),
            (
                re.compile(
                    r"\badd\s+reviewers?\s+([\w\s,]+?)\s+(?:to|on)\s+pr\s+(\d+)$",
                    re.IGNORECASE,
                ),
                "pr.request_review",
                {
                    "reviewers": lambda m: [
                        r.strip() for r in m.group(1).replace(" and ", ",").split(",") if r.strip()
                    ],
                    "pr_number": lambda m: int(m.group(2)),
                },
            ),
            (
                re.compile(
                    r"\badd\s+reviewers?\s+([\w\s,]+)$",
                    re.IGNORECASE,
                ),
                "pr.request_review",
                {
                    "reviewers": lambda m: [
                        r.strip() for r in m.group(1).replace(" and ", ",").split(",") if r.strip()
                    ],
                },
            ),
            (
                re.compile(
                    r"\brequest\s+reviewers?\s+([\w\s,]+?)\s+(?:for|on)\s+pr\s+(\d+)$",
                    re.IGNORECASE,
                ),
                "pr.request_review",
                {
                    "reviewers": lambda m: _parse_reviewers(m.group(1)),
                    "pr_number": lambda m: int(m.group(2)),
                },
            ),
            # Agent delegation (placed before less specific PR patterns to take precedence)
            (
                re.compile(
                    r"\b(?:ask|have|tell)\s+(?:the\s+)?agent\s+(?:to\s+)?(.*?)\s+(?:on\s+)?(?:pr|pull\s+request)\s+(\d+)$",
                    re.IGNORECASE,
                ),
                "agent.delegate",
                {
                    "instruction": lambda m: m.group(1).strip(),
                    "pr_number": lambda m: int(m.group(2)),
                },
            ),
            (
                re.compile(
                    r"\b(?:ask|have|tell)\s+(?:the\s+)?agent\s+(?:to\s+)?(.*?)\s+(?:issue|on\s+issue)\s+(\d+)$",
                    re.IGNORECASE,
                ),
                "agent.delegate",
                {
                    "instruction": lambda m: m.group(1).strip(),
                    "issue_number": lambda m: int(m.group(2)),
                },
            ),
            (
                re.compile(
                    r"\btell\s+copilot\s+to\s+handle\s+issue\s+(\d+)\b",
                    re.IGNORECASE,
                ),
                "agent.delegate",
                {
                    "instruction": "handle",
                    "issue_number": lambda m: int(m.group(1)),
                    "provider": "copilot",
                },
            ),
            # General agent delegation without specific target
            (
                re.compile(
                    r"\b(?:ask|have|tell)\s+(?:the\s+)?agent\s+(?:to\s+)?(.+)$",
                    re.IGNORECASE,
                ),
                "agent.delegate",
                {
                    "instruction": lambda m: m.group(1).strip(),
                },
            ),
            # PR request review - less specific patterns after agent delegation
            (
                re.compile(r"\bask\s+([\w]+)\s+to\s+review\s+pr\s+(\d+)\b", re.IGNORECASE),
                "pr.request_review",
                {
                    "reviewers": lambda m: [m.group(1)],
                    "pr_number": lambda m: int(m.group(2)),
                },
            ),
            (
                re.compile(r"\bask\s+([\w]+)\s+to\s+review\b", re.IGNORECASE),
                "pr.request_review",
                {"reviewers": lambda m: [m.group(1)]},
            ),
            # PR merge (side effect)
            (
                re.compile(r"\b(squash\s+)?merge\s+(pr\s+)?(\d+)\b", re.IGNORECASE),
                "pr.merge",
                {
                    "pr_number": lambda m: int(m.group(3)),
                    "merge_method": lambda m: "squash" if m.group(1) else "merge",
                },
            ),
            (
                re.compile(r"\bmerge\s+when\s+green\b", re.IGNORECASE),
                "pr.merge",
                {"merge_method": "squash", "auto": True},
            ),
            # Checks rerun (side effect)
            (
                re.compile(r"\brerun\s+checks\s+(?:for|on)\s+pr\s+(\d+)\b", re.IGNORECASE),
                "checks.rerun",
                {"pr_number": lambda m: int(m.group(1))},
            ),
            (
                re.compile(r"\brerun\s+ci\s+(?:for|on)\s+pr\s+(\d+)\b", re.IGNORECASE),
                "checks.rerun",
                {"pr_number": lambda m: int(m.group(1))},
            ),
            (
                re.compile(r"\brerun\s+(?:checks|ci)\b", re.IGNORECASE),
                "checks.rerun",
                {},
            ),
            # Checks status
            (
                re.compile(r"\bchecks\s+for\s+pr\s+(\d+)\b", re.IGNORECASE),
                "checks.status",
                {"pr_number": lambda m: int(m.group(1))},
            ),
            (
                re.compile(r"\bci\s+status\b", re.IGNORECASE),
                "checks.status",
                {},
            ),
            (
                re.compile(r"\bwhat'?s\s+failing\s+on\s+([\w\-/]+)\b", re.IGNORECASE),
                "checks.status",
                {"repo": lambda m: m.group(1)},
            ),
            # Agent progress
            (
                re.compile(r"\bagent\s+status\b", re.IGNORECASE),
                "agent.status",
                {},
            ),
            (
                re.compile(r"\bwhat'?s\s+the\s+agent\s+doing\b", re.IGNORECASE),
                "agent.status",
                {},
            ),
            (
                re.compile(r"\bsummarize\s+agent\s+progress\b", re.IGNORECASE),
                "agent.status",
                {},
            ),
            (
                re.compile(r"\bagent\s+progress\b", re.IGNORECASE),
                "agent.status",
                {},
            ),
            # Agent pause
            (
                re.compile(r"\bpause\s+task\s+([a-f0-9-]+)\b", re.IGNORECASE),
                "agent.pause",
                {"task_id": lambda m: m.group(1)},
            ),
            (
                re.compile(r"\bpause\s+agent\b", re.IGNORECASE),
                "agent.pause",
                {},
            ),
            # Agent resume
            (
                re.compile(r"\bresume\s+task\s+([a-f0-9-]+)\b", re.IGNORECASE),
                "agent.resume",
                {"task_id": lambda m: m.group(1)},
            ),
            (
                re.compile(r"\bresume\s+agent\b", re.IGNORECASE),
                "agent.resume",
                {},
            ),
        ]

    def parse(self, text: str) -> ParsedIntent:
        """Parse text input into a structured intent.

        Args:
            text: User input text (transcript or typed command)

        Returns:
            ParsedIntent with name, confidence, and extracted entities
        """
        text = text.strip()

        # Try to match against known patterns
        for pattern, intent_name, entity_extractors in self.patterns:
            match = pattern.search(text)
            if match:
                # Extract entities using the configured extractors
                entities: dict[str, Any] = {}
                for entity_key, extractor in entity_extractors.items():
                    if callable(extractor):
                        value = extractor(match)
                        if value is not None:
                            entities[entity_key] = value
                    else:
                        entities[entity_key] = extractor

                # Calculate confidence based on pattern match quality
                # For now, use 1.0 for exact matches, 0.9 for partial
                confidence = 1.0 if pattern.match(text) else 0.9

                return ParsedIntent(name=intent_name, confidence=confidence, entities=entities)

        # No match found - return unknown intent with low confidence
        return ParsedIntent(name="unknown", confidence=0.0, entities={"text": text})
