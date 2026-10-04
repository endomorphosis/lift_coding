"""Receive fixed full-successor transport and failed-worker metadata without native work."""
from __future__ import annotations

import argparse
import copy
import json
import math
import os
import re
import stat
import time
from hashlib import sha256
from pathlib import Path

INPUT_SCHEMA = "codebase-ir-successor-receiving-custody-input@1"
SCHEMA = "codebase-ir-successor-receiving-custody@1"
PROFILE = "retained-full300-successor-receiving@1"
MAX_FILE = 2 * 1024 * 1024
MAX_BYTES = 8 * 1024 * 1024
MAX_FILES = 32
MAX_MANIFEST = 128 * 1024
MAX_REPORT = 4 * 1024 * 1024
MAX_SECONDS = 120
MAX_DEPTH = 32
MAX_VALUES = 100000
ROLES = (
    "full_scan_native", "full_scan_audit", "actual_receiving", "host_configuration",
    "transport_controls", "signed_reader_controls", "failed_worker_02_native",
    "failed_worker_02_container", "failed_worker_03_native", "failed_worker_03_container",
)
PUBLIC_PINS = dict(zip(ROLES, (
    "2bd63662dc0b954ed98bf83012e805218c0ac6ca5981497a8cd754b18083f788",
    "43b5b045371bc85851657eeab04382e0f844ae22bf7aa4b0556fd9e22a8a73a1",
    "82e7b4697750b4a077e3dbbb82f8ed1fcd706a77f471f25f8c2dd21775adb7b8",
    "c60d91943187515915b8c4c0d0ace3f3703f7de4da1960f09e49371a8cdf6575",
    "548ce12d212ca2df1b44eddfb2c8667acaaaa704c24c1f51a92e1bce9c3bb417",
    "a79f065e0ef31d7d78982562e8281d72b892b5f9a27a2071f90acdbc8867caba",
    "5d4b31c1aef376b6d8515f804c3f3c11af6215d4ef3d9da0bbb495671a79bb16",
    "d1e69fc426029557165b044e017b6837a01b7ac08fee3c0a322d9b9d9f361476",
    "792756be4d40aa32ae9e25cc625bc7a3edb40252d5f5020b991f26a89e349e59",
    "25934c6e3ff8ff89dc98ceac84874d6e691ffaebc8e51b13cd15ffe3fc73954f",
), strict=True))
TRUE_FLAGS = (
    "retained_receiving_custody_conformance", "receiving_bindings_reconciled",
    "copied_path_relocations_reconciled", "native_pair_generation_advance_reconciled",
    "declared_archive_metadata_only_scope_preserved", "failed_whole_signed_attempts_preserved",
    "retained_cleanup_observations_reconciled", "unsigned_receiving_scope_preserved",
    "input_files_unchanged",
)
FALSE_FLAGS = (
    "native_execution_performed", "training_executed", "current_authority_claimed",
    "owner_sources_imported", "owner_database_opened", "profile_keys_read",
    "network_access_performed", "git_executable_invoked", "source_bodies_verified",
    "model_bodies_verified", "database_bodies_verified", "complete_archive_body_closure",
    "independent_native_receiving_reperformed", "numerical_execution_independently_reperformed",
    "optimizer_replay_qualified", "signed_successor_worker_qualified", "signed_admission_qualified",
    "worker_dispatch_qualified", "proof_authority", "source_semantics_verified",
    "source_execution_attested", "scan_execution_attested", "kernel_resource_enforcement_independently_verified",
    "live_cleanup_reobserved", "process_origin_attested", "production_default_activated",
    "complete_scan_independently_reperformed", "cuda_qualified", "384d_qualified",
    "signature_authentication_performed", "throughput_qualified", "whole_host_resource_pool_recreated",
)
ZERO_FIELDS = ("runtime_fact_count", "tasks_omitted_count", "additional_attempted_training_epochs")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")


def same(left, right):
    """JSON type-sensitive equality, including bool/int and int/float distinctions."""
    return wire(left) == wire(right)


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8")


def bounded_canonical(value, maximum):
    chunks, size = [], 0
    for token in json.JSONEncoder(sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False).iterencode(value):
        raw = token.encode("utf-8")
        require(size + len(raw) + 1 <= maximum, "serialized report allocation bound")
        chunks.append(raw)
        size += len(raw)
    return b"".join(chunks) + b"\n"


def document(raw):
    depth, quoted, escape, containers, tokens, bare = 0, False, False, 0, 0, False
    for token in raw:
        if quoted:
            if escape:
                escape = False
            elif token == 92:
                escape = True
            elif token == 34:
                quoted = False
        elif token == 34:
            quoted = True
            bare = False
            tokens += 1
        elif token in (91, 123):
            depth += 1
            containers += 1
            tokens += 1
            bare = False
            require(depth <= MAX_DEPTH and containers <= MAX_VALUES, "JSON structure allocation bound")
        elif token in (93, 125):
            depth -= 1
            bare = False
            require(depth >= 0, "JSON nesting mismatch")
        elif token in (9, 10, 13, 32, 44, 58):
            bare = False
        elif not bare:
            tokens += 1
            bare = True
        require(tokens <= MAX_VALUES, "JSON lexical value allocation bound")

    def pairs(items):
        value = {}
        for key, child in items:
            require(key not in value, "duplicate JSON key")
            value[key] = child
        return value

    def integer(token):
        require(len(token) <= 20, "JSON integer allocation bound")
        value = int(token)
        require(abs(value) <= 2**63 - 1, "JSON integer magnitude bound")
        return value

    def floating(token):
        require(len(token) <= 64, "JSON float allocation bound")
        value = float(token)
        require(math.isfinite(value), "nonfinite JSON number")
        return value

    def constant(_):
        raise ValueError("nonfinite JSON number")

    value = json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=pairs,
                       parse_int=integer, parse_float=floating, parse_constant=constant)
    require(type(value) is dict, "JSON object required")
    pending, count = [(value, 0)], 0
    while pending:
        child, level = pending.pop()
        count += 1
        require(count <= MAX_VALUES and level <= MAX_DEPTH, "JSON value allocation bound")
        if type(child) is str:
            require(len(child) <= MAX_FILE and "\x00" not in child and not any(0xD800 <= ord(char) <= 0xDFFF for char in child), "bounded JSON text required")
        elif type(child) is dict:
            pending.extend((key, level + 1) for key in child)
            pending.extend((item, level + 1) for item in child.values())
        elif type(child) is list:
            pending.extend((item, level + 1) for item in child)
    return value


