"""Bind an independent source-only lineage-audit review; never run the audit."""
import ast
import datetime
import hashlib
import json
import os
from pathlib import Path
import stat

W=Path('/home/barberb/lift_coding')
OUT=Path(__file__).resolve().parent
SOURCE=W/'maintenance/ranker-objective-scalar-Git-main-lineage-audit-20261005-01/audit_main_lineage_01.py'
EXPECTED=(16250,'61a9e7949ceff62fba941cd95355562ae6612bf961984791ba49c862137815b6')
PUB=W/'maintenance/ranker-objective-scalar-git-publication-20261005-01/closed.json'


def need(value,message):
    if value is not True:raise ValueError(message)


def read(path):
    need(path.is_absolute() and path.resolve(strict=True)==path and not path.is_symlink(),'canonical regular source')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    try:
        first=os.fstat(fd);need(stat.S_ISREG(first.st_mode) and first.st_size<=1024**2,'bounded review source')
        pieces=[];total=0
        while block:=os.read(fd,65536):
            total+=len(block);need(total<=first.st_size,'source grew');pieces.append(block)
        sig=lambda value:tuple(getattr(value,key) for key in ('st_dev','st_ino','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns'))
        need(sig(first)==sig(os.fstat(fd))==sig(path.lstat()) and total==first.st_size,'source changed')
        return b''.join(pieces)
    finally:os.close(fd)


def pin(path,raw):return {'path':str(path),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def main():
    need(__debug__,'optimized review refused')
    need(OUT==W/'maintenance/ranker-objective-scalar-Git-main-lineage-source-review-20261005-01' and
         not (OUT/'review-receipt.json').exists(),'fresh independent review namespace')
    raw=read(SOURCE);need((len(raw),hashlib.sha256(raw).hexdigest())==EXPECTED,'exact final audit source')
    tree=ast.parse(raw,filename=str(SOURCE));text=raw.decode()
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):
            need(all(item.name in {'argparse','datetime','hashlib','io','json','os','re','selectors','signal','stat','subprocess','time'} for item in node.names),'stdlib imports only')
        if isinstance(node,ast.ImportFrom):need(node.module=='pathlib' and node.level==0,'stdlib Path only')
    for token in ('--no-write-fetch-head','--refmap=','single admitted private fetch','new audit ref must not exist',
                  'start_new_session=True','os.killpg(process.pid,signal.SIGKILL)','process.communicate(timeout=5)',
                  'Git output exceeded cap','DEADLINE=time.monotonic()+180','time.monotonic()+90',
                  'published commit not ancestor of current main','current main changed a published release path/mode/blob',
                  'current main published release blob body differs','published snapshot nine Gitlinks changed',
                  'current main advanced during audit; preserve failure and renew audit','original/private checkout guard drift',
                  'failed_closed_retained_audit',"'current_main_gitlinks_required_equal_to_published':False"):
        need(token in text,'reviewed isolation/bounds/lineage/guard/failure invariant')
    need(text.count("'--refmap='")==2,'exact allowlist and sole fetch both suppress configured refmaps')
    call_commands=[]
    for node in ast.walk(tree):
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id in {'git','output'} and len(node.args)>1 and isinstance(node.args[1],ast.Constant):
            call_commands.append(node.args[1].value)
    need(set(call_commands)<={'rev-parse','ls-tree','ls-files','cat-file','merge-base','ls-remote','config','for-each-ref','fetch'} and
         call_commands.count('fetch')==1,'read-only command sites plus sole admitted private fetch')
    pubraw=read(PUB);publication=json.loads(pubraw)
    pubpin=pin(PUB,pubraw)
    need(pubpin['bytes']==164119 and pubpin['sha256']=='f321b3b0952c502e492b60e3f7cee8f0fc2ee23d1076004a0032738112fe6833' and
         publication['commit']=='f6ad5d846cf340a06781fafcde4a22e48610dfaa' and publication['new_file_count']==237 and
         publication['new_file_bytes']==14870784 and publication['committed_source_blobs']==publication['remote_readback_source_blobs'],
         'immutable published snapshot exact joins')
    need(read(SOURCE)==raw and read(PUB)==pubraw,'reviewed source/snapshot changed')
    own=read(Path(__file__).resolve())
    result={'schema':'ranker-objective-scalar-Git-main-lineage-independent-source-review@1','status':'passed_source_only','findings':[],
        'created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'reviewer':pin(Path(__file__).resolve(),own),
        'reviewed_source':pin(SOURCE,raw),'reviewed_snapshot':pubpin,'mode':'unexecuted_source_only',
        'review_method':'Independent complete source and receipt-API reading, AST parse and static command/bound inspection; audit source was not imported or executed.',
        'source_findings':{'exact_publication_stage_peer_joins':True,'fresh_main_before_fetch_after_equal_or_fail_closed':True,
             'one_fetch_only_fresh_private_audit_ref_empty_refmap_no_FETCH_HEAD':True,'new_process_session_bounded_group_kill_and_drain':True,
             '180second_total_90second_command_incremental_stdout_stderr_limits':True,
             'published_commit_ancestor_and_all237_actual_body_mode_OID_size_SHA256_checks':True,
             'published_commit_nine_links_exact_snapshot_current_tip_links_separate':True,
             'original_and_private_HEAD_index_guards_before_after':True,
             'held_sources_and_immutable_receipts_rechecked':True,'exclusive_external_started_observations_blobs_closed_or_failed_outputs':True,
             'no_checkout_reset_rebase_stage_commit_push_or_remote_mutation_path':True},
        'audit_target_imports_or_execution':0,'Git_network_classifier_codec_native_model_metadata_test_jobs_in_this_review':0,
        'proof_authority':False,'execution_authority':False,'completion_authority':False,'planner_activation':False,
        'full_task_satisfaction':'unknown','all32_governing_RPI_exits':'OPEN','official_benchmark_score':None,
        'limitations':['This is an exact source gate; the separately authorized actual audit must still observe the current main tip and prove all release blobs are preserved.',
                       'The admitted fetch writes fetched objects and one new audit ref only in the isolated private repository; no remote ref or original checkout mutation is authorized.',
                       'Current-tip gitlink values are inventoried independently and need not equal the immutable published snapshot.']}
    target=OUT/'review-receipt.json'
    with target.open('xb') as stream:
        stream.write((json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+'\n').encode());stream.flush();os.fsync(stream.fileno())
    print(json.dumps({'status':result['status'],'reviewer':result['reviewer'],'receipt':pin(target,read(target))}))


if __name__=='__main__':main()
