"""Actual native public Bottle nomination/readback; no provider or target import."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import time

STAGE = Path(__file__).resolve().parent
C = STAGE.parent / 'terminal-token-reduction-20261007-01/checkout'
E = STAGE.parent / 'terminal-compact-retrieval-20261011-01/pinned-dependencies-v10'
FIXTURE = STAGE / 'public-native-fixture-01'
CACHE = STAGE.parent / 'terminal-compact-context-20261011-01/tokenizer-cache'


def wire(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    output = STAGE / 'public-nomination-qualification-02'
    output.mkdir(mode=0o755)
    output.chmod(0o755)
    cwd = output / 'empty-working-directory'
    cwd.mkdir(mode=0o755)
    sentinel = output / 'unrelated-owner-must-stay-unused.duckdb'
    os.environ['IPFS_ACCELERATE_META_INDEX_DUCKDB'] = str(sentinel)
    os.environ.pop('IPFS_ACCELERATE_META_INDEX_DUCKLAKE',None)
    os.environ['TIKTOKEN_CACHE_DIR'] = str(CACHE)
    asset = (CACHE/'fb374d419588a4632f3f557e76b4b70aebbca790').read_bytes()
    assert sha(asset)=='446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d'
    import tiktoken
    tokens = tiktoken.get_encoding('o200k_base')
    def count(raw):
        return len(tokens.encode(raw.decode(),disallowed_special=()))
    from benchmarks.agent_supervisor.container_coding.terminal_public_intent_contract import build_terminal_public_intent_profile
    from ipfs_accelerate_py.agent_supervisor.runtime import code_source_inspection as original
    from ipfs_accelerate_py.agent_supervisor.runtime.intent_source_nomination import build_intent_source_nomination, REVIEW_SCHEMA
    from ipfs_accelerate_py.agent_supervisor.runtime.intent_source_inspection import prepare_intent_source_nomination_artifact
    started = time.monotonic()
    producers=[]
    for name in ['ipfs_accelerate_py/agent_supervisor/runtime/code_source_inspection.py',
                 'ipfs_accelerate_py/agent_supervisor/runtime/intent_source_nomination.py',
                 'ipfs_accelerate_py/agent_supervisor/runtime/intent_source_inspection.py']:
        raw=(C/name).read_bytes();producers.append({'path':str(C/name),'bytes':len(raw),'sha256':sha(raw)})
    producers.append({'path':str(Path(__file__).resolve()),'bytes':len(Path(__file__).read_bytes()),'sha256':sha(Path(__file__).read_bytes())})
    fixture=json.loads((FIXTURE/'summary.json').read_text())
    native=dict(repository=Path(fixture['repository']),artifact=fixture['frontier_artifact'],
        expected_sha256=fixture['frontier_artifact_sha256'],task_id=fixture['task_id'],task_cid=fixture['task_cid'],
        source_artifact=fixture['source_artifact'],source_sha256=fixture['source_artifact_sha256'])
    captured=original._capture_native_evidence(**native)
    instruction=(FIXTURE/'instruction.txt').read_text()
    profile=build_terminal_public_intent_profile(source_text=instruction)
    independent=dict(contract=profile['contract'],source_text=instruction,
        task_id=native['task_id'],task_cid=native['task_cid'],task_revision=captured['spec']['task_revision'],
        repository_id=captured['spec']['repository_id'],tree_id=captured['spec']['tree_id'],
        snapshot=captured['snapshot'],source_by_path=captured['sources'])
    generic=build_intent_source_nomination(**independent)
    (output/'generic-nomination.json').write_bytes(wire(generic))
    assert not generic['nominations'] and all(row['residual'] for row in generic['requirements'])
    assert len(generic['requirements'])==19
    def requirement(statement):
        matches=[row['native_requirement']['requirement_id'] for row in generic['requirements']
            if statement in row['native_requirement']['statement_ids']]
        assert len(matches)==1
        return matches[0]
    selected=[('bottle._hkey',requirement('public-bottle:statement:invalid-input-error')),
              ('bottle._hval',requirement('public-bottle:statement:invalid-input-error')),
              ('bottle.HeaderDict',requirement('public-bottle:statement:identify-bottle'))]
    query_symbols=[hit.row.qualified_symbol for hit in captured['result'].hits]
    assert all(symbol not in query_symbols for symbol,_ in selected)
    reviews={
        'empty':{'schema':REVIEW_SCHEMA,'bindings':generic['bindings'],
            'review_ref':'authored:public-bottle-empty-source-inventory@1','selectors':[]},
        'headers':{'schema':REVIEW_SCHEMA,'bindings':generic['bindings'],
            'review_ref':'authored:public-bottle-header-exploration-candidates@1',
            'selectors':[{'requirement_id':req,'path':'bottle.py','qualified_symbol':symbol} for symbol,req in selected]}}
    prepared={}
    prepare_seconds={}
    for name,review in reviews.items():
        review_path=output/(name+'-review.json');review_path.write_bytes(wire(review));review_path.chmod(0o644)
        began=time.monotonic()
        prepared[name]=prepare_intent_source_nomination_artifact(**native,contract=profile['contract'],
            source_text=instruction,review_path=review_path,review_sha256=sha(wire(review)),
            output=native['repository']/('intent-nomination-'+name))
        prepare_seconds[name]=time.monotonic()-began
    assert not prepared['empty']['nomination']['nominations']
    nominations=prepared['headers']['nomination']['nominations']
    assert len(nominations)==3 and all(row['residual'] for row in prepared['headers']['nomination']['requirements'])
    env=dict(os.environ,PYTHONPATH=':'.join(map(str,[C,E/'datasets',E/'kit'])),PYTHONDONTWRITEBYTECODE='1')
    calls=[]
    def cli(label,arguments,old=False):
        module='ipfs_accelerate_py.agent_supervisor.runtime.'+('code_source_inspection' if old else 'intent_source_inspection')
        cmd=[sys.executable,'-P','-m',module]
        for key,value in arguments.items():
            if value is not None:cmd += ['--'+key.replace('_','-'),str(value)]
        began=time.monotonic();result=subprocess.run(cmd,cwd=cwd,env=env,capture_output=True,timeout=60)
        item={'label':label,'returncode':result.returncode,'seconds':time.monotonic()-began,
            'stdout_bytes':len(result.stdout),'stderr_bytes':len(result.stderr)}
        if result.returncode==0:
            assert not result.stderr and len(result.stdout)<=arguments['max_bytes']
            value=json.loads(result.stdout);assert result.stdout==wire(value)
            item.update(sha256=sha(result.stdout),local_tokens=count(result.stdout))
            (output/(label+'.json')).write_bytes(result.stdout)
        else:
            assert result.returncode==2 and not result.stdout and len(result.stderr)<=512
            value=json.loads(result.stderr)
            assert value['schema'].endswith('inspection-error@1')
            item['bounded_refusal']=value
        calls.append(item)
        print(json.dumps({'completed':label,'returncode':result.returncode,'stdout_bytes':len(result.stdout),'seconds':round(item['seconds'],3)}),flush=True)
        return value,item
    def arguments(which='headers',**changes):
        data=prepared[which]
        args=dict(repository=native['repository'],artifact=data['artifact'],expected_sha256=data['sha256'],
            task_id=native['task_id'],task_cid=native['task_cid'],frontier_artifact=native['artifact'],
            frontier_sha256=native['expected_sha256'],source_artifact=native['source_artifact'],
            source_sha256=native['source_sha256'],contract_sha256=data['inputs']['contract']['sha256'],
            instruction_sha256=data['inputs']['instruction']['sha256'],review_sha256=data['inputs']['review']['sha256'],
            question='Inspect the explicitly authored source candidate; preserve all behavioral obligations.',
            max_bytes=8192)
        args.update(changes);return args
    cases=[]
    for entry in nominations:
        for mode in (['source','facts'] if entry['qualified_symbol']=='bottle._hkey' else ['source']):
            fragments=[];offset=0;continuation=None;case_calls=[]
            for number in range(1,17):
                label=entry['qualified_symbol'].replace('.','-')+'-'+mode+'-page-'+str(number)
                packet,item=cli(label,arguments(row_id=entry['row_id'],mode=mode,continuation=continuation))
                assert item['returncode']==0 and packet['schema']=='supervisor-intent-source-inspection@1'
                assert packet['bindings']['selection_basis']=='explicit_reviewed_source_row_nomination'
                assert packet['bindings']['selected_from_query_hits'] is False
                assert packet['bindings']['requirement_ids']==entry['requirement_ids']
                assert packet['bindings']['review_ref']==entry['review_ref']
                assert packet['bindings']['source_span']==entry['source_span']
                assert packet['bindings']['native_facts_sha256']==entry['native_facts_sha256']
                for key in ['semantic_authority','proof_authority','execution_authority','completion_authority',
                    'source_authentication_claimed','immutable_custody_claimed']:
                    assert packet[key] is False
                assert packet['bindings']['behavioral_requirements_satisfied'] is False
                fragment=packet['content_text'].encode();assert packet['page_offset']==offset
                assert len(fragment)==packet['page_bytes'] and sha(fragment)==packet['page_sha256']
                fragments.append(fragment);offset=packet['page_end'];case_calls.append(item)
                continuation=packet['continuation']
                if packet['complete']:
                    assert continuation is None;break
                assert continuation is not None
            else:raise AssertionError('bounded reconstruction did not complete')
            joined=b''.join(fragments)
            if mode=='source':
                raw=(native['repository']/entry['path']).read_bytes()
                expected=raw[entry['source_span']['byte_start']:entry['source_span']['byte_end']]
            else:
                row=next(row for row in captured['snapshot'].rows if row.row_id==entry['row_id'])
                from ipfs_accelerate_py.agent_supervisor.analysis.code_symbol_vector_index import resolve_code_symbol_ast_facts
                record=next(record for record in captured['ast_index'].path_records if record.path==row.path)
                expected=wire(resolve_code_symbol_ast_facts(record,row))
            assert joined==expected and sha(joined)==packet['content_sha256']
            cases.append({'symbol':entry['qualified_symbol'],'mode':mode,'pages':len(case_calls),
                'content_bytes':len(joined),'complete_output_bytes':sum(item['stdout_bytes'] for item in case_calls),
                'sum_independent_local_output_tokens':sum(item['local_tokens'] for item in case_calls),
                'exact_reconstruction':True})
    first=nominations[0]
    negatives=[('empty-review-no-row',arguments('empty',row_id=first['row_id'])),
        ('unreviewed-original-query-hit',arguments(row_id=captured['result'].hits[0].row.row_id)),
        ('foreign-task',arguments(row_id=first['row_id'],task_cid='task:foreign')),
        ('wrong-review-digest',arguments(row_id=first['row_id'],review_sha256='0'*64)),
        ('wrong-contract-digest',arguments(row_id=first['row_id'],contract_sha256='0'*64)),
        ('wrong-instruction-digest',arguments(row_id=first['row_id'],instruction_sha256='0'*64))]
    for label,args in negatives:
        _,item=cli(label,args);assert item['returncode']==2
    old=dict(native);old.update(row_id=first['row_id'],question='Read the authored candidate.',max_bytes=8192)
    _,item=cli('old-query-api-still-refuses',old,old=True);assert item['returncode']==2
    # The producer legitimately adds new public namespaces to the repository.
    # Original nominated input files and their file witnesses remain exact.
    for item in fixture['pins']:
        path=Path(item['path']);raw=path.read_bytes();info=path.lstat()
        assert len(raw)==item['bytes'] and sha(raw)==item['sha256']
        assert {key:getattr(info,key) for key in item['witness']}==item['witness']
    for item in producers:
        raw=Path(item['path']).read_bytes();assert len(raw)==item['bytes'] and sha(raw)==item['sha256']
    assert not sentinel.exists()
    summary={'schema':'public-bottle-reviewed-source-nomination-qualification@1','qualified':True,
        'fixture':{'path':str(FIXTURE/'summary.json'),'sha256':sha((FIXTURE/'summary.json').read_bytes())},
        'native_symbols':fixture['native_symbols'],'ducklake_projection':fixture['fresh_ducklake_projection'],
        'literal_query_hits':query_symbols,'literal_query_hits_unchanged':True,
        'generic_unknown_census':generic['unknown_census'],
        'reviewed_unknown_census':prepared['headers']['nomination']['unknown_census'],
        'all_19_requirements_residual':True,'reviewed_candidates':[row['qualified_symbol'] for row in nominations],
        'authored_selectors_are_task_meaning_or_behavior_proof':False,
        'artifact_bytes':{key:value['bytes'] for key,value in prepared.items()},
        'prepared_artifacts':{key:{field:value[field] for field in ['artifact','sha256','bytes','inputs','native_bindings']} for key,value in prepared.items()},
        'cases':cases,'calls':calls,'producer_pins':producers,'prepare_seconds':prepare_seconds,
        'seconds':time.monotonic()-started,'original_fixture_file_bytes_and_witnesses_unchanged':True,
        'unrelated_metadata_owner_activated':False,'separate_cwd_host_cli_qualified':True,
        'local_tokenizer':{'version':tiktoken.__version__,'encoding':'o200k_base','asset_sha256':sha(asset),
            'scope':'Independent LOCAL serialized output counts, not native/provider usage or turn attribution.'},
        'real_admitted_context_or_installed_worker_qualified':False,
        'coding_prompt_nomination_consumption_qualified':False,
        'signed_planning_inputs_modified':False,'planner_current_facts_supplied':False,
        'provider_calls':0,'training_steps':0,'prover_invocations':0,'target_module_imports':0,
        'provider_total_token_savings_established':False,'source_equivalence_proved':False,
        'task_satisfaction_proved':False,'model_convergence_proved':False}
    (output/'qualification.json').write_bytes(wire(summary))
    print(json.dumps({'qualified':True,'cases':len(cases),'calls':len(calls),'residual_requirements':19,
        'provider_calls':0,'seconds':summary['seconds']}),flush=True)


if __name__=='__main__':main()