def closed(value, keys, message):
    require(type(value) is dict and set(value) == set(keys), message)


def exact_int(value, maximum=2**63 - 1):
    require(type(value) is int and 0 <= value <= maximum, "bounded exact integer required")
    return value


def number(value):
    require(type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1e9, "bounded recorded number required")
    return value


def digest(value):
    require(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None, "SHA-256 required")
    return value


def identity(value):
    require(type(value) is str and 0 < len(value) <= 1024 and "\x00" not in value
            and re.fullmatch(r"[A-Za-z0-9:_./-]+", value) is not None, "bounded declared identity required")
    return value


def lexical_path(value, *, absolute=True):
    require(type(value) is str and 0 < len(value) <= 8192 and "\x00" not in value, "bounded lexical path required")
    path = Path(value)
    require(path.is_absolute() is absolute and ".." not in path.parts and str(path) == value and value != ".",
            "canonical lexical path required")
    return path


def descriptor(value):
    closed(value, {"path", "sha256", "size_bytes"}, "closed file descriptor required")
    lexical_path(value["path"])
    digest(value["sha256"])
    exact_int(value["size_bytes"], MAX_FILE)
    return dict(value)


def declared_pin(root, value):
    closed(value, {"path", "sha256", "bytes"}, "closed declared descriptor required")
    return descriptor({"path": str(root / lexical_path(value["path"], absolute=False)),
                       "sha256": value["sha256"], "size_bytes": value["bytes"]})


class Capture:
    """Two separate caches receive only explicitly pinned regular bodies."""

    def __init__(self, remap=None, *, started=None):
        self.remap, self.files, self.total, self.identities = remap, {}, 0, {}
        self.started = time.monotonic() if started is None else started

    def deadline(self):
        require(time.monotonic() - self.started <= MAX_SECONDS, "custody deadline")

    @staticmethod
    def fingerprint(path):
        row = path.lstat()
        return row.st_dev, row.st_ino, row.st_size, row.st_mtime_ns, row.st_ctime_ns

    @staticmethod
    def raw(path, maximum):
        require(path.is_absolute() and path.resolve(strict=True) == path, "canonical nonsymlink file required")
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            before = os.fstat(fd)
            require(stat.S_ISREG(before.st_mode) and 0 <= before.st_size <= maximum, "bounded regular file required")
            with os.fdopen(fd, "rb", closefd=False) as stream:
                raw = stream.read(maximum + 1)
            after, current = os.fstat(fd), path.lstat()
            def fingerprint(row):
                return row.st_dev, row.st_ino, row.st_size, row.st_mtime_ns, row.st_ctime_ns
            require(fingerprint(before) == fingerprint(after) == fingerprint(current) and len(raw) == before.st_size,
                    "file changed during bounded read")
            return raw
        finally:
            os.close(fd)

    def read(self, path, pin=None, *, mapped=True, maximum=MAX_FILE):
        self.deadline()
        logical = lexical_path(str(path))
        if self.remap is not None and mapped:
            require(str(logical) in self.remap, "explicit relocated member unavailable")
            physical = lexical_path(self.remap[str(logical)])
        else:
            physical = logical
        limit = maximum if pin is None else descriptor(pin)["size_bytes"]
        require(limit <= maximum, "preallocation file bound")
        if physical not in self.files:
            require(len(self.files) < MAX_FILES and self.total + limit <= MAX_BYTES, "preallocation aggregate bound")
            before = self.fingerprint(physical)
            self.files[physical] = self.raw(physical, limit)
            self.identities[physical] = self.fingerprint(physical)
            require(before == self.identities[physical], "file identity changed during capture")
            self.total += len(self.files[physical])
        raw = self.files[physical]
        if pin is not None:
            require(len(raw) == pin["size_bytes"] and sha256(raw).hexdigest() == pin["sha256"], "selected raw pin mismatch")
        return raw

    def stable(self):
        for path, raw in self.files.items():
            self.deadline()
            require(self.raw(path, len(raw)) == raw and self.fingerprint(path) == self.identities[path], "previously captured body or identity changed")
        return True


def scope():
    return {**dict.fromkeys(TRUE_FLAGS, True), **dict.fromkeys(FALSE_FLAGS, False),
            **dict.fromkeys(ZERO_FIELDS, 0)}


def recorded_false(value, fields, message):
    require(all(value[field] is False for field in fields), message)


def recorded_zero(value, fields, message):
    require(all(exact_int(value[field]) == 0 for field in fields), message)


