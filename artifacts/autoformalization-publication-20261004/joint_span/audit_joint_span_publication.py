"""Independently join public joint-span results to passed saved-score evidence.

Standard-library file/hash checking and aggregation only. This second phase
does not import the summarizer, selector, core auditor, owners, or ML providers.
The selected passed core audit supplies the separately verified score replay.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import re
import sys
from pathlib import Path

MASKS = ('weak_decoder_fit', 'strong_semantic_fit', 'contrastive_supervision',
         'proof_supervision', 'fidelity_evaluation')
PLACEHOLDER = re.compile(
    r'(\{\{[^}]*\}\}|<[^>]*(?:source|placeholder|todo|copy)[^>]*>|'
    r'\b(?:todo|tbd|placeholder|source_text|raw_source|copy_source|lorem ipsum)\b|'
    r'__[^_]*(?:source|placeholder|todo)[^_]*__)', re.IGNORECASE)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(value):
    data = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()
    return hashlib.sha256(data).hexdigest()


class Capture:
    def __init__(self):
        self.files = {}

    def bound(self, reference):
        require(type(reference) is dict and set(reference) == {'path', 'bytes', 'sha256'} and
                type(reference['bytes']) is int and 0 <= reference['bytes'] <= 128 * 1024**2,
                'closed bounded exact file binding required')
        path = Path(reference['path'])
        require(path.is_absolute() and not any(p.is_symlink() for p in (path, *path.parents)),
                'absolute nonsymlink evidence required')
        data = path.read_bytes()
        require(len(data) == reference['bytes'] and hashlib.sha256(data).hexdigest() == reference['sha256'],
                'selected file bytes differ: ' + str(path))
        require(str(path) not in self.files or self.files[str(path)] == reference, 'conflicting evidence binding')
        self.files[str(path)] = copy.deepcopy(reference)
        return data

    def read(self, reference):
        def pairs(items):
            result = {}
            for key, value in items:
                require(key not in result, 'duplicate JSON key')
                result[key] = value
            return result
        value = json.loads(self.bound(reference), object_pairs_hook=pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))
        if 'content_sha256' in value:
            require(value['content_sha256'] == digest({k: v for k, v in value.items() if k != 'content_sha256'}),
                    'JSON seal differs')
        return value

    def external(self, path, selected_sha):
        path = Path(path).absolute()
        data = path.read_bytes()
        reference = {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
        require(reference['sha256'] == selected_sha, 'externally selected SHA differs')
        return self.read(reference), reference

    def references(self, value):
        if type(value) is dict:
            if set(value) == {'path', 'bytes', 'sha256'}:
                self.bound(value)
            else:
                for item in value.values():
                    self.references(item)
        elif type(value) is list:
            for item in value:
                self.references(item)


def count_labels(labels):
    result = {}
    for label in labels:
        if label is not None:
            result[label] = result.get(label, 0) + 1
    return result


def statistics(rows):
    """Independent grouped/list-comprehension scalar reconstruction."""
    greedy = [row for row in rows if row['greedy']['status'] == 'decoded']
    joint = [row for row in rows if row['joint']['status'] == 'proposal']
    searched = [row['joint']['search']['diagnostics'] for row in rows if row['joint']['search'] is not None]
    search_totals = {}
    if len(searched) != len(rows):
        search_totals['rows_without_search'] = len(rows) - len(searched)
    if searched:
        search_totals.update(
            rows_with_search=len(searched),
            incomplete_search_rows=sum(d['incomplete_search'] for d in searched),
            rows_with_candidate_pruning=sum(d['pruned_candidate_count'] > 0 for d in searched),
            rows_with_beam_pruning=sum(d['pruned_beam_state_count'] > 0 for d in searched),
            enumerated_candidate_spans=sum(f['enumerated_span_count'] for d in searched for f in d['facets'].values()),
            retained_candidate_spans=sum(f['retained_candidate_count'] for d in searched for f in d['facets'].values()),
            candidate_cutoff_tied_facets=sum(f['cutoff_tied'] for d in searched for f in d['facets'].values()),
            beam_boundary_tied_layers=sum(layer['beam_boundary_tied'] for d in searched for layer in d['layers']))
        for key in ('attempted_expansion_count', 'overlap_rejected_expansion_count', 'pruned_candidate_count',
                    'pruned_beam_state_count', 'complete_retained_state_count'):
            search_totals[key] = sum(d[key] for d in searched)
    return {
        'request_count': len(rows), 'policy_outcome_count': len(rows) * 2,
        'greedy_proposals': len(greedy), 'joint_proposals': len(joint),
        'rescued_greedy_overlap_abstentions': sum(row['greedy']['reason'] == 'copied_spans_overlap' for row in joint),
        'preserved_greedy_proposals': sum(row['joint']['status'] == 'proposal' and
                                        row['greedy']['canonical_ir'] == row['joint']['canonical_ir'] for row in greedy),
        'changed_greedy_proposals': sum(row['joint']['status'] == 'proposal' and
                                      row['greedy']['canonical_ir'] != row['joint']['canonical_ir'] for row in greedy),
        'lost_greedy_proposals': sum(row['joint']['status'] != 'proposal' for row in greedy),
        'greedy_reason_counts': count_labels(row['greedy']['reason'] for row in rows),
        'joint_reason_counts': count_labels(row['joint']['reason'] for row in rows),
        'transition_counts': count_labels(row['greedy']['status'] + '->' + row['joint']['status'] for row in rows),
        'search_totals': search_totals,
        'search_maxima': {
            'peak_feasible_expanded_state_count': max([0] + [d['peak_feasible_expanded_state_count'] for d in searched]),
            'maximum_retained_beam_size': max([0] + [layer['retained_state_count'] for d in searched for layer in d['layers']]),
            'maximum_attempted_expansions_per_row': max([0] + [d['attempted_expansion_count'] for d in searched])}}


def zero_masks(value):
    require(type(value) is dict and set(value) == set(MASKS) and
            all(type(v) is int and v == 0 for v in value.values()), 'integer-zero semantic masks required')


def public_row(worker_row, seed, position):
    result = copy.deepcopy(worker_row)
    if 'span_diagnostics' in result['greedy']:
        del result['greedy']['span_diagnostics']['modality_logits']
    result.update(seed=seed, source_position=position, qualified=False, semantic_masks=dict.fromkeys(MASKS, 0))
    return result


def native_source_tokens(text):
    require(type(text) is str and text.strip() and len(text) <= 16384, 'bounded nonblank source required')
    result = []
    for match in re.finditer(r'\w+|[^\w\s]', text, re.UNICODE):
        value = match.group().casefold().encode('utf-8')
        require(len(value) <= 2048, 'native token UTF8 byte bound exceeded')
        result.append({'text': match.group(), 'start': match.start(), 'end': match.end(),
                       'byte_ids': [byte + 1 for byte in value]})
    require(1 <= len(result) <= 256, 'native source token count bound exceeded')
    return result


def complete_copied_rule_contract(ir):
    require(type(ir) is dict and set(ir) == {'rules'} and type(ir['rules']) is list and len(ir['rules']) == 1,
            'exact one-rule canonical AST required')
    rule = ir['rules'][0]
    require(type(rule) is dict and set(rule) == {'modality', 'actor', 'action', 'object', 'conditions', 'exceptions', 'temporal'},
            'exact seven canonical facets required')
    require(rule['modality'] in ('O', 'P', 'F'), 'unknown canonical deontic modality')
    strings = []
    for field in ('modality', 'actor', 'action', 'object'):
        value = rule[field]
        require(type(value) is str and len(value) <= 4096 and (field == 'object' or bool(value.strip())),
                'bounded canonical scalar required')
        strings.append(value)
    for field in ('conditions', 'exceptions', 'temporal'):
        atoms = rule[field]
        require(type(atoms) is list and len(atoms) <= 1 and
                all(type(value) is str and value.strip() and len(value) <= 4096 for value in atoms) and
                atoms == sorted(set(atoms)), 'bounded exact copied qualifier required')
        strings.extend(atoms)
    require(not any(PLACEHOLDER.search(value) for value in strings), 'pinned deontic grammar placeholder rejection')


def audit(core_path, core_sha, summary_path, summary_sha, ledger_path, ledger_sha, output):
    require('torch' not in sys.modules, 'pure publication audit must not import Torch')
    capture = Capture()
    core, core_binding = capture.external(core_path, core_sha)
    summary, summary_binding = capture.external(summary_path, summary_sha)
    public, public_binding = capture.external(ledger_path, ledger_sha)
    require(core['schema'] == 'independent-source-only-joint-span-audit/v1' and core['status'] == 'passed' and
            core['native_head_records_checked'] == core['paired_source_seed_occurrences'] == 192 and
            core['policy_outcomes_checked'] == 384 and core['complete_prior_raw_receipts_exact'] is True,
            'selected passed complete core audit required')
    require(summary['schema'] == 'source-only-joint-span-structural-summary/v1' and summary['status'] == 'completed' and
            public['schema'] == 'source-only-joint-span-public-proposal-ledger/v1', 'selected public result schemas differ')
    capture.references(core)
    capture.references(summary)
    capture.references(public)
    require(summary['plan_binding'] == public['plan_binding'] == core['plan_binding'] and
            summary['batch_binding'] == public['batch_binding'] == core['batch_binding'] and
            summary['public_ledger_binding'] == public_binding and summary['helper_binding'] == public['helper_binding'],
            'public result/core audit lineage differs')
    require([s['seed'] for s in summary['seeds']] == [s['seed'] for s in core['seed_checks']] == [1729, 1730, 1731],
            'all three original decoder seeds required')
    require(summary['original_source_count'] == 64 and summary['paired_source_seed_occurrences'] == 192 and
            summary['policy_outcomes'] == public['policy_outcome_count'] == 384 and public['row_count'] == len(public['rows']) == 192 and
            summary['unique_policy_model_forwards'] == 192 and summary['joint_extra_model_forwards'] == 0 and
            summary['exact_previous_greedy_repeat_occurrences'] == 192, 'complete denominator/call scope differs')
    for value in (summary, public):
        zero_masks(value['semantic_masks'])
        for key in ('accepted', 'qualified', 'proof_authority', 'source_fidelity_established', 'independent_semantic_review_completed'):
            require(value[key] is False, 'public evidence authority differs')
    for key in ('training_executed', 'formal_targets_read', 'semantic_accuracy_measured', 'new_model_weights_created'):
        require(summary[key] is False, 'summary semantic/numerical scope differs')
    for key in ('new_encoder_calls', 'new_ae_or_pca_fits', 'proof_calls'):
        require(type(summary[key]) is int and summary[key] == 0, 'new fitting/model/prover execution reported')
    for key in ('contains_full_head_score_arrays', 'contains_source_vectors', 'contains_model_weights', 'contains_formal_targets'):
        require(public[key] is False, 'public ledger contains excluded numerical/reference material')
    baseline_plan = capture.read(capture.read(core['plan_binding'])['baseline_plan_binding'])
    source_inputs = capture.read(baseline_plan['source_inputs_binding'])
    sources = {row['id']: row for row in source_inputs['rows']}
    worker_rows = []
    recomputed_seeds = []
    numerical_counts = {}
    wall = cpu = parent_wall = 0.0
    maximum_rss = 0
    native_encoding_rows_checked = grammar_proposal_occurrences_checked = 0
    core_outcome_map = {(row['seed'], row['id']): row for row in core['policy_outcomes']}
    require(len(core_outcome_map) == 192, 'core paired outcome identity set differs')
    for evidence, selected, checked in zip(summary['worker_evidence_bindings'], summary['seeds'], core['seed_checks'], strict=True):
        seed = selected['seed']
        require(evidence['seed'] == checked['seed'] == seed and evidence['report_binding'] == checked['worker_report_binding'] and
                evidence['parent_binding'] == checked['parent_report_binding'], 'public summary worker selection differs from core audit')
        report, parent = capture.read(evidence['report_binding']), capture.read(evidence['parent_binding'])
        require(evidence['ledger_binding'] == report['proposal_ledger_binding'] and evidence['score_bank_binding'] == report['score_bank_binding'],
                'public summary runtime ledger/score selection differs')
        ledger = capture.read(evidence['ledger_binding'])
        rows = ledger['rows']
        bank = capture.read(evidence['score_bank_binding'])
        score_rows = {row['id']: row for row in bank['rows']}
        native_rows = {}
        for split in ('train', 'development'):
            receipt = capture.read(report['baseline_summaries'][split]['receipt_binding'])
            native_rows.update({row['id']: row for row in receipt['rows']})
        stats = statistics(rows)
        expected = {'seed': seed, **stats, 'splits': {split: statistics([row for row in rows if row['split'] == split])
                    for split in ('train', 'development')}, 'counts': report['counts'],
                    'exact_greedy_baseline_repeat': True, 'resources': report['resources'],
                    'parent_wall_seconds': parent['wall_seconds']}
        require(selected == expected, 'public per-seed/split structural scalar summary differs')
        recomputed_seeds.append(expected)
        require(stats['greedy_proposals'] == checked['raw_greedy_proposals'] and
                stats['joint_proposals'] == checked['joint_structural_proposals'] and
                stats['preserved_greedy_proposals'] == checked['greedy_proposals_preserved_exactly'] and
                stats['rescued_greedy_overlap_abstentions'] == checked['overlap_abstentions_rescued_structurally'],
                'structural summary disagrees with independently replayed core audit')
        for position, row in enumerate(rows):
            copied = public_row(row, seed, position)
            worker_rows.append(copied)
            source = sources[row['id']]
            require(source['source_sha256'] == row['source_sha256'] and source['input']['source_text'] == row['source_text'],
                    'public proposal source hash/text binding differs')
            full_tokens = native_source_tokens(row['source_text'])
            reduced_tokens = [{key: token[key] for key in ('text', 'start', 'end')} for token in full_tokens]
            require(native_rows[row['id']]['encoding'] == {
                'outcome': 'admitted', 'token_count': len(full_tokens),
                'token_input_sha256': digest(full_tokens), 'reason': None},
                'native full token/byte_ids input hash differs')
            require(score_rows[row['id']]['tokens'] == reduced_tokens and
                    score_rows[row['id']]['token_input_sha256'] == digest(reduced_tokens),
                    'score-bank reduced token metadata hash differs')
            native_encoding_rows_checked += 1
            for policy, status in (('greedy', 'decoded'), ('joint', 'proposal')):
                if row[policy]['status'] == status:
                    complete_copied_rule_contract(row[policy]['canonical_ir'])
                    grammar_proposal_occurrences_checked += 1
            joined = core_outcome_map[(seed, row['id'])]
            require(all(joined[key] == value for key, value in {
                'split': row['split'], 'greedy_status': row['greedy']['status'], 'greedy_reason': row['greedy']['reason'],
                'joint_status': row['joint']['status'], 'joint_reason': row['joint']['reason']}.items()),
                'public paired row disagrees with independently audited outcome')
        for key, value in report['counts'].items():
            numerical_counts[key] = numerical_counts.get(key, 0) + value
        wall += report['resources']['elapsed_seconds']
        cpu += report['resources']['cpu_seconds']
        parent_wall += parent['wall_seconds']
        maximum_rss = max(maximum_rss, report['resources']['peak_rss_kib'])
    require(public['rows'] == worker_rows, 'public192-row transformation differs from exact saved worker ledgers')
    for row in public['rows']:
        zero_masks(row['semantic_masks'])
        for key in ('accepted', 'qualified', 'source_fidelity_established', 'independent_semantic_review_completed', 'proof_authority'):
            require(row[key] is False, 'public paired row grants unexpected authority')
        require('modality_logits' not in row['greedy'].get('span_diagnostics', {}), 'raw head logit bank leaked into public row')
    aggregate = statistics(worker_rows)
    require(summary['aggregate'] == aggregate and summary['actual_counts'] == numerical_counts == core['actual_root_worker_counts'],
            'public aggregate/outcome/model counters differ')
    # fsum is the summarizer's declared aggregation recipe; verify from original
    # report floats rather than depending on the local sequential running sums.
    resources = {
        'worker_wall_seconds_total': math.fsum(s['resources']['elapsed_seconds'] for s in recomputed_seeds),
        'worker_cpu_seconds_total': math.fsum(s['resources']['cpu_seconds'] for s in recomputed_seeds),
        'maximum_worker_peak_rss_kib': maximum_rss,
        'parent_wall_seconds_total': math.fsum(s['parent_wall_seconds'] for s in recomputed_seeds),
        'scope': 'native_greedy_model_execution_head_capture_and_pure_joint_search_excludes_upstream_encoding_and_prior_training'}
    require(summary['resources'] == resources and wall >= 0 and cpu >= 0 and parent_wall >= 0,
            'public measured-resource aggregation differs')
    require(summary['verified_input_binding_count'] == len(summary['verified_input_bindings']) and
            len({ref['path'] for ref in summary['verified_input_bindings']}) == len(summary['verified_input_bindings']),
            'public verified-input binding accounting differs')
    for reference in tuple(capture.files.values()):
        capture.bound(reference)
    auditor_path = Path(__file__).absolute()
    auditor_bytes = auditor_path.read_bytes()
    result = {
        'schema': 'independent-joint-span-publication-audit/v1', 'status': 'passed',
        'core_audit_binding': core_binding, 'summary_binding': summary_binding, 'public_ledger_binding': public_binding,
        'auditor_binding': {'path': str(auditor_path), 'bytes': len(auditor_bytes), 'sha256': hashlib.sha256(auditor_bytes).hexdigest()},
        'checked_file_count': len(capture.files), 'checked_file_bindings': list(capture.files.values()),
        'public_paired_source_seed_rows_joined_exactly': 192, 'public_policy_outcomes_joined': 384,
        'per_seed_and_split_structural_statistic_sets_recomputed': 9,
        'aggregate_structural_statistic_sets_recomputed': 1, 'resource_aggregate_recomputed': True,
        'native_full_token_encoding_rows_checked': native_encoding_rows_checked,
        'reduced_score_bank_token_rows_checked': native_encoding_rows_checked,
        'token_hash_recipes': {
            'native_encoding': 'digest(full_unicode_lexemes_including_casefold_utf8_byte_ids_plus_one)',
            'score_bank': 'digest(reduced_text_start_end_lexeme_metadata)'},
        'generated_proposal_contract_checks': grammar_proposal_occurrences_checked,
        'grammar_check_scope': 'Exact single-rule canonical fields/bounds/modality/qualifier uniqueness and pinned deontic placeholder and nonblank subject/action restrictions. Full-source-copy comparison inactive in worker codec because no source_text is supplied.',
        'exact_public_transformation': 'Remove only native modality_logits; add seed/source_position/qualifiedFalse/integerZeroMasks.',
        'recomputed_aggregate': aggregate, 'actual_root_worker_counts': numerical_counts,
        'all_authority_and_masks_preserved': True, 'torch_imported': False,
        'audit_model_calls': 0, 'audit_optimizer_updates': 0, 'audit_network_calls': 0, 'audit_prover_calls': 0,
        'semantic_target_bodies_read': False, 'semantic_accuracy_measured': False, 'source_fidelity_established': False,
        'accepted': False, 'qualified': False, 'proof_authority': False,
        'limitations': ['Uses the bound passed core audit for independent saved-score replay and literal grammar checks.',
                        'Exact public-row transport and scalar agreement do not establish numerical-score provenance or semantic fidelity.']}
    result['content_sha256'] = digest(result)
    require('torch' not in sys.modules, 'unexpected Torch import')
    with Path(output).open('xb') as stream:
        stream.write(json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False).encode() + b'\n')
    print(json.dumps({'status': 'passed', 'public_policy_outcomes_joined': 384,
                      'checked_file_count': len(capture.files), 'audit_model_calls': 0}, sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('core-audit', 'summary', 'public-ledger'):
        parser.add_argument('--' + name, type=Path, required=True)
        parser.add_argument('--' + name + '-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    audit(args.core_audit, args.core_audit_sha256, args.summary, args.summary_sha256,
          args.public_ledger, args.public_ledger_sha256, args.output)


if __name__ == '__main__':
    main()
