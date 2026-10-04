"""Receive ten retained successor planning bodies without native execution."""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import stat
import time
from hashlib import sha256
from pathlib import Path

INPUT_SCHEMA = "codebase-ir-successor-planning-custody-input@1"
SCHEMA = "codebase-ir-successor-planning-custody@1"
PROFILE = "retained-native-source-successor-planning@1"
PUBLIC_ANCHOR = "8a9a24c56873f97edac6e325078039fc0e2ba017c922839d11eaf3d92e7f2f91"
MAX_FILE = 1024 * 1024
MAX_BYTES = 8 * 1024 * 1024
MAX_FILES = 32
MAX_MANIFEST = 256 * 1024
MAX_REPORT = 4 * 1024 * 1024
MAX_SECONDS = 120
MAX_DEPTH = 32
MAX_VALUES = 100000
ROLES = (
    "machine_review", "closed_audit", "native_result", "failed_native_result",
    "authored_planning_inputs", "planning_preview", "cold_planning_preview",
    "planning_semantic_preimages", "cold_planning_semantic_preimages", "resource_admission",
)
LOCAL_NAMES = dict(zip(ROLES[4:], (
    "authored-planning-inputs.json", "planning-preview.json", "cold-planning-preview.json",
    "planning-semantic-preimages.json", "cold-planning-semantic-preimages.json", "resource-admission.json",
), strict=True))
TRUE_FLAGS = (
    "successor_planning_custody_produced", "recorded_task_residuals_reconciled",
    "recorded_stage_outcomes_reconciled", "typed_preimage_population_reconciled",
    "semantic_material_byte_digests_rederived", "reused_cold_preimages_disclosed",
    "declared_prefix_scope_reconciled", "failed_deadline_attempt_preserved",
    "recorded_costs_reconciled", "recorded_resource_drain_reconciled", "input_files_unchanged",
)
FALSE_FLAGS = (
    "native_execution_performed", "training_executed", "current_authority_claimed",
    "owner_sources_imported", "owner_database_opened", "profile_keys_read",
    "git_executable_invoked", "network_access_performed", "checkpoint_state_reconstructed",
    "model_bodies_read", "source_bodies_replayed", "semantic_digest_replay_qualified",
    "semantic_meanings_independently_replayed", "critic_body_closure_qualified",
    "obligation_graph_body_closure_qualified", "execution_plan_body_closure_qualified",
    "whole_planner_solver_free_qualified", "complete_successor_scan_qualified",
    "two_prefixes_are_64_distinct_members_qualified", "cold_process_restart_qualified",
    "current_resource_cleanup_verified", "kernel_resource_enforcement_qualified",
    "numerical_execution_independently_reperformed", "historical_process_origin_authenticated",
    "signature_authentication_performed", "proof_authority_qualified",
    "production_acceptance_requalified", "worker_admission_qualified",
    "unique_cpu_time_measured", "total_elapsed_wall_time_measured", "throughput_qualified",
)
ZERO_FIELDS = ("runtime_fact_count", "tasks_omitted_count", "additional_attempted_training_epochs")
MATERIAL_FIELDS = frozenset((
    "admission_materials", "candidate_context", "current_facts", "current_roots", "evidence_adapters",
    "evidence_bundle", "evidence_queries", "extra", "frozen_goal", "intent", "model_provider",
    "obligation_graph", "parallel_request", "parallel_tasks", "predicates", "producers",
    "query_plan", "scan", "task_candidates", "workflow_request",
))
PREFIX = "ipfs_accelerate_py.agent_supervisor.planning."
RECORD_FIELDS = {
    PREFIX + "obligation_graph_compiler.TypedIntent": frozenset(("intent_id", "desired_predicates", "source_refs", "current_root_id", "metadata")),
    PREFIX + "obligation_graph_compiler.TypedPredicate": frozenset(("predicate_id", "predicate_type", "subject_ref", "object_ref", "property_id", "polarity", "support", "provenance_refs", "assumption_refs", "validation_requirement_refs", "proof_requirement_refs", "invalidation_selectors")),
    PREFIX + "obligation_graph_compiler.ProducerRule": frozenset(("producer_id", "effect_predicate_ids", "required_predicate_ids", "task_candidate_ids", "provenance_refs", "assumption_refs", "validation_requirement_refs", "proof_requirement_refs", "invalidation_selectors", "executable")),
    PREFIX + "obligation_graph_compiler.TaskCandidate": frozenset(("candidate_id", "closes_obligation_ids", "producer_id", "depends_on_candidate_ids", "provenance_refs")),
    PREFIX + "adaptive_planner.FrozenPlanningGoal": frozenset(("goal_id", "goal_content_id", "repository_tree_id", "policy")),
    PREFIX + "plan_evaluator.EvidenceAwarePlanPolicy": frozenset(("acceptance_criteria", "evidence_terms", "trusted_assumptions", "supported_semantics", "satisfied_dependencies", "allowed_scopes", "available_resource_classes", "max_estimated_resource_cost", "max_estimated_tokens", "max_estimated_runtime_seconds", "min_novelty", "require_validation", "require_proof")),
}
ENUM_VALUES = {
    PREFIX + "obligation_graph_compiler.PredicatePolarity": {"positive", "negative"},
    PREFIX + "obligation_graph_compiler.SemanticSupport": {"reviewed", "unsupported", "unknown"},
}
GOALS = ["goal:runtime:0", "goal:runtime:1"]
TASKS = ["task:runtime:0", "task:runtime:1"]
STAGES = ("scan", "query", "evidence", "obligation", "candidate", "critique", "admission", "parallel_plan")
BLOCKERS = ["execution_plan_not_admitted", "ir_admission_materials_absent", "parallel_plan_rejected",
            "parallel:output_collision", "parallel:resource_infeasible", "parallel:stale_capacity"]
PHASES = (
    "author_fresh_300_member_repository", "publish_previous_source", "explicit_previous_head_root_training",
    "publish_current_source", "build_default_source_delta", "explicit_current_head_child_training",
    "select_default_fresh_successor_root", "select_opt_out_successor_root",
    "infer_default_fresh_32_member_prefix", "infer_opt_out_fresh_32_member_prefix",
    "actual_current_source_delta_plan_preview", "refuse_old_model_for_new_head",
    "refuse_precancelled_selection_receiving", "cold_receive_successor_selection",
    "cold_receive_fresh_prefix_page", "cold_current_source_delta_plan_preview",
)
DEADLINES = {"default_selection": 120, "existing_repository_preview": 90, "inference_page": 600,
             "planning_adapter": 120, "reference_selection": 600.0, "reference_override_is_qualification_only": True}
