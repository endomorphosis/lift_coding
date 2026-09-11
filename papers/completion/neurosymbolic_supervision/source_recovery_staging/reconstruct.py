"""Deterministically reconstruct editable text from the reviewed PDF extraction.

Formatting is staging quality; source-word and symbol ambiguities are audited.
"""
from pathlib import Path
import collections, hashlib, json, re, shutil, unicodedata

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PDF = ROOT / 'papers/vericodegen_neurosymbolic_supervision_workshop_draft.pdf'
TEXT = HERE.parent / 'paper_extracted.txt'
PAGES = TEXT.read_text().split('\f')
TITLE = 'Proof-Carrying Neurosymbolic Supervision: State, Logic-Governed Decisions, and Test-Evidence Reuse'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def tex(text):
    text = unicodedata.normalize('NFC', text)
    replacements = {'\\':r'\textbackslash{}','{':r'\{','}':r'\}','$':r'\$','&':r'\&','#':r'\#','%':r'\%','_':r'\_','~':r'\textasciitilde{}','^':r'\textasciicircum{}'}
    return ''.join(replacements.get(c,c) for c in text)


EQUATIONS = {
1:r'''\begin{equation}\begin{aligned}
e = (&\mathrm{claim},\mathrm{subjects},\mathrm{assumptions},\mathrm{scope},\mathrm{dependencies},\\
&\mathrm{translation\ profile},\mathrm{checker\ result},\mathrm{environment},\mathrm{policy},\mathrm{provenance}).
\end{aligned}\tag{1}\end{equation}''',
2:r'''\begin{equation}\begin{aligned}
\mathrm{Publish}(s')\Rightarrow{}&\mathrm{CurrentParent}(s)\land\mathrm{Authorized}(a,s)\\
&\land\mathrm{Scoped}(a)\land\mathrm{CompleteManifest}(q,s')\\
&\land\mathrm{EvidenceAdmitted}(q,s')\land\mathrm{CAS}(s,s').
\end{aligned}\tag{2}\end{equation}''',
3:r'''\begin{equation}
\mathrm{TargetChecker}(\tau(\varphi))=\mathrm{accepted}\quad\not\Rightarrow\quad\mathrm{SourceSemantics}\models\varphi.
\tag{3}\end{equation}''',
4:r'''\begin{equation}
\text{Abstract state}=\mathrm{Const}\times\mathrm{Interval}\times\mathrm{Nullness}\times\mathrm{Exceptions}\times\mathrm{Effects}.
\tag{4}\end{equation}''',
5:r'''\begin{equation}
G\land\neg A\text{ is UNSAT}\quad\Rightarrow\quad G\Rightarrow A\quad\text{(in the encoded theory).}
\tag{5}\end{equation}''',
6:r'''\begin{equation}
A\Rightarrow I,\quad I\land B\text{ is UNSAT},\quad\mathrm{Symbols}(I)\subseteq\mathrm{Symbols}(A)\cap\mathrm{Symbols}(B).
\tag{6}\end{equation}''',
}

unicode_map = {'2227':r'\ensuremath{\land}','00AC':r'\ensuremath{\neg}','2192':r'\ensuremath{\rightarrow}',
'03B8':r'\ensuremath{\theta}','03C0':r'\ensuremath{\pi}','2032':r'\ensuremath{\prime}',
'21D2':r'\ensuremath{\Rightarrow}','03C4':r'\ensuremath{\tau}','03C6':r'\ensuremath{\varphi}',
'0398':r'\ensuremath{\Theta}','00D7':r'\ensuremath{\times}','2286':r'\ensuremath{\subseteq}',
'2229':r'\ensuremath{\cap}','00B7':r'\ensuremath{\cdot}','0142':r'\l{}','015B':r"\'{s}",'017A':r"\'{z}",
'0338':r'\ensuremath{\not}', '0301':r"\'{}"}


def record_line(raw):
    match = re.match(r'^ {0,3}(\d{1,3}) {2,}(\S.*)$',raw)
    if match:
        return int(match[1]), match[2], match.start(2)
    return None, raw, None


