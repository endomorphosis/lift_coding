# Regulation schema register

Register for the five regulation sources named by LCM-004. Each section keeps that source's version string or record fields. The sections stay separate from each other and from `country-laws-ir-graphrag/v1`. This file does not assign `worldwide-legal-search.law-source@1`. That string does not appear in the modules quoted below. This file does not edit the datasets checkout.

Read on 2026-11-09 from the training checkout `external/ipfs_datasets`. `git rev-parse HEAD` is `d40ab60649b83781e3849e191c1f2ac8545b042f`. `git status --short` printed no lines for the files quoted below.

`cfr_annual_processor.py` and `ecfr_crosscheck_processor.py` last changed in `e63549e2d337a1b6cb4c6b35d7caff28272e1cdf`. `live_cfr_source_processor.py` last changed in `11434fe73063640ee9b8137a91650dc0b31fb467`. `federal_register_scraper.py`, `regulation_version_tracker.py`, and `state_admin_rules_scraper.py` last changed in `df93e91e6338c84a17c3208ef68b88de8566f78c`. `federal_register_change_processor.py` last changed in `21269c0161ae22de9746a6801b1b25f507dc073d`. `federal_register_release_schema.py` last changed in `348bd7a0d8c216c676f2a5b6c0b9ed933925a976`. `patent_authority_sources.py` last changed in `8dc497d9232c5b332e7633339f736c417d56a280`. `country_laws_ir/__init__.py` last changed in `9df09d3f50b80beebd5ae8bcd83cf72d034078c2`.

The statute schema, from `ipfs_datasets_py/processors/legal_scrapers/country_laws_ir/__init__.py`, is a different assignment:

```python
SCHEMA_VERSION = "country-laws-ir-graphrag/v1"
```

CFR, eCFR, and the Federal Register change processor import a different authority schema from `ipfs_datasets_py/processors/legal_data/patent_authority_sources.py`:

```python
SCHEMA_VERSION = "patent-authority-sources-v1"
```

That import is bound as `AUTHORITY_SCHEMA_VERSION`. It is not a regulation id and it is not `country-laws-ir-graphrag/v1`.

## CFR

`ipfs_datasets_py/processors/legal_scrapers/federal_scrapers/cfr_annual_processor.py` acquires official annual Title 37 CFR packages from GovInfo. The module says official annual identity is never conflated with eCFR unofficial presentation. It has no column tuple. The record contract is `CfrSectionRecord`, serialized by `to_dict`.

```python
SCHEMA_VERSION = "cfr-annual-processor-v1"
FIXTURE_SCHEMA_VERSION = "cfr-annual-fixture-v1"
```

```python
DEFAULT_TITLE = "37"
```

`CfrSectionRecord.to_dict` writes these keys:

```python
        return {
            "citation": self.citation,
            "formats": {k: v.to_dict() for k, v in sorted(self.formats.items())},
            "heading": self.heading,
            "metadata": _deep_sorted(dict(self.metadata)),
            "package_id": self.package_id,
            "part": self.part,
            "section": self.section,
            "stable_id": self.stable_id,
            "status": self.status.value,
            "text_excerpt": self.text_excerpt,
            "title": self.title,
            "year": self.year,
        }
```

`CfrAnnualAcquisition.to_dict` writes `authority_source`, `ecfr_presentation_sha256`, `failures`, `metadata`, `notes`, `package`, `receipt`, `schema_version` (`SCHEMA_VERSION`, which is `cfr-annual-processor-v1`), `sections`, `status`, `title`, and `unknown_reason`. `identities_remain_separate` returns true when the official package hash and `ecfr_presentation_sha256` differ, and also when either value is absent.

`ipfs_datasets_py/processors/legal_scrapers/federal_scrapers/live_cfr_source_processor.py` is a separate CFR module, still Title 37. It keeps annual GovInfo acquisitions and eCFR acquisitions in separate mappings.

