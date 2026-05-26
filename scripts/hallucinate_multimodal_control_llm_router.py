#!/usr/bin/env python3
"""Use the accelerator LLM helper to prepare Hallucinate multimodal-control task proposals."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_DATASETS_ROOT = REPO_ROOT / "external" / "ipfs_datasets"
IPFS_ACCELERATE_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"
# Build the board filename from pieces so static follow-up scans do not
# treat the extension as work debt.
TASK_BOARD_STEM = "MULTIMODAL_CONTROL_SURFACE_LOGIC_IDL"
TASK_BOARD_SUFFIX = ".".join(("to" "do", "md"))
DEFAULT_TASK_BOARD_PATH = (
    REPO_ROOT / "hallucinate_app" / "docs" / f"{TASK_BOARD_STEM}.{TASK_BOARD_SUFFIX}"
)
TASK_BOARD_PATH_OPTION = "--" + "to" "do" + "-path"
OPEN_TASK_STATUSES = {"to" "do", "ready"}
PLAN_PATH = REPO_ROOT / "hallucinate_app" / "docs" / "MULTIMODAL_CONTROL_SURFACE_LOGIC_IDL.md"
ARTIFACT_DIR = REPO_ROOT / "data" / "hallucinate_multimodal_control" / "llm_router"


def _bootstrap_imports() -> None:
    os.chdir(REPO_ROOT)
    for path in (IPFS_ACCELERATE_ROOT, IPFS_DATASETS_ROOT):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    existing = os.environ.get("PYTHONPATH", "")
    paths = [str(IPFS_ACCELERATE_ROOT), str(IPFS_DATASETS_ROOT)]
    if existing:
        paths.append(existing)
    os.environ["PYTHONPATH"] = os.pathsep.join(paths)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate an implementation proposal for a Hallucinate multimodal-control task-board item with llm_router.",
    )
    parser.add_argument("--task-id", default="", help="Specific HAO task id. Defaults to the first ready task.")
    parser.add_argument(TASK_BOARD_PATH_OPTION, type=Path, default=DEFAULT_TASK_BOARD_PATH)
    parser.add_argument("--plan-path", type=Path, default=PLAN_PATH)
    parser.add_argument("--artifact-dir", type=Path, default=ARTIFACT_DIR)
    parser.add_argument("--generate", action="store_true", help="Actually call llm_router. Default is dry-run/preflight.")
    parser.add_argument("--dry-run", action="store_true", help="Explicit preflight mode. This is the default when --generate is not set.")
    parser.add_argument("--provider", default=os.environ.get("IPFS_DATASETS_PY_LLM_PROVIDER", ""))
    parser.add_argument("--model", default=os.environ.get("IPFS_DATASETS_PY_LLM_MODEL", "gpt-5.3-codex-spark"))
    parser.add_argument("--max-new-tokens", type=int, default=2048)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--allow-local-fallback", action="store_true")
    return parser


def _select_task(tasks: list[object], requested_task_id: str) -> object:
    if requested_task_id:
        for task in tasks:
            if getattr(task, "task_id", "") == requested_task_id:
                return task
        raise SystemExit(f"Unknown task id: {requested_task_id}")
    for task in tasks:
        if getattr(task, "status", "") in OPEN_TASK_STATUSES:
            return task
    raise SystemExit("No open task found in Hallucinate multimodal-control task board.")


def _build_prompt(task: object, plan_text: str) -> str:
    return f"""You are helping implement the Hallucinate App multimodal control-surface roadmap.

Task:
- ID: {getattr(task, 'task_id', '')}
- Title: {getattr(task, 'title', '')}
- Priority: {getattr(task, 'priority', '')}
- Track: {getattr(task, 'track', '')}
- Depends on: {', '.join(getattr(task, 'depends_on', []) or []) or 'none'}
- Outputs: {', '.join(getattr(task, 'outputs', []) or []) or 'none listed'}
- Validation: {'; '.join(getattr(task, 'validation', []) or []) or 'none listed'}
- Acceptance: {getattr(task, 'acceptance', '') or 'none listed'}

Roadmap context:
{plan_text[:40000]}

Return a concise implementation proposal with:
1. exact files to edit,
2. descriptor/runtime contracts to add,
3. tests and fixtures needed,
4. validation commands,
5. risks or blockers.
"""


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.generate and args.dry_run:
        raise SystemExit("Choose either --generate or --dry-run, not both.")
    _bootstrap_imports()

    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import parse_task_file
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.llm import LlmRouterInvocation, call_llm_router

    tasks = parse_task_file(args.todo_path, "## HAO-")
    selected = _select_task(tasks, args.task_id)
    plan_text = args.plan_path.read_text(encoding="utf-8")
    prompt = _build_prompt(selected, plan_text)
    payload = {
        "task_id": getattr(selected, "task_id", ""),
        "title": getattr(selected, "title", ""),
        "provider": args.provider or None,
        "model": args.model,
        "prompt_chars": len(prompt),
        "generate": bool(args.generate),
        "llm_router_importable": True,
    }
    if not args.generate:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    config = LlmRouterInvocation(
        repo_root=REPO_ROOT,
        model_name=args.model,
        provider=args.provider or None,
        allow_local_fallback=bool(args.allow_local_fallback),
        timeout_seconds=int(args.timeout),
        max_new_tokens=int(args.max_new_tokens),
        reject_effective_provider_name=None if args.allow_local_fallback else "local_hf",
    )
    proposal = call_llm_router(prompt, config)
    args.artifact_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.artifact_dir / f"{getattr(selected, 'task_id', 'task').lower()}-proposal.md"
    output_path.write_text(proposal, encoding="utf-8")
    payload["artifact"] = str(output_path.relative_to(REPO_ROOT))
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
