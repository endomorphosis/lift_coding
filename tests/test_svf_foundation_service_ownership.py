"""Portable foundation ownership regressions with isolated authored observations.

Service/kernel/network observations are mocked only in their unit tests. Eight
capture tests use actual private filesystem bytes and the real _arm_capture.
No real systemd, browser, network or provider operation is performed. To inspect
a staged candidate, set SVF_FOUNDATION_TEST_SOURCE_ROOT to that checkout root.
"""
from pathlib import Path
import copy,hashlib,importlib.util,io,json,os,stat,sys,tempfile,time,types,unittest,uuid
from unittest.mock import patch

REPOSITORY_ROOT=Path(__file__).resolve().parents[1]
SOURCE_ROOT=Path(os.environ.get('SVF_FOUNDATION_TEST_SOURCE_ROOT',str(REPOSITORY_ROOT))).resolve()
SOURCE=SOURCE_ROOT/'scripts/svf_backends/foundation_service_ownership.py'
spec=importlib.util.spec_from_file_location('svf_foundation_ownership_test_subject',SOURCE)
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
m=helper=mod

def registration_fixture(root):
 """Authored root-local registry, never a copy of a live deployment config."""
 families={}
 for family,(_,units) in mod.FAMILIES.items():
  families[family]={'units':list(units),'mcp_url':'http://127.0.0.1:18316/mcp' if family=='kit-pubsub' else 'http://127.0.0.1:18315/mcp','runtime_root':str(root/mod.RUNTIME/'backends'/('native-pubsub' if family=='kit-pubsub' else 'supervisor-fixtures')),'required_sources':sorted(mod.REQUIRED_SOURCES[family])}
 return {'schema':'swissknife.foundation-service-registration.v1','status':'REGISTERED','root':str(root),'families':families,'units':{unit:{'authored_unit_fixture_only':True} for _,units in mod.FAMILIES.values() for unit in units},'protected_sha256':{},'pubsub_peers':[]}

