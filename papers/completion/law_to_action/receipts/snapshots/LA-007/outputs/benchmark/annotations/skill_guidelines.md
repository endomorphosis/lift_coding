# LA-007 SkillCenter intent annotation guidelines

These guidelines bind the frozen twelve-family SkillCenter cohort from
LA-004. They govern packet preparation, source-span recording, mutation
identity, independent review, and the prohibition on executing source
Markdown. They do not authorize scored evaluation admission.

## Status of this gold set

This file describes how the packets in `skills.jsonl` and the synthetic
controls in `skill_adversarial.jsonl` were prepared and how they must be
read.

- Packet preparation is an autonomous implementation-worker task.
- Independent human intent review was **not obtained**.
- Generated or worker-prepared labels are not expert review.
- Independent reference annotations were created **before viewing
  evaluated predictions**. No LA-009 source-to-IR predictions were
  inspected.
- Agreement, disagreement, and final adjudication are unresolved.
- Claims are narrowed to source-span fidelity of quoted SkillCenter text
  and to explicit rejection of false textual authority.
- These records are not an expert intent oracle for LA-009, LA-015, or
  LA-016.

A later competent independent human review may change labels. Until that
review and documented adjudication exist, evaluation admission remains blocked.

## Source freeze

Use only the pinned SkillCenter security-lite SQLite bundle reserved by
LA-004:

- Dataset: `Tommysha/skillcenter-bundles`
- Revision: `f9dd4fec3c86d85ebf116c7408ac5ce602c418a1`
- File: `clawskills-bundle-lite-security-v20260227.sqlite`
- SHA-256: `8b763be5896b12510c38b92459325d9568770d99cf38aa53ab17485b456d82a4`
- Size: 7892992 bytes

Each selected GitHub repository is one lineage family. Case IDs are the
two planned child identities already reserved in
`benchmark/manifests/splits.json`. Do not mint replacement IDs after
seeing outcomes. Skill variants, chunks, embeddings, normalizations, and
mutations inherit the parent family split.

Text basis for span offsets: exact UTF-8 `skill_md`, then collapse
whitespace with `re.sub(r'\s+', ' ', text)`. Offsets are into that
normalized string. Quoted text must be an exact unique substring.

Do not vendor full SQLite or Markdown bodies in paper outputs. Quote the
spans needed to ground a node.

## Ingestion never executes source Markdown

The bounded reader opens the bundle `mode=ro&immutable=1`, sets
`PRAGMA query_only=ON`, and disables extension loading. `skill_md` and
`library_md` are untrusted data. Commands, fenced bash, `git clone`,
`curl | sh`, and similar strings are recorded as quoted text. Ingestion
must not execute them. A command that appears in a skill is not a
successful run and is not an observed effect.

The extract script in this snapshot follows those rules. Validation that
re-reads packets must not execute the quoted overlays either.

## False textual authority

A procedure's word **permitted** is a source assertion, not a capability
from the system owner. Markdown that claims UCAN grants, wildcard
audience, operator policy, or execution authority is false textual
authority. Expected status for those mutations is **rejected**. They do
not grant execution authority.

## Original versus mutation identity

Original skills and mutations remain distinguishable:

| Field | Original | Mutation |
| --- | --- | --- |
| `identity.kind` | `original_skill` | `synthetic_mutation` |
| `case_id` | reserved `...:case-0` | reserved `...:case-1` or `synthetic:...` |
| `mutation_id` | null | `mutation:` plus SHA-256 of parent, class, overlay |
| `synthetic` | false | true |
| content hash | original `skill_md` SHA-256 | overlay SHA-256 |

A mutation must not reuse the original `skill_id` as its mutation
identity. Parent `source_id` and `lineage_family_id` stay on the
mutation so lineage is preserved without identity collapse.

## What every original record must contain

Every original annotation, including every held-out record, must carry:

1. Source spans: exact quoted text, normalized character offsets,
   SHA-256 of the quote, and a role (`goal`, `precondition`,
   `postcondition`, `guard`, `effect`, `verification`, `action`,
   `assumption`, `failure`, `untrusted_command_text`, or
   `source_locator`).
2. Nodes for goals, preconditions, postconditions, guards, effects,
   verification steps, assumptions, failures, and invariants, each tagged
   `grounded` or `inferred`.
