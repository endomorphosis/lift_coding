"""Reconstruct a review copy from the supplied PDF's existing text extraction.

This is recovery tooling, not a benchmark or an author-source recovery claim.
No runtime state or source outside this staging directory is modified.
"""
from pathlib import Path
import hashlib
import json
import re
import shutil
import unicodedata

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
PDF = REPO / "papers/autoformalization_training_methods_revised-1.pdf"
EXTRACT = HERE.parent / "extracted.txt"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tex(text):
    text = unicodedata.normalize("NFC", text)
    math = {
        "Γ": r"\Gamma", "Θ": r"\Theta", "η": r"\eta", "θ": r"\theta",
        "λ": r"\lambda", "τ": r"\tau", "ψ": r"\psi", "ω": r"\omega",
        "ϕ": r"\phi", "ℓ": r"\ell", "←": r"\leftarrow", "→": r"\to",
        "⇒": r"\Rightarrow", "∀": r"\forall", "∃": r"\exists",
        "∇": r"\nabla", "∈": r"\in", "−": "-", "∥": r"\Vert",
        "∧": r"\land", "∨": r"\lor", "□": r"\Box", "¬": r"\neg",
    }
    chars = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%",
             "$": r"\$", "#": r"\#", "_": r"\_", "{": r"\{",
             "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
             "–": "--", "—": "---", "’": "'", "“": "``", "”": "''",
             "ł": r"\l{}", "ó": r"\'{o}", "ü": r'\"{u}',
             "ź": r"\'{z}", "ś": r"\'{s}", "ê": r"\^{e}",
             "\u0302": r"\textasciicircum{}", "\u0301": "'"}
    return "".join(r"\ensuremath{" + math[c] + "}" if c in math else chars.get(c, c) for c in text)


EQUATIONS = {
    1: r"I_1=C_\psi(x),\qquad \hat{x}=D_\omega(I_1),\qquad I_2=C_\psi(\hat{x}).",
    2: r"\hat e=e_0(f)+\sum_g A_g(f)W_g,",
    3: r"p_F=\operatorname{softmax}\!\left(\ell_F^0(f)+\sum_g A_g(f)U_g\right),",
    4: r"p_V=\operatorname{softmax}\!\left(\ell_V^0(f)+\sum_g A_g(f)V_g\right).",
    5: r"\begin{split}L_{\mathrm{packed}}={}&H(q_F,p_F)+H(q_V,p_V)+\operatorname{MSE}(e,\hat e)\\&+\lambda_c(1-\cos(e,\hat e))+L_{\mathrm{norm}}+\lambda_2R(\Theta).\end{split}",
    6: r"[\![\Box_i\phi]\!](w)=\forall v\,[R_i(w,v)\Rightarrow[\![\phi]\!](v)].",
    7: r"s\models\Gamma\land R_B(s,t)\Rightarrow t\models\tau(\Gamma),",
    8: r"t\models\tau(\phi)\land R_B(s,t)\Rightarrow s\models\phi.",
    9: r"\operatorname{Protected}(r)\land\neg\operatorname{Approved}(a,r,t)\Rightarrow O_{a,t,\theta}(\neg\operatorname{Write}(a,r,t)).",
    10: r"Q_1=\forall a,r,t:\operatorname{Protected}(r)\land\neg\operatorname{Approved}(a,r,t)\Rightarrow\neg\operatorname{Write}(a,r,t),",
    11: r"Q_2=\forall a,r,t:\operatorname{Write}(a,r,t)\Rightarrow\exists u\in[t,t+2]:\operatorname{Audit}(a,r,u).",
    12: r"L_{\mathrm{rec}}=\frac1n\sum_i\frac1d\|\hat e_i-e_i\|_2^2.",
    13: r"L_{\mathrm{CE}}=-\frac1n\sum_{i\in M}\sum_j q_{ij}\log\operatorname{softmax}(\ell_i)_j,",
    14: r"\Theta\leftarrow\Theta-\eta\,\operatorname{Clip}(\nabla_\Theta L),",
    15: r"s(t,d)=\operatorname{idf}(t)\frac{\operatorname{tf}(t,d)(k_1+1)}{\operatorname{tf}(t,d)+k_1(1-b+b\,|d|/\overline{|d|})}.",
}


