"""Read-only DOEP retained-pool release admission for a qualified native owner.

A verified task history or local terminal lifecycle is not callback/effect
settlement authority. This version can reject a mismatched request or identify
missing native evidence; it intentionally cannot authorize or perform release.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import Any

REQUEST_SCHEMA = 'ipfs_accelerate_py/agent-supervisor/doep-retained-pool-release-request@1'
RESULT_SCHEMA = 'ipfs_accelerate_py/agent-supervisor/doep-retained-pool-release-admission@1'
TASKS = frozenset({'DOEP-032', 'DOEP-041'})
OWNER_KEYS = frozenset({'server_id', 'process_birth_id', 'store_id', 'database_uuid', 'generation', 'fence_epoch'})
BIRTH_KEYS = frozenset({'pid', 'start_time_ticks', 'boot_id', 'parent_pid'})
REQUEST_KEYS = frozenset({'schema', 'task_alias', 'task_cid', 'task_revision', 'attempt_id', 'binding_id',
                          'pool_lease_token', 'pool_owner', 'lifecycle_lease_id', 'lifecycle_fence',
                          'owner_identity', 'store_generation'})
MAX_FILE_BYTES = 2 * 1024 * 1024


class AdmissionRejected(ValueError):
    """Closed, nonsecret reason for refusing the requested exact scope."""


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise AdmissionRejected(reason)


def _digest(raw: bytes) -> str:
    return 'sha256:' + hashlib.sha256(raw).hexdigest()


def read_request(path: Path) -> Mapping[str, Any]:
    value = json.loads(_read_regular(path, maximum=16 * 1024))
    _require(isinstance(value, dict), 'request_not_object')
    return value


def _read_regular(path: Path, *, maximum: int = MAX_FILE_BYTES) -> bytes:
    """Walk a pinned no-follow directory chain and recheck every path binding."""
    absolute = path.absolute()
    parts = absolute.parts[1:]
    _require(bool(parts) and len(parts) <= 128 and all(part not in ('.', '..') for part in parts),
             'evidence_namespace_invalid')
    directories = [os.open(absolute.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)]
    anchors = []
    descriptor = None
    try:
        for part in parts[:-1]:
            parent = directories[-1]
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            directories.append(child)
            anchors.append((parent, part, os.fstat(child)))
        parent = directories[-1]
        descriptor = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        first = os.fstat(descriptor)
        _require(stat.S_ISREG(first.st_mode) and first.st_nlink == 1, 'evidence_not_single_regular_file')
        _require(first.st_size <= maximum, 'evidence_byte_bound')
        chunks, size = [], 0
        while True:
            block = os.read(descriptor, min(64 * 1024, maximum + 1 - size))
            if not block:
                break
            chunks.append(block)
            size += len(block)
            _require(size <= maximum, 'evidence_byte_bound')
        signature = lambda value: (value.st_dev, value.st_ino, value.st_mode, value.st_nlink,
                                   value.st_size, value.st_mtime_ns, value.st_ctime_ns)
        _require(signature(first) == signature(os.fstat(descriptor))
                 == signature(os.stat(parts[-1], dir_fd=parent, follow_symlinks=False)),
                 'evidence_changed_during_read')
        directory_identity = lambda value: (value.st_dev, value.st_ino, value.st_mode, value.st_uid, value.st_gid)
        for parent, part, observed in anchors:
            _require(directory_identity(os.stat(part, dir_fd=parent, follow_symlinks=False))
                     == directory_identity(observed), 'evidence_namespace_changed')
        return b''.join(chunks)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        for directory in reversed(directories):
            os.close(directory)


def _validate_request(request: Mapping[str, Any]) -> None:
    from ipfs_accelerate_py.agent_supervisor.task_sources.control_plane_contracts import StoreGeneration

    _require(isinstance(request, Mapping) and set(request) == REQUEST_KEYS
             and request.get('schema') == REQUEST_SCHEMA, 'request_schema_invalid')
    _require(request['task_alias'] in TASKS, 'task_outside_retained_release_scope')
    for key in ('task_cid', 'binding_id'):
        _require(isinstance(request[key], str) and re.fullmatch(r'sha256:[0-9a-f]{64}', request[key]) is not None,
                 'request_identity_invalid')
    _require(isinstance(request['attempt_id'], str) and re.fullmatch(r'attempt:[0-9a-f]{32}', request['attempt_id']) is not None,
             'request_attempt_invalid')
    _require(isinstance(request['pool_lease_token'], str)
             and re.fullmatch(r'[0-9a-f]{12}-[0-9a-f]{12}', request['pool_lease_token']) is not None,
             'request_pool_token_invalid')
    for key in ('task_revision', 'lifecycle_fence'):
        _require(type(request[key]) is int and request[key] > 0, 'request_revision_or_fence_invalid')
    _require(type(request['lifecycle_lease_id']) is str and 0 < len(request['lifecycle_lease_id']) <= 128,
             'request_lifecycle_lease_invalid')
    owner, birth = request['owner_identity'], request['pool_owner']
    _require(isinstance(owner, Mapping) and set(owner) == OWNER_KEYS, 'request_owner_scope_invalid')
    _require(isinstance(birth, Mapping) and set(birth) == BIRTH_KEYS, 'request_pool_owner_invalid')
    for key in ('generation', 'fence_epoch'):
        _require(type(owner[key]) is int and owner[key] > 0, 'request_owner_generation_invalid')
    for key in OWNER_KEYS - {'generation', 'fence_epoch'}:
        _require(type(owner[key]) is str and 0 < len(owner[key]) <= 256, 'request_owner_identity_invalid')
    for key in ('pid', 'start_time_ticks', 'parent_pid'):
        _require(type(birth[key]) is int and birth[key] > 0, 'request_pool_owner_invalid')
    _require(type(birth['boot_id']) is str and 0 < len(birth['boot_id']) <= 64, 'request_pool_owner_invalid')
    generation = StoreGeneration.from_dict(request['store_generation'])
    _require(generation.to_record() == request['store_generation'], 'request_store_generation_invalid')


def _canonical_missing_evidence(status: Mapping[str, Any], request: Mapping[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Describe the bound task's actual canonical blockers, without promoting body claims."""
    history = status['task_histories'][request['task_alias']]
    revisions = history['revisions']
    _require(isinstance(revisions, list) and bool(revisions), 'canonical_history_empty')
    head = revisions[-1]
    _require(head.get('revision') == request['task_revision'], 'canonical_history_head_mismatch')
    body = head.get('body')
    _require(isinstance(body, Mapping), 'canonical_history_body_unavailable')
    task = next(row for row in status['tasks'] if row.get('task_cid') == request['task_cid'])
    _require(head.get('status') == task.get('status'), 'canonical_history_status_mismatch')
    terminal = body.get('completion_receipt')
    missing: list[dict[str, Any]] = []
    observed: dict[str, Any] = {'task_status': task['status'], 'task_revision': request['task_revision'],
                               'canonical_terminal_receipt_present': isinstance(terminal, Mapping)}
    if not isinstance(terminal, Mapping):
        missing.append({'kind': 'canonical_terminal_receipt', 'reason': 'absent_from_bound_task_history_head'})
    else:
        if terminal.get('attempt_id') != request['attempt_id']:
            missing.append({'kind': 'canonical_terminal_attempt_binding',
                            'reason': 'missing' if not terminal.get('attempt_id') else 'different_attempt'})
        unknown = terminal.get('failure_kind') == 'provider_callback_outcome_unknown'
        observed['canonical_callback_outcome_unknown'] = unknown
        if unknown:
            missing.append({'kind': 'canonical_callback_outcome', 'reason': 'bound_terminal_receipt_reports_unknown'})
    relations = status.get('closeout_snapshot', {}).get('closeout_facts', {}).get('relations', {})
    for table in ('task_claims', 'leases', 'effect_claims'):
        relation = relations.get(table, {})
        if relation.get('available') is not True or relation.get('truncated') is not False:
            observed[table + '_open_count'] = None
            missing.append({'kind': table, 'reason': 'canonical_relation_unavailable_or_truncated'})
            continue
        rows = relation.get('rows')
        _require(isinstance(rows, list) and all(isinstance(row, Mapping) for row in rows), 'canonical_relation_malformed')
        # A row without a task identity cannot prove this task has no effects.
        ambiguous = any(not isinstance(row.get('task_cid'), str) or not row['task_cid'] for row in rows)
        matching = [row for row in rows if row.get('task_cid') == request['task_cid']]
        observed[table + '_open_count'] = len(matching)
        if ambiguous:
            missing.append({'kind': table, 'reason': 'canonical_rows_lack_task_scope'})
        if matching:
            missing.append({'kind': table, 'reason': 'bound_task_has_open_canonical_rows', 'count': len(matching)})
    # Empty current claims and local terminal state do not establish what an
    # earlier callback did. These are specific gaps in the existing native API.
    missing.extend([
        {'kind': 'canonical_callback_effect_settlement', 'reason': 'execution_attempt_and_terminal_event_not_exposed_by_admitted_reader'},
        {'kind': 'historical_retained_candidate_receipt', 'reason': 'original_fingerprint_receipt_not_independently_admitted'},
        {'kind': 'exact_retained_pool_release_grant', 'reason': 'no_native_release_operation_admitted'},
    ])
    return observed, missing


