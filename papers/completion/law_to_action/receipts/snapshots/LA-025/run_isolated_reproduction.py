#!/usr/bin/env python3
"""LA-025 isolated retained-data reproduction and final-package audit.

Runs the documented bounded reproduce path from a clean HOME and sealed PATH.
Inspects the existing compiled PDF because latexmk/pdflatex are absent from the
authoritative validation PATH. Performs no new scientific benchmark, model call,
human validation, upload, or workshop submission.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

SEALED_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"
PYTHON = "/usr/bin/python3.12"
TEMPLATES = {
    "papers/neurips_2026_vericode_workshop.tex": "c1c74133705d906972ee7571ee34f57122da5088e9f09ffe9dacb01cf0db1250",
    "papers/neurips_2026_vericode.sty": "2944ec0d4f64dba353827e9ead104da1a9ac81b4057f4ff40969c693632a1e11",
    "papers/checklist.tex": "780ba13c480f652dcc42e69ed61a752ce0ea270f15d332d4a45b059dabad84f6",
    "papers/neurips_2026.sty": "c3fc2894e83d2517ca18b66741d6c595986d97957dc08ec08bb2125a7ec4555a",
    "papers/neurips_2026_vericode_competition.sty": "a0178f152d13cf24f44936da0ee95bab975ceced8d54980efbbf8f7c1bb31f72",
    "papers/neurips_2026_vericode_workshop_competition.tex": "0e21c08ce8a32cb3d4c0fb7123d38249209c2ef488a0c210acbea026f6fefc23",
}
RETAINED_CFP_SHA256 = "66b5740723edb198ed6faf80430bbee3634e316ee4c0385a64da6480e0724468"
LA024_PDF = "b306a5d4c64961f9e9a1c061dac99645fbc3fca406621092ba813bc3cd221ecb"
LA024_ZIP = "e46b58516a47020e3df826bb7cdc3f870566c28a6a3eb92c5abf53c64ed679e1"
PLACEHOLDER_RE = re.compile(r"\b(?:TBD|TODO|FIXME|PLACEHOLDER)\b")
SCIENTIFIC_TODO_RE = re.compile(r"\\(?:answerTODO|justificationTODO)\b")
IDENTIFYING_RE = re.compile(r"/home/(?!anonymous/)[\w.-]+/|overleaf\.com/project|barberb", re.I)
STYLE_OVERRIDE_RE = re.compile(
    r"\\(?:fontsize|small|footnotesize|scriptsize|tiny|large|Large|LARGE|huge|Huge|"
    r"geometry|newgeometry|linespread|enlargethispage|scalebox|resizebox)\b"
)
SPACING_OVERRIDE_RE = re.compile(
    r"\\(?:setlength|addtolength|renewcommand|def)\s*\{?\\(?:textwidth|textheight|"
    r"oddsidemargin|evensidemargin|topmargin|baselinestretch|baselineskip|parskip)\b"
)
ZIP_PREFIX = "law_to_action_final_supplement/"
CHECKSUM_PATHS = [
    "papers/completion/law_to_action/submission/paper.pdf",
    "papers/completion/law_to_action/submission/anonymous_supplement.zip",
    "papers/completion/law_to_action/submission/compliance_audit.md",
    "papers/completion/law_to_action/submission/disclosure.md",
    "papers/completion/law_to_action/submission/template_inputs.json",
    "papers/completion/law_to_action/manuscript/main.tex",
    "papers/completion/law_to_action/manuscript/results.tex",
    "papers/completion/law_to_action/manuscript/limitations.tex",
    "papers/completion/law_to_action/manuscript/checklist.tex",
    "papers/completion/law_to_action/manuscript/neurips_2026_vericode.sty",
    "papers/completion/law_to_action/manuscript/references.bib",
    "papers/completion/law_to_action/manuscript/related_work.bib",
    "papers/completion/law_to_action/artifact/anonymous_supplement.zip",
    "papers/completion/law_to_action/artifact/reproduce.sh",
    "papers/completion/law_to_action/artifact/reproduce.py",
    "papers/completion/law_to_action/artifact/manifest.json",
    "papers/completion/law_to_action/artifact/environment.lock",
    "papers/neurips_2026_vericode_workshop.tex",
    "papers/neurips_2026_vericode.sty",
    "papers/checklist.tex",
]


def utc_now():
    return datetime.now(timezone.utc)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def need(ok, message):
    if not ok:
        raise RuntimeError(message)


def sealed_env(home: Path) -> dict:
    env = {
        "PATH": SEALED_PATH,
        "HOME": str(home),
        "XDG_CACHE_HOME": str(home / ".cache"),
        "XDG_CONFIG_HOME": str(home / ".config"),
        "XDG_DATA_HOME": str(home / ".local/share"),
        "XDG_STATE_HOME": str(home / ".local/state"),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": "0",
        "SOURCE_DATE_EPOCH": "0",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "TZ": "UTC",
    }
    for name in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
        env[name] = "1"
    return env


def run(argv, cwd, env, log_dir, label, timeout=300):
    started = utc_now()
    stdout_path = log_dir / f"{label}.stdout.txt"
    stderr_path = log_dir / f"{label}.stderr.txt"
    with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
        proc = subprocess.run(
            argv,
            cwd=cwd,
            env=env,
            stdout=stdout,
            stderr=stderr,
            timeout=timeout,
            check=False,
        )
    finished = utc_now()
    record = {
        "argv": list(argv),
        "cwd": str(cwd),
        "exit_code": proc.returncode,
        "started_at": started.isoformat(),
        "completed_at": finished.isoformat(),
        "timeout_seconds": timeout,
        "stdout": str(stdout_path),
        "stderr": str(stderr_path),
        "execution_kind": "automated",
    }
    (log_dir / f"{label}.execution.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    need(proc.returncode == 0, f"{label} failed with exit {proc.returncode}; see {stderr_path}")
    return record


def which(name: str):
    return shutil.which(name, path=SEALED_PATH)


def extract_zip(archive: Path, dest: Path) -> Path:
    need(archive.is_file() and zipfile.is_zipfile(archive), "Submission ZIP missing or invalid")
    need(archive.stat().st_size <= 100_000_000, "ZIP exceeds 100 MB workshop cap")
    with zipfile.ZipFile(archive) as zipped:
        for info in zipped.infolist():
            path = PurePosixPath(info.filename)
            mode = info.external_attr >> 16
            need(path.parts and path.parts[0] == ZIP_PREFIX[:-1], "Unexpected ZIP prefix")
            need(not path.is_absolute() and ".." not in path.parts and "\\" not in info.filename, "Unsafe ZIP path")
            need(not info.is_dir() and not stat.S_ISLNK(mode) and not info.flag_bits & 1, "Nonregular ZIP member")
            out = dest / str(path)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(zipped.read(info))
            out.chmod(0o755 if str(path).endswith(".sh") else 0o644)
    root = dest / ZIP_PREFIX[:-1]
    need((root / "reproduce.sh").is_file(), "Extracted reproduce.sh missing")
    return root


def ratio_tuple(block):
    return (block["numerator"], block["denominator"], block["value"])


def add_ratio(left, right):
    return {
        "numerator": left["numerator"] + right["numerator"],
        "denominator": left["denominator"] + right["denominator"],
        "value": (left["numerator"] + right["numerator"]) / (left["denominator"] + right["denominator"]),
    }


def overall_from_splits(analysis):
    arms = {}
    for arm in ("A0", "A1", "A2", "A3", "A4"):
        acc = None
        for split in ("development", "calibration", "final"):
            metrics = analysis[split]["arms"][arm]
            if acc is None:
                acc = {
                    "forbidden_effect_rate": dict(metrics["forbidden_effect_rate"]),
                    "allowed_task_success_rate": dict(metrics["allowed_task_success_rate"]),
                    "decision_false_denial_rate": dict(metrics["decision_false_denial_rate"]),
                }
            else:
                for key in acc:
                    acc[key] = add_ratio(acc[key], metrics[key])
        arms[arm] = acc
    return arms


def checklist_skeleton(text, original=False):
    if original:
        text, count = re.subn(
            r"%%% BEGIN INSTRUCTIONS %%%.*?%%% END INSTRUCTIONS %%%\s*",
            "",
            text,
            count=1,
            flags=re.S,
        )
        need(count == 1, "Shared checklist instruction block missing")
    lines = []
    for line in text.splitlines():
        if r"\item[] Answer:" in line:
            line = re.sub(r"\\answer(?:TODO|Yes|No|NA)\{\}", r"\\answerFIELD{}", line, count=1)
        elif r"\item[] Justification:" in line:
            line = line[: line.index("Justification:") + len("Justification:")] + " FIELD"
        lines.append(line.rstrip())
    return "\n".join(lines).strip()


def inspect_pdf(pdf: Path, aux: Path, log: Path, env: dict) -> dict:
    need(pdf.is_file() and pdf.stat().st_size <= 50_000_000, "PDF missing or oversized")
    info = subprocess.check_output(["pdfinfo", str(pdf)], env=env, text=True)
    pages = int(re.search(r"^Pages:\s*(\d+)", info, re.M)[1])
    need(re.search(r"^Author:\s*(?:Anonymous Author\(s\))?\s*$", info, re.M), "Identifying PDF Author metadata")
    author = re.search(r"^Author:\s*(.*)$", info, re.M)
    author_value = (author.group(1).strip() if author else "") or "empty-anonymous"
    text = subprocess.check_output(["pdftotext", "-layout", str(pdf), "-"], env=env, text=True)
    parts = text.split("\f")
    need(len(parts) >= pages, "PDF text extraction incomplete")
    first = parts[0]
    need("Anonymous Author(s)" in first and "Affiliation" in first and "Address" in first and "email" in first, "Official anonymous block missing")
    need("Workshop on AI for Verifiable Coding" in text, "Workshop footer missing")
    need("Checklist" in text, "Rendered checklist missing")
    scanned = re.sub(r"Anonymous Author\(s\)|Affiliation|Address|email", "", text)
    leftover = PLACEHOLDER_RE.findall(scanned)
    need(not leftover, "Scientific placeholder in rendered PDF: " + ",".join(sorted(set(leftover))))
    aux_text = aux.read_text(encoding="utf-8", errors="replace")
    labels = re.findall(r"\\newlabel\{la-main-text-end\}\{\{[^}]*\}\{(\d+)\}", aux_text)
    need(len(labels) == 1, "Actual final-sentence page label missing")
    main_pages = int(labels[0])
    need(4 <= main_pages <= 9, "Main text outside 4-9 pages")
    need("References" in parts[main_pages], "References do not start after actual main text")
    log_text = log.read_text(encoding="utf-8", errors="replace")
    need(
        not re.search(r"Overfull \\hbox|There were undefined references|Citation .+ undefined|Reference .+ undefined", log_text),
        "Retained build log has overflow or unresolved citation/reference",
    )
    return {
        "bytes": pdf.stat().st_size,
        "sha256": sha256_file(pdf),
        "pages": pages,
        "main_text_pages": main_pages,
        "author_metadata": author_value,
        "anonymous_block": True,
        "workshop_footer": True,
        "scientific_placeholders": leftover,
        "pdfinfo": info,
    }


def audit_sources(repo: Path) -> dict:
    paper = repo / "papers/completion/law_to_action"
    main = (paper / "manuscript/main.tex").read_text(encoding="utf-8")
    results = (paper / "manuscript/results.tex").read_text(encoding="utf-8")
    style = paper / "manuscript/neurips_2026_vericode.sty"
    checklist = (paper / "manuscript/checklist.tex").read_text(encoding="utf-8")
    shared = {name: sha256_file(repo / name) for name in TEMPLATES}
    mismatches = {name: digest for name, digest in shared.items() if digest != TEMPLATES[name]}
    need(not mismatches, "Shared template changed: " + ", ".join(mismatches))
    need(sha256_file(style) == TEMPLATES["papers/neurips_2026_vericode.sty"], "Copied official style changed")
    need(r"\usepackage{neurips_2026_vericode}" in main, "Anonymous research style missing")
    need(not re.search(r"\\(?:documentclass|usepackage)\[[^\]]*(?:final|preprint|nonanonymous|sglblind|competition)", main, re.I), "Non-anonymous style option")
    need("neurips_2026.sty" not in main and "sglblindworkshop" not in main, "Wrong template")
    need(r"\input{checklist}" in main or r"\input{checklist.tex}" in main, "Checklist not included")
    need(re.search(r"\\input\{checklist(?:\.tex)?\}", main).start() > main.index(r"\bibliography"), "Checklist precedes bibliography")
    need(
        checklist_skeleton(checklist) == checklist_skeleton((repo / "papers/checklist.tex").read_text(encoding="utf-8"), True),
        "Official checklist questions/guidelines changed",
    )
    answers = re.findall(r"\\item\[\] Answer:\s*\\answer(Yes|No|NA)\{\}", checklist)
    justifications = re.findall(r"\\item\[\] Justification:\s*(.+)", checklist)
    need(len(answers) == len(justifications) == 16, "Checklist does not have 16 answers/justifications")
    need(all(len(item.strip()) > 20 for item in justifications), "Checklist justification too short")
    need("answerTODO" not in checklist and "justificationTODO" not in checklist, "Checklist placeholders remain")
    source_hits = []
    for path in sorted((paper / "manuscript").iterdir()):
        if path.suffix not in {".tex", ".bib"}:
            continue
        text = path.read_text(encoding="utf-8")
        if PLACEHOLDER_RE.search(text):
            source_hits.append(f"placeholder:{path.name}")
        if SCIENTIFIC_TODO_RE.search(text):
            source_hits.append(f"checklist-todo:{path.name}")
        if IDENTIFYING_RE.search(text):
            source_hits.append(f"identifying:{path.name}")
        if STYLE_OVERRIDE_RE.search(text):
            source_hits.append(f"font-override:{path.name}")
        if SPACING_OVERRIDE_RE.search(text):
            source_hits.append(f"spacing-override:{path.name}")
    need(not source_hits, "Source audit failures: " + "; ".join(source_hits))
    need("24$ pairs" not in results and r"24$ cases ($12$ pairs)" in results, "CVE polarity population ambiguity")
    need("19.793533" in results and "cumulative-active" in results and "18.022665493073873" in results, "Startup resource wording incomplete")
    return {
        "shared_templates_unchanged": True,
        "shared_template_sha256": shared,
        "copied_style_sha256": sha256_file(style),
        "anonymous_default_style": True,
        "checklist_answers": answers,
        "checklist_justification_count": len(justifications),
        "source_placeholder_hits": source_hits,
        "cve_population_wording": "24 cases / 12 pairs",
    }


def compare_claims(repo: Path, analysis: dict) -> dict:
    summary = json.loads((repo / "papers/completion/law_to_action/results/fixed_actions_admitted/summary.json").read_text())
    metrics = json.loads((repo / "papers/completion/law_to_action/results/source_ir/metrics.json").read_text())
    results = (repo / "papers/completion/law_to_action/manuscript/results.tex").read_text(encoding="utf-8")
    matrix = json.loads((repo / "papers/completion/law_to_action/claim_evidence_matrix.json").read_text())
    overall = overall_from_splits(analysis)
    expected = {
        ("overall", "A0"): (90, 90, 90, 90, 0, 90),
        ("overall", "A1"): (90, 90, 90, 90, 0, 90),
        ("overall", "A2"): (90, 90, 90, 90, 0, 90),
        ("overall", "A3"): (33, 90, 90, 90, 0, 90),
        ("overall", "A4"): (0, 90, 90, 90, 0, 90),
        ("final", "A0"): (54, 54, 54, 54, 0, 54),
        ("final", "A3"): (18, 54, 54, 54, 0, 54),
        ("final", "A4"): (0, 54, 54, 54, 0, 54),
    }
    observed = {}
    mismatches = []
    for split, arm in expected:
        block = analysis[split]["arms"][arm] if split == "final" else overall[arm]
        forb, allow, deny = block["forbidden_effect_rate"], block["allowed_task_success_rate"], block["decision_false_denial_rate"]
        got = (forb["numerator"], forb["denominator"], allow["numerator"], allow["denominator"], deny["numerator"], deny["denominator"])
        observed[f"{split}:{arm}"] = got
        if got != expected[(split, arm)]:
            mismatches.append(f"{split}:{arm} got {got} expected {expected[(split, arm)]}")
    need(not mismatches, "Recomputed rates differ from paper table: " + "; ".join(mismatches))
    need(analysis["final"]["families"] == 18, "Final family count differs")
    need(summary["rows"] == 900 and summary["host_attempts"] == 902, "Admitted summary denominators differ")
    need(summary["measured_group_cpu_seconds"] == 1608.817478, "CPU total differs")
    need(summary["model_calls"] == 0 and summary["human_agreement"] is None and summary["human_fidelity"] is None, "Unmeasured fields were filled")
    need(metrics["case_accounting"]["records"] == 60, "Source-IR cohort changed")
    need(metrics["by_population"]["legal"]["span_linked"]
         + metrics["by_population"]["cve"]["span_linked"]
         + metrics["by_population"]["skill"]["span_linked"] == 60, "Span linkage is not 60/60")
    schema = (
        metrics["by_population"]["legal"]["schema_valid"]
        + metrics["by_population"]["cve"]["schema_valid"]
        + metrics["by_population"]["skill"]["schema_valid"]
    )
    need(schema == 50, "Schema validity is not 50/60")
    need(metrics["independent_human_gold"] is False, "Human gold was asserted")
    forbidden_claims = []
    joined = results + json.dumps(matrix)
    for phrase in (
        "expert legal fidelity rate",
        "inter-annotator agreement of",
        "universal legal correctness",
        "universal prevention",
        "workshop acceptance",
    ):
        if phrase in joined.lower():
            forbidden_claims.append(phrase)
    need("withdrawn" in results.lower() or "unmeasured" in results.lower(), "Withdrawn legal-fidelity scope missing")
    return {
        "recomputed_table": observed,
        "rate_mismatches": mismatches,
        "source_ir_span_linked": 60,
        "source_ir_schema_valid": schema,
        "summary_rows": summary["rows"],
        "summary_host_attempts": summary["host_attempts"],
        "model_calls": summary["model_calls"],
        "human_agreement": summary["human_agreement"],
        "unsupported_empirical_phrases": forbidden_claims,
        "claim_statuses": sorted({row["status"] for row in matrix.get("manuscript_claims", [])}),
    }


def fetch_cfp(env, retained: Path) -> dict:
    record = {
        "url": "https://vericodegen.github.io/cfp.html",
        "retained_sha256": RETAINED_CFP_SHA256,
        "live_fetch": False,
        "live_sha256": None,
        "http_status": None,
        "error": None,
        "matches_retained": None,
        "paper_deadline": "2026-09-13 AoE",
        "abstract_deadline": "2026-09-11 AoE",
        "activity": "automated",
    }
    try:
        import urllib.request

        request = urllib.request.Request(record["url"], headers={"User-Agent": "law-to-action-la025-isolated/1"})
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read()
            record["http_status"] = int(response.status)
            record["live_fetch"] = True
            record["live_sha256"] = sha256_bytes(body)
            record["live_bytes"] = len(body)
            record["matches_retained"] = record["live_sha256"] == RETAINED_CFP_SHA256
    except Exception as exc:  # network may be absent in the sealed environment
        record["error"] = f"{type(exc).__name__}: {exc}"
        if retained.is_file():
            record["retained_present"] = True
            record["retained_actual_sha256"] = sha256_file(retained)
            record["matches_retained"] = record["retained_actual_sha256"] == RETAINED_CFP_SHA256
    return record


def write_checksums(repo: Path, extra: dict) -> str:
    lines = []
    for rel in CHECKSUM_PATHS:
        path = repo / rel
        need(path.is_file(), f"checksum target missing: {rel}")
        lines.append(f"{sha256_file(path)}  {rel}")
    for rel, digest in extra.items():
        lines.append(f"{digest}  {rel}")
    return "\n".join(lines) + "\n"


def render_final_validation(obs: dict) -> str:
    env = obs["environment"]
    analysis = obs["analysis_verification"]
    pdf = obs["pdf"]
    disc = obs["discrepancies"]
    claims = obs["claims"]
    cfp = obs["cfp"]
    checklist = ", ".join(obs["sources"]["checklist_answers"])
    disc_md = "\n".join(f"- {item}" for item in disc) if disc else "- None that block the retained-data reproduction or invalidate the current artifacts."
    return f"""# LA-025 final validation

