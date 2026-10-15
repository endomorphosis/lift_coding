"""Independent source-only review of the fixed ordinary bounded pytest runner.

Only stdlib parsing/hashing of inert source and small pinned evidence occurs.
The runner, candidate, helper and pytest are never imported or executed.
"""
import ast
import datetime
import hashlib
import json
import os
from pathlib import Path

W=Path('/home/barberb/lift_coding')
ROOT=Path(__file__).resolve().parent
RUNNER=W/'maintenance/ranker-objective-prefix-controls-20261005-01/run_controls_01.py'
EXPECTED=(14111,'d29bf73dd148ca084577877124f9443a2cd44e93579a05583d9625c03e7d31ef')

def pin(path):
    path=Path(path);assert path.resolve(strict=True)==path and not path.is_symlink()
    before=path.stat();raw=path.read_bytes();after=path.stat()
    assert (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns)
    assert len(raw)==before.st_size<=16*1024**2
    return raw,{'path':str(path),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}

def main():
    raw,reviewed=pin(RUNNER);assert (len(raw),reviewed['sha256'])==EXPECTED
    tree=ast.parse(raw);text=raw.decode();functions={n.name for n in ast.walk(tree) if isinstance(n,ast.FunctionDef)}
    assert {'main','child_limits','proof_census','checkout_guards'}<=functions
    required=["h['validate_guard_union'](request)","proof['request'] == plan['native_guard_request']",
      "seal['review'] in seal['files']","seal['regular_file_bytes'] == sum(r['bytes'] for r in seal['files'])",
      "hashlib.sha256(inventory_wire).hexdigest() == seal['file_inventory_sha256']",
      "passed_source_only_narrow_helper_schema_and_literal_fix","start_new_session=True, preexec_fn=child_limits",
      "os.killpg(process.pid, signal.SIGKILL)","process.wait(timeout=5)","len(output) + len(block) <= 65536",
      "resource.RLIMIT_CPU, (20, 20)","resource.RLIMIT_AS, (1024**3, 1024**3)",
      "resource.RLIMIT_FSIZE, (1024**2, 1024**2)","--noconftest","no:cacheprovider",
      "'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1'","len(cases) == 20","supervisor_lease_claimed': False",
      "kernel_semantic_equivalence_proved': False","'proof_authority', 'execution_authority', 'completion_authority', 'planner_activation'"]
    assert all(item in text for item in required) and text.count('proof_census()')==3
    gate_path=W/'maintenance/ranker-objective-prefix-compiler-source-review-20261005-02/review-receipt.json'
    gate_raw,gate_pin=pin(gate_path);assert gate_pin['bytes']==10164 and gate_pin['sha256']=='1f8c34ff56fa29b97e13af329cedfd591b4c73f7059cf9cc7192127a5b2f46fa'
    gate=json.loads(gate_raw);assert gate['status']=='passed_source_only_narrow_helper_schema_and_literal_fix' and gate['findings']==[]
    inputs=[reviewed,gate_pin]
    for row in gate['candidate_pins']:
        candidate_raw,actual=pin(row['path']);assert actual==row;inputs.append(actual)
        if Path(row['path']).name=='test_objective_prefix_compiler.py':
            tests=ast.parse(candidate_raw);names=[n.name for n in tests.body if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')]
            assert len(names)==20 and {name[5:7] for name in names}=={f'{i:02d}' for i in range(1,21)}
    q=W/'qualification/codebase_ir/ranker-objective-container-core-candidate-20261005-02'
    request_raw,request_pin=pin(q/'preparation/request-v3.json');request=json.loads(request_raw)
    strict={r['path']:r for r in request['strict_old_inputs']};live={r['path']:r for r in request['protected_live_sources']}
    assert len(strict)==len(request['strict_old_inputs'])==2421 and len(live)==4 and all(strict[path]==row for path,row in live.items())
    inputs.append(request_pin)
    seal_raw,seal_pin=pin(q/'file-only-seal-01.json');seal=json.loads(seal_raw)
    assert len(seal['files'])==seal['regular_file_count']==34 and sum(r['bytes'] for r in seal['files'])==seal['regular_file_bytes']==11290575
    assert hashlib.sha256(json.dumps(seal['files'],sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()).hexdigest()==seal['file_inventory_sha256']
    inputs.append(seal_pin)
    own_raw,own=pin(Path(__file__).resolve())
    receipt={'schema':'ranker-objective-prefix-independent-control-runner-source-review@1','status':'passed_source_only','findings':[],
      'reviewed_source':reviewed,'reviewer':own,'reviewed_input_pins':inputs,'created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'candidate_or_runner_or_helper_imports_or_execution':0,'test_native_model_metadata_or_publication_jobs':0,
      'reviewed_controls':['Externally SHA-pinned own source and closed plan; exact actual candidate gate/status and all four source-v2/root-doc roles.',
       'Original source/bindings byte pins; actual request joined to qualified proof, exact inherited2421+4 union, canonical34-file inventory, no exclusions or aliases, complete census before/after.',
       'Exact held Python source copies, child-only audited candidate import; bytecode/cache/entrypoint autoload/conftest disabled and addopts cleared.',
       'Separate ordinary pytest process session:20s CPU/45s wall/1GiB address space/1MiB file/64KiB stdout, process-group kill and5s wait on closure.',
       'Passing batch requires return0 plus one JUnit suite with exactly20 distinct numbered groups, no failures/errors/skips or testcase child outcomes.',
       'Historical/candidate input bodies and original root/child HEAD/index read back after child cleanup; partial stdout/JUnit, return code, error and cleanup retained in failure receipt.',
       'No supervisor lease/native proof claimed; all four authority flagsfalse, taskunknown and governing exitsOPEN.'],
      'limits':['This gate executes no target source, runner, helper or pytest. ROOT must run the exact reviewed runner with the actual closed plan.',
       'test_groups_passed is the accepted batch count:20 only after the entire batch and cleanup pass, otherwise0. Individual failures remain in bounded stdout/JUnit.',
       'Ordinary host tests do not establish CPython/Float/full objective/gradient/training equivalence or new kernel-qualified queries.'],
      'proof_authority':False,'execution_authority':False,'completion_authority':False,'planner_activation':False,
      'full_task_satisfaction':'unknown','all32_governing_RPI_exits':'OPEN','official_benchmark_score':None}
    out=ROOT/'review-receipt.json';body=(json.dumps(receipt,sort_keys=True,indent=2)+'\n').encode()
    with out.open('xb') as stream:stream.write(body);stream.flush();os.fsync(stream.fileno())
    print(json.dumps({'review':pin(out)[1],'reviewer':own,'status':receipt['status']}))

if __name__=='__main__':main()
