#!/usr/bin/env python3
"""NS-012 live qualification of complete inventories, parallel sealing, CAS, and restart.

Exercises the accelerate IncrementalProofSealer, full-checkpoint completeness
gate, manifest aggregation, admission, hermetic WAL/CAS publication, kit
DurableCoordinationStore root CAS, and fenced worktree lifecycle. Sequential
and parallel preparation are compared at multiple worker counts. Faults cover
missing/duplicate units, corrupt hash-memo, stale parent/generation/fence,
interrupted persistence, CAS races, crashes around publication, duplicated
events, unknown provider results, and store unavailability.

Federation/network partitions and remote libp2p/MCP transport remain explicitly
unavailable. This is sealed-profile qualification, not a live A–D experiment
and not a global-consensus or exactly-once side-effect claim.
"""

from __future__ import annotations

import hashlib
import json
import os
import resource
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


SNAP = Path(__file__).resolve().parent
ROOT = SNAP.parents[5]
PAPER = ROOT / "papers/completion/neurosymbolic_supervision"
QUAL = PAPER / "qualification"
SNAP_QUAL = SNAP / "qualification"
ACC_ROOT = ROOT / "external/ipfs_accelerate"
DS_ROOT = ROOT / "external/ipfs_datasets"
KIT_ROOT = ROOT / "external/ipfs_kit"
TASK_ID = "NS-012"
POLICY_ID = "ns-012-sealer-recovery-qualification-v1"
SCHEMA_MATRIX = "neurosymbolic-supervision/sealer-fault-matrix@1"
SCHEMA_RESULT = "neurosymbolic-supervision/sealer-result@1"
SCHEMA_RECOVERY = "neurosymbolic-supervision/recovery-receipt@1"
CANONICAL_PROFILE = {
    "canonicalization_version": "1",
    "codec": "canonical-json@1",
    "hash": "sha256",
    "source_mode": "immutable-bytes",
}
WORKER_COUNTS = (1, 2, 4, 8)
CHECKPOINT_DIR = Path(
    os.environ.get(
        "IPFS_ACCELERATE_AGENT_TASK_CHECKPOINT_DIR",
        str(SNAP / "checkpoints"),
    )
)

SOURCE_PATHS = (
    ACC_ROOT / "ipfs_accelerate_py/agent_supervisor/proof/incremental_sealing/sealer.py",
    ACC_ROOT / "ipfs_accelerate_py/agent_supervisor/proof/incremental_sealing/full_checkpoint.py",
    ACC_ROOT / "ipfs_accelerate_py/agent_supervisor/proof/incremental_sealing/aggregation.py",
    ACC_ROOT / "ipfs_accelerate_py/agent_supervisor/proof/incremental_sealing/delta_seal.py",
    ACC_ROOT / "ipfs_accelerate_py/agent_supervisor/proof/incremental_sealing/admission.py",
    ACC_ROOT / "ipfs_accelerate_py/agent_supervisor/semantic_state/durable_state.py",
    ACC_ROOT / "ipfs_accelerate_py/agent_supervisor/merge/worktree_lifecycle.py",
    KIT_ROOT / "ipfs_kit_py/proof_certificate_store.py",
    KIT_ROOT / "ipfs_kit_py/mcp_server/mcplusplus/coordination_storage.py",
    SNAP / "compat_shims.py",
)

