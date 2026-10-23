"""Authored accounting/control fixtures, never source or provider execution."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import aggregate_trials as agg
from test_accounting_snapshot import call


def selected(name='legacy-01', mode='legacy', repeat=1):
    return {'name': name, 'task': 'tune-mjcf', 'semantic_metadata_view': mode,
        'semantic_context_profile': agg.CONTEXT_PROFILE, 'repeat': repeat}


def model_report(identity, mode='legacy', effective=None, *, solved=True):
    invoke = call(identity)
    invoke.update(model_prompt_sha256='b' * 64, model_prompt_bytes=1000)
    report = {'semantic_context_profile': agg.CONTEXT_PROFILE,
        'implementation_route': 'model_router', 'provider_invocations': [invoke],
        'task_completed': solved, 'context_input_audit': {
            'status': 'verified_all_observed_model_inputs', 'all_observed_coding_inputs_verified': True,
            'coding_receipts_seen': 1, 'usable_coding_receipts': 1, 'read_errors': [],
            'invocations': [{'invocation_id': identity, 'status': 'verified_exact_model_input', 'model_input_verified': True}],
            'matches': [{'invocation_id': identity, 'model_input_verified': True, 'model_prompt_sha256': 'b' * 64,
                'model_prompt_bytes': 1000, 'model_input_checks': {'semantic_translation': True}}]}}
    if mode != 'legacy':
        effective = effective or mode
        report['semantic_metadata_view'] = {'requested_mode': mode}
        invoke['semantic_metadata_view'] = {
            'schema': 'supervisor-semantic-metadata-selection@1',
            'selected_mode': effective,
            'fallback_reason': 'complete_input_not_smaller_under_bytes_and_proxy' if effective == 'legacy' else None,
            'selected_complete_sha256': 'b' * 64, 'selected_complete_bytes': 1000,
            'candidate_only': True, 'token_proxy': 'utf8-bytes-ceil-div4@1',
            'view_receipt_sha256': 'd' * 64,
            'native_complete_sha256': 'b' * 64 if effective == 'legacy' else 'c' * 64,
            'candidate_complete_sha256': 'b' * 64 if effective != 'legacy' else 'c' * 64,
            'native_complete_bytes': 1000 if effective == 'legacy' else 1100,
            'candidate_complete_bytes': 1000 if effective != 'legacy' else 1100,
            'native_complete_proxy_tokens': 250 if effective == 'legacy' else 275,
            'candidate_complete_proxy_tokens': 250 if effective != 'legacy' else 275,
            'selected_complete_proxy_tokens': 250,
            **{key: False for key in ('source_freshness_verified', 'program_semantics_proved', 'omission_authority',
                'proof_authority', 'execution_authority', 'completion_authority', 'publication_authority')}}
        report['context_input_audit']['matches'][0]['model_input_checks']['semantic_metadata_selection_receipt'] = True
    return report


def fixture(root, selections, reports=None):
    protocol = {'trials': selections, 'preparations': {},
        'pairs_match_except': list(agg.REMOVED_AXES),
        'unordered_list_canonicalizations': list(agg.CANONICALIZED_AXES), 'source_commit': 'c' * 40}
    for i, item in enumerate(selections):
        folder = root / 'trials' / item['name']
        folder.mkdir(parents=True)
        kwargs = {'semantic_context_profile': agg.CONTEXT_PROFILE}
        if item['semantic_metadata_view'] != 'legacy': kwargs['semantic_metadata_view'] = item['semantic_metadata_view']
        config = {'job_name': 'job-' + item['name'], 'jobs_dir': str(folder / 'jobs'),
            'agents': [{'kwargs': kwargs}], 'model': 'gpt-6.1-sol',
            'retry': {'exclude_exceptions': ['Foo', 'Bar']}}
        raw = json.dumps(config).encode()
        (folder / 'config.json').write_bytes(raw)
        prepared = {'config_sha256': agg.digest(raw), 'archive_sha256': 'a' * 64,
            'task_input_sha256': {'instruction.md': 'd' * 64}, 'host_source_sha256': {'adapter.py': 'e' * 64},
            'semantic_context_profile': agg.CONTEXT_PROFILE, 'model': 'gpt-6.1-sol'}
        if item['semantic_metadata_view'] != 'legacy': prepared['semantic_metadata_view'] = item['semantic_metadata_view']
        (folder / 'preparation.json').write_text(json.dumps(prepared))
        frozen = {key: prepared[key] for key in ('archive_sha256', 'task_input_sha256', 'host_source_sha256')}
        frozen['normalized_configuration'] = agg.normalize_config(config)
        protocol['preparations'].setdefault(item['task'], frozen)
        if reports is not None:
            report, reward = reports[i]
            receipt = {'native_job_result_present': True, 'original_task_inputs_unchanged': True,
                'complete_single_trial_receipt': True, 'trials': [
                {'trial': item['name'] + '-attempt', 'task': item['task'],
                 'reward': {'reward': reward}, 'supervisor': report}]}
            (folder / 'receipt.json').write_text(json.dumps(receipt))
    (root / 'comparison-protocol.json').write_text(json.dumps(protocol))
    return protocol


class MetadataCampaignTests(unittest.TestCase):
    def test_normalization_excludes_metadata_only_and_records_other_exceptions(self):
        left = {'jobs_dir': 'a', 'job_name': 'b', 'agents': [{'kwargs': {
            'semantic_context_profile': agg.CONTEXT_PROFILE}}], 'retry': {'exclude_exceptions': ['Z', 'A']}}
        right = copy.deepcopy(left)
        right.update(jobs_dir='x', job_name='y')
        right['agents'][0]['kwargs']['semantic_metadata_view'] = 'common-bindings@1'
        right['retry']['exclude_exceptions'].reverse()
        self.assertEqual(agg.normalize_config(left), agg.normalize_config(right))
        for field in ('semantic_context_profile', 'semantic_transport_schema', 'coding_reply_mode', 'resource_profile'):
            drift = copy.deepcopy(right)
            drift['agents'][0]['kwargs'][field] = 'changed'
            self.assertNotEqual(agg.normalize_config(left), agg.normalize_config(drift))
        self.assertIn('semantic_context_profile', agg.normalize_config(right)['agents'][0]['kwargs'])

    def test_repeats_retained_and_grouped_without_profile_overwrite(self):
        selections = [selected(), selected('factored-01', 'common-bindings@1'),
            selected('factored-02', 'common-bindings@1', 2), selected('legacy-02', repeat=2)]
        reports = [(model_report(row['name'], row['semantic_metadata_view']), 1) for row in selections]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture(root, selections, reports)
            result = agg.aggregate(root)
            self.assertEqual(len(result['trials']), 4)
            for mode in agg.PROFILES:
                arm = result['arms'][mode]
                self.assertEqual(arm['planned_trials'], 2)
                self.assertEqual(arm['solved_trial_repeats'], 2)
                self.assertEqual(arm['distinct_tasks'], 1)
                self.assertEqual(arm['complete_tokens_all_attempts']['total_tokens'], 220)
                self.assertEqual(len(arm['repeat_ids']), 2)
                self.assertTrue(arm['effective_treatment_comparison_eligible'])

    def test_valid_fallback_charged_requested_arm_but_ineffective(self):
        item = selected('factored-01', 'common-bindings@1')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture(root, [item], [(model_report('fall', item['semantic_metadata_view'], 'legacy'), 0)])
            value = agg.aggregate(root)
            arm = value['arms']['common-bindings@1']
            self.assertNotIn('legacy', value['arms'])
            self.assertEqual(arm['complete_tokens_all_attempts']['total_tokens'], 110)
            self.assertTrue(arm['requested_arm_comparison_eligible'])
            self.assertFalse(arm['effective_treatment_comparison_eligible'])
            self.assertEqual(arm['fallback_trials'], 1)
            dispatch = value['trials'][0]['attempts'][0]['semantic_metadata_dispatch']
            self.assertEqual(dispatch['status'], 'verified_fallback')
            self.assertFalse(dispatch['effective_treatment_observed'])
            self.assertTrue(dispatch['all_coding_inputs_verified_by_retained_audit'])

    def test_context_profile_drift_is_not_normalized_away(self):
        item = selected()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture(root, [item], [(model_report('one'), 1)])
            config_path = root / 'trials' / item['name'] / 'config.json'
            config = json.loads(config_path.read_text())
            config['agents'][0]['kwargs']['semantic_context_profile'] = 'indexed-compact@1'
            config_path.write_text(json.dumps(config))
            row = agg.aggregate(root)['trials'][0]
            self.assertFalse(row['frozen_controls']['fixed_context_profile_matches_configuration'])
            self.assertFalse(row['frozen_controls']['normalized_configuration_matches_frozen_protocol'])
            self.assertFalse(row['requested_arm_comparison_eligible'])

    def test_wrong_requested_arm_is_not_hidden_by_normalization(self):
        item = selected('factored-01', 'common-bindings@1')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture(root, [item], [(model_report('one', item['semantic_metadata_view']), 1)])
            path = root / 'trials' / item['name'] / 'preparation.json'
            prep = json.loads(path.read_text())
            prep['semantic_metadata_view'] = 'legacy'
            path.write_text(json.dumps(prep))
            row = agg.aggregate(root)['trials'][0]
            self.assertFalse(row['frozen_controls']['selected_metadata_view_matches_preparation'])
            self.assertFalse(row['requested_arm_comparison_eligible'])

    def test_missing_receipts_keep_native_usage_known_but_treatment_unknown(self):
        item = selected('factored-01', 'common-bindings@1')
        report = model_report('one', item['semantic_metadata_view'])
        report['provider_invocations'][0].pop('semantic_metadata_view')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture(root, [item], [(report, 1)])
            row = agg.aggregate(root)['trials'][0]
            self.assertEqual(row['complete_tokens']['total_tokens'], 110)
            self.assertFalse(row['requested_arm_comparison_eligible'])
            self.assertIsNone(row['attempts'][0]['semantic_metadata_dispatch']['effective_treatment_observed'])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture(root, [item])
            row = agg.aggregate(root)['trials'][0]
            self.assertEqual(row['state'], 'pending')
            self.assertIsNone(row['complete_tokens']['total_tokens'])
            self.assertIsNone(row['known_token_subtotal']['total_tokens'])

    def test_failed_attempt_tokens_remain_in_arm_numerator(self):
        items = [selected(), selected('legacy-02', repeat=2)]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture(root, items, [(model_report('fail', solved=False), 0), (model_report('pass'), 1)])
            arm = agg.aggregate(root)['arms']['legacy']
            self.assertEqual(arm['tokens_per_solved_task_including_failures'], 220)
            self.assertEqual(arm['solved_trial_repeats'], 1)

    def test_reused_cumulative_session_across_repeats_is_not_double_counted(self):
        items = [selected(), selected('legacy-02', repeat=2)]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture(root, items, [(model_report('reused'), 1), (model_report('reused'), 1)])
            result = agg.aggregate(root)
            self.assertFalse(result['arms']['legacy']['usage_complete'])
            self.assertIsNone(result['arms']['legacy']['complete_tokens_all_attempts']['total_tokens'])
            self.assertIsNone(result['arms']['legacy']['known_total_token_subtotal'])
            self.assertTrue(all('native_cumulative_session_reused_across_trials' in row['comparison_exclusions'] for row in result['trials']))

    def test_raw_receipt_copy_is_one_attempt(self):
        item = selected()
        report = model_report('one')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture(root, [item], [(report, 1)])
            attempt = root / 'trials' / item['name'] / ('jobs/job-' + item['name']) / (item['name'] + '-attempt')
            (attempt / 'agent').mkdir(parents=True)
            (attempt / 'result.json').write_text(json.dumps({'task_name': item['task'], 'verifier_result': {'rewards': {'reward': 1}}}))
            (attempt / 'agent/supervisor-result.json').write_text(json.dumps(report))
            row = agg.aggregate(root)['trials'][0]
            self.assertEqual(row['attempt_count_observed'], 1)
            self.assertEqual(row['complete_tokens']['total_tokens'], 110)

    def test_protocol_rejects_duplicate_ids_and_wrong_axes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            protocol = fixture(root, [selected()])
            variants = []
            duplicate = copy.deepcopy(protocol)
            duplicate['trials'].append(copy.deepcopy(duplicate['trials'][0]))
            variants.append(duplicate)
            duplicate_repeat = copy.deepcopy(duplicate)
            duplicate_repeat['trials'][-1]['name'] = 'another'
            variants.append(duplicate_repeat)
            wrong_context = copy.deepcopy(protocol)
            wrong_context['trials'][0]['semantic_context_profile'] = 'indexed-compact@1'
            variants.append(wrong_context)
            wrong_axis = copy.deepcopy(protocol)
            wrong_axis['pairs_match_except'].append('semantic_context_profile')
            variants.append(wrong_axis)
            for variant in variants:
                with self.assertRaises(ValueError): agg.validate_protocol(variant)

    def test_bad_binding_and_missing_exact_audit_do_not_qualify(self):
        report = model_report('one', 'common-bindings@1')
        report['provider_invocations'][0]['semantic_metadata_view']['selected_complete_sha256'] = 'c' * 64
        value = agg.metadata_observation(report, 'common-bindings@1')
        self.assertFalse(value['all_selection_receipts_bound_to_model_inputs'])
        self.assertIsNone(value['effective_treatment_observed'])
        report = model_report('one', 'common-bindings@1')
        report['context_input_audit'] = {'status': 'unknown'}
        value = agg.metadata_observation(report, 'common-bindings@1')
        self.assertEqual(value['status'], 'unverified')
        self.assertFalse(value['all_coding_inputs_verified_by_retained_audit'])

if __name__ == '__main__': unittest.main(verbosity=2)
