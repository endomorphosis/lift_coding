"""Reconcile retained native batch pages and original clause custody offline.

No catalog, database, solver, restart child, model, scheduler or owner module is
opened. This fixed receiving profile checks exported records against separately
pinned historical counterparts; it does not authenticate their execution.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

if __package__:
    from . import native_receiver as codec
else:
    import native_receiver as codec

INPUT_SCHEMA = "codebase-ir-native-batch-query-input@1"
REPORT_SCHEMA = "codebase-ir-native-batch-query-receiving-report@1"
QUALIFICATION_SHA256 = "4583941a4b6e5e557549c5627b3111cd8d4640b9ad5885bc5b809a52506c4cbe"
QUALIFICATION_BYTES = 82220
MAX_FILE = 2 * 1024 * 1024
MAX_TOTAL = 8 * 1024 * 1024
MAX_FILES = 6
ROLES = {"native_result": "native-8-final/result.json", "restart_request": "native-8-final/restart-request.json",
         "restart_response": "native-8-final/restart.stdout", "source_snapshot": "source-snapshot.json"}
FALSE_FLAGS = (*codec.FALSE_FLAGS, "review_custody_verified", "request_execution_custody_verified",
               "batch_resource_execution_qualified", "throughput_improvement_qualified")
MATCH_FALSE = {"admission_authority", "authoritative_cache_eligible", "behavioral_satisfaction", "completion_authority",
               "execution_authority", "kernel_checked", "mutation_authority", "proof_authority", "recorded_execution_attested",
               "runtime_behavior_verified", "semantic_alignment_verified", "source_semantics_verified"}
EMPTY_FACTS = ("behavioral_satisfied_requirements", "current_behavioral_facts", "current_facts", "eligible_requirements",
               "removed_task_ids", "runtime_refutations")
QUERY_FIELDS = {"admission_authority", "authoritative_cache_eligible", "behavioral_satisfaction", "completion_authority", "contract",
                "contract_cid", "domain", "domain_cid", "execution_authority", "free_text_semantics_verified", "intent_document_json",
                "intent_source_ledger", "intent_source_sha256", "intent_source_text", "interpretation_scope", "kernel_checked",
                "mutation_authority", "native_document_sha256", "path", "producer", "profile", "proof_authority", "query_cid",
                "reasons", "requirement_ids", "review_custody_verified", "runtime_behavior_verified", "schema",
                "semantic_alignment_verified", "source_semantics_verified", "statement", "statement_id", "supported"}
PROFILE = "typed-straight-line-int-bool-linear@1"


class Capture:
    def __init__(self):
        self.raw, self.total = {}, 0

    def take(self, path, pin=None, limit=MAX_FILE):
        codec.require(path not in self.raw and len(self.raw) < MAX_FILES, "duplicate batch input or file count bound")
        allowance = min(limit, MAX_TOTAL - self.total, pin["bytes"] if pin else limit)
        raw = codec.OriginalCapture.read(path, allowance)
        codec.require(len(raw) <= allowance, "aggregate batch input byte bound")
        if pin:
            codec.require(len(raw) == pin["bytes"] and codec.sha(raw) == pin["sha256"], "raw selected batch input pin")
        self.raw[path] = raw
        self.total += len(raw)
        return raw

    def stable(self):
        for path, raw in self.raw.items():
            codec.require(codec.OriginalCapture.read(path, len(raw)) == raw, "batch input changed after capture")


def without(value, field):
    return {name: child for name, child in value.items() if name != field}


def header(head):
    codec.closed(head, {"schema", "repository_id", "generation", "manifest_cid", "receipt_cid", "snapshot_cid", "ast_revision_id"}, "source head")
    codec.require(head["schema"] == "codebase-head@1" and type(head["generation"]) is int and head["generation"] > 0, "typed source head")
    return codec.cid(head)


def page(value, head, inventory, epoch, start=None):
    codec.closed(value, {"authority", "complete", "entries", "epoch", "head", "head_cid", "inventory_cid", "next_cursor", "page_cid",
                         "schema", "selector", "selector_cid", "start_cursor"}, "retained native page")
    codec.require(value["schema"] == "codebase-verification-query-page@1" and value["head_cid"] == header(head)
                  and codec.equal(value["head"], head) and value["inventory_cid"] == inventory
                  and type(value["epoch"]) is int and value["epoch"] == epoch
                  and codec.equal(value["start_cursor"], start), "page source/inventory/epoch/start identity")
    codec.require(value["page_cid"] == codec.cid(without(value, "page_cid")), "page content CID")
    codec.require(type(value["complete"]) is bool and value["complete"] == (value["next_cursor"] is None), "page completeness/frontier")
    codec.closed(value["authority"], codec.EVIDENCE_FALSE | {"historical_conditional_evidence"}, "native page authority")
    codec.require(value["authority"]["historical_conditional_evidence"] is True
                  and all(value["authority"][name] is False for name in codec.EVIDENCE_FALSE), "page authority ceiling")
    selector = value["selector"]
    codec.closed(selector, {"schema", "path", "contract_id", "expected_contract_cid", "requested_domain_id", "requested_domain_cid",
                           "verification_cid", "canonical_key_id", "dependency_kind", "dependency_value"}, "native selector")
    codec.require(selector["schema"] == "codebase-verification-selector@1" and value["selector_cid"] == codec.cid(selector), "selector content CID")
    codec.require(type(value["entries"]) is list and len(value["entries"]) <= 64, "receiving page entry bound")
    previous = None
    for row in value["entries"]:
        codec.closed(row, {"applicability_cid", "canonical_key_ids", "contract_cid", "contract_id", "domain_cid", "domain_id", "entry_id",
                           "path", "projection_cid", "verification_cid"}, "native page entry")
        codec.require(row["entry_id"] == codec.cid({"projection_cid": row["projection_cid"], "contract_id": row["contract_id"]})
                      and (previous is None or row["entry_id"] > previous), "query entry CID/order")
        previous = row["entry_id"]
        codec.require(type(row["canonical_key_ids"]) is list and row["canonical_key_ids"] == sorted(set(row["canonical_key_ids"])), "canonical key membership order")
        for name, other in (("path", "path"), ("contract_id", "contract_id"), ("expected_contract_cid", "contract_cid"),
                            ("requested_domain_id", "domain_id"), ("requested_domain_cid", "domain_cid"), ("verification_cid", "verification_cid")):
            codec.require(selector[name] is None or selector[name] == row[other], "exact selector/page correspondence")
        codec.require(selector["canonical_key_id"] is None or selector["canonical_key_id"] in row["canonical_key_ids"], "selected native canonical key")
    for cursor, after in ((start, start["after"] if start else None), (value["next_cursor"], previous)):
        if cursor is not None:
            codec.closed(cursor, {"schema", "after", "epoch", "head_cid", "inventory_cid", "selector_cid"}, "retained native cursor")
            codec.require(cursor["schema"] == "codebase-verification-query-cursor@1" and cursor["head_cid"] == header(head)
                          and cursor["inventory_cid"] == inventory and type(cursor["epoch"]) is int and cursor["epoch"] == epoch
                          and cursor["selector_cid"] == value["selector_cid"] and cursor["after"] == after,
                          "cursor source/inventory/epoch/selector/position binding")
    if start and value["entries"]:
        codec.require(value["entries"][0]["entry_id"] > start["after"], "resumed cursor does not advance")
    if value["next_cursor"] is not None:
        codec.require(value["entries"], "nonterminal empty page")


def fixture_selector(position, identity):
    """Fixed captured fixture correspondence; this does not issue an owner query."""
    value = dict.fromkeys(("path", "contract_id", "expected_contract_cid", "requested_domain_id", "requested_domain_cid",
                          "verification_cid", "canonical_key_id", "dependency_kind", "dependency_value"))
    value["schema"] = "codebase-verification-selector@1"
    if position % 3 == 0:
        value["canonical_key_id"] = identity["key_id"]
    elif position % 3 == 1:
        value.update(dependency_kind="source", dependency_value=identity["source_cid"])
    else:
        value.update(path=identity["path"], contract_id=identity["contract_id"])
    return value


def pages(values, count, identities, head, inventory, epoch):
    codec.require(type(values) is list and len(values) == count and count in {1, 8, 32}, "ordered request/page population")
    for position, value in enumerate(values):
        page(value, head, inventory, epoch)
        identity = identities[position % 8]
        codec.require(value["complete"] is True and len(value["entries"]) == 1, "selected exact fixture page not complete")
        codec.require(codec.equal(value["selector"], fixture_selector(position, identity)), "ordered fixture request/selector binding")
        row = value["entries"][0]
        for name in ("path", "contract_id", "contract_cid", "domain_id", "domain_cid", "projection_cid", "verification_cid"):
            codec.require(row[name] == identity[name], "native source/contract/domain/projection identity")
        codec.require(identity["key_id"] in row["canonical_key_ids"], "fixture proof key missing")


def custody(query):
    codec.closed(query, QUERY_FIELDS, "captured requirement query")
    codec.require(query["schema"] == "supervisor-conditional-codebase-query@1" and query["profile"] == PROFILE
                  and query["query_cid"] == codec.cid(without(query, "query_cid")), "requirement query profile/CID")
    for name in (MATCH_FALSE - {"recorded_execution_attested"}) | {"free_text_semantics_verified", "review_custody_verified"}:
        codec.require(query[name] is False, "requirement query authority ceiling")
    codec.require(type(query["supported"]) is bool and query["interpretation_scope"] == "explicit_reviewed_native_mathematical_atom_only", "conditional interpretation scope")
    text, document_json = query["intent_source_text"], query["intent_document_json"]
    codec.require(type(text) is str and len(text.encode("utf-8")) <= 64 * 1024 and type(document_json) is str
                  and len(document_json.encode("utf-8")) <= 256 * 1024, "original requirement text/document bound")
    codec.require(codec.sha(text.encode("utf-8")) == query["intent_source_sha256"]
                  and codec.sha(document_json.encode("utf-8")) == query["native_document_sha256"], "original text/document SHA")
    doc = codec.document(document_json.encode("utf-8"), 256 * 1024)
    codec.require(doc["schema_version"] == "intent-ir/v1" and type(doc["statements"]) is list
                  and 1 <= len(doc["statements"]) <= 32 and type(doc["sources"]) is list and len(doc["sources"]) <= 64, "captured native intent population")
    statements, refs = {}, {}
    for row in doc["statements"]:
        name = row["statement_id"]
        codec.require(type(name) is str and name not in statements and row["modality"] == "required", "complete normative statement identity")
        statements[name] = row
    codec.require(query["requirement_ids"] == list(statements) and query["statement_id"] in statements, "complete original clause membership/order")
    selected = statements[query["statement_id"]]
    codec.require(type(query["statement"]) is dict and query["statement"]
                  == {name: selected[name] for name in ("arguments", "kind", "modality", "predicate", "source_ref_ids", "statement_id")}, "selected statement corresponds to original document")
    ledger = query["intent_source_ledger"]
    codec.require(type(ledger) is list and len(ledger) == len(doc["sources"]), "complete original source ledger")
    span_records = {}
    for row, source in zip(ledger, doc["sources"], strict=True):
        codec.closed(row, {"original_text", "reference_json"}, "original source ledger row")
        ref = codec.document(row["reference_json"].encode("utf-8"), 64 * 1024)
        codec.require(codec.equal(ref, source), "original reference differs from captured intent source")
        codec.require(ref["ref_id"] not in refs and ref["content_sha256"] == query["intent_source_sha256"], "source reference identity/hash")
        span = ref["span"]
        codec.closed(span, {"start_char", "end_char"}, "original character span")
        codec.integer(span["start_char"], 0, len(text), "span start")
        codec.integer(span["end_char"], span["start_char"] + 1, len(text), "span end")
        codec.require(text[span["start_char"]:span["end_char"]] == row["original_text"], "original clause span text")
        refs[ref["ref_id"]] = row["original_text"]
        byte_start = len(text[:span["start_char"]].encode("utf-8"))
        byte_end = len(text[:span["end_char"]].encode("utf-8"))
        raw_slice = text.encode("utf-8")[byte_start:byte_end]
        codec.require(raw_slice == row["original_text"].encode("utf-8"), "original UTF-8 byte span differs")
        span_records[ref["ref_id"]] = {"ref_id": ref["ref_id"], "character_span": span,
                                       "byte_span": {"start_byte": byte_start, "end_byte": byte_end},
                                       "source_slice_sha256": codec.sha(raw_slice)}
    for row in statements.values():
        codec.require(type(row["source_ref_ids"]) is list and row["source_ref_ids"]
                      and len(set(row["source_ref_ids"])) == len(row["source_ref_ids"])
                      and all(name in refs for name in row["source_ref_ids"]), "statement original source references")
    if query["supported"]:
        codec.require(selected["predicate"] == "conditional_int_bool_property"
                      and query["contract_cid"] == codec.cid(query["contract"])
                      and query["domain_cid"] == codec.cid(query["domain"]), "selected mathematical contract/domain correspondence")
        codec.require(selected["arguments"] == [query["path"], query["contract"]["function_name"], query["contract_cid"], query["domain_cid"], PROFILE], "selected mathematical statement bindings")
    return [{"statement_id": name, "modality": row["modality"], "predicate": row["predicate"],
             "original_source_ref_ids": row["source_ref_ids"], "original_clause_texts": [refs[ref] for ref in row["source_ref_ids"]],
             "original_source_spans": [span_records[ref] for ref in row["source_ref_ids"]],
             "selected_for_mathematical_lookup": name == query["statement_id"], "runtime_behavior": "unresolved"} for name, row in statements.items()]


def requirements(value, individual, head, inventory, epoch):
    codec.require(value["schema"] == "supervisor-conditional-codebase-batch@1" and value["profile"] == PROFILE
                  and value["batch_cid"] == codec.cid(without(value, "batch_cid")), "supervisor batch profile/CID")
    codec.require(value["complete_input_ledger"] is True and codec.equal(value["head"], head) and value["head_cid"] == header(head)
                  and codec.equal(value["inventory"], {"epoch": epoch, "inventory_cid": inventory}), "complete requirement ledger/head/inventory")
    for name in MATCH_FALSE:
        codec.require(value[name] is False, "supervisor batch authority ceiling")
    for name in EMPTY_FACTS:
        codec.require(type(value[name]) is list and value[name] == [], "conditional result became facts, refutations or omitted tasks")
    ids = [f"request-{index}" for index in range(4)]
    codec.require(value["requested_requirement_ids"] == ids and type(value["matches"]) is list and len(value["matches"]) == 4
                  and [row["requirement_id"] for row in value["matches"]] == ids
                  and codec.equal([row["match"] for row in value["matches"]], individual), "ordered batch/individual requirement equivalence")
    clauses, residuals, dispositions = [], [], []
    expected = ("recorded_conditional_proved", "recorded_conditional_refuted", "recorded_conditional_vacuous", "unknown")
    for index, wrapper in enumerate(value["matches"]):
        codec.closed(wrapper, {"requirement_id", "match"}, "complete requirement disposition")
        match = wrapper["match"]
        codec.require(match["schema"] == "supervisor-conditional-codebase-evidence@1" and match["profile"] == PROFILE
                      and match["match_cid"] == codec.cid(without(match, "match_cid")) and codec.equal(match["head"], head)
                      and match["head_cid"] == header(head) and match["current_root_id"] == head["snapshot_cid"], "individual match profile/CID/head")
        for name in MATCH_FALSE:
            codec.require(match[name] is False, "individual match authority ceiling")
        for name in EMPTY_FACTS:
            codec.require(type(match[name]) is list and match[name] == [], "individual match granted runtime authority")
        query = match["query"]
        rows = custody(query)
        codec.require(match["status"] == expected[index] and query["supported"] is (index < 3), "proved/refuted/vacuous/unsupported dispositions")
        if index < 3:
            codec.require(match["indexed_query_page"] is not None and match["evidence"] is not None, "supported requirement missing retained lookup")
            page(match["indexed_query_page"], head, inventory, epoch)
            evidence = match["evidence"]
            codec.require(evidence["historical_records_observed_live"] is False
                          and evidence["head_cid"] == header(head)
                          and evidence["contract_cid"] == query["contract_cid"] and evidence["domain_cid"] == query["domain_cid"], "conditional evidence exact requirement scope")
        else:
            codec.require(match["indexed_query_page"] is None and match["evidence"] is None, "unsupported requirement acquired evidence")
        expected_residuals = [{"statement_id": row["statement_id"], "selected_for_mathematical_lookup": row["selected_for_mathematical_lookup"],
                               "status": "runtime_behavior_unresolved"} for row in rows]
        codec.require(codec.equal(match["residual_requirements"], expected_residuals), "complete original clauses were omitted or resolved")
        residuals.extend({"requirement_id": wrapper["requirement_id"], **row} for row in expected_residuals)
        clauses.extend({"requirement_id": wrapper["requirement_id"], **row} for row in rows)
        dispositions.append({"requirement_id": wrapper["requirement_id"], "recorded_match_status": match["status"],
                             "selected_statement_id": query["statement_id"], "mathematical_lookup_supported": query["supported"],
                             "original_source_sha256": query["intent_source_sha256"], "native_document_sha256": query["native_document_sha256"],
                             "runtime_behavior": "unknown"})
    codec.require(len(clauses) == 8 and codec.equal(value["residual_requirements"], residuals), "all eight runtime clauses remain residual")
    return {"requirements": dispositions, "clause_ledger": clauses, "residual_requirements": residuals,
            "batch_cid": value["batch_cid"], "complete_input_ledger": True}


def receive(result, request, response, snapshot):
    codec.require(result["schema"] == "codebase-query-many-benchmark@1" and result["completed"] is True and result["errors"] == []
                  and type(result["checks"]) is dict and all(flag is True for flag in result["checks"].values()), "whole historical operation not completed")
    codec.closed(request, {"cursor", "directory", "head", "identities", "pages", "resumed_page", "source_pins"}, "retained cold request")
    codec.closed(response, {"completed", "measurements", "resumed_page", "source_pins", "process_audit", "saved_pool_after"}, "retained cold response")
    codec.require(response["completed"] is True and codec.equal(result["restart"], response), "separate original cold response differs from retained result")
    head, identities = result["head"], result["identities"]
    header(head)
    codec.require(codec.equal(request["head"], head) and codec.equal(request["identities"], identities)
                  and type(identities) is list and len(identities) == 8
                  and [row["path"] for row in identities] == [f"unit_{index:02d}.py" for index in range(8)], "ordered complete eight-unit identity ledger")
    codec.require(codec.equal(result["source_pins_before"], result["source_pins_after"])
                  and codec.equal(result["source_pins_before"], request["source_pins"])
                  and codec.equal(result["source_pins_before"], response["source_pins"])
                  and codec.equal(result["source_pins_before"], snapshot["native_source_pins"]), "recorded generation pins differ across independent captures")
    inventory = result["supervisor"]["batch"]["inventory"]["inventory_cid"]
    epoch = result["supervisor"]["batch"]["inventory"]["epoch"]
    codec.cid_shape(inventory)
    codec.integer(epoch, 1, 2**63 - 1, "inventory epoch")
    observations = result["measurements"]
    codec.require(type(observations) is list and len(observations) == 6
                  and [(row["round"], row["selectors"]) for row in observations] == [(round_id, count) for round_id in range(2) for count in (1, 8, 32)], "complete counterbalanced measurement population")
    summaries = []
    for row in observations:
        count = row["selectors"]
        codec.require(type(count) is int and type(row["round"]) is int and sorted(row["order"]) == ["batch", "individual"], "typed counterbalanced metadata")
        codec.require(codec.equal(row["individual"]["pages"], row["batch"]["pages"]), "ordered batch/individual page equivalence")
        pages(row["batch"]["pages"], count, identities, head, inventory, epoch)
        summaries.append({"round": row["round"], "selector_count": count, "page_count": count,
                          "page_cids": [value["page_cid"] for value in row["batch"]["pages"]], "counterbalanced_order": row["order"]})
    codec.require(codec.equal(request["pages"], response["measurements"]["pages"])
                  and codec.equal(request["pages"], observations[-1]["batch"]["pages"]), "request/response/warm ordered batch commitments")
    pages(response["measurements"]["pages"], 32, identities, head, inventory, epoch)
    codec.require(codec.equal(request["resumed_page"], response["resumed_page"])
                  and codec.equal(request["cursor"], response["resumed_page"]["start_cursor"]), "separate cold cursor request/response commitment")
    page(response["resumed_page"], head, inventory, epoch, request["cursor"])
    codec.require(response["resumed_page"]["complete"] is False and len(response["resumed_page"]["entries"]) == 3,
                  "retained resumed frontier must remain partial")
    ledger = requirements(result["supervisor"]["batch"], result["supervisor"]["individual_matches"], head, inventory, epoch)
    return {"head_cid": header(head), "inventory_cid": inventory, "epoch": epoch, "observations": summaries,
            "cold_response_page_cids": [value["page_cid"] for value in response["measurements"]["pages"]],
            "resumed_page_cid": response["resumed_page"]["page_cid"], "resume_frontier": "partial",
            "next_cursor": response["resumed_page"]["next_cursor"], **ledger}


def rehash_match(match):
    query = match["query"]
    query["query_cid"] = codec.cid(without(query, "query_cid"))
    match["match_cid"] = codec.cid(without(match, "match_cid"))


def controls(result, request, response, snapshot):
    results = []

    def run(name, mutate):
        changed = copy.deepcopy(result)
        mutate(changed)
        batch = changed["supervisor"]["batch"]
        for row in batch["matches"]:
            rehash_match(row["match"])
        batch["batch_cid"] = codec.cid(without(batch, "batch_cid"))
        for row in changed["measurements"]:
            for mode in ("individual", "batch"):
                for value in row[mode]["pages"]:
                    value["page_cid"] = codec.cid(without(value, "page_cid"))
        changed["restart"]["resumed_page"]["page_cid"] = codec.cid(without(changed["restart"]["resumed_page"], "page_cid"))
        try:
            receive(changed, request, response, snapshot)
        except (codec.ReceiverRefusal, KeyError, TypeError, ValueError) as error:
            results.append({"name": name, "container_cids_recomputed": True, "rejected": True, "reason": str(error)})
            return
        raise codec.ReceiverRefusal("batch negative control accepted: " + name)

    run("ordered_selector_reply_swapped", lambda value: value["measurements"][-1]["batch"]["pages"].reverse())
    run("last_request_omitted", lambda value: value["measurements"][-1]["batch"]["pages"].pop())
    run("duplicate_reply_appended", lambda value: value["measurements"][-1]["batch"]["pages"].append(copy.deepcopy(value["measurements"][-1]["batch"]["pages"][-1])))
    run("both_views_reordered_against_request", lambda value: [value["measurements"][-1][mode]["pages"].reverse() for mode in ("individual", "batch")])
    run("late_page_inventory_changed", lambda value: value["measurements"][-1]["batch"]["pages"][-1].update(inventory_cid=codec.cid({"other": "inventory"})))
    run("late_page_epoch_changed", lambda value: value["measurements"][-1]["batch"]["pages"][-1].update(epoch=10))
    run("late_page_source_changed", lambda value: value["measurements"][-1]["batch"]["pages"][-1].update(head_cid=codec.cid({"other": "head"})))
    run("source_generation_pin_changed", lambda value: value["source_pins_after"].update({next(iter(value["source_pins_after"])): "0" * 64}))
    run("incomplete_operation_withheld", lambda value: value.update(completed=False))
    run("unselected_integrity_check_refused", lambda value: value["checks"].update(integrity_and_source_controls=False))
    run("late_operation_error_withheld", lambda value: value["errors"].append({"message": "late integrity refusal"}))
    run("requirement_order_changed", lambda value: value["supervisor"]["batch"]["matches"].reverse())
    run("requirement_omitted", lambda value: value["supervisor"]["batch"]["matches"].pop())
    run("runtime_residual_omitted", lambda value: value["supervisor"]["batch"]["residual_requirements"].pop())
    run("runtime_residual_resolved", lambda value: value["supervisor"]["batch"]["residual_requirements"][0].update(status="proved"))
    run("unknown_became_proved", lambda value: value["supervisor"]["batch"]["matches"][3]["match"].update(status="recorded_conditional_proved"))
    run("runtime_fact_granted", lambda value: value["supervisor"]["batch"]["current_facts"].append({"requirement_id": "request-0"}))
    run("task_removed", lambda value: value["supervisor"]["batch"]["removed_task_ids"].append("task:request-0"))
    run("review_custody_promoted", lambda value: value["supervisor"]["batch"]["matches"][0]["match"]["query"].update(review_custody_verified=True))
    run("original_span_text_changed", lambda value: value["supervisor"]["batch"]["matches"][0]["match"]["query"]["intent_source_ledger"][0].update(original_text="Changed original clause."))
    run("original_selected_statement_substituted", lambda value: value["supervisor"]["batch"]["matches"][0]["match"]["query"].update(statement_id="runtime-goal"))
    run("authority_integer_false", lambda value: value["supervisor"]["batch"].update(proof_authority=0))
    run("cold_request_identity_substituted", lambda value: value["identities"][0].update(source_cid=codec.cid_bytes(b"other source")))
    run("cold_response_page_omitted", lambda value: value["restart"]["measurements"]["pages"].pop())
    run("cold_resumed_cursor_stale_epoch", lambda value: value["restart"]["resumed_page"]["start_cursor"].update(epoch=10))
    run("cold_resumed_frontier_false_complete", lambda value: value["restart"]["resumed_page"].update(complete=True, next_cursor=None))
    return results


def load_input(manifest):
    capture = Capture()
    raw = capture.take(manifest, limit=codec.MAX_MANIFEST)
    spec = codec.document(raw, codec.MAX_MANIFEST)
    codec.closed(spec, {"schema", "prior_qualification", *ROLES}, "batch input manifest")
    codec.require(spec["schema"] == INPUT_SCHEMA, "batch input schema")
    codec.descriptor(spec["prior_qualification"])
    anchor = spec["prior_qualification"]
    codec.require(anchor["sha256"] == QUALIFICATION_SHA256 and anchor["bytes"] == QUALIFICATION_BYTES, "fixed independent batch qualification anchor")
    qualification = codec.document(capture.take(codec.canonical_path(anchor["path"]), anchor))
    codec.require(qualification["schema"] == "codebase-query-many-qualification@1"
                  and qualification["status"] == "bounded_increment_qualified_production_exits_open"
                  and qualification["production_tasks_closed"] == [], "historical batch qualification scope")
    namespace = Path(spec["native_result"]["original_path"]).parent.parent
    bodies = {}
    for role, relative in ROLES.items():
        pin = spec[role]
        codec.descriptor(pin, original=True)
        codec.require(pin["original_path"] == str(namespace / relative)
                      and qualification["artifact_sha256"].get(relative) == pin["sha256"], "selected public batch role/anchor binding")
        bodies[role] = codec.document(capture.take(codec.canonical_path(pin["path"]), pin))
    codec.require(bodies["restart_request"]["directory"] == str(namespace / "native-8-final"), "captured cold request directory provenance")
    return capture, spec, bodies


def audit(manifest, output):
    manifest, output = codec.canonical_path(str(manifest)), codec.canonical_path(str(output))
    capture, spec, bodies = load_input(manifest)
    protected = {path.parent for path in capture.raw if path != manifest}
    protected.update(codec.canonical_path(spec[role]["original_path"]).parent for role in ROLES)
    codec.require(not output.exists() and all(output != path and path not in output.parents for path in protected), "fresh output outside selected input scopes required")
    result, request, response, snapshot = (bodies[role] for role in ROLES)
    received = receive(result, request, response, snapshot)
    negative = controls(result, request, response, snapshot)
    capture.stable()
    output.mkdir(parents=True, exist_ok=False)
    retained = output / "inputs"
    retained.mkdir()
    files = []
    for index, (path, raw) in enumerate(capture.raw.items()):
        destination = retained / f"{index:02d}-{path.name}"
        destination.write_bytes(raw)
        codec.require(codec.OriginalCapture.read(destination, len(raw)) == raw, "batch retained copy differs")
        files.append({"path": str(path), "retained_path": str(destination), "sha256": codec.sha(raw), "bytes": len(raw)})
    capture.stable()
    for row in files:
        codec.require(codec.sha(codec.OriginalCapture.read(Path(row["retained_path"]), row["bytes"])) == row["sha256"], "batch retained copy changed")
    report = {"schema": REPORT_SCHEMA, "status": "passed", "manifest_sha256": codec.sha(capture.raw[manifest]),
              "prior_qualification_sha256": spec["prior_qualification"]["sha256"],
              **{role + "_sha256": spec[role]["sha256"] for role in ROLES},
              "scope": "selected_historical_batch_records_and_original_clause_custody_not_owner_execution_or_authentication",
              "native_batch_receiving_conformance": True, "original_requirement_custody_reconciled": True,
              "restart_request_response_bindings_reconciled": True, "input_files_unchanged": True,
              **{name: False for name in FALSE_FLAGS}, "runtime_fact_count": 0, "tasks_omitted_count": 0,
              "additional_attempted_training_epochs": 0, "native_unit_count": 8, "measurement_count": 6,
              "batch_page_count": 82, "individual_page_count": 82, "cold_batch_page_count": 32, "resumed_page_count": 1,
              "requirement_count": 4, "clause_count": 8, "runtime_residual_count": 8,
              "supported_lookup_requirement_count": 3, "unsupported_lookup_requirement_count": 1,
              "mutation_control_count": len(negative), "input_file_count": len(files), "input_bytes": capture.total,
              "received": received, "input_files": files, "mutation_controls": negative,
              "recorded_producer_effort": {"qualification_status": "historical_producer_claims_only",
                  "native_wall_seconds": result["wall_seconds"], "native_phase_counts": result["native_phase_counts"],
                  "observations": [{"round": row["round"], "selector_count": row["selectors"],
                                    "individual_seconds": row["individual"]["seconds"], "batch_seconds": row["batch"]["seconds"],
                                    "individual_calls": row["individual"]["calls"], "batch_calls": row["batch"]["calls"]} for row in result["measurements"]],
                  "cold_batch_seconds": response["measurements"]["seconds"]},
              "limitations": ["The fixed qualification raw hash is an unsigned local anchor, not producer or execution authentication.",
                              "Ordered typed per-call request tuple bodies and original request page-size/budget ceilings were not exported; no request-budget enforcement or raw invocation custody is inferred.",
                              "Cold request directory and producer source paths are provenance labels; their databases, CAS objects, owner code and process event ledgers are never opened.",
                              "Original intent text/document/reference spans are structurally reconciled; human review status, free-text interpretation and source/runtime semantics remain unauthenticated.",
                              "Recorded conditional results are compared with retained individual matcher outputs; no solver, source assumptions or checker artifacts are replayed.",
                              "The resumed page is partial and carries a continuation; it establishes no complete absence frontier.",
                              "Historical timings and resource counters are retained as producer claims, without renewed execution, throughput or hard aggregate containment qualification."]}
    (output / "native_batch_query.json").write_bytes(codec.wire(report) + b"\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        report = audit(args.manifest, args.output)
    except (codec.ReceiverRefusal, KeyError, TypeError, ValueError, OSError, RecursionError) as error:
        print(json.dumps({"status": "refused", "reason": str(error)}), file=sys.stderr)
        return 1
    print(json.dumps({"status": "passed", "pages": report["batch_page_count"], "clauses": report["clause_count"], "controls": report["mutation_control_count"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
