"""Independent source-only audit of the generic poststage Git peer.

Stdlib file reads and AST parsing only. Never imports/executes the reviewed source.
"""
import ast
import datetime
import hashlib
import json
import os
from pathlib import Path
import stat

W=Path('/home/barberb/lift_coding')
SOURCE=W/'maintenance/ranker-objective-scalar-git-helper-source-20261005-01/independent_final_input_review_01.py'
OUT=Path(__file__).resolve().parent
EXPECTED_SIZE=41488
EXPECTED_SHA='3addab8516ffd5bf4ad0bcd5accfb3f82b33560e507a28b0002d210a673d646f'


def require(value,message):
    if value is not True:raise ValueError(message)


def read(path):
    require(path.resolve(strict=True)==path and not path.is_symlink(),'canonical regular source')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    try:
        a=os.fstat(fd);require(stat.S_ISREG(a.st_mode) and a.st_size<=1024**2,'bounded source')
        chunks=[];total=0
        while block:=os.read(fd,65536):
            total+=len(block);require(total<=1024**2,'bounded source growth');chunks.append(block)
        signature=lambda x:tuple(getattr(x,k) for k in ('st_dev','st_ino','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns'))
        require(signature(a)==signature(os.fstat(fd))==signature(path.lstat()) and total==a.st_size,'source changed')
        return b''.join(chunks)
    finally:os.close(fd)


def pin(path,raw):return {'path':str(path),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def main():
    require(__debug__,'optimized audit refused')
    raw=read(SOURCE);binding=pin(SOURCE,raw)
    require(binding['bytes']==EXPECTED_SIZE and binding['sha256']==EXPECTED_SHA,'exact independently reviewed peer source')
    tree=ast.parse(raw,filename=str(SOURCE));text=raw.decode()
    functions={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
    require({'read','git','guards','omit','hf_gate','partition','safe_extra_census','main'}<=set(functions),'required bounded audit functions')
    imports={a.name for n in ast.walk(tree) if isinstance(n,ast.Import) for a in n.names}
    allowed={'argparse','collections','datetime','hashlib','json','os','re','selectors','stat','subprocess','time'}
    require(imports<=allowed and all(n.module=='pathlib' for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)),'stdlib-only imports')
    forbidden={'eval','exec','compile','__import__'}
    require(not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id in forbidden for n in ast.walk(tree)),
        'reviewed sources never imported or dynamically executed')
    main=ast.get_source_segment(text,functions['main']);git=ast.get_source_segment(text,functions['git'])
    require("{'rev-parse', 'ls-tree', 'ls-files', 'cat-file'}" in git and "'/usr/bin/git'" in git and 'selectors.DefaultSelector()' in git and
        "'Git output exceeded cap'" in git and 'process.kill()' in git,'bounded read-only local Git allowlist/drain')
    calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id=='subprocess']
    require(len(calls)==1 and calls[0].func.attr=='Popen','single bounded Git subprocess path only')
    for node in ast.walk(tree):
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='git':
            require(len(node.args)>1 and isinstance(node.args[1],ast.Constant) and node.args[1].value in {'rev-parse','ls-tree','ls-files','cat-file'},
                'every actual plumbing call read-only literal')
    required=["'ranker-objective-scalar-independent-final-Git-input-review@1'",
        "'passed_file_only_actual_HF_gate_and_exact_compact_selection'","'findings': []","'reviewed_input_pins': list(pins.values())",
        "'actual_HF_commit': hf_commit","'combined_selected_files': count","'combined_selected_bytes': size",
        "'stage': prep / 'final-stage-closed-01.json'","'HF_closed': R / 'hf-publication-01/closed.json'",
        "'HF_readback': R / 'hf-public-readback-01.json'","'HF_ledger': R / 'release-publication-ledger-01.json'",
        "'full staged tree/index equals entire parent plus exact increment'","'actual staged object bytes differ from source'",
        "'all nine live staged/parent links preserved'","'original checkout HEAD/index changed'",
        "'independent whole safe-extra namespace census'","'same actual qualified and frozen HF source population'",
        "'entire seal plus sealself retained in full HF denominator'","'original_planning_extractor_not_selected_for_Git'",
        "'next plan remains unqualified'","safe_selector_request=extra['request']","args.output == OUT / 'review-receipt.json'",
        "Path(__file__).resolve() == PUBLIC_SOURCE","'review_receipt_external_to_staged_population': True"]
    require(all(item in text for item in required),'exact stage/HF/source/parent/peer interface gates')
    require(main.index('ledger = hf_gate(')<main.index('live_guards = guards('),'actual HF gate before any live Git calls')
    require("AUTHORITY = ('proof_authority', 'execution_authority', 'completion_authority', 'planner_activation')" in text and
        "'full_task_satisfaction': 'unknown'" in text and "'official_benchmark_score': None" in text,'four closed authority/open task fields')
    require(read(SOURCE)==raw,'source changed before review closure')
    own=Path(__file__).resolve();own_raw=read(own)
    result={'schema':'ranker-objective-scalar-independent-poststage-peer-source-review@1','status':'passed_source_only','outstanding_issues':[],
        'created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'reviewer':pin(own,own_raw),'reviewed_source':binding,
        'source_AST_parses':1,'reviewed_source_imports_or_execution':0,'Git_or_network_calls':0,'native_model_metadata_classifier_test_jobs':0,
        'review_basis':['Full file read plus source/API review against actual candidate, stage, safe selector, policy, HF ledger and parent-owned combined closer.',
            'Bounded inert stdlib source; exact read-only Git command census and source/index/tree/parent/gate pins.',
            'Exact external poststage receipt avoids cyclic staged digests; no source qualification or authority beyond file-only audit.'],
        'proof_authority':False,'execution_authority':False,'completion_authority':False,'planner_activation':False,'full_task_satisfaction':'unknown'}
    path=OUT/'review-receipt.json'
    with path.open('xb') as f:
        f.write((json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n').encode());f.flush();os.fsync(f.fileno())
    print(json.dumps({'status':result['status'],'receipt':pin(path,read(path)),'reviewed_source':binding}))


if __name__=='__main__':main()
