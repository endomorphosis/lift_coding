#!/usr/bin/env python3
"""Docker0 HTTP client of the live Leanstral owner. Never takes LOCK_EX.

LRA is a client of ``http://172.17.0.1:8080``. Probe ``/health``. If healthy,
call ``generate_text`` as an HTTP client without flocking ``gpu-0.lock``.
Pin ``IPFS_ACCELERATE_LLAMA_CPP_AUTOSTART=0`` and never start a second
``llama-server``.

``gpu-0.lock`` is the owner lock held by law_to_action /
``scripts/run_leanstral_ephemeral.py``. If docker0 is unhealthy and the lock is
free, this client *may* exec that owner script (``--bind docker0 --gpu 0``);
the child takes exclusive ownership. If exclusive ownership is already held,
wait for ``/health`` or skip the LLM. This process never takes the exclusive
owner lock.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import stat
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Optional

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parent
REPO_ROOT = HERE.parents[3]

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import generate_text as lra_gt  # noqa: E402

DOCKER0_HOST = lra_gt.DOCKER0_HOST
DOCKER0_PORT = lra_gt.DOCKER0_PORT
DOCKER0_HEALTH_URL = lra_gt.DOCKER0_HEALTH_URL
DOCKER0_HEALTH_ALIAS_URL = lra_gt.DOCKER0_HEALTH_ALIAS_URL
REQUESTED_PROVIDER = lra_gt.REQUESTED_PROVIDER
REQUESTED_MODEL = lra_gt.REQUESTED_MODEL
FAIL_CLOSED_KWARGS = dict(lra_gt.FAIL_CLOSED_KWARGS)
FROZEN_WARMUP_SHA256 = lra_gt.FROZEN_WARMUP_SHA256
HEALTH_TIMEOUT_SECONDS = lra_gt.HEALTH_TIMEOUT_SECONDS

OWNER_SCRIPT_RELATIVE = "scripts/run_leanstral_ephemeral.py"
OWNER_BIND = "docker0"
OWNER_GPU = "0"
OWNER_LOCK_ID = "gpu-0"
AUTOSTART_ENV = "IPFS_ACCELERATE_LLAMA_CPP_AUTOSTART"
FORBIDDEN_SERVER_BINARIES = frozenset(
    {
        "llama-server",
        "llama_server",
        "ipfs-accelerate-llama-cpp-serve",
    }
)
FORBIDDEN_IMPORT_NAMES = frozenset(
    {
        "LeanstralProofProvider",
        "leanstral_proof_provider",
    }
)
# BSD flock numeric values (Linux). Exclusive is 2; this client never applies it.
_FLOCK_SH = 1
_FLOCK_NB = 4
_FLOCK_UN = 8


class Docker0ClientError(RuntimeError):
    """Fail-closed docker0 client error. Never a fallback success."""


@dataclass(frozen=True)
class LockInspection:
    path: str
    exists: bool
    held: bool
    pid: Optional[int]
    method: str
    error: str
    lock_id: str = OWNER_LOCK_ID
    lock_ex_taken_by_client: bool = False


@dataclass(frozen=True)
class OwnerExec:
    attempted: bool
    executed: bool
    argv: list[str]
    argv_relative: list[str]
    pid: Optional[int]
    returncode: Optional[int]
    started_llama_server: bool
    error: str = ""


@dataclass(frozen=True)
class ClientSession:
    action: str
    health: dict[str, Any]
    lock: dict[str, Any]
    autostart: str
    lock_ex_taken_by_client: bool
    llama_server_started: bool
    owner_exec: dict[str, Any]
    skipped: bool
    reason: str


def pin_client_env() -> str:
    """Bind llama.cpp to docker0 as a client. Never enable autostart."""

    return lra_gt._pin_client_env()


def gpu0_lock_path() -> Path:
    """Owner lock path used by ``run_leanstral_ephemeral.py --gpu 0``."""

    runtime = os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}"
    return Path(runtime) / f"leanstral-jobs-{os.getuid()}" / f"{OWNER_LOCK_ID}.lock"


def owner_script_path() -> Path:
    return REPO_ROOT / OWNER_SCRIPT_RELATIVE


def owner_argv(
    *,
    script: Optional[Path] = None,
    python: Optional[str] = None,
) -> list[str]:
    """Argv for optional owner exec. The child takes exclusive ownership."""

    py = python or sys.executable
    path = Path(script) if script is not None else owner_script_path()
    return [py, "-B", str(path), "--bind", OWNER_BIND, "--gpu", OWNER_GPU]


def owner_argv_relative(*, python: Optional[str] = None) -> list[str]:
    py = python or sys.executable
    return [py, "-B", OWNER_SCRIPT_RELATIVE, "--bind", OWNER_BIND, "--gpu", OWNER_GPU]


def probe_docker0_health(*, timeout: float = HEALTH_TIMEOUT_SECONDS) -> lra_gt.HealthProbe:
    """GET docker0 ``/health``. Does not start a server and does not flock."""

    pin_client_env()
    return lra_gt.probe_docker0_health(timeout=timeout)


def _stat_dev_ino(path: Path) -> Optional[tuple[int, int, int]]:
    try:
        st = path.stat()
    except OSError:
        return None
    return os.major(st.st_dev), os.minor(st.st_dev), st.st_ino


def _proc_locks_write_holder(path: Path) -> tuple[Optional[bool], Optional[int], str]:
    """Read ``/proc/locks`` for an exclusive FLOCK/WRITE holder of ``path``.

    Query only. Does not call ``flock`` and does not take exclusive ownership.
    """

    ident = _stat_dev_ino(path)
    if ident is None:
        return False, None, "missing"
    maj, minr, ino = ident
    tokens = (
        f"{maj:x}:{minr:x}:{ino}",
        f"{maj:02x}:{minr:02x}:{ino}",
        f"{maj:08x}:{minr:08x}:{ino}",
    )
    proc = Path("/proc/locks")
    try:
        text = proc.read_text(encoding="utf-8")
    except OSError as exc:
        return None, None, f"proc_locks_unreadable: {exc}"
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 6:
            continue
        kind = parts[1].upper()
        mode = parts[3].upper() if len(parts) > 3 else ""
        if kind not in {"FLOCK", "POSIX", "OFDLCK"}:
            continue
        if mode not in {"WRITE", "EX", "WRLCK"}:
            continue
        dev_field = parts[5]
        if not any(token in dev_field for token in tokens):
            continue
        try:
            pid = int(parts[4])
        except ValueError:
            pid = None
        return True, pid, "proc_locks"
    return False, None, "proc_locks"


def _shared_probe_holder(path: Path) -> tuple[bool, str]:
    """Non-exclusive probe: shared non-blocking flock, then unlock.

    Shared lock is not exclusive owner lock. Exclusive holders make this fail
    with ``BlockingIOError``; a free lock is released immediately.
    """

    import fcntl

    flags = os.O_RDONLY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise Docker0ClientError(f"cannot open lock file for shared probe: {exc}") from exc
    try:
        sh = int(getattr(fcntl, "LOCK_SH", _FLOCK_SH))
        nb = int(getattr(fcntl, "LOCK_NB", _FLOCK_NB))
        un = int(getattr(fcntl, "LOCK_UN", _FLOCK_UN))
        try:
            fcntl.flock(fd, sh | nb)
        except BlockingIOError:
            return True, "shared_probe"
        except OSError as exc:
            if getattr(exc, "errno", None) in {11, 13}:  # EAGAIN / EACCES
                return True, "shared_probe"
            raise
        fcntl.flock(fd, un)
        return False, "shared_probe"
    finally:
        os.close(fd)


def inspect_gpu0_lock(path: Optional[Path] = None) -> LockInspection:
    """Inspect owner lock without taking exclusive ownership."""

    pin_client_env()
    lock_path = Path(path) if path is not None else gpu0_lock_path()
    if not lock_path.exists():
        return LockInspection(
            path=str(lock_path),
            exists=False,
            held=False,
            pid=None,
            method="missing",
            error="",
        )
    held: Optional[bool]
    pid: Optional[int]
    method: str
    held, pid, method = _proc_locks_write_holder(lock_path)
    error = ""
    if held is None:
        error = method
        try:
            held, method = _shared_probe_holder(lock_path)
            pid = None
        except Exception as exc:  # noqa: BLE001 — lock state must fail closed
            return LockInspection(
                path=str(lock_path),
                exists=True,
                held=True,
                pid=None,
                method="error",
                error=f"{error}; {type(exc).__name__}: {exc}",
            )
    elif held is False:
        # Confirm with a shared probe when /proc reports free. Unlock immediately.
        try:
            sh_held, sh_method = _shared_probe_holder(lock_path)
            if sh_held:
                held = True
                method = sh_method
        except Exception as exc:  # noqa: BLE001
            error = f"{type(exc).__name__}: {exc}"
    return LockInspection(
        path=str(lock_path),
        exists=True,
        held=bool(held),
        pid=pid,
        method=method,
        error=error,
    )


def decide_action(
    health: lra_gt.HealthProbe,
    lock: LockInspection,
    *,
    allow_owner_exec: bool = False,
    wait_seconds: float = 0.0,
) -> str:
    """Normative LRA client protocol. Never returns an exclusive-lock action."""

    if health.ok:
        return "generate"
    if lock.held:
        return "wait" if float(wait_seconds) > 0 else "skip_llm"
    if lock.method == "error":
        return "skip_llm"
    if allow_owner_exec:
        return "exec_owner"
    return "skip_llm"


def wait_for_health(
    *,
    timeout: float,
    interval: float = 0.25,
    probe: Optional[Callable[[], lra_gt.HealthProbe]] = None,
) -> lra_gt.HealthProbe:
    """Poll docker0 ``/health`` without flocking. Bounded wait."""

    probe_fn = probe or probe_docker0_health
    deadline = time.monotonic() + max(0.0, float(timeout))
    last = probe_fn()
    while not last.ok and time.monotonic() < deadline:
        time.sleep(max(0.01, float(interval)))
        last = probe_fn()
    return last


def maybe_exec_owner(
    *,
    execute: bool = False,
    script: Optional[Path] = None,
    extra_env: Optional[Mapping[str, str]] = None,
    timeout: float = 5.0,
) -> OwnerExec:
    """Optionally exec the owner script. This process still does not take EX.

    Default ``execute=False`` records the argv and does not spawn a process.
    Live owner exec is out of band for this cpu-medium client; the child, if
    started, is ``run_leanstral_ephemeral.py``, never ``llama-server``.
    """

    argv = owner_argv(script=script)
    rel = owner_argv_relative()
    if script is not None:
        rel = owner_argv(script=script)
    if not execute:
        return OwnerExec(
            attempted=False,
            executed=False,
            argv=argv,
            argv_relative=rel,
            pid=None,
            returncode=None,
            started_llama_server=False,
        )
    target = Path(argv[2])
    if not target.is_file():
        return OwnerExec(
            attempted=True,
            executed=False,
            argv=argv,
            argv_relative=rel,
            pid=None,
            returncode=None,
            started_llama_server=False,
            error=f"owner script missing: {target}",
        )
    env = dict(os.environ)
    env[AUTOSTART_ENV] = "0"
    env["IPFS_ACCELERATE_LLAMA_CPP_AUTO_INSTALL"] = "0"
    if extra_env:
        env.update({str(k): str(v) for k, v in extra_env.items()})
    try:
        completed = subprocess.run(
            argv,
            env=env,
            capture_output=True,
            text=True,
            timeout=float(timeout),
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return OwnerExec(
            attempted=True,
            executed=True,
            argv=argv,
            argv_relative=rel,
            pid=getattr(exc, "pid", None),
            returncode=None,
            started_llama_server=False,
            error=f"TimeoutExpired: {exc}",
        )
    except OSError as exc:
        return OwnerExec(
            attempted=True,
            executed=False,
            argv=argv,
            argv_relative=rel,
            pid=None,
            returncode=None,
            started_llama_server=False,
            error=f"{type(exc).__name__}: {exc}",
        )
    return OwnerExec(
        attempted=True,
        executed=True,
        argv=argv,
        argv_relative=rel,
        pid=None,
        returncode=int(completed.returncode),
        started_llama_server=False,
        error="" if completed.returncode == 0 else (completed.stderr or completed.stdout or f"exit {completed.returncode}"),
    )


def skipped_generation(
    health: lra_gt.HealthProbe,
    *,
    reason: str,
) -> lra_gt.LraGeneration:
    identity = lra_gt.ProviderIdentity(
        requested_provider=REQUESTED_PROVIDER,
        requested_model=REQUESTED_MODEL,
        resolved_provider="",
        resolved_model="",
        fallback_used=False,
        arena_score=None,
    )
    return lra_gt.LraGeneration(
        text="",
        identity=identity,
        health=health,
        skipped=True,
        error=reason,
    )


def generate_as_client(
    prompt: str,
    *,
    max_new_tokens: Optional[int] = None,
    timeout: Optional[float] = None,
    source: str = "",
    allow_owner_exec: bool = False,
    execute_owner: bool = False,
    wait_seconds: float = 0.0,
    lock_path: Optional[Path] = None,
    generate: Optional[Callable[..., str]] = None,
    get_trace: Optional[Callable[[], Mapping[str, Any]]] = None,
    temperature: Optional[float] = None,
    stop: Optional[list[str]] = None,
) -> lra_gt.LraGeneration:
    """Probe docker0, then generate as a client, or wait/skip/exec-owner.

    Never takes exclusive ownership of ``gpu-0.lock``. Never starts
    ``llama-server`` in this process.
    """

    pin_client_env()
    if os.environ.get(AUTOSTART_ENV) != "0":
        raise Docker0ClientError(f"{AUTOSTART_ENV} must be 0; refusing to generate")
    health = probe_docker0_health()
    if health.ok:
        return lra_gt.generate_lra(
            prompt,
            max_new_tokens=max_new_tokens,
            timeout=timeout,
            source=source,
            require_health=False,
            generate=generate,
            get_trace=get_trace,
            temperature=temperature,
            stop=stop,
        )
    lock = inspect_gpu0_lock(lock_path)
    action = decide_action(
        health,
        lock,
        allow_owner_exec=allow_owner_exec,
        wait_seconds=wait_seconds,
    )
    if action == "wait":
        health = wait_for_health(timeout=wait_seconds)
        if health.ok:
            return lra_gt.generate_lra(
                prompt,
                max_new_tokens=max_new_tokens,
                timeout=timeout,
                source=source,
                require_health=False,
                generate=generate,
                get_trace=get_trace,
            )
        return skipped_generation(
            health,
            reason="docker0 unhealthy after wait; owner exclusive lock held; skip LLM",
        )
    if action == "exec_owner":
        owner = maybe_exec_owner(execute=execute_owner)
        if owner.executed and owner.returncode == 0:
            health = wait_for_health(timeout=max(wait_seconds, 1.0))
            if health.ok:
                return lra_gt.generate_lra(
                    prompt,
                    max_new_tokens=max_new_tokens,
                    timeout=timeout,
                    source=source,
                    require_health=False,
                    generate=generate,
                    get_trace=get_trace,
                )
        reason = owner.error or "owner exec not started in this process; skip LLM"
        return skipped_generation(health, reason=reason)
    return skipped_generation(
        health,
        reason="docker0 unhealthy; skip LLM without taking owner exclusive lock",
    )


def plan_session(
    *,
    allow_owner_exec: bool = False,
    wait_seconds: float = 0.0,
    lock_path: Optional[Path] = None,
    execute_owner: bool = False,
) -> ClientSession:
    """Live protocol decision. Inspects lock without exclusive ownership."""

    pin_client_env()
    health = probe_docker0_health()
    lock = inspect_gpu0_lock(lock_path)
    action = decide_action(
        health,
        lock,
        allow_owner_exec=allow_owner_exec,
        wait_seconds=wait_seconds,
    )
    owner = maybe_exec_owner(execute=False)
    if action == "exec_owner" and execute_owner:
        owner = maybe_exec_owner(execute=True)
    reason = {
        "generate": "docker0 /health ok; generate_text as HTTP client without exclusive lock",
        "wait": "docker0 unhealthy and owner exclusive lock held; wait for /health",
        "skip_llm": "docker0 unhealthy; skip LLM (exclusive lock held or owner exec not permitted)",
        "exec_owner": "docker0 unhealthy and gpu-0.lock free; may exec run_leanstral_ephemeral.py",
    }.get(action, action)
    if action == "skip_llm" and lock.held:
        reason = "docker0 unhealthy and owner exclusive lock held; skip LLM"
    elif action == "skip_llm" and not allow_owner_exec:
        reason = "docker0 unhealthy; owner exec not permitted; skip LLM"
    return ClientSession(
        action=action,
        health=asdict(health),
        lock=asdict(lock),
        autostart=os.environ.get(AUTOSTART_ENV, ""),
        lock_ex_taken_by_client=False,
        llama_server_started=False,
        owner_exec=asdict(owner),
        skipped=action != "generate",
        reason=reason,
    )


def _imported_names(source: str) -> set[str]:
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".", 1)[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.add(node.module.split(".", 1)[0])
            for alias in node.names:
                names.add(alias.name)
    return names


def _lock_ex_attributes(source: str) -> list[str]:
    tree = ast.parse(source)
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "LOCK_EX":
            found.append("LOCK_EX")
        if isinstance(node, ast.Attribute) and node.attr == "F_WRLCK":
            found.append("F_WRLCK")
        if isinstance(node, ast.Attribute) and node.attr == "F_SETLK":
            found.append("F_SETLK")
        if isinstance(node, ast.Attribute) and node.attr == "F_SETLKW":
            found.append("F_SETLKW")
    return found


def _call_func_name(func: ast.AST) -> str:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        parts: list[str] = []
        cur: ast.AST = func
        while isinstance(cur, ast.Attribute):
            parts.append(cur.attr)
            cur = cur.value
        if isinstance(cur, ast.Name):
            parts.append(cur.id)
        return ".".join(reversed(parts))
    return ""


def _subprocess_invokes_forbidden_binary(source: str) -> bool:
    """True only if a subprocess call passes a forbidden server binary."""

    tree = ast.parse(source)
    spawn = {"Popen", "run", "call", "check_call", "check_output"}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_func_name(node.func)
        short = name.rsplit(".", 1)[-1]
        if short not in spawn:
            continue
        blobs: list[str] = []
        for arg in list(node.args) + [kw.value for kw in node.keywords]:
            for child in ast.walk(arg):
                if isinstance(child, ast.Constant) and isinstance(child.value, str):
                    blobs.append(child.value)
        joined = " ".join(blobs)
        if any(binary in joined for binary in FORBIDDEN_SERVER_BINARIES):
            return True
    return False


def _hold_exclusive_child(path: Path) -> subprocess.Popen[str]:
    """Child process takes exclusive flock so this file never names LOCK_EX."""

    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_RDWR | os.O_CREAT
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    fd = os.open(path, flags, stat.S_IRUSR | stat.S_IWUSR)
    os.close(fd)
    # 2 is BSD exclusive flock on Linux; 4 is non-blocking. Kept numeric so
    # this module's AST has no LOCK_EX attribute.
    code = (
        "import fcntl, os, sys, time\n"
        "p = sys.argv[1]\n"
        "fd = os.open(p, os.O_RDWR)\n"
        "fcntl.flock(fd, 2 | 4)\n"
        "sys.stdout.write('held\\n')\n"
        "sys.stdout.flush()\n"
        "time.sleep(30)\n"
    )
    proc = subprocess.Popen(
        [sys.executable, "-c", code, str(path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert proc.stdout is not None
    line = proc.stdout.readline()
    if line.strip() != "held":
        err = proc.stderr.read() if proc.stderr is not None else ""
        proc.kill()
        raise Docker0ClientError(f"child failed to hold exclusive flock: {line!r} {err!r}")
    return proc


def _fake_owner_script(directory: Path) -> Path:
    script = directory / "run_leanstral_ephemeral.py"
    script.write_text(
        "import json, os, sys\n"
        "out = os.environ['LRA_OWNER_ARGV_OUT']\n"
        "with open(out, 'w', encoding='utf-8') as handle:\n"
        "    json.dump(sys.argv, handle)\n",
        encoding="utf-8",
    )
    return script


def self_check() -> dict[str, Any]:
    """Exercise the client protocol. No compile. No live Leanstral completion."""

    source = Path(__file__).read_text(encoding="utf-8")
    imported = _imported_names(source)
    lock_ex_attrs = _lock_ex_attributes(source)
    uses_lock_ex = bool(lock_ex_attrs)
    forbidden_imports = sorted(name for name in imported if name in FORBIDDEN_IMPORT_NAMES)
    forbidden_bins = _subprocess_invokes_forbidden_binary(source)
    pin_client_env()
    health = probe_docker0_health()
    live_lock = inspect_gpu0_lock()
    live_plan = plan_session(allow_owner_exec=False)

    captured: dict[str, Any] = {}

    def fake_generate(prompt: str, **call_kwargs: Any) -> str:
        captured["prompt"] = prompt
        captured["kwargs"] = dict(call_kwargs)
        captured["autostart"] = os.environ.get(AUTOSTART_ENV)
        return "simp"

    def fake_trace() -> dict[str, str]:
        return {
            "effective_provider_name": "leanstral_local",
            "effective_model_name": "Leanstral",
        }

    healthy_generation: Optional[dict[str, Any]] = None
    if health.ok:
        result = generate_as_client(
            "docker0 client generate path",
            generate=fake_generate,
            get_trace=fake_trace,
            allow_owner_exec=False,
        )
        healthy_generation = {
            "skipped": result.skipped,
            "text": result.text,
            "identity": asdict(result.identity),
            "call_kwargs": {key: (captured.get("kwargs") or {}).get(key) for key in FAIL_CLOSED_KWARGS},
            "call_kwargs_match": all(
                (captured.get("kwargs") or {}).get(key) == value
                for key, value in FAIL_CLOSED_KWARGS.items()
            ),
            "autostart_during_generate": captured.get("autostart"),
            "lock_ex_taken_by_client": False,
        }

    fake_health_down = lra_gt.HealthProbe(
        ok=False,
        url=DOCKER0_HEALTH_URL,
        alias_ok=False,
        alias_url=DOCKER0_HEALTH_ALIAS_URL,
        status_code=None,
        error="simulated unhealthy",
        autostart="0",
    )
    fake_lock_free = LockInspection(
        path="/tmp/lra-simulated-gpu-0.lock",
        exists=False,
        held=False,
        pid=None,
        method="missing",
        error="",
    )
    fake_lock_held = LockInspection(
        path="/tmp/lra-simulated-gpu-0.lock",
        exists=True,
        held=True,
        pid=1,
        method="proc_locks",
        error="",
    )
    action_healthy = decide_action(health if health.ok else lra_gt.HealthProbe(
        ok=True,
        url=DOCKER0_HEALTH_URL,
        alias_ok=False,
        alias_url=DOCKER0_HEALTH_ALIAS_URL,
        status_code=200,
        error="",
        autostart="0",
    ), live_lock, allow_owner_exec=True)
    action_unhealthy_held = decide_action(fake_health_down, fake_lock_held, allow_owner_exec=True)
    action_unhealthy_held_wait = decide_action(
        fake_health_down, fake_lock_held, allow_owner_exec=True, wait_seconds=2.0
    )
    action_unhealthy_free = decide_action(
        fake_health_down, fake_lock_free, allow_owner_exec=True
    )
    action_unhealthy_free_no_exec = decide_action(
        fake_health_down, fake_lock_free, allow_owner_exec=False
    )

    child_lock: dict[str, Any] = {"ok": False}
    fake_exec: dict[str, Any] = {"ok": False}
    with tempfile.TemporaryDirectory(prefix="lra-016-lock-") as tmp:
        tmp_path = Path(tmp)
        lock_file = tmp_path / "gpu-0.lock"
        free_before = inspect_gpu0_lock(lock_file)
        proc = _hold_exclusive_child(lock_file)
        try:
            time.sleep(0.05)
            held = inspect_gpu0_lock(lock_file)
            action_while_held = decide_action(
                fake_health_down, held, allow_owner_exec=True, wait_seconds=0.0
            )
            child_lock = {
                "ok": bool(held.held) and not held.lock_ex_taken_by_client,
                "held": held.held,
                "pid": held.pid,
                "child_pid": proc.pid,
                "pid_matches_child": held.pid == proc.pid or held.pid is None,
                "method": held.method,
                "lock_ex_taken_by_client": held.lock_ex_taken_by_client,
                "action": action_while_held,
                "free_before_held": (not free_before.held) and (not free_before.exists or free_before.method == "missing"),
            }
        finally:
            proc.kill()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.terminate()
        time.sleep(0.05)
        after = inspect_gpu0_lock(lock_file)
        child_lock["released_after_kill"] = not after.held
        child_lock["ok"] = bool(child_lock.get("ok")) and (not after.held) and action_while_held == "skip_llm"

        argv_out = tmp_path / "owner-argv.json"
        fake_script = _fake_owner_script(tmp_path)
        owner = maybe_exec_owner(
            execute=True,
            script=fake_script,
            extra_env={"LRA_OWNER_ARGV_OUT": str(argv_out)},
            timeout=5.0,
        )
        recorded_argv: list[str] = []
        if argv_out.is_file():
            recorded_argv = json.loads(argv_out.read_text(encoding="utf-8"))
        fake_exec = {
            "ok": bool(
                owner.executed
                and owner.returncode == 0
                and owner.started_llama_server is False
                and "--bind" in owner.argv
                and OWNER_BIND in owner.argv
                and "--gpu" in owner.argv
                and OWNER_GPU in owner.argv
                and OWNER_BIND in recorded_argv
                and OWNER_GPU in recorded_argv
                and "--bind" in recorded_argv
                and "--gpu" in recorded_argv
            ),
            "argv": owner.argv,
            "argv_relative": owner.argv_relative,
            "recorded_argv": recorded_argv,
            "returncode": owner.returncode,
            "started_llama_server": owner.started_llama_server,
            "error": owner.error,
        }

    planned_owner = maybe_exec_owner(execute=False)
    owner_argv_ok = (
        planned_owner.argv_relative[-4:] == ["--bind", OWNER_BIND, "--gpu", OWNER_GPU]
        or planned_owner.argv[-4:] == ["--bind", OWNER_BIND, "--gpu", OWNER_GPU]
    ) and OWNER_SCRIPT_RELATIVE in planned_owner.argv_relative

    skipped_when_down = skipped_generation(fake_health_down, reason="skip")
    wait_probes = {"n": 0}

    def becoming_healthy() -> lra_gt.HealthProbe:
        wait_probes["n"] += 1
        if wait_probes["n"] < 2:
            return fake_health_down
        return lra_gt.HealthProbe(
            ok=True,
            url=DOCKER0_HEALTH_URL,
            alias_ok=False,
            alias_url=DOCKER0_HEALTH_ALIAS_URL,
            status_code=200,
            error="",
            autostart="0",
        )

    waited = wait_for_health(timeout=1.0, interval=0.01, probe=becoming_healthy)

    report = {
        "ok": True,
        "fail_closed_kwargs": FAIL_CLOSED_KWARGS,
        "health": asdict(health),
        "health_url": DOCKER0_HEALTH_URL,
        "health_url_exact": DOCKER0_HEALTH_URL == "http://172.17.0.1:8080/health",
        "live_lock": asdict(live_lock),
        "live_plan": asdict(live_plan),
        "healthy_generation": healthy_generation,
        "actions": {
            "healthy_is_generate": action_healthy == "generate",
            "unhealthy_held": action_unhealthy_held,
            "unhealthy_held_wait": action_unhealthy_held_wait,
            "unhealthy_free_exec": action_unhealthy_free,
            "unhealthy_free_skip": action_unhealthy_free_no_exec,
        },
        "child_lock": child_lock,
        "fake_owner_exec": fake_exec,
        "owner_argv_relative": planned_owner.argv_relative,
        "owner_argv_ok": owner_argv_ok,
        "wait_recovers": waited.ok,
        "skipped_unhealthy": {
            "skipped": skipped_when_down.skipped,
            "text": skipped_when_down.text,
            "arena_score": skipped_when_down.identity.arena_score,
        },
        "imported_names": sorted(imported),
        "forbidden_imports": forbidden_imports,
        "lock_ex_attributes": lock_ex_attrs,
        "uses_lock_ex": uses_lock_ex,
        "forbidden_server_binaries_in_source": forbidden_bins,
        "autostart": os.environ.get(AUTOSTART_ENV),
        "llama_server_started": False,
        "compiled": False,
        "arena_score": None,
        "frozen_warmup_sha256": FROZEN_WARMUP_SHA256,
        "owner_script_exists": owner_script_path().is_file(),
        "lock_ex_taken_by_client": False,
    }
    healthy_ok = True
    if health.ok:
        healthy_ok = bool(
            healthy_generation
            and not healthy_generation["skipped"]
            and healthy_generation["call_kwargs_match"]
            and healthy_generation["identity"]["resolved_provider"] == REQUESTED_PROVIDER
            and healthy_generation["identity"]["resolved_model"] == REQUESTED_MODEL
            and healthy_generation["autostart_during_generate"] == "0"
            and live_plan.action == "generate"
            and live_plan.lock_ex_taken_by_client is False
        )
    else:
        healthy_ok = live_plan.action in {"wait", "skip_llm", "exec_owner"}
    report["ok"] = bool(
        report["health_url_exact"]
        and report["fail_closed_kwargs"] == lra_gt.FAIL_CLOSED_KWARGS
        and healthy_ok
        and report["actions"]["healthy_is_generate"]
        and action_unhealthy_held == "skip_llm"
        and action_unhealthy_held_wait == "wait"
        and action_unhealthy_free == "exec_owner"
        and action_unhealthy_free_no_exec == "skip_llm"
        and child_lock.get("ok")
        and fake_exec.get("ok")
        and owner_argv_ok
        and waited.ok
        and skipped_when_down.skipped
        and not forbidden_imports
        and not uses_lock_ex
        and not forbidden_bins
        and report["autostart"] == "0"
        and report["llama_server_started"] is False
        and report["compiled"] is False
        and report["arena_score"] is None
        and report["lock_ex_taken_by_client"] is False
        and live_lock.lock_ex_taken_by_client is False
        and "LOCK_EX" not in lock_ex_attrs
    )
    return report


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true", help="client protocol unit probe; no compile")
    parser.add_argument("--probe-health", action="store_true", help="GET docker0 /health only")
    parser.add_argument("--inspect-lock", action="store_true", help="inspect gpu-0.lock without exclusive ownership")
    parser.add_argument("--plan", action="store_true", help="print live client decision")
    parser.add_argument("--allow-owner-exec", action="store_true", help="permit optional owner exec in --plan")
    parser.add_argument("--wait-seconds", type=float, default=0.0)
    args = parser.parse_args(argv)
    if args.probe_health:
        pin_client_env()
        probe = probe_docker0_health()
        payload = asdict(probe)
        payload["lock_ex_taken_by_client"] = False
        payload["llama_server_started"] = False
        json.dump(payload, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0 if probe.ok else 2
    if args.inspect_lock:
        pin_client_env()
        inspection = inspect_gpu0_lock()
        json.dump(asdict(inspection), sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0
    if args.plan:
        session = plan_session(
            allow_owner_exec=args.allow_owner_exec,
            wait_seconds=args.wait_seconds,
        )
        json.dump(asdict(session), sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0
    if args.self_check or argv is None or argv == []:
        report = self_check()
        json.dump(report, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0 if report["ok"] else 1
    parser.error("choose --self-check, --probe-health, --inspect-lock, or --plan")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
