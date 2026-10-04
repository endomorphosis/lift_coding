"""Receive selected native inventory exports without opening their owners.

This is a bounded reconciliation of retained public records. It does not run the
catalog, compiler, model, checker, planner, or signature verifier. The fixed raw
primary-audit anchor identifies this particular export; it is not authentication.
"""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path

if __package__:
    from .receiver import Capture as OriginalCapture
    from .receiver import ReceiverRefusal, canonical_path, closed, digest, integer, require
else:
    from receiver import Capture as OriginalCapture
    from receiver import ReceiverRefusal, canonical_path, closed, digest, integer, require

INPUT_SCHEMA = "codebase-ir-native-inventory-query-input@1"
REPORT_SCHEMA = "codebase-ir-native-inventory-query-receiving-report@1"
AUDIT_SHA256 = "46f73d7b64af1e320655cbb0f26ccc3b7cf1f08d9d0b0d2396b5f1c554a40fba"
AUDIT_BYTES = 263983
MAX_FILE = 2 * 1024 * 1024
MAX_MANIFEST = 256 * 1024
MAX_TOTAL = 16 * 1024 * 1024
MAX_FILES = 64
JOINS = ("complete", "partial", "empty-budget", "deferred", "exact-key")
PREVIEWS = ("complete", "partial", "empty-budget")
NATIVE_NAMES = tuple(f"{name}-join.json" for name in JOINS) + tuple(
    f"{name}-plan-preview.json" for name in PREVIEWS) + (
    "independent-authored-plan-preview.json",) + tuple(
    f"native-{index:02d}-{role}.json" for index in range(5)
    for role in ("verification", "applicability"))
PROTOCOL_NAMES = (
    "ipfs_datasets_py.logic.software_contracts.codebase_inventory_scan",
    "ipfs_datasets_py.logic.software_contracts.content",
    "ipfs_datasets_py.logic.software_contracts.codebase_inventory_evidence",
    "ipfs_datasets_py.duckdb_control.codebase_verification_queries",
    "ipfs_datasets_py.logic.software_contracts.codebase_applicability",
    "ipfs_accelerate_py.agent_supervisor.planning.codebase_inventory_evidence_context",
)
FALSE_FLAGS = (
    "native_execution_performed", "training_executed", "current_authority_claimed",
    "owner_database_opened", "profile_keys_read", "signature_authentication_performed",
    "numerical_state_replayed", "source_execution_replayed", "checker_executions_replayed",
    "live_eligibility_qualified", "production_acceptance_qualified",
    "native_export_adoption_qualified",
)
JOIN_FALSE = {
    "source_semantics_verified", "runtime_behavior_verified", "proof_authority",
    "execution_authority", "completion_authority", "mutation_authority",
    "admission_authority", "authoritative_cache_eligible", "behavioral_satisfaction",
    "training_executed", "decoded_formulas_generated", "repository_code_executed",
    "source_execution_attested", "scan_execution_attested",
}
EVIDENCE_FALSE = {
    "kernel_checked", "source_runtime_semantics_verified", "behavioral_satisfaction",
    "authoritative_cache_eligible", "admission_authority", "completion_authority",
}
KEY_FIELDS = {
    "assumptions", "authority_ceiling", "bounds", "checker", "environment",
    "evidence_kind", "expression", "formalization", "interface", "network_policy",
    "obligation", "policy", "provider", "schema", "schema_version", "slice",
    "source", "source_cid", "translation",
}
SEMANTIC_FIELDS = ("intent", "producers", "task_candidates", "frozen_goal", "predicates", "current_facts")
REQUIREMENTS = [f"goal:runtime:source{index:02d}.py" for index in range(4)]
TASKS = [f"task:source{index:02d}.py" for index in range(4)]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("ascii")


def equal(left, right):
    return wire(left) == wire(right)


def document(raw, limit=MAX_FILE):
    require(type(raw) is bytes and len(raw) <= limit, "JSON byte bound")

    def pairs(rows):
        value = {}
        for key, child in rows:
            require(key not in value, "duplicate JSON key")
            value[key] = child
        return value

    def bad_constant(_):
        raise ReceiverRefusal("nonfinite JSON number")

    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=bad_constant)
    except ReceiverRefusal:
        raise
    except (ValueError, UnicodeError, RecursionError) as error:
        raise ReceiverRefusal("invalid JSON") from error
    pending, nodes = [(value, 0)], 0
    while pending:
        item, depth = pending.pop()
        nodes += 1
        require(depth <= 64 and nodes <= 200000, "JSON structure bound")
        if type(item) is dict:
            pending.extend((key, depth + 1) for key in item)
            pending.extend((child, depth + 1) for child in item.values())
        elif type(item) is list:
            pending.extend((child, depth + 1) for child in item)
        elif type(item) is str:
            try:
                item.encode("utf-8")
            except UnicodeError as error:
                raise ReceiverRefusal("JSON contains a surrogate") from error
        elif type(item) is float:
            require(math.isfinite(item), "nonfinite JSON float")
        elif type(item) is int:
            require(abs(item) <= 2**63 - 1, "JSON integer magnitude bound")
    require(type(value) is dict, "JSON object required")
    return value


def cid_bytes(raw):
    return "b" + base64.b32encode(b"\x01\x55\x12\x20" + hashlib.sha256(raw).digest()).decode().lower().rstrip("=")


def cid(value):
    # Native dag-json has no floating-point values; the scan/join use raw CIDs.
    pending = [value]
    while pending:
        item = pending.pop()
        require(type(item) in (dict, list, str, bool, int, type(None)), "dag-json contains an unsupported value")
        if type(item) is dict:
            require(all(type(key) is str for key in item), "dag-json string keys required")
            pending.extend(item.values())
        elif type(item) is list:
            pending.extend(item)
        elif type(item) is str:
            try:
                item.encode("utf-8")
            except UnicodeError as error:
                raise ReceiverRefusal("dag-json contains a surrogate") from error
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                     allow_nan=False).encode("utf-8")
    return "b" + base64.b32encode(b"\x01\xa9\x02\x12\x20" + hashlib.sha256(raw).digest()).decode().lower().rstrip("=")


def cid_shape(value, raw=False):
    require(type(value) is str and value.startswith("b") and "=" not in value, "canonical native CID required")
    try:
        body = base64.b32decode(value[1:].upper() + "=" * ((1 - len(value)) % 8))
    except ValueError as error:
        raise ReceiverRefusal("invalid CID") from error
    prefix = b"\x01\x55\x12\x20" if raw else b"\x01\xa9\x02\x12\x20"
    require(body.startswith(prefix) and len(body) == len(prefix) + 32
            and "b" + base64.b32encode(body).decode().lower().rstrip("=") == value, "CID codec or canonical spelling differs")


