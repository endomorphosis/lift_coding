"""Authored RAM proof-shape vectors; no browser/provider or live acceptance."""
import copy
import hashlib
import importlib.util
import inspect
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid

REPOSITORY = Path(os.environ.get('SVF_FOUNDATION_REPOSITORY_ROOT', str(Path(__file__).resolve().parents[1])))
SCRIPTS = Path(os.environ.get('SVF_VPC_CANDIDATE_SCRIPTS', str(REPOSITORY / 'scripts')))
sys.path.insert(0, str(REPOSITORY / 'scripts')); sys.path.insert(0, str(SCRIPTS))
import swissknife_visual_functional_final_coverage as final
import swissknife_visual_functional_llm as llm
spec = importlib.util.spec_from_file_location('vpc_worker', SCRIPTS / 'swissknife_visual_functional_worker.py')
worker = importlib.util.module_from_spec(spec); spec.loader.exec_module(worker)


class Fixture:
    def __init__(self, root):
        self.root = root
        self.profile = {'runtimeRoot': 'data/agent_supervisor/swissknife_visual_functional', 'appContractPath': 'swissknife/config/contract.json',
            'taskSpecPath': 'config/tasks.json', 'humanPlanPath': 'plan.md', 'todoPath': 'todo.md',
            'objectivePath': 'goals.md', 'llm': {'provider': 'grok_cli', 'model': 'grok-4.7',
                'allowLocalFallback': False, 'allowCrossProviderFallback': False}, 'bounds': {}}
        self.apps = [{'app_id': f'app-{i}', 'title': 'Authored app', 'disposition': 'browser_local',
            'source_paths': [f'web/js/app-{i}.js'], 'primary_workflow': {'expected_results': ['Observed arithmetic result'],
            'persist_reopen': 'Restored result', 'error': 'Observed invalid input', 'recovery': 'Clear and calculate again'}} for i in range(45)]
        originals = [{'task_id': f'SVF-{101+i}', 'kind': 'verify', 'app_id': app['app_id']} for i, app in enumerate(self.apps)]
        dependencies = [task['task_id'] for task in originals] + ['SVF-043', 'SVF-044']
        self.tasks = [{'task_id': f'SVF-{1001+i}', 'kind': 'final-app-verify', 'title': 'Authored final viewport followup',
            'app_id': app['app_id'], 'original_verify_task': originals[i]['task_id'], 'acceptance': 'Authored vector only',
            'checks': [], 'edit_paths': [], 'dependencies': dependencies} for i, app in enumerate(self.apps)]
        mapping = {task['app_id']: task['task_id'] for task in self.tasks}
        self.regression = {'task_id': 'SVF-900', 'kind': 'regression', 'final_app_tasks': mapping,
                           'dependencies': [*dependencies, *mapping.values()]}
        self.aggregate = {'task_id': 'SVF-990', 'kind': 'aggregate', 'final_app_tasks': mapping,
                          'regression_task': 'SVF-900', 'dependencies': ['SVF-900', 'SVF-910', 'SVF-920', 'SVF-930']}
        self.spec = {'tasks': [*originals, *self.tasks, self.regression, self.aggregate]}
        for name in final.STATIC_INPUTS:
            self.write(name, '// AUTHORED SOURCE NOT EXECUTED\n// ' + name)
        self.write('swissknife/web/index.html', '<LINK href="/css/one.css" rel="stylesheet"><link rel=stylesheet href=\'/css/two.css\'>')
        self.write('swissknife/web/css/one.css', 'body { color: black; }')
        self.write('swissknife/web/css/two.css', 'button { color: blue; }')
        self.write(self.profile['appContractPath'], {'apps': self.apps})
        self.write(self.profile['taskSpecPath'], self.spec)
        self.write('config/swissknife_visual_functional_supervisor.json', self.profile)
        self.write('todo.md', ''.join('## '+task['task_id']+' Authored readonly followup\n\n- Predicted files:\n\n' for task in self.tasks))
        self.write('plan.md', 'Authored unit vector only'); self.write('goals.md', 'Authored unit vector only')
        for app in self.apps:
            self.write('swissknife/' + app['source_paths'][0], '// authored app source')
            self.write('swissknife/test/e2e/functional-workflows/' + app['app_id'] + '.json', self.scenario(app))
        (root / self.profile['runtimeRoot']).mkdir(parents=True)

    def write(self, name, value):
        target = self.root / name; target.parent.mkdir(parents=True, exist_ok=True)
        raw = value if type(value) is bytes else (json.dumps(value, sort_keys=True) + '\n').encode() if type(value) in {dict, list} else str(value).encode()
        target.write_bytes(raw); target.chmod(0o600); return target

    @staticmethod
    def scenario(app):
        def assertion(role, expected):
            return {'op': 'assert', 'requirement_id': role, 'probe': {'kind': 'text', 'selector': '#result'}, 'operator': 'equals', 'expected': expected}
        return {'schema': 'swissknife.visual-functional-scenario.v1', 'app_id': app['app_id'],
            'backend_bindings': [], 'phases': {'primary_result': [{'op': 'press', 'selector': '#equals', 'key': 'Enter'}, assertion('result_1', '50')],
            'persist_reopen': [{'op': 'reopen_app'}, assertion('persist_reopen', '50')], 'failure_recovery': [
                {'op': 'fill', 'selector': '#expression', 'value': 'invalid'},
                {'op': 'assert', 'checkpoint_id': 'error_observed', 'probe': {'kind': 'text', 'selector': '#result'}, 'operator': 'equals', 'expected': 'Invalid input'},
                {'op': 'click', 'selector': '#clear'}, assertion('failure_recovery', '50')]}}

    def group(self, index=0):
        task = self.tasks[index]; app = self.apps[index]; scenario = self.scenario(app)
        folder = self.root / self.profile['runtimeRoot'] / 'tasks' / task['task_id'] / 'verification/attempt-authored'
        sources = final.source_snapshot(self.root, self.profile, task)
        children = []
        semantics = {'result_1': app['primary_workflow']['expected_results'][0], 'persist_reopen': app['primary_workflow']['persist_reopen'],
                     'failure_recovery': app['primary_workflow']['error'] + ' Recovery: ' + app['primary_workflow']['recovery']}
        for viewport in final.VIEWPORTS:
            name = viewport['name']; child_dir = folder / name
            png = bytearray(129); png[:8] = b'\x89PNG\r\n\x1a\n'; png[12:16] = b'IHDR'; png[16:24] = struct.pack('>II', viewport['width'], viewport['height'])
            self.write(str((child_dir / (name + '.png')).relative_to(self.root)), bytes(png))
            self.write(str((child_dir / 'trace.zip').relative_to(self.root)), b'AUTHORED NOT A BROWSER TRACE')
            layout = {'viewport': {'width': viewport['width'], 'height': viewport['height']},
                'primary': {'left': 10, 'top': 30, 'width': 200, 'height': 100},
                'window': {'left': 0, 'top': 0, 'right': viewport['width'], 'bottom': viewport['height']}, 'violations': []}
            self.write(str((child_dir / (name + '-layout.json')).relative_to(self.root)), layout)
            assertions = []; errors = []
            for phase, steps in scenario['phases'].items():
                for step_index, step in enumerate(steps):
                    if step['op'] != 'assert': continue
                    row = {'phase': phase, 'step_index': step_index, 'probe': step['probe'],
                        'observed': {'operator': step['operator'], 'actual': step['expected'], 'expected': step['expected']}}
                    if 'requirement_id' in step:
                        assertions.append({**row, 'requirement_id': step['requirement_id'], 'requirement_text': semantics[step['requirement_id']], 'passed': True})
                    else: errors.append({**row, 'checkpoint_id': step['checkpoint_id']})
            values = {'primary_result': ['result_1'], 'keyboard': True, name + '_layout': [], 'error_recovery': ['failure_recovery']}
            records = [final.reference(self.root, child_dir / file) for file in (name + '.png', name + '-layout.json', 'trace.zip')]
            child = {'schema': final.CHILD_SCHEMA, 'app_id': task['app_id'], 'viewport': viewport, 'initial_viewport': viewport,
                'session_id': str(uuid.uuid4()), 'passed': True, 'actual_desktop': True, 'source_template': False,
                **sources, 'artifacts': records, 'result_screenshot': records[0],
                'checks': [{'kind': kind, 'passed': True, 'observation': {'operator': 'equals', 'actual': value, 'expected': value}} for kind, value in values.items()],
                'semantic_assertions': assertions, 'error_observations': errors,
                'keyboard_observations': [{'phase': 'primary_result', 'step_index': 0, 'key': 'Enter', 'focused': True, 'inside_app': True, 'semantic_requirement_id': 'result_1'}],
                'temporal_observations': [], 'viewports': [{'name': name, **layout}], 'backend_observations': [],
                'unexpected_backend_calls': 0, 'backend_call_count': 0, 'backend_call_phases': {name: 0 for name in ('primary_result', 'persist_reopen', 'failure_recovery', 'backend_proof', 'unknown')}, 'work_complete': False, 'completion_authority': False}
            children.append(child)
        group = {'task': task, 'folder': folder, 'children': children, 'sources': sources}
        self.persist(group); self.review(group); self.receipt(group); return group

    def source_vector(self, root, profile, task, app):
        # Proof-shape vectors stub only graph discovery. Python still hashes
        # all real RAM bytes; actual AST collection has separate direct tests.
        scenario = 'swissknife/test/e2e/functional-workflows/' + app['app_id'] + '.json'
        names = [*final.STATIC_INPUTS, profile['appContractPath'], scenario,
            *['swissknife/'+name for name in app['source_paths']], 'swissknife/web/css/one.css', 'swissknife/web/css/two.css']
        sources = {name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in sorted(set(names))}
        return {'contract_sha256': sources[profile['appContractPath']], 'scenario_sha256': sources[scenario], 'source_sha256': sources}

    def persist(self, group):
        entries = []; artifacts = []
        for child in group['children']:
            name = child['viewport']['name']; target = group['folder'] / name / 'workflow.json'
            self.write(str(target.relative_to(self.root)), child); record = final.reference(self.root, target)
            entries.append({'name': name, 'viewport': {k: child['viewport'][k] for k in ('width', 'height')}, 'report': record})
            artifacts += [record, *child['artifacts']]
        parent = {'schema': final.PARENT_SCHEMA, 'app_id': group['task']['app_id'], 'passed': True, 'actual_desktop': True,
            'source_template': False, 'coverage': 'independent_canonical_sessions', **group['sources'],
            'viewport_reports': entries, 'artifacts': artifacts, 'work_complete': False, 'completion_authority': False}
        group['report'] = self.write(str((group['folder'] / 'workflow.json').relative_to(self.root)), parent)
        return parent

    def validated(self, group):
        return final.validate_dual_workflow(self.root, self.profile, group['task'], group['report'],
            observation_validator=worker.validate_observed, backend_validator=worker.validate_backend_observation)

    def review(self, group, decision='pass', context_path=None):
        validated = self.validated(group); task = group['task']; expected = final.binding(task, validated)
        context_path = context_path or group['folder'] / ('model-inputs/visual-review-authored-' + uuid.uuid4().hex) / 'context.json'
        if not context_path.exists():
            self.write(str(context_path.relative_to(self.root)), {'task': {k: task[k] for k in ('task_id', 'kind', 'app_id')},
                'final_workflow_evidence': expected})
        context = final.reference(self.root, context_path); session = str(uuid.uuid4())
        images = [{'path': record['path'], 'sha256': record['sha256'], 'size_bytes': record['bytes'], 'width': viewport['width'], 'height': viewport['height']} for record, viewport in zip(validated['images'], final.VIEWPORTS)]
        response = {'schema': llm.RESPONSE_SCHEMA, 'task_id': task['task_id'], 'mode': 'review', 'decision': decision,
            'summary': 'Authored receipt-shape vector only', 'inspected_screenshots': [image['path'] for image in images], 'findings': [], 'edits': []}
        immutable = group['folder'] / 'model-invocations' / ('visual-review-' + session + '.json')
        receipt = {'schema': llm.RECEIPT_SCHEMA, 'invocation_id': session, 'task_id': task['task_id'], 'mode': 'review',
            'provider': 'grok_cli', 'model': 'grok-4.7', 'temperature': 0, 'success': True, 'allow_local_fallback': False,
            'allow_cross_provider_fallback': False, 'disable_model_retry': True, 'edits_applied': False,
            'work_complete': False, 'completion_authority': False,
            'effective_route': {'effective_provider_name': 'grok_cli', 'effective_model_name': 'grok-4.7'},
            **{key: 'a'*64 for key in ('source_contract_sha256', 'prompt_sha256', 'output_sha256')},
            'router_source_sha256': group['sources']['source_sha256']['external/ipfs_accelerate/ipfs_accelerate_py/llm_router.py'],
            'response_sha256': hashlib.sha256(llm._json(response).encode()).hexdigest(), 'response': response,
            'screenshots': images, 'input_files': [{'path': context['path'], 'sha256': context['sha256'], 'size_bytes': context['bytes']}],
            'attempt_receipt_path': str(immutable.relative_to(self.root)),
            'native_observation': {'exit_code': 0, 'native_grok_reason_code': 'end_turn', 'native_grok_error_observed': False,
                'native_grok_usage_observed': True, 'native_grok_envelope_observed': True,
                'native_grok_progress': {'response_usable': True, 'stdout_eof': True, 'stderr_eof': True,
                    'process_exit_observed': True, 'stream_complete': True, 'stream_tainted': False, 'text_truncated': False,
                    'timed_out': False, 'returncode': 0, 'final_event_type': 'end', 'final_reason_code': 'end_turn',
                    'tool_name_counts': {'read_file': 2}}}}
        group['review'] = self.write(str((group['folder'] / 'visual-review.json').relative_to(self.root)), receipt)
        self.write(str(immutable.relative_to(self.root)), receipt); return receipt

    def replace_review(self, group, receipt):
        receipt['response_sha256'] = hashlib.sha256(llm._json(receipt['response']).encode()).hexdigest()
        self.write(str(group['review'].relative_to(self.root)), receipt)
        self.write(receipt['attempt_receipt_path'], receipt)

    def receipt(self, group):
        task = group['task']; validated = self.validated(group)
        joined = final.review_join(self.root, self.profile, task, final.binding(task, validated), group['review'])
        parent = json.loads(group['report'].read_bytes())
        files = [final.reference(self.root, group['report']), *parent['artifacts'], final.reference(self.root, group['review'])]
        command = ['node', 'swissknife/scripts/run-visual-functional-workflow.mjs', '--app', task['app_id'],
            '--contracts', self.profile['appContractPath'], '--output-dir', str(group['folder']), '--independent-viewports']
        receipt = {'schema': 'swissknife.visual-functional-task.v1', 'task_id': task['task_id'], 'kind': task['kind'],
            'task_spec_sha256': worker.stable(task), 'artifacts': files, 'checks': [{'argv': command, 'exit_code': 0}],
            'detail': {'final_viewport_review_join': joined, 'readonly_verification': True, 'repair_admissions': 0},
            'work_complete': False, 'completion_authority': False}
        self.write(self.profile['runtimeRoot'] + '/tasks/' + task['task_id'] + '/receipt.json', receipt); return receipt

    def tool_backed(self, group, *, declared='owner-value', observed='owner-value', raw_binding='declared.get', semantic=False):
        app = self.apps[0]; app['disposition'] = 'tool_backed'
        app['backend_roles'] = [{'owner': 'ipfs_kit_py', 'bindings': [{'binding_id': 'declared.get',
            'exact_tool_candidates': ['artifacts_get'], 'transports': ['http'], 'mutates_remote_state': False}]}]
        scenario = self.scenario(app); scenario['fixture_scope'] = 'authored'
        scenario['backend_bindings'] = [{'binding_id': 'declared.get', 'result_assertion': {
            'pointer': '/result/result/value', 'operator': 'equals', 'expected': declared}}]
        if semantic:
            scenario['phases']['persist_reopen'][1].update(probe={'kind': 'backend_result', 'binding_id': 'declared.get', 'pointer': '/result/result/value'},
                operator='at_least', expected=1)
        self.write(self.profile['appContractPath'], {'apps': self.apps})
        self.write('swissknife/test/e2e/functional-workflows/app-0.json', scenario)
        sources = final.source_snapshot(self.root, self.profile, group['task']); group['sources'] = sources
        for child in group['children']:
            name = child['viewport']['name']; correlation = name + ':authored'
            child.update(sources); child['backend_call_count'] = 1
            child['backend_call_phases']['persist_reopen' if semantic else 'backend_proof'] = 1
            call = {'protocol': 'swissknife.all-app-tool-gateway.v1', 'owner': 'ipfs_kit_py', 'tool_id': 'artifacts_get',
                'transport': 'http', 'route': '/mcp/tools/call', 'correlation_id': correlation, 'app_id': app['app_id'],
                'binding_id': raw_binding, 'intent_id': 'declared.get', 'receipt_required': True,
                'input': {'correlation_id': correlation, 'payload': {}, 'policy': {'dry_run': False, 'outcome': 'allow', 'consent': 'not_required'}}}
            observation = {key: call[key] for key in ('owner', 'tool_id', 'transport', 'route', 'correlation_id')}
            observation.update(binding_id='declared.get', app_id=app['app_id'], outcome='executed', receipt_verified=True,
                semantic_result_verified=True, actual_desktop=True, result_assertion={'pointer': '/result/result/value',
                    'operator': 'at_least' if semantic else 'equals', 'actual': observed, 'expected': 1 if semantic else observed})
            for kind, field in (('receipt', 'receipt_id'), ('event', 'event_dag_cid')):
                raw = final.encoded({'kind': kind, 'call': call, 'result': {'result': {'receipt': {'tool': 'artifacts_get'}, 'value': observed}}})
                target = self.write(str((group['folder']/name/(kind+'.json')).relative_to(self.root)), raw)
                observation[field] = worker._raw_cid(raw); observation[kind+'_artifact'] = str(target.relative_to(self.root))
                child['artifacts'].append(final.reference(self.root, target))
            child['backend_observations'] = [observation]
            if semantic:
                assertion = next(item for item in child['semantic_assertions'] if item['requirement_id'] == 'persist_reopen')
                assertion.update(probe=scenario['phases']['persist_reopen'][1]['probe'],
                                 observed={'operator': 'at_least', 'actual': observed, 'expected': 1})
        self.persist(group)


class FinalCoverageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='svf-vpc-consumer-', dir='/dev/shm'); self.addCleanup(self.tmp.cleanup)
        self.addCleanup(patch.stopall); self.f = Fixture(Path(self.tmp.name))
        patch.object(final, '_node_source_snapshot', side_effect=self.f.source_vector).start()
        patch.object(final, '_node_source_snapshots', side_effect=lambda root, profile, apps: {
            app['app_id']: self.f.source_vector(root, profile, {'app_id': app['app_id']}, app) for app in apps}).start()
        self.g = self.f.group()
        patch.object(worker, 'ROOT', self.f.root).start()

    def validate(self): return self.f.validated(self.g)
    def join(self): return final.review_join(self.f.root, self.f.profile, self.g['task'], final.binding(self.g['task'], self.validate()), self.g['review'])
    def changed_child(self, change):
        change(self.g['children'][1]); self.f.persist(self.g)
        with self.assertRaises((ValueError, KeyError, TypeError)): self.validate()

    def test_current_both_children_and_exact_fresh_visual_join_pass(self):
        self.assertEqual(len(self.validate()['children']), 2); self.assertEqual(self.join()['task_id'], 'SVF-1001')
        worker.validate(self.f.profile, self.g['task'])

    def test_v1_cannot_qualify_final_coverage(self):
        data = json.loads(self.g['report'].read_bytes()); data['schema'] = 'swissknife.visual-functional-workflow.v1'
        self.f.write(str(self.g['report'].relative_to(self.f.root)), data)
        with self.assertRaises(ValueError): self.validate()

    def test_mobile_semantics_missing(self): self.changed_child(lambda c: c['semantic_assertions'].pop())
    def test_mobile_layout_only(self): self.changed_child(lambda c: c.update(semantic_assertions=[]))
    def test_duplicate_session(self): self.changed_child(lambda c: c.update(session_id=self.g['children'][0]['session_id']))
    def test_non_v4_session(self): self.changed_child(lambda c: c.update(session_id=str(uuid.uuid1())))
    def test_nil_session(self): self.changed_child(lambda c: c.update(session_id=str(uuid.UUID(int=0))))
    def test_mobile_initial_viewport_mislabeled(self): self.changed_child(lambda c: c.update(initial_viewport=final.VIEWPORTS[0]))
    def test_mobile_forged_expected_value(self): self.changed_child(lambda c: c['semantic_assertions'][0]['observed'].update(actual='fake', expected='fake'))
    def test_mobile_wrong_assertion_step(self): self.changed_child(lambda c: c['semantic_assertions'][0].update(step_index=0))
    def test_mobile_fake_keyboard(self): self.changed_child(lambda c: c['keyboard_observations'][0].update(step_index=1))
    def test_mobile_missing_error(self): self.changed_child(lambda c: c.update(error_observations=[]))
    def test_mobile_layout_detached(self): self.changed_child(lambda c: c['viewports'][0]['primary'].update(width=199))
    def test_mobile_owner_boundary_violation(self): self.changed_child(lambda c: c.update(backend_call_count=1))
    def test_missing_actual_owner_phase_counts(self): self.changed_child(lambda c: c.pop('backend_call_phases'))
    def test_mobile_temporal_forgery(self): self.changed_child(lambda c: c.update(temporal_observations=[{'before': 0, 'after': 1, 'sample_ms': 100}]))
    def test_mobile_screenshot_swapped(self): self.changed_child(lambda c: c.update(result_screenshot=self.g['children'][0]['result_screenshot']))

    def test_missing_mobile_parent(self):
        data = json.loads(self.g['report'].read_bytes()); data['viewport_reports'].pop()
        self.f.write(str(self.g['report'].relative_to(self.f.root)), data)
        with self.assertRaises(ValueError): self.validate()

    def test_source_controller_or_stylesheet_change_stales_both_children(self):
        for name in ('scripts/swissknife_visual_functional_worker.py', 'swissknife/web/css/two.css',
                     'swissknife/test/e2e/functional-workflows/app-0.json'):
            target = self.f.root / name; old = target.read_bytes(); target.write_bytes(old + b'\nchanged')
            with self.assertRaises(ValueError): self.validate()
            target.write_bytes(old)

    def test_omitted_source_closure_entry_refuses(self):
        data = json.loads(self.g['report'].read_bytes()); data['source_sha256'].pop('swissknife/web/js/live-tool-gateway.js')
        self.f.write(str(self.g['report'].relative_to(self.f.root)), data)
        with self.assertRaises(ValueError): self.validate()

    def test_wrong_png_dimensions_even_with_new_hash_refuses(self):
        child = self.g['children'][1]; record = child['result_screenshot']; png = bytearray((self.f.root / record['path']).read_bytes()); png[16:24] = struct.pack('>II', 1440, 900)
        self.f.write(record['path'], bytes(png)); changed = final.reference(self.f.root, self.f.root / record['path'])
        child['result_screenshot'] = changed; child['artifacts'][0] = changed; self.f.persist(self.g)
        with self.assertRaises(ValueError): self.validate()

    def test_symlink_child_artifact_refuses(self):
        image = self.f.root / self.g['children'][1]['result_screenshot']['path']; backup = image.with_suffix('.real'); image.rename(backup); image.symlink_to(backup)
        with self.assertRaises(ValueError): self.validate()

    def test_model_receipt_images_swapped_even_if_rehashed_refuses(self):
        receipt = json.loads(self.g['review'].read_bytes()); receipt['screenshots'].reverse()
        receipt['response']['inspected_screenshots'].reverse(); self.f.replace_review(self.g, receipt)
        with self.assertRaises(ValueError): self.join()

    def test_report_hash_change_cannot_reuse_same_pixel_review(self):
        data = json.loads(self.g['report'].read_bytes()); data['extra_diagnostic'] = 'new report same images'
        self.f.write(str(self.g['report'].relative_to(self.f.root)), data)
        with self.assertRaises(ValueError): self.join()

    def test_positive_receipt_cannot_be_rebound_to_failed_review_cache(self):
        with self.assertRaises(ValueError): final.remember_failed_review(self.f.root, self.f.profile, self.g['task'], self.validate(), self.g['review'])

    def test_tainted_native_receipt_cannot_qualify(self):
        receipt = json.loads(self.g['review'].read_bytes()); receipt['native_observation']['native_grok_progress']['stream_tainted'] = True
        self.f.replace_review(self.g, receipt)
        with self.assertRaises(ValueError): self.join()

    def test_missing_immutable_native_receipt_refuses(self):
        receipt = json.loads(self.g['review'].read_bytes()); (self.f.root / receipt['attempt_receipt_path']).unlink()
        with self.assertRaises(OSError): self.join()

    def test_stale_router_native_receipt_refuses(self):
        receipt = json.loads(self.g['review'].read_bytes()); receipt['router_source_sha256'] = 'f'*64; self.f.replace_review(self.g, receipt)
        with self.assertRaises(ValueError): self.join()

    def test_failed_review_fences_unchanged_sources_before_another_review(self):
        self.f.review(self.g, 'needs_changes')
        final.remember_failed_review(self.f.root, self.f.profile, self.g['task'], self.validate(), self.g['review'])
        with self.assertRaisesRegex(ValueError, 'unchanged_final_app_visual_review'):
            final.assert_final_review_allowed(self.f.root, self.f.profile, self.g['task'])
        target = self.f.root / 'swissknife/web/js/live-tool-gateway.js'; target.write_bytes(target.read_bytes() + b'\nscoped fix')
        final.assert_final_review_allowed(self.f.root, self.f.profile, self.g['task'])

    def test_failed_review_cache_dangling_symlink_fails_closed(self):
        target = final._failure_path(self.f.root, self.f.profile, self.g['task']); target.symlink_to(target.with_name('absent'))
        with self.assertRaises(ValueError): final.assert_final_review_allowed(self.f.root, self.f.profile, self.g['task'])

    def test_malformed_failed_review_cache_fails_closed(self):
        self.f.write(str(final._failure_path(self.f.root, self.f.profile, self.g['task']).relative_to(self.f.root)), {})
        with self.assertRaises(ValueError): final.assert_final_review_allowed(self.f.root, self.f.profile, self.g['task'])

    def test_exact_successful_dual_producer_is_required(self):
        receipt = self.f.receipt(self.g); receipt['checks'][0]['argv'].pop()
        with self.assertRaisesRegex(ValueError, 'exact successful'):
            final.retained_final_report(self.f.root, self.f.profile, self.g['task'], receipt, self.g['folder'].parent, validate_report=worker.validate_workflow)

    def test_extra_foreign_workflow_in_task_receipt_refuses(self):
        receipt = self.f.receipt(self.g); receipt['artifacts'].append(receipt['artifacts'][1])
        with self.assertRaises(ValueError):
            final.retained_final_report(self.f.root, self.f.profile, self.g['task'], receipt, self.g['folder'].parent, validate_report=worker.validate_workflow)

    def test_final_task_cannot_add_edit_scope_or_repair_admission(self):
        task = {**self.g['task'], 'edit_paths': ['swissknife/web/js/app-0.js']}
        with self.assertRaises(ValueError): final.validate_final_task_contract(self.f.root, self.f.profile, task, self.f.spec)

    def test_final_task_waits_for_all_original_app_verifications(self):
        task = {**self.g['task'], 'dependencies': self.g['task']['dependencies'][:-1]}
        with self.assertRaises(ValueError): final.validate_final_task_contract(self.f.root, self.f.profile, task, self.f.spec)

    def test_regression_without_45_fresh_mapping_refuses(self):
        task = {**self.f.regression, 'final_app_tasks': {}}
        with self.assertRaises(ValueError): final.final_task_map(self.f.root, self.f.profile, task, self.f.spec)

    def test_swapped_app_task_mapping_refuses(self):
        mapping = dict(self.f.regression['final_app_tasks']); mapping['app-0'], mapping['app-1'] = mapping['app-1'], mapping['app-0']
        with self.assertRaises(ValueError): final.final_task_map(self.f.root, self.f.profile, {**self.f.regression, 'final_app_tasks': mapping}, self.f.spec)

    def test_projection_has_both_independent_semantics_and_exact_images_under_cap(self):
        data = final.projection(self.f.root, self.g['report']); self.assertEqual(len(data['viewports']), 2)
        self.assertEqual(data['viewports'][1]['original'], self.validate()['children'][1]['entry']['report'])
        self.assertEqual(data['viewports'][1]['semantic_assertions'][0]['observed']['actual'], '50')
        self.assertLess(len(final.encoded(data)), 18000)

    def test_cross_app_aggregate_still_requires_three_original_cross_tasks(self):
        task = {**self.f.aggregate, 'dependencies': ['SVF-900', 'SVF-910']}
        with patch.object(worker, 'validate_dag', return_value=[]), self.assertRaisesRegex(ValueError, 'three original'):
            worker.validate_aggregate_dependencies(self.f.profile, task)

    def test_newkind_refuses_repair_mode_before_any_provider(self):
        with patch.object(worker, 'load', return_value=(self.f.profile, self.f.spec)), patch.object(worker, 'assert_no_campaign_hold'), patch.object(worker, 'assert_storage_available'), patch.object(llm, 'invoke_task_model') as provider:
            with self.assertRaisesRegex(ValueError, 'cannot create paid repair'):
                worker.model('unused', self.g['task'], 'repair', [], [], self.g['folder'] / 'never.json')
            provider.assert_not_called()

    def test_legacy_v1_app_workflow_keeps_its_original_validation_meaning(self):
        task = {'task_id': 'SVF-101', 'kind': 'verify', 'app_id': 'app-0'}
        folder = self.f.root / self.f.profile['runtimeRoot'] / 'tasks/SVF-101/verification/attempt-legacy'
        records = []
        for name in ('desktop.png', 'mobile.png', 'trace.zip'):
            target = self.f.write(str((folder/name).relative_to(self.f.root)), b'authored legacy artifact')
            records.append(final.reference(self.f.root, target))
        child = self.g['children'][0]
        data = {'schema': 'swissknife.visual-functional-workflow.v1', 'app_id': 'app-0', 'passed': True,
            'actual_desktop': True, 'source_template': False, 'contract_sha256': self.g['sources']['contract_sha256'],
            'source_sha256': self.g['sources']['source_sha256'], 'artifacts': records,
            'semantic_assertions': child['semantic_assertions'], 'backend_observations': [], 'unexpected_backend_calls': 0,
            'checks': [{'kind': kind, 'passed': True, 'observation': {'operator': 'equals', 'actual': True, 'expected': True}}
                       for kind in ('primary_result', 'keyboard', 'desktop_layout', 'mobile_layout', 'error_recovery')]}
        report = self.f.write(str((folder/'workflow.json').relative_to(self.f.root)), data)
        self.assertIsNone(worker.validate_workflow(self.f.profile, task, report))

    def test_real_review_compiler_stops_before_backend_with_both_images_and_original_caps(self):
        class PromptCaptured(Exception): pass
        captured = {}
        def before_backend(_root):
            frame = inspect.currentframe().f_back
            while frame and 'prompt' not in frame.f_locals: frame = frame.f_back
            assert frame is not None
            captured.update(prompt=frame.f_locals['prompt'], settings=frame.f_locals['settings'])
            raise PromptCaptured()
        with patch.object(worker, 'assert_no_campaign_hold'), patch.object(worker, 'assert_storage_available'), \
                patch.object(worker, 'storage_refusal', return_value=None), patch.object(llm, '_load_backend', side_effect=before_backend) as backend:
            with self.assertRaises(PromptCaptured):
                worker.model('config/swissknife_visual_functional_supervisor.json', self.g['task'], 'review',
                    [self.f.profile['appContractPath'], str(self.g['report'].relative_to(self.f.root))],
                    [item['path'] for item in self.validate()['images']], self.g['folder']/'visual-review-audit.json')
            backend.assert_called_once()
        self.assertLessEqual(len(captured['prompt'].encode()), 32768)
        self.assertEqual(captured['settings']['modelContextBytes'], 32768)
        self.assertLessEqual(captured['settings']['maxTurns'], 8)
        self.assertLessEqual(captured['settings']['maxOutputTokens'], 12288)
        for child in self.g['children']:
            self.assertEqual(captured['prompt'].count(child['session_id']), 1)
            self.assertIn(child['result_screenshot']['path'], captured['prompt'])
        self.assertIn('Initial/demo/layout-only mobile state', captured['prompt'])

    def test_full_over_1mib_canonical_taskboard_hashes_before_provider_without_growing_prompt_caps(self):
        self.f.profile['todoPath'] = llm.CANONICAL_TODO_PATH
        self.f.write('config/swissknife_visual_functional_supervisor.json', self.f.profile)
        board = ('## SVF-1001 Authored final app followup\n\n- Predicted files:\n\n'
                 '## SVF-AUX Unrelated task metadata\n' + 'unrelated taskboard metadata\n' * 42000).encode()
        self.assertGreater(len(board), 1048576); self.assertLess(len(board), 4*1024*1024)
        self.f.write(llm.CANONICAL_TODO_PATH, board); self.g = self.f.group()
        class StopBeforeProvider(Exception): pass
        captured = {}
        def stop(_root):
            frame = inspect.currentframe().f_back
            while frame and 'prompt' not in frame.f_locals: frame = frame.f_back
            captured.update(prompt=frame.f_locals['prompt'], settings=frame.f_locals['settings'], records=frame.f_locals['records'])
            raise StopBeforeProvider()
        with patch.object(worker, 'assert_no_campaign_hold'), patch.object(worker, 'assert_storage_available'), \
                patch.object(worker, 'storage_refusal', return_value=None), patch.object(llm, '_load_backend', side_effect=stop):
            with self.assertRaises(StopBeforeProvider):
                worker.model('config/swissknife_visual_functional_supervisor.json', self.g['task'], 'review',
                    [self.f.profile['appContractPath'], str(self.g['report'].relative_to(self.f.root))],
                    [item['path'] for item in self.validate()['images']], self.g['folder']/'large-board-audit.json')
        record = next(item for item in captured['records'] if item['path'] == llm.CANONICAL_TODO_PATH)
        self.assertEqual(record['size_bytes'], len(board)); self.assertEqual(record['sha256'], hashlib.sha256(board).hexdigest())
        self.assertLessEqual(len(captured['prompt'].encode()), 32768)
        self.assertEqual(captured['settings']['modelContextBytes'], 32768)
        self.assertNotIn('Unrelated task metadata', captured['prompt'])
        ordinary = self.f.write('ordinary-source.md', board)
        with self.assertRaises(llm.ModelAdapterError): llm._read(self.f.root, str(ordinary.relative_to(self.f.root)))
        self.f.write(llm.CANONICAL_TODO_PATH, b'x' * (4*1024*1024+1))
        with self.assertRaises(llm.ModelAdapterError): llm._snapshot(self.f.root, llm.CANONICAL_TODO_PATH)
        target = self.f.root/llm.CANONICAL_TODO_PATH; target.unlink(); target.symlink_to(ordinary)
        with self.assertRaises(llm.ModelAdapterError): llm._read(self.f.root, llm.CANONICAL_TODO_PATH)

    def test_current_python_and_javascript_source_snapshot_protocols_are_identical(self):
        runner = Path(os.environ.get('SVF_VPC_RUNNER_CANDIDATE', str(REPOSITORY/'swissknife/scripts/run-visual-functional-workflow.mjs')))
        code = """import {pathToFileURL} from 'node:url';
const m=await import(pathToFileURL(process.argv[2]).href);const root=process.argv[3];const app=JSON.parse(process.argv[4]);
console.log(JSON.stringify({fixed:m.INDEPENDENT_STATIC_INPUTS,snapshot:m.independentWorkflowSourceSnapshot(app,{projectRoot:root+'/swissknife',contractsPath:root+'/swissknife/config/contract.json',scenarioPath:root+'/swissknife/test/e2e/functional-workflows/'+app.app_id+'.json'})}));"""
        result = subprocess.run(['node', '--input-type=module', '-e', code, 'snapshot-parity', str(runner), str(self.f.root), json.dumps(self.f.apps[0])],
            text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        observed = json.loads(result.stdout)
        self.assertEqual(tuple(observed['fixed']), final.STATIC_INPUTS)
        self.assertEqual(observed['snapshot'], self.g['sources'])

    def actual_collect(self):
        return patch.object(final, '_node_source_snapshot', side_effect=lambda root, profile, task, app: final._node_collect(root, profile, app))

    def test_actual_readonly_collector_cannot_execute_app_code_or_node_preloads(self):
        runner = Path(os.environ.get('SVF_VPC_RUNNER_CANDIDATE', str(REPOSITORY/'swissknife/scripts/run-visual-functional-workflow.mjs')))
        self.f.write('swissknife/web/js/app-0.js', "throw new Error('app code must never execute during source collection');")
        marker = self.f.root/'preload-would-have-written'
        preload = self.f.write('preload.cjs', 'require("node:fs").writeFileSync('+json.dumps(str(marker))+',"unexpected");')
        with self.actual_collect(), patch.object(final, '_snapshot_runner_path', return_value=runner), \
                patch.dict(os.environ, {'NODE_OPTIONS': '--require '+str(preload)}):
            actual = final.source_snapshot(self.f.root, self.f.profile, self.g['task'])
        self.assertIn('swissknife/web/js/app-0.js', actual['source_sha256']); self.assertFalse(marker.exists())

    def test_actual_batched_graph_transaction_refuses_new_import_resolution_shadow(self):
        runner = Path(os.environ.get('SVF_VPC_RUNNER_CANDIDATE', str(REPOSITORY/'swissknife/scripts/run-visual-functional-workflow.mjs')))
        self.f.write('swissknife/web/js/app-0.js', "import './dep.js';")
        self.f.write('swissknife/web/js/dep.js', '// original firstparty dependency')
        with self.actual_collect(), patch.object(final, '_snapshot_runner_path', return_value=runner), \
                patch.object(final, '_node_source_snapshots', side_effect=lambda root, profile, apps: final._node_collect(root, profile, apps)):
            with self.assertRaisesRegex(ValueError, 'graph changed'):
                with final.source_snapshot_transaction(self.f.root, self.f.profile, [self.g['task']]):
                    self.f.write('swissknife/web/js/dep.ts', '// newly materialized import resolution candidate')

    def test_900_requires_all_45_current_positive_visual_joins(self):
        groups = [self.g] + [self.f.group(index) for index in range(1, 45)]
        coverage = final.coverage(self.f.root, self.f.profile, self.f.regression, validate_task=worker.validate,
            retained_report=worker.retained_workflow_report, validate_report=worker.validate_workflow, spec=self.f.spec)
        self.assertEqual(len(coverage['groups']), 45); self.assertEqual(coverage['fresh_positive_visual_review_count'], 45)
        folder = self.f.root / self.f.profile['runtimeRoot'] / 'tasks/SVF-900'
        manifest = self.f.write(str((folder/'final-app-coverage.json').relative_to(self.f.root)), coverage)
        receipt = {'schema': 'swissknife.visual-functional-task.v1', 'task_id': 'SVF-900', 'kind': 'regression',
            'task_spec_sha256': worker.stable(self.f.regression), 'artifacts': [final.reference(self.f.root, manifest)],
            'checks': [], 'detail': coverage, 'work_complete': False, 'completion_authority': False}
        self.f.write(str((folder/'receipt.json').relative_to(self.f.root)), receipt)
        worker.validate(self.f.profile, self.f.regression)
        self.assertEqual(len(worker.regression_workflow_reports(self.f.profile, self.f.aggregate)), 45)
        # One real per-app review join missing must refuse BOTH900 and990;
        # filenames, images and the other44 current groups cannot cover it.
        groups[-1]['review'].unlink()
        with self.assertRaises((ValueError, OSError)):
            worker.validate(self.f.profile, self.f.regression)
        with self.assertRaises((ValueError, OSError)):
            worker.regression_workflow_reports(self.f.profile, self.f.aggregate)

    def test_900_cannot_promote_legacy_workflow_filenames_into_final_coverage(self):
        with patch.object(worker, 'workflow', side_effect=AssertionError('900 must join bounded followups, not run45 browsers')):
            with patch.object(worker, 'ensure_lease'), patch.object(worker, 'check_owned_sources'), patch.object(worker, 'assert_storage_available'):
                task = {**self.f.regression, 'final_app_tasks': {}}
                with self.assertRaisesRegex(ValueError, '45 canonical'):
                    worker.execute('unused', self.f.profile, self.f.spec, task)

    def test_newkind_semantic_failure_cannot_invoke_paid_repair_or_visual_provider(self):
        with patch.object(worker, 'ensure_lease'), patch.object(worker, 'check_owned_sources'), patch.object(worker, 'assert_storage_available'), \
                patch.object(worker, 'storage_refusal', return_value=None), patch.object(worker, 'remember_execution_failure'), \
                patch.object(worker, 'workflow', side_effect=ValueError('actual mobile semantic assertion failed')), patch.object(worker, 'model') as provider:
            with self.assertRaisesRegex(ValueError, 'mobile semantic'):
                worker.execute('unused', self.f.profile, self.f.spec, self.g['task'])
            provider.assert_not_called()

    def test_both_viewports_need_distinct_actual_raw_owner_receipts(self):
        self.f.tool_backed(self.g); self.validate()
        desktop, mobile = self.g['children']
        copied = copy.deepcopy(desktop['backend_observations'][0])
        for kind in ('receipt', 'event'):
            old = self.f.root / copied[kind+'_artifact']; target = self.g['folder']/'mobile'/('copied-'+kind+'.json')
            self.f.write(str(target.relative_to(self.f.root)), old.read_bytes())
            copied[kind+'_artifact'] = str(target.relative_to(self.f.root)); mobile['artifacts'].append(final.reference(self.f.root, target))
        mobile['backend_observations'] = [copied]; self.f.persist(self.g)
        with self.assertRaisesRegex(ValueError, 'reused desktop owner'): self.validate()

    def test_raw_owner_binding_spoof_even_with_real_matching_cids_refuses(self):
        self.f.tool_backed(self.g, raw_binding='unrelated.get')
        with self.assertRaisesRegex(ValueError, 'different binding'): self.validate()

    def test_owner_fallback_self_consistent_wrong_semantics_refuses(self):
        self.f.tool_backed(self.g, declared='wanted', observed='actual')
        with self.assertRaisesRegex(ValueError, 'declared backend probe/fallback'): self.validate()

    def test_backend_result_actual_must_join_raw_proof_not_just_pass_its_own_assertion(self):
        self.f.tool_backed(self.g, observed=3, semantic=True); self.validate()
        next(item for item in self.g['children'][1]['semantic_assertions'] if item['requirement_id'] == 'persist_reopen')['observed']['actual'] = 2
        self.f.persist(self.g)
        with self.assertRaisesRegex(ValueError, 'detached from its actual raw owner'): self.validate()

    def test_geometry_matches_collector_tolerance_and_internal_scroll_policy(self):
        child = self.g['children'][1]; view = child['viewports'][0]
        view['primary'].update(left=-1, top=-1, height=2000)
        target = self.f.write(str((self.g['folder']/'mobile/mobile-layout.json').relative_to(self.f.root)), {key: value for key, value in view.items() if key != 'name'})
        child['artifacts'][1] = final.reference(self.f.root, target)
        self.f.persist(self.g); self.validate()
        view['primary']['top'] = view['window']['bottom']
        target = self.f.write(str((self.g['folder']/'mobile/mobile-layout.json').relative_to(self.f.root)), {key: value for key, value in view.items() if key != 'name'})
        child['artifacts'][1] = final.reference(self.f.root, target)
        self.f.persist(self.g)
        with self.assertRaisesRegex(ValueError, 'geometry'): self.validate()


if __name__ == '__main__': unittest.main(verbosity=2)
