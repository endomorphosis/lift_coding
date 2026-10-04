"""Fresh-process, read-only public historical admission replay.

Only the historical verifier is called. Audit denial is an execution guard,
not an operating-system sandbox or a portable signature/archive attestation.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.abc
import importlib.machinery
import json
import os
import pwd
import resource
import selectors
import signal
import stat
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from codebase_ir_admission_evidence import (
    ArtifactReader,
    assert_fixture,
    canonical,
    load_fixture,
    source_pin_groups,
)
from codebase_ir_external_pins import _bounded_document
from codebase_ir_planning_qualification import verify_snapshot_binding

TIMEOUT_SECONDS = 45
MAX_OUTPUT_BYTES = 1024 * 1024
MAX_READ_FILES = 2048
MAX_READ_TOTAL_BYTES = 256 * 1024 * 1024
MAX_READ_FILE_BYTES = 64 * 1024 * 1024
MAX_CORE_FILES = 512
MAX_CORE_BYTES = 16 * 1024 * 1024


class HistoricalReplayRefusal(PermissionError):
    pass


class ReadOnlyTrace:
    def __init__(self, allowed_roots: list[Path], allowed_files: list[Path]):
        self.allowed_roots, self.allowed_files = allowed_roots, set(allowed_files)
        self.before: dict[str, dict[str, Any]] = {}
        self.bytes_read, self.internal, self.denied = 0, False, []
        self.directories: dict[str, tuple] = {}
        self.native_open = os.open

    def directory(self, path: Path) -> None:
        if (path.resolve(strict=True) != path or any(parent.is_symlink() for parent in (path, *path.parents))
                or not any(path.is_relative_to(root) or root.is_relative_to(path) for root in self.allowed_roots)):
            raise HistoricalReplayRefusal("historical directory metadata outside exact read scope")
        observed = path.stat(follow_symlinks=False)
        if not stat.S_ISDIR(observed.st_mode) or len(self.directories) >= 512 and str(path) not in self.directories:
            raise HistoricalReplayRefusal("historical directory type/count refused")
        identity = observed.st_dev, observed.st_ino, observed.st_mode
        if str(path) in self.directories and self.directories[str(path)] != identity:
            raise HistoricalReplayRefusal("historical directory identity changed")
        self.directories[str(path)] = identity

    def open(self, path, flags, mode=0o777, *, dir_fd=None):
        """Resolve a native directory descriptor before permitting a read."""
        if not self.internal:
            if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
                self.denied.append("open:write")
                raise HistoricalReplayRefusal("read-only historical replay denied write")
            selected = Path(os.fsdecode(path))
            if not selected.is_absolute():
                base = Path.cwd() if dir_fd is None else Path(os.readlink(f"/proc/self/fd/{dir_fd}"))
                selected = base / selected
            if selected.exists():
                self.directory(selected) if selected.is_dir() else self.pin(selected)
        return self.native_open(path, flags, mode, dir_fd=dir_fd)

    def pin(self, path: Path) -> bytes:
        path = path.absolute()
        if not path.exists():
            raise FileNotFoundError(path)
        if path.resolve(strict=True) != path or any(parent.is_symlink() for parent in (path, *path.parents)):
            raise HistoricalReplayRefusal("historical read alias/symlink refused")
        if not (path in self.allowed_files or any(path.is_relative_to(root) for root in self.allowed_roots)):
            raise HistoricalReplayRefusal("historical read outside explicit owner/interpreter/source scope")
        self.internal = True
        try:
            key = str(path)
            if key not in self.before:
                if len(self.before) >= MAX_READ_FILES:
                    raise HistoricalReplayRefusal("historical read count cap exceeded")
                limit = min(MAX_READ_FILE_BYTES, MAX_READ_TOTAL_BYTES - self.bytes_read)
            else:
                limit = self.before[key]["size_bytes"]
            if limit < 0:
                raise HistoricalReplayRefusal("historical read byte cap exceeded")
            raw = _bounded_document(path, limit)
        finally:
            self.internal = False
        pin = {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}
        key = str(path)
        if key in self.before:
            if self.before[key] != pin:
                raise HistoricalReplayRefusal("historical read bytes changed between observations")
        else:
            if len(self.before) >= MAX_READ_FILES or self.bytes_read + len(raw) > MAX_READ_TOTAL_BYTES:
                raise HistoricalReplayRefusal("historical read inventory exceeds bounded profile")
            self.before[key] = pin
            self.bytes_read += len(raw)
        return raw

    def audit(self, event: str, args: tuple[Any, ...]) -> None:
        if self.internal:
            return
        mutations = {"os.mkdir", "os.remove", "os.rmdir", "os.rename", "os.chmod", "os.chown", "os.utime",
            "os.link", "os.symlink", "os.truncate", "os.mknod", "os.setxattr", "os.removexattr", "fcntl.flock"}
        if event in mutations or event.startswith(("subprocess.", "socket.", "os.exec", "os.spawn")) or event in {"os.system", "os.fork", "os.posix_spawn"}:
            self.denied.append(event)
            raise HistoricalReplayRefusal("read-only historical replay denied operation: " + event)
        if event == "open":
            path, mode, flags = args
            if (type(flags) is int and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)
                    or type(mode) is str and any(marker in mode for marker in "wax+")):
                self.denied.append("open:write")
                raise HistoricalReplayRefusal("read-only historical replay denied write")
            if isinstance(path, str | bytes):
                selected = Path(os.fsdecode(path)).absolute()
                if selected.exists():
                    self.directory(selected) if selected.is_dir() else self.pin(selected)
        if event == "import" and len(args) > 1 and type(args[1]) is str and args[1]:
            selected = Path(args[1]).absolute()
            if selected.is_file():
                self.pin(selected)

    def finish(self) -> list[dict[str, Any]]:
        rows = []
        self.internal = True
        try:
            for path, before in sorted(self.before.items()):
                raw = _bounded_document(Path(path), before["size_bytes"])
                after = {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}
                rows.append({"path": path, "before": before, "after": after, "unchanged": before == after})
        finally:
            self.internal = False
        return rows


class ObservedSourceLoader(importlib.machinery.SourceFileLoader):
    def __init__(self, fullname: str, path: str, finder: ObservedCoreFinder):
        super().__init__(fullname, path)
        self.finder = finder

    def get_code(self, fullname: str):
        raw = self.finder.trace.pin(Path(self.path))
        self.finder.observe(fullname, Path(self.path), raw)
        return self.source_to_code(raw, self.path)


class ObservedCoreFinder(importlib.abc.MetaPathFinder):
    def __init__(self, roots: list[Path], trace: ReadOnlyTrace):
        self.roots, self.trace, self.observations = roots, trace, {}
        self.total = 0

    def observe(self, fullname: str, path: Path, raw: bytes) -> None:
        key = str(path)
        if key not in self.observations:
            if len(self.observations) >= MAX_CORE_FILES or self.total + len(raw) > MAX_CORE_BYTES:
                raise HistoricalReplayRefusal("core historical import byte/count cap exceeded")
            self.observations[key] = {"module_names": [], "before": {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}}
            self.total += len(raw)
        self.observations[key]["module_names"].append(fullname)

    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".", 1)[0] not in {"ipfs_accelerate_py", "ipfs_datasets_py"}:
            return None
        spec = importlib.machinery.PathFinder.find_spec(fullname, path if path is not None else [str(root) for root in self.roots])
        if spec is None:
            raise ImportError("historical core import unavailable: " + fullname)
        locations = ([spec.origin] if spec.origin and spec.origin != "namespace" else []) + list(spec.submodule_search_locations or [])
        if not locations or any(not any(Path(location).resolve().is_relative_to(root) for root in self.roots) for location in locations):
            raise HistoricalReplayRefusal("historical core namespace escaped selected working roots")
        if spec.origin:
            if Path(spec.origin).suffix != ".py":
                raise HistoricalReplayRefusal("historical core source must be an explicit Python file")
            spec.loader = ObservedSourceLoader(fullname, spec.origin, self)
        return spec


def select_runtime_roots(workspace: Path, snapshot_roots: list[Path] | None,
                         snapshot_sha256: str | None) -> tuple[list[Path], dict[str, Any] | None]:
    selected = snapshot_roots is not None or snapshot_sha256 is not None
    if selected and (not snapshot_roots or not snapshot_sha256):
        raise HistoricalReplayRefusal("sealed historical replay requires both exact roots and canonical generation identity")
    roots = snapshot_roots or [workspace / "external" / "ipfs_accelerate", workspace / "external" / "ipfs_datasets"]
    return roots, verify_snapshot_binding(roots, snapshot_sha256) if snapshot_sha256 else None


def retained_producer_comparison(records: dict[str, Any], finder: ObservedCoreFinder) -> dict[str, Any]:
    admission = records["before-admission.json"]
    groups = source_pin_groups(admission)
    results = {}
    for group, expected in groups.items():
        rows = []
        for module_name, expected_sha in sorted(expected.items()):
            observed = next(((path, value) for path, value in finder.observations.items() if module_name in value["module_names"]), None)
            rows.append({"module": module_name, "expected_sha256": expected_sha,
                "actual_loaded_path": observed[0] if observed else None,
                "actual_preexec_pin": observed[1]["before"] if observed else None,
                "matches_retained_pin": observed is not None and observed[1]["before"]["sha256"] == expected_sha})
        results[group] = {"pins": rows, "expected_count": len(expected), "all_match": all(row["matches_retained_pin"] for row in rows)}
    return results


def child_replay(fixture: Path, expected_result_sha256: str, *, workspace: Path,
                 snapshot_roots: list[Path] | None = None, snapshot_sha256: str | None = None) -> dict[str, Any]:
    started = time.monotonic()
    resource.setrlimit(resource.RLIMIT_CPU, (30, 30))
    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_OUTPUT_BYTES, MAX_OUTPUT_BYTES))
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    repository = workspace.resolve(strict=True)
    roots, snapshot_before = select_runtime_roots(repository, snapshot_roots, snapshot_sha256)
    reader = ArtifactReader(fixture)
    records = load_fixture(reader)
    assert_fixture(records)
    if reader.pins[str(reader.root / "result.json")]["sha256"] != expected_result_sha256:
        raise HistoricalReplayRefusal("retained fixture input drifted before fresh process")
    declaration = records["before-admission.json"]["declaration"]["payload"]
    registry = Path(pwd.getpwuid(os.geteuid()).pw_dir) / ".local" / "state" / "ipfs_accelerate_py" / "local-profile-root-registry"
    allowed = [reader.root, *roots, Path(sys.base_prefix).resolve(), Path(sys.prefix).resolve(), registry]
    if snapshot_roots:
        allowed.extend([roots[0].parent, Path(__file__).resolve().parents[1] / "release_audit"])
    tools = [Path(declaration["tool_policy"][name]["path"]) for name in ("python", "lean")]
    trace = ReadOnlyTrace(allowed, tools)
    finder = ObservedCoreFinder(roots, trace)
    sys.meta_path.insert(0, finder)
    sys.addaudithook(trace.audit)
    os.open = trace.open
    report: dict[str, Any] = {"schema": "codebase-ir-owner-local-historical-replay@1", "status": "incomplete",
        "observed_current": False, "current_launch_permission_claimed": False, "task_store_opened": False,
        "native_observation_or_proof_invoked": False, "worker_launched": False, "training_steps": 0,
        "runtime_source_mode": "sealed_snapshot_read_only" if snapshot_roots else "working_tree_observed_read_only",
        "runtime_snapshot_roots": [str(root) for root in snapshot_roots or []], "requested_runtime_snapshot_sha256": snapshot_sha256,
        "runtime_snapshot_before": snapshot_before, "original_whole_producer_closure_replayed": False,
        "guard_scope": "Python audit denial with explicit directory-relative read tracking; not an OS sandbox or process-origin attestation",
        "guard_profile": "codebase-ir-read-only-directory-relative-files@1", "native_controls": []}
    try:
        from ipfs_accelerate_py.agent_supervisor.control.profile_authority import (
            LocalProfileTampered,
        )
        from ipfs_accelerate_py.agent_supervisor.prompt.prompt_workflow import PromptGraphError
        from ipfs_accelerate_py.agent_supervisor.runtime.finite_repository_admission import (
            FiniteRepositoryAdmissionError,
            verify_finite_repository_admission,
        )
        from ipfs_accelerate_py.agent_supervisor.runtime.local_planning_admission import (
            LocalPlanningError,
        )
        report["retained_producer_comparison"] = retained_producer_comparison(records, finder)
        if snapshot_roots and not all(group["all_match"] for group in report["retained_producer_comparison"].values()):
            raise HistoricalReplayRefusal("selected signed producer or model frontend bytes differ from retained evidence")
        for name, successor in (("before-admission.json", False), ("successor-admission.json", True), ("cold-admission.json", True)):
            verified = verify_finite_repository_admission(admission=records[name])
            if verified.get("observed_current") is not False or verified["admission"] != records[name]:
                raise AssertionError("historical verifier changed scope or complete admission")
            report.setdefault("verifications", []).append({"record": name, "observed_current": False,
                "administrator_task_cids": verified["semantic_context"]["administrator_task_cids"],
                "native_task_bindings": verified["semantic_context"]["native_task_bindings"],
                "no_work_review_only": successor, "planning_permitted_historically": verified["receipt"]["planning_permitted"]})
        for mutation in ("reduced_graph", "swapped_binding", "changed_fact", "changed_authority"):
            changed = copy.deepcopy(records["before-admission.json"])
            if mutation == "reduced_graph":
                changed["graph"]["tasks"].pop()
            elif mutation == "swapped_binding":
                bindings = changed["declaration"]["payload"]["task_bindings"]
                keys = sorted(bindings)
                bindings[keys[0]], bindings[keys[1]] = bindings[keys[1]], bindings[keys[0]]
            elif mutation == "changed_fact":
                changed["evidence"]["match"]["current_facts"][0]["authority"] = "proved"
            else:
                changed["receipt"]["payload"]["execution_authority"] = True
            expected_exceptions = {"reduced_graph": (FiniteRepositoryAdmissionError, LocalPlanningError, PromptGraphError),
                "swapped_binding": (LocalProfileTampered,), "changed_fact": (FiniteRepositoryAdmissionError,),
                "changed_authority": (LocalProfileTampered,)}[mutation]
            try:
                verify_finite_repository_admission(admission=changed)
            except expected_exceptions as exc:
                report["native_controls"].append({"mutation_id": mutation, "outcome": "refused", "exception": type(exc).__name__, "message": str(exc),
                    "expected_exception_types": [kind.__name__ for kind in expected_exceptions]})
            else:
                raise AssertionError("native historical verifier accepted altered signed context")
        report["status"] = "passed"
    except (ImportError, HistoricalReplayRefusal) as exc:
        report.update({"status": "unavailable", "blocker": f"{type(exc).__name__}: {exc}"})
    except Exception as exc:
        report.update({"status": "refused", "blocker": f"{type(exc).__name__}: {exc}"})
    finally:
        try:
            report["retained_producer_comparison"] = retained_producer_comparison(records, finder)
            if snapshot_sha256:
                report["runtime_snapshot_after"] = verify_snapshot_binding(roots, snapshot_sha256)
                report["runtime_snapshot_identity_stable"] = report["runtime_snapshot_after"] == snapshot_before
                if not report["runtime_snapshot_identity_stable"]:
                    raise HistoricalReplayRefusal("historical snapshot identity or verifier bytes changed")
            reads = trace.finish()
            report["read_file_pins"] = reads
            report["read_files_unchanged"] = all(row["unchanged"] for row in reads)
            actual_after = {row["path"]: row["after"] for row in reads}
            report["import_observations"] = {"schema": "codebase-ir-historical-read-only-import-observation@1",
                "core_package_roots": [str(root) for root in roots], "source_bytes_total": finder.total,
                "complete_import_closure_claimed": False,
                "modules": [{"path": path, **value, "after": actual_after[path], "unchanged": value["before"] == actual_after[path]}
                    for path, value in sorted(finder.observations.items())]}
            report["directory_identity_observations"] = []
            for path, before in sorted(trace.directories.items()):
                observed = Path(path).stat(follow_symlinks=False)
                after = observed.st_dev, observed.st_ino, observed.st_mode
                report["directory_identity_observations"].append({"path": path, "before": list(before), "after": list(after),
                                                                "unchanged": before == after})
                if before != after:
                    report.update({"status": "refused", "blocker": "owner directory identity changed during replay"})
            if not report["read_files_unchanged"]:
                report.update({"status": "refused", "blocker": "owner/artifact/import read bytes changed during replay"})
        except (ValueError, OSError) as exc:
            report.update({"status": "refused", "blocker": f"{type(exc).__name__}: {exc}"})
        report["denied_operations"] = trace.denied
        report["elapsed_seconds"] = time.monotonic() - started
        report["maximum_rss_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
        report["runtime_closure_proven"] = False
    return report


def launch_historical_replay(fixture: Path, output: Path, *, python: Path, expected_result_sha256: str,
                             workspace: Path, snapshot_roots: list[Path] | None = None,
                             snapshot_sha256: str | None = None) -> dict[str, Any]:
    command = [str(python.absolute()), "-B", str(Path(__file__).resolve()), "--child", "--fixture-root", str(fixture),
        "--expected-result-sha256", expected_result_sha256, "--workspace", str(workspace.resolve(strict=True))]
    for root in snapshot_roots or []:
        command.extend(["--snapshot-root", str(root)])
    if snapshot_sha256 is not None:
        command.extend(["--snapshot-sha256", snapshot_sha256])
    captured = {"stdout": bytearray(), "stderr": bytearray()}
    report: dict[str, Any] = {"status": "unavailable", "observed_current": False, "current_launch_permission_claimed": False,
        "command": command, "timeout_seconds": TIMEOUT_SECONDS, "max_output_bytes": MAX_OUTPUT_BYTES}
    started = time.monotonic()
    process = subprocess.Popen(command, cwd=output, env={"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C"},
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    selector = selectors.DefaultSelector()
    try:
        for name, stream in (("stdout", process.stdout), ("stderr", process.stderr)):
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, name)
        while selector.get_map():
            if time.monotonic() - started > TIMEOUT_SECONDS:
                raise HistoricalReplayRefusal("fresh-process historical replay timeout")
            for key, _ in selector.select(timeout=0.1):
                chunk = os.read(key.fileobj.fileno(), 65536)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                captured[key.data].extend(chunk)
                if len(captured[key.data]) > MAX_OUTPUT_BYTES:
                    raise HistoricalReplayRefusal("fresh-process historical replay output cap")
        process.wait(timeout=max(0.1, TIMEOUT_SECONDS - (time.monotonic() - started)))
        if process.returncode != 0:
            report["blocker"] = "fresh-process verifier exited " + str(process.returncode)
        else:
            report.update(json.loads(captured["stdout"]))
    except (ValueError, OSError, HistoricalReplayRefusal, subprocess.TimeoutExpired) as exc:
        report["blocker"] = f"{type(exc).__name__}: {exc}"
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=5)
        selector.close()
        for stream in (process.stdout, process.stderr):
            if stream is not None:
                stream.close()
        for name, raw in captured.items():
            (output / ("historical_replay." + name)).write_bytes(bytes(raw[:MAX_OUTPUT_BYTES]))
        report["child_returncode"] = process.returncode
        report["parent_elapsed_seconds"] = time.monotonic() - started
        (output / "historical_replay.json").write_bytes(canonical(report) + b"\n")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--child", action="store_true", required=True)
    parser.add_argument("--fixture-root", type=Path, required=True)
    parser.add_argument("--expected-result-sha256", required=True)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--snapshot-root", type=Path, action="append")
    parser.add_argument("--snapshot-sha256")
    args = parser.parse_args()
    try:
        report = child_replay(args.fixture_root, args.expected_result_sha256, workspace=args.workspace,
            snapshot_roots=args.snapshot_root, snapshot_sha256=args.snapshot_sha256)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        report = {"schema": "codebase-ir-owner-local-historical-replay@1", "status": "unavailable",
            "blocker": f"{type(exc).__name__}: {exc}", "observed_current": False, "current_launch_permission_claimed": False,
            "native_observation_or_proof_invoked": False, "worker_launched": False, "task_store_opened": False,
            "requested_runtime_snapshot_sha256": args.snapshot_sha256, "runtime_snapshot_roots": [str(root) for root in args.snapshot_root or []]}
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