class OwnershipGuards(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='svf-foundation-');self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.controls=[]
  self.cfg=registration_fixture(self.root);self.cfg.update(root=str(self.root),status='REGISTERED')
  for family,rule in self.cfg['families'].items():
   rule['runtime_root']=str(self.root/mod.RUNTIME/'backends'/('native-pubsub' if family=='kit-pubsub' else 'supervisor-fixtures'))
  self.sources={}
  for names in mod.REQUIRED_SOURCES.values():
   for name in names:
    p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('owned source '+name+'\n');p.chmod(0o600);self.sources[name]=mod.sha(p)
  protected=self.root/'scripts/authority.py';protected.parent.mkdir(exist_ok=True);protected.write_text('protected=True\n');protected.chmod(0o600);self.cfg['protected_sha256']={'scripts/authority.py':mod.sha(protected)}
  reg=self.root/mod.REGISTRATION;reg.parent.mkdir(parents=True);reg.write_text(json.dumps(self.cfg));reg.chmod(0o600)
  self.protected={}
  for name in mod.REQUIRED_PROTECTED:
   p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('fixed protected source '+name+'\n');p.chmod(0o600);self.protected[name]=mod.sha(p)
  self.cfg['protected_sha256']=dict(self.protected);self.write_cfg(self.cfg)
  self.expected={p:self.sources[p] for p in mod.REQUIRED_SOURCES['kit-pubsub']}
  ledger=self.root/mod.RUNTIME/'owned-source-hashes.json';ledger.parent.mkdir(parents=True);ledger.write_text(json.dumps(self.sources));ledger.chmod(0o600)
  self.output=self.root/mod.RUNTIME/'tasks/SVF-043/qualification';self.calls=[];self.generations={name:1 for name in self.cfg['units']}
  self.proofs=lambda name:{'pid':100+list(self.cfg['units']).index(name),'start_ticks':str(self.generations[name]),'unit':name,'invocation_id':'generation-'+str(self.generations[name]),'control_group':'/owned/'+name}
 def promotion(self,**kw):
  defaults={'family':'kit-pubsub','expected_sources':self.expected,'output_dir':self.output};defaults.update(kw);return mod.ensure_owned_services(self.root,**defaults)
 def stub_promotion(self,*,change_generation=True):
  def control(argv,**kwargs):
   self.controls.append(argv)
   self.assertEqual(argv[:3],['systemctl','--user','restart']);self.assertEqual(len(argv),4)
   if change_generation:self.generations[argv[3]]+=1
   return types.SimpleNamespace(returncode=0)
  patches=[patch.object(mod,'_registration',return_value=self.cfg),patch.object(mod,'_admission',return_value=('actual-fixture-lease','900')),patch.object(mod,'unit_identity',side_effect=lambda root,name,expected:self.proofs(name)),patch.object(mod.subprocess,'run',side_effect=control),patch.object(mod,'_arm_capture',return_value={'reload_unit_test_only':True})]
  for p in patches:p.start();self.addCleanup(p.stop)
 def write_cfg(self,value):
  (self.root/mod.REGISTRATION).write_text(json.dumps(value))
 def test_draft_registration_refused_before_any_service_call(self):
  cfg=copy.deepcopy(self.cfg);cfg['status']='DRAFT_NOT_DEPLOYED';self.write_cfg(cfg)
  with patch.object(mod.subprocess,'run')as control,patch.object(mod.subprocess,'check_output')as query:
   with self.assertRaises(ValueError):mod._registration(self.root)
   control.assert_not_called();query.assert_not_called()
 def test_arbitrary_nonempty_protected_map_is_not_registration_authority(self):
  cfg=copy.deepcopy(self.cfg);cfg['protected_sha256']={'scripts/authority.py':mod.sha(self.root/'scripts/authority.py')};self.write_cfg(cfg)
  with self.assertRaises(ValueError):mod._registration(self.root)
 def test_unknown_family_and_outside_output_refused(self):
  self.stub_promotion()
  with self.assertRaises(ValueError):self.promotion(family='foreign-command')
  with self.assertRaises(ValueError):self.promotion(output_dir=self.root/'outside')
  self.assertEqual(self.controls,[])
 def test_source_hash_and_ledger_tamper_refused_before_control(self):
  self.stub_promotion();name=next(iter(self.expected));path=self.root/name;path.write_text('foreign changed bytes')
  with self.assertRaises(ValueError):self.promotion()
  self.assertEqual(self.controls,[])
 def test_missing_or_extra_source_declaration_refused_before_control(self):
  self.stub_promotion();name=next(iter(self.expected));missing=dict(self.expected);missing.pop(name)
  with self.assertRaises(ValueError):self.promotion(expected_sources=missing)
  with self.assertRaises(ValueError):self.promotion(expected_sources={**self.expected,'foreign.py':'a'*64})
  self.assertEqual(self.controls,[])
 def test_attestation_symlink_refused_before_any_unit_restart(self):
  self.stub_promotion();path=self.root/mod.RUNTIME/'backends/foundation-service-attestations/kit-pubsub.json';path.parent.mkdir(parents=True);foreign=self.root/'foreign.json';foreign.write_text('{}');path.symlink_to(foreign)
  with self.assertRaises(ValueError):self.promotion()
  self.assertEqual(self.controls,[],'An unsafe attestation must not cause restart before rejection')
  self.assertEqual(foreign.read_text(),'{}')
 def test_restart_without_new_pid_birth_invocation_cannot_attest_source(self):
  self.stub_promotion(change_generation=False)
  with self.assertRaises(ValueError):self.promotion()
 def test_actual_restart_is_exact_registered_pair_and_cache_never_grants_authority(self):
  self.stub_promotion();first=self.promotion();self.assertEqual(self.controls,[['systemctl','--user','restart',name] for name in mod.FAMILIES['kit-pubsub'][1]]);self.assertTrue(Path(first['witness_path']).is_file())
  first_att=json.loads(Path(first['witness_path']).read_text());self.assertEqual(first_att['native_process']if'native_process'in first_att else first_att['processes'][0],self.proofs(mod.FAMILIES['kit-pubsub'][1][0]));self.assertFalse(first_att['completion_authority'])
  self.promotion();self.assertEqual(len(self.controls),4)
 def test_owner_change_before_promotion_refused(self):
  self.stub_promotion();answers=iter([('lease','900'),('different','900')])
  with patch.object(mod,'_admission',side_effect=lambda *a:next(answers)):
   with self.assertRaises(ValueError):self.promotion()
  self.assertEqual(self.controls,[])
 def test_registered_protected_closure_is_complete_and_current(self):
  self.assertEqual(mod._registration(self.root),self.cfg)
  for name in mod.REQUIRED_PROTECTED:
   with self.subTest(missing=name):
    cfg=copy.deepcopy(self.cfg);cfg['protected_sha256'].pop(name);self.write_cfg(cfg)
    with self.assertRaises(ValueError):mod._registration(self.root)
  self.write_cfg(self.cfg)
 def test_protected_source_change_during_admission_refused_before_control(self):
  self.stub_promotion();calls=0
  def admitted(*args):
   nonlocal calls
   calls+=1
   if calls==2:(self.root/next(iter(mod.REQUIRED_PROTECTED))).write_text('changed protected bytes')
   return ('actual-fixture-lease','900')
  with patch.object(mod,'_admission',side_effect=admitted):
   with self.assertRaises(ValueError):self.promotion()
  self.assertEqual(self.controls,[])
 def test_registration_bytes_change_during_admission_refused_before_control(self):
  self.stub_promotion();calls=0
  def admitted(*args):
   nonlocal calls
   calls+=1
   if calls==2:(self.root/mod.REGISTRATION).write_text(json.dumps({'foreign':'replacement'}))
   return ('actual-fixture-lease','900')
  with patch.object(mod,'_admission',side_effect=admitted):
   with self.assertRaises(ValueError):self.promotion()
  self.assertEqual(self.controls,[])
 def test_attestation_parent_symlink_refused_before_control(self):
  self.stub_promotion();parent=self.root/mod.RUNTIME/'backends';parent.mkdir(parents=True);foreign=self.root/'foreign-telemetry';foreign.mkdir();(parent/'foundation-service-attestations').symlink_to(foreign,target_is_directory=True)
  with self.assertRaises(ValueError):self.promotion()
  self.assertEqual(self.controls,[]);self.assertEqual(list(foreign.iterdir()),[])
 def test_listener_readiness_wait_keeps_single_exact_reload(self):
  self.stub_promotion();not_ready=0
  def identity(root,name,expected):
   nonlocal not_ready
   value=self.proofs(name)
   if self.generations[name]>1 and name==mod.FAMILIES['kit-pubsub'][1][0] and not_ready<1:
    not_ready+=1;raise mod.ServicePortsNotReady(value)
   return value
  with patch.object(mod,'unit_identity',side_effect=identity),patch.object(mod.time,'sleep')as pause:
   self.promotion();self.assertEqual(len(self.controls),2);pause.assert_called_once_with(0.5)
 def test_listener_timeout_never_restarts_again_or_writes_attestation(self):
  self.stub_promotion();tick=0
  def clock():
   nonlocal tick
   tick+=50;return tick
  def identity(root,name,expected):
   value=self.proofs(name)
   if self.generations[name]>1:raise mod.ServicePortsNotReady(value)
   return value
  with patch.object(mod,'unit_identity',side_effect=identity),patch.object(mod.time,'monotonic',side_effect=clock),patch.object(mod.time,'sleep'):
   with self.assertRaises(ValueError):self.promotion()
  self.assertEqual(len(self.controls),1);self.assertFalse((self.root/mod.RUNTIME/'backends/foundation-service-attestations/kit-pubsub.json').exists())
 def test_changing_generation_while_waiting_for_port_is_not_accepted(self):
  self.stub_promotion();cycles=0
  def identity(root,name,expected):
   nonlocal cycles
   value=self.proofs(name)
   if self.generations[name]>1:
    if name==mod.FAMILIES['kit-pubsub'][1][0]:cycles+=1
    value={**value,'start_ticks':str(self.generations[name]+cycles),'invocation_id':'changed-'+str(cycles)}
    raise mod.ServicePortsNotReady(value)
   return value
  with patch.object(mod,'unit_identity',side_effect=identity),patch.object(mod.time,'sleep'):
   with self.assertRaises(ValueError):self.promotion()
  self.assertEqual(len(self.controls),1)
 def test_required_source_set_cannot_be_removed_in_registration(self):
  cfg=copy.deepcopy(self.cfg);cfg['families']['kit-pubsub']['required_sources'].pop();self.write_cfg(cfg)
  with self.assertRaises(ValueError):mod._registration(self.root)
 def test_native_eight_second_warm_precedes_facade_restart_and_capture(self):
  self.stub_promotion();native,facade=mod.FAMILIES['kit-pubsub'][1];clock=[0.0];events=[]
  def identity(root,name,expected):
   value=self.proofs(name)
   if name==native and self.generations[name]>1 and clock[0]<8:
    events.append(('native_loading',clock[0]));raise mod.ServicePortsNotReady(value)
   if name==native and self.generations[name]>1:events.append(('native_ready',clock[0]))
   if name==facade and self.generations[name]>1:events.append(('facade_ready',clock[0]))
   return value
  def control(argv,**kwargs):
   self.assertEqual(argv[:3],['systemctl','--user','restart']);self.assertEqual(len(argv),4);self.controls.append(argv);name=argv[3]
   if name==facade:self.assertTrue(any(event[0]=='native_ready' for event in events));self.assertGreaterEqual(clock[0],8)
   events.append(('restart_'+('native' if name==native else 'facade'),clock[0]));self.generations[name]+=1;return types.SimpleNamespace(returncode=0)
  def pause(seconds):clock[0]+=seconds
  def arm(*args):
   self.assertTrue(any(event[0]=='facade_ready' for event in events));events.append(('capture',clock[0]));return {'reload_unit_test_only':True}
  with patch.object(mod,'unit_identity',side_effect=identity),patch.object(mod.subprocess,'run',side_effect=control),patch.object(mod.time,'monotonic',side_effect=lambda:clock[0]),patch.object(mod.time,'sleep',side_effect=pause),patch.object(mod,'_arm_capture',side_effect=arm):
   result=self.promotion()
  self.assertEqual(self.controls,[['systemctl','--user','restart',native],['systemctl','--user','restart',facade]])
  labels=[event[0] for event in events];self.assertLess(labels.index('restart_native'),labels.index('native_ready'));self.assertLess(labels.index('native_ready'),labels.index('restart_facade'));self.assertLess(labels.index('facade_ready'),labels.index('capture'));self.assertGreaterEqual(labels.count('native_loading'),16);self.assertTrue(Path(result['witness_path']).is_file())
 def test_wrong_native_identity_refuses_immediately_without_facade_restart_or_capture(self):
  self.stub_promotion();native=mod.FAMILIES['kit-pubsub'][1][0]
  def identity(root,name,expected):
   if name==native and self.generations[name]>1:raise ValueError('wrong executable or cgroup')
   return self.proofs(name)
  with patch.object(mod,'unit_identity',side_effect=identity),patch.object(mod.time,'sleep')as pause,patch.object(mod,'_arm_capture')as capture:
   with self.assertRaisesRegex(ValueError,'wrong executable or cgroup'):self.promotion()
   pause.assert_not_called();capture.assert_not_called()
  self.assertEqual(self.controls,[['systemctl','--user','restart',native]])
 def test_old_facade_owner_change_after_native_ready_refuses_before_facade_control(self):
  self.stub_promotion();native,facade=mod.FAMILIES['kit-pubsub'][1]
  def identity(root,name,expected):
   value=self.proofs(name)
   if name==facade and self.generations[native]>1:value={**value,'start_ticks':'foreign-replacement','invocation_id':'foreign-invocation'}
   return value
  with patch.object(mod,'unit_identity',side_effect=identity),patch.object(mod,'_arm_capture')as capture:
   with self.assertRaisesRegex(ValueError,'changed before promotion'):self.promotion()
   capture.assert_not_called()
  self.assertEqual(self.controls,[['systemctl','--user','restart',native]])
 def test_source_change_during_native_warm_refuses_before_facade_control(self):
  self.stub_promotion();native=mod.FAMILIES['kit-pubsub'][1][0];changed=False
  def identity(root,name,expected):
   nonlocal changed
   if name==native and self.generations[name]>1 and not changed:
    (self.root/next(iter(mod.REQUIRED_PROTECTED))).write_text('changed during native warm');changed=True
   return self.proofs(name)
  with patch.object(mod,'unit_identity',side_effect=identity),patch.object(mod,'_arm_capture')as capture:
   with self.assertRaises(ValueError):self.promotion()
   capture.assert_not_called()
  self.assertEqual(self.controls,[['systemctl','--user','restart',native]])
 def test_registered_starting_has_bounded_readonly_wait_before_any_control(self):
  self.stub_promotion();pending=[2]
  def identity(root,name,expected):
   if pending[0]>0:pending[0]-=1;raise mod.ServiceStarting(name)
   return self.proofs(name)
  with patch.object(mod,'unit_identity',side_effect=identity),patch.object(mod.time,'sleep')as pause:
   self.promotion();self.assertEqual(pause.call_args_list,[unittest.mock.call(.5),unittest.mock.call(.5)])
  self.assertEqual(len(self.controls),2)
 def test_registered_starting_timeout_has_no_control_or_capture(self):
  self.stub_promotion();native=mod.FAMILIES['kit-pubsub'][1][0]
  with patch.object(mod,'unit_identity',side_effect=mod.ServiceStarting(native)),patch.object(mod.time,'monotonic',side_effect=[0,36]),patch.object(mod,'_arm_capture')as capture:
   with self.assertRaisesRegex(ValueError,'within35seconds'):self.promotion()
   capture.assert_not_called()
  self.assertEqual(self.controls,[])
 def test_real_generation_disappearance_during_warm_is_not_treated_as_new_start(self):
  self.stub_promotion();native=mod.FAMILIES['kit-pubsub'][1][0];samples=[0]
  def identity(root,name,expected):
   value=self.proofs(name)
   if name==native and self.generations[name]>1:
    samples[0]+=1
    if samples[0]==1:raise mod.ServicePortsNotReady(value)
    raise mod.ServiceStarting(name)
   return value
  with patch.object(mod,'unit_identity',side_effect=identity),patch.object(mod.time,'sleep'),patch.object(mod,'_arm_capture')as capture:
   with self.assertRaisesRegex(ValueError,'disappeared'):self.promotion()
   capture.assert_not_called()
  self.assertEqual(self.controls,[['systemctl','--user','restart',native]])


