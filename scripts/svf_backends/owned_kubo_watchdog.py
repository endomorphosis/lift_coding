#!/usr/bin/env python3
"""Observe one registered Kubo owner; opt-in bounded recovery of latched RW errors.

Never a task-completion authority. No discovery, installation, arbitrary commands,
shared-daemon restart, or counter reset. The SDK probe pins and verifies one owned nonce block, then unpins it.
"""
from __future__ import annotations
import argparse
import base64
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time
import uuid

SCHEMA = 'swissknife.owned-kubo-supervisor.v1'
STATE_SCHEMA = 'swissknife.owned-kubo-watchdog-state.v1'
UNIT = 'swissknife-visual-functional-native-ipfs.service'
PROBE = b'swissknife-owned-kubo-write-canary-v1\n'
PROBE_SHA = hashlib.sha256(PROBE).hexdigest()
PROBE_CID = 'b' + base64.b32encode(bytes([1, 85, 18, 32]) + hashlib.sha256(PROBE).digest()).decode().lower().rstrip('=')
SDK_RELATIVE = 'external/ipfs_kit/ipfs_kit_py/assurance/pinned_ipfs.py'
IDENTITY_KEYS = {'schema','owner','uid','unit','repo','node_id','api','gateway','binary','binary_sha256','fragment','fragment_sha256','argv'}


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def safe_file(path, *, private=False):
    path = Path(path)
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & (0o077 if private else 0o022):
        raise ValueError('unsafe owner-controlled regular file')
    if info.st_size > 1024 * 1024: raise ValueError('oversized registration/state')
    return path


def load_config(path):
    cfg = json.loads(safe_file(path).read_text())
    if set(cfg) != {'identity','marker','root','state','status','sdk_sha256','cooldown_seconds','failure_threshold','poll_seconds','hold_path'}:
        raise ValueError('unknown or missing config fields')
    ident = cfg['identity']
    if type(ident) is not dict or set(ident) != IDENTITY_KEYS: raise ValueError('invalid identity registration')
    if ident['schema'] != SCHEMA or ident['owner'] != 'swissknife_visual_functional' or type(ident['uid']) is not int or ident['uid'] != os.getuid() or ident['unit'] != UNIT:
        raise ValueError('foreign owner/unit')
    if ident['api'] != 'http://127.0.0.1:5031' or ident['gateway'] != 'http://127.0.0.1:8092':
        raise ValueError('only registered private node endpoints are permitted; legacy nodes forbidden')
    root = Path(cfg['root'])
    repo = Path(ident['repo'])
    if not root.is_absolute() or root.resolve() != root or not repo.is_absolute() or repo.resolve() != repo or not repo.is_relative_to(root / 'data/agent_supervisor/swissknife_visual_functional/backends'):
        raise ValueError('repo is outside canonical owned namespace')
    if Path(cfg['marker']) != repo.parent / 'supervised-owner.json': raise ValueError('wrong owner marker location')
    if ident['argv'] != [ident['binary'],'daemon','--enable-gc','--migrate=false','--agent-version-suffix=svf-owned-recovery-20261027']:
        raise ValueError('unregistered daemon argv')
    if any(type(v) is not str or not v or re.search(r'\s',v) for v in ident['argv']): raise ValueError('invalid argv')
    if Path(ident['fragment']) != Path.home()/'.config/systemd/user'/UNIT: raise ValueError('foreign unit fragment')
    for key in ('binary_sha256','fragment_sha256'):
        if not re.fullmatch('[0-9a-f]{64}',ident[key]): raise ValueError('unqualified hash')
    if not re.fullmatch('[0-9a-f]{64}',cfg['sdk_sha256']): raise ValueError('unqualified SDK source')
    for key in ('state','status','hold_path'):
        p = Path(cfg[key])
        if not p.is_absolute() or p.resolve() != p or not p.is_relative_to(root / 'data/agent_supervisor/swissknife_visual_functional'):
            raise ValueError('runtime path escapes owner namespace')
    if any(type(cfg[k]) is not int for k in ('cooldown_seconds','failure_threshold','poll_seconds')): raise ValueError('timing must be integer seconds/count')
    if not 30 <= cfg['cooldown_seconds'] <= 3600 or not 2 <= cfg['failure_threshold'] <= 6 or not 10 <= cfg['poll_seconds'] <= 300: raise ValueError('unbounded timing')
    return cfg


