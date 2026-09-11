import importlib, json, hashlib, shutil, sys
for name in ['ipfs_accelerate_py.agent_supervisor.autonomous_repair.formal_assurance_cegis','ipfs_accelerate_py.agent_supervisor.todo_daemon.deterministic_repair_composition','ipfs_accelerate_py.agent_supervisor.analysis.formal_assurance.ipa','ipfs_datasets_py.logic.software_contracts','ipfs_accelerate_py.agent_supervisor.semantic_state','ipfs_accelerate_py.agent_supervisor.proof.incremental_sealing.sealer']:
    try:
        module=importlib.import_module(name); path=module.__file__
        print(json.dumps({'module': name, 'loaded': True, '__file__': path, 'sha256': hashlib.sha256(open(path, 'rb').read()).hexdigest()}, sort_keys=True))
    except Exception as exc:
        print(json.dumps({'module': name, 'loaded': False, 'failure': f'{type(exc).__name__}: {exc}'}, sort_keys=True))
print(json.dumps({'python_version': sys.version.split()[0], 'native_binaries': {x: shutil.which(x) for x in ['z3','cvc5','lean','lake','coqc','souffle']}}, sort_keys=True))
