"""Public historical evidence replay, separate from current dispatch authority."""
import argparse
import json
import math
from pathlib import Path
import re
import resource
import stat
from admission_io import ROOT,FALSE,inputs,read,write,wire,sha
from admission_run import POLICY,FILES,MODES,build_contexts,make_request,input_binding,check_lease
TASKS={'headless-terminal','llm-inference-batching-scheduler','feal-differential-cryptanalysis','break-filter-js-from-html'}
WORKER_LEAVES={'request.json','stdout.json','stderr.log','router-allocation.duckdb','router-allocation.duckdb.wal'}

def _public_path(name):
    need(type(name) is str and '\\' not in name and all(ord(c)>=32 for c in name),'canonical public artifact text required')
    path=Path(name)
    need(not path.is_absolute() and path.as_posix()==name and not set(path.parts)&{'.','..','.git'},'canonical public artifact path required')
    if name in FILES:return path
    parts=path.parts
    if len(parts)==4 and parts[0]=='workers':
        need(parts[1] in TASKS and parts[2] in MODES and parts[3] in WORKER_LEAVES,'closed known worker artifact scope required')
        return path
    if len(parts)==4 and parts[0]=='jobs':
        need(parts[1] in {task+'-'+mode for task in TASKS for mode in MODES},'closed known native job scope required')
        need((parts[2]=='repository' and parts[3] in {'input-binding.json','validate-planning-observation.py','planning-observation.json'})
            or (parts[2]=='admission' and parts[3]=='planning-job.json'),'closed known public native job artifact required')
        return path
    raise ValueError('closed known public artifact scope required')

def need(value,message):
    if not value:raise ValueError(message)

def _head(value):
    from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead
    head=CodebaseHead.from_dict(value)
    need(wire(head.to_dict())==wire(value),'complete canonical current head required')
    return head

def validate_result(result):
    fields={'schema','completed','policy','native_head','source_count','task_count','native_local_metatasks_admitted',
        'worker_child_invocations','local_consumer_calls','actual_external_provider_invocations','new_optimizer_updates',
        'new_prover_invocations','source_body_execution','metadata_original_record_counts','native_capsule_inventory',
        'artifact_pins','seconds','peak_rss_kib',*FALSE}
    need(type(result) is dict and set(result)==fields,'closed selected admission result required')
    need(result['schema']=='terminal-planning-admission-experiment@1' and result['completed'] is True,'complete selected admission result required')
    need(wire(result['policy'])==wire(POLICY),'exact selected policy required')
    for key,count in dict(source_count=5,task_count=4,native_local_metatasks_admitted=8,worker_child_invocations=8,
            local_consumer_calls=8,actual_external_provider_invocations=0,new_optimizer_updates=0,new_prover_invocations=0).items():
        need(type(result[key]) is int and result[key]==count,'exact actual work counters required')
    need(all(result[k] is False for k in FALSE) and result['source_body_execution'] is False,'result promotes unobserved authority')
    _head(result['native_head'])
    need(type(result['seconds']) in {int,float} and math.isfinite(result['seconds']) and result['seconds']>=0
        and type(result['peak_rss_kib']) is int and result['peak_rss_kib']>=0,'finite nonnegative process diagnostics required')
    for key in ('metadata_original_record_counts','native_capsule_inventory'):
        need(type(result[key]) is dict and result[key] and all(type(k) is str and type(v) is int and v>=0
            for k,v in result[key].items()),'exact nonnegative metadata inventory required')

