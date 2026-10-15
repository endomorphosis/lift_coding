"""Live preparation cannot inherit missing, tampered or unprofitable offline evidence."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('query_preparation', Path(__file__).with_name('prepare-campaign.py'))
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class GateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source'
        paths = {'experiment': 'benchmarks/agent_supervisor/container_coding/terminal_query_reference_experiment.py',
            'query_reference_codec': 'ipfs_accelerate_py/agent_supervisor/runtime/semantic_query_reference.py',
            'router': 'ipfs_accelerate_py/agent_supervisor/runtime/router_implementation_runner.py',
            'input_audit': 'benchmarks/agent_supervisor/container_coding/terminal_context_audit.py'}
        hashes = {}
        for key, relative in paths.items():
            path = self.source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(key.encode())
            hashes[key] = hashlib.sha256(key.encode()).hexdigest()
        self.qualification = {'schema': 'terminal-query-reference-experiment@1', 'qualified': True,
            'provider_calls': 0, 'tasks': [{'task_name': task, 'qualified': True,
                'implementation_sha256': hashes, 'coding_reply_mode': 'ordinary-completion@1',
                'stale_required_instruction_refused': True, 'matched_source_selection': True,
                'arms': [{'policy': policy, 'positive_reference_observed': i == 1,
                    'historical_replay_after_workspace_removed': True, 'full_input_bytes': 2000 - i * 100,
                    'full_input_proxy_tokens': 600 - i * 20} for i, policy in enumerate(MODULE.MODES)],
                'comparison': {'input_proxy_tokens_change': -20}}
                for task in ['tune-mjcf', 'llm-inference-batching-scheduler']]}
        (self.root / 'public-final').mkdir()

    def write(self, qualification=None):
        raw = json.dumps(qualification or self.qualification).encode()
        (self.root / 'public-final/qualification.json').write_bytes(raw)
        (self.root / 'independent-public-replay.json').write_text(json.dumps({
            'qualification_sha256': hashlib.sha256(raw).hexdigest(), 'all_four_inputs_exact': True}))

    def test_positive_current_source_and_exact_pair_pass(self):
        self.write()
        result = MODULE.offline_gate(self.root, self.source)
        self.assertTrue(result['source_bodies_match'])
        self.assertEqual(len(result['metrics']), 2)

    def test_evidence_and_improvement_mutations_refuse(self):
        mutations = [lambda q: q.update(qualified=False), lambda q: q['tasks'].pop(),
            lambda q: q['tasks'][0]['arms'][1].update(positive_reference_observed=False),
            lambda q: q['tasks'][0]['arms'][1].update(full_input_proxy_tokens=600),
            lambda q: q['tasks'][0]['arms'][1].update(full_input_bytes=2000),
            lambda q: q['tasks'][0].update(stale_required_instruction_refused=False),
            lambda q: q['tasks'][0]['implementation_sha256'].update(router='0'*64)]
        for mutate in mutations:
            value = copy.deepcopy(self.qualification)
            mutate(value)
            self.write(value)
            with self.assertRaises(ValueError):
                MODULE.offline_gate(self.root, self.source)

    def test_replay_hash_or_source_mutation_refuse(self):
        self.write()
        (self.root / 'independent-public-replay.json').write_text('{}')
        with self.assertRaises(ValueError):
            MODULE.offline_gate(self.root, self.source)
        self.write()
        path = self.source / 'ipfs_accelerate_py/agent_supervisor/runtime/semantic_query_reference.py'
        path.write_bytes(b'changed')
        with self.assertRaises(ValueError):
            MODULE.offline_gate(self.root, self.source)

    def test_normalization_keeps_other_comparison_controls(self):
        base = {'job_name': 'a', 'jobs_dir': '/a', 'agents': [{'kwargs': {'query_reference_policy': 'legacy', 'model': 'pinned'}}]}
        changed = copy.deepcopy(base)
        changed['job_name'] = 'b'
        changed['agents'][0]['kwargs']['query_reference_policy'] = MODULE.MODES[1]
        self.assertEqual(MODULE.normalize_config(base), MODULE.normalize_config(changed))
        changed['agents'][0]['kwargs']['model'] = 'different'
        self.assertNotEqual(MODULE.normalize_config(base), MODULE.normalize_config(changed))


if __name__ == '__main__':
    unittest.main()
