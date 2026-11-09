# Display and doc register

Register for the display ids that exist now, the five kind views this plan reserves, and the docs LCM-009 marked future-stale. `worldwide-legal-search.law-source@1` stays the statute view. This file does not edit the site, SwissKnife, `docs/worldwide/supervisor-operations.md`, or any markdown under `legal_scrapers` or `docs/legal`.

Read on 2026-11-09. Site checkout `/home/barberb/worldwidelaws.github.io`, `git rev-parse HEAD` `d41cf3311478e1861d58387b0033065330744097`. `git status --short` printed no lines for `src/lib/worldwide/data/schema.ts`, `src/lib/worldwide/data/identity.ts`, `src/lib/worldwide/jurisdiction/schema.ts`, `scripts/worldwide/refresh.ts`, `scripts/worldwide/update.ts`, and `src/components/worldwide/LawReader.tsx`. Training checkout `external/ipfs_datasets`, `git rev-parse HEAD` `d40ab60649b83781e3849e191c1f2ac8545b042f`. SwissKnife checkouts: `/home/barberb/lift_coding/swissknife` at `70e058f1416f0102a3cc4e926fa8a38ef2b8f19a`, and `/home/barberb/swissknife` at `9d758cd6e72e00c9b2575e682b38b077916bb392`.

A search of the site tree for `caselaw-view@`, `regulation-view@`, `legislative-act-view@`, `court-view@`, and `municipal-instrument-view@` returned no matches. The same search of `web/` in both SwissKnife checkouts returned no matches, and neither `web/` tree contains `law-source@1`.

## Statute view

`src/lib/worldwide/data/schema.ts` last changed in `72211e93b7df2be38820cb7bf214ee1d56bebba5`. The file header is `Versioned law-source and law-section schema.`

```ts
export const SCHEMA_VERSION = 1;
export const LAW_SOURCE_SCHEMA = 'worldwide-legal-search.law-source@1';
export const LAW_SECTION_SCHEMA = 'worldwide-legal-search.law-section@1';
export const QUARANTINE_SCHEMA = 'worldwide-legal-search.quarantine@1';
```

```ts
export const REQUIRED_LAW_COLUMNS = ['id', 'title', 'text'] as const;
export const REQUIRED_ARTICLE_COLUMNS = ['id', 'law_id', 'title', 'text'] as const;
```

`law-source@1` remains the statute view. This register does not renumber it and does not reserve a second statute view id. `law-section@1` remains the section record. `quarantine@1` in this file is the data-file quarantine id.

The same file exports `INSTRUMENT_KINDS`: `constitution`, `statute`, `code`, `regulation`, `ordinance`, `treaty`, `decision`, `notice`, `amendment`, `consolidation`, and `unknown`. That tuple is a label list inside `law-source@1`. It is not `regulation-view@1`, a caselaw view, or a court view.

`src/components/worldwide/LawReader.tsx` exports `worldwide-legal-search.law-reader@1` as `READER_SCHEMA`. That is the reader page schema. It is not a replacement for `law-source@1`.

## Corpus pin carried by the site

`src/lib/worldwide/data/identity.ts` last changed in `8eade85b30bfd59f5f886eee0e2740ebf990f8fa`:

```ts
export const CORPUS_SCHEMA_VERSION = 'country-laws-ir-graphrag/v1';
export const ENTRY_IDENTITY_SCHEMA = 'country-laws-entry/v1';
export const LAW_IDENTITY_SCHEMA = 'country-laws-law/v1';
export const INHERIT_VERSION = 'instrument-inherit/v1';
```

`CORPUS_SCHEMA_VERSION` is the statute corpus pin. The other three constants are identity and inheritance pins in the same file. They are not display view ids.

## Jurisdiction ids

`src/lib/worldwide/jurisdiction/schema.ts` last changed in `c4ddae864ebe3717adfaf9b8614f3668478b2c83`. The header says this module does not resolve coordinates or rank disputed views.

```ts
export const SCHEMA_VERSION = 1;
export const CITY_REQUIRED = false as const;
export const APPLICABILITY = 'not-asserted' as const;

export const JURISDICTION_GRAPH_SCHEMA = 'worldwide-legal-search.jurisdiction-graph@1';
export const JURISDICTION_NODE_SCHEMA = 'worldwide-legal-search.jurisdiction-node@1';
export const JURISDICTION_EDGE_SCHEMA = 'worldwide-legal-search.jurisdiction-edge@1';
export const DISPUTED_VIEW_SCHEMA = 'worldwide-legal-search.disputed-view@1';
export const UNKNOWN_RELATIONSHIP_SCHEMA = 'worldwide-legal-search.unknown-relationship@1';
export const QUARANTINE_SCHEMA = 'worldwide-legal-search.jurisdiction-quarantine@1';
```

