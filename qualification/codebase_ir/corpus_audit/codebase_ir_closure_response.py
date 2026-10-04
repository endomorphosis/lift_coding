#!/usr/bin/env python3
"""Review proposed owner responses without granting native split closure authority."""
from __future__ import annotations

import argparse
import copy
import sys
from dataclasses import asdict, dataclass, replace
from pathlib import Path

import codebase_ir_closure_requests as handoff
import codebase_ir_corpus_audit as audit
import codebase_ir_source_metadata as metadata

RESPONSE_SCHEMA = "codebase-ir-proposed-owner-response@1"
REPORT_SCHEMA = "codebase-ir-owner-response-review@1"
SCOPE_SCHEMA = "codebase-ir-owner-response-captured-scope@1"
RELATIONS = {"dependency", "related_revision", "dependency_group_disjoint", "revision_family_disjoint"}
REQUEST_FIELDS = {"request_id", "source_identity", "affected_unit_ids", "missing_claims",
                  "native_target_bindings", "proposed_owner_inputs", "locally_recovered_facts_are_closure_certificate"}
HANDOFF_FIELDS = {"schema", "status", "input_manifest_sha256", "pinned_input_sha256", "baseline_audit_status",
                  "baseline_closure_issue_count", "closure_request_count", "recovered_manifest_count", "owner_fact_count",
                  "native_closure_certification_verified", "closure_claims_applied", "comparison_audit_status",
                  "comparison_closure_issue_count", "whole_repository_coverage", "unseen_rename_ancestry_verified",
                  "native_registry_receipts_verified", "training_executed", "promotion_decisions_made", "proof_authority",
                  "limits", "closure_requests", "other_missing_evidence", "recovery_frontier_count", "owner_facts_sha256", "scope"}


@dataclass(frozen=True)
class ResponseLimits:
    max_requests: int = 64
    max_observations: int = 512
    max_relations: int = 1024
    max_frontiers: int = 1024
    max_evidence_files: int = 32
    max_evidence_file_bytes: int = 1024 * 1024
    max_evidence_bytes: int = 8 * 1024 * 1024
    max_total_bytes: int = 64 * 1024 * 1024

    def __post_init__(self):
        audit._require(all(type(value) is int and value > 0 for value in asdict(self).values()),
                       "positive exact response budgets required")


DEFAULT_LIMITS = ResponseLimits()


def _sha_object(value):
    return audit._sha(audit._canonical(value))


def _list(value, maximum, label):
    audit._require(type(value) is list and len(value) <= maximum, f"bounded {label} list required")
    return value


def _ids(value, maximum, label):
    rows = _list(value, maximum, label)
    result = [audit._text(row, label, 1024) for row in rows]
    audit._require(len(result) == len(set(result)), f"duplicate {label}")
    return result


def _binding(request):
    return {"request_id": request["request_id"], "request_sha256": _sha_object(request),
            "source_identity": request["source_identity"], "affected_unit_ids": request["affected_unit_ids"],
            "native_target_bindings_sha256": _sha_object(request["native_target_bindings"])}


