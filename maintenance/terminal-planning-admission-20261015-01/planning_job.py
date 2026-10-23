"""A genuine native job for a distinct, bounded planning-observation experiment.

The fixture registry is deliberately separate from the account registry.  Native
profile signatures, lifecycle checks, formal compilation and pending task gates
run unchanged inside it.  A public report is historical data, never a live job
capability, and this job does not discharge the original coding instructions.
"""
from __future__ import annotations

from contextlib import contextmanager
import copy
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import threading
import weakref

from ipfs_accelerate_py.agent_supervisor.control import profile_authority as profiles
from ipfs_accelerate_py.agent_supervisor.core.multiformats_identity import cid_for_dag_json
from ipfs_accelerate_py.agent_supervisor.planning.formal_plan_compiler import FormalPlanCompiler
from ipfs_accelerate_py.agent_supervisor.planning.formal_plan_validator import validate_formal_plan
from ipfs_accelerate_py.agent_supervisor.proof.formal_verification_contracts import content_identity
from ipfs_accelerate_py.agent_supervisor.prompt.prompt_workflow import (
    PromptAcceptanceRecord, PromptGoalGraph, PromptGoalRecord, PromptOutputRecord,
    PromptTaskRecord, PromptValidationRecord,
)
from ipfs_accelerate_py.agent_supervisor.runtime import local_planning_admission as native
from ipfs_accelerate_py.agent_supervisor.runtime.supervisor_meta_index import public_replay_without_metadata
from ipfs_accelerate_py.agent_supervisor.task_sources.intent_repository import IntentRepository

ROOT = Path(__file__).resolve().parent
INPUT_NAME = "input-binding.json"
VALIDATOR_NAME = "validate-planning-observation.py"
OUTPUT_NAME = "planning-observation.json"
FALSE = {name: False for name in (
    "original_task_coverage", "original_requirements_resolved", "completion_authority",
    "code_proof_authority", "production_activation", "source_model_equivalence",
    "semantic_intent_understanding", "convergence_proved", "account_registry_authority",
)}
_LOCK = threading.RLock()
_LIVE = weakref.WeakSet()
_CURRENT = None
_TOKEN = object()


