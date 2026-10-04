#!/usr/bin/env python3
"""Enumerate every captured cohort group without certifying independent splits."""
from __future__ import annotations

import argparse
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import codebase_ir_closure_response as response
import codebase_ir_corpus_audit as audit
import codebase_ir_source_metadata as metadata

REPORT_SCHEMA = "codebase-ir-captured-cohort-inventory@1"
REVIEW_FIELDS = {"schema", "disposition", "binding", "response_sha256", "limits", "closure_request_count",
                "response_request_count", "unanswered_request_ids", "response_observation_count", "unanswered_unit_ids",
                "evidence_inventory", "baseline_audit_status", "baseline_issue_count", "proposed_audit_status",
                "proposed_audit_issue_count", "proposed_relation_count", "proposed_inventory_claim_count",
                "contradiction_count", "contradictions", "leakage_count", "leaks", "relations", "owner_frontiers",
                "producer_authentication_verified", "relationship_truth_verified", "native_closure_certification_verified",
                "closure_claims_applied", "whole_repository_coverage", "unseen_rename_ancestry_verified", "proof_authority",
                "training_executed", "promotion_decisions_made", "artifacts"}
UNIT_FIELDS = set(audit.Unit.__dataclass_fields__)
BASE_FILES = {"captured_requests.json", "owner_facts.json", "captured_scope.json", "response_template.json", "baseline_audit_report.json"}
RESPONSE_FILES = {"captured_response.json", "proposed_relation_audit_report.json"}


@dataclass(frozen=True)
class InventoryLimits:
    max_artifacts: int = 48
    max_total_bytes: int = 64 * 1024 * 1024
    max_edges: int = 16384
    max_group_rows: int = 512

    def __post_init__(self):
        audit._require(all(type(value) is int and value > 0 for value in asdict(self).values()),
                       "positive exact cohort budgets required")


DEFAULT_LIMITS = InventoryLimits()


