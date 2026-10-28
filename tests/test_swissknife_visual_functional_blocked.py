"""Authored native metadata tests negative proposal admission, with no provider."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import swissknife_visual_functional_blocked as cache
import swissknife_visual_functional_llm as adapter


class BlockedTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        (self.root/'app.js').write_text('const output = null;\n');(self.root/'backend.py').write_text('# native dependency\n')
        self.task={'task_id':'SVF-133','kind':'verify','app_id':'accelerate-panel','acceptance':'Actual useful result',
                   'edit_paths':['app.js'],'checks':[]}
        self.route={'provider':'grok_cli','model':'grok-4.7','temperature':0,'allowLocalFallback':False,'allowCrossProviderFallback':False}
        self.edits={'app.js':self.sha('app.js')};self.readonly={'backend.py':self.sha('backend.py')}
        self.failure={'schema':cache.FAILURE_SCHEMA,'task_id':'SVF-133','source_sha256':self.edits,
            'stage':'workflow','error':{'code':'ValidationCommandError','message':'actual backend failure'},
            'diagnostic':{'phase':'primary_result','step':5,'error':{'code':'POSTCONDITION_FAILED',
                'details':{'actual':'No usable output','expected':'short test','probe':{'kind':'text','selector':'#output'}}},
                'retained_observations':[{'observation':{'records':[{'binding_id':'accelerate.inference','tool_id':'run_inference_job',
                    'response':{'outcome':'failed','correlation_id':'old-correlation','result':{'error':'native typed reason'},
                                'receipt':{'receipt_id':'old-receipt'}}}]}}]},
            'created_at':'old-time','work_complete':False,'completion_authority':False}
        self.directory='data/agent_supervisor/swissknife_visual_functional/tasks/SVF-133/blocked-repairs'
        self.path=self.root/'result.json';self.save_receipt()

    def sha(self,name):return hashlib.sha256((self.root/name).read_bytes()).hexdigest()

    def scope(self,**overrides):
        args={'task':self.task,'route':self.route,'edit_hashes':self.edits,'readonly_hashes':self.readonly,'failure':self.failure};args.update(overrides)
        return cache.build_scope(self.root,**args)

    def save_receipt(self,change=lambda r:None):
        response={'schema':adapter.RESPONSE_SCHEMA,'task_id':'SVF-133','mode':'repair','decision':'blocked',
                  'summary':'Native adapter cause is outside the edit scope.','inspected_screenshots':[],
                  'findings':[{'severity':'blocker','category':'backend','description':'Inspect backend.py before repairing.',
                               'evidence_paths':['backend.py']}],'edits':[]}
        r={'schema':adapter.RECEIPT_SCHEMA,'task_id':'SVF-133','mode':'repair','provider':'grok_cli','model':'grok-4.7',
           'temperature':0,'success':True,'allow_local_fallback':False,'allow_cross_provider_fallback':False,
           'disable_model_retry':True,'edits_applied':False,'work_complete':False,'completion_authority':False,
           'effective_route':{'effective_provider_name':'grok_cli','effective_model_name':'grok-4.7'},
           'native_observation':{'exit_code':0,'native_grok_reason_code':'end_turn','native_grok_error_observed':False,
               'native_grok_progress':{'response_usable':True,'tool_name_counts':{'read_file':0,'run_terminal_cmd':0,'unknown':0}}},
           'screenshots':[],'response':response,'input_files':[{'path':k,'sha256':v} for k,v in {**self.edits,**self.readonly}.items()]}
        for key in ['source_contract_sha256','prompt_sha256','router_source_sha256','output_sha256']:r[key]='c'*64
        r['response_sha256']=hashlib.sha256(adapter._json(response).encode()).hexdigest();change(r)
        self.path.write_text(json.dumps(r));return r

    def remember(self):return cache.remember_blocked(self.root,self.directory,self.scope(),'result.json')

    def test_valid_negative_reuses_reason_and_findings_without_granting_acceptance(self):
        record=self.remember()
        with self.assertRaises(cache.CachedBlockedRepair) as ctx:cache.raise_if_blocked(self.root,self.directory,self.scope())
        self.assertEqual(ctx.exception.code,'cached_model_decline');self.assertEqual(ctx.exception.reason,record['response']['summary'])
        self.assertEqual(ctx.exception.findings,record['response']['findings']);self.assertFalse(record['completion_authority'])
        self.assertFalse((self.root/self.directory/'receipt.json').exists())

    def test_new_clock_correlation_receipt_attempt_ids_do_not_renew_paid_eligibility(self):
        scope=self.scope();self.remember();f=copy.deepcopy(self.failure);f['created_at']='new-time';f['pid']=999
        response=f['diagnostic']['retained_observations'][0]['observation']['records'][0]['response'];response['correlation_id']='new-correlation';response['receipt']['receipt_id']='new-receipt'
        other=self.scope(failure=f);self.assertEqual(scope,other)
        with self.assertRaises(cache.CachedBlockedRepair):cache.raise_if_blocked(self.root,self.directory,other)

    def test_changed_native_reason_or_asserted_value_is_new_concrete_failure(self):
        self.remember();f=copy.deepcopy(self.failure);f['diagnostic']['error']['details']['actual']='different output'
        self.assertIsNone(cache.raise_if_blocked(self.root,self.directory,self.scope(failure=f)))
        f=copy.deepcopy(self.failure);f['diagnostic']['retained_observations'][0]['observation']['records'][0]['response']['result']['error']='new native reason'
        self.assertIsNone(cache.raise_if_blocked(self.root,self.directory,self.scope(failure=f)))

    def test_real_source_or_dependency_change_invalidates_negative_scope(self):
        self.remember();(self.root/'backend.py').write_text('# actual dependency repaired\n')
        with self.assertRaises(cache.BlockedCacheError):self.scope()
        new=self.scope(readonly_hashes={'backend.py':self.sha('backend.py')})
        self.assertIsNone(cache.raise_if_blocked(self.root,self.directory,new))
        (self.root/'app.js').write_text('const output = 42;\n');f=copy.deepcopy(self.failure);edits={'app.js':self.sha('app.js')};f['source_sha256']=edits
        self.assertIsNone(cache.raise_if_blocked(self.root,self.directory,self.scope(edit_hashes=edits,readonly_hashes={'backend.py':self.sha('backend.py')},failure=f)))

    def test_changed_task_policy_is_not_reused(self):
        self.remember();task=dict(self.task,acceptance='Different genuine result')
        self.assertIsNone(cache.raise_if_blocked(self.root,self.directory,self.scope(task=task)))

    def test_owner_error_code_and_type_change_negative_identity(self):
        row=self.failure['diagnostic']['retained_observations'][0]['observation']['records'][0]
        row['response']['result']['owner_error']={'code':'INVALID_INPUT','type':'ValueError','message':'bad input'}
        first=self.scope();self.remember()
        row['response']['result']['owner_error']['code']='MISSING_MODEL'
        self.assertNotEqual(first['fingerprint'],self.scope()['fingerprint'])
        self.assertIsNone(cache.raise_if_blocked(self.root,self.directory,self.scope()))

    def test_real_profile_token_limits_are_policy_not_credentials(self):
        route=dict(self.route,maxOutputTokens=16384,modelContextBytes=262144,repairReadPolicy='inline_only')
        scope=self.scope(route=route)
        cache.remember_blocked(self.root,self.directory,scope,'result.json')
        with self.assertRaises(cache.CachedBlockedRepair):cache.raise_if_blocked(self.root,self.directory,scope)
        with self.assertRaises(cache.BlockedCacheError):self.scope(route=dict(route,api_key='private'))

    def test_wrong_route_task_and_stale_failure_are_rejected(self):
        with self.assertRaises(cache.BlockedCacheError):self.scope(route=dict(self.route,model='another-model'))
        with self.assertRaises(cache.BlockedCacheError):self.scope(failure=dict(self.failure,task_id='SVF-OTHER'))
        with self.assertRaises(cache.BlockedCacheError):self.scope(failure=dict(self.failure,source_sha256={'app.js':'0'*64}))
        with self.assertRaises(cache.BlockedCacheError):self.scope(failure=dict(self.failure,error={'code':'browser_contention'}))

    def test_only_successful_validated_blocked_no_edits_receipts_are_cached(self):
        changes=[lambda r:r.update(success=False),lambda r:r['native_observation'].update(exit_code=1),
                 lambda r:r['effective_route'].update(effective_model_name='wrong'),
                 lambda r:r['response'].update(decision='pass'),lambda r:r['response'].update(edits=[{'path':'app.js'}]),
                 lambda r:r['input_files'][0].update(sha256='0'*64)]
        for change in changes:
            with self.subTest(change=change):
                self.save_receipt(change)
                with self.assertRaises((cache.BlockedCacheError,adapter.ModelAdapterError)):self.remember()

    def test_corrupt_cache_or_sanitized_receipt_cannot_suppress_model(self):
        record=self.remember();f=self.root/record['receipt']['path'];f.write_text('changed')
        with self.assertRaises(cache.BlockedCacheError):cache.raise_if_blocked(self.root,self.directory,self.scope())

    def test_non_directory_cache_state_fails_closed_before_paid_retry(self):
        path=self.root/self.directory;path.parent.mkdir(parents=True);path.write_text('malformed cache directory')
        with self.assertRaises(cache.BlockedCacheError):cache.raise_if_blocked(self.root,self.directory,self.scope())

    def test_unsafe_provider_bodies_are_never_copied_into_negative_cache(self):
        self.save_receipt(lambda r:r['native_observation'].update(raw_provider_logs='RAW PROVIDER LOG MUST NEVER BE CACHED'))
        self.remember();allbytes=b''.join(p.read_bytes() for p in (self.root/self.directory).glob('*.json'))
        self.assertNotIn(b'RAW PROVIDER LOG',allbytes);self.assertNotIn(b'raw_provider_logs',allbytes)

    def test_native_error_projection_never_caches_provider_logs_or_auth_bodies(self):
        row=self.failure['diagnostic']['retained_observations'][0]['observation']['records'][0]
        row['response']['result'].update(raw_provider_logs='DO NOT RETAIN PROVIDER BODY', authorization='DO NOT RETAIN AUTH')
        self.remember();content=b''.join(p.read_bytes() for p in (self.root/self.directory).glob('*.json'))
        self.assertNotIn(b'DO NOT RETAIN',content)

    def test_projected_readonly_context_is_fenced_without_claiming_direct_file_delivery(self):
        self.save_receipt(lambda r:r.update(input_files=r['input_files'][:1]))
        self.remember()
        with self.assertRaises(cache.CachedBlockedRepair):cache.raise_if_blocked(self.root,self.directory,self.scope())

    def test_original_mutable_output_can_change_without_changing_immutable_model_proof(self):
        record=self.remember();self.path.write_text('new unrelated invocation')
        with self.assertRaises(cache.CachedBlockedRepair):cache.raise_if_blocked(self.root,self.directory,self.scope())
        self.assertTrue((self.root/record['receipt']['path']).is_file())

    def test_cache_is_bounded_and_never_overwrites_a_prior_model_reason(self):
        first=self.remember();before={p.name:p.read_bytes() for p in (self.root/self.directory).glob('*.json')}
        self.remember();self.assertEqual(before,{p.name:p.read_bytes() for p in (self.root/self.directory).glob('*.json')})
        with self.assertRaises(cache.BlockedCacheError):cache.remember_blocked(self.root,'data/foreign',self.scope(),'result.json')

    def test_symlink_and_injected_scope_are_refused(self):
        self.remember();scope=self.scope();scope['identity']['task']['acceptance']='tampered'
        with self.assertRaises(cache.BlockedCacheError):cache.raise_if_blocked(self.root,self.directory,scope)
        (self.root/'link').symlink_to(self.root/'backend.py')
        with self.assertRaises(cache.BlockedCacheError):self.scope(readonly_hashes={'link':self.sha('backend.py')})



class WorkerCacheIntegrationTests(unittest.TestCase):
    def setUp(self):
        from unittest.mock import patch
        import swissknife_visual_functional_worker as worker
        self.worker=worker
        self.fixture=BlockedTests('test_valid_negative_reuses_reason_and_findings_without_granting_acceptance')
        self.fixture.setUp();self.addCleanup(self.fixture.doCleanups);self.root=self.fixture.root
        self.patch=patch.object(worker,'ROOT',self.root);self.patch.start();self.addCleanup(self.patch.stop)
        self.task=self.fixture.task
        self.profile={'runtimeRoot':'data/agent_supervisor/swissknife_visual_functional','appContractPath':'contracts.json',
            'taskSpecPath':'tasks.json','humanPlanPath':'plan.md','llm':dict(self.fixture.route,repairReadPolicy='inline_only',maxOutputTokens=16384)}
        for name,value in [('profile.json',json.dumps(self.profile)),('contracts.json',json.dumps({'apps':[{'app_id':self.task['app_id']}]})),
                           ('tasks.json',json.dumps({'tasks':[self.task]})),('swissknife/docs/visual-functional-driver-contract.md','Exact readonly grammar')]:
            path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(value)
        self.directory=self.root/self.profile['runtimeRoot']/'tasks'/self.task['task_id'];self.directory.mkdir(parents=True)
        self.failure=copy.deepcopy(self.fixture.failure);self.failure.update(task_context_sha256=worker.failure_task_context(self.task),task_spec_sha256=worker.stable(self.task))
        self.failure_path=worker.execution_failure_path(self.profile,self.task);self.save_failure()
        self.calls=0

    def save_failure(self):self.failure_path.write_text(json.dumps(self.failure))

    def invoke(self,*args,**kwargs):
        self.calls+=1
        receipt=self.fixture.save_receipt()
        receipt['input_files']=[{'path':name,'sha256':self.fixture.sha(name)} for name in kwargs['input_paths']]
        # Editable full source is directly supplied by the current worker.
        for name in kwargs['predicted_files']:
            if name not in {v['path'] for v in receipt['input_files']}:
                receipt['input_files'].append({'path':name,'sha256':self.fixture.sha(name)})
        path=self.root/kwargs['output_path'];path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(receipt))
        return receipt

    def call(self):
        from unittest.mock import patch
        with patch.object(adapter,'invoke_task_model',side_effect=self.invoke):
            return self.worker.model('profile.json',self.task,'repair',['app.js','backend.py'],[],self.directory/'repair.json')

    def test_first_real_blocked_receipt_prevents_second_identical_paid_call_and_keeps_failure(self):
        original=self.failure_path.read_bytes()
        with self.assertRaisesRegex(ValueError,'declined'):self.call()
        with self.assertRaises(cache.CachedBlockedRepair):self.call()
        self.assertEqual(self.calls,1);self.assertEqual(self.failure_path.read_bytes(),original)
        self.assertFalse((self.directory/'receipt.json').exists())
        self.assertFalse((self.directory/'lane_resume_attempts.semantic-recovery.json').exists())

    def test_changed_readonly_dependency_or_concrete_failure_allows_new_bounded_proposal(self):
        with self.assertRaises(ValueError):self.call()
        (self.root/'backend.py').write_text('# actual dependency repair\n')
        with self.assertRaises(ValueError):self.call()
        self.assertEqual(self.calls,2)
        self.failure['diagnostic']['error']['details']['actual']='new real failure';self.save_failure()
        with self.assertRaises(ValueError):self.call()
        self.assertEqual(self.calls,3)

    def test_declared_dependency_change_renews_model_eligibility_even_when_projected(self):
        self.task['execution_inputs']=['owner-service.py']
        (self.root/'owner-service.py').write_text('# original native dependency')
        with self.assertRaises(ValueError):self.call()
        (self.root/'owner-service.py').write_text('# actual native dependency repair')
        with self.assertRaises(ValueError):self.call()
        self.assertEqual(self.calls,2)

    def test_malformed_existing_cache_cannot_bypass_negative_admission(self):
        with self.assertRaises(ValueError):self.call()
        paths=list((self.directory/'blocked-repairs').glob('*.json'));target=next(p for p in paths if not p.name.endswith('.receipt.json'))
        target.write_text('{invalid')
        with self.assertRaises(cache.BlockedCacheError):self.call()
        self.assertEqual(self.calls,1)

    def test_no_current_observed_failure_keeps_initial_repair_path_uncached(self):
        self.failure_path.unlink()
        for _ in range(2):
            with self.assertRaises(ValueError):self.call()
        self.assertEqual(self.calls,2);self.assertFalse((self.directory/'blocked-repairs').exists())

if __name__=='__main__':unittest.main()
