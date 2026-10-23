"""Merge explicit public JUnit cases and replay the frozen patch in memory."""
import collections
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import xml.etree.ElementTree as ET

E = Path('/home/barberb/lift_coding/maintenance/terminal-compact-retrieval-20261011-01')
PATCH_SHA = '5c1f4a6c41206126de5936fee434eef1f1d54337ef0357e4498d842279671976'
# Parent independently confirmed process9337 exited0 before this aggregation.
CONFIRMED_INTEGRATION_EXIT_CODE = 0

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def read(path):
    assert path.is_file() and not path.is_symlink()
    return path.read_bytes()

def canonical_path(value):
    p = PurePosixPath(value)
    assert not p.is_absolute() and str(p)==value and '..' not in p.parts
    return p

old_path = E/'validation-summary.json'
old_raw = read(old_path)
old = json.loads(old_raw)
guidance_receipt_path = E/'guidance-validation-receipt.json'
guidance_receipt_raw = read(guidance_receipt_path)
guidance_receipt = json.loads(guidance_receipt_raw)
selected = [Path(row['path']) for row in old['reports']]
selected += [Path(row['path']) for row in guidance_receipt['reports']]
selected += [E/'followup-integration-01.xml']
assert len(selected)==len(set(selected)) and CONFIRMED_INTEGRATION_EXIT_CODE==0
modules = {
    'test.api.test_compact_code_retrieval', 'test.api.test_verified_code_retrieval_projection',
    'test.api.test_router_implementation_runner', 'test.api.test_terminal_doctor_dispatch',
    'test.api.test_terminal_intent_benchmark_config',
    *{'benchmarks.agent_supervisor.container_coding.'+name for name in (
        'test_terminal_retrieval_codec','test_terminal_context_audit','test_terminal_context_audit_budget',
        'test_terminal_retrieval_transport','test_terminal_intent_transport','test_full_supervisor_harbor_agent',
        'test_terminal_instruction_delivery','test_terminal_deployment','test_benchmark_comparison',
        'test_terminal_retrieval_codec_comparison')},
}

def identity(classname, name, report):
    normalized = ('test.'+classname) if classname.startswith('api.') else classname
    if classname=='':
        assert report=='wrapper-validation-03/tests.xml'
        normalized='test.api.test_verified_code_retrieval_projection'
    matches=[m for m in modules if normalized==m or normalized.startswith(m+'.')]
    assert len(matches)==1, (classname,name,report)
    module=matches[0]
    test_class=normalized[len(module):].lstrip('.')
    test_file=module.replace('.','/')+'.py'
    node_name=(test_class+'::' if test_class else '')+name
    return test_file,node_name,normalized

reports, cases, aliases, overrides = [], {}, [], []
for path in selected:
    raw=read(path)
    assert len(raw)<=1024*1024
    report=path.relative_to(E).as_posix()
    records=[]
    for case in ET.fromstring(raw).iter('testcase'):
        classname,name=case.get('classname',''),case.get('name')
        assert type(classname) is str and name
        tags=[tag for tag in ('failure','error','skipped') if case.find(tag) is not None]
        assert len(tags)<=1
        outcome={'failure':'failed','error':'errors','skipped':'skipped'}.get(tags[0] if tags else None,'passed')
        records.append((classname,name,outcome))
    if report=='followup-integration-01.xml':
        assert len(records)==270 and all(row[2]=='passed' for row in records)
    reports.append({'path':str(path),'relative_path':report,'sha256':sha(raw),'bytes':len(raw),
        'testcase_records':len(records),'outcomes':dict(collections.Counter(row[2] for row in records))})
    within=set()
    for classname,name,outcome in records:
        test_file,node_name,normalized=identity(classname,name,report)
        key=test_file,node_name
        assert key not in within
        within.add(key)
        if normalized!=classname:
            aliases.append({'report':report,'recorded_classname':classname,'recorded_name':name,
                'effective_file':test_file,'effective_node_name':node_name,
                'reason':'Explicit known selected test module; empty wrapper classname or pytest api/test.api prefix drift.'})
        observed={'report':report,'recorded_classname':classname,'recorded_name':name,'recorded_outcome':outcome}
        if key in cases:
            previous=cases[key]
            if previous['outcome']!=outcome:
                assert test_file=='test/api/test_terminal_intent_benchmark_config.py'
                assert name in {'test_old_config_calls_retain_default_arm_without_contract[full]',
                                'test_old_config_calls_retain_default_arm_without_contract[no-index]'}
                assert previous['selected_report']=='router-regression-01.xml' and report=='job-name-fixed.xml'
                assert previous['outcome']=='failed' and outcome=='passed'
                overrides.append({'test_file':test_file,'name':name,'old_report':previous['selected_report'],
                    'old_outcome':'failed','latest_report':report,'latest_outcome':'passed'})
            provenance=previous['reported_identities']+[observed]
        else:
            provenance=[observed]
        cases[key]={'test_file':test_file,'node_name':node_name,'outcome':outcome,
            'selected_report':report,'reported_identities':provenance}
