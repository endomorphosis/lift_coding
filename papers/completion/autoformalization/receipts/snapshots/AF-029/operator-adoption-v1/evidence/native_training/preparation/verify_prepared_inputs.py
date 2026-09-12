"""Verify the committed, train/selection-only AF029 encoder input artifact."""
from pathlib import Path
import hashlib,json,math

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def verify(inputs,manifest,windows,sources,manifest_sha256):
    assert inputs['schema']=='af-frozen-real-semantic-encoder-inputs/v1'
    assert inputs['manifest_sha256']==windows['manifest_sha256']==manifest_sha256
    assert inputs['scope']=='train_and_selection_only' and inputs['final_test_access'] is False
    assert inputs['no_fitting_on_selection'] is True and manifest['splits']=={'train':69,'selection':15}
    assert inputs['model_id']==manifest['model_id'] and inputs['model_revision']==manifest['model_revision']
    expected={}
    for split in ['train','selection']:
        assert len(sources[split])==manifest['splits'][split]
        for row in sources[split]:
            assert row['record_id'] not in expected
            expected[row['record_id']]=(split,row)
    assert len(inputs['rows'])==len(windows['rows'])==len(expected)==84
    wm={r['record_id']:r for r in windows['rows']};assert len(wm)==84
    seen=set();total_windows=0;total_tokens=0
    for row in inputs['rows']:
        rid=row['record_id'];assert rid in expected and rid not in seen;seen.add(rid)
        split,source=expected[rid];assert row['split']==split and row['document_sha256']==source['document_sha256']
        assert row['text_sha256']==hashlib.sha256(source['text'].encode()).hexdigest()
        assert row['text_characters']==len(source['text'])
        assert row['embedding_model']==manifest['model_id'] and row['embedding_revision']==manifest['model_revision']
        assert row['preprocessing_manifest_sha256']==manifest_sha256 and row['source_gold'] is False and row['independent_gold'] is False
        v=row['embedding_vector'];assert len(v)==row['embedding_dimension']==384
        assert all(type(x) in (int,float) and math.isfinite(x) for x in v)
        assert abs(math.sqrt(sum(x*x for x in v))-1)<1e-5 and digest(v)==row['embedding_vector_sha256']
        w=wm[rid];assert w['split']==split and w['text_sha256']==row['text_sha256'] and len(w['windows'])==row['windows']
        end=0
        for index,part in enumerate(w['windows']):
            assert part['offset']==end and 1<=part['content_tokens']<=254
            assert part['input_tokens_with_specials']==part['content_tokens']+2<=256
            if index<len(w['windows'])-1:assert part['content_tokens']==254
            assert len(part['token_ids_sha256'])==64
            end+=part['content_tokens']
        assert end==row['content_tokens']>0
        total_tokens+=end;total_windows+=len(w['windows'])
    assert seen==set(expected)==set(wm)
    return {'rows':84,'splits':{'train':69,'selection':15},'dimensions':384,'content_tokens':total_tokens,'windows':total_windows,'source_rows_omitted':0,'uncovered_content_tokens':0,'final_inputs':0}

def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--paper-root',type=Path,required=True);args=p.parse_args();root=args.paper_root
    prep=root/'evidence/native_training/preparation';mp=prep/'preprocessing_manifest.json';m=json.loads(mp.read_text());ip=root/'data/native_training_inputs.json'
    package=json.loads((prep/'package_manifest.json').read_text())
    for rel,value in package['files'].items():assert sha(root/rel)==value['sha256']
    sources={}
    for split in ['train','selection']:
        path=root/'receipts/snapshots/AF-004'/(split+'.sources.jsonl');assert sha(path)==m['inputs'][split]['sha256'];sources[split]=[json.loads(x)for x in path.read_text().splitlines()if x.strip()]
    result=verify(json.loads(ip.read_text()),m,json.loads((prep/'window_inventory.json').read_text()),sources,sha(mp));print(json.dumps(result,sort_keys=True))
if __name__=='__main__':main()