def atomic(path, value):
    path = Path(path)
    if path.is_symlink(): raise ValueError('symlink output refused')
    if path.exists(): safe_file(path, private=True)
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    temporary=path.with_name('.'+path.name+'.'+uuid.uuid4().hex)
    try:
        fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'w') as out:
            json.dump(value,out,sort_keys=True,allow_nan=False);out.flush();os.fsync(out.fileno())
        os.replace(temporary,path)
        fd=os.open(path.parent,os.O_DIRECTORY);os.fsync(fd);os.close(fd)
    finally: temporary.unlink(missing_ok=True)


class Host:
    def __init__(self,cfg): self.cfg=cfg;self.client=None
    def storage(self):
        sys.path.insert(0,str(Path(self.cfg['root'])/'scripts'))
        from lift_ipfs_accelerate_bootstrap import bootstrap_ipfs_accelerate
        bootstrap_ipfs_accelerate(Path(self.cfg['root'])/'scripts/owned_kubo_watchdog.py')
        from ipfs_accelerate_py.agent_supervisor.rescue.storage_pressure import check_storage_capacity
        repo=Path(self.cfg['identity']['repo'])
        return check_storage_capacity([repo,repo/'blocks',repo/'datastore',Path(self.cfg['state']).parent],durable=True)
    def emergency(self,payload):
        from ipfs_accelerate_py.agent_supervisor.rescue.storage_pressure import publish_emergency_status
        publish_emergency_status(Path(self.cfg['status']),payload)
    def unit(self):
        names=['Id','LoadState','ActiveState','MainPID','FragmentPath','DropInPaths','NeedDaemonReload','ControlGroup','ExecStart','WorkingDirectory']
        result=subprocess.run(['systemctl','--user','show',UNIT,*['--property='+v for v in names]],capture_output=True,text=True,timeout=8,check=True)
        return dict(line.split('=',1) for line in result.stdout.splitlines() if '=' in line)
    def process(self,pid):
        proc=Path('/proc')/str(pid);fields=(proc/'stat').read_text().rsplit(')',1)[1].split()
        if fields[0]=='Z': raise ValueError('zombie owner')
        env=dict(item.split(b'=',1) for item in (proc/'environ').read_bytes().split(b'\0') if b'=' in item)
        sockets=set()
        for entry in (proc/'fd').iterdir():
            try: sockets.add(os.readlink(entry))
            except FileNotFoundError: pass  # A closed unrelated descriptor is normal; missing listeners still refuse proof.
        owned_ports=set()
        for row in Path('/proc/net/tcp').read_text().splitlines()[1:]:
            values=row.split()
            if values[3]=='0A' and values[1].startswith('0100007F:') and 'socket:['+values[9]+']' in sockets:
                owned_ports.add(int(values[1].split(':')[1],16))
        return {'pid':pid,'uid':proc.stat().st_uid,'start_ticks':fields[19], 'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                'argv':(proc/'cmdline').read_bytes().rstrip(b'\0').decode().split('\0'), 'exe_sha256':sha(proc/'exe'),
                'cwd':str((proc/'cwd').resolve()),'ipfs_path':os.fsdecode(env.get(b'IPFS_PATH',b'')),
                'cgroups':(proc/'cgroup').read_text().splitlines(),'ports':sorted(owned_ports)}
    def sdk(self):
        cfg=self.cfg;path=Path(cfg['root'])/SDK_RELATIVE
        if sha(path)!=cfg['sdk_sha256']: raise ValueError('SDK source drift')
        if self.client is None:
            sys.path.insert(0,str(Path(cfg['root'])/'external/ipfs_kit'))
            import ipfs_kit_py.assurance.pinned_ipfs as sdk
            if Path(sdk.__file__).resolve()!=path: raise ValueError('foreign SDK import')
            self.client=sdk.LivePinnedIpfsAdapter(api_url=cfg['identity']['api'],timeout=5)
        if self.client.simulated or not self.client.live_provider or self.client._transport is not None: raise ValueError('simulated SDK refused')
        return self.client
    def node_id(self):
        result=self.sdk().node_id(deadline=time.monotonic()+5)
        if result.success is not True: raise ValueError('native node identity unavailable')
        return result.metadata['ID']
    def probe(self,pending):
        data=probe_bytes(pending)
        client=self.sdk();deadline=time.monotonic()+15
        added=client.add(data,pin=True,deadline=deadline)
        if added.success is not True or added.resulting_content_cid!=pending['cid']: raise ValueError('native fresh pin failed CID verification')
        read=client.cat(pending['cid'],expected_sha256=pending['sha256'],deadline=deadline)
        if read.success is not True or read.data!=data: raise ValueError('native cat failed owned nonce byte verification')
        # Only the persisted owned nonce, independently read/hash-verified above,
        # can enter public SDK unpin. No arbitrary user CID is accepted.
        removed=client.unpin(pending['cid'],deadline=deadline)
        if removed.success is not True: raise ValueError('native owned-nonce cleanup failed')
        if sha(Path(self.cfg['root'])/SDK_RELATIVE)!=self.cfg['sdk_sha256']: raise ValueError('SDK changed during probe')
        return {'cid':pending['cid'],'sha256':pending['sha256'],'bytes':len(data),'sdk_source_sha256':self.cfg['sdk_sha256'],'sdk_class':'ipfs_kit_py.assurance.pinned_ipfs.LivePinnedIpfsAdapter','sdk_methods':['add','cat','unpin'],'pin_writer_rw_verified':True,'owned_nonce_unpinned':True,'simulated':False}
    def restart(self):
        subprocess.run(['systemctl','--user','restart',UNIT],capture_output=True,timeout=45,check=True)
    def wait(self): time.sleep(1)


