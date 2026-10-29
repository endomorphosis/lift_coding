import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

STAGE = Path(__file__).resolve().parents[1]
LIVE = Path.cwd().resolve()
if not (LIVE / 'scripts/swissknife_visual_functional_worker.py').is_file():
    LIVE = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(STAGE / 'scripts'), str(LIVE / 'scripts')]
import swissknife_visual_functional_native_context as context


class NativeContextTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.relative = 'swissknife/docs/svf-pubsub-app-contract.json'
        self.file = self.root / self.relative
        self.file.parent.mkdir(parents=True)
        self.file.write_text(json.dumps({'schema': 'swissknife.native-foundation-app-context.v1',
            'capability': 'pubsub', 'app_ids': ['p2p-chat-unified', 'p2p-chat'],
            'tools': {'tool': 'ipfs_pubsub_publish'}, 'request_contract': {'dry_run': False},
            'response_contract': {'requires': 'actual peer bytes'}, 'scope': 'Readonly API; original gates decide'}))
        self.task = {'task_id': 'SVF-343', 'kind': 'verify', 'app_id': 'p2p-chat-unified',
                     'execution_inputs': [self.relative], 'edit_paths': ['app.js']}

    def test_only_declared_matching_app_gets_full_readonly_api_context(self):
        value = context.load_native_app_context(self.root, self.task)
        self.assertEqual(value['contract'], json.loads(self.file.read_text()))
        self.assertEqual(value['original']['path'], self.relative)
        self.assertNotIn(self.relative, self.task['edit_paths'])
        self.assertIsNone(context.load_native_app_context(self.root, {**self.task, 'execution_inputs': []}))
        self.assertIsNone(context.load_native_app_context(self.root, {**self.task, 'app_id': 'unrelated'}))

    def test_wrong_capability_app_or_schema_refuses(self):
        original = json.loads(self.file.read_text())
        for key, value in [('capability', 'supervisor'), ('app_ids', ['other']), ('schema', 'wrong')]:
            with self.subTest(key=key):
                self.file.write_text(json.dumps({**original, key: value}))
                with self.assertRaises(ValueError):
                    context.load_native_app_context(self.root, self.task)

    def test_symlink_oversized_duplicate_and_empty_context_refuse(self):
        original = self.file.read_bytes()
        self.file.unlink()
        self.file.symlink_to(self.root / 'missing')
        with self.assertRaises(ValueError):
            context.load_native_app_context(self.root, self.task)
        self.file.unlink()
        for data in [b' ' * 8193, b'{"schema":1,"schema":2}', b'']:
            self.file.write_bytes(data)
            with self.assertRaises(ValueError):
                context.load_native_app_context(self.root, self.task)
        self.file.write_bytes(original)

    def test_actual_worker_supplies_contract_inline_before_router_call(self):
        spec = importlib.util.spec_from_file_location('native_context_worker', STAGE / 'scripts/swissknife_visual_functional_worker.py')
        worker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(worker)
        import swissknife_visual_functional_llm as adapter
        (self.root / 'app.js').write_text('const actual = 1;\n')
        contracts = self.root / 'contracts.json'
        contracts.write_text(json.dumps({'apps': [{'app_id': 'p2p-chat-unified'}]}))
        (self.root / 'swissknife/docs/visual-functional-driver-contract.md').write_text('Root scenario grammar.')
        profile = {'runtimeRoot': 'data/agent_supervisor/swissknife_visual_functional',
                   'appContractPath': 'contracts.json', 'taskSpecPath': 'tasks.json', 'humanPlanPath': 'plan.md',
                   'llm': {'provider': 'grok_cli', 'model': 'grok-4.7', 'repairReadPolicy': 'inline_only'}}
        output = self.root / profile['runtimeRoot'] / 'tasks/SVF-343/repair.json'
        observed = []
        class InspectedBeforeProvider(Exception): pass
        def inspect(*args, **kwargs):
            inputs = kwargs['input_paths']
            body = json.loads((self.root / inputs[0]).read_text())
            observed.append(body['native_backend_contract'])
            self.assertEqual(body['native_backend_contract']['contract'], json.loads(self.file.read_text()))
            self.assertEqual(body['task']['edit_paths'], ['app.js'])
            self.assertIn('app.js', inputs)
            raise InspectedBeforeProvider()
        with patch.object(worker, 'ROOT', self.root), patch.object(worker, 'load', return_value=(profile, {'tasks': [self.task]})), \
                patch.object(worker, 'assert_no_campaign_hold'), patch.object(worker, 'assert_storage_available'), \
                patch.object(worker, 'workflow_fixtures', return_value=None), patch.object(worker, 'load_execution_failure', return_value=None), \
                patch.object(worker, 'load_repair_feedback', return_value=None), patch.object(adapter, 'invoke_task_model', side_effect=inspect):
            with self.assertRaises(InspectedBeforeProvider):
                worker.model('profile.json', self.task, 'repair', ['app.js'], [], output)
        self.assertEqual(len(observed), 1)


if __name__ == '__main__':
    unittest.main()
