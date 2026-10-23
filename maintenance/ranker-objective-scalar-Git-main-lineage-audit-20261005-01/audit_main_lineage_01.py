"""Audit current main ancestry and every published release blob.

Inert stdlib source. Actual execution may fetch only one fresh private audit ref;
no checkout, reset, rebase, staging, commit, push or remote mutation is present.
The immutable prior publication and both original checkout guards are preserved.
"""
import argparse
import datetime
import hashlib
import io
import json
import os
from pathlib import Path
import re
import selectors
import signal
import stat
import subprocess
import time

W = Path('/home/barberb/lift_coding')
SOURCE_ROOT = W / 'maintenance/ranker-objective-scalar-Git-main-lineage-audit-20261005-01'
PRIVATE = W / 'maintenance/ranker-objective-scalar-private-git-preparation-20261005-01/root'
PUBLICATION = W / 'maintenance/ranker-objective-scalar-git-publication-20261005-01/closed.json'
PUBLICATION_PIN = {'path':str(PUBLICATION),'bytes':164119,'sha256':'f321b3b0952c502e492b60e3f7cee8f0fc2ee23d1076004a0032738112fe6833'}
ORIGINAL_STATE = W / 'maintenance/ranker-curvature-private-git-preparation-20261005-01/original-checkout-state-01.json'
PUBLISHED = 'f6ad5d846cf340a06781fafcde4a22e48610dfaa'
MAX_FILE = 16 * 1024**2
MAX_GIT = 256 * 1024**2
HELD = {}
DEADLINE = None
GIT_CALLS = 0
FETCH_CALLS = 0


def need(value,message):
    if value is not True:raise ValueError(message)


def digest(value,length=40):
    need(type(value) is str and re.fullmatch('[0-9a-f]{'+str(length)+'}',value) is not None,'exact lowercase digest')
    return value


def read(path):
    need(path.is_absolute() and path.resolve(strict=True)==path and not path.is_symlink(),'canonical regular input')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    try:
        first=os.fstat(fd);need(stat.S_ISREG(first.st_mode) and first.st_size<=MAX_FILE,'bounded regular input')
        pieces=[];total=0
        while block:=os.read(fd,65536):
            total+=len(block);need(total<=MAX_FILE,'input grew');pieces.append(block)
        sig=lambda x:tuple(getattr(x,k) for k in ('st_dev','st_ino','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns'))
        need(sig(first)==sig(os.fstat(fd))==sig(path.lstat()) and total==first.st_size,'input changed')
        return b''.join(pieces)
    finally:os.close(fd)


