"""Explicit producer copies, process-group deadline, and immutable attempt logs."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from evidence_io import ROOT,TYPED,PRIOR,DATASETS,pin,read,write,sha

def selected():
    names=['env_run.py','launch.py','evidence_io.py','typed_targets.py','typed_training.py',
        'nomination_review.py','run_successor.py','verify_successor.py','run_process.py',
        'test_typed_targets.py','test_typed_training.py','test_nomination_review.py','test_result_scope.py']
    paths=[ROOT/name for name in names]
    paths += [TYPED/name for name in ['evidence-manifest.json','native_structural_ir.py','scheduler_overlay.py',
        'native-policy-overlay-01/source-pins.json','native-policy-overlay-01/resource_scheduler.py',
        'native-policy-overlay-01/proof_resource_safety.py','align_projection.py']]
    paths += [PRIOR/name for name in ['evidence-manifest.json','corpus-manifest-01.json','metadata_projections.py']]
    paths += [DATASETS/name for name in ['logic/formalization/autoencoder/security/codebase_autoencoder.py',
        'optimizers/logic_theorem_optimizer/modal_autoencoder_cuda.py','logic/software_contracts/codebase_ir.py',
        'logic/software_contracts/duckdb_ast_store.py','logic/software_contracts/duckdb_ingest.py',
        'logic/software_contracts/cache.py','logic/software_contracts/codebase_resources.py',
        'logic/software_contracts/semantic_index/snapshot.py','duckdb_control/codebase_catalog.py']]
    return [pin(path) for path in paths]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True)
    parser.add_argument('--kind',choices=['train','cold','test'],required=True)
    parser.add_argument('--run',default='experiment-01');args=parser.parse_args()
    for name in [args.label,args.run]:
        if not name or Path(name).name!=name or name in {'.','..'}:raise ValueError('local attempt name required')
    before=selected();directory=ROOT/(args.label+'-frozen-sources');directory.mkdir(mode=0o700)
    retained=[]
    for index,entry in enumerate(before):
        body=read(Path(entry['path']),32*1024*1024)
        if sha(body)!=entry['sha256']:raise ValueError('producer changed before copy')
        target=directory/(f'{index:03d}-'+Path(entry['path']).name)
        with target.open('xb') as stream:
            stream.write(body);stream.flush();os.fchmod(stream.fileno(),0o444);os.fsync(stream.fileno())
        retained.append({**entry,'retained_copy':str(target)})
    write(ROOT/(args.label+'-source-pins.json'),{'pins':before,'retained_copies':retained,
        'complete_transitive_loaded_code_closure':False})
    if args.kind=='train':command=['run_successor.py','--output',str(ROOT/args.run)]
    elif args.kind=='cold':command=['verify_successor.py','--run',args.run,'--report',args.label+'-cold-report.json']
    else:command=['--module','pytest','-q','-p','no:cacheprovider','--junitxml='+str(ROOT/(args.label+'.xml')),
        'test_typed_targets.py','test_typed_training.py','test_nomination_review.py','test_result_scope.py']
    timed_out=False;started=time.monotonic()
    with (ROOT/(args.label+'-stdout.log')).open('xb') as stdout,(ROOT/(args.label+'-stderr.log')).open('xb') as stderr:
        process=subprocess.Popen([sys.executable,'-B',str(ROOT/'env_run.py'),*command],cwd=ROOT,
            stdout=stdout,stderr=stderr,start_new_session=True)
        try:code=process.wait(timeout=240)
        except subprocess.TimeoutExpired:
            timed_out=True;os.killpg(process.pid,signal.SIGKILL);code=process.wait(timeout=10)
    after=selected();report={'kind':args.kind,'exit_code':code,'timed_out':timed_out,
        'seconds':time.monotonic()-started,'selected_sources_unchanged':before==after,
        'qualified':code==0 and not timed_out and before==after,'outer_wall_seconds':240,'before':before,'after':after}
    if args.kind=='test' and (ROOT/(args.label+'.xml')).is_file():
        import xml.etree.ElementTree as ET
        suites=list(ET.fromstring(read(ROOT/(args.label+'.xml'))).iter('testsuite'))
        report['tests']={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ['tests','failures','errors','skipped']}
        report['qualified']=report['qualified'] and report['tests']['failures']==0 and report['tests']['errors']==0 and report['tests']['skipped']==0
    write(ROOT/(args.label+'-process-report.json'),report)
    print(json.dumps({k:v for k,v in report.items() if k not in ['before','after']}))
    raise SystemExit(0 if report['qualified'] else 1)

if __name__=='__main__':main()
