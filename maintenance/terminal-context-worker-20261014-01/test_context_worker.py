"""Data guards use named sealed public fixtures, never predecessor databases."""
from copy import deepcopy
from io import BytesIO
import json
import pytest
from context_worker import prepare_request,read_request,WorkerInputError
from worker_io import REFERENCE,REFERENCE_MANIFEST_SHA,read,sha,wire
from worker_run import make_request

@pytest.fixture(scope='module')
def task():
    raw=read(REFERENCE/'evidence-manifest.json',1024**2)
    assert sha(raw)==REFERENCE_MANIFEST_SHA
    inventory={v['path']:v for v in json.loads(raw)['files']}
    name='experiment-02/contexts.json';raw=read(REFERENCE/name,1024**2)
    assert sha(raw)==inventory[name]['sha256']
    return json.loads(raw)['tasks'][1]

@pytest.fixture(scope='module')
def descriptor():
    from token_cost_review import load_tokenizer
    return load_tokenizer()[1]

def test_real_sealed_source_context_prepares_with_exact_packed_history(task,descriptor):
    request=make_request(task,'adaptive',0,descriptor,[])
    selected,previous=prepare_request(request)
    assert selected['selected_form']=='packed'
    second=make_request(task,'adaptive',1,descriptor,previous)
    actual,manifest=prepare_request(second)
    assert manifest[:len(previous)]==previous
    assert actual['input_tokens']<=request['max_input_tokens']

@pytest.mark.parametrize('mutation',['rewrite','reorder','omit','identity','role','nonrequired'])
def test_observed_history_cannot_change(task,descriptor,mutation):
    _,previous=prepare_request(make_request(task,'adaptive',0,descriptor,[]))
    request=make_request(task,'adaptive',1,descriptor,previous)
    if mutation=='rewrite':request['messages'][0]['content']+=' altered'
    elif mutation=='reorder':request['messages'][:2]=reversed(request['messages'][:2])
    elif mutation=='omit':request['messages']=request['messages'][1:]
    elif mutation=='identity':request['messages'][0]['message_id']='different'
    elif mutation=='role':request['messages'][0]['role']='user'
    else:request['history_required_ids']=[]
    with pytest.raises(ValueError):prepare_request(request)

def test_wrong_complete_head_refused(task,descriptor):
    request=make_request(task,'adaptive',0,descriptor,[])
    request=deepcopy(request);request['expected_head']['generation']+=1
    with pytest.raises(WorkerInputError,match='expected head'):prepare_request(request)

def test_underbudget_refused_before_any_router_import(task,descriptor):
    request=make_request(task,'adaptive',0,descriptor,[]);request['max_input_tokens']=1
    with pytest.raises(ValueError):prepare_request(request)

def test_decoded_control_exact_original_context(task,descriptor):
    request=make_request(task,'decode_before_model',0,descriptor,[])
    selected,_=prepare_request(request)
    assert selected['selected_form']=='expanded'
    assert selected['selected_messages'][1]['content']==request['original_rendered']

def test_request_exact_canonical_roundtrip(task,descriptor):
    request=make_request(task,'adaptive',0,descriptor,[])
    assert read_request(BytesIO(wire(request)))==request

@pytest.mark.parametrize('raw',[b'{} ',b'{"schema":1,"schema":2}',b'{"x":1.0}',b'{"x":NaN}',b'['*65+b']'*65])
def test_noncanonical_or_unbounded_parser_inputs_refused(raw):
    with pytest.raises(ValueError):read_request(BytesIO(raw))