```python
SCHEMA_VERSION = "live-cfr-source-processor-v1"
FIXTURE_SCHEMA_VERSION = "live-cfr-recipe-v1"
```

`LiveCfrProvision` fields, in class order:

```python
    stable_id: str
    title: str
    section: str
    source_cid: str
    source_span: SourceSpan
    effective_interval: EffectiveInterval
    authority_status: AuthorityStatus
    authentication_status: AuthenticationStatus
    citation: Optional[str] = None
    heading: Optional[str] = None
    text_excerpt: Optional[str] = None
    content_sha256: Optional[str] = None
    source_url: Optional[str] = None
    package_id: Optional[str] = None
    granule_id: Optional[str] = None
    version_id: Optional[str] = None
    provider: str = PROVIDER_GOVINFO
    part: Optional[str] = None
    change_kind: ProvisionChangeKind = ProvisionChangeKind.UNCHANGED
    media_type: str = "application/xml"
    acquisition_receipt_cid: Optional[str] = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
```

The class docstring says authority status and authentication status stay separate. `LiveCfrAcquisitionReport` stores `ecfr_acquisitions` and `annual_acquisitions` as two mappings and sets `schema_version` to `SCHEMA_VERSION` (`live-cfr-source-processor-v1`).

`cfr-annual-processor-v1` and `live-cfr-source-processor-v1` are not `country-laws-ir-graphrag/v1`. A CFR section record is not stored as that statute schema.

## eCFR

`ipfs_datasets_py/processors/legal_scrapers/federal_scrapers/ecfr_crosscheck_processor.py` says every admitted record carries `authority_tier=unofficial-current` and `IdentityRole.DERIVED_PRESENTATION`, and that eCFR text must never impersonate an official annual CFR or GovInfo artifact. Default title is `"37"`. There is no column tuple. The record contract is `EcfrSectionRecord`.

```python
SCHEMA_VERSION = "ecfr-crosscheck-processor-v1"
FIXTURE_SCHEMA_VERSION = "ecfr-crosscheck-fixture-v1"
```

`EcfrSectionRecord.to_dict` writes these keys:

```python
        return {
            "amendment": None if self.amendment is None else self.amendment.to_dict(),
            "citation": self.citation,
            "content_kind": self.content_kind.value,
            "content_sha256": self.content_sha256,
            "heading": self.heading,
            "media_type": self.media_type,
            "metadata": _deep_sorted(dict(self.metadata)),
            "part": self.part,
            "section": self.section,
            "source_url": self.source_url,
            "stable_id": self.stable_id,
            "status": self.status.value,
            "text_excerpt": self.text_excerpt,
            "title": self.title,
            "up_to_date_as_of": _date_to_str(self.up_to_date_as_of),
            "version_id": self.version_id,
        }
```

`AmendmentMeta.to_dict` writes `amendatory_action`, `authority_citation`, `effective_date`, `fr_citation`, `notes`, `publication_date`, and `source_citation`. `EcfrVersionPoint` is the version record. Its fields, in class order, are `up_to_date_as_of`, `title`, `provider`, `version_id`, `content_sha256`, `source_url`, `structure_url`, `full_xml_url`, `versions_url`, `retrieved_at`, `is_current_snapshot`, and `metadata`. `version_identity` returns this string:

```python
def version_identity(*, title: Any, up_to_date_as_of: date) -> str:
    """Concrete version identity string (never ``latest``)."""

    t = normalize_title(title)
    return f"ecfr-title-{t}-as-of-{up_to_date_as_of.isoformat()}"
```

`EcfrVersionPoint.__post_init__` calls `reject_hard_coded_latest` on that version id. The rejection is on the version record, not inside `version_identity`.

`ecfr-crosscheck-processor-v1` is not `cfr-annual-processor-v1` and not `country-laws-ir-graphrag/v1`.

## Federal Register

