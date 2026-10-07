"""Read-only forecast using exact frozen inventory functions; never admit work.

The only dynamically evaluated statements are listed AST class/function nodes
from the authenticated owner. No owner package, scheduler, model, or encoder is
imported or instantiated. Shared atomic files are read, never locked or written.
The actual guardian must still obtain fresh locked admission.
"""
import ast
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import time

W = Path('/home/barberb/lift_coding')
G = W / 'artifacts/autoencoder-dual-bank-replay-20261007/guardian'
OWNER = W / 'external/ipfs_datasets/workspace/test-logs/native4096-four-width-20261004/resource-cap/autoencoder_daemon_resources.py'
OWNER_SHA = 'b00d2752ba852fe73760bba4fbd51b0e845742c3527642606a2a77ed9f8f5e2c'
LEDGER = W / 'external/ipfs_datasets/workspace/test-logs/federal-corpus-audits/owned-daemon-resource-control/disk-reservations.json'
FUNCTIONS = ('_safe_path', '_checked_path', '_root_identity', '_inventory_descendant',
             '_inventory_entry_disappeared', '_inventory', '_process')


def stable_read(path, limit):
    path = Path(path)
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or path.is_symlink() or before.st_size > limit:
        raise ValueError('bounded regular shared file required')
    raw = path.read_bytes()
    after = path.lstat()
    identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    if identity(before) != identity(after) or len(raw) != before.st_size:
        raise ValueError('shared atomic file changed during read; retry later')
    return json.loads(raw), dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
                                device=before.st_dev, inode=before.st_ino)


