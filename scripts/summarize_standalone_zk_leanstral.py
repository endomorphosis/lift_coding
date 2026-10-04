#!/usr/bin/env python3
"""Validate the corrected independent-ZK and Leanstral throughput comparison."""
import argparse
import json
import math
from pathlib import Path
import statistics

from benchmark_autoformal_outputs import digest, ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, default=ROOT / 'artifacts/autoformal-throughput-800x20-20261003-summary/summary.json')
    parser.add_argument('--zk', type=Path, default=ROOT / 'artifacts/autoformal-standalone-zk-800x20-20261003')
    parser.add_argument('--leanstral', type=Path, required=True)
    args = parser.parse_args()
    baseline = json.loads(args.baseline.read_text())
    zk = json.loads((args.zk / 'report.json').read_text())
    lean = json.loads((args.leanstral / 'report.json').read_text())
    assert zk['compiler_calls'] == zk['decompiler_calls'] == 0
    assert zk['workload_sha256'] == lean['workload_sha256'] == baseline['workload_sha256']
    assert lean['status'] == 'completed' and lean['original_service_restored'] is True
    assert zk['cpu_affinity'] == lean['server_cpu_affinity'] == list(range(20))
    workload = json.loads((args.zk / 'workload.json').read_text())
    assert len(workload) == 800 and digest(workload) == zk['workload_sha256']
    proofs_checked, vectors_checked = 0, 0
    for run in zk['runs']:
        proofs = json.loads((args.zk / f"proofs-{run['repeat']}.json").read_text())
        verifications = json.loads((args.zk / f"verifications-{run['repeat']}.json").read_text())
        assert digest(proofs) == run['proofs_sha256'] and digest(verifications) == run['verifications_sha256']
        assert len(proofs) == len(verifications) == run['verified_count'] == 800
        assert math.isclose(run['prove_transactions_per_second'], 800 / run['prove_wall_seconds'])
        assert math.isclose(run['verify_transactions_per_second'], 800 / run['verify_wall_seconds'])
        for source, proof, verification in zip(workload, proofs, verifications, strict=True):
            assert source['id'] == proof['id'] == verification['id']
            assert proof['theorem'] == source['source_text'] == proof['proof']['public_inputs']['theorem']
            assert verification['verified'] is True
            assert not {'ir', 'text', 'vocabulary'} & proof.keys()
        proofs_checked += len(proofs)
    native_tokens = sum(len(row['tokens']) for row in lean['token_receipts'])
    first_vectors = None
    max_replay_l2 = 0
    for run in lean['runs']:
        outputs = json.loads((args.leanstral / f"outputs-{run['repeat']}.json").read_text())
        assert digest(outputs) == run['outputs_sha256'] and len(outputs) == 800
        assert run['native_input_tokens'] == native_tokens
        assert math.isclose(run['transactions_per_second'], 800 / run['wall_seconds'])
        for source, output in zip(workload, outputs, strict=True):
            assert source['id'] == output['id']
            assert len(output['embedding']) == 4096
            assert all(math.isfinite(value) for value in output['embedding'])
            assert abs(math.hypot(*output['embedding']) - 1) < 1e-4
        vectors = [row['embedding'] for row in outputs]
        if first_vectors is not None:
            difference = max(math.sqrt(sum((a-b)**2 for a, b in zip(left, right, strict=True)))
                             for left, right in zip(vectors, first_vectors, strict=True))
            max_replay_l2 = max(max_replay_l2, difference)
            assert difference <= 1e-3
        else:
            first_vectors = vectors
        vectors_checked += len(outputs)
    results = {}
    for method in ['compiler', 'spacy8', 'gte384', 'gte768']:
        row = baseline['methods'][method]
        results[method] = {'label': row['label'], 'wall_seconds_800_median': 800 / row['transactions_per_second_median'],
                          'transactions_per_second': row['transactions_per_second_median'],
                          'source_equivalent_tokens_per_second': row['source_lexical_tokens_per_second_median'],
                          'native_input_tokens_per_second': row['native_input_tokens_per_second_median'],
                          'hardware': '20 CPU cores', 'scope': 'earlier three matched-workload measurements'}
    for phase in ['prove', 'verify']:
        medians = zk['medians']
        key = 'prove_source_tokens_per_second' if phase == 'prove' else 'verify_source_equivalent_tokens_per_second'
        results['zk_' + phase] = {'label': 'Standalone Groth16 ' + ('proof generation' if phase == 'prove' else 'proof verification'),
                                 'wall_seconds_800_median': medians[phase + '_wall_seconds'],
                                 'transactions_per_second': medians[phase + '_transactions_per_second'],
                                 'source_equivalent_tokens_per_second': medians[key], 'native_input_tokens_per_second': None,
                                 'single_transaction_seconds_median': medians[phase + '_single_transaction_seconds_median'],
                                 'hardware': '20 CPU cores', 'scope': zk[('proving' if phase == 'prove' else 'verification') + '_scope']}
    results['leanstral4096'] = {'label': '4096D Leanstral (last pooling)', 'hardware': '20 CPU threads + existing CUDA GPU offload',
                               'wall_seconds_800_median': lean['medians']['wall_seconds'],
                               'transactions_per_second': lean['medians']['transactions_per_second'],
                               'source_equivalent_tokens_per_second': lean['medians']['source_lexical_tokens_per_second'],
                               'native_input_tokens_per_second': lean['medians']['native_input_tokens_per_second'],
                               'scope': lean['timing_scope']}
    summary = {'schema': 'independent-zk-leanstral-comparison/v1', 'workload_sha256': zk['workload_sha256'],
               'replacement_synthetic_workload': True, 'transactions_per_method_per_run': 800, 'repeats': 3,
               'methods': results, 'zk_report': str(args.zk / 'report.json'), 'leanstral_report': str(args.leanstral / 'report.json'),
               'baseline_report': str(args.baseline), 'standalone_proofs_checked': proofs_checked,
               'leanstral_vectors_checked': vectors_checked, 'leanstral_max_replay_l2': max_replay_l2,
               'leanstral_single_batch_equivalent_at_1e_3': lean['canary']['single_batch_equivalent_at_1e_3'],
               'original_leanstral_generation_service_restored': True}
    lines = ['# Corrected 800-transaction throughput comparison', '',
             'Median of three warm measurements of 800 distinct replacement synthetic statements. Twenty CPUs; shared-host contention is uncontrolled.',
             'ZK generation and verification are standalone, independently timed phases. Neither phase invokes the compiler or decompiler.', '',
             '| Method | Seconds / 800 | Transactions/s | Source-equivalent tokens/s | Native input tokens/s |',
             '| --- | ---: | ---: | ---: | ---: |']
    for row in results.values():
        native = row['native_input_tokens_per_second']
        lines.append(f"| {row['label']} | {row['wall_seconds_800_median']:.4f} | {row['transactions_per_second']:.2f} | "
                     f"{row['source_equivalent_tokens_per_second']:.2f} | {f'{native:.2f}' if native is not None else '—'} |")
    lines += ['', 'Source-equivalent tokens/s uses 6,400 Unicode source words/punctuation per 800 transactions. Verification receives serialized proofs, not source tokens; its token rate is a workload-equivalent normalization. Native tokens use actual encoder tokenization, including special tokens for GTE and Leanstral.', '',
              'The ZK circuit is Groth16 v1 knowledge of an axiom commitment, using each source as the public theorem and single private axiom. It does not prove semantic entailment or translation correctness. Existing trusted setup is excluded; witness construction, CLI proving and proof return are included in generation. Verification includes deserialization and the Rust verifier, and excludes generation.',
              f"Median per-worker generation call: {zk['medians']['prove_single_transaction_seconds_median']*1000:.3f} ms; verification call: {zk['medians']['verify_single_transaction_seconds_median']*1000:.3f} ms. These are concurrent call latencies, distinct from aggregate 20-worker throughput.", '',
              'Leanstral uses the same local 119B-A6B NVFP4 GGUF and requested CUDA offload as the existing generation service, with twenty CPU threads and sixteen parallel slots. It is GPU assisted; the other rows use CPUs. Exact raw source text is last-token pooled to real finite normalized 4096D hidden vectors. No logits, padded smaller vectors, or chat-template text are used.',
              'All slot caches are erased before every batch. Each batch has at most one input per empty slot; cache erasure, HTTP, inference, and output validation are included in the main wall time. Server load and token-evidence collection are excluded. Request-only and cache-clear times are retained separately.',
              f"Single/batch canary L2 difference: {lean['canary']['single_vs_batch_l2']:.8g}; A/B/A replay: {lean['canary']['a_b_a_replay_l2']:.8g}; maximum full-workload repeat difference: {max_replay_l2:.8g}. Registered tolerance: 1e-3.", '',
              'Single-versus-batch equivalence FAILED at that tolerance. These are fixed-batch throughput measurements, not evidence that changing the batch shape preserves the embedding. The original failed equivalence receipt is retained in artifacts/autoformal-leanstral4096-800x20-20261003/report.json. Full-workload repeatability within the fixed batch profile passed.', '',
              'The compiler, 8D, 384D and 768D rows retain the earlier three measurements on the identical hashed workload. Encoding rows measure vector production rather than full formalization. All generated proof and vector outputs are preserved.',
              f'Validated {proofs_checked} standalone proof/verification records and {vectors_checked} native Leanstral vectors. The original generation service was restored and passed its health check.', '',
              'Replay standalone ZK: `python3 scripts/benchmark_standalone_zk.py --output artifacts/NEW-ZK-RUN`.',
              'Replay Leanstral (stops and restores the managed generation service): `python3 scripts/benchmark_leanstral_embeddings.py --output artifacts/NEW-LEANSTRAL-RUN`.']
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    (args.output / 'summary.md').write_text('\n'.join(lines) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
