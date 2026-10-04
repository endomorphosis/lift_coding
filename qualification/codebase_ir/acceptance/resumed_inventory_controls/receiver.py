"""Receive a frozen 300-member export without native owners or numerical replay.

The fixed independent raw audit identifies one historical export. Content hashes
and structural reconciliation are not signatures, numerical authentication, or
current source/model authority. The overall failed scan attempt stays failed.
"""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
import math
import os
import stat
import sys
from collections import Counter
from pathlib import Path

INPUT_SCHEMA = "codebase-ir-resumed-inventory-controls-input@1"
REPORT_SCHEMA = "codebase-ir-resumed-inventory-controls@1"
ORIGIN = "privately_frozen_completed_native_resumed_inventory_export"
AUDIT_SHA256 = "501330f167706f39bdbde7ac235de2444f2c94cb7a14bfe27f0f5258fb87e940"
AUDIT_BYTES = 6204895
SCAN_SHA256 = "56275f04227e19d7bebe3f9ed1df18ddeefd140e417e6841ead56f447ede982d"
COMPOSED_SHA256 = "b6307c0c8cd912c55161c3f6d50563cbf71e2d1ac9ba5538b52cb498a90e353f"
MAX_FILE = 8 * 1024 * 1024
MAX_MANIFEST = 256 * 1024
MAX_REPORT = 1024 * 1024
MAX_TOTAL = 32 * 1024 * 1024
MAX_FILES = 64
ROLES = ("root", *(f"page-{n:02d}" for n in range(1, 11)), "completion",
         "optout-root", "optout-reference-page")
AUTHORITY = {
    "admission_authority", "authoritative_cache_eligible", "behavioral_satisfaction",
    "completion_authority", "decoded_formulas_generated", "execution_authority",
    "mutation_authority", "proof_authority", "repository_code_executed",
    "runtime_behavior_verified", "scan_execution_attested", "source_execution_attested",
    "source_semantics_verified", "training_executed",
}
TRUE_FLAGS = ("retained_resumed_inventory_conformance", "ordered_complete_membership_reconciled",
              "historical_resumption_records_reconciled", "failed_and_composed_outcomes_preserved",
              "input_files_unchanged")
FALSE_FLAGS = (
    "native_execution_performed", "training_executed", "current_authority_claimed",
    "owner_database_opened", "profile_keys_read", "signature_authentication_performed",
    "numerical_state_replayed", "source_execution_replayed", "checker_executions_replayed",
    "runtime_execution_replayed", "resource_enforcement_qualified", "process_origin_attested",
    "live_eligibility_qualified", "production_acceptance_qualified", "native_export_adoption_qualified",
)
ZERO_FIELDS = ("runtime_fact_count", "tasks_omitted_count", "additional_attempted_training_epochs")
DISPOSITIONS = {"inferred": 205, "deferred_budget": 89, "opaque": 2, "parse_failed": 1,
                "unindexed": 1, "unsupported_target": 2}
MEMBER_FIELDS = {"ast_cid", "entry_cid", "opaque_reason", "parse_status", "path", "raw_path_hex",
                 "source_cid", "source_key", "source_size_bytes"}
ENTRY_FIELDS = {"coverage", "disposition", "entry_cid", "inference_index", "member_index", "reason",
                "source_digest", "source_key", "target_sha256"}
PAGE_FIELDS = {"authority", "coverage", "end", "entries", "head_cid", "inference", "membership_cid",
               "model_artifact_cid", "page_membership_cid", "previous_page_cid", "root_cid", "schema",
               "start", "total_entries", "worker_receipt"}
ROOT_FIELDS = {"authority", "head", "head_cid", "implementation", "limits", "members", "membership_cid",
               "model", "optimized", "schema"}
CHUNK_FIELDS = {"complete", "final_resources", "fit_guard_scope", "max_pages", "next_cursor", "numerical_after",
                "numerical_before", "pages_created", "pid", "post_setup_fit_attempt_count", "prefix_tail_cid", "qualified",
                "recorded_seconds", "registry_owner_generation_after", "registry_owner_generation_before", "request_cursor",
                "root_cid", "run_number", "schema", "source_model_owner_preservation", "timeout_seconds", "version_id"}
RESUME_FIELDS = {"complete", "completion_cid", "coverage", "final_resources", "fit_guard_scope", "numerical_after",
                 "numerical_before", "pages_created", "pid", "pids", "post_setup_fit_attempt_count", "process_runs", "qualified",
                 "recorded_seconds", "registry_owner_generation_after", "registry_owner_generation_before", "root_cid", "schema",
                 "source_model_owner_preservation", "version_id"}


class Refusal(ValueError):
    """A bounded receiving condition was not met."""


def require(condition, label):
    if not condition:
        raise Refusal(label)


def closed(value, fields, label):
    require(type(value) is dict and set(value) == set(fields), label + " fields")


def integer(value, low, high, label):
    require(type(value) is int and low <= value <= high, label + " exact integer")


def digest(value):
    require(type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value),
            "canonical SHA256")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("ascii")


def equal(left, right):
    return wire(left) == wire(right)


def document(raw, limit=MAX_FILE):
    require(type(raw) is bytes and len(raw) <= limit, "JSON byte budget")

    def pairs(rows):
        value = {}
        for key, child in rows:
            require(key not in value, "duplicate JSON key")
            value[key] = child
        return value

    def bad_constant(_):
        raise Refusal("nonfinite JSON number")

    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=bad_constant)
    except (ValueError, UnicodeError, RecursionError) as error:
        if isinstance(error, Refusal):
            raise
        raise Refusal("invalid JSON") from error
    pending, count = [(value, 0)], 0
    while pending:
        item, depth = pending.pop()
        count += 1
        require(depth <= 64 and count <= 500000, "JSON structure budget")
        if type(item) is dict:
            pending.extend((key, depth + 1) for key in item)
            pending.extend((child, depth + 1) for child in item.values())
        elif type(item) is list:
            pending.extend((child, depth + 1) for child in item)
        elif type(item) is str:
            try:
                item.encode("utf-8")
            except UnicodeError as error:
                raise Refusal("surrogate string") from error
        elif type(item) is float:
            require(math.isfinite(item), "nonfinite JSON float")
        elif type(item) is int:
            require(abs(item) <= 2**63 - 1, "JSON integer magnitude")
    require(type(value) is dict, "JSON object")
    return value


def cid_raw(raw, structured=False):
    prefix = b"\x01\xa9\x02\x12\x20" if structured else b"\x01\x55\x12\x20"
    return "b" + base64.b32encode(prefix + hashlib.sha256(raw).digest()).decode().lower().rstrip("=")


