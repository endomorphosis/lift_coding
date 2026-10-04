"""Prepare an isolated, unpublished Git history with exact HF artifact references.

This helper never pushes, uploads, trains, or changes the original repository.
Only exact selected path/blob pairs are replaced, by adjacent .hf.json blobs.
All already-published GitHub commit histories are excluded from rewriting.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path

BASE = Path(__file__).parent
SOURCE = Path("/home/barberb/lift_coding/external/ipfs_accelerate")
PLAN = BASE / "main-gitlink-restoration/accelerate/plan-v2.json"
PREPARED = BASE / "main-gitlink-restoration/accelerate/prepared-v2.json"
EXPECTED_TIP = "49569f1f2a9aa233e532e92c27f74ba5c004fd48"
ASSETS = {
    "data/agent_supervisor/formal_verification_tactician_readiness/bundles/index.duckdb":
        ("14d6706502842110d16161a81d168281d6989a1c", 142880768,
         "080ad89846dcc7fbef2015d8335d441a49bf38861ddf3fe311af58fcfbc0c833"),
    "data/agent_supervisor/proof_grounded_ir_learning/datasets/pgir-objective-ast.jsonl":
        ("9b6ded832adffea56cd1402bb08d1dca484eb3c8", 2022179327,
         "829685569fa11e2a699d973fed8a6d68e59d5e76c4c2205edf82e521a30d34c5"),
}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def seal(value):
    value = {key: item for key, item in value.items() if key != "content_sha256"}
    return {**value, "content_sha256": hashlib.sha256(canonical(value)).hexdigest()}


def binding(path):
    path = Path(path)
    data = path.read_bytes()
    return {"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def selected_json(pin):
    data = Path(pin["path"]).read_bytes()
    if len(data) != pin["bytes"] or hashlib.sha256(data).hexdigest() != pin["sha256"]:
        raise ValueError("selected file changed")
    return json.loads(data.decode("utf-8"))


def write(path, value):
    data = canonical(seal(value)) + b"\n"
    with Path(path).open("xb") as stream:
        os.chmod(path, 0o600)
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return binding(path)


def git(repository, *args, data=None, accepted=(0,)):
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update({"GIT_TERMINAL_PROMPT": "0", "GIT_LFS_SKIP_SMUDGE": "1"})
    result = subprocess.run(["git", "-c", "gc.auto=0", "-c", "maintenance.auto=false", "-c",
                             "core.hooksPath=/dev/null", "-C", str(repository), *args],
                            input=data, capture_output=True, env=env, check=False)
    if result.returncode not in accepted:
        raise RuntimeError(f"git {args[0]} failed: {result.stderr.decode(errors='replace')[:2000]}")
    return result.stdout


def source_state(repository, selected_files):
    index = Path(os.fsdecode(git(repository, "rev-parse", "--git-path", "index").strip()))
    if not index.is_absolute():
        index = Path(repository) / index
    files = []
    for row in selected_files:
        path = Path(repository) / row["path"]
        if path.is_symlink():
            files.append({"path": row["path"], "symlink": os.readlink(path)})
        elif path.is_file():
            files.append({"path": row["path"], **{key: item for key, item in binding(path).items() if key != "path"}})
        else:
            files.append({"path": row["path"], "absent": True})
    return {"head": git(repository, "rev-parse", "HEAD").decode().strip(), "index": binding(index),
            "refs": git(repository, "for-each-ref", "--format=%(refname) %(objectname)").decode().splitlines(),
            "selected_working_file_bytes": files}


class Objects:
    """Bounded tree/commit reader. Large source blobs are never materialized."""

    def __init__(self, repository):
        self.repository = repository
        env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        self.process = subprocess.Popen(["git", "-C", str(repository), "cat-file", "--batch"],
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, env=env)

    def read(self, oid, kind):
        self.process.stdin.write(oid.encode() + b"\n")
        self.process.stdin.flush()
        header = self.process.stdout.readline().decode().split()
        if len(header) != 3 or header[:2] != [oid, kind] or int(header[2]) > 32 * 1024 * 1024:
            raise ValueError("unexpected or excessive Git metadata object")
        data = self.process.stdout.read(int(header[2]))
        if len(data) != int(header[2]) or self.process.stdout.read(1) != b"\n":
            raise ValueError("truncated Git object")
        return data

    def put(self, kind, data):
        return git(self.repository, "hash-object", "-w", "-t", kind, "--stdin", data=data).decode().strip()

    def close(self):
        self.process.stdin.close()
        self.process.stdout.close()
        if self.process.wait() != 0:
            raise ValueError("Git object reader failed")


def tree_entries(data):
    entries, offset = [], 0
    while offset < len(data):
        space = data.index(b" ", offset)
        end = data.index(b"\0", space)
        mode, name = data[offset:space], data[space + 1:end]
        oid = data[end + 1:end + 21]
        if len(oid) != 20:
            raise ValueError("invalid SHA1 tree entry")
        entries.append((mode, name, oid.hex()))
        offset = end + 21
    return entries


def tree_bytes(entries):
    def order(entry):
        mode, name, _ = entry
        return name + (b"/" if mode == b"40000" else b"\0")
    return b"".join(mode + b" " + name + b"\0" + bytes.fromhex(oid)
                    for mode, name, oid in sorted(entries, key=order))


def rewrite_unpublished(repository, tip, published_commits, references):
    """Return exact commit/tree maps without changing any ref or working tree."""
    commits = git(repository, "rev-list", "--reverse", "--topo-order", tip, "--not", *published_commits).decode().splitlines()
    objects = Objects(repository)
    tree_map, commit_map, occurrences = {}, {}, []
    try:
        pointer_oids = {path: objects.put("blob", canonical(reference) + b"\n") for path, reference in references.items()}

        def transform(oid, prefix=""):
            key = (oid, prefix)
            if key in tree_map:
                return tree_map[key]
            original = objects.read(oid, "tree")
            entries, result = tree_entries(original), []
            names = {name for _, name, _ in entries}
            for mode, name, entry_oid in entries:
                path = prefix + os.fsdecode(name)
                if mode == b"40000" and any(target.startswith(path + "/") for target in references):
                    entry_oid = transform(entry_oid, path + "/")
                elif path in references and entry_oid == references[path]["source_git_blob_oid"]:
                    adjacent = name + b".hf.json"
                    if adjacent in names:
                        raise ValueError("adjacent HF reference would overwrite an existing historical file")
                    if mode not in (b"100644", b"100755"):
                        raise ValueError("artifact is not a regular Git blob")
                    occurrences.append({"original_tree_oid": oid, "path": path, "source_git_blob_oid": entry_oid})
                    name, entry_oid = adjacent, pointer_oids[path]
                result.append((mode, name, entry_oid))
            rewritten = tree_bytes(result)
            tree_map[key] = oid if rewritten == original else objects.put("tree", rewritten)
            return tree_map[key]

        for oid in commits:
            original = objects.read(oid, "commit")
            header, separator, message = original.partition(b"\n\n")
            if not separator or b"\ngpgsig " in header or b"\nmergetag " in header:
                raise ValueError("unsupported signed or malformed unpublished commit")
            result = []
            for line in header.split(b"\n"):
                if line.startswith(b"tree "):
                    line = b"tree " + transform(line[5:].decode()).encode()
                elif line.startswith(b"parent "):
                    parent = line[7:].decode()
                    line = b"parent " + commit_map.get(parent, parent).encode()
                result.append(line)
            rewritten = b"\n".join(result) + separator + message
            commit_map[oid] = oid if rewritten == original else objects.put("commit", rewritten)
        return {"tip": commit_map.get(tip, tip), "commit_map": commit_map,
                "tree_map": [{"old": old, "prefix": prefix, "new": new} for (old, prefix), new in tree_map.items()],
                "replaced_tree_occurrences": occurrences, "reference_blob_oids": pointer_oids}
    finally:
        objects.close()


def tree(repository, commit):
    result = {}
    for record in git(repository, "ls-tree", "-r", "-z", commit).split(b"\0"):
        if record:
            meta, path = record.split(b"\t", 1)
            mode, kind, oid = meta.decode().split()
            result[os.fsdecode(path)] = {"mode": mode, "kind": kind, "git_oid": oid}
    return result


def prepare(output):
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    plan_pin, prepared_pin = binding(PLAN), binding(PREPARED)
    plan, prepared = selected_json(plan_pin), selected_json(prepared_pin)
    if prepared["integrated_tip"] != EXPECTED_TIP or git(SOURCE, "rev-parse", plan["integration_branch"]).decode().strip() != EXPECTED_TIP:
        raise ValueError("selected restored integration tip changed")
    before = source_state(SOURCE, plan["authoritative_source"]["selected_files"])
    remote = git(SOURCE, "remote", "get-url", "origin").decode().strip()
    advertised = git(SOURCE, "ls-remote", "--refs", "origin").decode().splitlines()
    clone = output / "isolated.git"
    git(SOURCE, "clone", "--bare", "--shared", "--no-hardlinks", str(SOURCE), str(clone))
    git(clone, "remote", "set-url", "origin", remote)
    git(clone, "fetch", "--no-tags", "--recurse-submodules=no", "origin", "+refs/*:refs/published-github/*")
    actual, published_commits = [], []
    for row in advertised:
        oid, ref = row.split("\t")
        private_ref = "refs/published-github/" + ref.removeprefix("refs/")
        if git(clone, "rev-parse", private_ref).decode().strip() != oid:
            raise ValueError("published ref changed during isolated fetch")
        commit = git(clone, "rev-parse", "--verify", private_ref + "^{commit}", accepted=(0, 128)).decode().strip()
        if commit:
            published_commits.append(commit)
        actual.append({"ref": ref, "git_oid": oid, "isolated_ref": private_ref, "commit_oid": commit or None})
    if git(SOURCE, "ls-remote", "--refs", "origin").decode().splitlines() != advertised:
        raise ValueError("live published ref selection changed during capture")
    after = source_state(SOURCE, plan["authoritative_source"]["selected_files"])
    if before != after:
        raise ValueError("original repository state changed during preparation")
    result = {"schema": "isolated-hf-history-reference-preflight/v1", "original_repository": str(SOURCE),
              "isolated_repository": str(clone), "selected_plan_binding": plan_pin, "selected_prepared_binding": prepared_pin,
              "original_tip": EXPECTED_TIP, "published_refs": actual, "published_commit_exclusions": sorted(set(published_commits)),
              "original_state": before, "original_state_preserved": True, "scope": "Isolated preparation only; no conversion yet.",
              "git_lfs_migration_executed": False, "origin_push_executed": False, "hf_upload_executed": False,
              "training_executed": False}
    return write(output / "preflight.json", result)


def convert(output, artifact_binding):
    preflight_pin = binding(output / "preflight.json")
    preflight, artifacts = selected_json(preflight_pin), selected_json(artifact_binding)
    if set(artifacts) != {"schema", "rows"} or artifacts["schema"] != "hf-large-artifact-reference-selection/v1":
        raise ValueError("unsupported HF artifact selection")
    references = {}
    for row in artifacts["rows"]:
        keys = {"original_path", "source_git_blob_oid", "bytes", "sha256", "hf_repo_id", "hf_repo_type", "hf_revision", "hf_path"}
        if set(row) != keys or row["original_path"] in references or row["original_path"] not in ASSETS:
            raise ValueError("invalid or duplicate selected artifact")
        if (row["source_git_blob_oid"], row["bytes"], row["sha256"]) != ASSETS[row["original_path"]] or type(row["bytes"]) is not int:
            raise ValueError("artifact does not match the exact oversized path/blob")
        for key, length in (("sha256", 64), ("hf_revision", 40)):
            value = row[key]
            if type(value) is not str or len(value) != length or any(char not in "0123456789abcdef" for char in value):
                raise ValueError("invalid immutable HF digest/revision")
        if row["hf_repo_type"] != "dataset" or row["hf_repo_id"] != "Publicus/autoformalization-artifacts":
            raise ValueError("unexpected HF artifact repository")
        if row["hf_path"] != "releases/20261004-git-large-artifacts-v1/" + row["original_path"]:
            raise ValueError("invalid selected HF path")
        references[row["original_path"]] = {"schema": "immutable-hf-large-artifact-reference/v1", **row,
                                           "content_kind": "generated_nonweight_data", "original_raw_payload_omitted_from_this_git_tree": True}
    if set(references) != set(ASSETS):
        raise ValueError("exactly the two selected artifacts are required")
    plan = selected_json(preflight["selected_plan_binding"])
    if source_state(SOURCE, plan["authoritative_source"]["selected_files"]) != preflight["original_state"]:
        raise ValueError("original repository changed since isolated capture")
    repository = Path(preflight["isolated_repository"])
    result = rewrite_unpublished(repository, preflight["original_tip"], preflight["published_commit_exclusions"], references)
    mapped = [{**row, "original_oid": row["oid"], "oid": result["commit_map"].get(row["oid"], row["oid"])} for row in plan["heads"]]
    for row in mapped:
        git(repository, "merge-base", "--is-ancestor", row["oid"], result["tip"])
    baseline = plan["origin_main_sha256_or_git_oid"]
    git(repository, "merge-base", "--is-ancestor", baseline, result["tip"])
    old_tree, new_tree = tree(repository, preflight["original_tip"]), tree(repository, result["tip"])
    if old_tree != new_tree:
        raise ValueError("current canonical final tree unexpectedly changed")
    rows = git(repository, "rev-list", "--objects", result["tip"], "--not", *preflight["published_commit_exclusions"])
    metadata = git(repository, "cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)",
                   data=b"\n".join(row.split(b" ", 1)[0] for row in rows.splitlines()) + b"\n")
    excessive = [row.decode() for row in metadata.splitlines() if row.split()[1] == b"blob" and int(row.split()[2]) > 100 * 1024 * 1024]
    if excessive:
        raise ValueError("converted unpublished history still contains oversized Git blobs")
    if source_state(SOURCE, plan["authoritative_source"]["selected_files"]) != preflight["original_state"]:
        raise ValueError("original repository changed during conversion")
    selected_ref = "refs/heads/publication/hf-references-20261004/accelerate"
    git(repository, "update-ref", selected_ref, result["tip"], "0" * 40)
    report = {"schema": "isolated-hf-history-reference-conversion/v1", "preflight_binding": preflight_pin,
              "artifact_selection_binding": artifact_binding, "original_tip": preflight["original_tip"],
              "converted_tip": result["tip"], "converted_ref": selected_ref, "isolated_repository": str(repository),
              "commit_map": result["commit_map"], "tree_map": result["tree_map"], "mapped_selected_heads": mapped,
              "replaced_tree_occurrences": result["replaced_tree_occurrences"], "references": references,
              "reference_blob_oids": result["reference_blob_oids"], "all_mapped_selected_heads_ancestors": True,
              "published_main_unchanged_and_ancestor": True, "final_current_tree_exactly_preserved": True,
              "original_repository_state_preserved": True, "newly_reachable_oversized_git_blob_count": 0,
              "original_rewritten_commit_oids_remote_ancestry_claimed": False, "signature_headers_modified": False,
              "git_lfs_migration_executed": False, "git_lfs_upload_executed": False, "origin_push_executed": False,
              "hf_upload_executed": False, "training_executed": False,
              "scope": "Exact oversized historical path/blob substitutions; selected HF reference content is externally pinned, not fetched by this helper."}
    return write(output / "conversion.json", report)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("prepare", "convert"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--artifact-selection-binding", type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    if args.operation == "prepare":
        result = prepare(args.output)
    elif args.artifact_selection_binding:
        result = convert(args.output, json.loads(args.artifact_selection_binding.read_bytes()))
    else:
        parser.error("conversion requires an external artifact-selection file binding")
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