Applicability stays `not-asserted`. `disputed-view@1` is a named jurisdiction interpretation. It is not `court-view@1`. `jurisdiction-quarantine@1` is not the data-file `quarantine@1`.

## Other current UI schema ids

These ids are exported from `src/` in the site working tree at the HEAD above. They are current UI or site-library ids. None of them is a caselaw, regulation, legislative-act, court, or municipal-instrument view.

| Id | Export |
| --- | --- |
| `worldwide-legal-search.shell@1` | `SHELL_SCHEMA` in `src/components/worldwide/SearchContext.tsx` |
| `worldwide-legal-search.results-page@1` | `RESULTS_PAGE_SCHEMA` in `src/components/worldwide/SearchResults.tsx` |
| `worldwide-legal-search.law-reader@1` | `READER_SCHEMA` in `src/components/worldwide/LawReader.tsx` |
| `worldwide-legal-search.place-page@1` | `PLACE_PAGE_SCHEMA` in `src/components/worldwide/PlacePage.tsx` |
| `worldwide-legal-search.place-picker@1` | `PLACE_PICKER_SCHEMA` in `src/components/worldwide/PlacePicker.tsx` |
| `worldwide-legal-search.place-selection@1` | `PLACE_SELECTION_SCHEMA` in `src/components/worldwide/PlacePicker.tsx` |
| `worldwide-legal-search.source-page@1` | `SOURCE_PAGE_SCHEMA` in `src/components/worldwide/SourcePage.tsx` |
| `worldwide-legal-search.coverage-page@1` | `COVERAGE_PAGE_SCHEMA` in `src/components/worldwide/CoveragePage.tsx` |
| `worldwide-legal-search.compare-places@1` | `COMPARE_SCHEMA` in `src/components/worldwide/ComparePlaces.tsx` |
| `worldwide-legal-search.research-panel@1` | `RESEARCH_SCHEMA` in `src/components/worldwide/ResearchPanel.tsx` |
| `worldwide-legal-search.route-contract@1` | `ROUTE_CONTRACT_ID` in `src/lib/worldwide/routes.ts` |
| `worldwide-legal-search.retrieval-contract@1` | `RETRIEVAL_CONTRACT_ID` in `src/lib/worldwide/contracts.ts` |
| `worldwide-legal-search.i18n@1` | `I18N_SCHEMA` in `src/lib/worldwide/i18n.ts` |
| `worldwide-legal-search.public-cache@1` | `CACHE_SCHEMA` and `CACHE_DATABASE` in `src/lib/worldwide/data/cache.ts` |
| `worldwide-legal-search.public-artifacts@1` | `CACHE_STORAGE_NAME` in `src/lib/worldwide/data/cache.ts` |
| `worldwide-legal-search.catalog@1` | `CATALOG_SCHEMA` in `src/lib/worldwide/data/catalog.ts` |
| `worldwide-legal-search.source-inventory@1` | schema string in `src/lib/worldwide/data/catalog.ts` |
| `worldwide-legal-search.source-dispositions@1` | schema string in `src/lib/worldwide/data/catalog.ts` |
| `worldwide-legal-search.rights@1` | schema string in `src/lib/worldwide/data/catalog.ts` |
| `worldwide-legal-search.search-plan@1` | `SEARCH_PLAN_SCHEMA` in `src/lib/worldwide/search/planner.ts` |
| `worldwide-legal-search.worldwide-search@1` | `SEARCH_SCHEMA` in `src/lib/worldwide/search/global.ts` |
| `worldwide-legal-search.global-routing@1` | `GLOBAL_ROUTING_SCHEMA` in `src/lib/worldwide/search/global.ts` |
| `worldwide-legal-search.global-envelope@1` | `ENVELOPE_SCHEMA` in `src/lib/worldwide/search/global.ts` |
| `worldwide-legal-search.global-directory@1` | `DIRECTORY_SCHEMA` in `src/lib/worldwide/search/global.ts` |
| `worldwide-legal-search.global-shard-summary@1` | `SHARD_SCHEMA` in `src/lib/worldwide/search/global.ts` |
| `worldwide-legal-search.rank-fusion@1` | `FUSION_SCHEMA` in `src/lib/worldwide/search/fusion.ts` |
| `worldwide-legal-search.transport@1` | `TRANSPORT_SCHEMA` in `src/lib/worldwide/data/transport.ts` |
| `worldwide-legal-search.transport-capability@1` | `CAPABILITY_SCHEMA` in `src/lib/worldwide/data/transport.ts` |
| `worldwide-legal-search.immutable-artifact@1` | `ARTIFACT_SCHEMA` in `src/lib/worldwide/data/transport.ts` |
| `worldwide-legal-search.artifact-batch@1` | `ARTIFACT_BATCH_SCHEMA` in `src/lib/worldwide/data/transport.ts` |
| `worldwide-legal-search.viewer-page@1` | `VIEWER_PAGE_SCHEMA` in `src/lib/worldwide/data/transport.ts` |
| `worldwide-legal-search.viewer-layout@1` | `VIEWER_LAYOUT_SCHEMA` in `src/lib/worldwide/data/transport.ts` |
| `worldwide-legal-search.viewer-walk@1` | `VIEWER_WALK_SCHEMA` in `src/lib/worldwide/data/transport.ts` |
| `worldwide-legal-search.viewer-compatibility@1` | `VIEWER_COMPATIBILITY_SCHEMA` in `src/lib/worldwide/data/transport.ts` |
| `worldwide-legal-search.authority-stack@1` | `AUTHORITY_STACK_SCHEMA` in `src/lib/worldwide/jurisdiction/authority.ts` |
| `worldwide-legal-search.temporal-scope@1` | `TEMPORAL_SCOPE_SCHEMA` in `src/lib/worldwide/jurisdiction/temporal.ts` |
| `worldwide-legal-search.point-resolution@1` | `POINT_RESOLUTION_SCHEMA` in `src/lib/worldwide/jurisdiction/resolve.ts` |
| `worldwide-legal-search.place-resolution@1` | `PLACE_RESOLUTION_SCHEMA` in `src/lib/worldwide/jurisdiction/resolve.ts` |
| `worldwide-legal-search.place-index@1` | `PLACE_INDEX_SCHEMA` in `src/lib/worldwide/jurisdiction/resolve.ts` |
| `worldwide-legal-search.place-state@1` | `PLACE_STATE_SCHEMA` in `src/lib/worldwide/location/state.ts` |
| `worldwide-legal-search.saved-place@1` | `SAVED_PLACE_SCHEMA` in `src/lib/worldwide/location/state.ts` |
| `worldwide-legal-search.device-location@1` | `DEVICE_LOCATION_SCHEMA` in `src/lib/worldwide/location/device.ts` |
| `worldwide-legal-search.device-outcome@1` | `DEVICE_OUTCOME_SCHEMA` in `src/lib/worldwide/location/device.ts` |
| `worldwide-legal-search.device-resolution@1` | `DEVICE_RESOLUTION_SCHEMA` in `src/lib/worldwide/location/device.ts` |
| `worldwide-legal-search.geoip-provider-decision@1` | `GEOIP_DECISION_SCHEMA` in `src/lib/worldwide/location/geoip.ts` |
| `worldwide-legal-search.geoip-hint@1` | `GEOIP_HINT_SCHEMA` in `src/lib/worldwide/location/geoip.ts` |
| `worldwide-legal-search.geoip-outcome@1` | `GEOIP_OUTCOME_SCHEMA` in `src/lib/worldwide/location/geoip.ts` |
| `worldwide-legal-search.geoip-opt-out@1` | `GEOIP_OPT_OUT_SCHEMA` in `src/lib/worldwide/location/geoip.ts` |
| `worldwide-legal-search.geoip-session@1` | `GEOIP_SESSION_SCHEMA` in `src/lib/worldwide/location/geoip.ts` |