def artifact_check(output,result):
    need(output.resolve(strict=True)==output and output.parent==ROOT,'owned selected run required')
    pins=result['artifact_pins'];need(type(pins) is list and 65<=len(pins)<=256,'complete bounded public evidence required')
    names=[];acquired={}
    from worker_capture import _read
    for row in pins:
        need(set(row)=={'relative_path','bytes','sha256'},'closed artifact pin required')
        name=row['relative_path'];path=_public_path(name)
        need(name not in names and type(row['bytes']) is int and 0<=row['bytes']<=32*1024**2,'unique bounded artifact required')
        raw=_read(output/path,32*1024**2,empty=row['bytes']==0)
        need(len(raw)==row['bytes'] and sha(raw)==row['sha256'],'selected public artifact changed')
        acquired[name]=raw;names.append(name)
    need(names==sorted(names) and set(FILES)<=set(names),'sorted complete core artifact inventory required')
    expected=set(FILES)
    for task in TASKS:
        for mode in MODES:
            expected|={'workers/'+task+'/'+mode+'/'+leaf for leaf in WORKER_LEAVES-{'router-allocation.duckdb.wal'}}
            expected|={'jobs/'+task+'-'+mode+'/repository/'+leaf for leaf in ('input-binding.json','validate-planning-observation.py','planning-observation.json')}
            expected.add('jobs/'+task+'-'+mode+'/admission/planning-job.json')
    need(expected<=set(names),'all required native job/worker artifact pins required')
    for dirname in ('workers','jobs'):
        actual=set()
        for path in (output/dirname).rglob('*'):
            relative=path.relative_to(output)
            if '.git' in relative.parts:continue
            need(not path.is_symlink() and path.resolve(strict=True)==path,'public artifact symlink refused')
            if path.is_file():actual.add(relative.as_posix())
        need(actual=={name for name in names if name.startswith(dirname+'/')},'complete actual public subtree differs')
    return acquired

