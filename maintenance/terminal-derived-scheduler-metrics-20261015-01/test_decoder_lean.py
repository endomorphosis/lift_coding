"""Replay actual native kernel receipts; never substitute a mock compiler."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

import decoder_lean as lean
from strict_jsonl import parse_jsonl, StrictJSONLError

ROOT = Path(__file__).resolve().parent
EXPERIMENT = ROOT / 'experiment-01'
OUTPUT = EXPERIMENT / 'decoder-lean'


def _hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resign(report):
    report.pop('report_sha256', None)
    report['report_sha256'] = hashlib.sha256(lean._wire(report)).hexdigest()


@pytest.fixture(scope='module')
def actual():
    report = json.loads((OUTPUT / 'report.json').read_bytes())
    theory = json.loads((EXPERIMENT / 'decoder-theory.json').read_bytes())
    witnesses = json.loads((EXPERIMENT / 'decoder-witnesses.json').read_bytes())
    assert lean.validate_decoder_evidence(report, theory=theory, output=OUTPUT) is report
    paths = [OUTPUT / 'report.json', EXPERIMENT / 'decoder-theory.json',
             EXPERIMENT / 'decoder-witnesses.json', ROOT / 'decoder_kernel.lean']
    paths += [OUTPUT / (label + ext) for label in lean.DECODER_LABELS
              for ext in ('.lean', '-process.json')]
    pins = {path: _hash(path) for path in paths}
    yield report, theory, witnesses, pins
    assert all(_hash(path) == digest for path, digest in pins.items())


def test_all_retained_exact_byte_equalities_and_model_results(actual):
    report, theory, witnesses, _ = actual
    assert report['positive_compiles'] == 1
    assert report['false_controls_rejected'] == 5
    assert len(lean.DECODER_LABELS) == 6
    assert len(theory['unique_files']) == len(witnesses['witnesses']) == 70
    assert len(theory['theorems']) == 104
    assert theory['finite_model_case_count'] == 16
    assert theory['composed_decoded_model_case_count'] == 16
    assert sum(w['expected_parse_success'] for w in witnesses['witnesses']) == 43
    assert len(theory['witness_theorem_joins']) == 70
    assert report['proof_scope'] == lean.PROOF_SCOPE
    assert all(report[key] is False for key in lean.AUTHORITY)
    assert theory['general_python_parser_equivalence_proved'] is False
    assert theory['general_checker_model_equivalence_proved'] is False
    assert report['proved_theorems'] == theory['theorems']
    positive = report['checks'][0]
    assert 'sorryAx' not in positive['stdout']
    assert all('DecoderKernel.' + name in positive['stdout'] for name in theory['theorems'])
    assert [row['status'] for row in report['checks']] == ['passed'] + ['rejected'] * 5
    assert all(row['native_lifecycle']['cleanup_confirmed'] is True for row in report['checks'])
    assert all(row['limits']['resident_memory_bytes'] == 1024**3 for row in report['checks'])


def test_each_kernel_file_result_matches_complete_parser_replay(actual):
    _, theory, witnesses, _ = actual
    joins = {row['witness_id']: row['theorem'] for row in theory['witness_theorem_joins']}
    results = {row['theorem']: row for row in theory['unique_files']}
    for witness in witnesses['witnesses']:
        raw = bytes.fromhex(witness['raw_hex'])
        result = results[joins[witness['witness_id']]]
        assert result['raw_bytes'] == len(raw)
        assert result['raw_sha256'] == hashlib.sha256(raw).hexdigest()
        assert result['kind'] == witness['kind']
        try:
            parsed = parse_jsonl(raw, kind=witness['kind'])
            rows = lean._scalar_rows(parsed['rows'], witness['kind'])
            assert witness['expected_parse_success'] is True
            assert witness['expected_rows'] == rows
        except StrictJSONLError:
            assert witness['expected_parse_success'] is False
            assert witness['expected_rows'] is None


def test_decoded_control_identifiers_are_rendered_as_exact_scalar_lists(actual):
    _, theory, witnesses, _ = actual
    control_rows = [row for witness in witnesses['witnesses']
                    if witness['expected_parse_success'] for row in witness['expected_rows']
                    if any(n in (1, 8, 12) for n in row['request_id'])]
    assert control_rows
    assert all(type(n) is int for row in control_rows for n in row['request_id'])
    source = theory['sources'][0]['source']
    assert 'native_decide' not in source
    assert 'partial ' not in source and 'unsafe ' not in source
    assert 'sorry' not in source and 'axiom ' not in source
    assert ': String' not in source and 'String.ofList' not in source


def test_every_composed_outcome_requires_all_four_actual_file_decoders(actual):
    _, theory, witnesses, _ = actual
    by_witness = {w['witness_id']: w for w in witnesses['witnesses']}
    assert len(theory['composed_case_joins']) == 16
    assert sum(join['expected_pass'] for join in theory['composed_case_joins']) == 7
    source = theory['sources'][0]['source']
    assert '.getD' not in source
    for index, join in enumerate(theory['composed_case_joins']):
        assert join['derived_case_index'] == index
        assert join['decode_success_required_before_model_evaluation'] is True
        assert join['supplied_metrics_runtime_observed'] is False
        assert join['theorem'] == 'exact_decoded_model_' + str(index)
        assert len(join['files']) == 4
        assert {(f['bucket_id'], f['kind']) for f in join['files']} == {
            (1, 'requests'), (1, 'plan'), (2, 'requests'), (2, 'plan')}
        for file in join['files']:
            witness = by_witness[file['witness_id']]
            assert witness['kind'] == file['kind']
            assert witness['expected_parse_success'] is True
            assert file['decoder_theorem'] == 'exact_file_' + str(file['file_index'])
        assert ('theorem ' + join['theorem'] + ' : decodedOutcome' + str(index)
                + ' = some ' + ('true' if join['expected_pass'] else 'false')) in source


@pytest.mark.parametrize('mutation', (
    'raw-byte', 'expected-row', 'expected-result', 'witness-join', 'duplicate-file',
    'case-result', 'scope', 'template-pin', 'generated-source', 'proved-name',
    'composed-file', 'composed-fallback'))
def test_resigned_theory_mutations_cannot_replay(actual, mutation):
    _, original, _, pins = actual
    theory = deepcopy(original)
    if mutation == 'raw-byte':
        item = theory['witnesses']['witnesses'][0]
        raw = bytes.fromhex(item['raw_hex']) + b' '
        item.update(raw_hex=raw.hex(), raw_bytes=len(raw), raw_sha256=hashlib.sha256(raw).hexdigest())
    elif mutation == 'expected-row':
        item = next(w for w in theory['witnesses']['witnesses'] if w['expected_parse_success'] and w['expected_rows'])
        item['expected_rows'][0]['request_id'].append(1)
    elif mutation == 'expected-result':
        theory['witnesses']['witnesses'][0]['expected_parse_success'] ^= True
    elif mutation == 'witness-join':
        theory['witness_theorem_joins'][0]['theorem'] = 'exact_file_999'
    elif mutation == 'duplicate-file':
        theory['witnesses']['witnesses'].append(deepcopy(theory['witnesses']['witnesses'][0]))
    elif mutation == 'case-result':
        theory['witnesses']['derived_cases'][0]['expected_pass'] ^= True
    elif mutation == 'scope':
        theory['general_python_parser_equivalence_proved'] = True
    elif mutation == 'template-pin':
        theory['kernel_template']['sha256'] = '0' * 64
    elif mutation == 'generated-source':
        theory['sources'][0]['source'] += '\n'
    elif mutation == 'proved-name':
        theory['theorems'].pop()
    elif mutation == 'composed-file':
        theory['composed_case_joins'][0]['files'][0]['file_index'] = 999
    elif mutation == 'composed-fallback':
        theory['composed_case_joins'][0]['decode_success_required_before_model_evaluation'] = False
    _resign(theory)
    with pytest.raises((ValueError, TypeError, KeyError)):
        lean._lean_sources(theory)
    assert all(_hash(path) == digest for path, digest in pins.items())


def _memory_receipts(monkeypatch, report):
    read = lean._read
    def override(path, maximum=64 * 1024**2):
        if path == OUTPUT / 'report.json':
            return lean._wire(report)
        for check in report['checks']:
            if path == OUTPUT / (check['label'] + '-process.json'):
                return lean._wire(check)
        return read(path, maximum)
    monkeypatch.setattr(lean, '_read', override)


@pytest.mark.parametrize('mutation', (
    'missing-control', 'positive-count', 'false-count', 'sorry-axiom', 'drop-axiom-output',
    'proof-scope', 'authority', 'cpu-limit', 'rss-limit', 'timeout-limit', 'argv',
    'home', 'cleanup', 'retained-workspace', 'pid', 'leader-pid', 'birth-reuse',
    'unjoined-readers', 'remaining-group', 'kernel-containment', 'unknown-field'))
def test_resigned_actual_process_receipts_refuse_without_file_edits(actual, monkeypatch, mutation):
    original, theory, _, pins = actual
    report = deepcopy(original)
    check = report['checks'][0]
    if mutation == 'missing-control': report['checks'].pop()
    elif mutation == 'positive-count': report['positive_compiles'] = True
    elif mutation == 'false-count': report['false_controls_rejected'] = 4
    elif mutation == 'sorry-axiom': check['stdout'] += '\nsorryAx\n'
    elif mutation == 'drop-axiom-output': check['stdout'] = ''
    elif mutation == 'proof-scope': report['proof_scope'] = 'general_source_equivalence'
    elif mutation == 'authority': report['proof_authority'] = True
    elif mutation == 'cpu-limit': check['limits']['cpu_seconds'] = True
    elif mutation == 'rss-limit': check['limits']['resident_memory_bytes'] *= 2
    elif mutation == 'timeout-limit': check['limits']['timeout_seconds'] = 600
    elif mutation == 'argv': check['actual_invocation_command'].insert(1, '--run')
    elif mutation == 'home': check['environment']['HOME'] = '/tmp'
    elif mutation == 'cleanup': check['native_lifecycle']['cleanup_confirmed'] = False
    elif mutation == 'retained-workspace': check['native_lifecycle']['workspace']['removed'] = False
    elif mutation == 'pid': check['pid'] = True
    elif mutation == 'leader-pid': check['native_lifecycle']['leader']['pid'] += 1
    elif mutation == 'birth-reuse': report['checks'][1]['native_lifecycle']['leader'] = deepcopy(check['native_lifecycle']['leader'])
    elif mutation == 'unjoined-readers': check['native_lifecycle']['readers']['joined'] = 0
    elif mutation == 'remaining-group': check['native_lifecycle']['remaining_group_members'] = [check['native_lifecycle']['leader']]
    elif mutation == 'kernel-containment': check['native_lifecycle']['kernel_containment_attested'] = True
    elif mutation == 'unknown-field': check['fully_verified'] = True
    _resign(report)
    _memory_receipts(monkeypatch, report)
    with pytest.raises((ValueError, TypeError, KeyError)):
        lean.validate_decoder_evidence(report, theory=theory, output=OUTPUT)
    assert all(_hash(path) == digest for path, digest in pins.items())
