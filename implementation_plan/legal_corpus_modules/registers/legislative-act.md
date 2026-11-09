# Legislative-act schema register

Register for act-shaped sources. A legislative act here is a gazette act or a public law before consolidation. US Code consolidation is excluded. This file does not add a method to `query.py`, does not open a national query route, and does not edit the datasets checkout.

Read on 2026-11-09 from the training checkout `external/ipfs_datasets`. `git rev-parse HEAD` is `d40ab60649b83781e3849e191c1f2ac8545b042f`. `git status --short` printed no lines for the files quoted below. Copies under `international/harvested` and under `hub_integrated` other than `world_law_pipeline/schema.py` and `world_law_pipeline/SCHEMA.md` are not this register's contract.

## Public law before consolidation

`ipfs_datasets_py/processors/legal_scrapers/federal_scrapers/public_law_change_processor.py` last changed in `ca0dc4b8e707b3f3f19511606bfbb053b93f93ee`. A GovInfo Public Law package is the official change. A House OLRC / `uscode.house.gov` view is a cross-check and cannot replace that package. The module docstring says:

```text
* House OLRC codification views and eCFR/FederalRegister.gov material may
  appear only as **cross-check** (``unofficial-current`` /
  ``derived_presentation``); they never replace the official GovInfo Public
  Law artifact.
* Official Public Law packages carry ``authority_tier=official-change`` with
  ``IdentityRole.OFFICIAL_ARTIFACT``.
```

```python
SCHEMA_VERSION = "public-law-change-processor-v1"
FIXTURE_SCHEMA_VERSION = "public-law-change-fixture-v1"
```

```python
CROSS_CHECK_PROVIDERS = frozenset(
    {
        "ushouse",
        "uscode.house.gov",
        "house",
        "ecfr",
        "www.ecfr.gov",
        "federalregister.gov",
        "www.federalregister.gov",
        "fr.gov",
    }
)
```

```python
class CrossCheckRole(str, Enum):
    """How a non-GovInfo view is used relative to the official Public Law."""

    NONE = "none"
    HOUSE_CODIFICATION = "house_codification"
    ECFR_PRESENTATION = "ecfr_presentation"
    FEDERAL_REGISTER_DISCOVERY = "federal_register_discovery"
    OTHER = "other"
```

`stable_public_law_identity` returns `plaw:us:{congress}:{law_number}` after `normalize_congress` and `normalize_law_number`. `PublicLawRecord.authority_tier` returns `AuthorityTier.OFFICIAL_CHANGE`. `PublicLawRecord.to_dict` writes these keys, in source order: `affects_titles`, `authority_tier`, `citation`, `congress`, `content_sha256`, `cross_checks`, `date_approved`, `date_enacted`, `formats`, `law_number`, `metadata`, `notes`, `official_artifact`, `package_id`, `patent_relevant`, `receipt`, `retrieved_at`, `source_spans`, `source_url`, `stable_id`, `status`, `subjects`, `text_excerpt`, `title`, `verification_state`.

`assert_cross_check_only` fails closed when a cross-check provider is labeled as official. Its docstring is `Fail closed when a cross-check provider is labeled as official.` A provider in `CROSS_CHECK_PROVIDERS`, including `uscode.house.gov`, is a cross-check. The authority note on the record says `Official GovInfo Public Law package; House/eCFR/FR.gov views remain cross-check-only when present.` The metadata stores `authority_schema` from the imported patent-authority schema and `processor_schema` from this module's `SCHEMA_VERSION`. Those are two different strings.

A fixture in the same processor records the House view as cross-check only:

```python
"provider": "ushouse",
"role": "house_codification",
"notes": "House OLRC codification view; cross-check only.",
```

`ipfs_datasets_py/processors/legal_data/patent_authority_sources.py` last changed in `8dc497d9232c5b332e7633339f736c417d56a280`:

```python
SCHEMA_VERSION = "patent-authority-sources-v1"
```

The processor imports that name as `AUTHORITY_SCHEMA_VERSION`. It is not `public-law-change-processor-v1` and it is not a US Code release schema.

## `gazette_act` still needs a per-dataset check

`ipfs_datasets_py/processors/legal_scrapers/hub_integrated/world_law_pipeline/schema.py` last changed in `d40ab60649b83781e3849e191c1f2ac8545b042f`. `gazette_act` is one pipeline `DOC_TYPES` value. It sits beside `code_section` and `statute`. It is not a US Code section record and it is not `public-law-change-processor-v1`.

```python
SCHEMA_VERSION = "1.2.0"  # 1.1.0: optional provenance columns + extra_metadata (appended); 1.2.0: pdf_ref (appended)
```

```python
DOC_TYPES = ("code_section", "ordinance", "regulation", "statute", "gazette_act", "decision")
```

`validate_record` checks membership and does not name a dataset:

```python
dt = rec.get("doc_type")
if dt and dt not in DOC_TYPES:
    errs.append(f"bad_doc_type:{dt!r}")
```

