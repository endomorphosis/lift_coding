"""Collect externally selected successful publications before reconstruction fits."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent


def raw(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def bind(path):
    data = path.read_bytes()
    return {"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def load(binding):
    path = Path(binding["path"])
    if bind(path) != binding:
        raise ValueError("selected publication file differs")
    value = json.loads(path.read_bytes())
    body = raw({k: v for k, v in value.items() if k != "content_sha256"})
    if value.get("schema") == "retained-HF-append-only-publication/v1":
        body += b"\n"
    if value.get("content_sha256") != hashlib.sha256(body).hexdigest():
        raise ValueError("selected publication seal differs")
    return value


def save(path, value):
    value["content_sha256"] = hashlib.sha256(raw(value)).hexdigest()
    with path.open("xb") as stream:
        stream.write(raw(value) + b"\n")
    return bind(path)


def create(selection_path, selected_sha, output):
    binding = bind(selection_path)
    if binding["sha256"] != selected_sha:
        raise ValueError("external publication selection differs")
    selection = load(binding)
    if set(selection) != {"schema", "git_publications", "hf_publications", "content_sha256"} or selection["schema"] != "initial-publication-gate-selection/v1":
        raise ValueError("closed publication selection required")
    repositories, git_rows, hf_rows = set(), [], []
    for binding in selection["git_publications"]:
        receipt = load(binding)
        origin = receipt["normalized_origin"]
        if receipt.get("schema") != "git-integrated-main-publication/v1" or receipt.get("status") != "published_and_verified" or receipt.get("remote_publication_verified") is not True:
            raise ValueError("verified Git publication required")
        if origin in repositories or not origin.startswith("github.com/endomorphosis/") or receipt["integrated_tip"] != receipt["remote_main_after"]:
            raise ValueError("unique actual owned main publication required")
        repositories.add(origin)
        git_rows.append({"normalized_origin": origin, "published_main_oid": receipt["remote_main_after"], "receipt_binding": binding})
    if len(repositories) != 16:
        raise ValueError("all sixteen selected owned repository publications required")
    destinations = set()
    for binding in selection["hf_publications"]:
        receipt = load(binding)
        profile = receipt.get("schema")
        verified = (profile == "append-only-HF-publication/v1" and receipt.get("status") == "published_and_verified"
                    and receipt.get("all_remote_files_verified") is True) or (
                    profile == "retained-HF-append-only-publication/v1" and receipt.get("remote_verification_completed") is True)
        if not verified:
            raise ValueError("verified immutable HF publication required")
        key = (receipt["repo_id"], receipt["prefix"])
        if key in destinations or not receipt["remote_files"]:
            raise ValueError("unique nonempty HF release required")
        destinations.add(key)
        hf_rows.append({"repo_id": receipt["repo_id"], "prefix": receipt["prefix"], "revision": receipt["commit_oid"],
            "verified_file_count": len(receipt["remote_files"]), "receipt_binding": binding})
    if len(hf_rows) != 9:
        raise ValueError("all nine initial immutable HF releases required")
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    aggregate = save(output / "initial-publications.json", {"schema": "verified-initial-publications-before-reconstruction/v1",
        "selection_binding": bind(selection_path), "git_publications": git_rows, "hf_publications": hf_rows,
        "verification_scope": "Exact root-selected successful receipt identities; remote OIDs were observed by each publisher, not authenticated by training workers.",
        "training_executed": False, "proof_authority": False, "semantic_fit_admission": False})
    gate = save(output / "publication-gate.json", {"schema": "reconstruction-publication-gate/v1",
        "published_artifact_receipts_sha256": aggregate["sha256"], "training_release_authorized": True})
    print(json.dumps({"aggregate_binding": aggregate, "gate_binding": gate}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--selection-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    create(args.selection, args.selection_sha256, args.output)
