"""Offline whole-batch scenario preflight; authored models never grant acceptance."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

REPO=Path(os.environ.get('SVF_FOUNDATION_REPOSITORY_ROOT',Path(__file__).resolve().parents[1]))
SCRIPTS=Path(os.environ.get('SVF_VPC_CANDIDATE_SCRIPTS',REPO/'scripts'))
sys.path.insert(0,str(REPO/'scripts'));sys.path.insert(0,str(SCRIPTS))
import swissknife_visual_functional_worker as worker
import swissknife_visual_functional_llm as llm
import swissknife_visual_functional_recovery as recovery

SCENARIO='swissknife/test/e2e/functional-workflows/authoring-unit.json'
MAIN='swissknife/web/js/main-simple.js'
NEW='swissknife/web/js/new-parent/new-app.js'
CONTRACT='swissknife/config/visual-functional-app-contracts.json'
def digest(value):return hashlib.sha256(value).hexdigest()
def encoded(value):return (json.dumps(value,indent=2)+'\n').encode()
def scenario():
 return {'schema':'swissknife.visual-functional-scenario.v1','app_id':'authoring-unit','fixture_scope':'svf-authoring-unit','backend_bindings':[],
  'phases':{'primary_result':[{'op':'assert','requirement_id':'result_1','probe':{'kind':'text','selector':'#result'},'operator':'equals','expected':'ready'}],
   'persist_reopen':[{'op':'reopen_app'},{'op':'assert','requirement_id':'persist_reopen','probe':{'kind':'text','selector':'#result'},'operator':'equals','expected':'ready'}],
   'failure_recovery':[{'op':'assert','checkpoint_id':'error_observed','probe':{'kind':'text','selector':'#error'},'operator':'equals','expected':'failed'},
    {'op':'click','selector':'#retry'},{'op':'assert','requirement_id':'failure_recovery','probe':{'kind':'text','selector':'#result'},'operator':'equals','expected':'ready'}]}}
def contract():return {'apps':[{'app_id':'authoring-unit','disposition':'browser_local','backend_roles':[],
 'primary_workflow':{'expected_results':['Actual result'],'persist_reopen':'Actual restored result','error':'Real error','recovery':'Actual retry'}}]}

class ScenarioPreapplyTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir='/dev/shm',prefix='svf-scenario-preapply-');self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.install(self.root)
  self.profile={'runtimeRoot':'data/agent_supervisor/swissknife_visual_functional','appContractPath':CONTRACT,
   'humanPlanPath':'plan.md','taskSpecPath':'tasks.json'}
  self.task={'task_id':'SVF-777','kind':'repair','app_id':'authoring-unit','edit_paths':[MAIN,NEW,SCENARIO],
   'checks':[['node','authored-protected-check.mjs']]}
  self.ledger=self.root/self.profile['runtimeRoot']/'owned-source-hashes.json';self.ledger.parent.mkdir(parents=True)
  self.ledger.write_bytes(encoded({MAIN:digest((self.root/MAIN).read_bytes()),SCENARIO:digest((self.root/SCENARIO).read_bytes())}))
  self.ledger_before=self.ledger.read_bytes();self.ledger_inode=self.ledger.stat().st_ino
 def install(self,root):
  for name in ['swissknife/scripts/run-visual-functional-workflow.mjs','swissknife/scripts/capture-visual-functional-baseline.mjs','swissknife/scripts/lib/pick-free-port.mjs']:
   p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((REPO/name).read_bytes())
  for name,raw in [(CONTRACT,encoded(contract())),(SCENARIO,encoded(scenario())),(MAIN,b'// unchanged shared application\n'),('plan.md',b'authored plan'),('tasks.json',b'{}')]:
   p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
 def edits(self,value):
  return [{'path':MAIN,'before_sha256':digest((self.root/MAIN).read_bytes()),'old':'unchanged','new':'changed'},
   {'path':NEW,'before_sha256':None,'old':'','new':'// authored new source\n'},
   {'path':SCENARIO,'before_sha256':digest((self.root/SCENARIO).read_bytes()),'old':(self.root/SCENARIO).read_text(),'new':encoded(value).decode()}]
 def duplicate(self):
  s=scenario();s['phases']['persist_reopen'].append(copy.deepcopy(s['phases']['persist_reopen'][-1]));s['phases']['failure_recovery'].append(copy.deepcopy(s['phases']['failure_recovery'][-1]));return s
 def pristine(self):
  self.assertEqual((self.root/MAIN).read_bytes(),b'// unchanged shared application\n');self.assertEqual((self.root/SCENARIO).read_bytes(),encoded(scenario()))
  self.assertFalse((self.root/NEW).parent.exists());self.assertEqual(self.ledger.read_bytes(),self.ledger_before);self.assertEqual(self.ledger.stat().st_ino,self.ledger_inode)
  self.assertEqual(list(self.root.rglob('.svf-edit-*')),[]);self.assertEqual(list(self.root.rglob('.svf-dir-*')),[])
 def test_actual_pure_node_rejects_duplicate_whole_batch_before_staging_parent_and_ledger(self):
  with patch.object(llm,'_stage_source',wraps=llm._stage_source)as stage:
   with self.assertRaises(worker.ScenarioProposalError)as caught:worker.apply_task_edits(self.root,self.profile,self.task,self.edits(self.duplicate()),self.task['edit_paths'],lease_check=lambda:None)
   stage.assert_not_called()
  issues=caught.exception.diagnostic['issues'];self.assertTrue(any(x['id']=='persist_reopen' and x['step_index']==2 for x in issues));self.assertTrue(any(x['id']=='failure_recovery' and x['step_index']==3 for x in issues))
  self.pristine()
 def test_bad_reference_json_identity_and_unknown_app_refuse_without_writes(self):
  cases=[];s=scenario();s['phases']['failure_recovery'].append({'op':'assert','checkpoint_id':'recovery_image_retained','retained_from':{'primary_result':0,'persist_reopen':1},'probe':{'kind':'image_state','selector':'#image','pointer':'/natural_width'},'operator':'equals','expected':64});cases.append(s)
  s=scenario();s['app_id']='different-app';cases.append(s)
  for value in cases:
   with self.subTest(value=value):
    with self.assertRaises(worker.ScenarioProposalError):worker.apply_task_edits(self.root,self.profile,self.task,self.edits(value),self.task['edit_paths'],lease_check=lambda:None)
    self.pristine()
  edits=self.edits(scenario());edits[-1]['new']='{"schema":';
  with self.assertRaisesRegex(worker.ScenarioProposalError,'INVALID_SCENARIO_JSON'):worker.apply_task_edits(self.root,self.profile,self.task,edits,self.task['edit_paths'],lease_check=lambda:None)
  self.pristine()
 def test_valid_whole_batch_proceeds_through_real_atomic_applier(self):
  value=scenario();value['description']='Authored structurally valid proposal'
  result=worker.apply_task_edits(self.root,self.profile,self.task,self.edits(value),self.task['edit_paths'],lease_check=lambda:None)
  self.assertEqual(len(result['applied']),3);self.assertIn('changed',(self.root/MAIN).read_text());self.assertTrue((self.root/NEW).is_file());self.assertEqual(json.loads((self.root/SCENARIO).read_text()),value)
  self.assertEqual(self.ledger.read_bytes(),self.ledger_before)
 def test_real_import_guard_has_no_runner_argv_and_denies_network_child_and_writes(self):
  runner=self.root/'swissknife/scripts/run-visual-functional-workflow.mjs'
  runner.write_text(runner.read_text()+'''
if(process.argv[1]!==undefined)throw new Error('pure scenario import received a CLI entry argument');
const guardHttp=await import('node:http');
for(const probe of [()=>guardHttp.createServer(),()=>spawn(null),()=>fs.writeFileSync('guard-should-not-write','no')]){
 let denied=false;try{probe();}catch(error){denied=String(error.message).includes('scenario preflight forbids');}
 if(!denied)throw new Error('pure scenario import guard was not enforced');
}
''')
  worker.validate_proposed_scenarios(self.root,self.profile,self.task,{SCENARIO:encoded(scenario())})
  self.assertFalse((self.root/'guard-should-not-write').exists());self.pristine()
 def test_already_after_invalid_scenario_blocks_pending_shared_source(self):
  (self.root/SCENARIO).write_bytes(encoded(self.duplicate()));edits=[self.edits(scenario())[0]]
  with patch.object(llm,'_stage_source',wraps=llm._stage_source)as stage:
   with self.assertRaises(worker.ScenarioProposalError):worker.apply_task_edits(self.root,self.profile,self.task,edits,[MAIN],lease_check=lambda:None)
   stage.assert_not_called()
  self.assertIn('unchanged',(self.root/MAIN).read_text());self.assertEqual(self.ledger.read_bytes(),self.ledger_before);self.assertFalse((self.root/NEW).parent.exists())
 def test_unchanged_scenario_drift_during_lease_check_blocks_pending_source(self):
  checks=0
  def foreign():
   nonlocal checks
   checks+=1
   if checks==2:(self.root/SCENARIO).write_bytes(encoded(self.duplicate()))
  edits=[self.edits(scenario())[0]]
  with patch.object(llm,'_stage_source',wraps=llm._stage_source)as stage:
   with self.assertRaisesRegex(ValueError,'scenario contract or validator changed'):worker.apply_task_edits(self.root,self.profile,self.task,edits,[MAIN],lease_check=foreign)
   stage.assert_not_called()
  self.assertIn('unchanged',(self.root/MAIN).read_text());self.assertEqual(self.ledger.read_bytes(),self.ledger_before)
 def test_proposed_contract_cannot_authorize_weaker_requirements(self):
  edits=self.edits(self.duplicate());edits.append({'path':CONTRACT,'before_sha256':digest((self.root/CONTRACT).read_bytes()),'old':(self.root/CONTRACT).read_text(),'new':encoded({'apps':[]}).decode()})
  with self.assertRaisesRegex(worker.ScenarioProposalError,'APPROVED_CONTRACT_CHANGED'):worker.apply_task_edits(self.root,self.profile,self.task,edits,[*self.task['edit_paths'],CONTRACT],lease_check=lambda:None)
  self.pristine();self.assertEqual(json.loads((self.root/CONTRACT).read_text()),contract())
 def test_real_worker_ordinary_and_verify_routes_reject_before_source_or_ledger_and_retain_feedback(self):
  for kind in ['repair','verify']:
   task={**self.task,'kind':kind};proposal={'response':{'edits':self.edits(self.duplicate())}}
   with patch.object(worker,'ROOT',self.root),patch.object(worker,'ensure_lease'),patch.object(worker,'dirty_paths',return_value=set()),patch.object(worker,'assert_storage_available'),patch.object(worker,'assert_no_campaign_hold'),patch.object(worker,'qualified_recovery',return_value=None),patch.object(worker,'model',return_value=proposal),patch.object(worker,'workflow',side_effect=RuntimeError('authored producer failure')),patch.object(worker,'remember_execution_failure'),patch('swissknife_visual_functional_review_recheck.assert_recheck_allowed'),patch.object(llm,'_stage_source',wraps=llm._stage_source)as stage:
    with self.assertRaises(worker.ScenarioProposalError):worker.execute('profile.json',self.profile,{},task)
    stage.assert_not_called();feedback=worker.load_repair_feedback(self.profile,task);self.assertEqual(feedback['error']['code'],'scenario_prevalidation_failed');self.assertTrue(feedback['error']['issues'])
   self.pristine()
 def test_real_worker_scoped_callback_cannot_bypass_final_overlay_preflight(self):
  task={**self.task,'kind':'scoped-remediation'}
  def child(root,profile_path,profile,spec,actual,**callbacks):return callbacks['apply_edits'](root,self.edits(self.duplicate()),actual['edit_paths'],lease_check=lambda:None)
  with patch.object(worker,'ROOT',self.root),patch.object(worker,'ensure_lease'),patch.object(worker,'assert_storage_available'),patch.object(worker,'assert_no_campaign_hold'),patch('swissknife_visual_functional_phase_remediation.execute_child',side_effect=child),patch.object(llm,'_stage_source',wraps=llm._stage_source)as stage:
   with self.assertRaises(worker.ScenarioProposalError):worker.execute('profile.json',self.profile,{},task)
   stage.assert_not_called()
  self.pristine()
 def test_node_timeout_malformed_output_and_current_authority_drift_refuse(self):
  for fake in [subprocess.TimeoutExpired(['node'],15),subprocess.CompletedProcess(['node'],0,'{}','')]:
   with patch.object(worker.subprocess,'run',side_effect=fake if isinstance(fake,Exception)else None,return_value=fake):
    with self.assertRaises(worker.ScenarioProposalError):worker.apply_task_edits(self.root,self.profile,self.task,self.edits(scenario()),self.task['edit_paths'],lease_check=lambda:None)
   self.pristine()
  real=subprocess.run
  def changed(*args,**kw):
   result=real(*args,**kw);(self.root/CONTRACT).write_bytes(encoded({**contract(),'foreign':True}));return result
  with patch.object(worker.subprocess,'run',side_effect=changed):
   with self.assertRaisesRegex(worker.ScenarioProposalError,'SCENARIO_AUTHORITY_CHANGED'):worker.apply_task_edits(self.root,self.profile,self.task,self.edits(scenario()),self.task['edit_paths'],lease_check=lambda:None)
  self.pristine();self.assertTrue(json.loads((self.root/CONTRACT).read_text())['foreign'])
 def test_direct_semantic_recovery_uses_same_preflight_and_preserves_admission_spend(self):
  spec=importlib.util.spec_from_file_location('authored_recovery_base',REPO/'tests/test_swissknife_visual_functional_recovery.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  fixture=module.RecoveryTests('runTest');fixture.setUp();self.addCleanup(fixture.doCleanups);self.install(fixture.root)
  fixture.profile['appContractPath']=CONTRACT;fixture.task['edit_paths'].append(SCENARIO);fixture.packet['source_before'][SCENARIO]=digest((fixture.root/SCENARIO).read_bytes());fixture.save_packet()
  fixture.edits=lambda:[{'path':'app.py','before_sha256':digest(fixture.target.read_bytes()),'old':'before','new':'after'},
   {'path':SCENARIO,'before_sha256':digest((fixture.root/SCENARIO).read_bytes()),'old':(fixture.root/SCENARIO).read_text(),'new':encoded(self.duplicate()).decode()}]
  before=fixture.journal_path.read_bytes()
  with patch.object(llm,'_stage_source',wraps=llm._stage_source)as stage:
   with self.assertRaises(worker.ScenarioProposalError):fixture.run_recovery()
   stage.assert_not_called()
  self.assertIn('before',fixture.target.read_text());self.assertEqual(fixture.journal_path.read_bytes(),before);self.assertEqual(fixture.owned,[])

if __name__=='__main__':unittest.main()
