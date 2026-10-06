"""Independently audit all inventoried model-weight staging without model imports."""

from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import json
import math
import os
import stat
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CHUNK = 1024 * 1024
MASKS = {"qualified": False, "source_fidelity_established": False,
         "proof_authority": False, "semantic_gold_created": False}


def demand(value, message):
    if not value:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode()


def unique_object(pairs):
    value = {}
    for key, item in pairs:
        demand(key not in value, "duplicate JSON key")
        value[key] = item
    return value


def parse(data):
    return json.loads(data, object_pairs_hook=unique_object,
                      parse_constant=lambda _value: (_ for _ in ()).throw(ValueError("nonfinite JSON")))


def binding(path):
    path = Path(path).absolute()
    demand(not any(p.is_symlink() for p in (path, *path.parents)), "symlink input")
    before = path.stat()
    demand(stat.S_ISREG(before.st_mode), "ordinary file required")
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(CHUNK), b""):
            size += len(chunk)
            digest.update(chunk)
    after = path.stat()
    demand((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
           == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns),
           "input changed while hashing")
    return {"path": str(path), "bytes": size, "sha256": digest.hexdigest()}


def check(selected):
    demand(binding(selected["path"]) == selected, "file binding differs")


def sealed_document(selected):
    check(selected)
    demand(selected["bytes"] <= 128 * CHUNK, "bounded metadata required")
    value = parse(Path(selected["path"]).read_bytes())
    check(selected)
    demand(isinstance(value, dict), "metadata object required")
    digest = value.get("content_sha256")
    body = {key: item for key, item in value.items() if key != "content_sha256"}
    demand(hashlib.sha256(canonical(body)).hexdigest() == digest, "metadata seal differs")
    return value


def numeric_count(value):
    if type(value) in (int, float):
        demand(type(value) is int or math.isfinite(value), "nonfinite saved state")
        return 1
    if isinstance(value, dict):
        return sum(numeric_count(item) for item in value.values())
    if isinstance(value, list):
        return sum(numeric_count(item) for item in value)
    demand(value is None or type(value) in (str, bool), "unexpected JSON state value")
    return 0


def descriptor(value):
    fields = ("json_pointer", "key", "numeric_leaf_count", "canonical_json_sha256",
              "canonical_json_bytes", "optimizer_only", "state_parameter_key_count")
    result = {key: value[key] for key in fields if key in value}
    if "state_parameter_key_count" in result:
        demand(type(result["state_parameter_key_count"]) is int
               and result["state_parameter_key_count"] >= 0, "invalid parameter key count")
    if "state_parameter_keys" in value:
        keys = value["state_parameter_keys"]
        if isinstance(keys, list):
            demand(all(type(key) is str for key in keys) and len(keys) == len(set(keys)),
                   "unique string parameter keys required")
            count = len(keys)
        else:
            demand(type(keys) is int and keys >= 0, "invalid legacy parameter key count")
            count = keys
        demand("state_parameter_key_count" not in result or result["state_parameter_key_count"] == count,
               "parameter key list and count conflict")
        result["state_parameter_key_count"] = count
    return result


def alias(path):
    return str(Path(path).relative_to(ROOT))


def stream_gzip(selected, storage, collect=False):
    check(selected)
    with Path(selected["path"]).open("rb") as stream:
        header = stream.read(10)
    demand(header[:3] == b"\x1f\x8b\x08" and header[3] == 0
           and header[4:8] == b"\x00\x00\x00\x00" and header[8] == 4,
           "gzip header differs from empty-name mtime-zero level-one recipe")
    size = 0
    digest = hashlib.sha256()
    data = bytearray() if collect else None
    with gzip.open(selected["path"], "rb") as stream:
        for chunk in iter(lambda: stream.read(CHUNK), b""):
            size += len(chunk)
            demand(size <= storage["uncompressed_bytes"], "gzip output exceeds bound")
            digest.update(chunk)
            if data is not None:
                data.extend(chunk)
    demand(size == storage["uncompressed_bytes"]
           and digest.hexdigest() == storage["uncompressed_sha256"], "gzip roundtrip digest differs")
    check(selected)
    return bytes(data) if data is not None else None


