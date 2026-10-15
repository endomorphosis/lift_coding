from pathlib import Path
import re
root=Path(__file__).resolve().parents[1]
p=root/'manuscript/related_work.bib'
def records(text):
 out={}
 for m in re.finditer(r'^@\w+\{([^,]+),',text,re.M):
  start=m.start(); pos=m.end(); depth=1
  while depth:
   if text[pos]=='{' and text[pos-1]!='\\':depth+=1
   elif text[pos]=='}' and text[pos-1]!='\\':depth-=1
   pos+=1
  out[m.group(1)]=text[start:pos]
 return out
entries=records(p.read_text())
for name in ['corrections_classic.bib','corrections_modern.bib']:entries.update(records((root/'review'/name).read_text()))
for key in ['mcp','mcp-auth','quack','ipfs','libp2p','ucan']:
 entry=entries[key]
 entry=re.sub(r'note = \{[^\n]+\}', 'note = {Accessed 14 September 2026.}',entry)
 if key in ['ipfs','ucan']:entry=re.sub(r'^  year = .*\n','',entry,flags=re.M)
 if key=='quack':entry=entry.replace('The duckdb client-server protocol','The DuckDB Client-Server Protocol')
 if key=='libp2p':
  entry=entry.replace('libp2p connections specification','Connection Establishment in libp2p').replace('year = {2026}','year = {2022}').replace('Accessed 14 September 2026.','Revision r1, 7 December 2022. Accessed 14 September 2026.')
 entries[key]=entry
entries.pop('vericode2026cfp')
entries['cvefixes-source']=r'''@misc{cvefixes-source,
  author = {{hitoshura25}},
  title = {{CVEfixes} dataset package},
  year = {2025},
  url = {https://huggingface.co/datasets/hitoshura25/cvefixes},
  note = {Dataset snapshot. Accessed 14 September 2026.}
}'''
entries['skillcenter-source']=r'''@misc{skillcenter-source,
  author = {{Tommysha}},
  title = {{SkillCenter Bundles}},
  year = {2026},
  url = {https://huggingface.co/datasets/Tommysha/skillcenter-bundles},
  note = {Dataset snapshot. Accessed 14 September 2026.}
}'''
p.write_text('% Verified primary-source bibliography; evidence and version choices are documented in review/citation_audit.md.\n\n'+'\n\n'.join(entries.values())+'\n')
# The old eight-key bibliography is not loaded and would duplicate corrected entries.
legacy=root/'manuscript/references.bib'
if legacy.exists():legacy.rename(root/'review/unused_original_references.bib')
print('Merged',len(entries),'verified bibliography entries.')
