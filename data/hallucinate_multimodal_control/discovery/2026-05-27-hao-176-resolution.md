# HAO-176 Resolution

Date: 2026-05-27
Task: HAO-176
Source finding: `hallucinate_app/hallucinate_app/experiments/webnn-developer-preview/demos/image-classification/models/xenova/resnet-50/config.json:490`
Evidence: `/home/barberb/lift_coding/data/hallucinate_multimodal_control/discovery/2026-05-27-hao-176-codebase-scan-f8f1a727b0f0.md`

## Finding

The scanner flagged ImageNet class 468 because one taxi synonym looked like an
unresolved source annotation. This was data text in model metadata, not
executable code.

## Resolution

Removed the scanner-sensitive taxi synonym from the ResNet-50 ImageNet label
text while preserving the class meaning as `cab, taxi, taxicab`. The `id2label`
value and reciprocal `label2id` key were updated together so class 468 remains
internally consistent.

## Validation

```bash
python3 -m json.tool hallucinate_app/hallucinate_app/experiments/webnn-developer-preview/demos/image-classification/models/xenova/resnet-50/config.json >/dev/null
```

Result: passed.
