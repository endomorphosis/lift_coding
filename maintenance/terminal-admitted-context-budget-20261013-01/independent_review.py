"""Stage AA named-public-evidence audit, independent decoder and token recount.

No project/native imports, subprocesses, service calls, DB/CAS bodies or source
execution. Native process-origin outcomes remain attributed to the pinned actual
experiment. Public signed/serialized data never reconstitutes live owner authority.
This agent authored the broker and some test/deployment fixtures; this is a
separate implementation-free data audit, not independent authorship review.
"""
from __future__ import annotations
import ast,base64,hashlib,importlib.metadata,io,json,os,re,stat,sys,tarfile,traceback
from collections import Counter
from copy import deepcopy
from pathlib import Path
import xml.etree.ElementTree as ET
W=Path('/home/barberb/lift_coding/maintenance/terminal-admitted-context-budget-20261013-01')
PREVIOUS=Path('/home/barberb/lift_coding/maintenance/terminal-checked-worker-context-20261013-01')
C=W/'checkout'
TOKENIZER=Path('/home/barberb/lift_coding/maintenance/terminal-token-pairing-20261012-01/pinned-host-tokenizer')
checks,failures,captures,counts=[],[],{},{}
config={};exports={};metadata_only=[];declared_occurrences=[];toolchain_mounts=[];historical_aliases={}
R=A=F=None

def allowed(path):
    path=Path(path)
    return (path.is_absolute() and not set(path.parts)&{'cas','lake','.git'} and
        path.suffix not in {'.duckdb','.sqlite','.sqlite3','.db','.wal','.parquet'})


def read(path,expected=None,*,max_bytes=8_388_608):
    path=Path(path);key=str(path)
    require(allowed(path),'custody:explicit-public-path:'+key)
    if key not in captures:
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        before=os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink==1,'custody:regular-singlelink:'+key)
        require(0<=before.st_size<=max_bytes,'custody:bounded:'+key)
        raw=b''
        while len(raw)<=max_bytes:
            block=os.read(fd,min(1048576,max_bytes+1-len(raw)))
            if not block:break
            raw+=block
        require(len(raw)==before.st_size and stamp(before)==stamp(os.fstat(fd))==stamp(path.lstat()),
                'custody:nofollow-FD-stat-bytes:'+key)
        captures[key]={'fd':fd,'stamp':stamp(before),'raw':raw,
            'pin':{'path':key,'bytes':len(raw),'sha256':sha(raw)}}
    item=captures[key]
    if expected is not None:
        check(expected.get('bytes',expected.get('size_bytes'))==len(item['raw']),'pin:bytes:'+key)
        check(expected['sha256'].removeprefix('sha256:')==item['pin']['sha256'],'pin:SHA256:'+key)
    return item['raw']


def load(path,expected=None):
    return parse(read(path,expected))


def selected(name):
    value=config[name]
    require(type(value)is str and Path(value).is_absolute(),'config:absolute-explicit:'+name)
    path=Path(value)
    require(path.is_relative_to(W),'config:owned-stage-input:'+name)
    return path


def add_export(container_path,host_path,pin=None,*,kind='public-file'):
    require(type(container_path)is str and Path(container_path).is_absolute(), 'export:absolute-container-namespace')
    host_path=Path(host_path)
    require(host_path.is_absolute() and allowed(host_path) and
        (host_path.is_relative_to(Path('/home/barberb/lift_coding')) or
         host_path.is_relative_to(Path('/home/barberb/.elan/toolchains/leanprover--lean4---v4.34.1'))),
        'export:explicit-known-public-host-target')
    row={'path':str(host_path),'kind':kind}
    if pin is not None:row.update(bytes=pin.get('bytes',pin.get('size_bytes')),sha256=pin['sha256'].removeprefix('sha256:'))
    if container_path in exports:
        compare_tree({k:v for k,v in exports[container_path].items()if k!='kind'},
            {k:v for k,v in row.items()if k!='kind'},'export:one-unambiguous-map:'+container_path)
    else:exports[container_path]=row


def pin_declared(value,where='root',*,origin_path=None):
    """Preserve occurrences; container paths resolve only via explicit maps."""
    if type(value)is dict:
        if type(value.get('path'))is str and type(value.get('sha256'))is str and ('bytes'in value or 'size_bytes'in value):
            path=value['path'];descriptor={'where':where,'path':path,'bytes':value.get('bytes',value.get('size_bytes')),'sha256':value['sha256']}
            declared_occurrences.append(descriptor)
            alias_key=(path,descriptor['bytes'],descriptor['sha256'].removeprefix('sha256:'))
            if alias_key in historical_aliases:
                for alias in historical_aliases[alias_key]:read(alias['path'],value)
            elif origin_path is not None and str(Path(origin_path)) in config.get('historical_descriptor_files',[]):
                metadata_only.append({**descriptor,'reason':'historical-provenance-descriptor-not-current-authority'})
            elif path in exports:
                read(exports[path]['path'],value)
            elif any(Path(path).is_relative_to(Path(row['Destination'])) for row in toolchain_mounts):
                mount=next(row for row in toolchain_mounts if Path(path).is_relative_to(Path(row['Destination'])))
                relative=Path(path).relative_to(mount['Destination']);host=Path(mount['Source'])/relative
                require(not set(relative.parts)&{'..','cas','lake','.git'} and
                    (host.suffix in {'.olean','.ilean','.so'} or relative.as_posix()=='bin/lean'),
                    'toolchain:declared-readonly-mount-public-file-only:'+path)
                read(host,value)
            elif Path(path).is_relative_to(W) and Path(path).name=='public-source.tar.gz':
                require(path in config.get('metadata_only_bulk_archives',[]),
                    'descriptor:bulk-archive-requires-exact-declared-metadata-policy:'+path)
                metadata_only.append({**descriptor,'reason':'explicit-bulk-source-archive-metadata-not-opened'})
            elif Path(path).is_absolute() and Path(path).is_relative_to(Path('/home/barberb/lift_coding')) and allowed(path):
                # Historical public host inputs retain their own named custody.
                read(path,value)
            else:
                descriptor['reason']=('system-or-private-descriptor-not-public-body' if not allowed(path)
                    or Path(path).is_absolute() else 'nonabsolute-descriptor-no-path-authority')
                metadata_only.append(descriptor)
        for key,item in value.items():pin_declared(item,where+'/'+key,origin_path=origin_path)
    elif type(value)is list:
        for i,item in enumerate(value):pin_declared(item,where+'/'+str(i),origin_path=origin_path)


def ceiling(value,name):
    false_names={'proof_authority','execution_authority','mutation_authority','completion_authority',
        'publication_authority','omission_authority','production_activated','production_activation',
        'source_semantics_verified','runtime_behavior_verified','source_to_model_equivalence_proved',
        'source_equivalence_proved','cpython_equivalence_proved','convergence_proved',
        'training_convergence_proved','full_task_satisfaction','whole_program_semantics_verified',
        'source_parser_correctness_proved','python_import_resolution_proved','loaded_module_code_attested',
        'transitive_dependency_closure_attested','public_terminal_bench_task_satisfied',
        'training_executed','source_body_executed','semantic_equivalence_claimed','proof_transfer',
        'provider_savings_measured','native_governor_qualified','production_context_pack_qualified',
        'context_sufficiency_proved','provider_usage_measured','provider_output_measured',
        'serialized_live_authority','rendered_input_origin_verified','full_supervisor_entrypoint_used',
        'global_task_budget_enforced','durable_budget_resume_supported','provider_billing_savings_measured',
        'Terminal_Bench_harness_used'}
    if type(value)is dict:
        for key,item in value.items():
            if key in false_names:check(item is False,name+'/'+key+':false-ceiling')
            if key in {'provider_calls','training_steps'}:check(type(item)is int and item==0,name+'/'+key+':zero')
            ceiling(item,name+'/'+key)
    elif type(value)is list:
        for i,item in enumerate(value):ceiling(item,name+'/'+str(i))
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
    recovered={};current_objects={expected_head}
    def walk(oid,prefix='',depth=0):
        require(depth<=16 and len(current_objects)<=128,'git:bounded-current-source-object-closure')
        current_objects.add(oid)
        kind,body=objects[oid];require(kind=='tree','git:declared-tree-object:'+oid)
        cursor=0
        while cursor<len(body):
            space=body.index(b' ',cursor);end=body.index(b'\0',space)
            mode=body[cursor:space];name=body[space+1:end].decode();target=body[end+1:end+21].hex();cursor=end+21
            require(name not in {'','.','..'} and '/'not in name,'git:finite-relative-tree-entry')
            path=prefix+name
            if mode in {b'40000',b'040000'}:walk(target,path+'/',depth+1)
            else:
                require(mode==b'100644' and objects[target][0]=='blob','git:exact-nonexecutable-source-blob:'+path)
                recovered[path]=objects[target][1];current_objects.add(target)
    walk(expected_tree)
    require(set(recovered)==set(expected_sources),'git:exact-four-source-blobs-no-metadata')
    for name,content in expected_sources.items():require(recovered[name]==content,'git:exact-native/checked-source-byte-join:'+name)
    counts.update(independent_git_pack_objects=n,independent_git_source_blobs=len(recovered))
    return {'sources':recovered,'current_objects':{oid:objects[oid]for oid in current_objects}}

