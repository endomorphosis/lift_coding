"""Receive inert full-successor page cohorts and exact snapshot metadata.

This separately bounded profile performs no source, numerical, model, Git,
owner, solver, database or service execution. Exported origins and semantics
remain declarations beyond the independently checked raw/typed protocol joins.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import os
import stat
import sys
from collections import Counter
from pathlib import Path, PurePosixPath

INPUT_SCHEMA = "codebase-ir-full-successor-cohort-audit-input@1"
REPORT_SCHEMA = "codebase-ir-full-successor-cohort-audit@1"
MiB = 1024 * 1024
MAX_ORIGINALS, MAX_FILES, MAX_BYTES = 128, 256, 16 * MiB
ANCHORS = {
    "full_scan_result": "2bd63662dc0b954ed98bf83012e805218c0ac6ca5981497a8cd754b18083f788",
    "independent_audit": "43b5b045371bc85851657eeab04382e0f844ae22bf7aa4b0556fd9e22a8a73a1",
    "prior_review": "8a9a24c56873f97edac6e325078039fc0e2ba017c922839d11eaf3d92e7f2f91",
}
SELECTORS = {
    "previous_manifest": "seed-evidence/previous-manifest.json",
    "current_manifest": "seed-evidence/current-manifest.json",
    "previous_publication": "seed-evidence/previous-publication-receipt.json",
    "current_publication": "seed-evidence/current-publication-receipt.json",
    "source_delta": "source-delta.json",
    "optimized_selection": "successor-selection.json",
    "reference_selection": "reference-successor-selection.json",
    "optimized_root": "scan-root.json",
    "reference_root": "reference-scan-root.json",
    "completion": "successor-scan-completion.json",
    "reference_page": "reference-prefix-page.json",
}
SELECTORS.update({f"default_page_{i:02d}": n for i, n in enumerate(
    ["successor-parent-page-01.json", "successor-parent-page-02.json"]
    + [f"successor-process-{process:02d}-page-{page:02d}.json" for process in range(1, 5) for page in range(1, 3)])})
for _kind, _name in (("run", "successor-fresh-process-run"), ("request", "successor-resume-request"), ("launch", "successor-fresh-process-launch")):
    SELECTORS.update({f"process_{_kind}_{i:02d}": f"{_name}-{i:02d}.json" for i in range(1, 5)})
SELECTORS.update({"checkpoint_before": "checkpoint-states-before.json", "checkpoint_after": "checkpoint-states-after.json",
                  "owners_before": "owners-before.json", "owners_after_parent": "owners-after-parent-pages.json",
                  "owners_after_cold": "owners-after-cold.json", "materialization": "materialized-successor-setup.json"})
ROLES = (*ANCHORS, *SELECTORS)
TRUE_FLAGS = (
    "full_successor_cohort_accounting_produced", "complete_default_page_population_rederived",
    "complete_member_dispositions_rederived", "snapshot_schema_verified", "snapshot_entry_schema_verified",
    "current_manifest_membership_reconciled", "previous_manifest_membership_reconciled",
    "source_delta_metadata_reconciled", "reference_first32_scope_preserved",
    "historical_no_fit_declarations_preserved", "declared_role_membership_reconciled",
    "fresh_process_declarations_reconciled", "input_files_unchanged", "unknown_pretraining_exposure",
)
FALSE_FLAGS = (
    "native_execution_performed", "training_executed", "current_authority_claimed", "owner_sources_imported",
    "owner_database_opened", "git_executable_invoked", "profile_keys_read", "raw_source_bytes_replayed",
    "captured_ast_bindings_rederived", "source_execution_attested", "scan_execution_attested",
    "source_semantics_verified", "source_runtime_truth_verified", "semantic_state_identity_rederived",
    "native_target_digest_rederived", "numerical_execution_reperformed", "complete_inference_reperformed",
    "numerical_provenance_verified", "inference_correctness_verified", "optimizer_state_replayed",
    "checkpoint_states_verified", "full_ancestry_verified", "root_training_population_verified",
    "replay_population_verified", "complete_pretraining_exposure_verified", "heldout_independence_verified",
    "learned_weight_dependence_verified", "learned_quality_improvement_verified", "model_selection_performed",
    "candidate_model_qualified", "promotion_performed", "model_advanced", "numerical_reuse_authorized",
    "full_reference_scan_verified", "all_members_numerically_inferred", "final_population_modified",
    "producer_authentication_verified", "process_origin_independently_attested", "kernel_resource_enforcement_verified",
    "whole_repository_coverage", "physical_absence_verified", "production_default_activated",
)
ZERO_FIELDS = ("runtime_fact_count", "tasks_omitted_count", "additional_attempted_training_epochs", "new_final_assignments")


MEMBER_FIELDS = {"ast_cid", "entry_cid", "opaque_reason", "parse_status", "path", "raw_path_hex",
                 "source_cid", "source_key", "source_size_bytes"}


HEAD_FIELDS = {"schema", "repository_id", "generation", "ast_revision_id", "snapshot_cid", "manifest_cid", "receipt_cid"}


AUTHORITY_FIELDS = {"admission_authority", "authoritative_cache_eligible", "behavioral_satisfaction", "completion_authority",
                    "decoded_formulas_generated", "execution_authority", "mutation_authority", "proof_authority",
                    "repository_code_executed", "runtime_behavior_verified", "scan_execution_attested",
                    "source_execution_attested", "source_semantics_verified", "training_executed"}


ROOT_FIELDS = {"authority", "head", "head_cid", "implementation", "limits", "members", "membership_cid", "model", "optimized", "schema"}


SELECTION_FIELDS = {"authority", "current_head", "current_membership_cid", "implementation", "inference_performed_here", "model",
                    "model_head_promoted", "numerical_reuse", "optimized", "previous_head", "previous_membership_cid", "previous_model",
                    "previous_training_record_cid", "root_cid", "scan_limits", "schema", "source_delta_cid", "training_performed_here", "training_record_cid"}


PAGE_FIELDS = {"authority", "coverage", "end", "entries", "head_cid", "inference", "membership_cid", "model_artifact_cid",
               "page_membership_cid", "previous_page_cid", "root_cid", "schema", "start", "total_entries", "worker_receipt"}


ENTRY_FIELDS = {"coverage", "disposition", "entry_cid", "inference_index", "member_index", "reason", "source_digest", "source_key", "target_sha256"}


MODEL_FIELDS = {"ancestry", "artifact", "artifact_cid", "contract_sha256", "feature_columns", "feature_space_sha256", "latent_width",
                "projection_ids", "projection_widths", "state_sha256", "variant_id", "version_id"}


class Refused(ValueError):
    """Selected source/export bytes do not satisfy this closed diagnostic profile."""


def require(condition, reason):
    if not condition:
        raise Refused(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def cid(raw, structured=False):
    return "b" + base64.b32encode((b"\x01\xa9\x02\x12\x20" if structured else b"\x01\x55\x12\x20")
                                 + hashlib.sha256(raw).digest()).decode("ascii").lower().rstrip("=")


def object_cid(value):
    return cid(wire(value), True)


def report_bytes(value):
    chunks, size = [], 0
    for chunk in json.JSONEncoder(sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False).iterencode(value):
        raw = chunk.encode("utf-8")
        size += len(raw)
        require(size + 1 <= 4 * MiB, "main report allocation bound")
        chunks.append(raw)
    return b"".join(chunks) + b"\n"


def closed(value, fields, reason):
    require(type(value) is dict and set(value) == set(fields), reason)


def document(raw):
    def pairs(items):
        value = {}
        for key, item in items:
            require(key not in value, "duplicate JSON field")
            value[key] = item
        return value

    def integer(token):
        require(len(token) <= 20, "JSON integer allocation bound")
        value = int(token)
        require(abs(value) <= 2**63 - 1, "JSON integer bound")
        return value

    def floating(token):
        require(len(token) <= 64 and math.isfinite(float(token)), "finite JSON number required")
        return float(token)

    def bad(_):
        raise Refused("nonfinite JSON constant")

    value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_int=integer,
                       parse_float=floating, parse_constant=bad)
    pending, nodes = [(value, 0)], 0
    while pending:
        item, depth = pending.pop()
        nodes += 1
        require(depth <= 64 and nodes <= 1000000, "JSON structure budget")
        if type(item) is dict:
            pending.extend((x, depth + 1) for x in item)
            pending.extend((x, depth + 1) for x in item.values())
        elif type(item) is list:
            pending.extend((x, depth + 1) for x in item)
        elif type(item) is str:
            item.encode("utf-8")
    require(type(value) is dict, "JSON object required")
    return value


def descriptor(value):
    closed(value, {"path", "sha256", "size_bytes"}, "closed raw descriptor required")
    require(type(value["path"]) is str and type(value["sha256"]) is str
            and len(value["sha256"]) == 64 and all(x in "0123456789abcdef" for x in value["sha256"])
            and type(value["size_bytes"]) is int and 0 <= value["size_bytes"], "typed exact raw descriptor required")
    return Path(value["path"])


class Reads:
    def __init__(self):
        self.plan, self.raw, self.inodes = {}, {}, {}

    def reserve(self, path, pin, cap):
        path = Path(path)
        require(path.is_absolute() and path.resolve(strict=True) == path, "canonical selected file required")
        require(type(pin) is dict and set(pin) == {"sha256", "size_bytes"}
                and type(pin["size_bytes"]) is int and 0 <= pin["size_bytes"] <= cap, "declared preallocation body bound")
        require(type(pin["sha256"]) is str and len(pin["sha256"]) == 64
                and all(x in "0123456789abcdef" for x in pin["sha256"]), "raw SHA required")
        if path in self.plan:
            require(self.plan[path] == pin, "conflicting selected descriptor")
            return
        require(len(self.plan) < MAX_ORIGINALS and 2 * (sum(x["size_bytes"] for x in self.plan.values())
                + pin["size_bytes"]) <= MAX_BYTES, "complete original and copy reservation budget")
        info = path.stat(follow_symlinks=False)
        require(stat.S_ISREG(info.st_mode) and info.st_size == pin["size_bytes"], "regular exact selected size")
        inode = (info.st_dev, info.st_ino)
        require(inode not in self.inodes, "hardlink selected alias")
        self.inodes[inode], self.plan[path] = path, pin

    @staticmethod
    def bounded(path, cap):
        require(path.is_absolute() and path.resolve(strict=True) == path, "canonical bounded read required")
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            before = os.fstat(fd)
            require(stat.S_ISREG(before.st_mode) and before.st_size <= cap, "bounded regular descriptor required")
            with os.fdopen(fd, "rb", closefd=False) as stream:
                raw = stream.read(cap + 1)
            after, final = os.fstat(fd), path.stat(follow_symlinks=False)
            def identity(value):
                return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns
            require(len(raw) == before.st_size and identity(before) == identity(after) == identity(final), "selected descriptor drift")
            return raw
        finally:
            os.close(fd)

    def take(self, path):
        require(path in self.plan, "unreserved read refused")
        if path not in self.raw:
            pin = self.plan[path]
            raw = self.bounded(path, pin["size_bytes"])
            require(sha(raw) == pin["sha256"], "selected raw SHA mismatch")
            self.raw[path] = raw
        return self.raw[path]

    def stable(self):
        for path, raw in self.raw.items():
            require(self.bounded(path, len(raw)) == raw, "late original selected body drift")


def typed_equal(a, b):
    return wire(a) == wire(b)


def integer(value, lower, upper, reason):
    require(type(value) is int and lower <= value <= upper, reason)
    return value


def digest(value):
    require(type(value) is str and len(value) == 64 and all(x in "0123456789abcdef" for x in value), "closed SHA digest")
    return value


def source_head(value):
    closed(value, HEAD_FIELDS, "closed declared source head")
    require(value["schema"] == "codebase-head@1", "unsupported source head schema")
    integer(value["generation"], 1, 2**31 - 1, "typed head generation")
    require(type(value["repository_id"]) is str and value["ast_revision_id"] == "rev:" + value["repository_id"]
            + ":snapshot:" + value["snapshot_cid"], "declared head revision identity")


def authority(value):
    closed(value, AUTHORITY_FIELDS, "closed advisory authority vocabulary")
    require(all(x is False for x in value.values()), "advisory authority ceiling")


def envelope(value, fields, schema, raw_codec=False):
    closed(value, {"artifact_cid", "value"}, "closed captured envelope")
    body = value["value"]
    closed(body, fields, "closed captured protocol")
    require(body["schema"] == schema and value["artifact_cid"] == cid(wire(body), not raw_codec), "captured protocol schema/CID")
    authority(body["authority"])
    return body


def model(value):
    closed(value, MODEL_FIELDS, "closed declared model descriptor")
    integer(value["feature_columns"], 1, 4096, "typed feature width")
    integer(value["latent_width"], 1, 384, "typed latent width")
    require(value["latent_width"] == 8 and value["feature_columns"] == 53, "closed CPU8D declaration")
    closed(value["artifact"], {"bytes", "sha256"}, "closed uninspected model-body claim")
    integer(value["artifact"]["bytes"], 1, 64 * MiB, "declared model body size")
    digest(value["artifact"]["sha256"])
    for field in ("contract_sha256", "feature_space_sha256", "state_sha256"):
        digest(value[field])
    require(value["version_id"] == "sha256:" + digest(value["version_id"].removeprefix("sha256:"))
            and value["variant_id"] == "modality-" + value["contract_sha256"], "declared model/variant identities")
    require(value["projection_ids"] == ["codebase_ir.contracts@1", "codebase_ir.program@1"]
            and typed_equal(value["projection_widths"], {"codebase_ir.contracts@1": 2, "codebase_ir.program@1": 51}), "declared projection widths")
    require(type(value["ancestry"]) is list and 1 <= len(value["ancestry"]) <= 2, "bounded declared ancestry")
    for item in value["ancestry"]:
        closed(item, {"artifact", "version_id"}, "closed ancestry declaration")
        closed(item["artifact"], {"bytes", "sha256"}, "closed ancestor body claim")
        integer(item["artifact"]["bytes"], 1, 64 * MiB, "declared ancestor size")
        digest(item["artifact"]["sha256"])
    require(typed_equal(value["ancestry"][0], {"version_id": value["version_id"], "artifact": value["artifact"]}), "declared self ancestry")


def member_list(members):
    require(type(members) is list and 32 <= len(members) <= 512, "bounded complete root population")
    paths, keys = [], []
    for m in members:
        closed(m, MEMBER_FIELDS, "closed root member")
        raw_path = bytes.fromhex(m["raw_path_hex"])
        require(0 < len(raw_path) <= 1024 and b"\0" not in raw_path and raw_path.decode("utf-8") == m["path"]
                and m["source_key"] == "raw:" + m["raw_path_hex"]
                and not PurePosixPath(m["path"]).is_absolute() and ".." not in PurePosixPath(m["path"]).parts, "raw source path/key binding")
        integer(m["source_size_bytes"], 0, 2**63 - 1, "typed declared source length")
        require(m["parse_status"] in {"ok", "unindexed", "failed", "opaque"}, "closed parse disposition")
        paths.append(raw_path)
        keys.append(m["source_key"])
    require(paths == sorted(paths) and len(set(paths)) == len(paths) and len(set(keys)) == len(keys), "ordered unique root membership")


def selection_pair(metadata):
    result = []
    for route in ("optimized", "reference"):
        s = envelope(metadata[route + "_selection"], SELECTION_FIELDS, "codebase-inventory-successor-scan@1")
        r = envelope(metadata[route + "_root"], ROOT_FIELDS, "codebase-inventory-resume-root@1")
        source_head(s["previous_head"])
        source_head(s["current_head"])
        require(s["current_head"]["repository_id"] == s["previous_head"]["repository_id"]
                and s["current_head"]["generation"] == s["previous_head"]["generation"] + 1, "successive declared source heads")
        for field in ("inference_performed_here", "training_performed_here", "model_head_promoted", "numerical_reuse"):
            require(s[field] is False, "selection no-fit/no-inference scope")
        require(s["optimized"] is (route == "optimized") and r["optimized"] is s["optimized"], "exact route declaration")
        model(s["model"])
        model(s["previous_model"])
        parent, child = s["previous_model"], s["model"]
        require(len(parent["ancestry"]) == 1 and typed_equal(child["ancestry"], [child["ancestry"][0], parent["ancestry"][0]])
                and child["version_id"] != parent["version_id"], "declared direct-child ancestry")
        for field in ("contract_sha256", "feature_columns", "feature_space_sha256", "latent_width", "projection_ids", "projection_widths", "variant_id"):
            require(typed_equal(child[field], parent[field]), "declared fixed basis/contract continuity")
        member_list(r["members"])
        require(typed_equal(r["head"], s["current_head"]) and r["head_cid"] == object_cid(r["head"])
                and r["membership_cid"] == object_cid(r["members"]) == s["current_membership_cid"]
                and typed_equal(r["model"], child) and typed_equal(r["limits"], s["scan_limits"])
                and s["root_cid"] == metadata[route + "_root"]["artifact_cid"], "root/selection exact joins")
        integer(r["limits"]["page_entries"], 32, 32, "closed prefix page size")
        result.append((s, r))
    left, right = result
    require(left[0]["root_cid"] != right[0]["root_cid"], "fresh separate route roots")
    for field in SELECTION_FIELDS - {"optimized", "root_cid"}:
        require(typed_equal(left[0][field], right[0][field]), "exact shared successor declaration")
    require(typed_equal(left[1]["members"], right[1]["members"]), "same complete route population")
    return result


def child_request(owners, selection):
    closed(owners, {"model_artifacts", "registry", "source"}, "closed captured owner metadata")
    closed(owners["registry"], {"events", "heads", "meta", "operations", "outbox", "runs", "variants", "versions"}, "closed inert registry export")
    require(owners["registry"]["heads"] == [], "captured unpromoted registry declaration")
    require(typed_equal(owners["source"]["current_head"], selection["current_head"]), "captured owner/source head declaration")
    versions, runs = owners["registry"]["versions"], owners["registry"]["runs"]
    require(type(versions) is list and len(versions) == 2 and all(type(v) is list and len(v) == 5 for v in versions), "closed two-version registry rows")
    by_id = {v[0]: v for v in versions}
    child, parent = selection["model"], selection["previous_model"]
    require(set(by_id) == {parent["version_id"], child["version_id"]}, "exact registry version population")
    for declared, predecessor in ((parent, None), (child, parent["version_id"])):
        row = by_id[declared["version_id"]]
        require(row[1] == declared["variant_id"] and row[2] == predecessor
                and typed_equal(document(row[3].encode()), declared["artifact"]), "declared registry parent/artifact joins")
    require(type(runs) is list and len(runs) == 1 and type(runs[0]) is list and len(runs[0]) == 9, "only one child run declaration available")
    row = runs[0]
    require(row[1] == child["variant_id"] and row[2] == parent["version_id"] and row[4] == "completed", "completed child request declaration")
    integer(row[5], 1, 1, "typed declared run attempt")
    integer(row[6], 1, 1, "typed declared run fence")
    request, result = document(row[3].encode()), document(row[8].encode())
    closed(request, {"canary_targets_sha256", "configuration", "contract_sha256", "head", "implementation", "parent_version_id",
                     "schema", "selections", "training_targets_sha256", "tuning_targets_sha256"}, "closed child training request")
    require(request["schema"] == "codebase-source-feature-training@1" and typed_equal(request["head"], selection["current_head"])
            and request["parent_version_id"] == parent["version_id"] and request["contract_sha256"] == child["contract_sha256"], "child request head/parent/contract declarations")
    closed(request["configuration"], {"epochs", "learning_rate", "seed"}, "closed declared setup configuration")
    integer(request["configuration"]["epochs"], 1, 1, "typed declared child setup epoch")
    integer(request["configuration"]["seed"], 0, 2**31 - 1, "typed declared seed")
    rate = request["configuration"]["learning_rate"]
    require(type(rate) in {float, int} and 0 < rate < 1, "typed declared learning rate")
    selections = request["selections"]
    require(type(selections) is list and len(selections) == 3, "exact child declared role population")
    for s in selections:
        closed(s, {"contracts", "path", "role"}, "closed child source selection")
        require(type(s["path"]) is str and s["role"] in {"train", "tune", "canary"} and s["contracts"] == [], "closed child selection roles/contracts")
    require(len({s["path"] for s in selections}) == 3 and Counter(s["role"] for s in selections) == Counter({"train": 1, "tune": 1, "canary": 1}), "unique declared child role paths")
    for field in ("training_targets_sha256", "tuning_targets_sha256", "canary_targets_sha256"):
        digest(request[field])
    for field in ("admitted", "formalized", "promotion_performed", "qualified"):
        require(result[field] is False, "captured training result authority ceiling")
    require(result["training_purpose"] == "feature_pretraining", "declared training purpose")
    for field in ("contract_sha256", "feature_space_sha256", "state_sha256"):
        require(result[field] == child[field], "child result fingerprint declarations")
    return request


def checkpoint(stage, output):
    """Explicit receiving boundary for authored late-drift controls."""


def raw_cid_digest(value, structured=False):
    require(type(value) is str and value.startswith("b") and len(value) <= 64, "canonical declared CID")
    try:
        encoded = value[1:].upper()
        decoded = base64.b32decode(encoded + "=" * (-len(encoded) % 8))
    except (ValueError, TypeError) as exc:
        raise Refused("invalid declared CID encoding") from exc
    prefix = b"\x01\xa9\x02\x12\x20" if structured else b"\x01\x55\x12\x20"
    require(len(decoded) == len(prefix) + 32 and decoded.startswith(prefix)
            and "b" + base64.b32encode(decoded).decode("ascii").lower().rstrip("=") == value,
            "closed declared CID codec/hash")
    return decoded[len(prefix):].hex()


def hex_path(value, path):
    require(type(value) is str and len(value) <= 2048 and len(value) % 2 == 0
            and all(x in "0123456789abcdef" for x in value), "canonical raw path hex")
    raw = bytes.fromhex(value)
    require(type(path) is str and 0 < len(raw) <= 1024 and b"\0" not in raw
            and raw.decode("utf-8") == path and str(PurePosixPath(path)) == path
            and not PurePosixPath(path).is_absolute() and not any(x in {".", "..", ".git"} for x in path.split("/"))
            and "\\" not in path, "closed relative path declaration")
    return raw


def snapshot(envelope_value, expected_head):
    closed(envelope_value, {"artifact_cid", "value"}, "closed structural manifest envelope")
    manifest = envelope_value["value"]
    closed(manifest, {"schema", "ast_revision_id", "authority", "coverage", "semantic_state", "snapshot", "units"}, "closed structural manifest")
    require(manifest["schema"] == "codebase-ir-structural-manifest@1" and manifest["authority"] == "structural_only"
            and manifest["ast_revision_id"] == expected_head["ast_revision_id"]
            and envelope_value["artifact_cid"] == object_cid(manifest) == expected_head["manifest_cid"], "manifest CID/head preimage")
    captured = manifest["snapshot"]
    closed(captured, {"entries", "exclusions", "git_commit", "git_tree", "max_entries", "max_file_bytes", "mode", "repository_id", "schema", "snapshot_cid"}, "closed captured snapshot")
    require(captured["schema"] == "ipfs-datasets.software-contracts.semantic-repository-snapshot@4"
            and captured["repository_id"] == expected_head["repository_id"]
            and captured["snapshot_cid"] == expected_head["snapshot_cid"]
            == object_cid({k: v for k, v in captured.items() if k != "snapshot_cid"}), "snapshot schema/CID/head preimage")
    integer(captured["max_entries"], 1, 512, "typed snapshot entry limit")
    integer(captured["max_file_bytes"], 1, 65536, "typed snapshot file limit")
    require(captured["mode"] == "git-clean" and type(captured["exclusions"]) is list
            and len(captured["exclusions"]) <= 64 and all(type(x) is str and 0 < len(x) <= 64 for x in captured["exclusions"])
            and captured["exclusions"] == sorted(set(captured["exclusions"])), "declared capture acquisition/exclusions")
    for field in ("git_commit", "git_tree"):
        require(type(captured[field]) is str and len(captured[field]) == 40
                and all(x in "0123456789abcdef" for x in captured[field]), "inert Git identity declaration")
    entries, units = captured["entries"], manifest["units"]
    require(type(entries) is list and type(units) is list and len(entries) == len(units) == 300
            and len(entries) <= captured["max_entries"], "complete declared 300-member snapshot population")
    unit_map = {}
    for unit in units:
        closed(unit, {"schema", "source_key", "entry_cid", "ast_cid", "parse_status"}, "closed structural unit")
        require(unit["schema"] == "codebase-ir-structural-unit@1" and type(unit["source_key"]) is str
                and unit["source_key"] not in unit_map and unit["parse_status"] in {"ok", "failed", "opaque", "unindexed"}, "unique structural unit declaration")
        raw_cid_digest(unit["entry_cid"], True)
        if unit["ast_cid"] is not None:
            raw_cid_digest(unit["ast_cid"], True)
        require((unit["ast_cid"] is not None) is (unit["parse_status"] in {"ok", "failed"}), "declared AST presence/parse disposition")
        unit_map[unit["source_key"]] = unit
    rows, order = {}, []
    for entry in entries:
        closed(entry, {"acquisition", "disposition", "entry_cid", "git_blob_oid", "head_blob_oid", "index_blob_oids", "kind", "opaque_reason", "path", "raw_path_hex", "schema", "size_bytes", "source_cid"}, "closed semantic snapshot entry")
        require(entry["schema"] == "ipfs-datasets.software-contracts.semantic-snapshot-entry@3"
                and entry["entry_cid"] == object_cid({k: v for k, v in entry.items() if k != "entry_cid"}), "entry schema/CID preimage")
        order.append(hex_path(entry["raw_path_hex"], entry["path"]))
        integer(entry["size_bytes"], 0, 2**63 - 1, "typed declared entry length")
        require(entry["acquisition"] == ("opaque" if entry["kind"] == "opaque" else "git-object") and entry["disposition"] == "clean"
                and entry["index_blob_oids"] == {}, "inert clean capture declarations")
        for field in ("git_blob_oid", "head_blob_oid"):
            require(type(entry[field]) is str and len(entry[field]) == 40
                    and all(x in "0123456789abcdef" for x in entry[field]), "inert blob identity declaration")
        require(entry["git_blob_oid"] == entry["head_blob_oid"], "declared clean blob equality")
        require(entry["kind"] in {"artifact", "python", "opaque"}, "closed captured entry kind")
        if entry["kind"] == "opaque":
            require(entry["opaque_reason"] in {"undecodable", "oversized"}, "closed opaque frontier")
            require((entry["source_cid"] is None) is (entry["opaque_reason"] == "oversized"), "opaque source CID frontier")
        else:
            require(entry["opaque_reason"] is None and entry["size_bytes"] <= captured["max_file_bytes"]
                    and entry["source_cid"] is not None, "bounded captured source declaration")
        if entry["source_cid"] is not None:
            raw_cid_digest(entry["source_cid"])
        key = "raw:" + entry["raw_path_hex"]
        require(key not in rows and key in unit_map and unit_map[key]["entry_cid"] == entry["entry_cid"], "complete entry/unit identity join")
        unit = unit_map[key]
        require((unit["parse_status"] == "opaque") is (entry["kind"] == "opaque"), "opaque parse/entry declaration")
        member = dict(ast_cid=unit["ast_cid"], entry_cid=entry["entry_cid"], opaque_reason=entry["opaque_reason"],
                      parse_status=unit["parse_status"], path=entry["path"], raw_path_hex=entry["raw_path_hex"],
                      source_cid=entry["source_cid"], source_key=key, source_size_bytes=entry["size_bytes"])
        rows[key] = dict(entry=entry, member=member)
    require(order == sorted(order) and len(set(order)) == 300 and set(rows) == set(unit_map), "ordered exact captured population")
    semantic = manifest["semantic_state"]
    closed(semantic, {"artifacts", "edges", "extractor_name", "extractor_version", "repository_id", "schema", "state_cid", "symbols"}, "closed inert semantic metadata container")
    require(semantic["schema"] == "ipfs-datasets.software-contracts.semantic-index@2"
            and semantic["repository_id"] == expected_head["repository_id"], "semantic metadata container declarations")
    raw_cid_digest(semantic["state_cid"], True)
    for field, limit in (("symbols", 2048), ("edges", 4096), ("artifacts", 1024)):
        require(type(semantic[field]) is list and len(semantic[field]) <= limit, "bounded inert semantic metadata population")
    # The semantic state has its own native identity recipe. Its identity and
    # source correspondence remain declarations; the manifest raw/CID seal
    # covers these exact bodies without deriving the semantic-state identity.
    counts = Counter(unit["parse_status"] for unit in units)
    coverage = dict(ast_failed=counts["failed"], ast_ok=counts["ok"], ast_partial=0,
                    captured_entries=300 - counts["opaque"], checked_properties=0, formalized_properties=0,
                    inventory_entries=300, opaque_entries=counts["opaque"], semantic_symbols=len(semantic["symbols"]),
                    unindexed_entries=counts["unindexed"])
    require(typed_equal(manifest["coverage"], coverage), "typed independently counted snapshot coverage")
    return rows, dict(schema=captured["schema"], entry_schema="ipfs-datasets.software-contracts.semantic-snapshot-entry@3",
                      coverage=coverage, semantic_edges=len(semantic["edges"]), semantic_artifacts=len(semantic["artifacts"]),
                      manifest_cid=envelope_value["artifact_cid"], snapshot_cid=captured["snapshot_cid"],
                      git_identity_scope="declared_only_no_git_body_or_executable_replay", semantic_state_identity_scope="unverified_native_identity_recipe")


def source_delta(metadata, previous, current, selection):
    fields = {"schema", "authority", "capture_policy", "coverage", "current_head", "current_membership_cid", "current_publication_receipt", "implementation", "ledger", "limits", "model_advanced", "numerical_reuse", "optimized", "physical_absence_verified", "previous_head", "previous_membership_cid", "previous_publication_receipt", "removal_scope"}
    value = envelope(metadata["source_delta"], fields, "codebase-inventory-source-delta@1")
    require(value["model_advanced"] is value["numerical_reuse"] is value["physical_absence_verified"] is False
            and value["optimized"] is True and value["removal_scope"] == "absent_from_current_complete_capture", "delta declaration authority/scope")
    for which, rows in (("previous", previous), ("current", current)):
        head = selection[which + "_head"]
        require(typed_equal(value[which + "_head"], head), "delta source head join")
        receipt = metadata[which + "_publication"]
        closed(receipt, {"ast_revision_id", "generation", "manifest_cid", "operation_id", "previous_head", "repository_id", "request_cid", "schema", "snapshot_cid"}, "closed publication receipt")
        require(receipt["schema"] == "codebase-publication-receipt@1" and object_cid(receipt) == head["receipt_cid"]
                and typed_equal(value[which + "_publication_receipt"], receipt)
                and all(typed_equal(receipt[k], head[k]) for k in ("repository_id", "generation", "ast_revision_id", "snapshot_cid", "manifest_cid")), "publication exact typed head/CID join")
        members = [row["member"] for row in rows.values()]
        require(value[which + "_membership_cid"] == selection[which + "_membership_cid"] == object_cid(members), "complete source/member CID join")
    require(metadata["previous_publication"]["previous_head"] is None
            and typed_equal(metadata["current_publication"]["previous_head"], selection["previous_head"]), "declared predecessor publication")
    closed(value["capture_policy"], {"exclusions", "max_entries", "max_file_bytes"}, "closed capture policy")
    for which in ("previous", "current"):
        capture = metadata[which + "_manifest"]["value"]["snapshot"]
        require(typed_equal(value["capture_policy"], {k: capture[k] for k in value["capture_policy"]}), "delta/capture policy join")
    ledger, counters = [], {k: Counter() for k in ("classifications", "source_bytes_comparisons", "ast_identity_comparisons")}
    for key in sorted(set(previous) | set(current)):
        a, b = previous.get(key), current.get(key)
        kind = "added" if a is None else "removed" if b is None else "retained" if typed_equal(a["entry"], b["entry"]) else "changed"
        byte_comparison = ast_comparison = "unavailable"
        if a is not None and b is not None:
            old, new = a["member"], b["member"]
            if old["parse_status"] != "opaque" and new["parse_status"] != "opaque" and old["source_cid"] is not None and new["source_cid"] is not None:
                byte_comparison = "equal" if old["source_cid"] == new["source_cid"] else "different"
            if old["ast_cid"] is not None and new["ast_cid"] is not None:
                ast_comparison = "equal" if old["ast_cid"] == new["ast_cid"] else "different"
        ledger.append(dict(source_key=key, classification=kind, previous=a, current=b,
                           source_bytes_comparison=byte_comparison, ast_identity_comparison=ast_comparison))
        counters["classifications"][kind] += 1
        counters["source_bytes_comparisons"][byte_comparison] += 1
        counters["ast_identity_comparisons"][ast_comparison] += 1
    require(len(ledger) <= 1024 and typed_equal(value["ledger"], ledger), "complete typed source delta ledger from snapshots")
    coverage = dict(previous_entries=len(previous), current_entries=len(current), union_entries=len(ledger),
                    classifications={k: counters["classifications"][k] for k in ("retained", "changed", "added", "removed")},
                    source_bytes_comparisons={k: counters["source_bytes_comparisons"][k] for k in ("equal", "different", "unavailable")},
                    ast_identity_comparisons={k: counters["ast_identity_comparisons"][k] for k in ("equal", "different", "unavailable")})
    require(typed_equal(value["coverage"], coverage) and metadata["source_delta"]["artifact_cid"] == selection["source_delta_cid"], "rederived delta coverage/selection join")
    return dict(coverage=coverage, comparisons_scope="declared_CID_identity_with_opaque_frontier_not_raw_source_replay",
                changes=[dict(source_key=row["source_key"], classification=row["classification"]) for row in ledger if row["classification"] != "retained"])


def page(envelope_value, root, selection, start, previous_cid):
    value = envelope(envelope_value, PAGE_FIELDS, "codebase-inventory-resume-page@1", True)
    end = min(start + 32, len(root["members"]))
    integer(value["start"], start, start, "typed exact page start")
    integer(value["end"], end, end, "typed exact page end")
    integer(value["total_entries"], len(root["members"]), len(root["members"]), "typed full member population")
    members = root["members"][start:end]
    require(value["root_cid"] == selection["root_cid"] and value["head_cid"] == root["head_cid"]
            and value["membership_cid"] == root["membership_cid"] and value["page_membership_cid"] == object_cid(members)
            and value["previous_page_cid"] == previous_cid and value["model_artifact_cid"] == selection["model"]["artifact_cid"], "complete page/root/previous/head/member joins")
    require(type(value["entries"]) is list and len(value["entries"]) == len(members), "complete exact page entry population")
    inf = value["inference"]
    inf_fields = {"admitted", "contract_sha256", "coverage", "decoded_formulas_generated", "feature_space_sha256", "formalized", "promotion_performed", "qualified", "representation", "rows", "schema", "state_sha256", "training_executed"}
    if inf is not None:
        closed(inf, inf_fields, "closed exported numerical row declaration")
        require(inf["schema"] == "native-projection-feature-inference/v1"
                and inf["representation"] == "native_compiler_structural_features_not_semantic_text_embeddings", "closed exported numerical representation")
        require(all(inf[k] is False for k in ("admitted", "decoded_formulas_generated", "formalized", "promotion_performed", "qualified", "training_executed")), "exported inference authority ceiling")
        require(all(inf[k] == selection["model"][k] for k in ("contract_sha256", "feature_space_sha256", "state_sha256")), "exported fixed model fingerprints")
        require(type(inf["rows"]) is list and len(inf["rows"]) <= 32 and type(inf["coverage"]) is list, "bounded returned row/coverage population")
    rows, covered, counts, members_with_dispositions = [], [], Counter(), []
    for index, (entry, member) in enumerate(zip(value["entries"], members, strict=True), start):
        closed(entry, ENTRY_FIELDS, "closed complete scan entry")
        integer(entry["member_index"], index, index, "typed contiguous member index")
        require(entry["source_key"] == member["source_key"] and entry["entry_cid"] == member["entry_cid"], "complete entry/member identity")
        disposition = entry["disposition"]
        require(disposition in {"inferred", "deferred_budget", "unsupported_target", "opaque", "parse_failed", "unindexed"}, "closed complete scan disposition")
        counts[disposition] += 1
        members_with_dispositions.append(dict(member_index=index, path=member["path"], source_key=member["source_key"], disposition=disposition))
        if disposition in {"opaque", "parse_failed", "unindexed"}:
            expected_parse = {"opaque": "opaque", "parse_failed": "failed", "unindexed": "unindexed"}[disposition]
            reason = {"opaque": member["opaque_reason"], "parse_failed": "captured_parse_failed", "unindexed": "captured_source_has_no_ast_projection"}[disposition]
            require(member["parse_status"] == expected_parse and (member["ast_cid"] is None or disposition == "parse_failed")
                    and entry["source_digest"] is entry["target_sha256"] is entry["inference_index"] is None
                    and entry["coverage"] == [] and entry["reason"] == reason, "complete explicit unavailable-source frontier")
            continue
        require(member["parse_status"] == "ok" and member["ast_cid"] is not None, "declared supported AST presence")
        digest(entry["source_digest"])
        digest(entry["target_sha256"])
        if disposition == "unsupported_target":
            require(entry["coverage"] == [] and entry["inference_index"] is None and entry["reason"] == "native_target_not_complete", "unsupported target remains explicit")
            continue
        require(type(entry["coverage"]) is list and len(entry["coverage"]) == 2, "closed two-projection advisory coverage")
        for item, projection in zip(entry["coverage"], selection["model"]["projection_ids"], strict=True):
            closed(item, {"known_atoms", "projection_id", "unknown_atoms"}, "closed atom coverage")
            require(item["projection_id"] == projection, "ordered advisory projections")
            integer(item["known_atoms"], 0, 4096, "typed known atoms")
            integer(item["unknown_atoms"], 0, 4096, "typed unknown atoms")
        if disposition == "deferred_budget":
            require(entry["inference_index"] is None and type(entry["reason"]) is str and 0 < len(entry["reason"]) <= 4096, "deferred target absence")
            continue
        require(inf is not None, "inferred row requires an exported body")
        integer(entry["inference_index"], len(rows), len(rows), "typed contiguous numerical row index")
        require(entry["reason"] is None and len(rows) < len(inf["rows"]), "inferred row/reason declaration")
        row = inf["rows"][len(rows)]
        closed(row, {"latent", "reconstructed_projection_features", "source_digest"}, "closed numerical row")
        require(row["source_digest"] == entry["source_digest"] and type(row["latent"]) is list and len(row["latent"]) == 8, "source digest/latent width join")
        closed(row["reconstructed_projection_features"], selection["model"]["projection_ids"], "closed numerical projection widths")
        arrays = [row["latent"]]
        for projection, width in selection["model"]["projection_widths"].items():
            array = row["reconstructed_projection_features"][projection]
            require(type(array) is list and len(array) == width, "closed returned projection width")
            arrays.append(array)
        require(all(type(x) in {int, float} and abs(x) <= 1e100 and math.isfinite(x) for array in arrays for x in array), "typed finite numerical declarations")
        rows.append(row)
        covered.extend(entry["coverage"])
    if inf is None:
        require(not rows, "no numerical body with inferred rows")
    else:
        require(len(rows) == len(inf["rows"]) and typed_equal(covered, inf["coverage"]), "complete exported row/atom population")
    coverage = dict(dispositions=dict(sorted(counts.items())), inferred_rows=len(rows), inventory_entries=len(members))
    require(typed_equal(value["coverage"], coverage), "typed independent complete page disposition counts")
    receipt = value["worker_receipt"]
    if receipt is not None:
        closed(receipt, {"elapsed_ms", "executable_sha256", "input_bytes", "input_sha256", "limits", "memory_enforcement", "output_bytes", "output_sha256", "returncode", "source_execution_attested", "worker_sha256", "workspace_cleaned"}, "closed historical worker receipt")
        require(receipt["source_execution_attested"] is False and receipt["workspace_cleaned"] is True
                and receipt["memory_enforcement"] == "sampled_process_tree_rss_with_possible_overshoot", "historical worker resource/authority scope")
        integer(receipt["returncode"], 0, 0, "typed recorded worker exit")
        closed(receipt["limits"], {"max_input_bytes", "max_output_bytes", "resident_memory_bytes"}, "closed declared worker limits")
        for field in receipt["limits"]:
            integer(receipt["limits"][field], 1, 2**40, "typed declared worker cap")
        integer(receipt["input_bytes"], 0, receipt["limits"]["max_input_bytes"], "recorded input bound")
        integer(receipt["output_bytes"], 0, receipt["limits"]["max_output_bytes"], "recorded output bound")
        integer(receipt["elapsed_ms"], 0, 900000, "recorded worker elapsed bound")
        for field in ("executable_sha256", "input_sha256", "output_sha256", "worker_sha256"):
            digest(receipt[field])
    require((receipt is not None) is bool(rows), "recorded worker presence/returned row correspondence")
    return value, dict(page_cid=envelope_value["artifact_cid"], start=start, end=end,
                       membership_cid=value["page_membership_cid"], dispositions=coverage["dispositions"],
                       inferred_rows=coverage["inferred_rows"]), members_with_dispositions


def cursor(value, root_cid, offset, previous_page):
    closed(value, {"schema", "root_cid", "next_offset", "previous_page_cid"}, "closed process cursor declaration")
    integer(value["next_offset"], offset, offset, "typed exact process cursor offset")
    require(value["schema"] == "codebase-inventory-resume-cursor@1" and value["root_cid"] == root_cid
            and value["previous_page_cid"] == previous_page, "process cursor page ancestry")


def checkpoint_declarations(value, selection):
    closed(value, {"root", "child"}, "closed two-model checkpoint declaration")
    for name, declared, epochs in (("root", selection["previous_model"], 1), ("child", selection["model"], 2)):
        row = value[name]
        closed(row, {"adam_steps", "artifact", "completed_epochs", "feature_columns", "latent_width", "report_sha256", "state_sha256"}, "closed numerical checkpoint declaration")
        integer(row["completed_epochs"], epochs, epochs, "typed inherited completed epoch declaration")
        integer(row["feature_columns"], 53, 53, "typed feature columns declaration")
        integer(row["latent_width"], 8, 8, "typed latent width declaration")
        require(type(row["adam_steps"]) is list and len(row["adam_steps"]) == 4, "closed declared Adam block population")
        for step in row["adam_steps"]:
            integer(step, epochs, epochs, "typed declared Adam step")
        digest(row["report_sha256"])
        require(typed_equal(row["artifact"], declared["artifact"]) and row["state_sha256"] == declared["state_sha256"], "declared checkpoint/model identity join")


def resource_declarations(value, expected_pids):
    closed(value, {"active_lease_count", "global_active_lease_count", "global_waiting_request_count", "owner_pids", "scope", "waiting_request_count"}, "closed named process resource declaration")
    require(value["scope"] == "named_scan_process_owners_only" and typed_equal(value["owner_pids"], expected_pids), "named process resource scope")
    for field in ("active_lease_count", "global_active_lease_count", "global_waiting_request_count", "waiting_request_count"):
        integer(value[field], 0, 0, "typed recorded ending resource count")


def process_declarations(metadata, selection, pages, native, completion_cid, manifest_rows):
    integer(native["fresh_process_count"], 4, 4, "typed four recorded fresh processes")
    integer(native["owner_open_count"], 6, 6, "typed recorded owner opens")
    require(type(native["fresh_processes"]) is list and len(native["fresh_processes"]) == 4, "complete fresh process receipt population")
    checkpoints = metadata["checkpoint_before"]
    checkpoint_declarations(checkpoints, selection)
    require(typed_equal(checkpoints, metadata["checkpoint_after"]) and typed_equal(checkpoints, native["checkpoint_states"]), "unchanged exported checkpoint declarations")
    process_rows, pids = [], []
    for number in range(1, 5):
        run, request, launch = (metadata[f"process_{kind}_{number:02d}"] for kind in ("run", "request", "launch"))
        final = number == 4
        run_fields = {"complete", "final_resources", "fit_guard_scope", "helper_sha256", "materialization_receipt_sha256", "max_pages", "new_fitting_epochs", "next_cursor", "numerical_after", "numerical_before", "pages_created", "pid", "post_setup_fit_attempt_count", "prefix_tail_cid", "proof_authority", "qualified", "recorded_seconds", "registry_owner_generation_after", "registry_owner_generation_before", "request_cursor", "request_sha256", "root_cid", "run_number", "scan_execution_attested", "scheduler_configuration", "scheduler_state_path", "schema", "source_execution_attested", "source_model_owner_preservation", "timeout_seconds", "version_id"}
        closed(run, run_fields | ({"completion_cid", "coverage"} if final else set()), "closed fresh process run receipt")
        closed(request, {"checkpoint_states", "cursor", "expected_head", "expected_registry_owner_generation", "helper_sha256", "materialization_receipt_sha256", "max_pages", "output", "root_cid", "run_number", "scheduler_configuration", "scheduler_state_path", "schema", "timeout_seconds", "version_id"}, "closed fresh process request")
        closed(launch, {"child_pid", "child_working_directory", "helper_sha256", "parent_pid", "recorded_seconds", "request_sha256", "returncode", "run_number", "scheduler_state_path", "schema", "timeout_group_terminated"}, "closed child launch declaration")
        require(run["schema"] == "source-successor-fresh-scan-chunk@1" and request["schema"] == "source-successor-fresh-scan-chunk-request@1"
                and launch["schema"] == "source-successor-fresh-scan-child-launch@1", "recorded process protocol schemas")
        for value in (run, request, launch):
            integer(value["run_number"], number, number, "typed ordered process number")
        for value in (run, request):
            integer(value["max_pages"], 2, 2, "typed two pages per fresh process")
            integer(value["timeout_seconds"], 900, 900, "typed explicit process allowance")
            require(value["root_cid"] == selection["root_cid"] and value["version_id"] == selection["model"]["version_id"]
                    and typed_equal(value["scheduler_configuration"], native["scheduler_configuration"])
                    and value["scheduler_state_path"] == native["scheduler_state_path"], "fixed process root/model/scheduler declarations")
        for field in ("new_fitting_epochs", "post_setup_fit_attempt_count"):
            integer(run[field], 0, 0, "typed process no-fit declaration")
        require(run["complete"] is final and run["qualified"] is run["source_model_owner_preservation"] is True
                and run["proof_authority"] is run["scan_execution_attested"] is run["source_execution_attested"] is False,
                "process completeness/no-authority ceiling")
        require(run["fit_guard_scope"] == "three named owner-process training APIs plus exact frozen checkpoints and native owner rows", "recorded fit guard scope")
        require(typed_equal(run["numerical_before"], checkpoints) and typed_equal(run["numerical_after"], checkpoints)
                and typed_equal(request["checkpoint_states"], checkpoints) and typed_equal(request["expected_head"], selection["current_head"]), "no-fit checkpoint/head declaration joins")
        start = 64 * number
        previous_page = pages[2 * number - 1]["page_cid"]
        cursor(run["request_cursor"], selection["root_cid"], start, previous_page)
        require(typed_equal(run["request_cursor"], request["cursor"]), "run/request exact cursor declaration")
        expected_pages = [pages[2 * number]["page_cid"], pages[2 * number + 1]["page_cid"]]
        require(typed_equal(run["pages_created"], expected_pages) and run["prefix_tail_cid"] == expected_pages[-1], "process exact two-page cohort")
        if final:
            require(run["next_cursor"] is None and run["completion_cid"] == completion_cid
                    and typed_equal(run["coverage"], native["coverage"]), "final process completion declaration")
        else:
            cursor(run["next_cursor"], selection["root_cid"], start + 64, expected_pages[-1])
        integer(run["pid"], 1, 2**31 - 1, "typed process PID declaration")
        integer(launch["child_pid"], run["pid"], run["pid"], "launch/run PID declaration join")
        integer(launch["parent_pid"], native["pid"], native["pid"], "launch/parent PID declaration join")
        integer(launch["returncode"], 0, 0, "typed recorded launch exit")
        require(launch["timeout_group_terminated"] is False, "recorded launch did not terminate timeout group")
        require(run["pid"] != native["pid"] and run["pid"] not in pids, "distinct recorded process PID declarations")
        pids.append(run["pid"])
        resource_declarations(run["final_resources"], [run["pid"]])
        for field in ("registry_owner_generation_before", "registry_owner_generation_after"):
            integer(run[field], number + 3, number + 3, "typed recorded per-process owner generation")
        integer(request["expected_registry_owner_generation"], number + 3, number + 3, "typed requested owner generation")
        require(run["request_sha256"] == launch["request_sha256"] == manifest_rows[f"process_request_{number:02d}"]["sha256"]
                and run["materialization_receipt_sha256"] == request["materialization_receipt_sha256"] == manifest_rows["materialization"]["sha256"]
                and run["helper_sha256"] == request["helper_sha256"] == launch["helper_sha256"], "selected process request/materialization/helper raw bindings")
        digest(run["helper_sha256"])
        require(typed_equal(run, native["fresh_processes"][number - 1]), "native/full run receipt equality")
        for value in (run["recorded_seconds"], launch["recorded_seconds"]):
            require(type(value) in {int, float} and math.isfinite(value) and 0 <= value <= 900, "recorded process elapsed bound")
        process_rows.append(dict(run_number=number, pid=run["pid"], member_start=start, member_end=min(start + 64, 300),
                                 page_cids=expected_pages, complete=final, new_fitting_epochs=0,
                                 scope="recorded_receipts_not_independent_process_origin_attestation"))
    resource_declarations(native["final_resources"], [native["pid"], *pids])
    return process_rows


def role_declarations(audit, owners, selection, previous, current, dispositions):
    request = child_request(owners, selection)
    paths = {row["member"]["path"]: row["member"] for row in current.values()}
    by_path = {row["path"]: row for row in dispositions}
    roles = {row["role"]: row["path"] for row in request["selections"]}
    require(set(roles) == {"train", "tune", "canary"}, "complete declared child role vocabulary")
    rows = []
    for role in ("train", "tune", "canary"):
        path = roles[role]
        require(path in paths and path in by_path, "declared child role is inside complete scan")
        member = paths[path]
        rows.append(dict(role=role, path=path, source_cid=member["source_cid"], entry_cid=member["entry_cid"],
                         disposition=by_path[path]["disposition"], role_scope="declared_child_request_only_no_training_population_replay"))
    closure = audit["current_evaluation_closure"]
    closed(closure, {"complete_current_evaluation_bindings_verified", "frozen_cohort_role_source_bytes_verified", "models", "source_runtime_semantics_verified", "targets_independently_relowered"}, "closed independently recorded evaluation observation")
    require(closure["complete_current_evaluation_bindings_verified"] is closure["frozen_cohort_role_source_bytes_verified"] is True
            and closure["source_runtime_semantics_verified"] is closure["targets_independently_relowered"] is False, "evaluation observation authority ceiling")
    closed(closure["models"], {"root", "child"}, "closed evaluation model observations")
    for name, target_count in (("root", 1), ("child", 2)):
        captured_scope = previous if name == "root" else current
        captured_head = selection["previous_head"] if name == "root" else selection["current_head"]
        model_row = closure["models"][name]
        closed(model_row, {"current_evaluation_bindings", "current_role_paths", "stored_training_target_count"}, "closed model evaluation observations")
        integer(model_row["stored_training_target_count"], target_count, target_count, "typed recorded target count only")
        require(typed_equal(model_row["current_role_paths"], roles) and type(model_row["current_evaluation_bindings"]) is list
                and len(model_row["current_evaluation_bindings"]) == 2, "complete tune/canary observed binding declarations")
        observed = set()
        for item in model_row["current_evaluation_bindings"]:
            closed(item, {"binding", "role"}, "closed evaluation binding role")
            require(item["role"] in {"tune", "canary"} and item["role"] not in observed, "unique evaluation role observation")
            observed.add(item["role"])
            binding = item["binding"]
            closed(binding, {"ast_cid", "authored_contracts", "content_sha256", "entry", "head", "path", "repository_id", "schema", "source_cid", "source_key", "source_revision", "unit"}, "closed declared current evaluation source binding")
            path = roles[item["role"]]
            captured = next(row for row in captured_scope.values() if row["member"]["path"] == path)
            member = captured["member"]
            require(binding["schema"] == "codebase-ir-feature-source-binding@1" and binding["path"] == path
                    and binding["source_key"] == member["source_key"] and binding["source_cid"] == member["source_cid"]
                    and binding["ast_cid"] == member["ast_cid"] and binding["authored_contracts"] == []
                    and binding["content_sha256"] == raw_cid_digest(member["source_cid"])
                    and typed_equal(binding["entry"], captured["entry"]) and typed_equal(binding["head"], captured_head)
                    and binding["repository_id"] == captured_head["repository_id"]
                    and binding["source_revision"] == "snapshot:" + captured_head["snapshot_cid"], "evaluation binding/snapshot exact declaration joins")
            expected_unit = dict(schema="codebase-ir-structural-unit@1", source_key=member["source_key"], entry_cid=member["entry_cid"],
                                 ast_cid=member["ast_cid"], parse_status=member["parse_status"])
            require(typed_equal(binding["unit"], expected_unit), "evaluation unit/current snapshot join")
    return rows


def derive(metadata, manifest_rows):
    native, audit, prior = (metadata[k] for k in ANCHORS)
    require(native["schema"] == "codebase-full-successor-native-qualification@1"
            and audit["schema"] == "codebase-full-successor-independent-audit@1"
            and prior["schema"] == "repository-proof-index-source-successor-review@1", "fixed native/audit/prior schemas")
    require(native["qualified"] is native["complete_scan_qualified"] is native["cold_receiving_verified"] is True
            and audit["qualified"] is audit["complete_scan_qualified"] is True and audit["errors"] == [], "recorded complete successor observation")
    for field in ("384d_qualified", "cuda_qualified", "production_default_activated", "proof_authority", "repository_code_executed", "scan_execution_attested", "source_execution_attested", "worker_dispatch_qualified", "model_head_promoted", "numerical_page_reuse", "kernel_resource_enforcement_claimed"):
        require(native[field] is False, "native complete scan authority ceiling")
    for field in ("384d_qualified", "cuda_qualified", "proof_authority", "worker_dispatch_qualified", "git_executed", "native_owners_opened", "sql_executed", "primary_writes", "process_origin_attested", "numerical_execution_independently_reperformed", "targets_independently_relowered"):
        require(audit[field] is False, "independent metadata audit authority ceiling")
    closed(audit["audited_result"], {"path", "bytes", "sha256"}, "closed audited result raw binding")
    require(audit["audited_result"]["sha256"] == manifest_rows["full_scan_result"]["sha256"]
            and type(audit["audited_result"]["bytes"]) is int
            and audit["audited_result"]["bytes"] == manifest_rows["full_scan_result"]["size_bytes"], "audit/native selected raw binding")
    pairs = selection_pair(metadata)
    selection, root = pairs[0]
    reference_selection, reference_root = pairs[1]
    require(len(root["members"]) == 300 and typed_equal(native["current_head"], selection["current_head"])
            and typed_equal(native["previous_head"], selection["previous_head"])
            and typed_equal(prior["native_work"]["current_head"], selection["current_head"]), "same current successor generation/prior prefix")
    require(native["root_cid"] == metadata["optimized_root"]["artifact_cid"]
            and native["source_delta_cid"] == metadata["source_delta"]["artifact_cid"]
            and native["successor_selection_cid"] == metadata["optimized_selection"]["artifact_cid"], "native exact selected protocol artifacts")
    previous, previous_summary = snapshot(metadata["previous_manifest"], selection["previous_head"])
    current, current_summary = snapshot(metadata["current_manifest"], selection["current_head"])
    require(typed_equal([row["member"] for row in current.values()], root["members"]), "complete current snapshot/root member join")
    delta = source_delta(metadata, previous, current, selection)
    page_values, pages, dispositions, previous_page = [], [], [], None
    for i in range(10):
        role = f"default_page_{i:02d}"
        value, row, members = page(metadata[role], root, selection, i * 32, previous_page)
        page_values.append(value)
        pages.append(row)
        dispositions.extend(members)
        previous_page = row["page_cid"]
    require(len(dispositions) == 300 and len({row["source_key"] for row in dispositions}) == 300, "complete unique disposition coverage")
    counts = Counter(row["disposition"] for row in dispositions)
    coverage = dict(dispositions=dict(sorted(counts.items())), inferred_rows=counts["inferred"], inventory_entries=300, pages=10)
    require(typed_equal(coverage, native["coverage"]) and typed_equal(coverage, audit["complete_scan"]["coverage"]), "native/audit/full page coverage join")
    complete = envelope(metadata["completion"], {"authority", "coverage", "head_cid", "membership_cid", "model_artifact_cid", "pages", "root_cid", "schema"}, "codebase-inventory-resume-completion@1")
    require(complete["root_cid"] == selection["root_cid"] and complete["head_cid"] == root["head_cid"]
            and complete["membership_cid"] == root["membership_cid"] and complete["model_artifact_cid"] == selection["model"]["artifact_cid"]
            and typed_equal(complete["pages"], pages) and typed_equal(complete["coverage"], coverage)
            and metadata["completion"]["artifact_cid"] == native["completion_cid"] == audit["complete_scan"]["completion_cid"], "complete ten-page completion preimage and population")
    require(typed_equal(audit["complete_scan"]["page_cids"], [row["page_cid"] for row in pages])
            and audit["complete_scan"]["all300_members_have_explicit_dispositions"] is True
            and audit["complete_scan"]["all300_members_numerically_inferred"] is False, "complete disposition/all-inferred distinction")
    reference_value, reference_page, _ = page(metadata["reference_page"], reference_root, reference_selection, 0, None)
    for field in ("entries", "coverage", "inference"):
        require(typed_equal(page_values[0][field], reference_value[field]), "reference/default first32 exact exported equality")
    require(native["opt_out_equivalence"]["scope"] == "first32_ordered_members_only"
            and native["opt_out_equivalence"]["throughput_qualified"] is False
            and native["opt_out_equivalence"]["entries_coverage_and_inference_exact"] is True
            and native["opt_out_equivalence"]["optimized_page_cid"] == pages[0]["page_cid"]
            and native["opt_out_equivalence"]["reference_page_cid"] == reference_page["page_cid"], "reference scope is only one32-member page")
    for field, expected in (("new_default_scan_pages", 10), ("new_reference_scan_pages", 1), ("new_scan_pages_created", 11),
                            ("inherited_scan_pages", 0), ("inherited_setup_epochs", 2), ("new_fitting_epochs", 0),
                            ("post_setup_fit_attempt_count", 0), ("inference_attempts_outside_pages", 0)):
        integer(native[field], expected, expected, "typed complete scan historical work declaration")
    integer(native["pid"], 1, 2**31 - 1, "typed recorded parent PID")
    processes = process_declarations(metadata, selection, pages, native, metadata["completion"]["artifact_cid"], manifest_rows)
    roles = role_declarations(audit, metadata["owners_before"], selection, previous, current, dispositions)
    require(typed_equal(metadata["owners_before"], metadata["owners_after_parent"]), "unchanged parent-stage inert owner declarations")
    before, after = metadata["owners_before"], metadata["owners_after_cold"]
    closed(after, {"model_artifacts", "registry", "source"}, "closed ending owner metadata")
    require(typed_equal(before["source"], after["source"]) and typed_equal(before["model_artifacts"], after["model_artifacts"]), "unchanged source/model owner export declarations")
    closed(after["registry"], before["registry"], "closed ending registry metadata")
    for field in before["registry"]:
        if field != "meta":
            require(typed_equal(before["registry"][field], after["registry"][field]), "unchanged inert registry rows")
    require(type(before["registry"]["meta"]) is list and type(after["registry"]["meta"]) is list
            and len(before["registry"]["meta"]) == len(after["registry"]["meta"]) == 1, "single owner generation declaration")
    b, a = before["registry"]["meta"][0], after["registry"]["meta"][0]
    require(type(b) is list and type(a) is list and len(a) == len(b) == 6 and typed_equal(b[:-1], a[:-1]), "owner generation is only row difference")
    integer(b[-1], 3, 3, "typed recorded initial owner generation")
    integer(a[-1], 8, 8, "typed recorded final owner generation")
    materialization = metadata["materialization"]
    require(materialization["qualified"] is materialization["fresh_native_receiving_required"] is True
            and materialization["proof_authority"] is materialization["source_execution_attested"] is materialization["scan_execution_attested"] is False
            and typed_equal(materialization["current_head"], selection["current_head"])
            and typed_equal(materialization["checkpoint_states"], metadata["checkpoint_before"]), "materialization head/checkpoint/no-authority declarations")
    for field, expected in (("inherited_scan_pages", 0), ("inherited_setup_epochs", 2), ("new_fitting_epochs", 0), ("new_scan_pages", 0)):
        integer(materialization[field], expected, expected, "typed seed materialization work declaration")
    phases = native["phases"]
    require(type(phases) is list and len(phases) == 16 and all(type(row) is dict and set(row) == {"elapsed_seconds", "name", "status"} for row in phases)
            and len({row["name"] for row in phases}) == 16 and all(row["status"] == "completed" for row in phases), "complete16 recorded native phases")
    for row in phases:
        require(type(row["elapsed_seconds"]) in {int, float} and math.isfinite(row["elapsed_seconds"])
                and 0 <= row["elapsed_seconds"] <= 4200, "typed recorded phase duration")
    require(type(native["recorded_seconds"]) in {int, float} and math.isfinite(native["recorded_seconds"])
            and 0 <= native["recorded_seconds"] <= 4200, "typed recorded whole-attempt duration")
    require(typed_equal(audit["costs"]["phases"], phases), "recorded independent audit/native phase costs")
    return dict(complete_member_count=300, unique_observed_member_count=300, default_page_count=10,
                reference_page_count=1, reference_observed_member_count=32, outside_reference_prefix_member_count=268,
                recorded_default_inferred_rows=counts["inferred"], recorded_reference_inferred_rows=reference_page["inferred_rows"],
                default_dispositions=coverage["dispositions"], previous_snapshot=previous_summary, current_snapshot=current_summary,
                source_delta=delta, default_pages=pages, reference_first32_page=reference_page, member_dispositions=dispositions,
                complete_scan_cid=metadata["completion"]["artifact_cid"], fresh_process_count=4, fresh_processes=processes,
                declared_child_roles=roles, declared_child_role_counts=dict(Counter(row["role"] for row in roles)),
                root_training_exposure_scope="unavailable_model_training_bodies_not_selected",
                replay_exposure_scope="unavailable_parent_training_bodies_not_selected",
                exposure_independence_scope="unknown_prior_training_and_dependency_or_revision_closure",
                inherited_setup_epochs_declared=2, new_fitting_epochs_declared=0, recorded_native_seconds=native["recorded_seconds"],
                recorded_native_phase_count=16, recorded_controls=native["controls"],
                costs_scope="retained_attempt_declarations_no_new_native_execution_or_throughput_qualification",
                git_identity_scope="inert_snapshot_declarations_no_git_or_origin_attestation",
                numerical_identity_scope="exported_model_checkpoint_fingerprints_only_no_tensor_or_optimizer_replay",
                production_tasks_closed=[])


def population(output, expected, identity):
    require(output.is_absolute() and output.resolve(strict=True) == output, "canonical output directory fence")
    info = output.stat(follow_symlinks=False)
    require(stat.S_ISDIR(info.st_mode) and (info.st_dev, info.st_ino) == identity, "stable output directory identity")
    files, directories = set(), set()
    for parent, children, names in os.walk(output, followlinks=False):
        require(len(files) + len(directories) + len(children) + len(names) <= MAX_FILES, "bounded output population")
        for name in children:
            path = Path(parent) / name
            require(stat.S_ISDIR(path.stat(follow_symlinks=False).st_mode), "nonsymlink output directory")
            directories.add(path.relative_to(output).as_posix())
        for name in names:
            path = Path(parent) / name
            require(stat.S_ISREG(path.stat(follow_symlinks=False).st_mode), "regular nonsymlink output body")
            files.add(path.relative_to(output).as_posix())
    require(files == set(expected) and directories == {"inputs"}, "exact closed output population")


def evaluate(manifest_path, output):
    manifest_path, output = Path(manifest_path), Path(output)
    raw_manifest = Reads.bounded(manifest_path, 128 * 1024)
    manifest = document(raw_manifest)
    closed(manifest, {"schema", "selected_files"}, "closed full successor cohort manifest")
    require(manifest["schema"] == INPUT_SCHEMA and type(manifest["selected_files"]) is list
            and len(manifest["selected_files"]) == len(ROLES), "closed42-role full successor cohort input")
    reads, planned, manifest_rows = Reads(), [], {}
    reads.reserve(manifest_path, {"sha256": sha(raw_manifest), "size_bytes": len(raw_manifest)}, 128 * 1024)
    require(reads.take(manifest_path) == raw_manifest, "same bytes manifest parsed and pinned")
    for row, role in zip(manifest["selected_files"], ROLES, strict=True):
        closed(row, {"role", "path", "sha256", "size_bytes"}, "closed selected inert metadata descriptor")
        require(row["role"] == role, "exact ordered metadata role population")
        path = descriptor({k: row[k] for k in ("path", "sha256", "size_bytes")})
        if role in ANCHORS:
            require(row["sha256"] == ANCHORS[role], "fixed outer metadata anchor")
        reads.reserve(path, {k: row[k] for k in ("sha256", "size_bytes")}, 2 * MiB if role in {"previous_manifest", "current_manifest"} else MiB)
        require(path != manifest_path and path not in (p for _, p in planned), "distinct selected input bodies")
        planned.append((role, path))
        manifest_rows[role] = row
    bodies = {role: reads.take(path) for role, path in planned}
    metadata = {role: document(body) for role, body in bodies.items()}
    archive = metadata["independent_audit"]["archive"]["files"]
    require(type(archive) is list and len(archive) <= 2048, "bounded inert archive inventory")
    pins = {}
    for row in archive:
        require(type(row) is dict and type(row.get("path")) is str and row["path"] not in pins, "unique inert archive selector population")
        pins[row["path"]] = row
    for role, selector in SELECTORS.items():
        pin = pins.get(selector)
        require(type(pin) is dict and pin.get("kind") == "file" and type(pin.get("bytes")) is int
                and pin["bytes"] == len(bodies[role]) and pin.get("sha256") == sha(bodies[role]), "selected inert metadata archive raw join")
    derived = derive(metadata, manifest_rows)
    require(output.is_absolute() and not output.exists() and not output.is_symlink()
            and output.parent.resolve(strict=True) == output.parent, "fresh canonical output path required")
    protected = {manifest_path.parent, *(path.parent for _, path in planned)}
    require(all(output != scope and output not in scope.parents and scope not in output.parents for scope in protected), "protected selected input scope")
    output.mkdir()
    info = output.stat(follow_symlinks=False)
    identity = info.st_dev, info.st_ino
    (output / "inputs").mkdir()
    input_copy = output / "input.json"
    with input_copy.open("xb") as stream:
        stream.write(raw_manifest)
    retained, expected = [], {"input.json"}
    for index, (role, path) in enumerate(planned):
        relative = f"inputs/{index:03d}-{role}.body"
        target = output / relative
        with target.open("xb") as stream:
            stream.write(bodies[role])
        expected.add(relative)
        retained.append(dict(role=role, path=str(path), retained_path=str(target), sha256=sha(bodies[role]),
                             size_bytes=len(bodies[role]), selector=SELECTORS.get(role)))
    checkpoint("after_copy", output)
    report = dict(schema=REPORT_SCHEMA, status="passed", selected_manifest_sha256=sha(raw_manifest),
                  **dict.fromkeys(TRUE_FLAGS, True), **dict.fromkeys(FALSE_FLAGS, False), **dict.fromkeys(ZERO_FIELDS, 0),
                  selected_original_count=len(planned), selected_original_bytes=sum(len(body) for body in bodies.values()),
                  selected_files=retained, selected_original_manifest=dict(path=str(manifest_path), retained_path=str(input_copy),
                                                                         sha256=sha(raw_manifest), size_bytes=len(raw_manifest)),
                  raw_source_body_count=0, selected_model_body_count=0, selected_git_body_count=0,
                  limits=dict(max_originals=MAX_ORIGINALS, max_original_and_copy_files=MAX_FILES,
                              max_original_and_copy_bytes=MAX_BYTES, max_manifest_bytes=128 * 1024,
                              max_snapshot_body_bytes=2 * MiB, max_other_metadata_body_bytes=MiB,
                              max_report_bytes=4 * MiB, max_default_pages=10, max_reference_pages=1,
                              max_snapshot_members=300, max_json_nodes=1000000, max_json_depth=64), **derived)
    encoded = report_bytes(report)

    def closing(stage):
        reads.stable()
        checkpoint(stage + "_originals", output)
        require(Reads.bounded(input_copy, len(raw_manifest)) == raw_manifest, "late retained input manifest drift")
        for row in retained:
            require(Reads.bounded(Path(row["retained_path"]), row["size_bytes"]) == bodies[row["role"]], "late retained selected body drift")
        checkpoint(stage + "_copies", output)

    closing("before_publish")
    population(output, expected, identity)
    report_path = output / "full_successor_cohort_audit.json"
    with report_path.open("xb") as stream:
        stream.write(encoded)
    published = report_path.stat(follow_symlinks=False)
    try:
        checkpoint("after_publish", output)
        closing("after_publish")
        require(Reads.bounded(report_path, 4 * MiB) == encoded, "closing main report raw body drift")
        population(output, expected | {report_path.name}, identity)
    except (OSError, ValueError, TypeError):
        if output.resolve(strict=True) == output and report_path.exists():
            current = report_path.stat(follow_symlinks=False)
            if (published.st_dev, published.st_ino) == (current.st_dev, current.st_ino):
                report_path.unlink()
        raise
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        report = evaluate(args.manifest, args.output)
    except (Refused, OSError, ValueError, TypeError, KeyError, IndexError, UnicodeError, RecursionError, OverflowError) as exc:
        print(json.dumps(dict(schema=REPORT_SCHEMA, status="refused", reason=str(exc), unknown_pretraining_exposure=True,
                              **dict.fromkeys(FALSE_FLAGS, False)), sort_keys=True))
        return 2
    print(json.dumps(dict(status=report["status"], complete_member_count=report["complete_member_count"],
                          default_page_count=report["default_page_count"], reference_page_count=report["reference_page_count"]), sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
