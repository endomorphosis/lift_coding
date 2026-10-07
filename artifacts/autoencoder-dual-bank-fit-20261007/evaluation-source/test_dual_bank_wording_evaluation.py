"""Pure metric controls using genuine token parsing and complete fixture censuses.

Synthetic logits are labelled fixtures. No learned model or tensor library runs.
"""
from copy import deepcopy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import subprocess
import sys

import pytest


HERE = Path(__file__).parent
SOURCE_ROOT = Path('/home/barberb/lift_coding/.worktrees/dual-bank-wording-adapter-datasets-20261007')


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


evaluation = load(HERE / 'evaluate_dual_bank_wording_continuation.py', '_dual_evaluation_test')
fidelity = load(SOURCE_ROOT / 'ipfs_datasets_py/logic/formalization/autoencoder/decoder_source_fidelity.py', '_genuine_pure_fidelity')


def encode(value, codec):
    raw = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    parts = re.findall(r'"[^"\\]*"|[{}\[\]:,]', raw)
    assert ''.join(parts) == raw
    return [codec['target_vocabulary'].index(p) for p in parts]


def validator(value):
    assert set(value) == {'rules'}
    for rule in value['rules']:
        assert set(rule) == set(evaluation.FACETS)
        assert rule['modality'] in ('O', 'P', 'F')
        assert all(rule[k] == [] for k in ('conditions', 'exceptions', 'temporal'))
    return {'valid': True}


def packet():
    tokens = ['<pad>', '<bos>', '<eos>', '{', '}', '[', ']', ':', ',',
        *[json.dumps(k) for k in ('rules', 'actor', 'action', 'modality', 'object', 'conditions', 'exceptions', 'temporal')],
        *[json.dumps(k) for k in ('O', 'P', 'F', 'a0', 'a1', 'a2', 'x0', 'x1', 'x2', 'x3', 'x4', 'b0', 'b1')],
        'unused0', 'unused1']
    assert len(tokens) == 32
    codec = dict(schema='typed-json-lexical/v1', target_vocabulary=tokens)
    originals = [dict(actor=a, action=x, modality=m, object=b, conditions=[], exceptions=[], temporal=[])
        for m in ('O', 'P', 'F') for a in ('a0', 'a1', 'a2') for x in ('x0', 'x1', 'x2', 'x3', 'x4') for b in ('b0', 'b1')]
    rows, refs, predictions = [], [], []
    cursor = 0
    for count in (1, 2, 4, 8):
        for n in range(12):
            identity = f'fixture:{count}:{n}'
            source = '\n\n'.join(f'Authored naïve α fixture {count} {n} {i}.' for i in range(count))
            target = {'rules': [deepcopy(originals[(cursor + i) % 90]) for i in range(count)]}
            cursor += count
            content = encode(target, codec)
            rows.append(dict(id=identity, source_text=source, input=[0.125] * 384))
            refs.append(dict(id=identity, source_text=source, target=target, target_ids=[1, *content, 2], clause_count=count))
            predictions.append(dict(id=identity, token_ids=content, eos_reached=True, generation_status='eos'))
    refs = evaluation.bind_references(rows, refs, codec)
    contexts = {'fixture': 'source-only immutable context', 'ids': [r['id'] for r in rows]}
    trace = dict(predictions=predictions, model_tensor_sha256='a' * 64)
    scored = fidelity.score_predictions(refs, predictions, codec=codec, validate_rule=validator, output_limit=512)
    events = []
    for row in refs:
        for slot, rule in enumerate(row['target']['rules']):
            for field in evaluation.FIELDS:
                target = codec['target_vocabulary'].index(json.dumps(rule[field]))
                events.append(dict(id=row['id'], slot=slot, field=field, target_token_id=target,
                    source={'argmax_token_id': target}))
    scalar = dict(complete=True, events=events, unvisited_reference_sites=[], unscored_sites=[])
    joined = evaluation.join_scalar_formula(scalar, scored, refs)
    return dict(rows=rows, refs=refs, codec=codec, contexts=contexts, trace=trace, scored=scored, scalar=scalar, joined=joined)


def make_panel(data):
    return evaluation.build_gate_panel(data['trace'], data['scored'], data['joined'], data['rows'],
        data['contexts'], data['refs'], data['codec'])


def rehash(report):
    report['report_sha256'] = evaluation.digest({k: v for k, v in report.items() if k != 'report_sha256'})


