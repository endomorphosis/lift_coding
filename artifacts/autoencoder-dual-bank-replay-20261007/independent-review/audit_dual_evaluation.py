"""Independent stdlib eight-panel dual replay audit after explicit root completion.

Only saved outputs are read; no model/numerical owner imports or resource calls.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import time

PURE_PATH = Path('/home/barberb/lift_coding/artifacts/autoencoder-balanced-wording-20261007/training-review/audit_training.py')
PURE_SHA = 'cd8bd76cac229cf1d914286905f61d87d784544f06809e35f862eda4d2848976'
if hashlib.sha256(PURE_PATH.read_bytes()).hexdigest()!=PURE_SHA:raise ValueError('Frozen independent arithmetic differs')
spec=importlib.util.spec_from_file_location('_independent_saved_training_arithmetic',PURE_PATH)
training=importlib.util.module_from_spec(spec);spec.loader.exec_module(training)
pure=training.pure;raw,digest,close=pure.raw,pure.digest,pure.close
FIELDS,FACETS=pure.FIELDS,pure.FACETS
ARMS=('dual-bank-retention-ce',);ROLES=('selected','last-attempt')
COHORTS=('original_train48','normative_train48','new_balanced_train48','exposed_v3_48')


def context_from_lookup(rows,lookup):
    contexts={}
    for row in rows:
        char=byte=0;segments=[]
        for text in row['source_text'].split('\n\n'):
            vector=lookup[text]
            if len(vector)!=384 or any(type(v) not in (int,float) or not math.isfinite(v) for v in vector):raise ValueError('Invalid384 source vector')
            if abs(math.fsum(v*v for v in vector)-1)>1e-4:raise ValueError('Unnormalized cached vector')
            segments.append(dict(source_text=text,source_sha256=hashlib.sha256(text.encode()).hexdigest(),embedding_sha256=digest(vector),vector=vector,char_start=char,char_end=char+len(text),byte_start=byte,byte_end=byte+len(text.encode())))
            char+=len(text)+2;byte+=len(text.encode())+2
        contexts[row['id']]=dict(source_sha256=hashlib.sha256(row['source_text'].encode()).hexdigest(),segments=segments)
    return contexts


def distribution_summary(values,total=180):
    n=len(values)
    return dict(reference_sites=total,visited_scored_sites=n,unvisited_or_unavailable_sites=total-n,
        argmax_correct=sum(v['argmax_correct'] for v in values),full_vocabulary_size=32,
        mean_cross_entropy=math.fsum(v['full_vocabulary_cross_entropy'] for v in values)/n if n else None,
        minimum_target_margin=min((v['target_minus_best_other'] for v in values),default=None),
        maximum_target_margin=max((v['target_minus_best_other'] for v in values),default=None),
        mean_target_margin=math.fsum(v['target_minus_best_other'] for v in values)/n if n else None,
        nonpositive_target_margins=sum(v['target_minus_best_other']<=0 for v in values),
        unvisited_or_unavailable_counted_correct=False)


def prediction_signature(predictions):
    keys=('id','token_ids','generation_status','eos_reached')
    return [{key:row[key] for key in keys} for row in predictions]


def audit(attempt,output,completion):
    if not completion:raise ValueError('Explicit root evaluation completion signal required before output reads')
    started=time.monotonic();attempt=Path(attempt).resolve();run=attempt.parent
    if not re.fullmatch(r'evaluation-r[1-9][0-9]*',attempt.name):raise ValueError('Explicit completed evaluation attempt required')
    reader=pure.Reader();checks=[]
    def check(name,ok,detail=None):
        if not ok:raise ValueError(name)
        v=dict(check=name,passed=True)
        if detail is not None:v['detail']=detail
        checks.append(v)
    manifest=reader.json(run/'evaluation-manifest.json');plan=reader.json(run/'evaluation-plan.json')
    check('Exact frozen evaluation plan/input closure',manifest['plan_sha256']==reader.bindings[str(run/'evaluation-plan.json')]['sha256'] and plan['input_sha256']==manifest['inputs'])
    for path,wanted in manifest['inputs'].items():reader.body(path,{'sha256':wanted})
    for relative,wanted in manifest['extensions'].items():reader.body(run/'experiment-source'/relative,{'sha256':wanted})
    summary=reader.json(attempt/'results/summary.json');barrier=reader.json(attempt/'results/predictions-complete.json')
    expected={(a,r,c) for a in ARMS for r in ROLES for c in COHORTS}
    panels=pure.unique(summary['panels'],lambda p:(p['arm'],p['role'],p['cohort']));barrier_index=pure.unique(barrier['records'],lambda p:(p['arm'],p['role'],p['cohort']))
    check('All8 physical/logical panels and durable barrier',set(panels)==set(barrier_index)==expected and summary['logical_panels']==summary['physical_panels']==barrier['logical_panels']==barrier['physical_panels']==8 and barrier['complete'] is barrier['all_predictions_fsynced'] is True and barrier['v3_reference_json_loaded'] is False and barrier['inherited_TRAIN_validation_metadata_already_loaded'] is True and summary['all_v3_references_after_durable_prediction_barrier'] is True and summary['withheld_reference_blinding_claimed'] is False)
    check('Fixed384/512/temp0/full32/no-fit/no-encoder profile',summary['dimensions']==[384] and summary['source_context_tokens']==summary['output_tokens']==512 and summary['temperature']==0 and summary['batch_size']==8 and summary['full_vocabulary_size']==32 and summary['optimizer_steps']==0 and summary['training_executed'] is summary['encoder_executed'] is summary['teacher_forced_loss_measured'] is summary['reconstructed_input_mse_measured'] is False and summary['bridge_names']==[] and summary['legal_ir_evaluate_provers'] is False)
    training.false_masks(summary)
    trained=reader.json(manifest['training_summary']);runs=pure.unique([reader.ref(ref) for ref in trained['runs']],lambda r:r['arm']);states={(a,r):reader.ref(runs[a]['states'][r]) for a in ARMS for r in ROLES};codec=states[ARMS[0],ROLES[0]]['codec'];vocabulary=codec['target_vocabulary']
    for key,state in states.items():
        check('Actual typed endpoint state hash',state['tensor_sha256']==runs[key[0]]['states'][key[1]]['tensor_sha256']==training.typed_tensor_digest(state['model_state']) and state['weights_sha256']==digest(state['model_state']) and state['codec']==codec)
    aliases={a:states[a,'selected']['tensor_sha256']==states[a,'last-attempt']['tensor_sha256'] for a in ARMS}
    distinct_endpoints=len({s['tensor_sha256'] for s in states.values()})
    check('Onefit two endpoint roles preserve actual alias status',1<=distinct_endpoints<=2)
    reference_report=reader.ref(runs[ARMS[0]]['training_ref']);originals=None;original_contexts=None
    for path in manifest['inputs']:
        if path.endswith('/384/training-rows.json'):
            value=reader.json(path)
            if digest(value['train'])==reference_report['training_rows_sha256'] and digest(value['validation'])==reference_report['validation_rows_sha256']:originals=value
        if path.endswith('/384/source-contexts.json'):
            value=reader.json(path)
            if digest(value)==reference_report['source_contexts_sha256']:original_contexts=value
    check('Original cached48 rows/contexts authenticated',originals is not None and original_contexts is not None)
    inventories={role:reader.json(path) for role,path in manifest['source_inventories'].items()}
    cohorts={'original_train48':dict(rows=[{k:r[k] for k in ('id','source_text','input')} for r in originals['train']],contexts=original_contexts['train'])}
    for name,role in (('normative_train48','control'),('new_balanced_train48','balanced')):
        data=inventories[role]['source_inputs'];rows=data['rows'];lookup={r['source_text']:r['input'] for r in data['clause_cache']};contexts=context_from_lookup(rows,lookup)
        check('Native TRAIN source cache/context exact: '+name,data['targets_attached'] is False and data['inputs_sha256']==digest({k:v for k,v in data.items() if k!='inputs_sha256'}) and contexts==data['source_contexts'])
        cohorts[name]=dict(rows=rows,contexts=contexts)
    prior=inventories['control']['prior_sources_by_dataset']['exposed_v3'];lookup={}
    for row in inventories['control']['evaluation_vectors_by_dataset']['exposed_v3']:
        text=row['source_text'];check('v3 exact-text vector aliases consistent',text not in lookup or lookup[text]==row['input']);lookup[text]=row['input']
    v3rows=[dict(r,input=lookup[r['source_text']]) for r in prior];cohorts['exposed_v3_48']=dict(rows=v3rows,contexts=context_from_lookup(prior,lookup))
    identities=set()
    for name,data in cohorts.items():
        ids={r['id'] for r in data['rows']};check('Separate48/180 source cohort: '+name,len(ids)==len(data['rows'])==48 and not ids&identities and all(set(r)=={'id','source_text','input'} for r in data['rows']) and sum(len(c['segments']) for c in data['contexts'].values())==180)
        identities|=ids
        rebuilt=context_from_lookup(data['rows'],{s['source_text']:s['vector'] for c in data['contexts'].values() for s in c['segments']});check('Everysource hash/vector/digest/offset reconstructed: '+name,rebuilt==data['contexts'])
    # Validate every durable prediction and trace before parsing explicit v3
    # reference bodies. Input hashing above does not parse that reference JSON.
    saved={};physical_paths=set();trace_site_total=0
    for key,record in panels.items():
        arm,role,cohort=key;bar=barrier_index[key];trace=reader.ref(record['trace_ref']);prediction=reader.ref(record['predictions_ref']);state=states[arm,role];data=cohorts[cohort]
        for field in ('state_ref','trace_ref','predictions_ref','prediction_fsynced','physical_panel_computed'):check('Barrier exact panel binding',record[field]==bar[field])
        check('Physical panel and alias declaration',record['physical_panel_computed'] is record['prediction_fsynced'] is True and record['selected_last_tensor_alias'] is aliases[arm] and record['trace_ref']['path'] not in physical_paths);physical_paths.add(record['trace_ref']['path'])
        check('Same-pass source-only trace identity/prefix-free policy',trace['trace_sha256']==digest({k:v for k,v in trace.items() if k!='trace_sha256'}) and trace['sample_count']==48 and trace['dimension']==384 and trace['model_tensor_sha256']==state['tensor_sha256']==prediction['model_tensor_sha256'] and trace['codec_sha256']==digest(codec) and trace['input_transform_sha256']==digest(state['input_transform']) and trace['source_rows_sha256']==digest(data['rows']) and trace['source_contexts_sha256']==digest(data['contexts']) and trace['predictions']==prediction['predictions'] and prediction['same_pass_scalar_trace_sha256']==trace['trace_sha256'] and all(trace[k] is False for k in ('reference_count_access','reference_prefix_access','reference_documents_passed_to_model','inventory_access','source_context_target_access','syntax_mask','forced_closure','model_copied')) and all(trace[k] is True for k in ('source_only','full_vocabulary_retained','decomposition_exact','caller_state_preserved','hooks_removed','complete_rollout_before_reference_scoring')) and trace['extra_model_passes']==trace['source_head_extra_evaluations']==trace['optimizer_steps']==0)
        sites={};batch_steps={}
        for i,(source,row,pred) in enumerate(zip(data['rows'],trace['rows'],trace['predictions'],strict=True)):
            check('Actual prefix/source row binding',source['id']==row['id']==pred['id'] and row['consumed_prefix']==[1]+pred['token_ids'][:len(row['consumed_prefix'])-1] and row['input_sha256']==digest(source['input']) and row['source_context_sha256']==digest(data['contexts'][source['id']]) and row['batch_offset']==i//8*8)
            routes,invalid=pure.causal_sites(row['consumed_prefix'],vocabulary);check('Every causally visited grammar/scalar site retained',len(routes)==len(row['scalar_sites']) and row['first_invalid_prefix_position']==invalid)
            batch_steps[row['batch_offset']]=max(batch_steps.get(row['batch_offset'],0),len(row['consumed_prefix']))
            for route,site in zip(routes,row['scalar_sites'],strict=True):
                sitekey=(row['id'],site['slot'],site['field']);check('Exact consumed grammar route and unique site',all(site[k]==v for k,v in route.items()) and sitekey not in sites)
                vectors=[pure.vector32(site[k]) for k in ('raw_recurrent_logits','applied_source_logits','combined_logits')];available=site['slot']<len(data['contexts'][row['id']]['segments'])
                check('Float32 actual addition/unrestrictedargmax/source slot binding',[pure.f32(a+b) for a,b in zip(*vectors[:2])]==vectors[2] and max(range(32),key=vectors[2].__getitem__)==site['actual_next_token_id']==pred['token_ids'][site['position']] and site['source_slot_available'] is available and (available or all(v==0 for v in vectors[1])) and site['source_clause_sha256']==(data['contexts'][row['id']]['segments'][site['slot']]['source_sha256'] if available else None))
                sites[sitekey]=(site,row)
        check('Actual trace steps/site totals full',trace['scalar_site_count']==len(sites) and sum(batch_steps.values())==trace['greedy_batch_steps']==trace['recurrent_readout_calls'])
        trace_site_total+=len(sites);saved[key]=(trace,prediction,sites);training.false_masks(trace);training.false_masks(prediction)
    check('All8 durable panel bodies checked before v3 reference parsing',len(saved)==len(physical_paths)==8)
    reference_sets={'original_train48':[dict(id=r['id'],source_text=r['source_text'],target_ids=r['target_ids'],target=training.strict_json(''.join(vocabulary[t] for t in r['target_ids'][1:-1])),clause_count=len(r['source_text'].split('\n\n')),template='original_train',split='training') for r in originals['train']], 'normative_train48':inventories['control']['corpus']['references'],'new_balanced_train48':inventories['balanced']['corpus']['references'],'exposed_v3_48':reader.json(manifest['v3_references'])}
    references={}
    for name,refs in reference_sets.items():
        by_id=pure.unique(refs,lambda r:r['id']);ordered=[]
        for row in cohorts[name]['rows']:
            ref=dict(by_id[row['id']]);ref.update(source_sha256=hashlib.sha256(row['source_text'].encode()).hexdigest(),clause_count=len(ref['target']['rules']))
            check('Complete seven-facet authored reference/target IDs',ref['source_text']==row['source_text'] and training.strict_json(''.join(vocabulary[t] for t in ref['target_ids'][1:-1]))==ref['target'] and ref['target_ids'][0]==1 and ref['target_ids'][-1]==2 and ref['clause_count']==len(row['source_text'].split('\n\n')) and all(set(rule)==set(FACETS) and all(rule[f]==[] for f in FACETS[4:]) for rule in ref['target']['rules']))
            ordered.append(ref)
        check('Reference48/180/720 fixed denominator: '+name,len(ordered)==48 and sum(r['clause_count'] for r in ordered)==180);references[name]=ordered
    summaries={};scored_total=distribution_count=reference_total=0
    for key,record in panels.items():
        arm,role,name=key;trace,prediction,sites=saved[key];refs=references[name];refmap={r['id']:r for r in refs};data=cohorts[name];scalar=reader.ref(record['scalar_score_ref']);fidelity=reader.ref(record['formula_fidelity_ref']);joined=reader.ref(record['scalar_formula_join_ref'])
        scored_rows=[dict(row,target_ids=ref['target_ids']) for row,ref in zip(data['rows'],refs,strict=True)]
        check('Posthoc score exact durable trace/reference identities',scalar['score_sha256']==digest({k:v for k,v in scalar.items() if k!='score_sha256'}) and scalar['trace_sha256']==trace['trace_sha256'] and scalar['rows_sha256']==digest(scored_rows) and scalar['references_sha256']==digest(refs) and scalar['source_contexts_sha256']==digest(data['contexts']) and scalar['reference_labels_used_only_after_rollout'] is True and scalar['optimizer_steps']==0)
        events=pure.unique(scalar['events'],lambda e:(e['id'],e['slot'],e['field']));wanted={(r['id'],slot,f) for r in refs for slot in range(r['clause_count']) for f in FIELDS};check('Complete720 scalarreference coverage definition',len(wanted)==record['scalar_reference_sites']==720 and set(events)<=wanted and set(events)<=set(sites) and len(events)==scalar['scored_sites'])
        per_field={f:dict(scored=0,source_correct=0,recurrent_correct=0,combined_correct=0,source_correct_combined_wrong=0) for f in FIELDS};distributions=defaultdict(list)
        for identity,event in events.items():
            site,row=sites[identity];gold=refmap[identity[0]]['target']['rules'][identity[1]];target=vocabulary.index(json.dumps(gold[identity[2]],ensure_ascii=False,separators=(',',':')))
            check('Scored actualprefix/label/position/source-clause binding',event['target_token_id']==target and event['position']==site['position'] and event['actual_next_token_id']==site['actual_next_token_id'] and event['prefix_sha256']==digest(row['consumed_prefix'][:site['position']+1]) and event['source_clause_sha256']==site['source_clause_sha256'])
            per_field[identity[2]]['scored']+=1
            for head,vector in (('source','applied_source_logits'),('recurrent','raw_recurrent_logits'),('combined','combined_logits')):
                expected_metrics=pure.metrics(site[vector],target,site['actual_next_token_id']);check('Stored full32 source/recurrent/combined CE/margin exact',close(event[head],expected_metrics));correct=expected_metrics['argmax_token_id']==target;per_field[identity[2]][head+'_correct']+=correct;distributions[identity[2],head].append(dict(expected_metrics,argmax_correct=correct));distribution_count+=1
            per_field[identity[2]]['source_correct_combined_wrong']+=event['source']['argmax_token_id']==target and event['combined']['argmax_token_id']!=target
        check('Independent scalarperfield totals exact',scalar['per_field']==per_field)
        unvisited={(e['id'],e['slot'],e['field']) for e in scalar['unvisited_reference_sites']};unavailable={(e['id'],e['slot'],e['field']) for e in scalar['unscored_sites'] if (e['id'],e['slot'],e['field']) in wanted};extra=[e for e in scalar['unscored_sites'] if (e['id'],e['slot'],e['field']) not in wanted]
        check('Every reference site scored or explicitunvisited/unavailable',unvisited==wanted-set(events) and unavailable<=unvisited and len(unvisited)==len(scalar['unvisited_reference_sites']))
        counts=Counter();seven={f:Counter() for f in FACETS};by_length={};generated_map={}
        check('All48 actual formula rows retained',len(fidelity['rows'])==48 and fidelity['complete_evaluation'] is True and [r['id'] for r in fidelity['rows']]==[r['id'] for r in refs])
        for ref,pred,row in zip(refs,prediction['predictions'],fidelity['rows'],strict=True):
            generated,c,facets=training.formula_counts(ref['target'],pred,vocabulary);check('Actual emitted formulas/allseven facetsofexpectedrules',ref['id']==pred['id']==row['id'] and row['expected_ir']==ref['target'] and row['generated_ir']==generated and row['counts']==c and row['by_facet']==facets and row['generated_token_ids']==pred['token_ids']);generated_map[ref['id']]=generated
            counts.update(c);length=str(ref['clause_count']);bucket=by_length.setdefault(length,dict(metrics=Counter(),by_facet={f:Counter() for f in FACETS}));bucket['metrics'].update(c)
            for f,v in facets.items():seven[f].update(v);bucket['by_facet'][f].update(v)
        check('Formula aggregate/correctdenominators/order/extras/omissions',dict(counts)==fidelity['metrics']==record['formula_metrics'] and {f:dict(v) for f,v in seven.items()}==fidelity['by_facet'] and by_length==fidelity['by_length'] and record['seven_facets']=={f:{k:seven[f][k] for k in ('correct','total')} for f in FACETS} and counts['expected_rules']==180)
        join_counts={f:dict(reference_sites=180,visited=0,unvisited=0,unavailable=0,source_correct=0,source_incorrect=0,source_correct_formula_wrong=0,source_wrong_formula_correct=0) for f in FIELDS};wrong_rows=[]
        ordered_rules=[(r,slot,rule) for r in refs for slot,rule in enumerate(r['target']['rules'])]
        for row,(ref,slot,gold) in zip(joined['rows'],ordered_rules,strict=True):
            produced=generated_map[ref['id']];rules=produced.get('rules') if type(produced)is dict else None;generated_rule=rules[slot] if type(rules)is list and slot<len(rules) else None
            check('Complete180 scalar/formula joinedrule ordering',row['id']==ref['id'] and row['slot']==slot and row['expected_rule']==gold and row['generated_rule']==generated_rule)
            for field in FIELDS:
                identity=(ref['id'],slot,field);value=row['fields'][field];event=events.get(identity);formula_correct=type(generated_rule)is dict and generated_rule.get(field)==gold[field];status='visited' if event else 'unavailable' if identity in unavailable else 'unvisited';bucket=join_counts[field];bucket[status]+=1
                check('Source/formula correctness statusesindependent',value['status']==status and value['formula_field_correct'] is formula_correct)
                if event:
                    correct=event['source']['argmax_token_id']==event['target_token_id'];check('Visited join retains every actual event metric',value['source_correct'] is correct and all(value[k]==v for k,v in event.items()));bucket['source_correct' if correct else 'source_incorrect']+=1;bucket['source_correct_formula_wrong']+=correct and not formula_correct;bucket['source_wrong_formula_correct']+=not correct and formula_correct
                else:check('Unvisited/unavailable source truth remains null',value['source_correct'] is None)
            if generated_rule!=gold:wrong_rows.append(dict(paragraph_id=ref['id'],slot=slot,source_text=ref['source_text'].split('\n\n')[slot],expected_rule=gold,generated_rule=generated_rule,fields=row['fields']))
        check('Every720 joinedstatus/fullperfield denominator preserved',len(joined['rows'])==180 and joined['per_field']==record['scalar_by_field']==join_counts and joined['extra_generated_unavailable_sites']==extra and joined['unvisited_counted_correct'] is joined['unavailable_counted_correct'] is False)
        if name=='original_train48':
            old=reader.ref(runs[arm]['postfit'][role]['training']);check('ActualoriginalTRAIN token/status/EOS parity withtrainingpanel',prediction_signature(prediction['predictions'])==prediction_signature(old['predictions']))
        training.false_masks(scalar);training.false_masks(fidelity);training.false_masks(joined)
        combined_formula={f:dict(reference_sites=180,visited=0,unvisited=0,unavailable=0,combined_correct=0,combined_incorrect=0,combined_correct_formula_wrong=0,combined_wrong_formula_correct=0) for f in FIELDS}
        for row in joined['rows']:
            for field in FIELDS:
                value=row['fields'][field];bucket=combined_formula[field];bucket[value['status']]+=1
                if value['status']=='visited':
                    correct=value['combined']['argmax_token_id']==value['target_token_id'];formula_correct=value['formula_field_correct'];bucket['combined_correct' if correct else 'combined_incorrect']+=1;bucket['combined_correct_formula_wrong']+=correct and not formula_correct;bucket['combined_wrong_formula_correct']+=not correct and formula_correct
        summaries[key]=dict(combined_formula_join_counts=combined_formula,arm=arm,role=role,cohort=name,tensor_sha256=states[arm,role]['tensor_sha256'],paragraphs=48,rules=180,reference_scalar_sites=720,visited_trace_sites=len(sites),scored_sites=len(events),unvisited_reference_sites=len(unvisited-unavailable),unavailable_reference_sites=len(unavailable),extra_generated_sites=len(set(sites)-wanted),formula_metrics=dict(counts),seven_facets={f:dict(v) for f,v in seven.items()},by_length=by_length,source_formula_join_counts=join_counts,actual_prefix_full32_distributions={f:{head:distribution_summary(distributions[f,head]) for head in ('source','recurrent','combined')} for f in FIELDS},wrong_emitted_rules=wrong_rows,generation_seconds=record['generation_seconds'],scoring_seconds=record['scoring_seconds'])
        scored_total+=len(events);reference_total+=720
    for arm in ARMS:
        for cohort in COHORTS:
            selected=saved[arm,'selected',cohort];last=saved[arm,'last-attempt',cohort];check('Actual tensor alias deterministic repeatedpanels are notreplicates',not aliases[arm] or selected[1]['predictions']==last[1]['predictions'] and selected[0]['rows']==last[0]['rows'])
    check('All384paragraphs/1440rules/5760 reference sites explicit',sum(s['paragraphs'] for s in summaries.values())==384 and sum(s['rules'] for s in summaries.values())==1440 and reference_total==5760)
    for path,wanted in summary['source_dependencies'].items():reader.body(path,{'sha256':wanted})
    final=reader.json(attempt/'resources-final.json');start=reader.json(attempt/'resources-start.json');child=reader.json(attempt/'child-exit.json');outer=reader.json(run/(attempt.name+'-guardian-exit.json'));record=final['record'];lease=final['resource_lease'];initial=start['record'];periodic_path=attempt/'resource-observations.json';periodic=reader.json(periodic_path) if periodic_path.is_file() else [];samples=[initial['last_usage'],*periodic,record['last_usage']]
    check('Completedexit0/durableownrelease/identity/groupzero',child['returncode']==outer['returncode']==0 and child['leader_reaped'] is True and final['status']==record['status']=='released' and record['artifacts_durable_asserted'] is True and record['attempt_exceeded_reservation'] is False and final['cleanup_error'] is None and lease['released'] is True and lease['lease_id']==start['resource_lease']['lease_id'] and record['reservation_id']==initial['reservation_id'] and record['child']==initial['child'] and record['last_usage']['group_rss']['available'] is True and record['last_usage']['group_rss']['live_processes']==record['last_usage']['group_rss']['rss_bytes']==0)
    check('OneCPU/1536MiB/100MB sampledbounds and145GBfinalcensus',record['cpu_slots']==record['child_process_slots']==1 and record['memory_mb']==1536 and record['storage_bytes']==100000000 and all(r['attempt_bytes']<=r['attempt_limit_bytes'] and r['charged_bytes']<=r['limit_bytes'] and r['group_rss']['rss_bytes']<=r['memory_limit_bytes'] and r['process_slot_estimate_exceeded'] is False for r in samples) and record['final_accounting']['charged_bytes']<=record['final_accounting']['limit_bytes']==145000000000)
    watchdog=final['lease_watchdog'];present=[json.loads(line) for line in reader.body(watchdog['events_path'],{'sha256':watchdog['events_sha256']}).splitlines() if line];present=[e for e in present if e.get('lease_present')is True];post=watchdog['post_release_observation'];check('Sampledownedleasehealthy/absence/configunchanged',bool(present) and all(e['healthy'] is e['configuration_matches'] is True and e['cancelled'] is False for e in present) and post['lease_present'] is False and post['healthy'] is post['configuration_matches'] is True and watchdog['shared_state_mutated_by_observer'] is watchdog['continuous_lease_coverage_claimed'] is False)
    # Compare to the separately completed parent retention/observer evidence;
    # never pool cohorts or call the already exposedv3 panel a fresh holdout.
    protocol=reader.json(manifest['comparison_protocol'])
    archived=reader.ref(protocol['archived_evaluation'])
    archived_index=pure.unique(archived['selected_panels'],lambda p:(p['arm'],p['cohort']))
    comparisons={}
    for name in COHORTS:
        replay=summaries[ARMS[0],'selected',name]
        control=archived_index['control-wording-ce',name]
        balanced=archived_index['balanced-wording-ce',name]
        check('Archived comparator same48/180/720 denominators',control['paragraphs']==balanced['paragraphs']==48 and control['rules']==balanced['rules']==180 and control['reference_scalar_sites']==balanced['reference_scalar_sites']==720)
        comparisons[name]=dict(replay_ordered_exact=replay['formula_metrics']['ordered_exact'],archived_control_ordered_exact=control['formula_metrics']['ordered_exact'],archived_balanced_ordered_exact=balanced['formula_metrics']['ordered_exact'],replay_minus_archived_control=replay['formula_metrics']['ordered_exact']-control['formula_metrics']['ordered_exact'],replay_minus_archived_balanced=replay['formula_metrics']['ordered_exact']-balanced['formula_metrics']['ordered_exact'],replay_seven_facets=replay['seven_facets'],archived_control_seven_facets=control['seven_facets'],fresh_matched_control=False,auxiliary_chronology_changed=True,bank_mixing_effect_causally_isolated=False)
    reader.body(PURE_PATH,{'sha256':PURE_SHA});reader.body(__file__)
    report=dict(schema='dual-bank-replay-native384-postfit-evaluation-independent-review/v1',passed=True,findings=[],checks=checks,artifacts=reader.bindings,attempt=str(attempt),panels=[summaries[k] for k in sorted(summaries)],cohort_comparisons=comparisons,physical_panels=8,logical_panels=8,physical_paragraphs=384,reference_rules=1440,reference_scalar_sites=5760,actual_visited_trace_sites=trace_site_total,actual_scored_scalar_sites=scored_total,source_recurrent_combined_distributions=distribution_count,distinct_tensor_endpoints=distinct_endpoints,selected_last_role_aliases=aliases,selected_last_alias_status_verified=True,aliases_are_independent_replicates=False,all8durability_barrier_checked_before_explicit_v3_reference_parse=True,inherited_TRAIN_validation_metadata_access_disclosed=True,fresh_semantic_holdout=False,training_executed=False,models_or_encoders_or_numerical_owners_imported_or_executed_by_audit=False,qualified=False,admitted=False,proof_authority=False,source_semantics_verified=False,checkpoint_promoted=False,convergence_proven=False,resources=dict(own_lease_durably_released=True,final_live_group_processes=0,periodic_sample_count=len(periodic),maximum_saved_group_RSS_bytes=max(r['group_rss']['rss_bytes'] for r in samples),peak_RSS_measured=False,storage_reservation_bytes=100000000,memory_MiB=1536,final_attempt_census_bytes=record['final_attempt_bytes'],final_named_root_charge_bytes=record['final_accounting']['charged_bytes'],named_root_cap_bytes=145000000000,present_own_lease_samples=len(present),continuous_coverage_claimed=False,current_foreign_scheduler_read_or_modified=False),timing=dict(driver_seconds=summary['elapsed_seconds'],outer_guardian_seconds=outer['elapsed_seconds'],launch_return_through_reap_seconds=child['launch_return_through_reap_wall_seconds'],scope='8 physical same-pass greedy panels and pure posthoc scoring on cached384 features; no teacher-forced loss, reconstruction MSE, new encoder, native compiler, Lake/proof or end-to-end speed measurement.'),limits=['Four cohorts retain separate48/180/720 denominators; all reference sites survive incomplete or unavailable generation.','Selected/last equality is checked from actual tensors. Equal endpoints must repeat deterministic output; differing endpoints are distinct roles from one fit, not independent replications.','v3 is exposed development and original meanings are deliberately reused. The explicitv3 file is parsed only after8 durable prediction files; inherited historical setup metadata access is disclosed.','Source/recurrent/combined full32 arithmetic includes source-conditioned recurrent history and is not causal isolation. This one fit is compared with archived controls; bank mixing and auxiliary chronology cannot be isolated.','Original384 paragraph/context caches remain caller-byte authenticated without new producer verification; new balanced384 cache has separate target-free native preparation receipts. Evaluation forwards no encoder.','Frozen historical schema callbacks and import logs do not establish canonical working-tree compiler execution, Lean admission, convergence or legal authority.'],audit_elapsed_seconds=time.monotonic()-started)
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x') as stream:stream.write(json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+'\n')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--completed-attempt',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--root-completion-acknowledged',action='store_true');args=parser.parse_args();report=audit(args.completed_attempt,args.output,args.root_completion_acknowledged)
    print(json.dumps(dict(passed=True,checks=len(report['checks']),reference_scalar_sites=report['reference_scalar_sites'],visited_sites=report['actual_visited_trace_sites'],distributions=report['source_recurrent_combined_distributions'],output=str(args.output))))
