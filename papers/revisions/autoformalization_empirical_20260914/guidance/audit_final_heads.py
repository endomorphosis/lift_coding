#!/usr/bin/env python3
"""Describe emitted T3 head variation without new predictions or outcome tuning."""
import argparse
import collections
import hashlib
import json
from pathlib import Path

SEEDS = (104729, 130363, 155921)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--predictions', nargs=3, required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    reports, source_ids = {}, None
    for path in args.predictions:
        receipt = json.loads(Path(str(path) + '.receipt.json').read_text())
        if receipt['count'] != 1913 or receipt['split'] != 'final' or receipt['predictions_sha256'] != sha(path):
            raise ValueError('Incomplete or unbound final prediction file')
        rows = [json.loads(line) for line in path.open()]
        ids = [row['record_id'] for row in rows]
        if len(ids) != 1913 or len(set(ids)) != 1913 or (source_ids is not None and ids != source_ids):
            raise ValueError('Source cohort or order differs')
        source_ids = ids
        seeds = {row['seed'] for row in rows}
        if len(seeds) != 1 or not seeds.issubset(SEEDS):
            raise ValueError('Unexpected seed')
        seed = seeds.pop()
        if str(seed) in reports or any(row['arm_id'] != 'T3' or row['reference_targets_used'] for row in rows):
            raise ValueError('Unexpected arm or target use')
        contexts = sorted(rows[0]['proof_heads_by_family'])
        if any(sorted(row['proof_heads_by_family']) != contexts for row in rows):
            raise ValueError('Head context schema differs')
        head_variants, head_counts = {}, collections.Counter()
        per_context = {}
        for context in contexts:
            variants, counts = {}, collections.Counter()
            for row in rows:
                head = row['proof_heads_by_family'][context]['heads']
                head_hash = digest(head)
                head_variants[head_hash] = head
                head_counts[head_hash] += 1
                probabilities = head['obligation_family']['probabilities']
                probability_hash = digest(probabilities)
                variants[probability_hash] = probabilities
                counts[probability_hash] += 1
            per_context[context] = {
                'source_records': len(rows),
                'unique_obligation_probability_vectors': len(variants),
                'probability_variants': [dict(probabilities=variants[key], count=counts[key]) for key in sorted(variants)],
            }
        reports[str(seed)] = {
            'input_filename': path.name,
            'input_sha256': sha(path),
            'receipt_sha256': sha(Path(str(path) + '.receipt.json')),
            'source_records': len(rows),
            'contexts': per_context,
            'unique_complete_head_vectors_across_sources_and_contexts': len(head_variants),
            'head_variants': [dict(sha256=key, occurrences=head_counts[key], heads=head_variants[key]) for key in sorted(head_variants)],
            'original_emitted_head_vectors': len(rows) * len(contexts),
            'within_context_source_probability_variation_observed': any(v['unique_obligation_probability_vectors'] != 1 for v in per_context.values()),
        }
    if set(reports) != {str(seed) for seed in SEEDS}:
        raise ValueError('Missing seed')
    output = {
        'schema': 'descriptive-final-T3-head-audit/v1',
        'source_records_per_seed': 1913,
        'seed_reports': reports,
        'new_model_calls': 0,
        'new_model_head_calls': 0,
        'interpretation': 'Counts describe already emitted native fixed-context heads. A constant learned obligation prior can change scheduling but is not source-specific discrimination. Singleton categorical heads have probability one by vocabulary construction; they are not calibrated probabilities of proof truth, trusted acceptance, semantic fidelity, or reconstruction correctness.',
    }
    with args.output.open('x') as stream:
        stream.write(json.dumps(output, indent=2) + '\n')
    print(json.dumps({seed: report['unique_complete_head_vectors_across_sources_and_contexts'] for seed, report in reports.items()}))


if __name__ == '__main__':
    main()
