#!/usr/bin/env python3
"""Snapshot the three paper boards and restart a dead campaign controller.

Native Quack status is authoritative. Markdown todo files are import sources.
This script never marks a scientific task complete. It only records blockers
and restarts the campaign when the controller is dead or the Law owner is dead
while work remains. Unreadable Quack boards are not treated as complete.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
STATE = Path.home() / ".local/state/ipfs_accelerate_py/vericodegen-2026"
JOURNAL = ROOT / "papers/completion/watchdog"
CAMPAIGN = ROOT / "scripts/paper_supervisor_campaign.py"
PAPERS = ("autoformalization", "law_to_action", "neurosymbolic_supervision")


def now():
    return datetime.now(timezone.utc).isoformat()


def run_status():
    process = subprocess.run([sys.executable, str(CAMPAIGN), "status"], cwd=ROOT,
                             capture_output=True, text=True, timeout=120)
    if process.returncode != 0:
        return {"ok": False, "returncode": process.returncode,
                "stderr": (process.stderr or "")[-4000:], "stdout": (process.stdout or "")[-1000:]}
    return {"ok": True, "status": json.loads(process.stdout)}


def remaining(lane):
    if lane.get("quack_read") is not True:
        return None
    tasks = lane.get("tasks") or {}
    return sum(count for status, count in tasks.items() if status != "completed")


def snapshot():
    observed = run_status()
    payload = {"schema": "vericodegen-paper-board-watchdog/v1", "observed_at": now(),
               "cwd": str(ROOT), "state_root": str(STATE), "campaign_status": observed}
    if not observed.get("ok"):
        payload["action"] = "campaign_status_failed"
        return payload
    status = observed["status"]
    lanes = {}
    work_remaining = False
    for paper in PAPERS:
        lane = (status.get("lanes") or {}).get(paper) or {}
        left = remaining(lane)
        work_remaining = work_remaining or left is None or left > 0
        progress = lane.get("progress") or {}
        lanes[paper] = {
            "owner_alive": lane.get("owner_alive"),
            "supervisor_alive": lane.get("supervisor_alive"),
            "quack_read": lane.get("quack_read"),
            "tasks": lane.get("tasks"),
            "remaining_noncomplete": left,
            "state": progress.get("state"),
            "in_progress": progress.get("in_progress") or [],
            "eligible_candidates": progress.get("eligible_candidates") or [],
            "blocked": progress.get("blocked") or [],
            "waiting": progress.get("waiting") or [],
        }
    payload["lanes"] = lanes
    payload["controller_alive"] = status.get("controller_alive")
    # Unreadable Quack boards are not complete; a dead owner must not look like 0 remaining.
    payload["boards_complete"] = all(row.get("quack_read") is True and row["remaining_noncomplete"] == 0
                                     for row in lanes.values())
    payload["work_remaining"] = work_remaining
    law = lanes.get("law_to_action") or {}
    adopt = STATE / "adopt_live_controller.py"
    python = Path.home() / "lift_coding/.venvs/ipfs-datasets-duckdb-quack/bin/python"
    af_ns_live = all((lanes.get(name) or {}).get("owner_alive")
                     for name in ("autoformalization", "neurosymbolic_supervision"))
    if payload["boards_complete"]:
        payload["action"] = "all_native_boards_complete"
    elif not status.get("controller_alive") and work_remaining and af_ns_live and adopt.exists():
        with (STATE / "campaign.log").open("a") as handle:
            process = subprocess.Popen([str(python), str(adopt)], cwd=ROOT, stdin=subprocess.DEVNULL,
                                       stdout=handle, stderr=subprocess.STDOUT, start_new_session=True)
        payload["action"] = "adopted_live_af_ns_orphans"
        payload["restart"] = {"pid": process.pid, "adopt": str(adopt)}
    elif not status.get("controller_alive") and work_remaining:
        start = subprocess.run([sys.executable, str(CAMPAIGN), "start"], cwd=ROOT,
                               capture_output=True, text=True, timeout=60)
        payload["action"] = "restarted_dead_campaign_controller"
        payload["restart"] = {"returncode": start.returncode, "stdout": (start.stdout or "")[-2000:],
                              "stderr": (start.stderr or "")[-2000:]}
    elif not law.get("owner_alive") and work_remaining:
        prior_pid = None
        campaign_record = STATE / "campaign.json"
        if campaign_record.exists():
            prior_pid = (json.loads(campaign_record.read_text()).get("controller") or {}).get("pid")
        stop = subprocess.run([sys.executable, str(CAMPAIGN), "stop"], cwd=ROOT,
                              capture_output=True, text=True, timeout=60)
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if not isinstance(prior_pid, int) or not Path(f"/proc/{prior_pid}").exists():
                break
            time.sleep(1)
        if af_ns_live and adopt.exists():
            with (STATE / "campaign.log").open("a") as handle:
                process = subprocess.Popen([str(python), str(adopt)], cwd=ROOT, stdin=subprocess.DEVNULL,
                                           stdout=handle, stderr=subprocess.STDOUT, start_new_session=True)
            payload["action"] = "restarted_dead_law_owner_through_adopt"
            payload["restart"] = {"stop_returncode": stop.returncode, "pid": process.pid,
                                  "prior_controller_pid": prior_pid, "adopt": str(adopt)}
        else:
            start = subprocess.run([sys.executable, str(CAMPAIGN), "start"], cwd=ROOT,
                                   capture_output=True, text=True, timeout=60)
            payload["action"] = "restarted_dead_law_owner_through_campaign"
            payload["restart"] = {"stop_returncode": stop.returncode, "returncode": start.returncode,
                                  "prior_controller_pid": prior_pid,
                                  "stdout": (start.stdout or "")[-2000:], "stderr": (start.stderr or "")[-2000:]}
    else:
        payload["action"] = "inspect_and_unblock"
    return payload


def main():
    JOURNAL.mkdir(parents=True, exist_ok=True)
    payload = snapshot()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    latest = JOURNAL / "latest.json"
    record = JOURNAL / f"observation-{stamp}.json"
    record.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    latest.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    with (JOURNAL / "journal.jsonl").open("a") as stream:
        stream.write(json.dumps({"observed_at": payload["observed_at"], "action": payload.get("action"),
                                 "controller_alive": payload.get("controller_alive"),
                                 "boards_complete": payload.get("boards_complete"),
                                 "lanes": {name: {"tasks": row.get("tasks"), "state": row.get("state"),
                                                  "blocked": row.get("blocked")}
                                           for name, row in (payload.get("lanes") or {}).items()}}) + "\n")
    print(json.dumps({"observed_at": payload["observed_at"], "action": payload.get("action"),
                      "controller_alive": payload.get("controller_alive"),
                      "boards_complete": payload.get("boards_complete"),
                      "lanes": {name: {"tasks": row.get("tasks"), "state": row.get("state"),
                                       "blocked": [item.get("task") for item in row.get("blocked") or []]}
                                for name, row in (payload.get("lanes") or {}).items()},
                      "latest": str(latest)}, indent=2, sort_keys=True))
    return 0 if payload.get("campaign_status", {}).get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