`ipfs_datasets_py/processors/legal_scrapers/federal_scrapers/federal_register_scraper.py` assigns no `SCHEMA_VERSION`. The record contract is the dict returned by `_normalize_document`. The docstring calls that dict the scraper output schema.

```python
    return {
        "document_number": result.get("document_number", ""),
        "title": result.get("title", ""),
        "agency": agency_names[0] if agency_names else "",
        "agencies": agency_names,
        "agency_abbr": agency_slugs[0] if agency_slugs else "",
        "agency_abbrs": agency_slugs,
        "document_type": result.get("type", ""),
        "publication_date": result.get("publication_date", ""),
        "abstract": result.get("abstract", "")[:500] if result.get("abstract") else "",
        "citation": result.get("citation", ""),
        "fr_url": result.get("html_url", ""),
        "pdf_url": result.get("pdf_url", ""),
        "raw_text_url": result.get("raw_text_url", ""),
        "signing_date": result.get("signing_date", ""),
        "effective_date": result.get("effective_on") or result.get("effective_date") or "",
        "docket_ids": result.get("docket_ids", []),
        "regulation_id_numbers": result.get("regulation_id_numbers", []),
        "topics": result.get("topics", []),
        "significant": result.get("significant", False),
    }
```

`ipfs_datasets_py/processors/legal_scrapers/federal_scrapers/federal_register_change_processor.py` is a different contract. The module says FederalRegister.gov discovery text is `authority_tier=unofficial-current` with `IdentityRole.DERIVED_PRESENTATION` and never masquerades as an official edition or GovInfo artifact.

```python
SCHEMA_VERSION = "federal-register-change-processor-v1"
FIXTURE_SCHEMA_VERSION = "federal-register-change-fixture-v1"
```

`RuleChangeRecord` fields, in class order:

```python
    document_number: str
    document_type: RuleDocumentType
    title: str
    publication_date: Optional[date] = None
    effective_date: Optional[date] = None
    compliance_date: Optional[date] = None
    termination_date: Optional[date] = None
    delayed_effective_date: Optional[date] = None
    agencies: tuple[str, ...] = ()
    citation: Optional[str] = None
    fr_citation: Optional[str] = None  # e.g. 89 FR 12345
    cfr_references: tuple[str, ...] = ()
    text_excerpt: Optional[str] = None
    discovery: Optional[DiscoveryDocument] = None
    govinfo_package_id: Optional[str] = None
    govinfo_granule_id: Optional[str] = None
    official_artifact: Optional[ArtifactIdentity] = None
    derived_presentation: Optional[ArtifactIdentity] = None
    signature: Optional[SignatureEvidence] = None
    verification_state: VerificationState = VerificationState.UNVERIFIED
    verification_status: Optional[str] = None
    verification_failure: Optional[Mapping[str, Any]] = None
    is_binding: bool = False
    withdrawn: bool = False
    corrects: Optional[str] = None
    withdraws: Optional[str] = None
    delays: Optional[str] = None
    amends: Optional[str] = None
    relations: tuple[ChangeEdge, ...] = ()
    receipt: Optional[SourceReceipt] = None
    status: ResolutionStatus = ResolutionStatus.RESOLVED
    metadata: Mapping[str, Any] = field(default_factory=dict)
```

`official_artifact` and `derived_presentation` are separate fields.

A further schema lives outside `federal_scrapers`, in `ipfs_datasets_py/processors/legal_data/federal_register_release_schema.py`:

```python
SCHEMA_VERSION: Final = "federal-register-sparse-graphrag-release-schema-v2"
RELEASE_PROFILE: Final = "federal-register-ir-graphrag/v2"
```

That release schema is not the scraper dict, not `federal-register-change-processor-v1`, and not `country-laws-ir-graphrag/v1`. No version string was invented for `federal_register_scraper.py`.

## `regulation_version_tracker.py`