class ActiveAdmission(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='svf-foundation-');self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  state=self.root/mod.RUNTIME/'state/svf_status.json';state.parent.mkdir(parents=True);state.write_text(json.dumps({'active_task_id':'SVF-043','phase':'deterministic_command','pid':200}));self.state=state
  watchcfg=self.root/'config/swissknife_visual_functional_watchdog.json';watchcfg.parent.mkdir(parents=True);watchcfg.write_text('{}')
  self.processes={100:{'pid':100,'start_ticks':'1000','ppid':200,'argv':['python','scripts/swissknife_visual_functional_worker.py','--task-id','SVF-043'],'cgroups':['0::/owned-main.service']},200:{'pid':200,'start_ticks':'2000','ppid':1,'argv':['python','supervisor.py'],'cgroups':['0::/owned-main.service']}}
  supervisor=types.ModuleType('swissknife_visual_functional_supervisor');worker=types.ModuleType('swissknife_visual_functional_worker')
  self.load_profile=supervisor.load_profile=unittest.mock.Mock(return_value={'runtimeRoot':mod.RUNTIME})
  self.lease=supervisor.assert_campaign_lease=unittest.mock.Mock(return_value={'lease_id':'real-fixture-lease'})
  self.hold=worker.assert_no_campaign_hold=unittest.mock.Mock()
  self.storage=worker.assert_storage_available=unittest.mock.Mock()
  watchdog=types.ModuleType('ipfs_accelerate_py.agent_supervisor.rescue.leased_service_watchdog')
  self.owner_config=types.SimpleNamespace(repo_root=self.root,unit='swissknife-visual-functional-supervisor.service')
  watchdog.Config=types.SimpleNamespace(from_dict=unittest.mock.Mock(return_value=self.owner_config))
  self.owners={'child':{'pid':200,'start_ticks':'2000'},'unit':{'ActiveState':'active','ControlGroup':'/owned-main.service'}}
  self.owner_observer=unittest.mock.Mock(side_effect=lambda:copy.deepcopy(self.owners))
  watchdog.LeasedServiceWatchdog=unittest.mock.Mock(return_value=types.SimpleNamespace(_owners=self.owner_observer))
  self.sub=patch.dict(sys.modules,{'swissknife_visual_functional_supervisor':supervisor,'swissknife_visual_functional_worker':worker,'ipfs_accelerate_py.agent_supervisor.rescue.leased_service_watchdog':watchdog});self.sub.start();self.addCleanup(self.sub.stop)
  self.pid=patch.object(mod.os,'getpid',return_value=100);self.pid.start();self.addCleanup(self.pid.stop)
  self.proc=patch.object(mod,'process',side_effect=lambda pid:copy.deepcopy(self.processes[pid]));self.procmock=self.proc.start();self.addCleanup(self.proc.stop)
  self.query=patch.object(mod.subprocess,'check_output',return_value='[]');self.querymock=self.query.start();self.addCleanup(self.query.stop)
 def test_actual_active_task_worker_ancestry_and_lease_is_accepted(self):
  self.assertEqual(mod._admission(self.root,'kit-pubsub'),('real-fixture-lease','2000'))
  self.lease.assert_called_once_with(self.load_profile.return_value,root=self.root)
  self.hold.assert_called_once();self.storage.assert_called_once()
  argv=self.querymock.call_args.args[0];self.assertEqual(argv[:3],['/usr/bin/node','--input-type=module','-e']);self.assertIn('findBrowserOwners',argv[3])
 def test_wrong_task_and_wrong_execution_phase_refused(self):
  for changed in [{'active_task_id':'SVF-044'},{'phase':'visual_review'}]:
   value={'active_task_id':'SVF-043','phase':'deterministic_command','pid':200,**changed};self.state.write_text(json.dumps(value))
   with self.subTest(changed=changed),self.assertRaises(ValueError):mod._admission(self.root,'kit-pubsub')
  self.querymock.assert_not_called()
 def test_wrong_task_worker_argv_is_not_a_worker_admission(self):
  self.processes[100]['argv'][-1]='SVF-044'
  with self.assertRaises(ValueError):mod._admission(self.root,'kit-pubsub')
  self.querymock.assert_not_called()
 def test_forged_copied_lease_environment_cannot_replace_real_guard(self):
  self.lease.side_effect=ValueError('not a descendant of actual leased supervisor')
  with self.assertRaises(ValueError):mod._admission(self.root,'kit-pubsub')
  self.querymock.assert_not_called();self.procmock.assert_not_called()
 def test_hold_or_storage_pressure_stops_before_process_or_browser_observation(self):
  for callback in [self.hold,self.storage]:
   callback.side_effect=ValueError('admission denied')
   with self.subTest(callback=callback),self.assertRaises(ValueError):mod._admission(self.root,'kit-pubsub')
   callback.side_effect=None
  self.procmock.assert_not_called();self.querymock.assert_not_called()
 def test_live_browser_owner_stops_before_promotion(self):
  self.querymock.return_value='[{"pid":999,"owner":"foreign-browser"}]'
  with self.assertRaises(ValueError):mod._admission(self.root,'kit-pubsub')
 def test_foreign_worker_or_foreground_cgroup_refused(self):
  for pid in [100,200]:
   with self.subTest(pid=pid):
    original=self.processes[pid]['cgroups'];self.processes[pid]['cgroups']=['0::/foreign.service']
    with self.assertRaises(ValueError):mod._admission(self.root,'kit-pubsub')
    self.processes[pid]['cgroups']=original
  self.querymock.assert_not_called()
 def test_status_pid_must_be_actual_registered_live_foreground(self):
  self.owners['child']['pid']=300
  with self.assertRaises(ValueError):mod._admission(self.root,'kit-pubsub')
  self.querymock.assert_not_called()
 def test_foreign_main_unit_configuration_refused(self):
  self.owner_config.unit='foreign.service'
  with self.assertRaises(ValueError):mod._admission(self.root,'kit-pubsub')
  self.owner_observer.assert_not_called()
 def test_target_birth_change_during_ancestry_is_refused(self):
  sequence={200:0}
  def proc(pid):
   p=copy.deepcopy(self.processes[pid])
   if pid==200:
    sequence[200]+=1
    if sequence[200]>1:p['start_ticks']='replacement'
   return p
  self.procmock.side_effect=proc
  with self.assertRaises(ValueError):mod._admission(self.root,'kit-pubsub')