def identity(cfg,host):
    ident=cfg['identity'];marker=json.loads(safe_file(cfg['marker']).read_text())
    if marker!=ident: raise ValueError('owner marker differs from pinned registration')
    if sha(safe_file(ident['fragment']))!=ident['fragment_sha256'] or sha(ident['binary'])!=ident['binary_sha256']: raise ValueError('binary/unit fragment drift')
    unit=host.unit()
    if (unit.get('Id')!=UNIT or unit.get('LoadState')!='loaded' or unit.get('ActiveState')!='active' or unit.get('FragmentPath')!=ident['fragment'] or unit.get('DropInPaths') or unit.get('NeedDaemonReload')!='no' or unit.get('WorkingDirectory')!=str(Path(ident['repo']).parent)):
        raise ValueError('unit is not the exact active registered owner')
    argv=re.search(r'argv\[\]=(.*?) ;',unit.get('ExecStart',''))
    if not argv or argv.group(1)!=' '.join(ident['argv']): raise ValueError('loaded unit command differs')
    pid=int(unit['MainPID']);p=host.process(pid)
    if (pid<=1 or p['uid']!=ident['uid'] or p['argv']!=ident['argv'] or p['exe_sha256']!=ident['binary_sha256'] or p['cwd']!=str(Path(ident['repo']).parent) or p['ipfs_path']!=ident['repo'] or not p['start_ticks'] or not p['boot_id'] or not {5031,8092}.issubset(p['ports'])):
        raise ValueError('process identity/socket/repo does not match registered owner')
    group=unit.get('ControlGroup','')
    if not group or not group.endswith('/'+UNIT) or not any(row.split(':',2)[-1]==group for row in p['cgroups']): raise ValueError('owner cgroup differs')
    repo_config=json.loads(safe_file(Path(ident['repo'])/'config').read_text())
    if (repo_config['Identity']['PeerID']!=ident['node_id'] or repo_config['Addresses']['API']!='/ip4/127.0.0.1/tcp/5031' or repo_config['Addresses']['Gateway']!='/ip4/127.0.0.1/tcp/8092' or repo_config.get('Bootstrap')!=[] or repo_config['Discovery']['MDNS']['Enabled'] is not False or repo_config['AutoConf']['Enabled'] is not False or repo_config['Routing']['Type']!='none' or repo_config['Routing'].get('DelegatedRouters')!=[] or repo_config['Addresses'].get('Swarm')!=['/ip4/127.0.0.1/tcp/40031'] or repo_config.get('Gateway',{}).get('NoFetch') is not True):
        raise ValueError('registered repo isolation/identity differs')
    spec=repo_config.get('Datastore',{}).get('Spec',{})
    mounts=spec.get('mounts',[])
    if spec.get('type')!='mount' or len(mounts)!=2 or {(m.get('mountpoint'),m.get('path'),m.get('type')) for m in mounts}!={('/blocks','blocks','flatfs'),('/','datastore','levelds')}:
        raise ValueError('unregistered datastore paths/types')
    if host.node_id()!=ident['node_id']: raise ValueError('API belongs to another node')
    # Re-read after API access so PID reuse/replacement during proof cannot authorize writes.
    if host.process(pid)!=p: raise ValueError('owner changed during identity proof')
    return p


