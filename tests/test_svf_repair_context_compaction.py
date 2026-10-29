"""Lossless repair-packet formatting; finite authored fixtures never load providers."""
from __future__ import annotations
import inspect
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, os.environ.get('SVF_REPAIR_CONTEXT_CANDIDATE_SCRIPTS', str(BASE / 'scripts')))
import swissknife_visual_functional_worker as worker
import swissknife_visual_functional_llm as adapter


class ProviderBoundary(Exception):
    pass


class RepairCompactionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir='/dev/shm')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.addCleanup(patch.stopall)
        patch.object(worker, 'ROOT', self.root).start()
        self.profile = {'todoPath': 'board.todo.md', 'runtimeRoot': 'data/agent_supervisor/swissknife_visual_functional',
                        'appContractPath': 'contracts.json', 'taskSpecPath': 'tasks.json', 'humanPlanPath': 'plan.md',
                        'llm': {'provider': 'grok_cli', 'model': 'grok-4.7', 'repairReadPolicy': 'inline_only',
                                'allowLocalFallback': False, 'allowCrossProviderFallback': False,
                                'modelContextBytes': 65536}}
        self.task = {'task_id': 'SVF-503', 'kind': 'verify', 'app_id': 'demo',
                     'edit_paths': ['app.js', 'scenario.json'], 'context_paths': [], 'checks': []}
        self.write('profile.json', json.dumps(self.profile))
        self.write('board.todo.md', '## SVF-503 Verify authored app\n- Status: ready\n- Predicted files: app.js, scenario.json\n')
        self.write('tasks.json', json.dumps({'tasks': [self.task]}))
        self.write('contracts.json', json.dumps({'apps': [{'app_id': 'demo', 'title': 'Authored app'}]}))
        self.write('scenario.json', '{"steps":[{"action":"fill","value":"\\\"\\\\\\tλ\\n"}]}\n')
        self.write('support.js', '// bounded readonly support\n' * 2000)
        self.write('swissknife/docs/visual-functional-driver-contract.md', 'Exact authored scenario grammar.\n')
        self.context = {'task': self.task, 'authority': 'proposal_only; do not manufacture test evidence',
                        'complete_edit_targets': [], 'latest_execution_failure': {
                            'original': {'path': 'last-execution-failure.json', 'sha256': 'a' * 64, 'bytes': 12345},
                            'failure': {'work_complete': False, 'completion_authority': False,
                                'diagnostic': {'schema': 'swissknife.visual-functional-workflow-failure.v1',
                                    'phase': 'failure_recovery', 'step': 3,
                                    'error': {'code': 'POSTCONDITION_FAILED', 'details': {
                                        'actual': 'No query failure.', 'expected': 'The selection was kept.'}},
                                    'observed': [{'index': i, 'text': 'literal \\"\t\nλ雪',
                                        'values': [None, False, True, i, 1.2345678901234, -0.0],
                                        'nested': {'source_sha256': 'b' * 64, 'path': 'actual/source.js'}}
                                        for i in range(40)]}}}}
        self.directory = self.root / self.profile['runtimeRoot'] / 'tasks/SVF-503/model-inputs/authored'
        self.context_path = self.directory / 'context.json'
        # Calibrate an authored full target to leave supporting-excerpt space
        # only after lossless packet compaction. The declared cap stays fixed.
        compact_cost = self.cost(self.context_name, json.dumps(self.context, separators=(',', ':')) + '\n')
        source_bytes = 65536 - compact_cost - 4096 - 512 - 6500
        self.write('app.js', '// UNIQUE original anchor λ\\"\n' + 'x' * source_bytes)
        self.inputs = ['app.js', 'scenario.json', 'support.js']

    @property
    def context_name(self):
        return str(self.context_path.relative_to(self.root))

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    @staticmethod
    def cost(name, text):
        return len(json.dumps({'path': name, 'content': text}, ensure_ascii=False, separators=(',', ':')).encode())

    def select(self, compact=True):
        worker.atomic_json(self.context_path, self.context, compact=compact)
        return worker._repair_inputs(self.profile, self.task, self.inputs, self.context_path, self.directory, 65536)

    def compile(self, selected):
        captured = {}
        def refuse(_root):
            frame = inspect.currentframe().f_back
            while frame is not None and 'prompt' not in frame.f_locals:
                frame = frame.f_back
            self.assertIsNotNone(frame)
            for key in ('prompt', 'contract', 'settings', 'records'):
                captured[key] = frame.f_locals[key]
            raise ProviderBoundary
        with patch.object(adapter, '_load_backend', side_effect=refuse) as backend:
            with self.assertRaises(ProviderBoundary):
                adapter.invoke_task_model('profile.json', self.task['task_id'], 'repair', root=self.root,
                                          input_paths=[self.context_name, *selected], predicted_files=self.task['edit_paths'])
            self.assertEqual(backend.call_count, 1)
        return captured

    def test_previously_oversize_packet_reaches_real_adapter_boundary_losslessly(self):
        with self.assertRaises(adapter.ModelContextBudgetError):
            self.select(compact=False)
        selected, original, complete = self.select()
        self.context['complete_edit_targets'] = complete
        worker.atomic_json(self.context_path, self.context, compact=True)
        compiled = self.compile(selected)
        self.assertLessEqual(len(compiled['prompt'].encode()), 65536)
        self.assertEqual(compiled['settings']['modelContextBytes'], 65536)
        self.assertEqual(adapter.REPAIR_MAX_PROMPT_BYTES, 262144)
        texts = {row['path']: row['content'] for row in compiled['contract']['input_files']}
        self.assertEqual(json.loads(texts[self.context_name]), self.context)
        self.assertEqual({row['path'] for row in complete}, set(self.task['edit_paths']))
        for name in self.task['edit_paths']:
            self.assertEqual(texts[name], (self.root / name).read_text())
            self.assertIn(worker.artifact(self.root / name), complete)
        for row in original:
            self.assertEqual(row, worker.artifact(self.root / row['path']))
        # The full readonly source remains individually hash-bound even though
        # its explicitly labelled excerpt is all the budget can inline.
        source = next(name for name in selected if Path(name).name.startswith('source-'))
        self.assertEqual(json.loads((self.root / source).read_text())['original'], worker.artifact(self.root / 'support.js'))

    def test_unicode_escaping_numeric_types_and_negative_zero_survive(self):
        worker.atomic_json(self.context_path, self.context, compact=True)
        actual = json.loads(self.context_path.read_text())
        self.assertEqual(actual, self.context)
        values = actual['latest_execution_failure']['failure']['diagnostic']['observed'][0]['values']
        self.assertEqual([type(value) for value in values], [type(None), bool, bool, int, float, float])
        self.assertEqual(math.copysign(1, values[-1]), -1)
        self.assertIn('λ雪', actual['latest_execution_failure']['failure']['diagnostic']['observed'][0]['text'])
        self.assertNotIn('\n  "', self.context_path.read_text())
        self.assertTrue(self.context_path.read_bytes().endswith(b'\n'))

    def test_default_artifact_serialization_remains_byte_for_byte_unchanged(self):
        worker.atomic_json(self.context_path, self.context)
        self.assertEqual(self.context_path.read_text(), json.dumps(self.context, indent=2) + '\n')

    def test_compact_nonfinite_refuses_without_replacing_old_artifact(self):
        self.write(self.context_name, 'previous exact owned artifact\n')
        for invalid in (float('nan'), float('inf'), -float('inf')):
            with self.assertRaises(ValueError):
                worker.atomic_json(self.context_path, {'actual': invalid}, compact=True)
            self.assertEqual(self.context_path.read_text(), 'previous exact owned artifact\n')
        self.assertEqual(list(self.directory.glob('.svf-*')), [])

    def test_complete_target_still_refuses_when_it_cannot_fit(self):
        self.write('app.js', 'a' * 65000)
        with patch.object(adapter, '_load_backend') as backend:
            with self.assertRaises(adapter.ModelContextBudgetError):
                self.select()
            backend.assert_not_called()
        self.assertEqual((self.root / 'app.js').read_text(), 'a' * 65000)

    def test_file_limit_and_final_prompt_limit_remain_enforced_before_backend(self):
        self.write('app.js', 'a' * 250001)
        with self.assertRaises(adapter.ModelContextBudgetError) as error:
            self.select()
        self.assertEqual(error.exception.limit_bytes, 250000)
        self.write('app.js', 'a' * 64000)
        worker.atomic_json(self.context_path, self.context, compact=True)
        with patch.object(adapter, '_load_backend') as backend:
            with self.assertRaises(adapter.ModelContextBudgetError) as error:
                adapter.invoke_task_model('profile.json', 'SVF-503', 'repair', root=self.root,
                                          input_paths=[self.context_name, 'app.js', 'scenario.json'], predicted_files=self.task['edit_paths'])
            self.assertEqual(error.exception.limit_bytes, 65536)
            backend.assert_not_called()

    def test_actual_model_context_writes_are_compact_but_other_artifacts_unchanged(self):
        self.write('app.js', '// bounded current full source\n')
        self.profile['llm'].pop('modelContextBytes')
        self.write('profile.json', json.dumps(self.profile))
        captures = []
        def invoke(*args, **kwargs):
            self.assertEqual(args[2], 'repair')
            context_path = self.root / kwargs['input_paths'][0]
            raw = context_path.read_text()
            value = json.loads(raw)
            self.assertEqual(raw, json.dumps(value, separators=(',', ':')) + '\n')
            self.assertEqual({row['path'] for row in value['complete_edit_targets']}, set(self.task['edit_paths']))
            captures.append(value)
            return {'success': True}
        with patch.object(worker, 'assert_storage_available'), patch.object(worker, 'load_execution_failure', return_value=None), \
                patch.object(adapter, 'invoke_task_model', side_effect=invoke), patch.object(adapter, 'validate_model_receipt'):
            worker.model('profile.json', self.task, 'repair', self.task['edit_paths'], [],
                         self.root / self.profile['runtimeRoot'] / 'tasks/SVF-503/repair.json')
        self.assertEqual(len(captures), 1)

    def test_near_limit_escaping_and_unicode_use_exact_serialized_byte_cost(self):
        worker.atomic_json(self.context_path, self.context, compact=True)
        overhead = (self.cost(self.context_name, self.context_path.read_text())
                    + len(json.dumps((self.root / 'board.todo.md').read_text(), ensure_ascii=False).encode())
                    + 4096 + 256 * len(self.task['edit_paths']))
        scenario_cost = self.cost('scenario.json', (self.root / 'scenario.json').read_text())
        unit = '\\\"\tλ雪\n'
        left, right = 0, 10000
        while left + 1 < right:
            middle = (left + right) // 2
            if overhead + self.cost('app.js', unit * middle) + scenario_cost + 2048 <= 65536 - 64:
                left = middle
            else:
                right = middle
        self.write('app.js', unit * left)
        selected, _, complete = self.select()
        self.context['complete_edit_targets'] = complete
        worker.atomic_json(self.context_path, self.context, compact=True)
        compiled = self.compile(selected)
        prompt_bytes = len(compiled['prompt'].encode())
        self.assertLessEqual(prompt_bytes, 65536)
        self.assertGreater(prompt_bytes, 60000)
        texts = {row['path']: row['content'] for row in compiled['contract']['input_files']}
        self.assertEqual(texts['app.js'], unit * left)
        self.assertEqual(json.loads(texts[self.context_name]), self.context)

    def test_compact_packet_does_not_bypass_source_fence(self):
        selected, _, _ = self.select()
        original = adapter._unchanged
        def drift(root, records):
            self.write('app.js', 'concurrent source mutation')
            original(root, records)
        with patch.object(adapter, '_unchanged', side_effect=drift), patch.object(adapter, '_load_backend') as backend:
            with self.assertRaisesRegex(adapter.ModelAdapterError, 'changed'):
                adapter.invoke_task_model('profile.json', 'SVF-503', 'repair', root=self.root,
                                          input_paths=[self.context_name, *selected], predicted_files=self.task['edit_paths'])
            backend.assert_not_called()


if __name__ == '__main__':
    unittest.main()
