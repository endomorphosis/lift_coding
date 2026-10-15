"""Fresh bounded test attempt with explicit before/after source pins."""
import hashlib,json,os,subprocess,sys,time,xml.etree.ElementTree as ET
from pathlib import Path
AA=Path(__file__).resolve().parent;C=AA/'checkout';os.umask(0o077)
name=sys.argv[1];out=AA/name;out.mkdir(mode=0o700)
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',IPFS_ACCELERATE_META_INDEX_DUCKDB=str(out/'meta.duckdb'),
 IPFS_ACCELERATE_PYTEST_SEAL_DUCKDB=str(out/'seal.duckdb'),IPFS_ACCELERATE_AGENT_ORCHESTRATION_DIR=str(out/'orchestration'))
env.pop('IPFS_ACCELERATE_META_INDEX_DUCKLAKE',None)
rows=subprocess.check_output(['git','status','--porcelain=v1','--untracked-files=all'],cwd=C,text=True).splitlines()
paths=sorted({line[3:] for line in rows if line[3:].endswith('.py') and line[3:].startswith(('ipfs_accelerate_py/','benchmarks/','test/api/'))})
def pins():
 result=[]
 for relative in paths:
  p=C/relative;b=p.read_bytes();result.append({'path':str(p),'relative_path':relative,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
 return result
before=pins();start=time.monotonic();xml=out/'results.xml'
cmd=[sys.executable,'-B','-m','pytest','-q','-p','no:cacheprovider','--basetemp='+str(out/'tmp'),'--junitxml='+str(xml),*sys.argv[2:]]
with (out/'pytest.log').open('xb') as f:r=subprocess.run(cmd,cwd=C,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=1200,preexec_fn=lambda:os.umask(0o022))
after=pins();root=ET.fromstring(xml.read_bytes());cases=list(root.iter('testcase'));ids=[(c.get('classname'),c.get('name'))for c in cases]
counts={'tests':len(cases),'unique_tests':len(set(ids)),'failures':len(list(root.iter('failure'))),'errors':len(list(root.iter('error'))),'skips':len(list(root.iter('skipped')))}
ok=r.returncode==0 and before==after and counts['tests']==counts['unique_tests'] and not any(counts[k] for k in ('failures','errors','skips'))
report={'schema':'terminal-admitted-context-budget-test-attempt@1','qualified':ok,'exit_code':r.returncode,'seconds':time.monotonic()-start,'command':cmd,'counts':counts,'source_pins_before':before,'source_pins_after':after,'source_bytes_unchanged':before==after,'provider_calls':0,'actual_native_birth_qualified':False}
with (AA/(name+'-report.json')).open('x')as f:json.dump(report,f,sort_keys=True,indent=2);f.write('\n')
print(json.dumps({'qualified':ok,**counts,'source_bytes_unchanged':before==after}));raise SystemExit(0 if ok else 1)