PLAN_AUTHORITY = frozenset(("admission_authority", "authoritative_cache_eligible", "behavioral_satisfaction",
    "completion_authority", "decoded_formulas_generated", "execution_authority", "mutation_authority",
    "proof_authority", "repository_code_executed", "runtime_behavior_verified", "scan_execution_attested",
    "source_execution_attested", "source_semantics_verified", "training_executed"))


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
            require(len(child) <= MAX_FILE and "\x00" not in child, "bounded JSON text required")
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


def selected_bindings(pins, machine, audit):
    require(machine["schema"] == "repository-proof-index-source-successor-review@1" and machine["qualified"] is True,
            "machine review schema and status")
    path = lexical_path(pins["machine_review"]["path"])
    tail = Path("external/ipfs_accelerate/docs/architecture/repository_proof_index_and_codebase_ir.source_successor_review.json")
    require(path.parts[-len(tail.parts):] == tail.parts, "machine review location")
    workspace = path.parents[4]
    namespace = workspace / lexical_path(machine["native_namespace"], absolute=False)
    require(namespace == workspace / "artifacts/codebase_ir_terminal_bench/source-successor-qualification-20261003-02",
            "selected successor namespace")
    expected = {"machine_review": pins["machine_review"],
                "closed_audit": declared_pin(workspace, machine["independent_closed_audit"]),
                "native_result": declared_pin(workspace, machine["native_result"]),
                "failed_native_result": declared_pin(workspace, machine["failed_native_attempt"]["result"])}
    require(expected["native_result"]["path"] == str(namespace / "result.json")
            and expected["failed_native_result"]["path"] == str(workspace / "artifacts/codebase_ir_terminal_bench/source-successor-qualification-20261003-01/result.json"),
            "exact successful and failed attempt locations")
    require(audit["schema"] == "codebase-source-successor-independent-audit@1" and audit["qualified"] is True
            and audit["errors"] == [] and audit["preserved"] is True and audit["namespace"] == str(namespace), "closed audit scope")
    require(same(declared_pin(namespace, audit["audited_result"]), expected["native_result"]), "audit native result binding")
    rows = audit["archive"]["files"]
    require(type(rows) is list and len(rows) <= 4096, "archive metadata population bound")
    members, regular, size = {}, 0, 0
    for row in rows:
        kind = row["kind"]
        closed(row, {"kind", "mode", "mtime_ns", "path"} | ({"bytes", "sha256", "nlink"} if kind == "file" else set()), "closed archive metadata row")
        require(kind in ("file", "directory"), "unreviewed archive member kind")
        if row["path"] != ".":
            lexical_path(row["path"], absolute=False)
        else:
            require(kind == "directory", "archive root directory")
        require(row["path"] not in members, "duplicate archive metadata member")
        exact_int(row["mode"], 0o7777)
        exact_int(row["mtime_ns"])
        members[row["path"]] = row
        if kind == "file":
            exact_int(row["nlink"], 65536)
            digest(row["sha256"])
            size += exact_int(row["bytes"], 2**31)
            regular += 1
    require(regular == exact_int(audit["archive"]["regular_files"], 4096)
            and size == exact_int(audit["archive"]["regular_bytes"]), "archive declared metadata totals")
    for role, member in LOCAL_NAMES.items():
        row = members[member]
        require(row["kind"] == "file", "selected archive member is a file")
        expected[role] = descriptor({"path": str(namespace / member), "sha256": row["sha256"], "size_bytes": row["bytes"]})
    require(same(expected, pins) and len({row["path"] for row in pins.values()}) == len(ROLES), "complete exact selected raw bindings")
    return workspace, namespace


def project(value):
    """Construct this authored fixture's tags; never instantiate native classes."""
    if type(value) in (list, tuple):
        return {"$sequence": type(value).__name__, "items": [project(item) for item in value]}
    if type(value) is dict:
        if "$record" in value or "$enum" in value:
            return value
        return {"$mapping": {key: project(item) for key, item in value.items()}}
    return value


def authored_fields(snapshot_cid):
    def record(name, fields):
        return {"$record": PREFIX + name, "fields": project(fields)}

    def enum(name, value):
        return {"$enum": PREFIX + "obligation_graph_compiler." + name, "value": value}

    predicates, producers, tasks = [], [], []
    for index in range(2):
        goal, producer, task = GOALS[index], f"producer:runtime:{index}", TASKS[index]
        predicates.append(record("obligation_graph_compiler.TypedPredicate", {
            "predicate_id": goal, "predicate_type": "reviewed_runtime_requirement", "subject_ref": "calc.py",
            "object_ref": f"requirement:{index}", "property_id": "", "polarity": enum("PredicatePolarity", "positive"),
            "support": enum("SemanticSupport", "reviewed"),
            **{field: () for field in ("provenance_refs", "assumption_refs", "validation_requirement_refs", "proof_requirement_refs", "invalidation_selectors")},
        }))
        producers.append(record("obligation_graph_compiler.ProducerRule", {
            "producer_id": producer, "effect_predicate_ids": (goal,), "executable": True,
            **{field: () for field in ("required_predicate_ids", "task_candidate_ids", "provenance_refs", "assumption_refs", "validation_requirement_refs", "proof_requirement_refs", "invalidation_selectors")},
        }))
        tasks.append(record("obligation_graph_compiler.TaskCandidate", {
            "candidate_id": task, "producer_id": producer, "closes_obligation_ids": (f"obligation:producer:{producer}:for:{goal}",),
            "depends_on_candidate_ids": (), "provenance_refs": (),
        }))
    policy = {"acceptance_criteria": tuple(GOALS), "evidence_terms": ("source:authored-runtime",),
              "trusted_assumptions": (), "supported_semantics": (), "satisfied_dependencies": (),
              "allowed_scopes": ("scope:calc.py",), "available_resource_classes": ("cpu",),
              "max_estimated_resource_cost": 1000000.0, "max_estimated_tokens": 1000000000,
              "max_estimated_runtime_seconds": 1000000.0, "min_novelty": 0.0, "require_validation": True, "require_proof": False}
    values = dict.fromkeys(MATERIAL_FIELDS)
    values.update(current_facts=(), predicates=(), evidence_queries=(), producers=tuple(producers), task_candidates=tuple(tasks),
                  intent=record("obligation_graph_compiler.TypedIntent", {
                      "intent_id": "intent:authored-source-successor", "desired_predicates": tuple(predicates),
                      "source_refs": ("source:authored-runtime",), "current_root_id": snapshot_cid, "metadata": {},
                  }), frozen_goal=record("adaptive_planner.FrozenPlanningGoal", {
                      "goal_id": "goal:runtime", "goal_content_id": "baguqeera4da5a3nxyystiby75cuecis6uqovskarvl5ch5fijthl7szrgutq",
                      "repository_tree_id": snapshot_cid, "policy": record("plan_evaluator.EvidenceAwarePlanPolicy", policy),
                  }), candidate_context={"repository_paths": ["calc.py"], "task_metadata": {
                      task: {"predicted_files": ["calc.py"], "scope_ids": ["scope:calc.py"], "resource_classes": ["cpu"]} for task in TASKS
                  }}, extra={"authored_review": "review:complete-runtime-requirements"})
    return {field: project(value) for field, value in values.items()}


