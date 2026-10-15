"""Independent, named-file Stage X evidence audit.

Never imports project/native implementations, opens databases/CAS/lake bodies,
executes source, or invokes a service, test, prover, provider or training job.
The only non-stdlib dependency is the separately pinned offline tokenizer.
"""
from __future__ import annotations

import ast
import base64
from collections import Counter
from copy import deepcopy
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import stat
import sys
import traceback
import xml.etree.ElementTree as ET

W = Path('/home/barberb/lift_coding/maintenance/terminal-semantic-audit-view-20261013-01')
PREVIOUS = Path('/home/barberb/lift_coding/maintenance/terminal-native-semantic-capsule-20261013-01')
R = W / 'preview-run-02'
A = W / 'actual-public-audit-01'
C = Path('/home/barberb/lift_coding/maintenance/terminal-token-reduction-20261007-01/checkout')
V = Path('/home/barberb/lift_coding/maintenance/terminal-call-review-forecast-20261013-01')
TOKENIZER = Path('/home/barberb/lift_coding/maintenance/terminal-token-pairing-20261012-01/pinned-host-tokenizer')
EXPECTED_PRIOR_SEAL = '469541a3ddc2f9e9a6a388301d41ad97f6d6d74924d1c9b19a9063c597a0c403'
checks, failures, captures, counts = [], [], {}, {}


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
        'production_context_pack_qualified', 'context_sufficiency_proved'}
    if type(value) is dict:
        for key, item in value.items():
            if key in names:
                check(item is False, name + '/' + key + ':false-ceiling')
            ceiling(item, name + '/' + key)
    elif type(value) is list:
        for index, item in enumerate(value):
            ceiling(item, name + '/' + str(index))


def decode_wire(raw):
    """Own bounded decoder; does not call or copy target functions at runtime."""
    require(len(raw) <= 256000, 'wire:encoded-byte-bound')
    envelope = parse(raw, floats=False)
    fields = {'schema', 'codec_version', 'decoder_instructions', 'original_canonical_sha256',
              'original_canonical_bytes', 'string_table', 'encoded_node', 'codec_sha256'}
    require(type(envelope) is dict and set(envelope) == fields, 'wire:closed-envelope')
    require(canonical(envelope) == raw, 'wire:canonical-envelope')
    require(envelope['schema'] == 'terminal-semantic-context-dictionary@1'
            and type(envelope['codec_version']) is int and envelope['codec_version'] == 1,
            'wire:exact-schema-version')
    require(envelope['codec_sha256'] == sha(canonical({k:v for k,v in envelope.items()
        if k != 'codec_sha256'})), 'wire:envelope-digest')
    require(type(envelope['decoder_instructions']) is str
            and 'then run the existing complete packet/current-source/proof validators' in
            envelope['decoder_instructions'], 'wire:decoder-guidance-included')
    table = envelope['string_table']
    require(type(table) is list and len(table) <= 256 and all(type(x) is str for x in table),
            'wire:bounded-string-table')
    require(table == sorted(set(table), key=lambda x:x.encode('utf-8'))
            and len(canonical(table)) <= 65536, 'wire:unique-sorted-table')
    used, node_count, string_size = Counter(), 0, 0

    def decode(node, depth):
        nonlocal node_count, string_size
        node_count += 1
        require(depth <= 64 and node_count <= 100000, 'wire:bounded-node:' + str(node_count))
        if type(node) is not list or len(node) not in (1,2) or type(node[0]) is not int:
            raise ValueError('invalid tagged node')
        tag = node[0]
        if tag == 0:
            if len(node) != 1: raise ValueError('invalid null node')
            return None
        if len(node) != 2: raise ValueError('payload missing')
        payload = node[1]
        if tag == 1:
            if type(payload) is not bool: raise ValueError('invalid bool')
            return payload
        if tag == 2:
            if type(payload) is not int or payload.bit_length() > 13607:
                raise ValueError('invalid integer')
            return payload
        if tag == 4:
            if type(payload) is not int or not 0 <= payload < len(table):
                raise ValueError('invalid reference')
            used[payload] += 1
            payload = table[payload]
        if tag in (3,4):
            if type(payload) is not str: raise ValueError('invalid string')
            string_size += len(payload.encode('utf-8'))
            require(string_size <= 1048576, 'wire:bounded-string-expansion:' + str(node_count))
            return payload
        if tag not in (5,6) or type(payload) is not list: raise ValueError('invalid container')
        if tag == 5:
            return [decode(child, depth+1) for child in payload]
        result = {}
        for pair in payload:
            if type(pair) is not list or len(pair) != 2: raise ValueError('invalid object pair')
            key = decode(pair[0], depth+1)
            if type(key) is not str or key in result: raise ValueError('invalid object key')
            result[key] = decode(pair[1], depth+1)
        if list(result) != sorted(result): raise ValueError('noncanonical decoded object')
        return result

    result = decode(envelope['encoded_node'], 0)
    require(type(result) is dict, 'wire:root-object')
    require(set(used) == set(range(len(table))) and all(n > 1 for n in used.values()),
            'wire:all-table-members-repeated-and-used')
    expanded = canonical(result)
    require(len(expanded) <= 1048576 and type(envelope['original_canonical_bytes']) is int
            and len(expanded) == envelope['original_canonical_bytes'], 'wire:decoded-size')
    require(sha(expanded) == envelope['original_canonical_sha256'], 'wire:decoded-hash')
    counts.update(wire_nodes=node_count, wire_strings_bytes=string_size,
                  wire_dictionary_entries=len(table), wire_dictionary_bytes=len(canonical(table)))
    return result


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


