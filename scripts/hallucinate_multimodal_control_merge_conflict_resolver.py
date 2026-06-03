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

DEFAULT_STATE_DIR = REPO_ROOT / "data" / "hallucinate_multimodal_control" / "state"
DEFAULT_EVENTS_PATH = DEFAULT_STATE_DIR / "hallucinate_multimodal_control_events.jsonl"
HAO_ENV_PREFIX = "HANDSFREE_HAO"
HAO_LLM_MERGE_RESOLVER_COMMAND_ENV = _prefixed_env_var(HAO_ENV_PREFIX, "LLM_MERGE_RESOLVER_COMMAND")
HAO_PROMPT_HEADING = "Resolve the HAO daemon merge conflict in this repository."
HAO_COMPLETION_RULE = "Do not remove the task from blocked_tasks until validation passes."

from ipfs_accelerate_py.agent_supervisor.merge_resolver import (  # noqa: E402
    MergeResolverCliConfig,
    build_configured_merge_resolver_arg_parser,
    build_llm_merge_resolver_invoker,
    build_merge_prompt_callback,
    build_resolver_payload_callback,
    compact_text,
    iter_jsonl,
    latest_failed_merge_event,
    run_configured_merge_resolver_cli,
    unmerged_paths,
)

_HAO_MERGE_RESOLVER_CONFIG = MergeResolverCliConfig(
    default_events_path=DEFAULT_EVENTS_PATH,
    default_repo_root=REPO_ROOT,
    prompt_heading=HAO_PROMPT_HEADING,
    completion_rule=HAO_COMPLETION_RULE,
    primary_command_env_var=HAO_LLM_MERGE_RESOLVER_COMMAND_ENV,
    description=__doc__ or "Prepare or invoke an LLM merge-conflict resolver.",
    missing_event_exit_code=1,
    apply_failed_exit_code=2,
)

build_merge_prompt = build_merge_prompt_callback(
    prompt_heading=HAO_PROMPT_HEADING,
    completion_rule=HAO_COMPLETION_RULE,
)
resolver_payload = build_resolver_payload_callback(
    prompt_heading=HAO_PROMPT_HEADING,
    completion_rule=HAO_COMPLETION_RULE,
)
invoke_llm_resolver = build_llm_merge_resolver_invoker(
    primary_command_env_var=HAO_LLM_MERGE_RESOLVER_COMMAND_ENV,
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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    return build_configured_merge_resolver_arg_parser(_HAO_MERGE_RESOLVER_CONFIG).parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    return run_configured_merge_resolver_cli(_HAO_MERGE_RESOLVER_CONFIG, argv)


if __name__ == "__main__":
    sys.exit(main())