The five `geoip-*` ids are location-schema ids that already exist. They are not a kind view, and this register does not add a GEOIP field to a view.

`scripts/worldwide/refresh.ts` last changed in `5ebbd7188a4b884d85e47c125c91751eebb50cd2` exports `worldwide-legal-search.refresh@1`, `worldwide-legal-search.refresh-manifest@1`, `worldwide-legal-search.refresh-current@1`, `worldwide-legal-search.refresh-quarantine@1`, and `SCHEMA_VERSION` `1`. `scripts/worldwide/update.ts` last changed in `668e6633a09ef671f64127e8cf0b633ba6d6231e` exports `worldwide-legal-search.ingestion-artifact@1`, `worldwide-legal-search.ingestion-manifest@1`, `worldwide-legal-search.ingestion-current@1`, `worldwide-legal-search.ingestion-quarantine@1`, `worldwide-legal-search.incremental-update@1`, and `SCHEMA_VERSION` `1`. Those are refresh and ingestion schemas, not legal-instrument views. The same scripts tree also exports `worldwide-legal-search.source-dispositions@1`, `worldwide-legal-search.index-format@1`, `worldwide-legal-search.performance@1`, `worldwide-legal-search.source-inventory@1`, and `worldwide-legal-search.geography-manifest@1`. Those are build-script ids, not kind views.