class _Bundle:
    def __init__(self, path, limits, audit_limits):
        self.path, self.limits, self.audit_limits = path, limits, audit_limits
        self.raw = audit._read_bounded(path, min(audit_limits.max_json_bytes, limits.max_total_bytes))
        self.report = audit._closed(audit._load_json(self.raw, audit_limits), HANDOFF_FIELDS, "closure handoff")
        audit._require(self.report["schema"] == handoff.REPORT_SCHEMA, "versioned closure handoff required")
        for field in ("native_closure_certification_verified", "whole_repository_coverage", "proof_authority",
                      "unseen_rename_ancestry_verified", "native_registry_receipts_verified", "training_executed",
                      "promotion_decisions_made"):
            audit._require(self.report[field] is False, "handoff must retain nonauthoritative scope")
        audit._require(type(self.report["closure_claims_applied"]) is int and self.report["closure_claims_applied"] == 0,
                       "handoff must not apply closure claims")
        for field in ("baseline_closure_issue_count", "closure_request_count", "recovered_manifest_count", "owner_fact_count",
                      "comparison_closure_issue_count", "recovery_frontier_count"):
            audit._require(type(self.report[field]) is int and self.report[field] >= 0, "exact handoff count required")
        audit._closed(self.report["limits"], set(asdict(handoff.DEFAULT_RECOVERY_LIMITS)), "handoff recovery limits")
        handoff.RecoveryLimits(**self.report["limits"])
        remaining = limits.max_total_bytes - len(self.raw)
        audit._require(remaining > 0, "response aggregate input byte budget exhausted")
        capture_limits = replace(audit_limits, max_json_bytes=min(audit_limits.max_json_bytes, remaining),
                                 max_total_json_bytes=min(audit_limits.max_total_json_bytes, remaining))
        self.captured = metadata._Captured(path.parent / "pinned_input.json", capture_limits)
        audit._require(audit._sha(self.captured.raw) == self.report["pinned_input_sha256"], "stale captured input binding")
        self.baseline = self.captured.audit_report
        audit._require(self.baseline["status"] == self.report["baseline_audit_status"]
                       and len(self.baseline["issues"]) == self.report["baseline_closure_issue_count"],
                       "handoff baseline disagrees with captured input")
        remaining -= self.captured.loader.json_bytes
        audit._require(remaining > 0, "response aggregate input byte budget exhausted")
        self.facts_raw = audit._read_bounded(path.parent / "owner_facts.json", min(audit_limits.max_json_bytes, remaining))
        audit._require(audit._sha(self.facts_raw) == self.report["owner_facts_sha256"], "stale owner facts binding")
        self.facts = audit._closed(audit._load_json(self.facts_raw, audit_limits),
                                   {"schema", "native_targets", "owner_facts", "retained_cas_artifacts",
                                    "retained_git_objects", "git_snapshot_bindings", "source_receipt_predecessors",
                                    "qualification_report", "recovery_frontiers", "native_closure_certification_verified",
                                    "proof_authority"}, "retained owner facts")
        audit._require(self.facts.get("schema") == handoff.FACTS_SCHEMA
                       and self.facts.get("native_closure_certification_verified") is False
                       and self.facts.get("proof_authority") is False, "nonauthoritative retained owner facts required")
        self.total = len(self.raw) + len(self.facts_raw) + self.captured.loader.json_bytes
        self.targets = self._targets()
        audit._require(self.facts.get("native_targets") == self.targets, "owner target inventory binding drift")
        units = self.captured.loader.units
        expected = {}
        for issue in self.baseline["issues"]:
            if issue["code"] not in {"dependencies_not_declared_complete", "revision_relations_not_declared_complete"}:
                continue
            unit = units[issue["unit_id"]]
            row = expected.setdefault(unit.identity(), {"ids": set(), "claims": set()})
            row["ids"].add(unit.id)
            row["claims"].add(issue["code"])
        self.requests = {}
        rows = _list(self.report["closure_requests"], limits.max_requests, "closure request")
        audit._require(len(rows) == len(expected) == self.report["closure_request_count"], "closure request inventory drift")
        for row in rows:
            audit._closed(row, REQUEST_FIELDS, "closure request")
            identity = audit._closed(row["source_identity"], {"repository_id", "path", "content_sha256"}, "source identity")
            audit._text(identity["repository_id"], "source repository")
            audit._relative_path(identity["path"], "source path")
            audit._digest(identity["content_sha256"], "source identity")
            key = tuple(identity[field] for field in ("repository_id", "path", "content_sha256"))
            audit._require(key in expected and row["affected_unit_ids"] == sorted(expected[key]["ids"])
                           and row["missing_claims"] == sorted(expected[key]["claims"]), "closure source inventory drift")
            request_id = "closure-request:" + _sha_object(identity)
            audit._require(row["request_id"] == request_id and request_id not in self.requests,
                           "duplicate or stale closure request identity")
            bound = [target for target in self.targets if units[target["unit_id"]].identity() == key]
            audit._require(row["native_target_bindings"] == bound, "closure native head/target binding drift")
            audit._require(row["locally_recovered_facts_are_closure_certificate"] is False,
                           "structural facts cannot certify closure")
            self.requests[request_id] = row
        self.scope = {"schema": SCOPE_SCHEMA, "requests_sha256": audit._sha(self.raw),
                      "pinned_input_sha256": audit._sha(self.captured.raw),
                      "units": self.baseline["units"], "native_target_bindings": self.targets,
                      "ancestry_complete_claim": self.captured.manifest["ancestry_complete"],
                      "whole_repository_coverage": False, "unseen_rename_ancestry_verified": False}
        self.scope_sha = _sha_object(self.scope)
        self.check_budget()

    def check_budget(self):
        audit._require(self.total <= self.limits.max_total_bytes, "response aggregate input byte budget exceeded")

    def _targets(self):
        targets = []
        for version, raw in sorted(self.captured.exports.items()):
            value = audit._load_json(raw, self.audit_limits)
            provenance = value if value.get("schema") == audit.NATIVE_LINEAGE_SCHEMA else value["report"]["codebase_provenance"]
            for field in ("training_targets", "tuning_targets", "canary_targets", "replay_targets"):
                for index, target in enumerate(provenance[field]):
                    binding = target["validation"][0]["details"]["source_binding"]
                    targets.append({"unit_id": f"native/{version}/{field}/{index}", "version_id": version,
                                    "batch_field": field, "index": index, "target_source_digest": target["source_digest"],
                                    "head": binding["head"], "head_sha256": _sha_object(binding["head"]),
                                    "source_binding": binding, "source_binding_sha256": _sha_object(binding),
                                    "export_sha256": audit._sha(raw)})
        return targets

    def binding(self):
        return {"requests_sha256": audit._sha(self.raw), "owner_facts_sha256": audit._sha(self.facts_raw),
                "pinned_input_sha256": audit._sha(self.captured.raw), "captured_scope_sha256": self.scope_sha}

    def template(self):
        responses = []
        for request in self.requests.values():
            observations = [{"unit_id": unit_id, "dependency_inventory_claim": "partial",
                             "revision_inventory_claim": "partial", "relations": [],
                             "evidence_ids": ["captured-owner-facts"], "frontiers": [
                                 {"code": "native_closure_not_certified", "detail": "Retained structural facts leave owner closure unreviewed."}]}
                            for unit_id in request["affected_unit_ids"]]
            responses.append({"request_binding": _binding(request), "observations": observations})
        return {"schema": RESPONSE_SCHEMA, "binding": self.binding(),
                "producer": {"id": "qualification:authored-proposed-response", "method": "retained source/Git review",
                             "policy": "captured source scope only; omitted files and renames remain unknown",
                             "authentication": "unverified"}, "native_certification_claimed": False,
                "evidence": [{"id": "captured-owner-facts", "kind": "retained_artifact", "file": "owner_facts.json",
                              "sha256": audit._sha(self.facts_raw), "size_bytes": len(self.facts_raw)}],
                "responses": responses}


