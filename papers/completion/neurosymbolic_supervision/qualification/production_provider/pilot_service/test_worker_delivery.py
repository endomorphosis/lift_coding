"""Constructed client integration checks: no provider, scorer, network or native calls."""
import ast,copy,hashlib,importlib.util,json,shutil,socket,sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
PAPER=Path('papers/completion/neurosymbolic_supervision');SERVICE=PAPER/'qualification/production_provider/pilot_service'
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,sort_keys=True,separators=(',',':')))
class Delivery(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='ns028-client-constructed-');self.root=Path(self.tmp.name);self.addCleanup(self.tmp.cleanup)
  shutil.copytree(HERE,self.root/SERVICE,ignore=shutil.ignore_patterns('__pycache__'))
  for name in ('production_gateway.py','run_comparison.py','score_runs.py'):
   p=self.root/PAPER/'experiments'/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(HERE/'integration_candidates'/PAPER/'experiments'/name,p)
  self.W=load('fixture_worker',self.root/SERVICE/'worker_adapter.py');self.B=load('fixture_builder',self.root/SERVICE/'build_offer_drop.py');self.G=load('fixture_gateway',self.root/PAPER/'experiments/production_gateway.py')
  self.profile={'host_handoff':{'unchanged_development_fixture':True},'pilot_host_handoff':json.loads((HERE/'pilot_profile.template.json').read_text())};save(self.root/PAPER/'experiments/production_profile.json',self.profile)
  self.request={'path_class':'production','record_kind':'pilot','task_id':'ns-hist-05-dnspython','arm':'A','cache':'local_cold','repetition':0}
 def activate(self):
  import datetime as dt
  grants=[]
  for i,unit in enumerate(sorted(self.W.UNITS)):
   queue=self.root/SERVICE/'host_handoff'/str(i);queue.mkdir(parents=True)
   grant={'schema':'operator-historical-pilot-grant/v1','unit':unit,'arm':'A','max_provider_calls':1,'authority':'explicit_operator_pilot_grant_not_campaign_claim','expires_at':(dt.datetime.now(dt.timezone.utc)+dt.timedelta(hours=1)).isoformat(),'queue':str(queue),'grant_id':str(i),'amendment_sha256':'a'*64,'profile':{'constructed_fixture':True},'source_sha256':'b'*64,'manifest_sha256':'c'*64}
   gp=self.root/'private-metadata'/str(i)/'grant.json';save(gp,grant);grants.append(gp)
   req={'schema':'operator-pilot-request/v1','batch_sha256':'d'*64,'cell_id':str(i),'cache':'local_cold','repetition':0,'record_kind':'pilot','grant_sha256':self.W.sha(gp.read_bytes()),'grant_id':str(i),'request_id':str(i),'unit':unit,'arm':'A','amendment_sha256':'a'*64}
   save(queue/'offer.json',{'request':req,'profile':grant['profile'],'source_sha256':grant['source_sha256'],'public_key_sha256':'e'*64,'public_verifier':{'algorithm':'Ed25519','encoding':'spki_der_base64','data':''}})
  names={str(PAPER/'experiments'/n)for n in ('production_gateway.py','run_comparison.py','score_runs.py')}|{str(SERVICE/n)for n in ('worker_adapter.py','pilot_client.py')}
  review={'schema':'ns028-scientific-pilot-activation-review/v1','accepted':True,'frozen_before_comparison_outcomes':True,'comparison_scope_frozen':True,'final_admitted':False,'reviewer_kind':'ai_operator','host_package_sha256':self.W.HOST_PACKAGE,'planned_cells':48,'retained_arms':['A','B','C','D'],'distinct_mechanisms_verified':True,'retained_arm_profiles':{a:{'mechanism_id':'constructed-'+a,'source_sha256':'2'*64,'qualification_sha256':'3'*64}for a in ('A','B','C','D')},'mechanism_context_profile_sha256':'f'*64,'worker_source_review_sha256':'1'*64,'batch_sha256':'d'*64,'worker_source_files':{n:self.W.sha((self.root/n).read_bytes())for n in names},'constructed_fixture_only':True}
  rp=self.root/'fixture-review.json';save(rp,review);out=self.root/'proposed-drop'
  result=self.B.stage(self.root,grants,rp,self.W.sha(rp.read_bytes()),out);self.assertFalse(result['installed'])
  shutil.copy2(out/'offer_drop.json',self.root/SERVICE/'host_handoff/offer_drop.json');shutil.copy2(out/'production_profile.proposed.json',self.root/PAPER/'experiments/production_profile.json')
  return grants,rp
 def test_missing_activation_pending_no_effect(self):
  result=self.G.dispatch(self.request,root=self.root);self.assertEqual(result['status'],'pending_operator_inputs');self.assertFalse(result['terminal']);self.assertFalse((self.root/SERVICE/'host_handoff').exists())
 def test_unsupported_arm_refused(self):
  with self.assertRaises(ValueError):self.W.dispatch(self.root,{**self.request,'arm':'B'})
 def test_late_drop_pending_and_exact_request_replay(self):
  self.activate();first=self.G.dispatch(self.request,root=self.root);second=self.G.dispatch(self.request,root=self.root);self.assertEqual(first,second);self.assertEqual(first['status'],'pending_operator');binding=first['grant_binding'];pc=self.W.client(self.root);queue,offer=pc.selected(self.root,binding);self.assertEqual((queue/'request.json').read_bytes(),pc.canon(offer['request']))
 def test_changed_offer_refused(self):
  self.activate();p=self.root/SERVICE/'host_handoff/0/offer.json';p.write_text('{}')
  req={**self.request,'task_id':sorted(self.W.UNITS)[0]}
  with self.assertRaises(ValueError):self.W.dispatch(self.root,req)
 def test_changed_worker_source_refused(self):
  self.activate();p=self.root/PAPER/'experiments/run_comparison.py';p.write_text(p.read_text()+'\n# changed\n')
  with self.assertRaisesRegex(ValueError,'source changed'):self.W.dispatch(self.root,self.request)
 def test_changed_development_profile_refused(self):
  self.activate();p=self.root/PAPER/'experiments/production_profile.json';x=json.loads(p.read_text());x['host_handoff']={};save(p,x)
  with self.assertRaisesRegex(ValueError,'development/profile'):self.W.dispatch(self.root,self.request)
 def test_activation_requires_real_review_binding(self):
  grants,rp=self.activate();x=json.loads(rp.read_text());x['frozen_before_comparison_outcomes']=False;save(rp,x)
  with self.assertRaisesRegex(ValueError,'pre-outcome'):self.B.stage(self.root,grants,rp,self.W.sha(rp.read_bytes()),self.root/'never-created')
 def test_single_arm_activation_refused(self):
  grants,rp=self.activate();x=json.loads(rp.read_text());x['retained_arms']=['A'];save(rp,x)
  with self.assertRaisesRegex(ValueError,'at least two'):self.B.stage(self.root,grants,rp,self.W.sha(rp.read_bytes()),self.root/'never-created')
 def test_runner_pending_precedes_materialize_and_publish(self):
  R=load('fixture_runner',self.root/PAPER/'experiments/run_comparison.py');obj=R.AttemptExecutor.__new__(R.AttemptExecutor);obj.root=self.root;obj.evidence=object();obj.args=types.SimpleNamespace(scenario='normal',path='production',task_id=self.request['task_id'],arm='A',cache='local_cold',repetition=0,record_kind='pilot');obj.ledger=types.SimpleNamespace(get_internal=lambda _:None);obj._publish=lambda **kw:(_ for _ in()).throw(AssertionError('terminal publish forbidden'))
  with patch.object(R,'load_task',return_value={'task_id':self.request['task_id'],'live_repair_admitted':True}),patch.object(R,'load_gateway',return_value=self.G),patch.object(R,'materialize_live_task',side_effect=AssertionError('historical body access forbidden')):
   result=obj.execute()
  self.assertEqual(result['status'],'pending_operator_inputs');self.assertFalse(result['terminal_published'])
 def test_original_development_route_unchanged(self):
  sentinel={'original_development_route':True}
  with patch.object(self.G,'dispatch_host_handoff',return_value=sentinel)as fn:
   self.assertIs(self.G.dispatch({**self.request,'record_kind':'development'},root=self.root),sentinel);fn.assert_called_once()
 def test_rescore_pilot_scalar_no_hidden_reconstruction(self):
  S=load('fixture_score',self.root/PAPER/'experiments/score_runs.py');binding={'task_id':self.request['task_id'],'arm':'A','cache':'local_cold','repetition':0,'record_kind':'pilot'};receipt={'source_sha256':'s','candidate_sha256':'c','historical_pilot_unit_admitted':True,'served_profile_admitted':True};verified={'receipt':receipt,'binding':binding,'response_sha256':'r'};attempt={'provider_receipt':{'host_verified':verified},'measurement':{'identity':{**binding,'source_preimage_id':'s'},'record_kind':'pilot','admission':{}},'bindings':{'source_preimage_id':'s'},'runner':{'candidate':{'host_candidate_sha256':'c'}}};gw=types.SimpleNamespace(verify_host_response=lambda *_:copy.deepcopy(verified),host_oracle=lambda _:{'status':'passed','reason':'constructed fixture scalar only'})
  with patch.object(S.RUNNER,'load_gateway',return_value=gw),patch.object(S.RUNNER,'repo_root',return_value=self.root),patch.object(S,'reconstruct_hidden_oracle',side_effect=AssertionError('hidden access forbidden'),create=True):result=S.score_host_attempt(attempt)
  self.assertEqual(result['measurement']['terminal_state'],'solved');self.assertEqual(result['runner']['host_rescore']['new_scorer_calls'],0)
  attempt['measurement']['record_kind']='final'
  with patch.object(S.RUNNER,'load_gateway',return_value=gw),patch.object(S.RUNNER,'repo_root',return_value=self.root):
   with self.assertRaisesRegex(ValueError,'schedule'):S.score_host_attempt(attempt)
 def test_remote_accounting_stays_unavailable(self):
  source=(HERE/'integration_candidates'/PAPER/'experiments/run_comparison.py').read_text();self.assertIn('client counters are not a substitute',source);self.assertIn('if kw["record_kind"] == "pilot" else "Historical development only',source)
if __name__=='__main__':
 with patch.object(socket,'create_connection',side_effect=AssertionError('network forbidden')),patch.object(socket.socket,'connect',side_effect=AssertionError('network forbidden')):unittest.main()
