#!/usr/bin/env python3
"""Import probe run only by audit.py in an isolated standard-library process."""

from __future__ import annotations

import importlib
import importlib.abc
import importlib.machinery
import json
import os
import resource
import sys
import sysconfig
import traceback
from pathlib import Path


def main() -> int:
    request = json.loads(Path(sys.argv[1]).read_text())
    roots = [Path(x).resolve() for x in request["snapshot_roots"]]
    state = Path(request["state"]).resolve()
    local = set(request["local_packages"])
    # -I -S removes cwd, PYTHONPATH, user site and installed site packages.
    # Retain only CPython's standard library and the explicitly sealed roots.
    stdlib = Path(sysconfig.get_path("stdlib")).resolve()
    safe_stdlib = [
        p
        for p in sys.path
        if p
        and "site-packages" not in p
        and "dist-packages" not in p
        and (
            Path(p).resolve().is_relative_to(stdlib)
            or Path(p).name.startswith("python")
            and Path(p).suffix == ".zip"
        )
    ]
    sys.path[:] = [str(p) for p in roots] + safe_stdlib
    sys.dont_write_bytecode = True
    resource.setrlimit(resource.RLIMIT_CPU, (15, 15))
    resource.setrlimit(resource.RLIMIT_AS, (768 * 1024 * 1024, 768 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_FSIZE, (2 * 1024 * 1024, 2 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_NOFILE, (128, 128))
    attempts = []
    forbidden = []
    missing_assets = []
    allowed_native_handles = []

    def allowed_read(path: Path) -> bool:
        return (
            any(path.is_relative_to(root) for root in roots)
            or path.is_relative_to(state)
            or path.is_relative_to(stdlib)
            or path.name.startswith("python")
            and path.suffix == ".zip"
            and path.parent == stdlib.parent
        )

    def audit(event, args):
        if event == "open" and args and isinstance(args[0], str | bytes | os.PathLike):
            path = Path(os.fsdecode(args[0])).resolve()
            mode = args[1] or ""
            flags = args[2] if len(args) > 2 and isinstance(args[2], int) else 0
            writing = any(c in str(mode) for c in "wax+") or bool(
                flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)
            )
            if not (path.is_relative_to(state) if writing else allowed_read(path)):
                forbidden.append({"event": event, "path": str(path), "writing": writing})
                raise PermissionError(
                    f"probe refuses file access outside snapshot/private state/stdlib: {path}"
                )
            if (
                not writing
                and any(path.is_relative_to(root) for root in roots)
                and not path.exists()
            ):
                missing_assets.append({"path": str(path), "disposition": "missing_snapshot_asset"})
        if (
            event == "ctypes.dlopen"
            and args
            and args[0] is None
            and request.get("allow_ctypes_python_handle") is True
        ):
            allowed_native_handles.append(
                {"event": event, "library": None, "scope": "current_process_python_api"}
            )
            return
        if event.startswith("socket.") or event in {
            "subprocess.Popen",
            "os.system",
            "os.posix_spawn",
            "os.exec",
            "ctypes.dlopen",
        }:
            forbidden.append({"event": event})
            raise PermissionError(f"probe refuses runtime side effect: {event}")
        if event in {
            "os.mkdir",
            "os.remove",
            "os.rmdir",
            "os.rename",
            "os.link",
            "os.symlink",
            "os.chmod",
            "os.truncate",
        }:
            # Only private state paths may be mutated. No target source is changed.
            count = 2 if event in {"os.rename", "os.link", "os.symlink"} else 1
            for argument in args[:count]:
                if isinstance(argument, str | bytes | os.PathLike) and not Path(
                    os.fsdecode(argument)
                ).resolve().is_relative_to(state):
                    forbidden.append({"event": event, "path": os.fsdecode(argument)})
                    raise PermissionError(f"probe refuses filesystem mutation: {event}")

    class SnapshotFinder(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if fullname.split(".")[0] not in local:
                return None
            spec = importlib.machinery.PathFinder.find_spec(fullname, path)
            if spec is None:
                attempts.append({"module": fullname, "disposition": "absent_local_module"})
                raise ModuleNotFoundError(
                    f"local module absent from sealed snapshot: {fullname}", name=fullname
                )
            locations = (
                [spec.origin]
                if spec.origin and spec.origin not in {"built-in", "frozen"}
                else list(spec.submodule_search_locations or [])
            )
            if any(
                not any(Path(location).resolve().is_relative_to(root) for root in roots)
                for location in locations
            ):
                forbidden.append(
                    {"event": "local_module_fallback", "module": fullname, "locations": locations}
                )
                raise ImportError(f"local module resolved outside sealed snapshot: {fullname}")
            attempts.append({"module": fullname, "disposition": "snapshot", "locations": locations})
            return spec

    sys.meta_path.insert(0, SnapshotFinder())
    sys.addaudithook(audit)
    result = {
        "module": request["module"],
        "isolated_sys_path": list(sys.path),
        "local_import_attempts": attempts,
        "forbidden_operations": forbidden,
        "missing_snapshot_assets": missing_assets,
        "request_identity": request.get("request_identity"),
        "allowed_native_handles": allowed_native_handles,
        "environment_profile": {
            "site_packages": False,
            "allow_ctypes_python_handle": request.get("allow_ctypes_python_handle") is True,
            "named_ctypes_libraries": False,
        },
        "resources": {
            "cpu_seconds": 15,
            "address_space_bytes": 768 * 1024 * 1024,
            "output_file_bytes": 2 * 1024 * 1024,
            "open_files": 128,
        },
    }
    try:
        importlib.import_module(request["module"])
        result["disposition"] = "imported"
    except Exception as exc:
        missing = exc.name if isinstance(exc, ModuleNotFoundError) else None
        result.update(
            disposition="absent_local_module"
            if missing and missing.split(".")[0] in local
            else "environment_unavailable"
            if missing
            else "isolated_import_error",
            error_type=type(exc).__name__,
            error=str(exc),
            missing_module=missing,
            traceback=traceback.format_exc(),
        )
    result["resolved_local_modules"] = [
        {
            "module": name,
            "file": getattr(module, "__file__", None),
            "path": list(getattr(module, "__path__", [])),
        }
        for name, module in sorted(sys.modules.items())
        if name.split(".")[0] in local
    ]
    (state / "result.json").write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