def test_positive_real_token_scorer_full_census_and_unicode():
    data = packet()
    panel = make_panel(data)
    assert panel['formula_metrics']['ordered_exact'] == panel['formula_metrics']['eos_count'] == 48
    assert panel['formula_metrics']['expected_rules'] == 180
    assert all(v == {'correct': 180, 'total': 180} for v in panel['seven_facets'].values())
    assert all(v['reference_sites'] == v['visited'] == v['source_correct'] == 180 for v in panel['scalar_by_field'].values())
    assert panel['source_binding']['source_text_rows_sha256'] == evaluation.digest(
        [{k: r[k] for k in ('id', 'source_text')} for r in data['rows']])
    assert all(panel[k] is False for k in evaluation.FALSE)


@pytest.mark.parametrize('change', ['bool_token', 'bool_eos', 'none_status', 'wrong_eos_status', 'reorder', 'drop', 'extra_key'])
def test_typed_raw_prediction_refusals(change):
    data = packet()
    p = data['trace']['predictions']
    if change == 'bool_token': p[0]['token_ids'][0] = True
    elif change == 'bool_eos': p[0]['eos_reached'] = 1
    elif change == 'none_status': p[0]['generation_status'] = None
    elif change == 'wrong_eos_status': p[0]['generation_status'] = 'output_limit'
    elif change == 'reorder': p.reverse()
    elif change == 'drop': p.pop()
    else: p[0]['target_ids'] = []
    with pytest.raises(ValueError): evaluation.typed_predictions(p, data['rows'])


@pytest.mark.parametrize('change', ['bool_count', 'missing_row', 'reorder', 'aggregate_lie', 'facet_lie',
    'source_text', 'source_sha', 'token_join', 'expected_target', 'codec_join', 'row_denominator'])
def test_complete_fidelity_joins_not_aggregate_fabrication(change):
    data = packet()
    f = data['scored']
    if change == 'bool_count': f['rows'][0]['counts']['rows'] = True
    elif change == 'missing_row': f['rows'].pop()
    elif change == 'reorder': f['rows'].reverse()
    elif change == 'aggregate_lie': f['metrics']['ordered_exact'] = 47
    elif change == 'facet_lie': f['by_facet']['action']['correct'] = 179
    elif change == 'source_text': f['rows'][0]['source_provenance']['source_text'] += 'changed'
    elif change == 'source_sha': f['rows'][0]['source_provenance']['source_sha256'] = 'b' * 64
    elif change == 'token_join': f['rows'][0]['generated_token_ids'] = []
    elif change == 'expected_target': f['rows'][0]['expected_ir']['rules'][0]['action'] = 'x4'
    elif change == 'codec_join': f['codec_sha256'] = 'b' * 64
    else: f['rows'][0]['by_facet']['action']['total'] = 0
    rehash(f)
    with pytest.raises(ValueError): make_panel(data)


@pytest.mark.parametrize('change', ['early_eos', 'wrong_modality', 'missing_rule', 'extra_rule', 'duplicate_rule', 'wrong_order'])
def test_genuine_scorer_retains_per_row_failures(change):
    data = packet()
    index = next(i for i, r in enumerate(data['refs']) if r['clause_count'] == 8)
    target = deepcopy(data['refs'][index]['target'])
    if change == 'early_eos': target['rules'] = []
    elif change == 'wrong_modality': target['rules'][0]['modality'] = 'F' if target['rules'][0]['modality'] != 'F' else 'O'
    elif change == 'missing_rule': target['rules'].pop()
    elif change == 'extra_rule': target['rules'].append(deepcopy(target['rules'][0]))
    elif change == 'duplicate_rule': target['rules'][1] = deepcopy(target['rules'][0])
    else: target['rules'].reverse()
    data['trace']['predictions'][index]['token_ids'] = encode(target, data['codec'])
    data['scored'] = fidelity.score_predictions(data['refs'], data['trace']['predictions'], codec=data['codec'], validate_rule=validator, output_limit=512)
    data['joined'] = evaluation.join_scalar_formula(data['scalar'], data['scored'], data['refs'])
    panel = make_panel(data)
    assert panel['formula_metrics']['ordered_exact'] == 47
    assert len(panel['formula_rows']) == 48 and panel['formula_rows'][index]['counts']['ordered_exact'] == 0
    assert panel['formula_metrics']['expected_rules'] == 180
    assert all(v['total'] == 180 for v in panel['seven_facets'].values())


