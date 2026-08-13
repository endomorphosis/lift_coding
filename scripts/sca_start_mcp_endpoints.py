#!/usr/bin/env python3
"""Start live package MCP HTTP endpoints for SCA interop + symbolic repair.

Default ports (override with env / flags):

* accelerate  — 8000  (``IPFS_ACCELERATE_MCP_URL``)
* datasets    — 3002  (``IPFS_DATASETS_MCP_URL``)
* kit         — 8004  (``IPFS_KIT_MCP_URL``)

Each server is launched as a background subprocess with PYTHONPATH pinned to
this repo's ``external/`` checkouts so the wrong site-packages tree is not used.

Usage:
  python3 scripts/sca_start_mcp_endpoints.py [--no-kit] [--no-datasets] [--no-accelerate]
  python3 scripts/sca_start_mcp_endpoints.py --status
  python3 scripts/sca_start_mcp_endpoints.py --stop
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
SCA = REPO / "data" / "agent_supervisor" / "swissknife_contract_assurance"
STATE_DIR = SCA / "evaluation" / "mcp_endpoints"
STATE_FILE = STATE_DIR / "endpoints.json"
ENV_FILE = STATE_DIR / "endpoints.env"
LOG_DIR = STATE_DIR / "logs"

DEFAULTS = {
    "ipfs_accelerate_py": {
        "port": 8000,
        "env_key": "IPFS_ACCELERATE_MCP_URL",
        "health_paths": ("/mcp", "/mcp/tools/list", "/docs", "/"),
    },
    "ipfs_datasets_py": {
        "port": 3002,
        "env_key": "IPFS_DATASETS_MCP_URL",
        "health_paths": ("/mcp", "/mcp/tools/list", "/docs", "/"),
    },
    "ipfs_kit_py": {
        "port": 8004,
        "env_key": "IPFS_KIT_MCP_URL",
        "health_paths": ("/mcp", "/api", "/docs", "/"),
    },
}


def _pythonpath() -> str:
    parts = [
        str(REPO / "external" / "ipfs_accelerate"),
        str(REPO / "external" / "ipfs_datasets"),
        str(REPO / "external" / "ipfs_kit"),
        str(REPO / "Mcp-Plus-Plus"),
        os.environ.get("PYTHONPATH", ""),
    ]
    return os.pathsep.join(p for p in parts if p)


def _url(port: int) -> str:
    return f"http://127.0.0.1:{int(port)}"


def _probe(url: str, paths: tuple[str, ...] = ("/",)) -> dict[str, Any]:
    last = "no_paths"
    for path in paths:
        target = url.rstrip("/") + path
        try:
            req = urllib.request.Request(target, method="GET")
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                return {
                    "ok": True,
                    "path": path,
                    "status": getattr(resp, "status", 200),
                    "url": target,
                }
        except Exception as exc:  # noqa: BLE001
            last = f"{type(exc).__name__}: {exc}"
    # JSON-RPC tools/list probe
    for path in ("/mcp", "/mcp/"):
        target = url.rstrip("/") + path
        payload = json.dumps(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        ).encode()
        try:
            req = urllib.request.Request(
                target,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                data = json.loads(body) if body else {}
                tools = (
                    (data.get("result") or {}).get("tools")
                    if isinstance(data, dict)
                    else None
                )
                return {
                    "ok": True,
                    "path": path,
                    "status": getattr(resp, "status", 200),
                    "url": target,
                    "tool_count": len(tools) if isinstance(tools, list) else None,
                    "jsonrpc": True,
                }
        except Exception as exc:  # noqa: BLE001
            last = f"{type(exc).__name__}: {exc}"
    return {"ok": False, "error": last, "url": url}


def _load_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return {"servers": {}}
    return json.loads(STATE_FILE.read_text(encoding="utf-8"))


def _save_state(state: dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    STATE_FILE.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
    # Write shell-sourceable env
    lines = [
        f"# Generated {state['updated_at']} by sca_start_mcp_endpoints.py",
        "export PYTHONPATH=" + json.dumps(_pythonpath()),
    ]
    for pkg, meta in (state.get("servers") or {}).items():
        if meta.get("url") and meta.get("running"):
            env_key = DEFAULTS[pkg]["env_key"]
            lines.append(f"export {env_key}={meta['url']}")
    ENV_FILE.write_text("\n".join(lines) + "\n")


def _pid_alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(int(pid), 0)
        return True
    except OSError:
        return False


def _stop_all(state: dict[str, Any]) -> dict[str, Any]:
    for pkg, meta in list((state.get("servers") or {}).items()):
        pid = meta.get("pid")
        if _pid_alive(pid):
            try:
                os.kill(int(pid), signal.SIGTERM)
            except OSError:
                pass
        meta["running"] = False
        meta["stopped_at"] = datetime.now(timezone.utc).isoformat()
    # Wait briefly
    time.sleep(1.0)
    for pkg, meta in list((state.get("servers") or {}).items()):
        pid = meta.get("pid")
        if _pid_alive(pid):
            try:
                os.kill(int(pid), signal.SIGKILL)
            except OSError:
                pass
            meta["running"] = False
    _save_state(state)
    return state


def _cmd_for(package: str, port: int) -> list[str]:
    py = sys.executable
    if package == "ipfs_accelerate_py":
        return [
            py,
            "-c",
            (
                "from ipfs_accelerate_py.mcp_server.fastapi_service import "
                "create_fastapi_app, run_standalone_app, UnifiedFastAPIConfig; "
                f"cfg=UnifiedFastAPIConfig(host='127.0.0.1', port={port}); "
                "app=create_fastapi_app(cfg); "
                f"run_standalone_app(app, host='127.0.0.1', port={port})"
            ),
        ]
    if package == "ipfs_datasets_py":
        return [
            py,
            "-m",
            "ipfs_datasets_py.mcp_server",
            "--http",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ]
    if package == "ipfs_kit_py":
        # Prefer the MCP++ Hypercorn HTTP transport (stdio UnifiedMCPServer
        # harness does not wire HTTP). Module: ipfs_kit_py.mcp_server.server
        return [
            py,
            "-m",
            "ipfs_kit_py.mcp_server.server",
            "--transport",
            "http",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ]
    raise ValueError(package)


def _start_one(package: str, port: int, state: dict[str, Any]) -> dict[str, Any]:
    LOG_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    log_path = LOG_DIR / f"{package}.log"
    env = os.environ.copy()
    env["PYTHONPATH"] = _pythonpath()
    env["PYTHONUNBUFFERED"] = "1"
    # Keep package MCP URLs consistent even before all are up
    env["IPFS_ACCELERATE_MCP_URL"] = _url(DEFAULTS["ipfs_accelerate_py"]["port"])
    env["IPFS_DATASETS_MCP_URL"] = _url(DEFAULTS["ipfs_datasets_py"]["port"])
    env["IPFS_KIT_MCP_URL"] = _url(DEFAULTS["ipfs_kit_py"]["port"])
    if package == "ipfs_accelerate_py":
        env["IPFS_MCP_HOST"] = "127.0.0.1"
        env["IPFS_MCP_PORT"] = str(port)

    cmd = _cmd_for(package, port)
    log_handle = open(log_path, "ab", buffering=0)
    proc = subprocess.Popen(
        cmd,
        cwd=str(REPO),
        env=env,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    meta = {
        "package": package,
        "pid": proc.pid,
        "port": port,
        "url": _url(port),
        "env_key": DEFAULTS[package]["env_key"],
        "log": str(log_path),
        "cmd": cmd,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "running": True,
    }
    state.setdefault("servers", {})[package] = meta
    _save_state(state)
    return meta


def _wait_ready(package: str, meta: dict[str, Any], timeout: float = 45.0) -> dict[str, Any]:
    paths = tuple(DEFAULTS[package]["health_paths"])
    deadline = time.time() + timeout
    last: dict[str, Any] = {"ok": False, "error": "timeout"}
    while time.time() < deadline:
        if not _pid_alive(meta.get("pid")):
            return {"ok": False, "error": "process_exited", "log": meta.get("log")}
        last = _probe(str(meta["url"]), paths)
        if last.get("ok"):
            return last
        time.sleep(0.75)
    return last


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--stop", action="store_true")
    parser.add_argument("--no-accelerate", action="store_true")
    parser.add_argument("--no-datasets", action="store_true")
    parser.add_argument("--no-kit", action="store_true")
    parser.add_argument("--accelerate-port", type=int, default=DEFAULTS["ipfs_accelerate_py"]["port"])
    parser.add_argument("--datasets-port", type=int, default=DEFAULTS["ipfs_datasets_py"]["port"])
    parser.add_argument("--kit-port", type=int, default=DEFAULTS["ipfs_kit_py"]["port"])
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args(argv)

    STATE_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    state = _load_state()

    if args.stop:
        state = _stop_all(state)
        print("stopped")
        print(f"state={STATE_FILE}")
        return 0

    if args.status:
        servers = state.get("servers") or {}
        for pkg, meta in servers.items():
            alive = _pid_alive(meta.get("pid"))
            probe = _probe(str(meta.get("url") or _url(meta.get("port") or 0)), tuple(DEFAULTS[pkg]["health_paths"])) if meta.get("url") else {"ok": False}
            print(
                f"{pkg:20} pid={meta.get('pid')} alive={alive} "
                f"url={meta.get('url')} probe_ok={probe.get('ok')} "
                f"tools={probe.get('tool_count')}"
            )
        print(f"env_file={ENV_FILE}")
        return 0

    plan = []
    if not args.no_accelerate:
        plan.append(("ipfs_accelerate_py", args.accelerate_port))
    if not args.no_datasets:
        plan.append(("ipfs_datasets_py", args.datasets_port))
    if not args.no_kit:
        plan.append(("ipfs_kit_py", args.kit_port))

    # Stop only packages we are about to (re)start; keep others running.
    servers = dict(state.get("servers") or {})
    for package, _port in plan:
        meta = servers.get(package) or {}
        pid = meta.get("pid")
        if _pid_alive(pid):
            try:
                os.kill(int(pid), signal.SIGTERM)
            except OSError:
                pass
        if package in servers:
            servers[package]["running"] = False
    time.sleep(0.8)
    for package, _port in plan:
        meta = servers.get(package) or {}
        pid = meta.get("pid")
        if _pid_alive(pid):
            try:
                os.kill(int(pid), signal.SIGKILL)
            except OSError:
                pass
    state["servers"] = {
        k: v for k, v in servers.items() if k not in {p for p, _ in plan}
    }

    results = []
    for package, port in plan:
        print(f"starting {package} on {_url(port)} …")
        meta = _start_one(package, port, state)
        ready = _wait_ready(package, meta, timeout=args.timeout)
        meta["ready"] = bool(ready.get("ok"))
        meta["probe"] = ready
        state["servers"][package] = meta
        _save_state(state)
        results.append((package, meta, ready))
        print(
            f"  pid={meta['pid']} ready={ready.get('ok')} "
            f"detail={ready.get('path') or ready.get('error')}"
        )

    print(f"\nenv_file={ENV_FILE}")
    print(f"state={STATE_FILE}")
    print("source with:  set -a; source", ENV_FILE, "; set +a")
    ok = all(r[2].get("ok") for r in results) if results else False
    # Allow partial: accelerate+datasets is enough for logic prove path
    critical = [
        r
        for r in results
        if r[0] in {"ipfs_accelerate_py", "ipfs_datasets_py"}
    ]
    critical_ok = all(r[2].get("ok") for r in critical) if critical else False
    print("PASSED" if critical_ok else "FAILED")
    return 0 if critical_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
