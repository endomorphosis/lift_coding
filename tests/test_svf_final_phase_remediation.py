"""Finite authored RAM final-remediation fixtures; no live/browser/provider authority.

The fixed final-app population below is the canonical public task family, not a
live task-source read. Publication tests exercise real metadata CAS and native
plan-revision admission on temporary files; only explicit external producer and
lease observations are authored boundaries.
"""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import os
import sys
import tempfile
import unittest
import uuid
from unittest.mock import patch

ROOT=Path(os.environ.get('SVF_FOUNDATION_REPOSITORY_ROOT',Path(__file__).resolve().parents[1]))
STAGE=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(STAGE/'scripts'),str(ROOT/'scripts'),str(ROOT/'tests'),str(ROOT/'external/ipfs_accelerate')]
import swissknife_visual_functional_phase_remediation as r

FINAL_APPS=('terminal','vibecode','music-studio-unified','ai-chat','file-manager','task-manager','todo','model-browser','huggingface','openrouter','ipfs-explorer','device-manager','settings','mcp-control','api-keys','github','oauth-login','cron','navi','p2p-network','p2p-chat-unified','neural-network-designer','training-manager','calculator','clock','calendar','peertube','friends-list','image-viewer','notes','media-player','system-monitor','neural-photoshop','cinema','strudel','strudel-ai-daw','music-studio','p2p-chat','datasets-browser','accelerate-panel','idl-explorer','glasses-preview','orb-auto-ui','mcp-plus-plus','agent-supervisor')
FINAL_IDS={f'SVF-{1001+i}':app for i,app in enumerate(FINAL_APPS)}
POLICY={'schema':'swissknife.final-remediation.v1','enabled':True,'max_finals':45,'max_children_per_final':1,'max_paid_assessments':1,'max_paid_proposals':1,'child_timeout_seconds':3600}

def canonical_tasks():
 verifies=[]
 for identity,app in r.ORIGINAL_APPS.items():
  verifies.append({'task_id':identity,'kind':'verify','app_id':app,'goal_id':'SVF-G001','status':'completed','dependencies':[], 'checks':[], 'edit_paths':['swissknife/web/js/apps/'+app+'.js','swissknife/test/e2e/functional-workflows/'+app+'.json'], 'execution_inputs':[], 'context_paths':[]})
 basis={t['app_id']:t['task_id']for t in verifies};deps=[*r.ORIGINAL_APPS,'SVF-043','SVF-044']
 finals=[{'task_id':identity,'kind':'final-app-verify','app_id':app,'original_verify_task':basis[app], 'goal_id':'SVF-G601','status':'ready','dependencies':list(deps),'checks':[], 'edit_paths':[], 'acceptance':'Original readonly two-view acceptance remains authoritative.', 'execution_command':['python3',r.WORKER,'--task-id',identity], 'execution_validation':['python3',r.WORKER,'--validate','--task-id',identity], 'timeout_seconds':3600, 'context_paths':['swissknife/web/js/apps/'+app+'.js'], 'execution_inputs':['swissknife/web/js/apps/'+app+'.js']}for identity,app in FINAL_IDS.items()]
 return verifies+[{'task_id':n,'kind':'command','goal_id':'SVF-G001','status':'completed','dependencies':[]}for n in ['SVF-043','SVF-044']]+finals

