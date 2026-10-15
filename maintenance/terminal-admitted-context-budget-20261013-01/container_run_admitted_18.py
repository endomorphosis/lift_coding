"""One genuine native START with original current model and budget in this owner.

The registered observer stops before providers. No source-nomination phase is
claimed. Public outputs are explicitly written under the public child only.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import time
import traceback

os.umask(0o077)
assert os.getuid() == os.geteuid() == 1000
ROOT = Path("/opt/ipfs-supervisor")
OUT = ROOT / "state/aa-start-18"
PUBLIC = OUT / "public"
MODEL = ROOT / "state/aa-model-18"
FIXTURE = ROOT / "public-fixture-aa18"
REPOSITORY = Path("/app")
WORKTREES = ROOT / "worktrees"
assert not OUT.exists()
OUT.mkdir(mode=0o700)
PUBLIC.mkdir(mode=0o700)
os.environ["IPFS_ACCELERATE_META_INDEX_DUCKDB"] = str(OUT / "meta-index.duckdb")
os.environ["IPFS_ACCELERATE_PYTEST_SEAL_DUCKDB"] = str(OUT / "pytest-seal.duckdb")
os.environ["IPFS_ACCELERATE_AGENT_ORCHESTRATION_DIR"] = str(OUT / "orchestration")

from benchmarks.agent_supervisor.container_coding.terminal_codebase_finite_service_experiment import _open, _scheduler
from benchmarks.agent_supervisor.container_coding.terminal_call_ir_composition import validate_current_call_composition
from benchmarks.agent_supervisor.container_coding import terminal_call_review_planning as planning
from benchmarks.agent_supervisor.container_coding import terminal_semantic_call_review as semantic
from benchmarks.agent_supervisor.container_coding import terminal_semantic_audit_review as audit_review
from benchmarks.agent_supervisor.container_coding import terminal_native_semantic_capsule as native_capsules
from benchmarks.agent_supervisor.container_coding import terminal_semantic_context_transport as transport
from benchmarks.agent_supervisor.container_coding import terminal_call_review_capacity as capacity
from benchmarks.agent_supervisor.container_coding import terminal_call_intent_profile as profiles
from benchmarks.agent_supervisor.container_coding import terminal_call_proof_capsule as capsules
from benchmarks.agent_supervisor.container_coding import terminal_semantic_context_budget as budgets
from benchmarks.agent_supervisor.container_coding import terminal_checked_worker_budget as worker_budget
from benchmarks.agent_supervisor.container_coding.native_quack_qualification import open_existing_native_owner
from ipfs_accelerate_py.agent_supervisor.entrypoints.admitted_benchmark_runtime import AdmittedBenchmarkRuntime
from ipfs_accelerate_py.agent_supervisor.runtime.checked_observer_budget import create_checked_observer_budget_scope
from ipfs_accelerate_py.agent_supervisor.runtime import checked_audit_context as checked
from ipfs_accelerate_py.agent_supervisor.runtime import native_dispatch_diagnostics as diagnostic
from ipfs_accelerate_py.agent_supervisor.runtime import model_input_observation_receipt as observations
from ipfs_accelerate_py.agent_supervisor.runtime import router_implementation_runner as native_runner
from ipfs_accelerate_py.agent_supervisor.runtime import local_planning_admission as local
from ipfs_accelerate_py.agent_supervisor.planning.plan_revision_contracts import PlanAuthorityRoots
from ipfs_accelerate_py.agent_supervisor.task_sources.task_execution_route_policy import GROK_CODEX_EXECUTION_MODE
from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead
from ipfs_datasets_py.logic.software_contracts.content import cid_for_structured

PUBLIC_NAMES = []
retained = []
RUNTIME = None
SCOPE = None
LIVE = None
CONNECTION = None
SCHEDULER = None


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode()


def save_bytes(name, raw):
    relative = Path(name)
    assert not relative.is_absolute() and ".." not in relative.parts and len(relative.parts) == 1
    path = PUBLIC / relative
    with path.open("xb") as stream:
        stream.write(raw)
    PUBLIC_NAMES.append(name)
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def save(name, value):
    return save_bytes(name, wire(value))


def guarded_bytes(path, limit=1048576):
    """Retain original nofollow file witnesses for the named proof/log exports."""
    path = Path(path)
    assert path.resolve(strict=True) == path
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    before = os.fstat(fd)
    sig = lambda info: tuple(getattr(info, key) for key in (
        "st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns"))
    try:
        assert stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and 0 <= before.st_size <= limit
        with os.fdopen(fd, "rb", closefd=False) as stream:
            raw = stream.read(limit + 1)
        assert len(raw) == before.st_size and sig(before) == sig(os.fstat(fd)) == sig(path.lstat())
        retained.append((path, fd, before, hashlib.sha256(raw).hexdigest(), sig, limit))
        return raw
    except BaseException:
        os.close(fd)
        raise


def recheck_retained():
    for path, fd, before, digest, sig, limit in retained:
        assert path.resolve(strict=True) == path and sig(before) == sig(os.fstat(fd)) == sig(path.lstat())
        os.lseek(fd, 0, os.SEEK_SET)
        with os.fdopen(fd, "rb", closefd=False) as stream:
            raw = stream.read(limit + 1)
        assert len(raw) == before.st_size and hashlib.sha256(raw).hexdigest() == digest
        assert sig(before) == sig(os.fstat(fd)) == sig(path.lstat())


def load(path):
    return json.loads(guarded_bytes(path, 4 * 1024 * 1024))


def git(*args):
    return subprocess.check_output(["git", "-C", str(REPOSITORY), *args], text=True, timeout=10).strip()


def task_projection(source, cid):
    task = source.get_task(cid)
    return {"task_cid": task.task_cid, "task_alias": task.task_alias,
            "status": task.status, "revision": task.revision}


def capture_observation(runtime, *, task_id, deadline):
    samples = []
    origin_ns, origin_cpu_ns = time.monotonic_ns(), time.process_time_ns()
    next_sample_ns = origin_ns

    def sample_progress():
        nonlocal next_sample_ns
        now_ns = time.monotonic_ns()
        if now_ns < next_sample_ns or len(samples) >= 32:
            return
        next_sample_ns = now_ns + 2000000000
        cpu_ns = time.process_time_ns()
        row = {"ordinal": len(samples), "monotonic_ns": now_ns,
            "elapsed_milliseconds": (now_ns - origin_ns) // 1000000,
            "owner_process_cpu_ns": cpu_ns, "owner_process_cpu_elapsed_ns": cpu_ns - origin_cpu_ns,
            "cpu_scope": "Aggregate original owner process CPU, including its threads; not broker-only CPU."}
        try:
            row["broker"] = runtime.checked_context_dispatch_broker.diagnostic_snapshot()
        except Exception as error:
            row["diagnostic_error_type"] = type(error).__name__
        samples.append(row)

    try:
        return _capture_observation(runtime, task_id=task_id, deadline=deadline, sample_progress=sample_progress)
    finally:
        primary_failure = sys.exc_info()[1]
        try:
            save("broker-progress-samples.json", {"schema": "admitted-budget-broker-progress-samples@1",
                "sample_interval_milliseconds": 2000, "sample_limit": 32, "samples": samples,
                "origin_monotonic_ns": origin_ns, "origin_owner_process_cpu_ns": origin_cpu_ns,
                "elapsed_milliseconds": (time.monotonic_ns() - origin_ns) // 1000000,
                "exported_on_observation_failure": primary_failure is not None,
                "diagnostic_only": True, "atomic_snapshot_claimed": False,
                "locking_getters_used": False, "current_verification_added": False,
                "deadline_extended": False, "proof_authority": False, "completion_authority": False})
        except BaseException as error:
            summary["progress_samples_export_error"] = {"type": type(error).__name__, "message": str(error)[:1024]}
            if primary_failure is None:
                raise


def _capture_observation(runtime, *, task_id, deadline, sample_progress):
    scope = runtime.manifest["native_dispatch_diagnostic_scope"]
    run = runtime.state / "run"
    while time.monotonic() < deadline:
        sample_progress()
        first_path = run / diagnostic.FIRST_PASS_NAME
        if not first_path.exists():
            time.sleep(0.25)
            continue
        # Preserve native failure evidence before interpreting or asserting it.
        first_raw = guarded_bytes(first_path, diagnostic.MAX_RECORD_BYTES)
        save_bytes("native-first-pass-raw.json", first_raw)
        decoded = json.loads(first_raw)
        save("native-first-pass.json", decoded)
        first = diagnostic.read_first_claimed_pass_diagnostic(run_root=run, expected_scope=scope)
        assert first is not None and wire(first) == wire(decoded)
        assert type(first["attempt_id"]) is str and first["attempt_id"]
        attempt_key = hashlib.sha256(first["attempt_id"].encode()).hexdigest()[:24]
        logs = run / "admitted_database_portal_attempts" / attempt_key / "implementation-logs"
        assert logs.resolve(strict=True) == logs and logs.is_dir()
        entries = []
        for entry in logs.iterdir():
            assert len(entries) < 32
            entries.append(entry)
        save("native-first-attempt-log-directory.json", {"attempt_id": first["attempt_id"],
            "directory": str(logs), "entry_names": sorted(entry.name for entry in entries),
            "directory_walk_scope": "Only bounded first actual attempt implementation-log directory."})
        pattern = re.compile(re.escape(task_id.lower()) + r"-attempt-1-[0-9a-f]{32}\.log")
        selected = [entry for entry in entries if entry.name.endswith(".log")]
        assert len(selected) == 1
        raw = guarded_bytes(selected[0], 1048576)
        save_bytes("native-implementation.log", raw)
        assert pattern.fullmatch(selected[0].name)
        assert first["active_task_id"] == task_id and first["claimed_task_cid"] == scope["task_cid"]
        assert type(first["sequence"]) is int and first["sequence"] == 1
        assert type(first["write_count"]) is int and first["write_count"] == 1
        if first["portal_implementation"]["returncode"] != 75:
            raise RuntimeError("native first implementation returned " + str(first["portal_implementation"]["returncode"])
                + "; expected observer-stop return75; original first-pass and implementation log retained")
        assert raw.endswith(b"\n")
        receipts = []
        for ordinal, line in enumerate(raw.decode("utf-8").splitlines()):
            assert ordinal < 8192 and len(line.encode()) <= 262144
            stripped = line.strip()
            if not stripped.startswith(("{", "[")):
                continue
            value = json.loads(stripped)
            assert type(value) is dict and type(value.get("schema")) is str
            assert value["schema"] in observations.SUPPORTED_SCHEMAS
            receipts.append(observations.validate_model_input_observation(value))
        assert len(receipts) == 1 and receipts[0]["schema"] == observations.CHECKED_SCHEMA
        assert receipts[0]["status"] == "observed"
        save("native-observation.json", receipts[0])
        return receipts[0]
    raise TimeoutError("native checked observer did not produce its single current-run receipt")


def bounded_diagnostic(callback):
    """Bound a public getter without extending the original owner deadline."""
    previous = signal.getitimer(signal.ITIMER_REAL)
    started = time.monotonic()
    signal.setitimer(signal.ITIMER_REAL, min(previous[0], 2.0) if previous[0] > 0 else 2.0)
    try:
        return callback()
    finally:
        remaining = max(0.000001, previous[0] - (time.monotonic() - started)) if previous[0] > 0 else 0
        signal.setitimer(signal.ITIMER_REAL, remaining, previous[1])


def snapshot_pending_attempt_logs(runtime, *, task_id):
    """Bounded diagnostic byte snapshots; changing/incomplete logs are data."""
    root = runtime.state / "run/admitted_database_portal_attempts"
    result = {"schema": "admitted-budget-pending-attempt-log-snapshot@1", "root": str(root),
        "attempts": [], "directory_limit": 8, "entries_per_log_directory_limit": 32,
        "log_file_limit": 8, "log_bytes_limit": 1048576, "proof_authority": False,
        "completion_authority": False, "snapshot_is_diagnostic_only": True,
        "complete_log_claimed": False, "database_bodies_opened": False, "errors": []}
    if not root.exists():
        result["root_present"] = False
        return result
    assert root.resolve(strict=True) == root and root.is_dir() and root.stat().st_uid == os.geteuid()
    entries = []
    for entry in root.iterdir():
        assert len(entries) < 8
        entries.append(entry)
    assert type(task_id) is str and 0 < len(task_id) <= 256
    pattern = re.compile(re.escape(task_id.lower()) + r"-attempt-1-[0-9a-f]{32}\.log")
    count = 0
    for attempt in sorted(entries):
        assert re.fullmatch(r"[0-9a-f]{24}", attempt.name) and not attempt.is_symlink()
        assert attempt.resolve(strict=True) == attempt and attempt.is_dir()
        row = {"directory": str(attempt), "logs": []}
        result["attempts"].append(row)
        logs = attempt / "implementation-logs"
        if not logs.exists():
            row["log_directory_present"] = False
            continue
        assert logs.resolve(strict=True) == logs and logs.is_dir() and not logs.is_symlink()
        names = []
        for entry in logs.iterdir():
            assert len(names) < 32
            names.append(entry)
        row["entry_names"] = sorted(entry.name for entry in names)
        for path in sorted(names):
            if not pattern.fullmatch(path.name):
                continue
            assert count < 8 and path.resolve(strict=True) == path
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            try:
                before = os.fstat(fd)
                assert stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_uid == os.geteuid()
                raw = os.pread(fd, 1048576, 0)
                after, final = os.fstat(fd), path.lstat()
                name = "pending-implementation-%02d.log" % count
                pin = save_bytes(name, raw)
                row["logs"].append({"container_source_path": str(path), "exported_snapshot": pin,
                    "source_size_before": before.st_size, "source_size_after": after.st_size,
                    "source_identity_retained_during_read": (before.st_dev, before.st_ino) ==
                        (after.st_dev, after.st_ino) == (final.st_dev, final.st_ino),
                    "stat_stable_during_read": all(getattr(before, key) == getattr(after, key) == getattr(final, key)
                        for key in ("st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns")),
                    "prefix_truncated": before.st_size > len(raw) or after.st_size > len(raw),
                    "ends_with_newline": raw.endswith(b"\n"), "complete_log_claimed": False})
                count += 1
            finally:
                os.close(fd)
    result["captured_log_count"] = count
    return result


def capture_pending_failure(runtime, errors, *, task_id):
    """Use public scope/broker APIs before STOP; no private object traversal."""
    broker = runtime.checked_context_dispatch_broker
    snapshot = None
    try:
        snapshot = bounded_diagnostic(broker.diagnostic_snapshot)
        save("broker-diagnostic-before-failure-cleanup.json", snapshot)
    except BaseException as error:
        errors.append({"phase": "public_broker_diagnostic", "type": type(error).__name__, "message": str(error)[:1024]})
    if type(snapshot) is dict and snapshot.get("pending") is False:
        if SCOPE is not None:
            capture_cleanup_json("failure-native-dispatch-prepared-record.json",
                lambda: bounded_diagnostic(lambda: SCOPE.prepared_record), errors)
        capture_cleanup_json("broker-observations-before-failure-cleanup.json",
            lambda: bounded_diagnostic(lambda: broker.observations), errors)
    else:
        save("failure-locked-getters-skipped.json", {"broker_pending": snapshot.get("pending") if type(snapshot) is dict else None,
            "prepared_record_getter_called": False, "observations_getter_called": False,
            "unavailable_data_while_pending": True,
            "reason": "No lock-bearing getter while broker reports pending or diagnostic status is unavailable.",
            "proof_authority": False, "completion_authority": False})
    capture_cleanup_json("pending-attempt-log-snapshots.json",
        lambda: bounded_diagnostic(lambda: snapshot_pending_attempt_logs(runtime, task_id=task_id)), errors)
    save("failure-diagnostic-capture-timing.json", {"monotonic_ns": time.monotonic_ns(),
        "elapsed_milliseconds": (time.monotonic_ns() - started_ns) // 1000000,
        "remaining_owner_alarm_milliseconds": int(signal.getitimer(signal.ITIMER_REAL)[0] * 1000),
        "overall_owner_limit_seconds": 180, "capacity_limit_seconds": 120,
        "deadline_extended": False, "proof_authority": False})


def capture_runtime_receipts(runtime, errors):
    """Retain only exact native receipt names, including partial close success."""
    for source_name, public_name in (
        ("start-receipt.json", "native-START-raw.json"),
        ("stop-receipt.json", "native-STOP-raw.json"),
        ("worker-stop-receipt.json", "native-worker-stop-raw.json"),
        ("native-lifecycle-receipt.json", "native-lifecycle-last-raw.json"),
        ("child-bootstrap-receipt.json", "native-child-bootstrap-last-raw.json"),
        ("checked-context-dispatch-broker-close-receipt.json", "checked-context-dispatch-broker-close-receipt.json"),
        ("checked-observer-budget-close-receipt.json", "checked-observer-budget-close-receipt.json"),
    ):
        try:
            path = runtime.state / source_name
            if public_name not in PUBLIC_NAMES and path.exists():
                save_bytes(public_name, guarded_bytes(path))
        except BaseException as error:
            errors.append({"phase": "native_receipt_export", "name": source_name,
                           "type": type(error).__name__, "message": str(error)[:1024]})


def capture_cleanup_json(name, callback, errors):
    try:
        if name not in PUBLIC_NAMES:
            save(name, callback())
    except BaseException as error:
        errors.append({"phase": "public_cleanup_export", "name": name,
                       "type": type(error).__name__, "message": str(error)[:1024]})


def save_failure_trace(name, error):
    raw = "".join(traceback.format_exception(type(error), error, error.__traceback__, limit=32)).encode()
    # Public authored fixture and selected code only; no locals or environment.
    save_bytes(name, raw[:65536])


started_ns = time.monotonic_ns()
summary = {"schema": "admitted-budget-actual-START-experiment@1", "qualified": False,
    "provider_calls": 0, "training_steps": 0, "source_body_executed": False,
    "new_prover_invocations_in_START_owner": 0, "full_supervisor_entrypoint_used": False,
    "Terminal_Bench_harness_used": False, "global_task_budget_enforced": False,
    "durable_budget_resume_supported": False, "source_to_model_equivalence_proved": False,
    "convergence_proved": False, "full_task_satisfaction": False,
    "proof_authority": False, "completion_authority": False,
    "actual_native_START_calls": 0,
    "original_owner_budget_committed": False,
    "provider_billing_savings_measured": False, "native_admitted_benchmark_runtime_START_used": False}


def deadline_expired(_signal, _frame):
    signal.setitimer(signal.ITIMER_REAL, 0)
    raise TimeoutError("bounded AA owner observation deadline expired")


signal.signal(signal.SIGALRM, deadline_expired)
signal.setitimer(signal.ITIMER_REAL, 180)
try:
    producer_names = [
        "ipfs_accelerate_py/agent_supervisor/runtime/checked_observer_budget.py",
        "ipfs_accelerate_py/agent_supervisor/runtime/checked_context_dispatch.py",
        "ipfs_accelerate_py/agent_supervisor/entrypoints/admitted_benchmark_runtime.py",
        "ipfs_accelerate_py/agent_supervisor/runtime/router_implementation_runner.py",
        "ipfs_accelerate_py/agent_supervisor/runtime/model_input_observation_receipt.py",
        "benchmarks/agent_supervisor/container_coding/container_worker_deployment.py",
        "ipfs_accelerate_py/agent_supervisor/todo_daemon/supervisor_runtime.py",
        "ipfs_accelerate_py/agent_supervisor/todo_daemon/implementation_daemon.py",
        "benchmarks/agent_supervisor/container_coding/terminal_checked_worker_budget.py",
    ]
    producer_pins = []
    for name in producer_names:
        path = ROOT / "source" / name
        raw = guarded_bytes(path, 8 * 1024 * 1024)
        info = path.lstat()
        assert info.st_uid == 0 and not info.st_mode & 0o022
        producer_pins.append({"path": str(path), "relative_path": name, "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(), "uid": info.st_uid, "mode": oct(stat.S_IMODE(info.st_mode))})
    save("container-producer-pins.json", {"files": producer_pins,
        "root_protected_declared_sources": True, "loaded_module_code_attested": False,
        "transitive_dependency_closure_attested": False})
    prepared = load(MODEL / "prepared.json")
    model = load(MODEL / "model/result.json")
    callee = load(Path(model["callee"]["native_proof"]["path"]))
    native_owner = load(FIXTURE / "owner-receipt.json")
    admission = load(FIXTURE / "admission.json")
    bundle = load(FIXTURE / "context-bundle.json")
    verified = local.verify_local_benchmark_admission(admission, initial=True)
    task = verified["graph"].tasks[0]
    assert task.task_cid == native_owner["task_cid"] and len(verified["graph"].tasks) == 1
    boundary_path = ROOT / "container-boundary.json"
    boundary_raw = guarded_bytes(boundary_path)
    boundary_record = json.loads(boundary_raw)
    boundary = {key: boundary_record[key] for key in ("schema", "container_id", "image_id", "namespaces", "owner_uid", "worker_uid")}
    boundary.update(purpose="coding", manifest_sha256=hashlib.sha256(boundary_raw).hexdigest(), completion_authority=False)
    assert boundary["owner_uid"] == os.getuid() == 1000 and boundary["worker_uid"] == 1001
    head = CodebaseHead.from_dict(prepared["head"])
    SCHEDULER = _scheduler(MODEL / "resources.json")
    CONNECTION, index = _open(MODEL)
    cold = validate_current_call_composition(expected=model, index=index, repository=REPOSITORY,
        expected_head=head, tool_policy=prepared["tool_policy"], scheduler=SCHEDULER)
    save("native-cold-model-validation.json", cold)
    prompt = "Under closed-caller-model@1, caller.py::twice(n) must return n + 2."
    profile = profiles.build_call_intent_profile(prompt=prompt)
    save("intent-profile.json", profile)
    policy = {name: {"schema": "authored-call-review-policy@1", "role": name,
        "production_activated": False, "worker_allowed": False, "model_calls": 0,
        "training_allowed": False, "mutation_authority": False}
        for name in ("policy", "legal", "security", "provider", "usage")}
    policy["configuration"] = capacity.capacity_configuration_profile()
    policy["catalog"] = {"schema": "authored-call-review-catalog@1",
        "operations": [list(row) for row in planning.previous.OPERATIONS],
        "scope": "conditional evidence review only; native START uses its independent signed admission",
        "completion_authority": False, "mutation_authority": False}
    save("policy.json", policy)
    query = capsules.query_call_capsule_rows(output=MODEL / "model/metadata",
        expected_metadata=model["metadata"], expected_head=head.to_dict())
    save("query.json", query)
    basis = dict(prompt=prompt, intent_profile=profile, model_record=model, query=query, callee_proof=callee)
    save("checked-call-capsule.json", capsules.build_call_proof_capsule(**basis))
    observations_policy = []

    def policy_observer(_request):
        recheck_retained()
        observed = index.observe_current(REPOSITORY, expected_head=head, scheduler=SCHEDULER)
        catalog = cid_for_structured(policy["catalog"])
        intent_root = planning.previous.intent_root(profile)
        role = lambda name: cid_for_structured(policy[name])
        roots = PlanAuthorityRoots(repository_id=head.repository_id, repository_root_cid=head.snapshot_cid,
            dirty_worktree_root=head.snapshot_cid,
            task_source_id=cid_for_structured({"intent": intent_root, "catalog": catalog}),
            task_source_revision=catalog, policy_root=role("policy"), intent_ir_root=intent_root,
            legal_ir_root=role("legal"), security_ir_root=role("security"),
            program_root=observed.manifest.semantic_state.state_cid, capability_catalog_root=catalog,
            provider_catalog_root=role("provider"), usage_policy_root=role("usage"), configuration_root=role("configuration"))
        observations_policy.append(roots.to_dict())
        return roots

    roots = policy_observer(None)
    observed = index.observe_current(REPOSITORY, expected_head=head, scheduler=SCHEDULER)
    manifest = observed.manifest
    native_set = native_capsules.build_native_semantic_capsule_set(manifest=manifest, expected_head=head)
    sources = {path: (REPOSITORY / path).read_bytes() for path in model["paths"]}
    code_views = transport.build_bound_code_views(sources=sources, head=head.to_dict())
    request, materials, binding = semantic.build_semantic_call_review_basis(manifest=manifest,
        expected_head=head, native_capsules=native_set, code_views=code_views, sources=sources,
        repository=REPOSITORY, policy_roots=roots, **basis)
    save("observed-manifest.json", manifest.to_dict())
    save("native-semantic-capsules.json", native_set)
    save("code-views.json", code_views)
    save("pre-capacity-binding.json", binding)
    original_commit, original_tree = git("rev-parse", "HEAD"), git("rev-parse", "HEAD^{tree}")
    public_instruction = native_owner["public_instruction"]
    # Native Quack/signing setup is complete before the bounded review capacity starts.
    with open_existing_native_owner(database=Path(native_owner["database"]), checkout=REPOSITORY,
            state_dir=OUT / "owner", repository_id=verified["manifest"]["repository_cid"],
            execution_routes={task.task_key: GROK_CODEX_EXECUTION_MODE},
            store_id="admitted-context-budget-aa18") as owner:
        save("native-task-before.json", task_projection(owner.source, task.task_cid))
        with capacity.reserve_call_review_capacity(scheduler=SCHEDULER, binding=binding, timeout_seconds=120) as control:
            packet = audit_review.build_semantic_audit_context_packet(representation="view", capacity_control=control,
                native_capsules=native_set, code_views=code_views, manifest=manifest,
                expected_head=head, sources=sources, **basis)
            save_bytes("view-packet.json", packet.encode())
            view = json.loads(packet)["payload"]["model_view"]
            save("audit-view.json", view)
            budget_binding = budgets.build_context_budget_binding(head=head, view_id=view["view_id"],
                reference_basis_cid=view["expansion_directory"]["reference_basis_cid"],
                native_root_cid=view["native_root_cid"], capsule_set_id=view["capsule_set_id"], state_cid=view["state_cid"])
            budget_policy = budgets.ContextBudgetPolicy(max_rendered_input_tokens=100000, max_new_content_tokens=100000,
                max_rendered_input_bytes=1000000, max_new_content_bytes=1000000,
                max_model_calls=2, max_expansion_calls=0, max_retry_calls=1, max_events=2, max_payload_bytes=256000)
            LIVE = budgets.create_semantic_context_budget(binding=budget_binding, policy=budget_policy)
            save("budget-binding.json", budget_binding)
            save("budget-policy.json", budget_policy.to_dict())
            save("initial-budget-state.json", LIVE.snapshot())
            SCOPE = create_checked_observer_budget_scope(budget_owner=LIVE, context_packet=packet,
                admission=admission, public_instruction=public_instruction, boundary=boundary,
                index=index, repository=REPOSITORY, expected_head=head, native_capsules=native_set,
                code_views=code_views, tool_policy=prepared["tool_policy"], policy_roots=roots,
                policy_observer=policy_observer, scheduler=SCHEDULER, capacity_control=control, basis=basis)
            save("owner-scope-material.json", SCOPE.material_binding)
            command = ["/opt/ipfs-supervisor/bin/router-worker", "--model", "authored-offline-observer",
                "--reasoning-effort", "high", "--timeout", "30", "--max-output-tokens", "128",
                "--purpose", "coding", "--semantic-repository", str(REPOSITORY), "--semantic-transport", "native",
                "--intent-requirements-transport", "expanded", "--code-retrieval-codec", "expanded",
                "--code-retrieval-wire-delivery", "inline", "--public-instruction-artifact", public_instruction["artifact"],
                "--public-instruction-sha256", public_instruction["sha256"], "--public-instruction-task-cid", task.task_cid,
                "--checked-context-owner-scope-cid", SCOPE.context_cid, "--observe-model-input-only"]
            import shlex
            runtime_created = False
            try:
                RUNTIME = AdmittedBenchmarkRuntime.create(OUT / "launch", admission=admission,
                    server=owner.server, source=owner.source, implement=True,
                    implementation_command=shlex.join(command), context_bundle=bundle,
                    max_task_attempts=1, timeout_ms=20000, lifetime_seconds=300,
                    worker_worktree_root=WORKTREES, candidate_runner_argv=("/opt/ipfs-supervisor/bin/validation-worker",),
                    native_dispatch_diagnostics=True, checked_observer_budget_scope=SCOPE)
                runtime_created = True
                save("native-launch-manifest.json", RUNTIME.manifest)
                save("native-launch-signature.json", RUNTIME.signature)
                summary["native_admitted_benchmark_runtime_START_used"] = True
                summary["actual_native_START_calls"] = 1
                start = RUNTIME.start().to_dict()
                save("native-START.json", start)
                save_bytes("native-START-raw.json", guarded_bytes(RUNTIME.state / "start-receipt.json"))
                assert start["status"] == "succeeded"
                receipt = capture_observation(RUNTIME, task_id=task.task_key, deadline=time.monotonic() + 60)
                summary["actual_native_worker_observer_invocations"] = 1
                assert receipt["requested_model"] == "authored-offline-observer"
                assert receipt["timeout_seconds"] == 30 and receipt["requested_output_tokens"] == 128
                commit = SCOPE.commit_observation(receipt)
                save("native-budget-commit.json", commit)
                record = SCOPE.prepared_record
                save("native-dispatch-prepared-record.json", record)
                preparation = record["preparation"]
                save("native-budget-preparation.json", preparation)
                save("native-checked-inclusion.json", record["preflight"])
                save("native-checked-descriptor.json", record["descriptor"])
                save("native-semantic-verification.json", record["verification"])
                actual_basis = preparation["basis"]
                save_bytes("native-emitted-prompt.txt", actual_basis["native_prompt"].encode())
                save_bytes("native-complete-input.txt", preparation["event"]["rendered_input"]["text"].encode())
                save_bytes("checked-context-public-artifact.json", guarded_bytes(Path(record["descriptor"]["artifact"]), 2 * 1024 * 1024))
                save_bytes("public-instruction-artifact.json", guarded_bytes(Path(public_instruction["artifact"])))
                rendered, advisory = native_runner.render_model_prompt(prompt=actual_basis["router_prompt"] + actual_basis["checked_suffix"],
                    purpose="coding", workspace=Path(actual_basis["worker_workspace"]), semantic_transport=False, code_retrieval_projected=False)
                assert rendered == preparation["event"]["rendered_input"]["text"]
                assert hashlib.sha256(rendered.encode()).hexdigest() == receipt["model_prompt_sha256"]
                assert len(rendered.encode()) == receipt["model_prompt_bytes"]
                save("native-exact-input-replay.json", {"passed": True, "model_prompt_sha256": receipt["model_prompt_sha256"],
                    "model_prompt_bytes": receipt["model_prompt_bytes"], "workspace_advisory_bytes": len(advisory.encode()),
                    "actual_native_stdin_used": True, "manual_fixture_native_prompt_used": False,
                    "provider_calls": 0, "source_body_executed": False})
                assert LIVE.snapshot()["totals"]["events"] == 1
                controls = []
                if preparation["event"]["rendered_input"]["tokens"] > 50000:
                    retry = worker_budget.prepare_checked_worker_budget_event(budget_owner=LIVE,
                        event_id="checked-observer:pure-retry-control", kind="retry", retry_of="checked-observer:initial",
                        native_prompt=actual_basis["native_prompt"], worker_workspace=Path(actual_basis["worker_workspace"]),
                        router_prompt=actual_basis["router_prompt"], checked_suffix=actual_basis["checked_suffix"], task_cid=task.task_cid,
                        instruction_receipt=actual_basis["instruction_receipt"], boundary=boundary, boundary_sha256=boundary["manifest_sha256"])
                    before = LIVE.snapshot()
                    try:
                        ticket = LIVE.reserve(retry["event"])
                    except budgets.SemanticContextBudgetExceeded as error:
                        controls.append({"name": "pure-cumulative-retry-preflight", "rejected": True,
                            "error_type": type(error).__name__, "reason": str(error), "native_START_calls": 0,
                            "worker_callbacks": 0, "scope_dispatch_retry_attempted": False})
                    else:
                        ticket.abort()
                        raise AssertionError("cumulative retry control unexpectedly admitted")
                    assert LIVE.snapshot() == before
                else:
                    controls.append({"name": "pure-cumulative-retry-preflight", "exercised": False,
                        "reason": "actual first input does not exceed half of100k allowance; no failed-budget claim"})
                save("controls.json", controls)
                broker = RUNTIME.checked_context_dispatch_broker
                save("broker-observations-before-STOP.json", broker.observations)
                assert broker.wrapper_birth_observed is True and broker.worker_birth_observed is True
                assert broker.ambiguous_birth_possible is False
                assert len(RUNTIME.bootstrap_receipts) == 1 and not RUNTIME.bootstrap_errors
                summary.update(whole_coding_input={key: preparation["event"]["rendered_input"][key] for key in ("sha256", "bytes", "tokens")},
                    new_content={key: preparation["event"]["new_content"][key] for key in ("sha256", "bytes", "tokens")},
                    actual_native_worker_observer_invocations=1, original_owner_budget_committed=True,
                    native_kernel_wrapper_and_worker_births_verified=True, head=head.to_dict(),
                    context_cid=SCOPE.context_cid, controls=controls)
                summary["qualified"] = True
            finally:
                primary_failure = sys.exc_info()[1]
                cleanup = {"native_runtime_created": runtime_created, "STOP_called": False, "closed": False}
                if primary_failure is not None:
                    cleanup["primary_failure"] = {"type": type(primary_failure).__name__, "message": str(primary_failure)[:1024]}
                cleanup_errors = []
                if primary_failure is not None:
                    try:
                        save_failure_trace("native-operation-failure-traceback.txt", primary_failure)
                    except BaseException as error:
                        cleanup_errors.append({"phase": "primary_failure_trace_export", "type": type(error).__name__,
                                               "message": str(error)[:1024]})
                    if RUNTIME is not None:
                        capture_pending_failure(RUNTIME, cleanup_errors, task_id=task.task_key)
                if LIVE is not None:
                    capture_cleanup_json("budget-state-before-native-cleanup.json", LIVE.snapshot, cleanup_errors)
                if RUNTIME is not None:
                    try:
                        stop = RUNTIME.stop().to_dict()
                        save("native-STOP.json", stop)
                        save_bytes("native-STOP-raw.json", guarded_bytes(RUNTIME.state / "stop-receipt.json"))
                        cleanup.update(STOP_called=True, stop=stop,
                            remaining_owner_processes=len(RUNTIME.process.snapshot(RUNTIME.profile).members))
                        assert stop["status"] == "succeeded" and stop["data"]["old_tree_fenced"] is True
                        assert stop["data"]["isolated_worker_cleanup"]["returncode"] == 0
                        assert cleanup["remaining_owner_processes"] == 0
                    except BaseException as error:
                        cleanup_errors.append({"phase": "native_STOP", "type": type(error).__name__, "message": str(error)[:1024]})
                    finally:
                        capture_cleanup_json("native-bootstrap-receipts.json", lambda: RUNTIME.bootstrap_receipts, cleanup_errors)
                        capture_cleanup_json("native-bootstrap-errors.json", lambda: RUNTIME.bootstrap_errors, cleanup_errors)
                        capture_cleanup_json("broker-observations-after-STOP.json",
                            lambda: RUNTIME.checked_context_dispatch_broker.observations, cleanup_errors)
                        try:
                            fallback = subprocess.run(["/usr/bin/sudo", "-n", "-u", "benchmarkworker", "--",
                                "/opt/ipfs-supervisor/bin/worker-entry", "--cleanup"], cwd="/",
                                stdin=subprocess.DEVNULL, capture_output=True, timeout=15)
                            save_bytes("final-worker-cleanup.stdout", fallback.stdout)
                            save_bytes("final-worker-cleanup.stderr", fallback.stderr)
                            cleanup["final_worker_cleanup_returncode"] = fallback.returncode
                            assert fallback.returncode == 0
                        except BaseException as error:
                            cleanup_errors.append({"phase": "worker_cleanup", "type": type(error).__name__, "message": str(error)[:1024]})
                        try:
                            RUNTIME.close()
                            cleanup["closed"] = True
                        except BaseException as error:
                            cleanup_errors.append({"phase": "runtime_close", "type": type(error).__name__, "message": str(error)[:1024]})
                        finally:
                            capture_runtime_receipts(RUNTIME, cleanup_errors)
                            capture_cleanup_json("broker-observations-after-close.json",
                                lambda: RUNTIME.checked_context_dispatch_broker.observations, cleanup_errors)
                elif SCOPE is not None:
                    # Constructor rollback may already have closed the scope.
                    # A genuinely unbound scope has its separate no-birth close.
                    try:
                        if not SCOPE.is_closed:
                            bound = SCOPE.bound_runtime
                            cleanup["unlaunched_scope_close"] = SCOPE.close_unlaunched_construction(bound)
                    except BaseException as error:
                        cleanup_errors.append({"phase": "unlaunched_scope_close", "type": type(error).__name__, "message": str(error)[:1024]})
                cleanup["errors"] = cleanup_errors
                save("native-cleanup.json", cleanup)
                if LIVE is not None:
                    save("budget-state-after-native-cleanup.json", LIVE.snapshot())
                if cleanup_errors:
                    summary["qualified"] = False
                    if primary_failure is None:
                        raise RuntimeError("native cleanup failed; see retained native-cleanup.json")
        after = task_projection(owner.source, task.task_cid)
        save("native-task-after.json", after)
        assert after["status"] not in {"completed", "done", "skipped"}
    assert git("rev-parse", "HEAD") == original_commit and git("rev-parse", "HEAD^{tree}") == original_tree
    for path, raw in sources.items():
        assert (REPOSITORY / path).read_bytes() == raw
    assert index.current(head.repository_id) == head
    recheck_retained()
    save("current-source-after.json", {"git_commit": original_commit, "git_tree": original_tree,
        "head": head.to_dict(), "source_unchanged": True, "task_completed": False})
    summary["resources_after"] = SCHEDULER.snapshot()
    assert summary["resources_after"]["active_lease_count"] == summary["resources_after"]["waiting_request_count"] == 0
    save("policy-observations.json", observations_policy)
except BaseException as error:
    signal.setitimer(signal.ITIMER_REAL, 0)
    summary["qualified"] = False
    summary["failure"] = {"type": type(error).__name__, "message": str(error)[:2048]}
    try:
        save_failure_trace("owner-failure-traceback.txt", error)
    except BaseException as trace_error:
        summary["failure_trace_export_error"] = {"type": type(trace_error).__name__, "message": str(trace_error)[:1024]}
finally:
    signal.setitimer(signal.ITIMER_REAL, 0)
    # The actual container itself is disposed by the host after public evidence export.
    outer_cleanup = {"scope_closed": SCOPE is None, "original_budget_closed": LIVE is None, "errors": []}
    if SCOPE is not None:
        try:
            if not SCOPE.is_closed:
                bound = SCOPE.bound_runtime
                if bound is None:
                    outer_cleanup["scope_close"] = SCOPE.close_unlaunched_construction()
                elif RUNTIME is None:
                    outer_cleanup["scope_close"] = SCOPE.close_unlaunched_construction(bound)
                else:
                    # This original API independently requires its genuine STOP fence.
                    outer_cleanup["scope_close"] = SCOPE.close_after_native_stop(RUNTIME)
            outer_cleanup["scope_closed"] = SCOPE.is_closed is True
        except BaseException as error:
            outer_cleanup["errors"].append({"phase": "scope_close", "type": type(error).__name__, "message": str(error)[:1024]})
    if LIVE is not None:
        try:
            LIVE.close()
            outer_cleanup["original_budget_closed"] = LIVE.snapshot()["closed"] is True
        except BaseException as error:
            outer_cleanup["errors"].append({"phase": "original_budget_close", "type": type(error).__name__, "message": str(error)[:1024]})
        try:
            save("final-budget-state.json", LIVE.snapshot())
        except BaseException as error:
            outer_cleanup["errors"].append({"phase": "final_budget_export", "type": type(error).__name__, "message": str(error)[:1024]})
    if outer_cleanup["errors"] or not outer_cleanup["scope_closed"] or not outer_cleanup["original_budget_closed"]:
        summary["qualified"] = False
        summary["owner_cleanup_failed"] = True
    save("outer-owner-cleanup.json", outer_cleanup)
    if CONNECTION is not None:
        CONNECTION.close()
    for _, fd, _, _, _, _ in retained:
        os.close(fd)
    summary["elapsed_milliseconds"] = (time.monotonic_ns() - started_ns) // 1000000
    summary["public_files"] = list(PUBLIC_NAMES) + ["summary.json"]
    save("summary.json", summary)
    print(json.dumps({"qualified": summary["qualified"], "public_directory": str(PUBLIC),
        "public_files": summary["public_files"], "failure": summary.get("failure")}), flush=True)

raise SystemExit(0 if summary["qualified"] else 1)
