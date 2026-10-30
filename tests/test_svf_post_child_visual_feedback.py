"""Authored RAM streaming-proof, versioned-annex, unpaid-resume and keyboard-normalization tests.

No browser, provider, service or live mutation. Real hash/metadata CAS and paid
admission/source application logic remain under the staged phase implementation;
only explicitly authored external observation boundaries may be substituted.
"""
from pathlib import Path
import copy
import hashlib
import json
import os
import sys
import tempfile
import unittest
import uuid
import zipfile
from unittest.mock import patch

ROOT=Path(os.environ.get('SVF_FOUNDATION_REPOSITORY_ROOT',Path(__file__).resolve().parents[1]))
STAGE=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(STAGE/'scripts'),str(ROOT/'scripts'),str(ROOT/'tests'),str(ROOT/'external/ipfs_accelerate')]
import swissknife_visual_functional_phase_remediation as r


def sha(value):return hashlib.sha256(value).hexdigest()


class StreamingProofArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir='/dev/shm');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.path=self.root/'evidence/trace.zip';self.path.parent.mkdir()
        with zipfile.ZipFile(self.path,'w',compression=zipfile.ZIP_STORED)as archive:
            archive.writestr('authored-large-proof.bin',b'A'*(9*1024*1024))
        self.value={'path':str(self.path.relative_to(self.root)),'sha256':sha(self.path.read_bytes()),'bytes':self.path.stat().st_size}
        self.assertGreater(self.value['bytes'],8*1024*1024)

    def test_valid_zip_larger_than_json_cap_streams_exactly_without_broadening_json(self):
        before=self.path.stat();result=r._check_proof_artifact(self.root,self.value)
        self.assertEqual(result,self.value);self.assertEqual(self.path.stat().st_ino,before.st_ino)
        self.assertEqual(sha(self.path.read_bytes()),self.value['sha256'])
        large=self.root/'large.json';large.write_bytes(b'{"authored":"'+b'B'*(9*1024*1024)+b'"}')
        with self.assertRaisesRegex(r.RemediationRefusal,'bound'):
            r._check_proof_artifact(self.root,{'path':'large.json','sha256':sha(large.read_bytes()),'bytes':large.stat().st_size})

    def test_wrong_hash_size_signature_and_bool_size_refuse(self):
        for changes in [{'sha256':'e'*64},{'bytes':self.value['bytes']-1},{'bytes':True}]:
            with self.subTest(changes=changes),self.assertRaises(r.RemediationRefusal):
                r._check_proof_artifact(self.root,{**self.value,**changes})
        false_zip=self.root/'false.zip';false_zip.write_bytes(b'not a ZIP file')
        with self.assertRaisesRegex(r.RemediationRefusal,'signature'):
            r._check_proof_artifact(self.root,{'path':'false.zip','sha256':sha(false_zip.read_bytes()),'bytes':false_zip.stat().st_size})

    def test_separate_binary_cap_rejects_sparse_overflow_before_read(self):
        oversized=self.root/'overflow.zip';oversized.write_bytes(b'PK\x03\x04')
        with oversized.open('r+b')as handle:handle.truncate(r.MAX_PROOF_ZIP_BYTES+1)
        with patch.object(r.os,'fdopen',side_effect=AssertionError('Over-bound artifact must refuse before opening its stream')):
            with self.assertRaisesRegex(r.RemediationRefusal,'bound'):
                r._check_proof_artifact(self.root,{'path':'overflow.zip','sha256':'a'*64,'bytes':r.MAX_PROOF_ZIP_BYTES+1})
        self.assertEqual(oversized.stat().st_size,r.MAX_PROOF_ZIP_BYTES+1)

    def test_identical_bytes_replacement_during_stream_is_detected_by_inode(self):
        original=r.os.fdopen;raw=self.path.read_bytes();before=self.path.stat().st_ino;replaced=[];owner=self
        class RacingStream:
            def __init__(self,handle):self.handle=handle
            def __enter__(self):return self
            def __exit__(self,*args):return self.handle.__exit__(*args)
            def fileno(self):return self.handle.fileno()
            def read(self,amount):
                if not replaced:
                    replacement=owner.path.with_name('replacement.zip');replacement.write_bytes(raw);os.replace(replacement,owner.path);replaced.append(True)
                return self.handle.read(amount)
        def fdopen(fd,mode,*args,**kwargs):
            handle=original(fd,mode,*args,**kwargs)
            return RacingStream(handle)if mode=='rb'else handle
        with patch.object(r.os,'fdopen',side_effect=fdopen):
            with self.assertRaisesRegex(r.RemediationRefusal,'changed'):
                r._check_proof_artifact(self.root,self.value)
        self.assertTrue(replaced);self.assertNotEqual(self.path.stat().st_ino,before)
        self.assertEqual(sha(self.path.read_bytes()),self.value['sha256'],'Race must be detected even when replacement bytes match')

    def test_symlink_and_reference_shape_cannot_bypass_stream_boundary(self):
        other=self.root/'alias.zip';other.symlink_to(self.path)
        with self.assertRaises(r.RemediationRefusal):r._check_proof_artifact(self.root,{**self.value,'path':'alias.zip'})
        with self.assertRaises(r.RemediationRefusal):r._check_proof_artifact(self.root,{**self.value,'foreign':False})


