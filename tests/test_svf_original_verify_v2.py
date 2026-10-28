"""Authored RAM orchestration/proof vectors; no actual browser or provider acceptance."""
import copy
import hashlib
import inspect
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid

REPOSITORY = Path(os.environ.get('SVF_FOUNDATION_REPOSITORY_ROOT', str(Path(__file__).resolve().parents[1])))
SCRIPTS = Path(os.environ.get('SVF_VPC_CANDIDATE_SCRIPTS', str(REPOSITORY / 'scripts')))
sys.path.insert(0, str(REPOSITORY / 'tests'))
sys.path.insert(0, str(REPOSITORY / 'scripts')); sys.path.insert(0, str(SCRIPTS))
import test_svf_final_viewport_coverage as shapes
import swissknife_visual_functional_worker as worker
import swissknife_visual_functional_phase_budget as budget
final, llm = shapes.final, shapes.llm


def copy_authored_dual_group(fixture, template, task, folder):
    """Relocate exact typed RAM children; this never executes a browser."""
    group = {'task': task, 'folder': folder, 'children': copy.deepcopy(template['children']),
             'sources': final.source_snapshot(fixture.root, fixture.profile, task)}
    for child in group['children']:
        records = []
        for record in child['artifacts']:
            target = folder / child['viewport']['name'] / Path(record['path']).name
            fixture.write(str(target.relative_to(fixture.root)), (fixture.root / record['path']).read_bytes())
            records.append(final.reference(fixture.root, target))
        child.update(group['sources']); child['artifacts'] = records; child['result_screenshot'] = records[0]
    fixture.persist(group)
    return group