@pytest.mark.parametrize('change', ['duplicate', 'foreign', 'drop', 'unavailable'])
def test_scalar_denominators_include_unvisited_and_unavailable(change):
    data = packet()
    scalar = data['scalar']
    event = scalar['events'][0]
    if change == 'duplicate': scalar['events'].append(deepcopy(event))
    elif change == 'foreign': scalar['events'][0]['id'] = 'not-a-source'
    elif change == 'drop': scalar['events'].pop()
    else:
        scalar['events'].pop(0)
        site = {k: event[k] for k in ('id', 'slot', 'field')}
        scalar['unvisited_reference_sites'] = [site]
        scalar['unscored_sites'] = [site]
    if change == 'unavailable':
        result = evaluation.join_scalar_formula(scalar, data['scored'], data['refs'])
        assert result['per_field'][event['field']]['unavailable'] == 1
        assert result['per_field'][event['field']]['source_correct'] == 179
    else:
        with pytest.raises(ValueError): evaluation.join_scalar_formula(scalar, data['scored'], data['refs'])


def bank_packet():
    data = packet()
    bank = {'rows': []}
    readout = dict(complete=True, row_count=180, reference_fields=720, model_tensor_sha256='a' * 64,
        source_targets_joined_after_numeric_return=True, source_forwards_owned_by_inherited_evaluator=True,
        extra_source_forwards=0, optimizer_steps=0, rows=[], by_field={}, qualified=False, admitted=False,
        proof_authority=False, used_for_selection=False)
    for i, ref in enumerate(data['refs']):
        for slot, rule in enumerate(ref['target']['rules']):
            text = f'Independent synthetic bank source {i} {slot}.'
            row = dict(id=f'bank:{i}:{slot}', source_sha256=hashlib.sha256(text.encode()).hexdigest(),
                template='fixture', target=deepcopy(rule))
            bank['rows'].append(row)
            fields = {}
            for field in evaluation.FIELDS:
                target = data['codec']['target_vocabulary'].index(json.dumps(rule[field]))
                logits = [0.] * 32
                logits[target] = 2.
                ce = 2. + math.log(math.fsum(math.exp(v - 2.) for v in logits)) - 2.
                fields[field] = dict(target_token_id=target, argmax_token_id=target, correct=True,
                    full32_logits=logits, cross_entropy=ce, margin=2.)
            readout['rows'].append(dict(row_id=row['id'], source_sha256=row['source_sha256'], template=row['template'],
                original_rule_sha256=evaluation.digest(rule), fields=fields))
    readout['by_field'] = {f: {'correct': 180, 'total': 180} for f in evaluation.FIELDS}
    return data, bank, readout


def test_both_complete_bank_fields_require_full32_observations():
    data, bank, readout = bank_packet()
    assert evaluation.verified_bank_metrics(readout, bank, data['codec'], 'a' * 64) == readout['by_field']


@pytest.mark.parametrize('change', ['bool_logits', 'ragged', 'nonfinite', 'wrong_argmax', 'wrong_target',
    'wrong_correct', 'wrong_confidence', 'aggregate_lie', 'reorder', 'wrong_template', 'wrong_source', 'wrong_tensor', 'missing_field'])
def test_complete_bank_observation_controls(change):
    data, bank, r = bank_packet()
    row = r['rows'][0]
    field = row['fields']['modality']
    if change == 'bool_logits': field['full32_logits'][0] = True
    elif change == 'ragged': field['full32_logits'].pop()
    elif change == 'nonfinite': field['full32_logits'][0] = float('nan')
    elif change == 'wrong_argmax': field['argmax_token_id'] = 0
    elif change == 'wrong_target': field['target_token_id'] = 0
    elif change == 'wrong_correct': field['correct'] = False
    elif change == 'wrong_confidence': field['cross_entropy'] += .01
    elif change == 'aggregate_lie': r['by_field']['action']['correct'] = 179
    elif change == 'reorder': r['rows'].reverse()
    elif change == 'wrong_template': row['template'] = 'foreign'
    elif change == 'wrong_source': row['source_sha256'] = 'b' * 64
    elif change == 'wrong_tensor': r['model_tensor_sha256'] = 'b' * 64
    else: row['fields'].pop('object')
    with pytest.raises(ValueError): evaluation.verified_bank_metrics(r, bank, data['codec'], 'a' * 64)