def decode_preimage(value, depth=0):
    require(depth <= MAX_DEPTH, "typed preimage depth bound")
    if type(value) is not dict:
        require(type(value) in (str, int, float, bool, type(None)), "typed semantic scalar required")
        if type(value) is float:
            require(math.isfinite(value), "finite typed scalar required")
        return value
    if set(value) == {"$mapping"}:
        require(type(value["$mapping"]) is dict, "typed mapping required")
        return {key: decode_preimage(child, depth + 1) for key, child in value["$mapping"].items()}
    if set(value) == {"$sequence", "items"}:
        require(value["$sequence"] in ("tuple", "list") and type(value["items"]) is list, "typed sequence required")
        return [decode_preimage(child, depth + 1) for child in value["items"]]
    if set(value) == {"$record", "fields"}:
        require(type(value["$record"]) is str and value["$record"] in RECORD_FIELDS, "unreviewed native record class")
        closed(value["fields"], {"$mapping"}, "typed record fields tag")
        closed(value["fields"]["$mapping"], RECORD_FIELDS[value["$record"]], "closed typed native record fields")
        return {"native_type": value["$record"], "fields": decode_preimage(value["fields"], depth + 1)}
    if set(value) == {"$enum", "value"}:
        require(type(value["$enum"]) is str and value["$enum"] in ENUM_VALUES
                and type(value["value"]) is str and value["value"] in ENUM_VALUES[value["$enum"]], "unreviewed native enum class or value")
        return {"enum_type": value["$enum"], "value": value["value"]}
    raise ValueError("unreviewed typed preimage tag")


def material_binding(value):
    closed(value, {"schema", "field_digests", "unsupported_fields", "reuse_supported", "opaque_material_nonce"}, "closed material binding")
    require(value["schema"] == "ipfs_accelerate_py/agent-supervisor/plan-create-semantic-material-binding@1"
            and value["unsupported_fields"] == {} and value["reuse_supported"] is True and value["opaque_material_nonce"] == "", "supported material binding")
    closed(value["field_digests"], MATERIAL_FIELDS, "twenty material digest fields")
    for declared in value["field_digests"].values():
        require(type(declared) is str and declared.startswith("sha256:"), "typed material digest namespace")
        digest(declared[7:])


def preimages(export, planning, current_head):
    closed(export, {"schema", "entries", "capture", "execution_attestation"}, "closed semantic preimage export")
    require(export["schema"] == "source-successor-planning-semantic-preimages@1"
            and export["capture"] == "explicit_reconstruction_checked_against_native_consumed_material_binding"
            and export["execution_attestation"] is False and type(export["entries"]) is list and len(export["entries"]) == 3,
            "three reconstructed material variants required")
    variants, identifiers = [], []
    for entry in export["entries"]:
        closed(entry, {"binding", "preimages"}, "closed material variant")
        material_binding(entry["binding"])
        closed(entry["preimages"], MATERIAL_FIELDS, "twenty typed preimage fields")
        total, decoded = 0, {}
        for field in sorted(MATERIAL_FIELDS):
            raw = wire(entry["preimages"][field])
            total += len(raw)
            expected = "sha256:" + sha256(b"plan-create-semantic-input\n" + field.encode("utf-8") + b"\n" + raw).hexdigest()
            require(entry["binding"]["field_digests"][field] == expected, "typed material byte digest differs: " + field)
            decoded[field] = decode_preimage(entry["preimages"][field])
        require(total <= MAX_FILE, "combined typed material byte bound")
        identifiers.append(sha256(wire(entry["binding"])).hexdigest())
        variants.append({"binding": entry["binding"], "fields": entry["preimages"], "decoded": decoded, "bytes": total})
    require(identifiers == sorted(set(identifiers)), "three distinct ordered material variants")
    fixture = authored_fields(current_head["snapshot_cid"])
    authored = [index for index, variant in enumerate(variants) if same(variant["fields"], fixture)]
    require(len(authored) == 1, "complete exact authored fixture meanings required")
    consumed = planning["repository_preview"]["input_snapshot"]["material_binding"]
    material_binding(consumed)
    matching = [index for index, variant in enumerate(variants) if same(variant["binding"], consumed)]
    require(len(matching) == 1, "consumed native snapshot variant binding")
    context = planning["repository_preview"]["structural_context"]
    context_cid = planning["repository_preview"]["structural_context_cid"]
    extra = {"authored_review": "review:complete-runtime-requirements",
             "codebase_source_delta_advisory": planning["codebase_source_delta_advisory"]}
    intermediate = {**fixture, "extra": project(extra)}
    candidate = decode_preimage(fixture["candidate_context"])
    expanded = {**intermediate,
                "scan": project({"scan_cid": planning["repository_preview"]["preview"]["scan_cid"], "structural_codebase": context}),
                "candidate_context": project({**candidate, "structural_codebase": context, "structural_codebase_context_cid": context_cid}),
                "extra": project({**extra, "root_observation_profile": "repository-live-root-observation@1",
                                  "structural_codebase": context, "structural_codebase_context_cid": context_cid})}
    expected_variants = {wire(fields) for fields in (fixture, intermediate, expanded)}
    require({wire(variant["fields"]) for variant in variants} == expected_variants
            and same(variants[matching[0]]["fields"], expanded), "exact authored, advisory and consumed material meanings")
    stable_fields = MATERIAL_FIELDS - {"candidate_context", "extra", "scan"}
    for variant in variants:
        for field in stable_fields:
            require(same(variant["fields"][field], fixture[field]), "authored meaning differs: " + field)
        for key in ("repository_paths", "task_metadata"):
            require(same(variant["decoded"]["candidate_context"][key], variants[authored[0]]["decoded"]["candidate_context"][key]), "authored candidate meaning differs")
    native = variants[matching[0]]["decoded"]
    require(same(native["scan"], {"scan_cid": planning["repository_preview"]["preview"]["scan_cid"], "structural_codebase": context}), "consumed structural scan binding")
    require(same(native["candidate_context"]["structural_codebase"], context)
            and native["candidate_context"]["structural_codebase_context_cid"] == planning["repository_preview"]["structural_context_cid"], "consumed candidate structural binding")
    for variant in variants:
        extra = variant["decoded"]["extra"]
        require(extra["authored_review"] == "review:complete-runtime-requirements", "authored review binding")
        if "codebase_source_delta_advisory" in extra:
            require(same(extra["codebase_source_delta_advisory"], planning["codebase_source_delta_advisory"]), "typed advisory binding")
    closed(native["extra"], {"authored_review", "codebase_source_delta_advisory", "root_observation_profile", "structural_codebase", "structural_codebase_context_cid"}, "consumed extra fields")
    require(same(native["extra"]["structural_codebase"], context)
            and native["extra"]["structural_codebase_context_cid"] == planning["repository_preview"]["structural_context_cid"], "consumed extra structural binding")
    require(native["extra"]["root_observation_profile"] == "repository-live-root-observation@1", "root observation profile declaration")
    return {"variant_count": 3, "fields_per_variant": 20, "byte_digests_rederived": 60,
            "consumed_variant_index": matching[0], "authored_variant_index": authored[0],
            "binding_ids": identifiers, "bindings": [variant["binding"] for variant in variants],
            "variant_preimage_bytes": [variant["bytes"] for variant in variants],
            "typed_record_classes": sorted(RECORD_FIELDS), "typed_enum_classes": sorted(ENUM_VALUES),
            "capture": export["capture"], "execution_attestation": False,
            "digest_encoding": "sha256(domain LF field LF typed JSON sorted keys, compact separators, ensure_ascii=True)",
            "digest_domain": "plan-create-semantic-input", "semantic_digest_replay_qualified": False}