def _result() -> dict[str, Any]:
    return {
        'schema': RESULT_SCHEMA, 'observed_at': datetime.now(UTC).isoformat(),
        'disposition': 'rejected', 'release_authorized': False, 'completion_authority': False,
        'recovery_authority': False, 'source_adoption_authority': False, 'mutations_performed': False,
        'reason_codes': [], 'missing_evidence': [],
    }


def release_admission(
    request: Mapping[str, Any], *, repo_root: Path, runtime_root: Path,
    observe_status: Callable[..., Mapping[str, Any]], observe_source: Callable[[], Mapping[str, Any]],
) -> dict[str, Any]:
    """Correlate exact native read scope and retained custody, always read-only.

    No caller-supplied receipt, local event, task body flag, missing record or
    timeout can authorize release. Future release support requires a separately
    admitted canonical settlement interface and owner-side mutation contract.
    """
    result = _result()
    phase = 'request'
    try:
        _validate_request(request)
        from ipfs_accelerate_py.agent_supervisor.task_sources.control_plane_contracts import content_identity
        from ipfs_accelerate_py.agent_supervisor.merge.worktree_lifecycle import WorktreeLifecycleStore, WorkspaceLifecycleRecord
        from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_supervisor import TodoImplementationSupervisor

        result['request_id'] = content_identity(dict(request))
        phase = 'source_admission'
        source = observe_source()
        _require(isinstance(source, Mapping) and source.get('source_admitted') is True, 'source_not_admitted')
        phase = 'canonical_history'
        before = observe_status(history_tasks=[request['task_alias']])

        def check_native(value: Mapping[str, Any]) -> None:
            owner = value['owner_identity']
            _require(value.get('authoritative_task_observation') is True, 'native_observation_not_admitted')
            _require({key: owner.get(key) for key in OWNER_KEYS} == request['owner_identity'], 'native_owner_identity_mismatch')
            _require(value.get('store_generation') == request['store_generation'], 'native_store_generation_mismatch')
            tasks = [row for row in value['tasks'] if row.get('task_cid') == request['task_cid']]
            _require(len(tasks) == 1 and tasks[0].get('task_alias') == request['task_alias']
                     and tasks[0].get('revision') == request['task_revision'], 'native_task_scope_mismatch')
            _require(set(value['task_histories']) == {request['task_alias']}, 'native_history_scope_mismatch')
            history = value['task_histories'][request['task_alias']]
            _require(history.get('task_cid') == request['task_cid'], 'native_history_task_mismatch')
            unsigned = {key: val for key, val in history.items() if key != 'projection_cid'}
            _require(history.get('projection_cid') == content_identity(unsigned), 'native_history_digest_mismatch')

        check_native(before)
        canonical_observed, missing_evidence = _canonical_missing_evidence(before, request)
        phase = 'retained_custody'
        token = request['pool_lease_token']
        pool_path = runtime_root / 'worktrees/.pool-state' / (token + '.json')
        lock_path = pool_path.with_suffix('.lock')
        evidence: dict[Path, bytes] = {}

        def read(path: Path) -> dict[str, Any]:
            raw = _read_regular(path)
            evidence[path] = raw
            value = json.loads(raw)
            _require(isinstance(value, dict), 'retained_evidence_not_object')
            return value

        pool, lock = read(pool_path), read(lock_path)
        workspace = runtime_root / 'worktrees' / ('workspace_' + token.replace('-', '_'))
        _require(pool.get('schema') == 'agent-supervisor-worktree-pool-v1'
                 and pool.get('state') == 'leased' and pool.get('lease_token') == token
                 and pool.get('repo_root') == str(repo_root) and pool.get('path') == str(workspace),
                 'pool_scope_mismatch')
        _require(type(pool.get('lease_pid')) is int and type(lock.get('pid')) is int
                 and pool['lease_pid'] == lock['pid'] == request['pool_owner']['pid'], 'pool_owner_mismatch')
        store = WorktreeLifecycleStore(repo_root)
        lifecycle_path = store.workspace_path_for(workspace)
        record = WorkspaceLifecycleRecord.from_dict(read(lifecycle_path))
        _require(record.record_id == record.compute_record_id(), 'lifecycle_identity_mismatch')
        _require(record.owner.to_dict() == request['pool_owner'], 'lifecycle_owner_mismatch')
        _require(record.lease_id == request['lifecycle_lease_id'] and record.fence == request['lifecycle_fence'],
                 'lifecycle_lease_or_fence_mismatch')
        _require(record.state.value == 'terminal' and record.task_id == request['task_alias']
                 and record.branch == pool.get('branch') and record.repo_root == str(repo_root)
                 and record.workspace_path == str(workspace), 'lifecycle_scope_not_terminal')
        attempt_dir = Path(record.state_dir)
        relative = attempt_dir.relative_to(runtime_root / 'state')
        _require(len(relative.parts) == 3 and re.fullmatch(r'lane-[0-3]', relative.parts[0]) is not None
                 and relative.parts[1] == f'doep_lane_{relative.parts[0][-1]}_database_portal_attempts'
                 and re.fullmatch(r'[0-9a-f]{24}', relative.parts[2]) is not None, 'attempt_namespace_mismatch')
        read(attempt_dir / 'database-attempt-binding.json')
        projection_path = attempt_dir / 'task-projection.md'
        evidence[projection_path] = _read_regular(projection_path)
        state = read(attempt_dir / 'portal-task-state.json')
        _require(state.get('implementation_in_progress') is False and state.get('active_task_id') == '',
                 'local_callback_not_inactive')
        checker = TodoImplementationSupervisor.__new__(TodoImplementationSupervisor)
        validated = checker._validated_managed_database_lifecycle_binding(record, attempt_root=attempt_dir.parent)
        _require(validated is not None and validated[0] == attempt_dir, 'native_attempt_projection_not_verified')
        binding = validated[1]
        _require(binding.get('task_cid') == request['task_cid'] and binding.get('attempt_id') == request['attempt_id']
                 and binding.get('binding_id') == request['binding_id'], 'database_attempt_binding_mismatch')
        phase = 'final_generation_check'
        after = observe_status(history_tasks=[request['task_alias']])
        check_native(after)
        _require(_canonical_missing_evidence(after, request) == (canonical_observed, missing_evidence),
                 'canonical_release_blockers_changed')
        _require(after['task_histories'] == before['task_histories'], 'canonical_history_changed')
        _require(observe_source() == source, 'source_changed')
        for path, raw in evidence.items():
            _require(_read_regular(path) == raw, 'retained_custody_changed')
        result.update(
            disposition='deferred', task_alias=request['task_alias'], task_cid=request['task_cid'],
            owner_identity=dict(request['owner_identity']), store_generation=dict(request['store_generation']),
            source_observation=source, task_history_projection_cid=after['task_histories'][request['task_alias']]['projection_cid'],
            evidence_digests={str(path.relative_to(repo_root)) if path.is_relative_to(repo_root) else path.name: _digest(raw)
                              for path, raw in evidence.items()},
            local_terminal_lifecycle_verified=True, local_events_admit_release=False,
            reason_codes=['retained_pool_release_not_admitted'],
            canonical_task_observation=canonical_observed, missing_evidence=missing_evidence,
        )
    except AdmissionRejected as exc:
        result['reason_codes'] = [str(exc)]
    except Exception as exc:
        # Preserve fail-closed monitoring on unavailable native transport or
        # bounded evidence reads, without exposing paths, tokens or exception
        # payloads and without retrying a mutation or borrowing another grant.
        result.update(disposition='unavailable', reason_codes=[phase + '_unavailable'], error_class=type(exc).__name__)
    return result


def release_admission_file(path: Path, **context: Any) -> dict[str, Any]:
    """Bound a request file without allowing parse failures to expose its content."""
    try:
        request = read_request(path)
    except AdmissionRejected as exc:
        result = _result()
        result['reason_codes'] = [str(exc)]
        return result
    except (OSError, ValueError, RecursionError) as exc:
        result = _result()
        result.update(disposition='unavailable', reason_codes=['request_unavailable'], error_class=type(exc).__name__)
        return result
    return release_admission(request, **context)
