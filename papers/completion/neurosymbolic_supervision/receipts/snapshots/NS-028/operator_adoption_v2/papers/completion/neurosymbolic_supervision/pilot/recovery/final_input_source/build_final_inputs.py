"""Stage saved public contexts, then bind an explicit native-format final freeze.

Both commands are source/metadata preparation only. Effects remain behind the
separate root operator admission in batch_control.checked. Existing outputs are
never overwritten. No oracle payload is opened and no context is recomputed.
"""
import sys
sys.dont_write_bytecode = True
import argparse, hashlib, json, os, stat
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE/'final_service'))
import adapter as A, batch_control as B, pilot_gateway as G, http_proposer as F
import native_final_gate as N

def write(p, value): A.write(p, A.canonical(value))
def bind(p): return {'path':str(p), 'sha256':A.sha(p)}
def read_registry(path, expected):
    """Registry inventories exceed 1 MiB; other metadata keeps its smaller cap."""
    p=Path(path);limit=16*1024*1024
    B.require(p.is_absolute() and p.resolve()==p and B.sha_ok(expected),'canonical registry required')
    fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
    try:
        s=os.fstat(fd)
        B.require(stat.S_ISREG(s.st_mode) and s.st_size<=limit and
                  s.st_mode&0o077==0 and p.parent.stat().st_mode&0o077==0,'private bounded registry required')
        with os.fdopen(fd,'rb',closefd=False) as f: raw=f.read(limit+1)
    finally: os.close(fd)
    B.require(len(raw)<=limit and hashlib.sha256(raw).hexdigest()==expected,'registry bytes changed')
    value=json.loads(raw)
    B.require(value.get('schema') in ('ns-historical-private-host-registry/v1',
              'ns-historical-private-final-registry/v1'),'historical registry schema required')
    return value
def packet(path, expected):
    p = Path(path)
    B.require(p.is_absolute() and p.resolve()==p and B.sha_ok(expected),'canonical context packet required')
    fd = os.open(p, os.O_RDONLY|os.O_NOFOLLOW)
    try:
        s = os.fstat(fd)
        B.require(stat.S_ISREG(s.st_mode) and s.st_size<=16*1024*1024 and
                  s.st_mode&0o077==0 and p.parent.stat().st_mode&0o077==0,'private bounded context required')
        with os.fdopen(fd,'rb',closefd=False) as f: raw=f.read(16*1024*1024+1)
    finally: os.close(fd)
    B.require(len(raw)<=16*1024*1024 and hashlib.sha256(raw).hexdigest()==expected,'context bytes changed')
    value=json.loads(raw)
    B.require(value.get('schema')=='ns-pilot-AB-prepared-public-context/v1','qualified component packet required')
    return value

def fresh(path):
    B.require(path.is_absolute() and path.resolve()==path and not path.exists(),'fresh canonical output required')
    path.mkdir(mode=0o700)

