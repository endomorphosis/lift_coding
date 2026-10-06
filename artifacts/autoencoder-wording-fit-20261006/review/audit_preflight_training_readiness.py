"""Audit completed saved preflights and issue scoped fit readiness; no models."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

ROOT=Path('/home/barberb/lift_coding');P=ROOT/'external/ipfs_datasets'
R=P/'workspace/test-logs/decoder-normative-wording-r2-20261006'
OUT=ROOT/'artifacts/autoencoder-wording-fit-20261006/review'
RVIEW=R/'review';checks=0;artifacts={}


def check(value,label):
    global checks
    if not value:raise AssertionError(label)
    checks+=1


def raw(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()
def digest(value):return hashlib.sha256(raw(value)).hexdigest()
def text_sha(value):return hashlib.sha256(value.encode()).hexdigest()


def bind(path,wanted=None,size=None):
    path=Path(path).resolve();h=hashlib.sha256();count=0
    with path.open('rb')as stream:
        for block in iter(lambda:stream.read(1048576),b''):h.update(block);count+=len(block)
    record=dict(sha256=h.hexdigest(),bytes=count)
    if wanted is not None:check(record['sha256']==wanted,'artifact SHA:'+str(path))
    if size is not None:check(count==size,'artifact bytes:'+str(path))
    artifacts[str(path)]=record;return record


def load(path):bind(path);return json.loads(Path(path).read_bytes())
def self_hash(value,key):check(value[key]==digest({k:v for k,v in value.items()if k!=key}),'payload digest:'+key)
def reference(ref):bind(ref['path'],ref['sha256'],ref.get('bytes'));return json.loads(Path(ref['path']).read_bytes())


manifest=load(R/'training-manifest.json');plan=load(R/'training-plan.json')
bind(R/'training-plan.json',manifest['plan_sha256'])
check(plan['input_sha256']==manifest['inputs'],'fixed all training input bindings')
for path,wanted in manifest['inputs'].items():bind(path,wanted)
for path,wanted in manifest['producer_pins'].items():bind(path,wanted)
for relative,wanted in manifest['extensions'].items():bind(R/'experiment-source'/relative,wanted)
check(plan['arms']==[dict(name='normative-wording-zero',weight=0.),dict(name='normative-wording-ce',weight=.05)],'fixed matched0/.05 objective')
for key,expected in dict(context_tokens=512,max_target_tokens=512,temperature=0,learning_rate=.0001,seed=1729,
    epochs_per_stage=10,optimizer_steps_per_fit=170,row_presentations=1220,valid_target_token_presentations=112920,
    source_value_presentations=12800,paraphrase_diagnostic_presentations_per_fit=1020,full_vocabulary_size=32,
    cpu_slots_per_width=1,memory_mb_per_width=1536,storage_bytes_per_width=400000000,max_seconds_per_fit=180,
    max_seconds_entire_width=900,selection_unchanged=True,zero_arm_exact_m2_zero_replay=True,
    previous_development_targets_used_for_training=False,package_aliases_modified=False,encoder_executed=False,
    preprocessing_refitted=False,legal_ir_evaluate_provers=False,metric_disk_cache_used=False).items():
    check(type(plan[key])is type(expected)and plan[key]==expected,'training fixed field:'+key)
check(manifest['prospective_development_references_bound_in_training']is False,'future refs not bound in TRAIN')
native_audit=load(OUT/'native_preparation_audit.json')
check(native_audit['passed']is True and native_audit['findings']==[]and native_audit['checks']==328365,'actualnative preparation clean audited')
paths=manifest['normative_preparation_artifacts'];clause_refs=load(paths['clause-training-references.json'])
sources=load(paths['prior-source-inventories.json'])['prospective_development_sources']
check(len(sources)==60 and all(set(r)=={'id','source_text'}for r in sources),'future source-only exclusions full60')
bytext={r['source_text']:r for r in clause_refs};sealed_draws=load(manifest['independent_inputs']['auxiliary_schedule'])
check(len(sealed_draws)==170,'sealed complete170 draws')
parent_tensors={384:'6a527b568c1ec834fc6704a9d12a17532840076432a93dc1390c59c92d483ec3',
                768:'8900d69fb00c17a54b7d3cbe6fbd2c24651b614839ad57c588d0f04dc308fada'}
audits={}
for width in(384,768):
    attempt=R/f'preflight-{width}-r1';data=attempt/'results'
    outer=load(R/f'preflight-{width}-r1-guardian-exit.json');child=load(attempt/'child-exit.json');final=load(attempt/'resources-final.json')
    check(outer['returncode']==child['returncode']==0 and child['leader_reaped']is True,'completed guarded preflight width'+str(width))
    check(final['status']==final['record']['status']=='released'and final['record']['artifacts_durable_asserted']is True
          and final['record']['attempt_exceeded_reservation']is False,'owned preflight durable release width'+str(width))
    summary=load(data/'summary.json');check(summary['complete']is True and summary['phase']=='preflight'
          and summary['dimension']==width and len(summary['runs'])==2,'both preflight arms complete')
    for key in('admitted','qualified','encoder_executed','lake_executed','helper_defaults_modified','package_aliases_modified',
               'checkpoint_promoted','convergence_proven','native_validation_executed'):
        check(summary[key]is False,'preflight retains diagnostic scope:'+key)
    for path,wanted in summary['source_dependencies'].items():bind(path,wanted)
    for path in data.rglob('*'):
        if path.is_file():bind(path)
    check(not list(data.rglob('*state.json'))and not list(data.rglob('training.json')),'preflight emits no optimizerfit/checkpoint states')
    bank=load(data/'paraphrase-bank.json');self_hash(bank,'bank_sha256')
    inventory=load(data/'source-inventory.json');self_hash(inventory,'payload_sha256')
    check(bank['source_inventory_sha256']==inventory['payload_sha256']and bank['prospective_reference_labels_supplied']is False,
          'independently prepared source inventory and futurelabel barrier')
    check(inventory['prior_sources_by_dataset']['prospective_development_sources']==sources,'complete future source exclusions in helper envelope')
    check(bank['dimension']==width and len(bank['rows'])==bank['selected_rows']==180,'full180 bank')
    native=load(paths[f'production-{width}.json']);vectors={r['source_sha256']:r['vector']for r in native['vectors']}
    for row in bank['rows']:
        ref=bytext[row['source_text']]
        check(row['id']=='clause:'+row['source_sha256']and row['source_sha256']==text_sha(row['source_text']),'bank literal identity')
        check(row['target']==ref['target']['rules'][0]and row['template']==ref['template']
              and row['parent_id']==ref['parent_paragraph_id']and row['derivation']==ref['derivations'][0], 'complete TRAIN rule/provenance unchanged')
        check(row['input']==vectors[row['source_sha256']]and row['input_sha256']==digest(row['input']),'real native TRAIN vector bank join')
        check(row['modality']==row['target']['modality']and row['modality_token_id']=={'O':4,'P':5,'F':3}[row['modality']], 'full32V modality target')
    check([r['id']for r in bank['rows']]==sorted({r['id']for r in bank['rows']}),'fixed sorted bank IDs')
    declared=load(data/'predeclared-auxiliary-schedule.json')
    check(declared['draws']==sealed_draws and declared['bank_sha256']==bank['bank_sha256']
          and declared['independent_inputs_verified']is True,'predeclared actual draws match independent sealed schedule')
    strata=[tuple(v.split(':',1))for v in plan['paraphrase_auxiliary_strata']];orders=[]
    for stratum in strata:
        indices=[i for i,row in enumerate(bank['rows'])if(row['modality'],row['template'])==stratum]
        check(len(indices)==30,'full30 rows in every fixed cell')
        orders.append(sorted(indices,key=lambda i:digest([1729,stratum,bank['rows'][i]['source_sha256'],bank['rows'][i]['id']])))
    check(orders==declared['orders'],'independently recomputed hashordered streams')
    exposures=Counter()
    for step,draw in enumerate(declared['draws']):
        indices=[order[step%30]for order in orders];selected=[bank['rows'][i]for i in indices]
        check(draw==dict(step=step,indices=indices,row_ids=[r['id']for r in selected],source_sha256=[r['source_sha256']for r in selected],
                        strata=[[r['modality'],r['template']]for r in selected],target_token_ids=[r['modality_token_id']for r in selected]),
              'independent exact sixrow draw step'+str(step))
        exposures.update(draw['row_ids'])
    check(dict(exposures)==declared['per_source_exposures']and Counter(exposures.values())=={6:120,5:60}
          and sum(exposures.values())==1020 and declared['per_modality_presentations']=={'O':340,'P':340,'F':340}, 'complete exposure budget no samplingshortcut')
    parent_baseline=load(manifest['baseline_summaries'][str(width)]);baseline=reference(parent_baseline['training_ref'])
    primary=load(manifest['independent_inputs']['primary_schedules'][str(width)])
    check(len(primary)==len(baseline['committed_updates'])==170,'complete originalstream baseline')
    for row,update in zip(primary,baseline['committed_updates']):
        check(row['decoder_ids']==update['decoder_row_ids']and row['count_ids']==update['count_row_ids'],'original decoder/count batches preserved')
        if width==384:check(row['original_auxiliary_source_modality']==update['auxiliary_source_modality']['receipt'],'original384 auxiliary preserved')
    preparation=load(data/'preprocessing.json');contexts=load(data/'source-contexts.json');training_rows=load(data/'training-rows.json')
    observations=[]
    for run in summary['runs']:
        check(run['arm']in('normative-wording-zero','normative-wording-ce')and run['dimension']==width,'explicit arm width')
        parity=run['initial_parity'];original=reference(parity['parent_prediction_ref']);restored=reference(parity['restored_prediction_ref'])
        check(parity['predictions_equal']is True and parity['rows']==len(restored['predictions'])==48
              and original['predictions']==restored['predictions'],'independent originalDEV whole prediction parity')
        check(parity['parent_tensor_sha256']==parity['restored_tensor_sha256']==parent_tensors[width],'exact authenticated selectedparent tensor parity')
        check(restored['source_fidelity']['metrics']['ordered_exact']==restored['source_fidelity']['metrics']['syntax_valid']==48,
              'all originalDEV whole-paragraph outputs retained')
        cache=reference(run['cache'])
        check(cache['bank_sha256']==bank['bank_sha256']and cache['orders']==orders and cache['rows']==180
              and cache['dimension']==width and cache['seed']==1729 and cache['batch_size']==6 and cache['full_vocabulary_size']==32
              and cache['max_optimizer_steps']==170 and cache['source_slot']==0,'complete detached fixed tensor cache contract')
        check(cache['cached_tensor_bytes']==180*width*36+2880,'independent preparedtensor bytecount')
        expected_estimate=len(raw(bank))*4+180*width*160+171*6*(32*40+4096)+1048576
        check(cache['estimated_training_work_bytes']==expected_estimate,'bounded training work estimate')
        check(cache['input_transform_sha256']==digest(preparation['input_transform']),'unchanged originalTRAIN transform')
        for key in('normalization_fitted','selection_performed','model_copied','encoder_executed','recurrent_forward_executed','count_forward_executed'):
            check(cache[key]is False,'cache performs no unauthorized work:'+key)
        expected_inventory=[{k:r[k]for k in('id','source_sha256','input_sha256','target_sha256','modality','template','modality_token_id')}for r in bank['rows']]
        check(cache['row_inventory']==expected_inventory,'complete cache row identity/target/vector hashes')
        readout=reference(run['full180_parent_readout'])
        check(readout['complete']is True and len(readout['rows'])==180 and readout['full_vocabulary_size']==32
              and readout['source_head_forward_calls']==30 and readout['model_tensor_sha256']==parent_tensors[width]
              and readout['optimizer_steps']==0 and readout['used_for_selection']is False,'complete diagnostic full180 head nofit readout')
        groups={};max_ce_error=0.;confusion={m:Counter()for m in('O','P','F')}
        for row,source in zip(readout['rows'],bank['rows']):
            logits=row['full_vocabulary_logits'];gold=source['modality_token_id'];argmax=max(range(32),key=logits.__getitem__)
            check(len(logits)==32 and all(type(v)is float and math.isfinite(v)for v in logits),'complete unmasked32V logits')
            check(row['id']==source['id']and row['source_sha256']==source['source_sha256']and row['target_token_id']==gold
                  and row['modality']==source['modality']and row['template']==source['template']
                  and row['correct']is(argmax==gold),'independent per-source full32V classification')
            top=max(logits);ce=math.log(math.fsum(math.exp(v-top)for v in logits))+top-logits[gold]
            error=abs(ce-row['cross_entropy']);max_ce_error=max(max_ce_error,error)
            check(error<=2e-6,'independent doubleCE vs recordedfloat32 numerical tolerance')
            confusion[source['modality']][str(argmax)]+=1
            for key in('all','modality:'+source['modality'],'template:'+source['template'],'stratum:'+source['modality']+':'+source['template']):
                item=groups.setdefault(key,dict(rows=0,correct=0,loss=0.));item['rows']+=1;item['correct']+=argmax==gold;item['loss']+=row['cross_entropy']
        expected={k:dict(rows=v['rows'],correct=v['correct'],cross_entropy=v['loss']/v['rows'])for k,v in groups.items()}
        check(readout['groups']==expected,'independent completegroup denominators/accuracy/authoritativefloat32 CE')
        observations.append(dict(arm=run['arm'],parent_tensor_sha256=parent_tensors[width],correct=readout['groups']['all']['correct'],
            clauses=180,cross_entropy=readout['groups']['all']['cross_entropy'],groups=readout['groups'],
            full32V_confusion_token_ids={k:dict(v)for k,v in confusion.items()},max_python_double_CE_difference=max_ce_error,
            note='Saved losses are float32 telemetry; double recomputation is a consistency check, not relabeled training telemetry.'))
    check(observations[0]['groups']==observations[1]['groups'],'both arms observe exactly same unchangedparent head')
    observations_path=attempt/'resource-observations.json'
    start_resource=load(attempt/'resources-start.json')
    if observations_path.exists():
        usage=load(observations_path)
    else:
        usage=[start_resource['record']['last_usage'],final['record']['last_usage']]
    peak=max(v['group_rss']['rss_bytes']for v in usage if v['group_rss']['available'])
    check(all(v['group_rss']['rss_bytes']<=v['memory_limit_bytes']for v in usage if v['group_rss']['available']), 'sampled own preflightmemory bound')
    leasepath=R/f'preflight-{width}-r1-lease-observations.jsonl';bind(leasepath)
    lease=[json.loads(line)for line in leasepath.read_text().splitlines()];lease=[v for v in lease if v.get('schema')=='guardian-owned-lease-observation/v1']
    check(all(v['healthy']and v['configuration_matches']for v in lease)and lease[-1]['expected']=='absent'
          and lease[-1]['lease_present']is False,'healthy sampled owned preflightlease andfinalrelease')
    audits[str(width)]=dict(passed=True,findings=[],dimension=width,driver_seconds=summary['elapsed_seconds'],guardian_seconds=outer['elapsed_seconds'],
        retained_attempt_bytes=final['record']['final_attempt_bytes'],sampled_rss_max=peak,rss_samples=len(usage),
        live_rss_samples=sum(v['group_rss']['live_processes']>0 for v in usage),
        periodic_resource_observations_file_present=observations_path.exists(),absolute_peak_claimed=False,
        source_only_no_nativeencoder=True,whole_originalDEV_parity=48,parent_head_readouts=observations,
        resource_status=final['status'],cap_bytes=final['storage_limit_bytes'],charged_campaign_bytes=final['record']['final_accounting']['charged_bytes'])
for name in('run_guardian.py','run_reserved.py','adopt_shared_scheduler.py','lazy_scheduler_adoption.py','owned_lease_watchdog.py'):
    bind(R/name)
bind(Path(__file__))
audit_path=OUT/'preflight_audit.json';audit=dict(schema='normative-wording-preflight-audit/v1',passed=True,findings=[],checks=checks,
    created_at=datetime.now(timezone.utc).isoformat(),dimensions=audits,artifacts=artifacts,models_loaded_by_auditor=False,
    native_encoders_executed_by_auditor=False,training_executed_by_auditor=False,qualified=False,admitted=False,lake_executed=False,
    limitations=['Full source-head readout is modality classification, not complete formula generation on the new wordings.',
                 'Preflight does not establish fit convergence; zeroarm exact M2 numerical/tensor replay must still pass after the actual fit.',
                 'No future development label bodies were read. Old originalDEV labels/material remain historically exposed.',
                 'Native preparation audit explicitly excludes availablecomposition64 vectors from its prior-vector comparison; complete source exclusion is preserved.',
                 'Resource measurements are sampled own-group data and saved accounting snapshots, not absolute peak or future capacity admission.'])
with audit_path.open('x')as f:json.dump(audit,f,indent=2,sort_keys=True);f.write('\n')
bind(audit_path)
for width in(384,768):
    ready=dict(schema='normative-wording-phase-readiness/v1',passed=True,findings=[],phase='training',dimension=width,run_root=str(R.resolve()),
        created_at=datetime.now(timezone.utc).isoformat(),artifacts=artifacts,checks=checks,preflight_audit_path=str(audit_path),
        preflight=audits[str(width)],native_preparation_audit_path=str(OUT/'native_preparation_audit.json'),
        resource_policy=dict(storage_bytes=400000000,memory_mib=1536,cpu_slots=1,child_process_slots=1,outer_seconds=1000,
            driver_seconds=900,fit_seconds=180,cap_bytes=145000000000,new_fit_admission_performed=False),
        experiment_scope='Fixed paired zero/.05 newTRAIN modality-supervision diagnostic; full originalstreams/gates retained.',
        qualified=False,admitted=False,lake_executed=False,checkpoint_promoted=False)
    path=RVIEW/f'training-{width}-readiness.json'
    with path.open('x')as f:json.dump(ready,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps(dict(path=str(path),sha256=bind(path)['sha256'],passed=True,dimension=width,checks=checks,
        initialTRAINheadcorrect=audits[str(width)]['parent_head_readouts'][0]['correct'],artifact_count=len(artifacts)),sort_keys=True))
