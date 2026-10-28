"""Typed HOLD admission tests; no actual model/browser/worker execution."""
import contextlib,io,json,os,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(os.environ.get('SVF_FOUNDATION_REPOSITORY_ROOT',str(Path(__file__).resolve().parents[1])))
if os.environ.get('SVF_HOLD_WORKER_CANDIDATE'):sys.path.insert(0,str(Path(os.environ['SVF_HOLD_WORKER_CANDIDATE']).parent))
sys.path.append(str(ROOT/'scripts'))
import swissknife_visual_functional_worker as w
import swissknife_visual_functional_llm as llm

class CoordinatorHoldTests(unittest.TestCase):
 def setUp(self):
  temporary=tempfile.TemporaryDirectory(dir='/dev/shm');self.addCleanup(temporary.cleanup);self.root=Path(temporary.name)
  p=patch.object(w,'ROOT',self.root);p.start();self.addCleanup(p.stop)
  self.profile={'runtimeRoot':'data/agent_supervisor/swissknife_visual_functional','taskSpecPath':'tasks.json','humanPlanPath':'board.md','todoPath':'board.md','appContractPath':'contracts.json','llm':{'provider':'grok_cli','model':'grok-4.7','repairReadPolicy':'inline_only'}}
  self.task={'task_id':'SVF-099','kind':'implementation','title':'Authored task','acceptance':'Actual evidence required','edit_paths':['app.py'],'checks':[['python3','app.py']]}
  for name,value in [('profile.json',self.profile),('tasks.json',{'tasks':[self.task]}),('contracts.json',{'apps':[]})]:(self.root/name).write_text(json.dumps(value))
  (self.root/'app.py').write_text('VALUE = 1\n');(self.root/'board.md').write_text('## SVF-099 Authored\n- Status: ready\n- Predicted files: app.py\n')
  self.budget=self.root/self.profile['runtimeRoot']/'tasks/SVF-099/required-phase-repair-budget.json';self.budget.parent.mkdir(parents=True);self.budget.write_bytes(b'{"spent":6,"history":["existing paid work"]}\n')
  self.source=(self.root/'app.py').read_bytes();self.paid=self.budget.read_bytes()
 def assert_preserved(self):
  self.assertEqual((self.root/'app.py').read_bytes(),self.source);self.assertEqual(self.budget.read_bytes(),self.paid);self.assertFalse(list(self.root.rglob('receipt.json')))
 def test_actual_main_hold_after_spawn_refuses_before_lease_model_budget_or_sources(self):
  (self.root/'HOLD').write_text('authored operator hold')
  with patch.object(w,'assert_storage_available',side_effect=AssertionError('no storage admission')),patch.object(w,'model',side_effect=AssertionError('no model')),contextlib.redirect_stderr(io.StringIO())as stderr:
   code=w.main(['--profile','profile.json','--task-id','SVF-099'])
  self.assertEqual(code,75);self.assertEqual(json.loads(stderr.getvalue()),{'task_id':'SVF-099','error':{'code':'operator_hold'},'retryable':True,'work_complete':False,'completion_authority':False});self.assert_preserved()
 def test_identical_runtimeerror_message_is_still_a_real_failure(self):
  with patch.object(w,'execute',side_effect=RuntimeError('coordinator hold is active; no new model invocation or source apply')),contextlib.redirect_stderr(io.StringIO())as stderr:
   code=w.main(['--profile','profile.json','--task-id','SVF-099'])
  self.assertEqual(code,1);self.assertIn('RuntimeError',stderr.getvalue());self.assertNotIn('operator_hold',stderr.getvalue());self.assert_preserved()
 def test_all_existing_hold_markers_raise_only_the_dedicated_type(self):
  for directory in (self.root,w.runtime_root(self.profile),w.runtime_root(self.profile)/'state',w.runtime_root(self.profile)/'watchdog'):
   directory.mkdir(parents=True,exist_ok=True)
   for name in ('HOLD','OPERATOR_STOP','watchdog.disabled','hold','operator.hold'):
    with self.subTest(directory=directory,name=name):
     path=directory/name;path.touch()
     try:
      with self.assertRaises(w.CoordinatorHold):w.assert_no_campaign_hold(self.profile)
     finally:path.unlink()
 def test_verify_hold_cannot_start_repair_or_write_semantic_failure(self):
  task={**self.task,'kind':'verify','app_id':'demo'}
  import swissknife_visual_functional_review_recheck as recheck
  with patch.object(w,'ensure_lease'),patch.object(w,'check_owned_sources'),patch.object(w,'assert_storage_available'),patch.object(recheck,'assert_recheck_allowed'),patch.object(w,'workflow',side_effect=w.CoordinatorHold('authored hold race')),patch.object(w,'model',side_effect=AssertionError('no repair')),patch.object(w,'remember_execution_failure',side_effect=AssertionError('no semantic failure')):
   with self.assertRaises(w.CoordinatorHold):w.execute('profile.json',self.profile,{'tasks':[task]},task)
  self.assert_preserved()
 def test_final_verify_hold_cannot_become_negative_visual_evidence(self):
  task={**self.task,'kind':'final-app-verify','app_id':'demo'}
  import swissknife_visual_functional_final_coverage as final
  with patch.object(w,'ensure_lease'),patch.object(w,'check_owned_sources'),patch.object(w,'assert_storage_available'),patch.object(final,'validate_final_task_contract'),patch.object(final,'assert_final_review_allowed'),patch.object(w,'workflow',side_effect=w.CoordinatorHold('authored hold race')),patch.object(w,'model',side_effect=AssertionError('no model')),patch.object(w,'remember_execution_failure',side_effect=AssertionError('no semantic failure')):
   with self.assertRaises(w.CoordinatorHold):w.execute('profile.json',self.profile,{'tasks':[task]},task)
  self.assert_preserved()
 def test_hold_during_source_apply_propagates_without_repair_feedback_or_checks(self):
  with patch.object(w,'ensure_lease'),patch.object(w,'check_owned_sources'),patch.object(w,'assert_storage_available'),patch.object(w,'model',return_value={'response':{'edits':[]}}),patch.object(w,'apply_task_edits',side_effect=w.CoordinatorHold('authored source fence hold')),patch.object(w,'remember_repair_failure',side_effect=AssertionError('no false repair failure')),patch.object(w,'run',side_effect=AssertionError('no check')):
   with self.assertRaises(w.CoordinatorHold):w.execute('profile.json',self.profile,{'tasks':[self.task]},self.task)
  self.assert_preserved()
 def test_hold_during_declared_check_does_not_start_another_repair_attempt(self):
  with patch.object(w,'ensure_lease'),patch.object(w,'check_owned_sources'),patch.object(w,'assert_storage_available'),patch.object(w,'model',return_value={'response':{'edits':[]}})as model,patch.object(w,'apply_task_edits',return_value={'applied':[]}),patch.object(w,'remember_owned_sources'),patch.object(w,'remember_repair_failure',side_effect=AssertionError('no false semantic feedback')),patch.object(w,'run',side_effect=w.CoordinatorHold('authored check fence hold')):
   with self.assertRaises(w.CoordinatorHold):w.execute('profile.json',self.profile,{'tasks':[self.task]},self.task)
  self.assertEqual(model.call_count,1);self.assert_preserved()
 def test_preprovider_recheck_catches_new_hold_after_context_without_spending_paid_budget(self):
  actual=w._repair_inputs;calls=[]
  def pack(*args,**kwargs):
   result=actual(*args,**kwargs);(self.root/'HOLD').touch();return result
  def no_provider(*args,**kwargs):calls.append('provider');raise AssertionError('no provider')
  with patch.object(w,'assert_storage_available'),patch.object(w,'workflow_fixtures',return_value=None),patch.object(w,'load_execution_failure',return_value=None),patch.object(w,'_repair_inputs',side_effect=pack),patch.object(llm,'invoke_task_model',side_effect=no_provider):
   with self.assertRaises(w.CoordinatorHold):w.model('profile.json',self.task,'repair',[],[],self.budget.parent/'proposal.json')
  self.assertEqual(calls,[]);self.assertFalse(list(self.root.rglob('last-repair-error.json')));self.assert_preserved()

if __name__=='__main__':unittest.main()
