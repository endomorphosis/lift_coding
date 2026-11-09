# Caselaw schema register

Register for five caselaw sources. Each section keeps the schema id and the columns that source writes. The five column lists stay separate. This file does not edit the datasets checkout, start a GraphRAG build, or open a query route.

Read on 2026-11-09 from the training checkout `external/ipfs_datasets`. `git rev-parse HEAD` is `d40ab60649b83781e3849e191c1f2ac8545b042f`. `git status --short` printed no lines for the files quoted below.

`caselaw_access_program/vector_search_integration.py` and `recap_archive_scraper.py` last changed in `df93e91e6338c84a17c3208ef68b88de8566f78c`. `collect_fr_dila.py`, `collect_de_rii.py`, `catalog.py`, `upload.py`, `peachjam.py`, `br_stj.py`, `co_cc.py`, and `wayback_generic.py` last changed in `d40ab60649b83781e3849e191c1f2ac8545b042f`.

None of these modules assigns `SCHEMA_VERSION`. Each section below uses schema id `unversioned`.

## CAP

Schema id: `unversioned`.

Local reader: `ipfs_datasets_py/processors/legal_scrapers/caselaw_access_program/vector_search_integration.py`, class `CAPVectorSearchConfig`. The default dataset id is a Hub repo name, not a schema id:

```python
dataset_id: str = "justicedao/Caselaw_Access_Project_embeddings"
```

`_load_parquet_rows` copies each parquet row with `dict(row)`. The row keeps whatever columns that file has. The extractor then looks up names in this order.

Text, checked by `_extract_content` until one value is a non-empty string:

```python
text_field_candidates: Tuple[str, ...] = (
    "text",
    "content",
    "document",
    "opinion_text",
    "case_text",
    "summary",
    "title",
)
```

Embedding, checked by `_extract_embedding_vector` until one value becomes a non-empty float list. If none of these names is present, the same function scans `row.values()`:

```python
embedding_field_candidates: Tuple[str, ...] = (
    "embedding",
    "embeddings",
    "vector",
    "vectors",
    "centroid",
)
```

Chunk id, checked by `_extract_chunk_id` until one value has text. If none does, the id is `cap-row-{row_index}`:

```python
id_field_candidates: Tuple[str, ...] = (
    "chunk_id",
    "cid",
    "id",
    "case_id",
    "document_id",
)
```

Metadata priority, copied by `_extract_content` only when no text candidate hits, and also used as case-key candidates (`case_id`, `cid`, `citation`, `document_id`, `id`) in `_resolve_case_key`:

```python
metadata_priority_fields: Tuple[str, ...] = (
    "cid",
    "citation",
    "case_id",
    "court",
    "jurisdiction",
    "decision_date",
    "date",
    "docket_number",
    "reporter",
    "source",
    "cluster_id",
)
```

`_extract_metadata` copies every remaining key on the row and skips the embedding candidate names. Cluster parquet lookup also tries `cluster_id`, `cluster`, `id`, then `cids`, `content_ids`, `ids`. Those names are fallbacks for a second file. They are not a column order for the embedding rows.

`catalog.py` binds key `us-caselaw` to this module and to Hub ids `justicedao/caselaw_access_project`, `justicedao/ipfs_caselaw_access_project`, `justicedao/Caselaw_Access_Project_embeddings`, `justicedao/dedup_ipfs_caselaw_access_project`, and `endomorphosis/Caselaw_Access_Project_JSON`.

## DILA

Schema id: `unversioned`.

Local writer: `parse` in `ipfs_datasets_py/processors/legal_scrapers/national_collectors/collect_fr_dila.py`. `write_parquet` stores that dict with `pa.Table.from_pylist`. `existing_ids` reads the column `dila_id` back from staged parquet.

The request header is `JusticeDAO-caselaw-collector/0.1 (open-data research; ipfs_datasets_py)`. Dump names map to `config` here:

```python
FONDS = {"CASS": "fr_cass", "CAPP": "fr_capp", "JADE": "fr_jade", "CONSTIT": "fr_constit", "INCA": "fr_inca"}
```

