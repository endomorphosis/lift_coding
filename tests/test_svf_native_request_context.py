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