def pin_pair(value, pin, message):
    closed(value, {"bytes", "sha256"}, message)
    require(exact_int(value["bytes"], MAX_FILE) == pin["size_bytes"]
            and digest(value["sha256"]) == pin["sha256"], message)


def archive_metadata(value):
    """Check complete declared rows without following any archive member path."""
    closed(value, {"files", "regular_files", "regular_bytes", "inventory_cid"}, "closed declared archive")
    rows = value["files"]
    require(type(rows) is list and 0 < len(rows) <= 4096, "bounded declared archive population")
    members, size = {}, 0
    for row in rows:
        require(type(row) is dict and row.get("kind") in ("file", "directory"), "declared archive kind")
        kind = row["kind"]
        closed(row, {"path", "kind", "mode", "mtime_ns"} | ({"bytes", "sha256", "nlink"} if kind == "file" else set()),
               "closed declared archive row")
        if row["path"] == ".":
            require(kind == "directory", "declared archive root")
        else:
            lexical_path(row["path"], absolute=False)
        require(row["path"] not in members, "distinct declared archive paths")
        exact_int(row["mode"], 0o7777)
        exact_int(row["mtime_ns"])
        if kind == "file":
            size += exact_int(row["bytes"], 2**31)
            require(exact_int(row["nlink"], 65536) > 0, "positive declared hardlink count")
            digest(row["sha256"])
        members[row["path"]] = row
    regular = sum(row["kind"] == "file" for row in rows)
    require(regular == exact_int(value["regular_files"], 4096)
            and size == exact_int(value["regular_bytes"]), "declared archive counts")
    # This CID authenticates these metadata bytes, not the named source/model bodies.
    import base64
    raw = json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    cid = "b" + base64.b32encode(b"\x01\xa9\x02\x12\x20" + sha256(raw).digest()).decode().lower().rstrip("=")
    require(value["inventory_cid"] == cid, "declared archive metadata CID")
    return members, {"declared_regular_files": regular, "declared_regular_bytes": size,
                     "metadata_inventory_cid_rederived": cid, "named_member_bodies_opened": 0,
                     "deep_body_closure": "unknown_not_selected"}


def drained(value):
    require(value["scope"] == "named_scan_process_owners_only", "named-owner resource scope")
    for field in ("active_lease_count", "waiting_request_count", "global_active_lease_count", "global_waiting_request_count"):
        require(exact_int(value[field]) == 0, "recorded named-owner resource drain")
    require(type(value["owner_pids"]) is list and 0 < len(value["owner_pids"]) <= 8
            and all(exact_int(pid) > 0 for pid in value["owner_pids"]), "recorded positive owner PID population")
    return {"owner_pids": value["owner_pids"], "recorded_zero_leases_and_waiters": True,
            "live_cleanup_reobserved": False, "physical_absence_inferred": False}


def checkpoint_declarations(value):
    closed(value, {"root", "child"}, "complete two checkpoint declarations")
    for role, epochs in (("root", 1), ("child", 2)):
        row = value[role]
        closed(row, {"artifact", "adam_steps", "completed_epochs", "feature_columns", "latent_width", "report_sha256", "state_sha256"},
               "closed checkpoint declaration")
        closed(row["artifact"], {"bytes", "sha256"}, "closed checkpoint artifact declaration")
        require(exact_int(row["artifact"]["bytes"], 2**31) > 0, "positive checkpoint artifact declaration")
        digest(row["artifact"]["sha256"])
        digest(row["report_sha256"])
        digest(row["state_sha256"])
        require(exact_int(row["completed_epochs"]) == epochs and exact_int(row["feature_columns"]) == 53
                and exact_int(row["latent_width"]) == 8 and type(row["adam_steps"]) is list
                and len(row["adam_steps"]) == 4 and all(exact_int(step) == epochs for step in row["adam_steps"]),
                "exact inherited checkpoint dimensions/epochs/Adam step declarations")