def main():
    started = time.monotonic()
    raw = OWNER.read_bytes()
    if hashlib.sha256(raw).hexdigest() != OWNER_SHA:
        raise ValueError('frozen resource owner changed')
    parsed = ast.parse(raw)
    selected = [node for node in parsed.body
                if isinstance(node, ast.FunctionDef) and node.name in FUNCTIONS
                or isinstance(node, ast.ClassDef) and node.name == 'DaemonResourceError']
    if len(selected) != len(FUNCTIONS) + 1:
        raise ValueError('exact read-only owner function inventory required')
    namespace = dict(os=os, Path=Path, stat=stat, MAX_INVENTORY_ENTRIES=2_000_000)
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(OWNER), 'exec'), namespace)
    ledger_before, ledger_binding_before = stable_read(LEDGER, 8 * 1024 * 1024)
    roots = [Path(record['path']) for record in ledger_before['roots']]
    if ledger_before['limit_bytes'] != 145_000_000_000:
        raise ValueError('existing 145 GB ledger required; never migrate here')
    if [namespace['_root_identity'](path) for path in roots] != ledger_before['roots']:
        raise ValueError('named resource root identities differ')
    inventory_started = time.monotonic()
    inventory = namespace['_inventory'](roots)
    inventory_seconds = time.monotonic() - inventory_started
    ledger, ledger_binding_after = stable_read(LEDGER, 8 * 1024 * 1024)
    if ledger['roots'] != ledger_before['roots'] or ledger['limit_bytes'] != ledger_before['limit_bytes']:
        raise ValueError('resource owner roots/cap changed during census')
    outstanding = sum(row['storage_bytes'] for row in ledger['reservations'].values()
                      if row['status'] != 'released')
    charged = inventory['apparent_bytes'] + outstanding
    free = min(shutil.disk_usage(path).free for path in roots)
    scheduler_path = Path(os.environ.get('IPFS_DATASETS_RESOURCE_SCHEDULER_PATH',
                                        f'/tmp/ipfs-datasets-resource-scheduler-{os.getuid()}.json')).resolve()
    scheduler, scheduler_binding = stable_read(scheduler_path, 16 * 1024 * 1024)
    active_totals = Counter()
    lease_live_identity_census = Counter()
    for lease in scheduler['leases'].values():
        for key in ('cpu_slots', 'memory_mb', 'child_process_slots', 'gpu_memory_mb', 'unified_memory_mb'):
            active_totals[key] += lease.get(key, 0)
        process = namespace['_process'](lease.get('owner_pid', -1))
        lease_live_identity_census['owner_pid_present' if process else 'owner_pid_absent'] += 1
    meminfo = {}
    for line in Path('/proc/meminfo').read_text().splitlines():
        key, value = line.split(':', 1)
        if key in ('MemTotal', 'MemAvailable', 'SwapTotal', 'SwapFree'):
            meminfo[key + '_bytes'] = int(value.strip().split()[0]) * 1024
    forecast = {}
    for phase, additional in (('preflight', 100_000_000), ('training', 400_000_000), ('evaluation', 100_000_000)):
        forecast[phase] = dict(requested_storage_bytes=additional, requested_memory_mib=1536,
                              requested_cpu_slots=1, requested_child_process_slots=1,
                              charged_if_admitted_bytes=charged + additional,
                              named_root_cap_headroom_after_request_bytes=145_000_000_000 - charged - additional,
                              snapshot_storage_forecast_passes=(charged + additional <= 145_000_000_000
                                                                and free >= outstanding + additional))
    result = dict(schema='dual-bank-read-only-resource-forecast/v1', complete=True,
                  created_at_unix=time.time(), elapsed_seconds=time.monotonic() - started,
                  frozen_owner=dict(path=str(OWNER), sha256=OWNER_SHA, bytes=len(raw)),
                  exact_AST_readonly_functions=list(FUNCTIONS), inventory=inventory,
                  inventory_seconds=inventory_seconds, roots=ledger['roots'],
                  ledger_before=ledger_binding_before, ledger_after=ledger_binding_after,
                  ledger_bytes_unchanged_during_census=(ledger_binding_before == ledger_binding_after),
                  outstanding_full_reservations_bytes=outstanding,
                  reservation_counts_by_status=dict(Counter(row['status'] for row in ledger['reservations'].values())),
                  observed_apparent_bytes=inventory['apparent_bytes'], charged_snapshot_bytes=charged,
                  cap_bytes=145_000_000_000, headroom_snapshot_bytes=145_000_000_000 - charged,
                  minimum_filesystem_free_bytes=free, phase_forecast=forecast,
                  scheduler_binding=scheduler_binding, scheduler_config=scheduler['config'],
                  scheduler_config_sha256=hashlib.sha256(json.dumps(scheduler['config'], sort_keys=True,
                                                                   separators=(',', ':')).encode()).hexdigest(),
                  scheduler_lease_count=len(scheduler['leases']), scheduler_waiter_count=len(scheduler['waiters']),
                  raw_claim_totals=dict(active_totals), lease_owner_pid_observation=dict(lease_live_identity_census),
                  stale_lease_recovery_performed=False, host_memory_snapshot=meminfo,
                  process_cpu_affinity_slots=len(os.sched_getaffinity(0)),
                  accounting_scope='Named-root apparent pathname bytes; hardlinks count per pathname; full unreleased claims added. Census and unlocked ledger snapshots are not one atomic admission.',
                  forecast_not_admission=True, availability_not_reserved=True,
                  resource_lease_or_reservation_acquired=False, shared_state_written=False,
                  shared_config_changed=False, foreign_claims_modified=False,
                  package_or_scheduler_imported=False, model_or_encoder_imported=False,
                  models_executed=False, execution_readiness_granted=False,
                  qualified=False, admitted=False, Lake_executed=False)
    target = G / 'resource-availability-readonly-r1.json'
    with target.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True); stream.write('\n')
    print(json.dumps(dict(path=str(target), sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                          bytes=target.stat().st_size, headroom_snapshot_bytes=result['headroom_snapshot_bytes'],
                          phase_forecast=forecast, scheduler_leases=result['scheduler_lease_count'],
                          scheduler_waiters=result['scheduler_waiter_count'])))


if __name__ == '__main__':
    main()
