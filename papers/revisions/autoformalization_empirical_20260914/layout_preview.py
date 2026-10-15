from pathlib import Path
E=Path(__file__).resolve().parent;R=E/'editable/results'
# Temporary typesetting placeholders; never copied to final handoff.
(R/'empirical_numbers.tex').write_text('\\newcommand{\\AEColdCosine}{\\textemdash}\n\\newcommand{\\AETrainedCosine}{\\textemdash}\n')
t=r'''\begin{table}[t]
\centering\small
\caption{Native representation and reconstruction outcomes. A and C share structural checks on the 100-source subset. B uses its stricter native deontic contract. Counts are not source-semantic accuracy.}
\label{tab:pipeline-results}
\begin{tabular}{lrrrrr}\toprule
Method & Units & IR passes & Nonempty & Exact cycle & Cycle timeout\\\midrule
Native B & 1913 & --- & --- & --- & ---\\
Native C & 1913 & --- & --- & --- & ---\\
Repaired C (T5) & 1913 & --- & --- & --- & ---\\\midrule
Direct model A & 100 & --- & --- & --- & ---\\
Native C, same subset & 100 & --- & --- & --- & ---\\\bottomrule
\end{tabular}
\end{table}
'''
(R/'empirical_pipeline.tex').write_text(t)
(R/'empirical_pipeline_discussion.tex').write_text('\\textit{Layout preview only: final measurements are still running.} The completed run will report native representation checks, cycle failures, typed abstention, source-prefix truncation, and paired exception-scoping changes.\n')
(R/'empirical_learning.tex').write_text(r'''\begin{table}[t]
\centering\small
\caption{Source-conditioned embedding reconstruction on 1,913 held-out units. This decoder has no demonstrated compression bottleneck; an identity-copy control is exact by construction.}
\label{tab:training-results}
\begin{tabular}{llrr}\toprule
Condition & Seed & Mean cosine & Mean MSE\\\midrule
T0 cold & fixed & --- & ---\\
T1 sample memory & three seeds & --- & ---\\
T2 shared parameters & 104729 & --- & ---\\
T2 shared parameters & 130363 & --- & ---\\
T2 shared parameters & 155921 & --- & ---\\
T3 isolated proof heads & tied to T2 & --- & ---\\
Identity-copy control & analytic & 1.000 & 0.000\\\bottomrule
\end{tabular}
\end{table}
''')
(R/'empirical_learning_discussion.tex').write_text('\\textit{Layout preview only.} The completed run will report paired component-bootstrap intervals, memory hits, learned-priority activation and rollback, and held-out compiler-repair effects.\n')
(R/'empirical_assistance.tex').write_text(r'''\begin{table}[t]
\centering\small
\caption{Native acceptance on 64 constructed goals (32 valid, 32 invalid). Every method attempted the same fixed declarations.}
\label{tab:assistance-results}
\begin{tabular}{lrrr}\toprule
Method & Valid accepted & Invalid accepted & Unsupported\\\midrule
Fixed native tactics & 32/32 & 0/32 & 0\\
SMT-guided reconstruction & 24/32 & 0/32 & 16\\
Leanstral, primary policy & 12/32 & 0/32 & 0\\\bottomrule
\end{tabular}
\end{table}
''')
(R/'empirical_execution.tex').write_text('\\textit{Layout preview only: execution costs will be inserted after all bounded jobs finish.}\n')
p=E/'editable/manuscript/main.tex';s=p.read_text().replace('\\label{af-main-text-end}','\\label{af-main-text-end}\\typeout{EMPIRICAL-MAIN-END:\\thepage}');p.write_text(s)