def _wire(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("ascii")


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _same(left, right):
    # JSON distinguishes false from 0 and true from 1; Python equality does not.
    return _wire(left) == _wire(right)


def _data(value, *, depth=0, count=None):
    """Bound exact JSON types; preserve every text byte, without normalization."""
    if count is None:
        count = [0]
    count[0] += 1
    if depth > 32 or count[0] > 100000:
        raise ValueError("input binding structure bound exceeded")
    if value is None or type(value) in (str, bool, int):
        if type(value) is str:
            value.encode("utf-8", "strict")
        return
    if type(value) is dict:
        if any(type(key) is not str for key in value):
            raise ValueError("input binding keys must be exact strings")
        for key, item in value.items():
            key.encode("utf-8", "strict")
            _data(item, depth=depth+1, count=count)
        return
    if type(value) is list:
        for item in value:
            _data(item, depth=depth+1, count=count)
        return
    raise ValueError("input binding requires finite, float-free exact JSON data")


def validate_input_binding(value):
    if type(value) is not dict:
        raise ValueError("input binding must be an exact dict")
    _data(value)
    required = {"native_head", "instructions", "source_records", "max_input_tokens"}
    if not required <= set(value) or type(value["native_head"]) is not dict or not value["native_head"]:
        raise ValueError("complete native head and public input binding required")
    limit = value["max_input_tokens"]
    if type(limit) is not int or not 1 <= limit <= 1000000:
        raise ValueError("positive bounded input-token budget required")
    instructions = value["instructions"]
    sources = value["source_records"]
    if type(instructions) is not list or not 1 <= len(instructions) <= 4:
        raise ValueError("one to four complete public instructions required")
    if type(sources) is not list or not 1 <= len(sources) <= 5:
        raise ValueError("one to five complete public sources required")
    seen = set()
    for row in instructions:
        if type(row) is not dict or not {"task_id", "instruction_text", "instruction_sha256"} <= set(row):
            raise ValueError("whole instruction fields required")
        task_id, text = row["task_id"], row["instruction_text"]
        if (type(task_id) is not str or not task_id or len(task_id) > 256 or task_id.strip() != task_id
                or any(char in task_id for char in "\n\r\0") or task_id in seen
                or type(text) is not str or not text.strip()):
            raise ValueError("instruction identity or whole text invalid")
        seen.add(task_id)
        if _sha(text.encode("utf-8")) != row["instruction_sha256"]:
            raise ValueError("whole instruction SHA differs")
    seen = set()
    for row in sources:
        if type(row) is not dict or not {"path", "sha256", "source_text"} <= set(row):
            raise ValueError("whole source fields required")
        path, text = row["path"], row["source_text"]
        if type(path) is not str or type(text) is not str or not path or len(path) > 1024 or any(char in path for char in "\n\r\0"):
            raise ValueError("source identity or text invalid")
        rel = PurePosixPath(path)
        if path == "." or rel.is_absolute() or str(rel) != path or any(part in (".", "..", ".git") for part in rel.parts) or path in seen:
            raise ValueError("source paths must be unique canonical relative paths")
        seen.add(path)
        if _sha(text.encode("utf-8")) != row["sha256"]:
            raise ValueError("whole source SHA differs")
    raw = _wire(value)
    if len(raw) > 750000:
        raise ValueError("complete public input exceeds job source bound")
    return copy.deepcopy(value)


# This fixed, tracked script validates only the metatask's eventual observation.
# It neither imports nor executes the original repository's source code.
VALIDATOR = '''"""Validate a planning-observation artifact, not benchmark correctness."""
import hashlib,json,pathlib
root=pathlib.Path(__file__).resolve().parent
def need(condition):
    if not condition: raise ValueError("planning-observation contract failed")
def pairs(items):
    result={}
    for key,value in items:
        need(key not in result)
        result[key]=value
    return result
def load(path):
    need(path.is_file() and not path.is_symlink() and path.stat().st_size<=1000000)
    data=path.read_bytes()
    return data,json.loads(data,object_pairs_hook=pairs,parse_constant=lambda value:need(False))
raw,binding=load(root/"input-binding.json")
_,out=load(root/"planning-observation.json")
false_names=("original_task_coverage","original_requirements_resolved","completion_authority","code_proof_authority","production_activation","source_model_equivalence","semantic_intent_understanding","convergence_proved","account_registry_authority")
need(type(out) is dict and set(out)=={"schema","input_binding","input_binding_sha256","native_head","observed_input_tokens","observations",*false_names})
need(out["schema"]=="terminal-planning-observation@1")
need(out["input_binding"]==binding)
need(out["input_binding_sha256"]==hashlib.sha256(raw).hexdigest())
need(out["native_head"]==binding["native_head"])
need(type(out["observed_input_tokens"]) is int and 0<=out["observed_input_tokens"]<=binding["max_input_tokens"])
need(type(out["observations"]) is list and 1<=len(out["observations"])<=32)
need(all(type(row) is dict for row in out["observations"]))
need(all(out[key] is False for key in false_names))
'''


def _canonical_path(path):
    path = Path(path).absolute()
    if path.resolve() != path:
        raise ValueError("owned job paths must have no symlink components")
    return path


def _git(root, *args):
    env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL="/dev/null", GIT_TEMPLATE_DIR="")
    for key in list(env):
        if key.startswith("GIT_") and key not in {"GIT_CONFIG_NOSYSTEM", "GIT_CONFIG_GLOBAL", "GIT_TEMPLATE_DIR"}:
            del env[key]
    return subprocess.check_output(["git", "-C", str(root), *args], env=env,
                                   stderr=subprocess.PIPE, timeout=10).decode().strip()


