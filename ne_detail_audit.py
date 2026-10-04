import hashlib
import json
import sys
import time
from collections import Counter
from pathlib import Path

SOURCE = Path("/home/barberb/portland-laws.github.io/workspace/codex-work/legal-corpora-reindex-mi-xml-validator-20260828/ipfs_datasets_py")
EVIDENCE = Path("/home/barberb/.ipfs_datasets/state_laws/legal-corpora-reindex-20260828-final-ne-evidence-VaxtrF/NE")
MIGRATION = EVIDENCE / "migrations/e903f4e594f713bd16c2edb3096eb640ef2e69fe6ef7b1826fd1c2b65afeee50.json"
sys.path.insert(0, str(SOURCE))

from ipfs_datasets_py.processors.legal_scrapers.state_scrapers.nebraska import (
    _source_bound_terminal_sections_from_chapter_catalog_html,
)
from ipfs_datasets_py.processors.legal_scrapers.state_scrapers.nebraska_section import (
    chapter_links,
    classify_nebraska_terminal_section_html,
    parse_nebraska_section_html,
    section_links,
)

seed = json.loads(MIGRATION.read_text())
projection = seed["selected_projection"]
by_url = {row["official_url"]: row for row in projection}

def raw_body(url):
    row = by_url[url]
    raw = (EVIDENCE / "objects" / f"{row['content_sha256']}.bin").read_bytes()
    observed = hashlib.sha256(raw).hexdigest()
    if observed != row["content_sha256"]:
        raise RuntimeError(f"digest mismatch: {url}")
    return raw

root_url = "https://nebraskalegislature.gov/laws/browse-statutes.php"
chapters = chapter_links(raw_body(root_url).decode("utf-8", errors="replace"), base_url=root_url)
units = []
catalog_terminal = {}
for chapter_number, chapter_name, chapter_url in chapters:
    html = raw_body(chapter_url).decode("utf-8", errors="replace")
    terminals = _source_bound_terminal_sections_from_chapter_catalog_html(
        html, source_url=chapter_url
    )
    for section_number, section_name, source_url in section_links(html, base_url=chapter_url):
        units.append((chapter_number, section_number, section_name, source_url))
        if source_url in terminals:
            catalog_terminal[source_url] = terminals[source_url]

counts = Counter()
terminal_counts = Counter()
identity_mismatch = []
unclassified = []
operative_examples = []
started = time.monotonic()
for index, (_chapter, expected_number, _name, url) in enumerate(units, start=1):
    if url in catalog_terminal:
        counts["catalog_terminal"] += 1
        continue
    html = raw_body(url).decode("utf-8", errors="replace")
    terminal = classify_nebraska_terminal_section_html(html, source_url=url)
    parsed = parse_nebraska_section_html(
        html,
        source_url=url,
        code_name="Nebraska Revised Statutes",
    )
    if parsed is not None:
        counts["operative"] += 1
        if str(parsed.section_number or "").strip() != expected_number:
            identity_mismatch.append({
                "url": url,
                "expected": expected_number,
                "observed": str(parsed.section_number or "").strip(),
            })
        if len(operative_examples) < 3:
            operative_examples.append({
                "url": url,
                "number": parsed.section_number,
                "text_sha256": hashlib.sha256(parsed.full_text.encode("utf-8")).hexdigest(),
            })
    elif terminal:
        counts["detail_terminal"] += 1
        terminal_counts[terminal] += 1
    else:
        counts["unclassified"] += 1
        if len(unclassified) < 100:
            unclassified.append(url)

result = {
    "elapsed_seconds": round(time.monotonic() - started, 3),
    "catalog_input_count": 1 + len(chapters),
    "chapter_count": len(chapters),
    "leaf_input_count": len(units),
    "leaf_url_unique_count": len({row[3] for row in units}),
    "counts": dict(counts),
    "catalog_terminal_dispositions": dict(Counter(
        row["disposition"] for row in catalog_terminal.values()
    )),
    "detail_terminal_dispositions": dict(terminal_counts),
    "excluded_total": counts["catalog_terminal"] + counts["detail_terminal"],
    "fetched_total": counts["operative"],
    "identity_mismatch_count": len(identity_mismatch),
    "identity_mismatch_sample": identity_mismatch[:10],
    "unclassified_sample": unclassified[:20],
    "operative_examples": operative_examples,
}
print(json.dumps(result, sort_keys=True))