def false_fields(value, fields, message):
    require(all(value[field] is False for field in fields), message)


def planning_receipt(planning, authored, export, native, audit, namespace):
    require(planning["schema"] == "supervisor-codebase-source-delta-plan-preview@1", "native planning preview schema")
    closed(planning["authority"], PLAN_AUTHORITY, "closed planning authority")
    false_fields(planning["authority"], PLAN_AUTHORITY, "planning authority must remain false")
    false_fields(planning, ("model_advanced", "numerical_reuse", "physical_absence_verified", "production_admitted", "worker_launched"), "planning advisory scope")
    for field in ("inference_calls", "training_steps", "source_property_solver_calls"):
        require(exact_int(planning[field]) == 0, "recorded planning no-fit/no-inference counts")
    require(planning["current_facts"] == [] and planning["removed_task_ids"] == []
            and same(planning["declared_requirement_ids"], GOALS) and same(planning["declared_task_ids"], TASKS)
            and same(planning["residual_task_ids"], TASKS)
            and same(planning["residual_requirements"], [{"predicate_id": goal, "status": "runtime_behavior_unresolved"} for goal in GOALS]),
            "every authored runtime goal and task remains residual")
    require(planning["result_cid"] == native["planning_result_cid"] == audit["planning"]["result_cid"], "declared planning result identity")
    producer = planning["producer"]
    require(producer["module"] == "ipfs_accelerate_py.agent_supervisor.planning.codebase_source_delta_context"
            and producer["scope"] == "listed_local_file_only_not_execution_attestation", "declared planning producer scope")
    digest(producer["sha256"])
    repository = planning["repository_preview"]
    require(repository["schema"] == "supervisor-repository-plan-preview@1", "repository preview schema")
    false_fields(repository, ("completion_authority", "execution_authority", "production_admitted", "proof_authority", "source_semantics_verified", "worker_launched"), "repository preview authority")
    require(exact_int(repository["model_calls"]) == exact_int(repository["observed_facts_supplied"]) == 0, "model-off preview counts")
    context = repository["structural_context"]
    require(context["schema"] == "supervisor-structural-codebase-context@1" and context["authority"] == "structural_only", "structural context scope")
    false_fields(context, ("completion_authority", "execution_authority", "proof_authority", "source_semantics_verified"), "structural context authority")
    require(context["head"]["snapshot_cid"] == native["current_head"]["snapshot_cid"], "current head structural context")
    advisory = planning["codebase_source_delta_advisory"]
    require(advisory["schema"] == "codebase-source-delta-advisory-refs@1", "declared source advisory schema")
    closed(advisory["authority"], PLAN_AUTHORITY, "closed source advisory authority")
    false_fields(advisory["authority"], PLAN_AUTHORITY, "source advisory authority remains false")
    require(advisory["artifact_cid"] == native["source_delta_cid"]
            and same(advisory["current_head"], native["current_head"]), "declared source advisory identity binding")
    snapshot, preview = repository["input_snapshot"], repository["preview"]
    require(snapshot["schema"] == "ipfs_accelerate_py/agent-supervisor/plan-create-input-snapshot@2", "native snapshot schema")
    require(preview["schema"] == "ipfs_accelerate_py/agent-supervisor/plan-create-preview-receipt@1"
            and preview["interface"] == "PlanCreateService@1" and preview["mode"] == "deterministic"
            and preview["read_only"] is True and preview["verdict"] == "review_only" and preview["wrote_effects"] == [], "review-only deterministic preview")
    request, materials = authored["request"], authored["materials"]
    require(request["schema"] == "ipfs_accelerate_py/agent-supervisor/plan-create-request@1"
            and exact_int(request["contract_version"]) == 1 and request["observe_roots"] is False
            and request["caller"] == "principal:unknown" and request["idempotency_key"] == "", "authored request contract")
    require(request["repository_root"] == snapshot["repository_root"] == str(namespace / "repository"), "declared repository path; never opened")
    for field in ("alias_prefix", "board_namespace", "budget", "dirty_tree_policy", "fallback_policy", "optional_analysis_operations",
                  "optional_logic_families", "repository_id", "required_analysis_operations", "required_logic_families", "roots",
                  "scope_paths", "supervisor_profile", "task_source_kind"):
        require(same(request[field], snapshot[field]), "authored request snapshot binding: " + field)
    require(request["alias_prefix"] == "SUCCESSOR" and request["board_namespace"] == "source-successor"
            and request["repository_id"] == "qualification:source-successor" and request["scope_paths"] == ["calc.py"]
            and request["task_source_kind"] == "both" and request["fallback_policy"] == "fail_closed"
            and request["dirty_tree_policy"] == "observe_and_bind", "authored request review scope")
    roots = request["roots"]
    closed(roots, {"schema", "contract_version", "repository_id", "repository_root_cid", "task_source_id", "task_source_revision",
                   "program_root", "legal_ir_root", "intent_ir_root", "security_ir_root", "policy_root", "configuration_root",
                   "capability_catalog_root", "provider_catalog_root", "usage_policy_root", "dirty_worktree_root"}, "closed authored authority roots")
    require(roots["schema"] == "ipfs_accelerate_py/agent-supervisor/plan-authority-roots@1"
            and exact_int(roots["contract_version"]) == 1 and roots["repository_id"] == request["repository_id"]
            and roots["task_source_id"] == "source:authored-runtime", "typed authority root declarations")
    for field, declared in roots.items():
        if field not in ("schema", "contract_version"):
            identity(declared)
    budget = request["budget"]
    closed(budget, {"schema", "contract_version", "max_analysis_operations", "max_cost_micros", "max_evidence_items", "max_goals",
                   "max_graph_depth", "max_latency_ms", "max_logic_families", "max_model_calls", "max_output_paths",
                   "max_provider_tokens", "max_ready_width", "max_repair_rounds", "max_scan_bytes", "max_tasks"}, "closed request budget")
    require(budget["schema"] == "ipfs_accelerate_py/agent-supervisor/plan-request-budget@1", "request budget schema")
    for field in budget:
        if field != "schema":
            exact_int(budget[field], 2**31)
    require(budget["contract_version"] == 1 and budget["max_model_calls"] == budget["max_cost_micros"] == 0
            and budget["max_latency_ms"] == 120000 and budget["max_tasks"] == 256 and budget["max_goals"] == 64
            and budget["max_graph_depth"] == 16 and budget["max_ready_width"] == 1 and budget["max_repair_rounds"] == 2,
            "authored model-off planning budget")
    require(materials["schema"] == "ipfs_accelerate_py/agent-supervisor/plan-create-materials@1"
            and materials["current_roots"] == {} and materials["evidence_adapter_slots"] == []
            and materials["extra_keys"] == ["authored_review"], "authored materials declaration")
    false_fields(materials, ("has_admission_materials", "has_model_provider", "has_workflow_request"), "absent authored admission and model materials")
    require(preview["input_snapshot_cid"] == snapshot["snapshot_cid"] == audit["planning"]["input_snapshot_cid"]
            and preview["request_cid"] == snapshot["request_cid"] and same(preview["roots"], snapshot["roots"])
            and preview["receipt_cid"] == audit["planning"]["receipt_cid"], "declared snapshot and receipt identities")
    stages = preview["stage_results"]
    require(type(stages) is list and len(stages) == 8, "all eight planning stages")
    expected_blockers = [[], [], [], [], [], [], BLOCKERS[:2], [BLOCKERS[2], BLOCKERS[3], *([BLOCKERS[4]] * 3), BLOCKERS[5]]]
    summary = []
    artifact_fields = ("scan_cid", "query_plan_cid", "evidence_bundle_cid", "obligation_graph_cid", "candidate_portfolio_cid", "critique_cid", "admission_receipt_cid", "execution_plan_cid")
    for index, stage in enumerate(stages):
        closed(stage, {"schema", "stage", "passed", "artifact_cid", "result_cid", "blockers", "detail_ids", "message"}, "closed native stage result")
        require(stage["schema"] == "ipfs_accelerate_py/agent-supervisor/plan-create-stage-result@1"
                and stage["stage"] == STAGES[index] and stage["passed"] is (index < 6)
                and same(stage["blockers"], expected_blockers[index]) and stage["artifact_cid"] == preview[artifact_fields[index]], "exact native stage outcome and artifact")
        require(type(stage["detail_ids"]) is list and len(stage["detail_ids"]) <= 32, "stage detail population")
        for declared in (stage["artifact_cid"], stage["result_cid"], *stage["detail_ids"]):
            identity(declared)
            require(declared in preview["artifact_refs"] or declared in stage["detail_ids"], "stage reference declaration")
        summary.append({key: stage[key] for key in ("stage", "passed", "artifact_cid", "result_cid", "blockers")})
    require(preview["rejection_reasons"] == BLOCKERS and preview["plan_root_cid"] == preview["critique_cid"], "review-only critic and rejection frontier")
    require(type(preview["artifact_refs"]) is list and len(preview["artifact_refs"]) == 17
            and len(set(preview["artifact_refs"])) == 17, "recorded artifact reference population")
    for declared in preview["artifact_refs"]:
        identity(declared)
    require(same(audit["planning"]["requirements"], GOALS) and same(audit["planning"]["tasks"], TASKS)
            and exact_int(audit["planning"]["observed_facts"]) == exact_int(audit["planning"]["removed_tasks"]) == 0
            and audit["planning"]["proof_authority"] is False, "audit residual planning accounting")
    require(audit["planning"]["preimage_capture_scope"] == "explicit reconstruction bound to recorded native consumed snapshot; not execution attestation"
            and audit["planning"]["cold_preimage_scope"] == "same warm reconstructed preimages reused against exactly identical cold consumed binding", "reconstructed and reused preimage disclosure")
    semantic = preimages(export, planning, native["current_head"])
    return {"declared_requirement_ids": GOALS, "declared_task_ids": TASKS, "residual_requirements": planning["residual_requirements"],
            "residual_task_ids": TASKS, "runtime_fact_count": 0, "tasks_omitted_count": 0,
            "stage_count": 8, "passed_stage_count": 6, "failed_stage_count": 2, "stages": summary,
            "rejection_reasons": preview["rejection_reasons"], "wrote_effects": [], "verdict": "review_only",
            "request_budget": budget, "declared_result_cid": planning["result_cid"],
            "declared_input_snapshot_cid": snapshot["snapshot_cid"], "declared_receipt_cid": preview["receipt_cid"],
            "preimage_materials": semantic, "preimage_capture_scope": audit["planning"]["preimage_capture_scope"],
            "cold_preimage_scope": audit["planning"]["cold_preimage_scope"],
            "artifact_identity_scope": "Native artifact IDs are declarations; critic, obligation and execution-plan bodies are not selected"}