## Reserved kind views

These ids are reserved. They are not exported by the site or by either SwissKnife `web/` tree. Later display tasks own the modules. This register does not add them to the site.

| Reserved id | Kind |
| --- | --- |
| `worldwide-legal-search.caselaw-view@1` | caselaw |
| `worldwide-legal-search.regulation-view@1` | regulation |
| `worldwide-legal-search.legislative-act-view@1` | legislative act |
| `worldwide-legal-search.court-view@1` | court |
| `worldwide-legal-search.municipal-instrument-view@1` | municipal instrument |

`worldwide-legal-search.law-source@1` stays the statute view beside this list.

## SwissKnife

A search of `web/js/apps` for `legal` returned no matches in either checkout. No file under either `web/js/apps` exports `law-source@1`, `law-section@1`, a jurisdiction schema id, or a legal-instrument view version.

Outside `web/js/apps`, both checkouts contain `src/services/logic/deontic/deontic-legal-text-engine.ts`, last changed in `6651a7279b1799b8629fcf5e95caaf07cb8accbc`. The header calls it a parser and export layer, not a display view:

```ts
/**
 * Deontic legal-text parser/export compatibility layer.
```

```ts
const SCHEMA_VERSION = 'deterministic_deontic_v12';
```

That string is a deontic IR schema. It does not export `worldwide-legal-search.law-source@1` or any reserved kind view id.

## Docs LCM-009 marked future-stale

LCM-009, `implementation_plan/legal_corpus_modules/evidence/LCM-009.md`, marked the files below future-stale. Each path was present in the training checkout when this register was written. None of these files was rewritten. `country-laws-ir-graphrag/v1` and pipeline `1.2.0` stay source contracts where those docs quote them. What LCM-009 marked stale is using the markdown, or the duplicate tree it points at, as the current module map.

### Reports that present `legal_scrapers` as the finished package

Each of these names the package path `ipfs_datasets_py.processors.legal_scrapers`. The import or path below is the line read for this register.

| File | Line read |
| --- | --- |
| `ipfs_datasets_py/processors/legal_scrapers/FINAL_PROJECT_REPORT.md` | `from ipfs_datasets_py.processors.legal_scrapers import (` |
| `ipfs_datasets_py/processors/legal_scrapers/PROJECT_COMPLETE.md` | `from ipfs_datasets_py.processors.legal_scrapers import BraveLegalSearch` |
| `ipfs_datasets_py/processors/legal_scrapers/BRAVE_LEGAL_SEARCH.md` | `from ipfs_datasets_py.processors.legal_scrapers import BraveLegalSearch` |
| `ipfs_datasets_py/processors/legal_scrapers/BRAVE_LEGAL_SEARCH_IMPLEMENTATION.md` | `from ipfs_datasets_py.processors.legal_scrapers import BraveLegalSearch`, and `ipfs_datasets_py/processors/legal_scrapers/__init__.py` |
| `ipfs_datasets_py/processors/legal_scrapers/HUGGINGFACE_INDEX_INTEGRATION.md` | `from ipfs_datasets_py.processors.legal_scrapers import CommonCrawlIndexLoader, LegalWebArchiveSearch` |
| `ipfs_datasets_py/processors/legal_scrapers/HUGGINGFACE_INTEGRATION_SUMMARY.md` | `from ipfs_datasets_py.processors.legal_scrapers import CommonCrawlIndexLoader` |
| `ipfs_datasets_py/processors/legal_scrapers/SHARED_COMPONENTS.md` | `from ipfs_datasets_py.processors.legal_scrapers.complaint_analysis import (` |
| `ipfs_datasets_py/processors/legal_scrapers/WEB_ARCHIVE_INTEGRATION_COMPLETE.md` | `from ipfs_datasets_py.processors.legal_scrapers import LegalWebArchiveSearch` and `ipfs_datasets_py/processors/legal_scrapers/legal_web_archive_search.py` |
| `ipfs_datasets_py/processors/legal_scrapers/LEGAL_WEB_ARCHIVE_INTEGRATION.md` | `ipfs_datasets_py/processors/legal_scrapers/legal_web_archive_search.py` |
| `ipfs_datasets_py/processors/legal_scrapers/MULTI_ENGINE_SEARCH.md` | `from ipfs_datasets_py.processors.legal_scrapers import MultiEngineLegalSearch` |
| `ipfs_datasets_py/processors/legal_scrapers/COMPLAINT_ANALYSIS_REFACTORING.md` | `from legal_scrapers.common import get_keywords, LegalPatternExtractor` |
| `ipfs_datasets_py/processors/legal_scrapers/complaint_analysis/README.md` | "shared with other systems in `legal_scrapers`" |
| `ipfs_datasets_py/processors/legal_scrapers/state_scrapers/README.md` | `from ipfs_datasets_py.processors.legal_scrapers.state_laws_scraper import scrape_state_laws` |

