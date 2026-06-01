#!/usr/bin/env python3
"""Prepare or invoke an LLM merge-conflict resolver for HAO daemon failures."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_ACCELERATE_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"
DEFAULT_STATE_DIR = REPO_ROOT / "data" / "hallucinate_multimodal_control" / "state"
DEFAULT_EVENTS_PATH = DEFAULT_STATE_DIR / "hallucinate_multimodal_control_events.jsonl"
HAO_LLM_MERGE_RESOLVER_COMMAND_ENV = "HANDSFREE_HAO_LLM_MERGE_RESOLVER_COMMAND"
HAO_PROMPT_HEADING = "Resolve the HAO daemon merge conflict in this repository."
HAO_COMPLETION_RULE = "Do not remove the task from blocked_tasks until validation passes."

if str(IPFS_ACCELERATE_ROOT) not in sys.path:
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))

from ipfs_accelerate_py.agent_supervisor.merge_resolver import (  # noqa: E402
    LLM_MERGE_RESOLVER_COMMAND_ENV,
    build_merge_prompt as _build_merge_prompt,
    compact_text,
    invoke_llm_resolver as _invoke_llm_resolver,
    iter_jsonl,
    latest_failed_merge_event,
    resolver_payload as _resolver_payload,
    unmerged_paths,
)

__all__ = [
    "build_merge_prompt",
    "compact_text",
    "invoke_llm_resolver",
    "iter_jsonl",
    "latest_failed_merge_event",
    "resolver_payload",
    "unmerged_paths",
]


def build_merge_prompt(*, event: dict[str, object], repo_root: Path) -> str:
    return _build_merge_prompt(
        event=event,
        repo_root=repo_root,
        prompt_heading=HAO_PROMPT_HEADING,
        completion_rule=HAO_COMPLETION_RULE,
    )


def resolver_payload(*, events_path: Path, repo_root: Path, task_id: str | None = None) -> dict[str, object]:
    return _resolver_payload(
        events_path=events_path,
        repo_root=repo_root,
        task_id=task_id,
        prompt_heading=HAO_PROMPT_HEADING,
        completion_rule=HAO_COMPLETION_RULE,
    )


def invoke_llm_resolver(payload: dict[str, object]) -> dict[str, object]:
    command_template = os.environ.get(HAO_LLM_MERGE_RESOLVER_COMMAND_ENV, "").strip() or None
    if command_template is None and not os.environ.get(LLM_MERGE_RESOLVER_COMMAND_ENV, "").strip():
        return {
            **payload,
            "applied": False,
            "apply_error": f"{HAO_LLM_MERGE_RESOLVER_COMMAND_ENV} or {LLM_MERGE_RESOLVER_COMMAND_ENV} is not set",
        }
    return _invoke_llm_resolver(payload, command_template=command_template)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-id", default=None, help="Resolve the latest merge failure for this HAO task id.")
    parser.add_argument("--events-path", type=Path, default=DEFAULT_EVENTS_PATH)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--apply", action="store_true", help="Invoke the configured LLM resolver command.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = resolver_payload(
        events_path=args.events_path,
        repo_root=args.repo_root,
        task_id=args.task_id,
    )
    if args.apply and payload.get("found"):
        payload = invoke_llm_resolver(payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    if not payload.get("found"):
        return 1
    if args.apply and not payload.get("applied"):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
