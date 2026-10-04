#!/usr/bin/env python3
"""Run one client against a temporary, bounded local Leanstral server (Linux).

No service is installed, enabled, unmasked, or reused. The transient systemd
backend provides cgroup limits; the fallback uses a subreaper, inherited limits,
CPU affinity, and aggregate RSS/task monitoring. See run_leanstral_ephemeral.md.
The subreaper pattern follows ipfs_accelerate's native_cli_subreaper.py without
importing the supervisor package or initializing any model providers.
"""
from __future__ import annotations

import argparse
import contextlib
import ctypes
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import shutil
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid

GIB = 1024 ** 3
CACHE = Path.home() / ".cache/ipfs_accelerate_py/llama_cpp"
DEFAULT_MODEL = CACHE / "models/cid-v1/bafkreicgnd6su3jhmtpckbejqurdb2lchdvvydluswdg5m5zy3cpvroh3i/Leanstral-1.5-119B-A6B-NVFP4.gguf"
STOP = 0
LOOPBACK_BIND = "127.0.0.1"
DOCKER0 = "docker0"


class RunnerError(Exception):
    pass


def ipv4_proc_hex(address):
    return "".join(f"{int(part):02X}" for part in reversed(address.split(".")))


def iface_ipv4(name):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        packed = struct.pack("256s", name[:15].encode())
        return socket.inet_ntoa(fcntl.ioctl(sock.fileno(), 0x8915, packed)[20:24])
    except OSError:
        return None
    finally:
        sock.close()


def resolve_bind(value):
    requested = str(value or "").strip()
    if requested in {"0.0.0.0", "::", "*", "localhost", ""}:
        raise RunnerError("Refusing wildcard, unspecified, or localhost bind; use 127.0.0.1 or docker0")
    if requested == LOOPBACK_BIND:
        return LOOPBACK_BIND
    gateway = iface_ipv4(DOCKER0)
    if requested in {DOCKER0, gateway} and gateway:
        return gateway
    raise RunnerError("Bind must be 127.0.0.1 or the docker0 gateway IPv4; broad host binds are refused")


def record_signal(signum, _frame):
    global STOP
    STOP = signum


def mem_available():
    values = dict(line.split(":", 1) for line in Path("/proc/meminfo").read_text().splitlines())
    return int(values["MemAvailable"].split()[0]) * 1024


def proc_tree(root):
    """Read owned descendants across threads and sessions, using kernel lineage."""
    found, todo = {}, [root]
    while todo:
        pid = todo.pop()
        if pid in found:
            continue
        try:
            # comm may contain spaces/parentheses; fields after its LAST ')' are fixed.
            fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
            found[pid] = {"rss": int(fields[21]) * os.sysconf("SC_PAGE_SIZE"),
                          "threads": int(fields[17]), "start": fields[19]}
            for task in Path(f"/proc/{pid}/task").iterdir():
                with contextlib.suppress(FileNotFoundError, ProcessLookupError):
                    todo.extend(map(int, (task / "children").read_text().split()))
        except (FileNotFoundError, ProcessLookupError):
            continue
    return found


def same_process(pid, start):
    try:
        return Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[19] == start
    except FileNotFoundError:
        return False


def owns_listener(port, server_pid, bind=LOOPBACK_BIND):
    """Do not accidentally run a client against another process in a bind race."""
    address = ipv4_proc_hex(bind) + ":" + format(port, "04X")
    inodes = {line.split()[9] for line in Path("/proc/net/tcp").read_text().splitlines()[1:]
              if line.split()[1] == address and line.split()[3] == "0A"}
    if not inodes:
        return False
    for pid in proc_tree(server_pid):
        with contextlib.suppress(FileNotFoundError):
            for fd in Path(f"/proc/{pid}/fd").iterdir():
                with contextlib.suppress(FileNotFoundError):
                    if os.readlink(fd) in {"socket:[" + inode + "]" for inode in inodes}:
                        return True
    return False


