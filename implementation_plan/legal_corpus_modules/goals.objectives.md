# Legal corpus modules goal bootstrap

Root, goals, and subgoals are planning records. Completion is not these status fields. This package is not admitted to a DuckDB board. `PLAN.md` is the contract.

## LCM-G000 Reorganize legal data into versioned modules
- Status: planned
- Parent goal ids json: []
- Required task ids json: ["LCM-000", "LCM-001", "LCM-002", "LCM-003", "LCM-004", "LCM-005", "LCM-006", "LCM-007", "LCM-008", "LCM-009", "LCM-010", "LCM-011", "LCM-012", "LCM-013", "LCM-014", "LCM-015", "LCM-016", "LCM-017", "LCM-018", "LCM-020", "LCM-021", "LCM-022", "LCM-023", "LCM-024", "LCM-025", "LCM-026", "LCM-030", "LCM-031", "LCM-032", "LCM-033", "LCM-034", "LCM-035", "LCM-036", "LCM-037", "LCM-038", "LCM-039", "LCM-040", "LCM-041", "LCM-042", "LCM-043", "LCM-050", "LCM-051", "LCM-052", "LCM-053", "LCM-060", "LCM-061", "LCM-062", "LCM-063", "LCM-064", "LCM-065", "LCM-066", "LCM-067", "LCM-070", "LCM-071", "LCM-072", "LCM-073", "LCM-074", "LCM-075", "LCM-080", "LCM-081", "LCM-082", "LCM-083"]
- Objective: Legal datasets are reached through versioned instrument modules, each ingest path keeps the source schema it was built for, each display module names the versions it can show, and the docs describe the tree after that reorganization.
- Acceptance: Every required task has a receipt that quotes the landed file, version string, and validation command. Closed routes, the explicit-place query, and the existing statute and municipal schemas still mean what `PLAN.md` says they mean.
- Board namespace: legal-corpus-modules-v1
- Completion authority: not admitted; a future named admission may bind a native checker, and until then a human accepts the receipt

## LCM-G010 Record the contracts that already exist
- Status: planned
- Parent goal ids json: ["LCM-G000"]
- Required task ids json: ["LCM-000", "LCM-001", "LCM-002", "LCM-003", "LCM-004", "LCM-005", "LCM-006", "LCM-007", "LCM-008", "LCM-009", "LCM-082"]
- Objective: The statute, municipal, pipeline, caselaw, regulation, legislative-act, court, copy-tree, UI, and doc surfaces are inventoried from the checkout named in `PLAN.md`.
- Acceptance: Each inventory names files, version strings, and column lists it read. None of them edit those sources.
- Board namespace: legal-corpus-modules-v1
- Completion authority: not admitted

## LCM-G010.S1 Baseline and non-admission
- Status: planned
- Parent goal ids json: ["LCM-G010"]
- Required task ids json: ["LCM-000", "LCM-082"]
- Objective: Record the published tips and prove this plan is not wired into the worldwide supervisor.
- Acceptance: `LCM-000` and `LCM-082` receipts exist and name the live supervisor config path they checked.
- Board namespace: legal-corpus-modules-v1
- Completion authority: not admitted

## LCM-G010.S2 Instrument schema inventory
- Status: planned
- Parent goal ids json: ["LCM-G010"]
- Required task ids json: ["LCM-001", "LCM-002", "LCM-003", "LCM-004", "LCM-005", "LCM-006"]
- Objective: Confirm or correct the pinned schemas for laws, municipal HTML, the pipeline, caselaw, regulations, legislative acts, and courts.
- Acceptance: Six inventory receipts, each either matching `PLAN.md` or listing the drifted lines.
- Board namespace: legal-corpus-modules-v1
- Completion authority: not admitted

## LCM-G010.S3 Copies, interfaces, and existing docs
- Status: planned
- Parent goal ids json: ["LCM-G010"]
- Required task ids json: ["LCM-007", "LCM-008", "LCM-009"]
- Objective: Map duplicate scraper trees, the 17 note files, the SkillCenter outliers, the site and SwissKnife display surfaces, and the docs that will go stale.
- Acceptance: Three receipts. The UI receipt does not invent a SwissKnife legal schema that the files do not export.
- Board namespace: legal-corpus-modules-v1
- Completion authority: not admitted