def _empty_directory(path, *, private=False):
    if path.exists():
        info = path.stat()
        if not path.is_dir() or any(path.iterdir()) or info.st_uid != os.geteuid():
            raise ValueError("owned job directories must be fresh, empty and user-owned")
        if private and stat.S_IMODE(info.st_mode) != 0o700:
            raise ValueError("private job root must have exact mode 0700")
    else:
        path.mkdir(mode=0o700 if private else 0o755)
    return path.stat().st_dev, path.stat().st_ino


def _task_invariants(task):
    return {key: copy.deepcopy(value) for key, value in dict(task).items()
            if key not in {"status", "revision", "created_at", "updated_at"}}


class OwnedPlanningJob:
    """Live, scoped native ownership; serialized public fields cannot recreate it."""
    def __init__(self, token, **values):
        if token is not _TOKEN:
            raise TypeError("owned planning jobs must be created by the context manager")
        self.__dict__.update(values)

    @property
    def job_binding(self):
        return json.loads(self._binding_bytes)

    @property
    def input_binding(self):
        return json.loads(self._input_bytes)

    @property
    def task_id(self):
        return self.job_binding["task_key"]

    @property
    def report(self):
        return copy.deepcopy(self._report)


def verify_planning_job(job):
    """Observe the live native job; public dictionaries alone grant no authority."""
    if not isinstance(job, OwnedPlanningJob) or job not in _LIVE or _CURRENT is not job or not job.intent.is_open:
        raise ValueError("a live owned planning job is required")
    if profiles._LIFECYCLE_REGISTRY_ROOT_OVERRIDE != job._registry_root:
        raise ValueError("owned fixture registry scope changed")
    if job.intent.owner_id != job._owner_id or job.intent.session_id != job._session_id:
        raise ValueError("native intent owner identity changed")
    if (job.job_repository / INPUT_NAME).read_bytes() != job._input_bytes:
        raise ValueError("complete planning job input binding changed")
    artifact = job.job_repository / OUTPUT_NAME
    if job._observation_bytes is None:
        if artifact.exists() or artifact.is_symlink():
            raise ValueError("undeclared planning observation appeared outside owned writer")
    elif artifact.is_symlink() or artifact.read_bytes() != job._observation_bytes:
        raise ValueError("owned planning observation changed")
    with public_replay_without_metadata():
        verified = native.verify_local_benchmark_admission(job.admission,
            initial=job._observation_bytes is None)
    if content_identity(job.admission) != job._admission_cid or verified["receipt"] != job._receipt:
        raise ValueError("native signed planning admission changed")
    task = job.intent.get_task(job.task_cid)
    plan = job.intent.get_plan(job.plan_id)
    if task is None or not _same(_task_invariants(task), job._task_snapshot):
        raise ValueError("native planning task body, identity or declared relations changed")
    if task["status"] in {"done", "complete", "completed", "skipped", "cancelled", "canceled"}:
        raise ValueError("planning observation acceptance must remain pending")
    if plan is None or plan["body"] != {"local_planning_receipt_ref": job.receipt_reference} or plan["status"] != "active":
        raise ValueError("native planning plan or receipt reference changed")
    with public_replay_without_metadata():
        if native.load_local_planning_receipt(job.receipt_reference, manifest=job.manifest) != job.admission["receipt"]:
            raise ValueError("native planning receipt reference differs")
    return job.job_binding


