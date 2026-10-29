"""RAM-only worker/CAS integration with authored browser/provider evidence.

Real worker execution, source application, ownership, payment, V2 consumer and
TaskReceipt validation run. Browser generation/graph discovery, lease and git
inspection are authored boundaries; no real provider/browser/backend is called.
"""
from pathlib import Path
import copy
import hashlib
import importlib.util
import inspect
import json
import os
import sys
import unittest
import uuid
from unittest.mock import patch

REPO=Path(os.environ.get('SVF_FOUNDATION_REPOSITORY_ROOT',Path(__file__).resolve().parents[1]))
STAGE=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(STAGE/'scripts'),str(STAGE/'tests'),str(REPO/'scripts'),str(REPO/'tests'),str(REPO/'external/ipfs_accelerate')]
_spec=importlib.util.spec_from_file_location('swissknife_visual_functional_worker',STAGE/'scripts/swissknife_visual_functional_worker.py')
_candidate_worker=importlib.util.module_from_spec(_spec);sys.modules[_spec.name]=_candidate_worker;_spec.loader.exec_module(_candidate_worker)
import test_svf_phase_remediation as shapes
import swissknife_visual_functional_phase_remediation as r
import swissknife_visual_functional_worker as worker
import swissknife_visual_functional_llm as llm
import swissknife_visual_functional_review_recheck as recheck
import swissknife_visual_functional_final_coverage as final
import test_svf_final_viewport_coverage as view_shapes
assert Path(worker.__file__).resolve()==STAGE/'scripts/swissknife_visual_functional_worker.py'


def authored_admission(root, profile, child, *, role='proposal', output=None):
    """Exact public compiler callback shape, explicitly authored (not paid)."""
    identity=str(uuid.uuid4());task=child['task_id'] if role=='proposal' else child['phase_remediation']['original_task']['task_id']
    output=output or profile['runtimeRoot']+'/tasks/'+task+'/proposal.json'
    target=Path(output)
    return {'schema':'swissknife.visual-functional-provider-admission.v1','output_path':output,
        'invocation_id':identity,'task_id':task,'mode':'repair' if role=='proposal' else 'review',
        'provider':'grok_cli','model':'grok-4.7',
        'attempt_receipt_path':str(target.parent/'model-invocations'/(target.stem+'-'+identity+'.json')),
        'source_contract_sha256':'c'*64,'prompt_sha256':'c'*64,'router_source_sha256':'c'*64,
        'input_files':[],'screenshots':[],'timeout_seconds':60,'model_context_bytes':262144,
        'max_output_tokens':12288,'max_turns':8}