def false_authority(value, fields):
    closed(value, fields, "authority")
    require(all(item is False for item in value.values()), "authority elevation or mistyped false")


def native_key(value):
    closed(value, KEY_FIELDS, "canonical proof key")
    require(value["interface"] == "CanonicalProofCacheKey@1"
            and value["schema_version"] == "canonical-proof-cache-key/v1", "canonical key profile")
    require(all(type(item) is str and item for key, item in value.items() if key != "source_cid")
            and (value["source_cid"] is None or type(value["source_cid"]) is str), "canonical key field types")
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return "canonical-proof-cache-key:sha256:" + sha(raw)


class Capture:
    """Bound every descriptor read by both the declared pin and remaining budget."""
    def __init__(self):
        self.raw = {}
        self.total = 0

    def take(self, path, pin=None, limit=MAX_FILE):
        require(path not in self.raw and len(self.raw) < MAX_FILES, "duplicate input or file population bound")
        allowance = min(limit, MAX_TOTAL - self.total, pin["bytes"] if pin else limit)
        raw = OriginalCapture.read(path, allowance)
        require(len(raw) <= allowance and self.total + len(raw) <= MAX_TOTAL, "aggregate capture byte bound")
        if pin:
            require(len(raw) == pin["bytes"] and sha(raw) == pin["sha256"], "selected raw input pin mismatch")
        self.raw[path] = raw
        self.total += len(raw)
        return raw

    def stable(self):
        for path, raw in self.raw.items():
            require(OriginalCapture.read(path, len(raw)) == raw, "input changed after capture")


def descriptor(value, named=False, original=False):
    fields = {"path", "sha256", "bytes"}
    if named:
        fields.add("name")
    if original:
        fields.add("original_path")
    closed(value, fields, "selected descriptor")
    canonical_path(value["path"])
    if original:
        canonical_path(value["original_path"])
    digest(value["sha256"], "selected raw pin")
    integer(value["bytes"], 0, MAX_FILE, "selected file bytes")
    if named:
        require(type(value["name"]) is str, "selected role name")


def implementation(value, protocol_pins):
    closed(value, {"files", "sha256", "scope"}, "implementation metadata")
    require(type(value["files"]) is dict and value["scope"] == "listed_local_files_only_not_execution_attestation",
            "producer pin scope")
    require(sha(wire(value["files"])) == value["sha256"], "producer pin aggregate")
    for name, pin in value["files"].items():
        digest(pin, "producer module pin")
        if name in protocol_pins:
            require(pin == protocol_pins[name], "selected inert producer pin differs")


def scan_record(scan, head, protocol_pins):
    closed(scan, {"artifact_cid", "record"}, "scan envelope")
    body = scan["record"]
    closed(body, {"authority", "codec", "counters", "entries", "head", "implementation", "limits", "membership",
                  "model", "profile", "schema", "shards", "timings", "worker_receipt"}, "scan record")
    require(body["schema"] == "codebase-inventory-feature-scan@1"
            and body["profile"] == "source_bound_inventory_scan_v1"
            and body["codec"] == "canonical-finite-native-json/raw-cidv1", "native scan codec")
    require(cid_bytes(wire(body)) == scan["artifact_cid"] and equal(body["head"], head), "scan CID or head differs")
    require(type(body["authority"]) is dict and all(flag is False for flag in body["authority"].values()), "scan authority")
    implementation(body["implementation"], protocol_pins)
    rows = body["entries"]
    require(type(rows) is list and 1 <= len(rows) <= 256, "bounded scan membership")
    require(type(body["limits"]) is dict, "scan limits")
    integer(body["limits"]["max_rows_per_shard"], 1, 256, "shard row limit")
    require(len(rows) <= body["limits"]["max_entries"], "scan member limit")
    ordered, previous, entry_ids, inferred = [], None, set(), []
    for row in rows:
        closed(row, {"path", "source_key", "raw_path_hex", "source_size_bytes", "source_sha256", "captured_source_available",
                     "entry_cid", "source_cid", "ast_cid", "parse_status", "disposition", "frontiers", "cohort_membership",
                     "authored_contracts_origin", "target_sha256", "source_digest", "coverage", "shard_index", "inference"}, "scan member")
        raw_path = row["raw_path_hex"]
        require(type(raw_path) is str and 0 < len(raw_path) <= 8192, "bounded raw path")
        try:
            path_bytes = bytes.fromhex(raw_path)
        except ValueError as error:
            raise ReceiverRefusal("invalid raw path hex") from error
        require(path_bytes.hex() == raw_path and row["source_key"] == "raw:" + raw_path
                and (previous is None or raw_path > previous), "ordered unique raw membership")
        require(row["path"] == path_bytes.decode("utf-8", "backslashreplace"), "captured path display")
        previous = raw_path
        cid_shape(row["entry_cid"])
        require(row["entry_cid"] not in entry_ids, "duplicate entry identity")
        entry_ids.add(row["entry_cid"])
        ordered.append({"source_key": row["source_key"], "entry_cid": row["entry_cid"]})
        require(type(row["captured_source_available"]) is bool
                and row["captured_source_available"] == (row["source_sha256"] is not None), "source availability flag")
        if row["source_sha256"] is not None:
            digest(row["source_sha256"], "source pin")
            cid_shape(row["source_cid"], raw=True)
            require(_cid_digest(row["source_cid"]) == row["source_sha256"], "source digest/CID differs")
        require(row["disposition"] in {"inferred", "deferred_budget", "opaque", "parse_failed", "unindexed", "unsupported_target"}, "scan disposition")
        if row["disposition"] == "inferred":
            integer(row["shard_index"], 0, 15, "shard index")
            inf = row["inference"]
            closed(inf, {"source_digest", "latent", "reconstructed_projection_features"}, "inference observation")
            require(inf["source_digest"] == row["source_digest"] and type(inf["latent"]) is list
                    and 1 <= len(inf["latent"]) <= 4096 and type(inf["reconstructed_projection_features"]) is dict, "inference layout")
            numbers = list(inf["latent"])
            for values in inf["reconstructed_projection_features"].values():
                require(type(values) is list and len(values) <= 1024, "feature width bound")
                numbers.extend(values)
            require(all(type(number) in (int, float) and abs(number) <= sys.float_info.max for number in numbers), "finite inference observation")
            inferred.append(row)
        else:
            require(row["inference"] is None and row["shard_index"] is None, "deferred/opaque member carries inference")
    require(equal(body["membership"], {"ordered": ordered, "cid": cid(ordered)}), "membership CID or ordered ledger differs")
    require(type(body["shards"]) is list and len(body["shards"]) <= 16, "bounded shards")
    flattened = []
    for index, shard in enumerate(body["shards"]):
        closed(shard, {"shard_index", "row_count", "target_source_digests", "inference_sha256"}, "shard receipt")
        require(type(shard["shard_index"]) is int and shard["shard_index"] == index, "shard order")
        group = [row for row in inferred if row["shard_index"] == index]
        integer(shard["row_count"], 1, body["limits"]["max_rows_per_shard"], "shard population")
        require(shard["row_count"] == len(group) and shard["target_source_digests"] == [row["source_digest"] for row in group], "shard source order")
        digest(shard["inference_sha256"], "retained inference pin")
        flattened.extend(group)
    require(equal(flattened, inferred), "inference shard assignment/order")
    counters = body["counters"]
    require(type(counters["inventory_entries"]) is int and counters["inventory_entries"] == len(rows)
            and type(counters["inferred_rows"]) is int and counters["inferred_rows"] == len(inferred)
            and equal(counters["dispositions"], dict(Counter(row["disposition"] for row in rows))), "scan counters differ")
    return rows


