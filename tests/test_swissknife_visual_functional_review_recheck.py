"""Source-fenced review admission without provider calls or counter mutation."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

STAGE = Path(__file__).resolve().parents[1]
LIVE = Path.cwd().resolve()
if not (LIVE / 'tests/test_swissknife_visual_functional_phase_budget.py').is_file():
    LIVE = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(STAGE / 'scripts'), str(LIVE / 'scripts')]
import swissknife_visual_functional_review_recheck as fence
import swissknife_visual_functional_phase_budget as budget

spec = importlib.util.spec_from_file_location('phase_fixture', LIVE / 'tests/test_swissknife_visual_functional_phase_budget.py')
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)
worker_spec = importlib.util.spec_from_file_location('staged_worker', STAGE / 'scripts/swissknife_visual_functional_worker.py')
staged_worker = importlib.util.module_from_spec(worker_spec)
worker_spec.loader.exec_module(staged_worker)


class ReviewRecheckTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.PhaseBudgetTests(methodName='runTest')
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.root, self.task = self.f.root, self.f.task
        self.profile = {'runtimeRoot': 'data/agent_supervisor/swissknife_visual_functional',
                        'todoPath': 'board.md', 'objectivePath': 'goals.md', 'taskSpecPath': 'tasks.json'}
        self.task['execution_inputs'] = ['app.js', 'desktop.js', 'board.md', 'goals.md', 'tasks.json']
        for _ in range(6):
            self.f.admit()
        with self.assertRaises(budget.PhaseRepairBudgetExhausted) as raised:
            self.f.admit()
        self.record = raised.exception.record
        self.budget_before = self.f.journal.read_bytes()

    def remember(self):
        fence.remember_exhaustion(self.root, self.profile, self.task, self.record)

    def assert_budget_unchanged(self):
        self.assertEqual(self.f.journal.read_bytes(), self.budget_before)

    def test_old_exhausted_phase_without_new_fence_gets_one_original_recheck(self):
        fence.assert_recheck_allowed(self.root, self.profile, self.task)
        self.assert_budget_unchanged()

    def test_unchanged_failed_exhausted_phase_blocks_before_new_browser_or_provider(self):
        self.remember()
        for _ in range(3):
            with self.assertRaises(fence.UnchangedExhaustedVisualReview):
                fence.assert_recheck_allowed(self.root, self.profile, self.task)
        self.assert_budget_unchanged()

    def test_actual_app_or_shared_source_change_admits_only_original_acceptance(self):
        for name in ['app.js', 'desktop.js']:
            with self.subTest(source=name):
                self.remember()
                self.f.put(name, 'a real new revision of ' + name)
                fence.assert_recheck_allowed(self.root, self.profile, self.task)
                self.assert_budget_unchanged()

    def test_board_progress_or_unrelated_spec_bytes_cannot_buy_a_paid_review(self):
        self.remember()
        for name in ['board.md', 'goals.md', 'tasks.json']:
            self.f.put(name, 'unrelated completed task progress')
        with self.assertRaises(fence.UnchangedExhaustedVisualReview):
            fence.assert_recheck_allowed(self.root, self.profile, self.task)
        self.assert_budget_unchanged()

    def test_corrupt_fence_or_failed_review_tamper_fails_closed(self):
        self.remember()
        path = fence._path(self.root, self.task)
        original = path.read_bytes()
        path.write_text('{malformed')
        with self.assertRaises(ValueError):
            fence.assert_recheck_allowed(self.root, self.profile, self.task)
        path.write_bytes(original)
        self.f.review.write_text(self.f.review.read_text() + ' ')
        with self.assertRaises(ValueError):
            fence.assert_recheck_allowed(self.root, self.profile, self.task)
        self.assert_budget_unchanged()

    def test_dangling_fence_symlink_does_not_bypass_admission(self):
        fence._path(self.root, self.task).symlink_to(self.root / 'absent')
        with self.assertRaises(ValueError):
            fence.assert_recheck_allowed(self.root, self.profile, self.task)
        self.assert_budget_unchanged()

    def test_mismatched_task_or_phase_history_is_rejected(self):
        self.remember()
        path = fence._path(self.root, self.task)
        value = json.loads(path.read_text())
        for key, replacement in [('task_id', 'SVF-OTHER'), ('history_sha256', '0' * 64), ('completion_authority', True)]:
            with self.subTest(key=key):
                edited = {**value, key: replacement}
                path.write_text(json.dumps(edited))
                with self.assertRaises(ValueError):
                    fence.assert_recheck_allowed(self.root, self.profile, self.task)
        self.assert_budget_unchanged()

    def test_actual_worker_refuses_unchanged_source_before_browser_or_paid_model(self):
        worker = staged_worker
        self.remember()
        with patch.object(worker, 'ROOT', self.root), patch.object(worker, 'ensure_lease') as lease, \
                patch.object(worker, 'check_owned_sources'), patch.object(worker, 'assert_storage_available') as storage, \
                patch.object(worker, 'workflow') as browser, patch.object(worker, 'model') as model:
            with self.assertRaises(fence.UnchangedExhaustedVisualReview):
                worker.execute('profile.json', self.profile, {'tasks': [self.task]}, self.task)
            lease.assert_called_once()
            storage.assert_called_once()
            browser.assert_not_called()
            model.assert_not_called()
        self.assert_budget_unchanged()

    def test_valid_original_pass_closes_phase_and_allows_later_revalidation(self):
        self.remember()
        workflow = self.f.attempt / 'workflow.json'
        workflow.write_text(json.dumps({'schema': 'swissknife.visual-functional-workflow.v1',
                                       'passed': True, 'actual_desktop': True, 'app_id': 'notes'}))
        projection = self.f.base / 'model-inputs/review/workflow.json'
        self.f.put(str(projection.relative_to(self.root)), json.dumps({
            'schema': 'swissknife.visual-functional-review-input.v1', 'original': budget._ref(self.root, workflow)}))
        self.f.review.write_text(json.dumps(self.f.receipt('review', 'pass', [budget._ref(self.root, projection)])))
        budget.close_after_pass(self.root, self.task, self.f.review, workflow)
        fence.assert_recheck_allowed(self.root, self.profile, self.task)
        current = json.loads(self.f.journal.read_text())
        self.assertEqual(current['spent'], 6)
        self.assertEqual(len(current['history']), 6)
        self.assertEqual(current['state'], 'closed')


if __name__ == '__main__':
    unittest.main()