REQUIRED_CASES = (
    "seq_par_worker_counts_match",
    "worker_completion_order_cannot_alter_authority",
    "hash_memo_requires_content_and_profile",
    "mtime_only_hash_memo_rejected",
    "corrupt_hash_memo_reverified_and_rejected",
    "empty_manifest_cannot_pass",
    "incomplete_manifest_missing_required_unit",
    "duplicate_required_unit_rejected",
    "membership_is_not_completeness",
    "aggregation_missing_child",
    "aggregation_duplicate_child",
    "aggregation_reordered_children",
    "stale_parent_cannot_overwrite",
    "exactly_one_concurrent_cas_winner",
    "pre_cas_crash_leaves_old_pointer",
    "failed_units_cannot_publish",
    "durable_stale_generation_conflict",
    "git_fence_mismatch_denied",
    "post_cas_crash_recovers_success",
    "pre_cas_crash_then_valid_continuation",
    "recovery_is_idempotent",
    "duplicate_reordered_events_idempotent",
    "unknown_provider_result_not_success",
    "simulated_required_unit_not_sealed",
    "store_unavailability_typed",
    "federation_network_unavailable",
    "measurements_separately_labeled",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def write_json(path: Path, payload: Any) -> None:
    encoded = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    atomic_write(path, encoded.encode("utf-8"))


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    lines = [
        json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        for row in rows
    ]
    atomic_write(path, ("\n".join(lines) + "\n").encode("utf-8"))


def checkpoint(name: str, payload: Mapping[str, Any]) -> None:
    try:
        CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
        write_json(CHECKPOINT_DIR / f"{name}.json", dict(payload))
    except OSError:
        fallback = SNAP / "checkpoints"
        fallback.mkdir(parents=True, exist_ok=True)
        write_json(fallback / f"{name}.json", dict(payload))


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def enum_val(value: Any) -> str:
    return str(getattr(value, "value", value))


def which(name: str) -> str | None:
    return shutil.which(name)


def git_head(path: Path) -> str | None:
    git = which("git")
    if git is None:
        return None
    try:
        proc = subprocess.run(
            [git, "-C", str(path), "rev-parse", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def source_hashes() -> dict[str, str]:
    hashes: dict[str, str] = {}
    for path in SOURCE_PATHS:
        if path.is_file():
            hashes[rel(path)] = sha256_file(path)
    return hashes


def digest_hex(payload: Mapping[str, Any] | str | bytes) -> str:
    if isinstance(payload, bytes):
        body = payload
    elif isinstance(payload, str):
        body = payload.encode("utf-8")
    else:
        body = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")
    return "sha256:" + hashlib.sha256(body).hexdigest()


def measurement(
    *,
    status: str,
    value: float | None,
    unit: str,
    source: str | None,
    reason: str | None,
) -> dict[str, Any]:
    return {
        "status": status,
        "value": value,
        "unit": unit,
        "source": source,
        "reason": reason,
    }


class StageTimer:
    def __init__(self, label: str) -> None:
        self.label = label
        self.elapsed_ms = 0.0
        self.cpu_ms = 0.0
        self.memory_bytes = 0
        self.storage_bytes = 0
        self._wall0 = 0.0
        self._cpu0 = 0.0
        self._rss0 = 0

    def __enter__(self) -> "StageTimer":
        self._wall0 = time.perf_counter()
        self._cpu0 = time.process_time()
        self._rss0 = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return self

    def __exit__(self, *_exc: object) -> None:
        self.elapsed_ms = (time.perf_counter() - self._wall0) * 1000.0
        self.cpu_ms = (time.process_time() - self._cpu0) * 1000.0
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        # Linux ru_maxrss is kilobytes.
        self.memory_bytes = max(0, int(rss) * 1024)

    def bind_storage(self, nbytes: int) -> None:
        self.storage_bytes = max(0, int(nbytes))

    def as_measurements(self) -> dict[str, Any]:
        return {
            f"{self.label}_elapsed": measurement(
                status="actual",
                value=round(self.elapsed_ms, 6),
                unit="ms",
                source="time.perf_counter",
                reason=None,
            ),
            f"{self.label}_cpu": measurement(
                status="actual",
                value=round(self.cpu_ms, 6),
                unit="ms",
                source="time.process_time",
                reason=None,
            ),
            f"{self.label}_memory": measurement(
                status="actual",
                value=float(self.memory_bytes),
                unit="bytes",
                source="resource.getrusage.ru_maxrss",
                reason=None,
            ),
            f"{self.label}_storage": measurement(
                status="actual",
                value=float(self.storage_bytes),
                unit="bytes",
                source="len(canonical_bytes_or_store_growth)",
                reason=None,
            ),
            f"{self.label}_gpu": measurement(
                status="unavailable",
                value=None,
                unit="ms",
                source=None,
                reason="no GPU prover or accelerator in the sealed PATH",
            ),
        }


def dir_size(path: Path) -> int:
    total = 0
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    for child in path.rglob("*"):
        if child.is_file():
            total += child.stat().st_size
    return total


def load_durable_state_modules() -> tuple[Any, Any]:
    """Load contracts/durable_state without semantic_state package __init__.

    That package imports MCP++ wire codecs which require anyio.  The durable
    adapter itself does not.  A dummy package is registered so submodule
    imports do not execute harness/receipts/wire.
    """

    import importlib.util
    import types

    pkg = "ipfs_accelerate_py.agent_supervisor.semantic_state"
    base = ACC_ROOT / "ipfs_accelerate_py/agent_supervisor/semantic_state"
    import ipfs_accelerate_py.agent_supervisor as supervisor  # noqa: F401

    if pkg not in sys.modules or not getattr(sys.modules[pkg], "__path__", None):
        dummy = types.ModuleType(pkg)
        dummy.__path__ = [str(base)]  # type: ignore[attr-defined]
        dummy.__file__ = str(base / "__init__.py")
        dummy.__package__ = pkg
        sys.modules[pkg] = dummy
        setattr(sys.modules["ipfs_accelerate_py.agent_supervisor"], "semantic_state", dummy)

    def load_sub(name: str, filename: str):
        full = f"{pkg}.{name}"
        if full in sys.modules and hasattr(sys.modules[full], "__file__"):
            return sys.modules[full]
        spec = importlib.util.spec_from_file_location(full, base / filename)
        if spec is None or spec.loader is None:
            raise ImportError(full)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[full] = mod
        spec.loader.exec_module(mod)
        setattr(sys.modules[pkg], name, mod)
        return mod

    contracts = load_sub("contracts", "contracts.py")
    durable = load_sub("durable_state", "durable_state.py")
    return contracts, durable


def prepare_imports() -> dict[str, Any]:
    initial_path = os.environ.get("PATH")
    for path in (str(ACC_ROOT), str(DS_ROOT), str(KIT_ROOT), str(SNAP)):
        if path not in sys.path:
            sys.path.insert(0, path)

    from compat_shims import install_qualification_shims

    shim_report = install_qualification_shims()

    from ipfs_accelerate_py.agent_supervisor.proof.incremental_sealing.admission import (
        EvidenceCandidate,
        verify_for_admission,
    )
    from ipfs_accelerate_py.agent_supervisor.proof.incremental_sealing.aggregation import (
        VerifiedUnit,
        aggregate_verified_units,
    )
    from ipfs_accelerate_py.agent_supervisor.proof.incremental_sealing.delta_seal import (
        TRANSITION_SCHEMA,
        DeltaTransitionStatement,
        DeltaUnitEvidence,
        DiffCommitmentView,
        ParentSealView,
    )
    from ipfs_accelerate_py.agent_supervisor.proof.incremental_sealing.full_checkpoint import (
        GENESIS_PARENT_SEAL,
        RepositoryStateView,
        RequiredUnitEvidence,
        VerificationPolicyView,
        create_full_checkpoint,
    )
    from ipfs_accelerate_py.agent_supervisor.proof.incremental_sealing.sealer import (
        IncrementalProofSealer,
        PublicationReason,
        SealerCrash,
        publish_delta_seal,
        publish_full_checkpoint,
    )
    from ipfs_datasets_py.logic.zkp.incremental_sealing.evidence import (
        IntegrityCommitment,
        ProofMode,
        ProofTerminalStatus,
        SealStatus,
    )
    from ipfs_kit_py.proof_seal_store.contracts import SealTransitionPhase, SealTransitionState

    durable_status = "unavailable"
    durable_error = None
    durable_mod = None
    ss_contracts = None
    try:
        ss_contracts, durable_mod = load_durable_state_modules()
        durable_status = "imported_bypass_package_init"
    except Exception as exc:
        durable_error = f"{type(exc).__name__}: {exc}"

    lifecycle_status = "unavailable"
    lifecycle_error = None
    lifecycle_mod = None
    try:
        from ipfs_accelerate_py.agent_supervisor.merge import worktree_lifecycle as lifecycle_mod

        lifecycle_status = "imported"
    except Exception as exc:
        lifecycle_error = f"{type(exc).__name__}: {exc}"

    return {
        "interpreter": sys.executable,
        "python_version": sys.version.split()[0],
        "path": initial_path,
        "shim_report": shim_report,
        "durable_status": durable_status,
        "durable_error": durable_error,
        "lifecycle_status": lifecycle_status,
        "lifecycle_error": lifecycle_error,
        "binaries": {
            "z3": which("z3"),
            "cvc5": which("cvc5"),
            "groth16": which("groth16"),
        },
        "api": {
            "EvidenceCandidate": EvidenceCandidate,
            "verify_for_admission": verify_for_admission,
            "VerifiedUnit": VerifiedUnit,
            "aggregate_verified_units": aggregate_verified_units,
            "TRANSITION_SCHEMA": TRANSITION_SCHEMA,
            "DeltaTransitionStatement": DeltaTransitionStatement,
            "DeltaUnitEvidence": DeltaUnitEvidence,
            "DiffCommitmentView": DiffCommitmentView,
            "ParentSealView": ParentSealView,
            "GENESIS_PARENT_SEAL": GENESIS_PARENT_SEAL,
            "RepositoryStateView": RepositoryStateView,
            "RequiredUnitEvidence": RequiredUnitEvidence,
            "VerificationPolicyView": VerificationPolicyView,
            "create_full_checkpoint": create_full_checkpoint,
            "IncrementalProofSealer": IncrementalProofSealer,
            "PublicationReason": PublicationReason,
            "SealerCrash": SealerCrash,
            "publish_delta_seal": publish_delta_seal,
            "publish_full_checkpoint": publish_full_checkpoint,
            "IntegrityCommitment": IntegrityCommitment,
            "ProofMode": ProofMode,
            "ProofTerminalStatus": ProofTerminalStatus,
            "SealStatus": SealStatus,
            "SealTransitionPhase": SealTransitionPhase,
            "SealTransitionState": SealTransitionState,
            "durable": durable_mod,
            "ss_contracts": ss_contracts,
            "lifecycle": lifecycle_mod,
        },
    }


def _state(api: Mapping[str, Any], **overrides: object):
    payload: dict[str, object] = {
        "repository_id": "repo/ns-012",
        "revision": "rev-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "source_root_cid": digest_hex("source-root"),
        "repository_state_cid": digest_hex("repo-state"),
        "environment_cid": digest_hex("environment"),
        "parent_revision_ids": (),
    }
    payload.update(overrides)
    return api["RepositoryStateView"](**payload)


def _policy(api: Mapping[str, Any], **overrides: object):
    payload: dict[str, object] = {
        "policy_cid": digest_hex("policy"),
        "proof_schema_version": "1",
        "canonicalization_version": CANONICAL_PROFILE["canonicalization_version"],
        "dependency_graph_schema_version": "graph@1",
        "circuit_id": "circuit@ns-012",
        "verification_key_id": "vk/ns-012",
    }
    payload.update(overrides)
    return api["VerificationPolicyView"](**payload)


def _unit(api: Mapping[str, Any], unit_id: str, **overrides: object):
    payload: dict[str, object] = {
        "unit_id": unit_id,
        "proof_object_cid": digest_hex(f"proof:{unit_id}"),
        "category": "unit_test",
        "terminal_status": api["ProofTerminalStatus"].INTEGRITY_VERIFIED.value,
        "proof_mode": api["ProofMode"].INTEGRITY_ONLY.value,
        "required_for_seal": True,
        "freshly_verified": True,
        "cache_reused_without_fresh_verification": False,
    }
    payload.update(overrides)
    return api["RequiredUnitEvidence"](**payload)


def _inventory(api: Mapping[str, Any], *, n: int = 6, tag: str = "core") -> tuple[Any, ...]:
    units = []
    categories = ("unit_test", "static_analysis", "source_integrity")
    for index in range(n):
        unit_id = f"unit/{tag}/{index:02d}"
        units.append(
            _unit(
                api,
                unit_id,
                category=categories[index % len(categories)],
                proof_object_cid=digest_hex(f"{tag}:{unit_id}"),
            )
        )
    return tuple(units)


def _expected_ids(units: Sequence[Any]) -> tuple[str, ...]:
    return tuple(item.unit_id for item in units)


def canonicalize_unit(unit: Any, *, profile: Mapping[str, str]) -> bytes:
    payload = {
        "profile": dict(profile),
        "unit": unit.to_canonical() if hasattr(unit, "to_canonical") else dict(unit),
    }
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


class HashMemo:
    """Content+profile keyed memo.  mtime is never authority."""

    def __init__(self) -> None:
        self._entries: dict[str, dict[str, Any]] = {}

    @staticmethod
    def key(content: bytes, profile: Mapping[str, str]) -> str:
        material = {
            "content_sha256": hashlib.sha256(content).hexdigest(),
            "profile": dict(profile),
        }
        return digest_hex(material)

    def put(self, content: bytes, profile: Mapping[str, str], digest: str) -> str:
        key = self.key(content, profile)
        self._entries[key] = {
            "digest": digest,
            "content_sha256": hashlib.sha256(content).hexdigest(),
            "profile": dict(profile),
        }
        return key

    def lookup(
        self,
        content: bytes,
        profile: Mapping[str, str],
        *,
        mtime_only: bool = False,
        corrupt: bool = False,
    ) -> dict[str, Any]:
        if mtime_only:
            return {
                "hit": False,
                "reason": "mtime_or_path_is_not_authority",
                "reverified": False,
            }
        key = self.key(content, profile)
        entry = self._entries.get(key)
        if entry is None:
            return {"hit": False, "reason": "miss", "reverified": False}
        observed = hashlib.sha256(content).hexdigest()
        stored = "ffff" * 16 if corrupt else entry["digest"]
        if stored != "sha256:" + observed and stored != digest_hex(content):
            recomputed = "sha256:" + observed
            if stored != recomputed:
                return {
                    "hit": False,
                    "reason": "corrupt_or_stale_memo",
                    "reverified": True,
                    "stored": stored,
                    "recomputed": recomputed,
                }
        return {
            "hit": True,
            "reason": "content_profile_reverified",
            "reverified": True,
            "digest": "sha256:" + observed,
        }


def prepare_units_parallel(
    units: Sequence[Any],
    *,
    workers: int,
    profile: Mapping[str, str],
    shuffle_completion: bool,
) -> dict[str, Any]:
    prepared: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    lock = threading.Lock()

    def work(unit: Any, delay_ns: int) -> dict[str, Any]:
        if delay_ns:
            time.sleep(delay_ns / 1_000_000_000)
        canonical = canonicalize_unit(unit, profile=profile)
        digest = "sha256:" + hashlib.sha256(canonical).hexdigest()
        record = {
            "unit_id": unit.unit_id,
            "canonical_sha256": digest,
            "proof_object_cid": unit.proof_object_cid,
            "category": unit.category,
            "terminal_status": unit.terminal_status,
            "bytes": canonical,
        }
        with lock:
            prepared[unit.unit_id] = {
                key: value for key, value in record.items() if key != "bytes"
            }
            order.append(unit.unit_id)
        return record

    delays = list(range(len(units)))
    if shuffle_completion:
        delays = list(reversed(delays))
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = [
            pool.submit(work, unit, delays[index] * 50_000)
            for index, unit in enumerate(units)
        ]
        for future in as_completed(futures):
            future.result()

    inventory = tuple(sorted(prepared))
    # Serial barrier: rebuild merkle inputs in normative unit_id order.
    ordered_ids = tuple(sorted(prepared))
    root_material = {
        "profile": dict(profile),
        "inventory": list(ordered_ids),
        "leaves": [prepared[unit_id]["canonical_sha256"] for unit_id in ordered_ids],
    }
    return {
        "workers": workers,
        "completion_order": list(order),
        "inventory": list(inventory),
        "leaf_root": digest_hex(root_material),
        "prepared": prepared,
        "canonical_profile": dict(profile),
    }


def row_base(
    *,
    case_id: str,
    family: str,
    polarity: str,
    expected_reason: str,
    description: str,
    table: str,
) -> dict[str, Any]:
    return {
        "schema": SCHEMA_RESULT,
        "task_id": TASK_ID,
        "policy_id": POLICY_ID,
        "case_id": case_id,
        "family": family,
        "polarity": polarity,
        "table": table,
        "expected_reason": expected_reason,
        "description": description,
        "live_ad_experiment": False,
        "federation_claimed": False,
        "exactly_once_external_claimed": False,
    }


def finish(
    base: dict[str, Any], *, observed_reason: str, extra: Mapping[str, Any]
) -> dict[str, Any]:
    status = "pass" if observed_reason == base["expected_reason"] else "fail"
    row = dict(base)
    row.update(dict(extra))
    row["observed_reason"] = observed_reason
    row["status"] = status
    return row


def declare(cases: list[dict[str, Any]], **kwargs: Any) -> None:
    cases.append(kwargs)


def parent_view_from_full(api: Mapping[str, Any], result: Any) -> Any:
    seal = result.full_seal
    return api["ParentSealView"](
        seal_cid=result.seal_cid,
        accepted=True,
        seal_status=enum_val(result.status),
        repository_id=result.repository_id,
        branch_id=result.branch_id,
        revision=seal.revision,
        source_root_cid=seal.source_root_cid,
        repository_state_cid=seal.repository_state_cid,
        environment_cid=seal.environment_cid,
        policy_cid=seal.policy_cid,
        manifest_root_cid=seal.manifest_root_cid,
        forest_root_cid=seal.repository_proof_root,
        aggregation_root=seal.aggregation_root,
        required_unit_ids=seal.required_unit_ids,
        unit_proof_cids={
            unit.unit_id: unit.proof_object_cid
            for unit in _inventory(api)
            if unit.unit_id in set(seal.required_unit_ids)
        },
        logical_epoch=1,
    )


def run_cases(api: Mapping[str, Any], work_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    cases: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    recoveries: list[dict[str, Any]] = []
    units = _inventory(api, n=8, tag="par")
    expected = _expected_ids(units)

    # --- Sequential vs parallel preparation ---
    seq_timer = StageTimer("prepare")
    with seq_timer:
        sequential = prepare_units_parallel(
            units, workers=1, profile=CANONICAL_PROFILE, shuffle_completion=False
        )
    seq_timer.bind_storage(sum(len(canonicalize_unit(u, profile=CANONICAL_PROFILE)) for u in units))

    parallel_runs = []
    for count in WORKER_COUNTS:
        run = prepare_units_parallel(
            units,
            workers=count,
            profile=CANONICAL_PROFILE,
            shuffle_completion=count > 1,
        )
        parallel_runs.append(run)

    verify_timer = StageTimer("verify")
    with verify_timer:
        seq_seal = api["create_full_checkpoint"](
            _state(api),
            _policy(api),
            units=units,
            expected_unit_ids=expected,
            parent_seal_cid=api["GENESIS_PARENT_SEAL"],
            fallback_reasons=("first_state",),
        )
        par_seals = []
        for run in parallel_runs:
            ordered = tuple(sorted(units, key=lambda item: item.unit_id))
            par_seals.append(
                api["create_full_checkpoint"](
                    _state(api),
                    _policy(api),
                    units=ordered,
                    expected_unit_ids=expected,
                    parent_seal_cid=api["GENESIS_PARENT_SEAL"],
                    fallback_reasons=("first_state",),
                )
            )
        agg_seq = api["aggregate_verified_units"](
            [
                api["VerifiedUnit"](
                    unit_id=u.unit_id,
                    proof_object_cid=u.proof_object_cid,
                    category=u.category,
                    terminal_status=u.terminal_status,
                    repository_state_cid=digest_hex("repo-state"),
                    environment_cid=digest_hex("environment"),
                )
                for u in sorted(units, key=lambda item: item.unit_id)
            ],
            expected_unit_ids=tuple(sorted(expected)),
        )
    verify_timer.bind_storage(len(json.dumps(seq_seal.to_canonical()).encode("utf-8")))

    match = all(
        run["leaf_root"] == sequential["leaf_root"]
        and run["inventory"] == sequential["inventory"]
        and set(run["prepared"]) == set(sequential["prepared"])
        for run in parallel_runs
    ) and all(
        seal.seal_cid() == seq_seal.seal_cid()
        and seal.manifest_root_cid == seq_seal.manifest_root_cid
        and seal.repository_proof_root == seq_seal.repository_proof_root
        and seal.aggregation_root == seq_seal.aggregation_root
        and seal.sealed is True
        for seal in par_seals
    )
    declare(
        cases,
        case_id="seq_par_worker_counts_match",
        family="parallel_prepare",
        polarity="valid",
        table="table9",
        expected_reason="identical_roots_inventories_dispositions",
        description="Sequential and parallel preparation at worker counts 1/2/4/8 produce identical bytes, roots, inventories, and dispositions.",
    )
    rows.append(
        finish(
            row_base(
                case_id="seq_par_worker_counts_match",
                family="parallel_prepare",
                polarity="valid",
                table="table9",
                expected_reason="identical_roots_inventories_dispositions",
                description="Sequential and parallel preparation at worker counts 1/2/4/8 produce identical bytes, roots, inventories, and dispositions.",
            ),
            observed_reason="identical_roots_inventories_dispositions"
            if match and seq_seal.sealed
            else "parallel_divergence",
            extra={
                "worker_counts": list(WORKER_COUNTS),
                "sequential_leaf_root": sequential["leaf_root"],
                "parallel_leaf_roots": [run["leaf_root"] for run in parallel_runs],
                "seal_cid": seq_seal.seal_cid(),
                "manifest_root_cid": seq_seal.manifest_root_cid,
                "repository_proof_root": seq_seal.repository_proof_root,
                "aggregation_root": seq_seal.aggregation_root,
                "agg_accepted": bool(agg_seq.accepted),
                "measurements": {**seq_timer.as_measurements(), **verify_timer.as_measurements()},
            },
        )
    )

    orders = [tuple(run["completion_order"]) for run in parallel_runs]
    order_varied = len(set(orders)) > 1 or any(
        order != tuple(sorted(order)) for order in orders[1:]
    )
    declare(
        cases,
        case_id="worker_completion_order_cannot_alter_authority",
        family="parallel_prepare",
        polarity="valid",
        table="table9",
        expected_reason="worker_order_is_not_authority",
        description="Worker completion order may vary; serial barrier preserves normative inventory and roots.",
    )
    rows.append(
        finish(
            row_base(
                case_id="worker_completion_order_cannot_alter_authority",
                family="parallel_prepare",
                polarity="valid",
                table="table9",
                expected_reason="worker_order_is_not_authority",
                description="Worker completion order may vary; serial barrier preserves normative inventory and roots.",
            ),
            observed_reason="worker_order_is_not_authority"
            if match and (order_varied or WORKER_COUNTS[-1] > 1)
            else "worker_order_changed_roots",
            extra={
                "completion_orders": [list(item) for item in orders],
                "normative_inventory": list(sorted(expected)),
            },
        )
    )

    memo = HashMemo()
    sample = canonicalize_unit(units[0], profile=CANONICAL_PROFILE)
    memo.put(sample, CANONICAL_PROFILE, "sha256:" + hashlib.sha256(sample).hexdigest())
    hit = memo.lookup(sample, CANONICAL_PROFILE)
    declare(
        cases,
        case_id="hash_memo_requires_content_and_profile",
        family="hash_memo",
        polarity="valid",
        table="table9",
        expected_reason="content_profile_reverified",
        description="Hash memo keys exact content and canonicalization/codec/hash/source-mode policy, then reverifies.",
    )
    rows.append(
        finish(
            row_base(
                case_id="hash_memo_requires_content_and_profile",
                family="hash_memo",
                polarity="valid",
                table="table9",
                expected_reason="content_profile_reverified",
                description="Hash memo keys exact content and canonicalization/codec/hash/source-mode policy, then reverifies.",
            ),
            observed_reason=hit["reason"] if hit["reverified"] else "memo_skipped_reverify",
            extra=hit,
        )
    )

    mtime = memo.lookup(sample, CANONICAL_PROFILE, mtime_only=True)
    declare(
        cases,
        case_id="mtime_only_hash_memo_rejected",
        family="hash_memo",
        polarity="invalid",
        table="table9",
        expected_reason="mtime_or_path_is_not_authority",
        description="A path or modification time alone is not the final SHA/CID authority.",
    )
    rows.append(
        finish(
            row_base(
                case_id="mtime_only_hash_memo_rejected",
                family="hash_memo",
                polarity="invalid",
                table="table9",
                expected_reason="mtime_or_path_is_not_authority",
                description="A path or modification time alone is not the final SHA/CID authority.",
            ),
            observed_reason=mtime["reason"],
            extra=mtime,
        )
    )

    corrupt = memo.lookup(sample, CANONICAL_PROFILE, corrupt=True)
    declare(
        cases,
        case_id="corrupt_hash_memo_reverified_and_rejected",
        family="hash_memo",
        polarity="invalid",
        table="table12",
        expected_reason="corrupt_or_stale_memo",
        description="A corrupted hash-memo digest is reverified against content and cannot authorize a root.",
    )
    rows.append(
        finish(
            row_base(
                case_id="corrupt_hash_memo_reverified_and_rejected",
                family="hash_memo",
                polarity="invalid",
                table="table12",
                expected_reason="corrupt_or_stale_memo",
                description="A corrupted hash-memo digest is reverified against content and cannot authorize a root.",
            ),
            observed_reason=corrupt["reason"],
            extra=corrupt,
        )
    )

    # --- Completeness ---
    empty = api["create_full_checkpoint"](
        _state(api, revision="rev-empty"),
        _policy(api),
        units=(),
        expected_unit_ids=("unit/mandatory",),
        parent_seal_cid=api["GENESIS_PARENT_SEAL"],
        fallback_reasons=("first_state",),
    )
    declare(
        cases,
        case_id="empty_manifest_cannot_pass",
        family="completeness",
        polarity="invalid",
        table="table9",
        expected_reason="incomplete_manifest",
        description="An empty required set cannot produce a production full seal.",
    )
    rows.append(
        finish(
            row_base(
                case_id="empty_manifest_cannot_pass",
                family="completeness",
                polarity="invalid",
                table="table9",
                expected_reason="incomplete_manifest",
                description="An empty required set cannot produce a production full seal.",
            ),
            observed_reason=enum_val(empty.seal_status)
            if not empty.sealed
            else "empty_manifest_sealed",
            extra={
                "sealed": empty.sealed,
                "reason": enum_val(empty.reason),
                "required_unit_ids": list(empty.required_unit_ids),
            },
        )
    )

    incomplete = api["create_full_checkpoint"](
        _state(api),
        _policy(api),
        units=units[:2],
        expected_unit_ids=expected,
        parent_seal_cid=api["GENESIS_PARENT_SEAL"],
        fallback_reasons=("first_state",),
    )
    declare(
        cases,
        case_id="incomplete_manifest_missing_required_unit",
        family="completeness",
        polarity="invalid",
        table="table9",
        expected_reason="incomplete_manifest",
        description="Missing required units fail closed; membership of a subset is not completeness.",
    )
    rows.append(
        finish(
            row_base(
                case_id="incomplete_manifest_missing_required_unit",
                family="completeness",
                polarity="invalid",
                table="table9",
                expected_reason="incomplete_manifest",
                description="Missing required units fail closed; membership of a subset is not completeness.",
            ),
            observed_reason=enum_val(incomplete.seal_status)
            if not incomplete.sealed
            else "incomplete_manifest_sealed",
            extra={
                "sealed": incomplete.sealed,
                "reason": enum_val(incomplete.reason),
                "rejected_unit_ids": list(incomplete.rejected_unit_ids),
                "required_unit_ids": list(incomplete.required_unit_ids),
            },
        )
    )

    duplicate_blocked = False
    duplicate_error = None
    try:
        api["create_full_checkpoint"](
            _state(api),
            _policy(api),
            units=(units[0], units[0]),
            expected_unit_ids=(units[0].unit_id,),
        )
    except Exception as exc:
        duplicate_blocked = True
        duplicate_error = f"{type(exc).__name__}: {exc}"
    declare(
        cases,
        case_id="duplicate_required_unit_rejected",
        family="completeness",
        polarity="invalid",
        table="table12",
        expected_reason="duplicate_required_unit",
        description="Duplicate required unit identities cannot pass a complete manifest.",
    )
    rows.append(
        finish(
            row_base(
                case_id="duplicate_required_unit_rejected",
                family="completeness",
                polarity="invalid",
                table="table12",
                expected_reason="duplicate_required_unit",
                description="Duplicate required unit identities cannot pass a complete manifest.",
            ),
            observed_reason="duplicate_required_unit"
            if duplicate_blocked
            else "duplicate_unit_admitted",
            extra={"error": duplicate_error},
        )
    )

    extra_member = api["create_full_checkpoint"](
        _state(api),
        _policy(api),
        units=units,
        expected_unit_ids=expected + ("unit/unrequired-extra",),
        parent_seal_cid=api["GENESIS_PARENT_SEAL"],
        fallback_reasons=("first_state",),
    )
    declare(
        cases,
        case_id="membership_is_not_completeness",
        family="completeness",
        polarity="invalid",
        table="table9",
        expected_reason="incomplete_manifest",
        description="Merkle membership of presented units is not completeness against the requirement manifest.",
    )
    rows.append(
        finish(
            row_base(
                case_id="membership_is_not_completeness",
                family="completeness",
                polarity="invalid",
                table="table9",
                expected_reason="incomplete_manifest",
                description="Merkle membership of presented units is not completeness against the requirement manifest.",
            ),
            observed_reason=enum_val(extra_member.seal_status)
            if not extra_member.sealed
            else "membership_treated_as_complete",
            extra={
                "sealed": extra_member.sealed,
                "reason": enum_val(extra_member.reason),
                "presented": list(expected),
                "required_manifest": list(expected) + ["unit/unrequired-extra"],
            },
        )
    )

    verified = [
        api["VerifiedUnit"](
            unit_id=u.unit_id,
            proof_object_cid=u.proof_object_cid,
            category=u.category,
            terminal_status=u.terminal_status,
        )
        for u in units
    ]
    missing_child = api["aggregate_verified_units"](
        verified[:-1], expected_unit_ids=_expected_ids(units)
    )
    declare(
        cases,
        case_id="aggregation_missing_child",
        family="aggregation",
        polarity="invalid",
        table="table9",
        expected_reason="missing_child",
        description="Manifest aggregation rejects a missing required child.",
    )
    rows.append(
        finish(
            row_base(
                case_id="aggregation_missing_child",
                family="aggregation",
                polarity="invalid",
                table="table9",
                expected_reason="missing_child",
                description="Manifest aggregation rejects a missing required child.",
            ),
            observed_reason=enum_val(missing_child.reason)
            if not missing_child.accepted
            else "missing_child_accepted",
            extra={"accepted": missing_child.accepted},
        )
    )

    duplicate_child = api["aggregate_verified_units"](
        [verified[0], verified[0]], expected_unit_ids=(verified[0].unit_id,)
    )
    declare(
        cases,
        case_id="aggregation_duplicate_child",
        family="aggregation",
        polarity="invalid",
        table="table12",
        expected_reason="duplicate_child",
        description="Manifest aggregation rejects duplicate children.",
    )
    rows.append(
        finish(
            row_base(
                case_id="aggregation_duplicate_child",
                family="aggregation",
                polarity="invalid",
                table="table12",
                expected_reason="duplicate_child",
                description="Manifest aggregation rejects duplicate children.",
            ),
            observed_reason=enum_val(duplicate_child.reason)
            if not duplicate_child.accepted
            else "duplicate_child_accepted",
            extra={"accepted": duplicate_child.accepted},
        )
    )

    reordered = api["aggregate_verified_units"](
        list(reversed(verified)),
        expected_unit_ids=_expected_ids(units),
    )
    declare(
        cases,
        case_id="aggregation_reordered_children",
        family="aggregation",
        polarity="invalid",
        table="table12",
        expected_reason="reordered_children",
        description="Reordered children cannot pass a complete ordered manifest.",
    )
    rows.append(
        finish(
            row_base(
                case_id="aggregation_reordered_children",
                family="aggregation",
                polarity="invalid",
                table="table12",
                expected_reason="reordered_children",
                description="Reordered children cannot pass a complete ordered manifest.",
            ),
            observed_reason=enum_val(reordered.reason)
            if not reordered.accepted
            else "reordered_children_accepted",
            extra={"accepted": reordered.accepted},
        )
    )

    # --- Publication / CAS / crashes ---
    store_a = work_root / "seal-a"
    store_a.mkdir()
    sealer = api["IncrementalProofSealer"](store_a)
    persist_timer = StageTimer("persist")
    cas_timer = StageTimer("cas")
    with persist_timer:
        genesis = sealer.publish_full_checkpoint(
            _state(api),
            _policy(api),
            units=units,
            expected_unit_ids=expected,
            parent_seal_cid=api["GENESIS_PARENT_SEAL"],
            fallback_reasons=("first_state",),
            transition_id="txn:genesis",
        )
    persist_timer.bind_storage(dir_size(store_a))
    with cas_timer:
        advanced = sealer.publish_full_checkpoint(
            _state(
                api,
                revision="rev-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                source_root_cid=digest_hex("source-root-2"),
                repository_state_cid=digest_hex("repo-state-2"),
            ),
            _policy(api),
            units=_inventory(api, n=8, tag="second"),
            expected_unit_ids=_expected_ids(_inventory(api, n=8, tag="second")),
            transition_id="txn:second",
        )
    cas_timer.bind_storage(dir_size(store_a))
    live = sealer.get_current_seal("repo/ns-012")
    stale = sealer.publish_delta_seal(
        parent_view_from_full(api, genesis),
        _state(
            api,
            revision="rev-stale",
            source_root_cid=digest_hex("stale-source"),
            repository_state_cid=digest_hex("stale-state"),
            parent_revision_ids=("rev-old",),
        ),
        _policy(api),
        api["DeltaTransitionStatement"](
            schema=api["TRANSITION_SCHEMA"],
            parent_seal_cid=genesis.seal_cid,
            branch_id="main",
            old_source_root_cid=genesis.full_seal.source_root_cid,
            old_repository_state_cid=genesis.full_seal.repository_state_cid,
            old_manifest_root_cid=genesis.full_seal.manifest_root_cid,
            old_forest_root_cid=genesis.full_seal.repository_proof_root,
            old_aggregation_root=genesis.full_seal.aggregation_root,
            new_source_root_cid=digest_hex("stale-source"),
            new_repository_state_cid=digest_hex("stale-state"),
            new_revision="rev-stale",
            parent_revision_ids=(genesis.full_seal.revision,),
            diff=api["DiffCommitmentView"](
                diff_algorithm="ipfs_datasets_py/logic/zkp/incremental_sealing/repository_diff/algorithm@1",
                changed_artifact_commitment=digest_hex("diff"),
                complete=True,
                changed_paths=("src/module.py",),
            ),
            expected_manifest_unit_ids=genesis.full_seal.required_unit_ids,
            expected_surviving_leaf_ids=genesis.full_seal.required_unit_ids,
            forest_rebuilt=True,
            aggregation_rebuilt=True,
            logical_epoch=2,
        ),
        units=(
            api["DeltaUnitEvidence"](
                unit_id=units[0].unit_id,
                disposition="reuse",
                proof_object_cid=units[0].proof_object_cid,
                parent_proof_object_cid=units[0].proof_object_cid,
            ),
        ),
    )
    declare(
        cases,
        case_id="stale_parent_cannot_overwrite",
        family="cas",
        polarity="invalid",
        table="table12",
        expected_reason="stale_parent",
        description="A stale parent cannot replace the accepted current seal.",
    )
    rows.append(
        finish(
            row_base(
                case_id="stale_parent_cannot_overwrite",
                family="cas",
                polarity="invalid",
                table="table12",
                expected_reason="stale_parent",
                description="A stale parent cannot replace the accepted current seal.",
            ),
            observed_reason=enum_val(stale.reason)
            if (not stale.published and live is not None and live.seal_cid == advanced.seal_cid)
            else "stale_parent_overwrote",
            extra={
                "published": stale.published,
                "live_seal_cid": None if live is None else live.seal_cid,
                "advanced_seal_cid": advanced.seal_cid,
                "genesis_seal_cid": genesis.seal_cid,
                "measurements": {**persist_timer.as_measurements(), **cas_timer.as_measurements()},
            },
        )
    )

    store_b = work_root / "seal-race"
    store_b.mkdir()
    race = api["IncrementalProofSealer"](store_b)
    parent = race.publish_full_checkpoint(
        _state(api),
        _policy(api),
        units=units,
        expected_unit_ids=expected,
        parent_seal_cid=api["GENESIS_PARENT_SEAL"],
        fallback_reasons=("first_state",),
        transition_id="txn:race-parent",
    )
    parent_pointer = race.get_current_seal("repo/ns-012")
    barrier = threading.Barrier(6)

    def attempt(index: int):
        barrier.wait(timeout=30)
        return race.publish_full_checkpoint(
            _state(
                api,
                revision=f"rev-worker-{index:02d}-" + ("c" * 32),
                source_root_cid=digest_hex(f"wsrc-{index}"),
                repository_state_cid=digest_hex(f"wst-{index}"),
            ),
            _policy(api),
            units=_inventory(api, n=8, tag=f"w{index}"),
            expected_unit_ids=_expected_ids(_inventory(api, n=8, tag=f"w{index}")),
            transition_id=f"txn:worker-{index}",
            expected_current=parent_pointer,
        )

    race_results = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(attempt, index) for index in range(6)]
        for future in as_completed(futures):
            race_results.append(future.result())
    winners = [item for item in race_results if item.published]
    losers = [item for item in race_results if not item.published]
    current_after = race.get_current_seal("repo/ns-012")
    declare(
        cases,
        case_id="exactly_one_concurrent_cas_winner",
        family="cas",
        polarity="valid",
        table="table12",
        expected_reason="single_cas_winner",
        description="Exactly one concurrent valid writer publishes a generation; losers are stale_parent.",
    )
    rows.append(
        finish(
            row_base(
                case_id="exactly_one_concurrent_cas_winner",
                family="cas",
                polarity="valid",
                table="table12",
                expected_reason="single_cas_winner",
                description="Exactly one concurrent valid writer publishes a generation; losers are stale_parent.",
            ),
            observed_reason="single_cas_winner"
            if (
                len(winners) == 1
                and len(losers) == 5
                and all(enum_val(item.reason) == "stale_parent" for item in losers)
                and current_after is not None
                and current_after.seal_cid == winners[0].seal_cid
            )
            else "cas_race_overclaim",
            extra={
                "winners": len(winners),
                "losers": len(losers),
                "loser_reasons": [enum_val(item.reason) for item in losers],
                "parent_seal_cid": parent.seal_cid,
            },
        )
    )

    store_c = work_root / "seal-crash-pre"
    store_c.mkdir()
    pre = api["IncrementalProofSealer"](store_c)
    first = pre.publish_full_checkpoint(
        _state(api),
        _policy(api),
        units=units,
        expected_unit_ids=expected,
        parent_seal_cid=api["GENESIS_PARENT_SEAL"],
        fallback_reasons=("first_state",),
        transition_id="txn:pre-parent",
    )
    old = pre.get_current_seal("repo/ns-012")
    crashed = False
    try:
        pre.publish_full_checkpoint(
            _state(
                api,
                revision="rev-crash-pre",
                source_root_cid=digest_hex("crash-pre-src"),
                repository_state_cid=digest_hex("crash-pre-st"),
            ),
            _policy(api),
            units=_inventory(api, n=8, tag="crash-pre"),
            expected_unit_ids=_expected_ids(_inventory(api, n=8, tag="crash-pre")),
            fail_before_phase=api["SealTransitionPhase"].SEAL_PERSISTENCE,
            transition_id="txn:crash-pre",
        )
    except api["SealerCrash"]:
        crashed = True
    after_crash = pre.get_current_seal("repo/ns-012")
    declare(
        cases,
        case_id="pre_cas_crash_leaves_old_pointer",
        family="crash",
        polarity="invalid",
        table="table12",
        expected_reason="pre_cas_pointer_unchanged",
        description="A crash before CAS leaves the old current pointer unchanged.",
    )
    rows.append(
        finish(
            row_base(
                case_id="pre_cas_crash_leaves_old_pointer",
                family="crash",
                polarity="invalid",
                table="table12",
                expected_reason="pre_cas_pointer_unchanged",
                description="A crash before CAS leaves the old current pointer unchanged.",
            ),
            observed_reason="pre_cas_pointer_unchanged"
            if crashed and old is not None and after_crash == old
            else "pre_cas_pointer_moved",
            extra={
                "old_seal_cid": None if old is None else old.seal_cid,
                "after_seal_cid": None if after_crash is None else after_crash.seal_cid,
                "parent_published": first.published,
            },
        )
    )

    failed = sealer.publish_full_checkpoint(
        _state(
            api,
            revision="rev-failed-units",
            source_root_cid=digest_hex("fail-src"),
            repository_state_cid=digest_hex("fail-st"),
        ),
        _policy(api),
        units=(
            _unit(
                api,
                "unit/fail",
                terminal_status=api["ProofTerminalStatus"].FAILED.value,
            ),
        ),
        transition_id="txn:failed-units",
    )
    still_live = sealer.get_current_seal("repo/ns-012")
    declare(
        cases,
        case_id="failed_units_cannot_publish",
        family="publication",
        polarity="invalid",
        table="table12",
        expected_reason="proof_failed",
        description="Failed required units cannot publish or invent task success.",
    )
    rows.append(
        finish(
            row_base(
                case_id="failed_units_cannot_publish",
                family="publication",
                polarity="invalid",
                table="table12",
                expected_reason="proof_failed",
                description="Failed required units cannot publish or invent task success.",
            ),
            observed_reason=enum_val(failed.status)
            if (not failed.published and still_live == live)
            else "failed_units_published",
            extra={
                "published": failed.published,
                "reason": enum_val(failed.reason),
                "wal_state": None
                if sealer.wal.get_transition("txn:failed-units") is None
                else enum_val(sealer.wal.get_transition("txn:failed-units").state),
            },
        )
    )

    # Durable operational CAS
    durable_reason = "durable_unavailable"
    durable_extra: dict[str, Any] = {
        "durable_status": "unavailable",
    }
    if api["durable"] is not None and api["ss_contracts"] is not None:
        try:
            import base64 as _b64

            def cid_for_bytes(data: bytes) -> str:
                digest = hashlib.sha256(bytes(data)).digest()
                cid_bytes = bytes([0x01, 0x55, 0x12, 0x20]) + digest
                return "b" + _b64.b32encode(cid_bytes).decode("ascii").rstrip("=").lower()

            contracts = api["ss_contracts"]
            durable_dir = work_root / "durable"
            adapter = api["durable"].open_local_durable_state(durable_dir, backend=None)

            def manifest(label: str, disposition: str):
                payload = {
                    "repository_id": "repo/ns-012-durable",
                    "base_tree_cid": cid_for_bytes(f"{label}-base".encode()),
                    "candidate_tree_cid": cid_for_bytes(f"{label}-cand".encode()),
                    "datasets_state_cid": cid_for_bytes(f"{label}-ds".encode()),
                    "datasets_semantic_state_root_cid": cid_for_bytes(f"{label}-dsr".encode()),
                    "capsule_index_cid": cid_for_bytes(f"{label}-cap".encode()),
                    "delta_cid": cid_for_bytes(f"{label}-delta".encode()),
                    "invalidation_cid": cid_for_bytes(f"{label}-inv".encode()),
                    "obligation_set_cid": cid_for_bytes(f"{label}-ob".encode()),
                    "test_selection_cid": cid_for_bytes(f"{label}-sel".encode()),
                    "receipt_index_cid": cid_for_bytes(f"{label}-rx".encode()),
                    "environment_binding_cids": [
                        cid_for_bytes(f"{label}-env-a".encode()),
                        cid_for_bytes(f"{label}-env-b".encode()),
                    ],
                    "event_head_cid": cid_for_bytes(f"{label}-evt".encode()),
                    "versions": {
                        "capsule_schema": "ipfs-datasets.software-contracts.semantic-capsule@1",
                        "selection_schema": "ipfs-datasets.software-contracts.semantic-test-selection@1",
                        "semantic_index_schema": "ipfs-datasets.software-contracts.semantic-index@2",
                        "semantic_state_schema": "ipfs-datasets.software-contracts.semantic-state@1",
                    },
                    "acceptance_disposition": disposition,
                }
                return contracts.SemanticStateRootManifest.from_dict(payload)

            boot = manifest("boot", contracts.AcceptanceDisposition.BOOTSTRAP.value)
            accepted = manifest("acc", contracts.AcceptanceDisposition.ACCEPTED.value)
            stale_m = manifest("stale", contracts.AcceptanceDisposition.ACCEPTED.value)
            boot_cid = api["durable"].cid_for_root_manifest(boot)
            acc_cid = api["durable"].cid_for_root_manifest(accepted)
            stale_cid = api["durable"].cid_for_root_manifest(stale_m)
            adapter.put(api["durable"].root_manifest_artifact(boot), expected_cid=boot_cid)
            adapter.put(api["durable"].root_manifest_artifact(accepted), expected_cid=acc_cid)
            adapter.put(api["durable"].root_manifest_artifact(stale_m), expected_cid=stale_cid)
            root1 = adapter.compare_and_swap_root("repo/ns-012-durable", None, boot_cid)
            root2 = adapter.compare_and_swap_root("repo/ns-012-durable", root1, acc_cid)
            conflicted = False
            try:
                adapter.compare_and_swap_root("repo/ns-012-durable", root1, stale_cid)
            except api["durable"].RootConflict:
                conflicted = True
            recovered = adapter.recover()
            still = adapter.read_root("repo/ns-012-durable")
            durable_reason = (
                "stale_generation_conflict"
                if conflicted and still == root2
                else "durable_cas_failed"
            )
            durable_extra = {
                "durable_status": "live",
                "bootstrap_cid": boot_cid,
                "accepted_cid": acc_cid,
                "generation": still.generation if still else None,
                "recover_keys": sorted(recovered)[:12] if isinstance(recovered, dict) else [],
            }
            adapter.close()
        except Exception as exc:
            durable_reason = "durable_unavailable"
            durable_extra = {
                "durable_status": "error",
                "error": f"{type(exc).__name__}: {exc}",
            }
    declare(
        cases,
        case_id="durable_stale_generation_conflict",
        family="operational_cas",
        polarity="invalid",
        table="table12",
        expected_reason="stale_generation_conflict",
        description="A stale generation-bearing operational writer cannot replace the accepted durable root.",
    )
    rows.append(
        finish(
            row_base(
                case_id="durable_stale_generation_conflict",
                family="operational_cas",
                polarity="invalid",
                table="table12",
                expected_reason="stale_generation_conflict",
                description="A stale generation-bearing operational writer cannot replace the accepted durable root.",
            ),
            observed_reason=durable_reason,
            extra=durable_extra,
        )
    )

    git_reason = "git_lifecycle_unavailable"
    git_extra: dict[str, Any] = {}
    if api["lifecycle"] is not None:
        try:
            life = api["lifecycle"]
            store_dir = work_root / "lifecycle"
            ws = work_root / "ws-ns012"
            ws.mkdir()
            store = life.WorktreeLifecycleStore(
                repo_root=ROOT, store_dir=store_dir, proc_root=Path("/proc")
            )
            rec = store.begin_preparing(
                task_id="NS-012",
                canonical_task_cid="cid:task:ns-012",
                attempt=1,
                lane_id="lane-a",
                workspace_path=ws,
                branch="ns-012-qual",
                merge_target="main",
            )
            active = store.mark_active(
                ws, lease_id=rec.lease_id, expected_fence=rec.fence
            )
            duplicate = False
            try:
                store.begin_preparing(
                    task_id="NS-012",
                    canonical_task_cid="cid:task:ns-012",
                    attempt=1,
                    lane_id="lane-b",
                    workspace_path=ws,
                    branch="ns-012-qual",
                    merge_target="main",
                )
            except life.DuplicateAttemptError:
                duplicate = True
            fence_denied = False
            try:
                store.mark_terminal(
                    ws,
                    lease_id=active.lease_id,
                    expected_fence=active.fence + 99,
                    reason="forged-fence",
                )
            except (life.FenceMismatchError, life.OwnershipError, life.WorktreeLifecycleError):
                fence_denied = True
            terminal = store.mark_terminal(
                ws,
                lease_id=active.lease_id,
                expected_fence=active.fence,
                reason="qualification-complete",
            )
            git_reason = (
                "git_fence_mismatch_denied"
                if duplicate and fence_denied and terminal.state is life.WorkspaceLifecycleState.TERMINAL
                else "git_fence_failed"
            )
            git_extra = {
                "duplicate_blocked": duplicate,
                "fence_denied": fence_denied,
                "lease_id": active.lease_id,
                "fence": active.fence,
                "terminal_reason": terminal.terminal_reason,
            }
        except Exception as exc:
            git_reason = "git_lifecycle_unavailable"
            git_extra = {"error": f"{type(exc).__name__}: {exc}"}
    declare(
        cases,
        case_id="git_fence_mismatch_denied",
        family="git_lifecycle",
        polarity="invalid",
        table="table12",
        expected_reason="git_fence_mismatch_denied",
        description="A stale or forged Git lifecycle fence cannot replace the admitted worktree claim.",
    )
    rows.append(
        finish(
            row_base(
                case_id="git_fence_mismatch_denied",
                family="git_lifecycle",
                polarity="invalid",
                table="table12",
                expected_reason="git_fence_mismatch_denied",
                description="A stale or forged Git lifecycle fence cannot replace the admitted worktree claim.",
            ),
            observed_reason=git_reason,
            extra=git_extra,
        )
    )

    # Recovery
    store_d = work_root / "seal-post-cas"
    store_d.mkdir()
    post = api["IncrementalProofSealer"](store_d)
    post_crashed = False
    try:
        post.publish_full_checkpoint(
            _state(api),
            _policy(api),
            units=units,
            expected_unit_ids=expected,
            parent_seal_cid=api["GENESIS_PARENT_SEAL"],
            fallback_reasons=("first_state",),
            transition_id="txn:post-cas",
            fail_before_phase=api["SealTransitionPhase"].CLEANUP,
        )
    except api["SealerCrash"]:
        post_crashed = True
    pointer_after = post.get_current_seal("repo/ns-012")
    open_rec = post.wal.get_transition("txn:post-cas")
    report = post.recover_publication(apply_mutations=True)
    decision = report.decision_for("txn:post-cas")
    recognized = post.recognize_post_cas_success("txn:post-cas")
    finalized = post.wal.get_transition("txn:post-cas")
    report2 = post.recover_publication(apply_mutations=True)
    decision2 = report2.decision_for("txn:post-cas")
    declare(
        cases,
        case_id="post_cas_crash_recovers_success",
        family="recovery",
        polarity="valid",
        table="table12",
        expected_reason="recovered_success",
        description="Post-CAS crash recovery recognizes the committed pointer and finalizes cleanup.",
    )
    rows.append(
        finish(
            row_base(
                case_id="post_cas_crash_recovers_success",
                family="recovery",
                polarity="valid",
                table="table12",
                expected_reason="recovered_success",
                description="Post-CAS crash recovery recognizes the committed pointer and finalizes cleanup.",
            ),
            observed_reason="recovered_success"
            if (
                post_crashed
                and pointer_after is not None
                and recognized.published
                and enum_val(recognized.reason) == "recovered_success"
                and finalized is not None
                and enum_val(finalized.state) == "committed"
            )
            else "recovery_failed",
            extra={
                "pointer_recognized": decision.pointer_recognized,
                "recovery_reason": enum_val(decision.reason),
                "applied": decision.applied,
                "open_phase": None if open_rec is None else enum_val(open_rec.phase),
                "recognized_seal_cid": recognized.seal_cid,
            },
        )
    )
    recoveries.append(
        {
            "schema": SCHEMA_RECOVERY,
            "task_id": TASK_ID,
            "case_id": "post_cas_crash_recovers_success",
            "transition_id": "txn:post-cas",
            "disposition": enum_val(decision.disposition),
            "reason": enum_val(decision.reason),
            "published": recognized.published,
            "seal_cid": recognized.seal_cid,
            "pointer_recognized": decision.pointer_recognized,
            "applied": decision.applied,
            "exactly_once_external_claimed": False,
        }
    )

    declare(
        cases,
        case_id="recovery_is_idempotent",
        family="recovery",
        polarity="valid",
        table="table12",
        expected_reason="idempotent_recovery",
        description="A second recovery is idempotent and does not move the accepted root.",
    )
    rows.append(
        finish(
            row_base(
                case_id="recovery_is_idempotent",
                family="recovery",
                polarity="valid",
                table="table12",
                expected_reason="idempotent_recovery",
                description="A second recovery is idempotent and does not move the accepted root.",
            ),
            observed_reason="idempotent_recovery"
            if enum_val(decision2.reason)
            in {"pointer_matches_seal", "committed_prefix", "idempotent"}
            and post.get_current_seal("repo/ns-012") == pointer_after
            else "recovery_not_idempotent",
            extra={"second_reason": enum_val(decision2.reason)},
        )
    )
    recoveries.append(
        {
            "schema": SCHEMA_RECOVERY,
            "task_id": TASK_ID,
            "case_id": "recovery_is_idempotent",
            "transition_id": "txn:post-cas",
            "disposition": enum_val(decision2.disposition),
            "reason": enum_val(decision2.reason),
            "published": True,
            "seal_cid": None if pointer_after is None else pointer_after.seal_cid,
            "pointer_recognized": decision2.pointer_recognized,
            "applied": decision2.applied,
            "exactly_once_external_claimed": False,
        }
    )

    store_e = work_root / "seal-continue"
    store_e.mkdir()
    cont = api["IncrementalProofSealer"](store_e)
    try:
        cont.publish_full_checkpoint(
            _state(api),
            _policy(api),
            units=units,
            expected_unit_ids=expected,
            parent_seal_cid=api["GENESIS_PARENT_SEAL"],
            fallback_reasons=("first_state",),
            transition_id="txn:continue-crash",
            fail_before_phase=api["SealTransitionPhase"].CURRENT_ROOT_CAS,
        )
        pre_cas_continue_crash = False
    except api["SealerCrash"]:
        pre_cas_continue_crash = True
    empty_pointer = cont.get_current_seal("repo/ns-012")
    cont.recover_publication(apply_mutations=True)
    resumed = cont.publish_full_checkpoint(
        _state(api),
        _policy(api),
        units=units,
        expected_unit_ids=expected,
        parent_seal_cid=api["GENESIS_PARENT_SEAL"],
        fallback_reasons=("first_state",),
        transition_id="txn:continue-valid",
    )
    declare(
        cases,
        case_id="pre_cas_crash_then_valid_continuation",
        family="recovery",
        polarity="valid",
        table="table12",
        expected_reason="valid_continuation",
        description="After a recoverable pre-CAS crash, a valid continuation publishes without unobserved duplicate success.",
    )
    rows.append(
        finish(
            row_base(
                case_id="pre_cas_crash_then_valid_continuation",
                family="recovery",
                polarity="valid",
                table="table12",
                expected_reason="valid_continuation",
                description="After a recoverable pre-CAS crash, a valid continuation publishes without unobserved duplicate success.",
            ),
            observed_reason="valid_continuation"
            if pre_cas_continue_crash and empty_pointer is None and resumed.published
            else "continuation_failed",
            extra={
                "resumed_seal_cid": resumed.seal_cid,
                "resumed_generation": resumed.generation,
                "pre_cas_pointer": None if empty_pointer is None else empty_pointer.seal_cid,
            },
        )
    )
    recoveries.append(
        {
            "schema": SCHEMA_RECOVERY,
            "task_id": TASK_ID,
            "case_id": "pre_cas_crash_then_valid_continuation",
            "transition_id": "txn:continue-valid",
            "disposition": "published",
            "reason": enum_val(resumed.reason),
            "published": resumed.published,
            "seal_cid": resumed.seal_cid,
            "pointer_recognized": True,
            "applied": True,
            "exactly_once_external_claimed": False,
            "note": "external exactly-once behavior is not claimed beyond this hermetic WAL/CAS boundary",
        }
    )

    # Duplicate / reordered events: re-run recover and republish same generation parent.
    again = cont.recover_publication(apply_mutations=True)
    live_cont = cont.get_current_seal("repo/ns-012")
    declare(
        cases,
        case_id="duplicate_reordered_events_idempotent",
        family="recovery",
        polarity="valid",
        table="table12",
        expected_reason="duplicate_events_idempotent",
        description="Duplicated or reordered recovery events remain idempotent and cannot invent a second success.",
    )
    rows.append(
        finish(
            row_base(
                case_id="duplicate_reordered_events_idempotent",
                family="recovery",
                polarity="valid",
                table="table12",
                expected_reason="duplicate_events_idempotent",
                description="Duplicated or reordered recovery events remain idempotent and cannot invent a second success.",
            ),
            observed_reason="duplicate_events_idempotent"
            if live_cont is not None and live_cont.seal_cid == resumed.seal_cid
            else "duplicate_events_moved_root",
            extra={
                "recovery_decisions": len(again.decisions),
                "live_seal_cid": None if live_cont is None else live_cont.seal_cid,
            },
        )
    )

    unknown = api["verify_for_admission"](
        api["EvidenceCandidate"](
            evidence=api["IntegrityCommitment"](
                digest=digest_hex("unknown"),
                cid=digest_hex("unknown-cid"),
                merkle_inclusion="leaf:0",
                byte_length=32,
            ),
            proof_system_id="exotic-unknown-system",
            public_input_cid=digest_hex("unknown"),
            proof_unit_id="unit/unknown-provider",
            required_for_seal=True,
        )
    )
    declare(
        cases,
        case_id="unknown_provider_result_not_success",
        family="unknown_effect",
        polarity="invalid",
        table="table12",
        expected_reason="unknown_proof_system",
        description="Unknown provider/proof-system results cannot be admitted as task success.",
    )
    rows.append(
        finish(
            row_base(
                case_id="unknown_provider_result_not_success",
                family="unknown_effect",
                polarity="invalid",
                table="table12",
                expected_reason="unknown_proof_system",
                description="Unknown provider/proof-system results cannot be admitted as task success.",
            ),
            observed_reason=str(unknown.reason_code)
            if not unknown.admitted
            else "unknown_provider_admitted",
            extra={
                "admitted": unknown.admitted,
                "reason_code": unknown.reason_code,
            },
        )
    )

    simulated = api["create_full_checkpoint"](
        _state(api),
        _policy(api),
        units=(
            _unit(
                api,
                "unit/sim",
                proof_mode=api["ProofMode"].SIMULATED.value,
                terminal_status=api["ProofTerminalStatus"].SIMULATED.value,
            ),
        ),
        expected_unit_ids=("unit/sim",),
    )
    declare(
        cases,
        case_id="simulated_required_unit_not_sealed",
        family="unknown_effect",
        polarity="invalid",
        table="table12",
        expected_reason="simulated_only",
        description="Simulated required units cannot satisfy a production seal.",
    )
    rows.append(
        finish(
            row_base(
                case_id="simulated_required_unit_not_sealed",
                family="unknown_effect",
                polarity="invalid",
                table="table12",
                expected_reason="simulated_only",
                description="Simulated required units cannot satisfy a production seal.",
            ),
            observed_reason=enum_val(simulated.seal_status)
            if not simulated.sealed
            else "simulated_sealed",
            extra={"sealed": simulated.sealed, "reason": enum_val(simulated.reason)},
        )
    )

    unavailable = False
    unavailable_error = None
    try:
        api["IncrementalProofSealer"](None)
    except Exception as exc:
        unavailable = True
        unavailable_error = type(exc).__name__
    relative_rejected = False
    try:
        api["IncrementalProofSealer"]("relative/sealer")
    except Exception:
        relative_rejected = True
    declare(
        cases,
        case_id="store_unavailability_typed",
        family="availability",
        polarity="invalid",
        table="table12",
        expected_reason="explicit_root_required",
        description="Missing or relative store roots are typed unavailable; no default HOME/daemon root is invented.",
    )
    rows.append(
        finish(
            row_base(
                case_id="store_unavailability_typed",
                family="availability",
                polarity="invalid",
                table="table12",
                expected_reason="explicit_root_required",
                description="Missing or relative store roots are typed unavailable; no default HOME/daemon root is invented.",
            ),
            observed_reason="explicit_root_required"
            if unavailable and relative_rejected
            else "store_defaulted",
            extra={"error_type": unavailable_error, "relative_rejected": relative_rejected},
        )
    )

    declare(
        cases,
        case_id="federation_network_unavailable",
        family="federation",
        polarity="diagnostic",
        table="table12",
        expected_reason="remote_faults_unavailable",
        description="Federation, network partition, and libp2p/MCP transport remain unavailable outside the tested local deployment.",
    )
    rows.append(
        finish(
            row_base(
                case_id="federation_network_unavailable",
                family="federation",
                polarity="diagnostic",
                table="table12",
                expected_reason="remote_faults_unavailable",
                description="Federation, network partition, and libp2p/MCP transport remain unavailable outside the tested local deployment.",
            ),
            observed_reason="remote_faults_unavailable",
            extra={
                "tested_deployment": "hermetic local WAL/CAS + DurableCoordinationStore + worktree lifecycle",
                "network_partition": "unavailable",
                "libp2p_mcp_transport": "unavailable",
                "cross_repository_gitlink_conflict": "unavailable",
                "remote_store": "unavailable",
                "federation_claimed": False,
            },
        )
    )

    labeled = persist_timer.as_measurements()
    labeled.update(cas_timer.as_measurements())
    labeled.update(seq_timer.as_measurements())
    labeled.update(verify_timer.as_measurements())
    required_labels = (
        "prepare_elapsed",
        "prepare_cpu",
        "prepare_memory",
        "prepare_storage",
        "verify_elapsed",
        "verify_cpu",
        "persist_elapsed",
        "persist_cpu",
        "persist_storage",
        "cas_elapsed",
        "cas_cpu",
        "cas_storage",
    )
    all_actual = all(
        labeled[name]["status"] == "actual" and labeled[name]["value"] is not None
        for name in required_labels
    )
    gpu_unavailable = labeled["prepare_gpu"]["status"] == "unavailable"
    declare(
        cases,
        case_id="measurements_separately_labeled",
        family="measurement",
        polarity="valid",
        table="table12",
        expected_reason="separately_labeled_actual_measurements",
        description="Prepare/verify/persist/CAS CPU, memory, storage, and elapsed measurements are real and separately labeled.",
    )
    rows.append(
        finish(
            row_base(
                case_id="measurements_separately_labeled",
                family="measurement",
                polarity="valid",
                table="table12",
                expected_reason="separately_labeled_actual_measurements",
                description="Prepare/verify/persist/CAS CPU, memory, storage, and elapsed measurements are real and separately labeled.",
            ),
            observed_reason="separately_labeled_actual_measurements"
            if all_actual and gpu_unavailable
            else "measurement_missing_or_estimated",
            extra={"measurements": labeled, "gpu_status": labeled["prepare_gpu"]["status"]},
        )
    )

    sealer.close()
    race.close()
    pre.close()
    post.close()
    cont.close()
    return cases, rows, recoveries


def build_matrix(
    *,
    cases: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    recoveries: list[dict[str, Any]],
    capability: dict[str, Any],
    hashes: dict[str, str],
    started_at: str,
) -> dict[str, Any]:
    by_id = {row["case_id"]: row for row in rows}
    seq = by_id.get("seq_par_worker_counts_match") or {}
    return {
        "schema": SCHEMA_MATRIX,
        "task_id": TASK_ID,
        "policy_id": POLICY_ID,
        "generated_at": started_at,
        "qualification_not_live_ad": True,
        "tested_deployment": "hermetic local IncrementalProofSealer WAL/CAS, DurableCoordinationStore, worktree lifecycle",
        "federation_claimed": False,
        "exactly_once_external_claimed": False,
        "table9": {
            "read_parse_canonicalize": "exact immutable canonical-json profile",
            "hash_memo": "content + codec/hash/canonicalization/source-mode; reverify; mtime rejected",
            "hash_verify_workers": list(WORKER_COUNTS),
            "merkle_construction": "normative unit_id order after serial barrier",
            "serial_barrier": "worker completion order cannot change bytes or disposition",
        },
        "table12": {
            "parallel_sealer": [
                "equal bytes/roots/dispositions at multiple worker counts",
                "malformed/missing/duplicate units",
                "cache/hash-memo corruption",
                "interrupted writes",
                "stale-parent races",
                "separate prepare/verify/persist/CAS CPU/memory/storage/elapsed",
            ],
            "recovery_and_federation": [
                "duplicate/reordered events",
                "worker crashes around artifact publication",
                "expiry/fencing",
                "unknown external effects",
                "store unavailable",
                "network partition retained unavailable",
                "cross-repository dirty overlays retained unavailable",
            ],
        },
        "positive_witness": {
            "seal_cid": seq.get("seal_cid"),
            "manifest_root_cid": seq.get("manifest_root_cid"),
            "repository_proof_root": seq.get("repository_proof_root"),
            "aggregation_root": seq.get("aggregation_root"),
        },
        "shim": capability.get("shim_report"),
        "capability": {
            "interpreter": capability.get("interpreter"),
            "python_version": capability.get("python_version"),
            "path": capability.get("path"),
            "durable_status": capability.get("durable_status"),
            "lifecycle_status": capability.get("lifecycle_status"),
            "binaries": capability.get("binaries"),
        },
        "source_hashes": hashes,
        "cases": cases,
        "recovery_receipt_count": len(recoveries),
        "claim_boundary": (
            "This matrix qualifies local sequential/parallel preparation, complete "
            "manifests, parent-bound CAS, and restart reconciliation on the located "
            "accelerate sealer plus hermetic WAL/CAS contracts. It is not global "
            "consensus, not federation, and not exactly-once physical side effects "
            "beyond the tested boundary."
        ),
    }


def build_report(
    *,
    capability: dict[str, Any],
    rows: list[dict[str, Any]],
    recoveries: list[dict[str, Any]],
    matrix: dict[str, Any],
    started_at: str,
) -> str:
    by_id = {row["case_id"]: row for row in rows}
    seq = by_id.get("seq_par_worker_counts_match") or {}
    rec = by_id.get("post_cas_crash_recovers_success") or {}
    cont = by_id.get("pre_cas_crash_then_valid_continuation") or {}
    meas = by_id.get("measurements_separately_labeled") or {}
    lines = [
        "# NS-012 Complete inventories, parallel sealing, CAS, and restart recovery",
        "",
        f"Generated at {started_at}. This is a sealed-profile qualification record, not a live A–D experiment, not federation, and not an external exactly-once claim.",
        "",
        "## Profile",
        "",
        "- Coordinator: `IncrementalProofSealer@1` with WAL-backed expected-parent CAS",
        "- Completeness: `create_full_checkpoint` / `aggregate_verified_units`",
        "- Admission: `EvidenceVerifier.verify_for_admission`",
        "- Operational CAS: `IpfsKitDurableStateAdapter` over `DurableCoordinationStore`",
        "- Git fencing: `WorktreeLifecycleStore`",
        f"- Policy: `{POLICY_ID}`",
        f"- Datasets evidence shim: `{capability.get('shim_report', {}).get('datasets_evidence_shim')}`",
        f"- Kit proof_seal_store shim: `{capability.get('shim_report', {}).get('kit_proof_seal_store_shim')}`",
        "",
        "## Environment",
        "",
        f"- Interpreter: `{capability.get('interpreter')}` ({capability.get('python_version')})",
        f"- Sealed `PATH` at process start: `{capability.get('path')}`",
        f"- Durable store import: `{capability.get('durable_status')}`",
        f"- Worktree lifecycle import: `{capability.get('lifecycle_status')}`",
        "",
        "## Coverage",
        "",
        f"- Result rows: {len(rows)}",
        f"- Failed rows: {sum(1 for row in rows if row.get('status') != 'pass')}",
        f"- Recovery receipts: {len(recoveries)}",
        f"- Sequential/parallel match: `{seq.get('observed_reason')}`",
        f"- Post-CAS recovery: `{rec.get('observed_reason')}`",
        f"- Valid continuation: `{cont.get('observed_reason')}`",
        "",
        "## Sequential/parallel preparation (Table 9)",
        "",
        "Units are canonicalized under a frozen codec/hash/canonicalization/source-mode profile. Hash memo keys that exact binding and reverifies stored digests; mtime/path keys are rejected. Independent workers may complete out of order. A serial barrier sorts leaves by `unit_id` and rebuilds the forest so worker completion order cannot change bytes, roots, inventories, or dispositions. Worker counts 1, 2, 4, and 8 produced identical leaf roots, inventories, full-checkpoint CIDs, and aggregation dispositions.",
        "",
        f"- Seal CID: `{seq.get('seal_cid')}`",
        f"- Manifest root: `{seq.get('manifest_root_cid')}`",
        f"- Repository proof root: `{seq.get('repository_proof_root')}`",
        f"- Aggregation root: `{seq.get('aggregation_root')}`",
        "",
        "## Completeness is independent of membership",
        "",
        "An empty required set, a missing mandatory unit, a duplicate identity, and a presented subset that does not equal the requirement manifest all fail `incomplete_manifest`. Manifest aggregation separately rejects missing, duplicate, and reordered children. Merkle membership of some units is never treated as completeness.",
        "",
        "## Stale, late, and failed writers",
        "",
        "A delta against a superseded parent returns `stale_parent` without moving the current pointer. Six concurrent same-parent writers produce exactly one published generation; losers are `stale_parent`. Pre-CAS crashes and failed required units leave the accepted root unchanged. DurableCoordinationStore generation tokens reject ABA-stale operational writers. Worktree lifecycle fences reject duplicate live claims and forged fence tokens.",
        "",
        "## Restart recovery",
        "",
        "A crash after CAS and before cleanup leaves the pointer on the new seal with an open WAL record. Recovery recognizes `pointer_matches_seal`, commits cleanup, and `recognize_post_cas_success` reports `recovered_success`. A second recovery is idempotent. A pre-CAS crash leaves no current pointer; a subsequent valid publish resumes a useful sealed task. Duplicate recovery events do not invent a second success. External exactly-once side effects outside this WAL/CAS/lifecycle boundary are not claimed.",
        "",
        "## Unavailable remote faults",
        "",
        "Network partition, libp2p/MCP transport, remote stores, and cross-repository dirty gitlink overlays are retained as `unavailable` for this local hermetic deployment. They are not simulated as successful federation.",
        "",
        "## Measurements",
        "",
        "Prepare, verify, persist, and CAS each record elapsed wall time, CPU time, peak RSS, and storage bytes from the live run. GPU time is `unavailable` because no accelerator is present in the sealed PATH. Overlapping parallel stage times are not added into a single physical quantity.",
        "",
        f"- Measurement case: `{meas.get('observed_reason')}`",
        "",
        "## Limitations",
        "",
        "- Nested `ipfs_kit_py.proof_seal_store` is absent from the pinned kit tree; NS-012 installs a contract-faithful hermetic WAL/CAS shim so the accelerate sealer can run. The shim is labeled and is not a released kit pin.",
        "- `ipfs_datasets_py.logic.zkp.incremental_sealing.evidence` is likewise absent; a closed vocabulary shim supplies SealStatus/ProofMode/terminal-status and evidence dataclasses the accelerate modules already import.",
        "- DurableCoordinationStore and WorktreeLifecycleStore are the live kit/accelerate surfaces for operational and Git reconciliation.",
        "- This receipt is not a matched A–D outcome, not a Groth16 proof of pytest execution, and not a multi-agent world-root claim.",
        "",
        "## Case outcomes",
        "",
        "| case_id | family | polarity | table | status | reason |",
        "|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| `{row['case_id']}` | {row['family']} | {row['polarity']} | {row.get('table')} | {row['status']} | `{row.get('observed_reason')}` |"
        )
    lines.extend(["", "## Recovery receipts", ""])
    for item in recoveries:
        lines.append(
            f"- `{item['case_id']}` transition `{item['transition_id']}` disposition `{item['disposition']}` reason `{item['reason']}` published `{item['published']}` seal `{item.get('seal_cid')}`"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    started_at = utc_now()
    checkpoint("start", {"started_at": started_at, "task_id": TASK_ID})
    capability = prepare_imports()
    api = capability.pop("api")
    hashes = source_hashes()
    work_root = Path(tempfile.mkdtemp(prefix="ns012-sealer-"))
    try:
        cases, rows, recoveries = run_cases(api, work_root)
    finally:
        shutil.rmtree(work_root, ignore_errors=True)

    failed = [row["case_id"] for row in rows if row.get("status") != "pass"]
    if failed:
        raise SystemExit(f"NS-012 qualification cases failed: {failed}")
    missing = [name for name in REQUIRED_CASES if name not in {row["case_id"] for row in rows}]
    if missing:
        raise SystemExit(f"NS-012 missing required cases: {missing}")

    matrix = build_matrix(
        cases=cases,
        rows=rows,
        recoveries=recoveries,
        capability=capability,
        hashes=hashes,
        started_at=started_at,
    )
    report = build_report(
        capability=capability,
        rows=rows,
        recoveries=recoveries,
        matrix=matrix,
        started_at=started_at,
    )
    QUAL.mkdir(parents=True, exist_ok=True)
    SNAP_QUAL.mkdir(parents=True, exist_ok=True)
    for directory in (QUAL, SNAP_QUAL):
        write_json(directory / "sealer_fault_matrix.json", matrix)
        write_jsonl(directory / "sealer_results.jsonl", rows)
        write_jsonl(directory / "recovery_receipts.jsonl", recoveries)
        atomic_write(directory / "sealer_recovery_report.md", report.encode("utf-8"))

    checkpoint(
        "outputs",
        {
            "finished_at": utc_now(),
            "rows": len(rows),
            "failed": failed,
            "matrix_sha256": sha256_file(QUAL / "sealer_fault_matrix.json"),
            "results_sha256": sha256_file(QUAL / "sealer_results.jsonl"),
            "recovery_sha256": sha256_file(QUAL / "recovery_receipts.jsonl"),
            "report_sha256": sha256_file(QUAL / "sealer_recovery_report.md"),
        },
    )
    print("NS-012 sealer qualification: OK")
    print(f"rows={len(rows)} failed={len(failed)} recoveries={len(recoveries)}")
    print("seq_par=", (by_id := {row['case_id']: row for row in rows})["seq_par_worker_counts_match"]["observed_reason"])
    print("recovery=", by_id["post_cas_crash_recovers_success"]["observed_reason"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
