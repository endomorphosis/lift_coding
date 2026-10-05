"""Summarize bound frozen conditioning interventions with no model execution.

The selected previous pure summary supplies capture, seal, literal transport
and structural counts. Native head arrays are read only for scalar diagnostic
differences and are excluded from the three public ledgers. Independent replay
must audit head selection and grammar separately.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import re
import sys
import types
from collections import Counter
from pathlib import Path

SEEDS = (1729, 1730, 1731)
CONTROLS = ('raw_source', 'pca_reconstructed', 'new_ae_reconstructed',
            'zero_raw', 'disabled_raw', 'rotated_raw')
SPLITS = ('train', 'development')
FIELDS = ('actor', 'action', 'object', 'conditions', 'exceptions', 'temporal')
MASKS = ('weak_decoder_fit', 'strong_semantic_fit', 'contrastive_supervision',
         'proof_supervision', 'fidelity_evaluation')
OLD_SUMMARY_SHA = 'eb914ea45be5c463b3523fcd547dbfb8eac8fb1bb19f978e8270fb95e6ac9896'
PLAN_KEYS = ('schema', 'helper_binding', 'baseline_helper_binding', 'baseline_plan_binding',
             'frozen_joint_helper_binding', 'summary_baseline_helper_binding', 'selector_binding',
             'protocol_binding', 'baseline_receipts', 'baseline_joint_ledgers', 'controls', 'policy',
             'resource_limits', 'semantic_masks', 'content_sha256')
CHANGE_KEYS = tuple(policy + '_' + key for policy in ('greedy', 'joint')
                    for key in ('status', 'reason', 'canonical_ir', 'status_reason_ir')) + (
    'fixed_modality', 'fixed_presence', 'fixed_ambiguity', 'greedy_facet_intervals',
    'joint_selected_spans', 'joint_search_presence', 'joint_search_status_reason',
    'joint_search_pruning_diagnostics', 'joint_search_full_diagnostics')
RAW_JOIN_FIELDS = ('id', 'split', 'source_sha256', 'latent_sha256', 'source_text', 'greedy', 'joint',
                   'accepted', 'source_fidelity_established', 'independent_semantic_review_completed', 'proof_authority')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_selected_summary(reference):
    require(type(reference) is dict and set(reference) == {'path', 'bytes', 'sha256'} and
            type(reference['bytes']) is int and 0 < reference['bytes'] <= 128 * 1024**2 and
            reference['sha256'] == OLD_SUMMARY_SHA, 'fixed pure summary dependency required')
    path = Path(reference['path'])
    require(path.is_absolute() and not any(p.is_symlink() for p in (path, *path.parents)),
            'canonical pure helper path required')
    data = path.read_bytes()
    require(len(data) == reference['bytes'] and hashlib.sha256(data).hexdigest() == reference['sha256'],
            'selected pure summary bytes differ')
    module = types.ModuleType('selected_previous_joint_summary')
    module.__file__ = str(path)
    exec(compile(data, str(path), 'exec'), module.__dict__)
    return module


def flattened(value):
    require(type(value) is list, 'native head array required')
    result = []
    for item in value:
        if type(item) is list:
            result.extend(flattened(item))
        else:
            require(type(item) in (int, float) and math.isfinite(item), 'finite nonboolean head value required')
            result.append(item)
    return result


def numeric_differences(pairs):
    differences, definedness = [], 0
    for left, right in pairs:
        require(all(v is None or type(v) in (int, float) and math.isfinite(v) for v in (left, right)),
                'finite optional diagnostic scalar required')
        definedness += (left is None) != (right is None)
        if left is not None and right is not None:
            differences.append(right - left)
    return {'paired_defined_count': len(differences), 'changed_definedness_count': definedness,
            'changed_value_count': sum(v != 0 for v in differences),
            'maximum_absolute_difference': max(map(abs, differences)) if differences else None,
            'mean_absolute_difference': math.fsum(map(abs, differences)) / len(differences) if differences else None,
            'mean_signed_difference': math.fsum(differences) / len(differences) if differences else None,
            'semantic_improvement_measured': False}


def greedy_intervals(row):
    facets = (row['greedy'].get('span_diagnostics') or {}).get('facets', {})
    return [[facets[field].get('present'), facets[field].get('token_start'),
             facets[field].get('token_end_inclusive')] if field in facets else [False, None, None]
            for field in FIELDS]


def search_pruning(search):
    if search is None:
        return None
    diagnostics = search['diagnostics']
    return {key: diagnostics[key] for key in ('incomplete_search', 'pruned_candidate_count',
            'pruned_beam_state_count', 'attempted_expansion_count', 'overlap_rejected_expansion_count',
            'complete_retained_state_count')}


def compare_rows(raw_rows, candidate_rows, raw_banks, candidate_banks):
    """Keep categorical/IR changes separate from numerically different scores."""
    require(len(raw_rows) == len(candidate_rows) == len(raw_banks) == len(candidate_banks) and
            [(r['seed'], r['split'], r['id']) for r in raw_rows] ==
            [(r['seed'], r['split'], r['id']) for r in candidate_rows], 'matched source/seed/split rows required')
    changes = dict.fromkeys(CHANGE_KEYS, 0)
    per_facet_presence = dict.fromkeys(FIELDS, 0)
    per_facet_intervals = dict.fromkeys(FIELDS, 0)
    head_deltas = {head: [] for head in ('start', 'end', 'presence', 'modality')}
    head_changed_rows = dict.fromkeys(head_deltas, 0)
    score_pairs = {key: [] for key in ('best_score', 'runner_up_score', 'joint_score_margin')}
    decision_pairs = {key: [] for key in ('modality', 'object', 'conditions', 'exceptions', 'temporal')}
    for left, right, a_bank, b_bank in zip(raw_rows, candidate_rows, raw_banks, candidate_banks, strict=True):
        for policy in ('greedy', 'joint'):
            a, b = left[policy], right[policy]
            for key in ('status', 'reason', 'canonical_ir'):
                changes[policy + '_' + key] += a[key] != b[key]
            changes[policy + '_status_reason_ir'] += any(a[key] != b[key]
                                                       for key in ('status', 'reason', 'canonical_ir'))
        a, b = left['joint']['fixed_decisions'], right['joint']['fixed_decisions']
        changes['fixed_modality'] += a['modality'] != b['modality']
        changes['fixed_presence'] += a['present'] != b['present']
        changes['fixed_ambiguity'] += a['ambiguous'] != b['ambiguous']
        for index, field in enumerate(FIELDS):
            per_facet_presence[field] += a['present'][index] != b['present'][index]
        for key in decision_pairs:
            decision_pairs[key].append((a['margins'][key], b['margins'][key]))
        changes['greedy_facet_intervals'] += greedy_intervals(left) != greedy_intervals(right)
        a, b = left['joint']['search'], right['joint']['search']
        a_spans = None if a is None else a['selected_spans']
        b_spans = None if b is None else b['selected_spans']
        changes['joint_selected_spans'] += a_spans != b_spans
        for index, field in enumerate(FIELDS):
            per_facet_intervals[field] += (None if a_spans is None else a_spans[index]) != (
                                         None if b_spans is None else b_spans[index])
        changes['joint_search_presence'] += (a is None) != (b is None)
        changes['joint_search_status_reason'] += (None if a is None else (a['status'], a['reason'])) != (
                                                 None if b is None else (b['status'], b['reason']))
        changes['joint_search_pruning_diagnostics'] += search_pruning(a) != search_pruning(b)
        changes['joint_search_full_diagnostics'] += (None if a is None else a['diagnostics']) != (
                                                    None if b is None else b['diagnostics'])
        for key in score_pairs:
            score_pairs[key].append((None if a is None else a[key], None if b is None else b[key]))
        for head in head_deltas:
            x, y = flattened(a_bank['heads'][head]), flattened(b_bank['heads'][head])
            require(len(x) == len(y) and x, 'matched nonempty diagnostic head shape required')
            deltas = [abs(u - v) for u, v in zip(x, y, strict=True)]
            head_changed_rows[head] += any(v != 0 for v in deltas)
            head_deltas[head].extend(deltas)
    return {'paired_source_seed_occurrences': len(raw_rows), 'changed_counts': changes,
            'changed_presence_by_facet': per_facet_presence,
            'changed_joint_selected_interval_by_facet': per_facet_intervals,
            'head_value_diagnostics': {head: {'paired_scalar_count': len(values),
                'changed_rows': head_changed_rows[head], 'changed_scalar_count': sum(v != 0 for v in values),
                'maximum_absolute_difference': max(values) if values else None,
                'mean_absolute_difference': math.fsum(values) / len(values) if values else None}
                for head, values in head_deltas.items()},
            'fixed_decision_margin_diagnostics': {key: numeric_differences(pairs)
                                                  for key, pairs in decision_pairs.items()},
            'joint_search_score_diagnostics': {key: numeric_differences(pairs)
                                               for key, pairs in score_pairs.items()},
            'score_scope': 'Native head values and retained-beam objectives; diagnostic differences without calibrated semantic confidence.',
            'semantic_improvement_measured': False}


def public_row(row, seed, position):
    result = copy.deepcopy(row)
    diagnostics = result['greedy'].get('span_diagnostics')
    if diagnostics is not None:
        diagnostics.pop('modality_logits')
    result.update(seed=seed, source_position=position, qualified=False, semantic_masks=dict.fromkeys(MASKS, 0))
    return result


def match_previous_raw_joint(previous, current):
    # The new head capture includes conditioner lineage metadata, so its whole
    # record digest changes even when all head values and outcomes are equal.
    require(all(previous[key] == current[key] for key in RAW_JOIN_FIELDS),
            'complete previous raw joint outcome differs')


def verify_bank_row(row, bank, native, seed, control, split, position, helper):
    require(bank['id'] == row['id'] == native['id'] and bank['seed'] == row['seed'] == seed and
            bank['control'] == row['control'] == control and bank['split'] == row['split'] == split and
            bank['capture_index'] == CONTROLS.index(control) * 64 + SPLITS.index(split) * 32 + position and
            helper.digest(bank) == row['score_row_sha256'], 'exact captured head/source row join differs')
    require(row['source_sha256'] == bank['source_sha256'] == native['source_sha256'] ==
            hashlib.sha256(row['source_text'].encode()).hexdigest() and bank['source_text'] == row['source_text'],
            'captured exact source text/hash differs')
    for key in ('original_latent_sha256', 'effective_latent_sha256', 'latent_donor_id',
                'latent_donor_position', 'latent_input_enabled'):
        require(row[key] == bank[key] == native[key], 'captured conditioner lineage differs: ' + key)
    require(row['latent_sha256'] == row['effective_latent_sha256'] == bank['latent_sha256'] ==
            native['decoder_row']['latent_sha256'] and row['greedy'] == native['decoder_row'],
            'exact paired native greedy/latent join differs')
    require(bank['request_sha256'] == native['request_sha256'] and
            row['latent_ablation'] == bank['latent_ablation'] ==
            {'zero_raw': 'zero', 'disabled_raw': 'disabled', 'rotated_raw': 'rotate'}.get(control, 'none') and
            row['latent_input_enabled'] is (control != 'disabled_raw') and
            row['conditioning_profile'] == bank['conditioning_profile'], 'control/gate/profile join differs')
    for key in ('model_latent_float32_sha256', 'control_transformation_scope'):
        require(row[key] == bank[key], 'captured tensor conditioner metadata differs: ' + key)
    require(set(bank['heads']) == {'start', 'end', 'presence', 'modality'}, 'four native head kinds required')
    tokens = [{'text': m.group(), 'start': m.start(), 'end': m.end()}
              for m in re.finditer(r'\w+|[^\w\s]', row['source_text'], re.UNICODE)]
    require(bank['tokens'] == tokens and bank['token_input_sha256'] == helper.digest(tokens),
            'captured source token join differs')
    count = len(tokens)
    for head in ('start', 'end'):
        require(len(bank['heads'][head]) == 6 and all(len(values) == count for values in bank['heads'][head]),
                'six native source interval heads required')
    require(len(bank['heads']['presence']) == 4 and all(len(v) == 2 for v in bank['heads']['presence']) and
            len(bank['heads']['modality']) == 3, 'fixed native decision head shape differs')
    for value in bank['heads'].values():
        flattened(value)
    for flag in ('accepted', 'source_fidelity_established', 'independent_semantic_review_completed', 'proof_authority'):
        require(row[flag] is False, 'unreviewed row authority differs')
    helper.verify_joint_transport(row)


def run(plan_path, plan_sha, batch_path, batch_sha, output):
    require(not any(name in sys.modules for name in ('torch', 'safetensors', 'transformers')),
            'summary must not import numerical/model providers')
    preliminary_data = Path(plan_path).read_bytes()
    require(hashlib.sha256(preliminary_data).hexdigest() == plan_sha, 'externally selected plan differs')
    preliminary = json.loads(preliminary_data)
    helper = load_selected_summary(preliminary['summary_baseline_helper_binding'])
    capture = helper.Capture()
    plan_binding, batch_binding = helper.binding(plan_path), helper.binding(batch_path)
    require(plan_binding['sha256'] == plan_sha and batch_binding['sha256'] == batch_sha,
            'externally selected plan/batch bytes differ')
    plan = capture.json(plan_binding)
    require(set(plan) == set(PLAN_KEYS) and plan['schema'] == 'source-only-joint-conditioning-plan/v1' and
            plan['policy'] == helper.POLICY and plan['controls'] == list(CONTROLS), 'closed fixed joint-conditioning plan differs')
    helper.zero_masks(plan['semantic_masks'])
    for key in ('helper_binding', 'baseline_helper_binding', 'frozen_joint_helper_binding',
                'summary_baseline_helper_binding', 'selector_binding'):
        capture.read(plan[key])
    protocol = capture.json(plan['protocol_binding'])
    require(protocol['schema'] == 'frozen-source-only-joint-conditioning-protocol-design/v1', 'protocol schema differs')
    baseline = capture.json(plan['baseline_plan_binding'])
    require([a['seed'] for a in baseline['arms']] == [p['seed'] for p in plan['baseline_receipts']] ==
            [p['seed'] for p in plan['baseline_joint_ledgers']] == list(SEEDS), 'fixed three-seed evidence required')
    batch = capture.json(batch_binding, sealed=False)
    require(batch['schema'] == 'source-only-joint-conditioning-batch/v1' and batch['successful_seeds'] == 3 and
            batch['selected_inputs_unchanged'] is True and [r['seed'] for r in batch['seeds']] == list(SEEDS) and
            batch['selected']['plan'] == plan_binding and batch['selected']['worker'] == plan['helper_binding'],
            'complete pinned three-seed batch required')
    for reference in batch['selected'].values():
        capture.read(reference)
    summaries, all_rows, all_banks, public_by_seed, reports, all_counts = [], [], [], {}, [], Counter()
    first_sources = None
    for selected, arm, prior, old_joint in zip(batch['seeds'], baseline['arms'], plan['baseline_receipts'],
                                              plan['baseline_joint_ledgers'], strict=True):
        seed = selected['seed']
        require(seed == arm['seed'] == prior['seed'] == old_joint['seed'] and selected['succeeded'] is True and
                type(selected['returncode']) is int and selected['returncode'] == 0, 'complete exact seed run required')
        parent = capture.json(selected['parent_report_binding'], sealed=False)
        require(parent['schema'] == 'source-only-joint-conditioning-worker-parent/v1' and parent['seed'] == seed and
                parent['succeeded'] is True and parent['failure'] is None and parent['returncode'] == 0 and
                parent['selected_inputs_unchanged'] is True and parent['selected'] ==
                {'plan': plan_binding, 'worker': plan['helper_binding']}, 'bounded parent evidence differs')
        report = capture.json(selected['worker_report_binding'])
        require(report['schema'] == 'source-only-joint-conditioning-report/v1' and report['status'] == 'completed' and
                report['seed'] == seed and report['plan_binding'] == plan_binding and report['policy'] == helper.POLICY and
                report['checkpoint_binding'] == arm['checkpoint_binding'] and report['request_count'] == 64 and
                report['conditioning_source_occurrences'] == 384 and report['total_greedy_joint_outcomes'] == 768 and
                report['runtime_admission_scope'] == 'fail_closed_complete64_per_each_of6_controls_previously_preflighted_finite_score_cohort',
                'fixed six-condition worker report differs')
        for flag in ('context_contract_unchanged', 'model_state_unchanged', 'checkpoint_unchanged',
                     'restored_adam_unchanged', 'global_cpu_rng_unchanged', 'all_requests_retained',
                     'greedy_profile_unchanged', 'native768_only', 'previous_raw_joint_exact_match'):
            require(report[flag] is True, 'worker preservation flag differs: ' + flag)
        for flag in ('parameter_gradients_created', 'formal_targets_read', 'training_executed',
                     'semantic_accuracy_measured', 'source_fidelity_established', 'qualified', 'accepted',
                     'proof_authority', 'independent_greedy_and_joint_model_forwards'):
            require(report[flag] is False, 'worker authority/execution flag differs: ' + flag)
        for key in ('new_encoder_calls', 'new_model_fits', 'proof_calls'):
            require(type(report[key]) is int and report[key] == 0, 'unexpected worker count: ' + key)
        helper.zero_masks(report['masks'])
        for reference in report['preserved_input_bindings']:
            capture.read(reference)
        for reference in report['selected_provider_entrypoints'].values():
            capture.read(helper.provider_binding(reference))
        ledger, bank = capture.json(report['proposal_ledger_binding']), capture.json(report['score_bank_binding'])
        require(ledger['schema'] == 'source-only-joint-conditioning-proposal-ledger/v1' and
                bank['schema'] == 'source-only-joint-conditioning-score-bank/v1' and
                ledger['seed'] == bank['seed'] == seed and ledger['plan_binding'] == bank['plan_binding'] == plan_binding and
                ledger['policy'] == helper.POLICY and len(ledger['rows']) == len(bank['rows']) == 384,
                'complete conditioned ledger/headbank selection differs')
        helper.zero_masks(ledger['semantic_masks'])
        helper.zero_masks(bank['semantic_masks'])
        require(bank['contains_formal_targets'] is False and all(ledger[f] is False for f in
                ('semantic_accuracy_measured', 'accepted', 'qualified', 'proof_authority')), 'worker ledger authority differs')
        rows, banks = ledger['rows'], bank['rows']
        require(len({(r['control'], r['split'], r['id']) for r in rows}) == 384, 'duplicate condition/source ledger pairs')
        old = capture.json(old_joint['ledger_binding'])
        require(old['schema'] == 'source-only-joint-span-proposal-ledger/v1' and old['seed'] == seed and
                len(old['rows']) == 64, 'previous complete raw joint ledger required')
        controls = {}
        raw_rows, raw_banks = rows[:64], banks[:64]
        for control_index, control in enumerate(CONTROLS):
            condition_rows, condition_banks = rows[control_index * 64:(control_index + 1) * 64], banks[control_index * 64:(control_index + 1) * 64]
            split_stats = {}
            for split_index, split in enumerate(SPLITS):
                now = capture.json(report['baseline_summaries'][control][split]['receipt_binding'])
                before = capture.json(prior['arms'][control][split + '_binding'])
                require(now == before and report['baseline_summaries'][control][split]['exact_previous_receipt_match'] is True and
                        now['input_count'] == now['eligible_count'] == len(now['rows']) == 32,
                        'exact saved six-control greedy replay differs')
                split_rows = condition_rows[split_index * 32:(split_index + 1) * 32]
                split_banks = condition_banks[split_index * 32:(split_index + 1) * 32]
                for position, (row, heads, native) in enumerate(zip(split_rows, split_banks, now['rows'], strict=True)):
                    verify_bank_row(row, heads, native, seed, control, split, position, helper)
                    require(row['conditioning_profile'] == report['conditioner_profiles'][control],
                            'declared conditioner profile differs')
                    if control == 'raw_source':
                        previous_row = old['rows'][split_index * 32 + position]
                        match_previous_raw_joint(previous_row, row)
                split_stats[split] = {**helper.structural_counts(split_rows), 'vs_raw': compare_rows(
                    raw_rows[split_index * 32:(split_index + 1) * 32], split_rows,
                    raw_banks[split_index * 32:(split_index + 1) * 32], split_banks)}
            controls[control] = {**helper.structural_counts(condition_rows), 'splits': split_stats,
                                'vs_raw': compare_rows(raw_rows, condition_rows, raw_banks, condition_banks)}
        sources = [(r['id'], r['split'], r['source_sha256'], r['source_text'], r['original_latent_sha256']) for r in raw_rows]
        require(first_sources is None or sources == first_sources, 'raw cohort/source vectors differ across decoder seeds')
        first_sources = sources
        stats = helper.structural_counts(rows)
        require(stats['greedy_proposals'] == report['greedy_proposals'] and stats['joint_proposals'] == report['joint_proposals'] and
                stats['joint_reason_counts'] == report['joint_reason_counts'] and
                stats['transition_counts'] == report['transition_counts'] and
                stats['search_totals'].get('incomplete_search_rows', 0) == report['search_incomplete_rows'],
                'worker structural counts differ from exact saved rows')
        expected_counts = {'optimizer_step_attempts': 0, 'optimizer_updates': 0, 'dimensional_restores': 1,
                           'embedded_parent_restores': 1, 'model_constructors': 3, 'wrapper_calls': 12,
                           'owner_decoder_calls': 12, 'source_row_decode_calls': 384, 'actual_model_forward_calls': 384,
                           'joint_selection_calls': stats['search_totals'].get('rows_with_search', 0),
                           'joint_additional_model_forward_calls': 0}
        require(report['counts'] == expected_counts and all(type(v) is int for v in report['counts'].values()),
                'actual native execution counters differ')
        require(len(report['restored_optimizer_state_checksums']) == 2 and
                report['restored_optimizer_state_checksums'][-1]['sha256'] == report['saved_optimizer_state_sha256'],
                'retained restored Adam checksum join differs')
        all_counts.update(report['counts'])
        all_rows.extend(rows)
        all_banks.extend(banks)
        public_by_seed[seed] = [public_row(row, seed, index % 64) for index, row in enumerate(rows)]
        reports.append({'seed': seed, 'report_binding': selected['worker_report_binding'],
                        'parent_binding': selected['parent_report_binding'], 'ledger_binding': report['proposal_ledger_binding'],
                        'score_bank_binding': report['score_bank_binding']})
        summaries.append({'seed': seed, 'aggregate': stats, 'controls': controls, 'counts': report['counts'],
                          'exact_previous_greedy_receipts': 12, 'exact_previous_raw_joint_rows': 64,
                          'resources': report['resources'], 'parent_wall_seconds': parent['wall_seconds']})
    require(dict(all_counts) == batch['completed_worker_counts'] and len(all_rows) == 1152,
            'complete combined native counters/outcomes differ')
    aggregate_controls = {}
    raw_rows = [r for r in all_rows if r['control'] == 'raw_source']
    raw_banks = [r for r in all_banks if r['control'] == 'raw_source']
    for control in CONTROLS:
        condition_rows = [r for r in all_rows if r['control'] == control]
        condition_banks = [r for r in all_banks if r['control'] == control]
        aggregate_controls[control] = {**helper.structural_counts(condition_rows), 'vs_raw': compare_rows(
            raw_rows, condition_rows, raw_banks, condition_banks), 'splits': {split: {
                **helper.structural_counts([r for r in condition_rows if r['split'] == split]),
                'vs_raw': compare_rows([r for r in raw_rows if r['split'] == split],
                                      [r for r in condition_rows if r['split'] == split],
                                      [r for r in raw_banks if r['split'] == split],
                                      [r for r in condition_banks if r['split'] == split])} for split in SPLITS}}
    capture.recheck()
    output = Path(output).absolute()
    require(not output.exists() and output.parent.is_dir() and
            not any(p.is_symlink() for p in (output, *output.parents)), 'fresh canonical public output required')
    output.mkdir(mode=0o700)
    own_binding = helper.binding(Path(__file__))
    public_bindings = []
    for seed in SEEDS:
        public_bindings.append({'seed': seed, 'ledger_binding': helper.write(output / ('seed' + str(seed) + '-ledger-01.json'), {
            'schema': 'source-only-joint-conditioning-public-proposal-ledger/v1', 'seed': seed,
            'plan_binding': plan_binding, 'batch_binding': batch_binding, 'helper_binding': own_binding,
            'policy': helper.POLICY, 'controls': list(CONTROLS), 'row_count': 384, 'policy_outcome_count': 768,
            'rows': public_by_seed[seed],
            'transformation': 'Exact worker ledger rows plus seed/source_position/qualified/integerzero masks; remove only greedy.span_diagnostics.modality_logits.',
            'contains_full_head_score_arrays': False, 'contains_source_vectors': False, 'contains_model_weights': False,
            'contains_formal_targets': False, 'accepted': False, 'qualified': False, 'proof_authority': False,
            'source_fidelity_established': False, 'independent_semantic_review_completed': False,
            'semantic_masks': dict.fromkeys(MASKS, 0)})})
    resources = {'worker_wall_seconds_total': math.fsum(r['resources']['elapsed_seconds'] for r in summaries),
                 'worker_cpu_seconds_total': math.fsum(r['resources']['cpu_seconds'] for r in summaries),
                 'maximum_worker_peak_rss_kib': max(r['resources']['peak_rss_kib'] for r in summaries),
                 'parent_wall_seconds_total': math.fsum(r['parent_wall_seconds'] for r in summaries),
                 'scope': 'Current native model/head capture plus both span selection policies; excludes upstream encoding/vector-bank creation/prior fitting/independent audits.',
                 'per_condition_performance_measured': False, 'compression_latency_gain_measured': False}
    summary_binding = helper.write(output / 'summary-01.json', {
        'schema': 'source-only-joint-conditioning-structural-summary/v1', 'status': 'completed',
        'plan_binding': plan_binding, 'batch_binding': batch_binding, 'helper_binding': own_binding,
        'summary_baseline_helper_binding': plan['summary_baseline_helper_binding'],
        'worker_evidence_bindings': reports, 'public_ledger_bindings': public_bindings,
        'policy': helper.POLICY, 'controls': list(CONTROLS), 'seeds': summaries,
        'aggregate': helper.structural_counts(all_rows), 'aggregate_controls': aggregate_controls,
        'actual_counts': dict(all_counts), 'original_source_count': 64, 'source_condition_seed_occurrences': 1152,
        'policy_outcomes': 2304, 'unique_policy_model_forwards': 1152, 'joint_extra_model_forwards': 0,
        'exact_previous_greedy_receipts': 36, 'exact_previous_greedy_repeat_occurrences': 1152,
        'exact_previous_raw_joint_repeat_occurrences': 192, 'resources': resources,
        'verified_input_binding_count': len(capture.references), 'verified_input_bindings': list(capture.references.values()),
        'validation_scope': 'Exact bound receipts/headbank joins, literal transport and scalar aggregation; fixed decisions, search and grammar require separate independent replay.',
        'accepted': False, 'qualified': False, 'proof_authority': False, 'training_executed': False,
        'formal_targets_read': False, 'source_fidelity_established': False, 'semantic_accuracy_measured': False,
        'independent_semantic_review_completed': False, 'semantic_masks': dict.fromkeys(MASKS, 0),
        'new_encoder_calls': 0, 'new_ae_or_pca_fits': 0, 'new_model_weights_created': False, 'proof_calls': 0,
        'limitations': protocol['interpretation_limits']})
    print(json.dumps({'status': 'completed', 'summary_binding': summary_binding,
                      'public_ledger_bindings': public_bindings, 'actual_counts': dict(all_counts),
                      'aggregate': helper.structural_counts(all_rows)}, sort_keys=True), flush=True)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('plan', 'batch'):
        parser.add_argument('--' + name, type=Path, required=True)
        parser.add_argument('--' + name + '-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    return run(args.plan, args.plan_sha256, args.batch, args.batch_sha256, args.output)


if __name__ == '__main__':
    raise SystemExit(main())
