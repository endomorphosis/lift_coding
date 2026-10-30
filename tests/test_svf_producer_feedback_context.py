"""Authored failed-producer packets; no producer, provider or service execution."""
import copy, hashlib, json, os, sys, tempfile, unittest, zipfile
from pathlib import Path
from unittest import mock

REPO = Path(os.environ.get('SVF_FOUNDATION_REPOSITORY_ROOT', str(Path(__file__).resolve().parents[1])))
CANDIDATE = Path(os.environ.get('SVF_PRODUCER_FEEDBACK_WORKER', str(Path(__file__).resolve().parents[1]/'scripts/swissknife_visual_functional_worker.py')))
sys.path.insert(0, str(CANDIDATE.parent)); sys.path.append(str(REPO/'scripts'))
import swissknife_visual_functional_worker as w
import swissknife_visual_functional_phase_remediation as phase


class ProducerFeedbackContextTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir='/dev/shm'); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); patch = mock.patch.object(w, 'ROOT', self.root); patch.start(); self.addCleanup(patch.stop)
        self.profile = {'runtimeRoot':'data/agent_supervisor/swissknife_visual_functional', 'appContractPath':'contracts.json',
                        'finalRemediation':{'max_paid_producer_repairs':1}}
        self.parent = {'task_id':'SVF-1005','kind':'final-app-verify','app_id':'file-manager','acceptance':'Real save and reread','edit_paths':[]}
        self.paths = ['swissknife/web/js/apps/file-manager.js','swissknife/test/e2e/functional-workflows/file-manager.json']
        self.child = {'task_id':'SVF-FINAL-R1005','kind':'scoped-remediation','app_id':'file-manager','edit_paths':self.paths,
                      'phase_remediation':{'mode':'final-review','original_task':self.parent}}
        self.childdir = self.root/self.profile['runtimeRoot']/'tasks'/self.child['task_id']
        self.attempt = self.root/self.profile['runtimeRoot']/'tasks'/self.parent['task_id']/'verification/attempt-authored'
        self.desktop = self.attempt/'desktop'; self.desktop.mkdir(parents=True); self.childdir.mkdir(parents=True)
        for name,text in zip(self.paths, ('export default "authored save";\n','{"phases":{}}\n')):self.write(name,text)
        self.after={name:w.sha(self.root/name) for name in self.paths}
        self.application = self.childdir/'application.json'; self.put(self.application, {'completion_authority':False,'after':self.after})
        self.dom = self.desktop/'failure-dom.json'; self.put(self.dom, {'diagnostic_only':True,'redacted':True,'primary_content':{
            'text':'Storage failure. Original selected file retained.','controls':[{'tag':'button','name':'Save renamed copy','disabled':False}]}})
        self.failure = self.desktop/'failure.json'; self.put(self.failure, {'schema':'swissknife.visual-functional-workflow-failure.v1',
            'app_id':'file-manager','completion_authority':False,'work_complete':False,'source_sha256':self.after,
            'scenario_sha256':self.after[self.paths[1]],'phase':'primary_result','step':8,
            'error':{'code':'WORKFLOW_ERROR','message':'Timed out waiting for confirmation'},'artifacts':[w.artifact(self.dom)]})
        self.record=self.childdir/'producer-failure-record.json'; self.put(self.record,{'schema':w.EXECUTION_FAILURE_SCHEMA,
            'task_id':self.parent['task_id'],'task_context_sha256':w.failure_task_context(self.parent),'stage':'workflow',
            'completion_authority':False,'work_complete':False,'error':{'code':'ValidationCommandError','message':'command exit 1: \nfailed'},
            'driver_failure':w.artifact(self.failure)})
        self.catalog={'controls':[{'app_id':'file-manager','binding_id':'file-manager.ipfs_kit_py.retrieve_content','owner':'ipfs_kit_py',
            'preferred_tool_ids':['ipfs_cat','ipfs_add'],'selected_tool_id':'ipfs_cat','status':'available','confirmation_required':True,
            'safe_payloads':{'ipfs_add':{'content':'authored bytes'}}}]}
        self.dispositions={'entries':[{'owner':'ipfs_kit_py','tool_id':'ipfs_add','disposition':{'kind':'server_only',
            'governance':'policy_review_required','rationale':'Host filesystem paths need server policy review.'},
            'reachability':{'approved_transports':[]}}, {'owner':'another','tool_id':'unrelated','disposition':{'kind':'browser'}}]}
        self.trace=self.desktop/'trace.zip'; self.make_trace()
        self.check={'argv':['node','swissknife/scripts/run-visual-functional-workflow.mjs','--app','file-manager','--contracts',
            'contracts.json','--output-dir',str(self.attempt),'--independent-viewports'],'exit_code':1,
            'stdout_sha256':hashlib.sha256(b'').hexdigest(),'stderr_sha256':hashlib.sha256(b'failed').hexdigest(),
            'stdout_bytes':0,'stderr_bytes':6,'output_tail':'\nfailed'}

    def write(self,path,text):
        path=Path(path);path=path if path.is_absolute() else self.root/path;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text);return path
    def put(self,path,value):return self.write(path,json.dumps(value))
    def make_trace(self, conflicting=False, missing=False):
        resources={}; events=[]
        for route,body in [('/mcp/tools/bindings?app_id=file-manager',self.catalog),('/mcp/tools/dispositions',self.dispositions)]:
            raw=json.dumps(body).encode();key=hashlib.sha1(raw).hexdigest()+'.json';resources['resources/'+key]=raw
            events.append({'snapshot':{'request':{'url':'http://127.0.0.1:3017'+route,'method':'GET'},
                'response':{'status':200,'content':{'_sha1':key}}}})
        if conflicting:
            raw=json.dumps({'entries':[]}).encode();key=hashlib.sha1(raw).hexdigest()+'.json';resources['resources/'+key]=raw
            events.append({'snapshot':{'request':{'url':'http://127.0.0.1:3017/mcp/tools/dispositions','method':'GET'},
                'response':{'status':200,'content':{'_sha1':key}}}})
        with zipfile.ZipFile(self.trace,'w') as archive:
            archive.writestr('authored.network','\n'.join(map(json.dumps,events)))
            for i,(name,raw) in enumerate(resources.items()):
                if not missing or i:archive.writestr(name,raw)
    def context(self,**kwargs):
        values=dict(profile=self.profile,child=self.child,parent=self.parent,initial_application=w.artifact(self.application),
                    failure_record=w.artifact(self.record),producer_check=self.check);values.update(kwargs);return w.producer_failure_context(**values)
    def packet(self):return {'initial_application':w.artifact(self.application),'failure_record':w.artifact(self.record),
                            'producer_check':self.check,'context':self.context()}

    def test_real_trace_join_preserves_server_only_prohibition_not_catalog_permission(self):
        before={p:p.read_bytes() for p in self.root.rglob('*') if p.is_file()};value=self.context()
        self.assertEqual(value['source_after'],self.after);self.assertEqual(value['producer_check']['exit_code'],1)
        self.assertIn('ipfs_add',value['captured_catalogs'][0]['controls'][0]['safe_payloads'])
        rows=value['captured_dispositions'][0]['entries'];self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['disposition']['kind'],'server_only');self.assertEqual(rows[0]['reachability']['approved_transports'],[])
        self.assertIn('prohibition',value['captured_dispositions'][0]['scope']);self.assertEqual(value['captured_dom'][0]['text'],'Storage failure. Original selected file retained.')
        self.assertIn('server_only is unavailable',value['policy_instruction']);self.assertIn('Never fabricate confirmation',value['policy_instruction'])
        self.assertTrue(value['trace']['sha256']);self.assertEqual(before,{p:p.read_bytes() for p in before})

    def test_source_application_or_driver_mutation_refuses(self):
        for kind in ('app','driver','application'):
            with self.subTest(kind=kind):
                target=self.root/self.paths[0] if kind=='app' else self.failure if kind=='driver' else self.application
                before=target.read_bytes();old_application=w.artifact(self.application);old_record=w.artifact(self.record)
                try:
                    target.write_bytes(before+b' ')
                    with self.assertRaises((ValueError,json.JSONDecodeError)):
                        self.context(initial_application=old_application,failure_record=old_record)
                finally:target.write_bytes(before)

    def test_command_exit_and_task_scope_are_closed(self):
        for change in ({'exit_code':0},{'exit_code':75},{'exit_code':False},{'argv':['node','other.mjs']},{'stdout_sha256':'bad'}, {'output_tail':'forged'}):
            with self.subTest(change=change),self.assertRaises(ValueError):self.context(producer_check={**self.check,**change})
        argv=list(self.check['argv']);argv[7]=str(self.root/'elsewhere/attempt-authored')
        with self.assertRaises(ValueError):self.context(producer_check={**self.check,'argv':argv})
        with self.assertRaises(ValueError):self.context(child={**self.child,'kind':'verify'})

    def test_conflicting_policy_missing_resource_and_foreign_artifact_refuse(self):
        self.make_trace(conflicting=True)
        with self.assertRaisesRegex(ValueError,'conflicting'):self.context()
        self.make_trace(missing=True)
        with self.assertRaisesRegex(ValueError,'missing'):self.context()
        self.make_trace(); foreign=self.root/'foreign.json';self.put(foreign,{})
        with self.assertRaises(ValueError):self.context(failure_record=w.artifact(foreign))

    def test_absent_trace_is_honestly_unobserved_not_approved(self):
        self.trace.unlink();value=self.context();self.assertIsNone(value['trace']);self.assertEqual(value['captured_catalogs'],[])
        self.assertEqual(value['captured_dispositions'],[]);self.assertIn('not approval',value['observation_scope'])

    def test_packet_reconstruction_and_payment_role_guard(self):
        packet=self.packet();ref={'path':'authored-packet.json','sha256':'a'*64,'bytes':1}
        with mock.patch.object(phase,'validate_producer_feedback',return_value=packet,create=True) as validate:
            observed=w._remediation_model_context(self.profile,{},self.child,'repair',(self.child,'producer_repair'),ref)
            self.assertEqual(observed,packet['context']);validate.assert_called_once()
            forged=copy.deepcopy(packet);forged['context']['captured_dispositions'][0]['entries'][0]['disposition']['kind']='browser'
            validate.return_value=forged
            with self.assertRaisesRegex(ValueError,'differs'):w._remediation_model_context(self.profile,{},self.child,'repair',(self.child,'producer_repair'),ref)

    def test_no_generic_recovery_assessment_or_unpaid_feedback_role(self):
        for task,mode,payment,ref in ((self.child,'repair',None,{}),(self.child,'review',(self.child,'producer_repair'),{}),
                ({**self.child,'kind':'implementation'},'repair',({**self.child,'kind':'implementation'},'producer_repair'),{}),
                (self.child,'repair',(self.child,'proposal'),{}),(self.child,'repair',(self.child,'unknown'),None)):
            with self.subTest(task=task['kind'],mode=mode,payment=payment),self.assertRaises(ValueError):
                w._remediation_model_context(self.profile,{},task,mode,payment,ref)
        self.assertIsNone(w._remediation_model_context(self.profile,{},self.child,'repair',(self.child,'proposal'),None))
        self.assertIsNone(w._remediation_model_context(self.profile,{},self.parent,'review',(self.child,'assessment'),None))

    def test_rehashed_packet_bool_to_int_context_mutation_is_not_equal(self):
        packet=self.packet();packet['context']['captured_catalogs'][0]['controls'][0]['confirmation_required']=1
        ref={'path':'authored-packet.json','sha256':'a'*64,'bytes':1}
        with mock.patch.object(phase,'validate_producer_feedback',return_value=packet,create=True):
            with self.assertRaisesRegex(ValueError,'differs'):
                w._remediation_model_context(self.profile,{},self.child,'repair',(self.child,'producer_repair'),ref)

    def test_real_model_boundary_charges_only_feedback_role_and_retains_policy_context(self):
        import swissknife_visual_functional_llm as llm
        import swissknife_visual_functional_native_context as native
        profile={**self.profile,'llm':{'provider':'grok_cli','model':'grok-4.7','repairReadPolicy':'inline_only','timeoutSeconds':600},
                 'humanPlanPath':'board.md','todoPath':'board.md','taskSpecPath':'tasks.json'}
        self.put(self.root/'contracts.json',{'apps':[{'app_id':'file-manager','title':'Authored File Manager'}]})
        self.write('board.md','## SVF-FINAL-R1005 Authored source-only child\n- Status: ready\n')
        self.write('swissknife/docs/visual-functional-driver-contract.md','Authored fixed grammar; no backend authority.\n')
        packet=self.packet();packet_path=self.childdir/'producer-feedback.json';self.put(packet_path,packet);packet_ref=w.artifact(packet_path)
        output=self.childdir/'producer-repair-proposal.json';seen={};before={p:p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        def invoke(*args,**kwargs):
            self.assertEqual(kwargs['task_limits']['timeoutSeconds'],85)
            self.assertNotIn(packet_ref['path'],kwargs['input_paths'])
            context_path=next(p for p in kwargs['input_paths'] if p.endswith('/context.json'))
            context=json.loads((self.root/context_path).read_bytes());seen['context']=context
            kwargs['before_provider']({'authored':'before-provider-only'})
            receipt={'response':{'decision':'needs_changes','edits':[{'path':self.paths[0],'old':'authored','new':'corrected'}]}}
            self.put(self.root/kwargs['output_path'],receipt);return receipt
        with mock.patch.object(w,'load',return_value=(profile,{})),mock.patch.object(w,'assert_no_campaign_hold'),mock.patch.object(w,'assert_storage_available'),mock.patch.object(w,'ensure_lease'),mock.patch.object(w,'workflow_fixtures',return_value=None),mock.patch.object(w,'load_execution_failure',return_value=None),mock.patch.object(w,'load_repair_feedback',return_value=None),mock.patch.object(native,'load_native_foundation_context',return_value=None),mock.patch.object(native,'load_native_app_context',return_value=None),mock.patch.object(phase,'validate_producer_feedback',return_value=packet,create=True),mock.patch.object(phase,'producer_repair_remaining_seconds',return_value=100,create=True) as remaining,mock.patch.object(phase,'admit_payment',return_value={'role':'producer_repair'}) as admission,mock.patch.object(phase,'finish_payment') as finish,mock.patch.object(llm,'invoke_task_model',side_effect=invoke) as model,mock.patch.object(llm,'validate_model_receipt'):
            w.model('profile.json',self.child,'repair',[packet_ref['path'],*self.paths],[],output,remediation_payment=(self.child,'producer_repair'),producer_failure=packet_ref)
            self.assertEqual(model.call_count,1);self.assertEqual(admission.call_count,1);self.assertEqual(admission.call_args.args[4],'producer_repair');finish.assert_called_once()
            model.reset_mock();admission.reset_mock();finish.reset_mock();remaining.return_value=15
            with self.assertRaisesRegex(ValueError,'deadline'):
                w.model('profile.json',self.child,'repair',[packet_ref['path'],*self.paths],[],output,remediation_payment=(self.child,'producer_repair'),producer_failure=packet_ref)
            model.assert_not_called();admission.assert_not_called();finish.assert_not_called()
        rows=seen['context']['producer_failure']['captured_dispositions'][0]['entries'];self.assertEqual(rows[0]['disposition']['kind'],'server_only')
        self.assertEqual(seen['context']['producer_failure_packet'],packet_ref)
        self.assertEqual({p:p.read_bytes() for p in before},before)

    def test_adapter_timeout_override_is_positive_integer_and_only_lower(self):
        import swissknife_visual_functional_llm as llm
        profile={'llm':{'timeoutSeconds':600}}
        self.assertEqual(llm.model_call_limits(profile,'repair',{'timeoutSeconds':1})['timeoutSeconds'],1)
        self.assertEqual(llm.model_call_limits(profile,'repair',{'timeoutSeconds':600})['timeoutSeconds'],600)
        for value in (0,-1,True,False,1.5,'30',601):
            with self.subTest(value=value),self.assertRaises(llm.ModelAdapterError):
                llm.model_call_limits(profile,'repair',{'timeoutSeconds':value})
        self.assertEqual(llm.model_call_limits(profile,'review')['timeoutSeconds'],600)
        with self.assertRaises(llm.ModelAdapterError):llm.model_call_limits({'llm':{'timeoutSeconds':300}},'repair',{'timeoutSeconds':301})

    def test_feedback_limit_honors_remaining_reserve_and_existing_lower_limit(self):
        profile={'llm':{'timeoutSeconds':600}}
        for remaining,want in ((700,600),(600,585),(100,85),(16,1)):
            with self.subTest(remaining=remaining),mock.patch.object(phase,'producer_repair_remaining_seconds',return_value=remaining,create=True):
                self.assertEqual(w._producer_repair_task_limits(profile,self.child,'repair')['timeoutSeconds'],want)
        for remaining in (15,5,0,-1,True):
            with self.subTest(remaining=remaining),mock.patch.object(phase,'producer_repair_remaining_seconds',return_value=remaining,create=True),self.assertRaises(ValueError):
                w._producer_repair_task_limits(profile,self.child,'repair')
        with mock.patch.object(phase,'producer_repair_remaining_seconds',return_value=700,create=True):
            self.assertEqual(w._producer_repair_task_limits(profile,{**self.child,'llm_limits':{'timeoutSeconds':40}},'repair')['timeoutSeconds'],40)
        with mock.patch.object(phase,'remaining_seconds',side_effect=AssertionError('original deadline must remain separate')),mock.patch.object(phase,'producer_repair_remaining_seconds',return_value=900,create=True):
            self.assertEqual(w._producer_repair_task_limits(profile,self.child,'repair')['timeoutSeconds'],600)

    def test_actual_adapter_metadata_and_authored_cli_share_reduced_timeout(self):
        from types import SimpleNamespace
        import swissknife_visual_functional_llm as llm
        profile={'todoPath':'board.md','llm':{'provider':'grok_cli','model':'grok-4.7','timeoutSeconds':600,'repairReadPolicy':'inline_only'}}
        self.put(self.root/'profile.json',profile);self.write('board.md','## SVF-FINAL-R1005 Authored child\n- Predicted files: '+self.paths[0]+'\n')
        router_path=self.write('router.py','# authored CLI seam; no subprocess\n');captured={};native={}
        metadata=SimpleNamespace(set_last_cli_observation=lambda provider,value:native.update(value),get_last_cli_observation=lambda provider:dict(native))
        def generate(prompt,**kwargs):
            captured['cli_timeout']=kwargs['timeout'];native.update(exit_code=0,native_grok_reason_code='end_turn',native_grok_error_observed=False,
                native_grok_progress={'response_usable':True,'tool_name_counts':{'read_file':0,'run_terminal_cmd':0,'unknown':0}})
            return json.dumps({'schema':llm.RESPONSE_SCHEMA,'task_id':self.child['task_id'],'mode':'repair','decision':'pass',
                'summary':'Authored transport response only.','inspected_screenshots':[],'findings':[],'edits':[]})
        router=SimpleNamespace(__file__=str(router_path),find_grok_cli=lambda:'/authored/no-process',_grok_cli_auth_available=lambda:True,
            generate_text=generate,get_last_generation_trace=lambda:{'effective_provider_name':'grok_cli','effective_model_name':'grok-4.7'})
        def admission(value):
            captured['admission_timeout']=value['timeout_seconds']
            if phase.producer_repair_remaining_seconds(self.root,profile,self.child)<value['timeout_seconds']+5:
                raise phase.RemediationRefusal('strict original deadline cannot contain provider timeout plus five')
        with mock.patch.object(phase,'producer_repair_remaining_seconds',side_effect=[100,91],create=True),mock.patch.object(llm,'_load_backend',return_value=(router,metadata)):
            limits=w._producer_repair_task_limits(profile,self.child,'repair')
            receipt=llm.invoke_task_model('profile.json',self.child['task_id'],'repair',input_paths=[self.paths[0]],screenshot_paths=[],
                predicted_files=[self.paths[0]],output_path=str((self.childdir/'authored-timeout.json').relative_to(self.root)),root=self.root,
                task_limits=limits,before_provider=admission)
        self.assertEqual(captured,{'cli_timeout':85,'admission_timeout':85});self.assertEqual(receipt['timeout_seconds'],85)
        captured.clear()
        with mock.patch.object(phase,'producer_repair_remaining_seconds',side_effect=[100,89],create=True),mock.patch.object(llm,'_load_backend',return_value=(router,metadata)):
            limits=w._producer_repair_task_limits(profile,self.child,'repair')
            with self.assertRaisesRegex(phase.RemediationRefusal,'deadline'):
                llm.invoke_task_model('profile.json',self.child['task_id'],'repair',input_paths=[self.paths[0]],screenshot_paths=[],
                    predicted_files=[self.paths[0]],output_path=str((self.childdir/'authored-timeout-refusal.json').relative_to(self.root)),root=self.root,
                    task_limits=limits,before_provider=admission)
        self.assertEqual(captured,{'admission_timeout':85})

    def test_archived_parent_record_allowed_but_mutable_latest_record_refused(self):
        archived=self.attempt.parent.parent/'execution-failures'/('a'*32+'.json');archived.parent.mkdir();archived.write_bytes(self.record.read_bytes())
        self.assertEqual(self.context(failure_record=w.artifact(archived))['failure_record'],w.artifact(archived))
        mutable=archived.parent.parent/'last-execution-failure.json';mutable.write_bytes(archived.read_bytes())
        with self.assertRaisesRegex(ValueError,'immutable'):self.context(failure_record=w.artifact(mutable))

    def test_actual_workflow_hook_only_checked_nonzero_and_no_resource_authority(self):
        runner=self.root/'swissknife/scripts/run-visual-functional-workflow.mjs';self.write(runner,'// authored\n')
        self.put(self.root/self.paths[1],{'phases':{}})
        profile={**self.profile,'backends':{'ipfs_kit_py':'http://127.0.0.1:18001','ipfs_datasets_py':'http://127.0.0.1:18002',
                                          'ipfs_accelerate_py':'http://127.0.0.1:18003'}};directory=self.attempt.parent
        def failed(argv,**kwargs):raise w.ValidationCommandError(argv,1,'','authored failed producer')
        archived=self.childdir/'hook-failure.json';self.put(archived,{'authored':True})
        patches=[mock.patch.object(w,'assert_no_campaign_hold'),mock.patch.object(w,'assert_storage_available'),
                 mock.patch.object(w,'workflow_fixtures',return_value=None),mock.patch.object(w,'run',side_effect=failed),
                 mock.patch.object(w,'remember_execution_failure',return_value=archived)]
        with __import__('contextlib').ExitStack() as stack:
            for p in patches:stack.enter_context(p)
            with self.assertRaises(w.ValidationCommandError) as raised:w.workflow(profile,self.parent,directory)
        error=raised.exception;self.assertEqual(error.producer_failure_record,w.artifact(archived));self.assertEqual(error.producer_check['exit_code'],1)
        self.assertEqual(error.producer_check['argv'][-1],'--independent-viewports')
        for resource in (w.CoordinatorHold('hold'),w.BrowserContention('busy'),w.StoragePressure('ENOSPC',28)):
            with mock.patch.object(w,'assert_no_campaign_hold'),mock.patch.object(w,'assert_storage_available'),mock.patch.object(w,'workflow_fixtures',return_value=None),mock.patch.object(w,'run',side_effect=resource),mock.patch.object(w,'storage_refusal',side_effect=lambda e:e if isinstance(e,w.StoragePressure) else None),mock.patch.object(w,'remember_execution_failure',return_value=archived):
                with self.assertRaises(type(resource)) as raised:w.workflow(profile,self.parent,directory)
                self.assertFalse(hasattr(raised.exception,'producer_check'))


if __name__=='__main__':unittest.main()