def cleanup_children(grace=2.0, receipt_path=None):
    """Kill all owned descendants, including adopted double forks/setsid children."""
    started = time.monotonic()
    deadline = started + grace
    seen = {}
    signals = []
    reaped = []
    while True:
        children = proc_tree(os.getpid())
        children.pop(os.getpid(), None)
        for pid, data in children.items():
            seen[pid] = {"start": data["start"], "rss": data["rss"], "threads": data["threads"]}
        signum = signal.SIGTERM if time.monotonic() < deadline else signal.SIGKILL
        for pid, data in children.items():
            if same_process(pid, data["start"]):
                with contextlib.suppress(ProcessLookupError):
                    os.kill(pid, signum)
                    signals.append({"pid": pid, "signal": int(signum), "monotonic": time.monotonic() - started})
        while True:
            try:
                waited, status = os.waitpid(-1, os.WNOHANG)
                if not waited:
                    break
                reaped.append({"pid": waited, "status": int(status)})
            except ChildProcessError:
                children = proc_tree(os.getpid())
                children.pop(os.getpid(), None)
                write_cleanup_receipt(receipt_path, seen, signals, reaped, children, started)
                return not children
        time.sleep(0.025)


def write_cleanup_receipt(receipt_path, seen, signals, reaped, remaining, started):
    if receipt_path is None:
        return
    payload = {
        "schema": "leanstral-ephemeral-child-termination/v1",
        "elapsed_seconds": round(time.monotonic() - started, 4),
        "descendants_seen": {str(pid): row for pid, row in seen.items()},
        "signals": signals,
        "reaped": reaped,
        "remaining_after": sorted(remaining),
        "empty_after": not remaining,
        "child_termination_proven": not remaining and bool(seen),
    }
    Path(receipt_path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def set_subreaper():
    libc = ctypes.CDLL(None, use_errno=True)
    enabled = ctypes.c_int()
    if libc.prctl(36, 1, 0, 0, 0) or libc.prctl(37, ctypes.byref(enabled), 0, 0, 0) or enabled.value != 1:
        raise RunnerError("Linux child subreaper unavailable; refusing to launch")


def child_limits(config):
    # A killed worker must immediately stop its direct children too.
    ctypes.CDLL(None, use_errno=True).prctl(1, signal.SIGKILL, 0, 0, 0)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    cpu = math.ceil(config["wall_seconds"] * config["cpus"])
    resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))
    resource.setrlimit(resource.RLIMIT_NOFILE, (1024, 1024))
    resource.setrlimit(resource.RLIMIT_FSIZE, (GIB, GIB))
    # GPU runtimes reserve substantial virtual address space. RSS is monitored
    # separately; this is only a finite virtual-address backstop.
    virtual = config["memory_bytes"] * 8
    resource.setrlimit(resource.RLIMIT_AS, (virtual, virtual))
    allowed = sorted(os.sched_getaffinity(0))[:config["cpus"]]
    os.sched_setaffinity(0, allowed)


def arm_parent_death():
    parent = os.getppid()
    if ctypes.CDLL(None, use_errno=True).prctl(1, signal.SIGTERM, 0, 0, 0):
        raise OSError("PR_SET_PDEATHSIG failed")
    if os.getppid() != parent:
        os.kill(os.getpid(), signal.SIGTERM)


def server_argv(c):
    command = [c["binary"], "--model", c["model"], "--host", c["bind"],
            "--port", str(c["port"]), "--alias", "leanstral_local",
            "--ctx-size", str(c["context"]), "--n-gpu-layers", str(c["gpu_layers"]),
            "--device", "none" if c["gpu"] == "none" else "CUDA0",
            "--threads", str(c["cpus"]), "--threads-batch", str(c["cpus"]),
            "--parallel", "1", "--batch-size", "128", "--ubatch-size", "64",
            "--fit", "on", "--fit-target", "8192", "--no-warmup"]
    if c.get("chat_template_file"):
        command.extend(["--jinja", "--chat-template-file", c["chat_template_file"]])
    return command


def client_environment(c):
    env = os.environ.copy()
    endpoint = f"http://{c['bind']}:{c['port']}/v1"
    env.update(LEANSTRAL_BASE_URL=endpoint, LEANSTRAL_ENDPOINT=endpoint,
               OPENAI_BASE_URL=endpoint, IPFS_ACCELERATE_LLAMA_CPP_BASE_URL=endpoint,
               IPFS_ACCELERATE_LLAMA_CPP_AUTOSTART="0",
               IPFS_ACCELERATE_PY_LLAMA_CPP_AUTOSTART="0",
               CUDA_VISIBLE_DEVICES="" if c["gpu"] == "none" else c["gpu"],
               OMP_NUM_THREADS=str(c["cpus"]), MKL_NUM_THREADS=str(c["cpus"]),
               OPENBLAS_NUM_THREADS=str(c["cpus"]), LEANSTRAL_MODEL="leanstral_local")
    return env


