#!/usr/bin/env python3
"""Recover bounded historical candidate pins; never execute upstream code."""
import concurrent.futures
import datetime
import hashlib
import json
from pathlib import Path
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

HERE=Path(__file__).resolve().parent
PRIOR=HERE.parent/'law_study_preparation_20260914'
SKILLS=PRIOR/'skill_candidates_v1'
LOCK=threading.Lock();RETAINED=0
def sha(raw):return hashlib.sha256(raw).hexdigest()
def bind(path):return {'path':str(path),'bytes':path.stat().st_size,'sha256':sha(path.read_bytes())}
def save(path,value):
    with path.open('x') as out:json.dump(value,out,indent=2,sort_keys=True);out.write('\n')
class Redirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        if urllib.parse.urlsplit(newurl).hostname not in ('api.github.com','raw.githubusercontent.com'):
            raise ValueError('Redirect outside public source host allowlist')
        return super().redirect_request(req,fp,code,msg,headers,newurl)
def fetch(url,directory,label,limit=1048576):
    global RETAINED
    started=time.monotonic()
    receipt={'url':url,'requested_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
             'maximum_bytes':limit,'status':None,'error':None}
    save(directory/(label+'.request.json'),receipt)
    try:
        request=urllib.request.Request(url,headers={'User-Agent':'vericodegen-skill-source-pins',
                                                   'Accept':'application/vnd.github+json'})
        with urllib.request.build_opener(Redirect()).open(request,timeout=15) as response:
            receipt.update(status=response.status,resolved_url=response.url,
                           rate_limit_remaining=response.headers.get('X-RateLimit-Remaining'))
            raw=response.read(limit+1)
        if len(raw)>limit:raise ValueError('Prospective response bound exceeded')
        with LOCK:
            if RETAINED+len(raw)>33554432:raise ValueError('Global byte budget exceeded')
            RETAINED+=len(raw)
        with (directory/(label+'.body')).open('xb') as out:out.write(raw)
        receipt.update(bytes=len(raw),sha256=sha(raw),response_file=label+'.body')
        return raw
    except urllib.error.HTTPError as error:
        receipt.update(status=error.code,error=str(error),rate_limit_remaining=error.headers.get('X-RateLimit-Remaining'))
    except Exception as error:
        receipt['error']=type(error).__name__+': '+str(error)
    finally:
        receipt['wall_seconds']=time.monotonic()-started
        save(directory/(label+'.receipt.json'),receipt)
