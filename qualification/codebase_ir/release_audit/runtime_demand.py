#!/usr/bin/env python3
"""Seal bounded runtime-demand dependency generations between isolated probes."""

from __future__ import annotations

import argparse
import ast
import collections
import importlib.machinery
import json
import os
import subprocess
import time
from pathlib import Path

from audit import (
    Closure,
    Imports,
    Repository,
    SourceBoundError,
    digest,
    file_inclusion,
    json_bytes,
    make_repositories,
    probe_import,
)
from observed_profile import ObservedProfileError, validate_profile
from snapshot_verify import SnapshotError, verify_snapshot

SCHEMA = "codebase-ir-runtime-demand/v1"


class DemandError(ValueError):
    pass


class DemandOwner:
    """The sole writer captures source only between immutable child probes."""

    def __init__(
        self,
        repositories: list[Repository],
        output: Path,
        *,
        max_files: int = 512,
        max_bytes: int = 16777216,
        max_file_bytes: int = 2097152,
        allowed_asset_suffixes: list[str] | None = None,
    ):
        self.closure = Closure(
            repositories, max_modules=max_files, max_bytes=max_bytes, max_file_bytes=max_file_bytes
        )
        self.output = output
        self.output.mkdir(parents=True, exist_ok=True)
        self.max_files, self.max_bytes, self.max_file_bytes = max_files, max_bytes, max_file_bytes
        self.allowed_assets = set(allowed_asset_suffixes or [".json", ".txt"])
        self.namespaces: set[tuple[str, str]] = set()
        self.requests: list[dict] = []
        self.frontier: list[dict] = []
        self.received: set[str] = set()
        self.generation = -1
        self.snapshot_root: Path | None = None
        self.snapshot_identity: str | None = None
        self.generations: list[dict] = []
        self.total_bytes = 0
        self.nominated_files: set[tuple[str, str]] = set()
        self.nominations: list[dict] = []
        self.observed_pins: dict[tuple[str, str], dict] | None = None
        self.initial_pins: dict[tuple[str, str], dict] = {}
        self.initial_verification: dict | None = None

    def capture_file(self, repo: Repository, path: str, *, module: str | None, kind: str) -> bool:
        key = (repo.name, path)
        parts = Path(path).parts
        if (
            not parts
            or parts[0] not in repo.packages
            or any(
                p.startswith(".") or p in {"workspace", "state", "artifacts", "__pycache__"}
                for p in parts
            )
        ):
            self.frontier.append(
                {
                    "repository": repo.name,
                    "path": path,
                    "disposition": "source_outside_owned_package",
                }
            )
            return False
        if not repo.ref and not (repo.root / path).resolve().is_relative_to(
            (repo.root / parts[0]).resolve()
        ):
            self.frontier.append(
                {
                    "repository": repo.name,
                    "path": path,
                    "disposition": "source_outside_owned_package",
                }
            )
            return False
        if key in self.closure.captured:
            return False
        if self.observed_pins is not None and key not in self.observed_pins and key not in self.initial_pins:
            self.frontier.append({"repository": repo.name, "path": path, "module": module,
                                  "disposition": "unrecorded_invocation_source_refused"})
            return False
        if len(self.closure.captured) >= self.max_files:
            self.frontier.append(
                {
                    "repository": repo.name,
                    "path": path,
                    "module": module,
                    "disposition": "file_limit",
                }
            )
            return False
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
            return False
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
            return False
        if self.observed_pins is not None:
            expected = (self.observed_pins[key]["observation"]["before"]
                        if key in self.observed_pins else
                        {"size_bytes": self.initial_pins[key]["bytes"], "sha256": self.initial_pins[key]["sha256"]})
            if len(data) != expected["size_bytes"] or digest(data) != expected["sha256"]:
                raise DemandError(f"recorded invocation source drift: {repo.name}:{path}")
        self.closure.captured[key] = data
        self.total_bytes += len(data)
        row = {
            "repository": repo.name,
            "path": path,
            "module": module,
            "kind": kind,
            "bytes": len(data),
            "sha256": digest(data),
            "captured_before_generation": self.generation + 1,
            "git_index_entries": repo.index.get(path, []),
        }
        if path in repo.tree:
            try:
                head = digest(repo.read_tree(path, self.max_file_bytes))
                row["head_sha256"] = head
                index_clean = repo.index.get(path) == [
                    {"mode": repo.tree[path][0], "git_blob_oid": repo.tree[path][1], "stage": 0}
                ]
                row["git_status"] = (
                    "tracked_clean" if head == row["sha256"] and index_clean else "tracked_dirty"
                )
            except SourceBoundError:
                row["git_status"] = "tracked_comparison_unavailable"
        else:
            row["git_status"] = "tracked_added" if path in repo.tracked else "untracked"
        self.closure.nodes[key] = row
        return True

    def demand_module(self, module: str, *, origin: str) -> bool:
        row = {"module": module, "origin": origin, "generation": self.generation}
        if not module or any(not part.isidentifier() for part in module.split(".")):
            row["disposition"] = "invalid_module_request"
            self.requests.append(row)
            return False
        owners = [
            r for r in self.closure.repositories.values() if module.split(".")[0] in r.packages
        ]
        if len(owners) != 1:
            row["disposition"] = "unowned_or_ambiguous_module"
            self.requests.append(row)
            return False
        repo = owners[0]
        changed = False
        parts = module.split(".")
        for i in range(1, len(parts)):
            package = "/".join(parts[:i])
            init = package + "/__init__.py"
            if repo.has(init):
                changed |= self.capture_file(
                    repo, init, module=".".join(parts[:i]), kind="package_initializer"
                )
            elif repo.is_directory(package):
                key = (repo.name, package)
                changed |= key not in self.namespaces
                self.namespaces.add(key)
        found = self.closure.candidates(module)
        if len(found) != 1:
            base = module.replace(".", "/")
            extensions = []
            if not repo.ref:
                for suffix in importlib.machinery.EXTENSION_SUFFIXES:
                    if repo.has(base + suffix):
                        extensions.append(base + suffix)
            row.update(
                disposition="non_python_local_module_unqualified"
                if extensions
                else "absent_local_source",
                repository=repo.name,
                candidate_python_paths=[base + ".py", base + "/__init__.py"],
                non_python_candidates=extensions,
            )
            self.frontier.append(row)
        else:
            _, path, package = found[0]
            if path:
                changed |= self.capture_file(
                    repo,
                    path,
                    module=module,
                    kind="package_initializer" if package else "python_module",
                )
                row.update(
                    disposition="captured"
                    if (repo.name, path) in self.closure.captured
                    else "capture_bound",
                    repository=repo.name,
                    path=path,
                )
            else:
                key = (repo.name, module.replace(".", "/"))
                changed |= key not in self.namespaces
                self.namespaces.add(key)
                row.update(disposition="namespace_directory", repository=repo.name, path=key[1])
        self.requests.append(row)
        return changed

    def demand_asset(self, snapshot_path: str, *, origin: str) -> bool:
        assert self.snapshot_root is not None
        requested = Path(snapshot_path).resolve()
        row = {"snapshot_path": snapshot_path, "origin": origin, "generation": self.generation}
        mappings = [
            (r, requested.relative_to(self.snapshot_root / r.name).as_posix())
            for r in self.closure.repositories.values()
            if requested.is_relative_to(self.snapshot_root / r.name)
        ]
        if len(mappings) != 1:
            row["disposition"] = "asset_request_outside_snapshot"
            self.frontier.append(row)
            return False
        repo, path = mappings[0]
        row.update(repository=repo.name, path=path)
        parts = Path(path).parts
        if (
            not parts
            or parts[0] not in repo.packages
            or any(
                p.startswith(".") or p in {"workspace", "state", "artifacts", "__pycache__"}
                for p in parts
            )
        ):
            row["disposition"] = "asset_outside_owned_package"
            self.frontier.append(row)
            return False
        if Path(path).suffix not in self.allowed_assets:
            row["disposition"] = "non_python_asset_unqualified"
            self.frontier.append(row)
            return False
        if not repo.has(path):
            row["disposition"] = "absent_local_asset"
            self.frontier.append(row)
            return False
        changed = self.capture_file(repo, path, module=None, kind="requested_asset")
        row["disposition"] = (
            "captured" if (repo.name, path) in self.closure.captured else "capture_bound"
        )
        self.requests.append(row)
        return changed

    def identity(self, seed: str, probe_id: str) -> dict:
        return {
            "generation": self.generation,
            "snapshot_sha256": self.snapshot_identity,
            "seed": seed,
            "probe_id": probe_id,
        }

    def receive(self, result: dict, expected: dict) -> bool:
        required = {"generation", "snapshot_sha256", "seed", "probe_id"}
        actual = result.get("request_identity")
        for identity in (expected, actual):
            if (
                not isinstance(identity, dict)
                or set(identity) != required
                or type(identity["generation"]) is not int
                or identity["generation"] < 0
                or any(
                    type(identity[key]) is not str or not identity[key]
                    for key in required - {"generation"}
                )
                or len(identity["snapshot_sha256"]) != 64
                or any(c not in "0123456789abcdef" for c in identity["snapshot_sha256"])
            ):
                raise DemandError("invalid exact probe request identity shape/types")
        if result.get("request_identity") != expected:
            raise DemandError(
                "probe payload identity differs from its exact requested generation/seed"
            )
        if (
            expected["generation"] != self.generation
            or expected["snapshot_sha256"] != self.snapshot_identity
        ):
            raise DemandError("stale probe generation")
        if expected["probe_id"] in self.received:
            raise DemandError("duplicate probe payload")
        self.received.add(expected["probe_id"])
        changed = False
        requests = sorted(
            {
                x["module"]
                for x in result.get("local_import_attempts", [])
                if x["disposition"] == "absent_local_module"
            }
        )
        for module in requests:
            changed |= self.demand_module(module, origin=expected["probe_id"])
        for asset in sorted({x["path"] for x in result.get("missing_snapshot_assets", [])}):
            changed |= self.demand_asset(asset, origin=expected["probe_id"])
        return changed

    def load_initial(self, root: Path, expected_sha256: str) -> None:
        root = root.resolve()
        self.initial_verification = verify_snapshot(root, expected_sha256, max_files=self.max_files,
                                                    max_bytes=self.max_bytes, max_file_bytes=self.max_file_bytes)
        self.initial_pins = {(row["repository"], row["path"]): row
                             for row in self.initial_verification["files"]}
        manifest = json.loads((root / "snapshot.json").read_text())
        stated = manifest.pop("snapshot_sha256")
        if stated != expected_sha256 or digest(json_bytes(manifest)) != stated:
            raise DemandError("initial snapshot manifest differs from explicit pin")
        for row in manifest["files"]:
            repo = self.closure.repositories.get(row["repository"])
            if repo is None:
                raise DemandError("initial snapshot repository has no configured owner")
            path = row["path"]
            source = root / repo.name / path
            if (
                not source.resolve().is_relative_to(root.resolve())
                or source.is_symlink()
                or source.stat().st_size != row["bytes"]
                or row["bytes"] > self.max_file_bytes
            ):
                raise DemandError("initial snapshot file path/size is invalid")
            if digest(source.read_bytes()) != row["sha256"]:
                raise DemandError("initial snapshot file bytes differ from manifest")
            module = (
                path[:-12].replace("/", ".")
                if path.endswith("/__init__.py")
                else path[:-3].replace("/", ".")
                if path.endswith(".py")
                else None
            )
            if not self.capture_file(repo, path, module=module, kind="pinned_initial_capture"):
                raise DemandError("initial snapshot capture bound/ownership refusal")
            if self.closure.nodes[(repo.name, path)]["sha256"] != row["sha256"]:
                raise DemandError("initial snapshot source drift")
        for row in manifest.get("namespace_directories", []):
            repo = self.closure.repositories.get(row["repository"])
            if (
                repo is None
                or Path(row["path"]).parts[0] not in repo.packages
                or ".." in Path(row["path"]).parts
            ):
                raise DemandError("initial namespace is outside package ownership")
            self.namespaces.add((repo.name, row["path"]))

    def nominate_eager_imports(self) -> bool:
        """Nominate direct module-body imports; keep provenance distinct from demand."""
        changed = False
        while True:
            pending = [
                (key, data)
                for key, data in self.closure.captured.items()
                if key not in self.nominated_files
            ]
            if not pending:
                return changed
            for (name, path), data in pending:
                self.nominated_files.add((name, path))
                if not path.endswith(".py"):
                    continue
                module = self.closure.nodes[(name, path)]["module"]
                try:
                    tree = ast.parse(data, filename=path)
                except (SyntaxError, ValueError, RecursionError, UnicodeError) as exc:
                    self.nominations.append(
                        {
                            "repository": name,
                            "path": path,
                            "disposition": "nomination_parse_failure",
                            "error": str(exc),
                        }
                    )
                    continue
                visitor = Imports(module, path.endswith("/__init__.py"))
                for node in tree.body:
                    if isinstance(node, ast.Import | ast.ImportFrom):
                        visitor.visit(node)
                for row in visitor.rows:
                    if not self.closure.local_name(row["module"]):
                        continue
                    origin = f"nominated_module_body:{name}:{path}:{row['line']}"
                    self.nominations.append(
                        {
                            **row,
                            "repository": name,
                            "path": path,
                            "source_sha256": digest(data),
                            "origin": origin,
                        }
                    )
                    changed |= self.demand_module(row["module"], origin=origin)
                    if row["kind"] == "from":
                        for symbol in row["symbols"]:
                            if symbol != "*" and self.closure.candidates(
                                row["module"] + "." + symbol
                            ):
                                changed |= self.demand_module(
                                    row["module"] + "." + symbol, origin=origin
                                )

    def check_stability(self) -> dict:
        result = self.closure.stability()
        if not result["stable"]:
            self.frontier.append(
                {
                    "disposition": "source_drift",
                    "changed_files": [x for x in result["files"] if not x["stable"]],
                    "heads": [x for x in result["heads"] if x["before"] != x["after"]],
                }
            )
        return result

    def seal(self) -> dict:
        if self.snapshot_root is not None:
            self.verify_snapshot()
        if not self.check_stability()["stable"]:
            raise DemandError("pinned source changed before sealing generation")
        self.generation += 1
        target = self.output / f"generation-{self.generation:03d}"
        target.mkdir(exist_ok=False)
        previous = self.snapshot_root
        records = []
        for (repo, path), data in sorted(self.closure.captured.items()):
            dest = target / repo / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            old = previous / repo / path if previous else None
            if old and old.is_file():
                os.link(old, dest)
            else:
                dest.write_bytes(data)
                dest.chmod(0o444)
            records.append(
                {"repository": repo, "path": path, "sha256": digest(data), "bytes": len(data)}
            )
        for repo, path in sorted(self.namespaces):
            (target / repo / path).mkdir(parents=True, exist_ok=True)
        for repo in self.closure.repositories:
            (target / repo).mkdir(exist_ok=True)
        manifest = {
            "schema": SCHEMA,
            "generation": self.generation,
            "parent_snapshot_sha256": self.snapshot_identity,
            "files": records,
            "namespace_directories": [
                {"repository": r, "path": p} for r, p in sorted(self.namespaces)
            ],
        }
        self.snapshot_identity = digest(json_bytes(manifest))
        manifest["snapshot_sha256"] = self.snapshot_identity
        (target / "snapshot.json").write_bytes(json_bytes(manifest))
        (target / "snapshot.json").chmod(0o444)
        for directory in sorted((p for p in target.rglob("*") if p.is_dir()), reverse=True):
            directory.chmod(0o555)
        target.chmod(0o555)
        self.snapshot_root = target.resolve()
        observation = {
            "generation": self.generation,
            "snapshot_root": str(self.snapshot_root),
            "snapshot_sha256": self.snapshot_identity,
            "files": len(records),
            "bytes": self.total_bytes,
        }
        self.generations.append(observation)
        return observation

    def verify_snapshot(self) -> None:
        assert self.snapshot_root is not None
        manifest = json.loads((self.snapshot_root / "snapshot.json").read_text())
        stated = manifest.pop("snapshot_sha256")
        if stated != self.snapshot_identity or digest(json_bytes(manifest)) != stated:
            raise DemandError("snapshot manifest identity changed")
        expected = set()
        for row in manifest["files"]:
            path = self.snapshot_root / row["repository"] / row["path"]
            expected.add(path.resolve())
            if (
                path.is_symlink()
                or not path.is_file()
                or path.stat().st_size != row["bytes"]
                or digest(path.read_bytes()) != row["sha256"]
            ):
                raise DemandError(
                    f"snapshot file identity changed: {row['repository']}:{row['path']}"
                )
        actual = {
            p.resolve()
            for p in self.snapshot_root.rglob("*")
            if p.is_file() and p != self.snapshot_root / "snapshot.json"
        }
        if actual != expected:
            raise DemandError("unexpected or missing snapshot files")

    def manifest(self) -> dict:
        return {
            "schema": SCHEMA,
            "files": sorted(
                self.closure.nodes.values(), key=lambda x: (x["repository"], x["path"])
            ),
            "repositories": [r.identity() for r in self.closure.repositories.values()],
            "generations": self.generations,
            "requests": self.requests,
            "static_nominations": self.nominations,
            "frontier": self.frontier,
            "snapshot_root": str(self.snapshot_root),
            "snapshot_sha256": self.snapshot_identity,
            "snapshot_roots": [str(self.snapshot_root / r) for r in self.closure.repositories]
            if self.snapshot_root is not None else [],
            "source_stability": self.check_stability(),
            "scope": "observed_seed_importability_only",
            "runtime_closure_proven": False,
            "static_closure_complete": False,
        }