def validate_capture(*, output_dir, request, capture, artifacts, expected_selection=None, expected_manifest=None):
    """Replay a retained capture's data joins without checking a PID as live."""
    import worker_capture as native
    import context_worker
    fields = {'schema', 'request_sha256', 'request_bytes', 'native_dispatch', 'observation',
        'output_artifacts', 'current_head_observation_owned_by_caller', 'provider_usage',
        'actual_external_provider_invocations', 'planning_admission', *native.FALSE}
    need(type(capture) is dict and set(capture) == fields and capture['schema'] == native.SCHEMA,
         'closed retained native worker capture required')
    need(all(capture[key] is False for key in native.FALSE) and capture['provider_usage'] is None
         and type(capture['actual_external_provider_invocations']) is int
         and capture['actual_external_provider_invocations'] == 0
         and capture['current_head_observation_owned_by_caller'] is True, 'capture promotes unobserved authority')
    request_raw = native._request(request)
    need(artifacts['request.json'] == request_raw and type(capture['request_bytes']) is int
         and capture['request_bytes'] == len(request_raw) and capture['request_sha256'] == sha(request_raw),
         'retained complete worker request differs')
    need(artifacts['stderr.log'] == b'', 'retained worker stderr is not empty')
    if expected_selection is None:
        expected_selection, expected_manifest = context_worker.prepare_request(request)
    observation = native._observation(artifacts['stdout.json'], request, request_raw, output_dir,
                                      expected_selection, expected_manifest)
    need(wire(observation) == wire(capture['observation'])
         and wire(observation['selection']) == wire(expected_selection)
         and wire(observation['selected_message_manifest']) == wire(expected_manifest),
         'retained child stdout/selected messages differ from deterministic replay')
    consumer = observation['consumer']
    need(wire(consumer['claims']) == wire(native.CONSUMER_CLAIMS), 'consumer claim scalar types differ')
    need(all(type(consumer[key]) is int for key in ('input_bytes', 'input_local_tokens', 'consumer_calls')),
         'exact consumer byte/token/call integers required')
    need(set(consumer['allocation_store']) == {'path', 'profile', 'slots_before', 'slots_after',
         'mutable_rows_before', 'mutable_rows_after'}, 'closed owned allocation-store capture required')
    files = capture['output_artifacts']
    need(type(files) is list and [row.get('relative_path') for row in files] == ['request.json', 'stdout.json', 'stderr.log'],
         'complete fixed worker output custody required')
    for row in files:
        need(type(row) is dict and set(row) == {'relative_path', 'bytes', 'sha256'}, 'closed worker output pin required')
        raw = artifacts[row['relative_path']]
        need(type(row['bytes']) is int and row['bytes'] == len(raw) and row['sha256'] == sha(raw),
             'worker output artifact custody differs')
    dispatch = capture['native_dispatch']
    need(type(dispatch) is dict and set(dispatch) == {'module', 'method', 'path', 'sha256', 'actual_child_birth',
        'actual_process_invoked', 'native_shared_parent_lease_used', 'native_child_lease', 'inherited_environment', 'shell'},
        'closed historical native dispatch description required')
    need(dispatch['module'] == 'ipfs_accelerate_py.agent_supervisor.todo_daemon.supervisor_runtime'
         and dispatch['method'] == 'run_process_group_stream' and dispatch['path'] == str(native.RUNTIME_SOURCE)
         and dispatch['sha256'] == sha(native._read(native.RUNTIME_SOURCE, 256_000)),
         'retained native launcher source identity differs')
    need(dispatch['actual_process_invoked'] is True and dispatch['native_shared_parent_lease_used'] is True
         and dispatch['inherited_environment'] is False and dispatch['shell'] is False,
         'historical native dispatch boundary differs')
    lease = dispatch['native_child_lease']
    need(type(lease) is dict and set(lease) == {'cpu_slots', 'memory_mb', 'child_process_slots'}
         and all(type(lease[key]) is int and lease[key] == value for key, value in
             {'cpu_slots': 1, 'memory_mb': 256, 'child_process_slots': 1}.items()), 'retained native child reservation differs')
    birth = dispatch['actual_child_birth']
    need(type(birth) is dict and set(birth) == {'pid', 'start_time_ticks'}
         and all(type(birth[key]) is int and birth[key] > 0 for key in birth), 'bounded historical child birth required')
    from planning_permit import SCHEMA as PERMIT_SCHEMA,CLAIMS,planning_request_binding
    proof=capture['planning_admission']
    evidence_fields={'schema','scope','worker_mode','native_coordinator_claim_fenced_before_after',
        'single_use_owner_permit_consumed','worker_birth_acknowledged_before_stdin','native_job_binding','request_binding',
        'claim_binding_sha256','launch_binding_sha256','actual_worker_birth','provider_usage','actual_external_provider_invocations',*CLAIMS}
    need(type(proof) is dict and set(proof)==evidence_fields and proof['schema']==PERMIT_SCHEMA,
        'closed historical planning permit evidence required')
    need(proof['scope']=='planning-observation-only' and proof['worker_mode']=='localcapture'
        and all(proof[key] is value for key,value in CLAIMS.items()) and proof['provider_usage'] is None
        and type(proof['actual_external_provider_invocations']) is int and proof['actual_external_provider_invocations']==0,
        'planning evidence promotes unobserved dispatch, provider or proof authority')
    need(all(proof[key] is True for key in ('native_coordinator_claim_fenced_before_after','single_use_owner_permit_consumed',
        'worker_birth_acknowledged_before_stdin')),'actual native claim/permit/birth evidence required')
    request_binding=planning_request_binding(request)
    need(wire(proof['request_binding'])==wire(request_binding),'historical permit complete request binding differs')
    job=proof['native_job_binding']
    need(job['input_binding']['planning_request_binding']==request_binding and job['native_head']==request['expected_head']
        and job['input_binding_sha256']==sha(wire(job['input_binding'])),'historical native job/request input join differs')
    actual=proof['actual_worker_birth']
    need(type(actual) is dict and set(actual)=={'pid','start_time_ticks','parent_pid','boot_id','uid'}
        and all(type(actual[key]) is int and actual[key]>0 for key in ('pid','start_time_ticks','parent_pid'))
        and type(actual['boot_id']) is str and bool(actual['boot_id'])
        and actual['pid']==birth['pid'] and actual['start_time_ticks']==birth['start_time_ticks']
        and type(actual['uid']) is int and actual['uid']>=0,'native guard and retained child births differ')
    need(type(proof['claim_binding_sha256']) is str and re.fullmatch(r'[0-9a-f]{64}',proof['claim_binding_sha256'])
        and proof['launch_binding_sha256']==sha(wire(native.capture_launch_binding(output_dir))),
        'retained native claim or command/environment/producer evidence differs')
    return observation, (birth['pid'], birth['start_time_ticks'])

