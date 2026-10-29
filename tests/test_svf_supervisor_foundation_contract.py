#!/usr/bin/env python3
"""Protected fixed programs and real offline SDK contract tests; no services."""
import ast,hashlib,importlib.util,json,os,subprocess,sys,tempfile,threading,unittest,uuid
from pathlib import Path
from unittest.mock import patch
BASE=Path(__file__).resolve().parents[1];SCRIPTS=BASE/'scripts/svf_backends';RAM=BASE/'qualification';RAM.mkdir(mode=0o700,exist_ok=True)
def module(name):
    spec=importlib.util.spec_from_file_location(name,SCRIPTS/(name+'.py'));m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
os.environ.setdefault('SVF_FOUNDATION_REPOSITORY_ROOT',str(Path.cwd()))
worker=module('fixed_supervisor_worker');validator=module('fixed_supervisor_output_validator');gate=module('validate_supervisor_foundation')

class FixedPrograms(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=RAM);self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.root.chmod(0o700);self.run=str(uuid.uuid4());self.challenge=uuid.uuid4().hex
    def test_actual_a_b_bytes_independently_validated(self):
        for stage in ('a','b'):
            observed=worker.produce(self.root,self.run,stage,self.challenge)
            check=validator.check(self.root,self.run,stage,self.challenge)
            self.assertEqual(check['output_sha256'],observed['output_sha256'])
        b=json.loads((self.root/self.run/'b.json').read_text());self.assertEqual(b['predecessor_sha256'],hashlib.sha256((self.root/self.run/'a.json').read_bytes()).hexdigest())
    def test_b_without_a_refused(self):
        with self.assertRaises(FileNotFoundError):worker.produce(self.root,self.run,'b',self.challenge)
        self.assertFalse((self.root/self.run/'b.json').exists())
    def test_forged_semantic_output_rejected(self):
        worker.produce(self.root,self.run,'a',self.challenge);path=self.root/self.run/'a.json';v=json.loads(path.read_text());v['result']='0'*64;path.write_text(json.dumps(v))
        with self.assertRaisesRegex(ValueError,'expected bytes'):validator.check(self.root,self.run,'a',self.challenge)
    def test_foreign_challenge_rejected(self):
        worker.produce(self.root,self.run,'a',self.challenge)
        with self.assertRaises(ValueError):validator.check(self.root,self.run,'a','f'*32)
    def test_noncanonical_bytes_rejected(self):
        worker.produce(self.root,self.run,'a',self.challenge);path=self.root/self.run/'a.json';path.write_text(path.read_text()+' ')
        with self.assertRaises(ValueError):validator.check(self.root,self.run,'a',self.challenge)
    def test_symlink_output_never_followed(self):
        run=worker.directory(self.root,self.run);outside=self.root/'foreign';outside.write_text('untouched');(run/'a.json').symlink_to(outside)
        with self.assertRaises(ValueError):worker.produce(self.root,self.run,'a',self.challenge)
        self.assertEqual(outside.read_text(),'untouched')
    def test_no_output_overwrite(self):
        worker.produce(self.root,self.run,'a',self.challenge);path=self.root/self.run/'a.json';original=path.read_bytes()
        with self.assertRaisesRegex(ValueError,'collision'):worker.produce(self.root,self.run,'a',self.challenge)
        self.assertEqual(path.read_bytes(),original)
    def test_unsafe_identifiers_refused(self):
        for identity in ('../../foreign','not-uuid','A'*36):
            with self.subTest(identity=identity),self.assertRaises(ValueError):worker.produce(self.root,identity,'a',self.challenge)
    def test_arbitrary_code_not_a_cli_argument(self):
        p=subprocess.run([sys.executable,'-I','-B',str(SCRIPTS/'fixed_supervisor_worker.py'),'--runtime-root',str(self.root),'--run-id',self.run,'--stage','a','--challenge',self.challenge,'--code','print(1)'],capture_output=True,text=True,timeout=3)
        self.assertEqual(p.returncode,2);self.assertFalse((self.root/self.run/'a.json').exists())
    def test_live_gate_missing_protected_owner_refuses(self):
        with self.assertRaisesRegex(ValueError,'not admitted'):gate.verify_live('config/swissknife_visual_functional_supervisor.json',self.root/'data/agent_supervisor/swissknife_visual_functional/tasks/SVF-044/qualification',root=self.root)
    def test_python3_checker_uses_exact_canonical_native_python_alias(self):
        native=str(gate.SDK_ROOT/'external/ipfs_datasets/.venv/bin/python')
        with patch.object(gate.sys,'executable',native+'3'):
            for validator_flag in (False,True):
                self.assertEqual(gate.fixed_argv(self.root,self.run,'a',self.challenge,validator=validator_flag)[0],native)
    def test_kernel_witness_observes_worker_spawned_from_nonmain_thread(self):
        result=[]
        def dispatch():
            result.append(subprocess.run(gate.fixed_argv(self.root,self.run,'a',self.challenge),capture_output=True,text=True,timeout=3))
        with gate.KernelWitness(os.getpid(),[SCRIPTS/'fixed_supervisor_worker.py'],self.run) as witness:
            thread=threading.Thread(target=dispatch);thread.start();thread.join(timeout=4)
        self.assertFalse(thread.is_alive());self.assertEqual(result[0].returncode,0)
        emitted=json.loads(result[0].stdout)
        self.assertTrue(any(row['pid']==emitted['pid'] and row['start_ticks']==emitted['start_ticks'] for row in witness.rows()))
    def test_fixture_prefix_cannot_intercept_ordinary_cpu_submit_task(self):
        tree=ast.parse((gate.SDK_ROOT/'scripts/svf_backends/native_accelerate_service.py').read_text())
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='NativeAccelerate');call=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='call')
        call.body.insert(0,ast.parse("if tool == 'submit_task':\n    return {}").body[0])
        target=self.root/'scripts/svf_backends/native_accelerate_service.py';target.parent.mkdir(parents=True);target.write_text(ast.unparse(tree))
        with self.assertRaisesRegex(ValueError,'ordinary CPU'):gate.assert_cpu_preserved(self.root)
    def test_current_cpu_route_ast_is_protected(self):
        gate.assert_cpu_preserved(gate.SDK_ROOT)
    def test_fake_native_provenance_refused(self):
        with self.assertRaises(ValueError):gate.check_native_payload({'success':True,'fixture_mode':gate.MODE,'native_provenance':{'simulated':True}}, {},gate.ALIAS,{})
    def test_missing_sdk_call_trace_cannot_qualify(self):
        with self.assertRaisesRegex(ValueError,'no actual native SDK calls'):
            gate.assert_sdk_chain({},root=self.root,runtime=self.root,run_id=self.run,ids={'a':'a','b':'b'},challenge=self.challenge,observed=[],objective_id='o',root_goal='g',child_goal='c')
    def test_other_run_sdk_trace_cannot_qualify(self):
        event={'enter':{'arguments':{'run_id':str(uuid.uuid4()),'database_path':'outside'}}}
        with self.assertRaisesRegex(ValueError,'no actual native SDK calls'):
            gate.assert_sdk_chain({'foreign':event},root=self.root,runtime=self.root,run_id=self.run,ids={'a':'a','b':'b'},challenge=self.challenge,observed=[],objective_id='o',root_goal='g',child_goal='c')
    def test_unfinished_required_sdk_call_cannot_qualify(self):
        event={'enter':{'arguments':{'run_id':self.run}}}
        with self.assertRaisesRegex(ValueError,'never terminated'):
            gate.assert_sdk_chain({'unfinished':event},root=self.root,runtime=self.root,run_id=self.run,ids={'a':'a','b':'b'},challenge=self.challenge,observed=[],objective_id='o',root_goal='g',child_goal='c')
    def test_self_certified_sdk_success_without_kernel_witness_refused(self):
        run=self.root/self.run;p=run/'attempts/one/producer.json';p.parent.mkdir(parents=True)
        raw={'schema':'ipfs_accelerate_py/agent-supervisor/verification-process-runner@1','process_started':True,'lease_id':'resource-lease:fake','pid':99999999,'command_argv':gate.executed_argv(gate.fixed_argv(self.root,self.run,'a',self.challenge)),'process_group_id':99999999,'ok':True,'publication_allowed':True,'exit_code':0}
        p.write_text(json.dumps(raw));p.chmod(0o600);item={'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
        with self.assertRaisesRegex(ValueError,'kernel PID'):
            gate.check_execution({'execution':{'producer':item,'validator':item}},run,self.root,self.run,'a',self.challenge,[])
    def test_raw_sdk_artifact_hash_tamper_refused(self):
        run=self.root/'run';p=run/'attempts/one/result.json';p.parent.mkdir(parents=True);p.write_text('{}');p.chmod(0o600)
        with self.assertRaisesRegex(ValueError,'hash mismatch'):gate.sdk_artifact({'path':str(p),'sha256':'0'*64},run)

class ActualSdk(unittest.TestCase):
    def qualified_root(self):
        root=Path(os.environ.get('SVF_FOUNDATION_REPOSITORY_ROOT',str(Path.cwd()))).resolve()
        self.assertTrue((root/'external/ipfs_accelerate/ipfs_accelerate_py/__init__.py').is_file())
        return root
    def test_backend_loader_preserves_sdk_contextmanagers_and_observer_wrappers(self):
        root=self.qualified_root();python=root/'external/ipfs_datasets/.venv/bin/python'
        # Import only in a fresh child: no repository/runner construction or
        # SDK method invocation, and no mutation of this test process's SDK.
        code="""import hashlib,importlib.util,inspect,os,sys,types
from pathlib import Path
def audit(event,args):
    if event.startswith('socket.') or event in {'subprocess.Popen','os.system','os.fork','os.posix_spawn','os.mkdir','os.remove','os.rmdir','os.rename','os.chmod','os.symlink','os.link'}:raise AssertionError('import-only test attempted '+event)
    if event=='open':
        _,mode,flags=args
        assert not (isinstance(mode,str) and any(flag in mode for flag in 'wax+')) and not (isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)),'import-only test attempted a file write'
sys.addaudithook(audit)
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec);sys.modules[name]=value;spec.loader.exec_module(value);return value
root=Path(sys.argv[1]);scripts=Path(sys.argv[2])
gate=module('sdk_preservation_gate',scripts/'validate_supervisor_foundation.py')
backend=module('sdk_preservation_backend',scripts/'native_supervisor_backend.py')
sdk=gate.sdk(root);classes=(sdk[0],sdk[1],sdk[3],sdk[4])
def snapshot():return {cls:dict(vars(cls)) for cls in classes}
def unchanged(before):
    loaded=backend.load_sdk()
    assert (loaded[0],loaded[1],loaded[3],loaded[4])==classes,'load_sdk replaced SDK classes'
    for cls,attributes in before.items():
        current=dict(vars(cls));assert current.keys()==attributes.keys(),'load_sdk changed SDK class attributes'
        for name,value in attributes.items():assert current[name] is value,'load_sdk mutated '+cls.__name__+'.'+name
for name in ('read_session','_connection'):
    fn=getattr(classes[0],name)
    assert hasattr(fn,'__wrapped__') and inspect.isgeneratorfunction(inspect.unwrap(fn)),'real SDK contextmanager missing'
unchanged(snapshot())
observer=module('sdk_preservation_observer',root/'scripts/svf_backends/foundation_native_entrypoint.py')
runner=classes[2];original=runner.run;relative=gate.SDK_PATHS['runner']
observer.instrument_class(runner,('run',),sink=types.SimpleNamespace(root=root),sdk_module=runner.__module__,source_path=relative,source_sha256=hashlib.sha256((root/relative).read_bytes()).hexdigest(),check=lambda:None)
observed=runner.run
assert observed is not original and observed.__svf_observed__ is True and inspect.unwrap(observed) is original,'protected observer sentinel missing'
unchanged(snapshot())
assert runner.run is observed,'load_sdk removed protected SDK observation'
"""
        result=subprocess.run([str(python),'-I','-B','-c',code,str(root),str(SCRIPTS)],
                              cwd=root,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','IPFS_ACCEL_SKIP_CORE':'1','SVF_FOUNDATION_REPOSITORY_ROOT':str(root)},
                              capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr[-4000:])
    def test_real_sdk_db_graph_kernel_worker_validation_timeout_cancel(self):
        root=self.qualified_root();python=root/'external/ipfs_datasets/.venv/bin/python'
        self.assertTrue(python.is_file())
        # A real checker has a fresh interpreter. Other test families may
        # legitimately import the datasets-vendored namespace in their process.
        with tempfile.TemporaryDirectory(prefix='svf-supervisor-sdk-',dir='/dev/shm') as tmp:
            output=Path(tmp)/'actual'
            environment={**os.environ,'SVF_FOUNDATION_REPOSITORY_ROOT':str(root),
                         'PYTHONDONTWRITEBYTECODE':'1','TMPDIR':tmp}
            completed=subprocess.run([str(python),'-I','-B',str(SCRIPTS/'validate_supervisor_foundation.py'),
                                      '--sdk-self-test','--output-root',str(output)],cwd=root,env=environment,
                                     capture_output=True,text=True,timeout=90)
            self.assertEqual(completed.returncode,0,(completed.stdout+'\n'+completed.stderr)[-4000:])
            capsule=json.loads(completed.stdout.strip().splitlines()[-1])
            self.assertTrue(capsule['sdk_qualification']);self.assertFalse(capsule['production_mcp_ready'])
            self.assertEqual(Path(capsule['report']),output/'sdk-qualification.json')
            report=json.loads((output/'sdk-qualification.json').read_text())
            self.assertTrue(report['qualified']);self.assertTrue(report['actual_sdk']);self.assertFalse(report['production_mcp_ready']);self.assertEqual(len(report['checks']),11)
            for key,passed in report['checks'].items():
                with self.subTest(check=key):self.assertTrue(passed)
            self.assertEqual(len(report['process_results']),6)
            self.assertGreaterEqual(len(report['kernel_witnesses']),4)
            self.assertTrue(all(row['lease_id'] and row['process_started'] for row in report['process_results']))
            self.assertEqual(report['sdk_sources'],{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in gate.SDK_PATHS.values()})
            for name in ('fixed_supervisor_worker.py','fixed_supervisor_output_validator.py','validate_supervisor_foundation.py'):
                path=SCRIPTS/name
                self.assertEqual(report['protected_sources'][str(path)],hashlib.sha256(path.read_bytes()).hexdigest())
    def test_foreign_import_origin_still_refused_in_fresh_process(self):
        root=self.qualified_root();python=root/'external/ipfs_datasets/.venv/bin/python'
        # Negative origin metadata is confined to this child. Never clear or
        # rebind the combined test process's legitimately imported namespace.
        code="""import importlib.util,sys
from pathlib import Path
spec=importlib.util.spec_from_file_location('strict_sdk_gate',sys.argv[1]);gate=importlib.util.module_from_spec(spec);sys.modules[spec.name]=gate;spec.loader.exec_module(gate)
root=Path(sys.argv[2]);gate.sdk(root)
import ipfs_accelerate_py.agent_supervisor.task_sources.intent_repository as source
source.__file__=str(root/'external/ipfs_datasets/ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/task_sources/intent_repository.py')
try:gate.sdk(root)
except ValueError as error:
    assert 'foreign SDK import' in str(error),str(error)
else:raise AssertionError('foreign module origin was accepted')
"""
        result=subprocess.run([str(python),'-I','-B','-c',code,str(SCRIPTS/'validate_supervisor_foundation.py'),str(root)],
                              cwd=root,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','SVF_FOUNDATION_REPOSITORY_ROOT':str(root)},
                              capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr[-4000:])

if __name__=='__main__':unittest.main()