assert len(overrides)==2
manifest_path=E/'source-manifest-final.json'
manifest_raw=read(manifest_path)
manifest=json.loads(manifest_raw)
checkout=Path(manifest['checkout'])
checks=[]
for row in manifest['files']:
    p=checkout.joinpath(*canonical_path(row['path']).parts)
    raw=read(p)
    checks.append({'path':row['path'],'expected_sha256':row['after_sha256'],'observed_sha256':sha(raw),
        'sha256_matches':sha(raw)==row['after_sha256'],'expected_bytes':row['after_bytes'],
        'observed_bytes':len(raw),'bytes_match':len(raw)==row['after_bytes']})
assert len(checks)==18 and all(c['sha256_matches'] and c['bytes_match'] for c in checks)
patch_path=E/'changes-final.patch'
patch_raw=read(patch_path)
assert sha(patch_raw)==PATCH_SHA==manifest['patch_sha256'] and len(patch_raw)==manifest['patch_bytes']
lines=patch_raw.decode().splitlines(True)
expected={row['path']:row for row in manifest['files']}
applied=[]
i=0
while i<len(lines):
    assert lines[i].startswith('--- ') and lines[i+1].startswith('+++ b/')
    name=lines[i+1][len('+++ b/'):].rstrip('\n')
    canonical_path(name)
    row=expected[name]
    assert name not in applied
    if row['new_file']:
        assert lines[i]=='--- /dev/null\n'
        assert not (E/'baseline'/name).exists()
        before=b''
    else:
        assert lines[i]=='--- a/'+name+'\n'
        before=read(E/'baseline'/name)
        assert sha(before)==row['before_sha256'] and len(before)==row['before_bytes']
    original=before.decode().splitlines(True)
    out=[]
    cursor=0
    i+=2
    while i<len(lines) and not lines[i].startswith('--- '):
        match=re.fullmatch(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@[^\n]*\n',lines[i])
        assert match
        old_start=int(match[1]);old_count=int(match[2]) if match[2] is not None else 1
        new_start=int(match[3]);new_count=int(match[4]) if match[4] is not None else 1
        begin=old_start-1 if old_start else 0
        assert cursor<=begin<=len(original)
        out.extend(original[cursor:begin]);cursor=begin
        assert len(out)==(new_start-1 if new_start else 0)
        old_n=new_n=0
        i+=1
        while i<len(lines) and not lines[i].startswith(('@@ ','--- ')):
            line=lines[i];assert line[0] in ' +-'
            content=line[1:]
            if line[0] in ' -':
                assert cursor<len(original) and original[cursor]==content
                cursor+=1;old_n+=1
            if line[0] in ' +':
                out.append(content);new_n+=1
            i+=1
        assert old_n==old_count and new_n==new_count
    out.extend(original[cursor:])
    after=''.join(out).encode()
    assert sha(after)==row['after_sha256'] and len(after)==row['after_bytes']
    assert after==read(checkout/name)
    applied.append(name)
assert set(applied)==set(expected)
assert read(old_path)==old_raw and read(manifest_path)==manifest_raw and read(patch_path)==patch_raw
outcomes=collections.Counter(row['outcome'] for row in cases.values())
assert len(cases)==534 and outcomes['passed']==534
legacy_path=E/'legacy-codec-replay.json';legacy_raw=read(legacy_path);legacy=json.loads(legacy_raw)
assert legacy['all_old_and_explicit_v1_bytes_equal'] is True
assert sha(read(Path(legacy['extracted_module'])))==legacy['expected_qualified_v12_module_sha256']
guidance_summary={'schema':'terminal-decoder-guidance-reviewed-validation@1',
    'review_kind':'Author self-review with independently extracted qualified-v12 module byte comparison; root separately reviews integration.',
    'full_suite':reports[-3],'golden_legacy_rerun':reports[-2],
    'unique_core_cases':51,'golden_case_is_a_rerun':True,
    'legacy_replay':{'path':str(legacy_path),'sha256':sha(legacy_raw),'old_module_sha256':legacy['extracted_module_sha256'],
        'all_old_and_explicit_v1_bytes_equal':True,'prefix_variants_checked':len(legacy['checks'])},
    'implementation_checks':{'full_advertised_shell_command_executes_without_added_arguments':True,
        'required_wire_path_and_hash_arguments_present':True,'quoted_absolute_task_wire_variable_supported':True,
        'canonical_wire_hash_charged_in_guidance_gate':True,'exact_integer_guidance_versions_1_or_2':True,
        'version1_exact_bytes_and_receipt_schema_preserved':True,'version2_receipt_adds_only_guidance_version':True,
        'wire_schema_remains_version1':True,'native_and_source_authority_not_added':True},
    'source_hashes':{c['path']:c['observed_sha256'] for c in checks if c['path'].endswith('compact_code_retrieval.py')},
    'provider_calls_during_review':0,'live_archive_modified':False}
with (E/'guidance-validation.json').open('x') as f:f.write(json.dumps(guidance_summary,indent=2,sort_keys=True)+'\n')
total=sum(r['testcase_records'] for r in reports)
summary={'schema':'terminal-compact-retrieval-validation-summary-final@1',
    'parent_confirmed_followup_process':{'session_id':9337,'exit_code':0,'tests_passed':270,'seconds':188.45},
    'selected_report_count':len(reports),'selected_testcase_records':total,'unique_test_cases':len(cases),
    'duplicate_testcase_records_removed':total-len(cases),'unique_outcomes':{key:outcomes[key] for key in ('passed','failed','errors','skipped')},
    'deduplication_key':['test_file','node_name'],'module_identity_policy':'Explicit known selected file mapping; nested pytest class is retained in node_name. All original identities and outcomes are retained.',
    'identity_aliases':aliases,'superseded_stale_failures':overrides,'reports':reports,
    'unique_cases':[cases[key] for key in sorted(cases)],
    'old_summary_preserved':{'path':str(old_path),'sha256_before':sha(old_raw),'sha256_after':sha(read(old_path))},
    'baseline_reproduction':old['baseline_reproduction'],
    'source_manifest_final':{'path':str(manifest_path),'sha256':sha(manifest_raw),'bytes':len(manifest_raw)},
    'source_hash_checks':checks,'changed_source_files_checked':18,'all_current_changed_sources_match_final_manifest':True,
    'patch':{'path':str(patch_path),'sha256':sha(patch_raw),'bytes':len(patch_raw),'applies_exactly_to_captured_baseline_in_memory':True,
        'reconstructed_files_match_current_sha_bytes':True,'files_replayed':len(applied),'filesystem_source_or_index_modified':False},
    'guidance_validation':{'path':str(E/'guidance-validation.json'),'sha256':sha(read(E/'guidance-validation.json'))},
    'excluded_report_names':['comparison-03.xml'],
    'count_reconciliation':{'old_unique_passes':486,'new_core_cases':13,'new_audit_cases':35,'final_unique_passes':534,
        'guidance_golden_rerun_adds_new_unique_case':False},
    'limitations':['Focused suites only; not full-repository CI.','Latest selected results override by explicit module/file node identity; only two baseline-reproduced stale failures changed outcome.',
        'Historical reports span source revisions; final270-case integration and current18-file SHA checks do not claim every older-only case was rerun on every later edit.',
        'The extra golden core case is a rerun of a case in the51-case guidance suite; it is counted once.',
        'Test evidence and exact codec replay establish no live provider token savings, benchmark advantage, formal task completion, or whole-program proof.',
        'Only explicit public JUnit, source manifest, captured baseline, patch and listed source files were read; no private fixture trees, auth, raw model logs or hidden verifier were scanned.'],
    'provider_calls_during_aggregation':0,'source_files_modified':False,'old_runtime_or_pilot_evidence_modified':False}
p=E/'validation-summary-final.json'
with p.open('x') as f:f.write(json.dumps(summary,indent=2,sort_keys=True)+'\n')
print(json.dumps({'path':str(p),'sha256':sha(read(p)),'unique_test_cases':len(cases),'outcomes':summary['unique_outcomes'],
    'selected_records':total,'duplicate_records_removed':total-len(cases),'source_files_verified':18,'patch_replayed_in_memory':True,
    'old_summary_preserved':True,'guidance_review_receipt':str(E/'guidance-validation.json')},indent=2))
