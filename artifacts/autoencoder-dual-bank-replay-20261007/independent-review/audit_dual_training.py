"""Independent stdlib saved-output audit of a completed matched384 fit.

No numerical owner/model import, forward, fitting, or resource operation.
Completion is required before any training-attempt body is read.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import struct
import time

PURE_PATH = Path('/home/barberb/lift_coding/artifacts/autoencoder-balanced-wording-20261007/preflight-review/audit_preflight-r2.py')
PURE_SHA = '260a51b7526003b199b627a7e1a3f7e9e9e96ad85b4fe37d2acc7779890861d6'
if hashlib.sha256(PURE_PATH.read_bytes()).hexdigest() != PURE_SHA:
    raise ValueError('Independent pure saved-output arithmetic changed')
spec = importlib.util.spec_from_file_location('_independent_pure_preflight_arithmetic', PURE_PATH)
pure = importlib.util.module_from_spec(spec); spec.loader.exec_module(pure)
raw, digest, close = pure.raw, pure.digest, pure.close
FIELDS, FACETS, ROLES, PARENT = pure.FIELDS, pure.FACETS, pure.ROLES, pure.PARENT
PANELS = ('training', 'validation', 'zero-condition', 'source-shuffle', 'context-only-shuffle',
          'cross-length-shuffle', 'context-reverse', 'context-rotate', 'recurrent-residual-off')
FALSE = {'qualified', 'admitted', 'proof_authority', 'source_semantics_verified', 'formalized',
         'checkpoint_promoted', 'roundtrip_ok', 'proof_ready', 'convergence_proven', 'fresh_holdout',
         'encoder_executed', 'downloads_performed', 'lake_executed', 'native_family_validation_performed',
         'used_for_selection', 'normalization_refitted', 'decoder_rows_replaced', 'full_targets_truncated',
         'encoder_context_changed', 'count_metrics_used_for_selection', 'source_value_metrics_used_for_selection',
         'action_contrastive_used_for_selection', 'generated_boundary_used_for_selection'}


def false_masks(value):
    if type(value) is dict:
        for key, child in value.items():
            if key in FALSE and child is not False: raise ValueError('Unsupported qualification/ownership flag: ' + key)
            false_masks(child)
    elif type(value) is list:
        for child in value: false_masks(child)


def shape_flat(value):
    if type(value) is not list: return [], [value]
    parts = [shape_flat(v) for v in value]
    if not parts or any(p[0] != parts[0][0] for p in parts): raise ValueError('Ragged/empty serialized tensor')
    return [len(value)] + parts[0][0], [v for p in parts for v in p[1]]


def typed_tensor_digest(state):
    """Reconstruct typed contiguous bytes in stdlib, without tensor objects.

    Frozen state declares32 tensors and uses float32/int64; tolist preserves
    distinct Python float/int types, including signed floating zero.
    """
    result = hashlib.sha256()
    for name, value in sorted(state.items()):
        shape, values = shape_flat(value); kinds = {type(v) for v in values}
        if len(kinds) != 1 or next(iter(kinds)) not in (float, int, bool): raise ValueError('Ambiguous tensor dtype')
        kind = next(iter(kinds)); dtype, fmt = {float: ('torch.float32', 'f'), int: ('torch.int64', 'q'), bool: ('torch.bool', '?')}[kind]
        if any(type(v) is float and not math.isfinite(v) for v in values): raise ValueError('Nonfinite state value')
        result.update(raw([name, dtype, shape]).encode()); result.update(struct.pack('<' + fmt * len(values), *values))
    return result.hexdigest()


def strict_json(text):
    def unique(pairs):
        result = {}
        for k, v in pairs:
            if k in result: raise ValueError('Duplicate generated JSON key')
            result[k] = v
        return result
    def invalid(v): raise ValueError('Nonfinite generated JSON constant')
    return json.loads(text, object_pairs_hook=unique, parse_constant=invalid)


def formula_counts(gold, prediction, vocabulary):
    tokens = prediction['token_ids']; status = prediction['generation_status']; eos = prediction['eos_reached']
    if len(tokens) > 511 or any(type(t) is not int or not 3 <= t < 32 for t in tokens): raise ValueError('Generated content outside512/full32 budget')
    if eos is not (status == 'eos') or status not in ('eos', 'output_limit', 'invalid_special_token') or eos and len(tokens)+2 > 512: raise ValueError('Generation EOS/status budget mismatch')
    try: generated = strict_json(''.join(vocabulary[t] for t in tokens))
    except ValueError: generated = None
    actual = generated['rules'] if type(generated) is dict and set(generated) == {'rules'} and type(generated['rules']) is list and len(generated['rules']) <= 32 else None
    valid = {i: r for i, r in enumerate(actual or []) if type(r) is dict and set(r) == set(FACETS) and r['modality'] in ('O', 'P', 'F') and all(type(r[f]) is str and bool(r[f]) and r[f].isprintable() and len(r[f]) <= 512 for f in FIELDS) and all(type(r[f]) is list and len(r[f]) <= 4 and all(type(v) is str for v in r[f]) and r[f] == sorted(set(r[f])) for f in FACETS[4:])}
    expected = Counter(raw(r) for r in gold['rules']); emitted = Counter(raw(r) for r in valid.values()); matched = sum((expected & emitted).values())
    syntax = actual is not None and bool(actual) and len(actual) == len(valid); n = len(actual or [])
    preserved = syntax and eos and matched == len(gold['rules']) == n; ordered = syntax and eos and generated == gold
    counts = dict(rows=1, expected_rules=len(gold['rules']), generated_rules=n, valid_generated_rules=len(valid), syntax_valid=int(syntax), parsed_documents=int(actual is not None), eos_count=int(eos), ordered_exact=int(ordered), all_rules_preserved=int(preserved), whole_rules_missing=len(gold['rules'])-matched, whole_rules_extra=n-matched, duplicate_rules=sum(max(0, v-1) for v in emitted.values()), order_mismatch_rows=int(preserved and not ordered), invalid_rule_count=n-len(valid), invalid_rows=int(not syntax), unscorable_generation_rows=int(actual is None), prediction_missing_rows=0)
    facets = {f: dict(correct=sum(i in valid and valid[i][f] == r[f] for i, r in enumerate(gold['rules'])), total=len(gold['rules']), unordered_correct=sum((Counter(raw(r[f]) for r in gold['rules']) & Counter(raw(r[f]) for r in valid.values())).values())) for f in FACETS}
    return generated, counts, facets


def source_readout(report, bank, codec, tensor_sha, check):
    vocab = codec['target_vocabulary']; fields = defaultdict(list); wrong = []
    check('Full180 source readout identity', report['complete'] is True and report['model_tensor_sha256'] == tensor_sha and report['row_count'] == 180 and report['reference_fields'] == 720 and len(report['rows']) == 180 and report['optimizer_steps'] == report['extra_source_forwards'] == 0 and report['source_targets_joined_after_numeric_return'] is True)
    for row, observed in zip(bank['rows'], report['rows'], strict=True):
        check('Source readout original/authentic identity', observed['row_id'] == row['id'] and observed['source_sha256'] == row['source_sha256'] and observed['original_rule_sha256'] == digest(row['target']) and observed['template'] == row['template'])
        for field in FIELDS:
            v = observed['fields'][field]; target = vocab.index(json.dumps(row['target'][field], ensure_ascii=False, separators=(',', ':'))); expected = pure.metrics(v['full32_logits'], target)
            check('Full32 source readout metric', v['target_token_id'] == target and v['correct'] is (expected['argmax_token_id'] == target) and close(v, dict(argmax_token_id=expected['argmax_token_id'], margin=expected['target_minus_best_other'], cross_entropy=expected['full_vocabulary_cross_entropy'])))
            fields[field].append(v)
            if not v['correct']: wrong.append(dict(row_id=row['id'], source_text=row['source_text'], field=field, target=row['target'][field], predicted_token=vocab[v['argmax_token_id']], margin=v['margin']))
    by_field = {f: dict(correct=sum(v['correct'] for v in values), total=180, cross_entropy=math.fsum(v['cross_entropy'] for v in values)/180, minimum_target_margin=min(v['margin'] for v in values)) for f, values in fields.items()}
    check('All720 bank field aggregates exact', close(report['by_field'], by_field))
    inherited = report['inherited_modality_readout']; groups = defaultdict(list)
    check('Inherited source modality provenance and30 passes', inherited['bank_sha256'] == bank['bank_sha256'] and inherited['model_tensor_sha256'] == tensor_sha and inherited['complete'] is True and inherited['source_head_forward_calls'] == 30 and inherited['optimizer_steps'] == 0 and inherited['full_vocabulary_size'] == 32)
    for row, v, inherited_row in zip(bank['rows'], fields['modality'], inherited['rows'], strict=True):
        check('Inherited full32 modality vectors identical', inherited_row['id'] == row['id'] and inherited_row['full_vocabulary_logits'] == v['full32_logits'] and inherited_row['target_token_id'] == v['target_token_id'] and inherited_row['correct'] is v['correct'] and math.isclose(inherited_row['cross_entropy'], v['cross_entropy'], abs_tol=1e-6, rel_tol=1e-5))
        for key in ('all', 'modality:'+row['modality'], 'template:'+row['template'], 'stratum:'+row['modality']+':'+row['template']): groups[key].append(inherited_row)
    check('Source modality groups all strata exact', set(groups) == set(inherited['groups']) and all(close(inherited['groups'][key], dict(rows=len(values), correct=sum(v['correct'] for v in values), cross_entropy=sum(v['cross_entropy'] for v in values)/len(values))) for key, values in groups.items()))
    false_masks(report)
    return dict(clauses=180, scalar_sites=720, full_vocabulary_size=32, by_field=by_field, wrong_source_sites=wrong, actual_greedy_formula_panel=False)


def loss_receipt(receipt, check):
    logits, targets, losses = receipt['full_vocabulary_logits'], receipt['target_token_ids'], receipt['per_row_cross_entropy']
    check('Full32 six-source gradient owner', receipt['full_vocabulary_size'] == 32 and receipt['batch_size'] == len(logits) == len(targets) == len(losses) == 6 and receipt['source_slot'] == 0 and receipt['loss_field'] == 'modality' and receipt['source_head_forward_calls'] == 1 and receipt['recurrent_forward_calls'] == receipt['count_forward_calls'] == 0 and receipt['labels_passed_to_model'] is receipt['model_copied'] is receipt['sampler_state_advanced'] is False)
    independent = [pure.metrics(values, target) for values, target in zip(logits, targets, strict=True)]
    check('Stored full32 per-source CE independent arithmetic', all(math.isclose(loss, m['full_vocabulary_cross_entropy'], abs_tol=2e-6, rel_tol=2e-5) for loss, m in zip(losses, independent)) and receipt['correct'] == sum(m['argmax_token_id'] == t for m, t in zip(independent, targets)) and math.isclose(receipt['mean_cross_entropy'], sum(losses)/6, abs_tol=2e-6, rel_tol=2e-5))
    return len(logits)


def audit(attempt, output, completed):
    if not completed: raise ValueError('Explicit root training completion signal required before attempt outputs')
    started = time.monotonic(); attempt = Path(attempt).resolve(); run = attempt.parent
    if not re.fullmatch(r'training-384-r[1-9][0-9]*', attempt.name): raise ValueError('Explicit matched native384 training attempt required')
    reader = pure.Reader(); checks = []
    def check(name, ok, detail=None):
        if not ok: raise ValueError(name)
        item = dict(check=name, passed=True)
        if detail is not None: item['detail'] = detail
        checks.append(item)
    manifest = reader.json(run/'training-manifest.json'); plan = reader.json(run/'training-plan.json'); profile = plan['training_profile']
    check('Exact frozen plan/input closure', manifest['plan_sha256'] == reader.bindings[str(run/'training-plan.json')]['sha256'] and plan['input_sha256'] == manifest['inputs'])
    for path, wanted in manifest['inputs'].items(): reader.body(path, {'sha256':wanted})
    for relative, wanted in manifest['extensions'].items(): reader.body(run/'experiment-source'/relative, {'sha256':wanted})
    result = reader.json(attempt/'results/summary.json')
    check('Completed one-arm384 bounded dual replay recipe', result['complete'] is True and result['phase'] == 'training' and result['dimension'] == 384 and result['training_executed'] is True and result['fits'] == 1 and len(result['runs']) == 1 and result['parent_tensor_sha256'] == PARENT and result['reference_rows_unavailable_to_selection'] == ['balanced48','sealed60','exposed-v3'] and result['selection_unchanged'] is result['original_decoder_rows_unchanged'] is True and result['preprocessing_refitted'] is False)
    check('FixedCPU/output/context/budget profile', profile['optimizer_steps_per_fit'] == 170 and profile['row_presentations_per_fit'] == profile['count_presentations_per_fit'] == 1220 and profile['target_token_presentations_per_fit'] == 112920 and profile['source_value_presentations_per_fit'] == 12800 and profile['original_used113_presentations_per_fit'] == profile['new_auxiliary_presentations_per_fit'] == 1020 and profile['native_context_tokens'] == profile['output_tokens'] == 512 and profile['temperature'] == 0 and profile['source_auxiliary_weight'] == .05)
    false_masks(result)
    parent = reader.json(manifest['parent_summary']); parent_state = reader.ref(parent['states']['selected']); baseline = reader.ref(parent['training_ref'])
    check('Exact E selected parent typed bytes', typed_tensor_digest(parent_state['model_state']) == parent_state['tensor_sha256'] == PARENT and parent_state['weights_sha256'] == digest(parent_state['model_state']))
    original_candidates = [p for p in manifest['inputs'] if p.endswith('/384/training-rows.json')]
    originals = None
    for path in original_candidates:
        value = reader.json(path)
        if digest(value['train']) == baseline['training_rows_sha256'] and digest(value['validation']) == baseline['validation_rows_sha256']:
            if originals is not None and originals != value: raise ValueError('Conflicting original cohorts')
            originals = value
    check('Original48 TRAIN/48 validation unchanged', originals is not None and len(originals['train']) == len(originals['validation']) == 48)
    rowmap = pure.unique(originals['train'], lambda r:r['id']); codec = parent_state['codec']; vocabulary = codec['target_vocabulary']
    gold_by_split = {split:{r['id']:strict_json(''.join(vocabulary[t] for t in r['target_ids'][1:-1])) for r in originals[split]} for split in ('train','validation')}
    check('Both original cohorts180 rules/seven facets', all(sum(len(g['rules']) for g in gold.values()) == 180 for gold in gold_by_split.values()))
    pairing = reader.ref(result['pairing']); check('Paired draws sealed and170 complete', pairing['pairing_sha256'] == digest({k:v for k,v in pairing.items() if k!='pairing_sha256'}) and len(pairing['draws']) == 170)
    banks = {role:reader.json(attempt/'results'/(role+'-bank.json')) for role in ROLES}
    for role, bank in banks.items():
        check('Complete authenticated180 source bank: '+role, bank['bank_sha256'] == digest({k:v for k,v in bank.items() if k!='bank_sha256'}) and len(bank['rows']) == 180 and pairing['banks'][role]['bank_sha256'] == bank['bank_sha256'])
    dual_schedule=reader.ref(result['dual_source_schedule'])
    check('Exact sealed dual170draw declaration',dual_schedule['schedule_sha256']==digest({k:v for k,v in dual_schedule.items() if k!='schedule_sha256'}) and len(dual_schedule['draws'])==170 and dual_schedule['original_pairing_sha256']==pairing['pairing_sha256'])
    arms = pure.unique([reader.ref(ref) for ref in result['runs']],lambda r:r['arm'])
    check('One authentic dual replay arm retained', set(arms)=={'dual-bank-retention-ce'})
    arm_summaries = {}; panel_paths = set(); bank_site_count = full32_training_count = 0
    for role in ('dual',):
        arm = arms['dual-bank-retention-ce']; report = reader.ref(arm['training_ref']); updates = report['committed_updates']
        states = {key:reader.ref(ref) for key,ref in arm['states'].items()}
        check('Three endpoint states/parent/fresh optimizer declaration: '+role, set(states)=={'initial','selected','last-attempt'} and arm['initial_tensor_sha256']==PARENT and arm['parent_state']==parent['states']['selected'] and arm['fresh_optimizer'] is arm['fresh_scheduler'] is True and arm['exact_optimizer_resume'] is False and arm['budget_completed'] is True and arm['original_panels_physically_evaluated_for_both_roles'] is True)
        for state_role,state in states.items():
            check('Endpoint typed tensor/hash closure: '+role+'/'+state_role, state['tensor_sha256']==arm['states'][state_role]['tensor_sha256']==typed_tensor_digest(state['model_state']) and state['weights_sha256']==digest(state['model_state']) and state['codec']==codec and state['input_transform']==parent_state['input_transform'] and state['architecture']==parent_state['architecture'] and state['dimension']==384 and state['optimizer_resumable'] is False)
            false_masks(state)
        check('Identical parent weights and endpoint report hashes: '+role, states['initial']['model_state']==parent_state['model_state'] and states['initial']['tensor_sha256']==report['initial_weights_sha256']==PARENT and states['selected']['tensor_sha256']==report['selected_weights_sha256'] and states['last-attempt']['tensor_sha256']==report['last_complete_attempt_weights_sha256'] and arm['selected_last_tensor_alias'] is (states['selected']['tensor_sha256']==states['last-attempt']['tensor_sha256']))
        check('Exact170/1220/112920/12800 original budgets: '+role, report['stopped_reason']=='epochs_completed' and report['optimizer_steps']==len(updates)==170 and report['row_presentations']==report['count_training_row_presentations']==1220 and report['valid_target_token_presentations']==112920 and report['source_value_presentations']==12800 and report['count_training_presentations_by_class']=={'1':305,'2':305,'4':305,'8':305})
        check('Frozen preprocessing/TRAIN labels and source/count ownership: '+role, all(report[key]==baseline[key] for key in ('training_rows_sha256','validation_rows_sha256','training_references_sha256','validation_references_sha256','codec_sha256','source_contexts_sha256','count_training_inventory_sha256')) and report['frozen_parameters_verified'] is True and report['source_context_target_access'] is report['count_reference_documents_passed_to_model'] is report['source_value_reference_documents_passed_to_model'] is report['source_value_validation_rows_used_for_training'] is report['count_validation_rows_used_for_training'] is False)
        check('Fresh optimizer/scheduler and unchanged configured losses: '+role, report['optimizer_instance_count']==1 and report['optimizer_reinitialized_between_stages'] is report['optimizer_resumable'] is False and report['config']['learning_rate']==.0001 and report['config']['seed']==1729 and report['config']['batch_size']==8 and report['config']['alpha']==0. and report['config']['max_target_tokens']==512 and report['non_action_learning_rate_multiplier']==10. and report['cardinality_weight']==report['source_value_weight']==.25 and report['action_contrastive_weight']==report['generated_boundary_weight']==.05 and report['selection']=='per_length_nonregression_then_fidelity_progress_then_reference_ce')
        stages=report['stage_reports'];check('Fresh moments at first stage and continuous stages', stages[0]['optimizer_step_start']==0 and stages[0]['optimizer_state_start']=={'moment_state_sha256':hashlib.sha256(b'').hexdigest(),'parameter_steps':{}} and stages[0]['optimizer_group_learning_rates_start']=={'base':.0001,'non_action_head':.001} and all(a['optimizer_state_end']==b['optimizer_state_start'] and a['optimizer_step_end']==b['optimizer_step_start'] for a,b in zip(stages,stages[1:])) and stages[-1]['optimizer_step_end']==170 and all(s['status']=='complete' for s in stages))
        for name in report['frozen_parameter_names']:
            check('Frozen parameter bytes persist: '+name, states['initial']['model_state'][name]==states['selected']['model_state'][name]==states['last-attempt']['model_state'][name])
        auxiliary = report['paraphrase_modality_auxiliary']
        inherited=reader.ref(arm['inherited_training_ref'])
        check('Preserved numerical inherited report unchanged',report['dual_bank_receipt_reconciliation']['inherited_report_canonical_sha256']==digest(inherited) and all(v==report[k] for k,v in inherited.items() if k!='paraphrase_modality_auxiliary') and inherited['committed_updates']==report['committed_updates'])
        check('Same170positive1020 dualsource presentations',auxiliary['schema']=='dual-authored-wording-training-summary/v1' and auxiliary['weight']==.05 and auxiliary['committed_updates']==170 and auxiliary['committed_clause_presentations']==auxiliary['positively_supervised_clause_presentations']==1020 and auxiliary['committed_presentations_per_modality']=={'O':340,'P':340,'F':340} and auxiliary['zero_weight_graph_attached'] is False and auxiliary['cache_receipt']['schema']=='dual-authored-wording-modality-cache/v1' and auxiliary['cache_receipt']['schedule_sha256']==dual_schedule['schedule_sha256'] and auxiliary['cache_receipt']['bank_count']==2 and auxiliary['cache_receipt']['max_local_uses_per_bank']==85 and auxiliary['cache_receipt']['model_copied'] is auxiliary['cache_receipt']['tensors_copied'] is False)
        check('Authentic cache receipts keep each bank local ownership',set(auxiliary['cache_receipt']['authentic_caches_by_role'])==set(ROLES) and all(c['bank_sha256']==banks[r]['bank_sha256'] and c['pairing_role']==r and c['orders']==pairing['orders'][r] and c['pairing_sha256']==pairing['pairing_sha256'] and c['fresh_immutable_cache'] is True and c['prepared_cache_mutated'] is False for r,c in auxiliary['cache_receipt']['authentic_caches_by_role'].items()))
        check('Observed attempts separate from committed receipts',auxiliary['forward_attempts']>=auxiliary['completed_forward_observations']>=170 and auxiliary['observed_clause_presentations']==6*auxiliary['completed_forward_observations'] and auxiliary['completed_forward_observations']==170+len(auxiliary['uncommitted_observations']))
        check('Unchanged used113 positive1020 source presentations',report['auxiliary_source_modality_weight']==.05 and report['auxiliary_source_modality_presentations']==1020 and report['auxiliary_source_modality_committed_updates']==170 and report['auxiliary_source_modality_used_for_selection'] is False and report['auxiliary_source_modality_encoder_executed'] is False)
        decoder_hash=hashlib.sha256();count_hash=hashlib.sha256();rows_seen=tokens_seen=source_seen=0;count_classes=Counter();weighted_losses=[];base_losses=[];source_ces=[];exposures={r:Counter() for r in ROLES};bank_updates=Counter();template_exposures=Counter()
        for index,(update,old,draw) in enumerate(zip(updates,baseline['committed_updates'],dual_schedule['draws'],strict=True)):
            check('Original decoder/count/used113 draw and target parity', update['decoder_row_ids']==old['decoder_row_ids'] and update['count_row_ids']==old['count_row_ids'] and all(update['auxiliary_source_modality']['receipt'][key]==old['auxiliary_source_modality']['receipt'][key] for key in ('row_ids','source_sha256','target_token_ids','indices','strata')) and update['optimizer_step']==index+1)
            decoder_hash.update(raw(update['decoder_row_ids']).encode());count_hash.update(raw(update['count_row_ids']).encode())
            rows_seen+=len(update['decoder_row_ids']);expected_tokens=sum(len(rowmap[i]['target_ids'])-1 for i in update['decoder_row_ids']);expected_sources=sum(len(gold_by_split['train'][i]['rules'])*4 for i in update['decoder_row_ids']);tokens_seen+=expected_tokens;source_seen+=expected_sources
            count_classes.update(str(len(gold_by_split['train'][i]['rules'])) for i in update['count_row_ids'])
            check('Per-update target and scalar presentations exact',update['target_token_presentations']==expected_tokens and update['source_value_presentations']==expected_sources)
            item=update['paraphrase_modality_auxiliary'];wrapper=item['receipt'];bank_role='control' if index%2==0 else 'balanced';local=index//2;receipt=wrapper['authentic_receipt'];indices=[order[local%30] for order in pairing['orders'][bank_role]];source_rows=[banks[bank_role]['rows'][i] for i in indices]
            check('Authentic global/local dual committed wrapper',wrapper['schema']=='dual-authored-wording-modality-loss/v1' and wrapper['global_committed_step']==index and wrapper['bank_role']==bank_role and wrapper['bank_local_committed_step']==local and wrapper['selected_bank_sha256']==banks[bank_role]['bank_sha256'] and wrapper['schedule_sha256']==dual_schedule['schedule_sha256'] and wrapper['authentic_receipt_sha256']==digest(receipt) and wrapper['local_receipt_relabelled'] is False and draw['bank_role']==bank_role and draw['indices']==indices)

            check('Actual170 paired gradient draws/authentic sources',item['zero_based_committed_step']==index and receipt['committed_step']==local and item['weight']==.05 and receipt['gradient_enabled'] is True and receipt['bank_sha256']==banks[bank_role]['bank_sha256'] and receipt['indices']==indices and receipt['row_ids']==[r['id'] for r in source_rows] and receipt['source_sha256']==[r['source_sha256'] for r in source_rows] and receipt['target_token_ids']==[r['modality_token_id'] for r in source_rows] and [[r['modality'],r['template']] for r in receipt['strata']]==[[r['modality'],r['template']] for r in source_rows] and [digest(r['target']) for r in source_rows]==draw['original_rule_sha256'])
            full32_training_count+=loss_receipt(receipt,check);full32_training_count+=loss_receipt(update['auxiliary_source_modality']['receipt'],check)
            check('Weighted auxiliary objective arithmetic float32',math.isclose(item['weighted_loss'],pure.f32(.05*receipt['mean_cross_entropy']),abs_tol=1e-7,rel_tol=1e-6) and math.isclose(update['objective'],pure.f32(item['base_objective']+item['weighted_loss']),abs_tol=2e-7,rel_tol=1e-6))
            check('Full original objective values finite and identity MSE explicitly separate',all(type(update[k]) in (int,float) and math.isfinite(update[k]) for k in ('token_ce','weighted_token_ce','count_ce','source_value_ce','objective','preclip_norm','raw_reconstruction_mse')) and update['raw_reconstruction_mse']==0.)
            boundary=update['generated_boundary'];check('Strict actual generated boundary retry/reference policy',boundary['retry_enabled'] is boundary['replay_logits_match_collection'] is True and boundary['retry_limit_per_original_batch']==1 and boundary['additional_optimizer_steps']==0 and boundary['target_prefixes_used'] is False and boundary['reference_counts_used_only_in_loss'] is True and boundary['vocabulary_size']==32)
            exposures[bank_role].update(receipt['row_ids']);bank_updates[bank_role]+=1;template_exposures.update(r['template'] for r in source_rows);weighted_losses.append(item['weighted_loss']);base_losses.append(item['base_objective']);source_ces.append(receipt['mean_cross_entropy'])
        check('All budget sums and original stream digests reproduced',rows_seen==1220 and tokens_seen==112920 and source_seen==12800 and count_classes=={'1':305,'2':305,'4':305,'8':305} and decoder_hash.hexdigest()==report['committed_decoder_batch_ids_sha256'] and count_hash.hexdigest()==report['committed_count_batch_ids_sha256'] and dict(bank_updates)=={'control':85,'balanced':85} and all(len(c)==180 and sum(c.values())==510 and Counter(c.values())=={3:150,2:30} for c in exposures.values()))
        check('Actual per-bank per-template per-source ledger complete',auxiliary['committed_updates_per_bank']==dict(bank_updates) and auxiliary['committed_presentations_per_bank']=={r:510 for r in ROLES} and auxiliary['committed_presentations_per_template']==dict(template_exposures)==dual_schedule['presentations_per_actual_template'] and set(template_exposures.values())=={255} and auxiliary['committed_per_source_exposures']=={r:dict(c) for r,c in exposures.items()}==dual_schedule['per_source_exposures'] and auxiliary['inherited_single_bank_template_counters_applicable'] is False and auxiliary['actual_counts_replayed_from_committed_receipts'] is True and auxiliary['numerical_loss_or_updates_changed'] is False)
        for wrapper in auxiliary['uncommitted_observations']:
            check('Uncommitted forward preserved separate from optimizer evidence',wrapper['schema']=='dual-authored-wording-modality-loss/v1' and wrapper['authentic_receipt_sha256']==digest(wrapper['authentic_receipt']))
        gradients=report['gradient_norms'];norms=[u['preclip_norm'] for u in updates];check('Stored gradient norm counts/means exact',gradients['optimizer_steps']==170 and math.isclose(gradients['max_preclip_norm'],max(norms),abs_tol=1e-12,rel_tol=1e-12) and math.isclose(gradients['mean_preclip_norm'],sum(norms)/170,abs_tol=1e-12,rel_tol=1e-12))
        endpoint_summaries={}
        for state_role in ('selected','last-attempt'):
            state=states[state_role];panels=arm['postfit'][state_role];check('Nine physically retained original panels',set(panels)==set(PANELS))
            panel_summaries={}
            for label in PANELS:
                ref=panels[label];path=ref['path'];check('Every original panel path physically distinct',path not in panel_paths);panel_paths.add(path)
                panel=reader.ref(ref);fidelity=panel['source_fidelity'];split='train' if label=='training' else 'validation';golds=gold_by_split[split];num=panel['report'];counts=Counter();seven={f:Counter() for f in FACETS};lengths={}
                check('Original panel provenance/full48/schema/output',num['complete'] is True and num['sample_count']==len(panel['predictions'])==len(fidelity['rows'])==48 and num['codec_sha256']==digest(codec) and num['input_transform_sha256']==digest(state['input_transform']) and num['max_target_tokens']==512 and num['generation_temperature']==0 and num['optimizer_steps']==0 and num['generation_target_access'] is False and fidelity['complete_evaluation'] is True and fidelity['codec_sha256']==digest(codec))
                control_tensor = typed_tensor_digest({'body.'+name:value for name,value in state['model_state'].items()}) if label in ('zero-condition','recurrent-residual-off') else state['tensor_sha256']
                check('Exact endpoint/control typed tensor binding',num['model_weights_sha256']==control_tensor and (label!='zero-condition' or panel['execution']['kind']=='zero_condition') and (label!='recurrent-residual-off' or panel['execution']['recurrent_residual_disabled'] is True))
                for prediction,row in zip(panel['predictions'],fidelity['rows'],strict=True):
                    identity=prediction['id'];generated,c,facets=formula_counts(golds[identity],prediction,vocabulary)
                    check('Actual original emitted formula/complete facet counts',identity==row['id'] and golds[identity]==row['expected_ir'] and generated==row['generated_ir'] and c==row['counts'] and facets==row['by_facet'])
                    counts.update(c);length=str(len(golds[identity]['rules']));bucket=lengths.setdefault(length,dict(metrics=Counter(),by_facet={f:Counter() for f in FACETS}));bucket['metrics'].update(c)
                    for f,values in facets.items():seven[f].update(values);bucket['by_facet'][f].update(values)
                check('All180 rules/seven facets/length aggregates',dict(counts)==fidelity['metrics'] and {f:dict(v) for f,v in seven.items()}==fidelity['by_facet'] and lengths==fidelity['by_length'] and counts['expected_rules']==180)
                check('Numerical formula/EOS counts and112920 timing scope separate',num['metrics']['count']==48 and num['metrics']['eos_count']==counts['eos_count'] and num['metrics']['exact_targets']==counts['ordered_exact'] and num['metrics']['ce_teacher_forced'] is True and num['metrics']['generation_teacher_forced'] is False and num['metrics']['target_token_count']==sum(len(r['target_ids'])-1 for r in originals[split]) and math.isfinite(num['metrics']['token_cross_entropy']))
                false_masks(panel)
                panel_summaries[label]=dict(rows=48,expected_rules=180,formula_metrics=dict(counts),seven_facets={f:dict(v) for f,v in seven.items()},token_cross_entropy_reported=num['metrics']['token_cross_entropy'],token_cross_entropy_recomputed_from_raw_logits=False,reconstruction_mse_reported=num['metrics']['reconstructed_input_mse'],reconstruction_scope='Identity projection/numerical reconstruction metric, not an independently learned semantic reconstruction claim.',timing=panel['timing'])
            readouts={}
            for bank_role in ROLES:
                observed=reader.ref(arm['full180_postfit_readouts'][state_role][bank_role]);readouts[bank_role]=source_readout(observed,banks[bank_role],codec,state['tensor_sha256'],check);bank_site_count+=720
            selected_report=report['selected' if state_role=='selected' else 'last_complete_attempt']
            check('Endpoint validation selection summary binds actual retained panel',selected_report['fidelity']['metrics']==panel_summaries['validation']['formula_metrics'] and selected_report['fidelity']['by_facet']==panel_summaries['validation']['seven_facets'])
            endpoint_summaries[state_role]=dict(tensor_sha256=state['tensor_sha256'],state_ref=arm['states'][state_role],original_panels=panel_summaries,source_bank_readouts=readouts)
        false_masks(report);false_masks(arm)
        arm_summaries[role]=dict(initial_tensor_sha256=PARENT,optimizer_steps=170,row_presentations=1220,target_token_presentations=112920,count_presentations=1220,source_value_presentations=12800,used113_source_presentations=1020,paired_source_presentations=1020,mean_paired_modality_CE=sum(source_ces)/170,mean_paired_weighted_loss=sum(weighted_losses)/170,mean_pre_auxiliary_objective=sum(base_losses)/170,selected_epoch=report['selected_epoch'],selection=report['selection'],selected_last_tensor_alias=arm['selected_last_tensor_alias'],attempted_source_forwards=auxiliary['forward_attempts'],completed_source_forward_observations=auxiliary['completed_forward_observations'],uncommitted_source_observations=len(auxiliary['uncommitted_observations']),committed_updates_per_bank=dict(bank_updates),committed_presentations_per_bank={r:510 for r in ROLES},committed_presentations_per_actual_template=dict(template_exposures),committed_per_source_exposures={r:dict(c) for r,c in exposures.items()},fresh_optimizer_moments_verified=True,scheduler_scope='Fresh declared scheduler and initial rates; scheduler state is not serialized for exact optimizer resume.',training_call_seconds=arm['training_call_elapsed_seconds'],training_owner_seconds=report['elapsed_seconds'],training_rows_per_second=arm['training_rows_per_second'],endpoints=endpoint_summaries)
        check('Actual fit time within180 and reported throughput denominator',arm['training_call_elapsed_seconds']<=180 and report['elapsed_seconds']<=180 and math.isclose(arm['training_rows_per_second'],1220/arm['training_call_elapsed_seconds'],rel_tol=1e-12,abs_tol=1e-12))
    check('All18 original panels/2880 endpoint source scalars/2040 training distributions',len(panel_paths)==18 and bank_site_count==2880 and full32_training_count==2040)
    for path,wanted in result['source_dependencies'].items():reader.body(path,{'sha256':wanted})
    final=reader.json(attempt/'resources-final.json');start=reader.json(attempt/'resources-start.json');child=reader.json(attempt/'child-exit.json');guardian=reader.json(run/(attempt.name+'-guardian-exit.json'));record=final['record'];lease=final['resource_lease'];old=start['record']
    check('Exit0/reaped/durable release/owned identity',child['returncode']==guardian['returncode']==0 and child['leader_reaped'] is True and final['status']==record['status']=='released' and final['cleanup_error'] is None and record['artifacts_durable_asserted'] is True and record['attempt_exceeded_reservation'] is False and lease['released'] is True and old['reservation_id']==record['reservation_id'] and old['child']==record['child'] and start['resource_lease']['lease_id']==lease['lease_id'])
    check('FixedCPU1/1536MiB/400MB/resource limits',record['cpu_slots']==record['child_process_slots']==1 and record['memory_mb']==1536 and record['storage_bytes']==400000000 and lease['requires_gpu'] is False)
    observations_path=attempt/'resource-observations.json';periodic=reader.json(observations_path) if observations_path.is_file() else [];samples=[old['last_usage'],*periodic,record['last_usage']]
    check('All available sampled resource bounds and final groupzero',all(r['attempt_bytes']<=r['attempt_limit_bytes'] and r['charged_bytes']<=r['limit_bytes'] and r['group_rss']['rss_bytes']<=r['memory_limit_bytes'] and r['process_slot_estimate_exceeded'] is False for r in samples) and record['last_usage']['group_rss']['available'] is True and record['last_usage']['group_rss']['live_processes']==record['last_usage']['group_rss']['rss_bytes']==0 and record['final_accounting']['charged_bytes']<=record['final_accounting']['limit_bytes']==145000000000)
    watchdog=final['lease_watchdog'];events=[json.loads(line) for line in reader.body(watchdog['events_path'],{'sha256':watchdog['events_sha256']}).splitlines() if line];present=[e for e in events if e.get('lease_present') is True];post=watchdog['post_release_observation']
    check('Own sampled lease healthy/released/config unchanged',bool(present) and all(e['healthy'] is e['configuration_matches'] is True and e['cancelled'] is False for e in present) and post['lease_present'] is False and post['healthy'] is post['configuration_matches'] is True and watchdog['continuous_lease_coverage_claimed'] is watchdog['shared_state_mutated_by_observer'] is False)
    check('Driver/outer resource time envelopes',result['elapsed_seconds']<=900 and guardian['elapsed_seconds']<=1000)
    reader.body(PURE_PATH,{'sha256':PURE_SHA});reader.body(__file__)
    review=dict(schema='dual-bank-replay-native384-training-independent-review/v1',passed=True,findings=[],checks=checks,artifacts=reader.bindings,attempt=str(attempt),phase='training',dimension=384,parent_tensor_sha256=PARENT,arms=arm_summaries,physical_original_panels=18,original_panel_rows=864,original_reference_rule_sites=3240,endpoint_source_bank_scalar_sites=2880,training_full32_modality_distributions_checked=2040,training_executed_by_audited_attempt=True,training_executed_by_audit=False,models_or_numerical_owners_imported_or_executed_by_audit=False,qualified=False,admitted=False,proof_authority=False,source_semantics_verified=False,convergence_proven=False,fresh_semantic_holdout=False,checkpoint_promoted=False,timing=dict(driver_seconds=result['elapsed_seconds'],outer_guardian_seconds=guardian['elapsed_seconds'],launch_return_through_reap_seconds=child['launch_return_through_reap_wall_seconds'],scope='One fresh-optimizer170-step numerical replay fit plus original exposed panels/source-bank readouts using cached384 features and frozen historical owners; no encoder/native compiler/Lean/end-to-end speed claim.'),resources=dict(storage_reservation_bytes=400000000,memory_MiB=1536,periodic_sample_count=len(periodic),maximum_saved_group_RSS_bytes=max(r['group_rss']['rss_bytes'] for r in samples),peak_RSS_measured=False,final_attempt_census_bytes=record['final_attempt_bytes'],final_named_root_charge_bytes=record['final_accounting']['charged_bytes'],named_root_cap_bytes=145000000000,owned_present_lease_samples=len(present),durable_lease_released=True,final_live_group_processes=0,continuous_coverage_claimed=False,foreign_scheduler_read_or_modified=False),measurement_limits=['Parent balanced bank and new48 were already correct before fitting; replay measures confidence/coverage/retention, not repair of new-bank classification errors. One new fit compares archived control; changed auxiliary chronology prevents isolated causal claims.','Original TRAIN/validation are exposed numerical cohorts; v3/sealed60/balanced48 labels do not select checkpoints and no fresh semantic holdout claim is made.','Endpoint source-bank argmax is distinct from greedy formula generation. This phase saves18 original greedy panels but no new48 postfit greedy rollout; later posthoc observation is separate.','Full32 source auxiliary loss is recomputed from stored logits; original decoder teacher-forced CE is an owner-reported aggregate without raw full-token logits.','Identity/projection MSE is not independently learned semantic reconstruction. Shared global clipping can affect all updates; source-only auxiliary forward ownership is not causal isolation.','Typed state hashes are recomputed from saved float32/int64 serialized values without constructing numerical tensors.','Frozen legal_formula_codec._rule schema validation and historical import-tree logs do not grant compiler execution, Lean admission or canonical working-tree throughput evidence.','Resource and lease samples are bounded observations; neither process peak RSS nor continuous lease coverage is claimed.'],audit_elapsed_seconds=time.monotonic()-started)
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x') as stream:stream.write(json.dumps(review,indent=2,sort_keys=True,allow_nan=False)+'\n')
    return review


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--completed-attempt',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--root-completion-acknowledged',action='store_true');args=parser.parse_args()
    review=audit(args.completed_attempt,args.output,args.root_completion_acknowledged)
    print(json.dumps(dict(passed=True,checks=len(review['checks']),original_panels=18,endpoint_source_scalar_sites=2880,training_full32_distributions=2040,output=str(args.output))))
