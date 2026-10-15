#!/usr/bin/env python3
"""Audit saved natural attempts without calling a model or changing scoring.

This checks retention, source/request binding, and unedited semantic fields.
It does not establish that a model's interpretation is faithful to the source.
"""
import argparse
import hashlib
import importlib.util
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXPECTED_INPUT_SHA = '2f0b5e35d5e0c4864745aa8e06f1a4e47e42d1b1fbdc8a90f7d4b03a49961d66'


def sha(value):
    return hashlib.sha256(value).hexdigest()


def read(path):
    return json.loads(path.read_text())


def audit(require_complete=False):
    protocol = read(HERE / 'frozen_natural_protocol.json')
    client_path = HERE / 'run_natural_a.py'
    assert sha(client_path.read_bytes()) == protocol['scripts_sha256'][client_path.name]
    spec = importlib.util.spec_from_file_location('frozen_natural_client', client_path)
    client = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(client)
    assert sha(client.REGISTRY_PATH.read_bytes()) == protocol['scripts_sha256']['modal_registry.py']
    manifest = HERE.parent / 'pipeline/final_a100.sources.jsonl'
    assert sha(manifest.read_bytes()) == EXPECTED_INPUT_SHA
    sources = [json.loads(line) for line in manifest.read_text().splitlines()]
    source_index = {row['record_id']: i for i, row in enumerate(sources)}
    assert len(sources) == len(source_index) == 100
    result_path = HERE / 'natural_model/results.jsonl'
    result_bytes = result_path.read_bytes()
    results = [json.loads(line) for line in result_bytes.decode().splitlines()]
    assert len({r['record_id'] for r in results}) == len(results)
    if require_complete:
        assert len(results) == 100
    audited_formulas = 0
    for result in results:
        index = source_index[result['record_id']]
        source = sources[index]
        folder = HERE / 'natural_model' / f'record-{index:03d}'
        assert read(folder / 'result.json') == result
        raw = str(source['text'])
        prefix = raw[:4096]
        normalized = re.sub(r'\s+', ' ', prefix).strip()
        assert result['text_sha256'] == sha(prefix.encode())
        assert result['full_text_sha256'] == sha(raw.encode())
        assert result['evaluated_chars'] == len(prefix)
        assert result['source_chars'] == len(raw)
        assert result['source_truncated'] == (len(raw) > 4096)
        request = read(folder / 'request.json')
        expected = dict(model='leanstral_local', messages=[dict(role='user', content=client.PROMPT_BASE + normalized)], temperature=0, seed=20260914, max_tokens=2048, reasoning_effort='none', stream=False, stop=['</s>'])
        assert request == expected
        assert result['prompt_sha256'] == sha(expected['messages'][0]['content'].encode())
        assert result['independent_semantic_fidelity_measured'] is False
        assert result['status'] in {'measured', 'response_rejected', 'request_failed'}
        if result['status'] == 'measured':
            assert result.get('model_format_accepted') is True
            assert 'canonical_ir' in result
            assert set(result.get('checks', {})) == {'modal_well_formedness', 'provenance_preservation'}
            assert all(type(check.get('passed')) is bool for check in result['checks'].values())
        if result.get('model_response_received'):
            response = read(folder / 'request_response.json')
            choice = response['choices'][0]
            assert result['finish_reason'] == choice.get('finish_reason')
            assert result['usage'] == response.get('usage')
            if result.get('model_format_accepted'):
                payload = client.strict_payload(choice)
                if 'canonical_ir' in result:
                    ir = result['canonical_ir']
                    assert ir['document_id'] == source['record_id']
                    assert ir['normalized_text'] == normalized
                    assert len(ir['formulas']) == len(payload) == result['formula_count']
                    for i, (original, stored) in enumerate(zip(payload, ir['formulas'])):
                        assert stored['formula_id'] == f"{source['record_id']}:f{i:04d}"
                        for field in ['operator', 'predicate', 'conditions', 'exceptions']:
                            assert stored[field] == original[field]
                        for field in ['start_char', 'end_char']:
                            assert stored['provenance'][field] == original['provenance'][field]
                        assert stored['provenance']['source_id'] == source['record_id']
                        assert stored['metadata'] == {}
                        audited_formulas += 1
        else:
            assert result['status'] == 'request_failed'
    terminal_ids = {r['record_id'] for r in results}
    outstanding = []
    for folder in (HERE / 'natural_model').glob('record-*'):
        started = folder / 'started.json'
        if started.exists() and read(started)['record_id'] not in terminal_ids:
            outstanding.append(folder.name)
    if require_complete:
        assert not outstanding
    return dict(audited_at=datetime.now(timezone.utc).isoformat(), passed=True, planned=100, terminal_attempts=len(results), outstanding_started_folders=outstanding, statuses=dict(Counter(r['status'] for r in results)), retained_unchanged_formulas=audited_formulas, input_sha256=EXPECTED_INPUT_SHA, result_bytes_sha256=sha(result_bytes), checks=['Frozen client and registry hashes', 'Exact100-source manifest hash', 'Unique terminal attempts and per-record receipt equality', 'Full and prefix source hash binding', 'Unchanged request content and sampling parameters', 'Raw response status and token usage retention', 'Unedited semantic fields and span indices after mechanical assembly'], model_calls=0, semantic_fidelity_established=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--require-complete', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = audit(args.require_complete)
    text = json.dumps(report, indent=2) + '\n'
    if args.output:
        args.output.write_text(text)
    print(text)