`ipfs_datasets_py/processors/legal_scrapers/hub_integrated/world_law_pipeline/SCHEMA.md` last changed in `4cdca488f0bd997e8f7a90438aa90a859cb85c5b`. Its `doc_type` row lists the same six names, including `gazette_act`. Its `consolidated` row says `` `false` for gazette/as-published acts ``. That note is a column description. It is not a list of datasets, and `validate_record` does not turn the label into an adapter claim.

An adapter must not claim a row because `doc_type` is `gazette_act`. The label still needs a per-dataset check against the module that wrote the row. The only `national_collectors` modules that assign `document_type="gazette_act"` are the four below. None of them is `us_code_scraper.py`. The public-law processor does not set `gazette_act`. The other act collectors in the next section do not set `gazette_act`. Harvested copies of these four files are not this contract.

| File | Last change | Module `SOURCE_TYPE` | Catalog `source_type` | What the module fetches |
| --- | --- | --- | --- | --- |
| `national_collectors/collect_si.py` | `d40ab60649b83781e3849e191c1f2ac8545b042f` | `uradni_list` | empty string | Slovenia: Uradni list RS official issue TOCs and act HTML. The module says the PISRS developer API is token-gated and is not used. |
| `national_collectors/collect_gr.py` | `b560f8d60962277b09c12c44457b424de25de83b` | `et_gr` | empty string | Greece: official National Printing House search.et.gr Azure API and FEK Α' PDFs. |
| `national_collectors/collect_bg.py` | `d40ab60649b83781e3849e191c1f2ac8545b042f` | `dv_parliament` | empty string | Bulgaria: State Gazette via Wayback of official URLs. The module says live TLS fails. |
| `national_collectors/ocr_gr_image_only.py` | `b560f8d60962277b09c12c44457b424de25de83b` | `et_gr` | not a catalog filename | Greece: OCR of remaining image-only FEK A PDFs. |

`catalog.py` lists `collect_si.py`, `collect_gr.py`, and `collect_bg.py`. Each of those rows has `source_type` `''` even though the module sets `SOURCE_TYPE`. An adapter must not invent a catalog `source_type` for those three rows. `ocr_gr_image_only.py` is not a catalog filename. `catalog.py` last changed in `d40ab60649b83781e3849e191c1f2ac8545b042f`.

## Act collectors that do not open a query route

`ipfs_datasets_py/processors/legal_scrapers/national_collectors/catalog.py` last changed in `d40ab60649b83781e3849e191c1f2ac8545b042f`. The module docstring is the catalog-wide limit:

```text
"""Catalog of official national gazette collectors vendored from Hugging Face.
...
Collectors target official gazettes and official open-data portals only.
Query-time walks and live official current-bundle closes are out of scope.
```

`ipfs_datasets_py/processors/legal_scrapers/country_laws_ir/query.py` last changed in the same revision. It does not import `national_collectors`. Its imports from this package are `duckdb_store` names: `bm25_search`, `document_shard_paths`, `graph_neighbors`, `adjacency_shard_paths`, and `cite_search`. The release methods are `bm25`, `vector`, `neighbors`, and `cite`. Document lookup calls `document_shard_paths` and, when that returns `None`, reads `data/bm25/documents`. Neighbor lookup calls `adjacency_shard_paths` and, when that returns `None`, reads `data/graph/adjacency/<direction>/*.parquet`. No act, gazette, or public-law method was added. This register does not add one.

The collectors below fetch acts or public laws, except `collect_jo_gazette.py`. They are harvest modules. They do not add a method to `query.py`. Where a catalog row exists and the module defines `SOURCE_TYPE`, that catalog `source_type` matches the module constant.

`collect_jo_gazette.py` last changed in `d40ab60649b83781e3849e191c1f2ac8545b042f`. Its module docstring says `Jordan Official Gazette collector. Importing this module does not run it.` The file defines no `SOURCE_TYPE`. It returns a vendored path and does not fetch. This register does not use that vendored copy as the contract. The catalog row says `Jordan Official Gazette instruments. Does not open a new query route by itself.` Catalog `source_type` is `jordan_official_gazette`. That catalog string is not a module constant.

