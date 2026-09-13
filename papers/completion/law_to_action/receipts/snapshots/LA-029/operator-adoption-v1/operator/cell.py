#!/usr/bin/python3.12
"""Execute exactly one frozen LA015 cell inside an operator-contained group.
Never invokes the original whole-run loop/resource probe. The original arm,
candidate, capability, proof and effect implementations remain byte-identical.
"""
import sys
sys.dont_write_bytecode = True
import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import time

ROOT = Path(__file__).resolve().parents[5]
PAPER = ROOT / 'papers/completion/law_to_action'
HARNESS = PAPER / 'receipts/snapshots/LA-015/run_fixed_actions.py'


def require(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def write(path, value, fresh=True):
    path = Path(path)
    temp = path if fresh else path.with_name(path.name + '.pending')
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as out:
        json.dump(value, out, sort_keys=True, indent=2); out.write('\n'); out.flush(); os.fsync(out.fileno())
    if not fresh:
        os.replace(temp, path)
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)


def boundary():
    root = Path('/sys/fs/cgroup')
    fields = {n: (root / n).read_text().strip() for n in
              ('cpu.max', 'cpuset.cpus.effective', 'memory.max', 'memory.swap.max', 'pids.max')}
    quota, period = fields['cpu.max'].split()
    require(quota != 'max' and int(quota) == int(period), 'Actual one-core quota required')
    cpu = fields['cpuset.cpus.effective']
    require(cpu.isdigit() and os.sched_getaffinity(0) == {int(cpu)}, 'Actual singleton cpuset required')
    require(fields['memory.max'] == '2147483648' and fields['memory.swap.max'] == '0'
            and fields['pids.max'] == '16', 'Actual memory/swap/process controls differ')
    return fields