def qualify(
    config: dict,
    output: Path,
    *,
    import_timeout: float = 5,
    max_rounds: int | None = None,
    max_files: int | None = None,
    max_bytes: int | None = None,
    total_timeout: float | None = None,
    initial_snapshot: Path | None = None,
    initial_snapshot_sha256: str | None = None,
) -> dict:
    output.mkdir(parents=True, exist_ok=False)
    (output / "config.json").write_bytes(json_bytes(config))
    configured = config.get("bounds", {})
    bounds = {
        "max_rounds": max_rounds or configured.get("max_rounds", 80),
        "max_files": max_files or configured.get("max_files", 512),
        "max_bytes": max_bytes or configured.get("max_bytes", 16777216),
        "max_file_bytes": configured.get("max_file_bytes", 2097152),
        "total_timeout": total_timeout or configured.get("total_timeout", 180),
    }
    repos = make_repositories(config, "working")
    owner = DemandOwner(
        repos,
        output / "snapshots",
        max_files=bounds["max_files"],
        max_bytes=bounds["max_bytes"],
        max_file_bytes=bounds["max_file_bytes"],
        allowed_asset_suffixes=config.get("allowed_asset_suffixes"),
    )
    started = time.monotonic()
    final_probes, rounds = [], []
    disposition = "unresolved"
    try:
        observed_profile = config.get("observed_profile")
        if observed_profile is not None:
            owner.observed_pins = validate_profile(observed_profile, config["repositories"])
        if initial_snapshot is not None:
            if not initial_snapshot_sha256:
                raise DemandError("initial snapshot requires its exact SHA256 pin")
            owner.load_initial(initial_snapshot, initial_snapshot_sha256)
        if owner.observed_pins is not None:
            for (repository, path), row in owner.observed_pins.items():
                if (repository, path) in owner.closure.captured:
                    continue
                if not owner.capture_file(owner.closure.repositories[repository], path,
                                          module=row["module"], kind="recorded_invocation_source"):
                    raise DemandError("recorded invocation profile capture bound/ownership refusal")
        for seed in config["seeds"]:
            owner.demand_module(seed, origin="seed")
        if config.get("nominate_eager_imports") is True:
            owner.nominate_eager_imports()
        owner.seal()
        for round_index in range(bounds["max_rounds"]):
            if not owner.check_stability()["stable"]:
                disposition = "source_drift"
                break
            owner.verify_snapshot()
            pending = []
            for seed_index, seed in enumerate(config["seeds"]):
                remaining = bounds["total_timeout"] - (time.monotonic() - started)
                if remaining <= 0:
                    disposition = "time_limit"
                    owner.frontier.append({"disposition": "time_limit", "round": round_index})
                    break
                identity = owner.identity(seed, f"round-{round_index:03d}-seed-{seed_index:02d}")
                result = probe_import(
                    seed,
                    owner.snapshot_root,
                    [r.name for r in repos],
                    [p for r in repos for p in r.packages],
                    output / "probes" / f"round-{round_index:03d}" / f"seed-{seed_index:02d}",
                    min(import_timeout, remaining),
                    request_identity=identity,
                    allow_ctypes_python_handle=config.get("allow_ctypes_python_handle") is True,
                )
                pending.append((result, identity))
            if disposition == "time_limit":
                break
            final_probes = [result for result, _ in pending]
            changed = False
            for result, identity in pending:
                if result.get("request_identity") is None and result["disposition"] in {
                    "timeout",
                    "probe_process_failure",
                }:
                    result["producer_result_disposition"] = result["disposition"]
                    result["disposition"] = "unbound_probe_result"
                    continue
                changed |= owner.receive(result, identity)
            if config.get("nominate_eager_imports") is True:
                changed |= owner.nominate_eager_imports()
            round_record = {
                "round": round_index,
                "generation": owner.generation,
                "snapshot_sha256": owner.snapshot_identity,
                "results": [
                    {
                        "seed": x["module"],
                        "disposition": x["disposition"],
                        "missing_module": x.get("missing_module"),
                    }
                    for x in final_probes
                ],
                "new_capture": changed,
                "files": len(owner.closure.captured),
                "bytes": owner.total_bytes,
            }
            rounds.append(round_record)
            print(
                json.dumps(
                    {
                        "round": round_index,
                        "files": len(owner.closure.captured),
                        "bytes": owner.total_bytes,
                        "imports": dict(
                            collections.Counter(x["disposition"] for x in final_probes)
                        ),
                        "new_capture": changed,
                    }
                ),
                flush=True,
            )
            if not owner.check_stability()["stable"]:
                disposition = "source_drift"
                break
            if not changed:
                disposition = (
                    "imports_qualified"
                    if all(x["disposition"] == "imported" for x in final_probes)
                    else "unresolved"
                )
                break
            if round_index + 1 == bounds["max_rounds"]:
                disposition = "round_limit"
                owner.frontier.append(
                    {"disposition": "round_limit", "next_generation_unprobed": True}
                )
            owner.seal()
        manifest = owner.manifest()
        owner.verify_snapshot()
        verification = verify_snapshot(owner.snapshot_root, owner.snapshot_identity,
                                       max_files=bounds["max_files"], max_bytes=bounds["max_bytes"],
                                       max_file_bytes=bounds["max_file_bytes"])
        if not manifest["source_stability"]["stable"]:
            disposition = "source_drift"
        source_files = manifest["files"]
        final_subset = []
        for result in final_probes:
            used = set()
            for row in result.get("resolved_local_modules", []):
                if row["file"]:
                    relative = (
                        Path(row["file"])
                        .resolve()
                        .relative_to(Path(result["snapshot_root"]).resolve())
                        .parts
                    )
                    used.add((relative[0], "/".join(relative[1:])))
            final_subset.append(
                {
                    "seed": result["module"],
                    "disposition": result["disposition"],
                    "request_identity": result.get("request_identity"),
                    "files": [x for x in source_files if (x["repository"], x["path"]) in used],
                    "probe": result,
                }
            )
        comparisons = {}
        for mode in ["head"] + [
            m
            for m in ("released_ref", "released_checkout")
            if all(m in s for s in config["repositories"])
        ]:
            reference_repos = []
            try:
                reference_repos = make_repositories(config, mode)
                reference = Closure(
                    reference_repos,
                    max_modules=bounds["max_files"],
                    max_bytes=bounds["max_bytes"],
                    max_file_bytes=bounds["max_file_bytes"],
                )
                comparisons[mode] = file_inclusion({"files": source_files}, reference)
                comparisons[mode]["repositories"] = [r.identity() for r in reference_repos]
                (output / f"working_vs_{mode}.json").write_bytes(json_bytes(comparisons[mode]))
            except (OSError, ValueError, subprocess.SubprocessError) as exc:
                comparisons[mode] = {"disposition": "reference_unavailable", "error": str(exc)}
            finally:
                for repo in reference_repos:
                    repo.close()
        summary = {
            **manifest,
            "disposition": disposition,
            "importability_qualified": disposition == "imports_qualified",
            "bounds": bounds,
            "elapsed_seconds": round(time.monotonic() - started, 6),
            "rounds": rounds,
            "per_seed": final_subset,
            "comparison_counts": {k: v.get("counts", {}) for k, v in comparisons.items()},
            "environment_profile": {
                "site_packages": False,
                "allow_ctypes_python_handle": config.get("allow_ctypes_python_handle") is True,
                "named_ctypes_libraries": False,
            },
            "nominate_eager_imports": config.get("nominate_eager_imports") is True,
            "initial_snapshot": str(initial_snapshot.resolve()) if initial_snapshot else None,
            "initial_snapshot_sha256": initial_snapshot_sha256,
            "initial_snapshot_verification": owner.initial_verification,
            "observed_invocation_profile": observed_profile,
            "snapshot_verification": verification,
            "qualification_scope": "Imports only; no service execution, training, numerical correctness or authority acceptance is established",
            "output": str(output.resolve()),
        }
        (output / "summary.json").write_bytes(json_bytes(summary))
        return summary
    except (DemandError, ObservedProfileError, SnapshotError) as exc:
        summary = {
            **owner.manifest(),
            "disposition": "source_or_snapshot_refusal",
            "error": str(exc),
            "importability_qualified": False,
            "bounds": bounds,
            "rounds": rounds,
            "output": str(output.resolve()),
            "observed_invocation_profile": config.get("observed_profile"),
            "initial_snapshot": str(initial_snapshot.resolve()) if initial_snapshot else None,
            "initial_snapshot_sha256": initial_snapshot_sha256,
            "initial_snapshot_verification": owner.initial_verification,
        }
        (output / "summary.json").write_bytes(json_bytes(summary))
        return summary
    finally:
        for repo in repos:
            repo.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--import-timeout", type=float, default=5)
    parser.add_argument("--max-rounds", type=int)
    parser.add_argument("--max-files", type=int)
    parser.add_argument("--max-bytes", type=int)
    parser.add_argument("--total-timeout", type=float)
    parser.add_argument("--initial-snapshot", type=Path)
    parser.add_argument("--initial-snapshot-sha256")
    args = parser.parse_args()
    if not 0 < args.import_timeout <= 30 or any(
        x is not None and x <= 0
        for x in (args.max_rounds, args.max_files, args.max_bytes, args.total_timeout)
    ):
        parser.error("positive bounds required; per-probe timeout must be at most30seconds")
    result = qualify(
        json.loads(args.config.read_text()),
        args.output,
        import_timeout=args.import_timeout,
        max_rounds=args.max_rounds,
        max_files=args.max_files,
        max_bytes=args.max_bytes,
        total_timeout=args.total_timeout,
        initial_snapshot=args.initial_snapshot,
        initial_snapshot_sha256=args.initial_snapshot_sha256,
    )
    print(
        json.dumps(
            {
                k: result.get(k)
                for k in (
                    "output",
                    "disposition",
                    "importability_qualified",
                    "snapshot_root",
                    "snapshot_sha256",
                    "comparison_counts",
                )
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
