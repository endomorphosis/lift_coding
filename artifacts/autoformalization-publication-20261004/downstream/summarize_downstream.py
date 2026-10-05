"""Audit pinned frozen downstream receipts and produce a scalar-only summary."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import stat
from collections import Counter
from pathlib import Path

SEEDS = (1729, 1730, 1731)
CONTROLS = ('raw_source', 'pca_reconstructed', 'new_ae_reconstructed',
            'zero_raw', 'disabled_raw', 'rotated_raw')
SPLITS = ('train', 'development')
MASKS = ('weak_decoder_fit', 'strong_semantic_fit', 'contrastive_supervision',
         'proof_supervision', 'fidelity_evaluation')
MAX_BYTES = 64 * 1024**2
OUTCOMES = {'source_blocked', 'clarification_required', 'source_encoding_unavailable',
            'decoder_abstained', 'decoder_unavailable', 'decoder_proposal'}
COUNTERS = ('optimizer_step_attempts', 'optimizer_updates', 'dimensional_restores',
            'embedded_parent_restores', 'model_constructors', 'wrapper_calls',
            'owner_decoder_calls', 'source_row_decode_calls', 'actual_model_forward_calls')


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def raw(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(raw(value)).hexdigest()


def closed(value, keys, reason):
    require(type(value) is dict and set(value) == set(keys), 'closed ' + reason + ' required')


def integer(value, lower=0, upper=None):
    require(type(value) is int and value >= lower and (upper is None or value <= upper),
            'bounded exact integer required')
    return value


def strict_json(data):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate JSON key')
            result[key] = value
        return result
    return json.loads(data.decode('utf-8'), object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))


def file_bytes(path):
    path = Path(path)
    require(path.is_absolute() and not any(p.is_symlink() for p in (path, *path.parents)),
            'absolute nonsymlink file required')
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(descriptor)
        require(stat.S_ISREG(before.st_mode) and 0 <= before.st_size <= MAX_BYTES,
                'bounded regular file required')
        with os.fdopen(descriptor, 'rb', closefd=False) as stream:
            data = stream.read(MAX_BYTES + 1)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) and
            len(data) == before.st_size, 'file changed during capture')
    return data


def binding(path):
    path = str(Path(path).absolute())
    data = file_bytes(path)
    return {'path': path, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


class Capture:
    def __init__(self):
        self.files = {}

    def get(self, reference):
        closed(reference, ('path', 'bytes', 'sha256'), 'external binding')
        integer(reference['bytes'], upper=MAX_BYTES)
        sha = reference['sha256']
        require(type(sha) is str and len(sha) == 64 and
                all(c in '0123456789abcdef' for c in sha), 'lowercase SHA256 required')
        path = reference['path']
        if path not in self.files:
            data = file_bytes(path)
            require(len(data) == reference['bytes'] and hashlib.sha256(data).hexdigest() == sha,
                    'external file binding differs')
            self.files[path] = (copy.deepcopy(reference), data)
        require(self.files[path][0] == reference, 'conflicting external file bindings')
        return self.files[path][1]

    def json(self, reference, sealed=True):
        value = strict_json(self.get(reference))
        require(type(value) is dict, 'JSON object required')
        if sealed:
            require(value.get('content_sha256') == digest({k: v for k, v in value.items()
                                                        if k != 'content_sha256'}), 'JSON seal differs')
        return value

    def recheck(self):
        for reference, data in self.files.values():
            require(file_bytes(reference['path']) == data, 'selected file changed during audit')


def receipt_scalars(record):
    require(record['schema'] == 'canonical-span-decoder-preflight-inference/v1',
            'existing wrapper receipt required')
    for key in ('target_access', 'teacher_forcing', 'training_executed', 'context_applied',
                'source_fidelity_established', 'qualified', 'proof_authority', 'accepted'):
        require(record[key] is False, 'receipt semantic or execution authority differs')
    rows = record['rows']
    require(type(rows) is list and len(rows) == integer(record['input_count']) == 32 and
            len({r['id'] for r in rows}) == 32 and
            [r['position'] for r in rows] == list(range(32)), 'all32 ordered request outcomes required')
    require(all(r['outcome'] in OUTCOMES for r in rows), 'unknown source outcome')
    backend_rows = [r['decoder_row'] for r in rows if r['decoder_row'] is not None]
    submitted = record['submitted_positions']
    require(type(submitted) is list and len(set(submitted)) == len(submitted) ==
            integer(record['eligible_count'], upper=32) and
            all(type(p) is int and 0 <= p < 32 for p in submitted), 'eligible positions differ')
    require([r['position'] for r in rows if r['submitted_position'] is not None] == submitted,
            'submitted row join differs')
    calls = integer(record['decoder_call_count'], upper=1)
    completions = integer(record['decoder_completion_count'], upper=1)
    require(calls == int(bool(submitted)) and completions <= calls and
            (len(backend_rows) == len(submitted) if completions else not backend_rows),
            'decoder completion accounting differs')
    require(record['backend_exception_type'] in (None, 'ImportError', 'OSError', 'RuntimeError'),
            'bounded exception category required')
    return {'requested_rows': 32,
            'preflight_outcomes': dict(Counter(r['preflight']['outcome'] for r in rows)),
            'source_outcomes': dict(Counter(r['outcome'] for r in rows)),
            'eligible_rows': len(submitted), 'decoder_calls': calls,
            'decoder_completions': completions, 'backend_exception_type': record['backend_exception_type'],
            'decoder_status_counts': dict(Counter(r['status'] for r in backend_rows)),
            'decoder_reason_counts': dict(Counter(r['reason'] for r in backend_rows if r['reason'] is not None)),
            'syntax_valid_unaccepted_proposals': sum(r['family_syntax_checked'] is True for r in backend_rows),
            'semantic_support_established': False, 'semantic_accuracy_measured': False,
            'accepted_artifacts': 0, 'proof_calls': 0}


def comparisons(baseline, candidate):
    require([r['id'] for r in baseline['rows']] == [r['id'] for r in candidate['rows']],
            'matched request identities required')
    changes = Counter()
    compared, maximum, total = 0, 0., 0.
    for left, right in zip(baseline['rows'], candidate['rows'], strict=True):
        changes['source_outcome'] += left['outcome'] != right['outcome']
        changes['preflight'] += raw(left['preflight']) != raw(right['preflight'])
        a, b = left['decoder_row'], right['decoder_row']
        changes['decoder_presence'] += (a is None) != (b is None)
        if a is None or b is None:
            continue
        for key in ('status', 'reason', 'canonical_ir'):
            changes[key] += raw(a[key]) != raw(b[key])
        changes['status_reason_ir'] += any(raw(a[k]) != raw(b[k])
                                          for k in ('status', 'reason', 'canonical_ir'))
        x = a.get('span_diagnostics', {}).get('modality_logits')
        y = b.get('span_diagnostics', {}).get('modality_logits')
        if x is not None and y is not None:
            require(type(x) is list and type(y) is list and len(x) == len(y) == 3 and
                    all(type(v) in (int, float) and math.isfinite(v) for v in x + y),
                    'finite three-logit comparison required')
            deltas = [abs(u - v) for u, v in zip(x, y, strict=True)]
            maximum = max(maximum, *deltas)
            total += math.fsum(deltas)
            compared += 1
    return {'requested_rows': len(baseline['rows']), 'changed_counts': dict(changes),
            'modality_logit_comparison_rows': compared,
            'max_abs_modality_logit_difference': maximum if compared else None,
            'mean_abs_modality_logit_difference': total / (3 * compared) if compared else None,
            'semantic_improvement_measured': False}


def stats(values):
    require(len(values) == 3 and all(v is None or type(v) in (int, float) and
                                   math.isfinite(v) for v in values), 'three finite seed outcomes required')
    observed = [v for v in values if v is not None]
    return {'seed_values': values, 'defined_seeds': len(observed),
            'mean': math.fsum(observed) / len(observed) if observed else None,
            'minimum': min(observed) if observed else None,
            'maximum': max(observed) if observed else None}


def grouped_counts(values):
    keys = sorted(set().union(*(set(v) for v in values)))
    return {key: stats([v.get(key, 0) for v in values]) for key in keys}


def validate_report(report, parent, selected, batch, capture):
    seed = selected['seed']
    require(type(seed) is int and seed in SEEDS and report['seed'] == parent['seed'] == seed,
            'selected seed joins differ')
    require(report['schema'] == 'source-only-frozen-downstream-span-report/v1' and
            report['status'] == 'completed' and
            parent['schema'] == 'source-only-frozen-downstream-worker-parent/v1' and
            parent['succeeded'] is True and parent['returncode'] == 0 and parent['failure'] is None and
            parent['selected_inputs_unchanged'] is True and parent['process_group_cleanup_attempted'] is True and
            parent['proof_or_semantic_qualification'] is False, 'completed preserved worker and parent required')
    require(parent['selected']['plan'] == report['plan_binding'] == batch['selected']['plan'] and
            parent['selected']['worker'] == report['helper_binding'] == batch['selected']['worker'],
            'parent/batch/report selected source joins differ')
    for key in ('model_state_unchanged', 'checkpoint_unchanged', 'restored_adam_unchanged',
                'global_cpu_rng_unchanged', 'context_contract_unchanged',
                'all64_requests_retained_per_control', 'native768_only', 'frozen_pca_ae_conditioners_reused'):
        require(report[key] is True, 'frozen model/input preservation required')
    for key in ('parameter_gradients_created', 'matched_8d_384d_decoder_experiments_executed',
                'teacher_forcing', 'target_access', 'semantic_accuracy_measured',
                'semantic_relevance_measured', 'source_fidelity_established', 'training_executed',
                'qualified', 'proof_authority', 'accepted', 'source_vector_tables_included',
                'compression_storage_or_latency_benefit_measured'):
        require(report[key] is False, 'target-free diagnostic scope differs')
    for key in ('new_pca_fits', 'new_ae_fits', 'new_encoder_calls', 'proof_calls'):
        require(integer(report[key]) == 0, 'inference-only counter differs')
    closed(report['masks'], MASKS, 'semantic masks')
    require(all(type(v) is int and v == 0 for v in report['masks'].values()), 'zero integer masks required')
    require(report['conditioner_width'] == 768 and
            report['control_transformation_scope'] == 'complete_within_split32_before_preflight',
            'native768 split-local control scope differs')
    for reference in report['preserved_input_bindings']:
        capture.get(reference)
    for key in ('checkpoint_binding', 'endpoints_binding', 'numeric_report_binding',
                'source_inputs_binding', 'cohort_binding', 'native_bundle_binding',
                'helper_binding', 'plan_binding'):
        capture.get(report[key])
    for key in ('stdout_binding', 'stderr_binding'):
        capture.get(parent[key])
    plan = capture.json(report['plan_binding'])
    require(plan['schema'] == 'source-only-frozen-downstream-span-plan/v1' and
            plan['controls'] == list(CONTROLS) and [a['seed'] for a in plan['arms']] == list(SEEDS) and
            plan['helper_binding'] == report['helper_binding'], 'fixed all-seed plan required')
    arm = next(a for a in plan['arms'] if a['seed'] == seed)
    require(all(arm[k] == report[k] for k in ('checkpoint_binding', 'endpoints_binding', 'numeric_report_binding')),
            'plan selected checkpoint/endpoints joins differ')
    require(plan['resource_limits'] == report['resources']['limits'] and
            parent['parent_wall_deadline_seconds'] == report['resources']['limits']['parent_wall_seconds'],
            'resource-limit joins differ')
    require(plan['source_inputs_binding'] == report['source_inputs_binding'] and
            plan['cohort_binding'] == report['cohort_binding'], 'plan source/cohort joins differ')
    inputs = capture.json(report['source_inputs_binding'])
    cohort = capture.json(report['cohort_binding'])
    require(inputs['schema'] == 'source-only-authored-expansion-inputs/v1' and
            cohort['schema'] == 'source-only-authored-expansion-cohort/v1' and
            inputs['contains_formal_targets'] is False and cohort['contains_formal_targets'] is False and
            len(inputs['rows']) == len(cohort['rows']) == 64 and
            inputs['policy'] == cohort['policy'] and
            inputs['policy']['semantic_label_admission'] is False,
            'original64 source-only cohort required')
    closed(inputs['policy']['semantic_masks'], MASKS, 'source-only masks')
    require(all(type(v) is int and v == 0 for v in inputs['policy']['semantic_masks'].values()),
            'original cohort masks must remain zero')
    expected = {}
    for split in SPLITS:
        source_rows = [r for r in inputs['rows'] if r['split'] == split]
        meta_rows = [r for r in cohort['rows'] if r['split'] == split]
        require(len(source_rows) == len(meta_rows) == 32 and
                [r['id'] for r in source_rows] == [r['id'] for r in meta_rows],
                'source/cohort split joins differ')
        expected[split] = source_rows
    require(set(report['arms']) == set(report['comparisons_against_raw']) == set(CONTROLS),
            'all six declared controls required')
    results, receipts = {}, {}
    for control in CONTROLS:
        require(set(report['arms'][control]) == set(report['comparisons_against_raw'][control]) == set(SPLITS),
                'both32-row splits required')
        results[control], receipts[control] = {}, {}
        for split in SPLITS:
            saved = report['arms'][control][split]
            record = capture.json(saved['receipt_binding'])
            scalar = receipt_scalars(record)
            require([r['id'] for r in record['rows']] == [r['id'] for r in expected[split]] and
                    all(r['source_sha256'] == source['source_sha256'] and
                        r['context_sha256'] == source['input']['context']['sha256']
                        for r, source in zip(record['rows'], expected[split], strict=True)),
                    'complete original source/context receipt joins differ')
            require(all(saved[k] == v and type(saved[k]) is type(v) for k, v in scalar.items()),
                    'saved receipt scalar recomputation differs')
            forwards = integer(saved['actual_model_forward_calls'], upper=scalar['eligible_rows'])
            require(saved['observed_owner_decoder_calls'] == scalar['decoder_calls'] and
                    saved['generation_executed'] is (forwards > 0), 'actual numerical call accounting differs')
            require(record['decoder_metadata']['input_dimension'] == 768 and
                    record['decoder_metadata']['model_state_sha256'] == report['model_state_sha256'],
                    'receipt selected model identity differs')
            if control != 'raw_source':
                require([r['preflight'] for r in record['rows']] ==
                        [r['preflight'] for r in receipts['raw_source'][split]['rows']],
                        'source-only preflight changes across views')
            compared = comparisons(record if control == 'raw_source' else receipts['raw_source'][split], record)
            require(raw(compared) == raw(report['comparisons_against_raw'][control][split]),
                    'raw-relative generated diagnostic recomputation differs')
            results[control][split] = {**scalar, 'actual_model_forward_calls': forwards,
                                      'generation_executed': forwards > 0, 'against_raw': compared}
            receipts[control][split] = record
    require(not ({r['id'] for r in receipts['raw_source']['train']['rows']} &
                 {r['id'] for r in receipts['raw_source']['development']['rows']}), 'split request IDs overlap')
    closed(report['counts'], COUNTERS, 'actual counters')
    counts = {k: integer(v) for k, v in report['counts'].items()}
    require(counts['optimizer_step_attempts'] == counts['optimizer_updates'] == 0 and
            counts['dimensional_restores'] == counts['embedded_parent_restores'] == 1 and
            counts['model_constructors'] == 3 and counts['wrapper_calls'] == 12 and
            counts['owner_decoder_calls'] == sum(v['decoder_calls'] for s in results.values() for v in s.values()) and
            counts['actual_model_forward_calls'] == sum(v['actual_model_forward_calls']
                                                        for s in results.values() for v in s.values()) and
            counts['source_row_decode_calls'] == sum(v['eligible_rows']
                                                      for s in results.values() for v in s.values()),
            'actual frozen counter sums differ')
    return {'seed': seed, 'report_binding': selected['report_binding'],
            'parent_binding': selected['parent_binding'], 'checkpoint_binding': report['checkpoint_binding'],
            'ae_checkpoint_binding': report['conditioner_profiles']['new_ae_reconstructed']['checkpoint_binding'],
            'arms': results, 'counts': counts, 'resources': report['resources'],
            'parent_wall_seconds': parent['wall_seconds']}


def summarize(selection_reference):
    capture = Capture()
    selection = capture.json(selection_reference)
    closed(selection, ('schema', 'reports', 'batch_binding', 'protocol_design_binding', 'content_sha256'),
           'summary selection')
    require(selection['schema'] == 'frozen-downstream-summary-selection/v1' and
            type(selection['reports']) is list and len(selection['reports']) == 3 and
            [r['seed'] for r in selection['reports']] == list(SEEDS), 'all three fixed seeds required')
    for selected in selection['reports']:
        closed(selected, ('seed', 'report_binding', 'parent_binding'), 'selected seed report')
    design = capture.json(selection['protocol_design_binding'], sealed=False)
    require(design['schema'] == 'frozen-downstream-source-representation-protocol-design/v1',
            'external protocol design required')
    batch = capture.json(selection['batch_binding'], sealed=False)
    require(batch['schema'] == 'source-only-frozen-downstream-batch/v1' and
            type(batch['successful_seeds']) is int and batch['successful_seeds'] == 3 and
            batch['selected_inputs_unchanged'] is True and batch['semantic_accuracy_measured'] is False and
            batch['qualified'] is False and batch['proof_authority'] is False and
            [r['seed'] for r in batch['seeds']] == list(SEEDS), 'complete three-seed batch required')
    for reference in batch['selected'].values():
        capture.get(reference)
    seed_results = []
    for selected, recorded in zip(selection['reports'], batch['seeds'], strict=True):
        require(recorded['succeeded'] is True and recorded['returncode'] == 0 and
                recorded['worker_report_binding'] == selected['report_binding'] and
                recorded['parent_report_binding'] == selected['parent_binding'], 'batch selected result joins differ')
        report = capture.json(selected['report_binding'])
        parent = capture.json(selected['parent_binding'], sealed=False)
        seed_results.append(validate_report(report, parent, selected, batch, capture))
    total_counts = {key: sum(r['counts'][key] for r in seed_results) for key in COUNTERS}
    require(batch['completed_worker_counts'] == total_counts, 'batch actual counter sums differ')
    grouped = {}
    for control in CONTROLS:
        grouped[control] = {}
        for split in SPLITS:
            values = [r['arms'][control][split] for r in seed_results]
            grouped[control][split] = {
                key: stats([v[key] for v in values]) for key in ('requested_rows', 'eligible_rows',
                    'decoder_calls', 'decoder_completions', 'syntax_valid_unaccepted_proposals',
                    'actual_model_forward_calls')}
            grouped[control][split].update({key: grouped_counts([v[key] for v in values])
                for key in ('preflight_outcomes', 'source_outcomes', 'decoder_status_counts', 'decoder_reason_counts')})
            compared = [v['against_raw'] for v in values]
            grouped[control][split]['against_raw'] = {
                'changed_counts': grouped_counts([v['changed_counts'] for v in compared]),
                **{key: stats([v[key] for v in compared]) for key in ('modality_logit_comparison_rows',
                        'max_abs_modality_logit_difference', 'mean_abs_modality_logit_difference')}}
    capture.recheck()
    return {'schema': 'source-only-frozen-downstream-summary/v1',
            'scope': 'exposed_authored_native768_frozen_decoder_conditioning_perturbation',
            'selection_binding': selection_reference, 'batch_binding': selection['batch_binding'],
            'protocol_design_binding': selection['protocol_design_binding'], 'seeds': list(SEEDS),
            'source_rows': 64, 'train_rows': 32, 'development_rows': 32,
            'selected_decoder_models': 3, 'views': list(CONTROLS), 'primary_view_seed_arms': 18,
            'split_receipts': 36, 'primary_request_outcomes': 1152, 'all_registered_seeds_reported': True,
            'development_winner_selected': False, 'seed_results': seed_results,
            'view_split_aggregates': grouped, 'actual_counters': total_counts,
            'verified_binding_count': len(capture.files), 'all_selected_bindings_preserved': True,
            'masks': dict.fromkeys(MASKS, 0), 'source_vector_tables_included': False,
            'generated_formula_bodies_included': False, 'formal_targets_read': False,
            'semantic_accuracy_measured': False, 'semantic_relevance_measured': False,
            'source_fidelity_established': False, 'proof_authority': False,
            'qualified': False, 'accepted': False,
            'limitations': [
                'The sources are exposed authored English legal fixtures, not natural sources or untouched confirmation evidence.',
                'PCA and AE reconstruction perturb a frozen raw-trained decoder; this is not a comparison of newly trained representation-conditioned decoders.',
                'Raw/PCA input representations are shared deterministic controls across the three seeded decoder models.',
                'AE and decoder seed indices are paired; AE-seed variance is coupled with decoder-seed variance.',
                'Output coverage, structural validity and changes in generated IR or logits do not measure legal or semantic accuracy.',
                'Decoder timing excludes upstream source encoding and PCA/AE production and does not establish compression savings.',
                'Only the compatible native768 decoder lane executes;8D and the current native GTE384 lane remain planned.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selection', type=Path, required=True)
    parser.add_argument('--selection-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    selected = binding(args.selection)
    require(selected['sha256'] == args.selection_sha256, 'externally pinned summary selection differs')
    value = summarize(selected)
    value['helper_binding'] = binding(__file__)
    value['content_sha256'] = digest(value)
    output = args.output.absolute()
    require(output.parent.is_dir() and not any(p.is_symlink() for p in (output, *output.parents)),
            'fresh nonsymlink output required')
    descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False,
                                allow_nan=False).encode('utf-8') + b'\n')
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({'summary_binding': binding(output), 'semantic_accuracy_measured': False}, sort_keys=True))


if __name__ == '__main__':
    main()
