"""Mutation controls for the independent archive auditor; no archive/model run."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).with_name('audit_replay_archive.py')
SPEC = importlib.util.spec_from_file_location('_archive_audit_pure', SCRIPT)
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class ArchiveAuditContracts(unittest.TestCase):
    def test_declared_roots(self):
        self.assertEqual(AUDIT.expected_source('owned-run/evaluation-r1/results/summary.json'),
            AUDIT.RUN / 'evaluation-r1/results/summary.json')
        self.assertEqual(AUDIT.expected_source('review-and-source/initial-state.json'), AUDIT.R/'initial-state.json')

    def test_traversal_and_unknown_roots(self):
        for member in ('../x','owned-run/../x','/owned-run/x','another-root/x','owned-run'):
            with self.subTest(member=member), self.assertRaises(ValueError):
                AUDIT.expected_source(member)

    def test_noncanonical_names(self):
        for member in ('owned-run//x','owned-run/./x','owned-run/x/','owned-run\\x',''):
            with self.subTest(member=member), self.assertRaises(ValueError):
                AUDIT.expected_source(member)

    def test_exact_content_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'sample';body=b'actual saved evidence\n';path.write_bytes(body)
            self.assertEqual(AUDIT.file_binding(path),dict(bytes=len(body),sha256=hashlib.sha256(body).hexdigest()))

    def test_symlink_body_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'sample';target.write_bytes(b'real')
            link=Path(directory)/'symbolic';link.symlink_to(target)
            with self.assertRaises(ValueError): AUDIT.file_binding(link)

    def test_directory_body_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError): AUDIT.file_binding(Path(directory))


if __name__=='__main__':
    unittest.main(verbosity=2)
