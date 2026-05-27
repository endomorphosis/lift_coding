# HAO-178 Resolution

Date: 2026-05-27
Task: HAO-178
Source finding: `hallucinate_app/hallucinate_app/experiments/webnn-developer-preview/demos/stable-diffusion-1.5/index.js:874`
Evidence: `/home/barberb/lift_coding/data/hallucinate_multimodal_control/discovery/2026-05-27-hao-178-codebase-scan-a73074e556ec.md`

## Finding

The scanner found an unresolved TODO asking whether ONNX Runtime's
`Tensor.toImageData()` could replace the Stable Diffusion demo's custom planar
RGB conversion.

## Resolution

The current display path keeps the decoded output as an ORT tensor after
`getData()` and calls `toImageData()` with NCHW RGB options when the backing
array exposes numeric float channel values directly.

The manual conversion path remains for `Uint16Array` float16 output because that
data stores encoded half-float bits and must be decoded before mapping the
`[-1, 1]` RGB planes to RGBA canvas pixels. The planar uint8 fallback copies the
red, green, and blue planes separately instead of repeating the red plane across
all channels.

## Validation

```bash
test -f hallucinate_app/hallucinate_app/experiments/webnn-developer-preview/demos/stable-diffusion-1.5/index.js
node --check hallucinate_app/hallucinate_app/experiments/webnn-developer-preview/demos/stable-diffusion-1.5/index.js
```

Result: passed.
