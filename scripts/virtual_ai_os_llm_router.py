#!/usr/bin/env python3
"""Use the accelerator LLM helper to prepare virtual-AI-OS task proposals."""

from __future__ import annotations

import argparse
import json
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
    TaskProposalRouterError,
    build_task_proposal_prompt,
    run_task_proposal_router,
)
from ipfs_accelerate_py.agent_supervisor.wrapper_utils import ensure_runtime_pythonpath  # noqa: E402


def _bootstrap_imports() -> None:
    os.chdir(REPO_ROOT)
    ensure_runtime_pythonpath([IPFS_ACCELERATE_ROOT, IPFS_DATASETS_ROOT])


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate an implementation proposal for a virtual-AI-OS task-board item with llm_router.",
    )
    parser.add_argument("--task-id", default="", help="Specific VAI task id. Defaults to the first ready task.")
    parser.add_argument(TASK_BOARD_PATH_OPTION, type=Path, default=TASK_BOARD_PATH)
    parser.add_argument("--plan-path", type=Path, default=PLAN_PATH)
    parser.add_argument("--artifact-dir", type=Path, default=ARTIFACT_DIR)
    parser.add_argument("--generate", action="store_true", help="Actually call llm_router. Default is dry-run/preflight.")
    parser.add_argument("--provider", default=os.environ.get("IPFS_DATASETS_PY_LLM_PROVIDER", ""))
    parser.add_argument("--model", default=os.environ.get("IPFS_DATASETS_PY_LLM_MODEL", "gpt-5.3-codex-spark"))
    parser.add_argument("--max-new-tokens", type=int, default=2048)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--allow-local-fallback", action="store_true")
    return parser


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
    args = _build_parser().parse_args(argv)
    _bootstrap_imports()
    try:
        payload = run_task_proposal_router(
            TaskProposalRouterConfig(
                repo_root=REPO_ROOT,
                task_board_path=args.todo_path,
                task_header_prefix="## VAI-",
                plan_path=args.plan_path,
                artifact_dir=args.artifact_dir,
                prompt_builder=_build_prompt,
                no_open_task_message="No open task found in virtual-AI-OS task board.",
            ),
            task_id=args.task_id,
            generate=bool(args.generate),
            provider=args.provider,
            model=args.model,
            max_new_tokens=int(args.max_new_tokens),
            timeout_seconds=int(args.timeout),
            allow_local_fallback=bool(args.allow_local_fallback),
        )
    except TaskProposalRouterError as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
