"""Audit an independently authored receiving corpus without opening native owners.

All identities and pages in this profile are assertion fixtures. They deliberately
do not use a production query codec or create proof, source, or model authority.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import stat
import sys
from pathlib import Path

INPUT_SCHEMA = "codebase-ir-inventory-query-controls-input@1"
FIXTURE_SCHEMA = "codebase-ir-inventory-query-controls-fixture@1"
REPORT_SCHEMA = "codebase-ir-inventory-query-controls-report@1"
ORIGIN = "independently_authored_receiver_controls"
PAGE_SCHEMA = "authored-inventory-evidence-page@1"
CURSOR_SCHEMA = "authored-inventory-evidence-cursor@1"
MAX_MANIFEST = 256 * 1024
MAX_FIXTURE = 1024 * 1024
MAX_SOURCE = 64 * 1024
MAX_TOTAL = 8 * 1024 * 1024
MAX_FILES = 66
MAX_UNITS = 64
MAX_RECORDS = 128
MAX_CASES = 32
MAX_PAGES = 16
MAX_PAGE_ROWS = 16
DISPOSITIONS = {"inferred", "deferred_budget", "opaque", "unindexed", "parse_failed",
                "parse_partial", "unsupported_target", "feature_incompatible"}
VERDICTS = {"proved", "refuted", "unknown", "timeout", "disagreement", "unsupported"}
UNIT_IDS = ("proved", "refuted_empty", "ambiguous", "deferred", "unsupported", "parse_failed", "opaque")
QUERY_IDS = ("full", "partial", "empty_budget", "empty_complete", "wrong_contract", "deferred_evidence")


class ReceiverRefusal(ValueError):
    """A closed fixture binding, population, or read safety check failed."""


def require(condition, message):
    if not condition:
        raise ReceiverRefusal(message)


def closed(value, fields, label):
    require(type(value) is dict and set(value) == set(fields), f"{label}: closed fields")


def integer(value, minimum, maximum, label):
    require(type(value) is int and minimum <= value <= maximum, f"{label}: bounded integer")


def digest(value, label):
    require(type(value) is str and len(value) == 64
            and all(char in "0123456789abcdef" for char in value), f"{label}: SHA256")


def string(value, label, maximum=4096):
    require(type(value) is str, f"{label}: bounded string")
    try:
        encoded = value.encode("utf-8")
    except UnicodeError as error:
        raise ReceiverRefusal(f"{label}: invalid UTF-8 string") from error
    require(0 < len(encoded) <= maximum, f"{label}: bounded string")


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("ascii")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def equal(left, right):
    """Canonical equality preserves integer/boolean distinctions."""
    return wire(left) == wire(right)


def document(raw, limit):
    require(len(raw) <= limit, "JSON byte bound")

    def pairs(rows):
        value = {}
        for key, item in rows:
            require(key not in value, "duplicate JSON key")
            value[key] = item
        return value

    def invalid_number(_):
        raise ReceiverRefusal("noninteger JSON number")

    try:
        value = json.loads(raw, object_pairs_hook=pairs, parse_float=invalid_number,
                           parse_constant=invalid_number)
    except ReceiverRefusal:
        raise
    except (UnicodeError, ValueError, RecursionError) as error:
        raise ReceiverRefusal("invalid bounded JSON") from error
    pending, count = [(value, 0)], 0
    while pending:
        item, depth = pending.pop()
        count += 1
        require(depth <= 32 and count <= 20000, "JSON structure bound")
        if type(item) is dict:
            pending.extend((child, depth + 1) for child in item.values())
        elif type(item) is list:
            pending.extend((child, depth + 1) for child in item)
        elif type(item) is int:
            require(abs(item) <= 2**63 - 1, "JSON integer magnitude bound")
        elif type(item) is str:
            try:
                item.encode("utf-8")
            except UnicodeError as error:
                raise ReceiverRefusal("JSON contains invalid UTF-8 string") from error
    require(type(value) is dict, "JSON object required")
    return value


def canonical_path(value):
    require(type(value) is str and value.startswith("/"), "absolute canonical input path")
    path = Path(value)
    require(str(path) == value and path.resolve(strict=False) == path, "noncanonical or symlinked input path")
    return path


def relative_path(value):
    string(value, "source relative path", 256)
    path = Path(value)
    require(not path.is_absolute() and str(path) == value
            and all(part not in {".", ".."} for part in path.parts), "source relative path")


class Capture:
    def __init__(self):
        self.raw = {}
        self.total = 0

    @staticmethod
    def read(path, limit):
        canonical_path(str(path))
        try:
            descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            with os.fdopen(descriptor, "rb") as stream:
                before = os.fstat(stream.fileno())
                require(stat.S_ISREG(before.st_mode), "input is not a regular file")
                require(before.st_size <= limit, "input size bound before allocation")
                raw = stream.read(limit + 1)
                after = os.fstat(stream.fileno())
                require(len(raw) == before.st_size and len(raw) <= limit, "input read byte bound")
                require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns,
                         before.st_ctime_ns) == (after.st_dev, after.st_ino, after.st_size,
                                                after.st_mtime_ns, after.st_ctime_ns), "input changed during read")
                return raw
        except OSError as error:
            raise ReceiverRefusal(f"input unavailable: {path}") from error

    def take(self, path, limit, pin=None):
        require(path not in self.raw, "aliased or duplicate input path")
        require(len(self.raw) < MAX_FILES, "selected file population bound")
        # Descriptor fstat sees the actual opened size, even after a growth race.
        remaining = MAX_TOTAL - self.total
        bounded_limit = min(limit, remaining, pin["bytes"] if pin is not None else limit)
        raw = self.read(path, bounded_limit)
        require(self.total + len(raw) <= MAX_TOTAL, "total input byte bound")
        if pin is not None:
            require(len(raw) == pin["bytes"] and sha(raw) == pin["sha256"], "selected raw input pin mismatch")
        self.raw[path] = (raw, len(raw))
        self.total += len(raw)
        return raw

    def stable(self):
        for path, (raw, limit) in self.raw.items():
            require(self.read(path, limit) == raw, "selected input changed after capture")


def descriptor(value, label, limit):
    closed(value, {"path", "sha256", "bytes"}, label)
    canonical_path(value["path"])
    digest(value["sha256"], label)
    integer(value["bytes"], 0, limit, label)


def validate_spec(spec):
    closed(spec, {"schema", "fixture_origin", "fixture", "sources"}, "input manifest")
    require(spec["schema"] == INPUT_SCHEMA and spec["fixture_origin"] == ORIGIN, "input profile identity")
    descriptor(spec["fixture"], "fixture", MAX_FIXTURE)
    require(type(spec["sources"]) is list and len(spec["sources"]) <= MAX_UNITS, "source descriptor population")
    ids, paths = set(), {spec["fixture"]["path"]}
    for row in spec["sources"]:
        closed(row, {"unit_id", "path", "sha256", "bytes"}, "source descriptor")
        string(row["unit_id"], "source unit id", 128)
        descriptor({key: row[key] for key in ("path", "sha256", "bytes")}, "source descriptor", MAX_SOURCE)
        require(row["unit_id"] not in ids and row["path"] not in paths, "duplicate source descriptor")
        ids.add(row["unit_id"])
        paths.add(row["path"])


def cursor(root, selector_sha, offset):
    return {"schema": CURSOR_SCHEMA, **root, "selector_sha256": selector_sha, "next_offset": offset}


def expected_case(fixture, case):
    """Independent assertion projection over a finite authored ledger, not a native query."""
    closed(case, {"query_id", "selector", "root", "page_size", "byte_budget", "response"}, "query case")
    string(case["query_id"], "query id", 128)
    selector = case["selector"]
    closed(selector, {"unit_ids", "contract_id", "domain_id"}, "query selector")
    require(type(selector["unit_ids"]) is list and len(selector["unit_ids"]) <= MAX_UNITS, "query member bound")
    string(selector["contract_id"], "query contract", 128)
    string(selector["domain_id"], "query domain", 128)
    inventory_ids = [row["unit_id"] for row in fixture["inventory"]["entries"]]
    wanted = selector["unit_ids"]
    require(all(type(item) is str for item in wanted) and len(wanted) == len(set(wanted))
            and wanted == [item for item in inventory_ids if item in wanted], "exact ordered query membership")
    integer(case["page_size"], 1, MAX_PAGE_ROWS, "page size")
    integer(case["byte_budget"], 0, MAX_FIXTURE, "query byte budget")
    root = fixture["query_root"]
    require(equal(case["root"], root), "query source/inventory/ledger/epoch root")
    matching = [row for row in fixture["evidence_ledger"]["records"]
                if row["unit_id"] in wanted and row["contract_id"] == selector["contract_id"]
                and row["domain_id"] == selector["domain_id"]]
    selector_sha = sha(wire(selector))
    pages, offset, retained_bytes = [], 0, 0
    while offset < len(matching):
        end = min(len(matching), offset + case["page_size"])
        page = {"schema": PAGE_SCHEMA, "root": root, "selector_sha256": selector_sha,
                "offset": offset, "records": matching[offset:end], "complete": end == len(matching),
                "next_cursor": None if end == len(matching) else cursor(root, selector_sha, end)}
        size = len(wire(page))
        if retained_bytes + size > case["byte_budget"]:
            break
        require(len(pages) < MAX_PAGES, "query page population bound")
        pages.append(page)
        retained_bytes += size
        offset = end
    complete = offset == len(matching)
    returned = [row for page in pages for row in page["records"]]
    summaries = []
    for unit_id in wanted:
        rows = [row for row in returned if row["unit_id"] == unit_id]
        disposition = ("matched_complete" if rows else "no_exact_indexed_conditional_evidence") if complete else (
            "matched_partial" if rows else "unknown_budget")
        summaries.append({"unit_id": unit_id, "evidence_disposition": disposition,
                          "record_ids": [row["record_id"] for row in rows], "ambiguous": len(rows) > 1,
                          "conditional_verdicts": [row["conditional_verdict"] for row in rows],
                          "applicability": [{"record_id": row["record_id"], **row["applicability"]} for row in rows]})
    planning = {"requirement_dispositions": [
        {"clause_id": row["clause_id"], "original_text": row["original_text"], "disposition": "residual"}
        for row in fixture["requirements"]], "task_ids": [row["task_id"] for row in fixture["requirements"]],
        "observed_runtime_facts": [], "omitted_task_ids": [], "execution_authority": False}
    return {"pages": pages, "complete": complete, "next_cursor": (
        pages[-1]["next_cursor"] if pages and not complete else None),
        "retained_query_bytes": retained_bytes, "stop_reason": "complete" if complete else "byte_budget",
        "member_summaries": summaries, "planning_materials": planning}


def validate_fixture(fixture, sources):
    closed(fixture, {"schema", "fixture_origin", "inventory", "shards", "evidence_ledger", "query_root",
                     "requirements", "query_cases", "proof_authority", "training_executed",
                     "current_authority_claimed"}, "fixture")
    require(fixture["schema"] == FIXTURE_SCHEMA and fixture["fixture_origin"] == ORIGIN, "fixture identity")
    for key in ("proof_authority", "training_executed", "current_authority_claimed"):
        require(fixture[key] is False, "fixture authority ceiling")
    inventory = fixture["inventory"]
    closed(inventory, {"profile", "source_head_sha256", "entries", "inventory_sha256"}, "inventory")
    require(inventory["profile"] == "authored-receiver-source-population@1", "inventory profile")
    entries = inventory["entries"]
    require(type(entries) is list and 1 <= len(entries) <= MAX_UNITS, "inventory population")
    ids, paths, retained_ids = [], set(), []
    for entry in entries:
        closed(entry, {"unit_id", "path", "source_sha256", "source_bytes", "inference_disposition", "shard_id"}, "inventory entry")
        string(entry["unit_id"], "inventory unit", 128)
        relative_path(entry["path"])
        require(entry["unit_id"] not in ids and entry["path"] not in paths, "duplicate inventory member")
        ids.append(entry["unit_id"])
        paths.add(entry["path"])
        require(type(entry["inference_disposition"]) is str
                and entry["inference_disposition"] in DISPOSITIONS, "inventory inference disposition")
        if entry["inference_disposition"] == "opaque":
            require(entry["source_sha256"] is None and entry["source_bytes"] is None,
                    "opaque source availability must be explicit")
        else:
            digest(entry["source_sha256"], "inventory source")
            integer(entry["source_bytes"], 0, MAX_SOURCE, "inventory source bytes")
            require(entry["unit_id"] in sources, "missing selected source body")
            path, raw = sources[entry["unit_id"]]
            require(path == entry["path"] and sha(raw) == entry["source_sha256"]
                    and len(raw) == entry["source_bytes"], "exact source body membership")
            retained_ids.append(entry["unit_id"])
        if entry["inference_disposition"] == "inferred":
            string(entry["shard_id"], "inference shard", 128)
        else:
            require(entry["shard_id"] is None, "non-inferred shard membership")
    require(list(sources) == retained_ids, "exact ordered selected source population")
    require(ids == list(UNIT_IDS), "closed authored control member population")
    source_projection = [{key: row[key] for key in ("unit_id", "path", "source_sha256", "source_bytes")} for row in entries]
    require(inventory["source_head_sha256"] == sha(wire({"profile": inventory["profile"], "entries": source_projection})),
            "authored exact source head")
    require(inventory["inventory_sha256"] == sha(wire({key: inventory[key] for key in ("profile", "source_head_sha256", "entries")})),
            "authored exact inventory root")
    shards = fixture["shards"]
    require(type(shards) is list and len(shards) <= MAX_PAGES, "shard population")
    shard_ids, inferred = [], []
    for shard in shards:
        closed(shard, {"shard_id", "unit_ids"}, "shard")
        string(shard["shard_id"], "shard id", 128)
        require(shard["shard_id"] not in shard_ids and type(shard["unit_ids"]) is list
                and 1 <= len(shard["unit_ids"]) <= MAX_PAGE_ROWS, "unique bounded shard")
        expected = [row["unit_id"] for row in entries if row["shard_id"] == shard["shard_id"]]
        require(equal(shard["unit_ids"], expected), "exact ordered shard membership")
        shard_ids.append(shard["shard_id"])
        inferred.extend(shard["unit_ids"])
    require(inferred == [row["unit_id"] for row in entries if row["inference_disposition"] == "inferred"],
            "complete ordered inferred shard population")
    ledger = fixture["evidence_ledger"]
    closed(ledger, {"evidence_epoch", "records", "ledger_sha256"}, "evidence ledger")
    integer(ledger["evidence_epoch"], 0, 2**31 - 1, "evidence epoch")
    require(type(ledger["records"]) is list and len(ledger["records"]) <= MAX_RECORDS, "evidence population")
    record_ids = set()
    for row in ledger["records"]:
        closed(row, {"record_id", "unit_id", "contract_id", "domain_id", "conditional_verdict", "applicability"}, "evidence record")
        for key in ("record_id", "unit_id", "contract_id", "domain_id"):
            string(row[key], f"evidence {key}", 128)
        require(row["record_id"] not in record_ids and row["unit_id"] in retained_ids, "exact unique evidence member")
        record_ids.add(row["record_id"])
        require(type(row["conditional_verdict"]) is str and row["conditional_verdict"] in VERDICTS, "conditional verdict")
        closed(row["applicability"], {"premises", "requested_domain"}, "applicability")
        require(type(row["applicability"]["premises"]) is str
                and type(row["applicability"]["requested_domain"]) is str
                and row["applicability"]["premises"] in {"satisfiable", "unsatisfiable", "unknown"}
                and row["applicability"]["requested_domain"] in {"covered", "uncovered", "empty", "unknown"}, "applicability status")
    require(ledger["ledger_sha256"] == sha(wire({key: ledger[key] for key in ("evidence_epoch", "records")})), "sealed authored evidence ledger")
    expected_root = {"source_head_sha256": inventory["source_head_sha256"],
                     "inventory_sha256": inventory["inventory_sha256"],
                     "ledger_sha256": ledger["ledger_sha256"], "evidence_epoch": ledger["evidence_epoch"]}
    require(equal(fixture["query_root"], expected_root), "query root exact identities")
    requirements = fixture["requirements"]
    require(type(requirements) is list and 1 <= len(requirements) <= 32, "requirement ledger bound")
    clause_ids, task_ids = set(), set()
    for row in requirements:
        closed(row, {"clause_id", "original_text", "task_id"}, "original requirement")
        for key in row:
            string(row[key], f"requirement {key}")
        require(row["clause_id"] not in clause_ids and row["task_id"] not in task_ids, "unique requirement/task meanings")
        clause_ids.add(row["clause_id"])
        task_ids.add(row["task_id"])
    cases = fixture["query_cases"]
    require(type(cases) is list and 1 <= len(cases) <= MAX_CASES, "query case population")
    require([case.get("query_id") for case in cases if type(case) is dict] == list(QUERY_IDS),
            "closed authored query control population")
    query_ids, reviewed = set(), []
    for case in cases:
        expected = expected_case(fixture, case)
        require(case["query_id"] not in query_ids, "duplicate query case")
        query_ids.add(case["query_id"])
        require(equal(case["response"], expected), f"query response rederivation: {case['query_id']}")
        reviewed.append({"query_id": case["query_id"], "selector": case["selector"], **expected})
    require(len(reviewed[0]["pages"]) >= 2 and reviewed[0]["complete"] is True
            and reviewed[1]["complete"] is False and len(reviewed[1]["pages"]) == 1
            and reviewed[2]["complete"] is False and not reviewed[2]["pages"]
            and reviewed[3]["complete"] is True and not reviewed[3]["pages"]
            and reviewed[4]["complete"] is True and not reviewed[4]["pages"]
            and reviewed[5]["complete"] is True, "required complete/partial/empty receiving coverage")
    return {"inventory_unit_count": len(entries), "retained_source_count": len(retained_ids),
            "inferred_unit_count": len(inferred),
            "deferred_unit_count": sum(row["inference_disposition"] == "deferred_budget" for row in entries),
            "opaque_unit_count": sum(row["inference_disposition"] == "opaque" for row in entries),
            "query_case_count": len(cases), "complete_query_case_count": sum(row["complete"] for row in reviewed),
            "partial_query_case_count": sum(not row["complete"] for row in reviewed),
            "empty_budget_query_case_count": sum(not row["complete"] and not row["pages"] for row in reviewed),
            "retained_page_count": sum(len(row["pages"]) for row in reviewed),
            "ambiguous_member_count": sum(member["ambiguous"] for row in reviewed for member in row["member_summaries"]),
            "query_cases": reviewed, "source_head_sha256": inventory["source_head_sha256"],
            "inventory_sha256": inventory["inventory_sha256"], "evidence_ledger_sha256": ledger["ledger_sha256"]}


def mutations(fixture):
    """Probe rehashed response forgeries against independent source and ledger anchors."""
    cases = []

    def add(name, change):
        value = copy.deepcopy(fixture)
        change(value)
        cases.append((name, value))

    def response(value, index=0):
        return value["query_cases"][index]["response"]

    def page(value):
        return response(value)["pages"][0]

    def record(value):
        return page(value)["records"][0]

    add("missing_inventory_member", lambda v: v["inventory"]["entries"].pop())
    add("duplicate_inventory_member", lambda v: v["inventory"]["entries"].append(copy.deepcopy(v["inventory"]["entries"][0])))
    add("reordered_shard", lambda v: v["shards"][0]["unit_ids"].reverse())
    add("missing_shard", lambda v: v["shards"].pop())
    add("deferred_joined_to_shard", lambda v: v["shards"][0]["unit_ids"].append("deferred"))
    add("wrong_source_body_pin", lambda v: v["inventory"]["entries"][0].update(source_sha256="0" * 64))
    add("opaque_body_invented", lambda v: v["inventory"]["entries"][-1].update(source_sha256="0" * 64, source_bytes=0))
    add("numeric_authority_alias", lambda v: v.update(proof_authority=0))
    add("authority_granted", lambda v: v.update(current_authority_claimed=True))
    add("missing_page", lambda v: response(v)["pages"].pop(0))
    add("duplicate_page", lambda v: response(v)["pages"].append(copy.deepcopy(page(v))))
    add("out_of_order_pages", lambda v: response(v)["pages"].reverse())
    add("wrong_page_head", lambda v: page(v)["root"].update(source_head_sha256="0" * 64))
    add("wrong_page_inventory", lambda v: page(v)["root"].update(inventory_sha256="0" * 64))
    add("wrong_page_epoch", lambda v: page(v)["root"].update(evidence_epoch=0))
    add("wrong_page_selector", lambda v: page(v).update(selector_sha256="0" * 64))
    add("wrong_cursor_root", lambda v: page(v)["next_cursor"].update(ledger_sha256="0" * 64))
    add("wrong_cursor_offset", lambda v: page(v)["next_cursor"].update(next_offset=0))
    add("duplicate_record", lambda v: page(v)["records"].append(copy.deepcopy(record(v))))
    add("wrong_record_source", lambda v: record(v).update(unit_id="deferred"))
    add("wrong_record_contract", lambda v: record(v).update(contract_id="other"))
    add("forged_conditional_status", lambda v: record(v).update(conditional_verdict="refuted"))
    add("forged_applicability", lambda v: record(v)["applicability"].update(requested_domain="empty"))
    def correlated_forgery(value):
        record(value)["conditional_verdict"] = "refuted"
        response(value)["member_summaries"][0]["conditional_verdicts"] = ["refuted"]
        response(value)["retained_query_bytes"] = sum(len(wire(item)) for item in response(value)["pages"])

    add("correlated_record_summary_forgery", correlated_forgery)
    add("partial_claims_complete", lambda v: response(v, 1).update(complete=True, stop_reason="complete", next_cursor=None))
    add("partial_invents_absence", lambda v: response(v, 1)["member_summaries"][-1].update(evidence_disposition="no_exact_indexed_conditional_evidence"))
    add("empty_budget_invents_absence", lambda v: response(v, 2)["member_summaries"][0].update(evidence_disposition="no_exact_indexed_conditional_evidence"))
    add("empty_budget_invents_cursor", lambda v: response(v, 2).update(next_cursor=copy.deepcopy(page(v)["next_cursor"])))
    add("empty_budget_charges_unretained_bytes", lambda v: response(v, 2).update(retained_query_bytes=1))
    add("boolean_complete_alias", lambda v: response(v).update(complete=1))
    add("ambiguous_record_hidden", lambda v: response(v)["member_summaries"][2].update(ambiguous=False, record_ids=["ambiguous-proved"]))
    add("runtime_fact_from_conditional_evidence", lambda v: response(v)["planning_materials"].update(observed_runtime_facts=["fact"]))
    add("task_omission", lambda v: response(v)["planning_materials"]["task_ids"].pop())
    add("original_instruction_changed", lambda v: response(v)["planning_materials"]["requirement_dispositions"][0].update(original_text="replacement"))
    add("residual_erased", lambda v: response(v)["planning_materials"]["requirement_dispositions"].pop())
    add("execution_authority_numeric_alias", lambda v: response(v)["planning_materials"].update(execution_authority=0))
    add("query_members_reordered", lambda v: v["query_cases"][0]["selector"]["unit_ids"].reverse())
    add("query_members_duplicated", lambda v: v["query_cases"][0]["selector"]["unit_ids"].append("proved"))
    return cases


def controls(fixture, sources):
    results = []
    for name, changed in mutations(fixture):
        try:
            validate_fixture(changed, sources)
        except ReceiverRefusal as error:
            results.append({"control": name, "refused": True, "reason": str(error),
                            "rehashed_fixture_sha256": sha(wire(changed))})
        else:
            raise ReceiverRefusal(f"mutation control accepted: {name}")
    return results


def output_preflight(output, spec_path, spec):
    path = Path(output).absolute()
    require(path.resolve(strict=False) == path and not path.exists() and not path.is_symlink(), "fresh canonical output required")
    fixture_root = canonical_path(spec["fixture"]["path"]).parent
    require(path != fixture_root and fixture_root not in path.parents, "output is inside fixture scope")
    for selected in [spec_path, canonical_path(spec["fixture"]["path"]),
                     *(canonical_path(row["path"]) for row in spec["sources"])]:
        require(path != selected and path not in selected.parents, "output overlaps selected input")
    return path


def run(manifest, output):
    capture = Capture()
    manifest = canonical_path(str(Path(manifest).absolute()))
    spec_raw = capture.take(manifest, MAX_MANIFEST)
    spec = document(spec_raw, MAX_MANIFEST)
    validate_spec(spec)
    output = output_preflight(output, manifest, spec)
    fixture_path = canonical_path(spec["fixture"]["path"])
    fixture_raw = capture.take(fixture_path, MAX_FIXTURE, spec["fixture"])
    fixture = document(fixture_raw, MAX_FIXTURE)
    sources = {}
    for row in spec["sources"]:
        path = canonical_path(row["path"])
        require(fixture_path.parent in path.parents, "source body outside selected fixture root")
        sources[row["unit_id"]] = (path.relative_to(fixture_path.parent).as_posix(), capture.take(path, MAX_SOURCE, row))
    summary = validate_fixture(fixture, sources)
    probes = controls(fixture, sources)
    capture.stable()
    output.mkdir(parents=True)
    retained = output / "retained"
    retained.mkdir()
    copies = []
    for index, (path, (raw, limit)) in enumerate(capture.raw.items()):
        destination = retained / f"input-{index:03d}{path.suffix}"
        destination.write_bytes(raw)
        require(Capture.read(destination, limit) == raw, "retained copy mismatch")
        copies.append({"original_path": str(path), "retained_path": str(destination),
                       "sha256": sha(raw), "bytes": len(raw)})
    capture.stable()
    for copied in copies:
        raw = Capture.read(Path(copied["retained_path"]), copied["bytes"])
        require(sha(raw) == copied["sha256"] and len(raw) == copied["bytes"], "retained copy changed")
    report = {"schema": REPORT_SCHEMA, "status": "passed", "fixture_origin": ORIGIN,
              "manifest_sha256": sha(spec_raw), "fixture_sha256": sha(fixture_raw),
              "input_files_unchanged": True, "authored_receiver_conformance": True,
              "native_export_adoption": "unavailable_no_complete_native_export_selected",
              "native_export_adoption_qualified": False, "native_execution_performed": False,
              "training_executed": False, "current_authority_claimed": False,
              "owner_database_opened": False, "profile_keys_read": False,
              "production_acceptance_claimed": False, "signature_authentication_performed": False,
              "numerical_state_replayed": False, "runtime_fact_count": 0, "tasks_omitted_count": 0,
              "additional_attempted_training_epochs": 0, "input_file_count": len(capture.raw),
              "input_bytes": capture.total, "mutation_control_count": len(probes),
              "mutation_controls": probes, "selected_input_pins": copies, **summary,
              "limitations": ["All inventory, ledger, pages and outcomes are independently authored assertion data.",
                              "No native query, checker, source execution, inference or admission was performed.",
                              "Rehashing all independent anchors cannot authenticate producer origin or numerical truth.",
                              "This receiving profile does not certify production codecs, durable recovery or eligibility."]}
    (output / "inventory_query_controls.json").write_bytes(wire(report) + b"\n")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        report = run(args.manifest, args.output)
    except (ReceiverRefusal, OSError) as error:
        print(f"inventory query controls refused: {error}", file=sys.stderr)
        return 2
    print(json.dumps({"status": report["status"], "query_case_count": report["query_case_count"],
                      "mutation_control_count": report["mutation_control_count"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
