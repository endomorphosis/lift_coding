from pathlib import Path
E=Path(__file__).resolve().parent
p=E/'editable/manuscript/main.tex';s=p.read_text()
s=s.replace('The evaluated T2 path additionally receives the target embedding and may return it directly, so its perfect reconstruction score is not a source-free decoder measurement.','The evaluated consumer excludes the legacy target-guided shortcut described below.')
s=s.replace(r'\hat e=e_0(f)+',r'\hat e=e_0(e,f)+')
s=s.replace('Two independent software checks','Two software checks')
s=s.replace('with one component containing 1,738 raw records.','with one component containing 1,738 raw records (1,730 distinct units).')
s=s.replace(r'then $\Gamma\models_{L_s}\phi$.',r'then $\Gamma,B\models_{L_s}\phi$ on the admitted source models.')
needle='The legacy TDFOL converter does not satisfy the contract.'
s=s.replace(needle,needle+r'''
\paragraph{Proof.} Let $s$ be an arbitrary admitted source model satisfying $\Gamma$ and $B$. Related-model existence supplies a target model $t$ with $R_B(s,t)$. Premise preservation gives $t\models\tau(\Gamma)$. The sound target consequence yields $t\models\tau(\phi)$, and goal reflection gives $s\models\phi$. Since $s$ was arbitrary, $\Gamma,B\models_{L_s}\phi$ over that admitted class. The bridge assumptions may be dropped only when they hold throughout the declared source profile.
''')
p.write_text(s)
# Keep the official questions and remove only their author-facing instructional guidelines.
p=E/'editable/manuscript/checklist.tex';s=p.read_text();lines=s.splitlines();out=[];skip=False;depth=0
for line in lines:
 if '\\item[] Guidelines:' in line:skip=True;depth=0;continue
 if skip:
  depth+=line.count('\\begin{itemize}')+line.count('\\begin{enumerate}')
  depth-=line.count('\\end{itemize}')+line.count('\\end{enumerate}')
  if depth==0 and ('\\end{itemize}' in line or '\\end{enumerate}' in line):skip=False
  continue
 out.append(line)
s='\n'.join(out)+'\n'
justifications=[
 'The abstract and introduction describe executed native compilation, source-conditioned reconstruction, learned check ordering, and constructed proof assistance, with explicit limits on source fidelity and generalization.',
 'The limitations section discusses unmeasured independent semantics, source prefixes, corpus dependence, empty classifier tables, the absence of a compression bottleneck, and the restricted proof suite.',
 r'The conditional transfer proposition states bridge assumptions, related-model existence, premise preservation, goal reflection, and soundness, with a complete argument in Appendix~\ref{app:prop}.',
 'Protocols, seeds, models, inputs, and metric definitions are disclosed. The supplement reproduces tables from per-unit measurements; a complete fresh inference run additionally requires the identified large local learned states, which are not included in the ZIP.',
 'The supplement releases observations and table-generation code. The multi-gigabyte learned states and complete external runtime are identified but not distributed here, so complete open-access end-to-end reproduction is not yet provided.',
 'The experimental-design section and supplement specify splits, three training seeds, native compilation budgets, fixed prompts, representation losses, and which stored heads were actually learned.',
 'We report paired component-bootstrap intervals, define resampling units and seeds, and discuss the dominant component. Proof-study intervals use semantic families; no independence of all template variants is assumed.',
 'The execution appendix reports current CPU/model limits and measured costs, plus earlier training costs and failures. Concurrent elapsed times are not presented as controlled throughput comparisons.',
 'The work uses public legal-source material and automated constructed tests; limitations and broader impacts distinguish machine checks from legal authority.',
 r'Potential benefits and misuse of automated legal or security formalization are discussed in Appendix~\ref{app:impacts}, including misleading claims of source-faithful verification.',
 'No new large generative model or personal-data collection is released; this question does not apply to a high-risk model or dataset release.',
 r'Appendix~\ref{app:assets} identifies the legal corpus and upstream license declarations, MiniLM, and the Leanstral model and quantization provenance.',
 'The supplement describes its metric observations, scripts, input identities, checksums, and omitted large assets. It includes an explicit distinction between table reproduction and fresh inference.',
 'No crowdsourcing or human-subject experiment was conducted, and no human agreement or semantic-fidelity score is reported.',
 'No human-subject research was performed.',
 r'Appendix~\ref{app:llm} identifies the actual Leanstral model, prompts and inference budgets, MiniLM teacher, historical development use, and agent assistance with implementation and writing.'
]
import re
idx=iter(justifications)
s=re.sub(r'(?m)^    \\item\[\] Justification:.*$',lambda m:'    \\item[] Justification: '+next(idx),s)
# Full open model/runtime access is intentionally not claimed.
key='\\item {\\bf Open access to data and code}'
a=s.index(key);b=s.index('\\item {\\bf Experimental setting/details}',a)
s=s[:a]+s[a:b].replace('\\answerYes{}','\\answerNo{}',1)+s[b:]
a=s.index('\\item {\\bf Experiment statistical significance}');b=s.index('\\item {\\bf Experiments compute resources}',a)
s=s[:a]+s[a:b].replace('\\answerNo{}','\\answerYes{}',1)+s[b:]
p.write_text(s)
print('Updated scope and checklist; official questions retained.')
