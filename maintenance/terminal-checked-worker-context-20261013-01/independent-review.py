"""Independent named-file Stage Z audit: no target/native imports or jobs.

Only stdlib plus directly constructed pinned offline tiktoken. Direct native
worker observations remain distinct from admitted supervisor START/provider use.
"""
from __future__ import annotations
import ast,base64,hashlib,importlib.metadata,json,os,stat,sys,traceback
from collections import Counter
from copy import deepcopy
from pathlib import Path
import xml.etree.ElementTree as ET
W=Path('/home/barberb/lift_coding/maintenance/terminal-checked-worker-context-20261013-01')
PREVIOUS=Path('/home/barberb/lift_coding/maintenance/terminal-semantic-context-budget-20261013-01')
R=W/'checked-worker-run-04'
A=W/'actual-public-checked-01'
C=W/'checkout'
TOKENIZER=Path('/home/barberb/lift_coding/maintenance/terminal-token-pairing-20261012-01/pinned-host-tokenizer')
checks,failures,captures,counts=[],[],{},{}

def check(condition, name, detail=None):
    entry = {'name': name, 'passed': bool(condition)}
    if detail is not None:
        entry['detail'] = detail
    checks.append(entry)
    if not condition:
        failures.append(entry)
    return bool(condition)


def require(condition, name):
    if not check(condition, name):
        raise AssertionError(name)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value, *, ascii=False):
    return json.dumps(value, sort_keys=True, ensure_ascii=ascii,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def pairs(values):
    result = {}
    for key, value in values:
        if key in result:
            raise ValueError('duplicate JSON object key')
        result[key] = value
    return result


def parse(raw, *, floats=True):
    def reject(value):
        raise ValueError('noninteger JSON scalar')
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_float=float if floats else reject, parse_constant=reject)


def stamp(info):
    return tuple(getattr(info, key) for key in ('st_dev', 'st_ino', 'st_mode',
        'st_uid', 'st_gid', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns'))


def allowed(path):
    path = Path(path)
    return (path.is_absolute() and 'cas' not in path.parts and 'lake' not in path.parts
        and '.git' not in path.parts and path.suffix not in
        {'.duckdb', '.sqlite', '.sqlite3', '.db', '.wal', '.parquet'})


def read(path, expected=None, *, max_bytes=8_000_000):
    path = Path(path)
    require(allowed(path), 'named-public-file-only:' + str(path))
    key = str(path)
    if key not in captures:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        info = os.fstat(fd)
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1,
                'regular-singlelink-file:' + key)
        require(0 <= info.st_size <= max_bytes, 'bounded-file:' + key)
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            raw = stream.read(max_bytes + 1)
        require(len(raw) == info.st_size and stamp(info) == stamp(os.fstat(fd))
                == stamp(path.lstat()), 'retained-read-custody:' + key)
        captures[key] = {'fd': fd, 'stamp': stamp(info), 'raw': raw,
            'pin': {'path': key, 'bytes': len(raw), 'sha256': sha(raw)},
            'mode': oct(stat.S_IMODE(info.st_mode))}
    value = captures[key]
    if expected is not None:
        size = expected.get('bytes', expected.get('size_bytes'))
        digest = expected['sha256'].removeprefix('sha256:')
        check(size == len(value['raw']), 'declared-size:' + key)
        check(digest == value['pin']['sha256'], 'declared-hash:' + key)
    return value['raw']


def load(path, expected=None):
    return parse(read(path, expected))


def pin_declared(value):
    if type(value) is dict:
        if type(value.get('path')) is str and Path(value['path']).is_absolute() \
                and type(value.get('sha256')) is str \
                and ('bytes' in value or 'size_bytes' in value):
            read(value['path'], value)
        for item in value.values():
            pin_declared(item)
    elif type(value) is list:
        for item in value:
            pin_declared(item)


def varint(number):
    result = bytearray()
    while number >= 128:
        result.append((number & 127) | 128)
        number >>= 7
    result.append(number)
    return bytes(result)


def cid(raw, codec=297):
    binary = varint(1) + varint(codec) + varint(18) + varint(32) + hashlib.sha256(raw).digest()
    return 'b' + base64.b32encode(binary).decode().lower().rstrip('=')


def structured(value):
    return cid(canonical(value))


def identity(value, field, name):
    check(value[field] == structured({key: item for key, item in value.items() if key != field}),
          name + ':' + field)


def compare_tree(a, b, name):
    """Complete canonical equality differentiates every JSON scalar type."""
    check(type(a) is type(b) and canonical(a)==canonical(b),name+':complete-type-aware-equality')


def ceiling(value, name):
    names = {'proof_authority', 'execution_authority', 'mutation_authority',
        'completion_authority', 'omission_authority', 'production_admitted',
        'production_activated', 'runtime_behavior_verified', 'source_semantics_verified',
        'source_origin_verified', 'source_origin_proved', 'source_equivalence_proved',
        'cpython_equivalence_proved', 'convergence_proved', 'training_convergence_proved',
        'full_task_satisfaction', 'whole_program_semantics_verified',
        'source_parser_correctness_proved', 'python_import_resolution_proved',
        'loaded_module_code_attested', 'transitive_dependency_closure_attested',
        'proof_transfer_to_display_or_dictionary', 'review_task_completion_proved',
        'public_terminal_bench_task_satisfied', 'original_task_budget_satisfied',
        'worker_launched', 'training_executed', 'source_body_executed',
        'network_isolation_enforced', 'semantic_equivalence_claimed',
        'source_authentication_claimed', 'source_omission_authority', 'proof_transfer',
        'provider_savings_measured', 'native_governor_qualified',
        'production_context_pack_qualified', 'context_sufficiency_proved',
        'provider_usage_measured', 'provider_output_measured', 'serialized_live_authority',
        'rendered_input_origin_verified',
        'full_supervisor_entrypoint_used', 'global_task_budget_enforced', 'durable_budget_resume_supported'}
    if type(value) is dict:
        for key, item in value.items():
            if key in names:
                check(item is False, name + '/' + key + ':false-ceiling')
            ceiling(item, name + '/' + key)
    elif type(value) is list:
        for index, item in enumerate(value):
            ceiling(item, name + '/' + str(index))


def tokenize_packets(packet_bytes, summary):
    # Construct from retained cached bytes; never call registry/get_encoding.
    sys.path.insert(0, str(TOKENIZER))
    require(importlib.metadata.version('tiktoken') == '0.13.0', 'tokenizer:pinned-version')
    bpe_url = 'https://openaipublic.blob.core.windows.net/encodings/o200k_base.tiktoken'
    bpe_path = Path('/tmp/data-gym-cache') / hashlib.sha1(bpe_url.encode()).hexdigest()
    raw = read(bpe_path)
    require(sha(raw) == '446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d',
            'tokenizer:pinned-local-BPE')
    ranks = {}
    for line in raw.splitlines():
        spelling, rank = line.split()
        key = base64.b64decode(spelling, validate=True)
        if key in ranks:
            raise ValueError('duplicate tokenizer byte spelling')
        ranks[key] = int(rank)
    check(len(ranks) == 199998 and len(set(ranks.values())) == len(ranks),
          'tokenizer:199998-unique-byte-spellings-and-ranks')
    pattern = '|'.join([
        r"[^\r\n\p{L}\p{N}]?[\p{Lu}\p{Lt}\p{Lm}\p{Lo}\p{M}]*[\p{Ll}\p{Lm}\p{Lo}\p{M}]+(?i:'s|'t|'re|'ve|'m|'ll|'d)?",
        r"[^\r\n\p{L}\p{N}]?[\p{Lu}\p{Lt}\p{Lm}\p{Lo}\p{M}]+[\p{Ll}\p{Lm}\p{Lo}\p{M}]*(?i:'s|'t|'re|'ve|'m|'ll|'d)?",
        r'\p{N}{1,3}', r' ?[^\s\p{L}\p{N}]+[\r\n/]*', r'\s*[\r\n]+', r'\s+(?!\S)', r'\s+'])
    specials = {'<|endoftext|>':199999, '<|endofprompt|>':200018}
    digest = hashlib.sha256(canonical({'name':'o200k_base', 'pattern':pattern,
                                      'special_tokens':specials}))
    for spelling, rank in sorted(ranks.items(), key=lambda item:item[1]):
        digest.update(rank.to_bytes(4,'big')); digest.update(len(spelling).to_bytes(4,'big'))
        digest.update(spelling)
    require(digest.hexdigest() == 'a6557bbd3ceb299981ac87fd86a51fa8f0e9505be18ed608c5ada94bdfd0f63f',
            'tokenizer:vocabulary-pattern-special-table-pin')
    import tiktoken
    import tiktoken.core
    read(tiktoken.__file__); read(tiktoken.core.__file__)
    encoding = tiktoken.Encoding('o200k_base', pat_str=pattern,
                                mergeable_ranks=ranks, special_tokens=specials)
    measured = {}
    for name, raw in packet_bytes.items():
        text = raw.decode('utf-8')
        encoded = encoding.encode(text, allowed_special=set(), disallowed_special=())
        check(encoding.decode(encoded) == text, 'tokenizer:lossless:' + name)
        measured[name] = {'tokens':len(encoded), 'bytes':len(raw), 'sha256':sha(raw)}
        compare_tree(measured[name], summary['measures'][name], 'tokenizer:independent-recount:' + name)
    counts['independent_token_measurements'] = measured
    return encoding


def reverse_ast_projection(projection, original):
    check(projection['field_mapping'] == [{'native_field':'body','planning_field':'ast_statement_sequence'}],
          'AST-projection:single-declared-key-map')
    check(projection['original_capsules_cid'] == structured(original), 'AST-projection:original-CID')
    paths = []

    def walk(value, path):
        if type(value) is list:
            return [walk(child,path+[index]) for index,child in enumerate(value)]
        if type(value) is dict:
            result = {}
            require('body' not in value, 'AST-projection:no-unprojected-body:' + repr(path))
            for key, item in value.items():
                target = 'body' if key == 'ast_statement_sequence' else key
                if key == 'ast_statement_sequence':
                    require(type(value.get('_type')) is str and type(item) is list,
                            'AST-projection:typed-original-AST-body:' + repr(path))
                    paths.append(path+['body'])
                result[target] = walk(item,path+[target])
            return result
        return value

    restored = walk(projection['capsules'], [])
    compare_tree(restored, original, 'AST-projection:exact-full-reversal')
    # Both traversals are JSON canonical-key sorted; key order was not semantic.
    check(sorted(paths,key=repr) == sorted(projection['original_field_paths'],key=repr),
          'AST-projection:all-and-only-declared-original-coordinate-paths')
    check(projection['original_source_text_included'] is False and projection['proof_transfer'] is False,
          'AST-projection:structural-only-ceiling')
    counts['reversibly_renamed_AST_body_arrays'] = len(paths)


def independent_registry(audit, view):
    """Reconstruct every expansion from original public data, without a target call."""
    directory=view['expansion_directory'];basis=directory['reference_basis']
    require(structured(basis)==directory['reference_basis_cid'],'reference:full-sealed-basis-CID')
    expected_basis={'schema':'terminal-semantic-audit-reference-basis@1','head':audit['head'],
        'native_root_cid':audit['native_root']['root_cid'],'capsule_set_id':audit['capsule_set_id'],
        'repository_state_cid':audit['repository_state']['state_cid'],
        'audit_sha256':sha(canonical(audit)),'audit_bytes':len(canonical(audit)),
        'checked_call_context_sha256':sha(view['checked_call_context'].encode()),
        'code_views_cid':structured(view['code_views']),
        'original_sources_cid':structured(view['original_sources'])}
    compare_tree(basis,expected_basis,'reference:complete-head-state-root-source-context-basis')
    registry={}
    def register(kind,identifier,raw,object_cid):
        require((kind,identifier) not in registry,'reference:unique-registry-key:' + kind + ':' + identifier)
        require(0<len(raw)<=1048576,'reference:bounded-complete-original-response:' + kind + ':' + identifier)
        handle={'schema':'terminal-semantic-audit-reference@1','kind':kind,'id':identifier,
            'reference_basis_cid':directory['reference_basis_cid'],'object_cid':object_cid,
            'sha256':sha(raw),'bytes':len(raw)}
        registry[(kind,identifier)]=(handle,raw)
    register('full_audit',audit['capsule_set_id'],canonical(audit),structured(audit))
    state_raw=audit['repository_state']['canonical_json'].encode()
    register('repository_state',audit['repository_state']['state_cid'],state_raw,
             structured(parse(state_raw,floats=False)))
    group={'blocks':audit['blocks']}
    register('native_blocks',audit['native_root']['root_cid'],canonical(group),structured(group))
    for block in audit['blocks']:
        register('native_block',block['cid'],block['canonical_json'].encode(),block['cid'])
    group={'artifact_facts':audit['artifact_facts']}
    register('artifact_facts',audit['native_root']['artifact_fact_index_cid'],canonical(group),structured(group))
    for fact in audit['artifact_facts']:
        register('artifact_fact',fact['fact_cid'],canonical(fact),structured(fact))
    expected=sorted((value[0] for value in registry.values()),key=lambda x:(x['kind'],x['id']))
    compare_tree(directory['references'],expected,'reference:all50-exact-independent-registered-handles')
    require(len(expected)==50,'reference:exact50-finite-expansions')
    require(directory['deferred_fields']==['artifact_facts','blocks','repository_state.canonical_json'],
            'view:closed-three-duplicate-field-partition')
    # Own exact typed decoder accepts registered handles only and returns whole
    # original bytes; no path/SQL parser, native API or owner is involved.
    def resolve(handle):
        fields={'schema','kind','id','reference_basis_cid','object_cid','sha256','bytes'}
        if type(handle) is not dict or set(handle)!=fields or type(handle['kind']) is not str \
                or type(handle['id']) is not str or type(handle['bytes']) is not int:
            raise ValueError('closed exact typed expansion reference required')
        if len(canonical(handle))>4096:raise ValueError('request bound')
        found=registry.get((handle['kind'],handle['id']))
        if found is None or canonical(found[0])!=canonical(handle):raise ValueError('unregistered or rebound handle')
        return found[1]
    for index,handle in enumerate(directory['references']):
        raw=resolve(handle)
        require(len(raw)==handle['bytes'] and sha(raw)==handle['sha256'] and cid(raw)==handle['object_cid'],
                'reference:every-original-byte-CID-size-hash:' + str(index))
        require(canonical(parse(raw,floats=False))==raw,'reference:every-response-exact-canonical-JSON:' + str(index))
    restored=dict(view['native_view']['retained_fields'])
    restored['schema']=view['native_view']['original_audit_schema']
    restored['capsule_set_id']=view['native_view']['audit_capsule_set_id']
    fields=directory['field_groups']
    restored['repository_state']={**view['native_view']['repository_state'],
        'canonical_json':resolve(fields['repository_state.canonical_json']).decode()}
    restored['blocks']=parse(resolve(fields['blocks']),floats=False)['blocks']
    restored['artifact_facts']=parse(resolve(fields['artifact_facts']),floats=False)['artifact_facts']
    require(canonical(restored)==canonical(audit),'view:own-decoder-restores-exact-entire-audit-bytes')
    require(resolve(directory['complete_audit_reference'])==canonical(restored),'view:full-reference-equals-independent-reconstruction')
    identity(restored,'capsule_set_id','view:restored-complete-native-audit')
    counts.update(registered_reference_count=len(registry),
                  independently_reconstructed_full_audit_bytes=len(canonical(restored)),
                  independently_reconstructed_full_audit_sha256=sha(canonical(restored)))
    return registry,resolve


def native_review(value, name, head, native, capacity, expected_ids):
    identity(value,'result_cid','preview:nested-native-result:' + name)
    compare_tree(value['head'],head,'preview:exact-native-head:' + name)
    compare_tree(value['capacity'],capacity,'preview:original-shared-held-capacity:' + name)
    check(value['selected_task_ids']==expected_ids,'preview:all-three-review-tasks:' + name)
    reverse_ast_projection(value['native_planning_material']['native_capsule_projection'],native['capsules'])
    result=value['native_preview'];receipt=result['preview'];plan=value['native_parallel_plan'];req=value['native_parallel_request']
    compare_tree(req,plan['replay_request'],'preview:exact-native-replay-request:' + name)
    check(receipt['verdict']=='review_only' and receipt['read_only'] is True and receipt['wrote_effects']==[],
          'preview:unchanged-native-read-only-verdict:' + name)
    stages={item['stage']:item for item in receipt['stage_results']}
    check(set(stages)=={'scan','query','evidence','obligation','candidate','critique','admission','parallel_plan'}
          and all(x['passed'] is True for key,x in stages.items() if key!='admission')
          and stages['admission']['passed'] is False
          and stages['admission']['blockers']==['ir_admission_materials_absent'],
          'preview:seven-native-stages-pass-only-IR-admission-missing:' + name)
    check(plan['outcome']=='review_only' and plan['admitted_width']==0 and
          plan['assignments']==plan['execution_waves']==plan['merge_order']==plan['issues']==[],
          'preview:zero-executable-width-empty-worker-assignments:' + name)
    check(plan['leaf_producer_closure']['closed'] is True and req['review_only'] is True
          and req['completed_task_ids']==[],'preview:logical-leaves-covered-never-completed:' + name)
    check(type(req['current_time_ms']) is int and req['current_time_ms']>0
          and req['current_time_ms']<=req['deadline_ms'],'preview:private-positive-bounded-clock:' + name)
    for index,task in enumerate(value['review_projection']['tasks']):
        check(task['task_id']==expected_ids[index] and task['review_only'] is True
              and task['worktree_policy']=='none' and all(task[key]==[] for key in
              ('outputs','effects','changed_paths','predicted_paths','completion_facts')),
              'preview:closed-no-write-task:' + name + ':' + str(index))
        check(task['depends_on']==([] if index==0 else [expected_ids[index-1]]),
              'preview:exact-serial-review-dependencies:' + name + ':' + str(index))
        resources=task['resource_contract']
        check(resources['cpu_slots']==resources['process_slots']==1 and
              resources['memory_bytes']==67108864 and resources['provider_requirement']=='' and
              resources['context_tokens']==resources['output_token_budget']==0,
              'preview:fixed-native-zero-provider-forecast-resources:' + name + ':' + str(index))
    for which in ('cold_validation_before','cold_validation_after'):
        cold=value[which]
        check(cold['data_validated'] is True and cold['checker_reinvoked'] is False and
              cold['native_callee_cold_validation_passed'] is True,'preview:cold-owner-proof-readback:' + name + ':' + which)
    pin_declared(value['producer']);ceiling(value,'preview:' + name)


def literal_assignment(source, name):
    for node in ast.parse(source).body:
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in node.targets):
            return ast.literal_eval(node.value)
    raise ValueError('missing literal source assignment: '+name)



