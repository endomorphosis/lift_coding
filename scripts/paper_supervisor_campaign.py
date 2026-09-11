#!/usr/bin/env python3
"""Run three isolated native supervisors with Quack authority and DuckLake history.

Only the campaign process owns its children. A failed lane is reported, never
silently reset or switched to a file/Markdown authority. Use status to inspect
live Quack reads; source Markdown is a reviewed import, not a scheduling board.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
PAPERS = ("autoformalization", "law_to_action", "neurosymbolic_supervision")
SUBMODULES = ("external/ipfs_accelerate", "external/ipfs_datasets", "external/ipfs_kit")
PYTHON = Path.home() / "lift_coding/.venvs/ipfs-datasets-duckdb-quack/bin/python"
GROK_TEX_PROFILE = Path("papers/completion/toolchains/grok_tex_profile.json")


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, default=str) + "\n")
    temporary.chmod(0o600)
    os.replace(temporary, path)


def birth(pid):
    try:
        # comm can contain spaces and parentheses; starttime is field 22.
        tail = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        return None if tail[0] == "Z" else tail[19]
    except (OSError, IndexError, ValueError):
        return None


def boot_id():
    try:
        return Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    except OSError:
        return None


def process_record(pid):
    return {"pid": pid, "birth": birth(pid), "boot_id": boot_id()}


def alive(record):
    if not isinstance(record, dict) or not isinstance(record.get("pid"), int) or record["pid"] <= 0:
        return False
    return bool(record.get("birth") and birth(record["pid"]) == str(record["birth"])
                and (not record.get("boot_id") or record["boot_id"] == boot_id()))


def owner_process(ready):
    """Read the native owner's PID-reuse-resistant identity, never a guessed PID."""
    try:
        native = ready["identity"]["process_birth"]
        pid, ticks = int(native["pid"]), int(native["start_time_ticks"])
        if pid <= 0 or ticks <= 0 or not native.get("boot_id"):
            return None
        return {"pid": pid, "birth": str(ticks), "boot_id": native["boot_id"]}
    except (KeyError, TypeError, ValueError):
        return None


def prepare_owner_start(ready_path, paper):
    if not ready_path.exists():
        return
    old = read(ready_path)
    owner = owner_process(old)
    if alive(owner):
        raise RuntimeError(f"live owner already exists for {paper}")
    if old.get("ready") and owner is None:
        raise RuntimeError(f"cannot establish ownership of existing readiness for {paper}")
    ready_path.unlink()


def wait_owner_ready(process, record, ready_path, *, paper, database,
                     stopping=lambda: False, timeout=45):
    deadline = time.monotonic() + timeout
    while True:
        if process.poll() is not None or time.monotonic() >= deadline or stopping():
            raise RuntimeError(f"owner did not become ready: {paper}; inspect its owner.log")
        if ready_path.exists():
            ready = read(ready_path)
            native = owner_process(ready)
            if (native is None or native != {key: record.get(key) for key in ("pid", "birth", "boot_id")}
                    or not alive(native)):
                raise RuntimeError(f"readiness belongs to a different owner process: {paper}")
            if (ready.get("database") != str(database.resolve())
                    or ready.get("store_id") != "vericodegen-2026-" + paper):
                raise RuntimeError(f"owner readiness has the wrong database/store: {paper}")
            if not ready.get("ready"):
                raise RuntimeError(f"owner failed readiness: {paper}")
            return ready
        time.sleep(0.1)


