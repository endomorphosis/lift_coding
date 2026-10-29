"""Authored presentation-policy tests; no producer, owner, model or compiler calls."""
import copy,importlib.util,inspect,json,os,sys,tempfile,unittest
from pathlib import Path
from unittest import mock
ROOT=Path(__file__).resolve().parents[1]
helper=Path(os.environ.get('SVF_PRIMARY_PROJECTION_HELPER',str(ROOT/'scripts/swissknife_visual_functional_final_coverage.py')))
spec=importlib.util.spec_from_file_location('svf_primary_projection_under_test',helper)
f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
# Exact retained 1001 primary payload; copied text is a fixture, not new execution evidence.
RETAINED_OBSERVED={'operator': 'contains', 'actual': "Welcome to SwissKnife Terminal\n=============================\n\nBrowser-local shell. Listings, file reads and history run in this page.\nThe workspace lives in this browser session.\n\nAvailable commands:\n• help - Show all available commands\n• pwd - Show the current directory\n• history - Show commands kept in this browser\n\nType 'help' for a complete list of commands.\nswissknife@desktop:/home/swissknife$ helpAvailable commands:System Commands:  help           - Show this help message  clear          - Clear the terminal  echo <text>    - Display text  pwd            - Show current directory  ls [flags]     - List files and directories  cd <dir>       - Change directory  mkdir <name>   - Create directory  touch <name>   - Create file  cat <file>     - Display file contents  date           - Show current date  whoami         - Show current user  uname          - Show system information  ps             - Show running processes  env            - Show environment variables  history        - Show command historyThis local shell runs only the commands listed above.swissknife@desktop:/home/swissknife$ lslocal directory listing: /home/swissknife📄 config.json  📁 projects  📄 README.md  📁 scripts  📄 data.jsonswissknife@desktop:/home/swissknife$ lslocal directory listing: /home/swissknife📄 config.json  📁 projects  📄 README.md  📁 scripts  📄 data.jsonswissknife@desktop:/home/swissknife$ history1  help2  ls3  ls4  history", 'expected': 'README.md'}

