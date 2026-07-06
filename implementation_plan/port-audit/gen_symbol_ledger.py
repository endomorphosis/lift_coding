#!/usr/bin/env python3
"""Symbol-coverage ledger generator for the ipfs_datasets_py/logic → swissknife TS port.
Emits a machine-checkable per-symbol classification: ported | needs-review | na.
This is the concrete mechanism to drive + verify symbol coverage 71.2% → 100% (doc-36 §12.23/PORT-234).
Reproduce: python3 gen_symbol_ledger.py  (from repo root)
"""
import os, re, json, sys

LOGIC="external/ipfs_datasets/ipfs_datasets_py/logic"
TSROOT="swissknife/src"
OUT_JSON="implementation_plan/port-audit/symbol-coverage.json"
OUT_MD="implementation_plan/port-audit/symbol-coverage.md"

EXCL=re.compile(r'/(DCEC_Library|Eng-DCEC|ShadowProver|Talos|ErgoAI|demos|examples|tests|benchmarks|__pycache__)/')
DEMO=re.compile(r'(^|/)(demonstrate_|example_|quickstart_|demo_)[^/]*\.py$|_demo\.py$|/conformance/py_reference_runner\.py$')

# §12.22.3 module-level N/A (host entrypoints / shims / protocol)
NA_MODULES={'api_server.py','cli.py','benchmarks.py','phase7_4_benchmarks.py',
  'integration/logic_verification_utils.py','integration/symbolic_contracts.py',
  'integrations/enhanced_graphrag_integration.py','integrations/unixfs_integration.py',
  'zkp/backends/backend_protocol.py'}
# host-native tracks (PORT-209–213) — symbols here are N/A for the *pure-TS* coverage goal
HOST_NATIVE_MODULES={
  'zkp/backends/provekit_ffi.py','zkp/provekit/cli.py','zkp/backends/simulated.py',
  'external_provers/neural/symbolicai_prover_bridge.py',
  'external_provers/interactive/lean_prover_bridge.py',
  'integration/bridges/prover_installer.py',
}

def portable(rel,f):
    if EXCL.search('/logic/'+rel+'/'): return False
    if f=='__init__.py': return False
    if re.match(r'(test_.*|.*_test|conftest|setup)\.py$',f): return False
    return True

def collect_py():
    out=[]
    for root,_,files in os.walk(LOGIC):
        for f in files:
            if f.endswith('.py'):
                rel=os.path.join(root,f).replace(LOGIC+'/','')
                if portable(rel,f): out.append(rel)
    return sorted(out)

def ts_idents():
    ident=re.compile(r'[A-Za-z_][A-Za-z0-9_]*')
    toks=set()
    for root,_,files in os.walk(TSROOT):
        for f in files:
            if f.endswith('.ts'):
                try: txt=open(os.path.join(root,f),encoding='utf-8',errors='ignore').read()
                except: continue
                toks.update(ident.findall(txt))
    return toks

def variants(sym):
    v={sym, sym.replace('_','')}
    parts=sym.split('_')
    if len(parts)>1:
        v.add(parts[0]+''.join(p.capitalize() for p in parts[1:]))
        v.add(''.join(p.capitalize() for p in parts))
    return {x for x in v if len(x)>=4}

def pubsyms(path):
    txt=open(os.path.join(LOGIC,path),encoding='utf-8',errors='ignore').read()
    cls=re.findall(r'^class\s+([A-Z]\w+)',txt,re.M)
    fns=[f for f in re.findall(r'^def\s+([a-z_]\w+)',txt,re.M)
         if not f.startswith('_') and f not in ('main','run','setup')]
    return list(dict.fromkeys(cls+fns))

