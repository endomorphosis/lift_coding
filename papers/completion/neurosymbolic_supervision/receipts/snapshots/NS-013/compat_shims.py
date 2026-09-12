#!/usr/bin/env python3
"""Qualification-local import shims reused by NS-013.

The accelerate IncrementalProofSealer, full-checkpoint, aggregation, admission,
and delta-seal modules import:

* ``ipfs_datasets_py.logic.zkp.incremental_sealing.evidence`` (closed vocabulary)
* ``ipfs_kit_py.proof_seal_store`` (hermetic WAL + current-root CAS)

This worktree's pinned ``external/ipfs_datasets`` tree has no
``logic.zkp.incremental_sealing`` package, and the nested accelerate
``ipfs_kit_py`` submodule is an empty reserved slot.  The outer
``external/ipfs_kit`` pin also lacks ``proof_seal_store``.

These shims reconstruct the *imported contracts* the accelerate sealer already
calls so that live coordinator, completeness, and CAS qualification can run.
They are not a nested-kit source pin, not a Groth16 backend, and not a
federation/network deployment.  Installation is explicit and labeled.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import types
from dataclasses import dataclass, field
from typing import ClassVar
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


SHIM_EVIDENCE = "ns-013/qualification-local-contract-shim@1"


# ---------------------------------------------------------------------------
# Datasets evidence vocabulary
# ---------------------------------------------------------------------------


class EvidenceClassError(ValueError):
    """Closed evidence-class parse failure."""


class ProofMode(str, Enum):
    INTEGRITY_ONLY = "integrity_only"
    SIGNED_ASSERTION = "signed_assertion"
    RECEIPT_AGGREGATION = "receipt_aggregation"
    DIRECT_EXECUTION_PROOF = "direct_execution_proof"
    INCREMENTAL_SEAL = "incremental_seal"
    SIMULATED = "simulated"


class ProofTerminalStatus(str, Enum):
    PROVED = "proved"
    INTEGRITY_VERIFIED = "integrity_verified"
    SIGNED_ASSERTION_VERIFIED = "signed_assertion_verified"
    FAILED = "failed"
    PROOF_FAILED = "proof_failed"
    INVALID = "invalid"
    STALE = "stale"
    DISPROVED = "disproved"
    SIMULATED = "simulated"
    UNKNOWN = "unknown"
    UNAVAILABLE = "unavailable"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    NOT_MODELED = "not_modeled"


class SealStatus(str, Enum):
    SEALED_FULL = "sealed_full"
    SEALED_INCREMENTAL = "sealed_incremental"
    STALE_PARENT = "stale_parent"
    PROOF_FAILED = "proof_failed"
    VERIFICATION_FAILED = "verification_failed"
    INCOMPLETE_MANIFEST = "incomplete_manifest"
    INVALID_CACHE = "invalid_cache"
    SIMULATED_ONLY = "simulated_only"
    FULL_REPROOF_REQUIRED = "full_reproof_required"
    UNAVAILABLE = "unavailable"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"
    NOT_SEALED = "not_sealed"


class EvidenceClass(str, Enum):
    IntegrityCommitment = "IntegrityCommitment"
    SignedExecutionReceipt = "SignedExecutionReceipt"
    ReceiptAggregationZkProof = "ReceiptAggregationZkProof"
    DirectExecutionProof = "DirectExecutionProof"
    IncrementalCommitSeal = "IncrementalCommitSeal"


def parse_proof_mode(value: str | ProofMode) -> ProofMode:
    if isinstance(value, ProofMode):
        return value
    return ProofMode(str(value).strip())


def parse_terminal_status(value: str | ProofTerminalStatus) -> ProofTerminalStatus:
    if isinstance(value, ProofTerminalStatus):
        return value
    return ProofTerminalStatus(str(value).strip())


_PASSING = frozenset(
    {
        ProofTerminalStatus.PROVED,
        ProofTerminalStatus.INTEGRITY_VERIFIED,
        ProofTerminalStatus.SIGNED_ASSERTION_VERIFIED,
    }
)


def status_satisfies_class(
    status: ProofTerminalStatus, evidence_class: EvidenceClass
) -> bool:
    if status not in _PASSING:
        return False
    if evidence_class is EvidenceClass.DirectExecutionProof:
        return status is ProofTerminalStatus.PROVED
    if evidence_class is EvidenceClass.SignedExecutionReceipt:
        return status in {
            ProofTerminalStatus.SIGNED_ASSERTION_VERIFIED,
            ProofTerminalStatus.PROVED,
        }
    return True


@dataclass(frozen=True, slots=True)
class IntegrityCommitment:
    digest: str
    cid: str
    merkle_inclusion: str = ""
    byte_length: int = 0
    ESTABLISHES: ClassVar[str] = (
        "byte digest and CID membership of already-hashed content"
    )
    DOES_NOT_ESTABLISH: ClassVar[str] = (
        "test execution, cryptographic proof of a program, or freshness"
    )


@dataclass(frozen=True, slots=True)
class SignedExecutionReceipt:
    signer_id: str
    receipt_digest: str
    signature: str
    statement: str = ""
    ESTABLISHES: ClassVar[str] = "signer attestation of declared receipt fields"
    DOES_NOT_ESTABLISH: ClassVar[str] = (
        "direct execution of the runner or underlying tests ran"
    )


@dataclass(frozen=True, slots=True)
class ReceiptAggregationZkProof:
    circuit_id: str
    receipt_digests: tuple[str, ...]
    proof_cid: str
    ESTABLISHES: ClassVar[str] = (
        "admitted receipt-field completeness under the named circuit"
    )
    DOES_NOT_ESTABLISH: ClassVar[str] = (
        "test execution; underlying tests ran; pytest executed"
    )


@dataclass(frozen=True, slots=True)
class DirectExecutionProof:
    program_id: str
    input_commitment: str
    output_commitment: str
    proof_system_id: str
    proof_cid: str
    ESTABLISHES: ClassVar[str] = (
        "bound public-input relation for the named program under the proof system"
    )
    DOES_NOT_ESTABLISH: ClassVar[str] = (
        "arbitrary CPython/pytest execution outside the stated relation"
    )


@dataclass(frozen=True, slots=True)
class IncrementalCommitSeal:
    parent_seal_cid: str
    transition_id: str
    reused_leaf_cids: tuple[str, ...]
    replacement_leaf_cids: tuple[str, ...]
    manifest_cid: str
    verification_root: str
    ESTABLISHES: ClassVar[str] = (
        "parent-bound incremental commit of named leaf identities"
    )
    DOES_NOT_ESTABLISH: ClassVar[str] = (
        "test execution or global consensus across Git and remote stores"
    )


_CLASS_MAP = {
    "IntegrityCommitment": IntegrityCommitment,
    "SignedExecutionReceipt": SignedExecutionReceipt,
    "ReceiptAggregationZkProof": ReceiptAggregationZkProof,
    "DirectExecutionProof": DirectExecutionProof,
    "IncrementalCommitSeal": IncrementalCommitSeal,
}


def evidence_from_canonical(payload: Mapping[str, Any]) -> Any:
    if not isinstance(payload, Mapping):
        raise EvidenceClassError("evidence payload must be an object")
    name = str(payload.get("evidence_class") or payload.get("class") or "")
    cls = _CLASS_MAP.get(name)
    if cls is None:
        raise EvidenceClassError(f"unknown evidence class {name!r}")
    data = {key: value for key, value in payload.items() if key not in {"evidence_class", "class"}}
    if "receipt_digests" in data and not isinstance(data["receipt_digests"], tuple):
        data["receipt_digests"] = tuple(data["receipt_digests"])
    if "reused_leaf_cids" in data and not isinstance(data["reused_leaf_cids"], tuple):
        data["reused_leaf_cids"] = tuple(data["reused_leaf_cids"])
    if "replacement_leaf_cids" in data and not isinstance(data["replacement_leaf_cids"], tuple):
        data["replacement_leaf_cids"] = tuple(data["replacement_leaf_cids"])
    try:
        return cls(**data)  # type: ignore[arg-type]
    except TypeError as exc:
        raise EvidenceClassError(str(exc)) from exc


# ---------------------------------------------------------------------------
# Kit proof-seal-store contracts (hermetic local WAL + CAS)
# ---------------------------------------------------------------------------


class ProofSealStoreContractError(ValueError):
    """Fail-closed proof-seal-store contract violation."""


class ExplicitRootRequiredError(ProofSealStoreContractError):
    """Raised when a store root is missing, relative, or home-derived."""


class SealTransitionWalError(ProofSealStoreContractError):
    """WAL contract violation."""


class SealTransitionWalCrash(SealTransitionWalError):
    """Injected WAL crash."""


class ArtifactKind(str, Enum):
    CHECKPOINT_SEAL = "checkpoint_seal"
    DELTA_SEAL = "delta_seal"
    PROOF_OBJECT = "proof_object"
    RECEIPT = "receipt"
    FOREST = "forest"
    AGGREGATE = "aggregate"


class SealTransitionPhase(str, Enum):
    INTENT = "intent"
    PROOF_EXECUTION = "proof_execution"
    RECEIPT_PERSISTENCE = "receipt_persistence"
    FOREST_UPDATE = "forest_update"
    AGGREGATE_GENERATION = "aggregate_generation"
    SEAL_PERSISTENCE = "seal_persistence"
    CURRENT_ROOT_CAS = "current_root_cas"
    CLEANUP = "cleanup"


PHASE_ORDER: tuple[SealTransitionPhase, ...] = (
    SealTransitionPhase.INTENT,
    SealTransitionPhase.PROOF_EXECUTION,
    SealTransitionPhase.RECEIPT_PERSISTENCE,
    SealTransitionPhase.FOREST_UPDATE,
    SealTransitionPhase.AGGREGATE_GENERATION,
    SealTransitionPhase.SEAL_PERSISTENCE,
    SealTransitionPhase.CURRENT_ROOT_CAS,
    SealTransitionPhase.CLEANUP,
)


class SealTransitionState(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMMITTED = "committed"
    ABORTED = "aborted"
    FAILED = "failed"


class PointerDisposition(str, Enum):
    SWAPPED = "swapped"
    STALE = "stale"
    UNCHANGED = "unchanged"
    ERROR = "error"


class PointerReason(str, Enum):
    OK = "ok"
    STALE_PARENT = "stale_parent"
    GENERATION_MISMATCH = "generation_mismatch"
    NAMESPACE_MISMATCH = "namespace_mismatch"
    UNAVAILABLE = "unavailable"


class RecoveryDisposition(str, Enum):
    REPAIR = "repair"
    ABORT = "abort"
    NOOP = "noop"
    REJECT = "reject"


class RecoveryReason(str, Enum):
    POINTER_MATCHES_SEAL = "pointer_matches_seal"
    COMMITTED_PREFIX = "committed_prefix"
    IDEMPOTENT = "idempotent"
    STALE_PARENT = "stale_parent"
    OPEN_PRE_CAS = "open_pre_cas"
    MISSING = "missing"
    CORRUPT = "corrupt"


def validate_explicit_root_path(root_path: str | Path, *, field_name: str = "root_path") -> Path:
    text = str(root_path)
    if not text or text.strip() != text:
        raise ExplicitRootRequiredError(f"{field_name} must be a nonempty trimmed path")
    if text.startswith("~") or text.startswith("$") or not os.path.isabs(text):
        raise ExplicitRootRequiredError(
            f"{field_name} must be an explicit absolute path; no default user-state root exists"
        )
    path = Path(text)
    if path.exists() and path.is_symlink():
        raise ExplicitRootRequiredError(f"{field_name} must not be a symlink")
    return path


@dataclass(frozen=True, slots=True)
class StoreRoot:
    root_path: str

    @classmethod
    def require(cls, root: str | Path | None) -> "StoreRoot":
        if root is None:
            raise ExplicitRootRequiredError(
                "explicit StoreRoot is required; no default user-state or daemon root exists"
            )
        path = validate_explicit_root_path(root)
        return cls(root_path=str(path))


@dataclass(frozen=True, slots=True)
class ArtifactReference:
    cid: str
    kind: ArtifactKind | str = ArtifactKind.CHECKPOINT_SEAL


@dataclass(frozen=True, slots=True)
class CurrentSealPointer:
    repository_id: str
    branch_id: str
    seal_cid: str
    seal_kind: ArtifactKind
    generation: int
    parent_seal_cid: str = ""

    def as_artifact_reference(self) -> ArtifactReference:
        return ArtifactReference(cid=self.seal_cid, kind=self.seal_kind)

    def to_dict(self) -> dict[str, Any]:
        return {
            "repository_id": self.repository_id,
            "branch_id": self.branch_id,
            "seal_cid": self.seal_cid,
            "seal_kind": self.seal_kind.value
            if isinstance(self.seal_kind, ArtifactKind)
            else str(self.seal_kind),
            "generation": self.generation,
            "parent_seal_cid": self.parent_seal_cid,
        }


@dataclass
class SealTransitionRecord:
    transition_id: str
    repository_id: str
    branch_id: str
    phase: SealTransitionPhase
    state: SealTransitionState
    expected_parent_seal_cid: str = ""
    generation: int = 0
    new_seal_cid: str = ""
    new_seal_kind: ArtifactKind | None = None
    artifact_cids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "repository_id": self.repository_id,
            "branch_id": self.branch_id,
            "phase": self.phase.value,
            "state": self.state.value,
            "expected_parent_seal_cid": self.expected_parent_seal_cid,
            "generation": self.generation,
            "new_seal_cid": self.new_seal_cid,
            "new_seal_kind": None
            if self.new_seal_kind is None
            else (
                self.new_seal_kind.value
                if isinstance(self.new_seal_kind, ArtifactKind)
                else str(self.new_seal_kind)
            ),
            "artifact_cids": list(self.artifact_cids),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SealTransitionRecord":
        kind = payload.get("new_seal_kind")
        return cls(
            transition_id=str(payload["transition_id"]),
            repository_id=str(payload["repository_id"]),
            branch_id=str(payload["branch_id"]),
            phase=SealTransitionPhase(payload["phase"]),
            state=SealTransitionState(payload["state"]),
            expected_parent_seal_cid=str(payload.get("expected_parent_seal_cid") or ""),
            generation=int(payload.get("generation") or 0),
            new_seal_cid=str(payload.get("new_seal_cid") or ""),
            new_seal_kind=None if not kind else ArtifactKind(kind),
            artifact_cids=tuple(payload.get("artifact_cids") or ()),
        )


@dataclass(frozen=True, slots=True)
class PutResult:
    cid: str
    kind: ArtifactKind
    byte_length: int


@dataclass(frozen=True, slots=True)
class PointerCasResult:
    swapped: bool
    disposition: PointerDisposition
    reason: PointerReason
    pointer: CurrentSealPointer | None
    diagnostics: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RecoveryDecision:
    transition_id: str
    reason: RecoveryReason
    disposition: RecoveryDisposition
    applied: bool
    pointer_recognized: bool
    publication_rejected: bool = False
    diagnostics: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RecoveryReport:
    decisions: tuple[RecoveryDecision, ...]
    evidence_subset: str = "ips/seal-recovery@1"

    def decision_for(self, transition_id: str) -> RecoveryDecision:
        for item in self.decisions:
            if item.transition_id == transition_id:
                return item
        raise KeyError(transition_id)


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def _cid_filename(cid: str) -> str:
    text = cid.replace(":", "_")
    return text if text else "empty"


class HermeticProofSealStore:
    """Local immutable-block store.  No daemon, no network, no default HOME root."""

    def __init__(self, root: StoreRoot | str | Path, *, create: bool = True) -> None:
        store_root = root if isinstance(root, StoreRoot) else StoreRoot.require(root)
        self._root = Path(store_root.root_path)
        self._blocks = self._root / "blocks"
        if create:
            self._blocks.mkdir(parents=True, exist_ok=True)
        elif not self._blocks.is_dir():
            raise ProofSealStoreContractError("store blocks directory is missing")
        self._lock = threading.RLock()

    def put_immutable(
        self,
        kind: ArtifactKind,
        envelope: bytes,
        *,
        claimed_cid: str,
    ) -> PutResult:
        recomputed = "sha256:" + hashlib.sha256(envelope).hexdigest()
        if recomputed != claimed_cid:
            raise ProofSealStoreContractError("claimed_cid does not rehash to envelope bytes")
        path = self._blocks / _cid_filename(claimed_cid)
        with self._lock:
            if path.exists():
                existing = path.read_bytes()
                if existing != envelope:
                    raise ProofSealStoreContractError("immutable CID collision with different bytes")
            else:
                _atomic_write(path, envelope)
        return PutResult(cid=claimed_cid, kind=kind, byte_length=len(envelope))

    def get_verified_bytes(self, ref: ArtifactReference | str | Mapping[str, Any]) -> bytes:
        if isinstance(ref, ArtifactReference):
            cid = ref.cid
        elif isinstance(ref, Mapping):
            cid = str(ref.get("cid") or ref.get("seal_cid") or "")
        else:
            cid = str(ref)
        path = self._blocks / _cid_filename(cid)
        if not path.is_file():
            raise ProofSealStoreContractError(f"missing immutable block {cid}")
        body = path.read_bytes()
        recomputed = "sha256:" + hashlib.sha256(body).hexdigest()
        if recomputed != cid:
            raise ProofSealStoreContractError("stored block does not rehash to cid")
        return body


class CurrentSealRepository:
    """Filesystem current-seal pointer with expected-parent CAS."""

    def __init__(self, root: StoreRoot | str | Path, *, create: bool = True) -> None:
        store_root = root if isinstance(root, StoreRoot) else StoreRoot.require(root)
        self._root = Path(store_root.root_path)
        self._dir = self._root / "current"
        if create:
            self._dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def _path(self, repository_id: str, branch_id: str) -> Path:
        safe = hashlib.sha256(f"{repository_id}\n{branch_id}".encode("utf-8")).hexdigest()
        return self._dir / f"{safe}.json"

    def get_current_seal(
        self, repository_id: str, branch_id: str
    ) -> CurrentSealPointer | None:
        path = self._path(repository_id, branch_id)
        with self._lock:
            if not path.is_file():
                return None
            payload = json.loads(path.read_text(encoding="utf-8"))
        return CurrentSealPointer(
            repository_id=str(payload["repository_id"]),
            branch_id=str(payload["branch_id"]),
            seal_cid=str(payload["seal_cid"]),
            seal_kind=ArtifactKind(payload["seal_kind"]),
            generation=int(payload["generation"]),
            parent_seal_cid=str(payload.get("parent_seal_cid") or ""),
        )

    def compare_and_swap_current_seal_result(
        self,
        expected: CurrentSealPointer | None,
        new_pointer: CurrentSealPointer,
    ) -> PointerCasResult:
        path = self._path(new_pointer.repository_id, new_pointer.branch_id)
        with self._lock:
            live = self.get_current_seal(new_pointer.repository_id, new_pointer.branch_id)
            expected_cid = "" if expected is None else expected.seal_cid
            live_cid = "" if live is None else live.seal_cid
            expected_gen = -1 if expected is None else expected.generation
            live_gen = -1 if live is None else live.generation
            if live_cid != expected_cid or live_gen != expected_gen:
                return PointerCasResult(
                    swapped=False,
                    disposition=PointerDisposition.STALE,
                    reason=PointerReason.STALE_PARENT,
                    pointer=live,
                    diagnostics={
                        "expected_cid": expected_cid,
                        "live_cid": live_cid,
                        "expected_generation": expected_gen,
                        "live_generation": live_gen,
                    },
                )
            _atomic_write(
                path,
                (
                    json.dumps(new_pointer.to_dict(), sort_keys=True, separators=(",", ":"))
                    + "\n"
                ).encode("utf-8"),
            )
            return PointerCasResult(
                swapped=True,
                disposition=PointerDisposition.SWAPPED,
                reason=PointerReason.OK,
                pointer=new_pointer,
                diagnostics={},
            )


class SealTransitionWal:
    """JSON WAL for seal transitions.  Close is idempotent."""

    def __init__(
        self,
        root: StoreRoot | str | Path,
        *,
        create: bool = True,
        crash_injector: Callable[..., Any] | None = None,
    ) -> None:
        store_root = root if isinstance(root, StoreRoot) else StoreRoot.require(root)
        self._root = Path(store_root.root_path)
        self._dir = self._root / "wal"
        if create:
            self._dir.mkdir(parents=True, exist_ok=True)
        self._crash_injector = crash_injector
        self._lock = threading.RLock()
        self._closed = False

    def _path(self, transition_id: str) -> Path:
        safe = hashlib.sha256(transition_id.encode("utf-8")).hexdigest()
        return self._dir / f"{safe}.json"

    def _maybe_crash(self, name: str, transition_id: str, phase: SealTransitionPhase | None = None) -> None:
        if self._crash_injector is None:
            return
        try:
            if phase is not None:
                self._crash_injector(name, transition_id, phase)
            else:
                self._crash_injector(name, transition_id)
        except TypeError:
            try:
                self._crash_injector(name, transition_id)
            except TypeError:
                self._crash_injector(name)

    def _write(self, record: SealTransitionRecord) -> None:
        _atomic_write(
            self._path(record.transition_id),
            (json.dumps(record.to_dict(), sort_keys=True, separators=(",", ":")) + "\n").encode(
                "utf-8"
            ),
        )

    def get_transition(self, transition_id: str) -> SealTransitionRecord | None:
        path = self._path(transition_id)
        with self._lock:
            if not path.is_file():
                return None
            return SealTransitionRecord.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def list_open(self) -> list[SealTransitionRecord]:
        records: list[SealTransitionRecord] = []
        with self._lock:
            if not self._dir.is_dir():
                return records
            for path in sorted(self._dir.glob("*.json")):
                if path.name.startswith("."):
                    continue
                record = SealTransitionRecord.from_dict(
                    json.loads(path.read_text(encoding="utf-8"))
                )
                if record.state in {
                    SealTransitionState.OPEN,
                    SealTransitionState.IN_PROGRESS,
                }:
                    records.append(record)
        return records

    def close(self) -> None:
        self._closed = True


def begin_transition(wal: SealTransitionWal, intent: SealTransitionRecord) -> SealTransitionRecord:
    existing = wal.get_transition(intent.transition_id)
    if existing is not None and existing.state not in {
        SealTransitionState.ABORTED,
        SealTransitionState.FAILED,
    }:
        if existing.state is SealTransitionState.COMMITTED:
            return existing
        raise SealTransitionWalError(f"transition already open: {intent.transition_id}")
    record = SealTransitionRecord(
        transition_id=intent.transition_id,
        repository_id=intent.repository_id,
        branch_id=intent.branch_id,
        phase=SealTransitionPhase.INTENT,
        state=SealTransitionState.OPEN,
        expected_parent_seal_cid=intent.expected_parent_seal_cid,
        generation=intent.generation,
        new_seal_cid=intent.new_seal_cid,
        new_seal_kind=intent.new_seal_kind,
        artifact_cids=intent.artifact_cids,
    )
    wal._write(record)
    return record


def record_phase(
    wal: SealTransitionWal,
    transition_id: str,
    phase: SealTransitionPhase,
    *,
    artifact_cids: Sequence[str] = (),
    new_seal_cid: str | None = None,
    new_seal_kind: ArtifactKind | None = None,
    generation: int | None = None,
) -> SealTransitionRecord:
    record = wal.get_transition(transition_id)
    if record is None:
        raise SealTransitionWalError(f"unknown transition {transition_id}")
    if record.state in {
        SealTransitionState.COMMITTED,
        SealTransitionState.ABORTED,
        SealTransitionState.FAILED,
    }:
        raise SealTransitionWalError(f"cannot advance terminal transition {transition_id}")
    record.phase = phase
    record.state = SealTransitionState.IN_PROGRESS
    if artifact_cids:
        record.artifact_cids = tuple(artifact_cids)
    if new_seal_cid is not None:
        record.new_seal_cid = new_seal_cid
    if new_seal_kind is not None:
        record.new_seal_kind = new_seal_kind
    if generation is not None:
        record.generation = generation
    wal._write(record)
    return record


def abort_transition(
    wal: SealTransitionWal,
    transition_id: str,
    *,
    phase: SealTransitionPhase | None = None,
) -> SealTransitionRecord:
    record = wal.get_transition(transition_id)
    if record is None:
        raise SealTransitionWalError(f"unknown transition {transition_id}")
    if record.state is SealTransitionState.COMMITTED:
        return record
    record.state = SealTransitionState.ABORTED
    if phase is not None:
        record.phase = phase
    wal._write(record)
    return record


def commit_transition(
    wal: SealTransitionWal,
    transition_id: str,
    *,
    new_seal_cid: str,
    new_seal_kind: ArtifactKind,
    phase: SealTransitionPhase = SealTransitionPhase.CLEANUP,
    generation: int | None = None,
) -> SealTransitionRecord:
    record = wal.get_transition(transition_id)
    if record is None:
        raise SealTransitionWalError(f"unknown transition {transition_id}")
    record.state = SealTransitionState.COMMITTED
    record.phase = phase
    record.new_seal_cid = new_seal_cid
    record.new_seal_kind = new_seal_kind
    if generation is not None:
        record.generation = generation
    wal._write(record)
    return record


def recover_seal_transitions(
    root: StoreRoot | str | Path,
    *,
    wal: SealTransitionWal | None = None,
    store: HermeticProofSealStore | None = None,
    pointers: CurrentSealRepository | None = None,
    policy: Mapping[str, Any] | None = None,
) -> RecoveryReport:
    store_root = root if isinstance(root, StoreRoot) else StoreRoot.require(root)
    wal = wal or SealTransitionWal(store_root, create=True)
    pointers = pointers or CurrentSealRepository(store_root, create=True)
    apply_mutations = True if policy is None else bool(policy.get("apply_mutations", True))
    decisions: list[RecoveryDecision] = []
    seen: set[str] = set()
    records = list(wal.list_open())
    # Also inspect committed records named by callers via directory scan.
    wal_dir = Path(store_root.root_path) / "wal"
    if wal_dir.is_dir():
        loaded: dict[str, SealTransitionRecord] = {item.transition_id: item for item in records}
        for path in sorted(wal_dir.glob("*.json")):
            record = SealTransitionRecord.from_dict(json.loads(path.read_text(encoding="utf-8")))
            loaded[record.transition_id] = record
        records = list(loaded.values())
    for record in records:
        if record.transition_id in seen:
            continue
        seen.add(record.transition_id)
        live = pointers.get_current_seal(record.repository_id, record.branch_id)
        if record.state is SealTransitionState.COMMITTED:
            decisions.append(
                RecoveryDecision(
                    transition_id=record.transition_id,
                    reason=RecoveryReason.COMMITTED_PREFIX
                    if live is not None and live.seal_cid == record.new_seal_cid
                    else RecoveryReason.IDEMPOTENT,
                    disposition=RecoveryDisposition.NOOP,
                    applied=False,
                    pointer_recognized=bool(
                        live is not None and live.seal_cid == record.new_seal_cid
                    ),
                )
            )
            continue
        if (
            record.new_seal_cid
            and live is not None
            and live.seal_cid == record.new_seal_cid
            and live.generation == record.generation
        ):
            if apply_mutations and record.state is not SealTransitionState.COMMITTED:
                commit_transition(
                    wal,
                    record.transition_id,
                    new_seal_cid=record.new_seal_cid,
                    new_seal_kind=record.new_seal_kind or ArtifactKind.CHECKPOINT_SEAL,
                    phase=SealTransitionPhase.CLEANUP,
                    generation=record.generation,
                )
            decisions.append(
                RecoveryDecision(
                    transition_id=record.transition_id,
                    reason=RecoveryReason.POINTER_MATCHES_SEAL,
                    disposition=RecoveryDisposition.REPAIR,
                    applied=apply_mutations,
                    pointer_recognized=True,
                )
            )
            continue
        if record.phase in {
            SealTransitionPhase.CURRENT_ROOT_CAS,
            SealTransitionPhase.CLEANUP,
        } and (live is None or live.seal_cid != record.new_seal_cid):
            if apply_mutations:
                abort_transition(wal, record.transition_id, phase=record.phase)
            decisions.append(
                RecoveryDecision(
                    transition_id=record.transition_id,
                    reason=RecoveryReason.STALE_PARENT,
                    disposition=RecoveryDisposition.REJECT,
                    applied=apply_mutations,
                    pointer_recognized=False,
                    publication_rejected=True,
                )
            )
            continue
        if apply_mutations:
            abort_transition(wal, record.transition_id, phase=record.phase)
        decisions.append(
            RecoveryDecision(
                transition_id=record.transition_id,
                reason=RecoveryReason.OPEN_PRE_CAS,
                disposition=RecoveryDisposition.ABORT,
                applied=apply_mutations,
                pointer_recognized=False,
                publication_rejected=False,
            )
        )
    return RecoveryReport(decisions=tuple(decisions))


def _ensure_package(name: str, file_hint: str) -> types.ModuleType:
    existing = __import__(name) if name in __import__("sys").modules else None
    import sys

    if name in sys.modules:
        return sys.modules[name]
    module = types.ModuleType(name)
    module.__file__ = file_hint
    module.__path__ = []  # type: ignore[attr-defined]
    sys.modules[name] = module
    parent_name, _, child = name.rpartition(".")
    if parent_name:
        parent = sys.modules.get(parent_name)
        if parent is None:
            parent = _ensure_package(parent_name, file_hint)
        setattr(parent, child, module)
    return module


def install_qualification_shims() -> dict[str, Any]:
    """Install missing datasets evidence + kit proof_seal_store into sys.modules."""

    import sys

    here = str(Path(__file__).resolve())
    report: dict[str, Any] = {
        "schema": SHIM_EVIDENCE,
        "datasets_evidence_shim": False,
        "kit_proof_seal_store_shim": False,
        "datasets_native_present": False,
        "kit_native_present": False,
    }

    try:
        from ipfs_datasets_py.logic.zkp.incremental_sealing.evidence import (  # noqa: F401
            SealStatus as _NativeSealStatus,
        )

        report["datasets_native_present"] = True
    except Exception:
        evidence_mod = types.ModuleType("ipfs_datasets_py.logic.zkp.incremental_sealing.evidence")
        evidence_mod.__file__ = here
        for name, value in list(globals().items()):
            if name in {
                "ProofMode",
                "ProofTerminalStatus",
                "SealStatus",
                "EvidenceClass",
                "EvidenceClassError",
                "IntegrityCommitment",
                "SignedExecutionReceipt",
                "ReceiptAggregationZkProof",
                "DirectExecutionProof",
                "IncrementalCommitSeal",
                "parse_proof_mode",
                "parse_terminal_status",
                "status_satisfies_class",
                "evidence_from_canonical",
            }:
                setattr(evidence_mod, name, value)
        # Ensure parent packages exist without replacing installed datasets.
        for pkg in (
            "ipfs_datasets_py",
            "ipfs_datasets_py.logic",
            "ipfs_datasets_py.logic.zkp",
            "ipfs_datasets_py.logic.zkp.incremental_sealing",
        ):
            if pkg not in sys.modules:
                try:
                    __import__(pkg)
                except Exception:
                    _ensure_package(pkg, here)
        sealing = sys.modules["ipfs_datasets_py.logic.zkp.incremental_sealing"]
        sealing.evidence = evidence_mod  # type: ignore[attr-defined]
        sys.modules["ipfs_datasets_py.logic.zkp.incremental_sealing.evidence"] = evidence_mod
        report["datasets_evidence_shim"] = True

    try:
        from ipfs_kit_py.proof_seal_store.local_store import (  # noqa: F401
            HermeticProofSealStore as _NativeStore,
        )

        report["kit_native_present"] = True
    except Exception:
        names = {
            "ArtifactKind": ArtifactKind,
            "CurrentSealPointer": CurrentSealPointer,
            "ExplicitRootRequiredError": ExplicitRootRequiredError,
            "ProofSealStoreContractError": ProofSealStoreContractError,
            "SealTransitionPhase": SealTransitionPhase,
            "SealTransitionRecord": SealTransitionRecord,
            "SealTransitionState": SealTransitionState,
            "StoreRoot": StoreRoot,
            "validate_explicit_root_path": validate_explicit_root_path,
            "PHASE_ORDER": PHASE_ORDER,
            "HermeticProofSealStore": HermeticProofSealStore,
            "CurrentSealRepository": CurrentSealRepository,
            "PointerDisposition": PointerDisposition,
            "PointerReason": PointerReason,
            "PointerCasResult": PointerCasResult,
            "RecoveryDisposition": RecoveryDisposition,
            "RecoveryReason": RecoveryReason,
            "RecoveryReport": RecoveryReport,
            "RecoveryDecision": RecoveryDecision,
            "recover_seal_transitions": recover_seal_transitions,
            "SealTransitionWal": SealTransitionWal,
            "SealTransitionWalCrash": SealTransitionWalCrash,
            "SealTransitionWalError": SealTransitionWalError,
            "abort_transition": abort_transition,
            "begin_transition": begin_transition,
            "commit_transition": commit_transition,
            "record_phase": record_phase,
            "ArtifactReference": ArtifactReference,
            "PutResult": PutResult,
        }
        contracts = types.ModuleType("ipfs_kit_py.proof_seal_store.contracts")
        local_store = types.ModuleType("ipfs_kit_py.proof_seal_store.local_store")
        pointer = types.ModuleType("ipfs_kit_py.proof_seal_store.pointer")
        recovery = types.ModuleType("ipfs_kit_py.proof_seal_store.recovery")
        wal = types.ModuleType("ipfs_kit_py.proof_seal_store.wal")
        pkg = types.ModuleType("ipfs_kit_py.proof_seal_store")
        pkg.__path__ = []  # type: ignore[attr-defined]
        pkg.__file__ = here
        for mod in (contracts, local_store, pointer, recovery, wal, pkg):
            mod.__file__ = here
            for key, value in names.items():
                setattr(mod, key, value)
        if "ipfs_kit_py" not in sys.modules:
            try:
                __import__("ipfs_kit_py")
            except Exception:
                _ensure_package("ipfs_kit_py", here)
        kit = sys.modules["ipfs_kit_py"]
        kit.proof_seal_store = pkg  # type: ignore[attr-defined]
        sys.modules["ipfs_kit_py.proof_seal_store"] = pkg
        sys.modules["ipfs_kit_py.proof_seal_store.contracts"] = contracts
        sys.modules["ipfs_kit_py.proof_seal_store.local_store"] = local_store
        sys.modules["ipfs_kit_py.proof_seal_store.pointer"] = pointer
        sys.modules["ipfs_kit_py.proof_seal_store.recovery"] = recovery
        sys.modules["ipfs_kit_py.proof_seal_store.wal"] = wal
        pkg.contracts = contracts  # type: ignore[attr-defined]
        pkg.local_store = local_store  # type: ignore[attr-defined]
        pkg.pointer = pointer  # type: ignore[attr-defined]
        pkg.recovery = recovery  # type: ignore[attr-defined]
        pkg.wal = wal  # type: ignore[attr-defined]
        report["kit_proof_seal_store_shim"] = True

    return report