class UnitIdentity(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='svf-foundation-');self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.name=mod.FAMILIES['kit-pubsub'][1][0];self.home=self.root/'home';fragment=self.home/'.config/systemd/user'/self.name;fragment.parent.mkdir(parents=True);fragment.write_text('owned unit');fragment.chmod(0o600)
  self.expected={'fragment':str(fragment),'fragment_sha256':mod.sha(fragment),'cwd':str(self.root),'argv':['/owned/python','native.py'],'binary_sha256':'a'*64,'ports':[18314],'environment':{'SVF_STRICT':'1'}}
  self.unit={'Id':self.name,'MainPID':'123','LoadState':'loaded','ActiveState':'active','SubState':'running','FragmentPath':str(fragment),'DropInPaths':'','NeedDaemonReload':'no','ControlGroup':'/owned/'+self.name,'InvocationID':'own-invocation','WorkingDirectory':str(self.root),'KillMode':'control-group','ExecStart':'{ path=/owned/python ; argv[]=/owned/python native.py ; ignore_errors=no ; }'}
  self.process={'pid':123,'start_ticks':'12300','uid':os.getuid(),'argv':self.expected['argv'][:],'cwd':str(self.root),'binary_sha256':'a'*64,'ports':[18314],'environment':{'SVF_STRICT':'1'},'cgroups':['0::'+self.unit['ControlGroup']]}
  for context in [patch.object(mod.Path,'home',return_value=self.home),patch.object(mod.subprocess,'check_output',side_effect=lambda *a,**k:'\n'.join(k+'='+v for k,v in self.unit.items())),patch.object(mod,'process',side_effect=lambda p:copy.deepcopy(self.process))]:
   context.start();self.addCleanup(context.stop)
 def test_exact_registered_live_unit_identity(self):
  self.assertEqual(mod.unit_identity(self.root,self.name,self.expected),{'pid':123,'start_ticks':'12300','unit':self.name,'invocation_id':'own-invocation','control_group':'/owned/'+self.name})
 def test_unregistered_unit_never_queries_systemd(self):
  with patch.object(mod.subprocess,'check_output')as query:
   with self.assertRaises(ValueError):mod.unit_identity(self.root,'foreign.service',self.expected)
   query.assert_not_called()
 def test_loaded_unit_guards(self):
  for key,bad in [('Id','foreign.service'),('ActiveState','inactive'),('SubState','exited'),('DropInPaths','/foreign/drop-in.conf'),('NeedDaemonReload','yes'),('InvocationID',''),('KillMode','process'),('ExecStart','{ argv[]=/owned/python attack.py ; }')]:
   with self.subTest(key=key):
    original=self.unit[key];self.unit[key]=bad
    with self.assertRaises(ValueError):mod.unit_identity(self.root,self.name,self.expected)
    self.unit[key]=original
 def test_process_binary_argv_cwd_socket_environment_cgroup_guards(self):
  for key,bad in [('argv',['python','foreign.py']),('cwd','/foreign'),('binary_sha256','b'*64),('ports',[]),('environment',{'SVF_STRICT':'0'}),('cgroups',['0::/foreign'])]:
   with self.subTest(key=key):
    original=self.process[key];self.process[key]=bad
    with self.assertRaises(ValueError):mod.unit_identity(self.root,self.name,self.expected)
    self.process[key]=original
 def test_changed_or_writable_unit_fragment_refused(self):
  p=Path(self.expected['fragment']);p.write_text('changed')
  with self.assertRaises(ValueError):mod.unit_identity(self.root,self.name,self.expected)
  self.expected['fragment_sha256']=mod.sha(p);p.chmod(0o666)
  with self.assertRaises(ValueError):mod.unit_identity(self.root,self.name,self.expected)
 def test_only_valid_registered_activating_zero_pid_is_typed_starting(self):
  for substate in ('start','auto-restart'):
   self.unit.update(ActiveState='activating',SubState=substate,MainPID='0',InvocationID='')
   with self.subTest(substate=substate),patch.object(mod,'process')as observed:
    with self.assertRaises(mod.ServiceStarting)as pending:mod.unit_identity(self.root,self.name,self.expected)
    self.assertEqual(pending.exception.unit,self.name);observed.assert_not_called()
 def test_starting_cannot_mask_wrong_unit_fragment_argv_or_unknown_state(self):
  self.unit.update(ActiveState='activating',SubState='auto-restart',MainPID='0')
  for key,value in [('ExecStart','{ argv[]=/foreign/command ; }'),('DropInPaths','/foreign/drop-in'),('NeedDaemonReload','yes'),('ActiveState','failed'),('SubState','unknown')]:
   original=self.unit[key];self.unit[key]=value
   with self.subTest(field=key):
    with self.assertRaises(ValueError)as caught:mod.unit_identity(self.root,self.name,self.expected)
    self.assertNotIsInstance(caught.exception,mod.ServiceStarting)
   self.unit[key]=original


