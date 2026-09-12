#!/usr/bin/env python3
"""Build the per-paper checklist from the official questionnaire."""
from __future__ import annotations

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[5]
OFFICIAL = REPO_ROOT / "papers/checklist.tex"
OUT = REPO_ROOT / "papers/completion/autoformalization/manuscript/checklist.tex"

ANSWERS = [
    (
        r"\answerYes{}",
        r"The abstract and introduction state the measured automated inventory "
        r"(A--E/T0--T5 conditions, unrun 1913-unit cells, T1 diagnostic, constructed "
        r"witnesses) and explicitly do not claim independent source fidelity or useful "
        r"proof coverage on unseen material.",
    ),
    (
        r"\answerYes{}",
        r"Section ``Limitations and conclusion'' records uncollected independent labels, "
        r"teacher bias, sample-memory shortcuts, lossy translations, unavailable native "
        r"checkers, unactivated T4/E, and that reconstruction or prover success is not "
        r"source gold.",
    ),
    (
        r"\answerYes{}",
        r"The conditional transfer proposition states nonvacuity, premise preservation, "
        r"goal reflection, and sound-checker assumptions (Eqs.~\ref{eq:prem}--\ref{eq:goal}; "
        r"Appendix~\ref{app:prop}) and is labeled a paper-level argument, not a "
        r"machine-checked compiler theorem.",
    ),
    (
        r"\answerYes{}",
        r"Seeds 104729/130363/155921, frozen splits, and sealed-path commands are in the "
        r"main text; the anonymous supplement regenerates Tables~\ref{tab:pipeline-results}, "
        r"\ref{tab:training-results}, and \ref{tab:assistance-results} from frozen "
        r"\texttt{summary.json}, retaining unrun cells rather than filling them.",
    ),
    (
        r"\answerYes{}",
        r"The anonymized supplement documents regeneration commands and checksums; large "
        r"packed-CPU states and MiniLM weights are hash-bound with anonymous access "
        r"strategies, and private holdout bodies are withheld (Appendix~\ref{app:assets}).",
    ),
    (
        r"\answerYes{}",
        r"The evaluation protocol, A--E/T0--T5 definitions, split counts, seeds, packed "
        r"SGD-style update, and teacher identities appear in the main text; full receipts "
        r"are in the supplement.",
    ),
    (
        r"\answerNo{}",
        r"Primary 1913-unit cells are unrun or unmeasured, so no error bars are reported "
        r"there; T1 reports exact seed-level teacher-cosine values, and the prespecified "
        r"95\% cluster bootstrap is not imputed for missing cells.",
    ),
    (
        r"\answerYes{}",
        r"The manuscript reports retained historical phase costs (963.171\,s), states "
        r"GPU/CUDA speedup and human-review seconds as unmeasured rather than 0.0, and "
        r"records failed encoder-preparation attempts.",
    ),
    (
        r"\answerYes{}",
        r"The study uses upstream-declared public-domain U.S.\ legal/policy text, withholds "
        r"private holdout bodies, does not collect human-subject data, and does not "
        r"fabricate annotations.",
    ),
    (
        r"\answerYes{}",
        r"Appendix~\ref{app:impacts} records potential verification benefits and harms from "
        r"treating incorrect legal or policy formalizations as authority, including misuse "
        r"of monitoring queries and solver success presented as source-faithful proof.",
    ),
    (
        r"\answerNA{}",
        r"No high-risk generative model or scraped internet image dump is released; holdout "
        r"source bodies remain private and MiniLM is a public encoder checkpoint "
        r"(Appendix~\ref{app:assets}).",
    ),
    (
        r"\answerYes{}",
        r"Appendix~\ref{app:assets} records upstream CC0-1.0 / public-domain-U.S.-government "
        r"declarations for the legal corpus, the MiniLM model id and revision, and that "
        r"4024 coding-shard license-risk rows remain \texttt{needs\_review} and are not "
        r"admitted as natural data.",
    ),
    (
        r"\answerYes{}",
        r"The anonymous supplement documents regeneration, checksums, and S01--S40 hashes; "
        r"new code and large checkpoints beyond that package are hash-bound rather than "
        r"silently omitted (Appendix~\ref{app:assets}).",
    ),
    (
        r"\answerNA{}",
        r"No crowdsourcing or human-subjects experiment was conducted; the 100-unit "
        r"candidate-blind sample remains blank and is not reported as agreement.",
    ),
    (
        r"\answerNA{}",
        r"No human-subjects research was performed, so no IRB or equivalent review applies.",
    ),
    (
        r"\answerYes{}",
        r"Appendix~\ref{app:llm} records served \texttt{grok-4.6} as the Arm~A development "
        r"model-to-target on 2026-09-12, MiniLM revision \texttt{1110a243\ldots} as a "
        r"grouping/teacher encoder, and zero Leanstral/plan-nomination calls; writing-only "
        r"assistance is disclosed there and is not experimental evidence.",
    ),
]


