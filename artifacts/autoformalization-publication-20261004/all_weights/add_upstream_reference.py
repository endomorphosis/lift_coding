"""Append one verified upstream reference without changing staged weight files."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def raw(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode()


def binding(path):
    data = path.read_bytes()
    return {"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--reference-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    old_pin, reference_pin = binding(args.plan), binding(args.reference)
    if old_pin["sha256"] != args.plan_sha256 or reference_pin["sha256"] != args.reference_sha256:
        raise ValueError("selected plan or reference changed")
    plan = json.loads(args.plan.read_bytes())
    old_body = {key: value for key, value in plan.items() if key != "content_sha256"}
    if hashlib.sha256(raw(old_body)).hexdigest() != plan["content_sha256"]:
        raise ValueError("original plan seal differs")
    if (plan["schema"], plan["repo_id"], plan["repo_type"], plan["prefix"]) != (
        "append-only-HF-publication-plan/v1", "Publicus/legal-ir-autoencoder", "model",
        "releases/20261005-all-project-weights-v1",
    ):
        raise ValueError("selected destination differs")
    reference = json.loads(args.reference.read_bytes())
    if reference.get("remote_exact_LFS_metadata_checked") is not True:
        raise ValueError("verified upstream reference required")
    directory = Path(plan["directory"])
    relative = "upstream-leanstral-reference.json"
    if any(row["path"] == relative for row in plan["files"]):
        raise ValueError("upstream reference already selected")
    destination = directory / relative
    if any(path.is_symlink() for path in (destination, *destination.parents)) or args.output.exists():
        raise ValueError("fresh ordinary destination required")
    data = args.reference.read_bytes()
    with destination.open("xb") as stream:
        stream.write(data)
    extended = {**old_body,
                "files": [*old_body["files"], {"path": relative, "bytes": len(data),
                           "sha256": reference_pin["sha256"]}],
                "original_input_bindings": [*old_body["original_input_bindings"], old_pin,
                                             reference_pin, binding(Path(__file__).resolve())],
                "tracking_metadata_policy": "allow_only_exact_selected_path_LFS_additions"}
    extended["content_sha256"] = hashlib.sha256(raw(extended)).hexdigest()
    payload = raw(extended) + b"\n"
    if len(payload) > 1024 * 1024:
        raise ValueError("extended plan exceeds retained bound")
    with args.output.open("xb") as stream:
        stream.write(payload)
    print(json.dumps({"plan_binding": binding(args.output), "original_plan_binding": old_pin,
                      "existing_weight_file_selections_unchanged": True,
                      "added_file": relative, "added_reference_binding": reference_pin}))


if __name__ == "__main__":
    main()
