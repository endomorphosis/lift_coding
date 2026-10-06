"""Offline checks for append-only destination, identity and error redaction."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('all_weights_publisher', HERE / 'publish_all_weights.py')
PUBLISHER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PUBLISHER)


class PublicationTests(unittest.TestCase):
    def test_only_explicit_destination_and_bounded_metadata_requests_added(self):
        original = (HERE.parent / 'expansion' / 'publish_expanded_release.py').read_bytes()
        self.assertEqual(hashlib.sha256(original).hexdigest(),
                         '091bbe96d61881fb136421d3ccd43b126881a55a6bd8562d3ff10f40d5a78e31')
        original_rule = b"('Publicus/legal-ir-autoencoder', 'model', 'releases/20261005-authored32-source-reconstruction-aes-v1')}"
        replacement = b"('Publicus/legal-ir-autoencoder', 'model', 'releases/20261005-authored32-source-reconstruction-aes-v1'),\n            ('Publicus/legal-ir-autoencoder', 'model', 'releases/20261005-all-project-weights-v1')}"
        helper = b"def get_paths_info_batched(api, repo, paths, kind, revision):\n    metadata = []\n    for start in range(0, len(paths), 500):\n        metadata.extend(api.get_paths_info(repo, paths[start:start + 500],\n                                           repo_type=kind, revision=revision))\n    return metadata\n\n\n"
        previous_call = b"metadata = api.get_paths_info(repo, [prefix + '/' + row['path'] for row in plan['files']], repo_type=kind, revision=commit.oid)"
        current_call = b"metadata = get_paths_info_batched(api, repo, [prefix + '/' + row['path'] for row in plan['files']], kind, commit.oid)"
        current = (HERE / 'publish_all_weights.py').read_bytes()
        self.assertEqual(current.count(replacement), 1)
        self.assertEqual(current.count(helper), 1)
        self.assertEqual(current.count(current_call), 1)
        self.assertEqual(current.replace(replacement, original_rule).replace(helper, b'')
                         .replace(current_call, previous_call), original)

    def test_metadata_exact_500_path_boundary(self):
        paths = [f'selected-{index}.gz' for index in range(500)]
        api = MagicMock()
        api.get_paths_info.return_value = paths
        self.assertEqual(PUBLISHER.get_paths_info_batched(api, 'selected/repo', paths, 'model', 'exact-revision'), paths)
        api.get_paths_info.assert_called_once_with('selected/repo', paths, repo_type='model', revision='exact-revision')

    def test_metadata_above_request_limit_preserves_order_and_revision(self):
        paths = [f'selected-{index}.gz' for index in range(1001)]
        api = MagicMock()
        api.get_paths_info.side_effect = lambda _repo, selected, **_kwargs: selected
        self.assertEqual(PUBLISHER.get_paths_info_batched(api, 'selected/repo', paths, 'model', 'exact-revision'), paths)
        self.assertEqual(len(api.get_paths_info.call_args_list), 3)
        for index, call in enumerate(api.get_paths_info.call_args_list):
            self.assertEqual(call.args, ('selected/repo', paths[index * 500:(index + 1) * 500]))
            self.assertEqual(call.kwargs, {'repo_type': 'model', 'revision': 'exact-revision'})

    def test_tracking_preserves_old_bytes(self):
        before = b'*.bin filter=lfs diff=lfs merge=lfs -text\n'
        line = 'release/selected.bin filter=lfs diff=lfs merge=lfs -text'
        self.assertEqual(PUBLISHER.validate_tracking_delta(before, before + line.encode() + b'\n', {line}), [line])

    def test_tracking_rejects_changes_and_unselected_paths(self):
        before = b'old rule\n'
        allowed = {'selected filter=lfs diff=lfs merge=lfs -text'}
        cases = [b'changed rule\n', before, before + b'unselected\n',
                 before + b'selected filter=lfs diff=lfs merge=lfs -text',
                 before + b'selected filter=lfs diff=lfs merge=lfs -text\n' * 2]
        for after in cases:
            with self.subTest(after=after), self.assertRaises(PUBLISHER.PublicationIntegrityError):
                PUBLISHER.validate_tracking_delta(before, after, allowed)

    def _fake_publication(self, principal, prefix='releases/20261005-all-project-weights-v1'):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        payload = root / 'selected.bin'
        payload.write_bytes(b'fixed fixture')
        binding = {'path': 'selected.bin', 'bytes': payload.stat().st_size,
                   'sha256': hashlib.sha256(payload.read_bytes()).hexdigest()}
        body = {'schema': 'append-only-HF-publication-plan/v1',
                'repo_id': 'Publicus/legal-ir-autoencoder', 'repo_type': 'model', 'prefix': prefix,
                'directory': str(root), 'files': [binding], 'original_input_bindings': []}
        body['content_sha256'] = hashlib.sha256(PUBLISHER.raw(body)).hexdigest()
        plan_path = root / 'plan.json'
        plan_path.write_bytes(PUBLISHER.raw(body) + b'\n')
        arguments = argparse.Namespace(plan=plan_path,
                                       plan_sha256=hashlib.sha256(plan_path.read_bytes()).hexdigest(),
                                       output=root / 'output')
        api = MagicMock()
        api.whoami.return_value = principal
        api.repo_info.side_effect = RuntimeError('provider-secret-signed-url')
        hf_module = types.ModuleType('huggingface_hub')
        hf_module.CommitOperationAdd = MagicMock()
        hf_module.HfApi = MagicMock(return_value=api)
        hf_module.get_token = MagicMock(return_value='fixture-credential')
        hf_module.hf_hub_url = MagicMock()
        errors_module = types.ModuleType('huggingface_hub.errors')
        errors_module.RepositoryNotFoundError = type('FakeRepositoryNotFoundError', (Exception,), {})
        requests_module = types.ModuleType('requests')
        requests_module.Session = MagicMock()
        with patch.dict('sys.modules', {'requests': requests_module, 'huggingface_hub': hf_module,
                                       'huggingface_hub.errors': errors_module}), contextlib.redirect_stdout(io.StringIO()):
            code = PUBLISHER.publish(arguments)
        receipt_bytes = (arguments.output / 'publication.json').read_bytes()
        self.assertEqual(code, 1)
        self.assertNotIn(b'provider-secret-signed-url', receipt_bytes)
        self.assertNotIn(b'fixture-credential', receipt_bytes)
        self.assertFalse(json.loads(receipt_bytes)['provider_error_details_retained'])
        api.create_commit.assert_not_called()
        requests_module.Session.assert_not_called()
        return api, json.loads(receipt_bytes)

    def test_principal_requires_exact_user_and_admin(self):
        cases = [
            {'name': 'different-user', 'orgs': [{'name': 'Publicus', 'roleInOrg': 'admin'}]},
            {'name': 'endomorphosis', 'orgs': [{'name': 'Publicus', 'roleInOrg': 'write'}]},
            {'name': 'endomorphosis', 'orgs': []},
            {'name': 'endomorphosis', 'orgs': [{'name': 'DifferentOrg', 'roleInOrg': 'admin'}]},
        ]
        for principal in cases:
            with self.subTest(principal=principal):
                api, receipt = self._fake_publication(principal)
                api.repo_info.assert_not_called()
                self.assertEqual(receipt['integrity_error'], 'unexpected publishing principal')

    def test_authorized_principal_advances_and_redacts_provider_error(self):
        api, receipt = self._fake_publication(
            {'name': 'endomorphosis', 'orgs': [{'name': 'Publicus', 'roleInOrg': 'admin'}]})
        api.repo_info.assert_called_once_with('Publicus/legal-ir-autoencoder', repo_type='model', files_metadata=True)
        self.assertEqual(receipt['error_type'], 'RuntimeError')
        self.assertEqual(receipt['auth']['Publicus_role'], 'admin')
        self.assertNotIn('integrity_error', receipt)

    def test_unapproved_destination_rejected_before_provider_calls(self):
        api, receipt = self._fake_publication(
            {'name': 'endomorphosis', 'orgs': [{'name': 'Publicus', 'roleInOrg': 'admin'}]},
            prefix='releases/unselected')
        api.whoami.assert_not_called()
        self.assertEqual(receipt['integrity_error'], 'explicit approved destination/profile required')


if __name__ == '__main__':
    unittest.main()
