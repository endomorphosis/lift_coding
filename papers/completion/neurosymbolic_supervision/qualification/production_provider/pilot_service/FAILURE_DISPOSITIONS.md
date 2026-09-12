# Failed pilot slots

The fixed order remains four pilot units × A/B × three repetitions, with all original 48 identities and costs retained. A failed slot is never retried, removed from the population, or credited with a score or success. A normal completed cold scorer that reports failure already remains a measured failed observation.

The host can add `disposition.json` for a known terminated proposal failure, an explicitly rejected sealed candidate before scoring, or a known terminated scorer exception. It preserves the original signed `proposal_result.json` / `result.json`, queue proposal / response, errors, usage, unknown charges, source/profile commitments, and consumed reservations. The separate signature binds those exact original bytes. It adds no model or scorer call. Accounting a scorer exception records current candidate integrity without re-admitting that candidate; rejecting an unscored candidate still requires its exact sealed bytes.

An incomplete or failed original response stays pending in the worker until the host supplies this record. The worker then imports an `unavailable` terminal outcome and retains the original remote costs. Its metadata-only rescore re-verifies both signatures and cannot award a score, validation, or useful-completion credit. An unavailable outcome is not a failed oracle judgment, and final comparison admission remains false. Keep it in the declared pilot denominator with its failure class; do not compute success only over successful/available cells.

## Operator commands

Use the reviewed installed service, private directory and its exact grant SHA. These commands read retained metadata and append accounting records; they never dispatch or score.

1. For candidate rejection, retain an actual `operator_review.json` generated from `review-template`, with `approved: false`, its exact binding, actual timestamp and specific rejection statement. It must precede every score reservation. For a scorer exception, preserve its original approved review and consumed score reservation.
2. Run `python -B pilot_gateway.py disposition-template --private PRIVATE --grant-sha256 SHA --classification CLASS`, where CLASS is `known_proposal_failure`, `candidate_rejected`, or `known_scorer_failure`. Save the returned template separately. Read the retained failure, cleanup identity and costs; create a fresh private `operator_disposition.json` with its exact binding, actual review time, explicit statement and `approved: true`. This approves failure accounting only.
3. Compute that file's SHA256 and run `python -B pilot_gateway.py dispose-failed --private PRIVATE --grant-sha256 SHA --record-sha256 RECORD_SHA`. The private and queue `disposition.json` are append-only. The worker resumes the same scheduled cell; it does not reissue a grant or effect.

The global phase lock and per-grant lock serialize this accounting phase with calls and scores. The durable disposition reservation is consumed before signing. An interruption before a complete signed disposition requires exact-file reconciliation and never authorizes a retry. If the complete private disposition exists but queue publication was interrupted, repeating `dispose-failed` with the same record may copy those identical signed bytes to the queue; it cannot sign a different outcome or run a scientific effect.

## Reconciliation boundary

This version accepts only the existing native child's retained `cleanup.json` with integer returncode 0, exact `container.cid`, and its recorded create command. It refuses missing or failed cleanup, unknown creation, unproven termination, mismatched identities, changed source/profile, and unexpected scorer state. It does not itself inspect or remove containers, ingest an external operator cleanup certificate, or rewrite old cleanup receipts. Such an uncertain slot remains pending until a separately reviewed exact-identity reconciliation path supplies admissible proof; elapsed time or a bare operator assertion is not proof. This restriction must not be mistaken for a scored failure or silently excluded from the pilot.

## Installation and binding

The replacement host package is installed in a fresh root, with the full nine-file source-binding map in `bindings.private.json`. The worker adapter pins that new host package and the exact new client. The production gateway pins the adapter; its pilot runner has one terminal-failure branch. The development route and metadata-only score interpreter otherwise retain their previous bytes/behavior.

Before the first paid call, root must review and rebuild the package, batch, per-cell amendments, activation review, profile and late offer drop for the actual fresh worker/source revision. Reuse the existing four qualified A/B public context packets; no re-encoding, context reselection, population change or mechanism change is needed. Preserve the old package and metadata. A path relocation changes the host source-binding map and requires a newly reviewed matching worker hash binding. No final experiments are authorized by installing this code.
