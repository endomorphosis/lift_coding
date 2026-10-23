"""Read three exact historical Git blobs; export count/status commitments only."""
import hashlib
import json
import os
import subprocess
from pathlib import Path
from audit_io import ROOT,OUT,write_json

PATH='papers/completion/neurosymbolic_supervision/qualification/reuse_analysis.json'
COMMITS=['d0714ecfae25d4ceca1f1c7044a8f542e64f5515','74c50e431a45f8af5e2b0a78d89ed196bc44dfd2','6765f4a62046613df119e085e84277feac5b8873']

def read(commit):
    spec=commit+':'+PATH
    size=int(subprocess.run(['git','-C',str(ROOT),'cat-file','-s',spec],check=True,capture_output=True,text=True).stdout)
    if size>2*1024*1024:raise ValueError('Git evidence exceeds bound')
    raw=subprocess.run(['git','-C',str(ROOT),'show',spec],check=True,capture_output=True).stdout
    source={'repository':str(ROOT),'commit':commit,'path':PATH,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),
            'evidence_tier':'original_record','signature_verification':'not_performed','read_only_git_blob':True}
    expected=next(x for x in json.loads((OUT/'workstreams/git_reuse_inputs.json').read_text())['records'] if x['commit']==commit)
    assert source['sha256']==expected['sha256']
    return json.loads(raw),source

def main():
    projections=[]
    for commit in COMMITS:
        d,source=read(commit)
        p={'source':source,'schema':d['schema'],'task_id':d['task_id'],'policy_id':d['policy_id'],
           'historical_source_hashes':d['source_hashes'],'behavior_reexecuted':False}
        if d['task_id']=='NS-011':
            a=d['all_attempted_reuse_cases'];subset=d['profiles']['identity-from-files']
            p.update(all_attempted= a['denominator'],all_attempted_false_reuse=a['false_reuse']['events'],
                     all_attempted_false_reuse_fraction=a['false_reuse']['exact_counts'],
                     excluded_stale_key_attack_in_denominator=a['includes_excluded_stale_key_attack'],
                     selected_profile_attempted=subset['attempted_reuse_cases'],selected_profile_false_reuse=subset['false_reuse']['events'],
                     selected_profile_safe_agreements=subset['safe_agreement_cases'],
                     skipped_or_unavailable_cases=subset['oracle_skip_or_unavailable_cases'],
                     positive_reuse_witnesses=d['positive_reuse_witness_count'],
                     scoring_class_counts={k:len(v) for k,v in d['scoring_classes'].items()},
                     later_scope_characterization='NS-027 characterizes this cohort as controlled mocked-verifier qualification, not production authority',
                     reported_consumer_gitlinks=d['consumer_gitlinks'],reported_workspace_git_head=d['workspace_git_head'],
                     confidence_intervals_not_recomputed_or_used_for_generality=True)
            assert p['all_attempted']==26 and p['all_attempted_false_reuse']==1
            assert sum(p['scoring_class_counts'].values())==26
        else:
            p.update(accepted_route=d['accepted_route'],final_admission_enabled=d['final_admission_enabled'],
                     reuse_admitted=d['reuse_admitted'],historical_ns011=d['historical_ns011'],
                     ns027_attempted=d['ns027_cohort']['attempted'],
                     ns027_false_reuse_events=d['paper_claim']['false_reuse']['events'],
                     ns027_false_reuse_denominator=d['paper_claim']['false_reuse']['denominator'],
                     ns027_reuse_witnesses=d['paper_claim']['reuse_witness_count'],
                     paper_claim_status=d['paper_claim']['claim_status'],speedup_claimed=d['paper_claim']['speedup_claimed'],
                     exclusion_reason=d['paper_claim']['exclusion'],
                     ns016_pilot_or_final_credit=d['ns016_pilot_or_final_credit'],
                     denominator_scope=d['ns027_cohort'].get('denominator_scope','not stated in this revision'),
                     false_denial_is_defined=d['paper_claim']['false_denial']['denominator'] is not None)
            assert p['reuse_admitted'] is False and p['ns027_reuse_witnesses']==0
        projections.append(p)
    result={'schema':'historical-reuse-git-recovery@1','records':projections,
            'exact_missing_file_recovered':True,'live_worktree_restored':False,'source_modified':False,
            'scoped_search_routes':[
                'git log --all -5 --format=%H -- '+PATH,
                'git cat-file -s COMMIT:'+PATH,
                'git show COMMIT:'+PATH],
            'new_run_or_reuse_admission':False,'old_false_reuse_preserved':True,
            'limits':['This recovers original analysis artifacts, not every underlying test/custody receipt.',
                      'NS-011 and NS-027 are different historical qualification stages, not repeats of the14-case later adapter.',
                      'The claimed NS-011 subset0/25 cannot erase all-attempted1/26.',
                      'NS-0270/16 under no admitted reuse is not a zero-risk estimate for positive reuse.',
                      'No historical confidence interval is used to infer general reliability.'],
            'gap_update':{'prior_gap':17,'status':'closed','resolved':'Exact missing reuse_analysis.json recovered in three scoped Git revisions; adverse original and later removal both preserved.',
                          'remaining':'Underlying per-case receipts/signatures and all earlier partials not recovered in this pass.'}}
    write_json('workstreams/git_reuse_recovery.json',result)
    print(json.dumps({'revisions':len(projections),'all_attempted_false_reuse':'1/26','later_route':projections[0]['accepted_route'],'new_execution':False}))

if __name__=='__main__':
    os.umask(0o077);main()