def receiving_receipt(docs, pins):
    native, audit, received, host = (docs[role] for role in ROLES[:4])
    require(native["schema"] == "codebase-full-successor-native-qualification@1" and native["qualified"] is True
            and native["complete_scan_qualified"] is True, "selected full-scan result status")
    require(audit["schema"] == "codebase-full-successor-independent-audit@1" and audit["qualified"] is True
            and audit["complete_scan_qualified"] is True and audit["errors"] == [] and audit["preserved"] is True,
            "selected full-scan audit status")
    recorded_false(native, ("proof_authority", "worker_dispatch_qualified", "source_execution_attested", "scan_execution_attested",
                           "cuda_qualified", "384d_qualified", "production_default_activated"), "full-scan authority boundary")
    recorded_false(audit, ("proof_authority", "worker_dispatch_qualified", "native_owners_opened", "sql_executed", "git_executed",
                          "numerical_execution_independently_reperformed", "process_origin_attested"), "closed full-scan audit boundary")
    require(type(audit["audited_result"]) is dict and set(audit["audited_result"]) == {"bytes", "sha256", "path"},
            "closed audited native descriptor")
    pin_pair({key: audit["audited_result"][key] for key in ("bytes", "sha256")}, pins["full_scan_native"], "audit/result raw binding")
    require(received["schema"] == "source-successor-dispatch-actual-receiving@1" and received["qualified"] is True
            and received["error"] is None and received["actual_native_receiving_complete"] is True
            and received["current_source_receiving_verified"] is True and received["current_pins_unchanged"] is True,
            "actual receiving status and recorded live-source observation")
    recorded_false(received, ("proof_authority", "signed_admission_qualified", "source_execution_attested", "scan_execution_attested",
                             "kernel_resource_enforcement", "native_owners_in_old_archives_opened", "git_in_old_archives_executed"),
                   "unsigned receiving authority boundary")
    recorded_zero(received, ("new_scan_pages", "new_fitting_epochs", "inference_attempts", "post_setup_fit_attempt_count"),
                  "actual receiving performs no fit or page inference")
    require(exact_int(received["owner_pairs_opened"]) == 1
            and exact_int(received["registry_owner_generation_increment_from_native_open"]) == 1,
            "exact one new native owner pair")
    require(all(received[key] is True for key in ("closed_source_archive_preserved", "old_closed_archive_preserved",
                "staged_archive_preserved", "own_lease_released", "rss_reservation_respected")), "recorded custody and cleanup observations")
    staged, materialized, relocated = received["staged"], received["materialized"], received["actual_relocations"]
    require(staged["schema"] == "source-successor-dispatch-staged-setup@1" and staged["qualified"] is True
            and staged["fresh_native_receiving_required"] is True, "staged declaration scope")
    recorded_false(staged, ("native_owners_opened", "proof_authority", "source_execution_attested", "scan_execution_attested"),
                   "staging is no native receiving")
    recorded_zero(staged, ("new_fitting_epochs", "new_scan_pages"), "staging cost scope")
    pin_pair(staged["native_result"], pins["full_scan_native"], "staged native/result binding")
    pin_pair(staged["audit"], pins["full_scan_audit"], "staged audit/raw binding")
    require(materialized["schema"] == "source-successor-dispatch-materialized-setup@1" and materialized["qualified"] is True
            and materialized["fresh_native_receiving_required"] is True and materialized["native_owners_opened"] is False
            and materialized["proof_authority"] is False, "materialization no native authority")
    recorded_zero(materialized, ("new_fitting_epochs", "new_scan_pages"), "materialization zero costs")
    require(same(materialized["staged_receipt"], staged) and materialized["seed"] == staged["staged_destination"]
            and materialized["output"] == relocated["output"], "complete embedded staged/materialized binding")
    require(digest(materialized["staged_receipt_sha256"]) == sha256(wire(staged) + b"\n").hexdigest()
            and digest(relocated["materialization_sha256"]) == sha256(wire(materialized) + b"\n").hexdigest(),
            "exact canonical embedded receipt byte digests")
    require(received["source_namespace"] == staged["source_namespace"] == audit["namespace"], "same selected full-scan namespace")
    lexical_path(received["source_namespace"])
    require(audit["audited_result"]["path"] == "result.json", "declared original native result location")
    lexical_path(materialized["output"])
    lexical_path(materialized["seed"])
    for field in ("root_cid", "completion_cid"):
        require(staged[field] == native[field] and (field != "completion_cid" or native[field] == audit["complete_scan"][field]), "full-scan receiving identity")
    for staged_key, native_key in (("selection_cid", "successor_selection_cid"), ("selected_version_id", "child_version_id"),
                                  ("previous_version_id", "parent_version_id"), ("source_delta_cid", "source_delta_cid"),
                                  ("current_head", "current_head"), ("previous_head", "previous_head")):
        require(same(staged[staged_key], native[native_key]), "selected source/model identity binding")
    checkpoint_declarations(staged["checkpoint_states"])
    require(same(staged["checkpoint_states"], native["checkpoint_states"])
            and same(staged["checkpoint_states"], received["checkpoint_states_before"])
            and same(staged["checkpoint_states"], received["checkpoint_states_after"]), "declared checkpoint observations agree")
    require(exact_int(staged["inherited_scan_pages"]) == 10 and exact_int(staged["inherited_reference_pages"]) == 1
            and exact_int(staged["inherited_setup_epochs"]) == 2, "inherited scan/reference/setup costs")
    require(exact_int(native["coverage"]["inventory_entries"]) == 300 and exact_int(native["coverage"]["pages"]) == 10,
            "declared complete scan denominator")
    require(host["schema"] == "successor-expansion-host-configuration@1" and host["kernel_enforcement_claimed"] is False,
            "selected shared host scope")
    host_pin = {"bytes": pins["host_configuration"]["size_bytes"], "sha256": pins["host_configuration"]["sha256"]}
    require(same(native["host_configuration_pin"], host_pin)
            and same(audit["shared_host"]["configuration_pin"], host_pin), "full-scan shared host pin")
    require(type(received["host_configuration"]) is dict and set(received["host_configuration"]) == {"path", "sha256", "bytes"}, "closed receiving shared host descriptor")
    pin_pair({key: received["host_configuration"][key] for key in ("bytes", "sha256")}, pins["host_configuration"], "receiving shared host pin")
    lexical_path(received["host_configuration"]["path"])
    require(same(native["scheduler_configuration"], host["persisted_config"])
            and native["scheduler_state_path"] == host["state_path"] == received["admission"]["state_path"], "shared host accounting state")
    members, source_archive = archive_metadata(received["source_archive_before"])
    _, old_archive = archive_metadata(received["old_archive_before"])
    require(staged["source_archive_inventory_cid"] == received["source_archive_before"]["inventory_cid"], "staged source archive metadata binding")
    copies, copied_size, copied_paths = staged["copied_members"], 0, set()
    require(type(copies) is list and len(copies) == 1631, "exact staged declared member population")
    for row in copies:
        closed(row, {"path", "source_path", "sha256", "bytes", "mode"}, "closed staged declared member")
        path, source = lexical_path(row["path"], absolute=False), lexical_path(row["source_path"], absolute=False)
        native_member = row["source_path"] in {"private/source.duckdb", "private/model.duckdb"} or row["source_path"].startswith(("private/source-artifacts/", "private/model-artifacts/", "repository/"))
        expected_path = source if native_member else Path("closed-full-scan") / source
        require(row["source_path"] not in copied_paths and path == expected_path, "staged relative path mapping")
        copied_paths.add(row["source_path"])
        require(row["source_path"] in members and members[row["source_path"]]["kind"] == "file", "staged declared membership")
        prior = members[row["source_path"]]
        require(digest(row["sha256"]) == prior["sha256"] and exact_int(row["bytes"], 2**31) == prior["bytes"]
                and exact_int(row["mode"], 0o7777) == prior["mode"], "staged complete byte/mode declarations")
        copied_size += row["bytes"]
    regular = {path for path, row in members.items() if row["kind"] == "file"}
    require(regular - copied_paths == {"progress.json", "private/model.duckdb.owner.lock"}
            and exact_int(staged["copied_files"]) == len(copies)
            and exact_int(staged["copied_bytes"]) == copied_size == 75553659, "declared staged totals and explicit exclusions")
    relocation_rows = relocation_receipt(received)
    resources = {"actual_receiving": drained(received["resources_after"]), "full_scan": drained(native["final_resources"]),
                 "receiving_recorded_admission": received["admission"], "shared_host_pin": host_pin,
                 "receiving_recorded_peak_rss_bytes": exact_int(received["peak_rss_bytes"]),
                 "kernel_containment_reverified": False, "other_owner_cleanup_inferred": False}
    require(exact_int(received["admission"]["cpu_slots"]) == 1 and exact_int(received["admission"]["child_process_slots"]) == 1
            and exact_int(received["admission"]["memory_mb"]) == 2048, "recorded receiving reservation")
    return {"root_cid": native["root_cid"], "completion_cid": native["completion_cid"],
            "selected_version_id": staged["selected_version_id"], "checkpoint_declarations_reconciled": True,
            "checkpoint_bodies_reconstructed": False, "inherited_default_pages": 10, "inherited_reference_pages": 1,
            "inherited_setup_epochs": 2, "new_page_inference": 0, "new_fitting_epochs": 0,
            "actual_receiving_recorded_seconds": number(received["recorded_seconds"]),
            "source_archive": source_archive, "old_archive": old_archive,
            "staged_archive": {"declared_regular_files": len(copies), "declared_regular_bytes": copied_size,
                "excluded_declared_paths": sorted(regular - copied_paths), "member_bodies_opened": 0,
                "full_byte_closure": "unknown_not_selected"}, "path_relocations": relocation_rows,
            "receiving_is_unsigned": True, "native_receiving_reexecuted": False}, resources
