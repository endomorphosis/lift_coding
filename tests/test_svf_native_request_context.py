"""Portable authored native-context fixtures; no browser, SDK, RPC or acceptance.

Every source, trace, process receipt and output in these tests is authored in a
private temporary tree. They exercise strict joins, never genuine execution.
"""
import base64
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
import uuid
import zipfile

HELPER = Path(os.environ.get('SVF_NATIVE_CONTEXT_HELPER', Path(__file__).resolve().parents[1] / 'scripts/swissknife_visual_functional_final_coverage.py'))
_spec = importlib.util.spec_from_file_location('svf_authored_native_context', HELPER)
e = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(e)
PHASES = ('primary_result', 'persist_reopen', 'failure_recovery')
PROVENANCE_SOURCES = (
 'external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/runtime/resource_scheduler.py',
 'external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/task_sources/database_task_source.py',
 'external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/task_sources/intent_repository.py',
 'external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/verification/process_runner.py',
 'scripts/svf_backends/fixed_supervisor_output_validator.py',
 'scripts/svf_backends/fixed_supervisor_worker.py',
 'scripts/svf_backends/native_accelerate_service.py',
 'scripts/svf_backends/native_supervisor_backend.py',
 'swissknife/scripts/ipfs-accelerate-native-forwarder.cjs',
 'swissknife/scripts/start-ipfs-accelerate-mcp-compat.cjs',
)

def sha(raw):
 return hashlib.sha256(raw).hexdigest()

def authored_uuid(value):
 return str(uuid.uuid5(uuid.NAMESPACE_URL, 'authored-native-context:' + value))