class CompletedChildFixture(unittest.TestCase):
    def setUp(self):
        import test_svf_final_producer_feedback as prior
        self.env=prior.ProducerFeedbackTests('runTest');self.env.setUp();self.addCleanup(self.env.doCleanups)
        self.root,self.profile,self.spec,self.child=self.env.root,self.env.profile,self.env.spec,self.env.child
        self.controllers=sorted(r.REQUALIFIABLE_CONTROLLERS)
        for name in self.controllers:self.env.put(name,'AUTHORED HISTORICAL CONTROLLER '+name)
        self.calls=[]
        self.files,self.checks,self.detail=self.env.execute(workflow=self.workflow)
        self.receipt={'schema':'swissknife.visual-functional-task.v1','task_id':self.child['task_id'],'kind':self.child['kind'],
                      'task_spec_sha256':sha(json.dumps(self.child,sort_keys=True,separators=(',',':')).encode()),
                      'artifacts':[r.ref(self.root,str(p.relative_to(self.root)))for p in self.files],
                      'checks':self.checks,'detail':self.detail,'work_complete':False,'completion_authority':False}
        self.env.put(self.env.directory+'/receipt.json',self.receipt)
        board=(self.root/'board.md').read_text();old=r.blocks(board)[self.child['task_id']]
        self.env.put('board.md',board.replace(old,old.replace('- Status: ready','- Status: completed')))
        self.preserved={n:(self.root/self.env.directory/n).read_bytes()for n in ['receipt.json','source-only-result.json','proposal.json','application.json','phase-remediation-payments.json','execution-deadline.json']}
        self.legacy=self.root/self.env.directory/'controller-requalification.json'
        self.legacy.write_bytes(b'{"AUTHORED":"legacy fixed annex bytes, never rewritten"}\n')
        self.legacy_raw=self.legacy.read_bytes()

    def workflow(self,profile,parent,directory,**options):
        self.calls.append(options);attempt=Path(directory)/('attempt-annex-'+str(len(self.calls)))
        sources={n:sha((self.root/n).read_bytes())for n in [*self.env.paths,*self.controllers]}
        children=[]
        for name,width,height in [('desktop',1440,900),('mobile',390,844)]:
            artifacts=[]
            if name=='mobile'and len(self.calls)==1:
                trace=attempt/name/'trace.zip';trace.parent.mkdir(parents=True,exist_ok=True)
                with zipfile.ZipFile(trace,'w',compression=zipfile.ZIP_STORED)as archive:archive.writestr('retained-body.bin',b'Z'*(9*1024*1024))
                artifacts=[{'path':str(trace.relative_to(self.root)),'sha256':sha(trace.read_bytes()),'bytes':trace.stat().st_size}]
            path=attempt/name/'workflow.json'
            self.env.put(str(path.relative_to(self.root)),{'schema':'swissknife.visual-functional-viewport.v1','app_id':parent['app_id'],
                         'session_id':str(uuid.uuid4()),'viewport':{'name':name,'width':width,'height':height},
                         'source_sha256':sources,'artifacts':artifacts,'passed':True,'actual_desktop':True})
            children.append({'name':name,'report':r.ref(self.root,str(path.relative_to(self.root)))})
        path=attempt/'workflow.json'
        self.env.put(str(path.relative_to(self.root)),{'schema':'swissknife.visual-functional-workflow.v2','app_id':parent['app_id'],
                     'source_sha256':sources,'viewport_reports':children,'artifacts':[],'passed':True,'actual_desktop':True})
        return[path],[{'argv':['node','swissknife/scripts/run-visual-functional-workflow.mjs','--app',parent['app_id'],'--contracts',profile['appContractPath'],
                              '--output-dir',str(attempt),'--independent-viewports'],'exit_code':0,'output_tail':'AUTHORED strict producer seam'}]

    def strict_current(self,profile,parent,path):
        body=json.loads(Path(path).read_text())
        self.assertEqual(body['source_sha256'],{n:sha((self.root/n).read_bytes())for n in body['source_sha256']})
        return{'AUTHORED_EXTERNAL_TWO_VIEW_BOUNDARY':True}

    def current_report(self):
        parent=r.child_contract(self.root,self.profile,self.spec,self.child)[1]
        reports,checks=self.workflow(self.profile,parent,self.root/'runtime/tasks'/parent['task_id']/'verification')
        return reports[0],checks

    def assert_old_preserved(self):
        for name,raw in self.preserved.items():self.assertEqual((self.root/self.env.directory/name).read_bytes(),raw,name)
        self.assertEqual(self.legacy.read_bytes(),self.legacy_raw)