class PeerGuards(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='svf-foundation-');self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.cfg={'pubsub_peers':[]};self.proc={};self.identities={};self.requests=[]
  for i,letter in enumerate('ab'):
   repo=self.root/m.RUNTIME/'backends/native-pubsub'/letter;repo.mkdir(parents=True);(repo/'config').write_text('{}');(repo/'config').chmod(0o600)
   unit='swissknife-visual-functional-pubsub-'+letter+'.service';api='http://127.0.0.1:'+str(5032+i);pid=100+i
   self.cfg['pubsub_peers'].append({'unit':unit,'api':api,'repo':str(repo),'config_sha256':m.sha(repo/'config'),'node_id':'fixture-node-'+letter,'unit_registration':{'ports':[5032+i],'environment':{'IPFS_PATH':str(repo)}}})
   self.identities[unit]={'pid':pid,'start_ticks':str(pid),'unit':unit,'invocation_id':'fixture-'+letter,'control_group':'/owned/'+unit}
   self.proc[pid]={'environment':{'IPFS_PATH':str(repo)},'uid':os.getuid(),'executable_path':'/owned/ipfs','binary_sha256':'a'*64}
  self.payloads={peer['api']:json.dumps({'ID':peer['node_id']}).encode() for peer in self.cfg['pubsub_peers']}
  def response(request,timeout):
   self.assertEqual(timeout,5);self.assertEqual(request.method,'POST');self.requests.append(request.full_url);return io.BytesIO(self.payloads[request.full_url.removesuffix('/api/v0/id')])
  for p in [patch.object(m,'_registration',return_value=self.cfg),patch.object(m,'unit_identity',side_effect=lambda root,unit,expected:copy.deepcopy(self.identities[unit])),patch.object(m,'process',side_effect=lambda pid:copy.deepcopy(self.proc[pid])),patch('urllib.request.urlopen',side_effect=response)]:p.start();self.addCleanup(p.stop)
 def inspect(self):return m.inspect_registered_pubsub_peers(self.root)
 def test_two_actual_distinct_peer_identities_preserve_explicit_aliases(self):
  result=self.inspect();self.assertEqual(len(result),2);self.assertEqual(len(self.requests),2)
  for actual,expected in zip(result,self.cfg['pubsub_peers']):
   self.assertEqual(actual['api_url'],expected['api']);self.assertEqual(actual['repo_path'],expected['repo']);self.assertEqual(actual['node_id'],expected['node_id']);self.assertTrue(actual['swarm_multiaddr'].endswith('/p2p/'+expected['node_id']))
 def test_missing_or_foreign_registered_peer_refuses_before_rpc(self):
  for change in ['missing','foreign-api']:
   original=copy.deepcopy(self.cfg['pubsub_peers'])
   if change=='missing':self.cfg['pubsub_peers'].pop()
   else:self.cfg['pubsub_peers'][0]['api']='http://127.0.0.1:5021'
   with self.subTest(change=change),self.assertRaises(ValueError):self.inspect()
   self.cfg['pubsub_peers']=original
  self.assertEqual(self.requests,[])
 def test_wrong_node_id_and_oversized_body_refuse(self):
  api=self.cfg['pubsub_peers'][0]['api']
  for body in [b'{"ID":"foreign"}',b'x'*16385]:
   self.payloads[api]=body
   with self.subTest(bytes=len(body)),self.assertRaises(ValueError):self.inspect()
 def test_wrong_repo_or_modified_configuration_refuses_before_rpc(self):
  peer=self.cfg['pubsub_peers'][0];self.proc[100]['environment']['IPFS_PATH']='/foreign'
  with self.assertRaises(ValueError):self.inspect()
  self.proc[100]['environment']['IPFS_PATH']=peer['repo'];(Path(peer['repo'])/'config').write_text('{"foreign":true}')
  with self.assertRaises(ValueError):self.inspect()
  self.assertEqual(self.requests,[])
 def test_same_peer_identity_cannot_be_two_peer_delivery_proof(self):
  self.cfg['pubsub_peers'][1]['node_id']=self.cfg['pubsub_peers'][0]['node_id'];self.payloads[self.cfg['pubsub_peers'][1]['api']]=self.payloads[self.cfg['pubsub_peers'][0]['api']]
  with self.assertRaises(ValueError):self.inspect()
 def test_generation_change_during_api_snapshot_refused(self):
  calls=0
  def identity(root,unit,expected):
   nonlocal calls
   calls+=1;p=copy.deepcopy(self.identities[unit]);p['start_ticks']=str(calls);return p
  with patch.object(m,'unit_identity',side_effect=identity),self.assertRaises(ValueError):self.inspect()
 def test_only_owned_api_optional_swarm_ports_and_exact_repo_environment_are_admitted(self):
  original=copy.deepcopy(self.cfg['pubsub_peers'][0]['unit_registration'])
  self.cfg['pubsub_peers'][0]['unit_registration']['ports']=[5032,40032];self.assertEqual(len(self.inspect()),2)
  for ports in [[5032,40033],[5021],[],[5032,8091]]:
   self.cfg['pubsub_peers'][0]['unit_registration']={**original,'ports':ports}
   with self.subTest(ports=ports),self.assertRaises(ValueError):self.inspect()
  self.cfg['pubsub_peers'][0]['unit_registration']={**original,'environment':{'IPFS_PATH':'/foreign'}}
  with self.assertRaises(ValueError):self.inspect()
 def test_peer_api_port_cannot_be_omitted_from_registered_process_listeners(self):
  self.cfg['pubsub_peers'][0]['unit_registration']['ports']=[]
  with self.assertRaises(ValueError):self.inspect()
  self.assertEqual(self.requests,[])