def main():
    for name in ("inputs", "pages", "blocks", "equations", "bibliography", "build"):
        (HERE / name).mkdir(exist_ok=True)
    for name in ("neurips_2026_vericode_workshop.tex", "neurips_2026_vericode.sty", "checklist.tex"):
        shutil.copyfile(REPO / "papers" / name, HERE / "inputs" / name)
    shutil.copyfile(REPO / "papers/neurips_2026_vericode.sty", HERE / "neurips_2026_vericode.sty")
    shutil.copyfile(EXTRACT, HERE / "original-layout.txt")
    for number, equation in EQUATIONS.items():
        (HERE / "equations" / f"equation-{number:02d}.tex").write_text(
            f"% Newly transcribed from original PDF equation ({number}); see recovery-map.json.\n"
            + "\\begin{equation}\n" + equation + f"\\tag{{{number}}}\\label{{eq:original-{number}}}\n\\end{{equation}}\n")

    pages = [p for p in EXTRACT.read_text().split("\f") if p.strip()]
    mapping = {"schema": "autoformalization-source-recovery/v1", "original_pdf": {
        "path": str(PDF.relative_to(REPO)), "sha256": digest(PDF), "pages": len(pages)},
        "extraction": {"path": str(EXTRACT.relative_to(REPO)), "sha256": digest(EXTRACT), "method": "Existing pdftotext -layout extraction; no OCR or model-generated prose."},
        "sections": [], "equations": [], "tables": [], "figure": [], "references": [],
        "original_numbered_lines": [], "blocks": [], "uncertainties": [], "template_inputs": []}
    for p in sorted((HERE / "inputs").iterdir()):
        mapping["template_inputs"].append({"path": str(p.relative_to(HERE)), "sha256": digest(p),
                                          "identical_to_user_file": digest(p) == digest(REPO / "papers" / p.name)})
    previous_table = None
    refs = {}
    current_reference = None

    for page_number, raw in enumerate(pages, 1):
        (HERE / "pages" / f"page-{page_number:02d}.txt").write_text(raw + "\n")
        output = [f"% Original PDF page {page_number}; hash in recovery-map.json.",
                  rf"\recoverypage{{{page_number}}}"]
        paragraph = []
        free = []

        def flush_paragraph():
            if paragraph:
                # Explicit line breaks preserve original word-break hyphens rather than guess spelling.
                output.append("\\noindent\n" + "\\linebreak[4]\n".join(tex(x) for x in paragraph) + "\\par\n")
                paragraph.clear()

        def flush_free():
            nonlocal previous_table
            if not any(x.strip() for x in free):
                free.clear()
                return
            text = "\n".join(free).strip("\n")
            free.clear()
            # Title/anonymous author/abstract heading and original page-one footer are reproduced separately.
            if page_number == 1 and ("Anonymous Author(s)" in text or "Submitted to NeurIPS" in text):
                mapping["blocks"].append({"page": page_number, "kind": "title-or-footer", "raw_text": text,
                                           "recovered_in": "main.tex title/anonymous author/research-style footnote"})
                return
            index = len(mapping["blocks"]) + 1
            raw_path = HERE / "blocks" / f"block-{index:03d}.txt"
            raw_path.write_text(text + "\n")
            block = {"page": page_number, "raw_path": str(raw_path.relative_to(HERE)), "sha256": digest(raw_path)}
            equation_numbers = [int(n) for n in re.findall(r"\((\d{1,2})\)\s*(?:\n|$)", text)]
            if equation_numbers and all(n in EQUATIONS for n in equation_numbers):
                block["kind"] = "display-equations"
                for n in equation_numbers:
                    path = f"equations/equation-{n:02d}.tex"
                    output.append(r"\input{" + path + "}")
                    mapping["equations"].append({"number": n, "original_page": page_number, "source": path,
                                                "raw_extraction": block["raw_path"], "status": "manual_transcription_requires_final_formula_audit"})
            elif "Figure 1:" in text:
                block["kind"] = "figure"
                output.append(r"\input{figure-01.tex}")
                mapping["figure"].append({"number": 1, "original_page": page_number, "source": "figure-01.tex", "raw_extraction": block["raw_path"], "status": "box_and_arrow_structure_visually_checked"})
            else:
                table = re.search(r"Table (\d+):\s*(.*)", text)
                if table:
                    previous_table = int(table.group(1))
                    mapping["tables"].append({"number": previous_table, "original_pages": [page_number], "caption_first_line": table.group(2), "raw_fragments": [block["raw_path"]], "status": "editable_layout_text_preserved_cell_typesetting_pending"})
                elif previous_table in (2, 9) and re.match(r"\s*(ID\s+Source role|View\s+Contribution)", text):
                    t = next(t for t in mapping["tables"] if t["number"] == previous_table)
                    t["original_pages"].append(page_number)
                    t["raw_fragments"].append(block["raw_path"])
                block["kind"] = "table-or-layout-excerpt"
                # Preserve intercolumn spacing and all words/numbers in editable TeX, without inferring cells.
                lines = text.splitlines()
                left = min(len(l) - len(l.lstrip()) for l in lines if l.strip())
                formatted = []
                for l in lines:
                    l = l[left:]
                    pieces = re.split(r"( {2,})", l)
                    formatted.append("".join(r"\hspace*{" + str(len(x)) + "\\fontdimen2\\font}" if x.startswith("  ") else tex(x) for x in pieces))
                tex_path = HERE / "blocks" / f"block-{index:03d}.tex"
                tex_path.write_text("% Editable layout transcription; cell boundaries not asserted.\n"
                                    + "\\begin{center}\\resizebox{\\linewidth}{!}{\\begin{tabular}{@{}l@{}}\n"
                                    + " \\\\\n".join(formatted) + "\n\\end{tabular}}\\end{center}\n")
                block["source"] = str(tex_path.relative_to(HERE))
                output.append(r"\input{" + block["source"] + "}")
            mapping["blocks"].append(block)

        for original_text_line, line in enumerate(raw.splitlines(), 1):
            if re.fullmatch(r"\s*" + str(page_number) + r"\s*", line):
                continue
            numbered = re.match(r"^\s*(\d{1,3})\s{2,}(.*)$", line)
            if numbered:
                flush_free()
                n, body = int(numbered.group(1)), numbered.group(2)
                mapping["original_numbered_lines"].append({"number": n, "original_page": page_number,
                    "extraction_line_on_page": original_text_line, "text": body, "source": f"pages/page-{page_number:02d}.tex"})
                if n == 1:
                    output.append(r"\begin{abstract}")
                elif n == 22:
                    flush_paragraph()
                    output.append(r"\end{abstract}")
                if page_number == 10 and n >= 377:
                    hit = re.match(r"\[(\d+)\]\s*(.*)", body)
                    if hit:
                        current_reference = int(hit.group(1))
                        refs[current_reference] = []
                    refs[current_reference].append(body if not hit else hit.group(2))
                heading = re.match(r"^([A-Q](?:\.\d+)?|[1-9](?:\.\d+)?)\s{2,}(\S.*)", body)
                if heading:
                    flush_paragraph()
                    label, title = heading.groups()
                    command = "subsection" if "." in label else "section"
                    output.append("\\" + command + "*{" + tex(label + "  " + title) + "}")
                    mapping["sections"].append({"label": label, "title": title, "original_page": page_number, "original_line": n, "source": f"pages/page-{page_number:02d}.tex"})
                elif body in ("References", "Paper checklist: official questionnaire required"):
                    flush_paragraph()
                    output.append(r"\section*{" + tex(body) + "}")
                else:
                    paragraph.append(body)
                if re.search(r"[ΓΘηθλτψωϕℓ∀∃∈∥□]|[a-zA-Z]\s*[|]=|[a-zA-Z]\u0302", body):
                    mapping["uncertainties"].append({"kind": "inline-math-typesetting", "original_page": page_number, "original_line": n, "text": body})
            elif line.strip():
                flush_paragraph()
                free.append(line)
            else:
                flush_paragraph()
                if free:
                    free.append("")
        flush_paragraph()
        flush_free()
        (HERE / "pages" / f"page-{page_number:02d}.tex").write_text("\n".join(output) + "\n")

    bib = ["% Recovered bibliography strings only. No external bibliographic verification performed.",
           "% Full rendered reference is retained in note to avoid inventing absent BibTeX metadata."]
    for n, lines in sorted(refs.items()):
        raw_reference = "\n".join(lines)
        path = HERE / "bibliography" / f"reference-{n:02d}.txt"
        path.write_text(raw_reference + "\n")
        joined = re.sub(r"(?<=\w)-\n(?=\w)", "", raw_reference).replace("\n", " ")
        bib.append(f"@misc{{original{n:02d},\n  title = {{{{Original PDF reference [{n}]}}}},\n  note = {{{tex(joined)}}}\n}}")
        mapping["references"].append({"number": n, "original_page": 10, "source": str(path.relative_to(HERE)), "bib_key": f"original{n:02d}", "status": "full_visible_reference_preserved_structured_metadata_pending", "normalized_rendered_string": joined})
    (HERE / "references.bib").write_text("\n\n".join(bib) + "\n")
    mapping["coverage"] = {"numbered_lines": len(mapping["original_numbered_lines"]),
                           "expected_numbered_lines": 859, "equations": len(mapping["equations"]),
                           "tables": len(mapping["tables"]), "references": len(mapping["references"]),
                           "TBD_occurrences_in_original": EXTRACT.read_text().count("[TBD]"),
                           "TODO_occurrences_in_original": EXTRACT.read_text().count("[TODO]"),
                           "To_complete_occurrences_in_original": EXTRACT.read_text().count("[To complete:")}
    assert [x["number"] for x in mapping["original_numbered_lines"]] == list(range(1, 860))
    assert sorted(e["number"] for e in mapping["equations"]) == list(range(1, 16))
    assert sorted(t["number"] for t in mapping["tables"]) == list(range(1, 14))
    assert len(mapping["references"]) == 10
    (HERE / "recovery-map.json").write_text(json.dumps(mapping, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(mapping["coverage"]))


if __name__ == "__main__":
    main()