## LCM-G020 Add versioned instrument interfaces
- Status: planned
- Parent goal ids json: ["LCM-G000"]
- Required task ids json: ["LCM-010", "LCM-011", "LCM-012", "LCM-013", "LCM-014", "LCM-015", "LCM-016", "LCM-017", "LCM-018", "LCM-020", "LCM-021", "LCM-022", "LCM-023", "LCM-024", "LCM-025", "LCM-026"]
- Objective: One shared instrument interface and one module per kind, each pinning the source schema it wraps.
- Acceptance: `legal-corpus.instrument@1` imports, and each kind module exports its own schema id without changing `document_role.ROLES` or `LawStatus`.
- Board namespace: legal-corpus-modules-v1
- Completion authority: not admitted

## LCM-G020.S1 Per-kind schema registers
- Status: planned
- Parent goal ids json: ["LCM-G020"]
- Required task ids json: ["LCM-010", "LCM-011", "LCM-012", "LCM-013", "LCM-014", "LCM-015", "LCM-016", "LCM-017"]
- Objective: Turn inventories into registers that name the source schema id, version, columns, and dataset each adapter must match.
- Acceptance: Eight register files, written in separate paths, with no shared file edited by more than one of these tasks.
- Board namespace: legal-corpus-modules-v1
- Completion authority: not admitted

## LCM-G020.S2 Kind modules
- Status: planned
- Parent goal ids json: ["LCM-G020"]
- Required task ids json: ["LCM-018", "LCM-020", "LCM-021", "LCM-022", "LCM-023", "LCM-024", "LCM-025", "LCM-026"]
- Objective: Land the shared interface and the law, regulation, legislative-act, caselaw, court, municipal, and status modules.
- Acceptance: Each module file exports the version named in its register. Status uses the existing `LawStatus` words.
- Board namespace: legal-corpus-modules-v1
- Completion authority: not admitted

## LCM-G030 Match ingest to each source schema
- Status: planned
- Parent goal ids json: ["LCM-G000"]
- Required task ids json: ["LCM-030", "LCM-031", "LCM-032", "LCM-033", "LCM-034", "LCM-035", "LCM-036", "LCM-037", "LCM-038", "LCM-039", "LCM-040", "LCM-041", "LCM-042", "LCM-043"]
- Objective: Each source family has an adapter that validates the source schema and records that schema id on the way in.
- Acceptance: Adapter tests round-trip a fixture of the source columns. They do not flatten caselaw, regulations, acts, laws, and courts into one table.
- Board namespace: legal-corpus-modules-v1
- Completion authority: not admitted

## LCM-G030.S1 Law and municipal ingest
- Status: planned
- Parent goal ids json: ["LCM-G030"]
- Required task ids json: ["LCM-030", "LCM-031", "LCM-032", "LCM-035"]
- Objective: Wrap country-laws IR, the 19-column municipal schema, pipeline `1.2.0`, and the US Code as law rather than as an act.
- Acceptance: The four adapters name the schema versions in `PLAN.md` and leave `query.py` shard lookup in place.
- Board namespace: legal-corpus-modules-v1
- Completion authority: not admitted

## LCM-G030.S2 Regulation, act, caselaw, and court ingest
- Status: planned
- Parent goal ids json: ["LCM-G030"]
- Required task ids json: ["LCM-033", "LCM-034", "LCM-036", "LCM-037", "LCM-038", "LCM-039", "LCM-040"]
- Objective: Separate adapters for CFR and register data, legislative acts, four caselaw sources, and court identity.
- Acceptance: DILA does not replace LEGI. Rechtsprechung im Internet does not replace GII. A court row is not stored as an opinion.
- Board namespace: legal-corpus-modules-v1
- Completion authority: not admitted

## LCM-G030.S3 Closed routes, notes, and outliers
- Status: planned
- Parent goal ids json: ["LCM-G030"]
- Required task ids json: ["LCM-041", "LCM-042", "LCM-043"]
- Objective: Keep closed national routes closed, quarantine the 17 non-Python notes, and leave the SkillCenter `v3` copies unmoved.
- Acceptance: Catalog lookups for Belgium, Portugal, Lithuania, and Ghana still do not gain statute routes. The note files are unchanged on disk.
- Board namespace: legal-corpus-modules-v1
- Completion authority: not admitted

## LCM-G040 Give the copies one module boundary
- Status: planned
- Parent goal ids json: ["LCM-G000"]
- Required task ids json: ["LCM-050", "LCM-051", "LCM-052", "LCM-053"]
- Objective: One canonical package re-exports the versioned modules. Duplicate trees get a boundary record and a retirement list.
- Acceptance: No duplicate tree is deleted. The retirement list names paths and the canonical module that would replace each group.
- Board namespace: legal-corpus-modules-v1
- Completion authority: not admitted

