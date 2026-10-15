"""Actual authored file cases for source-derived metrics, separate from legacy inputs."""
from copy import deepcopy
import json
from pathlib import Path

from jsonl_io import ROOT, wire, sha
from jsonl_cases import specs, fixture_payloads, create_bundle, FILE_PATHS
from observed_files import observe_bundle, reobserve_bundle, validate_bundle, decode_file, compare_bundles
from source_metric_bridge import build_derived_file_model, SOURCE_PATH, CLAIMS

METRIC_COUNTS = {'total': 33, 'accepted': 16, 'model_refusal': 13,
                 'metric_refusal': 4, 'binary64_refusal': 0, 'derived_cases': 29}


def _need(condition, message):
    if not condition:
        raise ValueError(message)


def metric_specs():
    original = {row['case_id']: row for row in specs()}
    result = []
    names = ('valid-minimal', 'valid-eight-global-shapes', 'valid-empty-bounded-model',
             'valid-unicode-crlf', 'valid-json-whitespace-no-final-lf', 'valid-escaped-identifiers',
             'invalid-nine-global-shapes', 'missing-output', 'extra-output', 'unaligned-sequence',
             'wrong-heads', 'wrong-hidden', 'inconsistent-batch-shapes', 'below-rounded-prompt')
    for name in names:
        spec = deepcopy(original[name])
        spec['case_id'] = 'metrics-' + name
        spec['case']['case_id'] = spec['case_id']
        spec['expected_outcome'] = ('metric_refusal' if name == 'extra-output' else
            'accepted' if name.startswith('valid-') else 'model_refusal')
        result.append(spec)

    def request(identifier, prompt, generated):
        return {'request_id': identifier, 'prompt_len': prompt, 'gen_len': generated}

    def row(identifier, batch, seq):
        return {'request_id': identifier, 'batch_id': batch,
                'shape': {'seq_align': seq, 'heads_align': 32, 'hidden_align': 4096}}

    def add(name, requests, plan, *, bucket=1, outcome='accepted', both=False):
        spec = deepcopy(original['valid-minimal'])
        spec['case_id'] = 'metrics-' + name
        spec['case']['case_id'] = spec['case_id']
        spec['expected_outcome'] = outcome
        for target in spec['case']['buckets']:
            if target['bucket_id'] == bucket or both:
                target['requests'] = deepcopy(requests)
                target['plan'] = deepcopy(plan)
        result.append(spec)

    for label, prompt, outcome in (('below', 54, 'accepted'), ('equal', 53, 'model_refusal'),
                                   ('above', 52, 'model_refusal')):
        add('bucket1-padding-' + label, [request('p', prompt, 147)], [row('p', 'batch', 64)], outcome=outcome)
    # The two-request construction isolates bucket2 padding without a long decode latency.
    for label, prompt, outcome in (('below', 64, 'accepted'), ('equal', 63, 'model_refusal'),
                                   ('above', 62, 'model_refusal')):
        add('bucket2-padding-' + label,
            [request('a', 64, 28), request('b', prompt, 5)],
            [row('a', 'batch', 64), row('b', 'batch', 64)], bucket=2, outcome=outcome)
    add('declared-shape-does-not-drive-execution', [request('r', 64, 1)], [row('r', 'batch', 8192)])
    add('zero-sequence-compilation-latency', [request('z', 0, 0)], [row('z', 'batch', 0)])
    add('zero-generation', [request('z', 64, 0)], [row('z', 'batch', 64)])
    add('raw-seven-generation', [request('r', 64, 7)], [row('r', 'batch', 64)])
    pair = [request('small', 64, 1), request('large', 128, 1)]
    add('compile-first-small', pair, [row('small', 'batch', 128), row('large', 'batch', 128)])
    add('compile-first-large', pair, [row('large', 'batch', 128), row('small', 'batch', 128)])
    add('lexicographic-compile-batch', pair, [row('small', '2', 128), row('large', '10', 128)])
    add('compilation-resets-per-bucket', [request('same', 64, 1)], [row('same', 'same', 64)], both=True)
    add('unsupported-prompt-bound', [request('r', 4097, 1)], [row('r', 'batch', 4160)], outcome='metric_refusal')
    add('unsupported-generation-bound', [request('r', 64, 1025)], [row('r', 'batch', 64)], outcome='metric_refusal')
    add('unsupported-sequence-bound', [request('r', 64, 1)], [row('r', 'batch', 8193)], outcome='metric_refusal')
    add('bucket2-actual-cost-exceeded', [request('a', 64, 1), request('b', 64, 1)],
        [row('a', 'a', 8192), row('b', 'b', 8128)], bucket=2, outcome='model_refusal')
    add('bucket2-actual-latency-exceeded', [request('r', 4096, 1024)],
        [row('r', 'batch', 4096)], bucket=2, outcome='model_refusal')
    _need(len(result) == 33 and len({row['case_id'] for row in result}) == 33, 'complete fixed metric cases required')
    return result


def _evaluate(*, spec, contract, source_profile, source_raw, before, after):
    try:
        bridge = build_derived_file_model(contract=contract, source_profile=source_profile, source_raw=source_raw,
                                         before=before, after=after, case_id=spec['case_id'])
    except ValueError as error:
        return {'outcome': 'metric_refusal', 'error': {'class': type(error).__name__, 'message': str(error)},
                'bridge': None, 'model': None, 'derived_metrics': None}
    outcome = ('accepted' if bridge['accepted'] else 'model_refusal'
               if not bridge['rational_model_passed'] else 'binary64_refusal')
    return {'outcome': outcome, 'error': None, 'bridge': bridge,
            'model': bridge['file_model'], 'derived_metrics': bridge['derivations']}