def _evidence(bundle, response, root, limits):
    rows = _list(response["evidence"], limits.max_evidence_files, "evidence artifact")
    known = {audit._sha(bundle.facts_raw)}
    for field in ("retained_cas_artifacts", "retained_git_objects"):
        inventory = _list(bundle.facts.get(field), handoff.DEFAULT_RECOVERY_LIMITS.max_owner_files, "retained artifact")
        for row in inventory:
            audit._require(type(row) is dict, "retained artifact object required")
            known.add(audit._digest(row.get("sha256"), "retained artifact"))
    qualification = bundle.facts.get("qualification_report")
    if qualification is not None:
        audit._require(type(qualification) is dict, "retained qualification object required")
        known.add(audit._digest(qualification.get("sha256"), "retained qualification report"))
    result, total, paths = {}, 0, set()
    for row in rows:
        audit._closed(row, {"id", "kind", "file", "sha256", "size_bytes"}, "evidence artifact")
        evidence_id = audit._text(row["id"], "evidence ID")
        audit._require(type(row["file"]) is str and evidence_id not in result and row["file"] not in paths,
                       "duplicate or malformed evidence ID/path")
        digest = audit._digest(row["sha256"], "evidence artifact")
        audit._require(type(row["kind"]) is str and row["kind"] in {"retained_artifact", "proposed_owner_statement"},
                       "unknown evidence kind")
        size = row["size_bytes"]
        audit._require(type(size) is int and 0 < size <= limits.max_evidence_file_bytes, "evidence file byte budget exceeded")
        remaining = min(limits.max_evidence_bytes - total, limits.max_total_bytes - bundle.total)
        audit._require(size <= remaining, "evidence aggregate byte budget exceeded")
        raw = audit._read_bounded(audit._input_file(root, row["file"]), min(size, remaining))
        audit._require(len(raw) == size and audit._sha(raw) == digest, "evidence artifact hash/size binding drift")
        total += len(raw)
        bundle.total += len(raw)
        if row["kind"] == "retained_artifact":
            audit._require(digest in known, "retained evidence not bound to handoff artifact inventory")
        else:
            statement = audit._closed(audit._load_json(raw, bundle.audit_limits),
                                      {"schema", "requests_sha256", "captured_scope_sha256", "description"}, "proposed evidence statement")
            audit._require(statement["schema"] == "codebase-ir-proposed-owner-evidence@1"
                           and statement["requests_sha256"] == audit._sha(bundle.raw)
                           and statement["captured_scope_sha256"] == bundle.scope_sha, "stale proposed evidence scope")
            audit._text(statement["description"], "proposed statement description", 4096)
        result[evidence_id] = (row, raw)
        paths.add(row["file"])
    bundle.check_budget()
    return result


