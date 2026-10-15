"""Cold source/metadata replay; declarations never become task or proof authority."""
import argparse
import json
import math
from pathlib import Path
import resource
import stat
from constraint_io import ROOT,FALSE,inputs,read,write,wire,sha
from constraint_run import POLICY,FILES,build_constraint_materials,metadata_records,check_lease
from constraint_lean import LEAN_LABELS
LEAN_LEAVES={'report.json'}|{label+suffix for label in LEAN_LABELS for suffix in ('.lean','-process.json')}

def need(condition,message):
    if not condition:raise ValueError(message)

def validate_result(result):
    fields={'schema','completed','policy','native_head','source_count','task_count','authored_case_count',
        'accepted_authored_cases','rejected_authored_cases','all_authored_case_expectations_matched','new_optimizer_updates',
        'external_provider_calls','source_body_execution','metadata_original_record_counts','native_capsule_inventory',
        'artifact_pins','seconds','peak_rss_kib',*FALSE}
    need(type(result) is dict and set(result)==fields,'closed complete finite constraint result required')
    need(result['schema']=='terminal-typed-scheduler-constraint-experiment@1' and result['completed'] is True
        and wire(result['policy'])==wire(POLICY),'complete original constraint policy required')
    for key,count in dict(source_count=5,task_count=4,new_optimizer_updates=0,external_provider_calls=0).items():
        need(type(result[key]) is int and result[key]==count,'exact work counter required')
    for key in ('authored_case_count','accepted_authored_cases','rejected_authored_cases'):
        need(type(result[key]) is int and 0<=result[key]<=256,'bounded exact authored-case counters required')
    need(20<=result['authored_case_count']<=256 and result['accepted_authored_cases']>0 and result['rejected_authored_cases']>0
        and result['accepted_authored_cases']+result['rejected_authored_cases']==result['authored_case_count']
        and result['all_authored_case_expectations_matched'] is True,'complete matched authored-case accounting required')
    need(result['source_body_execution'] is False and all(result[key] is False for key in FALSE),'result promotes unobserved authority')
    from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead
    need(wire(CodebaseHead.from_dict(result['native_head']).to_dict())==wire(result['native_head']),'complete canonical native head required')
    need(type(result['seconds']) in {int,float} and math.isfinite(result['seconds']) and result['seconds']>=0
        and type(result['peak_rss_kib']) is int and result['peak_rss_kib']>=0,'finite nonnegative diagnostics required')
    for key in ('metadata_original_record_counts','native_capsule_inventory'):
        need(type(result[key]) is dict and result[key] and all(type(k) is str and type(v) is int and v>=0
            for k,v in result[key].items()),'closed nonnegative metadata counter map required')

def artifact_check(output,result):
    need(output.is_absolute() and output.resolve(strict=True)==output and output.parent==ROOT,'canonical owned selected run required')
    pins=result['artifact_pins'];need(type(pins) is list and len(pins)==len(FILES)+len(LEAN_LEAVES),'complete bounded public artifact pins required')
    acquired={};names=[];total=0
    from worker_capture import _read
    for row in pins:
        need(type(row) is dict and set(row)=={'relative_path','bytes','sha256'},'closed public artifact pin required')
        name=row['relative_path'];need(type(name) is str and '\\' not in name and all(ord(c)>=32 for c in name),'canonical artifact text required')
        path=Path(name);need(not path.is_absolute() and path.as_posix()==name and not set(path.parts)&{'.','..','.git'},'canonical public artifact path required')
        need(name in FILES or (len(path.parts)==2 and path.parts[0]=='lean' and path.parts[1] in LEAN_LEAVES),
            'closed public core/Lean artifact scope required')
        need(name not in names and type(row['bytes']) is int and 0<=row['bytes']<=32*1024**2,'unique bounded artifact pin required')
        raw=_read(output/path,32*1024**2,empty=row['bytes']==0)
        need(len(raw)==row['bytes'] and sha(raw)==row['sha256'],'selected public artifact changed')
        total+=len(raw);need(total<=128*1024**2,'total selected artifact bound exceeded')
        acquired[name]=raw;names.append(name)
    need(names==sorted(names) and set(names)==set(FILES)|{'lean/'+name for name in LEAN_LEAVES},'complete sorted core and Lean inventory required')
    actual=set()
    need((output/'lean').is_dir() and not (output/'lean').is_symlink()
        and (output/'lean').resolve(strict=True)==output/'lean','canonical existing owned Lean directory required')
    for path in (output/'lean').rglob('*'):
        info=path.lstat();need(not path.is_symlink() and path.resolve(strict=True)==path,'Lean artifact symlink refused')
        if not stat.S_ISDIR(info.st_mode):
            need(stat.S_ISREG(info.st_mode) and info.st_nlink==1,'single-link regular Lean artifact required')
            actual.add(path.relative_to(output).as_posix())
    need(actual=={name for name in names if name.startswith('lean/')},'complete actual Lean artifact inventory differs')
    return acquired

