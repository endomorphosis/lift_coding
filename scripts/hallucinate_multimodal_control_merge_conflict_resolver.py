#!/usr/bin/env python3
"""Prepare or invoke an LLM merge-conflict resolver for HAO daemon failures."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_ACCELERATE_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"

if str(IPFS_ACCELERATE_ROOT) not in sys.path:
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))

from ipfs_accelerate_py.agent_supervisor.wrapper_utils import prefixed_env_var as _prefixed_env_var  # noqa: E402
from ipfs_accelerate_py.agent_supervisor.implementation_daemon_runner import (  # noqa: E402
    implementation_state_artifact_paths,
)

DEFAULT_STATE_DIR = REPO_ROOT / "data" / "hallucinate_multimodal_control" / "state"
DEFAULT_EVENTS_PATH = implementation_state_artifact_paths(
    DEFAULT_STATE_DIR,
    "hallucinate_multimodal_control",
)["events_path"]
HAO_ENV_PREFIX = "HANDSFREE_HAO"
HAO_LLM_MERGE_RESOLVER_COMMAND_ENV = _prefixed_env_var(HAO_ENV_PREFIX, "LLM_MERGE_RESOLVER_COMMAND")
HAO_PROMPT_HEADING = "Resolve the HAO daemon merge conflict in this repository."
HAO_COMPLETION_RULE = "Do not remove the task from blocked_tasks until validation passes."

from ipfs_accelerate_py.agent_supervisor.merge_resolver import (  # noqa: E402
    build_configured_merge_resolver_runner,
    compact_text,
    iter_jsonl,
    latest_failed_merge_event,
    unmerged_paths,
)

_HAO_MERGE_RESOLVER_RUNNER = build_configured_merge_resolver_runner(
    default_events_path=DEFAULT_EVENTS_PATH,
    default_repo_root=REPO_ROOT,
    prompt_heading=HAO_PROMPT_HEADING,
    completion_rule=HAO_COMPLETION_RULE,
    primary_command_env_var=HAO_LLM_MERGE_RESOLVER_COMMAND_ENV,
    description=__doc__ or "Prepare or invoke an LLM merge-conflict resolver.",
    missing_event_exit_code=1,
    apply_failed_exit_code=2,
)

build_merge_prompt = _HAO_MERGE_RESOLVER_RUNNER.build_merge_prompt()
resolver_payload = _HAO_MERGE_RESOLVER_RUNNER.resolver_payload()
invoke_llm_resolver = _HAO_MERGE_RESOLVER_RUNNER.llm_resolver_invoker()

__all__ = [
    "build_merge_prompt",
    "compact_text",
    "invoke_llm_resolver",
    "iter_jsonl",
    "latest_failed_merge_event",
    "resolver_payload",
    "unmerged_paths",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    return _HAO_MERGE_RESOLVER_RUNNER.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    return _HAO_MERGE_RESOLVER_RUNNER.run(argv)


if __name__ == "__main__":
    sys.exit(main())