| File | Last change | `SOURCE_TYPE` | What the module fetches |
| --- | --- | --- | --- |
| `national_collectors/collect_gm.py` | `0b9e4f0903c2aaa36e998a354afa01b36d149d76` | `gambia_official_gazette_acts` | Gambia official Acts and gazette PDFs via `*.gov.gm` |
| `national_collectors/collect_lr.py` | `0b9e4f0903c2aaa36e998a354afa01b36d149d76` | `liberia_official_gazette_acts` | Liberia official Acts and gazette PDFs via `*.gov.lr` |
| `national_collectors/collect_ls.py` | `0b9e4f0903c2aaa36e998a354afa01b36d149d76` | `lesotho_official_gazette_acts` | Lesotho official Acts, Bills, SI, Gazette, and Constitution PDFs |
| `national_collectors/collect_sc.py` | `0b9e4f0903c2aaa36e998a354afa01b36d149d76` | `seychelles_official_gazette_acts` | Seychelles official Acts, Bills, SI, Gazette, and Constitution PDFs |
| `national_collectors/collect_sl.py` | `0b9e4f0903c2aaa36e998a354afa01b36d149d76` | `sierra_leone_official_gazette_acts` | Sierra Leone official Acts and gazette PDFs via `*.gov.sl` |
| `national_collectors/collect_sz.py` | `0b9e4f0903c2aaa36e998a354afa01b36d149d76` | `eswatini_official_gazette_acts` | Eswatini official Acts, Bills, SI, Gazette, and Constitution PDFs |
| `national_collectors/collect_fm.py` | `0b9e4f0903c2aaa36e998a354afa01b36d149d76` | `cfsm_gov_fm_public_laws` | FSM Congress Public Law PDFs from cfsm.gov.fm |
| `national_collectors/collect_govza_acts.py` | `b560f8d60962277b09c12c44457b424de25de83b` | `govza_acts` | South Africa national Acts and the Constitution from the official gov.za portal |
| `national_collectors/collect_pg.py` | `af81ba630119ad59022b531294e82421fc4a17cb` | `png_parliament_acts` | Papua New Guinea Parliament Acts PDFs. `catalog.py` has no `collect_pg.py` row. |
| `national_collectors/collect_bt.py` | `0b9e4f0903c2aaa36e998a354afa01b36d149d76` | `oag_gov_bt_acts` | Bhutan Acts PDFs from oag.gov.bt |
| `national_collectors/collect_ck.py` | `0b9e4f0903c2aaa36e998a354afa01b36d149d76` | `parliament_gov_ck_acts` | Cook Islands Parliament Acts Library PDFs |
| `national_collectors/collect_jo_gazette.py` | `d40ab60649b83781e3849e191c1f2ac8545b042f` | none in this file | Jordan catalog `source_type` is `jordan_official_gazette`. The module defines no `SOURCE_TYPE` and does not fetch. |

`collect_si.py`, `collect_gr.py`, `collect_bg.py`, and `ocr_gr_image_only.py` are the modules that write `document_type="gazette_act"`. They do not add a query method. An adapter still has to check that dataset before it claims the pipeline `DOC_TYPES` value `gazette_act`.

## US Code consolidation is excluded

US Code consolidation stays a law schema. It is not a legislative-act schema. `us_code_scraper.py` is not a legislative-act schema.

`ipfs_datasets_py/processors/legal_scrapers/federal_scrapers/us_code_scraper.py` last changed in `5b60299354522835994ae7076e357f13583ab88c`. A search of that file found no `SCHEMA_VERSION`, no `document_type`, and no `gazette_act`. The module docstring says it downloads title packages and produces section-level records for full U.S. Code ingestion. `_extract_consolidated_sections` writes a consolidated section dict with keys `section_number`, `heading`, `text`, `body_text`, and `citations`, plus `title_number`, `title_name`, `year`, `package`, and `source_url` when metadata is included. The package default is `USCODE-{year}-title{title}` via `f"USCODE-{int(year)}-title{title_num}"`. The per-HTML section record adds `chapter`, `preamble`, `citations`, `legislative_history`, `subsections`, and `parser_warnings`. `legislative_history` here is a field parsed out of a code section. It does not make this file a legislative-act schema.

`ipfs_datasets_py/processors/legal_scrapers/federal_scrapers/uscode_release_processor.py` last changed in `e92671688a60a27435d012debceec38a29e49edb`. It acquires U.S. Code release points. The module docstring names the stable section identity ``usc:{title}:{section}``. `stable_section_identity` says the shape is ``usc:{jurisdiction}:{title}:{section}`` and returns `usc:{jurisdiction}:{title}:{section}` with the jurisdiction lower-cased. Source format is excluded from that identity.

```python
SCHEMA_VERSION = "uscode-release-processor-v1"
FIXTURE_SCHEMA_VERSION = "uscode-release-fixture-v1"
```

`ipfs_datasets_py/processors/legal_data/uscode_release_schema.py` last changed in `c9e2f8bf44095e65561da83e152a1a20624aa2ff`. This is the release schema for the consolidated US Code corpus, not a public-law or gazette-act schema.

```python
SCHEMA_VERSION: Final = "uscode-sparse-graphrag-release-schema-v2"
RELEASE_PROFILE: Final = "publicus-ir-graphrag/v2"
```

`national_collectors/catalog.py` lists the scraper under `IN_TREE_SCRAPERS` as key `us-uscode`, module `ipfs_datasets_py.processors.legal_scrapers.federal_scrapers.us_code_scraper`, summary `United States Code.` That catalog row is a dataset pointer. It does not assign `gazette_act` or `public-law-change-processor-v1` to the scraper.

`public-law-change-processor-v1`, pipeline `gazette_act`, and `uscode-release-processor-v1` / `uscode-sparse-graphrag-release-schema-v2` stay three different contracts. `us_code_scraper.py` stays on the US Code consolidation side. An adapter that claims a legislative act must reject a row from these US Code modules.