class OriginalVerifyV2Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='svf-original-v2-', dir='/dev/shm')
        self.addCleanup(self.tmp.cleanup); self.addCleanup(patch.stopall)
        self.root = Path(self.tmp.name); self.f = shapes.Fixture(self.root)
        self.task = {'task_id': 'SVF-101', 'kind': 'verify', 'app_id': 'app-0', 'title': 'Original app verification',
                     'acceptance': 'Original intended results, recovery and actual desktop/mobile visuals',
                     'edit_paths': ['swissknife/web/js/app-0.js', 'swissknife/test/e2e/functional-workflows/app-0.json'],
                     'checks': [], 'dependencies': [], 'timeout_seconds': 3600}
        self.f.tasks[0] = self.task; self.f.spec = {'tasks': [self.task]}
        self.f.write(self.f.profile['taskSpecPath'], self.f.spec)
        self.f.write('todo.md', '## SVF-101 Original verification\n\n- Predicted files:\n\n')
        patch.object(final, '_node_source_snapshot', side_effect=self.f.source_vector).start()
        patch.object(worker, 'ROOT', self.root).start(); patch.object(shapes.worker, 'ROOT', self.root).start()
        self.g = self.f.group(); self.latest = None
        self.profile = self.f.profile; self.profile_path = 'config/swissknife_visual_functional_supervisor.json'
        self.produced = []; self.reviewed = []

    def produce(self, argv, **_kwargs):
        self.assertEqual(argv[-1], '--independent-viewports')
        folder = Path(argv[argv.index('--output-dir') + 1]); self.assertEqual(list(folder.iterdir()), [])
        self.latest = copy_authored_dual_group(self.f, self.g, self.task, folder); self.produced.append(argv)
        return {'argv': argv, 'exit_code': 0, 'output_tail': 'Authored finite dual-producer vector only'}

    def provider(self, _profile, task_id, mode, **kwargs):
        self.assertEqual(task_id, self.task['task_id']); self.assertEqual(mode, 'review')
        self.assertEqual(kwargs['predicted_files'], [])
        contexts = [self.root / name for name in kwargs['input_paths'] if Path(name).name == 'context.json']
        self.assertEqual(len(contexts), 1)
        context = json.loads(contexts[0].read_bytes())
        self.assertEqual(context['task']['kind'], 'verify')
        self.assertEqual(context['review_scope'], 'independent_desktop_mobile_semantic_final_review')
        self.assertEqual(context['final_workflow_evidence'], final.binding(self.task, self.f.validated(self.latest)))
        self.assertEqual(kwargs['screenshot_paths'], [c['result_screenshot']['path'] for c in self.latest['children']])
        projections = [json.loads((self.root / name).read_bytes()) for name in kwargs['input_paths']
                       if Path(name).name.startswith('evidence-')]
        self.assertEqual(len(projections), 1)
        self.assertEqual(projections[0]['schema'], 'swissknife.visual-functional-review-input.v2')
        for row in projections[0]['viewports']:
            self.assertEqual(row['semantic_assertions'][0]['observed']['actual'], '50')
            self.assertEqual(row['error_observations'][0]['observed']['actual'], 'Invalid input')
            self.assertIn('failure_recovery', row['backend_call_phases'])
        self.reviewed.append(kwargs)
        return self.f.review(self.latest, context_path=contexts[0])

    def execute(self):
        with patch.object(worker, 'ensure_lease'), patch.object(worker, 'check_owned_sources'), \
                patch.object(worker, 'assert_storage_available'), patch.object(worker, 'assert_no_campaign_hold'), \
                patch.object(worker, 'run', side_effect=self.produce), patch.object(llm, 'invoke_task_model', side_effect=self.provider):
            return worker.execute(self.profile_path, self.profile, self.f.spec, self.task)

    def exhausted_phase(self):
        self.f.review(self.g, decision='needs_changes')
        reference = final.reference(self.root, self.g['review'])
        for _ in range(6):
            admission = budget.admit(self.root, self.task, reference, {})
            budget.finish(self.root, self.task, admission, error_type='AuthoredFailure')
        with self.assertRaises(budget.PhaseRepairBudgetExhausted): budget.admit(self.root, self.task, reference, {})
        self.phase_path = budget.directory(self.root, self.task) / 'required-phase-repair-budget.json'
        return json.loads(self.phase_path.read_bytes())

    def test_real_execute_model_receipt_validate_and_phase_close_with_six_spend_preserved(self):
        before = self.exhausted_phase()
        receipt = self.execute()
        self.assertEqual(len(self.produced), 1); self.assertEqual(len(self.reviewed), 1)
        self.assertEqual(worker.validate(self.profile, self.task), receipt)
        after = json.loads(self.phase_path.read_bytes())
        self.assertEqual(after['state'], 'closed'); self.assertEqual(after['spent'], 6)
        self.assertEqual(after['history'], before['history']); self.assertEqual(after['limit'], before['limit'])
        self.assertEqual(after['gap_request'], before['gap_request']); self.assertEqual(len(after['closures']), 1)
        self.assertEqual(len([a for a in receipt['artifacts'] if Path(a['path']).name == 'workflow.json']), 3)
        self.assertFalse(receipt['work_complete']); self.assertFalse(receipt['completion_authority'])

    def test_exact_two_result_images_remain_selected_when_child_retains_extra_pngs(self):
        for child in self.g['children']:
            name = child['viewport']['name']; target = self.g['folder'] / name / 'initial-diagnostic.png'
            self.f.write(str(target.relative_to(self.root)), (self.root / child['result_screenshot']['path']).read_bytes())
            child['artifacts'].append(final.reference(self.root, target))
        self.f.persist(self.g)
        receipt = self.execute(); self.assertEqual(len(self.reviewed[0]['screenshot_paths']), 2)
        self.assertEqual(sum(a['path'].endswith('.png') for a in receipt['artifacts']), 4)
        worker.validate(self.profile, self.task)

    def test_retained_v2_requires_exact_flag_children_and_artifacts(self):
        receipt = self.execute(); folder = self.root / self.profile['runtimeRoot'] / 'tasks/SVF-101/verification'
        self.assertEqual(worker.retained_workflow_report(self.profile, self.task, receipt, folder), self.latest['report'])
        for mutate in [lambda r: r['checks'][0]['argv'].pop(),
                       lambda r: r['artifacts'].remove(next(a for a in r['artifacts'] if a['path'].endswith('/mobile/workflow.json')))]:
            forged = copy.deepcopy(receipt); mutate(forged)
            with self.assertRaises(ValueError): worker.retained_workflow_report(self.profile, self.task, forged, folder)

    def failure(self, viewport='mobile'):
        folder = self.g['folder'] / viewport
        owner = self.f.write(str((folder / 'failure-owner-responses.json').relative_to(self.root)),
                             {'diagnostic_only': True, 'outcome': 'failed', 'actual': {'count': 0}})
        data = {'schema': 'swissknife.visual-functional-workflow-failure.v1', 'app_id': self.task['app_id'],
                'error': {'code': 'POSTCONDITION_FAILED', 'message': 'actual mobile result differs',
                          'details': {'actual': 0, 'expected': 1}}, 'phase': 'failure_recovery', 'step': 4,
                'source_sha256': self.g['sources']['source_sha256'], 'scenario_sha256': self.g['sources']['scenario_sha256'],
                'artifacts': [final.reference(self.root, owner)], 'actual_desktop': True,
                'functional_acceptance': 'not_evaluated', 'work_complete': False, 'completion_authority': False}
        return self.f.write(str((folder / 'failure.json').relative_to(self.root)), data), owner

    def test_actual_mobile_failure_retains_exact_owner_values_for_real_repair_context_assembly(self):
        self.f.write('swissknife/docs/visual-functional-driver-contract.md', 'Authored readonly scenario grammar fixture.')
        report, owner = self.failure()
        error = worker.ValidationCommandError(['node', 'authored producer'], 1, '', 'actual mobile result differs')
        def failed_producer(_argv, **_kwargs):
            target = Path(_argv[_argv.index('--output-dir') + 1]) / 'mobile'
            owner_copy = self.f.write(str((target / owner.name).relative_to(self.root)), owner.read_bytes())
            data = json.loads(report.read_bytes()); data['artifacts'] = [final.reference(self.root, owner_copy)]
            self.f.write(str((target / 'failure.json').relative_to(self.root)), data)
            raise error
        with patch.object(worker, 'run', side_effect=failed_producer), patch.object(worker, 'assert_no_campaign_hold'), \
                patch.object(worker, 'assert_storage_available'):
            with self.assertRaises(worker.ValidationCommandError):
                worker.workflow(self.profile, self.task, self.g['folder'].parent)
        observed = worker.load_execution_failure(self.profile, self.task)
        self.assertIsNotNone(observed)
        failure = observed['failure']; self.assertTrue(failure['driver_failure']['path'].endswith('/mobile/failure.json'))
        self.assertEqual(failure['diagnostic']['error']['details'], {'actual': 0, 'expected': 1})
        self.assertEqual(failure['diagnostic']['retained_observations'][0]['observation']['actual'], {'count': 0})
        class BeforeRepairProvider(Exception): pass
        def repair_provider(*_args, **kwargs):
            context = next(json.loads((self.root / p).read_bytes()) for p in kwargs['input_paths'] if Path(p).name == 'context.json')
            actual = context['latest_execution_failure']['failure']
            self.assertEqual(actual['driver_failure'], failure['driver_failure'])
            self.assertEqual(actual['diagnostic']['retained_observations'][0]['observation']['actual'], {'count': 0})
            raise BeforeRepairProvider()
        with patch.object(worker, 'assert_no_campaign_hold'), patch.object(worker, 'assert_storage_available'), \
                patch.object(llm, 'invoke_task_model', side_effect=repair_provider):
            with self.assertRaises(BeforeRepairProvider):
                worker.model(self.profile_path, self.task, 'repair', [self.task['edit_paths'][0]], [],
                             self.root / self.profile['runtimeRoot'] / 'tasks/SVF-101/repair-context-audit.json')
        self.assertFalse(failure['completion_authority']); self.assertFalse(failure['work_complete'])

    def test_child_failure_ambiguity_or_symlink_refuses_without_replacing_prior_failure(self):
        report, _ = self.failure()
        worker.remember_execution_failure(self.profile, self.task, ValueError('actual'), stage='workflow', attempt=self.g['folder'])
        recorded = worker.execution_failure_path(self.profile, self.task).read_bytes()
        self.failure('desktop')
        with self.assertRaisesRegex(ValueError, 'ambiguous'):
            worker.remember_execution_failure(self.profile, self.task, ValueError('ambiguous'), stage='workflow', attempt=self.g['folder'])
        self.assertEqual(worker.execution_failure_path(self.profile, self.task).read_bytes(), recorded)
        (self.g['folder'] / 'desktop/failure.json').unlink()
        report.unlink(); report.symlink_to(self.g['folder'] / 'desktop/failure.json')
        with self.assertRaisesRegex(ValueError, 'symbolic'):
            worker.remember_execution_failure(self.profile, self.task, ValueError('symlink'), stage='workflow', attempt=self.g['folder'])
        self.assertEqual(worker.execution_failure_path(self.profile, self.task).read_bytes(), recorded)

    def test_selected_child_failure_retains_original_size_hash_and_source_fences(self):
        report, owner = self.failure()
        worker.remember_execution_failure(self.profile, self.task, ValueError('actual'), stage='workflow', attempt=self.g['folder'])
        self.assertIsNotNone(worker.load_execution_failure(self.profile, self.task))
        owner.write_bytes(b'{"tampered":true}')
        self.assertIsNone(worker.load_execution_failure(self.profile, self.task))
        self.failure()
        worker.remember_execution_failure(self.profile, self.task, ValueError('actual'), stage='workflow', attempt=self.g['folder'])
        self.f.write('swissknife/web/js/app-0.js', '// actual changed source')
        self.assertIsNone(worker.load_execution_failure(self.profile, self.task))
        report.write_bytes(b' ' * 131073)
        worker.remember_execution_failure(self.profile, self.task, ValueError('oversized diagnostic'), stage='workflow', attempt=self.g['folder'])
        value = json.loads(worker.execution_failure_path(self.profile, self.task).read_bytes())
        self.assertNotIn('driver_failure', value)

    def test_legacy_top_level_failure_selection_keeps_its_existing_meaning(self):
        child, _ = self.failure()
        legacy = self.g['folder'] / 'failure.json'; self.f.write(str(legacy.relative_to(self.root)), child.read_bytes())
        worker.remember_execution_failure(self.profile, self.task, ValueError('legacy'), stage='workflow', attempt=self.g['folder'])
        value = worker.load_execution_failure(self.profile, self.task)
        self.assertEqual(value['failure']['driver_failure']['path'], str(legacy.relative_to(self.root)))

    def test_rehashed_missing_mobile_semantics_cannot_close_or_pass_validation(self):
        self.exhausted_phase(); self.execute()
        phase = self.phase_path.read_bytes()
        self.latest['children'][1]['semantic_assertions'].pop(); self.f.persist(self.latest)
        with self.assertRaises(ValueError): worker.validate_workflow(self.profile, self.task, self.latest['report'])
        with self.assertRaises(ValueError): budget.close_after_pass(self.root, self.task, self.latest['review'], self.latest['report'], profile=self.profile)
        self.assertEqual(self.phase_path.read_bytes(), phase)

    def test_wrong_kind_model_context_cannot_rebind_a_positive_original_v2_review(self):
        self.execute(); receipt = json.loads(self.latest['review'].read_bytes())
        record = receipt['input_files'][0]; context = json.loads((self.root / record['path']).read_bytes())
        context['task']['kind'] = 'final-app-verify'; self.f.write(record['path'], context)
        new_ref = final.reference(self.root, self.root / record['path'])
        record.update(sha256=new_ref['sha256'], size_bytes=new_ref['bytes'])
        self.f.replace_review(self.latest, receipt)
        validated = worker.validate_workflow(self.profile, self.task, self.latest['report'])
        with self.assertRaisesRegex(ValueError, 'rebound'):
            final.review_join(self.root, self.profile, self.task, final.binding(self.task, validated), self.latest['review'])

    def test_original_v2_positive_receipt_must_retain_its_exact_joined_review(self):
        receipt = self.execute(); review = final.reference(self.root, self.latest['review'])
        receipt['artifacts'].remove(review)
        self.f.write(self.profile['runtimeRoot'] + '/tasks/SVF-101/receipt.json', receipt)
        with self.assertRaises(ValueError): worker.validate(self.profile, self.task)

    def test_original_v2_review_cannot_swap_exact_result_images(self):
        self.execute(); receipt = json.loads(self.latest['review'].read_bytes())
        receipt['screenshots'].reverse()
        receipt['response']['inspected_screenshots'].reverse()
        self.f.replace_review(self.latest, receipt)
        validated = worker.validate_workflow(self.profile, self.task, self.latest['report'])
        with self.assertRaisesRegex(ValueError, 'images'):
            final.review_join(self.root, self.profile, self.task, final.binding(self.task, validated), self.latest['review'])

    def test_original_v2_source_change_refuses_fresh_validation_and_phase_closure(self):
        self.exhausted_phase(); self.execute(); before = self.phase_path.read_bytes()
        self.f.write('swissknife/web/js/app-0.js', '// changed actual RAM source after review')
        with self.assertRaisesRegex(ValueError, 'stale'):
            worker.validate_workflow(self.profile, self.task, self.latest['report'])
        with self.assertRaises(ValueError):
            budget.close_after_pass(self.root, self.task, self.latest['review'], self.latest['report'], profile=self.profile)
        self.assertEqual(self.phase_path.read_bytes(), before)

    def legacy(self):
        folder = self.root / self.profile['runtimeRoot'] / 'tasks/SVF-101/verification/attempt-legacy123'
        records = []
        for child in self.g['children']:
            name = child['viewport']['name']; target = folder / (name + '.png')
            self.f.write(str(target.relative_to(self.root)), (self.root / child['result_screenshot']['path']).read_bytes())
            records.append(final.reference(self.root, target))
        data = {'schema': 'swissknife.visual-functional-workflow.v1', 'app_id': self.task['app_id'], 'passed': True,
            'actual_desktop': True, 'source_template': False, 'contract_sha256': self.g['sources']['contract_sha256'],
            'source_sha256': self.g['sources']['source_sha256'], 'artifacts': records,
            'semantic_assertions': self.g['children'][0]['semantic_assertions'], 'backend_observations': [], 'unexpected_backend_calls': 0,
            'checks': [{'kind': kind, 'passed': True, 'observation': {'operator': 'equals', 'actual': True, 'expected': True}}
                       for kind in ('primary_result', 'keyboard', 'desktop_layout', 'mobile_layout', 'error_recovery')]}
        report = self.f.write(str((folder / 'workflow.json').relative_to(self.root)), data)
        visual = copy.deepcopy(json.loads(self.g['review'].read_bytes()))
        visual['screenshots'] = [{**{k: record[k] for k in ('path', 'sha256')}, 'size_bytes': record['bytes'],
                                 'width': view['width'], 'height': view['height']} for record, view in zip(records, final.VIEWPORTS)]
        visual['response']['inspected_screenshots'] = [r['path'] for r in records]
        visual['input_files'] = []; visual['invocation_id'] = str(uuid.uuid4())
        visual['attempt_receipt_path'] = str((folder / 'model-invocations' / ('visual-review-' + visual['invocation_id'] + '.json')).relative_to(self.root))
        visual['response_sha256'] = hashlib.sha256(llm._json(visual['response']).encode()).hexdigest()
        review = self.f.write(str((folder / 'visual-review.json').relative_to(self.root)), visual)
        self.f.write(visual['attempt_receipt_path'], visual)
        receipt = {'schema': 'swissknife.visual-functional-task.v1', 'task_id': self.task['task_id'], 'kind': 'verify',
            'task_spec_sha256': worker.stable(self.task), 'artifacts': [final.reference(self.root, report), *records, final.reference(self.root, review)],
            'checks': [{'argv': ['node', 'swissknife/scripts/run-visual-functional-workflow.mjs', '--app', self.task['app_id'],
                '--contracts', self.profile['appContractPath'], '--output-dir', str(folder)], 'exit_code': 0}],
            'detail': {}, 'work_complete': False, 'completion_authority': False}
        return report, receipt

    def test_historical_v1_original_task_receipt_still_passes_entire_validator(self):
        report, receipt = self.legacy()
        self.f.write(self.profile['runtimeRoot'] + '/tasks/SVF-101/receipt.json', receipt)
        self.assertIsNone(worker.validate_workflow(self.profile, self.task, report))
        self.assertEqual(worker.validate(self.profile, self.task), receipt)

    def test_final_followup_still_refuses_v1(self):
        report, _ = self.legacy()
        with self.assertRaises(ValueError): worker.validate_workflow(self.profile, {**self.task, 'kind': 'final-app-verify'}, report)

    def test_fresh_original_producer_cannot_return_v1_even_if_legacy_semantics_pass(self):
        report, _ = self.legacy()
        def v1_producer(argv, **_kwargs):
            target = Path(argv[argv.index('--output-dir') + 1]) / 'workflow.json'
            # This authored V1 remains valid under historical validation, but is invalid as a new dual producer.
            data = json.loads(report.read_bytes())
            for record in data['artifacts']:
                old = self.root / record['path']; new = target.parent / old.name
                self.f.write(str(new.relative_to(self.root)), old.read_bytes()); record.update(final.reference(self.root, new))
            self.f.write(str(target.relative_to(self.root)), data)
            return {'argv': argv, 'exit_code': 0}
        with patch.object(worker, 'assert_storage_available'), patch.object(worker, 'assert_no_campaign_hold'), \
                patch.object(worker, 'run', side_effect=v1_producer), patch.object(llm, 'invoke_task_model') as provider:
            with self.assertRaisesRegex(ValueError, 'fresh app verification'):
                worker.workflow(self.profile, self.task, self.g['folder'].parent)
            provider.assert_not_called()

    def test_real_compiler_keeps_original_review_caps_and_both_probe_values_before_provider(self):
        class BeforeProvider(Exception): pass
        captured = {}
        def stop(_root):
            frame = inspect.currentframe().f_back
            while frame and 'prompt' not in frame.f_locals: frame = frame.f_back
            self.assertIsNotNone(frame); captured.update(prompt=frame.f_locals['prompt'], settings=frame.f_locals['settings'])
            raise BeforeProvider()
        with patch.object(worker, 'assert_no_campaign_hold'), patch.object(worker, 'assert_storage_available'), \
                patch.object(llm, '_load_backend', side_effect=stop):
            with self.assertRaises(BeforeProvider):
                worker.model(self.profile_path, self.task, 'review',
                    [self.profile['appContractPath'], str(self.g['report'].relative_to(self.root))],
                    [child['result_screenshot']['path'] for child in self.g['children']], self.g['folder'] / 'visual-review-audit.json')
        self.assertLessEqual(len(captured['prompt'].encode()), 32768)
        self.assertEqual(captured['settings']['modelContextBytes'], 32768)
        self.assertLessEqual(captured['settings']['maxTurns'], 8); self.assertLessEqual(captured['settings']['maxOutputTokens'], 12288)
        for child in self.g['children']:
            self.assertEqual(captured['prompt'].count(child['session_id']), 1)
            self.assertIn(child['result_screenshot']['path'], captured['prompt'])
        self.assertIn('Invalid input', captured['prompt']); self.assertIn('independent_canonical_sessions', captured['prompt'])

    def test_actual_large_canonical_board_is_hashed_before_original_verify_provider(self):
        # Actual metadata bytes, authored app evidence: this is only a compiler boundary proof.
        board = (REPOSITORY / llm.CANONICAL_TODO_PATH).read_bytes()
        self.assertGreater(len(board), 1048576)
        self.task['task_id'] = 'SVF-403'; self.f.write(self.profile['taskSpecPath'], self.f.spec)
        self.profile['todoPath'] = llm.CANONICAL_TODO_PATH
        self.f.write(self.profile_path, self.profile); self.f.write(llm.CANONICAL_TODO_PATH, board)
        self.g = self.f.group()
        class BeforeProvider(Exception): pass
        captured = {}
        def stop(_root):
            frame = inspect.currentframe().f_back
            while frame and 'prompt' not in frame.f_locals: frame = frame.f_back
            self.assertIsNotNone(frame)
            captured.update(prompt=frame.f_locals['prompt'], records=frame.f_locals['records'])
            raise BeforeProvider()
        with patch.object(worker, 'assert_no_campaign_hold'), patch.object(worker, 'assert_storage_available'), \
                patch.object(llm, '_load_backend', side_effect=stop):
            with self.assertRaises(BeforeProvider):
                worker.model(self.profile_path, self.task, 'review',
                    [self.profile['appContractPath'], str(self.g['report'].relative_to(self.root))],
                    [child['result_screenshot']['path'] for child in self.g['children']], self.g['folder'] / 'visual-review-board-audit.json')
        self.assertLessEqual(len(captured['prompt'].encode()), 32768)
        reference = next(r for r in captured['records'] if r['path'] == llm.CANONICAL_TODO_PATH)
        self.assertEqual(reference['size_bytes'], len(board))
        self.assertEqual(reference['sha256'], hashlib.sha256(board).hexdigest())


if __name__ == '__main__': unittest.main()
