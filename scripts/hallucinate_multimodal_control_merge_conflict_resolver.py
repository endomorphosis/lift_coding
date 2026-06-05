#!/usr/bin/env python3
"""Prepare or invoke an LLM merge-conflict resolver for HAO daemon failures."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


SCRIPT_REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_ACCELERATE_ROOT = SCRIPT_REPO_ROOT / "external" / "ipfs_accelerate"

if str(IPFS_ACCELERATE_ROOT) not in sys.path:
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))

HAO_ENV_PREFIX = "HANDSFREE_HAO"
HAO_PROMPT_HEADING = "Resolve the HAO daemon merge conflict in this repository."
HAO_COMPLETION_RULE = "Do not remove the task from blocked_tasks until validation passes."

from ipfs_accelerate_py.agent_supervisor.wrapper_utils import build_repo_script_bootstrap  # noqa: E402
from ipfs_accelerate_py.agent_supervisor.merge_resolver import (  # noqa: E402
    build_namespace_merge_resolver_runner,
    compact_text,
    iter_jsonl,
    latest_failed_merge_event,
    unmerged_paths,
)

_SCRIPT_BOOTSTRAP = build_repo_script_bootstrap(__file__)
SCRIPT_REPO_ROOT = _SCRIPT_BOOTSTRAP.script_repo_root
IPFS_ACCELERATE_ROOT = _SCRIPT_BOOTSTRAP.package_root
REPO_ROOT = _SCRIPT_BOOTSTRAP.repo_root
_HAO_MERGE_RESOLVER_RUNNER = build_namespace_merge_resolver_runner(
    repo_root=REPO_ROOT,
    namespace="hallucinate_multimodal_control",
    env_prefix=HAO_ENV_PREFIX,
    prompt_heading=HAO_PROMPT_HEADING,
    completion_rule=HAO_COMPLETION_RULE,
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
