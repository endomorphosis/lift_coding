"""Mutate actual accepted native compiler receipts only in memory.

Main experiment-01 must finish before these tests execute. Missing evidence is
an error; there are no synthetic passing receipts, skips, or compiler launches.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest
import constraint_lean as lean

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / 'experiment-01' / 'lean'


@pytest.fixture(scope='module')
def actual_evidence():
    report = json.loads((OUTPUT / 'report.json').read_bytes())
    theory = json.loads((OUTPUT.parent / 'lean-theory.json').read_bytes())
    assert lean.validate_constraint_lean_evidence(report, theory=theory, output=OUTPUT) is report
    assert report['positive_compiles'] == 1 and report['false_controls_rejected'] == 4
    assert len(report['proved_theorems']) == 14
    assert report['proved_theorems'] == theory['theorems']
    paths = [OUTPUT / 'report.json', OUTPUT.parent / 'lean-theory.json']
    for label in lean.LEAN_LABELS:
        paths.extend([OUTPUT / (label + '.lean'), OUTPUT / (label + '-process.json')])
    originals = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    return report, theory, originals


def _resign(report):
    report.pop('report_sha256', None)
    report['report_sha256'] = hashlib.sha256(lean._wire(report)).hexdigest()


def _memory_receipts(monkeypatch, report):
    original_read = lean._read
    def read(path, maximum=64 * 1024**2):
        if path == OUTPUT / 'report.json':
            return lean._wire(report)
        for check in report['checks']:
            if path == OUTPUT / (check['label'] + '-process.json'):
                return lean._wire(check)
        return original_read(path, maximum)
    monkeypatch.setattr(lean, '_read', read)


def test_actual_native_finite_model_kernel_checks_are_qualified(actual_evidence):
    report, theory, _ = actual_evidence
    assert all(check['backend_executed'] is True and check['native_lifecycle']['cleanup_confirmed'] is True
        for check in report['checks'])
    assert all(check['limits']['resident_memory_bytes'] == 1024 * 1024**2
        and check['child_resource_request']['memory_mb'] == 1024 for check in report['checks'])
    positive = report['checks'][0]
    assert 'sorryAx' not in positive['stdout']
    assert all('SchedulerConstraint.' + name in positive['stdout'] for name in theory['theorems'])
    assert report['proof_scope'] == 'defined_authored_finite_model_only_not_source_semantics_or_IntentIR_equivalence'
    assert all(report[key] is False for key in lean.AUTHORITY)


@pytest.mark.parametrize('mutation', (
    'drop-proved-name', 'extra-proved-name', 'missing-printed-name', 'sorry-axiom-stdout',
    'proof-scope-promotion', 'original-task-promotion', 'unknown-fulltask-promotion',
    'theory-sha', 'missing-false-control', 'false-counter-bool-alias',
    'child-cpu-bool-alias', 'child-memory-bool-alias', 'limit-cpu-bool-alias', 'rss-bound',
    'actual-argv', 'home-assignment', 'cleanup-false', 'workspace-retained', 'kernel-containment-promotion',
    'pid-bool-alias', 'pid-mismatch', 'birth-bool-alias', 'duplicate-birth', 'unknown-process-field'))
def test_resigned_mutations_of_real_native_receipts_refuse(actual_evidence, monkeypatch, mutation):
    original, theory, originals = actual_evidence
    changed = deepcopy(original)
    check = changed['checks'][0]
    if mutation == 'drop-proved-name':changed['proved_theorems'].pop()
    elif mutation == 'extra-proved-name':changed['proved_theorems'].append('fabricated_theorem')
    elif mutation == 'missing-printed-name':
        name = theory['theorems'][0]
        check['stdout'] = '\n'.join(line for line in check['stdout'].splitlines()
            if 'SchedulerConstraint.' + name not in line)
    elif mutation == 'sorry-axiom-stdout':check['stdout'] += '\n[propext, sorryAx]\n'
    elif mutation == 'proof-scope-promotion':changed['proof_scope'] = 'complete_original_source_and_task_proof'
    elif mutation == 'original-task-promotion':changed['original_task_satisfaction'] = True
    elif mutation == 'unknown-fulltask-promotion':changed['full_task_satisfaction_proved'] = True
    elif mutation == 'theory-sha':changed['theory_sha256'] = '0' * 64
    elif mutation == 'missing-false-control':changed['checks'].pop()
    elif mutation == 'false-counter-bool-alias':changed['false_controls_rejected'] = True
    elif mutation == 'child-cpu-bool-alias':check['child_resource_request']['cpu_slots'] = True
    elif mutation == 'child-memory-bool-alias':check['child_resource_request']['memory_mb'] = True
    elif mutation == 'limit-cpu-bool-alias':check['limits']['cpu_seconds'] = True
    elif mutation == 'rss-bound':check['limits']['resident_memory_bytes'] *= 2
    elif mutation == 'actual-argv':check['actual_invocation_command'][-1] = 'Forged.lean'
    elif mutation == 'home-assignment':check['environment']['HOME'] = '/tmp/fabricated'
    elif mutation == 'cleanup-false':check['native_lifecycle']['cleanup_confirmed'] = False
    elif mutation == 'workspace-retained':check['native_lifecycle']['workspace']['removed'] = False
    elif mutation == 'kernel-containment-promotion':check['native_lifecycle']['kernel_containment_attested'] = True
    elif mutation == 'pid-bool-alias':check['pid'] = True
    elif mutation == 'pid-mismatch':check['pid'] += 1
    elif mutation == 'birth-bool-alias':check['native_lifecycle']['leader']['birth_ticks'] = True
    elif mutation == 'duplicate-birth':
        other = changed['checks'][1]
        other['pid'] = check['pid']
        other['native_lifecycle']['leader'] = deepcopy(check['native_lifecycle']['leader'])
    else:check['fabricated_proof_authority'] = True
    _resign(changed)
    _memory_receipts(monkeypatch, changed)
    with pytest.raises(ValueError):
        lean.validate_constraint_lean_evidence(changed, theory=theory, output=OUTPUT)
    assert all(hashlib.sha256(path.read_bytes()).hexdigest() == digest for path, digest in originals.items())