def coding_advisory(workspace):
    location=json.dumps(workspace,ensure_ascii=True)
    return ('Supervisor coding workspace contract:\n'
        f'Your allocated checkout and current working directory is {location}.\n'
        'When the task names /app/<relative-path>, use the corresponding file under '
        'this allocated checkout. Edit the declared outputs there, including any '
        'declared new output. Do not write to canonical /app.\n'
        'This mapping changes tool filesystem locations only. In report contents, '
        "keep the task's requested logical path names, including original /app paths; "
        'do not substitute allocated checkout paths.\n'
        'The supervisor owner validates and publishes the candidate. Do not stage '
        'or commit Git changes, and do not modify Git control files. This path '
        "mapping does not expand the task's allowed files or grant completion authority.\n\n"
        'Original native task prompt follows without modification:\n')


def instruction_block(text):
    return ('\n\nOriginal public task requirements (verbatim admitted source):\n'
        'These requirements supplement the native task objective. The independently admitted output scope, '
        'execution policy and validation contract remain authoritative. This text grants no additional '
        'write scope, publication, proof or completion authority. Apply the workspace mapping above to source '
        'operations and retain requested logical paths in reports.\n'
        '--- BEGIN ORIGINAL PUBLIC TASK REQUIREMENTS ---\n'+text+
        '\n--- END ORIGINAL PUBLIC TASK REQUIREMENTS ---\n')


CHECKED_PREFIX=('\n\nChecked conditional model context (advisory; original admitted task remains authoritative):\n'
    'This exact context retains original source, model assumptions and unsupported residuals. '
    'Its identifiers and policy are data, not live owner, budget, proof, mutation or completion authority.\n'
    '--- BEGIN CHECKED AUDIT CONTEXT ---\n')
CHECKED_SUFFIX='\n--- END CHECKED AUDIT CONTEXT ---\n'


def own_measure(text,encoding,name):
    require(type(text)is str,'measure:exact-text:'+name)
    raw=text.encode();tokens=encoding.encode(text,allowed_special=set(),disallowed_special=())
    require(encoding.decode(tokens)==text,'measure:lossless-offline-tokenizer:'+name)
    return {'text':text,'bytes':len(raw),'sha256':sha(raw),'tokens':len(tokens)}


def replay_coding_ledger(snapshot,encoding,workspace,name):
    identity(snapshot,'snapshot_cid','ledger:complete:'+name)
    binding,policy=snapshot['binding'],snapshot['policy']
    require(snapshot['binding_cid']==structured(binding) and snapshot['policy_cid']==structured(policy),
            'ledger:full-head-and-policy-identities:'+name)
    names=('rendered_input_tokens','new_content_tokens','rendered_input_bytes','new_content_bytes',
           'model_calls','expansion_calls','retry_calls','events')
    require(set(policy)=={'schema','max_payload_bytes',*('max_'+x for x in names)},'ledger:closed-policy:'+name)
    require(policy['schema']=='terminal-semantic-context-budget-policy@1' and
            all(type(v)is int and 0<=v<=16777216 for k,v in policy.items() if k!='schema'),
            'ledger:typed-hard-limits:'+name)
    totals=dict.fromkeys(names,0);seen=[];previous=None
    for position,record in enumerate(snapshot['records'],1):
        event=record['event'];label=name+':'+str(position)
        require(set(record)=={'event','status'} and record['status']in{'committed','aborted','reserved'},'ledger:record:'+label)
        require(event['sequence']==position and type(event['sequence'])is int and
                event['binding_cid']==snapshot['binding_cid'] and event['history_event_ids']==seen
                and event['previous_event_cid']==previous,'ledger:exact-charged-chain:'+label)
        require(event['event_id']not in seen and event['kind']in{'initial','retry'} and
                ((position==1 and event['kind']=='initial' and event['retry_of']is None)or
                 (position>1 and event['kind']=='retry' and event['retry_of']in seen)),
                'ledger:no-free-fallback-or-reset:'+label)
        identity(event,'event_cid','ledger:complete-event:'+label)
        require(event['tokenizer']==snapshot['tokenizer'] and event['expansion_request']is None
                and event['expansion_response']is None,'ledger:no-unaccounted-expansion:'+label)
        for field in ('new_content','rendered_input'):
            actual=own_measure(event[field]['text'],encoding,label+':'+field)
            compare_tree(event[field],actual,'ledger:independent-every-exact-text-measure:'+label+':'+field)
            require(actual['bytes']<=min(256000,policy['max_payload_bytes']),'ledger:single-native-byte-bound:'+label+':'+field)
            for metric in ('tokens','bytes'):totals[field+'_'+metric]+=actual[metric]
        require(event['rendered_input']['text']==coding_advisory(workspace)+event['new_content']['text'],
                'ledger:independent-complete-coding-guidance-and-input:'+label)
        totals['model_calls']+=1;totals['retry_calls']+=int(event['kind']=='retry');totals['events']+=1
        for key in names:require(totals[key]<=policy['max_'+key],'ledger:hard-cumulative-no-refund:'+label+':'+key)
        seen.append(event['event_id']);previous=event['event_cid']
    compare_tree(snapshot['totals'],totals,'ledger:all-eight-cumulative-totals:'+name)
    require(snapshot['provider_calls']==0 and snapshot['provider_output_tokens']is None and
            snapshot['provider_usage_measured']is False and snapshot['serialized_live_authority']is False
            and snapshot['rendered_input_origin_verified']is False and snapshot['history_inclusion_verified']is False,
            'ledger:data-only-no-provider-or-conversation-history-authority:'+name)
    ceiling(snapshot,'ledger:'+name)
    return totals


