#!/usr/bin/env python3
"""Build and validate the anonymous manuscript from completed measured tables."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess
HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 manuscript=HERE/'editable/manuscript';results=HERE/'editable/results';build=HERE/'editable/build'
 checklist=(manuscript/'checklist.tex').read_text()
 # The official contract requires all per-question guidelines as well as the
 # 16 questions. Only the instruction block and answer fields may differ.
 assert checklist.count('\\item[] Guidelines:')==16,'Official checklist guidelines missing'
 assert len(re.findall(r'\\item\[\] Answer: \\answer(?:Yes|No|NA)\{\}',checklist))==16,'Unanswered checklist question'
 contract=re.sub(r'(?m)^(\s*\\item\[\] Answer:).*$',lambda m:m.group(1)+' <ANSWER>',checklist)
 contract=re.sub(r'(?m)^(\s*\\item\[\] Justification:).*$',lambda m:m.group(1)+' <JUSTIFICATION>',contract)
 contract_sha=hashlib.sha256(contract.encode()).hexdigest()
 assert contract_sha=='f0115ecc8040a773d4d579a668f32fafbb663c416b07ff7a96b6968f30104374','Official checklist questions or guidelines changed'
 for p in results.glob('empirical_*.tex'):
  if 'Layout preview' in p.read_text() or '\\AEColdCosine}{\\textemdash}' in p.read_text():
   raise ValueError(f'Incomplete layout-only table cannot enter final PDF: {p.name}')
 original=HERE/'prior_handoff/editable/manuscript/neurips_2026_vericode.sty'
 assert sha(manuscript/'neurips_2026_vericode.sty')=='2944ec0d4f64dba353827e9ead104da1a9ac81b4057f4ff40969c693632a1e11','Official workshop style identity changed'
 if original.exists():assert sha(original)==sha(manuscript/original.name),'Workshop style was modified'
 build.mkdir(parents=True,exist_ok=True);env=dict(os.environ)
 env['SOURCE_DATE_EPOCH']='1789344000'
 commands=[]
 def run(argv,cwd,log,extra=None):
  e=dict(env);e.update(extra or {})
  with (build/log).open('w') as f:
   done=subprocess.run(argv,cwd=cwd,env=e,stdout=f,stderr=subprocess.STDOUT,timeout=120)
  commands.append({'argv':argv,'cwd':str(cwd.relative_to(HERE)),'log':log,'returncode':done.returncode})
  if done.returncode:raise RuntimeError(f'Build failed; see {log}')
 latex=['pdflatex','-no-shell-escape','-interaction=nonstopmode','-halt-on-error','-file-line-error','-output-directory=../build','main.tex']
 run(latex,manuscript,'final-pass1.log')
 run(['bibtex','main'],build,'final-bibtex.log',{'BIBINPUTS':str(manuscript)+os.pathsep})
 run(latex,manuscript,'final-pass2.log');run(latex,manuscript,'final-pass3.log')
 # TeX diagnostics can contain raw font-encoding bytes; warnings are ASCII.
 log=(build/'main.log').read_text(errors='replace');aux=(build/'main.aux').read_text()
 if 'undefined citations' in log or 'undefined references' in log or 'Overfull \\hbox' in log:raise ValueError('Unresolved typesetting warning')
 # Immediate typeout(\thepage) can precede TeX's final paragraph page break.
 # Use the shipped label plus the actual PDF reference boundary instead.
 found=re.search(r'\\newlabel\{af-main-text-end\}\{\{[^}]*\}\{(\d+)\}',aux);assert found
 main_text_last_page=int(found.group(1))
 pdf=build/'main.pdf';assert pdf.stat().st_size<50_000_000
 run(['pdftotext','-layout',str(pdf),str(build/'paper.txt')],HERE,'pdftotext.log')
 text=(build/'paper.txt').read_text()
 pages=text.split('\f')
 references_page=next((i+1 for i,page in enumerate(pages) if re.search(r'^\s*(?:\d+\s+)?References\s*$',page,re.M)),None)
 assert references_page is not None,'Reference boundary absent from actual PDF'
 main_pages=references_page-1
 assert main_text_last_page<=main_pages and 4<=main_pages<=9,(main_pages,main_text_last_page,'actual PDF main-page limit')
 if re.search(r'\[tbd\]|\[todo\]|Layout preview',text,re.I):raise ValueError('Placeholder leaked into PDF')
 info=subprocess.check_output(['pdfinfo',str(pdf)],text=True)
 if 'Anonymous' not in info:raise ValueError('Anonymous PDF metadata missing')
 report={'main_pages':main_pages,'main_text_last_page':main_text_last_page,'references_start_page':references_page,'pdf_bytes':pdf.stat().st_size,'pdf_sha256':sha(pdf),'official_style_sha256':sha(manuscript/original.name),'official_checklist_contract_sha256':contract_sha,'official_checklist_guideline_blocks':16,
  'commands':commands,'source_date_epoch':env['SOURCE_DATE_EPOCH'],'pdfinfo':info,
  'inputs_sha256':{str(p.relative_to(HERE)):sha(p) for p in sorted(list(manuscript.glob('*.tex'))+list(manuscript.glob('*.bib'))+list(results.glob('*.tex')))}}
 (HERE/'paper_build_validation.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({'main_pages':main_pages,'pdf_sha256':sha(pdf),'pdf_bytes':pdf.stat().st_size}))
if __name__=='__main__':main()
