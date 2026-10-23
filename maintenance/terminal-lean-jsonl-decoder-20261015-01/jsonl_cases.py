"""Authored public file fixtures; no benchmark inputs, tests or solutions."""
from copy import deepcopy
import json
import os
from pathlib import Path
from jsonl_io import ROOT,wire,sha

FILE_PATHS=('input_data/requests_bucket_1.jsonl','input_data/requests_bucket_2.jsonl',
    'output_data/plan_b1.jsonl','output_data/plan_b2.jsonl')

def specs():
    from scheduler_constraints import authored_cases
    old={row['case']['case_id']:row for row in authored_cases()};result=[]
    def add(name,base='valid-minimal',*,outcome='accepted',style='lf',fault=None):
        result.append({'case_id':name,'case':deepcopy(old[base]['case']),
            'metrics':{str(row['bucket_id']):deepcopy(row['metrics']) for row in old[base]['case']['buckets']},
            'expected_outcome':outcome,'style':style,'fault':fault,
            'intended_violation_ids':list(old[base]['intended_violation_ids']) if outcome=='model_refusal' else []})
    for name in ('valid-minimal','valid-eight-global-shapes','valid-thresholds-strictly-below','valid-empty-bounded-model'):
        add(name,base=name)
    add('valid-unicode-crlf',style='unicode_crlf')
    add('valid-json-whitespace-no-final-lf',style='spaces_no_final_lf')
    add('valid-escaped-identifiers',style='escaped_ids')
    for name in ('invalid-nine-global-shapes','missing-output','extra-output','unaligned-sequence',
            'wrong-heads','wrong-hidden','inconsistent-batch-shapes','below-rounded-prompt','threshold-1-pad_ratio-equal'):
        add(name,base=name,outcome='model_refusal')
    for fault in ('duplicate_key','escaped_duplicate_key','float_prompt','boolean_generation','nonfinite_prompt',
            'trailing_json_value','blank_line','invalid_utf8','unknown_plan_field','duplicate_request_id','duplicate_plan_id'):
        add('reject-'+fault,outcome='file_refusal',fault=fault)
    for fault in ('changed_input_bytes','changed_plan_bytes','same_bytes_replacement'):
        add('reject-'+fault,outcome='file_refusal',fault=fault)
    return result

def _encoded(rows,style,*,kind):
    ending='\r\n' if style=='unicode_crlf' else '\n'
    ascii_only=style!='unicode_crlf'
    if style=='escaped_ids':ascii_only=kind=='requests'
    lines=[]
    for row in rows:
        body=json.dumps(row,sort_keys=True,separators=(',',':'),ensure_ascii=ascii_only)
        if style=='spaces_no_final_lf':body='\t '+json.dumps(row,ensure_ascii=ascii_only)+'  '
        lines.append(body)
    text=ending.join(lines)
    if lines and style!='spaces_no_final_lf':text+=ending
    return text.encode('utf-8')

def fixture_payloads(spec):
    case=deepcopy(spec['case'])
    if spec['style'] in ('unicode_crlf','escaped_ids'):
        for bucket in case['buckets']:
            for request,row in zip(bucket['requests'],bucket['plan']):
                identifier='α🍋é-bucket'+str(bucket['bucket_id'])
                request['request_id']=identifier;row['request_id']=identifier;row['batch_id']='β₂'
    bodies={}
    for bucket in case['buckets']:
        number=bucket['bucket_id']
        bodies['input_data/requests_bucket_'+str(number)+'.jsonl']=_encoded(bucket['requests'],spec['style'],kind='requests')
        bodies['output_data/plan_b'+str(number)+'.jsonl']=_encoded(bucket['plan'],spec['style'],kind='plan')
    fault=spec['fault'];input_name=FILE_PATHS[0];plan_name=FILE_PATHS[2]
    first_request=case['buckets'][0]['requests'][0] if case['buckets'][0]['requests'] else None
    if fault in ('duplicate_key','escaped_duplicate_key','float_prompt','boolean_generation','nonfinite_prompt','trailing_json_value'):
        text=bodies[input_name].decode('utf-8')
        if fault=='duplicate_key':text=text.replace('"prompt_len":64','"prompt_len":64,"prompt_len":65')
        elif fault=='escaped_duplicate_key':text=text.replace('"prompt_len":64','"prompt_len":64,"prompt_\\u006cen":65')
        elif fault=='float_prompt':text=text.replace('"prompt_len":64','"prompt_len":64.0')
        elif fault=='boolean_generation':text=text.replace('"gen_len":1','"gen_len":true')
        elif fault=='nonfinite_prompt':text=text.replace('"prompt_len":64','"prompt_len":NaN')
        else:text=text.rstrip('\n')+' {}\n'
        bodies[input_name]=text.encode('utf-8')
    elif fault=='blank_line':bodies[plan_name]+=b'\n'
    elif fault=='invalid_utf8':bodies[input_name]=b'\xff'+bodies[input_name]
    elif fault=='unknown_plan_field':
        row=deepcopy(case['buckets'][0]['plan'][0]);row['undeclared']=True
        bodies[plan_name]=_encoded([row],spec['style'],kind='plan')
    elif fault=='duplicate_request_id':bodies[input_name]+=_encoded([first_request],spec['style'],kind='requests')
    elif fault=='duplicate_plan_id':bodies[plan_name]+=_encoded([case['buckets'][0]['plan'][0]],spec['style'],kind='plan')
    return bodies

def create_bundle(*,destination:Path,spec:dict):
    if destination.resolve()!=destination or ROOT not in destination.parents or destination.exists():
        raise ValueError('fresh canonical owned file fixture required')
    destination.mkdir(mode=0o700);(destination/'input_data').mkdir();(destination/'output_data').mkdir()
    bodies=fixture_payloads(spec)
    for name,raw in bodies.items():
        with (destination/name).open('xb') as stream:stream.write(raw)
    return {'schema':'terminal-authored-jsonl-file-fixture@1','case_id':spec['case_id'],
        'root':str(destination),'initial_payloads':{name:{'bytes':len(raw),'sha256':sha(raw)} for name,raw in sorted(bodies.items())},
        'real_benchmark_input_used':False,'source_body_execution':False}

def mutate_between_observations(*,destination:Path,spec:dict):
    fault=spec['fault']
    if fault not in ('changed_input_bytes','changed_plan_bytes','same_bytes_replacement'):return
    name=FILE_PATHS[2] if fault=='changed_plan_bytes' else FILE_PATHS[0]
    path=destination/name;raw=path.read_bytes()
    if fault=='same_bytes_replacement':
        temporary=path.with_name('.owned-replacement.jsonl')
        with temporary.open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path)
    else:
        with path.open('wb') as stream:stream.write(raw.rstrip(b'\n')+b' \n');stream.flush();os.fsync(stream.fileno())