class _Inputs:
    def __init__(self, path, limits, audit_limits):
        self.root, self.limits, self.audit_limits = path.parent, limits, audit_limits
        self.total, self.raws, self.values = 0, {}, {}
        self.raw = self.read(path)
        document = audit._load_json(self.raw, audit_limits)
        audit._require("artifacts" in document, "review lacks pinned artifact inventory; regenerate review rather than reconstruct past pins")
        self.review = audit._closed(document, REVIEW_FIELDS, "owner response review")
        audit._require(self.review["schema"] == response.REPORT_SCHEMA, "versioned owner response review required")
        for field in ("producer_authentication_verified", "relationship_truth_verified", "native_closure_certification_verified",
                      "whole_repository_coverage", "unseen_rename_ancestry_verified", "proof_authority", "training_executed",
                      "promotion_decisions_made"):
            audit._require(self.review[field] is False, "review must retain nonauthoritative scope")
        for field in ("closure_request_count", "response_request_count", "response_observation_count", "baseline_issue_count",
                      "proposed_relation_count", "proposed_inventory_claim_count", "contradiction_count", "leakage_count", "closure_claims_applied"):
            audit._require(type(self.review[field]) is int and self.review[field] >= 0, "exact review count required")
        audit._require(self.review["closure_claims_applied"] == 0, "review must preserve unknown closure claims")
        disposition = self.review["disposition"]
        audit._require(type(disposition) is str and disposition in {"awaiting_response", "proposed_evidence_incomplete",
                       "leaks_found", "contradictory"}, "unknown review disposition")
        binding = audit._closed(self.review["binding"], {"requests_sha256", "owner_facts_sha256", "pinned_input_sha256",
                                                        "captured_scope_sha256"}, "review scope binding")
        for field, value in binding.items():
            audit._digest(value, field)
        self.has_response = self.review["response_sha256"] is not None
        if self.has_response:
            audit._digest(self.review["response_sha256"], "captured response")
            audit._require(type(self.review["proposed_audit_issue_count"]) is int
                           and self.review["proposed_audit_issue_count"] >= 0, "exact proposed issue count required")
        else:
            audit._require(disposition == "awaiting_response" and self.review["proposed_audit_issue_count"] is None
                           and self.review["proposed_audit_status"] is None, "absent response scope drift")
        artifacts = self.review["artifacts"]
        expected = BASE_FILES | (RESPONSE_FILES if self.has_response else set())
        audit._require(type(artifacts) is dict and set(artifacts) == expected, "complete pinned review artifacts required")
        audit._require(len(artifacts) <= limits.max_artifacts, "cohort artifact count budget exceeded")
        for name, row in sorted(artifacts.items()):
            self.artifact(name, row)
        self.scope = audit._closed(self.values["captured_scope.json"],
                                   {"schema", "requests_sha256", "pinned_input_sha256", "units", "native_target_bindings",
                                    "ancestry_complete_claim", "whole_repository_coverage", "unseen_rename_ancestry_verified"}, "captured scope")
        audit._require(self.scope["schema"] == response.SCOPE_SCHEMA
                       and response._sha_object(self.scope) == binding["captured_scope_sha256"]
                       and self.scope["requests_sha256"] == binding["requests_sha256"]
                       and self.scope["pinned_input_sha256"] == binding["pinned_input_sha256"]
                       and self.scope["whole_repository_coverage"] is False
                       and self.scope["unseen_rename_ancestry_verified"] is False, "detached captured scope binding")
        audit._bool(self.scope["ancestry_complete_claim"], "original ancestry claim")
        for name, digest in (("captured_requests.json", binding["requests_sha256"]),
                             ("owner_facts.json", binding["owner_facts_sha256"])):
            audit._require(audit._sha(self.raws[name]) == digest, "detached request/owner artifact binding")
        self.baseline = self.values["baseline_audit_report.json"]
        audit._require(self.baseline.get("schema") == audit.REPORT_SCHEMA
                       and self.baseline.get("input_sha256") == binding["pinned_input_sha256"]
                       and self.baseline.get("units") == self.scope["units"], "detached baseline scope binding")
        for field in ("proof_authority", "training_executed", "native_replay_performed", "promotion_authority"):
            audit._require(self.baseline.get(field) is False, "baseline scope acquired authority")
        self.units = self.parse_units(self.scope["units"])
        self.issues = response._list(self.baseline.get("issues"), audit_limits.max_links, "baseline issue")
        audit._require(len(self.issues) == self.review["baseline_issue_count"]
                       and self.baseline.get("status") == self.review["baseline_audit_status"], "baseline count/status drift")
        self.preview = self.baseline
        if self.has_response:
            audit._require(audit._sha(self.raws["captured_response.json"]) == self.review["response_sha256"], "detached proposed response binding")
            proposed = self.values["captured_response.json"]
            audit._require(proposed.get("schema") == response.RESPONSE_SCHEMA
                           and proposed.get("binding") == binding and proposed.get("native_certification_claimed") is False,
                           "detached proposed response scope")
            self.preview = self.values["proposed_relation_audit_report.json"]
            audit._closed(self.preview, {"schema", "status", "baseline_input_sha256", "captured_scope_sha256",
                                        "complete_for_declared_scope", "units", "issues", "leaks", "closure_flags_preserved",
                                        "native_closure_certification_verified", "proof_authority"}, "relation preview")
            audit._require(self.preview["schema"] == "codebase-ir-owner-relation-preview@1"
                           and self.preview["baseline_input_sha256"] == binding["pinned_input_sha256"]
                           and self.preview["captured_scope_sha256"] == binding["captured_scope_sha256"]
                           and self.preview["complete_for_declared_scope"] is False
                           and self.preview["closure_flags_preserved"] is True
                           and self.preview["native_closure_certification_verified"] is False
                           and self.preview["proof_authority"] is False, "detached relation preview scope")
            preview_units = self.parse_units(self.preview["units"])
            audit._require(set(preview_units) == set(self.units), "preview cohort population changed")
            for unit_id, before in self.units.items():
                after = preview_units[unit_id]
                for field in UNIT_FIELDS - {"dependencies", "related_revisions"}:
                    audit._require(getattr(before, field) == getattr(after, field), "preview source role/identity/closure drift")
                audit._require(set(before.dependencies) <= set(after.dependencies)
                               and set(before.related_revisions) <= set(after.related_revisions), "preview discarded baseline relationships")
            before_issues = {audit._canonical(issue) for issue in self.issues}
            self.issues = response._list(self.preview["issues"], audit_limits.max_links, "preview issue")
            audit._require(before_issues <= {audit._canonical(issue) for issue in self.issues}
                           and len(self.issues) == self.review["proposed_audit_issue_count"]
                           and self.preview["status"] == self.review["proposed_audit_status"], "preview discarded original unknown claims")
            self.units = preview_units
        self.native = self.native_memberships()
        self.relations = response._list(self.review["relations"], response.DEFAULT_LIMITS.max_relations, "review relation")
        audit._require(len(self.relations) == self.review["proposed_relation_count"], "proposed relation count drift")
        self.frontiers = response._list(self.review["owner_frontiers"], response.DEFAULT_LIMITS.max_frontiers, "owner frontier")
        for row in self.frontiers:
            audit._closed(row, {"unit_id", "code", "detail"}, "review frontier")
            audit._require(type(row["unit_id"]) is str and row["unit_id"] in self.units, "owner frontier outside captured scope")
            audit._text(row["code"], "frontier code")
            audit._text(row["detail"], "frontier detail", 2048)
        for issue in self.issues:
            audit._require(type(issue) is dict and type(issue.get("code")) is str, "explicit captured issue required")
            if "unit_id" in issue:
                audit._require(type(issue["unit_id"]) is str and issue["unit_id"] in self.units,
                               "captured issue outside cohort scope")
        self.contradictions = response._list(self.review["contradictions"], response.DEFAULT_LIMITS.max_relations,
                                             "review contradiction")
        audit._require(len(self.contradictions) == self.review["contradiction_count"], "contradiction count drift")
        for row in self.contradictions:
            audit._require(type(row) is dict and type(row.get("code")) is str, "explicit review contradiction required")
            for field in ("from", "to", "unit_id"):
                if field in row:
                    audit._require(type(row[field]) is str and row[field] in self.units, "contradiction outside cohort scope")
        self.evidence()

    def read(self, path, maximum=None):
        remaining = self.limits.max_total_bytes - self.total
        audit._require(remaining > 0, "cohort aggregate input byte budget exhausted")
        cap = min(self.audit_limits.max_json_bytes if maximum is None else maximum, remaining)
        raw = audit._read_bounded(path, cap)
        self.total += len(raw)
        return raw

    def artifact(self, name, row):
        audit._closed(row, {"file", "sha256", "size_bytes"}, "review artifact descriptor")
        audit._require(row["file"] == name and type(row["size_bytes"]) is int and 0 < row["size_bytes"] <= self.audit_limits.max_json_bytes,
                       "exact bounded review artifact path/size required")
        audit._digest(row["sha256"], "review artifact")
        raw = self.read(audit._input_file(self.root, row["file"]), row["size_bytes"])
        audit._require(len(raw) == row["size_bytes"] and audit._sha(raw) == row["sha256"], "detached review artifact hash/size drift")
        self.raws[name] = raw
        self.values[name] = audit._load_json(raw, self.audit_limits)

    def parse_units(self, rows):
        units = {}
        for row in response._list(rows, min(self.audit_limits.max_units, self.limits.max_group_rows), "cohort unit"):
            audit._closed(row, UNIT_FIELDS, "captured source unit")
            unit_id = audit._text(row["id"], "unit ID", 1024)
            audit._require(unit_id not in units and type(row["role"]) is str and row["role"] in audit.ROLES,
                           "duplicate unit or ambiguous role")
            audit._text(row["repository_id"], "source repository")
            audit._relative_path(row["path"], "source path")
            audit._text(row["revision"], "source revision", 1024)
            audit._digest(row["content_sha256"], "source digest")
            if row["normalized_ast_sha256"] is not None:
                audit._digest(row["normalized_ast_sha256"], "source AST digest")
            audit._require(row["size_bytes"] is None or type(row["size_bytes"]) is int and row["size_bytes"] >= 0,
                           "exact source size required")
            audit._text(row["origin"], "source origin")
            for field in ("dependencies_complete", "revision_relations_complete", "source_bytes_verified"):
                audit._bool(row[field], field)
            values = dict(row)
            for field in ("dependencies", "related_revisions"):
                values[field] = audit._references(row[field], field, self.audit_limits)
            units[unit_id] = audit.Unit(**values)
        audit._require(bool(units), "captured cohort cannot be empty")
        return units

    def native_memberships(self):
        rows = response._list(self.scope["native_target_bindings"], self.audit_limits.max_units, "native cohort membership")
        facts = self.values["owner_facts.json"]
        audit._require(rows == facts.get("native_targets"), "detached native membership inventory")
        result = {}
        for row in rows:
            audit._closed(row, {"unit_id", "version_id", "batch_field", "index", "target_source_digest", "head", "head_sha256",
                                "source_binding", "source_binding_sha256", "export_sha256"}, "native target membership")
            unit_id = row["unit_id"]
            audit._require(type(unit_id) is str and unit_id in self.units and unit_id not in result,
                           "duplicate or unknown native cohort unit")
            audit._require(type(row["index"]) is int and row["index"] >= 0 and type(row["batch_field"]) is str
                           and row["batch_field"] in {"training_targets", "tuning_targets", "canary_targets", "replay_targets"},
                           "native batch/index binding required")
            audit._require(unit_id == f"native/{row['version_id']}/{row['batch_field']}/{row['index']}", "native unit position drift")
            for field in ("target_source_digest", "head_sha256", "source_binding_sha256", "export_sha256"):
                audit._digest(row[field], field)
            unit, binding = self.units[unit_id], row["source_binding"]
            audit._require(type(binding) is dict and row["head"] == binding.get("head")
                           and response._sha_object(row["head"]) == row["head_sha256"]
                           and response._sha_object(binding) == row["source_binding_sha256"]
                           and binding.get("repository_id") == unit.repository_id and binding.get("path") == unit.path
                           and binding.get("content_sha256") == unit.content_sha256
                           and binding.get("source_revision") == unit.revision, "native source/head digest drift")
            role = {"training_targets": "train", "replay_targets": "train", "tuning_targets": "tune", "canary_targets": "canary"}[row["batch_field"]]
            audit._require(unit.role == role, "native target role reassigned")
            result[unit_id] = row
        audit._require({key for key in self.units if key.startswith("native/")} == set(result), "native target membership omitted")
        return result

    def evidence(self):
        rows = response._list(self.review["evidence_inventory"], response.DEFAULT_LIMITS.max_evidence_files, "review evidence")
        audit._require(len(rows) + len(self.raws) <= self.limits.max_artifacts, "cohort evidence file budget exceeded")
        seen, retained = set(), set()
        for row in rows:
            audit._closed(row, {"id", "kind", "sha256", "size_bytes", "retained_as"}, "review evidence descriptor")
            evidence_id = audit._text(row["id"], "evidence ID")
            audit._require(evidence_id not in seen, "duplicate review evidence ID")
            seen.add(evidence_id)
            digest = audit._digest(row["sha256"], "review evidence")
            audit._require(row["retained_as"] == "evidence/" + digest + ".bin"
                           and type(row["size_bytes"]) is int and 0 < row["size_bytes"] <= response.DEFAULT_LIMITS.max_evidence_file_bytes,
                           "review evidence size/path drift")
            audit._require(type(row["kind"]) is str and row["kind"] in {"retained_artifact", "proposed_owner_statement"},
                           "unknown review evidence kind")
            if digest not in retained:
                raw = self.read(audit._input_file(self.root, row["retained_as"]), row["size_bytes"])
                audit._require(len(raw) == row["size_bytes"] and audit._sha(raw) == digest, "detached review evidence drift")
                self.raws[row["retained_as"]] = raw
                retained.add(digest)


