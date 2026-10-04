#!/usr/bin/env python3
"""Read-only, bounded Python dependency and release inclusion qualification."""

from __future__ import annotations

import argparse
import ast
import collections
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

SCHEMA = "codebase-ir-release-audit/v1"


class SourceBoundError(ValueError):
    def __init__(self, size: int, limit: int):
        super().__init__(f"source size {size} exceeds remaining byte limit {limit}")
        self.size = size


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def git(root: Path, *args: str) -> bytes:
    env = {**os.environ, "GIT_OPTIONAL_LOCKS": "0"}
    return subprocess.check_output(["git", "-C", str(root), *args], env=env, stderr=subprocess.PIPE)


class Repository:
    """One working checkout or immutable Git tree; no target import occurs here."""

    def __init__(self, name: str, root: Path, packages: list[str], ref: str | None = None):
        self.name, self.root, self.packages, self.ref = name, root.resolve(), packages, ref
        self.head = git(self.root, "rev-parse", "HEAD").decode().strip()
        self.commit = (
            git(self.root, "rev-parse", "--verify", f"{ref}^{{commit}}").decode().strip()
            if ref
            else self.head
        )
        raw = git(self.root, "ls-tree", "-r", "-l", "-z", "--full-tree", self.commit)
        self.tree: dict[str, tuple[str, str, int]] = {}
        for entry in raw.split(b"\0"):
            if entry:
                meta, path = entry.split(b"\t", 1)
                mode, kind, oid, size = meta.decode().split()
                if kind == "blob":
                    self.tree[os.fsdecode(path)] = (mode, oid, int(size))
        self.index: dict[str, list[dict]] = {}
        for entry in git(self.root, "ls-files", "--stage", "-z").split(b"\0"):
            if entry:
                meta, path = entry.split(b"\t", 1)
                mode, oid, stage = meta.decode().split()
                self.index.setdefault(os.fsdecode(path), []).append(
                    {"mode": mode, "git_blob_oid": oid, "stage": int(stage)}
                )
        self.tracked = set(self.index)
        self.directories = {
            str(parent) for path in self.tree for parent in Path(path).parents if str(parent) != "."
        }
        self._batch: subprocess.Popen | None = None

    def has(self, path: str) -> bool:
        if self.ref:
            return path in self.tree and self.tree[path][0] != "120000"
        target = self.root / path
        return (
            target.is_file()
            and not target.is_symlink()
            and target.resolve().is_relative_to(self.root)
        )

    def is_directory(self, path: str) -> bool:
        if self.ref:
            return path in self.directories
        target = self.root / path
        return (
            target.is_dir()
            and not target.is_symlink()
            and target.resolve().is_relative_to(self.root)
        )

    def read(self, path: str, limit: int | None = None) -> bytes:
        if not self.ref:
            target = self.root / path
            size = target.stat().st_size
            if limit is not None and size > limit:
                raise SourceBoundError(size, limit)
            with target.open("rb") as stream:
                data = stream.read(limit + 1 if limit is not None else -1)
            if limit is not None and len(data) > limit:
                raise SourceBoundError(len(data), limit)
            return data
        return self.read_tree(path, limit)

    def read_tree(self, path: str, limit: int | None = None) -> bytes:
        size = self.tree[path][2]
        if limit is not None and size > limit:
            raise SourceBoundError(size, limit)
        if self._batch is None:
            self._batch = subprocess.Popen(
                ["git", "-C", str(self.root), "cat-file", "--batch"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
            )
        assert self._batch.stdin is not None and self._batch.stdout is not None
        self._batch.stdin.write((self.tree[path][1] + "\n").encode())
        self._batch.stdin.flush()
        header = self._batch.stdout.readline().decode().split()
        if len(header) != 3 or header[1] != "blob":
            raise ValueError(f"unexpected git object header: {header}")
        remaining = int(header[2])
        parts = []
        while remaining:
            part = self._batch.stdout.read(remaining)
            if not part:
                raise ValueError("truncated git object")
            remaining -= len(part)
            parts.append(part)
        if self._batch.stdout.read(1) != b"\n":
            raise ValueError("invalid git object terminator")
        return b"".join(parts)

    def close(self) -> None:
        if self._batch is not None:
            self._batch.stdin.close()
            self._batch.stdout.close()
            self._batch.wait(timeout=5)
            self._batch = None

    def identity(self) -> dict:
        return {
            "name": self.name,
            "root": str(self.root),
            "requested_ref": self.ref,
            "observed_head": self.head,
            "resolved_commit": self.commit,
            "packages": self.packages,
        }


class Imports(ast.NodeVisitor):
    """Retain lexical conditions rather than silently discard optional imports."""

    def __init__(self, module: str, package: bool):
        self.module = module
        self.package = module if package else module.rpartition(".")[0]
        self.scope: list[str] = []
        self.rows: list[dict] = []
        self.dynamic: list[dict] = []
        self.importlib_aliases = {"importlib"}
        self.import_module_aliases: set[str] = set()

    def scoped(self, node: ast.AST, label: str) -> None:
        self.scope.append(label)
        self.generic_visit(node)
        self.scope.pop()

    def visit_FunctionDef(self, node):
        self.scoped(node, f"function:{node.name}")

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node):
        self.scoped(node, f"class:{node.name}")

    def visit_If(self, node):
        self.scoped(node, f"if:{ast.unparse(node.test)[:200]}")

    def visit_Try(self, node):
        self.scoped(node, "try:possibly_optional")

    visit_TryStar = visit_Try

    def add(self, node, module: str, kind: str, symbols: list[str] | None = None) -> None:
        self.rows.append(
            {
                "line": node.lineno,
                "scope": list(self.scope),
                "module": module,
                "kind": kind,
                "symbols": symbols or [],
            }
        )

    def visit_Import(self, node):
        for alias in node.names:
            self.add(node, alias.name, "import")
            if alias.name == "importlib":
                self.importlib_aliases.add(alias.asname or alias.name)

    def relative(self, name: str, level: int) -> str | None:
        parts = self.package.split(".") if self.package else []
        if level > len(parts):
            return None
        prefix = parts[: len(parts) - level + 1]
        return ".".join(prefix + (name.split(".") if name else []))

    def visit_ImportFrom(self, node):
        module = self.relative(node.module or "", node.level) if node.level else node.module or ""
        if module is None:
            self.dynamic.append(
                {
                    "line": node.lineno,
                    "scope": list(self.scope),
                    "kind": "invalid_relative_import",
                    "expression": ast.unparse(node),
                }
            )
            return
        self.add(node, module, "from", [alias.name for alias in node.names])
        if module == "importlib":
            for alias in node.names:
                if alias.name == "import_module":
                    self.import_module_aliases.add(alias.asname or alias.name)

    def visit_Call(self, node):
        func = node.func
        is_dynamic = isinstance(func, ast.Name) and (
            func.id == "__import__" or func.id in self.import_module_aliases
        )
        is_dynamic |= (
            isinstance(func, ast.Attribute)
            and func.attr == "import_module"
            and isinstance(func.value, ast.Name)
            and func.value.id in self.importlib_aliases
        )
        if is_dynamic:
            name = (
                node.args[0].value
                if node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
                else None
            )
            if name and not name.startswith("."):
                self.add(node, name, "dynamic_literal")
            else:
                self.dynamic.append(
                    {
                        "line": node.lineno,
                        "scope": list(self.scope),
                        "kind": "dynamic_import_unresolved",
                        "expression": ast.unparse(node)[:1000],
                    }
                )
        if isinstance(func, ast.Name) and func.id in {"exec", "eval"}:
            self.dynamic.append(
                {
                    "line": node.lineno,
                    "scope": list(self.scope),
                    "kind": "runtime_code_unresolved",
                    "expression": ast.unparse(node)[:1000],
                }
            )
        self.generic_visit(node)