def _cid_digest(value):
    return base64.b32decode(value[1:].upper() + "=" * ((1 - len(value)) % 8))[-32:].hex()


def proof_inventory(native):
    proofs, apps = {}, {}
    for index in range(5):
        proof = native[f"native-{index:02d}-verification.json"]
        app = native[f"native-{index:02d}-applicability.json"]
        closed(proof, {"authority", "canonical_keys", "coverage", "effective_bounds", "environment", "execution_stage", "fence", "limits",
                       "pipeline", "pipeline_result", "post_contract_program", "process_observations", "profile", "requested_bounds",
                       "requested_contracts", "schema", "solver_artifacts", "source_binding"}, "independent verification record")
        closed(app, {"authority", "canonical_keys", "checks", "conditional_proved", "conditional_refuted", "contract_results", "effective_bounds",
                     "environment", "fence", "limits", "model_applicability_established", "process_observations", "profile", "requested_bounds",
                     "requested_domains", "schema", "source_binding", "status", "verification_cid"}, "independent applicability record")
        require(proof["schema"] == "codebase-conditional-verification@2"
                and app["schema"] == "codebase-input-applicability@2", "native proof/applicability schema")
        proof_cid, app_cid = cid(proof), cid(app)
        require(proof_cid not in proofs and app_cid not in apps, "duplicate proof or domain record")
        require(app["verification_cid"] == proof_cid and equal(app["source_binding"], proof["source_binding"]), "independent linked applicability binding")
        for record in (proof, app):
            require(record["authority"].get("conditional_model_evidence") is True, "historical conditional evidence marker")
            require(all(flag is False for name, flag in record["authority"].items()
                        if name not in {"conditional_model_evidence", "typed_model_evidence_only"}), "historical record authority ceiling")
            require(type(record["canonical_keys"]) is list and 1 <= len(record["canonical_keys"]) <= 128, "native key population")
            for key in record["canonical_keys"]:
                native_key(key)
        proofs[proof_cid], apps[app_cid] = proof, app
    return proofs, apps


def summary_record(item, head, selector, rows, proofs, apps):
    closed(item, {"query_entry", "source_binding", "contract", "dependencies", "verification_status", "applicability_status",
                  "applicability_summary", "historical_records_observed_live", "authority"}, "conditional summary")
    false_authority(item["authority"], EVIDENCE_FALSE)
    require(item["historical_records_observed_live"] is False, "historical record cannot become live")
    binding, contract, query_row = item["source_binding"], item["contract"], item["query_entry"]
    closed(binding, {"head", "path", "entry", "content_sha256", "ast_cid", "source_revision"}, "source binding")
    entry = binding["entry"]
    require(equal(binding["head"], head) and binding["source_revision"] == "snapshot:" + head["snapshot_cid"], "summary head/source revision")
    key = "raw:" + entry["raw_path_hex"]
    require(key in rows, "summary source missing from inventory")
    row = rows[key]
    for name, other in (("path", "path"), ("raw_path_hex", "raw_path_hex"), ("entry_cid", "entry_cid"),
                        ("source_cid", "source_cid"), ("source_size_bytes", "size_bytes")):
        require(equal(row[name], entry[other]), "summary source membership differs")
    require(binding["path"] == row["path"] and binding["content_sha256"] == row["source_sha256"]
            and binding["ast_cid"] == row["ast_cid"], "summary source/AST digest differs")
    require(cid({name: value for name, value in entry.items() if name != "entry_cid"}) == entry["entry_cid"], "snapshot entry identity")
    closed(contract, {"contract_id", "requested_contract", "contract_cid", "lowered_contract_cid", "domain_id", "domain_cid",
                      "canonical_keys", "applicability_keys"}, "conditional contract")
    require(cid(contract["requested_contract"]) == contract["contract_cid"] and contract["requested_contract"]["contract_id"] == contract["contract_id"], "requested contract CID")
    closed(query_row, {"entry_id", "contract_id", "projection_cid", "verification_cid", "applicability_cid", "path", "contract_cid",
                       "domain_id", "domain_cid", "canonical_key_ids"}, "query row")
    require(query_row["entry_id"] == cid({"projection_cid": query_row["projection_cid"], "contract_id": query_row["contract_id"]}), "query row CID")
    for field in ("contract_id", "contract_cid", "domain_id", "domain_cid"):
        require(query_row[field] == contract[field], "query contract/domain identity")
    require(query_row["path"] == binding["path"], "query source path")
    require(query_row["verification_cid"] in proofs and query_row["applicability_cid"] in apps, "summary lacks independent proof/domain body")
    proof, app = proofs[query_row["verification_cid"]], apps[query_row["applicability_cid"]]
    require(equal(proof["source_binding"], binding) and equal(app["source_binding"], binding)
            and app["verification_cid"] == query_row["verification_cid"], "independent proof source binding differs")
    require([request for request in proof["requested_contracts"] if request["contract_id"] == contract["contract_id"]]
            == [contract["requested_contract"]], "independent requested contract differs")
    identities = []
    for field, original in (("canonical_keys", proof), ("applicability_keys", app)):
        wrappers = contract[field]
        require(type(wrappers) is list and len(wrappers) == len(original["canonical_keys"]), "complete native key membership")
        expected = {native_key(key): key for key in original["canonical_keys"]}
        seen = set()
        for wrapper in wrappers:
            closed(wrapper, {"key_id", "key", "obligation_id"} | ({"kind"} if field == "applicability_keys" else set()), "key wrapper")
            identity = native_key(wrapper["key"])
            require(identity == wrapper["key_id"] and identity in expected and identity not in seen
                    and equal(expected[identity], wrapper["key"]), "independent canonical key differs")
            seen.add(identity)
            identities.append(identity)
    require(query_row["canonical_key_ids"] == sorted(set(identities)), "query canonical key inventory")
    for selector_name, row_name in (("path", "path"), ("contract_id", "contract_id"), ("expected_contract_cid", "contract_cid"),
                                    ("verification_cid", "verification_cid"), ("requested_domain_id", "domain_id"), ("requested_domain_cid", "domain_cid")):
        require(selector[selector_name] is None or selector[selector_name] == query_row[row_name], "exact selector binding")
    require(selector["canonical_key_id"] is None or selector["canonical_key_id"] in identities, "exact canonical key selector")
    solved = [obligation for obligation in proof["pipeline_result"]["obligation_results"]
              if obligation["vc_obligation"]["parent_contract_id"] == contract["contract_id"]]
    verdict = ("recorded_conditional_refuted" if any(row["verdict_classification"] == "agree_disproved" for row in solved)
               else "recorded_conditional_proved" if solved and all(row["verdict_classification"] == "agree_proved" for row in solved)
               and proof["pipeline_result"]["status"] == "success" else "unknown")
    require(item["verification_status"] == verdict, "recorded conditional verdict differs from independent proof")
    selected = [row for row in app["contract_results"] if row["parent_contract_id"] == contract["contract_id"]]
    require(len(selected) == 1 and equal(selected[0], item["applicability_summary"])
            and item["applicability_status"] == selected[0]["status"], "domain summary differs from independent applicability record")
    app_row = selected[0]
    require(app_row["contract_cid"] == contract["lowered_contract_cid"] and app_row["domain_cid"] == contract["domain_cid"]
            and app_row["domain_id"] == contract["domain_id"], "domain/lowered contract binding")
    require(any(domain["domain_id"] == contract["domain_id"] and cid(domain) == contract["domain_cid"] for domain in app["requested_domains"]), "requested domain CID")
    deps = item["dependencies"]
    for name, expected in (("head_cid", cid(head)), ("snapshot_cid", head["snapshot_cid"]), ("manifest_cid", head["manifest_cid"]),
                           ("ast_revision_id", head["ast_revision_id"]), ("source_cid", entry["source_cid"]),
                           ("content_sha256", binding["content_sha256"]), ("ast_cid", binding["ast_cid"]),
                           ("source_revision", binding["source_revision"]), ("verification_cid", query_row["verification_cid"]),
                           ("applicability_cid", query_row["applicability_cid"])):
        require(deps.get(name) == expected, "conditional dependency binding")


