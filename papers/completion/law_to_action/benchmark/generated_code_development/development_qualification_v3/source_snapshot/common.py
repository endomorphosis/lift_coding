"""Exact JSON/byte bindings shared by the development runner."""
import hashlib, json, importlib.util, sys
from pathlib import Path

def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def digest(x):return hashlib.sha256(canonical(x)).hexdigest()
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,x):
 p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:json.dump(x,f,sort_keys=True,indent=2);f.write('\n');f.flush()
def load_module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);return module

def verify_runtime(profile,source):
 for rel,expected in profile['source_files'].items():
  p=source/rel
  if p.is_symlink() or sha(p)!=expected:raise ValueError('Native source changed: '+rel)
