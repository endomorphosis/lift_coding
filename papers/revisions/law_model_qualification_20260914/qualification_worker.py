#!/usr/bin/env python3
"""Eight frozen model-interface probes; no scientific cells or code execution.

--check-plan performs only offline construction/validation. Real calls require
the separately owned model job, pinned socket client, and explicit normal mode.
"""
from __future__ import annotations
import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import time

CLIENT_SHA256 = '17cafa11079000fa2e4aae166f97631f12bf53955ce61bc5d9fb49ce601bd9b7'
MODEL = 'leanstral_local'
SEEDS = (104729, 104759, 104761)
SYSTEM = 'Return only Python source defining one function run(payload). Use no imports, builtins, methods, or explanatory prose. The body may use a literal dictionary, payload indexing, and arithmetic.'
USER = "Write run(payload) returning {'doubled': payload['value'] * 2}. The supplied payload contains one integer under the key 'value'. This is an invented interface-qualification task, not a paper benchmark case."
NORMALIZATION = 'Preserve raw assistant content. For a derived syntax diagnostic only, remove one complete enclosing ```python or unlabelled ``` code fence when it is the entire stripped response. Do not repair, synthesize, dedent, extract partial fences, or execute code.'


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, value):
    with Path(path).open('xb') as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False).encode() + b'\n')