def native_receipts(machine, audit, native, failed):
    require(native["schema"] == failed["schema"] == "codebase-source-successor-native-qualification@1"
            and native["qualified"] is True and failed["qualified"] is False, "successful and failed native receipt scopes")
    require(native["scope"] == failed["scope"] == "fresh_300_member_successor_and_two_32_member_cpu8d_prefix_pages", "bounded native prefix scope")
    false_fields(machine, ("384d_qualified", "complete_successor_scan_qualified", "cuda_qualified", "production_default_activated",
                          "production_task_status_changed", "proof_authority", "runtime_reexecuted_here", "scan_execution_attested",
                          "signed_successor_worker_qualified", "source_execution_attested"), "public review non-authority scope")
    require(exact_int(machine["production_open_tasks"]) == 32, "production task population remains open")
    false_fields(audit, ("384d_qualified", "complete_scan_qualified", "cuda_qualified", "git_executed", "mutable_working_checkout_qualified",
                        "native_owners_opened", "numerical_execution_independently_reperformed", "primary_writes", "process_origin_attested",
                        "proof_authority", "sql_executed", "worker_admission_qualified"), "retained auditor non-execution scope")
    for receipt in (native, failed):
        false_fields(receipt, ("384d_qualified", "complete_scan_qualified", "cuda_qualified", "production_default_activated",
                              "proof_authority", "repository_code_executed", "worker_admission_qualified"), "native receipt non-production scope")
        for field in ("training_attempts_after_setup", "inference_attempts_during_selection_or_cold_receiving", "source_property_solver_calls", "inherited_scan_pages", "inherited_setup_epochs"):
            require(exact_int(receipt[field]) == 0, "recorded no-fit receiving counts")
        closed(receipt["final_resources"], {"active_lease_count", "waiting_request_count"}, "final resource counts")
        require(all(exact_int(count) == 0 for count in receipt["final_resources"].values()), "recorded final resource drain")
        attempts = receipt["setup_training_attempts"]
        require(type(attempts) is list and len(attempts) == 2, "two explicit setup training attempts")
        for index, attempt in enumerate(attempts):
            closed(attempt, {"name", "version_id", "requested_epochs", "actual_completed_epochs", "unknown_actual_epochs_on_failure"}, "closed explicit setup attempt")
            require(attempt["name"] == ("root", "child")[index] and exact_int(attempt["requested_epochs"]) == 1
                    and exact_int(attempt["actual_completed_epochs"]) == 1 and attempt["unknown_actual_epochs_on_failure"] is False
                    and attempt["version_id"] == receipt[("parent_version_id", "child_version_id")[index]], "known setup epoch accounting")
        require(exact_int(receipt["new_fitting_epochs"]) == sum(row["actual_completed_epochs"] for row in attempts) == 2, "setup epoch sum")
        exact_int(receipt["pid"], 2**31)
        number(receipt["recorded_seconds"])
        number(receipt["elapsed_seconds_so_far"])
    false_fields(native, ("model_head_promoted", "numerical_reuse"), "native model reuse scope")
    require(native["cold_receiving_verified"] is True and native["native_owner_unchanged_except_explicit_reopen"] is True
            and native["selected_producers_unchanged"] is True and native["original_source_artifacts_preserved"] is True
            and exact_int(native["source_owner_reopens"]) == exact_int(native["model_owner_reopens"]) == 1
            and exact_int(native["new_scan_pages_created"]) == 2 and exact_int(failed["new_scan_pages_created"]) == 0,
            "two fresh prefixes and same-process native reopen declarations")
    coverage = native["coverage"]
    require(exact_int(coverage["previous_entries"]) == exact_int(coverage["current_entries"]) == 300, "declared successor membership scope")
    prefix = native["prefix_coverage"]
    require(same(prefix, {"inventory_entries": 32, "inferred_rows": 22, "dispositions": {"inferred": 22, "deferred_budget": 9, "unindexed": 1}}), "exact incomplete prefix frontier")
    equivalence = native["opt_out_equivalence"]
    require(equivalence["scope"] == "first32_ordered_members_only" and equivalence["entries_coverage_and_inference_exact"] is True
            and equivalence["throughput_qualified"] is False
            and equivalence["optimized_page_cid"] == native["prefix_page_cid"] and equivalence["optimized_root_cid"] == native["root_cid"]
            and equivalence["optimized_page_cid"] != equivalence["reference_page_cid"]
            and equivalence["optimized_root_cid"] != equivalence["reference_root_cid"], "declared default/reference first32 equivalence")
    for key, value in equivalence.items():
        if key.endswith("_cid"):
            identity(value)
    for field, value in machine["native_work"].items():
        require(same(value, native[field]), "public native work declaration differs: " + field)
    failed_review = machine["failed_native_attempt"]
    for field in ("error", "error_type", "final_resources", "new_fitting_epochs", "new_scan_pages_created", "phases", "qualified", "recorded_seconds"):
        require(same(failed_review[field], failed[field]), "failed attempt declaration differs: " + field)
    require(failed["error_type"] == "LeaseTimeoutError" and failed["error"] == "resumable inventory deadline exceeded", "retained failed reference deadline")
    require(same(native["operation_deadline_seconds"], DEADLINES), "qualification-only reference deadline override")
    phases, failed_phases = native["phases"], failed["phases"]
    for rows, names in ((phases, PHASES), (failed_phases, PHASES[:8])):
        require(type(rows) is list and len(rows) == len(names), "recorded phase population")
        for index, phase in enumerate(rows):
            closed(phase, {"name", "elapsed_seconds", "status"}, "closed recorded phase")
            require(phase["name"] == names[index] and phase["status"] == ("failed" if rows is failed_phases and index == 7 else "completed"), "successful and failed phase outcomes")
            number(phase["elapsed_seconds"])
    require(120 < failed_phases[7]["elapsed_seconds"] < 600 and 120 < phases[7]["elapsed_seconds"] < 600, "failed default deadline and successful reference override remain separate")
    controls = native["controls"]
    require(type(controls) is list and len(controls) == 2, "retained native refusal controls")
    control_errors = (("old_model_for_new_head", "CodebaseSuccessorScanError", "selected version must be an exact registered direct child"),
                      ("precancelled_selection_receiving", "LeaseCancelledError", "resource lease request was cancelled"))
    for row, expected in zip(controls, control_errors, strict=True):
        closed(row, {"name", "error_type", "error", "refused", "elapsed_seconds"}, "closed native refusal observation")
        require((row["name"], row["error_type"], row["error"]) == expected and row["refused"] is True, "native refusal identity")
        number(row["elapsed_seconds"])
    costs = audit["costs"]
    require(same(costs["phases"], phases) and same(costs["explicit_setup_training"], native["setup_training_attempts"])
            and same(costs["operation_deadline_seconds"], DEADLINES) and costs["phases_are_cooperative_not_kernel_deadlines"] is True
            and same(costs["recorded_native_seconds"], native["recorded_seconds"]), "auditor recorded costs")
    for field in ("training_attempts_after_setup", "inference_attempts_during_selection_or_cold_receiving", "source_property_solver_calls", "new_fitting_epochs"):
        require(exact_int(costs[field]) == native[field], "auditor attempt accounting")
    public_cost = machine["costs"]
    require(same(public_cost["qualified_native_seconds"], native["recorded_seconds"])
            and same(public_cost["failed_native_seconds"], failed["recorded_seconds"])
            and same(public_cost["qualified_phase_seconds"], {row["name"]: row["elapsed_seconds"] for row in phases})
            and exact_int(public_cost["benchmark_new_fitting_epochs_across_two_attempts"]) == 4
            and exact_int(public_cost["inherited_benchmark_fitting_epochs"]) == 0
            and exact_int(public_cost["unit_fixture_new_fitting_epochs_separate"]) == 2, "public successful/failed/setup costs separate")
    number(public_cost["independent_reader_seconds"])
    return ({"declared_current_members": 300, "fresh_prefix_pages": 2, "ordered_members_per_route": 32,
             "inferred_rows_per_route": 22, "deferred_budget_per_route": 9, "unindexed_per_route": 1,
             "completion_qualified": False, "distinct_64_members_qualified": False,
             "scope": "Two routes over the same first32 ordered members; page bodies are not selected",
             "declared_prefix_equivalence": equivalence},
            {"training_attempts_after_setup": 0, "inference_attempts_during_selection_or_cold_receiving": 0,
             "source_property_solver_calls": 0, "source_owner_reopens": 1, "model_owner_reopens": 1,
             "same_process_reopen_declaration": True, "process_restart_qualified": False,
             "warm_cold_result_bytes_identical": True, "warm_preimages_reused_for_cold_receiving": True,
             "retained_refusals": controls, "whole_planner_solver_free_qualified": False},
            {"successful_native_recorded_seconds": native["recorded_seconds"], "failed_native_recorded_seconds": failed["recorded_seconds"],
             "independent_reader_recorded_seconds": public_cost["independent_reader_seconds"],
             "successful_phases": phases, "failed_phases": failed_phases, "operation_deadline_seconds": DEADLINES,
             "failed_reference_deadline_seconds": 120, "failed_reference_error": failed["error"],
             "failed_reference_error_type": failed["error_type"], "failed_attempt_qualified": False,
             "successful_setup_training_attempts": native["setup_training_attempts"], "failed_setup_training_attempts": failed["setup_training_attempts"],
             "benchmark_setup_epochs_across_attempts": 4, "unit_fixture_setup_epochs_separate": 2,
             "additional_attempted_training_epochs": 0, "cost_scope": "Recorded cooperative phases and attempts; do not sum nested timings or infer unique CPU/total wall time"})


