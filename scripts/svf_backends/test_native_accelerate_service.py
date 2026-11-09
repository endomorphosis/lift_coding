"""Authored unit transport fixtures only; actual CPU qualification is separate."""
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import native_accelerate_service as service

class NativeAccelerateTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  for name in [service.SDK_PATH,service.BACKEND_PATH,service.SERVICE_PATH]:
   p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('# authored unit fixture\n')
  self.runtime=self.root/service.NAMESPACE/'backends/test-native-accelerate'
  self.backend=service.NativeAccelerate(self.runtime,root=self.root)
  recovery=patch.object(self.backend.worker,'recover_async');recovery.start();self.addCleanup(recovery.stop)
 def authored_request(self,request_id,job,model,text,tokens,correlation):
  Path(job).mkdir(parents=True,exist_ok=True)
  return {'schema':'swissknife.native-accelerate-execution-result.v1','inference_executed':True,
   'source_sha256':self.backend.backend_sha,'manager_source_sha256':self.backend.sdk_sha,'model':model,
   'input':text,'offline':True,'external_provider_called':False,'warm_worker':{'request_id':request_id,'correlation_id':correlation,'worker_id':'authored-unit-only'},
   'model_cache_path':'/authored-fixture/cache','result':{'output':'Authored unit fixture only','generated_text':'fixture',
   'generated_token_count':1,'generated_token_ids':[42],'simulated':False,'echo_fallback':False}}
 def test_discovery_and_health_are_truthful_without_loading_or_running_model(self):
  with patch.object(self.backend,'cached',return_value=False):self.assertEqual(self.backend.health()['status'],'degraded')
  names=[t['name'] for t in service.dispatch(self.backend,{'jsonrpc':'2.0','id':1,'method':'tools/list'})['result']['tools']]
  self.assertEqual(names,['run_inference_job','list_models','hardware_profile','job_status','submit_task','get_task','detect_hardware',*service.OBSERVATION_TOOLS])
  self.assertFalse(self.backend.health()['engine_loaded'])
 def test_bad_missing_model_or_input_and_preview_never_launch_child(self):
  cases=[{'input':'x'},{'model':'gpt2'},{'model':'wrong','input':'x'}, {'model':'gpt2','input':'x','dry_run':True},
   {'model':'gpt2','input':'x','max_new_tokens':8},{'model':'gpt2','input':'x','max_new_tokens':True},
   {'model':'gpt2','input':'x','backend':'remote'},{'model':'gpt2','input':'x','task':'image-generation'}]
  with patch.object(self.backend.worker,'request') as child:
   for args in cases:
    with self.subTest(args=args),self.assertRaises(ValueError):self.backend.call('run_inference_job',args)
   child.assert_not_called()
 def test_unknown_parameters_and_conflicting_aliases_are_rejected(self):
  for args in [{'model':'gpt2','model_id':'other','input':'x'},{'model':'gpt2','input':'x','input_data':'different'}, {'model':'gpt2','input':'x','provider':'external'}]:
   with self.subTest(args=args),self.assertRaises(ValueError):self.backend.call('run_inference_job',args)
 def test_identical_model_and_input_aliases_are_accepted_without_fallback(self):
  with patch.object(self.backend.worker,'request',side_effect=self.authored_request) as child:
   result=self.backend.call('run_inference_job',{'model':'gpt2','model_id':'gpt2','input':'x','input_data':'x','max_length':64})
  self.assertEqual(result['content'][0]['json']['model_id'],'gpt2')
  self.assertEqual(child.call_args.args[2:5],('gpt2','x',4))
 def test_exact_aliases_launch_bounded_offline_child_and_retain_real_record(self):
  with patch.object(self.backend.worker,'request',side_effect=self.authored_request) as child:
   result=self.backend.call('run_inference_job',{'model_id':'gpt2','input_data':'x','max_length':64,'correlation_id':'unit-fixture'})
  payload=result['content'][0]['json'];self.assertEqual(payload['server_max_new_tokens'],4)
  self.assertEqual(payload['requested_max_length'],64);self.assertEqual(payload['effective_max_new_tokens'],4)
  self.assertEqual(self.backend.worker.request_timeout,30);self.assertEqual(child.call_args.args[4],4)
  self.assertEqual(payload['native_provenance'],result['receipt']['native_provenance'])
  read=self.backend.call('job_status',{'job_id':payload['job_id']})['content'][0]['json'];self.assertEqual(read['output'],payload['output'])
  self.assertTrue(read['read_from_execution_record'])
 def test_timeout_never_becomes_a_successful_execution_record(self):
  with patch.object(self.backend.worker,'request',side_effect=TimeoutError('authored worker deadline')):
   with self.assertRaises(TimeoutError):self.backend.call('run_inference_job',{'model':'gpt2','input':'x'})
  self.assertEqual(list(self.runtime.glob('jobs/*/mcp-result.json')),[])
 def test_busy_native_worker_does_not_launch_duplicate_generation(self):
  self.backend.slot.acquire()
  try:
   with patch.object(self.backend.worker,'request') as child:
    with self.assertRaisesRegex(RuntimeError,'busy'):self.backend.call('run_inference_job',{'model':'gpt2','input':'x'})
    child.assert_not_called()
  finally:self.backend.slot.release()
 def test_source_drift_rejects_before_child_execution(self):
  (self.root/service.SDK_PATH).write_text('changed source')
  self.assertEqual(self.backend.health()['status'],'degraded')
  self.assertFalse(self.backend.health()['source_contract_current'])
  with patch.object(self.backend.worker,'request') as child:
   with self.assertRaisesRegex(RuntimeError,'sources changed'):self.backend.call('run_inference_job',{'model':'gpt2','input':'x'})
   child.assert_not_called()
 def test_outside_and_symlinked_runtime_rejected_without_foreign_changes(self):
  with self.assertRaises(ValueError):service.NativeAccelerate(self.root/'outside',root=self.root)
  link=self.runtime.parent/'linked';link.symlink_to(self.runtime,target_is_directory=True)
  with self.assertRaises(ValueError):service.NativeAccelerate(link,root=self.root)
 def test_unknown_job_is_honestly_unavailable(self):
  with self.assertRaises(ValueError):self.backend.call('job_status',{'job_id':'00000000-0000-0000-0000-000000000000'})
 def test_submit_alias_invokes_genuine_execution_path_with_actual_context_and_no_queue_claim(self):
  args={'model_name':'gpt2','model_id':'gpt2','prompt':'bounded question','task_type':'inference',
   'payload':{'model_id':'gpt2','prompt':'bounded question','context':{'fact':'retained context'}}}
  with patch.object(self.backend.worker,'request',side_effect=self.authored_request) as child:
   result=service.dispatch(self.backend,{'jsonrpc':'2.0','id':7,'method':'tools/call','params':{'name':'submit_task','arguments':args}})['result']
  payload=result['content'][0]['json'];self.assertEqual(result['receipt']['tool'],'submit_task')
  self.assertEqual(result['receipt']['native_provenance']['sdk_method'],'execute_task')
  self.assertEqual(payload['execution_semantics'],'synchronous_completed_execution');self.assertFalse(payload['queue_used'])
  sent=child.call_args.args[3];self.assertIn('retained context',sent);self.assertIn('bounded question',sent)
  read=self.backend.call('get_task',{'task_id':payload['task_id']})
  self.assertEqual(read['receipt']['tool'],'get_task');self.assertTrue(read['content'][0]['json']['read_from_execution_record'])
 def test_prepare_output_dir_keeps_only_a_queue_file(self):
  import native_accelerate_backend as backend
  fresh=Path(self.tmp.name)/'fresh'
  backend.prepare_output_dir(fresh)
  self.assertTrue(fresh.is_dir())
  queued=Path(self.tmp.name)/'queued';queued.mkdir();(queued/'queue.json').write_text('{}')
  backend.prepare_output_dir(queued)
  dirty=Path(self.tmp.name)/'dirty';dirty.mkdir();(dirty/'execution.json').write_text('{}')
  with self.assertRaisesRegex(ValueError,'fresh directory'):backend.prepare_output_dir(dirty)
 def test_training_fixture_records_real_queue_transitions_and_checkpoint_cid(self):
  ordinary={'model':'gpt2','input':'x','fixture_scope':'svf-native-readiness'}
  with patch.object(self.backend.worker,'request',side_effect=self.authored_request):
   plain=self.backend.call('submit_task',ordinary)['content'][0]['json']
  self.assertFalse(plain['queue_used']);self.assertEqual(plain['execution_semantics'],'synchronous_completed_execution')
  self.assertNotIn('checkpoint',plain);self.assertNotIn('queue_observed',plain)
  prompt='dataset svf-training-isolated model gpt2'
  args={'model':'gpt2','model_id':'gpt2','input':prompt,'prompt':prompt,'task_type':'inference','max_new_tokens':4,
   'max_length':4,'backend':'cpu','task':'text-generation','fixture_scope':'svf-training-manager-g032','dry_run':False}
  with patch.object(self.backend.worker,'request',side_effect=self.authored_request) as child:
   result=self.backend.call('submit_task',args)
  payload=result['content'][0]['json']
  self.assertTrue(payload['queue_used']);self.assertEqual(payload['queue_observed'],'queued running completed')
  self.assertEqual(payload['execution_semantics'],'queued_running_completed')
  self.assertRegex(payload['checkpoint'],r'^b[a-z2-7]{58}$');self.assertTrue(payload['checkpoint'].startswith('bafkrei'))
  job=self.runtime/'jobs'/payload['job_id'];raw=(job/'checkpoint.json').read_bytes()
  self.assertEqual(payload['checkpoint'],service.raw_cid(raw))
  body=json.loads(raw);self.assertEqual(body['output'],'Authored unit fixture only');self.assertEqual(body['prompt'],prompt)
  self.assertNotIn('job_id',body);self.assertEqual((job/'checkpoint.json').stat().st_mode & 0o777,0o600)
  transitions=[{'order':1,'status':'queued'},{'order':2,'status':'running'},{'order':3,'status':'completed'}]
  self.assertEqual(payload['queue_transitions'],transitions)
  self.assertEqual(payload['persisted_selection'],{'dataset_id':'svf-training-isolated','model_id':'gpt2'})
  self.assertEqual(payload['owner_execution'],{'checkpoint':payload['checkpoint'],'dataset_id':'svf-training-isolated',
   'model_id':'gpt2','output':'Authored unit fixture only','queue_transitions':transitions,'status':'completed'})
  history=json.loads((self.runtime/'training-queue'/payload['job_id']/'queue.json').read_text())
  self.assertEqual([row['status'] for row in history['transitions']],['queued','running','completed'])
  self.assertEqual(history['transitions'][-1]['checkpoint'],payload['checkpoint'])
  self.assertEqual(json.loads((job/'queue.json').read_text()),history)
  child.assert_called_once()
  read=self.backend.call('get_task',{'task_id':payload['task_id'],'job_id':payload['job_id']})['content'][0]['json']
  self.assertEqual(read['checkpoint'],payload['checkpoint']);self.assertEqual(read['queue_observed'],'queued running completed')
  self.assertEqual(read['owner_execution'],payload['owner_execution']);self.assertEqual(read['persisted_selection'],payload['persisted_selection'])
  self.assertTrue(read['read_from_execution_record']);self.assertNotIn('bounded_recovery',payload)
  self.assertNotIn('owner_execution',plain);self.assertNotIn('persisted_selection',plain)
  recovered=dict(args,corrected_from='invalid')
  with patch.object(self.backend.worker,'request',side_effect=self.authored_request):
   second=self.backend.call('submit_task',recovered)['content'][0]['json']
  self.assertEqual(second['bounded_recovery'],{'corrected_from':'invalid','dataset_id':'svf-training-isolated','model_id':'gpt2','output_limit':4,'status':'completed'})
  self.assertEqual(second['queue_observed'],'queued running completed')
 def test_submit_conflicting_aliases_training_and_oversized_context_fail_without_child(self):
  cases=[{'model_name':'other','model_id':'gpt2','prompt':'x'},
   {'model_name':'gpt2','prompt':'x','payload':{'model_id':'other','prompt':'x'}},
   {'model_name':'gpt2','prompt':'x','task_type':'training'},
   {'model':'gpt2','input':'dataset svf-training-isolated model gpt2','fixture_scope':'svf-native-readiness','corrected_from':'invalid'},
   {'model_name':'gpt2','prompt':'x','payload':{'context':'x'*513}}]
  with patch.object(self.backend.worker,'request') as child:
   for args in cases:
    with self.subTest(args=args),self.assertRaises(ValueError):self.backend.call('submit_task',args)
   child.assert_not_called()
 def test_detect_alias_reports_actual_cpu_placement_and_requested_tool(self):
  value=self.backend.call('detect_hardware',{})
  self.assertEqual(value['receipt']['tool'],'detect_hardware');self.assertEqual(value['content'][0]['json']['device'],'cpu')
  self.assertEqual(value['content'][0]['json']['cpu']['logical_cpu_count'],service.os.cpu_count())
 def test_class_specific_and_quarantined_tools_remain_unsupported(self):
  for name in ['WorkflowCoordinator.submit_task','HardwareDetector.get_available_hardware']:
   with self.subTest(name=name),self.assertRaisesRegex(ValueError,'Unsupported'):self.backend.call(name,{})
 def test_missing_real_observation_sources_remain_unavailable(self):
  for name in service.OBSERVATION_TOOLS:
   with self.subTest(name=name),self.assertRaisesRegex(RuntimeError,'sources are unavailable'):self.backend.call(name,{})
 def test_service_source_is_pinned_and_drift_degrades_before_call(self):
  pinned=self.backend.service_sha
  self.assertEqual(self.backend.health()['service_source_sha256'],pinned)
  (self.root/service.SERVICE_PATH).write_text('new service source')
  self.assertEqual(self.backend.health()['status'],'degraded')
  self.assertEqual(self.backend.health()['service_source_sha256'],pinned)
  with self.assertRaisesRegex(RuntimeError,'sources changed'):self.backend.call('detect_hardware',{})
 def test_only_explicitly_supervised_source_drift_exits_for_owned_restart(self):
  server=service.Server.__new__(service.Server);server.backend=self.backend
  with patch.dict(service.os.environ,{'SVF_RESTART_ON_SOURCE_DRIFT':'1'}),patch.object(service.os,'_exit') as leave:
   server.service_actions();leave.assert_not_called()
   (self.root/service.SERVICE_PATH).write_text('new service source')
   server.service_actions();leave.assert_called_once_with(75)
  with patch.dict(service.os.environ,{'SVF_RESTART_ON_SOURCE_DRIFT':'0'}),patch.object(service.os,'_exit') as leave:
   server.service_actions();leave.assert_not_called()

if __name__=='__main__':unittest.main()
