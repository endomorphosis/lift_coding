"""Independent completed native384 preflight audit; standard library only.

Never import numerical owners, execute models, or consult live scheduler state.
The explicit completion flag is mandatory before any attempt output is read.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import time

FIELDS = ("actor", "action", "modality", "object")
FACETS = ("modality", "actor", "action", "object", "conditions", "exceptions", "temporal")
ROLES = ("control", "balanced")
PARENT = "0b3c7c3b1a5581cd393d9bb8db1d24b87fe2cb9dff0be268aa2b5ed1f88b6594"
FALSE = {"qualified", "admitted", "proof_authority", "source_semantics_verified", "formalized",
         "checkpoint_promoted", "train_eligible", "training_executed", "encoder_executed",
         "downloads_performed", "used_for_selection", "recurrent_clause_effect_causally_isolated"}


def raw(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(value):
    return hashlib.sha256(raw(value).encode()).hexdigest()


def f32(value):
    return struct.unpack("<f", struct.pack("<f", value))[0]


def vector32(values):
    if type(values) is not list or len(values) != 32 or any(type(v) not in (int, float) or not math.isfinite(v) for v in values):
        raise ValueError("Expected 32 finite unrestricted logits")
    return values


def metrics(values, target, emitted=None):
    values = vector32(values)
    if type(target) is not int or not 0 <= target < 32:
        raise ValueError("Target outside full32 vocabulary")
    winner = max(range(32), key=values.__getitem__)
    emitted = winner if emitted is None else emitted
    peak = max(values)
    return dict(argmax_token_id=winner,
                full_vocabulary_cross_entropy=peak + math.log(math.fsum(math.exp(v-peak) for v in values))-values[target],
                target_minus_best_other=values[target]-max(v for i, v in enumerate(values) if i != target),
                target_minus_emitted=values[target]-values[emitted])


def close(actual, expected, tolerance=1e-12):
    if type(expected) is dict:
        return type(actual) is dict and all(k in actual and close(actual[k], v, tolerance) for k, v in expected.items())
    if type(expected) is float:
        return type(actual) in (int, float) and math.isclose(actual, expected, rel_tol=tolerance, abs_tol=tolerance)
    return type(actual) is type(expected) and actual == expected


def false_masks(value):
    if type(value) is dict:
        for k, v in value.items():
            if k in FALSE and v is not False:
                raise ValueError("Unsupported qualification/update flag: " + k)
            false_masks(v)
    elif type(value) is list:
        for child in value:
            false_masks(child)


def unique(items, key):
    result = {}
    for item in items:
        identity = key(item)
        if identity in result:
            raise ValueError("Duplicate identity: " + str(identity))
        result[identity] = item
    return result


def causal_sites(prefix, vocabulary):
    """Pure lexical recognition of consumed prefixes, without target access.

    Six-state grammar follows the frozen scalar/cardinality routing declaration.
    A quoted field name in a value cannot produce an additional field site.
    """
    ids = {token: vocabulary.index(token) for token in ["{", "}", "[", "]", ":", ",", '"rules"', *[json.dumps(f) for f in FACETS]]}
    strings = {}
    for i, token in enumerate(vocabulary):
        if token.startswith('"'):
            value = json.loads(token)
            if type(value) is str:
                strings[i] = value
    ranks = {s: i+1 for i, s in enumerate(sorted(set(strings.values())))}
    state, sites, invalid = [0]*6, [], None
    for position, token in enumerate(prefix):
        if type(token) is not int or not 0 <= token < len(vocabulary):
            raise ValueError("Prefix token outside codec")
        before = list(state)
        phase, seen, pending, count, length, last = state
        rank = ranks.get(strings.get(token), 0)
        field = FACETS.index(strings[token]) if strings.get(token) in FACETS else -1
        following = 18
        if phase == 0 and token == 1: following = 1
        elif phase == 1 and token == ids['{']: following = 2
        elif phase == 2 and token == ids['"rules"']: following = 3
        elif phase == 3 and token == ids[':']: following = 4
        elif phase == 4 and token == ids['[']: following = 5
        elif phase in (5, 14) and token == ids['{']: following, seen = 6, 0
        elif phase == 6 and field >= 0 and not seen & (1 << field): following, seen, pending = 7, seen | (1 << field), field
        elif phase == 7 and token == ids[':']: following = 8
        elif phase == 8:
            if pending < 4 and rank > 0 and (pending != 0 or strings[token] in ('O', 'P', 'F')): following = 9
            elif pending >= 4 and token == ids['[']: following, length, last = 10, 0, 0
        elif phase == 10 and token == ids[']']: following = 9
        elif phase in (10, 12) and rank > last and rank > 0 and length < 4: following, length, last = 11, length+1, rank
        elif phase == 11 and token == ids[',']: following = 12
        elif phase == 11 and token == ids[']']: following = 9
        elif phase == 9 and token == ids[',']: following = 6
        elif phase == 9 and seen == 127 and token == ids['}']: following, count = 13, count+1
        elif phase == 13 and token == ids[',']: following = 14
        elif phase == 13 and token == ids[']']: following = 15
        elif phase == 15 and token == ids['}']: following = 16
        elif phase == 16 and token == 2: following = 17
        elif phase == 17 and token == 0: following = 17
        state = [following, seen, pending, count, length, last]
        if before[0] == 7 and following == 8 and FACETS[pending] in FIELDS and before[3] < 32:
            sites.append(dict(position=position, slot=before[3], field=FACETS[pending], grammar_before=before, grammar_after=list(state)))
        if following == 18 and invalid is None:
            invalid = position
    return sites, invalid


class Reader:
    def __init__(self): self.bindings = {}

    def body(self, path, wanted=None):
        path = Path(path)
        if path.is_symlink() or not path.is_file():
            raise ValueError("Expected direct regular artifact: " + str(path))
        before = path.stat(); body = path.read_bytes(); after = path.stat()
        if (before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
            raise ValueError("Artifact changed during audit")
        bound = dict(sha256=hashlib.sha256(body).hexdigest(), bytes=len(body))
        self.bindings[str(path)] = bound
        if wanted and any(bound[k] != wanted[k] for k in wanted if k in bound):
            raise ValueError("Artifact preimage differs: " + str(path))
        return body

    def json(self, path, wanted=None): return json.loads(self.body(path, wanted))
    def ref(self, ref): return self.json(ref['path'], ref)




def audit_dual_preparation(reader, summary, banks, pairing, inventories, readouts, check):
    """Recount new dual ledger/cache/detached dispatch from saved data only."""
    schedule = reader.ref(summary['dual_source_schedule'])
    check('Actual dual schedule seal andfixed170/1020',schedule['schedule_sha256']==digest({k:v for k,v in schedule.items() if k!='schedule_sha256'}) and schedule['optimizer_steps']==170 and schedule['auxiliary_clause_presentations']==1020 and schedule['seed']==1729 and schedule['source_auxiliary_weight']==.05 and schedule['first_bank']=='control' and schedule['original_pairing_sha256']==pairing['pairing_sha256'] and schedule['full_vocabulary_size']==32 and schedule['encoder_context_tokens']==512 and len(schedule['draws'])==170)
    exposures={r:Counter() for r in ROLES}; updates=Counter(); templates=Counter();modalities=Counter()
    for t,draw in enumerate(schedule['draws']):
        role='control' if t%2==0 else 'balanced';local=t//2;indices=[o[local%30] for o in pairing['orders'][role]];rows=[banks[role]['rows'][i] for i in indices]
        check('Dual canonical global/local source draw '+str(t),draw['global_committed_step']==t and draw['bank_role']==role and draw['bank_local_committed_step']==local and draw['indices']==indices and draw['selected_bank_sha256']==banks[role]['bank_sha256'] and draw['row_ids']==[r['id'] for r in rows] and draw['source_sha256']==[r['source_sha256'] for r in rows] and draw['original_rule_sha256']==[digest(r['target']) for r in rows] and draw['template_slots']==[0,1,0,1,0,1] and draw['templates']==[r['template'] for r in rows] and draw['modalities']==[r['modality'] for r in rows] and draw['target_token_ids']==[r['modality_token_id'] for r in rows])
        if t%2:check('Dual adjacent genuine meaning/template slots '+str(t),draw['original_rule_sha256']==schedule['draws'][t-1]['original_rule_sha256'])
        updates[role]+=1;exposures[role].update(draw['row_ids']);templates.update(draw['templates']);modalities.update(draw['modalities'])
    check('Dual85updates510presentations255pertemplatefull180coverage',dict(updates)==schedule['updates_per_bank']=={r:85 for r in ROLES} and schedule['presentations_per_bank']=={r:510 for r in ROLES} and all(len(c)==180 and sum(c.values())==510 and Counter(c.values())=={3:150,2:30} and dict(c)==schedule['per_source_exposures'][r] for r,c in exposures.items()) and dict(templates)==schedule['presentations_per_actual_template'] and len(templates)==4 and set(templates.values())=={255} and dict(modalities)==schedule['presentations_per_modality']=={'O':340,'P':340,'F':340})
    envelope=reader.ref(summary['dual_source_inventory'])
    check('Dual distinct genuine control13balanced16 envelope preserved',envelope['schema']=='dual-authored-wording-source-inventories/v1' and envelope['payload_sha256']==digest({k:v for k,v in envelope.items() if k!='payload_sha256'}) and envelope['inventories_by_role']==inventories and len(inventories['control']['prior_sources_by_dataset'])==13 and len(inventories['balanced']['prior_sources_by_dataset'])==16)
    cache=reader.ref(summary['parent_dual_cache_receipt'])
    check('One-model cache pair no additional model/tensorcopy',cache['schema']=='dual-authored-wording-modality-cache/v1' and cache['schedule_sha256']==schedule['schedule_sha256'] and cache['bank_count']==2 and cache['max_optimizer_steps']==170 and cache['max_local_uses_per_bank']==85 and cache['authentic_cache_handles_retained'] is True and cache['model_copied'] is cache['tensors_copied'] is cache['prepared_caches_mutated'] is False and set(cache['authentic_caches_by_role'])==set(ROLES))
    for role,c in cache['authentic_caches_by_role'].items():
        check('Each actual authentic paired cache receipt '+role,c['bank_sha256']==banks[role]['bank_sha256'] and c['dimension']==384 and c['max_optimizer_steps']==170 and c['full_vocabulary_size']==32 and c['pairing_sha256']==pairing['pairing_sha256'] and c['pairing_role']==role and c['orders']==pairing['orders'][role] and c['fresh_immutable_cache'] is True and c['model_copied'] is c['tensors_copied'] is c['prepared_cache_mutated'] is False)
        check('Each cache source row inventory '+role,c['row_inventory']==[{k:r[k] for k in ('id','source_sha256','input_sha256','target_sha256','modality','template','modality_token_id')} for r in banks[role]['rows']])
    check('Real cached tensor memory pair sum',cache['cached_tensor_bytes']==sum(c['cached_tensor_bytes'] for c in cache['authentic_caches_by_role'].values()) and cache['cached_tensor_bytes']==4982400)
    refs=summary['parent_dual_detached_losses'];check('Exactlytwo independent detached parent forwards',len(refs)==2)
    for t,ref in enumerate(refs):
        wrapper=reader.ref(ref);draw=schedule['draws'][t];role=draw['bank_role'];receipt=wrapper['authentic_receipt']
        check('Actual detached dispatch global'+str(t),wrapper['schema']=='dual-authored-wording-modality-loss/v1' and wrapper['global_committed_step']==t and wrapper['bank_role']==role and wrapper['bank_local_committed_step']==0 and wrapper['selected_bank_sha256']==banks[role]['bank_sha256'] and wrapper['schedule_sha256']==schedule['schedule_sha256'] and wrapper['authentic_receipt_sha256']==digest(receipt) and wrapper['local_receipt_relabelled'] is False and wrapper['source_head_forward_calls']==1 and wrapper['sampler_state_advanced'] is False)
        check('Authentic local0 full32 detached receipt '+role,receipt['committed_step']==0 and receipt['bank_sha256']==banks[role]['bank_sha256'] and receipt['gradient_enabled'] is False and receipt['full_vocabulary_size']==32 and receipt['batch_size']==6 and receipt['source_slot']==0 and receipt['source_head_forward_calls']==1 and receipt['recurrent_forward_calls']==receipt['count_forward_calls']==0 and receipt['labels_passed_to_model'] is receipt['model_copied'] is receipt['sampler_state_advanced'] is False and all(receipt[k]==draw[k] for k in ('indices','row_ids','source_sha256','target_token_ids')))
        logits=receipt['full_vocabulary_logits'];targets=receipt['target_token_ids'];losses=receipt['per_row_cross_entropy'];check('Allsix full32 detached observations '+role,len(logits)==len(targets)==len(losses)==6)
        expected=[metrics(v,target) for v,target in zip(logits,targets,strict=True)]
        check('Actual detached CEmean andargmax arithmetic '+role,all(math.isclose(loss,x['full_vocabulary_cross_entropy'],rel_tol=2e-5,abs_tol=2e-6) for loss,x in zip(losses,expected)) and math.isclose(receipt['mean_cross_entropy'],math.fsum(losses)/6,rel_tol=2e-5,abs_tol=2e-6) and receipt['correct']==sum(x['argmax_token_id']==target for x,target in zip(expected,targets)))
        source_by_id={row['row_id']:row for row in readouts[role]['rows']}
        check('Detached loss logitsmatch real same-parent bank readout '+role,all(close(v,source_by_id[identity]['fields']['modality']['full32_logits'],tolerance=2e-6) for identity,v in zip(receipt['row_ids'],logits)))
        false_masks(wrapper)
    false_masks(cache);false_masks(envelope);false_masks(schedule)
    return dict(schedule_sha256=schedule['schedule_sha256'],planned_training_updates=170,planned_auxiliary_presentations=1020,updates_per_bank=dict(updates),presentations_per_bank={r:sum(c.values()) for r,c in exposures.items()},actual_templates=dict(templates),all180_sources_per_bank_presented_two_or_three_times_in_declared_training=True,fitting_updates_executed_by_preflight=0,parent_detached_source_head_forwards=2,parent_detached_full32_clause_observations=12,parent_detached_forward_commits=0,cache_tensor_bytes=cache['cached_tensor_bytes'],cache_handle_identity_scope='Authenticated execution receipts plus independently reviewed immutable source; no live tensor object is imported by this audit.',qualified=False,admitted=False,proof_authority=False)


def audit(attempt, output, completion):
    if not completion:
        raise ValueError("Explicit root completion signal required before reading attempt outputs")
    started = time.monotonic(); attempt = Path(attempt).resolve(); run = attempt.parent
    if not re.fullmatch(r'preflight-384-r[1-9][0-9]*', attempt.name):
        raise ValueError("Explicit native384 preflight attempt required")
    reader = Reader(); checks = []
    def check(name, ok, details=None):
        if not ok: raise ValueError(name)
        item = dict(check=name, passed=True)
        if details is not None: item['details'] = details
        checks.append(item)
    manifest = reader.json(run / 'training-manifest.json')
    plan = reader.json(run / 'training-plan.json')
    check('Frozen plan/manifest exact', manifest['plan_sha256'] == reader.bindings[str(run / 'training-plan.json')]['sha256'] and plan['input_sha256'] == manifest['inputs'])
    for path, wanted in manifest['inputs'].items(): reader.body(path, {'sha256': wanted})
    for rel, wanted in manifest['extensions'].items(): reader.body(run / 'experiment-source' / rel, {'sha256': wanted})
    check('All declared inputs and private extensions unchanged', True, dict(inputs=len(manifest['inputs']), extensions=len(manifest['extensions'])))
    results = attempt / 'results'; summary = reader.json(results / 'summary.json')
    check('Exact zero-fit preflight profile and completion', summary['complete'] is True and summary['phase'] == 'preflight' and summary['dimension'] == 384 and summary['training_executed'] is False and summary['optimizer_steps'] == summary['fits'] == 0 and summary['checkpoint_selected'] is False and summary['runs'] == [] and summary['parent_tensor_sha256'] == PARENT and summary['native_context_tokens'] == summary['output_tokens'] == 512 and summary['temperature'] == 0 and summary['full_vocabulary_size'] == 32)
    check('Explicit inherited metadata and source-only generation', summary['inherited_TRAIN_validation_metadata_loaded'] is True and summary['labels_or_counts_supplied_to_generation'] is False and summary['qualification_granted'] is False)
    false_masks(summary)
    parent = reader.json(manifest['parent_summary'])
    state = reader.ref(parent['states']['selected'])
    codec, transform = state['codec'], state['input_transform']; vocabulary = codec['target_vocabulary']
    check('Selected E384 state and exact serialized weights unchanged', state['tensor_sha256'] == parent['states']['selected']['tensor_sha256'] == PARENT and state['weights_sha256'] == digest(state['model_state']) and len(vocabulary) == 32 and vocabulary[:3] == ['<pad>', '<bos>', '<eos>'])
    # State bytes are authenticated; no resident tensor is reconstructed here.
    parity = reader.ref(summary['initial_parity'])
    check('Parent original validation parity receipt', parity['predictions_equal'] is True and parity['model_tensor_sha256'] == PARENT and parity['rows'] == 48)
    archived = reader.ref(parent['postfit']['selected']['validation'])
    check('Archived validation panel complete', len(archived['predictions']) == 48)
    original = reader.json(manifest['original90_rules'])
    originals = unique(original, digest)
    check('Original90 exact seven-facet target census', len(originals) == 90 and Counter(r['modality'] for r in original) == {'O': 30, 'P': 30, 'F': 30} and all(set(r) == set(FACETS) and all(r[f] == [] for f in FACETS[4:]) for r in original))
    inventories = {role: reader.json(manifest['source_inventories'][role]) for role in ROLES}
    banks, readouts, bank_summaries, mappings = {}, {}, {}, {}
    for role in ROLES:
        inv = inventories[role]
        check('Authentic source inventory: ' + role, inv['payload_sha256'] == digest({k: v for k, v in inv.items() if k != 'payload_sha256'}))
        bank = banks[role] = reader.json(results / (role + '-bank.json'))
        observed = readouts[role] = reader.ref(summary['source_bank_readouts'][role])
        check('Full180/720 bank and source readout: ' + role, bank['bank_sha256'] == digest({k: v for k, v in bank.items() if k != 'bank_sha256'}) and bank['dimension'] == 384 and len(bank['rows']) == observed['row_count'] == 180 and observed['reference_fields'] == 720 and observed['model_tensor_sha256'] == PARENT and observed['complete'] is True and observed['extra_source_forwards'] == observed['optimizer_steps'] == 0 and observed['source_targets_joined_after_numeric_return'] is True)
        templates = sorted({r['template'] for r in bank['rows']})
        check('Six full30 source strata: ' + role, len(templates) == 2 and Counter((r['modality'], r['template']) for r in bank['rows']) == Counter({(m, t): 30 for m in ('O', 'P', 'F') for t in templates}))
        by_clause = unique(inv['clause_training_references'], lambda r: r['source_text'])
        mapping = mappings[role] = {}
        field_rows = defaultdict(list); wrong = []
        check('Authentic sorted180 source IDs: ' + role, [r['id'] for r in bank['rows']] == sorted({r['id'] for r in bank['rows']}))
        for row, seen in zip(bank['rows'], observed['rows'], strict=True):
            source_sha = hashlib.sha256(row['source_text'].encode()).hexdigest(); identity = digest(row['target']); ref = by_clause[row['source_text']]
            segment = next(s for s in inv['source_inputs']['source_contexts'][row['parent_id']]['segments'] if s['source_sha256'] == source_sha)
            check('Bank source/target/native-vector binding: ' + row['id'], row['id'] == 'clause:' + source_sha and row['source_sha256'] == source_sha and identity in originals and originals[identity] == row['target'] and row['modality'] == row['target']['modality'] and ref['target'] == {'rules': [row['target']]} and ref['source_sha256'] == source_sha and ref['parent_paragraph_id'] == row['parent_id'] and seen['row_id'] == row['id'] and seen['source_sha256'] == source_sha and seen['original_rule_sha256'] == identity and seen['template'] == row['template'] and len(row['input']) == 384 and row['input'] == segment['vector'] and row['input_sha256'] == segment['embedding_sha256'] == digest(row['input']) and row['target_sha256'] == digest({'rules': [row['target']]}))
            for field in FIELDS:
                value = seen['fields'][field]; target = vocabulary.index(json.dumps(row['target'][field], ensure_ascii=False, separators=(',', ':')))
                expected = metrics(value['full32_logits'], target)
                check('Full32 source scalar: ' + role + '/' + row['id'] + '/' + field, value['target_token_id'] == target and value['correct'] is (expected['argmax_token_id'] == target) and close(value, dict(argmax_token_id=expected['argmax_token_id'], margin=expected['target_minus_best_other'], cross_entropy=expected['full_vocabulary_cross_entropy'])))
                field_rows[field].append(value)
                if not value['correct']:
                    wrong.append(dict(row_id=row['id'], source_text=row['source_text'], template=row['template'], field=field, expected=row['target'][field], predicted=json.loads(vocabulary[value['argmax_token_id']]) if vocabulary[value['argmax_token_id']].startswith('"') else vocabulary[value['argmax_token_id']], margin=value['margin'], cross_entropy=value['cross_entropy']))
        computed = {f: dict(correct=sum(v['correct'] for v in vals), total=180, cross_entropy=math.fsum(v['cross_entropy'] for v in vals)/180, minimum_target_margin=min(v['margin'] for v in vals)) for f, vals in field_rows.items()}
        check('Source-bank summary exact: ' + role, close(observed['by_field'], computed) and summary['initial_bank_source_scalar_metrics'][role] == observed['by_field'])
        inherited = observed['inherited_modality_readout']
        check('Inherited modality pass exact provenance: ' + role, inherited['bank_sha256'] == bank['bank_sha256'] and inherited['model_tensor_sha256'] == PARENT and inherited['source_head_forward_calls'] == 30 and inherited['optimizer_steps'] == 0 and inherited['full_vocabulary_size'] == 32 and inherited['complete'] is True)
        groups = defaultdict(list)
        for source, seen, value in zip(bank['rows'], inherited['rows'], field_rows['modality'], strict=True):
            check('Inherited modality exact stored logits: ' + source['id'], seen['id'] == source['id'] and seen['target_token_id'] == value['target_token_id'] and seen['full_vocabulary_logits'] == value['full32_logits'] and seen['correct'] is value['correct'] and math.isclose(seen['cross_entropy'], value['cross_entropy'], rel_tol=1e-5, abs_tol=1e-6))
            for key in ('all', 'modality:' + source['modality'], 'template:' + source['template'], 'stratum:' + source['modality'] + ':' + source['template']): groups[key].append(seen)
        check('Inherited modality groups complete: ' + role, set(inherited['groups']) == set(groups) and all(close(inherited['groups'][k], dict(rows=len(rows), correct=sum(r['correct'] for r in rows), cross_entropy=sum(r['cross_entropy'] for r in rows)/len(rows))) for k, rows in groups.items()))
        receipt = reader.json(results / (role + '-paired-cache-receipt.json'))
        check('Fresh immutable cache handle receipt: ' + role, receipt['bank_sha256'] == bank['bank_sha256'] and receipt['fresh_immutable_cache'] is True and receipt['prepared_cache_mutated'] is False and receipt['model_copied'] is receipt['tensors_copied'] is receipt['source_hashes_relabelled'] is False)
        false_masks(observed); false_masks(bank)
        bank_summaries[role] = dict(clauses=180, source_scalar_sites=720, by_field=computed, all_four_correct=all(v['correct'] == 180 for v in computed.values()), wrong_sites=wrong, emitted_formulas_measured=False)
    pairing = reader.ref(summary['pairing'])
    check('Sealed paired original-rule schedule', pairing['pairing_sha256'] == digest({k: v for k, v in pairing.items() if k != 'pairing_sha256'}) and pairing['original_rules_sha256'] == digest(original) and pairing['steps'] == 170 and pairing['seed'] == 1729 and pairing['presentations_per_role'] == 1020 and pairing['rows_per_role'] == 180)
    for role in ROLES:
        bank = banks[role]; templates = pairing['banks'][role]['templates']; mapping = mappings[role]
        for i, (row, census) in enumerate(zip(bank['rows'], pairing['census'][role], strict=True)):
            slot = templates.index(row['template']); key = (digest(row['target']), slot)
            if key in mapping: raise ValueError('Duplicate original-rule/template slot')
            mapping[key] = i
            check('Complete paired census: ' + role + '/' + str(i), census == dict(index=i, row_id=row['id'], source_sha256=row['source_sha256'], original_rule_sha256=key[0], template_slot=slot, template=row['template'], modality=row['modality']))
        check('Complete90x2 target/template coverage: ' + role, set(mapping) == {(identity, slot) for identity in originals for slot in (0, 1)})
        orders = [[mapping[identity, slot] for identity in sorted((k for k, r in originals.items() if r['modality'] == m), key=lambda k: digest([1729, m, slot, k]))] for m in ('O', 'P', 'F') for slot in (0, 1)]
        check('Canonical six-stratum paired order: ' + role, pairing['orders'][role] == orders and pairing['banks'][role]['bank_sha256'] == bank['bank_sha256'])
        receipt = reader.json(results / (role + '-paired-cache-receipt.json'))
        check('Cache uses exact paired schedule: ' + role, receipt['orders'] == orders and receipt['pairing_sha256'] == pairing['pairing_sha256'] and receipt['pairing_role'] == role)
    for step, draw in enumerate(pairing['draws']):
        ids = []
        for role in ROLES:
            indices = [order[step % 30] for order in pairing['orders'][role]]
            check('Paired draw ' + role + '/' + str(step), draw['step'] == step and draw['indices'][role] == indices)
            ids.append([digest(banks[role]['rows'][i]['target']) for i in indices])
        check('Matched original identities draw ' + str(step), ids[0] == ids[1] == draw['original_rule_sha256'])
    check('All170 declared draws not executed fits', len(pairing['draws']) == 170 and summary['optimizer_steps'] == 0)
    false_masks(pairing)
    dual = audit_dual_preparation(reader, summary, banks, pairing, inventories, readouts, check)
    data = reader.json(manifest['balanced_source_inputs']); rows = data['rows']; contexts = data['source_contexts']
    refs = inventories['balanced']['corpus']['references']; refmap = unique(refs, lambda r: r['id'])
    check('Balanced source-only48 and complete180 target rules', data == inventories['balanced']['source_inputs'] and data['targets_attached'] is False and data['inputs_sha256'] == digest({k: v for k, v in data.items() if k != 'inputs_sha256'}) and len(rows) == len(refs) == len(contexts) == 48 and sum(len(r['target']['rules']) for r in refs) == 180 and all(set(row) == {'id', 'source_text', 'input'} for row in rows))
    trace = reader.ref(summary['balanced48_actual_greedy_trace']); predictions = reader.ref(summary['balanced48_actual_predictions']); scalar = reader.ref(summary['balanced48_posthoc_scalar_scores']); fidelity = reader.ref(summary['balanced48_posthoc_formula_fidelity'])
    check('Frozen-parent same-pass trace identity', trace['trace_sha256'] == digest({k: v for k, v in trace.items() if k != 'trace_sha256'}) and trace['sample_count'] == 48 and trace['vocabulary_size'] == 32 and trace['max_target_tokens'] == 512 and trace['batch_size'] == 8 and trace['generation_temperature'] == 0 and trace['model_tensor_sha256'] == predictions['model_tensor_sha256'] == PARENT and trace['codec_sha256'] == digest(codec) and trace['input_transform_sha256'] == digest(transform) and trace['source_rows_sha256'] == predictions['source_rows_sha256'] == digest(rows) and trace['source_contexts_sha256'] == predictions['source_contexts_sha256'] == digest(contexts) and predictions['same_pass_trace_sha256'] == trace['trace_sha256'] and predictions['predictions'] == trace['predictions'])
    check('No target/prefix/mask supplied and no extra pass', all(trace[k] is False for k in ('reference_count_access', 'reference_prefix_access', 'reference_documents_passed_to_model', 'inventory_access', 'source_context_target_access', 'syntax_mask', 'forced_closure', 'model_copied')) and all(trace[k] is True for k in ('full_vocabulary_retained', 'decomposition_exact', 'source_only', 'caller_state_preserved', 'hooks_removed', 'complete_rollout_before_reference_scoring')) and trace['extra_model_passes'] == trace['source_head_extra_evaluations'] == trace['optimizer_steps'] == 0 and trace['greedy_batch_steps'] == trace['recurrent_readout_calls'])
    sites = {}; batch_steps = {}
    for source, row, prediction in zip(rows, trace['rows'], trace['predictions'], strict=True):
        check('Actual consumed prefix: ' + source['id'], source['id'] == row['id'] == prediction['id'] and row['consumed_prefix'] == [1] + prediction['token_ids'][:len(row['consumed_prefix'])-1] and row['batch_offset'] == rows.index(source)//8*8 and prediction['eos_reached'] is (prediction['generation_status'] == 'eos'))
        expected, invalid = causal_sites(row['consumed_prefix'], vocabulary)
        check('All causally visited lexical sites: ' + source['id'], len(expected) == len(row['scalar_sites']) and row['first_invalid_prefix_position'] == invalid)
        batch_steps[row['batch_offset']] = max(batch_steps.get(row['batch_offset'], 0), len(row['consumed_prefix']))
        for declared, site in zip(expected, row['scalar_sites'], strict=True):
            check('Exact causal scalar route', all(site[k] == v for k, v in declared.items()))
            key = (row['id'], site['slot'], site['field'])
            if key in sites: raise ValueError('Repeated scalar event')
            vectors = [vector32(site[k]) for k in ('raw_recurrent_logits', 'applied_source_logits', 'combined_logits')]
            check('Exact actual float32 source/recurrent addition', [f32(a+b) for a, b in zip(*vectors[:2])] == vectors[2])
            available = site['slot'] < len(contexts[row['id']]['segments'])
            check('Actual unmasked full32 emitted argmax', site['source_slot_available'] is available and (available or all(v == 0 for v in vectors[1])) and max(range(32), key=vectors[2].__getitem__) == site['actual_next_token_id'] == prediction['token_ids'][site['position']])
            sites[key] = (site, row)
    check('Actual trace count/readout sum exact', len(sites) == trace['scalar_site_count'] and sum(batch_steps.values()) == trace['greedy_batch_steps'])
    scored_rows = [dict(row, target_ids=refmap[row['id']]['target_ids']) for row in rows]
    check('Posthoc full reference score binds same actual trace', scalar['score_sha256'] == digest({k: v for k, v in scalar.items() if k != 'score_sha256'}) and scalar['trace_sha256'] == trace['trace_sha256'] and scalar['rows_sha256'] == digest(scored_rows) and scalar['references_sha256'] == digest(refs) and scalar['source_contexts_sha256'] == digest(contexts) and scalar['reference_labels_used_only_after_rollout'] is True and scalar['optimizer_steps'] == 0)
    events = unique(scalar['events'], lambda e: (e['id'], e['slot'], e['field']))
    expected_keys = {(r['id'], slot, field) for r in refs for slot in range(len(r['target']['rules'])) for field in FIELDS}
    check('Full720 reference scalar denominator', len(expected_keys) == 720 and set(events) <= expected_keys and set(events) <= set(sites) and scalar['scored_sites'] == len(events))
    computed_per_field = {f: dict(scored=0, source_correct=0, recurrent_correct=0, combined_correct=0, source_correct_combined_wrong=0) for f in FIELDS}
    distributions = defaultdict(list); wrong_actual = []
    for key, event in events.items():
        site, row = sites[key]; gold = refmap[key[0]]['target']['rules'][key[1]]
        target = vocabulary.index(json.dumps(gold[key[2]], ensure_ascii=False, separators=(',', ':')))
        check('Actual event reference/prefix/clause identity', event['target_token_id'] == target and event['position'] == site['position'] and event['actual_next_token_id'] == site['actual_next_token_id'] and event['prefix_sha256'] == digest(row['consumed_prefix'][:site['position']+1]) and event['source_clause_sha256'] == site['source_clause_sha256'] == contexts[key[0]]['segments'][key[1]]['source_sha256'])
        group = computed_per_field[key[2]]; group['scored'] += 1
        for head, vector in (('source', 'applied_source_logits'), ('recurrent', 'raw_recurrent_logits'), ('combined', 'combined_logits')):
            independent = metrics(site[vector], target, site['actual_next_token_id'])
            check('Saved full32 event metrics exact: ' + head, close(event[head], independent))
            group[head + '_correct'] += independent['argmax_token_id'] == target
            distributions[key[2], head].append(independent)
        group['source_correct_combined_wrong'] += event['source']['argmax_token_id'] == target and event['combined']['argmax_token_id'] != target
        if event['combined']['argmax_token_id'] != target or event['source']['argmax_token_id'] != target:
            wrong_actual.append(dict(paragraph_id=key[0], slot=key[1], field=key[2], source_text=rows[[r['id'] for r in rows].index(key[0])]['source_text'].split('\n\n')[key[1]], expected=gold[key[2]], actual_token_id=site['actual_next_token_id'], actual_token=vocabulary[site['actual_next_token_id']], source=event['source'], recurrent=event['recurrent'], combined=event['combined']))
    check('Complete stored per-field scalar accounting', scalar['per_field'] == computed_per_field)
    unvisited = {(e['id'], e['slot'], e['field']) for e in scalar['unvisited_reference_sites']}
    check('Unvisited reference sites never counted correct', unvisited == expected_keys - set(events))
    seven = {f: dict(correct=0, total=0, unordered_correct=0) for f in FACETS}; counts = Counter(); by_length = {}
    check('Actual emitted formula fidelity full48', fidelity['complete_evaluation'] is True and len(fidelity['rows']) == 48)
    for ref, prediction, row in zip(refs, trace['predictions'], fidelity['rows'], strict=True):
        check('Actual formula identities', ref['id'] == prediction['id'] == row['id'])
        try: generated = json.loads(''.join(vocabulary[t] for t in prediction['token_ids']))
        except (ValueError, TypeError): generated = None
        check('Generated JSON retained verbatim', generated == row['generated_ir'] and ref['target'] == row['expected_ir'] and row['generated_token_ids'] == prediction['token_ids'])
        gold = ref['target']['rules']; actual = generated['rules'] if type(generated) is dict and set(generated) == {'rules'} and type(generated['rules']) is list else None
        valid = {i: r for i, r in enumerate(actual or []) if type(r) is dict and set(r) == set(FACETS) and r['modality'] in ('O', 'P', 'F') and all(type(r[f]) is str and bool(r[f]) for f in FIELDS) and all(type(r[f]) is list and len(r[f]) <= 4 and all(type(a) is str for a in r[f]) and r[f] == sorted(set(r[f])) for f in FACETS[4:])}
        syntax = actual is not None and bool(actual) and len(valid) == len(actual)
        ordered = syntax and prediction['eos_reached'] and generated == ref['target']
        expected_rules = Counter(raw(r) for r in gold); actual_rules = Counter(raw(r) for r in valid.values()); matched = sum((expected_rules & actual_rules).values()); generated_count = len(actual or [])
        preserved = syntax and prediction['eos_reached'] and matched == len(gold) == generated_count
        independent = dict(rows=1, expected_rules=len(gold), generated_rules=generated_count, valid_generated_rules=len(valid), syntax_valid=int(syntax), parsed_documents=int(actual is not None), eos_count=int(prediction['eos_reached']), ordered_exact=int(ordered), all_rules_preserved=int(preserved), whole_rules_missing=len(gold)-matched, whole_rules_extra=generated_count-matched, duplicate_rules=sum(max(0, c-1) for c in actual_rules.values()), order_mismatch_rows=int(preserved and not ordered), invalid_rule_count=generated_count-len(valid), invalid_rows=int(not syntax), unscorable_generation_rows=int(actual is None), prediction_missing_rows=0)
        check('Independent complete formula counts: ' + ref['id'], row['counts'] == independent)
        length = str(len(gold)); bucket = by_length.setdefault(length, dict(metrics=Counter(), by_facet={f: dict(correct=0, total=0, unordered_correct=0) for f in FACETS}))
        counts.update(independent); bucket['metrics'].update(independent)
        for field in FACETS:
            fieldcounts = dict(correct=sum(i in valid and valid[i][field] == rule[field] for i, rule in enumerate(gold)), total=len(gold), unordered_correct=sum((Counter(raw(r[field]) for r in gold) & Counter(raw(r[field]) for r in valid.values())).values()))
            check('All seven emitted facets: ' + field, row['by_facet'][field] == fieldcounts)
            for k, v in fieldcounts.items(): seven[field][k] += v; bucket['by_facet'][field][k] += v
    check('Full48/180 formula aggregate and length strata', fidelity['metrics'] == dict(counts) and fidelity['by_facet'] == seven and fidelity['by_length'] == by_length and counts['expected_rules'] == 180)
    check('Bank perfection claim exact, separate from generation', summary['initial_balanced_bank_all_four_scalars_correct'] is bank_summaries['balanced']['all_four_correct'])
    for value in (trace, predictions, scalar, fidelity, parity): false_masks(value)
    for path, wanted in summary['source_dependencies'].items(): reader.body(path, {'sha256': wanted})
    # Owned finalized receipts only; current foreign scheduler state is untouched.
    final = reader.json(attempt / 'resources-final.json'); start = reader.json(attempt / 'resources-start.json'); child = reader.json(attempt / 'child-exit.json'); guardian = reader.json(run / (attempt.name + '-guardian-exit.json'))
    record, active = final['record'], start['record']; lease = final['resource_lease']; oldlease = start['resource_lease']
    check('Completed exit0/reaped/durable released own resource', child['returncode'] == guardian['returncode'] == 0 and child['leader_reaped'] is True and final['status'] == record['status'] == 'released' and final['cleanup_error'] is None and record['artifacts_durable_asserted'] is True and record['attempt_exceeded_reservation'] is False and lease['released'] is True and start['status'] == active['status'] == 'active' and active['reservation_id'] == record['reservation_id'] and active['child'] == record['child'] and oldlease['lease_id'] == lease['lease_id'] and oldlease['cancelled'] is oldlease['released'] is False)
    check('Fixed CPU1/one child/1536MiB/100MB reservation', record['cpu_slots'] == record['child_process_slots'] == 1 and record['memory_mb'] == 1536 and record['storage_bytes'] == 100000000 and lease['requires_gpu'] is False)
    observation_path = attempt / 'resource-observations.json'; periodic = reader.json(observation_path) if observation_path.is_file() else []
    resource_samples = [active['last_usage'], *periodic, record['last_usage']]
    check('All saved resource snapshots within bounds', all(r['attempt_bytes'] <= r['attempt_limit_bytes'] and r['charged_bytes'] <= r['limit_bytes'] and r['group_rss']['rss_bytes'] <= r['memory_limit_bytes'] and r['process_slot_estimate_exceeded'] is False for r in resource_samples))
    check('Final groupzero and fresh145GB census', record['last_usage']['group_rss']['available'] is True and record['last_usage']['group_rss']['live_processes'] == record['last_usage']['group_rss']['rss_bytes'] == 0 and record['final_accounting']['charged_bytes'] <= record['final_accounting']['limit_bytes'] == 145000000000 and record['finalization_profile']['global_inventory_count'] == 1)
    watchdog = final['lease_watchdog']; events_body = reader.body(watchdog['events_path'], {'sha256': watchdog['events_sha256']}); lease_events = [json.loads(line) for line in events_body.splitlines() if line]; present = [e for e in lease_events if e.get('lease_present') is True]; post = watchdog['post_release_observation']
    check('Owned sampled lease healthy and released/config unchanged', bool(present) and all(e['healthy'] is e['configuration_matches'] is True and e['cancelled'] is False for e in present) and post['lease_present'] is False and post['healthy'] is post['configuration_matches'] is True and watchdog['continuous_lease_coverage_claimed'] is watchdog['shared_state_mutated_by_observer'] is False)
    validator_paths = [p for p in summary['source_dependencies'] if p.endswith('/legal_formula_codec.py')]
    check('One frozen historical schema validator leaf', len(validator_paths) == 1)
    validator_path = validator_paths[0]
    validator_bytes = reader.body(validator_path, {'sha256': summary['source_dependencies'][validator_path]})
    check('Formula validator is authenticated frozen schema callback', fidelity['validator_id'] == 'canonical-single-rule-sha256:' + hashlib.sha256(validator_bytes).hexdigest() and b'def _rule(canonical_ir)' in validator_bytes and b'CanonicalRoundTripIR.from_dict(canonical_ir).to_dict()' in validator_bytes)
    child_log_ref=reader.bindings.setdefault(str(attempt/'child.log'), {})
    reader.body(attempt/'child.log')
    reader.body(__file__)
    summaries = {field: {head: dict(reference_sites=180, visited_scored_sites=len(distributions[field, head]), unvisited_or_unavailable_sites=180-len(distributions[field, head]), argmax_correct=computed_per_field[field][head + '_correct'], mean_cross_entropy=math.fsum(v['full_vocabulary_cross_entropy'] for v in distributions[field, head])/len(distributions[field, head]) if distributions[field, head] else None, mean_target_margin=math.fsum(v['target_minus_best_other'] for v in distributions[field, head])/len(distributions[field, head]) if distributions[field, head] else None, minimum_target_margin=min((v['target_minus_best_other'] for v in distributions[field, head]), default=None), maximum_target_margin=max((v['target_minus_best_other'] for v in distributions[field, head]), default=None)) for head in ('source', 'recurrent', 'combined')} for field in FIELDS}
    result = dict(schema='dual-bank-replay-actual-preflight-independent-review/v1', passed=True, findings=[], checks=checks, artifacts=reader.bindings, attempt=str(attempt), parent_tensor_sha256=PARENT, dual_preparation=dual, source_bank_panels=bank_summaries, paired_schedule=dict(steps=170, rows_per_role=180, prior_pairing_declared_presentations_per_role=1020, dual_training_planned_presentations_per_role=510, fitting_presentations_executed_by_preflight=0, paired_original_identities_exact=True, six30_strata_per_role=True), parent_original_validation_parity=dict(receipt_claims_full_predictions_equal=True, archived_rows=48, replay_predictions_retained_separately=False, limitation='Preflight stores parity assertion only, not replay validation predictions; audit authenticates source implementation, parent archive and exact receipt but cannot independently compare unsaved replay tokens.'), actual_balanced48=dict(paragraphs=48, reference_rules=180, reference_scalar_sites=720, visited_scalar_sites=len(sites), scored_scalar_sites=len(events), unvisited_reference_sites=len(unvisited), unavailable_visited_sites=len(scalar['unscored_sites']), extra_generated_sites=len(set(sites)-expected_keys), formula_metrics=dict(counts), seven_facets=seven, by_length=by_length, actual_prefix_full32_readouts=summaries, wrong_source_or_combined_sites=wrong_actual), all_semantic_runtime_proof_qualification_false=True, numerical_owner_scope='Frozen historical numerical owners and legal_formula_codec._rule schema callback; no canonical working-tree compiler/Lean execution or legal-IR throughput/admission claim.', schema_validator=dict(path=validator_path, sha256=hashlib.sha256(validator_bytes).hexdigest(), callback='_rule', compiler_execution=False, Lean_execution=False), retained_child_log_independently_authenticated=True, training_executed=False, optimizer_steps=0, models_or_encoders_or_numerical_owners_imported_by_audit=False, source_or_tensor_modified_by_audit=False, resident_no_mutation_scope='Authenticated state bytes unchanged and frozen runtime records exact before/after tensor digest; no live tensor reconstruction by stdlib audit.', timing=dict(driver_seconds=summary['elapsed_seconds'], generation_seconds=trace['elapsed_seconds'], scalar_scoring_seconds=None, scalar_scoring_timing_scope='No separate scalar-scoring elapsed field was retained; no timing is inferred.', source_bank_seconds={role: readouts[role]['inherited_modality_readout']['elapsed_seconds'] for role in ROLES}, guardian_outer_seconds=guardian['elapsed_seconds'], launch_return_through_reap_seconds=child['launch_return_through_reap_wall_seconds'], scope='Zero-fit decoder inference on cached source features; timings do not measure encoder production, compiler bridges, Lake/proof or end-to-end autoformalization.'), resources=dict(final_group_live_process_count=0, durable_own_lease_released=True, periodic_sample_count=len(periodic), maximum_saved_group_RSS_bytes=max(r['group_rss']['rss_bytes'] for r in resource_samples), peak_RSS_measured=False, final_named_root_charge_bytes=record['final_accounting']['charged_bytes'], named_root_cap_bytes=record['final_accounting']['limit_bytes'], final_attempt_census_bytes=record['final_attempt_bytes'], reservation_bytes=record['storage_bytes'], memory_MiB=record['memory_mb'], own_present_lease_sample_count=len(present), continuous_coverage_claimed=False, current_foreign_scheduler_read_or_modified=False), limitations=['Authored fixture labels and original meanings are exposed TRAIN metadata, not reviewed natural-law gold or fresh semantic holdout.', 'Complete source-bank readouts are not emitted formula preservation; actual greedy formulas and all seven facets are reported separately.', 'Actual source/recurrent decomposition is arithmetic and includes source-conditioned recurrent history, not causal isolation.', 'Parent validation parity receipt does not retain replay token bodies; no independent token comparison is possible from this receipt alone.', 'No training, checkpoint selection, admission or proof qualification was performed.', 'Legacy initialization uses frozen historical S owners. Schema callback validation and import logs do not measure the canonical working-tree legal-IR compiler, Lean admission or compiler speed.'], audit_seconds=time.monotonic()-started)
    output = Path(output); output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x') as stream: stream.write(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--completed-attempt', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--root-completion-acknowledged', action='store_true')
    args = parser.parse_args()
    report = audit(args.completed_attempt, args.output, args.root_completion_acknowledged)
    print(json.dumps(dict(passed=report['passed'], checks=len(report['checks']), findings=len(report['findings']), output=str(args.output), formula_metrics=report['actual_balanced48']['formula_metrics'])))
