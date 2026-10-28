"""Pure authored RAM report tests. No commands, SDK, services or provider calls."""
from pathlib import Path
import hashlib
import json
import os
import sys
import tempfile
import unittest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / 'scripts'))
import swissknife_visual_functional_native_context as helper
RAM = Path(os.environ.get('SVF_BACKEND_REPORT_TEST_TMPDIR', '/dev/shm'))

class ReportLoader(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='svf-backend-report-', dir=RAM)
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.task = {'task_id': 'SVF-044', 'kind': 'backend-repair', 'acceptance': 'Authored original-check fixture',
            'checks': [['python3', '-B', 'tests/check.py'], ['python3', '-B', 'scripts/gate.py', '--verify']],
            'edit_paths': ['scripts/backend.py'], 'execution_inputs': ['scripts/readonly.py'],
            'semantic_recovery_inputs': ['scripts/recovery-only.py'], 'dependencies': ['SVF-042'],
            'context_paths': [], 'llm_limits': {'maxTurns': 1}, 'timeout_seconds': 30}
        paths = [*helper.BACKEND_CONTROLLER_INPUTS, 'tests/check.py', 'scripts/gate.py',
                 'scripts/backend.py', 'scripts/readonly.py', 'scripts/recovery-only.py']
        for name in paths:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('authored static source; never executed: ' + name)

    def records(self):
        return [{'index': index, 'declared_argv': list(command),
                 'executed_argv': [sys.executable, *command[1:]], 'exit_code': 0,
                 'output_tail': 'authored check passed'} for index, command in enumerate(self.task['checks'])]

    def create(self, *, failed=False):
        rows = self.records()
        diagnostic = None
        if failed:
            stdout, stderr = 'authored stdout', 'authored actual-command exception'
            rows[-1]['exit_code'] = 1
            rows[-1]['output_tail'] = helper.backend_output_tail(stdout, stderr)
            diagnostic = {'stage': 'command', 'code': 'ValidationCommandError', 'check_index': 1,
                          'argv': rows[-1]['executed_argv'], 'exit_code': 1,
                          'stdout_tail': stdout, 'stderr_tail': stderr}
        reference = helper.write_backend_check_report(self.root, self.task,
            source_sha256=helper.backend_source_hashes(self.root, self.task), checks=rows, diagnostic=diagnostic)
        return reference, self.root / reference['path']

    def rewrite(self, path, report, reference):
        # Deliberately malformed authored reports have freshly matching hashes.
        # These negative tests must exercise semantic validation too.
        raw = json.dumps(report, separators=(',', ':')).encode()
        path.write_bytes(raw)
        return {**reference, 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}

    def test_complete_pass_is_context_only_and_private(self):
        reference, path = self.create()
        loaded = helper.load_backend_check_report(self.root, self.task, reference)
        context = helper.backend_check_model_context(loaded)
        self.assertEqual(loaded['report']['outcome'], 'passed')
        self.assertFalse(context['completion_authority'])
        self.assertFalse(context['work_complete'])
        self.assertLessEqual(len(json.dumps(context).encode()), 16384)
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(path.parent.stat().st_mode & 0o777, 0o700)

    def test_real_command_failure_shape_is_not_a_workflow(self):
        reference, path = self.create(failed=True)
        loaded = helper.load_backend_check_report(self.root, self.task, reference)
        self.assertEqual(loaded['report']['outcome'], 'failed')
        self.assertEqual(loaded['report']['diagnostic']['code'], 'ValidationCommandError')
        self.assertNotIn('workflow', loaded['report'])
        self.assertEqual(loaded['report']['diagnostic']['argv'], self.records()[-1]['executed_argv'])

    def test_hash_changed_without_rebinding_is_refused(self):
        reference, path = self.create()
        path.write_bytes(path.read_bytes() + b' ')
        with self.assertRaises(ValueError): helper.load_backend_check_report(self.root, self.task, reference)

    def test_readonly_source_mutation_invalidates_report(self):
        reference, _ = self.create()
        (self.root / 'scripts/readonly.py').write_text('changed readonly source')
        with self.assertRaisesRegex(ValueError, 'stale'): helper.load_backend_check_report(self.root, self.task, reference)

    def test_recovery_only_source_mutation_invalidates_report(self):
        reference, _ = self.create()
        (self.root / 'scripts/recovery-only.py').write_text('changed semantic recovery compiler')
        with self.assertRaisesRegex(ValueError, 'stale'): helper.load_backend_check_report(self.root, self.task, reference)

    def test_task_policy_mutation_invalidates_report(self):
        reference, _ = self.create()
        changed = {**self.task, 'acceptance': 'different actual acceptance'}
        with self.assertRaisesRegex(ValueError, 'stale'): helper.load_backend_check_report(self.root, changed, reference)

    def test_report_symlink_or_public_permissions_refused(self):
        reference, path = self.create()
        path.chmod(0o644)
        with self.assertRaises(ValueError): helper.load_backend_check_report(self.root, self.task, reference)
        path.chmod(0o600)
        original = path.with_name('retained-original.json')
        path.rename(original)
        path.symlink_to(original)
        with self.assertRaises(ValueError): helper.load_backend_check_report(self.root, self.task, reference)

    def test_partial_pass_and_skipped_original_command_refused(self):
        reference, path = self.create()
        report = json.loads(path.read_text())
        report['checks'] = report['checks'][:1]
        malformed = self.rewrite(path, report, reference)
        with self.assertRaises(ValueError): helper.load_backend_check_report(self.root, self.task, malformed)

    def test_arbitrary_argument_cannot_be_added_to_observed_command(self):
        reference, path = self.create()
        report = json.loads(path.read_text())
        report['checks'][0]['executed_argv'].append('--skip-validation')
        malformed = self.rewrite(path, report, reference)
        with self.assertRaises(ValueError): helper.load_backend_check_report(self.root, self.task, malformed)

    def test_boolean_indices_are_not_integers(self):
        reference, path = self.create(failed=True)
        report = json.loads(path.read_text())
        for target, key, value in [(report['checks'][0], 'index', False), (report['diagnostic'], 'check_index', True)]:
            old = target[key]
            target[key] = value
            malformed = self.rewrite(path, report, reference)
            with self.assertRaises(ValueError): helper.load_backend_check_report(self.root, self.task, malformed)
            target[key] = old

    def test_nonfinite_timestamp_and_invalid_pid_refused(self):
        reference, path = self.create()
        report = json.loads(path.read_text())
        for field, value in [('observed_at', float('inf')), ('observed_at', -1), ('producer_pid', 0)]:
            with self.subTest(field=field, value=value):
                malformed = self.rewrite(path, {**report, field: value}, reference)
                with self.assertRaises(ValueError): helper.load_backend_check_report(self.root, self.task, malformed)

    def test_diagnostic_cannot_disagree_with_failing_output(self):
        reference, path = self.create(failed=True)
        report = json.loads(path.read_text())
        report['diagnostic']['stderr_tail'] = 'invented unrelated error'
        malformed = self.rewrite(path, report, reference)
        with self.assertRaises(ValueError): helper.load_backend_check_report(self.root, self.task, malformed)

    def test_duplicate_json_keys_refused_even_with_matching_hash(self):
        reference, path = self.create()
        raw = path.read_bytes()
        raw = b'{"schema":"duplicate",' + raw[1:]
        path.write_bytes(raw)
        malformed = {**reference, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        with self.assertRaisesRegex(ValueError, 'duplicate'): helper.load_backend_check_report(self.root, self.task, malformed)

    def test_other_task_namespace_refused(self):
        reference, _ = self.create()
        changed = {**self.task, 'task_id': 'SVF-043'}
        with self.assertRaises(ValueError): helper.load_backend_check_report(self.root, changed, reference)

if __name__ == '__main__': unittest.main(verbosity=2)