def resources(resource, native, audit):
    closed(resource, {"schema_version", "config", "leases", "waiters", "metrics", "next_sequence", "proof_backoff"}, "closed scheduler receipt")
    require(resource["schema_version"] == "legal-ir-global-resource-scheduler-v1" and resource["leases"] == {}
            and resource["waiters"] == {} and resource["proof_backoff"] == {}
            and same(resource["config"], native["scheduler_configuration"]), "recorded scheduler scope and drain")
    metrics = resource["metrics"]
    closed(metrics, {"acquisitions_total", "releases_total", "cancellations_total", "timeouts_total", "recoveries_total",
                     "recovered_leases_total", "saturation_events_total", "lanes", "wait_samples", "wait_seconds_max", "wait_seconds_total"}, "closed scheduler metrics")
    expected = {"acquisitions_total": 49, "releases_total": 49, "cancellations_total": 1, "timeouts_total": 0,
                "recoveries_total": 0, "recovered_leases_total": 0, "saturation_events_total": 0}
    for field, count in expected.items():
        require(exact_int(metrics[field]) == count, "recorded scheduler typed count")
    require(exact_int(resource["next_sequence"]) == 51, "scheduler sequence declaration")
    closed(metrics["lanes"], {"snapshot_evaluation", "trainer"}, "scheduler lane population")
    for lane, counts in (("snapshot_evaluation", (45, 1, 0, 46)), ("trainer", (4, 0, 0, 4))):
        row = metrics["lanes"][lane]
        closed(row, {"acquisitions_total", "cancellations_total", "timeouts_total", "wait_count", "wait_seconds_max", "wait_seconds_total"}, "closed scheduler lane")
        require(tuple(exact_int(row[field]) for field in ("acquisitions_total", "cancellations_total", "timeouts_total", "wait_count")) == counts, "scheduler lane typed counts")
        number(row["wait_seconds_max"])
        number(row["wait_seconds_total"])
    require(math.isclose(metrics["wait_seconds_total"], sum(row["wait_seconds_total"] for row in metrics["lanes"].values()), abs_tol=1e-15)
            and math.isclose(metrics["wait_seconds_max"], max(row["wait_seconds_max"] for row in metrics["lanes"].values()), abs_tol=1e-15), "scheduler aggregate lane costs")
    samples = metrics["wait_samples"]
    require(type(samples) is list and len(samples) == 50, "scheduler wait sample population")
    for sample in samples:
        number(sample)
    require(math.isclose(number(metrics["wait_seconds_max"]), max(samples), abs_tol=1e-15)
            and math.isclose(number(metrics["wait_seconds_total"]), sum(samples), abs_tol=1e-15), "scheduler wait sample costs")
    observed = audit["resources"]
    require(exact_int(observed["leases"]) == exact_int(observed["waiters"]) == 0
            and same(observed["final_resources"], native["final_resources"])
            and observed["kernel_memory_enforcement_claimed"] is False, "auditor resource drain scope")
    return {"recorded_final_resources": native["final_resources"], "scheduler_metrics": metrics,
            "next_sequence": 51, "scheduler_configuration": resource["config"],
            "current_resource_cleanup_verified": False, "kernel_resource_enforcement_qualified": False}


