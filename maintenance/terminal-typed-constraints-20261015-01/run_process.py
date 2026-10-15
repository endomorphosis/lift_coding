"""Retain explicit public producer pins and bound each complete owned attempt."""
import argparse
import json
import os
from pathlib import Path
import runpy
import signal
import subprocess
import sys
import time
from constraint_io import ROOT,INTENT,INTENT_MANIFEST_SHA,read,write,sha,pin

LOCAL=['env_run.py','launch.py','constraint_io.py','constraint_metadata.py','scheduler_constraints.py',
 'constraint_projections.py','constraint_lean.py','constraint_run.py','constraint_verify.py','constraint_faults.py',
 'constraint_source_mutation.py','run_process.py','finalize_stage.py','test_scheduler_constraints.py',
 'test_constraint_projections.py','test_constraint_lean.py','test_constraint_evidence.py','test_constraint_runtime_evidence.py']
TESTS=[name for name in LOCAL if name.startswith('test_')]

def selected():
    raw=read(INTENT/'evidence-manifest.json',1024**2)
    if sha(raw)!=INTENT_MANIFEST_SHA:raise ValueError('sealed full-instruction predecessor changed')
    manifest={row['path']:row for row in json.loads(raw)['files']}
    source=read(INTENT/'run_process.py')
    if sha(source)!=manifest['run_process.py']['sha256']:raise ValueError('sealed inventory producer changed')
    inherited=runpy.run_path(str(INTENT/'run_process.py'),run_name='intent_process_inventory')['selected']()
    from constraint_projections import producer_paths as projection_paths
    from constraint_lean import producer_paths as lean_paths
    paths=[ROOT/name for name in LOCAL]+[INTENT/'evidence-manifest.json']+projection_paths()+lean_paths()
    return sorted({row['path']:row for row in inherited+[pin(path) for path in paths]}.values(),key=lambda row:row['path'])

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--kind',choices=['test','run','fault','cold'],required=True)
    parser.add_argument('--label',required=True);parser.add_argument('--run',default='experiment-01')
    parser.add_argument('--fault-report',default='native-faults-01-fault-report.json');args=parser.parse_args()
    for name in [args.label,args.run,args.fault_report]:
        if not name or Path(name).name!=name or name in {'.','..'}:raise ValueError('fresh local attempt names required')
    before=selected();copies=ROOT/(args.label+'-frozen-sources');copies.mkdir(mode=0o700)
    retained=[]
    for i,entry in enumerate(before):
        raw=read(Path(entry['path']),32*1024**2)
        if sha(raw)!=entry['sha256']:raise ValueError('producer changed before capture')
        target=copies/(f'{i:03d}-'+Path(entry['path']).name)
        with target.open('xb') as stream:
            stream.write(raw);stream.flush();os.fchmod(stream.fileno(),0o444);os.fsync(stream.fileno())
        retained.append({**entry,'retained_copy':str(target)})
    write(ROOT/(args.label+'-source-pins.json'),{'pins':before,'retained_copies':retained,
        'complete_transitive_loaded_code_closure':False})
    if args.kind=='test':command=['--module','pytest','-q','-p','no:cacheprovider',
        '--junitxml='+str(ROOT/(args.label+'.xml')),*TESTS]
    elif args.kind=='run':command=['constraint_run.py','--output',str(ROOT/args.run)]
    elif args.kind=='fault':command=['constraint_faults.py','--run',args.run,'--label',args.label]
    else:command=['constraint_verify.py','--run',args.run,'--fault-report',args.fault_report,'--report',args.label+'-cold-report.json']
    started=time.monotonic();timed_out=False;cleanup_error=None
    with (ROOT/(args.label+'-stdout.log')).open('xb') as stdout,(ROOT/(args.label+'-stderr.log')).open('xb') as stderr:
        process=subprocess.Popen([sys.executable,'-B',str(ROOT/'env_run.py'),*command],cwd=ROOT,
            stdout=stdout,stderr=stderr,start_new_session=True)
        try:code=process.wait(timeout=600)
        except subprocess.TimeoutExpired:
            timed_out=True
            from ipfs_accelerate_py.agent_supervisor.todo_daemon.supervisor_runtime import read_process_birth,terminate_pid_tree
            try:
                try:birth=read_process_birth(process.pid)
                except OSError:birth=None
                if birth is not None:
                    if not terminate_pid_tree(process.pid,grace_seconds=5,freeze_first=True,require_gone=True,
                            owned_process_group_id=process.pid,expected_root_start_time_ticks=birth.start_time_ticks):
                        raise RuntimeError('owned outer process tree could not be fenced')
                code=process.wait(timeout=10)
            except Exception as error:
                cleanup_error=type(error).__name__+': '+str(error);code=process.poll()
    after=selected();report={'kind':args.kind,'selected_run':args.run,'exit_code':code,'timed_out':timed_out,
        'seconds':time.monotonic()-started,'selected_sources_unchanged':before==after,'cleanup_error':cleanup_error,
        'qualified':code==0 and not timed_out and before==after,'outer_wall_seconds':600,'before':before,'after':after}
    if args.kind=='test' and (ROOT/(args.label+'.xml')).is_file():
        import xml.etree.ElementTree as ET
        suites=list(ET.fromstring(read(ROOT/(args.label+'.xml'))).iter('testsuite'))
        report['tests']={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ['tests','failures','errors','skipped']}
        report['qualified']=report['qualified'] and not any(report['tests'][k] for k in ['failures','errors','skipped'])
    write(ROOT/(args.label+'-process-report.json'),report)
    print(json.dumps({k:v for k,v in report.items() if k not in ['before','after']}))
    raise SystemExit(0 if report['qualified'] else 1)

if __name__=='__main__':main()