class WorkerSourceReplayTests(unittest.TestCase):
    def setUp(self):
        self.env=shapes.PhaseRemediationTests('runTest');self.env.setUp();self.addCleanup(self.env.doCleanups)
        self.root=self.env.root;self.profile=self.env.profile;self.task=self.env.task
        self.addCleanup(patch.stopall)
        patch.object(worker,'ROOT',self.root).start()
        # Real consumer inputs, no browser execution or new original review.
        self.shape=view_shapes.Fixture.__new__(view_shapes.Fixture)
        self.shape.root=self.root;self.shape.profile=self.profile
        app={'app_id':'notes','title':'Authored native task fixture','disposition':'browser_local',
             'source_paths':['web/js/main-simple.js'],'primary_workflow':{'expected_results':['Observed arithmetic result'],
             'persist_reopen':'Restored result','error':'Observed invalid input','recovery':'Clear and calculate again'}}
        self.shape.apps=[app];self.shape.tasks=[self.task]
        self.shape.review=lambda group:None;self.shape.receipt=lambda group:None
        self.profile.update(appContractPath='swissknife/config/contract.json',bounds={},
            llm={'provider':'grok_cli','model':'grok-4.7','allowLocalFallback':False,'allowCrossProviderFallback':False})
        for name in final.STATIC_INPUTS:
            if not (self.root/name).exists():self.shape.write(name,'// AUTHORED NOT EXECUTED '+name)
        self.shape.write('swissknife/web/index.html','<link rel="stylesheet" href="/css/one.css"><link rel="stylesheet" href="/css/two.css">')
        self.shape.write('swissknife/web/css/one.css','body {color:black;}');self.shape.write('swissknife/web/css/two.css','button {color:blue;}')
        self.shape.write(self.profile['appContractPath'],{'apps':[app]})
        self.scenario='swissknife/test/e2e/functional-workflows/notes.json'
        self.shape.write(self.scenario,self.shape.scenario(app))
        self.shape.write('config/swissknife_visual_functional_supervisor.json',self.profile)
        patch.object(final,'_node_source_snapshot',side_effect=self.shape.source_vector).start()
        recheck.remember_exhaustion(self.root,self.profile,self.task,json.loads(self.env.f.journal.read_text()))
        self.spec,self.child=self.env.admitted_child()
        self.parent=next(task for task in self.spec['tasks'] if task['task_id']==self.task['task_id'])
        self.paths=self.child['edit_paths'];self.directory=self.profile['runtimeRoot']+'/tasks/'+self.child['task_id']
        self.before={name:(self.root/name).read_bytes() for name in self.paths}
        changed_scenario=json.loads(self.before[self.scenario]);changed_scenario['description']='Actual scoped source change in authored fixture'
        self.after={self.paths[0]:b'REPAIRED app source',self.scenario:(json.dumps(changed_scenario,sort_keys=True)+'\n').encode()}
        self.before_hashes={name:hashlib.sha256(raw).hexdigest() for name,raw in self.before.items()}
        self.after_hashes={name:hashlib.sha256(raw).hexdigest() for name,raw in self.after.items()}
        self.ledger=self.root/self.profile['runtimeRoot']/'owned-source-hashes.json'
        self.ledger.write_text(json.dumps(self.before_hashes))
        self.producer_calls=[]
        def producer(profile,parent,directory,**kwargs):
            self.producer_calls.append(kwargs);self.shape.tasks=[parent]
            group=self.shape.group();check={'argv':['node','swissknife/scripts/run-visual-functional-workflow.mjs','--app','notes','--contracts',profile['appContractPath'],'--output-dir',str(group['report'].parent),'--independent-viewports'], 'exit_code':0,'output_tail':'Authored dual-session producer only'}
            return [group['report']],[check]
        self.lease=patch.object(worker,'ensure_lease',return_value=None).start()
        patch.object(worker,'dirty_paths',return_value=set(self.paths)).start()
        patch.object(worker,'workflow',side_effect=producer).start()
        self.provider=patch.object(worker,'model',side_effect=AssertionError('No new paid call on retained proposal replay')).start()
        self._retained_proposal()

    def _retained_proposal(self):
        admission=authored_admission(self.root,self.profile,self.child)
        identity=r.admit_payment(self.root,self.profile,self.spec,self.child,'proposal',admission)
        receipt=self.env.f.receipt('repair','needs_changes')
        receipt.update({key:value for key,value in admission.items() if key not in {'schema','output_path'}})
        receipt['response'].update(task_id=self.child['task_id'],edits=[{'path':name,'before_sha256':self.before_hashes[name],
            'old':self.before[name].decode(),'new':self.after[name].decode()} for name in self.paths])
        receipt['response_sha256']=hashlib.sha256(llm._json(receipt['response']).encode()).hexdigest()
        raw=r.wire(receipt)+b'\n';r.atomic(self.root,admission['output_path'],raw,exclusive=True)
        r.atomic(self.root,admission['attempt_receipt_path'],raw,exclusive=True)
        llm.validate_model_receipt(self.root,receipt,task_id=self.child['task_id'],mode='repair',predicted_files=self.paths)
        r.finish_payment(self.root,self.profile,self.child,identity,receipt=r.ref(self.root,admission['output_path']))
        retained={}
        for index,name in enumerate(self.paths):
            saved=self.directory+'/original-'+str(index)+'.txt';r.atomic(self.root,saved,self.before[name],exclusive=True)
            retained[name]={'path':saved,'sha256':self.before_hashes[name],'bytes':len(self.before[name])}
        application={'schema':r.SCHEMA,'proposal':r.ref(self.root,admission['output_path']),
            'before':self.before_hashes,'after':self.after_hashes,'original_sources':retained,'completion_authority':False}
        r.atomic(self.root,self.directory+'/application-intent.json',r.wire(application)+b'\n',exclusive=True)

    def test_real_worker_partial_application_replays_only_exact_pending_file_without_new_call(self):
        first,second=self.paths;(self.root/first).write_bytes(self.after[first])
        with self.assertRaisesRegex(RuntimeError,'unowned dirty path'):worker.check_owned_sources(self.profile,self.paths)
        phase=self.env.f.journal.read_bytes();result=worker.execute('profile.json',self.profile,self.spec,self.child)
        self.assertEqual((self.root/second).read_bytes(),self.after[second]);self.assertEqual(json.loads(self.ledger.read_text()),self.after_hashes)
        self.provider.assert_not_called();self.assertEqual(len(self.producer_calls),1)
        self.assertEqual(self.env.f.journal.read_bytes(),phase);self.assertFalse(result['completion_authority'])
        self.assertEqual(worker.validate(self.profile,self.child),result)
        paid=r.payments(self.root,self.profile,self.child);self.assertEqual(paid['spent'],{'assessment':0,'proposal':1});self.assertTrue(paid['closed'])

    def test_real_worker_all_after_crash_before_ledger_recovers_without_reapplying_or_paying(self):
        for name,raw in self.after.items():(self.root/name).write_bytes(raw)
        with patch.object(llm,'apply_validated_edits',side_effect=AssertionError('Already-applied files must not be replaced')):
            result=worker.execute('profile.json',self.profile,self.spec,self.child)
        self.assertEqual(json.loads(self.ledger.read_text()),self.after_hashes);self.provider.assert_not_called();self.assertEqual(result['kind'],r.KIND)

    def test_foreign_ledger_on_already_applied_path_refuses_before_pending_file_changes(self):
        first,second=self.paths;(self.root/first).write_bytes(self.after[first]);ledger=dict(self.before_hashes);ledger[first]='e'*64;self.ledger.write_text(json.dumps(ledger));before=(self.root/second).read_bytes()
        with self.assertRaisesRegex(ValueError,'ledger|ownership'):worker.execute('profile.json',self.profile,self.spec,self.child)
        self.assertEqual((self.root/second).read_bytes(),before);self.assertEqual(json.loads(self.ledger.read_text()),ledger);self.assertEqual(self.producer_calls,[]);self.provider.assert_not_called()

    def test_foreign_source_third_value_never_replays_retained_proposal(self):
        first,second=self.paths;(self.root/first).write_bytes(b'FOREIGN meaningful source');before=(self.root/second).read_bytes()
        with self.assertRaisesRegex(ValueError,'foreign'):worker.execute('profile.json',self.profile,self.spec,self.child)
        self.assertEqual((self.root/first).read_bytes(),b'FOREIGN meaningful source');self.assertEqual((self.root/second).read_bytes(),before);self.provider.assert_not_called()

    def test_retained_proposal_original_bytes_cannot_be_rebound_for_replay(self):
        intent=json.loads((self.root/self.directory/'application-intent.json').read_text());saved=self.root/next(iter(intent['original_sources'].values()))['path'];saved.write_bytes(b'forged original')
        with self.assertRaisesRegex(ValueError,'rebound'):worker.execute('profile.json',self.profile,self.spec,self.child)
        self.provider.assert_not_called();self.assertEqual(self.producer_calls,[])


    def test_self_consistent_forged_producer_argv_cannot_replace_the_original_check(self):
        result=worker.execute('profile.json',self.profile,self.spec,self.child)
        record=result['detail']['source_only_remediation'];value=json.loads((self.root/record['path']).read_text())
        value['workflow_checks'][0]['argv'][3]='different-app'
        worker.atomic_json(self.root/record['path'],value)
        result['checks']=value['workflow_checks'];result['detail']['source_only_remediation']=r.ref(self.root,record['path'])
        result['artifacts']=[r.ref(self.root,item['path']) if item['path']==record['path'] else item for item in result['artifacts']]
        worker.atomic_json(self.root/self.directory/'receipt.json',result)
        with self.assertRaisesRegex(ValueError,'producer command'):worker.validate(self.profile,self.child)
        self.provider.assert_not_called()