def stage(args):
    original=read_registry(args.registry,args.registry_sha256)
    B.require(original['schema']=='ns-historical-private-host-registry/v1','original historical registry required')
    for path, expected in original['source_bindings'].items():
        B.require(A.sha(path)==expected,'original registry provenance changed')
    units={k:dict(v) for k,v in original['units'].items() if v['split']=='final'}
    B.require(set(units)==set(B.UNITS),'exact original eight final families required')
    prep=B.read_bound(args.context_manifest,args.context_manifest_sha256)
    B.require(prep.get('schema')=='ns-final-native-context-preparation-manifest/v1' and
              set(prep['units'])==set(B.UNITS),'all eight actual saved preparations required')
    for unit,m in units.items():
        b=prep['units'][unit];v=packet(b['path'],b['sha256'])
        B.require(set(b)=={'path','sha256'} and v['unit_id']==unit and
                  v['source_archive_sha256']==m['source_archive']['sha256'],'saved preparation source differs')
        B.require(set(v['bindings'])==set(B.ARMS) and set(v['request_sha256'])==set(B.ARMS),'paired context missing')
        m['public_context_preparation']=b
        m['historical_scorer_profile']=m['scorer_profile']
        B.require(m['historical_scorer_profile']=={**A.SCORER_PROFILE,'pids':32},'historical scorer profile differs')
        m['scorer_profile']=dict(A.SCORER_PROFILE)
        m['final_scorer_amendment']={'scope':'both final arms and all eight final families before outcomes','reason':'Original unchanged more-itertools public baseline requires50/100 threads;32PID compatibility failed; restore original128PID baseline ceiling. Provider/native preparation remain32PID.','historical_pids':32,'final_scorer_pids':128,'source_tests_population_unchanged':True}
    old=B.read_bound(args.original_plan,B.ORIGINAL_PLAN_SHA)
    selected=[u for u in old['units'] if u['arm'] in B.ARMS and u['cache']=='local_cold']
    B.require(len(old['units'])==192 and len(selected)==32,'original 192-to-32 order filter changed')
    B.require({(u['task_id'],u['arm'],u['repetition'])for u in selected}==
              {(u,a,r)for u in B.UNITS for a in B.ARMS for r in B.REPETITIONS},'original final identities changed')
    fresh(args.destination)
    registry={'schema':'ns-historical-private-final-registry/v1','pilot_execution_admitted':False,
              'final_execution_admitted':True,'source_bindings':G.source_binding(),'units':units,
              'predecessor_registry':bind(args.registry),'context_preparation_manifest':bind(args.context_manifest),
              'authority_note':'Typed final preparation registry; grants require separate root final admission.'}
    rp=args.destination/'final_registry.private.json';write(rp,registry)
    profiles, bindings={},{}
    for unit,m in units.items():
        target=args.destination/unit;A.prepare_admitted_unit(target,m)
        profiles[unit],bindings[unit]={},{}
        for arm in B.ARMS:
            request,binding=F.build_request(target,m,arm=arm)
            B.require(len(F.canon(request))<=65536,'request exceeds unchanged context cap')
            bindings[unit][arm]=binding;profiles[unit][arm]=G.profile_for(m,arm)
            write(target/('request_binding_'+arm+'.private.json'),binding)
    cells=[B.cell_id(u['task_id'],u['arm'],u['cache'],u['repetition'])for u in selected]
    common={'schema':'ns-final-AB-context-model-amendment/v1','record_kind':'final',
            'response_payload_protocol':'http-json-edits-v2','runtime_protocol':'http-json-edits-runtime-v3',
            'arms':list(B.ARMS),'cache':'local_cold','repetitions':list(B.REPETITIONS),'profiles':profiles,
            'original_plan_binding':bind(args.original_plan),'planned_cells':cells,
            'order_policy':'Exact original192 order filtered to A/B and local_cold; original repetition IDs retained.',
            'independent_families':8,'nested_repetitions_per_family_arm':2,'removed_factor_cells':160,
            'unrecruited_original_final_families':8,'reuse_admitted':False,'publication_comparison_admitted':False,
            'context_preparation_manifest':bind(args.context_manifest),'provider_calls':0,'scorer_calls':0,
            'scorer_resource_amendment':{'all_final_families_and_arms':True,'historical_pids':32,'final_scorer_pids':128,'provider_pids':32,'native_preparation_pids':32,'reason':'Original public more-itertools concurrency tests require up to100 threads; unchanged original128PID baseline restored prospectively.'},
            'context_preparation_costs_charged_once':True,'cold_scorer_is_fresh_per_cell':True,
            'final_dispatch_authorized':False}
    cp=args.destination/'common_amendment.private.json';write(cp,common)
    report={'schema':'ns-final-AB-prepared-inputs/v1','source_bindings':G.source_binding(),
            'package_sha256':A.digest(G.source_binding()),'registry':bind(rp),'common_amendment':bind(cp),
            'original_plan_binding':bind(args.original_plan),'profiles':profiles,'bindings':bindings,
            'ordered_units':selected,'planned_cells':cells,'provider_calls':0,'scorer_calls':0,
            'oracle_payloads_read':False,'new_native_context_computations':0}
    write(args.destination/'prepared_inputs.private.json',report)
    return args.destination/'prepared_inputs.private.json'

