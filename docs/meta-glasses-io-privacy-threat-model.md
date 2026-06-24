# Meta Glasses I/O Privacy Threat Model

MGW-416 defines the privacy and policy gate for expanded Meta glasses input and
output. No implementation should emit, persist, or replay real user data from
these surfaces until the control plane can produce an enforceable policy
decision, consent record, redaction result, retention class, replay guard, and
MCP++ audit receipt.

## Scope

The threat model covers the expanded I/O envelope used by Swissknife,
Hallucinate App, mobile bridges, simulators, and app-level MCP++ routes:

| Surface | Sensitive data | Minimum gate before data leaves the device or adapter |
| --- | --- | --- |
| camera capture | Photos, video frames, scene text, bystander faces, screens, documents | Explicit camera consent, app binding ID, policy decision, privacy redaction, retention class, and content-addressed payload reference. |
| microphone route/capture | Speech, background audio, voice identity, transcript text | Explicit microphone consent, active route label, capture indicator, transcript redaction, and denial path for stale or lost routes. |
| speaker/headphone playback | Spoken responses, notification content, private prompts | Playback consent, selected speaker or headphone route, volume/route readiness, and policy denial for unsafe contexts. |
| display content | Widget text, notification previews, generated images, action affordances | Display render scope, redacted content preview, retention class for screenshots or display assets, and confirmation for sensitive actions. |
| phone GPS | Precise or coarse location, travel patterns, home/work inference | Location consent, purpose binding, age/staleness bound, coarse downgrade support, and default denial for background use. |
| motion/orientation | Head pose, activity inference, attention or driving context | Sensor consent where required, sample-rate cap, aggregation/redaction, and denial when policy forbids context inference. |
| Meta Neural Band and captouch | Gesture intent, wrist interaction timing, focus/activation choices | Gesture/captouch consent, normalized intent only, no raw EMG assumption, replay nonce, and quiet-hours or sleeping policy denial. |

The contract also covers app binding IDs, control-plane routing, IPFS
persistence, libp2p peer/session metadata, and MCP++ receipts because those
metadata records can identify users, devices, peers, sessions, locations, and
behavior even when raw media is absent.

## Privacy Invariants

- Default outcome is deny. A route that lacks consent, a policy decision, an
  app binding ID, or an MCP++ receipt must not emit real camera, microphone,
  speaker, headphone, display, GPS, motion/orientation, Meta Neural Band, or
  captouch user data.
- App binding IDs are mandatory for every capture, render, playback, gesture,
  sensor, context, and route-control operation. The binding links the requesting
  app, method, surface, permission scopes, and route decision.
- Control-plane routing carries references and receipts, not raw Bluetooth,
  Wi-Fi, DAT, or Web Apps packets. IPFS/libp2p compatibility is expressed in
  app-level bridge envelopes and MCP++ metadata.
- Raw payloads are replaced by content-addressed references when persistence is
  allowed. Payload references must include purpose, media type, size, redaction,
  and retention metadata.
- Redaction happens before persistence, peer relay, audit export, replay
  fixture creation, or model/tool invocation. Unredacted payloads may remain
  only in a local ephemeral buffer required to complete the current authorized
  action.
- Retention is explicit: `ephemeral`, `session`, `policy_controlled`, or
  `pinned`. Camera, microphone, GPS, motion/orientation, Neural Band, and
  captouch data default to `ephemeral` unless the user grants a narrower purpose
  and policy allows a longer class.
- Auditability is mandatory. Each allow, deny, fallback, degrade, or
  confirmation result emits an MCP++ receipt with a correlation id, policy
  decision reference, route id, app binding ID, and parent receipt CIDs when the
  decision derives from earlier receipts.
- Replay protection is mandatory for all real I/O. Route decisions and receipts
  must include a fresh interaction id, route generation, peer/session ids,
  timestamp or monotonic sequence, and nonce or challenge hash so stale camera,
  microphone, GPS, gesture, playback, or display envelopes cannot be reused.

## Threats And Required Controls

| Threat | Affected surfaces | Required control |
| --- | --- | --- |
| Silent capture or route confusion | camera, microphone, phone GPS, motion/orientation | Require foreground consent, route readiness, app binding ID, visible capture state where applicable, and deny on missing or stale route metadata. |
| Bystander or environment disclosure | camera, microphone, display screenshots | Apply redaction for faces, screens, documents, secrets, transcripts, and notification text before persistence or relay. |
| Private output leakage | speaker, headphone, display content | Bind playback/display to the selected route; deny or require confirmation when a public speaker, shared display, locked screen, driving state, or meeting context is active. |
| Gesture misfire or unintended activation | Meta Neural Band, captouch, motion/orientation | Normalize to intent events, apply debouncing and replay nonces, and honor denial policies such as sleeping, quiet hours, driving, or app not focused. |
| Location or behavior profiling | GPS, motion/orientation, libp2p peer/session metadata | Minimize precision, cap sample rate, record staleness, redact peer/session exports, and use session retention unless policy grants more. |
| Cross-app confused deputy | app binding IDs, control-plane routing | Reject route decisions whose binding app id, method, scopes, descriptor CID, or MCP++ interface CID do not match the invoking app. |
| Persistent data escape | IPFS persistence | Persist only redacted payload refs with declared retention; deny pinning by default; require explicit consent and policy decision for `pinned` or externally shared CIDs. |
| Peer/session correlation | libp2p peer/session metadata | Treat peer ids and session ids as personal metadata; log hashed or scoped identifiers where possible; apply retention and audit policy to metadata too. |
| Receipt forgery or replay | MCP++ receipts, route decisions | Sign or hash receipt bodies, include parent receipt CIDs and nonce/sequence fields, reject duplicate correlation ids, and deny stale route generations. |
| Policy bypass | all surfaces | Invoke policy before capture, render, playback, persistence, relay, model/tool calls, or app dispatch. Denial paths must return a receipt and no raw payload. |

## Denial Paths

Implementations must fail closed before emitting real user data when any of
these checks fail:

- missing or expired consent for the requested camera, microphone, speaker,
  headphone, display, GPS, motion/orientation, Meta Neural Band, or captouch
  scope;
- missing app binding ID, descriptor CID, interface CID, or requested method
  mismatch;
- missing policy decision, denied policy decision, or unresolved confirmation;
- unsupported, unavailable, permission-denied, stale-session, disconnected, or
  route-lost readiness without an allowed fallback route;
- missing redaction metadata for a payload that could contain private content;
- missing retention metadata, or a retention request broader than the policy
  decision permits;
- missing MCP++ receipt metadata, libp2p peer/session metadata, replay nonce,
  route generation, or correlation id;
- duplicate replay nonce, stale route generation, expired receipt, or parent
  receipt CID mismatch.

Denial receipts must preserve enough metadata for auditability while excluding
raw camera frames, microphone audio, transcript text, GPS coordinates, display
content, Neural Band/captouch event detail beyond normalized intent, and any
unredacted payload CID.

## Implementation Readiness Checklist

Before enabling real data emission, each route must prove:

- consent UX and persisted consent state exist for every required permission
  scope;
- the policy decision point runs before capture/playback/render/relay;
- redaction and retention metadata are mandatory in payload refs;
- IPFS persistence is disabled or policy-controlled for sensitive payloads;
- libp2p peer/session metadata is minimized and retained under policy;
- MCP++ receipts include policy, route, app binding, replay, and parent linkage;
- replay protection rejects duplicates and stale route generations;
- fallback and denial paths are covered without leaking raw user data.
