#!/usr/bin/env python3
"""Fetch five exact public fixes and bounded full source; execute no upstream code."""
import ast
import concurrent.futures
import datetime
import hashlib
import json
from pathlib import Path
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = Path(__file__).resolve().parent
ORIGINAL = HERE.parent / 'law_study_preparation_20260914'
FILES = {130:['glances/compat.py','setup.py','requirements.txt'],
         150:['flask_appbuilder/security/views.py','flask_appbuilder/tests/test_mvc_oauth.py','flask_appbuilder/tests/config_oauth.py'],
         151:['flask_appbuilder/security/api.py','flask_appbuilder/security/manager.py','flask_appbuilder/security/schemas.py'],
         152:['flask_appbuilder/models/sqla/interface.py','flask_appbuilder/models/base.py','flask_appbuilder/tests/security/test_mvc_security.py'],
         153:['flask_appbuilder/security/manager.py','flask_appbuilder/security/views.py','tests/test_mvc_oid.py']}
LOCK = threading.Lock()
RETAINED = 0
def sha(raw): return hashlib.sha256(raw).hexdigest()
def save(path, data):
    with path.open('x') as out: json.dump(data,out,indent=2,sort_keys=True);out.write('\n')
class Redirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urllib.parse.urlsplit(newurl).hostname not in ('api.github.com','raw.githubusercontent.com'):
            raise ValueError('Unapproved redirect host')
        return super().redirect_request(req,fp,code,msg,headers,newurl)
def fetch(url, directory, label, limit=1048576):
    global RETAINED
    start=time.monotonic()
    receipt={'url':url,'requested_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
             'status':None,'error':None,'maximum_bytes':limit}
    save(directory/(label+'.request.json'),receipt)
    try:
        request=urllib.request.Request(url,headers={'User-Agent':'vericodegen-cve-screen-completion',
                                                   'Accept':'application/vnd.github+json'})
        with urllib.request.build_opener(Redirect()).open(request,timeout=15) as response:
            receipt.update(status=response.status,resolved_url=response.url)
            raw=response.read(limit+1)
        if len(raw)>limit:raise ValueError('Response byte bound exceeded')
        with LOCK:
            if RETAINED+len(raw)>33554432:raise ValueError('Total retained byte bound exceeded')
            RETAINED+=len(raw)
        with (directory/(label+'.body')).open('xb') as out:out.write(raw)
        receipt.update(bytes=len(raw),sha256=sha(raw),response_file=label+'.body')
        return raw
    except urllib.error.HTTPError as error:
        receipt.update(status=error.code,error=str(error))
    except Exception as error:
        receipt['error']=type(error).__name__+': '+str(error)
    finally:
        receipt['wall_seconds']=time.monotonic()-start
        save(directory/(label+'.receipt.json'),receipt)
def recover(row):
    number=row['physical_row'];directory=HERE/f'row-{number:04d}';directory.mkdir()
    repo=row['repository'].removeprefix('github.com/');fix=row['fix_commit']
    result={'original_screen_row':row,'files':[],'code_executed':False,'models_called':0}
    save(directory/'original_screen_row.json',row)
    raw=fetch(f'https://api.github.com/repos/{repo}/commits/{fix}',directory,'commit')
    if raw is None:
        result['blocker']='Exact public commit metadata unavailable';save(directory/'recovery.json',result);return result
    commit=json.loads(raw);parents=[p['sha'] for p in commit['parents']]
    assert commit['sha']==fix and len(parents)==1
    result.update(parent=parents[0],fixed=fix,tree=commit['commit']['tree']['sha'])
    for version,revision in [('parent',parents[0]),('fixed',fix)]:
        for index,path in enumerate(FILES[number]):
            label=f'{version}-{index}'
            body=fetch(f'https://raw.githubusercontent.com/{repo}/{revision}/{path}',directory,label,524288)
            info={'version':version,'revision':revision,'path':path,'available':body is not None,'response_file':label+'.body'}
            if body is not None:
                info.update(sha256=sha(body),bytes=len(body))
                if path.endswith('.py'):
                    try:ast.parse(body);info['python3_ast_parse']='PASS'
                    except Exception as error:info['python3_ast_parse']='FAIL';info['diagnostic']=str(error)
            result['files'].append(info)
    fetch(f'https://api.github.com/advisories?cve_id={row["cve_id"]}',directory,'advisory')
    fetch(f'https://api.github.com/repos/{repo}',directory,'repository')
    tree=fetch(f'https://api.github.com/repos/{repo}/git/trees/{result["tree"]}',directory,'root-tree')
    if tree:
        paths=sorted(x['path'] for x in json.loads(tree).get('tree',[])
                     if x['type']=='blob' and x['path'].lower().split('.')[0] in ('license','licence','copying','copyright'))
        if paths:
            body=fetch(f'https://raw.githubusercontent.com/{repo}/{fix}/{paths[0]}',directory,'license')
            result['license']={'path':paths[0],'available':body is not None,'sha256':sha(body) if body else None}
    save(directory/'recovery.json',result)
    return result
def main():
    rows=[r for r in json.loads((ORIGINAL/'cve_screening_audit.json').read_text())['rows'] if r['physical_row'] in FILES]
    assert len(rows)==5
    save(HERE/'recovery_policy.json',{'scope':'Complete only the five previously unclassified rows using unchanged prospective source criteria.',
        'upstream_policy_sha256':sha((ORIGINAL/'source_recovery_policy.json').read_bytes()),
        'eligibility_rule_sha256':sha((ORIGINAL/'prospective_eligibility_rule.json').read_bytes()),
        'source_screen_sha256':sha((ORIGINAL/'cve_screening_audit.json').read_bytes()),
        'rows':sorted(FILES),'max_concurrent_rows':3,'max_source_files_per_revision':3,
        'max_source_file_bytes':524288,'max_metadata_bytes':1048576,'max_total_response_bytes':33554432,
        'max_request_timeout_seconds':15,'no_silent_retries':True,'allowed_hosts':['api.github.com','raw.githubusercontent.com'],
        'source_or_model_code_executed':False,'model_calls':0,'scientific_cells':0})
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(recover,rows))
    report={'rows':results,'retained_response_bytes':RETAINED,'upstream_code_executed':False,'model_calls':0,
            'scientific_cells_executed':0,'frozen_source_files_mutated':0}
    save(HERE/'recovery_summary.json',report)
    print(json.dumps({'rows':len(results),'retained_response_bytes':RETAINED,
                      'available_full_files':sum(f['available'] for r in results for f in r['files'])}))
if __name__=='__main__':main()
