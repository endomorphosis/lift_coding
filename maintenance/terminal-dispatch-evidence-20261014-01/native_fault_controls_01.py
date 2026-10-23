"""Authored data/process perturbations at the existing live policy observer.

No claim, fence, lease, scope state, socket reply or kernel birth is substituted.
This module never launches a worker and never changes a deadline.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import signal
import stat
import threading
import time


CASES = ("baseline", "stale-head", "swapped-allocation", "modified-artifact", "disconnect", "exceeded-budget", "replayed-nonce")


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()


def _bytes(path, limit=2 * 1024 * 1024):
    path = Path(path)
    assert path.is_absolute() and path.resolve(strict=True) == path
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        assert stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_uid == os.geteuid()
        assert 0 < before.st_size <= limit
        raw = os.pread(fd, limit + 1, 0)
        signature = lambda value: tuple(getattr(value, key) for key in (
            "st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns"))
        assert len(raw) == before.st_size and signature(before) == signature(os.fstat(fd)) == signature(path.lstat())
        return raw, before
    finally:
        os.close(fd)


def _pin(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


class NativeFaultControl:
    def __init__(self, case):
        assert case in CASES
        self.case = case
        self.result = {"schema": "native-admitted-fault-control@1", "case": case,
            "triggered": False, "worker_callbacks": 0, "authority_substituted": False,
            "claim_or_fence_mutated": False, "deadline_extended": False,
            "provider_calls": 0, "proof_authority": False, "completion_authority": False}
        self.thread = None

    def policy_observed(self, *, scope, runtime, budget, index, repository, head, scheduler):
        if self.case not in {"stale-head", "swapped-allocation", "modified-artifact", "disconnect"} or self.result["triggered"]:
            return
        if scope is None or runtime is None or budget is None:
            return
        from ipfs_accelerate_py.agent_supervisor.runtime.checked_observer_budget import CheckedObserverBudgetError
        try:
            record = scope.prepared_record
        except CheckedObserverBudgetError as error:
            if str(error) == "no original coding dispatch has been prepared":
                return
            raise
        snapshot = budget.snapshot()
        diagnostic = runtime.checked_context_dispatch_broker.diagnostic_snapshot()
        if snapshot["totals"]["events"] != 1 or not diagnostic["pending"] or diagnostic["boundary"] != "native_daemon_to_owner_wrapper":
            return
        assert not diagnostic["wrapper_birth_observed"] and not diagnostic["worker_birth_observed"]
        self.result.update(triggered=True, trigger_monotonic_ns=time.monotonic_ns(),
            trigger_phase="charged_preparation_before_wrapper_release", trigger_diagnostic=diagnostic,
            charged_event_cid=record["preparation"]["event"]["event_cid"],
            charged_totals=dict(snapshot["totals"]))
        if self.case == "stale-head":
            current = index.prepare_current(repository, repository_id=head.repository_id,
                operation_id="stage-ab01-live-stale-head-control", expected_head=head, scheduler=scheduler).head
            assert current.generation == head.generation + 1 and current != head
            self.result.update(original_head=head.to_dict(), new_current_head=current.to_dict(),
                genuine_current_head_commit=True, source_bytes_modified=False)
        elif self.case == "modified-artifact":
            path = Path(record["descriptor"]["artifact"])
            raw, before = _bytes(path)
            assert hashlib.sha256(raw).hexdigest() == record["descriptor"]["sha256"]
            mode = stat.S_IMODE(before.st_mode)
            assert mode == 0o444
            path.chmod(0o644)
            fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW)
            try:
                assert os.fstat(fd).st_ino == before.st_ino
                os.write(fd, b"\n")
                os.fsync(fd)
            finally:
                os.close(fd)
                path.chmod(mode)
            changed, _ = _bytes(path)
            assert changed == raw + b"\n"
            self.result.update(named_fixture_path=str(path), before=_pin(raw), after=_pin(changed),
                original_descriptor_unchanged=True, actual_checked_artifact_modified=True)
        elif self.case == "swapped-allocation":
            from ipfs_accelerate_py.agent_supervisor.merge.worktree_lifecycle import WorktreeLifecycleStore, WorkspaceLifecycleRecord
            workspace = Path(record["preparation"]["basis"]["worker_workspace"])
            store = WorktreeLifecycleStore(repo_root=repository, store_dir=repository / ".git" / "agent-worktree-lifecycle")
            path = store.workspace_path_for(workspace)
            raw, before = _bytes(path)
            original = WorkspaceLifecycleRecord.from_dict(json.loads(raw))
            assert original.workspace_path == str(workspace) and original.record_id == original.compute_record_id()
            substituted = deepcopy(original.to_dict())
            substituted["task_id"] = "AB-AUTHORED-FOREIGN-ALLOCATION"
            substituted["record_id"] = WorkspaceLifecycleRecord.compute_record_id_for(
                canonical_task_cid=substituted["canonical_task_cid"], task_id=substituted["task_id"],
                attempt=substituted["attempt"], workspace_path=substituted["workspace_path"])
            changed = wire(substituted)
            temporary = path.with_name(path.name + ".ab01-substitution")
            fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, stat.S_IMODE(before.st_mode))
            with os.fdopen(fd, "wb") as stream:
                stream.write(changed)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
            assert _bytes(path)[0] == changed
            self.result.update(named_fixture_path=str(path), before=_pin(raw), after=_pin(changed),
                original_record_id=original.record_id, substituted_record_id=substituted["record_id"],
                original_task_id=original.task_id, substituted_task_id=substituted["task_id"],
                actual_allocation_file_replaced=True, substitution_payload_is_authority=False)
        else:
            self._disconnect(runtime)

    def _disconnect(self, runtime):
        from ipfs_accelerate_py.agent_supervisor.runtime.checked_context_dispatch import _kernel_identity
        receipts = runtime.bootstrap_receipts
        assert len(receipts) == 1
        original = _kernel_identity(receipts[0]["pid"])
        assert original["uid"] == os.geteuid() and original["process_birth_id"] == receipts[0]["process_birth_id"]
        assert original["command"][:4] == [runtime.manifest["argv"][0], "-P", "-m", "ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon"]
        pidfd = os.pidfd_open(original["pid"], 0)
        assert _kernel_identity(original["pid"])["process_birth_id"] == original["process_birth_id"]
        signal.pidfd_send_signal(pidfd, signal.SIGSTOP)
        self.result.update(daemon_pid=original["pid"], daemon_process_birth_id=original["process_birth_id"],
            daemon_argv_sha256=hashlib.sha256(wire(original["command"])).hexdigest(),
            exact_pidfd_used=True, original_daemon_stopped_before_prepared_release=True,
            original_channel_closed_by_real_peer_exit=False)

        def close_peer():
            try:
                deadline = time.monotonic() + 8
                while time.monotonic() < deadline:
                    sampled = runtime.checked_context_dispatch_broker.diagnostic_snapshot()
                    if sampled["prepared_ack_outstanding"]:
                        assert _kernel_identity(original["pid"])["process_birth_id"] == original["process_birth_id"]
                        self.result["disconnect_diagnostic"] = sampled
                        signal.pidfd_send_signal(pidfd, signal.SIGKILL)
                        self.result["original_channel_closed_by_real_peer_exit"] = True
                        self.result["disconnect_monotonic_ns"] = time.monotonic_ns()
                        return
                    if not sampled["pending"]:
                        break
                    time.sleep(0.005)
                self.result["disconnect_failure"] = "original prepared ACK boundary was not observed"
                signal.pidfd_send_signal(pidfd, signal.SIGKILL)
            except BaseException as error:
                self.result["disconnect_failure"] = {"type": type(error).__name__, "message": str(error)[:1024]}
                try:
                    signal.pidfd_send_signal(pidfd, signal.SIGKILL)
                except OSError:
                    pass
            finally:
                os.close(pidfd)

        self.thread = threading.Thread(target=close_peer, name="authentic-disconnect-qualification", daemon=True)
        self.thread.start()

    def finish(self):
        if self.thread is not None:
            self.thread.join(timeout=9)
            assert not self.thread.is_alive(), "authentic disconnect control did not finish"
        return json.loads(wire(self.result))

    def qualify_refusal(self, *, refusals, broker, budget):
        assert self.case not in {"baseline", "replayed-nonce"}
        assert len(refusals) == 1 and refusals[0]["status"] == "refused"
        refusal = refusals[0]
        assert refusal["boundary"] == "native_daemon_to_owner_wrapper"
        assert broker.wrapper_birth_observed is False and broker.worker_birth_observed is False
        snapshot = budget.snapshot()
        if self.case == "exceeded-budget":
            assert refusal["error_type"] == "SemanticContextBudgetExceeded"
            assert snapshot["totals"]["events"] == 0 and snapshot["records"] == []
            self.result.update(triggered=True, trigger_phase="actual_native_input_budget_reservation",
                actual_native_dispatch_budget_refused=True)
        else:
            assert self.result["triggered"] is True
            assert snapshot["totals"] == self.result["charged_totals"] and snapshot["totals"]["events"] == 1
            assert snapshot["records"][0]["event"]["event_cid"] == self.result["charged_event_cid"]
            assert snapshot["records"][0]["status"] == "aborted"
            frames = refusal["failure_frames"]
            assert type(frames) is list and frames
            if self.case == "stale-head":
                # The real stale-head01 run reached the original final catalog
                # guard after its policy callback published generation + 1.
                # Match that exact protected-source refusal, not ValueError in
                # general. The original scope and conservative charge remain.
                assert refusal["error_type"] == "ValueError"
                assert refusal["message_sha256"] == hashlib.sha256(
                    b"catalog head changed at delivery publication").hexdigest()
                assert any(frame.get("file") == "terminal_semantic_budget_delivery.py"
                    and frame.get("function") == "check" for frame in frames)
                assert any(frame.get("file") == "checked_observer_budget.py"
                    and frame.get("function") == "prepare_dispatch" for frame in frames)
                assert self.result["genuine_current_head_commit"] is True
                assert self.result["new_current_head"]["generation"] == self.result["original_head"]["generation"] + 1
            elif self.case == "modified-artifact":
                assert refusal["error_type"] == "CheckedAuditContextError"
            elif self.case == "swapped-allocation":
                assert refusal["error_type"] in {"CheckedContextDispatchError", "WorktreeLifecycleError"}
            else:
                assert self.result["original_channel_closed_by_real_peer_exit"] is True and "disconnect_failure" not in self.result
                assert broker.ambiguous_birth_possible is True and refusal["unacknowledged_child_birth_possible"] is True
        return {"schema": "native-admitted-fault-refusal-qualification@1", "case": self.case,
            "qualified": True, "original_broker_refusal": refusal,
            "wrapper_birth_observed": False, "worker_birth_observed": False,
            "unacknowledged_child_birth_possible": broker.ambiguous_birth_possible,
            "conservative_charge_retained": self.case != "exceeded-budget",
            "budget_rejected_before_reservation": self.case == "exceeded-budget",
            "original_budget_totals": snapshot["totals"], "actual_native_START_required": True,
            "no_unauthorized_birth_claim_scope": "No broker-authorized wrapper or worker release; original STOP independently fences possible births.",
            "proof_authority": False, "completion_authority": False, "provider_calls": 0}
