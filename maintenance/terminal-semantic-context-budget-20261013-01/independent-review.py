"""Independent, named-file Stage Y evidence audit.

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

W = Path('/home/barberb/lift_coding/maintenance/terminal-semantic-context-budget-20261013-01')
PREVIOUS = Path('/home/barberb/lift_coding/maintenance/terminal-semantic-audit-view-20261013-01')
R = W / 'preview-run-02'
A = W / 'actual-public-budget-01'
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
        'production_context_pack_qualified', 'context_sufficiency_proved',
        'provider_usage_measured', 'provider_output_measured', 'serialized_live_authority',
        'rendered_input_origin_verified', 'native_worker_observer_used',
        'full_supervisor_entrypoint_used', 'global_task_budget_enforced', 'durable_budget_resume_supported'}
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
    require(preservation['checked_occurrences']==len(preservation['occurrences'])==296,'preservation:296-nondeduplicated-pins')
    require(preservation['sealed_predecessor_named_files']==237 and
            preservation['sealed_predecessor_manifest_occurrences']==1 and
            preservation['baseline_dependency_occurrences']==58,'preservation:237-X-files-plus-seal-plus58-direct-dependencies')
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
    check(len(patch)==95365 and patch.count(b'new file mode 100644\n')==4,
          'package:95365-byte-four-new-file-patch')
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
    check(len(cases)==len(set(identities))==tests['tests']==tests['unique_identities']==162,
          'tests:162-unique-executed-identities')
    check(not list(xml.iter('failure')) and not list(xml.iter('error')) and not list(xml.iter('skipped')) and
          tests['failures']==tests['errors']==tests['skipped']==tests['exit_code']==0,
          'tests:zero-failure-error-skip-and-exit-zero')
    check(tests['sources_before']==tests['sources_after'] and tests['all_sources_unchanged'] is True,
          'tests:all-four-source-pins-unchanged')
    pin_declared(tests['sources_before']);pin_declared(tests['sources_after'])
    counts.update(final_tests=len(cases),explicit_public_inventory_files=113,preservation_occurrences=296,
                  new_source_test_files=4,packaged_patch_bytes=len(patch))


def literal_assignment(source, name):
    for node in ast.parse(source).body:
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in node.targets):
            return ast.literal_eval(node.value)
    raise ValueError('missing literal source assignment: '+name)


def replay_ledger(snapshot, *, instruction, encoding, name):
    """Own typed event, token, full-history and cumulative-budget replay."""
    identity(snapshot,'snapshot_cid','ledger:whole-snapshot:' + name)
    binding,policy=snapshot['binding'],snapshot['policy']
    require(snapshot['binding_cid']==structured(binding),'ledger:full-binding-CID:' + name)
    require(snapshot['policy_cid']==structured(policy),'ledger:complete-policy-CID:' + name)
    require(type(snapshot['closed']) is bool,'ledger:exact-closed-flag:' + name)
    policy_names={'max_rendered_input_tokens','max_new_content_tokens','max_rendered_input_bytes',
        'max_new_content_bytes','max_model_calls','max_expansion_calls','max_retry_calls','max_events','max_payload_bytes'}
    require(set(policy)==policy_names|{'schema'} and policy['schema']=='terminal-semantic-context-budget-policy@1',
            'ledger:closed-policy-shape:' + name)
    for key in policy_names:
        require(type(policy[key]) is int and 0<=policy[key]<=16777216,'ledger:bounded-exact-policy:' + name + ':' + key)
    require(type(snapshot['records']) is list and len(snapshot['records'])<=64,'ledger:bounded-complete-record-list:' + name)
    tokenizer={'library':'tiktoken','version':'0.13.0','encoding':'o200k_base',
        'vocabulary_sha256':'a6557bbd3ceb299981ac87fd86a51fa8f0e9505be18ed608c5ada94bdfd0f63f',
        'bpe_sha256':'446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d',
        'offline':True,'fallback':False}
    compare_tree(snapshot['tokenizer'],tokenizer,'ledger:exact-tokenizer-contract:' + name)
    total_keys=('rendered_input_tokens','new_content_tokens','rendered_input_bytes','new_content_bytes',
                'model_calls','expansion_calls','retry_calls','events')
    totals=dict.fromkeys(total_keys,0);seen=[];previous=None;committed=False
    prior=[]
    for position,record in enumerate(snapshot['records'],1):
        label=name+':'+str(position)
        require(type(record) is dict and set(record)=={'event','status'} and
                record['status'] in {'reserved','committed','aborted'},'ledger:closed-status-record:' + label)
        require(record['status']!='reserved' or position==len(snapshot['records']),'ledger:reserved-only-at-tail:' + label)
        event=record['event']
        fields={'schema','event_id','kind','sequence','binding_cid','previous_event_cid','history_event_ids',
                'retry_of','new_content','rendered_input','expansion_request','expansion_response','tokenizer','event_cid'}
        require(type(event) is dict and set(event)==fields and event['schema']=='terminal-semantic-context-budget-event@1',
                'ledger:closed-complete-event:' + label)
        require(type(event['sequence']) is int and event['sequence']==position and
                event['binding_cid']==snapshot['binding_cid'] and event['history_event_ids']==seen
                and event['previous_event_cid']==previous,'ledger:exact-order-binding-and-entire-history-chain:' + label)
        require(type(event['event_id']) is str and event['event_id'] not in seen and
                event['kind'] in {'initial','expansion','retry'},'ledger:unique-closed-event-identity:' + label)
        require((position==1 and event['kind']=='initial') or (position>1 and event['kind']!='initial'),
                'ledger:initial-context-cannot-reset-spending:' + label)
        require((event['kind']=='retry' and event['retry_of'] in seen) or
                (event['kind']!='retry' and event['retry_of'] is None),'ledger:prior-charged-retry-target:' + label)
        identity(event,'event_cid','ledger:complete-event-identity:' + label)
        compare_tree(event['tokenizer'],tokenizer,'ledger:event-tokenizer:' + label)
        for field in ('new_content','rendered_input','expansion_request','expansion_response'):
            value=event[field]
            if value is None:
                require(field in {'expansion_request','expansion_response'} and event['kind']!='expansion',
                        'ledger:only-nonexpansion-components-absent:' + label + ':' + field)
                continue
            require(type(value) is dict and set(value)=={'text','bytes','sha256','tokens'} and type(value['text']) is str,
                    'ledger:exact-whole-text-measurement:' + label + ':' + field)
            raw=value['text'].encode('utf-8');tokens=encoding.encode(value['text'],allowed_special=set(),disallowed_special=())
            require(encoding.decode(tokens)==value['text'] and type(value['bytes']) is int
                    and type(value['tokens']) is int and len(raw)==value['bytes'] and sha(raw)==value['sha256']
                    and len(tokens)==value['tokens'] and len(raw)<=policy['max_payload_bytes'],
                    'ledger:independent-complete-token-byte-hash-measurement:' + label + ':' + field)
        current={'event_id':event['event_id'],'kind':event['kind'],'content':event['new_content']['text']}
        transcript={'schema':'terminal-semantic-native-planning-transcript@1','purpose':'conditional_review',
            'binding':binding,'instruction':instruction,'events':[*prior,current]}
        require(canonical(transcript)==event['rendered_input']['text'].encode(),
                'ledger:independent-exact-native-planning-transcript-with-all-charged-attempts:' + label)
        require(len(canonical(transcript))<=256000,'ledger:native-planning-input-byte-bound:' + label)
        if event['kind']=='expansion':
            require(committed,'ledger:expansion-after-committed-context:' + label)
            content=parse(event['new_content']['text'],floats=False)
            require(set(content)=={'expansion_request','expansion_response','turn_instruction'} and
                    canonical(content['expansion_request']).decode()==event['expansion_request']['text'] and
                    canonical(content['expansion_response']).decode()==event['expansion_response']['text'],
                    'ledger:whole-expansion-message-components-counted-once:' + label)
        for field in ('new_content','rendered_input'):
            for metric in ('tokens','bytes'):totals[field+'_'+metric]+=event[field][metric]
        totals['model_calls']+=1;totals['expansion_calls']+=event['kind']=='expansion'
        totals['retry_calls']+=event['kind']=='retry';totals['events']+=1
        for key in total_keys:
            require(totals[key]<=policy['max_'+key],'ledger:exact-cumulative-hard-dimension:' + label + ':' + key)
        seen.append(event['event_id']);previous=event['event_cid'];committed=committed or record['status']=='committed'
        prior.append({**current,'status':record['status']})
    compare_tree(snapshot['totals'],totals,'ledger:all-eight-exact-nonrefunding-cumulative-totals:' + name)
    require(snapshot['provider_calls']==0 and snapshot['provider_output_tokens'] is None and
            snapshot['provider_usage_measured'] is False and snapshot['provider_output_measured'] is False
            and snapshot['serialized_live_authority'] is False and snapshot['rendered_input_origin_verified'] is False
            and snapshot['history_inclusion_verified'] is False,'ledger:serialized-data-and-provider-usage-ceilings:' + name)
    ceiling(snapshot,'ledger:' + name)
    return totals


def audit():
    summary=load(R/'summary.json');head=summary['head']
    native=load(R/'native-semantic-capsules.json');manifest=load(R/'observed-manifest.json')
    capsule=load(R/'checked-call-capsule.json');views=load(R/'code-views.json')
    intent=load(R/'intent-profile.json');query=load(R/'query.json');capacity=load(R/'capacity.json')
    view=load(R/'audit-view.json');call=parse(view['checked_call_context'],floats=False)
    require(summary['qualified'] is True,'actual:selected-qualified-Y-run02')
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
    instruction=literal_assignment(read(C/'benchmarks/agent_supervisor/container_coding/terminal_semantic_budget_delivery.py').decode(),'INSTRUCTION')
    packet_files={'expanded':'expanded-packet.json','view':'view-packet.json','failure':'failure-view-packet.json',
                  'proof':'custody-view-packet.json','late':'late-view-packet.json'}
    view_files={'main':'audit-view.json','failure':'failure-audit-view.json','custody':'custody-audit-view.json','late':'late-audit-view.json'}
    all_views={name:load(R/file) for name,file in view_files.items()}
    all_registries={}
    for name,item in all_views.items():
        identity(item,'view_id','view:exact-current-scope-view:' + name)
        retained={key:value for key,value in native.items() if key not in
                  {'schema','capsule_set_id','repository_state','blocks','artifact_facts'}}
        compare_tree(item['native_view']['retained_fields'],retained,'view:all-native-facts-links-bindings-caveats-direct:' + name)
        require(sum(x['bytes'] for x in item['original_sources'])==195,'view:all-original-source-bytes-direct:' + name)
        for original in item['original_sources']:
            require(original['text'].encode()==source_bytes[original['path']],
                    'view:exact-original-source-text:' + name + ':' + original['path'])
        local_call=parse(item['checked_call_context'],floats=False)
        compare_tree(local_call['context']['capsule'],capsule,'view:entire-checked-proof-scope-unchanged:' + name)
        all_registries[name]=independent_registry(native,item)
    snapshots={name:load(R/file) for name,file in {'expanded':'expanded-trace.json','view':'view-trace.json',
        'failure':'failure-trace.json','proof':'proof-mutation-failure-trace.json','late':'late-input-failure-trace.json'}.items()}
    measured,expected_measures={},{}
    for trace,snapshot in snapshots.items():
        for position,record in enumerate(snapshot['records'],1):
            for field in ('new_content','rendered_input','expansion_request','expansion_response'):
                value=record['event'][field]
                if value is not None:
                    key=trace+':'+str(position)+':'+field
                    measured[key]=value['text'].encode()
                    expected_measures[key]={name:value[name] for name in ('bytes','sha256','tokens')}
    encoding=tokenize_packets(measured,{'measures':expected_measures})
    replayed={}
    for name,snapshot in snapshots.items():
        replayed[name]=replay_ledger(snapshot,instruction=instruction,encoding=encoding,name=name)
        require(snapshot['closed'] is True,'ledger:each-explicit-local-trace-closed:' + name)
        packet=read(R/packet_files[name]).decode()
        require(snapshot['records'][0]['event']['new_content']['text']==packet,
                'ledger:original-initial-packet-never-replaced:' + name)
        packet_value=parse(packet,floats=False)
        require(packet_value['head']==head and packet_value['audit_view_id']==snapshot['binding']['view_id'],
                'ledger:initial-packet-complete-head-and-view-binding:' + name)
        scope='main' if name in {'expanded','view'} else 'custody' if name=='proof' else name
        scope_view=all_views[scope]
        expected_binding={'schema':'terminal-semantic-context-budget-binding@1','head':head,
            'view_id':scope_view['view_id'],'reference_basis_cid':scope_view['expansion_directory']['reference_basis_cid'],
            'native_root_cid':native['native_root']['root_cid'],'capsule_set_id':native['capsule_set_id'],
            'state_cid':native['repository_state']['state_cid']}
        compare_tree(snapshot['binding'],expected_binding,'ledger:exact-current-source-proof-audit-scope-binding:' + name)
        compare_tree(snapshot['policy'],summary['budget_policy'],'ledger:shared-policy-in-separate-counterfactual-traces:' + name)
    require(snapshots['expanded']['binding']==snapshots['view']['binding']==summary['selected_budget_binding'],
            'ledger:paired-main-arms-share-complete-head-root-basis-and-capacity-binding')
    for name in ('expanded','view'):
        require(summary['traces'][name]['snapshot_cid']==snapshots[name]['snapshot_cid'] and
                summary['traces'][name]['totals']==replayed[name], 'ledger:exact-selected-summary-totals:' + name)
    require(replayed['expanded']['rendered_input_tokens']==70977 and replayed['expanded']['new_content_tokens']==57379,
            'tokens:expanded-initial-complete-render70977-versus-new57379')
    require(snapshots['view']['records'][0]['event']['rendered_input']['tokens']==47215 and
            snapshots['view']['records'][0]['event']['new_content']['tokens']==43189 and
            replayed['view']['rendered_input_tokens']==95678 and replayed['view']['new_content_tokens']==44374,
            'tokens:view-initial47215-plus-expansion-entire-history95678-versus-new44374')
    require(replayed['view']['rendered_input_tokens']>2*replayed['view']['new_content_tokens'] and
            all(value['totals']['model_calls']==len(value['records']) for value in snapshots.values()),
            'tokens:whole-repeated-input-not-unique-context-or-provider-call-count')
    require([x['status'] for x in snapshots['failure']['records']]==['aborted','committed'] and
            snapshots['proof']['records'][0]['status']=='aborted' and snapshots['late']['records'][0]['status']=='committed',
            'ledger:failed-observer-and-proof-abort-retain-cost-late-publication-refusal-keeps-committed-cost')
    successes={'expanded-initial-delivery.json':('expanded',0),'view-initial-delivery.json':('view',0),
               'view-block-delivery.json':('view',1),'failed-retry-delivery.json':('failure',1)}
    for file,(trace,position) in successes.items():
        exported=load(R/file);event=exported['event'];receipt=exported['receipt'];snap=exported['budget_snapshot']
        compare_tree(event,snapshots[trace]['records'][position]['event'],'delivery:exact-charged-ledger-event:' + file)
        compare_tree(snap['records'],snapshots[trace]['records'][:position+1],'delivery:complete-original-charged-prefix:' + file)
        replay_ledger(snap,instruction=instruction,encoding=encoding,name=file)
        identity(receipt,'result_cid','delivery:outer-final-receipt:' + file)
        require(receipt['event_cid']==event['event_cid'] and receipt['budget_snapshot_cid']==snap['snapshot_cid']
                and receipt['preparation_cid']==structured({'event':event,'materialization':receipt['materialization']}),
                'delivery:exact-event-snapshot-and-preparation-joins:' + file)
        material=receipt['materialization']
        require(material['native_planning_renderer_used'] is True and material['history_inclusion_verified'] is True
                and material['purpose']=='planning' and material['transcript_sha256']==event['rendered_input']['sha256']
                and material['native_worker_observer_used'] is False and material['full_supervisor_entrypoint_used'] is False,
                'delivery:actual-narrow-native-planning-renderer-scope:' + file)
        cold=receipt['cold_proof_validation']
        require(cold['data_validated'] is True and cold['checker_reinvoked'] is False and cold['head']==head,
                'delivery:actual-current-cold-proof-custody-no-prover:' + file)
        require(receipt['local_observer_called'] is True and receipt['provider_calls']==0
                and receipt['provider_output_tokens'] is None,'delivery:local-observer-only-unknown-provider-output:' + file)
        if receipt['expansion_receipt'] is not None:
            current=receipt['expansion_receipt'];identity(current,'result_cid','delivery:actual-current-native-block-expansion')
            response=parse(event['expansion_response']['text'],floats=False)
            compare_tree(response['result'],current['expansion'],'delivery:entire-current-expansion-equals-reserved-response')
            reference=response['result']['reference'];raw=all_registries['main'][1](reference)
            require(current['expansion']['canonical_json'].encode()==raw and reference['kind']=='native_block',
                    'delivery:actual-current-native-block-exact-independent-reference-bytes')
            pin_declared(current['producer'])
        pin_declared(receipt['producer']);ceiling(receipt,'delivery:' + file)
    expected_controls=['expanded-retry-over-cumulative-budget-before-observer',
        'view-retry-over-cumulative-budget-before-observer','view-state-over-cumulative-budget-before-current-expansion',
        'full-audit-expansion-rejected-before-current-expansion','failed-observer-cost-retained',
        'serialized-budget-owner-refused','closed-budget-owner-refused','wrong-complete-head-refused',
        'same-byte-source-replaced-on-native-renderer','same-byte-proof-replaced-on-local-observer',
        'same-byte-source-replaced-on-first-capacity-callback',
        'input-mutation-after-final-scope-capacity-callback-refused','released-capacity-refused']
    require([x['name'] for x in summary['controls']]==expected_controls and
            all(x['rejected'] is True and x['reason'] for x in summary['controls']), 'controls:all13-exact-live-negative-controls')
    for number,control in enumerate(summary['controls'],1):compare_tree(load(R/('control-%02d.json'%number)),control,
                                                                     'controls:separately-retained-rejection:' + str(number))
    require(summary['actual_current_expansion_calls']==['native_block'] and len(summary['local_observer_calls'])==5,
            'callbacks:five-normal-probes-one-current-expansion-plus-two-injected-fault-callbacks')
    require(sum(len(value['records']) for value in snapshots.values())==7,
            'callbacks:seven-charged-local-attempts-never-seven-provider-calls')
    # Derive the two denied retries independently; every previously charged
    # attempt remains in the complete proposed next native input.
    denied={}
    for name,target in [('expanded','expanded.initial'),('view','view.block')]:
        snap=snapshots[name];event_id=name+'.retry';content='Continue the same conditional review.'
        messages=[{'event_id':row['event']['event_id'],'kind':row['event']['kind'],
                   'content':row['event']['new_content']['text'],'status':row['status']} for row in snap['records']]
        messages.append({'event_id':event_id,'kind':'retry','content':content})
        raw=canonical({'schema':'terminal-semantic-native-planning-transcript@1','purpose':'conditional_review',
            'binding':snap['binding'],'instruction':instruction,'events':messages})
        tokens=len(encoding.encode(raw.decode(),allowed_special=set(),disallowed_special=()))
        require(len(raw)<=256000 and snap['totals']['rendered_input_tokens']+tokens>snap['policy']['max_rendered_input_tokens'],
                'denial:whole-retry-exceeds-cumulative-budget-before-observer:' + name)
        denied[name+'-retry']={'proposed_whole_input_bytes':len(raw),'proposed_whole_input_tokens':tokens,
                             'prior_charged_tokens':snap['totals']['rendered_input_tokens']}
    previews={kind:load(R/(kind+'-preview.json')) for kind in ('expanded','view')}
    a,b=(previews[kind]['native_review'] for kind in ('expanded','view'))
    expected_ids=['task:call-review:revalidate_conditional_model','task:call-review:review_runtime_assumptions',
                  'task:call-review:review_uncovered_source']
    for name,value in previews.items():
        identity(value,'result_cid','preview:exact-outer-native-review:' + name)
        native_review(value['native_review'],name,head,native,capacity,expected_ids)
        pin_declared(value['producer'])
    for key in ('request','native_planning_material','review_projection'):
        compare_tree(a[key],b[key],'paired:complete-identical-native-' + key)
    compare_tree(a['native_preview']['input_snapshot'],b['native_preview']['input_snapshot'],'paired:complete-material-snapshot')
    def normalize(plan):
        value=deepcopy(plan)
        for key in ('input_digest','plan_id'):del value[key];del value['deterministic_replay'][key]
        del value['replay_request']['current_time_ms'];return value
    compare_tree(normalize(a['native_parallel_plan']),normalize(b['native_parallel_plan']),
                 'paired:entire-native-forecast-except-exact-five-clock-identity-fields')
    for key in ('input_snapshot_cid','obligation_graph_cid','candidate_portfolio_cid','critique_cid'):
        require(a['native_preview']['preview'][key]==b['native_preview']['preview'][key],'paired:stable-native-identity:' + key)
    require(summary['resources_after']['active_lease_count']==summary['resources_after']['waiting_request_count']==0,
            'resources:all-leases-waiters-released')
    require(summary['independent_counterfactual_traces'] is True and summary['global_task_budget_enforced'] is False
            and summary['durable_budget_resume_supported'] is False and summary['provider_calls']==0,
            'scope:separate-process-local-traces-no-global-or-provider-budget-claim')
    pin_declared(capsule['expansion']);pin_declared(capsule['producer']);pin_declared(query['producer'])
    qualification=load(A/'qualification-summary.json')
    require(qualification['rows']==49 and len(qualification['families'])==20,'metadata:49-rows-20-families')
    processes=load(A/'model/callee/native-lowering/lean_process.json');caller=load(A/'model/process.json')
    for name,process in [*processes.items(),('caller',caller)]:
        require(process['returncode']==0 and process['termination_reason']=='completed'
                and '/leanprover--lean4---v4.34.1/bin/lean' in process['command'][0],
                'proof:three-fresh-successful-pinned-Lean-process-receipts:' + name)
    package_and_tests()
    budget_source=read(C/'benchmarks/agent_supervisor/container_coding/terminal_semantic_context_budget.py').decode()
    tree=ast.parse(budget_source);classes={node.name:node for node in tree.body if isinstance(node,ast.ClassDef)}
    owner_methods={node.name:node for node in classes['ContextBudgetOwner'].body if isinstance(node,ast.FunctionDef)}
    for name in ('reserve','snapshot','close','prepare_event'):
        require(any(isinstance(node,ast.Name) and node.id=='_owner_locked' for node in owner_methods[name].decorator_list),
                'source:atomic-owner-transition:' + name)
    reservation_methods={node.name:node for node in classes['ContextBudgetReservation'].body if isinstance(node,ast.FunctionDef)}
    for name in ('commit','abort','__enter__'):
        require(any(isinstance(node,ast.Name) and node.id=='_reservation_locked' for node in reservation_methods[name].decorator_list),
                'source:atomic-reservation-transition:' + name)
    require('"lock_identity": id(self._lock)' in budget_source and 'with self.reserve(event, cancel_event=cancel_event)' in budget_source,
            'source:sealed-original-lock-and-preflight-before-callback')
    delivery_source=read(C/'benchmarks/agent_supervisor/container_coding/terminal_semantic_budget_delivery.py').decode()
    funcs={node.name:node for node in ast.parse(delivery_source).body if isinstance(node,ast.FunctionDef)}
    scope=ast.get_source_segment(delivery_source,funcs['_current_delivery_scope'])
    require(scope.index('with forecast.metadata._producer')<scope.index('forecast.revisions._capture')<
            scope.index('checked._retain_model_artifacts')<scope.index('capacity_control.require_current'),
            'source:all-original-witnesses-before-first-capacity-and-render-callback')
    live=ast.get_source_segment(delivery_source,funcs['observe_current_budgeted_semantic_input'])
    require(live.rindex('== receipt["result_cid"]')>live.index('# The context manager performs one last custody callback')
            and '_wire(value) == export_wire' in live and '_wire(committed["records"][-1]["event"])' in live,
            'source:nonaliasing-complete-export-and-charged-event-integrity-after-final-scope-callback')
    require('native_runner.render_model_prompt' in delivery_source and 'purpose="planning"' in delivery_source,
            'source:actual-narrow-native-planning-renderer-no-full-worker-route')
    for path in ('boundary-source-review.json','boundary-review-criteria.json','entrypoint-model-input-review.json'):
        load(W/path)
    for path in ('qualification-report.json','improvement-status.json','development-history.json'):
        report=load(W/path);ceiling(report,'report:' + path)
        if path=='development-history.json':pin_declared(report)
    claims=load(W/'qualification-claims-review.json')
    require(claims.get('checks_count')==128 and claims.get('discrepancies')==[],
            'claims:separate-readonly-claims-review-128-checks-no-discrepancies')
    for pin in claims['artifacts']:pin_declared(pin)
    ast.parse(read(W/'seal_current.py'),filename='seal_current.py')
    ast.parse(read(W/'run_current.py'),filename='run_current.py')
    for name,value in [('summary',summary),('view',view),('native',native),('capsule',capsule)]:ceiling(value,name)
    counts.update(native_capsules=6,native_blocks=45,registered_references_per_scope=50,
        current_capacity_scopes=4,charged_local_attempts=7,normal_probe_callbacks=5,injected_fault_callbacks=2,
        actual_current_expansion_calls=1,actual_live_controls=13,expanded_initial_whole_input_tokens=70977,
        view_initial_whole_input_tokens=47215,view_two_turn_whole_input_tokens=95678,
        view_two_turn_new_content_tokens=44374,independently_reconstructed_denied_retries=denied,
        provider_usage_measured=False,global_task_budget_enforced=False,
        native_worker_or_full_supervisor_entrypoint_qualified=False)

def finish(path):
    for name,value in captures.items():
        current=os.fstat(value['fd'])
        check(stamp(current)==value['stamp']==stamp(Path(name).lstat()),'closing-custody:' + name)
        os.lseek(value['fd'],0,os.SEEK_SET)
        digest=hashlib.sha256()
        while chunk:=os.read(value['fd'],1024*1024):digest.update(chunk)
        check(digest.hexdigest()==value['pin']['sha256'],'closing-retained-FD-content:' + name)
    report={'schema':'terminal-semantic-context-budget-independent-review@1',
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
            'interpretation':'Review rechecks public identities/joins/custody and own exact typed budget/transcript replay, reference reconstruction and token counts. Genuine native readbacks, compiler replays, controls and process outcomes are attributed to pinned application evidence; no origin authority is conferred.'}}
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
