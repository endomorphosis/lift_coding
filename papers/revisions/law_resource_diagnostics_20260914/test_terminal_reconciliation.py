import copy
import errno
import json
from pathlib import Path
import unittest

from terminal_reconciliation import reconcile_enodev

HERE = Path(__file__).resolve().parent


class TerminalReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.root = HERE / 'kernel_probe_v2'
        read = lambda name: json.loads((self.root / name).read_text())
        self.detail = read('stale_descriptor_probe.json')['detail']
        self.leaf = read('leaf_poll_observations.json')['samples'][-1]
        self.before, self.final = read('parent_before.json'), read('parent_after_cleanup.json')
        self.terminal = read('terminal.json')
        self.kwargs = {'container_id': self.terminal['Id'], 'parent_path': str(Path(self.detail['directory']).parent),
                       'leaf_path': self.detail['directory']}

    def run_check(self, **replacements):
        args = {'detail': self.detail, 'last_leaf': self.leaf, 'parent_before': self.before,
                'parent_final': self.final, 'terminal': self.terminal, **self.kwargs}
        args.update(replacements)
        return reconcile_enodev(**args)

    def test_actual_retained_kernel_condition_reconciles_resources_only(self):
        result = self.run_check()
        self.assertFalse(result['candidate_admission'])
        self.assertFalse(result['scientific_completion'])
        self.assertEqual(result['descendant_cpu_seconds'], self.final['cpu_usage_seconds'])
        self.assertEqual(result['failed_leaf_read_retained'], self.detail)

    def test_unreproduced_errors_and_unverified_missing_paths_remain_fatal(self):
        changes = [('errno', errno.EIO), ('errno', errno.EACCES),
                   ('operation', 'open_controller_file'),
                   ('path', self.detail['path'] + '.other'),
                   ('current_path_identity', {'error_type': 'PermissionError', 'errno': errno.EACCES}),
                   ('current_path_identity', {'identity': self.detail['initial_identity']}),
                   ('open_directory_identity', {'device': 0, 'inode': 0}),
                   ('observed_monotonic', self.final['observed_monotonic'] + 1)]
        for key, value in changes:
            with self.subTest(key=key, value=value):
                detail = copy.deepcopy(self.detail)
                detail[key] = value
                with self.assertRaises(ValueError):
                    self.run_check(detail=detail)

    def test_live_failed_foreign_or_oom_container_remains_fatal(self):
        changes = [('Running', True), ('Pid', 1), ('ExitCode', 1), ('OOMKilled', True)]
        for key, value in changes:
            with self.subTest(key=key):
                terminal = copy.deepcopy(self.terminal)
                terminal['State'][key] = value
                with self.assertRaises(ValueError):
                    self.run_check(terminal=terminal)
        terminal = copy.deepcopy(self.terminal)
        terminal['Id'] = 'a' * 64
        with self.assertRaises(ValueError):
            self.run_check(terminal=terminal)

    def test_populated_replaced_regressed_and_resource_limited_parent_rejected(self):
        changes = [('pids.current', '1'), ('cgroup.events', 'populated 1'),
                   ('identity', {'device': 0, 'inode': 0}), ('cpu_usage_seconds', 0),
                   ('memory.peak', '0'), ('memory.events', 'oom 1'), ('pids.events', 'max 1')]
        for key, value in changes:
            with self.subTest(key=key):
                final = copy.deepcopy(self.final)
                final[key] = value
                with self.assertRaises(ValueError):
                    self.run_check(parent_final=final)


if __name__ == '__main__':
    unittest.main()
