"""Selected sealed public inputs only; never open predecessor catalogs."""
import json
from pathlib import Path
from capsule_io import FALSE,read,write,wire,sha,pin

ROOT=Path(__file__).resolve().parent
REFERENCE=ROOT.parent/'terminal-reference-packing-20261014-01'
REFERENCE_MANIFEST_SHA='e1e7be5b57dea48fc7668551e89426897818f715dba9e67fcbed88bcbb88377f'

def inputs():
    raw=read(REFERENCE/'evidence-manifest.json',1024**2)
    if sha(raw)!=REFERENCE_MANIFEST_SHA: raise ValueError('sealed reference-packing inventory changed')
    inventory={v['path']:v for v in json.loads(raw)['files']};pins=[]
    def selected(name,maximum):
        entry=inventory[name];raw=read(REFERENCE/name,maximum)
        if len(raw)!=entry['bytes'] or sha(raw)!=entry['sha256']:
            raise ValueError('selected sealed public input changed')
        pins.append({'path':str(REFERENCE/name),'bytes':len(raw),'sha256':sha(raw)});return raw
    corpus=json.loads(selected('experiment-02/corpus-manifest.json',65536))
    prior=json.loads(selected('experiment-02/result.json',1024**2))
    bodies={};instructions={}
    for task in corpus['tasks']:
        for source in task['sources']:
            raw=selected('experiment-02/source-repository/'+source['path'],8192)
            if len(raw)!=source['bytes'] or sha(raw)!=source['sha256']:raise ValueError('complete public source pin differs')
            bodies[source['path']]=raw
        raw=selected('experiment-02/instructions/'+task['task_id']+'/instruction.md',8192)
        if len(raw)!=task['instruction']['bytes'] or sha(raw)!=task['instruction']['sha256']:
            raise ValueError('complete public instruction pin differs')
        instructions[task['task_id']]=raw
    if len(bodies)!=5 or len(instructions)!=4 or prior['completed'] is not True:
        raise ValueError('exact public source/task population required')
    return corpus,bodies,instructions,sorted(pins,key=lambda v:v['path'])
