from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MOCKUP_DOC = REPO_ROOT / "hallucinate_app" / "docs" / "SWISSKNIFE_VIRTUAL_DESKTOP_MOCKUP.md"
OBJECTIVE_HEAP = (
    REPO_ROOT / "implementation_plan" / "docs" / "23-virtual-ai-os-objective-goal-heap.md"
)
ORB_HARNESS = (
    REPO_ROOT / "swissknife" / "test" / "mcp-plus-plus" / "meta-glasses-display-harness.test.ts"
)


def _goal_block(heap_text: str, goal_id: str) -> str:
    marker = f"## {goal_id} "
    start = heap_text.index(marker)
    next_goal = heap_text.find("\n## VAIOS-", start + len(marker))
    return heap_text[start:] if next_goal == -1 else heap_text[start:next_goal]


def test_vaios_g040_operator_shell_evidence_terms_are_documented():
    mockup = MOCKUP_DOC.read_text(encoding="utf-8")
    harness = ORB_HARNESS.read_text(encoding="utf-8")

    required_terms = [
        "Hallucinate App operator console",
        "ORB display harness",
        "task monitor",
        "app launcher",
        "ORB inspector",
        "session replay",
        "swissknife/test/mcp-plus-plus/meta-glasses-display-harness.test.ts",
    ]
    for term in required_terms:
        assert term in mockup

    assert "ORB display harness" in harness


def test_vaios_g040_child_goals_are_aligned_with_operator_shell_heap():
    heap = OBJECTIVE_HEAP.read_text(encoding="utf-8")
    parent = _goal_block(heap, "VAIOS-G040")

    assert "hallucinate_app/docs/SWISSKNIFE_VIRTUAL_DESKTOP_MOCKUP.md" in parent
    assert "swissknife/test/mcp-plus-plus/meta-glasses-display-harness.test.ts" in parent
    assert "HAO-064 proof" in parent

    child_goals = {
        "VAIOS-G041": "task monitor",
        "VAIOS-G042": "app launcher",
        "VAIOS-G043": "ORB inspector",
        "VAIOS-G044": "session replay",
    }
    for goal_id, evidence_term in child_goals.items():
        block = _goal_block(heap, goal_id)
        assert "- Parent: VAIOS-G040" in block
        assert evidence_term in block
        assert "pytest tests/test_virtual_ai_os_operator_shell_docs.py" in block
