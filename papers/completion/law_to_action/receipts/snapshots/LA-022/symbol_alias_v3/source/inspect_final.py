#!/usr/bin/env python3
"""Inspect actual compiled Law paper and final artifact; no scientific execution."""
from __future__ import annotations
import argparse,ast,hashlib,json,re,subprocess,zipfile
from pathlib import Path

TEMPLATES={'neurips_2026_vericode_workshop.tex':'c1c74133705d906972ee7571ee34f57122da5088e9f09ffe9dacb01cf0db1250','neurips_2026_vericode.sty':'2944ec0d4f64dba353827e9ead104da1a9ac81b4057f4ff40969c693632a1e11','checklist.tex':'780ba13c480f652dcc42e69ed61a752ce0ea270f15d332d4a45b059dabad84f6'}
def need(v,m):
    if not v:raise RuntimeError(m)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return p.read_text(encoding='utf-8')
def without_instructions(text):
    result,n=re.subn(r'%%% BEGIN INSTRUCTIONS %%%.*?%%% END INSTRUCTIONS %%%\s*','',text,count=1,flags=re.S)
    need(n==1,'Instruction block missing');return result

def checklist_skeleton(text,original=False):
    if original:text=without_instructions(text)
    # Preserve all questions, headings, guidelines and comments exactly; mask only
    # the 16 explicit answer and justification fields (one source line each).
    lines=text.splitlines()
    out=[]
    for line in lines:
        if r'\item[] Answer:' in line:
            line=re.sub(r'\\answer(?:TODO|Yes|No|NA)\{\}',r'\\answerFIELD{}',line,count=1)
        elif r'\item[] Justification:' in line:line=line[:line.index('Justification:')+len('Justification:')]+' FIELD'
        out.append(line.rstrip())
    return '\n'.join(out).strip()
