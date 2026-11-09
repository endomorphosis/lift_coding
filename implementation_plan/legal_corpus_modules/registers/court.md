# Court schema register

Register for fields that identify a court as an institution. A court row uses those institution fields. Opinions stay in the caselaw register at `implementation_plan/legal_corpus_modules/registers/caselaw.md`. This file does not create a court row by copying an opinion id, a docket id, or a document id. It does not edit the datasets checkout and it does not open a query route.

Read on 2026-11-09 from the training checkout `external/ipfs_datasets`. `git rev-parse HEAD` is `d40ab60649b83781e3849e191c1f2ac8545b042f`. `git status --short` printed no lines for the files quoted below.

`courts_common.py`, `upload_world_courts.py`, `us_osm_courthouses.py`, `collect_fr_dila.py`, `collect_de_rii.py`, `peachjam.py`, `br_stj.py`, `co_cc.py`, `wayback_generic.py`, and `upload.py` last changed in `d40ab60649b83781e3849e191c1f2ac8545b042f`. `vector_search_integration.py`, `recap_archive_scraper.py`, and `courtlistener_ingestion.py` last changed in `df93e91e6338c84a17c3208ef68b88de8566f78c`.

None of those modules assigns `SCHEMA_VERSION`. `git ls-files` printed no path for `world_courts_schema.json`. This register's schema id is `unversioned`.

## Institution fields

The local constructor is `rec` in `ipfs_datasets_py/processors/legal_scrapers/hub_integrated/world_law_pipeline/scrapers/courts/intl/courts_common.py`. The default record has no opinion `text` field and no statute column. Its identifying fields are `court_id`, `name`, `name_local`, `level`, `court_system`, `country_code`, `subdivision`, `jurisdiction`, `parent_court_id`, and `record_type`.

```python
def rec(**kw):
    base = dict(court_id=None, record_type="courthouse", name=None, name_local=None, level="other", court_system="national", country_code=None,
                subdivision=None, jurisdiction=None, parent_court_id=None, address={"street": None, "city": None, "postcode": None, "region": None, "country": None},
                geo={"lat": None, "lon": None}, phone=None, website=None, wikidata=None, place_ids=[], source_url=None, source_kind="official",
                site_policy="robots_allowed", retrieved_at=NOW(), license=None, sources=[])
    base.update(kw)
```

`record_type` defaults to `"courthouse"`. `level` defaults to `"other"`. `court_system` defaults to `"national"`. `source_kind` defaults to `"official"`.

`ipfs_datasets_py/processors/legal_scrapers/hub_integrated/world_law_pipeline/scrapers/courts/upload_world_courts.py` publishes that record. The dataset name is a repo id, not a schema version:

```python
ROOT="/workspace/world_courts";PUB=ROOT+"/publish";STATE=PUB+"/.upload_state.json"
DS="endomorphosis/world_courts";PIPE="endomorphosis/world_law_pipeline"
```

`flat_court` requires `court_id` and `country_code`. It copies the institution fields below. `record_type` defaults to `"courthouse"` when the source row omits it. Address `region` and address `country` from `rec` are not copied. There is no opinion id and no opinion text.

```python
def flat_court(r):
    a=r.get("address") or {};g=r.get("geo") or {}
    return {"court_id":r["court_id"],"name":r.get("name"),"official_name":r.get("official_name"),"level":r.get("level"),"court_system":r.get("court_system"),
      "country_code":r["country_code"],"subdivision":r.get("subdivision"),"record_type":r.get("record_type","courthouse"),"license":r.get("license"),"geo_source":r.get("geo_source"),"upstream":r.get("upstream"),"subdivision_method":r.get("subdivision_method"),"hours":r.get("hours"),"email":r.get("email"),"jurisdiction":r.get("jurisdiction"),"county_fips":r.get("county_fips"),"parent_court_id":r.get("parent_court_id"),
      "street":a.get("street"),"city":a.get("city"),"postcode":a.get("postcode"),"lat":g.get("lat"),"lon":g.get("lon"),"phone":r.get("phone"),"website":r.get("website"),
      "wikidata":r.get("wikidata"),"place_ids":list(r.get("place_ids") or []),"place_match_method":r.get("place_match_method"),
      "source_url":r.get("source_url"),"source_kind":r.get("source_kind"),"site_policy":r.get("site_policy"),"sources_json":json.dumps(r.get("sources") or [],sort_keys=True),
      "needs_review":bool(r.get("needs_review",False)),"retrieved_at":r.get("retrieved_at")}
```

