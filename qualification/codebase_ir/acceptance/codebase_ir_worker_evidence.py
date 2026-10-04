"""Stdlib read-only correlation of the retained model-off native worker fixture.

This audit verifies retained bytes and structural joins. It executes no worker,
opens no owner database or profile key, and authenticates no signature.
"""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
import math
import shlex
import sys
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

from codebase_ir_admission_evidence import (
    FALSE_FLAGS,
    OFFSET_CLAUSE,
    TYPE_CLAUSE,
    AdmissionEvidenceError,
    _envelope,
    _false,
    _workflow_payload,
    assert_admission,
    canonical,
    cid,
    exact,
    need,
    parse_document,
    raw_cid,
)
from codebase_ir_external_pins import _bounded_document
from codebase_ir_worker_git import hex_digest, verify_publication

SCHEMA = "codebase-ir-retained-worker-audit@1"
ORIGINAL_ROOT = PurePosixPath("/results/native")
ORIGINAL_CANDIDATE = "/opt/ipfs-supervisor/finite-handoffs/candidate.json"
MAX_FILES = 256
MAX_TOTAL_BYTES = 32 * 1024 * 1024
MAX_FILE_BYTES = 4 * 1024 * 1024
INVENTORY = ["calc.py", "check_offset.py", "check_type.py", "consumer.py", "decoy.py", "support.py", "unsupported.py"]
RECORDS = ("result.json", "before-admission.json", "materialized.json", "captured-inventory.json",
    "execution-scope.json", "candidate-descriptor.json", "prerequisite-native-claim.json", "prerequisite-validation.json",
    "native-lifecycle.json", "owner-fixture-worktree-cleanup.json", "successor-admission.json", "cold-admission.json",
    "cold-comparison.json", "fresh-process-replay.json", "historical-parent-artifact-pins.json")
PREVIEW_DIRECTORIES = {"before-preview", "materialization-preview", "successor-preview", "cold-preview"}
CANDIDATE_FALSE = {"execution_authority", "completion_authority", "publication_authority", "proof_authority",
    "source_semantics_verified", "task_omission_authority"}
SCOPE_FALSE = {"completion_authority", "production_activation", "proof_authority", "publication_authority", "task_omission_authority"}
COMPARISON_FIELDS = ["source_cid", "query", "domain_inputs", "observations", "eligible_requirement_ids",
    "residual_requirement_ids", "finite_selected_task_ids", "operation_catalog_cid", "model_status"]
EXECUTION_MODULES = {
    "benchmarks.agent_supervisor.container_coding.finite_repository_worker_experiment",
    "benchmarks.agent_supervisor.container_coding.finite_repository_admission_experiment",
    "ipfs_accelerate_py.agent_supervisor.runtime.finite_repository_admission",
    "ipfs_accelerate_py.agent_supervisor.runtime.finite_repository_execution",
    "ipfs_accelerate_py.agent_supervisor.runtime.finite_repository_candidate_runner",
    "ipfs_accelerate_py.agent_supervisor.entrypoints.admitted_benchmark_runtime",
    "ipfs_accelerate_py.agent_supervisor.runtime.candidate_execution",
    "ipfs_accelerate_py.agent_supervisor.runtime.local_completion_bridge",
    "ipfs_accelerate_py.agent_supervisor.runtime.local_planning_admission",
    "ipfs_accelerate_py.agent_supervisor.task_sources.intent_repository",
}
SCOPE_MODULES = {"ipfs_accelerate_py.agent_supervisor.entrypoints.admitted_benchmark_runtime",
    "ipfs_accelerate_py.agent_supervisor.planning.finite_integer_source_custody",
    "ipfs_accelerate_py.agent_supervisor.runtime.finite_repository_admission",
    "ipfs_accelerate_py.agent_supervisor.runtime.finite_repository_candidate_runner",
    "ipfs_accelerate_py.agent_supervisor.runtime.finite_repository_execution",
    "ipfs_accelerate_py.agent_supervisor.runtime.local_planning_admission"}
PARENT_CAS_CIDS = {
    "bafkreihlukkwaoux5x5ucijjm2ljevpiuxt5jai3hx3ta3vxbyeia74zgq",
    "bafkreicamh2xktfppuc4427e7z6eo2iagojomrma3g4r2ihbjpnoxa3eza",
    "bafkreih2m7trcclh3xajtjhlnfqiqv7qgnt3hvfuf5p2elqkwttmatyuka",
    "bafkreiasnapoyago6qk7tdfe35msiumkldj6byc3ktzstpxyu2qcrsckra",
    "bafkreifi5unvh2bzt7kgizg5mjzm2bf64jpoqocz6psi3vpwml33wecqpy",
    "bafkreidb7mlwkypr5eey64alaohxgnje3ik2b35i3gtsvp2y2ooowfooeu",
    "bafkreibphnonbjqu6k24tyg5n6aeg4jgxwwleju6ntj5yfc6iqwkvvpj6m",
    "bafkreidcynm2c2ju3z32vd4tal6yesz7oc2r5j2otov22splmcmltqf4lu",
    "bafkreidtmz7kk774n7gagwfcdlzvk246afv5eknmjsukabd75ioovlxovi",
    "bafkreiaoap3fm3zpimli2vask3yrf2gnuz5it2tywswmabi2jf2spatl54",
    "bafkreid3pwkrhcf6lkbfzinsyphuqyg6qxyzqvagarxb644pfq37icxvju",
    "bafkreieacgikh5xlsrkyy3za6fwwi3mqqasuumfvpo26cwz5b6bejyix3y",
    "bafkreievhhjso4e2xbuaqdzgxoy7swzz2galjhrjhfdjyfbywd433bhyki",
    "bafkreicbulijedqv4gzdp2lk22uec5fwvnicq4kynepykwfouphd6zmyze",
    "bafkreia66d65po6asi7mbw77rezkqgtthdbke7xaqdfcswy6z7mbt7cdze",
    "bafkreig3s3zht5yypjoamuvpjlanw52d6upqf4edgg33cbixrnfrw2l7bm",
    "bafkreig2whzodbawj5uf6jnxwuklau7dypg4y7o76drwhcihfoxilmvtvq",
    "baguqeeradsgdxdkkzg2kwlbl3k2sc2hvxji4flbp746befniojgzu45e6beq",
    "baguqeerawn4liekasqczwyrxeob56vll42unbnw6e2r2flmaqf4uispdiwaa",
    "baguqeeracvvq7w4mpmernbn4t2qyknyaoqtkrbqfslwmhctrgrr64jhrgmoa",
    "baguqeerabidpapan2i656qeu3wy7a7lwpe33fbc36rwmy7ggcbaa47kv5ida",
    "baguqeeraaadi5ohhq5juyyeheuecc52zi637anq5dtqrc7rfefy3qqugfmtq",
    "baguqeerav4dpwfjnphgo3o4cxnisfivap33524kum7a2af7amquifntlgrha",
    "baguqeerabqgejbmafvkoo4cbbposauakcpzo6qj36x7unaouqtp24kyb5oba",
    "baguqeeraq4dofzbocvqhre6t665zegebki4uz6vm5yzdqukzasbodvxdmxsa",
    "baguqeerack7gthp4yw6vigy2up4cnq6gww5biwbs3veh6grlymckkaedmp7q",
    "baguqeerabd6vb6pvatdj2b4c4c5zh34nflcgnqkcczhiujhyh6r3l2rhdhjq",
    "baguqeerapiuqoquumvskvryaosb3sgqdb5sqpec2l2q6ryn2tbvkuwr6hv5a",
    "baguqeerayyjrjhwusaegqw4q5hu6ilmoqjvlbnohfqmi5ovt3c7wnbkkjd4a",
}