Paper: From Law to Action: Neuro-Symbolic Runtime Enforcement for MCP Agents.
Task: isolated retained-data reproduction, package audit, optional author handoff.
Recorded: {obs["completed_at"]}.
Activity class: **automated**. Independent human review was not collected and is not required.

This record is technical reproduction and artifact integrity evidence. It is not workshop submission, acceptance, author impersonation, or independent human validation.

## Environment (authoritative validation PATH)

| Field | Value |
| --- | --- |
| PATH | `{env["PATH"]}` |
| Python | `{env["python_executable"]}` ({env["python_version"]}) |
| Python SHA-256 | `{env["python_executable_sha256"]}` |
| HOME | private directory `{env["home_basename"]}` |
| XDG cache/config/data/state | `$HOME/.cache`, `$HOME/.config`, `$HOME/.local/share`, `$HOME/.local/state` |
| latexmk | `{env["tools"]["latexmk"]}` |
| pdflatex | `{env["tools"]["pdflatex"]}` |
| pdfinfo | `{env["tools"]["pdfinfo"]}` |
| pdftotext | `{env["tools"]["pdftotext"]}` |
| git HEAD | `{env["git_head"]}` |
| repository dirty files | {env["git_dirty_files"]} |

`latexmk` and `pdflatex` are absent from the sealed PATH. The documented PDF rebuild (`./build_pdf.sh`) was **not executed** in this environment. The existing LA-024 compiled `paper.pdf` was inspected with `pdfinfo`/`pdftotext` against the retained `main.aux`/`main.log`. That is a toolchain capability gap for a fresh TeX rebuild, not a missing scientific run.

