"""Bounded target-free replay of retained native768 source-span decoders."""
from collections import Counter
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import sys
import time

ROOT = Path('/home/barberb/lift_coding')
REPO = ROOT / 'external/ipfs_datasets'
CAMPAIGN = ROOT / 'artifacts/autoformalization-alignment-20261003'
OUTPUT = CAMPAIGN / 'span-replay-01'
CONTROLS = ('none', 'zero', 'disabled', 'rotate')
MAX_SECONDS = 180
MAX_RSS_KIB = 2 * 1024 * 1024


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def bind(path):
    path = Path(path)
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def load(path):
    return json.loads(Path(path).read_bytes())


def verify(ref):
    current = bind(ref['path'])
    assert current['sha256'] == ref['sha256'], ref['path']
    if 'bytes' in ref:
        assert current['bytes'] == ref['bytes'], ref['path']
    return current


def save(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')
    return bind(path)


def generation(row):
    return {key: row[key] for key in ('status', 'reason', 'canonical_ir')}


def compare(left, right):
    assert len(left['rows']) == len(right['rows']) == 34
    changed = []
    max_logit_difference = 0.
    numerical_rows = 0
    for index, (a, b) in enumerate(zip(left['rows'], right['rows'])):
        assert a['source_sha256'] == b['source_sha256']
        if generation(a) != generation(b):
            changed.append(index)
        x = a.get('span_diagnostics', {}).get('modality_logits')
        y = b.get('span_diagnostics', {}).get('modality_logits')
        if x is not None and y is not None:
            assert len(x) == len(y) == 3 and all(math.isfinite(v) for v in x + y)
            max_logit_difference = max(max_logit_difference, *(abs(u - v) for u, v in zip(x, y)))
            numerical_rows += 1
    return {'generation_changed_count': len(changed), 'generation_changed_row_positions': changed,
            'modality_logit_comparison_rows': numerical_rows,
            'max_abs_modality_logit_difference': max_logit_difference}


def summary(result):
    return {'decoded_count': result['decoded_count'],
            'abstention_reasons': dict(Counter(row['reason'] for row in result['rows'] if row['status'] != 'decoded')),
            'model_state_unchanged': result['model_state_unchanged'], 'target_access': False,
            'teacher_forcing': False, 'source_fidelity_established': False}


def main():
    started = time.monotonic()
    resource.setrlimit(resource.RLIMIT_CPU, (120, 130))
    os.environ['CUDA_VISIBLE_DEVICES'] = ''
    discovery = load(CAMPAIGN / 'decoder-discovery-01/inventory.json')
    assert discovery['content_sha256'] == digest({k: v for k, v in discovery.items() if k != 'content_sha256'})
    prior = load(CAMPAIGN / 'plan-synthesis-01/validation.json')
    assert prior['content_sha256'] == digest({k: v for k, v in prior.items() if k != 'content_sha256'})
    inputs_path = CAMPAIGN / 'richer-embedding-01/embedding_inputs.json'
    lane_path = CAMPAIGN / 'richer-embedding-01/native768_embeddings.json'
    input_refs = [bind(inputs_path), bind(lane_path), bind(CAMPAIGN / 'richer-01/panel.json'),
                  bind(CAMPAIGN / 'decoder-discovery-01/inventory.json'),
                  bind(CAMPAIGN / 'decoder-discovery-01/source-span-static-admission.json'),
                  bind(CAMPAIGN / 'plan-synthesis-01/validation.json')]
    static = load(CAMPAIGN / 'decoder-discovery-01/source-span-static-admission.json')
    assert static['content_sha256'] == digest({k: v for k, v in static.items() if k != 'content_sha256'})
    sources = [verify(ref) for ref in discovery['preserved_prior_bindings']]
    sources += [verify(ref) for ref in static['checkpoint_implementation_bindings']]
    checkpoint_refs = []
    for item in discovery['source_span_decoders']['runs']:
        checkpoint_refs += [verify(item['selected_checkpoint']), verify(item['last_checkpoint'])]
    inputs = load(inputs_path)
    lane = load(lane_path)
    sys.path.insert(0, str(REPO))
    from ipfs_datasets_py.logic.formalization.autoencoder import alignment_richer_embeddings as embeddings
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer import legal_span_dimensions as owner
    embeddings.validate_richer_embedding_inputs(inputs)
    embeddings.validate_embedding_lane(lane, inputs)
    assert lane['status'] == 'produced' and lane['lane_id'] == 'native768' and lane['dimension'] == 768
    assert lane['backend_evidence']['execution_kind'] == 'observed_native'
    assert len(inputs['rows']) == len(lane['receipts']) == 34
    by_id = {row['id']: row for row in lane['receipts']}
    texts = [row['source_text'] for row in inputs['rows']]
    vectors = [by_id[row['id']]['embedding'] for row in inputs['rows']]
    context_positions = [index for index, row in enumerate(inputs['rows'])
                         if row['context_role'] == 'explicit_assumptions']
    assert len(context_positions) == 2
    context_left, context_right = context_positions
    assert texts[context_left] == texts[context_right]
    assert vectors[context_left] == vectors[context_right]
    for row, vector in zip(inputs['rows'], vectors):
        assert hashlib.sha256(row['source_text'].encode()).hexdigest() == row['source_sha256']
        assert by_id[row['id']]['source_sha256'] == row['source_sha256']
        assert by_id[row['id']]['embedding_sha256'] == digest(vector)
        owner.span.tokenize_source(row['source_text'])

    import torch
    torch.set_num_threads(1)
    torch.set_default_dtype(torch.float32)
    torch.set_default_device('cpu')
    rng_before = torch.get_rng_state().clone()
    calls = {'optimizer_steps': 0, 'inference_calls': 0, 'row_forward_calls': 0}
    def forbid_step(*args, **kwargs):
        calls['optimizer_steps'] += 1
        raise RuntimeError('optimizer updates forbidden in decoder replay')
    torch.optim.Adam.step = forbid_step
    def admission():
        assert time.monotonic() - started < MAX_SECONDS, 'replay wall budget exceeded'
        assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss < MAX_RSS_KIB, 'replay RSS budget exceeded'
    OUTPUT.mkdir(exist_ok=False)
    plan = {'schema': 'alignment-source-span-replay-plan/v1', 'input_bindings': input_refs,
            'checkpoint_bindings': checkpoint_refs, 'implementation_bindings': sources,
            'runner_binding': bind(__file__), 'rows': 34, 'seeds': [1729, 1730, 1731],
            'states': ['constructed_initial_control', 'selected400', 'last800'],
            'controls': list(CONTROLS), 'source_input_recipe': 'exact_source_only',
            'context_assumptions_forwarded': False, 'new_encoder_calls': 0,
            'normalization_or_alias_mapping_added': False, 'evaluation_role': 'exposed_authored_development',
            'posthoc_reference_scope': 'literal_source_span_contract_only', 'max_seconds': MAX_SECONDS,
            'max_rss_kib': MAX_RSS_KIB, 'cpu_threads': 1, 'device': 'cpu', 'dtype': 'float32',
            'training_executed': False, 'qualified': False, 'proof_authority': False}
    plan_ref = save(OUTPUT / 'plan.json', plan)
    join_rows = [{'id': row['id'], 'input_sha256': row['input_sha256'],
                  'source_sha256': row['source_sha256'], 'embedding_sha256': by_id[row['id']]['embedding_sha256'],
                  'token_input_sha256': by_id[row['id']]['token_input_sha256'],
                  'context_role': row['context_role'], 'context_forwarded': False,
                  'rotated_donor_id': inputs['rows'][(index + 1) % 34]['id'],
                  'rotated_donor_source_sha256': inputs['rows'][(index + 1) % 34]['source_sha256'],
                  'rotated_source_differs': row['source_sha256'] != inputs['rows'][(index + 1) % 34]['source_sha256'],
                  'rotated_embedding_differs': vector != vectors[(index + 1) % 34]}
                 for index, (row, vector) in enumerate(zip(inputs['rows'], vectors))]
    join_ref = save(OUTPUT / 'source_input_joins.json', {'schema': 'alignment-source-span-replay-joins/v1',
                   'input_payload_sha256': inputs['payload_sha256'], 'lane_payload_sha256': lane['payload_sha256'],
                   'profile_id': lane['backend_evidence']['profile_id'], 'rows': join_rows})
    observed = []
    outputs_for_scoring = {}
    reload_count = 0
    for item in discovery['source_span_decoders']['runs']:
        checkpoint = owner.load_checkpoint(item['selected_checkpoint']['path'],
                                           expected_sha256=item['selected_checkpoint']['sha256'])
        assert lane['backend_evidence']['profile_id'] == checkpoint['context_contract']['representation_id']
        initial = copy.deepcopy(checkpoint)
        initial['model_state'] = owner._initial_state(initial['source_parent_checkpoint'], initial['config'])
        assert owner.checkpoint_digest(initial['model_state']) == checkpoint['initial_model_state_sha256']
        initial.update(optimizer_state={'schema': 'adam-default-betas-eps/v1', 'parameters': {}},
                       progress={'epochs_completed': 0, 'row_cursor': 0, 'optimizer_steps': 0},
                       parent_checkpoint_sha256=None)
        initial_ref = save(OUTPUT / f"seed{item['seed']}-constructed-initial-control.json", initial)
        last = owner.load_checkpoint(item['last_checkpoint']['path'],
                                     expected_sha256=item['last_checkpoint']['sha256'])
        for role, state, ref in [('constructed_initial_control', initial, initial_ref),
                                 ('selected400', checkpoint, item['selected_checkpoint']),
                                 ('last800', last, item['last_checkpoint'])]:
            admission()
            model_started = time.monotonic()
            reader = owner.DimensionalSpanDecoder(state)
            params = dict(reader.model.named_parameters())
            assert len(params) == 23 and sum(p.numel() for p in params.values()) == 33271
            assert all(p.device.type == 'cpu' and p.dtype == torch.float32 for p in params.values())
            model_digest_before = owner.checkpoint_digest({k: v.tolist() for k, v in reader.model.state_dict().items()})
            results = {}
            paths = {}
            for control in CONTROLS:
                admission()
                with torch.inference_mode():
                    result = reader.decode_formal_logic(texts, vectors, latent_ablation=control)
                calls['inference_calls'] += 1
                calls['row_forward_calls'] += 34
                assert result['target_access'] is False and result['teacher_forcing'] is False
                assert result['training_executed'] is False and result['model_state_unchanged'] is True
                for index, row in enumerate(result['rows']):
                    effective = ([0.] * 768 if control == 'zero' else vectors[(index + 1) % 34]
                                 if control == 'rotate' else vectors[index])
                    assert row['source_sha256'] == inputs['rows'][index]['source_sha256']
                    assert row['latent_sha256'] == owner.checkpoint_digest(effective)
                    assert row['latent_input_enabled'] is (control != 'disabled')
                results[control] = result
                paths[control] = save(OUTPUT / f"seed{item['seed']}-{role}-{control}.json", result)
            context_predictions_equal = (
                results['none']['rows'][context_left] == results['none']['rows'][context_right])
            assert context_predictions_equal, 'identical source-only context inputs differ'
            fresh = owner.DimensionalSpanDecoder(state)
            fresh_params = dict(fresh.model.named_parameters())
            assert all(params[k].data_ptr() != fresh_params[k].data_ptr() for k in params)
            with torch.inference_mode():
                repeated = fresh.decode_formal_logic(texts, vectors, latent_ablation='none')
            calls['inference_calls'] += 1
            calls['row_forward_calls'] += 34
            assert repeated == results['none'], 'private reload output replay differs'
            reload_count += 1
            repeat_ref = save(OUTPUT / f"seed{item['seed']}-{role}-none-private-reload.json", repeated)
            model_digest_after = owner.checkpoint_digest({k: v.tolist() for k, v in reader.model.state_dict().items()})
            assert model_digest_before == model_digest_after == owner.checkpoint_digest(state['model_state'])
            observed.append({'seed': item['seed'], 'role': role, 'checkpoint_binding': ref,
                             'checkpoint_payload_sha256': owner.checkpoint_digest(state),
                             'model_state_sha256': model_digest_before, 'model_state_unchanged': True,
                             'recorded_optimizer_steps': state['progress']['optimizer_steps'],
                             'adam_moment_restore_validated': True, 'optimizer_resume_executed': False,
                             'model_parameter_count': 33271, 'model_tensor_count': 23,
                             'output_bindings': paths, 'private_reload_binding': repeat_ref,
                             'private_reload_bitwise_json_equal': True, 'private_models_disjoint_storage': True,
                             'context_pair_equal_source_only': context_predictions_equal,
                             'summaries': {k: summary(v) for k, v in results.items()},
                             'control_comparisons': {k: compare(results['none'], results[k]) for k in CONTROLS[1:]},
                             'elapsed_seconds': time.monotonic() - model_started})
            outputs_for_scoring[(item['seed'], role)] = results['none']
            del reader, fresh, params, fresh_params

    # References are loaded only after all target-free numerical forwards finish.
    panel = load(CAMPAIGN / 'richer-01/panel.json')
    panel_by_input = {row['input_sha256']: row for row in panel['rows']}
    scope_rows = []
    for row in inputs['rows']:
        reference = panel_by_input[row['input_sha256']]
        assert reference['source_sha256'] == row['source_sha256']
        eligible, reason = False, 'diagnostic_nonpositive_or_context_unapplied'
        if reference['row_kind'] == 'positive' and row['context_role'] == 'none_required':
            try:
                owner.span._labels(row['source_text'], reference['target'], owner.span.tokenize_source(row['source_text']))
                eligible, reason = True, None
            except ValueError as error:
                reason = str(error)
        scope_rows.append({'id': row['id'], 'panel_id': reference['id'], 'row_kind': reference['row_kind'],
                           'literal_reference_compatible': eligible, 'reason': reason,
                           'independent_review_status': reference['provenance']['review_status']})
    compatibility = {row['id']: row['literal_reference_compatible'] for row in scope_rows}
    literal_count = sum(compatibility.values())
    exact = []
    for (seed, role), result in outputs_for_scoring.items():
        matches = sum(compatibility[row['id']] and prediction['canonical_ir'] ==
                      panel_by_input[row['input_sha256']]['target']
                      for row, prediction in zip(inputs['rows'], result['rows']))
        exact.append({'seed': seed, 'role': role, 'literal_compatible_reference_count': literal_count,
                      'literal_exact_count': matches, 'literal_exact_rate': matches / literal_count if literal_count else None,
                      'independent_source_fidelity_established': False})
    scope_ref = save(OUTPUT / 'posthoc_reference_scope.json', {
        'schema': 'alignment-source-span-literal-reference-scope/v1', 'rows': scope_rows,
        'literal_compatible_reference_count': literal_count, 'scores': exact,
        'semantic_alias_mapping_added': False, 'references_used_for_generation': False,
        'qualified': False, 'source_fidelity_established': False})
    for ref in sources + input_refs + checkpoint_refs:
        verify(ref)
    module_sources = []
    for name, module in sorted(sys.modules.items()):
        path = getattr(module, '__file__', None)
        if path and Path(path).suffix == '.py' and Path(path).resolve().is_relative_to(REPO):
            module_sources.append(dict(bind(path), module_name=name))
    assert calls['optimizer_steps'] == 0 and calls['inference_calls'] == 45 and calls['row_forward_calls'] == 1530
    admission()
    report = {'schema': 'alignment-source-span-replay-report/v1', 'status': 'completed_unqualified',
              'plan_binding': plan_ref, 'source_input_joins_binding': join_ref, 'reference_scope_binding': scope_ref,
              'runner_binding': bind(__file__), 'runs': observed, 'source_bindings': sources,
              'loaded_repository_modules': module_sources, 'complete_dependency_manifest': False,
              'calls': calls, 'checkpoint_states_replayed': 9, 'private_reload_comparisons': reload_count,
              'literal_compatible_reference_count': literal_count,
              'context_pair_positions': context_positions,
              'context_pair_source_and_embedding_equal': True,
              'context_pair_equal_source_only': all(run['context_pair_equal_source_only'] for run in observed),
              'torch_version': str(torch.__version__), 'cpu_threads': torch.get_num_threads(),
              'device': 'cpu', 'dtype': 'float32', 'rng_state_unchanged': bool(torch.equal(rng_before, torch.get_rng_state())),
              'max_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
              'elapsed_seconds': time.monotonic() - started,
              'new_encoder_calls': 0, 'proof_calls': 0, 'training_executed': False,
              'original_validation_accessed': False, 'sealed_final_test_accessed': False,
              'independent_review_completed': False, 'qualified': False, 'proof_authority': False,
              'source_fidelity_established': False,
              'limitations': ['Constructed initial controls are exact initializer reconstructions, not retained trained checkpoints.',
                              'Raw source-only vectors withhold explicit assumptions.',
                              'Source-span copying cannot emit normalized aliases absent from source tokens.',
                              'Decoded means supported single-rule syntax, not independently faithful source meaning.',
                              'Moment restoration validates saved Adam state but does not execute optimizer resumption.',
                              'Observed private reload equality is specific to this CPU process and input panel.']}
    report['content_sha256'] = digest(report)
    ref = save(OUTPUT / 'report.json', report)
    print(json.dumps({'report': ref, 'checkpoint_states_replayed': 9, 'row_forward_calls': 1530,
                      'private_reload_comparisons': 9, 'literal_compatible_reference_count': literal_count,
                      'elapsed_seconds': report['elapsed_seconds'], 'max_rss_kib': report['max_rss_kib']}, indent=2))


if __name__ == '__main__':
    main()
