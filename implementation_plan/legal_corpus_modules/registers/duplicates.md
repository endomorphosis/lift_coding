# Duplicate-tree disposition

Register for the trees `PLAN.md` lists under "Duplicate trees". Each tree below has one disposition: `canonical`, `mirror`, `collector-entry`, or `quarantine`. The 17 note files are `quarantine`. The Argentina and Malta SkillCenter `v3` copies are `leave-in-place`. No path is marked `delete`. This file does not remove, rename, or rewrite a scraper, and it does not authorize a bulk delete.

Read on 2026-11-09 from the training checkout `external/ipfs_datasets`. `git rev-parse HEAD` is `d40ab60649b83781e3849e191c1f2ac8545b042f`. `git status --short` printed no lines for the trees and files quoted below. Paths sit under `ipfs_datasets_py/processors/legal_scrapers/` unless a line says otherwise.

`country_laws_ir/` and `world_municipal/schema.py` are not in the duplicate-tree list. They are the schema homes the mirrors repeat. They receive no duplicate disposition.

## Disposition

| Tree | Disposition |
| --- | --- |
| `hub_dataset_scripts` | `mirror` |
| `hub_integrated/justicedao_world_law_scrapers` | `mirror` |
| `hub_integrated/legal_scrapers` | `mirror` |
| `hub_integrated/world_law_pipeline` | `canonical` |
| `international/harvested` | `mirror` |
| `national_collectors` | `collector-entry` |
| `national_campaigns` | `collector-entry` |
| `state_scrapers` | `mirror` |
| `world_municipal_campaigns` | `mirror` |
| `municipal` | `mirror` |

`canonical` means the tree holds the schema file `PLAN.md` names as still authoritative. `mirror` means the tree repeats a schema or a collector and is not an independent instrument schema. `collector-entry` means `PLAN.md` keeps that directory as the catalog of national entry points. `quarantine` is used for the 17 note files, not for a whole tree. `leave-in-place` is only the two SkillCenter `v3` copies.

## `hub_integrated/world_law_pipeline` — `canonical`

`hub_integrated/world_law_pipeline/schema.py`, last changed in `d40ab60649b83781e3849e191c1f2ac8545b042f`, is the pipeline contract. The tree disposition is `canonical` because this file is the `1.2.0` source. It stays that source until a later named go-ahead says otherwise. This register does not move schema authority and does not delete the tree. Scripts under `scrapers/` repeat collector text. They are not a second schema id and they are not marked `delete`.

```python
SCHEMA_VERSION = "1.2.0"  # 1.1.0: optional provenance columns + extra_metadata (appended); 1.2.0: pdf_ref (appended)
```

```python
REPO_ID = "endomorphosis/world_municipal_law"
NATIONAL_REPO_ID = "endomorphosis/world_national_law"   # national + subnational (iso:* places), split 2026-10-11
```

```python
DOC_TYPES = ("code_section", "ordinance", "regulation", "statute", "gazette_act", "decision")
```

## `hub_dataset_scripts` — `mirror`

The statute schema home is `country_laws_ir/__init__.py`, last changed in `9df09d3f50b80beebd5ae8bcd83cf72d034078c2`. That file is not a duplicate tree.

```python
SCHEMA_VERSION = "country-laws-ir-graphrag/v1"
LAYOUT_FAMILY = "skillcenter-huggingface-release/v3"
```

`LAYOUT_FAMILY` is not the statute schema. A v1 package inside the duplicate tree repeats both strings. `hub_dataset_scripts/justicedao__ipfs_germany_laws_ir/country_laws_ir/__init__.py`, last changed in `5f457fb04b1bbc27ccc84451fe6ba7f93700d9cd`:

```python
SCHEMA_VERSION = "country-laws-ir-graphrag/v1"
LAYOUT_FAMILY = "skillcenter-huggingface-release/v3"
```

The tree also repeats a collector helper. `hub_dataset_scripts/endomorphosis__legal_scrapers/scrapers/common.py`, last changed in `af81ba630119ad59022b531294e82421fc4a17cb`, opens `Shared helpers for national legislation collectors.` and sets:

```python
ROOT = Path("/workspace/legal-corpora")
SCHEMA_PATH = ROOT / "_templates" / "collection_record.schema.json"
```

That helper is not an instrument schema. The tree is a `mirror`. It is not marked `delete`.

## `hub_integrated/justicedao_world_law_scrapers` — `mirror`

`hub_integrated/justicedao_world_law_scrapers/ir_builder/country_laws_ir/__init__.py`, last changed in `4cdca488f0bd997e8f7a90438aa90a859cb85c5b`, assigns the same pair as the statute schema home:

```python
SCHEMA_VERSION = "country-laws-ir-graphrag/v1"
LAYOUT_FAMILY = "skillcenter-huggingface-release/v3"
```

The tree repeats that schema and repeats collectors, including the nested catalog under `ipfs_datasets_py_legal/`. Disposition is `mirror`. The tree is not marked `delete`.

## `hub_integrated/legal_scrapers` — `mirror`

`hub_integrated/legal_scrapers/schema.py`, last changed in `d40ab60649b83781e3849e191c1f2ac8545b042f`:

```python
IR_SCHEMA_VERSION = "country-laws-ir-graphrag/v1"
```

```python
MUNICIPAL_SCHEMA_VERSION = "world-laws-municipal/v1"
```

`hub_integrated/legal_scrapers/municipal/schema.py`, last changed in `4cdca488f0bd997e8f7a90438aa90a859cb85c5b`, assigns the same `IR_SCHEMA_VERSION = "country-laws-ir-graphrag/v1"`. Those strings are copies. The 19-column municipal contract is `world_municipal/schema.py`, which is outside this tree. Disposition of the tree is `mirror`. The 17 note files inside it are `quarantine` in the next section. Neither the tree nor those notes are marked `delete`.

## `international/harvested` — `mirror`

`international/harvested/NOTICE`, last changed in `dbd94493a570fdebcd93368fb43b26f7fc79cf58`, starts `Harvested official-gazette collectors from Hugging Face`. A search for a line `SCHEMA_VERSION =` under `international/harvested` returned no matches. `international/harvested/shared/common.py`, last changed in `4cdca488f0bd997e8f7a90438aa90a859cb85c5b`, stamps the collector row with:

```python
"schema_version": "collection_record.v1",
```

That string travels with the copied collectors. It is not a schema module. Disposition is `mirror`. The harvested scripts are not marked `delete`.

## `national_collectors` — `collector-entry`

`national_collectors/catalog.py`, last changed in `d40ab60649b83781e3849e191c1f2ac8545b042f`, opens `Catalog of official national gazette collectors vendored from Hugging Face.` A search for a line `SCHEMA_VERSION =` under `national_collectors/` returned no matches. Row builders in that directory stamp `"schema_version": "collection_record.v1"` on a collector record. That stamp is not a second instrument schema. `PLAN.md` says these collectors stay the catalog of national entry points, and copies of their schemas do not. Disposition is `collector-entry`. The catalog is not marked `delete`.

## `national_campaigns` — `collector-entry`

The wave scripts are harvest entry points beside `national_collectors`. `national_campaigns/wave13/pw_harvest13.py`, last changed in `4cdca488f0bd997e8f7a90438aa90a859cb85c5b`, writes the collector row with `'schema_version': 'collection_record.v1'` and `'metadata': {'collector': 'wave13 palaugov harvest (palaugov.pw)', ...}`. A search of that file found no line `SCHEMA_VERSION =`. The same `collection_record.v1` string is written by `wave13/pw_ocr13.py` and `wave13/pw_reverify13.py`. Disposition is `collector-entry`. The wave scripts are not marked `delete`.

## `state_scrapers` — `mirror`

`state_scrapers/README.md` says the directory contains individual scrapers for each US state's official legislative website and that each scraper outputs a `NormalizedStatute`. A search for a line `SCHEMA_VERSION =` under `state_scrapers/` returned no matches. Local receipt strings in this tree are not `country-laws-ir-graphrag/v1`.

`state_scrapers/new_york_law_pdf.py`, last changed in `1226373a4f2a69a8f4965273fc958aaffda815b5`:

```python
SUPPLEMENTAL_PROOF_SCHEMA_VERSION = "new-york-supplemental-proof-input-v1"
```

`state_scrapers/california_bulk.py`, last changed in `df53f62e06d00ab69f53aadf0ec0d997c1647d87`:

```python
LARGE_FILE_TRANSPORT_RECEIPT_SCHEMA = (
    "state-laws-large-file-transport-receipt-v1"
)
```

`PLAN.md` does not give this tree the national-catalog exception. It is not an independent instrument schema. Disposition is `mirror`. The scrapers are not marked `delete`.

## `world_municipal_campaigns` — `mirror`

A search for `schema_version` under `world_municipal_campaigns/` returned no matches. `world_municipal_campaigns/de_pilot/harvest_de_pilot.py`, last changed in `4cdca488f0bd997e8f7a90438aa90a859cb85c5b`, is titled `Germany municipal-law pilot harvester.` The docstring says rows split on section headings into the world_municipal 19-column schema. This file does not assign `SCHEMA_VERSION`.