def relocation_receipt(received):
    value = received["actual_relocations"]
    require(value["schema"] == "source-successor-dispatch-copied-store-relocations@1" and value["qualified"] is True,
            "relocation metadata schema/status")
    recorded_false(value, ("native_owner_generation_advanced", "old_native_owners_opened", "proof_authority"),
                   "relocation does not open native owners or publish")
    recorded_zero(value, ("new_fitting_epochs", "new_scan_pages"), "relocation zero fitting/pages")
    rows = value["relocations"]
    require(type(rows) is list and len(rows) == 2 and [row["owner"] for row in rows] == ["source", "registry"],
            "exact ordered two owner path relocations")
    output = lexical_path(value["output"])
    declared_namespace = lexical_path(received["source_namespace"])
    summaries = []
    for row in rows:
        closed(row, {"owner", "old_artifact_root", "new_artifact_root", "before_sha256", "after_sha256", "before", "after",
                     "only_local_path_changed", "old_native_owners_opened", "native_publication_performed", "fitting_performed",
                     "owner_generation_advanced"}, "closed path-relocation record")
        recorded_false(row, ("old_native_owners_opened", "native_publication_performed", "fitting_performed", "owner_generation_advanced"),
                       "path relocation publication boundary")
        require(row["only_local_path_changed"] is True, "only local path relocation")
        suffix = "source-artifacts" if row["owner"] == "source" else "model-artifacts"
        require(row["old_artifact_root"] == str(declared_namespace / "private" / suffix)
                and row["new_artifact_root"] == str(output / "private" / suffix), "exact old/new local artifact path")
        require(digest(row["before_sha256"]) == sha256(wire(row["before"])).hexdigest()
                and digest(row["after_sha256"]) == sha256(wire(row["after"])).hexdigest(), "complete observed row digest")
        wanted = copy.deepcopy(row["before"])
        metadata = wanted["catalog"]["meta"] if row["owner"] == "source" else wanted["meta"]
        require(type(metadata) is list and len(metadata) == 1 and type(metadata[0]) is list
                and len(metadata[0]) == (5 if row["owner"] == "source" else 6)
                and exact_int(metadata[0][0]) == 1 and metadata[0][4] == row["old_artifact_root"], "complete singleton owner row")
        metadata[0][4] = row["new_artifact_root"]
        require(same(wanted, row["after"]), "unrelated owner rows unchanged through relocation")
        if row["owner"] == "source":
            before = received["native_owners_before"]["source"]
            require(same(row["after"]["ast"], before["tables"])
                    and same(before, received["native_owners_after"]["source"]), "source native pair retained observations unchanged")
        else:
            expected_native = copy.deepcopy(row["after"])
            require(exact_int(expected_native["meta"][0][5]) == 8, "recorded prior registry owner generation")
            expected_native["meta"][0][5] = 9
            require(same(expected_native, received["native_owners_before"]["registry"])
                    and same(expected_native, received["native_owners_after"]["registry"]), "sole native open advances registry 8 to9")
        summaries.append({"owner": row["owner"], "before_sha256": row["before_sha256"], "after_sha256": row["after_sha256"],
                          "old_artifact_root": row["old_artifact_root"], "new_artifact_root": row["new_artifact_root"],
                          "only_declared_local_path_changed": True, "database_bytes_opened": 0})
    require(same(received["native_owners_before"]["model_artifacts"], received["native_owners_after"]["model_artifacts"]),
            "model artifact declared pins unchanged")
    return summaries