def package_and_tests():
    inventory=load(W/'actual-public-inventory.json')
    require(len(inventory['files'])==inventory['explicit_named_file_count']==113,'inventory:113-explicit-public-files')
    require(len({item['path'] for item in inventory['files']})==113,'inventory:no-duplicate-paths')
    for pin in inventory['files']:read(pin['path'],pin)
    check(inventory['database_bodies_included'] is False and inventory['cas_bodies_included'] is False and
          inventory['ducklake_parquet_bodies_included'] is False and inventory['recursive_traversal'] is False,
          'inventory:no-DB-CAS-lake-body-or-recursive-scope')
    pin_declared(inventory['producer'])
    preservation=load(W/'preservation-before-package.json')
    require(preservation['checked_occurrences']==len(preservation['occurrences'])==292,'preservation:292-nondeduplicated-pins')
    require(preservation['sealed_predecessor_named_files']==239 and
            preservation['sealed_predecessor_manifest_occurrences']==1 and
            preservation['baseline_dependency_occurrences']==52,'preservation:239-W-files-plus-seal-plus52-direct-dependencies')
    for item in preservation['occurrences']:
        check(item['expected']==item['actual'] and item['unchanged'] is True,
              'preservation:declared-unchanged:' + item['group'] + ':' + str(item['ordinal']))
        read(item['expected']['path'],item['expected'])
    read(preservation['predecessor_seal']['path'],preservation['predecessor_seal'])
    package=load(W/'package-report.json')
    require(package['source_count']==len(package['files'])==4,'package:four-new-source-test-files')
    for item in package['files']:
        left=read(item['source']['path'],item['source']);right=read(item['packaged']['path'],item['packaged'])
        check(left==right,'package:exact-source-copy:' + item['relative_path'])
        check(captures[item['source']['path']]['mode']=='0o644','package:new-source-mode644:' + item['relative_path'])
        ast.parse(left,filename=item['relative_path'])
    patch=read(package['patch']['path'],package['patch'])
    check(len(patch)==86146 and patch.count(b'new file mode 100644\n')==4,
          'package:86146-byte-four-new-file-patch')
    check(package['patch_check_passed'] is True and package['patch_exact_apply_passed'] is True and
          package['original_repository_index_written'] is False and package['commits_created']==0 and package['pushes']==0,
          'package:fresh-scratch-application-no-project-publication')
    reconstructed={}
    for section in patch.split(b'diff --git ')[1:]:
        lines=section.splitlines(keepends=True)
        target=next(line[6:].strip().decode() for line in lines if line.startswith(b'+++ b/'))
        start=next(i for i,line in enumerate(lines) if line.startswith(b'@@ '))
        content=[]
        for line in lines[start+1:]:
            if line.startswith(b'+'):content.append(line[1:])
            elif line.startswith(b'\\ No newline at end of file'):content[-1]=content[-1].removesuffix(b'\n')
            else:raise ValueError('non-added new-file patch body')
        reconstructed[target]=b''.join(content)
    check(set(reconstructed)=={item['relative_path'] for item in package['files']},'package:exact-independent-patch-target-set')
    for item in package['files']:
        check(reconstructed[item['relative_path']]==read(item['source']['path']),
              'package:independent-patch-body-exact:' + item['relative_path'])
    tests=load(W/'test-final-run.json');xml=ET.fromstring(read(W/'test-final.xml'))
    cases=list(xml.iter('testcase'));identities=[(item.get('classname'),item.get('name')) for item in cases]
    check(len(cases)==len(set(identities))==tests['tests']==tests['unique_identities']==171,
          'tests:171-unique-executed-identities')
    check(not list(xml.iter('failure')) and not list(xml.iter('error')) and not list(xml.iter('skipped')) and
          tests['failures']==tests['errors']==tests['skipped']==tests['exit_code']==0,
          'tests:zero-failure-error-skip-and-exit-zero')
    check(tests['sources_before']==tests['sources_after'] and tests['all_sources_unchanged'] is True,
          'tests:all-four-source-pins-unchanged')
    pin_declared(tests['sources_before']);pin_declared(tests['sources_after'])
    counts.update(final_tests=len(cases),explicit_public_inventory_files=113,preservation_occurrences=292,
                  new_source_test_files=4,packaged_patch_bytes=len(patch))