class VersionedControllerAnnexTests(CompletedChildFixture):
    def test_new_controller_tuple_appends_second_annex_with_large_old_zip_and_preserves_first(self):
        self.env.put(self.controllers[0],'AUTHORED CONTROLLER GENERATION ONE')
        report,checks=self.current_report();first=r.record_controller_requalification(self.root,self.profile,self.spec,self.child,self.receipt,report,checks,validate_workflow=self.strict_current)
        first_raw=(self.root/first['path']).read_bytes();first_identity=r.controller_requalification_identity(self.root)
        self.assertEqual(first['path'],r.controller_requalification_path(self.profile,self.child,first_identity))
        self.env.put(self.controllers[1],'AUTHORED CONTROLLER GENERATION TWO')
        report,checks=self.current_report();second=r.record_controller_requalification(self.root,self.profile,self.spec,self.child,self.receipt,report,checks,validate_workflow=self.strict_current)
        self.assertNotEqual(first['path'],second['path']);self.assertEqual((self.root/first['path']).read_bytes(),first_raw)
        current=r.validate_controller_requalification(self.root,self.profile,self.spec,self.child,self.receipt,validate_workflow=self.strict_current)
        self.assertEqual(current['controller_identity'],r.controller_requalification_identity(self.root));self.assertFalse(current['completion_authority'])
        self.assert_old_preserved()

    def test_controller_key_shape_and_foreign_tuple_cannot_replace_current_annex(self):
        identity=r.controller_requalification_identity(self.root)
        for variant in ['key','missing','foreign']:
            bad=copy.deepcopy(identity)
            if variant=='key':bad['key']='e'*64
            elif variant=='missing':bad['controller_sha256'].pop(self.controllers[0])
            else:bad['controller_sha256']['scripts/unrelated.py']='a'*64
            with self.subTest(variant=variant),self.assertRaises(r.RemediationRefusal):r.controller_requalification_path(self.profile,self.child,bad)
        self.env.put(self.controllers[0],'AUTHORED NEW CONTROLLER')
        report,checks=self.current_report();first=r.record_controller_requalification(self.root,self.profile,self.spec,self.child,self.receipt,report,checks,validate_workflow=self.strict_current)
        prior_raw=(self.root/first['path']).read_bytes()
        self.env.put(self.controllers[1],'AUTHORED FOREIGN CURRENT GENERATION')
        newidentity=r.controller_requalification_identity(self.root);wrong=self.root/r.controller_requalification_path(self.profile,self.child,newidentity)
        wrong.parent.mkdir(parents=True,exist_ok=True);wrong.write_bytes(prior_raw)
        with self.assertRaisesRegex(r.RemediationRefusal,'rebound'):
            r.validate_controller_requalification(self.root,self.profile,self.spec,self.child,self.receipt,validate_workflow=self.strict_current)
        self.assertEqual((self.root/first['path']).read_bytes(),prior_raw);self.assert_old_preserved()


RESUME_POLICY={'schema':'swissknife.retained-proposal-resume.v1','enabled':True,'max_finals':45,
               'max_resumes_per_child':1,'max_paid_calls':0,'timeout_seconds':900}


