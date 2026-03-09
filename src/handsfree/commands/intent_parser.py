"""Intent parser for converting text to structured intents."""

import re
from dataclasses import dataclass
from typing import Any

from handsfree.mcp import resolve_provider_alias


PROVIDER_ALIASES = {
    "copilot": "copilot",
}


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


def _parse_agent_provider(text: str) -> str:
    """Resolve agent provider aliases, including MCP-backed IPFS providers."""
    normalized = text.strip().lower()
    return PROVIDER_ALIASES.get(normalized) or resolve_provider_alias(normalized) or normalized


def _parse_cids(text: str) -> list[str]:
    """Parse one or more CIDs from a phrase like 'bafy1, bafy2 and bafy3'."""
    normalized = re.sub(r"\s+(?:and|&)\s+", ",", text.strip(), flags=re.IGNORECASE)
    return [cid.strip() for cid in normalized.split(",") if cid.strip()]


def _infer_agent_execution_mode(text: str) -> str | None:
    """Infer a preferred execution mode from natural language phrasing."""
    normalized = text.strip().lower()

    direct_import_patterns = (
        r"\blocally\b",
        r"\blocal\s+only\b",
        r"\bon[ -]?device\b",
        r"\bdirect[ -]?import\b",
    )
    mcp_remote_patterns = (
        r"\bremotely\b",
        r"\bremote\s+only\b",
        r"\bvia\s+mcp\b",
        r"\bthrough\s+mcp\b",
        r"\busing\s+mcp\b",
        r"\bin\s+the\s+background\b",
        r"\bas\s+a\s+background\s+task\b",
    )

    if any(re.search(pattern, normalized, re.IGNORECASE) for pattern in direct_import_patterns):
        return "direct_import"
    if any(re.search(pattern, normalized, re.IGNORECASE) for pattern in mcp_remote_patterns):
        return "mcp_remote"
    return None