def freeze(args):
    prepared=B.read_bound(args.prepared_inputs,args.prepared_inputs_sha256)
    B.require(prepared.get('schema')=='ns-final-AB-prepared-inputs/v1' and
              prepared['source_bindings']==G.source_binding(),'prepared source package changed')
    authority=B.read_bound(args.freeze_authority,args.freeze_authority_sha256)
    B.require(authority.get('schema')=='ns028-root-final-freeze-authority/v1' and
              authority.get('approved') is True and authority.get('final_outcomes_observed')==0,
              'explicit pre-outcome root freeze authority required')
    for key in ('prepared_inputs_sha256','pilot_analysis_binding','analysis_policy_binding',
                'native_harness_execution','native_pin_files','native_head','native_harness_source_sha256'):
        B.require(key in authority,'freeze authority field missing: '+key)
    B.require(authority['prepared_inputs_sha256']==args.prepared_inputs_sha256,'authority targets different prepared inputs')
    B.require(authority.get('resource_reservation_obtained') is True and
              isinstance(authority.get('resource_reservation_evidence'),dict),'actual bounded resource reservation evidence required')
    lease=N.resource_reservation(authority['resource_reservation_evidence'])
    B.require(lease['held'],'root allocation not held')
    analysis=B.read_bound(
        authority['pilot_analysis_binding']['path'],authority['pilot_analysis_binding']['sha256'])
    B.require(analysis.get('complete') is True and analysis.get('terminal_cells')==24,'complete developmental pilot required')
    policy=B.read_bound(authority['analysis_policy_binding']['path'],authority['analysis_policy_binding']['sha256'])
    B.require(policy.get('schema')=='ns028-final-AB-analysis-policy/v1' and
              policy.get('frozen_before_final_outcomes') is True,'prospective final analysis policy required')
    pin_files=authority['native_pin_files']
    for label in pin_files: A.safe_rel(label)
    pins=N.current_digests(pin_files)
    B.require(authority.get('immutable_pins')==pins,'actual current source/profile bytes differ')
    families=dict(zip(B.UNITS,B.FAMILIES));registry=read_registry(prepared['registry']['path'],prepared['registry']['sha256'])
    useful={}
    for arm in B.ARMS:
        count=sum(1 for row in analysis['rows'] if row['arm']==arm and row['useful_completion'] is True)
        B.require(count>0,'retained arm lacks actual useful cold witness')
        useful[arm]={'has_useful_path':True,'independently_scored':True,'useful_pilot_cells':count,
                     'pilot_analysis_sha256':authority['pilot_analysis_binding']['sha256']}
    shared={'package_sha256':prepared['package_sha256'],'registry_sha256':prepared['registry']['sha256'],
            'planned_cells':prepared['planned_cells'],'native_head':authority['native_head'],
            'native_harness_source_sha256':authority['native_harness_source_sha256'],
            'native_runtime_profile_binding':authority['native_runtime_profile_binding']}
    final={'schema':'paper-ns-final-experiment-freeze/v1','frozen':True,'final_dispatch_authorized':True,
           'first_final_attempt_started':False,'immutable_pins':pins,'retained_executable_arms':list(B.ARMS),
           'arm_useful_paths':useful,'served_model_identity':{'served_model':'grok-4.6',
               'underlying_served_revision_known':False,'binding':'exact alias; per-call actual served identity retained'},
           'resource_reservation_obtained':True,'resource_reservation_evidence':authority['resource_reservation_evidence'],
           'developmental_task_ids':authority['developmental_task_ids'],
           'developmental_family_ids':authority['developmental_family_ids'],
           'final_task_ids':list(B.UNITS),'final_family_ids':list(B.FAMILIES),
           'removed_arms':{a:{'claim_update':'No '+a+' comparative routing, reuse, lifecycle or publication claim; unsupported mechanism removed before final outcomes.'}
                           for a in B.HISTORICAL_ARMS if a not in B.ARMS},
           'pilot_complete':True,'pilot_analysis_sha256':authority['pilot_analysis_binding']['sha256'],
           'analysis_policy_sha256':authority['analysis_policy_binding']['sha256'],
           'native_harness_execution':authority['native_harness_execution'],
           'root_freeze_authority':bind(args.freeze_authority),**shared}
    final['freeze_sha256']=B.digest(final)
    fresh(args.destination);fp=args.destination/'final_experiment_freeze.json';write(fp,final)
    manifest={'schema':'paper-ns-final-run-manifest/v1','freeze_binding':bind(fp),
              'original_plan_binding':prepared['original_plan_binding'],'units':prepared['ordered_units'],
              'independent_family_count':8,'unrecruited_original_final_families':8,
              'planned_cells':32,'removed_factor_cells':160,'final_dispatch_authorized':False,
              'requires_separate_operator_admission':True}
    mp=args.destination/'final_run_manifest.json';write(mp,manifest)
    batch={'schema':'ns-historical-final-AB-cold-batch/v1','scope':'heldout_AB_cold_final_only',
           'final_admitted':False,'requires_separate_operator_admission':True,'enabled_arms':list(B.ARMS),
           'enabled_cache':'local_cold','repetitions':list(B.REPETITIONS),'max_provider_calls':32,
           'max_scorer_calls':32,'candidate_review_required':True,'retries':0,'fallback_allowed':False,
           'units':{u:{'split':'final','family_id':families[u],'manifest_sha256':A.digest(m),
                     'arms':{a:{'request_binding_sha256':A.digest(prepared['bindings'][u][a]),
                                'context_binding_sha256':prepared['bindings'][u][a]['context_binding_sha256'],
                                'profile_sha256':A.digest(prepared['profiles'][u][a])}for a in B.ARMS}}
                    for u,m in registry['units'].items()},
           'enabled_cells':prepared['planned_cells'],'original_plan_binding':prepared['original_plan_binding'],
           'removed_old_units':160,'unrecruited_original_final_families':8,
           'retained_claims':['A_vs_B_native_semantic_context'],'reuse_admitted':False,
           'publication_comparison_admitted':False,'private_root':str(args.private_root),'queue_root':str(args.queue_root),
           'amendment_source_sha256':prepared['common_amendment']['sha256'],'native_pin_files':pin_files,
           'freeze_binding':bind(fp),'pilot_analysis_binding':authority['pilot_analysis_binding'],
           'analysis_policy_binding':authority['analysis_policy_binding'],**shared}
    B.validate(batch);bp=args.destination/'batch.private.json';write(bp,batch);templates={}
    for row,cid in zip(prepared['ordered_units'],prepared['planned_cells']):
        u,a,r=row['task_id'],row['arm'],row['repetition'];m=registry['units'][u]
        value={'schema':'ns-historical-final-provider-amendment/v1','scope':'heldout_AB_cold_final_only',
               'unit_id':u,'provider':'grok','model':'grok-4.6','expected_served_aliases':['grok-4.6'],
               'fallback_allowed':False,'max_provider_calls':1,'arm':a,'cache':'local_cold','repetition':r,
               'transport':F.PROFILE['transport'],'manifest_sha256':A.digest(m),
               'prompt_sha256':hashlib.sha256(m['prompt'].encode()).hexdigest(),'profile':prepared['profiles'][u][a],
               'request_binding':prepared['bindings'][u][a],
               'batch_binding':{**bind(bp),'cell_id':cid,'operator_admission_path':'PENDING_ROOT_REVIEW',
                                'operator_admission_sha256':'PENDING_ROOT_REVIEW'}}
        p=args.destination/(cid+'.amendment.pending.json');write(p,value)
        templates[cid]={**bind(p),'cell_id':cid,'unit':u,'arm':a,'repetition':r}
    report={'schema':'ns-final-AB-staged-inputs/v1','source_bindings':G.source_binding(),
            'registry':prepared['registry'],'prepared_inputs':bind(args.prepared_inputs),'batch':bind(bp),
            'common_amendment':prepared['common_amendment'],'freeze':bind(fp),'final_manifest':bind(mp),
            'amendment_templates':templates,'planned_cells':32,'original_planned_cells':192,
            'operator_admission_required':True,'grants_created':0,'provider_calls':0,'scorer_calls':0,
            'oracle_payloads_read':False}
    write(args.destination/'staged_inputs.private.json',report)
    return args.destination/'staged_inputs.private.json'

def main():
    ap=argparse.ArgumentParser(description=__doc__);subs=ap.add_subparsers(dest='command',required=True)
    s=subs.add_parser('stage')
    for name in ('registry','context-manifest','original-plan','destination'): s.add_argument('--'+name,type=Path,required=True)
    for name in ('registry-sha256','context-manifest-sha256'): s.add_argument('--'+name,required=True)
    f=subs.add_parser('freeze')
    for name in ('prepared-inputs','freeze-authority','destination','private-root','queue-root'): f.add_argument('--'+name,type=Path,required=True)
    for name in ('prepared-inputs-sha256','freeze-authority-sha256'): f.add_argument('--'+name,required=True)
    args=ap.parse_args();os.umask(0o077);out=stage(args) if args.command=='stage' else freeze(args)
    print(json.dumps({**bind(out),'provider_calls':0,'scorer_calls':0,'grants_created':0}))

if __name__=='__main__': main()
