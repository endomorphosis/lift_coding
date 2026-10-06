"""Derive compact documentation evidence from saved outputs; stdlib only."""
import hashlib
import json
import math
import subprocess
from collections import Counter
from pathlib import Path

WORKSPACE = Path('/home/barberb/lift_coding')
R = WORKSPACE / 'artifacts/autoencoder-next-reconstruction-gap-20261006'
OUT = R / 'documentation/evidence'
P = WORKSPACE / 'external/ipfs_datasets'
ATTEMPT = P / 'workspace/test-logs/decoder-train-readout-observation-20261006/train-observation-r1'
FACETS = ('modality', 'actor', 'action', 'object', 'conditions', 'exceptions', 'temporal')
SCALARS = FACETS[:4]
ROUTES = {'source': 'applied_source_logits', 'recurrent': 'raw_recurrent_logits', 'combined': 'combined_logits'}
ARTIFACTS = {}
CHECKS = []


def pin(path):
    path = Path(path)
    data = path.read_bytes()
    value = {'path': str(path), 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
    ARTIFACTS[str(path)] = {k: value[k] for k in ('sha256', 'bytes')}
    return value


def read(path):
    binding = pin(path)
    return json.loads(Path(binding['path']).read_text())


def checked_ref(ref):
    actual = pin(ref['path'])
    assert all(actual[key] == ref[key] for key in ('sha256', 'bytes')), ref['path']
    return actual


def write(name, value):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    path.write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n')
    return pin(path)


def near(actual, expected):
    assert math.isclose(actual, expected, rel_tol=1e-11, abs_tol=1e-11), (actual, expected)


def distribution(vector, target):
    assert len(vector) == 32 and all(math.isfinite(x) for x in vector)
    largest = max(vector)
    return {
        'argmax_token_id': max(range(32), key=vector.__getitem__),
        'full_vocabulary_cross_entropy': largest + math.log(sum(math.exp(x - largest) for x in vector)) - vector[target],
        'target_minus_best_other': vector[target] - max(x for i, x in enumerate(vector) if i != target),
    }


summary = read(ATTEMPT / 'results/summary.json')
manifest = read(R / 'train-observation/observation-manifest.json')
plan = read(R / 'train-observation/observation-plan.json')
freeze = read(R / 'train-observation/source-freeze.json')
barrier = read(ATTEMPT / 'results/predictions-complete.json')
assert summary['complete'] and summary['archived_original_generation_parity_verified']
assert barrier['all_predictions_fsynced'] and not barrier['posthoc_train_reference_json_loaded']
assert summary['all_predictions_fsynced_before_reference_load']
assert summary['inherited_train_validation_metadata_loaded_before_collection']
assert len(summary['panels']) == 4 and len(manifest['inputs']) == 1162
for key in ('training_executed', 'encoder_executed', 'downloads_performed', 'lake_executed', 'qualified', 'admitted',
            'formalized', 'proof_authority', 'source_semantics_verified', 'used_for_selection', 'checkpoint_promoted',
            'fresh_holdout', 'independent_semantic_holdout', 'convergence_proven', 'roundtrip_ok'):
    assert summary[key] is False, key
    assert plan[key] is False, key
CHECKS.append('Four-state completion, durable pre-reference barrier and explicit inherited metadata exception; all scientific authority masks false.')
codec = read(WORKSPACE / 'artifacts/autoencoder-wording-fit-20261006/development/codec.json')
vocab = codec['target_vocabulary']
assert len(vocab) == 32
panels, misses = [], []
observed_sites = 0
raw_distributions = 0
cohort_id_order = None

for panel in summary['panels']:
    state_key = str(panel['dimension']) + '-' + panel['arm']
    selected = manifest['selected_states'][state_key]
    for key in ('path', 'sha256', 'bytes'):
        assert selected[key] == panel['state_ref'][key]
    refs = {key: checked_ref(panel[key]) for key in ('state_ref', 'predictions_ref', 'score_ref', 'source_head_score_ref',
                                                   'source_head_formula_join_ref', 'source_head_trace_ref')}
    predictions = read(refs['predictions_ref']['path'])
    score = read(refs['score_ref']['path'])
    source_score = read(refs['source_head_score_ref']['path'])
    join = read(refs['source_head_formula_join_ref']['path'])
    trace = read(refs['source_head_trace_ref']['path'])
    tensor = panel['state_ref']['tensor_sha256']
    assert all(x['model_tensor_sha256'] == tensor for x in (predictions, score, source_score, trace))
    assert predictions['same_pass_scalar_trace_sha256'] == trace['trace_sha256']
    assert len(predictions['predictions']) == len(trace['rows']) == 96
    assert len(join['rows']) == 360 and len(source_score['events']) == 1440
    assert trace['vocabulary_size'] == 32 and trace['extra_model_passes'] == trace['source_head_extra_evaluations'] == 0
    assert all(trace[k] is False for k in ('syntax_mask', 'forced_closure', 'reference_count_access', 'reference_prefix_access',
                                         'reference_documents_passed_to_model', 'inventory_access', 'model_copied'))
    ordered_ids = [row['id'] for row in predictions['predictions']]
    assert len(set(ordered_ids)) == 96
    assert all(x.startswith('authored-paragraph:train:') for x in ordered_ids[:48])
    assert all(x.startswith('normative-training-v1:') for x in ordered_ids[48:])
    if cohort_id_order is None:
        cohort_id_order = ordered_ids
    assert cohort_id_order == ordered_ids
    archived_ref = checked_ref(manifest['archived_original_predictions'][state_key])
    archived = read(archived_ref['path'])
    assert len(archived['predictions']) == 48
    for actual, old in zip(predictions['predictions'][:48], archived['predictions'], strict=True):
        assert all(actual[key] == old[key] for key in ('id', 'token_ids', 'generation_status', 'eos_reached'))
    CHECKS.append(state_key + ': selected tensor identity, same-pass/no-mask traces,96 sources/360 rules/1440 events and all48 archived original tokens/status/EOS exact.')
    raw_sites = {}
    for row in trace['rows']:
        for site in row['scalar_sites']:
            key = (row['id'], site['slot'], site['field'])
            assert key not in raw_sites
            raw_sites[key] = site
    assert len(raw_sites) == 1440
    events = {}
    for event in source_score['events']:
        key = (event['id'], event['slot'], event['field'])
        assert key not in events and key in raw_sites
        site = raw_sites[key]
        assert site['position'] == event['position'] and site['actual_next_token_id'] == event['actual_next_token_id']
        for route, logits_key in ROUTES.items():
            measured = distribution(site[logits_key], event['target_token_id'])
            assert measured['argmax_token_id'] == event[route]['argmax_token_id']
            for metric in ('full_vocabulary_cross_entropy', 'target_minus_best_other'):
                near(measured[metric], event[route][metric])
            raw_distributions += 1
        assert all(abs(a + b - c) < 1e-5 for a, b, c in zip(site['applied_source_logits'], site['raw_recurrent_logits'], site['combined_logits'], strict=True))
        assert site['decomposition_exact'] and site['source_slot_available'] and site['source_guidance_active']
        events[key] = event
        observed_sites += 1
    fidelity = {row['id']: row for row in score['fidelity']['rows']}
    teacher = {row['id']: row for row in score['teacher_forced']['rows']}
    assert set(fidelity) == set(teacher) == set(ordered_ids)
    cohorts = {}
    for name, ids in (('original_train', ordered_ids[:48]), ('normative_train', ordered_ids[48:])):
        idset = set(ids)
        declared = panel['by_cohort'][name]
        rows = [fidelity[i] for i in ids]
        rules = sum(len(x['expected_ir']['rules']) for x in rows)
        assert rules == 180 and declared['scalar_sites'] == 720 and declared['paragraphs'] == 48
        metrics = {key: sum(x['counts'][key] for x in rows) for key in rows[0]['counts']}
        assert metrics == declared['formula_metrics']
        assert declared['ordered_exact'] == sum(x['expected_ir'] == x['generated_ir'] for x in rows)
        seven = {facet: {'correct': 0, 'total': 0} for facet in FACETS}
        for row in rows:
            assert len(row['expected_ir']['rules']) == len(row['generated_ir']['rules'])
            for expected, generated in zip(row['expected_ir']['rules'], row['generated_ir']['rules'], strict=True):
                assert set(expected) == set(generated) == set(FACETS)
                assert all(expected[facet] == [] for facet in FACETS[4:])
                for facet in FACETS:
                    seven[facet]['total'] += 1
                    seven[facet]['correct'] += expected[facet] == generated[facet]
        assert seven == declared['seven_facets']
        tokens = sum(teacher[i]['token_count'] for i in ids)
        token_ce = sum(teacher[i]['cross_entropy'] * teacher[i]['token_count'] for i in ids) / tokens
        assert tokens == declared['target_tokens']
        near(token_ce, declared['token_cross_entropy'])
        distributions = {}
        for field in SCALARS:
            measured_events = [event for key, event in events.items() if key[0] in idset and key[2] == field]
            assert len(measured_events) == 180
            distributions[field] = {}
            for route in ROUTES:
                records = [e[route] for e in measured_events]
                margins = [e['target_minus_best_other'] for e in records]
                values = {
                    'visited': len(records), 'argmax_correct': sum(e[route]['argmax_token_id'] == e['target_token_id'] for e in measured_events),
                    'margin_min': min(margins), 'margin_mean': sum(margins) / len(margins), 'margin_max': max(margins),
                    'nonpositive_margins': sum(x <= 0 for x in margins),
                    'mean_cross_entropy': sum(e['full_vocabulary_cross_entropy'] for e in records) / len(records),
                }
                published = declared['full_vocabulary_scalar_distributions'][field][route]
                correspondence = {'visited': 'visited_scored_sites', 'argmax_correct': 'argmax_correct', 'margin_min': 'minimum_target_margin',
                                  'margin_mean': 'mean_target_margin', 'margin_max': 'maximum_target_margin',
                                  'nonpositive_margins': 'nonpositive_target_margins', 'mean_cross_entropy': 'mean_cross_entropy'}
                for key, target in correspondence.items():
                    near(values[key], published[target])
                assert published['unvisited_or_unavailable_sites'] == 0 and published['reference_sites'] == 180
                assert published['full_vocabulary_size'] == 32
                distributions[field][route] = values
        cohort_joins = [row for row in join['rows'] if row['id'] in idset]
        assert len(cohort_joins) == 180
        fields = {}
        for field in SCALARS:
            fields[field] = {'reference_sites': 180, 'visited': 180, 'unvisited': 0, 'unavailable': 0,
                             'source_correct': 0, 'source_correct_formula_wrong': 0}
            for row in cohort_joins:
                record = row['fields'][field]
                assert record['status'] == 'visited'
                assert record['source_correct'] == (record['source']['argmax_token_id'] == record['target_token_id'])
                assert record['formula_field_correct'] == (row['expected_rule'][field] == row['generated_rule'][field])
                assert record['source'] == events[(row['id'], row['slot'], field)]['source']
                fields[field]['source_correct'] += record['source_correct']
                fields[field]['source_correct_formula_wrong'] += record['source_correct'] and not record['formula_field_correct']
                if panel['dimension'] == 384 and panel['arm'] == 'normative-wording-ce' and not record['source_correct']:
                    misses.append({'cohort': name, 'id': row['id'], 'slot': row['slot'], 'field': field,
                                   'source_sha256': row['source_sha256'], 'source_text': fidelity[row['id']]['source_provenance']['source_text'],
                                   'expected_rule': row['expected_rule'], 'generated_rule': row['generated_rule'],
                                   'source_label': json.loads(vocab[record['source']['argmax_token_id']]),
                                   'combined_label': json.loads(vocab[record['combined']['argmax_token_id']]),
                                   'source': record['source'], 'recurrent': record['recurrent'], 'combined': record['combined'],
                                   'formula_correct': record['formula_field_correct'], 'position': record['position']})
        assert fields == declared['fields']
        cohorts[name] = {'paragraphs': 48, 'rules': 180, 'scalar_sites': 720, 'ordered_exact': declared['ordered_exact'],
                         'formula_metrics': metrics, 'seven_facets': seven, 'fields': fields,
                         'teacher_forced_target_tokens': tokens, 'teacher_forced_token_cross_entropy': token_ce,
                         'full32_actual_prefix_distributions': distributions}
        CHECKS.append(state_key + '/' + name + ': all seven facets, complete formula counts, token-weighted teacher CE and all12 visited full32 route summaries agree.')
    panels.append({'dimension': panel['dimension'], 'arm': panel['arm'], 'role': panel['role'], 'state_ref': panel['state_ref'],
                   'selected_last_identical_tensor_alias': panel['selected_last_identical_tensor_alias'],
                   'greedy_seconds_96_cached_paragraphs': panel['generation_seconds'],
                   'scoring_seconds': panel['scoring_seconds'], 'source_head_scoring_seconds': panel['source_head_scoring_seconds'],
                   'archived_original_predictions': archived_ref, 'artifacts': refs, 'by_cohort': cohorts})

assert observed_sites == 5760 and raw_distributions == 17280 and len(misses) == 1
assert misses[0]['field'] == 'action' and misses[0]['source_label'] == 'approve' and misses[0]['combined_label'] == 'deliver'
diagnosis = read(R / 'diagnosis/numeric-diagnosis.json')
v3_action = next(row for row in diagnosis['auxiliary384_complete_error_classification']['errors'] if row['field'] == 'action')
misses[0]['source_clause'] = misses[0]['source_text'].split('\n\n')[misses[0]['slot']]
v3_comparison = {key: v3_action[key] for key in ('id', 'slot', 'source_clause', 'gold', 'generated', 'source_argmax_token',
                                                'combined_argmax_token', 'source', 'combined', 'recurrent', 'template_family',
                                                'actual_prefix_equal_reference_prefix')}
misses[0]['distinct_exposed_v3_action_comparison'] = v3_comparison

resource = read(ATTEMPT / 'resources-final.json')
observations = read(ATTEMPT / 'resource-observations.json')
child = read(ATTEMPT / 'child-exit.json')
guardian_exit = read(ATTEMPT.parent / 'train-observation-r1-guardian-exit.json')
assert child['returncode'] == guardian_exit['returncode'] == 0 and child['leader_reaped']
assert resource['status'] == 'released' and resource['cleanup_error'] is None
assert resource['resource_lease']['released'] and not resource['record']['attempt_exceeded_reservation']
timing = {'numerical_driver_seconds': summary['elapsed_seconds'], 'outer_guardian_seconds': guardian_exit['elapsed_seconds'],
          'launch_return_through_reap_wall_seconds': child['launch_return_through_reap_wall_seconds'],
          'reserved_wrapper_through_child_exit_seconds': child['guardian_elapsed_through_child_exit_seconds'],
          'greedy_scope': 'one96-paragraph source-only pass per endpoint; setup/scoring/encoder/native/Lake excluded',
          'end_to_end_autoformalization_measured': False}
resource_summary = {'storage_reservation_bytes': resource['record']['storage_bytes'], 'memory_reservation_MiB': resource['record']['memory_mb'],
                    'cpu_slots': resource['record']['cpu_slots'], 'child_process_slots': resource['record']['child_process_slots'],
                    'finalization_census_attempt_bytes': resource['record']['final_attempt_bytes'],
                    'maximum_sampled_group_RSS_bytes': max(x['group_rss']['rss_bytes'] for x in observations),
                    'sample_count': len(observations), 'continuous_lease_coverage_claimed': False,
                    'own_lease_released': resource['resource_lease']['released'],
                    'post_release_configuration_matches': resource['lease_watchdog']['post_release_observation']['configuration_matches'],
                    'terminal_cancelled_flag_scope': 'scheduler missing-lease lookup after release, not a continuous-coverage claim',
                    'independent_resource_review_pending': True}
false_authority = {key: summary[key] for key in ('training_executed', 'encoder_executed', 'downloads_performed', 'lake_executed', 'qualified',
                                                'admitted', 'formalized', 'proof_authority', 'source_semantics_verified', 'used_for_selection',
                                                'checkpoint_promoted', 'fresh_holdout', 'independent_semantic_holdout', 'convergence_proven', 'roundtrip_ok')}
train_summary = {'schema': 'compact-train-readout-observation/v1', 'complete': True, 'summary': pin(ATTEMPT / 'results/summary.json'),
                 'authority': false_authority, 'source_input_pins': len(manifest['inputs']),
                 'actual_reference_scalar_sites': observed_sites, 'full32_distributions_independently_recomputed': raw_distributions,
                 'cohorts_are_separate': True, 'qualifier_labels_empty_on_both_cohorts': True,
                 'all_four_original_train_generation_parity_exact': True,
                 'all_predictions_durable_before_posthoc_reference_load': True,
                 'inherited_train_validation_metadata_loaded_before_collection': True,
                 'no_labels_or_reference_counts_used_as_model_inputs': True, 'panels': panels,
                 'auxiliary_384_source_only_misses': misses, 'timing': timing, 'resource_receipt_summary': resource_summary,
                 'method': 'stdlib inspection and exact count recomputation from saved traces/joins/fidelity; no model or numerical-owner import/run',
                 'interpretation': 'Auxiliary generated TRAIN formulas and modality source/combined argmaxes are exact at both widths. Same-bank combined-modality CE would be confidence-only. A384 source-only action miss remains but is corrected by actual combined generation; prioritize balanced independently reviewed wording coverage.'}
availability_commit = '0440a869aac1feb6f40d2e33fd28ecf7d1795411'
git_bindings = {}
for path in ('artifacts/normative-checkpoint-availability-20261006/completion.json',
             'implementation_plan/docs/60-normative-checkpoint-availability-2026-10-06.md'):
    raw = subprocess.check_output(['git', 'show', availability_commit + ':' + path], cwd=WORKSPACE)
    binding = {'commit': availability_commit, 'repository': 'endomorphosis/lift_coding', 'path': path,
               'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
               'url': 'https://github.com/endomorphosis/lift_coding/blob/' + availability_commit + '/' + path}
    git_bindings[path] = binding
    ARTIFACTS['git:' + availability_commit + ':' + path] = binding
    if path.endswith('.json'):
        availability = json.loads(raw)
assert availability['availability_completed'] and availability['registered_serializations'] == 8
assert availability['unique_tensor_endpoints'] == 4
registered = {(p['dimension'], p['arm']): p['state_ref'] for p in availability['latest_peer_retention']['panels']}
for panel in panels:
    assert panel['state_ref'] == registered[(panel['dimension'], panel['arm'])]
train_summary['upstream_asset_availability'] = {
    'all_four_selected_endpoint_hashes_match_registered_and_published_assets': True,
    'unique_tensor_endpoints': 4, 'registered_selected_last_serializations': 8,
    'selected_last_are_aliases_not_replications': True,
    'runtime_ready': availability['runtime_ready'], 'teacher_qualified': availability['teacher_qualified'],
    'proof_authority': availability['proof_authority'], 'publication_bindings': git_bindings,
    'ordinary_working_copy_availability_inferred': False,
}
CHECKS.append('All four observed E selected state containers/tensors match upstream published and registered endpoints; selected/last aliases stay distinct from replications and qualification.')
write('train-observation-summary.json', train_summary)

qualifier = read(R / 'qualifier-review/qualifier-review.json')
validation = read(R / 'qualifier-review/implementation-validation.json')
implementation = read(R / 'qualifier-review/implementation-freeze.json')
assert validation['passed'] and implementation['passed'] and implementation['tests'] == 37
assert validation['test_result']['failures'] == validation['test_result']['errors'] == validation['test_result']['skipped'] == '0'
for path, binding in implementation['artifacts'].items():
    checked_ref({'path': path, **binding})
write('qualifier-preflight-summary.json', {
    'schema': 'compact-canonical-qualifier-preflight/v1', 'passed': True, 'findings': [],
    'module': pin(P / 'ipfs_datasets_py/logic/legal_ir/canonical_qualifier_training_preflight.py'),
    'tests': pin(P / 'tests/unit/logic/legal_ir/test_canonical_qualifier_training_preflight.py'),
    'implementation_validation': pin(R / 'qualifier-review/implementation-validation.json'),
    'implementation_freeze': pin(R / 'qualifier-review/implementation-freeze.json'),
    'test_result': validation['test_result'], 'api': 'preflight_qualifier_cohort(rows, *, word_codec=None, review_inputs=None)',
    'input_bounds': {'rows_min': 1, 'rows_max': 64, 'bytes_max': 16777216},
    'word_codec_source_target_caps': 64, 'byte_output_cap': 512, 'refused_public_byte_fixture_tokens': 579,
    'checked_corpus_evidence': qualifier['checked_corpus_evidence'], 'current_intake_train_eligible': False,
    'review_to_cohort_binding_assessed': False, 'review_replay_is_training_authority': False,
    'new_reviewed_TRAIN_qualifier_pairs_available': False,
    'defaults_activated': False, 'existing_codecs_modified': False,
    'always_false_authority_flags': validation['always_false_authority_flags'],
    'models_or_encoders_or_training_or_Lake_executed': False, 'Constitution_formalized': False,
})
scale_panels = []
for panel in diagnosis['panels']:
    scale_panels.append({key: panel[key] for key in ('dimension', 'arm', 'state_ref', 'tensor_sha256', 'actual_model_state_sha256',
                                                    'paragraphs', 'ordered_rules', 'original_ordered_exact_paragraphs',
                                                    'reference_scalar_sites', 'visited_scalar_sites', 'unvisited_scalar_sites',
                                                    'unavailable_scalar_sites', 'extra_scalar_sites',
                                                    'prespecified_source_scale_grid_at_original_prefixes')})
write('fixed-prefix-scale-summary.json', {
    'schema': 'compact-fixed-prefix-scale-diagnosis/v1', 'passed': diagnosis['passed'], 'findings': diagnosis['findings'],
    'diagnosis': pin(R / 'diagnosis/numeric-diagnosis.json'),
    'source_scale_grid_prespecified': diagnosis['source_scale_grid_prespecified'],
    'full32_scalar_sites_independently_authenticated': diagnosis['full32_scalar_sites_independently_authenticated'],
    'auxiliary384_error_counts': {key: diagnosis['auxiliary384_complete_error_classification'][key] for key in (
        'action_errors', 'modality_errors', 'modality_source_wrong', 'modality_source_correct_combined_wrong')},
    'measurement_limits': diagnosis['measurement_limits'], 'audit_execution': diagnosis['audit_execution'],
    'authority': diagnosis['authority'], 'panels': scale_panels,
})
write('independent-saved-output-summary-check.json', {
    'schema': 'independent-saved-output-documentation-check/v1', 'passed': True, 'findings': [],
    'checks': CHECKS, 'scalar_sites_checked': observed_sites, 'full32_distributions_recomputed': raw_distributions,
    'all_four_original_train_tokens_status_EOS_parity': True, 'artifacts': ARTIFACTS,
    'models_imported_or_executed': False, 'numerical_owners_imported_or_executed': False,
    'encoders_or_training_or_Lake_executed': False, 'canonical_mutations': False,
    'reviewer_authored_private_TRAIN_observer': True,
    'required_separate_agent_numerical_or_resource_review_replaced': False,
    'independence_scope': 'Arithmetic recomputation from saved vectors without frozen numerical owners; author documentation check, separate-agent actual-output reviews still required.',
})
print(json.dumps({'passed': True, 'checks': len(CHECKS), 'sites': observed_sites, 'distributions': raw_distributions,
                  'panels': len(panels), 'artifact_bindings': len(ARTIFACTS), 'outputs': str(OUT)}, sort_keys=True))