`ipfs_datasets_py/processors/legal_scrapers/regulation_version_tracker.py` assigns no `SCHEMA_VERSION`. The record contract is two dataclasses.

```python
@dataclass
class RegulationVersion:
    """A specific version of a regulation."""

    regulation_id: str
    version_id: str
    content: str
    effective_date: datetime
    end_date: Optional[datetime] = None
    title: str = ""
    source_url: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    content_hash: str = ""
```

```python
@dataclass
class RegulationChange:
    """Change between two regulation versions."""

    regulation_id: str
    from_version: str
    to_version: str
    from_date: datetime
    to_date: datetime
    change_type: str  # "added", "modified", "deleted"
    diff: str = ""
    summary: str = ""
```

`RegulationVersionTracker.versions` stores `Dict[str, List[RegulationVersion]]`. When `content_hash` is empty and `content` is present, `__post_init__` sets `content_hash` to the first 16 hex characters of SHA-256:

```python
            self.content_hash = hashlib.sha256(self.content.encode()).hexdigest()[:16]
```

That hash prefix is not a schema id. This record is not `country-laws-ir-graphrag/v1`.

## State admin-rules scrapers

`ipfs_datasets_py/processors/legal_scrapers/state_admin_rules_scraper.py` assigns no `SCHEMA_VERSION`. `scrape_state_admin_rules` says:

```python
    """Scrape state administrative rules for selected states.

    The scraper delegates network extraction to ``scrape_state_laws`` and then
    filters the normalized output to administrative-rule records only.
    """
```

The filter `_is_admin_rule_statute` reads `legal_area`, `code_name`, `section_name` or `short_title`, `official_cite`, `source_url`, `full_text`, and `structured_data` `code_type` or `type`. A selected row stays an administrative-rule record. This register does not relabel it as a statute and does not assign `country-laws-ir-graphrag/v1`.

The fallback JSON-LD object written for a selected row is:

```python
    payload: Dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "Legislation",
        "legislationType": "StateAdministrativeRule",
        "legislationJurisdiction": f"US-{state_code}",
        "name": title,
        "identifier": statute_id or title,
        "description": section_name or full_text[:500],
        "text": full_text or section_name,
        "url": source_url,
        "sourceUrl": source_url,
        "sectionNumber": section_number,
        "sectionName": section_name,
    }
```

`_enrich_admin_rule_structured_data` sets `structured_data["type"]` to `"regulation"` when that field is empty, and sets JSON-LD `legislationType` to `"StateAdministrativeRule"`. The in-memory list key remains `statutes` because the scraper filters rows that already use that key. The regulation tag is `structured_data["type"]` and `legislationType`, not `country-laws-ir-graphrag/v1` and not `worldwide-legal-search.law-source@1`.

Rows added on the agentic path use this shape:

```python
            statute = {
                "state_code": state_code,
                "state_name": state_name,
                "statute_id": f"{state_code}-AGENTIC-{section_number}",
                "code_name": f"{state_name} Administrative Rules (Agentic Discovery)",
                "section_number": section_number,
                "section_name": section_name,
                "short_title": section_name,
                "full_text": stored_text,
                "summary": stored_text[:500],
                "legal_area": "administrative",
                "source_url": doc_url,
                "official_cite": f"{state_code} Admin Rule {section_number}",
                "structured_data": {
                    "type": "regulation",
                    "agentic_discovery": True,
                    "relaxed_recovery": bool(relaxed_recovery),
                    "method_used": method_value,
                    "source_domain": urlparse(doc_url).netloc,
                },
            }
```

The paired `kg_rows` record is a different shape: `state_code`, `state_name`, `url`, `domain`, `title`, `text`, `method_used`, `query`, `source` (`"agentic_web_archiving"`), and `fetched_at`. That row is not the JSON-LD object and not `country-laws-ir-graphrag/v1`.

No schema version was invented for this scraper. The file's variable name `statute` is the name in the source. The selected row is an administrative rule.