The 19-column contract is `world_municipal/schema.py`, last changed in `4cdca488f0bd997e8f7a90438aa90a859cb85c5b`. That path is not a duplicate tree. Its docstring calls it the 19-column generalized schema. `EXPECTED_COLUMNS` lists 19 names, from `cid` through `retrieved`. The campaign tree repeats harvesters for that contract. Disposition is `mirror`. The campaigns are not marked `delete`.

## `municipal` — `mirror`

A search for `schema_version` under `municipal/` returned no matches. `municipal/__init__.py`, last changed in `dbd94493a570fdebcd93368fb43b26f7fc79cf58`, opens `US municipal code scrapers backed by the Hugging Face American Municipal Law corpus.` `municipal/catalog.py`, last changed in the same commit, sets `HUB_DATASET_ID = "endomorphosis/american_municipal_law"`. It does not assign `SCHEMA_VERSION`. This tree is another collector surface for that corpus. It does not hold the 19-column contract. Disposition is `mirror`. The tree is not marked `delete`.

## Seventeen note files — `quarantine`

These 17 files are under `hub_integrated/legal_scrapers/`. Each first line was read in this checkout. Each first line starts with `linked logs/`. They are not importable scrapers. Disposition of each file is `quarantine`. They stay at these paths. They are not marked `delete`. `git log -1` for `al_alfresco_tip26b.py` is `d40ab60649b83781e3849e191c1f2ac8545b042f`.

| File | First line |
| --- | --- |
| `al_alfresco_tip26b.py` | `linked logs/al_alfresco_tip26v.py -` |
| `al_close_tip26b.py` | `linked logs/al_close_tip26v.py -` |
| `az_cdx_extra_tip26f.py` | `linked logs/az_cdx_extra_tip26v.py -` |
| `az_live_gap_tip24o.py` | `linked logs/az_live_gap_tip26v.py -` |
| `az_live_gap_tip26f.py` | `linked logs/az_live_gap_tip26u.py -` |
| `bo_live_cdx_miss_tip26m.py` | `linked logs/bo_live_cdx_miss_tip26v.py -` |
| `bo_live_failures_tip26a.py` | `linked logs/bo_live_failures_tip26v.py -` |
| `bo_live_failures_tip26b.py` | `linked logs/bo_live_failures_tip26u.py -` |
| `ir_media_recent_tip25q.py` | `linked logs/ir_media_recent_tip26v.py -` |
| `ir_media_recent_tip26b.py` | `linked logs/ir_media_recent_tip26u.py -` |
| `ir_media_recent_tip26n.py` | `linked logs/ir_media_recent_tip26s.py -` |
| `mw_akn_miss_tip25m.py` | `linked logs/mw_akn_miss_tip26v.py -` |
| `mw_akn_miss_tip26b.py` | `linked logs/mw_akn_miss_tip26u.py -` |
| `mw_akn_miss_tip26n.py` | `linked logs/mw_akn_miss_tip26s.py -` |
| `mw_extra_akn_tip25p.py` | `linked logs/mw_extra_akn_tip26v.py -` |
| `mw_extra_akn_tip26b.py` | `linked logs/mw_extra_akn_tip26u.py -` |
| `mw_extra_akn_tip26m.py` | `linked logs/mw_extra_akn_tip26s.py -` |

## SkillCenter `v3` copies — `leave-in-place`

A search for `SCHEMA_VERSION = "skillcenter-huggingface-release/v3"` under `legal_scrapers` returned two files, both under `hub_dataset_scripts`. Both last changed in `5f457fb04b1bbc27ccc84451fe6ba7f93700d9cd`. Disposition of each copy is `leave-in-place`. They are not `country-laws-ir-graphrag/v1`. They are not marked `delete`.

`hub_dataset_scripts/justicedao__ipfs_argentina_laws-ir/country_laws_ir/__init__.py`:

```python
"""Country-law CID-keyed sparse GraphRAG packager (SkillCenter IR v3 layout)."""

__version__ = "0.1.0"
SCHEMA_VERSION = "skillcenter-huggingface-release/v3"
```

`hub_dataset_scripts/justicedao__ipfs_malta_laws-ir/country_laws_ir/__init__.py` assigns the same version and the same module docstring. The underscore package `hub_dataset_scripts/justicedao__ipfs_malta_laws_ir/country_laws_ir/__init__.py`, last changed in the same commit, assigns `SCHEMA_VERSION = "country-laws-ir-graphrag/v1"`. That underscore package stays inside the `hub_dataset_scripts` `mirror`. It is not a `leave-in-place` copy.
