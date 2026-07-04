#!/usr/bin/env python3
"""Port SUBSTANCE audit: does each TS 'port' actually reimplement the Python module,
or is it a hollow stub / a wrapper that delegates back to ipfs_datasets_py?

Signals per Python module:
  - pyLoc: effective (non-blank/comment) Python LOC + public symbol count
  - tsFile: best normalized-name TS match in swissknife/src ; tsLoc
  - locRatio = tsLoc / pyLoc  (thin port suspicion when < 0.3)
  - hollow markers in the TS port (stub/simulated/not-implemented/hardcoded)
  - delegation markers (wrapper: calls remote MCP python tool / "Python return dicts")
Verdict: MISSING | WRAPPER | HOLLOW | THIN | SUBSTANTIVE
Reproduce: python3 port_substance_audit.py  (from repo root)
"""
import os, re, json
LOGIC="external/ipfs_datasets/ipfs_datasets_py/logic"
TSROOTS=["swissknife/src/services","swissknife/src"]
OUT="implementation_plan/port-audit/port-substance.json"
OUTMD="implementation_plan/port-audit/port-substance.md"

EXCL=re.compile(r'/(DCEC_Library|Eng-DCEC|ShadowProver|Talos|ErgoAI|demos|examples|tests|benchmarks|__pycache__|conformance)/')
DEMO=re.compile(r'(^|/)(demonstrate_|example_|quickstart_|demo_)[^/]*\.py$|_demo\.py$')

HOLLOW=re.compile(r'not implemented|not bound|not available|FFI not bound|pseudo-proof|deterministic pseudo|simulated — for testing|placeholder|TODO|FIXME|throw new Error\(\s*[\'"`][^\'"`]*not|return null;\s*//|/\*\s*stub|\bstub\b|for now|in practice', re.I)
DELEG=re.compile(r'\binvokeTool\(|\.callTool\(|connector\.dispatch\(|\.dispatch\([^,]+,\s*[\'"`](tdfol_prove|tdfol_batch_prove|legal_text_to_deontic|logic_health)')

def py_eff_loc(txt):
    n=0
    for l in txt.splitlines():
        s=l.strip()
        if not s or s.startswith('#'): continue
        n+=1
    return n
def ts_eff_loc(txt):
    n=0
    for l in txt.splitlines():
        s=l.strip()
        if not s or s.startswith('//') or s.startswith('*') or s.startswith('/*'): continue
        n+=1
    return n

def portable(rel,f):
    if EXCL.search('/logic/'+rel+'/'): return False
    if f=='__init__.py' or DEMO.search('/'+rel): return False
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

def norm(name): return re.sub(r'[^a-z0-9]','',name.lower())

def index_ts():
    idx={}
    for r in TSROOTS:
        for root,_,files in os.walk(r):
            for f in files:
                if f.endswith('.ts') and not f.endswith('.d.ts'):
                    p=os.path.join(root,f)
                    idx.setdefault(norm(f[:-3]),[]).append(p)
    return idx

def pub_syms(txt):
    cls=re.findall(r'^class\s+([A-Z]\w+)',txt,re.M)
    fns=[f for f in re.findall(r'^def\s+([a-z_]\w+)',txt,re.M) if not f.startswith('_')]
    return cls+fns

def best_ts(rel, tsidx):
    base=norm(os.path.basename(rel)[:-3])
    # exact
    if base in tsidx: return tsidx[base]
    # substring both ways
    cand=[]
    for k,paths in tsidx.items():
        if len(base)>=5 and (base in k or k in base): cand.extend(paths)
    return cand[:3]

def main():
    tsidx=index_ts()
    pys=collect_py()
    rows=[]
    for rel in pys:
        txt=open(os.path.join(LOGIC,rel),encoding='utf-8',errors='ignore').read()
        ploc=py_eff_loc(txt); psym=len(pub_syms(txt))
        matches=best_ts(rel,tsidx)
        tsloc=0; hollow=0; deleg=0; tsfiles=[]
        for m in matches:
            t=open(m,encoding='utf-8',errors='ignore').read()
            tsloc+=ts_eff_loc(t)
            hollow+=len(HOLLOW.findall(t))
            deleg+=len(DELEG.findall(t))
            tsfiles.append(m.replace('swissknife/src/','sk:'))
        ratio=round(tsloc/ploc,2) if ploc else 0
        if not matches: verdict='MISSING'
        elif deleg>=2 and tsloc< ploc*0.6: verdict='WRAPPER'
        elif hollow>=3 and ratio<0.5: verdict='HOLLOW'
        elif ratio<0.3 and ploc>=40: verdict='THIN'
        else: verdict='SUBSTANTIVE'
        rows.append({'module':rel,'pyLoc':ploc,'pySymbols':psym,'tsFiles':tsfiles,
                     'tsLoc':tsloc,'locRatio':ratio,'hollowMarkers':hollow,
                     'delegationMarkers':deleg,'verdict':verdict})
    from collections import Counter
    vc=Counter(r['verdict'] for r in rows)
    summary={'modules':len(rows),'pyLocTotal':sum(r['pyLoc'] for r in rows),
             'tsLocTotal':sum(r['tsLoc'] for r in rows),'verdicts':dict(vc)}
    os.makedirs(os.path.dirname(OUT),exist_ok=True)
    json.dump({'summary':summary,'modules':rows},open(OUT,'w'),indent=2)
    flagged=[r for r in rows if r['verdict'] in ('MISSING','WRAPPER','HOLLOW','THIN')]
    flagged.sort(key=lambda r:(r['verdict'],-r['pyLoc']))
    with open(OUTMD,'w') as fh:
        fh.write("# Port substance audit (are the TS ports real, or wrappers/stubs?)\n\n")
        fh.write("Auto-generated by `port_substance_audit.py`. Screening oracle for doc-36 §12.26.\n\n")
        fh.write(f"- Modules: {summary['modules']} | Python eff-LOC: {summary['pyLocTotal']} | TS eff-LOC (matched): {summary['tsLocTotal']}\n")
        fh.write(f"- Verdicts: {json.dumps(summary['verdicts'])}\n\n")
        fh.write("## Flagged modules (MISSING / WRAPPER / HOLLOW / THIN)\n\n")
        fh.write("| Verdict | Module | pyLoc | tsLoc | ratio | hollow | deleg | TS file(s) |\n|---|---|--:|--:|--:|--:|--:|---|\n")
        for r in flagged:
            fh.write(f"| {r['verdict']} | `{r['module']}` | {r['pyLoc']} | {r['tsLoc']} | {r['locRatio']} | {r['hollowMarkers']} | {r['delegationMarkers']} | {', '.join(r['tsFiles']) or '—'} |\n")
    print(json.dumps(summary,indent=2))
    print(f"\nflagged: {len(flagged)} → {OUTMD}")

if __name__=='__main__': main()
