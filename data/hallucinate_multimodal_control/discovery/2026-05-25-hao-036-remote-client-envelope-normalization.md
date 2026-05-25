# HAO-036 Remote Client Envelope Normalization

Date: 2026-05-25
Task: HAO-036

## Summary

Meta-glasses, mobile, and simulator remote-client artifacts now carry the
canonical Hallucinate App control-surface payloads:

- `control_surface_contract_ref`
- `interaction_envelope`
- `normalized_intent`
- `policy_decision`
- `mediation_receipt`

The mobile ORB bridge no longer mints a `sha256:mobile-orb-policy:*` policy
contract for edge registration. The legacy `policy_cid` field remains nullable
for compatibility only, while stored edge-session records and bridge responses
use `control_surface_contract_ref` plus `mediation_receipt`.

Published glasses events no longer store a local `accepted: True` artifact in
the backend event record. The API response still exposes `accepted` as a
transport compatibility projection derived from the canonical mediation receipt.

## Evidence

The evidence in
`data/hallucinate_multimodal_control/discovery/2026-05-25-hao-025-implementation-unknowns.md`
identified local permit/accepted artifacts in
`src/handsfree/meta_glasses_mobile_orb_artifacts.py`. This implementation
replaced those local artifacts with canonical Hallucinate App envelope builders
and mirrored the same artifact transport through the mobile simulator bridge and
Swissknife mobile ORB service.

Remote clients can now transport an existing `mediation_receipt`, but the local
remote-client paths do not define a separate `control_surface_contract` object
or authorize through a separate mobile policy contract.
