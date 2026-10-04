# JusticeDAO Hugging Face Inventory

Inventory date: **2026-08-16 UTC**  
Organization: [`justicedao`](https://huggingface.co/justicedao)  
Scope: public Hugging Face datasets relevant to source corpora, IR/retrieval artifacts, and legal-IR checkpoints for `ProofGroundedIRLearningFabric`.

The Hugging Face organization API returned **21 public dataset repositories and no model repositories**. All 21 were public, ungated, and `disabled=false` when inspected. Counts below come from the Dataset Viewer/size API when it loaded successfully; otherwise they come from a pinned manifest and are marked accordingly. `Unknown` means the pinned Hub metadata did not establish the fact; it is not an inferred value.

## Admission summary

There is **no unconditional proof-grounded training admission** in the current organization snapshot:

- `patent-legal-ir-graphrag/corpus` is the strongest source-ingest candidate. It is content-addressed, Viewer-loadable, and source-bound, but its own card says `license: other`; an admitted campaign must bind the public-domain source-rights evidence and the exact component revisions below.
- `wetwijzer_netherlands_legal_corpus/laws` is Viewer-loadable and quality-audited, but source and transformation rights are unresolved (`license: other`) and parser/normalizer build revisions are absent. It is **no-go pending rights and build-identity repair**.
- BM25 postings, embeddings, graph nodes/edges, adjacency pages, index rows, translations, and repeated checkpoint states are derivatives. They may be auxiliary supervision but are never independent source examples.
- Every usable dataset configuration has only a `train` split. No repository supplies a lineage-safe train/development/calibration/test/hidden-test manifest.
- No repository publishes typed formal-logic examples, `FormalizationArtifact`, `DomainLogicSlice`, compiler/decompiler traces, proof grounding, tactic/hammer traces, kernel receipts, or checked counterexamples as a qualified dataset configuration.
- Broken Viewer layouts, corrupt Parquet, manifest/count inconsistencies, missing rights, and missing source pins are fail-closed conditions, not warnings to bypass.

## Exact Hub pinset

| Repository and immutable tree | Revision | Role | Card license | Viewer/load status | Campaign disposition |
|---|---|---|---|---|---|
| [`Caselaw_Access_Project_embeddings`](https://huggingface.co/datasets/justicedao/Caselaw_Access_Project_embeddings/tree/53389cbc04d51d5fae69236906c4314058a1f559) | `53389cbc04d51d5fae69236906c4314058a1f559` | Derived embedding clusters | `agpl-3.0` | Viewer explicitly disabled | Auxiliary quarantine; never count as cases |
| [`american_municipal_law`](https://huggingface.co/datasets/justicedao/american_municipal_law/tree/ec3e4457cb9ab7192db36b0292fd35bfbdc588aa) | `ec3e4457cb9ab7192db36b0292fd35bfbdc588aa` | Municipal/county source candidate plus derivatives | `mit` | Viewer explicitly disabled | No-go: exact rows/source rights/cutoff unknown |
| [`dedup_ipfs_caselaw_access_project`](https://huggingface.co/datasets/justicedao/dedup_ipfs_caselaw_access_project/tree/70db72d98d6b5581add8d62dfe5fea923af51b43) | `70db72d98d6b5581add8d62dfe5fea923af51b43` | Deduplicated/repair artifact | Unknown | Viewer fails: invalid Parquet footer | Reject as broken |
| [`ipfs_caselaw_access_project`](https://huggingface.co/datasets/justicedao/ipfs_caselaw_access_project/tree/32bb7493781dcc1245a64b59c5ad1fd6c47837f1) | `32bb7493781dcc1245a64b59c5ad1fd6c47837f1` | CAP case source projection | Unknown | Viewer passes | No-go pending rights, source revision, and lineage manifest |
| [`ipfs_uscode`](https://huggingface.co/datasets/justicedao/ipfs_uscode/tree/a9720a26a52251526035c2ca8cebea418965bcf9) | `a9720a26a52251526035c2ca8cebea418965bcf9` | U.S. Code retrieval release | `other` | Viewer config discovery fails | No-go until external load and rights are repaired |
| [`ipfs_state_laws`](https://huggingface.co/datasets/justicedao/ipfs_state_laws/tree/42f0546acc7c6cd55627eaf51fb820d5613b9021) | `42f0546acc7c6cd55627eaf51fb820d5613b9021` | State-law source plus embeddings | `other` | Viewer passes, manifest disagrees | No-go: stale manifest/count and rights gaps |
| [`ipfs_state_admin_rules`](https://huggingface.co/datasets/justicedao/ipfs_state_admin_rules/tree/42087d4600c497a908dce4901381b7f2dc046589) | `42087d4600c497a908dce4901381b7f2dc046589` | State administrative rules and embeddings | Unknown | First rows load; size/config fails | No-go: heterogeneous releases and missing rights |
| [`ipfs_federal_register`](https://huggingface.co/datasets/justicedao/ipfs_federal_register/tree/720668ae016cc400916dda884c9005e03618edfa) | `720668ae016cc400916dda884c9005e03618edfa` | Federal Register API metadata | Unknown | Feature/size extraction fails | No-go; no full text and no rights manifest |
| [`ipfs_court_rules`](https://huggingface.co/datasets/justicedao/ipfs_court_rules/tree/c4b34a54810561c75857f215ef6ed1d7d617c76f) | `c4b34a54810561c75857f215ef6ed1d7d617c76f` | Court-rule source plus embeddings | `other` | Viewer passes | Loadable but unqualified; source pins/rights missing |
| [`ipfs_netherlands_laws`](https://huggingface.co/datasets/justicedao/ipfs_netherlands_laws/tree/7fd7ba42d24c7f8f924ce69fe901f080e3ca4312) | `7fd7ba42d24c7f8f924ce69fe901f080e3ca4312` | Dutch law source/component release | `other` | Viewer passes | Conditional after rights/build repair |
| [`ipfs_netherlands_laws_vector_index`](https://huggingface.co/datasets/justicedao/ipfs_netherlands_laws_vector_index/tree/753b523ce06de6f207365df97358f8be616c75ba) | `753b523ce06de6f207365df97358f8be616c75ba` | Dutch vector derivative | `other` | Viewer passes | Auxiliary only |
| [`ipfs_netherlands_laws_bm25_index`](https://huggingface.co/datasets/justicedao/ipfs_netherlands_laws_bm25_index/tree/10ce83f4960e8d1a83c4e86d8a15db34806c5802) | `10ce83f4960e8d1a83c4e86d8a15db34806c5802` | Dutch BM25 derivative | `other` | Viewer passes | Auxiliary only |
| [`ipfs_netherlands_laws_knowledge_graph`](https://huggingface.co/datasets/justicedao/ipfs_netherlands_laws_knowledge_graph/tree/d10ca67e60f2d77e13d2a346d09430a973927a5e) | `d10ca67e60f2d77e13d2a346d09430a973927a5e` | Dutch graph derivative | `other` | Viewer passes | Auxiliary only |
| [`netherlands-laws-nl-normalized`](https://huggingface.co/datasets/justicedao/netherlands-laws-nl-normalized/tree/4070ab39856db63ea6a8e0e730b3b757ae32011a) | `4070ab39856db63ea6a8e0e730b3b757ae32011a` | Older normalized Dutch snapshot | `other` | Viewer passes | Historical/compatibility; same lineage groups |
| [`wetwijzer_netherlands_legal_corpus`](https://huggingface.co/datasets/justicedao/wetwijzer_netherlands_legal_corpus/tree/827e9412f55cbe332f18824ff669bdbbae39005d) | `827e9412f55cbe332f18824ff669bdbbae39005d` | Unified Dutch source plus derivatives | `other` | All nine configs pass | No-go pending rights/build pins; then conditional source ingest |
| [`legal-ir-autoencoder-checkpoints`](https://huggingface.co/datasets/justicedao/legal-ir-autoencoder-checkpoints/tree/94ca549d102e3e31781370aec1247f91365440eb) | `94ca549d102e3e31781370aec1247f91365440eb` | Legacy feature-state registry | `mit` | Size/first-rows fail | Artifact-only; not promotable evidence |
| [`patent-legal-corpus`](https://huggingface.co/datasets/justicedao/patent-legal-corpus/tree/86c77cb650d30ee366983d1b2e25cd85e8c22e34) | `86c77cb650d30ee366983d1b2e25cd85e8c22e34` | Patent source artifact registry | `cc0-1.0` | Declared Parquet absent; Viewer fails | Use pinned manifests only; repair layout |
| [`patent-legal-bm25`](https://huggingface.co/datasets/justicedao/patent-legal-bm25/tree/8d7f938a25a56a53d58d96d7f1cdde9f51eff694) | `8d7f938a25a56a53d58d96d7f1cdde9f51eff694` | Patent BM25 registry | `cc0-1.0` | Declared Parquet absent; Viewer fails | Auxiliary manifest only; repair layout |
| [`patent-legal-vectors`](https://huggingface.co/datasets/justicedao/patent-legal-vectors/tree/f215a9c115f2af1147b0fcbf2c047ec250cb54d7) | `f215a9c115f2af1147b0fcbf2c047ec250cb54d7` | Patent vector registry | `cc0-1.0` | Config discovery fails | Auxiliary manifest only; repair layout |
| [`patent-legal-knowledge-graph`](https://huggingface.co/datasets/justicedao/patent-legal-knowledge-graph/tree/f4ee31011dbd976b61f2f9144775ed9a12c16e62) | `f4ee31011dbd976b61f2f9144775ed9a12c16e62` | Patent graph registry | `cc0-1.0` | Config discovery fails | Auxiliary manifest only; repair layout |
| [`patent-legal-ir-graphrag`](https://huggingface.co/datasets/justicedao/patent-legal-ir-graphrag/tree/845669408081f1334c54519d2bb7df6bf780ccd5) | `845669408081f1334c54519d2bb7df6bf780ccd5` | Working source projection plus retrieval derivatives | `other` | All 16 configs pass | Conditional source-ingest candidate; derivatives auxiliary only |

## Patent legal release

### Working consolidated release

`patent-legal-ir-graphrag@845669408081f1334c54519d2bb7df6bf780ccd5` has schema `patent.public_legal_ir_hf_release/v1`, layout `publicus-ir-graphrag/v1`, corpus root `bafkreiak2bzrnblycry6t34kyusupep3nusxpptwlaffaz7glur3cpeiem`, and release root `bafkreidjgszp2welhobw42nhsvxebcjt7uugqsbufgzph46ghvj2r6vose`. Its pinned [`manifest.json`](https://huggingface.co/datasets/justicedao/patent-legal-ir-graphrag/blob/845669408081f1334c54519d2bb7df6bf780ccd5/manifest.json) and [`release-metadata.json`](https://huggingface.co/datasets/justicedao/patent-legal-ir-graphrag/blob/845669408081f1334c54519d2bb7df6bf780ccd5/release-metadata.json) bind the following train-only configurations:

| Config | File/pattern | Physical rows | Semantic role |
|---|---|---:|---|
| `corpus` | `data/corpus/*.parquet` | 2,174 | Source-bound document projections |
| `bm25_documents` | `data/bm25/documents/*.parquet` | 2,174 | Derived document statistics |
| `bm25_postings` | `data/bm25/postings/*.parquet` | 30,514 | Derived term rows containing 854,046 logical postings |
| `vectors` | `data/vectors/*.parquet` | 2,174 | Derived embeddings |
| `graph_nodes` | `data/graph/nodes/*.parquet` | 37,764 | Derived nodes, including 30,514 BM25 term nodes |
| `graph_edges` | `data/graph/edges/*.parquet` | 883,628 | Derived authority and term edges |
| `graph_incoming_adjacency` | `data/graph/adjacency/incoming/*.parquet` | 36,635 | Derived adjacency pages |
| `graph_outgoing_adjacency` | `data/graph/adjacency/outgoing/*.parquet` | 2,175 | Derived adjacency pages |
| `bm25_document_chunk_index` | `indexes/bm25_document_chunks.parquet` | 1 | Routing index |
| `bm25_keyword_index` | `indexes/bm25_keyword_shards.parquet` | 8 | Routing index |
| `corpus_chunk_index` | `indexes/corpus_chunks.parquet` | 1 | Routing index |
| `graph_edge_chunk_index` | `indexes/graph_edge_chunks.parquet` | 216 | Routing index |
| `graph_incoming_adjacency_index` | `indexes/graph_incoming_adjacency.parquet` | 9 | Routing index |
| `graph_node_chunk_index` | `indexes/graph_node_chunks.parquet` | 10 | Routing index |
| `graph_outgoing_adjacency_index` | `indexes/graph_outgoing_adjacency.parquet` | 1 | Routing index |
| `vector_meta_index` | `indexes/vector_chunks.parquet` | 1 | Routing index |

Core schemas are:

- `corpus`: `authority,citation,classification,document_cid,document_index,entry_cid,family,kind,partition,record_id,schema_version,section_id,source_cids,source_root_id,text,text_sha256,title`.
- `vectors`: `authority,dimension,document_index,embedding,entry_cid,family,has_embedding,kind,model_id,model_revision,node_cid,partition,record_id,schema_version,source_cids`.
- `graph_nodes`: `entry_cid,kind,label,node_cid,node_id,properties_json,schema_version,source_cids`.
- `graph_edges`: `edge_cid,edge_id,object_cid,relation,schema_version,source_cids,subject_cid,weight`.
- `bm25_postings`: `body_frequencies,corpus_frequency,document_frequency,document_indices,document_lengths,idf,posting_chunk_count,posting_chunk_index,schema_version,term,title_frequencies`.

Source composition and rights come from the pinned component [`coverage.json`](https://huggingface.co/datasets/justicedao/patent-legal-corpus/blob/86c77cb650d30ee366983d1b2e25cd85e8c22e34/coverage.json):

| Source root | Documents | Authority | Exact upstream revision | Current-through/cutoff | Source rights | Known gap |
|---|---:|---|---|---|---|---|
| `cfr-title37-annual-2024` | 1,246 | Regulation | `govinfo-CFR-2024-title37` | `2024-07-01` | `public-domain-US-government` | One catalog section lacks text |
| `mpep-mpep-9-r07.2022` | 746 | Guidance | `uspto-mpep-9-r07.2022` | `2022-07-01` | `public-domain-US-government` | Not binding law; section inventory disclosed as incomplete |
| `uscode-title35-2024` | 175 | Statute | `govinfo-2024-title35` | `2024-12-31` | `public-domain-US-government` | None declared |
| `uspto-guidance-pdfs-2024-07-17` | 7 | Guidance | `uspto-guidance-pdfs-2024-07-17` | `2024-07-17` | `public-domain-US-government` | Nonbinding; superseded editions may remain |

Parser identities are `patent.hub_index_package.v1` and `patent.public_legal_corpus.v1`. Embeddings are 256-dimensional `local-hashed-term-projection@1.0.0`; BM25 uses tokenizer `cvefixes-ascii-code-nfkc-casefold/v1`. The card reports 9/9 local retrieval rule cases and 13/13 integration tests, which qualify retrieval behavior only—not semantic preservation or proof authority.

### Broken component layouts

The four component repositories declare Parquet configs but contain JSONL under different paths. Their `dataset_infos.json` files report zero examples and the Viewer cannot load them. Their pinned manifests still provide useful immutable artifact facts:

| Repository | Declared train configs | Manifest-backed actual artifacts |
|---|---|---|
| `patent-legal-corpus@86c77cb...` | `applications,cfr,citations,claims,events,federal_register,office_actions,projected_rules,public_law,usc` | `data/corpus/documents/train.jsonl`, 2,174 documents |
| `patent-legal-bm25@8d7f938...` | `bm25_documents,bm25_postings` | 2,174 documents, 43,107 terms, 824,019 postings; `patent.public_legal_bm25.v1` |
| `patent-legal-vectors@f215a9c...` | `vector_chunk_index,vectors` | 2,174 vectors, dimension 256; `local-hashed-term-projection@1.0.0` |
| `patent-legal-knowledge-graph@f4ee310...` | `graph_edge_chunk_index,graph_edges,graph_node_chunk_index,graph_nodes` | 7,250 nodes, 29,582 edges; `patent.public_legal_graph.v1` |

The consolidated release rebuilt BM25 and the graph, so component and consolidated derived artifacts are different identities despite sharing the same corpus root.

## WetWijzer and Dutch components

`wetwijzer_netherlands_legal_corpus@827e9412f55cbe332f18824ff669bdbbae39005d` is a partial Dutch corpus, not a full-current-law claim. Its pinned [`dataset_manifest.json`](https://huggingface.co/datasets/justicedao/wetwijzer_netherlands_legal_corpus/blob/827e9412f55cbe332f18824ff669bdbbae39005d/dataset_manifest.json) reports a source snapshot date of `2026-04-11`, retrieval/build activity on `2026-06-27`, jurisdiction Netherlands, and language `nl`.

| Train config | File | Rows | Source/derived classification |
|---|---|---:|---|
| `laws` | `data/laws.parquet` | 4,999 | Source document records |
| `articles` | `data/articles.parquet` | 89,737 | Derived sections bound by `law_cid` |
| `cid_index` | `data/cid_index.parquet` | 94,736 | Derived identity index |
| `vector_index` | `indexes/vector/vector_mapping.parquet` | 94,736 | Derived embeddings |
| `bm25_documents` | `indexes/bm25/bm25_documents.parquet` | 94,736 | Derived document rows |
| `bm25_terms` | `indexes/bm25/bm25_terms.parquet` | 120,521 | Derived term/posting rows |
| `knowledge_graph_nodes` | `graph/kg_nodes.parquet` | 94,736 | Derived nodes |
| `knowledge_graph_edges` | `graph/kg_edges.parquet` | 89,737 | Derived edges |
| `logic_relationships` | `logic/logic_relationships.parquet` | 261,720 | Heuristic/derived relationships, not proofs |

Schema shapes and identity-bearing fields:

- `laws` has 46 fields covering jurisdiction/language, stable and version identifiers, title/text/source URLs, document type/citation, legal status, effective and validity dates, retrieval/status evidence, article-extraction diagnostics, metadata, CID, and content address.
- `articles` has 41 fields covering law/document/article version identifiers, citation and hierarchy, text, legal/effective status, retrieval evidence, `law_cid`, `cid`, and content address.
- `cid_index` has 15 lineage/status fields.
- `vector_index` has 22 fields including `source_cid`, `law_cid`, embedding, dimension, and row CID.
- `bm25_documents` has 22 fields including the same lineage/status bindings and document statistics; `bm25_terms` has `term,doc_freq,idf,postings_count,postings,term_row_cid`.
- Graph nodes have 16 lineage/status fields; edges have nine CID-bound fields.
- `logic_relationships` has 20 fields including source/target CIDs, relationship type, status, confidence, and derivation note. These labels do not establish logical equivalence.

Quality/audit status:

| Measure | Actual |
|---|---:|
| Discovered catalog identifiers | 42,956 |
| Complete | 5,000 |
| Verified law rows | 4,999 |
| Failed | 1 |
| Remaining | 37,956 |
| Coverage | 11.639817% |
| Integrity gate | Pass |
| Current quality gate | Pass |
| Duplicate article-text groups | 1,762 |
| Empty articles | 28 |
| Suspiciously short articles | 14,711 |
| Suspiciously long articles | 230 |
| Ambiguous packaged law status | 22 |

The vector build is TF-IDF plus truncated SVD, dimension 256, but no immutable model/code revision is declared. The graph root is `bafkreif7wvaltwab2lsb7qanno37ridzzyanshllnhsq3lqtosui5qx67u`; a graph-builder version is absent. Parser and normalization versions are absent. All cards use `license: other` with no sufficient source/transformation-rights statement, so training admission remains blocked.

The unified files match the component file SHA-256/CIDs, but the unified manifest does not embed the four Hub commits. The campaign must bind all four exact pins from the table. `netherlands-laws-nl-normalized@4070ab...` contains 151 law rows and 7,775 article rows; it is an older normalized snapshot, not another source population.

## Existing autoencoder checkpoint registry

The pinned [`checkpoint manifest`](https://huggingface.co/datasets/justicedao/legal-ir-autoencoder-checkpoints/blob/94ca549d102e3e31781370aec1247f91365440eb/checkpoints/20260630T221836Z/manifest.json) identifies:

| Field | Value |
|---|---|
| Checkpoint ID | `legal-ir-autoencoder-canonical-20260630T221836Z` |
| State SHA-256 | `7236de26bd3d7f8414ffa04805f1b6e8a8849f9e0103cec6edb4985b911658be` |
| State size | 398,209,746 bytes |
| Generalizable entries | 1,205,336 |
| Merge mode | `weighted_union` |
| Source/reviewed/deprecated runs | 10 / 24 / 14 |
| Source code commit | `4f8ec909c82504e64efd5572ca50c7fa2e4f92c0` |
| Source code status | Dirty (`workspace/hf_checkpoint_upload/` untracked) |
| Named source dataset | `justicedao/ipfs_uscode` |
| Source dataset revision/config/split | Unknown/missing |
| Compiler/decompiler/tokenizer identities | Unknown/missing |
| Proof/kernel evidence | Absent |

This is a `ModalAutoencoderTrainingState` feature-weight warm start, not a complete resumable neural checkpoint. Source architectures are mostly `legacy_dense_v1` or `legacy_unknown`; the published smoke runs use a single validation canary. Proof-bridge values are sentinels (`acceptance=-1`, proof-failure ratio and total loss `1e12`) and controlled-text reconstruction is zero. Classification: **legacy artifact-only; never promotion evidence**.

## Other U.S. releases

| Repository | Configs/counts and schema | Rights/currentness | Decision |
|---|---|---|---|
| `ipfs_uscode@a9720a...` | Declares train configs `publicus-ir-graphrag/v2` (`data/**/*.parquet`) and `recovery-quarantine/v1` (`recovery/**/*.json`). Internal [`admission.json`](https://huggingface.co/datasets/justicedao/ipfs_uscode/blob/a9720a26a52251526035c2ca8cebea418965bcf9/reports/admission.json): 60,068 admitted corpus rows, 9 quarantined; derived 60,068 BM25 docs, 12,826,459 postings, 60,068 vectors, 242,198 graph nodes, 1,723,928 edges. Release root `bafkreicu56or275w2gtokcxy7hj73su4653xyqxxz6ee24t6hnkbuepmfe`; `thenlper/gte-small@17e1f347d17fe144873b1201da91788898c639cd`. | Card `other`; tag says public-domain U.S. government, but no sufficient rights manifest. Legal-current cutoff explicitly not claimed. Internal source revision `75cfc598...` lacks repository identity. | Internal quality reports pass, but Hub config discovery fails: no-go until repackaged and rights/source identity repaired. |
| `ipfs_state_laws@42f054...` | `state_laws_canonical`: 47,204 Viewer rows, ten fields; `state_laws_embeddings`: 17,338 rows, five fields. README/manifest claims only 20,514 canonical rows. | `other`; exact source pins and cutoff absent. | No-go: live file and manifest disagree. |
| `ipfs_court_rules@c4b34a...` | `state_court_rules_canonical`: 86 rows; `state_court_rules_embeddings`: 76 rows. Ten canonical/five embedding fields; seven states. | `other`; build inputs include unpinned temporary artifacts. | Loadable but unqualified. |
| `ipfs_state_admin_rules@42087d...` | Auto `default/train`; first-row schema exposes 24 top-level fields including source URL, structured citations, parser warnings, scrape time, `scraper_version=1.0`, and CID. Manifest says 4,969 canonical unique CIDs; default size fails because releases are mixed. | No card/license/source pin. | No-go. |
| `ipfs_federal_register@720668...` | Auto `default/train` fails schema/size. Metadata claims 993,703 API records from 1994-01-01 through 2026-03-02, scraped 2026-03-03, `include_full_text=false`. | No card/license; API metadata is not authoritative full text. | No-go. |
| `ipfs_caselaw_access_project@32bb74...` | Auto `default/train`: 7,038,450 rows, 22 fields including CID, citation, court, decision date, text, and CAP provenance. | No license/card/release/source revision. | No-go pending rights and lineage; count only case rows, not associated embedding projections. |
| `dedup_ipfs_caselaw_access_project@70db72...` | Default config cannot determine splits: Parquet magic bytes missing. | Unknown. | Reject broken artifact. |
| `Caselaw_Access_Project_embeddings@53389c...` | Viewer disabled; 16,391 repository files; card describes three embedding families and 4,096 clusters. Exact row count unknown without bulk download. | `agpl-3.0`; source linkage insufficient for independent examples. | Derived auxiliary quarantine. |
| `american_municipal_law@ec3e44...` | Viewer disabled; 4,027 repository files. Card documents HTML, citation, and embedding file families; exact rows/config unions unknown. | Card `mit`; underlying source rights and cutoff not documented. | Source candidate quarantine. |

## Required campaign treatment

1. Freeze the 21 Hub commits above; never use `main` as a durable identity.
2. Admit only source configs/rows after rights review. Treat every section, translation, BM25 row, vector, graph projection, and proof/model trace as a derivative linked to its source CID group.
3. Create a new content-addressed source manifest and lineage-group split manifest. Do not reuse the Hub's train-only partitions as training/evaluation splits.
4. Repair or exclude every Viewer-broken repository. A pinned manifest does not make missing or corrupt data files loadable.
5. Record parser, normalizer, compiler, decompiler, tokenizer, embedding, graph, and checkpoint identities that the current Dutch and legacy checkpoint artifacts omit.
6. Do not interpret retrieval-graph edges, WetWijzer `logic_relationships`, model confidence, cosine proximity, or checkpoint smoke metrics as semantic or proof evidence.
7. Maintain a fail-closed no-go for rights-unknown, source-revision-unknown, stale-manifest, corrupt, or heterogeneous-release inputs.

