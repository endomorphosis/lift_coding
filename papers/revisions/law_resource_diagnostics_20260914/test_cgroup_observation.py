import copy
import errno
import os
from pathlib import Path
import tempfile
import subprocess
import unittest
from unittest.mock import patch

from cgroup_observation import CgroupReader, ObservationError, retained_parent_check
from qualify_observation import exact_absence


class ObservationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'group'
        self.root.mkdir()
        values = {'cpu.stat': 'usage_usec 20\nuser_usec 10\nsystem_usec 10\n',
                  'cpu.max': '100000 100000', 'cpuset.cpus.effective': '0',
                  'memory.current': '0', 'memory.peak': '100', 'memory.max': '2147483648',
                  'memory.swap.max': '0', 'memory.events': 'max 0\noom 0\noom_kill 0',
                  'pids.current': '0', 'pids.max': '16', 'pids.events': 'max 0',
                  'cgroup.events': 'populated 0\nfrozen 0'}
        for name, value in values.items():
            (self.root / name).write_text(value)

    def test_retained_parent_is_necessary_but_never_admits_failed_leaf(self):
        with CgroupReader(self.root) as reader:
            before = reader.sample(parent=True)
            after = reader.sample(parent=True)
        result = retained_parent_check(before, after)
        self.assertTrue(result['empty_parent'])
        self.assertFalse(result['failed_leaf_admitted'])

    def test_all_oserror_classes_preserve_operation_errno_path_and_identity(self):
        for code in (errno.EIO, errno.ENODEV, errno.EACCES, errno.ENOENT):
            with self.subTest(errno=code), CgroupReader(self.root) as reader:
                with patch('cgroup_observation.os.read', side_effect=OSError(code, 'injected read failure')):
                    with self.assertRaises(ObservationError) as caught:
                        reader.read('cpu.stat')
                detail = caught.exception.detail
                self.assertEqual(detail['errno'], code)
                self.assertEqual(detail['operation'], 'read_controller_file')
                self.assertEqual(detail['path'], str(self.root / 'cpu.stat'))
                self.assertEqual(detail['initial_identity'], detail['open_directory_identity'])
                self.assertEqual(reader.read('pids.current'), '0')

    def test_failed_open_records_correct_operation(self):
        (self.root / 'cpu.stat').unlink()
        with CgroupReader(self.root) as reader:
            with self.assertRaises(ObservationError) as caught:
                reader.read('cpu.stat')
            self.assertEqual(caught.exception.detail['operation'], 'open_controller_file')
            self.assertEqual(caught.exception.detail['errno'], errno.ENOENT)

    def test_directory_replacement_cannot_inherit_previous_counters(self):
        with CgroupReader(self.root) as reader:
            self.root.rename(self.root.with_name('old'))
            self.root.mkdir()
            with self.assertRaises(ObservationError) as caught:
                reader.sample()
            self.assertEqual(caught.exception.detail['operation'], 'validate_directory_identity')

    def test_sample_rejects_replacement_during_controller_reads(self):
        with CgroupReader(self.root) as reader:
            original = reader.read
            def replace(name):
                value = original(name)
                if name == 'pids.events':
                    self.root.rename(self.root.with_name('old'))
                    self.root.mkdir()
                return value
            with patch.object(reader, 'read', side_effect=replace):
                with self.assertRaises(ObservationError) as caught:
                    reader.sample()
            self.assertEqual(caught.exception.detail['operation'], 'revalidate_directory_identity')

    def test_undeclared_files_and_symlinks_rejected(self):
        with CgroupReader(self.root) as reader:
            with self.assertRaises(ValueError):
                reader.read('../secret')
            (self.root / 'cpu.stat').unlink()
            (self.root / 'cpu.stat').symlink_to('/etc/passwd')
            with self.assertRaises(ObservationError) as caught:
                reader.read('cpu.stat')
            self.assertEqual(caught.exception.detail['errno'], errno.ELOOP)
        link = self.root.with_name('link')
        link.symlink_to(self.root)
        with self.assertRaises(ValueError):
            CgroupReader(link)

    def test_parent_identity_counter_and_population_rejections(self):
        with CgroupReader(self.root) as reader:
            before = reader.sample(parent=True)
        mutations = [('identity', {'device': 0, 'inode': 0}),
                     ('cpu_usage_seconds', 0), ('cpu_user_seconds', 0),
                     ('cpu_system_seconds', 0), ('memory.peak', '0'),
                     ('pids.current', '1'), ('cgroup.events', 'populated 1')]
        for field, value in mutations:
            with self.subTest(field=field):
                after = copy.deepcopy(before)
                after[field] = value
                with self.assertRaises(ValueError):
                    retained_parent_check(before, after)

    def test_error_and_success_paths_close_controller_descriptors(self):
        with CgroupReader(self.root) as reader:
            before = len(os.listdir('/proc/self/fd'))
            for _ in range(25):
                with patch('cgroup_observation.os.read', side_effect=OSError(errno.EIO, 'injected')):
                    with self.assertRaises(ObservationError):
                        reader.read('cpu.stat')
                reader.read('cpu.stat')
            self.assertEqual(len(os.listdir('/proc/self/fd')), before)

    def test_absence_requires_exact_container_and_recognized_docker_response(self):
        cid = 'a' * 64
        for prefix in ('error: no such object: ', 'Error: No such object: ',
                       'Error response from daemon: No such container: '):
            result = subprocess.CompletedProcess([], 1, b'[]\n', (prefix + cid + '\n').encode())
            self.assertTrue(exact_absence(result, cid))
            self.assertFalse(exact_absence(result, 'b' * 64))
        for rc, body, error in ((1, b'[]', b'permission denied'),
                                (125, b'[]', ('error: no such object: ' + cid).encode()),
                                (1, b'[{"Id":"other"}]', ('error: no such object: ' + cid).encode())):
            self.assertFalse(exact_absence(subprocess.CompletedProcess([], rc, body, error), cid))


if __name__ == '__main__':
    unittest.main()
