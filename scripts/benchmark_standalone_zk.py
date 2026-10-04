#!/usr/bin/env python3
"""Measure Groth16 proving and verification in separate 20-worker phases.

No compiler/decompiler calls. The source itself is the public theorem and its
single private axiom. V1 proves commitment knowledge, not theorem entailment.
Existing trusted setup is reused; witness construction is included in proving.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import statistics
import time

from benchmark_autoformal_outputs import ROOT, REPO, LEXICAL, digest, write


def initialize(ready):
    global BACKEND
    from ipfs_datasets_py.logic.zkp.backends.groth16 import Groth16Backend
    BACKEND = Groth16Backend(timeout_seconds=120)
    ready.wait(timeout=120)


def prove(row):
    started = time.perf_counter()
    proof = BACKEND.generate_proof(row['source_text'], [row['source_text']], {'circuit_version': 1})
    seconds = time.perf_counter() - started
    return {'id': row['id'], 'theorem': row['source_text'], 'prove_seconds': seconds, 'proof': proof.to_dict()}


def verify(row):
    from ipfs_datasets_py.logic.zkp import ZKPProof
    started = time.perf_counter()
    proof = ZKPProof.from_dict(row['proof'])
    verified = BACKEND.verify_proof(proof)
    if not verified:
        raise RuntimeError('proof verification failed: ' + row['id'])
    return {'id': row['id'], 'verified': True, 'verify_seconds': time.perf_counter() - started}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workload', type=Path, default=ROOT / 'artifacts/autoformal-throughput-800x20-20261003/workload.json')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cores', type=int, default=20)
    parser.add_argument('--repeats', type=int, default=3)
    args = parser.parse_args()
    rows = json.loads(args.workload.read_text())
    cpus = sorted(os.sched_getaffinity(0))[:args.cores]
    assert len(cpus) == args.cores and len(rows) >= args.cores and args.repeats > 0
    os.sched_setaffinity(0, cpus)
    args.output.mkdir(parents=True, exist_ok=False)
    from ipfs_datasets_py.logic.zkp.backends.groth16 import Groth16Backend
    backend = Groth16Backend().get_backend_info()
    backend['binary_sha256'] = hashlib.sha256(Path(backend['binary_path']).read_bytes()).hexdigest()
    report = {'schema': 'standalone-zk-throughput/v1', 'started_utc': datetime.now(timezone.utc).isoformat(),
              'workload_sha256': digest(rows), 'transactions_per_phase': len(rows), 'cpu_affinity': cpus,
              'compiler_calls': 0, 'decompiler_calls': 0, 'backend': backend,
              'proof_scope': 'Groth16 v1 knowledge of the private source-text commitment; not entailment or translation correctness',
              'proving_scope': 'witness construction, Rust CLI proving, and proof return; serialization/IPC included in phase wall time',
              'verification_scope': 'load already generated in-memory proof objects, deserialize, Rust CLI verify; no generation in measured verification phase',
              'trusted_setup_timed': False, 'source_lexical_tokens': sum(len(LEXICAL.findall(row['source_text'])) for row in rows),
              'producer_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'runs': []}
    write(args.output / 'workload.json', rows)
    context = multiprocessing.get_context('spawn')
    with ProcessPoolExecutor(max_workers=args.cores, mp_context=context, initializer=initialize,
                             initargs=(context.Barrier(args.cores),)) as pool:
        setup_started = time.perf_counter()
        warm = list(pool.map(prove, rows[:args.cores], chunksize=1))
        list(pool.map(verify, warm, chunksize=1))
        report['worker_setup_and_warmup_seconds'] = time.perf_counter() - setup_started
        for repeat in range(args.repeats):
            print(json.dumps({'repeat': repeat + 1, 'phase': 'prove'}), flush=True)
            started = time.perf_counter()
            proofs = list(pool.map(prove, rows, chunksize=1))
            prove_wall = time.perf_counter() - started
            write(args.output / f'proofs-{repeat + 1}.json', proofs)
            print(json.dumps({'repeat': repeat + 1, 'phase': 'verify', 'prove_wall_seconds': prove_wall}), flush=True)
            started = time.perf_counter()
            verified = list(pool.map(verify, proofs, chunksize=1))
            verify_wall = time.perf_counter() - started
            write(args.output / f'verifications-{repeat + 1}.json', verified)
            item = {'repeat': repeat + 1, 'prove_wall_seconds': prove_wall, 'verify_wall_seconds': verify_wall,
                    'prove_transactions_per_second': len(rows) / prove_wall,
                    'verify_transactions_per_second': len(rows) / verify_wall,
                    'prove_source_tokens_per_second': report['source_lexical_tokens'] / prove_wall,
                    'verify_source_equivalent_tokens_per_second': report['source_lexical_tokens'] / verify_wall,
                    'prove_single_transaction_seconds_median': statistics.median(row['prove_seconds'] for row in proofs),
                    'verify_single_transaction_seconds_median': statistics.median(row['verify_seconds'] for row in verified),
                    'proofs_sha256': digest(proofs), 'verifications_sha256': digest(verified), 'verified_count': len(verified)}
            report['runs'].append(item)
            write(args.output / 'report.json', report)
            print(json.dumps(item), flush=True)
    report['medians'] = {key: statistics.median(run[key] for run in report['runs'])
                         for key in report['runs'][0] if key not in {'repeat', 'proofs_sha256', 'verifications_sha256', 'verified_count'}}
    write(args.output / 'report.json', report)


if __name__ == '__main__':
    main()