def environment(repo):
    env = os.environ.copy()
    # Do not inherit another campaign's authority or task routing selection.
    for key in list(env):
        if key.startswith(("IPFS_ACCELERATE_AGENT_STATE_", "IPFS_ACCELERATE_AGENT_QUACK_",
                           "IPFS_ACCELERATE_AGENT_IMPLEMENTATION_ROUTE_")) or key == "IPFS_ACCELERATE_AGENT_DATABASE_PROGRAM_JSON":
            env.pop(key)
    env.update(PYTHONPATH=os.pathsep.join(str(repo / p) for p in SUBMODULES),
               IPFS_ACCEL_SKIP_CORE="1", IPFS_AUTO_INSTALL="false",
               IPFS_DATASETS_AUTO_INSTALL="false", PYTHONUNBUFFERED="1",
               # Complete native quota-only route requested by the user.
               # Real independent quota evidence remains mandatory; provider
               # errors or missing authentication do not authorize fallback.
               IPFS_ACCELERATE_AGENT_IMPLEMENTATION_PROVIDER="grok",
               IPFS_ACCELERATE_AGENT_GROK_MODEL="grok-4.6",
               IPFS_ACCELERATE_AGENT_IMPLEMENTATION_FALLBACK_PROVIDER="codex",
               IPFS_ACCELERATE_AGENT_CODEX_MODEL="gpt-5.6-terra",
               IPFS_ACCELERATE_AGENT_IMPLEMENTATION_FALLBACK_TRIGGER="primary_quota_exhausted",
               IPFS_ACCELERATE_AGENT_CODEX_REASONING_EFFORT="high",
               # The native Docker runner verifies the exact tree/launcher
               # hashes before mounting this formatting toolchain read-only.
               IPFS_ACCELERATE_AGENT_GROK_TEX_TOOLCHAIN_JSON=json.dumps(
                   read(repo / GROK_TEX_PROFILE), sort_keys=True, separators=(",", ":")),
               # Successful merged workspaces use native terminal cleanup.
               # Failure rescue and ownership checks remain native obligations.
               IPFS_ACCELERATE_AGENT_WORKTREE_POOL_ENABLED="false",
               IPFS_ACCELERATE_AGENT_WORKTREE_POOL_MAX_ENTRIES="1")
    return env


def repo_for(paper, worktree_parent):
    return worktree_parent / f"vericodegen-{paper}-2026"


def cfg(repo, paper):
    return read(repo / "papers/completion" / paper / "supervisor.json")


def token_for(ready, lane):
    handle = ready["endpoint_secret_handle"].replace(":", "_").replace("/", "_")
    path = lane / "quack-owner" / (handle + ".quack-token")
    if path.stat().st_mode & 0o077:
        raise RuntimeError("owner token permissions must be private")
    return path.read_text().strip()


def native_argv(repo, paper, lane, ready):
    config = cfg(repo, paper)
    argv = [str(PYTHON), "-P", "-m",
            "ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_supervisor",
            "--todo-path", str(lane / "control.duckdb"),
            "--task-prefix", config["task_prefix"], "--state-prefix", config["state_prefix"],
            "--state-dir", str(lane / "state"), "--worktree-root", str(lane / "worktrees"),
            "--merge-queue-dir", str(lane / "merge-queue"),
            "--merge-target-branch", f"agent/vericodegen-2026-{paper}",
            "--task-source-kind", "duckdb", "--authority-mode", "quack",
            "--quack-endpoint", ready["quack_endpoint"],
            "--endpoint-secret-handle", ready["endpoint_secret_handle"],
            "--state-store-id", ready["store_id"],
            "--state-store-generation", str(ready["store_generation"]),
            "--state-schema-revision", str(ready["schema_revision"]),
            "--state-failover-policy", "fail_closed", "--implement",
            "--max-task-attempts", "3", "--implementation-timeout", "7200",
            "--implementation-max-timeout", "7200", "--implementation-log-stall-seconds", "1800",
            "--daemon-interval", "30", "--check-interval", "30",
            "--implementation-retry-budget", "3", "--validation-retry-budget", "3",
            "--merge-retry-budget", "3", "--no-objective-goal-refinement",
            "--no-objective-goal-completion-reconcile", "--no-objective-goal-migration"]
    for path in SUBMODULES:
        argv.extend(["--worktree-submodule-path", path])
    protected = ["scripts/paper_supervisors.py", "scripts/paper_supervisor_campaign.py",
                 "scripts/materialize_paper_database.py", "scripts/paper_state_owner.py",
                 "scripts/paper_ducklake_projection.py", "scripts/paper_worker_observation.py",
                 "scripts/migrate_paper_validation_argv.py", "scripts/repair_paper_launch_validation.py",
                 "scripts/repair_paper_snapshot_outputs.py",
                 "papers/completion/README.md",
                 "papers/neurips_2026_vericode_workshop.tex", "papers/neurips_2026_vericode.sty", "papers/checklist.tex"]
    for other in PAPERS:
        config = cfg(repo, other)
        protected.extend([config[k] for k in ("pdf", "manifest_path", "review_path", "todo_path", "objective_path")])
        protected.append(f"papers/completion/{other}/supervisor.json")
    for path in protected:
        argv.extend(["--implementation-protected-path", path])
    return argv