def verify_public_signature(envelope,name):
    """Own Ed25519 public-data verifier; no target/crypto library or key access.

    Equality authenticates the payload under its supplied public did:key, not
    the identity's origin, actual signing process or its external trust anchor.
    """
    require(set(envelope)=={'payload','binding'},'signature:closed-envelope:'+name)
    binding=envelope['binding'];did=binding['identity']
    require(set(binding)=={'identity','profile_id','signature'} and did.startswith('did:key:z'),
            'signature:closed-public-did-key:'+name)
    alphabet='123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz';number=0
    for ch in did[len('did:key:z'):]:number=number*58+alphabet.index(ch)
    encoded=number.to_bytes((number.bit_length()+7)//8,'big')
    require(encoded[:2]==b'\xed\x01' and len(encoded)==34,'signature:Ed25519-multicodec:'+name)
    key=encoded[2:];signature=base64.b64decode(binding['signature'],validate=True)
    require(len(signature)==64,'signature:64bytes:'+name)
    p=2**255-19;order=2**252+27742317777372353535851937790883648493
    d=(-121665*pow(121666,p-2,p))%p;i=pow(2,(p-1)//4,p);zero=(0,1,1,0)
    def add(a,b):
        x,y,z,t=a;u,v,w,s=b
        aa=((y-x)*(v-u))%p;bb=((y+x)*(v+u))%p;cc=(2*d*t*s)%p;dd=(2*z*w)%p
        e=(bb-aa)%p;f=(dd-cc)%p;g=(dd+cc)%p;h=(bb+aa)%p
        return e*f%p,g*h%p,f*g%p,e*h%p
    def multiply(a,n):
        value=zero
        while n:
            if n&1:value=add(value,a)
            a=add(a,a);n>>=1
        return value
    def encode(a):
        x,y,z,_=a;inverse=pow(z,p-2,p);x=x*inverse%p;y=y*inverse%p
        return (y|((x&1)<<255)).to_bytes(32,'little')
    def decode(raw):
        packed=int.from_bytes(raw,'little');y=packed&((1<<255)-1);sign=packed>>255
        if y>=p:raise ValueError('noncanonical Ed25519 y')
        x2=(y*y-1)*pow(d*y*y+1,p-2,p)%p;x=pow(x2,(p+3)//8,p)
        if x*x%p!=x2:x=x*i%p
        if x*x%p!=x2 or (x==0 and sign):raise ValueError('invalid Ed25519 point')
        if x&1!=sign:x=p-x
        value=(x,y,1,x*y%p)
        if encode(value)!=raw:raise ValueError('noncanonical Ed25519 point')
        return value
    public=decode(key);r=decode(signature[:32]);s=int.from_bytes(signature[32:],'little')
    require(s<order and encode(public)!=encode(zero) and encode(multiply(public,order))==encode(zero)
            and encode(multiply(r,order))==encode(zero),'signature:canonical-prime-order-points-and-scalar:'+name)
    base=decode((4*pow(5,p-2,p)%p).to_bytes(32,'little'))
    challenge=int.from_bytes(hashlib.sha512(signature[:32]+key+canonical(envelope['payload'],ascii=True)).digest(),'little')%order
    require(encode(multiply(base,s))==encode(add(r,multiply(public,challenge))),
            'signature:independent-exact-public-Ed25519-equation:'+name)
    counts['independently_verified_public_signatures']=counts.get('independently_verified_public_signatures',0)+1


def decode_git_bundle(raw,expected_head,expected_tree,expected_sources):
    """Own bounded Git bundle/pack decoder: no Git subprocess or source execution."""
    import struct,zlib
    require(raw.startswith(b'# v2 git bundle\n') and len(raw)<=1048576,'git:bounded-public-v2-bundle')
    header,pack=raw.split(b'\n\n',1)
    refs=[line.split()for line in header.splitlines()[1:]]
    require([expected_head.encode(),b'HEAD']in refs and not any(line.startswith(b'-')for line in header.splitlines()),
            'git:complete-self-contained-HEAD-reference')
    require(pack[:4]==b'PACK' and hashlib.sha1(pack[:-20]).digest()==pack[-20:],'git:exact-pack-SHA1-trailer')
    version,n=struct.unpack('>II',pack[4:12]);require(version==2 and 1<=n<=64,'git:bounded-standard-pack')
    offset=12;objects={};by_offset={};pending=[];kinds={1:'commit',2:'tree',3:'blob',4:'tag'}
    for number in range(n):
        start=offset;byte=pack[offset];offset+=1;kind=(byte>>4)&7;size=byte&15;shift=4
        while byte&128:
            byte=pack[offset];offset+=1;size|=(byte&127)<<shift;shift+=7
        require(kind in {*kinds,6,7} and size<=1048576,'git:bounded-source-object:'+str(number))
        base=None
        if kind==6:
            byte=pack[offset];offset+=1;distance=byte&127
            while byte&128:
                byte=pack[offset];offset+=1;distance=((distance+1)<<7)+(byte&127)
            base=('offset',start-distance)
        elif kind==7:
            base=('oid',pack[offset:offset+20].hex());offset+=20
        stream=zlib.decompressobj();body=stream.decompress(pack[offset:-20],size+1)
        require(stream.eof and len(body)==size,'git:complete-object-decompression:'+str(number))
        offset+=len(pack[offset:-20])-len(stream.unused_data)
        if base is not None:pending.append((start,base,body));continue
        name=kinds[kind];oid=hashlib.sha1((name+' '+str(size)+'\0').encode()+body).hexdigest()
        require(oid not in objects,'git:unique-pack-object:'+str(number));objects[oid]=(name,body);by_offset[start]=(name,body)
    def delta(original,data):
        cursor=0
        def integer():
            nonlocal cursor
            value=shift=0
            while True:
                byte=data[cursor];cursor+=1;value|=(byte&127)<<shift;shift+=7
                if not byte&128:return value
        require(integer()==len(original),'git:delta-original-size')
        size=integer();require(size<=1048576,'git:bounded-delta-result');out=bytearray()
        while cursor<len(data):
            opcode=data[cursor];cursor+=1
            if opcode&128:
                where=count=0
                for bit in range(4):
                    if opcode&(1<<bit):where|=data[cursor]<<(8*bit);cursor+=1
                for bit in range(3):
                    if opcode&(1<<(4+bit)):count|=data[cursor]<<(8*bit);cursor+=1
                count=count or 65536
                require(where+count<=len(original),'git:delta-copy-bound');out.extend(original[where:where+count])
            else:
                require(opcode>0 and cursor+opcode<=len(data),'git:delta-literal-bound')
                out.extend(data[cursor:cursor+opcode]);cursor+=opcode
            require(len(out)<=size,'git:delta-output-bound')
        require(len(out)==size,'git:exact-delta-result');return bytes(out)
    while pending:
        next_pending=[];progress=False
        for start,base,data in pending:
            original=by_offset.get(base[1])if base[0]=='offset'else objects.get(base[1])
            if original is None:next_pending.append((start,base,data));continue
            name,content=original;body=delta(content,data)
            oid=hashlib.sha1((name+' '+str(len(body))+'\0').encode()+body).hexdigest()
            require(oid not in objects,'git:unique-reconstructed-delta-object');objects[oid]=(name,body);by_offset[start]=(name,body);progress=True
        require(progress,'git:all-delta-bases-contained-no-external-fetch');pending=next_pending
    require(offset==len(pack)-20 and objects[expected_head][0]=='commit','git:whole-pack-decoded')
    commit=objects[expected_head][1]
    require(commit.splitlines()[0]==b'tree '+expected_tree.encode(),'git:exact-HEAD-tree')
    recovered={}
    def walk(oid,prefix=''):
        kind,body=objects[oid];require(kind=='tree','git:declared-tree-object:'+oid)
        cursor=0
        while cursor<len(body):
            space=body.index(b' ',cursor);end=body.index(b'\0',space)
            mode=body[cursor:space];name=body[space+1:end].decode();target=body[end+1:end+21].hex();cursor=end+21
            require(name not in {'','.','..'} and '/'not in name,'git:finite-relative-tree-entry')
            path=prefix+name
            if mode in {b'40000',b'040000'}:walk(target,path+'/')
            else:
                require(mode==b'100644' and objects[target][0]=='blob','git:exact-nonexecutable-source-blob:'+path)
                recovered[path]=objects[target][1]
    walk(expected_tree)
    require(set(recovered)==set(expected_sources),'git:exact-four-source-blobs-no-metadata')
    for name,content in expected_sources.items():require(recovered[name]==content,'git:exact-native/checked-source-byte-join:'+name)
    counts.update(independent_git_pack_objects=n,independent_git_source_blobs=len(recovered))
    return recovered

def audit_native_basis(summary):
    head=summary['head']
    native=load(R/'native-semantic-capsules.json');manifest=load(R/'observed-manifest.json')
    capsule=load(R/'checked-call-capsule.json');views=load(R/'code-views.json')
    intent=load(R/'intent-profile.json');query=load(R/'query.json')
    view=load(R/'audit-view.json');call=parse(view['checked_call_context'],floats=False)
    require(summary['qualified'] is True,'actual:selected-qualified-Z-run')
    for name,value in [('native',native),('capsule',capsule),('views',views),('view',view),('call',call)]:
        compare_tree(value['head'],head,'head:complete-current-owner-through-all-required-evidence:' + name)
    compare_tree(call['context']['capsule'],capsule,'proof:whole-original-checked-call-capsule')
    require(capsule['residuals'][0]['path']=='dynamic.py' and
            capsule['intent']['mathematical_domain']=={'kind':'unbounded_mathematical_integer',
                'python_input_assumption':'exact_builtin_int_excluding_bool_and_subclasses','runtime_equivalence_proved':False},
            'proof:explicit-domain-and-open-dynamic-residual')
    require(len(capsule['assumptions']['caller'])==5 and len(capsule['assumptions']['callee_compilation'])==3
            and len(capsule['assumptions']['callee_translation'])==3,'proof:all-eleven-original-assumptions')
    identity(native,'capsule_set_id','native:complete-envelope')
    identity(capsule,'capsule_id','proof:complete-envelope')
    check(native['coverage'] == manifest['coverage'] and native['units'] == manifest['units']
          and native['snapshot'] == manifest['snapshot'], 'native:complete-manifest-projection')
    snapshot, state, producer, root = manifest['snapshot'], manifest['semantic_state'],native['producer'],native['native_root']
    # Native RepositoryState.to_dict uses the index schema, while its identity
    # payload uses a repository-state schema plus semantic_index_schema.
    state_identity={k:v for k,v in state.items() if k not in {'state_cid','schema'}}
    state_identity.update(schema='ipfs-datasets.software-contracts.semantic-repository-state@1',
                          semantic_index_schema=state['schema'])
    check(structured(state_identity)==state['state_cid'],'native:RepositoryState:state_cid')
    identity(snapshot,'snapshot_cid','native:RepositorySnapshot')
    check(structured(manifest) == head['manifest_cid'], 'native:full-manifest-CID')
    state_bytes = native['repository_state']['canonical_json'].encode()
    check(canonical(state) == state_bytes and sha(state_bytes) == native['repository_state']['sha256']
          and len(state_bytes) == native['repository_state']['bytes'], 'native:entire-RepositoryState-bytes')
    compare_tree(producer, root['producer'], 'native:root-producer')
    for key,value in {'repository_state_cid':state['state_cid'],
            'repository_snapshot_cid':head['snapshot_cid'],'source_manifest_cid':head['manifest_cid'],
            'git_commit_oid_or_null':snapshot['git_commit'],'git_tree_oid_or_null':snapshot['git_tree'],
            'semantic_index_schema':state['schema'],'extractor_name':state['extractor_name'],
            'extractor_version':state['extractor_version']}.items():
        check(producer[key] == value, 'native:explicit-producer-complete-join:' + key)
    check(producer['repository_snapshot_cid'] != state['state_cid'] and
          producer['source_manifest_cid'] != state['state_cid'], 'native:no-state-ID-fallback')
    identity(root,'root_cid','native:root')
    entries = {item['path']:item for item in snapshot['entries']}
    require(set(entries) == {'callee.py','caller.py','dynamic.py'}, 'native:exact-three-authored-source-paths')
    source_bytes = {path:read(A/'repository'/path) for path in entries}
    for source in capsule['source_closure']['sources']:
        raw=source_bytes[source['path']]
        check(len(raw)==source['bytes'] and sha(raw)==source['sha256'],
              'proof:exact-three-original-sources:' + source['path'])
    check(capsule['residuals'][0]['source_sha256']==sha(source_bytes['dynamic.py']),
          'proof:dynamic-residual-bound-to-exact-original')
    intent_raw=intent['intent_document_json'].encode('utf-8')
    check(len(intent_raw)==intent['intent_document_bytes'] and
          sha(intent_raw)==intent['intent_document_sha256']==capsule['intent']['intent_document_sha256'],
          'intent:exact-canonical-native-JSON-string-and-proof-join')
    check(sha(call['user_prompt'].encode())==capsule['intent']['prompt']['sha256'] and
          call['user_prompt']=='Under closed-caller-model@1, caller.py::twice(n) must return n + 2.',
          'intent:exact-CNL-prompt-and-contract')
    for path,entry in entries.items():
        identity(entry,'entry_cid','native:entry:' + path)
        check(entry['source_cid'] == cid(source_bytes[path],85) and entry['size_bytes'] == len(source_bytes[path]),
              'native:original-source-byte-CID-and-size:' + path)
        check(entry['raw_path_hex'] == path.encode().hex(), 'native:original-raw-path:' + path)
    blocks = {}
    for ordinal, item in enumerate(native['blocks']):
        raw = item['canonical_json'].encode('utf-8'); payload = parse(raw,floats=False)
        require(item['cid'] not in blocks, 'native:unique-block:' + str(ordinal))
        check(canonical(payload) == raw and len(raw) == item['bytes'] and sha(raw) == item['sha256']
              and cid(raw) == item['cid'], 'native:independent-canonical-block-hash-CID:' + str(ordinal))
        blocks[item['cid']] = payload
    require(len(blocks) == len(native['blocks']) == native['cold_incremental']['block_count'] == 45,
            'native:45-complete-finite-blocks')
    check(sum(item['bytes'] for item in native['blocks']) == native['cold_incremental']['native_block_bytes'],
          'native:complete-native-block-byte-count')
    check(native['cold_incremental']['equal_root'] is True and
          native['cold_incremental']['equal_complete_block_map'] is True, 'native:cold-incremental-equality-receipt')
    compare_tree(blocks[root['root_cid']],{k:v for k,v in root.items() if k!='root_cid'},'native:root-stored-block')
    indexes = {}
    for key in ('symbol_fact_index_cid','artifact_fact_index_cid','semantic_link_index_cid',
                'symbol_node_index_cid','capsule_index_cid','analysis_limitation_index_cid'):
        block = blocks[root[key]]
        pairs_list = block['pairs']
        check(block['schema'].endswith('semantic-sorted-pair-index@1') and
              pairs_list == sorted(pairs_list) and len({x[0] for x in pairs_list}) == len(pairs_list),
              'native:closed-sorted-unique-root-index:' + key)
        for left,right in pairs_list:
            check(right in blocks,'native:root-index-target-block:' + key + ':' + left)
        indexes[key] = dict(pairs_list)
    compare_tree(blocks[root['environment_binding_set_cid']],
                 {k:v for k,v in native['environment_bindings'].items() if k!='binding_set_cid'},
                 'native:environment-binding-block')
    check(native['environment_bindings']['bindings'] == [],'native:explicit-environment-bindings-empty-limit')
    completion=native['binding_projection_completion']
    require(completion['original_native_block_count'] == 39 and
            completion['pinned_native_compiler_stores_projection_blocks'] is False and
            completion['root_and_capsule_identity_preserved'] is True and
            len(completion['supplemental_projection_cids']) == 6,
            'native:six-explicit-supplemental-projection-blocks-over-39-original')
    symbols={item['stable_id']:item for item in state['symbols']}
    require(len(native['capsules']) == len(symbols) == len(native['capsules']) == 6,
            'native:every-observed-symbol-retained-once')
    confidence_rank={'exact':0,'conservative':1,'heuristic':2,'opaque':3}
    seen=[]
    for number,item in enumerate(native['capsules']):
        cap, assessment, expansion, projection = (item[k] for k in
            ('capsule','native_freshness','original_source_expansion','relevant_binding_projection'))
        symbol=symbols[cap['stable_symbol_id']]; seen.append(symbol['stable_id'])
        identity(cap,'capsule_cid','native:capsule:' + str(number))
        identity(assessment,'assessment_cid','native:freshness:' + str(number))
        identity(projection,'projection_cid','native:binding-projection:' + str(number))
        compare_tree(blocks[cap['capsule_cid']],{k:v for k,v in cap.items() if k!='capsule_cid'},
                     'native:capsule-stored-bytes:' + str(number))
        fact=blocks[cap['symbol_fact_cid']]
        compare_tree(fact['symbol'],symbol,'native:fact-full-original-symbol:' + str(number))
        check(indexes['capsule_index_cid'][symbol['stable_id']] == cap['capsule_cid']
              and indexes['symbol_fact_index_cid'][symbol['stable_id']] == cap['symbol_fact_cid'],
              'native:capsule-and-fact-index-join:' + str(number))
        for key,value in {'source_cid':symbol['source_cid'],'version_cid':symbol['version_cid'],
                'source_slice_path':symbol['module_path'],'metadata':symbol['metadata'],
                'signature':symbol['signature'],'annotations':symbol['annotations']}.items():
            compare_tree(cap[key],value,'native:original-symbol-capsule-join:' + str(number) + ':' + key)
        check(confidence_rank[cap['confidence']] >= confidence_rank[symbol['confidence']],
              'native:confidence-never-strengthened:' + str(number))
        compare_tree(expansion['span'],symbol['span'],'native:exact-original-span:' + str(number))
        check(expansion['path'] == symbol['module_path'] and
              expansion['qualified_name'] == symbol['qualified_name'] and
              expansion['source_cid'] == symbol['source_cid'] and
              expansion['entry_cid'] == entries[symbol['module_path']]['entry_cid'] and
              expansion['version_cid'] == symbol['version_cid'] and
              expansion['ast_revision_id'] == head['ast_revision_id'] and
              expansion['snapshot_cid'] == head['snapshot_cid'],
              'native:original-source-AST-full-head-expansion-join:' + str(number))
        require(expansion['raw_source_required_by_adapter'] is True and expansion['proof_transfer'] is False,
                'native:original-source-always-required:' + str(number))
        projection_id=cap['relevant_binding_projection_cid']
        compare_tree(blocks[projection_id],{k:v for k,v in projection.items() if k!='projection_cid'},
                     'native:required-projection-block:' + str(number))
        check(projection_id in completion['supplemental_projection_cids'] and
              projection['stable_symbol_id'] == symbol['stable_id'] and projection['binding_ids'] == [] and
              projection['binding_set_cid'] == root['environment_binding_set_cid'],
              'native:supplemental-projection-membership-current-join:' + str(number))
        check(assessment['root_cid'] == root['root_cid'] and
              assessment['producer_repository_state_cid'] == state['state_cid'] and
              assessment['capsule_cid'] == cap['capsule_cid'] and
              assessment['relevant_binding_projection_cid'] == projection_id,
              'native:freshness-complete-current-root-join:' + str(number))
        if cap['confidence'] in {'opaque','heuristic'}:
            check(item['native_requires_raw_source'] is True and item['native_safe_substitute'] is False
                  and assessment['admission'] == 'raw_source_required',
                  'native:unsafe-confidence-raw-source:' + str(number))
        if cap['confidence'] == 'conservative':
            check(assessment['admission'] == 'conservative_substitute_with_caveats'
                  and 'confidence:conservative' in assessment['caveats'],
                  'native:conservative-substitution-caveat:' + str(number))
    check(set(seen)==set(symbols) and len(seen)==len(set(seen)), 'native:exact-complete-symbol-coverage')
    check(native['source_scope']['paths']==sorted(entries)
          and native['source_scope']['selected_omissions']==[]
          and native['source_scope']['snapshot_exclusion_policy']==snapshot['exclusions']
          and len(snapshot['exclusions'])==26
          and native['source_scope']['whole_filesystem_coverage'] is False
          and native['source_scope']['excluded_paths_observed'] is False,
          'native:admitted-inventory-only-exclusion-policy-bound')
    for name,field,index,identity_field in [('artifact','artifact_facts','artifact_fact_index_cid','fact_cid'),
          ('link','semantic_links','semantic_link_index_cid','link_cid'),
          ('limitation','analysis_limitations','analysis_limitation_index_cid','limitation_cid')]:
        rows=native[field]
        check(len(rows)==len(indexes[index]),'native:complete-family:' + name)
        for row in rows:
            identity(row,identity_field,'native:' + name)
            compare_tree(blocks[row[identity_field]],{k:v for k,v in row.items() if k!=identity_field},
                         'native:stored-family-row:' + name + ':' + row[identity_field])
    check(len(native['semantic_links'])==len(state['edges']), 'native:every-native-dependency-retained')
    for edge in state['edges']:
        match=[row for row in native['semantic_links'] if row['edge_id']==edge['edge_id']]
        require(len(match)==1,'native:original-edge-present:' + edge['edge_id'])
        link=match[0]
        check(link['confidence']==edge['confidence'] and link['source_span']==edge['span'],
              'native:original-edge-confidence-and-coordinates:' + edge['edge_id'])
        if link['target_kind']=='unresolved':
            check(link['target_stable_id'] is None and link['target_fact_cid'] is None,
                  'native:unresolved-target-remains-unknown:' + edge['edge_id'])
    for code_view_record in views['views']:
        path=code_view_record['path'];raw=source_bytes[path];preview=code_view_record['native_preview'];handle=code_view_record['source_handle']
        require(code_view_record['selected']=='original' and code_view_record['display_text'].encode()==raw,
                'display:honest-tiny-original-fallback:' + path)
        check(code_view_record['fallback_reason']=='complete_guided_view_does_not_reduce_bytes',
              'display:guidance-overhead-fallback-reason:' + path)
        check(code_view_record['display_sha256']==sha(raw) and code_view_record['display_bytes']==len(raw)
              and handle['source_sha256']==sha(raw) and handle['source_cid']==cid(raw,85)
              and handle['head']==head,'display:distinct-original-binding-preserved:' + path)
        check(preview['ast_structure_verified'] is True and preview['token_structure_verified'] is True
              and 'not a semantic-equivalence proof' in preview['guidance'],
              'display:structural-only-guidance:' + path)
    check(sum(map(len,source_bytes.values()))==195, 'view:195-original-source-bytes-direct')
    return {'head':head,'native':native,'manifest':manifest,'capsule':capsule,'views':views,'view':view,'call':call,'sources':source_bytes,'query':query,'intent':intent}



def audit_native_fixture(basis):
    for name in ('context/context_compiler.py','context/context_contracts.py','proof/formal_verification_contracts.py'):
        ast.parse(read(C/'ipfs_accelerate_py/agent_supervisor'/name),filename=name)
    public=W/'native-fixture-05/public';owner=load(public/'owner-receipt.json')
    admission=load(public/'admission.json');manifest=load(public/'manifest.json');graph=load(public/'graph.json')
    material=load(public/'materialization.json');task=load(public/'task-readback.json')
    descriptor=load(public/'instruction-descriptor.json');capsule=load(public/'native-capsule.json')
    compiled=load(public/'compilation-receipt.json');context=load(public/'context-preparation.json')
    native=read(public/'native-prompt.txt').decode();prompt=basis['call']['user_prompt']
    projection=context['semantic']['ducklake']
    require(projection['status']=='projected' and projection['stored_catalogs']==projection['stored_links']==2
            and projection['stored_bindings']==0 and projection['authoritative']is False,
            'native-fixture:genuine-native-DuckLake-metadata-projection-required')
    require(owner['qualified']is True and owner['task_completed']is False and task['status']=='ready'
            and task['validation_executed']is False and owner['START_called']is False
            and owner['worker_dispatched']is False,'native-fixture:actual-pending-preparation-only')
    compare_tree(admission['manifest'],manifest,'native-fixture:complete-signed-manifest')
    compare_tree(admission['graph'],graph,'native-fixture:complete-signed-graph')
    verify_public_signature(manifest,'native-fixture-manifest')
    verify_public_signature(admission['receipt'],'native-fixture-admission')
    require(manifest['binding']['identity']==admission['receipt']['binding']['identity'] and
            manifest['binding']['profile_id']==admission['receipt']['binding']['profile_id'],
            'native-fixture:one-public-signing-profile-no-origin-inference')
    selected=manifest['payload'];receipt=admission['receipt']['payload']
    require(receipt['manifest_cid']==structured(manifest)==material['manifest_cid']==owner['manifest_cid']
            and receipt['pending_cid']==material['pending_cid']==owner['pending_cid']
            and receipt['plan_id']==material['plan_id']==owner['plan_id'],
            'native-fixture:exact-local-plan-pending-manifest-joins')
    require(receipt['planning_permitted']is True and receipt['completion_authority']is False
            and receipt['code_proof_authority']is False and len(graph['tasks'])==1,
            'native-fixture:administrative-admission-not-code-proof-or-completion')
    require(graph['tasks'][0]['task_key']==owner['task_id']==task['task_alias']
            and material['task_cids']==[owner['task_cid']]==[task['task_cid']],
            'native-fixture:one-actual-pending-task')
    sources={**basis['sources'],'build/task-instruction.txt':prompt.encode()}
    require(set(selected['sources'])==set(sources),'native-fixture:all-four-signed-inputs')
    for path,raw in sources.items():
        require(selected['sources'][path]=={'sha256':sha(raw),'executable':False}
                and owner['source_inventory'][path]=={'sha256':sha(raw),'bytes':len(raw)},
                'native-fixture:exact-four-source-byte-and-mode-joins:'+path)
    require(sum(map(len,basis['sources'].values()))==195 and len(prompt.encode())==67,
            'native-fixture:195Python-plus67byte-separate-instruction')
    snapshot=basis['manifest']['snapshot']
    require(owner['baseline_commit']==selected['baseline_commit']==snapshot['git_commit'] and
            owner['git_tree']==snapshot['git_tree'],'native-fixture:host-and-container-same-exact-Git-baseline')
    decode_git_bundle(read(public/'source.gitbundle'),owner['baseline_commit'],owner['git_tree'],sources)
    native_fields={'contract_version','repository_id','tree_id','objective_id','objective_revision','policy_id',
        'policy_revision','caller','stage','goal','authority','scope','acceptance','evidence'}
    rendered={key:capsule[key]for key in native_fields}
    require(canonical(rendered).decode()==native,'native-fixture:own-complete-capsule-render-reconstruction')
    require(capsule['omissions']==[] and capsule['truncated']is False and
            native.encode() and sha(native.encode())==owner['native_prompt']['sha256']
            and len(native.encode())==owner['native_prompt']['bytes'],
            'native-fixture:complete-untruncated-original-native-input')
    require(rendered['objective_id']==owner['task_id'] and rendered['goal']['task_cid']==owner['task_cid']
            and rendered['scope']['allowed_paths']==['caller.py'],'native-fixture:exact-admitted-output-scope')
    grouped={}
    for reference in rendered['evidence']:
        require(reference['metadata']['required']is True,'native-fixture:each-original-context-chunk-required')
        chunk=reference['summary'].encode()
        require(reference['byte_count']==len(chunk) and
                reference['referenced_content_id']=='sha256:'+sha(chunk),
                'native-fixture:exact-native-evidence-chunk:'+reference['reference_id'])
        grouped.setdefault(reference['kind'],[]).append(reference)
    require(set(grouped)=={'semantic-context','world-context'},'native-fixture:closed-native-evidence-families')
    restored={}
    for kind,rows in grouped.items():
        ordered=sorted(rows,key=lambda x:x['metadata']['chunk_index'])
        require([x['metadata']['chunk_index']for x in ordered]==list(range(len(rows))) and
                all(x['metadata']['chunk_count']==len(rows)for x in rows),
                'native-fixture:all-contiguous-native-context-chunks:'+kind)
        raw=''.join(x['summary']for x in ordered).encode()
        require(all(x['metadata']['artifact_content_id']=='sha256:'+sha(canonical({'text':raw.decode()}))for x in rows),
                'native-fixture:whole-native-source-artifact-hash:'+kind)
        restored[kind]=parse(raw)
    semantic=restored['semantic-context']
    require(semantic['raw_sources']=={p:raw.decode()for p,raw in basis['sources'].items()}
            and semantic['required_raw_paths']==sorted(basis['sources']) and len(semantic['capsules'])==6,
            'native-fixture:all195bytes-and-six-native-capsules-direct')
    require(semantic['semantic_root_cid']==owner['semantic_root_cid']==context['semantic_root_cid'] and
            semantic['completion_authority']is False,'native-fixture:native-semantic-domain-exact-root')
    # Native semantic producer IDs are deliberately separate from the checked
    # CodebaseIR head. Only exact original paths/bytes and Git baseline join them.
    require(semantic['scope_cid']!=basis['head']['snapshot_cid'],
            'native-fixture:distinct-semantic-and-checked-identity-domains')
    for p,raw in basis['sources'].items():
        require(semantic['manifest'][p]['sha256']==sha(raw) and
                semantic['manifest'][p]['source_cid']==cid(raw,85),
                'native-fixture:semantic/checked/signed-three-way-byte-join:'+p)
    require(owner['context_bundle']==load(public/'context-bundle.json'), 'native-fixture:exact-native-context-nomination')
    instruction={'schema':'supervisor-public-instruction@1','repository':'/app','task_cid':owner['task_cid'],
        'task_id':owner['task_id'],'manifest':manifest,'manifest_cid':structured(manifest),
        'owner_identity':manifest['binding']['identity'],'owner_profile_id':manifest['binding']['profile_id'],
        'source_path':'build/task-instruction.txt','source_sha256':sha(prompt.encode()),'source_bytes':len(prompt.encode()),
        'completion_authority':False,'publication_authority':False,'scope_expansion_authority':False}
    instruction['context_cid']=structured(instruction)
    instruction_raw=json.dumps(instruction,sort_keys=True,indent=2).encode()+b'\n'
    require(descriptor['sha256']==sha(instruction_raw) and descriptor['context_cid']==instruction['context_cid']
            and descriptor['source_sha256']==sha(prompt.encode()) and descriptor['source_bytes']==67,
            'native-fixture:own-exact-readonly-public-instruction-artifact-reconstruction')
    for name in ('owner-receipt.json','materialization.json','context-preparation.json','instruction-descriptor.json'):
        ceiling(load(public/name),'native-fixture:'+name)
    counts.update(native_pending_tasks=1,native_signed_inventory_files=4,native_semantic_source_files=3,
                  original_Python_bytes=195,separate_instruction_bytes=67)
    return {'owner':owner,'manifest':manifest,'admission':admission,'graph':graph,'native_prompt':native,
            'descriptor':descriptor,'instruction_payload':instruction,'instruction_bytes':instruction_raw,
            'semantic':semantic,'world':restored['world-context']}


def own_checked_extension(preflight,packet,binding,policy,native_fixture):
    checked=preflight['checked_inclusion'];owner=native_fixture['owner'];native=native_fixture['native_prompt']
    descriptor=native_fixture['descriptor'];scope=[]
    view=parse(packet,floats=False)['payload']['model_view']
    for row in view['original_sources']:scope.append({key:row[key]for key in ('path','sha256','bytes','source_cid')})
    flags={'proof_authority','execution_authority','mutation_authority','completion_authority','publication_authority',
        'scope_expansion_authority','current_owner_verified','live_budget_owner_verified','serialized_live_authority',
        'global_task_budget_enforced','durable_budget_resume_supported','source_semantics_verified','runtime_behavior_verified',
        'source_to_model_equivalence_proved','training_convergence_proved','full_task_satisfaction',
        'external_boundary_verified_here','semantic_replay_performed'}
    instruction={key:descriptor[key]for key in ('artifact','context_cid','source_path','source_sha256','source_bytes')}
    instruction['artifact_sha256']=descriptor['sha256']
    task={'task_id':owner['task_id'],'task_cid':owner['task_cid'],
        'admission_manifest_cid':structured(native_fixture['manifest']),'admission_cid':structured(native_fixture['admission']),
        'native_prompt_sha256':sha(native.encode()),'native_prompt_bytes':len(native.encode())}
    domains={'native':'signed_task_source_inventory_including_literal_instruction',
        'checked':'exact_three_python_sources_in_declared_dataset_head',
        'join':'exact_relative_paths_and_original_bytes_not_cross_domain_CID_equality',
        'excluded_native_inputs':'explicit_signed_instruction_is_outside_checked_python_scope'}
    value={'schema':'supervisor-checked-audit-context@1','repository':'/app','admission':native_fixture['admission'],
        'task':task,'instruction':instruction,'native_semantic':preflight['semantic_verification'],
        'checked_binding':binding,'context_packet':packet,'context_sha256':sha(packet.encode()),'context_bytes':len(packet.encode()),
        'budget_policy':policy,'source_scope':scope,'signed_instruction':{'path':instruction['source_path'],
            'sha256':instruction['source_sha256'],'bytes':instruction['source_bytes']},
        'inventory_domains':domains,'scope':'advisory_checked_context_observer_only',**dict.fromkeys(flags,False)}
    value['extension_cid']=structured(value);raw=canonical(value)
    actual=preflight['descriptor']
    require(read(W/'native-worker-public-readback-02/checked-context.json')==raw,
            'checked:independently-reconstructed-extension-equals-actual-protected-public-readback')
    require(read(W/'native-worker-public-readback-02/public-instruction.json')==native_fixture['instruction_bytes'],
            'checked:independently-reconstructed-instruction-equals-actual-protected-public-readback')
    require(actual['sha256']==sha(raw) and actual['bytes']==len(raw) and
            actual['extension_cid']==value['extension_cid'],'checked:own-complete-extension-artifact-reconstruction')
    suffix=CHECKED_PREFIX+packet+CHECKED_SUFFIX
    expected={'schema':'supervisor-checked-audit-context-inclusion@1','artifact':actual['artifact'],
        'artifact_sha256':sha(raw),'artifact_bytes':len(raw),'extension_cid':value['extension_cid'],**task,
        'instruction_context_cid':instruction['context_cid'],'instruction_artifact_sha256':instruction['artifact_sha256'],
        'instruction_source_path':instruction['source_path'],'instruction_source_sha256':instruction['source_sha256'],
        'instruction_source_bytes':instruction['source_bytes'],'checked_binding':binding,
        'native_semantic':preflight['semantic_verification'],'budget_policy':policy,
        'context_sha256':sha(packet.encode()),'context_bytes':len(packet.encode()),'suffix_sha256':sha(suffix.encode()),
        'suffix_bytes':len(suffix.encode()),'source_scope':scope,'signed_instruction':value['signed_instruction'],
        'worker_binding':checked['worker_binding'],'inventory_domains':domains,'scope':value['scope'],
        'manifest_signature_verified':True,'source_inventory_join_verified':True,'packet_bytes_bound':True,
        **dict.fromkeys(flags,False)}
    compare_tree(checked,expected,'checked:own-closed-complete-native-inclusion-reconstruction')
    require(preflight['checked_suffix']==suffix,'checked:exact-complete-guidance-and-original-packet-suffix')
    return expected,suffix


def audit_worker(summary,basis,native_fixture):
    view=basis['view'];native=basis['native'];call=basis['call'];head=basis['head']
    packet=read(R/'view-packet.json').decode();expanded=read(R/'expanded-packet.json').decode()
    values={name:parse(text,floats=False)for name,text in [('view',packet),('expanded',expanded)]}
    for name,value in values.items():
        require(canonical(value).decode()==({'view':packet,'expanded':expanded}[name]),'packet:exact-canonical:'+name)
        compare_tree(value['head'],head,'packet:whole-checked-head:'+name)
        require(value['audit_view_id']==view['view_id'] and value['representation']==name,
                'packet:exact-representation-and-shared-view:'+name)
        ceiling(value,'packet:'+name)
    compare_tree(values['view']['payload'],{'model_view':view},'packet:complete-view-input')
    compare_tree(values['expanded']['payload'],{'native_semantic_audit':native,'code_view_audit':basis['views'],
        'checked_call_context':view['checked_call_context']},'packet:complete-expanded-counterfactual-input')
    compare_tree({k:v for k,v in values['view'].items()if k not in {'representation','payload'}},
        {k:v for k,v in values['expanded'].items()if k not in {'representation','payload'}},
        'packet:only-representation/payload-differ-in-whole-pair')
    identity(view,'view_id','view:whole-original-checked-view')
    retained={k:v for k,v in native.items()if k not in {'schema','capsule_set_id','repository_state','blocks','artifact_facts'}}
    compare_tree(view['native_view']['retained_fields'],retained,'view:all-native-facts-links-bindings-and-limitations-direct')
    independent_registry(native,view)
    for row in view['original_sources']:
        require(row['text'].encode()==basis['sources'][row['path']] and row['raw_source_required']is True,
                'view:exact-original195bytes-direct:'+row['path'])
    compare_tree(parse(view['checked_call_context'],floats=False)['context']['capsule'],basis['capsule'],
                 'view:whole-original-assumptions-domain-residual-proof-closure-direct')
    preflight=load(R/'native-preflight.json');binding=load(R/'budget-binding.json');policy=load(R/'budget-policy.json')
    require(binding=={'schema':'terminal-semantic-context-budget-binding@1','head':head,'view_id':view['view_id'],
        'reference_basis_cid':view['expansion_directory']['reference_basis_cid'],'native_root_cid':view['native_root_cid'],
        'capsule_set_id':view['capsule_set_id'],'state_cid':view['state_cid']},'budget:exact-current-whole-source-proof-view-binding')
    checked,suffix=own_checked_extension(preflight,packet,binding,policy,native_fixture)
    native_prompt=native_fixture['native_prompt'];literal=call['user_prompt'];block=instruction_block(literal)
    require(preflight['router_prompt']==native_prompt+block,'coding:own-original-native-and-literal-instruction-composition')
    require(preflight['checked_inclusion']['worker_binding']['workspace']==preflight['workspace'],
            'coding:exact-allocated-workspace-bound-to-checked-context')
    prepared=load(R/'native-budget-preparation.json');trace=load(R/'native-budget-trace.json')
    event=prepared['event'];measurements={key:event[key]['text'].encode()for key in ('new_content','rendered_input')}
    expected={key:{k:event[key][k]for k in ('bytes','sha256','tokens')}for key in measurements}
    encoding=tokenize_packets(measurements,{'measures':expected})
    identity(prepared,'preparation_cid','budget:whole-original-preparation')
    require(prepared['basis']['native_prompt']==native_prompt and prepared['basis']['router_prompt']==native_prompt+block
            and prepared['basis']['checked_suffix']==suffix and prepared['basis']['worker_workspace']==preflight['workspace'],
            'budget:complete-original-native-source-instruction-and-checked-context-basis')
    require(event['new_content']['text']==native_prompt+block+suffix and
            event['rendered_input']['text']==coding_advisory(preflight['workspace'])+native_prompt+block+suffix,
            'coding:independent-full-model-input-with-all-native-guidance-and-metadata')
    require(trace['closed']is True and len(trace['records'])==1 and trace['records'][0]['status']=='committed'
            and trace['records'][0]['event']==event,'budget:one-actual-native-attempt-conservatively-committed')
    totals=replay_coding_ledger(trace,encoding,preflight['workspace'],'actual-native-worker')
    compare_tree(trace['binding'],binding,'budget:original-live-binding-retained')
    compare_tree(trace['policy'],policy,'budget:original-complete-live-policy-retained')
    compare_tree(summary['totals'],totals,'budget:summary-all-eight-exact-cumulative-totals')
    compare_tree(summary['whole_coding_input'],expected['rendered_input'],'coding:summary-whole-input-counts')
    compare_tree(summary['new_content'],expected['new_content'],'coding:summary-complete-router-content-counts')
    material=prepared['materialization']
    for name,text in [('native_prompt',native_prompt),('router_prompt',native_prompt+block+suffix),
                      ('model_prompt',event['rendered_input']['text']),('workspace_advisory',coding_advisory(preflight['workspace']))]:
        compare_tree(material[name],{'sha256':sha(text.encode()),'bytes':len(text.encode())},'coding:exact-materialization:'+name)
    observation=load(R/'native-observation.json');raw_worker=read(R/'worker-01.stdout')
    require(type(observation)is dict and set(observation)==set(['checked_context', 'code_retrieval_codec', 'code_retrieval_projection', 'code_retrieval_wire_delivery', 'completion_authority', 'doctor_residual_context', 'error_type', 'execution_authority', 'external_container_boundary', 'final_custody_guard_verified', 'intent_requirements_transport', 'model_prompt_bytes', 'model_prompt_sha256', 'native_prompt_bytes', 'native_prompt_sha256', 'native_rollout_usage', 'observation_id', 'prompt_bytes', 'prompt_sha256', 'proof_authority', 'provider_attempted', 'public_instruction', 'purpose', 'reasoning_effort', 'requested_model', 'requested_output_tokens', 'requested_provider', 'reviewed_source_nomination_context', 'router_calls', 'router_prompt_bytes', 'router_prompt_sha256', 'schema', 'seconds', 'semantic_context_verification', 'semantic_translation', 'semantic_transport', 'status', 'timeout_seconds', 'usage', 'wire_delivery_cleanup_status', 'wire_delivery_post_observation_verified', 'workspace', 'workspace_advisory_bytes', 'workspace_advisory_sha256']),
            'worker:exact-closed-version2-observation-no-dropped-or-extra-fields')
    import math
    require(type(observation['seconds'])in{int,float}and math.isfinite(observation['seconds'])
            and 0<=observation['seconds']<=86400,'worker:exact-finite-native-seconds-retained')
    compare_tree(parse(raw_worker),observation,'worker:entire-actual-stdout-is-one-exact-native-observation')
    require(observation['schema']=='supervisor-model-input-observation@2' and observation['status']=='observed'
            and observation['provider_attempted']is False and observation['router_calls']==0
            and observation['usage']is None and observation['native_rollout_usage']is None
            and observation['final_custody_guard_verified']is True,'worker:distinct-observer-stop-no-provider-call')
    require(observation['requested_model']=='authored-offline-observer' and observation['timeout_seconds']==30
            and observation['requested_output_tokens']==128 and observation['purpose']=='coding',
            'worker:exact-unattempted-model-and-bounded-coding-controls')
    for name,value in material.items():
        if name in {'native_prompt','router_prompt','model_prompt','workspace_advisory'}:
            require(all(observation[name+'_'+metric]==value[metric]for metric in ('sha256','bytes')),
                    'worker:actual-complete-input-byte-hash-join:'+name)
    compare_tree(observation['checked_context'],checked,'worker:entire-closed-checked-inclusion')
    compare_tree(observation['semantic_context_verification'],preflight['semantic_verification'],'worker:native-source-verification-join')
    compare_tree(observation['public_instruction'],preflight['instruction_receipt'],'worker:exact-readonly-instruction-inclusion')
    compare_tree(observation['external_container_boundary'],prepared['basis']['boundary'],'worker:exact-protected-namespace-boundary')
    instruction=observation['public_instruction']
    require(instruction['block_sha256']==sha(block.encode()) and instruction['block_bytes']==len(block.encode())
            and instruction['source_sha256']==sha(literal.encode()) and instruction['source_bytes']==67,
            'worker:whole-literal-readonly-instruction-framing-counted')
    for field in ('semantic_translation','code_retrieval_projection','doctor_residual_context','reviewed_source_nomination_context',
                  'wire_delivery_post_observation_verified','wire_delivery_cleanup_status'):
        require(observation[field]is None,'worker:no-extra-unaccounted-route:'+field)
    require([observation[k]for k in ('semantic_transport','intent_requirements_transport','code_retrieval_codec','code_retrieval_wire_delivery')]
            ==['native','expanded','expanded','inline'],'worker:closed-selected-native-observer-profile')
    result=load(R/'budgeted-native-observation.json');identity(result,'result_cid','budget:whole-committed-native-observation-result')
    envelope=result['observation'];identity(envelope,'receipt_cid','budget:lossless-float-preserving-native-receipt-envelope')
    expected_raw=canonical(observation)
    require(envelope['canonical_json'].encode()==expected_raw and envelope['sha256']==sha(expected_raw)
            and envelope['bytes']==len(expected_raw),'budget:all-native-receipt-fields-retained-without-rounding')
    require(result['event_cid']==event['event_cid'] and result['preparation_cid']==prepared['preparation_cid']
            and result['budget_snapshot']['records']==trace['records'] and result['budget_snapshot']['closed']is False,
            'budget:exact-committed-prefix-before-owner-close')
    require(result['worker_origin_independently_verified']is False and result['current_owner_verified']is False
            and result['complete_rendered_input_join_verified']is True and result['local_budget_reservation_committed']is True,
            'budget:pure-helper-byte-join-never-child-origin-authority')
    replay_coding_ledger(result['budget_snapshot'],encoding,preflight['workspace'],'committed-native-prefix')
    launch=load(R/'worker-01-launch.json')
    require(launch['returncode']==75 and launch['stdin_sha256']==sha(native_prompt.encode())
            and launch['stdin_bytes']==len(native_prompt.encode()),'worker:actual-stop75-and-original-stdin-hash')
    argv=launch['argv']
    require(argv[:5]==['docker','exec','-i','--user','supervisor'] and
            '/opt/ipfs-supervisor/bin/router-worker'in argv and '--observe-model-input-only'in argv,
            'worker:actual-controlled-Docker-owner-launch-of-protected-router')
    require(summary['native_admitted_benchmark_runtime_START_used']is False and
            summary['full_supervisor_entrypoint_used']is False and summary['Terminal_Bench_harness_used']is False,
            'scope:direct-native-worker-distinct-from-supervisor-START-and-Terminal-Bench')
    for join in summary['snapshot_joins']:
        require(join['snapshot_cid']==head['snapshot_cid'] and join['git_commit']==basis['manifest']['snapshot']['git_commit']
                and join['git_tree']==basis['manifest']['snapshot']['git_tree'],'worker:current-container/host-exact-source-snapshot-join')
    require(len(summary['snapshot_joins'])>=2,'worker:before-and-after-current-source-observations-retained')
    historical=load(R/'historical-replay.json');cleanup=load(R/'cleanup.json')
    require(historical['passed']is True and all(value is True for value in historical['checks'].values())
            and historical['model_sha256']==observation['model_prompt_sha256']
            and historical['model_bytes']==observation['model_prompt_bytes'] and historical['allocated_worktree_absent']is True,
            'worker:exact-native-historical-replay-after-worktree-removal')
    require(cleanup['cleanup_returncode']==0 and cleanup['remaining_worker_pids']==[] and cleanup['worktree_removed']is True,
            'worker:actual-cleanup-no-remaining-worker-processes')
    controls=summary['controls']
    for index,control in enumerate(controls,1):
        compare_tree(load(R/('control-%02d.json'%index)),control,'controls:exact-retained-outcome:'+str(index))
        require(control['rejected']is True,'controls:actual-rejection:'+control['name'])
    require(any('retry-over-cumulative-token-budget'in x['name']for x in controls) and
            any('expanded-complete-native-input-exceeds-byte-bound'in x['name']for x in controls),
            'controls:retry-and-expanded-refused-before-actual-worker')
    proposed_retry_tokens=event['rendered_input']['tokens']
    require(totals['rendered_input_tokens']+proposed_retry_tokens>policy['max_rendered_input_tokens'],
            'controls:own-independent-cumulative-repeat-input-over-budget')
    expanded_model=coding_advisory(preflight['workspace'])+native_prompt+block+CHECKED_PREFIX+expanded+CHECKED_SUFFIX
    require(len(expanded_model.encode())>256000,'controls:own-complete-expanded-native-model-byte-bound')
    expanded_measure=own_measure(expanded_model,encoding,'counterfactual-expanded-full-coding-input')
    local_delta=expanded_measure['tokens']-event['rendered_input']['tokens']
    require(local_delta>0,'tokens:conditional-fixture-view-reduces-counterfactual-expanded-complete-input')
    comparison=load(W/'coding-input-comparison-02.json')
    compare_tree(comparison['observed'],expected['rendered_input'],'tokens:standalone-comparison-observed-complete-input')
    compare_tree(comparison['expanded_counterfactual'],{k:expanded_measure[k]for k in ('bytes','sha256','tokens')},
                 'tokens:standalone-comparison-expanded-complete-counterfactual')
    require(comparison['local_input_token_difference']==local_delta and
            comparison['local_input_token_reduction_percent']==round(local_delta*100/expanded_measure['tokens'],4)and
            comparison['counterfactual_dispatched']is False and comparison['counterfactual_valid_checked_artifact']is False
            and comparison['provider_usage_measured']is False and comparison['task_total_savings_measured']is False,
            'tokens:exact-local-comparison-with-no-expanded/provider/task-savings-claim')
    ast.parse(read(W/'count_coding_inputs_02.py'),filename='count_coding_inputs_02.py')
    resources=summary['resources_after']
    require(resources['active_lease_count']==resources['waiting_request_count']==0,'resources:all-current-review-capacity-released')
    require(summary['actual_native_worker_observer_invocations']==1 and summary['actual_router_calls']==0
            and summary['provider_calls']==0 and summary['provider_output_tokens']is None,
            'scope:one-actual-worker-observer-zero-provider-calls-no-billing-claim')
    for value,name in [(observation,'native-observation'),(checked,'checked-inclusion'),(result,'pure-budget-result'),(summary,'actual-summary')]:
        ceiling(value,name)
    counts.update(actual_native_worker_observer_invocations=1,actual_provider_calls=0,
        complete_native_coding_input_tokens=event['rendered_input']['tokens'],
        complete_native_coding_input_bytes=event['rendered_input']['bytes'],
        new_router_content_tokens=event['new_content']['tokens'],controls=len(controls),
        independent_expanded_complete_model_bytes=len(expanded_model.encode()),
        independent_retry_proposed_input_tokens=proposed_retry_tokens,
        counterfactual_expanded_complete_coding_input={k:expanded_measure[k]for k in ('bytes','sha256','tokens')},
        conditional_local_view_input_token_delta=local_delta,
        conditional_local_view_reduction_basis_points=local_delta*10000//expanded_measure['tokens'],
        counterfactual_expanded_artifact_admitted=False,counterfactual_expanded_worker_dispatched=False,
        provider_or_whole_task_billing_savings_measured=False,
        cumulative_input_claim_scope='all actually charged single coding attempts; no conversation-history delivery or provider billing claim')


def apply_text_patch(patch,baselines):
    """Independently apply bounded unified source hunks, with exact old context."""
    import re
    result={}
    for section in patch.split(b'diff --git ')[1:]:
        lines=section.splitlines(keepends=True)
        target=next(line[6:].strip().decode()for line in lines if line.startswith(b'+++ b/'))
        require(target not in result and '..'not in Path(target).parts and not Path(target).is_absolute(),
                'package:unique-relative-target:'+target)
        old=baselines.get(target,b'');oldlines=old.splitlines(keepends=True);cursor=0;output=[];position=0
        while position<len(lines):
            match=re.match(rb'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@',lines[position])
            if match is None:position+=1;continue
            old_start=int(match[1]);old_count=int(match[2]or b'1');new_count=int(match[4]or b'1')
            start=old_start-1 if old_count else old_start
            require(cursor<=start<=len(oldlines),'package:ordered-old-hunk:'+target)
            output.extend(oldlines[cursor:start]);cursor=start;position+=1;seen_old=seen_new=0
            while position<len(lines)and not lines[position].startswith(b'@@ '):
                line=lines[position]
                if not line.startswith((b' ',b'+',b'-')):break
                kind=line[:1];payload=line[1:];position+=1
                if position<len(lines)and lines[position].startswith(b'\\ No newline at end of file'):
                    payload=payload.removesuffix(b'\n');position+=1
                if kind in (b' ',b'-'):
                    require(cursor<len(oldlines)and oldlines[cursor]==payload,'package:exact-original-context:'+target+':'+str(cursor))
                    cursor+=1;seen_old+=1
                if kind in (b' ',b'+'):output.append(payload);seen_new+=1
            require((seen_old,seen_new)==(old_count,new_count),'package:exact-hunk-line-counts:'+target)
        output.extend(oldlines[cursor:]);result[target]=b''.join(output)
    return result


def audit_preservation():
    previous=load(PREVIOUS/'evidence-manifest.json')
    require(previous['explicit_named_file_count']==len(previous['files'])==276,'preservation:276-sealed-Y-named-files-plus-seal')
    for item in previous['files']:read(item['path'],item)
    baseline=load(W/'preservation-baseline.json')
    retained_previous=baseline['sealed_previous_files']
    require(type(retained_previous)is list and len(retained_previous)==baseline['verified_file_occurrences']==277,
            'preservation:original-Y-census-retained')
    expected_previous={item['path']:item for item in previous['files']}
    previous_manifest=str(PREVIOUS/'evidence-manifest.json')
    expected_previous[previous_manifest]=captures[previous_manifest]['pin']
    compare_tree({item['path']:item for item in retained_previous},expected_previous,
                 'preservation:exact-276-Y-named-pins-plus-seal')
    pin_declared(retained_previous)
    assets=load(W/'source-assets.json')
    require(len(assets['files'])==5 and assets['no_database_bodies']is True,'preservation:five-public-SQL-source-assets')
    for item in assets['files']:
        expected={'bytes':item['bytes'],'sha256':item['sha256']}
        require(read(item['source'],expected)==read(item['target'],expected),'preservation:exact-public-SQL-supplement:'+item['target'])
    snapshot=load(W/'native-source-snapshot.json')
    require(snapshot['source_only_projection']is True and snapshot['model_assets_or_runtime_data_copied']is False
            and snapshot['original_sources_edited']is False and snapshot['original_index_written']is False,
            'preservation:source-copy-scope-not-import-closure-attestation')
    counts.update(preserved_Y_named_files=276,preserved_Y_files_plus_seal=277,public_SQL_source_supplements=5,
                  source_copy_inventory_entries=snapshot['file_count'])


def audit_proof(basis):
    model=load(A/'model/result.json');prepared=load(A/'prepared.json');qualification=load(A/'qualification-summary.json')
    compare_tree(prepared['head'],basis['head'],'proof:fresh-Z-current-head')
    require(model['model_status']=='model_proved' and qualification['model_status']=='model_proved'
            and qualification['rows']==49 and len(qualification['families'])==20,'proof:conditional-model-49rows20families')
    processes=load(A/'model/callee/native-lowering/lean_process.json');caller=load(A/'model/process.json')
    require(len(processes)==2,'proof:callee-version-and-compile-receipts')
    for name,item in [*processes.items(),('caller',caller)]:
        require(item['returncode']==0 and item['termination_reason']=='completed'
                and '/leanprover--lean4---v4.34.1/bin/lean'in item['command'][0],
                'proof:three-fresh-successful-pinned-Lean-process-receipts:'+name)
    for value in (model,basis['capsule']['producer'],basis['capsule']['expansion'],basis['query']['producer']):
        pin_declared(value)
    ceiling(model,'proof:fresh-conditional-model-record')
    counts.update(conditional_metadata_rows=49,conditional_metadata_families=20,application_Lean_process_receipts=3,
                  reviewer_prover_invocations=0)


def audit_boundary():
    actual=load(W/'docker-boundary-02/result.json');install=load(W/'docker-boundary-02/installation/installation.json')
    qualification=load(W/'docker-boundary-02/qualification/qualification.json')
    require(actual['qualified']is True and qualification['qualified']is True and
            install['observer_only']is True and install['provider_assets_required']is False,
            'boundary:actual-native-installer-and-permission-qualification-selected')
    permission=qualification['permission_evidence']
    require(permission['uid']==1001 and permission['candidate_write']is True and
            len(permission['private_denials'])==6 and qualification['remaining_worker_pids']==[],
            'boundary:actual-UID1001-write-six-denials-and-termination-probe')
    boundary=install['boundary'];profile=install['deployment_profile']
    require(boundary['schema']=='supervisor-container-worker-boundary@1' and
            profile=={'schema':'container-worker-deployment-profile@1','observer_only':True,
                'boundary_sha256':install['boundary_sha256']},'boundary:unchanged-typed-boundary-and-explicit-root-profile')
    boundary_raw=json.dumps(boundary,sort_keys=True,indent=2).encode()+b'\n'
    require(sha(boundary_raw)==install['boundary_sha256'] and
            sha(canonical(profile)+b'\n')==install['deployment_profile_sha256'],
            'boundary:independent-protected-artifact-bytes-and-hashes')
    require(actual['network']=='none' and actual['credentials_transferred']is False and
            actual['provider_calls']==0 and actual['native_admission_created']is False,
            'boundary:provider-free-offline-probes-not-native-admission')
    load(W/'docker-boundary-02/launch.json');load(W/'docker-boundary-02/container-public-identity.json')
    load(W/'docker-boundary-02/final-public-identity.json')
    counts.update(actual_boundary_permission_denials=6,actual_boundary_worker_uid=1001,
                  actual_boundary_remaining_worker_processes=0)



def audit_final_public_readbacks():
    prerequisite=load(W/'offline-duckdb-prerequisite.json')
    require(prerequisite['schema']=='checked-worker-offline-duckdb-extension-prerequisite@1'
            and prerequisite['cached_image_public_extensions_used']is True
            and prerequisite['database_bodies_copied']is False and prerequisite['extension_bodies_exported']is False
            and prerequisite['network_used']is False
            and prerequisite['native_load']=={'duckdb_version':'1.5.5','native_offline_ducklake_load_passed':True,'network_used':False},
            'environment:explicit-offline-public-extension-cache-prerequisite')
    require(len(prerequisite['files'])==3 and
            {Path(x['source']).name for x in prerequisite['files']}==
            {'ducklake.duckdb_extension','httpfs.duckdb_extension','quack.duckdb_extension'},
            'environment:exact-three-public-extension-metadata-records-no-body-read')
    for item in prerequisite['files']:
        require(item['source']=='/home/supervisor/.duckdb/extensions/v1.5.5/linux_arm64/'+Path(item['source']).name
                and item['target']=='/opt/ipfs-supervisor/home/.duckdb/extensions/v1.5.5/linux_arm64/'+Path(item['source']).name
                and item['target_uid']==1000 and item['mode']=='0o444' and type(item['bytes'])is int
                and item['bytes']>0 and len(item['sha256'])==64,
                'environment:bounded-reported-public-image-extension-cache-join:'+Path(item['source']).name)
    deployed=load(W/'deployed-runtime-source-pins-02.json')
    require(deployed['exact_copies']is True and len(deployed['files'])==10
            and deployed['credential_bodies_included']is False and deployed['loaded_module_code_attested']is False
            and deployed['transitive_dependency_closure_attested']is False,
            'deployed:ten-exact-current-source-readbacks-no-loaded-code-attestation')
    for item in deployed['files']:
        read(item['path'],item)
        require(item['uid']==item['gid']==0 and item['mode']=='0o444' and item['singlelink']is True
                and item['container_path']=='/opt/ipfs-supervisor/source/'+item['relative_path']
                and item['path']==str(C/item['relative_path']),
                'deployed:protected-exact-host/worker-runtime-source:'+item['relative_path'])
    public=load(W/'native-worker-public-readback-02.json')
    require(len(public['files'])==2 and public['credentials_included']is False and public['database_bodies_included']is False,
            'deployed:two-public-immutable-artifacts-only')
    for item in public['files']:
        read(item['path'],item)
        require(item['uid']==item['gid']==1000 and item['mode']=='0o444',
                'deployed:exact-native-owner-readonly-public-artifact:'+item['container_path'])
    task=load(W/'native-task-final-readback-02.json')
    require(task['unchanged']is True and task['completion_authority']is False and
            all(task['after'][key]==task['before'][key]for key in ('task_cid','task_alias','status','revision','event_watermark'))
            and task['after']['status']=='ready','native-owner:pending-task-revision-and-event-watermark-unchanged')
    disposal=load(W/'container-disposal-02.json')
    require(disposal['container']=='ipfs-checked-worker-context-z02' and disposal['stop_returncode']==disposal['remove_returncode']==0
            and disposal['container_absent']is True and disposal['only_owned_fixture_removed']is True
            and disposal['worker_cleanup_previously_verified']is True,'cleanup:only-owned-container-stopped-and-removed')
    inventory=load(W/'actual-public-inventory.json')
    require(len(inventory['files'])==inventory['explicit_named_file_count']==113 and
            len({x['path']for x in inventory['files']})==113 and inventory['declared_native_public_closure_matched']is True,
            'inventory:113-unique-explicit-native-public-source/proof/metadata-files')
    for item in inventory['files']:read(item['path'],item)
    require(all(inventory[key]is False for key in ('database_bodies_included','cas_bodies_included',
            'ducklake_parquet_bodies_included','recursive_traversal')),'inventory:no-private-or-recursive-body-scope')
    pin_declared(inventory['producer']);pin_declared(inventory['public_path_pattern'])
    preserved=load(W/'preservation-final.json')
    require(preserved['qualified']is True and preserved['all_expected_pins_unchanged']is True and
            preserved['checked_occurrences']==len(preserved['occurrences'])==356
            and preserved['sealed_predecessor_named_files']==276
            and preserved['sealed_predecessor_manifest_occurrences']==1 and preserved['baseline_dependency_occurrences']==79
            and preserved['occurrences_deduplicated']is False,'preservation:276-Y-files-plus-seal-plus79-dependency-occurrences')
    for item in preserved['occurrences']:
        require(item['unchanged']is True and item['expected']==item['actual'],
                'preservation:exact-nondeduplicated-occurrence:'+item['group']+':'+str(item['ordinal']))
        read(item['expected']['path'],item['expected'])
    pin_declared(preserved['predecessor_seal']);pin_declared(preserved['baseline']);pin_declared(preserved['producer'])
    counts.update(deployed_current_runtime_sources=10,protected_public_worker_artifacts=2,
                  explicit_public_inventory_files=113,preservation_occurrences=356,owned_container_disposed=True)


def audit_source():
    names=['benchmarks/agent_supervisor/container_coding/container_worker_deployment.py',
        'benchmarks/agent_supervisor/container_coding/terminal_checked_worker_budget.py',
        'ipfs_accelerate_py/agent_supervisor/runtime/checked_audit_context.py',
        'ipfs_accelerate_py/agent_supervisor/runtime/router_implementation_runner.py',
        'ipfs_accelerate_py/agent_supervisor/runtime/model_input_observation_receipt.py',
        'benchmarks/agent_supervisor/container_coding/terminal_context_audit.py',
        'benchmarks/agent_supervisor/container_coding/terminal_model_input_observation_audit.py']
    for name in names:ast.parse(read(C/name),filename=name)
    source=read(C/names[1]).decode();tree=ast.parse(source)
    funcs={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
    operation=funcs['transact_checked_worker_observation']
    reservations=[node for node in ast.walk(operation)if isinstance(node,ast.With)and
        any(isinstance(item.context_expr,ast.Call)and isinstance(item.context_expr.func,ast.Attribute)and
            isinstance(item.context_expr.func.value,ast.Name)and item.context_expr.func.value.id=='budget_owner'and
            item.context_expr.func.attr=='reserve'for item in node.items)]
    require(len(reservations)==1,'source:one-typed-owner-reservation-context')
    reservation=reservations[0]
    callbacks={name:[node for node in ast.walk(operation)if isinstance(node,ast.Call)and
                    isinstance(node.func,ast.Name)and node.func.id==name]
               for name in ('current_guard','launch_observer')}
    descendants={id(node)for node in ast.walk(reservation)}
    require(len(callbacks['current_guard'])==2 and len(callbacks['launch_observer'])==1
            and all(id(node)in descendants for nodes in callbacks.values()for node in nodes)
            and reservation.lineno<min(node.lineno for node in callbacks['current_guard'])<callbacks['launch_observer'][0].lineno,
            'source:original-live-reservation-before-both-current-guard-and-actual-launch')
    require('worker_origin_independently_verified' in source and 'caller_must_qualify_independently'in source,
            'source:pure-data-join-never-confers-child-origin')
    runner=read(C/names[3]).decode()
    require('checked_guard' in runner and '_guard_stack' in runner and
            'CHECKED_OBSERVATION_SCHEMA' in runner,'source:versioned-checked-route-with-retained-final-guards')
    checked=read(C/names[2]).decode()
    require(literal_assignment(checked,'PREFIX')==CHECKED_PREFIX and literal_assignment(checked,'SUFFIX')==CHECKED_SUFFIX,
            'source:independent-framing-constants-match-pinned-native-producer')
    deployment=read(C/names[0]).decode()
    require('observer_only: bool = False'in deployment and 'PROFILE_GUARD'in deployment and
            'profile=_worker_profile'in deployment and 'credential_setup'in deployment,
            'source:default-compatible-explicit-protected-observer-profile')
    ast.parse(read(W/'run_checked_worker_04.py'),filename='run_checked_worker_04.py')
    ast.parse(read(W/'prepare_native_fixture_05.py'),filename='prepare_native_fixture_05.py')
    ast.parse(read(W/'run_boundary_current_02.py'),filename='run_boundary_current_02.py')
    load(W/'entrypoint-integration-review.json');load(W/'observer-profile-focused-report.json')


def audit_package_and_tests():
    package=load(W/'review-package-02.json');files=package['sources'];bases={}
    require(package['schema']=='terminal-checked-worker-source-review-package@1' and
            package['counts']['source_files']==len(files)==14 and
            package['counts']['modified']==8 and package['counts']['new']==6,
            'package:exact14-source-test-files-eight-modified-six-new')
    for item in files:
        relative=item['relative_path'];left=read(item['source_pin']['path'],item['source_pin'])
        require(left==read(item['packaged_pin']['path'],item['packaged_pin'])==
                read(item['package_worktree_pin']['path'],item['package_worktree_pin']),
                'package:all-three-exact-final-source-copies:'+relative)
        for pin_name in ('source_pin','packaged_pin','package_worktree_pin'):
            own_pin=item[pin_name]
            require(captures[own_pin['path']]['mode']==own_pin['mode'],
                    'package:exact-declared-filesystem-mode:'+pin_name+':'+relative)
        source_mode=int(item['source_pin']['mode'],8)
        applied_mode=int(item['package_worktree_pin']['mode'],8)
        require(bool(source_mode&0o111)==bool(applied_mode&0o111),
                'package:independent-Git-executable-mode-match:'+relative)
        ast.parse(left,filename=relative)
        if item['baseline_pin']is None:
            require(item['change']=='new','package:new-files-have-no-fabricated-baseline:'+relative);bases[relative]=b''
        else:
            require(item['change']=='modified','package:existing-files-keep-real-baseline:'+relative)
            old=read(item['baseline_pin']['path'],item['baseline_pin']);bases[relative]=old
            git_blob=hashlib.sha1(('blob '+str(len(old))+'\0').encode()+old).hexdigest()
            require(git_blob==item['baseline_git_blob'],'package:exact-original-Git-blob:'+relative)
    patch=read(package['patch']['path'],package['patch'])
    decoded=apply_text_patch(patch,bases)
    require(set(decoded)=={item['relative_path']for item in files},'package:all-and-only14-independent-patch-targets')
    for item in files:require(decoded[item['relative_path']]==read(item['source_pin']['path']),
            'package:own-exact-unified-patch-application:'+item['relative_path'])
    applied=package['independent_apply'];preserved=package['original_preservation']
    require(applied['git_apply_check']['returncode']==applied['git_apply']['returncode']==0
            and applied['exact_all_source_bytes']is True and applied['checked_files']==14,
            'package:actual-fresh-scratch-application-matches-independent-decoder')
    require(applied['exact_all_git_executable_modes']is True and applied['exact_all_source_modes']is False
            and len(applied['filesystem_mode_differences'])==4,
            'package:four-disclosed-nonexecutable-filesystem-permission-differences')
    require(all(preserved[key]is True for key in ('head_unchanged','index_unchanged','status_unchanged','source_pins_unchanged')),
            'package:original-head-index-status-and-source-files-preserved')
    report=load(W/'final-combined-02-report.json');xml=ET.fromstring(read(W/'final-combined-02/results.xml'))
    cases=list(xml.iter('testcase'));ids=[(x.get('classname'),x.get('name'))for x in cases];totals=report['test_counts']
    require(len(cases)==len(set(ids))==totals['tests']==totals['unique_tests'],
            'tests:every-unique-executed-XML-case-enumerated')
    require(not list(xml.iter('failure'))and not list(xml.iter('error'))and not list(xml.iter('skipped'))and
            totals['failures']==totals['errors']==totals['skips']==report['exit_code']==0 and report['timed_out']is False,
            'tests:zero-failure-error-skip-timeout-and-zero-exit')
    suite_counts=dict(Counter(x.get('classname','').rsplit('.',1)[-1]for x in cases))
    compare_tree(suite_counts,report['per_suite_test_counts'],'tests:independently-enumerated-all13-suite-counts')
    require(len(suite_counts)==len(report['test_files'])==13,'tests:exact-thirteen-targeted-suite-files')
    for suite,expected_count in report['required_counts'].items():
        require(suite_counts.get(suite)==expected_count,'tests:independent-required-suite-count:'+suite)
    require(report['qualified_combined_test_run']is True and report['producer_bytes_unchanged']is True
            and report['changed_path_population_unchanged']is True and report['suite_bytes_unchanged']is True
            and report['required_counts_match']is True and report['changed_source_count']==14,
            'tests:complete-final-suite-and-all14-producer-pins-unchanged')
    compare_tree(report['pins_before'],report['pins_after'],'tests:exact-before-after-producer-pins')
    pin_declared(report['pins_before']);pin_declared(report['pins_after'])
    for name in ('testcase-ids.json','producer-pins-before.json','producer-pins-after.json','suite-pins-before.json','suite-pins-after.json'):
        load(W/'final-combined-02'/name)
    read(W/'final-combined-02/pytest.log')
    counts.update(final_unique_tests=len(cases),final_per_suite_test_counts=suite_counts,packaged_source_test_files=14,packaged_modified_files=8,
                  packaged_new_files=6,packaged_patch_bytes=len(patch))


def audit():
    require((W/'qualification-report.json').is_file(),'audit:root-declares-final-readiness-before-execution')
    summary=load(R/'summary.json');basis=audit_native_basis(summary)
    audit_boundary();audit_final_public_readbacks();native_fixture=audit_native_fixture(basis)
    audit_worker(summary,basis,native_fixture);audit_proof(basis);audit_source();audit_preservation();audit_package_and_tests()
    for name in ('qualification-report.json','improvement-status.json','development-history.json'):
        value=load(W/name);ceiling(value,'final-report:'+name)
    for name in ('write_final_reports.py','seal_final.py'):
        ast.parse(read(W/name),filename=name)
    counts.update(target_or_native_implementation_imports=0,provider_calls_by_reviewer=0,
        tests_run_by_reviewer=0,prover_invocations_by_reviewer=0,database_bodies_opened=False,
        CAS_bodies_opened=False,DuckLake_parquet_bodies_opened=False,
        native_admitted_benchmark_runtime_START_used=False,full_supervisor_entrypoint_used=False,
        Terminal_Bench_harness_used=False,provider_usage_measured=False,source_to_model_equivalence_proved=False,
        training_convergence_proved=False,full_task_satisfaction=False)


def finish(path):
    for name,value in captures.items():
        current=os.fstat(value['fd'])
        check(stamp(current)==value['stamp']==stamp(Path(name).lstat()),'closing-custody:'+name)
        os.lseek(value['fd'],0,os.SEEK_SET);digest=hashlib.sha256()
        while chunk:=os.read(value['fd'],1048576):digest.update(chunk)
        check(digest.hexdigest()==value['pin']['sha256'],'closing-retained-FD-bytes:'+name)
    result={'schema':'terminal-checked-worker-independent-review@1','passed':not failures,'qualified':not failures,
        'check_count':len(checks),'passed_checks':sum(x['passed']for x in checks),'failed_checks':len(failures),
        'failed':len(failures),'blockers':failures,'checks':checks,'counts':counts,
        'read_pins':[captures[name]['pin']for name in sorted(captures)],
        'input_custody':'retained named nofollow regular single-link FD/stat/SHA before and after; no recursive traversal',
        'review_independence_scope':'Separate source-import-free decoder, reconstruction, signature/Git/token/ledger checks. This agent previously implemented the observer deployment profile and performed the separately recorded container boundary/fixture operations; it is not an independent human/author review of that profile.',
        'read_only_execution':{'scope':'this final audit process only; earlier development and container operations are separate evidence', 'target_or_native_implementation_imports':0,'project_service_calls':0,
            'database_bodies_opened':False,'CAS_bodies_opened':False,'DuckLake_parquet_bodies_opened':False,
            'tests_run':0,'prover_invocations':0,'provider_calls':0,'training_steps':0,'source_body_executed':False,
            'source_or_sealed_files_edited':False,'network_fetches':0,'subprocesses':0,
            'only_nonstdlib_dependency':'pinned tiktoken0.13.0 directly constructed from retained local BPE bytes'},
        'limits':{'native_admitted_benchmark_runtime_START_used':False,'full_supervisor_entrypoint_used':False,
            'Terminal_Bench_harness_used':False,'provider_transmission_verified':False,'provider_usage_measured':False,
            'source_to_model_equivalence_proved':False,'training_convergence_proved':False,'full_task_satisfaction':False,
            'loaded_code_attested':False,'transitive_import_closure_attested':False,'producer_process_origin_authenticated':False,
            'reviewer_reinvoked_native_runtime_or_Lean':False,
            'interpretation':'Own exact packet/reference/Git-bundle/signature/input/token/ledger reconstruction verifies public data joins. Actual kernel observations, native checker replays and process outcomes remain attributed to pinned application evidence; public did:key signature verification establishes no identity-origin authority.'}}
    raw=json.dumps(result,sort_keys=True,indent=2).encode()+b'\n'
    if len(raw)>8*1048576:raise ValueError('review report exceeds8MiB bound')
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
    with os.fdopen(fd,'wb')as stream:stream.write(raw)
    for value in captures.values():os.close(value['fd'])
    print(json.dumps({'passed':result['passed'],'check_count':result['check_count'],'failed_checks':len(failures),
        'read_pins':len(result['read_pins']),'bytes':len(raw),'sha256':sha(raw),'first_failures':failures[:5]}))
    return 0 if result['passed']else 1


if __name__=='__main__':
    if len(sys.argv)>1:R=W/sys.argv[1]
    report=W/(sys.argv[2]if len(sys.argv)>2 else 'independent-review.json')
    require(report.parent==W and R.parent==W,'audit:owned-output-and-explicit-selected-run')
    read(Path(__file__).absolute())
    try:audit()
    except Exception as error:
        check(False,'audit:unhandled-error',{'type':type(error).__name__,'message':str(error),'traceback':traceback.format_exc()})
    raise SystemExit(finish(report))
