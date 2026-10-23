"""Read explicitly named sealed public inputs; predecessor catalogs stay closed."""
import json
from pathlib import Path
from capsule_io import FALSE, read, write, wire, sha, pin

ROOT = Path(__file__).resolve().parent
CAPS = ROOT.parent / 'terminal-source-capsules-20261014-01'
CAPS_MANIFEST_SHA = 'd7beaf7179dc06cb36f10bbb99c1e6071e86207378d26401dbf8b1c0b8919742'

def inputs():
    raw = read(CAPS / 'evidence-manifest.json', 1024**2)
    if sha(raw) != CAPS_MANIFEST_SHA:
        raise ValueError('sealed predecessor manifest changed')
    inventory = {v['path']: v for v in json.loads(raw)['files']}
    pins = []
    def selected(name, maximum):
        entry = inventory[name]
        raw = read(CAPS / name, maximum)
        if len(raw) != entry['bytes'] or sha(raw) != entry['sha256']:
            raise ValueError('named sealed public input changed')
        pins.append({'path': str(CAPS / name), 'bytes': len(raw), 'sha256': sha(raw)})
        return raw
    corpus = json.loads(selected('experiment-04/corpus-manifest.json', 65536))
    old = json.loads(selected('experiment-04/result.json', 1024**2))
    bodies, instructions = {}, {}
    for task in corpus['tasks']:
        for source in task['sources']:
            raw = selected('experiment-04/source-repository/' + source['path'], 8192)
            if sha(raw) != source['sha256'] or len(raw) != source['bytes']:
                raise ValueError('public source pin differs')
            bodies[source['path']] = raw
        raw = selected('experiment-04/instructions/' + task['task_id'] + '/instruction.md', 8192)
        if sha(raw) != task['instruction']['sha256'] or len(raw) != task['instruction']['bytes']:
            raise ValueError('complete public instruction pin differs')
        instructions[task['task_id']] = raw
    if len(bodies) != 5 or len(instructions) != 4 or old['completed'] is not True:
        raise ValueError('complete selected source population required')
    return corpus, bodies, instructions, sorted(pins, key=lambda v: v['path'])