def native_imports():
    for p in reversed(SUBMODULES):
        sys.path.insert(0, str(ROOT / p))
    os.environ.setdefault("IPFS_ACCEL_SKIP_CORE", "1")
    os.environ.setdefault("IPFS_AUTO_INSTALL", "false")
    from ipfs_accelerate_py.agent_supervisor.task_sources.duckdb_state import open_quack_transport_connection
    return open_quack_transport_connection


def fetch_board(paper, lane):
    ready = read(lane / "quack-owner/paper-owner.ready.json")
    open_connection = native_imports()
    conn = open_connection(ready["quack_endpoint"], token=token_for(ready, lane))
    try:
        conn.execute("BEGIN TRANSACTION")
        def records(sql):
            # The native cursor has no DB-API description; each row is a Mapping.
            return [dict(row.items()) for row in conn.execute(sql).fetchall()]
        metadata = {row[0]: row[1] for row in conn.execute("SELECT key, value FROM control_plane_metadata").fetchall()}
        identity = ready["identity"]
        if metadata.get("database_uuid") != identity["database_uuid"]:
            raise RuntimeError("remote database identity differs from ready owner")
        tasks = records("SELECT * FROM tasks ORDER BY ordinal, task_alias")
        goals = records("SELECT * FROM goals ORDER BY ordinal, goal_alias")
        events = records("SELECT * FROM domain_events ORDER BY global_sequence")
        conn.commit()
        return {"paper_id": paper, "board_namespace": "vericodegen-2026-" + paper,
                "store_identity": {"store_id": ready["store_id"], "database_uuid": identity["database_uuid"]},
                "store_generation": {"generation": ready["store_generation"]},
                "tasks": tasks, "goals": goals, "events": events}
    finally:
        conn.close()


def snapshot(state):
    return {"schema": "vericodegen-quack-snapshot/v1", "transport": "quack",
            "fetched_at": now(), "boards": [fetch_board(p, state / p) for p in PAPERS]}


def worker_observation(lane, authoritative_tasks=None):
    try:
        from paper_worker_observation import observe_lane
        return observe_lane(lane, authoritative_tasks=authoritative_tasks)
    except Exception as exc:
        # A transient private projection read must not suppress owner health.
        return {"authoritative": False, "error_type": type(exc).__name__}


def launch(argv, cwd, env, log):
    with log.open("a") as handle:
        process = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                   stdout=handle, stderr=subprocess.STDOUT, start_new_session=True)
    return process, {**process_record(process.pid), "log": str(log), "argv": argv}


def cleanup_children(children):
    failures = []
    if not children:
        return failures
    native_imports()
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_supervisor import terminate_pid_tree
    for kind, process, record in reversed(children):
        try:
            if process.poll() is None and alive(record):
                terminate_pid_tree(process.pid, grace_seconds=3.0, freeze_first=False, require_gone=True)
            if process.poll() is not None:
                process.wait(timeout=1)
            elif alive(record):
                failures.append({"kind": kind, "pid": process.pid, "error_type": "CleanupIncomplete"})
        except ProcessLookupError:
            pass
        except Exception as exc:
            # Continue cleaning other exact children even if one tree cannot be fenced.
            failures.append({"kind": kind, "pid": process.pid, "error_type": type(exc).__name__})
    return failures