def main() -> int:
    text = OFFICIAL.read_text(encoding="utf-8")
    text = re.sub(
        r"\n%%% BEGIN INSTRUCTIONS %%%.*?%%% END INSTRUCTIONS %%%\n+",
        "\n",
        text,
        count=1,
        flags=re.S,
    )
    answers = re.findall(r"\\answerTODO\{\}", text)
    justifications = re.findall(r"\\justificationTODO\{\}", text)
    if len(answers) != 16 or len(justifications) != 16:
        raise SystemExit(f"expected 16 TODO pairs, found {len(answers)} answers and {len(justifications)} justifications")
    if len(ANSWERS) != 16:
        raise SystemExit(f"answer table has {len(ANSWERS)} entries")

    def replace_answer(_match: re.Match[str], counter=[0]) -> str:
        value = ANSWERS[counter[0]][0]
        counter[0] += 1
        return value

    def replace_justification(_match: re.Match[str], counter=[0]) -> str:
        value = ANSWERS[counter[0]][1]
        counter[0] += 1
        return value

    text = re.sub(r"\\answerTODO\{\} % Replace by \\answerYes\{\}, \\answerNo\{\}, or \\answerNA\{\}\.", replace_answer, text)
    text = re.sub(r"\\justificationTODO\{\}", replace_justification, text)
    if "\\answerTODO" in text or "\\justificationTODO" in text:
        raise SystemExit("TODO fields remain after replacement")
    if "BEGIN INSTRUCTIONS" in text or "END INSTRUCTIONS" in text:
        raise SystemExit("instruction block was not fully removed")
    if "NeurIPS Paper Checklist" not in text:
        raise SystemExit("checklist heading missing")
    for heading in (
        "Claims",
        "Limitations",
        "Theory assumptions and proofs",
        "Experimental result reproducibility",
        "Open access to data and code",
        "Experimental setting/details",
        "Experiment statistical significance",
        "Experiments compute resources",
        "Code of ethics",
        "Broader impacts",
        "Safeguards",
        "Licenses for existing assets",
        "New assets",
        "Crowdsourcing and research with human subjects",
        "Institutional review board (IRB) approvals or equivalent for research with human subjects",
        "Declaration of LLM usage",
    ):
        if heading not in text:
            raise SystemExit(f"missing official question heading: {heading}")
    answer_lines = [ln for ln in text.splitlines() if r"\item[] Answer:" in ln]
    if len(answer_lines) != 16:
        raise SystemExit(f"expected 16 Answer lines, found {len(answer_lines)}")
    if any("TODO" in ln for ln in answer_lines):
        raise SystemExit("Answer lines still contain TODO")
    if not all(re.search(r"\\answer(Yes|No|NA)\{\}", ln) for ln in answer_lines):
        raise SystemExit("Answer lines missing Yes/No/N/A macros")
    if "Guidelines:" not in text or text.count("Guidelines:") < 16:
        raise SystemExit("official guidelines were not preserved")
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