def main():
    (HERE/'audit').mkdir(exist_ok=True)
    for source in ['neurips_2026_vericode.sty','checklist.tex']:
        shutil.copyfile(ROOT/'papers'/source,HERE/source)
    out=[]; audit={'sections':[],'tables':[],'equations':[],'references':[],'numbered_lines':{},'uncertain_math_lines':[],'layout_blocks':[]}
    refs=[]
    reference_lines=[]
    for raw in PAGES[9].splitlines():
        number,text,column=record_line(raw)
        if number is not None and number!=307:
            reference_lines.append((number,text))
    current=[]
    for number,text in reference_lines:
        match=re.match(r'\[(\d+)\]\s*(.*)',text)
        if match:
            if current:refs.append(current)
            current=[int(match[1]),match[2],[number]]
        else:
            current[1]+=' '+text;current[2].append(number)
    if current:refs.append(current)
    reftex=[r'\begin{thebibliography}{12}']
    bib=[]
    for index,text,lines in refs:
        reftex.append(r'\bibitem{baseline%02d} '%index+tex(text))
        bib.append('@misc{baseline%02d,\n  note = {%s},\n  annote = {Literal PDF-page-10 transcription; structured author/title fields require reconciliation}\n}\n'%(index,tex(text)))
        audit['references'].append({'id':index,'pdf_page':10,'pdf_line_numbers':lines,'transcribed_entry':unicodedata.normalize('NFC',text),'status':'literal_entry_transcribed; metadata not independently verified'})
    reftex.append(r'\end{thebibliography}')
    (HERE/'references.tex').write_text('\n\n'.join(reftex)+'\n')
    (HERE/'references.bib').write_text('\n'.join(bib))
    abstract=[]
    for raw in PAGES[0].splitlines():
        number,text,column=record_line(raw)
        if number is not None and 1<=number<=19: abstract.append(tex(text))
    (HERE/'abstract.tex').write_text('\n'.join(abstract)+'\n')
    for page,content in enumerate(PAGES,1):
        if not content.strip():continue
        out.append('%% Original PDF page %d'%page)
        lines=content.splitlines()
        if page==10:out.append(r'\clearpage\input{references.tex}')
        if page==11:out.append(r'\clearpage')
        rawblock=[]
        def flush():
            if not rawblock:return
            rawtext='\n'.join(rawblock).strip('\n')
            rawblock.clear()
            if not rawtext.strip():return
            tags=re.findall(r'\((\d+)\)\s*$',rawtext,re.M)
            if len(tags)==1 and int(tags[0]) in EQUATIONS:
                num=int(tags[0]);out.append(r'\setcounter{equation}{%d}'%(num-1));out.append(EQUATIONS[num])
                audit['equations'].append({'number':num,'pdf_page':page,'status':'native LaTeX reconstructed and visually compared with original rendered page','extracted_text':rawtext,'tex_sha256':hashlib.sha256(EQUATIONS[num].encode()).hexdigest()})
                return
            used=rawtext.splitlines()
            left=min(len(s)-len(s.lstrip()) for s in used if s.strip())
            normalized='\n'.join(s[left:] for s in used)
            out.extend([r'\begingroup\fontsize{7}{8.4}\selectfont',r'\begin{alltt}',tex(normalized),r'\end{alltt}\endgroup'])
            audit['layout_blocks'].append({'pdf_page':page,'sha256':hashlib.sha256(rawtext.encode()).hexdigest(),'line_count':len(used),'status':'editable preformatted text; semantic table cells/inline scripts not fully typeset'})
        for lineno,raw in enumerate(lines,1):
            number,text,column=record_line(raw)
            if number is not None:
                audit['numbered_lines'][str(number)]={'pdf_page':page,'pdf_extraction_line':lineno,'source_text':text}
                if page==10 or (page==1 and number<=19):continue
                flush()
                if any(char in text for char in '∧¬→θπ′⇒τφΘ×⊆∩='):
                    audit['uncertain_math_lines'].append({'pdf_page':page,'pdf_line':number,'text':text,'status':'inline/subscript positioning requires visual reconciliation'})
                heading=re.match(r'^(\d+(?:\.\d+){0,3}|[A-M](?:\.\d+){0,3})\s{2,}(.+)$',text)
                if heading:
                    depth=heading[1].count('.')
                    command=['section','subsection','subsubsection','paragraph'][min(depth,3)]
                    out.append('\\%s*{%s %s}'%(command,heading[1],tex(heading[2])))
                    audit['sections'].append({'number':heading[1],'title':heading[2],'pdf_page':page,'pdf_line':number,'status':'editable heading and adjacent prose transcribed'})
                elif column is not None and column>=10:
                    out.append(r'\noindent '+tex(text)+r'\par')
                else:
                    out.append('%% PDF p.%d line %d'%(page,number))
                    out.append(tex(text))
            elif page==10:continue
            elif page==1 and (not any(record_line(l)[0] is not None for l in lines[:lineno])):continue
            elif re.match(r'^\s*\d{1,2}\s*$',raw):continue
            elif 'Submitted to NeurIPS 2026 Workshop' in raw:continue
            elif not raw.strip():
                flush();out.append('')
            else:
                rawblock.append(raw)
                table=re.search(r'Table (\d+):\s*(.*)',raw)
                if table:audit['tables'].append({'number':int(table[1]),'pdf_page':page,'caption_first_line':table[2],'status':'all extracted words/numbers retained in editable preformatted layout; row/cell alignment requires visual reconciliation'})
        flush()
    (HERE/'transcription.tex').write_text('\n'.join(out)+'\n')
    preamble=r'''\documentclass{article}
\PassOptionsToPackage{numbers,compress}{natbib}
\usepackage{neurips_2026_vericode}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{amsmath,amssymb,alltt,booktabs,microtype,url,hyperref}
'''
    preamble+='\n'.join(r'\DeclareUnicodeCharacter{%s}{%s}'%(k,v) for k,v in unicode_map.items())+'\n'
    preamble+=r'\title{'+tex(TITLE)+'}\n'+r'\workshoptitle{AI for Verifiable Coding}'+'\n'+r'\author{Anonymous Authors}'+'\n'
    preamble+=r'''\hypersetup{pdftitle={Proof-Carrying Neurosymbolic Supervision: source reconstruction staging},pdfauthor={Anonymous Authors},pdfsubject={Unverified editorial reconstruction; no new experiment results}}
\begin{document}
\maketitle
\begin{abstract}
\input{abstract.tex}
\end{abstract}
\input{transcription.tex}
\end{document}
'''
    (HERE/'main.tex').write_text(preamble)
    numbered=set(map(int,audit['numbered_lines']))
    assert numbered==set(range(1,779)), sorted(set(range(1,779))-numbered)
    assert sorted(t['number'] for t in audit['tables'])==list(range(1,19))
    assert sorted(t['number'] for t in audit['equations'])==list(range(1,7))
    assert len(refs)==12
    audit['coverage']={'original_pdf_pages':28,'numbered_pdf_lines':len(numbered),'missing_numbered_lines':[],
                       'sections_and_subsections':len(audit['sections']),'tables':18,'numbered_equations':6,'references':12,
                       'algorithm':{'number':1,'pdf_page':27,'steps':17,'status':'all numbered steps transcribed'},
                       'literal_TBD_cells_in_original':TEXT.read_text().count('[TBD]'),
                       'literal_TBD_cells_in_tex':(HERE/'transcription.tex').read_text().count('[TBD]'),
                       'task_complete':False,'full_visual_fidelity_verified':False}
    audit['sources']={str(PDF.relative_to(ROOT)):sha(PDF),str(TEXT.relative_to(ROOT)):sha(TEXT),
                      'papers/neurips_2026_vericode.sty':sha(ROOT/'papers/neurips_2026_vericode.sty'),
                      'papers/neurips_2026_vericode_workshop.tex':sha(ROOT/'papers/neurips_2026_vericode_workshop.tex'),
                      'papers/checklist.tex':sha(ROOT/'papers/checklist.tex')}
    audit['discrepancies']=[
        {'id':'NS-REC-001','status':'open','pdf_pages':list(range(1,29)),'issue':'PDF extraction does not recover original LaTeX macros, semantic table cells, citation commands, inline sub/superscripts, or exact pagination.'},
        {'id':'NS-REC-002','status':'open','pdf_pages':[10],'issue':'Bibliography wording is transcribed; references.bib preserves full entries in note fields. Structured author/title metadata, accents, and DOI linebreak joining need reconciliation; no bibliographic fact was independently checked.'},
        {'id':'NS-REC-003','status':'open','pdf_pages':list(range(1,29)),'issue':'Explicit end-of-line hyphens are retained; distinguish linguistic hyphens from automatic line-wrap hyphenation before polishing.'},
        {'id':'NS-REC-004','status':'open','pdf_pages':[1,8,24,25,28],'issue':'All original missing-results/disclosure/checklist placeholders remain. No experiment, result, author identity, or checklist answer was supplied.'},
        {'id':'NS-REC-005','status':'open','pdf_pages':[28],'issue':'Original obsolete checklist-placeholder wording is preserved for reconciliation. Official checklist.tex is copied separately, unchanged and unanswered; do not treat original questionnaire-absence wording as current fact.'},
        {'id':'NS-REC-006','status':'unresolved_access','pdf_pages':list(range(1,29)),'issue':'User-supplied Overleaf project 6a7b4742e20ac910c422a7e0 could not previously be retrieved; contents and paper mapping remain unverified. This staging is reconstruction, not recovered original source.'},
    ]
    (HERE/'audit/reconstruction.json').write_text(json.dumps(audit,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps(audit['coverage']))


if __name__=='__main__':main()