class CaptureAdmission(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix='svf-foundation-capture-');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name);self.family='kit-pubsub';self.native={'pid':os.getpid(),'start_ticks':Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19],'invocation_id':uuid.uuid4().hex};self.expected={p:hashlib.sha256(p.encode()).hexdigest() for p in helper.REQUIRED_SOURCES[self.family]};self.lease=str(uuid.uuid4());self.birth='321';self.pin='a'*64;self.cfg={'protected_sha256':{'scripts/svf_backends/foundation_native_entrypoint.py':self.pin}};self.directory=self.root/helper.RUNTIME/'backends/foundation-call-witness'/self.family/self.native['invocation_id'];self.directory.mkdir(parents=True,mode=0o700);self.file=self.directory/'observer.json';self.capture=self.directory/'capture.json';self.observer={'schema':'swissknife.foundation-sdk-call-observer.v1','family':self.family,'invocation_id':self.native['invocation_id'],'identity':{k:self.native[k] for k in ('pid','start_ticks')},'observer_sha256':self.pin,'source_sha256':self.expected,'observational_only':True,'authenticated_origin':False,'completion_authority':False};self.save()
 def save(self):self.file.write_text(json.dumps(self.observer));self.file.chmod(0o600)
 def arm(self):return helper._arm_capture(self.root,self.cfg,self.family,self.native,self.expected,self.lease,self.birth)
 def test_actual_private_filesystem_capture_is_source_owner_hash_bound_and_0600(self):
  before=time.time();returned=self.arm();after=time.time();raw=self.capture.read_bytes();value=json.loads(raw);self.assertEqual(stat.S_IMODE(self.capture.stat().st_mode),0o600);self.assertEqual(value['native_process'],self.observer['identity']);self.assertEqual(value['task_id'],'SVF-043');self.assertEqual(value['lease_id'],self.lease);self.assertEqual(value['foreground_birth'],self.birth);self.assertEqual(value['expected_sources'],self.expected);self.assertTrue(before<=value['issued_at']<=after);self.assertEqual(value['expires_at']-value['issued_at'],300);self.assertEqual(returned['capture']['sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(returned['capture']['bytes'],len(raw));self.assertEqual(returned['capture_id'],value['capture_id']);self.assertEqual(returned['observer_source']['sha256'],self.pin);self.assertFalse(value['completion_authority'])
 def test_wrong_native_birth_and_pid_refuse_without_authorized_capture(self):
  for field,value in [('pid',self.native['pid']+100),('start_ticks','old')]:
   self.observer['identity']={k:self.native[k] for k in ('pid','start_ticks')};self.observer['identity'][field]=value;self.save()
   with self.subTest(field=field),self.assertRaises(ValueError):self.arm()
   self.assertFalse(self.capture.exists())
 def test_wrong_observer_pin_and_source_map_refuse_without_capture(self):
  self.observer['observer_sha256']='0'*64;self.save()
  with self.assertRaises(ValueError):self.arm()
  self.assertFalse(self.capture.exists());self.observer['observer_sha256']=self.pin;self.observer['source_sha256']={};self.save()
  with self.assertRaises(ValueError):self.arm()
  self.assertFalse(self.capture.exists())
 def test_wrong_family_invocation_and_authority_flags_refuse(self):
  for field,value in [('family','accelerate-supervisor'),('invocation_id',uuid.uuid4().hex),('authenticated_origin',True),('observational_only',False),('completion_authority',True)]:
   original=self.observer[field];self.observer[field]=value;self.save()
   with self.subTest(field=field),self.assertRaises(ValueError):self.arm()
   self.assertFalse(self.capture.exists());self.observer[field]=original
 def test_existing_capture_is_never_overwritten(self):
  first=self.arm();before=self.capture.read_bytes()
  with self.assertRaises(ValueError):self.arm()
  self.assertEqual(self.capture.read_bytes(),before);self.assertEqual(helper.sha(self.capture),first['capture']['sha256'])
 def test_observer_symlink_cannot_authorize_capture(self):
  target=self.root/'actual-observer.json';self.file.rename(target);self.file.symlink_to(target)
  with self.assertRaises(ValueError):self.arm()
  self.assertFalse(self.capture.exists())
 def test_capture_symlink_cannot_overwrite_foreign_target(self):
  target=self.root/'unrelated.json';target.write_text('preserve exact bytes');self.capture.symlink_to(target)
  with self.assertRaises(ValueError):self.arm()
  self.assertEqual(target.read_text(),'preserve exact bytes');self.assertTrue(self.capture.is_symlink())
 def test_writable_observer_file_cannot_authorize_capture(self):
  self.file.chmod(0o666)
  with self.assertRaises(ValueError):self.arm()
  self.assertFalse(self.capture.exists())

if __name__=='__main__':unittest.main(verbosity=2)