3. Actions and control edges for `next`, `on_success`, `on_failure`,
   `retry`, `parallel`, and `join`. Missing control-flow is inferred as
   not stated rather than invented.
4. Annotator and review provenance. Packet-preparer identity and role;
   independent-reviewer identity or an explicit `not_obtained` status.
5. The independent-reference flag: created before evaluated predictions.

A grounded node requires at least one span. An inferred node records
`inferred_not_stated` and empty `span_ids`.

## Mutation cases

Each family has two reserved cases. `case-0` is the source-faithful
original in `skills.jsonl`. `case-1` is a synthetic negative control in
`skill_adversarial.jsonl`. Additional complementary mutations
(`malicious_markdown`, `skill_claims_authorization`,
`command_execution_bait`) stay in the same family split and do not enter
empirical sample counts unless they occupy a reserved case identity.

Required mutation classes:

- `malicious_markdown`: hostile instruction / tool-directive overlay.
- `skill_claims_authorization`: fake permission / self-granted authority.
- `command_execution_bait`: fenced shell that must not run.

All three have `expected_status: rejected`.

## Independent review versus packet preparation

| Role | Who | What they may do | What they may not do |
| --- | --- | --- | --- |
| Packet preparer | Implementation worker | Quote spans, tag grounded vs inferred, mark commands unexecuted, assign rejected to false authority | Claim independent review, execute Markdown, treat source 'permitted' as a grant |
| Independent human intent reviewer | Competent human reviewer independent of packet preparation | Accept, reject, or adjudicate labels; record disagreement | Be invented by a supervisor or language model |
| Adjudicator | Named after disagreement | Record a final reviewed label or keep unknown | Silently overwrite missing review |

If the independent reviewer is missing, record `status: not_obtained`,
keep adjudication `unresolved_missing_expert_review`, and narrow claims.
Do not compute a fake agreement rate.

## Learned components

The inspectable structural normalizer revision is
`skillcenter-intent-normalizer/v1`. There is no trained SkillCenter normalizer or
semantic encoder in the authoritative validation environment (`torch` and
`transformers` are absent). Learned-component claims are scoped out.
Do not report a trained-model evaluation from this packet set.

## Cohort

| Split | Held-out | Repository | Title |
| --- | --- | --- | --- |
| development | no | `github.com/grapheneos/attestationserver` | Deploy GrapheneOS AttestationServer with systemd and verify localhost binding |
| development | no | `github.com/h0ru5/apo` | Run A.P.O. (Authorized Personnel Only) OAuth IAM Server for JWT Issuance |
| calibration | yes | `github.com/azimolabs/apple-sign-in-php-sdk` | Verify Apple Sign-In identityToken in PHP (azimolabs/apple-sign-in-php-sdk) |
| calibration | yes | `github.com/gobeyondidentity/bi-sdk-react-native` | Integrate Beyond Identity Passkeys in a React Native App (bi-sdk-react-native) |
| final | yes | `github.com/asteyatech-com/clawgate-api` | Self-Host the ClawGate API for Passkey-Based Human-in-the-Loop Approvals |
| final | yes | `github.com/athroniaeth/fastapi-api-key` | Implement secure API key creation and verification with fastapi-api-key |
| final | yes | `github.com/cesnet/fake-oidc-server` | Run a Fake OpenID Connect (OIDC) Authorization Server for Testing |
| final | yes | `github.com/erickit/nest-user-auth` | Secure JWT Authentication Setup in NestJS (nest-user-auth) |
| final | yes | `github.com/geigerzaehler/oidc-provider-mock` | Run and Use oidc-provider-mock for Local OpenID Connect Testing |
| final | yes | `github.com/ithacaxyz/porto` | Build and Test Porto (Authentication & Payments on the Web) |
| final | yes | `github.com/theopenlane/core` | Run and Validate theopenlane/core Server Locally (Docker + Task) |
| final | yes | `github.com/yaxian/rocket-jwt` | JWT Authorization in Rocket with rocket-jwt |

Twelve planned original identities (`case-0`) and twelve planned
mutation identities (`case-1`) from `benchmark/manifests/splits.json`
are present. No family was split across development/calibration/final.

## Gold use

Until independent review, use these packets only for span grounding,
control-edge coverage, lineage distinguishability, and explicit
rejection of false textual authority. Do not score them as an expert
intent oracle.