def expected_parent_paths() -> set[str]:
    paths = {str(ORIGINAL_ROOT / "cas" / ("source" if value.startswith("baf") else "structured") / value[:4] / value)
             for value in PARENT_CAS_CIDS}
    for preview in ("before-preview", "materialization-preview"):
        for name in ("FiniteInteger.lean", "driver.py", "captured_source.py", "python_process.json", "request.json",
                     "result.json", "lean_process.json", "lean_certificate.json", "FiniteInteger.olean", "observations.json", "compiled.json", "tool_policy.json"):
            paths.add(str(ORIGINAL_ROOT / preview / "finite-observation" / name))
        for name in ("frontend.json", "captured_source.py", "result.json", "translation.json", "lean_process.json",
                     "lean_certificate.json", "IntegerModel.olean", "IntegerModel.lean", "compiled.json", "tool_policy.json"):
            paths.add(str(ORIGINAL_ROOT / preview / "operational-model" / name))
    return paths | {str(ORIGINAL_ROOT / name) for name in ("before-admission.json", "materialized.json",
        "private/lifecycle/local-planning-receipts/ea000dde50a87d2bf02e55d262b639c6ba0f07e6de912087b91d24ab6259fd46.json")} | {ORIGINAL_CANDIDATE}


def integer(value: Any, expected: int | None = None) -> bool:
    return type(value) is int and (expected is None or value == expected)


def decode_source(value: Any) -> bytes:
    need(type(value) is str and len(value) <= MAX_FILE_BYTES * 2, "bounded source encoding required")
    return base64.b64decode(value, validate=True)


def structured_identity(value: Any) -> bool:
    if type(value) is not str or len(value) != 61 or not value.startswith("b"):
        return False
    try:
        raw = base64.b32decode(value[1:].upper() + "=" * ((-len(value[1:])) % 8))
    except ValueError:
        return False
    return len(raw) == 37 and raw.startswith(b"\x01\xa9\x02\x12\x20") and "b" + base64.b32encode(raw).decode().lower().rstrip("=") == value


def immutable_task_cid(task: dict[str, Any]) -> str:
    """Native v1 execution-route projection, excluding operational completion/status."""
    need(integer(task["ordinal"]), "native task ordinal must be an exact integer")
    payload = {key: task[key] for key in ("task_cid", "task_alias", "goal_cid", "plan_cid", "objective_id", "ordinal",
        "priority", "dependencies", "outputs", "acceptance", "validations")}
    payload["body"] = {key: value for key, value in task["body"].items()
                       if key.strip().lower().replace("_", " ") not in {"status", "completion receipt"}}
    return cid(payload)


class WorkerReader:
    """Only selected public files inside the relocated fixture and its one handoff."""
    def __init__(self, fixture_root: Path):
        self.root = fixture_root.absolute()
        need(self.root.resolve(strict=True) == self.root and self.root.is_dir()
             and not any(path.is_symlink() for path in (self.root, *self.root.parents)), "canonical worker fixture root required")
        self.handoff = self.root.parent / "handoffs" / "candidate.json"
        self.pins: dict[str, dict[str, Any]] = {}
        self.total = 0

    def path(self, original: str) -> Path:
        need(type(original) is str and str(PurePosixPath(original)) == original
             and ".." not in PurePosixPath(original).parts, "exact original artifact selector required")
        if original == ORIGINAL_CANDIDATE:
            return self.handoff
        selected = PurePosixPath(original)
        need(selected.is_relative_to(ORIGINAL_ROOT) and selected != ORIGINAL_ROOT, "artifact outside selected original worker root")
        return self.root.joinpath(*selected.relative_to(ORIGINAL_ROOT).parts)

    def permitted(self, path: Path) -> bool:
        if path == self.handoff:
            return True
        if not path.is_relative_to(self.root):
            return False
        parts = path.relative_to(self.root).parts
        if len(parts) == 1:
            return parts[0] in RECORDS
        if parts[0] in PREVIEW_DIRECTORIES or parts[0] in {"cas", "selected-source-snapshot"}:
            return True
        if parts[:3] == ("private", "lifecycle", "local-planning-receipts"):
            return len(parts) == 4 and parts[3].endswith(".json") and hex_digest(parts[3][:-5], 64)
        if parts[:5] == ("private", "launch", "state", "run", "admitted_database_portal_attempts"):
            return len(parts) == 7 and hex_digest(parts[5], 24) and parts[6] in {"database-attempt-binding.json", "task_queue.json"}
        if parts[:3] == ("repository", ".git", "objects"):
            return len(parts) == 5 and hex_digest(parts[3] + parts[4], 40)
        return len(parts) == 2 and parts[0] == "repository" and parts[1] in INVENTORY

    def read(self, path: Path, *, original: str | None = None) -> bytes:
        need(path.is_absolute() and self.permitted(path) and path.resolve(strict=True) == path
             and not any(part.is_symlink() for part in (path, *path.parents)), "worker artifact path, private-state or alias refused")
        key = str(path)
        if key not in self.pins:
            need(len(self.pins) < MAX_FILES, "worker artifact count cap exceeded")
            limit = min(MAX_FILE_BYTES, MAX_TOTAL_BYTES - self.total)
            need(limit > 0, "worker artifact aggregate byte cap exceeded")
        else:
            limit = self.pins[key]["size_bytes"]
        raw = _bounded_document(path, limit)
        observed = {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}
        if key in self.pins:
            need({name: self.pins[key][name] for name in observed} == observed, "worker retained bytes changed between reads")
        else:
            self.pins[key] = {**observed, "retained_path": key, "original_paths": []}
            self.total += len(raw)
        if original and original not in self.pins[key]["original_paths"]:
            self.pins[key]["original_paths"].append(original)
        return raw

    def original(self, original: str) -> bytes:
        return self.read(self.path(original), original=original)

    def record(self, name: str) -> Any:
        return parse_document(self.read(self.root / name, original=str(ORIGINAL_ROOT / name)))

    def recheck(self) -> bool:
        for key in tuple(self.pins):
            self.read(Path(key))
        return True