class RetainedProposalResumeTests(unittest.TestCase):
    def setUp(self):
        import test_svf_final_producer_feedback as prior
        self.env=prior.ProducerFeedbackTests('runTest');self.env.setUp();self.addCleanup(self.env.doCleanups)
        self.root,self.profile,self.spec,self.child=self.env.root,self.env.profile,self.env.spec,self.env.child
        self.profile['retainedProposalResume']=copy.deepcopy(RESUME_POLICY)
        self.expired_now=(json.loads(self.env.original_deadline)['deadline_at_ms']+1000)/1000
        self.oldpaid=(self.root/r.payment_path(self.profile,self.child)).read_bytes()
        self.producer_calls=[];self.model_calls=[]

    def options(self,**overrides):
        values={'model':lambda *a,**k:self.fail('Unpaid retained resume cannot dispatch a model'),
                'workflow':self.producer,'validate_workflow':lambda *a:{'AUTHORED_EXTERNAL_STRICT_TWO_VIEW':True},
                'apply_edits':self.env.apply_edits,'ensure_lease':lambda *a:None,'check_owned':self.env.check_owned,
                'remember_owned':self.env.remember_owned,'producer_failure_context':self.env.failure_context}
        values.update(overrides);return values

    def producer(self,profile,parent,directory,**options):
        self.producer_calls.append(options);attempt=Path(directory)/('attempt-retained-'+str(len(self.producer_calls)));path=attempt/'workflow.json'
        self.env.put(str(path.relative_to(self.root)),{'AUTHORED':True,'two_independent_views':True})
        check={'argv':['node','swissknife/scripts/run-visual-functional-workflow.mjs','--app',parent['app_id'],'--contracts',profile['appContractPath'],
                       '--output-dir',str(attempt),'--independent-viewports'],'exit_code':0,'output_tail':'AUTHORED unpaid producer'}
        return[path],[check]

    def run_resume(self,**overrides):
        with patch.object(r.time,'time',return_value=self.expired_now):
            return r.execute_child(self.root,'profile.json',self.profile,self.spec,self.child,**self.options(**overrides))

    def assert_unchanged_originals(self):
        self.env.assert_preserved();self.assertEqual((self.root/r.payment_path(self.profile,self.child)).read_bytes(),self.oldpaid)
        self.assertEqual((self.root/self.env.directory/'execution-deadline.json').read_bytes(),self.env.original_deadline)
        self.assertEqual(r.payments(self.root,self.profile,self.child)['spent'],{'assessment':0,'proposal':1})
        self.assertEqual(self.model_calls,[])

    def test_expired_returned_proposal_resumes_exactly_once_unpaid_and_preserves_original_spend(self):
        files,checks,detail=self.run_resume()
        self.assertEqual({n:(self.root/n).read_bytes()for n in self.env.paths},self.env.initial_after)
        self.assertEqual(len(self.producer_calls),1);self.assertEqual(detail['retained_resume_paid_calls'],0)
        result=r.validate_child_result(self.root,self.profile,self.spec,self.child,{'checks':checks,'detail':detail},
                                      validate_workflow=lambda *a:{'AUTHORED_EXTERNAL_STRICT_TWO_VIEW':True})
        self.assertFalse(result['completion_authority']);self.assertFalse(result['work_complete'])
        phase=json.loads((self.root/self.env.directory/'retained-proposal-resume-phase.json').read_text())
        self.assertEqual(phase['deadline_at_ms']-phase['created_at_ms'],900000)
        self.assertEqual(phase['max_paid_calls'],0)
        again=self.run_resume(workflow=lambda *a,**k:self.fail('A closed unpaid producer must not rerun'))
        self.assertEqual(again[2]['source_only_remediation'],detail['source_only_remediation'])
        self.assert_unchanged_originals()

    def test_resume_policy_has_zero_paid_calls_and_one_nine_hundred_second_envelope(self):
        self.assertTrue(r.retained_proposal_resume_enabled(self.profile,self.child))
        for key,bad in [('max_paid_calls',1),('max_paid_calls',False),('max_resumes_per_child',2),('timeout_seconds',901),('enabled',1)]:
            profile=copy.deepcopy(self.profile);profile['retainedProposalResume'][key]=bad
            with self.subTest(key=key,bad=bad),self.assertRaises(r.RemediationRefusal):r.retained_proposal_resume_enabled(profile,self.child)
        foreign=copy.deepcopy(self.child);foreign['phase_remediation']['mode']='post-child-final-review'
        self.assertFalse(r.retained_proposal_resume_enabled(self.profile,foreign))
        self.assert_unchanged_originals()

    def test_partial_application_crash_replays_only_retained_pending_hunk_without_new_call(self):
        interrupted=[]
        def partial(root,edits,paths,**options):
            if not interrupted:
                from swissknife_visual_functional_llm import apply_validated_edits
                first=paths[0];apply_validated_edits(root,[e for e in edits if e['path']==first],[first],**options)
                interrupted.append(True);raise RuntimeError('AUTHORED interruption after one retained hunk')
            return self.env.apply_edits(root,edits,paths,**options)
        with self.assertRaisesRegex(RuntimeError,'one retained hunk'):self.run_resume(apply_edits=partial)
        self.assertEqual((self.root/self.env.paths[0]).read_bytes(),self.env.initial_after[self.env.paths[0]])
        self.assertEqual((self.root/self.env.paths[1]).read_bytes(),self.env.before[self.env.paths[1]])
        phase=(self.root/self.env.directory/'retained-proposal-resume-phase.json').read_bytes()
        self.run_resume()
        self.assertEqual((self.root/self.env.directory/'retained-proposal-resume-phase.json').read_bytes(),phase)
        self.assertEqual(len(self.producer_calls),1);self.assert_unchanged_originals()

    def test_unknown_original_proposal_outcome_or_foreign_source_never_creates_resume(self):
        for variant in ['unknown','source']:
            with self.subTest(variant=variant):
                other=RetainedProposalResumeTests('runTest');other.setUp()
                try:
                    if variant=='unknown':
                        paid=json.loads(other.oldpaid);paid['history'][0]['state']='admitted';paid['history'][0].pop('receipt',None)
                        other.env.put(r.payment_path(other.profile,other.child),paid)
                        other.oldpaid=(other.root/r.payment_path(other.profile,other.child)).read_bytes()
                    else:other.env.put(other.env.paths[0],'FOREIGN source must remain')
                    with other.assertRaises((ValueError,OSError)):other.run_resume()
                    other.assertFalse((other.root/other.env.directory/'retained-proposal-resume-phase.json').exists())
                    other.assertEqual(other.producer_calls,[])
                    if variant=='source':other.assertEqual((other.root/other.env.paths[0]).read_text(),'FOREIGN source must remain')
                    other.assertEqual((other.root/r.payment_path(other.profile,other.child)).read_bytes(),other.oldpaid)
                finally:other.doCleanups()

    def test_unknown_unpaid_producer_outcome_is_not_repeated(self):
        attempted=[]
        def lost(*args,**kwargs):attempted.append(True);raise RuntimeError('AUTHORED unpaid producer outcome unknown')
        with self.assertRaisesRegex(RuntimeError,'outcome unknown'):self.run_resume(workflow=lost)
        self.assertTrue((self.root/self.env.directory/'retained-proposal-resume-producer-claim.json').exists())
        watched=[self.root/'runtime/owned-source-hashes.json',self.root/self.env.directory/'application.json']
        before={str(path):(path.read_bytes(),path.stat().st_ino)for path in watched}
        with self.assertRaisesRegex(r.RemediationRefusal,'unknown|rerun'):
            self.run_resume(workflow=lambda *a,**k:self.fail('Unknown admitted producer cannot rerun'))
        self.assertEqual({str(path):(path.read_bytes(),path.stat().st_ino)for path in watched},before,
                         'Unknown producer reentry must not republish the ledger or application')
        self.assertEqual(len(attempted),1);self.assert_unchanged_originals()

    def test_resume_clock_reader_is_readonly_and_cannot_be_renewed_or_repainted(self):
        before={str(p.relative_to(self.root)):p.read_bytes()for p in self.root.rglob('*')if p.is_file()}
        with self.assertRaises((ValueError,OSError)):r.retained_proposal_resume_remaining_seconds(self.root,self.profile,self.child)
        self.assertEqual(before,{str(p.relative_to(self.root)):p.read_bytes()for p in self.root.rglob('*')if p.is_file()})
        def pause(*args,**kwargs):raise RuntimeError('AUTHORED stop after irreversible producer claim')
        with self.assertRaises(RuntimeError):self.run_resume(workflow=pause)
        path=self.root/self.env.directory/'retained-proposal-resume-phase.json';raw=path.read_bytes();phase=json.loads(raw)
        with patch.object(r.time,'time',return_value=(phase['deadline_at_ms']+1)/1000):
            with self.assertRaisesRegex(r.RemediationRefusal,'exhausted'):r.retained_proposal_resume_remaining_seconds(self.root,self.profile,self.child)
        self.assertEqual(path.read_bytes(),raw)
        phase['created_at_ms']+=1000;phase['deadline_at_ms']+=1000;self.env.put(str(path.relative_to(self.root)),phase)
        with self.assertRaisesRegex(r.RemediationRefusal,'anchor|changed|renewed'):
            r.retained_proposal_resume_remaining_seconds(self.root,self.profile,self.child)
        self.assert_unchanged_originals()

    def test_real_resumed_producer_failure_enters_existing_paid_feedback_without_duplicate_probe(self):
        with patch.object(r.time,'time',return_value=self.expired_now):
            files,checks,detail=r.execute_child(self.root,'profile.json',self.profile,self.spec,self.child,
                                               **self.options(workflow=self.env.workflow,model=self.env.model))
        self.assertEqual(len(self.env.workflow_calls),2,'One resumed failure and one corrected producer, no extra probe')
        self.assertEqual(len(self.env.model_calls),1)
        self.assertEqual(r.producer_repair_payments(self.root,self.profile,self.child)['spent'],1)
        self.assertFalse((self.root/self.env.directory/'producer-repair-probe.json').exists())
        self.assertEqual({n:(self.root/n).read_bytes()for n in self.env.paths},self.env.feedback_after)
        self.assert_unchanged_originals()


