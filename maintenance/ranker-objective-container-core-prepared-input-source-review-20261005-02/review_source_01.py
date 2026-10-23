"""Independent source/AST review of the unexecuted prepared-input successor02."""
import ast
import datetime
import hashlib
import json
import os
from pathlib import Path
import stat

W=Path('/home/barberb/lift_coding')
P=W/'maintenance/ranker-objective-container-core-input-review-20261005-02'
Q=W/'qualification/codebase_ir/ranker-objective-container-core-candidate-20261005-02'
OUT=W/'maintenance/ranker-objective-container-core-prepared-input-source-review-20261005-02'
EXPECTED={
 P/'review_inputs_01.py':(9655,'fc8824a8d7e7aac63bfe729b758eec7d90159ab67c3db667767d6cad7586d482'),
 P/'review_inputs_02.py':(11732,'50adfa733b6b12d54c9c4d1f83c4e079782b298b4af047a697b750395595e47c'),
 Q/'container_core_file_helpers_01.py':(17601,'815bec62dd2c8de4073b389dbdf62827c4a639d4f6a3e08e5e79ef83ccffff3a'),
 W/'maintenance/ranker-objective-container-core-tooling-source-review-20261005-02/review-receipt.json':(9173,'bb1f7df2dd76f37349480094cdf3181d93e53b5886a263bca4fc3bc3b0f57b4e'),
 W/'maintenance/ranker-objective-container-core-patch-source-review-20261005-02/review-receipt.json':(5852,'1cdfea8f580bc113a190a56720eef2b0baa335b7b5f59491aaaa7493fcdd8359')}

def need(value,message):
    if value is not True:raise ValueError(message)

def read(path):
    need(path.resolve(strict=True)==path and not path.is_symlink(),'canonical source review input')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    try:
        first=os.fstat(fd);need(stat.S_ISREG(first.st_mode) and first.st_size<=1024**2,'bounded regular source/receipt')
        parts=[];total=0
        while part:=os.read(fd,65536):
            total+=len(part);need(total<=first.st_size,'source grew');parts.append(part)
        sig=lambda s:(s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
        need(total==first.st_size and sig(first)==sig(os.fstat(fd))==sig(path.lstat()),'same-read source stable')
        raw=b''.join(parts);pin={'path':str(path),'bytes':total,'sha256':hashlib.sha256(raw).hexdigest()}
        need(path not in EXPECTED or (total,pin['sha256'])==EXPECTED[path],'exact expected source pin')
        return raw,pin
    finally:os.close(fd)

def main():
    need(__debug__,'optimized source review refused')
    inputs={path:read(path) for path in EXPECTED}
    old,new=[inputs[P/name][0] for name in ('review_inputs_01.py','review_inputs_02.py')]
    a,b=ast.parse(old),ast.parse(new)
    need([ast.dump(n,include_attributes=False) for n in a.body if not isinstance(n,ast.FunctionDef)]==
         [ast.dump(n,include_attributes=False) for n in b.body if not isinstance(n,ast.FunctionDef)],'imports/constants/entrypoint unchanged')
    text=new.decode()
    for token in ("set(spec) == {'schema'", "len(captures) == 5", "capture['original'] == original and capture['captured'] == spec[role]", "exact(original); exact(spec[role])", "files.get(executable['path']) == executable", "len(union) == 2421", "h['validate_guard_union'](request)", "for row in profile['files']:", "h['verify_held']()", "'qualified_module'", "'ObjectiveContainerCore' not in module_names", "'proof_limits'", "'proof_pressure_limits'"):
        need(token in text,'reviewed exact capture/admission/rehash source controls')
    for digest in ('9c3761eb4b778ed04349ae29ef84a4b93f1da36c0f8ef9b59e806805ff10c9b3','04015267ed110533a7406c0b39c38b88a974a1d80259fd5755a99ef908a8a8b4','ccdf7df547844ac5d39cc077c8a14194fd06f7bb51838d80ffa9d7f349999e66','1a301bb1763139d48ae638d97b11edf56de6cd185e1b054eae6dc28c271c0c5f'):
        need(digest in text,'exact source/checker/retention/Python pin present')
    tooling=json.loads(inputs[W/'maintenance/ranker-objective-container-core-tooling-source-review-20261005-02/review-receipt.json'][0])
    math=json.loads(inputs[W/'maintenance/ranker-objective-container-core-patch-source-review-20261005-02/review-receipt.json'][0])
    need(tooling['status']==math['status']=='passed_source_only' and tooling['findings']==math['findings']==[] and
         tooling['tooling_source_pins']['container_core_file_helpers_01.py']==inputs[Q/'container_core_file_helpers_01.py'][1], 'exact reviewed helper and math/tooling gates')
    need(all(read(path)[1]==pin for path,(_,pin) in inputs.items()),'all source review inputs rehashed')
    result={'schema':'ranker-objective-container-core-prepared-input-independent-source-review@1','status':'passed_source_only','findings':[],
       'created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'reviewer':read(Path(__file__).resolve())[1],
       'reviewed_source':inputs[P/'review_inputs_02.py'][1],'reviewed_input_pins':[pin for _,pin in inputs.values()],
       'mode':'unexecuted_target_source_only','source_execution_calls':0,'native_test_model_metadata_preparation_or_remote_jobs':0,
       'reviewed_controls':['Externally pinned own source/closed prepared plan and exact four prepared roles.',
         'All15 specification fields closed; five ordered captures join exact original source/checker/retention/freezer/helper descriptors, captured role and destination basename. Existing Python body and profile descriptor pinned.',
         'New math source and tooling gates pinned; exact2421 strict union reconstructed from complete failed-v1 seal29+self and fresh3 docs, with inherited live4 overlaps required equal.',
         'Prior20114 declared physical entries preserved; exactlyfive new captures give20119, all full bodies rehashed before/after with running FD size/stat binding.',
         'Three qualified imports require actual accepted checks, whole objects/ordered chunk reconstruction and first loader candidate joined; candidate module absent from existing registry.',
         'Native20-second/64KiB/16MiB, retention61/3997696raw, root1CPU/2048MiB/4children, pressure and120-second outer bounds unchanged. All output authorities false.'],
       'limitations':['This source review imports/executes no target reviewer/helper and hashes no large dependency closure. Root must run the exact successor on its frozen prepared plan and retain its actual result.',
          'Prepared inputs do not establish native qualification or broader Python/Float/objective/gradient/training/AE/task correctness.'],
       'proof_authority':False,'execution_authority':False,'completion_authority':False,'planner_activation':False,
       'all32_governing_RPI_exits':'OPEN','full_task_satisfaction':'unknown','official_benchmark_score':None}
    output=OUT/'review-receipt.json'
    with output.open('xb') as stream:
        stream.write((json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+'\n').encode());stream.flush();os.fsync(stream.fileno())
    print(json.dumps(read(output)[1],sort_keys=True))

if __name__=='__main__':main()
