#!/usr/bin/env python3
"""Insert measured 8-probe and 900-cell results into the Law-to-Action manuscripts."""
from __future__ import annotations
import json
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SYN = ROOT / 'papers/revisions/law_to_action_synthesis_20260914/manuscript'
FINAL = ROOT / 'papers/final/law_to_action/editable/manuscript'


def frac(num, den):
    return r'$%s/%s$' % (num, den)


def table(summary):
    lines = []
    for split in ('overall', 'final'):
        for arm in ('A0', 'A1', 'A2', 'A3', 'A4'):
            stats = summary['arms'][arm] if split == 'overall' else summary['arms_by_split'][arm]['final']
            name = {'A0': 'A0 unguarded', 'A1': 'A1 policy prompt', 'A2': 'A2 retrieval',
                    'A3': 'A3 path policy', 'A4': r'A4 \texttt{ENFORCE}'}[arm]
            lines.append('%s & %s & %s & %s & %s \\\\' % (
                name, split, frac(stats['forbidden'], stats['n']),
                frac(stats['useful'], stats['n']), frac(stats['format_fail'], stats['n'])))
    return '\n'.join(lines)


def section(probe, summary):
    useful = sum(summary['arms'][arm]['useful'] for arm in summary['arms'])
    return r'''
\subsection{Generated-code planning and interface qualification}
\label{sec:eval-generated}

Eight frozen synthetic interface probes were executed against the pinned local Leanstral deployment (seeds $104729$, $104759$, and $104761$; 2048-input / 1024-output contract; no scientific sources). Status \texttt{%s}: seven generations plus the expected input-overflow rejection; the identical seed-$104729$ repeat matched exactly; prompt-token counts equalled preflight input counts. Distinct exchanges reserved: %s.

The same warm model then executed the original $60\times 5\times 3=900$ generated-code identities (180 development, 180 calibration, 540 final) without reload, under a 36{,}000-second service wall and a 360-second startup bound. Recorded cells: %s/900. Model calls: %s. Prompt/completion tokens: %s/%s. Exact useful-work matches: %s/900. Generated programs ran in the bounded in-process profile. A0--A2 execute inside fixture containment; A3 applies declared path policy; A4 additionally refuses secret-bearing arguments. Useful work and forbidden effects are independent fixture observations, not model self-reports. This matrix is not pooled with the fixed-action study. Expert legal fidelity was not scored.

\begin{table}[t]
\centering
\caption{Generated-code 900-cell observations. Every scheduled identity remains in the denominator, including format and transport failures.}
\label{tab:generated}
\begin{tabular}{@{}llccc@{}}
\toprule
Arm & Split & Forbidden effects & Useful work & Format/transport fail \\
\midrule
%s
\bottomrule
\end{tabular}
\end{table}
''' % (str(probe.get('status')).replace('_', r'\_'), probe.get('reserved_distinct_exchanges'),
       summary['recorded_cells'], summary['model_calls'],
       summary['prompt_tokens'], summary['completion_tokens'], useful, table(summary))


def patch(path, old, new):
    text = path.read_text()
    if old not in text:
        raise RuntimeError('Expected passage missing in ' + str(path) + ': ' + old[:80])
    path.write_text(text.replace(old, new, 1))


def build_pdf(manuscript, out_pdf):
    build = manuscript.parent / 'build-generated-update'
    if build.exists():
        shutil.rmtree(build)
    build.mkdir()
    cmd = ['pdflatex', '-no-shell-escape', '-interaction=nonstopmode', '-halt-on-error',
           '-file-line-error', '-output-directory', str(build), 'main.tex']
    subprocess.run(cmd, cwd=manuscript, check=True, capture_output=True, text=True)
    bib = manuscript / 'references.bib'
    if bib.exists():
        subprocess.run(['bibtex', str(build / 'main')], cwd=manuscript, check=False, capture_output=True, text=True)
        subprocess.run(cmd, cwd=manuscript, check=True, capture_output=True, text=True)
        subprocess.run(cmd, cwd=manuscript, check=True, capture_output=True, text=True)
    shutil.copyfile(build / 'main.pdf', out_pdf)
    return out_pdf


def main():
    probe = json.loads((HERE / 'interface_qualification/qualification_results.json').read_text())
    summary = json.loads((HERE / 'summary.json').read_text())
    if not summary.get('complete') or summary.get('recorded_cells') != 900:
        raise RuntimeError('Refusing to edit the paper before 900 recorded cells')
    generated = section(probe, summary)

    patch(FINAL / 'results.tex',
          'Closed-loop generated-code planning (protocol RQ3) is explicitly withdrawn: $900/900$ scheduled cells were \\texttt{not\\_started}, model calls $0$, generated programs $0$. Unstarted zeros are accounting, not measured agent failure. Results are not pooled with the fixed-action matrix.',
          'Closed-loop generated-code planning (protocol RQ3) was executed as a separate 900-cell study against the pinned local model; Table~\\ref{tab:generated} reports those observations and is not pooled with the fixed-action matrix.' + generated)
    patch(FINAL / 'main.tex',
          'Expert legal fidelity, human agreement, and closed-loop model planning were not collected or executed and are withdrawn rather than filled.',
          'Expert legal fidelity and human agreement were not collected. Closed-loop model planning was executed as a separate 900-cell study and is not pooled with the fixed-action matrix.')
    patch(FINAL / 'limitations.tex',
          'The evaluated handler consumes a declarative export instruction; closed-loop model-generated programs were not executed.',
          'The fixed-action handler consumes a declarative export instruction. A separate 900-cell generated-code study executed model programs in a bounded interpreter; those observations are not pooled with the fixed-action rates.')

    patch(SYN / 'results.tex',
          'No scientific model calls or model-generated programs enter this study.',
          'No scientific model calls enter the fixed-action matrix. A separate generated-code study is reported in Section~\\ref{sec:eval-generated}.')
    patch(SYN / 'results.tex',
          'The planned closed-loop study was not executed and contributes no measured outcomes.',
          'The closed-loop generated-code study was executed separately; Table~\\ref{tab:generated} reports those observations and is not pooled with the fixed-action matrix.' + generated)
    if (SYN / 'evaluation_details.tex').exists():
        patch(SYN / 'evaluation_details.tex',
              'The planned generated-code study was withdrawn without execution: $900/900$ scheduled cells were \\texttt{not\\_started}, model calls were $0$, and generated programs were $0$. These counts are scheduling accounting, not observed agent failures, and are not pooled with the fixed-action results.',
              'The generated-code study was executed: $900/900$ scheduled cells have terminal records. Table~\\ref{tab:generated} reports the observations. They are not pooled with the fixed-action results.')
    patch(SYN / 'main.tex',
          'Legal interpretation accuracy and closed-loop model planning were not evaluated.',
          'Legal interpretation accuracy was not evaluated. Closed-loop model planning was measured in a separate 900-cell study.')

    final_pdf = ROOT / 'papers/final/law_to_action/paper.pdf'
    syn_pdf = ROOT / 'papers/revisions/law_to_action_synthesis_20260914/paper.pdf'
    build_pdf(FINAL, final_pdf)
    if (SYN / 'main.tex').exists():
        build_pdf(SYN, syn_pdf)
    print(json.dumps({'probe': probe.get('status'), 'cells': summary['recorded_cells'],
                      'model_calls': summary['model_calls'], 'final_pdf': str(final_pdf)}))


if __name__ == '__main__':
    main()