KEYBOARD_POLICY={'schema':'swissknife.keyboard-confirmation-normalization.v1','enabled':True,
                 'max_normalizations_per_child':1,'max_paid_calls':0,'timeout_seconds':900}
KEYBOARD_ERROR='keyboard actions need their own subsequent observed semantic result'


def keyboard_scenario(app='terminal'):
    binding=app+'.ipfs_kit_py.retrieve_content';confirm='[data-gateway-confirm="'+binding+'"]'
    semantic=lambda identity,text:{'op':'assert','requirement_id':identity,'probe':{'kind':'text','selector':'#workflow-status'},'operator':'contains','expected':text}
    return {'schema':'swissknife.visual-functional-scenario.v1','app_id':app,'fixture_scope':'authored-keyboard-proof',
            'backend_bindings':[{'binding_id':binding,'mode':'isolated_mutation','consent':'ui_required','max_output_bytes':65536}],
            'preserved_metadata':{'numeric':1,'boolean':True,'literal':'no invented receipt'},
            'phases':{'primary_result':[{'op':'click','selector':'#open-file'},{'op':'wait_for','selector':confirm,'state':'visible','timeout_ms':15000},
                        {'op':'click','selector':confirm},{'op':'press','selector':'#copy-name','key':'Enter'},
                        {'op':'wait_for','selector':confirm,'state':'visible','timeout_ms':15000},{'op':'click','selector':confirm},
                        {'op':'wait_for','selector':'#workflow-status','state':'visible','timeout_ms':15000},semantic('result_1','real bytes')],
                      'persist_reopen':[{'op':'reopen_app'},semantic('persist_reopen','retained copy')],
                      'failure_recovery':[{'op':'press','selector':'#copy-name','key':'Enter'},
                        {'op':'assert','checkpoint_id':'error_observed','probe':{'kind':'text','selector':'#file-error'},'operator':'contains','expected':'conflict'},
                        {'op':'press','selector':'#retry-name','key':'Enter'},{'op':'wait_for','selector':confirm,'state':'visible','timeout_ms':15000},
                        {'op':'click','selector':confirm},semantic('failure_recovery','retry bytes')]}}