class PrimaryObservationTests(unittest.TestCase):
 def fixture(self,observed=None):
  observed=copy.deepcopy(RETAINED_OBSERVED if observed is None else observed)
  views=[];sources=[]
  for index,name in enumerate(('desktop','mobile')):
   original={'requirement_id':'result_1','requirement_text':'Actual local operation','phase':'primary_result','step_index':9,'probe':{'kind':'text','selector':'#terminal-output'},'passed':True,'observed':copy.deepcopy(observed)}
   reference={'path':'tasks/fixture/'+name+'/workflow.json','sha256':str(index+1)*64,'bytes':100+index}
   child={'session_id':name+'-distinct','semantic_assertions':[original]}
   row={**copy.deepcopy(original),'observed_sha256':f.digest(observed),'observed':{'projection_omitted':True,'original_bytes':len(f.encoded(observed)),'original_sha256':f.digest(observed)}}
   views.append({'name':name,'session_id':child['session_id'],'original':copy.deepcopy(reference),'semantic_assertions':[row],'backend_observations':[],'phase_evidence':{}})
   sources.append(({'name':name,'report':reference},child))
  return {'viewports':views,'original_fact':[False,0,-0.0,None,'雪',{'actual':{'@':[9]}}]},sources
 def decoded(self,value):return f._expand_projection(value)
 def restore(self,value,sources):return f._retain_primary_observations(value,sources)
 def test_exact_retained_primary_body_two_views_and_all_old_facts(self):
  value,sources=self.fixture();before=copy.deepcopy(value);result=self.restore(value,sources);decoded=self.decoded(result)
  self.assertEqual(len(f.encoded(RETAINED_OBSERVED)),1529)
  self.assertEqual(f.digest(RETAINED_OBSERVED),'3ea89cdc48b6a7a43c642e6478058d40aaddf30bc602acc60c63f061a2f7cac2')
  for row in decoded['viewports']:
   self.assertEqual(f.encoded(row['semantic_assertions'][0]['observed']),f.encoded(RETAINED_OBSERVED))
   self.assertIn('local directory listing: /home/swissknife',row['semantic_assertions'][0]['observed']['actual'])
  for view,old in zip(decoded['viewports'],before['viewports']):view['semantic_assertions'][0]['observed']=old['semantic_assertions'][0]['observed']
  self.assertEqual(f.encoded(decoded),f.encoded(before));self.assertEqual(value,before)
 def test_oversize_payload_keeps_exact_existing_omission_and_real_cap(self):
  value,sources=self.fixture({'operator':'contains','actual':'X'*24000,'expected':'X'})
  result=self.restore(value,sources)
  self.assertEqual(f.encoded(result),f.encoded(value));self.assertLessEqual(len(f.encoded(result)),18000)
 def test_reversible_factor_can_fit_group_without_raising_cap(self):
  value,sources=self.fixture();value['existing_unique_fact']='x'*14000
  self.assertLessEqual(len(f.encoded(value)),18000)
  result=self.restore(value,sources);self.assertLessEqual(len(f.encoded(result)),18000)
  self.assertEqual(self.decoded(result)['viewports'][0]['semantic_assertions'][0]['observed'],RETAINED_OBSERVED)
  self.assertEqual(self.decoded(result)['existing_unique_fact'],value['existing_unique_fact'])
 def test_source_ref_session_requirement_probe_step_and_hash_mismatch_refused(self):
  edits=[lambda v,s:s[0][0].update(name='wrong'),lambda v,s:s[0][0].update(report={**s[0][0]['report'],'sha256':'a'*64}),lambda v,s:s[0][1].update(session_id='wrong'),lambda v,s:s[0][1]['semantic_assertions'][0].update(requirement_id='other'),lambda v,s:s[0][1]['semantic_assertions'][0].update(step_index=8),lambda v,s:s[0][1]['semantic_assertions'][0].update(probe={'kind':'text','selector':'#foreign'}),lambda v,s:v['viewports'][0]['semantic_assertions'][0].update(observed_sha256='0'*64),lambda v,s:v['viewports'][0]['semantic_assertions'][0]['observed'].update(original_bytes=1)]
  for change in edits:
   value,sources=self.fixture();change(value,sources)
   with self.subTest(change=change),self.assertRaises(ValueError):self.restore(value,sources)
 def test_other_phase_omissions_remain_identical(self):
  value,sources=self.fixture()
  for view,source in zip(value['viewports'],sources):view['semantic_assertions'][0]['phase']='persist_reopen';source[1]['semantic_assertions'][0]['phase']='persist_reopen'
  self.assertIs(self.restore(value,sources),value)
 def test_already_literal_projection_is_byte_identical(self):
  value,sources=self.fixture()
  for view in value['viewports']:view['semantic_assertions'][0]['observed']=copy.deepcopy(RETAINED_OBSERVED)
  self.assertIs(self.restore(value,sources),value)
 def test_partial_or_wrong_omission_marker_refused(self):
  for marker in ({'projection_omitted':True},{'projection_omitted':False,'original_bytes':1529,'original_sha256':f.digest(RETAINED_OBSERVED)}):
   value,sources=self.fixture();value['viewports'][0]['semantic_assertions'][0]['observed']=marker
   with self.subTest(marker=marker),self.assertRaises(ValueError):self.restore(value,sources)
 def test_literal_json_types_and_active_codec_keys_are_opaque(self):
  observed={'operator':'not_equals','expected':None,'actual':{'@':[9], 'review_ref':'r0','typed':[False,0,-0.0,1.0,None,'雪']*200}}
  value,sources=self.fixture(observed);result=self.restore(value,sources)
  self.assertEqual(f.encoded(self.decoded(result)['viewports'][0]['semantic_assertions'][0]['observed']),f.encoded(observed))
 def test_smaller_existing_codecs_preserve_complete_native_and_typed_tree(self):
  value,sources=self.fixture();value['repeat']=['exact-source-identity-'+'x'*100]*8
  value['native_request_facts']={'all_requests':[{'phase':'primary_result','index':i,'receipt':'literal-'+str(i),'typed':[False,0,None,'雪']}for i in range(10)]}
  result=f._compact_review_presentation(value)
  self.assertLess(len(f.encoded(result)),len(f.encoded(value)))
  self.assertEqual(f.encoded(f._expand_projection(result)),f.encoded(value))
 def test_projection_builder_restores_exact_payload_without_new_IO_or_facts(self):
  value,sources=self.fixture();root=Path('/authored');report=root/'tasks/fixture/workflow.json';files={}
  entries=[]
  for view,source in zip(value['viewports'],sources):
   name=view['name'];child=copy.deepcopy(source[1]);child.update(viewport={'width':390 if name=='mobile' else 1440,'height':844 if name=='mobile' else 900},result_screenshot={'path':'tasks/fixture/'+name+'/result.png','sha256':'a'*64,'bytes':1},checks=[],keyboard_observations=[],error_observations=[],temporal_observations=[],backend_observations=[],backend_call_count=0,backend_call_phases={},viewports=[{}])
   raw=f.encoded(child);rel='tasks/fixture/'+name+'/workflow.json';files[rel]=raw;entries.append({'name':name,'report':{'path':rel,'sha256':f.digest(child),'bytes':len(raw)}})
  parent={'schema':f.PARENT_SCHEMA,'app_id':'authored-terminal','passed':True,'actual_desktop':True,'source_template':'authored','coverage':{},'contract_sha256':'b'*64,'scenario_sha256':'c'*64,'source_sha256':{'only':'d'*64},'viewport_reports':entries}
  files['tasks/fixture/workflow.json']=f.encoded(parent);files['swissknife/test/e2e/functional-workflows/authored-terminal.json']=f.encoded({'phases':{}})
  with mock.patch.object(f,'read',side_effect=lambda r,n,*a,**k:files[n]),mock.patch.object(f,'_project_backend_observations',return_value=([],[])),mock.patch.object(f,'validate_decoded_images',return_value=[]),mock.patch.object(f,'validate_supplemental_observations',return_value=[]),mock.patch.object(f,'phase_projection',return_value=None),mock.patch.object(f,'native_request_facts',return_value=None):result=f.projection(root,report)
  self.assertLessEqual(len(f.encoded(result)),18000)
  for view in self.decoded(result)['viewports']:self.assertEqual(f.encoded(view['semantic_assertions'][0]['observed']),f.encoded(RETAINED_OBSERVED))

