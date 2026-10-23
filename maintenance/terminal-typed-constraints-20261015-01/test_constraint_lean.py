"""Exact generator and mathematical proof boundary tests; no synthetic receipts."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest
import constraint_lean as lean


@pytest.fixture(scope='module')
def inputs():
    from constraint_io import inputs as public_inputs
    from scheduler_constraints import build_scheduler_contract, authored_cases
    _, bodies, instructions, _ = public_inputs()
    prior = Path(__file__).resolve().parent.parent / 'terminal-intent-coverage-20261015-01' / 'experiment-02' / 'structural-report.json'
    head = json.loads(prior.read_bytes())['head']
    contract = build_scheduler_contract(instruction=instructions['llm-inference-batching-scheduler'], head=head,
        source_records=[{'path':name,'sha256':hashlib.sha256(raw).hexdigest(),'source_text':raw.decode('utf-8')}
            for name,raw in sorted(bodies.items())])
    return contract, authored_cases()


@pytest.fixture(scope='module')
def theory(inputs):
    contract, cases = inputs
    return lean.build_lean_theory(contract=contract, cases=cases)


def _resign(theory):
    theory.pop('report_sha256', None)
    theory['report_sha256'] = hashlib.sha256(lean._wire(theory)).hexdigest()


def test_exact_five_fixed_compiler_sources_and_bound_inputs(theory, inputs):
    contract, cases = inputs
    assert [row['label'] for row in theory['sources']] == list(lean.LEAN_LABELS)
    assert [row['expected_success'] for row in theory['sources']] == [True,False,False,False,False]
    assert theory['contract'] == contract and theory['cases'] == cases
    assert theory['contract_sha256'] == hashlib.sha256(lean._wire(contract)).hexdigest()
    assert theory['cases_sha256'] == hashlib.sha256(lean._wire(cases)).hexdigest()
    assert len(theory['accepted_case_ids']) >= 2
    assert lean._lean_sources(theory)[0][2] is True


def test_genuine_theorems_not_uninterpreted_modal_declarations(theory):
    source = theory['sources'][0]['source']
    for name in lean.GENERIC_THEOREMS:
        assert 'theorem ' + name in source
        assert '#print axioms ' + name in source
    assert 'List.isPerm_iff.mp' in source
    assert 'uniqueInput.count_of_mem' in source
    assert 'List.all_eq_true.mp' in source
    assert '((a ++ b).map Row.shape).eraseDups' in source
    assert 'theorem aligned_ceiling_covers_prompt' in source
    assert 'value.numerator * denominator < numerator * value.denominator' in source
    assert all(token not in source for token in ('sorry', 'axiom ', 'unsafe ', 'native_decide'))
    assert all(theory[key] is False for key in lean.AUTHORITY)
    assert theory['native_fol_lean_correspondence'] == 'unproved'


@pytest.mark.parametrize('mutation', ('source','omit-control','proof-promotion','native-correspondence',
    'drop-accepted','theorem-name','contract-sha','cases-sha','unknown-field','changed-case','changed-source-text'))
def test_resigned_theory_forgeries_refuse(theory, mutation):
    changed = deepcopy(theory)
    if mutation == 'source':changed['sources'][0]['source'] += '\naxiom fabricated : False\n'
    elif mutation == 'omit-control':changed['sources'].pop()
    elif mutation == 'proof-promotion':changed['source_model_equivalence_proved'] = True
    elif mutation == 'native-correspondence':changed['native_fol_lean_correspondence'] = 'proved'
    elif mutation == 'drop-accepted':changed['accepted_case_ids'] = []
    elif mutation == 'theorem-name':changed['theorems'].append('fabricated')
    elif mutation == 'contract-sha':changed['contract_sha256'] = '0'*64
    elif mutation == 'cases-sha':changed['cases_sha256'] = '0'*64
    elif mutation == 'unknown-field':changed['full_task_proved'] = True
    elif mutation == 'changed-case':changed['cases'][0]['case']['buckets'][0]['plan'][0]['shape']['seq_align'] = 1
    else:changed['contract']['sources'][0]['source_text'] += '\n# edited\n'
    _resign(changed)
    with pytest.raises((ValueError,KeyError,TypeError)):
        lean._lean_sources(changed)


def test_false_theorems_are_actual_semantic_contradictions(theory):
    controls = {row['label']:row['source'] for row in theory['sources'][1:]}
    assert 'coverageCheck controlRequests [row1, row1] = true' in controls['false-duplicate-missing-ids']
    assert 'globalCapCheck (nineShapeRows.take 5) (nineShapeRows.drop 5) = true' in controls['false-nine-global-shapes']
    assert 'batchCheck [row1, row2] = true' in controls['false-inconsistent-batch']
    assert 'prompt := 65' in controls['false-insufficient-alignment']
    assert 'seq := 64' in controls['false-insufficient-alignment']
    for source in controls.values():
        assert 'theorem deliberate_false_control' in source
        assert ':= by decide' in source


def test_wrong_case_expectations_refuse(inputs):
    contract, cases = inputs
    changed = deepcopy(cases)
    changed[0]['expected_pass'] = not changed[0]['expected_pass']
    with pytest.raises(ValueError):lean.build_lean_theory(contract=contract,cases=changed)


@pytest.mark.parametrize('value', (True,False,-1,10**18+1,1.0,'64',None))
def test_lean_natural_boundary_rejects_aliases(value):
    with pytest.raises(ValueError):lean._nat(value)


def test_missing_live_lease_never_creates_output(theory):
    output = Path(__file__).resolve().parent / 'unit-forbidden-lean-output'
    assert not output.exists()
    with pytest.raises(ValueError):lean.compile_constraint_theory(theory,output=output,lease=None)
    assert not output.exists()


def test_false_intended_violation_claims_refuse(inputs):
    contract, cases = inputs
    changed = deepcopy(cases)
    changed[0]['intended_violation_ids'] = ['scheduler.fabricated']
    with pytest.raises(ValueError):lean.build_lean_theory(contract=contract,cases=changed)