class KeyboardNormalizationShapeTests(unittest.TestCase):
    def test_exact_two_confirmation_rows_only_and_original_semantic_binding_tree_preserved(self):
        before=keyboard_scenario();after,changes=r.normalize_keyboard_confirmations(before)
        self.assertEqual([(x['phase'],x['step_index'])for x in changes],[('primary_result',5),('failure_recovery',4)])
        self.assertEqual(after['backend_bindings'],before['backend_bindings']);self.assertEqual(after['preserved_metadata'],before['preserved_metadata'])
        self.assertEqual(after['phases']['primary_result'][2],before['phases']['primary_result'][2],'A file-click confirmation must remain a click')
        restored=copy.deepcopy(after)
        for row in changes:
            self.assertEqual(row['after'],{'op':'press','selector':row['before']['selector'],'key':'Enter'})
            restored['phases'][row['phase']][row['step_index']]=row['before']
        self.assertEqual(r.wire(restored),r.wire(before))
        with self.assertRaisesRegex(r.RemediationRefusal,'no exact'):r.normalize_keyboard_confirmations(after)

    def test_wrong_key_wait_foreign_binding_intervening_action_and_missing_semantic_refuse(self):
        base=keyboard_scenario();steps=base['phases']['primary_result'][3:]
        for variant in ['key','wait','binding','action','semantic']:
            scene=copy.deepcopy(base);scene['phases']={'primary_result':copy.deepcopy(steps)}
            if variant=='key':scene['phases']['primary_result'][0]['key']='Space'
            elif variant=='wait':scene['phases']['primary_result'][1]['state']='hidden'
            elif variant=='binding':scene['backend_bindings'][0]['consent']='not-required'
            elif variant=='action':scene['phases']['primary_result'].insert(3,{'op':'click','selector':'#different-action'})
            else:scene['phases']['primary_result']=[x for x in scene['phases']['primary_result']if'requirement_id'not in x]
            with self.subTest(variant=variant),self.assertRaisesRegex(r.RemediationRefusal,'no exact'):r.normalize_keyboard_confirmations(scene)