def fault_precondition(name,*,output,result,result_raw):
    need(type(name) is str and Path(name).name==name and name not in {'.','..'},'owned preceding fault report required')
    raw=read(ROOT/name,1024**2);fault=json.loads(raw)
    expected={'schema','qualified','selected_run','selected_result_sha256','native_head','controls','source_restored',
        'source_body_execution','external_provider_calls','new_optimizer_updates',*FALSE}
    need(type(fault) is dict and set(fault)==expected and wire(fault)==raw,'closed canonical preceding intent faults required')
    need(fault['schema']=='terminal-typed-constraint-faults@1' and fault['qualified'] is True
        and fault['selected_run']==output.name and fault['selected_result_sha256']==sha(result_raw)
        and wire(fault['native_head'])==wire(result['native_head']),'preceding qualified faults must bind selected result/head')
    need(fault['source_restored'] is True and fault['source_body_execution'] is False and all(fault[key] is False for key in FALSE)
        and type(fault['external_provider_calls']) is int and fault['external_provider_calls']==0
        and type(fault['new_optimizer_updates']) is int and fault['new_optimizer_updates']==0,'native fault scope differs')
    cases=['changed_instruction','changed_contract_bound','forged_case_evaluation','projection_authority_promoted','source_changed_at_exit']
    need(type(fault['controls']) is list and len(fault['controls'])==len(cases),'all exact native fault controls required')
    for row in fault['controls']:
        need(type(row) is dict and set(row)=={'case','rejected','exception_class','message'} and row['rejected'] is True
            and type(row['exception_class']) is str and row['exception_class'] and type(row['message']) is str and row['message'],
            'closed exact refusal observation required')
    need([row['case'] for row in fault['controls']]==cases,'all exact ordered native fault controls required')
    need(fault['controls'][-1]['exception_class']=='StaleCodebaseError','native owner exit refusal required')
    return raw,{'relative_path':name,'bytes':len(raw),'sha256':sha(raw)}

