# UIR-087 recovery receipt — text-prefix verify (2026-08-04)

## Failure

UIR-010 repair-grant attempt 4:

1. Landed-route fallthrough + seal-after-start succeeded.
2. Production packet built with multi-file scope including
   `ui_ux_ir.schema.json` as `text-prefix@1`.
3. Packet verify failed closed with `corpus_widening`:
   source selection contained `prefix_byte_length`, which the verifier did not
   allow (only `mode` + `qualified_symbols` were accepted).

Failure event `sha256:9952417126feeadb4b0e619e40017c6ddec01b1cb323f9c35ac130e08602a6eb` sequence **2126**.

## Fix

`verify_production_context_slice` now accepts `text-prefix@1` with
`prefix_byte_length` and rebuilds the deterministic prefix selection.

## Release

Completing this repair mints attempt **5** for UIR-010.