def write_planning_observation(job, capture_report):
    """Create only the declared data artifact; no acceptance transition is made.

    The caller's independently checked capture remains observational data. This
    helper binds its canonical digest and token count and preserves the entire
    signed input. It does not authenticate a caller-supplied capture dictionary.
    """
    verify_planning_job(job)
    if job._observation_bytes is not None:
        raise ValueError("planning observation is create-only")
    _data(capture_report)
    if type(capture_report) is not dict:
        raise ValueError("capture observation must be an exact dict")
    try:
        tokens = capture_report["observation"]["selection"]["input_tokens"]
    except (KeyError, TypeError):
        raise ValueError("capture selected full-input token count required") from None
    if type(tokens) is not int or not 0 <= tokens <= job.input_binding["max_input_tokens"]:
        raise ValueError("capture input tokens exceed signed planning budget")
    capture_bytes = _wire(capture_report)
    observation = {"schema": "terminal-planning-observation@1", "input_binding": job.input_binding,
        "input_binding_sha256": _sha(job._input_bytes), "native_head": job.input_binding["native_head"],
        "observed_input_tokens": tokens, "observations": [{"capture_sha256": _sha(capture_bytes),
        "capture_bytes": len(capture_bytes), "capture_origin_authenticated_by_writer": False}], **FALSE}
    raw = _wire(observation)
    if len(raw) > 1000000:
        raise ValueError("planning observation exceeds native output bound")
    target = job.job_repository / OUTPUT_NAME
    with target.open("xb") as stream:
        stream.write(raw)
    job._observation_bytes = raw
    verify_planning_job(job)
    return {"path": str(target), "bytes": len(raw), "sha256": _sha(raw),
            "acceptance_pending": True, "capture_origin_authenticated_by_writer": False, **FALSE}


