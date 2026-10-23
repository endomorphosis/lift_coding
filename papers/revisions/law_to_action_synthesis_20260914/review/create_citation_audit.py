from pathlib import Path
import json,re
root=Path(__file__).resolve().parents[1];review=root/'review'
classic=json.loads((review/'citations_classic.json').read_text())['entries']
modern=json.loads((review/'citations_modern.json').read_text())['records']
infra=json.loads((review/'citations_infrastructure.json').read_text())
bykey={x['key']:x for x in [*classic,*modern,*infra]}
bib=(root/'manuscript/related_work.bib').read_text()
keys=set(re.findall(r'^@\w+\{([^,]+),',bib,re.M))
aux=(review/'publication-build/main.aux').read_text()
ordered=sorted(((int(n),k) for k,n in re.findall(r'\\bibcite\{([^}]+)\}\{\{(\d+)\}',aux)))
assert len(keys)==40 and {k for n,k in ordered}==keys and keys<=set(bykey)
changes={
'pang2019zanzibar':'Corrected author list using current official USENIX metadata.',
'chen2021codex':'Corrected Michael Petrov; pinned arXiv v2.',
'cutler2024cedar':'Restored Andrew M. Wells as printed in the published paper.',
'sun2024clover':'Updated the valid preprint citation to the published SAIV 2024 chapter.',
'wang2025agentspec':'Updated the valid preprint citation to ICSE 2026 publication metadata.',
'shi2025progent':'Aligned year 2026 with the explicitly cited revised arXiv v3.',
'andriushchenko2025agentharm':'Explicitly cited author-updated arXiv v3 to match the 14-author list.',
'libp2p':'Corrected specification title and revision year 2022.',
'ipfs':'Removed unsupported publication year; recorded consultation date.',
'ucan':'Removed unsupported publication year; recorded consultation date.',
'cvefixes-source':'Added citation for the exact source package; pinned revision verified via primary API.',
'skillcenter-source':'Added dataset citation; pinned revision and card metadata verified via primary API.'}
records=[]
preferred_urls={
'wang2025agentspec':'https://conf.researchr.org/details/icse-2026/icse-2026-research-track/29/AgentSpec-Customizable-Runtime-Enforcement-for-Safe-and-Reliable-LLM-Agents',
'sun2024clover':'https://link.springer.com/chapter/10.1007/978-3-031-65112-0_7',
'chen2021codex':'https://arxiv.org/pdf/2107.03374v2',
'andriushchenko2025agentharm':'https://arxiv.org/pdf/2410.09024v3'}
def public_fields(value):
 if isinstance(value,dict):return {k:public_fields(v) for k,v in value.items() if k!='local_evidence'}
 if isinstance(value,list):return [public_fields(v) for v in value]
 return value
for number,key in ordered:
 x=bykey[key]
 sources=x.get('sources',x.get('primary_sources',[]))
 if not sources:sources=[{'url':x['primary_url'],'basis':x['basis']}]
 sources=public_fields(sources)
 if key in preferred_urls:
  assert any(s['url']==preferred_urls[key] for s in sources)
  sources=sorted(sources,key=lambda s:s['url']!=preferred_urls[key])
 metadata=x.get('verified_metadata',{})
 title=metadata.get('title',x.get('title',key))
 if isinstance(title,list):title='; '.join(title)
 title=title.replace('{Google}','Google')
 records.append({'number':number,'key':key,'title':title,'existence':'verified','action':changes.get(key,'Retained verified metadata.'),'primary_sources':sources,'access_limitation':'Direct thesis download was blocked; existence, metadata, and relevant content were checked through live indexed author and institutional pages.' if key=='miller2006robust' else None})
audit={'checked_at':'2026-09-14','cited_references':40,'unmatched_citations':0,'unused_bibliography_entries':0,'scope':'Existence, scholarly metadata, version consistency, and support for the cited background claims; not an independent replication of cited experiments.','records':records}
(review/'citation_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
text='''# Citation audit — Law to Action

Checked 14 September 2026. **All 40 references cited in the revised PDF correspond to real primary sources.** Every citation key resolves, and the selected bibliography contains no unused entries.

The review checked titles, author lists, dates, venues, pagination, DOI/arXiv identities, and the background claims supported by each reference. It used official proceedings, publisher-deposited Crossref metadata, author/institution pages, arXiv records and selected PDFs, official protocol documentation, and the pinned dataset APIs. Matching a DOI URL alone was not treated as sufficient verification. This is a citation audit, not a replication of the referenced studies.

## Corrections and version choices

- Zanzibar: replaced the incorrect author list using current USENIX metadata.
- Code-model paper: corrected Michael Petrov and pinned arXiv v2.
- Cedar: restored the published author form Andrew M. Wells.
- Clover and AgentSpec: replaced valid preprint entries with verified published versions.
- Progent: aligned the year with the cited 2026 revision.
- AgentHarm: retained all14 authors of the author-updated arXiv v3 and identified that version explicitly. The original proceedings version has12 authors; this is a version difference, not a fabricated reference.
- libp2p: corrected the specification title and2022 revision date. IPFS and UCAN entries now use access dates without inventing publication years.
- Added separate source-package citations for CVEfixes and SkillCenter; their exact revisions were verified via the primary dataset API.
- Corrected the prose to distinguish Catala from the Mlang French tax compiler, and to identify LeanDojo as theorem proving.
- The pinned SkillCenter card declares a custom license category. The checklist no longer describes it as unqualified MIT packaging; nested source terms remain distinct.

The original39 bibliography entries, including the uncited workshop page, were all checked. The workshop entry was moved to the format audit, and two dataset entries were added, leaving40 cited references. Miller's dissertation was confirmed through live indexed author and institutional primary pages; direct PDF retrieval was blocked or timed out. The audit does not claim a full direct reading of that PDF. The accompanying JSON records the primary evidence and access limitation for each reference.

## Reference-by-reference primary evidence

| PDF no. | Citation key | Verified work and primary evidence | Action |
|---|---|---|---|
'''
for x in records:
 url=x['primary_sources'][0]['url']; title=x['title'].replace('|','/')
 text+=f"| {x['number']} | `{x['key']}` | [{title}]({url}) | {x['action']} |\n"
text+='''
## Format and scientific scope

The revised paper has **7 main pages**, including the figure and tables. References and appendices bring the full PDF to23 pages. The [official workshop policy](https://vericodegen.github.io/cfp.html) permits4–9 main pages and excludes references and technical appendices from that count. The supplied style, anonymous author block, and checklist questions/answers remain unchanged.

The original architecture has been integrated with the existing900-cell fixed-action study. Richer logical views, learned proposals, context minification, program-state reuse, and closed-loop planning are separated from measured claims. No new experiment, semantic validation, or scientific result was added during this revision.
'''
# Normalize spacing in prose before saving the public report.
for a,b in [('all14','all 14'),('has12','has 12'),('and2022','and 2022'),('original39','original 39'),('leaving40','leaving 40'),('to23','to 23'),('permits4','permits 4'),('existing900','existing 900')]:text=text.replace(a,b)
(review/'citation_audit.md').write_text(text)
print('Created complete 40-reference audit and verified exact citation-key coverage.')
