"""Authored RAM producer-feedback protocol fixtures, never live acceptance.

The fixture keeps native child admission/CAS, payment claims, source hashes and
application replay real. Browser/provider/kernel observations are explicit
callbacks; audit guards prevent network, subprocesses and non-RAM mutation.
"""
from pathlib import Path
import copy
import hashlib
import json
import os
import sys
import unittest
import uuid
from unittest.mock import patch

ROOT = Path(os.environ.get('SVF_FOUNDATION_REPOSITORY_ROOT', Path(__file__).resolve().parents[1]))
STAGE = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(STAGE/'scripts'), str(ROOT/'scripts'), str(ROOT/'tests'), str(ROOT/'external/ipfs_accelerate')]
import swissknife_visual_functional_phase_remediation as r
import swissknife_visual_functional_llm as llm
import test_svf_final_phase_remediation as shapes


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class FeedbackFixture(unittest.TestCase):
    """A native-admitted child with its first genuine-shaped proposal spent."""
    def setUp(self):
        self.policy = {**shapes.POLICY, 'max_paid_producer_repairs': 1, 'producer_repair_timeout_seconds': 900}
        p = patch.object(shapes, 'POLICY', self.policy)
        p.start(); self.addCleanup(p.stop)
        self.env = shapes.FinalAdmissionTests('runTest')
        self.env.setUp(); self.addCleanup(self.env.doCleanups)
        self.root, self.profile = self.env.root, self.env.profile
        self.plan, self.native_admission, self.spec, self.child = self.env.admitted()
        self.original, self.parent, _ = r.child_contract(self.root, self.profile, self.spec, self.child)
        self.paths = list(self.child['edit_paths'])
        self.directory = self.profile['runtimeRoot']+'/tasks/'+self.child['task_id']
        self.before = {name: (self.root/name).read_bytes() for name in self.paths}
        self.before_hashes = {name: sha(raw) for name, raw in self.before.items()}
        self.initial_after = {self.paths[0]: b'AUTHORED FIRST NATIVE PROPOSAL\n', self.paths[1]: b'{"authored":"first native scenario"}\n'}
        self.feedback_after = {self.paths[0]: b'AUTHORED SECOND PROPOSAL WITH REAL PRODUCER FEEDBACK\n', self.paths[1]: b'{"authored":"feedback scenario"}\n'}
        self.model_calls = []
        self.workflow_calls = []
        self.apply_calls = []
        self.env.put('runtime/owned-source-hashes.json', self.before_hashes)
        self.initial_admission = self.admission('proposal', self.directory+'/proposal.json')
        identity = r.admit_payment(self.root, self.profile, self.spec, self.child, 'proposal', self.initial_admission)
        receipt = self.model_receipt(self.initial_admission, self.before, self.initial_after)
        self.put_receipt(self.initial_admission, receipt)
        r.finish_payment(self.root, self.profile, self.child, identity, receipt=r.ref(self.root, self.initial_admission['output_path']))
        self.initial_paid_row = copy.deepcopy(r.payments(self.root, self.profile, self.child)['history'][0])
        self.original_paid_bytes=(self.root/r.payment_path(self.profile,self.child)).read_bytes()
        self.initial_proposal = (self.root/self.initial_admission['output_path']).read_bytes()
        self.original_deadline = (self.root/self.directory/'execution-deadline.json').read_bytes()
        self.original_canonical = {name:(self.root/name).read_bytes() for name in ['tasks.json','board.md','goals.md']}

    def put(self, name, value):
        return self.env.put(name, value)

    def admission(self, role, output):
        identity = str(uuid.uuid4()); target = Path(output)
        return {'schema':'swissknife.visual-functional-provider-admission.v1', 'invocation_id':identity,
                'task_id':self.child['task_id'], 'mode':'repair', 'provider':'grok_cli','model':'grok-4.7',
                'output_path':output,'attempt_receipt_path':str(target.parent/'model-invocations'/(target.stem+'-'+identity+'.json')),
                'source_contract_sha256':'a'*64,'prompt_sha256':'b'*64,'router_source_sha256':'c'*64,
                'input_files':[],'screenshots':[],'timeout_seconds':60,'model_context_bytes':262144,
                'max_output_tokens':12288,'max_turns':1}

    def model_receipt(self, admission, old, new):
        edits = [{'path':name,'before_sha256':sha(old[name]),'old':old[name].decode(),'new':new[name].decode()} for name in old if old[name] != new[name]]
        response = {'schema':llm.RESPONSE_SCHEMA,'task_id':self.child['task_id'],'mode':'repair','decision':'needs_changes',
                    'summary':'Authored scoped source correction; real acceptance remains downstream.',
                    'inspected_screenshots':[], 'findings':[{'severity':'major','category':'functionality','description':'Observed authored producer failure requires correction.','evidence_paths':[]}], 'edits':edits}
        value = {k:v for k,v in admission.items() if k not in {'schema','output_path'}}
        value.update(schema=llm.RECEIPT_SCHEMA, temperature=0, success=True, allow_local_fallback=False,
                     allow_cross_provider_fallback=False, disable_model_retry=True, edits_applied=False,
                     work_complete=False, completion_authority=False,
                     effective_route={'effective_provider_name':'grok_cli','effective_model_name':'grok-4.7'},
                     native_observation={'exit_code':0,'native_grok_reason_code':'end_turn','native_grok_error_observed':False,
                                         'native_grok_progress':{'response_usable':True,'tool_name_counts':{'read_file':0,'run_terminal_cmd':0,'unknown':0}}},
                     response=response,response_sha256=sha(llm._json(response).encode()),output_sha256='d'*64)
        llm.validate_model_receipt(self.root,value,task_id=self.child['task_id'],mode='repair',predicted_files=self.paths)
        return value

    def put_receipt(self, admission, value):
        raw=r.wire(value)+b'\n'
        self.put(admission['output_path'],raw); self.put(admission['attempt_receipt_path'],raw)

    def apply_edits(self, root, edits, paths, **options):
        self.assertEqual(Path(root), self.root)
        self.apply_calls.append(list(paths))
        return llm.apply_validated_edits(root, edits, paths, **options)

    def check_owned(self, profile, paths):
        ledger=json.loads((self.root/'runtime/owned-source-hashes.json').read_text())
        for name in paths:
            self.assertEqual(sha((self.root/name).read_bytes()), ledger[name], name)

    def remember_owned(self, profile, paths):
        ledger=json.loads((self.root/'runtime/owned-source-hashes.json').read_text())
        ledger.update({name:sha((self.root/name).read_bytes()) for name in paths})
        self.put('runtime/owned-source-hashes.json',ledger)

    def assert_preserved(self):
        self.env.assert_preserved()
        for name,raw in self.original_canonical.items():
            self.assertEqual((self.root/name).read_bytes(),raw,name)
        self.assertEqual((self.root/self.initial_admission['output_path']).read_bytes(), self.initial_proposal)
        self.assertEqual((self.root/self.directory/'execution-deadline.json').read_bytes(), self.original_deadline)
        self.assertEqual(r.payments(self.root,self.profile,self.child)['history'][0],self.initial_paid_row)
        if (self.root/self.directory/'producer-repair-phase.json').exists():
            self.assertEqual((self.root/r.payment_path(self.profile,self.child)).read_bytes(),self.original_paid_bytes)


    def workflow(self, profile, parent, directory, **options):
        """Author the exact boundary data; no Chrome, gateway or provider."""
        self.workflow_calls.append(options)
        attempt = Path(directory)/('attempt-authored-'+str(len(self.workflow_calls)))
        argv=['node','swissknife/scripts/run-visual-functional-workflow.mjs','--app',parent['app_id'],
              '--contracts',profile['appContractPath'],'--output-dir',str(attempt),'--independent-viewports']
        if len(self.workflow_calls) == 1 or len(self.workflow_calls) in getattr(self,'failure_calls',set()) or getattr(self, 'force_failure', False):
            leaf=attempt/'desktop';leaf.mkdir(parents=True)
            self.put(str((leaf/'failure-dom.json').relative_to(self.root)), {'AUTHORED':True,'text':'Storage failure; no confirmation exists'})
            self.put(str((leaf/'failure-owner-responses.json').relative_to(self.root)), {'AUTHORED':True,'requests':[]})
            failure={'schema':'swissknife.visual-functional-workflow-failure.v1','app_id':parent['app_id'],
                     'error':{'code':'WORKFLOW_ERROR','message':'AUTHORED missing confirmation after rejected tool',
                              'details':{'context':{'phase':'primary_result','step':8,'operation':'wait_for','selector':'[data-gateway-confirm="authored"]'}}},
                     'phase':'primary_result','step':8,'source_sha256':{n:sha((self.root/n).read_bytes())for n in self.paths},
                     'scenario_sha256':sha((self.root/self.paths[1]).read_bytes()),
                     'artifacts':[r.ref(self.root,str((leaf/n).relative_to(self.root)))for n in ['failure-dom.json','failure-owner-responses.json']],
                     'actual_desktop':True,'functional_acceptance':'not_evaluated','work_complete':False,'completion_authority':False}
            failure_name=str((leaf/'failure.json').relative_to(self.root));self.put(failure_name,failure)
            check={'argv':argv,'exit_code':1,'stdout_sha256':sha(b''),'stderr_sha256':sha(b'AUTHORED producer refusal'),
                   'stdout_bytes':0,'stderr_bytes':len(b'AUTHORED producer refusal'),'output_tail':'AUTHORED fixed producer failed'}
            error=RuntimeError('AUTHORED closed independent producer failure')
            error.producer_failure_record=r.ref(self.root,failure_name)
            error.producer_check=check
            self.failure_ref=error.producer_failure_record
            self.producer_check=check
            raise error
        report=attempt/'workflow.json'
        self.put(str(report.relative_to(self.root)), {'AUTHORED':True,'two_independent_viewports':True})
        return [report],[{'argv':argv,'exit_code':0,'output_tail':'AUTHORED fresh independent two-view result'}]

    def failure_context(self, profile, child, parent, application_ref, failure_ref, check):
        self.assertEqual(child,self.child); self.assertEqual(parent,self.parent)
        self.assertEqual(failure_ref,self.failure_ref); self.assertEqual(check,self.producer_check)
        self.assertEqual(application_ref,r.ref(self.root,self.directory+'/application.json'))
        # Worker-owned tests cover reconstruction of actual policy/catalog/trace.
        return {'schema':'swissknife.producer-failure-context.v1','AUTHORED_TRUSTED_EXTERNAL_BOUNDARY':True,
                'policy_observation':{'tool_id':'ipfs_add','kind':'server_only','approved_transports':[]},
                'constraint':'Never bypass the actual gateway or create synthetic consent.'}

    def model(self, profile_path, child, mode, files, images, output, **options):
        self.model_calls.append({'mode':mode,'files':files,'output':str(output),'options':options})
        self.assertEqual(options['remediation_payment'],(self.child,'producer_repair'))
        self.assertEqual(mode,'repair'); self.assertEqual(images,[])
        admission=self.admission('producer_repair',str(Path(output).relative_to(self.root)))
        identity=r.admit_payment(self.root,self.profile,self.spec,self.child,'producer_repair',admission)
        current={name:(self.root/name).read_bytes()for name in self.paths}
        receipt=self.model_receipt(admission,current,self.feedback_after)
        self.put_receipt(admission,receipt)
        r.finish_payment(self.root,self.profile,self.child,identity,receipt=r.ref(self.root,admission['output_path']))

    def execute(self, **overrides):
        options={'model':self.model,'workflow':self.workflow,'validate_workflow':lambda profile,parent,report:{'AUTHORED_EXTERNAL_STRICT_PRODUCER':True},
                 'apply_edits':self.apply_edits,'ensure_lease':lambda profile:None,'check_owned':self.check_owned,
                 'remember_owned':self.remember_owned,'producer_failure_context':self.failure_context}
        options.update(overrides)
        return r.execute_child(self.root,'profile.json',self.profile,self.spec,self.child,**options)


