#!/usr/bin/env python3
"""Portable, offline counts and byte-provenance audit; Python 3.9+ only.

This reproduces recorded structural outcomes, not independent legal fidelity.
No model, solver, package installation, or network access is required.
"""
import argparse
import collections
import hashlib
import json
import math
import re
from pathlib import Path


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_text())


def verify(root):
    root = root.resolve()
    manifest = read(root / 'MANIFEST.json')
    for entry in manifest['files']:
        path = (root / entry['bundle_path']).resolve()
        assert path.is_relative_to(root), 'Unsafe manifest path'
        assert sha(path.read_bytes()) == entry['bundle_sha256'], entry['bundle_path']
    source_bytes = (root / 'sources.jsonl').read_bytes()
    assert sha(source_bytes) == '2f0b5e35d5e0c4864745aa8e06f1a4e47e42d1b1fbdc8a90f7d4b03a49961d66'
    sources = [json.loads(line) for line in source_bytes.decode().splitlines()]
    rows = [json.loads(line) for line in (root / 'results.jsonl').read_text().splitlines()]
    assert len(sources) == len(rows) == 100
    assert len({row['record_id'] for row in sources}) == len({row['record_id'] for row in rows}) == 100
    source_index = {source['record_id']: index for index, source in enumerate(sources)}
    protocol = read(root / 'frozen_natural_protocol.json')
    formula_bodies = 0
    for row in rows:
        index = source_index[row['record_id']]
        source = sources[index]
        folder = root / 'records' / f'record-{index:03d}'
        assert read(folder / 'result.json') == row
        raw = str(source['text'])
        normalized = re.sub(r'\s+', ' ', raw[:4096]).strip()
        request = read(folder / 'request.json')
        assert request == dict(model='leanstral_local', messages=[dict(role='user', content=protocol['prompt_base'] + normalized)], temperature=0, seed=20260914, max_tokens=2048, reasoning_effort='none', stream=False, stop=['</s>'])
        assert row['text_sha256'] == sha(raw[:4096].encode())
        assert row['full_text_sha256'] == sha(raw.encode())
        assert row['prompt_sha256'] == sha(request['messages'][0]['content'].encode())
        assert row['independent_semantic_fidelity_measured'] is False
        if row['status'] == 'measured':
            assert row.get('model_format_accepted') is True
            assert 'canonical_ir' in row
            assert set(row.get('checks', {})) == {'modal_well_formedness', 'provenance_preservation'}
            assert all(type(check.get('passed')) is bool for check in row['checks'].values())
        if row.get('model_response_received'):
            response = read(folder / 'request_response.json')
            choice = response['choices'][0]
            assert row['finish_reason'] == choice.get('finish_reason')
            assert row['usage'] == response.get('usage')
            if 'canonical_ir' in row:
                assert choice['finish_reason'] == 'stop'
                original = json.loads(choice['message']['content'])
                assert set(original) == {'formulas'}
                ir = row['canonical_ir']
                assert ir['normalized_text'] == normalized
                assert ir['document_id'] == row['record_id']
                assert len(ir['formulas']) == len(original['formulas']) == row['formula_count']
                for formula_index, (before, after) in enumerate(zip(original['formulas'], ir['formulas'])):
                    assert after['formula_id'] == f"{row['record_id']}:f{formula_index:04d}"
                    assert after['provenance']['source_id'] == row['record_id']
                    assert after['metadata'] == {}
                    for key in ['operator', 'predicate', 'conditions', 'exceptions']:
                        assert before[key] == after[key]
                    for key in ['start_char', 'end_char']:
                        assert before['provenance'][key] == after['provenance'][key]
                    formula_bodies += 1
        else:
            assert row['status'] == 'request_failed'
    valid = [row for row in rows if row['status'] == 'measured' and all(check['passed'] for check in row.get('checks', {}).values())]
    counts = dict(planned=100, attempted=len(rows), statuses=dict(collections.Counter(row['status'] for row in rows)),
                  responses=sum(row.get('model_response_received', False) for row in rows),
                  complete_responses=sum(row.get('finish_reason') == 'stop' for row in rows),
                  formats_accepted=sum(row.get('model_format_accepted', False) for row in rows),
                  structural_and_provenance_pass=len(valid),
                  nonempty_eligible=sum(row.get('formula_count', 0) > 0 for row in valid),
                  empty_valid=sum(row.get('formula_count', 0) == 0 for row in valid),
                  formula_count=sum(row.get('formula_count', 0) for row in valid),
                  exact_nonempty_cycles=sum(row.get('formula_count', 0) > 0 and row.get('cycle', {}).get('exact_semantic_field_multiset', False) for row in valid),
                  cycles_measured=sum(row.get('cycle', {}).get('status') == 'measured' for row in valid),
                  cycle_statuses=dict(collections.Counter(row.get('cycle', {}).get('status', 'not_attempted') for row in rows)),
                  inference_wall_seconds=sum(row.get('inference_seconds', 0) for row in rows),
                  total_record_wall_seconds=sum(row['wall_seconds'] for row in rows),
                  prompt_tokens=sum((row.get('usage') or {}).get('prompt_tokens', 0) for row in rows),
                  completion_tokens=sum((row.get('usage') or {}).get('completion_tokens', 0) for row in rows))
    recorded = read(root / 'natural_summary.json')
    for key, value in counts.items():
        assert math.isclose(value, recorded[key], rel_tol=1e-12, abs_tol=1e-6) if isinstance(value, float) else value == recorded[key], key
    return dict(passed=True, verified_manifest_files=len(manifest['files']), unchanged_formula_bodies=formula_bodies, counts=counts,
                model_calls=0, native_checker_reexecution=False, semantic_fidelity_established=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--bundle', type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    print(json.dumps(verify(args.bundle), indent=2))