def probe_bytes(pending):
    if type(pending) is not dict or set(pending)!={'nonce','cid','sha256'} or type(pending['nonce']) is not str or re.fullmatch('[0-9a-f]{32}',pending['nonce']) is None:
        raise ValueError('invalid owned probe intent')
    data=PROBE+pending['nonce'].encode()+b'\n'
    digest=hashlib.sha256(data).hexdigest()
    cid='b'+base64.b32encode(bytes([1,85,18,32])+bytes.fromhex(digest)).decode().lower().rstrip('=')
    if pending['cid']!=cid or pending['sha256']!=digest: raise ValueError('probe intent does not bind owned nonce bytes')
    return data


def new_probe():
    nonce=uuid.uuid4().hex;data=PROBE+nonce.encode()+b'\n';digest=hashlib.sha256(data).hexdigest()
    return {'nonce':nonce,'sha256':digest,'cid':'b'+base64.b32encode(bytes([1,85,18,32])+bytes.fromhex(digest)).decode().lower().rstrip('=')}


def load_state(cfg):
    path=Path(cfg['state']);fingerprint=hashlib.sha256(json.dumps(cfg['identity'],sort_keys=True).encode()).hexdigest()
    if path.is_symlink(): raise ValueError('symlink journal refused')
    if not path.exists(): return {'schema':STATE_SCHEMA,'identity_sha256':fingerprint,'restart_attempts':0,'restarts':[],'total_rw_failures':0,'consecutive_rw_failures':0,'retry_after':0,'pending_probe':None,'work_complete':False,'completion_authority':False}
    state=json.loads(safe_file(path,private=True).read_text())
    if state.get('schema')!=STATE_SCHEMA or state.get('identity_sha256')!=fingerprint or state.get('work_complete') is not False or state.get('completion_authority') is not False: raise ValueError('foreign/malformed restart journal')
    for key in ('restart_attempts','total_rw_failures','consecutive_rw_failures','retry_after'):
        if type(state.get(key)) is not int or state[key]<0: raise ValueError('malformed restart counters')
    if state['restart_attempts']>3 or type(state.get('restarts')) is not list or len(state['restarts'])!=state['restart_attempts'] or state['total_rw_failures']<state['consecutive_rw_failures']: raise ValueError('inconsistent durable budget')
    for row in state['restarts']:
        if set(row)!={'at','old_pid','old_start_ticks','outcome'} or type(row['at']) is not int or type(row['old_pid']) is not int or type(row['old_start_ticks']) is not str or row['outcome'] not in {'reserved','verified','failed'}: raise ValueError('invalid restart history')
    if 'pending_probe' not in state: raise ValueError('missing probe intent state')
    if state['pending_probe'] is not None: probe_bytes(state['pending_probe'])
    return state


