"""Verify this unsigned scalar component and reproduce its counts/table joins.

Standard-library file reads only; never imports retained qualification sources.
"""
import argparse, hashlib, json
from pathlib import Path

def sha(raw): return hashlib.sha256(raw).hexdigest()
def read(root, name): return (root/name).read_bytes()
def load(root, name): return json.loads(read(root,name))
def rows(root, name): return [json.loads(x) for x in read(root,name).splitlines()]
def require(ok, message):
    if not ok: raise ValueError(message)
def replay(root):
    manifest=load(root,'manifest.json')
    require(manifest['schema']=='ns020-public-boundary-component/v1' and manifest['unsigned_derivatives'] is True, 'Component scope differs')
    for name,spec in manifest['members'].items():
        path=Path(name)
        require(not path.is_absolute() and '..' not in path.parts, 'Unsafe component path')
        raw=read(root,name);require(sha(raw)==spec['sha256'] and len(raw)==spec['bytes'],'Changed component member: '+name)
    count={};maps={}
    for task,name in [('NS-007','context_results'),('NS-008','provider_gate_receipts'),('NS-009','logic_receipts'),('NS-011','reuse_mutation_results'),('NS-012','sealer_results')]:
        rr=rows(root,f'data/{task}/{name}.jsonl');count[task]=len(rr);maps[task]={r['case_id']:r for r in rr}
        require(len(maps[task])==len(rr),'Duplicate qualification case')
    require(count=={'NS-007':26,'NS-008':20,'NS-009':32,'NS-011':26,'NS-012':27},'Fixed historical case counts differ')
    require(all(r['source_claim_admitted'] is False for r in maps['NS-009'].values()),'Translation source-proof overclaim')
    false=[r for r in maps['NS-011'].values() if r['false_reuse'] is True]
    require(len(false)==1 and false[0]['case_id']=='stale_key_presented_without_rebind' and false[0]['unsound_reuse'] is True,'All-attempt false reuse missing')
    inv=load(root,'data/NS-027/invocations.json')['invocations']
    require(len(inv)==4 and [r['completed_case_rows']for r in inv]==[0,15,16,16] and [r['case_attempts_observed']for r in inv]==[0,16,16,16] and [r['exit_code']for r in inv]==[1,1,0,0],'Failed/partial invocation accounting differs')
    require(sum(r['case_attempts_observed']for r in inv)==48,'All correction attempts required')
    for n,expected in [(2,15),(3,16),(4,16)]:
        require(len(rows(root,f'data/NS-027/v{n}_outcomes.jsonl'))==expected,'Correction outcomes missing')
    baselines=load(root,'data/NS-027/full_cold_baselines.json')['runs']
    require([r['run_id']for r in baselines]==['operator-repair-qualification-v3','operator-repair-qualification-v4'],'Corrected snapshot epochs differ')
    require(all(r['collected']==r['passed']==r['expected_count']==34 and r['reuse_credit'] is False and r['pilot_or_final_admission'] is False and r['provider_calls']==r['hidden_scorer_calls']==0 for r in baselines),'Full public cold scope differs')
    witness=load(root,'boundary_witnesses.json');require(witness['preparation_only'] is True and witness['final_claim_reconciliation_complete'] is False and witness['native_completion_claimed'] is False,'No final completion authority')
    for table_id,task in [('B-provider','NS-008'),('B-translation','NS-009')]:
        item=next(x for x in witness['table18_rows']if x['id']==table_id)
        for polarity in ('safe_rejection','valid_progress'):
            for case in item[polarity]['cases']:
                actual=maps[task][case['case_id']]
                require(all(actual[k]==v for k,v in case.items()),'Table case differs from scalar record')
    item=next(x for x in witness['table18_rows']if x['id']=='B-reuse')
    require(all(false[0][k]==v for k,v in item['safe_rejection']['historical_counterexample'][0].items()),'Table false reuse differs')
    claims=load(root,'claim_index.json')
    require(len(claims['claims'])==32 and len({r['original_claim_id']for r in claims['claims']})==32 and claims['all_final_claims_resolved'] is False and all(r['empirical_final_outcome']is None for r in claims['claims']),'Original claims or deferred final scope changed')
    require(all(x['empirical_final_rows']==[] for x in witness['final_empirical_boundary_joins']),'Final observations cannot enter this component')
    return {'schema':'ns020-public-boundary-count-replay/v1','historical_rows':count,'NS011_false_reuse':{'all_attempts':26,'observed':1,'selected_25_not_substituted':True},'NS027':{'invocations':4,'case_attempts':48,'completed_rows':47,'full_public_baselines':2,'tests_per_baseline':34,'reuse_credit':False},'NS012_recovery_records':len(rows(root,'data/NS-012/recovery_receipts.jsonl')),'original_claims':32,'table_rows':len(witness['table18_rows']),'final_outcome_rows':0,'native_qualification_reexecuted':False,'provider_calls':0,'scorer_calls':0,'signature_authentication_of_derivatives':False}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=Path(__file__).resolve().parent);a=p.parse_args()
    result=replay(a.root.resolve());require(result==load(a.root,'expected_counts.json'),'Expected replay differs')
    print(json.dumps(result,sort_keys=True,indent=2))
if __name__=='__main__':main()