class SDKBoundaryHookTests(unittest.TestCase):
    def setUp(self):
        import tempfile,signal
        self.tmp=tempfile.TemporaryDirectory(dir='/dev/shm');self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        name='ipfs_accelerate_py.agent_supervisor.rescue._svf_integration_candidate'
        file=STAGE/'external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/rescue/lane_resume.py'
        spec=importlib.util.spec_from_file_location(name,file);self.lane=importlib.util.module_from_spec(spec);sys.modules[name]=self.lane;spec.loader.exec_module(self.lane);self.addCleanup(sys.modules.pop,name,None)
        for sig in (signal.SIGTERM,signal.SIGINT):self.addCleanup(signal.signal,sig,signal.getsignal(sig))
        (self.root/'board.md').write_text('## SVF-001 Authored boundary task\n\n- Status: ready\n')
        self.args=['--repo-root',str(self.root),'--todo-path','board.md','--task-header-prefix','## SVF-',
            '--status-path',str(self.root/'state/status.json'),'--pid-path',str(self.root/'state/pid'),
            '--log-path',str(self.root/'state/log'),'--bundle-key','authored-integration',
            '--max-seconds','1','--minimum-free-bytes','1']
        # Relocate only the SDK's fixed emergency telemetry directory into this authored RAM runtime.
        emergency=self.root/'emergency';emergency.mkdir(mode=0o700)
        patch('ipfs_accelerate_py.agent_supervisor.rescue.storage_pressure._runtime_directory',return_value=emergency).start()
        self.clock=0.0;self.events=[];self.statuses=[]
        patch.object(self.lane.time,'monotonic',side_effect=lambda:self.clock).start()
        patch.object(self.lane.time,'sleep',side_effect=lambda value:setattr(self,'clock',self.clock+value)).start()
        patch.object(self.lane,'lane_execution_health',return_value={'health':'healthy','pending_failure_count':0}).start()
        original_status=self.lane.write_lane_status
        def status(*args,**kwargs):self.statuses.append(kwargs);return original_status(*args,**kwargs)
        patch.object(self.lane,'write_lane_status',side_effect=status).start()
        def cycle(**kwargs):self.events.append('cycle');return {'phase':'deterministic_resume_unavailable','state':'blocked'}
        self.cycle=patch.object(self.lane,'run_resume_cycle',side_effect=cycle).start();self.addCleanup(patch.stopall)

    def test_default_sdk_serve_preserves_original_cycle_without_new_hook(self):
        self.assertIsNone(inspect.signature(self.lane.serve).parameters['between_cycles'].default)
        self.assertEqual(self.lane.serve(self.args),0);self.assertEqual(self.events,['cycle']);self.cycle.assert_called_once()

    def test_optional_hook_runs_before_next_native_cycle(self):
        def hook():self.events.append('hook');return {'state':'committed','completion_authority':False}
        self.assertEqual(self.lane.serve(self.args,between_cycles=hook),0);self.assertEqual(self.events,['hook','cycle'])

    def test_refused_or_exceptional_boundary_never_runs_a_native_cycle(self):
        def hook():self.events.append('hook');return {'state':'refused','reason':'Authored foreign HOLD'}
        self.assertEqual(self.lane.serve(self.args,between_cycles=hook),0);self.cycle.assert_not_called()
        self.assertEqual(self.events,['hook']);self.assertTrue(any(s.get('phase')=='between_cycles_refused' for s in self.statuses))
        self.assertLessEqual(self.clock,1.0)


if __name__=='__main__':unittest.main()