def load_harness(inputs):
    require(hashlib.sha256(HARNESS.read_bytes()).hexdigest() == inputs['harness_sha256'], 'Frozen arm harness changed')
    for rel, expected in inputs['source_files'].items():
        p = ROOT / rel
        require(not p.is_symlink() and hashlib.sha256(p.read_bytes()).hexdigest() == expected, 'Frozen dependency changed')
    spec = importlib.util.spec_from_file_location('la029_frozen_la015_harness', HARNESS)
    module = importlib.util.module_from_spec(spec); sys.modules[spec.name] = module; spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', required=True, type=Path)
    parser.add_argument('--inputs-sha256', required=True)
    parser.add_argument('--index', required=True, type=int)
    parser.add_argument('--shared', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    require(args.output.is_dir() and not any(args.output.iterdir()), 'Fresh cell output required')
    require(args.shared.is_dir() and args.shared.resolve() == args.shared and args.output.resolve() == args.output, 'Private path redirected')
    write(args.output / 'child_started.json', {'schema': 'la029-cell-start/v1', 'index': args.index,
          'pid': os.getpid(), 'wall_time': time.time(), 'scientific_result': False})
    require(hashlib.sha256(args.inputs.read_bytes()).hexdigest() == args.inputs_sha256, 'Frozen input envelope changed')
    inputs = json.loads(args.inputs.read_bytes())
    require(inputs['schema'] == 'la029-frozen-fixed-action-inputs/v1' and len(inputs['schedule']) == 900
            and len(inputs['candidates']) == 60 and 0 <= args.index < 900, 'Frozen population/index mismatch')
    slot = inputs['schedule'][args.index]
    candidates = {c['candidate_id']: c for c in inputs['candidates']}
    require(len(candidates) == 60 and slot['case_id'] in candidates, 'Frozen candidate membership mismatch')
    observed = boundary()
    write(args.output / 'child_boundary.json', observed)
    # The controller holds a distinct run lock. This shared-state lock covers
    # every native store/key access by the one authorized cell process.
    lock = os.open(args.shared / 'cell.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        ready_path = args.shared / 'ready.json'
        if args.index:
            require(ready_path.is_file(), 'Shared state never initialized; no replacement')
            ready = json.loads(ready_path.read_bytes())
            require(ready['next_index'] == args.index and ready['inputs_sha256'] == args.inputs_sha256,
                    'Predecessor incomplete or source changed; no replay')
        else:
            require(not ready_path.exists() and not (args.shared / 'initialization.used.json').exists(), 'Consumed initialization')
            write(args.shared / 'initialization.used.json', {'index': 0, 'inputs_sha256': args.inputs_sha256})
        write(args.shared / f'cell-{args.index:04d}.used.json', {'index': args.index, 'slot': slot,
              'inputs_sha256': args.inputs_sha256, 'result': 'unknown_before_dispatch'})
        scratch = args.output / 'scratch'; scratch.mkdir(mode=0o700)
        os.environ['TMPDIR'] = str(scratch); tempfile.tempdir = str(scratch)
        harness = load_harness(inputs)
        baselines = harness.load_baselines(); config = baselines.load_arms()
        require(digest(config) == inputs['arms_canonical_sha256'], 'Arm configuration changed')
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives import serialization
        from ipfs_kit_py.mcp_server.mcplusplus.revocation import RevocationLedger
        from ipfs_kit_py.mcp_server.mcplusplus.ucan import public_key_bytes
        key_path = args.shared / 'study_ed25519.private'
        ledger_path = args.shared / 'shared-ucan-ledger.json'
        if args.index == 0:
            require(not key_path.exists() and not ledger_path.exists() and not (args.shared / 'control.duckdb').exists(), 'Shared state unexpectedly preexists')
            key = Ed25519PrivateKey.generate()
            data = key.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
            fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, 'wb') as out: out.write(data); out.flush(); os.fsync(out.fileno())
            ledger = RevocationLedger(ledger_path)
            ledger.register_public_key(baselines.ISSUER, 'root-v1', public_key_bytes(key))
            ready = {'next_index': 0, 'inputs_sha256': args.inputs_sha256,
                     'public_key_sha256': hashlib.sha256(public_key_bytes(key)).hexdigest()}
        else:
            require(key_path.is_file() and not key_path.is_symlink() and ledger_path.is_file()
                    and (args.shared / 'control.duckdb').is_file(), 'Persistent shared bytes missing; no replacement')
            key = Ed25519PrivateKey.from_private_bytes(key_path.read_bytes())
            require(hashlib.sha256(public_key_bytes(key)).hexdigest() == ready['public_key_sha256'], 'Study key changed')
        durable = baselines.load_durable()
        store = durable.DuckDBCapabilityConsumptionStore(args.shared / 'control.duckdb', owner_id='owner:la-015')
        try:
            store.attach()
            write(args.output / 'dispatch_started.json', {'slot': slot, 'index': args.index, 'wall_time': time.time(),
                  'original_implementation_revision': inputs['original_implementation_revision'],
                  'original_source_head': inputs['original_source_head'], 'public_key_sha256': ready['public_key_sha256']})
            # The host independently admits resource observations after group
            # termination. A child boolean cannot confer scoring authority.
            row = harness.run_slot(baselines, slot=slot, candidate=candidates[slot['case_id']], config=config,
                                   store=store, shared={'root_key': key, 'ledger_path': str(ledger_path)},
                                   revision=inputs['original_implementation_revision'], scored=False)
        finally:
            store.close()
        require(row['attempt_id'] == slot['attempt_id'] and row['case_id'] == slot['case_id']
                and row['arm_id'] == slot['arm_id'] and row['seed'] == slot['seed'], 'Result identity differs')
        write(args.output / 'result.json', {'schema': 'la029-fixed-action-cell-result/v1', 'index': args.index,
              'inputs_sha256': args.inputs_sha256, 'slot': slot, 'result': row,
              'child_claims_scored_admission': False, 'public_key_sha256': ready['public_key_sha256'],
              'mechanism_source_unchanged': True, 'store_close_completed': True})
        ready['next_index'] = args.index + 1
        write(ready_path, ready, fresh=args.index == 0)
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN); os.close(lock)


if __name__ == '__main__':
    main()