def query_record(query, selector, head, limits, evidence):
    closed(query, {"selector_cid", "inventory_cid", "epoch", "pages", "complete", "next_cursor", "closing_page_cid"}, "query ledger")
    require(query["selector_cid"] == cid(selector) and type(query["complete"]) is bool, "query selector or complete flag")
    cid_shape(query["inventory_cid"])
    cid_shape(query["closing_page_cid"])
    integer(query["epoch"], 1, 2**63 - 1, "query epoch")
    require(type(query["pages"]) is list and len(query["pages"]) <= limits["max_pages"], "page limit")
    start, previous, flattened, seen, terminal = None, None, [], set(), False
    for wrapper in query["pages"]:
        require(not terminal, "page after terminal page")
        closed(wrapper, {"page_size", "page"}, "page wrapper")
        integer(wrapper["page_size"], 1, limits["page_size"], "page size")
        page = wrapper["page"]
        closed(page, {"schema", "selector", "selector_cid", "head", "head_cid", "inventory_cid", "epoch", "entries",
                      "start_cursor", "next_cursor", "complete", "authority", "page_cid"}, "native page")
        require(page["schema"] == "codebase-verification-query-page@1" and equal(page["selector"], selector)
                and page["selector_cid"] == cid(selector) and equal(page["head"], head) and page["head_cid"] == cid(head)
                and page["inventory_cid"] == query["inventory_cid"] and type(page["epoch"]) is int
                and page["epoch"] == query["epoch"] and equal(page["start_cursor"], start), "page head/inventory/epoch/selector/start binding")
        require(type(page["complete"]) is bool and page["complete"] == (page["next_cursor"] is None), "terminal page binding")
        closed(page["authority"], EVIDENCE_FALSE | {"historical_conditional_evidence"}, "page authority")
        require(page["authority"]["historical_conditional_evidence"] is True
                and all(page["authority"][name] is False for name in EVIDENCE_FALSE), "page authority elevation")
        require(page["page_cid"] == cid({name: value for name, value in page.items() if name != "page_cid"})
                and page["page_cid"] not in seen, "page CID or duplicate page")
        seen.add(page["page_cid"])
        require(type(page["entries"]) is list and len(page["entries"]) <= wrapper["page_size"], "bounded page rows")
        for row in page["entries"]:
            require(previous is None or row["entry_id"] > previous, "query row duplicate/order regression")
            previous = row["entry_id"]
            flattened.append(row)
        if page["next_cursor"] is not None:
            cursor = page["next_cursor"]
            closed(cursor, {"schema", "head_cid", "inventory_cid", "epoch", "selector_cid", "after"}, "native cursor")
            require(cursor["schema"] == "codebase-verification-query-cursor@1" and page["entries"]
                    and cursor["head_cid"] == cid(head) and cursor["inventory_cid"] == query["inventory_cid"]
                    and type(cursor["epoch"]) is int and cursor["epoch"] == query["epoch"]
                    and cursor["selector_cid"] == cid(selector) and cursor["after"] == previous, "cursor binding differs")
        start, terminal = page["next_cursor"], page["complete"]
    require(equal(flattened, [row["query_entry"] for row in evidence]), "page rows differ from evidence summaries")
    require(query["complete"] == bool(query["pages"] and terminal) and equal(query["next_cursor"], start), "query complete/resume binding")
    charged = len(wire({"pages": query["pages"], "evidence": evidence})) if query["pages"] or evidence else 0
    require(len(evidence) <= limits["max_evidence_entries"] and charged <= limits["max_query_bytes"], "query aggregate byte/row bound")
    return charged


