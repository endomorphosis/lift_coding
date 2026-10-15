"""Replay real metric compiler receipts; mutations remain inert memory values."""
from copy import deepcopy
import json
from pathlib import Path

import pytest
import metrics_lean as M


@pytest.fixture(scope='module')
def retained():
    root = Path(__file__).resolve().parent / 'experiment-01'
    report = json.loads(M._read(root / 'metric-case-report.json'))
    theory = json.loads(M._read(root / 'metric-theory.json'))
    output = root / 'metric-lean'
    evidence = json.loads(M._read(output / 'report.json'))
    return report, theory, evidence, output


def _resign(value):
    value.pop('report_sha256', None)
    value['report_sha256'] = M._sha(M._wire(value))
    return value


def test_actual_metric_theory_rebuilds(retained):
    report, theory, _, _ = retained
    assert M._wire(M.build_metrics_theory(report=report)) == M._wire(theory)


def test_actual_metric_native_receipts_validate(retained):
    _, theory, evidence, output = retained
    assert M.validate_metrics_evidence(evidence, theory=theory, output=output) == evidence


def test_complete_metric_case_join(retained):
    report, theory, _, _ = retained
    assert len(report['entries']) == 33
    assert theory['metric_case_count'] == 33
    assert [row['case_id'] for row in theory['case_joins']] == [row['case_id'] for row in report['entries']]
    assert sum(row['decimal_model_result'] is None for row in theory['case_joins']) == 4
    for row in theory['case_joins']:
        assert len(row['files']) == 4
        assert row['metrics_derived_from_decoded_rows'] is True
        assert row['binary64_equivalence_proved'] is False
        assert row['theorem'] in theory['theorems']
        assert row['composed_theorem'] in theory['theorems']


def test_closed_metric_compiler_inventory(retained):
    _, theory, evidence, _ = retained
    assert tuple(row['label'] for row in theory['sources']) == M.METRICS_LABELS
    assert [row['expected_success'] for row in theory['sources']] == [True] * 4 + [False] * 5
    assert set(theory['theorems']) == {name for row in theory['sources'] for name in row['theorems']}
    assert evidence['positive_compiles'] == 4
    assert evidence['false_controls_rejected'] == 5
    assert evidence['proof_scope'] == M.PROOF_SCOPE
    assert evidence['qualified'] is True


def test_metrics_acceptance_has_no_supplied_metric_parameter():
    kernel = M._kernel()
    start = kernel.index('def derivedModelAccept')
    end = kernel.index('def fractionEquivalent', start)
    body = kernel[start:end]
    assert 'derivedMetrics a.requests a.rows' in body
    assert 'derivedMetrics b.requests b.rows' in body
    assert 'with metrics := ma' in body and 'with metrics := mb' in body
    assert all(token not in kernel for token in ('native_decide', 'unsafe ', 'partial ', 'sorry', 'admit'))


def test_metric_profile_is_explicit():
    kernel = M._kernel()
    assert 'request.prompt ≤ 4096' in kernel
    assert 'request.generated ≤ 1024' in kernel
    assert 'row.shape.seq ≤ 8192' in kernel
    assert 'requests.length ≤ 256' in kernel


def test_source_order_and_compilation_rules_are_defined():
    kernel = M._kernel()
    assert 'metricSort scalarLE' in kernel
    assert 'lastShape rows bid' in kernel
    assert '(x + 3750000) :: xs' in kernel
    assert 'if shape.seq = 0 then 0' in kernel


@pytest.mark.parametrize('mutation', [
    'schema', 'metric-case-count', 'source', 'theorem', 'kernel-pin',
    'case-result', 'composed-join', 'witness-hash', 'decimal-scope'])