def pin(path,raw=None):
    if raw is None:raw=read(path)
    return {'path':str(path),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def hold(row):
    need(type(row) is dict and set(row)=={'path','bytes','sha256'} and type(row['bytes']) is int and 0<=row['bytes']<=MAX_FILE,
         'exact bounded descriptor')
    digest(row['sha256'],64);path=Path(row['path']);raw=read(path)
    need(pin(path,raw)==row,'held source/receipt descriptor differs')
    if path in HELD:need(HELD[path]==(raw,row),'previous held input changed')
    HELD[path]=(raw,row)
    return raw


def load(row):return json.loads(hold(row))


def git(repo,*args,limit=MAX_FILE,ok=(0,),audit_ref=None):
    global GIT_CALLS,FETCH_CALLS
    allowed={'rev-parse','ls-tree','ls-files','cat-file','merge-base','ls-remote','config','for-each-ref','fetch'}
    need(len(args)>0 and args[0] in allowed,'read-only Git command or admitted private fetch only')
    need(type(limit) is int and 0<limit<=MAX_GIT,'bounded Git output')
    if args[0]=='fetch':
        need(repo==PRIVATE and audit_ref is not None and re.fullmatch('refs/ranker-objective-scalar-publication-audit/20261005-[0-9]{2}',audit_ref) is not None and
             args==('fetch','--no-tags','--no-write-fetch-head','--refmap=','origin','refs/heads/main:'+audit_ref),'fetch only new private audit ref')
        FETCH_CALLS+=1;need(FETCH_CALLS==1,'single admitted private fetch')
    remaining=DEADLINE-time.monotonic();need(remaining>0,'audit wall deadline')
    env=dict(os.environ,GIT_OPTIONAL_LOCKS='0',GIT_TERMINAL_PROMPT='0')
    command=['/usr/bin/git','-c','core.fsmonitor=false','-c','core.hooksPath=/dev/null','-c','gc.auto=0','-c','maintenance.auto=false','-C',str(repo),*args]
    process=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,start_new_session=True)
    GIT_CALLS+=1;data={process.stdout:bytearray(),process.stderr:bytearray()};end=min(DEADLINE,time.monotonic()+90)
    try:
        with selectors.DefaultSelector() as selector:
            for stream in data:selector.register(stream,selectors.EVENT_READ)
            while selector.get_map():
                need(time.monotonic()<end,'Git deadline')
                for key,_ in selector.select(min(0.25,max(0,end-time.monotonic()))):
                    block=os.read(key.fd,65536)
                    if not block:selector.unregister(key.fileobj)
                    else:
                        data[key.fileobj].extend(block)
                        need(len(data[key.fileobj])<=(limit if key.fileobj is process.stdout else 65536),'Git output exceeded cap')
        code=process.wait(timeout=max(0.001,end-time.monotonic()));need(code in ok,'bounded Git command failed')
        return bytes(data[process.stdout]),code
    finally:
        # Every descendant belongs to this new command's private process group.
        try:os.killpg(process.pid,signal.SIGKILL)
        except ProcessLookupError:pass
        process.communicate(timeout=5)
        process.stdout.close();process.stderr.close()


def output(repo,*args,**kwargs):return git(repo,*args,**kwargs)[0]


def tree(oid):
    digest(oid);result={}
    for entry in output(PRIVATE,'ls-tree','-r','-z','--full-tree',oid,limit=MAX_FILE).split(b'\0'):
        if not entry:continue
        meta,name=entry.split(b'\t',1);mode,kind,blob=meta.decode().split();path=os.fsdecode(name)
        need(mode in ('100644','100755','120000','160000') and '\n' not in path and path not in result,'unique normal Git tree leaf')
        digest(blob);result[path]=(mode,kind,blob)
    return result


def links(rows):return sorted([{'path':name,'mode':value[0],'oid':value[2]} for name,value in rows.items() if value[0]=='160000'],key=lambda r:os.fsencode(r['path']))


def guards():
    original=load(pin(ORIGINAL_STATE));result={}
    for name,old in original['original_checkouts'].items():
        path=Path(old['path']);index=Path(old['index_path']);raw=read(index)
        value={'head':output(path,'rev-parse','HEAD',limit=128).decode().strip(),'index_bytes':len(raw),'index_sha256':hashlib.sha256(raw).hexdigest()}
        need(all(value[key]==old[key] for key in value),'original root/child HEAD/index changed');result[name]=value
    current=[]
    for line in output(W,'ls-files','--stage',limit=MAX_FILE).decode().splitlines():
        if line.startswith('160000 '):
            metadata,name=line.split('\t',1);mode,oid,stage=metadata.split();current.append({'path':name,'mode':mode,'blob':oid,'stage':int(stage)})
    need(current==original['root_index_gitlinks'],'original index Gitlinks changed')
    return result


def private_guard():
    head=output(PRIVATE,'rev-parse','HEAD',limit=128).decode().strip()
    index_name=output(PRIVATE,'rev-parse','--git-path','index',limit=4096).decode().strip();path=Path(index_name)
    if not path.is_absolute():path=PRIVATE/path
    return {'head':head,'index':pin(path)}


def main_snapshot():
    raw=output(PRIVATE,'ls-remote','origin','refs/heads/main',limit=1024)
    fields=raw.decode().strip().split();need(len(fields)==2 and fields[1]=='refs/heads/main','exact public main ref')
    return {'created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'commit':digest(fields[0]),
            'ref':'refs/heads/main','observation':'fresh_git_ls_remote_origin_main'}