def validate_deliveries(*,output,contexts,deliveries,descriptor,artifacts,head,corpus,bodies,instructions):
    from planning_permit import planning_request_binding,SCHEMA,CLAIMS
    from planning_job import verify_historical_planning_report,OUTPUT_NAME,INPUT_NAME,FALSE as JOB_FALSE
    tasks={row['task_id']:row for row in contexts['tasks']};seen=set();births=set();counts={}
    need(deliveries['schema']=='terminal-planning-admitted-deliveries@1','selected deliveries schema differs')
    need(deliveries['native_local_metatasks_admitted']==8 and len(deliveries['deliveries'])==8,'eight distinct native admissions required')
    need(deliveries['original_benchmark_tasks_admitted'] is False and deliveries['full_supervisor_invoked'] is False,
        'native metatasks cannot promote original-task or full-supervisor authority')
    need(deliveries['isolated_fixture_authority'] is True and deliveries['actual_external_provider_invocations']==0
        and deliveries['provider_usage'] is None,'local fixture scope differs')
    for item in deliveries['deliveries']:
        task_id,mode=item['task_id'],item['delivery_mode'];key=(task_id,mode)
        need(task_id in tasks and mode in MODES and key not in seen,'complete unique task/mode dispatch required');seen.add(key)
        request=make_request(tasks[task_id],mode,0,descriptor,[])
        need(wire(request)==wire(item['request']) and request['expected_head']==head,'exact complete request differs')
        expected_input=input_binding(request=request,structural={'head':head},corpus=corpus,bodies=bodies,instructions=instructions)
        report=item['native_job'];job_binding=item['job_binding']
        need(report['job_binding']==job_binding and job_binding['input_binding']==expected_input,'native signed complete input differs')
        verify_historical_planning_report(report)
        prefix='jobs/'+task_id+'-'+mode
        need(artifacts[prefix+'/admission/planning-job.json']==wire(report),'retained native public report differs')
        need(artifacts[prefix+'/repository/'+INPUT_NAME]==wire(expected_input),'every signed original input byte must remain present')
        capture=item['capture'];worker_prefix='workers/'+task_id+'/'+mode
        leaf={name:artifacts[worker_prefix+'/'+name] for name in ('request.json','stdout.json','stderr.log')}
        observation,birth=validate_capture(output_dir=output/worker_prefix,request=request,capture=capture,artifacts=leaf)
        need(birth not in births,'historical worker birth reused');births.add(birth)
        proof=capture['planning_admission']
        need(proof['schema']==SCHEMA and proof['scope']=='planning-observation-only' and proof['worker_mode']=='localcapture',
            'distinct native planning observation evidence required')
        need(all(proof[key] is value for key,value in CLAIMS.items()) and proof['native_job_binding']==job_binding
            and proof['request_binding']==planning_request_binding(request),'native permit request/job evidence differs')
        need(proof['native_coordinator_claim_fenced_before_after'] is True and proof['single_use_owner_permit_consumed'] is True
            and proof['worker_birth_acknowledged_before_stdin'] is True,'native claim/permit/birth evidence required')
        need(proof['actual_worker_birth']['pid']==birth[0] and proof['actual_worker_birth']['start_time_ticks']==birth[1],
            'native guard and actual child births differ')
        artifact=item['observation_artifact'];raw=artifacts[prefix+'/repository/'+OUTPUT_NAME];observed=json.loads(raw)
        need(artifact['bytes']==len(raw) and artifact['sha256']==sha(raw),'created observation byte binding differs')
        need(observed['input_binding']==expected_input and observed['input_binding_sha256']==sha(wire(expected_input))
            and observed['native_head']==head and observed['observed_input_tokens']==observation['selection']['input_tokens'],
            'declared planning observation loses complete input/head/budget')
        need(observed['observations']==[{'capture_sha256':sha(wire(capture)),'capture_bytes':len(wire(capture)),
            'capture_origin_authenticated_by_writer':False}] and all(observed[key] is False for key in JOB_FALSE),
            'planning observation promotes capture or original-task authority')
        need(item['acceptance_pending'] is True and item['owner_current_before_and_after'] is True,'acceptance must remain pending')
        counts.setdefault(task_id,{})[mode]=observation['selection']['input_tokens']
    need(seen=={(key,mode) for key in tasks for mode in MODES},'full four-task paired delivery inventory required')
    expanded=sum(row['expanded'] for row in counts.values());adaptive=sum(row['adaptive'] for row in counts.values())
    need(all(row['adaptive']<=row['expanded'] for row in counts.values()),'adaptive delivery increases a task input cost')
    return {'retained_calls':8,'distinct_historical_births':len(births),'per_task_local_input_tokens':counts,
        'expanded_local_input_tokens':expanded,'adaptive_local_input_tokens':adaptive,'local_input_tokens_saved':expanded-adaptive,
        'saved_fraction':(expanded-adaptive)/expanded,'provider_usage':None,'provider_token_savings_qualified':False,
        'native_signatures_verified_as_historical_fixture_evidence':True,'current_dispatch_authority_recreated':False}