def test_resigned_metric_theory_mutations_rejected(retained, mutation):
    _, original, _, _ = retained
    theory = deepcopy(original)
    if mutation == 'schema':
        theory['schema'] += '-forged'
    elif mutation == 'metric-case-count':
        theory['metric_case_count'] -= 1
    elif mutation == 'source':
        theory['sources'][0]['source'] += '\n-- forged body\n'
    elif mutation == 'theorem':
        theory['theorems'].pop()
    elif mutation == 'kernel-pin':
        theory['metric_kernel_template']['sha256'] = '0' * 64
    elif mutation == 'case-result':
        theory['case_joins'][0]['decimal_model_result'] = not theory['case_joins'][0]['decimal_model_result']
    elif mutation == 'composed-join':
        theory['case_joins'][0]['files'].pop()
    elif mutation == 'witness-hash':
        theory['unique_files'][0]['raw_sha256'] = '0' * 64
    elif mutation == 'decimal-scope':
        theory['source_binary64_equivalence_proved'] = True
    _resign(theory)
    with pytest.raises((ValueError, KeyError, TypeError)):
        M._lean_sources(theory)


@pytest.mark.parametrize('mutation', [
    'scope', 'profile', 'proof-authority', 'qualified', 'proved-name',
    'positive-count', 'false-count', 'theory-binding', 'training', 'provider',
    'source-command', 'actual-command', 'rss', 'threads', 'environment',
    'cleanup', 'remaining-process', 'birth-identity', 'lease', 'sorry-axiom',
    'control-status', 'control-diagnostic', 'timed-out', 'source-pin'])
def test_resigned_metric_receipt_mutations_rejected(retained, mutation, monkeypatch):
    _, theory, original, output = retained
    evidence = deepcopy(original)
    check = evidence['checks'][0]
    if mutation == 'scope':
        evidence['proof_scope'] = 'full_source_equivalence'
    elif mutation == 'profile':
        evidence['profile'] += '-forged'
    elif mutation == 'proof-authority':
        evidence['proof_authority'] = True
    elif mutation == 'qualified':
        evidence['qualified'] = False
    elif mutation == 'proved-name':
        evidence['proved_theorems'].pop()
    elif mutation == 'positive-count':
        evidence['positive_compiles'] = 5
    elif mutation == 'false-count':
        evidence['false_controls_rejected'] = 4
    elif mutation == 'theory-binding':
        evidence['theory_sha256'] = '0' * 64
    elif mutation == 'training':
        evidence['training_steps'] = 1
    elif mutation == 'provider':
        evidence['provider_calls'] = 1
    elif mutation == 'source-command':
        check['requested_command'] = [str(M.LEAN), 'DecoderTheory.lean']
    elif mutation == 'actual-command':
        check['actual_invocation_command'][2] = '8'
    elif mutation == 'rss':
        check['limits']['resident_memory_bytes'] *= 2
    elif mutation == 'threads':
        check['lean_threads'] = 8
    elif mutation == 'environment':
        check['environment']['HOME'] = '/forged'
    elif mutation == 'cleanup':
        check['native_lifecycle']['cleanup_confirmed'] = False
    elif mutation == 'remaining-process':
        check['native_lifecycle']['remaining_group_members'] = [check['pid']]
    elif mutation == 'birth-identity':
        check['native_lifecycle']['leader']['birth_ticks'] = 0
    elif mutation == 'lease':
        check['native_shared_child_lease_used'] = False
    elif mutation == 'sorry-axiom':
        check['stdout'] += '\nuses sorryAx\n'
    elif mutation == 'control-status':
        evidence['checks'][4]['status'] = 'passed'
    elif mutation == 'control-diagnostic':
        evidence['checks'][4]['stdout'] = 'arbitrary syntax error'
    elif mutation == 'timed-out':
        check['timed_out'] = True
    elif mutation == 'source-pin':
        check['source']['sha256'] = '0' * 64
    _resign(evidence)
    reader = M._read
    overrides = {output / (row['label'] + '-process.json'): M._wire(row) for row in evidence['checks']}
    overrides[output / 'report.json'] = M._wire(evidence)
    monkeypatch.setattr(M, '_read', lambda path, maximum=64 * 1024**2:
        overrides[path] if path in overrides else reader(path, maximum))
    with pytest.raises((ValueError, KeyError, TypeError)):
        M.validate_metrics_evidence(evidence, theory=theory, output=output)