def recover(family):
    directory=HERE/family['task_key'];directory.mkdir()
    row=json.loads((SKILLS/family['row_snapshot']).read_text())
    match=re.search(r'^source_fetched_at: "([^"]+)"$',row['metadata_yaml'],re.M)
    assert match
    cutoff=match.group(1)
    result={'family':family,'source_row':bind(SKILLS/family['row_snapshot']),
            'recorded_original_fetch_at':cutoff,'original_captured_upstream_commit_known':False,
            'candidate_pin_selection':'Latest API-listed commit at/before recorded source fetch on currently named default branch; historical branch identity and exact original source capture remain unproven.',
            'upstream_code_executed':False,'scientific_admission':False,'files':[],'blocking_fetch_failures':[]}
    try:
        repo=family['repository'].removeprefix('github.com/')
        assert re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo)
        raw=fetch('https://api.github.com/repos/'+repo,directory,'repository')
        if raw is None:result['blocking_fetch_failures'].append('repository_metadata_unavailable');return result
        metadata=json.loads(raw)
        result['repository_identity']={k:metadata.get(k) for k in ['id','node_id','full_name','html_url','fork','default_branch','archived','license']}
        result['fork_parent_and_source']={k:{n:metadata[k].get(n) for n in ['id','node_id','full_name','html_url','fork','default_branch']}
                                           for k in ['parent','source'] if isinstance(metadata.get(k),dict)}
        query=urllib.parse.urlencode({'sha':metadata['default_branch'],'until':cutoff,'per_page':1})
        raw=fetch('https://api.github.com/repos/'+metadata['full_name']+'/commits?'+query,directory,'historical-commit-list')
        if raw is None:result['blocking_fetch_failures'].append('historical_commit_listing_unavailable');return result
        commits=json.loads(raw)
        if len(commits)!=1:result['blocking_fetch_failures'].append('no_unique_commit_before_recorded_fetch');return result
        commit=commits[0]
        result['candidate_commit']={'sha':commit['sha'],'tree_sha':commit['commit']['tree']['sha'],
            'author_date':commit['commit']['author']['date'],'committer_date':commit['commit']['committer']['date'],
            'parents':[p['sha'] for p in commit['parents']],'html_url':commit['html_url']}
        assert datetime.datetime.fromisoformat(result['candidate_commit']['committer_date'].replace('Z','+00:00'))<=datetime.datetime.fromisoformat(cutoff.replace('Z','+00:00'))
        raw=fetch('https://api.github.com/repos/'+metadata['full_name']+'/git/trees/'+result['candidate_commit']['tree_sha'],directory,'root-tree')
        if raw is None:result['blocking_fetch_failures'].append('exact_commit_root_tree_unavailable');return result
        tree=json.loads(raw);assert tree['sha']==result['candidate_commit']['tree_sha'] and not tree.get('truncated')
        files={r['path']:r for r in tree['tree'] if r['type']=='blob'}
        readmes=sorted(p for p in files if p.lower().split('.')[0]=='readme')
        licenses=sorted(p for p in files if p.lower().split('.')[0] in ['license','licence','copying','copyright'])
        result['root_readme_paths']=readmes;result['root_license_paths']=licenses
        wanted=[('readme',p) for p in readmes[:1]]+[('license-'+str(i),p) for i,p in enumerate(licenses[:2])]
        for label,path in wanted:
            url='https://raw.githubusercontent.com/'+metadata['full_name']+'/'+commit['sha']+'/'+urllib.parse.quote(path)
            body=fetch(url,directory,label,524288)
            item={'kind':'readme' if label=='readme' else 'license','path':path,'revision':commit['sha'],
                  'git_blob_id':files[path]['sha'],'available':body is not None,'url':url}
            if body is not None:
                blob=hashlib.sha1(b'blob '+str(len(body)).encode()+b'\0'+body).hexdigest()
                assert blob==files[path]['sha']
                item.update(response_binding=bind(directory/(label+'.body')),git_blob_id_verified=True)
            result['files'].append(item)
        return result
    finally:
        save(directory/'recovery.json',result)
def main():
    manifest=json.loads((SKILLS/'source_manifest.json').read_text())
    assert len(manifest['families'])==12
    save(HERE/'recovery_policy.json',{'schema':'skill-upstream-historical-candidate-pin-policy/v1',
        'before_downloads':True,'source_manifest':bind(SKILLS/'source_manifest.json'),
        'selection':'Keep the exact12 existing source candidates. Select latest reachable current-default-branch commit before each row source_fetched_at; no outcome/performance selection.',
        'not_original_capture_proof':True,'no_replacements_on_download_failure':True,
        'maximum_parallel_repositories':3,'maximum_retained_response_bytes':33554432,
        'maximum_single_response_bytes':1048576,'maximum_source_file_bytes':524288,'maximum_request_seconds':15,
        'allowed_hosts':['api.github.com','raw.githubusercontent.com'],
        'files':'Exact-commit root README and up to two root license files, verified against Git tree blob IDs.',
        'execution':'Inert source inspection only; no upstream builds/tests, model, paid service or scientific execution.',
        'native_mutations':0,'frozen_source_mutations':0})
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(recover,manifest['families']))
    save(HERE/'recovery_summary.json',{'schema':'skill-upstream-historical-candidate-pin-recovery/v1',
        'families':results,'retained_response_bytes':RETAINED,'model_calls':0,'upstream_code_executed':False,
        'scientific_admission':False,'native_mutations':0})
    print(json.dumps({'families':len(results),'candidate_commits':sum('candidate_commit' in r for r in results),
                      'retained_response_bytes':RETAINED,'blocking_fetch_failures':[r['family']['task_key'] for r in results if r['blocking_fetch_failures']]}))
if __name__=='__main__':main()