def member_ledger(rows, evidence, complete):
    matches = {row["source_key"]: [] for row in rows}
    for item in evidence:
        key = "raw:" + item["source_binding"]["entry"]["raw_path_hex"]
        require(key in matches, "evidence is outside source population")
        matches[key].append(item["query_entry"]["entry_id"])
    return [{"source_key": row["source_key"], "entry_cid": row["entry_cid"], "evidence_disposition":
             ("matched_complete" if matches[row["source_key"]] else "no_exact_indexed_conditional_evidence") if complete else
             ("matched_partial" if matches[row["source_key"]] else "unknown_budget"),
             "evidence_entry_ids": sorted(matches[row["source_key"]])} for row in rows]


def receive_join(value, proofs, apps, protocol_pins):
    closed(value, {"authority", "codec", "entries", "evidence", "head", "head_cid", "implementation", "limits", "profile", "query", "scan", "schema", "selector"}, "native join")
    require(value["schema"] == "codebase-inventory-conditional-evidence@1"
            and value["profile"] == "current_inventory_historical_conditional_evidence_v1"
            and value["codec"] == "canonical-finite-native-json/raw-cidv1", "native join codec")
    false_authority(value["authority"], JOIN_FALSE)
    head = value["head"]
    require(value["head_cid"] == cid(head), "join head CID")
    implementation(value["implementation"], protocol_pins)
    selector = value["selector"]
    closed(selector, {"schema", "path", "contract_id", "expected_contract_cid", "requested_domain_id", "requested_domain_cid", "verification_cid", "canonical_key_id", "dependency_kind", "dependency_value"}, "query selector")
    require(selector["schema"] == "codebase-verification-selector@1" and selector["dependency_kind"] is None
            and selector["dependency_value"] is None, "receiving selector scope")
    limits = value["limits"]
    closed(limits, {"max_evidence_entries", "max_output_bytes", "max_pages", "max_query_bytes", "page_size"}, "join limits")
    for name, maximum in (("max_evidence_entries", 256), ("max_pages", 16), ("max_query_bytes", MAX_TOTAL), ("max_output_bytes", 32 * 1024 * 1024), ("page_size", 64)):
        integer(limits[name], 0 if name == "max_query_bytes" else 1, maximum, name)
    require(len(wire(value)) <= min(MAX_FILE, limits["max_output_bytes"]), "join serialized output bound")
    rows = scan_record(value["scan"], head, protocol_pins)
    require(type(value["evidence"]) is list and len(value["evidence"]) <= 256, "summary population")
    row_map = {row["source_key"]: row for row in rows}
    for item in value["evidence"]:
        summary_record(item, head, selector, row_map, proofs, apps)
    charged = query_record(value["query"], selector, head, limits, value["evidence"])
    require(equal(value["entries"], member_ledger(rows, value["evidence"], value["query"]["complete"])), "complete member disposition ledger differs")
    counts = Counter(row["evidence_disposition"] for row in value["entries"])
    source_counts = Counter(row["source_binding"]["path"] for row in value["evidence"])
    return {"artifact_cid": cid_bytes(wire(value)), "inventory_member_count": len(rows),
            "membership_cid": value["scan"]["record"]["membership"]["cid"],
            "query_inventory_cid": value["query"]["inventory_cid"], "query_epoch": value["query"]["epoch"],
            "query_selector_cid": value["query"]["selector_cid"], "next_cursor": value["query"]["next_cursor"],
            "closing_page_cid": value["query"]["closing_page_cid"], "member_ledger": value["entries"],
            "inferred_row_count": sum(row["disposition"] == "inferred" for row in rows),
            "deferred_row_count": sum(row["disposition"] == "deferred_budget" for row in rows),
            "evidence_record_count": len(value["evidence"]), "page_count": len(value["query"]["pages"]),
            "query_bytes_charged": charged, "complete": value["query"]["complete"],
            "matched_member_count": counts["matched_complete"] + counts["matched_partial"],
            "complete_absence_member_count": counts["no_exact_indexed_conditional_evidence"],
            "unknown_member_count": counts["unknown_budget"],
            "ambiguous_members": sorted(path for path, count in source_counts.items() if count > 1),
            "conditional_verdicts": [{"path": row["source_binding"]["path"], "query_entry_id": row["query_entry"]["entry_id"],
                                      "recorded_verification_status": row["verification_status"],
                                      "recorded_applicability_status": row["applicability_status"],
                                      "conditional_proved_for_requested_domain": row["applicability_summary"]["conditional_proved"],
                                      "conditional_refuted_for_requested_domain": row["applicability_summary"]["conditional_refuted"],
                                      "runtime_behavior": "unknown"} for row in value["evidence"]]}


def advisory_refs(join):
    model, query, rows = join["scan"]["record"]["model"], join["query"], join["entries"]
    return {"schema": "codebase-inventory-evidence-advisory-refs@1", "artifact_cid": cid_bytes(wire(join)),
            "head": join["head"], "head_cid": join["head_cid"], "scan_artifact_cid": join["scan"]["artifact_cid"],
            "membership_cid": join["scan"]["record"]["membership"]["cid"],
            "model": {name: model[name] for name in ("version_id", "variant_id", "artifact_cid", "contract_sha256", "state_sha256", "feature_space_sha256")},
            "coverage": {"inventory_entries": len(rows), "inferred_rows": sum(row["disposition"] == "inferred" for row in join["scan"]["record"]["entries"]),
                         "evidence_entries": len(join["evidence"]), "evidence_matched_members": sum(bool(row["evidence_entry_ids"]) for row in rows),
                         "evidence_complete_absent_members": sum(row["evidence_disposition"] == "no_exact_indexed_conditional_evidence" for row in rows),
                         "evidence_unknown_members": sum(row["evidence_disposition"] == "unknown_budget" for row in rows)},
            "query": {"selector_cid": query["selector_cid"], "inventory_cid": query["inventory_cid"], "epoch": query["epoch"],
                      "complete": query["complete"], "next_cursor": query["next_cursor"], "page_cids": [wrapper["page"]["page_cid"] for wrapper in query["pages"]]},
            "entry_evidence": rows, "authority": {name: False for name in JOIN_FALSE}}


def repository_preview(value):
    require(value["schema"] == "supervisor-repository-plan-preview@1", "repository preview schema")
    for name in ("completion_authority", "execution_authority", "production_admitted", "proof_authority", "source_semantics_verified", "worker_launched"):
        require(value[name] is False, "repository preview authority or facts")
    require(type(value["observed_facts_supplied"]) is int and value["observed_facts_supplied"] == 0, "repository preview observed facts")
    require(type(value["model_calls"]) is int and value["model_calls"] == 0, "repository preview model calls")
    require(value["structural_context_cid"] == cid(value["structural_context"]), "preview structural context identity")
    receipt, snapshot = value["preview"], value["input_snapshot"]
    require(receipt["input_snapshot_cid"] == snapshot["snapshot_cid"] and receipt["read_only"] is True
            and receipt["wrote_effects"] == [], "preview receipt snapshot/effects")
    for stage in ("obligation", "candidate"):
        matches = [row for row in receipt["stage_results"] if row["stage"] == stage]
        require(len(matches) == 1 and matches[0]["passed"] is True, "preview declared obligation/candidate stage")