def verify_historical_planning_report(report):
    """Replay retained public signatures and plans, with no current authority.

    The retained root DID is a fixture root, not an independently trusted account
    identity. This check establishes consistency of that historical signed
    bundle. It never opens former profile, lifecycle, repository or DB paths.
    """
    keys = {"schema", "job_binding", "native_admission", "native_materialization",
        "native_formal_compilation", "native_plan_validation", "native_profile", "native_lifecycle_witness",
        "native_receipt_reference", "original_instruction_residuals", "native_pending_contract",
        "authority_scope", "capability_scope", "profile_capabilities", "public_evidence_historical_only",
        "acceptance_pending", "original_source_execution", "external_provider_invocations", "optimizer_steps",
        "prover_invocations", *FALSE}
    if type(report) is not dict or set(report) != keys or report.get("schema") != "terminal-owned-planning-job@1":
        raise ValueError("historical owned planning report required")
    if len(_wire(report)) > 8000000:
        raise ValueError("historical planning report exceeds bounded public replay")
    if any(report.get(key) is not False for key in FALSE):
        raise ValueError("historical report cannot promote original-task or account authority")
    if report.get("acceptance_pending") is not True or report.get("public_evidence_historical_only") is not True:
        raise ValueError("historical observation acceptance must remain pending")
    if report.get("authority_scope") != "isolated-experimental-fixture-registry" or report.get("capability_scope") != "bounded-local-work":
        raise ValueError("historical fixture scope changed")
    if report.get("original_source_execution") is not False or any(type(report.get(key)) is not int or report[key] != 0
            for key in ("external_provider_invocations", "optimizer_steps", "prover_invocations")):
        raise ValueError("historical report promotes execution, provider or proof claims")
    bound = report["job_binding"]
    bound_keys = {"schema", "task_key", "task_cid", "goal_cid", "plan_id", "graph_cid", "manifest_cid",
        "admission_cid", "receipt_cid", "pending_cid", "job_repository", "repository_cid", "baseline_commit",
        "source_tree_id", "intent_owner_id", "intent_session_id", "input_binding_sha256", "input_binding_cid",
        "input_binding", "native_head", *FALSE}
    if type(bound) is not dict or set(bound) != bound_keys:
        raise ValueError("closed historical job binding required")
    binding = validate_input_binding(bound["input_binding"])
    raw = _wire(binding)
    if any(bound.get(key) is not False for key in FALSE):
        raise ValueError("historical job binding promotes authority")
    if (bound.get("input_binding_sha256") != _sha(raw) or bound.get("input_binding_cid") != cid_for_dag_json(binding)
            or not _same(bound.get("native_head"), binding["native_head"])):
        raise ValueError("historical whole-input binding changed")
    witness = report["native_lifecycle_witness"]
    with public_replay_without_metadata():
        profile = profiles.verify_local_profile_lifecycle_witness(witness,
            expected_board_namespace="terminal-planning-observation-fixture",
            expected_base_head=bound["baseline_commit"], expected_base_tree=witness["base_tree"],
            expected_nonce="planning-observation-" + _sha(raw),
            expected_root_identity_did=witness["root_identity_did"],
            reference_time_ms=witness["observed_at_ms"],
            max_age_ms=witness["expires_at_ms"] - witness["observed_at_ms"])
        admission = report["native_admission"]
        if set(admission) != {"manifest", "graph", "receipt"}:
            raise ValueError("exact historical admission bundle required")
        manifest = native._verify_signature(admission["manifest"], profile)
        if manifest["schema"] != native.CREATE_MANIFEST_SCHEMA:
            raise ValueError("historical job requires the distinct declared-create profile")
        native._validate_local_manifest_declarations(manifest)
        if (manifest["sources"] != {
            INPUT_NAME: {"sha256": _sha(raw), "executable": False},
            VALIDATOR_NAME: {"sha256": _sha(VALIDATOR.encode()), "executable": False}}
                or manifest["created_outputs"] != [OUTPUT_NAME]):
            raise ValueError("historical complete input or fixed validator source changed")
        graph = PromptGoalGraph.from_dict(admission["graph"])
        if len(graph.tasks) != 1 or graph.tasks[0].task_key != bound["task_key"]:
            raise ValueError("historical metatask population changed")
        receipt = native._verify_signature(admission["receipt"], profile)
        expected_receipt = native._planning_payload(graph, admission["manifest"], manifest, profile, manifest["sources"])
        if receipt != expected_receipt:
            raise ValueError("historical native planning receipt differs from public replay")
        compiled = FormalPlanCompiler().compile_prompt_graph(graph,
            repository_tree_id=native._tree(manifest["sources"]), actor_id=profile.content_id)
        checked = validate_formal_plan(compiled.plan, compiled.formulas)
        if not _same(compiled.to_dict(), report["native_formal_compilation"]) or not _same(checked.to_dict(), report["native_plan_validation"]):
            raise ValueError("historical formal compilation or validation differs")
        pending = native._verify_signature(report["native_pending_contract"], profile)
        expected_pending = native._pending_contract_payload(admission=admission,
            verified={"manifest": manifest, "graph": graph, "receipt": receipt},
            task=graph.tasks[0], intent_owner_id=bound["intent_owner_id"])
        if pending != expected_pending:
            raise ValueError("historical signed pending contract differs")
    reference = native._receipt_reference(admission["receipt"], native._receipt_bytes(admission["receipt"]))
    expected_joins = {"schema": "terminal-owned-planning-job-binding@1", "task_key": graph.tasks[0].task_key,
        "task_cid": graph.tasks[0].task_cid, "goal_cid": graph.tasks[0].goal_cid,
        "plan_id": receipt["plan_id"], "graph_cid": graph.content_id,
        "manifest_cid": content_identity(admission["manifest"]), "admission_cid": content_identity(admission),
        "receipt_cid": reference["receipt_cid"], "pending_cid": receipt["pending_cid"],
        "job_repository": manifest["repository"], "repository_cid": manifest["repository_cid"],
        "baseline_commit": manifest["baseline_commit"], "source_tree_id": receipt["source_tree_id"]}
    if any(not _same(bound.get(key), value) for key, value in expected_joins.items()):
        raise ValueError("historical native job join differs")
    repository_cid = cid_for_dag_json({"schema": "ipfs_accelerate_py.agent_supervisor.observed-repository-root@1",
        "root": manifest["repository"], "head_tree": witness["base_tree"]})
    if (not _same(profile.to_dict(), report["native_profile"]) or profile.repository_cid != repository_cid
            or repository_cid != bound["repository_cid"] or profile.baseline_commit != bound["baseline_commit"]
            or manifest["profile_content_id"] != profile.content_id
            or report["profile_capabilities"] != sorted(profiles.ALLOWED_LOCAL_CAPABILITIES)
            or sorted(profile.capabilities) != report["profile_capabilities"]
            or not _same(reference, report["native_receipt_reference"])):
        raise ValueError("historical public profile, repository or receipt reference differs")
    residuals = [{"task_id": row["task_id"], "instruction_text": row["instruction_text"],
        "instruction_sha256": row["instruction_sha256"], "required": True, "resolved": False,
        "coverage": "whole-original-instruction-unresolved"} for row in binding["instructions"]]
    if not _same(report["original_instruction_residuals"], residuals):
        raise ValueError("historical original instruction residuals changed")
    materialization = {"schema": "supervisor-local-materialization@1", "plan_id": receipt["plan_id"],
        "task_cids": [graph.tasks[0].task_cid], "pending_cid": receipt["pending_cid"],
        "manifest_cid": receipt["manifest_cid"], "completion_authority": False}
    if not _same(report["native_materialization"], materialization):
        raise ValueError("historical native materialization reference changed")
    return {"schema": "terminal-historical-planning-report-replay@1", "consistent": True,
        "historical_signature_consistency_only": True, "current_owner_authority": False,
        "live_registry_observed": False, "private_state_opened": False,
        "job_binding": copy.deepcopy(bound), **FALSE}