class KeyboardNormalizationTests(unittest.TestCase):
    def setUp(self):
        import test_svf_final_producer_feedback as prior
        self.env=prior.ProducerFeedbackTests('runTest');self.env.setUp();self.addCleanup(self.env.doCleanups)
        self.root,self.profile,self.spec,self.child=self.env.root,self.env.profile,self.env.spec,self.env.child
        self.scene_path=self.env.paths[1];self.scene=keyboard_scenario(self.child['app_id'])
        self.env.feedback_after[self.scene_path]=(json.dumps(self.scene,sort_keys=True)+'\n').encode()
        self.env.force_failure=True
        def seed_producer(profile,parent,directory,**options):
            try:return self.env.workflow(profile,parent,directory,**options)
            except RuntimeError as error:
                if len(self.env.workflow_calls)==2:
                    driver_path=self.root/error.producer_failure_record['path'];driver=json.loads(driver_path.read_text())
                    driver.update(phase='backend_proof',step=None,error={'code':'MISSING_POSTCONDITION','message':KEYBOARD_ERROR,'details':{'AUTHORED':True}})
                    self.env.put(str(driver_path.relative_to(self.root)),driver)
                    stderr=json.dumps({'error':'MISSING_POSTCONDITION','message':KEYBOARD_ERROR,'functional_acceptance':'not_evaluated'})+'\n'
                    check={**error.producer_check,'output_tail':'\n'+stderr,'stderr_bytes':len(stderr.encode()),'stderr_sha256':sha(stderr.encode())}
                    name='runtime/tasks/'+parent['task_id']+'/execution-failures/'+uuid.uuid4().hex+'.json'
                    record={'schema':'swissknife.visual-functional-execution-failure.v1','task_id':parent['task_id'],'stage':'workflow',
                            'error':{'code':'ValidationCommandError','message':'command exit 1: '+check['output_tail']},
                            'driver_failure':r.ref(self.root,str(driver_path.relative_to(self.root))), 'work_complete':False,'completion_authority':False}
                    self.env.put(name,record);error.producer_failure_record=r.ref(self.root,name);error.producer_check=check
                raise
        with self.assertRaisesRegex(RuntimeError,'AUTHORED closed'):self.env.execute(workflow=seed_producer)
        self.profile['keyboardConfirmationNormalization']=copy.deepcopy(KEYBOARD_POLICY)
        self.originals={name:(self.root/self.env.directory/name).read_bytes()for name in
                        ['proposal.json','application.json','phase-remediation-payments.json','execution-deadline.json',
                         'producer-repair-proposal.json','producer-repair-application.json','producer-repair-payments.json',
                         'producer-repair-payments.json.claim.json','producer-repair-failed.json']}
        self.canonical={name:(self.root/name).read_bytes()for name in ['tasks.json','board.md','goals.md']}
        self.app_bytes=(self.root/self.env.paths[0]).read_bytes();self.app_inode=(self.root/self.env.paths[0]).stat().st_ino
        self.producer_calls=[]

    def producer(self,profile,parent,directory,**options):
        self.producer_calls.append(options);path=Path(directory)/('attempt-normalized-'+str(len(self.producer_calls)))/'workflow.json'
        self.env.put(str(path.relative_to(self.root)),{'AUTHORED':True,'two_independent_views':True})
        return[path],[{'argv':['node','swissknife/scripts/run-visual-functional-workflow.mjs','--app',parent['app_id'],'--contracts',profile['appContractPath'],
                              '--output-dir',str(path.parent),'--independent-viewports'],'exit_code':0,'output_tail':'AUTHORED normalized producer'}]

    def run_normalization(self,**overrides):
        options={'model':lambda *a,**k:self.fail('Keyboard normalization cannot admit a model'),
                 'workflow':self.producer,'validate_workflow':lambda *a:{'AUTHORED_EXTERNAL_TWO_VIEW':True},
                 'apply_edits':self.env.apply_edits,'ensure_lease':lambda *a:None,'check_owned':self.env.check_owned,'remember_owned':self.env.remember_owned}
        options.update(overrides)
        return r.execute_child(self.root,'profile.json',self.profile,self.spec,self.child,**options)

    def assert_preserved(self):
        for name,raw in self.originals.items():self.assertEqual((self.root/self.env.directory/name).read_bytes(),raw,name)
        for name,raw in self.canonical.items():self.assertEqual((self.root/name).read_bytes(),raw,name)
        self.assertEqual((self.root/self.env.paths[0]).read_bytes(),self.app_bytes)
        self.assertEqual((self.root/self.env.paths[0]).stat().st_ino,self.app_inode)
        self.assertEqual(len(self.env.model_calls),1,'Only the preexisting paid correction was authored')

    def test_exact_failed_paid_chain_normalizes_scenario_only_unpaid_and_validates_new_proof(self):
        before=(self.root/self.scene_path).read_bytes();files,checks,detail=self.run_normalization()
        expected,changes=r.normalize_keyboard_confirmations(json.loads(before));after=json.loads((self.root/self.scene_path).read_text())
        self.assertEqual(after,expected);self.assertEqual(len(changes),2);self.assertEqual(detail['normalization_paid_calls'],0)
        result=r.validate_child_result(self.root,self.profile,self.spec,self.child,{'checks':checks,'detail':detail},validate_workflow=lambda *a:{'AUTHORED_EXTERNAL_TWO_VIEW':True})
        self.assertFalse(result['completion_authority']);self.assertFalse(result['work_complete']);self.assertEqual(len(self.producer_calls),1)
        inode=(self.root/self.scene_path).stat().st_ino
        replay=self.run_normalization(workflow=lambda *a,**k:self.fail('Closed normalized producer cannot rerun'))
        self.assertEqual(replay[2]['source_only_remediation'],detail['source_only_remediation']);self.assertEqual((self.root/self.scene_path).stat().st_ino,inode)
        self.assert_preserved()

    def test_paid_or_unbounded_normalization_policy_is_rejected(self):
        self.assertTrue(r.keyboard_confirmation_normalization_enabled(self.profile,self.child))
        for key,bad in [('max_paid_calls',1),('max_paid_calls',False),('max_normalizations_per_child',2),('timeout_seconds',901),('enabled',1)]:
            profile=copy.deepcopy(self.profile);profile['keyboardConfirmationNormalization'][key]=bad
            with self.subTest(key=key,bad=bad),self.assertRaises(r.RemediationRefusal):r.keyboard_confirmation_normalization_enabled(profile,self.child)
        self.assert_preserved()

    def test_unknown_unpaid_producer_outcome_never_repeats_or_pays_again(self):
        attempted=[]
        def lost(*args,**kwargs):attempted.append(True);raise RuntimeError('AUTHORED normalized producer outcome unknown')
        with self.assertRaisesRegex(RuntimeError,'outcome unknown'):self.run_normalization(workflow=lost)
        watched=[self.root/'runtime/owned-source-hashes.json',self.root/self.env.directory/'keyboard-confirmation-normalization-application.json']
        before={str(path):(path.read_bytes(),path.stat().st_ino)for path in watched}
        with self.assertRaisesRegex(r.RemediationRefusal,'unknown|rerun'):
            self.run_normalization(workflow=lambda *a,**k:self.fail('No repeated unpaid producer'))
        self.assertEqual({str(path):(path.read_bytes(),path.stat().st_ino)for path in watched},before,
                         'Unknown producer reentry must not republish the ledger or normalization application')
        self.assertEqual(len(attempted),1);self.assertFalse((self.root/self.env.directory/'source-only-result.json').exists());self.assert_preserved()

    def test_scenario_cas_interruption_recovers_exact_candidate_without_second_model_or_producer(self):
        interrupted=[]
        def partial(root,edits,paths,**options):
            self.assertEqual(paths,[self.scene_path]);self.env.apply_edits(root,edits,paths,**options)
            if not interrupted:interrupted.append(True);raise RuntimeError('AUTHORED after normalized scenario CAS')
        with self.assertRaisesRegex(RuntimeError,'normalized scenario CAS'):self.run_normalization(apply_edits=partial)
        after=(self.root/self.scene_path).read_bytes();self.run_normalization()
        self.assertEqual((self.root/self.scene_path).read_bytes(),after);self.assertEqual(len(self.producer_calls),1);self.assert_preserved()

    def test_expired_or_repainted_normalization_clock_cannot_renew_authority(self):
        before={str(p.relative_to(self.root)):p.read_bytes()for p in self.root.rglob('*')if p.is_file()}
        with self.assertRaises((ValueError,OSError)):r.keyboard_normalization_remaining_seconds(self.root,self.profile,self.child)
        self.assertEqual(before,{str(p.relative_to(self.root)):p.read_bytes()for p in self.root.rglob('*')if p.is_file()})
        phase=r._start_keyboard_confirmation_normalization(self.root,self.profile,self.spec,self.child)
        path=self.root/self.env.directory/'keyboard-confirmation-normalization-phase.json';raw=path.read_bytes()
        with patch.object(r.time,'time',return_value=(phase['deadline_at_ms']+1000)/1000):
            with self.assertRaisesRegex(r.RemediationRefusal,'exhausted'):r.keyboard_normalization_remaining_seconds(self.root,self.profile,self.child)
        self.assertEqual(path.read_bytes(),raw)
        phase['created_at_ms']+=1000;phase['deadline_at_ms']+=1000;self.env.put(str(path.relative_to(self.root)),phase)
        with self.assertRaisesRegex(r.RemediationRefusal,'clock|renewed|rebound'):
            r.keyboard_normalization_remaining_seconds(self.root,self.profile,self.child)
        self.assert_preserved()

    def test_foreign_current_scenario_or_unknown_paid_outcome_refuses_before_any_normalization(self):
        for variant in ['source','paid','wrong_error']:
            other=KeyboardNormalizationTests('runTest');other.setUp()
            try:
                if variant=='source':other.env.put(other.scene_path,'FOREIGN scenario bytes')
                elif variant=='paid':
                    name=other.env.directory+'/producer-repair-payments.json';paid=json.loads((other.root/name).read_text())
                    paid['history'][0]['state']='admitted';paid['history'][0].pop('receipt',None);other.env.put(name,paid)
                else:
                    marker_path=other.root/other.env.directory/'producer-repair-failed.json';marker=json.loads(marker_path.read_text())
                    record_path=other.root/marker['failure_record']['path'];record=json.loads(record_path.read_text())
                    driver_path=other.root/record['driver_failure']['path'];driver=json.loads(driver_path.read_text())
                    driver['error']['message']='A different missing postcondition must never authorize normalization'
                    other.env.put(str(driver_path.relative_to(other.root)),driver);record['driver_failure']=r.ref(other.root,str(driver_path.relative_to(other.root)))
                    stderr=json.dumps({'error':'MISSING_POSTCONDITION','message':driver['error']['message']})+'\n'
                    marker['producer_check'].update(output_tail='\n'+stderr,stderr_bytes=len(stderr.encode()),stderr_sha256=sha(stderr.encode()))
                    record['error']['message']='command exit 1: '+marker['producer_check']['output_tail']
                    other.env.put(str(record_path.relative_to(other.root)),record);marker['failure_record']=r.ref(other.root,str(record_path.relative_to(other.root)))
                    other.env.put(str(marker_path.relative_to(other.root)),marker)
                with self.subTest(variant=variant),other.assertRaises((ValueError,OSError)):other.run_normalization()
                other.assertEqual(other.producer_calls,[]);other.assertFalse((other.root/other.env.directory/'keyboard-confirmation-normalization-phase.json').exists())
                if variant=='source':other.assertEqual((other.root/other.scene_path).read_text(),'FOREIGN scenario bytes')
            finally:other.doCleanups()
        self.assert_preserved()


