"""Experimental planning-input worker, with a real router local consumer.

This entrypoint grants no task admission, source editing or completion. The
owner observes the actual repository before and after its native process launch.
"""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent

def bootstrap():
    parent=ROOT.parent
    pinned=parent/'terminal-compact-retrieval-20261011-01'/'pinned-dependencies-v10'
    paths=[ROOT,parent/'terminal-reference-packing-20261014-01',parent/'terminal-source-capsules-20261014-01',
        parent/'terminal-token-pairing-20261012-01'/'pinned-host-tokenizer',parent/'terminal-typed-ir-training-20261014-01',
        parent/'terminal-typed-ir-proof-index-20261014-01',parent/'terminal-codebase-ir-training-20261014-01',
        parent/'terminal-proof-cache-revision-20261012-01'/'pinned-host-duckdb',
        parent/'terminal-dispatch-evidence-20261014-01'/'checkout',pinned/'datasets',pinned/'kit']
    sys.path[:0]=[str(path) for path in paths]
    from scheduler_overlay import load_overlay
    load_overlay()

SCHEMA='terminal-complete-context-worker-request@1'
RESPONSE_SCHEMA='terminal-complete-context-worker-observation@1'
FIELDS={'schema','request_id','session_id','expected_head','original_rendered','packed_wire','messages',
    'context_message_id','max_input_tokens','tokenizer_descriptor','history_required_ids','delivery_mode','previous_message_manifest'}
CLAIMS={key:False for key in ['native_full_supervisor_invoked','official_terminal_bench_harness_executed',
    'proof_authority','execution_authority','completion_authority','task_satisfaction','model_interpretation_equivalence_proved']}

class WorkerInputError(ValueError):
    pass

def need(ok,message):
    if not ok:raise WorkerInputError(message)

def read_request(stream):
    import json
    from worker_io import wire
    from reference_codec import _plain
    raw=stream.read(1048577)
    need(type(raw) is bytes and 0<len(raw)<=1048576,'bounded worker request bytes required')
    text=raw.decode('ascii');depth=0;quoted=False;escaped=False
    for char in text:
        if quoted:
            if escaped:escaped=False
            elif char=='\\':escaped=True
            elif char=='"':quoted=False
        elif char=='"':quoted=True
        elif char in '[{':
            depth+=1;need(depth<=64,'bounded request nesting required')
        elif char in ']}':
            depth-=1;need(depth>=0,'request nesting differs')
    need(depth==0 and not quoted,'complete request JSON required')
    def pairs(items):
        result={}
        for key,value in items:
            need(key not in result,'duplicate request key');result[key]=value
        return result
    def reject(_):raise WorkerInputError('exact integer-only request JSON required')
    value=json.loads(text,object_pairs_hook=pairs,parse_float=reject,parse_constant=reject)
    _plain(value,maximum=1048576)
    need(wire(value)==raw,'canonical ASCII worker request required')
    return value

def prepare_request(request):
    import json
    from worker_io import wire,sha
    from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead
    from reference_codec import decode_reference_packet
    from nested_context import restore_context_strings,validate_source_complete
    from adaptive_delivery import select_delivery
    need(type(request) is dict and set(request)==FIELDS and request['schema']==SCHEMA,'closed worker request scope required')
    for key in ['request_id','session_id']:
        value=request[key]
        need(type(value) is str and 0<len(value.encode('utf-8'))<=128 and
            all(ord(c)>=32 and ord(c)!=127 for c in value),'bounded worker request identity required')
    head=CodebaseHead.from_dict(request['expected_head'])
    need(wire(head.to_dict())==wire(request['expected_head']),'canonical complete native head required')
    original=request['original_rendered']
    document=decode_reference_packet(request['packed_wire'])
    need(restore_context_strings(document)==original,'packed context differs from complete original')
    validate_source_complete(rendered=original,doc=document)
    core=json.loads(original)
    need(wire(core['scope']['head'])==wire(head.to_dict()),'request expected head differs from complete source context')
    need(type(request['history_required_ids']) is list,'explicit bounded history ID list required')
    mode=request['delivery_mode']
    need(type(mode) is str and mode in {'adaptive','expanded','packed','decode_before_model'},'closed worker delivery mode required')
    selected=select_delivery(original_rendered=original,packed_wire=request['packed_wire'],messages=request['messages'],
        context_message_id=request['context_message_id'],restore=restore_packed,
        max_input_tokens=request['max_input_tokens'],tokenizer_descriptor=request['tokenizer_descriptor'],
        history_required_ids=tuple(request['history_required_ids']),delivery_mode='expanded' if mode=='decode_before_model' else mode)
    previous=request['previous_message_manifest']
    need(type(previous) is list and len(previous)<=32,'bounded observed history manifest required')
    actual=[{'message_id':row['message_id'],'role':row['role'],'content_sha256':sha(row['content'].encode('utf-8'))}
        for row in selected['selected_messages']]
    by_id={row['message_id']:row for row in actual};seen=set()
    for row in previous:
        need(type(row) is dict and set(row)=={'message_id','role','content_sha256'} and
            type(row['message_id']) is str and row['message_id'] not in seen,'unique exact observed history row required')
        seen.add(row['message_id'])
        need(row==by_id.get(row['message_id']),'previously delivered message omitted or rewritten')
    need(actual[:len(previous)]==previous,'previously delivered history must remain an ordered prefix')
    need(seen<=set(request['history_required_ids']),'every previously delivered message must remain required')
    return selected,actual

def restore_packed(text):
    from reference_codec import decode_reference_packet
    from nested_context import restore_context_strings
    return restore_context_strings(decode_reference_packet(text))

def execute_request(request):
    from worker_io import sha,wire
    from router_consumer import capture_with_native_router
    selected,manifest=prepare_request(request)
    consumer=capture_with_native_router(payload=selected['serialized_payload'],expected_sha256=selected['payload_sha256'],
        expected_bytes=selected['payload_bytes'],tokenizer_descriptor=request['tokenizer_descriptor'])
    need(consumer['input_sha256']==selected['payload_sha256'] and consumer['input_bytes']==selected['payload_bytes'] and
        consumer['input_local_tokens']==selected['input_tokens'] and consumer['consumer_calls']==1,
        'actual local router consumer input differs from the selected full payload')
    return {'schema':RESPONSE_SCHEMA,'request_id':request['request_id'],'session_id':request['session_id'],
        'expected_head':request['expected_head'],'request_sha256':sha(wire(request)),'selection':selected,
        'consumer':consumer,'selected_message_manifest':manifest,'provider_usage':None,
        'actual_external_provider_invocations':0,**CLAIMS}

if __name__=='__main__':
    import signal
    signal.alarm(35)
    bootstrap()
    from worker_io import wire
    result=execute_request(read_request(sys.stdin.buffer))
    sys.stdout.buffer.write(wire(result));sys.stdout.buffer.flush()
