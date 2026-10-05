"""Frozen joint span selection across all six previously saved conditioners.

One unchanged native decoder forward supplies greedy and bounded joint outputs.
This source-only intervention reads no formal targets and establishes no fidelity.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib
import json
import math
import os
import resource
import struct
import sys
import time
import types
from collections import Counter
from pathlib import Path

BASELINE_HELPER_SHA = 'b8d0c28006805585115aec4f236a6b14bdba6f43f82f9ec3e6cc64654925e475'
FROZEN_JOINT_HELPER_SHA = 'c589e45f501b500ad86f88b04b56c83df5445e6aa578c90fa9925cbc64395a3e'
SUMMARY_BASELINE_HELPER_SHA = 'eb914ea45be5c463b3523fcd547dbfb8eac8fb1bb19f978e8270fb95e6ac9896'
SELECTOR_SHA = 'b926b0ab29f02c3eeed020b1c261151e83d073dbd4edf90ba63e9e9dee659afa'
CONTROLS = ('raw_source', 'pca_reconstructed', 'new_ae_reconstructed',
            'zero_raw', 'disabled_raw', 'rotated_raw')
SEEDS = (1729, 1730, 1731)
SPLITS = ('train', 'development')
PLAN_KEYS = ('schema', 'helper_binding', 'baseline_helper_binding', 'baseline_plan_binding',
             'frozen_joint_helper_binding', 'selector_binding', 'protocol_binding',
             'summary_baseline_helper_binding', 'baseline_receipts', 'baseline_joint_ledgers',
             'controls', 'policy', 'resource_limits', 'semantic_masks', 'content_sha256')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_selected(reference, expected_sha=None):
    path = Path(reference['path'])
    require(path.is_absolute() and not any(p.is_symlink() for p in (path, *path.parents)),
            'selected canonical path required')
    data = path.read_bytes()
    require(len(data) == reference['bytes'] and hashlib.sha256(data).hexdigest() == reference['sha256'] and
            (expected_sha is None or reference['sha256'] == expected_sha), 'selected source differs')
    module = types.ModuleType('selected_' + path.stem)
    module.__file__ = str(path)
    exec(compile(data, str(path), 'exec'), module.__dict__)
    return module


def validate_plan(plan, helper, frozen, self_binding):
    helper.closed(plan, PLAN_KEYS, 'joint conditioning plan')
    helper.seal_check(plan)
    require(plan['schema'] == 'source-only-joint-conditioning-plan/v1' and
            plan['helper_binding'] == self_binding and
            plan['baseline_helper_binding']['sha256'] == BASELINE_HELPER_SHA and
            plan['frozen_joint_helper_binding']['sha256'] == FROZEN_JOINT_HELPER_SHA and
            plan['selector_binding']['sha256'] == SELECTOR_SHA and
            plan['summary_baseline_helper_binding']['sha256'] == SUMMARY_BASELINE_HELPER_SHA and
            helper.raw(plan['controls']) == helper.raw(list(CONTROLS)) and
            plan['policy'] == frozen.POLICY and plan['resource_limits'] == helper.LIMITS and
            helper.raw(plan['semantic_masks']) == helper.raw(dict.fromkeys(helper.MASKS, 0)),
            'fixed six-condition source-only joint policy differs')
    for name in ('baseline_receipts', 'baseline_joint_ledgers'):
        require(type(plan[name]) is list and len(plan[name]) == 3 and
                [row.get('seed') for row in plan[name]] == list(SEEDS), 'fixed three seeds required')
    for row in plan['baseline_receipts']:
        helper.closed(row, ('seed', 'arms'), 'six-condition baseline')
        helper.closed(row['arms'], CONTROLS, 'six-condition receipt arms')
        for pair in row['arms'].values():
            helper.closed(pair, ('train_binding', 'development_binding'), 'receipt split pair')
    for row in plan['baseline_joint_ledgers']:
        helper.closed(row, ('seed', 'ledger_binding'), 'previous raw joint ledger')


def conditioner_profiles(endpoints, profile_sha):
    return {
        'raw_source': {'kind': 'original_pinned_native_source', 'source_profile_sha256': profile_sha},
        'pca_reconstructed': {'kind': 'out_of_distribution_frozen_pca_inverse_perturbation',
                              'original_producer_receipt_claimed': False, 'pca_control': endpoints['pca_control']},
        'new_ae_reconstructed': {'kind': 'out_of_distribution_frozen_ae_reconstruction_perturbation',
                                 'original_producer_receipt_claimed': False,
                                 'checkpoint_binding': endpoints['new_checkpoint_binding']},
        'zero_raw': {'kind': 'zero_vector_ablation', 'original_producer_receipt_claimed': False},
        'disabled_raw': {'kind': 'original_raw_vector_gate_disabled', 'latent_input_enabled': False},
        'rotated_raw': {'kind': 'within_split32_one_position_rotation_before_preflight',
                        'original_matched_source_producer_receipt_claimed': False}}


def conditioner_joins(panel, vectors, record, control, digest, profile):
    """Independently join complete split-local interventions to wrapper receipts.

    A rotated recipient retains its own original hash while its effective hash
    belongs to the successor donor. Disabled conditioning retains the raw vector
    with the gate off. No source is filtered before those transformations.
    """
    require(control in CONTROLS and len(panel) == len(vectors) == 32 and
            len(record['rows']) == 32 and record['eligible_count'] == 32 and
            record['submitted_positions'] == list(range(32)) and
            record['backend_exception_type'] is None, 'complete split32 eligibility required')
    require(len({request['id'] for request in panel}) == 32, 'unique complete split32 identities required')
    ablation = {'zero_raw': 'zero', 'disabled_raw': 'disabled', 'rotated_raw': 'rotate'}.get(control, 'none')
    require(record['requested_control'] == ablation and
            record['owner_control'] == ('disabled' if control == 'disabled_raw' else 'none'),
            'wrapper intervention control differs')
    require(all(type(v) is list and len(v) == 768 and
                all(type(x) in (int, float) and abs(x) <= 3.4028234e38 and math.isfinite(x) for x in v)
                for v in vectors), 'finite native768 original vectors required')
    effective = [[0.0] * 768 for _ in vectors] if control == 'zero_raw' else copy.deepcopy(vectors)
    donors = list(range(32))
    if control == 'rotated_raw':
        effective = effective[1:] + effective[:1]
        donors = donors[1:] + donors[:1]
    joined = []
    for position, (request, original, vector, native_row) in enumerate(
            zip(panel, vectors, effective, record['rows'], strict=True)):
        expected = {'original_latent_sha256': digest(original, ascii=True),
                    'effective_latent_sha256': digest(vector, ascii=True),
                    'latent_donor_id': panel[donors[position]]['id'],
                    'latent_donor_position': donors[position],
                    'latent_input_enabled': control != 'disabled_raw'}
        require(native_row['id'] == request['id'] and native_row['position'] == position and
                native_row['submitted_position'] == position and
                native_row['preflight']['outcome'] == 'unassessed' and
                native_row['encoding']['outcome'] == 'admitted' and
                all(native_row[key] == value for key, value in expected.items()),
                'complete source/effective conditioner/donor/gate join differs')
        decoder_row = native_row['decoder_row']
        require(type(decoder_row) is dict and decoder_row['latent_sha256'] == expected['effective_latent_sha256'] and
                decoder_row['latent_input_enabled'] is expected['latent_input_enabled'],
                'native decoder effective conditioning differs')
        float32_vector = [struct.unpack('f', struct.pack('f', x))[0] for x in vector]
        joined.append({**expected, 'latent_sha256': expected['effective_latent_sha256'],
                       'latent_ablation': ablation, 'conditioning_profile': copy.deepcopy(profile),
                       'model_latent_float32_sha256': digest(float32_vector, ascii=True),
                       'control_transformation_scope': 'complete_within_split32_before_preflight'})
    return joined


def validate_joint_counters(calls, banks, results):
    """Retain every outcome while counting search only after fixed decisions.

    The native greedy decoder may return on an early span overlap before it
    checks a later presence head. Complete finite heads therefore do not imply
    that all fixed modality and presence decisions pass the ambiguity gate.
    """
    require(calls['actual_model_forward_calls'] == calls['source_row_decode_calls'] == 384 and
            calls['wrapper_calls'] == calls['owner_decoder_calls'] == 12 and
            len(results) == len(banks) == 384 and calls['joint_additional_model_forward_calls'] == 0,
            'one native forward and retained joint outcome per source/control required')
    searched = sum(row['joint']['search'] is not None for row in results)
    ambiguous = sum(row['joint']['reason'] == 'ambiguous_fixed_decision_scores' for row in results)
    require(0 <= calls['joint_selection_calls'] <= 384 and
            calls['joint_selection_calls'] == searched and 384 - searched == ambiguous,
            'actual joint search calls must exclude retained fixed-decision ambiguity outcomes')
    return ambiguous


def previous_joint_rows(ledger, seed):
    require(ledger['schema'] == 'source-only-joint-span-proposal-ledger/v1' and
            ledger['seed'] == seed and len(ledger['rows']) == 64 and
            ledger['semantic_accuracy_measured'] is False and ledger['accepted'] is False and
            ledger['qualified'] is False and ledger['proof_authority'] is False,
            'previous raw joint structural-only ledger required')
    result = {}
    for row in ledger['rows']:
        key = (row['split'], row['id'])
        require(row['split'] in SPLITS and key not in result and
                all(row[field] is False for field in ('accepted', 'source_fidelity_established',
                    'independent_semantic_review_completed', 'proof_authority')),
                'unique previous raw joint outcome joins required')
        result[key] = copy.deepcopy(row)
    require(Counter(key[0] for key in result) == Counter(train=32, development=32) and
            len({key[1] for key in result}) == 64,
            'complete previous raw joint split32 panels required')
    return result


def match_previous_raw_joint(previous, result, digest):
    fields = ('id', 'split', 'source_sha256', 'latent_sha256', 'source_text', 'greedy', 'joint',
              'accepted', 'source_fidelity_established', 'independent_semantic_review_completed', 'proof_authority')
    require(digest({key: previous[key] for key in fields}) == digest({key: result[key] for key in fields}),
            'unchanged raw greedy/joint outcome differs from previous joint trial')


def run(plan_path, plan_sha, seed, output):
    started = time.monotonic()
    before_usage = resource.getrusage(resource.RUSAGE_SELF)
    cpu_before = before_usage.ru_utime + before_usage.ru_stime
    require(sys.flags.isolated and sys.dont_write_bytecode, 'selected interpreter -I -B required')
    data = Path(plan_path).read_bytes()
    require(hashlib.sha256(data).hexdigest() == plan_sha, 'externally selected joint plan differs')
    preliminary = json.loads(data)
    helper = load_selected(preliminary['baseline_helper_binding'], BASELINE_HELPER_SHA)
    frozen = load_selected(preliminary['frozen_joint_helper_binding'], FROZEN_JOINT_HELPER_SHA)
    capture = helper.Capture()
    plan_binding = helper.binding(plan_path)
    plan = capture.json(plan_binding)
    validate_plan(plan, helper, frozen, helper.binding(Path(__file__)))
    for key in ('helper_binding', 'baseline_helper_binding', 'frozen_joint_helper_binding',
                'selector_binding', 'summary_baseline_helper_binding'):
        capture.get(plan[key])
    selector = load_selected(plan['selector_binding'], SELECTOR_SHA)
    helper.seal_check(capture.json(plan['protocol_binding']))
    require(not any(name in sys.modules for name in ('torch', 'safetensors')), 'numerical providers imported before capture')
    for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
        require(os.environ.get(name) == '1', 'one thread required')
    require(os.environ.get('CUDA_VISIBLE_DEVICES') == '' and
            os.environ.get('HF_HUB_OFFLINE') == os.environ.get('TRANSFORMERS_OFFLINE') == '1', 'offline CPU required')
    limits = helper.LIMITS
    resource.setrlimit(resource.RLIMIT_AS, (limits['address_space_bytes'], limits['address_space_bytes']))
    resource.setrlimit(resource.RLIMIT_CPU, (limits['cpu_seconds_soft'], limits['cpu_seconds_hard']))
    resource.setrlimit(resource.RLIMIT_FSIZE, (helper.MAX_BYTES, helper.MAX_BYTES))
    base = capture.json(plan['baseline_plan_binding'])
    helper.validate_plan(base, plan['baseline_helper_binding'])
    require(seed in helper.SEEDS, 'fixed decoder seed required')
    for item in plan['baseline_receipts']:
        for pair in item['arms'].values():
            for split in SPLITS:
                capture.get(pair[split + '_binding'])
    for item in plan['baseline_joint_ledgers']:
        capture.get(item['ledger_binding'])
    previous = next(r for r in plan['baseline_receipts'] if r['seed'] == seed)
    old_joint_binding = next(r['ledger_binding'] for r in plan['baseline_joint_ledgers'] if r['seed'] == seed)
    old_joint_ledger = capture.json(old_joint_binding)
    helper.seal_check(old_joint_ledger)
    require(helper.raw(old_joint_ledger['semantic_masks']) == helper.raw(dict.fromkeys(helper.MASKS, 0)),
            'previous raw joint masks must remain integer zero')
    old_joint_rows = previous_joint_rows(old_joint_ledger, seed)
    bootstrap_data = capture.get(base['bootstrap_binding'])
    sources = {item['module']: (item['binding'], capture.get(item['binding'])) for item in base['canonical_module_bindings']}
    inputs, cohort = capture.json(base['source_inputs_binding']), capture.json(base['cohort_binding'])
    requests, metadata = helper.validate_sources(inputs, cohort)
    encoding = capture.json(base['encoding_report_binding'])
    helper.seal_check(encoding)
    require(encoding['source_inputs_binding'] == base['source_inputs_binding'] and
            encoding['cohort_metadata_binding'] == base['cohort_binding'] and
            helper.raw(encoding['masks']) == helper.raw(dict.fromkeys(helper.MASKS, 0)), 'source native joins differ')
    native_binding = encoding['artifacts']['native768']['full_bundle']
    native_vectors, profile = helper.validate_native(capture.json(native_binding), inputs, encoding)
    for arm in base['arms']:
        for key in ('checkpoint_binding', 'endpoints_binding', 'numeric_report_binding'):
            capture.get(arm[key])
    arm = next(a for a in base['arms'] if a['seed'] == seed)
    endpoints, numeric = capture.json(arm['endpoints_binding']), capture.json(arm['numeric_report_binding'])
    rows = helper.validate_endpoints(endpoints, numeric, arm, metadata, native_vectors)
    for key in ('native_train_bundle_binding', 'native_development_bundle_binding'):
        capture.get(endpoints[key])
    profiles = conditioner_profiles(endpoints, helper.PROFILE_SHA)
    checkpoint = capture.json(arm['checkpoint_binding'])
    context_contract = helper.validate_checkpoint_source(checkpoint, seed, sources, profile)
    digest = helper.digest
    checkpoint_before = digest(checkpoint, ascii=True)
    saved_optimizer_before = digest(checkpoint['optimizer_state'], ascii=True)
    output = Path(output)
    require(output.is_absolute() and not output.exists() and output.parent.is_dir() and
            not any(p.is_symlink() for p in output.parents), 'fresh canonical output required')
    output.mkdir(mode=0o700)
    bootstrap = {'__name__': 'selected_native_bootstrap', '__file__': base['bootstrap_binding']['path']}
    exec(compile(bootstrap_data, base['bootstrap_binding']['path'], 'exec'), bootstrap)
    selected_providers = bootstrap['select_native_site']()
    helper.install_sources(sources)
    owner = importlib.import_module(helper.OPTIMIZER + 'legal_span_dimensions')
    wrapper = importlib.import_module(helper.LEGAL + 'canonical_span_decoder')
    import torch
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.set_default_dtype(torch.float32)
    torch.set_default_device('cpu')
    rng_before = torch.get_rng_state().clone()
    calls = Counter(optimizer_step_attempts=0, optimizer_updates=0, dimensional_restores=0,
                    embedded_parent_restores=0, model_constructors=0, wrapper_calls=0,
                    owner_decoder_calls=0, source_row_decode_calls=0, actual_model_forward_calls=0,
                    joint_selection_calls=0, joint_additional_model_forward_calls=0)

    def admission():
        require(time.monotonic() - started < limits['cooperative_seconds'], 'soft wall budget exceeded')
        require(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss < limits['cooperative_rss_kib'], 'soft RSS exceeded')

    def forbid_step(*_args, **_kwargs):
        calls['optimizer_step_attempts'] += 1
        raise RuntimeError('optimizer updates forbidden in frozen joint span evaluation')

    def counted(original, name):
        def invoke(*args, **kwargs):
            admission()
            calls[name] += 1
            return original(*args, **kwargs)
        return invoke

    torch.optim.Adam.step = forbid_step
    restored_optimizers = []
    parent_restore, dimensional_restore = owner.span._restore, owner._restore

    def restore_parent(*args, **kwargs):
        calls['embedded_parent_restores'] += 1
        value = parent_restore(*args, **kwargs)
        restored_optimizers.append(('embedded_source_parent', value[1], value[2]))
        return value

    def restore_dimensional(*args, **kwargs):
        calls['dimensional_restores'] += 1
        value = dimensional_restore(*args, **kwargs)
        restored_optimizers.append(('retained_dimensional_decoder', value[1], value[2]))
        return value

    owner.span._restore, owner._restore = restore_parent, restore_dimensional
    owner.span._model = counted(owner.span._model, 'model_constructors')
    decoder = owner.DimensionalSpanDecoder(checkpoint)
    require(calls['dimensional_restores'] == calls['embedded_parent_restores'] == 1 and
            calls['model_constructors'] == 3, 'unexpected restoration counts')
    require(all(p.device.type == 'cpu' and p.dtype == torch.float32 for p in decoder.model.parameters()), 'CPU float32 required')
    decoder.decode_formal_logic = counted(decoder.decode_formal_logic, 'owner_decoder_calls')
    decoder._decode = counted(decoder._decode, 'source_row_decode_calls')
    native_forward = decoder.model.forward
    captured = []

    def capture_forward(*args, **kwargs):
        admission()
        calls['actual_model_forward_calls'] += 1
        result = native_forward(*args, **kwargs)
        finite = all(bool(torch.isfinite(value).all()) for value in result.values())
        require(len(args) == 4 and set(kwargs) == {'enabled'} and type(kwargs['enabled']) is bool,
                'native model positional conditioner/gate contract differs')
        captured.append({'heads': {name: value.detach().tolist()[0] for name, value in result.items()} if finite else None,
                         'model_latent_float32_sha256': digest(args[3].detach().tolist()[0], ascii=True),
                         'enabled': kwargs['enabled']})
        return result

    decoder.model.forward = capture_forward
    model_before = digest({k: v.detach().tolist() for k, v in decoder.model.state_dict().items()}, ascii=True)
    require(model_before == digest(checkpoint['model_state'], ascii=True), 'restored model differs')

    def optimizer_digest(model, optimizer):
        return digest(owner.span._pack(model, optimizer)[1], ascii=True)

    optimizer_before = [(role, optimizer_digest(model, optimizer)) for role, model, optimizer in restored_optimizers]
    require(len(optimizer_before) == 2 and optimizer_before[-1][1] == saved_optimizer_before, 'restored Adam differs')
    banks, results, baseline_summaries = [], [], {}
    for control in CONTROLS:
        baseline_summaries[control] = {}
        for split in SPLITS:
            admission()
            panel, vectors, owner_control = helper.prepare_arm(rows, metadata, requests, control, split)
            captured.clear()
            calls['wrapper_calls'] += 1
            with torch.inference_mode():
                record = wrapper.decode_with_preflight(decoder, panel, vectors, latent_ablation=owner_control)
            wrapper.validate_preflight_decoding(record, panel, vectors)
            previous_binding = previous['arms'][control][split + '_binding']
            saved_baseline = capture.json(previous_binding)
            require(helper.raw(record) == helper.raw(saved_baseline), 'unchanged greedy replay differs from saved baseline')
            require(len(captured) == 32, 'all32 greedy forwards required')
            joins = conditioner_joins(panel, vectors, record, control, digest, profiles[control])
            baseline_summaries[control][split] = {
                'receipt_binding': helper.write(output / (control + '-' + split + '.json'), record),
                'previous_receipt_binding': previous_binding,
                **helper.receipt_summary(record), 'actual_model_forward_calls': 32,
                'observed_owner_decoder_calls': 1, 'exact_previous_receipt_match': True}
            for request, native_row, captured_row, conditioning in zip(panel, record['rows'], captured, joins, strict=True):
                admission()
                heads = captured_row['heads']
                require(heads is not None and
                        captured_row['model_latent_float32_sha256'] == conditioning['model_latent_float32_sha256'] and
                        captured_row['enabled'] is conditioning['latent_input_enabled'],
                        'finite captured native scores/model conditioner/gate required')
                tokens = [{k: t[k] for k in ('text', 'start', 'end')}
                          for t in owner.span.tokenize_source(request['source_text'])]
                frozen.shape_scores(heads, len(tokens))
                decisions = frozen.fixed_decisions(heads)
                item = {'id': request['id'], 'seed': seed, 'control': control, 'capture_index': len(banks),
                        'input_sha256': request['id'][7:], 'token_input_sha256': digest(tokens),
                        'request_sha256': native_row['request_sha256'], 'profile_sha256': helper.PROFILE_SHA,
                        'source_profile_sha256': helper.PROFILE_SHA,
                        'split': split, 'source_text': request['source_text'],
                        'source_sha256': native_row['source_sha256'], **conditioning, 'tokens': tokens, 'heads': heads}
                banks.append(item)
                joint = {'status': 'abstained', 'reason': 'ambiguous_fixed_decision_scores',
                         'canonical_ir': None, 'facets': None, 'search': None, 'fixed_decisions': decisions,
                         'family_syntax_checked': False}
                if not decisions['ambiguous']:
                    calls['joint_selection_calls'] += 1
                    search = selector.select_joint_spans(heads['start'], heads['end'], decisions['present'],
                        candidates_per_facet=16, beam_width=64, ambiguity_epsilon=1e-7)
                    joint.update(reason=search['reason'], search=search)
                    if search['status'] == 'selected':
                        ir, facets = frozen.literal_rule(request['source_text'], tokens, decisions, search['selected_spans'])
                        try:
                            owner.span.codec_module._rule(ir)
                        except ValueError as error:
                            joint.update(reason='joint_generated_ir_rejected', grammar_error=str(error))
                        else:
                            joint.update(status='proposal', reason=None, canonical_ir=ir, facets=facets,
                                         family_syntax_checked=True)
                result = {'id': request['id'], 'seed': seed, 'control': control, 'split': split,
                          'source_sha256': item['source_sha256'], **conditioning,
                          'score_row_sha256': digest(item), 'source_text': request['source_text'],
                          'greedy': copy.deepcopy(native_row['decoder_row']), 'joint': joint, 'accepted': False,
                          'source_fidelity_established': False, 'independent_semantic_review_completed': False,
                          'proof_authority': False}
                if control == 'raw_source':
                    match_previous_raw_joint(old_joint_rows[(split, request['id'])], result, digest)
                results.append(result)
    admission()
    ambiguous_rows = validate_joint_counters(calls, banks, results)
    capture.recheck()
    require(model_before == digest({k: v.detach().tolist() for k, v in decoder.model.state_dict().items()}, ascii=True) and
            digest(checkpoint, ascii=True) == digest(decoder.checkpoint, ascii=True) == checkpoint_before, 'state changed')
    require(optimizer_before == [(role, optimizer_digest(model, optimizer)) for role, model, optimizer in restored_optimizers] and
            torch.equal(rng_before, torch.get_rng_state()) and calls['optimizer_step_attempts'] == 0 and
            all(p.grad is None for p in decoder.model.parameters()), 'Adam/RNG/gradient state changed')
    for reference in selected_providers.values():
        bootstrap['checked_bytes'](reference['path'], reference['sha256'], reference['bytes'])
    masks = dict.fromkeys(helper.MASKS, 0)
    score_binding = helper.write(output / 'score-bank.json', {'schema': 'source-only-joint-conditioning-score-bank/v1',
        'seed': seed, 'rows': banks, 'plan_binding': plan_binding, 'contains_formal_targets': False, 'semantic_masks': masks})
    ledger_binding = helper.write(output / 'proposal-ledger.json', {'schema': 'source-only-joint-conditioning-proposal-ledger/v1',
        'seed': seed, 'rows': results, 'plan_binding': plan_binding, 'policy': frozen.POLICY, 'semantic_masks': masks,
        'semantic_accuracy_measured': False, 'accepted': False, 'qualified': False, 'proof_authority': False})
    report = {'schema': 'source-only-joint-conditioning-report/v1', 'status': 'completed', 'seed': seed,
        'plan_binding': plan_binding, 'checkpoint_binding': arm['checkpoint_binding'],
        'preserved_input_bindings': capture.references(), 'selected_provider_entrypoints': selected_providers,
        'original_context_contract': context_contract, 'context_contract_unchanged': True,
        'model_state_sha256': model_before, 'saved_optimizer_state_sha256': saved_optimizer_before,
        'restored_optimizer_state_checksums': [{'role': role, 'sha256': checksum} for role, checksum in optimizer_before],
        'model_state_unchanged': True, 'checkpoint_unchanged': True, 'restored_adam_unchanged': True,
        'global_cpu_rng_unchanged': True, 'parameter_gradients_created': False,
        'baseline_summaries': baseline_summaries, 'score_bank_binding': score_binding, 'proposal_ledger_binding': ledger_binding,
        'counts': dict(calls), 'policy': frozen.POLICY, 'request_count': 64, 'all_requests_retained': True,
        'conditioner_profiles': profiles, 'controls': list(CONTROLS), 'conditioning_source_occurrences': 384,
        'total_greedy_joint_outcomes': 768, 'ambiguous_fixed_decision_rows': ambiguous_rows,
        'joint_selection_call_scope': 'unambiguous_fixed_modality_and_presence_only',
        'previous_raw_joint_ledger_binding': old_joint_binding,
        'previous_raw_joint_exact_match': True, 'previous_raw_joint_rows_compared': 64,
        'all36_previous_greedy_receipts_captured_before_ml': True, 'exact_previous_greedy_receipts_matched': 12,
        'control_transformation_scope': 'complete_within_split32_before_preflight',
        'conditioner_width': 768, 'compression_storage_or_latency_benefit_measured': False,
        'frozen_pca_ae_conditioners_reused': True, 'new_pca_fits': 0, 'new_ae_fits': 0,
        'greedy_proposals': sum(r['greedy']['status'] == 'decoded' for r in results),
        'joint_proposals': sum(r['joint']['status'] == 'proposal' for r in results),
        'joint_reason_counts': dict(Counter(r['joint']['reason'] for r in results if r['joint']['reason'] is not None)),
        'transition_counts': dict(Counter(r['greedy']['status'] + '->' + r['joint']['status'] for r in results)),
        'search_incomplete_rows': sum(r['joint']['search'] is not None and
                                      r['joint']['search']['diagnostics']['incomplete_search'] for r in results),
        'masks': masks, 'formal_targets_read': False, 'new_encoder_calls': 0, 'new_model_fits': 0,
        'training_executed': False, 'semantic_accuracy_measured': False, 'source_fidelity_established': False,
        'qualified': False, 'accepted': False, 'proof_authority': False, 'proof_calls': 0,
        'native768_only': True, 'greedy_profile_unchanged': True, 'joint_profile': 'separate_bounded_joint_span_intervention/v1',
        'runtime_admission_scope': 'fail_closed_complete64_per_each_of6_controls_previously_preflighted_finite_score_cohort',
        'independent_greedy_and_joint_model_forwards': False, 'natural_sources': False, 'pristine_holdout': False,
        'dependency_scope': 'selected_entrypoints_and_captured_canonical_modules_not_complete_binary_closure',
        'os_sandbox': False, 'resources': {'limits': limits, 'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'elapsed_seconds': time.monotonic() - started,
            'cpu_seconds': resource.getrusage(resource.RUSAGE_SELF).ru_utime + resource.getrusage(resource.RUSAGE_SELF).ru_stime - cpu_before,
            'observation_scope': 'worker_before_final_report_serialization'}}
    report_binding = helper.write(output / 'joint-conditioning-report.json', report)
    print(json.dumps({'status': 'completed', 'seed': seed, 'report_binding': report_binding,
                      'greedy_proposals': report['greedy_proposals'], 'joint_proposals': report['joint_proposals'],
                      'counts': dict(calls)}, sort_keys=True), flush=True)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--plan-sha256', required=True)
    parser.add_argument('--seed', type=int, choices=(1729, 1730, 1731), required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    return run(args.plan, args.plan_sha256, args.seed, args.output)


if __name__ == '__main__':
    raise SystemExit(main())