class Closure:
    def __init__(
        self,
        repositories: list[Repository],
        max_modules: int = 1200,
        max_bytes: int = 32 * 1024 * 1024,
        max_file_bytes: int = 2 * 1024 * 1024,
    ):
        self.repositories = {r.name: r for r in repositories}
        self.max_modules, self.max_bytes, self.max_file_bytes = (
            max_modules,
            max_bytes,
            max_file_bytes,
        )
        self.nodes: dict[tuple[str, str], dict] = {}
        self.captured: dict[tuple[str, str], bytes] = {}
        self.frontier: list[dict] = []
        self.edges: list[dict] = []
        self.queue: collections.deque = collections.deque()
        self.queued: set[tuple[str, str]] = set()
        self.total_bytes = 0
        self.candidate_cache: dict[str, list] = {}

    def candidates(self, module: str) -> list[tuple[Repository, str | None, bool]]:
        if module in self.candidate_cache:
            return self.candidate_cache[module]
        if not module or any(not p.isidentifier() for p in module.split(".")):
            return []
        base = module.replace(".", "/")
        found = []
        owners = [r for r in self.repositories.values() if module.split(".")[0] in r.packages]
        for repo in owners or self.repositories.values():
            if repo.has(base + ".py"):
                found.append((repo, base + ".py", False))
            elif repo.has(base + "/__init__.py"):
                found.append((repo, base + "/__init__.py", True))
            elif repo.is_directory(base):
                found.append((repo, None, True))
        self.candidate_cache[module] = found
        return found

    def local_name(self, module: str) -> bool:
        return any(module.split(".")[0] in r.packages for r in self.repositories.values())

    def enqueue(self, repo: Repository, path: str, module: str, package: bool) -> None:
        key = (repo.name, path)
        if key not in self.queued:
            self.queued.add(key)
            self.queue.append((repo, path, module, package))

    def resolve(self, module: str, importer: dict, *, optional_symbol: bool = False) -> dict:
        found = self.candidates(module)
        row = {**importer, "module": module}
        # Importing an absent child still executes existing ancestor packages.
        # Keep these initializers even when a seed itself is absent in a release.
        owners = [r for r in self.repositories.values() if module.split(".")[0] in r.packages]
        if len(owners) == 1:
            parts = module.split(".")
            for i in range(1, len(parts)):
                init = "/".join(parts[:i]) + "/__init__.py"
                if owners[0].has(init):
                    self.enqueue(owners[0], init, ".".join(parts[:i]), True)
        if len(found) > 1:
            row.update(
                disposition="ambiguous_local_module",
                candidates=[{"repository": r.name, "path": p} for r, p, _ in found],
            )
            self.frontier.append(row)
        elif found:
            repo, path, package = found[0]
            row.update(
                disposition="local" if path else "namespace_package",
                repository=repo.name,
                path=path,
            )
            # Python executes every regular ancestor package initializer.
            parts = module.split(".")
            for i in range(1, len(parts)):
                init = "/".join(parts[:i]) + "/__init__.py"
                if repo.has(init):
                    self.enqueue(repo, init, ".".join(parts[:i]), True)
            if path:
                self.enqueue(repo, path, module, package)
        elif optional_symbol:
            row["disposition"] = "attribute_or_unresolved_submodule"
        elif self.local_name(module):
            row["disposition"] = "missing_local_module"
            self.frontier.append(row)
        else:
            row["disposition"] = (
                "stdlib"
                if module.split(".")[0] in sys.stdlib_module_names or module == "__future__"
                else "external_dependency_unresolved"
            )
        self.edges.append(row)
        return row

    def run(self, seeds: list[str]) -> dict:
        for seed in seeds:
            self.resolve(seed, {"importer": None, "line": None, "scope": [], "kind": "seed"})
        while self.queue:
            repo, path, module, package = self.queue.popleft()
            key = (repo.name, path)
            if len(self.nodes) >= self.max_modules:
                self.frontier.append(
                    {
                        "repository": repo.name,
                        "path": path,
                        "module": module,
                        "disposition": "module_limit",
                    }
                )
                continue
            try:
                data = repo.read(path, min(self.max_file_bytes, self.max_bytes - self.total_bytes))
            except SourceBoundError as exc:
                self.frontier.append(
                    {
                        "repository": repo.name,
                        "path": path,
                        "module": module,
                        "disposition": "byte_limit",
                        "bytes": exc.size,
                    }
                )
                continue
            except (OSError, ValueError) as exc:
                self.frontier.append(
                    {
                        "repository": repo.name,
                        "path": path,
                        "module": module,
                        "disposition": "source_read_error",
                        "error": str(exc),
                    }
                )
                continue
            if len(data) > self.max_file_bytes or self.total_bytes + len(data) > self.max_bytes:
                self.frontier.append(
                    {
                        "repository": repo.name,
                        "path": path,
                        "module": module,
                        "disposition": "byte_limit",
                        "bytes": len(data),
                    }
                )
                continue
            self.captured[key] = data
            self.total_bytes += len(data)
            entry = {
                "repository": repo.name,
                "path": path,
                "module": module,
                "package_initializer": package,
                "bytes": len(data),
                "sha256": digest(data),
            }
            if repo.ref:
                entry["git_status"] = "tracked_tree"
            else:
                tracked = path in repo.tracked
                entry["git_index_entries"] = repo.index.get(path, [])
                if path in repo.tree and repo.tree[path][0] != "120000":
                    try:
                        head_digest = digest(repo.read_tree(path, self.max_file_bytes))
                        entry["head_sha256"] = head_digest
                        index_clean = repo.index.get(path) == [
                            {
                                "mode": repo.tree[path][0],
                                "git_blob_oid": repo.tree[path][1],
                                "stage": 0,
                            }
                        ]
                        mode_clean = bool((repo.root / path).stat().st_mode & 0o111) == (
                            repo.tree[path][0] == "100755"
                        )
                        entry["git_status"] = (
                            "tracked_clean"
                            if tracked
                            and index_clean
                            and mode_clean
                            and head_digest == entry["sha256"]
                            else "tracked_dirty"
                            if tracked
                            else "untracked_matches_head"
                        )
                    except SourceBoundError:
                        entry["head_comparison_unavailable"] = "head_blob_exceeds_file_bound"
                        entry["git_status"] = (
                            "tracked_comparison_unavailable" if tracked else "untracked"
                        )
                else:
                    entry["git_status"] = "tracked_added" if tracked else "untracked"
            self.nodes[key] = entry
            try:
                tree = ast.parse(data, filename=path)
            except (SyntaxError, ValueError, UnicodeError, RecursionError) as exc:
                entry["syntax_error"] = {
                    "type": type(exc).__name__,
                    "message": str(exc),
                    "line": getattr(exc, "lineno", None),
                }
                self.frontier.append(
                    {
                        "repository": repo.name,
                        "path": path,
                        "module": module,
                        "disposition": "syntax_error",
                    }
                )
                continue
            visitor = Imports(module, package)
            try:
                visitor.visit(tree)
            except (RecursionError, ValueError) as exc:
                entry["ast_analysis_error"] = {"type": type(exc).__name__, "message": str(exc)}
                self.frontier.append(
                    {
                        "repository": repo.name,
                        "path": path,
                        "module": module,
                        "disposition": "ast_analysis_error",
                    }
                )
                continue
            importer = {"importer": f"{repo.name}:{path}"}
            for imp in visitor.rows:
                base = self.resolve(imp["module"], {**importer, **imp})
                if imp["kind"] == "from" and base["disposition"] in {"local", "namespace_package"}:
                    for symbol in imp["symbols"]:
                        if symbol == "*":
                            self.frontier.append(
                                {**importer, **imp, "disposition": "star_export_unresolved"}
                            )
                        else:
                            self.resolve(
                                imp["module"] + "." + symbol,
                                {**importer, **imp, "kind": "from_symbol"},
                                optional_symbol=True,
                            )
            self.frontier.extend(
                {**importer, **row, "disposition": row["kind"]} for row in visitor.dynamic
            )
        structural_gaps = {
            "missing_local_module",
            "source_read_error",
            "module_limit",
            "byte_limit",
            "syntax_error",
            "ambiguous_local_module",
            "invalid_relative_import",
            "ast_analysis_error",
        }
        return {
            "schema": SCHEMA,
            "seeds": seeds,
            "repositories": [r.identity() for r in self.repositories.values()],
            "bounds": {
                "max_modules": self.max_modules,
                "max_bytes": self.max_bytes,
                "max_file_bytes": self.max_file_bytes,
            },
            "files": sorted(self.nodes.values(), key=lambda x: (x["repository"], x["path"])),
            "imports": self.edges,
            "frontier": self.frontier,
            "static_closure_complete": not any(
                x["disposition"] in structural_gaps for x in self.frontier
            ),
            "runtime_closure_proven": False,
            "total_bytes": self.total_bytes,
            "limitations": [
                "All lexical static imports, including optional branches and function bodies, are included; this is a conservative union rather than a runtime trace.",
                "Dynamic imports, star exports, attribute-versus-submodule ambiguity, non-Python package assets and extension modules remain explicit limitations.",
            ],
        }

    def stability(self) -> dict:
        rows = []
        for (name, path), data in sorted(self.captured.items()):
            repo = self.repositories[name]
            if repo.ref:
                continue
            try:
                after = repo.read(path, self.max_file_bytes)
                rows.append(
                    {
                        "repository": name,
                        "path": path,
                        "before_sha256": digest(data),
                        "after_sha256": digest(after),
                        "stable": after == data,
                    }
                )
            except (OSError, ValueError) as exc:
                rows.append(
                    {
                        "repository": name,
                        "path": path,
                        "before_sha256": digest(data),
                        "after_sha256": None,
                        "stable": False,
                        "error": str(exc),
                    }
                )
        heads = [
            {
                "repository": r.name,
                "before": r.head,
                "after": git(r.root, "rev-parse", "HEAD").decode().strip(),
            }
            for r in self.repositories.values()
            if not r.ref
        ]
        return {
            "files": rows,
            "heads": heads,
            "stable": all(x["stable"] for x in rows)
            and all(x["before"] == x["after"] for x in heads),
            "atomic_capture_claim": False,
        }


