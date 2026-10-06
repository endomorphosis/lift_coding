"""Reconstruct completed fit accounting and tensor identities from saved JSON only."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

ROOT = Path('/home/barberb/lift_coding'); P = ROOT / 'external/ipfs_datasets'
R = P / 'workspace/test-logs/decoder-normative-wording-r2-20261006'
OUT = ROOT / 'artifacts/autoencoder-wording-fit-20261006/review'
checks = 0; artifacts = {}


def check(value, label):
    global checks
    if not value: raise AssertionError(label)
    checks += 1


def raw(value): return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()
def digest(value): return hashlib.sha256(raw(value)).hexdigest()
def f32(value): return struct.unpack('<f', struct.pack('<f', float(value)))[0]


def ulp32(value):
    if value == 0.: return 2.**-149
    return max(2.**-149, 2.**(math.frexp(abs(value))[1] - 24))


def bind(path, wanted=None, size=None):
    path = Path(path).resolve(); h = hashlib.sha256(); count = 0
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''): h.update(block); count += len(block)
    record = dict(sha256=h.hexdigest(), bytes=count)
    if wanted is not None: check(record['sha256'] == wanted, 'exact saved artifact SHA:' + str(path))
    if size is not None: check(count == size, 'exact saved artifact size:' + str(path))
    artifacts[str(path)] = record; return record


def load(path): bind(path); return json.loads(Path(path).read_bytes())
def reference(ref): bind(ref['path'], ref['sha256'], ref.get('bytes')); return json.loads(Path(ref['path']).read_bytes())


def shape_flat(value):
    if type(value) is not list: return [], [value]
    check(bool(value), 'nonempty saved tensor axis')
    inner, _ = shape_flat(value[0]); values = []
    for item in value:
        shape, numbers = shape_flat(item); check(shape == inner, 'rectangular saved tensor axis'); values.extend(numbers)
    return [len(value)] + inner, values


def tensor_state(state, wrapper_prefix=''):
    check(sys.byteorder == 'little', 'recorded contiguous CPU byte order')
    check(digest(state['model_state']) == state['weights_sha256'], 'saved numerical model-state JSON hash')
    h = hashlib.sha256()
    for name, value in sorted(state['model_state'].items()):
        shape, values = shape_flat(value); integer = all(type(v) is int for v in values)
        check(integer or all(type(v) is float and math.isfinite(v) for v in values), 'saved tensor scalar type')
        dtype = 'torch.int64' if integer else 'torch.float32'
        h.update(raw([wrapper_prefix + name, dtype, shape])); h.update(struct.pack('<' + ('q' if integer else 'f') * len(values), *values))
    if not wrapper_prefix:
        check(h.hexdigest() == state['tensor_sha256'], 'independent names/dtypes/shapes/contiguous float32-int64 byte digest')
    return h.hexdigest()


def ce_check(logits, target, observed):
    check(len(logits) == 32 and all(type(v) is float and math.isfinite(v) for v in logits), 'complete finite unmasked32V logits')
    maximum = max(logits)
    expected = math.log(math.fsum(math.exp(v - maximum) for v in logits)) + maximum - logits[target]
    error = abs(expected - observed)
    check(error <= 1e-6, 'double logsumexp checks recorded float32 CE within numerical tolerance')
    return error


def readout(ref, bank, expected_tensor):
    result = reference(ref)
    check(result['complete'] is True and result['model_tensor_sha256'] == expected_tensor and result['full_vocabulary_size'] == 32
          and len(result['rows']) == 180 and result['source_head_forward_calls'] == 30 and result['optimizer_steps'] == 0
          and result['used_for_selection'] is False, 'complete detached180 head readout no optimizer/selection')
    groups = {}; maximum_error = 0.
    for row, source in zip(result['rows'], bank['rows']):
        check(row['id'] == source['id'] and row['source_sha256'] == source['source_sha256']
              and row['modality'] == source['modality'] and row['template'] == source['template']
              and row['target_token_id'] == source['modality_token_id'], 'full bank source/reference readout join')
        logits = row['full_vocabulary_logits']; target = row['target_token_id']
        correct = max(range(32), key=logits.__getitem__) == target
        check(row['correct'] is correct, 'independent32V argmax classification')
        maximum_error = max(maximum_error, ce_check(logits, target, row['cross_entropy']))
        for key in ('all', 'modality:' + source['modality'], 'template:' + source['template'],
                    'stratum:' + source['modality'] + ':' + source['template']):
            item = groups.setdefault(key, dict(rows=0, correct=0, loss=0.))
            item['rows'] += 1; item['correct'] += correct; item['loss'] += row['cross_entropy']
    groups = {key: dict(rows=item['rows'], correct=item['correct'], cross_entropy=item['loss'] / item['rows']) for key,item in groups.items()}
    check(result['groups'] == groups, 'independent all stratum/template/modality denominators and float32 telemetry averages')
    return dict(correct=groups['all']['correct'], clauses=180, cross_entropy=groups['all']['cross_entropy'], groups=groups,
                max_double_CE_difference=maximum_error, elapsed_seconds=result['elapsed_seconds'],
                seconds_per_clause=result['elapsed_seconds'] / 180)


manifest = load(R / 'training-manifest.json'); plan = load(R / 'training-plan.json')
bind(R / 'training-plan.json', manifest['plan_sha256'])
for path,wanted in manifest['inputs'].items(): bind(path, wanted)
for path,wanted in manifest['producer_pins'].items(): bind(path, wanted)
for relative,wanted in manifest['extensions'].items(): bind(R / 'experiment-source' / relative, wanted)
check(manifest['prospective_development_references_bound_in_training'] is False, 'prospectiveDEV labels remain outside fit inputs')
expected_parent = {384: '6a527b568c1ec834fc6704a9d12a17532840076432a93dc1390c59c92d483ec3',
                   768: '8900d69fb00c17a54b7d3cbe6fbd2c24651b614839ad57c588d0f04dc308fada'}
draws = load(manifest['independent_inputs']['auxiliary_schedule'])
panels = {'training','validation','source-shuffle','cross-length-shuffle','context-rotate','context-reverse',
          'context-only-shuffle','recurrent-residual-off','zero-condition'}
dimensions = {}; total_steps = total_primary_rows = total_aux_observed = total_aux_supervised = 0
for width in (384, 768):
    attempt = R / f'training-{width}-r1'; data = attempt / 'results'
    outer = load(R / f'training-{width}-r1-guardian-exit.json'); child = load(attempt / 'child-exit.json'); final = load(attempt / 'resources-final.json')
    check(outer['returncode'] == child['returncode'] == 0 and child['leader_reaped'] is True, 'actual successful fit child and guardian exits')
    check(final['status'] == final['record']['status'] == 'released' and final['record']['artifacts_durable_asserted'] is True
          and final['record']['attempt_exceeded_reservation'] is False, 'owned durable completed fit release')
    summary = load(data / 'summary.json')
    check(summary['complete'] is True and summary['phase'] == 'training' and summary['dimension'] == width
          and len(summary['runs']) == 2 and summary['encoder_executed'] is False, 'completed paired numerical fit phase')
    for path,wanted in summary['source_dependencies'].items(): bind(path,wanted)
    baseline_run = load(manifest['baseline_summaries'][str(width)]); baseline = reference(baseline_run['training_ref'])
    baseline_states = {role: reference(ref) for role,ref in baseline_run['states'].items()}
    for state in baseline_states.values(): tensor_state(state)
    primary = load(manifest['independent_inputs']['primary_schedules'][str(width)])
    arm_results = []
    for descriptor in summary['runs']:
        run_path = Path(descriptor['summary_path']); bind(run_path,descriptor['summary_sha256']); run = load(run_path)
        arm = run['arm']; weight = run['recipe']['weight']; positive = weight > 0.
        check((arm,weight) in (('normative-wording-zero',0.),('normative-wording-ce',.05)) and run['dimension'] == width
              and run['budget_completed'] is True and run['fresh_optimizer'] is True and run['exact_optimizer_resume'] is False,
              'fixed completed arm with fresh optimizer')
        report = reference(run['training_ref']); bank = reference(run['bank']); declared = reference(run['schedule'])
        check(report['optimizer_steps'] == len(report['committed_updates']) == 170 and report['stopped_reason'] == 'epochs_completed'
              and len(report['history']) == 40 and len(report['stage_reports']) == 4
              and all(v['completed_epochs'] == 10 for v in report['stage_reports']), 'four complete tenepoch stages170 updates')
        check(report['row_presentations'] == report['count_training_row_presentations'] == 1220
              and report['valid_target_token_presentations'] == 112920 and report['source_value_presentations'] == 12800
              and report['count_training_presentations_by_class'] == {'1':305,'2':305,'4':305,'8':305}, 'all original work denominators preserved')
        for key in ('initial_weights_sha256','training_rows_sha256','validation_rows_sha256','training_references_sha256',
                    'validation_references_sha256','committed_decoder_batch_ids_sha256','committed_count_batch_ids_sha256'):
            check(report[key] == baseline[key], 'unchanged original source/target stream identity:' + key)
        for key,expected in dict(encoder_context_changed=False,full_targets_truncated=False,generation_temperature=0,
            source_value_validation_rows_used_for_training=False,count_validation_rows_used_for_training=False,
            source_value_reference_documents_passed_to_model=False,count_reference_documents_passed_to_model=False,
            frozen_parameters_verified=True,optimizer_instance_count=1,optimizer_reinitialized_between_stages=False,
            non_action_learning_rate_multiplier=10.,native_family_validation_performed=False,qualified=False,admitted=False,
            lake_executed=False,production_checkpoint=False,convergence_proven=False).items():
            check(report[key] == expected, 'fixed ownership/optimizer/diagnostic report field:' + key)
        aux = report['paraphrase_modality_auxiliary']
        check(aux['weight'] == weight and aux['bank_receipt']['bank_sha256'] == bank['bank_sha256']
              and all(aux[k] == 170 for k in ('max_updates_estimated','forward_attempts','completed_forward_observations','committed_updates'))
              and aux['observed_clause_presentations'] == aux['committed_clause_presentations'] == 1020
              and aux['positively_supervised_clause_presentations'] == (1020 if positive else 0)
              and aux['uncommitted_observations'] == [], 'full completed observed/committed/supervised auxiliary work')
        check(aux['committed_presentations_per_modality'] == {'O':340,'P':340,'F':340}
              and aux['committed_presentations_per_template'] == dict(explicit_actor_status_v1=510,regulation_norm_operator_v1=510), 'complete balanced auxiliary exposures')
        check(all(aux[k] is False for k in ('zero_weight_graph_attached','used_for_selection','decoder_rows_replaced','normalization_refitted'))
              and aux['training_only'] is True and 'source_training_mixture' not in report, 'no loss replacement/context or selection shortcuts')
        exposures = Counter(); maximum_ce_error = maximum_mean_error = 0.
        for step,(update,old,original,draw) in enumerate(zip(report['committed_updates'],baseline['committed_updates'],primary,draws)):
            check(update['optimizer_step'] == step + 1 and update['decoder_row_ids'] == original['decoder_ids'] == old['decoder_row_ids']
                  and update['count_row_ids'] == original['count_ids'] == old['count_row_ids'], 'exact original minibatch identity every committed step')
            if width == 384:
                check(update['auxiliary_source_modality']['receipt']['row_ids'] == old['auxiliary_source_modality']['receipt']['row_ids'], 'original384 auxiliary stream preserved')
            item = update['paraphrase_modality_auxiliary']; receipt = item['receipt']
            check(item['zero_based_committed_step'] == receipt['committed_step'] == step and item['weight'] == weight
                  and receipt['bank_sha256'] == bank['bank_sha256'] and receipt['gradient_enabled'] is positive,
                  'auxiliary step/weight/gradient/bank ownership')
            check(all(receipt[k] == draw[k] for k in ('indices','row_ids','source_sha256','target_token_ids'))
                  and [[v['modality'],v['template']] for v in receipt['strata']] == draw['strata'], 'all six exact predeclared stratum rows every update')
            check(receipt['full_vocabulary_size'] == 32 and receipt['batch_size'] == 6 and receipt['source_head_forward_calls'] == 1
                  and receipt['recurrent_forward_calls'] == receipt['count_forward_calls'] == 0
                  and all(receipt[k] is False for k in ('labels_passed_to_model','model_copied','sampler_state_advanced','encoder_executed','qualified','admitted','lake_executed')),
                  'unmasked32V source-only bounded auxiliary forward')
            correct = 0
            for logits,target,loss in zip(receipt['full_vocabulary_logits'],receipt['target_token_ids'],receipt['per_row_cross_entropy']):
                maximum_ce_error = max(maximum_ce_error,ce_check(logits,target,loss)); correct += max(range(32),key=logits.__getitem__) == target
            check(len(receipt['full_vocabulary_logits']) == len(receipt['per_row_cross_entropy']) == 6 and receipt['correct'] == correct, 'every sixrow CE and argmax counted')
            mean = math.fsum(receipt['per_row_cross_entropy']) / 6; error = abs(mean - receipt['mean_cross_entropy'])
            maximum_mean_error = max(maximum_mean_error,error)
            check(error <= 8*ulp32(receipt['mean_cross_entropy']) + 1e-10, 'float32 sixrow reduction numerical consistency')
            weighted = 0. if not positive else f32(f32(weight) * receipt['mean_cross_entropy'])
            check(item['weighted_loss'] == weighted and update['objective'] == f32(item['base_objective'] + weighted), 'exact serialized float32 weightedloss/objective arithmetic')
            exposures.update(receipt['row_ids'])
            if not positive:
                for key in ('token_ce','weighted_token_ce','count_ce','source_value_ce','raw_reconstruction_mse','objective','preclip_norm',
                            'learning_rate','target_token_presentations','source_value_presentations'):
                    check(update[key] == old[key], 'bit-exact M2 zero original numerical update:' + key)
                check(item['base_objective'] == update['objective'], 'zero diagnostic attaches no zero graph')
        check(sum(exposures.values()) == 1020 and dict(exposures) == declared['per_source_exposures'], 'complete actual auxiliary source exposure replay')
        check(sum(v['target_token_presentations'] for v in report['committed_updates']) == 112920
              and sum(v['source_value_presentations'] for v in report['committed_updates']) == 12800
              and sum(len(v['decoder_row_ids']) for v in report['committed_updates']) == 1220, 'independent sum of original committed work')
        check(report['selected_epoch'] == 40 and report['last_complete_attempt_is_selected'] is True, 'selected/last complete endpoint selection identity')
        states = {role: reference(ref) for role,ref in run['states'].items()}
        check(set(states) == {'initial','selected','last-attempt'}, 'all required retained endpoint roles')
        tensors = {role:tensor_state(state) for role,state in states.items()}
        check(tensors['initial'] == report['initial_weights_sha256'] == expected_parent[width]
              and tensors['selected'] == report['selected_weights_sha256']
              and tensors['last-attempt'] == report['last_complete_attempt_weights_sha256'] == tensors['selected'], 'independently hashed exported tensor endpoints')
        check(states['selected']['model_state'] == states['last-attempt']['model_state'], 'last/selected actual saved numerical tensors match')
        for name in report['frozen_parameter_names']:
            check(all(state['model_state'][name] == states['initial']['model_state'][name] for state in states.values()), 'every frozen projection parameter unchanged:' + name)
        if not positive:
            check(run['zero_arm_archived_replay_verified'] is True, 'runner verified zero replay')
            for key in ('initial_weights_sha256','selected_weights_sha256','last_complete_attempt_weights_sha256','selected_epoch'):
                check(report[key] == baseline[key], 'zero endpoint matches M2:' + key)
            for role in states:
                check(states[role]['model_state'] == baseline_states[role]['model_state'], 'actual zero serialized tensor values exactly M2:' + role)
        readouts = {'initial':readout(run['full180_parent_readout'],bank,tensors['initial'])}
        for role,ref in run['full180_postfit_readouts'].items(): readouts[role] = readout(ref,bank,tensors[role])
        check(readouts['selected']['groups'] == readouts['last-attempt']['groups'], 'selected/last full180 readouts identical')
        original_panels = {}
        # Both frozen pure inference controls deepcopy the entire endpoint as
        # child module `body`; routes change, while tensor values stay identical.
        # The state_dict name prefix is therefore part of their exact digest.
        wrapped_tensors = {role:tensor_state(state, 'body.') for role,state in states.items()}
        for role,panel_refs in run['postfit'].items():
            check(set(panel_refs) == panels, 'all nine original controls retained at endpoint:' + role)
            original_panels[role] = {}
            for label,ref in panel_refs.items():
                result = reference(ref); numerical = ref['numerical']; execution = result['execution']
                expected_control_tensor = wrapped_tensors[role] if label in ('recurrent-residual-off','zero-condition') else tensors[role]
                if label == 'recurrent-residual-off':
                    check(execution['kind'] == 'recurrent_residual_off' and execution['recurrent_residual_disabled'] is True, 'declared private recurrent residual ablation')
                elif label == 'zero-condition':
                    check(execution['kind'] == 'zero_condition' and execution['normalized_clause_values_and_padding_mask_removed'] is True, 'declared private zero source ablation')
                check(numerical['complete'] is True and numerical['generation_temperature'] == 0 and numerical['max_target_tokens'] == 512
                      and numerical['generation_target_access'] is False and numerical['model_weights_sha256'] == expected_control_tensor
                      and numerical['published_parent_unchanged'] is True and numerical['optimizer_steps'] == 0
                      and numerical['encoder_context_changed'] is False and numerical['full_targets_truncated'] is False
                      and all(execution[k] is False for k in ('target_payloads_read','references_accepted','training_performed','selection_performed','qualified','admitted','lake_executed'))
                      and execution['source_only'] is True, 'source-only fixed output/control evaluation with exact private-wrapper tensor digest')
                check(numerical['sample_count'] == len(result['predictions']) == 48, 'complete original48 panel outputs')
                if not positive:
                    old_result = reference(baseline_run['postfit'][role][label])
                    check(result['predictions'] == old_result['predictions'], 'bit-exact M2 zero original generation panel:' + label)
                original_panels[role][label] = dict(executed_tensor_sha256=expected_control_tensor,
                    private_body_wrapper=label in ('recurrent-residual-off','zero-condition'),
                    ordered_exact=ref['fidelity']['metrics']['ordered_exact'],
                    syntax_valid=ref['fidelity']['metrics']['syntax_valid'],rows=48,
                    token_cross_entropy=numerical['metrics']['token_cross_entropy'],elapsed_seconds=numerical['elapsed_seconds'],
                    wall_seconds_per_span=numerical['wall_seconds_per_span'],timing_scope=numerical['timing_scope'])
        check(original_panels['selected']['validation']['ordered_exact'] == 48, 'originalDEV whole formula reconstruction retained')
        arm_results.append(dict(arm=arm,weight=weight,optimizer_steps=170,selected_epoch=40,tensor_sha256=tensors,
            original_row_presentations=1220,valid_target_token_presentations=112920,source_value_presentations=12800,
            new_observed_clause_presentations=1020,new_positive_supervision_clause_presentations=1020 if positive else 0,
            exact_M2_zero_tensor_and_numeric_replay=not positive,full180_head_readouts=readouts,original_panels=original_panels,
            auxiliary_max_double_CE_difference=maximum_ce_error,auxiliary_max_mean_reduction_difference=maximum_mean_error,
            fit_call_seconds=run['training_call_elapsed_seconds'],training_rows_per_second=run['training_rows_per_second'],
            seconds_per_original_row=run['training_call_elapsed_seconds']/1220,
            seconds_per_committed_update=run['training_call_elapsed_seconds']/170,
            training_report_seconds=report['elapsed_seconds'],cache_scope=summary['cache_scope']))
        check(run['training_rows_per_second'] == 1220/run['training_call_elapsed_seconds'], 'recorded actual fit throughput')
        total_steps += 170; total_primary_rows += 1220; total_aux_observed += 1020; total_aux_supervised += 1020 if positive else 0
    zero,positive = arm_results
    check(zero['weight'] == 0. and positive['weight'] == .05, 'fixed paired arm order')
    zero_ce=zero['original_panels']['selected']['validation']['token_cross_entropy'];positive_ce=positive['original_panels']['selected']['validation']['token_cross_entropy']
    usage=load(attempt/'resource-observations.json');peak=max(v['group_rss']['rss_bytes'] for v in usage if v['group_rss']['available'])
    check(all(v['group_rss']['rss_bytes'] <= v['memory_limit_bytes'] for v in usage if v['group_rss']['available']), 'sampled actual fit RSS below1536MiB')
    lease_path=R/f'training-{width}-r1-lease-observations.jsonl';bind(lease_path)
    events=[json.loads(line) for line in lease_path.read_text().splitlines()];events=[v for v in events if v.get('schema')=='guardian-owned-lease-observation/v1']
    check(all(v['healthy'] and v['configuration_matches'] for v in events) and events[-1]['expected']=='absent'
          and events[-1]['lease_present'] is False, 'sampled healthy ownlease thenrelease')
    dimensions[str(width)]=dict(arms=arm_results,driver_elapsed_seconds=summary['elapsed_seconds'],guardian_elapsed_seconds=outer['elapsed_seconds'],
        originalDEV_positive_CE_delta=positive_ce-zero_ce,originalDEV_CE_improved=positive_ce<zero_ce,
        TRAINhead_positive_accuracy_gain=positive['full180_head_readouts']['selected']['correct']-zero['full180_head_readouts']['selected']['correct'],
        measured_positive_fit_call_seconds_delta=positive['fit_call_seconds']-zero['fit_call_seconds'],
        resource_status=final['status'],retained_attempt_bytes=final['record']['final_attempt_bytes'],sampled_RSS_max=peak,
        RSS_samples=len(usage),absolute_peak_claimed=False,lease_observation_count=len(events),continuous_lease_coverage_claimed=False,
        final_charged_campaign_bytes=final['record']['final_accounting']['charged_bytes'],cap_bytes=final['storage_limit_bytes'])
bind(Path(__file__));report=dict(schema='normative-wording-completed-fit-audit/v1',passed=True,findings=[],checks=checks,
    created_at=datetime.now(timezone.utc).isoformat(),artifacts=artifacts,dimensions=dimensions,
    total_optimizer_updates=total_steps,total_original_row_presentations=total_primary_rows,
    total_auxiliary_observed_clause_presentations=total_aux_observed,total_auxiliary_positively_supervised_clause_presentations=total_aux_supervised,
    scope=dict(widths=[384,768],bridge_names=[],legal_ir_provers=False,metric_disk_cache=False,workers_per_width=1,
               source_cache='warm authenticated new native vectors',temperature=0,context_tokens=512,decoder_output_tokens=512,
               original_meanings_previously_exposed=True,prospectiveDEV_reference_bodies_read=False),
    interpretation='AdditionalTRAIN wording supervision repairs full180 modality classification at both widths while originalDEV exact generation remains48/48. OriginalDEV CE worsens slightly; prospective complete formula generation still requires the separately sealed postfit evaluation. No checkpoint promotion.',
    limitations=['Head accuracy is modality-only TRAIN classification, not whole new-wording formulas or independent holdout fidelity.',
                 'Full32V CE recheck uses double precision against saved float32 losses with a numerical rounding tolerance; exact weightedloss and objective arithmetic uses float32.',
                 'Positive supervision adds backward work and global clipping can influence all trainable groups. Host-sharing makes tiny paired timing differences unsuitable as a demonstrated speedup.',
                 'No family/Lake qualification ran; all existing gates remain unchanged. The restricted32V grammar has empty qualifiers, and the Constitution remains unformalized.',
                 'No newmodels or inference ran in this audit. Saved tensor values were consumed only to produce hashes and equality checks; no weights are included in this report.'],
    models_loaded_by_auditor=False,training_executed_by_auditor=False,native_encoders_executed_by_auditor=False,
    qualified=False,admitted=False,lake_executed=False,checkpoint_promoted=False)
destination=OUT/'fit_audit.json'
with destination.open('x') as stream:json.dump(report,stream,indent=2,sort_keys=True);stream.write('\n')
print(json.dumps(dict(path=str(destination),sha256=bind(destination)['sha256'],passed=True,checks=checks,
    optimizer_updates=total_steps,TRAINhead_gains={k:v['TRAINhead_positive_accuracy_gain'] for k,v in dimensions.items()},
    originalDEV_CE_deltas={k:v['originalDEV_positive_CE_delta'] for k,v in dimensions.items()}),sort_keys=True))
