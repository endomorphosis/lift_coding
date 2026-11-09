# Municipal and pipeline schema register

Register for the 19-column municipal HTML rows and for pipeline `DOC_TYPES` labels. An adapter keeps both schemas. This file does not edit `world_municipal/schema.py` or pipeline schema code, and it does not reorder the 19 columns.

Read on 2026-11-09 from the training checkout `external/ipfs_datasets`. `git rev-parse HEAD` is `d40ab60649b83781e3849e191c1f2ac8545b042f`. `git status --short` printed no lines for the files quoted below.

`world_municipal/schema.py` last changed in `4cdca488f0bd997e8f7a90438aa90a859cb85c5b`. `hub_integrated/world_law_pipeline/schema.py` last changed in `d40ab60649b83781e3849e191c1f2ac8545b042f`. `SCHEMA.md`, `card.py`, `scrapers/afme/afme_sources.md`, and `scrapers/states/at_ris.py` last changed in `4cdca488f0bd997e8f7a90438aa90a859cb85c5b`.

## Nineteen municipal columns

`ipfs_datasets_py/processors/legal_scrapers/world_municipal/schema.py` defines `EXPECTED_COLUMNS` in this order:

```python
EXPECTED_COLUMNS: List[str] = [
    "cid",
    "jurisdiction_id",
    "jurisdiction_name",
    "country",
    "doc_id",
    "regeling_id",
    "regeling_work_id",
    "doc_order",
    "title",
    "structural_path",
    "node_label",
    "html_title",
    "html",
    "text",
    "source_url",
    "xml_url",
    "date_effective",
    "date_modified",
    "retrieved",
]
```

Those 19 names, in that order, are `cid`, `jurisdiction_id`, `jurisdiction_name`, `country`, `doc_id`, `regeling_id`, `regeling_work_id`, `doc_order`, `title`, `structural_path`, `node_label`, `html_title`, `html`, `text`, `source_url`, `xml_url`, `date_effective`, `date_modified`, `retrieved`.

`PLAN.md` lists the same 19 names in the same order. That line still matches.

## Append-only extra-column rule

The module docstring states the extension rule:

```python
Country-specific provenance columns follow the sanctioned extension pattern:
they are appended AFTER column 19, never reordered or interleaved
(e.g. Portugal full harvest appends ``tipo`` as column 20).
```

`build_schema` appends `extra_columns` after those 19 and raises if an extra name collides with a canonical name. `validate_table` gate 1 is `exact canonical column order (extras allowed only after column 19)`. An adapter accepts a trailing provenance column and rejects a column inserted into the 19 or placed ahead of them.

`doc_order` stays the only non-string column. The docstring says:

```python
- ``doc_order`` is the only non-string column (uint32), 0-based and strictly
  sequential within a jurisdiction file;
```

`_UINT32 = pa.uint32()`. `build_schema` uses that type only for `doc_order`. `validate_table` rejects a non-sequential column with `doc_order is not strictly sequential 0..n-1`. `rows_to_table` builds `pa.array(orders, type=pa.uint32())` at `EXPECTED_COLUMNS.index("doc_order")`.

Missing string values serialize as `""`. The docstring says writers serialize missing values as `""` and that NULLs are a validation failure. `validate_table` reports `NULL values (serialize missing as "")`. `rows_to_table` writes `"" if v is None else str(v)`. A NULL in a string column fails validation.

## Pipeline `1.2.0`

`ipfs_datasets_py/processors/legal_scrapers/hub_integrated/world_law_pipeline/schema.py`:

```python
SCHEMA_VERSION = "1.2.0"  # 1.1.0: optional provenance columns + extra_metadata (appended); 1.2.0: pdf_ref (appended)
PDF_REPO_ID = "endomorphosis/world_law_scanned_pdfs"  # raw image-only scanned PDFs awaiting OCR
REPO_ID = "endomorphosis/world_municipal_law"
NATIONAL_REPO_ID = "endomorphosis/world_national_law"   # national + subnational (iso:* places), split 2026-10-11
NATIONAL_LEVELS = ("country", "adm1", "supranational")


def is_national_key(pkey: str) -> bool:
    """iso:* places (country / first-level subdivision / supranational, SCHEMA.md §3) live in NATIONAL_REPO_ID;
    everything else (municipal, county, water board, ...) in REPO_ID."""
    return str(pkey).startswith("iso_")
```

`1.1.0` appended optional provenance columns and `extra_metadata`. `1.2.0` appended `pdf_ref`. `HTML_COLUMNS = V11_HTML_COLUMNS + PDF_COLUMNS` with `PDF_COLUMNS = ["pdf_ref"]`. Those appended pipeline columns stay after the earlier columns. They are not a substitute for the municipal 19, and they are not inserted into `EXPECTED_COLUMNS`.

`is_national_key` is true only when the place key starts with `iso_`. `place_key` documents `iso:US-CA -> iso_US-CA` and returns `pid.replace(":", "_")`. The docstring says `iso:*`. The predicate that runs is `startswith("iso_")`. Municipal, county, and water-board keys stay in `REPO_ID` `endomorphosis/world_municipal_law`. `iso_` keys stay in `NATIONAL_REPO_ID` `endomorphosis/world_national_law`.

`PLAN.md` names `SCHEMA_VERSION` `1.2.0`, the append note, both repo ids, and `is_national_key` true when the place key starts with `iso_`. Those lines still match.

## `DOC_TYPES` as source labels

```python
DOC_TYPES = ("code_section", "ordinance", "regulation", "statute", "gazette_act", "decision")
```

`SCHEMA.md` lists the same six names for `doc_type`. `card.py` repeats `doc_type` ∈ `code_section | ordinance | regulation | statute | gazette_act | decision`.

`validate_record` checks membership and does not relabel the value:

```python
dt = rec.get("doc_type")
if dt and dt not in DOC_TYPES:
    errs.append(f"bad_doc_type:{dt!r}")
```

An adapter stores the source `DOC_TYPES` string on the row. The kind below is a classification beside that string. `schema.py` does not contain the word caselaw.

## Label classification

| Source label | Kind |
| --- | --- |
| `code_section` | law |
| `ordinance` | law |
| `regulation` | regulation |
| `statute` | law |
| `gazette_act` | act |
| `decision` | not yet classified |

`code_section` and `statute` are law. `scrapers/states/at_ris.py` describes the same Landesrecht source as `whole consolidated Land law, doc_type statute` and `single provision, doc_type code_section`. A single provision keeps the law kind. `PLAN.md` keeps US Code consolidation on the law kind.

`ordinance` is law. `scrapers/afme/afme_sources.md` says `doc_type: ordinance (local law/by-law), regulation (subordinate/policy)`.

`regulation` is regulation. The enum value is the word `regulation`, and the same afme sentence calls that label subordinate/policy. The schema does not rename it to a statute id.

`gazette_act` is act. `PLAN.md` says legislative acts are instruments such as a gazette act or a public law before consolidation. `SCHEMA.md` says `consolidated` is `false` for gazette/as-published acts. `card.py` says `consolidated=false` marks as-published gazette acts. The stored label remains `gazette_act`. A later per-dataset check still has to run before an adapter claims a particular row.

`decision` is not yet classified. `validate_record` leaves the label as stored. `schema.py` does not map it to another kind. LCM-003 inventories `caselaw_access_program`, France DILA, Rechtsprechung im Internet, `recap_archive_scraper`, and `endomorphosis/world_caselaw`. That inventory does not cite pipeline `DOC_TYPES` `decision` as one of those contracts. `PLAN.md` says `decision` is not caselaw unless the source register says so for that dataset. This register does not say so. The label stays `not yet classified`, and the row keeps the source string `decision`.
