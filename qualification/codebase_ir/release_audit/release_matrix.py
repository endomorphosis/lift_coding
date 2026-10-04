#!/usr/bin/env python3
"""Bounded, read-only commit reconciliation; retained claims are never requalified."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from snapshot_verify import verify_snapshot

SCHEMA = "codebase-ir-release-matrix@1"
INPUT_SCHEMA = "codebase-ir-release-matrix-input@1"
MAX_FILE_BYTES = 4 * 1024 * 1024
MAX_TOTAL_BYTES = 64 * 1024 * 1024
MAX_FILES = 768
MAX_COMMANDS = 2400
MAX_SECONDS = 120
IDS = {f"RPI-{i:03d}" for i in range(1, 33)}
FALSE_FLAGS = ("native_execution_performed", "training_executed", "current_authority_claimed",
               "production_acceptance_requalified")


class MatrixRefusal(ValueError):
    pass


def need(condition: bool, message: str) -> None:
    if not condition:
        raise MatrixRefusal(message)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode()


def exact_hex(value: object, length: int = 64) -> bool:
    return type(value) is str and re.fullmatch(f"[0-9a-f]{{{length}}}", value) is not None


def pairs(rows: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in rows:
        need(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def finite_float(text: str) -> float:
    result = float(text)
    need(math.isfinite(result), "nonfinite JSON number")
    return result


def constant(text: str) -> None:
    raise MatrixRefusal("nonfinite JSON constant: " + text)


def document(raw: bytes) -> dict:
    try:
        result = json.loads(raw, object_pairs_hook=pairs, parse_float=finite_float,
                            parse_constant=constant)
    except (ValueError, RecursionError, UnicodeError) as exc:
        raise MatrixRefusal("strict bounded JSON required: " + str(exc)) from exc
    need(type(result) is dict, "JSON object required")
    return result


def fields(value: object, expected: set[str], label: str) -> None:
    need(type(value) is dict and set(value) == expected, "exact " + label + " fields required")


def text(value: object) -> bool:
    return type(value) is str and bool(value) and len(value) <= 16384


def relative(value: object) -> str:
    need(type(value) is str and value and len(value) <= 1024, "relative path text required")
    path = Path(value)
    need(not path.is_absolute() and path.as_posix() == value and len(path.parts) <= 32
         and all(not part.startswith(".") and part not in {"state", "workspace", "__pycache__"}
                 for part in path.parts), "path outside selected public package/evidence scope")
    return value


def canonical(value: object, *, directory: bool = False) -> Path:
    need(type(value) is str and value, "absolute canonical path text required")
    path = Path(value)
    need(path.is_absolute() and str(path) == str(path.resolve(strict=True))
         and not any(p.is_symlink() for p in (path, *path.parents)), "path alias/symlink refused")
    if directory:
        need(path.is_dir(), "repository/artifact directory required")
    return path


class Capture:
    """First-capture budget; stability has a separate equal-size reread budget."""
    def __init__(self):
        self.cache: dict[Path, bytes] = {}
        self.total_bytes = 0
        self.git_commands = 0
        self.started = time.monotonic()

    def time_check(self):
        need(time.monotonic() - self.started <= MAX_SECONDS, "audit wall-time ceiling reached")

    def reserve(self, size: int):
        self.time_check()
        need(type(size) is int and 0 <= size <= MAX_FILE_BYTES
             and self.total_bytes + size <= MAX_TOTAL_BYTES, "artifact/Git body byte ceiling reached")
        self.total_bytes += size

    @staticmethod
    def identity(info: os.stat_result) -> tuple:
        return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns

    def read_body(self, path: Path, limit: int) -> bytes:
        canonical(str(path))
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as stream:
            before = os.fstat(stream.fileno())
            need(stat.S_ISREG(before.st_mode) and before.st_size <= limit,
                 "bounded regular input file required")
            raw = stream.read(limit + 1)
            after = os.fstat(stream.fileno())
        need(len(raw) == before.st_size and len(raw) <= limit
             and self.identity(before) == self.identity(after) == self.identity(path.stat(follow_symlinks=False)),
             "input changed during bounded descriptor read")
        return raw

    def read(self, path: Path, digest: str | None = None, size: int | None = None) -> bytes:
        self.time_check()
        if path not in self.cache:
            need(len(self.cache) < MAX_FILES, "input file-count ceiling reached")
            info = path.stat(follow_symlinks=False)
            self.reserve(info.st_size)
            self.cache[path] = self.read_body(path, info.st_size)
        raw = self.cache[path]
        need(digest is None or exact_hex(digest) and sha(raw) == digest, "input raw SHA256 differs")
        need(size is None or type(size) is int and size == len(raw), "input byte pin differs")
        return raw

    def stability(self) -> dict:
        rows = []
        for path, raw in self.cache.items():
            self.time_check()
            try:
                after = self.read_body(path, len(raw))
                row = {"path": str(path), "before_sha256": sha(raw), "after_sha256": sha(after),
                       "unchanged": after == raw}
            except (ValueError, OSError) as exc:
                row = {"path": str(path), "before_sha256": sha(raw), "after_sha256": None,
                       "unchanged": False, "error": str(exc)}
            rows.append(row)
        return {"unchanged": all(x["unchanged"] for x in rows), "files": rows,
                "scope": "exact sequential rereads of first-captured local inputs; no atomic capture claim"}


class GitObjects:
    def __init__(self, spec: dict, capture: Capture):
        fields(spec, {"name", "root", "commit", "package_roots"}, "repository")
        need(text(spec["name"]) and spec["name"].isidentifier() and exact_hex(spec["commit"], 40),
             "explicit repository name and 40-hex commit required")
        need(type(spec["package_roots"]) is list and 1 <= len(spec["package_roots"]) <= 8
             and len(set(spec["package_roots"])) == len(spec["package_roots"])
             and all(type(x) is str and x.isidentifier() for x in spec["package_roots"]),
             "exact package roots required")
        self.name, self.root, self.commit = spec["name"], canonical(spec["root"], directory=True), spec["commit"]
        self.packages, self.capture = spec["package_roots"], capture
        self.commands, self.cache, self.trees = 0, {}, {}
        self.executable = shutil.which("git")
        need(self.executable is not None, "Git executable unavailable")
        need(self.command(["cat-file", "-t", self.commit], 64).strip() == b"commit", "explicit Git commit missing")
        size_raw = self.command(["cat-file", "-s", self.commit], 64).strip()
        need(size_raw.isdigit(), "Git commit size malformed")
        size = int(size_raw)
        capture.reserve(size)
        raw = self.command(["cat-file", "commit", self.commit], size)
        need(len(raw) == size and hashlib.sha1(b"commit " + str(size).encode() + b"\0" + raw).hexdigest() == self.commit,
             "Git exact commit object identity differs")
        first = raw.split(b"\n", 1)[0]
        need(first.startswith(b"tree ") and exact_hex(first[5:].decode("ascii"), 40), "Git commit root tree malformed")
        self.root_tree = first[5:].decode("ascii")

    def tree(self, oid: str) -> dict[bytes, tuple[str, str]]:
        if oid in self.trees:
            return self.trees[oid]
        size_raw = self.command(["cat-file", "-s", oid], 64).strip()
        need(size_raw.isdigit(), "Git tree size malformed")
        size = int(size_raw)
        self.capture.reserve(size)
        raw = self.command(["cat-file", "tree", oid], size)
        need(len(raw) == size and hashlib.sha1(b"tree " + str(size).encode() + b"\0" + raw).hexdigest() == oid,
             "Git exact traversed tree object identity differs")
        result, offset = {}, 0
        while offset < len(raw):
            need(len(result) < 4096, "Git tree entry-count ceiling reached")
            end = raw.find(b"\0", offset)
            need(end >= 0 and end + 21 <= len(raw), "malformed Git raw tree entry")
            header = raw[offset:end].split(b" ", 1)
            need(len(header) == 2, "malformed Git raw tree header")
            mode, name = header[0].decode("ascii"), header[1]
            need(mode in {"40000", "100644", "100755", "120000", "160000"}
                 and name and b"/" not in name and name not in {b".", b".."} and name not in result,
                 "Git raw tree mode/name/duplicate refused")
            result[name] = mode, raw[end + 1:end + 21].hex()
            offset = end + 21
        self.trees[oid] = result
        return result

    def command(self, args: list[str], limit: int) -> bytes:
        self.capture.time_check()
        self.commands += 1
        self.capture.git_commands += 1
        need(self.capture.git_commands <= MAX_COMMANDS, "Git command-count ceiling reached")
        env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        env.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                    "GIT_NO_LAZY_FETCH": "1", "GIT_NO_REPLACE_OBJECTS": "1",
                    "GIT_OPTIONAL_LOCKS": "0", "LC_ALL": "C"})
        argv = [self.executable, "--no-replace-objects", "--literal-pathspecs", "-C", str(self.root), *args]
        with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as error:
            child = subprocess.Popen(argv, env=env, stdout=output, stderr=error)
            deadline = min(self.capture.started + MAX_SECONDS, time.monotonic() + 5)
            try:
                while child.poll() is None:
                    need(time.monotonic() < deadline, "Git command timeout")
                    need(os.fstat(output.fileno()).st_size <= limit
                         and os.fstat(error.fileno()).st_size <= 16384, "Git command output ceiling reached")
                    time.sleep(0.005)
                need(os.fstat(output.fileno()).st_size <= limit
                     and os.fstat(error.fileno()).st_size <= 16384, "Git command output ceiling reached")
                need(child.returncode == 0, "Git object command failed")
                output.seek(0)
                return output.read(limit + 1)
            finally:
                if child.poll() is None:
                    child.kill()
                child.wait()

    def blob(self, path: str) -> tuple[dict, bytes | None]:
        relative(path)
        if path in self.cache:
            return self.cache[path]
        parts, oid, found = Path(path).parts, self.root_tree, None
        for index, part in enumerate(parts):
            found = self.tree(oid).get(part.encode("utf-8"))
            if found is None:
                break
            mode, oid = found
            if index < len(parts) - 1:
                need(mode == "40000", "Git selected pathname crosses a non-directory boundary")
        if found is None:
            result = ({"repository": self.name, "commit": self.commit, "path": path,
                       "disposition": "missing"}, None)
        else:
            need(mode in {"100644", "100755"} and exact_hex(oid, 40), "Git selected path is not an exact regular blob")
            size_raw = self.command(["cat-file", "-s", oid], 64).strip()
            need(size_raw.isdigit(), "Git blob size malformed")
            size = int(size_raw)
            try:
                self.capture.reserve(size)
            except MatrixRefusal:
                self.capture.time_check()
                result = ({"repository": self.name, "commit": self.commit, "path": path,
                           "disposition": "unread_byte_limit", "git_blob": oid, "size_bytes": size}, None)
            else:
                raw = self.command(["cat-file", "blob", oid], size)
                need(len(raw) == size and hashlib.sha1(b"blob " + str(size).encode() + b"\0" + raw).hexdigest() == oid,
                     "Git exact object body identity differs")
                result = ({"repository": self.name, "commit": self.commit, "path": path,
                           "disposition": "captured", "git_blob": oid, "size_bytes": size,
                           "sha256": sha(raw)}, raw)
        self.cache[path] = result
        return result


def dependencies(value: object) -> tuple[list[str], list[str]]:
    need(text(value), "prerequisite declaration required")
    if value == "None":
        return [], []
    def expand_range(match):
        first, last = int(match[1]), int(match[2])
        need(1 <= first <= last <= 32, "RPI prerequisite range malformed")
        return ", ".join(f"RPI-{i:03d}" for i in range(first, last + 1))
    normalized = re.sub(r"RPI-(\d{3}) through RPI-(\d{3})", expand_range, value)
    normalized = re.sub(r"RPI-(\d{3})((?:/\d{3})+)",
                        lambda m: ", ".join("RPI-" + x for x in [m[1], *m[2].split("/")[1:]]), normalized)
    token = r"(?<![A-Za-z0-9])(?:RPI|TIP)-\d{3}(?![A-Za-z0-9])"
    tokens = re.findall(token, normalized)
    remainder = re.sub(token, "", normalized)
    need(tokens and "RPI" not in remainder and "TIP" not in remainder
         and len(tokens) == len(set(tokens)), "malformed/duplicate prerequisite IDs")
    rpi, external = sorted(x for x in tokens if x.startswith("RPI")), sorted(x for x in tokens if x.startswith("TIP"))
    need(all(x in IDS for x in rpi) and all(1 <= int(x[4:]) <= 999 for x in external), "unknown prerequisite ID")
    return rpi, external


def task_table(raw: bytes) -> dict:
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeError as exc:
        raise MatrixRefusal("task table must be UTF-8") from exc
    rows = {}
    for number, line in enumerate(lines, 1):
        if not re.match(r"\|\s*RPI-", line):
            continue
        parts = [x.strip() for x in line.strip().split("|")[1:-1]]
        need(len(parts) == 4 and parts[0] in IDS and parts[0] not in rows, "malformed/duplicate current task row")
        rpi, external = dependencies(parts[2])
        rows[parts[0]] = {"owners": parts[1], "dependencies": parts[2], "criterion": parts[3],
                           "source_line": number, "rpi_dependencies": rpi, "external_dependencies": external}
    need(set(rows) == IDS, "exact 32-task current table population required")
    return rows


def validate_ledger(value: dict) -> dict:
    fields(value, {"schema", "updated_at_utc", "scope", "source", "summary", "evidence", "criteria",
                   "source_revision_observation", "closure_audit"}, "released ledger")
    need(value["schema"] == "repository-proof-index-backlog-status/v1", "unsupported released ledger schema")
    source = value["source"]
    fields(source, {"path", "sha256", "worktree_head", "working_source", "table_rows"}, "ledger source")
    need(text(source["path"]) and exact_hex(source["sha256"]) and exact_hex(source["worktree_head"], 40)
         and type(source["working_source"]) is bool and type(source["table_rows"]) is int
         and source["table_rows"] == 32, "ledger source identity/population malformed")
    evidence = value["evidence"]
    need(type(evidence) is dict and len(evidence) <= 128, "bounded evidence catalog required")
    for key, row in evidence.items():
        need(text(key) and type(row) is dict and {"path", "sha256", "retention"} <= set(row)
             and set(row) <= {"path", "sha256", "retention", "repository", "summary"}
             and exact_hex(row["sha256"]) and text(row["retention"])
             and ("repository" not in row or text(row["repository"])), "evidence identity malformed")
        relative(row["path"])
        need(row["path"].startswith("docs/"), "nonpublic evidence path refused")
    need(type(value["criteria"]) is list and len(value["criteria"]) == 32, "32 criterion rows required")
    criteria = {}
    required = {"id", "owners", "dependencies", "criterion", "source_line", "production_acceptance",
                "local_status", "locally_qualified_portions", "remaining_work", "evidence", "criterion_acceptance"}
    optional = {"blocking_dependencies", "qualified_profile", "out_of_profile_extensions", "dependency_scope"}
    for row in value["criteria"]:
        need(type(row) is dict and required <= set(row) <= required | optional
             and type(row["id"]) is str and row["id"] in IDS and row["id"] not in criteria,
             "criterion population/fields malformed")
        need(all(text(row[x]) for x in ("owners", "criterion", "local_status"))
             and type(row["source_line"]) is int and row["source_line"] > 0
             and row["production_acceptance"] in {"closed", "open"}
             and row["criterion_acceptance"] in {"qualified_for_declared_profile", "not_yet_qualified"},
             "criterion claim/type malformed")
        for key in {"locally_qualified_portions", "remaining_work", "evidence", "blocking_dependencies", "out_of_profile_extensions"} & set(row):
            need(type(row[key]) is list and len(row[key]) <= 128 and all(text(x) for x in row[key])
                 and len(row[key]) == len(set(row[key])), "criterion list malformed")
        need(all(x in evidence for x in row["evidence"]), "unknown criterion evidence ID")
        rpi, external = dependencies(row["dependencies"])
        need(row["id"] not in rpi, "self prerequisite refused")
        need(all(x in rpi + external for x in row.get("blocking_dependencies", [])), "undeclared blocking prerequisite")
        need("qualified_profile" not in row or text(row["qualified_profile"]), "profile must be text")
        need("dependency_scope" not in row or text(row["dependency_scope"]), "dependency scope must be text")
        criteria[row["id"]] = {**row, "rpi_dependencies": rpi, "external_dependencies": external}
    need(set(criteria) == IDS, "exact32 criterion population required")
    active, visited = set(), set()
    def visit(key):
        need(key not in active, "cyclic prerequisite graph refused")
        if key in visited:
            return
        active.add(key)
        for child in criteria[key]["rpi_dependencies"]:
            visit(child)
        active.remove(key)
        visited.add(key)
    for key in criteria:
        visit(key)
    return criteria


def reconcile(manifest_path: Path, *, expected_manifest_sha256: str | None = None) -> dict:
    capture = Capture()
    manifest_path = canonical(str(manifest_path))
    manifest_raw = capture.read(manifest_path)
    need(expected_manifest_sha256 is None or sha(manifest_raw) == expected_manifest_sha256,
         "manifest changed after output-scope preflight")
    spec = document(manifest_raw)
    fields(spec, {"schema", "repositories", "ledger", "released_documents", "local_documents",
                  "selected_evidence", "source_profiles", "snapshot"}, "input manifest")
    need(spec["schema"] == INPUT_SCHEMA and type(spec["repositories"]) is list
         and 1 <= len(spec["repositories"]) <= 4, "input schema/repository bound malformed")
    repos = {}
    for row in spec["repositories"]:
        repo = GitObjects(row, capture)
        need(repo.name not in repos and all(repo.root != other.root for other in repos.values()), "duplicate repository identity")
        repos[repo.name] = repo
    ledger_pin = spec["ledger"]
    fields(ledger_pin, {"repository", "path", "sha256"}, "ledger pin")
    need(ledger_pin["repository"] in repos and exact_hex(ledger_pin["sha256"]), "ledger pin malformed")
    ledger_blob, raw = repos[ledger_pin["repository"]].blob(ledger_pin["path"])
    need(raw is not None and sha(raw) == ledger_pin["sha256"], "released ledger absent/unread/different")
    ledger = document(raw)
    criteria = validate_ledger(ledger)
    need(type(spec["local_documents"]) is list and 1 <= len(spec["local_documents"]) <= 8,
         "bounded local document population required")
    local, names, table = [], set(), None
    for row in spec["local_documents"]:
        fields(row, {"name", "path", "sha256", "size_bytes", "kind", "source_basis", "observed_path"}, "local document pin")
        need(text(row["name"]) and row["name"] not in names and row["kind"] in {"task_table", "context"}
             and exact_hex(row["sha256"]) and type(row["size_bytes"]) is int, "local document identity malformed")
        names.add(row["name"])
        path = canonical(row["path"])
        need(path.suffix in {".md", ".json"}, "local document suffix refused")
        observed_path = Path(row["observed_path"]) if type(row["observed_path"]) is str else None
        need(row["source_basis"] in {"current_working_source", "retained_working_observation"}
             and observed_path is not None and observed_path.is_absolute()
             and observed_path.as_posix() == row["observed_path"]
             and all(part not in {".", ".."} for part in observed_path.parts)
             and (row["source_basis"] != "current_working_source" or observed_path == path)
             and (row["source_basis"] != "retained_working_observation"
                  or path != observed_path and not any(path.is_relative_to(repo.root) for repo in repos.values())),
             "explicit working document observation basis required")
        body = capture.read(path, row["sha256"], row["size_bytes"])
        local.append(dict(row))
        if row["kind"] == "task_table":
            need(table is None, "exactly one current task table required")
            table = task_table(body)
            current_digest = row["sha256"]
    need(table is not None, "current task table missing")
    need(type(spec["released_documents"]) is list and len(spec["released_documents"]) <= 8,
         "released document bound malformed")
    released_documents = []
    names.clear()
    for row in spec["released_documents"]:
        fields(row, {"name", "repository", "path", "sha256"}, "released document pin")
        need(text(row["name"]) and row["name"] not in names and row["repository"] in repos
             and (row["sha256"] is None or exact_hex(row["sha256"])), "released document identity malformed")
        names.add(row["name"])
        observed, body = repos[row["repository"]].blob(row["path"])
        need((row["sha256"] is None and observed["disposition"] == "missing")
             or body is not None and sha(body) == row["sha256"], "released document pin/absence differs")
        released_documents.append({**observed, "name": row["name"], "expected_sha256": row["sha256"]})
    selected = spec["selected_evidence"]
    need(type(selected) is list and len(selected) <= 128 and all(type(x) is str for x in selected)
         and len(selected) == len(set(selected)) and all(x in ledger["evidence"] for x in selected),
         "selected evidence population malformed")
    aliases = {package: name for name, repo in repos.items() for package in repo.packages}
    need(len(aliases) == sum(len(repo.packages) for repo in repos.values()), "ambiguous package ownership")
    evidence_rows = []
    for key in selected:
        row = ledger["evidence"][key]
        name = aliases.get(row.get("repository"), row.get("repository", ledger_pin["repository"]))
        need(name in repos, "selected evidence has unconfigured repository")
        observed, body = repos[name].blob(row["path"])
        disposition = observed["disposition"] if body is None else "identical" if sha(body) == row["sha256"] else "different"
        evidence_rows.append({**observed, "id": key, "expected_sha256": row["sha256"],
                              "declared_retention": row["retention"], "disposition": disposition,
                              "portability": "exact_selected_blob_available" if disposition == "identical" else "not_established",
                              "transitive_artifacts_qualified": False})
    snapshot_before = None
    source_rows = []
    if spec["snapshot"] is not None:
        fields(spec["snapshot"], {"root", "sha256"}, "snapshot pin")
        root = canonical(spec["snapshot"]["root"], directory=True)
        need(exact_hex(spec["snapshot"]["sha256"]), "snapshot digest malformed")
        snapshot_before = verify_snapshot(root, spec["snapshot"]["sha256"])
        for row in snapshot_before["files"]:
            need(row["repository"] in repos and row["path"].split("/")[0] in repos[row["repository"]].packages,
                 "snapshot file outside configured package ownership")
            source_rows.append({"repository": row["repository"], "path": row["path"],
                                "sha256": row["sha256"], "size_bytes": row["bytes"],
                                "retained_path": str(root / row["repository"] / row["path"]),
                                "profile": "sealed_snapshot", "origin_basis": "manifest_bound_retained_generation"})
    need(type(spec["source_profiles"]) is list and len(spec["source_profiles"]) <= 8, "source profile bound malformed")
    names.clear()
    for profile in spec["source_profiles"]:
        fields(profile, {"name", "origin_basis", "files"}, "source profile")
        need(text(profile["name"]) and profile["name"] not in names and text(profile["origin_basis"])
             and type(profile["files"]) is list and len(profile["files"]) <= 512, "source profile malformed")
        names.add(profile["name"])
        for row in profile["files"]:
            fields(row, {"repository", "path", "sha256", "size_bytes", "retained_path"}, "selected source pin")
            need(row["repository"] in repos and exact_hex(row["sha256"])
                 and type(row["size_bytes"]) is int and 0 <= row["size_bytes"] <= 2 * 1024 * 1024,
                 "selected source pin malformed")
            relative(row["path"])
            need(row["path"].split("/")[0] in repos[row["repository"]].packages
                 and Path(row["path"]).suffix == ".py", "selected source outside package scope")
            path = canonical(row["retained_path"])
            need(not any(path.is_relative_to(repo.root) for repo in repos.values()), "live source cannot stand in for retained copy")
            need(len(source_rows) < 512 and sum(x["size_bytes"] for x in source_rows) + row["size_bytes"] <= 16 * 1024 * 1024,
                 "selected source population/byte ceiling reached before capture")
            capture.read(path, row["sha256"], row["size_bytes"])
            source_rows.append({**row, "profile": profile["name"], "origin_basis": profile["origin_basis"]})
    need(len(source_rows) <= 512 and sum(x["size_bytes"] for x in source_rows) <= 16 * 1024 * 1024,
         "selected source population/byte ceiling reached")
    seen = set()
    source_results = []
    for row in source_rows:
        key = row["repository"], row["path"]
        need(key not in seen, "duplicate selected source identity")
        seen.add(key)
        observed, body = repos[row["repository"]].blob(row["path"])
        disposition = observed["disposition"] if body is None else "identical" if sha(body) == row["sha256"] else "different"
        source_results.append({**row, "release_view": observed, "disposition": disposition,
                               "source_execution_qualified": False, "dependency_closure_qualified": False})
    ancestor_cache = {}
    def ancestors(key):
        if key in ancestor_cache:
            return ancestor_cache[key]
        result = set()
        for child in criteria[key]["rpi_dependencies"]:
            result.add(child)
            result.update(ancestors(child))
        ancestor_cache[key] = result
        return result
    matrix = []
    for key in sorted(IDS):
        row, current = criteria[key], table[key]
        blockers = sorted(x for x in ancestors(key) if criteria[x]["production_acceptance"] != "closed")
        chosen = [x for x in evidence_rows if x["id"] in row["evidence"]]
        matrix.append({"id": key, "frozen_criterion": row["criterion"], "frozen_criterion_sha256": sha(row["criterion"].encode()),
                       "current_criterion": current["criterion"], "current_criterion_sha256": sha(current["criterion"].encode()),
                       "criterion_changed": row["criterion"] != current["criterion"],
                       "owners_changed": row["owners"] != current["owners"],
                       "dependencies_changed": row["dependencies"] != current["dependencies"],
                       "declared_production_acceptance": row["production_acceptance"],
                       "declared_criterion_acceptance": row["criterion_acceptance"],
                       "declared_local_status": row["local_status"], "declared_profile": row.get("qualified_profile"),
                       "rpi_dependencies": row["rpi_dependencies"], "transitive_open_rpi_dependencies": blockers,
                       "declared_blocking_dependencies": row.get("blocking_dependencies", []),
                       "external_dependencies": row["external_dependencies"],
                       "external_dependency_scope_declaration": row.get("dependency_scope"),
                       "external_prerequisites_independently_verified": False,
                       "rpi_declared_closure_consistent": not (row["production_acceptance"] == "closed" and blockers),
                       "declared_evidence": row["evidence"], "selected_evidence": [x["id"] for x in chosen],
                       "unselected_evidence": sorted(set(row["evidence"]) - set(selected)),
                       "selected_evidence_gaps": [x["id"] for x in chosen if x["disposition"] != "identical"],
                       "disposition": "declared_profile_closed" if row["production_acceptance"] == "closed" else
                           "own_profile_qualified_prerequisites_open" if row["criterion_acceptance"] == "qualified_for_declared_profile" else "declared_open",
                       "production_acceptance_requalified": False})
    counts = {"criteria": 32, "production_closed": sum(x["production_acceptance"] == "closed" for x in criteria.values()),
              "production_open": sum(x["production_acceptance"] == "open" for x in criteria.values()),
              "criteria_qualified_for_declared_profile": sum(x["criterion_acceptance"] == "qualified_for_declared_profile" for x in criteria.values())}
    fields(ledger["summary"], set(counts), "ledger summary")
    need(all(type(x) is int and 0 <= x <= 32 for x in ledger["summary"].values()), "summary exact count types required")
    stability = capture.stability()
    snapshot_after = verify_snapshot(Path(snapshot_before["snapshot_root"]), snapshot_before["snapshot_sha256"]) if snapshot_before else None
    snapshot_stable = snapshot_before == snapshot_after
    need(stability["unchanged"] and snapshot_stable, "input/snapshot byte drift refused")
    return {"schema": SCHEMA, "status": "passed", "manifest_sha256": sha(manifest_raw),
            "scope": "commit-pinned claim reconciliation and selected byte inclusion; no qualification replay",
            "repositories": [{"name": x.name, "root": str(x.root), "commit": x.commit,
                              "git_commands": x.commands, "verified_traversed_tree_objects": len(x.trees)} for x in repos.values()],
            "read_only_git_invoked": True, "pathname_tree_object_hash_verification_performed": True,
            "ledger": ledger_blob, "declared_counts": ledger["summary"], "reconstructed_claim_counts": counts,
            "declared_summary_matches": counts == ledger["summary"], "criteria": matrix,
            "criterion_source": {"frozen_document_sha256_declared": ledger["source"]["sha256"],
                                 "frozen_original_document_independently_captured": False,
                                 "frozen_criteria_basis": "exact pinned released ledger fields",
                                 "current_local_document_sha256": current_digest,
                                 "local_document_basis": next(row["source_basis"] for row in local if row["kind"] == "task_table"),
                                 "current_live_document_freshness_qualified": False,
                                 "raw_document_changed": current_digest != ledger["source"]["sha256"],
                                 "changed_criteria": [x["id"] for x in matrix if x["criterion_changed"]]},
            "local_documents": local, "released_documents": released_documents,
            "evidence": evidence_rows, "evidence_dispositions": dict(collections.Counter(x["disposition"] for x in evidence_rows)),
            "selected_sources": source_results, "source_dispositions": dict(collections.Counter(x["disposition"] for x in source_results)),
            "snapshot_before": snapshot_before, "snapshot_after": snapshot_after,
            "snapshot_identity_stable": snapshot_stable, "input_files_unchanged": True, "input_stability": stability,
            "portability": {"scope": "selected regular Git blobs and retained local input bytes only",
                            "all_referenced_artifacts_available": False, "owner_local_state_portable": False,
                            "runtime_environment_qualified": False, "dynamic_dependency_frontier": "unknown_unexecuted",
                            "runtime_dependency_closure_qualified": False},
            "bounds": {"max_file_bytes": MAX_FILE_BYTES, "max_first_capture_bytes": MAX_TOTAL_BYTES,
                       "max_local_files": MAX_FILES, "max_total_git_commands": MAX_COMMANDS,
                       "max_seconds": MAX_SECONDS, "stability_reread_bytes": sum(len(x) for x in capture.cache.values()),
                       "first_capture_bytes": capture.total_bytes, "selected_source_files": len(source_results)},
            **dict.fromkeys(FALSE_FLAGS, False)}


def output_scope(manifest: dict, output: Path) -> None:
    """Refuse output beneath original inputs before creating any directory."""
    fields(manifest, {"schema", "repositories", "ledger", "released_documents", "local_documents",
                      "selected_evidence", "source_profiles", "snapshot"}, "input manifest")
    need(type(manifest["repositories"]) is list and 1 <= len(manifest["repositories"]) <= 4
         and type(manifest["local_documents"]) is list and 1 <= len(manifest["local_documents"]) <= 8
         and type(manifest["source_profiles"]) is list and len(manifest["source_profiles"]) <= 8,
         "bounded input scope lists required")
    protected = []
    for row in manifest["repositories"]:
        fields(row, {"name", "root", "commit", "package_roots"}, "repository")
        protected.append(canonical(row["root"], directory=True))
    if manifest["snapshot"] is not None:
        fields(manifest["snapshot"], {"root", "sha256"}, "snapshot pin")
        protected.append(canonical(manifest["snapshot"]["root"], directory=True))
    for row in manifest["local_documents"]:
        fields(row, {"name", "path", "sha256", "size_bytes", "kind", "source_basis", "observed_path"}, "local document pin")
        protected.append(canonical(row["path"]).parent)
        need(type(row["observed_path"]) is str and Path(row["observed_path"]).is_absolute(),
             "original working document path required")
        original_parent = Path(row["observed_path"]).parent
        if original_parent.exists():
            protected.append(canonical(str(original_parent), directory=True))
    for profile in manifest["source_profiles"]:
        fields(profile, {"name", "origin_basis", "files"}, "source profile")
        need(type(profile["files"]) is list and len(profile["files"]) <= 512,
             "bounded source scope list required")
        for row in profile["files"]:
            fields(row, {"repository", "path", "sha256", "size_bytes", "retained_path"}, "selected source pin")
            protected.append(canonical(row["retained_path"]).parent)
    need(not any(output.is_relative_to(root) for root in protected), "output lies inside an original input scope")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    output = args.output
    created, manifest_digest = False, None
    try:
        need(output.is_absolute() and str(output) == str(output.resolve())
             and output.parent.resolve(strict=True) == output.parent
             and not any(p.is_symlink() for p in output.parents) and not output.exists(),
             "fresh canonical output directory required")
        manifest_raw = Capture().read(canonical(str(args.manifest)))
        manifest_digest = sha(manifest_raw)
        output_scope(document(manifest_raw), output)
        output.mkdir()
        created = True
        report = reconcile(args.manifest, expected_manifest_sha256=manifest_digest)
    except (ValueError, OSError, KeyError, TypeError, RecursionError) as exc:
        report = {"schema": SCHEMA, "status": "refused", "manifest_sha256": manifest_digest,
                  "input_files_unchanged": False, "reason": str(exc), **dict.fromkeys(FALSE_FLAGS, False)}
        if created:
            (output / "release_matrix.json").write_bytes(json_bytes(report))
        print("release matrix refused: " + str(exc), file=sys.stderr)
        return 2
    (output / "release_matrix.json").write_bytes(json_bytes(report))
    print(json.dumps({"status": report["status"], "manifest_sha256": report["manifest_sha256"],
                      "criteria": len(report["criteria"]), "evidence": len(report["evidence"]),
                      "sources": len(report["selected_sources"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