def main():
    toks=ts_idents(); toks_lc={t.lower() for t in toks}
    def present(sym):
        for v in variants(sym):
            if v in toks or v.lower() in toks_lc: return True
        return False
    modules=[]
    tot_sym=tot_ported=tot_review=tot_na=0
    for rel in collect_py():
        is_demo=bool(DEMO.search('/'+rel))
        is_na = rel in NA_MODULES or is_demo
        is_host= rel in HOST_NATIVE_MODULES
        syms=pubsyms(rel)
        entries=[]
        for s in syms:
            if is_na:
                cls='na'; reason='demo/example' if is_demo else 'module-level N/A (shim/host-entrypoint/protocol)'
            elif is_host:
                cls='na'; reason='host-native (PORT-209–213 track)'
            elif present(s):
                cls='ported'; reason=''
            else:
                cls='needs-review'; reason='not present as TS identifier — port or map to consolidation'
            entries.append({'symbol':s,'class':cls,'reason':reason})
            tot_sym+=1
            if entries[-1]['class']=='ported': tot_ported+=1
            elif entries[-1]['class']=='na': tot_na+=1
            else: tot_review+=1
        n_rev=sum(1 for e in entries if e['class']=='needs-review')
        n_por=sum(1 for e in entries if e['class']=='ported')
        n_na =sum(1 for e in entries if e['class']=='na')
        cov = (n_por/(n_por+n_rev)) if (n_por+n_rev)>0 else 1.0
        modules.append({'module':rel,'subpackage':(rel.split('/')[0] if '/' in rel else '(root)'),
            'na':is_na or is_host,'symbolCount':len(syms),'ported':n_por,'needsReview':n_rev,'naCount':n_na,
            'coverage':round(cov,4),'symbols':entries})
    # denominators for the pure-TS coverage goal (exclude na modules & na symbols)
    review_modules=[m for m in modules if not m['na'] and m['needsReview']>0]
    denom=tot_ported+tot_review
    ledger={
      'schemaVersion':'2026-07-03',
      'source':{'ipfs_datasets_logic':LOGIC,'swissknife_ts':TSROOT},
      'pins':{'ipfs_datasets':'4672e0b2','swissknife':'47e9e19'},
      'summary':{
        'modulesTotal':len(modules),
        'symbolsTotal':tot_sym,
        'ported':tot_ported,'needsReview':tot_review,'na':tot_na,
        'pureTsCoveragePercent':round(100*tot_ported/denom,1) if denom else 100.0,
        'modulesNeedingReview':len(review_modules),
      },
      'modules':modules,
    }
    os.makedirs(os.path.dirname(OUT_JSON),exist_ok=True)
    json.dump(ledger,open(OUT_JSON,'w'),indent=2)
    # human-readable summary
    from collections import defaultdict
    g=defaultdict(lambda:[0,0])
    for m in review_modules:
        g[m['subpackage']][0]+=1; g[m['subpackage']][1]+=m['needsReview']
    with open(OUT_MD,'w') as fh:
        fh.write("# Logic-submodule → TypeScript symbol-coverage ledger\n\n")
        fh.write("Auto-generated by `gen_symbol_ledger.py`. **Independent cross-check** of the "
                 "authoritative `../conformance/symbol-map.json` (PORT-234 gate). "
                 "Companion to doc-36 §12.23/§12.24. Do not hand-edit; re-run the generator.\n\n")
        s=ledger['summary']
        fh.write(f"- Pins: ipfs_datasets `{ledger['pins']['ipfs_datasets']}`, swissknife `{ledger['pins']['swissknife']}`\n")
        fh.write(f"- Modules: {s['modulesTotal']} | Symbols: {s['symbolsTotal']}\n")
        fh.write(f"- **Pure-TS symbol coverage: {s['pureTsCoveragePercent']}%** "
                 f"(ported {s['ported']} / needs-review {s['needsReview']}; N/A {s['na']})\n")
        fh.write(f"- Modules needing review: **{s['modulesNeedingReview']}**\n\n")
        fh.write("## Needs-review by subpackage\n\n| Subpackage | Modules | Symbols to resolve |\n|---|---:|---:|\n")
        for sub in sorted(g,key=lambda k:-g[k][1]):
            fh.write(f"| `{sub}` | {g[sub][0]} | {g[sub][1]} |\n")
        fh.write("\n## Modules needing review (each symbol → port or map to consolidation)\n\n")
        for m in sorted(review_modules,key=lambda m:(m['coverage'],-m['needsReview'])):
            miss=[e['symbol'] for e in m['symbols'] if e['class']=='needs-review']
            fh.write(f"- **{m['module']}** — {m['coverage']*100:.0f}% "
                     f"({m['ported']}/{m['ported']+m['needsReview']}) → resolve: "
                     f"{', '.join(miss[:12])}{'…' if len(miss)>12 else ''}\n")
    print(f"WROTE {OUT_JSON} and {OUT_MD}")
    print(json.dumps(ledger['summary'],indent=2))

if __name__=='__main__':
    main()