def audit():
    summary=load(R/'summary.json');head=summary['head']
    native=load(R/'native-semantic-capsules.json');manifest=load(R/'observed-manifest.json')
    capsule=load(R/'checked-call-capsule.json');views=load(R/'code-views.json')
    intent=load(R/'intent-profile.json');query=load(R/'query.json');capacity=load(R/'capacity.json')
    view=load(R/'audit-view.json')
    packet_bytes={kind:read(R/(kind+'-packet.json')) for kind in ('expanded','view')}
    packets={kind:parse(raw,floats=False) for kind,raw in packet_bytes.items()}
    call=parse(view['checked_call_context'],floats=False)
    require(summary['qualified'] is True,'actual:selected-qualified-run02')
    for kind,packet in packets.items():
        require(canonical(packet)==packet_bytes[kind],'packet:canonical-full-model-string:' + kind)
        compare_tree(packet['head'],head,'packet:exact-current-head:' + kind)
        check(packet['audit_view_id']==view['view_id'],'packet:same-complete-audit-view-identity:' + kind)
    compare_tree(packets['expanded']['payload']['native_semantic_audit'],native,'packet:expanded-complete-native-audit')
    compare_tree(packets['expanded']['payload']['code_view_audit'],views,'packet:expanded-complete-code-view-audit')
    compare_tree(packets['view']['payload']['model_view'],view,'packet:view-exact-registered-full-model-view')
    require(packets['expanded']['payload']['checked_call_context']==view['checked_call_context'],
            'packet:entire-checked-call-context-string-unchanged')
    compare_tree(call['context']['capsule'],capsule,'packet:entire-original-checked-call-proof-capsule')
    for field in ('assumptions','checker_dependencies','coverage','residuals','expansion','source_closure','intent'):
        compare_tree(call['context']['capsule'][field],capsule[field],'proof:complete-direct-required-field:' + field)
    check(capsule['residuals'][0]['path']=='dynamic.py' and
          capsule['residuals'][0]['reason']=='outside_selected_closed_call_model','proof:dynamic-eval-residual-stays-open')
    check(capsule['intent']['mathematical_domain']=={'kind':'unbounded_mathematical_integer',
          'python_input_assumption':'exact_builtin_int_excluding_bool_and_subclasses','runtime_equivalence_proved':False},
          'proof:math-Int-and-exact-Python-int-assumptions-only')
    check(len(capsule['assumptions']['caller'])==5 and len(capsule['assumptions']['callee_compilation'])==3
          and len(capsule['assumptions']['callee_translation'])==3,'proof:all-eleven-explicit-assumptions-retained')
    for name,value in [('capsule',capsule),('native',native),('call',call),('views',views),('view',view)]:
        compare_tree(value['head'],head,'head:all-representations-exact-current-owner:' + name)
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
    require(len(blocks) == summary['native_blocks'] == native['cold_incremental']['block_count'] == 45,
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
    require(len(native['capsules']) == len(symbols) == summary['native_symbols'] == 6,
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
    check(summary['all_source_bytes_direct']==sum(map(len,source_bytes.values()))==195, 'view:195-original-source-bytes-direct')
    identity(view,'view_id','view:entire-direct-facts-reference-directory')
    retained=view['native_view']['retained_fields']
    expected={key:value for key,value in native.items() if key not in
              {'schema','capsule_set_id','repository_state','blocks','artifact_facts'}}
    compare_tree(retained,expected,'view:all-and-only-complete-direct-native-fields')
    for field in ('capsules','semantic_links','environment_bindings','analysis_limitations',
                  'producer','source_scope','native_root','coverage','snapshot','units'):
        compare_tree(retained[field],native[field],'view:every-review-required-native-fact-direct:' + field)
    require(len(retained['capsules'])==6 and len(view['original_sources'])==3,'view:all-six-symbols-and-three-originals-direct')
    for original in view['original_sources']:
        path=original['path'];raw=original['text'].encode()
        require(raw==source_bytes[path] and len(raw)==original['bytes'] and sha(raw)==original['sha256']
                and cid(raw,85)==original['source_cid'],'view:exact-direct-original-bytes-and-CID:' + path)
        code_view=next(item for item in views['views'] if item['path']==path)
        compare_tree(original['original_span'],code_view['source_handle']['original_span'],
                     'view:corrected-physical-LF-original-span:' + path)
        compare_tree(original['symbol_expansion_handles'],[item['original_source_expansion'] for item in native['capsules']
            if item['original_source_expansion']['path']==path],'view:all-original-symbol-source-span-handles:' + path)
    require(len(native['artifact_facts'])==1 and len(state['artifacts'])==1,'view:exactly-one-snapshot-artifact')
    artifact=state['artifacts'][0]
    require(artifact['artifact_id']=='artifact:snapshot-evidence' and artifact['kind']=='snapshot-evidence'
            and artifact['path']=='@snapshot-evidence' and artifact['confidence']=='exact'
            and artifact['source_cid']==head['snapshot_cid'] and artifact['metadata']=={
                'snapshot':snapshot,'acquisition':snapshot['mode'],'exclusions':snapshot['exclusions']},
            'view:only-exact-duplicate-snapshot-artifact-deferred')
    registry,resolve=independent_registry(native,view)
    expected_measurements={name:{field:record[field] for field in ('bytes','sha256','tokens')}
                           for name,record in summary['packets'].items()}
    for exchange in summary['expansion_exchanges']:
        kind=exchange['kind'];host=load(R/('expansion-'+kind+'-host.json'))
        request_path=R/('expansion-'+kind+'-request.json');response_path=R/('expansion-'+kind+'-response.json')
        request_raw,response_raw=read(request_path),read(response_path)
        request,response=parse(request_raw,floats=False),parse(response_raw,floats=False)
        require(canonical(request)==request_raw and canonical(response)==response_raw,
                'expansion:whole-request-response-canonical-model-strings:' + kind)
        require(set(request)=={'tool','arguments'} and request['tool']=='expand_semantic_audit'
                and set(response)=={'tool','result'} and response['tool']=='expand_semantic_audit',
                'expansion:closed-hypothetical-model-exchange:' + kind)
        compare_tree(request['arguments'],exchange['reference'],'expansion:registered-current-request:' + kind)
        compare_tree(response['result'],host['expansion'],'expansion:entire-host-payload-delivered-counterfactually:' + kind)
        expansion=host['expansion'];raw=resolve(request['arguments'])
        require(expansion['canonical_json'].encode()==raw and expansion['sha256']==sha(raw)
                and expansion['bytes']==len(raw) and expansion['object_cid']==cid(raw)
                and expansion['reference']==request['arguments'] and expansion['view_id']==view['view_id']
                and expansion['partial_response'] is False and expansion['original_registered_bytes'] is True,
                'expansion:exact-current-native-original-payload-no-partial-response:' + kind)
        identity(host,'result_cid','expansion:outer-current-owner-receipt:' + kind)
        compare_tree(host['head'],head,'expansion:full-current-owner-head:' + kind)
        cold=host['cold_proof_validation']
        check(cold['data_validated'] is True and cold['checker_reinvoked'] is False and
              cold['head']==head and cold['native_callee_cold_validation_passed'] is True,
              'expansion:actual-cold-proof-owner-readback-no-prover:' + kind)
        compare_tree(host['context_validation'],load(R/'view-preview.json')['context_validation'],
                     'expansion:same-entire-registered-context-validation:' + kind)
        pin_declared(host['producer']);ceiling(host,'expansion:' + kind)
        packet_bytes[kind+'-request']=request_raw;packet_bytes[kind+'-response']=response_raw
        expected_measurements[kind+'-request']=exchange['request']
        expected_measurements[kind+'-response']=exchange['response']
        check(exchange['actual_provider_calls']==0 and exchange['counterfactual_exchange_only'] is True,
              'expansion:no-provider-delivery-claim:' + kind)
    require([item['kind'] for item in summary['expansion_exchanges']]==['repository_state','native_block','full_audit'],
            'expansion:three-actual-current-owner-counterfactual-cost-scenarios')
    tokenize_packets(packet_bytes,{'measures':expected_measurements})
    measurements=counts['independent_token_measurements']
    saving=measurements['expanded']['tokens']-measurements['view']['tokens']
    check(saving==summary['offline_initial_input_token_reduction']==13865 and
          10000*saving//measurements['expanded']['tokens']==summary['offline_initial_reduction_basis_points']==2417,
          'tokens:exact-initial-13865-token-2417-basis-point-reduction')
    for exchange in summary['expansion_exchanges']:
        kind=exchange['kind'];total=measurements['view']['tokens']+measurements[kind+'-request']['tokens']+measurements[kind+'-response']['tokens']
        check(total==exchange['initial_view_plus_exchange_tokens'],'tokens:whole-request-response-plus-initial-view:' + kind)
        if kind=='full_audit':check(total>measurements['expanded']['tokens'],'tokens:full-audit-expansion-erases-initial-saving')
    check(summary['provider_token_savings_measured'] is False and summary['cumulative_task_token_savings_measured'] is False
          and summary['selected_representation']=='view','tokens:offline-view-selection-no-provider-or-task-budget-claim')
    previews={name:load(R/(name+'-preview.json')) for name in ('expanded','view')};final=load(R/'final-current-preview.json')
    expected_ids=['task:call-review:revalidate_conditional_model','task:call-review:review_runtime_assumptions',
                  'task:call-review:review_uncovered_source']
    a,b=(previews[name]['native_review'] for name in ('expanded','view'))
    compare_tree(previews['expanded']['context_validation'],previews['view']['context_validation'],
                 'paired:entire-normalized-context-validation')
    compare_tree(a['request'],b['request'],'paired:entire-native-request')
    compare_tree(a['native_preview']['input_snapshot'],b['native_preview']['input_snapshot'],
                 'paired:entire-native-material-snapshot-and-twenty-field-binding')
    compare_tree(a['native_planning_material'],b['native_planning_material'],'paired:entire-native-planning-material')
    compare_tree(a['review_projection'],b['review_projection'],'paired:entire-three-task-review-projection')
    compare_tree(previews['expanded']['pure_material_basis_cid'],previews['view']['pure_material_basis_cid'],
                 'paired:unchanged-W-pure-native-material-basis-no-capacity-cycle')
    exclusions=['input_digest','plan_id','deterministic_replay.input_digest','deterministic_replay.plan_id',
                'replay_request.current_time_ms']
    check(summary['normalization_exclusions']==exclusions,'paired:only-five-declared-clock-identity-normalizations')
    def normalized(plan):
        result=deepcopy(plan)
        for key in ('input_digest','plan_id'):del result[key];del result['deterministic_replay'][key]
        del result['replay_request']['current_time_ms']
        return result
    compare_tree(normalized(a['native_parallel_plan']),normalized(b['native_parallel_plan']),
                 'paired:full-native-forecast-except-exact-five-clock-identity-fields')
    check(a['native_parallel_plan']['plan_id']!=b['native_parallel_plan']['plan_id'] and
          summary['complete_parallel_plan_ids_equal'] is False,'paired:complete-plan-IDs-honestly-differ')
    for field in summary['stable_native_identity_fields']:
        check(a['native_preview']['preview'][field]==b['native_preview']['preview'][field],
              'paired:stable-genuine-native-stage-identity:' + field)
    for name,value in [*previews.items(),('final-current',final)]:
        identity(value,'result_cid','preview:outer-final-current-result:' + name)
        compare_tree(value['context_validation'],previews['view']['context_validation'],
                     'preview:complete-same-context-meaning:' + name)
        check(value['pure_material_basis_cid']==a['pre_capacity_binding']['material_basis_cid'],
              'preview:exact-original-native-material-basis:' + name)
        native_review(value['native_review'],name,head,native,capacity,expected_ids)
        pin_declared(value['producer']);ceiling(value,'outer-preview:' + name)
    controls=summary['controls']
    require(len(controls)==17 and len({item['name'] for item in controls})==17 and
            all(item['rejected'] is True and item['reason'] for item in controls),'controls:17-distinct-actual-live-rejections')
    expected_controls=['serialized-capacity-cannot-create-current-view',
        'rehashed-view-cannot-drop-capsules','rehashed-view-cannot-drop-semantic_links',
        'rehashed-view-cannot-drop-analysis_limitations','rehashed-view-cannot-drop-original_sources',
        'rehashed-view-cannot-drop-checked_call_assumptions','rehashed-view-cannot-drop-checked_call_residuals',
        'rehashed-view-cannot-drop-execution_width','reference-cannot-request-arbitrary-path',
        'reference-cannot-execute-sql','same-snapshot-wrong-generation',
        'same-byte-source-replaced-on-first-capacity-callback',
        'same-byte-proof-replaced-during-expansion-policy-observer',
        'input-mutation-after-last-preview-capacity-callback',
        'input-mutation-after-last-expansion-capacity-callback',
        'released-capacity-cannot-replay-view','released-capacity-cannot-expand-live-reference']
    compare_tree([item['name'] for item in controls],expected_controls,'controls:exact17-required-live-regressions')
    for name,reason in [('input-mutation-after-last-preview-capacity-callback','audit inputs changed after final capacity callback'),
                        ('input-mutation-after-last-expansion-capacity-callback','expansion inputs changed after final capacity callback')]:
        require(any(item['name']==name and item['reason']==reason for item in controls),
                'controls:closing-order-mutable-input-regression:' + name)
    require(summary['resources_after']['active_lease_count']==summary['resources_after']['waiting_request_count']==0 and
            summary['resources_after']['allocated_child_process_slots']==0,'resources:no-active-leases-waiters-after-release')
    check(summary['held_resources_before_release']['active_lease_count']==1 and
          summary['held_resources_before_release']['allocated']=={'cpu_slots':1,'memory_mb':64} and
          summary['held_resources_before_release']['allocated_child_process_slots']==1,
          'resources:one-held-native-forecast-quota-shared-by-paired-arms')
    for name,value in [('summary',summary),('view',view),('native',native),('capsule',capsule),
                       ('expanded-packet',packets['expanded']),('view-packet',packets['view'])]:ceiling(value,name)
    pin_declared(capsule['expansion']);pin_declared(capsule['producer']);pin_declared(query['producer'])
    check(query['sql_executed'] is True and query['quack_executed'] is False and query['row_count']==4,
          'metadata:actual-four-family-read-only-DuckDB-selection')
    qualification=load(A/'qualification-summary.json')
    check(qualification['rows']==49 and len(qualification['families'])==20 and
          sum(qualification['families'].values())==49,'metadata:49-rows-20-families')
    model=load(A/'model/result.json')
    check(model['head']==head and model['model_status']=='model_proved' and
          model['actual_caller_compiler_returned'] is True,'proof:actual-fresh-qualified-caller-model')
    processes=load(A/'model/callee/native-lowering/lean_process.json');caller_process=load(A/'model/process.json')
    for name,process in [*processes.items(),('caller',caller_process)]:
        check(process['returncode']==0 and process['termination_reason']=='completed' and process['timed_out'] is False
              and process['resource_exhausted'] is False and '/leanprover--lean4---v4.34.1/bin/lean' in process['command'][0],
              'proof:three-successful-bounded-pinned-Lean-process-receipts:' + name)
    check(len(processes)+1==summary['fresh_qualification_lean_processes']==3 and
          summary['checker_invocations_during_planning_and_expansion']==0,'proof:three-fresh-qualification-processes-no-cold-checker')
    package_and_tests()
    source=read(C/'benchmarks/agent_supervisor/container_coding/terminal_semantic_audit_review.py').decode()
    functions={node.name:node for node in ast.parse(source).body if isinstance(node,ast.FunctionDef)}
    for name in ('preview_current_semantic_audit_review','resolve_current_semantic_audit_reference'):
        body=ast.get_source_segment(source,functions[name])
        require(body.index('with forecast.metadata._producer')<body.index('forecast.revisions._capture')<
                body.index('checked._retain_model_artifacts')<body.index('capacity_control.require_current'),
                'source:original-source-proof-producer-witnesses-before-first-capacity-callback:' + name)
        require(body.rindex('original == input_wire()')>body.rindex('capacity_control.public_dict()') and
                body.rindex('original == input_wire()')>body.rindex('index.current('),
                'source:complete-inert-input-check-after-final-capacity-and-current-catalog-callback:' + name)
        require('== value["result_cid"]' in body and body.rindex('== value["result_cid"]')>body.index('value["result_cid"] ='),
                'source:outer-result-CID-rechecked-after-assembly:' + name)
    body=ast.get_source_segment(source,functions['preview_current_semantic_audit_review'])
    require('== review["result_cid"]' in body and 'semantic.preview_current_semantic_call_review(' in body,
            'source:unchanged-W-native-service-and-nested-result-integrity')
    pure=read(C/'benchmarks/agent_supervisor/container_coding/terminal_semantic_audit_view.py').decode()
    require('"original_span": dict(original_spans[path])' in pure and
            'item["source_handle"]["original_span"]' in pure,'source:Unicode-coordinate-fix-reuses-native-physical-span')
    require('immutable_bundle_capsule_reader(bundle, root_cid=bundle.root.root_cid)' in pure and
            'native.validate_native_semantic_capsule_set(' in pure,'source:genuine-immutable-native-reader-and-complete-replay')
    load(W/'boundary-review-criteria.json')
    reviewer_history=load(W/'independent-review-development-history.json')
    check(len(reviewer_history['excluded_attempts'])==2 and
          all(item['qualified'] is False and item['selected_final_audit'] is False
              for item in reviewer_history['excluded_attempts']),
          'reviewer-history:two-local-audit-adaptations-retained-and-excluded')
    ast.parse(read(W/'run_current.py'),filename='run_current.py')
    hypothetical_total=measurements['view']['tokens']+sum(
        measurements[item['kind']+'-request']['tokens']+measurements[item['kind']+'-response']['tokens']
        for item in summary['expansion_exchanges'])
    for name in ('qualification-report.json','improvement-status.json','development-history.json'):
        path=W/name
        if path.exists():
            report=load(path);ceiling(report,'final-report:' + name)
            if name=='development-history.json':
                pin_declared(report)
                check(report['selected_final_live_run']=='preview-run-02' and
                      report['cached_skips_used_for_qualification'] is False,
                      'history:corrected-final-run-and-executed-tests-selected')
            if name=='qualification-report.json':
                check(report['offline_initial_expanded_tokens']==measurements['expanded']['tokens'] and
                      report['offline_initial_view_tokens']==measurements['view']['tokens'] and
                      report['offline_initial_token_reduction']==saving and
                      report['offline_initial_reduction_basis_points']==2417 and
                      report['initial_view_plus_all_three_exchanges_tokens']==hypothetical_total==106184,
                      'qualification:all-initial-and-hypothetical-expansion-costs-recounted')
                check(report['unique_tests']==171 and report['live_negative_controls']==17 and
                      report['registered_exact_expansion_references']==50 and
                      report['current_owner_expansion_groups_qualified']==3 and
                      report['all_original_source_bytes_direct']==195 and
                      report['native_symbols']==6 and report['native_blocks']==45,
                      'qualification:exact-final-counts-and-direct-source-facts')
                check(report['native_admission_passed'] is False and
                      report['remaining_admission_blockers']==['ir_admission_materials_absent'] and
                      report['provider_token_savings_measured'] is False and
                      report['cumulative_task_token_savings_measured'] is False,
                      'qualification:admission-and-provider-task-cost-ceilings-unchanged')
        else:counts.setdefault('final_reports_pending',[]).append(name)
    counts.update(native_capsules=6,native_blocks=45,native_original_blocks=39,supplemental_projection_blocks=6,
                  actual_live_controls=17,original_source_bytes_direct=195,initial_offline_token_reduction=saving,
                  initial_reduction_basis_points=2417,actual_current_owner_expansion_groups=3,
                  provider_or_cumulative_task_token_savings_measured=False,
                  native_governor_or_production_ContextPack_qualified=False,
                  hypothetical_initial_view_plus_all_three_exchanges_tokens=hypothetical_total)

def finish(path):
    for name,value in captures.items():
        current=os.fstat(value['fd'])
        check(stamp(current)==value['stamp']==stamp(Path(name).lstat()),'closing-custody:' + name)
        os.lseek(value['fd'],0,os.SEEK_SET)
        digest=hashlib.sha256()
        while chunk:=os.read(value['fd'],1024*1024):digest.update(chunk)
        check(digest.hexdigest()==value['pin']['sha256'],'closing-retained-FD-content:' + name)
    report={'schema':'terminal-semantic-audit-view-independent-review@1',
        'qualified':not failures and not counts.get('final_reports_pending'),
        'passed':not failures and not counts.get('final_reports_pending'),
        'check_count':len(checks), 'passed_checks':sum(x['passed'] for x in checks),
        'failed_checks':len(failures),'failed':len(failures),
        'blockers':failures,'checks':checks,'counts':counts,
        'inputs':[captures[name]['pin'] for name in sorted(captures)],
        'read_pins':[captures[name]['pin'] for name in sorted(captures)],
        'input_custody':'retained nofollow regular single-link FD/stat/SHA before and after; named files only',
        'read_only_execution':{'target_or_native_implementation_imports':0,
            'project_service_calls':0,'database_bodies_opened':False,'CAS_bodies_opened':False,
            'DuckLake_parquet_bodies_opened':False,'recursive_traversal':False,'tests_run':0,
            'prover_invocations':0,'provider_calls':0,'training_steps':0,'source_body_executed':False,
            'source_or_sealed_files_edited':False,'network_fetches':0,'subprocesses':0,
            'only_nonstdlib_dependency':'pinned tiktoken0.13.0 constructed directly from retained local BPE bytes'},
        'limits':{'runtime_equivalence_proved':False,'source_origin_proved':False,
            'training_convergence_proved':False,'full_task_satisfaction':False,
            'loaded_code_attested':False,'transitive_import_closure_attested':False,
            'native_runtime_reexecution_performed':False,'Lean_kernel_reinvoked':False,
            'producer_receipt_origin_independently_authenticated':False,
            'native_parallel_recompiled_by_reviewer':False,
            'interpretation':'Review rechecks public identities/joins/custody and own typed reference reconstruction, audit decoding and token counts. Genuine native readbacks, compiler replays, controls and process outcomes are attributed to pinned application evidence; no origin authority is conferred.'}}
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
    with os.fdopen(fd,'wb') as stream:stream.write(json.dumps(report,sort_keys=True,indent=2).encode()+b'\n')
    for value in captures.values():os.close(value['fd'])
    print(json.dumps({'report':str(path),'qualified':report['qualified'],'passed':report['passed_checks'],
        'failed':report['failed'],'unique_inputs':len(report['inputs']),'counts':counts,
        'first_failures':failures[:8]}))
    return 0 if report['qualified'] else 1


if __name__=='__main__':
    report_path=W/(sys.argv[1] if len(sys.argv)>1 else 'independent-review.json')
    require(report_path.parent==W,'review:report-only-in-owned-stage-directory')
    read(Path(__file__).absolute())
    try:
        audit()
    except Exception as exc:
        check(False,'review:unhandled-audit-error',{'type':type(exc).__name__,
            'message':str(exc),'traceback':traceback.format_exc()})
    sys.exit(finish(report_path))