def _review(bundle, response, evidence, limits):
    units = copy.deepcopy(bundle.captured.loader.units)
    observations, relations, frontiers, claims, answered = [], [], [], [], set()
    seen_units = set()

    def references(value):
        values = _ids(value, limits.max_evidence_files, "observation evidence")
        audit._require(bool(values) and all(item in evidence for item in values), "missing observation evidence binding")
        return sorted(values)

    for row in _list(response["responses"], limits.max_requests, "response request"):
        audit._closed(row, {"request_binding", "observations"}, "request response")
        binding = row["request_binding"]
        audit._require(type(binding) is dict and type(binding.get("request_id")) is str
                       and binding["request_id"] in bundle.requests, "unknown response request")
        request_id = binding["request_id"]
        audit._require(request_id not in answered and binding == _binding(bundle.requests[request_id]),
                       "duplicate or stale response source/head/target binding")
        answered.add(request_id)
        for observation in _list(row["observations"], limits.max_observations, "observation"):
            audit._closed(observation, {"unit_id", "dependency_inventory_claim", "revision_inventory_claim",
                                        "relations", "evidence_ids", "frontiers"}, "response observation")
            unit_id = observation["unit_id"]
            audit._require(type(unit_id) is str and unit_id in bundle.requests[request_id]["affected_unit_ids"]
                           and unit_id not in seen_units, "unknown or duplicate observation unit binding")
            seen_units.add(unit_id)
            observations.append(observation)
            audit._require(len(observations) <= limits.max_observations, "aggregate observation budget exceeded")
            references(observation["evidence_ids"])
            for field in ("dependency_inventory_claim", "revision_inventory_claim"):
                audit._require(type(observation[field]) is str and observation[field] in {"partial", "captured_scope"},
                               "unknown proposed inventory scope")
            local_frontiers = _list(observation["frontiers"], limits.max_frontiers, "owner frontier")
            for frontier in local_frontiers:
                audit._closed(frontier, {"code", "detail"}, "owner frontier")
                audit._text(frontier["code"], "owner frontier code")
                audit._text(frontier["detail"], "owner frontier detail", 2048)
                frontiers.append({"unit_id": unit_id, **frontier})
                audit._require(len(frontiers) <= limits.max_frontiers, "aggregate frontier budget exceeded")
            for field in ("dependency_inventory_claim", "revision_inventory_claim"):
                if observation[field] == "captured_scope":
                    claims.append({"unit_id": unit_id, "kind": field, "frontiers_present": bool(local_frontiers)})
            local_edges = set()
            for relation in _list(observation["relations"], limits.max_relations, "proposed relation"):
                audit._closed(relation, {"kind", "target_unit_id", "evidence_ids"}, "proposed relation")
                kind, target = relation["kind"], relation["target_unit_id"]
                audit._require(type(kind) is str and kind in RELATIONS and type(target) is str and target in units
                               and target != unit_id, "unknown/self/out-of-scope proposed relation")
                key = kind, target
                audit._require(key not in local_edges, "duplicate proposed relation")
                local_edges.add(key)
                item = {"from": unit_id, "to": target, "kind": kind,
                        "evidence_ids": references(relation["evidence_ids"])}
                relations.append(item)
                audit._require(len(relations) <= limits.max_relations, "aggregate proposed relation budget exceeded")
                if kind in {"dependency", "related_revision"}:
                    field = "dependencies" if kind == "dependency" else "related_revisions"
                    units[unit_id] = replace(units[unit_id], **{field: tuple(sorted(set(getattr(units[unit_id], field)) | {target}))})
    dependency, revision = audit._Union(list(units)), audit._Union(list(units))
    buckets = {}
    for unit_id, unit in sorted(units.items()):
        for reference in unit.dependencies:
            dependency.join(unit_id, reference)
        for reference in unit.related_revisions:
            revision.join(unit_id, reference)
        for kind, key in (("source", unit.content_sha256), ("ast", unit.normalized_ast_sha256),
                          ("path", (unit.repository_id, unit.path))):
            if key is not None:
                group = buckets.setdefault((kind, key), [])
                if group:
                    revision.join(group[0], unit_id)
                group.append(unit_id)
    contradictions = []
    for relation in relations:
        graph = dependency if relation["kind"] == "dependency_group_disjoint" else revision
        if relation["kind"] in {"dependency_group_disjoint", "revision_family_disjoint"}:
            if graph.find(relation["from"]) == graph.find(relation["to"]):
                contradictions.append({"code": "proposed_disjointness_contradicts_captured_or_proposed_relationships", **relation})
    for claim in claims:
        if claim["frontiers_present"]:
            contradictions.append({"code": "proposed_complete_scope_has_unresolved_frontiers", **claim})
    loader = copy.copy(bundle.captured.loader)
    loader.issues = []
    leaks = audit._group_leaks(units, loader)
    issues = sorted(bundle.baseline["issues"] + loader.issues, key=audit._canonical)
    preview = {"schema": "codebase-ir-owner-relation-preview@1", "status": "leaks_found" if leaks else "incomplete",
               "baseline_input_sha256": audit._sha(bundle.captured.raw), "captured_scope_sha256": bundle.scope_sha,
               "complete_for_declared_scope": False, "units": [units[key].report() for key in sorted(units)],
               "issues": issues, "leaks": leaks, "closure_flags_preserved": True,
               "native_closure_certification_verified": False, "proof_authority": False}
    return {"answered": sorted(answered), "observed_unit_ids": sorted(seen_units), "observations": observations,
            "relations": relations, "frontiers": frontiers,
            "claims": claims, "contradictions": sorted(contradictions, key=audit._canonical), "preview": preview}


