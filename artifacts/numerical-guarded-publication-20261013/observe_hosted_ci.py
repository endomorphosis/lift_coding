"""Observe documentation CI for one exact published accelerator commit."""
from datetime import datetime,timezone
import hashlib,json,subprocess,sys
from pathlib import Path
head='d13c68ce80dba65478c87f24ada0669ddfb36a1b'
repo='endomorphosis/ipfs_accelerate_py'
requests=[]
def api(path):
    argv=['gh','api',path]
    run=subprocess.run(argv,capture_output=True)
    requests.append(dict(argv=argv,exit_code=run.returncode,response_sha256=hashlib.sha256(run.stdout).hexdigest(),response_bytes=len(run.stdout),stderr=run.stderr.decode()))
    run.check_returncode()
    return json.loads(run.stdout)
runs=api(f'repos/{repo}/actions/workflows/documentation-gates.yml/runs?head_sha={head}&per_page=10')['workflow_runs']
rows=[]
for run in runs:
    assert run['head_sha']==head
    row={k:run[k] for k in ('id','head_sha','html_url','status','conclusion','created_at','updated_at')}
    jobs=api(f'repos/{repo}/actions/runs/{run["id"]}/jobs')['jobs']
    row['jobs']=[]
    for job in jobs:
        assert job['head_sha']==head
        entry={k:job[k] for k in ('id','head_sha','html_url','status','conclusion','runner_id','runner_name','steps')}
        path=job['check_run_url'].removeprefix('https://api.github.com/')
        assert path.startswith(f'repos/{repo}/check-runs/')
        entry['annotations']=api(path+'/annotations')
        row['jobs'].append(entry)
    rows.append(row)
locked=any('account is locked due to a billing issue' in a.get('message','') for row in rows for j in row['jobs'] for a in j['annotations'])
record=dict(schema='numerical-guarded-hosted-ci@1',observed_utc=datetime.now(timezone.utc).isoformat(),exact_head_sha=head,repository=repo,api_requests=requests,runs=rows,billing_lock_observed=locked,hosted_documentation_gates_passed=bool(rows) and all(r['conclusion']=='success' for r in rows))
out=Path(sys.argv[1]);out.parent.mkdir(parents=True,exist_ok=True)
with out.open('x') as file:json.dump(record,file,indent=2);file.write('\n')
print(json.dumps(dict(runs=len(rows),complete=bool(rows) and all(r['status']=='completed' for r in rows),billing_lock_observed=locked)))