def worker(c):
    set_subreaper()
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, record_signal)
    # The fallback worker gets a parent-death signal, including on outer SIGKILL.
    if c["backend"] == "process":
        arm_parent_death()
        if os.getppid() != c["parent_pid"]:
            return 143
    # systemd creates the service independently and cannot inherit our flock.
    # Acquire the same lock inside the service BEFORE loading any model.
    service_lock = None
    if c["backend"] == "systemd":
        service_lock = open(c["lock_path"], "a+")
        try:
            fcntl.flock(service_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("Another Leanstral job acquired the GPU lock; no server started", file=sys.stderr)
            return 125
    start = time.monotonic()
    env = client_environment(c)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    client = None
    try:
        with open(c["server_log"], "wb") as log:
            server = subprocess.Popen(server_argv(c), env=env, stdin=subprocess.DEVNULL,
                                      stdout=log, stderr=subprocess.STDOUT,
                                      start_new_session=True,
                                      preexec_fn=lambda: child_limits(c))
            print(json.dumps({"event": "server_started", "pid": server.pid,
                              "backend": c["backend"], "log": c["server_log"]}), flush=True)
            while True:
                elapsed = time.monotonic() - start
                if STOP:
                    return 128 + STOP
                if elapsed >= c["wall_seconds"] or (client is None and elapsed >= c["startup_seconds"]):
                    print("Leanstral job timed out; cleaning up", file=sys.stderr)
                    return 124
                tree = proc_tree(os.getpid())
                if (sum(x["rss"] for x in tree.values()) > c["memory_bytes"]
                        or sum(x["threads"] for x in tree.values()) > c["tasks"]
                        or mem_available() < c["reserve_bytes"]):
                    print("Leanstral resource limit reached; cleaning up", file=sys.stderr)
                    return 125
                if client is not None and client.poll() is not None:
                    return client.returncode if client.returncode >= 0 else 128 - client.returncode
                if server.poll() is not None:
                    print(f"Leanstral server exited ({server.returncode}); see {c['server_log']}", file=sys.stderr)
                    return 125
                if client is None:
                    try:
                        with opener.open(f"http://{c['bind']}:{c['port']}/health", timeout=min(0.5, max(0.01, c["startup_seconds"] - elapsed), max(0.01, c["wall_seconds"] - elapsed))) as reply:
                            healthy = reply.status == 200 and json.loads(reply.read(4096)).get("status") == "ok"
                    except (OSError, ValueError, urllib.error.URLError):
                        healthy = False
                    if healthy and not STOP and owns_listener(c["port"], server.pid, c["bind"]):
                        print(json.dumps({"event": "server_ready", "elapsed_seconds": round(elapsed, 3)}), flush=True)
                        client = subprocess.Popen(c["client"], env=env, stdin=subprocess.DEVNULL,
                                                  start_new_session=True,
                                                  preexec_fn=lambda: child_limits(c))
                time.sleep(0.1)
    finally:
        receipt = Path(c["server_log"]).with_name(Path(c["server_log"]).stem + ".cleanup.json")
        cleanup_children(receipt_path=receipt)
        if service_lock is not None:
            service_lock.close()


def systemd_prefix(unit, c):
    return ["systemd-run", "--user", "--quiet", "--wait", "--collect", "--pipe",
            "--unit=" + unit, "--property=Type=exec", "--property=KillMode=control-group",
            "--property=RuntimeMaxSec=" + str(c["wall_seconds"]),
            "--property=TimeoutStopSec=3", "--property=SendSIGKILL=yes",
            "--property=MemoryMax=" + str(c["memory_bytes"]), "--property=MemorySwapMax=0",
            "--property=CPUQuota=" + str(c["cpus"] * 100) + "%",
            "--property=TasksMax=" + str(c["tasks"]), "--property=OOMPolicy=kill"]


def systemd_available(c):
    if not shutil.which("systemd-run") or not shutil.which("systemctl"):
        return False
    unit = "leanstral-preflight-" + uuid.uuid4().hex
    try:
        result = subprocess.run(systemd_prefix(unit, c) + ["/usr/bin/true"],
                                capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False
    finally:
        with contextlib.suppress(OSError, subprocess.TimeoutExpired):
            subprocess.run(["systemctl", "--user", "stop", unit], capture_output=True, timeout=5)


def preflight(c):
    if sys.platform != "linux":
        raise RunnerError("This runner requires Linux /proc, affinity, and child subreapers")
    binary, model = Path(c["binary"]), Path(c["model"])
    if not binary.is_file() or not os.access(binary, os.X_OK):
        raise RunnerError(f"Server binary is absent or not executable: {binary}")
    if not model.is_file() or model.stat().st_size == 0:
        raise RunnerError(f"Model file is absent or empty: {model}")
    if c.get("chat_template_file"):
        template = Path(c["chat_template_file"])
        if not template.is_file() or not os.access(template, os.R_OK) or template.stat().st_size == 0:
            raise RunnerError(f"Chat template is absent, unreadable, or empty: {template}")
        c["chat_template_sha256"] = hashlib.sha256(template.read_bytes()).hexdigest()
    if not c["client"] or shutil.which(c["client"][0]) is None:
        raise RunnerError("A real client executable is required after --")
    c["client"][0] = shutil.which(c["client"][0])
    if c["cpus"] > len(os.sched_getaffinity(0)):
        raise RunnerError("Requested CPU count exceeds available affinity")
    estimate = model.stat().st_size * 1.10 + min(4 * GIB, c["memory_bytes"] * 0.1)
    if estimate > c["memory_bytes"] or estimate + c["reserve_bytes"] > mem_available():
        raise RunnerError("Insufficient available RAM or memory limit for model plus headroom/reserve")
    with socket.socket() as sock:
        # TIME_WAIT from a completed job is not an active listener conflict.
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((c["bind"], c["port"]))
        except OSError as exc:
            raise RunnerError(f"Port {c['port']} is already in use; refusing to reuse/stop it") from exc
    if c["gpu"] != "none":
        try:
            check = subprocess.run(["nvidia-smi", "--id=" + c["gpu"],
                                    "--query-gpu=index,name,memory.total,memory.free", "--format=csv,noheader"],
                                   capture_output=True, text=True, timeout=5, check=True)
            c["gpu_preflight"] = check.stdout.strip()
        except (OSError, subprocess.SubprocessError) as exc:
            raise RunnerError("Selected NVIDIA GPU is unavailable; use --gpu none for CPU execution") from exc
    c["estimated_minimum_bytes"] = int(estimate)
    c["available_memory_bytes"] = mem_available()


def run(c):
    preflight(c)
    # One job per GPU, even on different ports. CPU-only jobs share a CPU lock.
    runtime = Path(os.environ.get("XDG_RUNTIME_DIR", tempfile.gettempdir())) / f"leanstral-jobs-{os.getuid()}"
    runtime.mkdir(mode=0o700, exist_ok=True)
    if runtime.stat().st_uid != os.getuid() or runtime.stat().st_mode & 0o077:
        raise RunnerError("Runner state directory must be private and owned by this user")
    lock_path = runtime / ("gpu-" + c["gpu"] + ".lock")
    c["lock_path"] = str(lock_path)
    with open(lock_path, "a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RunnerError("Another ephemeral Leanstral job owns the selected GPU/CPU lock") from exc
        if c["preflight_only"]:
            print(json.dumps({"event": "preflight_ok", **c, "server_argv": server_argv(c)}, indent=2))
            return 0
        if c["backend"] != "process":
            available = systemd_available(c)
            if c["backend"] == "systemd" and not available:
                raise RunnerError("Requested transient systemd limits unavailable; no server started")
            c["backend"] = "systemd" if available else "process"
        c["parent_pid"] = os.getpid()
        # A separate watchdog worker remains alive if the invoking wrapper dies.
        # In fallback mode it inherits the lock so a killed wrapper cannot allow
        # a second job to start before descendant cleanup finishes.
        with tempfile.TemporaryDirectory(prefix="job-", dir=runtime) as work:
            config = Path(work) / "config.json"
            config.write_text(json.dumps(c))
            config.chmod(0o600)
            cmd = [sys.executable, "-B", str(Path(__file__).resolve()), "--internal-worker", str(config)]
            unit = "leanstral-job-" + uuid.uuid4().hex
            if c["backend"] == "systemd":
                cmd = systemd_prefix(unit, c) + ["--working-directory=" + os.getcwd()] + cmd
                # Atomic flock in worker arbitrates any competing launch here.
                fcntl.flock(lock, fcntl.LOCK_UN)
            for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
                signal.signal(sig, record_signal)
            process = subprocess.Popen(cmd, start_new_session=True, pass_fds=(lock.fileno(),))
            deadline = time.monotonic() + c["wall_seconds"] + 8
            try:
                while process.poll() is None:
                    if STOP or time.monotonic() >= deadline:
                        if c["backend"] == "systemd":
                            subprocess.run(["systemctl", "--user", "stop", unit], capture_output=True, timeout=6)
                        else:
                            process.send_signal(signal.SIGTERM)
                        process.wait(timeout=6)
                        return 128 + STOP if STOP else 124
                    time.sleep(0.1)
                return process.returncode if process.returncode >= 0 else 128 - process.returncode
            finally:
                if c["backend"] == "systemd":
                    with contextlib.suppress(OSError, subprocess.TimeoutExpired):
                        subprocess.run(["systemctl", "--user", "stop", unit], capture_output=True, timeout=6)
                elif process.poll() is None:
                    process.send_signal(signal.SIGTERM)
                    process.wait(timeout=6)


def positive(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("must be finite and positive")
    return number


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--internal-worker":
        return worker(json.loads(Path(sys.argv[2]).read_text()))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=CACHE / "build/bin/llama-server")
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--chat-template-file", type=Path,
                        help="explicit Jinja template, passed across both runner backends")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--bind", default=LOOPBACK_BIND,
                        help="127.0.0.1 (default) or docker0 gateway IPv4 for restricted bridge-worker transport")
    parser.add_argument("--backend", choices=("auto", "systemd", "process"), default="auto")
    parser.add_argument("--wall-seconds", type=positive, default=10000,
                        help="total job deadline including startup (default: 10000)")
    parser.add_argument("--startup-seconds", type=positive, default=360,
                        help="readiness timeout before the client starts; part of --wall-seconds (default: 360)")
    parser.add_argument("--memory-gib", type=positive, default=90)
    parser.add_argument("--reserve-gib", type=positive, default=12)
    parser.add_argument("--cpus", type=int, default=4)
    parser.add_argument("--tasks", type=int, default=128)
    parser.add_argument("--context", type=int, default=4096)
    parser.add_argument("--gpu", default="0", help="single NVIDIA GPU index, or none")
    parser.add_argument("--gpu-layers", type=int, default=36)
    parser.add_argument("--server-log", type=Path, default=Path("leanstral-ephemeral-server.log"))
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("client", nargs=argparse.REMAINDER, help="-- CLIENT ARG ... (no shell)")
    args = parser.parse_args()
    c = vars(args)
    c["client"] = args.client[1:] if args.client[:1] == ["--"] else args.client
    if not (1 <= args.port <= 65535 and args.cpus > 0 and args.tasks >= 4 and args.context > 0
            and args.gpu_layers >= 0 and (args.gpu == "none" or args.gpu.isdigit())):
        parser.error("invalid port, CPU/task/context count, GPU layers, or GPU index")
    try:
        c["bind"] = resolve_bind(args.bind)
    except RunnerError as exc:
        parser.error(str(exc))
    c["memory_bytes"] = int(c.pop("memory_gib") * GIB)
    c["reserve_bytes"] = int(c.pop("reserve_gib") * GIB)
    for key in ("binary", "model", "server_log"):
        c[key] = str(c[key].expanduser().resolve())
    if c["chat_template_file"] is not None:
        c["chat_template_file"] = str(c["chat_template_file"].expanduser().resolve())
    if args.gpu == "none":
        c["gpu_layers"] = 0
    try:
        return run(c)
    except (RunnerError, OSError, subprocess.SubprocessError) as exc:
        print(f"Leanstral runner: {exc}", file=sys.stderr)
        return 125


if __name__ == "__main__":
    raise SystemExit(main())