def _summary(entries):
    summary = {'total': len(entries), **{name: sum(e['outcome'] == name for e in entries)
               for name in ('accepted', 'model_refusal', 'metric_refusal', 'binary64_refusal')},
               'derived_cases': sum(e['model'] is not None for e in entries)}
    _need(summary == METRIC_COUNTS, 'fixed actual derived-metric outcomes differ from independently authored expectations')
    return summary


def _assemble(*, entries, contract, source_profile, source_raw):
    return {'schema': 'terminal-source-derived-metric-cases@1', 'source_profile': deepcopy(source_profile),
        'source_raw_hex': source_raw.hex(), 'source_profile_sha256': sha(wire(source_profile)),
        'contract': deepcopy(contract), 'contract_sha256': sha(wire(contract)), 'head': deepcopy(contract['head']),
        'entries': entries, 'summary': _summary(entries), 'caller_supplied_metrics_accepted': False,
        'all_expected_outcomes_matched': True, 'claims': dict(CLAIMS)}


def validate_metric_case_data(report):
    """Rebuild mathematical data bindings; this grants no live filesystem authority."""
    from source_profile import validate_source_profile
    _need(type(report) is dict and type(report.get('source_raw_hex')) is str, 'complete public source metric cases required')
    source_raw = bytes.fromhex(report['source_raw_hex'])
    _need(source_raw.hex() == report['source_raw_hex'], 'canonical whole source hex required')
    contract, profile = report['contract'], report['source_profile']
    validate_source_profile(profile, raw=source_raw, source_path=SOURCE_PATH, head=contract['head'])
    authored = metric_specs()
    _need(type(report.get('entries')) is list and len(report['entries']) == len(authored), 'all fixed metric cases required')
    rebuilt = []
    for entry, spec in zip(report['entries'], authored):
        _need(type(entry) is dict and wire(entry.get('spec')) == wire(spec), 'fixed exact authored metric recipe required')
        before, after = entry['before'], entry['after']
        for observation in (before, after):
            validate_bundle(observation)
            expected = fixture_payloads(spec)
            _need(all(decode_file(observation, path) == expected[path] for path in FILE_PATHS),
                  'metric rows differ from independently authored exact fixture bytes')
        fixture = {'schema': 'terminal-authored-jsonl-file-fixture@1', 'case_id': spec['case_id'],
            'root': after['root'], 'initial_payloads': {name: {'bytes': len(raw), 'sha256': sha(raw)}
                for name, raw in sorted(fixture_payloads(spec).items())},
            'real_benchmark_input_used': False, 'source_body_execution': False}
        _need(before['root'] == after['root'], 'the exact metric bundle scope changed')
        comparison = compare_bundles(before, after)
        _need(all(comparison.get(key) is True for key in ('roots_equal', 'directory_generations_equal',
            'unchanged_inputs', 'same_file_generations')),
            'every metric case requires a stable observation bracket, including domain refusals')
        values = _evaluate(spec=spec, contract=contract, source_profile=profile, source_raw=source_raw, before=before, after=after)
        _need(values['outcome'] == spec['expected_outcome'], 'source-derived outcome contradicts authored expectation')
        rebuilt.append({'case_id': spec['case_id'], 'spec': spec, 'fixture': fixture, 'before': before, 'after': after,
                        **values, 'expected_outcome': spec['expected_outcome']})
    expected = _assemble(entries=rebuilt, contract=contract, source_profile=profile, source_raw=source_raw)
    _need(wire(report) == wire(expected), 'source, files, metric derivations, aliases, scope or complete case inventory changed')
    return report


def run_metric_cases(*, output, contract, source_profile, source_raw):
    from source_profile import validate_source_profile
    validate_source_profile(source_profile, raw=source_raw, source_path=SOURCE_PATH, head=contract['head'])
    _need(isinstance(output, Path) and output.is_absolute() and output.resolve() == output
          and ROOT in output.parents and not output.exists(), 'fresh owned metric fixture directory required')
    output.mkdir(mode=0o700)
    entries = []
    for spec in metric_specs():
        bundle = output / spec['case_id']
        fixture = create_bundle(destination=bundle, spec=spec)
        before, after = observe_bundle(root=bundle), observe_bundle(root=bundle)
        values = _evaluate(spec=spec, contract=contract, source_profile=source_profile, source_raw=source_raw,
                           before=before, after=after)
        _need(values['outcome'] == spec['expected_outcome'],
              'actual derived-metric case outcome differs: ' + spec['case_id'] + ': ' + values['outcome']
              + (': ' + str(values['error']) if values['error'] else ''))
        reobserve_bundle(after, root=bundle)
        entries.append({'case_id': spec['case_id'], 'spec': spec, 'fixture': fixture, 'before': before, 'after': after,
                        **values, 'expected_outcome': spec['expected_outcome']})
    result = _assemble(entries=entries, contract=contract, source_profile=source_profile, source_raw=source_raw)
    validate_metric_case_data(result)
    return result


def validate_metric_cases(report, *, output, contract, source_profile, source_raw):
    validate_metric_case_data(report)
    _need(isinstance(output, Path) and output.is_absolute() and output.resolve(strict=True) == output
          and ROOT in output.parents, 'canonical owned current metric fixture directory required')
    _need(wire(report['contract']) == wire(contract) and wire(report['source_profile']) == wire(source_profile)
          and report['source_raw_hex'] == source_raw.hex(), 'current source-bound metric context changed')
    _need({p.name for p in output.iterdir()} == {row['case_id'] for row in metric_specs()},
          'actual metric fixture inventory changed')
    for entry in report['entries']:
        bundle = output / entry['case_id']
        _need(entry['after']['root'] == str(bundle), 'metric bundle moved outside selected current experiment')
        reobserve_bundle(entry['after'], root=bundle)
    return report
