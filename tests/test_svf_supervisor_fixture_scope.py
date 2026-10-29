"""Pure supervisor argument boundaries; no SDK, RPC, service, or worker execution."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest
import uuid
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'scripts/svf_backends/native_supervisor_backend.py'
spec = importlib.util.spec_from_file_location('scope_boundary_supervisor', SOURCE)
backend = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend)


class ReachedQualifiedBoundary(Exception):
    """Intercept before any filesystem or SDK side effect."""


class SupervisorFixtureScope(unittest.TestCase):
    def test_scope_is_the_single_declared_supervisor_app_fixture(self):
        self.assertEqual(backend.FIXTURE_SCOPE, 'svf-agent-supervisor-552')

    def arguments(self, action):
        value = {'fixture_mode': backend.MODE, 'fixture_scope': backend.FIXTURE_SCOPE,
                 'correlation_id': 'desktop:' + str(uuid.UUID(int=11))}
        if action == 'create':
            value.update(action='create', fixture='dependency-output-v1', dry_run=False)
        else:
            value.update(run_id=str(uuid.UUID(int=12)), task_key='a')
            if action != 'read': value.update(action=action, dry_run=False)
        return value

    def test_exact_scope_is_losslessly_accepted_for_each_fixed_argument_shape(self):
        for action, allowed in [('create', backend.CREATE_KEYS), ('dispatch', backend.MUTATE_KEYS),
                                ('retry', backend.MUTATE_KEYS), ('cancel', backend.MUTATE_KEYS),
                                ('read', backend.READ_KEYS)]:
            with self.subTest(action=action):
                args = self.arguments(action); before = copy.deepcopy(args)
                self.assertIsNone(backend.check_common(args, allowed))
                self.assertEqual(args, before)
                self.assertEqual(json.loads(json.dumps(args)), before)

    def test_wrong_scope_and_wrong_scope_types_are_rejected_for_every_operation(self):
        for allowed in [backend.CREATE_KEYS, backend.MUTATE_KEYS, backend.READ_KEYS]:
            for scope in ['', 'svf-agent-supervisor-553', 'svf-agent-supervisor-552-extra',
                          'svf-agent-supervisor-552\n', None, False, 552, [], {}]:
                with self.subTest(allowed=allowed, scope=scope):
                    with self.assertRaisesRegex(ValueError, 'fixture scope'):
                        backend.check_common({'fixture_mode': backend.MODE, 'fixture_scope': scope}, allowed)

    def test_historical_scope_absent_foundation_api_is_preserved(self):
        for allowed in [backend.CREATE_KEYS, backend.MUTATE_KEYS, backend.READ_KEYS]:
            self.assertIsNone(backend.check_common({'fixture_mode': backend.MODE}, allowed))

    def test_unknown_arguments_cannot_be_smuggled_through_the_scope_allowance(self):
        for field, value in [('argv', ['/bin/true']), ('command', 'true'), ('url', 'http://example.invalid'),
                             ('database_path', '/foreign/control.duckdb'), ('scope', backend.FIXTURE_SCOPE),
                             ('fixture_scope_extra', backend.FIXTURE_SCOPE)]:
            for allowed in [backend.CREATE_KEYS, backend.MUTATE_KEYS, backend.READ_KEYS]:
                with self.subTest(field=field, allowed=allowed):
                    with self.assertRaisesRegex(ValueError, 'Unsupported supervisor fixture arguments'):
                        backend.check_common({'fixture_mode': backend.MODE,
                                              'fixture_scope': backend.FIXTURE_SCOPE, field: value}, allowed)

    def test_existing_mode_preview_and_correlation_rejections_remain_closed(self):
        for extra in [{'fixture_mode': 'other'}, {'dry_run': True}, {'dry_run': 0},
                      {'correlation_id': ''}, {'correlation_id': 7}, {'correlation_id': 'x' * 257}]:
            args = self.arguments('create'); args.update(extra)
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                backend.check_common(args, backend.CREATE_KEYS)

    def test_scoped_create_reaches_original_boundary_without_calling_sdk(self):
        args = self.arguments('create')
        with patch.object(backend, 'private_dir', side_effect=ReachedQualifiedBoundary), \
             patch.object(backend, 'open_sdk', side_effect=AssertionError('SDK must not execute')) as sdk:
            with self.assertRaises(ReachedQualifiedBoundary): backend.supervise(None, backend.SUBMIT, args)
            sdk.assert_not_called()

    def test_scoped_mutations_and_read_reach_original_run_lookup_boundary(self):
        for action in ['dispatch', 'retry', 'cancel', 'read']:
            args = self.arguments(action)
            with self.subTest(action=action), \
                 patch.object(backend, 'load_run', side_effect=ReachedQualifiedBoundary) as lookup, \
                 patch.object(backend, 'open_sdk', side_effect=AssertionError('SDK must not execute')) as sdk:
                with self.assertRaises(ReachedQualifiedBoundary):
                    backend.supervise(None, 'get_task' if action == 'read' else backend.SUBMIT, args)
                lookup.assert_called_once_with(args['run_id']); sdk.assert_not_called()

    def test_wrong_scope_refuses_before_filesystem_or_native_run_lookup(self):
        for action in ['create', 'dispatch', 'retry', 'cancel', 'read']:
            args = self.arguments(action); args['fixture_scope'] = 'foreign'
            with self.subTest(action=action), \
                 patch.object(backend, 'private_dir', side_effect=AssertionError('no filesystem effects')), \
                 patch.object(backend, 'load_run', side_effect=AssertionError('no run lookup')), \
                 patch.object(backend, 'load_sdk', side_effect=AssertionError('no SDK')):
                with self.assertRaisesRegex(ValueError, 'fixture scope'):
                    backend.supervise(None, 'get_task' if action == 'read' else backend.SUBMIT, args)

    def test_unsupported_tools_actions_fixtures_and_task_keys_stay_rejected(self):
        cases = [(backend.SUBMIT, {**self.arguments('create'), 'fixture': 'arbitrary-workload'}),
                 (backend.SUBMIT, {**self.arguments('dispatch'), 'action': 'exec'}),
                 (backend.SUBMIT, {**self.arguments('dispatch'), 'task_key': '/bin/true'}),
                 ('arbitrary_tool', self.arguments('create'))]
        for tool, args in cases:
            with self.subTest(tool=tool, args=args), \
                 patch.object(backend, 'load_run', return_value={}), \
                 patch.object(backend, 'private_dir', side_effect=AssertionError('no filesystem effects')):
                with self.assertRaises(ValueError): backend.supervise(None, tool, args)

    def test_actual_gateway_admission_demands_exact_scope_before_native_dispatch(self):
        # Invoke only the existing exported pure policy function, never the desktop or a service.
        repository = Path(os.environ.get('SVF_FOUNDATION_REPOSITORY_ROOT', ROOT))
        node = shutil.which('node')
        self.assertIsNotNone(node)
        script = r'''
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
const root = process.argv[1];
const { admitBackendCall } = await import(pathToFileURL(path.join(root,'swissknife/scripts/run-visual-functional-workflow.mjs')));
const app = JSON.parse(fs.readFileSync(path.join(root,'swissknife/config/visual-functional-app-contracts.json'),'utf8')).apps.find(row=>row.app_id==='agent-supervisor');
const scenario = JSON.parse(fs.readFileSync(path.join(root,'swissknife/test/e2e/functional-workflows/agent-supervisor.json'),'utf8'));
const binding = app.backend_roles.find(row=>row.owner==='ipfs_accelerate_py').bindings[0];
const correlation = 'desktop:00000000-0000-4000-8000-000000000011';
const base = {protocol:'swissknife.all-app-tool-gateway.v1',route:'/mcp/tools/call',binding_id:binding.binding_id,
 app_id:app.app_id,intent_id:'scope-boundary-authored-call',owner:'ipfs_accelerate_py',tool_id:'WorkflowCoordinator.submit_task',
 transport:'http',correlation_id:correlation,receipt_required:true,input:{correlation_id:correlation,
 payload:{fixture_mode:'svf-goal-worker-v1',fixture_scope:scenario.fixture_scope,action:'create',fixture:'dependency-output-v1',dry_run:false},
 policy:{dry_run:false,outcome:'require_confirmation',consent:'granted'}}};
const before=JSON.stringify(base); admitBackendCall(base,app,scenario);
if(JSON.stringify(base)!==before)throw Error('policy mutated exact scoped call');
for (const scope of [undefined,'foreign',null,false]) {
 const call=structuredClone(base); if(scope===undefined)delete call.input.payload.fixture_scope;else call.input.payload.fixture_scope=scope;
 let rejected=false;try{admitBackendCall(call,app,scenario);}catch(error){rejected=error.code==='POLICY_BOUNDARY';}
 if(!rejected)throw Error('missing/foreign mutation scope was not rejected');
}
console.log('exact scope accepted; four missing/foreign scopes rejected; no dispatch');
'''
        completed = subprocess.run([node, '--input-type=module', '--eval', script, str(repository)],
                                   capture_output=True, text=True, timeout=15, check=False)
        self.assertEqual(completed.returncode, 0, completed.stderr[-2000:])
        self.assertIn('no dispatch', completed.stdout)


if __name__ == '__main__': unittest.main()