def load_worker(reader: WorkerReader) -> dict[str, Any]:
    records = {name: reader.record(name) for name in RECORDS}
    ref = records["materialized.json"]["finite_admission_ref"]
    need(ref.get("schema") == "supervisor-finite-repository-admission-reference@1"
         and integer(ref.get("bytes")) and 0 < ref["bytes"] <= MAX_FILE_BYTES, "bounded complete native admission reference required")
    raw = reader.original(ref["path"])
    need(len(raw) == ref["bytes"] and hashlib.sha256(raw).hexdigest() == ref["sha256"], "native plan reference byte drift")
    records["referenced_admission"] = parse_document(raw)
    raw = reader.original(ORIGINAL_CANDIDATE)
    records["candidate"] = parse_document(raw)
    records["candidate_byte_pin"] = {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
    verified, sources = {}, {}
    for name in ("before-admission.json", "successor-admission.json", "cold-admission.json"):
        admission = records[name]
        for record in (admission["evidence"]["match"]["observation"], admission["evidence"]["operational_model"]):
            artifacts = record["artifacts"]
            need(type(artifacts) is dict and 1 <= len(artifacts) <= 16, "bounded complete observation/model artifacts required")
            for descriptor in artifacts.values():
                need(type(descriptor) is dict and set(descriptor) == {"path", "sha256", "size_bytes", "cid"}
                     and integer(descriptor["size_bytes"]) and 0 <= descriptor["size_bytes"] <= MAX_FILE_BYTES
                     and PurePosixPath(descriptor["path"]).parent == PurePosixPath(record["output"]), "native artifact descriptor scope drift")
                data = reader.original(descriptor["path"])
                actual = {"sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data), "cid": raw_cid(data)}
                need(exact(actual, {key: descriptor[key] for key in actual}), "native observation/model artifact byte drift")
                verified[descriptor["path"]] = actual
            need(reader.original(record["output"] + "/result.json") == canonical(record), "full native model/observation result differs")
            data = reader.original(artifacts["source"]["path"])
            source = base64.b64encode(data).decode()
            need(name not in sources or sources[name] == source, "model and finite observation source bytes disagree")
            sources[name] = source
    records["verified_native_artifacts"] = verified
    records["selected_source_bytes"] = sources
    parent = records["historical-parent-artifact-pins.json"]
    need(type(parent) is list and len(parent) == 77, "complete retained 77-parent-artifact population required")
    observed_parent, seen = {}, set()
    for descriptor in parent:
        need(type(descriptor) is dict and set(descriptor) == {"path", "sha256", "bytes"}
             and descriptor["path"] not in seen and hex_digest(descriptor["sha256"], 64)
             and integer(descriptor["bytes"]) and 0 <= descriptor["bytes"] <= MAX_FILE_BYTES, "parent artifact duplicate/type/digest drift")
        seen.add(descriptor["path"])
        raw = reader.original(descriptor["path"])
        actual = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
        need(exact(actual, {key: descriptor[key] for key in actual}), "historical parent artifact bytes differ")
        observed_parent[descriptor["path"]] = actual
        if descriptor["path"].startswith("/results/native/cas/source/"):
            need(raw_cid(raw) == PurePosixPath(descriptor["path"]).name, "raw CAS identity differs")
        elif descriptor["path"].startswith("/results/native/cas/structured/"):
            need(cid(parse_document(raw)) == PurePosixPath(descriptor["path"]).name, "structured CAS identity differs")
    records["verified_parent_pins"] = observed_parent
    custody = records["execution-scope.json"]["payload"]["source_custody"]
    cas_sources, ast = {}, {}
    for descriptor in custody["files"]:
        if descriptor["role"].startswith("cas:source:"):
            name = descriptor["role"].split(":", 2)[2]
            need(name in INVENTORY and name not in cas_sources, "custody source population duplicate or foreign")
            data = reader.original(descriptor["path"])
            need(len(data) == descriptor["size_bytes"] and hashlib.sha256(data).hexdigest() == descriptor["sha256"], "original custody CAS bytes drift")
            cas_sources[name] = base64.b64encode(data).decode()
        elif descriptor["role"].startswith("cas:ast:"):
            name = descriptor["role"].split(":", 2)[2]
            need(name in INVENTORY and name not in ast, "custody AST population duplicate or foreign")
            data = reader.original(descriptor["path"])
            need(hashlib.sha256(data).hexdigest() == descriptor["sha256"] and len(data) == descriptor["size_bytes"], "retained AST bytes drift")
            ast[name] = PurePosixPath(descriptor["path"]).name
    records["original_source_bytes"], records["original_ast_ids"] = cas_sources, ast
    selected = {}
    for original in records["result.json"]["execution_sources"]:
        path = PurePosixPath(original["path"])
        prefix = PurePosixPath("/opt/ipfs-supervisor/source")
        need(path.is_relative_to(prefix) and str(path) == original["path"] and ".." not in path.parts and path.suffix == ".py",
             "exact selected producer source path required")
        module = ".".join(path.relative_to(prefix).with_suffix("").parts)
        need(module not in selected, "duplicate selected producer module")
        data = reader.read(reader.root / "selected-source-snapshot" / (module + ".py"), original=original["path"])
        actual = {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
        need(exact(actual, {key: original[key] for key in actual}), "retained selected producer copy differs from original native pin")
        selected[module] = actual
    records["verified_execution_sources"] = selected
    allocations = records["native-lifecycle.json"]["observed_worker_allocations"]
    need(type(allocations) is list and len(allocations) == 1, "one exact native residual allocation required")
    records["retained_attempt_binding"] = parse_document(reader.original(allocations[0]["state_dir"] + "/database-attempt-binding.json"))
    records["retained_portal_queue"] = parse_document(reader.original(allocations[0]["state_dir"] + "/task_queue.json"))
    records["git_publication"] = verify_publication(reader.root / "repository", reader, records["result.json"], records["candidate"])
    return records


def false_fields(record: dict[str, Any], names: set[str]) -> None:
    need(type(record) is dict and all(name in record and record[name] is False for name in names),
         "required review-only authority fields missing or granted")


def identifiers(record: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    result = {}
    for field in fields:
        value = record[field]
        if field in {"fence_epoch", "fencing_token"}:
            need(integer(value) and value > 0, "exact native fence integer required")
        else:
            need(type(value) is str and 0 < len(value) <= 256, "nonempty bounded native attempt identity required")
        result[field] = value
    return result


FENCE_FIELDS = ("attempt_id", "claim_id", "lease_id", "owner_session_id", "fence_epoch", "fencing_token")


def assert_candidate(records: dict[str, Any], before: dict[str, Any], offset_cid: str) -> dict[str, bytes]:
    candidate, descriptor = records["candidate"], records["candidate-descriptor.json"]
    false_fields(candidate, CANDIDATE_FALSE)
    manifest = before["declaration"]["payload"]["manifest"]["payload"]
    semantic = before["receipt"]["payload"]["semantic_context"]
    need(candidate["schema"] == "supervisor-finite-repository-candidate@1"
         and candidate["scope"] == "one_closed_integer_offset_edit_in_allocated_native_worktree"
         and candidate["finite_admission"] == before and candidate["finite_admission_cid"] == cid(before)
         and candidate["semantic_context_cid"] == cid(semantic) and candidate["operation_catalog_cid"] == semantic["operation_catalog_cid"]
         and candidate["baseline_commit"] == manifest["baseline_commit"] and candidate["repository"] == manifest["repository"]
         and candidate["task_cid"] == offset_cid and candidate["task_id"] == "FINITE-OFFSET" and integer(candidate["task_revision"], 1),
         "candidate detached from complete original task, admission or baseline")
    need(candidate["original_prompt"] == before["declaration"]["payload"]["source_text"]
         and candidate["original_clause_ids"] == sorted([TYPE_CLAUSE, OFFSET_CLAUSE])
         and candidate["permitted_outputs"] == [{"path": "calc.py", "effect": "modify", "media_type": "text/x-python"}]
         and integer(candidate["training_steps"], 0) and integer(candidate["provider_calls"], 0), "candidate task meanings, model-off mode or output changed")
    need(candidate["candidate_cid"] == cid({key: value for key, value in candidate.items() if key != "candidate_cid"}), "candidate structural identity drift")
    edit = candidate["edit"]
    need(set(edit) == {"path", "effect", "before_bytes_base64", "after_bytes_base64", "before_sha256", "after_sha256"}
         and edit["path"] == "calc.py" and edit["effect"] == "modify", "closed candidate edit scope changed")
    images = {name: decode_source(edit[name + "_bytes_base64"]) for name in ("before", "after")}
    need(images == {"before": b"def increment(n: int) -> int:\n    return n + 1\n",
                    "after": b"def increment(n: int) -> int:\n    return n + 2\n"}, "exact closed integer edit preimage/postimage changed")
    for name, raw in images.items():
        need(hashlib.sha256(raw).hexdigest() == edit[name + "_sha256"], "candidate byte digest drift")
    expected_descriptor = {name: candidate[name] for name in ("candidate_cid", "finite_admission_cid", "semantic_context_cid", "task_cid", "task_id", "task_revision")}
    expected_descriptor.update({"artifact": ORIGINAL_CANDIDATE, "sha256": records["candidate_byte_pin"]["sha256"],
        "before_sha256": edit["before_sha256"], "after_sha256": edit["after_sha256"]})
    need(exact(descriptor, expected_descriptor), "candidate descriptor does not bind exact retained handoff bytes")
    return images


def assert_native_population(records: dict[str, Any], scope: dict[str, Any], before: dict[str, Any], task_ids: dict[str, str]) -> dict[str, Any]:
    population = scope["native_population"]
    tasks = population["tasks"]
    need(type(tasks) is list and len(tasks) == 2 and {task["task_alias"] for task in tasks} == set(task_ids)
         and {task["task_cid"] for task in tasks} == set(task_ids.values()), "original native task population reduced or relabeled")
    by_alias = {task["task_alias"]: task for task in tasks}
    manifest_envelope = before["declaration"]["payload"]["manifest"]
    manifest = manifest_envelope["payload"]
    materialized = records["materialized.json"]
    specs = {spec["task_key"]: spec for spec in manifest["tasks"]}
    for alias, task in by_alias.items():
        expected_dependencies = [] if alias == "FINITE-TYPE" else [task_ids["FINITE-TYPE"]]
        need(task["task_cid"] == task_ids[alias] and task["dependencies"] == expected_dependencies
             and task["identity"]["task_cid"] == task["task_cid"] and task["identity"]["task_alias"] == alias,
             "native task identity or prerequisite drift")
        local = task["body"]["local_planning_contract"]
        contract = _envelope(local)
        need(contract["schema"] == "supervisor-local-pending-completion@1" and contract["task_cid"] == task["task_cid"]
             and contract["task_key"] == alias and contract["task_spec"] == specs[alias]
             and contract["manifest"] == manifest_envelope and contract["manifest_cid"] == cid(manifest_envelope)
             and contract["graph_cid"] == cid(_workflow_payload(before["graph"])) and contract["dependencies"] == expected_dependencies
             and contract["planning_receipt_cid"] == cid(before["local_admission"]["receipt"])
             and contract["pending_cid"] == materialized["pending_cid"] and contract["plan_id"] == materialized["plan_id"] == task["plan_cid"]
             and task["identity"]["local_contract_cid"] == cid(local), "native task detached from complete signed specification")
        spec = specs[alias]
        need(task["outputs"] == [{"effect": row, "ordinal": index, "path": row["path"]} for index, row in enumerate(spec["outputs"])]
             and task["validations"] == [{"argv": row["argv"], "ordinal": index, "policy": {key: value for key, value in row.items() if key != "argv"}}
                                        for index, row in enumerate(spec["validations"])]
             and task["acceptance"] == [{"criterion": row["criterion"], "evidence_policy": row, "ordinal": index} for index, row in enumerate(spec["acceptance"])],
             "native task validation executable, acceptance or output changed")
    prerequisite, offset = by_alias["FINITE-TYPE"], by_alias["FINITE-OFFSET"]
    need(prerequisite["status"] == "completed" and integer(prerequisite["revision"], 4)
         and offset["status"] == "ready" and integer(offset["revision"], 1)
         and population["selected_task_cids"] == [task_ids["FINITE-OFFSET"]], "exact completed prerequisite and ready residual revisions required")
    owner = population["owner_identity"]
    need(owner["schema"] == "ipfs_accelerate_py/agent-supervisor/state-server-identity@1"
         and owner["repository_id"] == manifest["repository_cid"] and owner["status"] == "ready"
         and integer(owner["fence_epoch"], 1), "original native owner identity drift")
    claim, validation = records["prerequisite-native-claim.json"], records["prerequisite-validation.json"]
    need(claim["operation"] == "database_attempt_admitted" and claim["claim_phase_schema"] == "ipfs_accelerate_py/agent-supervisor/typed-database-attempt-admission@1"
         and claim["attempt_execution_phase"] == "claimed" and integer(claim["attempt_number"], 1)
         and integer(claim["claimed_from_revision"], 1) and integer(claim["admitted_from_revision"], 2), "genuine typed prerequisite claim projection changed")
    claimed = identifiers(claim, FENCE_FIELDS)
    completed = prerequisite["body"]["completion_receipt"]
    need(exact(identifiers(completed, FENCE_FIELDS), claimed) and completed["operation"] == "database_complete"
         and claimed["fence_epoch"] == owner["fence_epoch"], "prerequisite completion detached from exact native attempt and fence")
    attestation = claim["claim_process_attestation"]
    need(attestation["process_birth_id"] == owner["process_birth_id"] and integer(attestation["uid"], 1000)
         and all(exact(attestation[key], owner["process_birth"][key]) for key in ("boot_id", "pid", "parent_pid", "start_time_ticks")),
         "retained prerequisite process identity differs from native owner")
    route = population["execution_route_policy"]
    need(type(route["entries"]) is list and len(route["entries"]) == 2
         and {row["task_alias"] for row in route["entries"]} == set(task_ids)
         and route["plan_root_cid"] == materialized["plan_id"], "complete native execution route population required")
    by_route = {row["task_alias"]: row for row in route["entries"]}
    for alias, row in by_route.items():
        need(row["task_cid"] == task_ids[alias] and integer(row["task_revision"], 1) and row["execution_mode"] == "grok-codex"
             and row["task_contract_cid"] == immutable_task_cid(by_alias[alias]), "native task execution route contract differs")
    binding = claim["execution_route_binding"]
    need(all(exact(binding[key], by_route["FINITE-TYPE"][key]) for key in by_route["FINITE-TYPE"])
         and binding["policy_id"] == claim["execution_route_policy_id"] == route["policy_id"]
         and binding["plan_root_cid"] == route["plan_root_cid"] and binding["repository_tree_id"] == route["repository_tree_id"], "prerequisite claim retargeted native execution route")
    need(validation["passed"] is True and validation["task_cid"] == task_ids["FINITE-TYPE"]
         and validation["source_tree_id"] == route["repository_tree_id"]
         and validation["results"] == [{"validation_key": "public-type", "outcome": "passed", "evidence_digest": completed["evidence_digest"]}],
         "actual prerequisite public validation differs from completion evidence")
    summaries, rows = population["completed_prerequisites"], population["completion_rows"]
    type_cid = task_ids["FINITE-TYPE"]
    need(set(summaries) == set(rows) == {type_cid} and len(rows[type_cid]) == 1 and len(rows[type_cid][0]) == 10,
         "complete prerequisite completion row missing, duplicate or foreign")
    row, summary = rows[type_cid][0], summaries[type_cid]
    evidence = parse_document(row[9].encode())
    need(row[1] == type_cid and summary["task_cid"] == type_cid and summary["task_alias"] == "FINITE-TYPE"
         and integer(summary["task_revision"], 4) and row[0] == summary["completion_receipt_cid"]
         and row[8] == summary["completion_evidence_digest"] and evidence["receipt"] == completed
         and integer(evidence["revision"], 4) and evidence["evidence_digests"] == [completed["evidence_digest"]],
         "retained prerequisite completion row detached from actual validation and fence")
    return by_alias


def assert_residual(records: dict[str, Any], native_tasks: dict[str, Any], offset_cid: str) -> dict[str, Any]:
    result, lifecycle = records["result.json"], records["native-lifecycle.json"]
    task = result["task"]
    need(task == lifecycle["task"] and task["status"] == "completed" and integer(task["revision"], 4)
         and task["body"]["local_planning_contract"] == native_tasks["FINITE-OFFSET"]["body"]["local_planning_contract"],
         "native residual completion or original contract drift")
    observations = result["task_observations"]
    need(observations == lifecycle["task_observations"] and type(observations) is list and len(observations) == 2
         and [(row["status"], row["revision"]) for row in observations] == [("in_progress", 3), ("completed", 4)]
         and all(integer(row["revision"]) and type(row["seconds"]) in {float, int} and math.isfinite(row["seconds"])
                 and 0 <= row["seconds"] <= result["elapsed_seconds"] for row in observations)
         and observations[0]["seconds"] < observations[1]["seconds"], "exact residual revision/fence progression missing")
    receipt = task["body"]["completion_receipt"]
    fence = identifiers(receipt, FENCE_FIELDS)
    need(receipt["operation"] == "database_complete" and integer(fence["fence_epoch"], 1) and integer(fence["fencing_token"], 1),
         "native residual completion fence/operation changed")
    validation, preparation = receipt["validation"], receipt["coordination_preparation"]
    need(preparation["schema"] == "ipfs_accelerate_py/agent-supervisor/task-completion-preparation@1"
         and preparation["status"] == "prepared" and preparation["task_cid"] == offset_cid
         and exact(identifiers(preparation, FENCE_FIELDS), fence) and integer(preparation["control_expected_revision"], 3)
         and preparation["control_expected_status"] == "in_progress" and integer(preparation["attempt_number"], 1)
         and preparation["body"]["validation"] == validation and preparation["evidence_digest"] == receipt["evidence_digest"],
         "residual validation/completion preparation detached from exact admitted attempt")
    need(validation["outcome"] == "passed" and validation["task_cid"] == offset_cid
         and validation["validator"] == "DatabasePortalExecutionBridge@1" and validation["argv"] == ["portal-supervisor-gates"]
         and validation["attempt_id"] == fence["attempt_id"] and validation["evidence_digest"] == receipt["evidence_digest"],
         "actual owner residual validation identity or outcome changed")
    transition = validation["accepted_source_transition"]
    binding = transition["database_attempt_binding"]
    need(binding == records["retained_attempt_binding"], "residual attempt/fence differs from exact retained portal binding bytes")
    need(transition["transition_cid"] == "sha256:" + hashlib.sha256(canonical({key: value for key, value in transition.items() if key != "transition_cid"})).hexdigest(),
         "accepted native source transition content identity drift")
    queue = records["retained_portal_queue"]
    canonical_task = transition["canonical_task_cid"]
    need(structured_identity(canonical_task) and queue["schema"] == "persistent_task_queue_v3" and integer(queue["entry_count"], 1)
         and set(queue["entries"]) == {canonical_task} and queue["aliases"] == {"FINITE-OFFSET": canonical_task, "intent::FINITE-OFFSET": canonical_task},
         "canonical residual task differs from exact retained portal alias population")
    entry = queue["entries"][canonical_task]
    need(entry["canonical_task_cid"] == canonical_task and entry["canonical_task_key"] == transition["canonical_task_key"]
         and entry["task_id"] == "FINITE-OFFSET" and entry["aliases"] == ["FINITE-OFFSET", "intent::FINITE-OFFSET"]
         and integer(entry["attempt_count"], 1), "canonical residual task aliases or attempt counter drift")
    need(transition["schema"] == "ipfs_accelerate_py/agent-supervisor/accepted-source-transition@1"
         and transition["authority"] == "database_completion_cas_after_portal_and_git_verification"
         and transition["database_task_cid"] == binding["task_cid"] == offset_cid
         and transition["task_alias"] == binding["task_alias"] == "FINITE-OFFSET"
         and transition["attempt_id"] == binding["attempt_id"] == fence["attempt_id"]
         and transition["claim_id"] == binding["claim_id"] == fence["claim_id"]
         and transition["fencing_token"] == binding["fencing_token"] == fence["fencing_token"]
         and binding["lease_id"] == fence["lease_id"] and binding["fence_epoch"] == fence["fence_epoch"]
         and integer(binding["task_revision"], 3) and integer(binding["control_expected_revision"], 3)
         and binding["plan_cid"] == native_tasks["FINITE-OFFSET"]["plan_cid"]
         and binding["goal_cid"] == native_tasks["FINITE-OFFSET"]["goal_cid"]
         and binding["projection_authority"] is False and transition["worker_self_approval"] is False
         and transition["task_completion_authority"] is False,
         "accepted publication detached from exact residual attempt, fence or native plan")
    publication = records["git_publication"]
    need(publication["git_object_verification_performed"] is True
         and publication["published_commit_parents"] == result["published_commit_parents"]
         and result["published_commit_parents"][0] == result["original_commit"]
         and publication["original_commit"] == transition["baseline_ref"] == result["original_commit"]
         and publication["published_commit"] == transition["merge_commit"] == result["published_commit"]
         and publication["implementation_commit"] == transition["implementation_commit"] == result["published_commit_parents"][1]
         and publication["published_tree"] == transition["merge_tree"] == transition["implementation_tree"]
         and transition["target_branch"] == "master" and integer(transition["attempt_number"], 1) and integer(transition["portal_attempt_number"], 1),
         "retained Git publication does not match actual accepted source transition")
    proof, output = transition["integration_commit_proof"], transition["declared_output_invariant"]
    need(proof["passed"] is True and proof["reasons"] == [] and proof["target_branch"] == "master"
         and proof["implementation_commit"] == publication["implementation_commit"]
         and proof["integration_commit"] == proof["integration_ref"] == publication["published_commit"], "retained integration proof does not bind actual merge")
    need(output["passed"] is True and output["mode"] == "repository_tree" and output["task_ids"] == ["FINITE-OFFSET"]
         and output["repository_ref"] == publication["published_commit"] and all(output[key] == [] for key in ("missing_outputs", "unsafe_outputs", "untracked_outputs"))
         and output["checks"] == [{"exists": True, "path": "calc.py", "reason": "declared_output_tracked", "repository": ".",
             "repository_ref": publication["published_commit"], "task_id": "FINITE-OFFSET", "tracked": True, "tracked_path": "calc.py"}],
         "native declared output verification changed or retargeted")
    return {"attempt_id": fence["attempt_id"], "claim_id": fence["claim_id"], "lease_id": fence["lease_id"],
        "fence_epoch": fence["fence_epoch"], "fencing_token": fence["fencing_token"], "task_revision": 4,
        "task_cid": offset_cid, "canonical_task_cid": transition["canonical_task_cid"]}


def assert_lifecycle(records: dict[str, Any], scope: dict[str, Any], before: dict[str, Any], task_ids: dict[str, str], residual: dict[str, Any]) -> None:
    result, lifecycle = records["result.json"], records["native-lifecycle.json"]
    need(lifecycle["schema"] == result["schema"] == "finite-repository-native-worker-qualification@1"
         and lifecycle["status"] == "incomplete", "native lifecycle checkpoint scope changed")
    for name in ("start", "stop", "inventory_paths", "original_commit", "remaining_processes", "bootstrap_errors", "observed_worker_allocations", "resource_before_stop"):
        need(exact(lifecycle[name], result[name]), "final result differs from actual lifecycle checkpoint: " + name)
    manifest = before["declaration"]["payload"]["manifest"]["payload"]
    start, stop = result["start"], result["stop"]
    for operation, record in (("start", start), ("stop", stop)):
        need(record["schema"] == "ipfs_accelerate_py/agent-supervisor/operation-result@1" and record["operation"] == operation
             and record["status"] == "succeeded" and record["error"] is None and record["authority"] == "mutation"
             and record["repository_id"] == manifest["repository_cid"] and record["caller"] == records["execution-scope.json"]["binding"]["identity"]
             and integer(record["bounds"]["timeout_ms"], 30000), "actual bounded native START/STOP outcome changed")
        effects = record["effects"]
        need(len(effects) == 1 and effects[0]["applied"] is True and effects[0]["effect_id"] == operation + ":isolated-process-tree"
             and effects[0]["resource"] == manifest["repository_cid"] and effects[0]["receipt_id"] == record["audit_receipt_id"],
             "native START/STOP receipt or effect population changed")
    need(start["policy_id"] == stop["policy_id"] and start["objective_id"] == stop["objective_id"]
         and start["tree_id"] == stop["tree_id"] and start["data"]["old_tree_fenced"] is False
         and stop["data"]["old_tree_fenced"] is True and stop["data"]["new_process_identity"] is None,
         "native STOP no longer fences the original launched tree")
    process = start["data"]["new_process_identity"]
    need(process["schema"] == "ipfs_accelerate_py/agent-supervisor/process-identity@1"
         and process["repository_root"] == process["cwd"] == manifest["repository"]
         and process["parent_pid"] == scope["native_population"]["owner_identity"]["process_birth"]["pid"]
         and all(integer(process[key]) and process[key] > 0 for key in ("pid", "parent_pid", "process_group_id", "session_id", "start_time_ticks", "fencing_epoch"))
         and process["pid"] == process["process_group_id"] == process["session_id"]
         and process["boot_id"] == scope["native_population"]["owner_identity"]["process_birth"]["boot_id"]
         and process["executable"] == before["declaration"]["payload"]["tool_policy"]["python"]["path"],
         "native launched process identity/owner/repository changed")
    argv = process["argv"]
    need(type(argv) is list and all(type(value) is str for value in argv)
         and argv[:4] == ["/opt/ipfs-supervisor/venv/bin/python", "-P", "-m", "ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_supervisor"],
         "exact installed launch interpreter, flags and module required")
    for flag, expected in (("--execution-slice-task-cid", [task_ids["FINITE-OFFSET"], task_ids["FINITE-TYPE"]]),
                           ("--execution-slice-task-id", ["FINITE-OFFSET", "FINITE-TYPE"]),
                           ("--implementation-command", [scope["candidate"]["implementation_command"]]),
                           ("--task-source-kind", ["duckdb"]), ("--authority-mode", ["quack"]),
                           ("--max-task-attempts", ["1"])):
        values = [argv[index + 1] for index, value in enumerate(argv[:-1]) if value == flag]
        need(values == expected, "actual launched CLI task population, command or source mode changed")
    cleanup = stop["data"]["isolated_worker_cleanup"]
    need(cleanup["schema"] == "isolated-worker-stop-observation@1" and integer(cleanup["worker_uid"], 1001)
         and integer(cleanup["returncode"], 0) and cleanup["single_worker"] is True and cleanup["completion_authority"] is False
         and set(cleanup["namespaces"]) == {"mnt", "net", "pid"}
         and all(type(value) is str and 0 < len(value) <= 64 for value in cleanup["namespaces"].values())
         and integer(result["remaining_processes"], 0) and result["bootstrap_errors"] == [], "successful retained UID cleanup or absent process tree changed")
    allocations, owner_cleanup = result["observed_worker_allocations"], records["owner-fixture-worktree-cleanup.json"]
    need(type(allocations) is list and len(allocations) == 1 and type(owner_cleanup) is list and len(owner_cleanup) == 1
         and owner_cleanup[0]["allocation"] == allocations[0], "explicit owner cleanup lost exact observed allocation")
    allocation = allocations[0]
    path = PurePosixPath(allocation["workspace_path"])
    need(allocation["schema"] == "ipfs_accelerate_py/agent-supervisor/worktree-lifecycle-record@1"
         and allocation["task_id"] == "FINITE-OFFSET" and allocation["canonical_task_cid"] == residual["canonical_task_cid"]
         and allocation["repo_root"] == manifest["repository"] and allocation["merge_target"] == "master"
         and path.is_relative_to(PurePosixPath("/opt/ipfs-supervisor/worktrees")) and len(path.parts) == 5
         and ".." not in path.parts and str(path) == allocation["workspace_path"]
         and allocation["owner"]["parent_pid"] == process["pid"] and allocation["owner"]["boot_id"] == process["boot_id"],
         "native observed worktree allocation or owner birth binding changed")
    decision = owner_cleanup[0]["decision"]
    need(owner_cleanup[0]["scope"] == "explicit owner fixture cleanup after native STOP; not native completion recovery"
         and owner_cleanup[0]["native_lifecycle_record_after_stop"] is None and decision["allowed"] is True
         and decision["reason"] == "no_lifecycle_record" and decision["record"] is None and decision["disposition"] == "allow",
         "explicit fixture cleanup replaced with an automatic recovery claim")
    lease, held, released = scope["lease"], result["resource_before_stop"], result["resource_after_owner_close"]
    need(integer(lease["cpu_slots"], 4) and integer(lease["memory_mb"], 4096) and integer(lease["child_process_slots"], 8)
         and lease["lane"] == "orchestration" and lease["owner_pid"] == process["parent_pid"]
         and integer(held["active_lease_count"], 1) and integer(held["active_root_lease_count"], 1)
         and integer(held["allocated_child_process_slots"], 8) and exact(held["allocated"], {"cpu_slots": 4, "memory_mb": 4096}),
         "held native admission accounting envelope changed before STOP")
    need(all(integer(released[key], 0) for key in ("active_lease_count", "active_root_lease_count", "active_child_lease_count", "waiting_request_count", "allocated_child_process_slots"))
         and exact(released["allocated"], {"cpu_slots": 0, "memory_mb": 0})
         and integer(result["active_leases"], 0) and integer(result["waiting_requests"], 0), "native lease/waiter accounting retained after owner close")


def assert_worker(records: dict[str, Any]) -> dict[str, Any]:
    result = records["result.json"]
    need(result["schema"] == "finite-repository-native-worker-qualification@1" and result["status"] == "completed"
         and type(result["elapsed_seconds"]) in {float, int} and math.isfinite(result["elapsed_seconds"])
         and 0 < result["elapsed_seconds"] <= 120, "retained completed bounded worker fixture required")
    for name in ("worker_launched", "complete_task_population_retained", "actual_public_checks_passed", "historical_artifacts_unchanged",
                 "stale_current_admission_rejected", "successor_cold_finite_outcomes_agree", "no_work_successor_grants_no_task_omission", "native_worker_successor_loop_qualified"):
        need(result[name] is True, "retained worker crossing absent: " + name)
    for name in ("production_activated", "task_omission_authority", "universal_python_semantics_proved"):
        need(result[name] is False, "retained worker fixture overstates authority: " + name)
    need(integer(result["provider_calls"], 0) and integer(result["training_steps"], 0), "model-off worker fixture performed provider/training calls")
    publication = records["git_publication"]
    need(publication["git_object_verification_performed"] is True
         and all(exact(result[key], publication[key]) for key in ("original_commit", "published_commit", "published_commit_parents", "changed_paths")),
         "final publication differs from retained physical Git commit/tree/blob verification")
    before, successor, cold = (records[name] for name in ("before-admission.json", "successor-admission.json", "cold-admission.json"))
    population = assert_admission(before, successor=False)
    next_population, cold_population = assert_admission(successor, successor=True), assert_admission(cold, successor=True)
    need(population["task_cids"] == next_population["task_cids"] == cold_population["task_cids"], "successor changed original complete task meanings")
    task_ids = {task["task_key"]: task["content_id"] for task in before["graph"]["tasks"]}
    materialized = records["materialized.json"]
    _false(materialized, FALSE_FLAGS)
    _false(materialized["finite_admission_ref"], {"execution_authority", "completion_authority", "mutation_authority"})
    need(materialized["administrator_task_population_preserved"] is True and materialized["task_cids"] == population["task_cids"]
         and materialized["finite_admission_cid"] == materialized["finite_admission_ref"]["admission_cid"] == cid(before)
         and records["referenced_admission"] == before, "materialized native reference lost full original task/admission population")
    manifest = before["declaration"]["payload"]["manifest"]["payload"]
    semantic = before["receipt"]["payload"]["semantic_context"]
    need(manifest["baseline_commit"] == result["original_commit"] and result["changed_paths"] == ["calc.py"]
         and result["inventory_paths"] == INVENTORY == sorted(manifest["sources"]), "original published baseline or complete inventory changed")
    inventory = records["captured-inventory.json"]
    need(inventory["paths"] == INVENTORY and set(inventory["ast_units"]) == {"calc.py", "decoy.py", "unsupported.py"}
         and inventory["unsupported_integer_profile"]["rejected"] is True
         and type(inventory["unsupported_integer_profile"]["error"]) is str and inventory["unsupported_integer_profile"]["error"], "decoy/unsupported AST inventory or rejection lost")
    need(set(records["original_source_bytes"]) == set(records["original_ast_ids"]) == set(INVENTORY)
         and all(inventory["ast_units"][name] == records["original_ast_ids"][name] for name in inventory["ast_units"]), "captured complete source/AST population differs from actual CAS")
    for name, encoded in records["original_source_bytes"].items():
        need(hashlib.sha256(decode_source(encoded)).hexdigest() == manifest["sources"][name]["sha256"], "original CAS source detached from signed inventory")
    need(raw_cid(decode_source(records["original_source_bytes"]["calc.py"])) == semantic["source_cid"]
         and raw_cid(decode_source(records["original_source_bytes"]["decoy.py"])) != semantic["source_cid"], "selected source identity replaced with same-name decoy")
    images = assert_candidate(records, before, task_ids["FINITE-OFFSET"])
    need(images["before"] == decode_source(records["original_source_bytes"]["calc.py"]), "candidate preimage differs from captured source")
    verified = records["verified_native_artifacts"]
    for name, expected in (("before-admission.json", images["before"]), ("successor-admission.json", images["after"]), ("cold-admission.json", images["after"])):
        admission = records[name]
        source = decode_source(records["selected_source_bytes"][name])
        need(source == expected and raw_cid(source) == admission["receipt"]["payload"]["semantic_context"]["source_cid"], "retained finite/model source image drift")
        for record in (admission["evidence"]["match"]["observation"], admission["evidence"]["operational_model"]):
            for descriptor in record["artifacts"].values():
                need(descriptor["path"] in verified and exact(verified[descriptor["path"]], {key: descriptor[key] for key in ("sha256", "size_bytes", "cid")}),
                     "native observation/model descriptor detached from retained byte checks")
    parent = records["historical-parent-artifact-pins.json"]
    need(type(parent) is list and len(parent) == 77 and {row["path"] for row in parent} == expected_parent_paths()
         and set(records["verified_parent_pins"]) == expected_parent_paths(), "original 77-parent-artifact population reduced, substituted or relabeled")
    for row in parent:
        need(exact({key: row[key] for key in ("sha256", "bytes")}, records["verified_parent_pins"][row["path"]]), "historical parent pin differs from actual retained byte check")
    scope = _envelope(records["execution-scope.json"])
    false_fields(scope, SCOPE_FALSE)
    need(records["execution-scope.json"] == result["execution_scope_after_stop"]
         and scope["schema"] == "supervisor-finite-repository-execution-scope@1" and scope["profile"] == "finite-repository-one-ready-native-worker@1"
         and scope["task_population_preserved"] is True and scope["finite_facts_are_context_only"] is True
         and scope["finite_admission_cid"] == cid(before) and structured_identity(scope["fresh_evidence_cid"])
         and scope["semantic_context_cid"] == cid(semantic) and scope["head"] == semantic["head"]
         and scope["future_claim_and_fence"] == "existing_native_typed_owner", "held execution scope detached from original finite/native meanings")
    custody = scope["source_custody"]
    false_fields(custody, {"atomicity_attested", "process_origin_attested", "behavior_authority", "completion_authority", "execution_authority",
        "mutation_authority", "production_admitted", "proof_authority", "runtime_behavior_verified", "source_semantics_verified"})
    need(custody["admitted_source_paths"] == INVENTORY and custody["head"] == semantic["head"], "source custody original inventory/head changed")
    descriptor = records["candidate-descriptor.json"]
    argv = ["/opt/ipfs-supervisor/bin/owner-worker", "--finite-repository-artifact", ORIGINAL_CANDIDATE,
        "--finite-repository-sha256", descriptor["sha256"], "--finite-repository-task-cid", task_ids["FINITE-OFFSET"]]
    need(scope["candidate"] == {"argv": argv, "descriptor": descriptor, "implementation_command": shlex.join(argv)}, "scope installed candidate command drift")
    source_pins = records["verified_execution_sources"]
    need(set(source_pins) == EXECUTION_MODULES and len(result["execution_sources"]) == 10
         and set(scope["implementation"]) == SCOPE_MODULES and all(hex_digest(value, 64) for value in scope["implementation"].values()),
         "closed selected worker producer population changed")
    for module, digest in scope["implementation"].items():
        if module in source_pins:
            need(source_pins[module]["sha256"] == digest, "execution scope producer differs from selected retained copy")
    for admission in (before, successor, cold):
        declared_pins = admission["declaration"]["payload"]["implementation"]["source_sha256"]
        for module in source_pins.keys() & declared_pins.keys():
            need(source_pins[module]["sha256"] == declared_pins[module], "selected worker producer differs from signed admission implementation")
    native_tasks = assert_native_population(records, scope, before, task_ids)
    residual = assert_residual(records, native_tasks, task_ids["FINITE-OFFSET"])
    assert_lifecycle(records, scope, before, task_ids, residual)
    publication = records["git_publication"]
    for admission in (successor, cold):
        declared = admission["declaration"]["payload"]
        next_manifest = declared["manifest"]["payload"]
        need(next_manifest["baseline_commit"] == result["published_commit"] and next_manifest["sources"].keys() == manifest["sources"].keys()
             and declared["intent_json"] == before["declaration"]["payload"]["intent_json"]
             and declared["source_text"] == before["declaration"]["payload"]["source_text"]
             and declared["operation_catalog"] == before["declaration"]["payload"]["operation_catalog"], "signed successor changed original task/source requirement meanings")
        for path in INVENTORY:
            need(next_manifest["sources"][path]["sha256"] == publication["after_source_sha256"][path], "successor signed source differs from published Git blob")
        need(declared["manifest"]["binding"]["profile_id"] != before["declaration"]["payload"]["manifest"]["binding"]["profile_id"], "successor discarded independent profile scope")
    next_semantic, cold_semantic = (admission["receipt"]["payload"]["semantic_context"] for admission in (successor, cold))
    comparison = records["cold-comparison.json"]
    need(comparison["agreement"] is True and comparison["compared_fields"] == COMPARISON_FIELDS
         and not exact(next_semantic["head"], cold_semantic["head"]) and not exact(semantic["head"], next_semantic["head"])
         and all(exact(next_semantic[name], cold_semantic[name]) for name in COMPARISON_FIELDS), "complete nine-field successor/cold comparison or distinct generation envelopes changed")
    replay = records["fresh-process-replay.json"]
    need(replay == result["fresh_process_historical_replay"] and set(replay) == {"schema", "historical_integrity_verified", "task_statuses", "current_freshness_claimed", "training_steps"}
         and replay["schema"] == "finite-worker-fresh-process-historical-replay@1" and replay["historical_integrity_verified"] is True
         and replay["task_statuses"] == {"FINITE-TYPE": "completed", "FINITE-OFFSET": "completed"}
         and replay["current_freshness_claimed"] is False and integer(replay["training_steps"], 0), "retained fresh historical replay lost completed population or scope")
    return {"preserved_task_population": {"task_keys": sorted(task_ids), "task_cids": population["task_cids"],
            "historical_completed_statuses": replay["task_statuses"], "source": "retained producer records; no task-store open during audit"},
        "residual_attempt": residual, "retained_native_elapsed_seconds": result["elapsed_seconds"], "historical_parent_artifact_count": 77,
        "selected_producer_copy_count": 10, "successor_cold_compared_fields": COMPARISON_FIELDS, "git_publication": publication,
        "cleanup_scope": "retained successful STOP/UID cleanup plus explicit owner fixture cleanup; automatic worktree/crash recovery unqualified"}


def mutate_tree(value: Any, callback) -> None:
    if type(value) is dict:
        callback(value)
        for member in value.values():
            mutate_tree(member, callback)
    elif type(value) is list:
        for member in value:
            mutate_tree(member, callback)


WORKER_CONTROLS = (
    "drop_original_native_task", "drop_prerequisite_completion", "false_prerequisite_validation", "relabel_prerequisite_check",
    "change_prerequisite_fence", "retarget_candidate", "change_candidate_preimage", "grant_candidate_authority",
    "drop_original_launch_task", "wrong_stop_fence", "wrong_cleanup_uid", "omit_owner_cleanup", "claim_automatic_cleanup",
    "foreign_worktree_path", "correlated_foreign_residual_attempt", "correlated_boolean_fence", "foreign_published_parent",
    "broaden_published_paths", "drop_cold_comparison_field", "relabel_historical_completed_task", "drop_parent_artifact",
    "substitute_parent_artifact", "correlated_producer_digest", "foreign_launch_interpreter", "correlated_boolean_process_pid",
    "foreign_transition_identity", "correlated_foreign_canonical_task", "grant_serialized_scope_authority",
)


def worker_controls(records: dict[str, Any]) -> list[dict[str, Any]]:
    results = []
    for name in WORKER_CONTROLS:
        changed = copy.deepcopy(records)
        result, scope = changed["result.json"], changed["execution-scope.json"]["payload"]
        if name == "drop_original_native_task":
            scope["native_population"]["tasks"].pop()
        elif name == "drop_prerequisite_completion":
            scope["native_population"]["completion_rows"] = {}
            scope["native_population"]["completed_prerequisites"] = {}
        elif name == "false_prerequisite_validation":
            changed["prerequisite-validation.json"]["passed"] = False
        elif name == "relabel_prerequisite_check":
            changed["prerequisite-validation.json"]["results"][0]["validation_key"] = "public-offset"
        elif name == "change_prerequisite_fence":
            changed["prerequisite-native-claim.json"]["fencing_token"] = 2
        elif name in {"retarget_candidate", "change_candidate_preimage", "grant_candidate_authority"}:
            candidate = changed["candidate"]
            if name == "retarget_candidate":
                candidate["edit"]["path"] = "decoy.py"
                candidate["permitted_outputs"][0]["path"] = "decoy.py"
            elif name == "change_candidate_preimage":
                raw = b"def increment(n: int) -> int:\n    return n + 2\n"
                candidate["edit"]["before_bytes_base64"] = base64.b64encode(raw).decode()
                candidate["edit"]["before_sha256"] = hashlib.sha256(raw).hexdigest()
            else:
                candidate["publication_authority"] = True
            candidate["candidate_cid"] = cid({key: value for key, value in candidate.items() if key != "candidate_cid"})
            changed["candidate-descriptor.json"]["candidate_cid"] = candidate["candidate_cid"]
        elif name == "drop_original_launch_task":
            argv = result["start"]["data"]["new_process_identity"]["argv"]
            type_cid = next(task["task_cid"] for task in scope["native_population"]["tasks"] if task["task_alias"] == "FINITE-TYPE")
            for flag, value in (("--execution-slice-task-cid", type_cid), ("--execution-slice-task-id", "FINITE-TYPE")):
                index = next(index for index, item in enumerate(argv[:-1]) if item == flag and argv[index + 1] == value)
                del argv[index:index + 2]
        elif name == "wrong_stop_fence":
            result["stop"]["data"]["old_tree_fenced"] = False
        elif name == "wrong_cleanup_uid":
            result["stop"]["data"]["isolated_worker_cleanup"]["worker_uid"] = 1000
        elif name == "omit_owner_cleanup":
            changed["owner-fixture-worktree-cleanup.json"] = []
        elif name == "claim_automatic_cleanup":
            changed["owner-fixture-worktree-cleanup.json"][0]["scope"] = "automatic completion cleanup"
        elif name == "foreign_worktree_path":
            result["observed_worker_allocations"][0]["workspace_path"] = "/foreign/workspace"
            changed["owner-fixture-worktree-cleanup.json"][0]["allocation"] = copy.deepcopy(result["observed_worker_allocations"][0])
        elif name == "correlated_foreign_residual_attempt":
            receipt = result["task"]["body"]["completion_receipt"]
            previous = receipt["attempt_id"]
            def change_attempt(row, expected=previous):
                for key, value in row.items():
                    if key == "attempt_id" and value == expected:
                        row[key] = "attempt:foreign"
            mutate_tree(receipt, change_attempt)
        elif name == "correlated_boolean_fence":
            def boolean_fence(row):
                if "fencing_token" in row:
                    row["fencing_token"] = True
            mutate_tree(result["task"], boolean_fence)
            mutate_tree(changed["retained_attempt_binding"], boolean_fence)
        elif name == "foreign_published_parent":
            result["published_commit_parents"][0] = "0" * 40
        elif name == "broaden_published_paths":
            result["changed_paths"] = ["calc.py", "decoy.py"]
        elif name == "drop_cold_comparison_field":
            changed["cold-comparison.json"]["compared_fields"].pop()
        elif name == "relabel_historical_completed_task":
            changed["fresh-process-replay.json"]["task_statuses"] = {"FINITE-OFFSET": "completed"}
            result["fresh_process_historical_replay"] = copy.deepcopy(changed["fresh-process-replay.json"])
        elif name == "drop_parent_artifact":
            changed["historical-parent-artifact-pins.json"].pop()
        elif name == "substitute_parent_artifact":
            row = changed["historical-parent-artifact-pins.json"][0]
            original = row["path"]
            row["path"] = "/results/native/cas/source/bafk/foreign"
            changed["verified_parent_pins"][row["path"]] = changed["verified_parent_pins"].pop(original)
        elif name == "correlated_producer_digest":
            module = "ipfs_accelerate_py.agent_supervisor.runtime.finite_repository_admission"
            changed["verified_execution_sources"][module]["sha256"] = "a" * 64
            scope["implementation"][module] = "a" * 64
            next(row for row in result["execution_sources"] if row["path"].endswith("/finite_repository_admission.py"))["sha256"] = "a" * 64
        elif name == "foreign_launch_interpreter":
            result["start"]["data"]["new_process_identity"]["argv"][0] = "/foreign/python"
        elif name == "correlated_boolean_process_pid":
            result["start"]["data"]["new_process_identity"]["pid"] = True
            result["observed_worker_allocations"][0]["owner"]["parent_pid"] = True
            changed["owner-fixture-worktree-cleanup.json"][0]["allocation"] = copy.deepcopy(result["observed_worker_allocations"][0])
        elif name == "foreign_transition_identity":
            def foreign_transition(row):
                if row.get("schema") == "ipfs_accelerate_py/agent-supervisor/accepted-source-transition@1":
                    row["transition_cid"] = "sha256:" + "0" * 64
            mutate_tree(result["task"], foreign_transition)
        elif name == "correlated_foreign_canonical_task":
            def foreign_canonical(row):
                if "canonical_task_cid" in row:
                    row["canonical_task_cid"] = cid({"foreign": "task"})
            mutate_tree(result, foreign_canonical)
            mutate_tree(changed["owner-fixture-worktree-cleanup.json"], foreign_canonical)
        else:
            scope["publication_authority"] = True
        if name != "foreign_transition_identity":
            def rehash_transition(row):
                if row.get("schema") == "ipfs_accelerate_py/agent-supervisor/accepted-source-transition@1":
                    row["transition_cid"] = "sha256:" + hashlib.sha256(canonical({key: value for key, value in row.items() if key != "transition_cid"})).hexdigest()
            mutate_tree(result["task"], rehash_transition)
        result["execution_scope_after_stop"] = copy.deepcopy(changed["execution-scope.json"])
        for key in ("start", "stop", "task", "task_observations", "observed_worker_allocations"):
            changed["native-lifecycle.json"][key] = copy.deepcopy(result[key])
        try:
            assert_worker(changed)
        except AdmissionEvidenceError as exc:
            results.append({"mutation_id": name, "outcome": "refused", "exception": type(exc).__name__, "message": str(exc),
                "scope": "authored correlated dictionary corruption; no signature, worker or proof authority"})
        else:
            raise AssertionError("corrupted retained worker accepted: " + name)
    return results


def run(fixture_root: Path, output: Path) -> dict[str, Any]:
    need(not output.exists(), "worker audit output must be fresh")
    output.mkdir(parents=True, mode=0o700, exist_ok=False)
    report: dict[str, Any] = {"schema": SCHEMA, "status": "incomplete", "started_at": datetime.now(UTC).isoformat(),
        "fixture_root": str(fixture_root.absolute()), "worker_execution_during_audit": False, "worker_launched": False,
        "signature_authentication_performed_by_structural_audit": False, "current_launch_permission_claimed": False,
        "historical_native_worker_observed": False, "historical_observation_scope": "retained producer record only; no authenticated process-origin observation",
        "historical_replay_performed_during_audit": False, "production_tasks_closed": [], "task_database_opened": False,
        "profile_keys_read": False, "native_proof_invoked": False, "git_invoked": False, "network_invoked": False,
        "training_steps": 0, "structural_control_count": 0, "structural_controls_refused": 0,
        "publication_verified": False, "held_full_fresh_evidence_cid_rederived": False,
        "bounds": {"files": MAX_FILES, "total_bytes": MAX_TOTAL_BYTES, "file_bytes": MAX_FILE_BYTES},
        "unknowns": ["Full held capacity preview is not serialized; its fresh_evidence_cid is a retained signed field, not independently rederived.",
            "No signature authentication, current owner-state verification, new launch grant, UID isolation attestation, worker run or training occurred.",
            "Git verification covers exact retained loose objects; no current checkout or durable recovery verification.",
            "Selected producer copies and sequential records do not attest full executed dependency closure or process origin.",
            "Worktree cleanup was explicit owner fixture cleanup, not automatic native completion or crash recovery."]}
    reader = None
    try:
        reader = WorkerReader(fixture_root)
        records = load_worker(reader)
        report["input_result_sha256"] = reader.pins[str(reader.root / "result.json")]["sha256"]
        report.update(assert_worker(records))
        controls = worker_controls(records)
        report.update(status="passed", historical_native_worker_observed=True, publication_verified=True,
            structural_control_count=len(controls), structural_controls_refused=sum(row["outcome"] == "refused" for row in controls),
            structural_controls=controls, retained_files_unchanged=reader.recheck())
    except (ValueError, OSError, KeyError, TypeError, RecursionError, AssertionError) as exc:
        report.update(status="refused", blocker=type(exc).__name__ + ": " + str(exc))
    if reader is not None:
        report.update(read_file_count=len(reader.pins), read_bytes=reader.total, retained_file_pins=list(reader.pins.values()))
    report["finished_at"] = datetime.now(UTC).isoformat()
    (output / "worker_evidence.json").write_bytes(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False).encode() + b"\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = run(args.fixture_root, args.output)
    print(json.dumps({"status": report["status"], "report": str(args.output / "worker_evidence.json"),
        "worker_execution_during_audit": False, "current_launch_permission_claimed": False}, sort_keys=True))
    sys.exit(0 if report["status"] == "passed" else 3)


if __name__ == "__main__":
    main()
