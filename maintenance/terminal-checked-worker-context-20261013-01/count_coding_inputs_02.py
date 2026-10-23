"""Offline whole-string counting of observed and counterfactual coding inputs."""
import ast,base64,hashlib,importlib.metadata,json,os,sys
from pathlib import Path
Z=Path(__file__).resolve().parent;os.umask(0o077)
T=Z.parent/'terminal-token-pairing-20261012-01/pinned-host-tokenizer';sys.path.insert(0,str(T))
source=Z/'checkout/benchmarks/agent_supervisor/container_coding/terminal_input_token_comparison.py'
nodes={n.targets[0].id:n.value for n in ast.parse(source.read_bytes()).body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name)}
def const(name):return ast.literal_eval(nodes[name])
assert importlib.metadata.version('tiktoken')==const('TOKENIZER_VERSION')
bpe=Path('/tmp/data-gym-cache')/hashlib.sha1(const('BPE_URL').encode()).hexdigest();raw=bpe.read_bytes()
assert hashlib.sha256(raw).hexdigest()==const('BPE_SHA256')
import tiktoken
pattern='|'.join(ast.literal_eval(nodes['_PATTERN'].args[0]))
ranks={base64.b64decode(a,validate=True):int(b) for a,b in (line.split() for line in raw.splitlines())}
encoding=tiktoken.Encoding(const('ENCODING'),pat_str=pattern,mergeable_ranks=ranks,special_tokens={'<|endoftext|>':199999,'<|endofprompt|>':200018})
def wire(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
digest=hashlib.sha256(wire({'name':encoding.name,'pattern':encoding._pat_str,'special_tokens':encoding._special_tokens}))
for token,rank in sorted(ranks.items(),key=lambda item:item[1]):
 digest.update(rank.to_bytes(4,'big'));digest.update(len(token).to_bytes(4,'big'));digest.update(token)
assert digest.hexdigest()==const('TOKENIZER_SHA256')
R=Z/'checked-worker-run-04';pre=json.loads((R/'native-budget-preparation.json').read_bytes())
view=(R/'view-packet.json').read_text();expanded=(R/'expanded-packet.json').read_text();observed=pre['event']['rendered_input']['text']
assert observed.count(view)==1
counterfactual=observed.replace(view,expanded)
def measure(text):
 tokens=encoding.encode(text,allowed_special=set(),disallowed_special=());assert encoding.decode(tokens)==text
 return {'sha256':hashlib.sha256(text.encode()).hexdigest(),'bytes':len(text.encode()),'tokens':len(tokens)}
a,b=measure(observed),measure(counterfactual)
assert all(a[k]==pre['event']['rendered_input'][k] for k in a)
assert a['bytes']<=256000<b['bytes']
report={'schema':'checked-worker-local-coding-input-comparison@1','observed':a,'expanded_counterfactual':b,'local_input_token_difference':b['tokens']-a['tokens'],'local_input_token_reduction_percent':round(100*(b['tokens']-a['tokens'])/b['tokens'],4),'counterfactual_dispatched':False,'counterfactual_valid_checked_artifact':False,'expanded_byte_bound_refusal_verified':True,'tokenizer_version':const('TOKENIZER_VERSION'),'encoding':const('ENCODING'),'vocabulary_sha256':digest.hexdigest(),'bpe_sha256':hashlib.sha256(raw).hexdigest(),'whole_strings_counted':True,'provider_calls':0,'provider_usage_measured':False,'task_total_savings_measured':False,'training_steps':0,'scope':'Same complete authored coding-input text except semantic view versus expanded packet; expanded text exceeds bound and is an unadmitted counterfactual.'}
with (Z/'coding-input-comparison-02.json').open('x') as f:json.dump(report,f,sort_keys=True,indent=2);f.write('\n')
print(json.dumps(report))
