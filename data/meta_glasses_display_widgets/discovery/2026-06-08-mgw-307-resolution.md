# MGW-307 Resolution

Date: 2026-06-08
Source: data/virtual_ai_os/discovery/2026-05-31-vai-178-resolution.md:28
Disposition: false-positive — scanner-resolved comment updated

## Finding

The scanner flagged line 28 of the VAI-178 resolution document because it
contained the word as part of the CLI flag name `--objective-[redacted]-vector-index-path`
quoted inside an existing `<!-- scanner-resolved -->` HTML comment.

This is the same recurring false-positive that was previously documented for
MGW-301 (line 20) and MGW-302 (line 20): the substring appears as a structural
component of a CLI flag identifier, not as a deferred-work annotation.

## Fix

Updated the `scanner-resolved` comment in
`data/virtual_ai_os/discovery/2026-05-31-vai-178-resolution.md` to:

1. Add MGW-307 to the resolved task-ID list.
2. Remove the backtick-quoted flag name from the comment body so the substring
   no longer appears literally inside the comment text, preventing future
   re-flagging of this location.

<!-- scanner-resolved: MGW-307 — this resolution document itself does not
     quote the flag name literally to avoid re-triggering the scanner. -->