## Commands actually executed (automated)

1. Isolated extract of `papers/completion/law_to_action/submission/anonymous_supplement.zip` into a fresh directory.
2. `./reproduce.sh --output <fresh-analysis>` from the extracted package, with sealed PATH and private HOME.
3. `pdfinfo` and `pdftotext -layout` on the live `submission/paper.pdf`.
4. Source, checklist, template-checksum, claim, and placeholder audits in this process.
5. Optional live CFP GET of `https://vericodegen.github.io/cfp.html`.

Exact argv, exit codes, and logs are retained under `papers/completion/law_to_action/receipts/snapshots/LA-025/`.

## Observed reproduction outcomes

The bounded reproduction is retained-data analysis. It does **not** rerun the 900-cell operator matrix, Docker cells, solvers, or models.

| Check | Observed |
| --- | --- |
| package files verified | `{analysis["all_package_files_verified"]}` |
| 9,933 reducer inputs verified | `{analysis["all_9933_original_reducer_inputs_verified"]}` |
| 45 paired family-bootstrap contrasts recomputed | `{analysis["all_45_paired_family_bootstrap_contrasts_recomputed"]}` |
| scientific rows | `{analysis["scope"]["scientific_rows"]}` |
| host attempts | `{analysis["scope"]["host_attempts"]}` |
| group CPU seconds | `{analysis["scope"]["actual_group_cpu_seconds"]}` |
| startup CPU counted once | `{analysis["scope"]["startup_cpu_seconds_counted_once"]}` |
| new scientific executions | `{analysis["new_scientific_executions"]}` |
| compact analysis exit | `{analysis["compact_analysis"]["exit_code"]}` |
| recovery analysis exit | `{analysis["recovery_analysis"]["exit_code"]}` |