def cid(value):
    pending = [value]
    while pending:
        item = pending.pop()
        require(type(item) in (dict, list, str, bool, int, type(None)), "DAG JSON value type")
        if type(item) is dict:
            pending.extend(item)
            pending.extend(item.values())
        elif type(item) is list:
            pending.extend(item)
    return cid_raw(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                              allow_nan=False).encode("utf-8"), structured=True)


def cid_shape(value, structured=True):
    require(type(value) is str and value.startswith("b") and "=" not in value, "CID canonical spelling")
    try:
        raw = base64.b32decode(value[1:].upper() + "=" * ((1 - len(value)) % 8))
    except ValueError as error:
        raise Refusal("CID encoding") from error
    prefix = b"\x01\xa9\x02\x12\x20" if structured else b"\x01\x55\x12\x20"
    require(raw.startswith(prefix) and len(raw) == len(prefix) + 32
            and "b" + base64.b32encode(raw).decode().lower().rstrip("=") == value, "CID codec/size")


def authority(value):
    closed(value, AUTHORITY, "native authority ceiling")
    require(all(item is False for item in value.values()), "native authority elevated")


def canonical_path(value, existing=True):
    require(type(value) in (str, type(Path())) or isinstance(value, Path), "path type")
    path = Path(value)
    require(path.is_absolute() and path.resolve(strict=existing) == path, "canonical absolute path")
    return path


class Capture:
    """Bound allocations using the pin and aggregate allowance before reading."""
    def __init__(self):
        self.raw = {}
        self.total = 0

    @staticmethod
    def read(path, allowance):
        canonical_path(path)
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            try:
                before = os.fstat(fd)
                require(stat.S_ISREG(before.st_mode) and 0 <= before.st_size <= allowance,
                        "regular file/preallocation budget")
                data = bytearray()
                while len(data) <= allowance:
                    piece = os.read(fd, min(65536, allowance + 1 - len(data)))
                    if not piece:
                        break
                    data.extend(piece)
                after = os.fstat(fd)
                def key(s):
                    return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
                require(len(data) <= allowance and len(data) == before.st_size and key(before) == key(after),
                        "bounded descriptor changed")
                canonical_path(path)
                end = path.stat(follow_symlinks=False)
                require(key(end) == key(after) and stat.S_ISREG(end.st_mode), "path changed during read")
                return bytes(data)
            finally:
                os.close(fd)
        except OSError as error:
            raise Refusal("guarded input read failed") from error

    def take(self, path, pin=None, limit=MAX_FILE):
        require(path not in self.raw and len(self.raw) < MAX_FILES, "duplicate input/file budget")
        allowance = min(limit, MAX_TOTAL - self.total, pin["size_bytes"] if pin else limit)
        require(allowance >= 0, "aggregate read budget")
        raw = self.read(path, allowance)
        if pin:
            require(len(raw) == pin["size_bytes"] and sha(raw) == pin["sha256"], "raw input pin")
        self.raw[path] = raw
        self.total += len(raw)
        return raw

    def stable(self):
        for path, raw in self.raw.items():
            require(self.read(path, len(raw)) == raw, "final original/copy/report bytes changed")


def descriptor(value):
    closed(value, {"path", "sha256", "size_bytes"}, "descriptor")
    canonical_path(value["path"])
    digest(value["sha256"])
    integer(value["size_bytes"], 0, MAX_FILE, "descriptor byte budget")