def serve(state, worktree_parent):
    state.mkdir(parents=True, exist_ok=True)
    os.chmod(state, 0o700)
    lock = (state / "campaign.lock").open("a")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BaseException:
        lock.close()
        raise
    children = []
    report = {"schema": "vericodegen-campaign/v1", "started_at": now(),
              "controller": process_record(os.getpid()),
              "authority": "duckdb-through-quack", "history": "ducklake", "lanes": {}}
    stopping = False
    def stop(_signum, _frame):
        nonlocal stopping
        stopping = True
    previous_signals = {sig: signal.signal(sig, stop) for sig in (signal.SIGTERM, signal.SIGINT)}
    try:
        # Verify every lane before starting owners/providers.
        for paper in PAPERS:
            repo = repo_for(paper, worktree_parent)
            branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=repo, text=True).strip()
            if branch != f"agent/vericodegen-2026-{paper}":
                raise RuntimeError(f"wrong integration branch for {paper}")
            dirty = subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=normal"], cwd=repo, text=True)
            if dirty.strip():
                raise RuntimeError(f"lane integration tree has uncommitted changes: {paper}")
            for path in ("papers", "scripts/paper_supervisors.py", "scripts/paper_state_owner.py",
                         "scripts/materialize_paper_database.py", "scripts/paper_supervisor_campaign.py",
                         "scripts/paper_ducklake_projection.py", "scripts/paper_worker_observation.py"):
                if not subprocess.check_output(["git", "ls-files", "--", path], cwd=repo, text=True).strip():
                    raise RuntimeError(f"uncommitted campaign source {path}")
        for paper in PAPERS:
            if stopping:
                raise RuntimeError("campaign startup was stopped")
            repo, lane = repo_for(paper, worktree_parent), state / paper
            lane.mkdir(parents=True, exist_ok=True)
            database = lane / "control.duckdb"
            if not database.exists():
                subprocess.run([str(PYTHON), str(repo / "scripts/materialize_paper_database.py"),
                                "--paper", paper, "--database", str(database)], cwd=repo,
                               env=environment(repo), check=True, stdout=subprocess.DEVNULL)
            elif not database.with_name(database.name + ".bootstrap.json").exists():
                raise RuntimeError(f"existing store has no campaign bootstrap provenance: {paper}")
            ready_path = lane / "quack-owner/paper-owner.ready.json"
            prepare_owner_start(ready_path, paper)
            argv = [str(PYTHON), str(repo / "scripts/paper_state_owner.py"), "--database", str(database),
                    "--state-dir", str(lane / "quack-owner"), "--store-id", "vericodegen-2026-" + paper,
                    "--secret-handle", "handle:vericodegen-2026:" + paper]
            process, record = launch(argv, repo, environment(repo), lane / "owner.log")
            children.append(("owner", process, record))
            report["lanes"][paper] = {"repo": str(repo), "owner": record}
            write(state / "campaign.json", report)
            wait_owner_ready(process, record, ready_path, paper=paper, database=database,
                             stopping=lambda: stopping)
            fetch_board(paper, lane)  # independent real remote authenticated read
        # Establish actual DuckLake projection before implementations begin.
        from paper_ducklake_projection import project_snapshot
        snap = snapshot(state)
        write(state / "quack-snapshot.json", snap)
        lake = project_snapshot(snap, state / "ducklake", repo_root=ROOT, source_path=state / "quack-snapshot.json")
        write(state / "ducklake-status.json", lake)
        for paper in PAPERS:
            if stopping:
                raise RuntimeError("campaign startup was stopped")
            lane, repo = state / paper, repo_for(paper, worktree_parent)
            ready = read(lane / "quack-owner/paper-owner.ready.json")
            env = environment(repo)
            env["IPFS_ACCELERATE_AGENT_QUACK_TOKEN"] = token_for(ready, lane)
            process, record = launch(native_argv(repo, paper, lane, ready), repo, env, lane / "supervisor.log")
            children.append(("supervisor", process, record))
            report["lanes"][paper]["supervisor"] = record
            write(state / "campaign.json", report)
        while not stopping:
            failures = [dict(kind=kind, pid=p.pid, exit_code=p.returncode) for kind, p, _record in children if p.poll() is not None]
            health = {"checked_at": now(), "children_exited": failures}
            try:
                snap = snapshot(state)
                health["workers"] = {b["paper_id"]: worker_observation(
                    state / b["paper_id"], authoritative_tasks=b["tasks"]) for b in snap["boards"]}
                write(state / "quack-snapshot.json", snap)
                lake = project_snapshot(snap, state / "ducklake", repo_root=ROOT, source_path=state / "quack-snapshot.json")
                write(state / "ducklake-status.json", lake)
                health["tasks"] = {b["paper_id"]: dict(Counter(t["status"] for t in b["tasks"])) for b in snap["boards"]}
                health["quack_reads_succeeded"] = True
            except Exception as exc:
                health.update(quack_reads_succeeded=False, error_type=type(exc).__name__)
                if "workers" not in health:
                    health["workers"] = {paper: worker_observation(state / paper) for paper in PAPERS}
            write(state / "health.json", health)
            print(json.dumps(health), flush=True)
            for _ in range(30):
                if stopping:
                    break
                time.sleep(1)
    finally:
        # Only exact children are stopped; no fleet-wide process matching.
        try:
            report["cleanup_errors"] = cleanup_children(children)
            report["stopped_at"] = now()
            write(state / "campaign.json", report)
        finally:
            for sig, handler in previous_signals.items():
                signal.signal(sig, handler)
            lock.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("start", "serve", "status", "stop"))
    parser.add_argument("--state-root", type=Path, default=Path.home() / ".local/state/ipfs_accelerate_py/vericodegen-2026")
    parser.add_argument("--worktree-parent", type=Path, default=ROOT / ".worktrees")
    args = parser.parse_args()
    state = args.state_root.expanduser().resolve()
    if args.action == "serve":
        serve(state, args.worktree_parent.resolve())
    elif args.action == "start":
        state.mkdir(parents=True, exist_ok=True)
        prior = read(state / "campaign.json") if (state / "campaign.json").exists() else {}
        if alive(prior.get("controller")):
            raise RuntimeError("campaign controller is already running")
        argv = [str(PYTHON), str(Path(__file__).resolve()), "serve", "--state-root", str(state),
                "--worktree-parent", str(args.worktree_parent.resolve())]
        process, record = launch(argv, ROOT, environment(ROOT), state / "campaign.log")
        print(json.dumps({"controller": record, "status": "starting", "state_root": str(state)}, indent=2))
    elif args.action == "stop":
        report = read(state / "campaign.json")
        controller = report.get("controller")
        if alive(controller):
            os.kill(controller["pid"], signal.SIGTERM)
            print("Stop requested for this campaign and its owned children.")
        else:
            print("Campaign controller is not running.")
    else:
        report = read(state / "campaign.json")
        result = {"controller_alive": alive(report.get("controller")), "lanes": {}}
        for paper, lane_report in report["lanes"].items():
            lane = state / paper
            item = {"owner_alive": alive(lane_report.get("owner")),
                    "supervisor_alive": alive(lane_report.get("supervisor")), "repo": lane_report["repo"]}
            try:
                board = fetch_board(paper, lane)
                item["workers"] = worker_observation(lane, authoritative_tasks=board["tasks"])
                item.update(quack_read=True, tasks=dict(Counter(t["status"] for t in board["tasks"])),
                            active_tasks=[t["task_alias"] for t in board["tasks"] if t["status"] not in {"ready", "open", "todo"}],
                            events=len(board["events"]))
            except Exception as exc:
                item.update(quack_read=False, error_type=type(exc).__name__)
                if "workers" not in item:
                    item["workers"] = worker_observation(lane)
            result["lanes"][paper] = item
        result["ducklake"] = read(state / "ducklake-status.json") if (state / "ducklake-status.json").exists() else None
        print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
