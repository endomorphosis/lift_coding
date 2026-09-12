from pathlib import Path
import json,subprocess,datetime,hashlib,uuid,concurrent.futures,shutil,os
HERE=Path(__file__).resolve().parent
IMAGE='sha256:74c4a6ff67f397f8a10b058851d218896b2f1ee0f2cddf47741219b734de93a6'
CAPTURE=HERE/'candidate/papers/completion/neurosymbolic_supervision/benchmark'
NODES=json.loads((HERE/'original_visible_nodes.json').read_text())['nodes']
WHEEL=HERE/'dependency_wheels/railroad_diagrams-3.0.1-py3-none-any.whl'
DOCKER=['docker','--host','unix:///var/run/docker.sock']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def execute(src):
 name=src['task_id'];root=HERE/'baseline_remaining12_v3'/name;root.mkdir(parents=True,exist_ok=False);work=root/'work';shutil.copytree(src['tree'],work,symlinks=True)
 records=[]
 for stage,extra in [('collect',['--collect-only']),('run',[])]:
  cname='ns-baseline-'+uuid.uuid4().hex;cid=root/(stage+'.cid');out=root/(stage+'.stdout.log');err=root/(stage+'.stderr.log')
  argv=DOCKER+['run','--rm','--name',cname,'--cidfile',str(cid),'--network=none','--read-only','--cap-drop=ALL','--security-opt=no-new-privileges','--user','1000:1000','--cpus','1','--memory','2g','--memory-swap','2g','--pids-limit','128','--tmpfs','/tmp:rw,nosuid,nodev,size=256m','--mount',f'type=bind,src={work},dst=/workspace','--mount',f'type=bind,src={CAPTURE},dst=/capture,readonly','--mount',f'type=bind,src={WHEEL},dst=/railroad.whl,readonly','--mount',f'type=bind,src={root},dst=/result','--env',f'BASELINE_OBSERVATION=/result/{stage}.observation.json','--env','PYTHONPATH=/workspace/src:/workspace:/capture:/railroad.whl','--workdir','/workspace','--env','HOME=/tmp','--env','PYTHONDONTWRITEBYTECODE=1','--env','PYTEST_DISABLE_PLUGIN_AUTOLOAD=1','--entrypoint','python3',IMAGE,'-m','pytest','-q','-p','no:cacheprovider','-p','baseline_capture',*extra,*NODES[name]]
  started=datetime.datetime.now(datetime.timezone.utc).isoformat();timedout=False
  with out.open('wb') as stdout,err.open('wb') as stderr:
   try:p=subprocess.run(argv,stdout=stdout,stderr=stderr,timeout=180);rc=p.returncode
   except subprocess.TimeoutExpired:
    timedout=True;rc=124;subprocess.run(DOCKER+['kill',cname],capture_output=True,timeout=15)
  records.append({'stage':stage,'argv':argv,'started_at':started,'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'returncode':rc,'timed_out':timedout,'stdout':{'path':str(out),'sha256':sha(out)},'stderr':{'path':str(err),'sha256':sha(err)},'container_id':cid.read_text().strip() if cid.exists() else None})
  if stage=='collect' and rc!=0:break
 report={'task_id':name,'source':src,'runs':records,'capture_plugin_sha256':sha(CAPTURE/'baseline_capture.py'),'dependency_wheel_sha256':sha(WHEEL),'no_network':True,'no_credentials_or_scorer_mounts':True}
 p=root/'report.json';p.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'task':name,'runs':[{'stage':r['stage'],'returncode':r['returncode']} for r in records],'report':str(p)}),flush=True);return {'path':str(p),'sha256':sha(p)}
if __name__=='__main__':
 j=json.loads((HERE/'source_recovery_all16.json').read_text())
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:out=list(ex.map(execute,[r for r in j['sources'] if NODES[r['task_id']]]))
 (HERE/'baseline_remaining12_v3.json').write_text(json.dumps({'script_sha256':sha(Path(__file__)),'reports':out},indent=2)+'\n')
