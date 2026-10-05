"""Verify saved joint-span evidence and publish structural-only scalar results.

Standard-library aggregation only: no model, score replay, formal targets,
canonical owner imports, fitting, network or prover calls. Independent audit
must replay selection and grammar separately from this bound-evidence summary.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import re
import stat
from collections import Counter
from pathlib import Path

SEEDS = (1729, 1730, 1731)
SPLITS = ('train', 'development')
FIELDS = ('actor', 'action', 'object', 'conditions', 'exceptions', 'temporal')
MASKS = ('weak_decoder_fit', 'strong_semantic_fit', 'contrastive_supervision',
         'proof_supervision', 'fidelity_evaluation')
POLICY = {'candidates_per_facet': 16, 'beam_width': 64, 'ambiguity_epsilon': 1e-7,
          'modality_and_presence': 'unchanged_native_argmax_and_float32_margin',
          'span_pair_scores': 'float32_start_plus_end',
          'joint_objective': 'python_math_fsum_of_float32_pair_scores',
          'span_order': 'native_facet_order', 'optimality_scope': 'surviving_beam_only',
          'greedy_fallback': False, 'optional_facet_removal': False}
MAX_BYTES = 128 * 1024 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def strict_json(data):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate JSON key')
            result[key] = value
        return result

    def constant(value):
        raise ValueError('nonfinite JSON constant: ' + value)

    return json.loads(data, object_pairs_hook=pairs, parse_constant=constant)


def seal(value):
    require(type(value) is dict and value.get('content_sha256') ==
            digest({k: v for k, v in value.items() if k != 'content_sha256'}), 'record seal differs')


def zero_masks(value):
    require(type(value) is dict and set(value) == set(MASKS) and
            all(type(v) is int and v == 0 for v in value.values()), 'all semantic masks must remain integer zero')


def read_bytes(path):
    path = Path(path)
    require(path.is_absolute() and not any(p.is_symlink() for p in (path, *path.parents)),
            'absolute nonsymlink evidence path required')
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, 'rb') as stream:
        before = os.fstat(stream.fileno())
        require(stat.S_ISREG(before.st_mode) and 0 < before.st_size <= MAX_BYTES,
                'bounded regular evidence file required')
        data = stream.read(MAX_BYTES + 1)
        after = os.fstat(stream.fileno())
    require(len(data) == before.st_size and
            (before.st_ino, before.st_size, before.st_mtime_ns) ==
            (after.st_ino, after.st_size, after.st_mtime_ns), 'evidence changed while reading')
    return data


def binding(path):
    path = Path(path).absolute()
    data = read_bytes(path)
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def provider_binding(reference):
    """Keep provider version metadata separate from its closed byte binding."""
    require(type(reference) is dict and set(reference) == {'path', 'bytes', 'sha256', 'version'} and
            type(reference['version']) is str, 'selected provider metadata differs')
    return {key: reference[key] for key in ('path', 'bytes', 'sha256')}


class Capture:
    def __init__(self):
        self.references = {}

    def read(self, reference):
        require(type(reference) is dict and set(reference) == {'path', 'bytes', 'sha256'} and
                type(reference['bytes']) is int and 0 < reference['bytes'] <= MAX_BYTES and
                type(reference['sha256']) is str and re.fullmatch('[0-9a-f]{64}', reference['sha256']),
                'closed exact file binding required')
        data = read_bytes(reference['path'])
        require(len(data) == reference['bytes'] and hashlib.sha256(data).hexdigest() == reference['sha256'],
                'selected evidence binding differs: ' + reference['path'])
        previous = self.references.get(reference['path'])
        require(previous is None or previous == reference, 'conflicting selected file bindings')
        self.references[reference['path']] = copy.deepcopy(reference)
        return data

    def json(self, reference, *, sealed=True):
        value = strict_json(self.read(reference))
        if sealed:
            seal(value)
        return value

    def recheck(self):
        for reference in list(self.references.values()):
            self.read(reference)


def write(path, value):
    value['content_sha256'] = digest(value)
    data = encoded(value) + b'\n'
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return binding(path)


def verify_joint_transport(row):
    joint = row['joint']
    require(joint['status'] in ('proposal', 'abstained'), 'unknown joint row status')
    decisions = joint['fixed_decisions']
    require(decisions['modality'] in ('O', 'P', 'F') and
            type(decisions['present']) is list and len(decisions['present']) == 6 and
            all(type(v) is bool for v in decisions['present']) and decisions['present'][:2] == [True, True],
            'fixed required modality/presence contract differs')
    if joint['status'] == 'abstained':
        require(type(joint['reason']) is str and joint['canonical_ir'] is None and
                joint['facets'] is None and joint['family_syntax_checked'] is False,
                'joint abstention contains a proposal')
        return
    require(joint['reason'] is None and joint['family_syntax_checked'] is True and
            type(joint['canonical_ir']) is dict and set(joint['canonical_ir']) == {'rules'} and
            type(joint['canonical_ir']['rules']) is list and len(joint['canonical_ir']['rules']) == 1 and
            type(joint['facets']) is dict and set(joint['facets']) == set(FIELDS),
            'joint structural proposal shape differs')
    text = row['source_text']
    tokens = [{'text': m.group(), 'start': m.start(), 'end': m.end()}
              for m in re.finditer(r'\w+|[^\w\s]', text, re.UNICODE)]
    rule = joint['canonical_ir']['rules'][0]
    require(type(rule) is dict and set(rule) == {'modality', *FIELDS} and
            rule['modality'] == decisions['modality'], 'joint rule decision fields differ')
    occupied = set()
    for index, field in enumerate(FIELDS):
        facet = joint['facets'][field]
        present = decisions['present'][index]
        require(facet['present'] is present, 'joint copied facet presence differs')
        if present:
            left, right = facet['token_start'], facet['token_end_inclusive']
            require(type(left) is type(right) is int and 0 <= left <= right < len(tokens),
                    'joint token interval differs')
            positions = set(range(left, right + 1))
            require(not occupied & positions, 'joint copied spans overlap')
            occupied.update(positions)
            begin, end = tokens[left]['start'], tokens[right]['end']
            require(facet['char_start'] == begin and facet['char_end'] == end and
                    facet['text'] == text[begin:end], 'joint exact source transport differs')
            atom = facet['text']
        else:
            require(all(facet[key] is None for key in ('token_start', 'token_end_inclusive',
                        'char_start', 'char_end', 'text')), 'absent facet contains a source span')
            atom = ''
        expected = [atom] if present and field in FIELDS[3:] else [] if field in FIELDS[3:] else atom
        require(rule[field] == expected, 'joint rule/source facet join differs')


def structural_counts(rows):
    result = {'request_count': len(rows), 'policy_outcome_count': len(rows) * 2,
              'greedy_proposals': 0, 'joint_proposals': 0, 'rescued_greedy_overlap_abstentions': 0,
              'preserved_greedy_proposals': 0, 'changed_greedy_proposals': 0,
              'lost_greedy_proposals': 0}
    greedy_reasons, joint_reasons, transitions = Counter(), Counter(), Counter()
    search_totals = Counter()
    maxima = {'peak_feasible_expanded_state_count': 0, 'maximum_retained_beam_size': 0,
              'maximum_attempted_expansions_per_row': 0}
    for row in rows:
        greedy, joint = row['greedy'], row['joint']
        result['greedy_proposals'] += greedy['status'] == 'decoded'
        result['joint_proposals'] += joint['status'] == 'proposal'
        greedy_reasons.update([greedy['reason']] if greedy['reason'] is not None else [])
        joint_reasons.update([joint['reason']] if joint['reason'] is not None else [])
        transitions[greedy['status'] + '->' + joint['status']] += 1
        if greedy['status'] == 'decoded':
            if joint['status'] != 'proposal':
                result['lost_greedy_proposals'] += 1
            elif greedy['canonical_ir'] == joint['canonical_ir']:
                result['preserved_greedy_proposals'] += 1
            else:
                result['changed_greedy_proposals'] += 1
        if greedy['reason'] == 'copied_spans_overlap' and joint['status'] == 'proposal':
            result['rescued_greedy_overlap_abstentions'] += 1
        search = joint['search']
        if search is None:
            search_totals['rows_without_search'] += 1
            continue
        diagnostics = search['diagnostics']
        search_totals['rows_with_search'] += 1
        search_totals['incomplete_search_rows'] += diagnostics['incomplete_search']
        search_totals['rows_with_candidate_pruning'] += diagnostics['pruned_candidate_count'] > 0
        search_totals['rows_with_beam_pruning'] += diagnostics['pruned_beam_state_count'] > 0
        for key in ('attempted_expansion_count', 'overlap_rejected_expansion_count',
                    'pruned_candidate_count', 'pruned_beam_state_count', 'complete_retained_state_count'):
            search_totals[key] += diagnostics[key]
        search_totals['enumerated_candidate_spans'] += sum(
            facet['enumerated_span_count'] for facet in diagnostics['facets'].values())
        search_totals['retained_candidate_spans'] += sum(
            facet['retained_candidate_count'] for facet in diagnostics['facets'].values())
        search_totals['candidate_cutoff_tied_facets'] += sum(
            facet['cutoff_tied'] for facet in diagnostics['facets'].values())
        search_totals['beam_boundary_tied_layers'] += sum(layer['beam_boundary_tied'] for layer in diagnostics['layers'])
        maxima['peak_feasible_expanded_state_count'] = max(
            maxima['peak_feasible_expanded_state_count'], diagnostics['peak_feasible_expanded_state_count'])
        maxima['maximum_retained_beam_size'] = max(
            maxima['maximum_retained_beam_size'], *(layer['retained_state_count'] for layer in diagnostics['layers']))
        maxima['maximum_attempted_expansions_per_row'] = max(
            maxima['maximum_attempted_expansions_per_row'], diagnostics['attempted_expansion_count'])
    result.update(greedy_reason_counts=dict(greedy_reasons), joint_reason_counts=dict(joint_reasons),
                  transition_counts=dict(transitions), search_totals=dict(search_totals), search_maxima=maxima)
    return result


def run(plan_path, plan_sha, batch_path, batch_sha, output):
    capture = Capture()
    plan_binding, batch_binding = binding(plan_path), binding(batch_path)
    require(plan_binding['sha256'] == plan_sha and batch_binding['sha256'] == batch_sha,
            'externally selected plan/batch differs')
    plan = capture.json(plan_binding)
    require(plan['schema'] == 'source-only-joint-span-plan/v1' and plan['policy'] == POLICY,
            'fixed joint plan differs')
    zero_masks(plan['semantic_masks'])
    for key in ('helper_binding', 'selector_binding', 'baseline_helper_binding'):
        capture.read(plan[key])
    capture.json(plan['protocol_binding'])
    baseline = capture.json(plan['baseline_plan_binding'])
    require([r['seed'] for r in plan['baseline_raw_receipts']] == list(SEEDS), 'three baseline seeds required')
    batch = capture.json(batch_binding, sealed=False)
    require(batch['schema'] == 'source-only-joint-span-batch/v1' and batch['successful_seeds'] == 3 and
            batch['selected_inputs_unchanged'] is True and
            [r['seed'] for r in batch['seeds']] == list(SEEDS) and
            batch['selected']['plan'] == plan_binding and batch['selected']['worker'] == plan['helper_binding'],
            'complete pinned three-seed batch required')
    for reference in batch['selected'].values():
        capture.read(reference)
    summaries, public_rows, all_counts, report_bindings = [], [], Counter(), []
    first_sources = None
    for batch_row, prior, arm in zip(batch['seeds'], plan['baseline_raw_receipts'], baseline['arms'], strict=True):
        seed = batch_row['seed']
        require(seed == prior['seed'] == arm['seed'] and batch_row['succeeded'] is True and
                type(batch_row['returncode']) is int and batch_row['returncode'] == 0, 'seed execution incomplete')
        parent = capture.json(batch_row['parent_report_binding'], sealed=False)
        require(parent['schema'] == 'source-only-joint-span-worker-parent/v1' and parent['seed'] == seed and
                parent['succeeded'] is True and parent['failure'] is None and parent['returncode'] == 0 and
                parent['selected_inputs_unchanged'] is True and
                parent['selected'] == {'plan': plan_binding, 'worker': plan['helper_binding']},
                'independent parent evidence differs')
        report = capture.json(batch_row['worker_report_binding'])
        require(report['schema'] == 'source-only-joint-span-report/v1' and report['status'] == 'completed' and
                report['seed'] == seed and report['plan_binding'] == plan_binding and report['policy'] == POLICY and
                report['checkpoint_binding'] == arm['checkpoint_binding'] and report['request_count'] == 64 and
                report['runtime_admission_scope'] == 'fail_closed_complete64_previously_preflighted_finite_score_cohort',
                'fixed worker report differs')
        for flag in ('context_contract_unchanged', 'model_state_unchanged', 'checkpoint_unchanged',
                     'restored_adam_unchanged', 'global_cpu_rng_unchanged', 'all_requests_retained',
                     'greedy_profile_unchanged', 'native768_only'):
            require(report[flag] is True, 'worker preservation flag differs: ' + flag)
        for flag in ('parameter_gradients_created', 'formal_targets_read', 'training_executed',
                     'semantic_accuracy_measured', 'source_fidelity_established', 'qualified',
                     'accepted', 'proof_authority', 'independent_greedy_and_joint_model_forwards'):
            require(report[flag] is False, 'worker authority or execution flag differs: ' + flag)
        for field in ('new_encoder_calls', 'new_model_fits', 'proof_calls'):
            require(type(report[field]) is int and report[field] == 0, 'unexpected execution count: ' + field)
        zero_masks(report['masks'])
        for reference in report['preserved_input_bindings']:
            capture.read(reference)
        for reference in report['selected_provider_entrypoints'].values():
            capture.read(provider_binding(reference))
        capture.read(report['score_bank_binding'])
        ledger = capture.json(report['proposal_ledger_binding'])
        require(ledger['schema'] == 'source-only-joint-span-proposal-ledger/v1' and ledger['seed'] == seed and
                ledger['plan_binding'] == plan_binding and ledger['policy'] == POLICY and len(ledger['rows']) == 64,
                'worker ledger selection differs')
        zero_masks(ledger['semantic_masks'])
        for flag in ('semantic_accuracy_measured', 'accepted', 'qualified', 'proof_authority'):
            require(ledger[flag] is False, 'worker ledger authority differs')
        rows = ledger['rows']
        require(len({r['id'] for r in rows}) == 64, 'duplicate source ledger IDs')
        baseline_rows = {}
        for split in SPLITS:
            now = capture.json(report['baseline_summaries'][split]['receipt_binding'])
            before = capture.json(prior[split + '_binding'])
            require(now == before and report['baseline_summaries'][split]['exact_previous_receipt_match'] is True and
                    now['input_count'] == now['eligible_count'] == 32 and len(now['rows']) == 32,
                    'unchanged exact native greedy replay differs')
            baseline_rows[split] = now['rows']
            split_rows = [r for r in rows if r['split'] == split]
            require(len(split_rows) == 32 and [r['id'] for r in split_rows] == [r['id'] for r in now['rows']],
                    'split/native original ID order differs')
            for row, native in zip(split_rows, now['rows'], strict=True):
                require(row['greedy'] == native['decoder_row'] and row['source_sha256'] == native['source_sha256'] and
                        row['latent_sha256'] == native['effective_latent_sha256'] == native['decoder_row']['latent_sha256'] and
                        native['id'] == native['latent_donor_id'] == row['id'], 'paired source/raw/native join differs')
        sources = []
        for index, row in enumerate(rows):
            require(row['split'] == SPLITS[index // 32] and
                    hashlib.sha256(row['source_text'].encode()).hexdigest() == row['source_sha256'],
                    'source text hash/order differs')
            for flag in ('accepted', 'source_fidelity_established', 'independent_semantic_review_completed', 'proof_authority'):
                require(row[flag] is False, 'row authority differs')
            require(re.fullmatch('[0-9a-f]{64}', row['score_row_sha256']), 'score row digest required')
            verify_joint_transport(row)
            sources.append((row['id'], row['split'], row['source_sha256'], row['latent_sha256'], row['source_text']))
            public = copy.deepcopy(row)
            diagnostics = public['greedy'].get('span_diagnostics')
            if diagnostics is not None:
                diagnostics.pop('modality_logits')
            public.update(seed=seed, source_position=index, qualified=False, semantic_masks=dict.fromkeys(MASKS, 0))
            public_rows.append(public)
        require(first_sources is None or sources == first_sources, 'source/raw vectors differ across decoder seeds')
        first_sources = sources
        stats = structural_counts(rows)
        require(stats['greedy_proposals'] == report['greedy_proposals'] and stats['joint_proposals'] == report['joint_proposals'] and
                stats['joint_reason_counts'] == report['joint_reason_counts'] and
                stats['transition_counts'] == report['transition_counts'] and
                stats['search_totals'].get('incomplete_search_rows', 0) == report['search_incomplete_rows'],
                'worker structural scalar report differs from saved rows')
        counts = report['counts']
        expected = {'optimizer_step_attempts': 0, 'optimizer_updates': 0, 'dimensional_restores': 1,
                    'embedded_parent_restores': 1, 'model_constructors': 3, 'wrapper_calls': 2,
                    'owner_decoder_calls': 2, 'source_row_decode_calls': 64, 'actual_model_forward_calls': 64,
                    'joint_selection_calls': stats['search_totals'].get('rows_with_search', 0),
                    'joint_additional_model_forward_calls': 0}
        require(counts == expected and all(type(v) is int for v in counts.values()), 'native/joint actual counters differ')
        require(len(report['restored_optimizer_state_checksums']) == 2 and
                report['restored_optimizer_state_checksums'][-1]['sha256'] == report['saved_optimizer_state_sha256'],
                'retained Adam checksum join differs')
        all_counts.update(counts)
        report_bindings.append({'seed': seed, 'report_binding': batch_row['worker_report_binding'],
                                'parent_binding': batch_row['parent_report_binding'],
                                'ledger_binding': report['proposal_ledger_binding'],
                                'score_bank_binding': report['score_bank_binding']})
        summaries.append({'seed': seed, **stats, 'splits': {split: structural_counts(
            [r for r in rows if r['split'] == split]) for split in SPLITS}, 'counts': counts,
            'exact_greedy_baseline_repeat': True, 'resources': report['resources'],
            'parent_wall_seconds': parent['wall_seconds']})
    require(dict(all_counts) == batch['completed_worker_counts'] and len(public_rows) == 192,
            'batch combined counts or complete paired outcomes differ')
    capture.recheck()
    aggregate = structural_counts(public_rows)
    resources = {'worker_wall_seconds_total': math.fsum(r['resources']['elapsed_seconds'] for r in summaries),
                 'worker_cpu_seconds_total': math.fsum(r['resources']['cpu_seconds'] for r in summaries),
                 'maximum_worker_peak_rss_kib': max(r['resources']['peak_rss_kib'] for r in summaries),
                 'parent_wall_seconds_total': math.fsum(r['parent_wall_seconds'] for r in summaries),
                 'scope': 'native_greedy_model_execution_head_capture_and_pure_joint_search_excludes_upstream_encoding_and_prior_training'}
    output = Path(output).absolute()
    require(not output.exists() and output.parent.is_dir() and
            not any(p.is_symlink() for p in (output, *output.parents)), 'fresh canonical public output required')
    output.mkdir(mode=0o700)
    helper_binding = binding(Path(__file__))
    ledger_binding = write(output / 'proposal-ledger-01.json', {
        'schema': 'source-only-joint-span-public-proposal-ledger/v1', 'plan_binding': plan_binding,
        'batch_binding': batch_binding, 'helper_binding': helper_binding, 'policy': POLICY,
        'row_count': 192, 'policy_outcome_count': 384, 'rows': public_rows,
        'transformation': 'Exact worker ledger rows plus seed/source_position/qualified/zero masks; remove only greedy.span_diagnostics.modality_logits.',
        'contains_full_head_score_arrays': False, 'contains_source_vectors': False, 'contains_model_weights': False,
        'contains_formal_targets': False, 'accepted': False, 'qualified': False, 'proof_authority': False,
        'source_fidelity_established': False, 'independent_semantic_review_completed': False,
        'semantic_masks': dict.fromkeys(MASKS, 0)})
    summary_binding = write(output / 'summary-01.json', {
        'schema': 'source-only-joint-span-structural-summary/v1', 'status': 'completed',
        'plan_binding': plan_binding, 'batch_binding': batch_binding, 'helper_binding': helper_binding,
        'worker_evidence_bindings': report_bindings, 'public_ledger_binding': ledger_binding,
        'policy': POLICY, 'seeds': summaries, 'aggregate': aggregate, 'actual_counts': dict(all_counts),
        'original_source_count': 64, 'paired_source_seed_occurrences': 192, 'policy_outcomes': 384,
        'unique_policy_model_forwards': 192, 'joint_extra_model_forwards': 0,
        'exact_previous_greedy_repeat_occurrences': 192, 'resources': resources,
        'verified_input_binding_count': len(capture.references),
        'verified_input_bindings': list(capture.references.values()),
        'validation_scope': 'Exact bound receipts and aggregation plus literal transport; numerical scores and joint search are not independently replayed by this summarizer.',
        'runtime_admission_scope': 'fail_closed_complete64_previously_preflighted_finite_score_cohort',
        'accepted': False, 'qualified': False, 'proof_authority': False, 'training_executed': False,
        'formal_targets_read': False, 'source_fidelity_established': False, 'semantic_accuracy_measured': False,
        'independent_semantic_review_completed': False, 'semantic_masks': dict.fromkeys(MASKS, 0),
        'new_encoder_calls': 0, 'new_ae_or_pca_fits': 0, 'new_model_weights_created': False, 'proof_calls': 0,
        'limitations': ['Structural proposal coverage is not source-fidelity or legal correctness.',
                        'Top16 candidate pruning and beam64 pruning can hide feasible, correct or best assignments.',
                        'Survivor margins concern retained complete beam states; they are not calibrated semantic confidence.',
                        'All64 exposed authored sources use repeated components; no natural or pristine holdout claim.',
                        'TRAIN/DEV labels describe reconstruction splits; historical decoder training overlap is unaudited.',
                        'Single copied deontic rule only; actor/action/modality/scope errors remain possible.',
                        'Both policies share one fixed raw768 decoder forward; there are no independently retrained models.',
                        '8D/384D and PCA/AE conditioner interventions were not executed in this round.',
                        'Recorded model/Adam/RNG preservation checks are worker evidence, not independent numerical attestation.',
                        'Selected entrypoints and canonical sources do not form a complete native binary closure or OS sandbox.']})
    print(json.dumps({'status': 'completed', 'summary_binding': summary_binding,
                      'public_ledger_binding': ledger_binding, 'aggregate': aggregate,
                      'actual_counts': dict(all_counts)}, sort_keys=True), flush=True)
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
