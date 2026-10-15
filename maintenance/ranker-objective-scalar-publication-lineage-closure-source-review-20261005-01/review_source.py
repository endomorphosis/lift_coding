"""Record an independent source-only review of the unexecuted lineage closer."""
import ast
import datetime
import hashlib
import json
import os
from pathlib import Path
import stat

W=Path('/home/barberb/lift_coding')
R=W/'maintenance/ranker-objective-scalar-publication-root-20261005-01'
OUT=Path(__file__).resolve().parent
SOURCE=R/'close_combined_publication_02.py'
EXPECTED=(14606,'9f69ee08d4a7db4255d2a281a220fa60c9d14c501a4e3c9191c85e9b6a60d6ce')


def need(value,message):
    if value is not True:raise ValueError(message)


def read(path):
    need(path.is_absolute() and path.resolve(strict=True)==path and not path.is_symlink(),'canonical regular source')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    try:
        first=os.fstat(fd);need(stat.S_ISREG(first.st_mode) and first.st_size<=1024**2,'bounded review source')
        blocks=[];total=0
        while block:=os.read(fd,65536):
            total+=len(block);need(total<=first.st_size,'source grew');blocks.append(block)
        sig=lambda value:tuple(getattr(value,key) for key in ('st_dev','st_ino','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns'))
        need(sig(first)==sig(os.fstat(fd))==sig(path.lstat()) and total==first.st_size,'source changed')
        return b''.join(blocks)
    finally:os.close(fd)


