"""Snapshot seven canonical source trees without touching their HEAD or index.

Only selected actual tracked differences and meaningful, effectively unignored
untracked source files enter a private HEAD-initialized index. Raw Git blobs
preserve exact file bytes; existing gitlinks stay at the captured parent tree.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import stat
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path("/home/barberb/lift_coding")
OUTPUT = ROOT / "artifacts/autoformalization-publication-20261004/canonical_git/snapshot-03"
REPOS = {
    "root": (ROOT, ("docs", "implementation_plan", "maintenance", "scripts", "tests", "tracking", "work", ".github",
        "artifacts/autoformalization-alignment-20261003", "artifacts/autoformalization-publication-20261004")),
    "datasets": (ROOT / "external/ipfs_datasets", ("ipfs_datasets_py", "tests", "docs", "scripts", "benchmarks", "configs", "data/logic", ".github")),
    "accelerate": (ROOT / "external/ipfs_accelerate", ("ipfs_accelerate_py", "test", "tests", "docs", "scripts", "benchmarks", ".github", "container-qualification", "containers", "ipfs_accelerate_js")),
    "kit": (ROOT / "external/ipfs_kit", ("ipfs_kit_py", "tests", "docs", "tools", "scripts", ".github")),
    "mcp_cpp": (ROOT / "Mcp-Plus-Plus", ("include", "src", "test", "tests", "docs", "tools", "config", "configs", "examples", ".github")),
    "hallucinate": (ROOT / "hallucinate_app", ("src", "web", "app", "public", "scripts", "docs", "tests", ".github")),
    "swissknife": (ROOT / "swissknife", ("src", "web", "test", "tests", "docs", "scripts", "packages", ".github")),
}
BLOCKED_PARTS = {".git", "node_modules", ".venv", "venv", "__pycache__", ".pytest_cache", ".ruff_cache", "site-packages"}
BINARY_SUFFIXES = {".safetensors", ".bin", ".pt", ".pth", ".pkl", ".pickle", ".h5", ".ckpt", ".gguf", ".onnx",
    ".tar", ".gz", ".tgz", ".xz", ".zip", ".7z", ".parquet", ".arrow", ".sqlite", ".duckdb", ".pdf", ".png", ".jpg", ".jpeg",
    ".gif", ".ico", ".mp3", ".mp4", ".wav", ".so", ".o", ".a", ".exe", ".dll", ".class", ".pyc"}
SOURCE_SUFFIXES = {".py", ".sh", ".bash", ".js", ".ts", ".tsx", ".jsx", ".mjs", ".cjs", ".c", ".cc", ".cpp", ".h", ".hpp",
    ".rs", ".go", ".java", ".kt", ".swift", ".lean", ".v", ".tla", ".md", ".rst", ".txt", ".json", ".jsonl", ".yaml", ".yml",
    ".toml", ".ini", ".cfg", ".conf", ".xml", ".html", ".css", ".scss", ".svg", ".csv", ".sql", ".cmake", ".proto", ".lock", ".map"}
MAX_FILE = 100 * 1024 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def raw(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(raw(value)).hexdigest()


def save(path, value):
    value["content_sha256"] = digest(value)
    with Path(path).open("x", encoding="utf-8") as stream:
        os.chmod(path, 0o600)
        json.dump(value, stream, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    data = Path(path).read_bytes()
    return {"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def git(repo, *args, data=None, index=None):
    env = dict(os.environ)
    env["GIT_OPTIONAL_LOCKS"] = "0"
    if index is not None:
        env["GIT_INDEX_FILE"] = str(index)
    command = ["git", "-c", "gc.auto=0", "-c", "maintenance.auto=false", "-c", "core.fsmonitor=false"]
    if index is not None:
        command.extend(["-c", "core.sparseCheckout=false", "-c", "core.sparseCheckoutCone=false", "-c", "index.sparse=false"])
    command.extend(args)
    result = subprocess.run(command, cwd=repo, input=data, capture_output=True, env=env,
                            timeout=120, check=False)
    require(result.returncode == 0, "Git operation failed: " + " ".join(args[:2]) + ": " + result.stderr.decode("utf-8", "replace")[:1000])
    return result.stdout


def paths(data):
    return [os.fsdecode(item) for item in data.split(b"\x00") if item]


def index_binding(repo):
    target = Path(os.fsdecode(git(repo, "rev-parse", "--git-path", "index").strip()))
    if not target.is_absolute():
        target = repo / target
    if not target.exists():
        return {"path": str(target), "present": False}
    data = target.read_bytes()
    return {"path": str(target), "present": True, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def refs(repo):
    result = {}
    for line in git(repo, "for-each-ref", "--format=%(refname) %(objectname)", "refs/heads").decode().splitlines():
        name, identity = line.split(" ")
        result[name] = identity
    return result


def file_state(repo, name):
    path = repo / name
    if not path.exists() and not path.is_symlink():
        return {"state": "deleted", "path": name}, None
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode), "source must be regular file or symlink")
    require(info.st_size <= MAX_FILE, "source exceeds file cap")
    if stat.S_ISLNK(info.st_mode):
        data, mode = os.fsencode(os.readlink(path)), "120000"
    else:
        data, mode = path.read_bytes(), "100755" if info.st_mode & 0o111 else "100644"
    return {"state": "present", "path": name, "mode": mode, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}, data


def eligibility(repo, name, tracked):
    parts, basename = Path(name).parts, Path(name).name.lower()
    require(not Path(name).is_absolute() and ".." not in parts, "relative Git path required")
    if set(parts) & BLOCKED_PARTS:
        return "dependency_or_runtime_path"
    if basename in {"token", "tokens", "secrets", "credentials", "id_rsa", "id_ed25519", "secrets.json", "credentials.json", "token.json"}:
        return "credential_material"
    if basename.startswith(".env") and not any(word in basename for word in ("example", "sample", "template")):
        return "environment_secret"
    if Path(name).suffix.lower() in {".pem", ".key", ".p12", ".pfx", ".jks"}:
        return "key_material"
    if Path(name).suffix.lower() in BINARY_SUFFIXES:
        return "binary_or_weight_artifact"
    if name.startswith("artifacts/autoformalization-publication-20261004/canonical_git/snapshot-"):
        return "own_runtime_receipts_and_indexes"
    if name.startswith("artifacts/autoformalization-publication-20261004/git/git_inventory"):
        return "large_raw_inventory"
    if name.startswith("artifacts/autoformalization-publication-20261004/huggingface/retained-lanes-v1/"):
        return "retained_model_copy"
    path = repo / name
    if path.exists() and path.lstat().st_size > MAX_FILE:
        return "file_exceeds_100mib"
    if not tracked:
        if any(part in {"workspace", "downloads", "vendor", "runtime", "dist", "build"} for part in parts):
            return "generated_untracked_path"
        if Path(name).suffix.lower() not in SOURCE_SUFFIXES and not (len(parts) == 1 and basename in {
            ".gitignore", ".gitattributes", ".gitmodules", "dockerfile", "makefile", "cmakelists.txt", "license", "copying", "readme"}):
            return "unsupported_untracked_source_type"
    if path.exists() and path.is_file() and not path.is_symlink():
        with path.open("rb") as stream:
            if b"\x00" in stream.read(8192):
                return "binary_payload"
    return None


def snapshot(name, repo, roots, directory):
    head = git(repo, "rev-parse", "HEAD").decode().strip()
    # Symbolic-ref exit one is expected for a detached HEAD.
    result = subprocess.run(["git", "symbolic-ref", "--quiet", "HEAD"], cwd=repo, capture_output=True, check=False)
    require(result.returncode in (0, 1), "HEAD identity read failed")
    branch = result.stdout.decode().strip() or None
    original_index, original_refs = index_binding(repo), refs(repo)
    entries = {}
    for item in git(repo, "ls-tree", "-r", "-z", head).split(b"\x00"):
        if item:
            metadata, path = item.split(b"\t", 1)
            entries[os.fsdecode(path)] = metadata.split()[0].decode()
    current_gitlinks = set()
    for item in git(repo, "ls-files", "--stage", "-z").split(b"\x00"):
        if item:
            metadata, path = item.split(b"\t", 1)
            if metadata.split()[0] == b"160000":
                current_gitlinks.add(os.fsdecode(path))
    tracked = paths(git(repo, "diff", "--no-ext-diff", "--no-renames", "--name-only", "-z", head, "--"))
    untracked = paths(git(repo, "ls-files", "--others", "--exclude-standard", "-z", "--", *roots, ":(top,glob)*"))
    chosen, omitted, gitlinks = [], [], []
    for path in sorted(set(tracked) | set(untracked)):
        if entries.get(path) == "160000" or path in current_gitlinks:
            gitlinks.append(path)
            continue
        reason = eligibility(repo, path, path in tracked)
        if reason is not None:
            omitted.append({"path": path, "reason": reason, "tracked": path in tracked})
            continue
        state, _ = file_state(repo, path)
        state["selection"] = "actual_tracked_diff_HEAD" if path in tracked else "effective_unignored_explicit_source_root"
        chosen.append(state)
    syntax_errors = []
    for state in chosen:
        if state["state"] == "present" and state["path"].endswith(".py"):
            try:
                ast.parse((repo / state["path"]).read_bytes(), filename=state["path"])
            except (SyntaxError, UnicodeError) as error:
                syntax_errors.append({"path": state["path"], "line": getattr(error, "lineno", None), "error": str(getattr(error, "msg", type(error).__name__))})
    temp_root = Path(tempfile.mkdtemp(prefix=name + "-index-", dir=directory))
    os.chmod(temp_root, 0o700)
    index = temp_root / "index"
    git(repo, "read-tree", head, index=index)
    staged_entries = []
    for state in chosen:
        actual, data = file_state(repo, state["path"])
        require(actual == {k: v for k, v in state.items() if k != "selection"}, "selected source changed before staging")
        if data is None:
            mode, blob = "0", "0" * 40
        else:
            mode, blob = state["mode"], git(repo, "hash-object", "-w", "--stdin", data=data).decode().strip()
        staged_entries.append(mode.encode() + b" " + blob.encode() + b"\t" + os.fsencode(state["path"]) + b"\x00")
    if staged_entries:
        git(repo, "update-index", "-z", "--index-info", data=b"".join(staged_entries), index=index)
    tree = git(repo, "write-tree", index=index).decode().strip()
    actual_changed = set(paths(git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", "-z", head, tree)))
    require(actual_changed <= {state["path"] for state in chosen}, "snapshot changed an unselected HEAD path")
    for state in chosen:
        if state["state"] == "present":
            blob = git(repo, "show", tree + ":" + state["path"])
            require(hashlib.sha256(blob).hexdigest() == state["sha256"], "snapshot blob differs from source bytes")
    for path in gitlinks:
        require(git(repo, "ls-tree", head, "--", path) == git(repo, "ls-tree", tree, "--", path), "gitlink changed in source snapshot")
    commit = git(repo, "-c", "commit.gpgsign=false", "commit-tree", tree, "-p", head,
        data=("Snapshot canonical source work for autoformalization publication\n\nRepository: " + name + "\nPreserve existing HEAD, branches and index.\n").encode()).decode().strip()
    new_ref = "refs/heads/publication/canonical-complete-20261004/" + hashlib.sha256(str(repo).encode()).hexdigest()[:24]
    git(repo, "update-ref", new_ref, commit, "0" * 40)
    require(git(repo, "rev-parse", "HEAD").decode().strip() == head, "original HEAD changed")
    require(index_binding(repo) == original_index, "original index changed")
    current_refs = refs(repo)
    require(all(current_refs.get(key) == value for key, value in original_refs.items()), "preexisting branch changed")
    for state in chosen:
        actual, _ = file_state(repo, state["path"])
        require(actual == {k: v for k, v in state.items() if k != "selection"}, "selected worktree source changed: " + state["path"])
    with index.open("rb") as stream:
        os.fsync(stream.fileno())
    report = {"schema": "canonical-source-snapshot/v1", "repository": str(repo), "name": name,
        "original_head": head, "original_branch": branch, "original_index": original_index,
        "snapshot_tree": tree, "snapshot_commit": commit, "snapshot_ref": new_ref,
        "tracked_diff_count": len(tracked), "eligible_untracked_count": sum(state["selection"].startswith("effective") for state in chosen),
        "selected_file_count": len(chosen), "changed_tree_path_count": len(actual_changed), "selected_files": chosen,
        "omitted_files": omitted, "gitlinks_deferred": gitlinks, "python_syntax_errors": syntax_errors,
        "temporary_index": str(index), "original_head_index_branches_and_selected_file_bytes_preserved": True,
        "gitlink_changes_executed": False, "main_merge_executed": False, "origin_push_executed": False,
        "source_file_bytes_modified": False, "syntax_checked_without_imports": True}
    return report


def main():
    os.umask(0o077)
    require(not OUTPUT.exists(), "fresh snapshot output required")
    OUTPUT.mkdir(mode=0o700, parents=True)
    started, reports, bindings = time.monotonic(), [], []
    for name, (repo, roots) in REPOS.items():
        if name != "accelerate":
            continue
        report = snapshot(name, repo, roots, OUTPUT)
        reference = save(OUTPUT / (name + ".json"), report)
        reports.append(report)
        bindings.append(reference)
        print(json.dumps({"name": name, "commit": report["snapshot_commit"], "files": report["selected_file_count"],
                          "syntax_errors": len(report["python_syntax_errors"])}), flush=True)
    summary = {"schema": "canonical-seven-source-snapshots/v1", "status": "completed_source_snapshots_only",
        "snapshot_count": len(reports), "reports": bindings,
        "snapshots": [{key: value[key] for key in ("name", "repository", "original_head", "snapshot_commit", "snapshot_ref",
            "selected_file_count", "gitlinks_deferred", "python_syntax_errors")} for value in reports],
        "wall_seconds": time.monotonic() - started, "main_merge_executed": False, "origin_push_executed": False,
        "original_indexes_heads_branches_and_selected_sources_preserved": True}
    save(OUTPUT / "report.json", summary)


if __name__ == "__main__":
    main()
