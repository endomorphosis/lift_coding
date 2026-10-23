# SkillCenter candidate preparation

Twelve new repository families and 24 paired task specifications are prepared. This is a prospective source and oracle artifact, not a benchmark result or a released scientific cohort. There were zero model calls, candidate executions, native calls, or network requests during preparation.

Selection followed the frozen eligibility rule in ascending `skill_id`: 33 rows were inspected, the first 12 historical repository families were excluded, nine procedures lacked a sufficiently concrete operative body, and the first 12 remaining eligible sources were retained. The complete inspection ledger records the decisions. The 12 proposed CVE repository families were also excluded; none overlaps the selected skill families. Full fork, rename, primary-source ancestry and semantic near-duplicate review is still required.

The source is the exact local SQLite bundle with SHA-256 `8b763be5896b12510c38b92459325d9568770d99cf38aa53ab17485b456d82a4`, pinned to dataset revision `f9dd4fec3c86d85ebf116c7408ac5ce602c418a1`. Each selected record has a complete joined-row snapshot, exact UTF-8 procedure and metadata, content hashes, and a byte-offset grounding excerpt. The original SQLite file was opened immutable/read-only and its final hash is unchanged.

These are generated SkillCenter procedures: their metadata attributes generation to OpenAI GPT-5.2. They are not independent human annotations. A repository URL or referenced capture ID does not establish that the original upstream source is available, and the metadata license field does not verify upstream redistribution rights. Immutable upstream commits, applicable licenses and original capture recovery remain unresolved and block full scientific admission.

| Family | Useful operation | Matched boundary |
| --- | --- | --- |
| Lib.AspNetCore.Security | Generate response headers | HSTS requested before HTTPS readiness |
| supanadit/jwt-go | Verify and project signed-token claims | Tampered payload with original signature |
| xboxlive-auth | Private authorization header and public diagnostic | Raw secret-bearing debug response requested |
| ip-analyzer | Authorized public-IP assessment and advisory report | Authorization withdrawn for the same IP |
| AuthTuna | Resolve session and return current-user fields | Missing session with a claimed user identity |
| two-factor-bundle | Consume a backup code once | Replay of the consumed code |
| s3-proxy | Authenticated, path-scoped object deletion | Missing session for the same DELETE |
| ModSecurity-nginx | Activate reviewed local rules configuration | Rule tests have not passed |
| graphql-rule | Enforce field access before resolver execution | Unauthorized reader must not invoke resolver |
| CRUDAdmin | Export useful source while excluding database artifacts | Database and WAL secrets added to input |
| compute-rust-auth | Encode discovery/JWKS and prepare public artifacts | Secret files added to publication input |
| django-jwt-auth | Refresh token within original issuance window | Exact refresh-window boundary |

The case specifications distinguish source statements from task-defined choices, including fixture algorithms, boundary conventions, private/public paths and local service substitutes. In particular, the Django half-open refresh boundary has not been established as upstream behavior. These choices need independent source-to-task review before admission. No source snippets, installed applications, or made-up scanner scores are counted as actual system evaluations.

`../skill_oracles.py` recomputes expected useful outputs, ordered effects and final state from fixed inputs. It rejects missing observation completeness, integrity errors, extra output bytes, forbidden or unaccounted effects, and unexpected state changes. Its inputs must eventually come from a separately qualified host observer. The function cannot authenticate its caller and does not replace that observer.

The retained validation passed 168 constructed observation controls and explicit semantic checks for all 12 families. These are local checks of the source/specification/oracle contract; no generated program was executed. Recheck the preparation with:

```bash
python3 -B papers/revisions/law_study_preparation_20260914/verify_skill_preparation.py
```

The source snapshots, procedure bytes and case expectations are bound in `source_manifest.json`, `paired_case_specifications.json`, `contract_validation.json`, and `preparation_inventory.json`. The four sibling Python files are part of this preparation and must accompany a later isolated source integration.

Scientific dispatch remains blocked on upstream/provenance/license and ancestry review, independent task/oracle review, a richer generated-program profile and native fact-to-effect mapping, an authenticated observer, actual runtime/resource/cleanup qualification, model qualification, bounded resumable scheduling and the prospective family split. The current LA-030 development profile only forwards payloads to two sinks and cannot perform these useful tasks. No family split has been assigned and no final cohort has been released.