def fault_precondition(name,*,output,result,result_raw):
    need(type(name) is str and Path(name).name==name and name not in {'.','..'}
        and name.endswith('-fault-report.json'),'owned fault report name required')
    raw=read(ROOT/name,1024**2);fault=json.loads(raw)
    fields={'schema','qualified','selected_run','selected_result_sha256','native_head','controls','artifact_pins',
        'actual_extra_worker_children','actual_external_provider_invocations','provider_usage','source_body_execution',
        'private_authority_destroyed','original_source_restored',*FALSE}
    need(type(fault) is dict and set(fault)==fields and wire(fault)==raw,'closed canonical preceding native faults required')
    need(fault['schema']=='terminal-planning-admission-faults@1' and fault['qualified'] is True,'qualified preceding native faults required')
    need(fault['selected_run']==output.name and fault['selected_result_sha256']==sha(result_raw)
        and fault['native_head']==result['native_head'],'preceding faults must bind exact result/head')
    need(type(fault['actual_extra_worker_children']) is int and fault['actual_extra_worker_children']==1
        and type(fault['actual_external_provider_invocations']) is int and fault['actual_external_provider_invocations']==0
        and fault['provider_usage'] is None and fault['source_body_execution'] is False
        and fault['private_authority_destroyed'] is True and fault['original_source_restored'] is True
        and all(fault[key] is False for key in FALSE),'preceding native fault scope differs')
    cases=('request_changed','output_exists','claim_released','source_changed_after_spawn')
    expected=[key+suffix for key in cases for suffix in ('','-replay')]
    need(type(fault['controls']) is list and len(fault['controls'])==8
        and [row['case'] for row in fault['controls']]==expected,'all eight ordered native fault controls required')
    for row in fault['controls']:
        need(set(row)=={'case','rejected','exception_class','message','actual_child_spawned','original_source_restored'}
            and row['rejected'] is True and row['original_source_restored'] is True and type(row['exception_class']) is str
            and bool(row['exception_class']) and type(row['message']) is str and bool(row['message'])
            and row['actual_child_spawned'] is (row['case']=='source_changed_after_spawn'),'native fault refusal or process scope differs')
    need(fault['controls'][6]['exception_class']=='StaleCodebaseError','native exit owner stale-source refusal required')
    label=name.removesuffix('-fault-report.json');prefix=ROOT/(label+'-artifacts');names=[];acquired={}
    need(type(fault['artifact_pins']) is list and 12<=len(fault['artifact_pins'])<=40,'complete bounded public native fault artifacts required')
    for row in fault['artifact_pins']:
        need(type(row) is dict and set(row)=={'path','bytes','sha256'},'closed fault artifact pin required')
        path=Path(row['path']);need(path.is_absolute() and prefix in path.parents and '.git' not in path.parts
            and path.resolve(strict=True)==path,'owned public fault artifact required')
        relative=path.relative_to(prefix).parts
        need(relative[0] in cases and ((len(relative)==3 and
            ((relative[1]=='repository' and relative[2] in {'input-binding.json','validate-planning-observation.py'})
             or (relative[1]=='admission' and relative[2]=='planning-job.json')
             or (relative[0]=='source_changed_after_spawn' and relative[1]=='capture' and relative[2] in WORKER_LEAVES)))
            or (relative==('source_changed_after_spawn','refused-candidate-capture.json'))),'closed known public fault leaf required')
        need(str(path) not in names and type(row['bytes']) is int and 0<=row['bytes']<=32*1024**2,'unique bounded fault artifact required')
        names.append(str(path))
        from worker_capture import _read
        body=_read(path,32*1024**2,empty=row['bytes']==0)
        need(len(body)==row['bytes'] and sha(body)==row['sha256'],'preceding native fault artifact changed')
        acquired[path.relative_to(prefix).as_posix()]=body
    actual=set()
    for path in prefix.rglob('*'):
        if '.git' in path.relative_to(prefix).parts:continue
        need(not path.is_symlink() and path.resolve(strict=True)==path,'fault artifact symlink refused')
        if path.is_file():actual.add(str(path))
    need(names==sorted(names) and set(names)==actual,'complete sorted fault artifact inventory differs')
    required={case+'/'+leaf for case in cases for leaf in (
        'repository/input-binding.json','repository/validate-planning-observation.py','admission/planning-job.json')}
    source_case='source_changed_after_spawn'
    required|={source_case+'/capture/'+leaf for leaf in WORKER_LEAVES-{'router-allocation.duckdb.wal'}}
    required.add(source_case+'/refused-candidate-capture.json')
    need(required<=set(acquired),'all native fault job and source-candidate artifacts required')

    # Bind each historical fault job to the selected main run's exact original
    # public request.  This is retained-data replay, never a new live permit.
    main_pins={row['relative_path']:row for row in result['artifact_pins']}
    need('deliveries.json' in main_pins,'selected main deliveries artifact required')
    main_raw=read(output/'deliveries.json',32*1024**2);main_pin=main_pins['deliveries.json']
    need(type(main_pin['bytes']) is int and len(main_raw)==main_pin['bytes'] and sha(main_raw)==main_pin['sha256'],
        'selected main request artifact changed')
    main=json.loads(main_raw)
    need(wire(main)==main_raw and main.get('schema')=='terminal-planning-admitted-deliveries@1'
        and type(main.get('deliveries')) is list,'canonical selected main deliveries required')
    selected=[row['request'] for row in main['deliveries'] if row.get('task_id')=='headless-terminal'
        and row.get('delivery_mode')=='adaptive']
    need(len(selected)==1,'one exact selected headless adaptive request required')
    request=selected[0]
    from worker_capture import _request
    _request(request)
    need(wire(request['expected_head'])==wire(result['native_head']) and request['delivery_mode']=='adaptive'
        and request['session_id']=='headless-terminal:adaptive'
        and request['request_id']=='headless-terminal:adaptive:0','selected main request/head identity differs')
    corpus,bodies,instructions,_=inputs()
    expected_input=input_binding(request=request,structural={'head':result['native_head']},corpus=corpus,
        bodies=bodies,instructions=instructions)
    from planning_job import verify_historical_planning_report,VALIDATOR
    reports={}
    for case in cases:
        job_raw=acquired[case+'/admission/planning-job.json'];report=json.loads(job_raw)
        need(wire(report)==job_raw,'canonical historical fault job report required')
        verified=verify_historical_planning_report(report)
        binding=verified['job_binding']
        need(binding['task_key']=='fault-'+case.replace('_','-')
            and wire(binding['native_head'])==wire(result['native_head'])
            and wire(binding['input_binding'])==wire(expected_input),
            'historical fault job must preserve exact original request, instructions, sources and head')
        need(acquired[case+'/repository/input-binding.json']==wire(expected_input)
            and acquired[case+'/repository/validate-planning-observation.py']==VALIDATOR.encode('utf-8'),
            'historical signed fault input or fixed validator differs')
        need(binding['job_repository']==str(prefix/case/'repository'),
            'historical fault job repository path differs')
        reports[case]=report
    candidate_raw=acquired[source_case+'/refused-candidate-capture.json'];candidate=json.loads(candidate_raw)
    need(wire(candidate)==candidate_raw,'canonical refused source-candidate capture required')
    leaves={leaf:acquired[source_case+'/capture/'+leaf] for leaf in ('request.json','stdout.json','stderr.log')}
    _,birth=validate_capture(output_dir=prefix/source_case/'capture',request=request,capture=candidate,artifacts=leaves)
    need(wire(candidate['planning_admission']['native_job_binding'])==wire(reports[source_case]['job_binding']),
        'refused source candidate belongs to a different signed native fault job')
    need(birth[0]>0 and birth[1]>0,'retained source-candidate historical child birth required')
    return raw,{'relative_path':name,'bytes':len(raw),'sha256':sha(raw)}



