"""Independent saved native/source/provenance audit; no package/model imports."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import struct

ROOT = Path('/home/barberb/lift_coding'); P = ROOT / 'external/ipfs_datasets'
R = P / 'workspace/test-logs/decoder-normative-wording-r2-20261006'
A = R / 'preparation-r1'; D = A / 'results'
OUT = ROOT / 'artifacts/autoencoder-wording-fit-20261006/review'
checks = 0; bindings = {}


def check(value, label):
    global checks
    if not value: raise AssertionError(label)
    checks += 1


def raw(value): return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()
def digest(value): return hashlib.sha256(raw(value)).hexdigest()
def text_sha(value): return hashlib.sha256(value.encode()).hexdigest()
def normal(value): return ' '.join(value.casefold().split())


def bind(path, wanted=None, size=None):
    path = Path(path).resolve(); h = hashlib.sha256(); count = 0
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1048576), b''): h.update(block); count += len(block)
    result = dict(sha256=h.hexdigest(), bytes=count)
    if wanted is not None: check(result['sha256'] == wanted, 'exact artifact hash:' + str(path))
    if size is not None: check(count == size, 'exact artifact size:' + str(path))
    bindings[str(path)] = result; return result


def load(path):
    bind(path); return json.loads(Path(path).read_bytes())


def self_hash(value, key): check(value[key] == digest({k:v for k,v in value.items() if k != key}), 'content binding:' + key)


def vector(value, width):
    check(type(value) is list and len(value) == width, 'complete numerical vector width')
    check(all(type(v) in (int,float) and math.isfinite(v) for v in value), 'finite numerical vector')
    for v in value:
        check(struct.unpack('>f', struct.pack('>f', float(v)))[0] == v, 'exact float32 numerical value')
    check(abs(math.sqrt(math.fsum(float(v)*float(v) for v in value)) - 1.) <= 1e-5, 'L2 vector normalization')


VOCABULARY = ['<pad>', '<bos>', '<eos>', '"F"', '"O"', '"P"', '"action"',
    '"actor"', '"approve"', '"archive"', '"conditions"', '"deliver"', '"examine"',
    '"exceptions"', '"modality"', '"notary"', '"notice"', '"object"', '"preserve"',
    '"publish"', '"registrar"', '"rules"', '"secretary"', '"temporal"',
    '"treasurer"', '"trustee"', ',', ':', '[', ']', '{', '}']


def decode(ids):
    check(type(ids) is list and 3 <= len(ids) <= 512 and ids[0] == 1 and ids[-1] == 2,
          'complete bounded BOS/EOS target')
    check(all(type(v) is int and 3 <= v < 32 for v in ids[1:-1]), 'original32V token IDs')
    wire = ''.join(VOCABULARY[v] for v in ids[1:-1]); target = json.loads(wire)
    check(raw(target).decode() == wire, 'canonical complete target tokens')
    return target


manifest = load(R / 'preparation-manifest.json'); plan = load(R / 'preparation-plan.json')
check(bind(R / 'preparation-plan.json')['sha256'] == manifest['plan_sha256'], 'frozen plan hash')
for path,wanted in manifest['inputs'].items(): bind(path,wanted)
for path,wanted in manifest['producer_pins'].items(): bind(path,wanted)
for rel,wanted in manifest['extensions'].items(): bind(R / 'experiment-source' / rel,wanted)
summary = load(D / 'summary.json')
check(summary['complete'] is True and summary['phase'] == 'preparation' and summary['encoder_executed'] is True, 'completed native-only phase')
for key in ('qualified','admitted','training_executed','model_scoring_executed','development_reference_json_parsed',
            'downloads_performed','preprocessing_fitted','lake_executed','checkpoint_promoted','fresh_holdout','legal_ir_evaluate_provers','metric_disk_cache_used'):
    check(summary[key] is False, 'no unsupported authority:' + key)
check(summary['bridge_names'] == [] and summary['workers'] == 1 and summary['batch_size'] == 4
      and summary['context_tokens'] == summary['output_tokens'] == 512 and summary['temperature'] == 0, 'fixed diagnostic execution recipe')
for path,wanted in summary['source_dependencies'].items():
    bind(path,wanted)
    check('/HACC/' not in path and '/hallucinate_app/' not in path, 'authenticated source tree not drifted alternate parser')
source_rows = load(D / 'source-rows.json'); refs = load(D / 'training-references.json')
clause_refs = load(D / 'clause-training-references.json'); corpus = load(D / 'training-corpus-receipt.json')
bank = load(D / 'original-training-bank-used.json'); prior = load(D / 'prior-source-inventories.json')
source_plan = load(D / 'source-plan.json'); dev_plan = load(D / 'development-source-plan.json')
sealed_dev = load(manifest['development_seal']); dev_sources = load(manifest['development_sources'])
check(sealed_dev['sealed_recipe_sha256'] == dev_plan['sealed_recipe_sha256'] == '14f8a6b363580c6ed1e5556e8a5990cc187f83dfdb1b0e59ca109e57903f1474', 'proper separate future-development seal')
check(str(Path(sealed_dev['artifact_files']['references']['path']).resolve()) not in manifest['inputs'], 'newDEV reference bodies absent from native preparation inputs')
check(prior['prospective_development_sources'] == dev_sources, 'TRAIN excludes complete future source strings')
check(len(bank) == 180 and len(source_rows) == len(refs) == 48 and len(clause_refs) == 180, 'complete TRAIN derivation denominators')
check(corpus['original_train_bank_sha256'] == digest(bank) and corpus['references_sha256'] == digest(refs)
      and corpus['source_rows_sha256'] == digest(source_rows) and corpus['clause_references_sha256'] == digest(clause_refs), 'complete TRAIN corpus payload hashes')
self_hash(corpus,'receipt_sha256'); self_hash(source_plan,'plan_sha256'); self_hash(source_plan['shape_plan'],'plan_sha256'); self_hash(dev_plan,'plan_sha256')
original_rules = {}; original_sources = {}
for row in bank:
    check(set(row) == {'id','source_text','target_ids'}, 'closed original TRAIN bank row')
    target = decode(row['target_ids']); check(len(target['rules']) == 1, 'single originalTRAIN rule')
    rule = target['rules'][0]; key = digest(rule)
    original_rules[key] = rule; original_sources.setdefault(key,[]).append(dict(id=row['id'], source_sha256=text_sha(row['source_text']),
        target_sha256=digest(target), target_ids_sha256=digest(row['target_ids'])))
check(len(original_rules) == 90 and all(len(v) == 2 for v in original_sources.values()), 'exact90 originalrules with2 authenticated source renderings')
forbidden_normal = {normal(t) for rows in prior.values() for row in rows for t in [row['source_text'],*row['source_text'].split('\n\n')]}
forbidden_literal = {text_sha(t) for rows in prior.values() for row in rows for t in [row['source_text'],*row['source_text'].split('\n\n')]}
gerunds = dict(approve='approving', deliver='delivering', examine='examining', preserve='preserving', publish='publishing')
clauses = {r['id']:r for r in clause_refs}; rule_uses = Counter(); modality = Counter()
for row,ref in zip(source_rows,refs):
    check(set(row) == {'id','source_text'} and row['id'] == ref['id'] and row['source_text'] == ref['source_text'], 'source-only paragraph/reference identity')
    check(normal(row['source_text']) not in forbidden_normal and text_sha(row['source_text']) not in forbidden_literal, 'paragraph literal and normalized exclusion')
    check(decode(ref['target_ids']) == ref['target'] and digest(ref['target']) == ref['target_sha256'], 'full32V paragraph reference preservation')
    pieces = row['source_text'].split('\n\n'); check(len(pieces) == ref['clause_count'] == len(ref['target']['rules']), 'source/target clause count unchanged')
    check(len({tuple(r[k] for k in ('actor','action','object')) for r in ref['target']['rules']}) == len(pieces), 'no contradictory content group packing')
    for slot,(piece,rule,cid,derivation) in enumerate(zip(pieces,ref['target']['rules'],ref['clause_ids'],ref['derivations'])):
        key = digest(rule); item = clauses[cid]
        check(key in original_rules and rule == original_rules[key], 'every target field exactly originalTRAIN')
        check(set(rule) == {'actor','action','object','modality','conditions','exceptions','temporal'}
              and all(rule[k] == [] for k in ('conditions','exceptions','temporal')), 'complete unchanged seven-field restricted rule')
        actor,action,obj,m = (rule[k] for k in ('actor','action','object','modality'))
        if ref['template'] == 'explicit_actor_status_v1':
            expected = f'Under this regulation, the {actor} is prohibited from {gerunds[action]} the {obj}.' if m == 'F' else f'Under this regulation, the {actor} is '+{'O':'obliged','P':'authorized'}[m]+f' to {action} the {obj}.'
        else:
            check(ref['template'] == 'regulation_norm_operator_v1','exact secondTRAIN template')
            expected = (f'This regulation places a duty on the {actor} to {action} the {obj}.' if m == 'O' else
                        f'This regulation grants the {actor} permission to {action} the {obj}.' if m == 'P' else
                        f'This regulation bans the {actor} from {gerunds[action]} the {obj}.')
        check(piece == expected and normal(piece) not in forbidden_normal and text_sha(piece) not in forbidden_literal, 'exact TRAIN wording and complete clause exclusion')
        check(derivation['rule_sha256'] == key and derivation['original_train_sources'] == original_sources[key], 'two original source/target/token provenance bindings')
        check(item['parent_paragraph_id'] == row['id'] and item['slot'] == slot and item['source_text'] == piece
              and item['source_sha256'] == text_sha(piece) and item['target'] == {'rules':[rule]}
              and decode(item['target_ids']) == item['target'] and item['derivations'] == [derivation], 'complete ordered clause reference join')
        check(item['source_semantics_verified'] is False and item['qualified'] is False and item['admitted'] is False
              and item['roundtrip_ok'] is False and item['lake_executed'] is False, 'authored labels are not semantic/proof admission')
        rule_uses[key]+=1;modality[m]+=1
check(len(rule_uses) == 90 and set(rule_uses.values()) == {2} and modality == {'O':60,'P':60,'F':60}, 'complete balanced two-stratum coverage')
check(Counter(r['clause_count'] for r in refs) == {1:12,2:12,4:12,8:12}, 'complete deterministic paragraph inventory')
preseal = load(D / 'pre-native-source-seal.json')
check(preseal['complete'] and preseal['train_source_sha256'] == digest(source_rows)
      and preseal['train_reference_sha256'] == digest(refs) and preseal['development_source_sha256'] == digest(dev_sources)
      and preseal['encoder_executed'] is False and preseal['development_reference_json_parsed'] is False, 'pre-native complete source/reference seal')


def shape_check(p, rows, expected_sources):
    check(p['shape_plan']['source_rows'] == rows and all(set(r) == {'id','source_text'} for r in rows), 'closed actual source plan')
    inputs = []; aliases = []; seen = set()
    for row in rows:
        for role,slot,text in [('paragraph',None,row['source_text']),*[('clause',i,t) for i,t in enumerate(row['source_text'].split('\n\n'))]]:
            sha = text_sha(text); identity = 'source:'+sha
            if sha not in seen: seen.add(sha);inputs.append(dict(id=identity,source_text=text))
            aliases.append(dict(paragraph_id=row['id'],role=role,slot=slot,source_id=identity,source_sha256=sha))
    check(p['shape_plan']['source_inputs'] == inputs and p['shape_plan']['source_aliases'] == aliases
          and len(inputs) == expected_sources, 'full source-derived native inventory and aliases')
    check(p['target_access'] is False and p['targets_attached'] is False, 'native plan does not expose references')


shape_check(source_plan,source_rows,216); shape_check(dev_plan,dev_sources,60)
widths = {}
for width in (384,768):
    reports = {}; inputs = {}
    for kind,p,rows,count in [('train',source_plan,source_rows,216),('development',dev_plan,dev_sources,60)]:
        prefix = '' if kind == 'train' else 'development-'
        report = load(D / f'{prefix}production-{width}.json'); reports[kind] = report
        data = load(D / (f'dimension-inputs-{width}.json' if kind == 'train' else f'development-inputs-{width}.json')); inputs[kind] = data
        self_hash(report,'production_sha256'); self_hash(data,'inputs_sha256')
        check(report['receipt_count'] == len(report['vectors']) == count and report['dimension'] == width
              and report['plan_sha256'] == p['plan_sha256'] and report['source_rows_sha256'] == p['source_rows_sha256']
              and report['sealed_recipe_sha256'] == p['sealed_recipe_sha256'], 'complete ordered native report/plan binding')
        check(report['encoder_executed'] is True and report['batch_size'] == 4 and 0 < report['max_seconds'] <= 600
              and report['target_access'] is False and report['targets_attached'] is False and report['qualified'] is False
              and report['admitted'] is False and report['downloads_performed'] is False, 'actual local native-only execution and no admission')
        for path,wanted in report['producer_files'].items():bind(path,wanted)
        native = report['native_production']; source_inputs = p['shape_plan']['source_inputs']
        if width == 384:
            expected_execution = dict(backend='sentence-transformers',batch_size=4,cpu_threads=1,device='cpu',dtype='float32',
                                      eval_mode=True,gradient_mode='inference_mode',kind='native',max_tokens=512,
                                      normalization='l2',pooling='mean',seed=0,truncation=False)
            check(native['execution'] == expected_execution, 'real384 native qualified execution profile')
            check(native['model'] == dict(dimension=384,model_id='thenlper/gte-small',revision='17e1f347d17fe144873b1201da91788898c639cd'), 'pinned real384 model')
            for asset in native['model_assets']:
                bind(Path(report['asset_config']['snapshot_path']) / asset['name'], asset['sha256'], asset['bytes'])
            artifact = report['source_artifact'];bind(artifact['path'],artifact['sha256'],artifact['bytes']);blob = Path(artifact['path']).read_bytes()
            check(len(native['inputs']) == len(native['results']) == count and native['status_counts']['embedded'] == count, 'real384 complete source/results')
            native_vectors=[];token_rows=[]
            for item,result,source in zip(native['inputs'],native['results'],source_inputs):
                span=item['source'];check(item['text'] == source['source_text'] and span['document_id'] == source['id']
                    and span['release_id'] == p['sealed_recipe_sha256'] and span['normalization'] == 'identity'
                    and blob[span['byte_start']:span['byte_end']].decode() == source['source_text'], 'real384 exact byte-bound complete source')
                check(result['input_id'] == item['input_id'] and result['status'] == 'embedded', 'real384 ordered native result identity')
                encoded=result['vector'];check(encoded['dimension'] == width and encoded['encoding'] == 'float32-be-hex', 'real384 float32 byte encoding')
                native_vectors.append(list(struct.unpack('>384f',bytes.fromhex(encoded['bits']))));token_rows.append(result['tokens'])
            forward_count=None;sample_forward_observations=None
        else:
            check(native['source_rows'] == source_inputs and native['experiment_token_limit'] == 512
                  and native['historical_profile_token_limit'] == 8192 and native['cached_profile_relabelled'] is False, 'real768 exact sources and unchanged historical ceiling')
            check(native['execution_profile'] == dict(batch_size=4,device='cpu',dtype='float32',pooling='cls',normalization='l2',
                                                     max_tokens_including_special_tokens=512,attention_implementation='eager'), 'real768 exact actual execution profile')
            assets=native['assets'];check(assets['status'] == 'available' and assets['manifest_sha256'] == report['asset_config']['expected_manifest_sha256'], 'real768 complete local asset admission evidence')
            bind(report['asset_config']['manifest_path'],assets['manifest_sha256'])
            for asset in assets['files']:
                path=Path(assets[asset['relative_to']+'_directory'])/asset['path'];bind(path,asset['sha256'],asset['bytes'])
            with (Path(assets['model_directory'])/'model.safetensors').open('rb') as stream:
                header_len=struct.unpack('<Q',stream.read(8))[0];check(header_len <= 8*1024**2,'bounded safetensors header only')
                header=json.loads(stream.read(header_len))
            tensor_names=sorted(k for k in header if k!='__metadata__');loading=native['complete_checkpoint_loading']
            check(tensor_names == loading['tensor_names'] and loading['tensor_count'] == len(tensor_names) == 138, 'real768 complete saved tensor inventory matches local safetensors header')
            check(loading['architecture'] == 'NewForTokenClassification' and loading['classifier_loaded'] is True
                  and loading['classifier_logits_used_for_dense_embedding'] is False
                  and all(loading[k] == [] for k in ('missing_keys','unexpected_keys','mismatched_keys','error_msgs')), 'real768 no missing ignored classifier or encoder tensors')
            check(native['dense_path_verification']['encoder_and_complete_hidden_states_bitwise_equal'] is True
                  and native['dense_path_verification']['evaluation_mode'] is True, 'saved768 source-only dense probe equality')
            native_vectors=native['vectors'];token_rows=native['token_rows'];events=native['forward_observations']
            schedule=[('complete',[0]),('encoder',[0])]+[('complete',list(range(i,min(i+4,count)))) for i in range(0,count,4)]
            check(len(events) == len(schedule), 'real768 complete and encoder probe plus every batchforward')
            for number,(event,(role,indices)) in enumerate(zip(events,schedule)):
                padded=max(len(token_rows[i]['input_ids']) for i in indices)
                check(event['index'] == number and event['path'] == role and event['batch_size'] == len(indices)
                      and event['padded_width'] == padded <= 512 and event['actual_forward_checked'] is True, 'real768 exact bounded forward geometry')
                sources=[]
                for position,index in enumerate(indices):
                    ids=token_rows[index]['input_ids'];observed=event['input_ids'][position];mask=event['attention_mask'][position]
                    check(observed[:len(ids)] == ids and len(observed) == padded and mask == [1]*len(ids)+[0]*(padded-len(ids)), 'real768 no truncation actual active tokens')
                    sources.append(dict(id=source_inputs[index]['id'],source_sha256=text_sha(source_inputs[index]['source_text']),
                                        active_token_count=len(ids),token_input_sha256=digest(ids)))
                check(event['sources'] == sources,'real768 actualforward source and token digest identity')
            forward_count=len(events);sample_forward_observations=sum(v['batch_size'] for v in events)
            check(native['forward_validation']['forward_count'] == forward_count
                  and native['forward_validation']['sample_forward_observations'] == sample_forward_observations
                  and native['forward_validation']['maximum_forward_width'] == max(v['padded_width'] for v in events), 'independent768 forward counts match producer validation')
        check(len(native_vectors) == len(token_rows) == count, 'complete native numerical/token row inventory')
        lookup={}
        for source,result,value,tokens in zip(source_inputs,report['vectors'],native_vectors,token_rows):
            vector(value,width);ids=tokens['input_ids']
            check(type(ids) is list and 1 <= len(ids) <= 512 and all(type(i) is int and i>=0 for i in ids), 'complete untruncated actual native token IDs')
            check(tokens['attention_mask'] == [1]*len(ids), 'all actual source tokens active')
            check(result == dict(id=source['id'],source_sha256=text_sha(source['source_text']),vector=value,
                                 token_count=len(ids),token_input_sha256=digest(ids)), 'report matches full saved native source/vector/token numerical data')
            lookup[source['source_text']]=value
        check(data['production_sha256'] == report['production_sha256'] and data['source_plan_sha256'] == p['plan_sha256'], 'raw assembled data report and plan provenance')
        check(len(data['rows']) == len(rows) and len(data['clause_cache']) == (180 if kind=='train' else 60)
              and set(data['source_contexts']) == {r['id'] for r in rows}, 'complete raw rows caches and source context inventory')
        for actual,source in zip(data['rows'],rows):
            check(set(actual) == {'id','source_text','input'} and actual['id'] == source['id'] and actual['source_text'] == source['source_text']
                  and actual['input'] == lookup[source['source_text']], 'source-only assembled paragraph exact native vector')
            pieces=source['source_text'].split('\n\n');context=data['source_contexts'][source['id']]
            check(context['source_sha256'] == text_sha(source['source_text']) and len(context['segments']) == len(pieces), 'full paragraph source descriptor')
            char=byte=0
            for piece,segment in zip(pieces,context['segments']):
                check(segment == dict(source_text=piece,source_sha256=text_sha(piece),embedding_sha256=digest(lookup[piece]),vector=lookup[piece],
                                      char_start=char,char_end=char+len(piece),byte_start=byte,byte_end=byte+len(piece.encode())), 'literal prefix and complete clause/vector/offset joins')
                char+=len(piece)+2;byte+=len(piece.encode())+2
        for cached in data['clause_cache']:
            check(set(cached) == {'id','source_text','input'} and cached['id'] == 'clause:'+text_sha(cached['source_text'])
                  and cached['input'] == lookup[cached['source_text']], 'cached complete clause bytes and unchanged raw native vector')
        widths.setdefault(str(width),{})[kind]=dict(unique_sources=count,seconds=report['elapsed_seconds'],seconds_per_unique_source=report['elapsed_seconds']/count,
            actual_tokens_min=min(len(t['input_ids']) for t in token_rows),actual_tokens_max=max(len(t['input_ids']) for t in token_rows),
            actual_forward_count=forward_count,sample_forward_observations=sample_forward_observations,production_sha256=report['production_sha256'])
    combined=[tuple(v['vector']) for r in reports.values() for v in r['vectors']]
    check(len(combined) == len(set(combined)) == 276,'all276 actual new native vectors unique atwidth'+str(width))
    old=[]
    for descriptor in manifest['prior_vector_rows'][str(width)]:
        values=load(descriptor['path'])
        for key in descriptor['keys']:values=values[key]
        old.extend(tuple(row['input']) for row in values)
    check(not set(old).intersection(combined) and len(old) == summary['outputs'][str(width)]['prior_vector_rows']
          and len(set(old)) == summary['outputs'][str(width)]['prior_unique_vectors'],'no vector identity overlap within declared frozen inventory')
    widths[str(width)]['prior_vector_rows']=len(old);widths[str(width)]['prior_unique_vectors']=len(set(old))
    for role,reference in summary['outputs'][str(width)].items():
        if type(reference) is dict and {'path','bytes','sha256'} <= set(reference):bind(reference['path'],reference['sha256'],reference['bytes'])
outer=load(R/'preparation-r1-guardian-exit.json');child=load(A/'child-exit.json');final=load(A/'resources-final.json')
check(outer['returncode'] == child['returncode'] == 0 and child['leader_reaped'] is True,'actual guardian/child successful exits')
record=final['record'];check(final['status'] == record['status'] == 'released' and record['artifacts_durable_asserted'] is True
    and record['final_total_charged_bytes'] == record['final_attempt_bytes'] == 28606836
    and record['attempt_exceeded_reservation'] is False, 'owned completed durable attempt released within100MB')
check(final['storage_limit_bytes'] == record['final_accounting']['limit_bytes'] == 145000000000
    and record['final_accounting']['charged_bytes'] == 141167973457, 'actual final campaign accountingcapunchanged')
observations=load(A/'resource-observations.json');peak=max(o['group_rss']['rss_bytes'] for o in observations if o['group_rss']['available'])
check(all(o['group_rss']['rss_bytes'] <= o['memory_limit_bytes'] for o in observations if o['group_rss']['available']), 'sampled actual live group RSS within4096MiB')
lease_path=R/'preparation-r1-lease-observations.jsonl';bind(lease_path)
lease_events=[json.loads(line) for line in lease_path.read_text().splitlines()];observed=[r for r in lease_events if r.get('schema')=='guardian-owned-lease-observation/v1']
check(all(r['healthy'] and r['configuration_matches'] and r['read_only'] for r in observed)
    and observed[-1]['expected']=='absent' and observed[-1]['lease_present'] is False, 'healthy sampled owned lease then observedrelease')
maximum_lease_gap=max(b['observed_at_monotonic']-a['observed_at_monotonic'] for a,b in zip(observed,observed[1:]))
bind(Path(__file__))
report=dict(schema='normative-wording-native-preparation-audit/v1',passed=True,findings=[],checks=checks,
    created_at=datetime.now(timezone.utc).isoformat(),artifacts=bindings,dimensions=widths,
    driver_elapsed_seconds=summary['elapsed_seconds'],guardian_elapsed_seconds=outer['elapsed_seconds'],
    resources=dict(status=final['status'],retained_attempt_bytes=record['final_attempt_bytes'],sampled_group_rss_bytes_max=peak,
        rss_samples=len(observations),absolute_peak_claimed=False,lease_observations=len(observed),maximum_sampled_lease_gap_seconds=maximum_lease_gap,
        continuous_lease_coverage_claimed=False,charged_campaign_bytes=record['final_accounting']['charged_bytes'],cap_bytes=145000000000),
    scope=dict(source_rows_train=48,unique_original_train_rules=90,original_train_sources=180,TRAINunique_clauses=180,
        development_single_sources=60,native_unique_sources_per_width=276,source_only_native_inputs=True,
        development_reference_bodies_read_by_auditor=False,development_reference_bodies_preparation_inputs=False,
        historical768profile_limit=8192,actual_experiment_token_limit=512,historical_profile_relabelled=False,
        cache_scope=summary['cache_scope'],worker_count=1,bridge_names=[],provers=False,metric_disk_cache=False,
        incomplete_all_prior_vector_coverage=True,composition64_native_vectors_available_but_not_compared=True,
        composition64_source_exclusion_complete=True),
    limitations=['This audits saved recorded runtime, asset and numerical consistency; it does not supply cryptographic kernel attestation or independent source-semantic review.',
                 '384 receipt records the qualified native execution profile and actual token/vector outputs; it lacks a separate per-forward observation stream comparable to768.',
                 'Availablecomposition64 vector inventories remain outside the declared prior-vector comparison contract. Its64 complete sources are excluded; historical8192 profile identity is preserved.',
                 'TRAINtargets preserve authored original90 rules with empty qualifiers. This establishes no richer semantics, full logic-family coverage, fresh semantic holdout, Lake admission or Constitution formalization.',
                 'Preparation is local-only. No Hub upload, checkpoint promotion, autoencoder fit or compiler/decompiler fidelity test occurred.'],
    auditor_encoder_execution=False,auditor_model_load=False,auditor_training=False,qualified=False,admitted=False,lake_executed=False)
destination=OUT/'native_preparation_audit.json'
with destination.open('x') as stream:json.dump(report,stream,indent=2,sort_keys=True);stream.write('\n')
print(json.dumps(dict(path=str(destination),sha256=bind(destination)['sha256'],passed=True,checks=checks,widths=widths,sampled_group_rss_bytes_max=peak),sort_keys=True))