class PolicyAndPopulationTests(unittest.TestCase):
 def test_exact_opt_in_policy_is_finite_and_disabled_by_default(self):
  self.assertFalse(r.policy_enabled({}));self.assertFalse(r.policy_enabled({'finalRemediation':{**POLICY,'enabled':False}}));self.assertTrue(r.policy_enabled({'finalRemediation':copy.deepcopy(POLICY)}))
  for key,value in [('max_finals',46),('max_children_per_final',2),('max_paid_assessments',2),('max_paid_proposals',2),('child_timeout_seconds',3601),('max_paid_proposals',True),('schema','swissknife.phase-remediation.v1'),('unknown',False)]:
   with self.subTest(key=key,value=value),self.assertRaises(r.RemediationRefusal):r.policy_enabled({'finalRemediation':{**POLICY,key:value}})
 def test_exact_forty_five_final_ids_apps_and_no_duplicate_or_legacy_substitution(self):
  tasks=canonical_tasks();self.assertEqual({k:v['app_id']for k,v in r.finals({'tasks':tasks}).items()},FINAL_IDS)
  for mutation in ('missing','duplicate','wrong_app','wrong_id','wrong_kind','writable_final','recovery_authority','wrong_basis','missing_dependency'):
   candidate=copy.deepcopy(tasks);target=next(t for t in candidate if t['task_id']=='SVF-1001')
   if mutation=='missing':candidate.remove(target)
   elif mutation=='duplicate':candidate.append(copy.deepcopy(target))
   elif mutation=='wrong_app':target['app_id']='notes'
   elif mutation=='wrong_id':target['task_id']='SVF-1046'
   elif mutation=='wrong_kind':target['kind']='verify'
   elif mutation=='writable_final':target['edit_paths']=['swissknife/web/js/apps/terminal.js']
   elif mutation=='recovery_authority':target['recovery_edit_paths']=[]
   elif mutation=='wrong_basis':target['original_verify_task']='SVF-123'
   else:target['dependencies'].remove('SVF-044')
   with self.subTest(mutation=mutation),self.assertRaises(r.RemediationRefusal):r.finals({'tasks':candidate})