def verify(output,fault_name):
    resource.setrlimit(resource.RLIMIT_CPU,(480,480));resource.setrlimit(resource.RLIMIT_AS,(8*1024**3,8*1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE,(32*1024**2,32*1024**2))
    result_raw=read(output/'result.json',1024**2);result=json.loads(result_raw);validate_result(result)
    need(wire(result)==result_raw,'canonical selected result required');acquired=artifact_check(output,result)
    fault_raw,fault_pin=fault_precondition(fault_name,output=output,result=result,result_raw=result_raw)
    corpus,bodies,instructions,lineage=inputs()
    need(wire(corpus)==acquired['corpus-manifest.json'] and wire(lineage)==acquired['lineage.json'],'selected public input lineage differs')
    for key,raw in instructions.items():need(read(output/'instructions'/key/'instruction.md',8192)==raw,'whole instruction differs')
    for key,raw in bodies.items():need(read(output/'source-repository'/key,8192)==raw,'whole copied source differs')
    structural=json.loads(acquired['structural-report.json'])
    from native_structural_ir import verify_structural_ir,_scheduler
    verify_structural_ir(repository=output/'source-repository',output=output/'structural',expected=structural)
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import ResourceLane
    from ipfs_datasets_py.logic.software_contracts.codebase_ir import CodebaseIRManifest
    from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead
    from native_capsules import verify_native_capsules
    from capsule_codec import build_capsule_codec
    from constraint_lean import validate_constraint_lean_evidence
    from metadata_projections import _wire as metadata_wire
    from benchmarks.agent_supervisor.container_coding import codebase_ir_metadata as native_metadata
    from benchmarks.agent_supervisor.container_coding.terminal_codebase_supervisor_fixture import reconstruct_terminal_codebase_metadata_records
    native=json.loads(acquired['native-capsules.json']);codecs=json.loads(acquired['codec-views.json'])
    lean=json.loads(acquired['lean-evidence.json']);metadata=json.loads(acquired['metadata-report.json'])
    with _scheduler().acquire(ResourceLane.VALIDATION,cpu_slots=1,memory_mb=1024,child_process_slots=1,
            timeout=30,request_id='terminal-typed-constraints:cold-replay') as lease:
        verify_native_capsules(CodebaseIRManifest.from_dict(structural['manifest']),CodebaseHead.from_dict(structural['head']),native)
        for source in structural['sources']:
            for arm in ('minified','aliased'):
                rebuilt=build_capsule_codec(bodies[source['path']],source['path'],source['source_cid'],structural['head'],aliases=arm=='aliased')
                need(wire(rebuilt)==wire(codecs[source['path']][arm]),'complete byte codec replay differs')
        built=build_constraint_materials(output=output,structural=structural,corpus=corpus,bodies=bodies,instructions=instructions,lease=lease)
        for key,name in [('inventories','intent-inventories.json'),('grounding','source-grounding.json'),('projections','intent-logic-projections.json'),('structural_context','structural-context.json'),('contract','scheduler-contract.json'),('constraint_projections','constraint-projections.json'),('cases','authored-cases.json'),('evaluations','case-evaluations.json'),('theory','lean-theory.json')]:
            need(wire(built[key])==acquired[name],'deterministic current-source intent/grounding/projection replay differs')
        validate_constraint_lean_evidence(lean,theory=built['theory'],output=output/'lean')
        records=metadata_records(structural=structural,bodies=bodies,instructions=instructions,corpus=corpus,native=native,
            codecs=codecs,lineage=lineage,built=built,lean=lean)
        with lease.acquire_child(lane=ResourceLane.PERSISTENCE,cpu_slots=1,memory_mb=256,child_process_slots=1,
                timeout=20,request_id='terminal-typed-constraints:cold-metadata') as child:
            check_lease(child)
            reopened=native_metadata.validate_codebase_ir_metadata(output=output/'metadata',expected=metadata['native_metadata'],fresh_process=True)
        restored={family:[json.loads(line)['payload'] for line in read(output/'metadata'/entry['relative_path'],32*1024**2).splitlines()]
            for family,entry in reopened['exports'].items()}
        recovered=reconstruct_terminal_codebase_metadata_records(restored)
        need(metadata_wire(recovered)==metadata_wire(records) and sha(metadata_wire(recovered))==metadata['records_sha256'],
            'complete fresh-process metadata reconstruction differs')
    need(wire(result['native_head'])==wire(structural['head']) and wire(result['metadata_original_record_counts'])==wire(metadata['family_counts'])
        and wire(result['native_capsule_inventory'])==wire(native['complete_inventory']),'result source and metadata inventories differ')
    need(result['authored_case_count']==len(built['cases'])
        and result['accepted_authored_cases']==sum(row['evaluation']['evaluation_passed'] for row in built['evaluations'])
        and result['rejected_authored_cases']==sum(not row['evaluation']['evaluation_passed'] for row in built['evaluations']),
        'selected result counters must match every reconstructed authored case')
    verify_structural_ir(repository=output/'source-repository',output=output/'structural',expected=structural)
    end_fault,end_pin=fault_precondition(fault_name,output=output,result=result,result_raw=result_raw)
    need(artifact_check(output,result)==acquired and read(output/'result.json',1024**2)==result_raw
        and end_fault==fault_raw and end_pin==fault_pin and inputs()[3]==lineage,'selected evidence changed during cold replay')
    return {'schema':'terminal-typed-constraints-cold-replay@1','qualified':True,'selected_run':output.name,
        'selected_result_sha256':sha(result_raw),'selected_native_head':structural['head'],
        'selected_artifact_pins_sha256':sha(wire(result['artifact_pins'])),'preceding_fault_report':fault_pin,
        'qualified_faults_verified_before_positive_replay':True,'complete_metadata_reopened':True,
        'current_owner_entry_and_exit_observed':True,'intent_inventories_and_grounding_rebuilt':True,
        'logic_family_projections_rebuilt':True,'lean_evidence_verified_as_historical_finite_model_proofs':True,
        'authored_cases_replayed':len(built['cases']),'all_authored_case_expectations_matched':True,
        'original_task_satisfaction_verified':False,
        'new_lean_compiler_invocations':0,'external_provider_calls':0,'source_body_execution':False,**FALSE}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run',required=True);parser.add_argument('--report',required=True)
    parser.add_argument('--fault-report',required=True);args=parser.parse_args()
    for name in (args.run,args.report,args.fault_report):
        need(Path(name).name==name and name not in {'.','..'},'owned local names required')
    result=verify(ROOT/args.run,args.fault_report);write(ROOT/args.report,result);print(json.dumps({'qualified':True,'cold_replay':True}))
