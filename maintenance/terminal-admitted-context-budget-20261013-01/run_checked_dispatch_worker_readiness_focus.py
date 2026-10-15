import os,sys,json,hashlib,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
W=Path(__file__).resolve().parent;C=W/'checkout';E=Path('/home/barberb/lift_coding/maintenance/terminal-compact-retrieval-20261011-01/pinned-dependencies-v10');out=W/sys.argv[1];out.mkdir(mode=0o700)
rels=['ipfs_accelerate_py/agent_supervisor/runtime/checked_context_dispatch.py','ipfs_accelerate_py/agent_supervisor/runtime/checked_observer_budget.py','ipfs_accelerate_py/agent_supervisor/entrypoints/admitted_benchmark_runtime.py','ipfs_accelerate_py/agent_supervisor/todo_daemon/implementation_daemon.py','ipfs_accelerate_py/agent_supervisor/todo_daemon/supervisor_runtime.py','benchmarks/agent_supervisor/container_coding/container_worker_deployment.py','test/api/test_checked_context_dispatch.py','test/api/test_checked_observer_budget.py','test/api/test_checked_context_native_integration.py']
def pin(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
before=[pin(C/r)for r in rels];env=dict(os.environ,PYTHONPATH=':'.join(['/home/barberb/lift_coding/maintenance/terminal-proof-cache-revision-20261012-01/pinned-host-duckdb','/home/barberb/lift_coding/maintenance/terminal-token-pairing-20261012-01/pinned-host-tokenizer',str(C),str(E/'datasets'),str(E/'kit'),'/home/barberb/lift_coding/.venvs/terminal-bench-harbor/lib/python3.12/site-packages']),PYTHONDONTWRITEBYTECODE='1',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',TIKTOKEN_CACHE_DIR='/tmp/data-gym-cache',IPFS_ACCELERATE_META_INDEX_DUCKDB=str(out/'metadata.duckdb'),IPFS_ACCELERATE_PYTEST_SEAL_DUCKDB=str(out/'seal.duckdb'),IPFS_ACCELERATE_AGENT_ORCHESTRATION_DIR=str(out/'orchestration'));env.pop('IPFS_ACCELERATE_META_INDEX_DUCKLAKE',None)
args=['/home/barberb/lift_coding/.venv/bin/python','-B','-m','pytest','-vv','-o','faulthandler_timeout=30','-o','addopts=','-p','no:cacheprovider','--basetemp='+str(out/'tmp'),'--junitxml='+str(out/'results.xml'),'test/api/test_checked_context_dispatch.py']
log=out/'pytest.log'
with log.open('xb')as handle:
    process=subprocess.Popen(args,cwd=C,env=env,stdout=handle,stderr=subprocess.STDOUT)
    timed_out=False
    try:exit_code=process.wait(timeout=300)
    except subprocess.TimeoutExpired:
        timed_out=True;process.kill();exit_code=process.wait(timeout=10)
cases=list(ET.parse(out/'results.xml').getroot().iter('testcase'))if(out/'results.xml').exists()else[]
counts=dict(tests=len(cases),unique_tests=len({(x.get('classname'),x.get('name'))for x in cases}),failures=sum(len(x.findall('failure'))for x in cases),errors=sum(len(x.findall('error'))for x in cases),skips=sum(len(x.findall('skipped'))for x in cases))
after=[pin(C/r)for r in rels]
report=dict(schema='checked-dispatch-native-worker-metadata-readiness-regression@1',actual_native_origin_qualified=False,exit_code=exit_code,timed_out=timed_out,counts=counts,source_pins_before=before,source_pins_after=after,source_bytes_unchanged=before==after,argv=args,log_pin=pin(log),qualified_test_run=not timed_out and exit_code==0 and len(cases)==229 and all(counts[k]==0 for k in('failures','errors','skips'))and before==after)
p=W/(sys.argv[1]+'-report.json');p.write_text(json.dumps(report,sort_keys=True,indent=2)+'\n');print(json.dumps(dict(report_pin=pin(p),counts=counts,source_bytes_unchanged=before==after,qualified=report['qualified_test_run'],timed_out=timed_out)));sys.exit(0 if report['qualified_test_run']else 1)
