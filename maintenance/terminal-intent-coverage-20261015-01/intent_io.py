"""Bounded public-only inputs from the sealed planning-admission experiment."""
import json
from pathlib import Path
from capsule_io import FALSE,read,write,wire,sha,pin
ROOT=Path(__file__).resolve().parent
ADMISSION=ROOT.parent/'terminal-planning-admission-20261015-01'
ADMISSION_MANIFEST_SHA='a6189cbec99bc699f08891471ea19844a6c6d797c0e9cb556b28fbbb177307f5'

def inputs():
    manifest_raw=read(ADMISSION/'evidence-manifest.json',1024**2)
    if sha(manifest_raw)!=ADMISSION_MANIFEST_SHA:raise ValueError('sealed planning-admission inventory changed')
    inventory={row['path']:row for row in json.loads(manifest_raw)['files']};pins=[]
    def select(name,maximum):
        row=inventory[name];raw=read(ADMISSION/name,maximum)
        if len(raw)!=row['bytes'] or sha(raw)!=row['sha256']:raise ValueError('selected public input changed')
        pins.append({'path':str(ADMISSION/name),'bytes':len(raw),'sha256':sha(raw)});return raw
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
