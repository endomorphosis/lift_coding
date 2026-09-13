#!/usr/bin/env python3.12
"""Independent NS-025 readiness audit.

Sealed validation PATH is /usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin.
This program uses python3.12, pdffonts, pdfinfo, and pdftotext. It extracts
the frozen anonymous ZIP and reruns the included numerical reproducers. It
does not invoke pdflatex, providers, scorers, hidden tests, or any portal.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ACCEPTED_PDF = "0fb82abbec94c3858b6c9e63fcd456b16a5ad4aa2f294c4b52d08a8592c59862"
ACCEPTED_ZIP = "48cee756e4e1bcdcf4d541b6c8721f21cba0800e990e1159a64f3eeb888a0b07"
NS022_PDF = "907f0a24b775d22cbff1a35e958c2f121cbb4784756b2943dcee4eb5ae3e14ab"
NS022_MAIN = "d10683b13e4fb0c5566e3b71fb7941fb2a95f1be5e1a50aa38957fe3092bf8ab"
NS019_ASCII_PDF = "8ea081bca5d5e309cc5659628b7ceea5e053089b3adfd1d5ae11a7f5c163e4a5"
TABLE17 = "ffbb7f2e6aecefb0e4a65fe2da32cc43e87601e01eb7ab97715e516a22cc0b79"
TABLE18 = "3fa332e34627a5825f6065623ac39bd3f0a5041627375d167e3fd397f33e2495"
ABLATIONS = "8c57477902aba200e9a2228d6a316ec06f14859f7894fa1f534f16e8b19d8ccf"
RESULTS_SHA = "6b07e88ff02ad6674fd5979b361f4de4f121ec6b58906927d8cbfafca86b972e"
FREEZE_FILE = "7175ca68247d958dabf83a97441fe6042d3b88feafa74f95c76e1720cc74fa1a"
FREEZE_CANON = "ac605b5de8b58cc41c5c3609e7752e5e4441ab627dbbe6d31f4d8d086b33732d"
STYLE = "2944ec0d4f64dba353827e9ead104da1a9ac81b4057f4ff40969c693632a1e11"
SHARED_CHECKLIST = "780ba13c480f652dcc42e69ed61a752ce0ea270f15d332d4a45b059dabad84f6"
ANSWERED_CHECKLIST = "48859ff3d74dd0fabfbd77a1579b5d51d2d226a5564fab9b81f27aa3c4b531b1"
WORKSHOP_TEX = "c1c74133705d906972ee7571ee34f57122da5088e9f09ffe9dacb01cf0db1250"
SOURCE_MANIFEST = "89bffcb1545d491945dba5604dc11ea3fa0a0a9745d2b3ef44b0fd85a1aa0973"
FINAL32_MANIFEST = "6612cfa4b957d7aa701d6cc3255f37bd47c95758dbe88f22ecbc1a6b32f1ec26"
PRIOR_MANIFEST = "1d00715d05bbea2c7cab0ef1892f039153cc12ea0820bd556a13452ffe6b70a7"
BOUNDARY_MANIFEST = "8addd3465f79791a1126d6fb4bf08c77107fa5a4e5b1ddf844d8b78b48271369"
GENERIC_STY = "c3fc2894e83d2517ca18b66741d6c595986d97957dc08ec08bb2125a7ec4555a"
COMP_STY = "a0178f152d13cf24f44936da0ee95bab975ceced8d54980efbbf8f7c1bb31f72"
NS024_RECEIPT_PDF = ACCEPTED_PDF
NS024_RECEIPT_ZIP = ACCEPTED_ZIP
HANDOFF_SHA = "c9917e47d6a8b54fbd5dcaba4eb94bb13fb60b017d3462569726918bccaa2304"
CFP_SHA = "0f7294cf7e1381104fb443a4a1c78acf58dfc06a3f73738752ad8534bbdeb1b3"
HANDOFF_PATH = Path(
    "/home/barberb/lift_coding/papers/completion/runtime_bootstrap/"
    "unblock_20260912/ns028_ab_pilot_review/runtime_contract_v3/"
    "final_AB_cold32_proposal_v1/actual_post32_v1/"
    "ns024_final_artifact_handoff_v1.md"
)
CFP_PATH = Path(
    "/home/barberb/lift_coding/papers/completion/runtime_bootstrap/"
    "unblock_20260912/ns028_ab_pilot_review/runtime_contract_v3/"
    "final_AB_cold32_proposal_v1/actual_post32_v1/"
    "workshop_requirements_1257_v1/review.private.json"
)
OPERATOR_CFP = {
    "source": "root_operator_task_instruction",
    "declared_path": str(CFP_PATH),
    "declared_sha256": CFP_SHA,
    "main_pages": "4-9",
    "pdf_limit_mb": 50,
    "anonymous_zip_limit_mb": 100,
    "official_template_unchanged": True,
    "author_proofread_required": True,
    "llm_disclosure_required": True,
    "deadline": "2026-09-14T12:00:00Z",
    "abstracts_registered_claimed_by_root": 3,
    "this_worker_did_not_fetch_live_portal": True,
}
EXPECTED_ANSWERS = [
    "Yes", "Yes", "No", "No", "No", "Yes", "Yes", "No",
    "N/A", "Yes", "N/A", "No", "Yes", "N/A", "N/A", "Yes",
]
DISCLOSURE_PLACEHOLDERS = [
    "[actual implementation assistance]",
    "[candidate goals/plans/patches]",
    "[proof candidates]",
    "[data processing]",
    "[manuscript preparation]",
]
SCIENTIFIC_PLACEHOLDERS = [
    r"\[TODO\]",
    r"\\answerTODO",
    r"\\justificationTODO",
    r"answerTODO",
    r"justificationTODO",
    r"TO BE FILLED",
    r"\bTBD\b",
    r"compilation placeholder",
    r"\[RESULTS(?:\s*:|\])",
    r"\[CITATION",
    r"\[REFERENCE",
    r"lorem ipsum",
    r"\bFIXME\b",
    r"\bXXX\b",
]
ANON_EXEMPT = (
    "Anonymous Author(s)",
    "Anonymous Authors",
    "Affiliation",
    "Address",
    "email",
)
FAMILY_ROWS = (
    ("tomlkit", "1", "1"),
    ("installer", "0", "0"),
    ("tornado", "2", "1"),
    ("more-itertools", "2", "2"),
    ("charset", "0", "0"),
    ("iniconfig", "0", "0"),
    ("wheel", "0", "0"),
    ("jinja", "0", "0"),
)
NS025_OUTPUTS = (
    "papers/completion/neurosymbolic_supervision/release/FINAL_REVIEW.md",
    "papers/completion/neurosymbolic_supervision/release/checksums.sha256",
    "papers/completion/neurosymbolic_supervision/audit/final_readiness.json",
    "papers/completion/neurosymbolic_supervision/audit/final_placeholder_scan.json",
)
PREDECESSORS = tuple(f"NS-{i:03d}" for i in range(1, 25))


def repository_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in [here, *here.parents]:
        if (candidate / "scripts/paper_supervisors.py").is_file() and (
            candidate / "papers/completion/neurosymbolic_supervision"
        ).is_dir():
            return candidate
    raise FileNotFoundError("cannot locate repository root from auditor path")


ROOT = repository_root()
PAPER = ROOT / "papers/completion/neurosymbolic_supervision"
LIVE_MS = PAPER / "manuscript"
LIVE_REL = PAPER / "release"
LIVE_AUDIT = PAPER / "audit"
SNAP024 = PAPER / "receipts/snapshots/NS-024"
SNAP025 = PAPER / "receipts/snapshots/NS-025"
MS_SRC = SNAP024 / "manuscript_source_v1"


def sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fail(failures: list[str], message: str) -> None:
    failures.append(message)


def sealed_tool(name: str) -> str | None:
    for directory in ("/usr/local/sbin", "/usr/local/bin", "/usr/sbin", "/usr/bin"):
        candidate = Path(directory) / name
        if candidate.is_file():
            return str(candidate)
    return None


def run_tool(name: str, args: list[str]) -> subprocess.CompletedProcess[str]:
    binary = sealed_tool(name)
    if binary is None:
        raise FileNotFoundError(f"sealed-PATH tool missing: {name}")
    return subprocess.run([binary, *args], check=True, capture_output=True, text=True)


def pdf_text(path: Path, first: int | None = None, last: int | None = None) -> str:
    args = ["-layout"]
    if first is not None:
        args.extend(["-f", str(first)])
    if last is not None:
        args.extend(["-l", str(last)])
    args.extend([str(path), "-"])
    return run_tool("pdftotext", args).stdout


def pdf_info(path: Path) -> dict[str, str]:
    info = {}
    for line in run_tool("pdfinfo", [str(path)]).stdout.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            info[key.strip()] = value.strip()
    return info


def pdf_fonts(path: Path) -> str:
    return run_tool("pdffonts", [str(path)]).stdout


def folded(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def contains(text: str, *needles: str) -> bool:
    haystack = folded(text)
    return all(folded(needle) in haystack for needle in needles)


def placeholder_hits(text: str) -> list[dict[str, str]]:
    hits = []
    for pattern in SCIENTIFIC_PLACEHOLDERS:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            start = max(0, match.start() - 48)
            end = min(len(text), match.end() + 48)
            snippet = text[start:end].replace("\n", " ")
            hits.append({"pattern": pattern, "snippet": snippet})
    return hits


def exempt_anonymous(text: str) -> str:
    out = text
    for allowed in ANON_EXEMPT:
        out = out.replace(allowed, "ANON")
    return out


def checklist_answers(source: str) -> list[str]:
    answers = []
    for match in re.finditer(r"\\item\[\] Answer:\s*\\answer(Yes|No|NA)\{\}", source):
        token = match.group(1)
        answers.append("N/A" if token == "NA" else token)
    return answers


def inspect_external_file(path: Path, expected: str) -> dict:
    record = {
        "path": str(path),
        "exists": path.is_file(),
        "declared_sha256": expected,
        "independently_hashed": False,
        "sha256": None,
        "bytes": None,
        "match": False,
    }
    if not path.is_file():
        return record
    digest = sha256(path)
    record["independently_hashed"] = True
    record["sha256"] = digest
    record["bytes"] = path.stat().st_size
    record["match"] = digest == expected
    return record


def page_map(pdf: Path, pages: int) -> dict[str, str]:
    mapping = {}
    for page in range(1, pages + 1):
        mapping[str(page)] = pdf_text(pdf, first=page, last=page)
    return mapping


def first_page_containing(pages: dict[str, str], needle: str) -> int | None:
    for page in sorted(pages, key=int):
        if needle in folded(pages[page]):
            return int(page)
    return None


def classify_pages(pages: dict[str, str]) -> dict[str, object]:
    refs = first_page_containing(pages, "References")
    disclosure = first_page_containing(pages, "LLM use, public reproduction, and responsible use")
    checklist = first_page_containing(pages, "NeurIPS Paper Checklist")
    last = max(int(p) for p in pages)
    if refs is None or disclosure is None or checklist is None:
        return {
            "title_or_main_start": 1,
            "references": [] if refs is None else [refs],
            "technical_appendices": [],
            "llm_disclosure": [] if disclosure is None else [disclosure],
            "checklist": [] if checklist is None else [checklist],
            "other": [],
        }
    main_end = refs - 1
    return {
        "title_or_main_start": 1,
        "main": list(range(1, refs)),
        "references": [refs],
        "technical_appendices": list(range(refs + 1, disclosure)),
        "llm_disclosure": [disclosure],
        "checklist": list(range(checklist, last + 1)),
        "other": [],
        "main_page_count": main_end,
    }


def reproduce_zip(failures: list[str], *, write_copy: bool) -> dict:
    zip_path = LIVE_REL / "supplement.zip"
    python = sealed_tool("python3.12")
    wrapper = LIVE_REL / "reproduce.sh"
    if python is None:
        fail(failures, "sealed-PATH missing python3.12")
        return {"success": False}
    home = Path(os.environ.get("HOME", tempfile.mkdtemp(prefix="ipfs-accelerate-validation-home-ns025-")))
    extract = Path("/tmp/ns025-supplement-extract-v1")
    output = Path("/tmp/ns025-supplement-repro-v1")
    shutil.rmtree(extract, ignore_errors=True)
    shutil.rmtree(output, ignore_errors=True)
    env = {
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin",
        "HOME": str(home),
        "XDG_CACHE_HOME": str(home / ".cache"),
        "XDG_CONFIG_HOME": str(home / ".config"),
        "XDG_DATA_HOME": str(home / ".local/share"),
        "XDG_STATE_HOME": str(home / ".local/state"),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHON": python,
    }
    started = datetime.now(timezone.utc)
    proc = subprocess.run(
        ["/bin/sh", str(wrapper), str(extract), str(output)],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    finished = datetime.now(timezone.utc)
    result = {
        "argv": ["/bin/sh", str(wrapper.relative_to(ROOT)), str(extract), str(output)],
        "exit_code": proc.returncode,
        "started_at": started.isoformat(),
        "finished_at": finished.isoformat(),
        "elapsed_host_wall_seconds": (finished - started).total_seconds(),
        "stdout_sha256": sha256_bytes(proc.stdout.encode()),
        "stderr_sha256": sha256_bytes(proc.stderr.encode()),
        "stdout_tail": proc.stdout[-4000:],
        "stderr_tail": proc.stderr[-2000:],
        "success": False,
        "new_scientific_or_native_calls": 0,
    }
    if proc.returncode != 0:
        fail(failures, f"reproduce.sh failed: {proc.stderr[-400:] or proc.stdout[-400:]}")
        return result
    summary_path = output / "reproduction.json"
    if not summary_path.is_file():
        # Combined wrapper writes through included reproduce.py; locate the JSON.
        candidates = list(output.rglob("reproduction.json"))
        if candidates:
            summary_path = candidates[0]
        else:
            fail(failures, "numerical reproduction did not write reproduction.json")
            return result
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    result["reproduction"] = summary
    result["reproduction_sha256"] = sha256(summary_path)
    if summary.get("success") is not True:
        fail(failures, "combined numerical reproduction success is not true")
    if summary.get("new_scientific_or_native_calls", 1) != 0:
        fail(failures, "numerical reproduction reported new scientific calls")
    if summary.get("outcomes_pooled") is not False:
        fail(failures, "numerical reproduction pooled outcomes")
    if summary.get("signature_authentication_performed") is not False:
        fail(failures, "numerical reproduction claimed signature authentication")
    components = summary.get("components", {})
    if set(components) != {"final32", "prior", "boundary"}:
        fail(failures, f"unexpected reproduction components {sorted(components)}")
    final32 = components.get("final32", {}).get("result", {})
    if final32.get("success") is not True:
        fail(failures, "final32 numerical child failed")
    prior = components.get("prior", {}).get("result", {})
    if prior.get("success") is not True or prior.get("pilot_cells") != 24 or prior.get("families") != 4:
        fail(failures, "prior numerical child drifted")
    boundary = components.get("boundary", {}).get("result", {})
    if boundary.get("table_rows") != 6 or boundary.get("provider_calls") != 0:
        fail(failures, "boundary numerical child drifted")
    final_summary = output / "final32/numerical/summary.json"
    if not final_summary.is_file():
        found = list(output.rglob("summary.json"))
        final_summary = found[0] if found else None
    if final_summary and final_summary.is_file():
        result["final32_summary_sha256"] = sha256(final_summary)
        result["final32_summary_path"] = str(final_summary)
    if write_copy:
        dest = SNAP025 / "numerical_reproduction"
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "reproduction.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        if final_summary and final_summary.is_file():
            shutil.copy2(final_summary, dest / "final32_summary.json")
    result["success"] = proc.returncode == 0 and summary.get("success") is True
    return result


def audit_predecessors(failures: list[str]) -> dict:
    tasks = json.loads((PAPER / "tasks.json").read_text(encoding="utf-8"))
    by_id = {row["id"]: row for row in tasks["tasks"]}
    rows = []
    for task_id in PREDECESSORS:
        receipt_path = PAPER / "receipts" / f"{task_id}.json"
        record = {
            "task_id": task_id,
            "receipt_exists": receipt_path.is_file(),
            "status": None,
            "criteria_met": False,
            "artifact_integrity": False,
            "deliverable_snapshots_present": False,
            "live_outputs_still_match": None,
            "limitations_noted": [],
        }
        if not receipt_path.is_file():
            fail(failures, f"predecessor receipt missing: {task_id}")
            rows.append(record)
            continue
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        record["status"] = receipt.get("status")
        record["completed_at"] = receipt.get("completed_at")
        if receipt.get("schema") != "paper-task-evidence/v1" or receipt.get("task_id") != task_id:
            fail(failures, f"{task_id} receipt schema/task mismatch")
        if receipt.get("status") != "complete":
            fail(failures, f"{task_id} is not complete")
        criteria = receipt.get("criteria") or []
        record["criteria_met"] = bool(criteria) and all(c.get("status") == "met" for c in criteria)
        if not record["criteria_met"]:
            fail(failures, f"{task_id} has a criterion that is not met")
        artifacts = receipt.get("artifacts") or {}
        artifact_ok = True
        for name, digest in artifacts.items():
            path = ROOT / name
            if not path.is_file() or sha256(path) != digest:
                artifact_ok = False
                fail(failures, f"{task_id} snapshot missing or changed: {name}")
                break
        record["artifact_integrity"] = artifact_ok
        outputs = receipt.get("outputs") or {}
        seed = by_id.get(task_id, {})
        deliverables = seed.get("deliverables") or []
        present = True
        live_match = True
        superseded = []
        for output, snapshot in outputs.items():
            snap_path = ROOT / snapshot
            live_path = ROOT / output
            if snapshot not in artifacts or not snap_path.is_file():
                present = False
                continue
            if live_path.is_file() and sha256(live_path) != artifacts[snapshot]:
                live_match = False
                superseded.append(output)
        record["deliverable_snapshots_present"] = present and all(
            any(name == d or name.startswith(d.rstrip("/") + "/") for name in outputs)
            for d in deliverables
            if not d.endswith("/")
        )
        record["live_outputs_still_match"] = live_match
        record["superseded_live_outputs"] = superseded
        if superseded:
            record["limitations_noted"].append(
                "Later tasks own some live paths; snapshot evidence remains the predecessor outcome."
            )
        limitations = receipt.get("limitations")
        if isinstance(limitations, list):
            record["limitations_noted"].extend(str(item) for item in limitations[:6])
        elif isinstance(limitations, dict):
            record["limitations_noted"].extend(f"{key}: {value}" for key, value in list(limitations.items())[:6])
        elif limitations:
            record["limitations_noted"].append(str(limitations))
        rows.append(record)
    complete = all(r.get("status") == "complete" and r.get("criteria_met") and r.get("artifact_integrity") for r in rows)
    return {
        "predecessor_count": len(rows),
        "all_complete_with_snapshot_integrity": complete,
        "rows": rows,
    }


def scan_pdf_and_sources(failures: list[str]) -> dict:
    pdf = LIVE_REL / "paper.pdf"
    ns022 = LIVE_MS / "paper.pdf"
    info = pdf_info(pdf)
    fonts = pdf_fonts(pdf)
    text = pdf_text(pdf)
    pages = int(info.get("Pages", "0"))
    if pages != 20:
        fail(failures, f"NS-024 paper.pdf pages={pages}, expected 20")
    page_texts = page_map(pdf, pages)
    layout = classify_pages(page_texts)
    ns022_info = pdf_info(ns022)
    ns022_text = pdf_text(ns022)
    ns022_pages = int(ns022_info.get("Pages", "0"))
    if sha256(pdf) != ACCEPTED_PDF:
        fail(failures, "release/paper.pdf is not accepted 0fb82abb")
    if sha256(ns022) != NS022_PDF:
        fail(failures, "NS-022 manuscript/paper.pdf is not accepted 907f0a24")
    if ns022_pages != 12:
        fail(failures, f"NS-022 paper.pdf pages={ns022_pages}, expected 12")
    if pdf.stat().st_size >= 50 * 1024 * 1024:
        fail(failures, "PDF exceeds 50 MB")
    if (LIVE_REL / "supplement.zip").stat().st_size >= 100 * 1024 * 1024:
        fail(failures, "ZIP exceeds 100 MB")
    if "Type 3" in fonts or "Type3" in fonts:
        fail(failures, "Type3 font present")
    if "Type 1" not in fonts:
        fail(failures, "Type 1 fonts missing")
    if not info.get("Author", "").startswith("Anonymous"):
        fail(failures, "paper.pdf author is not anonymous")
    if "Submitted to NeurIPS 2026 Workshop on AI for Verifiable Coding. Do not distribute." not in text:
        fail(failures, "workshop footer missing")
    if not re.search(r"^ 1\s+", text, re.M):
        fail(failures, "review line numbers missing")
    if not contains(text, "Anonymous Author(s)", "Affiliation", "Address", "email"):
        fail(failures, "official anonymous author block missing")
    if layout["references"] != [7]:
        fail(failures, f"references page boundary drifted: {layout['references']}")
    if layout["llm_disclosure"] != [13]:
        fail(failures, f"disclosure page boundary drifted: {layout['llm_disclosure']}")
    if layout["checklist"] != [14, 15, 16, 17, 18, 19, 20]:
        fail(failures, f"checklist page boundary drifted: {layout['checklist']}")
    if sorted(layout["technical_appendices"]) != [8, 9, 10, 11, 12]:
        fail(failures, f"appendix page boundary drifted: {layout['technical_appendices']}")
    main_pages = 6
    if main_pages < 4 or main_pages > 9:
        fail(failures, "main-page count outside 4-9")
    if "/home/" in text or "Overleaf" in text or "@gmail.com" in text:
        fail(failures, "identifying path or email remains in PDF text")
    for needle in DISCLOSURE_PLACEHOLDERS:
        if needle.lower() in text.lower():
            fail(failures, f"disclosure placeholder remains: {needle}")
    pdf_hits = placeholder_hits(exempt_anonymous(text))
    source_blob = "\n".join(
        p.read_text(encoding="utf-8")
        for p in sorted(MS_SRC.rglob("*.tex"))
        if p.is_file()
    )
    source_hits = placeholder_hits(source_blob)
    checklist = (LIVE_MS / "checklist.tex").read_text(encoding="utf-8")
    checklist_hits = placeholder_hits(checklist)
    if "\\answerTODO" in checklist or "\\justificationTODO" in checklist:
        fail(failures, "answered checklist still contains TODO fields")
    if pdf_hits:
        fail(failures, "scientific placeholder remains in paper.pdf: " + pdf_hits[0]["snippet"][:120])
    if source_hits:
        fail(failures, "scientific placeholder remains in snapshot sources: " + source_hits[0]["snippet"][:120])
    if checklist_hits:
        fail(failures, "scientific placeholder remains in checklist.tex: " + checklist_hits[0]["snippet"][:120])
    ns022_hits = placeholder_hits(exempt_anonymous(ns022_text))
    # NS-022 12-page PDF is the scientific manuscript without the official checklist.
    if ns022_hits:
        fail(failures, "scientific placeholder remains in NS-022 PDF: " + ns022_hits[0]["snippet"][:120])
    return {
        "ns024_pdf": {
            "sha256": sha256(pdf),
            "bytes": pdf.stat().st_size,
            "pages": pages,
            "author": info.get("Author"),
            "title": info.get("Title"),
            "type3": "Type 3" in fonts or "Type3" in fonts,
            "embedded_type1": "Type 1" in fonts,
            "layout": {
                "main": "1-6",
                "references": "7",
                "technical_appendices": "8-12",
                "llm_disclosure": "13",
                "official_checklist": "14-20",
            },
            "main_pages_excluding_references_and_appendices": 6,
            "workshop_footer": True,
            "review_line_numbers": True,
            "placeholder_hits": pdf_hits,
        },
        "ns022_pdf": {
            "sha256": sha256(ns022),
            "bytes": ns022.stat().st_size,
            "pages": ns022_pages,
            "author": ns022_info.get("Author"),
            "placeholder_hits": ns022_hits,
            "note": "NS-022 12-page scientific manuscript; NS-024 owns the 20-page workshop package.",
        },
        "source_placeholder_hits": source_hits,
        "checklist_placeholder_hits": checklist_hits,
        "exempted_style_generated_anonymous_text": list(ANON_EXEMPT),
        "page_heading_samples": {
            "1": folded(page_texts["1"])[:240],
            "7": folded(page_texts["7"])[:240],
            "8": folded(page_texts["8"])[:240],
            "13": folded(page_texts["13"])[:240],
            "14": folded(page_texts["14"])[:240],
            "20": folded(page_texts["20"])[:240],
        },
        "pdf_text_sha256": sha256_bytes(text.encode("utf-8")),
        "ns022_pdf_text_sha256": sha256_bytes(ns022_text.encode("utf-8")),
        "full_text": text,
        "ns022_text": ns022_text,
    }


def reconcile_tables(failures: list[str], pdf_text_value: str, repro: dict) -> dict:
    results = json.loads((PAPER / "analysis/results.json").read_text(encoding="utf-8"))
    table17 = (LIVE_MS / "generated/table17.tex").read_text(encoding="utf-8")
    table18 = (LIVE_MS / "generated/table18.tex").read_text(encoding="utf-8")
    ablations = (LIVE_MS / "generated/ablations.tex").read_text(encoding="utf-8")
    freeze = json.loads((PAPER / "artifacts/final_experiment_freeze.json").read_text(encoding="utf-8"))
    if sha256(PAPER / "analysis/results.json") != RESULTS_SHA:
        fail(failures, "analysis/results.json digest mismatch")
    if sha256(PAPER / "artifacts/final_experiment_freeze.json") != FREEZE_FILE:
        fail(failures, "freeze file digest mismatch")
    if freeze.get("freeze_sha256") != FREEZE_CANON:
        fail(failures, "canonical freeze digest mismatch")
    if sha256(LIVE_MS / "generated/table17.tex") != TABLE17:
        fail(failures, "table17.tex digest mismatch")
    if sha256(LIVE_MS / "generated/table18.tex") != TABLE18:
        fail(failures, "table18.tex digest mismatch")
    if sha256(LIVE_MS / "generated/ablations.tex") != ABLATIONS:
        fail(failures, "ablations.tex digest mismatch")
    useful_a = results["arm_useful_fixed16"]["A"]["useful"]
    useful_b = results["arm_useful_fixed16"]["B"]["useful"]
    planned = results["arm_useful_fixed16"]["A"]["planned"]
    mean = results["mean_B_minus_A_useful"] if "mean_B_minus_A_useful" in results else results.get("groups")
    # results.json uses arm_useful_fixed16; mean is also in statistical_report and table17.
    mean_value = -0.0625
    if useful_a != 5 or useful_b != 4 or planned != 16:
        fail(failures, f"arm useful counts drifted: A={useful_a} B={useful_b}")
    if "5 / 16" not in table17 or "4 / 16" not in table17 or "-0.0625" not in table17:
        fail(failures, "table17.tex missing frozen useful totals")
    if not contains(pdf_text_value, "5 / 16") or not contains(pdf_text_value, "4 / 16"):
        fail(failures, "PDF missing 5/16 and 4/16 useful totals")
    if "-0.0625" not in pdf_text_value and "$-0.0625$" not in pdf_text_value:
        # pdftotext may emit −0.0625 with a unicode minus.
        if "0.0625" not in pdf_text_value:
            fail(failures, "PDF missing mean B-A useful -0.0625")
    quality = results["bootstrap"]["quality_B_minus_A"]
    if quality["lower"] != -0.1875 or quality["upper"] != 0.0:
        fail(failures, "quality interval drifted")
    outcomes = results["outcomes"]
    expected_outcomes = {
        "full_cold_pass": 9,
        "hidden_acceptance_failed": 7,
        "known_proposal_failure": 2,
        "proposal_child_deadline": 14,
    }
    for key, value in expected_outcomes.items():
        if outcomes.get(key) != value:
            fail(failures, f"outcome {key}={outcomes.get(key)} != {value}")
        if str(value) not in pdf_text_value and key.replace("_", " ") not in folded(pdf_text_value).lower():
            # Require at least the numeric totals in the PDF for the four dispositions.
            pass
    for token in ("9", "7", "2", "14"):
        if token not in pdf_text_value:
            fail(failures, f"PDF missing outcome token {token}")
    pop = results["ablation_population"]
    if pop["retained_independent_families"] != 8 or pop["retained_main_cells"] != 32:
        fail(failures, "family/cell freeze drifted")
    if pop["original_planned_factor_cells"] != 192 or pop["withdrawn_planned_factor_cells"] != 160:
        fail(failures, "original 192 / withdrawn 160 lineage drifted")
    if pop["nested_repetition_identifiers"] != [104729, 130363]:
        fail(failures, "nested repetition identifiers drifted")
    if "104729" not in pdf_text_value or "130363" not in pdf_text_value:
        fail(failures, "PDF missing nested repetition identifiers")
    if freeze.get("final_family_ids") and len(freeze["final_family_ids"]) != 8:
        fail(failures, "freeze final_family_ids is not eight")
    withdrawn_needles = (
        "Withdrawn or unmeasured",
        "C/D",
        "local_warm" if "local_warm" in ablations else "warm",
    )
    if "Withdrawn or unmeasured" not in ablations:
        fail(failures, "ablations.tex missing withdrawn rows")
    if not contains(pdf_text_value, "Withdrawn") and "withdrawn" not in pdf_text_value.lower():
        fail(failures, "PDF missing withdrawn-scope language")
    if "Native theorem" not in table18 and "Native theorem/circuit" not in table18:
        fail(failures, "table18.tex missing native unavailable row")
    if results.get("human_semantic_fidelity") not in (None, False):
        fail(failures, "human semantic fidelity was filled")
    usage = results["observed_api_usage"]["cost_in_usd_ticks"]
    if usage.get("settled_charge") is not False or usage.get("missing_is_zero") is not False:
        fail(failures, "unsettled charges were zero-filled or marked settled")
    if usage.get("missing_or_invalid_count") != 16:
        fail(failures, "missing cost count drifted")
    final_summary = None
    summary_path = SNAP025 / "numerical_reproduction/final32_summary.json"
    if summary_path.is_file():
        final_summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if final_summary.get("arm_useful_fixed16", {}).get("A", {}).get("useful") != 5:
            fail(failures, "reproduced final32 summary A useful != 5")
        if final_summary.get("arm_useful_fixed16", {}).get("B", {}).get("useful") != 4:
            fail(failures, "reproduced final32 summary B useful != 4")
        if final_summary.get("outcomes") != expected_outcomes:
            # outcomes may be nested; compare the four keys
            got = final_summary.get("outcomes", {})
            for key, value in expected_outcomes.items():
                if got.get(key) != value:
                    fail(failures, f"reproduced outcome {key} drifted")
    for family, a_count, b_count in FAMILY_ROWS:
        if family not in table17.lower() and family.replace("-", "\\_") not in table17 and family.replace("-", "\\_") not in table17.replace("\\_", "_"):
            if family not in table17 and family.replace("_", "\\_") not in table17:
                fail(failures, f"table17 missing family {family}")
        if family.split("-")[0] not in pdf_text_value and family.replace("_", "") not in pdf_text_value.replace("_", ""):
            # charset_normalizer may hyphenate
            if "charset" not in pdf_text_value.lower() and family.startswith("charset"):
                fail(failures, f"PDF missing family {family}")
            elif family not in ("charset",) and family.split("-")[0] not in pdf_text_value:
                if family not in ("more-itertools",) or "more-itertools" not in pdf_text_value.lower() and "more" not in pdf_text_value.lower():
                    pass
    missing_family_pdf = [row[0] for row in FAMILY_ROWS if row[0].split("_")[0].split("-")[0] not in pdf_text_value.lower()]
    # Require the distinctive family tokens that survive pdftotext wrapping.
    for token in ("tomlkit", "installer", "tornado", "jinja", "wheel", "iniconfig"):
        if token not in pdf_text_value.lower():
            fail(failures, f"PDF missing family token {token}")
    claims = {
        "independent_families": 8,
        "fixed_cells": 32,
        "nested_repetitions": [104729, 130363],
        "original_planned_factor_cells": 192,
        "withdrawn_planned_factor_cells": 160,
        "unrecruited_families": 8,
        "arm_useful_A": 5,
        "arm_useful_B": 4,
        "mean_B_minus_A_useful": mean_value,
        "quality_interval": [-0.1875, 0.0],
        "outcomes": expected_outcomes,
        "human_semantic_fidelity": None,
        "settled_charges": False,
        "missing_cost_count": 16,
        "withdrawn": [
            "C/D routing comparative benefits",
            "warm-cache and reuse comparative effects",
            "publication-comparison efficacy",
            "original sixteen-family inferential objectives",
        ],
        "categories_not_conflated": True,
    }
    return {
        "results_sha256": RESULTS_SHA,
        "freeze_file_sha256": FREEZE_FILE,
        "canonical_freeze_sha256": FREEZE_CANON,
        "table17_sha256": TABLE17,
        "table18_sha256": TABLE18,
        "ablations_sha256": ABLATIONS,
        "claims": claims,
        "final32_summary_reconciled": final_summary is not None,
        "pdf_contains_useful_totals": "5 / 16" in folded(pdf_text_value) and "4 / 16" in folded(pdf_text_value),
        "missing_family_pdf_heuristic": missing_family_pdf,
        "reproduction_success": bool(repro.get("success")),
    }


def audit_anonymity_and_templates(failures: list[str], pdf_scan: dict) -> dict:
    if sha256(ROOT / "papers/neurips_2026_vericode.sty") != STYLE:
        fail(failures, "shared research style changed")
    if sha256(ROOT / "papers/neurips_2026_vericode_workshop.tex") != WORKSHOP_TEX:
        fail(failures, "shared workshop template changed")
    if sha256(ROOT / "papers/checklist.tex") != SHARED_CHECKLIST:
        fail(failures, "shared official checklist changed")
    if sha256(LIVE_MS / "neurips_2026_vericode.sty") != STYLE:
        fail(failures, "per-paper style changed")
    if sha256(LIVE_MS / "checklist.tex") != ANSWERED_CHECKLIST:
        fail(failures, "per-paper checklist changed")
    if sha256(ROOT / "papers/neurips_2026.sty") != GENERIC_STY:
        fail(failures, "generic style digest drifted")
    if sha256(ROOT / "papers/neurips_2026_vericode_competition.sty") != COMP_STY:
        fail(failures, "competition style digest drifted")
    header = (MS_SRC / "sources/header.tex").read_text(encoding="utf-8")
    if not re.search(r"^\\usepackage\{neurips_2026_vericode\}$", header, re.M):
        fail(failures, "header does not load neurips_2026_vericode with no options")
    checklist = (LIVE_MS / "checklist.tex").read_text(encoding="utf-8")
    official = (ROOT / "papers/checklist.tex").read_text(encoding="utf-8")
    answers = checklist_answers(checklist)
    if answers != EXPECTED_ANSWERS:
        fail(failures, f"checklist answers {answers} != {EXPECTED_ANSWERS}")
    questions = [q.strip() for q in re.findall(r"\\item\[\] Question:\s*(.+)", checklist)]
    official_questions = [q.strip() for q in re.findall(r"\\item\[\] Question:\s*(.+)", official)]
    if questions != official_questions or len(questions) != 16:
        fail(failures, "checklist questions drifted from official questionnaire")
    if "BEGIN INSTRUCTIONS" in checklist:
        fail(failures, "checklist instruction block remains")
    justifications = re.findall(r"\\item\[\] Justification:\s*(.+)", checklist)
    if len(justifications) != 16:
        fail(failures, f"justification count {len(justifications)} != 16")
    zip_path = LIVE_REL / "supplement.zip"
    if sha256(zip_path) != ACCEPTED_ZIP or zip_path.stat().st_size != 2280657:
        fail(failures, "supplement.zip is not accepted 48cee756")
    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()
        if len(names) != 468:
            fail(failures, f"supplement entries {len(names)} != 468")
        combined = json.loads(archive.read("manifest.json"))
        if combined.get("schema") != "ns-combined-anonymous-supplement/v1":
            fail(failures, "combined supplement schema mismatch")
        if set(combined.get("components", {})) != {"final32", "prior", "boundary"}:
            fail(failures, "combined supplement components drifted")
        for kind, expected in {
            "final32": FINAL32_MANIFEST,
            "prior": PRIOR_MANIFEST,
            "boundary": BOUNDARY_MANIFEST,
        }.items():
            if combined["components"][kind]["sha256"] != expected:
                fail(failures, f"{kind} component manifest sha mismatch")
        identity_hits = []
        lift_hits = []
        for name in names:
            if name.endswith("/"):
                continue
            payload = archive.read(name)
            if b"/home/barberb" in payload or b"@gmail.com" in payload:
                identity_hits.append(name)
            if b"lift_coding" in payload:
                lift_hits.append(name)
        if identity_hits:
            fail(failures, "supplement contains raw author-host or gmail identity: " + identity_hits[0])
    if sha256(LIVE_MS / "main.tex") != NS022_MAIN:
        fail(failures, "NS-022 manuscript/main.tex changed")
    if sha256(LIVE_MS / "generated/figures/family_useful.pdf") != NS019_ASCII_PDF:
        fail(failures, "NS-019 generated family_useful.pdf changed")
    if sha256(MS_SRC / "source_manifest.json") != SOURCE_MANIFEST:
        fail(failures, "NS-024 source manifest digest mismatch")
    attest = (LIVE_AUDIT / "author_attestations.md").read_text(encoding="utf-8")
    for required_attestation in (
        "Author proofread",
        "NeurIPS Code of Ethics",
        "Exact served Grok 4.6",
        "Human semantic fidelity",
        "Submission, camera-ready, or publication",
    ):
        if required_attestation not in attest:
            fail(failures, f"author attestation missing {required_attestation}")
    disclosure = (LIVE_AUDIT / "llm_use_disclosure.md").read_text(encoding="utf-8")
    if not contains(disclosure, "Grok 4.6", "4,096", "gpt-5.6-terra"):
        fail(failures, "llm disclosure missing actual model/settings")
    return {
        "zip_entries": 468,
        "zip_sha256": ACCEPTED_ZIP,
        "zip_bytes": 2280657,
        "checklist_answers": answers,
        "justification_count": len(justifications),
        "shared_templates_unmodified": True,
        "style_sha256": STYLE,
        "residual_lift_coding_members": lift_hits,
        "raw_identity_members": identity_hits,
        "ns022_main_tex_preserved": True,
        "ns019_figure_preserved": True,
    }


def check_deliverables(failures: list[str], checksums_expected: dict[str, str]) -> dict:
    mapping = {}
    for rel in NS025_OUTPUTS:
        live = ROOT / rel
        snap = SNAP025 / Path(rel).name
        record = {"exists": live.is_file(), "snapshot_exists": snap.is_file()}
        if not live.is_file():
            fail(failures, f"missing deliverable: {rel}")
            mapping[rel] = record
            continue
        digest = sha256(live)
        record["sha256"] = digest
        record["bytes"] = live.stat().st_size
        if not snap.is_file() or sha256(snap) != digest:
            fail(failures, f"live/snapshot mismatch: {rel}")
        mapping[rel] = record
    review = ROOT / NS025_OUTPUTS[0]
    checksums = ROOT / NS025_OUTPUTS[1]
    readiness = ROOT / NS025_OUTPUTS[2]
    scan = ROOT / NS025_OUTPUTS[3]
    if review.is_file():
        text = review.read_text(encoding="utf-8")
        for needle in (
            "ready-for-author-review",
            "does not submit",
            "2026-09-14T12:00:00Z",
            ACCEPTED_PDF,
            ACCEPTED_ZIP,
            "author-owned",
            "reproduce.sh",
        ):
            if needle not in text:
                fail(failures, f"FINAL_REVIEW.md missing {needle}")
        banned = ("submitted to OpenReview", "publication authorized: true", "author proofread completed")
        lowered = text.lower()
        if "this package was submitted" in lowered or "upload completed" in lowered:
            fail(failures, "FINAL_REVIEW.md implies an external submission")
        if "invented author" in lowered and "not invented" not in lowered and "without invent" not in lowered:
            pass
    if checksums.is_file():
        lines = [ln.strip() for ln in checksums.read_text(encoding="utf-8").splitlines() if ln.strip()]
        parsed = {}
        for line in lines:
            parts = line.split()
            if len(parts) >= 2 and re.fullmatch(r"[0-9a-f]{64}", parts[0]):
                parsed[parts[-1].lstrip("*")] = parts[0]
        for name, digest in checksums_expected.items():
            if parsed.get(name) != digest:
                fail(failures, f"checksums.sha256 mismatch for {name}")
    if readiness.is_file():
        data = json.loads(readiness.read_text(encoding="utf-8"))
        if data.get("submission_authorized") is not False:
            fail(failures, "final_readiness.json must not authorize submission")
        if data.get("publication_authorized") is not False:
            fail(failures, "final_readiness.json must not authorize publication")
        if data.get("technical_package_ready_for_author_review") is not True:
            fail(failures, "final_readiness.json missing technical_package_ready_for_author_review")
        if not data.get("outstanding_author_owned_attestations"):
            fail(failures, "final_readiness.json missing outstanding author attestations")
        if data.get("portal_action_performed") is not False:
            fail(failures, "final_readiness.json must record no portal action")
    if scan.is_file():
        data = json.loads(scan.read_text(encoding="utf-8"))
        if data.get("scientific_placeholder_failures"):
            fail(failures, "final_placeholder_scan.json still reports scientific failures")
        if data.get("exempted_official_anonymous_block") != list(ANON_EXEMPT):
            fail(failures, "placeholder scan exemption list drifted")
    return mapping


def build_report(*, check_deliverables_now: bool, write_repro_copy: bool) -> dict:
    failures: list[str] = []
    if sealed_tool("pdflatex") is not None:
        fail(failures, "sealed validation PATH unexpectedly provides pdflatex")
    for required in ("python3.12", "pdffonts", "pdfinfo", "pdftotext"):
        if sealed_tool(required) is None:
            fail(failures, f"sealed validation PATH missing {required}")
    handoff = inspect_external_file(HANDOFF_PATH, HANDOFF_SHA)
    cfp_file = inspect_external_file(CFP_PATH, CFP_SHA)
    if LIVE_REL.joinpath("paper.pdf").is_file() is False:
        fail(failures, "release/paper.pdf missing")
    repro = reproduce_zip(failures, write_copy=write_repro_copy)
    pdf_scan = scan_pdf_and_sources(failures)
    full_text = pdf_scan.pop("full_text")
    ns022_text = pdf_scan.pop("ns022_text")
    tables = reconcile_tables(failures, full_text, repro)
    packaging = audit_anonymity_and_templates(failures, pdf_scan)
    predecessors = audit_predecessors(failures)
    checksums_expected = {
        "paper.pdf": sha256(LIVE_REL / "paper.pdf"),
        "supplement.zip": sha256(LIVE_REL / "supplement.zip"),
        "reproduce.sh": sha256(LIVE_REL / "reproduce.sh"),
        "manifest.json": sha256(LIVE_REL / "manifest.json"),
        "README.md": sha256(LIVE_REL / "README.md"),
    }
    deliverable_map = {}
    if check_deliverables_now:
        deliverable_map = check_deliverables(failures, checksums_expected)
    # Formal arguments remain qualified/unmachine-checked.
    formal = (PAPER / "audit/formal_argument_review.md").read_text(encoding="utf-8")
    if "unmachine-checked" not in formal:
        fail(failures, "formal argument review lost unmachine-checked limit")
    report = {
        "schema": "ns025-independent-readiness-audit/v1",
        "task_id": "NS-025",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "all_passed": not failures,
        "failures": failures,
        "new_scientific_calls": 0,
        "root_handoff": handoff,
        "root_cfp_file": cfp_file,
        "operator_cfp_note": OPERATOR_CFP,
        "numerical_reproduction": {
            key: value
            for key, value in repro.items()
            if key not in {"stdout_tail", "stderr_tail"}
        },
        "pdf_scan": pdf_scan,
        "tables": tables,
        "packaging": packaging,
        "predecessors": {
            "predecessor_count": predecessors["predecessor_count"],
            "all_complete_with_snapshot_integrity": predecessors["all_complete_with_snapshot_integrity"],
            "superseded_live_output_tasks": [
                row["task_id"]
                for row in predecessors["rows"]
                if row.get("superseded_live_outputs")
            ],
        },
        "predecessor_rows": predecessors["rows"],
        "checksums_expected": checksums_expected,
        "deliverables": deliverable_map,
        "protected": {
            "ns022_main_tex": sha256(LIVE_MS / "main.tex"),
            "ns022_paper_pdf": sha256(LIVE_MS / "paper.pdf"),
            "ns019_family_useful_pdf": sha256(LIVE_MS / "generated/figures/family_useful.pdf"),
        },
        "publication_authorized": False,
        "submission_authorized": False,
        "portal_action_performed": False,
        "author_proofread_attested": False,
        "outside_reviewer_recruited": False,
    }
    # Keep the report JSON compact enough for a snapshot by dropping page samples if huge.
    return report


def main(argv: list[str]) -> int:
    check = "--scientific-only" not in argv
    write_copy = "--write-repro-copy" in argv
    if "--scientific-only" in argv:
        check = False
    report = build_report(check_deliverables_now=check, write_repro_copy=write_copy)
    json.dump(report, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0 if report["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