Columns, in the order `parse` writes them: `ecli`, `jurisdiction`, `court`, `chamber`, `date`, `number`, `title`, `text`, `source_url`, `archive_name`, `is_archive`, `licence`, `retrieved_at`, `court_id`, `dila_id`, `config`.

```python
    return {
        "ecli": _t(root, ".//ECLI"),
        "jurisdiction": "FR",
        "court": _t(root, f"{meta}/JURIDICTION"),
        "chamber": _t(root, ".//FORMATION"),
        "date": _t(root, f"{meta}/DATE_DEC"),
        "number": _t(root, f"{meta}/NUMERO", ".//NUMEROS_AFFAIRES/NUMERO_AFFAIRE"),
        "title": _t(root, f"{meta}/TITRE"),
        "text": text,
        "source_url": url, "archive_name": archive, "is_archive": False,
        "licence": "Licence Ouverte 2.0",
        "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "court_id": None, "dila_id": _t(root, ".//META_COMMUN/ID"), "config": FONDS[fond],
    }
```

`text` is the concatenated text of `.//CONTENU`. The module docstring says this collector does not replace `collect_legi`.

## Rechtsprechung im Internet

Schema id: `unversioned`.

Local writer: `parse` in `ipfs_datasets_py/processors/legal_scrapers/national_collectors/collect_de_rii.py`. `flush` stores that dict with `pa.Table.from_pylist`.

The request header is `justicedao-caselaw-research/0.1 (Benjamin Barber; 0.5 req/s)`. `config` is the literal `de_bund`.

Columns, in the order `parse` writes them: `ecli`, `jurisdiction`, `court`, `chamber`, `date`, `number`, `title`, `text`, `source_url`, `archive_name`, `is_archive`, `licence`, `retrieved_at`, `court_id`, `rii_doknr`, `doctype`, `norm`, `config`.

```python
    return dict(
        ecli=field("ecli") or None,
        jurisdiction="de",
        court=court,
        chamber=field("spruchkoerper") or None,
        date=decided,
        number=field("aktenzeichen"),
        title=txt(document.find("titelzeile")) or (field("doktyp") + " " + field("aktenzeichen")).strip(),
        text="\n\n".join(parts),
        source_url=link,
        archive_name=None,
        is_archive=False,
        licence=LIC,
        retrieved_at=datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        court_id=None,
        rii_doknr=field("doknr"),
        doctype=field("doktyp"),
        norm=field("norm"),
        config="de_bund",
    )
```

`text` is built from these XML tags, in this order, when the tag has text: `leitsatz`, `sonstosatz`, `tenor`, `tatbestand`, `entscheidungsgruende`, `gruende`, `abwmeinung`, `sonstlt`. Those tags stay inside `text`. They are not extra columns.

`court` is `gertyp` plus `spruchkoerper`. `date` is `entsch-datum`, rewritten from `YYYYMMDD` to `YYYY-MM-DD` when the value has length 8.

This column list shares some names with DILA and then diverges. DILA writes `dila_id` and a `FONDS` config. This writer writes `rii_doknr`, `doctype`, `norm`, and `config="de_bund"`. Jurisdiction is `de` here and `FR` on DILA. The module docstring says this collector does not replace `collect_gii`.

## RECAP

Schema id: `unversioned`.

Local reader: `ipfs_datasets_py/processors/legal_scrapers/recap_archive_scraper.py`. The file assigns no schema version.

`search_recap_documents` calls `https://www.courtlistener.com/api/rest/v3/search/`. `get_recap_document` calls `https://www.courtlistener.com/api/rest/v3/recap-documents/{document_id}/`.

Search columns, in the order that function writes them: `id`, `docket_id`, `case_name`, `court`, `court_full_name`, `document_type`, `document_number`, `description`, `date_filed`, `page_count`, `pacer_doc_id`, `recap_url`, `docket_url`, `plain_text_available`, `pdf_available`, `ocr_status`, `abstract`.