def review_response(requests_path, output, *, response_path=None, limits=DEFAULT_LIMITS, audit_limits=audit.DEFAULT_LIMITS):
    bundle = _Bundle(Path(requests_path), limits, audit_limits)
    output = Path(output)
    response, raw, evidence, reviewed = None, None, {}, None
    if response_path is not None:
        response_path = Path(response_path)
        raw = audit._read_bounded(response_path, min(audit_limits.max_json_bytes, limits.max_total_bytes - bundle.total))
        bundle.total += len(raw)
        bundle.check_budget()
        response = audit._closed(audit._load_json(raw, audit_limits),
                                 {"schema", "binding", "producer", "native_certification_claimed", "evidence", "responses"}, "owner response")
        audit._require(response["schema"] == RESPONSE_SCHEMA and response["binding"] == bundle.binding(), "stale owner response scope binding")
        audit._require(response["native_certification_claimed"] is False, "native certification is outside proposed response profile")
        producer = audit._closed(response["producer"], {"id", "method", "policy", "authentication"}, "response producer")
        for field in ("id", "method", "policy"):
            audit._text(producer[field], "producer " + field, 2048)
        audit._require(producer["authentication"] == "unverified", "producer authority cannot be inferred")
        evidence = _evidence(bundle, response, response_path.parent, limits)
        reviewed = _review(bundle, response, evidence, limits)
    output.mkdir(mode=0o700, parents=False, exist_ok=False)
    metadata._write_bytes(output / "captured_requests.json", bundle.raw)
    metadata._write_bytes(output / "owner_facts.json", bundle.facts_raw)
    audit.write_private_report(output / "captured_scope.json", bundle.scope)
    audit.write_private_report(output / "response_template.json", bundle.template())
    audit.write_private_report(output / "baseline_audit_report.json", bundle.baseline)
    if raw is not None:
        metadata._write_bytes(output / "captured_response.json", raw)
        (output / "evidence").mkdir(mode=0o700)
        retained = set()
        for _evidence_id, (row, data) in sorted(evidence.items()):
            if row["sha256"] not in retained:
                metadata._write_bytes(output / "evidence" / (row["sha256"] + ".bin"), data)
                retained.add(row["sha256"])
        audit.write_private_report(output / "proposed_relation_audit_report.json", reviewed["preview"])
    contradictions = [] if reviewed is None else reviewed["contradictions"]
    leaks = bundle.baseline["leaks"] if reviewed is None else reviewed["preview"]["leaks"]
    disposition = "awaiting_response" if reviewed is None else "contradictory" if contradictions else "leaks_found" if leaks else "proposed_evidence_incomplete"
    report = {"schema": REPORT_SCHEMA, "disposition": disposition, "binding": bundle.binding(),
              "response_sha256": None if raw is None else audit._sha(raw), "limits": asdict(limits),
              "closure_request_count": len(bundle.requests), "response_request_count": 0 if reviewed is None else len(reviewed["answered"]),
              "unanswered_request_ids": sorted(set(bundle.requests) - (set() if reviewed is None else set(reviewed["answered"]))),
              "response_observation_count": 0 if reviewed is None else len(reviewed["observations"]),
              "unanswered_unit_ids": sorted({unit_id for request in bundle.requests.values() for unit_id in request["affected_unit_ids"]}
                                            - (set() if reviewed is None else set(reviewed["observed_unit_ids"]))),
              "evidence_inventory": [{"id": evidence_id, "kind": row["kind"], "sha256": row["sha256"],
                                      "size_bytes": row["size_bytes"], "retained_as": "evidence/" + row["sha256"] + ".bin"}
                                     for evidence_id, (row, _data) in sorted(evidence.items())],
              "baseline_audit_status": bundle.baseline["status"], "baseline_issue_count": len(bundle.baseline["issues"]),
              "proposed_audit_status": None if reviewed is None else reviewed["preview"]["status"],
              "proposed_audit_issue_count": None if reviewed is None else len(reviewed["preview"]["issues"]),
              "proposed_relation_count": 0 if reviewed is None else len(reviewed["relations"]),
              "proposed_inventory_claim_count": 0 if reviewed is None else len(reviewed["claims"]),
              "contradiction_count": len(contradictions), "contradictions": contradictions,
              "leakage_count": len(leaks), "leaks": leaks,
              "relations": [] if reviewed is None else sorted(reviewed["relations"], key=audit._canonical),
              "owner_frontiers": [] if reviewed is None else sorted(reviewed["frontiers"], key=audit._canonical),
              "producer_authentication_verified": False, "relationship_truth_verified": False,
              "native_closure_certification_verified": False, "closure_claims_applied": 0,
              "whole_repository_coverage": False, "unseen_rename_ancestry_verified": False,
              "proof_authority": False, "training_executed": False, "promotion_decisions_made": False}
    artifact_names = ["captured_requests.json", "owner_facts.json", "captured_scope.json", "response_template.json",
                      "baseline_audit_report.json"]
    if raw is not None:
        artifact_names.extend(["captured_response.json", "proposed_relation_audit_report.json"])
    report["artifacts"] = {}
    for name in artifact_names:
        data = audit._read_bounded(output / name, audit_limits.max_json_bytes)
        report["artifacts"][name] = {"file": name, "sha256": audit._sha(data), "size_bytes": len(data)}
    audit.write_private_report(output / "response_review_report.json", report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requests", required=True, type=Path)
    parser.add_argument("--response", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        report = review_response(args.requests, args.output, response_path=args.response)
    except (audit.AuditInputError, OSError, UnicodeError) as exc:
        print(f"invalid input: {exc}", file=sys.stderr)
        return 3
    print(f"owner response review: {report['disposition']}; {report['response_request_count']} requests; "
          f"{report['contradiction_count']} contradictions; {report['leakage_count']} leak groups; native closure certified: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