def inspect(paper,build,archive,analysis):
    repo=paper.parents[2];main=read(paper/'manuscript/main.tex');results=read(paper/'manuscript/results.tex');style=paper/'manuscript/neurips_2026_vericode.sty';checklist=read(paper/'manuscript/checklist.tex')
    for name,h in TEMPLATES.items():need(sha(repo/'papers'/name)==h,'Shared template changed: '+name)
    need(sha(style)==TEMPLATES['neurips_2026_vericode.sty'],'Copied official style changed')
    need(r'\usepackage{neurips_2026_vericode}'in main,'Anonymous research style missing')
    need(not re.search(r'\\(?:documentclass|usepackage)\[[^\]]*(?:final|preprint|nonanonymous|sglblind|competition)',main,re.I),'Non-anonymous style option')
    need('neurips_2026.sty'not in main and 'sglblindworkshop'not in main,'Wrong template')
    need(r'\input{checklist}'in main or r'\input{checklist.tex}'in main,'Checklist not included')
    need(re.search(r'\\input\{checklist(?:\.tex)?\}',main).start()>main.index(r'\bibliography'),'Checklist precedes bibliography')
    need(checklist_skeleton(checklist)==checklist_skeleton(read(repo/'papers/checklist.tex'),True),'Official checklist questions/guidelines changed')
    answers=re.findall(r'\\item\[\] Answer:\s*\\answer(Yes|No|NA)\{\}',checklist)
    justifications=re.findall(r'\\item\[\] Justification:\s*(.+)',checklist)
    need(len(answers)==len(justifications)==16 and all(len(x.strip())>20 for x in justifications),'Incomplete checklist')
    need('answerTODO'not in checklist and 'justificationTODO'not in checklist,'Checklist placeholders')
    sources=[p for p in (paper/'manuscript').iterdir()if p.suffix in ('.tex','.bib')]
    for p in sources:
        text=read(p)
        need(not re.search(r'\b(?:TBD|TODO|FIXME|PLACEHOLDER)\b',text),'Unresolved source placeholder: '+p.name)
        need(not re.search(r'/home/(?!anonymous/)[\w.-]+/|overleaf\.com/project|barberb',text,re.I),'Identifying source path/link')
        need(not re.search(r'\\(?:fontsize|small|footnotesize|scriptsize|tiny|large|Large|LARGE|huge|Huge|geometry|newgeometry|linespread|enlargethispage|scalebox|resizebox)\b',text),'Manual font/geometry override: '+p.name)
        need(not re.search(r'\\(?:setlength|addtolength|renewcommand|def)\s*\{?\\(?:textwidth|textheight|oddsidemargin|evensidemargin|topmargin|baselinestretch|baselineskip|parskip)\b',text),'Manual page/line spacing override: '+p.name)
    need('24$ pairs'not in results and '24$ cases ($12$ pairs)'in results,'CVE polarity population ambiguity')
    need('19.793533'in results and 'cumulative-active'in results and '18.022665493073873'in results,'Startup resource wording incomplete')
    alias_map=json.loads((paper/'artifact/symbol_aliases.json').read_bytes())
    need(alias_map['schema']=='law-public-technical-symbol-aliases/v1'and len(alias_map['aliases'])==alias_map['symbol_count']==8,'Public symbol map missing')
    need('Implementation identifiers here are neutral aliases'in main,'Compiled-source alias explanation missing')
    with zipfile.ZipFile(archive)as outer:
        prefix='law_to_action_final_supplement/'
        need(outer.read(prefix+'symbol_aliases.json')==(paper/'artifact/symbol_aliases.json').read_bytes(),'Packaged symbol map differs')
        for alias in alias_map['aliases']:
            loc=alias['included_source']
            if 'path'in loc:raw=outer.read(prefix+loc['path'])
            else:
                import io
                with zipfile.ZipFile(io.BytesIO(outer.read(prefix+loc['archive'])))as inner:raw=inner.read(loc['member'])
            need(hashlib.sha256(raw).hexdigest()==alias['included_source_sha256'],'Included symbol source changed')
            nodes=[n for n in ast.walk(ast.parse(raw))if isinstance(n,(ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef))and n.name==alias['original_symbol']]
            need(len(nodes)==1 and nodes[0].lineno==alias['definition_line'],'Symbol source definition differs')
    pdf=build/'main.pdf';aux=read(build/'main.aux');log=read(build/'main.log')
    need(pdf.is_file()and pdf.stat().st_size<=50_000_000,'Actual PDF missing/oversized')
    labels=re.findall(r'\\newlabel\{la-main-text-end\}\{\{[^}]*\}\{(\d+)\}',aux);need(len(labels)==1,'Actual final-sentence page label missing');main_pages=int(labels[0]);need(4<=main_pages<=9,'Main text outside 4–9 pages')
    need(not re.search(r'Overfull \\hbox|There were undefined references|Citation .+ undefined|Reference .+ undefined',log),'PDF overflow or unresolved citation/reference')
    info=subprocess.check_output(['pdfinfo',str(pdf)],text=True);need(re.search(r'^Author:\s*(?:Anonymous Author\(s\))?\s*$',info,re.M),'Identifying PDF Author metadata')
    pages=int(re.search(r'^Pages:\s*(\d+)',info,re.M)[1]);text=subprocess.check_output(['pdftotext','-layout',str(pdf),'-'],text=True);parts=text.split('\f')
    need(len(parts)>=pages,'PDF text extraction incomplete');need('Anonymous Author(s)'in parts[0]and 'Affiliation'in parts[0]and 'Address'in parts[0]and 'email'in parts[0],'Official anonymous block missing')
    need('Workshop on AI for Verifiable Coding'in text,'Workshop footer missing')
    need('References'in parts[main_pages],'References do not start after actual main text')
    need('Checklist'in text and not re.search(r'\b(?:TBD|TODO|FIXME)\b',text),'Rendered checklist/scientific placeholders')
    need(archive.is_file()and archive.stat().st_size<=100_000_000 and zipfile.is_zipfile(archive),'Actual ZIP missing/invalid/oversized')
    proof=json.loads((analysis/'verification.json').read_bytes());need(proof['success']and proof['all_package_files_verified']and proof['all_9933_original_reducer_inputs_verified']and proof['all_45_paired_family_bootstrap_contrasts_recomputed'],'Actual clean artifact analysis failed')
    return {'schema':'law-final-paper-artifact-inspection/v1','success':True,'main_pages':main_pages,'total_pages':pages,'pdf':{'bytes':pdf.stat().st_size,'sha256':sha(pdf)},'archive':{'bytes':archive.stat().st_size,'sha256':sha(archive)},'official_template_hashes':TEMPLATES,'neutral_symbols_resolve_to_included_sources':8,'checklist_questions':16,'answers':answers,'shared_templates_unchanged':True,'anonymous_default_style':True,'source_and_pdf_placeholders_absent':True,'all_actual_resource_cost_and_pairing_analysis_verified':True,'new_scientific_executions':0,'external_submission':False,'limits':'Source/PDF/package conformance and retained-data analysis; not new scientific execution, expert validation or workshop acceptance.'}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--paper',type=Path,required=True);p.add_argument('--build',type=Path,required=True);p.add_argument('--archive',type=Path,required=True);p.add_argument('--analysis',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();need(not a.output.exists(),'Fresh inspection output required');result=inspect(a.paper.resolve(),a.build.resolve(),a.archive.resolve(),a.analysis.resolve());a.output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');print(json.dumps(result,sort_keys=True))
if __name__=='__main__':main()