def failed_worker_receipt(native, container, pins, suffix, selected):
    require(native["schema"] == "codebase-signed-successor-native-qualification@1" and native["qualified"] is False,
            "failed whole signed native attempt preserved")
    expected_error = ("SourceSuccessorAuditError", "structured identity rejects unreviewed scalar") if suffix == "02" else (
        "LeaseTimeoutError", "resumable inventory deadline exceeded")
    require((native["error_type"], native["error"]) == expected_error, "whole signed attempt terminal refusal")
    phases = native["phases"]
    names = ["materialize_independently_audited_complete_successor", "open_only_new_copied_native_owners",
             "receive_full_successor_default_pair_120_then30"]
    if suffix == "03":
        names += ["initialize_private_signed_owner", "sign_fresh_full_successor_task_manifest"]
    require(type(phases) is list and [row["name"] for row in phases] == names, "whole signed attempt phase population")
    for index, row in enumerate(phases):
        number(row["elapsed_seconds"])
        status = "failed" if suffix == "03" and index == len(names) - 1 else "completed"
        require(row["status"] == status, "whole signed attempt phase status")
        if status == "failed":
            require((row["error_type"], row["error"]) == expected_error, "terminal phase/top refusal join")
    recorded_false(native, ("proof_authority", "source_execution_attested", "scan_execution_attested", "production_default_activated",
                           "cuda_qualified", "384d_qualified", "complete_scan_reexecuted_here", "shares_host_pid_state"),
                   "failed worker authority and host PID boundary")
    recorded_zero(native, ("inference_attempt_count", "new_fitting_epochs", "post_setup_fit_attempt_count", "new_scan_pages",
                          "new_reference_pages", "provider_calls"), "failed worker new inference/training/provider work")
    require(exact_int(native["inherited_scan_pages"]) == 10 and exact_int(native["inherited_reference_pages"]) == 1
            and exact_int(native["inherited_setup_epochs"]) == 2 and native["local_pool_bounded_by_host_envelope"] is True,
            "failed worker inherited work and nested pool")
    for field in ("root_cid", "completion_cid"):
        require(native[field] == selected[field], "failed worker selected complete scan identity")
    require(native["selected_version_id"] == selected["selected_version_id"], "failed worker selected child declaration")
    reference = native["public_receivers_reference_close"]
    require(reference["budget_refused"] is True and reference["completed"] is False
            and reference["integrity_refusal_claimed"] is False and exact_int(reference["deadline_seconds"]) == 30
            and (reference["error_type"], reference["error"]) == ("LeaseTimeoutError", "resumable inventory deadline exceeded"),
            "separate public close budget refusal is no integrity finding")
    number(reference["elapsed_seconds"])
    require(container["schema"] == "signed-successor-worker-offline-container-execution@1"
            and exact_int(container["returncode"]) == 1, "failed container driver outcome")
    recorded_false(container, ("proof_authority", "production_activated", "privileged"), "failed container authority")
    require(container["network"] == "none" and container["host_reservation_acquired"] is True
            and container["host_reservation_released"] is True and container["host_lease_held_after_native_exit"] is True
            and container["container_removed"] is True and container["container_results_copied"] is True,
            "failed container recorded reservation/cleanup lifecycle")
    recorded_zero(container, ("new_scan_pages_created", "new_setup_fitting_epochs"), "failed container zero new work")
    pin_pair(container["source_audit"], pins["full_scan_audit"], "failed container full-scan audit binding")
    pin_pair(native["container_resource_authority_pin"], {"size_bytes": len(canonical(container["container_resource_authority"])),
             "sha256": sha256(canonical(container["container_resource_authority"])).hexdigest()}, "failed native/container authority byte binding")
    pin_pair(container["host_configuration_pin"], pins["host_configuration"], "failed container shared host pin")
    limits = container["actual_container_limits"]
    for field in ("inspection_returncode", "cgroup_returncode"):
        require(exact_int(limits[field]) == 0, "recorded cgroup/inspection command outcome")
    observation = limits["inspection"]
    require(observation["Id"] == container["container_id"], "exact recorded container ID")
    host_config = observation["HostConfig"]
    require(exact_int(host_config["Memory"]) == exact_int(container["memory_limit_bytes"]) == 8192 * 1024 * 1024
            and exact_int(host_config["NanoCpus"]) == 12 * 10**9
            and exact_int(container["cpu_limit"]) == 12 and exact_int(host_config["PidsLimit"]) == exact_int(container["pids_limit"]) == 512
            and host_config["NetworkMode"] == "none" and host_config["Privileged"] is False,
            "recorded container limits")
    require(same(limits["cgroup"]["values"], {"cpu.max": "1200000 100000", "memory.max": str(8192 * 1024 * 1024), "pids.max": "512"}),
            "recorded engine/cgroup limit agreement")
    authority = container["container_resource_authority"]
    require(authority["independent_whole_host_pool"] is False and authority["shares_host_pid_state"] is False
            and authority["proof_authority"] is False, "inner local accounting scope")
    envelope = authority["parent_host_envelope"]
    require(same(envelope["host_reservation"], container["host_reservation"])
            and envelope["container_id"] == container["container_id"]
            and same(envelope["host_configuration_pin"], container["host_configuration_pin"]), "same held outer host envelope")
    for key, expected in (("cpu_slots", 12), ("child_process_slots", 12), ("memory_mb", 8192)):
        require(exact_int(container["host_reservation"][key]) == expected, "held host envelope bound")
    require(container["host_reservation"]["released"] is False, "snapshot is held reservation, final release is separate observation")
    require(authority["persisted_config"]["total_cpu_slots"] == 9 and type(authority["persisted_config"]["total_cpu_slots"]) is int
            and exact_int(authority["persisted_config"]["total_memory_mb"]) == 6553, "safe inner pool below outer envelope")
    absence = container["container_absence_observation"]
    require(absence["container_id"] == container["container_id"] and exact_int(absence["returncode"]) == 0
            and absence["stdout"] == "", "recorded exact named container removal")
    return {"attempt": "signed_worker_" + suffix, "native_outcome": "failed_whole_attempt", "driver_returncode": 1,
            "native_recorded_seconds": number(native["recorded_seconds"]), "driver_recorded_seconds": number(container["elapsed_seconds"]),
            "error_type": expected_error[0], "error": expected_error[1], "complete_ordered_phases": phases,
            "public_close_budget_refusal": reference, "new_fitting_epochs": 0, "new_scan_pages": 0,
            "inherited_setup_epochs_per_attempt": 2, "container_reported_limits": host_config,
            "recorded_inner_pool_cpu_slots": 9, "recorded_inner_pool_memory_mb": 6553,
            "held_snapshot_and_later_release_separate": True, "container_resource_scope": "local PID pool under held host cgroup envelope",
            "native_recorded_cleanup": drained(native["final_resources"]),
            "host_recorded_cleanup": drained(container["host_owned_resources_after_cleanup"]),
            "container_removal_observation_retained": True, "signed_worker_qualification": False,
            "independent_failed_attempt_audit": "unknown_not_selected", "process_origin_authentication": False,
            "live_cleanup_reobserved": False, "unique_cpu_or_wall_time": "unknown_not_measured"}


