"""Export public review bindings for one already admitted preparation.

The empty template is not a review decision. An external author must supply
selectors and independently pin the completed review before resuming the same
owner. This export neither changes signed inputs nor supplies planning facts.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


SCHEMA = "terminal-source-nomination-review-preparation@1"
MAX_BYTES = 65536


def _wire(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def prepare_source_nomination_review_baseline(*, state: Path) -> dict:
    """Replay actual admission/current sources and export exact public identities."""
    from ipfs_accelerate_py.agent_supervisor.runtime.supervisor_meta_index import public_replay_without_metadata
    with public_replay_without_metadata():
        return _prepare(state=state)


def _prepare(*, state):
    from . import terminal_indexed_preparation as preparation
    from .terminal_initial_context import load_initial_context
    from ipfs_accelerate_py.agent_supervisor.runtime import code_source_inspection as source
    from ipfs_accelerate_py.agent_supervisor.runtime.code_retrieval_frontier import prepare_code_retrieval_frontier
    from ipfs_accelerate_py.agent_supervisor.runtime.intent_source_nomination import build_intent_source_nomination, REVIEW_SCHEMA
    from ipfs_accelerate_py.agent_supervisor.runtime.intent_source_inspection import _publish, _parent_names, _capture_after_publication
    from ipfs_accelerate_py.agent_supervisor.task_sources.intent_repository import IntentRepository

    state = Path(state).absolute()
    if state.resolve(strict=True) != state:
        raise ValueError("same canonical prepared owner state required")
    prepared = preparation._load_prepared(state)
    contract = prepared.get("intent_requirement_contract")
    if type(contract) is not dict or contract.get("schema") != "intent-plan-requirement-contract@2":
        raise ValueError("source review preparation requires an explicit symbolic requirement contract")
    admission = json.loads((state / "admission.json").read_bytes())
    verified = preparation.local.verify_local_benchmark_admission(admission, initial=True)
    if admission["manifest"] != prepared["manifest"] or len(verified["graph"].tasks) != 1:
        raise ValueError("source review preparation differs from admitted declaration")
    repository = Path(prepared["repository"])
    loaded = load_initial_context(state=state, prepared=prepared, require_empty_owner=False)
    task = verified["graph"].tasks[0]
    with IntentRepository(state / "intent.duckdb", install_schema=False) as intent:
        tasks = intent.plan_projection(task_cids=[task.task_cid])["tasks"]
    if len(tasks) != 1 or tasks[0]["status"] != "ready" or tasks[0]["task_cid"] != task.task_cid:
        raise ValueError("source review requires the current ready admitted task")
    task_revision = str(tasks[0]["revision"])
    metadata = loaded["descriptor"]["metadata"]
    output = repository / ".runtime/source-review-preparation"
    if output.resolve(strict=False) != output or output.exists():
        raise ValueError("new public source review namespace required")
    frontier = prepare_code_retrieval_frontier(repository=repository,
        task_id=task.task_key, task_cid=task.task_cid, task_revision=task_revision,
        repository_id=loaded["descriptor"]["repository_id"], tree_id=loaded["semantic"]["scope_cid"],
        source_artifact=metadata["Code retrieval artifact"], source_sha256=metadata["Code retrieval sha256"],
        output=output / "frontier")
    fm = frontier["metadata"]
    evidence = source._capture_native_evidence(repository,
        fm["Code retrieval frontier artifact"], fm["Code retrieval frontier sha256"],
        task.task_key, task.task_cid,
        metadata["Code retrieval artifact"], metadata["Code retrieval sha256"])
    generic = build_intent_source_nomination(contract=contract, source_text=prepared["query"],
        task_id=task.task_key, task_cid=task.task_cid, task_revision=task_revision,
        repository_id=evidence["spec"]["repository_id"], tree_id=evidence["spec"]["tree_id"],
        snapshot=evidence["snapshot"], source_by_path=evidence["sources"])
    template = {"schema": REVIEW_SCHEMA, "bindings": generic["bindings"],
        "review_ref": "pending:external-source-selector-review", "selectors": []}
    template_raw = _wire(template)
    public_output = output / "review"
    template_path = public_output / "review-template.json"
    result = {"schema": SCHEMA, "task_id": task.task_key, "task_cid": task.task_cid,
        "task_revision": task_revision, "bindings": generic["bindings"],
        "review_template": {"artifact": template_path.relative_to(repository).as_posix(),
            "sha256": hashlib.sha256(template_raw).hexdigest(), "bytes": len(template_raw)},
        "requirements": [{"requirement_id": row["native_requirement"]["requirement_id"],
            "statement_ids": row["native_requirement"]["statement_ids"], "mandatory": row["mandatory"],
            "residual": True} for row in generic["requirements"]],
        "unknown_census": generic["unknown_census"],
        "original_retrieval": {"artifact": metadata["Code retrieval artifact"], "sha256": metadata["Code retrieval sha256"]},
        "review_frontier": {"artifact": fm["Code retrieval frontier artifact"], "sha256": fm["Code retrieval frontier sha256"]},
        "instructions": "Copy the template into a separate public review file; author review_ref and explicit requirement_id/path/qualified_symbol selectors, preserve all bindings, then pin the completed canonical UTF-8 JSON SHA-256 and resume the same prepared owner. The empty template makes no selection decision.",
        "review_required": True, "authored_selectors": False,
        "review_authentication_claimed": False, "source_authentication_claimed": False,
        "signed_planning_inputs_modified": False, "planner_current_facts_added": 0,
        "behavioral_requirements_satisfied": False, "proof_authority": False,
        "execution_authority": False, "completion_authority": False}
    raw = _wire(result)
    if len(raw) > MAX_BYTES or len(template_raw) > MAX_BYTES:
        raise ValueError("complete source review export exceeds its byte bound")
    # Reuse the protected publisher and exact authorized-parent-change guard.
    # Fresh public outputs only; no signing state or existing source is written.
    capture = evidence["capture"]
    files = {"review-template.json": template_raw, "bindings.json": raw}
    if len(capture.values) + len(files) > source.MAX_FILES:
        raise ValueError("source review export exceeds captured file bound")
    if sum(map(len, capture.values.values())) + sum(map(len, files.values())) > source.MAX_CAPTURE_BYTES:
        raise ValueError("source review export exceeds captured byte bound")
    directories = {(root, key) for root, witnesses in capture.witnesses.items()
        for key in witnesses if key.startswith("directory:")}
    parts = public_output.relative_to(repository).parts
    directories.update((repository, "directory:" + "/".join(parts[:end])) for end in range(1, len(parts) + 1))
    if len(directories) > source.MAX_DIRECTORIES:
        raise ValueError("source review export exceeds captured directory bound")
    parent_before = _parent_names(repository, public_output.parent)
    capture.verify_originals()
    _publish(repository, public_output, files)
    _capture_after_publication(capture, public_output, files, parent_before).verify_originals()
    preparation.local.verify_local_benchmark_admission(admission, initial=True)
    load_initial_context(state=state, prepared=prepared, require_empty_owner=False)
    if preparation._load_prepared(state) != prepared:
        raise ValueError("prepared declaration changed during source review export")
    return {"schema": SCHEMA, "artifact": (public_output / "bindings.json").relative_to(repository).as_posix(),
        "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
        "review_template": result["review_template"], "review_required": True,
        "task_id": task.task_key, "task_cid": task.task_cid, "task_revision": task_revision,
        "signed_planning_inputs_modified": False, "planner_current_facts_added": 0,
        "proof_authority": False, "execution_authority": False, "completion_authority": False}