Recomputed modeled-policy rates (independent effect counters):

| Arm | Split | Forbidden effects | Allowed useful work | False denials |
| --- | --- | --- | --- | --- |
| A0 | overall | 90/90 | 90/90 | 0/90 |
| A1 | overall | 90/90 | 90/90 | 0/90 |
| A2 | overall | 90/90 | 90/90 | 0/90 |
| A3 | overall | 33/90 | 90/90 | 0/90 |
| A4 | overall | 0/90 | 90/90 | 0/90 |
| A0 | final | 54/54 | 54/54 | 0/54 |
| A3 | final | 18/54 | 54/54 | 0/54 |
| A4 | final | 0/54 | 54/54 | 0/54 |

These equal the manuscript Table 3 and the admitted `summary.json`. They remain finite, policy-relative sandbox observations, not legal correctness or universal prevention.

## Manuscript and artifact audit (automated)

| Check | Observed |
| --- | --- |
| paper.pdf SHA-256 | `{pdf["sha256"]}` |
| paper.pdf bytes | {pdf["bytes"]} |
| main-text pages | {pdf["main_text_pages"]} (required 4–9) |
| total PDF pages | {pdf["pages"]} |
| official anonymous block | present |
| workshop footer | present |
| scientific PDF placeholders | {pdf["scientific_placeholders"] or "none"} |
| ZIP SHA-256 | `{obs["zip"]["sha256"]}` |
| ZIP bytes | {obs["zip"]["bytes"]} |
| shared templates unchanged | `{obs["sources"]["shared_templates_unchanged"]}` |
| copied style SHA-256 | `{obs["sources"]["copied_style_sha256"]}` |
| checklist answers (16) | {checklist} |
| source-IR span linkage | 60/60 |
| source-IR schema validity | 50/60 |
| model calls in scored study | {claims["model_calls"]} |
| human_agreement / human_fidelity | `{claims["human_agreement"]}` / unmeasured |

