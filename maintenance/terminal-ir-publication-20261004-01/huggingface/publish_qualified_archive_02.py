"""Publish one reviewed evidence derivative without replacing bootstrap files.

Every batch uses the exact fresh parent commit. Failed network calls may have
external effects: receipts retain partial commits and require remote readback.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

REPO='Publicus/codebase-ir-proof-index'
PREFIX='releases/20261004-terminal-codebase-ir-evidence-v1/archive-payload-v1'
SCHEMA='terminal-ir-reviewed-archive-HF-publication@1'


def wire(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def save(p,v):
 with p.open('xb') as f:f.write(wire(v)+b'\n');f.flush();os.fsync(f.fileno())
def pin(p):
 fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW);digest=hashlib.sha256();count=0
 try:
  before=os.fstat(fd)
  while block:=os.read(fd,8*1024**2):digest.update(block);count+=len(block)
  after=os.fstat(fd)
  if (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns):raise ValueError('publication input changed during read')
 finally:os.close(fd)
 return {'path':str(p),'bytes':count,'sha256':digest.hexdigest()}
def identity(row):
 return {'path':row.path,'bytes':row.size,'blob_id':row.blob_id,'lfs_sha256':row.lfs.sha256 if row.lfs else None}


def publish(args,output,state,deadline):
 # Import only the installed publication client; no model/owned-producer import.
 from huggingface_hub import HfApi,CommitOperationAdd,hf_hub_download
 from huggingface_hub.utils import get_token
 manifestpin=pin(args.manifest);reviewpin=pin(args.review)
 if manifestpin['sha256']!=args.expected_manifest_sha256 or reviewpin['sha256']!=args.expected_review_sha256:raise ValueError('external publication input pin mismatch')
 manifest=json.loads(args.manifest.read_bytes());review=json.loads(args.review.read_bytes())
 if manifest['status']!='closed_public_derivative_requires_root_classification_review' or manifest['upload_qualified'] is not True:raise ValueError('closed qualified derivative required')
 if review.get('schema')!='terminal-ir-public-archive-root-review@1' or review.get('status')!='APPROVED_PUBLIC_DERIVATIVE' or review.get('archive_manifest_sha256')!=manifestpin['sha256'] or review.get('repo_id')!=REPO or review.get('release_prefix')!=PREFIX:raise ValueError('exact root-reviewed publication required')
 if review.get('credential_classification_complete') is not True or review.get('quarantine_originals_retained_local') is not True:raise ValueError('credential/exclusion review incomplete')
 token=get_token()
 if not token:raise ValueError('cached publication credential unavailable')
 api=HfApi(token=token);who=api.whoami()
 if who.get('name')!='endomorphosis' or not any(o.get('name')=='Publicus' and o.get('roleInOrg')=='admin' for o in who.get('orgs',[])):raise ValueError('unexpected publication identity')
 info=api.repo_info(REPO,repo_type='dataset',revision='main')
 if info.sha!=args.expected_parent_commit:raise ValueError('fresh expected dataset parent changed')
 before={r.path:identity(r) for r in api.list_repo_tree(REPO,repo_type='dataset',revision=info.sha,recursive=True) if hasattr(r,'blob_id')}
 if any(name==PREFIX or name.startswith(PREFIX+'/') for name in before):raise ValueError('immutable payload prefix already occupied')
 save(output/'remote-before.json',{'repo':REPO,'parent':info.sha,'files':before})
 files=[];names=set()
 for row in manifest['data_shards']:
  path=Path(row['source_path']);binding={k:row[k] for k in ['bytes','sha256']};binding['path']=str(path)
  files.append({'local':binding,'remote':PREFIX+'/'+row['archive']})
 for key in ['path_manifest_shards','chunk_index_shards']:
  for row in manifest[key]:files.append({'local':{k:row[k] for k in ['path','bytes','sha256']},'remote':PREFIX+'/'+Path(row['path']).name})
 # The classifier manifest is qualified by the separate exact root review.
 files.append({'local':manifestpin,'remote':PREFIX+'/archive-manifest.json'})
 files.append({'local':reviewpin,'remote':PREFIX+'/root-classification-review.json'})
 for item in files:
  if item['remote'] in names or '..' in Path(item['remote']).parts:raise ValueError('duplicate/unsafe publication path')
  names.add(item['remote'])
  if pin(Path(item['local']['path']))!=item['local']:raise ValueError('publication file pin mismatch')
  if item['local']['bytes']>256*1024**2:raise ValueError('publication file exceeds archive cap')
 save(output/'publication-file-plan.json',{'repo':REPO,'prefix':PREFIX,'files':files,'selected_bytes':sum(i['local']['bytes'] for i in files),'file_count':len(files)})
 state.update({'manifest':manifestpin,'root_review':reviewpin,'starting_parent':info.sha,'uploaded_files':0,'commits':[],'known_external_effects_possible_on_failure':True})
 parent=info.sha;verified={};batches=[files[i:i+20] for i in range(0,len(files),20)]
 for number,batch in enumerate(batches):
  if time.monotonic()>deadline:raise TimeoutError('publication wall budget')
  if api.repo_info(REPO,repo_type='dataset',revision='main').sha!=parent:raise ValueError('dataset parent changed before batch')
  save(output/('batch-%04d-started.json'%number),{'expected_parent':parent,'files':batch,'started_wall_time':time.time()})
  for item in batch:
   if pin(Path(item['local']['path']))!=item['local']:raise ValueError('prebatch publication file pin mismatch')
  start=time.monotonic()
  commit=api.create_commit(REPO,repo_type='dataset',revision='main',parent_commit=parent,
    operations=[CommitOperationAdd(path_in_repo=item['remote'],path_or_fileobj=item['local']['path']) for item in batch],
    commit_message='Preserve reviewed Terminal Bench evidence archive batch %d/%d'%(number+1,len(batches)),num_threads=2)
  current=commit.oid
  observed={'parent':parent,'commit':current,'elapsed_seconds':time.monotonic()-start,'verification_status':'pending','files':len(batch)}
  state['commits'].append(observed.copy());save(output/('batch-%04d-commit-observed.json'%number),observed)
  remote={r.path:r for r in api.get_paths_info(REPO,[item['remote'] for item in batch],repo_type='dataset',revision=current)}
  checks=[]
  for item in batch:
   row=remote.get(item['remote']);expected=item['local']
   if row is None or row.size!=expected['bytes']:raise ValueError('committed file size/readback mismatch')
   if row.lfs:
    if row.lfs.sha256!=expected['sha256']:raise ValueError('committed LFS SHA256 mismatch')
    mode='committed_LFS_content_SHA256_and_size'
   else:
    if expected['bytes']>32*1024**2:raise ValueError('large file unexpectedly stored outside LFS')
    downloaded=Path(hf_hub_download(REPO,item['remote'],repo_type='dataset',revision=current,token=token,cache_dir=output/'download-cache',force_download=True))
    resolved=downloaded.resolve(strict=True);cache=(output/'download-cache').resolve()
    if cache not in resolved.parents:raise ValueError('download cache path escaped output')
    if pin(resolved)['sha256']!=expected['sha256']:raise ValueError('committed Git file byte readback mismatch')
    mode='committed_small_file_download_SHA256_and_size'
   actual=identity(row);verified[item['remote']]=actual;checks.append({'expected':expected,'actual':actual,'verification_method':mode})
   if pin(Path(expected['path']))!=expected:raise ValueError('local publication file changed during upload')
  receipt={'parent':parent,'commit':current,'elapsed_seconds':time.monotonic()-start,'files':checks,'verified':True}
  save(output/('batch-%04d-closed.json'%number),receipt);state['commits'][-1].update({'elapsed_seconds':receipt['elapsed_seconds'],'verification_status':'passed'});state['uploaded_files']+=len(batch);parent=current
 for name,expected in before.items():
  row=next(iter(api.get_paths_info(REPO,[name],repo_type='dataset',revision=parent)),None)
  if row is None or identity(row)!=expected:raise ValueError('bootstrap/prior repository file changed')
 if api.repo_info(REPO,repo_type='dataset',revision='main').sha!=parent:raise ValueError('dataset parent changed at final verification')
 if pin(args.manifest)!=manifestpin or pin(args.review)!=reviewpin:raise ValueError('review/manifest changed')
 state.update({'status':'PUBLISHED_AND_SELECTED_REMOTE_IDENTITIES_VERIFIED','final_commit':parent,'file_count':len(files),'selected_uploaded_bytes':sum(i['local']['bytes'] for i in files),'prior_remote_files_preserved':len(before),'all_selected_files_verified':True,'whole_payload_large_file_download_performed':False,'large_file_scope':'HF committed LFS content SHA256/size, not full duplicate download','universal_secret_free_claim':False,'all_original_raw_bytes_published':manifest['original_raw_bytes_all_published'],'native_model_training_calls':0,'prover_calls':0,'proof_authority':False})
 save(output/'verified-files.json',{'repo':REPO,'revision':parent,'files':verified})


def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('manifest','review','output'):p.add_argument('--'+name,type=Path,required=True)
 for name in ('manifest','review'):p.add_argument('--expected-'+name+'-sha256',required=True)
 p.add_argument('--expected-parent-commit',required=True);p.add_argument('--wall-seconds',type=float,default=18000)
 args=p.parse_args();start=time.monotonic();output=args.output.resolve();output.mkdir(parents=True,exist_ok=False)
 state={'schema':SCHEMA,'status':'started','started_wall_time':time.time(),'primary_error_type':None,'external_network_effects_unknown_if_call_raises':True}
 save(output/'invocation.json',{'script':pin(Path(__file__).resolve()),'argv':{k:str(v) if isinstance(v,Path) else v for k,v in vars(args).items()}});save(output/'started.json',state)
 try:publish(args,output,state,start+args.wall_seconds)
 except BaseException as error:state.update({'status':'FAILED_PUBLICATION_PARTIAL_EFFECTS_RETAINED','primary_error_type':type(error).__name__});raise
 finally:state['elapsed_seconds']=time.monotonic()-start;save(output/'closed.json',state)
 print(json.dumps({'status':state['status'],'commit':state['final_commit'],'files':state['file_count'],'elapsed_seconds':state['elapsed_seconds']}))

if __name__=='__main__':main()
