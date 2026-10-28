"""Filesystem-only artifact persistence; no supervisor SDK, workers, or services."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import stat
import tempfile
import unittest
import uuid
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'scripts/svf_backends/native_supervisor_backend.py'
spec = importlib.util.spec_from_file_location('fs_only_supervisor_backend', SOURCE)
backend = importlib.util.module_from_spec(spec); spec.loader.exec_module(backend)


class AuthoredResult:
    def to_dict(self): return {'fixture': 'filesystem-only; no SDK runner proof', 'value': 7}


class PrivateAttemptDirectories(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.runtime = self.root / 'runtime'
        self.runtime.mkdir(mode=0o700); self.run = self.runtime / str(uuid.uuid4()); self.run.mkdir(mode=0o700)
        self.scopes = [patch.object(backend, 'RUNTIME', self.runtime),
                       patch.object(backend, 'load_sdk', side_effect=AssertionError('filesystem test must not call SDK'))]
        for scope in self.scopes: scope.start(); self.addCleanup(scope.stop)

    def mode(self, path): return stat.S_IMODE(path.stat().st_mode)
    def write(self, path=None): return backend.write_artifact(path or self.run, AuthoredResult())

    def test_missing_attempt_parent_is_created_privately_before_unique_artifact_leaf(self):
        self.assertFalse((self.run / 'attempts').exists())
        artifact = self.write(); path = Path(artifact['path'])
        self.assertEqual(path.name, 'result.json'); self.assertEqual(path.parent.parent, self.run / 'attempts')
        self.assertEqual(str(uuid.UUID(path.parent.name)), path.parent.name)
        self.assertEqual(json.loads(path.read_text()), AuthoredResult().to_dict())
        self.assertEqual(artifact['sha256'], hashlib.sha256(path.read_bytes()).hexdigest())
        for parent in [self.runtime, self.run, path.parent.parent, path.parent]: self.assertEqual(self.mode(parent), 0o700)
        self.assertEqual(self.mode(path), 0o600)

    def test_existing_owned_ancestors_are_private_and_each_result_gets_a_distinct_leaf(self):
        for path in [self.runtime, self.run]: path.chmod(0o755)
        attempts = self.run / 'attempts'; attempts.mkdir(mode=0o755)
        first, second = self.write(), self.write()
        self.assertNotEqual(first['path'], second['path'])
        for path in [self.runtime, self.run, attempts]: self.assertEqual(self.mode(path), 0o700)
        self.assertEqual(len(list(attempts.iterdir())), 2)

    def test_broad_process_umask_cannot_make_created_directories_or_artifact_public(self):
        old = os.umask(0)
        try: artifact = self.write()
        finally: os.umask(old)
        path = Path(artifact['path'])
        self.assertEqual(self.mode(path), 0o600)
        self.assertEqual(self.mode(path.parent), 0o700)
        self.assertEqual(self.mode(path.parent.parent), 0o700)

    def test_symlink_run_is_rejected_before_any_outside_attempt_directory_is_created(self):
        outside = self.root / 'outside'; outside.mkdir(mode=0o755)
        self.run.rmdir(); self.run.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError): self.write()
        self.assertEqual(list(outside.iterdir()), []); self.assertEqual(self.mode(outside), 0o755)

    def test_symlink_runtime_ancestor_is_rejected_without_outside_writes(self):
        real = self.root / 'real'; real.mkdir()
        fixtures = real / 'fixtures'; fixtures.mkdir()
        run = fixtures / str(uuid.uuid4()); run.mkdir()
        alias = self.root / 'alias'; alias.symlink_to(real, target_is_directory=True)
        with patch.object(backend, 'RUNTIME', alias / 'fixtures'):
            with self.assertRaises(ValueError): self.write(alias / 'fixtures' / run.name)
        self.assertEqual(list(run.iterdir()), [])

    def test_symlink_attempts_is_rejected_before_any_outside_write_or_chmod(self):
        outside = self.root / 'outside'; outside.mkdir(mode=0o755)
        (self.run / 'attempts').symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError): self.write()
        self.assertEqual(list(outside.iterdir()), []); self.assertEqual(self.mode(outside), 0o755)

    def test_dangling_attempt_symlink_is_rejected_without_creating_its_target(self):
        outside = self.root / 'missing'; (self.run / 'attempts').symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError): self.write()
        self.assertFalse(outside.exists())

    def test_artifact_uuid_symlink_is_rejected_without_outside_write(self):
        fixed = uuid.uuid4(); attempts = self.run / 'attempts'; attempts.mkdir(mode=0o700)
        outside = self.root / 'outside'; outside.mkdir(mode=0o755)
        (attempts / str(fixed)).symlink_to(outside, target_is_directory=True)
        with patch.object(backend.uuid, 'uuid4', return_value=fixed):
            with self.assertRaises(ValueError): self.write()
        self.assertEqual(list(outside.iterdir()), []); self.assertEqual(self.mode(outside), 0o755)

    def test_existing_uuid_directory_collision_preserves_immutable_result_bytes_and_mode(self):
        fixed = uuid.uuid4(); attempts = self.run / 'attempts'; attempts.mkdir(mode=0o700)
        folder = attempts / str(fixed); folder.mkdir(mode=0o700)
        path = folder / 'result.json'; path.write_bytes(b'original immutable result'); path.chmod(0o600)
        with patch.object(backend.uuid, 'uuid4', return_value=fixed):
            with self.assertRaises(FileExistsError): self.write()
        self.assertEqual(path.read_bytes(), b'original immutable result'); self.assertEqual(self.mode(path), 0o600)

    def test_attempt_parent_file_collision_is_refused_without_rewriting_file(self):
        path = self.run / 'attempts'; path.write_bytes(b'foreign existing file'); path.chmod(0o600)
        with self.assertRaises(FileExistsError): self.write()
        self.assertEqual(path.read_bytes(), b'foreign existing file'); self.assertEqual(self.mode(path), 0o600)

    def test_foreign_existing_run_outside_runtime_is_rejected_without_mutation(self):
        outside = self.root / str(uuid.uuid4()); outside.mkdir(mode=0o755)
        with self.assertRaises(ValueError): self.write(outside)
        self.assertEqual(list(outside.iterdir()), []); self.assertEqual(self.mode(outside), 0o755)

    def test_missing_run_is_not_invented_by_result_persistence(self):
        self.run.rmdir()
        with self.assertRaises(ValueError): self.write()
        self.assertFalse(self.run.exists())

    def test_nested_or_non_uuid_run_is_not_a_registered_direct_child(self):
        bad = self.runtime / 'not-a-run'; bad.mkdir()
        with self.assertRaises(ValueError): self.write(bad)
        parent = self.runtime / 'nested'; parent.mkdir(); nested = parent / str(uuid.uuid4()); nested.mkdir()
        with self.assertRaises(ValueError): self.write(nested)
        self.assertEqual(list(bad.iterdir()), []); self.assertEqual(list(nested.iterdir()), [])

    def test_private_dir_rejects_escape_before_creating_a_directory(self):
        path = self.root / 'outside-new'
        with self.assertRaises(ValueError): backend.private_dir(path)
        self.assertFalse(path.exists())

    def test_private_dir_does_not_blindly_create_unvalidated_intermediate_parents(self):
        parent = self.run / 'missing-parent'; target = parent / 'leaf'
        with self.assertRaises(FileNotFoundError): backend.private_dir(target)
        self.assertFalse(parent.exists())


if __name__ == '__main__': unittest.main()
