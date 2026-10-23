# Generated-code 8-probe qualification and 900-cell study

This package freezes the prepared 30 source families / 60 cases, runs the eight
synthetic Leanstral interface probes, then executes the original 60×5×3
generated-code matrix against one warm local model. It does not start a
permanent service.

```sh
python3 -B papers/revisions/law_generated_code_study_20260914/freeze.py
python3 -B scripts/run_leanstral_ephemeral.py \
  --wall-seconds 36000 --startup-seconds 360 \
  --chat-template-file papers/revisions/law_model_qualification_20260914/leanstral_v15.jinja \
  --server-log papers/revisions/law_generated_code_study_20260914/leanstral_server.log \
  -- python3 -B papers/revisions/law_generated_code_study_20260914/run_study.py
```

`interface_qualification/qualification_results.json` is the 8-probe record.
`results.jsonl` and `summary.json` are the 900-cell record. Model-generated
programs run in the bounded in-process interpreter; A0–A2 are unguarded inside
the fixture, A3 applies path policy, and A4 additionally refuses secret-bearing
arguments. These are policy-relative observations, not legal-validity scores.