class CompletedHistoricalFenceTests(CompletedChildFixture):
    def test_completed_child_uses_saved_native_fence_but_tampered_or_pending_child_refuses(self):
        old=self.child['phase_remediation']['original_task'];parent=self.env.parent
        review='runtime/tasks/'+parent['task_id']+'/verification/attempt-later-final/visual-review.json'
        self.env.put(review,{'schema':'swissknife.visual-functional-model-invocation.v1','task_id':parent['task_id'],
                            'mode':'review','provider':'grok_cli','model':'grok-4.7','success':True,
                            'invocation_id':str(uuid.uuid4()),'response':{'decision':'needs_changes'}})
        final=self.env.env.final
        later={'schema':final.FAILURE_SCHEMA,'task_id':parent['task_id'],'app_id':parent['app_id'],
               'task_contract':{k:v for k,v in parent.items()if k!='status'},'identity':self.env.env.identity(parent),
               'evidence':{'AUTHORED_LATER_NEGATIVE_TWO_VIEW_BOUNDARY':True},'failed_review':r.ref(self.root,review),
               'work_complete':False,'completion_authority':False}
        self.env.put(self.env.env.fence_name,later)
        original,current,intent=r.child_contract(self.root,self.profile,self.spec,self.child)
        self.assertEqual(original,old);self.assertEqual(current,parent)
        with r._mode(r.FINAL_MODE):directory=r._admission_directory(self.profile,self.child['phase_remediation']['gap']['key'])
        saved=self.root/directory/'original-fence.json';before=saved.read_bytes()
        self.assertEqual(sha(before),self.child['phase_remediation']['gap']['fence']['sha256'])
        saved.write_bytes(before+b' ')
        with self.assertRaisesRegex(r.RemediationRefusal,'saved final fence|changed|rebound'):
            r.child_contract(self.root,self.profile,self.spec,self.child)
        self.assertEqual(saved.read_bytes(),before+b' ','Foreign evidence must not be overwritten by validation')
        saved.write_bytes(before)
        board=(self.root/'board.md').read_text();block=r.blocks(board)[self.child['task_id']]
        self.env.put('board.md',board.replace(block,block.replace('- Status: completed','- Status: ready')))
        with self.assertRaises((ValueError,OSError)):r.child_contract(self.root,self.profile,self.spec,self.child)
        self.assert_old_preserved()


if __name__=='__main__':unittest.main()