### Duplicate-tree schema and column maps

`ipfs_datasets_py/processors/legal_scrapers/hub_integrated/legal_scrapers/SCHEMA.md` last changed in `4cdca488f0bd997e8f7a90438aa90a859cb85c5b`. It pins `world-laws-raw/v1` as "19 columns, this order, no others", beginning `id`, `title`, `text`, and it names `country-laws-ir-graphrag/v1` on the normalized layer. The code pointer in that file is `schema.py` in the same duplicate tree.

`ipfs_datasets_py/processors/legal_scrapers/hub_integrated/legal_scrapers/WORLD_COVERAGE_AUDIT.md` names `country-laws-ir-graphrag/v1` and the package path `ipfs_datasets_py/processors/legal_scrapers/country_laws_ir/{schema,normalize,structure,package,upload,coverage,catalog}.py`.

`ipfs_datasets_py/processors/legal_scrapers/hub_integrated/legal_scrapers/MANIFEST.md` names `country-laws-ir-graphrag/v1` on `normalizers/country_laws_ir/package.py` and `skillcenter-huggingface-release/v3` on `normalizers/country_laws_ir/parquet_io.py`.

`ipfs_datasets_py/processors/legal_scrapers/hub_integrated/legal_scrapers/normalizers/NORMALIZER_VERSION.md` calls `country_laws_ir/` a verbatim copy at path `ipfs_datasets_py/processors/legal_scrapers/` with schema `country-laws-ir-graphrag/v1`, and says "Canonical source of truth stays upstream".

`ipfs_datasets_py/processors/legal_scrapers/hub_integrated/justicedao_world_law_scrapers/ir_builder/README.md` names `country-laws-ir-graphrag/v1`, layout family `skillcenter-huggingface-release/v3`, and the command `cd /workspace/country-laws-ir`.

`ipfs_datasets_py/processors/legal_scrapers/hub_integrated/world_law_pipeline/SCHEMA.md` is titled "world_municipal_law — schema & staging contract (v1.2.0)" and says the source of truth is `/workspace/world_law/pipeline/schema.py`.

### Column layouts that are not the municipal instrument layout

Both eCode360 plans say the html parquet columns are `cid`, `doc_id`, `doc_order`, `html_title`, `html`.

- `ipfs_datasets_py/processors/legal_scrapers/municipal_law_database_scrapers/hub/ECODE360_AMLEGAL_PLAN.md`
- `ipfs_datasets_py/processors/legal_scrapers/hub_integrated/world_law_pipeline/world/ECODE360_AMLEGAL_PLAN.md`

### `docs/legal` refresh plans

These name a normalizer string from before the module boundary. They were not rewritten by this task.

- `docs/legal/justicedao_refresh_plan_20261016.md` says normalizer `american-municipal-html/v2+legal-record/v1` and `american-municipal-html/v3+legal-record/v1`.
- `docs/legal/justicedao_refresh_plan_20261017.md` says normalizer `american-municipal-html/v2+legal-record/v1`.
- `docs/legal/justicedao_refresh_plan_20261019.md` says normalizer `american-municipal-html/v4+legal-record/v1`.
- `docs/legal/justicedao_refresh_plan_20261021.md` says normalizer `american-municipal-html/v4+legal-record/v1`. `git status --short` prints `M docs/legal/justicedao_refresh_plan_20261021.md`. `git diff --numstat` prints `44 2`. The diff starts at the Romania paragraph and does not change that normalizer line. This register did not write that diff.

LCM-009 also names files that stay source contracts. Those are not in the future-stale list above.

## What this register does not do

No site file was edited. No SwissKnife file was edited. No future-stale doc was rewritten. No reserved view module was added. Parent goal `LCM-G020` was not marked complete.