class ProducerFeedbackTests(FeedbackFixture):
    def test_exact_final_feedback_opt_in_is_bounded_and_legacy_policy_is_not_expanded(self):
        self.assertTrue(r.policy_enabled(self.profile))
        for bad in [True,0,2,-1,1.5]:
            profile=copy.deepcopy(self.profile);profile['finalRemediation']['max_paid_producer_repairs']=bad
            with self.subTest(value=bad),self.assertRaises(r.RemediationRefusal):r.policy_enabled(profile)

    def test_one_feedback_chain_keeps_initial_payment_application_deadline_and_final_acceptance_downstream(self):
        files,checks,detail=self.execute()
        self.assertEqual(len(self.model_calls),1);self.assertEqual(len(self.workflow_calls),2)
        self.assertEqual({n:(self.root/n).read_bytes()for n in self.paths},self.feedback_after)
        paid=r.payments(self.root,self.profile,self.child)
        self.assertEqual(paid['spent'],{'assessment':0,'proposal':1});self.assertFalse(paid['closed'])
        self.assertEqual(self.feedback_paid()['spent'],1)
        self.assertFalse(detail.get('completion_authority',False))
        result=r.validate_child_result(self.root,self.profile,self.spec,self.child,{'checks':checks,'detail':detail},
                                      validate_workflow=lambda *args:{'AUTHORED_EXTERNAL_STRICT_PRODUCER':True})
        self.assertFalse(result['completion_authority']);self.assertFalse(result['work_complete'])
        self.assert_preserved()

    def test_missing_failure_context_or_untyped_failure_never_admits_feedback(self):
        before=r.payments(self.root,self.profile,self.child)
        with self.assertRaisesRegex(r.RemediationRefusal,'context callback'):self.execute(producer_failure_context=None)
        self.assertEqual(len(self.model_calls),0)
        self.assertEqual(r.payments(self.root,self.profile,self.child)['spent']['proposal'],1)
        self.assertEqual(r.payments(self.root,self.profile,self.child)['spent'].get('producer_repair',0),0)
        self.assertFalse((self.root/self.directory/'source-only-result.json').exists())
        self.assert_preserved()

    def feedback_paid(self):
        return r.producer_repair_payments(self.root,self.profile,self.child)

    def claim_feedback(self, output):
        admission=self.admission('producer_repair',str(Path(output).relative_to(self.root)))
        identity=r.admit_payment(self.root,self.profile,self.spec,self.child,'producer_repair',admission)
        return admission,identity

    def test_unknown_paid_feedback_outcome_never_redispatches_or_refunds(self):
        def interrupted(profile_path,child,mode,files,images,output,**options):
            self.model_calls.append('admitted then interrupted')
            self.claim_feedback(output)
            raise TimeoutError('AUTHORED interruption after irreversible feedback admission')
        with self.assertRaises(TimeoutError):self.execute(model=interrupted)
        before=self.feedback_paid()
        # The exclusive irreversible claim, not the replaceable aggregate, owns spend.
        claim=(self.root/self.directory/'producer-repair-payments.json.claim.json').read_bytes()
        (self.root/self.directory/'producer-repair-payments.json').unlink()
        self.assertEqual(self.feedback_paid(),before)
        with self.assertRaises(Exception):self.execute(model=lambda *a,**k:self.fail('Unknown paid outcome must not dispatch again'))
        self.assertEqual((self.root/self.directory/'producer-repair-payments.json.claim.json').read_bytes(),claim)
        self.assertEqual(self.feedback_paid(),before)
        self.assertEqual(len(self.workflow_calls),1,'Do not rerun the same failing producer without a corrected source')
        self.assertEqual(r.payments(self.root,self.profile,self.child)['spent']['proposal'],1)
        self.assert_preserved()

    def test_retained_feedback_proposal_recovers_after_crash_without_second_paid_call(self):
        def interrupted_apply(root,edits,paths,**options):
            if len(self.apply_calls)==1:
                raise RuntimeError('AUTHORED interruption before feedback source publication')
            return self.apply_edits(root,edits,paths,**options)
        with self.assertRaisesRegex(RuntimeError,'before feedback source'):self.execute(apply_edits=interrupted_apply)
        self.assertEqual({n:(self.root/n).read_bytes()for n in self.paths},self.initial_after)
        retained=(self.root/self.directory/'producer-repair-proposal.json').read_bytes()
        files,checks,detail=self.execute(model=lambda *a,**k:self.fail('Retained paid proposal must be replayed'))
        self.assertEqual((self.root/self.directory/'producer-repair-proposal.json').read_bytes(),retained)
        self.assertEqual(len(self.model_calls),1);self.assertEqual(len(self.workflow_calls),2)
        self.assertEqual({n:(self.root/n).read_bytes()for n in self.paths},self.feedback_after)
        self.assertTrue(self.feedback_paid()['closed']);self.assert_preserved()

    def test_partial_feedback_application_recovers_only_remaining_cas_source(self):
        interrupted=[False]
        def partial(root,edits,paths,**options):
            if len(self.apply_calls)==1 and not interrupted[0]:
                interrupted[0]=True
                first=paths[0]
                llm.apply_validated_edits(root,[e for e in edits if e['path']==first],[first],**options)
                raise RuntimeError('AUTHORED interruption after one feedback file')
            return self.apply_edits(root,edits,paths,**options)
        with self.assertRaisesRegex(RuntimeError,'after one feedback file'):self.execute(apply_edits=partial)
        self.assertEqual((self.root/self.paths[0]).read_bytes(),self.feedback_after[self.paths[0]])
        self.assertEqual((self.root/self.paths[1]).read_bytes(),self.initial_after[self.paths[1]])
        files,checks,detail=self.execute(model=lambda *a,**k:self.fail('No duplicate native proposal on partial CAS replay'))
        self.assertEqual({n:(self.root/n).read_bytes()for n in self.paths},self.feedback_after)
        self.assertEqual(len(self.model_calls),1);self.assertEqual(self.feedback_paid()['spent'],1)
        self.assert_preserved()

    def test_foreign_source_after_failed_producer_is_preserved_and_refuses_feedback(self):
        def foreign(*args):
            value=self.failure_context(*args)
            self.put(self.paths[0],b'FOREIGN SOURCE MUST NOT BE OVERWRITTEN')
            return value
        with self.assertRaisesRegex(r.RemediationRefusal,'source changed|foreign source'):self.execute(producer_failure_context=foreign)
        self.assertEqual((self.root/self.paths[0]).read_bytes(),b'FOREIGN SOURCE MUST NOT BE OVERWRITTEN')
        self.assertEqual(len(self.model_calls),0);self.assertEqual(r.payments(self.root,self.profile,self.child)['spent']['proposal'],1)
        self.assertFalse((self.root/self.directory/'source-only-result.json').exists());self.assert_preserved()

    def test_tampered_failure_bytes_cannot_be_rebound_to_feedback(self):
        def corrupt(*args):
            value=self.failure_context(*args)
            p=self.root/self.failure_ref['path'];p.write_bytes(p.read_bytes()+b' ')
            return value
        with self.assertRaisesRegex(r.RemediationRefusal,'changed|hash|reference'):self.execute(producer_failure_context=corrupt)
        self.assertEqual(len(self.model_calls),0);self.assert_preserved()

    def test_rehashed_foreign_app_or_source_failure_never_becomes_repair_authority(self):
        for variant in ['app','source','producer_command']:
            with self.subTest(variant=variant):
                # A separate authored fixture makes each candidate an independent chain.
                other=ProducerFeedbackTests('runTest');other.setUp()
                try:
                    def forged(profile,parent,directory,**options):
                        try:return other.workflow(profile,parent,directory,**options)
                        except RuntimeError as error:
                            record=json.loads((other.root/error.producer_failure_record['path']).read_text())
                            if variant=='app':record['app_id']='foreign-app'
                            elif variant=='source':record['source_sha256'][other.paths[0]]='e'*64
                            else:error.producer_check['argv'][3]='foreign-app'
                            other.put(error.producer_failure_record['path'],record)
                            error.producer_failure_record=r.ref(other.root,error.producer_failure_record['path'])
                            other.failure_ref=error.producer_failure_record
                            raise
                    with other.assertRaisesRegex(r.RemediationRefusal,'foreign|source|argv'):other.execute(workflow=forged)
                    other.assertEqual(len(other.workflow_calls),1)
                    other.assertEqual(len(other.model_calls),0);other.assert_preserved()
                finally:other.doCleanups()

    def test_feedback_cannot_edit_gateway_to_bypass_real_consent_or_policy(self):
        gateway='swissknife/web/js/live-tool-gateway.js'
        self.put(gateway,'AUTHORED READONLY POLICY GATE')
        def forbidden(profile_path,child,mode,files,images,output,**options):
            self.model_calls.append('authored attempted policy bypass')
            admission,identity=self.claim_feedback(output)
            current={n:(self.root/n).read_bytes()for n in self.paths}
            receipt=self.model_receipt(admission,current,self.feedback_after)
            receipt['response']['edits']=[{'path':gateway,'before_sha256':sha((self.root/gateway).read_bytes()),
                                          'old':'AUTHORED READONLY POLICY GATE','new':'AUTHORED synthetic consent bypass'}]
            receipt['response_sha256']=sha(llm._json(receipt['response']).encode())
            llm.validate_model_receipt(self.root,receipt,task_id=self.child['task_id'],mode='repair',predicted_files=self.paths)
            self.fail('A protected out-of-scope edit must not validate')
        with self.assertRaisesRegex(llm.ModelAdapterError,'outside declared Predicted files'):self.execute(model=forbidden)
        self.assertEqual((self.root/gateway).read_text(),'AUTHORED READONLY POLICY GATE')
        self.assertEqual({n:(self.root/n).read_bytes()for n in self.paths},self.initial_after)
        self.assertEqual(self.feedback_paid()['spent'],1,'Refused native outcome never refunds a charged feedback call')
        self.assertFalse((self.root/self.directory/'source-only-result.json').exists());self.assert_preserved()

    def test_failed_corrected_producer_seals_one_feedback_and_never_loops_same_source(self):
        self.force_failure=True
        with self.assertRaises(Exception):self.execute()
        self.assertEqual(len(self.model_calls),1)
        self.assertEqual(len(self.workflow_calls),2)
        self.assertTrue((self.root/self.directory/'producer-repair-failed.json').exists())
        self.assertEqual(self.feedback_paid()['spent'],1)
        before={n:(self.root/n).read_bytes()for n in self.paths}
        with self.assertRaises(Exception):self.execute(model=lambda *a,**k:self.fail('Feedback bound exhausted'),
                                                       workflow=lambda *a,**k:self.fail('Corrected producer outcome already retained'))
        self.assertEqual({n:(self.root/n).read_bytes()for n in self.paths},before)
        self.assertFalse((self.root/self.directory/'source-only-result.json').exists());self.assert_preserved()

    def test_completed_child_current_controller_annex_preserves_all_old_receipt_and_paid_bytes(self):
        controllers=['scripts/swissknife_visual_functional_worker.py','scripts/swissknife_visual_functional_phase_remediation.py',
                     'scripts/swissknife_visual_functional_llm.py','config/swissknife_visual_functional_supervisor.json']
        for name in controllers:self.put(name,'AUTHORED HISTORICAL CONTROLLER '+name)
        def good_workflow(profile,parent,directory,**options):
            self.workflow_calls.append(options)
            attempt=Path(directory)/('attempt-authored-positive-'+str(len(self.workflow_calls)))
            report=attempt/'workflow.json'
            sources={n:sha((self.root/n).read_bytes())for n in [*self.paths,*controllers]}
            children=[]
            for name,width,height in [('desktop',1440,900),('mobile',390,844)]:
                child_path=attempt/name/'workflow.json'
                self.put(str(child_path.relative_to(self.root)),
                         {'schema':'swissknife.visual-functional-viewport.v1','app_id':parent['app_id'],
                          'session_id':str(uuid.uuid4()),'viewport':{'name':name,'width':width,'height':height},
                          'source_sha256':sources,'artifacts':[],'passed':True,'actual_desktop':True})
                children.append({'name':name,'report':r.ref(self.root,str(child_path.relative_to(self.root)))})
            self.put(str(report.relative_to(self.root)),
                     {'schema':'swissknife.visual-functional-workflow.v2','app_id':parent['app_id'],
                      'source_sha256':sources,'viewport_reports':children,'passed':True,'actual_desktop':True,
                      'AUTHORED_EXTERNAL_PRODUCER':True})
            return [report],[{'argv':['node','swissknife/scripts/run-visual-functional-workflow.mjs','--app',parent['app_id'],
                                     '--contracts',profile['appContractPath'],'--output-dir',str(attempt),'--independent-viewports'],
                              'exit_code':0,'output_tail':'AUTHORED fresh two-view report'}]
        files,checks,detail=self.execute(workflow=good_workflow)
        self.assertEqual(len(self.model_calls),0)
        receipt={'schema':'swissknife.visual-functional-task.v1','task_id':self.child['task_id'],'kind':self.child['kind'],
                 'task_spec_sha256':sha(json.dumps(self.child,sort_keys=True,separators=(',',':')).encode()),
                 'artifacts':[r.ref(self.root,str(p.relative_to(self.root)))for p in files], 'checks':checks,'detail':detail,
                 'work_complete':False,'completion_authority':False}
        self.put(self.directory+'/receipt.json',receipt)
        # Explicitly author the native coordinator's completed-child checkpoint.
        board=(self.root/'board.md').read_text();oldblock=r.blocks(board)[self.child['task_id']]
        completed=oldblock.replace('- Status: ready','- Status: completed')
        self.assertNotEqual(completed,oldblock)
        self.put('board.md',board.replace(oldblock,completed))
        self.original_canonical['board.md']=(self.root/'board.md').read_bytes()
        names=[self.directory+'/'+n for n in ['receipt.json','source-only-result.json','application.json',
                                             'application-intent.json','proposal.json','phase-remediation-payments.json','execution-deadline.json']]
        before={n:(self.root/n).read_bytes()for n in names}
        old_report=self.root/json.loads((self.root/self.directory/'source-only-result.json').read_text())['workflow']['path']
        self.put(controllers[0],'AUTHORED APPROVED NEW CONTROLLER')
        reports,newchecks=good_workflow(self.profile,self.parent,self.root/'runtime/tasks'/self.parent['task_id']/'verification')
        consumed=[]
        def current_controller_consumer(profile,parent,report):
            consumed.append(Path(report))
            if Path(report)==old_report:
                raise ValueError('AUTHORED old report has historical controller sources; never rebind it')
            self.assertEqual(Path(report),reports[0])
            return {'AUTHORED_EXTERNAL_STRICT_PRODUCER':True}
        with self.assertRaisesRegex(r.RemediationRefusal,'distinct fresh'):
            r.record_controller_requalification(self.root,self.profile,self.spec,self.child,receipt,old_report,checks,
                                                validate_workflow=current_controller_consumer)
        with self.assertRaisesRegex(r.RemediationRefusal,'canonical completed receipt'):
            r.record_controller_requalification(self.root,self.profile,self.spec,self.child,{**receipt,'task_id':'FOREIGN'},reports[0],newchecks,
                                                validate_workflow=current_controller_consumer)
        self.assertFalse((self.root/self.directory/'controller-requalification.json').exists())
        r.record_controller_requalification(self.root,self.profile,self.spec,self.child,receipt,reports[0],newchecks,
                                            validate_workflow=current_controller_consumer)
        annex=r.validate_controller_requalification(self.root,self.profile,self.spec,self.child,receipt,
                                                    validate_workflow=current_controller_consumer)
        self.assertNotIn(old_report,consumed)
        self.assertGreaterEqual(len(consumed),1)
        self.assertFalse(annex.get('completion_authority',False))
        for n,raw in before.items():self.assertEqual((self.root/n).read_bytes(),raw,n)
        self.assertEqual(len(self.model_calls),0);self.assert_preserved()

    def test_missing_feedback_opt_in_leaves_legacy_one_proposal_bound_unchanged(self):
        del self.profile['finalRemediation']['max_paid_producer_repairs']
        self.assertFalse(r.producer_feedback_enabled(self.profile,self.child))
        with self.assertRaisesRegex(RuntimeError,'AUTHORED closed'):self.execute()
        self.assertEqual(len(self.workflow_calls),1);self.assertEqual(len(self.model_calls),0)
        self.assertFalse((self.root/self.directory/'producer-feedback.json').exists())
        self.assertEqual(r.payments(self.root,self.profile,self.child)['spent'],{'assessment':0,'proposal':1})
        self.assert_preserved()

    def test_feedback_cannot_extend_expired_supplemental_absolute_deadline(self):
        def expired(profile_path,child,mode,files,images,output,**options):
            self.model_calls.append('AUTHORED attempted admission after deadline')
            deadline=json.loads((self.root/self.directory/'producer-repair-phase.json').read_text())['deadline_at_ms']
            with patch.object(r.time,'time',return_value=(deadline+1000)/1000):
                self.claim_feedback(output)
        with self.assertRaisesRegex(r.RemediationRefusal,'deadline|envelope|expired'):self.execute(model=expired)
        self.assertEqual(self.feedback_paid()['spent'],0)
        self.assertEqual(len(self.model_calls),1)
        self.assertEqual((self.root/self.directory/'execution-deadline.json').read_bytes(),self.original_deadline)
        self.assertFalse((self.root/self.directory/'source-only-result.json').exists());self.assert_preserved()

    def test_infrastructure_refusals_keep_their_typed_retryable_identity_without_feedback_spend(self):
        import errno
        from swissknife_visual_functional_worker import CoordinatorHold, BrowserContention, StoragePressure
        errors=[CoordinatorHold('AUTHORED owned hold'),BrowserContention('AUTHORED browser busy'),
                StoragePressure('ENOSPC',errno.ENOSPC),StoragePressure('EDQUOT',errno.EDQUOT)]
        for error in errors:
            with self.subTest(kind=type(error).__name__,message=str(error)):
                other=ProducerFeedbackTests('runTest');other.setUp()
                try:
                    def withheld(*args,**options):
                        raise error
                    with other.assertRaises(type(error))as caught:other.execute(workflow=withheld)
                    other.assertIs(caught.exception,error)
                    other.assertEqual(len(other.model_calls),0)
                    other.assertEqual(other.feedback_paid()['spent'],0)
                    other.assertFalse((other.root/other.directory/'producer-feedback-intent.json').exists())
                    other.assertFalse((other.root/other.directory/'source-only-result.json').exists())
                    other.assertEqual({n:(other.root/n).read_bytes()for n in other.paths},other.initial_after)
                    other.assert_preserved()
                finally:other.doCleanups()

    def seed_retained_initial_failure(self):
        """Real original execute/CAS, then an authored archived worker boundary."""
        options={'model':self.model,'workflow':self.workflow,'validate_workflow':lambda *a:{'AUTHORED':True},
                 'apply_edits':self.apply_edits,'ensure_lease':lambda profile:None,'check_owned':self.check_owned,
                 'remember_owned':self.remember_owned}
        with self.assertRaisesRegex(RuntimeError,'AUTHORED closed'):
            r._initial_execute_child(self.root,'profile.json',self.profile,self.spec,self.child,**options)
        name='runtime/tasks/'+self.parent['task_id']+'/execution-failures/'+uuid.uuid4().hex+'.json'
        self.put(name,{'schema':'swissknife.visual-functional-execution-failure.v1','task_id':self.parent['task_id'],
                       'stage':'workflow','error':{'code':'ValidationCommandError','message':'command exit 1: AUTHORED closed failure'},
                       'driver_failure':self.failure_ref,'work_complete':False,'completion_authority':False})
        self.retained_failure=r.ref(self.root,name)
        self.assertFalse((self.root/self.directory/'producer-repair-phase.json').exists())
        return self.retained_failure

    def test_supplement_starts_once_after_expired_original_without_refund_and_uses_one_fresh_probe(self):
        self.seed_retained_initial_failure();self.failure_calls={2}
        old_deadline=json.loads(self.original_deadline)['deadline_at_ms']
        with patch.object(r.time,'time',return_value=(old_deadline+1000)/1000):
            files,checks,detail=self.execute()
            phase=json.loads((self.root/self.directory/'producer-repair-phase.json').read_text())
            self.assertEqual(phase['created_at_ms'],old_deadline+1000)
            self.assertEqual(phase['deadline_at_ms']-phase['created_at_ms'],900000)
            self.assertEqual(r.producer_repair_remaining_seconds(self.root,self.profile,self.child),900)
            r.validate_child_result(self.root,self.profile,self.spec,self.child,{'checks':checks,'detail':detail},
                                    validate_workflow=lambda *a:{'AUTHORED_FRESH_TWO_VIEWS':True})
        self.assertEqual(len(self.workflow_calls),3,'One historical failure, one unpaid probe and one corrected producer')
        self.assertEqual(len(self.model_calls),1);self.assertEqual(self.feedback_paid()['spent'],1)
        self.assertTrue((self.root/self.directory/'producer-repair-probe.json').exists())
        self.assert_preserved()

    def test_supplement_timer_reader_never_creates_or_renews_a_phase(self):
        before={str(p.relative_to(self.root)):p.read_bytes()for p in self.root.rglob('*')if p.is_file()}
        with self.assertRaises((ValueError,OSError)):
            r.producer_repair_remaining_seconds(self.root,self.profile,self.child)
        self.assertEqual(before,{str(p.relative_to(self.root)):p.read_bytes()for p in self.root.rglob('*')if p.is_file()})
        def interrupted(profile_path,child,mode,files,images,output,**options):
            self.claim_feedback(output)
            raise TimeoutError('AUTHORED admitted feedback interrupted')
        with self.assertRaises(TimeoutError):self.execute(model=interrupted)
        path=self.root/self.directory/'producer-repair-phase.json';raw=path.read_bytes();phase=json.loads(raw)
        with patch.object(r.time,'time',return_value=(phase['deadline_at_ms']+1000)/1000):
            with self.assertRaisesRegex(r.RemediationRefusal,'exhausted|deadline'):
                r.producer_repair_remaining_seconds(self.root,self.profile,self.child)
            with self.assertRaises((ValueError,OSError)):
                self.execute(model=lambda *a,**k:self.fail('Expired phase must not dispatch'))
        self.assertEqual(path.read_bytes(),raw);self.assertEqual(self.feedback_paid()['spent'],1)
        self.assert_preserved()

    def test_writer_authority_rejects_blocked_empty_invalid_feedback_and_fully_installed_source(self):
        def before_write(root,edits,paths,**options):
            if len(self.apply_calls)==1:raise RuntimeError('AUTHORED before feedback publication')
            return self.apply_edits(root,edits,paths,**options)
        with self.assertRaisesRegex(RuntimeError,'before feedback publication'):self.execute(apply_edits=before_write)
        self.assertTrue(r.child_can_still_write(self.root,self.profile,self.child))
        output=self.root/self.directory/'producer-repair-proposal.json'
        paid_path=self.root/self.directory/'producer-repair-payments.json'
        original_paid=paid_path.read_bytes();row=json.loads(original_paid)['history'][0]
        archive=self.root/row['provider_admission']['attempt_receipt_path'];original=output.read_bytes();archived=archive.read_bytes()
        for variant in ['blocked','empty','foreign_scope']:
            with self.subTest(variant=variant):
                altered=json.loads(original)
                if variant=='blocked':altered['response'].update(decision='blocked',edits=[])
                elif variant=='empty':altered['response']['edits']=[]
                else:altered['response']['edits'][0]['path']='swissknife/web/js/live-tool-gateway.js'
                altered['response_sha256']=sha(llm._json(altered['response']).encode())
                raw=r.wire(altered)+b'\n';output.write_bytes(raw);archive.write_bytes(raw)
                paid=json.loads(original_paid);paid['history'][0]['receipt']=r.ref(self.root,str(output.relative_to(self.root)))
                paid_path.write_bytes(r.wire(paid)+b'\n')
                self.assertFalse(r.child_can_still_write(self.root,self.profile,self.child))
        output.write_bytes(original);archive.write_bytes(archived);paid_path.write_bytes(original_paid)
        from swissknife_visual_functional_worker import BrowserContention
        def no_browser(*args,**options):raise BrowserContention('AUTHORED browser unavailable after real source install')
        with self.assertRaises(BrowserContention):self.execute(workflow=no_browser,model=lambda *a,**k:self.fail('No duplicate model'))
        self.assertEqual({n:(self.root/n).read_bytes()for n in self.paths},self.feedback_after)
        self.assertFalse((self.root/self.directory/'source-only-result.json').exists())
        self.assertFalse(r.child_can_still_write(self.root,self.profile,self.child))
        self.assert_preserved()

    def test_paid_feedback_packet_reference_cannot_be_rebound(self):
        def before_write(root,edits,paths,**options):
            if len(self.apply_calls)==1:raise RuntimeError('AUTHORED before feedback publication')
            return self.apply_edits(root,edits,paths,**options)
        with self.assertRaisesRegex(RuntimeError,'before feedback publication'):self.execute(apply_edits=before_write)
        path=self.root/self.directory/'producer-repair-payments.json';value=json.loads(path.read_text())
        value['history'][0]['feedback']['sha256']='e'*64;self.put(str(path.relative_to(self.root)),value)
        with self.assertRaisesRegex(r.RemediationRefusal,'identity|feedback|changed'):
            self.execute(model=lambda *a,**k:self.fail('Foreign packet must not pay again'))
        self.assertEqual({n:(self.root/n).read_bytes()for n in self.paths},self.initial_after)
        self.assertEqual(len(self.workflow_calls),1);self.assert_preserved()

    def test_paid_supplement_deadline_cannot_be_repainted_into_new_nine_hundred_seconds(self):
        def interrupted(profile_path,child,mode,files,images,output,**options):
            self.claim_feedback(output);raise TimeoutError('AUTHORED irreversible admission')
        with self.assertRaises(TimeoutError):self.execute(model=interrupted)
        path=self.root/self.directory/'producer-repair-phase.json';value=json.loads(path.read_text())
        value['created_at_ms']+=5000;value['deadline_at_ms']+=5000
        self.put(str(path.relative_to(self.root)),value)
        with self.assertRaisesRegex(r.RemediationRefusal,'phase|deadline|claim|changed'):
            r.producer_repair_remaining_seconds(self.root,self.profile,self.child)
        self.assertEqual(self.feedback_paid()['spent'],1);self.assert_preserved()


if __name__=='__main__':
    unittest.main()