def compare_files(current: dict, other: dict) -> dict:
    a = {(x["repository"], x["path"]): x for x in current["files"]}
    b = {(x["repository"], x["path"]): x for x in other["files"]}
    rows = []
    for key in sorted(a.keys() | b.keys()):
        disposition = (
            "absent_in_reference_closure"
            if key not in b
            else "reference_only_dependency"
            if key not in a
            else "identical"
            if a[key]["sha256"] == b[key]["sha256"]
            else "different_bytes"
        )
        rows.append(
            {
                "repository": key[0],
                "path": key[1],
                "disposition": disposition,
                "working_sha256": a.get(key, {}).get("sha256"),
                "reference_sha256": b.get(key, {}).get("sha256"),
            }
        )
    return {
        "files": rows,
        "counts": dict(sorted(collections.Counter(x["disposition"] for x in rows).items())),
        "reference_static_closure_complete": other["static_closure_complete"],
    }


def file_inclusion(current: dict, closure: Closure) -> dict:
    """Check release file presence independently of dependency reachability."""
    rows, observed, used, reused = [], {}, 0, 0
    for node in current["files"]:
        repo = closure.repositories[node["repository"]]
        path = node["path"]
        row = {"repository": repo.name, "path": path, "working_sha256": node["sha256"]}
        if not repo.has(path):
            row.update(disposition="missing_in_reference_source", reference_sha256=None)
        else:
            data = closure.captured.get((repo.name, path))
            from_capture = data is not None
            if data is None:
                try:
                    data = repo.read(path, min(closure.max_file_bytes, closure.max_bytes - used))
                except SourceBoundError:
                    row["disposition"] = "not_compared_byte_limit"
                except (OSError, ValueError) as exc:
                    row.update(disposition="reference_read_error", error=str(exc))
            if data is not None:
                if from_capture:
                    reused += len(data)
                else:
                    used += len(data)
                hashed = digest(data)
                row.update(
                    disposition="identical" if hashed == node["sha256"] else "different_bytes",
                    reference_sha256=hashed,
                    in_reference_dependency_closure=(repo.name, path) in closure.captured,
                )
                if not repo.ref:
                    observed[(repo.name, path)] = hashed
        rows.append(row)
    changed = []
    for (name, path), hashed in sorted(observed.items()):
        repo = closure.repositories[name]
        try:
            after = digest(repo.read(path, closure.max_file_bytes))
        except (OSError, ValueError):
            after = None
        if after != hashed:
            changed.append(
                {"repository": name, "path": path, "before_sha256": hashed, "after_sha256": after}
            )
    return {
        "files": rows,
        "counts": dict(sorted(collections.Counter(x["disposition"] for x in rows).items())),
        "comparison_bytes": used,
        "reused_capture_bytes": reused,
        "comparison_bound_bytes": closure.max_bytes,
        "reference_source_changed_after_read": changed,
        "reference_source_stable": not changed,
    }