class FinalAdmissionTests(unittest.TestCase):
 def setUp(self):
  import swissknife_visual_functional_final_coverage as final
  self.final=final;self.temp=tempfile.TemporaryDirectory(dir='/dev/shm');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
  self.profile={'runtimeRoot':'runtime','taskSpecPath':'tasks.json','todoPath':'board.md','objectivePath':'goals.md','appContractPath':'apps.json','finalRemediation':copy.deepcopy(POLICY)}
  self.tasks=canonical_tasks();self.task=next(t for t in self.tasks if t['task_id']=='SVF-1001');self.original=copy.deepcopy(self.task)
  self.put('tasks.json',{'tasks':self.tasks,'goals':[{'goal_id':'SVF-G001'},{'goal_id':'SVF-G601'}]});self.put('goals.md','IMMUTABLE ORIGINAL GOALS')
  self.completed='';board=''
  for t in self.tasks:
   block='## '+t['task_id']+' authored fixture\n\n- Status: '+t['status']+'\n- Goal id: '+t['goal_id']+'\n- Depends on: '+(', '.join(t['dependencies'])or'none')+'\n\n'
   board+=block
   if t['status']=='completed':self.completed+=block
  self.put('board.md',board)
  self.app='swissknife/web/js/apps/terminal.js';self.scenario='swissknife/test/e2e/functional-workflows/terminal.json';self.put(self.app,'AUTHORED ORIGINAL APP');self.put(self.scenario,{'schema':'AUTHORED scenario only'})
  self.put('apps.json',{'apps':[{'app_id':'terminal','source_paths':['web/js/apps/terminal.js','web/js/main-simple.js','web/css/terminal.css']}]})
  self.put('config/swissknife_visual_functional_foundation_owners.json',{'protected_sha256':{'scripts/protected-controller.py':'f'*64}})
  self.put('runtime/tasks/SVF-143/required-phase-repair-budget.json',{'spent':6,'history':['IMMUTABLE OLD SPEND']});self.put('runtime/state/lane_resume_attempts.json',{})
  self.put('runtime/tasks/SVF-143/receipt.json',{'AUTHORED':True,'preserve':'ORIGINAL ACCEPTED RECEIPT'})
  self.review_name='runtime/tasks/SVF-1001/verification/attempt-authored/visual-review.json';self.put(self.review_name,{'schema':'swissknife.visual-functional-model-receipt.v1','task_id':'SVF-1001','mode':'review','provider':'grok_cli','model':'grok-4.7','success':True,'invocation_id':'b1eeb321-2bfa-4b84-93fd-2274a04e2b82','response':{'decision':'needs_changes'}})
  self.fence_name='runtime/tasks/SVF-1001/failed-final-review-source-fence.json'
  value={'schema':final.FAILURE_SCHEMA,'task_id':'SVF-1001','app_id':'terminal','task_contract':{k:v for k,v in self.task.items()if k!='status'},'identity':self.identity(self.task),'evidence':{'authored_external_producer_boundary':True},'failed_review':r.ref(self.root,self.review_name),'work_complete':False,'completion_authority':False};self.put(self.fence_name,value)
  self.patches=[]
  for obj,name,kwargs in [(final,'_review_identity',{'side_effect':lambda root,profile,task:self.identity(task)}),(final,'review_join',{'return_value':{'AUTHORED_STRICT_BOUNDARY_ONLY':True}}),(r,'_validate_current_failed_phase',{'return_value':{'AUTHORED_STRICT_BOUNDARY_ONLY':True}})]:
   p=patch.object(obj,name,**kwargs);p.start();self.addCleanup(p.stop)
  self.baseline={n:(self.root/n).read_bytes()for n in ['goals.md','runtime/tasks/SVF-143/receipt.json','runtime/tasks/SVF-143/required-phase-repair-budget.json','runtime/state/lane_resume_attempts.json']}
  self.spec_before=(self.root/'tasks.json').read_bytes();self.board_before=(self.root/'board.md').read_bytes();self.authority=lambda:{'lease_id':'AUTHORED-physical-lease-boundary'}
 def put(self,name,value):
  p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(value if isinstance(value,bytes)else (json.dumps(value,indent=2)+'\n').encode()if not isinstance(value,str)else value.encode());return p
 def identity(self,task):
  return {'task_semantics_sha256':self.final.task_identity(task),'source_sha256':{n:hashlib.sha256((self.root/n).read_bytes()).hexdigest()for n in [self.app,self.scenario]}}
 def assert_preserved(self):
  for name,want in self.baseline.items():self.assertEqual((self.root/name).read_bytes(),want,name)
  for identity,block in r.blocks(self.board_before.decode()).items():
   if identity!='SVF-1001':self.assertEqual(r.blocks((self.root/'board.md').read_text())[identity],block)
 def plan(self):return r.propose(self.root,self.profile,'SVF-1001')
 def admitted(self):
  plan=self.plan();out=r.publish(self.root,self.profile,plan,ensure_authority=self.authority);spec=json.loads((self.root/'tasks.json').read_bytes());child=next(t for t in spec['tasks']if t['task_id']==plan['child']['task_id']);return plan,out,spec,child
 def test_final_gap_uses_real_closed_fence_without_spending_legacy_history(self):
  gap=r.qualify_gap(self.root,self.profile,self.task);self.assertEqual(gap['mode'],'final-review');self.assertNotIn('spent',gap);self.assertEqual(gap['phase'],gap['fence']);self.assertEqual(gap['source_task']['task_id'],'SVF-143');self.assertEqual(gap['source_scope'],[self.app,self.scenario]);self.assert_preserved()
 def test_wrong_review_hash_or_route_or_stale_source_is_refused_without_plan_write(self):
  original=(self.root/self.review_name).read_bytes();self.put(self.review_name,original+b' ')
  with self.assertRaises(r.RemediationRefusal):self.plan()
  self.put(self.review_name,original);self.put(self.app,'GENUINE NEW SOURCE')
  with self.assertRaisesRegex(r.RemediationRefusal,'stale final gap'):self.plan()
  self.assertEqual((self.root/'tasks.json').read_bytes(),self.spec_before);self.assertEqual((self.root/'board.md').read_bytes(),self.board_before);self.assert_preserved()
 def test_rehashed_foreign_or_positive_review_never_qualifies(self):
  original=json.loads((self.root/self.review_name).read_bytes());fence=json.loads((self.root/self.fence_name).read_bytes())
  for field,value in [('provider','openai'),('mode','repair'),('task_id','SVF-1002'),('success',False),('decision','pass')]:
   altered=copy.deepcopy(original)
   if field=='decision':altered['response']['decision']=value
   else:altered[field]=value
   self.put(self.review_name,altered);updated=copy.deepcopy(fence);updated['failed_review']=r.ref(self.root,self.review_name);self.put(self.fence_name,updated)
   with self.subTest(field=field),self.assertRaisesRegex(r.RemediationRefusal,'negative pinned'):self.plan()
  self.assertEqual((self.root/'tasks.json').read_bytes(),self.spec_before);self.assertEqual((self.root/'board.md').read_bytes(),self.board_before)
 def test_between_cycles_automatically_admits_final_once_without_legacy_namespace_spend(self):
  with patch.object(r,'no_hold_or_activity',return_value=None):
   result=r.between_cycles(self.root,self.profile,ensure_authority=self.authority);self.assertEqual(result['state'],'committed')
   again=r.between_cycles(self.root,self.profile,ensure_authority=self.authority);self.assertEqual(again['state'],'idle')
  spec=json.loads((self.root/'tasks.json').read_bytes());self.assertEqual(sum(t['task_id']=='SVF-FINAL-R1001'for t in spec['tasks']),1)
  self.assertFalse((self.root/'runtime/state/phase-remediation/admissions').exists());self.assert_preserved()
 def test_source_scope_excludes_protected_and_shared_controller_paths(self):
  spec=json.loads(self.spec_before);basis=next(t for t in spec['tasks']if t['task_id']=='SVF-143');basis['edit_paths'] += ['scripts/protected-controller.py','swissknife/web/js/main-simple.js','swissknife/web/js/apps/notes.js'];self.put('tasks.json',spec)
  _,scope=r.final_source_basis(self.root,self.profile,self.task);self.assertEqual(scope,[self.app,self.scenario])
  self.put('config/swissknife_visual_functional_foundation_owners.json',{'protected_sha256':{self.app:'a'*64,self.scenario:'b'*64}})
  with self.assertRaisesRegex(r.RemediationRefusal,'no bounded'):r.final_source_basis(self.root,self.profile,self.task)
 def test_native_metadata_cas_admits_one_child_preserves_original_and_replays_exactly(self):
  plan,out,spec,child=self.admitted();self.assertEqual(out['state'],'committed');self.assertEqual(child['task_id'],'SVF-FINAL-R1001');self.assertEqual(child['edit_paths'],[self.app,self.scenario]);self.assertEqual(child['timeout_seconds'],3600)
  parent_after=next(t for t in spec['tasks']if t['task_id']=='SVF-1001');self.assertEqual(len(self.original['dependencies']),47);self.assertEqual(len(parent_after['dependencies']),48);self.assertEqual(self.final.validate_final_task_contract(self.root,self.profile,parent_after,spec)['task_id'],'SVF-143')
  self.assertEqual(next(t for t in spec['tasks']if t['task_id']=='SVF-1001'),{**self.original,'dependencies':[*self.original['dependencies'],child['task_id']]});self.assertEqual(child['phase_remediation']['mode'],'final-review');self.assertFalse(child['phase_remediation']['allow_children']);self.assertFalse(child['phase_remediation']['allow_recovery'])
  self.assertEqual(child['phase_remediation']['max_paid_proposals'],1);self.assertEqual(child['phase_remediation']['max_paid_assessments'],1)
  original,parent,intent=r.child_contract(self.root,self.profile,spec,child);self.assertEqual(original,self.original);self.assertIn('/state/final-phase-remediation/',intent['native_admission']['path']);self.assertTrue(r.publish(self.root,self.profile,plan,ensure_authority=self.authority)['replayed']);self.assert_preserved()
  with self.assertRaises(r.RemediationRefusal):r.child_task(self.profile,child,plan['gap'])
 def test_foreign_canonical_or_hold_refuses_without_touching_source_or_history(self):
  plan=self.plan();self.put('board.md',self.board_before+b'\nFOREIGN completion must remain\n');foreign=(self.root/'board.md').read_bytes()
  with self.assertRaises(ValueError):r.publish(self.root,self.profile,plan,ensure_authority=self.authority)
  self.assertEqual((self.root/'tasks.json').read_bytes(),self.spec_before);self.assertEqual((self.root/'board.md').read_bytes(),foreign)
  self.put('board.md',self.board_before);self.put('HOLD','AUTHORED FOREIGN HOLD');before=(self.root/'HOLD').read_bytes()
  with self.assertRaisesRegex(r.RemediationRefusal,'HOLD'):r.publish(self.root,self.profile,plan,ensure_authority=self.authority)
  self.assertEqual((self.root/'HOLD').read_bytes(),before);self.assertEqual((self.root/'tasks.json').read_bytes(),self.spec_before)
 def test_crash_after_spec_publish_recovers_forward_with_no_second_native_identity(self):
  plan=self.plan()
  def fault(point):
   if point=='after:tasks.json':raise RuntimeError('AUTHORED interruption')
  with self.assertRaisesRegex(RuntimeError,'interruption'):r.publish(self.root,self.profile,plan,ensure_authority=self.authority,fault=fault)
  self.assertEqual((self.root/'board.md').read_bytes(),self.board_before);out=r.publish(self.root,self.profile,plan,ensure_authority=self.authority);self.assertEqual(out['state'],'committed');self.assert_preserved()
 def test_duplicate_and_completed_final_never_mint_another_child(self):
  plan,_,spec,child=self.admitted()
  with self.assertRaises(r.RemediationRefusal):self.plan()
  self.assertEqual(sum(t['task_id']==child['task_id']for t in spec['tasks']),1)
  self.put('tasks.json',self.spec_before);self.put('board.md',self.board_before.replace(b'## SVF-1001 authored fixture\n\n- Status: ready',b'## SVF-1001 authored fixture\n\n- Status: completed'))
  with self.assertRaisesRegex(r.RemediationRefusal,'completed history'):self.plan()
 def admission(self,child):
  identity=str(uuid.uuid4());output='runtime/tasks/'+child['task_id']+'/proposal.json'
  return {'schema':'swissknife.visual-functional-provider-admission.v1','invocation_id':identity,'task_id':child['task_id'],'mode':'repair','provider':'grok_cli','model':'grok-4.7','output_path':output,'attempt_receipt_path':str(Path(output).parent/'model-invocations'/('proposal-'+identity+'.json')),'source_contract_sha256':'a'*64,'prompt_sha256':'b'*64,'router_source_sha256':'c'*64,'input_files':[],'screenshots':[],'timeout_seconds':60,'model_context_bytes':262144,'max_output_tokens':12288,'max_turns':8}
 def test_real_payment_claim_is_once_and_deadline_cannot_reset_after_source_churn(self):
  _,_,spec,child=self.admitted();admission=self.admission(child);first=r.admit_payment(self.root,self.profile,spec,child,'proposal',admission);self.assertEqual(first,admission['invocation_id']);paid=r.payments(self.root,self.profile,child);self.assertEqual(paid['spent'],{'proposal':1,'assessment':0})
  with self.assertRaisesRegex(r.RemediationRefusal,'allowance exhausted'):r.admit_payment(self.root,self.profile,spec,child,'proposal',self.admission(child))
  before=(self.root/'runtime/tasks/SVF-FINAL-R1001/execution-deadline.json').read_bytes();self.put(self.app,'SOURCE CHURN DOES NOT REFUND SPEND');r.remaining_seconds(self.root,self.profile,child);self.assertEqual((self.root/'runtime/tasks/SVF-FINAL-R1001/execution-deadline.json').read_bytes(),before);self.assertEqual(r.payments(self.root,self.profile,child)['spent']['proposal'],1);self.assert_preserved()

if __name__=='__main__':unittest.main()
