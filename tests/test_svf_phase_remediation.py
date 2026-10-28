"""Finite authored RAM admission fixtures; no browser/provider/live acceptance."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(os.environ.get('SVF_FOUNDATION_REPOSITORY_ROOT', str(Path(__file__).resolve().parents[1])))
STAGE = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(STAGE/'scripts'), str(ROOT/'scripts'), str(ROOT/'tests'), str(ROOT/'external/ipfs_accelerate')]
import swissknife_visual_functional_phase_remediation as r
import swissknife_visual_functional_phase_budget as b
import swissknife_visual_functional_review_recheck as fence
import test_swissknife_visual_functional_phase_budget as shape


class PhaseRemediationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir='/dev/shm'); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.addCleanup(patch.stopall)
        self.f = shape.PhaseBudgetTests('runTest')
        # Fixture constructor has no external actions; force all of its files to RAM.
        self.f.root = self.root
        self.f.task = {'task_id':'SVF-123', 'app_id':'notes', 'kind':'verify', 'goal_id':'SVF-G001',
            'status':'ready', 'dependencies':['SVF-001'], 'acceptance':'Original acceptance unchanged.',
            'edit_paths':['swissknife/web/js/main-simple.js','swissknife/test/e2e/functional-workflows/notes.json'],
            'context_paths':[], 'execution_inputs':['swissknife/web/js/main-simple.js'],
            'timeout_seconds':1800, 'execution_command':['python3',r.WORKER,'--task-id','SVF-123'],
            'execution_validation':['python3',r.WORKER,'--validate','--task-id','SVF-123']}
        self.task = self.f.task; self.f.base=b.directory(self.root,self.task);self.f.base.mkdir(parents=True)
        self.f.attempt=self.f.base/'verification/attempt-one';self.f.attempt.mkdir(parents=True)
        self.f.image=self.f.attempt/'desktop.png';self.f.image.write_bytes(b'\x89PNG\r\n\x1a\nAUTHORED fixture')
        self.f.review=self.f.attempt/'visual-review.json';self.f.review.write_text(json.dumps(self.f.receipt('review')))
        self.f.ref=b._ref(self.root,self.f.review);self.f.hashes={};self.f.journal=self.f.base/'required-phase-repair-budget.json'
        self.profile={'runtimeRoot':'data/agent_supervisor/swissknife_visual_functional','taskSpecPath':'tasks.json',
                      'todoPath':'board.md','objectivePath':'goals.md',
                      'phaseRemediation':{'schema':r.SCHEMA,'enabled':True,'max_originals':45,'max_children_per_phase':1,
                        'max_paid_assessments':1,'max_paid_proposals':1,'child_timeout_seconds':3600}}
        self.f.put('swissknife/web/js/main-simple.js','ORIGINAL app source')
        self.f.put('swissknife/test/e2e/functional-workflows/notes.json','{}')
        tasks=[self.task,*[{'task_id':identity,'kind':'verify','app_id':app,'goal_id':'SVF-G001',
                         'dependencies':[],'status':'ready','edit_paths':[]}for identity,app in r.ORIGINAL_APPS.items() if identity!=self.task['task_id']],
               {'task_id':'SVF-001','kind':'command','goal_id':'SVF-G001','dependencies':[],'status':'completed',
                'acceptance':'Historical accepted command','timeout_seconds':60}]
        self.spec={'tasks':tasks,'goals':[{'goal_id':'SVF-G001','title':'Original goal'}]}
        self.f.put('tasks.json',json.dumps(self.spec,indent=2)+'\n')
        self.completed='## SVF-001 Historical completed task\n\n- Status: completed\n- Goal id: SVF-G001\n- Depends on: none\n- Receipt: IMMUTABLE ORIGINAL RECEIPT\n\n'
        board=self.completed+''.join('## '+t['task_id']+' '+t['app_id']+'\n\n- Status: ready\n- Goal id: SVF-G001\n- Depends on: '+(', '.join(t['dependencies'])or'none')+'\n\n'for t in tasks if t['kind']=='verify')
        self.f.put('board.md',board);self.f.put('goals.md','ORIGINAL goal heap')
        for _ in range(6): b.admit(self.root,self.task,self.f.ref,{})
        with self.assertRaises(b.PhaseRepairBudgetExhausted) as raised:b.admit(self.root,self.task,self.f.ref,{})
        fence.remember_exhaustion(self.root,self.profile,self.task,raised.exception.record)
        self.phase_before=self.f.journal.read_bytes();self.before_board=(self.root/'board.md').read_bytes()
        self.before_spec=(self.root/'tasks.json').read_bytes()
        self.authority=lambda:{'lease_id':'authored-owned-fixture-lease'}
        # Admission-state tests isolate the current V2 producer guard; separate
        # joined-V2 vectors below exercise that real guard without a provider.
        patch.object(r, '_validate_current_failed_phase', return_value={'authored_state_machine_fixture_only':True}).start()

    def plan(self):return r.propose(self.root,self.profile,self.task['task_id'])

    def test_plan_preserves_all_completed_literals_and_parent_acceptance_deadline(self):
        p=self.plan();before=json.loads(self.before_spec);after=json.loads(p['after']['tasks.json'])
        old=next(t for t in before['tasks']if t['task_id']=='SVF-123');new=next(t for t in after['tasks']if t['task_id']=='SVF-123')
        self.assertEqual(new,{**old,'dependencies':[*old['dependencies'],p['child']['task_id']]})
        self.assertIn(self.completed,p['after']['board.md']);self.assertEqual(self.f.journal.read_bytes(),self.phase_before)
        self.assertEqual(len(after['tasks']),47);self.assertEqual(p['child']['kind'],r.KIND)
        self.assertNotIn('semantic_recovery_command',p['child']);self.assertEqual(p['child']['phase_remediation']['max_paid_proposals'],1)

    def test_stale_gap_defers_to_normal_original_verification(self):
        self.f.put('swissknife/web/js/main-simple.js','REAL new source')
        with self.assertRaisesRegex(r.RemediationRefusal,'stale gap'):self.plan()
        self.assertEqual(self.f.journal.read_bytes(),self.phase_before)

    def test_authentic_receipt_tamper_is_refused(self):
        self.f.review.write_text(self.f.review.read_text()+' ')
        with self.assertRaises(ValueError):self.plan()

    def test_native_closed_public_revision_and_cas_publish(self):
        p=self.plan();result=r.publish(self.root,self.profile,p,ensure_authority=self.authority)
        self.assertEqual(result['state'],'committed');self.assertEqual(self.f.journal.read_bytes(),self.phase_before)
        self.assertIn(self.completed,(self.root/'board.md').read_text())
        path=self.root/r._admission_directory(self.profile,p['key'])/'native-metadata-admission.json'
        native=json.loads(path.read_text());self.assertTrue(native['metadata_only']);self.assertFalse(native['execution_history_authority'])
        self.assertEqual({item['operation']for item in native['delta']['items']},{'add_task','rewire_unstarted_dependency'})
        self.assertTrue(r.publish(self.root,self.profile,p,ensure_authority=self.authority)['replayed'])

    def test_crash_after_first_projection_recovers_forward_without_reset(self):
        p=self.plan()
        def fault(point):
            if point=='after:tasks.json':raise RuntimeError('authored process crash')
        with self.assertRaises(RuntimeError):r.publish(self.root,self.profile,p,ensure_authority=self.authority,fault=fault)
        self.assertEqual((self.root/'board.md').read_bytes(),self.before_board)
        r.publish(self.root,self.profile,p,ensure_authority=self.authority)
        self.assertEqual((self.root/'board.md').read_text(),p['after']['board.md'])
        self.assertEqual(self.f.journal.read_bytes(),self.phase_before)

    def test_foreign_completed_progress_during_crash_is_preserved_and_refused(self):
        p=self.plan()
        def fault(point):
            if point=='after:tasks.json':raise RuntimeError('authored process crash')
        with self.assertRaises(RuntimeError):r.publish(self.root,self.profile,p,ensure_authority=self.authority,fault=fault)
        foreign=(self.root/'board.md').read_bytes()+b'\nFOREIGN COMPLETED HISTORY MUST STAY\n';(self.root/'board.md').write_bytes(foreign)
        with self.assertRaisesRegex(r.RemediationRefusal,'foreign canonical drift'):r.publish(self.root,self.profile,p,ensure_authority=self.authority)
        self.assertEqual((self.root/'board.md').read_bytes(),foreign)

    def test_competing_beforeimage_refused_without_plan_write(self):
        p=self.plan();(self.root/'board.md').write_bytes(self.before_board+b'\nNEW completion\n')
        with self.assertRaises(ValueError):r.publish(self.root,self.profile,p,ensure_authority=self.authority)
        self.assertEqual((self.root/'tasks.json').read_bytes(),self.before_spec)

    def test_parent_completed_or_claimed_is_not_amended(self):
        for status in ('completed','in_progress','claimed'):
            (self.root/'board.md').write_bytes(self.before_board.replace(b'## SVF-123 notes\n\n- Status: ready',('## SVF-123 notes\n\n- Status: '+status).encode()))
            with self.subTest(status=status),self.assertRaises(r.RemediationRefusal):self.plan()

    def test_no_recursion_or_unlimited_source_derived_identity(self):
        p=self.plan();self.assertEqual(r.child_id(self.task),'SVF-PHASE-R123')
        with self.assertRaises(r.RemediationRefusal):r.child_id(p['child'])
        changed={**self.task,'edit_paths':['different.js']};self.assertEqual(r.gap_key(self.profile,changed),p['key'])


    def admitted_child(self):
        p=self.plan();r.publish(self.root,self.profile,p,ensure_authority=self.authority)
        spec=json.loads((self.root/'tasks.json').read_text())
        return spec,next(t for t in spec['tasks']if t['kind']==r.KIND)

    def admission(self,child,role):
        import uuid
        identity=str(uuid.uuid4()); original=child['phase_remediation']['original_task']
        task_id=child['task_id'] if role=='proposal' else original['task_id']
        output=self.profile['runtimeRoot']+'/tasks/'+task_id+('/proposal.json' if role=='proposal' else '/verification/attempt-authored/visual-review.json')
        target=Path(output)
        images=[]
        if role=='assessment':
            for name in ('desktop','mobile'):
                path=str(target.parent/(name+'.png'));self.f.put(path,'AUTHORED two-view fixture')
                raw=(self.root/path).read_bytes();images.append({'path':path,'size_bytes':len(raw),'sha256':r.hashlib.sha256(raw).hexdigest(),'width':1,'height':1})
        return {'schema':'swissknife.visual-functional-provider-admission.v1','output_path':output,'invocation_id':identity,
            'task_id':task_id,'mode':'repair' if role=='proposal' else 'review','provider':'grok_cli','model':'grok-4.7',
            'attempt_receipt_path':str(target.parent/'model-invocations'/(target.stem+'-'+identity+'.json')),
            'source_contract_sha256':'a'*64,'prompt_sha256':'b'*64,'router_source_sha256':'c'*64,
            'input_files':[],'screenshots':images,'timeout_seconds':600,'model_context_bytes':262144 if role=='proposal' else 32768,
            'max_output_tokens':12288,'max_turns':8}

    def test_timeout_claim_cannot_reset_after_source_or_aggregate_churn(self):
        spec,child=self.admitted_child();identity=r.admit_payment(self.root,self.profile,spec,child,'proposal',self.admission(child,'proposal'))
        r.finish_payment(self.root,self.profile,child,identity,error_type='ProviderTimeout')
        self.assertEqual(r.payments(self.root,self.profile,child)['spent']['proposal'],1)
        (self.root/r.payment_path(self.profile,child)).unlink()
        self.assertEqual(r.payments(self.root,self.profile,child)['spent']['proposal'],1)
        with self.assertRaises(r.RemediationRefusal):r.admit_payment(self.root,self.profile,spec,child,'proposal',self.admission(child,'proposal'))
        self.assertEqual(self.f.journal.read_bytes(),self.phase_before)

    def test_one_stale_refresh_is_separate_and_cannot_multiply(self):
        spec,child=self.admitted_child()
        with self.assertRaises(r.RemediationRefusal):r.admit_payment(self.root,self.profile,spec,child,'assessment',self.admission(child,'assessment'))
        self.f.put('swissknife/web/js/main-simple.js','GENUINE new source makes old review stale')
        identity=r.admit_payment(self.root,self.profile,spec,child,'assessment',self.admission(child,'assessment'))
        r.finish_payment(self.root,self.profile,child,identity,error_type='ProviderTimeout')
        with self.assertRaises(r.RemediationRefusal):r.admit_payment(self.root,self.profile,spec,child,'assessment',self.admission(child,'assessment'))
        with self.assertRaises(r.RemediationRefusal):r.admit_payment(self.root,self.profile,spec,child,'proposal',self.admission(child,'proposal'))
        self.assertEqual(r.payments(self.root,self.profile,child)['spent'],{'assessment':1,'proposal':0})

    def test_compiler_claim_rejects_missing_or_mismatched_metadata_before_spend(self):
        spec,child=self.admitted_child()
        with self.assertRaises(r.RemediationRefusal):r.admit_payment(self.root,self.profile,spec,child,'proposal',{})
        admission=self.admission(child,'proposal');admission['attempt_receipt_path']='outside.json'
        with self.assertRaises(r.RemediationRefusal):r.admit_payment(self.root,self.profile,spec,child,'proposal',admission)
        self.assertEqual(r.payments(self.root,self.profile,child)['spent'],{'assessment':0,'proposal':0})

    def test_expired_campaign_never_issues_role_claim(self):
        spec,child=self.admitted_child()
        with patch.dict(os.environ,{'SVF_CAMPAIGN_DEADLINE_AT_MS':'1'}):
            with self.assertRaisesRegex(r.RemediationRefusal,'deadline'):r.admit_payment(self.root,self.profile,spec,child,'proposal',self.admission(child,'proposal'))
        self.assertEqual(r.payments(self.root,self.profile,child)['spent']['proposal'],0)

    def test_hold_created_after_first_canonical_write_stops_until_exact_recovery(self):
        plan=self.plan()
        def fault(point):
            if point=='after:tasks.json':(self.root/'HOLD').write_text('foreign owner hold')
        with self.assertRaisesRegex(r.RemediationRefusal,'HOLD'):
            r.publish(self.root,self.profile,plan,ensure_authority=self.authority,fault=fault)
        self.assertEqual((self.root/'board.md').read_bytes(),self.before_board)
        self.assertEqual((self.root/'HOLD').read_text(),'foreign owner hold')
        (self.root/'HOLD').unlink()
        r.publish(self.root,self.profile,plan,ensure_authority=self.authority)
        self.assertEqual((self.root/'board.md').read_text(),plan['after']['board.md'])

    def test_scoped_gap_refusal_does_not_block_independent_cycle(self):
        # A malformed local phase is diagnostic, not a lane-wide authority failure.
        self.f.journal.write_text('{malformed')
        with patch.object(r,'no_hold_or_activity'),patch.object(r,'authority_fence'):
            result=r.between_cycles(self.root,self.profile,ensure_authority=self.authority)
        self.assertEqual(result['state'],'idle')
        report=r.parse(r.read(self.root,r.base(self.profile)+'/gap-refusals.json'))
        self.assertEqual(report['scope_refusals'][0]['task_id'],'SVF-123')
        self.assertEqual((self.root/'board.md').read_bytes(),self.before_board)

    def test_enabled_preflight_only_is_nonmutating_even_under_hold_and_pending(self):
        module=importlib.util.spec_from_file_location("r20_candidate_supervisor",STAGE/"scripts/swissknife_visual_functional_supervisor.py")
        supervisor=importlib.util.module_from_spec(module);module.loader.exec_module(supervisor)
        (self.root/'HOLD').write_text('owned maintenance hold')
        before={str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        with patch.object(supervisor,'__file__',str(self.root/'scripts/entry.py')),patch.object(supervisor,'load_profile',return_value=self.profile),\
             patch.object(supervisor,'preflight',side_effect=supervisor.PreflightError('operator hold is active')),\
             patch.object(r,'recover_pending',side_effect=AssertionError('must not recover')),\
             patch.object(r,'between_cycles',side_effect=AssertionError('must not callback')),\
             patch.object(r,'native_prepare',side_effect=AssertionError('must not initialize native projection')):
            with self.assertRaisesRegex(supervisor.PreflightError,'hold'):supervisor.main(['--preflight-only'])
        after={str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before,after)
        (self.root/'HOLD').unlink();plan=self.plan()
        def crash(point):
            if point=='after:tasks.json':raise RuntimeError('process died')
        with self.assertRaises(RuntimeError):r.publish(self.root,self.profile,plan,ensure_authority=self.authority,fault=crash)
        before={str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        with patch.object(supervisor,'__file__',str(self.root/'scripts/entry.py')),patch.object(supervisor,'load_profile',return_value=self.profile),\
             patch.object(r,'recover_pending',side_effect=AssertionError('readonly must not recover')):
            with self.assertRaisesRegex(supervisor.PreflightError,'pending authenticated'):supervisor.main(['--preflight-only'])
        self.assertEqual(before,{str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_normal_restart_rolls_forward_pending_before_consistency_preflight(self):
        module=importlib.util.spec_from_file_location("r20_candidate_supervisor",STAGE/"scripts/swissknife_visual_functional_supervisor.py")
        supervisor=importlib.util.module_from_spec(module);module.loader.exec_module(supervisor)
        plan=self.plan()
        def crash(point):
            if point=='after:tasks.json':raise RuntimeError('process died')
        with self.assertRaises(RuntimeError):r.publish(self.root,self.profile,plan,ensure_authority=self.authority,fault=crash)
        calls=[]
        def consistency(root,profile):
            calls.append('preflight')
            self.assertEqual((root/'board.md').read_text(),plan['after']['board.md'])
            self.assertEqual((root/'tasks.json').read_text(),plan['after']['tasks.json'])
            self.assertIn(self.completed,(root/'board.md').read_text())
            return {'ok':True}
        def serve(argv,*,between_cycles=None):
            self.assertEqual(calls,['preflight'])
            self.assertIsNotNone(between_cycles)
            return 0
        import ipfs_accelerate_py.agent_supervisor.rescue.lane_resume as lane
        with patch.object(supervisor,'__file__',str(self.root/'scripts/entry.py')),patch.object(supervisor,'load_profile',return_value=self.profile),\
             patch.object(supervisor,'require_swissknife_checkout_lease'),patch.object(supervisor,'assert_campaign_lease',return_value={'owned':True}),\
             patch.object(supervisor,'preflight',side_effect=consistency),patch.object(supervisor,'service_route_availability',return_value={}),\
             patch.object(r,'assert_controller_pins'),patch.object(r,'no_hold_or_activity'),\
             patch('lift_ipfs_accelerate_bootstrap.bootstrap_ipfs_accelerate'),patch.object(lane,'serve',side_effect=serve),patch.dict(os.environ,{},clear=False):
            os.environ.pop('SVF_CAMPAIGN_DEADLINE_AT_MS',None)
            self.assertEqual(supervisor.main(['--implement','--no-ephemeral-worktree','--no-worktree-reconciliation']),0)
        self.assertEqual(self.f.journal.read_bytes(),self.phase_before)

    def test_hard_crash_after_paid_archive_replays_exact_uuid_without_second_claim(self):
        import swissknife_visual_functional_llm as llm
        spec,child=self.admitted_child();admission=self.admission(child,'proposal')
        identity=r.admit_payment(self.root,self.profile,spec,child,'proposal',admission)
        receipt=self.f.receipt('repair','needs_changes')
        receipt.update({key:value for key,value in admission.items() if key not in {'schema','output_path'}})
        path=child['edit_paths'][0];before=(self.root/path).read_text()
        receipt['response'].update(task_id=child['task_id'],edits=[{'path':path,'before_sha256':r.ref(self.root,path)['sha256'],'old':before,'new':before+' real repair'}])
        receipt['response_sha256']=r.hashlib.sha256(llm._json(receipt['response']).encode()).hexdigest()
        r.atomic(self.root,admission['attempt_receipt_path'],r.wire(receipt)+b'\n',exclusive=True)
        output=self.root/admission['output_path']
        # Exact archived successful provider attempt exists; wrapper/aggregate
        # finishing was interrupted. Recovery cannot invoke a provider.
        self.assertFalse(output.exists())
        self.assertTrue(r.recover_payment(self.root,self.profile,child,'proposal',output))
        paid=r.payments(self.root,self.profile,child)
        self.assertEqual(paid['spent'],{'assessment':0,'proposal':1});self.assertEqual(paid['history'][0]['state'],'returned')
        self.assertEqual(paid['history'][0]['admission_id'],identity)
        self.assertTrue(r.recover_payment(self.root,self.profile,child,'proposal',output))
        with self.assertRaises(r.RemediationRefusal):r.admit_payment(self.root,self.profile,spec,child,'proposal',self.admission(child,'proposal'))

    def test_issued_claim_without_exact_archive_never_guesses_or_dispatches(self):
        spec,child=self.admitted_child();admission=self.admission(child,'proposal')
        r.admit_payment(self.root,self.profile,spec,child,'proposal',admission)
        with self.assertRaisesRegex(r.RemediationRefusal,'exact invocation outcome'):
            r.recover_payment(self.root,self.profile,child,'proposal',self.root/admission['output_path'])
        self.assertEqual(r.payments(self.root,self.profile,child)['spent']['proposal'],1)

    def test_finite_allowlist_cannot_be_replaced_by_another_45_verifiers(self):
        changed=copy.deepcopy(self.spec);changed['tasks'][1]['app_id']='unapproved-app'
        with self.assertRaisesRegex(r.RemediationRefusal,'allowlist'):r.originals(changed)
        self.assertEqual(len(r.ORIGINAL_APPS),45)

    def test_independent_ready_writer_defers_but_descendant_never_deadlocks(self):
        writer={'task_id':'SVF-800','kind':'repair','app_id':'writer','goal_id':'SVF-G001','status':'ready',
                'dependencies':['SVF-001'],'edit_paths':['swissknife/web/js/main-simple.js']}
        spec=copy.deepcopy(self.spec);spec['tasks'].append(writer)
        board=self.before_board.decode()+'## SVF-800 Independent source writer\n\n- Status: ready\n- Goal id: SVF-G001\n- Depends on: SVF-001\n'
        (self.root/'tasks.json').write_text(json.dumps(spec,indent=2)+'\n');(self.root/'board.md').write_text(board)
        with self.assertRaisesRegex(r.RemediationRefusal,'independently eligible source writers'):self.plan()
        spec['tasks'][-1]['dependencies']=['SVF-123']
        (self.root/'tasks.json').write_text(json.dumps(spec,indent=2)+'\n')
        self.assertEqual(r.source_writer_deferrals(self.root,self.profile,spec,board,self.task),[])
        self.assertEqual(self.plan()['parent'],'SVF-123')

    def test_foreign_dangling_hold_prevents_any_admission(self):
        (self.root/'HOLD').symlink_to(self.root/'absent-foreign-owner')
        with self.assertRaisesRegex(r.RemediationRefusal,'HOLD'):r.no_hold_or_activity(self.root,self.profile)
        self.assertEqual((self.root/'tasks.json').read_bytes(),self.before_spec)


class CurrentV2GapGuardTests(unittest.TestCase):
    def setUp(self):
        import test_svf_final_viewport_coverage as shapes
        import swissknife_visual_functional_worker as actual_worker
        self.tmp=tempfile.TemporaryDirectory(dir='/dev/shm');self.addCleanup(self.tmp.cleanup);self.addCleanup(patch.stopall)
        self.root=Path(self.tmp.name);self.f=shapes.Fixture(self.root);self.profile=self.f.profile
        patch.object(shapes.final,'_node_source_snapshot',side_effect=self.f.source_vector).start()
        patch.object(actual_worker,'ROOT',self.root).start()
        self.g=self.f.group();self.task={**self.g['task'],'kind':'verify','edit_paths':['swissknife/web/js/app-0.js']}
        self.g['task']=self.task;self.f.persist(self.g);self.f.review(self.g,'needs_changes')
        self.review=self.g['review'];reference=b._ref(self.root,self.review)
        for _ in range(6):b.admit(self.root,self.task,reference,{})
        with self.assertRaises(b.PhaseRepairBudgetExhausted)as raised:b.admit(self.root,self.task,reference,{})
        fence.remember_exhaustion(self.root,self.profile,self.task,raised.exception.record)

    def test_genuine_joined_current_v2_failed_phase_qualifies(self):
        gap=r.qualify_gap(self.root,self.profile,self.task)
        self.assertEqual(gap['spent'],6);self.assertEqual(gap['failed_review']['path'],str(self.review.relative_to(self.root)))

    def test_rebinding_fence_hash_cannot_make_old_producer_current(self):
        (self.root/'swissknife/web/js/app-0.js').write_text('GENUINE changed application')
        name=fence._path(self.root,self.task);value=json.loads(name.read_text())
        value['source_contract']=fence._source_contract(self.root,self.profile,self.task);name.write_text(json.dumps(value))
        with self.assertRaises(ValueError):r.qualify_gap(self.root,self.profile,self.task)

    def test_swapped_raw_result_image_cannot_authorize_child(self):
        image=self.root/self.g['children'][0]['result_screenshot']['path'];raw=image.read_bytes();image.write_bytes(raw[:-1]+b'x')
        with self.assertRaises(ValueError):r.qualify_gap(self.root,self.profile,self.task)


class ProcActivityAdmissionTests(unittest.TestCase):
    """Authored proc rows; never inspect real processes or signal anything."""
    class Process:
        def __init__(self,pid,argv,cwd,*,uid=None,argv_error=None,cwd_error=None,cgroup='0::/campaign.service\n',cgroup_error=None):
            self.name=str(pid);self.argv=argv;self.cwd=cwd;self.uid=os.getuid()if uid is None else uid
            self.argv_error=argv_error;self.cwd_error=cwd_error;self.argv_reads=0;self.cwd_reads=0
            self.cgroup=cgroup;self.cgroup_error=cgroup_error;self.cgroup_reads=0
        def stat(self):
            from types import SimpleNamespace
            return SimpleNamespace(st_uid=self.uid)
        def __truediv__(self,key):
            owner=self
            class Leaf:
                def read_bytes(self):
                    if key=='cgroup':
                        owner.cgroup_reads+=1
                        if owner.cgroup_error:raise owner.cgroup_error
                        return owner.cgroup.encode()
                    assert key=='cmdline';owner.argv_reads+=1
                    if owner.argv_error:raise owner.argv_error
                    return b'\0'.join(value.encode()for value in owner.argv)+b'\0'
                def resolve(self):
                    assert key=='cwd';owner.cwd_reads+=1
                    if owner.cwd_error:raise owner.cwd_error
                    return Path(owner.cwd)
            return Leaf()

    def observe(self,rows,*,own_cgroup_error=None):
        actual_path=Path
        class Proc:
            def iterdir(self):return iter(rows)
        class OwnGroup:
            def read_bytes(self):
                if own_cgroup_error:raise own_cgroup_error
                return b'0::/campaign.service\n'
        with tempfile.TemporaryDirectory(dir='/dev/shm')as folder:
            root=actual_path(folder)
            # Relevant process ownership is authored explicitly per vector.
            for row in rows:
                if row.cwd=='CHECKOUT':row.cwd=root
            with patch.object(r,'Path',side_effect=lambda value:Proc()if str(value)=='/proc'else OwnGroup()if str(value)=='/proc/self/cgroup'else actual_path(value)):
                return r.no_hold_or_activity(root,{'runtimeRoot':'runtime'})

    def test_irrelevant_same_uid_nondumpable_daemon_never_reads_cwd(self):
        daemon=self.Process(6595,['(sd-pam)'],'CHECKOUT',cwd_error=PermissionError('authored protected daemon cwd'))
        self.observe([daemon]);self.assertEqual(daemon.argv_reads,1);self.assertEqual(daemon.cwd_reads,0)

    def test_relevant_uninspectable_grok_browser_and_worker_refuse_boundedly(self):
        for argv in [['/opt/grok/bin/grok','--model','grok-4.7'],['/opt/google/chrome/chrome','--headless'],['python3',r.WORKER,'--task-id','SVF-443']]:
            with self.subTest(argv=argv):
                proc=self.Process(7001,argv,'CHECKOUT',cwd_error=PermissionError('PRIVATE argv/cwd text'))
                with self.assertRaisesRegex(r.RemediationRefusal,'possible active process pid=7001')as raised:self.observe([proc])
                self.assertEqual(proc.cwd_reads,1);self.assertLess(len(str(raised.exception)),140);self.assertNotIn('PRIVATE',str(raised.exception))

    def test_active_campaign_candidate_still_refuses(self):
        proc=self.Process(7002,['grok','--model','grok-4.7'],'CHECKOUT')
        with self.assertRaisesRegex(r.RemediationRefusal,'active campaign'):self.observe([proc])
        self.assertEqual(proc.cwd_reads,1)

    def test_inspectable_unrelated_active_candidate_does_not_claim_campaign(self):
        proc=self.Process(7003,['grok','--model','grok-4.7'],'/tmp/unrelated-checkout')
        self.observe([proc]);self.assertEqual(proc.cwd_reads,1)

    def test_other_uid_and_current_pid_remain_uninspected(self):
        other=self.Process(7004,['grok'],'CHECKOUT',uid=os.getuid()+1,cwd_error=PermissionError())
        own=self.Process(os.getpid(),['grok'],'CHECKOUT',cwd_error=PermissionError())
        self.observe([other,own]);self.assertEqual(other.argv_reads+other.cwd_reads+own.argv_reads+own.cwd_reads,0)

    def test_unreadable_cmdline_is_not_silently_admitted(self):
        proc=self.Process(7005,[],'CHECKOUT',argv_error=PermissionError('private'))
        with self.assertRaisesRegex(r.RemediationRefusal,'pid=7005'):self.observe([proc])
        self.assertEqual(proc.cwd_reads,0)

    def test_gone_process_races_remain_safe_to_skip(self):
        gone_argv=self.Process(7006,['grok'],'CHECKOUT',argv_error=FileNotFoundError())
        gone_cwd=self.Process(7007,['grok'],'CHECKOUT',cwd_error=ProcessLookupError())
        self.observe([gone_argv,gone_cwd]);self.assertEqual(gone_argv.cwd_reads,0);self.assertEqual(gone_cwd.cwd_reads,1)


class ControllerCgroupActivityTests(ProcActivityAdmissionTests):
    def test_foreign_interactive_grok_same_checkout_is_not_campaign(self):
        proc=self.Process(1594170,['grok','--resume','unrelated-chat'],'CHECKOUT',cgroup='0::/unrelated-chat.scope\n',cwd_error=PermissionError('must not inspect foreign cwd'))
        self.observe([proc]);self.assertEqual(proc.cgroup_reads,1);self.assertEqual(proc.cwd_reads,0)

    def test_own_group_grok_browser_worker_and_descendants_still_refuse(self):
        for argv in [['grok'],['/opt/chrome/chrome'],['python3',r.WORKER]]:
            for group in ['0::/campaign.service\n','0::/campaign.service/child.scope\n']:
                with self.subTest(argv=argv,group=group):
                    proc=self.Process(7100,argv,'CHECKOUT',cgroup=group)
                    with self.assertRaisesRegex(r.RemediationRefusal,'active campaign'):self.observe([proc])

    def test_similar_service_name_is_foreign_not_a_path_prefix_match(self):
        proc=self.Process(7101,['grok'],'CHECKOUT',cgroup='0::/campaign.service-other\n',cwd_error=PermissionError())
        self.observe([proc]);self.assertEqual(proc.cwd_reads,0)

    def test_unavailable_current_controller_group_is_not_a_candidate_exit_race(self):
        for error in [FileNotFoundError(),ProcessLookupError(),PermissionError()]:
            with self.subTest(error=type(error).__name__):
                proc=self.Process(7103,['grok'],'CHECKOUT')
                with self.assertRaisesRegex(r.RemediationRefusal,'current supervisor cgroup'):
                    self.observe([proc],own_cgroup_error=error)
                self.assertEqual(proc.cgroup_reads,0);self.assertEqual(proc.cwd_reads,0)

    def test_unavailable_candidate_cgroup_refuses_before_cwd(self):
        for error in [PermissionError('private'),None]:
            proc=self.Process(7102,['grok'],'CHECKOUT',cgroup='',cgroup_error=error)
            with self.assertRaises(r.RemediationRefusal):self.observe([proc])
            self.assertEqual(proc.cwd_reads,0)


if __name__=='__main__':unittest.main()
