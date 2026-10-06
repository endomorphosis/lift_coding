# Decoder modality gap, October 6

Four frozen 384D/768D selected endpoints were observed on the previously exposed
v3 cohort. Every generated token/status/EOS exactly matched its archived output.
All 2,880 scalar sites and full 32-token logits were retained. The main modality
errors originate in the source head; the positive 384D arm also has one correct
source prediction overturned by recurrence. No weights were trained or promoted.

| Endpoint | Source modality correct | Combined correct | Exact paragraphs |
| --- | --- | --- | --- |
| 384D zero | 139/180 | 139/180 | 20/48 |
| 384D 0.05 auxiliary | 137/180 | 136/180 | 19/48 |
| 768D zero | 178/180 | 178/180 | 46/48 |
| 768D 0.05 auxiliary | 178/180 | 178/180 | 46/48 |

[Completed findings](diagnosis/completed_findings.md) and the
[independent numerical audit](diagnosis/independent-numerical-audit.json) record
66,467 checks; [formula transitions](diagnosis/matched-formula-transitions.json)
pair complete reference and generated rules with their observed component scores.
[Runner tests](runner_review/tests-r2-receipt.json) record 73 passing pure cases.
The guardian and child exited successfully and released their resources.

[Data readiness](data/README.md) and its 3,839-check audit identify reusable R4
TRAIN vectors and the other agents' 64-source native caches. Pending formal
reviews and output-vocabulary limits remain explicit. The
[next training specification](data/next-wording-training-spec.md) fixes broader
TRAIN wording, original-rule provenance, controls, future development sealing
and bounded preparation. It is specified, not executed.

`review-evidence.tar.gz` has 78 bounded source/JSON evidence members, including
actual traces and guard receipts. Its SHA256 is
`5718a88ac5761109344e486ec4bd80a52dc02b8daa81404ce61798f7666af594`.
It excludes checkpoint tensors, encoder assets and predecessor source trees.
Local authenticated dependencies are needed to reproduce the numerical run.
The superseded first preparation seal is retained; it launched no model or lease.

This observed decoder study uses historical frozen numerical producers and warm
source vectors, one CPU worker, temperature 0, 512-token context/output,
bridge names `[]`, prover evaluation false and metric disk cache disabled.
It is not a current compiler or bridge-on Legal-IR speed measurement.
Only applicable successful `lake build <Lib>` grants Lean admission. No compiler,
family semantic validation or Lake build ran; no Constitution span is formalized.
