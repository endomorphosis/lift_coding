"""Real stale-source/artifact controls on the owned experiment, then exact restore."""
import argparse
import json
import os
from pathlib import Path
import resource
import time
from evidence_io import ROOT,FALSE,read,write,sha,pin
from verify_successor import run as cold_verify

def replace_owned(path,raw):
    if ROOT not in path.parents:raise ValueError('owned fault artifact required')
    read(path,32*1024**2)
    descriptor=os.open(path,os.O_WRONLY|os.O_TRUNC|os.O_NOFOLLOW)
    try:
        with os.fdopen(descriptor,'wb',closefd=False) as stream:
            stream.write(raw);stream.flush();os.fsync(stream.fileno())
    finally:os.close(descriptor)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',required=True);parser.add_argument('--report',required=True)
    args=parser.parse_args()
    for name in [args.run,args.report]:
        if not name or Path(name).name!=name or name in {'.','..'}:raise ValueError('local names required')
    resource.setrlimit(resource.RLIMIT_CPU,(180,180));resource.setrlimit(resource.RLIMIT_AS,(8*1024**3,8*1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE,(32*1024**2,32*1024**2))
    run=ROOT/args.run
    source=run/'source-repository'/'llm-inference-batching-scheduler/environment/task_file/scripts/cost_model.py'
    other=run/'source-repository'/'headless-terminal/environment/base_terminal.py'
    checkpoint=run/'primary-1729-checkpoint.json';result=run/'result.json'
    paths=[source,other,checkpoint,result];before=[pin(p) for p in paths];controls=[]
    def control(name,path,transform,expected_class,expected_message):
        original=read(path,32*1024**2);changed=transform(original)
        if changed==original:raise ValueError('fault must change bytes')
        started=time.monotonic()
        try:
            replace_owned(path,changed)
            try:cold_verify(run)
            except Exception as error:
                if type(error).__name__!=expected_class or expected_message not in str(error):raise
                controls.append({'control':name,'refused':True,'exception':type(error).__name__,
                    'message':str(error),'before_sha256':sha(original),'mutated_sha256':sha(changed),
                    'alignment_source_changed':path==source,'seconds':time.monotonic()-started})
            else:raise ValueError('negative native control accepted')
        finally:
            replace_owned(path,original)
            if read(path,32*1024**2)!=original:raise ValueError('owned fault restoration differs')
    def source_mutation(raw):
        needle=b'return ((x + g - 1) // g) * g'
        if raw.count(needle)!=1:raise ValueError('unique source arithmetic control required')
        return raw.replace(needle,b'return ((x + g - 2) // g) * g')
    control('actual_alignment_source_drift',source,source_mutation,'StaleCodebaseError','')
    control('other_indexed_source_drift',other,lambda raw:raw+b'\n# owned stale-head control\n','StaleCodebaseError','')
    def weight_mutation(raw):
        data=json.loads(raw);data['parameters'][0][0][0]+=.5
        return json.dumps(data,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    control('actual_checkpoint_artifact_drift',checkpoint,weight_mutation,'ValueError','selected artifact changed')
    def authority_mutation(raw):
        data=json.loads(raw);data['source_model_equivalence_proved']=True
        return json.dumps(data,sort_keys=True,separators=(',',':')).encode()
    control('result_equivalence_authority_promotion',result,authority_mutation,'ValueError','authority claims changed')
    after=[pin(p) for p in paths]
    if before!=after:raise ValueError('selected owned fault artifacts not restored')
    report={'schema':'terminal-richer-ir-native-faults@1','qualified':True,'controls':controls,
        'all_four_original_bodies_restored':True,'new_optimizer_steps':0,
        'positive_cold_readback_required_after_controls':True,**FALSE}
    write(ROOT/args.report,report)
    print(json.dumps({'qualified':True,'refused_controls':len(controls),'all_original_bodies_restored':True}))

if __name__=='__main__':main()