## LCM-G040.S1 Canonical package index
- Status: planned
- Parent goal ids json: ["LCM-G040"]
- Required task ids json: ["LCM-050"]
- Objective: Export the landed kind and adapter versions from one new index module.
- Acceptance: Importing the index reports every kind version and does not import the 17 note files.
- Board namespace: legal-corpus-modules-v1
- Completion authority: not admitted

## LCM-G040.S2 Duplicate-tree boundaries
- Status: planned
- Parent goal ids json: ["LCM-G040"]
- Required task ids json: ["LCM-051", "LCM-052", "LCM-053"]
- Objective: Record how `hub_dataset_scripts`, `hub_integrated`, and `international/harvested` point at the canonical modules.
- Acceptance: Three boundary files in three directories. Existing scraper bytes in those trees stay as they are.
- Board namespace: legal-corpus-modules-v1
- Completion authority: not admitted

## LCM-G050 Version the interfaces that display the modules
- Status: planned
- Parent goal ids json: ["LCM-G000"]
- Required task ids json: ["LCM-060", "LCM-061", "LCM-062", "LCM-063", "LCM-064", "LCM-065", "LCM-066", "LCM-067"]
- Objective: Site and SwissKnife views name the instrument versions they render and refuse an unknown version.
- Acceptance: `law-source@1` still means a statute-shaped law record. Caselaw, regulation, act, court, and municipal views use new schema ids.
- Board namespace: legal-corpus-modules-v1
- Completion authority: not admitted

## LCM-G050.S1 Display contract
- Status: planned
- Parent goal ids json: ["LCM-G050"]
- Required task ids json: ["LCM-060"]
- Objective: One display contract lists kind view ids, the instrument versions each view accepts, and the explicit-place query rule.
- Acceptance: The contract cites `legal-corpus.instrument@1` and does not add a GEOIP field.
- Board namespace: legal-corpus-modules-v1
- Completion authority: not admitted

## LCM-G050.S2 Site views
- Status: planned
- Parent goal ids json: ["LCM-G050"]
- Required task ids json: ["LCM-061", "LCM-062", "LCM-063", "LCM-064", "LCM-065", "LCM-067"]
- Objective: Add or declare site view modules for law, caselaw, regulation, legislative act, court, and municipal HTML.
- Acceptance: Each view file exports its schema id and the instrument versions it accepts. Jurisdiction `SCHEMA_VERSION` stays `1`.
- Board namespace: legal-corpus-modules-v1
- Completion authority: not admitted

## LCM-G050.S3 SwissKnife views
- Status: planned
- Parent goal ids json: ["LCM-G050"]
- Required task ids json: ["LCM-066"]
- Objective: Add a SwissKnife package that renders the same view ids.
- Acceptance: The package lives under SwissKnife source, exports the same schema ids as the site contract, and does not edit the live visual-functional board.
- Board namespace: legal-corpus-modules-v1
- Completion authority: not admitted

## LCM-G060 Document the tree that the refactor produced
- Status: planned
- Parent goal ids json: ["LCM-G000"]
- Required task ids json: ["LCM-070", "LCM-071", "LCM-072", "LCM-073", "LCM-074", "LCM-075", "LCM-080", "LCM-081", "LCM-083"]
- Objective: After the modules, adapters, boundaries, and views land, rewrite the docs so they describe those files and only those files.
- Acceptance: A drift check fails when a documented version, column list, or path disagrees with the file. The worldwide board still does not contain these task ids.
- Board namespace: legal-corpus-modules-v1
- Completion authority: not admitted

## LCM-G060.S1 Docs written from landed code
- Status: planned
- Parent goal ids json: ["LCM-G060"]
- Required task ids json: ["LCM-070", "LCM-071", "LCM-072", "LCM-073", "LCM-074"]
- Objective: Write interface, adapter, UI, and module-map docs from the files on disk, and mark older reports as historical.
- Acceptance: Every version string in the new docs is copied from the source file it cites. Historical banners do not delete the old reports.
- Board namespace: legal-corpus-modules-v1
- Completion authority: not admitted

## LCM-G060.S2 Drift check and campaign guards
- Status: planned
- Parent goal ids json: ["LCM-G060"]
- Required task ids json: ["LCM-075", "LCM-080", "LCM-081", "LCM-083"]
- Objective: Check version agreement, closed routes, the explicit-place query, and non-admission after the docs exist.
- Acceptance: The four checks exit 0 on the landed tree. A failure names the file and the mismatched string.
- Board namespace: legal-corpus-modules-v1
- Completion authority: not admitted
