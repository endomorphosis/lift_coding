#!/usr/bin/env python3
"""Use the accelerator LLM helper to prepare Hallucinate multimodal-control task proposals."""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_ACCELERATE_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"

if str(IPFS_ACCELERATE_ROOT) not in sys.path:
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))

from ipfs_accelerate_py.agent_supervisor.wrapper_utils import (  # noqa: E402
    task_board_path_option as _task_board_path_option,
)

from ipfs_accelerate_py.agent_supervisor.task_proposal_router import (  # noqa: E402
    build_repo_task_proposal_router_runner,
    build_task_proposal_route_paths,
    standard_task_proposal_requested_outputs,
)
HALLUCINATE_ROUTE_PATHS = build_task_proposal_route_paths(
    repo_root=REPO_ROOT,
    task_board_stem="MULTIMODAL_CONTROL_SURFACE_LOGIC_IDL",
    task_board_dir="hallucinate_app/docs",
    artifact_namespace="hallucinate_multimodal_control",
)
DEFAULT_TASK_BOARD_PATH = HALLUCINATE_ROUTE_PATHS.task_board_path
TASK_BOARD_PATH_OPTION = _task_board_path_option()
PLAN_PATH = HALLUCINATE_ROUTE_PATHS.plan_path
ARTIFACT_DIR = HALLUCINATE_ROUTE_PATHS.artifact_dir


TASK_PROPOSAL_RUNNER = build_repo_task_proposal_router_runner(
    repo_root=REPO_ROOT,
    task_board_path=DEFAULT_TASK_BOARD_PATH,
    task_header_prefix="## HAO-",
    plan_path=PLAN_PATH,
    artifact_dir=ARTIFACT_DIR,
    prompt_intro="You are helping implement the Hallucinate App multimodal control-surface roadmap.",
    requested_outputs=standard_task_proposal_requested_outputs(
        "descriptor/runtime contracts to add",
    ),
    no_open_task_message="No open task found in Hallucinate multimodal-control task board.",
    description=(
        "Generate an implementation proposal for a Hallucinate multimodal-control "
        "task-board item with llm_router."
    ),
    task_id_help="Specific HAO task id. Defaults to the first ready task.",
    task_board_option=TASK_BOARD_PATH_OPTION,
    include_dry_run_flag=True,
)


def main(argv: list[str] | None = None) -> int:
    return TASK_PROPOSAL_RUNNER.run(argv)


if __name__ == "__main__":
    raise SystemExit(main())
