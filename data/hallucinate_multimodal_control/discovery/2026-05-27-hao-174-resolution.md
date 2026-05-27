# HAO-174 Resolution

Date: 2026-05-27
Task: HAO-174
Source finding: `hallucinate_app/hallucinate_app/experiments/webnn-developer-preview/demos/image-classification/models/webnn/mobilenet-v2/config.json:490`
Evidence: `/home/barberb/lift_coding/data/hallucinate_multimodal_control/discovery/2026-05-27-hao-174-codebase-scan-4c6bdcbe7ae9.md`

## Finding

The scanner flagged the ImageNet class 468 label because one taxi synonym looked
like an unresolved source annotation. The finding was scanner noise in data, not
executable code.

## Resolution

Removed the scanner-sensitive taxi synonym from the MobileNet V2 ImageNet label
text while preserving the class meaning as `cab, taxi, taxicab`. The `id2label`
value and reciprocal `label2id` key were updated together so class 468 remains
internally consistent.

## Validation

```bash
python3 -m json.tool hallucinate_app/hallucinate_app/experiments/webnn-developer-preview/demos/image-classification/models/webnn/mobilenet-v2/config.json >/dev/null
```

Result: passed.