def scope():
    return {**dict.fromkeys(TRUE_FLAGS, True), **dict.fromkeys(FALSE_FLAGS, False), **dict.fromkeys(ZERO_FIELDS, 0)}


def write_new(path, raw):
    require(not path.exists() and not path.is_symlink(), "fresh output member required")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o444)
    try:
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(fd)
    finally:
        os.close(fd)


def output_population(output, files):
    expected = {"retained", *files}
    found = set()
    for parent, dirs, names in os.walk(output, followlinks=False):
        for name in (*dirs, *names):
            path = Path(parent) / name
            require(not path.is_symlink() and path.resolve(strict=True) == path, "canonical output population")
            found.add(path.relative_to(output).as_posix())
    require(found == expected, "exact local output population")


def audit(manifest, output, *, relocated_sources=None):
    started = time.monotonic()
    original, copies = Capture(relocated_sources, started=started), Capture(started=started)
    manifest, output = lexical_path(str(manifest)), lexical_path(str(output))
    require(output.parent.resolve(strict=True) == output.parent and not output.exists() and not output.is_symlink(), "fresh canonical output directory required")
    raw_manifest = original.read(manifest, maximum=MAX_MANIFEST)
    selection = document(raw_manifest)
    closed(selection, {"schema", "selected_profile", "selected_files"}, "closed successor input manifest")
    require(selection["schema"] == INPUT_SCHEMA and selection["selected_profile"] == PROFILE
            and type(selection["selected_files"]) is list and len(selection["selected_files"]) == len(ROLES), "fixed selected profile and population")
    pins = {}
    for role, row in zip(ROLES, selection["selected_files"], strict=True):
        closed(row, {"role", "path", "sha256", "size_bytes"}, "closed selected descriptor")
        require(row["role"] == role, "fixed ordered selected roles")
        pins[role] = descriptor({key: row[key] for key in ("path", "sha256", "size_bytes")})
    require(pins["machine_review"]["sha256"] == PUBLIC_ANCHOR, "fixed public review anchor")
    require(len({pin["path"] for pin in pins.values()}) == len(ROLES) and str(manifest) not in {pin["path"] for pin in pins.values()}, "disjoint original input population")
    if relocated_sources is not None:
        require(type(relocated_sources) is dict and set(relocated_sources) == {str(manifest), *(pin["path"] for pin in pins.values())}, "closed explicit relocated sources")
        require(len(set(relocated_sources.values())) == len(relocated_sources), "distinct relocated physical inputs")
    physical_inputs = [Path(relocated_sources.get(pin["path"], pin["path"])) if relocated_sources else Path(pin["path"]) for pin in pins.values()]
    physical_inputs.append(Path(relocated_sources[str(manifest)]) if relocated_sources else manifest)
    require(all(output != path and output not in path.parents and path not in output.parents for path in physical_inputs), "disjoint input and output paths")
    bodies = {"machine_review": original.read(Path(pins["machine_review"]["path"]), pins["machine_review"])}
    docs = {"machine_review": document(bodies["machine_review"])}
    machine = docs["machine_review"]
    path = Path(pins["machine_review"]["path"])
    tail = Path("external/ipfs_accelerate/docs/architecture/repository_proof_index_and_codebase_ir.source_successor_review.json")
    require(path.parts[-len(tail.parts):] == tail.parts, "machine review location before following descriptors")
    workspace = path.parents[4]
    require(same(pins["closed_audit"], declared_pin(workspace, machine["independent_closed_audit"])), "audit descriptor before opening")
    bodies["closed_audit"] = original.read(Path(pins["closed_audit"]["path"]), pins["closed_audit"])
    docs["closed_audit"] = document(bodies["closed_audit"])
    _, namespace = selected_bindings(pins, machine, docs["closed_audit"])
    for role in ROLES[2:]:
        bodies[role] = original.read(Path(pins[role]["path"]), pins[role])
        docs[role] = document(bodies[role])
    require(bodies["planning_preview"] == bodies["cold_planning_preview"]
            and bodies["planning_semantic_preimages"] == bodies["cold_planning_semantic_preimages"], "identical warm/cold results and reused preimages required")
    frontier, receiving, costs = native_receipts(machine, docs["closed_audit"], docs["native_result"], docs["failed_native_result"])
    planning = planning_receipt(docs["planning_preview"], docs["authored_planning_inputs"], docs["planning_semantic_preimages"],
                                docs["native_result"], docs["closed_audit"], namespace)
    resource = resources(docs["resource_admission"], docs["native_result"], docs["closed_audit"])
    original.stable()
    output.mkdir(mode=0o755)
    retained = output / "retained"
    retained.mkdir(mode=0o755)
    copy_rows, members = [], ["retained/input.json"]
    write_new(retained / "input.json", raw_manifest)
    copies.read(retained / "input.json", maximum=MAX_MANIFEST)
    for index, role in enumerate(ROLES):
        path = retained / (f"{index:02}-" + role + ".json")
        write_new(path, bodies[role])
        pin = {"path": str(path), "sha256": pins[role]["sha256"], "size_bytes": pins[role]["size_bytes"]}
        require(copies.read(path, pin) == bodies[role], "original and retained copy bytes")
        copy_rows.append({"role": role, **pins[role], "retained_copy": pin})
        members.append(path.relative_to(output).as_posix())
    nested = {"schema": "codebase-ir-successor-planning-selected-custody@1", "status": "passed", "qualified": True, "selected_files": copy_rows,
              "manifest_sha256": sha256(raw_manifest).hexdigest(), "scope": scope(),
              "original_capture_bytes": original.total, "copy_capture_bytes": copies.total,
              "planning": planning, "frontier": frontier, "receiving": receiving, "costs": costs, "resources": resource}
    nested_path = output / "selected_custody.json"
    nested_raw = bounded_canonical(nested, MAX_REPORT)
    write_new(nested_path, nested_raw)
    members.append(nested_path.name)
    report = {"schema": SCHEMA, "workflow": "successor_planning_custody", "selected_profile": PROFILE,
              "status": "passed", "qualified": True, "selected_files": copy_rows,
              "selected_file_count": len(ROLES), "selected_input_bytes": sum(pin["size_bytes"] for pin in pins.values()),
              "manifest_sha256": sha256(raw_manifest).hexdigest(),
              **{role + "_sha256": pins[role]["sha256"] for role in ROLES}, **scope(), "scope": scope(),
              "planning": planning, "frontier": frontier, "receiving": receiving, "costs": costs, "resources": resource,
              "declared_missing_closure": {key: "unknown_not_selected" for key in ("critic_body", "obligation_graph_body", "execution_plan_body")},
              "limits": {"max_file_bytes": MAX_FILE, "max_original_bytes": MAX_BYTES, "max_copy_bytes": MAX_BYTES,
                         "max_files_per_cache": MAX_FILES, "max_manifest_bytes": MAX_MANIFEST, "max_report_bytes": MAX_REPORT,
                         "max_seconds": MAX_SECONDS, "max_depth": MAX_DEPTH, "max_values": MAX_VALUES},
              "custody": {"original_file_count": len(original.files), "copy_file_count": len(copies.files),
                          "original_capture_bytes": original.total, "copy_capture_bytes": copies.total,
                          "local_receipt": {"path": str(nested_path), "sha256": sha256(nested_raw).hexdigest(), "size_bytes": len(nested_raw)}},
              "elapsed_seconds": time.monotonic() - started}
    report_path = output / "successor_planning_custody.json"
    report_raw = bounded_canonical(report, MAX_REPORT)
    write_new(report_path, report_raw)
    members.append(report_path.name)
    original.stable()
    copies.stable()
    local = report["custody"]["local_receipt"]
    require(local["path"] == str(output / "selected_custody.json"), "exact local nested path before opening")
    require(Capture.raw(nested_path, len(nested_raw)) == nested_raw and document(nested_raw) == nested, "final local nested raw body")
    require(Capture.raw(report_path, len(report_raw)) == report_raw and same(document(report_raw), report), "final main raw report body")
    output_population(output, members)
    original.deadline()
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    report = audit(args.manifest, args.output)
    print(json.dumps({"qualified": report["qualified"], "report": str(args.output / "successor_planning_custody.json")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
