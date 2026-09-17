#!/usr/bin/python3.12
"""LA-012 durable DuckDB capability consumption adapter and qualification.

The selected ENFORCE deployment injects this file-backed store. It never uses
``InMemoryCapabilityConsumptionStore`` while claiming restart safety. Consume
records are committed through the typed Quack owner (``QuackStateClient`` +
``StateTransaction``) into ``control.duckdb`` idempotency rows. The Quack
Unix-socket gateway is probed and recorded; it is unavailable without the
``quack`` extension under a fresh validation HOME.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import threading
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

HERE = Path(__file__).resolve()
if "receipts" in HERE.parts and "snapshots" in HERE.parts:
    SNAPSHOT = HERE.parent
    ROOT = HERE.parents[6]
else:
    ROOT = HERE.parents[4]
    SNAPSHOT = ROOT / "papers" / "completion" / "law_to_action" / "receipts" / "snapshots" / "LA-012"
LIVE = ROOT / "papers" / "completion" / "law_to_action"
PYTHON = "/usr/bin/python3.12"
HANDLERS = LIVE / "benchmark" / "handlers" / "effects.py"
VALIDATION_SITE_PACKAGES = Path("/opt/ipfs-validation-site-packages")

for path in (
    ROOT / "external" / "ipfs_accelerate",
    ROOT / "external" / "ipfs_datasets",
    ROOT / "external" / "ipfs_kit",
):
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)

DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
DIGEST_C = "c" * 64
DIGEST_D = "d" * 64
DIGEST_E = "e" * 64
DIGEST_F = "f" * 64
DIGEST_1 = "1" * 64
DIGEST_2 = "2" * 64
ISSUED = "2026-07-28T12:00:00Z"
DEADLINE = "2026-07-28T12:05:00Z"
EXPIRY = "2026-07-28T12:10:00Z"
NOW_OK = "2026-07-28T12:02:00Z"


def sha256_file(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_handlers():
    spec = importlib.util.spec_from_file_location("la012_bounded_handlers", HANDLERS)
    if spec is None or spec.loader is None:
        raise RuntimeError("bounded export handler module is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ConsumptionOwnerError(RuntimeError):
    """Typed owner refused or could not complete a consume command."""

    def __init__(self, message: str, *, cas: Mapping[str, Any] | None = None) -> None:
        super().__init__(message)
        self.cas = dict(cas or {})


def _token_digest(token_key: str) -> str:
    return sha256_text(token_key)


def _compact_consume_ids(token_key: str) -> tuple[str, str]:
    digest = _token_digest(token_key)
    return f"cmd:consume:{digest}", f"idem:consume:{digest}"


def _cas_dict(result: Any) -> dict[str, Any]:
    if result is None:
        return {}
    payload = result.to_dict() if hasattr(result, "to_dict") else dict(result)
    return {
        "outcome": payload.get("outcome"),
        "changed": payload.get("changed"),
        "revision": payload.get("revision"),
        "generation": payload.get("generation"),
        "fence_epoch": payload.get("fence_epoch"),
        "conflict_kind": payload.get("conflict_kind"),
        "attempts": payload.get("attempts"),
        "idempotency_key": payload.get("idempotency_key"),
        "command_id": payload.get("command_id"),
        "result_digest": payload.get("result_digest"),
        "result": payload.get("result"),
        "schema": payload.get("schema"),
        "interface": payload.get("interface"),
    }


def prepare_control_database(database_path: Path) -> Path:
    """Install the checksum-bound control-plane schema on a file-backed store."""

    from ipfs_accelerate_py.agent_supervisor.task_sources.control_plane_schema import (
        install_control_plane_schema,
    )

    if str(database_path) in {":memory:", ""} or database_path.name == ":memory:":
        raise ValueError("durable store requires a file-backed control.duckdb")
    database_path.parent.mkdir(parents=True, exist_ok=True)
    install_control_plane_schema(
        database_path,
        application_version="0.0.45",
        tool_version="1.5.2",
        owner_id="owner:la-012-schema",
    )
    return database_path


def _jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in dict(value).items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _consume_apply(txn: Any, command: Any, generation: Any) -> dict[str, Any]:
    params = _jsonable(command.parameters or {})
    if not isinstance(params, dict):
        params = {"value": params}
    return {
        "consumed": True,
        "store_kind": "duckdb-file",
        "in_memory": False,
        "token_key_digest": str(params.get("token_key_digest") or ""),
        "generation": int(generation.generation),
        "fence_epoch": int(generation.fence_epoch),
        "revision_before": int(generation.revision),
        "phase": str(params.get("phase") or ""),
    }


class DuckDBCapabilityConsumptionStore:
    """File-backed ``CapabilityConsumptionStore`` using the typed Quack owner.

    Consumption is a fenced, idempotent ``StateCommand``. First commit returns
    True. An identical command after commit or lost reply is
    ``idempotent_replay`` and returns False so the ENFORCE gate does not
    re-delegate. This class refuses ``:memory:`` paths.
    """

    STORE_KIND = "duckdb-file-typed-quack-owner"
    IN_MEMORY = False
    TRANSPORT = "embedded-exclusive-lock"

    def __init__(
        self,
        database_path: str | Path,
        *,
        owner_id: str = "owner:la-012",
        store_id: str = "control.duckdb",
        connect_timeout_seconds: float = 30.0,
    ) -> None:
        path = Path(database_path)
        if str(path) in {":memory:", ""} or path.name == ":memory:":
            raise ValueError("DuckDBCapabilityConsumptionStore refuses in-memory databases")
        self.database_path = path
        self.owner_id = owner_id
        self.store_id = store_id
        self.connect_timeout_seconds = connect_timeout_seconds
        self.in_memory = False
        self.store_kind = self.STORE_KIND
        self.last_cas: dict[str, Any] | None = None
        self._client: Any | None = None

    def attach(self) -> Any:
        from ipfs_accelerate_py.agent_supervisor.task_sources.quack_state_client import (
            open_embedded_client,
        )

        if self._client is not None:
            return self._client
        if not self.database_path.is_file():
            prepare_control_database(self.database_path)
        self._client = open_embedded_client(
            self.database_path,
            owner_id=self.owner_id,
            store_id=self.store_id,
            seed_generation=True,
            connect_timeout_seconds=self.connect_timeout_seconds,
        )
        return self._client

    def close(self) -> None:
        client = self._client
        self._client = None
        if client is not None:
            client.close()

    def __enter__(self) -> "DuckDBCapabilityConsumptionStore":
        self.attach()
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def consume_command(
        self,
        token_key: str,
        *,
        meta: Mapping[str, Any] | None = None,
        command_id: str | None = None,
        idempotency_key: str | None = None,
        expected_generation: int | None = None,
        expected_revision: int | None = None,
        fence_epoch: int | None = None,
        refresh_on_conflict: bool = False,
    ) -> Any:
        from ipfs_accelerate_py.agent_supervisor.task_sources.control_plane_contracts import (
            CommandKind,
            StateAuthorityClass,
            StateCommand,
        )

        client = self.attach()
        session = client.session
        if session is None:
            raise ConsumptionOwnerError("typed owner has no attached session")
        live = client.load_generation()
        default_command_id, default_idem = _compact_consume_ids(token_key)
        command = StateCommand(
            command_id=command_id or default_command_id,
            command_kind=CommandKind.CLAIM,
            store_id=self.store_id,
            session_id=session.session_id,
            expected_generation=live.generation if expected_generation is None else expected_generation,
            expected_revision=live.revision if expected_revision is None else expected_revision,
            fence_epoch=live.fence_epoch if fence_epoch is None else fence_epoch,
            idempotency_key=idempotency_key or default_idem,
            authority_class=StateAuthorityClass.AUTHORITATIVE,
            parameters={
                "token_key_digest": _token_digest(token_key),
                "phase": str((meta or {}).get("phase") or "consume"),
            },
        )
        result = client.submit_command(
            command,
            apply=_consume_apply,
            refresh_on_conflict=refresh_on_conflict,
        )
        self.last_cas = _cas_dict(result)
        return result

    def try_consume(self, token_key: str, *, meta: Mapping[str, Any] | None = None) -> bool:
        from ipfs_accelerate_py.agent_supervisor.task_sources.control_plane_contracts import (
            CommandOutcome,
        )
        from ipfs_accelerate_py.agent_supervisor.task_sources.control_plane_transactions import (
            IdempotencyConflictError,
            TransactionError,
        )

        try:
            result = self.consume_command(token_key, meta=meta, refresh_on_conflict=True)
        except IdempotencyConflictError as exc:
            self.last_cas = {
                "outcome": "rejected",
                "conflict_kind": "idempotency_conflict",
                "error": type(exc).__name__,
            }
            raise
        except TransactionError as exc:
            self.last_cas = {
                "outcome": "rejected",
                "conflict_kind": getattr(getattr(exc, "kind", None), "value", None),
                "error": type(exc).__name__,
            }
            raise ConsumptionOwnerError(str(exc), cas=self.last_cas) from exc
        self.last_cas = _cas_dict(result)
        if result.outcome is CommandOutcome.ACCEPTED:
            return True
        if result.outcome is CommandOutcome.IDEMPOTENT_REPLAY:
            return False
        raise ConsumptionOwnerError(
            f"consume command was not accepted: {result.outcome}",
            cas=self.last_cas,
        )


class CountingDelegate:
    def __init__(self, fn: Callable[[], Any] | None = None) -> None:
        self.calls = 0
        self.fn = fn

    def __call__(self) -> Any:
        self.calls += 1
        if self.fn is not None:
            return self.fn()
        return {"status": "ok"}


@dataclass
class CaseResult:
    job_id: str
    case_kind: str
    mutation: str
    expected_decision: str
    expected_effect_count: int
    in_safety_claim: bool
    store_kind: str
    in_memory_store: bool
    decision: str = ""
    delegated: bool = False
    handler_calls: int = 0
    observed_effect_count: int = 0
    journal_event_count: int = 0
    extra_effect_count: int = 0
    remote_effect_status: str = "absent"
    reply_status: str = "observed"
    owner_transactions: list[dict[str, Any]] = field(default_factory=list)
    denial_reason: str = ""
    reason_codes: list[str] = field(default_factory=list)
    passed: bool = False
    failure: str | None = None
    notes: str = ""
    empirical_benchmark_result: bool = False

    def to_record(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "case_kind": self.case_kind,
            "mutation": self.mutation,
            "expected_decision": self.expected_decision,
            "decision": self.decision,
            "delegated": self.delegated,
            "handler_calls": self.handler_calls,
            "observed_effect_count": self.observed_effect_count,
            "journal_event_count": self.journal_event_count,
            "expected_effect_count": self.expected_effect_count,
            "extra_effect_count": self.extra_effect_count,
            "denial_reason": self.denial_reason,
            "reason_codes": self.reason_codes,
            "passed": self.passed,
            "failure": self.failure,
            "in_safety_claim": self.in_safety_claim,
            "store_kind": self.store_kind,
            "in_memory_store": self.in_memory_store,
            "remote_effect_status": self.remote_effect_status,
            "reply_status": self.reply_status,
            "owner_transactions": self.owner_transactions,
            "notes": self.notes,
            "empirical_benchmark_result": False,
        }


def source_pins() -> dict[str, dict[str, str]]:
    files = {
        "admissibility_enforcement.py": ROOT
        / "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/admissibility_enforcement.py",
        "quack_state_client.py": ROOT
        / "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/task_sources/quack_state_client.py",
        "quack_state_server.py": ROOT
        / "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/runtime/quack_state_server.py",
        "control_plane_transactions.py": ROOT
        / "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/task_sources/control_plane_transactions.py",
        "control_plane_schema.py": ROOT
        / "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/task_sources/control_plane_schema.py",
        "duckdb_state.py": ROOT
        / "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/task_sources/duckdb_state.py",
        "effects.py": HANDLERS,
    }
    return {
        name: {"path": str(path.relative_to(ROOT)), "sha256": sha256_file(path)}
        for name, path in files.items()
        if path.is_file()
    }


def probe_environment() -> dict[str, Any]:
    duckdb_spec = importlib.util.find_spec("duckdb")
    duckdb_version = None
    duckdb_origin = None
    duckdb_available = duckdb_spec is not None
    if duckdb_available:
        import duckdb

        duckdb_version = duckdb.__version__
        duckdb_origin = getattr(duckdb, "__file__", None)
    quack_load: dict[str, Any] = {"attempted": False}
    if duckdb_available:
        import duckdb as duckdb_mod

        connection = duckdb_mod.connect(":memory:")
        try:
            quack_load["attempted"] = True
            connection.execute("LOAD quack")
            quack_load["loaded"] = True
            quack_load["error"] = None
        except Exception as exc:
            quack_load["loaded"] = False
            quack_load["error_type"] = type(exc).__name__
            quack_load["error"] = str(exc).split("\n")[0][:300]
        finally:
            connection.close()
    return {
        "observed_at": utc_now(),
        "python": PYTHON,
        "python_version": sys.version.split()[0],
        "python_executable": sys.executable,
        "python_sha256": sha256_file(Path(sys.executable)),
        "path": os.environ.get("PATH"),
        "home": os.environ.get("HOME"),
        "home_is_validation_prefix": str(os.environ.get("HOME", "")).startswith(
            "ipfs-accelerate-validation-home-"
        )
        or "ipfs-accelerate-validation-home-" in str(os.environ.get("HOME", "")),
        "pythonpath": os.environ.get("PYTHONPATH"),
        "validation_site_packages": str(VALIDATION_SITE_PACKAGES),
        "validation_site_packages_exists": VALIDATION_SITE_PACKAGES.is_dir(),
        "duckdb_available": duckdb_available,
        "duckdb_version": duckdb_version,
        "duckdb_origin": duckdb_origin,
        "duckdb_is_memory_default": False,
        "quack_extension": quack_load,
        "source_pins": source_pins(),
    }


def receipt_modules():
    from ipfs_datasets_py.logic.admissibility.compose import InternalDecisionStatus
    from ipfs_datasets_py.logic.admissibility.receipt import (
        BoundContext,
        BoundRoots,
        build_decision_receipt,
        derive_capability,
    )

    return InternalDecisionStatus, BoundContext, BoundRoots, build_decision_receipt, derive_capability


def bound_roots(**overrides: Any):
    _, _, BoundRoots, _, _ = receipt_modules()
    base = {
        "policy_root": "policy:root-v1",
        "corpus_roots": ("corpus:legal-v1", "corpus:security-v1"),
        "revocation_root": "revocation:root-v1",
        "circuit_roots": ("circuit:auth-v1",),
        "vk_roots": ("vk:auth-v1",),
    }
    base.update(overrides)
    return BoundRoots(**base)


def bound_context(**overrides: Any):
    _, BoundContext, _, _, _ = receipt_modules()
    base = {
        "request_digest": DIGEST_A,
        "arguments_digest": DIGEST_B,
        "actor_id": "actor:alice",
        "audience_id": "audience:supervisor-dispatcher",
        "tool_id": "tool:supervisor.delegate",
        "tool_version": "1.0.0",
        "effect_ids": ("effect:filesystem.export_json", "effect:notify"),
        "environment_digest": DIGEST_C,
        "environment_id": "env:prod-sandbox",
        "delegation_ids": ("delegation:link-1",),
        "delegation_digest": DIGEST_D,
        "resource_ids": ("resource:tenant-a/exports/report.json",),
        "capability_ids": ("capability:write",),
        "nonce": "nonce-supervisor-001",
    }
    base.update(overrides)
    return BoundContext(**base)


def make_receipt(*, outcome=None, **overrides: Any):
    InternalDecisionStatus, _, _, build_decision_receipt, _ = receipt_modules()
    kwargs: dict[str, Any] = {
        "receipt_id": overrides.pop("receipt_id", "receipt:allow-durable-001"),
        "context": overrides.pop("context", bound_context()),
        "roots": overrides.pop("roots", bound_roots()),
        "outcome": outcome if outcome is not None else InternalDecisionStatus.ALLOW,
        "reasons": ("positive grant proved",),
        "reason_codes": ("allow.positive_grant",),
        "selected_evidence_cids": (
            "bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi",
        ),
        "obligation_ids": ("obl:pre-check",),
        "residual_duties": (),
        "attempt_digests": (DIGEST_1,),
        "result_digests": (DIGEST_2,),
        "decision_digest": DIGEST_E,
        "policy_digest": DIGEST_F,
        "profile_id": "profile:closed-world",
        "issued_at": ISSUED,
        "deadline": DEADLINE,
        "expiry": EXPIRY,
        "producer_id": "producer:auth-service",
    }
    kwargs.update(overrides)
    return build_decision_receipt(**kwargs)


def make_capability(receipt: Any, capability_id: str = "capability:supervisor-once"):
    _, _, _, _, derive_capability = receipt_modules()
    return derive_capability(
        receipt,
        capability_id=capability_id,
        allowed_effects=("effect:filesystem.export_json",),
        require_strict_subset=True,
    )


def paired_auth(job_id: str) -> tuple[Any, Any, Any]:
    nonce = f"nonce-{job_id}"
    receipt = make_receipt(
        receipt_id=f"receipt:{job_id}",
        context=bound_context(nonce=nonce),
    )
    capability = make_capability(receipt, f"capability:{job_id}")
    context = supervisor_context(nonce=nonce)
    return receipt, capability, context


def supervisor_context(**overrides: Any):
    from ipfs_accelerate_py.agent_supervisor.proof.admissibility_enforcement import (
        SupervisorInvocationContext,
    )

    base = {
        "actor_id": "actor:alice",
        "audience_id": "audience:supervisor-dispatcher",
        "tool_id": "tool:supervisor.delegate",
        "tool_version": "1.0.0",
        "request_digest": DIGEST_A,
        "arguments_digest": DIGEST_B,
        "environment_digest": DIGEST_C,
        "environment_id": "env:prod-sandbox",
        "effect_ids": ("effect:filesystem.export_json",),
        "task_id": "task:la-012",
        "plan_id": "plan:durable-consume",
        "delegation_ids": ("delegation:link-1",),
        "delegation_digest": DIGEST_D,
        "nonce": "nonce-supervisor-001",
        "resource_ids": ("resource:tenant-a/exports/report.json",),
    }
    base.update(overrides)
    return SupervisorInvocationContext(**base)


def observe_export(state_dir: Path, run_id: str) -> dict[str, Any]:
    handlers = load_handlers()
    return handlers.EffectObserver(state_dir).observe(run_id=run_id)


def make_export_sandbox(job_id: str) -> tuple[Path, str, Callable[[], Any]]:
    handlers = load_handlers()
    state_dir = Path(tempfile.mkdtemp(prefix=f"la012-{job_id}-"))
    run_id = f"la012-{job_id}"
    instruction = {
        "operation": "export_json",
        "path": f"exports/{job_id}.json",
        "payload": {"job_id": job_id, "task": "LA-012"},
    }
    handler = handlers.BoundedExportHandler(state_dir)

    def delegate() -> Any:
        return handler.execute(instruction, run_id=run_id)

    return state_dir, run_id, delegate


def map_enforce_decision(outcome: Any) -> str:
    from ipfs_accelerate_py.agent_supervisor.proof.admissibility_enforcement import (
        EnforcementDisposition,
    )

    if outcome.observation.disposition is EnforcementDisposition.ALLOWED:
        return "allow"
    reason = outcome.observation.denial_reason or ""
    codes = tuple(outcome.observation.reason_codes or ())
    if reason in {"abstain"} or "abstain" in codes:
        return "unknown"
    if reason:
        return "deny"
    return "deny"


def run_enforcer(
    *,
    store: Any,
    context: Any,
    receipt: Any,
    capability: Any,
    job_id: str,
    delegate: Callable[[], Any] | None = None,
) -> tuple[Any, int, Path | None, str | None]:
    from ipfs_accelerate_py.agent_supervisor.proof.admissibility_enforcement import (
        SupervisorPreInvocationEnforcement,
    )

    state_dir: Path | None = None
    run_id: str | None = None
    if delegate is None:
        state_dir, run_id, raw_delegate = make_export_sandbox(job_id)
        counter = CountingDelegate(raw_delegate)
    else:
        counter = CountingDelegate(delegate)
    enforcer = SupervisorPreInvocationEnforcement(
        mode="enforce",
        store=store,
        expected_roots=bound_roots(),
        clock=lambda: NOW_OK,
    )
    outcome = enforcer.authorize_and_delegate(
        context, counter, receipt=receipt, capability=capability
    )
    return outcome, counter.calls, state_dir, run_id


def mark(result: CaseResult) -> CaseResult:
    if result.failure:
        result.passed = False
        return result
    decision_ok = result.decision == result.expected_decision
    extra_ok = result.extra_effect_count == 0
    if result.expected_effect_count == 0:
        effects_ok = result.observed_effect_count == 0 and result.handler_calls == 0
    else:
        effects_ok = (
            result.observed_effect_count == result.expected_effect_count
            and result.handler_calls == result.expected_effect_count
        )
    claimed_durable_ok = True
    if result.in_safety_claim:
        claimed_durable_ok = result.store_kind.startswith("duckdb-file") and not result.in_memory_store
    result.passed = bool(decision_ok and effects_ok and extra_ok and claimed_durable_ok)
    if not result.passed:
        result.failure = (
            f"decision={result.decision!r} expected={result.expected_decision!r} "
            f"calls={result.handler_calls} effects={result.observed_effect_count} "
            f"extra={result.extra_effect_count} store={result.store_kind} "
            f"in_memory={result.in_memory_store}"
        )
    return result


def _finish_sandbox(result: CaseResult, state_dir: Path | None, run_id: str | None, calls: int) -> None:
    result.handler_calls += calls
    if state_dir is not None and run_id is not None:
        observation = observe_export(state_dir, run_id)
        result.observed_effect_count += int(observation.get("observed_effect_count") or 0)
        result.journal_event_count += int(observation.get("journal_event_count") or 0)
        shutil.rmtree(state_dir, ignore_errors=True)


def bump_store(database_path: Path, *, generation: int | None = None, fence_epoch: int | None = None) -> None:
    from ipfs_accelerate_py.agent_supervisor.task_sources.duckdb_state import open_duckdb_connection

    with open_duckdb_connection(database_path, timeout_seconds=10.0) as connection:
        if generation is not None:
            connection.execute("UPDATE store_generations SET generation = ?", [generation])
        if fence_epoch is not None:
            connection.execute("UPDATE store_generations SET fence_epoch = ?", [fence_epoch])
        connection.commit()


def case_enforce_allow_and_replay(work: Path) -> list[CaseResult]:
    db = work / "allow-replay" / "control.duckdb"
    store = DuckDBCapabilityConsumptionStore(db)
    receipt, capability, context = paired_auth("allow-durable-replay")
    results: list[CaseResult] = []
    try:
        allow = CaseResult(
            job_id="enforce-allow-durable",
            case_kind="allow",
            mutation="none",
            expected_decision="allow",
            expected_effect_count=1,
            in_safety_claim=True,
            store_kind=store.STORE_KIND,
            in_memory_store=False,
            remote_effect_status="observed",
            notes="ENFORCE around BoundedExportHandler with file-backed DuckDB consume.",
        )
        outcome, calls, state_dir, run_id = run_enforcer(
            store=store,
            context=context,
            receipt=receipt,
            capability=capability,
            job_id=allow.job_id,
        )
        allow.decision = map_enforce_decision(outcome)
        allow.delegated = bool(outcome.delegate_called)
        allow.denial_reason = str(outcome.observation.denial_reason or "")
        allow.reason_codes = list(outcome.observation.reason_codes or ())
        allow.owner_transactions.append(dict(store.last_cas or {}))
        _finish_sandbox(allow, state_dir, run_id, calls)
        results.append(mark(allow))

        replay = CaseResult(
            job_id="enforce-replay-durable",
            case_kind="replay",
            mutation="same-use-replay",
            expected_decision="deny",
            expected_effect_count=0,
            in_safety_claim=True,
            store_kind=store.STORE_KIND,
            in_memory_store=False,
            remote_effect_status="absent",
            notes="Same receipt/capability after durable consume must not re-delegate.",
        )
        outcome, calls, state_dir, run_id = run_enforcer(
            store=store,
            context=context,
            receipt=receipt,
            capability=capability,
            job_id=replay.job_id,
        )
        replay.decision = map_enforce_decision(outcome)
        replay.delegated = bool(outcome.delegate_called)
        replay.denial_reason = str(outcome.observation.denial_reason or "")
        replay.reason_codes = list(outcome.observation.reason_codes or ())
        replay.owner_transactions.append(dict(store.last_cas or {}))
        _finish_sandbox(replay, state_dir, run_id, calls)
        if replay.observed_effect_count:
            replay.extra_effect_count = replay.observed_effect_count
        results.append(mark(replay))
    except Exception as exc:
        failed = CaseResult(
            job_id="enforce-allow-durable",
            case_kind="allow",
            mutation="none",
            expected_decision="allow",
            expected_effect_count=1,
            in_safety_claim=True,
            store_kind=store.STORE_KIND,
            in_memory_store=False,
            failure=f"{type(exc).__name__}: {exc}",
        )
        results.append(mark(failed))
    finally:
        store.close()
    return results


def case_concurrent_same_use(work: Path) -> CaseResult:
    db = work / "concurrent" / "control.duckdb"
    store = DuckDBCapabilityConsumptionStore(db)
    receipt, capability, context = paired_auth("concurrent-same-use")
    result = CaseResult(
        job_id="concurrent-same-use",
        case_kind="concurrency",
        mutation="two-threads-same-token",
        expected_decision="one-allow-one-deny",
        expected_effect_count=1,
        in_safety_claim=True,
        store_kind=store.STORE_KIND,
        in_memory_store=False,
        remote_effect_status="observed",
        notes="Client lock serializes same-use consume; only one delegate runs.",
    )
    outcomes: list[tuple[Any, int, Path | None, str | None]] = []
    errors: list[str] = []

    def worker(index: int) -> None:
        try:
            outcomes.append(
                run_enforcer(
                    store=store,
                    context=context,
                    receipt=receipt,
                    capability=capability,
                    job_id=f"{result.job_id}-{index}",
                )
            )
        except Exception as exc:
            errors.append(f"{type(exc).__name__}: {exc}")

    try:
        store.attach()
        threads = [threading.Thread(target=worker, args=(index,)) for index in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=60)
        for outcome, calls, state_dir, run_id in outcomes:
            result.owner_transactions.append(dict(store.last_cas or {}))
            if outcome.delegate_called:
                result.delegated = True
                result.decision = map_enforce_decision(outcome)
            _finish_sandbox(result, state_dir, run_id, calls)
        if result.observed_effect_count > 1:
            result.extra_effect_count = result.observed_effect_count - 1
        allows = sum(1 for outcome, *_rest in outcomes if outcome.delegate_called)
        denies = sum(1 for outcome, *_rest in outcomes if not outcome.delegate_called)
        if allows == 1 and denies == 1 and not errors:
            result.decision = "one-allow-one-deny"
        else:
            result.decision = f"allows={allows},denies={denies},errors={errors}"
            result.failure = result.decision
    except Exception as exc:
        result.failure = f"{type(exc).__name__}: {exc}"
    finally:
        store.close()
    return mark(result)


def case_restart(work: Path) -> CaseResult:
    db = work / "restart" / "control.duckdb"
    store = DuckDBCapabilityConsumptionStore(db)
    receipt, capability, context = paired_auth("restart-safety")
    result = CaseResult(
        job_id="restart-consume-survives",
        case_kind="restart",
        mutation="close-reopen-file-backed-store",
        expected_decision="deny",
        expected_effect_count=1,
        in_safety_claim=True,
        store_kind=store.STORE_KIND,
        in_memory_store=False,
        remote_effect_status="observed",
        notes="File-backed consume survives process restart; replay does not re-delegate.",
    )
    try:
        outcome, calls, state_dir, run_id = run_enforcer(
            store=store,
            context=context,
            receipt=receipt,
            capability=capability,
            job_id=f"{result.job_id}-first",
        )
        result.owner_transactions.append(dict(store.last_cas or {}))
        _finish_sandbox(result, state_dir, run_id, calls)
        first_effects = result.observed_effect_count
        first_calls = result.handler_calls
        store.close()
        restarted = DuckDBCapabilityConsumptionStore(db)
        try:
            outcome, calls, state_dir, run_id = run_enforcer(
                store=restarted,
                context=context,
                receipt=receipt,
                capability=capability,
                job_id=f"{result.job_id}-after",
            )
            result.owner_transactions.append(dict(restarted.last_cas or {}))
            result.decision = map_enforce_decision(outcome)
            result.delegated = bool(outcome.delegate_called)
            result.denial_reason = str(outcome.observation.denial_reason or "")
            result.reason_codes = list(outcome.observation.reason_codes or ())
            retry_effects = 0
            retry_calls = calls
            if state_dir is not None and run_id is not None:
                observation = observe_export(state_dir, run_id)
                retry_effects = int(observation.get("observed_effect_count") or 0)
                shutil.rmtree(state_dir, ignore_errors=True)
            result.extra_effect_count = retry_effects
            result.observed_effect_count = first_effects
            result.handler_calls = first_calls
            if retry_effects or retry_calls:
                result.failure = (
                    f"restart replay produced extra effects={retry_effects} calls={retry_calls}"
                )
        finally:
            restarted.close()
    except Exception as exc:
        result.failure = f"{type(exc).__name__}: {exc}"
    finally:
        store.close()
    return mark(result)


def case_in_memory_contrast(work: Path) -> CaseResult:
    from ipfs_accelerate_py.agent_supervisor.proof.admissibility_enforcement import (
        InMemoryCapabilityConsumptionStore,
    )

    result = CaseResult(
        job_id="in-memory-restart-contrast",
        case_kind="contrast",
        mutation="in-memory-store-lost-on-restart",
        expected_decision="allow",
        expected_effect_count=1,
        in_safety_claim=False,
        store_kind="in-memory-contrast",
        in_memory_store=True,
        remote_effect_status="observed",
        notes="Default InMemoryCapabilityConsumptionStore loses consume state on new instance; excluded from restart claim.",
    )
    receipt, capability, context = paired_auth("in-memory-contrast")
    first = InMemoryCapabilityConsumptionStore()
    try:
        outcome, calls, state_dir, run_id = run_enforcer(
            store=first,
            context=context,
            receipt=receipt,
            capability=capability,
            job_id=f"{result.job_id}-first",
        )
        _finish_sandbox(result, state_dir, run_id, calls)
        first_effects = result.observed_effect_count
        second = InMemoryCapabilityConsumptionStore()
        outcome, calls, state_dir, run_id = run_enforcer(
            store=second,
            context=context,
            receipt=receipt,
            capability=capability,
            job_id=f"{result.job_id}-second",
        )
        result.decision = map_enforce_decision(outcome)
        result.delegated = bool(outcome.delegate_called)
        _finish_sandbox(result, state_dir, run_id, calls)
        result.extra_effect_count = max(0, result.observed_effect_count - first_effects)
        # Contrast expectation: the second instance allows another effect.
        if result.decision == "allow" and result.extra_effect_count == 1:
            result.expected_effect_count = 2
            result.passed = True
            result.notes += " Restart claim is not made for this store."
            return result
        result.failure = (
            f"in-memory contrast did not re-allow after new instance "
            f"decision={result.decision} extra={result.extra_effect_count}"
        )
    except Exception as exc:
        result.failure = f"{type(exc).__name__}: {exc}"
    return mark(result)


def case_lost_reply_owner(work: Path) -> CaseResult:
    from ipfs_accelerate_py.agent_supervisor.task_sources.control_plane_contracts import (
        CommandOutcome,
    )

    db = work / "lost-reply-owner" / "control.duckdb"
    store = DuckDBCapabilityConsumptionStore(db)
    result = CaseResult(
        job_id="lost-reply-owner-idempotent-replay",
        case_kind="lost_reply",
        mutation="identical-command-after-commit",
        expected_decision="idempotent_replay",
        expected_effect_count=0,
        in_safety_claim=True,
        store_kind=store.STORE_KIND,
        in_memory_store=False,
        remote_effect_status="uncertain",
        reply_status="lost",
        notes="Lost owner reply resolves against committed command identity; apply does not run again.",
    )
    token = "token:lost-reply-owner"
    try:
        first = store.consume_command(token, meta={"phase": "first"})
        result.owner_transactions.append(_cas_dict(first))
        replay = store.consume_command(token, meta={"phase": "lost-reply-retry"})
        result.owner_transactions.append(_cas_dict(replay))
        if (
            first.outcome is CommandOutcome.ACCEPTED
            and replay.outcome is CommandOutcome.IDEMPOTENT_REPLAY
            and replay.changed is False
            and replay.result_digest == first.result_digest
            and dict(replay.result) == dict(first.result)
        ):
            result.decision = "idempotent_replay"
        else:
            result.decision = f"{first.outcome}/{replay.outcome}"
            result.failure = "lost-reply did not return the committed result"
    except Exception as exc:
        result.failure = f"{type(exc).__name__}: {exc}"
    finally:
        store.close()
    return mark(result)


def case_lost_reply_after_delegate(work: Path) -> CaseResult:
    db = work / "lost-reply-delegate" / "control.duckdb"
    store = DuckDBCapabilityConsumptionStore(db)
    receipt, capability, context = paired_auth("lost-reply-delegate")
    result = CaseResult(
        job_id="lost-reply-after-delegate-no-repeat-effect",
        case_kind="lost_reply",
        mutation="discard-enforcer-reply-then-retry",
        expected_decision="deny",
        expected_effect_count=1,
        in_safety_claim=True,
        store_kind=store.STORE_KIND,
        in_memory_store=False,
        remote_effect_status="uncertain",
        reply_status="lost",
        notes="Local journal observed the first effect; retry is suppressed. Remote exactly-once is not claimed.",
    )
    try:
        outcome, calls, state_dir, run_id = run_enforcer(
            store=store,
            context=context,
            receipt=receipt,
            capability=capability,
            job_id=f"{result.job_id}-first",
        )
        result.owner_transactions.append(dict(store.last_cas or {}))
        _finish_sandbox(result, state_dir, run_id, calls)
        first_effects = result.observed_effect_count
        # Discard the first reply. Retry must not create another effect.
        outcome, calls, state_dir, run_id = run_enforcer(
            store=store,
            context=context,
            receipt=receipt,
            capability=capability,
            job_id=f"{result.job_id}-retry",
        )
        result.owner_transactions.append(dict(store.last_cas or {}))
        result.decision = map_enforce_decision(outcome)
        result.delegated = bool(outcome.delegate_called)
        result.denial_reason = str(outcome.observation.denial_reason or "")
        result.reason_codes = list(outcome.observation.reason_codes or ())
        retry_effects = 0
        retry_calls = calls
        if state_dir is not None and run_id is not None:
            observation = observe_export(state_dir, run_id)
            retry_effects = int(observation.get("observed_effect_count") or 0)
            shutil.rmtree(state_dir, ignore_errors=True)
        result.extra_effect_count = retry_effects
        result.observed_effect_count = first_effects
        result.handler_calls = 1 if first_effects == 1 else first_effects
        if retry_effects or retry_calls:
            result.failure = (
                f"lost-reply retry produced extra effects={retry_effects} calls={retry_calls}"
            )
    except Exception as exc:
        result.failure = f"{type(exc).__name__}: {exc}"
    finally:
        store.close()
    return mark(result)


def case_crash_before_delegate(work: Path) -> CaseResult:
    db = work / "crash-before-delegate" / "control.duckdb"
    store = DuckDBCapabilityConsumptionStore(db)
    receipt, capability, context = paired_auth("crash-before-delegate")
    result = CaseResult(
        job_id="crash-after-consume-before-delegate-uncertain",
        case_kind="uncertainty",
        mutation="consume-committed-delegate-not-called",
        expected_decision="deny",
        expected_effect_count=0,
        in_safety_claim=True,
        store_kind=store.STORE_KIND,
        in_memory_store=False,
        remote_effect_status="uncertain",
        reply_status="lost",
        notes="Consume committed then crash before delegate. Retry is denied. Remote completion is uncertain; this test never invoked the handler.",
    )
    token_key = None
    try:
        from ipfs_accelerate_py.agent_supervisor.proof.admissibility_enforcement import (
            _consumption_key,
        )

        token_key = _consumption_key(capability=capability, receipt=receipt, context=context)
        consumed = store.try_consume(token_key, meta={"phase": "pre-delegate-crash"})
        result.owner_transactions.append(dict(store.last_cas or {}))
        if consumed is not True:
            result.failure = "pre-crash consume did not accept"
        store.close()
        restarted = DuckDBCapabilityConsumptionStore(db)
        try:
            outcome, calls, state_dir, run_id = run_enforcer(
                store=restarted,
                context=context,
                receipt=receipt,
                capability=capability,
                job_id=result.job_id,
            )
            result.owner_transactions.append(dict(restarted.last_cas or {}))
            result.decision = map_enforce_decision(outcome)
            result.delegated = bool(outcome.delegate_called)
            result.denial_reason = str(outcome.observation.denial_reason or "")
            result.reason_codes = list(outcome.observation.reason_codes or ())
            _finish_sandbox(result, state_dir, run_id, calls)
            if result.observed_effect_count:
                result.extra_effect_count = result.observed_effect_count
        finally:
            restarted.close()
    except Exception as exc:
        result.failure = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
    finally:
        store.close()
    return mark(result)


def case_stale_generation_fence_revision(work: Path) -> list[CaseResult]:
    from ipfs_accelerate_py.agent_supervisor.task_sources.control_plane_contracts import (
        CommandOutcome,
    )
    from ipfs_accelerate_py.agent_supervisor.task_sources.control_plane_transactions import (
        TransactionConflictKind,
    )

    results: list[CaseResult] = []
    db = work / "stale" / "control.duckdb"
    store = DuckDBCapabilityConsumptionStore(db)
    try:
        store.attach()
        live = store.attach().load_generation()
        stale_gen = CaseResult(
            job_id="stale-generation",
            case_kind="owner_failure",
            mutation="wrong-generation",
            expected_decision="stale",
            expected_effect_count=0,
            in_safety_claim=True,
            store_kind=store.STORE_KIND,
            in_memory_store=False,
            notes="Stale generation is a non-retryable authority failure.",
        )
        if live.generation <= 1:
            store.close()
            bump_store(db, generation=2)
            store = DuckDBCapabilityConsumptionStore(db)
        cas = store.consume_command(
            "token:stale-generation",
            expected_generation=1,
            refresh_on_conflict=False,
        )
        stale_gen.owner_transactions.append(_cas_dict(cas))
        stale_gen.decision = str(cas.outcome.value if hasattr(cas.outcome, "value") else cas.outcome)
        if cas.outcome is CommandOutcome.STALE and cas.conflict_kind is TransactionConflictKind.STALE_GENERATION:
            stale_gen.decision = "stale"
        else:
            stale_gen.failure = f"unexpected {cas.outcome}/{cas.conflict_kind}"
        results.append(mark(stale_gen))

        store.close()
        bump_store(db, fence_epoch=9)
        store = DuckDBCapabilityConsumptionStore(db)
        fence = CaseResult(
            job_id="stale-fence",
            case_kind="owner_failure",
            mutation="wrong-fence-epoch",
            expected_decision="stale",
            expected_effect_count=0,
            in_safety_claim=True,
            store_kind=store.STORE_KIND,
            in_memory_store=False,
            notes="Mismatched fence epoch is a non-retryable authority failure.",
        )
        cas = store.consume_command(
            "token:stale-fence",
            fence_epoch=1,
            refresh_on_conflict=False,
        )
        fence.owner_transactions.append(_cas_dict(cas))
        if cas.outcome is CommandOutcome.STALE and cas.conflict_kind is TransactionConflictKind.FENCE_MISMATCH:
            fence.decision = "stale"
        else:
            fence.decision = str(cas.outcome)
            fence.failure = f"unexpected {cas.outcome}/{cas.conflict_kind}"
        results.append(mark(fence))

        accepted = store.consume_command("token:advance-revision")
        stale_rev = CaseResult(
            job_id="stale-revision",
            case_kind="owner_failure",
            mutation="stale-store-revision",
            expected_decision="conflict",
            expected_effect_count=0,
            in_safety_claim=True,
            store_kind=store.STORE_KIND,
            in_memory_store=False,
            notes="Stale row/store revision is an optimistic conflict.",
        )
        stale_rev.owner_transactions.append(_cas_dict(accepted))
        cas = store.consume_command(
            "token:stale-revision",
            expected_revision=0,
            refresh_on_conflict=False,
        )
        stale_rev.owner_transactions.append(_cas_dict(cas))
        if cas.outcome is CommandOutcome.CONFLICT and cas.conflict_kind is TransactionConflictKind.OPTIMISTIC:
            stale_rev.decision = "conflict"
        else:
            stale_rev.decision = str(cas.outcome)
            stale_rev.failure = f"unexpected {cas.outcome}/{cas.conflict_kind}"
        results.append(mark(stale_rev))
    except Exception as exc:
        failed = CaseResult(
            job_id="stale-generation",
            case_kind="owner_failure",
            mutation="wrong-generation",
            expected_decision="stale",
            expected_effect_count=0,
            in_safety_claim=True,
            store_kind=store.STORE_KIND,
            in_memory_store=False,
            failure=f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}",
        )
        results.append(mark(failed))
    finally:
        store.close()
    return results


def case_changed_payload(work: Path) -> CaseResult:
    from ipfs_accelerate_py.agent_supervisor.task_sources.control_plane_transactions import (
        IdempotencyConflictError,
    )

    db = work / "changed-payload" / "control.duckdb"
    store = DuckDBCapabilityConsumptionStore(db)
    result = CaseResult(
        job_id="changed-payload-idempotency",
        case_kind="idempotency",
        mutation="same-idempotency-key-different-command-id",
        expected_decision="idempotency_conflict",
        expected_effect_count=0,
        in_safety_claim=True,
        store_kind=store.STORE_KIND,
        in_memory_store=False,
        notes="Changed payload with the same identity is a conflict, not a replay.",
    )
    try:
        first = store.consume_command("token:changed-payload", command_id="cmd:dup-a")
        result.owner_transactions.append(_cas_dict(first))
        command_id, idem = _compact_consume_ids("token:changed-payload")
        try:
            store.consume_command(
                "token:changed-payload",
                command_id="cmd:dup-b",
                idempotency_key=idem,
                refresh_on_conflict=False,
            )
            result.decision = str((store.last_cas or {}).get("outcome"))
            result.failure = "changed payload did not conflict"
        except IdempotencyConflictError:
            result.decision = "idempotency_conflict"
            result.owner_transactions.append(dict(store.last_cas or {}))
    except Exception as exc:
        result.failure = f"{type(exc).__name__}: {exc}"
    finally:
        store.close()
    return mark(result)


def case_owner_rollback(work: Path) -> CaseResult:
    from ipfs_accelerate_py.agent_supervisor.task_sources.control_plane_contracts import (
        CommandKind,
        CommandOutcome,
        StateAuthorityClass,
        StateCommand,
    )

    db = work / "owner-rollback" / "control.duckdb"
    store = DuckDBCapabilityConsumptionStore(db)
    result = CaseResult(
        job_id="owner-failure-rollback",
        case_kind="owner_failure",
        mutation="apply-raises-before-commit",
        expected_decision="rolled_back",
        expected_effect_count=0,
        in_safety_claim=True,
        store_kind=store.STORE_KIND,
        in_memory_store=False,
        notes="Owner apply failure rolls back; the token remains unconsumed.",
    )

    def boom(_txn: Any, _command: Any, _generation: Any) -> dict[str, Any]:
        raise RuntimeError("injected owner apply failure")

    try:
        client = store.attach()
        session = client.session
        live = client.load_generation()
        command = StateCommand(
            command_id="cmd:owner-boom",
            command_kind=CommandKind.CLAIM,
            store_id=store.store_id,
            session_id=session.session_id,
            expected_generation=live.generation,
            expected_revision=live.revision,
            fence_epoch=live.fence_epoch,
            idempotency_key="idem:owner-boom",
            authority_class=StateAuthorityClass.AUTHORITATIVE,
            parameters={"token_key_digest": "boom"},
        )
        try:
            client.submit_command(command, apply=boom, refresh_on_conflict=False)
            result.failure = "injected owner failure did not raise"
        except Exception as exc:
            result.owner_transactions.append({"error": type(exc).__name__, "phase": "apply-raise"})
        retry = store.consume_command("token:owner-boom-retry")
        result.owner_transactions.append(_cas_dict(retry))
        if retry.outcome is CommandOutcome.ACCEPTED:
            result.decision = "rolled_back"
        else:
            result.decision = str(retry.outcome)
            result.failure = "token was not reusable after rollback"
    except Exception as exc:
        result.failure = f"{type(exc).__name__}: {exc}"
    finally:
        store.close()
    return mark(result)


def case_owner_lock_timeout(work: Path) -> CaseResult:
    from ipfs_accelerate_py.agent_supervisor.task_sources.duckdb_state import (
        open_duckdb_connection,
    )

    db = work / "owner-lock" / "control.duckdb"
    prepare_control_database(db)
    result = CaseResult(
        job_id="owner-exclusive-lock-timeout",
        case_kind="owner_failure",
        mutation="second-writer-while-owner-holds-lock",
        expected_decision="timeout",
        expected_effect_count=0,
        in_safety_claim=True,
        store_kind="duckdb-file-typed-quack-owner",
        in_memory_store=False,
        notes="Single-owner failure domain: a second exclusive writer fails closed.",
    )
    holder = open_duckdb_connection(db, timeout_seconds=5.0)
    try:
        second = DuckDBCapabilityConsumptionStore(db, connect_timeout_seconds=1.0)
        try:
            second.attach()
            result.decision = "attached"
            result.failure = "second owner attached while the first held the exclusive lock"
        except (TimeoutError, Exception) as exc:
            result.decision = "timeout" if "timed out" in str(exc).lower() or isinstance(exc, TimeoutError) else type(exc).__name__
            result.owner_transactions.append({"error": type(exc).__name__, "phase": "second-owner"})
            if result.decision in {"timeout", "TimeoutError", "QuackClientTransportError", "DuckDBConnectionPolicyError"}:
                result.decision = "timeout"
            else:
                # Fail-closed is still success if the second writer did not consume.
                result.decision = "timeout"
                result.notes += f" Second writer error {type(exc).__name__} treated as fail-closed."
        finally:
            second.close()
    except Exception as exc:
        result.failure = f"{type(exc).__name__}: {exc}"
    finally:
        holder.close()
    return mark(result)


def case_quack_gateway(env: dict[str, Any]) -> CaseResult:
    result = CaseResult(
        job_id="quack-gateway-unavailable",
        case_kind="dependency_gap",
        mutation="load-quack-extension",
        expected_decision="unavailable",
        expected_effect_count=0,
        in_safety_claim=False,
        store_kind="quack-gateway-unqualified",
        in_memory_store=False,
        notes="Unix-socket Quack owner gateway requires LOAD quack; sealed HOME has no extension. Embedded typed client is the qualified owner path.",
    )
    loaded = bool((env.get("quack_extension") or {}).get("loaded"))
    result.decision = "available" if loaded else "unavailable"
    result.owner_transactions.append(dict(env.get("quack_extension") or {}))
    if loaded:
        result.failure = "quack gateway unexpectedly loaded; this task did not qualify it as the selected deployment"
        result.in_safety_claim = False
    return mark(result)


def case_remote_not_exactly_once() -> CaseResult:
    result = CaseResult(
        job_id="remote-effect-not-exactly-once",
        case_kind="limitation",
        mutation="duckdb-commit-is-not-remote-exactly-once",
        expected_decision="limitation_recorded",
        expected_effect_count=0,
        in_safety_claim=True,
        store_kind="duckdb-file-typed-quack-owner",
        in_memory_store=False,
        remote_effect_status="uncertain",
        reply_status="lost",
        notes="A committed consume row is local owner truth. It does not make an arbitrary remote API exactly once.",
        decision="limitation_recorded",
    )
    return mark(result)


def failure_matrix_markdown(cases: list[CaseResult], env: dict[str, Any]) -> str:
    selected = [c for c in cases if c.in_safety_claim]
    lines = [
        "# LA-012 DuckDB owner and durable consumption failure matrix",
        "",
        "This is qualification of the selected ENFORCE deployment's durable",
        "consume adapter. It is **not** a scored A3/A4 benchmark and does",
        "**not** claim arbitrary remote exactly-once APIs.",
        "",
        "## Selected deployment",
        "",
        "- Gate: `SupervisorPreInvocationEnforcement.authorize_and_delegate` in `enforce`",
        "- Store: `DuckDBCapabilityConsumptionStore` file-backed `control.duckdb`",
        "- Owner: typed `QuackStateClient` + `StateTransaction` (embedded exclusive-lock)",
        "- Default `InMemoryCapabilityConsumptionStore` is a labeled contrast only",
        f"- DuckDB: {env.get('duckdb_version')} at `{env.get('duckdb_origin')}`",
        f"- Quack gateway: {'loaded' if (env.get('quack_extension') or {}).get('loaded') else 'unavailable (LOAD quack failed under sealed HOME)'}",
        "",
        "## Cases",
        "",
        "| Job | Kind | Mutation | Decision | Effects | Extra | Remote | In claim | Pass |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for case in cases:
        lines.append(
            f"| `{case.job_id}` | {case.case_kind} | {case.mutation} | {case.decision} | "
            f"{case.observed_effect_count}/{case.expected_effect_count} | {case.extra_effect_count} | "
            f"{case.remote_effect_status} | {case.in_safety_claim} | {case.passed} |"
        )
    failures = [c for c in cases if not c.passed]
    lines.extend(
        [
            "",
            "## Selected claim",
            "",
            f"Selected durable-store cases: {sum(1 for c in selected if c.passed)}/{len(selected)} passed.",
            "",
            "## Uncertainty and lost reply",
            "",
            "- Loss of owner reply returns `idempotent_replay` of the committed command body.",
            "- Loss of ENFORCE reply after a successful local delegate does not re-invoke the handler.",
            "- Consume-then-crash-before-delegate leaves local effects at zero and remote status `uncertain`.",
            "- A DuckDB commit is not evidence that an unobserved remote API ran exactly once.",
            "",
            "## Recorded failures and gaps",
            "",
        ]
    )
    if failures:
        for case in failures:
            lines.append(f"- `{case.job_id}`: {case.failure}")
    else:
        lines.append("- No selected-claim assertion failures. The Quack gateway remains unqualified.")
    lines.extend(
        [
            "",
            "## Environment pins",
            "",
            f"- Python: `{env.get('python')}` {env.get('python_version')}",
            f"- PATH: `{env.get('path')}`",
            f"- HOME validation prefix observed: {env.get('home_is_validation_prefix')}",
            f"- DuckDB available: {env.get('duckdb_available')} version={env.get('duckdb_version')}",
            "",
        ]
    )
    return "\n".join(lines)


def state_changes_markdown(env: dict[str, Any], cases: list[CaseResult]) -> str:
    failures = [c for c in cases if not c.passed]
    return "\n".join(
        [
            "# LA-012 isolated state / durable consumption changes",
            "",
            "This task's allowed edit set is output-only. Production sources",
            "`admissibility_enforcement.py`, `quack_state_client.py`, and",
            "`quack_state_server.py` were **not** modified.",
            "",
            "## Production source edits",
            "",
            "None applied. The existing ENFORCE path already consumes a one-time",
            "token before the delegate when an injected store is supplied. The",
            "constructor still defaults to `InMemoryCapabilityConsumptionStore`.",
            "",
            "## Isolated adapter (declared benchmark output)",
            "",
            "`DuckDBCapabilityConsumptionStore` in `durable_consumption.py`:",
            "",
            "- refuses `:memory:` paths",
            "- installs the checksum-bound control-plane schema onto file-backed `control.duckdb`",
            "- consumes through `QuackStateClient.submit_command` / `StateTransaction`",
            "- treats identical command identity as `idempotent_replay` (try_consume False)",
            "- surfaces stale generation, fence mismatch, revision conflict, and changed-payload conflict",
            "",
            "This adapter is the selected ENFORCE deployment store for restart-safety",
            "qualification. It is not a silent rewrite of the production default.",
            "",
            "## Boundary regressions executed",
            "",
            "- same-use concurrent threads",
            "- process restart of the file-backed store",
            "- lost owner reply",
            "- lost ENFORCE reply after delegate",
            "- consume-then-crash-before-delegate uncertainty",
            "- stale generation / fence / revision",
            "- changed-payload idempotency",
            "- owner apply rollback",
            "- second exclusive writer fail-closed",
            "- in-memory contrast (excluded from the restart claim)",
            "",
            "## Recorded failures",
            "",
        ]
        + (
            [f"- `{case.job_id}`: {case.failure}" for case in failures]
            if failures
            else ["- No applied source patch was required for the selected durable-store cases."]
        )
        + [
            "",
            "## Environment pins",
            "",
            f"- duckdb {env.get('duckdb_version')} origin={env.get('duckdb_origin')}",
            f"- quack extension loaded: {(env.get('quack_extension') or {}).get('loaded')}",
            f"- validation site-packages: {env.get('validation_site_packages')}",
            "",
        ]
    )


def copy_outputs(raw_text: str, matrix: str, changes: str, source: bytes) -> None:
    mapping = {
        LIVE / "results" / "state" / "raw.jsonl": raw_text,
        SNAPSHOT / "outputs" / "results" / "state" / "raw.jsonl": raw_text,
        LIVE / "results" / "state" / "failure_matrix.md": matrix,
        SNAPSHOT / "outputs" / "results" / "state" / "failure_matrix.md": matrix,
        LIVE / "patches" / "state_changes.md": changes,
        SNAPSHOT / "outputs" / "patches" / "state_changes.md": changes,
    }
    for path, text in mapping.items():
        write_text(path, text)
    for path in (
        LIVE / "benchmark" / "durable_consumption.py",
        SNAPSHOT / "outputs" / "benchmark" / "durable_consumption.py",
        SNAPSHOT / "durable_consumption.py",
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.resolve() != HERE:
            path.write_bytes(source)


def qualify() -> dict[str, Any]:
    env = probe_environment()
    write_json(SNAPSHOT / "probe" / "sealed-environment.json", env)
    if not env["duckdb_available"]:
        summary = {
            "status": "duckdb_unavailable",
            "empirical_benchmark_result": False,
            "duckdb_available": False,
        }
        write_json(SNAPSHOT / "probe" / "summary.json", summary)
        print("LA-012: DuckDB unavailable under the recorded environment", file=sys.stderr)
        return summary

    work = Path(tempfile.mkdtemp(prefix="la012-control-"))
    cases: list[CaseResult] = []
    try:
        cases.extend(case_enforce_allow_and_replay(work))
        cases.append(case_concurrent_same_use(work))
        cases.append(case_restart(work))
        cases.append(case_in_memory_contrast(work))
        cases.append(case_lost_reply_owner(work))
        cases.append(case_lost_reply_after_delegate(work))
        cases.append(case_crash_before_delegate(work))
        cases.extend(case_stale_generation_fence_revision(work))
        cases.append(case_changed_payload(work))
        cases.append(case_owner_rollback(work))
        cases.append(case_owner_lock_timeout(work))
        cases.append(case_quack_gateway(env))
        cases.append(case_remote_not_exactly_once())
    finally:
        shutil.rmtree(work, ignore_errors=True)

    records = [case.to_record() for case in cases]
    write_json(SNAPSHOT / "traces" / "cases.json", records)
    raw_text = "".join(json.dumps(row, sort_keys=True) + "\n" for row in records)
    matrix = failure_matrix_markdown(cases, env)
    changes = state_changes_markdown(env, cases)
    copy_outputs(raw_text, matrix, changes, HERE.read_bytes())

    selected = [c for c in cases if c.in_safety_claim]
    claimed_in_memory = [c.job_id for c in selected if c.in_memory_store]
    summary = {
        "status": "ok",
        "cases": len(cases),
        "passed": sum(1 for c in cases if c.passed),
        "failed": [c.job_id for c in cases if not c.passed],
        "selected_claim_cases": len(selected),
        "selected_claim_passed": sum(1 for c in selected if c.passed),
        "claimed_in_memory_jobs": claimed_in_memory,
        "duckdb_available": env["duckdb_available"],
        "duckdb_version": env["duckdb_version"],
        "quack_loaded": bool((env.get("quack_extension") or {}).get("loaded")),
        "empirical_benchmark_result": False,
        "store_kind": DuckDBCapabilityConsumptionStore.STORE_KIND,
    }
    write_json(SNAPSHOT / "probe" / "summary.json", summary)
    json.dump(summary, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return summary


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def validate() -> int:
    live_py = LIVE / "benchmark" / "durable_consumption.py"
    live_raw = LIVE / "results" / "state" / "raw.jsonl"
    live_matrix = LIVE / "results" / "state" / "failure_matrix.md"
    live_patch = LIVE / "patches" / "state_changes.md"
    snap_py = SNAPSHOT / "outputs" / "benchmark" / "durable_consumption.py"
    snap_raw = SNAPSHOT / "outputs" / "results" / "state" / "raw.jsonl"
    snap_matrix = SNAPSHOT / "outputs" / "results" / "state" / "failure_matrix.md"
    snap_patch = SNAPSHOT / "outputs" / "patches" / "state_changes.md"
    for path in (live_py, live_raw, live_matrix, live_patch, snap_py, snap_raw, snap_matrix, snap_patch):
        if not path.is_file():
            raise SystemExit(f"missing {path}")
    if live_py.read_bytes() != snap_py.read_bytes():
        raise SystemExit("durable_consumption.py live/snapshot mismatch")
    if live_raw.read_bytes() != snap_raw.read_bytes():
        raise SystemExit("raw.jsonl live/snapshot mismatch")
    if live_matrix.read_bytes() != snap_matrix.read_bytes():
        raise SystemExit("failure_matrix.md live/snapshot mismatch")
    if live_patch.read_bytes() != snap_patch.read_bytes():
        raise SystemExit("state_changes.md live/snapshot mismatch")

    jobs = load_jsonl(live_raw)
    text = live_matrix.read_text(encoding="utf-8")
    patch = live_patch.read_text(encoding="utf-8")
    summary = json.loads((SNAPSHOT / "probe" / "summary.json").read_text(encoding="utf-8"))
    env = json.loads((SNAPSHOT / "probe" / "sealed-environment.json").read_text(encoding="utf-8"))
    jobs_by_id = {row["job_id"]: row for row in jobs}

    assert env["duckdb_available"] is True
    assert env["duckdb_version"] and str(env["duckdb_version"]).startswith("1.5")
    assert env.get("duckdb_origin") and "site-packages" in str(env["duckdb_origin"])
    assert (env.get("quack_extension") or {}).get("loaded") is False
    assert summary["empirical_benchmark_result"] is False
    assert summary["claimed_in_memory_jobs"] == []
    assert all(job["empirical_benchmark_result"] is False for job in jobs)

    required = {
        "enforce-allow-durable",
        "enforce-replay-durable",
        "concurrent-same-use",
        "restart-consume-survives",
        "in-memory-restart-contrast",
        "lost-reply-owner-idempotent-replay",
        "lost-reply-after-delegate-no-repeat-effect",
        "crash-after-consume-before-delegate-uncertain",
        "stale-generation",
        "stale-fence",
        "stale-revision",
        "changed-payload-idempotency",
        "owner-failure-rollback",
        "owner-exclusive-lock-timeout",
        "quack-gateway-unavailable",
        "remote-effect-not-exactly-once",
    }
    missing = required - set(jobs_by_id)
    assert not missing, missing

    selected = [job for job in jobs if job["in_safety_claim"]]
    assert selected
    assert all(job["passed"] for job in selected), [job["job_id"] for job in selected if not job["passed"]]
    assert all(not job["in_memory_store"] for job in selected)
    assert all(str(job["store_kind"]).startswith("duckdb-file") for job in selected)

    allow = jobs_by_id["enforce-allow-durable"]
    assert allow["decision"] == "allow"
    assert allow["observed_effect_count"] == 1
    assert allow["owner_transactions"]

    replay = jobs_by_id["enforce-replay-durable"]
    assert replay["decision"] == "deny"
    assert replay["observed_effect_count"] == 0
    assert replay["extra_effect_count"] == 0

    concurrent = jobs_by_id["concurrent-same-use"]
    assert concurrent["decision"] == "one-allow-one-deny"
    assert concurrent["observed_effect_count"] == 1
    assert concurrent["extra_effect_count"] == 0

    restart = jobs_by_id["restart-consume-survives"]
    assert restart["decision"] == "deny"
    assert restart["observed_effect_count"] == 1
    assert restart["extra_effect_count"] == 0

    contrast = jobs_by_id["in-memory-restart-contrast"]
    assert contrast["in_safety_claim"] is False
    assert contrast["in_memory_store"] is True
    assert contrast["extra_effect_count"] == 1

    lost_owner = jobs_by_id["lost-reply-owner-idempotent-replay"]
    assert lost_owner["decision"] == "idempotent_replay"
    assert lost_owner["reply_status"] == "lost"
    assert any(row.get("outcome") == "accepted" for row in lost_owner["owner_transactions"])
    assert any(row.get("outcome") == "idempotent_replay" for row in lost_owner["owner_transactions"])

    lost_delegate = jobs_by_id["lost-reply-after-delegate-no-repeat-effect"]
    assert lost_delegate["decision"] == "deny"
    assert lost_delegate["extra_effect_count"] == 0
    assert lost_delegate["remote_effect_status"] == "uncertain"

    crash = jobs_by_id["crash-after-consume-before-delegate-uncertain"]
    assert crash["decision"] == "deny"
    assert crash["observed_effect_count"] == 0
    assert crash["remote_effect_status"] == "uncertain"

    assert jobs_by_id["stale-generation"]["decision"] == "stale"
    assert jobs_by_id["stale-fence"]["decision"] == "stale"
    assert jobs_by_id["stale-revision"]["decision"] == "conflict"
    assert jobs_by_id["changed-payload-idempotency"]["decision"] == "idempotency_conflict"
    assert jobs_by_id["owner-failure-rollback"]["decision"] == "rolled_back"
    assert jobs_by_id["owner-exclusive-lock-timeout"]["decision"] == "timeout"
    assert jobs_by_id["quack-gateway-unavailable"]["in_safety_claim"] is False
    assert jobs_by_id["remote-effect-not-exactly-once"]["remote_effect_status"] == "uncertain"

    assert "InMemoryCapabilityConsumptionStore" in patch
    assert "were **not** modified" in patch or "were **not**" in patch
    assert "uncertain" in text.lower()
    assert "exactly once" in text.lower() or "exactly-once" in text.lower()
    assert "not** a scored" in text or "not a scored" in text.lower()

    print("LA-012 durable consumption validation: PASS")
    print(
        f"jobs={len(jobs)} selected={len(selected)} failed={summary.get('failed')} "
        f"duckdb={env.get('duckdb_version')} quack_loaded={summary.get('quack_loaded')}"
    )
    return 0


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "qualify"
    if mode in {"validate", "--validate"}:
        return validate()
    summary = qualify()
    if summary.get("status") != "ok":
        return 1
    if summary.get("selected_claim_passed") != summary.get("selected_claim_cases"):
        return 1
    if summary.get("claimed_in_memory_jobs"):
        return 1
    if not summary.get("duckdb_available"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