def _groups(inputs, limits):
    units, names = inputs.units, sorted(inputs.units)
    combined = audit._Union(names)
    edges, external = set(), set()

    def edge(kind, left, right, basis):
        edges.add((kind, left, right, basis))
        audit._require(len(edges) <= limits.max_edges, "cohort edge budget exceeded")
        combined.join(left, right)
        if right not in units:
            external.add(right)

    for kind, key in (("exact_bytes", lambda unit: unit.content_sha256),
                      ("normalized_ast", lambda unit: unit.normalized_ast_sha256),
                      ("same_repository_path", lambda unit: (unit.repository_id, unit.path))):
        buckets = {}
        for name in names:
            value = key(units[name])
            if value is not None:
                buckets.setdefault(value, []).append(name)
        for group in buckets.values():
            for name in group[1:]:
                edge(kind, group[0], name, "captured_source_identity")
    baseline = {row["id"]: row for row in inputs.baseline["units"]}
    proposed = set()
    for row in inputs.relations:
        audit._closed(row, {"from", "to", "kind", "evidence_ids"}, "review relationship")
        audit._require(type(row["from"]) is str and row["from"] in units
                       and type(row["to"]) is str and row["to"] in units
                       and type(row["kind"]) is str and row["kind"] in response.RELATIONS, "review relationship scope drift")
        if row["kind"] in {"dependency", "related_revision"}:
            field = "dependencies" if row["kind"] == "dependency" else "related_revisions"
            audit._require(row["to"] in getattr(units[row["from"]], field), "proposed relation detached from preview")
            proposed.add((field, row["from"], row["to"]))
    for name in names:
        for kind, field in (("dependency_connected", "dependencies"), ("related_revision", "related_revisions")):
            for reference in getattr(units[name], field):
                was_declared = reference in baseline[name][field]
                audit._require(was_declared or (field, name, reference) in proposed, "preview contains unreviewed proposed relationship")
                edge(kind, name, reference, "baseline_declared_relation" if was_declared else "proposed_owner_relation")
    buckets = {}
    for name in names:
        buckets.setdefault(combined.find(name), []).append(name)
    global_issues = [row for row in inputs.issues if "unit_id" not in row]
    groups = []
    for _root, members in sorted(buckets.items(), key=lambda row: row[1]):
        member_set = set(members)
        roots = {combined.find(name) for name in members}
        witnesses = [{"kind": kind, "from": left, "to": right, "basis": basis}
                     for kind, left, right, basis in sorted(edges) if combined.find(left) in roots]
        unknown_refs = sorted(reference for reference in external if combined.find(reference) in roots)
        roles = sorted({units[name].role for name in members})
        ancestor_ids = sorted(name for name in members if units[name].origin == "ancestral_training")
        final_ids = sorted(name for name in members if units[name].role == "final")
        nonfinal_ids = sorted(name for name in members if units[name].role != "final")
        issues = [row for row in inputs.issues if row.get("unit_id") in member_set]
        frontiers = [row for row in inputs.frontiers if row["unit_id"] in member_set]
        proposed_annotations = [row for row in inputs.relations if row["from"] in member_set or row["to"] in member_set]
        contradictions = [row for row in inputs.contradictions if any(row.get(field) in member_set for field in ("from", "to", "unit_id"))]
        false_claims = [{"unit_id": name, "dependencies_complete_claim": units[name].dependencies_complete,
                         "revision_relations_complete_claim": units[name].revision_relations_complete}
                        for name in members if not units[name].dependencies_complete or not units[name].revision_relations_complete]
        membership = []
        for name in members:
            unit = units[name]
            identity = {field: getattr(unit, field) for field in ("id", "role", "repository_id", "path", "revision", "content_sha256",
                                                               "normalized_ast_sha256", "origin", "source_bytes_verified")}
            identity["native_target"] = inputs.native.get(name)
            identity["ancestral_training_exposure"] = name in ancestor_ids
            membership.append(identity)
        risk = ("connected_to_training_or_evaluation" if final_ids and nonfinal_ids else
                "no_observed_connection_with_unresolved_claims" if final_ids and (issues or frontiers or false_claims or global_issues or unknown_refs) else
                "no_observed_connection_in_captured_scope" if final_ids else "no_final_membership")
        groups.append({"group_id": "cohort-group:" + response._sha_object(members), "unit_ids": members, "roles": roles,
                       "memberships": membership, "edges": witnesses, "cross_role_connection": len(roles) > 1,
                       "ancestral_training_unit_ids": ancestor_ids, "final_unit_ids": final_ids,
                       "final_exposure_risk": risk, "independence_verified": False,
                       "unresolved_claims": sorted(issues, key=audit._canonical), "original_unknown_completeness_flags": false_claims,
                       "proposed_relationship_annotations": sorted(proposed_annotations, key=audit._canonical),
                       "contradictions": sorted(contradictions, key=audit._canonical),
                       "owner_frontiers": sorted(frontiers, key=audit._canonical), "unresolved_reference_ids": unknown_refs,
                       "scope_wide_unknowns_apply": bool(global_issues), "closure_certified": False})
    audit._require(len(groups) <= limits.max_group_rows, "cohort group row budget exceeded")
    return groups, global_issues


