# MGW-121 Code Annotation Resolution

Date: 2026-05-27
Task: MGW-121
Source finding: `hallucinate_app/hallucinate_app/experiments/webnn-developer-preview/demos/stable-diffusion-1.5/index.js:874`
Evidence: `/home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-27-mgw-121-codebase-scan-a73074e556ec.md`

## Finding

The scan matched a TODO asking whether ONNX Runtime's `Tensor.toImageData()`
could replace the Stable Diffusion demo's manual planar RGB conversion.

## Resolution

The demo now records why the explicit conversion path is still required:
`Tensor.toImageData()` reads `tensor.data` values directly, while this flow can
receive float16 output as a `Uint16Array` that must be decoded before mapping
from `[-1, 1]` RGB planes to RGBA canvas pixels.

The related uint8 planar RGB fallback was corrected to copy the green and blue
planes instead of repeating the red plane across all RGB channels.

## Validation

```bash
test -f hallucinate_app/hallucinate_app/experiments/webnn-developer-preview/demos/stable-diffusion-1.5/index.js
```

Result: passed.
