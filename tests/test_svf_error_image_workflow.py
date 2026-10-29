"""Real worker admission; mocked command/browser boundary, no owner/model calls."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(os.environ.get('SVF_FOUNDATION_REPOSITORY_ROOT',Path(__file__).resolve().parents[1]))
SCRIPTS=Path(os.environ.get('SVF_VPC_CANDIDATE_SCRIPTS',ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(SCRIPTS))
import swissknife_visual_functional_worker as worker
SCENARIO=Path(os.environ.get('SVF_NEURAL_SCENARIO_CANDIDATE',ROOT/'swissknife/test/e2e/functional-workflows/neural-photoshop.json'))
class ReachedRunner(BaseException):pass
class ErrorImageWorkerAdmissionTests(unittest.TestCase):
 def setUp(self):
  self.scenario=json.loads(SCENARIO.read_bytes())
  self.scenario["phases"]["failure_recovery"]=[step for step in self.scenario["phases"]["failure_recovery"] if step.get("checkpoint_id")!="recovery_image_retained"]
 def run_case(self,scenario,accepted):
  with tempfile.TemporaryDirectory(dir='/dev/shm')as tmp:
   root=Path(tmp);p=root/'swissknife/test/e2e/functional-workflows/neural-photoshop.json';p.parent.mkdir(parents=True);p.write_text(json.dumps(scenario))
   runner=root/'swissknife/scripts/run-visual-functional-workflow.mjs';runner.parent.mkdir(parents=True);runner.write_text('// authored command boundary only\n')
   profile={'runtimeRoot':'data/agent_supervisor/swissknife_visual_functional','appContractPath':'contracts.json'};task={'task_id':'SVF-443','kind':'verify','app_id':'neural-photoshop'}
   with patch.object(worker,'ROOT',root),patch.object(worker,'assert_no_campaign_hold'),patch.object(worker,'assert_storage_available'),patch.object(worker,'run',side_effect=ReachedRunner)as call:
    if accepted:
     with self.assertRaises(ReachedRunner):worker.workflow(profile,task,root/'data/agent_supervisor/swissknife_visual_functional/tasks/SVF-443/verification')
     self.assertEqual(call.call_count,1);self.assertIn('--independent-viewports',call.call_args.args[0]);self.assertEqual(call.call_args.args[0][0:2],['node','swissknife/scripts/run-visual-functional-workflow.mjs'])
    else:
     with self.assertRaisesRegex(ValueError,'INVALID_SCENARIO'):worker.workflow(profile,task,root/'data/agent_supervisor/swissknife_visual_functional/tasks/SVF-443/verification')
     call.assert_not_called()
 def test_declared_retained_image_reaches_actual_original_runner_boundary(self):self.run_case(self.scenario,True)
 def test_legacy_single_checkpoint_admission_unchanged(self):
  value=copy.deepcopy(self.scenario);value['phases']['failure_recovery'].pop(5);self.run_case(value,True)
 def test_invalid_image_identity_and_order_refuse_before_browser(self):
  def mutation(index):
   s=copy.deepcopy(self.scenario);steps=s['phases']['failure_recovery']
   if index==0:steps[5]['checkpoint_id']='unknown'
   if index==1:steps.append(copy.deepcopy(steps[5]))
   if index==2:steps.insert(0,steps.pop(5))
   if index==3:steps.insert(7,steps.pop(5))
   if index==4:steps[5]['probe']['kind']='text'
   if index==5:steps[5]['retained_from']['primary_result']=0
   if index==6:steps[5]['retained_from']['persist_reopen']=True
   if index==7:steps[5]['retained_from']['unexpected']=0
   if index==8:del steps[5]['retained_from']
   if index==9:steps.insert(5,copy.deepcopy(steps[4]))
   if index==10:steps[5]['requirement_id']='failure_recovery'
   return s
  for index in range(11):
   with self.subTest(index=index):self.run_case(mutation(index),False)

class RecoveryImageWorkerAdmissionTests(unittest.TestCase):
 run_case=ErrorImageWorkerAdmissionTests.run_case
 def setUp(self):self.scenario=json.loads(SCENARIO.read_bytes())
 def test_canonical_post_retry_image_reaches_real_original_runner_boundary(self):
  self.assertEqual(self.scenario['phases']['failure_recovery'][-1]['checkpoint_id'],'recovery_image_retained')
  self.run_case(self.scenario,True)
 def test_post_only_and_historical_checkpoint_shapes_reach_runner(self):
  for omit in ({'error_image_retained'},{'recovery_image_retained'},{'error_image_retained','recovery_image_retained'}):
   value=copy.deepcopy(self.scenario);value['phases']['failure_recovery']=[step for step in value['phases']['failure_recovery'] if step.get('checkpoint_id') not in omit]
   with self.subTest(omit=omit):self.run_case(value,True)
 def test_invalid_post_image_role_order_references_and_retry_refuse_before_browser(self):
  def mutation(index):
   s=copy.deepcopy(self.scenario);steps=s['phases']['failure_recovery'];post=steps[-1]
   if index==0:post['checkpoint_id']='unknown'
   if index==1:steps.append(copy.deepcopy(post))
   if index==2:steps.insert(11,steps.pop())
   if index==3:steps.insert(5,steps.pop())
   if index==4:post['probe']['kind']='text'
   if index==5:post['probe']['temporal_ms']=100
   if index==6:post['retained_from']['primary_result']=0
   if index==7:post['retained_from']['persist_reopen']=True
   if index==8:post['retained_from']['extra']=0
   if index==9:del post['retained_from']
   if index==10:steps.append({'op':'click','selector':'#new-owner-action'})
   if index==11:steps.insert(12,{'op':'click','selector':'#changed-image'})
   if index==12:post['requirement_id']='failure_recovery'
   if index==13:del steps[6:9]
   if index==14:s['phases']['primary_result'].append(steps.pop())
   if index==15:del steps[11]['requirement_id']
   return s
  for index in range(16):
   with self.subTest(index=index):self.run_case(mutation(index),False)

if __name__=='__main__':unittest.main()