def snapshot(closure: Closure, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=False)
    rows = []
    for (repo, path), data in sorted(closure.captured.items()):
        target = output / repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        target.chmod(0o444)
        rows.append({"repository": repo, "path": path, "sha256": digest(data), "bytes": len(data)})
    manifest = {
        "schema": SCHEMA,
        "source": "captured_closure_bytes",
        "files": rows,
        "manifest_sha256": digest(json_bytes(rows)),
    }
    (output / "snapshot.json").write_bytes(json_bytes(manifest))
    (output / "snapshot.json").chmod(0o444)
    # Snapshot directories are read-only. Import probes use separate private state.
    for directory in sorted((x for x in output.rglob("*") if x.is_dir()), reverse=True):
        directory.chmod(0o555)
    output.chmod(0o555)
    return manifest


def probe_import(
    module: str,
    snapshot_root: Path,
    repo_names: list[str],
    local_packages: list[str],
    output: Path,
    timeout: float = 5,
    request_identity: dict | None = None,
    allow_ctypes_python_handle: bool = False,
) -> dict:
    output.mkdir(parents=True, exist_ok=False)
    state = output / "state"
    state.mkdir()
    payload = {
        "module": module,
        "snapshot_roots": [str((snapshot_root / r).resolve()) for r in repo_names],
        "local_packages": local_packages,
        "state": str(state.resolve()),
    }
    if request_identity is not None:
        payload["request_identity"] = request_identity
    payload["allow_ctypes_python_handle"] = allow_ctypes_python_handle
    request = output / "request.json"
    request.write_bytes(json_bytes(payload))
    env = {
        "PATH": os.defpath,
        "TMPDIR": str(state),
        "XDG_CACHE_HOME": str(state / "cache"),
        "XDG_DATA_HOME": str(state / "data"),
        "XDG_CONFIG_HOME": str(state / "config"),
        "PYTHONDONTWRITEBYTECODE": "1",
        "IPFS_DATASETS_AUTO_INSTALL": "0",
        "IPFS_KIT_AUTO_INSTALL_DEPS": "0",
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
    }
    command = [
        sys.executable,
        "-I",
        "-S",
        "-B",
        str(Path(__file__).with_name("probe.py").resolve()),
        str(request.resolve()),
    ]
    started = time.monotonic()
    with (output / "stdout.txt").open("wb") as stdout, (output / "stderr.txt").open("wb") as stderr:
        process = subprocess.Popen(
            command, cwd=state, env=env, stdout=stdout, stderr=stderr, start_new_session=True
        )
        timed_out = False
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=5)
    result_path = state / "result.json"
    result = (
        json.loads(result_path.read_text())
        if result_path.exists()
        else {"disposition": "timeout" if timed_out else "probe_process_failure"}
    )
    result.update(
        module=module,
        timeout_seconds=timeout,
        timed_out=timed_out,
        returncode=process.returncode,
        elapsed_seconds=round(time.monotonic() - started, 6),
        isolated=True,
        site_packages_enabled=False,
        snapshot_root=str(snapshot_root),
        command=command,
    )
    (output / "result.json").write_bytes(json_bytes(result))
    return result