def verify(output, fault_report):
    resource.setrlimit(resource.RLIMIT_CPU, (480,480))
    resource.setrlimit(resource.RLIMIT_AS, (8*1024**3,8*1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE, (32*1024**2,32*1024**2))
    output = Path(output)
    need(output.resolve(strict=True) == output and output.parent == ROOT, 'canonical owned completed worker run required')
    result_raw = read(output/'result.json', 1024**2)
    result = json.loads(result_raw)
    validate_result(result)
    need(wire(result) == result_raw, 'canonical completed worker result required')
    artifacts = artifact_check(output, result)
    fault_raw, fault_pin = fault_precondition(fault_report, output=output, result=result, result_raw=result_raw)
    corpus, bodies, instructions, lineage = inputs()
    need(wire(corpus) == artifacts['corpus-manifest.json'] and wire(lineage) == artifacts['lineage.json'], 'sealed worker public input lineage differs')
    for task, raw in instructions.items():
        need(read(output/'instructions'/task/'instruction.md',8192) == raw, 'complete copied instruction differs')
    structural = json.loads(artifacts['structural-report.json'])
    from native_structural_ir import verify_structural_ir, _scheduler
    verify_structural_ir(repository=output/'source-repository', output=output/'structural', expected=structural)
    for source in structural['sources']:
        need(read(output/'source-repository'/source['path'],8192) == bodies[source['path']], 'current complete copied source differs')
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import ResourceLane
    from ipfs_datasets_py.logic.software_contracts.codebase_ir import CodebaseIRManifest
    from native_capsules import verify_native_capsules
    from capsule_codec import build_capsule_codec
    from token_cost_review import load_tokenizer
    from benchmarks.agent_supervisor.container_coding import codebase_ir_metadata as metadata_api
    from benchmarks.agent_supervisor.container_coding.terminal_codebase_supervisor_fixture import reconstruct_terminal_codebase_metadata_records
    from metadata_projections import _wire as metadata_wire
    from admission_metadata import build_records
    native = json.loads(artifacts['native-capsules.json'])
    codecs = json.loads(artifacts['codec-views.json'])
    metadata = json.loads(artifacts['metadata-report.json'])
    head = _head(structural['head'])
    with _scheduler().acquire(ResourceLane.VALIDATION,cpu_slots=1,memory_mb=1024,child_process_slots=1,
            timeout=30,request_id='terminal-context-worker:cold-retained-replay') as lease:
        check_lease(lease)
        verify_native_capsules(CodebaseIRManifest.from_dict(structural['manifest']), head, native)
        for source in structural['sources']:
            for arm in ('minified','aliased'):
                regenerated = build_capsule_codec(bodies[source['path']],source['path'],source['source_cid'],structural['head'],aliases=arm=='aliased')
                need(wire(codecs[source['path']][arm]) == wire(regenerated), 'complete original source codec replay differs')
        tokenizer, descriptor = load_tokenizer(json.loads(artifacts['tokenizer.json']))
        with lease.acquire_child(lane=ResourceLane.PERSISTENCE,cpu_slots=1,memory_mb=256,child_process_slots=1,
                timeout=20,request_id='terminal-context-worker:cold-owned-metadata') as child:
            check_lease(child)
            reopened = metadata_api.validate_codebase_ir_metadata(output=output/'metadata',expected=metadata['native_metadata'],fresh_process=True)
        restored = {family:[json.loads(line)['payload'] for line in read(output/'metadata'/entry['relative_path'],(32*1024**2)).splitlines()]
                    for family,entry in reopened['exports'].items()}
        recovered = reconstruct_terminal_codebase_metadata_records(restored)
        records = build_records(structural=structural,bodies=bodies,instructions=instructions,corpus=corpus,native=native,codecs=codecs,lineage=lineage)
        need(metadata_wire(recovered) == metadata_wire(records) and sha(metadata_wire(recovered)) == metadata['records_sha256'],
             'complete cold DuckDB/DuckLake record reconstruction differs')
        contexts = build_contexts(output=output,structural=structural,corpus=corpus,instructions=instructions,native=native,
            metadata=metadata,tokenizer=tokenizer,descriptor=descriptor,lease=lease)
        need(wire(contexts) == artifacts['contexts.json'], 'deterministic complete current source contexts differ')
        replay = validate_deliveries(output=output,contexts=contexts,deliveries=json.loads(artifacts['deliveries.json']),
                                     descriptor=descriptor,artifacts=artifacts,head=head.to_dict(),corpus=corpus,bodies=bodies,instructions=instructions)
    need(wire(result['native_head']) == wire(head.to_dict()) and wire(result['native_capsule_inventory']) == wire(native['complete_inventory'])
         and wire(result['metadata_original_record_counts']) == wire(metadata['family_counts']), 'worker result head/capsule/metadata bindings differ')
    verify_structural_ir(repository=output/'source-repository',output=output/'structural',expected=structural)
    need(inputs()[3] == lineage and read(output/'result.json',1024**2) == result_raw, 'selected worker result/lineage changed during replay')
    end_fault_raw,end_fault_pin = fault_precondition(fault_report,output=output,result=result,result_raw=result_raw)
    need(artifact_check(output,result) == artifacts and end_fault_raw == fault_raw and end_fault_pin == fault_pin,
         'worker artifacts or preceding fault report changed during cold replay')
    return {'schema':'terminal-planning-admission-cold-replay@1','qualified':True,'selected_run':output.name,
        'selected_result_sha256':sha(result_raw),'selected_native_head':head.to_dict(),
        'selected_artifact_pins_sha256':sha(wire(result['artifact_pins'])),'preceding_fault_report':fault_pin,
        'qualified_faults_verified_before_positive_replay':True,'current_native_owner_observed_before_and_after':True,
        'complete_duckdb_ducklake_reopened':True,'complete_current_contexts_rebuilt':True,
        'retained_worker_observations_verified':replay['retained_calls'],'cost_observation':replay,
        'retained_births_checked_as_current_authority':False,'new_worker_children_spawned':0,
        'all_selected_payloads_budgets_and_history_replayed':True,'provider_usage':None,
        'actual_external_provider_invocations':0,'source_body_execution':False,**FALSE}


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run',required=True);parser.add_argument('--report',required=True)
    parser.add_argument('--fault-report',required=True);args=parser.parse_args()
    for name in (args.run,args.report,args.fault_report):
        need(name and Path(name).name == name and name not in {'.','..'}, 'owned local names required')
    report=verify(ROOT/args.run,args.fault_report);write(ROOT/args.report,report)
    print(json.dumps({'qualified':True,'retained_observations':8,'new_worker_children_spawned':0}))