Style-generated `Anonymous Author(s)`, `Affiliation`, `Address`, and `email` were exempted from the residual-placeholder scan. Scientific and checklist placeholders remain failures; none were found.

## Automated versus human activities

**Automated (this task):** isolated ZIP extract; `reproduce.sh` retained-data analysis; PDF text/metadata inspection; template checksums; checklist completeness; claim-to-raw comparison; CFP fetch attempt; checksum generation; handoff/metadata drafting.

**Human, not performed and not required:** independent legal/security/intent annotation; inter-annotator agreement; expert legal fidelity scoring; optional author scientific sign-off; OpenReview/CFP portal submission; workshop acceptance.

Missing outside reviewers and missing optional author feedback are **not blockers**. Missing required execution evidence or invalid artifact claims **would be blockers**; the bounded reproduction and live artifact hashes succeeded.

## Discrepancies

{disc_md}

## Residual limitations (not converted into results)

- Closed-loop generated-code planning remains withdrawn (`900/900` not started; model calls `0`).
- Expert legal fidelity, human agreement, and legal-validity rates remain unmeasured.
- LA-009 `18/18` is shared-producer conformance, not independent checker agreement.
- Original LA-015/rescue and LA-016/LA-017 comparison wording are protocol-unadmitted diagnostics.
- LA-020 traces are separate diagnostic replays.
- SAT/UNSAT on the selected QF_BOOL route has satisfiability authority only.
- Native Docker/runtime binaries, private keys, and corpus bodies are not in the anonymous ZIP; retrieving a hash is not a fresh scientific rerun.
- `latexmk` is absent from the sealed PATH, so this task did not rebuild the PDF.

