"""Durable paid phase admission, with authored native receipts and no provider."""
import copy
import fcntl
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import swissknife_visual_functional_phase_budget as budget
import swissknife_visual_functional_llm as adapter
import swissknife_visual_functional_worker as worker

class PhaseBudgetTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.task={'task_id':'SVF-123','app_id':'notes','kind':'verify','edit_paths':['app.js'],'context_paths':['desktop.js']}
        self.base=budget.directory(self.root,self.task);self.base.mkdir(parents=True)
        self.put('app.js','original app');self.put('desktop.js','original desktop')
        self.attempt=self.base/'verification'/'attempt-one';self.attempt.mkdir(parents=True)
        self.image=self.attempt/'desktop.png';self.image.write_bytes(b'\x89PNG\r\n\x1a\nactual authored screenshot fixture')
        self.review=self.attempt/'visual-review.json';self.review.write_text(json.dumps(self.receipt('review')))
        self.ref=budget._ref(self.root,self.review);self.hashes={'app.js':self.sha('app.js')}
        self.journal=self.base/'required-phase-repair-budget.json'
    def put(self,name,text):
        path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text);return path
    def sha(self,name):return hashlib.sha256((self.root/name).read_bytes()).hexdigest()
    def receipt(self,mode,decision=None,inputs=None):
        image=str(self.image.relative_to(self.root));decision=decision or ('needs_changes' if mode=='review' else 'blocked')
        response={'schema':adapter.RESPONSE_SCHEMA,'task_id':self.task['task_id'],'mode':mode,'decision':decision,
            'summary':'Retain original visual acceptance.','inspected_screenshots':[image] if mode=='review' else [],
            'findings':[] if decision=='pass' else [{'severity':'major','category':'visual','description':'Shared banner clips content.','evidence_paths':[image]}], 'edits':[]}
        value={'schema':adapter.RECEIPT_SCHEMA,'task_id':self.task['task_id'],'mode':mode,'invocation_id':str(uuid.uuid4()),
            'provider':'grok_cli','model':'grok-4.7','temperature':0,'success':True,'allow_local_fallback':False,
            'allow_cross_provider_fallback':False,'disable_model_retry':True,'edits_applied':False,'work_complete':False,
            'completion_authority':False,'effective_route':{'effective_provider_name':'grok_cli','effective_model_name':'grok-4.7'},
            'native_observation':{'exit_code':0,'native_grok_reason_code':'end_turn','native_grok_error_observed':False,
                'native_grok_progress':{'response_usable':True,'tool_name_counts':{'read_file':1 if mode=='review' else 0,'run_terminal_cmd':0,'unknown':0}}},
            'screenshots':[{'path':image,'sha256':self.sha(image),'size_bytes':self.image.stat().st_size}] if mode=='review' else [],
            'response':response,'input_files':inputs or []}
        for key in ['source_contract_sha256','prompt_sha256','router_source_sha256','output_sha256']:value[key]='c'*64
        value['response_sha256']=hashlib.sha256(adapter._json(response).encode()).hexdigest();return value
    def state(self):return json.loads(self.journal.read_text())
    def admit(self):return budget.admit(self.root,self.task,self.ref,self.hashes)
    def test_six_lifetime_admissions_survive_source_policy_and_process_churn(self):
        for i in range(6):
            self.put('app.js','actual source revision '+str(i));self.hashes={'app.js':self.sha('app.js')}
            identity=self.admit();budget.finish(self.root,self.task,identity,error_type='TimeoutError')
            self.task['execution_inputs']=['new-source-'+str(i)]
        with self.assertRaises(budget.PhaseRepairBudgetExhausted)as raised:self.admit()
        self.assertEqual(self.state()['spent'],6);self.assertEqual(len(self.state()['history']),6)
        self.assertEqual(raised.exception.gap_reference['edit_paths'],['app.js'])
        self.assertTrue(raised.exception.gap_reference['acceptance_must_remain_unchanged'])
        self.assertFalse(self.state()['completion_authority'])
    def test_interrupted_dispatch_consumes_admission_and_cannot_refund(self):
        first=self.admit();self.admit();self.assertEqual(self.state()['spent'],2)
        self.assertEqual(self.state()['history'][0]['state'],'admitted')
        budget.finish(self.root,self.task,first,error_type='ProviderTimeout')
        with self.assertRaises(budget.PhaseBudgetError):budget.finish(self.root,self.task,first)
        self.assertEqual(self.state()['spent'],2)
    def test_corrupt_ledger_is_not_replaced_by_fresh_budget(self):
        self.journal.write_text('{malformed')
        with self.assertRaises(budget.PhaseBudgetError):self.admit()
        self.assertEqual(self.journal.read_text(),'{malformed')
    def test_dangling_symlink_cannot_bypass_close_or_admit(self):
        self.journal.symlink_to(self.base/'missing')
        for action in [self.admit,lambda:budget.close_after_pass(self.root,self.task,self.review,'workflow.json')]:
            with self.assertRaises(budget.PhaseBudgetError):action()
        self.assertFalse((self.base/'missing').exists())
    def test_busy_journal_refuses_paid_dispatch(self):
        self.admit()
        with (self.base/'required-phase-repair-budget.lock').open('a')as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaisesRegex(budget.PhaseBudgetError,'busy'):self.admit()
        self.assertEqual(self.state()['spent'],1)
    def history(self,index,visual=True,valid=True):
        context=self.base/'model-inputs'/str(index)/'context.json'
        value={'task':self.task}
        if visual:value['latest_execution_failure']={'failure':{'visual_review':{'original':self.ref}}}
        self.put(str(context.relative_to(self.root)),json.dumps(value))
        receipt=self.receipt('repair',inputs=[budget._ref(self.root,context)])
        if not valid:receipt['native_observation']['exit_code']=1
        path=self.base/'model-invocations'/str(index)/'unused' # use canonical archive layout
        path=self.base/'archive'/str(index)/'model-invocations'/'repair.json'
        self.put(str(path.relative_to(self.root)),json.dumps(receipt));return path
    def test_qualified_history_is_seeded_once_unrelated_backend_repairs_excluded(self):
        first=self.history(1);self.history(2);self.history(3,visual=False);self.history(4,valid=False)
        self.put(str((self.base/'copy'/'model-invocations'/'same.json').relative_to(self.root)),first.read_text())
        self.assertEqual(len(budget.historical_visual_repairs(self.root,self.task)),2)
        self.assertFalse(self.journal.exists()) # observation itself never writes runtime
        self.admit();self.assertEqual(self.state()['spent'],3)
        self.assertEqual(sum(row['origin']=='historical_validated_completed' for row in self.state()['history']),2)
        self.admit();self.assertEqual(self.state()['spent'],4)
    def test_history_context_and_review_hashes_must_match(self):
        self.history(1);self.review.write_text(self.review.read_text()+' ')
        self.assertEqual(budget.historical_visual_repairs(self.root,self.task),[])
    def test_validated_pass_closes_without_refunding_or_completing(self):
        self.admit();workflow=self.attempt/'workflow.json'
        workflow.write_text(json.dumps({'schema':'swissknife.visual-functional-workflow.v1','passed':True,'actual_desktop':True,'app_id':'notes'}))
        projection=self.base/'model-inputs'/'review'/'workflow.json'
        self.put(str(projection.relative_to(self.root)),json.dumps({'schema':'swissknife.visual-functional-review-input.v1','original':budget._ref(self.root,workflow)}))
        self.review.write_text(json.dumps(self.receipt('review','pass',[budget._ref(self.root,projection)])))
        result=budget.close_after_pass(self.root,self.task,self.review,workflow)
        self.assertEqual(self.state()['state'],'closed');self.assertEqual(self.state()['spent'],1)
        self.assertFalse(result['work_complete']);self.assertFalse(result['completion_authority'])
    def test_pass_cannot_close_without_join_to_original_successful_workflow(self):
        self.admit();workflow=self.put('workflow.json',json.dumps({'schema':'swissknife.visual-functional-workflow.v1','passed':True,'actual_desktop':True,'app_id':'notes'}))
        self.review.write_text(json.dumps(self.receipt('review','pass')))
        with self.assertRaisesRegex(budget.PhaseBudgetError,'bind'):budget.close_after_pass(self.root,self.task,self.review,workflow)
        self.assertEqual(self.state()['state'],'open')
    def test_main_worker_spends_before_provider_failure_and_never_for_backend_only(self):
        profile={'runtimeRoot':'data/agent_supervisor/swissknife_visual_functional','appContractPath':'contracts.json','taskSpecPath':'tasks.json','humanPlanPath':'plan.md','llm':{'provider':'grok_cli','model':'grok-4.7','temperature':0,'repairReadPolicy':'inline_only'}}
        self.put('profile.json',json.dumps(profile));self.put('contracts.json',json.dumps({'apps':[{'app_id':'notes'}]}));self.put('tasks.json',json.dumps({'tasks':[self.task]}));self.put('swissknife/docs/visual-functional-driver-contract.md','readonly grammar')
        failure={'error':{'code':'ValueError'},'visual_review':{'original':self.ref}}
        failure_file=self.put(str((self.base/'last-execution-failure.json').relative_to(self.root)),json.dumps(failure))
        observed={'failure':failure,'original':budget._ref(self.root,failure_file)}
        def invoke(*args,**kw):
            self.assertEqual(self.state()['spent'],1);raise TimeoutError('bounded provider timeout')
        with patch.object(worker,'ROOT',self.root),patch.object(worker,'load_execution_failure',return_value=observed),patch('swissknife_visual_functional_blocked.build_scope',return_value={}),patch('swissknife_visual_functional_blocked.raise_if_blocked'),patch.object(adapter,'invoke_task_model',side_effect=invoke):
            with self.assertRaises(TimeoutError):worker.model('profile.json',self.task,'repair',['app.js'],[],self.base/'repair.json')
        self.assertEqual(self.state()['spent'],1);self.assertEqual(self.state()['history'][0]['error_type'],'TimeoutError')
        for _ in range(5):self.admit()
        original_failure=failure_file.read_bytes()
        with patch.object(worker,'ROOT',self.root),patch.object(worker,'load_execution_failure',return_value=observed),patch('swissknife_visual_functional_blocked.build_scope',return_value={}),patch('swissknife_visual_functional_blocked.raise_if_blocked'),patch.object(adapter,'invoke_task_model')as paid:
            with self.assertRaises(budget.PhaseRepairBudgetExhausted):worker.model('profile.json',self.task,'repair',['app.js'],[],self.base/'repair.json')
            paid.assert_not_called()
        self.assertEqual(failure_file.read_bytes(),original_failure);self.assertEqual(self.state()['spent'],6)
        self.journal.unlink();failure.pop('visual_review')
        with patch.object(worker,'ROOT',self.root),patch.object(worker,'load_execution_failure',return_value=observed),patch('swissknife_visual_functional_blocked.build_scope',return_value={}),patch('swissknife_visual_functional_blocked.raise_if_blocked'),patch.object(adapter,'invoke_task_model',side_effect=TimeoutError('no phase')):
            with self.assertRaises(TimeoutError):worker.model('profile.json',self.task,'repair',['app.js'],[],self.base/'repair.json')
        self.assertFalse(self.journal.exists())
    def test_malformed_admission_or_authority_cannot_reopen_paid_budget(self):
        self.admit();original=self.state()
        for change in [lambda v:v['history'].__setitem__(0,{'admission_id':'x','completion_authority':False}),
                       lambda v:v.pop('work_complete'),lambda v:v.update(state='made_up'),
                       lambda v:v['history'][0]['failed_review'].update(sha256='invalid')]:
            value=copy.deepcopy(original);change(value);self.journal.write_text(json.dumps(value))
            with self.assertRaises(budget.PhaseBudgetError):self.admit()

if __name__=='__main__':unittest.main()
