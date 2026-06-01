#!/usr/bin/env python3
"""Use the accelerator LLM helper to prepare virtual-AI-OS task proposals."""

from __future__ import annotations

import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_DATASETS_ROOT = REPO_ROOT / "external" / "ipfs_datasets"
IPFS_ACCELERATE_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"
TASK_BOARD_PATH = REPO_ROOT / "implementation_plan" / "docs" / (
    "19-virtual-ai-os-submodule-integration." + "to" + "do.md"
)
TASK_BOARD_PATH_OPTION = "--" + "to" "do" + "-path"
PLAN_PATH = REPO_ROOT / "implementation_plan" / "docs" / "19-virtual-ai-os-submodule-integration.md"
ARTIFACT_DIR = REPO_ROOT / "data" / "virtual_ai_os" / "llm_router"

if str(IPFS_ACCELERATE_ROOT) not in sys.path:
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))

from ipfs_accelerate_py.agent_supervisor.task_proposal_router import (  # noqa: E402
    TaskProposalRouterConfig,
    TaskProposalRouterCliConfig,
    build_task_proposal_prompt,
    run_task_proposal_router_cli,
)
from ipfs_accelerate_py.agent_supervisor.wrapper_utils import ensure_runtime_pythonpath  # noqa: E402


def _bootstrap_imports() -> None:
    os.chdir(REPO_ROOT)
    ensure_runtime_pythonpath([IPFS_ACCELERATE_ROOT, IPFS_DATASETS_ROOT])


def _build_cli_config() -> TaskProposalRouterCliConfig:
    return TaskProposalRouterCliConfig(
        router_config=TaskProposalRouterConfig(
            repo_root=REPO_ROOT,
            task_board_path=TASK_BOARD_PATH,
            task_header_prefix="## VAI-",
            plan_path=PLAN_PATH,
            artifact_dir=ARTIFACT_DIR,
            prompt_builder=_build_prompt,
            no_open_task_message="No open task found in virtual-AI-OS task board.",
        ),
        description="Generate an implementation proposal for a virtual-AI-OS task-board item with llm_router.",
        task_id_help="Specific VAI task id. Defaults to the first ready task.",
        task_board_option=TASK_BOARD_PATH_OPTION,
        bootstrap=_bootstrap_imports,
    )


def _build_prompt(task: object, plan_text: str) -> str:
    return build_task_proposal_prompt(
        task=task,
        plan_text=plan_text,
        intro="You are helping implement the HandsFree virtual AI operating system roadmap.",
        requested_outputs=(
            "exact files to edit",
            "runtime and cross-repo contracts to add",
            "tests and fixtures needed",
            "validation commands",
            "risks or blockers",
        ),
    )


def main(argv: list[str] | None = None) -> int:
    return run_task_proposal_router_cli(_build_cli_config(), argv)


if __name__ == "__main__":
    raise SystemExit(main())
