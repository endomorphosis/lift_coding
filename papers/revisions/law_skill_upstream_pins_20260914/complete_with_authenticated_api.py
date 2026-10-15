#!/usr/bin/env python3
"""Complete only failed public-source reads using existing gh authentication."""
import concurrent.futures
import datetime
import json
from pathlib import Path
import subprocess
import sys
import time
import urllib.parse

sys.dont_write_bytecode=True
import recover_upstream_pins as R

ORIGINAL=Path(__file__).resolve().parent
TARGET=ORIGINAL/'authenticated_completion_v1'
public_fetch=R.fetch

def authenticated_fetch(url,directory,label,limit=1048576):
    if urllib.parse.urlsplit(url).hostname=='raw.githubusercontent.com':
        return public_fetch(url,directory,label,limit)
    parsed=urllib.parse.urlsplit(url)
    assert parsed.scheme=='https' and parsed.hostname=='api.github.com'
    endpoint=parsed.path.lstrip('/')+('?' + parsed.query if parsed.query else '')
    assert endpoint.startswith('repos/')
    started=time.monotonic()
    receipt={'url':url,'requested_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
             'transport':'existing_authenticated_gh_api_public_repository_read',
             'maximum_bytes':limit,'credentials_retained':False,'returncode':None,'error':None}
    R.save(directory/(label+'.request.json'),receipt)
    try:
        completed=subprocess.run(['/usr/bin/gh','api',endpoint],capture_output=True,timeout=15)
        receipt['returncode']=completed.returncode
        if completed.returncode:
            receipt['error']='gh_public_api_read_failed';receipt['stderr']=completed.stderr[:4096].decode(errors='replace')
            return None
        raw=completed.stdout
        if len(raw)>limit:raise ValueError('Prospective API response bound exceeded')
        with R.LOCK:
            if R.RETAINED+len(raw)>33554432:raise ValueError('Total retained byte bound exceeded')
            R.RETAINED+=len(raw)
        with (directory/(label+'.body')).open('xb') as out:out.write(raw)
        receipt.update(bytes=len(raw),sha256=R.sha(raw),response_file=label+'.body')
        return raw
    except Exception as error:
        receipt['error']=type(error).__name__+': '+str(error)
    finally:
        receipt['wall_seconds']=time.monotonic()-started
        R.save(directory/(label+'.receipt.json'),receipt)

def main():
    initial=json.loads((ORIGINAL/'recovery_summary.json').read_text())
    pending=[r['family'] for r in initial['families'] if r['blocking_fetch_failures']]
    assert len(pending)==9
    TARGET.mkdir(exist_ok=False)
    R.save(TARGET/'completion_policy.json',{
        'schema':'skill-pin-public-api-authenticated-completion/v1',
        'initial_recovery':R.bind(ORIGINAL/'recovery_summary.json'),
        'initial_policy':R.bind(ORIGINAL/'recovery_policy.json'),
        'reason':'Initial anonymous API quota exhausted; failed receipts preserved. Use the existing authorized gh public API read capability.',
        'pending_task_keys':[f['task_key'] for f in pending],
        'successful_original_pins_requeried':False,'failed_original_receipts_overwritten':False,
        'credentials_copied_or_recorded':False,'upstream_code_or_models_executed':False,
        'same_cutoff_and_source_selection_policy':True,'max_parallel_repositories':3})
    R.HERE=TARGET
    R.fetch=authenticated_fetch
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(R.recover,pending))
    R.save(TARGET/'recovery_summary.json',{'schema':'skill-upstream-historical-candidate-pin-authenticated-completion/v1',
        'families':results,'retained_response_bytes':R.RETAINED,'model_calls':0,
        'upstream_code_executed':False,'scientific_admission':False,'native_mutations':0})
    print(json.dumps({'families':len(results),'candidate_commits':sum('candidate_commit' in r for r in results),
                     'retained_response_bytes':R.RETAINED,
                     'blocking_fetch_failures':[r['family']['task_key'] for r in results if r['blocking_fetch_failures']]}))

if __name__=='__main__':main()
