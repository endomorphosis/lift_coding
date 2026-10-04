"""Prepare exact leaf integration plans after the source-import readiness signal.

The selected root integration helper owns all merges. This driver checks its
frozen source bytes and preserves the canonical original HEAD and physical index.
It never pushes, fetches, changes original source files, or starts training.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import subprocess
from pathlib import Path

ROOT = Path("/home/barberb/lift_coding")
BASE = ROOT / "artifacts/autoformalization-publication-20261004/canonical_git"
HELPER = BASE.parent / "integrate_main.py"
HELPER_SHA = "98a07d90178b724ba28aeed8f7bc82e374ab0c93b172ff231b13f2283147e8a3"
REPORTS = {"accelerate": "snapshot-03", "kit": "snapshot-02", "mcp_cpp": "snapshot-02",
           "hallucinate": "snapshot-02", "swissknife": "snapshot-02"}
REPORT_SHA = {
    "accelerate": "e427440603e0109bb64815706e452c62258154e8a9f539a47e0aeb1291412041",
    "kit": "0418bef84439968287d5866051355ffb2e0ca260bc49eacb98d9dc33b2ad3709",
    "mcp_cpp": "3eda9a88e96daf8332f05f789ac267b3d0440ed54d32881ccc0ed2adcfd0836b",
    "hallucinate": "07b8cf08ae6057858f3cd1737735fde0254e30182f887b3389573ec011f8c3e2",
    "swissknife": "ff6de00c863e3a1d2013ead4a86673f2dd5bf57f28980ebf7a695fdb95278bea",
}


def git(repository, *args):
    return subprocess.check_output(["git", "-c", "gc.auto=0", *args], cwd=repository,
                                   env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"})


def sha(data):
    return hashlib.sha256(data).hexdigest()


def binding(path):
    data = path.read_bytes()
    return {"path": str(path), "bytes": len(data), "sha256": sha(data)}


def write(path, value):
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode() + b"\n"
    with path.open("xb") as stream:
        os.chmod(path, 0o600)
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return binding(path)


def index_binding(repository):
    path = Path(os.fsdecode(git(repository, "rev-parse", "--git-path", "index").strip()))
    if not path.is_absolute():
        path = repository / path
    return binding(path) if path.exists() else {"path": str(path), "present": False}


def verify_sources(repository, selected_files):
    for selected in selected_files:
        path = repository / selected["path"]
        if selected["state"] == "deleted":
            if path.exists() or path.is_symlink():
                raise ValueError("deleted source reappeared: " + selected["path"])
            continue
        data = os.fsencode(os.readlink(path)) if path.is_symlink() else path.read_bytes()
        mode = "120000" if path.is_symlink() else "100755" if path.stat().st_mode & stat.S_IXUSR else "100644"
        if sha(data) != selected["sha256"] or mode != selected["mode"]:
            raise ValueError("selected canonical source changed: " + selected["path"])


def prepare(name, execute):
    if binding(HELPER)["sha256"] != HELPER_SHA:
        raise ValueError("selected root integration helper changed")
    report_path = BASE / REPORTS[name] / (name + ".json")
    if binding(report_path)["sha256"] != REPORT_SHA[name]:
        raise ValueError("selected canonical snapshot report changed")
    canonical = json.loads(report_path.read_text())
    repository = Path(canonical["repository"])
    verify_sources(repository, canonical["selected_files"])
    original_head = git(repository, "rev-parse", "HEAD").decode().strip()
    original_index = index_binding(repository)
    origin = git(repository, "remote", "get-url", "origin").decode().strip().removesuffix(".git").removesuffix("/")
    if not origin.startswith("https://github.com/endomorphosis/"):
        raise ValueError("owned canonical HTTPS origin required")
    normalized = origin.removeprefix("https://")
    baseline = git(repository, "rev-parse", "origin/main").decode().strip()
    selected_refs = {}
    for line in git(repository, "for-each-ref", "--format=%(refname) %(objectname)", "refs/heads",
                    "refs/remotes/publication-history-20261004", "refs/remotes/publication-wip-20261004").decode().splitlines():
        ref, oid = line.split()
        selected_refs.setdefault(oid, []).append(ref)
    selected_refs.pop(canonical["snapshot_commit"], None)
    heads = [{"oid": oid, "kind": "preserved_history_or_worktree", "selected_refs": refs}
             for oid, refs in sorted(selected_refs.items())]
    heads.append({"oid": canonical["snapshot_commit"], "kind": "canonical_current_source",
                  "selected_refs": [canonical["snapshot_ref"]]})
    directory = BASE / "main-preparation" / name
    directory.mkdir(mode=0o700, parents=True, exist_ok=False)
    plan = {"schema": "canonical-leaf-main-integration-plan/v1", "canonical_repository": str(repository),
            "normalized_origin": normalized, "baseline_remote_ref": "origin/main",
            "origin_main_sha256_or_git_oid": baseline,
            "fresh_worktree": str(ROOT / ".worktrees/publication-main-20261004" / name),
            "integration_branch": "publication/main-20261004/" + name, "heads": heads,
            "authoritative_source": {"snapshot_commit": canonical["snapshot_commit"],
                                     "selected_files": canonical["selected_files"]},
            "published_gitlinks": [], "integration_helper_binding": binding(HELPER),
            "canonical_snapshot_report_binding": binding(report_path),
            "original_head": original_head, "original_index_binding": original_index,
            "source_import_readiness_required_before_invocation": True,
            "origin_push_authorized_for_driver": False, "training_authorized_for_driver": False}
    selected_plan = write(directory / "plan.json", plan)
    print(json.dumps({"name": name, "plan_binding": selected_plan, "head_count": len(heads)}), flush=True)
    if execute:
        subprocess.run(["python", str(HELPER), "--plan", selected_plan["path"], "--plan-sha", selected_plan["sha256"],
                        "--output", str(directory / "integration-01")], check=True)
        if git(repository, "rev-parse", "HEAD").decode().strip() != original_head or index_binding(repository) != original_index:
            raise ValueError("canonical original HEAD or index changed")
        if binding(HELPER)["sha256"] != HELPER_SHA:
            raise ValueError("root helper changed during integration")
        verify_sources(repository, canonical["selected_files"])
        write(directory / "original-preservation.json", {
            "schema": "canonical-leaf-original-state-preservation/v1", "name": name,
            "original_head": original_head, "original_index_binding": original_index,
            "original_head_and_index_preserved": True, "original_selected_source_bytes_preserved": True,
            "origin_push_executed": False, "training_executed": False,
            "prepared_binding": binding(directory / "integration-01/prepared.json"), "plan_binding": selected_plan})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--targets", nargs="+", choices=list(REPORTS), required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    os.umask(0o077)
    for name in args.targets:
        prepare(name, args.execute)


if __name__ == "__main__":
    main()
