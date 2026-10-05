"""Freeze concrete reviewed local/archive or authorized HF argv and byte pins."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re

W=Path('/home/barberb/lift_coding')
R=Path(__file__).resolve().parent
S=W/'maintenance/ranker-objective-scalar-publication-20261005-01'
P=W/'maintenance/ranker-objective-scalar-publication-package-20261005-01'
HF=W/'maintenance/terminal-ir-publication-20261004-01/huggingface'
INPUT_REVIEW=W/'maintenance/ranker-objective-scalar-publication-input-review-20261005-01'
HELD={}


def pin(path):
    path=Path(path).absolute()
    if path.resolve(strict=True)!=path or not path.is_file() or path.is_symlink():raise ValueError('canonical regular input')
    before=path.stat();digest=hashlib.sha256();size=0
    with path.open('rb') as f:
        while block:=f.read(1024**2):digest.update(block);size+=len(block)
    after=path.stat();sign=lambda v:(v.st_dev,v.st_ino,v.st_mode,v.st_size,v.st_mtime_ns,v.st_ctime_ns)
    if sign(before)!=sign(after) or size!=before.st_size:raise ValueError('input drift')
    value={'path':str(path),'bytes':size,'sha256':digest.hexdigest()}
    if str(path) in HELD and HELD[str(path)]!=value:raise ValueError('previous input changed')
    HELD[str(path)]=value
    return value


def load(path):
    before=pin(path)
    if before['bytes']>32*1024**2:raise ValueError('JSON input exceeds bound')
    with Path(path).open('rb') as f:raw=f.read(32*1024**2+1)
    if len(raw)>32*1024**2:raise ValueError('JSON input grew beyond bound')
    if len(raw)!=before['bytes'] or hashlib.sha256(raw).hexdigest()!=before['sha256']:raise ValueError('parsed buffer drift')
    return json.loads(raw)


def need(value,message):
    if value is not True:raise ValueError(message)


def main():
    need(__debug__,'optimized Python refused')
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=('package','package-review','final-upload-scan','hf-publication'))
    parser.add_argument('--expected-closure-sha256',required=True)
    parser.add_argument('--expected-input-review-sha256',required=True)
    parser.add_argument('--expected-guards-sha256',required=True)
    a=parser.parse_args()
    need(all(re.fullmatch('[0-9a-f]{64}',value) is not None for value in
        (a.expected_closure_sha256,a.expected_input_review_sha256,a.expected_guards_sha256)),
        'independent lowercase SHA256 pins required')
    closure=pin(S/'closed-inputs.json');need(closure['sha256']==a.expected_closure_sha256,'independent closure pin')
    closed=load(closure['path'])
    need(set(closed)=={'schema','plan','final_selection','preparation_source','publication_profile'} and
        closed['schema']=='ranker-objective-scalar-publication-closed-inputs@1','exact frozen closure schema')
    plan_pin=pin(S/'plan.json');selection_pin=pin(S/'final-selection.json')
    need(closed['plan']==plan_pin and closed['final_selection']==selection_pin and
        closed['preparation_source']==pin(S/'freeze_inputs.py'),'closure joins exact plan, selection and producer')
    publication_plan=load(plan_pin['path']);selection=load(selection_pin['path'])
    need(publication_plan['schema']=='ranker-objective-scalar-publication-plan@1' and
        publication_plan['status']=='frozen_final_plan' and publication_plan['source_and_artifacts_quiet'] is True and
        publication_plan['source_plan_quiet'] is True and publication_plan['publication_profile']==closed['publication_profile'],
        'quiet frozen plan and unchanged publication profile')
    need(selection['schema']=='ranker-objective-scalar-publication-final-selection@1','complete final selection schema')
    guard_pin=pin(R/'inherited-publication-guards-01.json')
    need(guard_pin['sha256']==a.expected_guards_sha256,'independent complete guard pin')
    review_pin=pin(INPUT_REVIEW/'review-receipt.json');need(review_pin['sha256']==a.expected_input_review_sha256,'independent input-review pin')
    review=load(review_pin['path']);need(review['status']=='passed_file_only_final_publication_input_review' and review['outstanding_issues']==[],'final independent scope review')
    need(review['schema']=='ranker-objective-scalar-final-publication-input-review@1' and
        review['fixed_inputs']=={'closed':closure,'plan':plan_pin,'selection':selection_pin,'guards':guard_pin} and
        review['reviewer']==pin(INPUT_REVIEW/'review_inputs_01.py'),
        'peer review joins exact closure, plan, selection, guards and reviewer source')
    need(all(review[key] is False for key in ('proof_authority','execution_authority','completion_authority','planner_activation')),
        'peer review grants no authority')
    guards=load(guard_pin['path'])['files']
    selected=selection['files']
    need(type(guards) is list and 0<len(guards)<=30000 and len(guards)==len({row['path'] for row in guards}),
        'complete unique bounded guard population')
    need(type(selected) is list and 0<len(selected)<=10000 and len(selected)==len({row['path'] for row in selected}),
        'complete unique bounded selected population')
    expected={row['path']:row for row in guards}
    for row in selected:
        item={k:row[k] for k in ('path','bytes','sha256')}
        if item['path'] in expected:need(expected[item['path']]==item,'inherited selection conflict')
        expected[item['path']]=item
    for path in (Path(__file__).resolve(),S/'closed-inputs.json',S/'plan.json',S/'final-selection.json',R/'inherited-publication-guards-01.json',INPUT_REVIEW/'review-receipt.json',INPUT_REVIEW/'review_inputs_01.py',HF/'run_frozen_publication_phase.py'):
        expected[str(path)]=pin(path)
    need(pin(HF/'run_frozen_publication_phase.py')['sha256']=='8d9955df76155f75326fdda8039119bacab9bad3ca71306f241be9b2124d01b8','frozen wrapper')
    if a.phase=='package':
        need(not P.exists(),'new local package namespace')
        argv=['/usr/bin/python3.12','-B',str(S/'build_package.py'),'--closed-inputs',closure['path'],'--expected-closed-inputs-sha256',closure['sha256'],'--output',str(P)]
    elif a.phase=='package-review':
        close=load(P/'closed.json');manifest=pin(P/'package/manifest.json');need(close['status']=='passed_local_frozen_package' and close['manifest']==manifest,'completed local package')
        for shard in load(manifest['path'])['data_shards']:
            bound={k:shard[k] for k in ('path','bytes','sha256')};need(pin(bound['path'])==bound,'shard drift');expected[bound['path']]=bound
        expected[manifest['path']]=manifest;expected[str(P/'closed.json')]=pin(P/'closed.json')
        argv=['/usr/bin/python3.12','-B',str(S/'review_package.py'),'--closed-inputs',closure['path'],'--expected-closed-inputs-sha256',closure['sha256'],'--manifest',manifest['path'],'--expected-manifest-sha256',manifest['sha256'],'--expected-builder-sha256',pin(S/'build_package.py')['sha256'],'--output',str(S/'package-review-01.json')]
    else:
        local_review=load(S/'package-review-01.json')
        package_closed=load(P/'closed.json');manifest_pin=pin(P/'package/manifest.json')
        need(local_review['status']=='passed' and local_review['closed_inputs']==closure and
            local_review['manifest']==manifest_pin and local_review['package_closure']==pin(P/'closed.json') and
            local_review['reviewer']==pin(S/'review_package.py') and
            package_closed['status']=='passed_local_frozen_package' and package_closed['manifest']==manifest_pin,
            'decoded member review joins this frozen population and package')
        expected[manifest_pin['path']]=manifest_pin;expected[str(P/'closed.json')]=pin(P/'closed.json')
        outer=load(R/'package-review-outer-01/closed.json');need(outer['status']=='closed_phase' and outer['returncode']==0 and outer['input_pins_unchanged'] is True and outer['cleanup_errors']==[],'decoded review outer closure')
        plan=load(R/'hf-plan-01.json');plan_pin=pin(R/'hf-plan-01.json')
        need(plan['expected_parent_commit']=='fae2e38dc882929edb2bcd2226560f0da3dfcd9e' and 0<len(plan['files'])<=100,'exact HF parent/population')
        need(plan['immutable_namespace']=='releases/20261004-terminal-codebase-ir-evidence-v1/successor-ranker-objective-scalar-v1',
            'exact objective-scalar immutable namespace')
        for item in plan['files']:expected[item['local']['path']]=item['local']
        for path in (S/'package-review-01.json',R/'package-review-outer-01/closed.json',R/'hf-plan-01.json',R/'prepare_hf_plan_01.py',R/'scan_final_upload_01.py',R/'review_hf_readback_01.py',HF/'publish_successor_evidence_02.py'):
            expected[str(path)]=pin(path)
        need(pin(HF/'publish_successor_evidence_02.py')['sha256']=='670e064a8222ce1b0c962e202985974741a9a4476630b0541c7ec880b32009f2','frozen publisher')
        if a.phase=='final-upload-scan':
            argv=['/usr/bin/python3.12','-B',str(R/'scan_final_upload_01.py'),'--expected-plan-sha256',plan_pin['sha256'],'--expected-files',str(len(plan['files']))]
        else:
            scan=load(R/'final-upload-scan-01.json');scan_outer=load(R/'final-upload-scan-outer-01/closed.json')
            need(scan['status']=='passed' and scan['candidate_hits']==0 and scan['plan']==plan_pin and scan['selected_files']==len(plan['files']),'complete final scan')
            need(scan_outer['status']=='closed_phase' and scan_outer['returncode']==0 and scan_outer['input_pins_unchanged'] is True and scan_outer['cleanup_errors']==[],'scan outer closure')
            for path in (R/'final-upload-scan-01.json',R/'final-upload-scan-outer-01/closed.json'):expected[str(path)]=pin(path)
            need(not (R/'hf-publication-01').exists(),'new publisher output')
            argv=['/usr/bin/env','HF_HUB_DISABLE_XET=1','HF_HUB_ENABLE_HF_TRANSFER=0','/home/barberb/.local/bin/python','-B',str(HF/'publish_successor_evidence_02.py'),'--plan',plan_pin['path'],'--expected-plan-sha256',plan_pin['sha256'],'--expected-parent-commit',plan['expected_parent_commit'],'--output',str(R/'hf-publication-01')]
    observed=[pin(path) for path in sorted(expected)]
    need(observed==[expected[path] for path in sorted(expected)],'whole frozen population drift')
    need(all(pin(path)==binding for path,binding in list(HELD.items())),'parsed/guard inputs drift')
    invocation={'schema':'terminal-ir-frozen-publication-phase-invocation@1','phase':'ranker-objective-scalar-'+a.phase+'-01','argv':argv,'cwd':str(W),'wall_seconds':900 if a.phase=='hf-publication' else 180,'pinned_inputs':observed,'remote_mutation_scope':'authorized_single_CAS_successor_commit_Publicus_codebase_ir_proof_index_only' if a.phase=='hf-publication' else 'none_local_bounded_archive_and_review_only','proof_authority':False,'execution_authority':False,'completion_authority':False,'planner_activation':False}
    target=R/(a.phase+'-invocation-01.json')
    with target.open('xb') as f:f.write((json.dumps(invocation,sort_keys=True,allow_nan=False)+'\n').encode());f.flush();os.fsync(f.fileno())
    print(json.dumps({'invocation':pin(target),'pinned_inputs':len(observed)}))


if __name__=='__main__':main()
