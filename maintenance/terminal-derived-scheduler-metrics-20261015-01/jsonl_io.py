"""Bounded public-only inputs from the sealed byte-bound JSONL experiment."""
import json
from pathlib import Path
from capsule_io import FALSE,read,write,wire,sha,pin
ROOT=Path(__file__).resolve().parent
CONSTRAINT=ROOT.parent/'terminal-typed-constraints-20261015-01'
CONSTRAINT_MANIFEST_SHA='c300af27d9c1765533434f8b3fc6066ed3984359d0f75a6377bf48c60d467910'
PREDECESSOR=ROOT.parent/'terminal-lean-jsonl-decoder-20261015-01'
PREDECESSOR_MANIFEST_SHA='656f94a954f9a51270a935ec697bd31645935f29349e74962b184c57f6b28632'

def inputs():
    manifest_raw=read(PREDECESSOR/'evidence-manifest.json',1024**2)
    if sha(manifest_raw)!=PREDECESSOR_MANIFEST_SHA:raise ValueError('sealed byte-bound JSONL inventory changed')
    inventory={row['path']:row for row in json.loads(manifest_raw)['files']};pins=[]
    def select(name,maximum):
        row=inventory[name];raw=read(PREDECESSOR/name,maximum)
        if len(raw)!=row['bytes'] or sha(raw)!=row['sha256']:raise ValueError('selected public input changed')
        pins.append({'path':str(PREDECESSOR/name),'bytes':len(raw),'sha256':sha(raw)});return raw
    corpus=json.loads(select('experiment-01/corpus-manifest.json',65536))
    result=json.loads(select('experiment-01/result.json',1024**2));bodies={};instructions={}
    for task in corpus['tasks']:
        for source in task['sources']:
            raw=select('experiment-01/source-repository/'+source['path'],8192)
            if len(raw)!=source['bytes'] or sha(raw)!=source['sha256']:raise ValueError('whole source pin differs')
            bodies[source['path']]=raw
        raw=select('experiment-01/instructions/'+task['task_id']+'/instruction.md',8192)
        if len(raw)!=task['instruction']['bytes'] or sha(raw)!=task['instruction']['sha256']:
            raise ValueError('whole instruction pin differs')
        instructions[task['task_id']]=raw
    if len(bodies)!=5 or len(instructions)!=4 or result['completed'] is not True:
        raise ValueError('complete public corpus required')
    return corpus,bodies,instructions,sorted(pins,key=lambda row:row['path'])
