"""Compare unchanged greedy decoding with bounded joint selection on one forward.

Captured native head scores feed a separate, explicitly approximate span policy.
No target, new model, optimizer update, semantic acceptance or proof is available.
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

FIELDS = ('actor', 'action', 'object', 'conditions', 'exceptions', 'temporal')
OPTIONAL = FIELDS[2:]
MODALITIES = ('O', 'P', 'F')
POLICY = {'candidates_per_facet': 16, 'beam_width': 64, 'ambiguity_epsilon': 1e-7,
          'modality_and_presence': 'unchanged_native_argmax_and_float32_margin',
          'span_pair_scores': 'float32_start_plus_end',
          'joint_objective': 'python_math_fsum_of_float32_pair_scores',
          'span_order': 'native_facet_order', 'optimality_scope': 'surviving_beam_only',
          'greedy_fallback': False, 'optional_facet_removal': False}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def f32(value):
    try:
        result = struct.unpack('f', struct.pack('f', value))[0]
    except (OverflowError, struct.error) as error:
        raise ValueError('float32 operation overflow') from error
    require(math.isfinite(result), 'finite float32 operation required')
    return result


def shape_scores(heads, count):
    """Validate detached native output shapes without invoking a model."""
    require(type(count) is int and 1 <= count <= 256, 'bounded positive token count required')
    require(type(heads) is dict and set(heads) == {'start', 'end', 'presence', 'modality'},
            'closed native head bank required')
    for name in ('start', 'end'):
        require(type(heads[name]) is list and len(heads[name]) == 6 and
                all(type(row) is list and len(row) == count for row in heads[name]), 'span head shape differs')
    require(type(heads['presence']) is list and len(heads['presence']) == 4 and
            all(type(row) is list and len(row) == 2 for row in heads['presence']) and
            type(heads['modality']) is list and len(heads['modality']) == 3, 'decision head shape differs')
    flat = [v for name in ('start', 'end', 'presence') for row in heads[name] for v in row] + heads['modality']
    require(all(type(v) in (int, float) and abs(v) <= 3.4028234663852886e38 and
                math.isfinite(v) and f32(v) == v for v in flat),
            'finite exact float32 head values required')


def fixed_decisions(heads):
    """Match native modality/presence choices and their float32 ambiguity gate."""
    scores = heads['modality']
    rank = sorted(range(3), key=lambda index: (-scores[index], index))
    margins = {'modality': f32(scores[rank[0]] - scores[rank[1]])}
    present = [True, True]
    for field, values in zip(OPTIONAL, heads['presence'], strict=True):
        margins[field] = abs(f32(values[1] - values[0]))
        present.append(values[1] > values[0])
    return {'modality': MODALITIES[rank[0]], 'present': present,
            'margins': margins, 'ambiguous': any(v <= 1e-7 for v in margins.values())}


def literal_rule(text, tokens, decisions, spans):
    """Bind every chosen interval to the exact source, checking global disjointness."""
    require(decisions['modality'] in MODALITIES and type(decisions['present']) is list and
            len(decisions['present']) == 6 and all(type(v) is bool for v in decisions['present']) and
            decisions['present'][:2] == [True, True], 'fixed native modality/required presence contract differs')
    require(type(spans) is list and len(spans) == 6, 'six facet selections required')
    rule = {'modality': decisions['modality']}
    facets, occupied = {}, set()
    for index, field in enumerate(FIELDS):
        present, interval = decisions['present'][index], spans[index]
        require((interval is not None) is present, 'fixed facet presence differs')
        atom = ''
        diagnostic = {'present': present, 'token_start': None, 'token_end_inclusive': None,
                      'char_start': None, 'char_end': None, 'text': None}
        if present:
            require(type(interval) is list and len(interval) == 2 and
                    all(type(v) is int for v in interval) and 0 <= interval[0] <= interval[1] < len(tokens),
                    'valid inclusive token interval required')
            left, right = interval
            positions = set(range(left, right + 1))
            require(not positions & occupied, 'joint selected spans overlap')
            occupied.update(positions)
            begin, end = tokens[left]['start'], tokens[right]['end']
            require(type(begin) is type(end) is int and 0 <= begin < end <= len(text), 'source character bounds differ')
            atom = text[begin:end]
            require(text[begin:tokens[left]['end']] == tokens[left]['text'] and
                    text[tokens[right]['start']:end] == tokens[right]['text'], 'literal token binding differs')
            diagnostic.update(token_start=left, token_end_inclusive=right, char_start=begin, char_end=end, text=atom)
        rule[field] = [atom] if present and field in ('conditions', 'exceptions', 'temporal') else \
                      [] if field in ('conditions', 'exceptions', 'temporal') else atom
        facets[field] = diagnostic
    return {'rules': [rule]}, facets


def load_selected(reference, expected_sha=None):
    path = Path(reference['path'])
    require(path.is_absolute() and not any(p.is_symlink() for p in (path, *path.parents)), 'selected canonical path required')
    data = path.read_bytes()
    require(len(data) == reference['bytes'] and hashlib.sha256(data).hexdigest() == reference['sha256'] and
            (expected_sha is None or reference['sha256'] == expected_sha), 'selected source differs')
    module = types.ModuleType('selected_' + path.stem)
    module.__file__ = str(path)
    exec(compile(data, str(path), 'exec'), module.__dict__)
    return module


def run(plan_path, plan_sha, seed, output):
    started = time.monotonic()
    before_usage = resource.getrusage(resource.RUSAGE_SELF)
    cpu_before = before_usage.ru_utime + before_usage.ru_stime
    require(sys.flags.isolated and sys.dont_write_bytecode, 'selected interpreter -I -B required')
    data = Path(plan_path).read_bytes()
    require(hashlib.sha256(data).hexdigest() == plan_sha, 'externally selected joint plan differs')
    preliminary = json.loads(data)
    helper = load_selected(preliminary['baseline_helper_binding'],
                           'b8d0c28006805585115aec4f236a6b14bdba6f43f82f9ec3e6cc64654925e475')
    capture = helper.Capture()
    plan_binding = helper.binding(plan_path)
    plan = capture.json(plan_binding)
    helper.closed(plan, ('schema', 'helper_binding', 'baseline_helper_binding', 'baseline_plan_binding',
                        'selector_binding', 'protocol_binding', 'baseline_raw_receipts', 'policy',
                        'resource_limits', 'semantic_masks', 'content_sha256'), 'joint plan')
    helper.seal_check(plan)
    require(plan['schema'] == 'source-only-joint-span-plan/v1' and plan['helper_binding'] == helper.binding(Path(__file__)) and
            plan['policy'] == POLICY and plan['resource_limits'] == helper.LIMITS and
            helper.raw(plan['semantic_masks']) == helper.raw(dict.fromkeys(helper.MASKS, 0)), 'fixed joint policy differs')
    capture.get(plan['helper_binding'])
    capture.get(plan['baseline_helper_binding'])
    selector = load_selected(plan['selector_binding'])
    capture.get(plan['selector_binding'])
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
    require(seed in helper.SEEDS and [r['seed'] for r in plan['baseline_raw_receipts']] == list(helper.SEEDS), 'fixed three seeds required')
    for item in plan['baseline_raw_receipts']:
        helper.closed(item, ('seed', 'train_binding', 'development_binding'), 'baseline raw receipt pair')
        for split in ('train', 'development'):
            capture.get(item[split + '_binding'])
    previous = next(r for r in plan['baseline_raw_receipts'] if r['seed'] == seed)
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
        captured.append({name: value.detach().tolist()[0] for name, value in result.items()} if finite else None)
        return result

    decoder.model.forward = capture_forward
    model_before = digest({k: v.detach().tolist() for k, v in decoder.model.state_dict().items()}, ascii=True)
    require(model_before == digest(checkpoint['model_state'], ascii=True), 'restored model differs')

    def optimizer_digest(model, optimizer):
        return digest(owner.span._pack(model, optimizer)[1], ascii=True)

    optimizer_before = [(role, optimizer_digest(model, optimizer)) for role, model, optimizer in restored_optimizers]
    require(len(optimizer_before) == 2 and optimizer_before[-1][1] == saved_optimizer_before, 'restored Adam differs')
    banks, results, baseline_summaries = [], [], {}
    for split in ('train', 'development'):
        panel, vectors, _ = helper.prepare_arm(rows, metadata, requests, 'raw_source', split)
        captured.clear()
        calls['wrapper_calls'] += 1
        with torch.inference_mode():
            record = wrapper.decode_with_preflight(decoder, panel, vectors, latent_ablation='none')
        wrapper.validate_preflight_decoding(record, panel, vectors)
        saved_baseline = capture.json(previous[split + '_binding'])
        require(helper.raw(record) == helper.raw(saved_baseline), 'unchanged greedy replay differs from saved baseline')
        require(record['eligible_count'] == len(panel) == len(captured) == 32 and
                record['backend_exception_type'] is None, 'all32 greedy forwards required')
        baseline_summaries[split] = {'receipt_binding': helper.write(output / ('greedy-' + split + '.json'), record),
                                    **helper.receipt_summary(record), 'exact_previous_receipt_match': True}
        for request, vector, native_row, heads in zip(panel, vectors, record['rows'], captured, strict=True):
            admission()
            require(native_row['id'] == request['id'] and native_row['latent_donor_id'] == request['id'] and
                    native_row['decoder_row']['latent_sha256'] == native_row['effective_latent_sha256'] ==
                    digest(vector, ascii=True), 'captured source/raw conditioner join differs')
            tokens = [{k: t[k] for k in ('text', 'start', 'end')} for t in owner.span.tokenize_source(request['source_text'])]
            require(heads is not None, 'finite native scores required for joint pilot')
            shape_scores(heads, len(tokens))
            decisions = fixed_decisions(heads)
            item = {'id': request['id'], 'seed': seed, 'control': 'raw_source', 'capture_index': len(banks),
                    'input_sha256': request['id'][7:], 'token_input_sha256': digest(tokens),
                    'request_sha256': native_row['request_sha256'], 'profile_sha256': helper.PROFILE_SHA,
                    'split': split, 'source_text': request['source_text'],
                    'source_sha256': native_row['source_sha256'],
                    'latent_sha256': native_row['decoder_row']['latent_sha256'], 'tokens': tokens, 'heads': heads}
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
                    ir, facets = literal_rule(request['source_text'], tokens, decisions, search['selected_spans'])
                    try:
                        owner.span.codec_module._rule(ir)
                    except ValueError as error:
                        joint.update(reason='joint_generated_ir_rejected', grammar_error=str(error))
                    else:
                        joint.update(status='proposal', reason=None, canonical_ir=ir, facets=facets,
                                     family_syntax_checked=True)
            results.append({'id': request['id'], 'split': split, 'source_sha256': item['source_sha256'],
                'latent_sha256': item['latent_sha256'], 'score_row_sha256': digest(item),
                'source_text': request['source_text'], 'greedy': copy.deepcopy(native_row['decoder_row']),
                'joint': joint, 'accepted': False, 'source_fidelity_established': False,
                'independent_semantic_review_completed': False, 'proof_authority': False})
    admission()
    require(calls['actual_model_forward_calls'] == calls['source_row_decode_calls'] == 64 and
            calls['wrapper_calls'] == calls['owner_decoder_calls'] == 2, 'single forward per source required')
    capture.recheck()
    require(model_before == digest({k: v.detach().tolist() for k, v in decoder.model.state_dict().items()}, ascii=True) and
            digest(checkpoint, ascii=True) == digest(decoder.checkpoint, ascii=True) == checkpoint_before, 'state changed')
    require(optimizer_before == [(role, optimizer_digest(model, optimizer)) for role, model, optimizer in restored_optimizers] and
            torch.equal(rng_before, torch.get_rng_state()) and calls['optimizer_step_attempts'] == 0 and
            all(p.grad is None for p in decoder.model.parameters()), 'Adam/RNG/gradient state changed')
    for reference in selected_providers.values():
        bootstrap['checked_bytes'](reference['path'], reference['sha256'], reference['bytes'])
    masks = dict.fromkeys(helper.MASKS, 0)
    score_binding = helper.write(output / 'score-bank.json', {'schema': 'source-only-frozen-span-score-bank/v1',
        'seed': seed, 'rows': banks, 'plan_binding': plan_binding, 'contains_formal_targets': False, 'semantic_masks': masks})
    ledger_binding = helper.write(output / 'proposal-ledger.json', {'schema': 'source-only-joint-span-proposal-ledger/v1',
        'seed': seed, 'rows': results, 'plan_binding': plan_binding, 'policy': POLICY, 'semantic_masks': masks,
        'semantic_accuracy_measured': False, 'accepted': False, 'qualified': False, 'proof_authority': False})
    report = {'schema': 'source-only-joint-span-report/v1', 'status': 'completed', 'seed': seed,
        'plan_binding': plan_binding, 'checkpoint_binding': arm['checkpoint_binding'],
        'preserved_input_bindings': capture.references(), 'selected_provider_entrypoints': selected_providers,
        'original_context_contract': context_contract, 'context_contract_unchanged': True,
        'model_state_sha256': model_before, 'saved_optimizer_state_sha256': saved_optimizer_before,
        'restored_optimizer_state_checksums': [{'role': role, 'sha256': checksum} for role, checksum in optimizer_before],
        'model_state_unchanged': True, 'checkpoint_unchanged': True, 'restored_adam_unchanged': True,
        'global_cpu_rng_unchanged': True, 'parameter_gradients_created': False,
        'baseline_summaries': baseline_summaries, 'score_bank_binding': score_binding, 'proposal_ledger_binding': ledger_binding,
        'counts': dict(calls), 'policy': POLICY, 'request_count': 64, 'all_requests_retained': True,
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
        'runtime_admission_scope': 'fail_closed_complete64_previously_preflighted_finite_score_cohort',
        'independent_greedy_and_joint_model_forwards': False, 'natural_sources': False, 'pristine_holdout': False,
        'dependency_scope': 'selected_entrypoints_and_captured_canonical_modules_not_complete_binary_closure',
        'os_sandbox': False, 'resources': {'limits': limits, 'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'elapsed_seconds': time.monotonic() - started,
            'cpu_seconds': resource.getrusage(resource.RUSAGE_SELF).ru_utime + resource.getrusage(resource.RUSAGE_SELF).ru_stime - cpu_before,
            'observation_scope': 'worker_before_final_report_serialization'}}
    report_binding = helper.write(output / 'joint-report.json', report)
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