def plan():
    base = [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': USER}]
    repair = base + [
        {'role': 'assistant', 'content': "def run(payload):\n    return {'doubled': payload['value'] + 2}\n"},
        {'role': 'user', 'content': "This is a supplied synthetic repair fixture, not a report from an executed prior model response. Fixture input {'value': 3} has required output {'doubled': 6}; the supplied addition-by-two program would yield {'doubled': 5}. Return the corrected function only."},
    ]
    unicode_messages = [{'role': 'user', 'content': "Return only this Python function's source, without imports or prose: run(payload) returns a literal dictionary with key 'label' and exact value 'café — Ω', and key 'value' containing payload['value'].\nPreserve the Unicode string exactly.\nThis is an invented interface probe."}]
    long_messages = [{'role': 'user', 'content': 'Deliberate tokenizer-overflow qualification fixture; it must be rejected before generation when over 2048 tokens. Synthetic identifiers:\n' + ' '.join('q' + format(index, '06x') for index in range(4096))}]
    definitions = [
        ('base_seed_104729', base, SEEDS[0], 1024, 'ordinary_generation'),
        ('identical_repeat_104729', base, SEEDS[0], 1024, 'ordinary_generation'),
        ('base_seed_104759', base, SEEDS[1], 1024, 'ordinary_generation'),
        ('base_seed_104761', base, SEEDS[2], 1024, 'ordinary_generation'),
        ('synthetic_repair_history', repair, SEEDS[0], 1024, 'ordinary_generation'),
        ('single_output_token', base, SEEDS[0], 1, 'ordinary_generation'),
        ('unicode_user_only', unicode_messages, SEEDS[1], 64, 'ordinary_generation'),
        ('input_token_overflow', long_messages, SEEDS[2], 16, 'input_rejection_before_generation'),
    ]
    requests = []
    for index, (name, messages, seed, maximum, expectation) in enumerate(definitions, 1):
        body = {'model': MODEL, 'messages': messages, 'temperature': 0, 'seed': seed,
                'max_tokens': maximum, 'stream': False}
        requests.append({'index': index, 'name': name,
                         'request_id': sha(('law-model-interface-qualification-20260914/v1/' + name).encode())[:32],
                         'body': body, 'body_sha256': sha(canonical(body)),
                         'messages_sha256': sha(canonical(messages)), 'maximum_call_seconds': 60,
                         'expectation': expectation, 'source_population': 'synthetic_interface_probe_no_cohort_source'})
    return {'schema': 'law-model-interface-qualification-plan/v1', 'model': MODEL,
            'scope': 'Source-disjoint synthetic model-interface qualification; no scientific study cells.',
            'requests': requests, 'maximum_distinct_exchange_reservations': 8,
            'maximum_generation_reservations_if_expected_overflow_holds': 7,
            'maximum_workload_seconds': 600, 'maximum_sum_call_seconds': 480,
            'automatic_retry': False, 'execute_generated_code': False,
            'normalization_rule': NORMALIZATION, 'transport_client_sha256': CLIENT_SHA256,
            'reproducibility': 'Observe exact assistant-content byte equality for calls 1 and 2; do not assume determinism or treat syntax as semantic correctness.'}


def normalized_source(text):
    if not isinstance(text, str):
        return None
    stripped = text.strip()
    if '```' not in stripped:
        return text
    match = re.fullmatch(r'```(?:python)?\r?\n([\s\S]*?)\r?\n```', stripped)
    if not match or '```' in match[1]:
        return None
    return match[1]


def validate_plan(value):
    requests = value['requests']
    assert len(requests) == 8 and len({r['request_id'] for r in requests}) == 8
    assert requests[0]['body'] == requests[1]['body']
    assert {r['body']['seed'] for r in requests} == set(SEEDS)
    assert [r['body']['seed'] for r in requests[:4]] == [104729, 104729, 104759, 104761]
    assert [m['role'] for m in requests[4]['body']['messages']] == ['system', 'user', 'assistant', 'user']
    assert 'supplied synthetic repair fixture' in requests[4]['body']['messages'][-1]['content']
    assert requests[5]['body']['max_tokens'] == 1
    assert [m['role'] for m in requests[6]['body']['messages']] == ['user']
    assert 'café — Ω' in requests[6]['body']['messages'][0]['content']
    assert len(requests[7]['body']['messages'][0]['content']) > 32000
    assert requests[7]['expectation'] == 'input_rejection_before_generation'
    for request in requests:
        body = request['body']
        assert set(body) == {'model', 'messages', 'temperature', 'seed', 'max_tokens', 'stream'}
        assert body['model'] == MODEL and body['temperature'] == 0 and body['stream'] is False
        assert body['seed'] in SEEDS and 1 <= body['max_tokens'] <= 1024
        assert len(canonical(body)) <= 256 * 1024 - 2048
        assert request['body_sha256'] == sha(canonical(body))
        assert request['messages_sha256'] == sha(canonical(body['messages']))
    assert sum(r['maximum_call_seconds'] for r in requests) == 480 <= value['maximum_workload_seconds']
    assert normalized_source('def run(payload):\n    return {}\n') == 'def run(payload):\n    return {}\n'
    assert normalized_source('```python\ndef run(payload):\n    return {}\n```') == 'def run(payload):\n    return {}'
    assert normalized_source('prose\n```python\ndef run(payload): pass\n```') is None
    assert normalized_source('```python\n```\n```') is None
    return {'schema': 'law-model-interface-offline-plan-check/v1', 'status': 'PASS_OFFLINE_PLAN_ONLY',
            'requests': 8, 'frozen_unique_ids': 8, 'all_three_seeds': True,
            'identical_repeat_body': True, 'maximum_call_seconds': 60, 'maximum_workload_seconds': 600,
            'planned_overflow_not_yet_tokenized': True,
            'normalization_controls': 4, 'model_calls': 0, 'candidate_executions': 0,
            'worker_sha256': sha(Path(__file__).read_bytes()), 'plan_sha256': sha(canonical(value))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job', type=Path, default=Path('/model-job'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--transport-client', type=Path, default=Path('/transport/client.py'))
    parser.add_argument('--workload-seconds', type=float, default=600)
    parser.add_argument('--check-plan', action='store_true')
    args = parser.parse_args()
    started = time.monotonic()
    if not 0 < args.workload_seconds <= 600:
        raise ValueError('Workload must have a positive <=600-second bound')
    args.output.mkdir(parents=True, exist_ok=True)
    frozen = plan()
    checks = validate_plan(frozen)
    save(args.output / 'request_plan.json', frozen)
    save(args.output / 'offline_plan_checks.json', checks)
    if args.check_plan:
        print(json.dumps(checks, indent=2))
        return 0
    client_raw = args.transport_client.read_bytes()
    if sha(client_raw) != CLIENT_SHA256:
        raise RuntimeError('Transport client differs from the frozen qualified bytes')
    job = json.loads((args.job / 'client.json').read_bytes())
    if job['model'] != MODEL:
        raise RuntimeError('Job model alias differs from the frozen request plan')
    sources = args.output / 'source_bytes'
    sources.mkdir(mode=0o700)
    (sources / 'qualification_worker.py').write_bytes(Path(__file__).read_bytes())
    (sources / 'client.py').write_bytes(client_raw)
    spec = importlib.util.spec_from_file_location('qualified_socket_client', args.transport_client)
    client = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(client)
    deadline = started + args.workload_seconds
    save(args.output / 'workload_started.json', {'started_monotonic': started, 'deadline_monotonic': deadline,
                                               'job_id': job['job_id'], 'plan_sha256': sha(canonical(frozen)),
                                               'maximum_distinct_exchanges': 8, 'automatic_retry': False})
    results = []
    stop_reason = None
    content = {}
    for request in frozen['requests']:
        row = {'index': request['index'], 'name': request['name'], 'request_id': request['request_id'],
               'exchange_reserved': False, 'generation_reserved': None, 'status': 'not_attempted',
               'semantic_correctness_measured': False, 'generated_code_executed': False}
        if stop_reason:
            row['not_attempted_reason'] = stop_reason
            results.append(row)
            continue
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            stop_reason = 'complete_workload_budget_exhausted'
            row['not_attempted_reason'] = stop_reason
            results.append(row)
            continue
        case = args.output / ('request-' + str(request['index']).zfill(2))
        case.mkdir(mode=0o700)
        save(case / 'started.json', {'request_id': request['request_id'], 'body_sha256': request['body_sha256'],
                                   'started_monotonic': time.monotonic(), 'budget_seconds': min(60, remaining),
                                   'exchange_reserved': True, 'automatic_retry': False})
        row['exchange_reserved'] = True
        try:
            response, receipt = client.exchange(args.job, request['body'], case / 'transport',
                                                budget_seconds=min(60, remaining), request_id=request['request_id'])
            row['worker_receipt'] = receipt
            if response is None or response.get('receipt') is None:
                raise RuntimeError('No authoritative host attempt receipt; reconcile before another exchange')
            host = response['receipt']
            row.update(generation_reserved=host['generation_reserved'], input_count=host['input_count'],
                       prompt_tokens=host['prompt_tokens'], completion_tokens=host['completion_tokens'],
                       token_usage_known=host['token_usage_known'], host_child_termination_proven=host['child_termination_proven'])
            if not host['child_termination_proven'] or host['cleanup_errors']:
                raise RuntimeError('Host request child cleanup is unproven')
            if request['expectation'] == 'input_rejection_before_generation':
                if response['ok'] or host['generation_reserved'] or type(host['input_count']) is not int or host['input_count'] <= 2048:
                    raise RuntimeError('Expected input-overflow rejection was not observed before generation')
                row['status'] = 'expected_input_rejection_observed'
            else:
                if not response['ok'] or receipt.get('tokenization_matches_usage') is not True:
                    raise RuntimeError('Model exchange failed or preflight/usage equality was not verified')
                generation = json.loads((case / 'transport/response.bin').read_bytes())
                text = generation['choices'][0]['message']['content']
                content[request['index']] = text
                row.update(status='interface_checks_passed', assistant_content_sha256=sha(text.encode()),
                           finish_reason=generation['choices'][0].get('finish_reason'))
                normalized = normalized_source(text)
                row['normalization_accepted'] = normalized is not None
                if normalized is not None:
                    (case / 'derived_source.py.txt').write_bytes(normalized.encode())
                    row['derived_source_sha256'] = sha(normalized.encode())
                    try:
                        ast.parse(normalized)
                    except Exception as exc:
                        row['syntax_diagnostic'] = type(exc).__name__
                    else:
                        row['syntax_diagnostic'] = 'parseable_python_not_executed_or_semantically_validated'
        except Exception as exc:
            row['status'] = 'infrastructure_failure_no_retry'
            row['error'] = type(exc).__name__ + ': ' + str(exc)
            stop_reason = row['error']
        save(case / 'result.json', row)
        results.append(row)
        print(json.dumps({'index': row['index'], 'name': row['name'], 'status': row['status'],
                          'generation_reserved': row['generation_reserved']}), flush=True)
    complete = all(r['status'] in ('interface_checks_passed', 'expected_input_rejection_observed') for r in results)
    summary = {'schema': 'law-model-interface-qualification-results/v1',
               'status': 'PASS_INTERFACE_CHECKS_ONLY' if complete else 'INCOMPLETE_OR_FAILED_NO_RETRY',
               'results': results, 'stop_reason': stop_reason, 'elapsed_seconds': time.monotonic() - started,
               'maximum_workload_seconds': args.workload_seconds, 'reserved_distinct_exchanges': sum(r['exchange_reserved'] for r in results),
               'known_generation_reservations': sum(r['generation_reserved'] is True for r in results),
               'uncertain_generation_reservations': sum(r['exchange_reserved'] and r['generation_reserved'] is None for r in results),
               'repeated_content_observed': 1 in content and 2 in content,
               'repeated_content_exact_match': None if 1 not in content or 2 not in content else content[1].encode() == content[2].encode(),
               'semantic_correctness_measured': False, 'scientific_cells_executed': 0, 'generated_code_executions': 0,
               'raw_output_repaired_or_retried': False, 'model_lifecycle_owner': 'separate_host_owner'}
    save(args.output / 'qualification_results.json', summary)
    return 0 if complete else 1


if __name__ == '__main__':
    raise SystemExit(main())