class IntentParser:
    """Parse text transcripts into structured intents using pattern matching."""

    def __init__(self) -> None:
        """Initialize the intent parser with pattern rules."""
        # Pattern rules: (regex, intent_name, entity_extractors)
        self.patterns: list[tuple[re.Pattern[str], str, dict[str, Any]]] = [
            # Debug/observability commands
            (
                re.compile(r"\b(explain what you heard|what did you hear)\b", re.IGNORECASE),
                "debug.transcript",
                {},
            ),
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
            (
                re.compile(r"\b(next result|next results)\b", re.IGNORECASE),
                "system.next",
                {},
            ),
            (
                re.compile(
                    r"\b(show|read|give me)\s+more\s+(?:results|dataset discoveries|ipfs results|fetches)\b",
                    re.IGNORECASE,
                ),
                "system.next",
                {},
            ),
            (
                re.compile(r"\bopen\s+(?:that|the|current)\s+result\b", re.IGNORECASE),
                "agent.result_open",
                {},
            ),
            (
                re.compile(
                    r"\b(?:what\s+can\s+i\s+do\s+with|show)\s+(?:that|the|current)\s+result\b",
                    re.IGNORECASE,
                ),
                "agent.result_actions",
                {},
            ),
            (
                re.compile(
                    r"\b(?:show|open|read)\s+(?:task\s+)?details?\s+for\s+(?:that|the|current)\s+result\b",
                    re.IGNORECASE,
                ),
                "agent.result_details",
                {},
            ),
            (
                re.compile(
                    r"\bshow\s+another\s+result\s+like\s+(?:this|that)\b",
                    re.IGNORECASE,
                ),
                "agent.result_related",
                {},
            ),
            (
                re.compile(
                    r"\brerun\s+(?:that|the|current)\s+fetch\s+with\s+(https?://\S+)\b",
                    re.IGNORECASE,
                ),
                "agent.result_rerun_fetch",
                {
                    "mcp_seed_url": lambda m: m.group(1).strip(),
                },
            ),
            (
                re.compile(
                    r"\brerun\s+(?:that|the|current)\s+dataset\s+(?:search|discovery)\s+with\s+(.+)$",
                    re.IGNORECASE,
                ),
                "agent.result_rerun_dataset",
                {
                    "mcp_input": lambda m: m.group(1).strip(),
                },
            ),
            (
                re.compile(
                    r"\b(?:save|store|persist)\s+(?:that|the|current)\s+result\s+to\s+ipfs\b",
                    re.IGNORECASE,
                ),
                "agent.result_save_ipfs",
                {},
            ),
            (
                re.compile(r"\bread\s+(?:the|that|current)\s+cid\b", re.IGNORECASE),
                "agent.result_read",
                {},
            ),
            (
                re.compile(
                    r"\bshare\s+(?:the|that|current)\s+cid\b",
                    re.IGNORECASE,
                ),
                "agent.result_share",
                {},
            ),
            (
                re.compile(
                    r"\bunpin\s+(?:that|the|current)(?:\s+cid|\s+result)?\b",
                    re.IGNORECASE,
                ),
                "agent.result_unpin",
                {},
            ),
            (
                re.compile(r"\bpin\s+(?:that|the|current)(?:\s+cid|\s+result)?\b", re.IGNORECASE),
                "agent.result_pin",
                {},
            ),
            (
                re.compile(
                    r"\brerun\s+(?:that|the|current)\s+workflow\b",
                    re.IGNORECASE,
                ),
                "agent.result_rerun",
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
                re.compile(
                    r"\b(?:read|load|open|show)\s+(?:summary|analysis|result)?\s*(?:from\s+)?cid\s+([A-Za-z0-9]+)\b",
                    re.IGNORECASE,
                ),
                "ai.read_cid",
                {"cid": lambda m: m.group(1)},
            ),
            (
                re.compile(
                    r"\b(?:read|load|open|show)\s+(?:summary|analysis|result)?\s*(?:from\s+)?ipfs\s+([A-Za-z0-9]+)\b",
                    re.IGNORECASE,
                ),
                "ai.read_cid",
                {"cid": lambda m: m.group(1)},
            ),
            (
                re.compile(
                    r"\b(?:accelerate\s+and\s+store|generate\s+and\s+store\s+with\s+acceleration)\s+(.+?)\s+(?:to|in)\s+ipfs\b",
                    re.IGNORECASE,
                ),
                "ai.accelerate_generate_and_store",
                {
                    "prompt": lambda m: m.group(1).strip(),
                    "kit_pin": True,
                },
            ),
            (
                re.compile(
                    r"\b(?:accelerate\s+and\s+store|generate\s+and\s+store\s+with\s+acceleration)\s+(.+)$",
                    re.IGNORECASE,
                ),
                "ai.accelerate_generate_and_store",
                {
                    "prompt": lambda m: m.group(1).strip(),
                },
            ),
            (
                re.compile(
                    r"\b(?:use\s+acceleration\s+for|use\s+accelerated\s+summary\s+for)\s+(?:rag\s+summary|augmented\s+summary)\s+(?:for\s+)?(?:pr|pull\s+request)\s+(\d+)\s+(?:on|in)\s+([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)\s+(?:to|in)\s+ipfs\b",
                    re.IGNORECASE,
                ),
                "ai.rag_summary",
                {
                    "pr_number": lambda m: int(m.group(1)),
                    "repo": lambda m: m.group(2),
                    "summary_backend": "accelerated",
                    "persist_output": True,
                },
            ),
            (
                re.compile(
                    r"\b(?:use\s+acceleration\s+for|use\s+accelerated\s+summary\s+for)\s+(?:rag\s+summary|augmented\s+summary)\s+(?:for\s+)?(?:pr|pull\s+request)\s+(\d+)\s+(?:to|in)\s+ipfs\b",
                    re.IGNORECASE,
                ),
                "ai.rag_summary",
                {
                    "pr_number": lambda m: int(m.group(1)),
                    "summary_backend": "accelerated",
                    "persist_output": True,
                },
            ),
            (
                re.compile(
                    r"\b(?:use\s+acceleration\s+for|use\s+accelerated\s+summary\s+for)\s+(?:rag\s+summary|augmented\s+summary)\s+(?:for\s+)?(?:pr|pull\s+request)\s+(\d+)\s+(?:on|in)\s+([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)\b",
                    re.IGNORECASE,
                ),
                "ai.rag_summary",
                {
                    "pr_number": lambda m: int(m.group(1)),
                    "repo": lambda m: m.group(2),
                    "summary_backend": "accelerated",
                },
            ),
            (
                re.compile(
                    r"\b(?:use\s+acceleration\s+for|use\s+accelerated\s+summary\s+for)\s+(?:rag\s+summary|augmented\s+summary)\s+(?:for\s+)?(?:pr|pull\s+request)\s+(\d+)\b",
                    re.IGNORECASE,
                ),
                "ai.rag_summary",
                {
                    "pr_number": lambda m: int(m.group(1)),
                    "summary_backend": "accelerated",
                },
            ),
            (
                re.compile(
                    r"\b(?:save|store|persist)\s+(?:rag\s+summary|augmented\s+summary)\s+(?:for\s+)?(?:pr|pull\s+request)\s+(\d+)\s+(?:on|in)\s+([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)\s+(?:to|in)\s+ipfs\b",
                    re.IGNORECASE,
                ),
                "ai.rag_summary",
                {
                    "pr_number": lambda m: int(m.group(1)),
                    "repo": lambda m: m.group(2),
                    "persist_output": True,
                },
            ),
            (
                re.compile(
                    r"\b(?:save|store|persist)\s+(?:rag\s+summary|augmented\s+summary)\s+(?:for\s+)?(?:pr|pull\s+request)\s+(\d+)\s+(?:to|in)\s+ipfs\b",
                    re.IGNORECASE,
                ),
                "ai.rag_summary",
                {
                    "pr_number": lambda m: int(m.group(1)),
                    "persist_output": True,
                },
            ),
            (
                re.compile(
                    r"\baccelerated\s+(?:rag\s+summary|augmented\s+summary)\s+(?:for\s+)?(?:pr|pull\s+request)\s+(\d+)\s+(?:on|in)\s+([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)\b",
                    re.IGNORECASE,
                ),
                "ai.accelerated_rag_summary",
                {
                    "pr_number": lambda m: int(m.group(1)),
                    "repo": lambda m: m.group(2),
                },
            ),
            (
                re.compile(
                    r"\baccelerated\s+(?:rag\s+summary|augmented\s+summary)\s+(?:for\s+)?(?:pr|pull\s+request)\s+(\d+)\b",
                    re.IGNORECASE,
                ),
                "ai.accelerated_rag_summary",
                {"pr_number": lambda m: int(m.group(1))},
            ),
            (
                re.compile(
                    r"\baccelerated\s+(?:rag\s+summary|augmented\s+summary)\b",
                    re.IGNORECASE,
                ),
                "ai.accelerated_rag_summary",
                {},
            ),
            (
                re.compile(
                    r"\b(?:rag\s+summary|augmented\s+summary)\s+(?:for\s+)?(?:pr|pull\s+request)\s+(\d+)\s+(?:on|in)\s+([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)\b",
                    re.IGNORECASE,
                ),
                "ai.rag_summary",
                {
                    "pr_number": lambda m: int(m.group(1)),
                    "repo": lambda m: m.group(2),
                },
            ),
            (
                re.compile(
                    r"\b(?:rag\s+summary|augmented\s+summary)\s+(?:for\s+)?(?:pr|pull\s+request)\s+(\d+)\b",
                    re.IGNORECASE,
                ),
                "ai.rag_summary",
                {"pr_number": lambda m: int(m.group(1))},
            ),
            (
                re.compile(r"\b(?:rag\s+summary|augmented\s+summary)\b", re.IGNORECASE),
                "ai.rag_summary",
                {},
            ),
            (
                re.compile(
                    r"\bfind\s+similar\s+failures\s+(?:for\s+)?(?:pr|pull\s+request)\s+(\d+)\s+(?:on|in)\s+([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)\s+using\s+cids?\s+([A-Za-z0-9,\s&-]+)\b",
                    re.IGNORECASE,
                ),
                "ai.find_similar_failures",
                {
                    "pr_number": lambda m: int(m.group(1)),
                    "repo": lambda m: m.group(2),
                    "history_cids": lambda m: _parse_cids(m.group(3)),
                },
            ),
            (
                re.compile(
                    r"\bfind\s+similar\s+failures\s+(?:for\s+)?(?:pr|pull\s+request)\s+(\d+)\s+using\s+cids?\s+([A-Za-z0-9,\s&-]+)\b",
                    re.IGNORECASE,
                ),
                "ai.find_similar_failures",
                {
                    "pr_number": lambda m: int(m.group(1)),
                    "history_cids": lambda m: _parse_cids(m.group(2)),
                },
            ),
            (
                re.compile(
                    r"\bfind\s+similar\s+workflow\s+(.+?)\s+failures\s+(?:for\s+)?(?:pr|pull\s+request)\s+(\d+)\s+using\s+cids?\s+([A-Za-z0-9,\s&-]+)\b",
                    re.IGNORECASE,
                ),
                "ai.find_similar_failures",
                {
                    "workflow_name": lambda m: m.group(1).strip(),
                    "pr_number": lambda m: int(m.group(2)),
                    "history_cids": lambda m: _parse_cids(m.group(3)),
                },
            ),
            (
                re.compile(
                    r"\bfind\s+similar\s+check\s+(.+?)\s+failures\s+(?:for\s+)?(?:pr|pull\s+request)\s+(\d+)\s+using\s+cids?\s+([A-Za-z0-9,\s&-]+)\b",
                    re.IGNORECASE,
                ),
                "ai.find_similar_failures",
                {
                    "check_name": lambda m: m.group(1).strip(),
                    "pr_number": lambda m: int(m.group(2)),
                    "history_cids": lambda m: _parse_cids(m.group(3)),
                },
            ),
            (
                re.compile(
                    r"\bfind\s+similar\s+failures\s+(?:for\s+)?(?:pr|pull\s+request)\s+(\d+)\s+(?:on|in)\s+([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)\b",
                    re.IGNORECASE,
                ),
                "ai.find_similar_failures",
                {
                    "pr_number": lambda m: int(m.group(1)),
                    "repo": lambda m: m.group(2),
                },
            ),
            (
                re.compile(
                    r"\bfind\s+similar\s+failures\s+(?:for\s+)?(?:pr|pull\s+request)\s+(\d+)\b",
                    re.IGNORECASE,
                ),
                "ai.find_similar_failures",
                {"pr_number": lambda m: int(m.group(1))},
            ),
            (
                re.compile(
                    r"\bfind\s+similar\s+workflow\s+(.+?)\s+failures\s+(?:for\s+)?(?:pr|pull\s+request)\s+(\d+)\b",
                    re.IGNORECASE,
                ),
                "ai.find_similar_failures",
                {
                    "workflow_name": lambda m: m.group(1).strip(),
                    "pr_number": lambda m: int(m.group(2)),
                },
            ),
            (
                re.compile(
                    r"\bfind\s+similar\s+check\s+(.+?)\s+failures\s+(?:for\s+)?(?:pr|pull\s+request)\s+(\d+)\b",
                    re.IGNORECASE,
                ),
                "ai.find_similar_failures",
                {
                    "check_name": lambda m: m.group(1).strip(),
                    "pr_number": lambda m: int(m.group(2)),
                },
            ),
            (
                re.compile(r"\bfind\s+similar\s+failures\b", re.IGNORECASE),
                "ai.find_similar_failures",
                {},
            ),
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
            # AI / Copilot read-only commands
            (
                re.compile(
                    r"\bexplain\s+pr\s+(\d+)\s+(?:on|in)\s+([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)\b",
                    re.IGNORECASE,
                ),
                "ai.explain_pr",
                {
                    "pr_number": lambda m: int(m.group(1)),
                    "repo": lambda m: m.group(2),
                },
            ),
            (
                re.compile(r"\bexplain\s+pr\s+(\d+)\b", re.IGNORECASE),
                "ai.explain_pr",
                {"pr_number": lambda m: int(m.group(1))},
            ),
            (
                re.compile(
                    r"\buse\s+copilot\s+to\s+summarize\s+diff\s+(?:for\s+)?(?:pr|pull\s+request)\s+(\d+)\s+(?:on|in)\s+([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)\b",
                    re.IGNORECASE,
                ),
                "ai.summarize_diff",
                {
                    "pr_number": lambda m: int(m.group(1)),
                    "repo": lambda m: m.group(2),
                    "provider": "copilot_cli",
                },
            ),
            (
                re.compile(
                    r"\buse\s+copilot\s+to\s+summarize\s+diff\s+(?:for\s+)?(?:pr|pull\s+request)\s+(\d+)\b",
                    re.IGNORECASE,
                ),
                "ai.summarize_diff",
                {
                    "pr_number": lambda m: int(m.group(1)),
                    "provider": "copilot_cli",
                },
            ),
            (
                re.compile(
                    r"\buse\s+acceleration\s+for\s+explain\s+(?:the\s+)?(?:failing\s+(?:checks?)|failure)\s+(?:for\s+)?(?:pr|pull\s+request)\s+(\d+)\s+(?:on|in)\s+([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)\s+(?:to|in)\s+ipfs\b",
                    re.IGNORECASE,
                ),
                "ai.explain_failure",
                {
                    "pr_number": lambda m: int(m.group(1)),
                    "repo": lambda m: m.group(2),
                    "failure_backend": "accelerated",
                    "persist_output": True,
                },
            ),
            (
                re.compile(
                    r"\buse\s+acceleration\s+for\s+explain\s+(?:the\s+)?(?:failing\s+(?:checks?)|failure)\s+(?:for\s+)?(?:pr|pull\s+request)\s+(\d+)\s+(?:to|in)\s+ipfs\b",
                    re.IGNORECASE,
                ),
                "ai.explain_failure",
                {
                    "pr_number": lambda m: int(m.group(1)),
                    "failure_backend": "accelerated",
                    "persist_output": True,
                },
            ),
            (
                re.compile(
                    r"\buse\s+acceleration\s+for\s+explain\s+(check|workflow)\s+(.+?)\s+for\s+(?:pr|pull\s+request)\s+(\d+)\s+(?:to|in)\s+ipfs\b",
                    re.IGNORECASE,
                ),
                "ai.explain_failure",
                {
                    "workflow_name": lambda m: m.group(2).strip()
                    if m.group(1).lower() == "workflow"
                    else None,
                    "check_name": lambda m: m.group(2).strip()
                    if m.group(1).lower() == "check"
                    else None,
                    "pr_number": lambda m: int(m.group(3)),
                    "failure_backend": "accelerated",
                    "persist_output": True,
                },
            ),
            (
                re.compile(
                    r"\buse\s+acceleration\s+for\s+explain\s+(?:the\s+)?(?:failing\s+(?:checks?)|failure)\s+(?:for\s+)?(?:pr|pull\s+request)\s+(\d+)\s+(?:on|in)\s+([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)\b",
                    re.IGNORECASE,
                ),
                "ai.explain_failure",
                {
                    "pr_number": lambda m: int(m.group(1)),
                    "repo": lambda m: m.group(2),
                    "failure_backend": "accelerated",
                },
            ),
            (
                re.compile(
                    r"\buse\s+acceleration\s+for\s+explain\s+(?:the\s+)?(?:failing\s+(?:checks?)|failure)\s+(?:for\s+)?(?:pr|pull\s+request)\s+(\d+)\b",
                    re.IGNORECASE,
                ),
                "ai.explain_failure",
                {
                    "pr_number": lambda m: int(m.group(1)),
                    "failure_backend": "accelerated",
                },
            ),
            (
                re.compile(
                    r"\buse\s+acceleration\s+for\s+explain\s+(check|workflow)\s+(.+?)\s+for\s+(?:pr|pull\s+request)\s+(\d+)\b",
                    re.IGNORECASE,
                ),
                "ai.explain_failure",
                {
                    "workflow_name": lambda m: m.group(2).strip()
                    if m.group(1).lower() == "workflow"
                    else None,
                    "check_name": lambda m: m.group(2).strip()
                    if m.group(1).lower() == "check"
                    else None,
                    "pr_number": lambda m: int(m.group(3)),
                    "failure_backend": "accelerated",
                },
            ),
            (
                re.compile(
                    r"\buse\s+copilot\s+to\s+explain\s+(?:the\s+)?(?:failing\s+(?:checks?)|failure)\s+(?:for\s+)?(?:pr|pull\s+request)\s+(\d+)\s+(?:on|in)\s+([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)\b",
                    re.IGNORECASE,
                ),
                "ai.explain_failure",
                {
                    "pr_number": lambda m: int(m.group(1)),
                    "repo": lambda m: m.group(2),
                    "provider": "copilot_cli",
                },
            ),
            (
                re.compile(
                    r"\buse\s+copilot\s+to\s+explain\s+(?:the\s+)?(?:failing\s+(?:checks?)|failure)\s+(?:for\s+)?(?:pr|pull\s+request)\s+(\d+)\b",
                    re.IGNORECASE,
                ),
                "ai.explain_failure",
                {
                    "pr_number": lambda m: int(m.group(1)),
                    "provider": "copilot_cli",
                },
            ),
            (
                re.compile(
                    r"\baccelerated\s+(?:failure\s+analysis|explain\s+failure)\s+(?:for\s+)?(?:pr|pull\s+request)\s+(\d+)\s+(?:on|in)\s+([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)\b",
                    re.IGNORECASE,
                ),
                "ai.accelerated_explain_failure",
                {
                    "pr_number": lambda m: int(m.group(1)),
                    "repo": lambda m: m.group(2),
                },
            ),
            (
                re.compile(
                    r"\baccelerated\s+(?:failure\s+analysis|explain\s+failure)\s+(?:for\s+)?(?:pr|pull\s+request)\s+(\d+)\b",
                    re.IGNORECASE,
                ),
                "ai.accelerated_explain_failure",
                {
                    "pr_number": lambda m: int(m.group(1)),
                },
            ),
            (
                re.compile(
                    r"\baccelerated\s+explain\s+(check|workflow)\s+(.+?)\s+for\s+(?:pr|pull\s+request)\s+(\d+)\b",
                    re.IGNORECASE,
                ),
                "ai.accelerated_explain_failure",
                {
                    "workflow_name": lambda m: m.group(2).strip()
                    if m.group(1).lower() == "workflow"
                    else None,
                    "check_name": lambda m: m.group(2).strip()
                    if m.group(1).lower() == "check"
                    else None,
                    "pr_number": lambda m: int(m.group(3)),
                },
            ),
            (
                re.compile(
                    r"\buse\s+copilot\s+to\s+explain\s+(check|workflow)\s+(.+?)\s+for\s+(?:pr|pull\s+request)\s+(\d+)\s+(?:on|in)\s+([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)\b",
                re.IGNORECASE,
                ),
                "ai.explain_failure",
                {
                    "workflow_name": lambda m: m.group(2).strip()
                    if m.group(1).lower() == "workflow"
                    else None,
                    "check_name": lambda m: m.group(2).strip()
                    if m.group(1).lower() == "check"
                    else None,
                    "pr_number": lambda m: int(m.group(3)),
                    "repo": lambda m: m.group(4),
                    "provider": "copilot_cli",
                },
            ),
            (
                re.compile(
                    r"\buse\s+copilot\s+to\s+explain\s+(check|workflow)\s+(.+?)\s+for\s+(?:pr|pull\s+request)\s+(\d+)\b",
                re.IGNORECASE,
                ),
                "ai.explain_failure",
                {
                    "workflow_name": lambda m: m.group(2).strip()
                    if m.group(1).lower() == "workflow"
                    else None,
                    "check_name": lambda m: m.group(2).strip()
                    if m.group(1).lower() == "check"
                    else None,
                    "pr_number": lambda m: int(m.group(3)),
                    "provider": "copilot_cli",
                },
            ),
            (
                re.compile(
                    r"\bsummarize\s+diff\s+(?:for\s+)?(?:pr|pull\s+request)\s+(\d+)\s+(?:on|in)\s+([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)\b",
                    re.IGNORECASE,
                ),
                "ai.summarize_diff",
                {
                    "pr_number": lambda m: int(m.group(1)),
                    "repo": lambda m: m.group(2),
                },
            ),
            (
                re.compile(
                    r"\bsummarize\s+diff\s+(?:for\s+)?(?:pr|pull\s+request)\s+(\d+)\b",
                    re.IGNORECASE,
                ),
                "ai.summarize_diff",
                {"pr_number": lambda m: int(m.group(1))},
            ),
            (
                re.compile(r"\bsummarize\s+diff\b", re.IGNORECASE),
                "ai.summarize_diff",
                {},
            ),
            (
                re.compile(
                    r"\bexplain\s+(check|workflow)\s+(.+?)\s+for\s+(?:pr|pull\s+request)\s+(\d+)\s+(?:on|in)\s+([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)\s+using\s+cids?\s+([A-Za-z0-9,\s&-]+)\b",
                    re.IGNORECASE,
                ),
                "ai.explain_failure",
                {
                    "workflow_name": lambda m: m.group(2).strip()
                    if m.group(1).lower() == "workflow"
                    else None,
                    "check_name": lambda m: m.group(2).strip()
                    if m.group(1).lower() == "check"
                    else None,
                    "pr_number": lambda m: int(m.group(3)),
                    "repo": lambda m: m.group(4),
                    "history_cids": lambda m: _parse_cids(m.group(5)),
                },
            ),
            (
                re.compile(
                    r"\bexplain\s+(check|workflow)\s+(.+?)\s+for\s+(?:pr|pull\s+request)\s+(\d+)\s+using\s+cids?\s+([A-Za-z0-9,\s&-]+)\b",
                    re.IGNORECASE,
                ),
                "ai.explain_failure",
                {
                    "workflow_name": lambda m: m.group(2).strip()
                    if m.group(1).lower() == "workflow"
                    else None,
                    "check_name": lambda m: m.group(2).strip()
                    if m.group(1).lower() == "check"
                    else None,
                    "pr_number": lambda m: int(m.group(3)),
                    "history_cids": lambda m: _parse_cids(m.group(4)),
                },
            ),
            (
                re.compile(
                    r"\bexplain\s+(check|workflow)\s+(.+?)\s+for\s+(?:pr|pull\s+request)\s+(\d+)\s+(?:on|in)\s+([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)\b",
                re.IGNORECASE,
                ),
                "ai.explain_failure",
                {
                    "workflow_name": lambda m: m.group(2).strip()
                    if m.group(1).lower() == "workflow"
                    else None,
                    "check_name": lambda m: m.group(2).strip()
                    if m.group(1).lower() == "check"
                    else None,
                    "pr_number": lambda m: int(m.group(3)),
                    "repo": lambda m: m.group(4),
                },
            ),
            (
                re.compile(
                    r"\bexplain\s+(check|workflow)\s+(.+?)\s+for\s+(?:pr|pull\s+request)\s+(\d+)\b",
                re.IGNORECASE,
                ),
                "ai.explain_failure",
                {
                    "workflow_name": lambda m: m.group(2).strip()
                    if m.group(1).lower() == "workflow"
                    else None,
                    "check_name": lambda m: m.group(2).strip()
                    if m.group(1).lower() == "check"
                    else None,
                    "pr_number": lambda m: int(m.group(3)),
                },
            ),
            (
                re.compile(
                    r"\b(?:save|store|persist)\s+(?:explain|summarize)\s+(?:the\s+)?(?:failing\s+(?:checks?)|failure)\s+(?:for\s+)?(?:pr|pull\s+request)\s+(\d+)\s+(?:on|in)\s+([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)\s+using\s+cids?\s+([A-Za-z0-9,\s&-]+)\s+(?:to|in)\s+ipfs\b",
                    re.IGNORECASE,
                ),
                "ai.explain_failure",
                {
                    "pr_number": lambda m: int(m.group(1)),
                    "repo": lambda m: m.group(2),
                    "history_cids": lambda m: _parse_cids(m.group(3)),
                    "persist_output": True,
                },
            ),
            (
                re.compile(
                    r"\b(?:save|store|persist)\s+(?:explain|summarize)\s+(?:the\s+)?(?:failing\s+(?:checks?)|failure)\s+(?:for\s+)?(?:pr|pull\s+request)\s+(\d+)\s+using\s+cids?\s+([A-Za-z0-9,\s&-]+)\s+(?:to|in)\s+ipfs\b",
                    re.IGNORECASE,
                ),
                "ai.explain_failure",
                {
                    "pr_number": lambda m: int(m.group(1)),
                    "history_cids": lambda m: _parse_cids(m.group(2)),
                    "persist_output": True,
                },
            ),
            (
                re.compile(
                    r"\b(?:explain|summarize)\s+(?:the\s+)?(?:failing\s+(?:checks?)|failure)\s+(?:for\s+)?(?:pr|pull\s+request)\s+(\d+)\s+(?:on|in)\s+([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)\s+using\s+cids?\s+([A-Za-z0-9,\s&-]+)\b",
                    re.IGNORECASE,
                ),
                "ai.explain_failure",
                {
                    "pr_number": lambda m: int(m.group(1)),
                    "repo": lambda m: m.group(2),
                    "history_cids": lambda m: _parse_cids(m.group(3)),
                },
            ),
            (
                re.compile(
                    r"\b(?:explain|summarize)\s+(?:the\s+)?(?:failing\s+(?:checks?)|failure)\s+(?:for\s+)?(?:pr|pull\s+request)\s+(\d+)\s+using\s+cids?\s+([A-Za-z0-9,\s&-]+)\b",
                    re.IGNORECASE,
                ),
                "ai.explain_failure",
                {
                    "pr_number": lambda m: int(m.group(1)),
                    "history_cids": lambda m: _parse_cids(m.group(2)),
                },
            ),
            (
                re.compile(
                    r"\b(?:save|store|persist)\s+(?:explain|summarize)\s+(?:the\s+)?(?:failing\s+(?:checks?)|failure)\s+(?:for\s+)?(?:pr|pull\s+request)\s+(\d+)\s+(?:on|in)\s+([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)\s+(?:to|in)\s+ipfs\b",
                    re.IGNORECASE,
                ),
                "ai.explain_failure",
                {
                    "pr_number": lambda m: int(m.group(1)),
                    "repo": lambda m: m.group(2),
                    "persist_output": True,
                },
            ),
            (
                re.compile(
                    r"\b(?:save|store|persist)\s+(?:explain|summarize)\s+(?:the\s+)?(?:failing\s+(?:checks?)|failure)\s+(?:for\s+)?(?:pr|pull\s+request)\s+(\d+)\s+(?:to|in)\s+ipfs\b",
                    re.IGNORECASE,
                ),
                "ai.explain_failure",
                {
                    "pr_number": lambda m: int(m.group(1)),
                    "persist_output": True,
                },
            ),
            (
                re.compile(
                    r"\b(?:explain|summarize)\s+(?:the\s+)?failing?\s+(?:checks?|failure)\s+(?:for\s+)?(?:pr|pull\s+request)\s+(\d+)\b",
                    re.IGNORECASE,
                ),
                "ai.explain_failure",
                {"pr_number": lambda m: int(m.group(1))},
            ),
            (
                re.compile(
                    r"\b(?:explain|summarize)\s+(?:the\s+)?failing?\s+(?:checks?|failure)\b",
                    re.IGNORECASE,
                ),
                "ai.explain_failure",
                {},
            ),
            (
                re.compile(
                    r"\buse\s+copilot\s+to\s+explain\s+(?:pr|pull\s+request)\s+(\d+)\s+(?:on|in)\s+([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)\b",
                    re.IGNORECASE,
                ),
                "ai.explain_pr",
                {
                    "pr_number": lambda m: int(m.group(1)),
                    "repo": lambda m: m.group(2),
                    "provider": "copilot_cli",
                },
            ),
            (
                re.compile(
                    r"\buse\s+copilot\s+to\s+explain\s+(?:pr|pull\s+request)\s+(\d+)\b",
                    re.IGNORECASE,
                ),
                "ai.explain_pr",
                {
                    "pr_number": lambda m: int(m.group(1)),
                    "provider": "copilot_cli",
                },
            ),
            (
                re.compile(
                    r"\bask\s+copilot\s+to\s+explain\s+(?:pr|pull\s+request)\s+(\d+)\b",
                    re.IGNORECASE,
                ),
                "ai.explain_pr",
                {
                    "pr_number": lambda m: int(m.group(1)),
                    "provider": "copilot_cli",
                },
            ),
            # Direct MCP-backed IPFS intents
            (
                re.compile(
                    r"^(?!.*\bagent\b).*\b(?:find|search|discover)\s+(.+?\s+datasets?)\b.*$",
                    re.IGNORECASE,
                ),
                "agent.delegate",
                {
                    "instruction": lambda m: f"{m.group(0).strip()}",
                    "provider": "ipfs_datasets_mcp",
                    "mcp_capability": "dataset_discovery",
                    "mcp_input": lambda m: m.group(1).strip(),
                },
            ),
            (
                re.compile(
                    r"^(?!.*\bagent\b).*\b(?:add|upload|store)\s+(.+?)\s+to\s+ipfs\b.*$",
                    re.IGNORECASE,
                ),
                "agent.delegate",
                {
                    "instruction": lambda m: m.group(0).strip(),
                    "provider": "ipfs_kit_mcp",
                    "mcp_capability": "ipfs_add",
                    "mcp_input": lambda m: m.group(1).strip(),
                },
            ),
            (
                re.compile(
                    r"^(?!.*\bagent\b).*\b(?:cat|fetch|get|read|download)\s+(.+?)\s+(?:from|on|in)\s+ipfs\b.*$",
                    re.IGNORECASE,
                ),
                "agent.delegate",
                {
                    "instruction": lambda m: m.group(0).strip(),
                    "provider": "ipfs_kit_mcp",
                    "mcp_capability": "ipfs_cat",
                    "mcp_input": lambda m: m.group(1).strip(),
                    "mcp_cid": lambda m: m.group(1).strip(),
                },
            ),
            (
                re.compile(
                    r"^(?!.*\bagent\b).*\b(pin|unpin)\s+(.+?)\s+(?:from|on|in)\s+ipfs\b.*$",
                    re.IGNORECASE,
                ),
                "agent.delegate",
                {
                    "instruction": lambda m: m.group(0).strip(),
                    "provider": "ipfs_kit_mcp",
                    "mcp_capability": "ipfs_pin",
                    "mcp_input": lambda m: m.group(2).strip(),
                    "mcp_cid": lambda m: m.group(2).strip(),
                    "mcp_pin_action": lambda m: m.group(1).strip().lower(),
                },
            ),
            (
                re.compile(
                    r"^(?!.*\bagent\b).*\b(?:run|start|create)\s+(?:an?\s+)?(?:p2p\s+|distributed\s+)?workflow\b.*$",
                    re.IGNORECASE,
                ),
                "agent.delegate",
                {
                    "instruction": lambda m: m.group(0).strip(),
                    "provider": "ipfs_accelerate_mcp",
                    "mcp_capability": "workflow",
                },
            ),
            (
                re.compile(
                    r"^(?!.*\bagent\b).*\bdiscover\s+and\s+fetch\s+(.+?)\s+from\s+(https?://\S+)\b.*$",
                    re.IGNORECASE,
                ),
                "agent.delegate",
                {
                    "instruction": lambda m: m.group(0).strip(),
                    "provider": "ipfs_accelerate_mcp",
                    "mcp_capability": "agentic_fetch",
                    "mcp_input": lambda m: m.group(1).strip(),
                    "mcp_seed_url": lambda m: m.group(2).strip(),
                },
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
                    r"\b(?:ask|have|tell)\s+(?:the\s+)?(ipfs\s+datasets|ipfs\s+dataset|ipfs\s+kit|ipfs\s+accelerate)\s+agent\s+(?:to\s+)?(.*?)\s+(?:on\s+)?(?:pr|pull\s+request)\s+(\d+)$",
                    re.IGNORECASE,
                ),
                "agent.delegate",
                {
                    "provider": lambda m: _parse_agent_provider(m.group(1)),
                    "instruction": lambda m: m.group(2).strip(),
                    "pr_number": lambda m: int(m.group(3)),
                },
            ),
            (
                re.compile(
                    r"\b(?:ask|have|tell)\s+(?:the\s+)?(ipfs\s+datasets|ipfs\s+dataset|ipfs\s+kit|ipfs\s+accelerate)\s+agent\s+(?:to\s+)?(.*?)\s+(?:issue|on\s+issue)\s+(\d+)$",
                    re.IGNORECASE,
                ),
                "agent.delegate",
                {
                    "provider": lambda m: _parse_agent_provider(m.group(1)),
                    "instruction": lambda m: m.group(2).strip(),
                    "issue_number": lambda m: int(m.group(3)),
                },
            ),
            (
                re.compile(
                    r"\b(?:ask|have|tell)\s+(?:the\s+)?(ipfs\s+datasets|ipfs\s+dataset|ipfs\s+kit|ipfs\s+accelerate)\s+agent\s+(?:to\s+)?(.+)$",
                    re.IGNORECASE,
                ),
                "agent.delegate",
                {
                    "provider": lambda m: _parse_agent_provider(m.group(1)),
                    "instruction": lambda m: m.group(2).strip(),
                },
            ),
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
            # PR comment (side effect)
            (
                re.compile(
                    r"\bcomment\s+on\s+(?:pr|pull\s+request)\s+(\d+):\s*(.+)$",
                    re.IGNORECASE,
                ),
                "pr.comment",
                {
                    "pr_number": lambda m: int(m.group(1)),
                    "comment_body": lambda m: m.group(2).strip(),
                },
            ),
            (
                re.compile(
                    r"\bpost\s+comment\s+on\s+(?:pr|pull\s+request)\s+(\d+)\s+saying\s+(.+)$",
                    re.IGNORECASE,
                ),
                "pr.comment",
                {
                    "pr_number": lambda m: int(m.group(1)),
                    "comment_body": lambda m: m.group(2).strip(),
                },
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
            (
                re.compile(
                    r"\b(?:show|list|summarize|read)\s+(?:the\s+)?latest\s+(dataset\s+discoveries|ipfs\s+results|fetches)\b",
                    re.IGNORECASE,
                ),
                "agent.results",
                {
                    "view": lambda m: {
                        "dataset discoveries": "datasets",
                        "ipfs results": "ipfs",
                        "fetches": "fetches",
                    }[m.group(1).strip().lower()],
                },
            ),
            (
                re.compile(
                    r"\b(?:show|list|summarize|read)\s+(?:the\s+)?recent\s+(dataset\s+discoveries|ipfs\s+results|fetches)\b",
                    re.IGNORECASE,
                ),
                "agent.results",
                {
                    "view": lambda m: {
                        "dataset discoveries": "datasets",
                        "ipfs results": "ipfs",
                        "fetches": "fetches",
                    }[m.group(1).strip().lower()],
                },
            ),
            (
                re.compile(r"\bagent\s+results\b", re.IGNORECASE),
                "agent.results",
                {"view": "overview"},
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

                if intent_name in {
                    "agent.delegate",
                    "agent.result_save_ipfs",
                    "agent.result_pin",
                    "agent.result_unpin",
                    "agent.result_rerun",
                    "agent.result_rerun_fetch",
                    "agent.result_rerun_dataset",
                }:
                    preferred_mode = _infer_agent_execution_mode(text)
                    if preferred_mode is not None:
                        entities.setdefault("mcp_preferred_execution_mode", preferred_mode)

                return ParsedIntent(name=intent_name, confidence=confidence, entities=entities)

        # No match found - return unknown intent with low confidence
        return ParsedIntent(name="unknown", confidence=0.0, entities={"text": text})