## Submission status

No file was uploaded, no author identity was asserted, and no workshop decision is implied. Proposed metadata for the authors is in `metadata.json`. Optional author review instructions are in `author_handoff.md`.
"""


def render_handoff(obs: dict) -> str:
    pdf = obs["pdf"]
    return f"""# Optional author handoff (LA-025)

This package is an **anonymous submission candidate** prepared by automated completion.
It is **not** an OpenReview submission, camera-ready deposit, or workshop acceptance.

Authors retain abstract registration, portal upload, review consent, authorship/funding facts, and final scientific sign-off. This task did not impersonate authors and did not contact organizers.

## What was completed automatically

- Isolated retained-data reproduction of the anonymous supplement (`./reproduce.sh`).
- Inspection of the compiled PDF and official-template/checklist constraints.
- Claim-to-raw comparison of Table 3 and the admitted 900-cell summary.
- SHA-256 inventory of the reviewable final files.

Optional author reading, if you do it, is **non-independent**. It is not expert legal review, not inter-annotator agreement, and not a prerequisite for generating this candidate.

## Files to review (do not treat this list as a submission)

| File | Role |
| --- | --- |
| `papers/completion/law_to_action/submission/paper.pdf` | Anonymous compiled manuscript (7 main / 23 total pages; SHA-256 `{pdf["sha256"]}`) |
| `papers/completion/law_to_action/submission/anonymous_supplement.zip` | Anonymous retained-data supplement (SHA-256 `{obs["zip"]["sha256"]}`) |
| `papers/completion/law_to_action/submission/compliance_audit.md` | Double-blind / template audit |
| `papers/completion/law_to_action/submission/disclosure.md` | LLM and human-judgment disclosure |
| `papers/completion/law_to_action/submission/final_validation.md` | This isolated reproduction record |
| `papers/completion/law_to_action/submission/checksums.sha256` | Final file hashes |
| `papers/completion/law_to_action/submission/metadata.json` | Proposed venue metadata, explicitly `not_submitted` |

## Author-only actions (not performed here)

1. Read the PDF and supplement. Confirm you accept the bounded, policy-relative claims and the withdrawn human/legal-fidelity scope.
2. Recheck https://vericodegen.github.io/cfp.html immediately before any portal action. Paper deadline recorded here: 2026-09-13 AoE (end of AoE is 2026-09-14 12:00 UTC).
3. If you submit, upload the **anonymous** PDF and ZIP yourselves. Do not add author-maintained URLs to the anonymous package.
4. Keep the private alias map, credentials, live database, and `papers/completion/law_to_action/private/` out of the public bundle.
5. Any later author comments are descriptive, not independent gold labels.

## Residual scientific blockers you must not paper over

- Do not report expert legal fidelity, human agreement, or legal validity numbers: they were not collected.
- Do not describe A4 `0/90` forbidden effects as universal safety or legality.
- Do not pool withdrawn closed-loop planning zeros with the admitted fixed-action matrix.
- Do not treat LA-015 diagnostic rates or LA-020 replays as the admitted study.
- A fresh physical 900-cell rerun requires a separately prepared runtime, Docker boundary, and new private store/key; this handoff does not supply them.

## Reviewer / validation note