def audit_native_basis(summary):
    head=summary['head']
    native=load(R/'native-semantic-capsules.json');manifest=load(R/'observed-manifest.json')
    capsule=load(R/'checked-call-capsule.json');views=load(R/'code-views.json')
    intent=load(R/'intent-profile.json');query=load(R/'query.json')
    view=load(R/'audit-view.json');call=parse(view['checked_call_context'],floats=False)
    require(summary['qualified'] is True,'actual:selected-qualified-AA-run')
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
    public=F;owner=load(public/'owner-receipt.json')
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
    git_current=decode_git_bundle(read(public/'source.gitbundle'),owner['baseline_commit'],owner['git_tree'],sources)
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
            'semantic':semantic,'world':restored['world-context'],'git_current':git_current}

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
    require(read(R/'checked-context-public-artifact.json')==raw,
            'checked:independently-reconstructed-extension-equals-actual-protected-public-readback')
    require(read(R/'public-instruction-artifact.json')==native_fixture['instruction_bytes'],
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

def audit_exports():
    """Explicit namespaces only: no private body lookup, no container path guessing."""
    global R,A,F
    R=selected('actual_public');A=selected('model_public');F=selected('fixture_public')
    if 'historical_source_aliases'in config:
        alias_paths=config['historical_source_aliases']
        if type(alias_paths)is str:alias_paths=[alias_paths]
        require(type(alias_paths)is list and 1<=len(alias_paths)<=16 and len(set(alias_paths))==len(alias_paths),
            'history:explicit-bounded-source-alias-manifests')
        occurrences=0
        for name in alias_paths:
            alias_path=Path(name)
            require(alias_path.parent==W and re.fullmatch(r'source-before-[0-9]{2}\.json',alias_path.name),
                'history:exact-stage-historical-alias-manifest')
            aliases=load(alias_path)
            require(aliases['schema']=='terminal-admitted-context-historical-source-aliases@1' and len(aliases['files'])==9,
                'history:exact-nine-public-source-byte-alias-occurrences:'+alias_path.name)
            for row in aliases['files']:
                pin=row['archived_pin'];require(Path(row['historical_path'])==C/row['relative_path']
                    and Path(pin['path']).is_relative_to(W/alias_path.stem),'history:exact-original-to-archive-byte-map')
                read(pin['path'],pin);key=(row['historical_path'],pin['bytes'],pin['sha256'])
                historical_aliases.setdefault(key,[]).append(pin);occurrences+=1
        counts.update(historical_source_alias_manifest_count=len(alias_paths),historical_source_alias_occurrences=occurrences,
            historical_source_alias_versions=len(historical_aliases),historical_source_aliases_grant_current_authority=False)
    if 'public_inventory'in config:
        inventory=load(selected('public_inventory'))
        require(inventory['qualified']is True,'inventory:explicit-public-mapping-qualified')
        for mapping in inventory['container_host_mappings']:
            pin=mapping['host_pin'];read(pin['path'],pin)
            add_export(mapping['container_path'],pin['path'],pin,kind=mapping['group'])
        for pin in inventory['files']:read(pin['path'],pin)
    boundary=load(selected('boundary_result'))
    for mount in boundary['mounts']:
        require(mount['Type']=='bind' and mount['RW']is False,'export:only-reported-readonly-public-toolchain-mount')
        if mount['Destination']=='/opt/ipfs-supervisor/lean':
            require(mount['Source']=='/home/barberb/.elan/toolchains/leanprover--lean4---v4.34.1',
                'export:exact-existing-pinned-Lean-toolchain-mount')
            toolchain_mounts.append(mount)
    result=load(selected('actual_result'))
    require(result['qualified']is True,'actual:host-export-and-disposal-qualified')
    execution=result['owner_execution'];names=execution['public_files'];rows=result['public_exports']
    require(execution['qualified']is True and len(names)==len(set(names))==len(rows) and 1<=len(names)<=80,
            'actual:closed-bounded-explicit-export-census')
    require({Path(row['path']).name for row in rows}==set(names),'actual:exact-public-export-basenames')
    for row in rows:
        name=Path(row['path']).name
        require(Path(row['path'])==R/name and Path(name).name==name,'actual:export-target-in-selected-namespace:'+name)
        read(row['path'],row)
        add_export(execution['public_directory']+'/'+name,row['path'],row)
    model=load(selected('model_result'));export=model['public_export'];model_rows=model['public_files']
    require(model['qualified']is True and len(export['files'])==len(model_rows)==113,
            'model:113-explicit-public-exports-not-private-stores')
    by_relative={Path(row['path']).relative_to(A).as_posix():row for row in model_rows}
    require(len(by_relative)==113,'model:unique-public-export-targets')
    previous=load(PREVIOUS/'actual-public-inventory.json')
    pattern={Path(row['path']).relative_to(PREVIOUS/'actual-public-checked-01').as_posix()for row in previous['files']}
    require(set(by_relative)==pattern,'model:exact-predecessor-path-selection-not-previous-body-reuse')
    for row in export['files']:
        relative=Path(row['relative_path'])
        require(not relative.is_absolute() and not set(relative.parts)&{'..','cas','lake','.git'},'model:public-relative-only')
        target=A/relative;host_pin=by_relative[relative.as_posix()]
        raw=read(target,host_pin);require(len(raw)==row['bytes'] and sha(raw)==row['sha256'],'model:three-way-container-export-byte-join:'+str(relative))
        expected=('/app/'+relative.parts[-1] if relative.parts[0]=='repository' else export['private_model_state']+'/'+relative.as_posix())
        require(row['container_path']==expected,'model:exact-declared-container-path:'+str(relative))
        add_export(row['container_path'],target,row)
    archive=model.get('archive')
    if archive:
        raw=read(archive['path'],archive,max_bytes=33*1048576)
        with tarfile.open(fileobj=io.BytesIO(raw),mode='r:')as bundle:
            members=bundle.getmembers()
            require(len(members)==113 and {x.name for x in members}==pattern,'model:exact113-archive-members')
            for member in members:
                require(member.isfile() and not member.issym() and not member.islnk() and 0<=member.size<=8388608,
                        'model:regular-bounded-archive-member:'+member.name)
                require(bundle.extractfile(member).read(8388609)==read(A/member.name),'model:exact-archive-public-body:'+member.name)
    fixture_result=load(selected('fixture_result')) if 'fixture_result'in config else None
    fixture_names={'source.gitbundle','manifest.json','graph.json','admission.json','materialization.json',
        'context-preparation.json','task-readback.json','native-prompt.txt','native-capsule.json',
        'compilation-receipt.json','instruction-descriptor.json','context-bundle.json','owner-receipt.json'}
    require(len(fixture_names)==13,'fixture:closed-public-fixture-name-set')
    for name in sorted(fixture_names):read(F/name)
    if fixture_result is not None:
        require(fixture_result['qualified']is True,'fixture:actual-native-preparation-qualified')
        pin_declared(fixture_result,'fixture-result',origin_path=selected('fixture_result'))
    for row in config.get('explicit_exports',[]):
        require(set(row)>={'container_path','host_path','bytes','sha256'},'config:closed-explicit-export-map')
        read(row['host_path'],row);add_export(row['container_path'],row['host_path'],row)
    producers=load(R/'container-producer-pins.json')
    require(producers['root_protected_declared_sources']is True and producers['loaded_module_code_attested']is False
        and producers['transitive_dependency_closure_attested']is False,'source:deployed-file-custody-only')
    require(len(producers['files'])==9,'source:exact9-deployed-runtime-file-descriptors')
    for row in producers['files']:
        relative=Path(row['relative_path']);require(not relative.is_absolute() and '..'not in relative.parts and relative.suffix=='.py',
            'source:exact-relative-runtime-Python')
        require(row['uid']==0 and int(row['mode'],8)&0o022==0,'source:declared-root-protected-file:'+str(relative))
        target=C/relative;read(target,row);add_export(row['path'],target,row,kind='deployed-source-file')
    counts.update(actual_named_public_exports=len(rows),model_named_public_exports=113,
        fixture_named_public_inputs=13,explicit_container_host_map_entries=len(exports),
        loaded_module_code_attested=False,transitive_dependency_closure_attested=False)
    return result


def audit_native_run(result,basis,fixture):
    summary=load(R/'summary.json');require(summary['qualified']is True,'actual:original-native-owner-qualified')
    require(summary['native_admitted_benchmark_runtime_START_used']is True and
        summary['actual_native_worker_observer_invocations']==1 and summary['provider_calls']==0,
        'actual:one-genuine-native-START-observer-and-zero-provider-calls')
    launch=load(R/'native-launch-manifest.json');signature=load(R/'native-launch-signature.json')
    verify_public_signature({'payload':launch,'binding':signature},'native-launch-manifest')
    launch_id='sha256:'+sha(canonical(launch,ascii=True))
    require(launch['schema']=='isolated-admitted-supervisor-launch@1','launch:exact-native-launch-schema')
    compare_tree(launch['local_admission'],fixture['admission'],'launch:original-signed-local-admission')
    compare_tree(launch['task_context_bundle'],fixture['owner']['context_bundle'],'launch:complete-native-context-bundle')
    require(launch['baseline_commit']==fixture['owner']['baseline_commit'] and launch['baseline_tree_id']==fixture['owner']['git_tree'],
        'launch:original-signed-source-Git-baseline')
    require(launch['argv_digest']=='sha256:'+sha(canonical(launch['argv'],ascii=True)),'launch:complete-native-daemon-argv-digest')
    material=load(R/'owner-scope-material.json');compare_tree(launch['checked_observer_budget_scope'],material,'launch:signed-original-owner-scope-material')
    context_id=structured(material);require(context_id==summary['context_cid'],'scope:complete-material-CID-not-live-authority')
    compare_tree(material['budget_binding'],load(R/'budget-binding.json'),'scope:complete-budget-binding')
    compare_tree(material['budget_policy'],load(R/'budget-policy.json'),'scope:complete-budget-policy')
    require(material['task_cid']==fixture['owner']['task_cid'] and material['task_id']==fixture['owner']['task_id']
        and material['admission_cid']==structured(fixture['admission']),'scope:exact-original-native-task-and-admission')
    env_rows=launch['environment'];require(len(env_rows)==len({x[0]for x in env_rows}),'launch:unique-signed-environment')
    env=dict(env_rows);socket_key='IPFS_ACCELERATE_CHECKED_CONTEXT_DISPATCH_SOCKET';context_key='IPFS_ACCELERATE_CHECKED_CONTEXT_DISPATCH_CID';owner_key='IPFS_ACCELERATE_CHECKED_CONTEXT_OWNER_BIRTH'
    require(env[socket_key]==launch['state_root']+'/checked-context.sock' and env[context_key]==context_id
        and len(env[socket_key].encode())<108,'launch:exact-pre-signed-private-socket-and-context')
    owner=parse(env[owner_key]);require(set(owner)=={'pid','process_birth_id'} and type(owner['pid'])is int and owner['pid']>0
        and canonical(owner).decode()==env[owner_key] and re.fullmatch(r'birth:[0-9a-f]{32}',owner['process_birth_id']),
        'launch:exact-signed-public-original-owner-kernel-birth-hint')
    require(not any(x in env for x in ('IPFS_ACCELERATE_CHECKED_CONTEXT_WRAPPER_TICKET','OPENAI_API_KEY','ANTHROPIC_API_KEY')),
        'launch:no-wrapper-ticket-or-provider-secret-in-signed-environment')
    require(launch.get('finite_execution_scope')is None and launch.get('inventory_execution_scope')is None
        and launch['published_retrieval_policy']is None and launch['context_refresh_policy']is None,
        'launch:closed-single-observer-route-no-alternate-scope')
    start=load(R/'native-START.json');require(start['status']=='succeeded','native:actual-START-succeeded')
    compare_tree(load(R/'native-START-raw.json'),start,'native:original-native-START-record-equals-harness-projection')
    boots=load(R/'native-bootstrap-receipts.json');errors=load(R/'native-bootstrap-errors.json')
    require(len(boots)==1 and errors==[],'native:one-real-bootstrap-no-errors')
    boot=boots[0]
    compare_tree(load(R/'native-child-bootstrap-last-raw.json'),boot,'native:original-native-bootstrap-record-equals-exported-receipt')
    # Actual kernel/owner results are application evidence, not reconstructed
    # kernel observations from this source-import-free reviewer process.
    require(boot['configuration_root']==launch_id,'native:bootstrap-exact-signed-manifest-digest')
    for field,expected in [('client_id',launch['bootstrap_client_id']),('route_policy_id',launch['execution_route_policy_id']),
            ('store_id',launch['owner_identity']['store_id']),('server_id',launch['owner_identity']['server_id'])]:
        require(boot[field]==expected,'native:bootstrap-manifest-'+field)
    require(type(boot['pid'])is int and boot['pid']>0 and re.fullmatch(r'birth:[0-9a-f]{32}',boot['process_birth_id']),
        'native:bootstrap-recorded-exact-daemon-kernel-birth-domain')
    first=load(R/'native-first-pass.json');raw_first=parse(read(R/'native-first-pass-raw.json'))
    compare_tree(first,raw_first,'native:exact-first-pass-raw-and-exported-record')
    require(first.get('scope')==launch['native_dispatch_diagnostic_scope'],'native:first-pass-exact-signed-diagnostic-scope')
    require(first['claimed_task_cid']==fixture['owner']['task_cid'] and first['active_task_id']==fixture['owner']['task_id']
        and type(first['sequence'])is int and first['sequence']==1
        and type(first['write_count'])is int and first['write_count']==1,'native:first-pass-exact-one-current-task-and-attempt')
    require(first['portal_implementation']['returncode']==75,'native:first-pass-observer-exit75')
    diagnostic=launch['native_dispatch_diagnostic_scope']
    require(diagnostic['run_id']==launch['run_id'] and diagnostic['task_cid']==fixture['owner']['task_cid']
        and diagnostic['producer_source_sha256']==sha(read(C/'ipfs_accelerate_py/agent_supervisor/runtime/native_dispatch_diagnostics.py')),
        'native:diagnostic-exact-signed-run-task-and-producer')
    observation=load(R/'native-observation.json');require(observation['schema']=='supervisor-model-input-observation@2'
        and observation['status']=='observed','native:closed-successful-checked-model-input-observer')
    receipt_source=read(C/'ipfs_accelerate_py/agent_supervisor/runtime/model_input_observation_receipt.py').decode()
    fields=None
    for node in ast.parse(receipt_source).body:
        if isinstance(node,ast.Assign) and any(isinstance(x,ast.Name)and x.id=='OBSERVATION_FIELDS'for x in node.targets):
            fields=set(ast.literal_eval(node.value.args[0]))
    require(fields is not None and set(observation)==fields|{'checked_context'},'native:independent-closed-observer-field-census')
    require(observation['requested_model']=='authored-offline-observer' and observation['purpose']=='coding'
        and observation['requested_output_tokens']==128 and observation['timeout_seconds']==30
        and observation['provider_attempted']is False and observation['router_calls']==0 and observation['usage']is None
        and observation['native_rollout_usage']is None,'native:actual-observer-stopped-before-any-provider')
    logged=[]
    for line in read(R/'native-implementation.log').decode().splitlines():
        if line.strip().startswith(('{','[')):
            value=parse(line.strip());require(type(value)is dict,'native:log-JSON-object-only');logged.append(value)
    require(len(logged)==1,'native:one-observer-receipt-in-real-implementation-log')
    compare_tree(logged[0],observation,'native:logged-exact-observation')
    prepared=load(R/'native-dispatch-prepared-record.json');preparation=prepared['preparation']
    pregrant=prepared['pregrant'];identity(pregrant,'pregrant_cid','pregrant:entire-data-only-private-worktree-record')
    authority={'worker_birth_established','provider_usage_measured','proof_authority','execution_authority',
        'completion_authority','global_task_budget_enforced','serialized_live_authority','full_task_satisfaction',
        'training_convergence_proved'}
    require(set(pregrant)=={'schema','phase','workspace','owner_uid','files','worker_readability_verified',
        'strict_allocated_load_verified','permission_transition_is_data_only','pregrant_cid',*authority}
        and pregrant['schema']=='checked-observer-pregrant-worktree@1' and pregrant['phase']=='canonical_pregrant'
        and pregrant['worker_readability_verified']is False and pregrant['strict_allocated_load_verified']is False
        and pregrant['permission_transition_is_data_only']is True and all(pregrant[k]is False for k in authority),
        'pregrant:closed-explicit-phase-not-postgrant-readability-or-live-authority')
    require(pregrant['workspace']==preparation['basis']['worker_workspace'] and pregrant['owner_uid']==material['boundary']['owner_uid'],
        'pregrant:actual-private-allocated-worktree-and-original-owner-binding')
    expected_pregrant_sources={**basis['sources'],'build/task-instruction.txt':basis['call']['user_prompt'].encode()}
    require(len(pregrant['files'])==4 and {row['relative_path']for row in pregrant['files']}==set(expected_pregrant_sources),
        'pregrant:exact-three-sources-plus-separate-signed-literal')
    stat_fields={'st_dev','st_ino','st_mode','st_uid','st_gid','st_nlink','st_size','st_mtime_ns','st_ctime_ns'}
    for row in pregrant['files']:
        raw=expected_pregrant_sources[row['relative_path']];original=row['original_stat']
        require(set(row)=={'relative_path','sha256','bytes','kind','original_stat'} and set(original)==stat_fields
            and all(type(original[k])is int for k in stat_fields) and original['st_uid']==pregrant['owner_uid']
            and original['st_nlink']==1 and stat.S_ISREG(original['st_mode']) and not original['st_mode']&0o022
            and original['st_size']==row['bytes']==len(raw) and row['sha256']==sha(raw),
            'pregrant:original-bounded-file-stat-and-canonical-byte-join:'+row['relative_path'])
        require(row['kind']==('signed_instruction'if row['relative_path']=='build/task-instruction.txt'else'source'),
            'pregrant:separate-literal-and-source-domain:'+row['relative_path'])
    counts.update(pregrant_original_file_witnesses=4,pregrant_serialized_authority=False,
        postgrant_strict_loader_unchanged=True)
    for key,name in [('preparation','native-budget-preparation.json'),('preflight','native-checked-inclusion.json'),
            ('descriptor','native-checked-descriptor.json'),('verification','native-semantic-verification.json')]:
        compare_tree(prepared[key],load(R/name),'scope:complete-prepared-record-projection:'+key)
    identity(preparation,'preparation_cid','budget:exact-original-preparation')
    compare_tree(observation['checked_context'],prepared['preflight'],'native:actual-observation-complete-checked-inclusion')
    basis_data=preparation['basis'];actual_native=read(R/'native-emitted-prompt.txt').decode()
    require(actual_native==basis_data['native_prompt'],'native:actual-emitted-stdin-not-manual-fixture-substitution')
    counts['actual_native_prompt_equals_manual_fixture_preview']=actual_native==fixture['native_prompt']
    packet=read(R/'view-packet.json').decode();require(material['context_sha256']==sha(packet.encode())
        and material['context_bytes']==len(packet.encode()),'scope:entire-context-packet-bound-to-signed-material')
    extension_fixture={**fixture,'native_prompt':actual_native}
    normalized={'checked_inclusion':prepared['preflight'],'descriptor':prepared['descriptor'],
        'semantic_verification':prepared['verification'],'checked_suffix':basis_data['checked_suffix']}
    checked,suffix=own_checked_extension(normalized,packet,material['budget_binding'],material['budget_policy'],extension_fixture)
    require(basis_data['router_prompt']==actual_native+instruction_block(basis['call']['user_prompt']),
        'native:entire-literal-signed-instruction-appended-after-actual-stdin')
    expected_content=basis_data['router_prompt']+suffix
    expected_full=coding_advisory(basis_data['worker_workspace'])+expected_content
    require(expected_full.encode()==read(R/'native-complete-input.txt') and expected_full==preparation['event']['rendered_input']['text'],
        'native:own-full-renderer-recomposition-including-guidance-and-metadata')
    encoding=tokenize_packets({}, {'measures':{}})
    own_full=own_measure(expected_full,encoding,'whole-actual-coding-input');own_new=own_measure(expected_content,encoding,'whole-router-content')
    compare_tree(preparation['event']['rendered_input'],own_full,'tokens:actual-complete-coding-input-independent-recount')
    compare_tree(preparation['event']['new_content'],own_new,'tokens:actual-complete-router-content-independent-recount')
    for label,text in [('native_prompt',actual_native),('router_prompt',expected_content),
            ('model_prompt',expected_full),('workspace_advisory',coding_advisory(basis_data['worker_workspace']))]:
        require(observation[label+'_sha256']==sha(text.encode()) and observation[label+'_bytes']==len(text.encode()),
            'native:actual-observer-exact-entire-input-identity:'+label)
        compare_tree(preparation['materialization'][label],{'sha256':sha(text.encode()),'bytes':len(text.encode())},
            'native:entire-prepared-materialization-identity:'+label)
    require(observation['workspace']==basis_data['worker_workspace'],'native:exact-random-allocated-worktree')
    compare_tree(observation['semantic_context_verification'],prepared['verification'],'native:semantic-source-verification-exact')
    compare_tree(observation['public_instruction'],basis_data['instruction_receipt'],'native:literal-public-instruction-exact-inclusion')
    compare_tree(observation['external_container_boundary'],material['boundary'],'native:actual-observer-current-UID-namespace-boundary')
    commit=load(R/'native-budget-commit.json');identity(commit,'commit_cid','budget:entire-owner-commit')
    require(commit['context_cid']==context_id and commit['event_cid']==preparation['event']['event_cid']
        and commit['local_reservation_committed']is True,'budget:original-context-event-exact-commit')
    require(commit['observation_json']==canonical(observation).decode() and commit['observation_sha256']==sha(canonical(observation))
        and commit['observation_bytes']==len(canonical(observation)),'budget:entire-observation-bytes-exactly-committed')
    snapshots=[('initial',load(R/'initial-budget-state.json')),('commit',commit['budget_snapshot']),
        ('after-native-cleanup',load(R/'budget-state-after-native-cleanup.json')),('final',load(R/'final-budget-state.json'))]
    for label,snapshot in snapshots:
        replay_coding_ledger(snapshot,encoding,basis_data['worker_workspace'],label)
        compare_tree(snapshot['binding'],material['budget_binding'],'budget:original-material-binding-in-every-prefix:'+label)
        compare_tree(snapshot['policy'],material['budget_policy'],'budget:original-material-policy-in-every-prefix:'+label)
        compare_tree(snapshot['tokenizer'],{'library':'tiktoken','version':'0.13.0','encoding':'o200k_base',
            'bpe_sha256':'446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d',
            'vocabulary_sha256':'a6557bbd3ceb299981ac87fd86a51fa8f0e9505be18ed608c5ada94bdfd0f63f',
            'offline':True,'fallback':False},'budget:exact-offline-pinned-tokenizer-profile:'+label)
    require(preparation['owner_snapshot_cid']==snapshots[0][1]['snapshot_cid'],'budget:preparation-from-exact-original-empty-owner')
    require(snapshots[0][1]['records']==[] and snapshots[0][1]['closed']is False,'budget:original-empty-open-start')
    compare_tree(snapshots[1][1]['records'],[{'event':preparation['event'],'status':'committed'}],'budget:exact-one-original-committed-reservation')
    for label,snapshot in snapshots[2:]:
        compare_tree(snapshot['records'],snapshots[1][1]['records'],'budget:no-event-refund-after-cleanup:'+label)
        compare_tree(snapshot['totals'],snapshots[1][1]['totals'],'budget:no-cost-refund-after-cleanup:'+label)
    require(snapshots[-1][1]['closed']is True,'budget:original-live-owner-closed-before-final-export')
    before=load(R/'broker-observations-before-STOP.json');after=load(R/'broker-observations-after-STOP.json')
    compare_tree(before,after,'native:birth-records-retained-through-STOP')
    require(len(before)==2 and [x['boundary']for x in before]==['native_daemon_to_owner_wrapper','isolated_worker']
        and all(x['status']=='spawned'for x in before),'native:two-genuine-recorded-birth-boundaries-no-refusal')
    wrapper,worker=before
    require(wrapper['wrapper_birth_observed']is True and worker['worker_birth_observed']is True
        and worker['isolated_uid_observed']is True and worker['worker_uid']==1001 and worker['wrapper_pid']==wrapper['pid'],
        'native:recorded-wrapper-to-isolated-worker-PID-and-UID-join')
    require(worker['worker_pid']>0 and worker['sudo_pid']>0 and re.fullmatch('birth:[0-9a-f]{32}',worker['worker_process_birth_id']),
        'native:recorded-worker-kernel-birth-domain')
    chain=worker['parent_chain'];require(1<=len(chain)<=8 and chain[0]['pid']==worker['worker_pid']
        and chain[0]['process_birth_id']==worker['worker_process_birth_id'] and chain[-1]['pid']==worker['sudo_pid']
        and len({row['pid']for row in chain})==len(chain),'native:recorded-bounded-isolated-worker-to-sudo-parent-chain')
    for left,right in zip(chain,chain[1:]):require(left['parent_pid']==right['pid'],'native:recorded-exact-adjacent-parent-join')
    require(chain[-1]['parent_pid']==wrapper['pid'],'native:recorded-sudo-parent-is-original-wrapper')
    worktree_observation=worker['worker_worktree_observation']
    worktree_fields={'schema','pid','uid','parent_pid','start_time_ticks','process_birth_id','boot_id','worktree',
        'command_sha256','namespaces','metadata_only','execution_authority','proof_authority','completion_authority',
        'source_body_executed','provider_calls'}
    require(type(worktree_observation)is dict and set(worktree_observation)==worktree_fields
        and worktree_observation['schema']=='checked-worker-kernel-worktree-observation@1'
        and worktree_observation['metadata_only']is True
        and all(worktree_observation[key]is False for key in
            ('execution_authority','proof_authority','completion_authority','source_body_executed'))
        and type(worktree_observation['provider_calls'])is int and worktree_observation['provider_calls']==0,
        'native:closed-metadata-only-same-worker-UID-cwd-observation-no-provider-or-source-execution')
    for key in ('pid','uid','parent_pid','start_time_ticks'):
        require(type(worktree_observation[key])is int and worktree_observation[key]==chain[0][key],
            'native:worktree-helper-metadata-joins-exact-captured-worker:'+key)
    require(worktree_observation['uid']==1001
        and worktree_observation['process_birth_id']==worker['worker_process_birth_id']
        and worktree_observation['worktree']==basis_data['worker_workspace']
        and worktree_observation['namespaces']==material['boundary']['namespaces']
        and re.fullmatch('[0-9a-f]{64}',worktree_observation['command_sha256'])is not None,
        'native:metadata-cwd-command-digest-joins-original-allocation-boundary-and-recorded-birth')
    birth_raw=(':'.join(str(worktree_observation[key])for key in
        ('pid','start_time_ticks','boot_id','parent_pid'))).encode()
    require('birth:'+sha(birth_raw)[:32]==worktree_observation['process_birth_id'],
        'native:independent-kernel-birth-domain-from-public-cwd-observation-scalars')
    counts.update(worker_worktree_public_metadata_joined=True,
        worker_worktree_metadata_is_serialized_live_authority=False,
        worker_kernel_argv_plaintext_publicly_exported=False,
        metadata_helper_process_is_coding_observer=False)
    git_grant=worker['worker_git_metadata_grant']
    grant_fields={'schema','worktree','canonical_repository','registration','selected_branch','selected_commit',
        'current_tree','scope','parent_history_traversed','packed_objects_supported','metadata_directories',
        'object_directories','current_objects','current_object_bytes','files','directories',
        'execution_authority','proof_authority','completion_authority','source_body_executed','provider_calls'}
    require(type(git_grant)is dict and set(git_grant)==grant_fields
        and git_grant['schema']=='checked-worker-git-metadata-read-grant@1'
        and git_grant['scope']=='exact_native_worktree_registration_current_commit_tree_blob_closure'
        and all(git_grant[key]is False for key in ('execution_authority','proof_authority','completion_authority',
            'source_body_executed','parent_history_traversed','packed_objects_supported'))
        and type(git_grant['provider_calls'])is int and git_grant['provider_calls']==0,
        'native:closed-current-only-readonly-Git-grant-data-confers-no-execution-proof-or-history-authority')
    repository=git_grant['canonical_repository'];git=Path(repository)/'.git';registration=Path(git_grant['registration'])
    require(repository==launch['repository_root'] and git_grant['worktree']==basis_data['worker_workspace']
        and registration.parent==git/'worktrees' and re.fullmatch('[A-Za-z0-9_.-]{1,128}',registration.name),
        'native:Git-grant-exact-canonical-repository-allocated-worktree-registration-domain')
    branches=re.findall(r'^Branch: (implementation/[^\n]+)$',read(R/'native-implementation.log').decode(),re.MULTILINE)
    require(branches==[git_grant['selected_branch']]
        and git_grant['selected_commit']==fixture['owner']['baseline_commit']
        and git_grant['current_tree']==fixture['owner']['git_tree'],
        'native:Git-read-grant-joins-logged-native-branch-and-signed-current-commit-tree')
    current_objects=fixture['git_current']['current_objects']
    object_paths={str(git/'objects'/oid[:2]/oid[2:]):oid for oid in current_objects}
    metadata_paths={str(Path(basis_data['worker_workspace'])/'.git'),str(git/'HEAD'),
        *(str(registration/name)for name in ('HEAD','gitdir','commondir','index','ORIG_HEAD','config.worktree','logs/HEAD')),
        str(git/'refs/heads'/git_grant['selected_branch'])}
    metadata_count=0;object_files=[]
    for i,pin in enumerate(git_grant['files']):
        require(set(pin)=={'path','bytes','sha256','kind','original_mode','granted_mode','permissions_changed'}
            and type(pin['bytes'])is int and pin['bytes']>0 and re.fullmatch('[0-9a-f]{64}',pin['sha256']),
            'native:closed-Git-read-file-metadata-descriptor:'+str(i))
        original,granted=pin['original_mode'],pin['granted_mode']
        require(type(original)is int and type(granted)is int and granted==original|0o040
            and not granted&0o022 and granted&0o700==original&0o700
            and pin['permissions_changed']is (original!=granted),
            'native:Git-group-read-only-mode-bridge-preserves-owner-rights:'+str(i))
        if pin['kind']=='objects':
            require(pin['path']in object_paths and original in {0o400,0o440,0o444,0o644}
                and pin['bytes']<=8*1024*1024,'native:exact-current-loose-object-path-and-bounds:'+str(i))
            object_files.append(pin['path'])
        else:
            metadata_count+=1
            canonical_leaf=Path(pin['path']).parent==git/'refs/heads' and Path(pin['path']).name not in {'.','..'}
            require(pin['kind']=='metadata' and (pin['path']in metadata_paths or canonical_leaf)
                and original in {0o600,0o640,0o440,0o444,0o644} and pin['bytes']<=2*1024*1024,
                'native:bounded-registration-or-exact-baseline-reference-read-metadata:'+str(i))
    require(len(set(object_files))==len(object_files) and set(object_files)==set(object_paths)
        and metadata_count<=16 and len(current_objects)==git_grant['current_objects']<=128,
        'native:all-and-only-public-bundle-current-object-closure-excluding-parent-history')
    decoded_bytes=sum(len(kind.encode())+1+len(str(len(body)).encode())+1+len(body)
        for kind,body in current_objects.values())
    require(decoded_bytes==git_grant['current_object_bytes']<=64*1024*1024,
        'native:independent-current-decoded-object-byte-closure-total')
    allowed_dirs={git,git/'worktrees',registration,registration/'logs',git/'refs',git/'refs/heads'}
    ref_parent=git/'refs/heads'
    for name in Path(git_grant['selected_branch']).parts[:-1]:ref_parent/=name;allowed_dirs.add(ref_parent)
    object_dirs={git/'objects',*(git/'objects'/oid[:2]for oid in current_objects)}
    for i,row in enumerate(git_grant['directories']):
        path=Path(row['path']);original,granted=row['original_mode'],row['granted_mode']
        require(set(row)=={'path','original_mode','granted_mode','permissions_changed'}
            and path in allowed_dirs|object_dirs and original in {0o700,0o750,0o755}
            and granted==(0o750 if original==0o700 else original) and not granted&0o022
            and row['permissions_changed']is (original!=granted),'native:exact-Git-parent-read-traverse-mode-bridge:'+str(i))
    require(git_grant['metadata_directories']<=8 and git_grant['object_directories']<=129
        and len(git_grant['directories'])==git_grant['metadata_directories']+git_grant['object_directories'],
        'native:separate-bounded-registration-and-current-object-parent-directories-no-private-recursion')
    counts.update(current_Git_read_grant_objects=len(current_objects),current_Git_read_grant_metadata_files=metadata_count,
        current_Git_compressed_body_hashes_independently_rehashed=False,Git_group_write_granted=False,
        Git_parent_history_granted=False,Git_permissions_reversed_after_STOP=False)
    cleanup=load(R/'native-cleanup.json');outer=load(R/'outer-owner-cleanup.json')
    require(cleanup['STOP_called']is True and cleanup['closed']is True and cleanup['errors']==[]
        and cleanup['remaining_owner_processes']==0 and cleanup['final_worker_cleanup_returncode']==0,
        'native:STOP-and-close-success-zero-owner-members')
    stop=cleanup['stop'];require(stop['status']=='succeeded' and stop['data']['old_tree_fenced']is True
        and stop['data']['isolated_worker_cleanup']['returncode']==0,'native:actual-STOP-fence-and-isolated-cleanup')
    compare_tree(load(R/'native-STOP.json'),stop,'native:complete-native-STOP-and-cleanup-projection')
    compare_tree(load(R/'native-STOP-raw.json'),stop,'native:original-native-STOP-record-equals-harness-projection')
    require(outer['scope_closed']is True and outer['original_budget_closed']is True and outer['errors']==[],
        'native:outer-original-scope-and-budget-cleanup-success')
    broker_close=load(R/'checked-context-dispatch-broker-close-receipt.json')
    scope_close=load(R/'checked-observer-budget-close-receipt.json')
    require(broker_close['broker_closed']is True and broker_close['socket_removed']is True
        and broker_close['thread_joined']is True and broker_close['isolated_cleanup_checked']is True
        and broker_close['worker_birth_observed']is True and broker_close['ambiguous_birth_possible']is False,
        'native:exported-native-broker-socket-thread-and-isolated-cleanup-close-receipt')
    require(broker_close['git_metadata_custody_closed']is True and broker_close['git_metadata_permission_reversal']is False,
        'native:original-Git-custody-disposed-after-fenced-STOP-no-permission-reversal-claim')
    compare_tree(broker_close['observations'],before,'native:close-receipt-retains-exact-previous-birth-observations')
    compare_tree(load(R/'broker-observations-after-close.json'),before,'native:exact-birth-observations-retained-after-close')
    require(scope_close['context_cid']==context_id and scope_close['unlaunched']is False
        and scope_close['retained_guards_closed']is True and scope_close['publication_check_claimed']is False,
        'native:exported-original-retained-scope-close-receipt-after-STOP')
    ceiling(broker_close,'native-broker-close');ceiling(scope_close,'native-owner-scope-close')
    require(result['container_disposal']['container_absent']is True and result['container_disposal']['only_exact_owned_container_removed']is True,
        'native:owned-container-disposed-after-native-fenced-STOP')
    controls=load(R/'controls.json');require(len(controls)==1,'control:one-exact-cumulative-budget-test')
    control=controls[0]
    if own_full['tokens']>50000:
        require(control.get('rejected')is True and control['native_START_calls']==0 and control['worker_callbacks']==0
            and control['scope_dispatch_retry_attempted']is False,'control:overbudget-pure-retry-refused-before-native-dispatch')
        require(2*own_full['tokens']>material['budget_policy']['max_rendered_input_tokens'],'control:independent-retry-exceeds-cumulative-policy')
    else:require(control.get('exercised')is False,'control:no-unexercised-budget-refusal-claim')
    current=load(R/'current-source-after.json');require(current['source_unchanged']is True and current['task_completed']is False
        and current['git_commit']==fixture['owner']['baseline_commit'] and current['git_tree']==fixture['owner']['git_tree'],
        'source:original-Git-and-three-source-bytes-unchanged-after-START')
    compare_tree(current['head'],basis['head'],'source:exact-original-model-head-after-START')
    capacity_binding=load(R/'pre-capacity-binding.json')
    compare_tree(capacity_binding['head'],basis['head'],'capacity:whole-original-head-retained')
    require(capacity_binding['capsule_id']==basis['capsule']['capsule_id'],'capacity:whole-checked-proof-capsule-retained')
    policy_rows=load(R/'policy-observations.json')
    require(len(policy_rows)>=2 and all(canonical(row)==canonical(policy_rows[0])for row in policy_rows),
        'policy:complete-repeated-current-authority-roots-stable')
    require(policy_rows[0]['repository_root_cid']==basis['head']['snapshot_cid']
        and policy_rows[0]['program_root']==basis['manifest']['semantic_state']['state_cid'],
        'policy:current-source-snapshot-and-native-semantic-state-join')
    resources=summary['resources_after']
    require(resources['active_lease_count']==resources['waiting_request_count']==0,'capacity:all-current-capacity-released-after-native-cleanup')
    task_after=load(R/'native-task-after.json');require(task_after['status']not in {'done','completed','skipped'},'task:observer-did-not-complete-original-task')
    for value,name in [(summary,'actual-summary'),(observation,'native-observation'),(commit,'original-owner-commit'),(material,'signed-scope-material')]:ceiling(value,name)
    # Counterfactual expanded input preserves the entire native/proof/source
    # material. It is an offline comparison, never an admitted worker input.
    expanded_packet=parse(packet,floats=False)
    expanded_packet['representation']='expanded';expanded_packet['payload']={
        'native_semantic_audit':basis['native'],'code_view_audit':basis['views'],
        'checked_call_context':basis['view']['checked_call_context']}
    expanded_text=canonical(expanded_packet).decode()
    expanded_full=coding_advisory(basis_data['worker_workspace'])+basis_data['router_prompt']+CHECKED_PREFIX+expanded_text+CHECKED_SUFFIX
    expanded_measure=own_measure(expanded_full,encoding,'unadmitted-expanded-complete-input')
    counts.update(counterfactual_expanded_complete_coding_input={k:expanded_measure[k]for k in ('bytes','sha256','tokens')},
        conditional_local_view_input_token_delta=expanded_measure['tokens']-own_full['tokens'],
        counterfactual_expanded_artifact_admitted=False,counterfactual_expanded_worker_dispatched=False,
        provider_or_whole_task_billing_savings_measured=False)
    counts.update(native_admitted_benchmark_runtime_START_used=True,actual_native_worker_observer_invocations=1,
        original_scope_serialized_authority_reconstituted=False,independent_original_object_identity_proved=False,
        complete_native_coding_input_tokens=own_full['tokens'],complete_native_coding_input_bytes=own_full['bytes'],
        complete_router_content_tokens=own_new['tokens'],actual_provider_calls=0,
        public_broker_claim_fence_receipt_self_contained=False,public_receipt_emitter_kernel_birth_directly_joined=False,
        public_broker_socket_thread_close_receipts_exported=True,
        origin_scope='Pinned native START/broker source and actual harness kernel outcomes, with compatible public joins. Public snapshots alone do not establish original owner objects or receipt-emitting worker provenance.')
    return encoding,preparation
def audit_view(basis):
    view,native=basis['view'],basis['native'];packet=read(R/'view-packet.json');value=parse(packet,floats=False)
    require(canonical(value)==packet and value['representation']=='view','view:entire-exact-canonical-model-packet')
    compare_tree(value['payload'],{'model_view':view},'view:complete-packet-no-implicit-fields')
    compare_tree(value['head'],basis['head'],'view:entire-exact-original-head')
    identity(view,'view_id','view:entire-model-view')
    retained={k:v for k,v in native.items()if k not in {'schema','capsule_set_id','repository_state','blocks','artifact_facts'}}
    compare_tree(view['native_view']['retained_fields'],retained,'view:every-native-fact-link-binding-caveat-direct')
    compare_tree(view['code_views'],basis['views'],'view:every-original-code-display-and-bound-source')
    require(len(view['original_sources'])==3 and {r['path']for r in view['original_sources']}==set(basis['sources']),
        'view:exact-three-original-source-files-direct')
    for row in view['original_sources']:
        require(row['text'].encode()==basis['sources'][row['path']] and row['raw_source_required']is True,
            'view:all-original195bytes-direct:'+row['path'])
    independent_registry(native,view)
    compare_tree(parse(view['checked_call_context'],floats=False)['context']['capsule'],basis['capsule'],
        'view:all-checked-proof-assumptions-domain-residual-and-closure-direct')
    binding=load(R/'budget-binding.json')
    compare_tree(binding,{'schema':'terminal-semantic-context-budget-binding@1','head':basis['head'],
        'view_id':view['view_id'],'reference_basis_cid':view['expansion_directory']['reference_basis_cid'],
        'native_root_cid':view['native_root_cid'],'capsule_set_id':view['capsule_set_id'],'state_cid':view['state_cid']},
        'view:complete-original-budget-head-root-proof-basis-binding')
    ceiling(value,'view-packet')


def audit_proof(basis):
    model=load(A/'model/result.json');prepared=load(A/'prepared.json');qualification=load(A/'qualification-summary.json')
    identity(model,'result_cid','proof:entire-original-conditional-model-result')
    compare_tree(prepared['head'],basis['head'],'proof:fresh-co-located-original-codebase-head')
    require(model['model_status']=='model_proved' and qualification['model_status']=='model_proved'
        and qualification['rows']==49 and len(qualification['families'])==20,'proof:49-metadata-rows20-families-conditional-model')
    require(qualification['fresh_native_Lean_processes']==3 and qualification['START_called']is False,
        'proof:three-fresh-proof-processes-before-native-START')
    processes=load(A/'model/callee/native-lowering/lean_process.json');caller=load(A/'model/process.json')
    require(len(processes)==2,'proof:callee-version-and-compile-process-receipts')
    for name,item in [*processes.items(),('caller',caller)]:
        require(item['returncode']==0 and item['termination_reason']=='completed' and 'lean'==Path(item['command'][0]).name,
            'proof:three-recorded-successful-Lean-processes:'+name)
        # Command/tool bindings are data; genuine invocation is attributed to
        # pinned original model runner and its public process logs, never rerun.
        pin_declared(item,'Lean-process:'+name)
    for name,value in [('model',model),('prepared',prepared),('proof-capsule',basis['capsule']),('query',basis['query'])]:
        pin_declared(value,name);ceiling(value,name)
    cold=load(R/'native-cold-model-validation.json')
    require(cold['data_validated']is True and cold['model_status']=='model_proved'
        and cold['native_callee_cold_validation_passed']is True and cold['native_callee_integration_readback_passed']is True
        and cold['checker_reinvoked']is False,'proof:original-owner-revalidated-current-cold-model-before-START')
    compare_tree(cold['head'],basis['head'],'proof:cold-revalidation-exact-original-head')
    counts.update(conditional_metadata_rows=49,conditional_metadata_families=20,
        application_Lean_process_receipts=3,application_Lean_compilation_processes=2,
        application_Lean_version_probe_processes=1,reviewer_prover_invocations=0,source_behavior_execution=False,
        source_to_model_equivalence_proved=False,training_convergence_proved=False)


def audit_preservation():
    previous=load(PREVIOUS/'evidence-manifest.json');baseline=load(W/'preservation-baseline.json')
    rows=baseline['sealed_previous_files']
    require(len(rows)==baseline['verified_file_occurrences']==650,'preservation:exact650-previous-sealed-occurrences')
    require(len(previous['files'])+1==650,'preservation:previous-explicit-files-plus-seal-census')
    expected={x['path']:{k:x[k]for k in ('path','bytes','sha256')}for x in previous['files']}
    expected[str(PREVIOUS/'evidence-manifest.json')]=captures[str(PREVIOUS/'evidence-manifest.json')]['pin']
    compare_tree({r['path']:{k:r[k]for k in ('path','bytes','sha256')}for r in rows},expected,
        'preservation:exactprevious649-named-files-plus-seal')
    for i,row in enumerate(rows):read(row['path'],row);counts['prior_sealed_occurrences_verified']=i+1
    dependencies=load(PREVIOUS/'preservation-final.json');occurrences=dependencies['occurrences']
    require(len(occurrences)==dependencies['checked_occurrences']==356 and dependencies['occurrences_deduplicated']is False,
        'preservation:356-additional-dependency-occurrences-retained-without-deduplication')
    for i,row in enumerate(occurrences):
        require(row['unchanged']is True,'preservation:original-occurrence-unchanged:'+str(i))
        compare_tree(row['expected'],row['actual'],'preservation:exact-original-occurrence:'+str(i))
        read(row['expected']['path'],row['expected'])
    snapshot=load(W/'source-snapshot.json');files=snapshot['files']
    require(snapshot['source_only_projection']is True and snapshot['model_assets_or_runtime_data_copied']is False
        and snapshot['original_sources_edited']is False and snapshot['original_index_written']is False,
        'snapshot:source-only-copy-no-runtime-private-bodies-or-original-edits')
    require(snapshot['file_count']==len(files)==14535 and snapshot['total_bytes']==sum(x['bytes']for x in files)==433560896,
        'snapshot:inventory-census-and-total-bytes-not-full-body-recheck')
    require(len({r['relative_path']for r in files})==len(files),'snapshot:unique-declared-relative-paths')
    require(all(type(r['bytes'])is int and r['bytes']>=0 and re.fullmatch('[0-9a-f]{64}',r['sha256'])
        and not Path(r['relative_path']).is_absolute() and '..'not in Path(r['relative_path']).parts for r in files),
        'snapshot:typed-relative-public-source-inventory')
    counts.update(prior_sealed_occurrences_verified=650,prior_dependency_occurrences_verified=356,
        preservation_occurrences_deduplicated=False,source_snapshot_inventory_entries=14535,
        source_snapshot_inventory_bytes=433560896,source_snapshot_all_bodies_rehashed=False)


def audit_source_and_tests():
    freeze_path=selected('runtime_freeze');raw=read(freeze_path);freeze=parse(raw)
    require(sha(raw)==config['runtime_freeze_sha256'],'source:explicit-selected-runtime-freeze-SHA')
    require(freeze['schema']=='terminal-admitted-context-runtime-freeze@1' and len(freeze['files'])==6,
        'source:exact6-runtime-producers')
    for row in freeze['files']:
        require(set(row)=={'path','relative_path','bytes','sha256'} and Path(row['path'])==C/row['relative_path'],
            'source:closed-exact-runtime-pin:'+row['relative_path'])
        ast.parse(read(row['path'],row),filename=row['path'])
    for row in freeze['scripts']:
        require(Path(row['path']).parent==W and Path(row['path']).suffix=='.py','source:explicit-owned-harness')
        ast.parse(read(row['path'],row),filename=row['path'])
    counts.update(frozen_runtime_producers=6,frozen_harness_scripts=len(freeze['scripts']))
    # Structural boundary assertions: no source execution/import is performed.
    base=C/'ipfs_accelerate_py/agent_supervisor';broker=read(base/'runtime/checked_context_dispatch.py').decode()
    tree=ast.parse(broker)
    local_roots={'benchmarks','ipfs_accelerate_py','ipfs_datasets_py','duckdb','quack','harbor'}
    top_imports=[]
    for node in tree.body:
        if isinstance(node,ast.Import):top_imports.extend(alias.name.split('.')[0]for alias in node.names)
        if isinstance(node,ast.ImportFrom):top_imports.append((node.module or '').split('.')[0])
    require(not(set(top_imports)&local_roots),'source:worker-client-module-has-no-heavy-project-imports')
    verify_calls=[node for node in ast.walk(tree)if isinstance(node,ast.Call)
        and isinstance(node.func,ast.Attribute)and node.func.attr=='_verify']
    require(len(verify_calls)==2 and all(len(node.keywords)==1 and node.keywords[0].arg=='_owner_local_tasks'
        and isinstance(node.keywords[0].value,ast.Constant)and node.keywords[0].value.value is True for node in verify_calls),
        'source:complete-native-owner-local-verifiers-never-use-reentrant-RPC')
    klass=next(n for n in tree.body if isinstance(n,ast.ClassDef)and n.name=='OwnerCheckedContextDispatchBroker')
    broker_methods={node.name:node for node in klass.body if isinstance(node,ast.FunctionDef)}
    checkpoint=broker_methods['_identity_checkpoint'];current=broker_methods['_identity_current']
    checkpoint_calls=[node for node in ast.walk(checkpoint)if isinstance(node,ast.Call)]
    require(not any(isinstance(node.func,ast.Attribute)and node.func.attr in {'_verify','require_current'}
        for node in checkpoint_calls),'source:read-batch-identity-checkpoint-confers-no-full-current-authority')
    current_calls=[node for node in ast.walk(current)if isinstance(node,ast.Call)and isinstance(node.func,ast.Attribute)]
    require([node.func.attr for node in sorted(current_calls,key=lambda node:node.lineno)]==['_identity_checkpoint','_verify'],
        'source:full-current-retains-original-identity-before-complete-native-verification')
    worktree=broker_methods['_worktree_current']
    checkpoints=[node for node in ast.walk(worktree)if isinstance(node,ast.Assign)
        and any(isinstance(target,ast.Name)and target.id=='checkpoint'for target in node.targets)]
    require(len(checkpoints)==1 and isinstance(checkpoints[0].value,ast.Attribute)
        and checkpoints[0].value.attr=='_identity_checkpoint','source:bounded-worktree-file-reads-use-only-interim-identity')
    closing=broker_methods['_closing_authority']
    closing_calls=[node for node in ast.walk(closing)if isinstance(node,ast.Call)and isinstance(node.func,ast.Attribute)]
    authority_names={'_identity_current','_claim','_same_native_dispatch_claim','_bootstrap_current',
        '_worktree_current','_run_lease_current','_require_native_grant_ack_budget'}
    order=[node.func.attr for node in sorted(closing_calls,key=lambda node:node.lineno)if node.func.attr in authority_names]
    cycle=['_identity_current','_claim','_same_native_dispatch_claim','_bootstrap_current',
        '_worktree_current','_run_lease_current','_require_native_grant_ack_budget']
    require(order==cycle+cycle,
        'source:whole-current-before-after-read-batch-then-native-claim-bootstrap-allocation-lease-grant-reread')
    expiry=[node for node in ast.walk(closing)if isinstance(node,ast.Attribute)and node.attr=='expires_at_ms']
    grant_calls=[node for node in closing_calls if node.func.attr=='_require_native_grant_ack_budget']
    require(len(expiry)==1 and expiry[0].lineno>max(node.lineno for node in grant_calls),
        'source:guarded-attempt-ACK-time-checked-after-final-native-authority-reread')
    worktree_check=broker_methods['_worker_worktree_current']
    imports=[node for node in ast.walk(worktree_check)if isinstance(node,ast.ImportFrom)]
    require(len(imports)==1 and imports[0].module=='benchmarks.agent_supervisor.container_coding.container_worker_deployment'
        and [row.name for row in imports[0].names]==['observe_worker_kernel_worktree'],
        'source:worker-cwd-helper-import-only-on-original-owner-boundary')
    worktree_calls=[node for node in ast.walk(worktree_check)if isinstance(node,ast.Call)]
    helper_calls=[node for node in worktree_calls if isinstance(node.func,ast.Name)
        and node.func.id=='observe_worker_kernel_worktree']
    kernel_calls=[node for node in worktree_calls if isinstance(node.func,ast.Attribute)
        and node.func.attr=='_kernel_identity']
    require(len(helper_calls)==len(kernel_calls)==1 and helper_calls[0].lineno<kernel_calls[0].lineno,
        'source:narrow-worker-UID-cwd-observation-followed-by-complete-original-kernel-identity-reread')
    isolated=broker_methods['_isolated_handoff']
    isolated_calls=[node for node in ast.walk(isolated)if isinstance(node,ast.Call)]
    require(not any(isinstance(node.func,ast.Attribute)and node.func.attr=='readlink'for node in isolated_calls),
        'source:original-owner-never-directly-reads-cross-UID-worker-cwd')
    observations=[node for node in isolated_calls if isinstance(node.func,ast.Attribute)
        and node.func.attr=='_worker_worktree_current']
    spawned=[node for node in ast.walk(isolated)if isinstance(node,ast.Assign)
        and any(isinstance(target,ast.Attribute)and target.attr=='_isolated_spawned'for target in node.targets)]
    require(len(observations)==len(spawned)==1 and observations[0].lineno<spawned[0].lineno,
        'source:joined-cwd-and-posthelper-kernel-birth-before-positive-worker-record-or-released-ACK')
    grant_calls=[node for node in isolated_calls if isinstance(node.func,ast.Attribute)
        and node.func.attr=='_grant_worker_git_metadata_current']
    closes=sorted([node for node in isolated_calls if isinstance(node.func,ast.Attribute)
        and node.func.attr=='_closing_authority'],key=lambda node:node.lineno)
    captures=[node for node in isolated_calls if isinstance(node.func,ast.Attribute)and node.func.attr=='capture_allocated']
    git_checks=sorted([node for node in isolated_calls if isinstance(node.func,ast.Attribute)
        and node.func.attr=='_git_metadata_current'],key=lambda node:node.lineno)
    prepared_sends=[node for node in isolated_calls if isinstance(node.func,ast.Name)and node.func.id=='_send'
        and any(isinstance(child,ast.Attribute)and child.attr=='_prepared_response'for child in ast.walk(node))]
    require(len(grant_calls)==len(captures)==len(prepared_sends)==1 and len(closes)==len(git_checks)==2
        and closes[0].lineno<grant_calls[0].lineno<captures[0].lineno<closes[1].lineno<git_checks[0].lineno
        <prepared_sends[0].lineno<observations[0].lineno<git_checks[1].lineno<spawned[0].lineno,
        'source:Git-grant-after-original-native-authority-before-allocated-capture-current-before-ACK-and-after-birth')
    query_scopes=[node for node in ast.walk(isolated)if isinstance(node,ast.With)
        and any(isinstance(item.context_expr,ast.Call)and isinstance(item.context_expr.func,ast.Attribute)
            and item.context_expr.func.attr=='_git_metadata_readonly_environment'for item in node.items)]
    require(len(query_scopes)==1 and query_scopes[0].lineno<captures[0].lineno
        and query_scopes[0].end_lineno>=git_checks[0].lineno
        and query_scopes[0].end_lineno<prepared_sends[0].lineno,
        'source:original-Git-readonly-query-environment-covers-postgrant-callbacks-and-strict-check-before-ACK')
    final_run_lease=[node for node in isolated_calls if isinstance(node.func,ast.Attribute)
        and node.func.attr=='_run_lease_current'and query_scopes[0].end_lineno<node.lineno<prepared_sends[0].lineno]
    final_grant=[node for node in isolated_calls if isinstance(node.func,ast.Attribute)
        and node.func.attr=='_require_native_grant_ack_budget'and query_scopes[0].end_lineno<node.lineno<prepared_sends[0].lineno]
    final_expiry=[node for node in ast.walk(isolated)if isinstance(node,ast.Attribute)
        and node.attr=='expires_at_ms'and query_scopes[0].end_lineno<node.lineno<prepared_sends[0].lineno]
    require(len(final_run_lease)==len(final_grant)==len(final_expiry)==1
        and query_scopes[0].end_lineno<final_run_lease[0].lineno<final_grant[0].lineno
        <final_expiry[0].lineno<prepared_sends[0].lineno,
        'source:original-native-run-lease-grant-attempt-ACK-expiry-reread-after-query-restoration-before-ACK')
    require(not any(isinstance(node.func,ast.Attribute)and node.func.attr in {'_identity_current',
        '_closing_authority','require_current','capture_allocated'}and final_expiry[0].lineno<node.lineno
        <prepared_sends[0].lineno for node in isolated_calls),
        'source:no-current-policy-callback-after-final-native-ACK-expiry-reread')
    release_run_lease=[node for node in isolated_calls if isinstance(node.func,ast.Attribute)
        and node.func.attr=='_run_lease_current'and observations[0].lineno<node.lineno<spawned[0].lineno]
    release_grant=[node for node in isolated_calls if isinstance(node.func,ast.Attribute)
        and node.func.attr=='_require_native_grant_ack_budget'and observations[0].lineno<node.lineno<spawned[0].lineno]
    release_expiry=[node for node in ast.walk(isolated)if isinstance(node,ast.Attribute)
        and node.attr=='expires_at_ms'and observations[0].lineno<node.lineno<spawned[0].lineno]
    require(len(release_run_lease)==len(release_grant)==len(release_expiry)==1
        and git_checks[1].lineno<release_run_lease[0].lineno<release_grant[0].lineno
        <release_expiry[0].lineno<spawned[0].lineno,
        'source:run-lease-grant-attempt-release-expiry-rechecked-after-worker-metadata-and-Git-custody')
    isolated_text=ast.get_source_segment(broker,isolated)
    require('remaining = deadline - time.monotonic()'in isolated_text
        and 'timeout_seconds=min(3.0,remaining)'in isolated_text
        and 'time.monotonic() < deadline'in isolated_text,
        'source:kernel-birth-and-worker-metadata-use-one-original-deadline-with-no-extension')
    query_method=broker_methods['_git_metadata_readonly_environment']
    query_text=ast.get_source_segment(broker,query_method)
    require('guard = self._git_metadata_identity()'in query_text
        and 'with guard.readonly_query_environment():'in query_text
        and query_text.count('self._git_metadata_identity() is guard')==2,
        'source:original-Git-resource-identity-rechecked-across-query-and-prior-environment-restoration')
    grant_method=broker_methods['_grant_worker_git_metadata_current']
    grant_text=ast.get_source_segment(broker,grant_method)
    require('allocation["branch"]'in grant_text and 'receipt.get("selected_branch")'in grant_text
        and 'receipt.get("selected_commit") == commit'in grant_text
        and '_git_metadata_original = guard'in grant_text and '_git_metadata_id'in grant_text,
        'source:Git-resource-original-identity-and-exact-native-branch-current-canonical-commit-join')
    git_current=broker_methods['_git_metadata_current']
    require(any(isinstance(node,ast.Call)and isinstance(node.func,ast.Attribute)and node.func.attr=='require_current'
        for node in ast.walk(git_current)),'source:Git-current-check-invokes-original-retained-FD-stat-byte-guard')
    # Refusal diagnostics are a separate bounded representation. They do not
    # replace a failed guard or run source/proof/policy callbacks.
    git_diagnostic=broker_methods['_public_git_metadata_drift']
    diagnostic_text=ast.get_source_segment(broker,git_diagnostic)
    diagnostic_calls=[node for node in ast.walk(git_diagnostic)if isinstance(node,ast.Call)
        and isinstance(node.func,ast.Attribute)]
    require(not any(node.func.attr in {'_identity_current','_verify','require_current','prepare_dispatch',
        'capture_allocated','_closing_authority'}for node in diagnostic_calls),
        'source:Git-refusal-export-performs-no-authority-current-or-policy-callback')
    require('type(error) is not WorkerWorktreeObservationError'in diagnostic_text
        and 'error.__dict__.get("git_metadata_drift")'in diagnostic_text
        and 'receipt["directories"]'in diagnostic_text and 'receipt["files"]'in diagnostic_text
        and 'len(selected) == 1'in diagnostic_text,
        'source:Git-refusal-export-only-exact-source-owned-error-and-original-selected-closure')
    require('set(changed) == derived'in diagnostic_text and 'len(raw) <= 16384'in diagnostic_text
        and 'type(selected[0]["granted_mode"]) is int'in diagnostic_text
        and 'expected["st_mode"] & 0o7777 == selected[0]["granted_mode"]'in diagnostic_text,
        'source:Git-refusal-export-bounds-and-recomputes-selected-mode-and-field-differences')
    serve=broker_methods['_serve'];serve_text=ast.get_source_segment(broker,serve)
    require('drift = self._public_git_metadata_drift(error)'in serve_text
        and 'if drift is not None: observation["git_metadata_drift"] = drift'in serve_text
        and '"ok":False'in serve_text and 'self._retire(ambiguous='in serve_text,
        'source:optional-Git-drift-record-preserves-refusal-and-nonrefundable-retirement')
    deployment_text=read(C/'benchmarks/agent_supervisor/container_coding/container_worker_deployment.py').decode()
    deployment_tree=ast.parse(deployment_text)
    git_class=next(node for node in deployment_tree.body if isinstance(node,ast.ClassDef)
        and node.name=='WorkerGitMetadataReadGuard')
    deployment_methods={node.name:node for node in git_class.body if isinstance(node,ast.FunctionDef)}
    optional_method=deployment_methods['readonly_query_environment']
    optional_text=ast.get_source_segment(deployment_text,optional_method)
    require('with self._query_lock:'in optional_text
        and 'self._query_lock is not _GIT_OPTIONAL_QUERY_LOCK'in optional_text
        and 'self._query_active is not None'in optional_text
        and 'threading.get_ident()'in optional_text and optional_text.count('self.require_current()')==2,
        'source:optional-Git-lock-prevention-original-nonnested-context-and-unchanged-strict-FD-checks')
    require('present = "GIT_OPTIONAL_LOCKS" in os.environ'in optional_text
        and 'os.environ["GIT_OPTIONAL_LOCKS"] = "0"'in optional_text
        and 'os.environ["GIT_OPTIONAL_LOCKS"] = previous'in optional_text
        and 'os.environ.pop("GIT_OPTIONAL_LOCKS", None)'in optional_text
        and 'if primary is None and cleanup_error is not None:'in optional_text,
        'source:optional-lock-prevention-restores-exact-prior-presence-and-value-and-preserves-primary-failure')
    module_functions={node.name:node for node in deployment_tree.body if isinstance(node,ast.FunctionDef)}
    helper_text=ast.get_source_segment(deployment_text,module_functions['observe_worker_kernel_worktree'])
    require('type(timeout_seconds) in (int, float)'in helper_text and 'math.isfinite(timeout_seconds)'in helper_text
        and '0 < timeout_seconds <= 3'in helper_text and 'timeout=timeout_seconds'in helper_text,
        'source:fixed-metadata-helper-receives-only-finite-remaining-time-cap-at-most-three-seconds')
    observer_literal=next(node.value.value for node in deployment_tree.body if isinstance(node,ast.Assign)
        and any(isinstance(target,ast.Name)and target.id=='WORKER_WORKTREE_OBSERVER'for target in node.targets))
    require("status.get('Uid','').split()!=['1001']*4"in observer_literal
        and "for key in ('CapEff','CapPrm','CapAmb')"in observer_literal
        and "readiness not in ('0','1')"in observer_literal
        and 'deadline=time.monotonic()+2.0'in observer_literal
        and "elif first!=original:"in observer_literal and 'if not ready:'in observer_literal
        and 'if first!=second:'in observer_literal,
        'source:bounded-NNP-startup-wait-preserves-exact-UID-caps-birth-cwd-command-and-two-ready-observations')
    failure_method=broker_methods['_public_worker_worktree_failure']
    failure_text=ast.get_source_segment(broker,failure_method)
    require('type(error) is not WorkerWorktreeObservationError'in failure_text
        and 'error.__dict__.get("worker_worktree_failure")'in failure_text
        and 'value["timeout_seconds"] == self._worker_metadata_timeout'in failure_text
        and 'value["helper_sha256"] == hashlib.sha256(expected).hexdigest()'in failure_text
        and 'child_wire = _wire(refusal) + b"\\n"'in failure_text,
        'source:closed-worker-helper-failure-joins-original-timeout-source-entry-and-reconstructed-refusal-bytes')
    require(not any(isinstance(node,ast.Call)and isinstance(node.func,ast.Attribute)
        and node.func.attr in {'_identity_current','_verify','require_current','prepare_dispatch','capture_allocated'}
        for node in ast.walk(failure_method)),
        'source:worker-helper-refusal-metadata-runs-no-current-policy-or-authority-callback')
    entry_start=deployment_text.index('WORKER_ENTRY = ')
    entry_profile=deployment_text.index('profile=_worker_profile(root,',entry_start)
    entry_scrub=deployment_text.index('os.environ.clear()',entry_profile)
    observer_git=deployment_text.index("if profile['observer_only']:os.environ['GIT_OPTIONAL_LOCKS']='0'",entry_scrub)
    require(entry_start<entry_profile<entry_scrub<observer_git,
        'source:observer-only-worker-forces-optional-lock-prevention-after-verified-profile-and-environment-scrub')
    drift_method=deployment_methods['_drift'];drift_text=ast.get_source_segment(deployment_text,drift_method)
    require(isinstance(drift_method.body[-1],ast.Raise)
        and 'error.git_metadata_drift'in drift_text
        and 'WorkerWorktreeObservationError("retained Git metadata custody changed")'in drift_text,
        'source:metadata-drift-emitter-always-retains-original-failed-custody-refusal')
    guard_text=ast.get_source_segment(deployment_text,deployment_methods['require_current'])
    require('retained != tuple(granted)'in guard_text and 'path_stat != tuple(granted)'in guard_text
        and 'fresh_first != tuple(granted)'in guard_text and 'fresh_last != tuple(granted)'in guard_text
        and 'observed_digest != digest'in guard_text,
        'source:diagnostic-emission-waives-no-selected-retained-fresh-stat-or-hash-field')
    counts.update(Git_drift_diagnostics_are_data_only=True,
        Git_drift_diagnostics_can_authorize_dispatch=False,
        Git_drift_directory_or_file_stat_fields_waived=False,
        Git_optional_lock_prevention_is_launch_authority=False,
        Git_optional_query_lock_constrains_unrelated_threads=False,
        Git_optional_query_prior_environment_restored_before_ACK=True,
        worker_readiness_success_accepts_NoNewPrivs_zero=False,
        worker_readiness_wait_extends_original_ACK_deadline=False,
        actual17_helper_failure_cause_known=False)
    close_method=broker_methods['close_after_native_stop']
    stop_checks=[node for node in ast.walk(close_method)if isinstance(node,ast.Call)
        and isinstance(node.func,ast.Attribute)and node.func.attr=='_context_refresh_stopped']
    git_disposal=[node for node in ast.walk(close_method)if isinstance(node,ast.Call)
        and isinstance(node.func,ast.Attribute)and node.func.attr=='_close_git_metadata_after_stop']
    finalizers=[node for node in ast.walk(close_method)if isinstance(node,ast.Try)
        and any(child is git_disposal[0]for statement in node.finalbody for child in ast.walk(statement))]if git_disposal else[]
    require(len(stop_checks)==len(git_disposal)==len(finalizers)==1 and stop_checks[0].lineno<git_disposal[0].lineno,
        'source:original-Git-resource-disposed-in-budget-abort-finally-only-after-native-STOP')
    counts.update(nominal_successful_pair_whole_checks_from_source=19,
        nominal_whole_check_count_is_measured=False,Git_read_grant_adds_original_closing_batch=True,
        Git_guard_can_authorize_birth_from_serialized_receipt=False)
    counts.update(full_current_checks_per_closing_batch=2,native_worktree_reads_per_closing_batch=2,
        batch_identity_checks_grant_effect_authority=False,whole_current_call_count_is_measured=False)
    handoff=next(n for n in klass.body if isinstance(n,ast.FunctionDef)and n.name=='_handoff')
    calls=[n for n in ast.walk(handoff)if isinstance(n,ast.Call)]
    preparations=[n for n in calls if isinstance(n.func,ast.Attribute)and n.func.attr=='prepare_dispatch']
    sends=[n for n in calls if isinstance(n.func,ast.Name)and n.func.id=='_send']
    require(len(preparations)==1 and preparations[0].lineno<min(n.lineno for n in sends),
        'source:original-owner-reservation-before-first-prepared-ACK')
    scope=read(base/'runtime/checked_observer_budget.py').decode()
    require('_pending.abort()'in scope and 'close_after_native_stop'in scope and 'os.getpid()'in scope,
        'source:original-owner-identity-nonrefund-and-fenced-close-present')
    scope_tree=ast.parse(scope);scope_functions={node.name:node for node in scope_tree.body if isinstance(node,ast.FunctionDef)}
    factory=scope_functions['create_checked_observer_budget_scope'];factory_calls=[node for node in ast.walk(factory)if isinstance(node,ast.Call)]
    storage=[node for node in factory_calls if isinstance(node.func,ast.Name)and node.func.id=='_prepare_checked_storage']
    instruction=[node for node in factory_calls if isinstance(node.func,ast.Attribute)and node.func.attr=='_instruction']
    delivery=[node for node in factory_calls if isinstance(node.func,ast.Attribute)and node.func.attr=='_current_delivery_scope']
    require(len(storage)==len(instruction)==len(delivery)==1 and storage[0].lineno<instruction[0].lineno<delivery[0].lineno,
        'source:fixed-metadata-provision-before-first-original-instruction-custody-before-delivery-callbacks')
    helper=scope_functions['_prepare_checked_storage']
    chmods=[node for node in ast.walk(helper)if isinstance(node,ast.Call)and isinstance(node.func,ast.Attribute)
        and node.func.attr in {'chmod','fchmod'}]
    created=[node for node in ast.walk(helper)if isinstance(node,ast.If)and isinstance(node.test,ast.Name)and node.test.id=='created']
    require(len(chmods)==1 and chmods[0].func.attr=='fchmod' and len(created)==1
        and any(node is chmods[0]for node in ast.walk(created[0])),'source:only-newly-created-directory-FD-permission-change')
    require(not any(isinstance(node,ast.Call)and isinstance(node.func,ast.Attribute)and node.func.attr=='umask'
        for node in ast.walk(scope_tree)),'source:owner-global-umask-never-changed')
    scope_class=next(node for node in scope_tree.body if isinstance(node,ast.ClassDef)and node.name=='CheckedObserverBudgetScope')
    methods={node.name:node for node in scope_class.body if isinstance(node,ast.FunctionDef)}
    dispatch_calls=[node for node in ast.walk(methods['prepare_dispatch'])if isinstance(node,ast.Call)
        and isinstance(node.func,ast.Attribute)]
    require(any(node.func.attr=='replay_checked_context_extension'for node in dispatch_calls)
        and not any(node.func.attr=='load_checked_context_extension'for node in dispatch_calls),
        'source:pregrant-uses-only-canonical-replay-plus-original-private-file-guard')
    capture_calls=[node for node in ast.walk(methods['capture_allocated'])if isinstance(node,ast.Call)
        and isinstance(node.func,ast.Attribute)]
    strict=[node for node in capture_calls if node.func.attr=='load_checked_context_extension']
    complete=[node for node in capture_calls if node.func.attr=='require_granted']
    require(len(strict)==1 and complete and min(node.lineno for node in complete)<strict[0].lineno,
        'source:complete-native-grant-profile-before-unchanged-strict-current-allocated-loader')
    runtime=read(base/'entrypoints/admitted_benchmark_runtime.py').decode()
    require('checked_observer_budget_scope.material_binding'in runtime and 'owner_dispatch_identity()'in runtime
        and 'checked_observer_budget_scope.bind_runtime(runtime' in runtime,
        'source:signed-scope-and-owner-hint-before-final-native-binding')
    report=load(selected('tests_report'));xml=read(selected('tests_xml'));root=ET.fromstring(xml);cases=list(root.iter('testcase'))
    actual={'tests':len(cases),'unique_tests':len({(r.get('classname'),r.get('name'))for r in cases}),
        'failures':len(list(root.iter('failure'))),'errors':len(list(root.iter('error'))),'skips':len(list(root.iter('skipped')))}
    compare_tree(report['counts'],actual,'tests:own-final-XML-census')
    expected=config['expected_unique_tests']
    require(type(expected)is int and expected>=818,'tests:explicit-final-expected-census')
    require(actual['tests']==actual['unique_tests']==expected and not any(actual[k]for k in ('failures','errors','skips'))
        and report['qualified']is True and report['exit_code']==0 and report['source_bytes_unchanged']is True,
        'tests:current-explicit-unique-pass-zero-fail-error-skip')
    compare_tree(report['source_pins_before'],report['source_pins_after'],'tests:all9-source-and-test-pins-unchanged')
    require(len(report['source_pins_before'])==9,'tests:exact9-changed-Python-files')
    for row in report['source_pins_after']:read(row['path'],row)
    counts['final_unique_tests']=expected


def audit_package():
    report=load(selected('package_report'))
    require(report['qualified']is True and report['files']==9 and report['modified']==4 and report['new']==5,
        'package:exact9-source-test-files4-modified5-new')
    require(report['exact_scratch_application']is True and report['git_executable_modes_match']is True
        and report['full_permission_bits_preserved_by_git_claimed']is False and report['source_index_unchanged']is True
        and report['production_promoted']is False and report['project_pushes']==0,
        'package:exact-application-Git-executable-modes-no-full-permission-or-promotion-claim')
    patch=read(report['patch']['path'],report['patch']);baseline={}
    for row in report['sources']:
        relative=row['relative_path'];source=read(row['current']['path'],row['current']);applied=read(row['applied']['path'],row['applied'])
        require(source==applied,'package:independent-scratch-exact-source:'+relative)
        if not row['new']:
            baseline[relative]=read(PREVIOUS/'checkout'/relative,row['baseline'])
        require(int(row['source_mode'],8)&0o111==0,'package:current-nonexecutable-Git-mode:'+relative)
    projected=apply_text_patch(patch,baseline)
    require(len(projected)==9,'package:independent-unified-patch-9-targets')
    for row in report['sources']:
        require(projected[row['relative_path']]==read(row['current']['path']),'package:own-patch-decoder-exact-source:'+row['relative_path'])
    counts.update(packaged_files=9,package_modified=4,package_new=5,independent_source_patch_bytes=len(patch))


def source_string(source, name):
    """Reconstruct literal concatenation from AST without importing its module."""
    assignments={target.id:node.value for node in ast.parse(source).body if isinstance(node,ast.Assign)
        for target in node.targets if isinstance(target,ast.Name)}
    def decode(node,seen):
        require(len(seen)<=64,'source-literal:bounded-concatenation:'+name)
        if isinstance(node,ast.Constant)and type(node.value)is str:return node.value
        if isinstance(node,ast.Name):
            require(node.id in assignments and node.id not in seen,'source-literal:known-nonrecursive-fragment:'+node.id)
            return decode(assignments[node.id],seen|{node.id})
        require(isinstance(node,ast.BinOp)and isinstance(node.op,ast.Add),'source-literal:literal-add-only:'+name)
        result=decode(node.left,seen)+decode(node.right,seen)
        require(len(result.encode())<=512*1024,'source-literal:bounded-worker-entry:'+name)
        return result
    require(name in assignments,'source-literal:named-root:'+name)
    return decode(assignments[name],{name}).encode()


def audit_helper_failure_metadata(value,label):
    """Independent decoder for closed helper failure data; this conveys no birth."""
    if type(value)is dict:
        if value.get('schema')=='checked-worker-kernel-worktree-helper-failure@1':
            fields={'schema','phase','returncode','stdout_bytes','stdout_sha256','helper_sha256','helper_bytes',
                'timeout_seconds','helper_refusal','metadata_only','execution_authority','proof_authority',
                'completion_authority','source_body_executed','provider_calls'}
            require(set(value)==fields and value['metadata_only']is True,'helper-failure:closed-data:'+label)
            ceiling(value,'helper-failure:'+label)
            require(value['phase']in {'subprocess_response','subprocess_timeout'}
                and(type(value['returncode'])is int if value['phase']=='subprocess_response'else value['returncode']is None)
                and type(value['stdout_bytes'])is int and 0<=value['stdout_bytes']<2**63
                and type(value['timeout_seconds'])is float and 0<value['timeout_seconds']<=3.0,
                'helper-failure:bounded-result-and-original-timeout:'+label)
            body=source_string(read(C/'benchmarks/agent_supervisor/container_coding/container_worker_deployment.py').decode(),'WORKER_ENTRY')
            require(value['helper_bytes']==len(body)and value['helper_sha256']==sha(body),
                'helper-failure:own-literal-decoder-selected-installed-entry-pin:'+label)
            refusal=value['helper_refusal']
            if refusal is not None:
                child_fields={'schema','stage','error_type','message_sha256','failure_frames','metadata_only',
                    'execution_authority','proof_authority','completion_authority','source_body_executed','provider_calls'}
                stages={'profile','privilege','boundary','self_privilege','worktree_scope','target_stat',
                    'target_status','target_command','target_birth_worktree','readiness','stable_observation','output'}
                require(type(refusal)is dict and set(refusal)==child_fields
                    and refusal['schema']=='checked-worker-kernel-worktree-refusal@1'
                    and refusal['stage']in stages and refusal['metadata_only']is True
                    and re.fullmatch('[A-Za-z_][A-Za-z0-9_]{0,127}',refusal['error_type'])
                    and re.fullmatch('[0-9a-f]{64}',refusal['message_sha256']),
                    'helper-failure:closed-child-refusal-no-text:'+label)
                frames=refusal['failure_frames']
                require(type(frames)is list and len(frames)<=16,'helper-failure:bounded-location-frames:'+label)
                for frame in frames:
                    require(type(frame)is dict and set(frame)=={'file','function','line'}
                        and type(frame['line'])is int and 0<=frame['line']<2**31
                        and all(type(frame[key])is str and 0<len(frame[key])<=bound
                            and all(32<=ord(ch)<127 for ch in frame[key])for key,bound in (('file',256),('function',128)))
                        and '/'not in frame['file']and '\\'not in frame['file'],
                        'helper-failure:locations-only-no-source-or-locals:'+label)
                raw=canonical(refusal)+b'\n'
                require(value['phase']=='subprocess_response'and value['returncode']!=0
                    and value['stdout_bytes']==len(raw)<=16384 and value['stdout_sha256']==sha(raw),
                    'helper-failure:own-nested-refusal-byte-count-and-SHA:'+label)
            require(re.fullmatch('[0-9a-f]{64}',value['stdout_sha256'])is not None,
                'helper-failure:stdout-hash-is-data-not-output-or-authority:'+label)
            counts['helper_failure_metadata_records_validated']=counts.get('helper_failure_metadata_records_validated',0)+1
        for key,item in value.items():audit_helper_failure_metadata(item,label+'/'+key)
    elif type(value)is list:
        for i,item in enumerate(value):audit_helper_failure_metadata(item,label+'/'+str(i))


def audit_boundary_and_reports():
    boundary=load(selected('boundary_result'));require(boundary['qualified']is True,'boundary:actual-installer-and-kernel-qualification')
    installation=load(selected('boundary_installation'));qualification=load(selected('boundary_qualification'))
    require(qualification['qualified']is True,'boundary:actual-native-qualification-succeeded')
    pin_declared(installation,'installation',origin_path=selected('boundary_installation'))
    pin_declared(qualification,'boundary-qualification',origin_path=selected('boundary_qualification'))
    for name in config.get('final_reports',[]):
        require(Path(name).is_absolute() and Path(name).parent==W,'reports:owned-final-explicit-file')
        value=load(name);ceiling(value,'final-report:'+Path(name).name)
    for name in config.get('final_scripts',[]):
        require(Path(name).is_absolute() and Path(name).parent==W and Path(name).suffix=='.py','reports:owned-final-source-script')
        ast.parse(read(name),filename=name)
    for row in config.get('additional_public_pins',[]):
        # A separately declared source archive may exceed ordinary evidence
        # limits; it is metadata only unless explicitly bounded <=256MiB.
        if row.get('policy')=='metadata-only-public-source-archive':
            require(Path(row['path']).is_relative_to(W) and Path(row['path']).name=='public-source.tar.gz'
                and type(row['bytes'])is int and 0<=row['bytes']<=256*1048576,
                'reports:exact-typed-bulk-source-metadata-policy')
            metadata_only.append({**row,'reason':'explicit-bulk-source-archive-metadata-not-opened'})
        else:read(row['path'],row,max_bytes=row.get('max_bytes',8388608))
    for name in config.get('additional_json',[]):
        require(Path(name).is_relative_to(W),'reports:explicit-owned-extra-JSON')
        value=load(name);pin_declared(value,'extra:'+Path(name).name,origin_path=name)
        audit_helper_failure_metadata(value,'extra:'+Path(name).name)
    # Follow provenance for this selected run, not every old sealed report's
    # historical producer path. The previous650+356 byte occurrences have
    # their own explicit census and cannot become current-source authority.
    explicit_current={str(selected('runtime_freeze')),str(selected('actual_result')),str(selected('model_result'))}
    explicit_current.update(config.get('final_reports',[]));explicit_current.update(config.get('additional_json',[]))
    if 'public_inventory'in config:explicit_current.add(str(selected('public_inventory')))
    for path,capture in list(captures.items()):
        if Path(path).suffix in {'.json','.jsonl'} and (path in explicit_current or
                any(Path(path).is_relative_to(root)for root in (R,A,F))):
            try:value=parse(capture['raw'])
            except (ValueError,UnicodeError):continue
            pin_declared(value,'named:'+path,origin_path=path)
    counts.update(declared_pin_occurrences=len(declared_occurrences),
        metadata_only_descriptor_occurrences=len(metadata_only),
        metadata_only_paths=sorted({r['path']for r in metadata_only}))
def audit():
    require(bool(config.get('ready')),'config:root-explicit-final-readiness')
    require(bool(config.get('final_reports')),'config:final-root-reports-required')
    current_keys={'runtime_freeze','actual_result','model_result','fixture_result','boundary_result',
        'boundary_installation','boundary_qualification','tests_report','tests_xml','package_report','public_inventory'}
    current_reports={config[key]for key in current_keys if type(config.get(key))is str}
    current_reports.update(config.get('final_reports',[]))
    selected_roots=[Path(config[key])for key in ('actual_public','model_public','fixture_public')]
    for name in config.get('historical_descriptor_files',[]):
        require(type(name)is str and Path(name).is_absolute()and Path(name).is_relative_to(W)
            and name not in current_reports and not any(Path(name).is_relative_to(root)for root in selected_roots),
            'config:historical-origin-cannot-defer-selected-current-custody:'+str(name))
    result=audit_exports();summary=load(R/'summary.json');basis=audit_native_basis(summary)
    audit_view(basis);fixture=audit_native_fixture(basis)
    audit_native_run(result,basis,fixture);audit_proof(basis)
    audit_source_and_tests();audit_package();audit_preservation();audit_boundary_and_reports()
    counts.update(project_or_native_implementation_imports=0,reviewer_service_calls=0,reviewer_provider_calls=0,
        reviewer_tests_run=0,reviewer_prover_invocations=0,reviewer_subprocesses=0,
        database_bodies_opened=False,CAS_bodies_opened=False,DuckLake_parquet_bodies_opened=False,
        full_supervisor_entrypoint_used=False,Terminal_Bench_harness_used=False,
        provider_usage_measured=False,source_to_model_equivalence_proved=False,
        training_convergence_proved=False,full_task_satisfaction=False)


def write_ordered_arrays(path, arrays):
    """Lossless bounded output shards, never deduplicated or check-filtered."""
    limit=8*1048576;target=6*1048576
    if set(arrays)!={'checks','declared_pin_occurrences'}:raise ValueError('exact ordered audit arrays required')
    directory=path.with_name(path.stem+'.arrays')
    if directory.parent!=W:raise ValueError('owned sibling array directory required')
    planned=[];descriptors={}
    for name,values in arrays.items():
        if type(values)is not list:raise ValueError('original ordered list required')
        full=canonical(values)
        chunks=[];items=[];size=0
        for item in values:
            encoded=canonical(item)
            if len(encoded)+1024>limit:raise ValueError('single audit array record exceeds segment bound')
            if items and size+len(encoded)+1>target:
                chunks.append(items);items=[];size=0
            items.append(item);size+=len(encoded)+1
        if items:chunks.append(items)
        start=0;rows=[]
        for index,items in enumerate(chunks):
            part={'schema':'terminal-audit-ordered-array-segment@1','array':name,
                'index':index,'start':start,'items':items}
            raw=canonical(part)+b'\n'
            if len(raw)>limit:raise ValueError('audit array segment exceeds8MiB bound')
            filename=directory/(name+'-'+str(index).zfill(4)+'.json')
            pin={'path':str(filename),'bytes':len(raw),'sha256':sha(raw)}
            rows.append({'index':index,'start':start,'count':len(items),'pin':pin})
            planned.append((filename,raw,part));start+=len(items)
        if start!=len(values):raise ValueError('ordered segmentation changed array count')
        descriptors[name]={'schema':'terminal-audit-ordered-array@1','name':name,'count':len(values),
            'canonical_bytes':len(full),'canonical_sha256':sha(full),'segments':rows}
    if len(planned)>128 or sum(len(raw)for _,raw,_ in planned)>512*1048576:
        raise ValueError('bounded ordered audit part population exceeded')
    # All data is planned before exclusive output effects; the main report is
    # published only after fresh FD/stat/hash and full reconstruction checks.
    os.mkdir(directory,0o700)
    held=[]
    try:
        reconstructed={name:[]for name in arrays}
        for filename,raw,expected in planned:
            fd=os.open(filename,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
            with os.fdopen(fd,'wb')as stream:stream.write(raw)
            fd=os.open(filename,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK);held.append(fd)
            before=os.fstat(fd)
            if not(stat.S_ISREG(before.st_mode)and before.st_nlink==1 and before.st_uid==os.geteuid()
                and stat.S_IMODE(before.st_mode)==0o600 and before.st_size==len(raw)<=limit):
                raise ValueError('original bounded audit output segment required')
            observed=b''
            while len(observed)<=limit:
                block=os.read(fd,min(1048576,limit+1-len(observed)))
                if not block:break
                observed+=block
            if observed!=raw or stamp(before)!=stamp(os.fstat(fd))or stamp(before)!=stamp(filename.lstat()):
                raise ValueError('audit output segment changed during reconstruction')
            actual=parse(observed)
            if canonical(actual)+b'\n'!=observed or canonical(actual)!=canonical(expected):
                raise ValueError('audit output segment is not exact canonical original data')
            name=actual['array']
            if actual['start']!=len(reconstructed[name]):raise ValueError('audit output segment order changed')
            reconstructed[name].extend(actual['items'])
        for name,values in arrays.items():
            observed=canonical(reconstructed[name]);descriptor=descriptors[name]
            if (type(descriptor['count'])is not int or type(descriptor['canonical_bytes'])is not int
                or len(reconstructed[name])!=descriptor['count'] or observed!=canonical(values)
                or len(observed)!=descriptor['canonical_bytes']or sha(observed)!=descriptor['canonical_sha256']):
                raise ValueError('complete ordered audit array reconstruction changed original records')
        counts.update(output_ordered_array_segments=len(planned),output_array_reconstruction_verified=True,
            output_arrays_deduplicated=False,output_checks_dropped=False)
        return descriptors
    finally:
        for fd in held:os.close(fd)


def finish(path):
    for name,value in captures.items():
        before=os.fstat(value['fd'])
        check(stamp(before)==value['stamp']==stamp(Path(name).lstat()),'closing:retained-FD-stat-path:'+name)
        os.lseek(value['fd'],0,os.SEEK_SET);digest=hashlib.sha256()
        while block:=os.read(value['fd'],1048576):digest.update(block)
        check(digest.hexdigest()==value['pin']['sha256'],'closing:all-retained-bytes:'+name)
    report={'schema':'terminal-admitted-context-independent-review@2','passed':not failures,
        'qualified':not failures,'check_count':len(checks),'passed_checks':len(checks)-len(failures),
        'failed_checks':len(failures),'blockers':failures,'checks':checks,'counts':counts,
        'read_pins':[captures[name]['pin']for name in sorted(captures)],
        'explicit_container_host_exports':exports,'metadata_only_descriptors':metadata_only,
        'declared_pin_occurrences':declared_occurrences,
        'input_custody':'Explicit named public nofollow regular single-link FDs; stat and SHA256 before and after. Container descriptors use explicit export/mount maps, never host path reinterpretation.',
        'review_independence_scope':'Separate project-import-free reference decoder, Git-pack decoder, public signature verifier, complete renderer reconstruction and pinned offline token/ledger recount. This agent authored the broker and some earlier deployment/tests; this is not independent authorship review.',
        'read_only_execution':{'project_or_native_implementation_imports':0,'project_service_calls':0,
            'database_bodies_opened':False,'CAS_bodies_opened':False,'DuckLake_parquet_bodies_opened':False,
            'tests_run':0,'prover_invocations':0,'provider_calls':0,'training_steps':0,
            'source_body_executed':False,'source_or_sealed_files_edited':False,'network_fetches':0,
            'subprocesses':0,'only_nonstdlib_dependency':'tiktoken0.13.0 directly constructed from retained offline BPE bytes'},
        'limits':{'public_snapshots_reconstitute_original_owner_authority':False,
            'original_object_identity_independently_recovered':False,'public_broker_claim_fence_receipt_self_contained':False,
            'receipt_emitting_worker_birth_directly_joined_in_public_data':False,
            'loaded_module_code_attested':False,'transitive_dependency_closure_attested':False,
            'full_supervisor_entrypoint_used':False,'Terminal_Bench_harness_used':False,
            'provider_transmission_verified':False,'provider_usage_measured':False,'provider_billing_savings_measured':False,
            'source_to_model_equivalence_proved':False,'training_convergence_proved':False,
            'full_task_satisfaction':False,'reviewer_reinvoked_native_runtime_or_Lean':False,
            'interpretation':'Native START/STOP, authenticated kernel births and original retained-owner checks remain attributed to pinned actual application evidence. Public signatures authenticate supplied keys, not external identity origin; data snapshots cannot prove original Python identity, private seals, active grants/locks, callback chronology or receipt-emitter provenance. Local token counts concern one authored observer input, not provider billing or whole-task savings.'}}
    segments=write_ordered_arrays(path,{'checks':report['checks'],
        'declared_pin_occurrences':report['declared_pin_occurrences']})
    report['checks']=segments['checks'];report['declared_pin_occurrences']=segments['declared_pin_occurrences']
    raw=canonical(report)+b'\n'
    if len(raw)>8*1048576:raise ValueError('review report exceeds8MiB bound')
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb')as stream:stream.write(raw)
    for capture in captures.values():os.close(capture['fd'])
    print(json.dumps({'passed':report['passed'],'check_count':len(checks),'failed_checks':len(failures),
        'read_pins':len(report['read_pins']),'bytes':len(raw),'sha256':sha(raw),'first_failures':failures[:8]}))
    return 0 if report['passed']else 1


if __name__=='__main__':
    require(len(sys.argv)in{3,5} and sys.argv[1]=='--config','usage:--config-explicit-JSON-[--report-name]')
    config_path=Path(sys.argv[2]).absolute();require(config_path.parent==W,'config:owned-stage-only')
    config=load(config_path)
    report_name='independent-review.json'
    if len(sys.argv)==5:
        require(sys.argv[3]=='--report','usage:optional-owned-report-name')
        report_name=sys.argv[4]
    report=W/report_name
    require(report.parent==W and report.suffix=='.json','report:owned-JSON-output-only')
    read(Path(__file__).absolute())
    try:audit()
    except BaseException as error:
        check(False,'audit:unhandled-error',{'type':type(error).__name__,'message':str(error),'traceback':traceback.format_exc()})
    raise SystemExit(finish(report))
