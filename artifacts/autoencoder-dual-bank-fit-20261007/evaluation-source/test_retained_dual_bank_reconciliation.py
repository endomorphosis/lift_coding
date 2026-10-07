"""Inert reconciliation controls; genuine pure parsing, no numerical execution."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import json
import os
import subprocess
import sys

import pytest

HERE = Path(__file__).parent


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


reconciliation = load(HERE / 'reconcile_retained_dual_bank_outputs.py', '_reconciliation_controls')
fixtures = load(HERE / 'test_dual_bank_wording_evaluation.py', '_frozen_metric_fixtures')
helper = fixtures.evaluation
builder = load(HERE / 'build_retained_parent_reconciliation_manifest.py', '_reconciliation_seal_controls')


def plan_pair():
    manifest = {k: '/fixture/' + k for k in reconciliation.FIELDS}
    manifest.update(schema='retained-dual-bank-parent-reconciliation-manifest/v1',
        inputs={'/fixture/input.json': 'a' * 64}, extensions={},
        source_inventories={'control': '/fixture/control.json', 'balanced': '/fixture/balanced.json'})
    return dict(deepcopy(reconciliation.PROFILE), input_sha256=manifest['inputs']), manifest


def test_only_original_parent_is_restored_no_candidate_reruns():
    plan, manifest = plan_pair()
    reconciliation.validate_plan(plan, manifest)
    assert plan['restored_models'] == 1 and plan['new_generation_panels'] == 4
    assert plan['reused_dual_panels'] == plan['reused_archived_control_panels'] == 8
    assert plan['candidate_models_restored'] is False and plan['fresh_matched_control'] is False
    assert plan['storage_bytes'] == 100000000 and plan['output_payload_cap_bytes'] == 97000000


@pytest.mark.parametrize('change', ['new_fit', 'candidate_restore', 'blind_claim', 'sealed_selector',
    'reduced_rules', 'bool_width', 'extra_manifest', 'budget_raise'])
def test_closed_phase_cannot_expand_or_relabel_reused_results(change):
    plan, manifest = plan_pair()
    if change == 'new_fit': plan['training_executed'] = True
    elif change == 'candidate_restore': plan['candidate_models_restored'] = True
    elif change == 'blind_claim': plan['fresh_holdout'] = True
    elif change == 'sealed_selector': plan['cohorts'].append('sealed60')
    elif change == 'reduced_rules': plan['rules_per_panel'] = 179
    elif change == 'bool_width': plan['dimension'] = True
    elif change == 'extra_manifest': manifest['launch_approved'] = True
    else: plan['storage_bytes'] += 1
    with pytest.raises(ValueError): reconciliation.validate_plan(plan, manifest)


def census():
    return {'complete': True, 'panels': [dict(arm=reconciliation.PARALLEL_ARM, role=role, cohort=cohort)
        for role in reconciliation.ROLES for cohort in reconciliation.COHORTS]}


def test_saved_panel_census_all_roles_all_cohorts():
    assert len(reconciliation.panel_census(census(), reconciliation.PARALLEL_ARM)) == 8


@pytest.mark.parametrize('change', ['missing', 'duplicate', 'foreign_cohort', 'wrong_role', 'incomplete'])
def test_saved_panel_census_cannot_drop_failed_rows_or_roles(change):
    data = census()
    if change == 'missing': data['panels'].pop()
    elif change == 'duplicate': data['panels'][-1] = deepcopy(data['panels'][0])
    elif change == 'foreign_cohort': data['panels'][-1]['cohort'] = 'sealed60'
    elif change == 'wrong_role': data['panels'][0]['role'] = 'initial'
    else: data['complete'] = False
    with pytest.raises(ValueError): reconciliation.panel_census(data, reconciliation.PARALLEL_ARM)


def test_case_regressions_survive_equal_aggregate_scores():
    baseline = {'formula_rows': [dict(id='a', counts={'ordered_exact': 1}), dict(id='b', counts={'ordered_exact': 0})]}
    candidate = {'formula_rows': [dict(id='a', counts={'ordered_exact': 0}), dict(id='b', counts={'ordered_exact': 1})]}
    diff = reconciliation.per_case_diff(baseline, candidate)
    assert diff['newly_wrong_ids'] == ['a'] and diff['newly_correct_ids'] == ['b']


@pytest.mark.parametrize('change', ['reorder', 'bool_exact', 'drop'])
def test_case_census_requires_position_and_exact_int_flags(change):
    baseline = {'formula_rows': [dict(id='a', counts={'ordered_exact': 1}), dict(id='b', counts={'ordered_exact': 0})]}
    candidate = deepcopy(baseline)
    if change == 'reorder': candidate['formula_rows'].reverse()
    elif change == 'bool_exact': candidate['formula_rows'][0]['counts']['ordered_exact'] = True
    else: candidate['formula_rows'].pop()
    with pytest.raises(ValueError): reconciliation.per_case_diff(baseline, candidate)


def complete_saved_packet():
    data = fixtures.packet()
    state_ref = {'path': '/fixture/state.json', 'bytes': 10, 'sha256': 'a' * 64, 'tensor_sha256': 'a' * 64}
    transform = {'mean': [0.] * 384, 'scale': 1.}
    trace = dict(data['trace'], complete=True, sample_count=48, dimension=384,
        source_rows_sha256=helper.digest(data['rows']), source_contexts_sha256=helper.digest(data['contexts']),
        codec_sha256=helper.digest(data['codec']), input_transform_sha256=helper.digest(transform),
        vocabulary_size=32, generation_temperature=0, max_target_tokens=512, batch_size=8,
        extra_model_passes=0, source_head_extra_evaluations=0, optimizer_steps=0)
    trace.update({k: True for k in ('source_only', 'full_vocabulary_retained', 'decomposition_exact',
        'caller_state_preserved', 'hooks_removed', 'complete_rollout_before_reference_scoring')})
    trace.update({k: False for k in ('reference_count_access', 'reference_prefix_access',
        'reference_documents_passed_to_model', 'inventory_access', 'source_context_target_access',
        'syntax_mask', 'forced_closure', 'model_copied', 'qualified', 'admitted', 'proof_authority',
        'source_semantics_verified', 'lake_executed', 'native_family_validation_performed')})
    trace['trace_sha256'] = helper.digest(trace)
    data['scalar'].update(trace_sha256=trace['trace_sha256'], model_tensor_sha256=trace['model_tensor_sha256'],
        codec_sha256=helper.digest(data['codec']), source_contexts_sha256=helper.digest(data['contexts']),
        references_sha256=helper.digest(data['refs']), rows_sha256=helper.digest([
            dict(row, target_ids=ref['target_ids']) for row, ref in zip(data['rows'], data['refs'])]))
    data['scalar']['score_sha256'] = helper.digest(data['scalar'])
    blobs = {'trace': trace, 'predictions': {'predictions': trace['predictions']},
        'fidelity': data['scored'], 'scalar': data['scalar'], 'join': data['joined']}
    record = dict(state_ref=state_ref, trace_ref={'fixture': 'trace'}, predictions_ref={'fixture': 'predictions'},
        formula_fidelity_ref={'fixture': 'fidelity'}, scalar_score_ref={'fixture': 'scalar'},
        scalar_formula_join_ref={'fixture': 'join'})
    panel = helper.build_gate_panel(trace, data['scored'], data['joined'], data['rows'], data['contexts'], data['refs'], data['codec'])
    record.update({k: panel[k] for k in ('formula_metrics', 'seven_facets', 'scalar_by_field')})
    return data, state_ref, transform, blobs, record


def reuse(data, state, transform, blobs, record):
    return reconciliation.reused_panel(helper, record, {'rows': data['rows'], 'source_contexts': data['contexts']},
        data['refs'], state, data['codec'], transform, lambda ref: deepcopy(blobs[ref['fixture']]))


def test_gate_panel_reuses_genuine_pure_scoring_and_all_saved_raw_rows():
    data, state, transform, blobs, record = complete_saved_packet()
    panel = reuse(data, state, transform, blobs, record)
    assert panel['formula_metrics']['ordered_exact'] == 48
    assert len(panel['formula_rows']) == 48 and all(v['total'] == 180 for v in panel['seven_facets'].values())


@pytest.mark.parametrize('change', ['checkpoint', 'tokens', 'trace_context', 'gold_target', 'scalar_drop',
    'scalar_join', 'formula_aggregate', 'facet_aggregate', 'source_aggregate'])
def test_reuse_is_not_accepting_summary_claims_without_underlying_byte_joins(change):
    data, state, transform, blobs, record = complete_saved_packet()
    if change == 'checkpoint': record['state_ref']['tensor_sha256'] = 'b' * 64;state = dict(state, tensor_sha256='a' * 64)
    elif change == 'tokens': blobs['predictions']['predictions'] = deepcopy(blobs['predictions']['predictions']);blobs['predictions']['predictions'][0]['token_ids'] = []
    elif change == 'trace_context': blobs['trace']['source_contexts_sha256'] = 'b' * 64
    elif change == 'gold_target': blobs['fidelity']['rows'][0]['expected_ir']['rules'][0]['modality'] = 'F';fixtures.rehash(blobs['fidelity'])
    elif change == 'scalar_drop': blobs['scalar']['events'].pop()
    elif change == 'scalar_join': blobs['join']['per_field']['modality']['source_correct'] = 179
    elif change == 'formula_aggregate': record['formula_metrics'] = dict(record['formula_metrics'], ordered_exact=47)
    elif change == 'facet_aggregate': record['seven_facets'] = deepcopy(record['seven_facets']);record['seven_facets']['modality']['correct'] = 179
    else: record['scalar_by_field'] = deepcopy(record['scalar_by_field']);record['scalar_by_field']['modality']['source_correct'] = 179
    with pytest.raises(ValueError): reuse(data, state, transform, blobs, record)


@pytest.mark.parametrize('field', ['trace_sha256', 'model_tensor_sha256', 'codec_sha256',
    'source_contexts_sha256', 'references_sha256', 'rows_sha256'])
def test_rehashed_scalar_metadata_from_another_trace_is_refused(field):
    data, state, transform, blobs, record = complete_saved_packet()
    scalar = blobs['scalar']
    scalar[field] = 'b' * 64
    scalar['score_sha256'] = helper.digest({k: v for k, v in scalar.items() if k != 'score_sha256'})
    with pytest.raises(ValueError, match='scalar score/trace'): reuse(data, state, transform, blobs, record)


def test_scalar_payload_change_cannot_keep_stale_canonical_score_digest():
    data, state, transform, blobs, record = complete_saved_packet()
    blobs['scalar']['events'][0]['source']['argmax_token_id'] = 31
    with pytest.raises(ValueError, match='scalar score/trace'): reuse(data, state, transform, blobs, record)


def test_scored_rows_digest_includes_exact_current_target_token_ids():
    data, state, transform, blobs, record = complete_saved_packet()
    scalar = blobs['scalar']
    scalar['rows_sha256'] = helper.digest(data['rows'])
    scalar['score_sha256'] = helper.digest({k: v for k, v in scalar.items() if k != 'score_sha256'})
    with pytest.raises(ValueError, match='scalar score/trace'): reuse(data, state, transform, blobs, record)


@pytest.mark.parametrize('role', ['selected', 'last-attempt'])
def test_actual_old_checkpoint_headers_match_original_context_without_model_imports(role):
    import json
    root = Path('/home/barberb/lift_coding/external/ipfs_datasets/workspace/test-logs')
    parent = json.loads((root / 'decoder-normative-wording-r2-20261006/training-384-r1/results/normative-wording-ce/selected-state.json').read_bytes())
    for study, phase, arm in [('decoder-dual-bank-replay-20261007', 'training-384-r1', 'dual-bank-retention-ce'),
            ('decoder-balanced-wording-20261007', 'training-384-r2', 'control-wording-ce')]:
        run = json.loads((root / study / phase / 'results' / arm / 'summary.json').read_bytes())
        report = json.loads(Path(run['training_ref']['path']).read_bytes())
        state = json.loads(Path(run['states'][role]['path']).read_bytes())
        reconciliation.checkpoint_join(state, run['states'][role], run, report, role, parent)


def test_builder_metadata_import_never_requests_tensor_encoder_or_database_modules():
    code = '''
import importlib.abc, importlib.util, sys
class Bomb(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, *args):
        if fullname.split('.')[0] in {'torch','numpy','transformers','sentence_transformers','duckdb','ducklake','huggingface_hub','ipfs_accelerate_py'}:
            raise RuntimeError('forbidden metadata import: ' + fullname)
sys.meta_path.insert(0,Bomb())
spec=importlib.util.spec_from_file_location('metadata_builder',sys.argv[1])
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
assert 'torch' not in sys.modules
'''
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    subprocess.run([sys.executable, '-c', code, str(HERE / 'build_retained_parent_reconciliation_manifest.py')],
        check=True, timeout=10, env=env)


@pytest.mark.parametrize('size', [True, 0, -1, '2'])
def test_retained_reference_declared_bytes_must_be_exact_int(tmp_path, size):
    path = tmp_path / 'metadata.json';path.write_text('{}')
    with pytest.raises(ValueError, match='typed exact'):
        builder.collect_refs({'path': str(path), 'sha256': builder.sha(path), 'bytes': size}, {}, set())


def test_historical_hash_only_metadata_pin_stays_hash_only(tmp_path):
    path = tmp_path / 'metadata.json';path.write_text('{}')
    ref = {'path': str(path), 'sha256': builder.sha(path)}
    pins, pending = {}, set()
    builder.collect_refs(ref, pins, pending)
    assert pins == {str(path): ref['sha256']} and pending == {str(path)} and 'bytes' not in ref


def test_actual_sixteen_saved_panels_join_current_unchanged_cached_sources():
    source_root = fixtures.SOURCE_ROOT
    sys.path.insert(0, str(source_root))
    from ipfs_datasets_py.logic.formalization.autoencoder import clause_source_context as context
    root = Path('/home/barberb/lift_coding')
    logs = root / 'external/ipfs_datasets/workspace/test-logs'
    initial = json.loads((logs / 'decoder-dual-bank-wording-20261007/phase-seal-r2/training-manifest.json').read_bytes())
    oldrows = json.loads(Path(initial['original_rows']).read_bytes())
    oldcontexts = json.loads(Path(initial['original_contexts']).read_bytes())
    parent = json.loads(Path(initial['runtime_options']['checkpoint_pin']['path']).read_bytes())
    envelopes = {role: json.loads(Path(path).read_bytes()) for role, path in initial['source_inventories'].items()}
    cohorts = helper.prepare_cohorts(dict(rows=oldrows, source_contexts=oldcontexts, donor=parent),
        envelopes['control'], envelopes['balanced'], context)
    v3 = logs / 'decoder-fresh-normative-style-r2-20261004/preparation-r1/results/references.json'
    refs = dict(original_train48=helper.original_train_references(oldrows['train'], parent['codec']),
        normative_train48=envelopes['control']['corpus']['references'],
        new_balanced_train48=envelopes['balanced']['corpus']['references'], exposed_v3_48=json.loads(v3.read_bytes()))
    refs = {name: helper.bind_references(cohorts[name]['rows'], values, parent['codec']) for name, values in refs.items()}
    def read_ref(ref):
        path = Path(ref['path']);raw = path.read_bytes()
        assert len(raw) == ref['bytes'] and builder.sha(path) == ref['sha256']
        return json.loads(raw)
    seen = 0
    for study, phase, arm in [('decoder-dual-bank-replay-20261007','training-384-r1',reconciliation.PARALLEL_ARM),
        ('decoder-balanced-wording-20261007','training-384-r2',reconciliation.CONTROL_ARM)]:
        summary = json.loads((logs / study / 'evaluation-r1/results/summary.json').read_bytes())
        run = json.loads((logs / study / phase / 'results' / arm / 'summary.json').read_bytes())
        for (role, cohort), record in reconciliation.panel_census(summary,arm).items():
            panel = reconciliation.reused_panel(helper,record,cohorts[cohort],refs[cohort],run['states'][role],
                parent['codec'],parent['input_transform'],read_ref)
            assert panel['rows'] == 48 and panel['expected_rules'] == 180
            seen += 1
    assert seen == 16 and 'torch' not in sys.modules