Independent outside review is not available and is not required for this amended automated-evidence paper. Returning a blank review packet later would still not convert compiler agreement into expert gold.
"""


def render_metadata(obs: dict) -> dict:
    pdf = obs["pdf"]
    return {
        "schema": "law-to-action-proposed-submission-metadata/v1",
        "status": "not_submitted",
        "external_upload": False,
        "workshop_acceptance": "not_claimed",
        "human_validation": "not_collected",
        "optional_author_review": {
            "required": False,
            "status": "not_returned",
            "independence": "non-independent if later supplied",
            "replaces_empirical_outcomes": False,
        },
        "venue": {
            "name": "NeurIPS 2026 Workshop on AI for Verifiable Coding",
            "track": "research",
            "double_blind": True,
            "non_archival": True,
            "cfp_url": "https://vericodegen.github.io/cfp.html",
            "cfp_live_fetch": obs["cfp"],
            "abstract_deadline": "2026-09-11 AoE",
            "paper_deadline": "2026-09-13 AoE",
            "paper_deadline_utc": "2026-09-14T12:00:00+00:00",
            "review_deadline": "2026-09-27",
            "notification": "2026-09-29",
            "camera_ready": "2026-10-14",
            "workshop": "2026-12-12 Atlanta",
            "main_text_pages": "4-9 excluding references and appendices",
            "pdf_max_mb": 50,
            "supplement_max_mb": 100,
            "template": "neurips_2026_vericode_workshop.tex + neurips_2026_vericode.sty (2026-01-29)",
        },
        "paper": {
            "title": "From Law to Action: Neuro-Symbolic Runtime Enforcement for MCP Agents",
            "anonymous": True,
            "official_author_block": ["Anonymous Author(s)", "Affiliation", "Address", "email"],
            "main_text_pages": pdf["main_text_pages"],
            "total_pages": pdf["pages"],
            "pdf_bytes": pdf["bytes"],
            "pdf_sha256": pdf["sha256"],
            "zip_bytes": obs["zip"]["bytes"],
            "zip_sha256": obs["zip"]["sha256"],
            "checklist_answers": obs["sources"]["checklist_answers"],
        },
        "reproduction": {
            "kind": "automated_isolated_retained_data_analysis",
            "new_scientific_executions": 0,
            "scientific_rows": 900,
            "host_attempts": 902,
            "model_calls": 0,
            "human_agreement": None,
            "latexmk_in_sealed_path": False,
            "pdf_rebuilt_in_this_task": False,
        },
        "files": {
            "paper_pdf": "papers/completion/law_to_action/submission/paper.pdf",
            "anonymous_supplement": "papers/completion/law_to_action/submission/anonymous_supplement.zip",
            "final_validation": "papers/completion/law_to_action/submission/final_validation.md",
            "checksums": "papers/completion/law_to_action/submission/checksums.sha256",
            "author_handoff": "papers/completion/law_to_action/submission/author_handoff.md",
        },
        "prohibitions": [
            "Do not interpret this metadata as a completed submission.",
            "Do not interpret optional author review as independent human gold.",
            "Do not fill unmeasured legal-fidelity or agreement rates.",
        ],
        "recorded_at": obs["completed_at"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--submission", type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()
    snapshot = args.snapshot.resolve()
    submission = args.submission.resolve()
    snapshot.mkdir(parents=True, exist_ok=True)
    work = snapshot / "work"
    need(not work.exists(), "Snapshot work directory must be fresh")
    work.mkdir(mode=0o700)
    home = work / "home"
    home.mkdir()
    for rel in (".cache", ".config", ".local/share", ".local/state"):
        (home / rel).mkdir(parents=True)
    env = sealed_env(home)
    logs = work / "logs"
    logs.mkdir()
    extract_root = work / "extract"
    extract_root.mkdir()
    analysis_out = work / "analysis"
    reports = work / "reports"
    reports.mkdir()

    tools = {name: which(name) or "absent" for name in ("python3", "python3.12", "latexmk", "pdflatex", "pdfinfo", "pdftotext", "git")}
    need(tools["python3.12"] == PYTHON or Path(tools["python3.12"]).resolve() == Path(PYTHON), "Canonical Python is not /usr/bin/python3.12")
    need(tools["pdfinfo"] != "absent" and tools["pdftotext"] != "absent", "pdfinfo/pdftotext missing from sealed PATH")
    python_sha = sha256_file(Path(PYTHON))
    git_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, env=env, text=True).strip()
    dirty = subprocess.check_output(["git", "status", "--porcelain"], cwd=repo, env=env, text=True)
    environment = {
        "PATH": SEALED_PATH,
        "python_executable": PYTHON,
        "python_version": sys.version.split()[0],
        "python_executable_sha256": python_sha,
        "home_basename": home.name,
        "tools": tools,
        "git_head": git_head,
        "git_dirty_files": len([line for line in dirty.splitlines() if line.strip()]),
        "latexmk_rebuild_attempted": False,
        "activity": "automated",
    }

    zip_path = repo / "papers/completion/law_to_action/submission/anonymous_supplement.zip"
    pdf_path = repo / "papers/completion/law_to_action/submission/paper.pdf"
    zip_info = {"bytes": zip_path.stat().st_size, "sha256": sha256_file(zip_path)}
    need(zip_info["sha256"] == LA024_ZIP, "Live ZIP does not match LA-024 public_redaction_v4 hash")
    need(sha256_file(pdf_path) == LA024_PDF, "Live PDF does not match LA-024 public_redaction_v4 hash")
    need(
        sha256_file(repo / "papers/completion/law_to_action/artifact/anonymous_supplement.zip") == zip_info["sha256"],
        "Artifact ZIP and submission ZIP differ",
    )

    extracted = extract_zip(zip_path, extract_root)
    reproduce = run(
        ["/bin/sh", str(extracted / "reproduce.sh"), "--output", str(analysis_out)],
        extracted,
        env,
        logs,
        "isolated_reproduce",
        timeout=300,
    )
    verification = json.loads((analysis_out / "verification.json").read_text())
    need(verification["success"] and verification["new_scientific_executions"] == 0, "Reproduction did not succeed in retained-data scope")
    need(verification["all_package_files_verified"] and verification["all_9933_original_reducer_inputs_verified"], "Package/reducer verification failed")
    need(verification["all_45_paired_family_bootstrap_contrasts_recomputed"], "Bootstrap recomputation missing")
    split_analysis = json.loads((analysis_out / "recovery_analysis" / "split_analysis.json").read_text())
    recovery = json.loads((analysis_out / "recovery_analysis" / "verification.json").read_text())
    need(recovery["scientific_rows"] == 900 and recovery["host_attempts"] == 902, "Recovery denominators differ")

    aux = repo / "papers/completion/law_to_action/receipts/snapshots/LA-024/public_redaction_v4/build_evidence/main.aux"
    log = repo / "papers/completion/law_to_action/receipts/snapshots/LA-024/public_redaction_v4/build_evidence/main.log"
    pdf = inspect_pdf(pdf_path, aux, log, env)
    need(pdf["sha256"] == LA024_PDF, "Inspected PDF hash drifted")
    sources = audit_sources(repo)
    claims = compare_claims(repo, split_analysis)
    cfp = fetch_cfp(env, repo / "papers/completion/law_to_action/receipts/snapshots/LA-024/cfp.html")

    template_inputs = json.loads((repo / "papers/completion/law_to_action/submission/template_inputs.json").read_text())
    discrepancies = []
    if tools["latexmk"] == "absent" or tools["pdflatex"] == "absent":
        discrepancies.append(
            "AUTOMATED capability gap: latexmk/pdflatex are absent from PATH "
            f"{SEALED_PATH}. Documented ./build_pdf.sh was not run. Live paper.pdf "
            f"{pdf['sha256']} was inspected instead of rebuilt."
        )
    compiled = template_inputs.get("compiled", {})
    if compiled.get("pdf_sha256") != pdf["sha256"]:
        discrepancies.append(
            "HISTORICAL: submission/template_inputs.json compiled.pdf_sha256 "
            f"{compiled.get('pdf_sha256')} records the earlier LA-024 compile; "
            f"live paper.pdf is the public_redaction_v4 file {pdf['sha256']}. "
            "Not a scientific outcome change."
        )
    if compiled.get("zip_sha256") != zip_info["sha256"]:
        discrepancies.append(
            "HISTORICAL: submission/template_inputs.json compiled.zip_sha256 "
            f"{compiled.get('zip_sha256')} records the earlier LA-024 archive; "
            f"live ZIP is the public_redaction_v4 file {zip_info['sha256']}. "
            "Not a scientific outcome change."
        )
    stale_log = repo / "papers/completion/law_to_action/manuscript/main.log"
    if stale_log.is_file() and "11 SEP 2026" in stale_log.read_text(encoding="utf-8", errors="replace")[:400]:
        discrepancies.append(
            "WORKTREE: papers/completion/law_to_action/manuscript/main.log is a stale 2026-09-11 compile and is not the submission PDF log. Citation/overflow checks used the retained LA-024 public_redaction_v4 build_evidence logs."
        )
    if cfp.get("live_fetch") is False:
        discrepancies.append(
            "AUTOMATED: live CFP fetch did not succeed "
            f"({cfp.get('error')}). Dates below use the retained 2026-09-13 snapshot "
            f"{RETAINED_CFP_SHA256} and are not a fresh page hash."
        )
    elif cfp.get("matches_retained") is False:
        discrepancies.append(
            "AUTOMATED: live CFP bytes differ from the 2026-09-13 retained snapshot. "
            "Authors must re-read the live page before any portal action. This task still does not submit."
        )

    observed = {
        "schema": "law-la025-isolated-reproduction/v1",
        "completed_at": utc_now().isoformat(),
        "environment": environment,
        "zip": zip_info,
        "pdf": {k: v for k, v in pdf.items() if k != "pdfinfo"},
        "analysis_verification": verification,
        "recovery_verification": recovery,
        "reproduce_command": reproduce,
        "sources": sources,
        "claims": claims,
        "cfp": cfp,
        "discrepancies": discrepancies,
        "activity_labels": {
            "automated": [
                "isolated ZIP extract",
                "reproduce.sh retained-data analysis",
                "pdfinfo/pdftotext inspection",
                "template/checklist/placeholder audit",
                "claim-to-raw comparison",
                "optional CFP fetch",
            ],
            "human_not_performed": [
                "independent legal/security/intent review",
                "inter-annotator agreement",
                "optional author scientific sign-off",
                "OpenReview or CFP portal submission",
                "workshop acceptance",
            ],
        },
        "new_scientific_executions": 0,
        "external_submission": False,
        "pdf_rebuilt_in_this_task": False,
    }
    (reports / "observation.json").write_text(json.dumps(observed, indent=2, sort_keys=True) + "\n")
    (reports / "pdfinfo.txt").write_text(pdf["pdfinfo"])
    shutil.copy2(analysis_out / "verification.json", reports / "analysis_verification.json")
    shutil.copy2(analysis_out / "recovery_analysis" / "verification.json", reports / "recovery_verification.json")
    shutil.copy2(analysis_out / "recovery_analysis" / "split_analysis.json", reports / "split_analysis.json")

    validation_text = render_final_validation(observed)
    handoff_text = render_handoff(observed)
    metadata = render_metadata(observed)
    submission.mkdir(parents=True, exist_ok=True)
    (submission / "final_validation.md").write_text(validation_text)
    (submission / "author_handoff.md").write_text(handoff_text)
    (submission / "metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    extra = {
        "papers/completion/law_to_action/submission/final_validation.md": sha256_file(submission / "final_validation.md"),
        "papers/completion/law_to_action/submission/author_handoff.md": sha256_file(submission / "author_handoff.md"),
        "papers/completion/law_to_action/submission/metadata.json": sha256_file(submission / "metadata.json"),
    }
    checksums = write_checksums(repo, extra)
    (submission / "checksums.sha256").write_text(checksums)
    outputs = snapshot / "outputs"
    outputs.mkdir()
    for name in ("final_validation.md", "author_handoff.md", "metadata.json", "checksums.sha256"):
        shutil.copy2(submission / name, outputs / name)

    summary = {
        "success": True,
        "pdf_sha256": pdf["sha256"],
        "zip_sha256": zip_info["sha256"],
        "main_text_pages": pdf["main_text_pages"],
        "total_pages": pdf["pages"],
        "new_scientific_executions": 0,
        "external_submission": False,
        "latexmk_absent": tools["latexmk"] == "absent",
        "discrepancy_count": len(discrepancies),
        "checklist_answers": sources["checklist_answers"],
    }
    (reports / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