def control_receipts(docs):
    transport, signed = docs["transport_controls"], docs["signed_reader_controls"]
    require(transport["schema"] == "source-successor-dispatch-stdlib-controls@1" and transport["qualified"] is True,
            "recorded transport control status")
    require(exact_int(transport["tests"]) == 79 and all(exact_int(transport[key]) == 0 for key in ("failures", "errors", "skipped",
            "new_fitting_epochs", "new_inference_pages")), "recorded complete transport case accounting")
    recorded_false(transport, ("git_executed", "native_owners_opened", "sql_executed"), "transport controls are detached")
    require(signed["schema"] == "signed-successor-independent-receipt-reader-controls@1" and signed["qualified"] is True
            and exact_int(signed["test_count"]) == 78 and exact_int(signed["returncode"]) == 0,
            "recorded signed-reader control accounting")
    recorded_false(signed, ("completion_authority", "docker_executed", "git_executed", "inference_executed", "native_owners_opened",
                           "process_origin_attested", "proof_authority", "source_repository_executed", "training_executed"),
                   "signed reader control authority scope")
    return {"transport": {"recorded_case_count": 79, "scope": transport["scope"], "native_qualification_inferred": False},
            "signed_reader": {"recorded_case_count": 78, "scope": signed["scope"], "native_qualification_inferred": False,
                              "public_signature_controls_retained": True, "signatures_verified_here": False}}
def write_new(path, raw):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=False) as stream:
            require(stream.write(raw) == len(raw), "complete owned write")
        os.fchmod(fd, 0o444)
    finally:
        os.close(fd)


def output_population(root, expected):
    require(root.is_absolute() and root.resolve(strict=True) == root and stat.S_ISDIR(root.lstat().st_mode),
            "canonical output directory")
    files, folders, pending = set(), set(), [root]
    while pending:
        folder = pending.pop()
        with os.scandir(folder) as entries:
            for entry in entries:
                relative = Path(entry.path).relative_to(root).as_posix()
                info = entry.stat(follow_symlinks=False)
                require(len(files) < MAX_FILES and len(folders) <= 1, "bounded owned output population")
                if stat.S_ISDIR(info.st_mode):
                    require(relative == "retained", "only expected retained directory")
                    folders.add(relative)
                    pending.append(Path(entry.path))
                else:
                    require(stat.S_ISREG(info.st_mode) and relative in expected, "exact regular owned output population")
                    files.add(relative)
    require(files == set(expected) and folders == {"retained"} and root.resolve(strict=True) == root,
            "exact final owned output population")