def save(root,name,body):
    path=root/name
    with path.open('xb') as f:f.write((json.dumps(body,sort_keys=True,indent=2,allow_nan=False)+'\n').encode());f.flush();os.fsync(f.fileno())
    fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)
    return pin(path)


def main():
    global DEADLINE
    need(__debug__,'optimized audit refused');DEADLINE=time.monotonic()+180
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',required=True,type=Path)
    parser.add_argument('--expected-source-sha256',required=True)
    parser.add_argument('--expected-source-review-sha256',required=True)
    args=parser.parse_args();root=args.output_dir
    need(root.is_absolute() and root.resolve()==root and root.parent==SOURCE_ROOT and re.fullmatch('run-[0-9]{2}',root.name) is not None and
         not root.exists(),'fresh external lineage audit output namespace')
    own_path=Path(__file__).resolve();own=pin(own_path)
    need(own_path==SOURCE_ROOT/'audit_main_lineage_01.py' and own['sha256']==digest(args.expected_source_sha256,64),'exact admitted source')
    review_path=W/'maintenance/ranker-objective-scalar-Git-main-lineage-source-review-20261005-01/review-receipt.json'
    review_pin=pin(review_path);need(review_pin['sha256']==digest(args.expected_source_review_sha256,64),'exact independent source-review pin')
    review=load(review_pin)
    need(review['schema']=='ranker-objective-scalar-Git-main-lineage-independent-source-review@1' and review['status']=='passed_source_only' and
         review['findings']==[] and review['reviewed_source']==own,'independent exact source gate')
    publication=load(PUBLICATION_PIN)
    need(publication['status']=='PUBLISHED_AND_VERIFIED' and publication['commit']==PUBLISHED and publication['remote_main']==PUBLISHED and
         publication['new_file_count']==237 and publication['new_file_bytes']==14870784,'immutable successful publication snapshot')
    stage=load(publication['final_stage']);peer=load(publication['independent_final_input_review'])
    need(stage['status']=='passed_complete_increment_HF_verified_ready_to_commit' and peer['findings']==[] and
         publication['final_stage'] in peer['reviewed_input_pins'],'published stage/externalpeer join')
    root.mkdir();started=save(root,'started.json',{'schema':'ranker-objective-scalar-main-lineage-audit-started@1','producer':own,
         'source_review':review_pin,'git_publication_pin':PUBLICATION_PIN,'published_commit':PUBLISHED,'remote_mutations':0})
    observed_commit=None
    try:
        before_guards=guards();before_private=private_guard()
        need(before_private['head']==PUBLISHED,'private checkout remains original published commit')
        url=output(PRIVATE,'config','--get','remote.origin.url',limit=4096).decode().strip()
        need(url in ('https://github.com/endomorphosis/lift_coding.git','git@github.com:endomorphosis/lift_coding.git'),'expected sanitized GitHub repository')
        before=main_snapshot();observed_commit=before['commit'];before_pin=save(root,'main-before.json',before)
        audit_ref='refs/ranker-objective-scalar-publication-audit/20261005-'+root.name[-2:]
        need(output(PRIVATE,'for-each-ref','--format=%(refname)',audit_ref,limit=1024)==b'','new audit ref must not exist')
        output(PRIVATE,'fetch','--no-tags','--no-write-fetch-head','--refmap=','origin','refs/heads/main:'+audit_ref,audit_ref=audit_ref,limit=65536)
        tip=output(PRIVATE,'rev-parse',audit_ref,limit=128).decode().strip();need(tip==before['commit'],'main advanced between observation and fetch')
        _,code=git(PRIVATE,'merge-base','--is-ancestor',PUBLISHED,tip,ok=(0,1),limit=128);need(code==0,'published commit not ancestor of current main')
        published_tree=tree(PUBLISHED);current_tree=tree(tip)
        need(output(PRIVATE,'rev-parse',PUBLISHED+'^{tree}',limit=128).decode().strip()==publication['tree'],'published tree changed')
        published_links=links(published_tree)
        need(len(published_links)==9 and published_links==publication['commit_gitlinks']==publication['parent_gitlinks'],'published snapshot nine Gitlinks changed')
        expected=publication['remote_readback_source_blobs']
        need(expected==publication['committed_source_blobs']==stage['staged_source_blobs'] and len(expected)==237 and
             sum(row['bytes'] for row in expected)==14870784,'whole immutable published population joins')
        verified=[]
        for row in expected:
            path=row['path'];wanted=('100644','blob',row['git_blob_oid'])
            need(published_tree.get(path)==wanted and current_tree.get(path)==wanted,'current main changed a published release path/mode/blob')
            raw=output(PRIVATE,'cat-file','blob',row['git_blob_oid'],limit=MAX_FILE)
            actual={'path':path,'mode':'100644','git_blob_oid':row['git_blob_oid'],'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
            need(actual==row,'current main published release blob body differs');verified.append(actual)
        blobs_pin=save(root,'verified-release-blobs.json',{'schema':'ranker-objective-scalar-current-main-release-blobs@1',
             'published_commit':PUBLISHED,'current_main':tip,'files':verified,'file_count':237,'file_bytes':14870784})
        for path,(raw,row) in list(HELD.items()):need(read(path)==raw and pin(path,raw)==row,'held immutable receipt/source changed')
        need(pin(own_path)==own,'source changed during audit')
        after_guards=guards();after_private=private_guard()
        need(before_guards==after_guards==publication['original_guard_after'] and before_private==after_private,'original/private checkout guard drift')
        after=main_snapshot();after_pin=save(root,'main-after.json',after)
        need(after['commit']==tip==before['commit'],'current main advanced during audit; preserve failure and renew audit')
        result={'schema':'ranker-objective-scalar-current-main-lineage-audit@1',
             'status':'passed_read_only_descendant_and_all_release_blobs_preserved','created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
             'producer':own,'source_review':review_pin,'started':started,'published_commit':PUBLISHED,'current_main':tip,
             'current_main_before':before['commit'],'current_main_after':after['commit'],'published_commit_is_ancestor':True,
             'release_files':237,'release_bytes':14870784,'all_release_blobs_at_current_main_verified':True,'stable_main_before_after':True,
             'git_publication_pin':PUBLICATION_PIN,'reviewed_input_pins':[PUBLICATION_PIN,publication['final_stage'],publication['independent_final_input_review'],review_pin],
             'main_before':before_pin,'main_after':after_pin,'verified_release_blobs':blobs_pin,'all_original_checkout_guards_unchanged':True,
             'original_guard_before':before_guards,'original_guard_after':after_guards,'private_guard_before':before_private,'private_guard_after':after_private,
             'published_commit_gitlinks_preserved':True,'published_commit_gitlinks':published_links,'current_main_gitlinks':links(current_tree),
             'current_main_gitlinks_required_equal_to_published':False,'fresh_private_audit_ref':audit_ref,'private_fetch_calls':FETCH_CALLS,
             'read_only_Git_and_admitted_private_fetch_calls':GIT_CALLS,'remote_mutations':0,'git_commits_or_pushes':0,
             'original_or_private_HEAD_index_mutations':0,'native_model_metadata_classifier_codec_or_test_jobs':0,'target_or_project_imports':0,
             'proof_authority':False,'execution_authority':False,'completion_authority':False,'planner_activation':False,'full_task_satisfaction':'unknown'}
        closed=save(root,'closed.json',result);print(json.dumps({'status':result['status'],'published_commit':PUBLISHED,'current_main':tip,
             'release_files':237,'release_bytes':14870784,'receipt':closed,'original_private_guards_unchanged':True}))
    except Exception as error:
        save(root,'failed.json',{'schema':'ranker-objective-scalar-main-lineage-retained-failure@1','status':'failed_closed_retained_audit',
             'producer':own,'git_publication_pin':PUBLICATION_PIN,'published_commit':PUBLISHED,'observed_main':observed_commit,
             'reason':str(error)[:2048] if isinstance(error,ValueError) else type(error).__name__,'remote_mutations':0,'git_commits_or_pushes':0,
             'private_fetch_calls':FETCH_CALLS,'proof_authority':False,'execution_authority':False,'completion_authority':False,'planner_activation':False})
        raise


if __name__=='__main__':main()
