"""Empirical probe: can the prompt-lifecycle facade tools open a Supervisor
in this environment, create a run, and steer it? Run with the lift_coding
venv, PYTHONPATH=external/ipfs_accelerate, cwd=lift_coding root."""
import asyncio
import importlib.util  # noqa: F401  (agent_supervisor lazy loader assumes it)
import json
import os
import sys

from ipfs_accelerate_py.mcp_server.tools.agent_supervisor_tools.prompt_entrypoints import (
    agent_supervisor_run,
    agent_supervisor_status,
    agent_supervisor_steer,
)


async def main() -> None:
    out: dict = {}
    out["status_no_run"] = await agent_supervisor_status()
    run = await agent_supervisor_run(
        prompt="Steering-route probe: keep the lift_coding supervisor verification backlog moving.",
    )
    out["run"] = run
    run_id = None
    if isinstance(run, dict) and run.get("ok"):
        run_id = run["result"].get("run_id")
    out["run_id"] = run_id
    if run_id:
        out["status_after_run"] = await agent_supervisor_status(run_id=run_id)
        out["steer"] = await agent_supervisor_steer(
            prompt="Prioritize the steering verification task and keep all other scope unchanged.",
            run_id=run_id,
        )
        out["status_after_steer"] = await agent_supervisor_status(run_id=run_id)
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