```python
                    doc = {
                        "id": result.get("id", ""),
                        "docket_id": result.get("docket_id", ""),
                        "case_name": result.get("caseName", result.get("case_name", "")),
                        "court": result.get("court", court or ""),
                        "court_full_name": result.get("court_name", ""),
                        "document_type": document_type or "unknown",
                        "document_number": result.get("document_number", ""),
                        "description": result.get("description", result.get("snippet", "")),
                        "date_filed": result.get("dateFiled", result.get("date_filed", "")),
                        "page_count": result.get("page_count", 0),
                        "pacer_doc_id": result.get("pacer_doc_id", ""),
                        "recap_url": result.get("download_url", ""),
                        "docket_url": result.get("absolute_url", ""),
                        "plain_text_available": result.get("plain_text", "") != "",
                        "pdf_available": result.get("filepath_local", "") != "",
                        "ocr_status": result.get("ocr_status", "unknown"),
                        "abstract": result.get("snippet", "")[:500]
                        if result.get("snippet")
                        else "",
                    }
```

Detail columns, in the order `get_recap_document` writes them: `id`, `docket_id`, `case_name`, `court`, `document_type`, `date_filed`, `page_count`, `recap_url`, `text`, `metadata`.

`metadata`, when `include_metadata` is true, holds `pacer_doc_id`, `pacer_case_id`, `ocr_status`, `plain_text_available`, `pdf_available`, `description`, `document_number`, `docket_number`, `docket_url`, `court_id`, `court_full_name`.

```python
                document = {
                    "id": document_id,
                    "docket_id": data.get("docket", "") or hydrated.get("docket_id", ""),
                    "case_name": data.get("case_name", "") or hydrated.get("case_name", ""),
                    "court": court_value,
                    "document_type": data.get("document_type", ""),
                    "date_filed": data.get("date_filed", "") or hydrated.get("date_filed", ""),
                    "page_count": data.get("page_count", 0),
                    "recap_url": data.get("filepath_local", ""),
                    "text": data.get("plain_text", "") if include_text else None,
                    "metadata": {
                        "pacer_doc_id": data.get("pacer_doc_id", ""),
                        "pacer_case_id": data.get("pacer_case_id", ""),
                        "ocr_status": data.get("ocr_status", ""),
                        "plain_text_available": data.get("plain_text", "") != "",
                        "pdf_available": data.get("filepath_local", "") != "",
                        "description": data.get("description", ""),
                        "document_number": data.get("document_number", ""),
                        "docket_number": hydrated.get("docket_number", ""),
                        "docket_url": hydrated.get("docket_url", "")
                        or data.get("absolute_url", ""),
                        "court_id": hydrated.get("court_id", ""),
                        "court_full_name": hydrated.get("court_full_name", "") or court_value,
                    }
                    if include_metadata
                    else None,
```

`scrape_recap_archive` copies the detail record onto the search row with `doc.update(doc_details["document"])`. That merge leaves both key sets on one dict. It does not declare one column order for search and detail.

## world caselaw

Schema id: `unversioned`.

Local writers live under `hub_integrated/world_law_pipeline/scrapers/caselaw/amea/`. `upload.py` names the Hub repo and assigns no schema version:

```python
REPO="endomorphosis/world_caselaw"
```

`peachjam.py` is the only file in this set that names a version, and only in the module docstring:

```python
"""Peachjam (AfricanLII) judgment scraper -> world_caselaw schema v1.0 jsonl.
```

That line is not a `SCHEMA_VERSION` assignment. `br_stj.py`, `co_cc.py`, and `wayback_generic.py` do not repeat it.

`peachjam.py` `build_row` writes these keys, in order: `id`, `court`, `court_id`, `jurisdiction_cc`, `place_id`, `decision_date`, `case_number`, `parties`, `judges`, `citation`, `text`, `source_url`, `license`, `site_policy`, `language`, `title`, `source`, `retrieved_at`, `x_akn_frbr_uri`, `x_text_status`.