@contextmanager
def create_owned_planning_job(*, job_repository: Path, private_root: Path,
                              public_output: Path, input_binding: dict, task_key: str):
    """Admit/materialize one native metatask, then destroy only its private state.

    The caller supplies disjoint fresh directories.  ``private_root`` must be
    outside this evidence stage.  Only the two public job sources are tracked;
    the original codebase is preserved as inert bytes in the input binding.
    """
    global _CURRENT
    binding = validate_input_binding(input_binding)
    if type(task_key) is not str or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}", task_key) is None:
        raise ValueError("bounded literal task key required")
    repo, private, output = map(_canonical_path, (job_repository, private_root, public_output))
    paths = (repo, private, output)
    if any(a == b or a in b.parents or b in a.parents for i, a in enumerate(paths) for b in paths[i+1:]):
        raise ValueError("public job, private owner and evidence directories must be disjoint")
    if private == ROOT or ROOT in private.parents:
        raise ValueError("private owner state must be outside the evidence stage")
    with _LOCK:
        if _CURRENT is not None:
            raise ValueError("owned fixture registry jobs may not overlap")
        # Validate all roots before taking cleanup ownership of private_root.
        for path in (repo, output):
            if path.exists() and (not path.is_dir() or any(path.iterdir()) or path.stat().st_uid != os.geteuid()):
                raise ValueError("owned public directories must be fresh and empty")
        private_identity = _empty_directory(private, private=True)
        previous_override = profiles._LIFECYCLE_REGISTRY_ROOT_OVERRIDE
        registry = private / "fixture-registry"
        intent = None
        job = None
        try:
            profiles._LIFECYCLE_REGISTRY_ROOT_OVERRIDE = registry
            _empty_directory(repo)
            _empty_directory(output)
            raw = _wire(binding)
            (repo / INPUT_NAME).write_bytes(raw)
            (repo / VALIDATOR_NAME).write_text(VALIDATOR, encoding="utf-8")
            _git(repo, "init", "--quiet")
            _git(repo, "add", "--", INPUT_NAME, VALIDATOR_NAME)
            _git(repo, "-c", "user.name=Planning Fixture", "-c", "user.email=fixture@invalid.local",
                 "-c", "commit.gpgsign=false", "commit", "--quiet", "-m", "Bind public planning-observation inputs")
            _, baseline, repository_cid = native._repository(repo)
            base_tree = _git(repo, "rev-parse", "HEAD^{tree}")
            profile_dir, lifecycle_dir = private / "profile", private / "lifecycle"
            with public_replay_without_metadata():
                profile = profiles.initialize_local_profile(repository_cid=repository_cid,
                    baseline_commit=baseline, profile_dir=profile_dir, lifecycle_dir=lifecycle_dir)
            policy_cid = content_identity(native.LOCAL_POLICY)
            validation = PromptValidationRecord(validation_key="observation-shape-head-budget-fulltext",
                argv=(sys.executable, VALIDATOR_NAME), policy_cid=policy_cid)
            criteria = (
                ("observation-shape", "The created artifact has the exact bounded planning-observation schema."),
                ("current-head-binding", "The observation repeats the complete original native codebase head binding."),
                ("input-token-budget", "The observed input-token count is an integer within the declared maximum."),
                ("fulltext-preservation", "The observation preserves every complete instruction and source input byte through the exact input binding."),
                ("original-requirements-pending", "Original coding requirements and all proof and completion authority remain unresolved and false."),
            )
            acceptance = tuple(PromptAcceptanceRecord(criterion_key=key, criterion=text,
                validation_keys=(validation.validation_key,)) for key, text in criteria)
            scope = (INPUT_NAME, OUTPUT_NAME, VALIDATOR_NAME)
            objective = "Create a bounded planning-observation artifact over the complete public input binding."
            provenance = {"input_binding_sha256": _sha(raw), "input_binding_cid": cid_for_dag_json(binding),
                          "authority_scope": "isolated-experimental-fixture-registry", **FALSE}
            goal = PromptGoalRecord(goal_key="planning-observation-goal", parent_goal_cid="",
                dependency_goal_cids=(), title="Bounded planning observation", objective=objective,
                rationale="Observe planning input delivery while all original coding requirements remain pending.",
                scope_paths=scope, acceptance=acceptance, provenance=provenance)
            task = PromptTaskRecord(task_key=task_key, goal_cid=goal.goal_cid, dependency_task_cids=(),
                objective=objective, rationale=goal.rationale, scope_paths=scope,
                outputs=(PromptOutputRecord(path=OUTPUT_NAME, effect="create", media_type="application/json"),),
                validations=(validation,), acceptance=acceptance, evidence_cids=(), policy_roots=(policy_cid,),
                track="isolated-planning-observation", predicted_files=(OUTPUT_NAME,), provenance=provenance)
            roots = {"request_cid": cid_for_dag_json({"schema": "terminal-planning-observation-request@1", "binding": binding}),
                     "scan_cid": cid_for_dag_json({"schema": "terminal-planning-observation-source-binding@1", "sources": binding["source_records"]}),
                     "program_root": cid_for_dag_json({"schema": "terminal-planning-observation-program@1", "native_head": binding["native_head"]})}
            graph = PromptGoalGraph(**roots, policy_roots=(policy_cid,), goals=(goal,), tasks=(task,), evidence=())
            spec = {"task_key": task.task_key, "scope_paths": list(task.scope_paths),
                    "outputs": [{key: getattr(row, key) for key in ("path", "effect", "media_type")} for row in task.outputs],
                    "validations": [{"validation_key": validation.validation_key, "argv": list(validation.argv), "cwd": ".", "expected_exit_codes": [0], "policy_cid": policy_cid}],
                    "acceptance": [{"criterion_key": row.criterion_key, "criterion": row.criterion, "evidence_cids": [], "validation_keys": list(row.validation_keys)} for row in task.acceptance],
                    "dependencies": []}
            owner_id, session_id = "planning-fixture-owner", "planning-fixture-" + _sha(raw)[:24]
            with public_replay_without_metadata():
                intent = IntentRepository(private / "intent.duckdb", owner_id=owner_id, session_id=session_id)
                manifest = native.author_local_benchmark_manifest(repository=repo, profile_dir=profile_dir,
                    lifecycle_dir=lifecycle_dir, task_specs=[spec], planning_roots=roots)
                compiled = FormalPlanCompiler().compile_prompt_graph(graph,
                    repository_tree_id=native._tree(manifest["payload"]["sources"]), actor_id=profile.content_id)
                if compiled.plan is None or compiled.status.value != "compiled" or compiled.proof_results:
                    raise ValueError("native metatask did not compile to an unproved formal plan")
                validation_result = validate_formal_plan(compiled.plan, compiled.formulas)
                if validation_result.status.value != "consistent":
                    raise ValueError("native planning-observation formal plan inconsistent")
                admission = native.admit_local_benchmark_plan(graph=graph, manifest=manifest)
                materialization = native.materialize_local_benchmark_plan(admission=admission, intent=intent)
                verified = native.verify_local_benchmark_admission(admission, initial=True)
            receipt = verified["receipt"]
            if materialization["task_cids"] != [task.task_cid] or receipt["plan_id"] != compiled.plan.plan_id:
                raise ValueError("native materialization task/plan join differs")
            plan = intent.get_plan(receipt["plan_id"])
            reference = copy.deepcopy(plan["body"]["local_planning_receipt_ref"])
            with public_replay_without_metadata():
                witness = profiles.export_local_profile_lifecycle_witness(repository_cid=repository_cid,
                    board_namespace="terminal-planning-observation-fixture", base_head=baseline,
                    base_tree=base_tree, nonce="planning-observation-" + _sha(raw),
                    profile_dir=profile_dir, lifecycle_dir=lifecycle_dir)
            job_binding = {"schema": "terminal-owned-planning-job-binding@1", "task_key": task_key,
                "task_cid": task.task_cid, "goal_cid": goal.goal_cid, "plan_id": receipt["plan_id"],
                "graph_cid": graph.content_id, "manifest_cid": receipt["manifest_cid"],
                "admission_cid": content_identity(admission), "receipt_cid": reference["receipt_cid"],
                "pending_cid": receipt["pending_cid"], "job_repository": str(repo),
                "repository_cid": repository_cid, "baseline_commit": baseline,
                "source_tree_id": receipt["source_tree_id"], "intent_owner_id": owner_id,
                "intent_session_id": session_id, "input_binding_sha256": _sha(raw),
                "input_binding_cid": cid_for_dag_json(binding), "input_binding": binding,
                "native_head": binding["native_head"], **FALSE}
            residuals = [{"task_id": row["task_id"], "instruction_text": row["instruction_text"],
                "instruction_sha256": row["instruction_sha256"], "required": True, "resolved": False,
                "coverage": "whole-original-instruction-unresolved"} for row in binding["instructions"]]
            report = {"schema": "terminal-owned-planning-job@1", "job_binding": job_binding,
                "native_admission": admission, "native_materialization": materialization,
                "native_formal_compilation": compiled.to_dict(), "native_plan_validation": validation_result.to_dict(),
                "native_profile": profile.to_dict(), "native_lifecycle_witness": witness,
                "native_receipt_reference": reference, "original_instruction_residuals": residuals,
                "native_pending_contract": copy.deepcopy(intent.get_task(task.task_cid)["body"][native.CONTRACT_KEY]),
                "authority_scope": "isolated-experimental-fixture-registry",
                "capability_scope": "bounded-local-work", "profile_capabilities": sorted(profile.capabilities),
                "public_evidence_historical_only": True, "acceptance_pending": True,
                "original_source_execution": False, "external_provider_invocations": 0,
                "optimizer_steps": 0, "prover_invocations": 0, **FALSE}
            job = OwnedPlanningJob(_TOKEN, intent=intent, task_cid=task.task_cid, plan_id=receipt["plan_id"],
                graph=graph, admission=admission, manifest=manifest, receipt_reference=reference,
                job_repository=repo, _registry_root=registry, _owner_id=owner_id, _session_id=session_id,
                _input_bytes=raw, _observation_bytes=None,
                _admission_cid=content_identity(admission), _receipt=copy.deepcopy(receipt),
                _task_snapshot=_task_invariants(intent.get_task(task.task_cid)),
                _binding_bytes=_wire(job_binding), _report=report)
            _CURRENT = job
            _LIVE.add(job)
            verify_planning_job(job)
            (output / "planning-job.json").write_bytes(_wire(report))
            yield job
            verify_planning_job(job)
        finally:
            if job is not None:
                _LIVE.discard(job)
            _CURRENT = None
            if intent is not None:
                intent.close()
            profiles._LIFECYCLE_REGISTRY_ROOT_OVERRIDE = previous_override
            # Never follow a replaced root when removing this context's state.
            if private.exists() and not private.is_symlink():
                info = private.stat()
                if (info.st_dev, info.st_ino) != private_identity:
                    raise RuntimeError("owned private root identity changed; refusing cleanup")
                shutil.rmtree(private)

