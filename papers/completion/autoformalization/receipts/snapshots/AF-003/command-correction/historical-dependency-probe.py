import importlib.util, shutil, json, sys
mods=('numpy','requests','torch','spacy','faiss','transformers','lean_dojo','openai','ipfs_datasets_py')
exes=('lean','lake','elan','cvc5','z3','vampire','eprover','prover9','coqc','isabelle')
print(json.dumps({'python':sys.version.split()[0], 'modules':{m:bool(importlib.util.find_spec(m)) for m in mods}, 'executables':{e:shutil.which(e) for e in exes}},sort_keys=True))
