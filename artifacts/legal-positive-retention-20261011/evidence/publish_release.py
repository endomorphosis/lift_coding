"""Append one reviewed positive-retention release and verify immutable bytes.

This module does nothing when imported. main() performs the authorized upload;
the fresh observed parent commit guards it. Existing prefixes/receipts refuse
execution, and uncertain outcomes require explicit reconciliation before retry.
"""
from __future__ import annotations

import argparse
from hashlib import sha1, sha256
import json
import os
from pathlib import Path, PurePosixPath
import re

F = Path(__file__).resolve().parent
REPO = "Publicus/legal-ir-autoencoder"
PREFIX = "experiments/positive-retention-20261011/run-01"
ARMS = ("bce", "positive_margin")
STEPS = (0, 120, 240)
RECEIPTS = ("hub-upload-parent.json", "hub-upload-proposal.json", "hub-upload-commit.json",
            "hub-upload-error.json", "hub-readback-verification.json", "hub-all-checkpoint-downloads.json")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def pin(raw):
    return {"bytes": len(raw), "sha256": sha256(raw).hexdigest()}


def closed_pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def read_json(path):
    return json.loads(Path(path).read_bytes(), object_pairs_hook=closed_pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonfinite JSON")))


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def write(path, value):
    raw = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    with Path(path).open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    sync_directory(Path(path).parent)


def write_bytes(path, raw):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    sync_directory(path.parent)


def relative_path(value):
    require(type(value) is str and value and str(PurePosixPath(value)) == value
            and not value.startswith("/") and ".." not in PurePosixPath(value).parts,
            "ordinary relative release path required")
    return value


def observe(api, revision=None):
    info = api.model_info(REPO, revision=revision, files_metadata=True)
    require(type(info.sha) is str and re.fullmatch(r"[0-9a-f]{40,64}", info.sha) is not None,
            "actual Hub commit identity required")
    files = {}
    for item in info.siblings:
        path = relative_path(item.rfilename)
        require(path not in files and type(item.size) is int and item.size >= 0,
                "complete unique remote file metadata required")
        lfs = item.lfs.sha256 if item.lfs else None
        require(type(item.blob_id) is str and re.fullmatch(r"[0-9a-f]{40,64}", item.blob_id) is not None,
                "remote Git blob identity required")
        require(lfs is None or type(lfs) is str and re.fullmatch(r"[0-9a-f]{64}", lfs) is not None,
                "remote LFS content identity required")
        files[path] = {"blob_id": item.blob_id, "size": item.size, "lfs_sha256": lfs}
    return {"repo": REPO, "revision": info.sha, "files": files}


def verify_local(stage):
    require(stage.is_dir() and not stage.is_symlink(), "ordinary prepared release directory required")
    manifest = read_json(stage / "release-manifest.json")
    require(manifest["schema"] == "positive-retention-release-manifest/v1"
            and manifest["repo"] == REPO and manifest["prefix"] == PREFIX
            and manifest["self_excluded"] == "release-manifest.json", "prepared release target/manifest differs")
    files = {}
    for path in stage.rglob("*"):
        require(not path.is_symlink(), "release symlinks are refused")
        if path.is_file():
            files[relative_path(str(path.relative_to(stage)))] = pin(path.read_bytes())
    require(set(files) == set(manifest["files"]) | {"release-manifest.json"},
            "manifest must cover every nonmanifest release file, with no extras")
    for relative, record in manifest["files"].items():
        require(files[relative] == {key: record[key] for key in ("bytes", "sha256")},
                "prepared release file changed: " + relative)
    inventory = read_json(stage / manifest["checkpoint_inventory"])
    roles = inventory["checkpoint_files"]
    expected = {"checkpoints/" + arm + "/checkpoint-" + str(step) + ".json" for arm in ARMS for step in STEPS}
    expected |= {"checkpoints/" + arm + "/checkpoint.json" for arm in ARMS}
    require(set(roles) == expected and len(roles) == manifest["numerical_checkpoint_files"] == 8,
            "all six original states and two aliases required")
    for relative, role in roles.items():
        require(files[relative] == {key: role[key] for key in ("bytes", "sha256")}, "checkpoint role/file binding differs")
        if relative.endswith("/checkpoint.json"):
            require(role["aliases"] in roles and (stage / relative).read_bytes() == (stage / role["aliases"]).read_bytes(),
                    "selected alias is not byte-exact")
    return manifest, files, roles


def publish(args):
    # SDK and credentials are reached only by this explicitly executed function.
    from huggingface_hub import HfApi, hf_hub_download

    root, stage, mirror = args.artifacts_root.resolve(), args.release.resolve(), args.readback.resolve()
    require(root.is_dir() and not mirror.exists(), "fresh readback directory required")
    require(all(not (root / name).exists() for name in RECEIPTS),
            "publication receipt already exists; resolve a previous/uncertain outcome before retry")
    manifest, local_files, roles = verify_local(stage)
    api = HfApi()
    before = observe(api)
    require(not any(path == PREFIX or path.startswith(PREFIX + "/") for path in before["files"]),
            "experiment prefix already exists; append-only upload refused")
    require(all(PREFIX + "/" + path not in before["files"] for path in local_files), "new release path overlaps prior files")
    write(root / "hub-upload-parent.json", before)
    write(root / "hub-upload-proposal.json", {"schema": "positive-retention-Hub-append-proposal/v1",
        "repo": REPO, "prefix": PREFIX, "parent_commit": before["revision"],
        "release_manifest": {"path": str(stage / "release-manifest.json"), **local_files["release-manifest.json"]},
        "local_files": local_files, "publisher": {"path": str(Path(__file__).resolve()), **pin(Path(__file__).read_bytes())},
        "prior_file_count": len(before["files"]), "overwrite_or_delete_allowed": False,
        "parent_observed_fresh_in_this_invocation": True})
    # Recheck immediately before the only remote mutation. No deletion patterns
    # or repo-root README/default edits are supplied to upload_folder.
    require(verify_local(stage)[1] == local_files, "local release changed before upload")
    try:
        commit = api.upload_folder(repo_id=REPO, repo_type="model", folder_path=str(stage),
            path_in_repo=PREFIX, parent_commit=before["revision"],
            commit_message="Publish matched support retention objectives and all measured research states")
    except Exception as error:
        write(root / "hub-upload-error.json", {"schema": "positive-retention-Hub-uncertain-outcome/v1",
            "repo": REPO, "prefix": PREFIX, "parent_commit": before["revision"],
            "error_type": type(error).__name__, "automatic_retry": False,
            "required_next_action": "Reconcile actual remote prefix/commit against the durable proposal before any retry; do not rerun this helper blindly."})
        raise
    revision = commit.oid
    require(type(revision) is str and re.fullmatch(r"[0-9a-f]{40,64}", revision) is not None,
            "actual upload commit required")
    write(root / "hub-upload-commit.json", {"repo": REPO, "prefix": PREFIX,
        "parent": before["revision"], "revision": revision, "url": commit.commit_url})
    after = observe(api, revision)
    require(after["revision"] == revision, "immutable after-observation revision differs")
    changed = [path for path, identity in before["files"].items() if after["files"].get(path) != identity]
    require(all(path == ".gitattributes" for path in changed), "prior file identity changed: " + repr(changed))
    attributes_append_only = False
    if changed:
        prior = Path(hf_hub_download(REPO, ".gitattributes", revision=before["revision"],
                                    cache_dir=str(root / "hub-download-cache"))).read_bytes()
        current = Path(hf_hub_download(REPO, ".gitattributes", revision=revision,
                                      cache_dir=str(root / "hub-download-cache"))).read_bytes()
        require(current.startswith(prior), "existing .gitattributes bytes rewritten")
        attributes_append_only = True
    new_paths = set(after["files"]) - set(before["files"])
    expected_paths = {PREFIX + "/" + path for path in local_files}
    require(new_paths - expected_paths <= {".gitattributes"}
            and expected_paths <= new_paths, "unexpected remote additions or missing release files")
    published = []
    for relative, expected in sorted(local_files.items()):
        raw = (stage / relative).read_bytes()
        require(pin(raw) == expected, "local release changed after upload")
        identity = after["files"].get(PREFIX + "/" + relative)
        require(identity is not None and identity["size"] == len(raw), "published file size differs")
        if identity["lfs_sha256"]:
            require(identity["lfs_sha256"] == expected["sha256"], "published LFS content identity differs")
        else:
            blob = sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
            require(identity["blob_id"] == blob, "published Git blob identity differs")
        published.append({"path": PREFIX + "/" + relative, **expected, "git_or_LFS_identity_verified": True})
    # Download every original state and alias at the immutable upload commit.
    # No checkpoint JSON is restored, no model import/forward occurs.
    downloaded = {}
    records = []
    for relative in sorted(roles):
        remote = Path(hf_hub_download(REPO, PREFIX + "/" + relative, revision=revision,
                                     cache_dir=str(root / "hub-download-cache")))
        raw = remote.read_bytes()
        require(raw == (stage / relative).read_bytes() and pin(raw) == local_files[relative],
                "downloaded checkpoint bytes differ: " + relative)
        downloaded[relative] = raw
        records.append({"path": relative, **pin(raw), "downloaded_bytes_exact": True,
                        "checkpoint_role": roles[relative]["role"]})
    require(len(downloaded) == 8, "all eight checkpoint downloads required")
    require(not mirror.exists(), "readback target was created concurrently")
    for relative, raw in downloaded.items():
        write_bytes(mirror / "all-checkpoints" / relative.removeprefix("checkpoints/"), raw)
    for arm in ARMS:
        relative = "checkpoints/" + arm + "/checkpoint.json"
        write_bytes(mirror / arm / "checkpoint.json", downloaded[relative])
    write(root / "hub-all-checkpoint-downloads.json", {"schema": "positive-retention-all-Hub-checkpoints/v1",
        "passed": True, "repo": REPO, "prefix": PREFIX, "revision": revision,
        "original_states": 6, "selected_aliases": 2, "checkpoint_files": 8,
        "model_restores": 0, "model_forwards": 0, "optimizer_updates": 0, "files": records})
    write(root / "hub-readback-verification.json", {"schema": "positive-retention-Hub-readback/v1",
        "passed": True, "repo": REPO, "prefix": PREFIX, "parent": before["revision"], "revision": revision,
        "prior_file_count": len(before["files"]), "prior_file_identities_preserved": True,
        "allowed_changed_prior_paths": changed, "gitattributes_append_only": attributes_append_only,
        "all_new_git_or_LFS_identities_verified": True, "new_file_count": len(published),
        "all_eight_checkpoints_downloaded_byte_exact": True, "both_selected_aliases_downloaded_byte_exact": True,
        "selected_alias_mirror": str(mirror), "files": published,
        "default_or_ModelManager_promotion": False, "model_restores": 0, "model_forwards": 0})
    return {"repo": REPO, "prefix": PREFIX, "revision": revision, "new_files": len(published),
            "prior_files_preserved": len(before["files"]), "all_eight_checkpoint_downloads_byte_exact": True,
            "selected_mirrors": [str(mirror / arm / "checkpoint.json") for arm in ARMS]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", type=Path, default=F / "release")
    parser.add_argument("--artifacts-root", type=Path, default=F)
    parser.add_argument("--readback", type=Path, default=F / "hub-readback")
    print(json.dumps(publish(parser.parse_args()), indent=2))


if __name__ == "__main__":
    main()
