#!/usr/bin/env python3
"""Synthetic integration qualification. Fake HTTP response; zero model calls."""
from pathlib import Path
import importlib.util,json,threading,http.server,sys
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('natural_a',HERE/'run_natural_a.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
sys.path.insert(0,str(HERE.parent/'pipeline'));import native_c
api=native_c.setup(False)
source='  An operator   shall retain records.  '
normalized='An operator shall retain records.'
payload={'formulas':[{'operator':{'family':'deontic','system':'D','symbol':'O','label':'obligation'},'predicate':{'name':'retain records','arguments':['operator'],'role':None},'conditions':[],'exceptions':[],'provenance':{'start_char':0,'end_char':len(normalized)}}]}
class H(http.server.BaseHTTPRequestHandler):
 def do_POST(self):
  request=json.loads(self.rfile.read(int(self.headers['Content-Length'])));assert request['messages'][0]['content'].endswith(normalized)
  data=json.dumps({'choices':[{'finish_reason':'stop','message':{'content':json.dumps(payload)}}],'usage':{'prompt_tokens':0,'completion_tokens':0}}).encode();self.send_response(200);self.end_headers();self.wfile.write(data)
 def log_message(self,*args):pass
server=http.server.HTTPServer(('127.0.0.1',0),H);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
out=HERE/'natural_scorer_qualification';out.mkdir(exist_ok=False)
try:result=a.evaluate({'record_id':'constructed:normalization','text':source},api,native_c,out,f'http://127.0.0.1:{server.server_port}')
finally:server.shutdown();server.server_close();thread.join()
assert result['status']=='measured' and all(v['passed'] for v in result['checks'].values()),result
# Same JSON with invalid bounds must fail the independent source binding check.
packet={'record_id':result['record_id'],'text_sha256':result['text_sha256'],'canonical_ir':json.loads(json.dumps(result['canonical_ir'])),'checker_contract':api[4](),'source_text':source}
packet['canonical_ir']['formulas'][0]['provenance']['end_char']=len(normalized)+1
bad=api[3]['provenance_preservation'](packet);assert not bad['passed']
for text,finish in [('```json\n{"formulas":[]}\n```','stop'),('{"formulas":[]}','length'),('{"formulas":[],"reasoning":"extra"}','stop')]:
 try:a.strict_payload({'finish_reason':finish,'message':{'content':text}})
 except (ValueError,json.JSONDecodeError):pass
 else:raise AssertionError('Malformed/truncatedextra response was admitted')
a.write(out/'summary.json',{'all_passed':True,'model_calls':0,'synthetic_http_response':True,'natural_final_test_accessed':False,'positive_result':result,'negative_span_check':bad,'schema_rejection_cases':3});print('Synthetic native scorer integration and rejection checks pass; zero model calls')