def audit(arguments):
    started = time.monotonic()
    selected = {"path": str(arguments.staging.absolute()),
                "bytes": arguments.staging.stat().st_size, "sha256": arguments.staging_sha256}
    staging = sealed_document(selected)
    demand(staging["schema"] == "all-project-model-weights-staging/v1"
           and staging["status"] == "prepared_and_verified", "prepared staging required")
    inventory = sealed_document(staging["inventory_binding"])
    coverage = sealed_document(staging["coverage_binding"])
    verification = sealed_document(staging["remote_verification_binding"])
    catalog = sealed_document(staging["catalog_binding"])
    plan = sealed_document(staging["publication_plan_binding"])
    originals = sealed_document(staging["original_source_alias_bindings"])
    demand(plan["original_source_alias_bindings"] == staging["original_source_alias_bindings"],
           "source alias manifest binding differs")
    demand(staging["publication_plan_binding"]["bytes"] <= CHUNK, "publication plan exceeds one MiB")
    demand(plan["repo_id"] == "Publicus/legal-ir-autoencoder" and plan["repo_type"] == "model"
           and plan["prefix"] == "releases/20261005-all-project-weights-v1", "destination differs")
    demand(verification["coverage_binding"] == staging["coverage_binding"]
           and verification["all_prior_release_files_verified"] is True
           and verification["all_current_release_paths_preserved_exact_content"] is True,
           "prior file verification differs")
    observed = {(item["repo_id"], item["immutable_revision"], item["path_in_repository"]): item
                for item in verification["remote_files"]}
    prior = {}
    for item in coverage["remote_file_references"]:
        key = (item["repo_id"], item["revision"], item["path_in_repository"])
        other = observed[key]
        demand(item["sha256"] == other["sha256"] and item["bytes"] == other["bytes"]
               and other["current_contents_unchanged"] is True, "prior byte coverage join differs")
        prior[key] = item
    demand(len(observed) == len(prior), "prior remote inventory differs")
    release = Path(plan["directory"])
    files = {}
    for item in plan["files"]:
        demand(item["path"] not in files and not Path(item["path"]).is_absolute()
               and ".." not in Path(item["path"]).parts, "unsafe or duplicate release path")
        files[item["path"]] = {**item, "path": str(release / item["path"])}
    demand(set(files) == {str(path.relative_to(release)) for path in release.rglob("*") if path.is_file()},
           "public release file closure differs")
    for item in files.values():
        check(item)
    checksum_lines = (release / "SHA256SUMS").read_text().splitlines()
    demand(checksum_lines == [f'{files[name]["sha256"]}  {name}' for name in sorted(files)
                              if name != "SHA256SUMS"], "checksum manifest differs")
    demand(staging["selected_file_count"] == len(files)
           and staging["selected_bytes"] == sum(item["bytes"] for item in files.values()),
           "selected public counts differ")
    groups = collections.defaultdict(list)
    all_sources = {}
    sidecar_sources = {}
    for item in inventory["weights"]:
        key = (item["sha256"], item["bytes"], item["format"])
        groups[key].append(item)
        demand(item["path"] not in all_sources, "duplicate inventoried source path")
        all_sources[item["path"]] = {field: item[field] for field in ("path", "bytes", "sha256")}
        sidecar = item.get("metadata_sidecar")
        if sidecar:
            demand(item["format"] == "safetensors", "sidecar for nonbinary weight")
            sidecar_sources[sidecar["path"]] = {field: sidecar[field] for field in ("path", "bytes", "sha256")}
    expected_sources = {**all_sources, **sidecar_sources}
    saved_sources = {item["path"]: item for item in originals["original_sources"]}
    demand(len(saved_sources) == len(originals["original_sources"]), "duplicate original source alias")
    for path, item in expected_sources.items():
        demand(saved_sources.get(path) == item, "original weight or sidecar alias absent")
    demand(staging["source_container_count"] == len(all_sources)
           and staging["unique_source_container_count"] == len(groups), "source container counts differ")
    records = {}
    for record in catalog["weight_containers"]:
        key = (record["source_sha256"], record["source_bytes"], record["format"])
        demand(key not in records, "duplicate catalog byte container")
        records[key] = record
    demand(set(records) == set(groups), "all inventoried contents must be represented exactly once")
    storage_counts = collections.Counter()
    used_new_files = set()
    descriptor_count = 0
    extracted_state_count = 0
    extracted_numeric_count = 0
    existing_mixed_containers = 0

    def storage_check(record, collect=False):
        storage = record["storage"]
        kind = storage["kind"]
        storage_counts[kind] += 1
        if kind == "existing_verified_immutable_HF_file":
            demand(storage["references"], "empty prior content references")
            for reference in storage["references"]:
                item = prior[(reference["repo_id"], reference["revision"], reference["path_in_repository"])]
                demand(reference["repo_type"] == "model" and reference["sha256"] == item["sha256"]
                       == record["source_sha256"] and reference["bytes"] == item["bytes"]
                       == record["source_bytes"], "exact existing file coverage differs")
            return None
        demand(storage["path"] in files, "new storage payload absent from publication plan")
        used_new_files.add(storage["path"])
        item = files[storage["path"]]
        demand(item["sha256"] == storage["sha256"] and item["bytes"] == storage["bytes"],
               "new payload binding differs")
        if kind.endswith("gzip"):
            return stream_gzip(item, storage, collect)
        demand(kind == "new_byte_exact_safetensors" and storage["sha256"] == record["source_sha256"]
               and storage["bytes"] == record["source_bytes"], "binary tensor byte copy differs")
        return None

    for completed, (key, source_group) in enumerate(sorted(groups.items()), 1):
        record = records[key]
        demand(record["aliases"] == sorted(alias(item["path"]) for item in source_group),
               "source alias coverage differs")
        demand(record["families"] == sorted({item["family"] for item in source_group}), "family coverage differs")
        expected_descriptors = {}
        for item in source_group:
            for state in item.get("json_states", []):
                metadata = descriptor(state)
                pointer = state["json_pointer"]
                demand(pointer not in expected_descriptors or expected_descriptors[pointer] == metadata,
                       "same-byte source descriptors conflict")
                expected_descriptors[pointer] = metadata
        states = [expected_descriptors[pointer] for pointer in sorted(expected_descriptors)]
        demand(record["states"] == states, "saved state descriptor coverage differs")
        descriptor_count += len(states)
        embedded = any(item.get("embedded_in_report") is True for item in source_group)
        demand(record["embedded_in_report"] == embedded, "mixed report classification differs")
        for name, value in MASKS.items():
            demand(record[name] is value, "model authority mask differs")
        kind = record["storage"]["kind"]
        if embedded:
            demand(kind in ("new_weights_only_JSON_capsule_gzip", "existing_verified_immutable_HF_file"),
                   "new mixed report container transport rejected")
            if kind == "existing_verified_immutable_HF_file":
                existing_mixed_containers += 1
        data = storage_check(record, kind == "new_weights_only_JSON_capsule_gzip")
        if kind == "new_byte_exact_JSON_gzip":
            demand(not embedded and record["format"] == "JSON"
                   and record["storage"]["uncompressed_bytes"] == record["source_bytes"]
                   and record["storage"]["uncompressed_sha256"] == record["source_sha256"],
                   "clean JSON byte preservation differs")
        if data is not None:
            capsule = parse(data)
            demand(set(capsule) == {"schema", "source_sha256", "source_bytes", "states", "content_sha256", *MASKS}
                   and capsule["schema"] == "all-project-model-weights-state-capsule/v1"
                   and capsule["source_sha256"] == record["source_sha256"]
                   and capsule["source_bytes"] == record["source_bytes"], "closed weights-only capsule scope differs")
            body = {name: value for name, value in capsule.items() if name != "content_sha256"}
            demand(hashlib.sha256(canonical(body)).hexdigest() == capsule["content_sha256"], "state capsule seal differs")
            demand(len(capsule["states"]) == len(states), "extracted saved state count differs")
            for item, metadata in zip(capsule["states"], states, strict=True):
                demand(set(item) == {"metadata", "value"} and item["metadata"] == metadata,
                       "extracted state metadata scope differs")
                value = canonical(item["value"])
                count = numeric_count(item["value"])
                demand(len(value) == metadata["canonical_json_bytes"]
                       and hashlib.sha256(value).hexdigest() == metadata["canonical_json_sha256"]
                       and count == metadata["numeric_leaf_count"] and count > 0,
                       "extracted canonical saved state digest differs")
                extracted_state_count += 1
                extracted_numeric_count += count
        if completed % 100 == 0 or completed == len(groups):
            print(json.dumps({"independent_weight_contents_audited": completed, "total": len(groups)}), flush=True)

    sidecar_groups = collections.defaultdict(list)
    for item in sidecar_sources.values():
        sidecar_groups[(item["sha256"], item["bytes"])].append(item)
    sidecar_records = {(item["source_sha256"], item["source_bytes"]): item
                       for item in catalog["checkpoint_metadata_sidecars"]}
    demand(set(sidecar_records) == set(sidecar_groups), "complete binary sidecar coverage differs")
    dependencies = 0
    for key, source_group in sorted(sidecar_groups.items()):
        record = sidecar_records[key]
        demand(record["aliases"] == sorted(alias(item["path"]) for item in source_group),
               "checkpoint sidecar aliases differ")
        storage_check(record)
        if record["storage"]["kind"] != "existing_verified_immutable_HF_file":
            demand(record["storage"]["kind"] == "new_byte_exact_checkpoint_metadata_gzip"
                   and record["storage"]["uncompressed_bytes"] == key[1]
                   and record["storage"]["uncompressed_sha256"] == key[0], "sidecar byte preservation differs")
        observed_dependencies = {(item["sidecar_alias"], item["role"]): item for item in record["weight_dependencies"]}
        demand(len(observed_dependencies) == 2 * len(source_group), "both model and optimizer dependency required")
        for source in source_group:
            document = parse(Path(source["path"]).read_bytes())
            demand(document["schema"] == "source-vector-reconstruction-checkpoint/v1", "binary metadata schema differs")
            for role in ("model_file", "optimizer_file"):
                item = document[role]
                path = Path(item["path"])
                if not path.is_absolute():
                    path = Path(source["path"]).parent / path
                selected_dependency = {"path": str(path), "bytes": item["bytes"], "sha256": item["sha256"]}
                demand(all_sources.get(str(path)) == selected_dependency, "binary restore dependency absent")
                expected = {"sidecar_alias": alias(source["path"]), "role": role,
                            "weight_alias": alias(path), "bytes": item["bytes"], "sha256": item["sha256"]}
                demand(observed_dependencies.get((expected["sidecar_alias"], role)) == expected,
                       "binary metadata dependency alias differs")
                dependencies += 1
    demand(set(files) == used_new_files | {"LICENSE", "LICENSE_SCOPE.txt", "README.md", "catalog.json", "SHA256SUMS"},
           "unexpected public files or missing selected payloads")
    demand(catalog["declared_JSON_state_count"] == descriptor_count
           == staging["declared_JSON_state_count"], "declared unique-container state counts differ")
    check(staging["inventory_binding"])
    check(staging["stager_source_binding"])
    check(staging["publication_plan_binding"])
    report = {"schema": "all-project-model-weights-independent-staging-audit/v1", "status": "passed",
              "staging_binding": selected, "auditor_source_binding": binding(__file__),
              "inventory_binding": staging["inventory_binding"], "catalog_binding": staging["catalog_binding"],
              "publication_plan_binding": staging["publication_plan_binding"],
              "source_weight_aliases_accounted_for": len(all_sources), "unique_weight_contents_audited": len(groups),
              "declared_unique_container_JSON_state_descriptors": descriptor_count,
              "extracted_canonical_saved_states_independently_verified": extracted_state_count,
              "extracted_finite_numeric_leaves_verified": extracted_numeric_count,
              "checkpoint_sidecar_aliases": len(sidecar_sources), "unique_checkpoint_sidecars": len(sidecar_groups),
              "exact_model_and_optimizer_sidecar_dependency_joins": dependencies,
              "selected_public_files_verified": len(files), "selected_public_bytes_verified": staging["selected_bytes"],
              "storage_counts_including_metadata_sidecars": dict(storage_counts),
              "all_weight_source_entries_accounted_for": True, "weights_only_capsules_closed_scope_verified": True,
              "existing_mixed_containers_referenced_without_new_report_transport": existing_mixed_containers,
              "all_new_mixed_containers_use_weights_only_capsules": True,
              "clean_original_JSON_and_binary_tensor_bytes_preserved": True,
              "all_gzip_payloads_roundtrip_verified": True, "publication_plan_within_one_MiB": True,
              "source_alias_manifest_covers_every_weight_and_sidecar": True,
              "original_aliases_rehashed_by_this_audit": False,
              "original_alias_preservation_scope": "all aliases bound; root rehashes originals after publication",
              "network_calls": 0, "model_loads": 0, "training_calls": 0, "source_values_in_report": False,
              "wall_seconds": round(time.monotonic() - started, 3), **MASKS}
    report["content_sha256"] = hashlib.sha256(canonical(report)).hexdigest()
    output = arguments.output.absolute()
    demand(not output.exists(), "fresh audit output required")
    descriptor_fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor_fd, "wb") as stream:
        stream.write(canonical(report) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({"status": "passed", "audit_binding": binding(output), "wall_seconds": report["wall_seconds"]}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staging", type=Path, required=True)
    parser.add_argument("--staging-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        audit(arguments)
        return 0
    except ValueError as error:
        print(json.dumps({"status": "independent_audit_rejected", "error": str(error)}), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
