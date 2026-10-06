# Normative wording LegalIR candidate checkpoints

This release preserves exact existing trained candidate bytes. It does not promote a decoder.

The complete study has four unique tensor endpoints and eight serialized states: selected and last-attempt aliases for zero and 0.05 modality-loss arms at 384D and 768D. This repository contains 4 state files. Each has all 32 model-state entries, but no optimizer/resume contract. Native output schema/version, decoder profile and format identities remain unknown.

The task is semantic_IR_reconstruction with native 384D/768D paragraph input, ordered eight clause vectors and a boolean mask. Apply the saved TRAIN-only input transform to real clause vectors once, then zero-pad; saved internal paragraph/clause normalization is a separate stage. Existing width-specific assets and embeddings were reused. Publication generates no embeddings.

The recorded experiment uses 512-token source scope and 512-token decoder output. The 768D encoder's 8192-token capacity does not qualify 8192-token reconstruction. The original contextual facade's saved recipe is unsupported for these normative states. Donor weights, original preprocessing corpora, raw vectors and executable model code are not bundled; metadata extracts preserve normalization/transform/initializer/prior values and original custody pins. This release alone does not supply a complete runtime restoration closure or a trained legal-text reconstruction head.

Runtime readiness, teacher/quality qualification, source-semantics and proof authority are false. The prospective 60-row wording panel uses previously exposed meanings; it is not a fresh semantic holdout. Source/context inventory correspondence is separate from independent encoder-producer authentication.
