#!/usr/bin/env python3
"""Bounded public source retrieval; never imports or executes recovered code."""
import argparse,ast,concurrent.futures,hashlib,json,threading,time,urllib.request,urllib.error,urllib.parse
from pathlib import Path
import pyarrow.parquet as pq

ROWS={64:'salt/states/user.py',72:'engine/engine.py',88:'core/db.py',90:'src/pikepdf/_xml.py',91:'plugins/src/allow_execmod.py',124:'astropy/coordinates/transformations.py',143:'bot/cogs/product.py',171:'llama_cpp/llama_chat_format.py',194:'pandora/workers/extractor.py',201:'openapi_python_client/utils.py',242:'src/octoprint/server/views.py',261:'xhu.py'}
ROOT=Path(__file__).resolve().parent
LOCK=threading.Lock();RETAINED=0
def sha(data):return hashlib.sha256(data).hexdigest()
def save(path,value):
 with path.open('x') as f:json.dump(value,f,indent=2,sort_keys=True);f.write('\n')
class Redirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):
  if urllib.parse.urlsplit(newurl).hostname not in ('api.github.com','raw.githubusercontent.com'):raise ValueError('Unapproved redirect host')
  return super().redirect_request(req,fp,code,msg,headers,newurl)
def fetch(url,out,label,limit=1048576):
 global RETAINED
 start=time.monotonic();receipt={'url':url,'started_monotonic':start,'status':None,'body_sha256':None,'error':None};save(out/(label+'.request.json'),receipt)
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'vericodegen-source-preparation','Accept':'application/vnd.github+json'})
  with urllib.request.build_opener(Redirect()).open(req,timeout=15) as r:data=r.read(limit+1);receipt['status']=r.status;receipt['resolved_url']=r.url
  if len(data)>limit:raise ValueError('Response exceeds prospective byte bound')
  with LOCK:
   if RETAINED+len(data)>33554432:raise ValueError('Global source byte budget exhausted')
   RETAINED+=len(data)
  (out/(label+'.body')).write_bytes(data);receipt.update(body_sha256=sha(data),bytes=len(data));return data
 except urllib.error.HTTPError as exc:receipt.update(status=exc.code,error=str(exc));return None
 except Exception as exc:receipt['error']=type(exc).__name__+': '+str(exc);return None
 finally:receipt['wall_seconds']=time.monotonic()-start;save(out/(label+'.receipt.json'),receipt)
def recover(row_index,row,out):
 folder=out/f'row-{row_index:04d}';folder.mkdir();repository=urllib.parse.urlsplit(row['repo_url']).path.strip('/').removesuffix('.git');fix=row['hash'];primary=ROWS[row_index]
 info={'row_index':row_index,'cve_id':row['cve_id'],'repository':repository,'dataset_fix_commit':fix,'primary_file':primary,'files':[],'source_modules_executed':False,'original_system_reproduction_qualified':False}
 try:
  raw=fetch(f'https://api.github.com/repos/{repository}/commits/{fix}',folder,'commit')
  if raw is None:info['blocker']='Exact upstream commit metadata unavailable';return info
  commit=json.loads(raw);parents=[p['sha'] for p in commit['parents']];info.update(resolved_fix_commit=commit['sha'],parent_commits=parents,tree_sha=commit['commit']['tree']['sha'],commit_metadata_sha256=sha(raw))
  if commit['sha']!=fix or len(parents)!=1:info['blocker']='Commit mismatch or ambiguous parent';return info
  wanted=[primary]+[p for p in row['file_paths'] if (p.startswith('test') or '/test' in p) and p.endswith('.py') and p!=primary][:2]
  for revision,version in [(fix,'fixed'),(parents[0],'parent')]:
   for i,path in enumerate(wanted):
    raw=fetch(f'https://raw.githubusercontent.com/{repository}/{revision}/{path}',folder,f'{version}-{i}',524288)
    item={'revision':revision,'version':version,'path':path,'available':raw is not None,'response_file':f'{version}-{i}.body' if raw is not None else None}
    if raw is not None:
     item.update(sha256=sha(raw),bytes=len(raw))
     try:ast.parse(raw,filename=path);item['python3_ast_parse']='PASS'
     except (SyntaxError,UnicodeDecodeError) as exc:item['python3_ast_parse']='FAIL';item['syntax_diagnostic']=str(exc)
    info['files'].append(item)
  # A newly added security wrapper may have no parent file; the caller's
  # parent implementation remains necessary evidence, never fabricated.
  if row_index==90:
   caller='src/pikepdf/models/metadata.py'
   raw=fetch(f'https://raw.githubusercontent.com/{repository}/{parents[0]}/{caller}',folder,'parent-caller',524288)
   info['files'].append({'revision':parents[0],'version':'parent','path':caller,'available':raw is not None,'response_file':'parent-caller.body' if raw else None,'sha256':sha(raw) if raw else None})
  tree_raw=fetch(f'https://api.github.com/repos/{repository}/git/trees/{info["tree_sha"]}',folder,'root-tree')
  if tree_raw:
   tree=json.loads(tree_raw);licenses=[x['path'] for x in tree.get('tree',[]) if x['type']=='blob' and x['path'].lower().split('.')[0] in ('license','licence','copying','copyright')]
   info['root_license_candidates']=licenses
   if licenses:
    name=sorted(licenses)[0];raw=fetch(f'https://raw.githubusercontent.com/{repository}/{fix}/{name}',folder,'license')
    info['license']={'path':name,'revision':fix,'available':raw is not None,'sha256':sha(raw) if raw else None,'response_file':'license.body' if raw else None}
   else:info['license']={'available':False,'reason':'No recognized root license file; manual source-license review required'}
  return info
 finally:save(folder/'recovery.json',info)
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);a=p.parse_args();out=a.output.resolve();out.mkdir();rows={};index=0
 parquet=ROOT.parent.parent/'completion/runtime_bootstrap/la004_source_bridge/train-00000-of-00003.parquet'
 for batch in pq.ParquetFile(parquet).iter_batches(columns=['cve_id','hash','repo_url','file_paths'],batch_size=128):
  for row in batch.to_pylist():
   if index in ROWS:rows[index]=row
   index+=1
  if index>max(ROWS):break
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(lambda item:recover(item[0],item[1],out),rows.items()))
 report={'schema':'la-candidate-cve-public-source-recovery/v1','policy_sha256':sha((ROOT/'source_recovery_policy.json').read_bytes()),'repositories':results,'retained_response_bytes':RETAINED,'models_called':0,'upstream_tests_executed':0,'final_cohort_released':False,'original_systems_qualified':0};save(out/'recovery_summary.json',report)
 print(json.dumps({'repositories':len(results),'available_full_files':sum(f['available'] for r in results for f in r['files']),'retained_bytes':RETAINED,'models_called':0}))
if __name__=='__main__':main()
