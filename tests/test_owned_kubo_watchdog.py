import copy
import contextlib
import io
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SOURCE=Path(__file__).resolve().parents[1]/'scripts/svf_backends/owned_kubo_watchdog.py'
spec=importlib.util.spec_from_file_location('owned_kubo_watchdog',SOURCE)
w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)


class Host:
    def __init__(self,cfg):
        self.cfg=cfg;self.cap=True;self.fail=True;self.restarts=0;self.probes=0;self.calls=[];self.pid=400;self.birth='50';self.foreign=False;self.identity_calls=0;self.change_at=0
    def storage(self):return {'ok':self.cap,'storage_pressure':not self.cap}
    def emergency(self,status):self.calls.append(status['action'])
    def unit(self):
        i=self.cfg['identity']
        return {'Id':w.UNIT,'LoadState':'loaded','ActiveState':'active','MainPID':str(self.pid),'FragmentPath':i['fragment'],'DropInPaths':'','NeedDaemonReload':'no','ControlGroup':'/user.slice/'+w.UNIT,'ExecStart':'{ path='+i['binary']+' ; argv[]='+' '.join(i['argv'])+' ; ignore_errors=no ; }','WorkingDirectory':str(Path(i['repo']).parent)}
    def process(self,pid):
        self.identity_calls+=1
        if self.change_at and self.identity_calls>=self.change_at:self.birth='reused'
        i=self.cfg['identity']
        return {'pid':pid,'uid':os.getuid(),'start_ticks':self.birth,'boot_id':'boot','argv':i['argv'],'exe_sha256':i['binary_sha256'],'cwd':str(Path(i['repo']).parent),'ipfs_path':i['repo'],'cgroups':['0::/user.slice/'+w.UNIT],'ports':[5031,8092]}
    def node_id(self):return 'foreign' if self.foreign else self.cfg['identity']['node_id']
    def probe(self,pending):
        self.probes+=1
        if self.fail:raise RuntimeError('latched native write failure')
        return {'cid':w.PROBE_CID,'sha256':w.PROBE_SHA}
    def restart(self):self.restarts+=1;self.pid+=1;self.birth=str(int(self.birth)+1);self.fail=False
    def wait(self):pass


class WatchdogTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);root=Path(self.tmp.name);runtime=root/'data/agent_supervisor/swissknife_visual_functional';repo=runtime/'backends/owned/repo';repo.mkdir(parents=True)
        fragment=root/'unit';fragment.write_text('unit')
        binary=root/'ipfs';binary.write_bytes(b'pinned binary')
        self.cfg={'identity':{'schema':w.SCHEMA,'owner':'swissknife_visual_functional','uid':os.getuid(),'unit':w.UNIT,'repo':str(repo),'node_id':'12D3ownednode','api':'http://127.0.0.1:5031','gateway':'http://127.0.0.1:8092','binary':str(binary),'binary_sha256':w.sha(binary),'fragment':str(fragment),'fragment_sha256':w.sha(fragment),'argv':[str(binary),'daemon','--enable-gc','--migrate=false','--agent-version-suffix=svf-owned-recovery-20261027']},'root':str(root),'marker':str(repo.parent/'supervised-owner.json'),'state':str(runtime/'watchdog/ipfs/state.json'),'status':str(runtime/'watchdog/ipfs/status.json'),'hold_path':str(runtime/'HOLD'),'sdk_sha256':'a'*64,'cooldown_seconds':300,'failure_threshold':2,'poll_seconds':30}
        Path(self.cfg['marker']).write_text(json.dumps(self.cfg['identity']))
        (repo/'config').write_text(json.dumps({'Identity':{'PeerID':'12D3ownednode'},'Addresses':{'API':'/ip4/127.0.0.1/tcp/5031','Gateway':'/ip4/127.0.0.1/tcp/8092','Swarm':['/ip4/127.0.0.1/tcp/40031']},'Gateway':{'NoFetch':True},'Datastore':{'Spec':{'type':'mount','mounts':[{'mountpoint':'/blocks','path':'blocks','type':'flatfs'},{'mountpoint':'/','path':'datastore','type':'levelds'}]}},'Bootstrap':[],'Discovery':{'MDNS':{'Enabled':False}},'AutoConf':{'Enabled':False},'Routing':{'Type':'none','DelegatedRouters':[]}}))
        for path in (fragment,binary,Path(self.cfg['marker']),repo/'config'):path.chmod(0o600)
        self.host=Host(self.cfg)
    def test_startup_lock_capacity_race_waits_without_restart_or_rpc(self):
        for number in (28,122):
            with self.subTest(errno=number),patch.object(w.sys,'argv',['watcher','--config','unused','--once']),patch.object(w,'load_config',return_value=self.cfg),patch.object(w,'Host',return_value=self.host),patch.object(w.os,'open',side_effect=OSError(number,'capacity race')),contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(w.main(),0)
            self.assertEqual(json.loads(out.getvalue())['action'],'storage_wait')
        self.assertEqual((self.host.probes,self.host.restarts),(0,0))
    def test_startup_permission_fault_is_not_storage_wait(self):
        with patch.object(w.sys,'argv',['watcher','--config','unused','--once']),patch.object(w,'load_config',return_value=self.cfg),patch.object(w,'Host',return_value=self.host),patch.object(w.os,'open',side_effect=PermissionError(13,'denied')):
            with self.assertRaises(PermissionError):w.main()
    def test_config_exact_endpoints_and_argv(self):
        cfg=copy.deepcopy(self.cfg);cfg['identity']['fragment']=str(Path.home()/'.config/systemd/user'/w.UNIT)
        config=Path(self.tmp.name)/'config.json';config.write_text(json.dumps(cfg));config.chmod(0o600)
        self.assertEqual(w.load_config(config)['identity']['api'],'http://127.0.0.1:5031')
        for field,value in [('api','http://127.0.0.1:5021'),('gateway','http://127.0.0.1:8091')]:
            bad=copy.deepcopy(cfg);bad['identity'][field]=value;config.write_text(json.dumps(bad))
            with self.assertRaisesRegex(ValueError,'legacy'):w.load_config(config)
    def test_wrong_socket_uid_cgroup_and_fragment_refused(self):
        for field,value in [('ports',[8092]),('uid',os.getuid()+1),('cgroups',['0::/foreign'])]:
            original=self.host.process
            self.host.process=lambda pid,field=field,value=value:{**original(pid),field:value}
            with self.assertRaises(ValueError):w.cycle(self.cfg,self.host,apply=True)
            self.host.process=original
        Path(self.cfg['identity']['fragment']).write_text('changed fragment')
        with self.assertRaisesRegex(ValueError,'drift'):w.cycle(self.cfg,self.host,apply=True)
        self.assertEqual(self.host.restarts,0)
    def test_low_storage_no_probe_restart_or_journal(self):
        self.host.cap=False
        self.assertEqual(w.cycle(self.cfg,self.host,apply=True)['action'],'storage_wait')
        self.assertEqual((self.host.probes,self.host.restarts),(0,0));self.assertFalse(Path(self.cfg['state']).exists())
    def test_hold_no_probe_or_budget(self):
        Path(self.cfg['hold_path']).touch()
        self.assertEqual(w.cycle(self.cfg,self.host,apply=True)['action'],'operator_hold');self.assertEqual(self.host.probes,0)
    def test_foreign_node_refused_no_write(self):
        self.host.foreign=True
        with self.assertRaisesRegex(ValueError,'another node'):w.cycle(self.cfg,self.host,apply=True)
        self.assertEqual((self.host.probes,self.host.restarts),(0,0))
    def test_wrong_marker_rejected(self):
        marker=Path(self.cfg['marker']);marker.write_text('{}')
        with self.assertRaisesRegex(ValueError,'marker'):w.cycle(self.cfg,self.host,apply=True)
        self.assertEqual(self.host.probes,0)
    def test_loaded_dropin_rejected(self):
        original=self.host.unit
        self.host.unit=lambda:{**original(),'DropInPaths':'/unknown.conf'}
        with self.assertRaisesRegex(ValueError,'exact active'):w.cycle(self.cfg,self.host,apply=True)
    def test_reused_pid_refused_before_probe(self):
        self.host.change_at=2
        with self.assertRaisesRegex(ValueError,'changed'):w.cycle(self.cfg,self.host,apply=True)
        self.assertEqual((self.host.probes,self.host.restarts),(0,0))
    def test_observe_only_counts_failure_without_restart_spend(self):
        w.cycle(self.cfg,self.host,now=1000)
        result=w.cycle(self.cfg,self.host,now=1030)
        self.assertEqual(result['action'],'restart_eligible');self.assertEqual(self.host.restarts,0)
        self.assertEqual(w.load_state(self.cfg)['restart_attempts'],0)
    def test_two_actual_failures_reserve_then_exact_restart_and_rw(self):
        w.cycle(self.cfg,self.host,apply=True,now=1000)
        restart=self.host.restart
        def checked_restart():
            state=w.load_state(self.cfg)
            self.assertEqual(state['restart_attempts'],1);self.assertEqual(state['restarts'][0]['outcome'],'reserved')
            restart()
        self.host.restart=checked_restart
        result=w.cycle(self.cfg,self.host,apply=True,now=1030)
        self.assertEqual(result['action'],'recovered');self.assertEqual(self.host.restarts,1)
        state=w.load_state(self.cfg);self.assertEqual(state['restart_attempts'],1);self.assertEqual(state['total_rw_failures'],2);self.assertEqual(state['consecutive_rw_failures'],0)
        w.cycle(self.cfg,self.host,apply=True,now=1040)
        self.assertEqual(w.load_state(self.cfg)['restart_attempts'],1)
    def test_lifetime_three_budget_never_success_reset(self):
        for n in range(3):
            self.host.fail=True;w.cycle(self.cfg,self.host,apply=True,now=1000+n*1000)
            self.assertEqual(w.cycle(self.cfg,self.host,apply=True,now=1030+n*1000)['action'],'recovered')
        self.host.fail=True;w.cycle(self.cfg,self.host,apply=True,now=5000)
        self.assertEqual(w.cycle(self.cfg,self.host,apply=True,now=5030)['reason'],'lifetime_restart_budget_exhausted')
        self.assertEqual(self.host.restarts,3);self.assertEqual(w.load_state(self.cfg)['restart_attempts'],3)
    def test_cooldown_retains_budget_and_history(self):
        w.cycle(self.cfg,self.host,apply=True,now=1000);w.cycle(self.cfg,self.host,apply=True,now=1030)
        self.host.fail=True;w.cycle(self.cfg,self.host,apply=True,now=1040)
        self.assertEqual(w.cycle(self.cfg,self.host,apply=True,now=1050)['action'],'cooldown');self.assertEqual(self.host.restarts,1)
    def test_space_recovers_then_latched_error_restarts_without_budget_reset(self):
        self.host.cap=False;w.cycle(self.cfg,self.host,apply=True,now=1000)
        self.host.cap=True;w.cycle(self.cfg,self.host,apply=True,now=1100)
        self.assertEqual(w.cycle(self.cfg,self.host,apply=True,now=1130)['action'],'recovered')
        self.assertEqual(w.load_state(self.cfg)['restart_attempts'],1)
    def test_failure_when_space_fills_does_not_count_rw_or_reserve(self):
        def fail(pending):self.host.cap=False;raise OSError(28,'full')
        self.host.probe=fail
        self.assertEqual(w.cycle(self.cfg,self.host,apply=True)['action'],'storage_wait')
        self.assertEqual(w.load_state(self.cfg)['total_rw_failures'],0);self.assertEqual(w.load_state(self.cfg)['restart_attempts'],0);self.assertEqual(self.host.restarts,0)
    def test_journal_failure_prevents_action(self):
        w.cycle(self.cfg,self.host,apply=True,now=1000)
        with patch.object(w,'atomic',side_effect=PermissionError('denied')):
            with self.assertRaises(PermissionError):w.cycle(self.cfg,self.host,apply=True,now=1030)
        self.assertEqual(self.host.restarts,0)
    def test_malformed_or_symlink_budget_never_resets(self):
        path=Path(self.cfg['state']);path.parent.mkdir(parents=True);path.write_text('{}');path.chmod(0o600)
        with self.assertRaisesRegex(ValueError,'journal'):w.cycle(self.cfg,self.host,apply=True)
        path.unlink();path.symlink_to(path.parent/'missing')
        with self.assertRaisesRegex(ValueError,'symlink'):w.cycle(self.cfg,self.host,apply=True)
    def test_unit_action_argv_is_exact_never_direct_kill(self):
        real=w.Host(self.cfg)
        with patch.object(w.subprocess,'run') as call:real.restart()
        self.assertEqual(call.call_args.args[0],['systemctl','--user','restart',w.UNIT])
    def test_probe_uses_sdk_fresh_owned_nonce_pin_cat_unpin(self):
        pending=w.new_probe();data=w.probe_bytes(pending)
        class Result:
            success=True;resulting_content_cid=pending['cid']
        result=Result();result.data=data
        class SDK:
            def __init__(self):self.calls=[]
            def add(self,data,**kw):self.calls.append(('add',data,kw));return result
            def cat(self,cid,**kw):self.calls.append(('cat',cid,kw));return result
            def unpin(self,cid,**kw):self.calls.append(('unpin',cid,kw));return result
        sdk=SDK();host=w.Host(self.cfg)
        with patch.object(host,'sdk',return_value=sdk),patch.object(w,'sha',return_value=self.cfg['sdk_sha256']):proof=host.probe(pending)
        self.assertEqual([row[0] for row in sdk.calls],['add','cat','unpin']);self.assertEqual(sdk.calls[0][1],data);self.assertTrue(sdk.calls[0][2]['pin']);self.assertEqual(sdk.calls[1][2]['expected_sha256'],pending['sha256']);self.assertTrue(proof['pin_writer_rw_verified']);self.assertTrue(proof['owned_nonce_unpinned'])
    def test_old_pinned_constant_success_cannot_hide_new_pin_failure(self):
        host=w.Host(self.cfg);calls=[]
        class SDK:
            def add(self,data,**kw):
                calls.append(data)
                if data==w.PROBE:return type('R',(),{'success':True,'resulting_content_cid':w.PROBE_CID})()
                raise RuntimeError('latched pin dirty writer')
        with patch.object(host,'sdk',return_value=SDK()):
            with self.assertRaisesRegex(RuntimeError,'dirty'):host.probe(w.new_probe())
        self.assertNotEqual(calls,[w.PROBE])
    def test_pending_intent_reused_and_success_changes_nonce_without_pin_accumulation(self):
        w.cycle(self.cfg,self.host,now=1000);first=w.load_state(self.cfg)['pending_probe']
        w.cycle(self.cfg,self.host,now=1030);self.assertEqual(w.load_state(self.cfg)['pending_probe'],first)
        self.host.fail=False;w.cycle(self.cfg,self.host,now=1060);self.assertIsNone(w.load_state(self.cfg)['pending_probe'])
        self.host.fail=True;w.cycle(self.cfg,self.host,now=1090);self.assertNotEqual(w.load_state(self.cfg)['pending_probe'],first)
    def test_arbitrary_cleanup_cid_refused_before_sdk_access(self):
        pending=w.new_probe();pending['cid']=w.PROBE_CID
        host=w.Host(self.cfg)
        with patch.object(host,'sdk') as sdk:
            with self.assertRaisesRegex(ValueError,'nonce bytes'):host.probe(pending)
            sdk.assert_not_called()

if __name__=='__main__':unittest.main()