def test_compact_writer_fresh_paths_and_physical_budget(tmp_path):
    save = evaluation.compact_writer(tmp_path, 30)
    p = tmp_path / 'a.json'
    ref = save(p, {'a': 1})
    assert ref['bytes'] == p.stat().st_size == 8
    with pytest.raises(FileExistsError): save(p, {'a': 1})
    with pytest.raises(ValueError, match='budget'): save(tmp_path / 'b.json', {'large': 'x' * 50})
    assert not (tmp_path / 'b.json').exists()


def test_private_parent_alias_fails_endpoint_capture(tmp_path):
    parent = tmp_path / 'assets'
    parent.mkdir()
    path = parent / 'source.json'
    path.write_bytes(b'{}')
    wanted = evaluation.sha(path)
    evaluation._capture(path, wanted)
    moved = tmp_path / 'moved'
    parent.rename(moved)
    parent.symlink_to(moved, target_is_directory=True)
    with pytest.raises(ValueError, match='canonical'): evaluation._capture(path, wanted)


def test_module_import_is_stdlib_only_under_ml_database_import_bombs():
    code = r'''
import importlib.abc,importlib.util,sys
class Bomb(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.split('.')[0] in {'torch','numpy','transformers','duckdb','sqlite3','huggingface_hub'}:
   raise RuntimeError('forbidden '+fullname)
sys.meta_path.insert(0,Bomb())
s=importlib.util.spec_from_file_location('evaluation',sys.argv[1]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
assert not {'torch','numpy','duckdb','transformers'}&set(sys.modules)
'''
    result = subprocess.run([sys.executable, '-c', code, str(HERE / 'evaluate_dual_bank_wording_continuation.py')], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def manifest_plan():
    manifest = dict(schema='dual-bank-wording-postfit-evaluation-manifest/v1',
        inputs={'/fixture/input.json': 'a' * 64}, extensions={evaluation.NUMERIC_RELATIVE: 'a' * 64},
        plan_sha256='a' * 64, comparison_protocol='/fixture/protocol.json',
        training_manifest='/fixture/training-manifest.json', training_plan='/fixture/training-plan.json',
        training_summary='/fixture/training-summary.json', training_terminal={'child_exit': '/fixture/exit.json',
            'resources_final': '/fixture/resources.json'}, source_inventories={'control': '/fixture/control.json',
            'balanced': '/fixture/balanced.json'}, v3_references='/fixture/known-v3.json')
    plan = dict(deepcopy(evaluation.PROFILE), input_sha256=deepcopy(manifest['inputs']))
    return manifest, plan


def test_closed_matched_profile_keeps_parent_all_roles_and_budget():
    manifest, plan = manifest_plan()
    evaluation.validate_plan(plan, manifest)
    assert plan['logical_panels'] == plan['physical_panels'] == 20
    assert plan['raw_original_probe_panels'] == 45 and plan['parent_baseline_included'] is True
    assert plan['storage_bytes'] == 100000000 and plan['output_payload_cap_bytes'] == 97000000
    assert plan['expected_bank_source_head_forward_calls'] == 300
    assert plan['raw_extra_count_head_passes_per_panel'] == 6
    assert plan['main_trace_observation_scope'].startswith('Twenty greedy panels only;')


@pytest.mark.parametrize('change', ['extra_manifest', 'extra_plan', 'sealed_selector', 'missing_parent',
    'bool_panels', 'reduced_denominator', 'extra_bank', 'budget_raise', 'scalar_head_extra_pass'])
def test_plan_must_not_waive_cohorts_or_select_exposed_panels(change):
    manifest, plan = manifest_plan()
    if change == 'extra_manifest': manifest['approved'] = True
    elif change == 'extra_plan': plan['sealed60_accuracy'] = 1.
    elif change == 'sealed_selector': plan['cohorts'].append('sealed60')
    elif change == 'missing_parent': plan['parent_baseline_included'] = False
    elif change == 'bool_panels': plan['physical_panels'] = True
    elif change == 'reduced_denominator': plan['rules_per_panel'] = 179
    elif change == 'extra_bank': manifest['source_inventories']['foreign'] = '/fixture/foreign.json'
    elif change == 'budget_raise': plan['storage_bytes'] += 1
    else: plan['extra_source_head_passes'] = 1
    with pytest.raises(ValueError): evaluation.validate_plan(plan, manifest)


def barrier(tmp_path):
    refs = []
    labels = [('parent', 'selected', c) for c in evaluation.COHORTS]
    labels += [(a, r, c) for a in evaluation.ARMS for r in evaluation.ROLES for c in evaluation.COHORTS]
    save = evaluation.compact_writer(tmp_path)
    for i, (arm, role, cohort) in enumerate(labels):
        trace = evaluation.durable(save, tmp_path / f'{i}-trace.json', {'fixture': 'synthetic'})
        pred = evaluation.durable(save, tmp_path / f'{i}-pred.json', {'fixture': 'synthetic'})
        refs.append(dict(arm=arm, role=role, cohort=cohort, trace_ref=trace, predictions_ref=pred,
            prediction_fsynced=True, physical_panel_computed=True))
    return refs


def test_barrier_rehashes_all_twenty_physical_parent_candidate_panels(tmp_path):
    evaluation.verify_barrier(barrier(tmp_path))


@pytest.mark.parametrize('change', ['drop_parent', 'duplicate', 'unfsynced', 'claimed_physical_bool', 'changed_prediction'])
def test_barrier_refuses_partial_or_changed_records_before_v3_read(change, tmp_path):
    records = barrier(tmp_path)
    if change == 'drop_parent': records.pop(0)
    elif change == 'duplicate': records[-1] = deepcopy(records[0])
    elif change == 'unfsynced': records[0]['prediction_fsynced'] = False
    elif change == 'claimed_physical_bool': records[0]['physical_panel_computed'] = 1
    else: Path(records[-1]['predictions_ref']['path']).write_text('{}')
    with pytest.raises(ValueError): evaluation.verify_barrier(records)


def test_positive_formula_facets_still_fail_complete_eos_floor():
    data = packet()
    data['trace']['predictions'][0].update(eos_reached=False, generation_status='output_limit')
    data['scored'] = fidelity.score_predictions(data['refs'], data['trace']['predictions'], codec=data['codec'], validate_rule=validator, output_limit=512)
    data['joined'] = evaluation.join_scalar_formula(data['scalar'], data['scored'], data['refs'])
    panel = make_panel(data)
    assert panel['formula_metrics']['eos_count'] == panel['formula_metrics']['ordered_exact'] == 47
    assert all(v == {'correct': 180, 'total': 180} for v in panel['seven_facets'].values())


def test_source_correct_and_generated_formula_wrong_remain_independent():
    data = packet()
    data['trace']['predictions'][0]['token_ids'] = encode({'rules': [dict(data['refs'][0]['target']['rules'][0], modality='F')]}, data['codec'])
    data['scored'] = fidelity.score_predictions(data['refs'], data['trace']['predictions'], codec=data['codec'], validate_rule=validator, output_limit=512)
    result = evaluation.join_scalar_formula(data['scalar'], data['scored'], data['refs'])
    assert result['per_field']['modality']['source_correct'] == 180
    assert result['per_field']['modality']['source_correct_formula_wrong'] == 1
    assert data['scored']['metrics']['ordered_exact'] == 47


def endpoint_packet(role='selected'):
    parent = dict(schema='private-native-dimension-source-state/v1', initializer_receipt={'fixture': 'original'},
        architecture={'dimension': 384, 'fixture': 'unchanged geometry'})
    ctx = dict(restore_packet={'checkpoint': parent}, donor={'codec': {'target_vocabulary': ['fixture']},
        'input_transform': {'mean': [0.], 'scale': 1.}}, lineage={'fixture': 'retained'},
        parent_summary={'states': {'selected': {'path': '/fixture/parent.json', 'sha256': 'a' * 64}}},
        pins={'/fixture/source.json': 'a' * 64}, run_id='fixture-run',
        phase_manifest_ref={'path': '/fixture/manifest.json', 'sha256': 'a' * 64},
        phase_plan_ref={'path': '/fixture/plan.json', 'sha256': 'a' * 64})
    run = dict(arm='dual_bank_replay', recipe={'name': 'dual_bank_replay', 'weight': .05},
        training_ref={'path': '/fixture/training.json', 'sha256': 'a' * 64},
        states={role: {'tensor_sha256': 'b' * 64}})
    report = {'selected_weights_sha256': 'b' * 64, 'last_complete_attempt_weights_sha256': 'b' * 64}
    state = dict(role=role, selected=True, recipe=deepcopy(run['recipe']), dimension=384,
        schema=parent['schema'], state_serialization_schema=parent['schema'], ir_family_id='legal_ir',
        dimension_role='input_embedding', task_id='semantic_IR_reconstruction', native_ir_schema_version=None,
        decoder_profile_id=None, decoder_format_id=None, codec=deepcopy(ctx['donor']['codec']),
        codec_sha256=evaluation.digest(ctx['donor']['codec']), input_transform=deepcopy(ctx['donor']['input_transform']),
        initializer_receipt=deepcopy(parent['initializer_receipt']), architecture=deepcopy(parent['architecture']),
        lineage=deepcopy(ctx['lineage']), model_state={'fixture': [0.]}, tensor_sha256='b' * 64,
        continuation_parent=deepcopy(ctx['parent_summary']['states']['selected']), continuation_source_refs=deepcopy(ctx['pins']),
        continuation_run_id=ctx['run_id'], continuation_arm=run['arm'], continuation_role=role,
        continuation_recipe=deepcopy(run['recipe']), continuation_training_ref=deepcopy(run['training_ref']),
        continuation_training_executed=True, continuation_phase_manifest=deepcopy(ctx['phase_manifest_ref']),
        continuation_phase_plan=deepcopy(ctx['phase_plan_ref']), **evaluation.FALSE)
    state['weights_sha256'] = evaluation.digest(state['model_state'])
    return ctx, run, report, state


@pytest.mark.parametrize('role', ['selected', 'last-attempt'])
def test_selected_and_last_aliases_keep_exact_roles_with_same_tensor(role):
    ctx, run, report, state = endpoint_packet(role)
    evaluation.verify_endpoint_join(ctx, run, report, role, state)


@pytest.mark.parametrize('change', ['family', 'task', 'dimension_role', 'width', 'bool_width', 'role', 'codec',
    'codec_sha', 'transform', 'initializer', 'architecture', 'lineage', 'weights', 'report_tensor', 'parent',
    'source_refs', 'run', 'arm', 'continuation_role', 'recipe', 'training_ref', 'phase_manifest', 'phase_plan',
    'training_executed', 'native_profile', 'proof_authority'])
def test_state_cannot_bypass_original_context_and_exact_report_receipt(change):
    ctx, run, report, s = endpoint_packet()
    if change == 'family': s['ir_family_id'] = 'security_ir'
    elif change == 'task': s['task_id'] = 'legal_prose_reconstruction'
    elif change == 'dimension_role': s['dimension_role'] = 'output_embedding'
    elif change == 'width': s['dimension'] = 768
    elif change == 'bool_width': s['dimension'] = True
    elif change == 'role': s['role'] = 'last-attempt'
    elif change == 'codec': s['codec']['target_vocabulary'].append('changed')
    elif change == 'codec_sha': s['codec_sha256'] = 'c' * 64
    elif change == 'transform': s['input_transform']['scale'] = 2.
    elif change == 'initializer': s['initializer_receipt']['fixture'] = 'foreign'
    elif change == 'architecture': s['architecture']['dimension'] = 768
    elif change == 'lineage': s['lineage']['fixture'] = 'foreign'
    elif change == 'weights': s['weights_sha256'] = 'c' * 64
    elif change == 'report_tensor': report['selected_weights_sha256'] = 'c' * 64
    elif change == 'parent': s['continuation_parent']['sha256'] = 'c' * 64
    elif change == 'source_refs': s['continuation_source_refs']['/fixture/source.json'] = 'c' * 64
    elif change == 'run': s['continuation_run_id'] = 'foreign'
    elif change == 'arm': s['continuation_arm'] = 'retained_bank_control'
    elif change == 'continuation_role': s['continuation_role'] = 'last-attempt'
    elif change == 'recipe': s['continuation_recipe']['weight'] = 0.
    elif change == 'training_ref': s['continuation_training_ref']['sha256'] = 'c' * 64
    elif change == 'phase_manifest': s['continuation_phase_manifest']['sha256'] = 'c' * 64
    elif change == 'phase_plan': s['continuation_phase_plan']['sha256'] = 'c' * 64
    elif change == 'training_executed': s['continuation_training_executed'] = 1
    elif change == 'native_profile': s['decoder_profile_id'] = 'invented'
    else: s['proof_authority'] = 0
    with pytest.raises(ValueError): evaluation.verify_endpoint_join(ctx, run, report, 'selected', s)
