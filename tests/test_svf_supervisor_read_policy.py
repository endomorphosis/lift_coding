"""Governed read-policy compatibility; authored fixtures, no native SDK/RPC."""
import copy
import hashlib
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT=Path(__file__).resolve().parents[1]
SOURCE=Path(os.environ.get('SVF_SUPERVISOR_READ_CANDIDATE',ROOT/'scripts/svf_backends/native_supervisor_backend.py'))
spec=importlib.util.spec_from_file_location('native_supervisor_read_policy',SOURCE)
backend=importlib.util.module_from_spec(spec);spec.loader.exec_module(backend)
RUN='00000000-0000-4000-8000-000000000001'
TASK='00000000-0000-4000-8000-000000000002'


class QualifiedReadBoundary(Exception):
    pass


class SupervisorReadPolicyTests(unittest.TestCase):
    def arguments(self):
        # Canonical browser payload plus the authoritative fields injected by
        # invokeOwnerOverMcpPlusPlus. This is an authored request, not an RPC.
        return {'fixture_mode':backend.MODE,'fixture_scope':backend.FIXTURE_SCOPE,
                'run_id':RUN,'task_key':'a','dry_run':False,
                'correlation_id':'desktop:00000000-0000-4000-8000-000000000003'}

    def test_governed_false_read_policy_is_accepted_without_mutating_arguments(self):
        arguments=self.arguments();before=copy.deepcopy(arguments)
        self.assertIsNone(backend.check_common(arguments,backend.READ_KEYS))
        self.assertEqual(arguments,before)

    def test_actual_public_get_task_reaches_run_lookup_before_any_sdk_or_write(self):
        with patch.object(backend,'load_run',side_effect=QualifiedReadBoundary) as lookup, \
             patch.object(backend,'open_sdk',side_effect=AssertionError('no actual SDK')) as sdk, \
             patch.object(backend,'private_dir',side_effect=AssertionError('no native writes')):
            with self.assertRaises(QualifiedReadBoundary):
                backend.supervise(None,'get_task',self.arguments())
        lookup.assert_called_once_with(RUN);sdk.assert_not_called()

    def test_readback_returns_exact_existing_output_hash_and_task_without_execution(self):
        with tempfile.TemporaryDirectory(dir='/dev/shm') as temporary:
            path=Path(temporary);raw=b'{"AUTHORED_EXISTING_FIXED_OUTPUT":true}\n';(path/'a.json').write_bytes(raw)
            state={'run_dir':str(path),'task_ids':{'a':TASK}};before=copy.deepcopy(state)
            repo=Mock();repo.get_task.return_value={'status':'completed'}
            source=Mock();source.ready_tasks.return_value=[]
            with patch.object(backend,'load_run',return_value=state), \
                 patch.object(backend,'open_sdk',return_value=(repo,source)), \
                 patch.object(backend,'provenance',return_value={'AUTHORED_UNIT_FIXTURE_ONLY':True}), \
                 patch.object(backend,'execute_stage',side_effect=AssertionError('read must never execute')) as execute, \
                 patch.object(backend,'write_artifact',side_effect=AssertionError('read must not publish an attempt')):
                result=backend.supervise(None,'get_task',self.arguments())
            body=result['content'][0]['json']
            self.assertEqual(body['run_id'],RUN);self.assertEqual(body['task_id'],TASK)
            self.assertEqual(body['task_key'],'a');self.assertEqual(body['status'],'completed')
            self.assertEqual(body['output_sha256'],hashlib.sha256(raw).hexdigest())
            self.assertEqual(result['receipt']['tool'],'get_task');self.assertEqual(state,before)
            self.assertEqual((path/'a.json').read_bytes(),raw)
            repo.get_task.assert_called_once_with(TASK);execute.assert_not_called()

    def test_preview_or_non_boolean_dry_run_refuses_before_native_lookup(self):
        for value in (True,0,1,None,'false',[],{}):
            arguments=self.arguments();arguments['dry_run']=value
            with self.subTest(value=value), \
                 patch.object(backend,'load_run',side_effect=AssertionError('no run lookup')), \
                 patch.object(backend,'open_sdk',side_effect=AssertionError('no SDK')):
                with self.assertRaisesRegex(ValueError,'Preview is not'):
                    backend.supervise(None,'get_task',arguments)

    def test_scope_mode_unknown_fields_and_malformed_correlation_still_refuse(self):
        cases=[{'fixture_scope':'foreign'},{'fixture_scope':None},{'fixture_mode':'other'},
               {'action':'dispatch'},{'command':['arbitrary']},{'database_path':'/foreign'},
               {'dry_run_extra':False},{'correlation_id':''},{'correlation_id':7},
               {'correlation_id':'x'*257}]
        for changed in cases:
            arguments={**self.arguments(),**changed}
            with self.subTest(changed=changed), \
                 patch.object(backend,'load_run',side_effect=AssertionError('no run lookup')), \
                 patch.object(backend,'open_sdk',side_effect=AssertionError('no SDK')):
                with self.assertRaises(ValueError):backend.supervise(None,'get_task',arguments)

    def test_historical_absent_dry_run_read_and_exact_scope_remain_supported(self):
        for absent in ('dry_run','fixture_scope'):
            arguments=self.arguments();arguments.pop(absent)
            with self.subTest(absent=absent), \
                 patch.object(backend,'load_run',side_effect=QualifiedReadBoundary), \
                 patch.object(backend,'open_sdk',side_effect=AssertionError('no SDK')):
                with self.assertRaises(QualifiedReadBoundary):backend.supervise(None,'get_task',arguments)


if __name__=='__main__':unittest.main()
