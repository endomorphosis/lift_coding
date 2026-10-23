"""Hermetic red-before-fix CID/revision repro over fresh public native fixtures."""
from pathlib import Path
from copy import deepcopy
import hashlib
import json
import os

C = Path('/home/barberb/lift_coding/maintenance/terminal-token-reduction-20261007-01/checkout')
O = Path(__file__).absolute().parent
BASELINE_SHA = 'ab3f9e8bc9f3da0afc1db862de2f153b53c41a0f58e45c4e9fff11ff56800e52'

def sha(raw): return hashlib.sha256(raw).hexdigest()
def pin(path):
    raw=path.read_bytes();return {'path':str(path),'bytes':len(raw),'sha256':sha(raw)}
def main():
    baseline_raw=(O/'beginning-source-pins.json').read_bytes()
    assert sha(baseline_raw)==BASELINE_SHA
    baseline=json.loads(baseline_raw)
    before=[]
    for row in baseline['files']:
        got=pin(C/row['path']);assert got['sha256']==row['sha256'] and got['bytes']==row['bytes']
        before.append({'path':row['path'],'bytes':got['bytes'],'sha256':got['sha256']})
    assert len(before)==4
    root=O/'repro-before-01';root.mkdir(mode=0o755)
    os.umask(0o022)
    from test.api.test_reviewed_source_nomination_context import make_case, load, modified_prompt
    from test.api.test_reviewed_source_nomination_audit import historical_case, replay
    from ipfs_accelerate_py.agent_supervisor.runtime.code_source_inspection import CodeSourceInspectionError
    cases=[]
    live_root=root/'live';live_root.mkdir(mode=0o755)
    live=make_case(live_root)
    old_block,old_receipt,_=load(live)
    cid,revision=live['inputs']['task_cid'],live['inputs']['task_revision']
    assert cid!=revision
    prompt,semantic=modified_prompt(live,lambda capsule:capsule.update(objective_revision=revision))
    old=json.loads(live['prompt']);new=json.loads(prompt)
    assert {k:v for k,v in old.items() if k!='objective_revision'}=={k:v for k,v in new.items() if k!='objective_revision'}
    assert live['public']['task_cid']==cid
    try:
        load(live,prompt=prompt,semantic_verification=semantic)
    except CodeSourceInspectionError as error:
        assert str(error)=='verified source-bound IntentIR coding instruction required'
        cases.append({'kind':'live','task_cid':cid,'task_revision':revision,
            'native_capsule_objective_revision_before':old['objective_revision'],
            'native_capsule_objective_revision_after':revision,
            'old_conflated_fixture_accepted':True,'production_correct_distinct_revision_refused':True,
            'refusal_type':type(error).__name__,'refusal_literal_sha256':sha(str(error).encode()),
            'only_capsule_revision_and_native_prompt_identity_updated':True,
            'public_instruction_and_independent_nomination_frontier_inputs_unchanged':True})
    else: raise AssertionError('prepatch live distinct revision unexpectedly admitted')
    historical_root=root/'historical';historical_root.mkdir(mode=0o755)
    case=historical_case(historical_root)
    block,checks,_=replay(case)
    assert block==case['block_expected']
    cid,revision=case['inputs']['task_cid'],case['inputs']['task_revision'];assert cid!=revision
    prompt,semantic=modified_prompt(case,lambda capsule:capsule.update(objective_revision=revision))
    receipt=deepcopy(case['receipt']);receipt.update(native_prompt_sha256=sha(prompt.encode()),native_prompt_bytes=len(prompt.encode()))
    assert {k:v for k,v in receipt.items() if k not in ('native_prompt_sha256','native_prompt_bytes')}=={k:v for k,v in case['receipt'].items() if k not in ('native_prompt_sha256','native_prompt_bytes')}
    try:
        replay(case,prompt=prompt,receipt=receipt,semantic_verification=semantic)
    except CodeSourceInspectionError as error:
        assert str(error)=='verified original signed instruction required'
        cases.append({'kind':'historical-published-source-retired-worktree','task_cid':cid,'task_revision':revision,
            'old_conflated_fixture_accepted':True,'production_correct_distinct_revision_refused':True,
            'refusal_type':type(error).__name__,'refusal_literal_sha256':sha(str(error).encode()),
            'original_baseline_preserved':True,'retired_worktree_absent':not case['retired_workspace'].exists(),
            'only_capsule_revision_and_native_prompt_identity_updated':True,
            'all_other_receipt_instruction_and_artifact_identities_unchanged':True})
    else: raise AssertionError('prepatch historical distinct revision unexpectedly admitted')
    after=[]
    for row in baseline['files']:
        got=pin(C/row['path']);after.append({'path':row['path'],'bytes':got['bytes'],'sha256':got['sha256']})
    assert after==before,'baseline changed during prepatch reproduction'
    result={'schema':'nomination-task-identity-prepatch-reproduction@1','baseline':pin(O/'beginning-source-pins.json'),
        'sources_before':before,'sources_after':after,'all_source_pins_unchanged':True,
        'cases':cases,'reproduced_old_cid_revision_conflation':len(cases)==2,
        'native_query_ast_frontier_capture_and_original_git_historical_replay_real':True,
        'cryptographic_instruction_admission_fixture':False,'fixture_admission_flags_explicit_stubs':True,
        'provider_or_actual_owner_or_target_code_or_private_auth_or_old_database_read':False,
        'source_tests_or_prior_stage_artifacts_modified':False,
        'training_model_convergence_or_task_success_claimed':False}
    raw=(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
    out=O/'prepatch-identity-reproduction-01.json'
    with out.open('xb') as stream:stream.write(raw)
    print(json.dumps({'receipt':str(out),'bytes':len(raw),'sha256':sha(raw),'reproduced_cases':len(cases),'source_pins_unchanged':True}))
if __name__=='__main__':main()