class WorkerPackingFallbackTests(unittest.TestCase):
 def fixture(self,worker_path=None,cap=13000,optional=True,representation_only=False):
  repository=Path(os.environ.get('SVF_PRIMARY_REPOSITORY_ROOT',str(ROOT)))
  sys.path.insert(0,str(ROOT/'scripts'));sys.path.append(str(repository/'scripts'))
  sys.modules['swissknife_visual_functional_final_coverage']=f
  import swissknife_visual_functional_llm as llm
  worker_path=worker_path or ROOT/'scripts/swissknife_visual_functional_worker.py'
  spec=importlib.util.spec_from_file_location('primary_fallback_worker_'+str(id(self)),worker_path)
  w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)
  temporary=tempfile.TemporaryDirectory(dir='/dev/shm');self.addCleanup(temporary.cleanup);root=Path(temporary.name)
  profile={'runtimeRoot':'data/agent_supervisor/swissknife_visual_functional','humanPlanPath':'plan.md','todoPath':'board.md','taskSpecPath':'tasks.json','appContractPath':'contracts.json','workflowFixturesPath':'fixtures.json','llm':{'provider':'grok_cli','model':'grok-4.7','temperature':0,'timeoutSeconds':600,'maxOutputTokens':12288,'maxTurns':8,'modelContextBytes':cap,'allowLocalFallback':False,'allowCrossProviderFallback':False,'disableModelRetry':True}}
  task={'task_id':'SVF-1001','kind':'verify','app_id':'demo','title':'Authored optional primary packing','acceptance':'Original requirements stay authoritative','edit_paths':[]}
  def write(name,value):
   p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(value if isinstance(value,bytes)else f.encoded(value));return p
  write('config/profile.json',profile);write('board.md',b'## SVF-1001 Authored optional primary packing\n\n- Status: ready\n- Predicted files:\n')
  write('tasks.json',{'tasks':[task]});write('contracts.json',{'apps':[{'app_id':'demo','title':'Demo'}]});write('fixtures.json',{'inference_model':'gpt2','notes_collection':'svf-notes-'+'a'*32})
  write('swissknife/test/e2e/functional-workflows/demo.json',{'phases':{}})
  source=write('app.js',b'authored readonly source\n');namespace=profile['runtimeRoot']+'/tasks/SVF-1001/verification/attempt-authored';images=[]
  for name in('desktop','mobile'):
   p=write(namespace+'/'+name+'/result.png',b'\x89PNG\r\n\x1a\n'+b'\0\0\0\rIHDR'+b'\0\0\0\x10\0\0\0\x10');images.append(f.reference(root,p))
  data={'schema':f.PARENT_SCHEMA,'app_id':'demo','source_sha256':{'app.js':f.digest('unused')},'artifacts':images};data['source_sha256']['app.js']=__import__('hashlib').sha256(source.read_bytes()).hexdigest()
  report=write(namespace+'/workflow.json',data)
  validated={'data':data,'report':f.reference(root,report),'children':[{'entry':{'report':{'path':namespace+'/'+name+'/workflow.json','sha256':'b'*64,'bytes':1}},'data':{'viewport':{'name':name}}}for name in('desktop','mobile')],'images':images,'source_identity_sha256':'c'*64}
  baseline={'schema':'swissknife.visual-functional-review-input.v2','projection_only':True,'viewports':[{'name':name,'semantic_assertions':[{'phase':'primary_result','observed':{'projection_omitted':True,'original_bytes':5400,'original_sha256':'d'*64}}]}for name in('desktop','mobile')],'all_old_typed_facts':[False,0,-0.0,None,'exact']}
  enriched=copy.deepcopy(baseline)
  for view in enriched['viewports']:view['semantic_assertions'][0]['observed']={'operator':'contains','actual':'雪'*1800,'expected':'雪'}
  if representation_only:
   baseline['repeat']=['same typed literal '+('x'*100)]*8
   enriched=f._compact_review_presentation(baseline)
  self.assertLess(len(f.encoded(enriched)),18000)
  facts={'schema':'authored-native-facts','requests':[{'request':6,'receipt':'literal-receipt','event':'literal-event','status':'completed','output_sha256':'e'*64}]}
  def project(path,*,retain_primary=True):
   self.assertEqual(Path(path),report);return copy.deepcopy(enriched if optional and retain_primary else baseline)
  patches=[mock.patch.object(w,'ROOT',root),mock.patch.object(w,'assert_no_campaign_hold'),mock.patch.object(w,'assert_storage_available'),mock.patch.object(w,'storage_refusal',return_value=None),mock.patch.object(w,'validate_workflow',return_value=validated),mock.patch.object(w,'_review_projection',side_effect=project),mock.patch.object(f,'native_request_facts',return_value=facts)]
  stack=__import__('contextlib').ExitStack();self.addCleanup(stack.close)
  for patch in patches:stack.enter_context(patch)
  output=root/namespace/'visual-review.json';before={str(p):p.read_bytes()for p in (report,source,*[root/x['path']for x in images])}
  def run():return w.model('config/profile.json',task,'review',[str(report.relative_to(root))],[x['path']for x in images],output)
  return w,llm,root,report,output,baseline,enriched,facts,before,run
 def test_real_worker_and_adapter_overflow_restores_baseline_before_provider_once(self):
  w,llm,root,report,output,baseline,enriched,facts,before,run=self.fixture()
  class StopBeforeProvider(BaseException):pass
  captured={}
  def stop(_root):
   frame=inspect.currentframe().f_back
   while frame and 'prompt'not in frame.f_locals:frame=frame.f_back
   captured.update({key:frame.f_locals[key]for key in('prompt','contract','settings')});raise StopBeforeProvider()
  with mock.patch.object(llm,'invoke_task_model',wraps=llm.invoke_task_model)as invoke,mock.patch.object(llm,'_load_backend',side_effect=stop)as backend:
   with self.assertRaises(StopBeforeProvider):run()
  self.assertEqual(invoke.call_count,2);backend.assert_called_once();self.assertLessEqual(len(captured['prompt'].encode()),13000)
  self.assertEqual(captured['settings']['modelContextBytes'],13000)
  embedded={Path(row['path']).name:json.loads(row['content'])for row in captured['contract']['input_files']if Path(row['path']).name in{'context.json','evidence-0.json'}}
  self.assertEqual(f.encoded(embedded['evidence-0.json']),f.encoded(baseline));self.assertEqual(f.encoded(embedded['context.json']['native_request_facts']),f.encoded(facts))
  diagnostics=list(root.rglob('primary-observation-packing-fallback.json'));self.assertEqual(len(diagnostics),1);d=json.loads(diagnostics[0].read_bytes())
  self.assertTrue(d['before_provider']);self.assertEqual(d['retry_limit'],1)
  saved=d['preserved_enriched_evidence'][0];savedpath=root/saved['retained']['path'];self.assertEqual(f.reference(root,savedpath),saved['retained']);self.assertEqual(json.loads(savedpath.read_bytes()),enriched)
  for name,raw in before.items():self.assertEqual(Path(name).read_bytes(),raw)
  self.assertFalse(list(root.rglob('receipt.json')));self.assertFalse(list(root.rglob('model-invocations')))
 def test_real_enriched_adapter_refuses_before_provider_at_tight_limit(self):
  w,llm,root,report,output,baseline,enriched,facts,before,run=self.fixture()
  class CapturedBudget(BaseException):pass
  real=llm.invoke_task_model;errors=[]
  def first_budget(*args,**kwargs):
   try:return real(*args,**kwargs)
   except llm.ModelContextBudgetError as error:errors.append(error);raise CapturedBudget()
  with mock.patch.object(llm,'invoke_task_model',side_effect=first_budget)as invoke,mock.patch.object(llm,'_load_backend',side_effect=AssertionError('no provider'))as backend:
   with self.assertRaises(CapturedBudget):run()
  self.assertEqual(invoke.call_count,1);backend.assert_not_called();self.assertEqual(len(errors),1);self.assertGreater(errors[0].actual_bytes,13000);self.assertEqual(errors[0].limit_bytes,13000)
  self.assertFalse(list(root.rglob('primary-observation-packing-fallback.json')))
 def test_failed_baseline_budget_propagates_without_third_attempt(self):
  w,llm,root,report,output,baseline,enriched,facts,before,run=self.fixture(cap=2048)
  with mock.patch.object(llm,'invoke_task_model',wraps=llm.invoke_task_model)as invoke,mock.patch.object(llm,'_load_backend',side_effect=AssertionError('no provider'))as backend:
   with self.assertRaises(llm.ModelContextBudgetError):run()
  self.assertEqual(invoke.call_count,2);backend.assert_not_called();self.assertEqual(len(list(root.rglob('primary-observation-packing-fallback.json'))),1)
 def test_nonbudget_exception_is_not_retried(self):
  w,llm,root,report,output,baseline,enriched,facts,before,run=self.fixture()
  with mock.patch.object(llm,'invoke_task_model',side_effect=RuntimeError('actual nonbudget error'))as invoke:
   with self.assertRaisesRegex(RuntimeError,'nonbudget'):run()
  invoke.assert_called_once();self.assertFalse(list(root.rglob('primary-observation-packing-fallback.json')))
 def test_postadmission_budget_typed_error_is_not_retried(self):
  w,llm,root,report,output,baseline,enriched,facts,before,run=self.fixture()
  def admitted(*a,**kw):kw['before_provider']({});raise llm.ModelContextBudgetError(14000,13000)
  with mock.patch.object(llm,'invoke_task_model',side_effect=admitted)as invoke:
   with self.assertRaises(llm.ModelContextBudgetError):run()
  invoke.assert_called_once();self.assertFalse(list(root.rglob('primary-observation-packing-fallback.json')))
 def test_budget_error_without_actual_optional_enrichment_is_not_retried(self):
  w,llm,root,report,output,baseline,enriched,facts,before,run=self.fixture(optional=False)
  with mock.patch.object(llm,'invoke_task_model',side_effect=llm.ModelContextBudgetError(14000,13000))as invoke:
   with self.assertRaises(llm.ModelContextBudgetError):run()
  invoke.assert_called_once();self.assertFalse(list(root.rglob('primary-observation-packing-fallback.json')))
 def test_representation_only_compaction_does_not_enable_optional_retry(self):
  w,llm,root,report,output,baseline,enriched,facts,before,run=self.fixture(representation_only=True)
  self.assertNotEqual(f.encoded(baseline),f.encoded(enriched));self.assertEqual(f.encoded(f._expand_projection(baseline)),f.encoded(f._expand_projection(enriched)))
  with mock.patch.object(llm,'invoke_task_model',side_effect=llm.ModelContextBudgetError(14000,13000))as invoke:
   with self.assertRaises(llm.ModelContextBudgetError):run()
  invoke.assert_called_once();self.assertFalse(list(root.rglob('primary-observation-packing-fallback.json')))
 def test_source_drift_between_budget_refusal_and_fallback_refuses(self):
  w,llm,root,report,output,baseline,enriched,facts,before,run=self.fixture()
  def drift(*a,**kw):report.write_bytes(report.read_bytes()+b' ');raise llm.ModelContextBudgetError(14000,13000)
  with mock.patch.object(llm,'invoke_task_model',side_effect=drift)as invoke:
   with self.assertRaisesRegex(ValueError,'evidence changed'):run()
  invoke.assert_called_once();self.assertFalse(list(root.rglob('primary-observation-packing-fallback.json')))
 def test_wrong_budget_limit_error_is_not_retried(self):
  w,llm,root,report,output,baseline,enriched,facts,before,run=self.fixture()
  with mock.patch.object(llm,'invoke_task_model',side_effect=llm.ModelContextBudgetError(14000,12000))as invoke:
   with self.assertRaises(llm.ModelContextBudgetError):run()
  invoke.assert_called_once();self.assertFalse(list(root.rglob('primary-observation-packing-fallback.json')))

if __name__=='__main__':unittest.main()
