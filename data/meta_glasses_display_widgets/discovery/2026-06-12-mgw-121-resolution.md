# MGW-121 Resolution

Date: 2026-06-12
Task: MGW-121
Source: hallucinate_app/hallucinate_app/experiments/webnn-developer-preview/demos/stable-diffusion-1.5/index.js:874

## Finding

The codebase scan reported a stale follow-up annotation:

```text
// TODO: See if ORT's toImageData() is flexible enough to handle this instead.
```

## Resolution

The current submodule source no longer contains that TODO. The image conversion
path now routes planar RGB tensors through `convertPlanarRgbTensorToImageData()`.
That helper uses ORT `toImageData()` for tensor data that exposes numeric channel
values directly, while keeping the explicit Uint16 float16 decoder fallback for
encoded half-float data before writing canvas `ImageData`.

This resolves the annotation without changing runtime behavior in this worktree.
