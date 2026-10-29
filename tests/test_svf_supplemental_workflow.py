"""RAM-only real worker/public-parser integration, no browser/provider/acceptance."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

REPO=Path(os.environ.get('SVF_FOUNDATION_REPOSITORY_ROOT',Path(__file__).resolve().parents[1]))
SCRIPTS=Path(os.environ.get('SVF_VPC_CANDIDATE_SCRIPTS',REPO/'scripts'))
sys.path.insert(0,str(REPO/'scripts'));sys.path.insert(0,str(SCRIPTS))
import swissknife_visual_functional_worker as worker
import swissknife_visual_functional_llm as llm
fixture_path=Path(os.environ.get('SVF_SCENARIO_PREAPPLY_TEST',REPO/'tests/test_svf_scenario_preapply.py'))
spec=importlib.util.spec_from_file_location('supplemental_preapply_fixture',fixture_path)
f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)

class BeforeRunner(BaseException):pass
class SupplementalWorkflowTests(unittest.TestCase):
 def setUp(self):
  self.f=f.ScenarioPreapplyTests('runTest');self.f.setUp();self.addCleanup(self.f.doCleanups)
  candidate=os.environ.get('SVF_SUPPLEMENTAL_RUNNER')
  if candidate:(self.f.root/'swissknife/scripts/run-visual-functional-workflow.mjs').write_bytes(Path(candidate).read_bytes())
 def value(self):
  value=f.scenario()
  for phase in ('persist_reopen','failure_recovery'):
   value['phases'][phase].append({'op':'assert','probe':{'kind':'text','selector':'#packet-identity'},'operator':'equals','expected':'Replay packet trail-note.'})
  return value
 def workflow(self,value,kind,accepted):
  (self.f.root/f.SCENARIO).write_bytes(f.encoded(value));task={**self.f.task,'kind':kind}
  with patch.object(worker,'ROOT',self.f.root),patch.object(worker,'assert_no_campaign_hold'),patch.object(worker,'assert_storage_available'),patch.object(worker,'run',side_effect=BeforeRunner)as run:
   if accepted:
    with self.assertRaises(BeforeRunner):worker.workflow(self.f.profile,task,self.f.root/self.f.profile['runtimeRoot']/'tasks'/task['task_id']/'verification')
    self.assertIn('--independent-viewports',run.call_args.args[0]);self.assertEqual(run.call_count,1)
   else:
    with self.assertRaisesRegex(ValueError,'INVALID_SCENARIO'):worker.workflow(self.f.profile,task,self.f.root/self.f.profile['runtimeRoot']/'tasks'/task['task_id']/'verification')
    run.assert_not_called()
 def test_independent_V2_keeps_original_runner_and_declared_extra_steps(self):
  for kind in ('verify','final-app-verify'):
   with self.subTest(kind=kind):self.workflow(self.value(),kind,True)
 def test_supplemental_read_does_not_relax_named_PNG_ordering(self):
  name='swissknife/test/e2e/functional-workflows/neural-photoshop.json'
  source=(REPO/name).read_bytes();value=json.loads(source)
  extra={'op':'assert','probe':{'kind':'text','selector':'#readonly-extra'},'operator':'equals','expected':'native read'}
  value['phases']['primary_result'].append(copy.deepcopy(extra))
  target=self.f.root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(source)
  (self.f.root/f.CONTRACT).write_bytes((REPO/f.CONTRACT).read_bytes())
  task={**self.f.task,'kind':'verify','app_id':'neural-photoshop','edit_paths':[name]}
  worker.validate_proposed_scenarios(self.f.root,self.f.profile,task,{name:f.encoded(value)})
  target.write_bytes(f.encoded(value))
  with patch.object(worker,'ROOT',self.f.root),patch.object(worker,'assert_no_campaign_hold'),patch.object(worker,'assert_storage_available'),patch.object(worker,'run',side_effect=BeforeRunner)as run:
   with self.assertRaises(BeforeRunner):worker.workflow(self.f.profile,task,self.f.root/self.f.profile['runtimeRoot']/'tasks'/task['task_id']/'verification')
   self.assertIn('--independent-viewports',run.call_args.args[0])
  value=json.loads(source);value['phases']['failure_recovery'].append(extra)
  with self.assertRaises(worker.ScenarioProposalError):worker.validate_proposed_scenarios(self.f.root,self.f.profile,task,{name:f.encoded(value)})
  target.write_bytes(f.encoded(value))
  with patch.object(worker,'ROOT',self.f.root),patch.object(worker,'assert_no_campaign_hold'),patch.object(worker,'assert_storage_available'),patch.object(worker,'run')as run:
   with self.assertRaisesRegex(ValueError,'INVALID_SCENARIO'):worker.workflow(self.f.profile,task,self.f.root/self.f.profile['runtimeRoot']/'tasks'/task['task_id']/'verification')
   run.assert_not_called()
 def test_fresh_V1_refuses_extras_before_runner_or_browser(self):
  self.workflow(self.value(),'repair',False)
 def test_worker_refuses_ninth_extra_nonDOM_temporal_nonScalar_or_retained_refs(self):
  cases=[];value=self.value();value['phases']['primary_result'] += [copy.deepcopy(value['phases']['persist_reopen'][-1])for _ in range(7)];cases.append(value)
  for kind in ('backend_result','image_state','media_state','dom_property','checked','count'):
   value=self.value();value['phases']['persist_reopen'][-1]['probe']['kind']=kind;cases.append(value)
  value=self.value();value['phases']['persist_reopen'][-1]['probe']['temporal_ms']=100;cases.append(value)
  value=self.value();value['phases']['persist_reopen'][-1]['expected']={'invented':'object'};cases.append(value)
  value=self.value();value['phases']['persist_reopen'][-1]['retained_from']={'primary_result':0,'persist_reopen':1};cases.append(value)
  for index,value in enumerate(cases):
   with self.subTest(index=index):self.workflow(value,'verify',False)
 def test_real_R22_preapply_accepts_two_extra_DOM_reads_atomically(self):
  value=self.value();before=self.f.ledger.read_bytes()
  result=worker.apply_task_edits(self.f.root,self.f.profile,self.f.task,self.f.edits(value),self.f.task['edit_paths'],lease_check=lambda:None)
  self.assertEqual(len(result['applied']),3);self.assertEqual(json.loads((self.f.root/f.SCENARIO).read_bytes()),value)
  self.assertEqual(self.f.ledger.read_bytes(),before)
 def test_real_public_parser_still_refuses_missing_duplicate_unknown_required_roles(self):
  cases=[];value=self.value();value['phases']['persist_reopen'][1].pop('requirement_id');cases.append(value)
  value=self.value();value['phases']['persist_reopen'].append(copy.deepcopy(value['phases']['persist_reopen'][1]));cases.append(value)
  value=self.value();value['phases']['persist_reopen'][1]['requirement_id']='invented-role';cases.append(value)
  value=self.value();value['phases']['failure_recovery'].pop(0);cases.append(value)
  for index,value in enumerate(cases):
   with self.subTest(index=index),patch.object(llm,'_stage_source',wraps=llm._stage_source)as staging:
    with self.assertRaises(worker.ScenarioProposalError):worker.apply_task_edits(self.f.root,self.f.profile,self.f.task,self.f.edits(value),self.f.task['edit_paths'],lease_check=lambda:None)
    staging.assert_not_called();self.f.pristine()
 def test_identity_keys_must_be_physically_absent_and_no_anonymous_retention_authority(self):
  for key,value in [('requirement_id',None),('requirement_id',''),('checkpoint_id',None),('checkpoint_id',''),('checkpoint_id','invented'),('retained_from',{})]:
   proposal=self.value();proposal['phases']['persist_reopen'][-1][key]=value
   with self.subTest(key=key,value=value),patch.object(llm,'_stage_source',wraps=llm._stage_source)as staging:
    with self.assertRaises(worker.ScenarioProposalError):worker.apply_task_edits(self.f.root,self.f.profile,self.f.task,self.f.edits(proposal),self.f.task['edit_paths'],lease_check=lambda:None)
    staging.assert_not_called();self.f.pristine()
 def legacy_fixture(self):
  spec=importlib.util.spec_from_file_location('legacy_supplemental_fixture',REPO/'tests/test_swissknife_visual_functional_worker.py')
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  self.assertIs(module.worker,worker)
  case=module.WorkerTests('runTest');case.setUp();self.addCleanup(case.doCleanups);return case
 def test_V1_consumer_refuses_nonempty_or_malformed_supplemental_wire(self):
  case=self.legacy_fixture()
  for value in ([{'phase':'persist_reopen','step_index':2}],None,{},True):
   case.data['supplemental_observations']=value
   with self.subTest(value=value),self.assertRaisesRegex(ValueError,'legacy V1 cannot consume supplemental'):case.validate()
 def test_V1_consumer_refuses_anonymous_canonical_source_even_without_wire(self):
  case=self.legacy_fixture();source=case.root/'swissknife/test/e2e/functional-workflows/demo.json';source.parent.mkdir(parents=True)
  source.write_text(json.dumps({'phases':{'persist_reopen':[{'op':'assert','probe':{'kind':'text','selector':'#packet'},'operator':'equals','expected':'native'}]}}))
  with self.assertRaisesRegex(ValueError,'legacy V1 cannot consume a supplemental scenario'):case.validate()
 def test_historical_V1_absent_source_and_missing_or_empty_wire_remain_valid(self):
  case=self.legacy_fixture();case.validate();case.data['supplemental_observations']=[];case.validate()
  source=case.root/'swissknife/test/e2e/functional-workflows/demo.json';source.parent.mkdir(parents=True)
  source.write_text(json.dumps({'schema':'historical no-extra fixture','phases':{}}));case.validate()
 def test_scalar_descriptor_bounds_refuse_without_source_or_ledger_write(self):
  cases=[];value=self.value();value['phases']['persist_reopen'][-1]['expected']='x'*511;cases.append(value)
  value=self.value();value['phases']['persist_reopen'][-1]['expected']=['not','scalar'];cases.append(value)
  value=self.value();value['phases']['persist_reopen'][-1]['probe']['selector']='#'+'long-'*70
  value['phases']['persist_reopen'] += [copy.deepcopy(value['phases']['persist_reopen'][-1])for _ in range(5)];cases.append(value)
  for index,value in enumerate(cases):
   with self.subTest(index=index),patch.object(llm,'_stage_source',wraps=llm._stage_source)as staging:
    with self.assertRaises(worker.ScenarioProposalError):worker.apply_task_edits(self.f.root,self.f.profile,self.f.task,self.f.edits(value),self.f.task['edit_paths'],lease_check=lambda:None)
    staging.assert_not_called();self.f.pristine()

if __name__=='__main__':unittest.main()