def create_inventory(review_path, output, *, limits=DEFAULT_LIMITS, audit_limits=audit.DEFAULT_LIMITS):
    inputs = _Inputs(Path(review_path), limits, audit_limits)
    groups, global_issues = _groups(inputs, limits)
    output = Path(output)
    output.mkdir(mode=0o700, parents=False, exist_ok=False)
    metadata._write_bytes(output / "captured_review.json", inputs.raw)
    for name, raw in sorted(inputs.raws.items()):
        destination = output / "captured_artifacts" / name
        destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        metadata._write_bytes(destination, raw)
    report = {"schema": REPORT_SCHEMA, "disposition": "inventory_produced", "review_sha256": audit._sha(inputs.raw),
              "review_disposition": inputs.review["disposition"], "binding": inputs.review["binding"], "limits": asdict(limits),
              "unit_count": len(inputs.units), "group_count": len(groups),
              "cross_role_group_count": sum(group["cross_role_connection"] for group in groups),
              "final_group_count": sum(bool(group["final_unit_ids"]) for group in groups),
              "final_connected_group_count": sum(group["final_exposure_risk"] == "connected_to_training_or_evaluation" for group in groups),
              "ancestral_training_exposure_count": sum(len(group["ancestral_training_unit_ids"]) for group in groups),
              "native_target_membership_count": len(inputs.native), "baseline_issue_count": inputs.review["baseline_issue_count"],
              "inventory_issue_count": len(inputs.issues), "owner_frontier_count": len(inputs.frontiers),
              "contradiction_count": len(inputs.contradictions),
              "scope_wide_unknowns": global_issues, "groups": groups,
              "captured_artifact_pins": inputs.review["artifacts"], "native_closure_certification_verified": False,
              "producer_authentication_verified": False, "relationship_truth_verified": False, "independence_verified": False,
              "closure_claims_applied": 0, "whole_repository_coverage": False, "unseen_rename_ancestry_verified": False,
              "proof_authority": False, "training_executed": False, "promotion_decisions_made": False,
              "scope": "all connected groups within byte-bound captured scope; unknown closure and unobserved relationships remain unknown"}
    audit.write_private_report(output / "cohort_inventory.json", report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        report = create_inventory(args.review, args.output)
    except (audit.AuditInputError, OSError, UnicodeError) as exc:
        print(f"invalid input: {exc}", file=sys.stderr)
        return 3
    print(f"cohort inventory: {report['group_count']} groups; {report['cross_role_group_count']} cross-role; "
          f"{report['inventory_issue_count']} unresolved issues; independence verified: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