class Fixture:
 def __init__(self, root):
  self.root = Path(root)
  self.fixture_root = self.root / 'data/agent_supervisor/swissknife_visual_functional/backends/supervisor-fixtures'
  self.provenance = {'schema': 'swissknife.native-supervisor-execution.v1', 'owner': 'ipfs_accelerate_py', 'simulated': False, 'cache_fallback': False, 'source_sha256': {}}
  for name in PROVENANCE_SOURCES:
   raw = ('# Authored source fixture; never executed: ' + name + '\n').encode()
   self.write(name, raw)
   self.provenance['source_sha256'][name] = sha(raw)
  self.records = {}
  self.children = {}
  self.entries = []
  self.report = self.root / 'reports/workflow.json'

 def write(self, name, raw):
  p = self.root / name
  p.parent.mkdir(parents=True, exist_ok=True)
  p.write_bytes(raw)
  return p

 def write_json(self, name, value):
  return self.write(name, e.encoded(value))

 def pair(self, view, run, stage, task):
  challenge = authored_uuid(view + run + ':challenge').replace('-', '')
  data = e.encoded({'authored_only': True, 'run_id': run, 'stage': stage, 'task': task})
  output = self.write(str((self.fixture_root / run / (stage + '.json')).relative_to(self.root)), data)
  body = {'run_id': run, 'task_key': stage, 'task_id': task, 'challenge': challenge, 'status': 'completed', 'output_sha256': sha(data), 'native_provenance': copy.deepcopy(self.provenance), 'execution': {}}
  for role, source in [('producer', 'scripts/svf_backends/fixed_supervisor_worker.py'), ('validator', 'scripts/svf_backends/fixed_supervisor_output_validator.py')]:
   result = {'output_sha256': sha(data)}
   if role == 'producer':
    result.update(output_path=str(output), bytes=len(data))
   else:
    result.update(validated=True, stage=stage, validator_source_sha256=sha((self.root / source).read_bytes()))
   text = e.encoded(result).decode()
   executable = '/usr/bin/python3'
   record = {'schema': 'ipfs_accelerate_py/agent-supervisor/verification-process-runner@1', 'ok': True, 'process_started': True, 'exit_code': 0, 'terminal_status': 'passed', 'timed_out': False, 'cancelled': False, 'executable': executable, 'command_argv': [executable, '-I', '-B', str(self.root / source), '--runtime-root', str(self.fixture_root), '--run-id', run, '--stage', stage, '--challenge', challenge], 'stdout': {'preview': text, 'truncated': False, 'byte_count': len(text.encode()), 'captured_byte_count': len(text.encode()), 'digest': 'sha256:' + sha(text.encode())}}
   path = self.write_json(str((self.fixture_root / run / 'attempts' / (stage + '-' + role) / 'result.json').relative_to(self.root)), record)
   body['execution'][role] = {'path': str(path), 'sha256': sha(path.read_bytes())}
  return body

 def call(self, view, index, payload, owner='ipfs_accelerate_py', tool='WorkflowCoordinator.submit_task'):
  return {'protocol': 'swissknife.all-app-tool-gateway.v1', 'app_id': self.app, 'binding_id': 'authored.binding', 'intent_id': 'authored.intent', 'owner': owner, 'tool_id': tool, 'transport': 'http', 'route': '/mcp/tools/call', 'receipt_required': True, 'correlation_id': view + ':authored-' + str(index), 'input': {'payload': payload, 'correlation_id': view + ':authored-' + str(index), 'policy': {'decision_id': 'authored-policy', 'outcome': 'allow' if tool in ('get_task', 'ipfs_cat') else 'require_confirmation', 'consent': 'not_required' if tool in ('get_task', 'ipfs_cat') else 'granted', 'dry_run': False, 'reason': 'Authored protocol fixture; never actual consent or execution.'}}}

 def response(self, call, body=None, *, error=None, video=False):
  if error is not None:
   result = {'error': error}
  else:
   inner = {'isError': False, 'content': [{'type': 'json', 'json': body}]}
   if video:
    inner['receipt'] = {'adapter': 'swissknife-ipfs-kit-compat'}
   result = {'result': inner}
  receipt = {}
  for kind, key in [('receipt', 'receipt_id'), ('event', 'event_dag_refs')]:
   cid = e._native_raw_cid(e.encoded({'call': call, 'kind': kind, 'result': result}))
   receipt[key] = [cid] if kind == 'event' else cid
  receipt.update(owner=call['owner'], tool_id=call['tool_id'], transport=call['transport'], correlation_id=call['correlation_id'], policy_outcome=call['input']['policy']['outcome'], outcome='executed' if error is None else 'failed', receipt_refs=[receipt['receipt_id']])
  receipt['persistence'] = {'status': 'persisted', 'receipt_cid': receipt['receipt_id'], 'event_cid': receipt['event_dag_refs'][0]}
  return {'ok': error is None, 'outcome': 'executed' if error is None else 'failed', 'owner': call['owner'], 'tool_id': call['tool_id'], 'transport': call['transport'], 'correlation_id': call['correlation_id'], 'result': result, 'receipt': receipt}

 def supervisor(self, view):
  self.app = 'authored-supervisor'
  runs = []
  for n in range(2):
   run, a, b = [authored_uuid(view + ':' + str(n) + ':' + k) for k in ('run', 'a', 'b')]
   runs.append((run, a, b))
  first = self.pair(view, runs[0][0], 'a', runs[0][1])
  second = self.pair(view, runs[1][0], 'a', runs[1][1])
  third = self.pair(view, runs[1][0], 'b', runs[1][2])
  readback = {k: copy.deepcopy(v) for k, v in first.items() if k != 'execution'}
  descriptors = [('create', 0, None, None), ('dispatch', 0, 'a', first), ('read', 0, 'a', readback), ('create', 1, None, None), ('dispatch', 1, 'b', 'failure'), ('dispatch', 1, 'a', second), ('retry', 1, 'b', third)]
  rows = []
  for index, (action, which, stage, body) in enumerate(descriptors):
   run, a, b = runs[which]
   payload = {'action': action, 'run_id': run}
   if stage:
    payload['task_key'] = stage
   if action == 'read':
    payload.pop('action')
   if action == 'create':
    body = {'run_id': run, 'task_ids': {'a': a, 'b': b}, 'native_provenance': copy.deepcopy(self.provenance)}
   call = self.call(view, index, payload, tool='get_task' if action == 'read' else 'WorkflowCoordinator.submit_task')
   response = self.response(call, error='JSON-RPC Error -32603: task is not ready') if body == 'failure' else self.response(call, body)
   phase = PHASES[0 if index < 2 else 1 if index == 2 else 2]
   rows.append({'call': call, 'response': response, 'phase': phase, 'step': [0, 1, 0, 0, 1, 2, 3][index], 'generation': 0 if index < 2 else 1})
  self.finish(view, rows, supervisor_body=first)
  return rows

 def cinema(self, view, *, source_size=70000, export_size=96, source_format='webm'):
  self.app = 'authored-cinema'
  header = b'\x00\x00\x00\x18ftypmp42' if source_format == 'mp4' else b'\x1aE\xdf\xa3'
  source = header + b's' * (source_size - len(header))
  output = b'\x1aE\xdf\xa3' + b'o' * (export_size - 4)
  source_cid, output_cid = map(e._native_raw_cid, (source, output))
  project = {'schema': 'swissknife.cinema.project.v1', 'source': {'cid': source_cid, 'size': len(source), 'sha256': sha(source)}, 'output': {'cid': output_cid, 'size': len(output), 'sha256': sha(output), 'trim': {'start': 0, 'end': 1}}, 'timeline': {'tracks': [{'kind': 'video', 'order': 0, 'in': 0, 'out': 1}]}}
  project_bytes = e.encoded(project)
  descriptors = [('ipfs_cat', 'source', source, source_cid), ('artifacts_put', 'video-export', output, output_cid), ('artifacts_put', 'video-project', project_bytes, e._native_raw_cid(project_bytes))]
  rows = []
  for index, (tool, kind, data, cid) in enumerate(descriptors):
   payload = {'cid': cid}
   body = {'success': True, 'cid': cid, 'backend': 'authored-native-owner'}
   if tool == 'ipfs_cat':
    body['bytes_base64'] = base64.b64encode(data).decode()
   else:
    payload.update(kind=kind, bytes_base64=base64.b64encode(data).decode())
    body.update(persisted=True, verified=True, bytes=len(data))
   call = self.call(view, index, payload, owner='ipfs_kit_py', tool=tool)
   rows.append({'call': call, 'response': self.response(call, body, video=True), 'phase': PHASES[0 if index < 2 else 1], 'step': index if index < 2 else 0, 'generation': 0 if index < 2 else 1})
  self.finish(view, rows)
  for phase, cid in [('primary_result', source_cid), ('persist_reopen', output_cid)]:
   selector = '[data-authored-native-video]'
   before = {'present': True, 'tag': 'VIDEO', 'visible': True, 'ready_state': 2, 'video_width': 64, 'video_height': 48, 'decoded_cid': cid, 'src_sha256': sha(b'authored-object-url'), 'current_time': 0}
   after = {**before, 'current_time': 0.1}
   selected = next(p for p in self.children[view]['phase_evidence']['phases'] if p['phase'] == phase)
   selected['steps'].append({'step_index': 5, 'step': {'op': 'assert', 'probe': {'kind': 'media_state', 'selector': selector, 'temporal_ms': 10}}, 'media': [{'selector': selector, 'same_element': True, 'before': before, 'after': after}]})
  self.save_child(view)
  return rows

 def finish(self, view, rows, *, supervisor_body=None):
  self.records[view] = rows
  scenario = {'backend_bindings': [{'binding_id': 'authored.binding'}], 'phases': {p: [{'op': 'assert'}] * 6 for p in PHASES}}
  self.write_json('swissknife/test/e2e/functional-workflows/' + self.app + '.json', scenario)
  folder = self.root / 'reports' / view
  folder.mkdir(parents=True, exist_ok=True)
  artifacts, observations, witnesses, network, resources = [], [], [], [], {}
  for index, row in enumerate(rows):
   call, response = row['call'], row['response']
   req, resp = e.encoded(call), e.encoded(response)
   request_name, response_name = [hashlib.sha1(raw).hexdigest() + '.json' for raw in (req, resp)]
   resources['resources/' + request_name] = req
   resources['resources/' + response_name] = resp
   network.append({'type': 'resource-snapshot', 'snapshot': {'request': {'url': 'http://127.0.0.1:3017/mcp/tools/call', 'method': 'POST', 'postData': {'text': '', '_sha1': request_name}}, 'response': {'status': 200, 'content': {'_sha1': response_name}}}})
   witness = {'request_index': index, 'phase': row['phase'], 'step_index': row['step'], 'generation': row['generation'], 'binding_id': call['binding_id'], 'correlation_id': call['correlation_id'], 'call_sha256': e.digest(call)}
   witnesses.append(witness)
   item = {'request_phase_index': index, 'binding_id': call['binding_id'], 'correlation_id': call['correlation_id']}
   for kind, cid in [('receipt', response['receipt']['receipt_id']), ('event', response['receipt']['event_dag_refs'][0])]:
    raw = e.encoded({'call': call, 'kind': kind, 'result': response['result']})
    p = self.write(str((folder / 'backend' / (kind + '-' + cid + '.json')).relative_to(self.root)), raw)
    artifacts.append(e.reference(self.root, p))
    item[kind + '_artifact'] = str(p.relative_to(self.root))
   observations.append(item)
  trace = folder / 'trace.zip'
  with zipfile.ZipFile(trace, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
   archive.writestr('trace.network', b'\n'.join(e.encoded(row) for row in network))
   for name, raw in resources.items():
    archive.writestr(name, raw)
  artifacts.append(e.reference(self.root, trace))
  child = {'app_id': self.app, 'artifacts': artifacts, 'backend_observations': observations, 'backend_call_count': len(rows), 'backend_call_phases': {p: sum(row['phase'] == p for row in rows) for p in (*PHASES, 'backend_proof', 'unknown')}, 'backend_request_phases': {'schema': e.BACKEND_REQUEST_PHASE_SCHEMA, 'requests': witnesses}, 'semantic_assertions': [], 'phase_evidence': {'phases': []}}
  history = ' '.join(r['response']['receipt']['receipt_id'] + ' ' + r['response']['receipt']['event_dag_refs'][0] for r in rows[:2])
  for phase in PHASES:
   observed = {'actual': history}
   if phase == 'persist_reopen' and supervisor_body:
    receipt = rows[2]['response']['receipt']
    observed = {'actual': history + ' ' + ' '.join(supervisor_body[k] for k in ('run_id', 'task_id', 'output_sha256')) + ' ' + receipt['receipt_id'] + ' ' + receipt['event_dag_refs'][0]}
   child['phase_evidence']['phases'].append({'phase': phase, 'generation_before': 0 if phase == 'primary_result' else 1, 'generation_after': 0 if phase == 'primary_result' else 1, 'steps': [{'step_index': 4, 'step': {'op': 'assert', 'probe': {'kind': 'text'}}, 'observed': observed}]})
   if phase in ('primary_result', 'persist_reopen'):
    child['semantic_assertions'].append({'phase': phase, 'step_index': 4, 'requirement_id': phase, 'probe': {'kind': 'text'}, 'observed': observed})
  self.children[view] = child
  self.save_child(view)

 def save_child(self, view):
  p = self.write_json('reports/' + view + '/workflow.json', self.children[view])
  self.entries = [v for v in self.entries if v['name'] != view] + [{'name': view, 'report': e.reference(self.root, p)}]
  self.entries.sort(key=lambda v: ('desktop', 'mobile').index(v['name']))
  self.write_json('reports/workflow.json', {'viewport_reports': self.entries})

 def mutate_archive(self, body, role, mutation):
  ref = body['execution'][role]
  p = Path(ref['path'])
  record = e.parse(p.read_bytes())
  mutation(record)
  p.write_bytes(e.encoded(record))
  ref['sha256'] = sha(p.read_bytes())

class NativeRequestFactsTests(unittest.TestCase):
 def test_supervisor_all_seven_requests_and_true_history(self):
  with tempfile.TemporaryDirectory() as tmp:
   f = Fixture(tmp)
   f.supervisor('desktop');f.supervisor('mobile')
   facts = e.native_request_facts(f.root, f.report)
   self.assertEqual(facts['format'], 'supervisor')
   self.assertEqual(len(facts['views']), 2)
   for view in facts['views']:
    self.assertEqual([row[0] for row in view['rows']], list(range(7)))
    self.assertIn('4', view['errors'])
    self.assertEqual(view['retained_UI_event_rows'], [0, 1])
   self.assertIn('reconstructed, not fetched', facts['proof'])

 def test_trace_call_witness_cid_and_retained_bytes_negatives(self):
  for fault in ('witness', 'cid', 'retained_bytes', 'foreign_trace', 'extra_request', 'receipt_identity', 'dry_run'):
   with self.subTest(fault=fault), tempfile.TemporaryDirectory() as tmp:
    f = Fixture(tmp);rows = f.supervisor('desktop');child = f.children['desktop'];path = f.root / 'reports/desktop/workflow.json'
    if fault == 'witness':
     child['backend_request_phases']['requests'][0]['call_sha256'] = 'f' * 64
    elif fault == 'cid':
     rows[0]['response']['receipt']['receipt_id'] = e._native_raw_cid(b'foreign claim')
     rows[0]['response']['receipt']['persistence']['receipt_cid'] = rows[0]['response']['receipt']['receipt_id']
     f.finish('desktop', rows)
    elif fault == 'receipt_identity':
     rows[0]['response']['receipt']['correlation_id'] = 'foreign-receipt'
     f.finish('desktop', rows)
    elif fault == 'dry_run':
     rows[0]['call']['input']['policy']['dry_run'] = True
     body = e._native_body(rows[0]['response']['result'])
     rows[0]['response'] = f.response(rows[0]['call'], body)
     f.finish('desktop', rows)
    elif fault == 'retained_bytes':
     p = f.root / child['backend_observations'][0]['receipt_artifact'];p.write_bytes(b'{}')
     child['artifacts'] = [e.reference(f.root, p) if r['path'] == str(p.relative_to(f.root)) else r for r in child['artifacts']]
    elif fault == 'foreign_trace':
     item = next(r for r in child['artifacts'] if r['path'].endswith('trace.zip'))
     p = f.write('foreign/trace.zip', (f.root / item['path']).read_bytes());child['artifacts'] = [e.reference(f.root, p) if r is item else r for r in child['artifacts']]
    else:
     child['backend_request_phases']['requests'].pop();child['backend_call_count'] -= 1;child['backend_call_phases']['failure_recovery'] -= 1;child['backend_observations'].pop()
    child = f.children['desktop']
    with self.assertRaises((ValueError, KeyError)):
     e._native_trace_rows(f.root, child, path)

 def test_native_archive_output_and_source_joins(self):
  faults = ('archive_hash', 'source', 'foreign_path', 'same_pair', 'argv', 'timeout', 'stdout_digest', 'output', 'validator')
  for fault in faults:
   with self.subTest(fault=fault), tempfile.TemporaryDirectory() as tmp:
    f = Fixture(tmp);rows = f.supervisor('desktop');body = e._native_body(rows[1]['response']['result']);row = {'body': body, 'call': rows[1]['call']}
    self.assertTrue(e._native_supervisor_pair(f.root, row))
    if fault == 'archive_hash':
     body['execution']['producer']['sha256'] = '0' * 64
    elif fault == 'source':
     (f.root / PROVENANCE_SOURCES[0]).write_bytes(b'changed source')
    elif fault == 'foreign_path':
     body['execution']['producer']['path'] = str(f.root / 'foreign/result.json')
    elif fault == 'same_pair':
     body['execution']['validator'] = copy.deepcopy(body['execution']['producer'])
    elif fault == 'argv':
     f.mutate_archive(body, 'producer', lambda r: r['command_argv'].__setitem__(-1, 'foreign-challenge'))
    elif fault == 'timeout':
     f.mutate_archive(body, 'producer', lambda r: r.update(timed_out=True))
    elif fault == 'stdout_digest':
     f.mutate_archive(body, 'producer', lambda r: r['stdout'].update(digest='sha256:' + '0' * 64))
    elif fault == 'output':
     (f.fixture_root / body['run_id'] / 'a.json').write_bytes(b'changed output')
    else:
     def invalidate_validator(record):
      value = e.parse(record['stdout']['preview']);value['validated'] = False
      text = e.encoded(value).decode();record['stdout'].update(preview=text, byte_count=len(text.encode()), captured_byte_count=len(text.encode()), digest='sha256:' + sha(text.encode()))
     f.mutate_archive(body, 'validator', invalidate_validator)
    with self.assertRaises(ValueError):
     e._native_supervisor_pair(f.root, row)

 def test_history_reopen_and_readback_negatives(self):
  for fault in ('missing_history', 'generation', 'dom_mismatch', 'readback'):
   with self.subTest(fault=fault), tempfile.TemporaryDirectory() as tmp:
    f = Fixture(tmp);f.supervisor('desktop');f.supervisor('mobile');c = f.children['mobile']
    if fault == 'generation':
     c['backend_request_phases']['requests'][2]['generation'] = 0;c['phase_evidence']['phases'][1]['generation_before'] = 0
    else:
     assertion = next(v for v in c['semantic_assertions'] if v['phase'] == 'persist_reopen')
     if fault == 'missing_history':
      assertion['observed']['actual'] = assertion['observed']['actual'].replace(f.records['mobile'][0]['response']['receipt']['receipt_id'], '')
     elif fault == 'dom_mismatch':
      c['phase_evidence']['phases'][1]['steps'][0]['observed'] = {'actual': 'different retained observation'}
     else:
      assertion['observed']['actual'] = assertion['observed']['actual'].replace(e._native_body(f.records['mobile'][2]['response']['result'])['output_sha256'], '')
    f.save_child('mobile')
    with self.assertRaises(ValueError):
     e.native_request_facts(f.root, f.report)

 def test_video_source_above_export_bound_and_project_joins(self):
  with tempfile.TemporaryDirectory() as tmp:
   f = Fixture(tmp);f.cinema('desktop', source_size=70000);f.cinema('mobile', source_size=70000)
   result = e.native_request_facts(f.root, f.report)
   self.assertEqual(result['format'], 'video-artifacts')
   self.assertEqual([v['artifacts'][0][1] for v in result['views']], [70000, 70000])
   self.assertEqual([v['projects'][0][:2] for v in result['views']], [[0, 1], [0, 1]])

 def test_supported_mp4_source_preserves_webm_only_output(self):
  with tempfile.TemporaryDirectory() as tmp:
   f = Fixture(tmp);f.cinema('desktop', source_size=100, source_format='mp4');f.cinema('mobile', source_size=100, source_format='mp4')
   facts = e.native_request_facts(f.root, f.report)
   self.assertEqual([v['artifacts'][0][1:3] for v in facts['views']], [[100, 'source'], [100, 'source']])
   self.assertEqual([v['artifacts'][1][2] for v in facts['views']], ['video-export', 'video-export'])

 def test_video_source_one_mib_and_overflow_export_bound(self):
  for size, export, allowed in ((1048576, 96, True), (1048577, 96, False), (100, 65537, False)):
   with self.subTest(source_size=size, export_size=export), tempfile.TemporaryDirectory() as tmp:
    f = Fixture(tmp);f.cinema('desktop', source_size=size, export_size=export);f.cinema('mobile', source_size=size, export_size=export)
    if allowed:
     self.assertEqual(e.native_request_facts(f.root, f.report)['views'][0]['artifacts'][0][1], size)
    else:
     with self.assertRaises(ValueError):e.native_request_facts(f.root, f.report)

 def test_decoded_video_requires_actual_playback_and_owner_cid(self):
  for fault in ('stationary', 'foreign_cid', 'not_ready'):
   with self.subTest(fault=fault), tempfile.TemporaryDirectory() as tmp:
    f = Fixture(tmp);f.cinema('desktop', source_size=100);f.cinema('mobile', source_size=100)
    phase = f.children['mobile']['phase_evidence']['phases'][0];media = phase['steps'][-1]['media'][0]
    if fault == 'stationary':media['after']['current_time'] = media['before']['current_time']
    elif fault == 'foreign_cid':
     media['before']['decoded_cid'] = media['after']['decoded_cid'] = e._native_raw_cid(b'foreign image')
    else:media['after']['ready_state'] = 1
    f.save_child('mobile')
    with self.assertRaises(ValueError):e.native_request_facts(f.root, f.report)

 def test_mixed_native_formats_cannot_share_one_facts_packet(self):
  with tempfile.TemporaryDirectory() as tmp:
   f = Fixture(tmp);f.supervisor('desktop');f.cinema('mobile', source_size=100)
   with self.assertRaises(ValueError):e.native_request_facts(f.root, f.report)

 def test_non_native_report_remains_without_added_facts(self):
  with tempfile.TemporaryDirectory() as tmp:
   f = Fixture(tmp)
   f.write_json('reports/workflow.json', {'viewport_reports': []})
   self.assertIsNone(e.native_request_facts(f.root, f.report))

if __name__ == '__main__':
 unittest.main()


class RetainedNativeContextTests(unittest.TestCase):
 """Add literal identity/observable caution facts without fabricating liveness."""
 CAUTION = 'Heartbeat and progress percent are not completion.'

 def with_caution(self, fixture, view):
  fixture.supervisor(view)
  child = fixture.children[view]
  for phase in ('primary_result', 'persist_reopen'):
   assertion = next(row for row in child['semantic_assertions'] if row['phase'] == phase)
   assertion['observed']['actual'] += ' ' + self.CAUTION
   assertion['observed']['expected'] = self.CAUTION
  fixture.save_child(view)

 def test_retained_events_are_literal_exact_request_ids(self):
  with tempfile.TemporaryDirectory() as tmp:
   f = Fixture(tmp)
   for name in ('desktop', 'mobile'):
    self.with_caution(f, name)
   facts = e.native_request_facts(f.root, f.report)
   for view in facts['views']:
    expected = [[index, f.records[view['name']][index]['response']['receipt']['receipt_id'], f.records[view['name']][index]['response']['receipt']['event_dag_refs'][0]] for index in (0, 1)]
    self.assertEqual(view['retained_UI_events'], expected)
    for _, receipt, event in view['retained_UI_events']:
     self.assertIsInstance(receipt, str)
     self.assertIsInstance(event, str)
     self.assertTrue(receipt.startswith('bafkrei'))
     self.assertTrue(event.startswith('bafkrei'))

 def test_caution_quotes_are_observed_bounded_and_ui_only(self):
  with tempfile.TemporaryDirectory() as tmp:
   f = Fixture(tmp)
   for name in ('desktop', 'mobile'):
    self.with_caution(f, name)
   facts = e.native_request_facts(f.root, f.report)
   for view in facts['views']:
    quotes = view['observed_UI_text']
    self.assertEqual(len(quotes), 2)
    for phase, step, quote in quotes:
     self.assertIn(phase, (0, 1))
     self.assertEqual(step, 4)
     self.assertIn(self.CAUTION, quote)
     self.assertLessEqual(len(quote.split()), 30)
     original = next(row for row in f.children[view['name']]['semantic_assertions'] if row['phase'] == PHASES[phase])
     self.assertIn(quote, original['observed']['actual'])
   encoded = e.encoded(facts).decode()
   self.assertNotIn('"heartbeat_fresh"', encoded)
   self.assertNotIn('"heartbeat_at_ms"', encoded)
   self.assertNotIn('"progress_percent"', encoded)

 def test_unobserved_caution_is_never_fabricated(self):
  with tempfile.TemporaryDirectory() as tmp:
   f = Fixture(tmp);f.supervisor('desktop');f.supervisor('mobile')
   facts = e.native_request_facts(f.root, f.report)
   for view in facts['views']:
    self.assertEqual(view['observed_UI_text'], [])

 def test_created_absence_and_validated_outputs_are_explicit(self):
  with tempfile.TemporaryDirectory() as tmp:
   f = Fixture(tmp);f.supervisor('desktop');f.supervisor('mobile')
   facts = e.native_request_facts(f.root, f.report)
   for view in facts['views']:
    self.assertEqual(view['created_without_output'], [0, 3])
    expected = []
    for index in (1, 5, 6):
     body = e._native_body(f.records[view['name']][index]['response']['result'])
     output = f.fixture_root / body['run_id'] / (body['task_key'] + '.json')
     expected.append([index, 'completed', len(output.read_bytes()), 0, 0, True])
    self.assertEqual(view['validated_outputs'], expected)
    self.assertNotIn(2, [row[0] for row in view['validated_outputs']], 'readback cannot invent a new execution/validation')

 def test_created_output_or_completion_cannot_be_claimed_absent(self):
  for added in ({'status': 'completed'}, {'output_sha256': 'a' * 64}, {'execution': {}}):
   with self.subTest(added=added), tempfile.TemporaryDirectory() as tmp:
    f = Fixture(tmp);f.supervisor('desktop');f.supervisor('mobile')
    rows = f.records['mobile']
    body = e._native_body(rows[0]['response']['result']);body.update(added)
    rows[0]['response'] = f.response(rows[0]['call'], body)
    first = e._native_body(rows[1]['response']['result'])
    f.finish('mobile', rows, supervisor_body=first)
    facts = e.native_request_facts(f.root, f.report)
    mobile = next(view for view in facts['views'] if view['name'] == 'mobile')
    self.assertNotIn(0, mobile['created_without_output'])

 def test_previous_supervisor_typed_view_tree_is_unchanged(self):
  with tempfile.TemporaryDirectory() as tmp:
   f = Fixture(tmp);f.supervisor('desktop');f.supervisor('mobile')
   facts = e.native_request_facts(f.root, f.report)
   old_keys = {'name', 'trace', 'runs', 'outputs', 'rows', 'errors', 'retained_UI_event_rows', 'retention_positions', 'readback_request'}
   expected_rows = [[0,0,0,0,0,None,0,None,None], [1,0,1,1,0,'a',0,0,True], [2,1,0,2,0,'a',0,0,None], [3,2,0,0,1,None,0,None,None], [4,2,1,1,1,'b',1,None,None], [5,2,2,1,1,'a',0,1,True], [6,2,3,3,1,'b',0,2,True]]
   for view in facts['views']:
    records = f.records[view['name']]
    bodies = [e._native_body(row['response']['result']) for row in records]
    trace = next(ref for ref in f.children[view['name']]['artifacts'] if ref['path'].endswith('trace.zip'))
    expected = {'name': view['name'], 'trace': {'path': 'trace.zip', 'sha256': trace['sha256']}, 'runs': [[bodies[i]['run_id'], bodies[i]['task_ids']['a'], bodies[i]['task_ids']['b']] for i in (0,3)], 'outputs': [bodies[i]['output_sha256'] for i in (1,5,6)], 'rows': expected_rows, 'errors': {'4': 'JSON-RPC Error -32603: task is not ready'}, 'retained_UI_event_rows': [0,1], 'retention_positions': [[0,4,0],[1,4,1]], 'readback_request': 2}
    self.assertEqual({key: view[key] for key in old_keys}, expected)

 def test_cinema_typed_view_tree_has_no_supervisor_additions(self):
  with tempfile.TemporaryDirectory() as tmp:
   f = Fixture(tmp);f.cinema('desktop', source_size=100);f.cinema('mobile', source_size=100)
   facts = e.native_request_facts(f.root, f.report)
   self.assertEqual(set(facts), {'format', 'proof', 'views', 'phases', 'columns', 'artifact_columns', 'project_columns', 'tools', 'decoded', 'legacy_cid_scope', 'recovery_sequence'})
   for view in facts['views']:
    records = f.records[view['name']]
    bodies = [e._native_body(row['response']['result']) for row in records]
    artifacts = [[body['cid'], [100,96,len(base64.b64decode(records[2]['call']['input']['payload']['bytes_base64']))][i], ['source','video-export','video-project'][i], body['backend']] for i,body in enumerate(bodies)]
    trace = next(ref for ref in f.children[view['name']]['artifacts'] if ref['path'].endswith('trace.zip'))
    expected = {'name': view['name'], 'trace': {'path': 'trace.zip', 'sha256': trace['sha256']}, 'artifacts': artifacts, 'projects': [[0,1,{'start':0,'end':1},[['video',0,0,1]]]], 'rows': [[0,0,0,0,0],[1,0,1,1,1],[2,1,0,1,2]], 'decoded_artifact_rows': [[0,5,0,1],[1,5,1,1]]}
    self.assertEqual(view, expected)


class CinemaRecoveryChronologyTests(unittest.TestCase):
 def setup_view(self, fixture, view):
  fixture.cinema(view, source_size=100)
  phase_evidence = copy.deepcopy(fixture.children[view]['phase_evidence'])
  rows = fixture.records[view]
  data = b'\x1aE\xdf\xa3authored later WebM bytes'
  cid = e._native_raw_cid(data)
  call = fixture.call(view, 3, {'cid': cid, 'kind': 'video-export', 'bytes_base64': base64.b64encode(data).decode()}, owner='ipfs_kit_py', tool='artifacts_put')
  body = {'success': True, 'cid': cid, 'backend': 'authored-native-owner', 'persisted': True, 'verified': True, 'bytes': len(data)}
  rows.append({'call': call, 'response': fixture.response(call, body, video=True), 'phase': 'failure_recovery', 'step': 12, 'generation': 1})
  fixture.finish(view, rows)
  child = fixture.children[view];child['phase_evidence'] = phase_evidence
  recovery = next(phase for phase in phase_evidence['phases'] if phase['phase'] == 'failure_recovery')
  child['error_observations'] = [];child['supplemental_observations'] = []
  for index, selector, text in [(2, '[data-cinema-workflow-status]', 'Unsupported codec authored-mp4'), (7, '[data-cinema-export-outcome]', 'Export unsupported; authored unavailable encoder')]:
   probe = {'kind': 'text', 'selector': selector}
   observed = {'operator': 'contains', 'expected': 'unsupported', 'actual': text}
   step = {'op': 'assert', 'probe': probe, 'operator': 'contains', 'expected': 'unsupported'}
   observation = {'phase': 'failure_recovery', 'step_index': index, 'probe': probe, 'observed': observed}
   if index == 2:
    step['checkpoint_id'] = 'error_observed';observation['checkpoint_id'] = 'error_observed';child['error_observations'].append(observation)
   else:
    child['supplemental_observations'].append(observation)
   recovery['steps'].append({'step_index': index, 'step': step, 'observed': observed})
  selector = '[data-authored-native-recovery-video]'
  before = {'present': True, 'tag': 'VIDEO', 'visible': True, 'ready_state': 2, 'video_width': 64, 'video_height': 48, 'decoded_cid': cid, 'src_sha256': sha(b'authored recovery object URL'), 'current_time': 0}
  recovery['steps'].append({'step_index': 17, 'step': {'op': 'assert', 'probe': {'kind': 'media_state', 'selector': selector, 'temporal_ms': 10}}, 'media': [{'selector': selector, 'same_element': True, 'before': before, 'after': {**before, 'current_time': 0.1}}]})
  recovery['steps'].sort(key=lambda step: step['step_index'])
  scenario = e.parse((fixture.root / ('swissknife/test/e2e/functional-workflows/' + fixture.app + '.json')).read_bytes())
  scenario['phases']['failure_recovery'] = [{'op': 'assert'}] * 20
  fixture.write_json('swissknife/test/e2e/functional-workflows/' + fixture.app + '.json', scenario)
  fixture.save_child(view)

 def test_literal_cinema_scope_and_strict_actual_recovery_order(self):
  with tempfile.TemporaryDirectory() as tmp:
   f = Fixture(tmp)
   for view in ('desktop', 'mobile'):
    self.setup_view(f, view)
   facts = e.native_request_facts(f.root, f.report)
   self.assertIn('declared result-assertion CIDs', facts['legacy_cid_scope'])
   self.assertIn('not every owner return', facts['legacy_cid_scope'])
   sequence = facts['recovery_sequence']
   self.assertEqual(sequence['phase'], 'failure_recovery')
   self.assertEqual(sequence['views'], {'desktop': [[2,12,17,3],[7,12,17,3]], 'mobile': [[2,12,17,3],[7,12,17,3]]})

 def test_recovery_metadata_rejects_forged_observation_and_does_not_infer_order(self):
  for fault in ('forged_observation', 'too_late', 'other_artifact'):
   with self.subTest(fault=fault), tempfile.TemporaryDirectory() as tmp:
    f = Fixture(tmp)
    for view in ('desktop', 'mobile'):
     self.setup_view(f, view)
    child = f.children['mobile'];recovery = next(phase for phase in child['phase_evidence']['phases'] if phase['phase'] == 'failure_recovery')
    if fault == 'forged_observation':
     # Break the independent observation-to-phase record equality, retaining its
     # native outcome prefix so the extraction must check the join.
     child['error_observations'][0]['observed'] = {**child['error_observations'][0]['observed'], 'actual': 'Unsupported codec forged observation'}
    elif fault == 'too_late':
     for old, new in ((2,13),(7,14)):
      observation = next(item for item in child['error_observations'] + child['supplemental_observations'] if item['step_index'] == old)
      observation['step_index'] = new
      next(step for step in recovery['steps'] if step['step_index'] == old)['step_index'] = new
    else:
     media = next(step for step in recovery['steps'] if step['step_index'] == 17)['media'][0]
     earlier = e._native_body(f.records['mobile'][1]['response']['result'])['cid']
     media['before']['decoded_cid'] = media['after']['decoded_cid'] = earlier
    f.save_child('mobile')
    if fault == 'forged_observation':
     with self.assertRaises(ValueError):e.native_request_facts(f.root, f.report)
    else:
     facts = e.native_request_facts(f.root, f.report)
     self.assertEqual(facts['recovery_sequence']['views']['mobile'], [])


class SupplementalProjectionRowsTests(unittest.TestCase):
 """Presentation codec only: preserve every original typed scalar/payload."""
 def tree(self):
  values = [None, False, True, 0, -0.0, 1.0, 'literal supplemental_rows', {'supplemental_rows': [[0, 'native literal']], 'supplemental_descriptors': None}]
  descriptors = [{'phase': PHASES[i % 3], 'step_index': i, 'probe': {'kind': 'text', 'selector': '[data-authored-long-supplemental-selector="' + str(i) + '"]'}, 'observed': {'operator': 'equals', 'actual': copy.deepcopy(values[i]), 'expected': {'native_expected': [i, values[i]], 'supplemental_rows': 'opaque expected marker'}}} for i in range(8)]
  return {'schema': 'swissknife.visual-functional-review-input.v2', 'viewports': [{'name': name, 'supplemental_observations': copy.deepcopy(descriptors), 'backend_observations': [{'observed': {'actual': {'supplemental_rows': 'unrelated owner literal'}}}]} for name in ('desktop','mobile')], 'unrelated_native_payload': {'supplemental_descriptors': None, 'supplemental_rows_semantics': {'opaque': True}}}

 def test_supplemental_row_codec_preserves_exact_tree_and_opaque_payloads(self):
  tree = self.tree();before = e.encoded(tree)
  compact = e._factor_supplemental_rows(tree)
  self.assertIn('supplemental_descriptors', compact)
  self.assertIn('supplemental_rows_semantics', compact)
  self.assertLess(len(e.encoded(compact)), len(before))
  self.assertEqual(e.encoded(e._expand_supplemental_rows(compact)), before)
  self.assertEqual(e.encoded(tree), before, 'factor must not mutate original evidence')
  self.assertEqual(compact['viewports'][0]['supplemental_observations']['supplemental_rows'][7][1], tree['viewports'][0]['supplemental_observations'][7]['observed']['actual'])
  self.assertEqual(compact['unrelated_native_payload'], tree['unrelated_native_payload'])
  self.assertEqual(compact['viewports'][0]['backend_observations'], tree['viewports'][0]['backend_observations'])

 def test_supplemental_row_codec_integrates_with_all_existing_lossless_codecs(self):
  tree = self.tree();tree['retained_literal_padding'] = 'x' * 15000
  original = e.encoded(tree)
  factored = e._factor_projection(tree)
  self.assertEqual(e.encoded(e._expand_projection(factored)), original)
  self.assertLess(len(e.encoded(factored)), len(original))
  self.assertEqual(e.encoded(e._expand_supplemental_rows(self.tree())), e.encoded(self.tree()), 'unencoded historical tree remains exact')

 def test_supplemental_row_decoder_refuses_incomplete_ambiguous_or_forged_shapes(self):
  valid = e._factor_supplemental_rows(self.tree())
  for fault in ('missing_descriptors','missing_semantics','null_descriptors','null_semantics','descriptor_arity','descriptor_phase_type','row_arity','boolean_index','unknown_index','duplicate_descriptor','unused_descriptor','mixed_marker'):
   with self.subTest(fault=fault):
    value = copy.deepcopy(valid)
    slot = value['viewports'][0]['supplemental_observations']
    if fault == 'missing_descriptors':value.pop('supplemental_descriptors')
    elif fault == 'missing_semantics':value.pop('supplemental_rows_semantics')
    elif fault == 'null_descriptors':value['supplemental_descriptors'] = None
    elif fault == 'null_semantics':value['supplemental_rows_semantics'] = None
    elif fault == 'descriptor_arity':value['supplemental_descriptors'][0].append('forged extra field')
    elif fault == 'descriptor_phase_type':value['supplemental_descriptors'][0][0] = ['not a phase string']
    elif fault == 'row_arity':slot['supplemental_rows'][0].append('forged extra field')
    elif fault == 'boolean_index':slot['supplemental_rows'][0][0] = True
    elif fault == 'unknown_index':slot['supplemental_rows'][0][0] = 999
    elif fault == 'duplicate_descriptor':value['supplemental_descriptors'].append(copy.deepcopy(value['supplemental_descriptors'][0]))
    elif fault == 'unused_descriptor':
     descriptor = copy.deepcopy(value['supplemental_descriptors'][0]);descriptor[1] = 999;value['supplemental_descriptors'].append(descriptor)
    else:slot['forged_native_field'] = 'mixed encoded/native shape'
    with self.assertRaises(ValueError):e._expand_supplemental_rows(value)


class ObjectArrayProjectionRowsTests(unittest.TestCase):
 def tree(self):
  opaque = {'@': [0, 'native dict marker'], '@1:0': 'native tag key', 'actual_nested': ['@2:0', False]}
  return {'records': [{'alpha_long_field': i, 'beta_long_field': 'retained literal ' + str(i), 'gamma_long_field': {'first_native_key': i, 'second_native_key': False, 'third_native_key': None}, 'actual': copy.deepcopy(opaque), 'expected': ['@0', -0.0, True]} for i in range(30)], 'native_arrays': [['@0', 7], ['@1:0', 8], ['@2:0', 9], [True, 'a native boolean-first array']], '@': 'native root marker key'}

 def test_array_wrappers_roundtrip_and_legacy_dictionary_decode_remain_exact(self):
  tree = self.tree();original = e.encoded(tree)
  legacy = e._factor_projection_objects(tree)
  self.assertEqual(legacy['object_rows_semantics'], e._OBJECT_ROWS_SEMANTICS)
  self.assertEqual(e.encoded(e._expand_projection_objects(legacy)), original)
  compact = e._shorten_projection_object_rows(legacy)
  self.assertEqual(compact['object_rows_semantics'], e._OBJECT_ROWS_ARRAY_SEMANTICS)
  self.assertIsInstance(compact['records'][0], list)
  self.assertLess(len(e.encoded(compact)), len(e.encoded(legacy)))
  self.assertEqual(e.encoded(e._expand_projection_objects(compact)), original)
  self.assertEqual(e.encoded(tree), original)

 def test_array_prefix_avoids_all_native_strings_and_opaque_values(self):
  tree = self.tree();compact = e._shorten_projection_object_rows(e._factor_projection_objects(tree));prefix = compact['object_row_marker']
  def strings(value):
   if isinstance(value, str):return [value]
   if isinstance(value, dict):return list(value) + [v for child in value.values() for v in strings(child)]
   if isinstance(value, list):return [v for child in value for v in strings(child)]
   return []
  self.assertFalse(any(text.startswith(prefix) for text in strings(tree)))
  restored = e._expand_projection_objects(compact)
  self.assertEqual(restored['native_arrays'], tree['native_arrays'])
  for before, after in zip(tree['records'], restored['records']):
   self.assertEqual(e.encoded(before['actual']), e.encoded(after['actual']))
   self.assertEqual(e.encoded(before['expected']), e.encoded(after['expected']))

 def test_array_decoder_rejects_malformed_tag_arity_index_and_mixed_legacy(self):
  valid = e._shorten_projection_object_rows(e._factor_projection_objects(self.tree()))
  prefix = valid['object_row_marker']
  for fault in ('unknown_schema','noncanonical_index','boolean_spelling','empty_index','row_arity','mixed_legacy'):
   with self.subTest(fault=fault):
    value = copy.deepcopy(valid);row = value['records'][0]
    if fault == 'unknown_schema':row[0] = prefix + '999'
    elif fault == 'noncanonical_index':row[0] = prefix + '00'
    elif fault == 'boolean_spelling':row[0] = prefix + 'True'
    elif fault == 'empty_index':row[0] = prefix
    elif fault == 'row_arity':row.pop()
    else:
     index = int(row[0][len(prefix):]);value['records'][0] = {prefix: [index, *row[1:]]}
    with self.assertRaises(ValueError):e._expand_projection_objects(value)


class NativeProjectionMinimumChoiceTests(unittest.TestCase):
 """A fitting packet may still need lossless reduction for its full prompt."""
 def tree(self):
  value = ObjectArrayProjectionRowsTests().tree()
  value['viewports'] = []
  value['native_request_facts'] = {'schema': 'authored-native-facts-only', 'typed': [None, False, True, 0, -0.0, 1.0, '雪'], 'actual': {'@0': ['@1:0', False], 'retained_literal': 'not a protocol row'}, 'expected': ['@2:0', -0.0, True]}
  return value

 def test_native_private_choice_minimizes_even_when_public_packet_already_fits(self):
  tree = self.tree();original = e.encoded(tree)
  self.assertLess(len(original), 18000)
  self.assertIs(e._factor_projection(tree), tree, 'public fitting/legacy behavior stays unchanged')
  compact = e._smallest_projection_candidate(tree)
  self.assertLess(len(e.encoded(compact)), len(original))
  self.assertEqual(compact['object_rows_semantics'], e._OBJECT_ROWS_ARRAY_SEMANTICS)
  self.assertEqual(e.encoded(e._expand_projection(compact)), original)
  self.assertEqual(e.encoded(e._expand_projection(compact)['native_request_facts']), e.encoded(tree['native_request_facts']))
  self.assertEqual(e.encoded(tree), original, 'candidate choice must not mutate original typed evidence')

 def test_native_private_choice_never_reencodes_existing_tables_or_adds_larger_metadata(self):
  original = self.tree();compact = e._smallest_projection_candidate(original)
  self.assertIn('object_schemas', compact)
  self.assertEqual(e.encoded(e._smallest_projection_candidate(compact)), e.encoded(compact))
  small = {'viewports': [], 'native_request_facts': {'actual': [False, 0, -0.0, None]}}
  result = e._smallest_projection_candidate(small)
  self.assertEqual(e.encoded(result), e.encoded(small))
  self.assertNotIn('object_schemas', result, 'min choice may not enlarge small evidence with unused schemas')