def annotate_probe(result: dict, closure: Closure) -> dict:
    missing = result.get("missing_module")
    if result.get("disposition") == "absent_local_module" and missing:
        candidates = closure.candidates(missing)
        result["exists_in_reference_source"] = bool(candidates)
        if candidates:
            causes = [
                x["disposition"]
                for x in closure.frontier
                if x.get("module") == missing
                and x["disposition"]
                in {"module_limit", "byte_limit", "ambiguous_local_module", "source_read_error"}
            ]
            result["snapshot_frontier_causes"] = causes
            result["disposition"] = (
                "incomplete_snapshot" if causes else "unresolved_dynamic_dependency"
            )
    return result


def make_repositories(config: dict, mode: str) -> list[Repository]:
    result = []
    try:
        for spec in config["repositories"]:
            root = Path(spec["root"])
            ref = None
            if mode == "head":
                ref = git(root, "rev-parse", "HEAD").decode().strip()
            elif mode == "released_ref":
                ref = spec["released_ref"]
            elif mode == "released_checkout":
                root = Path(spec["released_checkout"])
            result.append(Repository(spec["name"], root, spec["packages"], ref))
    except Exception:
        for repo in result:
            repo.close()
        raise
    return result


def run(
    config: dict,
    output: Path,
    *,
    with_snapshot: bool = False,
    with_probes: bool = False,
    import_timeout: float = 5,
    max_modules: int | None = None,
    max_bytes: int | None = None,
) -> dict:
    if not output.parent.exists():
        output.parent.mkdir(parents=True)
    output.mkdir(exist_ok=False)
    (output / "config.json").write_bytes(json_bytes(config))
    limits = config.get("bounds", {})
    limits = {
        "max_modules": max_modules or limits.get("max_modules", 1200),
        "max_bytes": max_bytes or limits.get("max_bytes", 32 * 1024 * 1024),
        "max_file_bytes": limits.get("max_file_bytes", 2 * 1024 * 1024),
    }
    views, observations, comparisons = {}, {}, {}
    modes = ["working", "head"] + [
        m
        for m in ("released_ref", "released_checkout")
        if all(m in s for s in config["repositories"])
    ]
    for mode in modes:
        repos = []
        try:
            repos = make_repositories(config, mode)
            closure = Closure(repos, **limits)
            manifest = closure.run(config["seeds"])
            stability_before_probes = closure.stability()
            manifest["source_stability"] = stability_before_probes
            views[mode] = manifest
            if mode != "working" and "working" in views:
                comparisons[mode] = file_inclusion(views["working"], closure)
                comparisons[mode]["dependency_closure_changes"] = compare_files(
                    views["working"], manifest
                )
                (output / f"working_vs_{mode}.json").write_bytes(json_bytes(comparisons[mode]))
            (output / f"{mode}.json").write_bytes(json_bytes(manifest))
            observations[mode] = {
                "files": len(manifest["files"]),
                "bytes": manifest["total_bytes"],
                "static_closure_complete": manifest["static_closure_complete"],
                "frontier_counts": dict(
                    sorted(
                        collections.Counter(x["disposition"] for x in manifest["frontier"]).items()
                    )
                ),
                "git_status_counts": dict(
                    sorted(collections.Counter(x["git_status"] for x in manifest["files"]).items())
                ),
                "source_stable": stability_before_probes["stable"],
                "repositories": manifest["repositories"],
            }
            if with_snapshot or with_probes:
                snapshot(closure, output / "snapshots" / mode)
                if with_probes:
                    observations[mode]["imports"] = [
                        annotate_probe(
                            probe_import(
                                module,
                                output / "snapshots" / mode,
                                [r.name for r in repos],
                                [p for r in repos for p in r.packages],
                                output / "probes" / mode / f"{i:02d}",
                                import_timeout,
                            ),
                            closure,
                        )
                        for i, module in enumerate(config.get("probe_seeds", config["seeds"]))
                    ]
            manifest["source_stability_after_probes"] = closure.stability()
            observations[mode]["source_stable_after_probes"] = manifest[
                "source_stability_after_probes"
            ]["stable"]
            (output / f"{mode}.json").write_bytes(json_bytes(manifest))
        except (OSError, subprocess.SubprocessError, ValueError, KeyError) as exc:
            observations[mode] = {"disposition": "unavailable", "error": str(exc)}
        finally:
            for repo in repos:
                repo.close()
    review = config.get("integration_review")
    reviewed_sources = []
    if review and Path(review).exists():
        data = Path(review).read_bytes()
        (output / "integration_review.json").write_bytes(data)
        record = json.loads(data)
        lookup = {
            (x["repository"], x["path"]): x for x in views.get("working", {}).get("files", [])
        }
        for name, source in sorted(record.get("sources", {}).items()):
            repo_name = "datasets" if "datasets" in name else "accelerate"
            for item in source.get("files", []):
                current = (
                    lookup.get((repo_name, item["path"])) if name.startswith("working_") else None
                )
                reviewed_sources.append(
                    {
                        "review_group": name,
                        "reviewed_head": source.get("head"),
                        "repository": repo_name,
                        "path": item["path"],
                        "reviewed_sha256": item["sha256"],
                        "current_working_sha256": current.get("sha256") if current else None,
                        "matches_working_capture": current["sha256"] == item["sha256"]
                        if current
                        else None,
                    }
                )
    summary = {
        "schema": SCHEMA,
        "observations": observations,
        "comparison_counts": {m: c["counts"] for m, c in comparisons.items()},
        "reviewed_sources": reviewed_sources,
        "release_integration_gate_closed": False,
        "reason": "Read-only qualification inventories pinned dependency closures and bounded imports; it does not integrate or release working source.",
        "output": str(output.resolve()),
    }
    (output / "summary.json").write_bytes(json_bytes(summary))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="New private run directory; existing directories are refused",
    )
    parser.add_argument("--snapshot", action="store_true")
    parser.add_argument("--probe-imports", action="store_true")
    parser.add_argument("--import-timeout", type=float, default=5)
    parser.add_argument("--max-modules", type=int)
    parser.add_argument("--max-bytes", type=int)
    args = parser.parse_args()
    if (
        args.import_timeout <= 0
        or args.import_timeout > 30
        or (args.max_modules is not None and args.max_modules < 1)
        or (args.max_bytes is not None and args.max_bytes < 1)
    ):
        parser.error("bounds must be positive; import timeout must be at most 30 seconds")
    summary = run(
        json.loads(args.config.read_text()),
        args.output,
        with_snapshot=args.snapshot,
        with_probes=args.probe_imports,
        import_timeout=args.import_timeout,
        max_modules=args.max_modules,
        max_bytes=args.max_bytes,
    )
    print(
        json.dumps(
            {
                "output": summary["output"],
                "observations": {
                    k: {a: b for a, b in v.items() if a not in {"imports", "repositories"}}
                    for k, v in summary["observations"].items()
                },
                "comparison_counts": summary["comparison_counts"],
            },
            sort_keys=True,
            indent=2,
        )
    )
    return (
        0
        if "working" in summary["observations"]
        and summary["observations"]["working"].get("disposition") != "unavailable"
        else 2
    )


if __name__ == "__main__":
    raise SystemExit(main())
