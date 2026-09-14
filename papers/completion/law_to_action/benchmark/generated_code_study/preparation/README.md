# LA-032 generated-code study preparation

This directory holds the prospective freeze builder and the earlier bootstrap
discovery. Completing LA-032 records readiness; it does not execute the 900
scientific cells.

Reproduce the freeze:

```sh
python3 -B papers/completion/law_to_action/benchmark/generated_code_study/preparation/prepare_study.py
python3 -B papers/completion/law_to_action/benchmark/generated_code_study/verify_preparation.py \
  --study papers/completion/law_to_action/benchmark/generated_code_study/prospective_study.json \
  --require-scientific-cells-unexecuted
```

Source bodies remain retrieval-only in a host cache. They are hashed, not
copied into the paper artifact.
