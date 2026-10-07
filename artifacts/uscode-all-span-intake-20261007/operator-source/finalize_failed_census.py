"""Audit and release only this campaign's stopped, durable first census claim."""
import copy
import hashlib
import json
import os
from pathlib import Path
import sys

BASE = Path('/home/barberb/lift_coding')
HELPERS = BASE / 'artifacts/autoencoder-dual-bank-fit-20261007/parent-replay-guardian-source-r2'
sys.path.insert(0, str(HELPERS))
from run_reserved import resource_owner, PACKAGE
from adopt_shared_scheduler import read_existing

RESERVATION = 'b5ce1c6fcdeb479fb79389795aaaddf7'
ATTEMPT = PACKAGE / 'workspace/test-logs/uscode-all-span-intake-20261007/source-census-01'
RECEIPT = BASE / 'artifacts/uscode-all-span-intake-20261007/failed-census-claim-release.json'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def main():
    if RECEIPT.exists():
        raise ValueError('audited release receipt already exists')
    resources = resource_owner()
    failure = json.loads((ATTEMPT / 'failure.json').read_bytes())
    record = failure['resources']['record']
    if (record['reservation_id'] != RESERVATION or record['attempt_directory']['path'] != str(ATTEMPT)
            or failure['cleanup']['leader_reaped'] is not True
            or failure['cleanup']['live_group_processes'] != 0):
        raise ValueError('failure receipt does not bind this exact stopped owned attempt')
    if resources._process(record['owner_pid']) is not None:
        raise ValueError('original owner PID is present; refuse recovery or PID reuse')
    child = failure['cleanup']['identity']
    if resources._group_usage(child)['live_processes']:
        raise ValueError('recorded child process group remains alive')
    lease = failure['resources']['resource_lease']
    state, _ = read_existing(Path('/tmp/ipfs-datasets-resource-scheduler-1000.json'))
    if lease['lease_id'] in state['leases']:
        raise ValueError('original lease is still present; recovery never edits scheduler claims')
    roots = [PACKAGE / 'workspace/test-logs', PACKAGE / 'workspace/todo-queues',
             PACKAGE / 'docs/implementation/reports/evidence', Path('/tmp/pytest-of-barberb')]
    owner = resources.DaemonResourceReservation(failure['resources']['ledger_path'], roots=roots,
        storage_bytes=record['storage_bytes'], memory_mb=record['memory_mb'],
        cpu_slots=record['cpu_slots'], child_process_slots=record['child_process_slots'],
        ledger_lock_timeout_seconds=60)
    # Legacy release explicitly supports audited recovery. Do not acquire a
    # replacement lease, transfer the ledger owner, or alter another claim.
    owner.reservation_id = RESERVATION
    owner._entered = True
    owner._attempt = copy.deepcopy(record['attempt_directory'])
    owner._child = copy.deepcopy(child)
    with owner._locked():
        before = owner._read()
        original = before['reservations'][RESERVATION]
        if (original['status'] != 'retained' or original['owner_pid'] != record['owner_pid']
                or original['attempt_directory'] != record['attempt_directory']
                or original['storage_bytes'] != record['storage_bytes']):
            raise ValueError('live retained claim differs from the owned failure receipt')
        owner._record = copy.deepcopy(original)
        foreign_before = digest({k:v for k,v in before['reservations'].items() if k != RESERVATION})
    pins = {}
    for path in ATTEMPT.rglob('*'):
        if path.is_symlink():
            raise ValueError('owned failure evidence contains a symlink')
        if path.is_file():
            with path.open('rb') as stream:
                h = hashlib.sha256()
                for chunk in iter(lambda: stream.read(1024*1024), b''):
                    h.update(chunk)
                os.fsync(stream.fileno())
            pins[str(path)] = {'bytes':path.stat().st_size, 'sha256':h.hexdigest()}
    for path in sorted([ATTEMPT]+[p for p in ATTEMPT.rglob('*') if p.is_dir()],
                       key=lambda p:len(p.parts), reverse=True):
        fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    final = owner.release(artifacts_durable=True)
    with owner._locked():
        after = owner._read()
        foreign_after = digest({k:v for k,v in after['reservations'].items() if k != RESERVATION})
    receipt = dict(schema='owned-failed-census-claim-release/v1', reservation_id=RESERVATION,
        attempt=str(ATTEMPT), old_owner_pid=record['owner_pid'], source_only=True,
        artifacts=pins, resources=final, original_child_group_dead=True,
        original_lease_absent=True, replacement_lease_acquired=False,
        foreign_claims_before_sha256=foreign_before, foreign_claims_after_sha256=foreign_after,
        foreign_snapshot_equal=foreign_before == foreign_after,
        evidence_removed=False, scheduler_mutated=False)
    with RECEIPT.open('x') as stream:
        json.dump(receipt, stream, sort_keys=True, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps(dict(status=final['status'], reservation_id=RESERVATION,
                         foreign_snapshot_equal=foreign_before == foreign_after)), flush=True)


if __name__ == '__main__':
    main()