def receive_preview(value, join, baseline, producer_pin):
    closed(value, {"schema", "authority", "codebase_inventory_evidence", "codebase_inventory_evidence_cid", "current_facts", "declared_requirement_ids",
                  "declared_task_ids", "inference_calls", "producer", "removed_task_ids", "repository_preview", "residual_requirements", "result_cid", "training_steps"}, "joined preview")
    require(value["schema"] == "supervisor-codebase-inventory-evidence-plan-preview@1", "joined preview schema")
    require(value["result_cid"] == cid({name: child for name, child in value.items() if name != "result_cid"}), "preview result identity")
    false_authority(value["authority"], JOIN_FALSE | {"omission_authority", "production_admitted", "worker_launched"})
    refs = advisory_refs(join)
    require(equal(value["codebase_inventory_evidence"], refs) and value["codebase_inventory_evidence_cid"] == cid(refs), "preview advisory refs differ from native join")
    require(value["producer"] == {"module": PROTOCOL_NAMES[-1], "sha256": producer_pin}, "preview inert producer pin")
    require(value["current_facts"] == [] and value["removed_task_ids"] == [], "conditional evidence became facts or omitted tasks")
    require(type(value["training_steps"]) is int and value["training_steps"] == 0
            and type(value["inference_calls"]) is int and value["inference_calls"] == 0, "receiving preview execution")
    require(value["declared_requirement_ids"] == REQUIREMENTS and value["declared_task_ids"] == TASKS, "authored requirement/task ledger changed")
    require(equal(value["residual_requirements"], [{"predicate_id": identity, "status": "runtime_behavior_unresolved"} for identity in REQUIREMENTS]), "runtime requirements falsely resolved")
    repository_preview(value["repository_preview"])
    repository_preview(baseline)
    before = baseline["input_snapshot"]["material_binding"]["field_digests"]
    after = value["repository_preview"]["input_snapshot"]["material_binding"]["field_digests"]
    require(all(after.get(name) == before[name] for name in SEMANTIC_FIELDS), "independently authored semantic material changed")
    require(equal(value["repository_preview"]["structural_context"], baseline["structural_context"]), "preview structural context changed")
    require(value["repository_preview"]["input_snapshot"]["snapshot_cid"] != baseline["input_snapshot"]["snapshot_cid"], "advisory receiving input was not separately bound")
    return {"result_cid": value["result_cid"], "advisory_cid": value["codebase_inventory_evidence_cid"],
            "input_snapshot_cid": value["repository_preview"]["input_snapshot"]["snapshot_cid"],
            "runtime_requirement_count": len(REQUIREMENTS), "runtime_task_count": len(TASKS),
            "runtime_fact_count": 0, "tasks_omitted_count": 0,
            "authored_material_fields_preserved": list(SEMANTIC_FIELDS), "runtime_requirement_status": "unresolved"}


def receive_profiles(native, protocol_pins):
    proofs, apps = proof_inventory(native)
    results = {name: receive_join(native[f"{name}-join.json"], proofs, apps, protocol_pins) for name in JOINS}
    complete = native["complete-join.json"]
    for name in JOINS:
        join = native[f"{name}-join.json"]
        require(equal(join["head"], complete["head"]) and equal(join["scan"]["record"]["membership"], complete["scan"]["record"]["membership"])
                and equal(join["scan"]["record"]["model"], complete["scan"]["record"]["model"])
                and join["query"]["inventory_cid"] == complete["query"]["inventory_cid"]
                and type(join["query"]["epoch"]) is int and join["query"]["epoch"] == complete["query"]["epoch"], "cross-profile frozen head/membership/model/evidence inventory")
        if name != "exact-key":
            require(equal(join["selector"], complete["selector"]), "broad profile selector changed")
    require(equal(native["deferred-join.json"]["evidence"], complete["evidence"]), "inference deferral changed independent proof ledger")
    expectations = {"complete": (22, 0, 5, 4, 24, 0, True, 5), "partial": (22, 0, 1, 1, 0, 27, False, 1),
                    "empty-budget": (22, 0, 0, 0, 0, 28, False, 0), "deferred": (4, 18, 5, 4, 24, 0, True, 5),
                    "exact-key": (22, 0, 1, 1, 27, 0, True, 1)}
    fields = ("inferred_row_count", "deferred_row_count", "evidence_record_count", "matched_member_count", "complete_absence_member_count", "unknown_member_count", "complete", "page_count")
    for name, expected in expectations.items():
        require(results[name]["inventory_member_count"] == 28 and equal([results[name][field] for field in fields], list(expected)), "selected native profile coverage differs")
    require(results["complete"]["ambiguous_members"] == ["source03.py"], "ambiguous records were collapsed")
    require(native["exact-key-join.json"]["selector"]["canonical_key_id"] is not None, "exact-key profile selector missing")
    baseline = native["independent-authored-plan-preview.json"]
    previews = {name: receive_preview(native[f"{name}-plan-preview.json"], native[f"{name}-join.json"], baseline, protocol_pins[PROTOCOL_NAMES[-1]]) for name in PREVIEWS}
    require(len({value["input_snapshot_cid"] for value in previews.values()}) == 3, "different advisory query states reused planning snapshot")
    return results, previews


def repair_join(join):
    """Rehash unsigned outer containers for adversarial controls, never proof bodies."""
    scan = join["scan"]["record"]
    ordered = [{"source_key": row["source_key"], "entry_cid": row["entry_cid"]} for row in scan["entries"]]
    scan["membership"] = {"ordered": ordered, "cid": cid(ordered)}
    join["scan"]["artifact_cid"] = cid_bytes(wire(scan))
    for wrapper in join["query"]["pages"]:
        page = wrapper["page"]
        page["page_cid"] = cid({name: value for name, value in page.items() if name != "page_cid"})


