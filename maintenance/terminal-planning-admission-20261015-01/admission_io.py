"""Read only named sealed public inputs; original private state stays closed."""
import json
from pathlib import Path
from capsule_io import FALSE,read,write,wire,sha,pin
ROOT=Path(__file__).resolve().parent
WORKER=ROOT.parent/'terminal-context-worker-20261014-01'
WORKER_MANIFEST_SHA='04e4e4f78ffd8d4f4e065eb924b3a28ec0fe5d7b972b932d21890bc4f29722f4'

def inputs():
    raw=read(WORKER/'evidence-manifest.json',1024**2)
    if sha(raw)!=WORKER_MANIFEST_SHA:raise ValueError('sealed worker inventory changed')
    inventory={row['path']:row for row in json.loads(raw)['files']};pins=[]
    def selected(name,maximum):
        row=inventory[name];raw=read(WORKER/name,maximum)
        if len(raw)!=row['bytes'] or sha(raw)!=row['sha256']:raise ValueError('selected public worker input changed')
        pins.append({'path':str(WORKER/name),'bytes':len(raw),'sha256':sha(raw)});return raw
    corpus=json.loads(selected('experiment-01/corpus-manifest.json',65536))
    prior=json.loads(selected('experiment-01/result.json',1024**2));bodies={};instructions={}
    for task in corpus['tasks']:
        for source in task['sources']:
            raw=selected('experiment-01/source-repository/'+source['path'],8192)
            if len(raw)!=source['bytes'] or sha(raw)!=source['sha256']:raise ValueError('source pin differs')
            bodies[source['path']]=raw
        raw=selected('experiment-01/instructions/'+task['task_id']+'/instruction.md',8192)
        if len(raw)!=task['instruction']['bytes'] or sha(raw)!=task['instruction']['sha256']:
            raise ValueError('complete instruction pin differs')
        instructions[task['task_id']]=raw
    if len(bodies)!=5 or len(instructions)!=4 or prior['completed'] is not True:
        raise ValueError('complete public corpus required')
    return corpus,bodies,instructions,sorted(pins,key=lambda row:row['path'])