def audit(manifest, output, *, relocated_sources=None):
    started = time.monotonic()
    original, copies = Capture(relocated_sources, started=started), Capture(started=started)
    manifest, output = lexical_path(str(manifest)), lexical_path(str(output))
    require(output.parent.resolve(strict=True) == output.parent and not output.exists() and not output.is_symlink(),
            "fresh canonical output directory")
    raw_manifest = original.read(manifest, maximum=MAX_MANIFEST)
    selection = document(raw_manifest)
    closed(selection, {"schema", "selected_profile", "selected_files"}, "closed receiving input manifest")
    require(selection["schema"] == INPUT_SCHEMA and selection["selected_profile"] == PROFILE
            and type(selection["selected_files"]) is list and len(selection["selected_files"]) == len(ROLES),
            "fixed selected profile and population")
    pins = {}
    for role, row in zip(ROLES, selection["selected_files"], strict=True):
        closed(row, {"role", "path", "sha256", "size_bytes"}, "closed selected descriptor")
        require(row["role"] == role, "fixed ordered selected roles")
        pins[role] = descriptor({key: row[key] for key in ("path", "sha256", "size_bytes")})
        require(pins[role]["sha256"] == PUBLIC_PINS[role], "fixed independent retained public selection")
    paths = {pin["path"] for pin in pins.values()}
    require(len(paths) == len(ROLES) and str(manifest) not in paths, "disjoint original input population")
    if relocated_sources is not None:
        require(type(relocated_sources) is dict and set(relocated_sources) == {str(manifest), *paths},
                "closed explicit relocated input population")
        require(len(set(relocated_sources.values())) == len(relocated_sources), "distinct relocated physical inputs")
    physical = [Path(relocated_sources.get(path, path)) if relocated_sources else Path(path) for path in [str(manifest), *paths]]
    require(all(output != path and output not in path.parents and path not in output.parents for path in physical),
            "disjoint physical inputs and owned output")
    bodies = {role: original.read(Path(pins[role]["path"]), pins[role]) for role in ROLES}
    docs = {role: document(raw) for role, raw in bodies.items()}
    receiving, resources = receiving_receipt(docs, pins)
    failures = [failed_worker_receipt(docs[f"failed_worker_{suffix}_native"], docs[f"failed_worker_{suffix}_container"],
                                     pins, suffix, receiving) for suffix in ("02", "03")]
    controls = control_receipts(docs)
    original.stable()
    output.mkdir(mode=0o755)
    root_identity = (output.lstat().st_dev, output.lstat().st_ino)
    retained = output / "retained"
    retained.mkdir(mode=0o755)
    copy_rows, members = [], ["retained/input.json"]
    write_new(retained / "input.json", raw_manifest)
    copies.read(retained / "input.json", maximum=MAX_MANIFEST)
    for index, role in enumerate(ROLES):
        path = retained / (f"{index:02}-" + role + ".json")
        write_new(path, bodies[role])
        pin = {"path": str(path), "sha256": pins[role]["sha256"], "size_bytes": pins[role]["size_bytes"]}
        require(copies.read(path, pin) == bodies[role], "original and retained copy raw bytes")
        copy_rows.append({"role": role, **pins[role], "retained_copy": pin})
        members.append(path.relative_to(output).as_posix())
    findings = {"receiving": receiving, "resources": resources, "failed_signed_attempts": failures,
                "recorded_controls": controls,
                "missing_body_closure": {key: "unknown_not_selected" for key in (
                    "source_member_bodies", "model_checkpoint_bodies", "database_bodies", "signed_worker_independent_audits")}}
    nested = {"schema": "codebase-ir-successor-receiving-selected-custody@1", "status": "passed", "qualified": True,
              "selected_files": copy_rows, "manifest_sha256": sha256(raw_manifest).hexdigest(), "scope": scope(),
              "original_capture_bytes": original.total, "copy_capture_bytes": copies.total, **findings}
    nested_path = output / "selected_custody.json"
    nested_raw = bounded_canonical(nested, MAX_REPORT)
    write_new(nested_path, nested_raw)
    members.append(nested_path.name)
    report = {"schema": SCHEMA, "workflow": "successor_receiving_custody", "selected_profile": PROFILE,
              "status": "passed", "qualified": True, "selected_files": copy_rows,
              "selected_file_count": len(ROLES), "selected_input_bytes": sum(pin["size_bytes"] for pin in pins.values()),
              "manifest_sha256": sha256(raw_manifest).hexdigest(), **{role + "_sha256": pins[role]["sha256"] for role in ROLES},
              **scope(), "scope": scope(), **findings,
              "limits": {"max_file_bytes": MAX_FILE, "max_original_bytes": MAX_BYTES, "max_copy_bytes": MAX_BYTES,
                         "max_files_per_cache": MAX_FILES, "max_manifest_bytes": MAX_MANIFEST, "max_report_bytes": MAX_REPORT,
                         "max_seconds": MAX_SECONDS, "max_depth": MAX_DEPTH, "max_values": MAX_VALUES},
              "custody": {"original_file_count": len(original.files), "copy_file_count": len(copies.files),
                          "original_capture_bytes": original.total, "copy_capture_bytes": copies.total,
                          "local_receipt": {"path": str(nested_path), "sha256": sha256(nested_raw).hexdigest(), "size_bytes": len(nested_raw)}},
              "elapsed_seconds": time.monotonic() - started}
    report_path = output / "successor_receiving_custody.json"
    report_raw = bounded_canonical(report, MAX_REPORT)
    write_new(report_path, report_raw)
    members.append(report_path.name)
    original.stable()
    copies.stable()
    require(Capture.raw(nested_path, len(nested_raw)) == nested_raw and same(document(nested_raw), nested), "final local nested raw body")
    require(Capture.raw(report_path, len(report_raw)) == report_raw and same(document(report_raw), report), "final main raw report body")
    require((output.lstat().st_dev, output.lstat().st_ino) == root_identity, "owned output directory identity unchanged")
    output_population(output, members)
    original.deadline()
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    report = audit(args.manifest, args.output)
    print(json.dumps({"qualified": report["qualified"], "report": str(args.output / "successor_receiving_custody.json")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
