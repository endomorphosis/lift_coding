"""Read actual checks/annotations for this contribution only."""
import argparse,json,subprocess
from pathlib import Path
from datetime import datetime,timezone
p=argparse.ArgumentParser();p.add_argument('--repo',required=True);p.add_argument('--head',required=True);p.add_argument('--output',required=True);a=p.parse_args()
def get(path):
 return json.loads(subprocess.check_output(['gh','api',path],text=True))
checks=get(f'repos/{a.repo}/commits/{a.head}/check-runs?per_page=100')['check_runs']
records=[]
for check in checks:
 assert check['head_sha']==a.head
 annotations=get(f'repos/{a.repo}/check-runs/{check["id"]}/annotations?per_page=100')
 records.append({k:check[k] for k in ('id','name','head_sha','status','conclusion','html_url')}|dict(annotations=annotations))
failures=[x['message'] for r in records for x in r['annotations'] if x['annotation_level']=='failure']
billing=bool(failures) and all('account is locked due to a billing issue' in x for x in failures)
value=dict(schema='support-retention-own-hosted-ci/v1',observed_at_utc=datetime.now(timezone.utc).isoformat(),repo=a.repo,head=a.head,availability='unavailable_account_billing_lock' if billing else 'observed_checks',claim_passed=bool(records) and all(r['conclusion']=='success' for r in records),checks=records)
Path(a.output).write_text(json.dumps(value,indent=2)+'\n')
print(json.dumps(dict(checks=len(records),availability=value['availability'],claim_passed=value['claim_passed'])))
