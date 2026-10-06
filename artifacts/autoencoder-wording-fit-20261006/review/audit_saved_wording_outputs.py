"""Audit completed saved postfit evidence with standard-library arithmetic only.

No package owner, encoder, parser, checkpoint model, or network is imported.
Future reference JSON is parsed only after all eight unchanged trace/prediction
files pass the saved durable-completion barrier. CE for scalar sites is rebuilt
from retained full32V logits. Teacher-forced token CE is checked from retained
per-token losses; its unavailable full logits are not invented.
"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import struct

DEFAULT_ROOT = Path('/home/barberb/lift_coding/external/ipfs_datasets/workspace/test-logs/decoder-normative-wording-r2-20261006')
DEFAULT_OUT = Path('/home/barberb/lift_coding/artifacts/autoencoder-wording-fit-20261006/review/development_results_audit.json')
ARMS = ('normative-wording-zero','normative-wording-ce')
ROLES = ('selected','last-attempt')
FIELDS = ('actor','action','modality','object')
ALL_FIELDS = (*FIELDS,'conditions','exceptions','temporal')


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',', ':'),
        ensure_ascii=True,allow_nan=False).encode()).hexdigest()


def sha(path):
    value=hashlib.sha256(); size=0
    with Path(path).open('rb') as stream:
        for data in iter(lambda:stream.read(1048576),b''):
            value.update(data); size+=len(data)
    return dict(sha256=value.hexdigest(),bytes=size)


def float32(value):
    return struct.unpack('<f',struct.pack('<f',value))[0]


def strict_json(text):
    def object_pairs(pairs):
        result={}
        for key,value in pairs:
            if key in result:
                raise ValueError('duplicate JSON key')
            result[key]=value
        return result
    def reject_constant(value):
        raise ValueError('nonfinite JSON constant '+value)
    return json.loads(text,object_pairs_hook=object_pairs,parse_constant=reject_constant)


def metrics(vector,target,emitted):
    maximum=max(vector)
    return dict(argmax_token_id=max(range(len(vector)),key=vector.__getitem__),
        target_minus_best_other=vector[target]-max(v for i,v in enumerate(vector) if i!=target),
        target_minus_emitted=vector[target]-vector[emitted],
        full_vocabulary_cross_entropy=maximum+math.log(math.fsum(math.exp(v-maximum) for v in vector))-vector[target])


class Audit:
    def __init__(self):
        self.checks=0
        self.bindings={}

    def check(self,value,message):
        if not value:
            raise ValueError(message)
        self.checks+=1

    def file(self,path,expected=None):
        path=Path(path).resolve(); value=sha(path)
        self.check(expected is None or value['sha256']==expected,'changed saved artifact '+str(path))
        self.check(str(path) not in self.bindings or self.bindings[str(path)]==value,
            'artifact changed during audit '+str(path))
        self.bindings[str(path)]=value
        return value

    def read(self,path,expected=None):
        self.file(path,expected)
        return json.loads(Path(path).read_bytes())

    def reference(self,ref):
        value=self.file(ref['path'],ref['sha256'])
        self.check('bytes' not in ref or ref['bytes']==value['bytes'],'artifact byte receipt differs')
        return json.loads(Path(ref['path']).read_bytes())

    def close(self,actual,expected,message):
        self.check(type(actual) in (int,float) and math.isfinite(actual)
            and math.isclose(actual,expected,rel_tol=1e-10,abs_tol=1e-10),message)


def audit(args):
    a=Audit();root=args.run_root.resolve();results=root/args.evaluation_attempt/'results'
    manifest=a.read(root/'evaluation-manifest.json');summary=a.read(results/'summary.json')
    a.check(summary['complete'] is True and summary['all_predictions_persisted_before_reference_load'] is True
        and summary['all_predictions_fsynced_before_reference_load'] is True,'complete durable postfit result required')
    a.check(summary['original_meanings_previously_exposed'] is True,'prior meaning exposure must remain explicit')
    a.check(all(summary[k] is False for k in ('qualified','admitted','lake_executed',
        'checkpoint_promoted','fresh_holdout','used_for_selection')),'postfit result gained admission/selection authority')
    a.check(summary['recipe']['panel_count']==8 and summary['recipe']['samples_per_panel']==60
        and summary['recipe']['vocabulary_size']==32,'complete8x60 full32V panel recipe')
    complete=a.read(results/'predictions-complete.json')
    a.check(complete['complete'] is True and complete['all_predictions_fsynced'] is True
        and complete['development_reference_json_loaded'] is False,'reference barrier completion receipt')
    records=complete['records'];expected={(d,arm,role) for d in (384,768) for arm in ARMS for role in ROLES}
    a.check(len(records)==8 and {(r['dimension'],r['arm'],r['role']) for r in records}==expected,
        'all eight unique endpoints required before reference parse')
    index={};sources={};caches={}
    for d in (384,768):
        path=manifest['source_inputs'][str(d)]
        cache=a.read(path,manifest['inputs'][str(Path(path).resolve())]);caches[d]=cache
        sources[d]=[{k:r[k] for k in ('id','source_text')} for r in cache['rows']]
        a.check(cache['schema']=='prospective-wording-source-inputs/v1' and cache['complete'] is True
            and cache['dimension']==d and len(cache['rows'])==60,'warm complete sixty-source cache')
        a.check(cache['inputs_sha256']==digest({k:v for k,v in cache.items() if k!='inputs_sha256'}),'source cache content binding')
    a.check(sources[384]==sources[768],'identical prospective source ordering by width')
    for record in records:
        key=(record['dimension'],record['arm'],record['role'])
        a.check(record['prediction_fsynced'] is True and record['source_head_trace_fsynced'] is True,
            'trace and prediction durability receipt')
        panel=a.reference(record['predictions_ref']);trace=a.reference(record['source_head_trace_ref'])
        d=record['dimension'];cache=caches[d]
        a.check(panel['complete'] is True and trace['complete'] is True and len(panel['predictions'])==60
            and trace['sample_count']==60 and trace['dimension']==d,'complete same-pass panel')
        a.check(trace['trace_sha256']==digest({k:v for k,v in trace.items() if k!='trace_sha256'}),'trace content hash')
        a.check(panel['predictions']==trace['predictions']
            and panel['same_pass_scalar_trace_sha256']==trace['trace_sha256'],'same-pass predictions equal trace')
        a.check([p['id'] for p in panel['predictions']]==[s['id'] for s in sources[d]],'all source identities retained')
        a.check(trace['model_tensor_sha256']==panel['model_tensor_sha256']==record['state_ref']['tensor_sha256'],
            'exact saved endpoint tensor binding')
        a.check(trace['source_rows_sha256']==panel['source_rows_sha256']==digest(cache['rows'])
            and trace['source_contexts_sha256']==panel['source_contexts_sha256']==digest(cache['source_contexts']),
            'exact warm sources and clause contexts')
        a.check(trace['full_vocabulary_retained'] is True and trace['vocabulary_size']==32
            and trace['extra_model_passes']==trace['source_head_extra_evaluations']==trace['optimizer_steps']==0,
            'all32 logit classes and no extra model pass')
        a.check(panel['generation_reference_access'] is False and trace['reference_count_access'] is False
            and trace['reference_prefix_access'] is False and trace['reference_documents_passed_to_model'] is False,
            'source-only generation policies')
        a.check(panel['reconstructed_input_mse_measured'] is False and 'reconstructed_input_mse' not in panel,
            'unmeasured embedding MSE must remain unavailable')
        index[key]=dict(record=record,panel=panel,trace=trace)
    # All eight source-only pairs have passed. Reference label bodies enter only here.
    path=manifest['references'];refs=a.read(path,manifest['inputs'][str(Path(path).resolve())])
    receipt_path=manifest['development_receipt'];receipt=a.read(receipt_path,
        manifest['inputs'][str(Path(receipt_path).resolve())])
    a.check(len(refs)==60 and receipt['source_rows']==60 and receipt['source_rows_sha256']==digest(sources[384])
        and receipt['references_sha256']==digest(refs),'all sixty authored reference/source bindings')
    a.check(receipt['original_meanings_previously_exposed'] is True and receipt['source_semantics_verified'] is False
        and receipt['fresh_holdout_claimed'] is False and receipt['training_allowed'] is False
        and receipt['selection_allowed'] is False,'honest authored prospective-wording provenance')
    codec_path=Path(manifest['development_seal']).parent/'codec.json'
    codec=a.read(codec_path,manifest['inputs'][str(codec_path.resolve())]);vocab=codec['target_vocabulary']
    a.check(len(vocab)==32 and digest(codec)==receipt['codec_sha256'],'unchanged32V codec')
    reference_by_id={r['id']:r for r in refs}
    a.check(len(reference_by_id)==60 and all(r['split']=='prospective_authored_development'
        and r['clause_count']==1 and len(r['target']['rules'])==1 for r in refs),'complete authored single-clause references')
    results_summary={};samples=[];sample_counts=Counter();panel_entries=summary['panels']
    a.check(len(panel_entries)==8 and {(r['dimension'],r['arm'],r['role']) for r in panel_entries}==expected,
        'all eight scored endpoints retained')
    for entry in panel_entries:
        key=(entry['dimension'],entry['arm'],entry['role']);saved=index[key]
        panel,trace=saved['panel'],saved['trace']
        score=a.reference(entry['score_ref']);scalar=a.reference(entry['source_head_score_ref'])
        joined=a.reference(entry['source_head_formula_join_ref'])
        a.check(scalar['score_sha256']==digest({k:v for k,v in scalar.items() if k!='score_sha256'})
            and scalar['trace_sha256']==trace['trace_sha256'],'posthoc scalar score trace binding')
        a.check(scalar['reference_labels_used_only_after_rollout'] is True
            and scalar['models_executed'] is False and scalar['training_loss_returned'] is False,
            'posthoc scalar labels cause no model or training work')
        a.check(score['teacher_forced']['full_vocabulary_size']==32
            and score['teacher_forced']['reference_prefixes_used'] is True
            and score['teacher_forced']['greedy_repeated'] is False,
            'teacher-forced full32V CE remains separate from greedy fidelity')
        sites={};event_counts=Counter();correct=Counter();ce_sum=defaultdict(float)
        for row in trace['rows']:
            a.check(row['id'] in reference_by_id,'trace source remains in declared cohort')
            for site in row['scalar_sites']:
                vectors=[site[k] for k in ('applied_source_logits','raw_recurrent_logits','combined_logits')]
                a.check(all(len(v)==32 and all(type(x) in (int,float) and math.isfinite(x) for x in v)
                    for v in vectors),'finite full32V scalar decomposition')
                a.check(all(float32(s+r)==c for s,r,c in zip(*vectors,strict=True)),
                    'independent float32 source plus recurrent equals actual combined')
                if site['source_slot_available']:
                    identity=(row['id'],site['slot'],site['field'])
                    a.check(identity not in sites,'causal site not collapsed')
                    sites[identity]=site
        a.check(len(scalar['events'])==scalar['scored_sites'],'all scored causal sites retained')
        for event in scalar['events']:
            identity=(event['id'],event['slot'],event['field']);site=sites[identity]
            a.check(event['slot']==0 and event['field'] in FIELDS,'only positioned single-source scalar slots scored')
            gold=reference_by_id[event['id']]['target']['rules'][0][event['field']]
            target=vocab.index(json.dumps(gold));emitted=site['actual_next_token_id']
            a.check(event['target_token_id']==target and event['actual_next_token_id']==emitted,'exact authored scalar label and emitted token')
            for name,vector_name in [('source','applied_source_logits'),('recurrent','raw_recurrent_logits'),('combined','combined_logits')]:
                actual=event[name];calculated=metrics(site[vector_name],target,emitted)
                a.check(actual['argmax_token_id']==calculated['argmax_token_id'],'independent full32V argmax')
                for field in ('target_minus_best_other','target_minus_emitted','full_vocabulary_cross_entropy'):
                    a.close(actual[field],calculated[field],'independent scalar '+field)
            field=event['field'];event_counts[field]+=1
            correct[field]+=event['source']['argmax_token_id']==target
            ce_sum[field]+=event['source']['full_vocabulary_cross_entropy']
        fidelity=score['fidelity'];formula_by_id={r['id']:r for r in fidelity['rows']}
        a.check(len(formula_by_id)==60 and [r['id'] for r in fidelity['rows']]==[r['id'] for r in refs],
            'all formula rows retained in fixed reference order')
        formula_counts=Counter();field_counts=Counter();join_counts={f:Counter() for f in FIELDS}
        events={(e['id'],e['slot'],e['field']):e for e in scalar['events']}
        unvisited={(e['id'],e['slot'],e['field']) for e in scalar['unvisited_reference_sites']}
        a.check(len(joined['rows'])==60 and joined['unvisited_counted_correct'] is False,'complete joined evidence with honest unvisited policy')
        for predicted,ref,joint in zip(panel['predictions'],refs,joined['rows'],strict=True):
            formula=formula_by_id[ref['id']]
            a.check(joint['id']==predicted['id']==ref['id'] and formula['expected_ir']==ref['target']
                and joint['expected_ir']==ref['target'] and joint['generated_ir']==formula['generated_ir'],
                'exact formula/ref/join identity and IR evidence')
            try:
                a.check(all(type(token) is int and 3<=token<32 for token in predicted['token_ids']),
                    'greedy output contains only declared content token IDs')
                decoded=strict_json(''.join(vocab[token] for token in predicted['token_ids']))
            except (ValueError,TypeError,KeyError,IndexError):
                decoded=None
            a.check(decoded==formula['generated_ir'],'independent strict JSON decoding of actual generated token body')
            independent_exact=predicted['eos_reached'] is True and decoded==ref['target']
            a.check(bool(formula['counts']['ordered_exact']) is independent_exact,
                'independent actual generated complete target equality with EOS')
            for name in ('ordered_exact','syntax_valid'):
                formula_counts[name]+=formula['counts'][name]
                a.check(joint['formula_'+name] is bool(formula['counts'][name]),'joined formula status')
            for field in ALL_FIELDS:
                field_counts[field]+=formula['by_facet'][field]['correct']
                a.check(formula['by_facet'][field]['total']==1,'one reference rule per facet denominator')
            for field in FIELDS:
                key_site=(ref['id'],0,field);value=joint['fields'][field]
                formula_correct=formula['by_facet'][field]['correct']==1
                a.check(value['formula_field_correct'] is formula_correct,'joined facet correctness')
                if key_site in events:
                    source_correct=events[key_site]['source']['argmax_token_id']==events[key_site]['target_token_id']
                    a.check(value['status']=='visited' and value['source_correct'] is source_correct,'joined head correctness')
                    join_counts[field]['visited']+=1
                    join_counts[field]['source_correct' if source_correct else 'source_incorrect']+=1
                    join_counts[field]['source_correct_formula_wrong']+=int(source_correct and not formula_correct)
                    join_counts[field]['source_wrong_formula_correct']+=int(not source_correct and formula_correct)
                else:
                    a.check(key_site in unvisited and value['status']=='unvisited' and value['source_correct'] is None,
                        'unvisited source site remains null')
                    join_counts[field]['unvisited']+=1
            sample_key=(entry['dimension'],entry['arm'])
            if entry['role']=='selected' and not formula['counts']['ordered_exact'] and sample_counts[sample_key]<3:
                samples.append(dict(dimension=entry['dimension'],arm=entry['arm'],id=ref['id'],
                    source_text=ref['source_text'],expected_ir=ref['target'],generated_ir=formula['generated_ir'],
                    source_head_fields=joint['fields'],formula_syntax_valid=joint['formula_syntax_valid']))
                sample_counts[sample_key]+=1
        for field in FIELDS:
            totals=dict(reference_rows=60,visited=0,unvisited=0,source_correct=0,source_incorrect=0,
                source_correct_formula_wrong=0,source_wrong_formula_correct=0)
            totals.update(join_counts[field])
            a.check(totals==joined['per_field'][field]==entry['source_head_by_field'][field],
                'independent full60 head/formula join denominators')
            a.check(totals['visited']==event_counts[field] and totals['source_correct']==correct[field],
                'head event and paired join counts agree')
        a.check(formula_counts['ordered_exact']==entry['ordered_exact']
            and formula_counts['syntax_valid']==entry['syntax_valid'],'full60 aggregate formula correctness')
        for field in ALL_FIELDS:
            a.check(field_counts[field]==fidelity['by_facet'][field]['correct']
                and fidelity['by_facet'][field]['total']==60,'complete seven-facet aggregate '+field)
        ce_rows=score['teacher_forced']['rows'];tokens=0;loss=0.0
        a.check(len(ce_rows)==60,'teacher-forced CE all60 rows')
        for ce_row,ref in zip(ce_rows,refs,strict=True):
            a.check(ce_row['id']==ref['id'] and ce_row['target_token_ids']==ref['target_ids'][1:]
                and len(ce_row['token_cross_entropies'])==ce_row['token_count']==len(ref['target_ids'])-1,
                'complete preserved reference token losses')
            row_sum=math.fsum(ce_row['token_cross_entropies']);tokens+=ce_row['token_count'];loss+=row_sum
            a.close(ce_row['cross_entropy'],row_sum/ce_row['token_count'],'CE row mean')
        a.check(tokens==score['teacher_forced']['valid_target_tokens'],'all valid token denominator')
        a.close(score['teacher_forced']['token_cross_entropy'],loss/tokens,'token CE aggregate')
        a.close(entry['token_cross_entropy'],loss/tokens,'summary token CE aggregate')
        name=f'{entry["dimension"]}:{entry["arm"]}:{entry["role"]}'
        results_summary[name]=dict(dimension=entry['dimension'],arm=entry['arm'],role=entry['role'],
            source_rows=60,formula_ordered_exact=formula_counts['ordered_exact'],
            formula_syntax_valid=formula_counts['syntax_valid'],formula_fields_correct=dict(field_counts),
            recurrent_teacher_forced_token_ce=loss/tokens,
            source_head={f:dict(visited=event_counts[f],unvisited=60-event_counts[f],
                correct=correct[f],full32V_cross_entropy_mean=(ce_sum[f]/event_counts[f] if event_counts[f] else None)) for f in FIELDS},
            source_head_formula_join=joined['per_field'],generation_seconds=entry['generation_seconds'],
            generation_seconds_per_span=entry['generation_seconds']/60,
            source_head_scoring_seconds=entry['source_head_scoring_seconds'],
            formula_scoring_seconds=entry['scoring_seconds'],
            selected_last_identical_tensor_alias=entry['selected_last_identical_tensor_alias'],
            model_tensor_sha256=saved['record']['state_ref']['tensor_sha256'],
            reconstructed_input_mse=None,reconstructed_input_mse_measured=False)
    deltas={}
    for d in (384,768):
        zero=results_summary[f'{d}:{ARMS[0]}:selected'];candidate=results_summary[f'{d}:{ARMS[1]}:selected']
        deltas[str(d)]=dict(ordered_exact_delta=candidate['formula_ordered_exact']-zero['formula_ordered_exact'],
            token_ce_delta=candidate['recurrent_teacher_forced_token_ce']-zero['recurrent_teacher_forced_token_ce'],
            modality_source_head_correct_delta=candidate['source_head']['modality']['correct']-zero['source_head']['modality']['correct'],
            modality_formula_correct_delta=candidate['formula_fields_correct']['modality']-zero['formula_fields_correct']['modality'])
    aliases={}
    for d in (384,768):
        for arm in ARMS:
            selected=index[d,arm,'selected'];last=index[d,arm,'last-attempt']
            alias=selected['record']['state_ref']['tensor_sha256']==last['record']['state_ref']['tensor_sha256']
            for role in ROLES:
                key=f'{d}:{arm}:{role}'
                a.check(results_summary[key]['selected_last_identical_tensor_alias'] is alias,
                    'selected/last tensor alias identity independently recomputed')
            identical_predictions=selected['panel']['predictions']==last['panel']['predictions']
            a.check(not alias or identical_predictions,'identical-tensor endpoints have identical deterministic greedy outputs')
            aliases[f'{d}:{arm}']=dict(identical_tensor_alias=alias,
                identical_greedy_predictions=identical_predictions,
                distinct_model_replicates=(1 if alias else 2))
    prep_manifest=a.read(root/'preparation-manifest.json')
    composition_vector_comparison={str(d):dict(composition64_literal_source_excluded=True,
        composition64_cached_vectors_available_from_prior_readiness=True,
        composition64_in_prior_vector_comparison=False,
        comparison_completeness='incomplete; no numeric comparison to composition64 bundles in this campaign') for d in (384,768)}
    for d,descriptors in prep_manifest['prior_vector_rows'].items():
        a.check(not any('/expansion/encoding-01/' in entry['path'] for entry in descriptors),
            'composition vector comparison incompleteness matches sealed descriptors')
    report=dict(schema='independent-saved-normative-wording-postfit-audit/v1',complete=True,passed=True,findings=[],
        checks=a.checks,created_utc=datetime.now(timezone.utc).isoformat(),run_root=str(root),
        evaluation_attempt=args.evaluation_attempt,panels=results_summary,selected_pair_deltas=deltas,
        selected_last_aliases=aliases,
        sampled_formula_errors=samples,saved_artifact_bindings=a.bindings,
        bridge_names=[],legal_ir_evaluate_provers=False,metric_disk_cache_used=False,
        workers=1,sample_count_per_panel=60,panel_count=8,
        decoder_cache_scope='warm verified native source vectors; no encoder forward during postfit',
        wording_literal_and_normalized_prior_overlap=0,original_meanings_previously_exposed=True,
        label_provenance='authored_development',fresh_semantic_holdout=False,
        composition64_vector_comparison=composition_vector_comparison,
        scalar_full32V_metrics_independently_recomputed=True,
        actual_formula_tokens_independently_strict_json_decoded=True,
        formula_ordered_exact_independent_target_equality_checked=True,
        teacher_forced_token_CE_checked_from_saved_losses=True,
        teacher_forced_full_logits_available=False,reconstructed_input_mse_measured=False,
        audit_model_execution=False,audit_encoder_execution=False,audit_package_imports=False,
        qualified=False,admitted=False,lake_executed=False,checkpoint_promoted=False,
        fidelity_limits='restricted seven-field authored32V IR; no richer-family or statutory semantic qualification')
    report['content_sha256']=digest(report)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as stream:
        json.dump(report,stream,sort_keys=True,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps(dict(complete=True,checks=a.checks,panels=8,selected_pair_deltas=deltas,output=str(args.output)),indent=2))
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-root',type=Path,default=DEFAULT_ROOT)
    parser.add_argument('--evaluation-attempt',default='evaluation-r1')
    parser.add_argument('--output',type=Path,default=DEFAULT_OUT)
    audit(parser.parse_args())


if __name__=='__main__':
    main()