```python
    return {
        "id": f"{src}:{url.split('/akn/')[-1]}", "court": court, "court_id": cmap.lookup(court, cc, url.split('/akn/')[0]),
        "jurisdiction_cc": cc, "place_id": None, "decision_date": parse_date(m.get("Judgment date", "")),
        "case_number": m.get("Case number"), "parties": parties, "judges": m.get("Judges"),
        "citation": m.get("Media Neutral Citation") or m.get("Citation"), "text": text, "source_url": fetch_url,
        "license": license_, "site_policy": policy, "language": (m.get("Language") or "").lower()[:2] or None,
        "title": title, "source": src, "retrieved_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "x_akn_frbr_uri": "/akn/" + url.split("/akn/")[-1], "x_text_status": "ok" if text else "no-text-on-source",
    }
```

`br_stj.py`, `co_cc.py`, and `wayback_generic.py` write the same keys through `retrieved_at`, then their own extra keys.

`br_stj.py` adds `x_date_kind`, `x_doc_type`, `x_registro`, `x_teor`, `x_assuntos`, `x_metadata_url`:

```python
                buf.append({"id":f"{SRC}:{sq}","court":"Superior Tribunal de Justiça","court_id":"br-national-supreme-stj","jurisdiction_cc":"br","place_id":None,
                 "decision_date":m.get("dataPublicacao"),"case_number":re.sub(r"\s+"," ",m.get("processo") or "") or None,"parties":None,
                 "judges":[m["NM_MINISTRO"]] if m.get("NM_MINISTRO") else None,"citation":None,"text":txt,"source_url":zips[d],
                 "license":"CC-BY-4.0","site_policy":"open-license;robots-allowed","language":"pt","title":f'{m.get("tipoDocumento")} {m.get("processo")}',
                 "source":SRC,"retrieved_at":datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                 "x_date_kind":"publication","x_doc_type":m.get("tipoDocumento"),"x_registro":m.get("numeroRegistro"),"x_teor":m.get("teor"),"x_assuntos":m.get("assuntos"),"x_metadata_url":meta[d]})
```

`co_cc.py` adds `x_proceso`, `x_expediente`, `x_sala`, `x_metadata_source`, `x_text_status`:

```python
            buf.append({"id":f"{SRC}:{s}","court":"Corte Constitucional","court_id":"co-corte-constitucional","jurisdiction_cc":"co","place_id":None,
              "decision_date":date,"case_number":s,"parties":None,"judges":[m["magistrado_a"]] if m.get("magistrado_a") else None,"citation":f"Sentencia {s}",
              "text":txt,"source_url":url or "https://www.datos.gov.co/resource/v2k4-2t8s","license":"unknown","site_policy":"robots-allowed",
              "language":"es","title":f'Sentencia {s} ({m.get("proceso")})',"source":SRC,"retrieved_at":datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
              "x_proceso":m.get("proceso"),"x_expediente":f'{m.get("expediente_tipo")}{m.get("expediente_numero")}',"x_sala":m.get("sala"),
              "x_metadata_source":"https://www.datos.gov.co/d/v2k4-2t8s","x_text_status":"ok" if txt else "not-found"})
```

`wayback_generic.py` adds `x_original_url`, `x_key`:

```python
        buf.append({"id": f"{a.src}:{key}", "court": court, "court_id": cid, "jurisdiction_cc": a.cc, "place_id": None, "decision_date": date,
            "case_number": cn, "parties": parties, "judges": None, "citation": cit, "text": txt, "source_url": fetch, "license": a.license or "unknown",
            "site_policy": pol, "language": a.lang, "title": title, "source": a.src,
            "retrieved_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "x_original_url": orig, "x_key": key})
```

Those extra keys stay on the writer that emits them. Peachjam's `x_akn_frbr_uri` is not a column of the STJ, Colombia, or Wayback rows.

## Separate column lists

An adapter keeps five column lists:

- CAP candidate names, with every other non-embedding key copied from the parquet row.
- DILA's 16 keys ending in `dila_id` and `config`.
- Rechtsprechung im Internet's 18 keys ending in `rii_doknr`, `doctype`, `norm`, and `config`.
- RECAP search keys and RECAP detail keys, including the nested `metadata` object.
- `endomorphosis/world_caselaw` keys through `retrieved_at`, plus the extra keys of the writer that produced the row.

No one of those lists is the column order of the other four.