def mutation_controls(native, protocol_pins):
    proofs, apps = proof_inventory(native)
    controls = []

    def join_control(name, profile, mutate):
        value = copy.deepcopy(native[f"{profile}-join.json"])
        mutate(value)
        repair_join(value)
        try:
            receive_join(value, proofs, apps, protocol_pins)
        except (ReceiverRefusal, KeyError, TypeError, ValueError) as error:
            controls.append({"name": name, "container_cids_recomputed": True, "rejected": True, "reason": str(error)})
            return
        raise ReceiverRefusal("negative control accepted: " + name)

    join_control("ordered_member_removed", "complete", lambda value: value["scan"]["record"]["entries"].pop())
    join_control("raw_member_order_reversed", "complete", lambda value: value["scan"]["record"]["entries"].reverse())
    join_control("member_duplicate", "complete", lambda value: value["scan"]["record"]["entries"].append(copy.deepcopy(value["scan"]["record"]["entries"][-1])))
    join_control("member_key_substituted", "complete", lambda value: value["scan"]["record"]["entries"][0].update(source_key="raw:00"))
    join_control("shard_source_order_reversed", "complete", lambda value: value["scan"]["record"]["shards"][0]["target_source_digests"].reverse())
    join_control("inference_borrowed_source", "complete", lambda value: next(row for row in value["scan"]["record"]["entries"] if row["inference"])["inference"].update(source_digest="0" * 64))
    join_control("deferred_with_inference", "deferred", lambda value: next(row for row in value["scan"]["record"]["entries"] if row["disposition"] == "deferred_budget").update(inference={}))
    join_control("boolean_inventory_counter", "complete", lambda value: value["scan"]["record"]["counters"].update(inventory_entries=True))
    join_control("member_ledger_omission", "complete", lambda value: value["entries"].pop())
    join_control("partial_false_absence", "partial", lambda value: next(row for row in value["entries"] if not row["evidence_entry_ids"]).update(evidence_disposition="no_exact_indexed_conditional_evidence"))
    join_control("empty_budget_false_absence", "empty-budget", lambda value: value["entries"][0].update(evidence_disposition="no_exact_indexed_conditional_evidence"))
    join_control("empty_budget_claimed_complete", "empty-budget", lambda value: value["query"].update(complete=True))
    join_control("cursor_wrong_epoch", "partial", lambda value: value["query"]["pages"][0]["page"]["next_cursor"].update(epoch=7))
    join_control("cursor_wrong_head", "partial", lambda value: value["query"]["pages"][0]["page"]["next_cursor"].update(head_cid=cid({"other": "head"})))
    join_control("cursor_wrong_inventory", "partial", lambda value: value["query"]["pages"][0]["page"]["next_cursor"].update(inventory_cid=cid({"other": "inventory"})))
    join_control("cursor_wrong_selector", "partial", lambda value: value["query"]["pages"][0]["page"]["next_cursor"].update(selector_cid=cid({"other": "selector"})))
    join_control("cursor_wrong_position", "partial", lambda value: value["query"]["pages"][0]["page"]["next_cursor"].update(after=cid({"other": "position"})))
    join_control("page_wrong_start", "complete", lambda value: value["query"]["pages"][1]["page"].update(start_cursor=None))
    join_control("duplicate_page", "complete", lambda value: value["query"]["pages"].insert(1, copy.deepcopy(value["query"]["pages"][0])))
    join_control("exact_key_not_in_evidence", "exact-key", lambda value: value["selector"].update(canonical_key_id="canonical-proof-cache-key:sha256:" + "0" * 64))
    join_control("conditional_verdict_corrupted", "complete", lambda value: value["evidence"][0].update(verification_status="recorded_conditional_proved"))
    join_control("empty_domain_becomes_applicable", "complete", lambda value: next(row for row in value["evidence"] if row["applicability_status"] == "empty_domain")["applicability_summary"].update(conditional_proved=True, model_applicability_established=True))
    join_control("conditional_record_becomes_live", "complete", lambda value: value["evidence"][0].update(historical_records_observed_live=True))
    join_control("source_binding_corrupted", "complete", lambda value: value["evidence"][0]["source_binding"].update(content_sha256="0" * 64))
    join_control("canonical_key_rehashed_but_not_native", "complete", lambda value: _mutate_key(value["evidence"][0]))
    join_control("dependency_head_substituted", "complete", lambda value: value["evidence"][0]["dependencies"].update(head_cid=cid({"other": "head"})))
    join_control("proof_record_substituted", "complete", lambda value: value["evidence"][0]["query_entry"].update(verification_cid=list(proofs)[0]))
    join_control("authority_integer_false", "complete", lambda value: value["authority"].update(proof_authority=0))
    join_control("page_authority_elevated", "complete", lambda value: value["query"]["pages"][0]["page"]["authority"].update(kernel_checked=True))
    join_control("query_byte_budget_undercharged", "complete", lambda value: value["limits"].update(max_query_bytes=1))
    baseline, joined = native["independent-authored-plan-preview.json"], native["complete-join.json"]
    for name, mutate in (
        ("runtime_fact_promoted", lambda value: value["current_facts"].append({"predicate_id": REQUIREMENTS[0]})),
        ("runtime_task_omitted", lambda value: value["removed_task_ids"].append(TASKS[0])),
        ("runtime_requirement_resolved", lambda value: value["residual_requirements"][0].update(status="proved")),
        ("authored_goal_digest_changed", lambda value: value["repository_preview"]["input_snapshot"]["material_binding"]["field_digests"].update(frozen_goal="sha256:" + "0" * 64)),
        ("preview_unknown_became_absence", lambda value: value["codebase_inventory_evidence"]["coverage"].update(evidence_unknown_members=1)),
        ("preview_omission_authority", lambda value: value["authority"].update(omission_authority=True)),
    ):
        value = copy.deepcopy(native["complete-plan-preview.json"])
        mutate(value)
        value["codebase_inventory_evidence_cid"] = cid(value["codebase_inventory_evidence"])
        value["result_cid"] = cid({key: child for key, child in value.items() if key != "result_cid"})
        try:
            receive_preview(value, joined, baseline, protocol_pins[PROTOCOL_NAMES[-1]])
        except ReceiverRefusal as error:
            controls.append({"name": name, "container_cids_recomputed": True, "rejected": True, "reason": str(error)})
        else:
            raise ReceiverRefusal("negative control accepted: " + name)
    return controls


def _mutate_key(item):
    wrapper = item["contract"]["canonical_keys"][0]
    wrapper["key"]["checker"] = "another-native-checker"
    old = wrapper["key_id"]
    wrapper["key_id"] = native_key(wrapper["key"])
    item["query_entry"]["canonical_key_ids"] = sorted(wrapper["key_id"] if value == old else value for value in item["query_entry"]["canonical_key_ids"])