`flat_court_eu` adds `court_family`, `tier`, `level_basis`, `cdb_id`, `ecli_code`, `name_local`, `upstream_court_id`, `accepted_languages`, `geoname_ids`, and `upstream_json`. `flat_court_row` adds `name_local`, `record_note`, `facility_kind`, `geonames_city`, `geonames_admin1`, `geonames_admin2`, `admin_qid`, `operational_status`, `geoname_ids`, and `upstream_json`. Those are extra institution columns. They are not opinion ids.

`build` writes the court table with `wr(f"courthouses/{cc}", ...)`, which stores `data/courthouses/<cc>.parquet` under the publish tree. The same function also writes judges, forms, rules, and rules-crosswalk parquet. Those are not court rows. The publisher comment on the GB / CA / AU loop is:

```python
# ---- phase 5: GB / CA / AU (same schema; record_type=court_body rows give the court hierarchy that parent_court_id points to)
```

`record_type` `"court_body"` is the hierarchy value that comment names. It is not an opinion.

`us_osm_courthouses.py` builds one courthouse jsonl row per OSM element. Its docstring says the output follows `schema/world_courts_schema.json` key `courthouses`. That JSON file is not in this checkout. The assigned court identifier is the OSM element id, not an opinion id:

```python
rec={"court_id":f"osm:{e['type']}/{e['id']}","name":name,"level":classify(name),"court_system":"federal" if classify(name)=="federal_district" else ("municipal" if classify(name)=="municipal" else "state"),
     "country_code":"US","subdivision":f"US-{st}","jurisdiction":t.get("addr:county"),"parent_court_id":None,
```

`source_url` on that row is `https://www.openstreetmap.org/{type}/{id}`. The row sets no `record_type` and no opinion text.

## Opinions stay in the caselaw register

The rows below name a court and also carry opinion text or a docket document. They stay in the caselaw register. A court row is not created by copying their ids. The court identifier remains `court_id` from the institution record above.

### CAP

`ipfs_datasets_py/processors/legal_scrapers/caselaw_access_program/vector_search_integration.py` writes no court table. `build_knowledge_graph_seeds` copies `metadata["court"]` onto the Case node, whose id is `case:{case_key}`. When `court` is present it adds an in-memory node. That node is not a court-table row, and the case id is not copied onto it:

```python
court = metadata.get("court")
if court:
    court_id = f"court:{court}"
    nodes[court_id] = {
        "id": court_id,
        "type": "Court",
        "properties": {"name": court},
    }
```

The only property is `name`. Do not copy `case:{case_key}`, `chunk_id`, or `case_id` into a court row.

### DILA

`ipfs_datasets_py/processors/legal_scrapers/national_collectors/collect_fr_dila.py` `parse` returns one opinion row. `text` comes from `CONTENU`. Court identity on that row is the string `court` from `META_JURI/JURIDICTION`. `court_id` is `None`. `dila_id` is the document id from `META_COMMUN/ID`. Do not copy `dila_id` into a court row.

```python
"court": _t(root, f"{meta}/JURIDICTION"),
"court_id": None, "dila_id": _t(root, ".//META_COMMUN/ID"), "config": FONDS[fond],
```

### Rechtsprechung im Internet

`ipfs_datasets_py/processors/legal_scrapers/national_collectors/collect_de_rii.py` `parse` returns one opinion row. `text` is the joined opinion parts. `court_id` is `None`. `rii_doknr` is `doknr` on that opinion. Do not copy `rii_doknr` into a court row.

```python
court = (field("gertyp") + " " + field("spruchkoerper")).strip()
```

The returned dict sets `court` to that string, `chamber` to `spruchkoerper`, and `court_id` to `None`.

