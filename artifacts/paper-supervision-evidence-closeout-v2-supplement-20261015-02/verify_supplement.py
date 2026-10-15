"""Verify the new supplement and frozen parent; no runtime or solver imports.

Ordinary integrity verification rehashes small evidence and exact Git blobs.
Large archive/checkpoint verification receipts are checked; the assets are only
checked for existence/size here. Use the bounded large-asset scripts to rehash.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

BASE=Path(__file__).resolve().parent
ROOT=Path('/home/barberb/lift_coding')
PRIOR=BASE.parent/'paper-supervision-evidence-closeout-v2-audit-20261015-01'

def load(p):return json.loads(p.read_text())
def rows(p):return [json.loads(s) for s in p.read_text().splitlines() if s]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True,type=Path)
    output=parser.parse_args().output
    checks=[]
    def check(name,passed,detail=None):checks.append({'check':name,'passed':bool(passed),'detail':detail})
    auth=load(BASE/'authorization.json')
    old_manifest=PRIOR/'audit/output_manifest.json'
    check('prior frozen manifest unchanged',sha(old_manifest)==auth['prior_output_manifest_sha256'])
    for x in load(old_manifest)['files']:
        p=PRIOR/x['path']
        check('prior audit unchanged:'+x['path'],p.is_file() and p.resolve()==p and sha(p)==x['sha256'])
    metadata=rows(BASE/'consolidated/artifacts.jsonl')
    for x in metadata:
        p=Path(x['path']);valid=p.is_relative_to(ROOT) and p.resolve()==p and p.is_file()
        valid=valid and p.stat().st_size==x['bytes'] and x['bytes']<=auth['limits']['per_json_text_file_bytes']
        check('small evidence unchanged:'+str(p),valid and sha(p)==x['sha256'])
    git_sources=load(BASE/'consolidated/git_artifacts.json')['sources']
    for x in git_sources:
        spec=x['commit']+':'+x['path']
        if x['repository']!=str(ROOT):raise ValueError('Unapproved Git repository')
        if not x['path'].startswith('papers/completion/neurosymbolic_supervision/'):raise ValueError('Unapproved historical path')
        size=int(subprocess.run(['git','-C',str(ROOT),'cat-file','-s',spec],check=True,capture_output=True,text=True).stdout)
        if size>2*1024*1024:raise ValueError('Git blob size bound')
        raw=subprocess.run(['git','-C',str(ROOT),'show',spec],check=True,capture_output=True).stdout
        check('historical Git blob unchanged:'+spec,len(raw)==x['bytes'] and hashlib.sha256(raw).hexdigest()==x['sha256'])
    log_counts={}
    for worker,limit in auth['allocations'].items():
        log=BASE/'workstreams'/f'{worker}_inputs.jsonl';items=rows(log) if log.exists() else []
        count=len(items);size=sum(x['bytes'] for x in items)
        if worker=='integration':count+=len(git_sources);size+=sum(x['bytes'] for x in git_sources)
        check('worker read allocation:'+worker,count<=limit['files'] and size<=limit['bytes'],{'files':count,'bytes':size})
        log_counts[worker]={'files':count,'bytes':size}
    assets=load(BASE/'audit/large_asset_verification.json')
    members=load(BASE/'audit/runtime_member_verification.json')
    for a in assets['results']:
        p=Path(a['path'])
        check('large asset retained size:'+a['asset'],p.resolve()==p and p.is_file() and p.stat().st_size==a['bytes'])
        check('recorded fresh large asset hash matched:'+a['asset'],a['matches_reported_identity'] and a['stable_during_read'])
    check('combined compressed/asset stream bound',assets['stream_bytes']+members['compressed_bytes_read']<=auth['limits']['total_stream_bytes'],assets['stream_bytes']+members['compressed_bytes_read'])
    check('archive regular-byte bound',members['regular_member_bytes']<=auth['limits']['archive_regular_member_bytes'])
    check('archive verified without extraction',members['all_declared_file_bytes_verified'] and members['archive_has_only_declared_regular_files'] and members['no_extraction_or_execution'] and not members['links_followed'])
    forest=load(BASE/'runtime_source_forest.json')
    check('actual imports not inferred',forest['actual_live_loaded_module_origins'] is None and forest['executed_git_forest'] is None)
    smallchecks=load(BASE/'consolidated/checks.json')
    check('assembly consistency',smallchecks['passed'] and all(x['passed'] for x in smallchecks['checks']),len(smallchecks['checks']))
    review=BASE/'audit/final_consolidation_review.md'
    check('independent projection review retained',review.is_file())
    runs=rows(BASE/'consolidated/runs.jsonl');prior=rows(PRIOR/'runs.jsonl')
    check('no new benchmark rows',len(runs)==len(prior))
    check('all outcomes and reported counters retained',all((a['original_reward'],a['reported_tokens'],a['native_usage_complete'])==(b['original_reward'],b['reported_tokens'],b['native_usage_complete']) for a,b in zip(runs,prior)))
    sessions=rows(BASE/'consolidated/sessions.jsonl')
    check('unique usage ledger identities',len({x['ledger_id'] for x in sessions})==len(sessions))
    for c in rows(BASE/'workstreams/historical_provider_calls.jsonl'):
        found=[x for x in sessions if x.get('invocation_id')==c['call_id']]
        check('provider request merged once:'+c['call_id'],len(found)==1 and found[0]['session_id'] is None and found[0]['recovered_per_request_usage']==c['reported_usage'])
    traces=rows(BASE/'consolidated/cross_ir_trace.jsonl');old_traces=rows(PRIOR/'cross_ir_trace.jsonl')
    check('no semantic stage promotion by byte verification',[x['status'] for x in traces]==[x['status'] for x in old_traces])
    uninvoked={x['ledger_id'] for x in runs if x['invoked'] is False}
    check('uninvoked rows remain uninvoked',all(x['status']!='actually invoked' for x in traces if x['ledger_id'] in uninvoked))
    manifest=load(BASE/'audit/output_manifest.json')
    for x in manifest['files']:
        p=BASE/x['path']
        check('supplement output hash:'+x['path'],p.resolve()==p and p.is_file() and sha(p)==x['sha256'])
    result={'schema':'paper-supplement-integrity@1','passed':all(x['passed'] for x in checks),'checks':checks,
            'read_allocation_summary':log_counts,'large_originals_rehashed_in_this_integrity_call':False,
            'large_original_check_scope':'Current existence/size only; earlier fresh complete hash/member verification receipts included in output manifest',
            'new_runtime_or_solver_execution':False,'signatures_verified':False,
            'output_manifest_sha256':sha(BASE/'audit/output_manifest.json')}
    with output.open('x') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
    output.chmod(0o600)
    print(json.dumps({'passed':result['passed'],'checks':len(checks),'failures':[x for x in checks if not x['passed']],'output':str(output)}))
    if not result['passed']:raise SystemExit(1)

if __name__=='__main__':
    os.umask(0o077);main()
