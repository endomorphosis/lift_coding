"""Independent standard-library replay of saved frozen joint-span results.

This auditor enumerates complete per-facet candidate lists using a full sort
and expands prefixes using sets of occupied token indices. It does not import
the selector, worker, canonical owners, Torch, or any numerical/model provider.
Integrity and structural replay are not semantic fidelity or proof evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import struct
import sys
from collections import Counter
from pathlib import Path

FIELDS = ('actor', 'action', 'object', 'conditions', 'exceptions', 'temporal')
MASKS = ('weak_decoder_fit', 'strong_semantic_fit', 'contrastive_supervision',
         'proof_supervision', 'fidelity_evaluation')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def encoded(value, *, ascii=False):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=ascii, allow_nan=False).encode('utf-8')


def digest(value, *, ascii=False):
    return hashlib.sha256(encoded(value, ascii=ascii)).hexdigest()


def rounded32(value):
    require(type(value) in (int, float) and math.isfinite(value), 'finite numeric score required')
    try:
        result = struct.unpack('>f', struct.pack('>f', value))[0]
    except (OverflowError, struct.error) as error:
        raise ValueError('finite rounded float32 score required') from error
    require(math.isfinite(result), 'finite rounded float32 score required')
    return result


def tokens(text):
    return [{'text': m.group(), 'start': m.start(), 'end': m.end()}
            for m in re.finditer(r'\w+|[^\w\s]', text, re.UNICODE)]


def decisions(heads):
    require(type(heads) is dict and set(heads) == {'start', 'end', 'presence', 'modality'},
            'closed four-head score record required')
    ranked = sorted(enumerate(heads['modality']), key=lambda pair: (-pair[1], pair[0]))
    margins = {'modality': rounded32(ranked[0][1] - ranked[1][1])}
    present = [True, True]
    for field, pair in zip(FIELDS[2:], heads['presence'], strict=True):
        margins[field] = abs(rounded32(pair[1] - pair[0]))
        present.append(pair[1] > pair[0])
    return {'modality': ('O', 'P', 'F')[ranked[0][0]], 'present': present,
            'margins': margins, 'ambiguous': any(v <= 1e-7 for v in margins.values())}


def replay(heads, present):
    """Recompute top16/beam64 result using full sorts and explicit token sets."""
    size = len(heads['start'][0])
    candidates, facets = [], {}
    union = set()
    greedy_overlaps = []
    for f, field in enumerate(FIELDS):
        if not present[f]:
            candidates.append([])
            facets[field] = {'present': False, 'enumerated_span_count': 0,
                             'retained_candidate_count': 0, 'pruned_candidate_count': 0,
                             'cutoff_tied': False, 'greedy_span': None,
                             'greedy_span_pair_score': None, 'greedy_span_logit_margin': None,
                             'retained_cutoff_pair_score': None, 'first_pruned_pair_score': None}
            continue
        scores = [(rounded32(heads['start'][f][i] + heads['end'][f][j]), (i, j))
                  for i in range(size) for j in range(i, size)]
        scores.sort(key=lambda item: (-item[0], item[1]))
        candidates.append(scores[:16])
        first = scores[0]
        positions = set(range(first[1][0], first[1][1] + 1))
        if union.intersection(positions):
            greedy_overlaps.append(field)
        union.update(positions)
        facets[field] = {
            'present': True, 'enumerated_span_count': len(scores),
            'retained_candidate_count': min(16, len(scores)),
            'pruned_candidate_count': max(0, len(scores) - 16),
            'cutoff_tied': len(scores) > 16 and scores[15][0] == scores[16][0],
            'greedy_span': list(first[1]), 'greedy_span_pair_score': first[0],
            'greedy_span_logit_margin': rounded32(first[0] - scores[1][0]) if len(scores) > 1 else None,
            'retained_cutoff_pair_score': scores[min(16, len(scores)) - 1][0],
            'first_pruned_pair_score': scores[16][0] if len(scores) > 16 else None}
    prefixes = [((), (), frozenset())]
    attempted = rejected = removed = 0
    layers = []
    for f, field in enumerate(FIELDS):
        next_prefixes = []
        local_attempted = local_rejected = 0
        for coordinates, pair_scores, occupied in prefixes:
            if not present[f]:
                local_attempted += 1
                next_prefixes.append((coordinates + (None,), pair_scores, occupied))
                continue
            for score, interval in candidates[f]:
                local_attempted += 1
                positions = frozenset(range(interval[0], interval[1] + 1))
                if positions.intersection(occupied):
                    local_rejected += 1
                    continue
                next_prefixes.append((coordinates + (interval,), pair_scores + (score,), occupied | positions))
        next_prefixes.sort(key=lambda row: (-math.fsum(row[1]),
                           tuple((-1, -1) if p is None else p for p in row[0])))
        attempted += local_attempted
        rejected += local_rejected
        pruned = max(0, len(next_prefixes) - 64)
        removed += pruned
        layers.append({'field': field, 'input_state_count': len(prefixes),
                       'feasible_expanded_state_count': len(next_prefixes),
                       'retained_state_count': min(64, len(next_prefixes)),
                       'pruned_state_count': pruned,
                       'retained_cutoff_joint_score': math.fsum(next_prefixes[min(64, len(next_prefixes)) - 1][1])
                       if next_prefixes else None,
                       'first_pruned_joint_score': math.fsum(next_prefixes[64][1])
                       if len(next_prefixes) > 64 else None,
                       'attempted_expansion_count': local_attempted,
                       'overlap_rejected_expansion_count': local_rejected,
                       'beam_boundary_tied': len(next_prefixes) > 64 and
                       math.fsum(next_prefixes[63][1]) == math.fsum(next_prefixes[64][1])})
        prefixes = next_prefixes[:64]
        if not prefixes:
            break
    best = math.fsum(prefixes[0][1]) if prefixes else None
    second = math.fsum(prefixes[1][1]) if len(prefixes) > 1 else None
    margin = best - second if second is not None else None
    ambiguous = margin is not None and margin <= 1e-7
    result = {
        'schema': 'bounded-joint-source-span-selection/v1',
        'status': 'selected' if prefixes and not ambiguous else 'abstained',
        'reason': None if prefixes and not ambiguous else 'ambiguous_joint_scores' if ambiguous
        else 'no_complete_assignment_in_retained_candidates',
        'selected_spans': [list(p) if p is not None else None for p in prefixes[0][0]]
        if prefixes and not ambiguous else None,
        'best_score': best, 'runner_up_score': second, 'joint_score_margin': margin}
    return result, {'facets': facets, 'layers': layers, 'attempted_expansion_count': attempted,
                    'overlap_rejected_expansion_count': rejected, 'pruned_beam_state_count': removed,
                    'pruned_candidate_count': sum(x['pruned_candidate_count'] for x in facets.values()),
                    'complete_retained_state_count': len(prefixes), 'greedy_overlap_fields': greedy_overlaps}


def literal(text, source_tokens, fixed, spans):
    require(type(spans) is list and len(spans) == 6, 'complete six-facet selection required')
    rule = {'modality': fixed['modality']}
    facets, occupied = {}, set()
    for field, present, interval in zip(FIELDS, fixed['present'], spans, strict=True):
        require((interval is not None) is present, 'fixed presence changed')
        atom = ''
        facet = {'present': present, 'token_start': None, 'token_end_inclusive': None,
                 'char_start': None, 'char_end': None, 'text': None}
        if present:
            left, right = interval
            require(type(left) is type(right) is int and 0 <= left <= right < len(source_tokens),
                    'invalid inclusive token coordinates')
            positions = set(range(left, right + 1))
            require(not occupied.intersection(positions), 'copied facet intervals overlap')
            occupied.update(positions)
            begin, end = source_tokens[left]['start'], source_tokens[right]['end']
            atom = text[begin:end]
            facet.update(token_start=left, token_end_inclusive=right,
                         char_start=begin, char_end=end, text=atom)
        rule[field] = ([atom] if present else []) if field in FIELDS[3:] else atom
        facets[field] = facet
    return {'rules': [rule]}, facets


class Inputs:
    def __init__(self):
        self.checked = {}

    def bound(self, reference):
        require(set(reference) == {'path', 'bytes', 'sha256'} and type(reference['bytes']) is int,
                'exact three-field binding required')
        path = Path(reference['path'])
        require(path.is_absolute() and not any(p.is_symlink() for p in (path, *path.parents)),
                'absolute nonsymlink audit input required')
        data = path.read_bytes()
        require(len(data) == reference['bytes'] and hashlib.sha256(data).hexdigest() == reference['sha256'],
                'bound file differs: ' + str(path))
        require(str(path) not in self.checked or self.checked[str(path)] == reference, 'conflicting file binding')
        self.checked[str(path)] = dict(reference)
        return data

    def read(self, path):
        path = Path(path).absolute()
        data = path.read_bytes()
        return self.json({'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})

    def json(self, reference):
        data = self.bound(reference)
        def unique_pairs(pairs):
            value = {}
            for key, item in pairs:
                require(key not in value, 'duplicate JSON key')
                value[key] = item
            return value
        value = json.loads(data.decode('utf-8'), object_pairs_hook=unique_pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))
        if 'content_sha256' in value:
            require(value['content_sha256'] == digest({k: v for k, v in value.items() if k != 'content_sha256'}),
                    'sealed audit input differs')
        return value

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


def zero_masks(value):
    require(type(value) is dict and set(value) == set(MASKS) and
            all(type(v) is int and v == 0 for v in value.values()), 'all semantic masks must be integer zero')


def validate_heads(heads, count):
    require(type(count) is int and 1 <= count <= 256, 'bounded token count required')
    require(type(heads) is dict and set(heads) == {'modality', 'presence', 'start', 'end'}, 'closed heads required')
    require(type(heads['modality']) is list and len(heads['modality']) == 3, 'three modality logits required')
    for name, rows, width in (('presence', 4, 2), ('start', 6, count), ('end', 6, count)):
        require(type(heads[name]) is list and len(heads[name]) == rows and
                all(type(row) is list and len(row) == width for row in heads[name]), 'head shapes differ')
    values = heads['modality'] + [v for name in ('presence', 'start', 'end') for row in heads[name] for v in row]
    require(all(type(v) in (int, float) and math.isfinite(v) and rounded32(v) == v for v in values),
            'captured head value is not exact finite float32')


def single_rule_contract(ir):
    """Independently check the pinned codec's bounded single-rule contract.

    One-rule CID sorting cannot reorder this AST. The current deontic grammar
    projection checks allowed modality and nonblank subject/action. No generic
    canonical owners, CID package or theorem prover is invoked here.
    """
    require(type(ir) is dict and set(ir) == {'rules'} and type(ir['rules']) is list and len(ir['rules']) == 1,
            'single exact canonical rule required')
    rule = ir['rules'][0]
    require(type(rule) is dict and set(rule) == {'modality', *FIELDS}, 'seven exact rule fields required')
    require(rule['modality'] in ('O', 'P', 'F'), 'unknown canonical modality')
    for field in ('modality', 'actor', 'action', 'object'):
        require(type(rule[field]) is str and len(rule[field]) <= 4096 and
                (field == 'object' or bool(rule[field].strip())), 'bounded canonical scalar required')
    for field in FIELDS[3:]:
        atoms = rule[field]
        require(type(atoms) is list and len(atoms) <= 1 and
                all(type(v) is str and v.strip() and len(v) <= 4096 for v in atoms) and
                atoms == sorted(set(atoms)), 'exact bounded copied qualifier required')


def validate_greedy_from_heads(row, bank):
    """Bind native greedy early-return diagnostics to captured complete heads."""
    heads, text, source_tokens = bank['heads'], bank['source_text'], bank['tokens']
    fixed = decisions(heads)
    diagnostics = row.get('span_diagnostics')
    require(diagnostics is not None and diagnostics['tokens'] == source_tokens and
            diagnostics['modality_logits'] == heads['modality'], 'greedy diagnostic token/head binding differs')
    if fixed['margins']['modality'] <= 1e-7:
        require(row['status'] == 'abstained' and row['reason'] == 'ambiguous_decoder_scores', 'greedy modality gate differs')
        return
    selected, expected_facets, occupied = [], {}, set()
    reason = None
    minimum = fixed['margins']['modality']
    size = len(source_tokens)
    for index, field in enumerate(FIELDS):
        present = fixed['present'][index]
        presence_margin = fixed['margins'][field] if index >= 2 else None
        if presence_margin is not None:
            if presence_margin <= 1e-7:
                reason = 'ambiguous_decoder_scores'
                break
            minimum = min(minimum, presence_margin)
        facet = {'present': present, 'presence_logit_margin': presence_margin,
                 'token_start': None, 'token_end_inclusive': None, 'char_start': None,
                 'char_end': None, 'text': None, 'span_logit_margin': None}
        interval = None
        if present:
            candidates = [(rounded32(heads['start'][index][i] + heads['end'][index][j]), i, j)
                          for i in range(size) for j in range(i, size)]
            candidates.sort(key=lambda p: (-p[0], p[1], p[2]))
            score, left, right = candidates[0]
            margin = rounded32(score - candidates[1][0]) if len(candidates) > 1 else None
            if margin is not None and margin <= 1e-7:
                reason = 'ambiguous_decoder_scores'
                break
            if margin is not None:
                minimum = min(minimum, margin)
            interval = [left, right]
            begin, end = source_tokens[left]['start'], source_tokens[right]['end']
            facet.update(token_start=left, token_end_inclusive=right, char_start=begin,
                         char_end=end, text=text[begin:end], span_logit_margin=margin)
            positions = set(range(left, right + 1))
            if positions.intersection(occupied):
                expected_facets[field] = facet
                reason = 'copied_spans_overlap'
                break
            occupied.update(positions)
        selected.append(interval)
        expected_facets[field] = facet
    require(diagnostics['facets'] == expected_facets, 'native greedy facet scores/spans differ from captured heads')
    if reason is not None:
        require(row['status'] == 'abstained' and row['reason'] == reason and row['canonical_ir'] is None,
                'native greedy early-abstention decision differs')
    else:
        ir, _ = literal(text, source_tokens, fixed, selected)
        single_rule_contract(ir)
        require(row['status'] == 'decoded' and row['reason'] is None and row['canonical_ir'] == ir and
                row['minimum_decision_logit_margin'] == minimum, 'native greedy complete proposal differs')


def audit(plan_path, plan_sha, batch_path, batch_sha, output):
    require('torch' not in sys.modules, 'audit must remain free of Torch')
    capture = Inputs()
    plan = capture.read(plan_path)
    plan_binding = capture.checked[str(Path(plan_path).absolute())]
    require(plan_binding['sha256'] == plan_sha and plan['schema'] == 'source-only-joint-span-plan/v1',
            'externally selected joint plan differs')
    capture.references(plan)
    zero_masks(plan['semantic_masks'])
    require(plan['policy'] == {
        'candidates_per_facet': 16, 'beam_width': 64, 'ambiguity_epsilon': 1e-7,
        'modality_and_presence': 'unchanged_native_argmax_and_float32_margin',
        'span_pair_scores': 'float32_start_plus_end', 'joint_objective': 'python_math_fsum_of_float32_pair_scores',
        'span_order': 'native_facet_order', 'optimality_scope': 'surviving_beam_only',
        'greedy_fallback': False, 'optional_facet_removal': False}, 'prespecified structural policy differs')
    base = capture.json(plan['baseline_plan_binding'])
    capture.references(base)
    require(base['schema'] == 'source-only-frozen-downstream-span-plan/v1' and
            [a['seed'] for a in base['arms']] == [1729, 1730, 1731], 'fixed original three-seed baseline differs')
    source_inputs, cohort = capture.json(base['source_inputs_binding']), capture.json(base['cohort_binding'])
    require(source_inputs['contains_formal_targets'] is cohort['contains_formal_targets'] is False,
            'source-only input metadata required')
    zero_masks(source_inputs['policy']['semantic_masks'])
    zero_masks(cohort['policy']['semantic_masks'])
    require(len(source_inputs['rows']) == len(cohort['rows']) == 64, 'complete64 source cohort required')
    sources = {r['id']: r for r in source_inputs['rows']}
    require(len(sources) == 64, 'unique64 source IDs required')
    for source, meta in zip(source_inputs['rows'], cohort['rows'], strict=True):
        require(all(source[k] == meta[k] for k in ('id', 'split', 'group_id', 'source_sha256', 'input_sha256')),
                'source/cohort identity join differs')
        require(source['id'] == 'sha256:' + digest(source['input']) and source['input_sha256'] == digest(source['input']) and
                source['source_sha256'] == hashlib.sha256(source['input']['source_text'].encode()).hexdigest(),
                'exact source ID/content hash differs')
    encoding = capture.json(base['encoding_report_binding'])
    native = capture.json(encoding['artifacts']['native768']['full_bundle'])
    require(len(native['rows']) == 64, 'native raw source vectors incomplete')
    source_profile_sha = digest(native['profile'])
    require(source_profile_sha == '151bd007468651bb720cfa60976c491e3e7cde55a06ef2336d786f9b80fe5f5e',
            'original native raw profile differs')
    raw_vectors = {}
    for row in native['rows']:
        source = sources[row['id']]
        require(row['input'] == source['input'] and row['input_sha256'] == source['input_sha256'] and
                row['encoder_text'] == source['input']['source_text'] and row['status'] == 'available' and
                len(row['vector']) == 768 and row['vector_sha256'] == digest(row['vector']), 'native source-vector binding differs')
        raw_vectors[row['id']] = row['vector']
    require(set(raw_vectors) == set(sources), 'native vector identity set differs')
    batch = capture.read(batch_path)
    batch_binding = capture.checked[str(Path(batch_path).absolute())]
    require(batch_binding['sha256'] == batch_sha and batch['schema'] == 'source-only-joint-span-batch/v1' and
            batch['successful_seeds'] == 3 and batch['selected_inputs_unchanged'] is True and
            [r['seed'] for r in batch['seeds']] == [1729, 1730, 1731], 'complete externally bound batch required')
    capture.references(batch)
    require(batch['selected']['plan'] == plan_binding and batch['selected']['worker'] == plan['helper_binding'],
            'batch worker/plan selection differs')
    all_counts = Counter()
    seed_checks = []
    outcomes = []
    for registered in batch['seeds']:
        seed = registered['seed']
        parent = capture.json(registered['parent_report_binding'])
        report = capture.json(registered['worker_report_binding'])
        require(registered['succeeded'] is True and registered['returncode'] == 0 and parent['succeeded'] is True and
                parent['selected_inputs_unchanged'] is True and parent['returncode'] == 0 and parent['failure'] is None,
                'successful bounded parent required')
        require(parent['seed'] == seed and parent['selected']['plan'] == plan_binding and
                parent['selected']['worker'] == plan['helper_binding'] and parent['process_group_cleanup_attempted'] is True,
                'parent selected command/state differs')
        capture.references(parent)
        require(report['schema'] == 'source-only-joint-span-report/v1' and report['status'] == 'completed' and
                report['seed'] == seed and report['plan_binding'] == plan_binding and report['policy'] == plan['policy'],
                'completed worker profile differs')
        capture.references(report)
        for provider in report['selected_provider_entrypoints'].values():
            capture.bound({k: provider[k] for k in ('path', 'bytes', 'sha256')})
        zero_masks(report['masks'])
        for key in ('formal_targets_read', 'training_executed', 'semantic_accuracy_measured', 'source_fidelity_established',
                    'qualified', 'accepted', 'proof_authority', 'parameter_gradients_created', 'natural_sources',
                    'pristine_holdout', 'independent_greedy_and_joint_model_forwards'):
            require(report[key] is False, 'worker authority/execution scope differs: ' + key)
        require(report['request_count'] == 64 and report['all_requests_retained'] is True and report['native768_only'] is True,
                'complete raw64 native768 cohort required')
        for key in ('new_encoder_calls', 'new_model_fits', 'proof_calls'):
            require(type(report[key]) is int and report[key] == 0, 'forbidden new numerical/semantic work reported')
        for key in ('context_contract_unchanged', 'model_state_unchanged', 'checkpoint_unchanged', 'restored_adam_unchanged',
                    'global_cpu_rng_unchanged', 'greedy_profile_unchanged'):
            require(report[key] is True, 'frozen numerical preservation assertion differs')
        arm = next(a for a in base['arms'] if a['seed'] == seed)
        require(report['checkpoint_binding'] == arm['checkpoint_binding'], 'checkpoint selection differs')
        checkpoint = capture.json(arm['checkpoint_binding'])
        require(checkpoint['config']['latent_dimension'] == 768 and checkpoint['progress']['optimizer_steps'] == 400 and
                checkpoint['config']['seed'] == seed and report['model_state_sha256'] == digest(checkpoint['model_state'], ascii=True) and
                report['saved_optimizer_state_sha256'] == digest(checkpoint['optimizer_state'], ascii=True) and
                report['original_context_contract'] == checkpoint['context_contract'], 'checkpoint/model/Adam/context digests differ')
        expected_optimizers = [
            {'role': 'embedded_source_parent', 'sha256': digest(checkpoint['source_parent_checkpoint']['optimizer_state'], ascii=True)},
            {'role': 'retained_dimensional_decoder', 'sha256': digest(checkpoint['optimizer_state'], ascii=True)}]
        require(report['restored_optimizer_state_checksums'] == expected_optimizers, 'recorded restored Adam checksums differ')
        previous = next(r for r in plan['baseline_raw_receipts'] if r['seed'] == seed)
        baseline_by_id = {}
        for split in ('train', 'development'):
            baseline = capture.json(report['baseline_summaries'][split]['receipt_binding'])
            original = capture.json(previous[split + '_binding'])
            require(baseline == original and report['baseline_summaries'][split]['exact_previous_receipt_match'] is True,
                    'complete original native greedy receipt differs')
            require(len(baseline['rows']) == baseline['eligible_count'] == 32 and baseline['decoder_call_count'] == 1,
                    'all32 greedy source calls required')
            expected_order = [s['id'] for s in source_inputs['rows'] if s['split'] == split]
            require([r['id'] for r in baseline['rows']] == expected_order, 'greedy original source ordering differs')
            baseline_by_id.update({r['id']: r for r in baseline['rows']})
        bank, ledger = capture.json(report['score_bank_binding']), capture.json(report['proposal_ledger_binding'])
        require(bank['schema'] == 'source-only-frozen-span-score-bank/v1' and ledger['schema'] == 'source-only-joint-span-proposal-ledger/v1'
                and bank['seed'] == ledger['seed'] == seed and bank['plan_binding'] == ledger['plan_binding'] == plan_binding and
                bank['contains_formal_targets'] is False and len(bank['rows']) == len(ledger['rows']) == 64,
                'complete source-only score bank and paired ledger required')
        zero_masks(bank['semantic_masks'])
        zero_masks(ledger['semantic_masks'])
        for key in ('accepted', 'qualified', 'proof_authority', 'semantic_accuracy_measured'):
            require(ledger[key] is False, 'paired ledger authority differs')
        expected_order = [r['id'] for split in ('train', 'development') for r in source_inputs['rows'] if r['split'] == split]
        require([r['id'] for r in bank['rows']] == [r['id'] for r in ledger['rows']] == expected_order,
                'captured score and ledger identity ordering differs')
        transitions = Counter()
        reasons = Counter()
        incomplete = proposals = greedy_proposals = preserved = rescued = joint_calls = 0
        search_totals = Counter()
        for index, (score, pair) in enumerate(zip(bank['rows'], ledger['rows'], strict=True)):
            source, native_row = sources[score['id']], baseline_by_id[score['id']]
            text = source['input']['source_text']
            source_tokens = tokens(text)
            require(score['seed'] == seed and score['control'] == 'raw_source' and score['capture_index'] == index and
                    score['id'] == pair['id'] and score['source_text'] == pair['source_text'] == text and
                    score['split'] == pair['split'] == source['split'] and score['source_sha256'] == pair['source_sha256'] == source['source_sha256'],
                    'sequential captured source/seed/control identity differs')
            require(score['request_sha256'] == native_row['request_sha256'] and
                    score['latent_sha256'] == pair['latent_sha256'] == native_row['effective_latent_sha256'] == digest(raw_vectors[score['id']], ascii=True) and
                    native_row['latent_donor_id'] == score['id'], 'captured request and exact raw conditioner binding differs')
            request = {'id': source['id'], 'source_text': text, 'context_text': '', 'requires_context_resolution': False}
            require(score['request_sha256'] == digest(request) and score['profile_sha256'] == source_profile_sha,
                    'complete request/raw profile hash differs')
            require(score['tokens'] == source_tokens and pair['score_row_sha256'] == digest(score),
                    'exact token bank/digest binding differs')
            require(score['input_sha256'] == source['input_sha256'] and score['token_input_sha256'] == digest(source_tokens),
                    'captured input/token hash differs')
            validate_heads(score['heads'], len(source_tokens))
            require(pair['greedy'] == native_row['decoder_row'], 'paired greedy row differs from original receipt')
            validate_greedy_from_heads(pair['greedy'], score)
            fixed = decisions(score['heads'])
            joint = pair['joint']
            require(joint['fixed_decisions'] == fixed, 'joint modality/presence decisions differ')
            for key in ('accepted', 'source_fidelity_established', 'independent_semantic_review_completed', 'proof_authority'):
                require(pair[key] is False, 'paired result authority differs')
            if fixed['ambiguous']:
                require(joint['search'] is None and joint['status'] == 'abstained' and
                        joint['reason'] == 'ambiguous_fixed_decision_scores', 'fixed decision ambiguity differs')
            else:
                joint_calls += 1
                reconstructed, diagnostics = replay(score['heads'], fixed['present'])
                actual = joint['search']
                require(type(actual) is dict and set(actual) == {*reconstructed, 'diagnostics'} and
                        all(actual[k] == v for k, v in reconstructed.items()), 'independent bounded search decision differs')
                for key, value in diagnostics.items():
                    require(actual['diagnostics'][key] == value, 'independent search accounting differs: ' + key)
                metadata = actual['diagnostics']
                require(metadata['token_count'] == len(source_tokens) and metadata['candidates_per_facet'] == 16 and
                        metadata['beam_width'] == 64 and metadata['confidence_scope'] == 'retained_complete_beam_only' and
                        metadata['global_optimality_established'] is False and
                        metadata['incomplete_search'] is bool(diagnostics['pruned_candidate_count'] or diagnostics['pruned_beam_state_count']),
                        'bounded search interpretation differs')
                for key in ('target_access', 'teacher_forcing', 'training_executed', 'grammar_validation_performed',
                            'source_fidelity_verified', 'qualified', 'accepted', 'proof_authority'):
                    require(metadata[key] is False, 'selector authority scope differs')
                require(metadata['attempted_expansion_count'] <= metadata['expansion_count_upper_bound'] == 6144,
                        'beam expansion bound exceeded')
                require(metadata['native_head_value_count'] == 12 * len(source_tokens) and
                        metadata['enumerated_span_count_upper_bound'] == 3 * len(source_tokens) * (len(source_tokens) + 1) and
                        metadata['peak_feasible_expanded_state_count'] == max(x['feasible_expanded_state_count'] for x in diagnostics['layers']) and
                        metadata['peak_feasible_expanded_state_count'] <= 1024, 'head/expanded-state resource bound differs')
                incomplete += metadata['incomplete_search']
                for key in ('attempted_expansion_count', 'overlap_rejected_expansion_count', 'pruned_candidate_count', 'pruned_beam_state_count'):
                    search_totals[key] += metadata[key]
                if reconstructed['status'] == 'selected':
                    ir, facets = literal(text, source_tokens, fixed, reconstructed['selected_spans'])
                    single_rule_contract(ir)
                    require(joint['status'] == 'proposal' and joint['reason'] is None and joint['canonical_ir'] == ir and
                            joint['facets'] == facets and joint['family_syntax_checked'] is True,
                            'exact non-overlapping copied canonical joint proposal differs')
                else:
                    require(joint['status'] == 'abstained' and joint['reason'] == reconstructed['reason'] and
                            joint['canonical_ir'] is None and joint['facets'] is None and joint['family_syntax_checked'] is False,
                            'joint abstention contains a promoted proposal')
            transitions[pair['greedy']['status'] + '->' + joint['status']] += 1
            if joint['reason'] is not None:
                reasons[joint['reason']] += 1
            greedy_proposals += pair['greedy']['status'] == 'decoded'
            proposals += joint['status'] == 'proposal'
            preserved += pair['greedy']['status'] == 'decoded' and joint['status'] == 'proposal' and pair['greedy']['canonical_ir'] == joint['canonical_ir']
            rescued += pair['greedy']['reason'] == 'copied_spans_overlap' and joint['status'] == 'proposal'
            outcomes.append({'seed': seed, 'split': source['split'], 'id': source['id'],
                             'greedy_status': pair['greedy']['status'], 'greedy_reason': pair['greedy']['reason'],
                             'joint_status': joint['status'], 'joint_reason': joint['reason']})
        require(report['joint_proposals'] == proposals and report['greedy_proposals'] == greedy_proposals and
                report['joint_reason_counts'] == dict(reasons) and report['transition_counts'] == dict(transitions) and
                report['search_incomplete_rows'] == incomplete, 'worker structural aggregate differs')
        expected_counts = {'optimizer_step_attempts': 0, 'optimizer_updates': 0, 'dimensional_restores': 1,
                           'embedded_parent_restores': 1, 'model_constructors': 3, 'wrapper_calls': 2,
                           'owner_decoder_calls': 2, 'source_row_decode_calls': 64, 'actual_model_forward_calls': 64,
                           'joint_selection_calls': joint_calls, 'joint_additional_model_forward_calls': 0}
        require(all(type(v) is int for v in report['counts'].values()) and report['counts'] == expected_counts,
                'single-forward/source and frozen restoration counters differ')
        all_counts.update(report['counts'])
        seed_checks.append({'seed': seed, 'worker_report_binding': registered['worker_report_binding'],
                            'parent_report_binding': registered['parent_report_binding'],
                            'raw_greedy_proposals': greedy_proposals, 'joint_structural_proposals': proposals,
                            'greedy_proposals_preserved_exactly': preserved, 'overlap_abstentions_rescued_structurally': rescued,
                            'transition_counts': dict(transitions), 'joint_reason_counts': dict(reasons),
                            'search_incomplete_rows': incomplete, 'search_counter_totals': dict(search_totals),
                            'source_rows_replayed': 64, 'native_head_bound_greedy_rows_checked': 64,
                            'all64_source_vector_token_digest_joins_exact': True, 'complete_original_baseline_receipts_exact': True})
    require(dict(all_counts) == batch['completed_worker_counts'] and all_counts['actual_model_forward_calls'] == 192,
            'batch completed-worker counts differ')
    for reference in tuple(capture.checked.values()):
        capture.bound(reference)
    result = {
        'schema': 'independent-source-only-joint-span-audit/v1', 'status': 'passed',
        'plan_binding': plan_binding, 'batch_binding': batch_binding, 'seed_checks': seed_checks,
        'checked_file_bindings': list(capture.checked.values()), 'checked_file_count': len(capture.checked),
        'actual_root_worker_counts': dict(all_counts), 'native_head_records_checked': 192,
        'paired_source_seed_occurrences': 192, 'policy_outcomes_checked': 384,
        'independent_algorithm': 'full_candidate_sort_and_token_set_beam_prefix_expansion/v1',
        'single_rule_grammar_validation_scope': 'independent_exact_seven_field_single_rule_contract_and_nonblank_deontic_projection_only',
        'source_literal_copy_and_global_nonoverlap_checked': True,
        'fixed_native_modality_and_presence_choices_checked': True,
        'complete_prior_raw_receipts_exact': True, 'all64_denominators_retained_per_seed': True,
        'policy_outcomes': outcomes, 'torch_imported': False, 'audit_model_calls': 0,
        'audit_optimizer_updates': 0, 'audit_network_calls': 0, 'audit_prover_calls': 0,
        'semantic_target_bodies_read': False, 'independent_semantic_reviews_created': 0,
        'semantic_accuracy_measured': False, 'source_fidelity_established': False,
        'accepted': False, 'qualified': False, 'proof_authority': False,
        'limits': ['Saved head origin and correctness are not independently attested.',
                   'Checkpoint file/digest consistency and recorded state-preservation assertions are checked; no numerical model is restored by this auditor.',
                   'Selected source/provider entrypoint bindings are not a complete binary dependency closure.',
                   'Top16/beam64 replay confirms a bounded approximate structural policy; it does not establish global optimality or calibrated confidence.',
                   'Literal copying, non-overlap and bounded grammar validity do not establish semantic fidelity.']}
    result['content_sha256'] = digest(result)
    require('torch' not in sys.modules, 'unexpected Torch import during pure audit')
    with Path(output).open('xb') as stream:
        stream.write(json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False).encode() + b'\n')
    print(json.dumps({'status': 'passed', 'output': str(output), 'checked_file_count': len(capture.checked),
                      'paired_source_seed_occurrences': 192, 'audit_model_calls': 0}, sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('plan', 'batch'):
        parser.add_argument('--' + name, type=Path, required=True)
        parser.add_argument('--' + name + '-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    audit(args.plan, args.plan_sha256, args.batch, args.batch_sha256, args.output)


if __name__ == '__main__':
    main()
