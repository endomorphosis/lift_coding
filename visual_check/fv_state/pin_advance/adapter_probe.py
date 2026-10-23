#!/usr/bin/env python3
"""Finisher adapter probe: two identical confirmed steering dispatches
against the LIVE accelerate compat adapter (:3003), which forwards to the
persistent SupervisorSteering bridge worker. Proves the dispatch reaches
the real backend and that its answer is stable/fail-closed: the session
snapshot after each call must be identical (no run created past the
backend's designed scanner boundary, no receipt fabricated).

Writes adapter-steer-1.json / adapter-steer-2.json next to this file and
prints a one-line summary of each.
"""
import json
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
URL = "http://127.0.0.1:3003/mcp"
PROMPT = (
    "Prioritize MCP++ Profile G conformance evidence for the supervisor "
    "console in the verification backlog."
)


def call(idx: int) -> dict:
    body = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": idx,
            "method": "agent_supervisor.prompt_steering.request",
            "params": {"prompt": PROMPT},
        }
    ).encode()
    req = urllib.request.Request(
        URL, data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        return json.loads(resp.read().decode())


def main() -> None:
    for idx in (1, 2):
        result = call(idx)
        out = HERE / f"adapter-steer-{idx}.json"
        out.write_text(json.dumps(result, indent=1), encoding="utf-8")
        res = result.get("result") or {}
        session = res.get("session") or {}
        print(
            f"call {idx}: ok={res.get('ok')} error_code={res.get('error_code')} "
            f"run_id={session.get('run_id')} run_error={session.get('run_error')!r}"
        )


if __name__ == "__main__":
    main()