def manifest_rows(value):
    closed(value, {"schema", "fixture_origin", "historical_scan_audit", "historical_scan_result",
                   "composed_worker_result", "transport_artifacts", "chunks", "resume_record"}, "manifest")
    require(value["schema"] == INPUT_SCHEMA and value["fixture_origin"] == ORIGIN, "manifest profile")
    rows = [(key, value[key]) for key in ("historical_scan_audit", "historical_scan_result", "composed_worker_result")]
    transport = value["transport_artifacts"]
    require(type(transport) is list and len(transport) == 14, "exact transport population")
    for index, row in enumerate(transport):
        closed(row, {"role", "input"}, "transport role")
        require(row["role"] == ROLES[index], "transport role order")
        rows.append(("transport_" + row["role"], row["input"]))
    chunks = value["chunks"]
    require(type(chunks) is list and len(chunks) == 4, "exact chunk population")
    for n, row in enumerate(chunks, 1):
        closed(row, {"run_number", "record", "stdout", "stderr"}, "chunk inputs")
        integer(row["run_number"], n, n, "chunk run order")
        rows.extend((f"chunk_{n}_{role}", row[role]) for role in ("record", "stdout", "stderr"))
    rows.append(("resume_record", value["resume_record"]))
    require(len(rows) == 30, "exact selected closure")
    for _, pin in rows:
        descriptor(pin)
    require(len({pin["path"] for _, pin in rows}) == 30, "duplicate input role path")
    require(sum(pin["size_bytes"] for _, pin in rows) <= MAX_TOTAL // 2 - MAX_REPORT, "closure budget before allocation")
    for role, expected in (("historical_scan_audit", AUDIT_SHA256), ("historical_scan_result", SCAN_SHA256),
                           ("composed_worker_result", COMPOSED_SHA256)):
        require(value[role]["sha256"] == expected, "fixed independent historical raw anchor")
    require(value["historical_scan_audit"]["size_bytes"] == AUDIT_BYTES, "fixed audit size")
    return rows


def numeric_state(value, model):
    closed(value, {"adam_steps", "completed_epochs", "feature_columns", "latent_width", "state_sha256"},
           "recorded numerical state")
    integer(value["completed_epochs"], 2, 2, "inherited epochs")
    integer(value["feature_columns"], 53, 53, "recorded basis width")
    integer(value["latent_width"], 8, 8, "recorded latent width")
    require(type(value["adam_steps"]) is list and len(value["adam_steps"]) == 4, "recorded optimizer population")
    for step in value["adam_steps"]:
        integer(step, 2, 2, "recorded optimizer step")
    require(value["state_sha256"] == model["state_sha256"], "recorded frozen state identity")


def root_record(root):
    closed(root, ROOT_FIELDS, "root")
    require(root["schema"] == "codebase-inventory-resume-root@1" and root["optimized"] is True, "root profile")
    authority(root["authority"])
    closed(root["head"], {"schema", "repository_id", "generation", "snapshot_cid", "manifest_cid", "receipt_cid",
                          "ast_revision_id"}, "source head")
    integer(root["head"]["generation"], 1, 1, "captured source generation")
    require(root["head"]["schema"] == "codebase-head@1" and root["head_cid"] == cid(root["head"]), "source head CID")
    members = root["members"]
    require(type(members) is list and len(members) == 300, "complete 300-member ledger")
    previous, identities = None, set()
    for member in members:
        closed(member, MEMBER_FIELDS, "captured member")
        raw_hex = member["raw_path_hex"]
        require(type(raw_hex) is str and 0 < len(raw_hex) <= 8192 and len(raw_hex) % 2 == 0
                and all(c in "0123456789abcdef" for c in raw_hex), "captured raw path")
        path = bytes.fromhex(raw_hex)
        require(previous is None or path > previous, "strict raw member order")
        previous = path
        require(member["source_key"] == "raw:" + raw_hex and member["source_key"] not in identities, "member source identity")
        identities.add(member["source_key"])
        require(type(member["path"]) is str and member["path"].encode("utf-8") == path
                and not member["path"].startswith("/") and all(x not in ("", ".", "..") for x in member["path"].split("/")),
                "captured relative path correspondence")
        integer(member["source_size_bytes"], 0, MAX_FILE, "source size metadata")
        require(member["parse_status"] in {"ok", "failed", "opaque", "unindexed"}, "captured parse disposition")
        cid_shape(member["entry_cid"])
        if member["ast_cid"] is not None:
            cid_shape(member["ast_cid"])
        if member["source_cid"] is not None:
            cid_shape(member["source_cid"], structured=False)
        require(member["opaque_reason"] in {None, "undecodable", "oversized"}, "captured opacity")
        require((member["parse_status"] == "opaque") == (member["opaque_reason"] is not None), "opacity/parse correspondence")
        require((member["parse_status"] in {"ok", "failed"}) == (member["ast_cid"] is not None),
                "captured AST availability correspondence")
        require((member["opaque_reason"] == "oversized") == (member["source_cid"] is None),
                "captured source CID availability")
    require(root["membership_cid"] == cid(members), "ordered whole membership CID")
    limits = root["limits"]
    closed(limits, {"max_file_bytes", "max_inferred_rows", "max_input_bytes", "max_inventory_entries", "max_manifest_bytes",
                   "max_output_bytes", "max_pages", "max_target_bytes", "page_entries"}, "root bounds")
    for name, value in limits.items():
        integer(value, 1, 64 * 1024 * 1024, "root declared " + name)
    require(limits["page_entries"] == 32 and 300 <= limits["max_inventory_entries"] <= 1024
            and limits["max_pages"] <= 1024 and limits["max_inferred_rows"] <= 1024, "selected bounded capture profile")
    impl = root["implementation"]
    closed(impl, {"files", "scope", "sha256"}, "inert producer inventory")
    require(type(impl["files"]) is dict and 1 <= len(impl["files"]) <= 32
            and impl["scope"] == "listed_local_files_only_not_execution_attestation"
            and impl["sha256"] == sha(wire(impl["files"])), "producer digest/scope")
    for pin in impl["files"].values():
        digest(pin)
    model = root["model"]
    closed(model, {"ancestry", "artifact", "artifact_cid", "contract_sha256", "feature_columns", "feature_space_sha256",
                   "latent_width", "projection_ids", "projection_widths", "state_sha256", "variant_id", "version_id"}, "model metadata")
    integer(model["feature_columns"], 53, 53, "basis metadata")
    integer(model["latent_width"], 8, 8, "latent metadata")
    require(model["projection_ids"] == ["codebase_ir.contracts@1", "codebase_ir.program@1"]
            and equal(model["projection_widths"], {"codebase_ir.contracts@1": 2, "codebase_ir.program@1": 51}), "frozen projection basis")
    for name in ("contract_sha256", "feature_space_sha256", "state_sha256"):
        digest(model[name])
    require(type(model["ancestry"]) is list and len(model["ancestry"]) == 2, "recorded model ancestry")
    for ancestor in model["ancestry"]:
        closed(ancestor, {"artifact", "version_id"}, "ancestry metadata")
        closed(ancestor["artifact"], {"bytes", "sha256"}, "model artifact metadata")
        integer(ancestor["artifact"]["bytes"], 1, MAX_FILE, "artifact metadata size")
        digest(ancestor["artifact"]["sha256"])
        require(type(ancestor["version_id"]) is str and ancestor["version_id"].startswith("sha256:"), "model version label")
        digest(ancestor["version_id"][7:])
    require(equal(model["artifact"], model["ancestry"][0]["artifact"])
            and model["version_id"] == model["ancestry"][0]["version_id"], "selected model ancestry binding")
    artifact_bytes = bytes.fromhex(model["artifact"]["sha256"])
    expected = "b" + base64.b32encode(b"\x01\x55\x12\x20" + artifact_bytes).decode().lower().rstrip("=")
    require(model["artifact_cid"] == expected, "artifact CID metadata")
    return cid(root)


def coverage(rows):
    counts = Counter(row["disposition"] for row in rows)
    return {"dispositions": dict(sorted(counts.items())), "inferred_rows": counts["inferred"], "inventory_entries": len(rows)}


def page_record(page, root, root_cid, previous, offset):
    closed(page, PAGE_FIELDS, "page")
    authority(page["authority"])
    integer(page["start"], offset, offset, "page start")
    integer(page["end"], offset + 1, min(offset + 32, 300), "page end")
    require(page["end"] == min(offset + 32, 300), "exact page population")
    integer(page["total_entries"], 300, 300, "page total membership")
    require(page["schema"] == "codebase-inventory-resume-page@1" and page["root_cid"] == root_cid
            and page["head_cid"] == root["head_cid"] and page["membership_cid"] == root["membership_cid"]
            and page["model_artifact_cid"] == root["model"]["artifact_cid"]
            and page["previous_page_cid"] == previous, "page root/source/model/predecessor identity")
    selected = root["members"][offset:page["end"]]
    require(page["page_membership_cid"] == cid(selected), "page ordered membership slice")
    entries = page["entries"]
    require(type(entries) is list and len(entries) == len(selected), "one disposition per source")
    inference = page["inference"]
    closed(inference, {"admitted", "contract_sha256", "coverage", "decoded_formulas_generated", "feature_space_sha256",
                       "formalized", "promotion_performed", "qualified", "representation", "rows", "schema", "state_sha256",
                       "training_executed"}, "inert numerical rows")
    require(inference["schema"] == "native-projection-feature-inference/v1"
            and inference["representation"] == "native_compiler_structural_features_not_semantic_text_embeddings", "numerical representation scope")
    for name in ("admitted", "decoded_formulas_generated", "formalized", "promotion_performed", "qualified", "training_executed"):
        require(inference[name] is False, "numerical row authority")
    for name in ("contract_sha256", "feature_space_sha256", "state_sha256"):
        require(inference[name] == root["model"][name], "numerical row frozen metadata")
    require(type(inference["rows"]) is list and len(inference["rows"]) <= 32, "numerical row population")
    inferred, recorded_coverage = 0, []
    for index, (entry, member) in enumerate(zip(entries, selected, strict=True), offset):
        closed(entry, ENTRY_FIELDS, "source disposition")
        integer(entry["member_index"], index, index, "source disposition index")
        require(entry["entry_cid"] == member["entry_cid"] and entry["source_key"] == member["source_key"], "source disposition exact membership")
        disposition = entry["disposition"]
        require(disposition in DISPOSITIONS, "source disposition vocabulary")
        require(type(entry["coverage"]) is list and len(entry["coverage"]) <= 2, "projection coverage population")
        if disposition in {"inferred", "deferred_budget", "unsupported_target"}:
            require(member["parse_status"] == "ok", "eligible disposition lacks captured AST")
            digest(entry["source_digest"])
            digest(entry["target_sha256"])
        else:
            expected = {"opaque": "opaque", "parse_failed": "failed", "unindexed": "unindexed"}[disposition]
            require(member["parse_status"] == expected and entry["source_digest"] is None
                    and entry["target_sha256"] is None, "unavailable source target preserved")
        if disposition == "inferred":
            integer(entry["inference_index"], inferred, inferred, "ordered inference index")
            require(entry["reason"] is None and len(entry["coverage"]) == 2 and inferred < len(inference["rows"]),
                    "inferred row completeness")
            row = inference["rows"][inferred]
            closed(row, {"latent", "reconstructed_projection_features", "source_digest"}, "recorded inference row")
            require(row["source_digest"] == entry["source_digest"], "inference source join")
            vectors = [(row["latent"], 8)]
            closed(row["reconstructed_projection_features"], root["model"]["projection_ids"], "recorded projections")
            vectors.extend((row["reconstructed_projection_features"][name], width)
                           for name, width in root["model"]["projection_widths"].items())
            for vector, width in vectors:
                require(type(vector) is list and len(vector) == width
                        and all(type(x) in (int, float) and abs(x) <= 10**100 for x in vector), "bounded finite numerical vector")
            for position, atom in enumerate(entry["coverage"]):
                closed(atom, {"known_atoms", "projection_id", "unknown_atoms"}, "coverage atom")
                name = root["model"]["projection_ids"][position]
                width = root["model"]["projection_widths"][name]
                integer(atom["known_atoms"], 0, width, "known atoms")
                integer(atom["unknown_atoms"], 0, width, "unknown atoms")
                require(atom["projection_id"] == name and atom["known_atoms"] + atom["unknown_atoms"] == width,
                        "complete projection atom accounting")
            recorded_coverage.extend(entry["coverage"])
            inferred += 1
        else:
            require(entry["inference_index"] is None and type(entry["reason"]) is str and entry["reason"],
                    "deferred/unsupported reason remains available")
            require(not entry["coverage"] or disposition == "deferred_budget", "unsupported source acquired projection coverage")
            if disposition == "deferred_budget":
                require(len(entry["coverage"]) == 2, "deferred target retains structural coverage")
                for position, atom in enumerate(entry["coverage"]):
                    closed(atom, {"known_atoms", "projection_id", "unknown_atoms"}, "deferred coverage atom")
                    name = root["model"]["projection_ids"][position]
                    width = root["model"]["projection_widths"][name]
                    integer(atom["known_atoms"], 0, width, "deferred known atoms")
                    integer(atom["unknown_atoms"], 0, width, "deferred unknown atoms")
                    require(atom["projection_id"] == name and atom["known_atoms"] + atom["unknown_atoms"] == width,
                            "deferred projection atom accounting")
            reasons = {"deferred_budget": "page_worker_input_byte_budget", "unsupported_target": "native_target_not_complete",
                       "parse_failed": "captured_parse_failed", "unindexed": "captured_source_has_no_ast_projection"}
            if disposition == "opaque":
                require(entry["reason"] == member["opaque_reason"], "opaque reason join")
            else:
                require(entry["reason"] == reasons[disposition], "deferred/unsupported reason")
    require(inferred == len(inference["rows"]) and equal(recorded_coverage, inference["coverage"])
            and equal(page["coverage"], coverage(entries)), "complete page/inference coverage")
    worker = page["worker_receipt"]
    closed(worker, {"elapsed_ms", "executable_sha256", "input_bytes", "input_sha256", "limits", "memory_enforcement",
                    "output_bytes", "output_sha256", "returncode", "source_execution_attested", "worker_sha256",
                    "workspace_cleaned"}, "recorded numerical worker receipt")
    for name in ("input_sha256", "output_sha256", "executable_sha256", "worker_sha256"):
        digest(worker[name])
    require(worker["worker_sha256"] == root["implementation"]["files"][
        "ipfs_datasets_py.optimizers.logic_theorem_optimizer.codebase_inventory_resume_worker"], "worker implementation label")
    integer(worker["returncode"], 0, 0, "recorded numerical return code")
    integer(worker["elapsed_ms"], 0, 420000, "recorded numerical duration")
    closed(worker["limits"], {"max_input_bytes", "max_output_bytes", "resident_memory_bytes"}, "worker declared limits")
    for name in worker["limits"]:
        integer(worker["limits"][name], 1, 2**32, "worker limit metadata")
    integer(worker["input_bytes"], 1, worker["limits"]["max_input_bytes"], "recorded worker input bytes")
    integer(worker["output_bytes"], 1, worker["limits"]["max_output_bytes"], "recorded worker output bytes")
    require(worker["source_execution_attested"] is False and worker["workspace_cleaned"] is True
            and worker["memory_enforcement"] == "sampled_process_tree_rss_with_possible_overshoot", "worker receipt scope")
    raw = wire(page)
    page_cid = cid_raw(raw)
    return {"page_cid": page_cid, "start": offset, "end": page["end"], "membership_cid": page["page_membership_cid"],
            "inferred_rows": inferred, "dispositions": coverage(entries)["dispositions"]}


def cursor(value, root_cid, previous, offset):
    closed(value, {"schema", "root_cid", "previous_page_cid", "next_offset"}, "resume cursor")
    integer(value["next_offset"], offset, offset, "resume next offset")
    require(value["schema"] == "codebase-inventory-resume-cursor@1" and value["root_cid"] == root_cid
            and value["previous_page_cid"] == previous, "cursor root/predecessor")


def frontier(root, pages, completion=None):
    """A closed receiving view: no retained prefix establishes complete absence."""
    require(type(pages) is list and len(pages) <= 10, "prefix page bound")
    root_cid = root_record(root)
    summaries, rows, previous, offset = [], [], None, 0
    for page in pages:
        summary = page_record(page, root, root_cid, previous, offset)
        summaries.append(summary)
        rows.extend(page["entries"])
        previous, offset = summary["page_cid"], summary["end"]
    complete = completion is not None
    if complete:
        closed(completion, {"authority", "coverage", "head_cid", "membership_cid", "model_artifact_cid", "pages", "root_cid", "schema"}, "completion")
        authority(completion["authority"])
        require(offset == 300 and len(pages) == 10 and completion["schema"] == "codebase-inventory-resume-completion@1"
                and completion["root_cid"] == root_cid and completion["head_cid"] == root["head_cid"]
                and completion["membership_cid"] == root["membership_cid"]
                and completion["model_artifact_cid"] == root["model"]["artifact_cid"]
                and equal(completion["pages"], summaries), "completion requires exact entire chain")
        whole = coverage(rows) | {"pages": 10}
        require(equal(whole, completion["coverage"]) and equal(whole["dispositions"], DISPOSITIONS), "complete selected coverage")
    return {"complete": complete, "captured_member_count": 300, "received_member_count": offset,
            "unreceived_member_count": 300 - offset, "page_count": len(pages),
            "absence_established": False, "runtime_behavior": "unknown",
            "next_cursor": None if complete else {"schema": "codebase-inventory-resume-cursor@1", "root_cid": root_cid,
                                                   "previous_page_cid": previous, "next_offset": offset},
            "ordered_pages": summaries, "coverage": coverage(rows)}


def reconcile(bundle):
    """Pure historical receiving profile; production adoption is never claimed."""
    closed(bundle, {"audit", "scan_result", "composed_result", "transport", "chunks", "resume"}, "receiving bundle")
    audit, scan, composed = bundle["audit"], bundle["scan_result"], bundle["composed_result"]
    transport = bundle["transport"]
    closed(transport, ROLES, "ordered transport")
    root = transport["root"]
    root_cid = root_record(root)
    pages = [transport[f"page-{n:02d}"] for n in range(1, 11)]
    done = transport["completion"]
    view = frontier(root, pages, done)
    summaries, whole = view["ordered_pages"], view["coverage"] | {"pages": 10}
    page_ids = [row["page_cid"] for row in summaries]
    completion_cid = cid(done)
    require(audit["schema"] == "inventory-resume-worker-independent-audit@1" and audit["authority"] == "none"
            and audit["qualified"] is False and audit["native_jobs_executed"] == 0
            and type(audit["native_jobs_executed"]) is int and audit["native_owner_databases_opened"] == 0
            and type(audit["native_owner_databases_opened"]) is int and audit["training_steps"] == 0
            and type(audit["training_steps"]) is int, "failed historical audit remains unauthoritative")
    observation = audit["positive_completed_scan"]
    require(observation["schema"] == "inventory-resume-positive-completed-scan-observation@1" and observation["verified"] is True
            and observation["overall_native_qualification"] is False and observation["native_worker_qualified"] is False,
            "scan observation cannot qualify failed worker attempt")
    for name in ("current_deployment_freshness_attested", "numerical_execution_independently_reperformed", "process_origin_attested"):
        require(observation[name] is False, "historical scan authenticity ceiling")
    for record in (observation, audit["scan"], scan):
        root_name = "scan_root_cid" if record is scan else "root_cid"
        done_name = "completed_scan_cid" if record is scan else "completion_cid"
        coverage_name = "scan_coverage" if record is scan else "coverage"
        require(record[root_name] == root_cid and record[done_name] == completion_cid and equal(record[coverage_name], whole),
                "raw scan/root/completion/coverage join")
    require(equal(observation["head"], root["head"]) and observation["membership_cid"] == root["membership_cid"]
            and equal(observation["model"], root["model"]) and equal(observation["ordered_pages"], summaries), "independent full membership/ordered page join")
    require(audit["scan"]["raw_worker_input_output_not_retained"] is True
            and audit["scan"]["numerical_execution_independently_reperformed"] is False, "raw numerical request/output remains unavailable")
    require(type(audit["scan"]["page_receipts"]) is list and len(audit["scan"]["page_receipts"]) == 10, "complete worker receipt population")
    for row, page, summary in zip(audit["scan"]["page_receipts"], pages, summaries, strict=True):
        closed(row, {"page_cid", "inferred_rows", "worker_receipt"}, "independent numerical receipt")
        require(equal(row, {"page_cid": summary["page_cid"], "inferred_rows": summary["inferred_rows"],
                            "worker_receipt": page["worker_receipt"]}), "independent numerical receipt join")
    declared = observation["transport_artifacts"]
    require(type(declared) is list and len(declared) == 14 and [row["role"] for row in declared] == list(ROLES), "audit transport population/order")
    for row in declared:
        value = transport[row["role"]]
        structured = row["role"] in {"root", "completion", "optout-root"}
        raw = (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
               if structured else wire(value))
        require(row["codec"] == ("dag-json" if structured else "raw") and row["cid"] == cid_raw(raw, structured)
                and row["sha256"] == sha(raw) and type(row["bytes"]) is int and row["bytes"] == len(raw), "immutable raw transport audit pin")
    reference_root = copy.deepcopy(transport["optout-root"])
    require(reference_root["optimized"] is False, "reference opt-out profile")
    reference_root["optimized"] = True
    require(equal(reference_root, root), "reference root differs beyond optimization choice")
    reference_page = copy.deepcopy(transport["optout-reference-page"])
    refroot_cid = cid(transport["optout-root"])
    require(reference_page["root_cid"] == refroot_cid, "reference page root")
    reference_page["root_cid"] = root_cid
    require(equal({k: v for k, v in reference_page.items() if k != "worker_receipt"},
                  {k: v for k, v in pages[0].items() if k != "worker_receipt"}), "reference first-page structural equality")
    require(equal(observation["reference_page_worker_receipt"], transport["optout-reference-page"]["worker_receipt"]), "retained reference receipt")
    require(scan["qualified"] is False and type(scan["error"]) is str and scan["error"]
            and scan["error_type"] == "StructuredIdentityError" and composed["qualified"] is True, "failed09 and composed14 whole outcomes")
    for value in (scan, composed):
        for name in ("384d_qualified", "cuda_qualified", "production_default_activated", "proof_authority", "scan_execution_attested", "source_execution_attested"):
            require(value[name] is False, "native fixture scope ceiling")
    require(composed["worker_launched"] is True, "recorded composed worker result distinct from local receiver")
    fresh = observation["fresh_process_resume"]
    require(fresh["schema"] == "inventory-resume-fresh-process@2" and fresh["process_origin_attested"] is False
            and fresh["reported_no_fitting"] is True and fresh["all_chunk_current_source_model_closures_retained"] is True,
            "historical process scope")
    integer(fresh["owner_processes"], 4, 4, "historical process count")
    require(type(fresh["chunks"]) is list and len(fresh["chunks"]) == 4 and type(bundle["chunks"]) is list
            and len(bundle["chunks"]) == 4, "four historical resumption records")
    retained_chunks, pids, chunk_details = [], [], []
    numerical = observation["numerical_state"]
    numeric_state(numerical, root["model"])
    for n, (selected, recorded) in enumerate(zip(bundle["chunks"], fresh["chunks"], strict=True), 1):
        closed(selected, {"record", "stdout", "stderr"}, "chunk packet")
        record = selected["record"]
        start = n * 64
        end = min(start + 64, 300)
        terminal = n == 4
        closed(record, CHUNK_FIELDS | ({"coverage", "completion_cid"} if terminal else set()), "native chunk record")
        integer(record["run_number"], n, n, "historical run number")
        integer(record["max_pages"], 2, 2, "historical chunk bound")
        integer(record["pid"], 1, 2**31 - 1, "recorded process label")
        require(record["pid"] not in pids, "duplicate historical process label")
        pids.append(record["pid"])
        require(record["schema"] == "inventory-resume-fresh-process-chunk@1" and record["root_cid"] == root_cid
                and record["version_id"] == root["model"]["version_id"] and record["qualified"] is True
                and record["complete"] is terminal and record["source_model_owner_preservation"] is True,
                "chunk profile/recorded completion scope")
        require(type(record["timeout_seconds"]) is float and record["timeout_seconds"] == 420.0
                and type(record["recorded_seconds"]) is float and 0 <= record["recorded_seconds"] <= 420,
                "recorded typed chunk times")
        integer(record["post_setup_fit_attempt_count"], 0, 0, "chunk new fits")
        require(equal(record["final_resources"], {"active_lease_count": 0, "waiting_request_count": 0}), "recorded chunk final counts")
        cursor(record["request_cursor"], root_cid, page_ids[n * 2 - 1], start)
        expected_pages = page_ids[n * 2:n * 2 + 2]
        require(record["pages_created"] == expected_pages and record["prefix_tail_cid"] == expected_pages[-1], "exact historical chunk pages")
        if terminal:
            require(record["next_cursor"] is None and record["completion_cid"] == completion_cid
                    and equal(record["coverage"], whole), "terminal chunk entire completion")
        else:
            cursor(record["next_cursor"], root_cid, expected_pages[-1], end)
            require("completion_cid" not in record and "coverage" not in record, "partial chunk fabricated completion")
        for name in ("numerical_before", "numerical_after"):
            numeric_state(record[name], root["model"])
            require(equal(record[name], numerical), "historical chunk frozen numerical metadata")
        for name in ("registry_owner_generation_before", "registry_owner_generation_after"):
            integer(record[name], n + 2, n + 2, "recorded chunk owner generation")
        expected_recorded = {key: record[key] for key in ("run_number", "pid", "pages_created", "request_cursor", "next_cursor",
                            "recorded_seconds", "registry_owner_generation_before", "registry_owner_generation_after")}
        expected_recorded.update(native_final_resources=record["final_resources"], stdout_sha256=sha(selected["stdout"]),
                                 stderr_sha256=sha(selected["stderr"]))
        require(equal(recorded, expected_recorded) and selected["stderr"] == b"", "audit chunk/stdout/stderr commitment")
        lines = selected["stdout"].splitlines()
        require(lines and len(lines) <= 64 and all(line.startswith(b"logic tree pin ") for line in lines[:-1]), "bounded recorded banner profile")
        require(equal(document(lines[-1], 1024), {"qualified": True, "recorded_seconds": record["recorded_seconds"]}), "recorded stdout disposition/time")
        retained_chunks.append(record)
        chunk_details.append({"run_number": n, "pid_label": record["pid"], "request_cursor": record["request_cursor"],
                              "page_cids": expected_pages, "next_cursor": record["next_cursor"], "complete": terminal,
                              "recorded_seconds": record["recorded_seconds"], "process_origin": "unattested"})
    require(fresh["pages_created"] == page_ids[2:] and fresh["pids"] == pids, "complete historical process population")
    resume = bundle["resume"]
    closed(resume, RESUME_FIELDS, "complete native resume record")
    require(resume["schema"] == "inventory-resume-fresh-process@2" and resume["qualified"] is True
            and resume["complete"] is True and resume["root_cid"] == root_cid and resume["completion_cid"] == completion_cid
            and equal(resume["coverage"], whole) and resume["pages_created"] == page_ids[2:] and resume["pids"] == pids
            and equal(resume["process_runs"], retained_chunks), "independent complete resume aggregation")
    for name in ("numerical_before", "numerical_after"):
        numeric_state(resume[name], root["model"])
    integer(resume["post_setup_fit_attempt_count"], 0, 0, "aggregate new fitting")
    integer(resume["pid"], pids[-1], pids[-1], "aggregate terminal process label")
    integer(resume["registry_owner_generation_before"], 3, 3, "aggregate first reopened owner")
    integer(resume["registry_owner_generation_after"], 6, 6, "aggregate last reopened owner")
    require(resume["source_model_owner_preservation"] is True and resume["version_id"] == root["model"]["version_id"]
            and equal(resume["final_resources"], {"active_lease_count": 0, "waiting_request_count": 0})
            and type(resume["recorded_seconds"]) is float and 0 <= resume["recorded_seconds"] <= 1680,
            "recorded aggregate resource/state/time labels")
    require(equal(scan["fresh_process_resume"], resume), "failed scan retains complete historical chunks")
    for field in ("scan_reuse", "source_scan_seed"):
        reuse = composed[field]
        require(reuse["qualified"] is False and reuse["fresh_native_validation_required"] is True
                and reuse["root_cid"] == root_cid and reuse["completion_cid"] == completion_cid
                and equal(reuse["head"], root["head"]) and equal(reuse["coverage"], whole)
                and reuse["selected_version_id"] == root["model"]["version_id"], "historical reuse isn't qualification")
        for key in ("new_fitting_epochs", "new_registry_reopens", "new_scan_pages"):
            integer(reuse[key], 0, 0, "composed no new " + key)
        integer(reuse["inherited_actual_setup_epochs"], 2, 2, "composed inherited setup epochs")
        require(reuse["unknown_fitting_epochs"] is False and reuse["source_audit"]["sha256"] == AUDIT_SHA256
                and type(reuse["source_audit"]["bytes"]) is int and reuse["source_audit"]["bytes"] == AUDIT_BYTES,
                "fixed source audit / known setup ledger")
        historical = reuse["source_scan_summary"]
        require(historical["overall_native_qualification"] is False and historical["native_worker_qualified"] is False
                and historical["historical_execution_only"] is True and historical["root_cid"] == root_cid
                and historical["completion_cid"] == completion_cid and historical["membership_cid"] == root["membership_cid"]
                and equal(historical["fresh_process_resume"], fresh), "composed reuse preserves failed-attempt history")
    integer(composed["scan_reuse"]["copied_cas_objects"], 14, 14, "retained reused CAS population")
    integer(composed["scan_reuse"]["copied_cas_bytes"], 816613, 816613, "retained reused CAS bytes")
    require(equal(composed["scan_coverage"], whole) and equal(composed["numerical_before"], numerical)
            and equal(composed["numerical_after"], numerical), "composed unchanged recorded model metadata")
    members = [{"member_index": n, "path": member["path"], "source_key": member["source_key"],
                "entry_cid": member["entry_cid"], "source_cid": member["source_cid"],
                "ast_cid": member["ast_cid"], "disposition": entry["disposition"],
                "reason": entry["reason"], "source_digest": entry["source_digest"],
                "target_sha256": entry["target_sha256"], "runtime_behavior": "unknown"}
               for n, (member, entry) in enumerate(zip(root["members"], [e for p in pages for e in p["entries"]], strict=True))]
    return {"root_cid": root_cid, "completion_cid": completion_cid, "membership_cid": root["membership_cid"],
            "head_cid": root["head_cid"], "model_artifact_cid": root["model"]["artifact_cid"],
            "inventory_member_count": 300, "page_count": 10, "historical_resumption_count": 4,
            "inferred_member_count": 205, "deferred_member_count": 89, "unsupported_member_count": 6,
            "new_scan_page_count": 0, "new_fitting_epoch_count": 0, "inherited_setup_epoch_count": 2,
            "historical_scan_overall_qualified": False, "composed_worker_overall_qualified": True,
            "coverage": whole, "source_members": members, "ordered_pages": summaries, "historical_chunks": chunk_details,
            "frontiers": [frontier(root, pages[:count], done if count == 10 else None)
                          for count in (0, 1, 2, 4, 6, 8, 10)],
            "numerical_worker_request_custody": "raw_input_output_unavailable",
            "recorded_numerical_state": numerical,
            "historical_scan_failure": {"error": scan["error"], "error_type": scan["error_type"]}}


def decode_packets(raw):
    return {"audit": document(raw["historical_scan_audit"]), "scan_result": document(raw["historical_scan_result"]),
            "composed_result": document(raw["composed_worker_result"]),
            "transport": {role: document(raw["transport_" + role]) for role in ROLES},
            "chunks": [{"record": document(raw[f"chunk_{n}_record"]), "stdout": raw[f"chunk_{n}_stdout"],
                        "stderr": raw[f"chunk_{n}_stderr"]} for n in range(1, 5)], "resume": document(raw["resume_record"])}


def corruption_controls(bundle):
    """Correlated mutations repair container IDs; the independent anchor stays fixed."""
    results = []

    def check(name, change):
        changed = copy.deepcopy(bundle)
        change(changed)
        try:
            reconcile(changed)
        except (Refusal, KeyError, IndexError, TypeError) as error:
            results.append({"name": name, "refused": True, "reason": str(error)})
        else:
            raise Refusal("corruption control accepted: " + name)

    def page(name="page-01"):
        return lambda b: b["transport"][name]

    check("duplicate_source_member", lambda b: b["transport"]["root"]["members"].__setitem__(1, copy.deepcopy(b["transport"]["root"]["members"][0])))
    check("bool_member_index", lambda b: page()(b)["entries"][0].update(member_index=False))
    check("wrong_page_predecessor", lambda b: page("page-03")(b).update(previous_page_cid=page()(b)["root_cid"]))
    check("reordered_disposition", lambda b: page()(b)["entries"].reverse())
    check("partial_false_completion", lambda b: b["transport"]["completion"]["pages"].pop())
    check("bool_page_offset", lambda b: page()(b).update(start=False))
    check("bool_worker_returncode", lambda b: page()(b)["worker_receipt"].update(returncode=False))
    check("inference_source_substitution", lambda b: page()(b)["inference"]["rows"][0].update(source_digest="0" * 64))
    check("inferred_projection_width", lambda b: page()(b)["inference"]["rows"][0]["latent"].pop())
    check("unattested_numerical_promotion", lambda b: page()(b)["inference"].update(qualified=True))
    check("unindexed_fabricated_inference", lambda b: page()(b)["entries"][0].update(disposition="inferred", inference_index=0))
    check("deferred_fabricated_fact", lambda b: page()(b)["entries"][-1].update(reason=None))
    check("stale_chunk_root", lambda b: b["chunks"][0]["record"]["request_cursor"].update(root_cid=b["transport"]["completion"]["head_cid"]))
    check("chunk_false_terminal", lambda b: b["chunks"][0]["record"].update(complete=True))
    check("chunk_skipped_page", lambda b: b["chunks"][1]["record"]["pages_created"].pop())
    check("chunk_duplicate_pid", lambda b: b["chunks"][1]["record"].update(pid=b["chunks"][0]["record"]["pid"]))
    check("false_scan09_whole_success", lambda b: b["scan_result"].update(qualified=True))
    check("composed_new_fit", lambda b: b["composed_result"]["scan_reuse"].update(new_fitting_epochs=1))
    check("composed_new_scan", lambda b: b["composed_result"]["source_scan_seed"].update(new_scan_pages=1))
    check("composed_history_reclassified", lambda b: b["composed_result"]["scan_reuse"]["source_scan_summary"].update(overall_native_qualification=True))
    check("raw_worker_request_invented", lambda b: b["audit"]["scan"].update(raw_worker_input_output_not_retained=False))
    check("reference_root_reclassified", lambda b: b["transport"]["optout-root"].update(optimized=True))

    def repaired_page(b):
        item = b["transport"]["page-01"]
        item["inference"]["rows"][0]["latent"][0] += 0.125
        item["worker_receipt"]["output_sha256"] = "1" * 64
        # Repair all local page-chain and completion references. The raw audit
        # still names the original bytes and original numerical-worker receipt.
        previous = None
        for n in range(1, 11):
            p = b["transport"][f"page-{n:02d}"]
            p["previous_page_cid"] = previous
            previous = cid_raw(wire(p))
            b["transport"]["completion"]["pages"][n - 1]["page_cid"] = previous
        b["scan_result"]["completed_scan_cid"] = cid(b["transport"]["completion"])

    check("rehashed_numerical_page_against_fixed_audit", repaired_page)
    for name in ("proof_authority", "source_semantics_verified", "authoritative_cache_eligible"):
        check("native_authority_" + name, lambda b, name=name: b["transport"]["root"]["authority"].update({name: True}))
    return results


def population(root, expected, originals=None):
    """Check the canonical root and exact population, then fresh final body bytes."""
    canonical_path(root)
    require(stat.S_ISDIR(root.stat(follow_symlinks=False).st_mode), "output root type")
    files, directories = {}, set()
    pending = [root]
    while pending:
        path = pending.pop()
        with os.scandir(path) as entries:
            for row in entries:
                p = Path(row.path)
                require(not row.is_symlink(), "output contains symlink")
                if row.is_dir(follow_symlinks=False):
                    directories.add(p.relative_to(root).as_posix())
                    require(len(directories) <= 1, "unexpected output directory")
                    pending.append(p)
                else:
                    require(row.is_file(follow_symlinks=False), "output nonregular file")
                    files[p.relative_to(root).as_posix()] = p
                    require(len(files) <= 32, "unexpected output population")
    require(set(files) == set(expected) and directories == {"inputs"}, "exact output file/directory population")
    for name, raw in expected.items():
        require(Capture.read(files[name], len(raw)) == raw, "late retained/report byte drift")
    for path, raw in (originals or {}).items():
        require(Capture.read(path, len(raw)) == raw, "late original byte drift")
    canonical_path(root)
    # Repeat the exact population after original rereads. These sequential
    # fences detect deterministic late drift; they do not claim atomic custody.
    require(stat.S_ISDIR(root.stat(follow_symlinks=False).st_mode), "late output root type")
    final_files, final_dirs, pending = set(), set(), [root]
    while pending:
        with os.scandir(pending.pop()) as entries:
            for row in entries:
                p = Path(row.path)
                require(not row.is_symlink(), "late output contains symlink")
                if row.is_dir(follow_symlinks=False):
                    final_dirs.add(p.relative_to(root).as_posix())
                    require(len(final_dirs) <= 1, "late extra output directory")
                    pending.append(p)
                else:
                    require(row.is_file(follow_symlinks=False), "late output nonregular file")
                    final_files.add(p.relative_to(root).as_posix())
                    require(len(final_files) <= 32, "late extra output file")
    require(final_files == set(expected) and final_dirs == {"inputs"}, "late exact output population")
    canonical_path(root)


def run(manifest_path, output_path):
    manifest_path = canonical_path(manifest_path)
    capture = Capture()
    manifest_raw = capture.take(manifest_path, limit=MAX_MANIFEST)
    manifest = document(manifest_raw, MAX_MANIFEST)
    rows = manifest_rows(manifest)
    output = canonical_path(output_path, existing=False)
    protected = {manifest_path.parent, *(Path(pin["path"]).parent for _, pin in rows)}
    require(not output.exists() and all(output != path and output not in path.parents and path not in output.parents
                                        for path in protected), "fresh output outside input scopes")
    raw = {role: capture.take(Path(pin["path"]), pin) for role, pin in rows}
    bundle = decode_packets(raw)
    summary = reconcile(bundle)
    controls = corruption_controls(bundle)
    capture.stable()
    originals = dict(capture.raw)
    (output / "inputs").mkdir(parents=True)
    expected, inputs = {}, []
    for role, pin in rows:
        target = output / "inputs" / (role + ".body")
        with target.open("xb") as stream:
            stream.write(raw[role])
        capture.take(target, pin)
        expected[target.relative_to(output).as_posix()] = raw[role]
        inputs.append({"role": role, "path": pin["path"], "sha256": pin["sha256"], "size_bytes": pin["size_bytes"],
                       "retained_path": str(target)})
    target = output / "inputs" / "manifest.body"
    with target.open("xb") as stream:
        stream.write(manifest_raw)
    capture.take(target, limit=MAX_MANIFEST)
    expected["inputs/manifest.body"] = manifest_raw
    report = {"schema": REPORT_SCHEMA, "status": "passed", "fixture_origin": ORIGIN,
              "interpretation_scope": "historical_structural_receiving_only_no_native_adoption",
              "manifest_sha256": sha(manifest_raw), "historical_scan_audit_sha256": sha(raw["historical_scan_audit"]),
              "historical_scan_result_sha256": sha(raw["historical_scan_result"]),
              "composed_worker_result_sha256": sha(raw["composed_worker_result"]),
              **{name: True for name in TRUE_FLAGS}, **{name: False for name in FALSE_FLAGS},
              **{name: 0 for name in ZERO_FIELDS}, "authority_ceiling": dict.fromkeys(sorted(AUTHORITY), False),
              **summary, "controls": controls, "control_count": len(controls), "input_files": inputs,
              "limitations": ["The fixed raw independent audit selects historical bytes; hashes are not authentication.",
                              "Numerical worker stdin/stdout, source preimages, owner databases, keys and model bodies are not consumed.",
                              "Recorded whole scan09 failure stays separate from composed14 success; neither is executed by this reader.",
                              "Chunk PID/timing/limit/state labels remain recorded observations; process origin and enforcement are unauthenticated.",
                              "Every source disposition remains available; inference deferral and partial frontiers never establish facts or omission.",
                              "Input preservation covers private frozen packets; historical live files were checked only during acquisition.",
                              "Observations are sequential and do not claim atomic filesystem custody or current deployment authority."]}
    report_raw = (json.dumps(report, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")
    require(len(report_raw) <= MAX_REPORT, "report byte budget")
    report_path = output / "resumed_inventory_controls.json"
    with report_path.open("xb") as stream:
        stream.write(report_raw)
    capture.take(report_path, limit=MAX_REPORT)
    expected[report_path.name] = report_raw
    capture.stable()
    population(output, expected, originals)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        report = run(args.manifest, args.output)
    except (Refusal, OSError, KeyError, IndexError, TypeError, RecursionError, UnicodeError) as error:
        print("refused: " + str(error), file=sys.stderr)
        return 2
    print(json.dumps({"status": report["status"], "inventory_member_count": report["inventory_member_count"],
                      "page_count": report["page_count"], "historical_resumption_count": report["historical_resumption_count"],
                      "control_count": report["control_count"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