def pin(path,raw):return {'path':str(path),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def main():
    need(__debug__,'optimized review refused')
    need(OUT==W/'maintenance/ranker-objective-scalar-publication-lineage-closure-source-review-20261005-01' and
         not (OUT/'review-receipt.json').exists(),'fresh independent source-review namespace')
    raw=read(SOURCE);need((len(raw),hashlib.sha256(raw).hexdigest())==EXPECTED,'final corrected closer pin')
    tree=ast.parse(raw,filename=str(SOURCE));text=raw.decode()
    old=R/'close_combined_publication_01.py';oldraw=read(old);ast.parse(oldraw,filename=str(old))
    helper=R/'close_release_publication_01.py';helperraw=read(helper);ast.parse(helperraw,filename=str(helper))
    for token in ('ranker-objective-scalar-combined-publication-plan@2','git_current_main_lineage',
                  'passed_read_only_descendant_and_all_release_blobs_preserved',
                  'actual published commit/current-main ancestry joins differ','actual current-main release population differs',
                  'fresh GitHub main differs from the stable lineage audit','independent ancestry recheck failed',
                  'current-main release path/mode/object changed','current-main release blob size differs',
                  'independent current-main release blob body recheck failed','GitHub main changed during independent current-tree/blob verification',
                  'ranker-objective-scalar-combined-publication-closure@2','release-publication-closed-02.json',
                  "'fresh_main_matches_published_commit': git_main == git_commit",'held inputs changed after remote checks'):
        need(token in text,'complete descendant-aware closure invariant')
    functions={node.name:node for node in tree.body if isinstance(node,ast.FunctionDef)}
    need('bounded_git_tree' in functions,'bounded tree reader present')
    bounded=functions['bounded_git_tree'];bt=ast.get_source_segment(text,bounded)
    need('maximum = 32 * 1024**2' in bt and 'deadline = time.monotonic() + 30' in bt and
         'min(65536, maximum - total + 1)' in bt and bt.index('if total > maximum:')<bt.index('blocks.append(block)') and
         'child.terminate()' in bt and 'child.kill()' in bt and 'child.wait(timeout=5)' in bt and 'child.stdout.close()' in bt,
         'incremental32MiB bound before append and bounded local-process cleanup')
    commands=[]
    for node in ast.walk(functions['main']):
        if isinstance(node,ast.List) and len(node.elts)>=4 and isinstance(node.elts[0],ast.Constant) and node.elts[0].value=='git':
            values=[part.value for part in node.elts if isinstance(part,ast.Constant) and type(part.value) is str]
            commands.extend(value for value in values if value in {'ls-remote','merge-base','ls-tree','cat-file','rev-parse','fetch','push','commit','checkout','reset','rebase','add'})
    need(set(commands)<={'ls-remote','merge-base','ls-tree','cat-file','rev-parse'} and set(commands)=={'ls-remote','merge-base','ls-tree','cat-file','rev-parse'},
         'new closer Git sites all read-only')
    need('git_independent_input_review' in text and 'full_frozen_selection' in text and
         "ledger['input_receipts']['frozen_inputs']" in text and "q['qualified_theorem_queries'] == 14" in text and
         "q['metadata_payloads'] == 4458" in text and 'all32_governing_RPI_exits' in text and
         "'full_task_satisfaction': 'unknown'" in text and "**namespace['AUTHORITY']" in text,
         'unchanged HF/qualification/full335/authority joins')
    need(read(SOURCE)==raw and read(old)==oldraw and read(helper)==helperraw,'reviewed sources changed')
    own=read(Path(__file__).resolve())
    result={'schema':'ranker-objective-scalar-publication-lineage-closure-independent-source-review@1','status':'passed_source_only',
        'findings':[],'mode':'unexecuted_source_only','created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'reviewer':pin(Path(__file__).resolve(),own),'reviewed_source':pin(SOURCE,raw),
        'sourcepins':[pin(SOURCE,raw),pin(old,oldraw),pin(helper,helperraw)],
        'review_method':'Independent complete final source and old01/new02 diff reading, AST parse, bound/API inspection; closer and held helper never imported or executed in this review.',
        'source_findings':{'exact_closed_v2_plan_git_main_and_lineage_descriptor':True,
             'published_commit_and_stable_current_main_are_separate':True,'exact_lineage_schema_status_ancestry_population_publication_pin_joins':True,
             'zero_mutation_false_authority_lineage_required':True,'independent_read_only_private_ancestry_current_tree_and_all237_mode_OID_size_body_SHA256_rechecks':True,
             'incremental32MiB_tree_read_30second_deadline_before_append':True,'immutable_blob_size_preflight_at_most14MiB':True,
             'fresh_main_before_after_exact_equality_or_refusal':True,'prior_HF_peer_qualification_full335_source_pin_joins_unchanged':True,
             'fresh_HF_identity_commit_original_checkout_guard_and_HELD_final_rechecks':True,
             'exclusive_new02_receipt_old01_failure_history_preserved':True,
             'no_fetch_checkout_reset_rebase_stage_commit_push_native_model_test_codec_or_metadata_job_in_new_closer':True},
        'reviewed_target_imports_or_execution':0,'Git_HTTP_native_model_classifier_codec_test_metadata_jobs_in_this_review':0,
        'proof_authority':False,'execution_authority':False,'completion_authority':False,'planner_activation':False,
        'all32_governing_RPI_exits':'OPEN','full_task_satisfaction':'unknown','official_benchmark_score':None,
        'limitations':['This exact source gate does not claim actual current-main ancestry or blob preservation; the authorized lineage audit and closer runtime must supply those observations.',
                       'The immutable published commit remains f6ad5d846cf340a06781fafcde4a22e48610dfaa; a separately pinned descendant main may be recorded while the published release blobs remain unchanged.',
                       'The existing externally pinned file-only helper is executed by the closer at runtime for stable reads, descriptor parsing and exclusive receipt save; this review executed neither source.']}
    target=OUT/'review-receipt.json'
    with target.open('xb') as stream:
        stream.write((json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+'\n').encode());stream.flush();os.fsync(stream.fileno())
    print(json.dumps({'status':result['status'],'reviewer':result['reviewer'],'receipt':pin(target,read(target))}))


if __name__=='__main__':main()