def load_input(manifest):
    capture = Capture()
    raw = capture.take(manifest, limit=MAX_MANIFEST)
    spec = document(raw, MAX_MANIFEST)
    closed(spec, {"schema", "prior_primary_audit", "generation_inputs", "native_files", "protocol_sources"}, "input manifest")
    require(spec["schema"] == INPUT_SCHEMA, "input schema")
    descriptor(spec["prior_primary_audit"])
    require(spec["prior_primary_audit"]["sha256"] == AUDIT_SHA256 and spec["prior_primary_audit"]["bytes"] == AUDIT_BYTES, "fixed independent primary audit anchor")
    audit = document(capture.take(canonical_path(spec["prior_primary_audit"]["path"]), spec["prior_primary_audit"]))
    require(audit["schema"] == "codebase-inventory-evidence-join-readonly-audit@1" and audit["passed"] is True
            and audit["primary_namespace_unchanged"] is True, "prior raw audit profile")
    namespace = canonical_path(audit["namespace"])
    descriptor(spec["generation_inputs"], original=True)
    generation_pin = spec["generation_inputs"]
    require(generation_pin["original_path"] == str(namespace / "generation-inputs.json")
            and audit["read_pins"].get(generation_pin["original_path"]) == generation_pin["sha256"], "generation input anchor")
    generation = document(capture.take(canonical_path(generation_pin["path"]), generation_pin))
    closed(generation, {"capture", "execution_attestation", "files", "schema", "scope"}, "generation inputs")
    require(generation["schema"] == "codebase-inventory-evidence-join-selected-inputs@1"
            and generation["execution_attestation"] is False
            and generation["scope"] == "listed_local_files_only_not_transitive_dependency_or_execution_attestation", "generation input scope")
    require(type(spec["native_files"]) is list and len(spec["native_files"]) == len(NATIVE_NAMES)
            and type(spec["protocol_sources"]) is list and len(spec["protocol_sources"]) == len(PROTOCOL_NAMES), "selected role population")
    native, protocol_pins = {}, {}
    for pin in spec["native_files"]:
        descriptor(pin, named=True, original=True)
        require(pin["name"] in NATIVE_NAMES and pin["name"] not in native
                and pin["original_path"] == str(namespace / pin["name"])
                and audit["read_pins"].get(pin["original_path"]) == pin["sha256"], "native public role/anchor binding")
        native[pin["name"]] = document(capture.take(canonical_path(pin["path"]), pin))
    for pin in spec["protocol_sources"]:
        descriptor(pin, named=True, original=True)
        matches = [row for row in generation["files"] if row["name"] == pin["name"]]
        require(pin["name"] in PROTOCOL_NAMES and pin["name"] not in protocol_pins and len(matches) == 1
                and pin["original_path"] == matches[0]["path"] and pin["sha256"] == matches[0]["sha256"]
                and pin["bytes"] == matches[0]["bytes"]
                and audit["read_pins"].get(pin["original_path"]) == pin["sha256"], "inert selected producer input anchor")
        capture.take(canonical_path(pin["path"]), pin)
        protocol_pins[pin["name"]] = pin["sha256"]
    return capture, spec, native, protocol_pins


def audit(manifest, output):
    manifest, output = canonical_path(str(manifest)), canonical_path(str(output))
    capture, spec, native, protocol_pins = load_input(manifest)
    # A copied manifest is a runner input; its parent is not the selected body scope.
    scopes = {path.parent for path in capture.raw if path != manifest}
    scopes.update(canonical_path(pin["original_path"]).parent for pin in
                  [spec["generation_inputs"], *spec["native_files"], *spec["protocol_sources"]])
    require(all(output != scope and scope not in output.parents for scope in scopes)
            and output not in capture.raw and not output.exists(), "output must be fresh and outside selected input scopes")
    profiles, previews = receive_profiles(native, protocol_pins)
    controls = mutation_controls(native, protocol_pins)
    capture.stable()
    output.mkdir(parents=True, exist_ok=False)
    retained = output / "inputs"
    retained.mkdir()
    input_files = []
    for index, (path, raw) in enumerate(capture.raw.items()):
        destination = retained / f"{index:02d}-{path.name}"
        destination.write_bytes(raw)
        require(OriginalCapture.read(destination, len(raw)) == raw, "retained copy differs")
        input_files.append({"path": str(path), "retained_path": str(destination), "sha256": sha(raw), "bytes": len(raw)})
    capture.stable()
    for row in input_files:
        require(sha(OriginalCapture.read(Path(row["retained_path"]), row["bytes"])) == row["sha256"], "retained copy changed")
    report = {"schema": REPORT_SCHEMA, "status": "passed", "passed": True, "manifest_sha256": sha(capture.raw[manifest]),
              "prior_primary_audit_sha256": spec["prior_primary_audit"]["sha256"],
              "input_origin": "retained_native_inventory_evidence_join_public_export_20261003_04",
              "scope": "selected_public_record_reconciliation_not_owner_execution_or_authentication",
              "input_files_unchanged": True, "native_export_receiving_conformance": True,
              **{name: False for name in FALSE_FLAGS},
              "runtime_fact_count": 0, "tasks_omitted_count": 0, "additional_attempted_training_epochs": 0,
              "native_profile_count": 5, "inventory_member_count": 28, "native_evidence_record_count": 5,
              "native_preview_count": 4, "runtime_requirement_count": 4, "runtime_task_count": 4,
              "retained_page_count": sum(value["page_count"] for value in profiles.values()),
              "mutation_control_count": len(controls), "input_file_count": len(input_files), "input_bytes": capture.total,
              "profiles": profiles, "previews": previews, "input_files": input_files, "mutation_controls": controls,
              "limitations": ["The independently pinned primary audit is a local raw-byte anchor, not a signature or producer execution attestation.",
                              "Recorded conditional verdicts and domain classifications are reconciled to retained original records; no checker or source semantics are replayed.",
                              "Numerical observations, worker receipts and inference shard digests remain recorded metadata; model state, tensors and source CAS bodies were not selected.",
                              "Closing-page CIDs identify retained fence metadata only; live catalog epoch, eligibility, owner state and profile grants were not observed.",
                              "The six semantic field digests are compared with the independent baseline preview; their underlying authored planning material is not independently reconstructed.",
                              "An adversary able to replace all independent anchors could author a self-consistent unsigned export. This receiving profile cannot authenticate such a producer."]}
    (output / "native_inventory_query.json").write_bytes(wire(report) + b"\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        report = audit(args.manifest, args.output)
    except (ReceiverRefusal, KeyError, TypeError, ValueError, OSError, RecursionError) as error:
        print(json.dumps({"passed": False, "reason": str(error)}), file=sys.stderr)
        return 1
    print(json.dumps({"passed": True, "profiles": report["native_profile_count"], "controls": report["mutation_control_count"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
