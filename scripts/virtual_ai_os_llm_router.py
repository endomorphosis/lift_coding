#!/usr/bin/env python3
"""Use the accelerator LLM helper to prepare virtual-AI-OS task proposals."""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_DATASETS_ROOT = REPO_ROOT / "external" / "ipfs_datasets"
IPFS_ACCELERATE_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"

if str(IPFS_ACCELERATE_ROOT) not in sys.path:
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))

from ipfs_accelerate_py.agent_supervisor.wrapper_utils import (  # noqa: E402
    build_runtime_environment_callbacks,
    task_board_filename as _task_board_filename,
    task_board_path_option as _task_board_path_option,
)

TASK_BOARD_PATH = REPO_ROOT / "implementation_plan" / "docs" / (
    _task_board_filename("19-virtual-ai-os-submodule-integration")
)
TASK_BOARD_PATH_OPTION = _task_board_path_option()
PLAN_PATH = REPO_ROOT / "implementation_plan" / "docs" / "19-virtual-ai-os-submodule-integration.md"
ARTIFACT_DIR = REPO_ROOT / "data" / "virtual_ai_os" / "llm_router"

from ipfs_accelerate_py.agent_supervisor.task_proposal_router import (  # noqa: E402
    build_configured_task_proposal_router_runner,
)


_RUNTIME_ENVIRONMENT = build_runtime_environment_callbacks(REPO_ROOT, (IPFS_ACCELERATE_ROOT, IPFS_DATASETS_ROOT))
_bootstrap_imports = _RUNTIME_ENVIRONMENT.enter
TASK_PROPOSAL_RUNNER = build_configured_task_proposal_router_runner(
    repo_root=REPO_ROOT,
    task_board_path=TASK_BOARD_PATH,
    task_header_prefix="## VAI-",
    plan_path=PLAN_PATH,
    artifact_dir=ARTIFACT_DIR,
    prompt_intro="You are helping implement the HandsFree virtual AI operating system roadmap.",
    requested_outputs=(
        "exact files to edit",
        "runtime and cross-repo contracts to add",
        "tests and fixtures needed",
        "validation commands",
        "risks or blockers",
    ),
    no_open_task_message="No open task found in virtual-AI-OS task board.",
    description="Generate an implementation proposal for a virtual-AI-OS task-board item with llm_router.",
    task_id_help="Specific VAI task id. Defaults to the first ready task.",
    task_board_option=TASK_BOARD_PATH_OPTION,
    bootstrap=_bootstrap_imports,
)


def main(argv: list[str] | None = None) -> int:
    return TASK_PROPOSAL_RUNNER.run(argv)


if __name__ == "__main__":
    raise SystemExit(main())
