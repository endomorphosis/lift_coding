"""Assemble new evidence overlays without changing the frozen prior audit.

Usage: python assemble_supplement.py --output /a/new/output/directory
Only reads previously generated audit projections. No runtime package imports.
"""
import argparse
import copy
import csv
import hashlib
import io
import json
import os
from pathlib import Path
from collections import Counter

BASE=Path(__file__).resolve().parent
PRIOR=BASE.parent/'paper-supervision-evidence-closeout-v2-audit-20261015-01'

def load(path):return json.loads(path.read_text())
def rows(path):return [json.loads(s) for s in path.read_text().splitlines() if s]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True,type=Path)
    out=parser.parse_args().output.absolute();out.mkdir(mode=0o700,parents=True,exist_ok=True)
    if out.resolve()!=out:raise ValueError('Symlink output')
    def write(name,text):
        p=out/name;p.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        with p.open('x') as f:f.write(text)
        p.chmod(0o600)
    def js(name,obj):write(name,json.dumps(obj,indent=2,sort_keys=True)+'\n')
    def jl(name,items):write(name,''.join(json.dumps(x,sort_keys=True)+'\n' for x in items))
    def table(name,items,fields):
        s=io.StringIO();w=csv.DictWriter(s,fieldnames=fields);w.writeheader()
        for x in items:w.writerow({k:json.dumps(x[k],sort_keys=True) if isinstance(x.get(k),(list,dict)) else x.get(k) for k in fields})
        write(name,s.getvalue())
    checks=[]
    def check(name,actual,expected):
        checks.append({'check':name,'actual':actual,'expected':expected,'passed':actual==expected})

    prior_runs=rows(PRIOR/'runs.jsonl');runs=copy.deepcopy(prior_runs)
    by_id={r['original_run_id']:r for r in runs if r['original_run_id'] is not None}
    candidate=next(r for r in runs if r['ledger_id']=='T1-retrieval-candidate')
    check('candidate prior identity unavailable',candidate['original_run_id'],None)
    identity='fix-code-vulnerability__VkepsZo'
    candidate['identity_history']=[{'original_run_id':None,'source':str(PRIOR/'runs.jsonl')},
                                   {'original_run_id':identity,'source':'workstreams/t1_run_updates.jsonl'}]
    candidate['original_run_id']=identity;by_id[identity]=candidate
    # Preserve old counters/flags even where a new original has a narrower schema.
    for file in ['t1_run_updates.jsonl','t2_runs.jsonl']:
        for obs in rows(BASE/'workstreams'/file):
            rid=obs['run_id'];r=by_id[rid]
            r.setdefault('supplement_observations',[]).append({'projection':file,'observation':obs})
            r['evidence_paths']=list(dict.fromkeys(r['evidence_paths']+obs.get('evidence_paths',[])))
            reward=obs.get('reward',obs.get('official_reward'))
            if reward is not None:check('original reward agrees:'+rid,reward,r['original_reward'])
            total=obs.get('total_tokens')
            if total is None:total=(obs.get('counters') or obs.get('receipt_known_counter_subtotal') or {}).get('total_tokens')
            if total is not None:check('retained total agrees:'+rid,total,r['reported_tokens'].get('total_tokens'))
    for obs in rows(BASE/'workstreams/t1_slot_inventory.jsonl'):
        if obs['run_id'] is not None:
            by_id[obs['run_id']]['planned']=obs['planned']
            by_id[obs['run_id']]['planned_slot_observation']=obs
    for r in runs:
        r['supplement_scope']='Additional evidence for an existing observation; no new trial or token charge'
    check('no new run rows',len(runs),len(prior_runs))
    for before,after in zip(prior_runs,runs):
        check('reported outcome/counters unchanged:'+after['ledger_id'],
              [after['original_reward'],after['reported_tokens'],after['native_usage_complete']],
              [before['original_reward'],before['reported_tokens'],before['native_usage_complete']])
    jl('runs.jsonl',runs)
    identity_map={'prior_ledger_id':'T1-retrieval-candidate','prior_original_run_id':None,'original_run_id':identity,
                  'same_two_native_sessions_bound':True,'new_trial':False,'new_token_charge':False,
                  'evidence':'workstreams/t1_integrity_joins.json'}
    js('identity_updates.json',identity_map)

    sessions=copy.deepcopy(rows(PRIOR/'sessions.jsonl'))
    sid_map={x['session_id']:x for x in sessions if x['session_id'] is not None}
    iid_map={x['invocation_id']:x for x in sessions if x.get('invocation_id') is not None}
    links=[]
    for file in ['t1_session_updates.jsonl','t2_sessions.jsonl']:
        for obs in rows(BASE/'workstreams'/file):
            sid=obs['session_id'];assert sid is not None
            existing=sid in sid_map
            if existing:s=sid_map[sid]
            else:
                s={'schema':'paper-session-ledger@1','ledger_id':'provider_session:'+sid,'identity_kind':'provider_session',
                   'session_id':sid,'invocation_id':obs.get('invocation_id'),'run_ids':[],
                   'reported_usage':obs.get('counters',obs.get('counts')),'usage_complete':None,
                   'evidence_paths':[],'signature_verification':'not_performed','combined_project_cost_authority':False}
                sid_map[sid]=s;sessions.append(s)
            s.setdefault('supplement_observations',[]).append({'projection':file,'observation':obs})
            s['run_ids']=list(dict.fromkeys(s['run_ids']+[obs['run_id']]))
            s['evidence_paths']=list(dict.fromkeys(s['evidence_paths']+obs.get('evidence_paths',[])))
            links.append({'original_session_id':sid,'existing_session_row':existing,'run_id':obs['run_id'],
                          'relation':'same-session-as','new_charge':False,'source_projection':file})
    for obs in rows(BASE/'workstreams/historical_provider_calls.jsonl'):
        call_id=obs['call_id'];s=iid_map[call_id]
        assert s['session_id'] is None
        s.setdefault('supplement_observations',[]).append({'projection':'historical_provider_calls.jsonl','observation':obs})
        s['recovered_per_request_usage']=obs['reported_usage']
        s['usage_complete_for_recorded_call']=obs['usage_complete_for_recorded_call']
        s['served_fingerprint']=obs['served_fingerprint']
        s['served_fingerprint_is_authenticated_weight_revision']=False
        links.append({'original_call_id':call_id,'existing_call_row':True,'run_id':obs['run_id'],
                      'relation':'reports-on','session_id':None,'new_charge':False})
    check('session ledger identity uniqueness',len({s['ledger_id'] for s in sessions}),len(sessions))
    jl('sessions.jsonl',sessions);jl('session_update_links.jsonl',links)

    encoders=copy.deepcopy(rows(PRIOR/'encoder_deployment_ledger.jsonl'))
    assets=load(BASE/'audit/large_asset_verification.json')
    backend=next(x for x in assets['results'] if x['asset']=='Intent development backend')
    count=0
    for x in encoders:
        if x.get('backend_checkpoint',{}).get('sha256')==backend['sha256']:
            x['prior_backend_exact_bytes_verified']=x['backend_exact_bytes_verified']
            x['backend_exact_bytes_verified']=backend['matches_reported_identity'] and backend['stable_during_read']
            x['prior_backend_verification_gap']=x['backend_verification_gap'];x['backend_verification_gap']=None
            x['supplement_byte_verification']=backend;count+=1
    check('exactly one standalone Intent backend promoted to byte-verified',count,1)
    jl('encoder_deployment_ledger.jsonl',encoders)
    traces=copy.deepcopy(rows(PRIOR/'cross_ir_trace.jsonl'))
    for x in traces:
        if x['ledger_id']=='T1-retrieval-candidate':
            x['prior_original_run_id']=x['run_id'];x['run_id']=identity
            x['identity_evidence']='workstreams/t1_integrity_joins.json'
    check('no cross-IR status promoted by checkpoint hashing',
          [x['status'] for x in traces],[x['status'] for x in rows(PRIOR/'cross_ir_trace.jsonl')])
    jl('cross_ir_trace.jsonl',traces)

    gaps=rows(PRIOR/'missing_evidence.jsonl')
    updates={i:{'prior_gap_id':i,'prior_gap':x,'status':'unchanged','changes':[],
                'remaining':x.get('reason'),'reason_not_closed':'No new closing evidence in this bounded supplement'} for i,x in enumerate(gaps,1)}
    for x in rows(BASE/'workstreams/t1_gap_status.jsonl'):
        i=x['prior_missing_entry'];updates[i].update(status='partially_closed' if x['status']=='partial' else x['status'],
                                                    changes=[x],remaining=x.get('remaining'),reason_not_closed=x.get('minimal_remedy'))
    for x in rows(BASE/'workstreams/t2_gap_updates.jsonl'):
        i=x['old_gap_id'];status='partially_closed' if x['status']=='partial' else x['status']
        if status=='unresolved_in_this_workstream':status='unchanged'
        updates[i].update(status=status,changes=[x],remaining=x.get('remaining',x.get('scope')),reason_not_closed=x.get('minimal_remedy'))
        for related in x.get('related_gap_ids',[]):
            updates[related].update(status='partially_closed',changes=[x],remaining=x.get('remaining'),reason_not_closed=x.get('minimal_remedy'))
    historic=load(BASE/'workstreams/historical_gap_updates.json')
    for i,x in zip([20,19,21,17],historic):
        updates[i].update(status='unchanged' if i==17 else 'partially_closed',changes=[x],remaining=x['remaining'],reason_not_closed=x['remaining'])
    for x in load(BASE/'workstreams/integration_gap_updates.json')['updates']:
        i=x['prior_gap'];updates[i].update(status=x['status'],changes=[x],remaining=x.get('remaining',x.get('does_not_resolve')),
                                         reason_not_closed=None if x['status']=='closed' else x.get('remaining'))
    for name in ['git_reuse_recovery.json','git_population_leads.json']:
        x=load(BASE/'workstreams'/name)['gap_update'];i=x['prior_gap']
        updates[i].update(status=x['status'],changes=[x],remaining=x.get('remaining'),
                          reason_not_closed=None if x['status']=='closed' else x.get('remaining'))
    # The T1 archive and Intent backend are not the T2/T4 Security/Source384 assets.
    updates[12].update(status='unchanged',reason_not_closed='T2/T3/T4/X1 exact checkpoint/archive bytes remain unverified; unrelated T1/Intent asset verification does not close this field.')
    jl('gap_status.jsonl',list(updates.values()))
    gap_counts=dict(Counter(x['status'] for x in updates.values()))
    lines=['# Remaining evidence after this supplement','', 'Earlier audit files remain unchanged. Closed status applies to the named evidence field, not complete experiment authenticity or semantic qualification.','', '| Prior gap | Field | Status | Remaining limitation |','|---:|---|---|---|']
    for i,x in updates.items():
        label=x['prior_gap'].get('field',x['prior_gap'].get('item'))
        remaining=x.get('remaining')
        if isinstance(remaining,list):remaining='; '.join(remaining)
        lines.append(f'| {i} | {label} | {x["status"]} | {str(remaining or "See scope in gap_status.jsonl").replace("|","/")} |')
    write('remaining_evidence.md','\n'.join(lines)+'\n')

    result=[]
    for r in runs:
        if r['projection_worker']=='historical':continue
        result.append({'study':r['study_id'],'audit_id':r['ledger_id'],'run_id':r['original_run_id'],
                       'profile':r['requested_treatment'] or r['profile'],'invoked':r['invoked'],'reward':r['original_reward'],
                       'reported_total_tokens':r['reported_tokens'].get('total_tokens'),
                       'legacy_native_usage_complete':r['native_usage_complete'],
                       'new_usage_completeness_inference':False})
    table('results.csv',result,list(result[0]))

    input_rows=[r for p in sorted((BASE/'workstreams').glob('*_inputs.jsonl')) for r in rows(p)]
    unique={}
    for r in input_rows:
        key=(r['path'],r['sha256'])
        if key not in unique:unique[key]={**r,'workers':[]}
        unique[key]['workers'].append(r['worker'])
    jl('artifacts.jsonl',sorted(unique.values(),key=lambda x:x['path']))
    git_sources=load(BASE/'workstreams/git_reuse_inputs.json')['records']+load(BASE/'workstreams/git_population_inputs.json')
    js('git_artifacts.json',{'sources':git_sources,'content_exported':False,'git_checkout_or_source_mutation':False})
    t1=load(BASE/'workstreams/t1_integrity_joins.json');t2=load(BASE/'workstreams/t2_reconciliation.json')
    historical=load(BASE/'workstreams/historical_findings.json')
    check('T1 subtotal unchanged',t1['known_nine_trial_subtotal_unchanged'],2523452)
    check('T1 missing usage retained',t1['missing_usage_trials'],3)
    check('T2 receipt bindings',t2['all_checked_bindings_match'],True)
    check('historical checks',historical['all_checks_passed'],True)
    check('T4 native original receipt corroboration',load(BASE/'audit/t4_native_report_join.json')['matches'],True)
    member=load(BASE/'audit/runtime_member_verification.json')
    check('runtime declared files verified',member['verified_files'],member['declared_files'])
    check('runtime member verification',member['all_declared_file_bytes_verified'],True)
    check('large asset identities',assets['all_matched'],True)
    check('selected source pins',load(BASE/'runtime_source_forest.json')['all_selected_pin_joins_match'],True)
    reuse=load(BASE/'workstreams/git_reuse_recovery.json')
    ns011=next(r for r in reuse['records'] if r['task_id']=='NS-011')
    check('original adverse reuse retained',[ns011['all_attempted_false_reuse'],ns011['all_attempted']],[1,26])
    check('later reuse removed',reuse['records'][0]['reuse_admitted'],False)
    check('planned units not substituted as executions',load(BASE/'workstreams/git_population_leads.json')['final_plan']['first_final_attempt_started'],False)
    cohort=load(BASE/'workstreams/historical_usage_joins.json')['cohorts']
    for name,expected in [('requests-cold-v1',108981),('requests-cold-v2',243255)]:check(name,cohort[name]['usage']['total_tokens'],expected)
    js('checks.json',{'passed':all(x['passed'] for x in checks),'checks':checks,
                      'arithmetic_or_consistency_only':True,'provider_authenticity_established':False})
    assert all(x['passed'] for x in checks),'Evidence discrepancy: do not silently overwrite'
    summary={'schema':'paper-closeout-supplement-summary@1','prior_audit':str(PRIOR),
             'run_rows':len(runs),'benchmark_rows':len(result),'identified_invoked_benchmark_trials':sum(x['invoked'] is True and x['run_id'] is not None for x in result),
             'new_benchmark_trials':0,'new_token_charges':0,'session_or_call_observation_rows':len(sessions),
             'original_text_json_files':len(unique),'text_json_bytes':sum(x['bytes'] for x in unique.values()),
             'historical_git_blobs':len(git_sources),'historical_git_blob_bytes':sum(x.get('bytes',0) for x in git_sources),
             'original_provider_receipts':23,'runtime_files_verified':member['verified_files'],
             'stream_asset_bytes_hashed':assets['stream_bytes'],'archive_member_regular_bytes_hashed':member['regular_member_bytes'],
             'gap_status_counts':gap_counts,'assembly_checks':len(checks),'passed':True,
             'historical_workstream_checks':historical['checks'] if isinstance(historical['checks'],int) else len(historical['checks']),
             'no_new_runtime_execution':True}
    js('summary.json',summary)
    print(json.dumps(summary))

if __name__=='__main__':
    os.umask(0o077);main()
