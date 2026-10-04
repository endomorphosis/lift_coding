# Reconstruction continuation after publication

This prepared run implements the user's request to continue training after the
initial Hugging Face and GitHub publication. It has not started numerical fitting.
Use `run-plan-02.json` and `preflight-02.json`; the first preparation is retained
as superseded evidence. The second version adds portable checkpoint-local tensor
paths and enforces the actual helper source SHA when loading.

The new objective is source-vector self-reconstruction on the original weak
TRAIN16 cohort. Inputs are the pinned spaCy8, GTE-small384 and multilingual
GTE768 source vectors. No formal label, query, DEV target, reviewer claim,
relation mask, parser or prover enters the fit. The original TRAIN metadata
retains `weak_decoder_fit=1` and all four other masks zero. New reconstruction
checkpoints keep all five semantic/decoder admission masks zero and declare
their separate user-authorized reconstruction-only scope. This does not create
semantic gold or authorize the previously proposed 960 contrastive updates.

| New lane | Native input/output | Hidden width | Complete latent width |
| --- | ---: | ---: | ---: |
| legacy8 | 8 | 16 | 4 |
| native384 | 384 | 128 | 32 |
| native768 | 768 | 128 | 64 |

Each encoder has two linear layers with an intermediate tanh; each decoder has
the reverse widths and an intermediate tanh. There is no skip connection or
sample memory. These are separately versioned reconstruction models, preserving
the old sparse spaCy categorical heads, retained 384D residual model and
768D-conditioned source-span decoder. The latter is not a reconstruction AE.

The selected 384D full decoder still rejects its changed UI implementation pin;
its archived projection-only replay remains valid within its named scope. The
768D span trainer can resume only its exact original TRAIN/tuning manifests.
It cannot substitute these TRAIN16 rows. The existing source-only typed-rule
and anchor owners can resume their exact TRAIN16 lineage, but repeating that
already saturated cohort would not address its zero weak DEV agreement. Their
current states are preserved. The isolated decoder checkout is a newer sidecar
source base and needs an explicit source-span overlay before that route can run.

The fixed seeds are 1729, 1730 and 1731 for every lane. Each arm performs 200
Adam updates at learning rate .003, batch size8, CPU float32, one thread,
gradient clipping5. The 16 rows stay in their original ordered identities and
four groups. Shuffling uses a private deterministic Python RNG per epoch.
Coordinate means and one global centered RMS are fitted on TRAIN only; this
normalization is separate from each frozen native producer/pooling profile.
Loss and reconstruction error are interpreted within a lane. Different widths
and capacities prevent treating cross-lane MSE as a semantic comparison.

Every arm saves step0, step100 and selected step200 as `checkpoint.json`,
`model.safetensors` and `optimizer.safetensors`. The checkpoint binds exact
data, producer, native dimensions, normalization, helper source and progress.
Step100 restores into a private model and Adam instance before continuing.
The selected200 model then reloads with bitwise-equal TRAIN outputs. A separate
two-step resume comparison performs three additional optimizer updates: direct
200→201→202 and independently restored201→202. It checks both parameters and
Adam moments without changing the selected200 model. Thus the planned budget
is1800 selected-lineage updates plus27 scratch comparison updates,1827 total.

Raw identity reconstruction has MSE0 without compression. It is recorded as a
control, alongside the untrained step0 network; lower network MSE does not beat
identity or establish retrieval quality. There is no DEV scoring or selection,
and no checkpoint is chosen by observed training loss. The selected budget is
fixed before fitting. All 40-family independent semantic-pilot reviews remain
unexecuted; this run supplies no fidelity or proof coverage measurement.

The native Python is `/home/barberb/.local/bin/python`, with Torch2.13.0+cu130
and safetensors0.7.0. CUDA13 sees one NVIDIA GB10, but its memory query reports
N/A. These small fits explicitly use CPU. Read-only host observations reported
20 CPUs and about46GiB available host memory at inventory time; these are
transient observations, not reserved capacity. Each new worker has90/100-second
CPU limits,8GiB address-space and32MiB output-file limits, and a60-second soft
training deadline. The parent must enforce a120-second wall deadline and poll
without blocking progress updates. This is a trusted local process, not an OS
sandbox. No backbone inference, download or heavy service start is needed.

Run the stdlib input preflight without a publication gate:

```sh
/home/barberb/.local/bin/python -I -B /home/barberb/lift_coding/artifacts/autoformalization-publication-20261004/training/train_reconstruction.py --plan /home/barberb/lift_coding/artifacts/autoformalization-publication-20261004/training/run-plan-02.json --plan-sha256 b02b0b35a9f2d82abd5422643f9034bea30e1d83f0c21772aa0a609c234ead3b --lane native768 --seed 1729 --preflight
```

After root verifies the initial Hugging Face and GitHub source publication,
root supplies an externally pinned, sealed publication gate with exact fields
`schema='reconstruction-publication-gate/v1'`,
`published_artifact_receipts_sha256`, `training_release_authorized=true` and
`content_sha256`. The gate records root's release decision; the numerical
worker does not authenticate external publication itself. No gate is prepared
or invented by this training helper.

Root then runs nine separate workers with the lane/seed/output varied:

```sh
CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /home/barberb/.local/bin/python -I -B /home/barberb/lift_coding/artifacts/autoformalization-publication-20261004/training/train_reconstruction.py --plan /home/barberb/lift_coding/artifacts/autoformalization-publication-20261004/training/run-plan-02.json --plan-sha256 b02b0b35a9f2d82abd5422643f9034bea30e1d83f0c21772aa0a609c234ead3b --lane native768 --seed 1729 --output-directory /home/barberb/lift_coding/artifacts/autoformalization-publication-20261004/training/run-01/native768-seed1729 --publication-gate /ROOT_SELECTED_PUBLICATION_GATE.json --publication-gate-sha256 ROOT_SELECTED_GATE_FILE_SHA256
```

The parent creates the fresh `run-01` directory; every arm directory must not
exist. Failure leaves partial files as incomplete evidence. Recovery resumes
only from separately selected saved state under a new output generation; it
never overwrites or relabels incomplete outputs. The current CLI starts a new
arm; interrupted-arm recovery needs an explicit separately prepared runner.

For the second Hugging Face release, publish the nine selected200 triplets,
the exact helper, run plan, original native-producer metadata and training
reports as experimental reconstruction-only models. Tensor paths in metadata
are fixed local filenames, so the triplet can relocate together. The loader
`load_checkpoint(torch, checkpoint_file_binding, selected_config)` verifies the
externally selected JSON bytes, same helper source, closed metadata, tensor
SHA/names/shapes, finite values, Adam state and normalization identity. It does
not require opening the historical source banks. Consumers normalize using
the saved TRAIN mean/RMS, call `model['encoder']`, and decode then reverse
normalization for native-vector reconstruction. These latents carry no semantic
qualification or formal-language generation claim.
