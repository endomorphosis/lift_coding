"""Package only the fourteen nominated stage sources against explicit captures."""
import difflib
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import xml.etree.ElementTree as ET

M=Path(__file__).resolve().parent
C=M.parent/'terminal-token-reduction-20261007-01/checkout'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def pin(path):
    assert path.is_file() and not path.is_symlink()
    raw=path.read_bytes()
    return {'path':str(path),'bytes':len(raw),'sha256':sha(raw)}
def write(name,value):
    target=M/name
    assert not target.exists()
    target.write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')

selected=json.loads((M/'selected-validation-reports.json').read_bytes())['reports']
cases={}; reports=[]; duplicate=0
for name in selected:
    path=M/name; root=ET.fromstring(path.read_bytes()); rows=root.findall('.//testcase')
    assert rows and not root.findall('.//failure') and not root.findall('.//error') and not root.findall('.//skipped')
    for case in rows:
        identity=(case.get('classname'),case.get('name'))
        assert all(identity)
        duplicate+=identity in cases
        cases.setdefault(identity,[]).append(name)
    reports.append({**pin(path),'physical_cases':len(rows)})
sources=[
 'benchmarks/agent_supervisor/container_coding/'+n+'.py' for n in (
 'terminal_container_supervisor','terminal_context_audit','container_worker_deployment',
 'test_terminal_nomination_entrypoint','terminal_source_nomination_budget','test_terminal_source_nomination_budget',
 'retained_source_nomination_lifecycle','test_retained_source_nomination_lifecycle',
 'terminal_model_input_observation_audit','test_terminal_model_input_observation_audit')]
sources+=['ipfs_accelerate_py/agent_supervisor/runtime/'+n+'.py' for n in ('router_implementation_runner','model_input_observation_receipt')]
sources+=['test/api/'+n+'.py' for n in ('test_router_model_input_observation','test_model_input_observation_receipt')]
assert len(sources)==len(set(sources))==14
before={}
for name in ('beginning-source-pins.json','observation-source-before-pins.json','worker-observation-before-pins.json'):
    for row in json.loads((M/name).read_bytes())['files']:
        path=row.get('baseline') or str(M/'baseline'/row['path'])
        raw=Path(path).read_bytes()
        assert len(raw)==row['bytes'] and sha(raw)==row['sha256']
        assert row['path'] not in before
        before[row['path']]={**row,'baseline':path}
assert len(before)==16
expected_old={
 'benchmarks/agent_supervisor/container_coding/'+n+'.py' for n in (
 'terminal_container_supervisor','terminal_context_audit','container_worker_deployment','test_terminal_nomination_entrypoint')}
expected_old.add('ipfs_accelerate_py/agent_supervisor/runtime/router_implementation_runner.py')
assert set(sources)&set(before)==expected_old
archive=json.loads((M/'runtime-archive-final-02/manifest.json').read_bytes())
archive_rows={row['path']:row for row in archive['files']}
chunks=[]; records=[]; heads={}
with tempfile.TemporaryDirectory(prefix='isolated-patch-verification-',dir=M) as temp:
    scratch=Path(temp)
    for name in sources:
        path=C/name; raw=path.read_bytes(); compile(raw,name,'exec'); heads[name]=raw
        archived=archive_rows['source/'+name]
        assert archived['bytes']==len(raw) and archived['sha256']==sha(raw)
        old=Path(before[name]['baseline']).read_bytes() if name in before else b''
        if name in before:
            target=scratch/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(old)
        chunks.append(''.join(difflib.unified_diff(old.decode().splitlines(keepends=True),raw.decode().splitlines(keepends=True),
            fromfile='a/'+name if name in before else '/dev/null',tofile='b/'+name)))
        records.append({'path':name,'absolute_path':str(path),'bytes':len(raw),'sha256':sha(raw),
            'absent_before':name not in before,'before_bytes':len(old) if name in before else None,
            'before_sha256':sha(old) if name in before else None,'baseline':before[name]['baseline'] if name in before else None})
    patch=''.join(chunks).encode();patch_path=M/'changes.patch';assert not patch_path.exists();patch_path.write_bytes(patch)
    subprocess.run(['git','init','-q',str(scratch)],check=True,capture_output=True)
    subprocess.run(['git','apply','--check',str(patch_path)],cwd=scratch,check=True,capture_output=True)
    subprocess.run(['git','apply',str(patch_path)],cwd=scratch,check=True,capture_output=True)
    assert all((scratch/name).read_bytes()==raw==(C/name).read_bytes() for name,raw in heads.items())
write('source-manifest.json',{'schema':'nomination-lifecycle-source-manifest@1','checkout':str(C),'files':records,
 'existing_deltas':5,'new_files':9,'patch_bytes':len(patch),'patch_sha256':sha(patch),
 'patch_applies_cleanly_to_captured_baselines':True,'applied_changed_bytes_match_checkout':True,
 'all_fourteen_source_hashes_match_final_runtime_archive':True,'final_runtime_archive_sha256':archive['archive_sha256'],
 'original_dirty_checkout_or_git_index_mutated':False,'remote_publication_performed':False})
write('final-focused-validation.json',{'schema':'nomination-lifecycle-focused-validation@1',
 'selected_reports':reports,'physical_cases':sum(r['physical_cases'] for r in reports),
 'distinct_cases':len(cases),'duplicate_cases_not_recounted':duplicate,
 'all_selected_cases_passed':True,'whole_repository_test_pass_claimed':False,
 'current_source_checks':records,'validation_scope':'Authored fixtures and selected regressions; actual Harbor qualification is a separate artifact.'})
print(json.dumps({'sources':14,'distinct_cases':len(cases),'duplicates_not_recounted':duplicate,'clean_patch':True}))