### `endomorphosis/world_caselaw`

`ipfs_datasets_py/processors/legal_scrapers/hub_integrated/world_law_pipeline/scrapers/caselaw/amea/upload.py` sets `REPO="endomorphosis/world_caselaw"` and assigns no schema version. The writers below emit judgment jsonl. Each judgment has its own `id` and a `text` field. Those rows stay in the caselaw register. Do not copy the judgment `id` into a court row.

`peachjam.py` reads the court name from the page meta key `Court`. `court_id` is a lookup against external `court_body` rows, not a copy of the judgment id:

```python
p = f"/workspace/world_courts/data/{cc}/{cc}_courthouses.jsonl"
```

```python
bodies = [r for r in self.rows if r.get("record_type") == "court_body"]
```

```python
"id": f"{src}:{url.split('/akn/')[-1]}", "court": court, "court_id": cmap.lookup(court, cc, url.split('/akn/')[0]),
```

The courthouse file is outside this checkout. A missing name is appended to `missing_courts.jsonl` with `name`, `country`, and `official_url`. That sidecar is not a court row in the repo. The judgment `id` stays on the opinion.

`br_stj.py` writes the judgment fields `court` `"Superior Tribunal de Justiça"` and `court_id` `"br-national-supreme-stj"` on the same row as `text`. The judgment id is `f"{SRC}:{sq}"`. Do not copy that id into a court row.

`co_cc.py` writes `court` `"Corte Constitucional"` and `court_id` `"co-corte-constitucional"` on the judgment row. The judgment id is `f"{SRC}:{s}"`. Do not copy that id into a court row.

`wayback_generic.py` sets `court` and `court_id` from CLI defaults or from a SAFLII path, then may replace `court_id` with a `court_body` id from the same external courthouse jsonl. The judgment id is `f"{a.src}:{key}"`. Do not copy that id into a court row.

### RECAP

`ipfs_datasets_py/processors/legal_scrapers/recap_archive_scraper.py` assigns no schema version and writes no court table. `search_recap_documents` calls `https://www.courtlistener.com/api/rest/v3/search/`. Search rows identify the court with `court` from the result field `court` and `court_full_name` from `court_name`. The search row's `id` is the document id. Do not copy that document id into a court row.

The `court` argument is a query filter. The docstring says `Court identifier (e.g., "ca9" for 9th Circuit, "nysd" for S.D.N.Y.)`. That filter is not a stored court row.

`_hydrate_recap_document_metadata` loads `https://www.courtlistener.com/api/rest/v3/dockets/{docket_id}/` and copies `court_id`. When `court` is an `http` URL it reads `full_name` and `short_name`:

```python
hydrated["court"] = (
    court_data.get("full_name", "") or court_data.get("short_name", "") or court_id
)
hydrated["court_full_name"] = court_data.get("full_name", "") or hydrated["court"]
```

`get_recap_document` keeps the document `id` and puts `court_id` and `court_full_name` in `metadata`, beside `docket_number`. `docket_number` identifies a case. `pacer_doc_id` identifies a document. Neither is copied into a court row. `text` comes from `plain_text` when text is requested. The document stays in the caselaw register.

### CourtListener dockets

`ipfs_datasets_py/processors/legal_data/courtlistener_ingestion.py` assigns no schema version and writes no court table.

```python
COURTLISTENER_API_ROOT = "https://www.courtlistener.com/api/rest/v4/"
```

Docket fetches use `dockets/{docket_id}/` under that root. The payload is a docket, with `documents`. Court identity on that payload is:

- `court`, the first present docket field among `court_id`, `court_name`, `court_full_name`, and `court`
- `metadata["court_id"]` from `court_id`
- `metadata["court_name"]` from `court_name` or `court_full_name`

`_normalize_courtlistener_court_reference` turns a CourtListener court URL into the last path segment:

```python
match = re.search(r"/courts/(?P<court_id>[^/]+)/?$", text)
```

If the value is not such a URL, the function returns the original string. `metadata["docket_number"]` and `metadata["pacer_case_id"]` stay case identifiers. Do not copy `docket_id` or `pacer_case_id` into a court row.
