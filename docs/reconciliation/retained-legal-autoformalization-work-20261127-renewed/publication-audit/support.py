from pathlib import Path
import subprocess,os,json
WORK=Path(__file__).resolve().parent
PREVIOUS=WORK.parent/'publish-all-20261126-nsFFGMUO'
CONTROLS=WORK.parent/'Phase8-existing-native-CI-trigger-repair-private-v01/coordination-full-goal-v02'
ENV={**os.environ,'GIT_OPTIONAL_LOCKS':'0','GIT_NO_LAZY_FETCH':'1','GIT_TERMINAL_PROMPT':'0'}
def git(name,*args,raw=None):
 return subprocess.check_output(['git','--git-dir',str(WORK/(name+'.git')),'-c','pack.threads=1','-c','index.threads=1',*args],input=raw,env=ENV,timeout=120)
def tree(name,rev):
 result={}
 for row in git(name,'ls-tree','-rz',rev).split(bytes([0])):
  if row:
   h,p=row.split(bytes([9]),1);mode,kind,oid=h.decode().split();result[p.decode()]=(mode,oid)
 return result
def save(name,value):
 with (WORK/name).open('x') as f:json.dump(value,f,indent=2,sort_keys=True);f.write(chr(10))
