# HAO-174 Codebase Scan Finding

Date: 2026-05-27
Fingerprint: 4c6bdcbe7ae962b1d80b0f1a47b1fce5f341f120
Kind: annotated_followup
Source: hallucinate_app/hallucinate_app/experiments/webnn-developer-preview/demos/image-classification/models/webnn/mobilenet-v2/config.json:490
Priority: P2
Track: ops

## Evidence

```text
"468": "cab, hack, taxi, taxicab",
```

## Suggested Handling

Review the finding in context, decide whether it represents a bug, missing test,
maintenance risk, or false positive, and land a small fix with validation. If the
finding is a false positive, document why in the changed code or discovery notes
so the supervisor does not keep re-adding the same work.
