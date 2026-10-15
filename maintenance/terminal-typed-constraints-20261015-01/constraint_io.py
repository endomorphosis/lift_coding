"""Bounded public-only inputs from the sealed full-instruction experiment."""
import json
from pathlib import Path
from capsule_io import FALSE,read,write,wire,sha,pin
ROOT=Path(__file__).resolve().parent
INTENT=ROOT.parent/'terminal-intent-coverage-20261015-01'
INTENT_MANIFEST_SHA='dbe1b34edaa8587ab72d9e8bca27e94ec92ca3479d7927502346917ef97a3739'

def inputs():
    manifest_raw=read(INTENT/'evidence-manifest.json',1024**2)
    if sha(manifest_raw)!=INTENT_MANIFEST_SHA:raise ValueError('sealed full-instruction inventory changed')
    inventory={row['path']:row for row in json.loads(manifest_raw)['files']};pins=[]
    def select(name,maximum):
        row=inventory[name];raw=read(INTENT/name,maximum)
        if len(raw)!=row['bytes'] or sha(raw)!=row['sha256']:raise ValueError('selected public input changed')
        pins.append({'path':str(INTENT/name),'bytes':len(raw),'sha256':sha(raw)});return raw
    corpus=json.loads(select('experiment-02/corpus-manifest.json',65536))
    result=json.loads(select('experiment-02/result.json',1024**2));bodies={};instructions={}
    for task in corpus['tasks']:
        for source in task['sources']:
            raw=select('experiment-02/source-repository/'+source['path'],8192)
            if len(raw)!=source['bytes'] or sha(raw)!=source['sha256']:raise ValueError('whole source pin differs')
            bodies[source['path']]=raw
        raw=select('experiment-02/instructions/'+task['task_id']+'/instruction.md',8192)
        if len(raw)!=task['instruction']['bytes'] or sha(raw)!=task['instruction']['sha256']:
            raise ValueError('whole instruction pin differs')
        instructions[task['task_id']]=raw
    if len(bodies)!=5 or len(instructions)!=4 or result['completed'] is not True:
        raise ValueError('complete public corpus required')
    return corpus,bodies,instructions,sorted(pins,key=lambda row:row['path'])