def cycle(cfg,host,*,apply=False,now=None):
    now=int(time.time()) if now is None else now
    status={'schema':'swissknife.owned-kubo-watchdog-observation.v1','at':now,'work_complete':False,'completion_authority':False,'unit':UNIT}
    capacity=host.storage()
    if capacity.get('ok') is not True:
        status.update(action='storage_wait',capacity=capacity);host.emergency(status);return status
    if Path(cfg['hold_path']).exists(): return {**status,'action':'operator_hold'}
    before=identity(cfg,host);state=load_state(cfg)
    capacity=host.storage()
    if capacity.get('ok') is not True:
        status.update(action='storage_wait',capacity=capacity);host.emergency(status);return status
    status.update(owner={key:before[key] for key in ('pid','start_ticks','boot_id','uid')},restart_attempts=state['restart_attempts'])
    if state['pending_probe'] is None:
        state['pending_probe']=new_probe();atomic(cfg['state'],state)
    try:
        proof=host.probe(state['pending_probe'])
        if identity(cfg,host)!=before: raise ValueError('owner changed during RW probe')
    except Exception as error:
        # A different process/registration must never turn its failure into restart authorization.
        if identity(cfg,host)!=before: raise ValueError('owner changed after probe error') from error
        capacity=host.storage()
        if capacity.get('ok') is not True:
            status.update(action='storage_wait',capacity=capacity);host.emergency(status);return status
        state['total_rw_failures']+=1;state['consecutive_rw_failures']+=1
        atomic(cfg['state'],state)
        status.update(action='rw_failure',error_type=type(error).__name__,consecutive_rw_failures=state['consecutive_rw_failures'],total_rw_failures=state['total_rw_failures'])
        if state['consecutive_rw_failures']<cfg['failure_threshold']: return status
        if state['restart_attempts']>=3: return {**status,'action':'attention_required','reason':'lifetime_restart_budget_exhausted'}
        if now<state['retry_after']: return {**status,'action':'cooldown','retry_after':state['retry_after']}
        if not apply: return {**status,'action':'restart_eligible','reason':'repeated_sdk_rw_failure_after_durable_capacity'}
        if identity(cfg,host)!=before: raise ValueError('owner changed before restart reservation')
        if Path(cfg['hold_path']).exists(): return {**status,'action':'operator_hold'}
        capacity=host.storage()
        if capacity.get('ok') is not True:
            status.update(action='storage_wait',capacity=capacity);host.emergency(status);return status
        state['restart_attempts']+=1;state['retry_after']=now+cfg['cooldown_seconds']
        state['restarts'].append({'at':now,'old_pid':before['pid'],'old_start_ticks':before['start_ticks'],'outcome':'reserved'})
        atomic(cfg['state'],state)  # Durable admission BEFORE action; never refund unknown outcome.
        try:
            if identity(cfg,host)!=before or Path(cfg['hold_path']).exists(): raise ValueError('owner/HOLD changed before exact-unit action')
            host.restart()
            last=None
            verification_deadline=time.monotonic()+30
            for _ in range(30):
                if time.monotonic()>=verification_deadline: break
                try:
                    current=identity(cfg,host)
                    if current==before: raise ValueError('restart did not replace the registered process')
                    proof=host.probe(state['pending_probe'])
                    if identity(cfg,host)!=current: raise ValueError('post-restart owner changed')
                    state['restarts'][-1]['outcome']='verified';state['consecutive_rw_failures']=0;state['pending_probe']=None
                    atomic(cfg['state'],state)
                    return {**status,'action':'recovered','restart_attempts':state['restart_attempts'],'proof':proof,'owner':current}
                except Exception as error: last=error;host.wait()
            raise RuntimeError('registered node did not recover within bounded verification') from last
        except Exception:
            state['restarts'][-1]['outcome']='failed';atomic(cfg['state'],state);raise
    state['consecutive_rw_failures']=0;state['pending_probe']=None;atomic(cfg['state'],state)
    return {**status,'action':'healthy','proof':proof,'total_rw_failures':state['total_rw_failures']}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--config',required=True);parser.add_argument('--apply',action='store_true');parser.add_argument('--once',action='store_true');args=parser.parse_args()
    cfg=load_config(args.config);host=Host(cfg)
    # Do not create even the persistent lock while its filesystem cannot commit.
    # A filesystem may fill between the durable probe and lock creation.
    while True:
        try:
            if host.storage().get('ok') is True:
                lock=Path(cfg['state']).with_suffix('.lock');lock.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
                fd=os.open(lock,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
                if os.fstat(fd).st_uid!=os.getuid() or os.fstat(fd).st_mode&0o077: raise ValueError('unsafe lock')
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
                break
        except OSError as error:
            if error.errno not in {28,122}: raise
        result={'action':'storage_wait','work_complete':False,'completion_authority':False};host.emergency(result)
        if args.once: print(json.dumps(result));return 0
        time.sleep(cfg['poll_seconds'])
    while True:
        try:
            result=cycle(cfg,host,apply=args.apply);atomic(cfg['status'],result)
        except OSError as error:
            if error.errno not in {28,122}: raise
            result={'action':'storage_wait','work_complete':False,'completion_authority':False};host.emergency(result)
        except Exception as error:
            result={'action':'observation_blocked','error_type':type(error).__name__,'reason':str(error)[:300],'work_complete':False,'completion_authority':False}
            try: atomic(cfg['status'],result)
            except OSError as secondary:
                if secondary.errno not in {28,122}: raise
                result={'action':'storage_wait','work_complete':False,'completion_authority':False};host.emergency(result)
        if args.once:
            print(json.dumps(result));return 0
        time.sleep(cfg['poll_seconds'])

if __name__=='__main__': raise SystemExit(main())
